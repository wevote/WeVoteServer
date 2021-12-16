# import_export_open_people/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import OpenPeopleApiCounterManager
from config.base import get_environment_variable
from concurrent.futures import ThreadPoolExecutor, as_completed
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import json
import requests
from requests.structures import CaseInsensitiveDict
from voter.controllers_contacts import assemble_contact_display_name
from voter.models import VoterContactEmail
import wevote_functions.admin
from wevote_functions.functions import convert_state_text_to_state_code, convert_to_int, \
    display_city_with_correct_capitalization, display_full_name_with_correct_capitalization, \
    generate_date_as_integer, positive_value_exists
from wevote_settings.models import WeVoteSetting, WeVoteSettingsManager

logger = wevote_functions.admin.get_logger(__name__)

OPEN_PEOPLE_USERNAME = get_environment_variable("OPEN_PEOPLE_USERNAME", no_exception=True)
OPEN_PEOPLE_PASSWORD = get_environment_variable("OPEN_PEOPLE_PASSWORD", no_exception=True)


def augment_emails_for_voter_with_open_people(voter_we_vote_id=''):
    status = ''
    success = True
    email_not_found_list = []

    api_counter_manager = OpenPeopleApiCounterManager()
    from voter.models import VoterManager
    voter_manager = VoterManager()
    # Augment all voter contacts with data from Open People
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id)
    if not voter_contact_results['voter_contact_email_list_found']:
        status += "NO_EMAILS_TO_AUGMENT "
        results = {
            'success': success,
            'status': status,
        }
        return results

    email_addresses_returned_list = voter_contact_results['email_addresses_returned_list']

    # Note: We rely on email_outbound/controller.py augment_emails_for_voter_with_we_vote_data having
    #  created a contact_email_augmented entry for every one of these emails previously

    # #########
    # Get list of emails which need to be augmented (updated) with data from Open People
    results = voter_manager.retrieve_contact_email_augmented_list(
        checked_against_open_people_more_than_x_days_ago=30,
        email_address_text_list=email_addresses_returned_list,
        read_only=False,
    )
    contact_email_augmented_list = results['contact_email_augmented_list']
    contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']
    email_addresses_returned_list = results['email_addresses_returned_list']
    email_addresses_remaining_list = email_addresses_returned_list

    # If we need to make a query, get or generate an updated access token
    open_people_authentication_token = ''
    if len(email_addresses_remaining_list) > 0:
        open_people_authentication_token = fetch_open_people_authentication_token()

    if len(email_addresses_remaining_list) == 0:
        status += "NO_MORE_EMAILS_TO_CHECK_AGAINST_OPEN_PEOPLE "
    elif not positive_value_exists(open_people_authentication_token):
        status += "VALID_OPEN_PEOPLE_AUTHENTICATION_TOKEN_NOT_FOUND "
        print(status)
    else:
        # Now reach out to Open People, with outer limit of 2000, but in blocks of 100 which must complete
        #  and be saved before the next block of 100 is started
        failed_api_count = 0
        loop_count = 0
        safety_valve_triggered = False
        number_of_outer_loop_executions_allowed = 40  # 2000 total = 40 loops * 50 number_executed_per_block
        number_executed_per_block = 50
        while len(email_addresses_remaining_list) > 0 and not safety_valve_triggered:
            loop_count += 1
            safety_valve_triggered = loop_count >= number_of_outer_loop_executions_allowed
            email_address_list_chunk = email_addresses_remaining_list[:number_executed_per_block]
            email_addresses_remaining_list = list(set(email_addresses_remaining_list) - set(email_address_list_chunk))

            if len(email_address_list_chunk) == 0:
                break

            open_people_results = query_open_people_email_from_list(
                email_list=email_address_list_chunk,
                authentication_token=open_people_authentication_token)
            number_of_items_sent_in_query = open_people_results['number_of_items_sent_in_query']
            if not open_people_results['success']:
                failed_api_count += 1
                if failed_api_count >= 3:
                    safety_valve_triggered = True
                    status += "OPEN_PEOPLE_API_FAILED_3_TIMES "
                if failed_api_count == 3:
                    print(status)
            elif open_people_results['email_results_found']:
                # A dict of results from Open People, with lowercase email_address_text as the key
                email_results_dict = open_people_results['email_results_dict']
                # print(email_results_dict)
                # Update our cached augmented data
                for contact_email_augmented in contact_email_augmented_list:
                    if contact_email_augmented.email_address_text in email_results_dict:
                        open_people_data = email_results_dict[contact_email_augmented.email_address_text]
                        augmented_email_found = open_people_data['augmented_email_found'] \
                            if 'augmented_email_found' in open_people_data else False
                        if augmented_email_found:
                            city = open_people_data['city'] if 'city' in open_people_data else None
                            first_name = open_people_data['first_name'] if 'first_name' in open_people_data else None
                            last_name = open_people_data['last_name'] if 'last_name' in open_people_data else None
                            middle_name = open_people_data['middle_name'] if 'middle_name' in open_people_data else None
                            state = open_people_data['state'] if 'state' in open_people_data else None
                            if positive_value_exists(state):
                                state_code = convert_state_text_to_state_code(state)
                            else:
                                state_code = None
                            zip_code = open_people_data['zip_code'] if 'zip_code' in open_people_data else None
                            results = voter_manager.update_or_create_contact_email_augmented(
                                checked_against_open_people=True,
                                email_address_text=contact_email_augmented.email_address_text,
                                existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict,
                                open_people_city=city,
                                open_people_first_name=first_name,
                                open_people_last_name=last_name,
                                open_people_middle_name=middle_name,
                                open_people_state_code=state_code,
                                open_people_zip_code=zip_code,
                            )
                            if not results['success']:
                                status += results['status']
                        else:
                            email_not_found_list.append(contact_email_augmented.email_address_text)
            else:
                email_not_found_list = list(set(email_not_found_list + email_address_list_chunk))

            # Use Open People API call counter to track the number of queries we are doing each day
            if positive_value_exists(number_of_items_sent_in_query):
                api_counter_manager.create_counter_entry(
                    'EmailAddressSearch',
                    number_of_items_sent_in_query=number_of_items_sent_in_query)

            # Mark as checked all of the email addresses where augmentation wasn't found
            email_not_found_list_unique = list(set(email_not_found_list))
            if len(email_not_found_list_unique) > 0:
                results = voter_manager.update_contact_email_augmented_list_not_found(
                    checked_against_open_people=True,
                    email_address_text_list=email_not_found_list_unique,
                )
                status += results['status']

    # #########
    # Finally, retrieve all of the augmented data we have collected and update VoterContactEmail entries
    results = voter_manager.retrieve_contact_email_augmented_list(
        email_address_text_list=email_addresses_returned_list,
        read_only=True,
    )
    if results['success'] and results['contact_email_augmented_list_found']:
        contact_email_augmented_list = results['contact_email_augmented_list']
        for contact_email_augmented in contact_email_augmented_list:
            city = contact_email_augmented.open_people_city
            city = display_city_with_correct_capitalization(city)
            first_name = contact_email_augmented.open_people_first_name
            last_name = contact_email_augmented.open_people_last_name
            middle_name = contact_email_augmented.open_people_middle_name
            state_code = contact_email_augmented.open_people_state_code
            zip_code = contact_email_augmented.open_people_zip_code

            contact_name_data_found = positive_value_exists(first_name) or \
                positive_value_exists(last_name) or \
                positive_value_exists(middle_name)
            location_data_found = positive_value_exists(city) or \
                positive_value_exists(state_code) or \
                positive_value_exists(zip_code)
            defaults = {}
            if city is not None:
                defaults['city'] = city
            if first_name is not None:
                defaults['first_name'] = first_name
            if last_name is not None:
                defaults['last_name'] = last_name
            if middle_name is not None:
                defaults['middle_name'] = middle_name
            if state_code is not None:
                defaults['state_code'] = state_code
            if zip_code is not None:
                defaults['zip_code'] = zip_code
            if contact_name_data_found:
                display_name_raw = assemble_contact_display_name(
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name)
                # if display_name_raw is all caps, correct the capitalization
                if display_name_raw.isupper() or display_name_raw.islower():
                    defaults['display_name'] = display_full_name_with_correct_capitalization(display_name_raw)
                else:
                    defaults['display_name'] = display_name_raw
            # Now update all of the VoterContactEmail entries, regardless of whose contact it is
            if location_data_found or contact_name_data_found:
                try:
                    number_updated = VoterContactEmail.objects.filter(
                        email_address_text__iexact=contact_email_augmented.email_address_text) \
                        .update(**defaults)
                    status += "NUMBER_OF_VOTER_CONTACT_EMAIL_UPDATED: " + str(number_updated) + " "
                except Exception as e:
                    status += "NUMBER_OF_VOTER_CONTACT_EMAIL_NOT_UPDATED: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
    }
    return results


def fetch_open_people_authentication_token():
    we_vote_settings_manager = WeVoteSettingsManager()
    authentication_token = ''

    expire_date_as_integer = we_vote_settings_manager.fetch_setting('open_people_expire_date_as_integer')
    if positive_value_exists(expire_date_as_integer):
        date_now_as_integer = generate_date_as_integer()
        if expire_date_as_integer > date_now_as_integer:
            authentication_token = we_vote_settings_manager.fetch_setting('open_people_authentication_token')

    if not positive_value_exists(authentication_token):
        response_dict = query_open_people_for_authentication_token()
        authentication_token = response_dict['token'] if 'token' in response_dict else ''
        token_expiry_utc = response_dict['token_expiry_utc'] if 'token_expiry_utc' in response_dict else ''
        expire_date_string = token_expiry_utc[:10]
        date_as_string = expire_date_string.replace('-', '')
        date_as_integer = convert_to_int(date_as_string)
        if positive_value_exists(date_as_integer):
            we_vote_settings_manager.save_setting(
                'open_people_expire_date_as_integer',
                date_as_integer,
                value_type=WeVoteSetting.INTEGER)
            we_vote_settings_manager.save_setting(
                'open_people_authentication_token',
                authentication_token,
                value_type=WeVoteSetting.STRING)

    return authentication_token


def query_open_people_email_search(email='', authentication_token=''):
    headers = CaseInsensitiveDict()
    headers["accept"] = "text/plain"
    headers["Authorization"] = "Bearer " + authentication_token
    headers["Content-Type"] = "application/json"

    data = '{"emailAddress":"' + email + '"}'
    response = requests.post(
        "https://api.openpeoplesearch.com/api/v1/Consumer/EmailAddressSearch",
        headers=headers,
        data=data,
    )
    structured_json = json.loads(response.text)
    # print(structured_json)

    return structured_json


def query_open_people_for_authentication_token():
    headers = CaseInsensitiveDict()
    headers["accept"] = "*/*"
    headers["Content-Type"] = "application/json"

    data = '{"username":"' + OPEN_PEOPLE_USERNAME + '","password":"' + OPEN_PEOPLE_PASSWORD + '"}'
    response = requests.post(
        "https://api.openpeoplesearch.com/api/v1/User/authenticate",
        headers=headers,
        data=data,
    )
    structured_json = json.loads(response.text)

    return structured_json


def query_open_people_phone_search(phone_number='', authentication_token=''):
    headers = CaseInsensitiveDict()
    headers["accept"] = "text/plain"
    headers["Authorization"] = 'Bearer {authentication_token}'.format(authentication_token=authentication_token)
    headers["Content-Type"] = "application/json"

    response = requests.post(
        'https://api.openpeoplesearch.com/api/v1/Consumer/PhoneSearch',
        headers=headers,
        data={
            'phoneNumber': phone_number,
        },
    )
    structured_json = json.loads(response.text)

    return structured_json


def query_open_people_email_from_list(email_list=[], authentication_token=''):
    success = True
    status = ""
    email_results_dict = {}
    email_results_found = False
    number_of_items_sent_in_query = 0

    if not len(email_list) > 0:
        status += "MISSING_EMAIL_LIST "
        success = False
        results = {
            'success':                          success,
            'status':                           status,
            'email_results_found':              email_results_found,
            'email_results_dict':               email_results_dict,
            'number_of_items_sent_in_query':    number_of_items_sent_in_query,
        }
        return results

    # Linear for testing
    # for one_email in email_list:
    #     one_result = {}
    #     number_of_items_sent_in_query += 1
    #     try:
    #         one_result = query_and_extract_from_open_people_email_address_search(
    #             email=one_email,
    #             authentication_token=authentication_token)
    #         email_address = one_result['email_address_text']
    #         email_address = email_address.lower()
    #         email_results_dict[email_address] = one_result
    #         if one_result['augmented_email_found']:
    #             email_results_found = True
    #     except Exception as e:
    #         status += one_result['status'] if 'status' in one_result else ''
    #         status += "CRASHING_ERROR: " + str(e) + ' '

    # Multi-thread for production
    threads = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for email in email_list:
            threads.append(executor.submit(query_and_extract_from_open_people_email_address_search,
                                           email, authentication_token))
            number_of_items_sent_in_query += 1

        for task in as_completed(threads):
            try:
                one_result = task.result()
                # print(one_result)
                email_address = one_result['email_address_text']
                email_address = email_address.lower()
                email_results_dict[email_address] = one_result
                if one_result['augmented_email_found']:
                    email_results_found = True
            except Exception as e:
                status += one_result['status'] if 'status' in one_result else ''
                status += "CRASHING_ERROR: " + str(e) + ' '

    results = {
        'success':                          success,
        'status':                           status,
        'email_results_found':              email_results_found,
        'email_results_dict':               email_results_dict,
        'number_of_items_sent_in_query':    number_of_items_sent_in_query,
    }
    return results


def query_and_extract_from_open_people_email_address_search(email='', authentication_token=''):
    success = True
    status = ""
    address_dict_with_highest_score = {}
    augmented_email_found = False
    json_from_open_people = {}
    name_dict_with_highest_score = {}

    if not positive_value_exists(email):
        status += "MISSING_EMAIL "
        success = False
        results = {
            'success':                  success,
            'status':                   status,
            'augmented_email_found':    augmented_email_found,
            'city':                     None,
            'email_address_text':       email,
            'state':                    None,
            'zip_code':                 None,
        }
        return results

    try:
        json_from_open_people = query_open_people_email_search(email=email, authentication_token=authentication_token)

        if 'errors' in json_from_open_people:
            status += "[" + json_from_open_people['errors'] + "] "
    except Exception as e:
        success = False
        status += 'QUERY_OPEN_PEOPLE_EMAIL_SEARCH_API_FAILED: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)

    number_of_records_found = json_from_open_people['records'] if 'records' in json_from_open_people else 0
    results_list = json_from_open_people['results'] if 'results' in json_from_open_people else []
    index_number = 0
    addresses_dict = {}
    most_recent_address_date = 0
    most_recent_address_dict = {}
    most_recent_name_date = 0
    most_recent_name_dict = {}
    names_dict = {}
    for open_people_profile in results_list:
        reported_date = open_people_profile['reportedDate'] if 'reportedDate' in open_people_profile else ''
        reported_date_as_string = reported_date[:10]
        reported_date_as_string = reported_date_as_string.replace('-', '')
        reported_date_as_integer = convert_to_int(reported_date_as_string)

        # Possible name (set) - firstName, middleName, lastName
        first_name = open_people_profile['firstName'] if 'firstName' in open_people_profile else None
        middle_name = open_people_profile['middleName'] if 'middleName' in open_people_profile else None
        last_name = open_people_profile['lastName'] if 'lastName' in open_people_profile else None
        if first_name and last_name:
            augmented_email_found = True
            name_dict = {
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
            }
            names_dict[index_number] = name_dict
            if reported_date_as_integer > most_recent_name_date:
                most_recent_name_date = reported_date_as_integer
                most_recent_name_dict = name_dict

        # Possible address (set) - city, state, zip
        city = open_people_profile['city'] if 'city' in open_people_profile else None
        state = open_people_profile['state'] if 'state' in open_people_profile else None
        zip_code = open_people_profile['zip'] if 'zip' in open_people_profile else None
        if city or state:
            augmented_email_found = True
            address_dict = {
                'city': city,
                'state': state,
                'zip_code': zip_code,
            }
            addresses_dict[index_number] = address_dict
            if reported_date_as_integer > most_recent_address_date:
                most_recent_address_date = reported_date_as_integer
                most_recent_address_dict = address_dict

        # Possible phone - phone

        index_number += 1

    if augmented_email_found:
        # Address with higher score is...
        address_dict_with_highest_score = most_recent_address_dict
        name_dict_with_highest_score = most_recent_name_dict
        print(json_from_open_people)

    results = {
        'success':                  success,
        'status':                   status,
        'augmented_email_found':    augmented_email_found,
        'email_address_text':       email,
        'city': address_dict_with_highest_score['city'] if 'city' in address_dict_with_highest_score else None,
        'first_name':
            name_dict_with_highest_score['first_name'] if 'first_name' in name_dict_with_highest_score else None,
        'last_name':
            name_dict_with_highest_score['last_name'] if 'last_name' in name_dict_with_highest_score else None,
        'middle_name':
            name_dict_with_highest_score['middle_name'] if 'middle_name' in name_dict_with_highest_score else None,
        'state': address_dict_with_highest_score['state'] if 'state' in address_dict_with_highest_score else None,
        'zip_code':
            address_dict_with_highest_score['zip_code'] if 'zip_code' in address_dict_with_highest_score else None,
    }
    return results
