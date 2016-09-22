# friend/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FriendInvitationVoterLink, FriendManager, CURRENT_FRIENDS, FRIEND_INVITATIONS_SENT_TO_ME, \
    FRIEND_INVITATIONS_SENT_BY_ME, FRIENDS_IN_COMMON
from email_outbound.models import EmailAddress, EmailManager, FRIEND_INVITATION
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def friend_invitation_by_email_send_for_api(voter_device_id, email_addresses_raw, invitation_message):
    success = False
    status = ""

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                               results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True
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
            'sender_voter_email_address_missing':   True
        }
        return error_results

    sender_voter = voter_results['voter']
    if not sender_voter.has_valid_email():
        error_results = {
            'status':                               "VOTER_DOES_NOT_HAVE_VALID_EMAIL",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True
        }
        return error_results

    # Break apart all of the emails in email_addresses_raw input from the voter
    email_manager = EmailManager()
    results = email_manager.parse_raw_emails_into_list(email_addresses_raw)
    if results['at_least_one_email_found']:
        raw_email_list_to_invite = results['email_list']
    else:
        error_results = {
            'status':                               "LIST_OF_EMAILS_NOT_RECEIVED " + results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   False
        }
        return error_results

    # Check to see if we recognize any of these emails
    messages_to_send = []
    for one_normalized_raw_email in raw_email_list_to_invite:
        # Starting with a raw email address, find (or create) the EmailAddress entry
        # and the owner (Voter) if exists
        retrieve_results = retrieve_voter_and_email_address(one_normalized_raw_email)
        if not retrieve_results['success']:
            results = {
                'success':                              False,
                'status':                               retrieve_results['status'],
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   False,
            }
            return results
        status += retrieve_results['status'] + " "

        email_address_object = retrieve_results['email_address_object']

        # Store the friend invitation linked to another voter, or to an email that isn't linked to a voter
        if retrieve_results['voter_found']:
            # Store the friend invitation in FriendInvitationVoterLink table
            voter_friend = retrieve_results['voter']
            friend_invitation_results = store_internal_friend_invitation_with_two_voters(
                sender_voter, invitation_message, voter_friend)
            status += friend_invitation_results['status'] + " "
            success = friend_invitation_results['success']
            sender_voter_we_vote_id = sender_voter.we_vote_id
            recipient_voter_we_vote_id = voter_friend.we_vote_id
            recipient_email_we_vote_id = email_address_object.we_vote_id
            recipient_voter_email = email_address_object.normalized_email_address
        else:
            # Store the friend invitation in FriendInvitationEmailLink table
            friend_invitation_results = store_internal_friend_invitation_with_unknown_email(
                sender_voter, invitation_message, email_address_object)
            status += friend_invitation_results['status'] + " "
            success = friend_invitation_results['success']
            sender_voter_we_vote_id = sender_voter.we_vote_id
            recipient_voter_we_vote_id = ""
            recipient_email_we_vote_id = email_address_object.we_vote_id
            recipient_voter_email = email_address_object.normalized_email_address

        # TODO DALE - What kind of policy do we want re: sending a second email to a person?
        # Create the outbound email description, then schedule it
        if friend_invitation_results['friend_invitation_saved']:
            # friend_invitation = friend_invitation_results['friend_invitation']
            kind_of_email_template = FRIEND_INVITATION
            outbound_results = email_manager.create_email_outbound_description(
                sender_voter_we_vote_id, recipient_voter_we_vote_id,
                recipient_email_we_vote_id, recipient_voter_email,
                invitation_message, kind_of_email_template)
            status += outbound_results['status'] + " "
            if outbound_results['email_outbound_description_saved']:
                email_outbound_description = outbound_results['email_outbound_description']
                schedule_results = email_manager.schedule_email(email_outbound_description)
                if schedule_results['email_scheduled_saved']:
                    messages_to_send.append(schedule_results['email_scheduled_id'])
                status += schedule_results['status'] + " "

    # When we are done scheduling all email, send it with a single connection to the smtp server
    # send_results = email_manager.send_scheduled_email_list(messages_to_send)

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   False,
    }
    return results


def friend_list_for_api(voter_device_id,
                        kind_of_list_we_are_looking_for=CURRENT_FRIENDS,
                        state_code=''):
    success = False
    status = "IN_DEVELOPMENT"
    friend_list_found = False
    friend_list = []

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

    # if kind_of_list in (
    # CURRENT_FRIENDS, FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_SENT_BY_ME, FRIENDS_IN_COMMON,
    # IGNORED_FRIEND_INVITATIONS, SUGGESTED_FRIENDS):
    friend_manager = FriendManager()
    voter_manager = VoterManager()
    if kind_of_list_we_are_looking_for == FRIEND_INVITATIONS_SENT_TO_ME:
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
                    one_friend = {
                        "voter_we_vote_id":                 friend_voter.we_vote_id,
                        "voter_display_name":               friend_voter.get_full_name(),
                        "voter_photo_url":                  friend_voter.voter_photo_url(),
                        "voter_twitter_handle":             friend_voter.twitter_screen_name,
                        "voter_twitter_description":        "",  # To be implemented
                        "voter_twitter_followers_count":    0,  # To be implemented
                        "voter_state_code":                 "",  # To be implemented
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
                # Augment the line with voter information
                friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    one_friend_invitation.recipient_voter_we_vote_id)  # The is the voter who received the invitation
                if friend_voter_results['voter_found']:
                    friend_voter = friend_voter_results['voter']
                    one_friend = {
                        "voter_we_vote_id":                 friend_voter.we_vote_id,
                        "voter_display_name":               friend_voter.get_full_name(),
                        "voter_photo_url":                  friend_voter.voter_photo_url(),
                        "voter_twitter_handle":             friend_voter.twitter_screen_name,
                        "voter_twitter_description":        "",  # To be implemented
                        "voter_twitter_followers_count":    0,  # To be implemented
                        "voter_state_code":                 "",  # To be implemented
                    }
                    friend_list.append(one_friend)
    else:
        status = kind_of_list_we_are_looking_for + " KIND_OF_LIST_NOT_IMPLEMENTED_YET"

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
        email_address_object_found = True
        email_address_object = email_results['email_address_object']
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
    create_results = friend_manager.create_or_update_friend_invitation_voter_link(
        sender_voter_we_vote_id, recipient_voter_we_vote_id, invitation_message)
    results = {
        'success':                  create_results['status'],
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
    create_results = friend_manager.create_or_update_friend_invitation_email_link(
        sender_voter_we_vote_id, recipient_email_we_vote_id,
        recipient_voter_email, invitation_message)
    results = {
        'success':                  create_results['success'],
        'status':                   create_results['status'],
        'friend_invitation_saved':  create_results['friend_invitation_saved'],
        'friend_invitation':        create_results['friend_invitation'],
    }

    return results
