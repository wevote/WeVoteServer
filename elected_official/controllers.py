# elected_official/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from import_export_google_civic.models import GoogleCivicApiCounterManager
import json
import requests
from wevote_functions.functions import positive_value_exists, logger

GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
REPRESENTATIVES_BY_ADDRESS_URL = get_environment_variable("REPRESENTATIVES_BY_ADDRESS_URL")


def retrieve_elected_officials_from_google_civic_api(text_for_map_search, incoming_google_civic_election_id=0,
                                                     use_test_elected_officials=False):
    # Request json file from Google servers
    # logger.info("Loading ballot for one address from representativeInfoByAddress from Google servers")
    print("retrieving elected officials for " + str(incoming_google_civic_election_id))
    if positive_value_exists(use_test_elected_officials):
        response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,
            "address": text_for_map_search,
            "includeOffices": True,  # The Google Civic API Test election
        })
    elif positive_value_exists(incoming_google_civic_election_id):
        response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,
            "address": text_for_map_search,
            "includeOffices": True,
        })
    else:
        response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,
            "address": text_for_map_search,
        })

    structured_json = json.loads(response.text)
    if 'success' in structured_json and not structured_json['success']:
        import_results = {
            'success': False,
            'status': "Error: " + structured_json['status'],
        }
        return import_results

    # # For internal testing. Write the json retrieved above into a local file
    # with open('/Users/dalemcgrew/PythonProjects/WeVoteServer/'
    #           'import_export_google_civic/import_data/voterInfoQuery_VA_sample.json', 'w') as f:
    #     json.dump(structured_json, f)
    #     f.closed
    #
    # # TEMP - FROM FILE (so we aren't hitting Google Civic API during development)
    # with open("import_export_google_civic/import_data/voterInfoQuery_VA_sample.json") as json_data:
    #     structured_json = json.load(json_data)

    # Verify that we got elected officials. (If you use an address in California for an elected office in New York,
    #  you won't get a elected officials for example.)
    success = False
    elected_officials_data_retrieved = False
    # polling_location_retrieved = False
    # contests_retrieved = False
    # election_administration_data_retrieved = False
    google_civic_election_id = 0
    error = structured_json.get('error', {})
    errors = error.get('errors', {})
    if len(errors):
        logger.debug("retrieve_elected_officials_from_google_civic_api failed: " + str(errors))

    if 'offices' in structured_json and len(structured_json['officials']) != 0:
            elected_officials_data_retrieved = True
            success = True

    # Use Google Civic API call counter to track the number of queries we are doing each day
    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_api_counter_manager.create_counter_entry('elected_official', google_civic_election_id)

    # if 'pollingLocations' in structured_json:
    #     polling_location_retrieved = True
    #     success = True
    #
    # if 'contests' in structured_json:
    #     if len(structured_json['contests']) > 0:
    #         contests_retrieved = True
    #         success = True
    #
    # if 'state' in structured_json:
    #     if len(structured_json['state']) > 0:
    #         if 'electionAdministrationBody' in structured_json['state'][0]:
    #             election_administration_data_retrieved = True
    #             success = True

    results = {
        'success':                                  success,
        'elected_officials_data_retrieved':         elected_officials_data_retrieved,
        # 'polling_location_retrieved':               polling_location_retrieved,
        # 'contests_retrieved':                       contests_retrieved,
        # 'election_administration_data_retrieved':   election_administration_data_retrieved,
        'structured_json':                          structured_json,
    }
    return results

# In progress
# # See import_data/voterInfoQuery_VA_sample.json
# def store_one_elected_official_from_google_civic_api(one_elected_official_json, polling_location_we_vote_id=''):
#     """
#     When we pass in polling_location_we_vote_id, we want to save a elected official for that area, which is useful for
#     getting new eletced offices started by showing them a elected officials roughly near them.
#     """
#     #     "election": {
#     #     "electionDay": "2015-11-03",
#     #     "id": "4162",
#     #     "name": "Virginia General Election",
#     #     "ocdDivisionId": "ocd-division/country:us/state:va"
#     # },
#     # if 'election' not in one_elected_official_json:
#     #     results = {
#     #         'status': 'BALLOT_JSON_MISSING_ELECTION',
#     #         'success': False,
#     #         'google_civic_election_id': 0,
#     #     }
#     #     return results
#
#     election_day_text = ''
#     election_description_text = ''
#     if 'name' in one_elected_official_json:
#         elected_official_name = one_elected_official_json['name']
#
#     if 'id' not in one_elected_official_json['election']:
#         results = {
#             'status': 'BALLOT_JSON_MISSING_ELECTION_ID',
#             'success': False,
#             'google_civic_election_id': 0,
#         }
#         return results
#
#     voter_address_dict = one_elected_official_json['normalizedInput'] if 'normalizedInput' in
#                               one_elected_official_json else {}
#     if positive_value_exists(voter_id):
#         if positive_value_exists(voter_address_dict):
#             # When saving a ballot for an individual voter, use this data to update voter address with the
#             #  normalized address information returned from Google Civic
#             # "normalizedInput": {
#             #   "line1": "254 hartford st",
#             #   "city": "san francisco",
#             #   "state": "CA",
#             #   "zip": "94114"
#             #  },
#             voter_address_manager = VoterAddressManager()
#             voter_address_manager.update_voter_address_with_normalized_values(
#                 voter_id, voter_address_dict)
#             # Note that neither 'success' nor 'status' are set here because updating the voter_address with normalized
#             # values isn't critical to the success of storing the ballot for a voter
#     # We don't store the normalized address information when we capture a ballot for a polling location
#
#     google_civic_election_id = one_elected_official_json['election']['id']
#     ocd_division_id = one_elected_official_json['election']['ocdDivisionId']
#     state_code = extract_state_from_ocd_division_id(ocd_division_id)
#     if not positive_value_exists(state_code):
#         # We have a backup method of looking up state from one_elected_official_json['state']['name']
#         # in case the ocd state fails
#         state_name = ''
#         if 'state' in one_elected_official_json:
#             if 'name' in one_elected_official_json['state']:
#                 state_name = one_elected_official_json['state']['name']
#             elif len(one_elected_official_json['state']) > 0:
#                 # In some cases, like test elections 2000 a list is returned in one_elected_official_json['state']
#                 for one_state_entry in one_elected_official_json['state']:
#                     if 'name' in one_state_entry:
#                         state_name = one_state_entry['name']
#         state_code = convert_state_text_to_state_code(state_name)
#     if not positive_value_exists(state_code):
#         if 'normalizedInput' in one_elected_official_json:
#             state_code = one_elected_official_json['normalizedInput']['state']
#
#     # Loop through all contests and store in local db cache
#     if 'contests' in one_elected_official_json:
#         results = process_contests_from_structured_json(one_elected_official_json['contests'],
#                                                         google_civic_election_id,
#                                                         ocd_division_id, state_code, voter_id,
#                                                         polling_location_we_vote_id)
#
#         status = results['status']
#         success = results['success']
#     else:
#         status = "STORE_ONE_BALLOT_NO_CONTESTS_FOUND"
#         success = False
#
#     # When saving a ballot for individual voter, loop through all pollingLocations and store in local db
#     # process_polling_locations_from_structured_json(one_elected_official_json['pollingLocations'])
#
#     # If we successfully save a ballot, create/update a BallotReturned entry
#     ballot_returned_found = False
#     ballot_returned = BallotReturned()
#     is_test_election = True if positive_value_exists(google_civic_election_id) \
#         and convert_to_int(google_civic_election_id) == 2000 else False
#
#     # Make sure we have this polling_location
#     polling_location_manager = PollingLocationManager()
#     results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
#     polling_location_latitude = None
#     polling_location_longitude = None
#     if results['polling_location_found']:
#         polling_location = results['polling_location']
#         polling_location_latitude = polling_location.latitude
#         polling_location_longitude = polling_location.longitude
#     else:
#         logger.info("No location found for " + str(results))
#
#     if success and positive_value_exists(voter_address_dict) and not is_test_election:
#         ballot_returned_manager = BallotReturnedManager()
#         if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
#             results = ballot_returned_manager.retrieve_ballot_returned_from_voter_id(voter_id,
#                                                                                      google_civic_election_id)
#             if results['ballot_returned_found']:
#                 update_results = ballot_returned_manager.update_ballot_returned_with_normalized_values(
#                     voter_address_dict, results['ballot_returned'],
#                     polling_location_latitude, polling_location_longitude)
#                 # If the update fails, we just return the original ballot_returned object
#                 ballot_returned_found = True
#                 ballot_returned = update_results['ballot_returned']
#             else:
#                 create_results = ballot_returned_manager.create_ballot_returned_with_normalized_values(
#                     voter_address_dict,
#                     election_day_text, election_description_text,
#                     google_civic_election_id, voter_id, '')
#                 # We store ballot_returned entries without latitude and longitude here.
#                 # These entries will not be found by a geo search until we augment them with latitude and longitude
#                 #  which we do at a later state. We do not do the latitude/longitude lookup here because the number
#                 #  of geocode lookups we can do is limited, and we want to manage our "lookup" budget separate
#                 #  from this function.
#                 ballot_returned_found = create_results['ballot_returned_found']
#                 ballot_returned = create_results['ballot_returned']
#         if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
#             results = ballot_returned_manager.retrieve_ballot_returned_from_polling_location_we_vote_id(
#                 polling_location_we_vote_id, google_civic_election_id)
#             if results['ballot_returned_found']:
#                 update_results = ballot_returned_manager.update_ballot_returned_with_normalized_values(
#                     voter_address_dict, results['ballot_returned'],
#                     polling_location_latitude, polling_location_longitude)
#                 # If the update fails, we just return the original ballot_returned object
#                 ballot_returned_found = True
#                 ballot_returned = update_results['ballot_returned']
#             else:
#                 voter_id = 0
#                 create_results = ballot_returned_manager.create_ballot_returned_with_normalized_values(
#                     voter_address_dict,
#                     election_day_text, election_description_text,
#                     google_civic_election_id, voter_id, polling_location_we_vote_id,
#                     polling_location_latitude, polling_location_longitude)
#                 ballot_returned_found = create_results['ballot_returned_found']
#                 ballot_returned = create_results['ballot_returned']
#
#         # Currently we don't report the success or failure of storing ballot_returned
#
#     results = {
#         'status':                   status,
#         'success':                  success,
#         'ballot_returned_found':    ballot_returned_found,
#         'ballot_returned':          ballot_returned,
#         'google_civic_election_id': google_civic_election_id,
#     }
#     return results
