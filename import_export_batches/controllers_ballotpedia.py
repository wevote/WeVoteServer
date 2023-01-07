# import_export_batches/controllers_ballotpedia.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import create_batch_from_json_wrapper, BATCH_HEADER_MAP_BALLOT_ITEMS_TO_BALLOTPEDIA_BALLOT_ITEMS, \
    BATCH_HEADER_MAP_CANDIDATES_TO_BALLOTPEDIA_CANDIDATES, BATCH_HEADER_MAP_CONTEST_OFFICES_TO_BALLOTPEDIA_RACES, \
    BATCH_HEADER_MAP_MEASURES_TO_BALLOTPEDIA_MEASURES
# from import_export_ballotpedia.controllers import groom_ballotpedia_data_for_processing
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

# VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
ELECTED_OFFICE = 'ELECTED_OFFICE'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'


def store_ballotpedia_json_response_to_import_batch_system(
        modified_json_list=[], google_civic_election_id='', kind_of_batch='',
        batch_set_id=0, state_code=""):
    success = False
    status = ""
    batch_header_id = 0
    number_of_batch_rows = 0
    if kind_of_batch is CONTEST_OFFICE:
        filename = "Races from Ballotpedia API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_CONTEST_OFFICES_TO_BALLOTPEDIA_RACES, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results
    elif kind_of_batch is CANDIDATE:
        filename = "Candidates from Ballotpedia API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_CANDIDATES_TO_BALLOTPEDIA_CANDIDATES, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results
    elif kind_of_batch is MEASURE:
        filename = "Measures from Ballotpedia API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_MEASURES_TO_BALLOTPEDIA_MEASURES, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results
    elif kind_of_batch is IMPORT_BALLOT_ITEM:
        filename = "Ballot Items for Address from Ballotpedia API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        # BATCH_HEADER_MAP_BALLOT_ITEMS_TO_BALLOTPEDIA_VOTER_DISTRICTS was used, but didn't make sense
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_BALLOT_ITEMS_TO_BALLOTPEDIA_BALLOT_ITEMS, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'batch_saved': success,
        'number_of_batch_rows': number_of_batch_rows,
    }
    return results
