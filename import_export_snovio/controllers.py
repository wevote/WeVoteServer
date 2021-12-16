# import_export_snovio/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import SnovIOApiCounterManager
from config.base import get_environment_variable
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import json
import requests
from voter.models import VoterContactEmail
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

SNOVIO_CLIENT_ID = get_environment_variable("SNOVIO_CLIENT_ID", no_exception=True)
SNOVIO_CLIENT_SECRET = get_environment_variable("SNOVIO_CLIENT_SECRET", no_exception=True)
SNOVIO_GET_PROFILE_BY_EMAIL_URL = "https://api.snov.io/v1/get-profile-by-email"


def augment_emails_for_voter_with_snovio(voter_we_vote_id=''):
    status = ''
    success = True

    from voter.models import VoterManager
    voter_manager = VoterManager()
    # Augment all voter contacts with data from SendGrid and SnovIO
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id)
    if voter_contact_results['voter_contact_email_list_found']:
        email_addresses_returned_list = voter_contact_results['email_addresses_returned_list']

        # Get list of emails which need to be augmented (updated) with data from SnovIO
        contact_email_augmented_list_as_dict = {}
        results = voter_manager.retrieve_contact_email_augmented_list(
            email_address_text_list=email_addresses_returned_list,
            read_only=False,
        )
        if results['contact_email_augmented_list_found']:
            # We retrieve all existing so we don't need 200 queries within update_or_create_contact_email_augmented
            contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']

        # Make sure we have an augmented entry for each email
        for email_address_text in email_addresses_returned_list:
            voter_manager.update_or_create_contact_email_augmented(
                email_address_text=email_address_text,
                existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict)

        # Get list of emails which need to be augmented (updated) with data from SnovIO
        results = voter_manager.retrieve_contact_email_augmented_list(
            checked_against_snovio_more_than_x_days_ago=15,
            email_address_text_list=email_addresses_returned_list,
            read_only=False,
        )
        if results['contact_email_augmented_list_found']:
            contact_email_augmented_list = results['contact_email_augmented_list']
            contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']
            email_addresses_returned_list = results['email_addresses_returned_list']
            email_addresses_remaining_list = email_addresses_returned_list

            # Now reach out to SnovIO, in blocks of 200
            failed_api_count = 0
            loop_count = 0
            safety_valve_triggered = False
            while len(email_addresses_remaining_list) > 0 and not safety_valve_triggered:
                loop_count += 1
                safety_valve_triggered = loop_count >= 250
                email_address_for_query = email_addresses_remaining_list[:1]
                email_addresses_remaining_list = \
                    list(set(email_addresses_remaining_list) - set(email_address_for_query))
                snovio_augmented_email_list_dict = {}
                email = email_address_for_query.pop()
                snovio_results = query_snovio_api_to_augment_email(email=email)
                if not snovio_results['success']:
                    failed_api_count += 1
                    if failed_api_count >= 3:
                        safety_valve_triggered = True
                        status += "SNOVIO_API_FAILED_3_TIMES "
                elif snovio_results['augmented_email_found']:
                    # A dict of results from SnovIO, with email_address_text as the key
                    snovio_augmented_email_list_dict = snovio_results['augmented_email_list_dict']

                    # Update our cached augmented data
                    for contact_email_augmented in contact_email_augmented_list:
                        if contact_email_augmented.email_address_text in snovio_augmented_email_list_dict:
                            augmented_email = \
                                snovio_augmented_email_list_dict[contact_email_augmented.email_address_text]
                            snovio_id = augmented_email['snovio_id'] \
                                if 'snovio_id' in augmented_email else None
                            snovio_locality = augmented_email['snovio_locality'] \
                                if 'snovio_locality' in augmented_email else None
                            snovio_source_state = augmented_email['snovio_source_state'] \
                                if 'snovio_source_state' in augmented_email else None
                            results = voter_manager.update_or_create_contact_email_augmented(
                                checked_against_snovio=True,
                                email_address_text=contact_email_augmented.email_address_text,
                                existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict,
                                snovio_id=snovio_id,
                                snovio_locality=snovio_locality,
                                snovio_source_state=snovio_source_state,
                            )
                            if results['success'] and positive_value_exists(snovio_source_state):
                                # Now update all of the VoterContactEmail entries, irregardless of whose contact it is
                                defaults = {
                                    'state_code': snovio_source_state,
                                }
                                try:
                                    number_updated = VoterContactEmail.objects.filter(
                                        email_address_text__iexact=contact_email_augmented.email_address_text) \
                                        .update(**defaults)
                                    status += "SNOVIO_NUMBER_OF_VOTER_CONTACT_EMAIL_UPDATED: " + str(number_updated) + " "
                                except Exception as e:
                                    status += "SNOVIO_NUMBER_OF_VOTER_CONTACT_EMAIL_NOT_UPDATED: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
    }
    return results


def get_access_token():
    params = {
        'grant_type': 'client_credentials',
        'client_id': SNOVIO_CLIENT_ID,
        'client_secret': SNOVIO_CLIENT_SECRET,
    }
    
    res = requests.post('https://api.snov.io/v1/oauth/access_token', data=params)
    resText = res.text.encode('ascii', 'ignore')
    
    return json.loads(resText)['access_token']


def query_snovio_api_to_augment_email(email=''):
    success = True
    status = ""
    augmented_email_dict = {}
    augmented_email_found = False
    json_from_snovio = {}

    if not positive_value_exists(email):
        status += "MISSING_EMAIL "
        success = False
        results = {
            'success': success,
            'status': status,
            'augmented_email_found':  augmented_email_found,
            'augmented_email_dict': augmented_email_dict,
        }
        return results

    try:
        # Get the ballot info at this address
        response = requests.post(
            SNOVIO_GET_PROFILE_BY_EMAIL_URL,
            data={
                "access_token": get_access_token(),
                "email": email,
            })
        json_from_snovio = json.loads(response.text)

        if 'errors' in json_from_snovio:
            status += "[" + json_from_snovio['errors'] + "] "

        # Use SnovIO API call counter to track the number of queries we are doing each day
        api_counter_manager = SnovIOApiCounterManager()
        api_counter_manager.create_counter_entry(
            'get-prospects-by-email',
            number_of_items_sent_in_query=1)
    except Exception as e:
        success = False
        status += 'QUERY_SNOVIO_EMAIL_SEARCH_API_FAILED: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)

    data_list = []
    if 'success' in json_from_snovio and positive_value_exists(json_from_snovio['success']):
        if 'data' in json_from_snovio:
            data_list = json_from_snovio['data']
        for snovio_profile in data_list:
            snovio_profile_id = snovio_profile['id']
            pass
            # augmented_email = json_from_snovio['']
            # email_address_text = augmented_email['vb.email_address']
            # if positive_value_exists(email_address_text):
            #     snovio_id = augmented_email['vb.voterbase_id']
            #     snovio_source_state = augmented_email['vb.vf_source_state']
            #     # Last voted?
            #     # Political party?
            #     # Full address so we can find their ballot?
            #     augmented_email_dict = {
            #         'email_address_text':       email_address_text,
            #         'snovio_id':           snovio_id,
            #         'snovio_source_state': snovio_source_state,
            #     }

    results = {
        'success': success,
        'status': status,
        'augmented_email_found': augmented_email_found,
        'augmented_email_dict': augmented_email_dict,
    }
    return results
