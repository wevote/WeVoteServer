# import_export_targetsmart/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import TargetSmartApiCounterManager
from config.base import get_environment_variable
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import json
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

TARGETSMART_API_KEY = get_environment_variable("TARGETSMART_API_KEY", no_exception=True)
TARGETSMART_EMAIL_SEARCH_URL = "https://api.targetsmart.com/person/email-search"
TARGETSMART_PHONE_SEARCH_URL = "https://api.targetsmart.com/person/phone-search"


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
