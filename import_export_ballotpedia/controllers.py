# import_export_ballotpedia/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from candidate.models import fetch_candidate_count_for_office
from config.base import get_environment_variable
from import_export_batches.models import BatchManager, \
    CANDIDATE, CONTEST_OFFICE, ELECTED_OFFICE, IMPORT_BALLOT_ITEM, MEASURE, \
    BATCH_HEADER_MAP_CANDIDATES_TO_BALLOTPEDIA_CANDIDATES, BATCH_HEADER_MAP_CONTEST_OFFICES_TO_BALLOTPEDIA_RACES, \
    BATCH_HEADER_MAP_MEASURES_TO_BALLOTPEDIA_MEASURES, BATCH_HEADER_MAP_BALLOT_ITEMS_TO_BALLOTPEDIA_VOTER_DISTRICTS
import json
from measure.models import ContestMeasureList
from office.models import ContestOfficeListManager
from polling_location.models import PollingLocationManager
import requests
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP

BALLOTPEDIA_API_KEY = get_environment_variable("BALLOTPEDIA_API_KEY")
BALLOTPEDIA_API_CANDIDATES_URL = get_environment_variable("BALLOTPEDIA_API_CANDIDATES_URL")
BALLOTPEDIA_API_CONTAINS_URL = get_environment_variable("BALLOTPEDIA_API_CONTAINS_URL")
BALLOTPEDIA_API_ELECTIONS_URL = get_environment_variable("BALLOTPEDIA_API_ELECTIONS_URL")
BALLOTPEDIA_API_MEASURES_URL = get_environment_variable("BALLOTPEDIA_API_MEASURES_URL")
BALLOTPEDIA_API_RACES_URL = get_environment_variable("BALLOTPEDIA_API_RACES_URL")


def extract_value_from_array(structured_json, index_key, default_value):
    if index_key in structured_json:
        return structured_json[index_key]
    else:
        return default_value


def retrieve_candidates_from_api(google_civic_election_id, zero_entries=True):
    success = True
    status = ""

    if not positive_value_exists(google_civic_election_id):
        results = {
            'success': False,
            'status': "Error: Missing election id",
        }
        return results

    maximum_number_to_retrieve = 50
    state_code = ""
    batch_header_id = 0
    return_list_of_objects = True
    contest_list_manager = ContestOfficeListManager()
    results = contest_list_manager.retrieve_offices(
        google_civic_election_id, state_code, [], return_list_of_objects)

    filtered_office_list = []
    office_count = 0
    if results['office_list_found']:
        office_list_objects = results['office_list_objects']

        for one_office in office_list_objects:
            candidate_count = fetch_candidate_count_for_office(one_office.id)
            if not positive_value_exists(candidate_count):
                filtered_office_list.append(one_office)
                office_count += 1

                if office_count >= maximum_number_to_retrieve:
                    # Limit to showing only maximum_number_to_retrieve
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

        candidate_status_string = "Candidacy Declared,On the Ballot"

        response = requests.get(BALLOTPEDIA_API_CANDIDATES_URL, params={
            "access_token": BALLOTPEDIA_API_KEY,
            "filters[race][in]": races_to_retrieve_string,
            "filters[status][in]": candidate_status_string,
            "limit": 1000,
        })

        structured_json = json.loads(response.text)

        # # Use Google Civic API call counter to track the number of queries we are doing each day
        # google_civic_api_counter_manager = GoogleCivicApiCounterManager()
        # google_civic_api_counter_manager.create_counter_entry('ballot', google_civic_election_id)

        results = process_ballotpedia_json_response(structured_json, google_civic_election_id)
        status += results['status']
        if 'batch_header_id' in results:
            batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def retrieve_districts_to_which_address_belongs_from_api(
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

        # # Use Google Civic API call counter to track the number of queries we are doing each day
        # google_civic_api_counter_manager = GoogleCivicApiCounterManager()
        # google_civic_api_counter_manager.create_counter_entry('ballot', google_civic_election_id)

        contains_api = True
        results = process_ballotpedia_json_response(structured_json, google_civic_election_id,
                                                    contains_api, polling_location_we_vote_id)
        status += results['status']
        if 'batch_header_id' in results:
            batch_header_id = results['batch_header_id']

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
    }
    return results


def process_ballotpedia_json_response(structured_json, google_civic_election_id,
                                      contains_api=False, polling_location_we_vote_id=""):
    success = False
    status = ""
    batch_header_id = 0
    number_of_batch_rows = 0
    batch_manager = BatchManager()
    # if kind_of_batch not in (MEASURE, ELECTED_OFFICE, CONTEST_OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION,
    #                          POLITICIAN, IMPORT_BALLOT_ITEM):

    if 'data' in structured_json:
        if 'meta' in structured_json:
            if 'table' in structured_json['meta']:
                if structured_json['meta']['table'] == 'races':
                    kind_of_batch = CONTEST_OFFICE
                    races_json_list = structured_json['data']
                    modified_races_json_list = []
                    # Loop through this data and move ['office']['data'] into root level
                    for one_office_json in races_json_list:
                        try:
                            inner_election_json = one_office_json['election']['data']
                            inner_office_json = one_office_json['office']['data']
                            # Add our own key/value pairs
                            # root level
                            one_office_json['ballotpedia_race_id'] = one_office_json['id']
                            # election
                            one_office_json['ballotpedia_election_id'] = inner_election_json['id']
                            # office
                            one_office_json['ballotpedia_district_id'] = inner_office_json['district']
                            one_office_json['ballotpedia_office_id'] = inner_office_json['id']
                            one_office_json['state_code'] = inner_office_json['district_state']
                        except KeyError:
                            pass
                        modified_races_json_list.append(one_office_json)

                    filename = "Races from Ballotpedia API"
                    organization_we_vote_id = ""
                    results = batch_manager.create_batch_from_json(
                        filename, modified_races_json_list,
                        BATCH_HEADER_MAP_CONTEST_OFFICES_TO_BALLOTPEDIA_RACES, kind_of_batch,
                        google_civic_election_id, organization_we_vote_id)
                    return results
                elif structured_json['meta']['table'] == 'candidates':
                    kind_of_batch = CANDIDATE
                    candidates_json_list = structured_json['data']
                    modified_candidates_json_list = []
                    # Loop through this data and move ['office']['data'] into root level
                    for one_candidate_json in candidates_json_list:
                        try:
                            # Add our own key/value pairs
                            # root level
                            one_candidate_json['ballotpedia_candidate_id'] = one_candidate_json['id']
                            one_candidate_json['candidate_participation_status'] = \
                                one_candidate_json['status']
                            one_candidate_json['is_incumbent'] = one_candidate_json['is_incumbent']
                            # race
                            if 'race' in one_candidate_json \
                                    and one_candidate_json['race'] \
                                    and 'data' in one_candidate_json['race']:
                                inner_race_json = one_candidate_json['race']['data']
                                one_candidate_json['ballotpedia_race_id'] = inner_race_json['id']
                                one_candidate_json['ballotpedia_office_id'] = inner_race_json['office']
                                one_candidate_json['ballotpedia_election_id'] = inner_race_json['election']
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
                                one_candidate_json['crowdpac_candidate_id'] = \
                                    inner_person_json['crowdpac_candidate_id']
                                one_candidate_json['birth_day_text'] = inner_person_json['date_born']
                            # party_affiliation
                            if 'party_affiliation' in one_candidate_json \
                                    and one_candidate_json['party_affiliation'] \
                                    and 'data' in one_candidate_json['party_affiliation']:
                                inner_party_affiliation_json = one_candidate_json['party_affiliation']['data']
                                one_candidate_json['candidate_party_name'] = inner_party_affiliation_json['name']
                        except KeyError:
                            pass
                        modified_candidates_json_list.append(one_candidate_json)

                    filename = "Candidates from Ballotpedia API"
                    organization_we_vote_id = ""
                    results = batch_manager.create_batch_from_json(
                        filename, modified_candidates_json_list,
                        BATCH_HEADER_MAP_CANDIDATES_TO_BALLOTPEDIA_CANDIDATES, kind_of_batch,
                        google_civic_election_id, organization_we_vote_id)
                    return results
                elif structured_json['meta']['table'] == 'ballot_measures':
                    kind_of_batch = MEASURE
                    measures_json_list = structured_json['data']
                    modified_measures_json_list = []
                    # Loop through this data and move ['office']['data'] into root level
                    for one_measure_json in measures_json_list:
                        try:
                            inner_election_json = one_measure_json['election']['data']
                            inner_district_json = one_measure_json['district']['data']
                            # Add our own key/value pairs
                            # root
                            one_measure_json['ballotpedia_measure_id'] = one_measure_json['id']
                            one_measure_json['ballotpedia_measure_url'] = one_measure_json['url']
                            one_measure_json['election_day_text'] = one_measure_json['election_date']
                            # election
                            one_measure_json['ballotpedia_election_id'] = inner_election_json['id']
                            # district
                            one_measure_json['ballotpedia_district_id'] = inner_district_json['id']
                            one_measure_json['state_code'] = inner_district_json['state']
                        except KeyError:
                            pass
                        modified_measures_json_list.append(one_measure_json)

                    filename = "Measures from Ballotpedia API"
                    organization_we_vote_id = ""
                    results = batch_manager.create_batch_from_json(
                        filename, modified_measures_json_list,
                        BATCH_HEADER_MAP_MEASURES_TO_BALLOTPEDIA_MEASURES, kind_of_batch,
                        google_civic_election_id, organization_we_vote_id)
                    return results
    elif contains_api:
        kind_of_batch = IMPORT_BALLOT_ITEM
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
                one_district_json['election_day_text'] = ""
            except KeyError:
                pass
            modified_district_json_list.append(one_district_json)

        ballot_items_results = process_ballotpedia_voter_districts(
            google_civic_election_id, modified_district_json_list, polling_location_we_vote_id)

        if ballot_items_results['ballot_items_found']:
            ballot_item_dict_list = ballot_items_results['ballot_item_dict_list']

            filename = "Ballot Items for Address from Ballotpedia API"
            organization_we_vote_id = ""
            results = batch_manager.create_batch_from_json(
                filename, ballot_item_dict_list,
                BATCH_HEADER_MAP_BALLOT_ITEMS_TO_BALLOTPEDIA_VOTER_DISTRICTS, kind_of_batch,
                google_civic_election_id, organization_we_vote_id)
            return results
        else:
            status += "NO_BALLOT_ITEMS_FOUND_IN_WE_VOTE "
    else:
        status += "IMPORT_BALLOTPEDIA_STRUCTURED_JSON_NOT_RECOGNIZED"

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'batch_saved': success,
        'number_of_batch_rows': number_of_batch_rows,
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
