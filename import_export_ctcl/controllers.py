# import_export_ctcl/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import xml.etree.ElementTree as ElementTree
from .models import CandidateSelection, CTCLApiCounterManager
from ballot.models import BallotReturnedManager
from config.base import get_environment_variable
from datetime import datetime
from electoral_district.controllers import electoral_district_import_from_xml_data
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from import_export_batches.controllers_ctcl import store_ctcl_json_response_to_import_batch_system
from import_export_google_civic.controllers import groom_and_store_google_civic_ballot_json_2021
import json
from party.controllers import party_import_from_xml_data
from polling_location.models import KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR, \
    KIND_OF_LOG_ENTRY_API_END_POINT_CRASH, KIND_OF_LOG_ENTRY_BALLOT_RECEIVED, KIND_OF_LOG_ENTRY_NO_CONTESTS, \
    KIND_OF_LOG_ENTRY_NO_BALLOT_JSON, PollingLocationManager
import requests
import wevote_functions.admin
from wevote_functions.functions import extract_state_code_from_address_string, positive_value_exists
from wevote_functions.functions_date import convert_we_vote_date_string_to_date

logger = wevote_functions.admin.get_logger(__name__)

CTCL_API_KEY = get_environment_variable("CTCL_API_KEY")
CTCL_ELECTION_QUERY_URL = "https://api.ballotinfo.org/elections"
CTCL_SAMPLE_XML_FILE = "import_export_ctcl/import_data/GoogleCivic.Sample.xml"
CTCL_VOTER_INFO_URL = "http://api.ballotinfo.org/voterinfo"
CTCL_API_VOTER_INFO_QUERY_TYPE = "voterinfo"


HEADERS_FOR_CTCL_API_CALL = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Host': 'api.ballotinfo.org',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0',
}

PRESIDENTIAL_CANDIDATES_JSON_LIST = [
    {
        'id': 54804,
        'race': 31729,
        'is_incumbent': True,
        'party_affiliation': [{
            'id': 1,
            'name': 'Republican Party',
            'url': 'https://ballotpedia.org/Republican_Party',
        }],
        'person': {
            'id': 15180,
            'image': {
            },
            'name': 'Donald Trump',
            'first_name': 'Donald',
            'last_name': 'Trump',
        },
    },
    {
        'id': 59216,
        'race': 31729,
        'is_incumbent': False,
        'party_affiliation': [{
            'id': 2,
            'name': 'Democratic Party',
            'url': 'https://ballotpedia.org/Democratic_Party',
        }],
        'person': {
            'id': 26709,
            'image': {
            },
            'name': 'Joe Biden',
            'first_name': 'Joe',
            'last_name': 'Biden',
        },
    },
]


# Deprecated function, currently not used
def import_ctcl_from_xml(request):
    load_from_url = False
    results = ''
    success = False
    status = ''
    if load_from_url:
        # Request xml file from CTCL servers
        logger.debug("TO BE IMPLEMENTED: Load CTCL XML from url")
    else:
        # Load saved xml from local file
        xml_tree = ElementTree.parse(CTCL_SAMPLE_XML_FILE)
        xml_root = xml_tree.getroot()
        logger.debug("Loading CTCL sample XML from local file")

        if xml_root:
            # Look for ElectoralDistrict and create the Master table first. ElectoralDistrict is the direct child node
            # of VipObject
            electoral_district_item_list = ''

            electoral_district_item_list = xml_root.findall('ElectoralDistrict')
            if electoral_district_item_list:
                electoral_district_results = electoral_district_import_from_xml_data(electoral_district_item_list)

                if not electoral_district_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'ELECTORAL_DISTRICT_IMPORT_FAILED'
                    }
                    return results
                    # to_continue_parsing = False

            # Look for Party data and create Master table. Party is the direct child node of VipObject
            party_item_list = xml_root.findall('Party')

            party_results = party_import_from_xml_data(party_item_list)
            if not party_results['success']:
                results = {
                    'success': False,
                    'import_complete': 'PARTY_IMPORT_FAILED'
                }
                return results

            # Create a batch manager and invoke its class functions
            # TODO fix below import, temporary fix to avoid circular dependency
            from import_export_batches.models import BatchManager
            try:
                batch_manager = BatchManager()
                # Ballot Measure import, look for BallotMeasureContest
                ballot_measure_results = ''
                ballot_measure_results = batch_manager.store_measure_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not ballot_measure_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'BALLOT_MEASURE_IMPORT_FAILED'
                    }
                    return results

                # Office import, look for Office
                office_results = ''
                office_results = batch_manager.store_office_held_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not office_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'OFFICE_HELD_IMPORT_FAILED'
                    }
                    return results

                politician_results = ''
                politician_results = batch_manager.store_politician_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not politician_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'POLITICIAN_IMPORT_FAILED'
                    }
                    return results

                candidate_results = ''
                candidate_results = batch_manager.store_candidate_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not candidate_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'CANDIDATE_IMPORT_FAILED'
                    }
                    return results

            except BatchManager.DoesNotExist:
                status = 'IMPORT_FAILED'
                success = False

                # success = 'True'
                # status = 'CTCL_SAMPLE_DATA_IMPORT_COMPLETE'

    results = {
        'success': True,
        'import_complete': 'CTCL_SAMPLE_DATA_IMPORT_COMPLETE'
    }

    return results


def create_candidate_selection_rows(xml_root, batch_set_id=0):
    """
    Create candidate selection entries in the CandidateSelection table based on CTCL XML CandidateSelection node values
    :param xml_root: 
    :param batch_set_id: 
    :return: 
    """
    success = False
    status = ''
    candidate_selection_created = False

    # Look for CandidateSelection and create the batch_header first. CandidateSelection is the direct child node
    # of VipObject
    candidate_selection_xml_node = xml_root.findall('CandidateSelection')
    candidate_selection = ''
    number_of_batch_rows = 0

    for one_candidate_selection in candidate_selection_xml_node:
        # look for relevant information under CandidateSelection: id, CandidateIds
        candidate_selection_id = one_candidate_selection.attrib['id']

        contest_office_id_node = one_candidate_selection.find("./CandidateIds")
        if contest_office_id_node is None:
            candidate_selection = CandidateSelection()
            results = {
                'success':                      False,
                'status':                       'CREATE_CANDIDATE_SELECTION_ROWS-CONTEST_OFFICE_ID_NOT_FOUND',
                'candidate_selection_created':  False,
                'candidate_selection':          candidate_selection,
            }
            return results

        contest_office_id = contest_office_id_node.text

        try:
            candidate_selection = CandidateSelection.objects.create(batch_set_id=batch_set_id,
                                                                    candidate_selection_id=candidate_selection_id,
                                                                    contest_office_id=contest_office_id)
            if candidate_selection:
                candidate_selection_created = True
                success = True
                status = "CANDIDATE_SELECTION_CREATED"
                number_of_batch_rows += 1
        except Exception as e:
            candidate_selection_created = False
            candidate_selection = CandidateSelection()
            success = False
            status = "CANDIDATE_SELECTION_NOT_CREATED"
            handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                      success,
        'status':                       status,
        'candidate_selection_created':  candidate_selection_created,
        'candidate_selection':          candidate_selection,
        'number_of_batch_rows':         number_of_batch_rows
    }
    return results


def retrieve_candidate_from_candidate_selection(candidate_selection_id, batch_set_id):
    """
    Given candidate_selection_id, get corresponding candidate name
    :param candidate_selection_id: 
    :param batch_set_id:
    :return: 
    """
    results = ''
    candidate_id = ''
    candidate_id_found = False

    if not candidate_selection_id or not positive_value_exists(batch_set_id):
        candidate_selection_item = CandidateSelection()
        results = {
            'candidate_id_found':   candidate_id_found,
            'candidate_selection':  candidate_selection_item,
        }
        return results

    # Look up CandidateSelection table with candidate_selection_id
    try:
        candidate_selection_query = CandidateSelection.objects.all()
        candidate_selection_item = candidate_selection_query.get(candidate_selection_id=candidate_selection_id,
                                                                 batch_set_id=batch_set_id)
        if candidate_selection_item:
            candidate_id_found = True

    except CandidateSelection.MultipleObjectsReturned as e:
        candidate_selection_item = CandidateSelection()
        handle_record_found_more_than_one_exception(e, logger)

        status = "ERROR_MORE_THAN_ONE_CANDIDATE_SELECTION_FOUND"

    except CandidateSelection.DoesNotExist:
        status = "CANDIDATE_SELECTION_DOES_NOT_EXIST"
        candidate_selection_item = CandidateSelection()
        # handle_exception(e, logger=logger, exception_message=status)

    # return candidate_selection_item
    results = {
        'candidate_id_found': candidate_id_found,
        'candidate_selection':       candidate_selection_item,
    }

    return results


def retrieve_ctcl_ballot_items_for_one_voter_api(
        google_civic_election_id,
        ctcl_election_uuid="",
        election_day_text="",
        ballot_returned=None,
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
    success = True
    status = ""
    batch_header_id = 0

    if not positive_value_exists(google_civic_election_id) or not positive_value_exists(ctcl_election_uuid):
        status += "Error-CTCL: Missing election id or ctcl_election_uuid"
        results = {
            'success': False,
            'status': status,
            'ballot_returned':  ballot_returned,
            'ballot_returned_found':  False,
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

    ballot_returned_error = False
    voter_id = 0
    if ballot_returned:
        voter_id = ballot_returned.voter_id
    else:
        ballot_returned_error = True
        status += "Error-CTCL: Missing ballot_returned object"

    if not ballot_returned.voter_id:
        ballot_returned_error = True
        status += "Error-CTCL: Missing ballot_returned.voter_id"

    if not ballot_returned.text_for_map_search:
        ballot_returned_error = True
        status += "Error-CTCL: Missing ballot_returned.text_for_map_search"

    if ballot_returned_error:
        results = {
            'success': False,
            'status': status,
            'ballot_returned':  ballot_returned,
            'ballot_returned_found':  False,
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

    ballot_returned_found = False
    text_for_map_search = ''
    if ballot_returned:
        text_for_map_search = ballot_returned.text_for_map_search

        if not positive_value_exists(ballot_returned.state_code):
            # Can we get state_code from normalized_state?
            if positive_value_exists(ballot_returned.normalized_state):
                ballot_returned.state_code = ballot_returned.normalized_state

        if not positive_value_exists(ballot_returned.state_code):
            # Can we get state_code from text_for_map_search?
            if positive_value_exists(ballot_returned.text_for_map_search):
                ballot_returned.state_code = extract_state_code_from_address_string(ballot_returned.text_for_map_search)

        if not positive_value_exists(state_code):
            state_code = ballot_returned.state_code

    if not positive_value_exists(text_for_map_search):
        status += "MISSING_TEXT_FOR_MAP_SEARCH "
        success = False

    if not positive_value_exists(CTCL_VOTER_INFO_URL):
        status += 'NO_CTCL_VOTER_INFO_URL_URL '
        success = False

    if not success:
        results = {
            'success': success,
            'status': status,
            'ballot_returned':  ballot_returned,
            'ballot_returned_found':  False,
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

    try:
        api_key = CTCL_API_KEY
        # Get the ballot info at this address
        response = requests.get(
            CTCL_VOTER_INFO_URL,
            headers=HEADERS_FOR_CTCL_API_CALL,
            params={
                "key": api_key,
                "electionId": ctcl_election_uuid,
                "address": text_for_map_search,
            })
        one_ballot_json = json.loads(response.text)
    except Exception as e:
        one_ballot_json = {}
        success = False
        status += 'CTCL_API_END_POINT_CRASH: ' + str(e) + ' '

    try:
        # Use CTCL API call counter to track the number of queries we are doing each day
        api_counter_manager = CTCLApiCounterManager()
        api_counter_manager.create_counter_entry(
            CTCL_API_VOTER_INFO_QUERY_TYPE,
            google_civic_election_id=google_civic_election_id)
    except Exception as e:
        status += 'COULD_NOT_STORE_METRICS_FOR_CTCL_API:' + str(e) + ''

    try:
        update_or_create_rules = {
            'create_candidates': True,
            'create_offices': True,
            'create_measures': True,
            'update_candidates': False,
            'update_offices': False,
            'update_measures': False,
        }
        groom_results = groom_and_store_google_civic_ballot_json_2021(
            one_ballot_json,
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            voter_id=voter_id,
            election_day_text=election_day_text,
            existing_offices_by_election_dict=existing_offices_by_election_dict,
            existing_candidate_objects_dict=existing_candidate_objects_dict,
            existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
            existing_measure_objects_dict=existing_measure_objects_dict,
            new_office_we_vote_ids_list=new_office_we_vote_ids_list,
            new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
            new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
            update_or_create_rules=update_or_create_rules,
            use_ctcl=True,
            )
        status += groom_results['status']
        ballot_item_dict_list = groom_results['ballot_item_dict_list']
        existing_offices_by_election_dict = groom_results['existing_offices_by_election_dict']
        existing_candidate_objects_dict = groom_results['existing_candidate_objects_dict']
        existing_candidate_to_office_links_dict = groom_results['existing_candidate_to_office_links_dict'],
        existing_measure_objects_dict = groom_results['existing_measure_objects_dict']
        new_office_we_vote_ids_list = groom_results['new_office_we_vote_ids_list']
        new_candidate_we_vote_ids_list = groom_results['new_candidate_we_vote_ids_list']
        new_measure_we_vote_ids_list = groom_results['new_measure_we_vote_ids_list']

        # If we successfully save a ballot, create/update a BallotReturned entry
        if ballot_item_dict_list and len(ballot_item_dict_list) > 0:
            ballot_returned_manager = BallotReturnedManager()
            results = ballot_returned_manager.update_or_create_ballot_returned(
                polling_location_we_vote_id='',
                voter_id=voter_id,
                google_civic_election_id=google_civic_election_id,
                text_for_map_search=text_for_map_search,
            )
            status += results['status']
            if results['ballot_returned_found']:
                status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-SUCCESS "
                ballot_returned = results['ballot_returned']
                ballot_returned_found = True
            else:
                ballot_returned_found = False
                status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-BALLOT_RETURNED_FOUND-FALSE "

            from import_export_google_civic.controllers import store_ballot_item_dict_list
            results = store_ballot_item_dict_list(
                ballot_item_dict_list=ballot_item_dict_list,
                google_civic_election_id=google_civic_election_id,
                voter_id=voter_id,
                state_code=state_code
            )
            if not results['success']:
                status += results['status']
        else:
            # We need to mark the BallotReturned entry with a new date_last_updated date,
            #  so we can move on to other ballot returned entries.
            status += "NO_INCOMING_BALLOT_ITEMS_FOUND_CTCL_ONE_VOTER "
    except Exception as e:
        success = False
        status += 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS_API_V4-ERROR-CTCL_ONE_VOTER: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'batch_header_id': batch_header_id,
        'ballot_location_display_name': "",
        'ballot_location_shortcut': "",
        'ballot_returned': ballot_returned,
        'ballot_returned_found': ballot_returned_found,
        # 'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
        'election_day_text': election_day_text,
        'election_description_text': "",
        # 'election_data_retrieved': bool(ballot_items_count),
        'existing_offices_by_election_dict': existing_offices_by_election_dict,
        'existing_candidate_objects_dict': existing_candidate_objects_dict,
        'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
        'existing_measure_objects_dict': existing_measure_objects_dict,
        'google_civic_election_id': google_civic_election_id,
        'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list': new_measure_we_vote_ids_list,
        'original_text_city': '',
        'original_text_state': '',
        'original_text_zip': '',
        'polling_location_retrieved': False,
        'state_code': state_code,
        'success': success,
        'status': status,
        'text_for_map_search': text_for_map_search,
    }
    return results


def retrieve_ctcl_ballot_items_from_polling_location_api(
        google_civic_election_id=0,
        ctcl_election_uuid="",
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
    success = True
    status = ""
    polling_location_found = False
    ballot_items_count = 0
    batch_header_id = 0

    if not positive_value_exists(google_civic_election_id) or not positive_value_exists(ctcl_election_uuid):
        status += "Error: Missing election id or ctcl_election_uuid"
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
        status += "Error: Missing map point we vote id and polling_location_object"
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

    polling_location_manager = PollingLocationManager()
    text_for_map_search = ''
    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
        text_for_map_search = polling_location.get_text_for_map_search()
    elif positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            text_for_map_search = polling_location.get_text_for_map_search()
            polling_location_found = True

    if polling_location_found:
        if not positive_value_exists(text_for_map_search):
            success = False
            status += "MISSING_TEXT_FOR_MAP_SEARCH "
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

        one_ballot_json = ''
        one_ballot_json_found = False
        ballot_returned_manager = BallotReturnedManager()
        try:
            api_key = CTCL_API_KEY
            # Get the ballot info at this address
            response = requests.get(
                CTCL_VOTER_INFO_URL,
                headers=HEADERS_FOR_CTCL_API_CALL,
                params={
                    "key": api_key,
                    "electionId": ctcl_election_uuid,
                    "address": text_for_map_search,
                })
            if positive_value_exists(response.url):
                status += str(response.url) + ' '
            if len(response.text) >= 2:
                one_ballot_json = json.loads(response.text)
                one_ballot_json_found = True
            else:
                status += "NO_RESULT_FOR: " + str(text_for_map_search) + " "
        except Exception as e:
            success = False
            status += 'CTCL_API_END_POINT_CRASH: ' + str(e) + ' '
            log_entry_message = status
            results = polling_location_manager.create_polling_location_log_entry(
                batch_process_id=batch_process_id,
                google_civic_election_id=google_civic_election_id,
                is_from_ctcl=True,
                kind_of_log_entry=KIND_OF_LOG_ENTRY_API_END_POINT_CRASH,
                log_entry_message=log_entry_message,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                text_for_map_search=text_for_map_search,
            )
            status += results['status']
            results = polling_location_manager.update_polling_location_with_log_counts(
                is_from_ctcl=True,
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
            # Use CTCL API call counter to track the number of queries we are doing each day
            api_counter_manager = CTCLApiCounterManager()
            api_counter_manager.create_counter_entry(
                CTCL_API_VOTER_INFO_QUERY_TYPE,
                google_civic_election_id=google_civic_election_id)
        except Exception as e:
            status += 'CTCL_API_COUNTER_CRASH: ' + str(e) + ' '

        if one_ballot_json_found:
            try:
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
                    use_ctcl=True,
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
                    ballot_items_count = len(ballot_item_dict_list)
                    ballot_returned_manager = BallotReturnedManager()
                    results = polling_location.get_text_for_map_search_results()
                    text_for_map_search = results['text_for_map_search']
                    try:
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
                            status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-SUCCESS "
                            # ballot_returned = results['ballot_returned']
                            # ballot_returned_found = True
                        else:
                            status += "UPDATE_OR_CREATE_BALLOT_RETURNED1-BALLOT_RETURNED_FOUND-FALSE "
                        try:
                            results = store_ctcl_json_response_to_import_batch_system(
                                modified_json_list=ballot_item_dict_list,
                                google_civic_election_id=google_civic_election_id,
                                kind_of_batch='IMPORT_BALLOT_ITEM',
                                batch_set_id=batch_set_id,
                                state_code=state_code)
                            status += results['status']
                            batch_header_id = results['batch_header_id']
                        except Exception as e:
                            status += "CRASH_IN_STORE_CTCL_JSON_RESPONSE: " + str(e) + ' '
                    except Exception as e:
                        status += "CRASH_IN_UPDATE_OR_CREATE_BALLOT_RETURNED: " + str(e) + ' '
                    # Store that we have reviewed this polling_location so we don't retrieve it again in the next chunk
                    results = polling_location_manager.create_polling_location_log_entry(
                        batch_process_id=batch_process_id,
                        google_civic_election_id=google_civic_election_id,
                        is_from_ctcl=True,
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
                    # Create BallotReturnedEmpty entry, so we don't keep retrieving this map point
                    status += "NO_INCOMING_BALLOT_ITEMS_CTCL_CREATE_EMPTY: " \
                              "" + str(polling_location_we_vote_id) + ' '
                    results = ballot_returned_manager.create_ballot_returned_empty(
                        google_civic_election_id=google_civic_election_id,
                        is_from_ctcl=True,
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
                                    status += "PROBLEM_PARSING_ERROR_CTCL: " + str(e) + ' '
                    except Exception as e:
                        status += "PROBLEM_GETTING_ERRORS_CTCL: " + str(e) + " "
                        log_entry_message += status
                    results = polling_location_manager.create_polling_location_log_entry(
                        batch_process_id=batch_process_id,
                        google_civic_election_id=google_civic_election_id,
                        is_from_ctcl=True,
                        kind_of_log_entry=kind_of_log_entry,
                        log_entry_message=log_entry_message,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        state_code=state_code,
                        text_for_map_search=text_for_map_search,
                    )
                    status += results['status']
                    if kind_of_log_entry == KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR:
                        results = polling_location_manager.update_polling_location_with_log_counts(
                            is_from_ctcl=True,
                            polling_location_we_vote_id=polling_location_we_vote_id,
                            update_error_counts=True,
                        )
                        status += results['status']
                    else:
                        results = polling_location_manager.update_polling_location_with_log_counts(
                            polling_location_we_vote_id=polling_location_we_vote_id,
                            update_data_counts=True,
                            is_no_contests=True,
                        )
                        status += results['status']
            except Exception as e:
                success = False
                status += 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS_API_V4-ERROR-CTCL_POLLING_LOCATION: ' + str(e) + ' '
                handle_exception(e, logger=logger, exception_message=status)
        else:
            status += "BALLOT_JSON_NOT_RETURNED_FROM_CTCL "
            results = ballot_returned_manager.create_ballot_returned_empty(
                google_civic_election_id=google_civic_election_id,
                is_from_ctcl=True,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
            )
            if not results['success']:
                status += results['status']
            log_entry_message = status
            results = polling_location_manager.create_polling_location_log_entry(
                batch_process_id=batch_process_id,
                google_civic_election_id=google_civic_election_id,
                is_from_ctcl=True,
                kind_of_log_entry=KIND_OF_LOG_ENTRY_NO_BALLOT_JSON,
                log_entry_message=log_entry_message,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                text_for_map_search=text_for_map_search,
            )
            status += results['status']
            results = polling_location_manager.update_polling_location_with_log_counts(
                is_from_ctcl=True,
                polling_location_we_vote_id=polling_location_we_vote_id,
                update_error_counts=True,
            )
            status += results['status']
    else:
        status += "POLLING_LOCATION_NOT_FOUND (" + str(polling_location_we_vote_id) + ") "
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


def retrieve_from_ctcl_api_election_query():
    status = "Loading json data from CTCL servers, API call electionQuery. "
    logger.info(status)
    print(status)

    if not positive_value_exists(CTCL_ELECTION_QUERY_URL):
        results = {
            'success':  False,
            'status':   'CTCL_ELECTION_QUERY_URL missing ',
        }
        return results

    if not positive_value_exists(CTCL_API_KEY):
        results = {
            'success':  False,
            'status':   'CTCL_API_KEY missing ',
        }
        return results

    response = requests.get(
        CTCL_ELECTION_QUERY_URL,
        headers=HEADERS_FOR_CTCL_API_CALL,
        params={
            "key": CTCL_API_KEY,
        })

    # Use API call counter to track the number of queries we are doing each day
    api_counter_manager = CTCLApiCounterManager()
    api_counter_manager.create_counter_entry('election')

    structured_json = json.loads(response.text)
    if 'success' in structured_json and structured_json['success'] is False:
        status_message = "CTCL_ELECTION_QUERY_URL: " + str(CTCL_ELECTION_QUERY_URL) + \
                         ", CTCL_API_KEY:" + str(CTCL_API_KEY) + " "
        logger.error(status_message)
        status += status_message
        status += structured_json['status']
        results = {
            'status': status,
            'structured_json':  structured_json,
            'success': False,
        }
    else:
        try:
            status += "CTCL_ELECTION_QUERY_RESPONSE: " + str(response.text) + " "
            status += "RESPONSE.URL: " + response.url + " "
        except Exception as e:
            status += "CTCL_ELECTION_QUERY_ERROR_RESPONSE_TEXT_MISSING: " + str(e) + " "
        results = {
            'status':           status,
            'structured_json':  structured_json,
            'success':          True,
        }
    return results


def store_results_from_ctcl_api_election_query(structured_json):
    from election.models import ElectionManager
    election_manager = ElectionManager()
    status = ''
    success = True
    if 'elections' in structured_json:
        elections_list_json = structured_json['elections']
    else:
        elections_list_json = {}
    for one_election_dict in elections_list_json:
        # If there is an existing election, leave it as-is
        one_result = election_manager.retrieve_election(
            ctcl_uuid=one_election_dict['id'], read_only=True)
        if one_result['election_found']:
            status += "ALREADY_EXISTS: " + str(one_election_dict['electionDay']) + " :: " \
                      + str(one_election_dict['id']) + " "
            continue

        election_is_in_future = False
        # We only want to store results for future elections. Analyze to see if this election is in the future.
        if 'electionDay' in one_election_dict:
            election_day_text = one_election_dict['electionDay']
            election_date = convert_we_vote_date_string_to_date(election_day_text)
            datetime_now = datetime.now()
            if election_date > datetime_now:
                election_is_in_future = True
            else:
                status += "NOT_IN_DB_BUT_NOT_IN_FUTURE: " + str(one_election_dict['electionDay']) + " "
                continue

        if election_is_in_future:
            status += "UPDATING_ELECTION: " + str(one_election_dict['electionDay']) + " "
            results = election_manager.update_or_create_election(
                ctcl_uuid=one_election_dict['id'],
                election_day_text=one_election_dict['electionDay'],
                election_name=one_election_dict['name'],
                election_name_do_not_override=True,
                ocd_division_id=one_election_dict['ocdDivisionId'],
                use_ctcl_as_data_source=True)
            status += results['status']
        else:
            status += "NOT_IN_FUTURE2: " + str(one_election_dict['electionDay']) + " "

    results = {
        'status': status,
        'success': success,
    }
    return results
