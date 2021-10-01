# import_export_targetsmart/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import TargetSmartApiCounterManager
from config.base import get_environment_variable
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import json
import requests
from voter.models import VoterContactEmail
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

TARGETSMART_API_KEY = get_environment_variable("TARGETSMART_API_KEY", no_exception=True)
TARGETSMART_EMAIL_SEARCH_URL = "https://api.targetsmart.com/person/email-search"
TARGETSMART_PHONE_SEARCH_URL = "https://api.targetsmart.com/person/phone-search"


def augment_emails_for_voter_with_targetsmart(voter_we_vote_id=''):
    status = ''
    success = True

    from voter.models import VoterManager
    voter_manager = VoterManager()
    # Augment all voter contacts with data from SendGrid and TargetSmart
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id)
    if voter_contact_results['voter_contact_email_list_found']:
        email_addresses_returned_list = voter_contact_results['email_addresses_returned_list']

        # Get list of emails which need to be augmented (updated) with data from TargetSmart
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

        # Get list of emails which need to be augmented (updated) with data from TargetSmart
        results = voter_manager.retrieve_contact_email_augmented_list(
            checked_against_targetsmart_more_than_x_days_ago=15,
            email_address_text_list=email_addresses_returned_list,
            read_only=False,
        )
        if results['contact_email_augmented_list_found']:
            contact_email_augmented_list = results['contact_email_augmented_list']
            contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']
            email_addresses_returned_list = results['email_addresses_returned_list']
            email_addresses_remaining_list = email_addresses_returned_list

            # Now reach out to TargetSmart, in blocks of 200
            failed_api_count = 0
            loop_count = 0
            safety_valve_triggered = False
            while len(email_addresses_remaining_list) > 0 and not safety_valve_triggered:
                loop_count += 1
                safety_valve_triggered = loop_count >= 250
                email_addresses_for_query = email_addresses_remaining_list[:200]
                email_addresses_remaining_list = \
                    list(set(email_addresses_remaining_list) - set(email_addresses_for_query))
                targetsmart_augmented_email_list_dict = {}
                targetsmart_results = query_targetsmart_api_to_augment_email_list(email_list=email_addresses_for_query)
                if not targetsmart_results['success']:
                    failed_api_count += 1
                    if failed_api_count >= 3:
                        safety_valve_triggered = True
                        status += "TARGET_SMART_API_FAILED_3_TIMES "
                elif targetsmart_results['augmented_email_list_found']:
                    # A dict of results from TargetSmart, with email_address_text as the key
                    targetsmart_augmented_email_list_dict = targetsmart_results['augmented_email_list_dict']

                    # Update our cached augmented data
                    for contact_email_augmented in contact_email_augmented_list:
                        if contact_email_augmented.email_address_text in targetsmart_augmented_email_list_dict:
                            augmented_email = \
                                targetsmart_augmented_email_list_dict[contact_email_augmented.email_address_text]
                            targetsmart_id = augmented_email['targetsmart_id'] \
                                if 'targetsmart_id' in augmented_email else None
                            targetsmart_source_state = augmented_email['targetsmart_source_state'] \
                                if 'targetsmart_source_state' in augmented_email else None
                            results = voter_manager.update_or_create_contact_email_augmented(
                                checked_against_targetsmart=True,
                                email_address_text=contact_email_augmented.email_address_text,
                                existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict,
                                targetsmart_id=targetsmart_id,
                                targetsmart_source_state=targetsmart_source_state,
                            )
                            if results['success']:
                                # Now update all of the VoterContactEmail entries, irregardless of whose contact it is
                                defaults = {
                                    'state_code': targetsmart_source_state,
                                }
                                number_updated = VoterContactEmail.objects.filter(
                                    email_address_text__iexact=contact_email_augmented.email_address_text) \
                                    .update(defaults)
                                status += "NUMBER_OF_VOTER_CONTACT_EMAIL_UPDATED: " + str(number_updated) + " "
    results = {
        'success': success,
        'status': status,
    }
    return results


def query_targetsmart_api_to_augment_email_list(email_list=[]):
    success = True
    status = ""
    augmented_email_list_dict = {}
    augmented_email_list_found = False
    json_from_targetsmart = {}

    if email_list is None or len(email_list) == 0:
        status += "MISSING_EMAIL_LIST "
        success = False
        results = {
            'success': success,
            'status': status,
            'augmented_email_list_found':  augmented_email_list_found,
            'augmented_email_list_dict': augmented_email_list_dict,
        }
        return results

    number_of_items_sent_in_query = len(email_list)

    try:
        api_key = TARGETSMART_API_KEY
        emails_param = ",".join(email_list)
        # Get the ballot info at this address
        response = requests.get(
            TARGETSMART_EMAIL_SEARCH_URL,
            headers={"x-api-key": api_key},
            params={
                "emails": emails_param,
            })
        json_from_targetsmart = json.loads(response.text)

        if 'message' in json_from_targetsmart:
            status += json_from_targetsmart['message'] + " "
            if json_from_targetsmart['message'].strip() in ['Failed', 'Forbidden']:
                success = False

        # Use TargetSmart API call counter to track the number of queries we are doing each day
        api_counter_manager = TargetSmartApiCounterManager()
        api_counter_manager.create_counter_entry(
            'email-search',
            number_of_items_sent_in_query=number_of_items_sent_in_query)
    except Exception as e:
        success = False
        status += 'QUERY_TARGETSMART_EMAIL_SEARCH_API_FAILED: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)

    if 'results' in json_from_targetsmart:
        results_list_from_targetsmart = json_from_targetsmart['results']
        for augmented_email in results_list_from_targetsmart:
            email_address_text = augmented_email['vb.email_address']
            if positive_value_exists(email_address_text):
                targetsmart_id = augmented_email['vb.voterbase_id']
                targetsmart_source_state = augmented_email['vb.vf_source_state']
                # Last voted?
                # Political party?
                # Full address so we can find their ballot?
                augmented_email_dict = {
                    'email_address_text':       email_address_text,
                    'targetsmart_id':           targetsmart_id,
                    'targetsmart_source_state': targetsmart_source_state,
                }
                augmented_email_list_dict[email_address_text.lower()] = augmented_email_dict

    results = {
        'success': success,
        'status': status,
        'augmented_email_list_found': augmented_email_list_found,
        'augmented_email_list_dict': augmented_email_list_dict,
    }
    return results
