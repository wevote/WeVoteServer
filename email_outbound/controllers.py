# email_outbound/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from email_outbound.models import EmailManager
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_email_address_retrieve_for_api(voter_device_id):
    """
    voterEmailAddressRetrieve
    :param voter_device_id:
    :return:
    """
    email_address_list_found = False
    status = ""
    success = True

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                           device_id_results['status'],
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                           "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    email_address_list_augmented = []
    email_results = email_manager.retrieve_voter_email_address_list(voter_we_vote_id)
    primary_email_address_found = False
    status += email_results['status']
    if email_results['email_address_list_found']:
        email_address_list_found = True
        email_address_list = email_results['email_address_list']

        for email_address in email_address_list:
            is_primary_email_address = False
            if email_address.we_vote_id == voter.primary_email_we_vote_id:
                is_primary_email_address = True
                primary_email_address_found = True
                primary_email_address = email_address
            elif email_address.normalized_email_address == voter.email:
                is_primary_email_address = True
                primary_email_address_found = True
                primary_email_address = email_address
            email_address_for_json = {
                'normalized_email_address': email_address.normalized_email_address,
                'primary_email_address': is_primary_email_address,
                'email_permanent_bounce': email_address.email_permanent_bounce,
                'email_ownership_is_verified': email_address.email_ownership_is_verified,
                'voter_we_vote_id': email_address.voter_we_vote_id,
                'email_we_vote_id': email_address.we_vote_id,
            }
            email_address_list_augmented.append(email_address_for_json)

        if primary_email_address_found:
            # Make sure the voter's cached "email" and "primary_email_we_vote_id" are both correct and match same email
            voter_data_updated = False
            if voter.primary_email_we_vote_id.lower != primary_email_address.we_vote_id.lower:
                voter.primary_email_we_vote_id = primary_email_address.we_vote_id
                voter_data_updated = True
            if voter.email.lower != primary_email_address.normalized_email_address.lower:
                voter.email = primary_email_address.normalized_email_address
                voter_data_updated = True

            if voter_data_updated:
                try:
                    voter.save()
                    status += "SAVED_UPDATED_EMAIL_VALUES"
                except Exception as e:
                    # TODO DALE We could get this exception if the EmailAddress table has email X for voter 1
                    # and the voter table stores the same email X for voter 2
                    status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES"
        else:
            # If here we need to heal data. If here we know that the voter record doesn't have any email info
            for primary_email_address_candidate in email_address_list:
                if primary_email_address_candidate.email_ownership_is_verified:
                    # Now that we have found a verified email, save it to the voter account, and break out of loop
                    voter.primary_email_we_vote_id = primary_email_address_candidate.we_vote_id
                    voter.email = primary_email_address_candidate.normalized_email_address
                    voter.email_ownership_is_verified = True
                    try:
                        voter.save()
                        status += "SAVED_PRIMARY_EMAIL_ADDRESS_CANDIDATE"
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_PRIMARY_EMAIL_ADDRESS_CANDIDATE"
                    break

    json_data = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'email_address_list_found':         email_address_list_found,
        'email_address_list':               email_address_list_augmented,
    }
    return json_data


def voter_email_address_save_for_api(voter_device_id, text_for_email_address, email_we_vote_id, make_primary_email):
    """
    voterEmailAddressSave
    :param voter_device_id:
    :param text_for_email_address:
    :param email_we_vote_id:
    :param make_primary_email:
    :return:
    """
    email_address_list_found = False
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                           device_id_results['status'],
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           "",
            'email_address_saved_we_vote_id':   "",
            'email_address_created':            False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                           "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           "",
            'email_address_saved_we_vote_id':   "",
            'email_address_created':            False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    email_address_list_augmented = []
    email_results = email_manager.retrieve_voter_email_address_list(voter_we_vote_id)
    if email_results['email_address_list_found']:
        email_address_list_found = True
        email_address_list = email_results['email_address_list']

        for email_address in email_address_list:
            email_address_list_augmented.append(email_address)

    json_data = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'text_for_email_address':           text_for_email_address,
        'email_address_saved_we_vote_id':   "",
        'email_address_created':            False,
        'email_address_found':              False,
        'email_address_list_found':         email_address_list_found,
        'email_address_list':               [],
    }
    return json_data
