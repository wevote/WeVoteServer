# import_export_vote_usa/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoteUSAApiCounterManager
from ballot.models import BallotReturnedManager
from config.base import get_environment_variable
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from import_export_batches.controllers_vote_usa import store_vote_usa_json_response_to_import_batch_system
from import_export_google_civic.controllers import groom_and_store_google_civic_ballot_json_2021
import json
from polling_location.models import PollingLocationManager
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

VOTE_USA_API_KEY = get_environment_variable("VOTE_USA_API_KEY")
VOTE_USA_VOTER_INFO_URL = "https://vote-usa.org/api/v1.asmx/voterInfoQuery"
VOTE_USA_VOTER_INFO_QUERY_TYPE = "voterinfo"

MAIL_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Host': 'api4.ballotpedia.org',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0',
}


def retrieve_vote_usa_ballot_items_from_polling_location_api(
        google_civic_election_id,
        election_day_text="",
        polling_location_we_vote_id="",
        polling_location=None,
        state_code="",
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
    polling_location_found = False
    batch_header_id = 0

    if not positive_value_exists(google_civic_election_id):
        status += "MISSING_ELECTION_ID "
        results = {
            'success': False,
            'status': status,
            'batch_header_id':  batch_header_id,
            'existing_offices_by_election_dict': existing_offices_by_election_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        status += "MISSING_POLLING_LOCATION_INFO "
        results = {
            'success': False,
            'status': status,
            'batch_header_id':  batch_header_id,
            'existing_offices_by_election_dict': existing_offices_by_election_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
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
    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
        latitude = polling_location.latitude
        longitude = polling_location.longitude
        text_for_map_search = polling_location.get_text_for_map_search()
    elif positive_value_exists(polling_location_we_vote_id):
        polling_location_manager = PollingLocationManager()
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
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
                'existing_offices_by_election_dict': existing_offices_by_election_dict,
                'existing_candidate_objects_dict': existing_candidate_objects_dict,
                'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
                'existing_measure_objects_dict': existing_measure_objects_dict,
                'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
            }
            return results

        if not latitude or not longitude:
            success = False
            status += "MISSING_LATITUDE_OR_LONGITUDE-VOTE_USA "
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
                'existing_offices_by_election_dict': existing_offices_by_election_dict,
                'existing_candidate_objects_dict': existing_candidate_objects_dict,
                'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
                'existing_measure_objects_dict': existing_measure_objects_dict,
                'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
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
                headers=MAIL_HEADERS,
                params={
                    "accessKey": api_key,
                    "electionDay": election_day_text,
                    "latitude": latitude,
                    "longitude": longitude,
                    "state": state_code,
                })
            one_ballot_json = json.loads(response.text)

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            api_counter_manager = VoteUSAApiCounterManager()
            api_counter_manager.create_counter_entry(
                VOTE_USA_VOTER_INFO_QUERY_TYPE,
                google_civic_election_id=google_civic_election_id)

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
            else:
                # We need to at least to mark the BallotReturned entry with a new date_last_updated date so
                #  we can more on to other ballot returned entries.
                status += "NO_INCOMING_BALLOT_ITEMS_FOUND-VOTE_USA "
        except Exception as e:
            success = False
            status += 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS_API_V4-VOTE_USA-ERROR: ' + str(e) + ' '
            handle_exception(e, logger=logger, exception_message=status)
    else:
        status += "POLLING_LOCATION_NOT_FOUND-VOTE_USA (" + str(polling_location_we_vote_id) + ") "
    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'existing_offices_by_election_dict': existing_offices_by_election_dict,
        'existing_candidate_objects_dict': existing_candidate_objects_dict,
        'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
        'existing_measure_objects_dict': existing_measure_objects_dict,
        'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
    }
    return results
