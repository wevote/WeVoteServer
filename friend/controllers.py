# friend/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FriendManager
from config.base import get_environment_variable
import copy
from email_outbound.models import EmailManager
from exception.models import handle_record_found_more_than_one_exception
from position.models import PositionManager, PERCENT_RATING
import requests
from voter.models import BALLOT_ADDRESS, fetch_voter_id_from_voter_device_link, Voter, VoterAddressManager, \
    VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, generate_voter_device_id, is_voter_device_id_valid, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def friend_invitation_by_email_send_for_api(voter_device_id, email_addresses_raw, invitation_message):
    success = False
    status = ""

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status': results['status'],
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_email_address_missing': True
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                       "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'voter_email_address_missing':  True
        }
        return error_results

    voter = voter_results['voter']
    voter_email_address_missing = not voter.has_valid_email()
    if not positive_value_exists(voter_email_address_missing):
        error_results = {
            'status':                       "VOTER_DOES_NOT_HAVE_VALID_EMAIL",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'voter_email_address_missing':  True
        }
        return error_results

    # Break apart all of the emails in email_addresses_raw
    friend_email_list = []

    # Check to see if we recognize any of these emails
    friend_manager = FriendManager()
    email_manager = EmailManager()
    for one_normalized_raw_email in friend_email_list:
        voter_friend_found = False
        voter_friend = Voter()
        current_voter_using_unlinked_email = False
        current_voter_using_linked_email = False
        email_linked_to_missing_voter = False

        email_results = email_manager.retrieve_email_address(one_normalized_raw_email)

        if email_results['email_found']:
            # We recognize the email
            email_address_entry_to_be_created = False
            # Is the email already connected to an existing voter?
            if email_results['voter_we_vote_id']:
                voter_friend_results = voter_manager.retrieve_voter_by_we_vote_id(email_results['voter_we_vote_id'])
                if voter_friend_results['voter_found']:
                    current_voter_using_linked_email = True
                else:
                    email_linked_to_missing_voter = True
        else:
            email_address_entry_to_be_created = True

            # Before we create a new EmailAddress entry, we want to see if any voters currently use this email
            voter_by_email_results = voter_manager.retrieve_voter_by_email(one_normalized_raw_email)

            # If voter is using this email
            if voter_by_email_results['voter_found']:
                current_voter_using_unlinked_email = True

        if current_voter_using_linked_email:
            # The simplest case
            pass
        elif email_linked_to_missing_voter:
            # Remove the voter_we_vote_id from EmailAddress

            # Check to make sure the email isn't in use with another voter
            voter_by_email_results = voter_manager.retrieve_voter_by_email(one_normalized_raw_email)

            # If voter is using this email
            if voter_by_email_results['voter_found']:
                current_voter_using_unlinked_email = True

            pass

        if current_voter_using_unlinked_email:
            # Link the email to that voter
            if email_address_entry_to_be_created:
                # Create the EmailAddress entry
                pass
            else:
                # We have the existing EmailAddress entry
                pass
            # Link the email_address and voter

        # Create EmailAddress entry for existing voter
        voter_friend_found = True
        voter_friend = voter_by_email_results['voter']
        email_results = email_manager.create_email_address_for_voter(one_normalized_raw_email, voter_friend)

        if email_results['email_found']:
            # We recognize the email
            # Is the email already connected to an existing voter?
            if email_results['voter_we_vote_id']:
                voter_friend_results = voter_manager.retrieve_voter_by_we_vote_id(email_results['voter_we_vote_id'])
                if voter_friend_results['voter_found']:
                    voter_friend = voter_friend_results['voter']
                    voter_friend_found = True
                else:
                    # If here we have a problem -- the we_vote_id we have for a voter didn't return the voter
                    pass
            else:
                # If here, we recognize the email, but it isn't linked to an existing voter
                # Heal the data
                voter_by_email_results = voter_manager.retrieve_voter_by_email(one_normalized_raw_email)
                if voter_by_email_results['voter_found']:
                    # Create EmailAddress entry for existing voter
                    voter_friend_found = True
                    voter_friend = voter_by_email_results['voter']
                    email_results = email_manager.create_email_address_for_voter(one_normalized_raw_email, voter_friend)

            if voter_friend_found:
                # If here, we have a record for one_normalized_raw_email
                results = friend_manager.create_friend_invitation_with_two_voters(voter, voter_friend)
            else:
                #
                pass
        else:
            # If here, we know that one_normalized_raw_email is not recognized
            results = friend_manager.create_friend_invitation_with_unknown_email(voter, one_normalized_raw_email,
                                                                                 new_email_we_vote_id)



    results = email_manager.create_email_outbound_description()

    # results = friend_manager.create_friend_invitation(voter, email_addresses_raw, invitation_message)

    # Break out useful email addresses from email_addresses_raw

    results = {
        'success':                      success,
        'status':                       status,
        'voter_device_id':              voter_device_id,
        'voter_email_address_missing':  voter_email_address_missing,
    }
    return results
