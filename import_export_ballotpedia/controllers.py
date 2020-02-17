# import_export_ballotpedia/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-
from .models import BallotpediaApiCounterManager
from ballot.models import BallotItemListManager, BallotItemManager, BallotReturned, BallotReturnedManager, \
    VoterBallotSavedManager
from candidate.models import CandidateCampaignManager, CandidateCampaignListManager, fetch_candidate_count_for_office
from config.base import get_environment_variable
from electoral_district.models import ElectoralDistrict, ElectoralDistrictManager
from election.models import BallotpediaElection, ElectionManager, Election
from exception.models import handle_exception
from geopy.geocoders import get_geocoder_for_service
from import_export_batches.controllers_ballotpedia import store_ballotpedia_json_response_to_import_batch_system
import json
from measure.models import ContestMeasureList, ContestMeasureManager
from office.models import ContestOfficeListManager, ContestOfficeManager
from politician.models import PoliticianManager
from polling_location.models import PollingLocationManager
import requests
from voter.models import fetch_voter_id_from_voter_device_link, VoterAddressManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_code_from_address_string, positive_value_exists

BALLOTPEDIA_API_KEY = get_environment_variable("BALLOTPEDIA_API_KEY")
BALLOTPEDIA_API_CANDIDATES_URL = get_environment_variable("BALLOTPEDIA_API_CANDIDATES_URL")
BALLOTPEDIA_API_CONTAINS_URL = get_environment_variable("BALLOTPEDIA_API_CONTAINS_URL")
BALLOTPEDIA_API_ELECTIONS_URL = get_environment_variable("BALLOTPEDIA_API_ELECTIONS_URL")
BALLOTPEDIA_API_FILES_URL = get_environment_variable("BALLOTPEDIA_API_FILES_URL")
BALLOTPEDIA_API_MEASURES_URL = get_environment_variable("BALLOTPEDIA_API_MEASURES_URL")
BALLOTPEDIA_API_RACES_URL = get_environment_variable("BALLOTPEDIA_API_RACES_URL")
BALLOTPEDIA_API_SAMPLE_BALLOT_ELECTIONS_URL = "https://api4.ballotpedia.org/sample_ballot_elections"
BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL = "https://api4.ballotpedia.org/sample_ballot_results"
BALLOTPEDIA_API_CANDIDATES_TYPE = "candidates"
BALLOTPEDIA_API_CONTAINS_TYPE = "contains"
BALLOTPEDIA_API_ELECTIONS_TYPE = "elections"
BALLOTPEDIA_API_FILES_TYPE = "files"
BALLOTPEDIA_API_MEASURES_TYPE = "measures"
BALLOTPEDIA_API_RACES_TYPE = "races"
BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_TYPE = "sample_ballot_results"
GEOCODE_TIMEOUT = 10
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")

IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'

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

logger = wevote_functions.admin.get_logger(__name__)


def extract_value_from_array(structured_json, index_key, default_value):
    if index_key in structured_json:
        return structured_json[index_key]
    else:
        return default_value


def attach_ballotpedia_election_by_district_from_api(election, google_civic_election_id,
                                                     ballotpedia_district_id_list, state_code):
    success = True
    status = ""
    chunks_of_district_strings = []
    election_object_found = False
    ballotpedia_election_id = 0
    ballotpedia_kind_of_election = ""
    elections_retrieve_url = ""

    if election and positive_value_exists(election.google_civic_election_id):
        election_object_found = True

    if not election_object_found and not positive_value_exists(google_civic_election_id):
        success = False
        status += "ATTACH_BALLOTPEDIA_ELECTION-MISSING_ELECTION_ID "
        results = {
            'success':          success,
            'status':           status,
            'election_found':   False,
        }
        return results

    if not len(ballotpedia_district_id_list):
        success = False
        status += "ATTACH_BALLOTPEDIA_ELECTION-MISSING_BALLOTPEDIA_DISTRICT_LIST "
        results = {
            'success':          success,
            'status':           status,
            'election_found':   False,
        }
        return results

    if not positive_value_exists(state_code):
        success = False
        status += "ATTACH_BALLOTPEDIA_ELECTION-STATE_CODE_REQUIRED "
        results = {
            'success':          success,
            'status':           status,
            'election_found':   False,
        }
        return results

    election_day_text = ""
    google_civic_election_found = False
    is_national_election = False
    if election_object_found:
        election_day_text = election.election_day_text
        is_national_election = election.is_national_election
        google_civic_election_id = election.google_civic_election_id
        google_civic_election_found = True
    else:
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            election_day_text = election.election_day_text
            is_national_election = election.is_national_election
            google_civic_election_found = True

    if not positive_value_exists(google_civic_election_found):
        success = False
        status += "ATTACH_BALLOTPEDIA_ELECTION-GOOGLE_CIVIC_ELECTION_NOT_FOUND "
        results = {
            'success':          success,
            'status':           status,
            'election_found':   google_civic_election_found,
        }
        return results

    district_string = ""
    ballotpedia_district_id_not_used_list = []
    count_of_districts_sent = 0
    for one_district in ballotpedia_district_id_list:
        if not positive_value_exists(one_district):
            continue
        # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
        #  office_district_string, but capture the districts not used
        # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
        if len(district_string) < 3796:
            district_string += str(one_district) + ","
            count_of_districts_sent += 1
        else:
            # In the future we might want to set up a second query to get the races for these districts
            ballotpedia_district_id_not_used_list.append(one_district)

    status += "COUNT_OF_FIRST_BLOCK_OF_DISTRICTS: " + str(count_of_districts_sent) + " "
    # Remove last comma
    if count_of_districts_sent > 1:
        district_string = district_string[:-1]
    chunks_of_district_strings.append(district_string)

    # Now add all of the districts that were missed from the first retrieve
    while len(ballotpedia_district_id_not_used_list):
        district_string = ""
        count_of_districts_sent = 0
        temp_ballotpedia_district_id_not_used_list = []
        for one_district in ballotpedia_district_id_not_used_list:
            if not positive_value_exists(one_district):
                continue
            # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
            #  office_district_string, but capture the districts not used
            # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
            if len(district_string) < 3796:
                district_string += str(one_district) + ","
                count_of_districts_sent += 1
            else:
                # In the future we might want to set up a second query to get the races for these districts
                temp_ballotpedia_district_id_not_used_list.append(one_district)

        # Remove last comma
        if count_of_districts_sent > 1:
            district_string = district_string[:-1]
        chunks_of_district_strings.append(district_string)
        ballotpedia_district_id_not_used_list = temp_ballotpedia_district_id_not_used_list

    elections_final_json_list = []
    # Tests are showing that election numbers aren't reused between primary & general
    election_count = 0
    election_found = False
    which_chunk_of_district_strings = 0
    for district_string in chunks_of_district_strings:
        which_chunk_of_district_strings += 1
        status += "CHUNK_OF_DISTRICT_STRINGS-" + str(which_chunk_of_district_strings) + " "

        if not positive_value_exists(election_day_text):
            status += "MISSING_ELECTION_DAY_TEXT "
            continue

        if not positive_value_exists(district_string):
            status += "MISSING_DISTRICT_STRING_VALUES "
            continue

        response = requests.get(BALLOTPEDIA_API_ELECTIONS_URL, params={
            "access_token":             BALLOTPEDIA_API_KEY,
            "filters[district][in]":    district_string,
            "filters[date][eq]":        election_day_text,
            "order[date]":              "ASC",
        })

        if not hasattr(response, 'text') or not positive_value_exists(response.text):
            status += "NO_RESPONSE_TEXT_FOUND-CHUNK: " + str(which_chunk_of_district_strings) + " "
            if positive_value_exists(response.url):
                shortened_url = response.url[:1000]
                status += ": " + shortened_url + " "
            continue

        if hasattr(response, 'success') and not positive_value_exists(response.success):
            status += "RESPONSE_SUCCESS_IS_FALSE-CHUNK: " + str(which_chunk_of_district_strings) + " "
            if positive_value_exists(response.url):
                shortened_url = response.url[:1000]
                status += ": " + shortened_url + " "
            if positive_value_exists(response.error):
                status += "error: " + str(response.error)
            continue

        if hasattr(response, 'ok') and not positive_value_exists(response.ok):
            success = False
            status += "RESPONSE_OK_IS_FALSE-CHUNK: " + str(which_chunk_of_district_strings) + " "
            if positive_value_exists(response.url):
                shortened_url = response.url[:1000]
                status += ": " + shortened_url + " "
            if hasattr(response, 'status_code'):
                status += "status_code: " + str(response.status_code)
                if response.status_code == 414:
                    status += " Too many races sent"
            continue

        structured_json = json.loads(response.text)
        status += "STRUCTURED_JSON_RETRIEVED "

        elections_retrieve_url = ""
        if positive_value_exists(response.url):
            elections_retrieve_url = response.url

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_ELECTIONS_TYPE,
                                                             google_civic_election_id=google_civic_election_id)

        ballotpedia_election_id = 0
        ballotpedia_kind_of_election = ""
        elections_json_list = []
        if 'data' in structured_json:
            if 'meta' in structured_json:
                if 'table' in structured_json['meta']:
                    if structured_json['meta']['table'] == 'election_dates':
                        elections_json_list = structured_json['data']
                        if elections_json_list:
                            elections_json_count = len(elections_json_list)
                            status += "ELECTIONS_JSON_FOUND: " + str(elections_json_count) + " "
                        else:
                            status += "ELECTIONS_JSON-GLITCH, no elections found "
                    else:
                        status += "NOT_TRUE: structured_json['meta']['table'] == 'election_dates' "
                else:
                    status += "NOT_TRUE: if 'table' in structured_json['meta'] "
            else:
                status += "NOT_TRUE: if 'meta' in structured_json "
        else:
            status += "NOT_TRUE: if 'data' in structured_json "

        if len(elections_json_list):
            elections_final_json_list = elections_final_json_list + elections_json_list

    if not len(elections_final_json_list):
        status += 'NO_ELECTIONS_RETURNED_FROM_BALLOTPEDIA '
    else:
        election_found = True
        status += "BALLOTPEDIA_ELECTION_DATA_FOUND "
        for one_election_json in elections_final_json_list:
            election_count += 1
            ballotpedia_election_id = 0
            ballotpedia_kind_of_election = ""
            is_general_election = False
            is_general_runoff_election = False
            is_primary_election = False
            is_primary_runoff_election = False

            try:
                ballotpedia_election_id = one_election_json['id']

                if one_election_json['type'] == "Primary":
                    ballotpedia_kind_of_election = "primary_election"
                    is_primary_election = True
                elif one_election_json['type'] == "General":
                    ballotpedia_kind_of_election = "general_election"
                    is_general_election = True
                elif one_election_json['type'] == "Primary Runoff":
                    ballotpedia_kind_of_election = "primary_runoff_election"
                    is_primary_runoff_election = True
                elif one_election_json['type'] == "General Runoff":
                    ballotpedia_kind_of_election = "general_runoff_election"
                    is_general_runoff_election = True
                else:
                    ballotpedia_kind_of_election = "unknown"
            except KeyError as e:
                status += "ELECTIONS_KEY_ERROR: " + str(e) + " "

            if positive_value_exists(ballotpedia_election_id) and positive_value_exists(ballotpedia_kind_of_election):
                # Does BallotpediaElection already exist?
                try:
                    ballotpedia_election = BallotpediaElection.objects.get(
                        ballotpedia_election_id=one_election_json['id'])
                    ballotpedia_election_found = True
                except BallotpediaElection.DoesNotExist:
                    ballotpedia_election_found = False
                except Exception as e:
                    ballotpedia_election_found = False
                    status += "ERROR_RETRIEVING_BALLOTPEDIA_ELECTION " + str(e) + " "
                    continue

                if positive_value_exists(ballotpedia_election_found):
                    try:
                        number_of_elections_updated = \
                            BallotpediaElection.objects.filter(
                                ballotpedia_election_id=one_election_json['id']
                            ).update(
                                election_description=one_election_json['description'],
                                election_type=one_election_json['type'],
                                district_name=one_election_json['district_name'],
                                district_type=one_election_json['district_type'],
                                is_general_election=is_general_election,
                                is_general_runoff_election=is_general_runoff_election,
                                is_partisan=one_election_json['is_partisan'],
                                is_primary_election=is_primary_election,
                                is_primary_runoff_election=is_primary_runoff_election,
                            )

                        ballotpedia_election = BallotpediaElection.objects.get(
                            ballotpedia_election_id=one_election_json['id'])

                        ballotpedia_election_id = ballotpedia_election.ballotpedia_election_id
                        status += "BALLOTPEDIA_ELECTION_LINKED " + str(ballotpedia_election_id) + " "
                        election_found = True
                    except Exception as e:
                        status += "COULD_NOT_SAVE_BALLOTPEDIA_ELECTION " + str(e) + " "
                else:
                    try:
                        ballotpedia_election = BallotpediaElection.objects.create(
                            ballotpedia_election_id=one_election_json['id'],
                            election_day_text=one_election_json['date'],
                            election_description=one_election_json['description'],
                            election_type=one_election_json['type'],
                            district_name=one_election_json['district_name'],
                            district_type=one_election_json['district_type'],
                            google_civic_election_id=google_civic_election_id,
                            is_general_election=is_general_election,
                            is_general_runoff_election=is_general_runoff_election,
                            is_partisan=one_election_json['is_partisan'],
                            is_primary_election=is_primary_election,
                            is_primary_runoff_election=is_primary_runoff_election,
                            state_code=state_code,
                        )

                        ballotpedia_election_id = ballotpedia_election.ballotpedia_election_id
                        status += "BALLOTPEDIA_ELECTION_CREATED_AND_LINKED " + str(ballotpedia_election_id) + " "
                        election_found = True
                    except Exception as e:
                        status += "COULD_NOT_CREATE_BALLOTPEDIA_ELECTION " + str(e) + " "
            else:
                status += "BALLOTPEDIA_ELECTION_INFO_NOT_FOUND "

        if election_count == 1:
            if not positive_value_exists(is_national_election):
                # Only one election found, so we also store the election info directly in the election object
                if positive_value_exists(ballotpedia_election_id) and \
                        positive_value_exists(ballotpedia_kind_of_election):
                    try:
                        election.ballotpedia_election_id = ballotpedia_election_id
                        election.ballotpedia_kind_of_election = ballotpedia_kind_of_election
                        election.save()
                        status += "BALLOTPEDIA_ELECTION_ATTACHED_TO_ELECTION "
                        election_found = True
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ELECTION " + str(e) + " "
                else:
                    status += "ONE_ELECTION-BALLOTPEDIA_ELECTION_INFO_NOT_FOUND " + str(elections_retrieve_url) + " "

    results = {
        'success':          success,
        'status':           status,
        'election_found':   election_found,
    }
    return results


def retrieve_ballotpedia_candidates_by_district_from_api(google_civic_election_id, state_code="",
                                                         only_retrieve_if_zero_candidates=False):
    success = True
    status = ""
    batch_header_id = 0
    return_list_of_objects = True

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
            'batch_header_id': batch_header_id,
        }
        return results

    contest_list_manager = ContestOfficeListManager()
    results = contest_list_manager.retrieve_offices(
        google_civic_election_id, state_code, return_list_of_objects=return_list_of_objects)

    ballotpedia_race_ids_string = ""
    ballotpedia_race_id_not_used_list = []
    chunks_of_race_id_strings = []
    filtered_office_list = []
    final_json_list = []
    kind_of_election_by_race = {}
    office_count = 0
    if results['office_list_found']:
        office_list_objects = results['office_list_objects']

        # Generate a list of offices we want to retrieve candidates for from Ballotpedia
        for one_office in office_list_objects:
            retrieve_candidates_for_this_office = True
            if only_retrieve_if_zero_candidates:
                candidate_count = fetch_candidate_count_for_office(one_office.id)
                retrieve_candidates_for_this_office = not positive_value_exists(candidate_count)
            if retrieve_candidates_for_this_office:
                filtered_office_list.append(one_office)
                office_count += 1
                kind_of_election_by_race[one_office.ballotpedia_race_id] = one_office.get_kind_of_ballotpedia_election()
                # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
                #  ballotpedia_race_ids_string, but capture the races not used
                # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
                if len(ballotpedia_race_ids_string) < 3796:
                    ballotpedia_race_ids_string += str(one_office.ballotpedia_race_id) + ","
                else:
                    # In the future we might want to set up a second query to get the races for these districts
                    ballotpedia_race_id_not_used_list.append(one_office.ballotpedia_race_id)
                    
        chunks_of_race_id_strings.append(ballotpedia_race_ids_string)

        # Now add all of the districts that were missed from the first retrieve
        while len(ballotpedia_race_id_not_used_list):
            ballotpedia_race_ids_string = ""
            ballotpedia_race_count = 0
            temp_ballotpedia_race_id_not_used_list = []
            for one_race_id in ballotpedia_race_id_not_used_list:
                # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
                #  office_district_string, but capture the districts not used
                # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
                if len(ballotpedia_race_ids_string) < 3796:
                    ballotpedia_race_ids_string += str(one_race_id) + ","
                    ballotpedia_race_count += 1
                else:
                    # In the future we might want to set up a second query to get the races for these districts
                    temp_ballotpedia_race_id_not_used_list.append(one_race_id)
    
            # Remove last comma
            if ballotpedia_race_count > 1:
                ballotpedia_race_ids_string = ballotpedia_race_ids_string[:-1]
            chunks_of_race_id_strings.append(ballotpedia_race_ids_string)
    
            ballotpedia_race_id_not_used_list = temp_ballotpedia_race_id_not_used_list

    if not positive_value_exists(office_count):
        status += "NO_OFFICES_FOUND_TO_USE_FOR_RETRIEVING_CANDIDATES "
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
        }
        return results

    kind_of_batch = ""
    for ballotpedia_race_ids_string in chunks_of_race_id_strings:
        response = requests.get(BALLOTPEDIA_API_CANDIDATES_URL, params={
            "access_token": BALLOTPEDIA_API_KEY,
            "filters[race][in]": ballotpedia_race_ids_string,
            "limit": 1000,
        })

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(
            BALLOTPEDIA_API_CANDIDATES_TYPE,
            google_civic_election_id=google_civic_election_id,
            ballotpedia_election_id=0)

        if not hasattr(response, 'text') or not positive_value_exists(response.text):
            success = False
            status += "NO_RESPONSE_TEXT_FOUND "
            if positive_value_exists(response.url):
                shortened_url = response.url[:1000]
                status += ": " + shortened_url + " "
            continue
            # results = {
            #     'success': success,
            #     'status': status,
            #     'batch_header_id': batch_header_id,
            # }
            # return results

        if hasattr(response, 'success') and not positive_value_exists(response.success):
            success = False
            status += "RESPONSE_SUCCESS_IS_FALSE"
            if positive_value_exists(response.url):
                shortened_url = response.url[:1000]
                status += ": " + shortened_url + " "
            if positive_value_exists(response.error):
                status += "error: " + str(response.error)
            continue
            # results = {
            #     'success': success,
            #     'status': status,
            #     'batch_header_id': batch_header_id,
            # }
            # return results

        if hasattr(response, 'ok') and not positive_value_exists(response.ok):
            success = False
            status += "RESPONSE_OK_IS_FALSE"
            if positive_value_exists(response.url):
                shortened_url = response.url[:1000]
                status += ": " + shortened_url + " "
            if hasattr(response, 'status_code'):
                status += "status_code: " + str(response.status_code)
                if response.status_code == 414:
                    status += " Too many races sent"
            continue
            # results = {
            #     'success': success,
            #     'status': status,
            #     'batch_header_id': batch_header_id,
            # }
            # return results

        structured_json = json.loads(response.text)

        contains_api = False
        groom_results = groom_ballotpedia_data_for_processing(
            structured_json, google_civic_election_id, state_code,
            contains_api,
            kind_of_election_by_race=kind_of_election_by_race)
        modified_json_list = groom_results['modified_json_list']
        kind_of_batch = groom_results['kind_of_batch']

        final_json_list = final_json_list + modified_json_list

        # Since the overall script might time out, we store a batch of candidates for every chunk of race id strings
        results = store_ballotpedia_json_response_to_import_batch_system(
            final_json_list, google_civic_election_id, kind_of_batch, state_code=state_code)
        status += results['status']
        final_json_list = []
        if 'batch_header_id' in results:
            batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_ballot_items_from_polling_location(
        google_civic_election_id, polling_location_we_vote_id="", polling_location=None, batch_set_id=0,
        state_code=""):
    success = True
    status = ""
    polling_location_found = False

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        results = {
            'success': False,
            'status': "Error: Missing polling location we vote id and polling_location_object",
        }
        return results

    batch_header_id = 0

    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
    elif positive_value_exists(polling_location_we_vote_id):
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_found = True

    if polling_location_found:
        if not polling_location.latitude or not polling_location.longitude:
            success = False
            status += "RETRIEVE_DISTRICTS-MISSING_LATITUDE_LONGITUDE "
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
            }
            return results

        try:
            latitude_longitude = str(polling_location.latitude) + "," + str(polling_location.longitude)
            response = requests.get(BALLOTPEDIA_API_CONTAINS_URL, params={
                "access_token": BALLOTPEDIA_API_KEY,
                "point": latitude_longitude,
            })

            structured_json = json.loads(response.text)

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
            ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_CONTAINS_TYPE,
                                                                 google_civic_election_id=google_civic_election_id,
                                                                 ballotpedia_election_id=0)

            contains_api = True
            groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id, state_code,
                                                                  contains_api)

            modified_json_list = groom_results['modified_json_list']
            kind_of_batch = groom_results['kind_of_batch']

            # This function makes sure there are candidates attached to an office before including the office
            #  on the ballot.
            ballot_items_results = process_ballotpedia_voter_districts(google_civic_election_id, state_code,
                                                                       modified_json_list, polling_location_we_vote_id)

            if ballot_items_results['ballot_items_found']:
                ballot_item_dict_list = ballot_items_results['ballot_item_dict_list']

                results = store_ballotpedia_json_response_to_import_batch_system(
                    modified_json_list=ballot_item_dict_list, google_civic_election_id=google_civic_election_id,
                    kind_of_batch=kind_of_batch, batch_set_id=batch_set_id, state_code=state_code)
                status += results['status']
                if 'batch_header_id' in results:
                    batch_header_id = results['batch_header_id']
        except Exception as e:
            success = False
            status += 'ERROR FAILED retrieve_ballot_items_from_polling_location ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_ballot_items_from_polling_location(
        google_civic_election_id, polling_location_we_vote_id="", polling_location=None, batch_set_id=0,
        state_code=""):
    success = True
    status = ""
    polling_location_found = False

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        results = {
            'success': False,
            'status': "Error: Missing polling location we vote id and polling_location_object",
        }
        return results

    batch_header_id = 0

    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
    elif positive_value_exists(polling_location_we_vote_id):
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_found = True

    if polling_location_found:
        if not polling_location.latitude or not polling_location.longitude:
            success = False
            status += "RETRIEVE_DISTRICTS-MISSING_LATITUDE_LONGITUDE "
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
            }
            return results

        try:
            latitude_longitude = str(polling_location.latitude) + "," + str(polling_location.longitude)
            response = requests.get(BALLOTPEDIA_API_CONTAINS_URL, params={
                "access_token": BALLOTPEDIA_API_KEY,
                "point": latitude_longitude,
            })

            structured_json = json.loads(response.text)

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
            ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_CONTAINS_TYPE,
                                                                 google_civic_election_id=google_civic_election_id,
                                                                 ballotpedia_election_id=0)

            contains_api = True
            groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id, state_code,
                                                                  contains_api)

            modified_json_list = groom_results['modified_json_list']
            kind_of_batch = groom_results['kind_of_batch']

            # This function makes sure there are candidates attached to an office before including the office
            #  on the ballot.
            ballot_items_results = process_ballotpedia_voter_districts(google_civic_election_id, state_code,
                                                                       modified_json_list, polling_location_we_vote_id)

            if ballot_items_results['ballot_items_found']:
                ballot_item_dict_list = ballot_items_results['ballot_item_dict_list']

                results = store_ballotpedia_json_response_to_import_batch_system(
                    modified_json_list=ballot_item_dict_list, google_civic_election_id=google_civic_election_id,
                    kind_of_batch=kind_of_batch, batch_set_id=batch_set_id, state_code=state_code)
                status += results['status']
                if 'batch_header_id' in results:
                    batch_header_id = results['batch_header_id']
        except Exception as e:
            success = False
            status += 'ERROR FAILED retrieve_ballot_items_from_polling_location ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_ballot_items_from_polling_location_api_v4(
        google_civic_election_id,
        election_day_text="",
        polling_location_we_vote_id="",
        polling_location=None,
        state_code="",
        batch_set_id=0,
        existing_office_objects_dict={},
        existing_candidate_objects_dict={},
        existing_measure_objects_dict={},
        new_office_we_vote_ids_list=[],
        new_candidate_we_vote_ids_list=[],
        new_measure_we_vote_ids_list=[]):
    success = True
    status = ""
    polling_location_found = False
    batch_header_id = 0

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
            'batch_header_id':  batch_header_id,
            'existing_office_objects_dict': existing_office_objects_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        results = {
            'success': False,
            'status': "Error: Missing polling location we vote id and polling_location_object",
            'batch_header_id':  batch_header_id,
            'existing_office_objects_dict': existing_office_objects_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
    elif positive_value_exists(polling_location_we_vote_id):
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_found = True

    if polling_location_found:
        if not polling_location.latitude or not polling_location.longitude:
            success = False
            status += "RETRIEVE_DISTRICTS-MISSING_LATITUDE_LONGITUDE "
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
                'existing_office_objects_dict': existing_office_objects_dict,
                'existing_candidate_objects_dict': existing_candidate_objects_dict,
                'existing_measure_objects_dict': existing_measure_objects_dict,
                'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
            }
            return results

        try:
            # Get the electoral_districts at this lat/long
            response = requests.get(
                BALLOTPEDIA_API_SAMPLE_BALLOT_ELECTIONS_URL,
                headers=MAIL_HEADERS,
                params={
                    "lat": polling_location.longitude,
                    "long": polling_location.latitude,
                    # NOTE: Ballotpedia appears to have swapped latitude and longitude
                    # "lat": polling_location.latitude,
                    # "long": polling_location.longitude,
                })
            structured_json = json.loads(response.text)

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
            ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_ELECTIONS_TYPE,
                                                                 google_civic_election_id=google_civic_election_id,
                                                                 ballotpedia_election_id=0)

            groom_results = groom_and_store_sample_ballot_elections_api_v4(structured_json, google_civic_election_id)
            ballotpedia_district_id_list = groom_results['ballotpedia_district_id_list']
            if not ballotpedia_district_id_list or len(ballotpedia_district_id_list) == 0:
                status += "NO_BALLOTPEDIA_DISTRICTS_RETURNED "
                results = {
                    'success': success,
                    'status': status,
                    'batch_header_id': batch_header_id,
                    'existing_office_objects_dict': existing_office_objects_dict,
                    'existing_candidate_objects_dict': existing_candidate_objects_dict,
                    'existing_measure_objects_dict': existing_measure_objects_dict,
                    'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                    'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                    'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
                }
                return results

            office_district_string = ""
            office_district_count = 0
            ballotpedia_district_id_not_used_list = []
            for one_district in ballotpedia_district_id_list:
                # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
                #  office_district_string, but capture the districts not used
                # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
                if len(office_district_string) < 3796:
                    office_district_string += str(one_district) + ","
                    office_district_count += 1
                else:
                    # In the future we might want to set up a second query to get the races for these districts
                    ballotpedia_district_id_not_used_list.append(one_district)

            # Remove last comma
            if office_district_count > 1:
                office_district_string = office_district_string[:-1]
            # chunks_of_district_strings.append(office_district_string)

            # Get the electoral_districts at this lat/long
            response = requests.get(BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL, headers=MAIL_HEADERS, params={
                "districts": office_district_string,
                "election_date": election_day_text,
            })
            structured_json = json.loads(response.text)

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
            ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_TYPE,
                                                                 google_civic_election_id=google_civic_election_id,
                                                                 ballotpedia_election_id=0)

            groom_results = groom_and_store_sample_ballot_results_api_v4(
                structured_json,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                polling_location_we_vote_id=polling_location_we_vote_id,
                election_day_text=election_day_text,
                existing_office_objects_dict=existing_office_objects_dict,
                existing_candidate_objects_dict=existing_candidate_objects_dict,
                existing_measure_objects_dict=existing_measure_objects_dict,
                new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                )
            status += groom_results['status']
            ballot_item_dict_list = groom_results['ballot_item_dict_list']
            existing_office_objects_dict = groom_results['existing_office_objects_dict']
            existing_candidate_objects_dict = groom_results['existing_candidate_objects_dict']
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
                    status += "UPDATE_OR_CREATE_BALLOT_RETURNED-SUCCESS "
                    # ballot_returned = results['ballot_returned']
                    # ballot_returned_found = True
                else:
                    status += "UPDATE_OR_CREATE_BALLOT_RETURNED-BALLOT_RETURNED_FOUND-FALSE "
                results = store_ballotpedia_json_response_to_import_batch_system(
                    modified_json_list=ballot_item_dict_list,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_batch=IMPORT_BALLOT_ITEM,
                    batch_set_id=batch_set_id,
                    state_code=state_code)
                status += results['status']
                batch_header_id = results['batch_header_id']
        except Exception as e:
            success = False
            status += 'ERROR FAILED retrieve_ballot_items_from_polling_location ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'existing_office_objects_dict': existing_office_objects_dict,
        'existing_candidate_objects_dict': existing_candidate_objects_dict,
        'existing_measure_objects_dict': existing_measure_objects_dict,
        'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
    }
    return results


def retrieve_ballot_items_for_one_voter_api_v4(
        google_civic_election_id,
        election_day_text="",
        ballot_returned=None,
        state_code="",
        batch_set_id=0,
        existing_office_objects_dict={},
        existing_candidate_objects_dict={},
        existing_measure_objects_dict={},
        new_office_we_vote_ids_list=[],
        new_candidate_we_vote_ids_list=[],
        new_measure_we_vote_ids_list=[]):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        status += "Error: Missing google_civic_election_id "
        success = False
        results = {
            'success': success,
            'status': status,
            'existing_office_objects_dict': existing_office_objects_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    if not ballot_returned:
        status += "Error: Missing ballot_returned "
        success = False
        results = {
            'success': success,
            'status': status,
            'existing_office_objects_dict': existing_office_objects_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    if not ballot_returned.voter_id:
        status += "Error: Missing ballot_returned.voter_id "
        success = False
        results = {
            'success': success,
            'status': status,
            'existing_office_objects_dict': existing_office_objects_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    if not ballot_returned.latitude or not ballot_returned.longitude:
        # Delete VoterBallotSaved
        voter_ballot_saved_manager = VoterBallotSavedManager()
        results = voter_ballot_saved_manager.delete_voter_ballot_saved_by_voter_id(
            voter_id=ballot_returned.voter_id, google_civic_election_id=google_civic_election_id)
        status += results['status']

        # Delete BallotItem entries
        ballot_item_list_manager = BallotItemListManager()
        results = ballot_item_list_manager.delete_all_ballot_items_for_voter(
            voter_id=ballot_returned.voter_id, google_civic_election_id=google_civic_election_id)
        status += results['status']

        try:
            # Delete BallotReturned
            ballot_returned.delete()
            status += "BALLOT_RETURNED_WITHOUT_LAT_LONG_DELETED "
        except Exception as e:
            status += "BALLOT_RETURNED_DELETE_FAILED " + str(e) + " "

        success = False
        status += "RETRIEVE_DISTRICTS-MISSING_BALLOT_RETURNED_LATITUDE_LONGITUDE "
        results = {
            'success': success,
            'status': status,
            'existing_office_objects_dict': existing_office_objects_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'existing_measure_objects_dict': existing_measure_objects_dict,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        }
        return results

    try:
        # Get the electoral_districts at this lat/long
        response = requests.get(
            BALLOTPEDIA_API_SAMPLE_BALLOT_ELECTIONS_URL,
            headers=MAIL_HEADERS,
            params={
                "lat": ballot_returned.longitude,
                "long": ballot_returned.latitude,
                # NOTE: Ballotpedia appears to have swapped latitude and longitude
                # "lat": ballot_returned.latitude,
                # "long": ballot_returned.longitude,
            })
        structured_json = json.loads(response.text)

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_ELECTIONS_TYPE,
                                                             google_civic_election_id=google_civic_election_id,
                                                             ballotpedia_election_id=0)

        groom_results = groom_and_store_sample_ballot_elections_api_v4(structured_json, google_civic_election_id)
        ballotpedia_district_id_list = groom_results['ballotpedia_district_id_list']
        if not ballotpedia_district_id_list or len(ballotpedia_district_id_list) == 0:
            status += "NO_BALLOTPEDIA_DISTRICTS_RETURNED-BALLOT_RETURNED "
            success = False
            batch_header_id = 0
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
                'existing_office_objects_dict': existing_office_objects_dict,
                'existing_candidate_objects_dict': existing_candidate_objects_dict,
                'existing_measure_objects_dict': existing_measure_objects_dict,
                'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
            }
            return results

        office_district_string = ""
        office_district_count = 0
        ballotpedia_district_id_not_used_list = []
        for one_district in ballotpedia_district_id_list:
            # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
            #  office_district_string, but capture the districts not used
            # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
            if len(office_district_string) < 3796:
                office_district_string += str(one_district) + ","
                office_district_count += 1
            else:
                # In the future we might want to set up a second query to get the races for these districts
                ballotpedia_district_id_not_used_list.append(one_district)

        # Remove last comma
        if office_district_count > 1:
            office_district_string = office_district_string[:-1]
        # chunks_of_district_strings.append(office_district_string)

        # Get the electoral_districts at this lat/long
        response = requests.get(BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL, headers=MAIL_HEADERS, params={
            "districts": office_district_string,
            "election_date": election_day_text,
        })
        structured_json = json.loads(response.text)

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_TYPE,
                                                             google_civic_election_id=google_civic_election_id,
                                                             ballotpedia_election_id=0)

        groom_results = groom_and_store_sample_ballot_results_api_v4(
            structured_json,
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            voter_id=ballot_returned.voter_id,
            election_day_text=election_day_text,
            existing_office_objects_dict=existing_office_objects_dict,
            existing_candidate_objects_dict=existing_candidate_objects_dict,
            existing_measure_objects_dict=existing_measure_objects_dict,
            new_office_we_vote_ids_list=new_office_we_vote_ids_list,
            new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
            new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
            )
        status += groom_results['status']
        ballot_item_dict_list = groom_results['ballot_item_dict_list']
        existing_office_objects_dict = groom_results['existing_office_objects_dict']
        existing_candidate_objects_dict = groom_results['existing_candidate_objects_dict']
        existing_measure_objects_dict = groom_results['existing_measure_objects_dict']
        new_office_we_vote_ids_list = groom_results['new_office_we_vote_ids_list']
        new_candidate_we_vote_ids_list = groom_results['new_candidate_we_vote_ids_list']
        new_measure_we_vote_ids_list = groom_results['new_measure_we_vote_ids_list']

        # If we successfully save a ballot, update the BallotReturned entry to update the date_last_changed
        if ballot_item_dict_list and len(ballot_item_dict_list) > 0:
            try:
                ballot_returned.save()
            except Exception as e:
                status += "FAILED_TO_UPDATE_BALLOT_RETURNED " + str(e) + " "

            results = store_ballotpedia_json_response_to_import_batch_system(
                modified_json_list=ballot_item_dict_list,
                google_civic_election_id=google_civic_election_id,
                kind_of_batch=IMPORT_BALLOT_ITEM,
                batch_set_id=batch_set_id,
                state_code=state_code)
            status += results['status']
        else:
            status += "NO_BALLOT_ITEMS_SAVED "
    except Exception as e:
        success = False
        status += 'ERROR FAILED retrieve_ballot_items_from_polling_location ' \
                  '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'existing_office_objects_dict': existing_office_objects_dict,
        'existing_candidate_objects_dict': existing_candidate_objects_dict,
        'existing_measure_objects_dict': existing_measure_objects_dict,
        'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
    }
    return results


def retrieve_ballotpedia_district_id_list_for_polling_location(
        google_civic_election_id, polling_location_we_vote_id="", polling_location=None,
        force_district_retrieve_from_ballotpedia=False):
    success = True
    status = ""
    state_code = ""
    state_code_found = False
    could_not_get_or_create_count = 0
    polling_location_found = False
    ballotpedia_district_id_list = []
    force_district_retrieve_from_ballotpedia = positive_value_exists(force_district_retrieve_from_ballotpedia)

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        results = {
            'success': False,
            'status': "Error: Missing polling location we vote id and polling_location_object",
            'ballotpedia_district_id_list': ballotpedia_district_id_list,
        }
        return results

    polling_location_latitude = 0
    polling_location_longitude = 0
    if polling_location:
        polling_location_found = True
        polling_location_latitude = polling_location.latitude
        polling_location_longitude = polling_location.longitude
        polling_location_we_vote_id = polling_location.we_vote_id
        state_code = polling_location.state
    elif positive_value_exists(polling_location_we_vote_id):
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_latitude = polling_location.latitude
            polling_location_longitude = polling_location.longitude
            state_code = polling_location.state
            polling_location_found = True

    if positive_value_exists(state_code):
        state_code_found = True

    if polling_location_found and state_code_found:
        if not polling_location.latitude or not polling_location.longitude:
            success = False
            status += "RETRIEVE_DISTRICTS-MISSING_LATITUDE_LONGITUDE "
            results = {
                'success': success,
                'status': status,
                'ballotpedia_district_id_list': ballotpedia_district_id_list,
            }
            return results

        # Check to see if we have already stored the ballotpedia districts
        electoral_district_manager = ElectoralDistrictManager()
        ballotpedia_district_id_list_found = False
        if positive_value_exists(force_district_retrieve_from_ballotpedia):
            # Delete any existing links between this district and this polling location
            results = electoral_district_manager.delete_electoral_district_link(
                    polling_location_we_vote_id=polling_location_we_vote_id)
            if not results['success']:
                status += results['status']
        else:
            results = electoral_district_manager.retrieve_ballotpedia_district_ids_for_polling_location(
                polling_location_we_vote_id)
            if results['ballotpedia_district_id_list_found']:
                ballotpedia_district_id_list = results['ballotpedia_district_id_list']
                ballotpedia_district_id_list_found = True
            else:
                ballotpedia_district_id_list = []
                ballotpedia_district_id_list_found = False

        if ballotpedia_district_id_list_found and not force_district_retrieve_from_ballotpedia:
            pass
        else:
            latitude_longitude = str(polling_location.latitude) + "," + str(polling_location.longitude)
            response = requests.get(BALLOTPEDIA_API_CONTAINS_URL, params={
                "access_token": BALLOTPEDIA_API_KEY,
                "point": latitude_longitude,
            })

            #if response.status_code == requests.codes.ok:
            structured_json = json.loads(response.text)
            #else:
            #    success = False
            #    status += response.text + " "
            #    results = {
            #        'success': success,
            #        'status': status,
            #        'ballotpedia_district_id_list': ballotpedia_district_id_list,
            #    }
            #    return results

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
            ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_CONTAINS_TYPE,
                                                                 ballotpedia_election_id=0)

            contains_api = True
            groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id, state_code,
                                                                  contains_api)
            ballotpedia_district_json_list = groom_results['modified_json_list']

            electoral_district_manager = ElectoralDistrictManager()
            for one_district_json in ballotpedia_district_json_list:
                if positive_value_exists(one_district_json['ballotpedia_district_id']):
                    ballotpedia_district_id = one_district_json['ballotpedia_district_id']
                    ballotpedia_district_id_list.append(ballotpedia_district_id)

                    # See if this district (get_or_create) is already in the database
                    try:
                        if not positive_value_exists(state_code):
                            state_code = one_district_json['state_code']
                        if positive_value_exists(one_district_json['latitude']):
                            ballotpedia_district_latitude = one_district_json['latitude']
                        else:
                            ballotpedia_district_latitude = polling_location_latitude
                        if positive_value_exists(one_district_json['longitude']):
                            ballotpedia_district_longitude = one_district_json['longitude']
                        else:
                            ballotpedia_district_longitude = polling_location_longitude

                        defaults = {
                            'ballotpedia_district_id':  one_district_json['ballotpedia_district_id'],
                            'ballotpedia_district_kml':  one_district_json['kml'],
                            'ballotpedia_district_latitude':  ballotpedia_district_latitude,
                            'ballotpedia_district_longitude':  ballotpedia_district_longitude,
                            'ballotpedia_district_type':  one_district_json['type'],
                            'ballotpedia_district_url':  one_district_json['url'],
                            'ballotpedia_district_ocd_id':  one_district_json['ocdid'],
                            'electoral_district_name':  one_district_json['ballotpedia_district_name'],
                            'state_code': state_code,
                        }
                        electoral_district, new_electoral_district_created = ElectoralDistrict.objects.get_or_create(
                            ballotpedia_district_id=one_district_json['ballotpedia_district_id'],
                            defaults=defaults)
                        if not positive_value_exists(electoral_district.we_vote_id) \
                                or not positive_value_exists(new_electoral_district_created):
                            # Trigger the creation of an electoral_district_we_vote_id, or save if this was a "get"
                            electoral_district.save()
                        electoral_district_we_vote_id = electoral_district.we_vote_id

                        # Now create a link between this district and this polling location
                        results = \
                            electoral_district_manager.update_or_create_electoral_district_link_to_polling_location(
                                polling_location_we_vote_id, electoral_district_we_vote_id, ballotpedia_district_id,
                                state_code)
                        if not results['success']:
                            status += results['status']
                    except Exception as e:
                        could_not_get_or_create_count += 1

    if positive_value_exists(could_not_get_or_create_count):
        status += "ELECTORAL_DISTRICT-COULD_NOT_GET_OR_CREATE: " + str(could_not_get_or_create_count) + " "

    results = {
        'success': success,
        'status': status,
        'ballotpedia_district_id_list': ballotpedia_district_id_list,
    }
    return results


def retrieve_ballotpedia_offices_by_district_from_api(google_civic_election_id, state_code,
                                                      ballotpedia_district_id_list):
    success = True
    status = ""
    multiple_batches_found = False

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
            'batch_header_id':  0,
        }
        return results

    if not len(ballotpedia_district_id_list):
        results = {
            'success': False,
            'status': "Error: Missing any districts",
            'batch_header_id': 0,
        }
        return results

    batch_header_id = 0
    election_day_text = ""
    election_day_year = ""
    election_manager = ElectionManager()
    kind_of_batch = ""
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        election_day_text = election.election_day_text
        election_day_year = election_day_text[:4]

    ballotpedia_district_id_not_used_list = []
    chunks_of_district_strings = []
    office_district_string = ""
    office_district_count = 0
    for one_district in ballotpedia_district_id_list:
        # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
        #  office_district_string, but capture the districts not used
        # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
        if len(office_district_string) < 3796:
            office_district_string += str(one_district) + ","
            office_district_count += 1
        else:
            # In the future we might want to set up a second query to get the races for these districts
            ballotpedia_district_id_not_used_list.append(one_district)

    # Remove last comma
    if office_district_count > 1:
        office_district_string = office_district_string[:-1]
    chunks_of_district_strings.append(office_district_string)

    # Now add all of the districts that were missed from the first retrieve
    while len(ballotpedia_district_id_not_used_list):
        office_district_string = ""
        office_district_count = 0
        temp_ballotpedia_district_id_not_used_list = []
        for one_district in ballotpedia_district_id_not_used_list:
            # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
            #  office_district_string, but capture the districts not used
            # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
            if len(office_district_string) < 3796:
                office_district_string += str(one_district) + ","
                office_district_count += 1
            else:
                # In the future we might want to set up a second query to get the races for these districts
                temp_ballotpedia_district_id_not_used_list.append(one_district)

        # Remove last comma
        if office_district_count > 1:
            office_district_string = office_district_string[:-1]
        chunks_of_district_strings.append(office_district_string)

        ballotpedia_district_id_not_used_list = temp_ballotpedia_district_id_not_used_list

    kind_of_election_list = []
    kind_of_election_dict = {
        'kind_of_election':             'general_election',
        'kind_of_election_filter_key':  'general_election_date',
    }
    kind_of_election_list.append(kind_of_election_dict)
    kind_of_election_dict = {
        'kind_of_election':             'general_runoff_election',
        'kind_of_election_filter_key':  'general_runoff_election_date',
    }
    kind_of_election_list.append(kind_of_election_dict)
    kind_of_election_dict = {
        'kind_of_election':             'primary_election',
        'kind_of_election_filter_key':  'primary_election_date',
    }
    kind_of_election_list.append(kind_of_election_dict)
    kind_of_election_dict = {
        'kind_of_election':             'primary_runoff_election',
        'kind_of_election_filter_key':  'primary_runoff_election_date',
    }
    kind_of_election_list.append(kind_of_election_dict)

    batches_found = 0
    final_json_list = []
    for office_district_string in chunks_of_district_strings:
        for kind_of_election_dict in kind_of_election_list:
            ballotpedia_kind_of_election = kind_of_election_dict['kind_of_election']

            response = requests.get(BALLOTPEDIA_API_RACES_URL, params={
                "access_token":                                 BALLOTPEDIA_API_KEY,
                "filters[year][eq]":                            election_day_year,
                "filters[office_district][in]":                 office_district_string,
                "filters[" + kind_of_election_dict['kind_of_election_filter_key'] + "][eq]":   election_day_text,
                "limit":                                        1000,
            })

            if not hasattr(response, 'text') or not positive_value_exists(response.text):
                success = False
                status += "NO_RESPONSE_TEXT_FOUND "
                if positive_value_exists(response.url):
                    shortened_url = response.url[:1000]
                    status += ": " + shortened_url + " "
                continue
                # results = {
                #     'success': success,
                #     'status': status,
                #     'batch_header_id': batch_header_id,
                # }
                # return results

            if hasattr(response, 'success') and not positive_value_exists(response.success):
                success = False
                status += "RESPONSE_SUCCESS_IS_FALSE"
                if positive_value_exists(response.url):
                    shortened_url = response.url[:1000]
                    status += ": " + shortened_url + " "
                if positive_value_exists(response.error):
                    status += "error: " + str(response.error)
                continue
                # results = {
                #     'success': success,
                #     'status': status,
                #     'batch_header_id': batch_header_id,
                # }
                # return results

            if hasattr(response, 'ok') and not positive_value_exists(response.ok):
                success = False
                status += "RESPONSE_OK_IS_FALSE"
                if positive_value_exists(response.url):
                    shortened_url = response.url[:1000]
                    status += ": " + shortened_url + " "
                if hasattr(response, 'status_code'):
                    status += "status_code: " + str(response.status_code)
                    if response.status_code == 414:
                        status += " Too many office_districts sent"
                continue
                # results = {
                #     'success': success,
                #     'status': status,
                #     'batch_header_id': batch_header_id,
                # }
                # return results

            structured_json = json.loads(response.text)

            # Use Ballotpedia API call counter to track the number of queries we are doing each day
            ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
            ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_RACES_TYPE,
                                                                 google_civic_election_id=google_civic_election_id)

            groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id, state_code,
                                                                  kind_of_election=ballotpedia_kind_of_election)
            modified_json_list = groom_results['modified_json_list']
            kind_of_batch = groom_results['kind_of_batch']

            for one_new_dict in modified_json_list:
                already_in_final_dict = False
                for one_final_dict in final_json_list:
                    if one_new_dict['ballotpedia_race_id'] == one_final_dict['ballotpedia_race_id']:
                        already_in_final_dict = True
                        continue
                if not already_in_final_dict:
                    final_json_list.append(one_new_dict)

        # Since the overall script might time out, we store the offices in an intermediate step
        if positive_value_exists(len(final_json_list)):
            status += "OFFICES_RETURNED "
            results = store_ballotpedia_json_response_to_import_batch_system(
                final_json_list, google_civic_election_id, kind_of_batch, state_code=state_code)
            final_json_list = []
            status += results['status']
            if 'batch_header_id' in results:
                batches_found += 1
                batch_header_id = results['batch_header_id']
        else:
            status += "NO_OFFICES_RETURNED "

    if batches_found > 1:
        multiple_batches_found = True
    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'multiple_batches_found': multiple_batches_found,
    }
    return results


def retrieve_ballotpedia_measures_by_district_from_api(google_civic_election_id, state_code,
                                                       ballotpedia_district_id_list):
    success = True
    status = ""
    multiple_batches_found = False

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id for measures",
            'batch_header_id': 0,
        }
        return results

    if not len(ballotpedia_district_id_list):
        results = {
            'success': False,
            'status': "Error: Missing any districts for measures",
            'batch_header_id': 0,
        }
        return results

    batch_header_id = 0
    ballotpedia_election_id = 0
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']

    ballotpedia_election_query = BallotpediaElection.objects.filter(
        google_civic_election_id=google_civic_election_id)
    if positive_value_exists(state_code):
        ballotpedia_election_query = ballotpedia_election_query.filter(state_code__iexact=state_code)
    ballotpedia_election_list = list(ballotpedia_election_query)

    if not positive_value_exists(len(ballotpedia_election_list)):
        results = {
            'success': False,
            'status': "Error: Missing Ballotpedia election ids for measures",
            'batch_header_id': 0,
        }
        return results

    # #########################
    # Get string with all elections within which we want to check for measures
    ballotpedia_elections_string = ""
    ballotpedia_election_count = 0
    for one_ballotpedia_election in ballotpedia_election_list:
        if positive_value_exists(one_ballotpedia_election.ballotpedia_election_id):
            ballotpedia_elections_string += str(one_ballotpedia_election.ballotpedia_election_id) + ","
            ballotpedia_election_count += 1
    # Remove last comma
    if ballotpedia_election_count > 1:
        ballotpedia_elections_string = ballotpedia_elections_string[:-1]

    # #########################
    # Get string with all districts within which we want to check for measures
    ballotpedia_district_id_not_used_list = []
    chunks_of_district_strings = []
    measure_district_string = ""
    measure_district_count = 0
    for one_district in ballotpedia_district_id_list:
        # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
        #  measure_district_string, but capture the districts not used
        # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
        if len(measure_district_string) < 3796:
            measure_district_string += str(one_district) + ","
            measure_district_count += 1
        else:
            # In the future we might want to set up a second query to get the races for these districts
            ballotpedia_district_id_not_used_list.append(one_district)

    # Remove last comma
    if measure_district_count > 1:
        measure_district_string = measure_district_string[:-1]
    chunks_of_district_strings.append(measure_district_string)

    # Now add all of the districts that were missed from the first retrieve
    while len(ballotpedia_district_id_not_used_list):
        measure_district_string = ""
        measure_district_count = 0
        temp_ballotpedia_district_id_not_used_list = []
        for one_district in ballotpedia_district_id_not_used_list:
            # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
            #  measure_district_string, but capture the districts not used
            # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
            if len(measure_district_string) < 3796:
                measure_district_string += str(one_district) + ","
                measure_district_count += 1
            else:
                # In the future we might want to set up a second query to get the races for these districts
                temp_ballotpedia_district_id_not_used_list.append(one_district)

        # Remove last comma
        if measure_district_count > 1:
            measure_district_string = measure_district_string[:-1]
        chunks_of_district_strings.append(measure_district_string)

        ballotpedia_district_id_not_used_list = temp_ballotpedia_district_id_not_used_list

    batches_found = 0
    final_json_list = []
    measures_already_retrieved = []
    for measure_district_string in chunks_of_district_strings:
        response = requests.get(BALLOTPEDIA_API_MEASURES_URL, params={
            "access_token":             BALLOTPEDIA_API_KEY,
            "filters[election][in]":    ballotpedia_elections_string,
            "filters[district][in]":    measure_district_string,
            "limit":                    1000,
        })

        if not hasattr(response, 'text') or not positive_value_exists(response.text):
            success = False
            status += "NO_RESPONSE_TEXT_FOUND"
            if positive_value_exists(response.url):
                status += ": " + response.url
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
            }
            return results

        if hasattr(response, 'success') and not positive_value_exists(response.success):
            success = False
            status += "RESPONSE_SUCCESS_IS_FALSE"
            if positive_value_exists(response.url):
                status += ": " + response.url + " "
            if positive_value_exists(response.error):
                status += "error: " + str(response.error)
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
            }
            return results

        try:
            structured_json = json.loads(response.text)
        except Exception as e:
            success = False
            status += "JSON.LOADS_FAILED " + str(e) + " "
            results = {
                'success': success,
                'status': status,
                'batch_header_id': batch_header_id,
            }
            return results

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_MEASURES_TYPE,
                                                             google_civic_election_id=google_civic_election_id)

        groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id, state_code)
        modified_json_list = groom_results['modified_json_list']
        kind_of_batch = groom_results['kind_of_batch']
        for one_new_dict in modified_json_list:
            if one_new_dict['ballotpedia_measure_id'] not in measures_already_retrieved:
                final_json_list.append(one_new_dict)
                measures_already_retrieved.append(one_new_dict['ballotpedia_measure_id'])

        # Since the overall script might time out, we store the offices in an intermediate step
        if positive_value_exists(len(final_json_list)):
            status += "MEASURES_RETURNED "
            results = store_ballotpedia_json_response_to_import_batch_system(
                final_json_list, google_civic_election_id, kind_of_batch, state_code=state_code)
            final_json_list = []
            batches_found += 1
            status += results['status']
            if 'batch_header_id' in results:
                batch_header_id = results['batch_header_id']
        else:
            status += "NO_MEASURES_RETURNED "

    if batches_found > 1:
        multiple_batches_found = True
    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'multiple_batches_found': multiple_batches_found,
    }
    return results


def retrieve_ballotpedia_candidate_image_from_api(ballotpedia_image_id, google_civic_election_id=0):
    success = True
    status = ""

    if not positive_value_exists(ballotpedia_image_id):
        results = {
            'success': False,
            'status': "RETRIEVE_BALLOTPEDIA_CANDIDATE_IMAGE-MISSING_IMAGE_ID ",
        }
        return results

    response = requests.get(BALLOTPEDIA_API_FILES_URL + "/" + str(ballotpedia_image_id), params={
        "access_token": BALLOTPEDIA_API_KEY,
    })

    if not positive_value_exists(response.text):
        status += "NO_RESPONSE_TEXT_FOUND"
        if positive_value_exists(response.url):
            status += ": " + response.url
        results = {
            'success': success,
            'status': status,
        }
        return results

    structured_json = json.loads(response.text)

    # Use Ballotpedia API call counter to track the number of queries we are doing each day
    ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
    ballotpedia_api_counter_manager.create_counter_entry(
        BALLOTPEDIA_API_FILES_TYPE, google_civic_election_id=google_civic_election_id)

    profile_image_url_https = None
    if 'data' in structured_json:
        if 'meta' in structured_json:
            if 'table' in structured_json['meta']:
                if structured_json['meta']['table'] == 'directus_files':
                    files_json = structured_json['data']
                    profile_image_url_https = files_json['url']

    results = {
        'success': success,
        'status': status,
        'profile_image_url_https': profile_image_url_https,
    }
    return results


def groom_and_store_sample_ballot_elections_api_v4(structured_json, google_civic_election_id):
    status = ""
    success = False
    ballotpedia_district_id_list = []

    if 'data' in structured_json and 'districts' in structured_json['data'] and \
            positive_value_exists(structured_json['data']['districts']):
        # electoral_district_manager = ElectoralDistrictManager()
        districts_json_list = structured_json['data']['districts']
        for one_district_json in districts_json_list:
            if 'id' in one_district_json and positive_value_exists(one_district_json['id']):
                ballotpedia_district_id = one_district_json['id']
                ballotpedia_district_id_list.append(ballotpedia_district_id)

                # See if this district (get_or_create) is already in the database
                # results = electoral_district_manager.retrieve_electoral_district(
                #     ballotpedia_district_id=ballotpedia_district_id)
                # if not results['electoral_district_found']:
                #     # Create new district entry
                #     pass
                # else:
                #     # Check to see if we need to update district
                #     pass
                # try:
                #     if not positive_value_exists(state_code):
                #         state_code = one_district_json['state_code']
                #     if positive_value_exists(one_district_json['latitude']):
                #         ballotpedia_district_latitude = one_district_json['latitude']
                #     else:
                #         ballotpedia_district_latitude = polling_location_latitude
                #     if positive_value_exists(one_district_json['longitude']):
                #         ballotpedia_district_longitude = one_district_json['longitude']
                #     else:
                #         ballotpedia_district_longitude = polling_location_longitude
                #
                #     defaults = {
                #         'ballotpedia_district_id': one_district_json['ballotpedia_district_id'],
                #         'ballotpedia_district_kml': one_district_json['kml'],
                #         'ballotpedia_district_latitude': ballotpedia_district_latitude,
                #         'ballotpedia_district_longitude': ballotpedia_district_longitude,
                #         'ballotpedia_district_type': one_district_json['type'],
                #         'ballotpedia_district_url': one_district_json['url'],
                #         'ballotpedia_district_ocd_id': one_district_json['ocdid'],
                #         'electoral_district_name': one_district_json['ballotpedia_district_name'],
                #         'state_code': state_code,
                #     }
                #     electoral_district, new_electoral_district_created = ElectoralDistrict.objects.get_or_create(
                #         ballotpedia_district_id=one_district_json['ballotpedia_district_id'],
                #         defaults=defaults)
                #     if not positive_value_exists(electoral_district.we_vote_id) \
                #             or not positive_value_exists(new_electoral_district_created):
                #         # Trigger the creation of an electoral_district_we_vote_id, or save if this was a "get"
                #         electoral_district.save()
                #     electoral_district_we_vote_id = electoral_district.we_vote_id
                #
                #     # Now create a link between this district and this polling location
                #     results = \
                #         electoral_district_manager.update_or_create_electoral_district_link_to_polling_location(
                #             polling_location_we_vote_id, electoral_district_we_vote_id, ballotpedia_district_id,
                #             state_code)
                #     if not results['success']:
                #         status += results['status']
                # except Exception as e:
                #     could_not_get_or_create_count += 1

    results = {
        'success':                      success,
        'status':                       status,
        'google_civic_election_id':     google_civic_election_id,
        'ballotpedia_district_id_list': ballotpedia_district_id_list,
    }
    return results


def groom_and_store_sample_ballot_results_api_v4(structured_json,
                                                 google_civic_election_id,
                                                 state_code='',
                                                 polling_location_we_vote_id='',
                                                 election_day_text='',
                                                 voter_id=0,
                                                 existing_office_objects_dict={},
                                                 existing_candidate_objects_dict={},
                                                 existing_measure_objects_dict={},
                                                 new_office_we_vote_ids_list=[],
                                                 new_candidate_we_vote_ids_list=[],
                                                 new_measure_we_vote_ids_list=[],
                                                 ):
    from image.controllers import cache_master_and_resized_image, BALLOTPEDIA_IMAGE_SOURCE
    status = ""
    success = False
    generated_ballot_order = 0
    ballot_item_dict_list = []

    contest_office_manager = ContestOfficeManager()
    candidate_manager = CandidateCampaignManager()
    measure_manager = ContestMeasureManager()
    politician_manager = PoliticianManager()
    office_names_with_no_state = ["President of the United States"]

    if 'data' in structured_json and 'districts' in structured_json['data']:
        districts_json_list = structured_json['data']['districts']
        for one_district_json in districts_json_list:
            district_name = ''
            if 'name' in one_district_json and positive_value_exists(one_district_json['name']):
                district_name = one_district_json['name']
            if 'races' in one_district_json and positive_value_exists(one_district_json['races']):
                races_json_list = one_district_json['races']
                for one_race_json in races_json_list:
                    # We only want to deal with the office if candidate data exists
                    candidate_data_exists = 'candidates' in one_race_json and \
                                            positive_value_exists(one_race_json['candidates'])
                    office_data_exists = 'office' in one_race_json and positive_value_exists(one_race_json['office'])

                    # Clear out prior values
                    ballotpedia_office_id = 0
                    ballotpedia_office_name = ""
                    ballotpedia_office_url = ""
                    ballotpedia_race_id = 0
                    ballotpedia_race_office_level = ""
                    ballotpedia_race_url = ""
                    candidates_json_list = []
                    contest_office = None
                    contest_office_id = 0
                    contest_office_we_vote_id = ""
                    district_id = 0
                    number_of_seats = 1
                    ocd_division_id = ""
                    office_name = ""
                    if office_data_exists:
                        if candidate_data_exists:
                            candidates_json_list = one_race_json['candidates']
                        else:
                            candidates_json_list = []
                        office_dict = one_race_json['office']

                        # Office dict
                        if 'id' in office_dict and positive_value_exists(office_dict['id']):
                            ballotpedia_office_id = office_dict['id']
                        if 'level' in office_dict and positive_value_exists(office_dict['level']):
                            ballotpedia_race_office_level = office_dict['level']
                        if 'name' in office_dict and positive_value_exists(office_dict['name']):
                            ballotpedia_office_name = office_dict['name']
                            office_name = office_dict['name']
                        if 'office_district' in office_dict and positive_value_exists(office_dict['office_district']):
                            district_id = office_dict['office_district']
                        if 'url' in office_dict and positive_value_exists(office_dict['url']):
                            ballotpedia_office_url = office_dict['url']

                        # Race dict
                        if 'id' in one_race_json and positive_value_exists(one_race_json['id']):
                            ballotpedia_race_id = convert_to_int(one_race_json['id'])
                        if 'url' in one_race_json and positive_value_exists(one_race_json['url']):
                            ballotpedia_race_url = one_race_json['url']
                        if 'number_of_seats' in one_race_json and \
                                positive_value_exists(one_race_json['number_of_seats']):
                            number_of_seats = one_race_json['number_of_seats']

                    # Check to see if this is a new office or if we have any new data
                    if positive_value_exists(ballotpedia_race_id):
                        if ballotpedia_race_id in existing_office_objects_dict:
                            contest_office = existing_office_objects_dict[ballotpedia_race_id]
                            contest_office_we_vote_id = contest_office.we_vote_id
                            contest_office_id = contest_office.id
                            office_name = contest_office.office_name
                        else:
                            office_results = contest_office_manager.retrieve_contest_office_from_ballotpedia_race_id(
                                ballotpedia_race_id=ballotpedia_race_id,
                                read_only=True)
                            if office_results['contest_office_found']:
                                contest_office = office_results['contest_office']
                                contest_office_we_vote_id = contest_office.we_vote_id
                                contest_office_id = contest_office.id
                                office_name = contest_office.office_name
                                if convert_to_int(contest_office.google_civic_election_id) != \
                                        convert_to_int(google_civic_election_id):
                                    # We need to record that his office (and all positions under it) came from
                                    #  another election
                                    origin_google_civic_election_id = 0
                                    try:
                                        origin_google_civic_election_id = \
                                            convert_to_int(contest_office.google_civic_election_id)
                                    except Exception as e:
                                        status += "ORIGIN_GOOGLE_CIVIC_ELECTION_ID: " + str(e) + " "
                                    visiting_results = contest_office_manager.update_or_create_visiting_link(
                                        contest_office_we_vote_id=contest_office_we_vote_id,
                                        ballotpedia_race_id=ballotpedia_race_id,
                                        host_google_civic_election_id=google_civic_election_id,
                                        origin_google_civic_election_id=origin_google_civic_election_id,
                                    )
                                    if not visiting_results['success']:
                                        status += visiting_results['status']

                                existing_office_objects_dict[ballotpedia_race_id] = contest_office
                                # In the future, we will want to look for updated data to save
                            elif office_results['MultipleObjectsReturned']:
                                status += "MORE_THAN_ONE_OFFICE_WITH_SAME_BALLOTPEDIA_RACE_ID: " \
                                          "" + str(ballotpedia_race_id) + " "
                                continue
                            elif not office_results['success']:
                                status += "RETRIEVE_BY_BALLOTPEDIA_RACE_ID_FAILED: "
                                status += office_results['status']
                                continue
                        if positive_value_exists(contest_office_we_vote_id):
                            generated_ballot_order += 1
                            office_json = {
                                'ballot_item_display_name': contest_office.office_name,
                                'contest_office_we_vote_id': contest_office.we_vote_id,
                                'contest_office_id': contest_office.id,
                                'contest_office_name': contest_office.office_name,
                                'local_ballot_order': generated_ballot_order,
                                'election_day_text': election_day_text,
                                'state_code': state_code,
                                'polling_location_we_vote_id': polling_location_we_vote_id,
                                'voter_id': voter_id,
                            }
                            ballot_item_dict_list.append(office_json)
                        else:
                            # Create an office entry
                            updated_contest_office_values = {
                                'ballotpedia_race_id': ballotpedia_race_id,
                                'google_civic_election_id': google_civic_election_id,
                            }
                            if positive_value_exists(ballotpedia_office_id):
                                updated_contest_office_values["ballotpedia_office_id"] = ballotpedia_office_id
                            if positive_value_exists(ballotpedia_office_url):
                                updated_contest_office_values["ballotpedia_office_url"] = ballotpedia_office_url
                            if positive_value_exists(ballotpedia_race_office_level):
                                updated_contest_office_values["ballotpedia_race_office_level"] = \
                                    ballotpedia_race_office_level
                            if positive_value_exists(ballotpedia_race_url):
                                updated_contest_office_values["ballotpedia_race_url"] = ballotpedia_race_url
                            if positive_value_exists(district_id):
                                updated_contest_office_values["district_id"] = district_id
                            if positive_value_exists(district_name):
                                updated_contest_office_values["district_name"] = district_name
                            if positive_value_exists(number_of_seats):
                                updated_contest_office_values["number_elected"] = number_of_seats
                            if positive_value_exists(ocd_division_id):
                                updated_contest_office_values["ocd_division_id"] = ocd_division_id
                            if positive_value_exists(office_name):
                                updated_contest_office_values["office_name"] = office_name
                                # We store the literal spelling here so we can match in the future
                                updated_contest_office_values["ballotpedia_office_name"] = ballotpedia_office_name
                            if positive_value_exists(state_code) and office_name not in office_names_with_no_state:
                                updated_contest_office_values["state_code"] = state_code
                            elif office_name in office_names_with_no_state:
                                updated_contest_office_values["state_code"] = 'NA'
                            create_results = contest_office_manager.update_or_create_contest_office(
                                ballotpedia_race_id=ballotpedia_race_id,
                                google_civic_election_id=google_civic_election_id,
                                office_name=office_name,
                                updated_contest_office_values=updated_contest_office_values)
                            if create_results['new_office_created']:
                                new_office_created = True
                                contest_office = create_results['contest_office']
                                contest_office_id = contest_office.id
                                contest_office_we_vote_id = contest_office.we_vote_id
                                generated_ballot_order += 1
                                office_json = {
                                    'ballot_item_display_name': contest_office.office_name,
                                    'contest_office_we_vote_id': contest_office.we_vote_id,
                                    'contest_office_id': contest_office.id,
                                    'contest_office_name': contest_office.office_name,
                                    'local_ballot_order': generated_ballot_order,
                                    'election_day_text': election_day_text,
                                    'state_code': state_code,
                                    'polling_location_we_vote_id': polling_location_we_vote_id,
                                    'voter_id': voter_id,
                                }
                                ballot_item_dict_list.append(office_json)
                                if contest_office_we_vote_id not in new_office_we_vote_ids_list:
                                    new_office_we_vote_ids_list.append(contest_office_we_vote_id)
                    # Now move onto dealing with candidates
                    if positive_value_exists(contest_office_we_vote_id):
                        for candidate_dict in candidates_json_list:
                            image_dict = {}
                            person_dict = {}
                            party_affiliation_dict = {}
                            if 'person' in candidate_dict:
                                if candidate_dict['person']:
                                    person_dict = candidate_dict['person']
                                    if 'image' in person_dict:
                                        if person_dict['image']:
                                            image_dict = person_dict['image']
                            if 'party_affiliation' in candidate_dict:
                                party_affiliation_list = candidate_dict['party_affiliation']
                                if len(party_affiliation_list):
                                    party_affiliation_dict = party_affiliation_list[0]

                            # Clear out previous variables
                            ballotpedia_candidate_id = 0
                            ballotpedia_candidate_name = ""
                            ballotpedia_profile_image_url_https = ''
                            candidate_campaign = None
                            candidate_campaign_we_vote_id = ''
                            new_candidate_created = False
                            save_ballotpedia_image = False

                            # candidate_dict
                            if 'id' in candidate_dict and positive_value_exists(candidate_dict['id']):
                                ballotpedia_candidate_id = convert_to_int(candidate_dict['id'])

                            if positive_value_exists(ballotpedia_candidate_id):
                                if ballotpedia_candidate_id in existing_candidate_objects_dict:
                                    candidate_campaign = existing_candidate_objects_dict[ballotpedia_candidate_id]
                                    candidate_campaign_we_vote_id = candidate_campaign.we_vote_id
                                else:
                                    # Does candidate already exist?
                                    candidate_results = \
                                        candidate_manager.retrieve_candidate_campaign_from_ballotpedia_candidate_id(
                                            ballotpedia_candidate_id=ballotpedia_candidate_id,
                                            read_only=True
                                        )
                                    if candidate_results['candidate_campaign_found']:
                                        candidate_campaign = candidate_results['candidate_campaign']
                                        candidate_campaign_we_vote_id = candidate_campaign.we_vote_id
                                        if ballotpedia_candidate_id not in existing_candidate_objects_dict:
                                            existing_candidate_objects_dict[ballotpedia_candidate_id] = \
                                                candidate_campaign
                                        # In the future, we will want to look for updated data to save
                                    elif candidate_results['MultipleObjectsReturned']:
                                        status += "MORE_THAN_ONE_CANDIDATE_WITH_SAME_BALLOTPEDIA_CANDIDATE_ID "
                                        continue
                                    elif not candidate_results['success']:
                                        status += "RETRIEVE_BY_BALLOTPEDIA_CANDIDATE_ID_FAILED "
                                        status += candidate_results['status']
                                        continue
                                if positive_value_exists(candidate_campaign_we_vote_id):
                                    pass
                                else:
                                    # Create new candidate
                                    update_values = {
                                        'ballotpedia_candidate_id': ballotpedia_candidate_id,
                                        'google_civic_election_id': google_civic_election_id,
                                    }

                                    # From outer loop
                                    if positive_value_exists(ballotpedia_office_id):
                                        update_values['ballotpedia_office_id'] = ballotpedia_office_id
                                    if positive_value_exists(contest_office_we_vote_id):
                                        update_values['contest_office_we_vote_id'] = contest_office_we_vote_id
                                    if positive_value_exists(contest_office_id):
                                        update_values['contest_office_id'] = contest_office_id
                                    if positive_value_exists(office_name):
                                        update_values['contest_office_name'] = office_name
                                    if positive_value_exists(state_code) and \
                                            office_name not in office_names_with_no_state:
                                        update_values['state_code'] = state_code
                                    elif office_name in office_names_with_no_state:
                                        update_values['state_code'] = 'NA'

                                    # candidate_dict
                                    if 'race' in candidate_dict and positive_value_exists(candidate_dict['race']):
                                        update_values['ballotpedia_race_id'] = convert_to_int(candidate_dict['race'])
                                    if 'is_incumbent' in candidate_dict:
                                        update_values['candidate_is_incumbent'] = candidate_dict['is_incumbent']
                                    else:
                                        update_values['candidate_is_incumbent'] = False
                                    # There are four incoming values, but isn't clear which one to use:
                                    #  primary_status, primary_runoff_status, general_status and general_runoff_status
                                    update_values['candidate_participation_status'] = "On the Ballot"
                                    if 'candidate_website_url' in candidate_dict:
                                        update_values['candidate_url'] = candidate_dict['candidate_website_url']
                                    if 'campaign_facebook_url' in candidate_dict:
                                        update_values['facebook_url'] = candidate_dict['campaign_facebook_url']

                                    # party_affiliation_dict
                                    if 'name' in party_affiliation_dict:
                                        update_values['party'] = party_affiliation_dict['name']

                                    # image_dict
                                    if image_dict and 'url' in image_dict:
                                        ballotpedia_profile_image_url_https = image_dict['url']
                                        update_values['photo_url'] = image_dict['url']
                                        save_ballotpedia_image = True

                                    # person_dict
                                    if 'name' in person_dict:
                                        update_values['candidate_name'] = person_dict['name']
                                        update_values['ballotpedia_candidate_name'] = person_dict['name']
                                        ballotpedia_candidate_name = person_dict['name']
                                    if 'summary' in person_dict:
                                        update_values['ballotpedia_candidate_summary'] = person_dict['summary']
                                    if 'url' in person_dict:
                                        update_values['ballotpedia_candidate_url'] = person_dict['url']
                                    if 'id' in person_dict:
                                        update_values['ballotpedia_person_id'] = person_dict['id']
                                    if 'contact_twitter' in person_dict:
                                        update_values['candidate_twitter_handle'] = person_dict['contact_twitter']
                                    if 'contact_website' in person_dict:
                                        update_values['candidate_contact_form_url'] = person_dict['contact_website']

                                    # These parameters are required to create a CandidateCampaign entry
                                    if positive_value_exists(ballotpedia_candidate_id) and \
                                            positive_value_exists(ballotpedia_candidate_name) \
                                            and positive_value_exists(google_civic_election_id):
                                        results = candidate_manager.create_candidate_row_entry(update_values)
                                        new_candidate_created = results['new_candidate_created']
                                        candidate_campaign = results['new_candidate']
                                        candidate_campaign_we_vote_id = candidate_campaign.we_vote_id
                                        if candidate_campaign_we_vote_id not in new_candidate_we_vote_ids_list:
                                            new_candidate_we_vote_ids_list.append(candidate_campaign_we_vote_id)

                                    if new_candidate_created and save_ballotpedia_image:
                                        cache_results = cache_master_and_resized_image(
                                            candidate_id=candidate_campaign.id,
                                            candidate_we_vote_id=candidate_campaign.we_vote_id,
                                            ballotpedia_candidate_id=candidate_campaign.ballotpedia_candidate_id,
                                            ballotpedia_image_id=candidate_campaign.ballotpedia_image_id,
                                            ballotpedia_profile_image_url=ballotpedia_profile_image_url_https,
                                            image_source=BALLOTPEDIA_IMAGE_SOURCE)
                                        cached_ballotpedia_image_url_https = cache_results[
                                            'cached_ballotpedia_image_url_https']
                                        we_vote_hosted_profile_image_url_large = cache_results[
                                            'we_vote_hosted_profile_image_url_large']
                                        we_vote_hosted_profile_image_url_medium = cache_results[
                                            'we_vote_hosted_profile_image_url_medium']
                                        we_vote_hosted_profile_image_url_tiny = cache_results[
                                            'we_vote_hosted_profile_image_url_tiny']

                                        save_candidate_campaign_results = \
                                            candidate_manager.update_candidate_ballotpedia_image_details(
                                                candidate_campaign,
                                                cached_ballotpedia_image_url_https,
                                                we_vote_hosted_profile_image_url_large,
                                                we_vote_hosted_profile_image_url_medium,
                                                we_vote_hosted_profile_image_url_tiny)
                                        candidate_campaign = save_candidate_campaign_results['candidate']
                                    # if new_candidate_created:
                                    #     # Need to update voter ballotpedia details for the candidate in future
                                    #     save_politician_details_results = \
                                    #         politician_manager.update_politician_details_from_candidate(
                                    #             candidate_campaign)

            if 'ballot_measures' in one_district_json and positive_value_exists(one_district_json['ballot_measures']):
                ballot_measures_json_list = one_district_json['ballot_measures']
                for measure_dict in ballot_measures_json_list:
                    ballotpedia_measure_id = 0
                    contest_measure = None
                    contest_measure_we_vote_id = ''
                    if 'id' in measure_dict and positive_value_exists(measure_dict['id']):
                        ballotpedia_measure_id = measure_dict['id']

                    if positive_value_exists(ballotpedia_measure_id):
                        if ballotpedia_measure_id in existing_measure_objects_dict:
                            contest_measure = existing_measure_objects_dict[ballotpedia_measure_id]
                            contest_measure_we_vote_id = contest_measure.we_vote_id
                        else:
                            # Does measure already exist?
                            measure_results = measure_manager.retrieve_contest_measure_from_ballotpedia_measure_id(
                                ballotpedia_measure_id=ballotpedia_measure_id,
                                read_only=True
                            )
                            if measure_results['contest_measure_found']:
                                contest_measure = measure_results['contest_measure']
                                contest_measure_we_vote_id = contest_measure.we_vote_id
                                if contest_measure.google_civic_election_id != google_civic_election_id:
                                    # We need to record that his measure (and all positions under it) came from
                                    #  another election
                                    pass
                                if ballotpedia_measure_id not in existing_measure_objects_dict:
                                    existing_measure_objects_dict[ballotpedia_measure_id] = contest_measure
                                # In the future, we will want to look for updated data to save
                            elif measure_results['MultipleObjectsReturned']:
                                status += "MORE_THAN_ONE_MEASURE_WITH_SAME_BALLOTPEDIA_MEASURE_ID "
                                continue
                            elif not measure_results['success']:
                                status += "RETRIEVE_BY_BALLOTPEDIA_MEASURE_ID_FAILED "
                                status += measure_results['status']
                                continue
                        if positive_value_exists(contest_measure_we_vote_id):
                            generated_ballot_order += 1
                            measure_json = {
                                'ballot_item_display_name': contest_measure.measure_title,
                                'contest_measure_we_vote_id': contest_measure.we_vote_id,
                                'contest_measure_id': contest_measure.id,
                                'contest_measure_name': contest_measure.measure_title,
                                'election_day_text': election_day_text,
                                'local_ballot_order': generated_ballot_order,
                                'measure_text': contest_measure.measure_text,
                                'measure_url': contest_measure.measure_url,
                                'no_vote_description': contest_measure.ballotpedia_no_vote_description,
                                'polling_location_we_vote_id': polling_location_we_vote_id,
                                'state_code': state_code,
                                'voter_id': voter_id,
                                'yes_vote_description': contest_measure.ballotpedia_yes_vote_description,
                            }
                            ballot_item_dict_list.append(measure_json)
                        else:
                            # Create new measure
                            update_values = {
                                'ballotpedia_measure_id': ballotpedia_measure_id,
                                'google_civic_election_id': google_civic_election_id,
                            }

                            # From outer loop
                            if positive_value_exists(district_name):
                                update_values['district_name'] = district_name
                            if positive_value_exists(election_day_text):
                                update_values['election_day_text'] = election_day_text
                            if positive_value_exists(google_civic_election_id):
                                update_values['google_civic_election_id'] = google_civic_election_id
                            if positive_value_exists(state_code):
                                update_values['state_code'] = state_code
                            generated_ballot_order += 1
                            update_values['google_ballot_placement'] = generated_ballot_order

                            # measure_dict
                            if 'name' in measure_dict and positive_value_exists(measure_dict['name']):
                                update_values['ballotpedia_measure_name'] = measure_dict['name']
                                update_values['measure_title'] = measure_dict['name']
                            if 'district' in measure_dict and positive_value_exists(measure_dict['district']):
                                update_values['ballotpedia_district_id'] = measure_dict['district']
                            if 'url' in measure_dict and positive_value_exists(measure_dict['url']):
                                update_values['ballotpedia_measure_url'] = measure_dict['url']
                            if 'summary' in measure_dict and positive_value_exists(measure_dict['summary']):
                                update_values['measure_text'] = measure_dict['summary']
                                update_values['ballotpedia_measure_summary'] = measure_dict['summary']
                            if 'yes_vote' in measure_dict and positive_value_exists(measure_dict['yes_vote']):
                                update_values['ballotpedia_yes_vote_description'] = measure_dict['yes_vote']
                            if 'no_vote' in measure_dict and positive_value_exists(measure_dict['no_vote']):
                                update_values['ballotpedia_no_vote_description'] = measure_dict['no_vote']
                            if 'status' in measure_dict and positive_value_exists(measure_dict['status']):
                                update_values['ballotpedia_measure_status'] = measure_dict['status']
                            create_results = measure_manager.update_or_create_contest_measure(
                                ballotpedia_measure_id=ballotpedia_measure_id,
                                google_civic_election_id=google_civic_election_id,
                                updated_contest_measure_values=update_values)
                            if create_results['new_measure_created']:
                                contest_measure = create_results['contest_measure']
                                contest_measure_we_vote_id = contest_measure.we_vote_id
                                measure_json = {
                                    'ballot_item_display_name': contest_measure.measure_title,
                                    'contest_measure_we_vote_id': contest_measure.we_vote_id,
                                    'contest_measure_id': contest_measure.id,
                                    'contest_measure_name': contest_measure.measure_title,
                                    'election_day_text': election_day_text,
                                    'local_ballot_order': generated_ballot_order,
                                    'measure_text': contest_measure.measure_text,
                                    'measure_url': contest_measure.measure_url,
                                    'no_vote_description': contest_measure.ballotpedia_no_vote_description,
                                    'state_code': state_code,
                                    'polling_location_we_vote_id': polling_location_we_vote_id,
                                    'voter_id': voter_id,
                                    'yes_vote_description': contest_measure.ballotpedia_yes_vote_description,
                                }
                                ballot_item_dict_list.append(measure_json)
                                if contest_measure_we_vote_id not in new_measure_we_vote_ids_list:
                                    new_measure_we_vote_ids_list.append(contest_measure_we_vote_id)

    results = {
        'success':                              success,
        'status':                               status,
        'google_civic_election_id':             google_civic_election_id,
        'ballot_item_dict_list':                ballot_item_dict_list,
        'existing_office_objects_dict':         existing_office_objects_dict,
        'existing_candidate_objects_dict':      existing_candidate_objects_dict,
        'existing_measure_objects_dict':        existing_measure_objects_dict,
        'new_office_we_vote_ids_list':          new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list':       new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list':         new_measure_we_vote_ids_list,
    }
    return results


def groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id, state_code="",
                                          contains_api=False, kind_of_election="", kind_of_election_by_race={}):
    success = False
    status = ""
    # if kind_of_batch not in (MEASURE, ELECTED_OFFICE, CONTEST_OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION,
    #                          POLITICIAN, IMPORT_BALLOT_ITEM):

    if 'data' in structured_json:
        if 'meta' in structured_json:
            if 'table' in structured_json['meta']:
                if structured_json['meta']['table'] == 'races':
                    kind_of_batch = 'CONTEST_OFFICE'
                    races_json_list = structured_json['data']
                    modified_races_json_list = []
                    # Loop through this data and move ['office']['data'] into root level
                    for one_office_json in races_json_list:
                        try:
                            # election
                            # Default the "is_..._election" to False
                            one_office_json['is_ballotpedia_primary_election'] = False
                            one_office_json['is_ballotpedia_primary_runoff_election'] = False
                            one_office_json['is_ballotpedia_general_election'] = False
                            one_office_json['is_ballotpedia_general_runoff_election'] = False
                            if kind_of_election == "primary_election":
                                inner_election_json = one_office_json['primary_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['is_ballotpedia_primary_election'] = True
                                one_office_json['election_day'] = inner_election_json['date']
                            elif kind_of_election == "primary_runoff_election":
                                inner_election_json = one_office_json['primary_runoff_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['is_ballotpedia_primary_runoff_election'] = True
                                one_office_json['election_day'] = inner_election_json['date']
                            elif kind_of_election == "general_election":
                                inner_election_json = one_office_json['general_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['is_ballotpedia_general_election'] = True
                                one_office_json['election_day'] = inner_election_json['date']
                            elif kind_of_election == "general_runoff_election":
                                inner_election_json = one_office_json['general_runoff_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['is_ballotpedia_general_runoff_election'] = True
                                one_office_json['election_day'] = inner_election_json['date']
                            else:
                                one_office_json['ballotpedia_election_id'] = 0
                                one_office_json['election_day'] = ""
                            inner_office_json = one_office_json['office']['data']
                            # Add our own key/value pairs
                            # root level
                            one_office_json['ballotpedia_race_id'] = one_office_json['id']
                            one_office_json['ballotpedia_is_marquee'] = one_office_json['is_marquee']
                            # office
                            one_office_json['ballotpedia_district_id'] = inner_office_json['district']
                            one_office_json['ballotpedia_office_id'] = inner_office_json['id']
                            one_office_json['state_code'] = inner_office_json['district_state']
                            modified_races_json_list.append(one_office_json)
                        except KeyError as e:
                            status += "OFFICE_KEY_ERROR: " + str(e) + " "

                    success = True
                    status += ""
                    results = {
                        'success': success,
                        'status': status,
                        'google_civic_election_id': google_civic_election_id,
                        'kind_of_batch': kind_of_batch,
                        'modified_json_list': modified_races_json_list,
                    }
                    return results
                elif structured_json['meta']['table'] == 'candidates':
                    kind_of_batch = 'CANDIDATE'
                    candidates_json_list = structured_json['data']
                    modified_candidates_json_list = []
                    # Loop through this data and move ['office']['data'] into root level
                    for one_candidate_json in candidates_json_list:
                        ballotpedia_race_id = 0
                        if 'race' in one_candidate_json \
                                and one_candidate_json['race'] \
                                and 'data' in one_candidate_json['race']:
                            inner_race_json = one_candidate_json['race']['data']
                            ballotpedia_race_id = inner_race_json['id']
                        else:
                            # If a race isn't included, then this candidate isn't running right now
                            continue

                        if kind_of_election_by_race[ballotpedia_race_id] == "primary_election":
                            one_candidate_json['candidate_participation_status'] = one_candidate_json['primary_status']
                            if not positive_value_exists(one_candidate_json['candidate_participation_status']) \
                                    and one_candidate_json['general_status'] \
                                    and one_candidate_json['general_status'] != "NULL":
                                # I notice that some candidates are returned with the primary_status empty, but the
                                #  general_status as "On the Ballot"
                                one_candidate_json['candidate_participation_status'] = \
                                    one_candidate_json['general_status']
                            if not positive_value_exists(one_candidate_json['candidate_participation_status']):
                                # These values are "Pu", "Pa.R" ???
                                one_candidate_json['candidate_participation_status'] = one_candidate_json['status']
                        elif kind_of_election_by_race[ballotpedia_race_id] == "primary_runoff_election":
                            one_candidate_json['candidate_participation_status'] = \
                                one_candidate_json['primary_runoff_status']
                        elif kind_of_election_by_race[ballotpedia_race_id] == "general_election":
                            one_candidate_json['candidate_participation_status'] = one_candidate_json['general_status']
                        elif kind_of_election_by_race[ballotpedia_race_id] == "general_runoff_election":
                            one_candidate_json['candidate_participation_status'] = \
                                one_candidate_json['general_runoff_status']
                        else:
                            one_candidate_json['candidate_participation_status'] = "unknown"

                        if one_candidate_json['candidate_participation_status'] \
                                not in ("Advanced", "Candidacy Declared", "Lost", "On the Ballot", "Pl", "Pu", "Pa.R"):
                            # If the candidate is not on the ballot yet or declared, we don't want to include them
                            # Pa.R == In Runoff ?
                            # Pl == Lost
                            # Pt == Withdrew
                            # Pu == Candidacy Declared
                            continue

                        try:
                            # Add our own key/value pairs
                            # root level
                            one_candidate_json['ballotpedia_candidate_id'] = one_candidate_json['id']
                            one_candidate_json['is_incumbent'] = one_candidate_json['is_incumbent']
                            one_candidate_json['google_civic_election_id'] = google_civic_election_id
                            # race
                            if 'race' in one_candidate_json \
                                    and one_candidate_json['race'] \
                                    and 'data' in one_candidate_json['race']:
                                inner_race_json = one_candidate_json['race']['data']
                                one_candidate_json['ballotpedia_race_id'] = inner_race_json['id']
                                one_candidate_json['ballotpedia_office_id'] = inner_race_json['office']
                                # If we want this here, we need to switch between primary_election and general_election
                                # one_candidate_json['ballotpedia_election_id'] = inner_race_json['election']
                                one_candidate_json['state_code'] = inner_race_json['election_district_state']
                            # person
                            if 'person' in one_candidate_json \
                                    and one_candidate_json['person'] \
                                    and 'data' in one_candidate_json['person']:
                                inner_person_json = one_candidate_json['person']['data']
                                one_candidate_json['ballotpedia_person_id'] = inner_person_json['id']
                                one_candidate_json['ballotpedia_candidate_name'] = inner_person_json['name']
                                one_candidate_json['ballotpedia_image_id'] = inner_person_json['image']
                                one_candidate_json['ballotpedia_candidate_url'] = inner_person_json['url']
                                one_candidate_json['ballotpedia_candidate_summary'] = \
                                    inner_person_json['summary']
                                one_candidate_json['candidate_url'] = inner_person_json['contact_website']
                                one_candidate_json['facebook_url'] = inner_person_json['contact_facebook']
                                one_candidate_json['ballotpedia_person_id'] = inner_person_json['id']
                                one_candidate_json['candidate_twitter_handle'] = \
                                    inner_person_json['contact_twitter']
                                one_candidate_json['candidate_gender'] = inner_person_json['gender']
                                one_candidate_json['candidate_email'] = inner_person_json['contact_email']
                                if 'crowdpac_candidate_id' in inner_person_json:
                                    one_candidate_json['crowdpac_candidate_id'] = \
                                        inner_person_json['crowdpac_candidate_id']
                                one_candidate_json['birth_day_text'] = inner_person_json['date_born']
                            # party_affiliation
                            if 'party_affiliation' in one_candidate_json \
                                    and one_candidate_json['party_affiliation'] \
                                    and 'data' in one_candidate_json['party_affiliation']:
                                inner_party_affiliation_json = one_candidate_json['party_affiliation']['data']
                                one_candidate_json['candidate_party_name'] = inner_party_affiliation_json['name']
                            # Make sure state_code exists
                            if 'state_code' not in one_candidate_json:
                                one_candidate_json['state_code'] = state_code
                            if not positive_value_exists(one_candidate_json['state_code']):
                                one_candidate_json['state_code'] = state_code

                            modified_candidates_json_list.append(one_candidate_json)
                        except KeyError as e:
                            status += "CANDIDATE_KEY_ERROR: " + str(e) + " "

                    success = True
                    status += ""
                    results = {
                        'success':                  success,
                        'status':                   status,
                        'google_civic_election_id': google_civic_election_id,
                        'kind_of_batch':            kind_of_batch,
                        'modified_json_list':       modified_candidates_json_list,
                    }
                    return results
                elif structured_json['meta']['table'] == 'ballot_measures':
                    kind_of_batch = 'MEASURE'
                    measures_json_list = structured_json['data']
                    modified_measures_json_list = []
                    # Loop through this data and move ['office']['data'] into root level
                    for one_measure_json in measures_json_list:
                        if one_measure_json['status'] \
                                not in ("On the ballot", "Qualified for the ballot"):
                            # If the candidate is not on the ballot yet or declared, we don't want to include them
                            continue

                        try:
                            inner_election_json = one_measure_json['election']['data']
                            inner_district_json = one_measure_json['district']['data']
                            # Add our own key/value pairs
                            # root
                            one_measure_json['ballotpedia_measure_id'] = one_measure_json['id']
                            one_measure_json['ballotpedia_measure_url'] = one_measure_json['url']
                            one_measure_json['ballotpedia_yes_vote_description'] = one_measure_json['yes_vote']
                            one_measure_json['ballotpedia_no_vote_description'] = one_measure_json['no_vote']
                            one_measure_json['ballotpedia_measure_url'] = one_measure_json['url']
                            one_measure_json['election_day_text'] = one_measure_json['election_date']
                            # election
                            one_measure_json['ballotpedia_election_id'] = inner_election_json['id']
                            one_measure_json['ballotpedia_election_type'] = inner_election_json['type']  # TODO
                            one_measure_json['ballotpedia_election_date'] = inner_election_json['date']  # TODO
                            # district
                            one_measure_json['ballotpedia_district_id'] = inner_district_json['id']
                            one_measure_json['state_code'] = inner_district_json['state']
                            modified_measures_json_list.append(one_measure_json)
                        except KeyError as e:
                            status += "MEASURE_KEY_ERROR: " + str(e) + " "

                    success = True
                    status += ""
                    results = {
                        'success':                  success,
                        'status':                   status,
                        'google_civic_election_id': google_civic_election_id,
                        'kind_of_batch':            kind_of_batch,
                        'modified_json_list':       modified_measures_json_list,
                    }
                    return results
    elif contains_api:
        kind_of_batch = 'IMPORT_BALLOT_ITEM'  # Update this to be "ELECTORAL_DISTRICT"
        modified_district_json_list = []
        for one_district_json in structured_json:
            try:
                # 'ballotpedia_district_id': 'ballotpedia_district_id',
                # 'ballotpedia_district_name': 'ballotpedia_district_name',
                # 'election_day_text': 'election_day_text',
                # 'local_ballot_order': 'local_ballot_order',
                # 'polling_location_we_vote_id': 'polling_location_we_vote_id',
                # 'state_code': 'state_code',
                one_district_json['ballotpedia_district_id'] = one_district_json['id']
                one_district_json['ballotpedia_district_name'] = one_district_json['name']
                one_district_json['state_code'] = one_district_json['state']
                if not positive_value_exists(one_district_json['state_code']):
                    one_district_json['state_code'] = state_code
                one_district_json['election_day_text'] = ""
                modified_district_json_list.append(one_district_json)
            except KeyError as e:
                status += "BALLOT_ITEM_KEY_ERROR: " + str(e) + " "

        success = True
        status += "CONTAINS_API-DISTRICTS_COUNT: " + str(len(modified_district_json_list)) + " "
        results = {
            'success':                          success,
            'status':                           status,
            'google_civic_election_id':         google_civic_election_id,
            'kind_of_batch':                    kind_of_batch,
            'modified_json_list':               modified_district_json_list,
        }
        return results
    else:
        status += "IMPORT_BALLOTPEDIA_STRUCTURED_JSON_NOT_RECOGNIZED"

    results = {
        'success': success,
        'status': status,
        'google_civic_election_id': google_civic_election_id,
        'kind_of_batch': None,
        'modified_json_list': [],
    }
    return results


def process_ballotpedia_voter_districts(google_civic_election_id, state_code, modified_district_json_list,
                                        polling_location_we_vote_id):
    success = True
    status = ""
    ballot_items_found = False
    ballot_item_dict_list = []
    generated_ballot_order = 0

    candidate_campaign_list = CandidateCampaignListManager()
    contest_office_list_manager = ContestOfficeListManager()
    measure_list_manager = ContestMeasureList()
    return_list_of_objects = True
    for one_district in modified_district_json_list:
        if 'ballotpedia_district_id' in one_district \
                and positive_value_exists(one_district['ballotpedia_district_id']):
            if not positive_value_exists(state_code):
                state_code = one_district['state_code']
            # Look for any offices in this election with this ballotpedia_district_id
            results = contest_office_list_manager.retrieve_offices(
                google_civic_election_id, state_code, [], return_list_of_objects, one_district['ballotpedia_district_id'])

            if results['office_list_found']:
                office_list_objects = results['office_list_objects']

                # Remove any offices from this list that don't have candidates
                modified_office_list_objects = []
                for one_office in office_list_objects:
                    results = candidate_campaign_list.retrieve_candidate_count_for_office(one_office.id, "")
                    if positive_value_exists(results['candidate_count']):
                        modified_office_list_objects.append(one_office)

                for one_office in modified_office_list_objects:
                    generated_ballot_order += 1
                    ballot_item_dict = {
                        'contest_office_we_vote_id': one_office.we_vote_id,
                        'contest_office_id': one_office.id,
                        'contest_office_name': one_office.office_name,
                        'election_day_text': one_district['election_day_text'],
                        'local_ballot_order': generated_ballot_order,
                        'polling_location_we_vote_id': polling_location_we_vote_id,
                        'state_code': state_code,
                    }
                    ballot_item_dict_list.append(ballot_item_dict)

            # Look for any measures in this election with this ballotpedia_district_id
            results = measure_list_manager.retrieve_measures(
                google_civic_election_id, one_district['ballotpedia_district_id'], state_code=state_code)
            if results['measure_list_found']:
                measure_list_objects = results['measure_list_objects']
                for one_measure in measure_list_objects:
                    generated_ballot_order += 1
                    ballot_item_dict = {
                        'contest_measure_we_vote_id': one_measure.we_vote_id,
                        'contest_measure_id': one_measure.id,
                        'contest_measure_name': one_measure.measure_title,
                        'election_day_text': one_district['election_day_text'],
                        'local_ballot_order': generated_ballot_order,
                        'polling_location_we_vote_id': polling_location_we_vote_id,
                        'state_code': state_code,
                    }
                    ballot_item_dict_list.append(ballot_item_dict)

    if positive_value_exists(generated_ballot_order):
        ballot_items_found = True

    results = {
        'success': success,
        'status': status,
        'ballot_items_found': ballot_items_found,
        'ballot_item_dict_list': ballot_item_dict_list,
    }
    return results


def voter_ballot_items_retrieve_from_ballotpedia_for_api_v4(
        voter_device_id, text_for_map_search='', google_civic_election_id=''):
    """
    We are telling the server to explicitly reach out to the Ballotpedia API and retrieve the ballot items
    for this voter.
    """
    # Confirm that we have the URL where we retrieve voter ballots
    if not positive_value_exists(BALLOTPEDIA_API_SAMPLE_BALLOT_ELECTIONS_URL):
        results = {
            'status':                       'NO BALLOTPEDIA_API_SAMPLE_BALLOT_ELECTIONS_URL '
                                            'in config/environment_variables.json ',
            'success':                      False,
            'voter_device_id':              voter_device_id,
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
            'ballot_returned_found':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        results = {
            'status':                       "VOTER_BALLOT_ITEMS_FROM_BALLOTPEDIA-VALID_VOTER_ID_MISSING ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
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

    status = ''
    success = False
    election_day_text = ''
    election_description_text = ''
    election_data_retrieved = False
    polling_location_retrieved = False
    ballot_location_display_name = ''
    ballot_location_shortcut = ''
    ballot_returned = None
    ballot_returned_we_vote_id = ''
    ballot_returned_found = False
    latitude = 0.0
    longitude = 0.0
    original_text_city = ''
    original_text_state = ''
    original_text_zip = ''
    lat_long_found = False
    status += "ENTERING-voter_ballot_items_retrieve_from_ballotpedia_for_api_v4, text_for_map_search: " \
              "" + str(text_for_map_search) + " "
    if not positive_value_exists(text_for_map_search):
        # Retrieve it from voter address
        voter_address_manager = VoterAddressManager()
        text_for_map_search = voter_address_manager.retrieve_ballot_map_text_from_voter_id(voter_id)
        results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
        if results['voter_address_found']:
            voter_address = results['voter_address']
            original_text_city = voter_address.normalized_city
            original_text_state = voter_address.normalized_state
            original_text_zip = voter_address.normalized_zip

    election_manager = ElectionManager()
    state_code = extract_state_code_from_address_string(text_for_map_search)
    status += "[STATE_CODE: " + str(state_code) + "] "
    if positive_value_exists(state_code):
        original_text_state = state_code
        status += "[ORIGINAL_TEXT_STATE: " + str(original_text_state) + "] "
    if positive_value_exists(google_civic_election_id):
        election_results = election_manager.retrieve_election(google_civic_election_id)
        if election_results['election_found']:
            election_data_retrieved = True
            election = election_results['election']
            google_civic_election_id = election.google_civic_election_id
            election_day_text = election.election_day_text
            election_description_text = election.election_name

        status += "ELECTION_BY_GOOGLE_CIVIC_ELECTION_ID: " + str(google_civic_election_id) + " "
    else:
        # We need to figure out next upcoming election for this person based on the state_code in text_for_map_search
        if positive_value_exists(state_code):
            election_results = election_manager.retrieve_next_election_for_state(state_code)
            if election_results['election_found']:
                election_data_retrieved = True
                election = election_results['election']
                google_civic_election_id = election.google_civic_election_id
                election_day_text = election.election_day_text
                election_description_text = election.election_name

            status += "NEXT_ELECTION_FOR_STATE: " + str(google_civic_election_id) + " "

    if not positive_value_exists(text_for_map_search) or not positive_value_exists(google_civic_election_id):
        status += 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH_FOR_ELECTION_ID '
        success = False
        results = {
            'success': success,
            'status': status,
            'voter_device_id': voter_device_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code': state_code,
            'election_day_text': election_day_text,
            'election_description_text': election_description_text,
            'election_data_retrieved': election_data_retrieved,
            'text_for_map_search':          text_for_map_search,
            'original_text_city':           original_text_city,
            'original_text_state':          original_text_state,
            'original_text_zip':            original_text_zip,
            'polling_location_retrieved': polling_location_retrieved,
            'ballot_returned_found': ballot_returned_found,
            'ballot_location_display_name': ballot_location_display_name,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned': ballot_returned,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
        }
        return results

    try:
        # Make sure we have a latitude and longitude
        google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        location = google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
        if location is None:
            status += 'RETRIEVE_FROM_BALLOTPEDIA-Could not find location matching "{}"'.format(text_for_map_search)
            success = False
        else:
            latitude = location.latitude
            longitude = location.longitude
            lat_long_found = True
            # Now retrieve the ZIP code
            if not positive_value_exists(original_text_zip) or not positive_value_exists(original_text_state):
                if hasattr(location, 'raw'):
                    if 'address_components' in location.raw:
                        for one_address_component in location.raw['address_components']:
                            if 'postal_code' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                original_text_zip = one_address_component['long_name']
                            if not positive_value_exists(original_text_state):
                                if 'administrative_area_level_1' in one_address_component['types'] \
                                        and positive_value_exists(one_address_component['short_name']):
                                    original_text_state = one_address_component['short_name']

    except Exception as e:
        status += "RETRIEVE_FROM_BALLOTPEDIA-EXCEPTION with get_geocoder_for_service " + str(e) + " "
        success = False
        # FOR TESTING
        # latitude = 37.8467035
        # longitude = -122.2595252
        # lat_long_found = True

    if not lat_long_found:
        results = {
            'success': success,
            'status': status,
            'voter_device_id': voter_device_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code': state_code,
            'election_day_text': election_day_text,
            'election_description_text': election_description_text,
            'election_data_retrieved': election_data_retrieved,
            'text_for_map_search':          text_for_map_search,
            'original_text_city':           original_text_city,
            'original_text_state':          original_text_state,
            'original_text_zip':            original_text_zip,
            'polling_location_retrieved': polling_location_retrieved,
            'ballot_returned_found': ballot_returned_found,
            'ballot_location_display_name': ballot_location_display_name,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned': ballot_returned,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
        }
        return results

    one_ballot_results = retrieve_one_ballot_from_ballotpedia_api_v4(
        latitude, longitude, google_civic_election_id, state_code=state_code,
        text_for_map_search=text_for_map_search, voter_id=voter_id)

    if not one_ballot_results['success']:
        status += 'UNABLE_TO-retrieve_one_ballot_from_ballotpedia_api'
        status += one_ballot_results['status']
        success = False
    else:
        status += "RETRIEVE_ONE_BALLOT_FROM_BALLOTPEDIA_API-SUCCESS "
        success = True
        ballot_returned_found = one_ballot_results['ballot_returned_found']
        if positive_value_exists(ballot_returned_found):
            ballot_returned = one_ballot_results['ballot_returned']
            ballot_returned_we_vote_id = ballot_returned.we_vote_id
            # Now that we know we have new ballot data, we need to delete prior ballot data for this election
            # because when we change voterAddress, we usually get different ballot items
            # We include a google_civic_election_id, so only the ballot info for this election is removed
            google_civic_election_id_to_delete = google_civic_election_id
            if positive_value_exists(google_civic_election_id_to_delete) and positive_value_exists(voter_id):
                # Remove all prior ballot items, so we make room for store_one_ballot_from_ballotpedia_api to save
                #  ballot items
                voter_ballot_saved_manager = VoterBallotSavedManager()
                voter_ballot_saved_id = 0
                voter_ballot_saved_manager.delete_voter_ballot_saved(
                    voter_ballot_saved_id, voter_id, google_civic_election_id_to_delete)
        else:
            status += "BALLOT_RETURNED_MISSING: "
            status += one_ballot_results['status']

    # VoterBallotSaved gets created outside of this function

    results = {
        'success':                      success,
        'status':                       status,
        'voter_device_id':              voter_device_id,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'election_day_text':            election_day_text,
        'election_description_text':    election_description_text,
        'election_data_retrieved':      election_data_retrieved,
        'text_for_map_search':          text_for_map_search,
        'original_text_city':           original_text_city,
        'original_text_state':          original_text_state,
        'original_text_zip':            original_text_zip,
        'polling_location_retrieved':   polling_location_retrieved,
        'ballot_returned_found':        ballot_returned_found,
        'ballot_location_display_name': ballot_location_display_name,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned':              ballot_returned,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
    }
    return results


def retrieve_one_ballot_from_ballotpedia_api(latitude, longitude, incoming_google_civic_election_id, state_code=""):
    success = False
    status = ""
    contests_retrieved = False
    structured_json = []
    ballotpedia_election_id = 0

    if not latitude or not longitude:
        status += "RETRIEVE_BALLOTPEDIA_API-MISSING_LATITUDE_AND_LONGITUDE "
        results = {
            'success': False,
            'status': status,
            'contests_retrieved': False,
            'structured_json': structured_json,
        }
        return results

    if not positive_value_exists(incoming_google_civic_election_id):
        status += "RETRIEVE_BALLOTPEDIA_API-MISSING_GOOGLE_CIVIC_ELECTION_ID "
        results = {
            'success': False,
            'status': status,
            'contests_retrieved': False,
            'structured_json': structured_json,
        }
        return results

    try:
        latitude_longitude = str(latitude) + "," + str(longitude)
        status += "LAT_LONG: " + str(latitude_longitude) + " "
        response = requests.get(BALLOTPEDIA_API_CONTAINS_URL, params={
            "access_token": BALLOTPEDIA_API_KEY,
            "point": latitude_longitude,
        })
        structured_json = json.loads(response.text)

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_CONTAINS_TYPE,
                                                             google_civic_election_id=0,
                                                             ballotpedia_election_id=0)

        success = len(structured_json)

        if not positive_value_exists(success):
            status += "RETRIEVE_BALLOTPEDIA_API-NO_DISTRICTS_FOUND "
            results = {
                'success': False,
                'status': status,
                'contests_retrieved': False,
                'structured_json': structured_json,
            }
            return results
    except Exception as e:
        status += "EXCEPTION with get_geocoder_for_service "

    contains_api = True
    polling_location_we_vote_id = ""
    groom_results = groom_ballotpedia_data_for_processing(structured_json, incoming_google_civic_election_id,
                                                          state_code, contains_api)

    structured_json = []
    if groom_results['success']:
        status += "GROOM_BALLOTPEDIA_DATA_FOR_PROCESSING-SUCCESSFUL "
        success = True
        modified_json_list = groom_results['modified_json_list']
        contests_retrieved = len(modified_json_list)

        ballot_items_results = process_ballotpedia_voter_districts(incoming_google_civic_election_id, state_code,
                                                                   modified_json_list, polling_location_we_vote_id)
        status += ballot_items_results['status']
        structured_json = ballot_items_results['ballot_item_dict_list']
    else:
        success = False
        status += groom_results['status']
        status += "GROOM_BALLOTPEDIA_DATA_FOR_PROCESSING-NOT_SUCCESSFUL "

    results = {
        'success': success,
        'status': status,
        'contests_retrieved': contests_retrieved,
        'structured_json': structured_json,
    }
    return results


def retrieve_one_ballot_from_ballotpedia_api_v4(latitude, longitude, google_civic_election_id, state_code="",
                                                text_for_map_search="", voter_id=0):
    success = True
    status = ""
    ballot_returned = None
    ballot_returned_found = False

    if not latitude or not longitude:
        status += "RETRIEVE_BALLOTPEDIA_API_v4-MISSING_LATITUDE_AND_LONGITUDE "
        results = {
            'success': False,
            'status': status,
            'ballot_returned': ballot_returned,
            'ballot_returned_found': ballot_returned_found,
        }
        return results

    if not positive_value_exists(google_civic_election_id):
        status += "RETRIEVE_BALLOTPEDIA_API_v4-MISSING_GOOGLE_CIVIC_ELECTION_ID "
        results = {
            'success': False,
            'status': status,
            'ballot_returned': ballot_returned,
            'ballot_returned_found': ballot_returned_found,
        }
        return results

    election_day_text = ""

    try:
        election_on_stage = Election.objects.using('readonly').get(google_civic_election_id=google_civic_election_id)
        election_day_text = election_on_stage.election_day_text
        election_name = election_on_stage.election_name
    except Election.MultipleObjectsReturned as e:
        status += "MULTIPLE_ELECTIONS_FOUND "
    except Election.DoesNotExist:
        status += "ELECTION_NOT_FOUND "

    try:
        # Get the electoral_districts at this lat/long
        response = requests.get(
            BALLOTPEDIA_API_SAMPLE_BALLOT_ELECTIONS_URL,
            headers=MAIL_HEADERS,
            params={
                "lat": longitude,
                "long": latitude,
                # NOTE: Ballotpedia appears to have swapped latitude and longitude
                # "lat": polling_location.latitude,
                # "long": polling_location.longitude,
            })
        structured_json = json.loads(response.text)

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_ELECTIONS_TYPE,
                                                             google_civic_election_id=google_civic_election_id,
                                                             ballotpedia_election_id=0)

        groom_results = groom_and_store_sample_ballot_elections_api_v4(structured_json, google_civic_election_id)
        ballotpedia_district_id_list = groom_results['ballotpedia_district_id_list']
        if not ballotpedia_district_id_list or len(ballotpedia_district_id_list) == 0:
            status += "NO_BALLOTPEDIA_DISTRICTS_RETURNED "
            success = False
            results = {
                'success': success,
                'status': status,
                'ballot_returned': ballot_returned,
                'ballot_returned_found': ballot_returned_found,
            }
            return results

        office_district_string = ""
        office_district_count = 0
        ballotpedia_district_id_not_used_list = []
        for one_district in ballotpedia_district_id_list:
            # The url we send to Ballotpedia can only be so long. If too long, we stop adding districts to the
            #  office_district_string, but capture the districts not used
            # 3796 = 4096 - 300 (300 gives us room for all of the other url variables we need)
            if len(office_district_string) < 3796:
                office_district_string += str(one_district) + ","
                office_district_count += 1
            else:
                # In the future we might want to set up a second query to get the races for these districts
                ballotpedia_district_id_not_used_list.append(one_district)

        # Remove last comma
        if office_district_count > 1:
            office_district_string = office_district_string[:-1]
        # chunks_of_district_strings.append(office_district_string)

        # Get the electoral_districts at this lat/long
        response = requests.get(BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL, headers=MAIL_HEADERS, params={
            "districts": office_district_string,
            "election_date": election_day_text,
        })
        structured_json = json.loads(response.text)

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_TYPE,
                                                             google_civic_election_id=google_civic_election_id,
                                                             ballotpedia_election_id=0)

        groom_results = groom_and_store_sample_ballot_results_api_v4(
            structured_json, google_civic_election_id=google_civic_election_id,
            state_code=state_code, voter_id=voter_id,
            election_day_text=election_day_text,
        )
        status += groom_results['status']
        ballot_item_dict_list = groom_results['ballot_item_dict_list']

        # If we successfully save a ballot, create/update a BallotReturned entry
        if ballot_item_dict_list and len(ballot_item_dict_list) > 0:
            ballot_returned_manager = BallotReturnedManager()
            results = ballot_returned_manager.update_or_create_ballot_returned(
                election_day_text=election_day_text,
                election_description_text=election_name,
                voter_id=voter_id,
                google_civic_election_id=google_civic_election_id,
                latitude=latitude,
                longitude=longitude,
                text_for_map_search=text_for_map_search,
            )
            status += results['status']
            if results['ballot_returned_found']:
                status += "UPDATE_OR_CREATE_BALLOT_RETURNED-SUCCESS "
                ballot_returned = results['ballot_returned']
                ballot_returned_found = True
            else:
                status += "UPDATE_OR_CREATE_BALLOT_RETURNED-BALLOT_RETURNED_FOUND-FALSE "

            ballot_item_manager = BallotItemManager()
            ballot_item_list_manager = BallotItemListManager()

            # Delete prior ballot items before we store the new ones for this election
            results = ballot_item_list_manager.delete_all_ballot_items_for_voter(voter_id, google_civic_election_id)
            if not results['success']:
                status += results['status']

            for one_ballot_item in ballot_item_dict_list:
                ballot_item_display_name = one_ballot_item['ballot_item_display_name'] \
                    if 'ballot_item_display_name' in one_ballot_item else ''
                contest_measure_we_vote_id = one_ballot_item['contest_measure_we_vote_id'] \
                    if 'contest_measure_we_vote_id' in one_ballot_item else ''
                contest_measure_id = one_ballot_item['contest_measure_id'] \
                    if 'contest_measure_id' in one_ballot_item else ''
                contest_office_id = one_ballot_item['contest_office_id'] \
                    if 'contest_office_id' in one_ballot_item else ''
                contest_office_we_vote_id = one_ballot_item['contest_office_we_vote_id'] \
                    if 'contest_office_we_vote_id' in one_ballot_item else ''
                local_ballot_order = one_ballot_item['local_ballot_order'] \
                    if 'local_ballot_order' in one_ballot_item else ''
                measure_subtitle = one_ballot_item['measure_subtitle'] \
                    if 'measure_subtitle' in one_ballot_item else ''
                measure_text = one_ballot_item['measure_text'] \
                    if 'measure_text' in one_ballot_item else ''
                state_code = one_ballot_item['state_code'] \
                    if 'state_code' in one_ballot_item else ''
                voter_id = one_ballot_item['voter_id'] \
                    if 'voter_id' in one_ballot_item else ''
                # For defaults
                measure_url = one_ballot_item['measure_url'] \
                    if 'measure_url' in one_ballot_item else ''
                no_vote_description = one_ballot_item['no_vote_description'] \
                    if 'no_vote_description' in one_ballot_item else ''
                yes_vote_description = one_ballot_item['yes_vote_description'] \
                    if 'yes_vote_description' in one_ballot_item else ''

                results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    ballot_item_display_name=ballot_item_display_name,
                    measure_subtitle=measure_subtitle,
                    measure_text=measure_text,
                    local_ballot_order=local_ballot_order,
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    state_code=state_code,
                    defaults={
                        'measure_url': measure_url,
                        'no_vote_description': no_vote_description,
                        'yes_vote_description': yes_vote_description,
                    })
            status += results['status']
    except Exception as e:
        success = False
        status += 'ERROR FAILED retrieve_ballot_items_from_polling_location ' \
                  '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'ballot_returned':  ballot_returned,
        'ballot_returned_found':  ballot_returned_found,
    }
    return results


def store_one_ballot_from_ballotpedia_api(ballot_item_dict_list, google_civic_election_id,
                                          text_for_map_search, latitude, longitude,
                                          ballot_location_display_name, voter_id=0, polling_location_we_vote_id='',
                                          normalized_city='', normalized_state='',
                                          normalized_zip=''):
    """
    When we pass in a voter_id, we want to save this ballot related to the voter.
    When we pass in polling_location_we_vote_id, we want to save a ballot for that area, which is useful for
    getting new voters started by showing them a ballot roughly near them.
    """

    election_day_text = ''
    election_description_text = ''
    ocd_division_id = ''
    status = ""
    success = True

    if not positive_value_exists(google_civic_election_id):
        results = {
            'status': 'BALLOT_ITEM_DICT_LIST_MISSING_ELECTION_ID ',
            'success': False,
            'google_civic_election_id': 0,
        }
        return results

    # Check to see if there is a state served for the election
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        if not positive_value_exists(normalized_state):
            normalized_state = election.state_code
        election_day_text = election.election_day_text

    # If we successfully save a ballot, create/update a BallotReturned entry
    ballot_returned_found = False
    ballot_returned = BallotReturned()

    # Make sure we have latitude and longitude
    if positive_value_exists(polling_location_we_vote_id) and not positive_value_exists(latitude) \
            and not positive_value_exists(longitude):
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        status += "RETRIEVING_LAT_LONG_FROM_POLLING_LOCATION "
        if results['polling_location_found']:
            polling_location = results['polling_location']
            latitude = polling_location.latitude
            longitude = polling_location.longitude
        else:
            pass

    # Similar to import_export_batches.controllers, import_ballot_item_data_from_batch_row_actions
    office_manager = ContestOfficeManager()
    measure_manager = ContestMeasureManager()
    google_ballot_placement = None
    number_of_ballot_items_updated = 0
    measure_subtitle = ""
    measure_text = ""
    for one_ballot_item_dict in ballot_item_dict_list:
        # status += "BALLOT_ITEM-START "

        contest_office_we_vote_id = one_ballot_item_dict['contest_office_we_vote_id'] \
            if 'contest_office_we_vote_id' in one_ballot_item_dict else ""
        contest_office_id = one_ballot_item_dict['contest_office_id'] \
            if 'contest_office_id' in one_ballot_item_dict else 0
        contest_measure_we_vote_id = one_ballot_item_dict['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_ballot_item_dict else ""
        contest_measure_id = one_ballot_item_dict['contest_measure_id'] \
            if 'contest_measure_id' in one_ballot_item_dict else 0

        if 'contest_office_name' in one_ballot_item_dict:
            ballot_item_display_name = one_ballot_item_dict['contest_office_name']
        elif 'contest_measure_name' in one_ballot_item_dict:
            ballot_item_display_name = one_ballot_item_dict['contest_measure_name']
        else:
            ballot_item_display_name = ""

        local_ballot_order = one_ballot_item_dict['local_ballot_order'] \
            if 'local_ballot_order' in one_ballot_item_dict else ""

        # Make sure we have both ids for office
        if positive_value_exists(contest_office_we_vote_id) \
                and not positive_value_exists(contest_office_id):
            contest_office_id = office_manager.fetch_contest_office_id_from_we_vote_id(contest_office_we_vote_id)
        elif positive_value_exists(contest_office_id) \
                and not positive_value_exists(contest_office_we_vote_id):
            contest_office_we_vote_id = office_manager.fetch_contest_office_we_vote_id_from_id(contest_office_id)
        # Make sure we have both ids for measure
        if positive_value_exists(contest_measure_we_vote_id) \
                and not positive_value_exists(contest_measure_id):
            contest_measure_id = measure_manager.fetch_contest_measure_id_from_we_vote_id(contest_measure_we_vote_id)
        elif positive_value_exists(contest_measure_id) \
                and not positive_value_exists(contest_measure_we_vote_id):
            contest_measure_we_vote_id = measure_manager.fetch_contest_measure_we_vote_id_from_id(contest_measure_id)

        # Update or create
        if positive_value_exists(ballot_item_display_name) and positive_value_exists(normalized_state) \
                and positive_value_exists(google_civic_election_id):
            ballot_item_manager = BallotItemManager()

            defaults = {}
            defaults['measure_url'] = one_ballot_item_dict['ballotpedia_measure_url'] \
                if 'ballotpedia_measure_url' in one_ballot_item_dict else ''
            defaults['yes_vote_description'] = one_ballot_item_dict['yes_vote_description'] \
                if 'yes_vote_description' in one_ballot_item_dict else ''
            defaults['no_vote_description'] = one_ballot_item_dict['no_vote_description'] \
                if 'no_vote_description' in one_ballot_item_dict else ''

            if positive_value_exists(voter_id):
                results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                        voter_id, google_civic_election_id, google_ballot_placement,
                        ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
                        contest_office_id, contest_office_we_vote_id,
                        contest_measure_id, contest_measure_we_vote_id, normalized_state, defaults)
                if results['ballot_item_found']:
                    number_of_ballot_items_updated += 1
                else:
                    status += results['status'] + " "
                    status += "UPDATE_OR_CREATE_BALLOT_ITEM_UNSUCCESSFUL "
            elif positive_value_exists(polling_location_we_vote_id):
                results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                    polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
                    ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
                    contest_office_id, contest_office_we_vote_id,
                    contest_measure_id, contest_measure_we_vote_id, normalized_state, defaults)
                if results['ballot_item_found']:
                    number_of_ballot_items_updated += 1
        else:
            status += "MISSING-BALLOT_ITEM_DISPLAY_NAME-OR-NORMALIZED_STATE-OR-ELECTION_ID "
            status += "DISPLAY_NAME:" + str(ballot_item_display_name) + " "
            status += "STATE:" + str(normalized_state) + " "

    # TODO: Figure out best way to save ballot_returned
    if positive_value_exists(number_of_ballot_items_updated):
        ballot_returned_manager = BallotReturnedManager()
        results = ballot_returned_manager.update_or_create_ballot_returned(
            polling_location_we_vote_id, voter_id, google_civic_election_id,
            latitude=latitude, longitude=longitude,
            ballot_location_display_name=ballot_location_display_name, text_for_map_search=text_for_map_search,
            normalized_city=normalized_city, normalized_state=normalized_state, normalized_zip=normalized_zip,
        )
        status += results['status']
        if results['ballot_returned_found']:
            status += "UPDATE_OR_CREATE_BALLOT_RETURNED-SUCCESS "
            ballot_returned = results['ballot_returned']
            ballot_returned_found = True
        else:
            status += "UPDATE_OR_CREATE_BALLOT_RETURNED-BALLOT_RETURNED_FOUND-FALSE "
    else:
        status += "NUMBER_OF_BALLOT_ITEMS_UPDATED-NEGATIVE "

    results = {
        'status':                   status,
        'success':                  success,
        'ballot_returned_found':    ballot_returned_found,
        'ballot_returned':          ballot_returned,
        'google_civic_election_id': google_civic_election_id,
    }
    return results
