# import_export_ballotpedia/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-
from .models import BallotpediaApiCounterManager
from ballot.models import BallotItemListManager, BallotItemManager, BallotReturned, BallotReturnedManager, \
    VoterBallotSavedManager
from candidate.models import fetch_candidate_count_for_office
from config.base import get_environment_variable
from election.models import ElectionManager
from geopy.geocoders import get_geocoder_for_service
from import_export_batches.controllers_ballotpedia import store_ballotpedia_json_response_to_import_batch_system
import json
from measure.models import ContestMeasureList, ContestMeasureManager
from office.models import ContestOfficeListManager, ContestOfficeManager
from polling_location.models import PollingLocationManager
import requests
from voter.models import fetch_voter_id_from_voter_device_link, VoterAddressManager
from wevote_functions.functions import extract_state_code_from_address_string, positive_value_exists

BALLOTPEDIA_API_KEY = get_environment_variable("BALLOTPEDIA_API_KEY")
BALLOTPEDIA_API_CANDIDATES_URL = get_environment_variable("BALLOTPEDIA_API_CANDIDATES_URL")
BALLOTPEDIA_API_CONTAINS_URL = get_environment_variable("BALLOTPEDIA_API_CONTAINS_URL")
BALLOTPEDIA_API_ELECTIONS_URL = get_environment_variable("BALLOTPEDIA_API_ELECTIONS_URL")
BALLOTPEDIA_API_FILES_URL = get_environment_variable("BALLOTPEDIA_API_FILES_URL")
BALLOTPEDIA_API_MEASURES_URL = get_environment_variable("BALLOTPEDIA_API_MEASURES_URL")
BALLOTPEDIA_API_RACES_URL = get_environment_variable("BALLOTPEDIA_API_RACES_URL")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
BALLOTPEDIA_API_CANDIDATES_TYPE = "candidates"
BALLOTPEDIA_API_CONTAINS_TYPE = "contains"
BALLOTPEDIA_API_ELECTIONS_TYPE = "elections"
BALLOTPEDIA_API_FILES_TYPE = "files"
BALLOTPEDIA_API_MEASURES_TYPE = "measures"
BALLOTPEDIA_API_RACES_TYPE = "races"


def extract_value_from_array(structured_json, index_key, default_value):
    if index_key in structured_json:
        return structured_json[index_key]
    else:
        return default_value


def attach_ballotpedia_election_by_district_from_api(google_civic_election_id, district_list):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success':          False,
            'status':           "Error: Missing election id for attaching",
            'election_found':   False,
        }
        return results

    if not len(district_list):
        results = {
            'success':          False,
            'status':           "Error: Missing any districts",
            'election_found':   False,
        }
        return results

    batch_header_id = 0
    election_day_text = ""
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        election_day_text = election.election_day_text

    district_string = ""
    for one_district in district_list:
        district_string += str(one_district) + ","

    # Remove last comma
    district_string = district_string[:-1]

    # & filters[district][ in]=299, 546, 1669, 5412, 12616, 61773, 61774, 61781, 22046, 79925
    # & filters[date][between] = 2018 - 06 - 13, 2019 - 06 - 13
    # & order[date] = ASC
    response = requests.get(BALLOTPEDIA_API_ELECTIONS_URL, params={
        "access_token":             BALLOTPEDIA_API_KEY,
        "filters[district][in]":    district_string,
        "filters[date][eq]":        election_day_text,
        "limit":                    1000,
    })

    if not positive_value_exists(response.text):
        success = False
        status += "NO_RESPONSE_TEXT_FOUND"
        if positive_value_exists(response.url):
            status += ": " + response.url
        results = {
            'success':          success,
            'status':           status,
            'election_found':   False,
        }
        return results

    structured_json = json.loads(response.text)

    # Use Ballotpedia API call counter to track the number of queries we are doing each day
    ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
    ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_ELECTIONS_TYPE,
                                                         google_civic_election_id=google_civic_election_id)

    election_count = 0
    ballotpedia_election_id = 0
    ballotpedia_kind_of_election = ""
    if 'data' in structured_json:
        if 'meta' in structured_json:
            if 'table' in structured_json['meta']:
                if structured_json['meta']['table'] == 'election_dates':
                    elections_json_list = structured_json['data']
                    election_count = len(elections_json_list)

                    for one_election_json in elections_json_list:
                        try:
                            ballotpedia_election_id = one_election_json['id']

                            if one_election_json['type'] == "Primary":
                                ballotpedia_kind_of_election = "primary_election"
                            elif one_election_json['type'] == "General":
                                ballotpedia_kind_of_election = "general_election"
                            elif one_election_json['type'] == "Primary Runoff":
                                ballotpedia_kind_of_election = "primary_runoff_election"
                            elif one_election_json['type'] == "General Runoff":
                                ballotpedia_kind_of_election = "general_runoff_election"
                            else:
                                ballotpedia_kind_of_election = "unknown"
                        except KeyError as e:
                            status += "ELECTIONS_KEY_ERROR: " + str(e) + " "

    election_found = False
    if election_count == 1:
        # Only one election found
        if positive_value_exists(ballotpedia_election_id) and positive_value_exists(ballotpedia_kind_of_election):
            try:
                election.ballotpedia_election_id = ballotpedia_election_id
                election.ballotpedia_kind_of_election = ballotpedia_kind_of_election
                election.save()
                status += "BALLOTPEDIA_ELECTION_ATTACHED "
                election_found = True
            except Exception as e:
                status += "COULD_NOT_SAVE_ELECTION " + str(e) + " "
        else:
            status += "ONE_ELECTION-BALLOTPEDIA_ELECTION_INFO_NOT_FOUND "
    elif election_count == 0:
        status += "ZERO_ELECTIONS-BALLOTPEDIA_ELECTION_INFO_NOT_FOUND "
    else:
        status += "BALLOTPEDIA_MULTIPLE_ELECTIONS_FOUND "

    results = {
        'success':          success,
        'status':           status,
        'election_found':   election_found,
    }
    return results


def retrieve_ballotpedia_candidates_by_election_from_api(google_civic_election_id,
                                                         only_retrieve_if_zero_candidates=False):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    ballotpedia_kind_of_election = ""
    ballotpedia_election_id = 0
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        ballotpedia_kind_of_election = election.ballotpedia_kind_of_election
        if election.ballotpedia_election_id:
            ballotpedia_election_id = election.ballotpedia_election_id

    if not positive_value_exists(ballotpedia_election_id):
        results = {
            'success': False,
            'status': "Error: Missing Ballotpedia election id",
        }
        return results

    maximum_offices_to_retrieve = 100
    state_code = ""
    batch_header_id = 0
    office_list = []
    return_list_of_objects = True
    contest_list_manager = ContestOfficeListManager()
    results = contest_list_manager.retrieve_offices(
        google_civic_election_id, state_code, office_list, return_list_of_objects)

    filtered_office_list = []
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

                if office_count >= maximum_offices_to_retrieve:
                    # Limit to showing only maximum_offices_to_retrieve
                    break

    if positive_value_exists(office_count):
        races_to_retrieve_string = ""
        for one_office in filtered_office_list:
            if positive_value_exists(one_office.ballotpedia_race_id):
                races_to_retrieve_string += str(one_office.ballotpedia_race_id) + ","

        # Remove last comma
        last_character = races_to_retrieve_string[-1:]
        if last_character == ",":
            races_to_retrieve_string = races_to_retrieve_string[:-1]

        response = requests.get(BALLOTPEDIA_API_CANDIDATES_URL, params={
            "access_token": BALLOTPEDIA_API_KEY,
            "filters[race][in]": races_to_retrieve_string,
            "limit": 1000,
        })

        structured_json = json.loads(response.text)

        # Use Ballotpedia API call counter to track the number of queries we are doing each day
        ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
        ballotpedia_api_counter_manager.create_counter_entry(
            BALLOTPEDIA_API_CANDIDATES_TYPE,
            google_civic_election_id=google_civic_election_id,
            ballotpedia_election_id=0)

        contains_api = False
        groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id,
                                                              contains_api, ballotpedia_kind_of_election)
        modified_json_list = groom_results['modified_json_list']
        kind_of_batch = groom_results['kind_of_batch']

        results = store_ballotpedia_json_response_to_import_batch_system(
            modified_json_list, google_civic_election_id, kind_of_batch)
        status += results['status']
        if 'batch_header_id' in results:
            batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_ballot_items_from_polling_location(
        google_civic_election_id, polling_location_we_vote_id="", polling_location=None, batch_set_id=0):
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
        groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id,
                                                              contains_api)

        modified_json_list = groom_results['modified_json_list']
        kind_of_batch = groom_results['kind_of_batch']

        ballot_items_results = process_ballotpedia_voter_districts(
            google_civic_election_id, modified_json_list, polling_location_we_vote_id)

        if ballot_items_results['ballot_items_found']:
            ballot_item_dict_list = ballot_items_results['ballot_item_dict_list']

            results = store_ballotpedia_json_response_to_import_batch_system(
                ballot_item_dict_list, google_civic_election_id, kind_of_batch, batch_set_id)
            status += results['status']
            if 'batch_header_id' in results:
                batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_district_list_from_polling_location(
        google_civic_election_id, polling_location_we_vote_id="", polling_location=None):
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
    district_list = []

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
        groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id,
                                                              contains_api)
        district_list = groom_results['district_list']

    results = {
        'success': success,
        'status': status,
        'district_list': district_list,
    }
    return results


def retrieve_ballotpedia_offices_by_election_from_api(google_civic_election_id):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    batch_header_id = 0
    ballotpedia_election_id = 0
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        if election.ballotpedia_election_id:
            ballotpedia_election_id = election.ballotpedia_election_id

    if not positive_value_exists(ballotpedia_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    response = requests.get(BALLOTPEDIA_API_RACES_URL, params={
        "access_token": BALLOTPEDIA_API_KEY,
        "filters[election][in]": str(ballotpedia_election_id),
        "limit": 1000,
    })

    if not positive_value_exists(response.text):
        status += "NO_RESPONSE_TEXT_FOUND"
        if positive_value_exists(response.url):
            status += ": " + response.url
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
        }
        return results

    structured_json = json.loads(response.text)

    # Use Ballotpedia API call counter to track the number of queries we are doing each day
    ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
    ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_RACES_TYPE,
                                                         ballotpedia_election_id=ballotpedia_election_id)

    groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id)
    modified_json_list = groom_results['modified_json_list']
    kind_of_batch = groom_results['kind_of_batch']

    results = store_ballotpedia_json_response_to_import_batch_system(
        modified_json_list, google_civic_election_id, kind_of_batch)
    status += results['status']
    if 'batch_header_id' in results:
        batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_ballotpedia_offices_by_district_from_api(google_civic_election_id, district_list):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    if not len(district_list):
        results = {
            'success': False,
            'status': "Error: Missing any districts",
        }
        return results

    batch_header_id = 0
    ballotpedia_election_id = 0
    ballotpedia_kind_of_election = ""
    election_day_text = ""
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        election_day_text = election.election_day_text
        ballotpedia_kind_of_election = election.ballotpedia_kind_of_election
        if election.ballotpedia_election_id:
            ballotpedia_election_id = election.ballotpedia_election_id

    if not positive_value_exists(ballotpedia_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    office_district_string = ""
    for one_district in district_list:
        office_district_string += str(one_district) + ","

    # Remove last comma
    office_district_string = office_district_string[:-1]

    election_day_key = ""
    if ballotpedia_kind_of_election == "primary_election" or ballotpedia_kind_of_election == "primary_election_date":
        election_day_key = "primary_election_date"
        ballotpedia_kind_of_election = "primary_election"
    elif ballotpedia_kind_of_election == "general_election" or ballotpedia_kind_of_election == "general_election_date":
        election_day_key = "general_election_date"
        ballotpedia_kind_of_election = "general_election"

    response = requests.get(BALLOTPEDIA_API_RACES_URL, params={
        "access_token":                                 BALLOTPEDIA_API_KEY,
        "filters[year][eq]":                            "2018",  # TODO Make general
        "filters[office_district][in]":                 office_district_string,
        "filters[" + str(election_day_key) + "][eq]":   election_day_text,
        "limit":                                        1000,
    })

    if not positive_value_exists(response.text):
        status += "NO_RESPONSE_TEXT_FOUND"
        if positive_value_exists(response.url):
            status += ": " + response.url
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
        }
        return results

    structured_json = json.loads(response.text)

    # Use Ballotpedia API call counter to track the number of queries we are doing each day
    ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
    ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_RACES_TYPE,
                                                         ballotpedia_election_id=ballotpedia_election_id)

    groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id,
                                                          kind_of_election=ballotpedia_kind_of_election)
    modified_json_list = groom_results['modified_json_list']
    kind_of_batch = groom_results['kind_of_batch']

    results = store_ballotpedia_json_response_to_import_batch_system(
        modified_json_list, google_civic_election_id, kind_of_batch)
    status += results['status']
    if 'batch_header_id' in results:
        batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_ballotpedia_measures_by_district_from_api(google_civic_election_id, district_list):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id for measures",
        }
        return results

    if not len(district_list):
        results = {
            'success': False,
            'status': "Error: Missing any districts for measures",
        }
        return results

    batch_header_id = 0
    ballotpedia_election_id = 0
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        if election.ballotpedia_election_id:
            ballotpedia_election_id = election.ballotpedia_election_id

    if not positive_value_exists(ballotpedia_election_id):
        results = {
            'success': False,
            'status': "Error: Missing Ballotpedia election id for measures",
        }
        return results

    measure_district_string = ""
    for one_district in district_list:
        measure_district_string += str(one_district) + ","

    # Remove last comma
    measure_district_string = measure_district_string[:-1]

    response = requests.get(BALLOTPEDIA_API_MEASURES_URL, params={
        "access_token":             BALLOTPEDIA_API_KEY,
        "filters[election][in]":    ballotpedia_election_id,
        "filters[district][in]":    measure_district_string,
        "limit":                    1000,
    })

    if not positive_value_exists(response.text):
        status += "NO_RESPONSE_TEXT_FOUND"
        if positive_value_exists(response.url):
            status += ": " + response.url
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
        }
        return results

    structured_json = json.loads(response.text)

    # Use Ballotpedia API call counter to track the number of queries we are doing each day
    ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
    ballotpedia_api_counter_manager.create_counter_entry(BALLOTPEDIA_API_MEASURES_TYPE,
                                                         ballotpedia_election_id=ballotpedia_election_id)

    groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id)
    modified_json_list = groom_results['modified_json_list']
    kind_of_batch = groom_results['kind_of_batch']

    if positive_value_exists(len(modified_json_list)):
        results = store_ballotpedia_json_response_to_import_batch_system(
            modified_json_list, google_civic_election_id, kind_of_batch)
        status += results['status']
        if 'batch_header_id' in results:
            batch_header_id = results['batch_header_id']
    else:
        status += "NO_VALUES_RETURNED "

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
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


def groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id,
                                          contains_api=False, kind_of_election=""):
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
                            if kind_of_election == "primary_election":
                                inner_election_json = one_office_json['primary_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['election_day'] = inner_election_json['date']
                            elif kind_of_election == "primary_runoff_election":
                                inner_election_json = one_office_json['primary_runoff_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['election_day'] = inner_election_json['date']
                            elif kind_of_election == "general_election":
                                inner_election_json = one_office_json['general_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['election_day'] = inner_election_json['date']
                            elif kind_of_election == "general_runoff_election":
                                inner_election_json = one_office_json['general_runoff_election']['data']
                                one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                                one_office_json['election_day'] = inner_election_json['date']
                            else:
                                one_office_json['ballotpedia_election_id'] = 0
                                one_office_json['election_day'] = ""
                            inner_office_json = one_office_json['office']['data']
                            # Add our own key/value pairs
                            # root level
                            one_office_json['ballotpedia_race_id'] = one_office_json['id']
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
                        if kind_of_election == "primary_election":
                            one_candidate_json['candidate_participation_status'] = one_candidate_json['primary_status']
                            # if not positive_value_exists(one_candidate_json['primary_status']):
                            #     # I notice that some candidates are returned with the primary_status empty, but the
                            #     #  general_status as "On the Ballot"
                            #     one_candidate_json['candidate_participation_status'] = \
                            #         one_candidate_json['general_status']
                        elif kind_of_election == "primary_runoff_election":
                            one_candidate_json['candidate_participation_status'] = \
                                one_candidate_json['primary_runoff_status']
                        elif kind_of_election == "general_election":
                            one_candidate_json['candidate_participation_status'] = one_candidate_json['general_status']
                        elif kind_of_election == "general_runoff_election":
                            one_candidate_json['candidate_participation_status'] = \
                                one_candidate_json['general_runoff_status']
                        else:
                            one_candidate_json['candidate_participation_status'] = "unknown"

                        if one_candidate_json['candidate_participation_status'] \
                                not in ("Candidacy Declared", "On the Ballot"):
                            # If the candidate is not on the ballot yet or declared, we don't want to include them
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
        kind_of_batch = 'IMPORT_BALLOT_ITEM'
        modified_district_json_list = []
        district_list = []
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
                one_district_json['election_day_text'] = ""
                if positive_value_exists(one_district_json['id']):
                    district_list.append(one_district_json['id'])
                modified_district_json_list.append(one_district_json)
            except KeyError as e:
                status += "BALLOT_ITEM_KEY_ERROR: " + str(e) + " "

        # ballot_items_results = process_ballotpedia_voter_districts(
        #     google_civic_election_id, modified_district_json_list, polling_location_we_vote_id)
        #
        # if ballot_items_results['ballot_items_found']:
        #     ballot_item_dict_list = ballot_items_results['ballot_item_dict_list']

        success = True
        status += ""
        district_list_found = positive_value_exists(len(district_list))
        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'kind_of_batch':            kind_of_batch,
            'modified_json_list':       modified_district_json_list,
            'district_list':            district_list,
            'district_list_found':      district_list_found,
        }
        return results
        # else:
        #     status += "NO_BALLOT_ITEMS_FOUND_IN_WE_VOTE "
    else:
        status += "IMPORT_BALLOTPEDIA_STRUCTURED_JSON_NOT_RECOGNIZED"

    results = {
        'success': success,
        'status': status,
        'google_civic_election_id': google_civic_election_id,
        'kind_of_batch': None,
        'modified_json_list': [],
        'district_list': [],
        'district_list_found': False,
    }
    return results


def process_ballotpedia_voter_districts(
        google_civic_election_id, modified_district_json_list, polling_location_we_vote_id):
    success = True
    status = ""
    ballot_items_found = False
    ballot_item_dict_list = []
    generated_ballot_order = 0

    contest_office_list_manager = ContestOfficeListManager()
    measure_list_manager = ContestMeasureList()
    return_list_of_objects = True
    for one_district in modified_district_json_list:
        if 'ballotpedia_district_id' in one_district \
                and positive_value_exists(one_district['ballotpedia_district_id']):
            # Look for any offices in this election with this ballotpedia_district_id
            results = contest_office_list_manager.retrieve_offices(
                google_civic_election_id, "", [], return_list_of_objects, one_district['ballotpedia_district_id'])

            if results['office_list_found']:
                office_list_objects = results['office_list_objects']
                for one_office in office_list_objects:
                    generated_ballot_order += 1
                    ballot_item_dict = {
                        'contest_office_we_vote_id': one_office.we_vote_id,
                        'contest_office_id': one_office.id,
                        'contest_office_name': one_office.office_name,
                        'election_day_text': one_district['election_day_text'],
                        'local_ballot_order': generated_ballot_order,
                        'polling_location_we_vote_id': polling_location_we_vote_id,
                        'state_code': one_district['state_code'],
                    }
                    ballot_item_dict_list.append(ballot_item_dict)

            # Look for any measures in this election with this ballotpedia_district_id
            results = measure_list_manager.retrieve_measures(
                google_civic_election_id, one_district['ballotpedia_district_id'])
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
                        'state_code': one_district['state_code'],
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


def voter_ballot_items_retrieve_from_ballotpedia_for_api(voter_device_id, text_for_map_search=''):
    """
    We are telling the server to explicitly reach out to the Ballotpedia API and retrieve the ballot items
    for this voter.
    """
    # Confirm that we have a Google Civic API Key (BALLOTPEDIA_API_KEY)
    if not positive_value_exists(BALLOTPEDIA_API_KEY):
        results = {
            'status':                       'NO_BALLOTPEDIA_API_KEY ',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned_we_vote_id':   "",
        }
        return results

    # Confirm that we have the URL where we retrieve voter ballots (VOTER_INFO_URL)
    if not positive_value_exists(BALLOTPEDIA_API_CONTAINS_URL):
        results = {
            'status':                       'NO BALLOTPEDIA_API_CONTAINS_URL in config/environment_variables.json ',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned_we_vote_id':   "",
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        results = {
            'status':                       "VOTER_BALLOT_ITEMS_FROM_BALLOTPEDIA-VALID_VOTER_ID_MISSING ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
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
    ballot_returned_we_vote_id = ''
    contests_retrieved = False
    google_civic_election_id = 0
    latitude = 0.0
    longitude = 0.0
    lat_long_found = False
    if not positive_value_exists(text_for_map_search):
        # Retrieve it from voter address
        voter_address_manager = VoterAddressManager()
        text_for_map_search = voter_address_manager.retrieve_ballot_map_text_from_voter_id(voter_id)

    # We need to figure out the next upcoming election for this person based on the state_code in text_for_map_search
    state_code = extract_state_code_from_address_string(text_for_map_search)
    if positive_value_exists(state_code):
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_next_election_for_state(state_code)
        if election_results['election_found']:
            election = election_results['election']
            google_civic_election_id = election.google_civic_election_id

    if not positive_value_exists(text_for_map_search) or not positive_value_exists(google_civic_election_id):
        status += 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH'
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
            'text_for_map_search': text_for_map_search,
            'polling_location_retrieved': polling_location_retrieved,
            'contests_retrieved': contests_retrieved,
            'ballot_location_display_name': ballot_location_display_name,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
        }
        return results

    try:
        # Make sure we have a latitude and longitude
        google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        location = google_client.geocode(text_for_map_search, sensor=False)
        if location is None:
            status += 'RETRIEVE_FROM_BALLOTPEDIA-Could not find location matching "{}"'.format(text_for_map_search)
            success = False
        else:
            latitude = location.latitude
            longitude = location.longitude
            lat_long_found = True
    except Exception as e:
        status += "RETRIEVE_FROM_BALLOTPEDIA-EXCEPTION with get_geocoder_for_service "
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
            'text_for_map_search': text_for_map_search,
            'polling_location_retrieved': polling_location_retrieved,
            'contests_retrieved': contests_retrieved,
            'ballot_location_display_name': ballot_location_display_name,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
        }
        return results

    one_ballot_results = retrieve_one_ballot_from_ballotpedia_api(latitude, longitude, google_civic_election_id)

    if not one_ballot_results['success']:
        status += 'UNABLE_TO-retrieve_one_ballot_from_ballotpedia_api'
        success = False
    else:
        success = True
        ballot_item_dict_list = one_ballot_results['structured_json']

        if len(ballot_item_dict_list):
            contests_retrieved = True

            # Now that we know we have new ballot data, we need to delete prior ballot data for this election
            # because when we change voterAddress, we usually get different ballot items
            # We include a google_civic_election_id, so only the ballot info for this election is removed
            google_civic_election_id_to_delete = google_civic_election_id
            if positive_value_exists(google_civic_election_id_to_delete) and positive_value_exists(voter_id):
                # Remove all prior ballot items, so we make room for store_one_ballot_from_ballotpedia_api to save
                #  ballot items
                voter_ballot_saved_manager = VoterBallotSavedManager()
                ballot_item_list_manager = BallotItemListManager()

                voter_ballot_saved_id = 0
                voter_ballot_saved_manager.delete_voter_ballot_saved(
                    voter_ballot_saved_id, voter_id, google_civic_election_id_to_delete)

                ballot_item_list_manager.delete_all_ballot_items_for_voter(
                    voter_id, google_civic_election_id_to_delete)

            # store_on_ballot... adds an entry to the BallotReturned table
            # We update VoterAddress with normalized address data in store_one_ballot_from_google_civic_api
            store_one_ballot_results = store_one_ballot_from_ballotpedia_api(
                    ballot_item_dict_list, google_civic_election_id,
                    text_for_map_search, latitude, longitude,
                    ballot_location_display_name,
                    voter_id)
            if store_one_ballot_results['success']:
                status += 'RETRIEVED_FROM_BALLOTPEDIA_AND_STORED_BALLOT_FOR_VOTER '
                success = True
                google_civic_election_id = store_one_ballot_results['google_civic_election_id']
                if store_one_ballot_results['ballot_returned_found']:
                    ballot_returned = store_one_ballot_results['ballot_returned']
                    ballot_location_display_name = ballot_returned.ballot_location_display_name
                    ballot_location_shortcut = ballot_returned.ballot_location_shortcut
                    ballot_returned_we_vote_id = ballot_returned.we_vote_id
            else:
                status += 'UNABLE_TO-store_one_ballot_from_ballotpedia_api: '
                status += store_one_ballot_results['status']

    # If a google_civic_election_id was not returned, outside of this function we search again using a test election,
    # so that during our initial user testing, ballot data is returned in areas where elections don't currently exist

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
        'polling_location_retrieved':   polling_location_retrieved,
        'contests_retrieved':           contests_retrieved,
        'ballot_location_display_name': ballot_location_display_name,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
    }
    return results


def retrieve_one_ballot_from_ballotpedia_api(latitude, longitude, incoming_google_civic_election_id):
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
                                                          contains_api)

    modified_json_list = []
    if groom_results['success']:
        success = True
        modified_json_list = groom_results['modified_json_list']
        contests_retrieved = len(modified_json_list)

        ballot_items_results = process_ballotpedia_voter_districts(
            incoming_google_civic_election_id, modified_json_list, polling_location_we_vote_id)

        if ballot_items_results['ballot_items_found']:
            modified_json_list = ballot_items_results['ballot_item_dict_list']
    else:
        success = False
        status += groom_results['status']

    results = {
        'success': success,
        'status': status,
        'contests_retrieved': contests_retrieved,
        'structured_json': modified_json_list,
    }
    return results


def store_one_ballot_from_ballotpedia_api(ballot_item_dict_list, google_civic_election_id,
                                          text_for_map_search, latitude, longitude,
                                          ballot_location_display_name, voter_id=0, polling_location_we_vote_id=''):
    """
    When we pass in a voter_id, we want to save this ballot related to the voter.
    When we pass in polling_location_we_vote_id, we want to save a ballot for that area, which is useful for
    getting new voters started by showing them a ballot roughly near them.
    """

    election_day_text = ''
    election_description_text = ''
    ocd_division_id = ''
    state_code = ''
    status = ""
    success = True

    if not positive_value_exists(google_civic_election_id):
        results = {
            'status': 'BALLOT_ITEM_DICT_LIST_MISSING_ELECTION_ID',
            'success': False,
            'google_civic_election_id': 0,
        }
        return results

    # Check to see if there is a state served for the election
    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        state_code = election.state_code
        election_day_text = election.election_day_text

    # If we successfully save a ballot, create/update a BallotReturned entry
    ballot_returned_found = False
    ballot_returned = BallotReturned()

    # Make sure we have latitude and longitude
    if positive_value_exists(polling_location_we_vote_id) and not positive_value_exists(latitude) \
            and not positive_value_exists(longitude):
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            latitude = polling_location.latitude
            longitude = polling_location.longitude
        else:
            pass

    # Similar to import_export_batches.controllers, import_ballot_item_data_from_batch_row_actions
    office_manager = ContestOfficeManager()
    measure_manager = ContestMeasureManager()
    google_ballot_placement = 0
    number_of_ballot_items_updated = 0
    measure_subtitle = ""
    measure_text = ""
    for one_ballot_item_dict in ballot_item_dict_list:
        # 'contest_office_we_vote_id': one_office.we_vote_id,
        # 'contest_office_id': one_office.id,
        # 'contest_office_name': one_office.office_name,
        # 'election_day_text': one_district['election_day_text'],
        # 'local_ballot_order': generated_ballot_order,
        # 'polling_location_we_vote_id': polling_location_we_vote_id,
        # 'state_code': one_district['state_code'],

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
        if positive_value_exists(ballot_item_display_name) and positive_value_exists(state_code) \
                and positive_value_exists(google_civic_election_id):
            ballot_item_manager = BallotItemManager()

            defaults = {}
            defaults['measure_url'] = one_ballot_item_dict['ballotpedia_measure_url'] \
                if 'ballotpedia_measure_url' in one_ballot_item_dict else ''
            defaults['yes_vote_description'] = one_ballot_item_dict['ballotpedia_yes_vote_description'] \
                if 'ballotpedia_yes_vote_description' in one_ballot_item_dict else ''
            defaults['no_vote_description'] = one_ballot_item_dict['ballotpedia_no_vote_description'] \
                if 'ballotpedia_no_vote_description' in one_ballot_item_dict else ''

            if positive_value_exists(voter_id):
                results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                        voter_id, google_civic_election_id, google_ballot_placement,
                        ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
                        contest_office_id, contest_office_we_vote_id,
                        contest_measure_id, contest_measure_we_vote_id, state_code, defaults)
                if results['ballot_item_found']:
                    number_of_ballot_items_updated += 1
            elif positive_value_exists(polling_location_we_vote_id):
                results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                    polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
                    ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
                    contest_office_id, contest_office_we_vote_id,
                    contest_measure_id, contest_measure_we_vote_id, state_code, defaults)
                if results['ballot_item_found']:
                    number_of_ballot_items_updated += 1

    # TODO: Figure out best way to save ballot_returned
    if positive_value_exists(number_of_ballot_items_updated):
        ballot_returned_manager = BallotReturnedManager()
        results = ballot_returned_manager.update_or_create_ballot_returned(
            polling_location_we_vote_id, voter_id, google_civic_election_id,
            latitude=latitude, longitude=longitude,
            ballot_location_display_name=ballot_location_display_name, text_for_map_search=text_for_map_search,
            normalized_state=state_code)
        if results['ballot_returned_found']:
            ballot_returned = results['ballot_returned']
            ballot_returned_found = True

    if number_of_ballot_items_updated:
        status += "IMPORT_BALLOT_ITEM_ENTRY:BALLOT_ITEM_UPDATED "

    results = {
        'status':                   status,
        'success':                  success,
        'ballot_returned_found':    ballot_returned_found,
        'ballot_returned':          ballot_returned,
        'google_civic_election_id': google_civic_election_id,
    }
    return results
