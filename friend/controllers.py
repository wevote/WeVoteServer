# friend/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ACCEPTED, FriendInvitationVoterLink, FriendManager, CURRENT_FRIENDS, \
    DELETE_INVITATION_EMAIL_SENT_BY_ME, FRIEND_INVITATIONS_PROCESSED, \
    FRIEND_INVITATIONS_SENT_BY_ME, FRIEND_INVITATIONS_SENT_TO_ME, FRIENDS_IN_COMMON, UNFRIEND_CURRENT_FRIEND
from config.base import get_environment_variable
from email_outbound.controllers import schedule_email_with_email_outbound_description, schedule_verification_email
from email_outbound.models import EmailAddress, EmailManager, FRIEND_INVITATION_TEMPLATE, VERIFY_EMAIL_ADDRESS_TEMPLATE
import json
from validate_email import validate_email
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import generate_random_string, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")


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


def friend_invitation_by_email_send_for_api(voter_device_id, email_addresses_raw, invitation_message,
                                            sender_email_address):
    success = False
    status = ""
    error_message_to_show_voter = ""

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
    sender_voter_id = voter_results['voter_id']
    if not positive_value_exists(sender_voter_id):
        error_results = {
            'status':                               "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    sender_voter = voter_results['voter']
    email_manager = EmailManager()
    messages_to_send = []

    send_now = False
    valid_new_sender_email_address = False
    if sender_voter.has_email_with_verified_ownership():
        send_now = True
        sender_email_with_ownership_verified = \
            email_manager.fetch_primary_email_with_ownership_verified(sender_voter.we_vote_id)
    else:
        # If here, check to see if a sender_email_address was passed in
        valid_new_sender_email_address = False
        if not positive_value_exists(sender_email_address) or not validate_email(sender_email_address):
            error_results = {
                'status':                               "VOTER_DOES_NOT_HAVE_VALID_EMAIL",
                'success':                              False,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   True,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results
        else:
            valid_new_sender_email_address = True

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
        elif results['email_address_list_found']:
            # The case where there is more than one email entry for one voter shouldn't be possible, but if so,
            # just use the first one returned
            email_address_list = results['email_address_list']
            sender_email_address_object = email_address_list[0]
            email_address_object_found = True
        else:
            # Create email address object
            email_results = email_manager.create_email_address_for_voter(sender_email_address, sender_voter)

            if email_results['email_address_object_saved']:
                # We recognize the email
                email_address_object_found = True
                sender_email_address_object = email_results['email_address_object']
            else:
                valid_new_sender_email_address = False

        # double-check that we have email_address_object
        if not email_address_object_found:
            success = False
            status = "FRIEND_INVITATION_BY_EMAIL_SEND-EMAIL_ADDRESS_OBJECT_MISSING"
            error_results = {
                'success':                              success,
                'status':                               status,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   True,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results

    if valid_new_sender_email_address:
        # Send verification email, and store the rest of the data without processing until sender_email is verified
        recipient_voter_we_vote_id = sender_voter.we_vote_id
        recipient_email_we_vote_id = sender_email_address_object.we_vote_id
        recipient_voter_email = sender_email_address_object.normalized_email_address
        recipient_email_address_secret_key = sender_email_address_object
        send_now = False
        verification_context = None  # TODO DALE Figure out best way to do this

        verifications_send_results = schedule_verification_email(sender_voter.we_vote_id, recipient_voter_we_vote_id,
                                                                 recipient_email_we_vote_id, recipient_voter_email,
                                                                 recipient_email_address_secret_key,
                                                                 verification_context)
        status += verifications_send_results['status']
        email_scheduled_saved = verifications_send_results['email_scheduled_saved']
        email_scheduled_id = verifications_send_results['email_scheduled_id']
        # if email_scheduled_saved:
        #     messages_to_send.append(email_scheduled_id)

    if sender_voter.has_valid_email() or valid_new_sender_email_address:
        # We can continue. Note that we are not checking for "voter.has_email_with_verified_ownership()"
        pass
    else:
        error_results = {
            'status':                               "VOTER_DOES_NOT_HAVE_VALID_EMAIL",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    # Break apart all of the emails in email_addresses_raw input from the voter
    results = email_manager.parse_raw_emails_into_list(email_addresses_raw)
    if results['at_least_one_email_found']:
        raw_email_list_to_invite = results['email_list']
    else:
        error_message_to_show_voter = "Please enter the email address of at least one friend."
        error_results = {
            'status':                               "LIST_OF_EMAILS_NOT_RECEIVED " + results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   False,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    sender_name = sender_voter.get_full_name()
    sender_photo = sender_voter.voter_photo_url()
    sender_description = ""
    sender_network_details = ""

    # Check to see if we recognize any of these emails
    for one_normalized_raw_email in raw_email_list_to_invite:
        # Starting with a raw email address, find (or create) the EmailAddress entry
        # and the owner (Voter) if exists
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
            recipient_name = voter_friend.get_full_name()
        else:
            # Store the friend invitation in FriendInvitationEmailLink table
            friend_invitation_results = store_internal_friend_invitation_with_unknown_email(
                sender_voter, invitation_message, recipient_email_address_object)
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

        if invitation_secret_key is None:
            invitation_secret_key = ""

        system_sender_email_address = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

        template_variables_for_json = {
            "subject":                      subject,
            "invitation_message":           invitation_message,
            "sender_name":                  sender_name,
            "sender_photo":                 sender_photo,
            "sender_email_address":         system_sender_email_address,  # TODO DALE WAS sender_email_address,
            "sender_description":           sender_description,
            "sender_network_details":       sender_network_details,
            "recipient_name":               recipient_name,
            "recipient_voter_email":        recipient_voter_email,
            "see_all_friend_requests_url":  WEB_APP_ROOT_URL + "/requests",
            "confirm_friend_request_url":   WEB_APP_ROOT_URL + "/requests/" + invitation_secret_key,
            "recipient_unsubscribe_url":    WEB_APP_ROOT_URL + "/unsubscribe?email_key=1234",
            "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
        }
        template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

        # TODO DALE - What kind of policy do we want re: sending a second email to a person?
        # Create the outbound email description, then schedule it
        if friend_invitation_results['friend_invitation_saved'] and send_now:
            kind_of_email_template = FRIEND_INVITATION_TEMPLATE
            outbound_results = email_manager.create_email_outbound_description(
                sender_voter_we_vote_id, sender_email_with_ownership_verified, recipient_voter_we_vote_id,
                recipient_email_we_vote_id, recipient_voter_email,
                template_variables_in_json, kind_of_email_template)
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

    # When we are done scheduling all email, send it with a single connection to the smtp server
    # if send_now:
    #     send_results = email_manager.send_scheduled_email_list(messages_to_send)

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   False,
        'error_message_to_show_voter':          error_message_to_show_voter
    }
    return results


def friend_invitation_by_email_verify_for_api(voter_device_id, invitation_secret_key):  # friendInvitationByEmailVerify
    """

    :param voter_device_id:
    :param invitation_secret_key:
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
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter':  False,
        }
        return json_data

    if not positive_value_exists(invitation_secret_key):
        error_results = {
            'status':                                       "VOTER_EMAIL_ADDRESS_VERIFY_MISSING_SECRET_KEY",
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter':  False,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                                       "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   False,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter':  False,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_has_data_to_preserve = voter.has_data_to_preserve()

    friend_manager = FriendManager()
    friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(invitation_secret_key)
    if not friend_invitation_results['friend_invitation_found']:
        error_results = {
            'status':                                       "INVITATION_NOT_FOUND_FROM_SECRET_KEY",
            'success':                                      False,
            'voter_device_id':                              voter_device_id,
            'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
            'invitation_found':                             False,
            'attempted_to_approve_own_invitation':          False,
            'invitation_secret_key':                        invitation_secret_key,
            'invitation_secret_key_belongs_to_this_voter':  False,
        }
        return error_results

    # Now that we have the friend_invitation data, look more closely at it
    invitation_found = True
    voter_we_vote_id_accepting_invitation = ""
    email_manager = EmailManager()
    if friend_invitation_results['friend_invitation_voter_link_found']:
        friend_invitation_voter_link = friend_invitation_results['friend_invitation_voter_link']

        if friend_invitation_voter_link.sender_voter_we_vote_id == voter_we_vote_id:
            error_results = {
                'status':                                       "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED",
                'success':                                      False,
                'voter_device_id':                              voter_device_id,
                'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
                'invitation_found':                             True,
                'attempted_to_approve_own_invitation':          True,
                'invitation_secret_key':                        invitation_secret_key,
                'invitation_secret_key_belongs_to_this_voter':  True,
            }
            return error_results

        voter_we_vote_id_accepting_invitation = friend_invitation_voter_link.recipient_voter_we_vote_id
        # Now we want to make sure we have a current_friend entry
        friend_results = friend_manager.create_or_update_current_friend(
            friend_invitation_voter_link.sender_voter_we_vote_id,
            friend_invitation_voter_link.recipient_voter_we_vote_id)

        # Now that a CurrentFriend entry exists, update the FriendInvitation...
        if friend_results['success']:
            try:
                friend_invitation_voter_link.invitation_status = ACCEPTED
                friend_invitation_voter_link.deleted = True
                friend_invitation_voter_link.save()
            except Exception as e:
                success = False
                status += 'FAILED_TO_UPDATE_INVITATION_STATUS1'
        else:
            success = False
            status = " friend_invitation_voter_link_found CREATE_OR_UPDATE_CURRENT_FRIEND_FAILED"

        # We don't need to do anything with the email because this was an invitation to a known voter
    elif friend_invitation_results['friend_invitation_email_link_found']:
        friend_invitation_email_link = friend_invitation_results['friend_invitation_email_link']

        if friend_invitation_email_link.sender_voter_we_vote_id == voter_we_vote_id:
            error_results = {
                'status':                                       "SENDER_AND_RECIPIENT_ARE_IDENTICAL_FAILED",
                'success':                                      False,
                'voter_device_id':                              voter_device_id,
                'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
                'invitation_found':                             True,
                'attempted_to_approve_own_invitation':          True,
                'invitation_secret_key':                        invitation_secret_key,
                'invitation_secret_key_belongs_to_this_voter':  False,
            }
            return error_results

        # Check to see if the email used has been claimed by a voter account yet
        temp_voter_we_vote_id = ""
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
                voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
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
                except Exception as e:
                    success = False
                    status += 'FAILED_TO_UPDATE_UNVERIFIED_EMAIL'
            else:
                email_ownership_is_verified = True
                email_create_results = email_manager.create_email_address_for_voter(
                    friend_invitation_email_link.recipient_voter_email, voter, email_ownership_is_verified)
                if email_create_results['email_address_object_saved']:
                    email_address_object = email_create_results['email_address_object']
                    voter_manager.update_voter_email_ownership_verified(voter, email_address_object)

        # Now that we know who owns the recipient_email_address, update invitation status
        friend_results = friend_manager.create_or_update_current_friend(
            friend_invitation_email_link.sender_voter_we_vote_id,
            voter_we_vote_id_accepting_invitation)

        if friend_results['success']:
            try:
                friend_invitation_email_link.invitation_status = ACCEPTED
                friend_invitation_email_link.deleted = True
                friend_invitation_email_link.save()
                success = True
                status += ' friend_invitation_email_link_found FRIENDSHIP_CREATED'
            except Exception as e:
                success = False
                status += 'FAILED_TO_UPDATE_INVITATION_STATUS2'
        else:
            success = False
            status = " friend_invitation_email_link_found CREATE_OR_UPDATE_CURRENT_FRIEND_FAILED"

    invitation_secret_key_belongs_to_this_voter = \
        voter_we_vote_id == voter_we_vote_id_accepting_invitation

    json_data = {
        'status':                                       status,
        'success':                                      success,
        'voter_device_id':                              voter_device_id,
        'voter_has_data_to_preserve':                   voter_has_data_to_preserve,
        'invitation_found':                             invitation_found,
        'attempted_to_approve_own_invitation':          False,
        'invitation_secret_key':                        invitation_secret_key,
        'invitation_secret_key_belongs_to_this_voter':  invitation_secret_key_belongs_to_this_voter,
    }
    return json_data


def friend_invite_response_for_api(voter_device_id, kind_of_invite_response, other_voter_we_vote_id,
                                   recipient_voter_email=''):
    """
    friendInviteResponse
    :param voter_device_id:
    :param kind_of_invite_response:
    :param other_voter_we_vote_id:
    :param recipient_voter_email:
    :return:
    """
    success = False
    status = "IN_DEVELOPMENT"

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
        error_results = {
            'status':                               "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
        }
        return error_results
    voter = voter_results['voter']

    if kind_of_invite_response != DELETE_INVITATION_EMAIL_SENT_BY_ME:
        other_voter_results = voter_manager.retrieve_voter_by_we_vote_id(other_voter_we_vote_id)
        other_voter_id = other_voter_results['voter_id']
        if not positive_value_exists(other_voter_id):
            error_results = {
                'status':                               "VOTER_NOT_FOUND_FROM_OTHER_VOTER_WE_VOTE_ID",
                'success':                              False,
                'voter_device_id':                      voter_device_id,
            }
            return error_results
        other_voter = other_voter_results['voter']

    friend_manager = FriendManager()
    if kind_of_invite_response == UNFRIEND_CURRENT_FRIEND:
        results = friend_manager.unfriend_current_friend(voter.we_vote_id, other_voter.we_vote_id)
    elif kind_of_invite_response == DELETE_INVITATION_EMAIL_SENT_BY_ME:
        results = friend_manager.process_friend_invitation_email_response(voter, recipient_voter_email,
                                                                          kind_of_invite_response)
    else:
        results = friend_manager.process_friend_invitation_voter_response(other_voter, voter, kind_of_invite_response)
    success = results['success']
    status = results['status']

    results = {
        'success':              success,
        'status':               status,
        'voter_device_id':      voter_device_id,
    }
    return results


def friend_list_for_api(voter_device_id,
                        kind_of_list_we_are_looking_for=CURRENT_FRIENDS,
                        state_code=''):
    """
    friendList API Endpoint
    :param voter_device_id:
    :param kind_of_list_we_are_looking_for:
    :param state_code:
    :return:
    """
    success = False
    friend_list_found = False
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
    # IGNORED_FRIEND_INVITATIONS, SUGGESTED_FRIENDS):
    friend_manager = FriendManager()
    if kind_of_list_we_are_looking_for == CURRENT_FRIENDS:
        retrieve_current_friends_as_voters_results = friend_manager.retrieve_current_friends_as_voters(voter.we_vote_id)
        success = retrieve_current_friends_as_voters_results['success']
        status = retrieve_current_friends_as_voters_results['status']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friend_list = retrieve_current_friends_as_voters_results['friend_list']
            for friend_voter in current_friend_list:
                one_friend = {
                    "voter_we_vote_id":                 friend_voter.we_vote_id,
                    "voter_display_name":               friend_voter.get_full_name(),
                    "voter_photo_url":                  friend_voter.voter_photo_url(),
                    "voter_email_address":              friend_voter.email,
                    "voter_twitter_handle":             friend_voter.twitter_screen_name,
                    "voter_twitter_description":        "",  # To be implemented
                    "voter_twitter_followers_count":    0,  # To be implemented
                    "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                    "voter_state_code":                 "",  # To be implemented
                    "invitation_status":                "",  # Not used with CurrentFriends
                    "invitation_sent_to":               "",  # Not used with CurrentFriends
                }
                friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_PROCESSED:
        retrieve_invitations_processed_results = friend_manager.retrieve_friend_invitations_processed(
            voter.we_vote_id)
        success = retrieve_invitations_processed_results['success']
        status = retrieve_invitations_processed_results['status']
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
                    one_friend = {
                        "voter_we_vote_id": friend_voter.we_vote_id,
                        "voter_display_name": friend_voter.get_full_name(),
                        "voter_photo_url": friend_voter.voter_photo_url(),
                        "voter_email_address": friend_voter.email,
                        "voter_twitter_handle": friend_voter.twitter_screen_name,
                        "voter_twitter_description": "",  # To be implemented
                        "voter_twitter_followers_count": 0,  # To be implemented
                        "linked_organization_we_vote_id": friend_voter.linked_organization_we_vote_id,
                        "voter_state_code": "",  # To be implemented
                        "invitation_status": one_friend_invitation.invitation_status,
                        "invitation_sent_to": recipient_voter_email,
                    }
                    friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_SENT_TO_ME:
        retrieve_invitations_sent_to_me_results = friend_manager.retrieve_friend_invitations_sent_to_me(
            voter.we_vote_id)
        success = retrieve_invitations_sent_to_me_results['success']
        status = retrieve_invitations_sent_to_me_results['status']
        if retrieve_invitations_sent_to_me_results['friend_list_found']:
            raw_friend_list = retrieve_invitations_sent_to_me_results['friend_list']
            for one_friend_invitation in raw_friend_list:
                # Augment the line with voter information
                friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    one_friend_invitation.sender_voter_we_vote_id)  # This is the voter who sent the invitation to me
                if friend_voter_results['voter_found']:
                    friend_voter = friend_voter_results['voter']
                    recipient_voter_email = one_friend_invitation.recipient_voter_email \
                        if hasattr(one_friend_invitation, "recipient_voter_email") \
                        else ""
                    one_friend = {
                        "voter_we_vote_id":                 friend_voter.we_vote_id,
                        "voter_display_name":               friend_voter.get_full_name(),
                        "voter_photo_url":                  friend_voter.voter_photo_url(),
                        "voter_email_address":              friend_voter.email,
                        "voter_twitter_handle":             friend_voter.twitter_screen_name,
                        "voter_twitter_description":        "",  # To be implemented
                        "voter_twitter_followers_count":    0,  # To be implemented
                        "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                        "voter_state_code":                 "",  # To be implemented
                        "invitation_status":                "",  # Not used for invitations sent to me
                        "invitation_sent_to":               recipient_voter_email,
                    }
                    friend_list.append(one_friend)
    elif kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_SENT_BY_ME:
        retrieve_invitations_sent_by_me_results = friend_manager.retrieve_friend_invitations_sent_by_me(
            voter.we_vote_id)
        success = retrieve_invitations_sent_by_me_results['success']
        status = retrieve_invitations_sent_by_me_results['status']
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
                        recipient_voter_we_vote_id)  # The is the voter who received invitation
                    if friend_voter_results['voter_found']:
                        friend_voter = friend_voter_results['voter']
                        one_friend = {
                            "voter_we_vote_id":                 friend_voter.we_vote_id,
                            "voter_display_name":               friend_voter.get_full_name(),
                            "voter_photo_url":                  friend_voter.voter_photo_url(),
                            "voter_email_address":              friend_voter.email,
                            "voter_twitter_handle":             friend_voter.twitter_screen_name,
                            "voter_twitter_description":        "",  # To be implemented
                            "voter_twitter_followers_count":    0,  # To be implemented
                            "linked_organization_we_vote_id":   friend_voter.linked_organization_we_vote_id,
                            "voter_state_code":                 "",  # To be implemented
                            "invitation_status":                one_friend_invitation.invitation_status,
                            "invitation_sent_to":               recipient_voter_email,
                        }
                        friend_list.append(one_friend)
                else:
                    if hasattr(one_friend_invitation, 'recipient_voter_email'):
                        if positive_value_exists(one_friend_invitation.recipient_voter_email):
                            one_friend = {
                                "voter_we_vote_id":                 "",
                                "voter_display_name":               "",
                                "voter_photo_url":                  "",
                                "voter_twitter_handle":             "",
                                "voter_twitter_description":        "",  # To be implemented
                                "voter_twitter_followers_count":    0,  # To be implemented
                                "voter_state_code":                 "",  # To be implemented
                                "voter_email_address":              one_friend_invitation.recipient_voter_email,
                                "invitation_status":                one_friend_invitation.invitation_status,
                                "invitation_sent_to":               recipient_voter_email,
                            }
                            friend_list.append(one_friend)
    else:
        status = kind_of_list_we_are_looking_for + " KIND_OF_LIST_NOT_IMPLEMENTED_YET"

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


def move_friend_invitations_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = "MOVE_FRIEND_INVITATIONS_IN_DEVELOPMENT "
    success = False
    friend_invitation_entries_moved = 0
    friend_invitation_entries_not_moved = 0

    # FriendInvitationEmailLink

    # FriendInvitationVoterLink

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'friend_entries_moved': friend_invitation_entries_moved,
        'friend_entries_not_moved': friend_invitation_entries_not_moved,
    }
    return results


def move_friends_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = False
    friend_entries_moved = 0
    friend_entries_not_moved = 0
    friend_manager = FriendManager()
    from_friend_results = friend_manager.retrieve_current_friends(from_voter_we_vote_id)
    from_friend_list = from_friend_results['current_friend_list']
    to_friend_results = friend_manager.retrieve_current_friends(to_voter_we_vote_id)
    to_friend_list = to_friend_results['current_friend_list']

    for from_friend_entry in from_friend_list:
        # See if the "to_voter" already has an entry for this organization
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
                from_friend_entry.viewer_voter_we_vote_id = to_voter_we_vote_id
                from_friend_entry.viewee_voter_we_vote_id = from_friend_other_friend
                from_friend_entry.save()
                friend_entries_moved += 1
            except Exception as e:
                friend_entries_not_moved += 1

    from_friend_list_remaining = friend_manager.retrieve_current_friends(from_voter_we_vote_id)
    for from_friend_entry in from_friend_list_remaining:
        # Delete the remaining friendship values
        try:
            # Leave this turned off until testing is finished
            # from_friend_entry.delete()
            pass
        except Exception as e:
            pass

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'friend_entries_moved': friend_entries_moved,
        'friend_entries_not_moved': friend_entries_not_moved,
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
    success = False
    status = ""

    voter_manager = VoterManager()
    email_manager = EmailManager()
    email_address_object = EmailAddress()
    email_address_object_found = False

    email_results = email_manager.retrieve_email_address_object(one_normalized_raw_email)

    if email_results['email_address_object_found']:
        # We have an EmailAddress entry for this raw email
        email_address_object = email_results['email_address_object']
        email_address_object_found = True
    elif email_results['email_address_list_found']:
        # This email was used by more than one voter account. Use the first one returned.
        email_address_list = email_results['email_address_list']
        email_address_object = email_address_list[0]
        email_address_object_found = True
    else:
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
        status = "RETRIEVE_VOTER_AND_EMAIL-EMAIL_ADDRESS_OBJECT_MISSING"
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
                # Error making the call -- do not remove voter_we_vote_id from email_address_object
                pass
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


def store_internal_friend_invitation_with_two_voters(voter, invitation_message,
                                                     voter_friend):
    sender_voter_we_vote_id = voter.we_vote_id
    recipient_voter_we_vote_id = voter_friend.we_vote_id

    # Check to make sure the sender_voter is not trying to invite self
    if sender_voter_we_vote_id == recipient_voter_we_vote_id:
        success = False
        status = "CANNOT_INVITE_SELF"
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

    create_results = friend_manager.create_or_update_friend_invitation_voter_link(
        sender_voter_we_vote_id, recipient_voter_we_vote_id, invitation_message, sender_email_ownership_is_verified,
        invitation_secret_key)
    results = {
        'success':                  create_results['success'],
        'status':                   create_results['status'],
        'friend_invitation_saved':  create_results['friend_invitation_saved'],
        'friend_invitation':        create_results['friend_invitation'],
    }

    return results


def store_internal_friend_invitation_with_unknown_email(voter, invitation_message,
                                                        email_address_object):
    sender_voter_we_vote_id = voter.we_vote_id
    recipient_email_we_vote_id = email_address_object.we_vote_id
    recipient_voter_email = email_address_object.normalized_email_address

    friend_manager = FriendManager()
    sender_email_ownership_is_verified = voter.has_email_with_verified_ownership()
    invitation_secret_key = generate_random_string(12)

    create_results = friend_manager.create_or_update_friend_invitation_email_link(
        sender_voter_we_vote_id, recipient_email_we_vote_id,
        recipient_voter_email, invitation_message, sender_email_ownership_is_verified,
        invitation_secret_key)
    results = {
        'success':                  create_results['success'],
        'status':                   create_results['status'],
        'friend_invitation_saved':  create_results['friend_invitation_saved'],
        'friend_invitation':        create_results['friend_invitation'],
    }

    return results
