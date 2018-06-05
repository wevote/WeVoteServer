# elected_official/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from import_export_google_civic.models import GoogleCivicApiCounterManager
import json
import requests
from wevote_functions.functions import positive_value_exists, logger

# GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
# REPRESENTATIVES_BY_ADDRESS_URL = get_environment_variable("REPRESENTATIVES_BY_ADDRESS_URL")


# Moved to import_export_google_civic/controllers.py
# def retrieve_elected_officials_from_google_civic_api(text_for_map_search, incoming_google_civic_election_id=0,
#                                                      use_test_elected_officials=False):
#     # Request json file from Google servers
#     # logger.info("Loading ballot for one address from representativeInfoByAddress from Google servers")
#     print("retrieving elected officials for " + str(incoming_google_civic_election_id))
#     if positive_value_exists(use_test_elected_officials):
#         response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
#             "key": GOOGLE_CIVIC_API_KEY,
#             "address": text_for_map_search,
#             "includeOffices": True,  # The Google Civic API Test election
#         })
#     elif positive_value_exists(incoming_google_civic_election_id):
#         response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
#             "key": GOOGLE_CIVIC_API_KEY,
#             "address": text_for_map_search,
#             "includeOffices": True,
#         })
#     else:
#         response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
#             "key": GOOGLE_CIVIC_API_KEY,
#             "address": text_for_map_search,
#         })
#
#     structured_json = json.loads(response.text)
#     if 'success' in structured_json and not structured_json['success']:
#         import_results = {
#             'success': False,
#             'status': "Error: " + structured_json['status'],
#         }
#         return import_results
#
#     # # For internal testing. Write the json retrieved above into a local file
#     # with open('/Users/dalemcgrew/PythonProjects/WeVoteServer/'
#     #           'import_export_google_civic/import_data/voterInfoQuery_VA_sample.json', 'w') as f:
#     #     json.dump(structured_json, f)
#     #     f.closed
#     #
#     # # TEMP - FROM FILE (so we aren't hitting Google Civic API during development)
#     # with open("import_export_google_civic/import_data/voterInfoQuery_VA_sample.json") as json_data:
#     #     structured_json = json.load(json_data)
#
#     # Verify that we got elected officials. (If you use an address in California for an elected office in New York,
#     #  you won't get a elected officials for example.)
#     success = False
#     elected_officials_data_retrieved = False
#     # polling_location_retrieved = False
#     # contests_retrieved = False
#     # election_administration_data_retrieved = False
#     google_civic_election_id = 0
#     error = structured_json.get('error', {})
#     errors = error.get('errors', {})
#     if len(errors):
#         logger.debug("retrieve_elected_officials_from_google_civic_api failed: " + str(errors))
#
#     if 'offices' in structured_json and len(structured_json['officials']) != 0:
#             elected_officials_data_retrieved = True
#             success = True
#
#     # Use Google Civic API call counter to track the number of queries we are doing each day
#     google_civic_api_counter_manager = GoogleCivicApiCounterManager()
#     google_civic_api_counter_manager.create_counter_entry('elected_official', google_civic_election_id)
#
#     # if 'pollingLocations' in structured_json:
#     #     polling_location_retrieved = True
#     #     success = True
#     #
#     # if 'contests' in structured_json:
#     #     if len(structured_json['contests']) > 0:
#     #         contests_retrieved = True
#     #         success = True
#     #
#     # if 'state' in structured_json:
#     #     if len(structured_json['state']) > 0:
#     #         if 'electionAdministrationBody' in structured_json['state'][0]:
#     #             election_administration_data_retrieved = True
#     #             success = True
#
#     results = {
#         'success':                                  success,
#         'elected_officials_data_retrieved':         elected_officials_data_retrieved,
#         # 'polling_location_retrieved':               polling_location_retrieved,
#         # 'contests_retrieved':                       contests_retrieved,
#         # 'election_administration_data_retrieved':   election_administration_data_retrieved,
#         'structured_json':                          structured_json,
#     }
#     return results
