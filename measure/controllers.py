# measure/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestMeasureList, ContestMeasureManager
from ballot.models import MEASURE
from config.base import get_environment_variable
from django.http import HttpResponse
from election.models import ElectionManager
import json
from position.controllers import update_all_position_details_from_contest_measure
import wevote_functions.admin
from wevote_functions.functions import convert_state_code_to_state_text, convert_to_int, positive_value_exists, \
    process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")  # measuresSyncOut


def measure_retrieve_for_api(measure_id, measure_we_vote_id):  # measureRetrieve
    """
    Used by the api
    :param measure_id:
    :param measure_we_vote_id:
    :return:
    """
    # NOTE: Office retrieve is independent of *who* wants to see the data. Office retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItemsFromGoogleCivic does

    if not positive_value_exists(measure_id) and not positive_value_exists(measure_we_vote_id):
        status = 'VALID_MEASURE_ID_AND_MEASURE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      MEASURE,
            'id':                       measure_id,
            'we_vote_id':               measure_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    measure_manager = ContestMeasureManager()
    if positive_value_exists(measure_id):
        results = measure_manager.retrieve_contest_measure_from_id(measure_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(measure_we_vote_id):
        results = measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_MEASURE_ID_AND_MEASURE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      MEASURE,
            'id':                       measure_id,
            'we_vote_id':               measure_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_measure = results['contest_measure']
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_election(contest_measure.google_civic_election_id)
        if election_results['election_found']:
            election = election_results['election']
            election_display_name = election.election_name
        else:
            election_display_name = ""
        json_data = {
            'status':                   status,
            'success':                  True,
            'kind_of_ballot_item':      MEASURE,
            'id':                       contest_measure.id,
            'we_vote_id':               contest_measure.we_vote_id,
            'google_civic_election_id': contest_measure.google_civic_election_id,
            'ballot_item_display_name': contest_measure.measure_title,
            'measure_subtitle':         contest_measure.measure_subtitle,
            'maplight_id':              contest_measure.maplight_id,
            'vote_smart_id':            contest_measure.vote_smart_id,
            'measure_text':             contest_measure.measure_text,
            'measure_url':              contest_measure.measure_url,
            'ocd_division_id':          contest_measure.ocd_division_id,
            'district_name':            contest_measure.district_name,
            'state_code':               contest_measure.state_code,
            'state_display_name':       convert_state_code_to_state_text(contest_measure.state_code),
            'election_display_name':    election_display_name,
            'regional_display_name':    "",
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      MEASURE,
            'id':                       measure_id,
            'we_vote_id':               measure_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def measures_import_from_master_server(request, google_civic_election_id, state_code=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Measures from We Vote Master servers",
        MEASURES_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
            "format": 'json',
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": state_code,
        }
    )

    if import_results['success']:
        results = filter_measures_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        import_results = measures_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed
    else:
        if "MISSING" in import_results['status']:
            import_results['status'] += ", This election may not have any measures."

    return import_results


def filter_measures_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove measures that seem to be duplicates, but have different we_vote_id's.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    measure_list_manager = ContestMeasureList()
    for one_measure in structured_json:
        measure_title = one_measure['measure_title'] if 'measure_title' in one_measure else ''
        we_vote_id = one_measure['we_vote_id'] if 'we_vote_id' in one_measure else ''
        google_civic_election_id = \
            one_measure['google_civic_election_id'] if 'google_civic_election_id' in one_measure else ''
        measure_url = one_measure['measure_url'] if 'measure_url' in one_measure else ''
        maplight_id = one_measure['maplight_id'] if 'maplight_id' in one_measure else ''
        vote_smart_id = one_measure['vote_smart_id'] if 'vote_smart_id' in one_measure else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = measure_list_manager.retrieve_possible_duplicate_measures(
            measure_title, google_civic_election_id, measure_url, maplight_id, vote_smart_id,
            we_vote_id_from_master)

        if results['measure_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_measure)

    candidates_results = {
        'success':              True,
        'status':               "FILTER_MEASURES_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return candidates_results


def measures_import_from_structured_json(structured_json):
    """
    This pathway in requires a we_vote_id, and is not used when we import from Google Civic
    :param structured_json:
    :return:
    """
    contest_measure_manager = ContestMeasureManager()
    measures_saved = 0
    measures_updated = 0
    measures_not_processed = 0
    for one_measure in structured_json:
        we_vote_id = one_measure['we_vote_id'] if 'we_vote_id' in one_measure else ''
        google_civic_election_id = \
            one_measure['google_civic_election_id'] if 'google_civic_election_id' in one_measure else 0
        google_civic_election_id = convert_to_int(google_civic_election_id)

        if positive_value_exists(we_vote_id) and positive_value_exists(google_civic_election_id):
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False

        if proceed_to_update_or_create:
            measure_title = one_measure['measure_title'] if 'measure_title' in one_measure else ''
            district_id = one_measure['district_id'] if 'district_id' in one_measure else 0
            district_name = one_measure['district_name'] if 'district_name' in one_measure else 0
            state_code = one_measure['state_code'] if 'state_code' in one_measure else ''

            updated_contest_measure_values = {
                # Values we search against
                'we_vote_id': we_vote_id,
                'google_civic_election_id': google_civic_election_id,
                # The rest of the values
                'ballotpedia_page_title': one_measure['ballotpedia_page_title'] if 'ballotpedia_page_title' in
                                                                                   one_measure else '',
                'ballotpedia_photo_url': one_measure['ballotpedia_photo_url'] if 'ballotpedia_photo_url' in
                                                                                 one_measure else '',
                'district_id': district_id,
                'district_name': district_name,
                'district_scope': one_measure['district_scope'] if 'district_scope' in one_measure else '',
                'maplight_id': one_measure['maplight_id'] if 'maplight_id' in one_measure else None,
                'vote_smart_id': one_measure['vote_smart_id'] if 'vote_smart_id' in one_measure else None,
                'measure_subtitle': one_measure['measure_subtitle'] if 'measure_subtitle' in one_measure else '',
                'measure_text': one_measure['measure_text'] if 'measure_text' in one_measure else '',
                'measure_url': one_measure['measure_url'] if 'measure_url' in one_measure else '',
                'measure_title': measure_title,
                'google_civic_measure_title':
                    one_measure['google_civic_measure_title'] if 'google_civic_measure_title' in one_measure else '',
                'ocd_division_id': one_measure['ocd_division_id'] if 'ocd_division_id' in one_measure else '',
                'primary_party': one_measure['primary_party'] if 'primary_party' in one_measure else '',
                'state_code': state_code,
                'wikipedia_page_id': one_measure['wikipedia_page_id'] if 'wikipedia_page_id' in one_measure else '',
                'wikipedia_page_title': one_measure['wikipedia_page_title'] if 'wikipedia_page_title' in
                                                                               one_measure else '',
                'wikipedia_photo_url': one_measure['wikipedia_photo_url'] if 'wikipedia_photo_url' in
                                                                             one_measure else '',
            }

            results = contest_measure_manager.update_or_create_contest_measure(
                we_vote_id, google_civic_election_id, measure_title,
                district_id, district_name, state_code, updated_contest_measure_values)
        else:
            measures_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_measure_created']:
                measures_saved += 1
            else:
                measures_updated += 1
        else:
            measures_not_processed += 1
    measures_results = {
        'success': True,
        'status': "MEASURES_IMPORT_PROCESS_COMPLETE",
        'saved': measures_saved,
        'updated': measures_updated,
        'not_processed': measures_not_processed,
    }
    return measures_results


def push_contest_measure_data_to_other_table_caches(contest_measure_id=0, contest_measure_we_vote_id=''):
    contest_measure_manager = ContestMeasureManager()
    if positive_value_exists(contest_measure_we_vote_id):
        results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(contest_measure_we_vote_id)
    elif positive_value_exists(contest_measure_id):
        results = contest_measure_manager.retrieve_contest_measure_from_id(contest_measure_id)

    if results['contest_measure_found']:
        contest_measure = results['contest_measure']
        save_position_from_measure_results = update_all_position_details_from_contest_measure(contest_measure)
        return save_position_from_measure_results
    else:
        results = {
            'success':                      False,
            'positions_updated_count':      0,
            'positions_not_updated_count':  0,
            'update_all_position_results':  []
        }
        return results
