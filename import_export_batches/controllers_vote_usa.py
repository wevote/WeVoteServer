# import_export_batches/controllers_vote_usa.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import create_batch_from_json_wrapper, BATCH_HEADER_MAP_BALLOT_ITEMS_TO_VOTE_USA_BALLOT_ITEMS, \
    BATCH_HEADER_MAP_CANDIDATES_TO_VOTE_USA_CANDIDATES, BATCH_HEADER_MAP_CONTEST_OFFICES_TO_VOTE_USA_OFFICES, \
    BATCH_HEADER_MAP_MEASURES_TO_VOTE_USA_MEASURES
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
OFFICE_HELD = 'OFFICE_HELD'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'


def store_vote_usa_json_response_to_import_batch_system(
        modified_json_list=[], google_civic_election_id='', kind_of_batch='',
        batch_set_id=0, state_code=""):
    success = False
    status = ""
    batch_header_id = 0
    number_of_batch_rows = 0
    if kind_of_batch is CONTEST_OFFICE:
        # TODO: Not updated from Ballotpedia yet
        filename = "Races from Vote USA API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_CONTEST_OFFICES_TO_VOTE_USA_OFFICES, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results
    elif kind_of_batch is CANDIDATE:
        # TODO: Not updated from Ballotpedia yet
        filename = "Candidates from Vote USA API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_CANDIDATES_TO_VOTE_USA_CANDIDATES, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results
    elif kind_of_batch is MEASURE:
        # TODO: Not updated from Ballotpedia yet
        filename = "Measures from Vote USA API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_MEASURES_TO_VOTE_USA_MEASURES, kind_of_batch,
            google_civic_election_id, organization_we_vote_id, batch_set_id=batch_set_id, state_code=state_code)
        return results
    elif kind_of_batch is IMPORT_BALLOT_ITEM:
        filename = "Ballot Items for Address from Vote USA API"
        if state_code != "":
            filename += " for " + state_code.upper()
        organization_we_vote_id = ""
        results = create_batch_from_json_wrapper(
            filename, modified_json_list,
            BATCH_HEADER_MAP_BALLOT_ITEMS_TO_VOTE_USA_BALLOT_ITEMS, kind_of_batch,
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
