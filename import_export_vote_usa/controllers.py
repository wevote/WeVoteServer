# import_export_vote_usa/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoteUSAApiCounterManager
from ballot.models import BallotReturnedManager
from candidate.models import PROFILE_IMAGE_TYPE_UNKNOWN, PROFILE_IMAGE_TYPE_VOTE_USA
from config.base import get_environment_variable
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from image.controllers import cache_master_and_resized_image, IMAGE_SOURCE_VOTE_USA
from import_export_batches.controllers_vote_usa import store_vote_usa_json_response_to_import_batch_system
import json
from polling_location.models import KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR, KIND_OF_LOG_ENTRY_API_END_POINT_CRASH, \
    KIND_OF_LOG_ENTRY_BALLOT_RECEIVED, KIND_OF_LOG_ENTRY_NO_CONTESTS, KIND_OF_LOG_ENTRY_NO_BALLOT_JSON, \
    PollingLocationManager
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

VOTE_USA_API_KEY = get_environment_variable("VOTE_USA_API_KEY", no_exception=True)
VOTE_USA_ELECTION_QUERY_URL = "https://vote-usa.org/api/v1.asmx/electionQuery"
VOTE_USA_VOTER_INFO_URL = "https://vote-usa.org/api/v1.asmx/voterInfoQuery"
VOTE_USA_VOTER_INFO_QUERY_TYPE = "voterinfo"

HEADERS_FOR_VOTE_USA_API_CALL = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0',
}


def retrieve_and_store_vote_usa_candidate_photo(candidate):
    success = True
    status = ''

    cache_results = cache_master_and_resized_image(
        candidate_id=candidate.id,
        candidate_we_vote_id=candidate.we_vote_id,
        photo_url_from_vote_usa=candidate.photo_url_from_vote_usa,
        image_source=IMAGE_SOURCE_VOTE_USA)
    vote_usa_profile_image_url_https = cache_results['cached_vote_usa_profile_image_url_https']
    we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
    we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
    we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

    candidate.vote_usa_profile_image_url_https = vote_usa_profile_image_url_https
    candidate.we_vote_hosted_profile_vote_usa_image_url_large = we_vote_hosted_profile_image_url_large
    candidate.we_vote_hosted_profile_vote_usa_image_url_medium = we_vote_hosted_profile_image_url_medium
    candidate.we_vote_hosted_profile_vote_usa_image_url_tiny = we_vote_hosted_profile_image_url_tiny

    if candidate.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
        candidate.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_VOTE_USA
    if candidate.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_VOTE_USA:
        candidate.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
        candidate.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
        candidate.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny

    try:
        candidate.save()
        status += "CANDIDATE_SAVED "
    except Exception as e:
        success = False
        status += "CANDIDATE_NOT_SAVED: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
        'candidate': candidate,
    }
    return results


def retrieve_from_vote_usa_api_election_query():
    logger.info("Loading json data from Vote USA servers, API call electionQuery")
    print("Loading json data from Vote USA servers, API call electionQuery")

    if not positive_value_exists(VOTE_USA_ELECTION_QUERY_URL):
        results = {
            'success':  False,
            'status':   'VOTE_USA_ELECTION_QUERY_URL missing ',
        }
        return results

    response = requests.get(
        VOTE_USA_ELECTION_QUERY_URL,
        headers=HEADERS_FOR_VOTE_USA_API_CALL,
        params={
            "accessKey": VOTE_USA_API_KEY,
        })

    # Use API call counter to track the number of queries we are doing each day
    api_counter_manager = VoteUSAApiCounterManager()
    api_counter_manager.create_counter_entry('election')

    structured_json = json.loads(response.text)
    if 'success' in structured_json and structured_json['success'] is False:
        results = {
            'success': False,
            'status': "Error: " + structured_json['status'],
        }
    else:
        results = {
            'structured_json':  structured_json,
            'success':          True,
            'status':           'structured_json retrieved',
        }
    return results


def retrieve_vote_usa_ballot_items_for_one_voter_api(
        google_civic_election_id,
        election_day_text="",
        ballot_returned=None,
        state_code=""):
    """
    We are telling the server to explicitly reach out to the Vote USA API and retrieve the ballot items
    for this voter.
    """
    status = ""
    success = True
    ballot_items_count = 0
    ballot_returned_we_vote_id = ''
    try:
        latitude = ballot_returned.latitude
        longitude = ballot_returned.longitude
        text_for_map_search = ballot_returned.text_for_map_search
        voter_id = ballot_returned.voter_id
    except Exception as e:
        status += "FAILED_TO_GET_VALUES_FROM_BALLOT_RETURNED: " + str(e) + " "
        success = False
        latitude = 0.0
        longitude = 0.0
        text_for_map_search = ''
        voter_id = 0

    if not positive_value_exists(VOTE_USA_VOTER_INFO_URL):
        status += 'NO VOTE_USA_API_SAMPLE_BALLOT_ELECTIONS_URL '
        success = False

    if not success:
        results = {
            'status':                       status,
            'success':                      False,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   "",
            'election_day_text':            "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'original_text_city':           '',
            'original_text_state':          '',
            'original_text_zip':            '',
            'polling_location_retrieved':   False,
            'ballot_returned_found':        False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    # ######
    # ############
    try:
        api_key = VOTE_USA_API_KEY
        # Get the ballot info at this address
        response = requests.get(
            VOTE_USA_VOTER_INFO_URL,
            headers=HEADERS_FOR_VOTE_USA_API_CALL,
            params={
                "accessKey": api_key,
                "electionDay": election_day_text,
                "latitude": latitude,
                "longitude": longitude,
                "state": state_code,
            })
        one_ballot_json = json.loads(response.text)
    except Exception as e:
        one_ballot_json = {}
        success = False
        status += 'VOTE_USA_API_END_POINT_CRASH: ' + str(e) + ' '
        log_entry_message = status

    ballot_returned_found = False
    try:
        # Use Vote USA API call counter to track the number of queries we are doing each day
        api_counter_manager = VoteUSAApiCounterManager()
        api_counter_manager.create_counter_entry(
            VOTE_USA_VOTER_INFO_QUERY_TYPE,
            google_civic_election_id=google_civic_election_id)

        if 'contests' in one_ballot_json:
            update_or_create_rules = {
                'create_candidates': True,
                'create_offices': True,
                'create_measures': True,
                'update_candidates': False,
                'update_offices': False,
                'update_measures': False,
            }
            from import_export_google_civic.controllers import groom_and_store_google_civic_ballot_json_2021
            groom_results = groom_and_store_google_civic_ballot_json_2021(
                one_ballot_json,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                voter_id=voter_id,
                election_day_text=election_day_text,
                # existing_offices_by_election_dict=existing_offices_by_election_dict,
                # existing_candidate_objects_dict=existing_candidate_objects_dict,
                # existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                # existing_measure_objects_dict=existing_measure_objects_dict,
                # new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                # new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                # new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                update_or_create_rules=update_or_create_rules,
                use_vote_usa=True,
                )
            success = groom_results['success']
            status += groom_results['status']
            ballot_item_dict_list = groom_results['ballot_item_dict_list']

            ballot_returned_manager = BallotReturnedManager()
            ballot_items_count = len(ballot_item_dict_list)
            results = ballot_returned_manager.retrieve_ballot_returned_from_voter_id(
                voter_id=voter_id,
                google_civic_election_id=google_civic_election_id,
            )
            status += results['status']
            if results['ballot_returned_found']:
                status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-VOTE_USA-SUCCESS "
                ballot_returned = results['ballot_returned']
                ballot_returned_we_vote_id = ballot_returned.we_vote_id
                ballot_returned_found = True
            else:
                status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-VOTE_USA-BALLOT_RETURNED_FOUND-FALSE "

            from import_export_google_civic.controllers import store_ballot_item_dict_list
            results = store_ballot_item_dict_list(
                ballot_item_dict_list=ballot_item_dict_list,
                google_civic_election_id=google_civic_election_id,
                voter_id=voter_id,
                state_code=state_code
            )
    except Exception as e:
        success = False
        status += 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS_API_V4-VOTE_USA-ERROR: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'status': status,
        'success': success,
        'google_civic_election_id': google_civic_election_id,
        'state_code': state_code,
        'election_day_text': election_day_text,
        'election_description_text': "",
        'election_data_retrieved': bool(ballot_items_count),
        'text_for_map_search': text_for_map_search,
        'original_text_city': '',
        'original_text_state': '',
        'original_text_zip': '',
        'polling_location_retrieved': False,
        'ballot_returned_found': ballot_returned_found,
        'ballot_location_display_name': "",
        'ballot_location_shortcut': "",
        'ballot_returned': ballot_returned,
        'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
    }
    return results


def retrieve_vote_usa_ballot_items_from_polling_location_api(
        google_civic_election_id=0,
        election_day_text="",
        polling_location_we_vote_id="",
        polling_location=None,
        state_code="",
        batch_process_id=0,
        batch_set_id=0,
        existing_offices_by_election_dict={},
        existing_candidate_objects_dict={},
        existing_candidate_to_office_links_dict={},
        existing_measure_objects_dict={},
        new_office_we_vote_ids_list=[],
        new_candidate_we_vote_ids_list=[],
        new_measure_we_vote_ids_list=[],
        update_or_create_rules={}):
    """

    :param google_civic_election_id:
    :param election_day_text:
    :param polling_location_we_vote_id:
    :param polling_location:
    :param state_code:
    :param batch_process_id:
    :param batch_set_id:
    :param existing_offices_by_election_dict:
    :param existing_candidate_objects_dict:
    :param existing_candidate_to_office_links_dict:
    :param existing_measure_objects_dict:
    :param new_office_we_vote_ids_list:
    :param new_candidate_we_vote_ids_list:
    :param new_measure_we_vote_ids_list:
    :param update_or_create_rules:
    :return:
    """
    success = True
    status = ""
    ballot_items_count = 0
    polling_location_found = False
    batch_header_id = 0

    if not positive_value_exists(google_civic_election_id):
        status += "MISSING_ELECTION_ID "
        results = {
            'success':                                  False,
            'status':                                   status,
            'ballot_items_count':                       ballot_items_count,
            'batch_header_id':                          batch_header_id,
            'existing_offices_by_election_dict':        existing_offices_by_election_dict,
            'existing_candidate_objects_dict':          existing_candidate_objects_dict,
            'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
            'existing_measure_objects_dict':            existing_measure_objects_dict,
            'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
        }
        return results

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        status += "MISSING_POLLING_LOCATION_INFO "
        results = {
            'success':                                  False,
            'status':                                   status,
            'ballot_items_count':                       ballot_items_count,
            'batch_header_id':                          batch_header_id,
            'existing_offices_by_election_dict':        existing_offices_by_election_dict,
            'existing_candidate_objects_dict':          existing_candidate_objects_dict,
            'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
            'existing_measure_objects_dict':            existing_measure_objects_dict,
            'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
        }
        return results

    # Create rules
    if 'create_offices' not in update_or_create_rules:
        update_or_create_rules['create_offices'] = True
    if 'create_candidates' not in update_or_create_rules:
        update_or_create_rules['create_candidates'] = True
    if 'create_measures' not in update_or_create_rules:
        update_or_create_rules['create_measures'] = True
    # Update rules
    if 'update_offices' not in update_or_create_rules:
        update_or_create_rules['update_offices'] = False
    if 'update_candidates' not in update_or_create_rules:
        update_or_create_rules['update_candidates'] = False
    if 'update_measures' not in update_or_create_rules:
        update_or_create_rules['update_measures'] = False

    latitude = 0.0
    longitude = 0.0
    text_for_map_search = ''
    polling_location_manager = PollingLocationManager()
    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
        latitude = polling_location.latitude
        longitude = polling_location.longitude
        text_for_map_search = polling_location.get_text_for_map_search()
    elif positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            latitude = polling_location.latitude
            longitude = polling_location.longitude
            text_for_map_search = polling_location.get_text_for_map_search()
            polling_location_found = True

    if polling_location_found:
        if not positive_value_exists(text_for_map_search):
            success = False
            status += "MISSING_TEXT_FOR_MAP_SEARCH-VOTE_USA "
            results = {
                'success':                                  success,
                'status':                                   status,
                'ballot_items_count':                       ballot_items_count,
                'batch_header_id':                          batch_header_id,
                'existing_offices_by_election_dict':        existing_offices_by_election_dict,
                'existing_candidate_objects_dict':          existing_candidate_objects_dict,
                'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
                'existing_measure_objects_dict':            existing_measure_objects_dict,
                'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
            }
            return results

        if not latitude or not longitude:
            success = False
            status += "MISSING_LATITUDE_OR_LONGITUDE-VOTE_USA "
            results = {
                'success':                                  success,
                'status':                                   status,
                'ballot_items_count':                       ballot_items_count,
                'batch_header_id':                          batch_header_id,
                'existing_offices_by_election_dict':        existing_offices_by_election_dict,
                'existing_candidate_objects_dict':          existing_candidate_objects_dict,
                'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
                'existing_measure_objects_dict':            existing_measure_objects_dict,
                'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
            }
            return results

        if not positive_value_exists(state_code):
            if positive_value_exists(polling_location.state):
                state_code = polling_location.state
            else:
                state_code = "na"

        try:
            api_key = VOTE_USA_API_KEY
            # Get the ballot info at this address
            response = requests.get(
                VOTE_USA_VOTER_INFO_URL,
                headers=HEADERS_FOR_VOTE_USA_API_CALL,
                params={
                    "accessKey": api_key,
                    "electionDay": election_day_text,
                    "latitude": latitude,
                    "longitude": longitude,
                    "state": state_code,
                })
            one_ballot_json = json.loads(response.text)
        except Exception as e:
            success = False
            status += 'VOTE_USA_API_END_POINT_CRASH: ' + str(e) + ' '
            log_entry_message = status
            results = polling_location_manager.create_polling_location_log_entry(
                batch_process_id=batch_process_id,
                google_civic_election_id=google_civic_election_id,
                is_from_vote_usa=True,
                kind_of_log_entry=KIND_OF_LOG_ENTRY_API_END_POINT_CRASH,
                log_entry_message=log_entry_message,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                text_for_map_search=text_for_map_search,
            )
            status += results['status']
            results = polling_location_manager.update_polling_location_with_log_counts(
                is_from_vote_usa=True,
                polling_location_we_vote_id=polling_location_we_vote_id,
                update_error_counts=True,
            )
            status += results['status']
            handle_exception(e, logger=logger, exception_message=status)
            results = {
                'success':                                  success,
                'status':                                   status,
                'ballot_items_count':                       ballot_items_count,
                'batch_header_id':                          batch_header_id,
                'existing_offices_by_election_dict':        existing_offices_by_election_dict,
                'existing_candidate_objects_dict':          existing_candidate_objects_dict,
                'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
                'existing_measure_objects_dict':            existing_measure_objects_dict,
                'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
            }
            return results

        try:
            # Use Vote USA API call counter to track the number of queries we are doing each day
            api_counter_manager = VoteUSAApiCounterManager()
            api_counter_manager.create_counter_entry(
                VOTE_USA_VOTER_INFO_QUERY_TYPE,
                google_civic_election_id=google_civic_election_id)

            if 'contests' in one_ballot_json:
                from import_export_google_civic.controllers import groom_and_store_google_civic_ballot_json_2021
                groom_results = groom_and_store_google_civic_ballot_json_2021(
                    one_ballot_json,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    election_day_text=election_day_text,
                    existing_offices_by_election_dict=existing_offices_by_election_dict,
                    existing_candidate_objects_dict=existing_candidate_objects_dict,
                    existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                    existing_measure_objects_dict=existing_measure_objects_dict,
                    new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                    new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                    new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                    update_or_create_rules=update_or_create_rules,
                    use_vote_usa=True,
                    )
                status += groom_results['status']
                ballot_item_dict_list = groom_results['ballot_item_dict_list']
                existing_offices_by_election_dict = groom_results['existing_offices_by_election_dict']
                existing_candidate_objects_dict = groom_results['existing_candidate_objects_dict']
                existing_candidate_to_office_links_dict = groom_results['existing_candidate_to_office_links_dict']
                existing_measure_objects_dict = groom_results['existing_measure_objects_dict']
                new_office_we_vote_ids_list = groom_results['new_office_we_vote_ids_list']
                new_candidate_we_vote_ids_list = groom_results['new_candidate_we_vote_ids_list']
                new_measure_we_vote_ids_list = groom_results['new_measure_we_vote_ids_list']

                # If we successfully save a ballot, create/update a BallotReturned entry
                if ballot_item_dict_list and len(ballot_item_dict_list) > 0:
                    ballot_returned_manager = BallotReturnedManager()
                    ballot_items_count = len(ballot_item_dict_list)
                    results = polling_location.get_text_for_map_search_results()
                    text_for_map_search = results['text_for_map_search']
                    results = ballot_returned_manager.update_or_create_ballot_returned(
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        voter_id=0,
                        google_civic_election_id=google_civic_election_id,
                        latitude=polling_location.latitude,
                        longitude=polling_location.longitude,
                        text_for_map_search=text_for_map_search,
                        normalized_city=polling_location.city,
                        normalized_state=polling_location.state,
                        normalized_zip=polling_location.zip_long,
                    )
                    status += results['status']
                    if results['ballot_returned_found']:
                        status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-VOTE_USA-SUCCESS "
                        # ballot_returned = results['ballot_returned']
                        # ballot_returned_found = True
                    else:
                        status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-VOTE_USA-BALLOT_RETURNED_FOUND-FALSE "
                    results = store_vote_usa_json_response_to_import_batch_system(
                        modified_json_list=ballot_item_dict_list,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_batch='IMPORT_BALLOT_ITEM',
                        batch_set_id=batch_set_id,
                        state_code=state_code)
                    status += results['status']
                    batch_header_id = results['batch_header_id']
                    # Store that we have reviewed this polling_location so we don't retrieve it again in the next chunk
                    results = polling_location_manager.create_polling_location_log_entry(
                        batch_process_id=batch_process_id,
                        google_civic_election_id=google_civic_election_id,
                        is_from_vote_usa=True,
                        kind_of_log_entry=KIND_OF_LOG_ENTRY_BALLOT_RECEIVED,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        state_code=state_code,
                        text_for_map_search=text_for_map_search,
                    )
                    if not results['success']:
                        status += results['status']
                    results = polling_location_manager.update_polling_location_with_log_counts(
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        update_data_counts=True,
                        is_successful_retrieve=True,
                    )
                    status += results['status']
                else:
                    # We need to at least to mark the BallotReturned entry with a new date_last_updated date so
                    #  we can move on to other ballot returned entries.
                    status += "CONTESTS_BUT_NO_INCOMING_BALLOT_ITEMS_FOUND_VOTE_USA "
            else:
                # Create BallotReturnedEmpty entry so we don't keep retrieving this map point
                status += "NO_INCOMING_BALLOT_ITEMS_FOUND_VOTE_USA "
                ballot_returned_manager = BallotReturnedManager()
                results = ballot_returned_manager.create_ballot_returned_empty(
                    google_civic_election_id=google_civic_election_id,
                    is_from_vote_usa=True,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    state_code=state_code,
                )
                if not results['success']:
                    status += results['status']
                kind_of_log_entry = KIND_OF_LOG_ENTRY_NO_CONTESTS
                log_entry_message = ''
                try:
                    error = one_ballot_json.get('error', {})
                    errors = error.get('errors', {})
                    if len(errors):
                        log_entry_message = errors
                        for one_error in errors:
                            try:
                                if 'reason' in one_error:
                                    if one_error['reason'] == "notFound":
                                        # Ballot data not found at this location
                                        address_not_found = True
                                    elif one_error['reason'] == "parseError":
                                        kind_of_log_entry = KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR
                                    else:
                                        reason_not_found = True
                            except Exception as e:
                                status += "PROBLEM_PARSING_ERROR_VOTE_USA: " + str(e) + ' '
                except Exception as e:
                    status += "PROBLEM_GETTING_ERRORS_VOTE_USA: " + str(e) + " "
                    log_entry_message += status
                results = polling_location_manager.create_polling_location_log_entry(
                    batch_process_id=batch_process_id,
                    google_civic_election_id=google_civic_election_id,
                    is_from_vote_usa=True,
                    kind_of_log_entry=kind_of_log_entry,
                    log_entry_message=log_entry_message,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    state_code=state_code,
                    text_for_map_search=text_for_map_search,
                )
                status += results['status']
                if kind_of_log_entry == KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR:
                    results = polling_location_manager.update_polling_location_with_log_counts(
                        is_from_vote_usa=True,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        update_error_counts=True,
                    )
                    status += results['status']
                else:
                    results = polling_location_manager.update_polling_location_with_log_counts(
                        is_no_contests=True,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        update_data_counts=True,
                    )
                    status += results['status']
        except Exception as e:
            success = False
            status += 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS_API_V4-VOTE_USA-ERROR: ' + str(e) + ' '
            handle_exception(e, logger=logger, exception_message=status)
    else:
        status += "POLLING_LOCATION_NOT_FOUND-VOTE_USA (" + str(polling_location_we_vote_id) + ") "
    results = {
        'success':                                  success,
        'status':                                   status,
        'ballot_items_count':                       ballot_items_count,
        'batch_header_id':                          batch_header_id,
        'existing_offices_by_election_dict':        existing_offices_by_election_dict,
        'existing_candidate_objects_dict':          existing_candidate_objects_dict,
        'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
        'existing_measure_objects_dict':            existing_measure_objects_dict,
        'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
    }
    return results


def store_results_from_vote_usa_api_election_query(structured_json):
    if 'elections' in structured_json:
        elections_list_json = structured_json['elections']
    else:
        elections_list_json = {}
    results = {}
    from election.models import ElectionManager
    election_manager = ElectionManager()
    for one_election in elections_list_json:
        results = election_manager.update_or_create_election(
            election_day_text=one_election['electionDay'],
            election_name=one_election['name'],
            election_name_do_not_override=True,
            state_code=one_election['state'],
            use_vote_usa_as_data_source=True,
            vote_usa_election_id=one_election['id'])

    return results
