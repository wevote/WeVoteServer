# friend/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from .models import ACCEPTED, FriendInvitationVoterLink, FriendManager, CURRENT_FRIENDS, \
    DELETE_INVITATION_EMAIL_SENT_BY_ME, DELETE_INVITATION_VOTER_SENT_BY_ME, FRIEND_INVITATIONS_PROCESSED, \
    FRIEND_INVITATIONS_SENT_BY_ME, FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION, \
    IGNORE_SUGGESTION, SUGGESTED_FRIEND_LIST, \
    FRIENDS_IN_COMMON, UNFRIEND_CURRENT_FRIEND
from config.base import get_environment_variable
from email_outbound.controllers import schedule_email_with_email_outbound_description, schedule_verification_email
from email_outbound.models import EmailAddress, EmailManager, FRIEND_ACCEPTED_INVITATION_TEMPLATE, \
    FRIEND_INVITATION_TEMPLATE, WAITING_FOR_VERIFICATION, TO_BE_PROCESSED
from follow.models import FollowIssueList
from import_export_facebook.models import FacebookManager
import json
from organization.controllers import transform_web_app_url
from organization.models import OrganizationManager, INDIVIDUAL
from position.controllers import add_position_network_count_entries_for_one_friend
from position.models import PositionMetricsManager
from validate_email import validate_email
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import generate_random_string, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def fetch_friend_invitation_recipient_voter_we_vote_id(friend_invitation):
    if hasattr(friend_invitation, 'recipient_voter_we_vote_id'):
        return friend_invitation.recipient_voter_we_vote_id
    elif hasattr(friend_invitation, 'recipient_voter_email'):
        email_manager = EmailManager()
        temp_voter_we_vote_id = ""
        primary_email_results = email_manager.retrieve_primary_email_with_ownership_verified(
            temp_voter_we_vote_id, friend_invitation.recipient_voter_email)
        if primary_email_results['email_address_object_found']:
            email_address_object = primary_email_results['email_address_object']
            return email_address_object.voter_we_vote_id

    return ''


def friend_accepted_invitation_send(accepting_voter_we_vote_id, original_sender_we_vote_id, invitation_message='',
                                    web_app_root_url=''):
    """
    A person has accepted a friend request, so we want to email the original_sender voter who invited the
    accepting_voter
    :param accepting_voter_we_vote_id:
    :param original_sender_we_vote_id:
    :param invitation_message:
    :param web_app_root_url:
    :return:
    """
    status = ""

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_we_vote_id(accepting_voter_we_vote_id)
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

    if not voter_results['voter_found']:
        error_results = {
            'status':                               "ACCEPTING_VOTER_NOT_FOUND",
            'success':                              False,
        }
        return error_results

    accepting_voter = voter_results['voter']

    original_sender_voter_results = voter_manager.retrieve_voter_by_we_vote_id(original_sender_we_vote_id)
    if not original_sender_voter_results['voter_found']:
        error_results = {
            'status':                               "ORIGINAL_SENDER_VOTER_NOT_FOUND",
            'success':                              False,
        }
        return error_results

    original_sender_voter = original_sender_voter_results['voter']

    email_manager = EmailManager()

    # Retrieve the email address of the original_sender (which is the person we are sending this notification to)
    original_sender_email_we_vote_id = ""
    original_sender_email = ""
    if original_sender_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(original_sender_we_vote_id)
        if results['email_address_object_found']:
            original_sender_email_object = results['email_address_object']
            original_sender_email_we_vote_id = original_sender_email_object.we_vote_id
            original_sender_email = original_sender_email_object.normalized_email_address
    else:
        # Not having an email is ok now, since the original_sender could have signed in with SMS or Twitter
        status += "ORIGINAL_SENDER_VOTER_DOES_NOT_HAVE_VALID_EMAIL "

    # Retrieve the email address of the accepting_voter (the person who received the friendship invitation)
    accepting_voter_email = ""
    accepting_voter_we_vote_id = accepting_voter.we_vote_id
    if accepting_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(accepting_voter_we_vote_id)
        if results['email_address_object_found']:
            accepting_voter_email_object = results['email_address_object']
            accepting_voter_email = accepting_voter_email_object.normalized_email_address
    else:
        # Not having an email is ok now, since the accepting_voter could have signed in with SMS or Twitter
        status += "ACCEPTING_VOTER_DOES_NOT_HAVE_VALID_EMAIL "

    if positive_value_exists(original_sender_email_we_vote_id):
        original_sender_voter_we_vote_id = original_sender_voter.we_vote_id

        # Template variables
        real_name_only = True
        original_sender_name = original_sender_voter.get_full_name(real_name_only)
        accepting_voter_name = accepting_voter.get_full_name(real_name_only)
        accepting_voter_photo = accepting_voter.voter_photo_url()
        accepting_voter_description = ""
        accepting_voter_network_details = ""

        # Variables used by templates/email_outbound/email_templates/friend_accepted_invitation.txt and .html
        if positive_value_exists(accepting_voter_name):
            subject = accepting_voter_name + " has accepted your invitation on We Vote"
        else:
            subject = "Friend accepted your invitation on We Vote"

        template_variables_for_json = {
            "subject":                      subject,
            "invitation_message":           invitation_message,
            "sender_name":                  accepting_voter_name,
            "sender_photo":                 accepting_voter_photo,
            "sender_email_address":         accepting_voter_email,  # Does not affect the "From" email header
            "sender_description":           accepting_voter_description,
            "sender_network_details":       accepting_voter_network_details,
            "recipient_name":               original_sender_name,
            "recipient_voter_email":        original_sender_email,
            "see_your_friend_list_url":     web_app_root_url_verified + "/friends",
            "recipient_unsubscribe_url":    web_app_root_url_verified + "/unsubscribe?email_key=1234",
            "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
        }
        template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

        # Create the outbound email description, then schedule it
        kind_of_email_template = FRIEND_ACCEPTED_INVITATION_TEMPLATE
        sender_voter_email = ""
        outbound_results = email_manager.create_email_outbound_description(
            sender_voter_we_vote_id=accepting_voter_we_vote_id,
            sender_voter_email=sender_voter_email,
            # sender_voter_name=original_sender_name,  # Not needed in notification that friend request was accepted
            recipient_voter_we_vote_id=original_sender_voter_we_vote_id,
            recipient_email_we_vote_id=original_sender_email_we_vote_id,
            recipient_voter_email=original_sender_email,
            template_variables_in_json=template_variables_in_json,
            kind_of_email_template=kind_of_email_template)
        status += outbound_results['status'] + " "
        if outbound_results['email_outbound_description_saved']:
            email_outbound_description = outbound_results['email_outbound_description']
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
            status += schedule_results['status'] + " "
            if schedule_results['email_scheduled_saved']:
                # messages_to_send.append(schedule_results['email_scheduled_id'])
                email_scheduled = schedule_results['email_scheduled']
                send_results = email_manager.send_scheduled_email(email_scheduled)
                email_scheduled_sent = send_results['email_scheduled_sent']
                status += send_results['status']

    results = {
        'success':                              True,
        'status':                               status,
    }
    return results


def friend_invitation_by_email_send_for_api(voter_device_id,  # friendInvitationByEmailSend
                                            email_address_array, first_name_array, last_name_array,
                                            email_addresses_raw, invitation_message,
                                            sender_email_address, web_app_root_url=''):
    """

    :param voter_device_id:
    :param email_address_array:
    :param first_name_array:
    :param last_name_array:
    :param email_addresses_raw:
    :param invitation_message:
    :param sender_email_address:
    :param web_app_root_url:
    :return:
    """
    success = True
    status = ""
    error_message_to_show_voter = ""
    sender_voter_email_address_missing = True

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                               results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   sender_voter_email_address_missing,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    sender_voter_id = voter_results['voter_id']
    if not positive_value_exists(sender_voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                               status,
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   sender_voter_email_address_missing,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    sender_voter = voter_results['voter']
    email_manager = EmailManager()

    send_now = False
    valid_new_sender_email_address = False
    sender_email_with_ownership_verified = ""
    if sender_voter.has_email_with_verified_ownership():
        send_now = True
        sender_email_with_ownership_verified = \
            email_manager.fetch_primary_email_with_ownership_verified(sender_voter.we_vote_id)
        sender_voter_email_address_missing = False
        status += "SENDER_HAS_EMAIL_WITH_OWNERSHIP_VERIFIED "
    elif positive_value_exists(sender_email_address) and validate_email(sender_email_address):
        # If here, check to see if a sender_email_address was passed in
        status += "VALID_EMAIL_PASSED_INTO_THIS_FUNCTION "
        valid_new_sender_email_address = True
    else:
        sender_voter_email_address_missing = True
        status += "SENDER_EMAIL_NOT_PASSED_IN "

    sender_email_address_object = EmailAddress()
    if valid_new_sender_email_address:
        # If here then the sender has entered an email address in the "Email a Friend" form.
        # Is this email owned and verified by another voter? If so, then save the invitations with this
        # voter_id and send a verification email.
        # TODO If that email is verified we will want to send the invitations *then*
        # Does this email exist in the EmailAddress database for this voter?
        email_address_object_found = False
        results = email_manager.retrieve_email_address_object(sender_email_address, '', sender_voter.we_vote_id)
        if results['email_address_object_found']:
            sender_email_address_object = results['email_address_object']
            email_address_object_found = True
            sender_voter_email_address_missing = False
            status += "ONE_SENDER_EMAIL_FOUND "
        elif results['email_address_list_found']:
            # The case where there is more than one email entry for one voter shouldn't be possible, but if so,
            # just use the first one returned
            email_address_list = results['email_address_list']
            sender_email_address_object = email_address_list[0]
            email_address_object_found = True
            sender_voter_email_address_missing = False
            status += "SENDER_EMAIL_LIST_FOUND "
        else:
            # Create email address object
            email_results = email_manager.create_email_address_for_voter(sender_email_address, sender_voter)

            if email_results['email_address_object_saved']:
                # We recognize the email
                email_address_object_found = True
                sender_voter_email_address_missing = False
                sender_email_address_object = email_results['email_address_object']
                status += "SENDER_EMAIL_CREATED "
            else:
                sender_voter_email_address_missing = True
                valid_new_sender_email_address = False
                status += "SENDER_EMAIL_COULD_NOT_BE_CREATED "

        # double-check that we have email_address_object
        if not email_address_object_found:
            status += "FRIEND_INVITATION_BY_EMAIL_SEND-EMAIL_ADDRESS_OBJECT_SAVING_PROBLEM "
            error_results = {
                'success':                              False,
                'status':                               status,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   sender_voter_email_address_missing,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results

    if valid_new_sender_email_address:
        # Send verification email, and store the rest of the data without processing until sender_email is verified
        recipient_voter_we_vote_id = sender_voter.we_vote_id
        recipient_email_we_vote_id = sender_email_address_object.we_vote_id
        recipient_voter_email = sender_email_address_object.normalized_email_address
        if positive_value_exists(sender_email_address_object.secret_key):
            recipient_email_address_secret_key = sender_email_address_object.secret_key
        else:
            recipient_email_address_secret_key = \
                email_manager.update_email_address_with_new_secret_key(recipient_email_we_vote_id)
        send_now = False

        verifications_send_results = schedule_verification_email(sender_voter.we_vote_id, recipient_voter_we_vote_id,
                                                                 recipient_email_we_vote_id, recipient_voter_email,
                                                                 recipient_email_address_secret_key,
                                                                 web_app_root_url)
        status += verifications_send_results['status']
        email_scheduled_saved = verifications_send_results['email_scheduled_saved']
        email_scheduled_id = verifications_send_results['email_scheduled_id']

    if sender_voter.has_valid_email() or valid_new_sender_email_address:
        # We can continue. Note that we are not checking for "voter.has_email_with_verified_ownership()"
        pass
    else:
        status += "VOTER_DOES_NOT_HAVE_VALID_EMAIL-CACHING_FOR_LATER "

    if not isinstance(first_name_array, (list, tuple)):
        first_name_array = []

    if not isinstance(last_name_array, (list, tuple)):
        last_name_array = []

    if email_address_array:
        # Reconstruct dictionary array from lists
        for n in range(len(email_address_array)):
            first_name = first_name_array[n]
            last_name = last_name_array[n]
            one_normalized_raw_email = email_address_array[n]

            # Make sure the current voter isn't already friends with owner of this email address
            is_friend_results = retrieve_current_friend_by_email(
                viewing_voter=sender_voter, one_normalized_raw_email=one_normalized_raw_email)
            if is_friend_results['current_friend_found']:
                # Do not send an invitation
                status += is_friend_results['status']
                status += "ALREADY_FRIENDS_WITH_SENDER_VOTER_EMAIL_ADDRESS_ARRAY "
                error_message_to_show_voter += "You are already friends with the owner of " \
                                               "'{one_normalized_raw_email}'. " \
                                               "".format(one_normalized_raw_email=one_normalized_raw_email)
                continue

            send_results = send_to_one_friend(voter_device_id, sender_voter, send_now,
                                              sender_email_with_ownership_verified,
                                              one_normalized_raw_email, first_name, last_name, invitation_message,
                                              web_app_root_url)
            status += send_results['status']

    else:
        # Break apart all of the emails in email_addresses_raw input from the voter
        results = email_manager.parse_raw_emails_into_list(email_addresses_raw)
        if results['at_least_one_email_found']:
            raw_email_list_to_invite = results['email_list']
            first_name = ""
            last_name = ""
            for one_normalized_raw_email in raw_email_list_to_invite:
                # Make sure the current voter isn't already friends with owner of this email address
                is_friend_results = retrieve_current_friend_by_email(
                    viewing_voter=sender_voter, one_normalized_raw_email=one_normalized_raw_email)
                if is_friend_results['current_friend_found']:
                    # Do not send an invitation
                    status += is_friend_results['status']
                    status += "ALREADY_FRIENDS_WITH_SENDER_VOTER_RAW_EMAILS "
                    error_message_to_show_voter += "You are already friends with the owner of " \
                                                   "'{one_normalized_raw_email}'. " \
                                                   "".format(one_normalized_raw_email=one_normalized_raw_email)
                    continue

                send_results = send_to_one_friend(voter_device_id, sender_voter, send_now,
                                                  sender_email_with_ownership_verified,
                                                  one_normalized_raw_email, first_name, last_name, invitation_message,
                                                  web_app_root_url)
                status += send_results['status']
        else:
            error_message_to_show_voter = "Please enter the email address of at least one friend."
            status += "LIST_OF_EMAILS_NOT_RECEIVED " + results['status']
            error_results = {
                'status':                               status,
                'success':                              False,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   sender_voter_email_address_missing,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results

    # Now send any "WAITING_FOR_VERIFICATION" emails if the voter has since verified themselves
    # Are there any waiting?
    send_status = WAITING_FOR_VERIFICATION
    scheduled_email_results = email_manager.retrieve_scheduled_email_list_from_send_status(
        sender_voter.we_vote_id, send_status)
    if scheduled_email_results['scheduled_email_list_found']:
        is_organization = False
        organization_full_name = ""
        organization_manager = OrganizationManager()
        if positive_value_exists(sender_voter.linked_organization_we_vote_id):
            organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                sender_voter.linked_organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                if organization.is_organization():
                    is_organization = True
                    organization_full_name = organization.organization_name

        email_manager = EmailManager()
        real_name_only = True
        if is_organization:
            if positive_value_exists(organization_full_name) and 'Voter-' not in organization_full_name:
                # Only send if the organization name exists
                send_results = email_manager.send_scheduled_emails_waiting_for_verification(
                    sender_voter.we_vote_id, organization_full_name)
                status += send_results['status']
            else:
                status += "CANNOT_SEND_SCHEDULED_EMAILS_WITHOUT_ORGANIZATION_NAME-FRIEND_CONTROLLER "
        elif positive_value_exists(sender_voter.get_full_name(real_name_only)):
            # Only send if the sender's full name exists
            send_results = email_manager.send_scheduled_emails_waiting_for_verification(
                sender_voter.we_vote_id, sender_voter.get_full_name(real_name_only))
            status += send_results['status']
        else:
            status += "CANNOT_SEND_SCHEDULED_EMAILS_WITHOUT_NAME-FRIEND_CONTROLLER "
        # TODO Do similar send for SMS

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   sender_voter_email_address_missing,
        'error_message_to_show_voter':          error_message_to_show_voter
    }
    return results


def send_to_one_friend(voter_device_id, sender_voter, send_now, sender_email_with_ownership_verified,
                       one_normalized_raw_email, first_name, last_name, invitation_message,
                       web_app_root_url=''):
    # Starting with a raw email address, find (or create) the EmailAddress entry
    # and the owner (Voter) if exists
    status = ""
    real_name_only = True
    sender_name = sender_voter.get_full_name(real_name_only)
    sender_photo = sender_voter.voter_photo_url()
    sender_description = ""
    sender_network_details = ""
    email_manager = EmailManager()
    error_message_to_show_voter = ''
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

    retrieve_results = retrieve_voter_and_email_address(one_normalized_raw_email)
    if not retrieve_results['success']:
        error_message_to_show_voter = "There was an error retrieving one of your friend's email addresses. " \
                                      "Please try again."
        results = {
            'success':                              False,
            'status':                               retrieve_results['status'],
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   False,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return results
    status += retrieve_results['status'] + " "

    recipient_email_address_object = retrieve_results['email_address_object']

    # Store the friend invitation linked to voter (if the email address has had its ownership verified),
    # or to an email that isn't linked to a voter
    invitation_secret_key = ""
    if retrieve_results['voter_found']:
        # Store the friend invitation in FriendInvitationVoterLink table
        voter_friend = retrieve_results['voter']
        existing_first_name = ''
        existing_last_name = ''
        try:
            existing_first_name = voter_friend.first_name
            existing_last_name = voter_friend.last_name
            voter_friend_found = True
        except AttributeError:
            voter_friend_found = False
        # See if voter_friend has a first_name and last_name already stored. If not, add the names used by friend.
        if positive_value_exists(voter_friend_found) \
                and not positive_value_exists(existing_first_name) and not positive_value_exists(existing_last_name):
            # Save the voter_friend with new info
            voter_manager = VoterManager
            facebook_email = False
            facebook_profile_image_url_https = False
            middle_name = False
            update_voter_results = voter_manager.update_voter_by_object(
                    voter_friend, facebook_email, facebook_profile_image_url_https,
                    first_name, middle_name, last_name)
            if update_voter_results['voter_updated']:
                voter_friend = update_voter_results['voter']

        friend_invitation_results = store_internal_friend_invitation_with_two_voters(
            sender_voter, invitation_message, voter_friend)
        status += friend_invitation_results['status'] + " "
        success = friend_invitation_results['success']
        if friend_invitation_results['friend_invitation_saved']:
            friend_invitation = friend_invitation_results['friend_invitation']
            invitation_secret_key = friend_invitation.secret_key
        sender_voter_we_vote_id = sender_voter.we_vote_id
        recipient_voter_we_vote_id = voter_friend.we_vote_id
        recipient_email_we_vote_id = recipient_email_address_object.we_vote_id
        recipient_voter_email = recipient_email_address_object.normalized_email_address

        # Template variables
        real_name_only = True
        recipient_name = voter_friend.get_full_name(real_name_only)
    else:
        # Store the friend invitation in FriendInvitationEmailLink table
        friend_invitation_results = store_internal_friend_invitation_with_unknown_email(
            sender_voter, invitation_message, recipient_email_address_object, first_name, last_name)
        status += friend_invitation_results['status'] + " "
        success = friend_invitation_results['success']
        if friend_invitation_results['friend_invitation_saved']:
            friend_invitation = friend_invitation_results['friend_invitation']
            invitation_secret_key = friend_invitation.secret_key
        sender_voter_we_vote_id = sender_voter.we_vote_id
        recipient_voter_we_vote_id = ""
        recipient_email_we_vote_id = recipient_email_address_object.we_vote_id
        recipient_voter_email = recipient_email_address_object.normalized_email_address

        # Template variables
        recipient_name = ""

    # Variables used by templates/email_outbound/email_templates/friend_invitation.txt and .html
    if positive_value_exists(sender_name):
        subject = sender_name + " wants to be friends on We Vote"
    else:
        subject = "Invitation to be friends on We Vote"

    if positive_value_exists(sender_email_with_ownership_verified):
        sender_email_address = sender_email_with_ownership_verified
    else:
        sender_email_address = ""

    if invitation_secret_key is None:
        invitation_secret_key = ""

    template_variables_for_json = {
        "subject":                      subject,
        "invitation_message":           invitation_message,
        "sender_name":                  sender_name,
        "sender_photo":                 sender_photo,
        "sender_email_address":         sender_email_address,  # Does not affect the "From" email header
        "sender_description":           sender_description,
        "sender_network_details":       sender_network_details,
        "recipient_name":               recipient_name,
        "recipient_voter_email":        recipient_voter_email,
        "see_all_friend_requests_url":  web_app_root_url_verified + "/friends",
        "confirm_friend_request_url":   web_app_root_url_verified + "/more/network/key/" + invitation_secret_key,
        "recipient_unsubscribe_url":    web_app_root_url_verified + "/unsubscribe?email_key=1234",  # TODO Implement
        "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

    # TODO DALE - What kind of policy do we want re: sending a second email to a person?
    # Create the outbound email description, then schedule it
    if friend_invitation_results['friend_invitation_saved']:
        kind_of_email_template = FRIEND_INVITATION_TEMPLATE
        outbound_results = email_manager.create_email_outbound_description(
            sender_voter_we_vote_id=sender_voter_we_vote_id,
            sender_voter_email=sender_email_with_ownership_verified,
            sender_voter_name=sender_name,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            recipient_email_we_vote_id=recipient_email_we_vote_id,
            recipient_voter_email=recipient_voter_email,
            template_variables_in_json=template_variables_in_json,
            kind_of_email_template=kind_of_email_template)
        status += outbound_results['status'] + " "
        email_outbound_description = outbound_results['email_outbound_description']
        if outbound_results['email_outbound_description_saved'] and send_now:
            send_status = TO_BE_PROCESSED
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description, send_status)
            status += schedule_results['status'] + " "
            if schedule_results['email_scheduled_saved']:
                # messages_to_send.append(schedule_results['email_scheduled_id'])
                email_scheduled = schedule_results['email_scheduled']
                send_results = email_manager.send_scheduled_email(email_scheduled)
                email_scheduled_sent = send_results['email_scheduled_sent']
                status += send_results['status']
        elif not send_now:
            send_status = WAITING_FOR_VERIFICATION
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description, send_status)
            status += schedule_results['status'] + " "

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   False,
        'error_message_to_show_voter':          error_message_to_show_voter
    }
    return results


def friend_invitation_information_for_api(voter_device_id, invitation_secret_key):  # friendInvitationInformation
    """

    :param voter_device_id:
    :param invitation_secret_key:
    :return:
    """
    status = ""
    success = False
    sender_voter_we_vote_id = ''
    friend_first_name = ''
    friend_last_name = ''
    friend_image_url_https_tiny = ''
    friend_issue_we_vote_id_list = []
    friend_we_vote_id = ''
    friend_organization_we_vote_id = ''
    invitation_message = ''
    invitation_secret_key_belongs_to_this_voter = ''

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        status += "friendInvitationInformation-MISSING_VOTER_DEVICE_ID:"
        status += device_id_results['status']
        json_data = {
            'status':                   status,
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'friend_first_name':        '',
            'friend_last_name':         '',
            'friend_image_url_https_tiny': '',
            'friend_issue_we_vote_id_list': [],
            'friend_we_vote_id':        '',
            'friend_organization_we_vote_id':   '',
            'invitation_found':         False,
            'invitation_message':       '',
            'invitation_secret_key':    invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter': False,
        }
        return json_data

    if not positive_value_exists(invitation_secret_key):
        status += "friendInvitationInformation_MISSING_SECRET_KEY "
        error_results = {
            'status':                                       status,
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'friend_first_name':        '',
            'friend_last_name':         '',
            'friend_image_url_https_tiny': '',
            'friend_issue_we_vote_id_list': [],
            'friend_we_vote_id':        '',
            'friend_organization_we_vote_id':   '',
            'invitation_found':         False,
            'invitation_message':       '',
            'invitation_secret_key':                        invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter': False,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "friendInvitationInformation_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                                       status,
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'friend_first_name':        '',
            'friend_last_name':         '',
            'friend_image_url_https_tiny': '',
            'friend_issue_we_vote_id_list': [],
            'friend_we_vote_id':        '',
            'friend_organization_we_vote_id':   '',
            'invitation_found':         False,
            'invitation_message':       '',
            'invitation_secret_key':                        invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter': False,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    friend_manager = FriendManager()
    friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(
        invitation_secret_key, for_retrieving_information=True, read_only=True)
    if not friend_invitation_results['friend_invitation_found']:
        status += "INVITATION_NOT_FOUND_FROM_SECRET_KEY "
        error_results = {
            'status':                   status,
            'success':                  True,
            'voter_device_id':          voter_device_id,
            'friend_first_name':        '',
            'friend_last_name':         '',
            'friend_image_url_https_tiny': '',
            'friend_issue_we_vote_id_list': [],
            'friend_we_vote_id':        '',
            'friend_organization_we_vote_id':   '',
            'invitation_found':         False,
            'invitation_message':       '',
            'invitation_secret_key':    invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter': False,
        }
        return error_results

    # Now that we have the friend_invitation data, look more closely at it
    invitation_found = True
    if friend_invitation_results['friend_invitation_voter_link_found']:
        friend_invitation_voter_link = friend_invitation_results['friend_invitation_voter_link']
        status += "FRIEND_INVITATION_VOTER_LINK_FOUND "

        if friend_invitation_voter_link.sender_voter_we_vote_id == voter_we_vote_id:
            status += "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED-VOTER_LINK "
            error_results = {
                'status':                   status,
                'success':                  False,
                'voter_device_id':          voter_device_id,
                'friend_first_name':        '',
                'friend_last_name':         '',
                'friend_image_url_https_tiny': '',
                'friend_issue_we_vote_id_list': [],
                'friend_we_vote_id':        '',
                'friend_organization_we_vote_id': '',
                'invitation_found':         invitation_found,
                'invitation_message':       '',
                'invitation_secret_key':    invitation_secret_key,
                'invitation_secret_key_belongs_to_this_voter': False,
            }
            return error_results

        if friend_invitation_voter_link.recipient_voter_we_vote_id != voter_we_vote_id:
            status += "RECIPIENT_DOES_NOT_MATCH_CURRENT_VOTER-VOTER_LINK "
            error_results = {
                'status':                   status,
                'success':                  False,
                'voter_device_id':          voter_device_id,
                'friend_first_name':        '',
                'friend_last_name':         '',
                'friend_image_url_https_tiny': '',
                'friend_issue_we_vote_id_list': [],
                'friend_we_vote_id':        '',
                'friend_organization_we_vote_id': '',
                'invitation_found':         invitation_found,
                'invitation_message':       '',
                'invitation_secret_key':    invitation_secret_key,
                'invitation_secret_key_belongs_to_this_voter': False,
            }
            return error_results

        invitation_secret_key_belongs_to_this_voter = True
        sender_voter_we_vote_id = friend_invitation_voter_link.sender_voter_we_vote_id
        invitation_message = friend_invitation_voter_link.invitation_message
    elif friend_invitation_results['friend_invitation_email_link_found']:
        friend_invitation_email_link = friend_invitation_results['friend_invitation_email_link']
        status += "FRIEND_INVITATION_EMAIL_LINK_FOUND "

        if friend_invitation_email_link.sender_voter_we_vote_id == voter_we_vote_id:
            status += "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED-EMAIL_LINK "
            error_results = {
                'status': status,
                'success': False,
                'voter_device_id': voter_device_id,
                'friend_first_name': '',
                'friend_last_name': '',
                'friend_image_url_https_tiny': '',
                'friend_issue_we_vote_id_list': [],
                'friend_we_vote_id': '',
                'friend_organization_we_vote_id': '',
                'invitation_found': invitation_found,
                'invitation_message': '',
                'invitation_secret_key': invitation_secret_key,
                'invitation_secret_key_belongs_to_this_voter': False,
            }
            return error_results

    if positive_value_exists(sender_voter_we_vote_id):
        voter_results = voter_manager.retrieve_voter_by_we_vote_id(sender_voter_we_vote_id)
        if voter_results['voter_found']:
            friend_we_vote_id = sender_voter_we_vote_id
            voter = voter_results['voter']
            friend_first_name = voter.first_name
            friend_last_name = voter.last_name
            friend_image_url_https_tiny = voter.we_vote_hosted_profile_image_url_tiny
            friend_organization_we_vote_id = voter.linked_organization_we_vote_id

            follow_issue_list_manager = FollowIssueList()
            friend_issue_we_vote_id_list = \
                follow_issue_list_manager.retrieve_follow_issue_following_we_vote_id_list_by_voter_we_vote_id(
                    friend_we_vote_id)
            success = True
        else:
            status += "SENDER_VOTER_NOT_FOUND_WITH_VOTER_WE_VOTE_ID: " + sender_voter_we_vote_id + " "
    else:
        status += "MISSING_SENDER_VOTER_WE_VOTE_ID "

    json_data = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'friend_first_name':                friend_first_name,
        'friend_last_name':                 friend_last_name,
        'friend_image_url_https_tiny':      friend_image_url_https_tiny,
        'friend_issue_we_vote_id_list':     friend_issue_we_vote_id_list,
        'friend_we_vote_id':                friend_we_vote_id,
        'friend_organization_we_vote_id':   friend_organization_we_vote_id,
        'invitation_found':                 invitation_found,
        'invitation_message':               invitation_message,
        'invitation_secret_key':            invitation_secret_key,
        'invitation_secret_key_belongs_to_this_voter':  invitation_secret_key_belongs_to_this_voter,
    }
    return json_data


def friend_invitation_by_email_verify_for_api(  # friendInvitationByEmailVerify
        voter_device_id, invitation_secret_key, web_app_root_url=''):
    """

    :param voter_device_id:
    :param invitation_secret_key:
    :param web_app_root_url:
    :return:
    """
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        status += device_id_results['status']
        json_data = {
            'status':                                       status,
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
        }
        return json_data

    if not positive_value_exists(invitation_secret_key):
        status += "VOTER_EMAIL_ADDRESS_VERIFY_MISSING_SECRET_KEY "
        error_results = {
            'status':                                       status,
            'success':                                      True,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                                       status,
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_has_data_to_preserve = voter.has_data_to_preserve()

    friend_manager = FriendManager()
    friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(
        invitation_secret_key, for_accepting_friendship=True, read_only=False)
    if not friend_invitation_results['friend_invitation_found']:
        status += "INVITATION_NOT_FOUND_FROM_SECRET_KEY "
        error_results = {
            'status':                                       status,
            'success':                                      True,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
        }
        return error_results

    # Now that we have the friend_invitation data, look more closely at it
    invitation_found = True
    voter_we_vote_id_accepting_invitation = ""
    email_manager = EmailManager()
    if friend_invitation_results['friend_invitation_voter_link_found']:
        friend_invitation_voter_link = friend_invitation_results['friend_invitation_voter_link']

        if friend_invitation_voter_link.sender_voter_we_vote_id == voter_we_vote_id:
            status += "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED "
            error_results = {
                'status':                                       status,
                'success':                                      True,
                'voter_device_id':                              voter_device_id,
                'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
                'invitation_found':                             True,
                'attempted_to_approve_own_invitation':          True,
                'invitation_secret_key':                        invitation_secret_key,
            }
            return error_results

        voter_we_vote_id_accepting_invitation = friend_invitation_voter_link.recipient_voter_we_vote_id
        # Now we want to make sure we have a current_friend entry
        recipient_organization_we_vote_id = ''
        voter_results = voter_manager.retrieve_voter_by_we_vote_id(
            friend_invitation_voter_link.recipient_voter_we_vote_id)
        if voter_results['voter_found']:
            recipient_organization_we_vote_id = voter_results['voter'].linked_organization_we_vote_id
        friend_results = friend_manager.update_or_create_current_friend(
            friend_invitation_voter_link.sender_voter_we_vote_id,
            friend_invitation_voter_link.recipient_voter_we_vote_id,
            voter.linked_organization_we_vote_id,
            recipient_organization_we_vote_id
        )

        friend_manager.update_suggested_friends_starting_with_one_voter(
            friend_invitation_voter_link.sender_voter_we_vote_id)
        friend_manager.update_suggested_friends_starting_with_one_voter(
            friend_invitation_voter_link.recipient_voter_we_vote_id)

        accepting_voter_we_vote_id = voter_we_vote_id_accepting_invitation
        original_sender_we_vote_id = friend_invitation_voter_link.sender_voter_we_vote_id
        results = friend_accepted_invitation_send(accepting_voter_we_vote_id, original_sender_we_vote_id,
                                                  web_app_root_url=web_app_root_url)

        # Update the PositionNetworkCount entries for both friends
        add_position_network_count_entries_for_one_friend(
            0, accepting_voter_we_vote_id, voter_we_vote_id=original_sender_we_vote_id)
        add_position_network_count_entries_for_one_friend(
            0, original_sender_we_vote_id, voter_we_vote_id=accepting_voter_we_vote_id)

        # Now that a CurrentFriend entry exists, update the FriendInvitation...
        if friend_results['success']:
            try:
                friend_invitation_voter_link.invitation_status = ACCEPTED
                friend_invitation_voter_link.save()
            except Exception as e:
                success = False
                status += 'FAILED_TO_UPDATE_INVITATION_STATUS1 ' + str(e) + ' '
        else:
            success = False
            status += "friend_invitation_voter_link_found CREATE_OR_UPDATE_CURRENT_FRIEND_FAILED "

        # We don't need to do anything with the email because this was an invitation to a known voter
    elif friend_invitation_results['friend_invitation_email_link_found']:
        friend_invitation_email_link = friend_invitation_results['friend_invitation_email_link']
        if friend_invitation_email_link.sender_voter_we_vote_id == voter_we_vote_id:
            status += "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED "
            error_results = {
                'status':                                       status,
                'success':                                      False,
                'voter_device_id':                              voter_device_id,
                'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
                'invitation_found':                             True,
                'attempted_to_approve_own_invitation':          True,
                'invitation_secret_key':                        invitation_secret_key,
            }
            return error_results

        this_voter_has_first_or_last_name_saved = voter_manager.this_voter_has_first_or_last_name_saved(voter)
        if positive_value_exists(friend_invitation_email_link.recipient_first_name) or \
                positive_value_exists(friend_invitation_email_link.recipient_last_name):
            we_have_first_or_last_name_from_friend_invitation_email_link = True
        else:
            we_have_first_or_last_name_from_friend_invitation_email_link = False

        # Check to see if the email used has been claimed by a voter account yet
        temp_voter_we_vote_id = ""
        update_voter_name = False
        email_results = email_manager.retrieve_primary_email_with_ownership_verified(
            temp_voter_we_vote_id, friend_invitation_email_link.recipient_voter_email)
        if email_results['email_address_object_found']:
            # The email belongs to this or another voter
            email_address_object = email_results['email_address_object']
            voter_we_vote_id_accepting_invitation = email_address_object.voter_we_vote_id

            # We might need to heal the data in the voter record
            if voter_we_vote_id_accepting_invitation != voter_we_vote_id:
                email_owner_results = voter_manager.retrieve_voter_by_we_vote_id(email_address_object.voter_we_vote_id)
                if email_owner_results['voter_found']:
                    email_owner_voter = email_owner_results['voter']
                    voter_manager.update_voter_email_ownership_verified(email_owner_voter, email_address_object)
            else:
                # If we are here, then the email_address_object doesn't belong to another voter and can be
                #  claimed by this current voter.
                voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
                if we_have_first_or_last_name_from_friend_invitation_email_link and \
                        not this_voter_has_first_or_last_name_saved:
                    # The current voter does not have first or last name, and we have incoming names to apply
                    update_voter_name = True

        else:
            voter_we_vote_id_accepting_invitation = voter_we_vote_id
            # If we are here, we know the email is unclaimed. We can assign it to the current voter.
            # Is there an email address entry for this voter/email?
            email_we_vote_id = ''
            email_results = email_manager.retrieve_email_address_object(
                friend_invitation_email_link.recipient_voter_email, email_we_vote_id,
                voter_we_vote_id)
            if email_results['email_address_object_found']:
                email_address_object = email_results['email_address_object']
                try:
                    email_address_object.email_ownership_is_verified = True
                    email_address_object.secret_key = generate_random_string(12)  # Reset the secret_key
                    email_address_object.save()
                    voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
                    if we_have_first_or_last_name_from_friend_invitation_email_link and \
                            not this_voter_has_first_or_last_name_saved:
                        # The current voter does not have first or last name, and we have incoming names to apply
                        update_voter_name = True
                except Exception as e:
                    success = False
                    status += 'FAILED_TO_UPDATE_UNVERIFIED_EMAIL ' + str(e) + ' '
            else:
                email_ownership_is_verified = True
                email_create_results = email_manager.create_email_address_for_voter(
                    friend_invitation_email_link.recipient_voter_email, voter, email_ownership_is_verified)
                if email_create_results['email_address_object_saved']:
                    email_address_object = email_create_results['email_address_object']
                    voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
                    if we_have_first_or_last_name_from_friend_invitation_email_link and \
                            not this_voter_has_first_or_last_name_saved:
                        # The current voter does not have first or last name, and we have incoming names to apply
                        update_voter_name = True

        # The current voter does not have first or last name, and we have incoming names that can be used
        if update_voter_name:
            results = voter_manager.update_voter_name_by_object(
                voter, friend_invitation_email_link.recipient_first_name,
                friend_invitation_email_link.recipient_last_name)
            if results['voter_updated']:
                voter = results['voter']

        # Now that we know who owns the recipient_email_address, update invitation status
        sender_organization_we_vote_id = ''
        voter_results = voter_manager.retrieve_voter_by_we_vote_id(
            friend_invitation_email_link.sender_voter_we_vote_id)
        if voter_results['voter_found']:
            sender_organization_we_vote_id = voter_results['voter'].linked_organization_we_vote_id
        friend_results = friend_manager.update_or_create_current_friend(
            friend_invitation_email_link.sender_voter_we_vote_id,
            voter_we_vote_id_accepting_invitation,
            sender_organization_we_vote_id,
            voter.linked_organization_we_vote_id
        )

        friend_manager.update_suggested_friends_starting_with_one_voter(
            friend_invitation_email_link.sender_voter_we_vote_id)
        friend_manager.update_suggested_friends_starting_with_one_voter(voter_we_vote_id_accepting_invitation)

        accepting_voter_we_vote_id = voter_we_vote_id_accepting_invitation
        original_sender_we_vote_id = friend_invitation_email_link.sender_voter_we_vote_id
        friend_accepted_invitation_send(accepting_voter_we_vote_id, original_sender_we_vote_id,
                                        web_app_root_url=web_app_root_url)

        # Update the PositionNetworkCount entries for both friends
        add_position_network_count_entries_for_one_friend(
            0, accepting_voter_we_vote_id, voter_we_vote_id=original_sender_we_vote_id)
        add_position_network_count_entries_for_one_friend(
            0, original_sender_we_vote_id, voter_we_vote_id=accepting_voter_we_vote_id)

        if friend_results['success']:
            try:
                friend_invitation_email_link.invitation_status = ACCEPTED
                friend_invitation_email_link.save()
                success = True
                status += ' friend_invitation_email_link_found FRIENDSHIP_CREATED '
            except Exception as e:
                success = False
                status += 'FAILED_TO_UPDATE_INVITATION_STATUS2 ' + str(e) + ' '
        else:
            success = False
            status += "friend_invitation_email_link_found CREATE_OR_UPDATE_CURRENT_FRIEND_FAILED "

        # And finally, create an organization for this brand new signed-in voter so they can create public opinions
        organization_name = voter.get_full_name()
        organization_website = ""
        organization_twitter_handle = ""
        organization_twitter_id = ""
        organization_email = ""
        organization_facebook = ""
        organization_image = voter.voter_photo_url()
        organization_type = INDIVIDUAL
        organization_manager = OrganizationManager()
        create_results = organization_manager.create_organization(
            organization_name, organization_website, organization_twitter_handle,
            organization_email, organization_facebook, organization_image, organization_twitter_id, organization_type)
        if create_results['organization_created']:
            # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
            organization = create_results['organization']
            try:
                voter.linked_organization_we_vote_id = organization.we_vote_id
                voter.save()
                status += "VOTER_AND_ORGANIZATION_CREATED_FROM_FRIEND_INVITATION "
            except Exception as e:
                status += "UNABLE_CREATE_AND_LINK_VOTER_FROM_FRIEND_INVITATION " + str(e) + ' '

    json_data = {
        'status':                                       status,
        'success':                                      success,
        'voter_device_id':                              voter_device_id,
        'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
        'invitation_found':                             invitation_found,
        'attempted_to_approve_own_invitation':          False,
        'invitation_secret_key':                        invitation_secret_key,
    }
    return json_data


def friend_invitation_by_facebook_send_for_api(voter_device_id, recipients_facebook_id_array,
                                               recipients_facebook_name_array, facebook_request_id):
    # friendInvitationByFacebookSend
    """
    :param voter_device_id:
    :param recipients_facebook_id_array:
    :param recipients_facebook_name_array:
    :param facebook_request_id:
    :return:
    """
    success = False
    status = ""
    friends_facebook_detail_array = []
    all_friends_facebook_link_created_results = []

    if recipients_facebook_id_array:
        # reconstruct dictionary array from lists
        for n in range(len(recipients_facebook_id_array)):
            one_friend_facebook_id_dict = {'recipient_facebook_name': recipients_facebook_name_array[n],
                                           'recipient_facebook_id': recipients_facebook_id_array[n]}
            friends_facebook_detail_array.append(one_friend_facebook_id_dict)

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                                       results['status'],
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'all_friends_facebook_link_created_results':    all_friends_facebook_link_created_results
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    sender_voter_id = voter_results['voter_id']
    if not positive_value_exists(sender_voter_id):
        error_results = {
            'status':                                       "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'all_friends_facebook_link_created_results':    all_friends_facebook_link_created_results
        }
        return error_results

    sender_voter = voter_results['voter']
    sender_voter_we_vote_id = sender_voter.we_vote_id
    facebook_manager = FacebookManager()
    friend_manager = FriendManager()

    facebook_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        sender_voter_we_vote_id)
    if not facebook_link_to_voter_results['facebook_link_to_voter_found']:
        status += "FRIEND_INVITATION_BY_FACEBOOK-FACEBOOK_LINK_TO_VOTER_NOT_FOUND "
        error_results = {
            'status':                                       status,
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'all_friends_facebook_link_created_results':    all_friends_facebook_link_created_results
        }
        return error_results

    facebook_link_to_voter = facebook_link_to_voter_results['facebook_link_to_voter']
    sender_facebook_id = facebook_link_to_voter.facebook_user_id
    for friend_facebook_detail in friends_facebook_detail_array:
        recipient_facebook_id = friend_facebook_detail["recipient_facebook_id"]
        recipient_facebook_name = friend_facebook_detail["recipient_facebook_name"]
        create_results = friend_manager.update_or_create_friend_invitation_facebook_link(
            facebook_request_id, sender_facebook_id, recipient_facebook_id, recipient_facebook_name)
        results = {
            'success': create_results['success'],
            'status': create_results['status'],
            'recipient_facebook_name': recipient_facebook_name,
            'friend_invitation_saved': create_results['friend_invitation_saved'],
            # 'friend_invitation': create_results['friend_invitation'],
        }
        all_friends_facebook_link_created_results.append(results)
    status += "FRIEND_INVITATION_BY_FACEBOOK_SEND_COMPLETED "

    results = {
        'status':                                       status,
        'success':                                      True,
        'voter_device_id':                              voter_device_id,
        'all_friends_facebook_link_created_results':    all_friends_facebook_link_created_results
    }
    return results


def friend_invitation_by_facebook_verify_for_api(voter_device_id, facebook_request_id, recipient_facebook_id,
                                                 sender_facebook_id):  # friendInvitationByFacebookVerify
    """

    :param voter_device_id:
    :param facebook_request_id:
    :param recipient_facebook_id:
    :param sender_facebook_id:
    :return:
    """
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                                       device_id_results['status'],
            'success':                                      False,
            'attempted_to_approve_own_invitation':          False,
            'facebook_request_id':                          facebook_request_id,
            'invitation_found':                             False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
        }
        return json_data

    if not positive_value_exists(facebook_request_id):
        error_results = {
            'status':                                       "MISSING_FACEBOOK_REQUEST_ID",
            'success':                                      False,
            'attempted_to_approve_own_invitation':          False,
            'facebook_request_id':                          facebook_request_id,
            'invitation_found':                             False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                                       "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                                      False,
            'attempted_to_approve_own_invitation':          False,
            'facebook_request_id':                          facebook_request_id,
            'invitation_found':                             False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id_accepting_invitation = voter.we_vote_id
    voter_has_data_to_preserve = voter.has_data_to_preserve()

    friend_manager = FriendManager()
    facebook_manager = FacebookManager()

    # Retrieve sender voter we vote id
    facebook_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter(sender_facebook_id)
    if not facebook_link_to_voter_results['facebook_link_to_voter_found']:
        error_results = {
            'status':                                       "FACEBOOK_LINK_TO_SENDER_NOT_FOUND",
            'success':                                      False,
            'attempted_to_approve_own_invitation':          False,
            'facebook_request_id':                          facebook_request_id,
            'invitation_found':                             False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
        }
        return error_results

    facebook_link_to_voter = facebook_link_to_voter_results['facebook_link_to_voter']
    sender_voter_we_vote_id = facebook_link_to_voter.voter_we_vote_id

    friend_invitation_results = friend_manager.retrieve_friend_invitation_from_facebook(
        facebook_request_id.split('_')[0], recipient_facebook_id, sender_facebook_id)
    if not friend_invitation_results['friend_invitation_facebook_link_found']:
        error_results = {
            'status':                                       "INVITATION_NOT_FOUND_FROM_FACEBOOK",
            'success':                                      False,
            'attempted_to_approve_own_invitation':          False,
            'facebook_request_id':                          facebook_request_id,
            'invitation_found':                             False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
        }
        return error_results

    # Now that we have the friend_invitation data, look more closely at it
    invitation_found = True
    friend_invitation_facebook_link = friend_invitation_results['friend_invitation_facebook_link']

    if sender_voter_we_vote_id == voter_we_vote_id_accepting_invitation:
        error_results = {
            'status':                                       "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED",
            'success':                                      False,
            'attempted_to_approve_own_invitation':          True,
            'facebook_request_id':                          facebook_request_id,
            'invitation_found':                             True,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
        }
        return error_results

    # Now we want to make sure we have a current_friend entry
    sender_organization_we_vote_id = ''
    voter_results = voter_manager.retrieve_voter_by_we_vote_id(
        sender_voter_we_vote_id)
    if voter_results['voter_found']:
        sender_organization_we_vote_id = voter_results['voter'].linked_organization_we_vote_id
    friend_results = friend_manager.update_or_create_current_friend(
        sender_voter_we_vote_id,
        voter_we_vote_id_accepting_invitation,
        sender_organization_we_vote_id,
        voter.linked_organization_we_vote_id,
    )

    friend_manager.update_suggested_friends_starting_with_one_voter(sender_voter_we_vote_id)
    friend_manager.update_suggested_friends_starting_with_one_voter(voter_we_vote_id_accepting_invitation)

    # Update the PositionNetworkCount entries for both friends
    add_position_network_count_entries_for_one_friend(
        0, voter_we_vote_id_accepting_invitation, voter_we_vote_id=sender_voter_we_vote_id)
    add_position_network_count_entries_for_one_friend(
        0, sender_voter_we_vote_id, voter_we_vote_id=voter_we_vote_id_accepting_invitation)

    if friend_results['success']:
        try:
            friend_invitation_facebook_link.invitation_status = ACCEPTED
            friend_invitation_facebook_link.deleted = True
            # Facebook doesn't use secret key
            friend_invitation_facebook_link.save()
            success = True
            status += "INVITATION_FROM_FACEBOOK_UPDATED "
        except Exception as e:
            success = False
            status += 'FAILED_TO_UPDATE_INVITATION_STATUS1 ' + str(e) + ' '
    else:
        success = False
        status += " friend_invitation_facebook_link_found CREATE_OR_UPDATE_CURRENT_FRIEND_FAILED "

    json_data = {
        'status':                                       status,
        'success':                                      success,
        'attempted_to_approve_own_invitation':          False,
        'facebook_request_id':                          facebook_request_id,
        'invitation_found':                             invitation_found,
        'voter_device_id':                              voter_device_id,
        'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
    }
    return json_data


def friend_invitation_by_we_vote_id_send_for_api(voter_device_id, other_voter_we_vote_id, invitation_message,
                                                 web_app_root_url=''):  # friendInvitationByWeVoteIdSend
    """

    :param voter_device_id:
    :param other_voter_we_vote_id:
    :param invitation_message:
    :param web_app_root_url:
    :return:
    """
    status = ""
    error_message_to_show_voter = ""
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                               results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)

    if not voter_results['voter_found']:
        error_results = {
            'status':                               "OTHER_VOTER_NOT_FOUND_FOR_FRIEND_INVITATION",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    other_voter_found = False
    recipient_voter = Voter()
    if positive_value_exists(other_voter_we_vote_id):
        other_voter_we_vote_id_found = True
        recipient_voter_results = voter_manager.retrieve_voter_by_we_vote_id(other_voter_we_vote_id)
        if recipient_voter_results['voter_found']:
            recipient_voter = recipient_voter_results['voter']
            other_voter_found = True
    else:
        other_voter_we_vote_id_found = False

    if not other_voter_we_vote_id_found or not other_voter_found:
        error_results = {
            'status':                               "OTHER_VOTER_NOT_FOUND_FROM_INCOMING_WE_VOTE_ID",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    sender_voter = voter_results['voter']
    email_manager = EmailManager()
    friend_manager = FriendManager()

    if sender_voter.has_email_with_verified_ownership():
        send_now = True
        sender_email_with_ownership_verified = \
            email_manager.fetch_primary_email_with_ownership_verified(sender_voter.we_vote_id)
    else:
        error_results = {
            'status':                               "VOTER_SENDER_DOES_NOT_HAVE_VALID_EMAIL",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    # Store the friend invitation in FriendInvitationVoterLink table
    friend_invitation_saved = False
    friend_invitation_results = store_internal_friend_invitation_with_two_voters(
        sender_voter, invitation_message, recipient_voter)
    status += friend_invitation_results['status'] + " "
    success = friend_invitation_results['success']
    invitation_secret_key = ""
    if friend_invitation_results['friend_invitation_saved']:
        friend_invitation_saved = True
        friend_invitation = friend_invitation_results['friend_invitation']
        invitation_secret_key = friend_invitation.secret_key

    if recipient_voter.has_email_with_verified_ownership() and positive_value_exists(invitation_secret_key):
        results = email_manager.retrieve_primary_email_with_ownership_verified(other_voter_we_vote_id)
        if results['email_address_object_found']:
            recipient_email_address_object = results['email_address_object']

            sender_voter_we_vote_id = sender_voter.we_vote_id
            recipient_voter_we_vote_id = recipient_voter.we_vote_id
            recipient_email_we_vote_id = recipient_email_address_object.we_vote_id
            recipient_voter_email = recipient_email_address_object.normalized_email_address

            # Template variables
            real_name_only = True
            recipient_name = recipient_voter.get_full_name(real_name_only)

            real_name_only = True
            sender_name = sender_voter.get_full_name(real_name_only)
            sender_photo = sender_voter.voter_photo_url()
            sender_description = ""
            sender_network_details = ""

            # Variables used by templates/email_outbound/email_templates/friend_invitation.txt and .html
            if positive_value_exists(sender_name):
                subject = sender_name + " wants to be friends on We Vote"
            else:
                subject = "Invitation to be friends on We Vote"

            if positive_value_exists(sender_email_with_ownership_verified):
                sender_email_address = sender_email_with_ownership_verified
            else:
                sender_email_address = ""

            if invitation_secret_key is None:
                invitation_secret_key = ""

            template_variables_for_json = {
                "subject":                      subject,
                "invitation_message":           invitation_message,
                "sender_name":                  sender_name,
                "sender_photo":                 sender_photo,
                "sender_email_address":         sender_email_address,  # Does not affect the "From" email header
                "sender_description":           sender_description,
                "sender_network_details":       sender_network_details,
                "recipient_name":               recipient_name,
                "recipient_voter_email":        recipient_voter_email,
                "see_all_friend_requests_url":  web_app_root_url_verified + "/friends",
                "confirm_friend_request_url":   web_app_root_url_verified + "/more/network/key/" + invitation_secret_key,
                "recipient_unsubscribe_url":    web_app_root_url_verified + "/unsubscribe?email_key=1234",
                "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
            }
            template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

            # TODO DALE - What kind of policy do we want re: sending a second email to a person?
            # Create the outbound email description, then schedule it
            if friend_invitation_results['friend_invitation_saved'] and send_now:
                kind_of_email_template = FRIEND_INVITATION_TEMPLATE
                outbound_results = email_manager.create_email_outbound_description(
                    sender_voter_we_vote_id=sender_voter_we_vote_id,
                    sender_voter_email=sender_email_with_ownership_verified,
                    sender_voter_name=sender_name,
                    recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                    recipient_email_we_vote_id=recipient_email_we_vote_id,
                    recipient_voter_email=recipient_voter_email,
                    template_variables_in_json=template_variables_in_json,
                    kind_of_email_template=kind_of_email_template)
                status += outbound_results['status'] + " "
                if outbound_results['email_outbound_description_saved']:
                    email_outbound_description = outbound_results['email_outbound_description']
                    schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
                    status += schedule_results['status'] + " "
                    if schedule_results['email_scheduled_saved']:
                        # messages_to_send.append(schedule_results['email_scheduled_id'])
                        email_scheduled = schedule_results['email_scheduled']
                        send_results = email_manager.send_scheduled_email(email_scheduled)
                        email_scheduled_sent = send_results['email_scheduled_sent']
                        status += send_results['status']

    if friend_invitation_saved:
        # Update the SuggestedFriend entry to show that an invitation was sent
        defaults = {
            'friend_invite_sent': True,
        }
        suggested_results = friend_manager.update_suggested_friend(
            voter_we_vote_id=sender_voter.we_vote_id, other_voter_we_vote_id=other_voter_we_vote_id, defaults=defaults)
        status += suggested_results['status']

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   False,
        'error_message_to_show_voter':          error_message_to_show_voter
    }
    return results


def friend_invite_response_for_api(  # friendInviteResponse
        voter_device_id, kind_of_invite_response, other_voter_we_vote_id,
        recipient_voter_email='', web_app_root_url=''):
    """
    friendInviteResponse
    :param voter_device_id:
    :param kind_of_invite_response:
    :param other_voter_we_vote_id:
    :param recipient_voter_email:
    :param web_app_root_url:
    :return:
    """
    status = ""
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                               results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += voter_results['status']
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                               status,
            'success':                              False,
            'voter_device_id':                      voter_device_id,
        }
        return error_results
    voter = voter_results['voter']

    if kind_of_invite_response != DELETE_INVITATION_EMAIL_SENT_BY_ME:
        other_voter_results = voter_manager.retrieve_voter_by_we_vote_id(other_voter_we_vote_id)
        other_voter_id = other_voter_results['voter_id']
        status += other_voter_results['status']
        if not positive_value_exists(other_voter_id):
            status += "VOTER_NOT_FOUND_FROM_OTHER_VOTER_WE_VOTE_ID "
            error_results = {
                'status':                               status,
                'success':                              False,
                'voter_device_id':                      voter_device_id,
            }
            return error_results
        other_voter = other_voter_results['voter']
    else:
        other_voter = Voter()

    friend_manager = FriendManager()
    friend_invitation_accepted = False
    if kind_of_invite_response == UNFRIEND_CURRENT_FRIEND:
        results = friend_manager.unfriend_current_friend(voter.we_vote_id, other_voter.we_vote_id)
        status += results['status']
    elif kind_of_invite_response == DELETE_INVITATION_EMAIL_SENT_BY_ME:
        results = friend_manager.process_friend_invitation_email_response(
            sender_voter=voter, recipient_voter_email=recipient_voter_email,
            kind_of_invite_response=kind_of_invite_response)
        status += results['status']
    elif kind_of_invite_response == DELETE_INVITATION_VOTER_SENT_BY_ME:
        results = friend_manager.process_friend_invitation_voter_response(
            sender_voter=voter, recipient_voter=other_voter, kind_of_invite_response=kind_of_invite_response)
        status += results['status']
    elif kind_of_invite_response == IGNORE_SUGGESTION:
        # Update the SuggestedFriend entry to show that the acting_voter_we_vote_id
        # doesn't want to see this person as a SuggestedFriend
        defaults = {
            'voter_we_vote_id_deleted': voter.we_vote_id,
        }
        suggested_results = friend_manager.update_suggested_friend(
            voter_we_vote_id=voter.we_vote_id, other_voter_we_vote_id=other_voter.we_vote_id,
            defaults=defaults)
        status += suggested_results['status']
    else:
        # Conditions where we want the recipient_voter to be the voter viewing the page
        # IGNORE_INVITATION
        results = friend_manager.process_friend_invitation_voter_response(
            sender_voter=other_voter, recipient_voter=voter, kind_of_invite_response=kind_of_invite_response)
        status += results['status']
        if results['friend_invitation_accepted']:
            friend_invitation_accepted = True

    if friend_invitation_accepted:
        accepting_voter_id = voter.id
        accepting_voter_we_vote_id = voter.we_vote_id
        original_sender_id = other_voter.id
        original_sender_we_vote_id = other_voter.we_vote_id
        friend_accepted_invitation_send(accepting_voter_we_vote_id, original_sender_we_vote_id,
                                        web_app_root_url=web_app_root_url)
        # Update both friends
        results1 = add_position_network_count_entries_for_one_friend(accepting_voter_id, original_sender_we_vote_id)
        status += results1['status']
        results2 = add_position_network_count_entries_for_one_friend(original_sender_id, accepting_voter_we_vote_id)
        status += results2['status']

    success = results['success']

    results = {
        'success':              success,
        'status':               status,
        'voter_device_id':      voter_device_id,
    }
    return results


def friend_list_for_api(voter_device_id,  # friendList
                        kind_of_list_we_are_looking_for=CURRENT_FRIENDS,
                        state_code=''):
    """
    friendList API Endpoint
    :param voter_device_id:
    :param kind_of_list_we_are_looking_for:
    :param state_code:
    :return:
    """
    status = ""
    success = False
    friend_list = []

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':               results['status'],
            'success':              False,
            'voter_device_id':      voter_device_id,
            'state_code':           state_code,
            'kind_of_list':         kind_of_list_we_are_looking_for,
            'friend_list_found':    False,
            'friend_list':          friend_list,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':               "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'state_code':           state_code,
            'kind_of_list':         kind_of_list_we_are_looking_for,
            'friend_list_found':    False,
            'friend_list':          friend_list,
        }
        return error_results
    voter = voter_results['voter']

    # if kind_of_list in (
    # CURRENT_FRIENDS, FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_SENT_BY_ME, FRIENDS_IN_COMMON,
    # IGNORED_FRIEND_INVITATIONS, SUGGESTED_FRIEND_LIST):
    friend_manager = FriendManager()
    position_metrics_manager = PositionMetricsManager()
    if kind_of_list_we_are_looking_for == CURRENT_FRIENDS:
        status += "KIND_OF_LIST-CURRENT_FRIENDS "
        retrieve_current_friends_as_voters_results = friend_manager.retrieve_current_friends_as_voters(voter.we_vote_id)
        success = retrieve_current_friends_as_voters_results['success']
        status += retrieve_current_friends_as_voters_results['status']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friend_list = retrieve_current_friends_as_voters_results['friend_list']
            for friend_voter in current_friend_list:
                if not positive_value_exists(friend_voter.linked_organization_we_vote_id):
                    # We need to retrieve another voter object that can be saved
                    organization_manager = OrganizationManager()
                    voter_results = voter_manager.retrieve_voter_by_we_vote_id(friend_voter.we_vote_id, read_only=False)
                    if voter_results['voter_found']:
                        friend_voter = voter_results['voter']
                        heal_results = \
                            organization_manager.heal_voter_missing_linked_organization_we_vote_id(friend_voter)
                        if heal_results['voter_healed']:
                            status += "FRIEND_HEALED-MISSING_LINKED_ORGANIZATION_WE_VOTE_ID: " \
                                      "" + friend_voter.we_vote_id + " "
                            friend_voter = heal_results['voter']
                            # Now we need to make sure the friend entry gets updated
                            friend_results = friend_manager.retrieve_current_friend(
                                voter.we_vote_id, friend_voter.we_vote_id, read_only=False)
                            if friend_results['current_friend_found']:
                                status += "HEAL_CURRENT_FRIEND-FOUND "
                                current_friend = friend_results['current_friend']
                                heal_current_friend(current_friend)
                            else:
                                status += "COULD_NOT_RETRIEVE_CURRENT_FRIEND_FOR_HEALING "
                        else:
                            status += "VOTER_COULD_NOT_BE_HEALED " + heal_results['status']
                    else:
                        status += "COULD_NOT_RETRIEVE_VOTER_THAT_CAN_BE_SAVED " + voter_results['status']
                mutual_friends = friend_manager.fetch_mutual_friends_count(voter.we_vote_id, friend_voter.we_vote_id)
                positions_taken = position_metrics_manager.fetch_positions_count_for_this_voter(friend_voter)
                one_friend = {
                    "voter_we_vote_id":                 friend_voter.we_vote_id,
                    "voter_display_name":               friend_voter.get_full_name(),
                    "voter_photo_url_large":            friend_voter.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(friend_voter.we_vote_hosted_profile_image_url_large)
                    else friend_voter.voter_photo_url(),
                    'voter_photo_url_medium':           friend_voter.we_vote_hosted_profile_image_url_medium,
                    'voter_photo_url_tiny':             friend_voter.we_vote_hosted_profile_image_url_tiny,
                    "voter_email_address":              friend_voter.email,
                    "voter_twitter_handle":             friend_voter.twitter_screen_name,
                    "voter_twitter_description":        "",  # To be implemented
                    "voter_twitter_followers_count":    0,  # To be implemented
                    "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                    "voter_state_code":                 "",  # To be implemented
                    "invitation_status":                "",  # Not used with CurrentFriends
                    "invitation_sent_to":               "",  # Not used with CurrentFriends
                    "mutual_friends":                   mutual_friends,
                    "positions_taken":                  positions_taken,
                }
                friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_PROCESSED:
        status += "KIND_OF_LIST-FRIEND_INVITATIONS_PROCESSED "
        retrieve_invitations_processed_results = friend_manager.retrieve_friend_invitations_processed(
            voter.we_vote_id)
        success = retrieve_invitations_processed_results['success']
        status += retrieve_invitations_processed_results['status']
        if retrieve_invitations_processed_results['friend_list_found']:
            raw_friend_list = retrieve_invitations_processed_results['friend_list']
            for one_friend_invitation in raw_friend_list:
                # Augment the line with voter information
                friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    one_friend_invitation.sender_voter_we_vote_id)  # This is the voter who sent the invitation to me
                if friend_voter_results['voter_found']:
                    friend_voter = friend_voter_results['voter']
                    recipient_voter_email = one_friend_invitation.recipient_voter_email \
                        if hasattr(one_friend_invitation, "recipient_voter_email") \
                        else ""
                    mutual_friends = friend_manager.fetch_mutual_friends_count(
                        voter.we_vote_id, friend_voter.we_vote_id)
                    positions_taken = position_metrics_manager.fetch_positions_count_for_this_voter(friend_voter)
                    one_friend = {
                        "voter_we_vote_id":                 friend_voter.we_vote_id,
                        "voter_display_name":               friend_voter.get_full_name(),
                        "voter_photo_url_large":            friend_voter.we_vote_hosted_profile_image_url_large
                            if positive_value_exists(friend_voter.we_vote_hosted_profile_image_url_large)
                            else friend_voter.voter_photo_url(),
                        'voter_photo_url_medium':           friend_voter.we_vote_hosted_profile_image_url_medium,
                        'voter_photo_url_tiny':             friend_voter.we_vote_hosted_profile_image_url_tiny,
                        "voter_email_address":              friend_voter.email,
                        "voter_twitter_handle":             friend_voter.twitter_screen_name,
                        "voter_twitter_description":        "",  # To be implemented
                        "voter_twitter_followers_count":    0,  # To be implemented
                        "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                        "voter_state_code":                 "",  # To be implemented
                        "invitation_status":                one_friend_invitation.invitation_status,
                        "invitation_sent_to":               recipient_voter_email,
                        "mutual_friends":                   mutual_friends,
                        "positions_taken":                  positions_taken,
                    }
                    friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_SENT_TO_ME:
        status += "KIND_OF_LIST-FRIEND_INVITATIONS_SENT_TO_ME "
        retrieve_invitations_sent_to_me_results = friend_manager.retrieve_friend_invitations_sent_to_me(
            voter.we_vote_id, read_only=True)
        success = retrieve_invitations_sent_to_me_results['success']
        status += retrieve_invitations_sent_to_me_results['status']
        if retrieve_invitations_sent_to_me_results['friend_list_found']:
            raw_friend_list = retrieve_invitations_sent_to_me_results['friend_list']
            heal_results = heal_friend_invitations_sent_to_me(voter.we_vote_id, raw_friend_list)
            verified_friend_list = heal_results['friend_list']
            status += heal_results['status']
            for one_friend_invitation in verified_friend_list:
                # Augment the line with voter information
                friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    one_friend_invitation.sender_voter_we_vote_id)  # This is the voter who sent the invitation to me
                if friend_voter_results['voter_found']:
                    friend_voter = friend_voter_results['voter']
                    recipient_voter_email = one_friend_invitation.recipient_voter_email \
                        if hasattr(one_friend_invitation, "recipient_voter_email") \
                        else ""
                    mutual_friends = friend_manager.fetch_mutual_friends_count(
                        voter.we_vote_id, friend_voter.we_vote_id)
                    positions_taken = position_metrics_manager.fetch_positions_count_for_this_voter(friend_voter)
                    one_friend = {
                        "voter_we_vote_id":                 friend_voter.we_vote_id,
                        "voter_display_name":               friend_voter.get_full_name(),
                        "voter_photo_url_large":            friend_voter.we_vote_hosted_profile_image_url_large
                            if positive_value_exists(friend_voter.we_vote_hosted_profile_image_url_large)
                            else friend_voter.voter_photo_url(),
                        'voter_photo_url_medium':           friend_voter.we_vote_hosted_profile_image_url_medium,
                        'voter_photo_url_tiny':             friend_voter.we_vote_hosted_profile_image_url_tiny,
                        "voter_email_address":              friend_voter.email,
                        "voter_twitter_handle":             friend_voter.twitter_screen_name,
                        "voter_twitter_description":        "",  # To be implemented
                        "voter_twitter_followers_count":    0,  # To be implemented
                        "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                        "voter_state_code":                 "",  # To be implemented
                        "invitation_status":                "",  # Not used for invitations sent to me
                        "invitation_sent_to":               recipient_voter_email,
                        "invitation_table":                 one_friend_invitation.invitation_table,
                        "mutual_friends":                   mutual_friends,
                        "positions_taken":                  positions_taken,
                    }
                    friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_SENT_BY_ME:
        status += "KIND_OF_LIST-FRIEND_INVITATIONS_SENT_BY_ME "
        retrieve_invitations_sent_by_me_results = friend_manager.retrieve_friend_invitations_sent_by_me(
            voter.we_vote_id)
        success = retrieve_invitations_sent_by_me_results['success']
        status += retrieve_invitations_sent_by_me_results['status']
        if retrieve_invitations_sent_by_me_results['friend_list_found']:
            raw_friend_list = retrieve_invitations_sent_by_me_results['friend_list']
            for one_friend_invitation in raw_friend_list:
                # Two kinds of invitations come in the raw_friend_list, 1) an invitation connected to voter
                # 2) an invitation to a previously unrecognized email address
                if hasattr(one_friend_invitation, 'recipient_voter_we_vote_id'):
                    recipient_voter_we_vote_id = one_friend_invitation.recipient_voter_we_vote_id
                else:
                    recipient_voter_we_vote_id = ""
                recipient_voter_email = one_friend_invitation.recipient_voter_email \
                    if hasattr(one_friend_invitation, "recipient_voter_email") \
                    else ""

                if positive_value_exists(recipient_voter_we_vote_id):
                    friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                        recipient_voter_we_vote_id)  # This is the voter who received invitation
                    if friend_voter_results['voter_found']:
                        friend_voter = friend_voter_results['voter']
                        positions_taken = position_metrics_manager.fetch_positions_count_for_this_voter(friend_voter)
                        mutual_friends = friend_manager.fetch_mutual_friends_count(
                            voter.we_vote_id, friend_voter.we_vote_id)
                        one_friend = {
                            "voter_we_vote_id":                 friend_voter.we_vote_id,
                            "voter_display_name":               friend_voter.get_full_name(),
                            "voter_photo_url_large":            friend_voter.we_vote_hosted_profile_image_url_large
                            if positive_value_exists(friend_voter.we_vote_hosted_profile_image_url_large)
                            else friend_voter.voter_photo_url(),
                            'voter_photo_url_medium':           friend_voter.we_vote_hosted_profile_image_url_medium,
                            'voter_photo_url_tiny':             friend_voter.we_vote_hosted_profile_image_url_tiny,
                            "voter_email_address":              friend_voter.email,
                            "voter_twitter_handle":             friend_voter.twitter_screen_name,
                            "voter_twitter_description":        "",  # To be implemented
                            "voter_twitter_followers_count":    0,  # To be implemented
                            "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                            "voter_state_code":                 "",  # To be implemented
                            "invitation_status":                one_friend_invitation.invitation_status,
                            "invitation_table":                 one_friend_invitation.invitation_table,
                            "invitation_sent_to":               recipient_voter_email,
                            "mutual_friends":                   mutual_friends,
                            "positions_taken":                  positions_taken,
                        }
                        friend_list.append(one_friend)
                else:
                    if hasattr(one_friend_invitation, 'recipient_voter_email'):
                        if positive_value_exists(one_friend_invitation.recipient_voter_email):
                            one_friend = {
                                "voter_we_vote_id":                 "",
                                "voter_display_name":               "",
                                "voter_photo_url_large":            "",
                                'voter_photo_url_medium':           "",
                                'voter_photo_url_tiny':             "",
                                "voter_twitter_handle":             "",
                                "voter_twitter_description":        "",  # To be implemented
                                "voter_twitter_followers_count":    0,  # To be implemented
                                "voter_state_code":                 "",  # To be implemented
                                "voter_email_address":              one_friend_invitation.recipient_voter_email,
                                "invitation_status":                one_friend_invitation.invitation_status,
                                "invitation_table":                 one_friend_invitation.invitation_table,
                                "invitation_sent_to":               recipient_voter_email,
                                "mutual_friends":                   0,
                                "positions_taken":                  0,
                            }
                            friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION:
        status += "KIND_OF_LIST-FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION "
        send_status = WAITING_FOR_VERIFICATION
        success = True
        status = ""
        email_manager = EmailManager()
        scheduled_email_results = email_manager.retrieve_scheduled_email_list_from_send_status(
            voter.we_vote_id, send_status)
        status += scheduled_email_results['status']
        if scheduled_email_results['scheduled_email_list_found']:
            scheduled_email_list = scheduled_email_results['scheduled_email_list']
            for scheduled_email in scheduled_email_list:
                one_friend = {
                    "voter_we_vote_id": "",
                    "voter_display_name": "",
                    "voter_photo_url_large": "",
                    'voter_photo_url_medium': "",
                    'voter_photo_url_tiny': "",
                    "voter_twitter_handle": "",
                    "voter_twitter_description": "",
                    "voter_twitter_followers_count": 0,
                    "voter_state_code": "",
                    "voter_email_address": "",
                    "invitation_status": scheduled_email.send_status,
                    "invitation_sent_to": scheduled_email.recipient_voter_email,
                    "mutual_friends": 0,
                    "positions_taken": 0,
                }
                friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == SUGGESTED_FRIEND_LIST:
        status += "KIND_OF_LIST-SUGGESTED_FRIEND_LIST "
        retrieve_suggested_friend_list_as_voters_results = friend_manager.retrieve_suggested_friend_list_as_voters(
            voter.we_vote_id)
        success = retrieve_suggested_friend_list_as_voters_results['success']
        status += retrieve_suggested_friend_list_as_voters_results['status']
        if retrieve_suggested_friend_list_as_voters_results['friend_list_found']:
            suggested_friend_list = retrieve_suggested_friend_list_as_voters_results['friend_list']
            for suggested_friend in suggested_friend_list:
                if not positive_value_exists(suggested_friend.linked_organization_we_vote_id):
                    # We need to retrieve another voter object that can be saved
                    organization_manager = OrganizationManager()
                    voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                        suggested_friend.we_vote_id, read_only=False)
                    if voter_results['voter_found']:
                        suggested_friend = voter_results['voter']
                        heal_results = \
                            organization_manager.heal_voter_missing_linked_organization_we_vote_id(suggested_friend)
                        if heal_results['voter_healed']:
                            suggested_friend = heal_results['voter']
                            status += "SUGGESTED_FRIEND_HEALED-MISSING_LINKED_ORGANIZATION_WE_VOTE_ID: " \
                                      "" + suggested_friend.we_vote_id + " "
                        else:
                            status += "SUGGESTED_FRIEND_VOTER_COULD_NOT_BE_HEALED " + heal_results['status']
                    else:
                        status += "SUGGESTED-COULD_NOT_RETRIEVE_VOTER_THAT_CAN_BE_SAVED " + voter_results['status']
                mutual_friends = \
                    friend_manager.fetch_mutual_friends_count(voter.we_vote_id, suggested_friend.we_vote_id)
                positions_taken = position_metrics_manager.fetch_positions_count_for_this_voter(suggested_friend)
                one_friend = {
                    "voter_we_vote_id":                 suggested_friend.we_vote_id,
                    "voter_display_name":               suggested_friend.get_full_name(),
                    "voter_photo_url_large":            suggested_friend.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(suggested_friend.we_vote_hosted_profile_image_url_large)
                    else suggested_friend.voter_photo_url(),
                    'voter_photo_url_medium':           suggested_friend.we_vote_hosted_profile_image_url_medium,
                    'voter_photo_url_tiny':             suggested_friend.we_vote_hosted_profile_image_url_tiny,
                    "voter_email_address":              suggested_friend.email,
                    "voter_twitter_handle":             suggested_friend.twitter_screen_name,
                    "voter_twitter_description":        "",  # To be implemented
                    "voter_twitter_followers_count":    0,  # To be implemented
                    "linked_organization_we_vote_id":   suggested_friend.linked_organization_we_vote_id,
                    "voter_state_code":                 "",  # To be implemented
                    "invitation_status":                "",  # Not used with SuggestedFriendList
                    "invitation_sent_to":               "",  # Not used with SuggestedFriendList
                    "mutual_friends":                   mutual_friends,
                    "positions_taken":                  positions_taken,
                }
                friend_list.append(one_friend)
    else:
        status += kind_of_list_we_are_looking_for + " KIND_OF_LIST_NOT_IMPLEMENTED_YET "

    friend_list_found = True if len(friend_list) else False

    results = {
        'success':              success,
        'status':               status,
        'voter_device_id':      voter_device_id,
        'state_code':           state_code,
        'kind_of_list':         kind_of_list_we_are_looking_for,
        'friend_list_found':    friend_list_found,
        'friend_list':          friend_list,
    }
    return results


def heal_current_friend(current_friend, force_update=False):
    change_needed = False
    if not positive_value_exists(current_friend.viewee_organization_we_vote_id) \
            or not positive_value_exists(current_friend.viewer_organization_we_vote_id) or force_update:
        # We need to retrieve a copy of current friend which is editable
        friend_manager = FriendManager()
        results = friend_manager.retrieve_current_friend(
            current_friend.viewer_voter_we_vote_id, current_friend.viewee_voter_we_vote_id, read_only=False)
        if results['current_friend_found']:
            current_friend = results['current_friend']
    try:
        voter_manager = VoterManager()
        if not positive_value_exists(current_friend.viewee_organization_we_vote_id) or force_update:
            current_friend.viewee_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(
                    current_friend.viewee_voter_we_vote_id)
            change_needed = True
        if not positive_value_exists(current_friend.viewer_organization_we_vote_id) or force_update:
            current_friend.viewer_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(
                    current_friend.viewer_voter_we_vote_id)
            change_needed = True
        if change_needed:
            current_friend.save()
    except Exception as e:
        pass
    return current_friend


def heal_friend_invitations_sent_to_me(voter_we_vote_id, friend_invitation_list):
    success = True
    status = ''
    modified_friend_list = []
    if not positive_value_exists(voter_we_vote_id):
        status += 'HEAL_FRIEND_INVITATIONS_MISSING_VOTER_WE_VOTE_ID '
        results = {
            'success': success,
            'status': status,
            'friend_list': friend_invitation_list,
        }
        return results

    friend_manager = FriendManager()
    for one_friend_invitation in friend_invitation_list:
        if not positive_value_exists(one_friend_invitation.sender_voter_we_vote_id):
            # Cannot heal without sender_voter_we_vote_id
            modified_friend_list.append(one_friend_invitation)
            continue
        friend_results = friend_manager.retrieve_current_friend(
            sender_voter_we_vote_id=voter_we_vote_id,
            recipient_voter_we_vote_id=one_friend_invitation.sender_voter_we_vote_id,
            read_only=True)
        if friend_results['current_friend_found']:
            status += friend_results['status']
            # Delete the friend invitation
            invitation_results = friend_manager.delete_friend_invitation_voter_link(id=one_friend_invitation.id)
            status += invitation_results['status']
        else:
            modified_friend_list.append(one_friend_invitation)

    results = {
        'success':              success,
        'status':               status,
        'friend_list':          modified_friend_list,
    }
    return results


def move_friend_invitations_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = "MOVE_FRIEND_INVITATIONS_START "
    success = False
    friend_invitation_entries_moved = 0
    friend_invitation_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status = "MOVE_FRIENDS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID"
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'friend_invitation_entries_moved':      0,
            'friend_invitation_entries_not_moved':  0,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_FRIEND_INVITATIONS_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'friend_invitation_entries_moved': 0,
            'friend_invitation_entries_not_moved': 0,
        }
        return results

    friend_manager = FriendManager()

    # ###############################
    # FriendInvitationEmailLink
    # SENDER entries
    # FROM SENDER: Invitations sent BY the from_voter to others
    friend_invitation_email_link_from_sender_results = friend_manager.retrieve_friend_invitation_email_link_list(
        from_voter_we_vote_id)
    if friend_invitation_email_link_from_sender_results['friend_invitation_list_found']:
        friend_invitation_email_link_from_sender_list = \
            friend_invitation_email_link_from_sender_results['friend_invitation_list']

        # TO SENDER: Now get existing invitations for the to_voter so we can see if an invitation already exists
        friend_invitation_email_link_to_sender_results = friend_manager.retrieve_friend_invitation_email_link_list(
            to_voter_we_vote_id)
        friend_invitation_email_link_to_sender_list = \
            friend_invitation_email_link_to_sender_results['friend_invitation_list']

        for from_sender_entry in friend_invitation_email_link_from_sender_list:
            # See if the "to_voter" already has an invitation
            to_sender_invitation_found = False
            # Cycle through all of the "to_voter" entries and if there isn't one, move it
            for to_sender_entry in friend_invitation_email_link_to_sender_list:
                if to_sender_entry.recipient_voter_email == from_sender_entry.recipient_voter_email:
                    to_sender_invitation_found = True
                    break

            if not to_sender_invitation_found:
                # Change the sender_voter_we_vote_id to the new we_vote_id
                try:
                    from_sender_entry.sender_voter_we_vote_id = to_voter_we_vote_id
                    from_sender_entry.save()
                    friend_invitation_entries_moved += 1
                except Exception as e:
                    status += "FriendInvitationEmailLink Sender entries not moved " + str(e) + ' '
                    friend_invitation_entries_not_moved += 1
            else:
                status += "to_sender_invitation_found found, EmailLink Sender entries not moved "
                # friend_invitation_entries_not_moved += 1
                # TODO DALE Shouldn't we delete the from_sender_entry?

    # ###############################
    # FriendInvitationVoterLink
    # SENDER entries
    # FROM SENDER: Invitations sent BY the from_voter to others
    friend_invitation_voter_link_from_sender_results = friend_manager.retrieve_friend_invitation_voter_link_list(
        from_voter_we_vote_id)
    if friend_invitation_voter_link_from_sender_results['friend_invitation_list_found']:
        friend_invitation_voter_link_from_sender_list = \
            friend_invitation_voter_link_from_sender_results['friend_invitation_list']

        # TO SENDER: Now get existing invitations for the to_voter so we can see if an invitation already exists
        friend_invitation_voter_link_to_sender_results = friend_manager.retrieve_friend_invitation_voter_link_list(
            to_voter_we_vote_id)
        friend_invitation_voter_link_to_sender_list = \
            friend_invitation_voter_link_to_sender_results['friend_invitation_list']

        for from_sender_entry in friend_invitation_voter_link_from_sender_list:
            # See if the "to_voter" already has an invitation
            to_sender_invitation_found = False
            # Cycle through all of the "to_voter" entries and if there isn't one, move it
            for to_sender_entry in friend_invitation_voter_link_to_sender_list:
                if to_sender_entry.recipient_voter_we_vote_id == from_sender_entry.recipient_voter_we_vote_id:
                    to_sender_invitation_found = True
                    break

            if not to_sender_invitation_found:
                # Change the friendship values to the new we_vote_id
                try:
                    from_sender_entry.sender_voter_we_vote_id = to_voter_we_vote_id
                    from_sender_entry.save()
                    friend_invitation_entries_moved += 1
                except Exception as e:
                    status += "FriendInvitationVoterLink Sender entries not moved " + str(e) + ' '
                    friend_invitation_entries_not_moved += 1
            else:
                status += "to_sender_invitation_found found, VoterLink Sender entries not moved "
                # friend_invitation_entries_not_moved += 1
                # TODO DALE Shouldn't we delete the from_sender_entry?

    # RECIPIENT entries
    # FROM RECIPIENT: Invitations sent TO the from_voter from others
    friend_invitation_voter_link_from_recipient_results = friend_manager.retrieve_friend_invitation_voter_link_list(
        '', from_voter_we_vote_id)
    if friend_invitation_voter_link_from_recipient_results['friend_invitation_list_found']:
        friend_invitation_voter_link_from_recipient_list = \
            friend_invitation_voter_link_from_recipient_results['friend_invitation_list']

        # TO RECIPIENT: Now get existing invitations for the to_voter so we can see if an invitation already exists
        friend_invitation_voter_link_to_recipient_results = friend_manager.retrieve_friend_invitation_voter_link_list(
            '', to_voter_we_vote_id)
        friend_invitation_voter_link_to_recipient_list = \
            friend_invitation_voter_link_to_recipient_results['friend_invitation_list']
        status += friend_invitation_voter_link_to_recipient_results['status']

        for from_sender_entry in friend_invitation_voter_link_from_recipient_list:
            # See if the "to_voter" already has an invitation
            to_sender_invitation_found = False
            # Cycle through all of the "to_voter" entries and if there isn't one, move it
            for to_sender_entry in friend_invitation_voter_link_to_recipient_list:
                if to_sender_entry.sender_voter_we_vote_id == from_sender_entry.sender_voter_we_vote_id:
                    to_sender_invitation_found = True
                    break

            if not to_sender_invitation_found:
                # Change the friendship values to the new we_vote_id
                try:
                    from_sender_entry.recipient_voter_we_vote_id = to_voter_we_vote_id
                    from_sender_entry.save()
                    friend_invitation_entries_moved += 1
                except Exception as e:
                    status += "FriendInvitationVoterLink Recipient entries not moved "
                    friend_invitation_entries_not_moved += 1
            else:
                status += "to_sender_invitation_found found, Recipient entries not moved "
                # friend_invitation_entries_not_moved += 1
                # TODO DALE Shouldn't we delete the from_sender_entry?
    status += " FRIEND_INVITATIONS moved: " + str(friend_invitation_entries_moved) + \
              ", not moved: " + str(friend_invitation_entries_not_moved) + " "

    results = {
        'status':                   status,
        'success':                  success,
        'from_voter_we_vote_id':    from_voter_we_vote_id,
        'to_voter_we_vote_id':      to_voter_we_vote_id,
        'friend_entries_moved':     friend_invitation_entries_moved,
        'friend_entries_not_moved': friend_invitation_entries_not_moved,
    }
    return results


def move_friends_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id,
        to_voter_linked_organization_we_vote_id):
    status = ''
    success = False
    friend_entries_moved = 0
    friend_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_FRIENDS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'friend_entries_moved': friend_entries_moved,
            'friend_entries_not_moved': friend_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_FRIENDS_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'friend_entries_moved': friend_entries_moved,
            'friend_entries_not_moved': friend_entries_not_moved,
        }
        return results

    if not positive_value_exists(to_voter_linked_organization_we_vote_id):
        voter_manager = VoterManager()
        to_voter_linked_organization_we_vote_id = \
            voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(to_voter_we_vote_id)

    friend_manager = FriendManager()
    from_friend_results = friend_manager.retrieve_current_friends(from_voter_we_vote_id, read_only=False)
    from_friend_list = from_friend_results['current_friend_list']
    to_friend_results = friend_manager.retrieve_current_friends(to_voter_we_vote_id, read_only=False)
    to_friend_list = to_friend_results['current_friend_list']

    for from_friend_entry in from_friend_list:
        # See if the "to_voter" already has a matching entry
        to_friend_found = False
        from_friend_other_friend = from_friend_entry.fetch_other_voter_we_vote_id(from_voter_we_vote_id)
        # Cycle through all of the "to_voter" current_friend entries and if there isn't one, create it
        for to_friend_entry in to_friend_list:
            to_friend_other_friend = to_friend_entry.fetch_other_voter_we_vote_id(to_voter_we_vote_id)
            if to_friend_other_friend == from_friend_other_friend:
                to_friend_found = True
                break

        if not to_friend_found:
            # Change the friendship values to the new we_vote_id
            try:
                if from_friend_entry.viewer_voter_we_vote_id == from_voter_we_vote_id:
                    from_friend_entry.viewer_voter_we_vote_id = to_voter_we_vote_id
                    from_friend_entry.viewer_organization_we_vote_id = to_voter_linked_organization_we_vote_id
                else:
                    from_friend_entry.viewee_voter_we_vote_id = to_voter_we_vote_id
                    from_friend_entry.viewee_organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_friend_entry.save()
                friend_entries_moved += 1
            except Exception as e:
                friend_entries_not_moved += 1
                status += "PROBLEM_UPDATING_FRIEND " + str(e) + ' '

    from_friend_list_remaining_results = friend_manager.retrieve_current_friends(from_voter_we_vote_id, read_only=False)
    from_friend_list_remaining = from_friend_list_remaining_results['current_friend_list']
    for from_friend_entry in from_friend_list_remaining:
        # Delete the remaining friendship values
        try:
            # Leave this turned off until testing is finished
            from_friend_entry.delete()
        except Exception as e:
            status += "PROBLEM_DELETING_FRIEND " + str(e) + ' '

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'friend_entries_moved': friend_entries_moved,
        'friend_entries_not_moved': friend_entries_not_moved,
    }
    return results


def move_suggested_friends_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = False
    suggested_friend_entries_moved = 0
    suggested_friend_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_SUGGESTED_FRIENDS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'suggested_friend_entries_moved':       suggested_friend_entries_moved,
            'suggested_friend_entries_not_moved':   suggested_friend_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_SUGGESTED_FRIENDS_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'suggested_friend_entries_moved':       suggested_friend_entries_moved,
            'suggested_friend_entries_not_moved':   suggested_friend_entries_not_moved,
        }
        return results

    friend_manager = FriendManager()
    from_friend_results = friend_manager.retrieve_suggested_friend_list(
        from_voter_we_vote_id, hide_deleted=False, read_only=False)
    from_friend_list = from_friend_results['suggested_friend_list']
    to_friend_results = friend_manager.retrieve_suggested_friend_list(
        to_voter_we_vote_id, hide_deleted=False, read_only=False)
    to_friend_list = to_friend_results['suggested_friend_list']

    for from_friend_entry in from_friend_list:
        # See if the "to_voter" already has a matching entry
        to_friend_found = False
        from_friend_other_friend = from_friend_entry.fetch_other_voter_we_vote_id(from_voter_we_vote_id)
        # Cycle through all of the "to_voter" current_friend entries and if there isn't one, create it
        for to_friend_entry in to_friend_list:
            to_friend_other_friend = to_friend_entry.fetch_other_voter_we_vote_id(to_voter_we_vote_id)
            if to_friend_other_friend == from_friend_other_friend:
                to_friend_found = True
                break

        if not to_friend_found:
            # Change the friendship values to the new we_vote_id
            try:
                if from_friend_entry.viewer_voter_we_vote_id == from_voter_we_vote_id:
                    from_friend_entry.viewer_voter_we_vote_id = to_voter_we_vote_id
                else:
                    from_friend_entry.viewee_voter_we_vote_id = to_voter_we_vote_id
                from_friend_entry.save()
                suggested_friend_entries_moved += 1
            except Exception as e:
                suggested_friend_entries_not_moved += 1
                status += "PROBLEM_UPDATING_SUGGESTED_FRIEND " + str(e) + ' '

    from_friend_list_remaining_results = friend_manager.retrieve_suggested_friend_list(
        from_voter_we_vote_id, hide_deleted=False, read_only=False)
    from_friend_list_remaining = from_friend_list_remaining_results['suggested_friend_list']
    for from_friend_entry in from_friend_list_remaining:
        # Delete the remaining friendship values
        try:
            # Leave this turned off until testing is finished
            from_friend_entry.delete()
        except Exception as e:
            status += "PROBLEM_DELETING_FRIEND " + str(e) + ' '

    results = {
        'status':                               status,
        'success':                              success,
        'from_voter_we_vote_id':                from_voter_we_vote_id,
        'to_voter_we_vote_id':                  to_voter_we_vote_id,
        'suggested_friend_entries_moved':       suggested_friend_entries_moved,
        'suggested_friend_entries_not_moved':   suggested_friend_entries_not_moved,
    }
    return results


def retrieve_voter_and_email_address(one_normalized_raw_email):
    """
    Starting with an incoming email address, find the EmailAddress and Voter that owns it (if it exists)
    Includes code to "heal" the data if needed.
    :param one_normalized_raw_email:
    :return:
    """
    voter_friend_found = False
    voter_friend = Voter()
    status = ""
    status += "RETRIEVE_VOTER_AND_EMAIL_ADDRESS "

    voter_manager = VoterManager()
    email_manager = EmailManager()
    email_address_object = EmailAddress()
    email_address_object_found = False

    email_results = email_manager.retrieve_email_address_object(one_normalized_raw_email)

    if email_results['email_address_object_found']:
        # We have an EmailAddress entry for this raw email
        email_address_object = email_results['email_address_object']
        email_address_object_found = True
        status += "EMAIL_ADDRESS_FOUND "
    elif email_results['email_address_list_found']:
        # This email was used by more than one voter account. Use the first one returned.
        email_address_list = email_results['email_address_list']
        email_address_object = email_address_list[0]
        email_address_object_found = True
        status += "EMAIL_ADDRESS_LIST_FOUND "
    else:
        status += email_results['status']
        status += "CREATE_EMAIL_ADDRESS_FOR_NEW_VOTER "
        # We need to create an EmailAddress entry for this raw email
        voter_by_email_results = voter_manager.retrieve_voter_by_email(one_normalized_raw_email)
        if voter_by_email_results['voter_found']:
            # Create EmailAddress entry for existing voter
            voter_friend_found = True
            voter_friend = voter_by_email_results['voter']
            email_results = email_manager.create_email_address_for_voter(one_normalized_raw_email, voter_friend)
        else:
            # Create EmailAddress entry without voter
            voter_friend_found = False
            email_results = email_manager.create_email_address(one_normalized_raw_email)

        if email_results['email_address_object_saved']:
            # We recognize the email
            email_address_object_found = True
            email_address_object = email_results['email_address_object']

    # double-check that we have email_address_object
    if not email_address_object_found:
        success = False
        status += "RETRIEVE_VOTER_AND_EMAIL-EMAIL_ADDRESS_OBJECT_MISSING "
        results = {
            'success':              success,
            'status':               status,
            'voter_found':          voter_friend_found,
            'voter':                voter_friend,
            'email_address_object': email_address_object,
        }
        return results
    else:
        success = True

    if not voter_friend_found:
        if positive_value_exists(email_address_object.voter_we_vote_id):
            voter_friend_results = voter_manager.retrieve_voter_by_we_vote_id(email_address_object.voter_we_vote_id)
            if not voter_friend_results['success']:
                status += voter_friend_results['status']
            else:
                if voter_friend_results['voter_found']:
                    voter_friend_found = True
                    voter_friend = voter_friend_results['voter']
                else:
                    email_address_object.voter_we_vote_id = ''
                    voter_friend_found = False
                    voter_friend = Voter()

    # Does another, different voter use this email address?
    # voter_by_email_results = voter_manager.retrieve_voter_by_email(one_normalized_raw_email)
    # If so, we need to ...

    results = {
        'success':              success,
        'status':               status,
        'voter_found':          voter_friend_found,
        'voter':                voter_friend,
        'email_address_object': email_address_object,
    }
    return results


def retrieve_current_friend_by_email(viewing_voter, one_normalized_raw_email):
    success = True
    status = ''
    voter_friend = None
    email_address_object = None
    current_friend_found = False
    current_friend = None

    results = retrieve_voter_and_email_address(one_normalized_raw_email)
    voter_friend_found = results['voter_found']
    if voter_friend_found:
        voter_friend = results['voter']
        email_address_object = results['email_address_object']

        friend_manager = FriendManager()
        friend_results = friend_manager.retrieve_current_friend(
            sender_voter_we_vote_id=viewing_voter.we_vote_id, recipient_voter_we_vote_id=voter_friend.we_vote_id)
        current_friend_found = friend_results['current_friend_found']
        current_friend = friend_results['current_friend']

    results = {
        'success':              success,
        'status':               status,
        'voter_found':          voter_friend_found,
        'voter':                voter_friend,
        'email_address_object': email_address_object,
        'current_friend_found': current_friend_found,
        'current_friend':       current_friend,
    }
    return results


def store_internal_friend_invitation_with_two_voters(voter, invitation_message,
                                                     voter_friend):
    status = ""
    sender_voter_we_vote_id = voter.we_vote_id
    recipient_voter_we_vote_id = voter_friend.we_vote_id

    # Check to make sure the sender_voter is not trying to invite self
    if sender_voter_we_vote_id == recipient_voter_we_vote_id:
        success = False
        status += "CANNOT_INVITE_SELF "
        friend_invitation = FriendInvitationVoterLink()
        results = {
            'success':                  success,
            'status':                   status,
            'friend_invitation_saved':  False,
            'friend_invitation':        friend_invitation,
        }
        return results

    friend_manager = FriendManager()
    sender_email_ownership_is_verified = voter.has_email_with_verified_ownership()
    invitation_secret_key = generate_random_string(12)

    create_results = friend_manager.update_or_create_friend_invitation_voter_link(
        sender_voter_we_vote_id, recipient_voter_we_vote_id, invitation_message, sender_email_ownership_is_verified,
        invitation_secret_key=invitation_secret_key)
    status += create_results['status']
    results = {
        'success':                  create_results['success'],
        'status':                   status,
        'friend_invitation_saved':  create_results['friend_invitation_saved'],
        'friend_invitation':        create_results['friend_invitation'],
    }
    return results


def store_internal_friend_invitation_with_unknown_email(voter, invitation_message,
                                                        email_address_object, first_name, last_name):
    sender_voter_we_vote_id = voter.we_vote_id
    recipient_email_we_vote_id = email_address_object.we_vote_id
    recipient_voter_email = email_address_object.normalized_email_address

    friend_manager = FriendManager()
    sender_email_ownership_is_verified = voter.has_email_with_verified_ownership()
    invitation_secret_key = generate_random_string(12)

    create_results = friend_manager.update_or_create_friend_invitation_email_link(
        sender_voter_we_vote_id,
        recipient_email_we_vote_id,
        recipient_voter_email, first_name, last_name, invitation_message, sender_email_ownership_is_verified,
        invitation_secret_key)
    results = {
        'success':                  create_results['success'],
        'status':                   create_results['status'],
        'friend_invitation_saved':  create_results['friend_invitation_saved'],
        'friend_invitation':        create_results['friend_invitation'],
    }

    return results
