# measure/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestMeasure, ContestMeasureListManager, ContestMeasureManager, \
    CONTEST_MEASURE_UNIQUE_IDENTIFIERS, CONTEST_MEASURE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED
from ballot.models import MEASURE
from config.environment_variable_functions import get_environment_variable
from django.http import HttpResponse
from election.models import ElectionManager
from ballot.controllers import move_ballot_items_to_another_measure
import json
from position.controllers import move_positions_to_another_measure, update_all_position_details_from_contest_measure
import wevote_functions.admin
from wevote_functions.functions import convert_state_code_to_state_text, MEASURE_TITLE_SYNONYMS, \
    positive_value_exists, process_request_from_master, strip_html_tags
from wevote_functions.functions_date import DATE_FORMAT_YMD_HMS


logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")  # measuresSyncOut


def fetch_duplicate_measure_count(contest_measure, ignore_measure_we_vote_id_list):
    if not hasattr(contest_measure, 'google_civic_election_id'):
        return 0

    if not positive_value_exists(contest_measure.google_civic_election_id):
        return 0

    # Search for other offices within this election that match name and election
    contest_measure_list_manager = ContestMeasureListManager()
    return contest_measure_list_manager.fetch_measures_from_non_unique_identifiers_count(
        contest_measure.google_civic_election_id, contest_measure.state_code,
        contest_measure.office_name, ignore_measure_we_vote_id_list)


def figure_out_measure_conflict_values(contest_measure1, contest_measure2):
    contest_measure_merge_conflict_values = {}

    for attribute in CONTEST_MEASURE_UNIQUE_IDENTIFIERS:
        try:
            contest_measure1_attribute = getattr(contest_measure1, attribute)
            contest_measure2_attribute = getattr(contest_measure2, attribute)
            if contest_measure1_attribute is None and contest_measure2_attribute is None:
                contest_measure_merge_conflict_values[attribute] = 'MATCHING'
            elif contest_measure1_attribute is None or contest_measure1_attribute == "":
                contest_measure_merge_conflict_values[attribute] = 'CONTEST_MEASURE2'
            elif contest_measure2_attribute is None or contest_measure2_attribute == "":
                contest_measure_merge_conflict_values[attribute] = 'CONTEST_MEASURE1'
            else:
                if attribute == "measure_title" or attribute == "state_code":
                    if contest_measure1_attribute.lower() == contest_measure2_attribute.lower():
                        contest_measure_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        contest_measure_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    if contest_measure1_attribute == contest_measure2_attribute:
                        contest_measure_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        contest_measure_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return contest_measure_merge_conflict_values


def filter_measures_structured_json_for_local_duplicates(structured_json):  # Consumes measuresSyncOut
    """
    With this function, we remove measures that seem to be duplicates, but have different we_vote_id's.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    measure_list_manager = ContestMeasureListManager()
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


def find_duplicate_contest_measure(contest_measure, ignore_measure_we_vote_id_list):
    if not hasattr(contest_measure, 'google_civic_election_id'):
        error_results = {
            'success':                                  False,
            'status':                                   "FIND_DUPLICATE_CONTEST_MEASURE_MISSING_OFFICE_OBJECT ",
            'contest_measure_merge_possibility_found':   False,
            'contest_measure_list':                      [],
        }
        return error_results

    if not positive_value_exists(contest_measure.google_civic_election_id):
        error_results = {
            'success':                                False,
            'status':                                 "FIND_DUPLICATE_CONTEST_MEASURE_MISSING_GOOGLE_CIVIC_ELECTION_ID ",
            'contest_measure_merge_possibility_found': False,
            'contest_measure_list':                    [],
        }
        return error_results

    # Search for other contest measures within this election that match name and election
    contest_measure_list_manager = ContestMeasureListManager()
    try:
        google_civic_election_id_list = [contest_measure.google_civic_election_id]
        results = contest_measure_list_manager.retrieve_contest_measures_from_non_unique_identifiers(
            google_civic_election_id_list, contest_measure.state_code, contest_measure.measure_title,
            contest_measure.district_id, contest_measure.district_name, ignore_measure_we_vote_id_list)

        if results['contest_measure_found']:
            contest_measure_merge_conflict_values = \
                figure_out_measure_conflict_values(contest_measure, results['contest_measure'])

            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_MEASURE_DUPLICATES_FOUND",
                'contest_measure_merge_possibility_found':   True,
                'contest_measure_merge_possibility':         results['contest_measure'],
                'contest_measure_merge_conflict_values':     contest_measure_merge_conflict_values,
                'contest_measure_list':                      results['contest_measure_list'],
            }
            return results
        elif results['contest_measure_list_found']:
            # Only deal with merging the incoming contest measure and the first on found
            contest_measure_merge_conflict_values = \
                figure_out_measure_conflict_values(contest_measure, results['contest_measure_list'][0])

            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_MEASURE_DUPLICATES_FOUND",
                'contest_measure_merge_possibility_found':   True,
                'contest_measure_merge_possibility':         results['contest_measure_list'][0],
                'contest_measure_merge_conflict_values':     contest_measure_merge_conflict_values,
                'contest_measure_list':                      results['contest_measure_list'],
            }
            return results
        else:
            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_MEASURE_NO_DUPLICATES_FOUND",
                'contest_measure_merge_possibility_found':   False,
                'contest_measure_list':                      results['contest_measure_list'],
            }
            return results

    except ContestMeasure.DoesNotExist:
        pass
    except Exception as e:
        pass

    results = {
        'success':                                  True,
        'status':                                   "FIND_DUPLICATE_CONTEST_MEASURE_NO_DUPLICATES_FOUND",
        'contest_measure_merge_possibility_found':   False,
    }
    return results


def measure_retrieve_for_api(measure_id, measure_we_vote_id):  # measureRetrieve
    """
    Used by the api
    :param measure_id:
    :param measure_we_vote_id:
    :return:
    """
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
        date_last_updated = ''
        if positive_value_exists(contest_measure.date_last_updated):
            date_last_updated = contest_measure.date_last_updated.strftime(DATE_FORMAT_YMD_HMS)  # '%Y-%m-%d %H:%M:%S'
        json_data = {
            'status':                   status,
            'success':                  True,
            'ballot_item_display_name': contest_measure.measure_title,
            'ballotpedia_measure_url':  contest_measure.ballotpedia_measure_url,
            'district_name':            contest_measure.district_name,
            'election_display_name':    election_display_name,
            'google_civic_election_id': contest_measure.google_civic_election_id,
            'id':                       contest_measure.id,
            'kind_of_ballot_item':      MEASURE,
            'last_updated':             date_last_updated,
            'maplight_id':              contest_measure.maplight_id,
            'measure_subtitle':         contest_measure.measure_subtitle,
            'measure_text':             contest_measure.measure_text,
            'measure_url':              contest_measure.measure_url
            if contest_measure.measure_url else contest_measure.ballotpedia_measure_url,
            'no_vote_description':      strip_html_tags(contest_measure.ballotpedia_no_vote_description),
            'ocd_division_id':          contest_measure.ocd_division_id,
            'referendum_con':           contest_measure.referendum_con,
            'referendum_pro':           contest_measure.referendum_pro,
            'regional_display_name':    "",
            'state_code':               contest_measure.state_code,
            'state_display_name':       convert_state_code_to_state_text(contest_measure.state_code),
            'vote_smart_id':            contest_measure.vote_smart_id,
            'we_vote_id':               contest_measure.we_vote_id,
            'yes_vote_description':     strip_html_tags(contest_measure.ballotpedia_yes_vote_description),
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


def measures_import_from_master_server(request, google_civic_election_id, state_code=''):  # Consumes measuresSyncOut
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Measures from We Vote Master servers",
        MEASURES_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
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


def measures_import_from_structured_json(structured_json):  # Consumes measuresSyncOut
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
        vote_usa_measure_id = one_measure['vote_usa_measure_id'] if 'vote_usa_measure_id' in one_measure else ''
        we_vote_id = one_measure['we_vote_id'] if 'we_vote_id' in one_measure else ''
        google_civic_election_id = \
            one_measure['google_civic_election_id'] if 'google_civic_election_id' in one_measure else 0
        # google_civic_election_id = convert_to_int(google_civic_election_id)

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
                'ballotpedia_district_id': one_measure['ballotpedia_district_id'] if 'ballotpedia_district_id' in
                                                                                     one_measure else '',
                'ballotpedia_election_id': one_measure['ballotpedia_election_id'] if 'ballotpedia_election_id' in
                                                                                     one_measure else '',
                'ballotpedia_measure_id': one_measure['ballotpedia_measure_id'] if 'ballotpedia_measure_id' in
                                                                                   one_measure else '',
                'ballotpedia_measure_name': one_measure['ballotpedia_measure_name'] if 'ballotpedia_measure_name' in
                                                                                       one_measure else '',
                'ballotpedia_measure_status': one_measure['ballotpedia_measure_status']
                if 'ballotpedia_measure_status' in one_measure else '',
                'ballotpedia_measure_summary': one_measure['ballotpedia_measure_summary']
                if 'ballotpedia_measure_summary' in one_measure else '',
                'ballotpedia_measure_text': one_measure['ballotpedia_measure_text'] if 'ballotpedia_measure_text' in
                                                                                       one_measure else '',
                'ballotpedia_measure_url': one_measure['ballotpedia_measure_url']
                if 'ballotpedia_measure_url' in one_measure else '',
                'ballotpedia_no_vote_description': one_measure['ballotpedia_no_vote_description']
                if 'ballotpedia_no_vote_description' in one_measure else '',
                'ballotpedia_page_title': one_measure['ballotpedia_page_title'] if 'ballotpedia_page_title' in
                                                                                   one_measure else '',
                'ballotpedia_photo_url': one_measure['ballotpedia_photo_url'] if 'ballotpedia_photo_url' in
                                                                                 one_measure else '',
                'ballotpedia_yes_vote_description': one_measure['ballotpedia_yes_vote_description']
                if 'ballotpedia_yes_vote_description' in one_measure else '',
                'ctcl_uuid': one_measure['ctcl_uuid'] if 'ctcl_uuid' in one_measure else '',
                'district_id': district_id,
                'district_name': district_name,
                'district_scope': one_measure['district_scope'] if 'district_scope' in one_measure else '',
                'election_day_text': one_measure['election_day_text'] if 'election_day_text' in one_measure else '',
                'google_ballot_placement': one_measure['google_ballot_placement'] if 'google_ballot_placement' in
                                                                                     one_measure else '',
                'google_civic_election_id': google_civic_election_id,
                'google_civic_measure_title':
                    one_measure['google_civic_measure_title'] if 'google_civic_measure_title' in one_measure else '',
                'google_civic_measure_title2':
                    one_measure['google_civic_measure_title2'] if 'google_civic_measure_title2' in one_measure else '',
                'google_civic_measure_title3':
                    one_measure['google_civic_measure_title3'] if 'google_civic_measure_title3' in one_measure else '',
                'google_civic_measure_title4':
                    one_measure['google_civic_measure_title4'] if 'google_civic_measure_title4' in one_measure else '',
                'google_civic_measure_title5':
                    one_measure['google_civic_measure_title5'] if 'google_civic_measure_title5' in one_measure else '',
                'maplight_id': one_measure['maplight_id'] if 'maplight_id' in one_measure else None,
                'vote_smart_id': one_measure['vote_smart_id'] if 'vote_smart_id' in one_measure else None,
                'measure_subtitle': one_measure['measure_subtitle'] if 'measure_subtitle' in one_measure else '',
                'measure_text': one_measure['measure_text'] if 'measure_text' in one_measure else '',
                'measure_title': measure_title,
                'measure_url': one_measure['measure_url'] if 'measure_url' in one_measure else '',
                'measure_year': one_measure['measure_year'] if 'measure_year' in one_measure else '',
                'ocd_division_id': one_measure['ocd_division_id'] if 'ocd_division_id' in one_measure else '',
                'primary_party': one_measure['primary_party'] if 'primary_party' in one_measure else '',
                'referendum_con': one_measure['referendum_con'] if 'referendum_con' in one_measure else '',
                'referendum_pro': one_measure['referendum_pro'] if 'referendum_pro' in one_measure else '',
                'state_code': state_code,
                'vote_usa_measure_id':
                    one_measure['vote_usa_measure_id'] if 'vote_usa_measure_id' in one_measure else '',
                'we_vote_id': we_vote_id,
                'wikipedia_page_id': one_measure['wikipedia_page_id'] if 'wikipedia_page_id' in one_measure else '',
                'wikipedia_page_title': one_measure['wikipedia_page_title'] if 'wikipedia_page_title' in
                                                                               one_measure else '',
                'wikipedia_photo_url': one_measure['wikipedia_photo_url'] if 'wikipedia_photo_url' in
                                                                             one_measure else '',
            }

            results = contest_measure_manager.update_or_create_contest_measure(
                we_vote_id=we_vote_id,
                google_civic_election_id=google_civic_election_id,
                measure_title=measure_title,
                district_id=district_id,
                district_name=district_name,
                state_code=state_code,
                updated_contest_measure_values=updated_contest_measure_values)
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


def retrieve_measure_list_for_all_upcoming_elections(
        google_civic_election_id_list=[],
        limit_to_this_state_code="",
        return_list_of_objects=False):

    status = ""
    success = True
    measure_list_objects = []
    measure_list_light = []
    measure_list_found = False

    if not google_civic_election_id_list \
            or not positive_value_exists(len(google_civic_election_id_list)):
        election_manager = ElectionManager()
        election_list_results = \
            election_manager.retrieve_upcoming_google_civic_election_id_list(limit_to_this_state_code)
        google_civic_election_id_list = election_list_results['upcoming_google_civic_election_id_list']
        status += election_list_results['status']

    if len(google_civic_election_id_list):
        measure_list_manager = ContestMeasureListManager()
        results = measure_list_manager.retrieve_measures_for_specific_elections(
            google_civic_election_id_list,
            limit_to_this_state_code=limit_to_this_state_code,
            return_list_of_objects=return_list_of_objects)
        if results['measure_list_found']:
            measure_list_found = True
            measure_list_light = results['measure_list_light']
        else:
            status += results['status']
            success = results['success']

    results = {
        'success': success,
        'status': status,
        'measure_list_found':               measure_list_found,
        'measure_list_objects':             measure_list_objects if return_list_of_objects else [],
        'measure_list_light':               measure_list_light,
        'return_list_of_objects':           return_list_of_objects,
        'google_civic_election_id_list':    google_civic_election_id_list,
    }
    return results


def add_measure_name_alternatives_to_measure_list_light(measure_list_light):
    """
    In our database, measure names are like "Measure FF: East Bay Regional Park District Parcel Tax Renewal", but
    on endorsement pages, they are listed like "Measure FF". This function takes long names, and adds a list of
    alternate names
    :param measure_list_light:
    :return:
    """
    success = True
    status = ""
    measure_list_light_modified = []

    class BreakException(Exception):  # Also called LocalBreak elsewhere
        pass

    break_exception = BreakException()  # Also called LocalBreak elsewhere

    # Look in measure_list_light and try to find variants on proposition names
    for one_measure_light in measure_list_light:
        # Add alternate names to the 'alternate_names' value
        full_ballot_item_display_name = one_measure_light['ballot_item_display_name'].lower()
        one_measure_light['alternate_names'] = []
        try:
            for one_synonym_list in MEASURE_TITLE_SYNONYMS:
                for one_synonym in one_synonym_list:
                    if one_synonym in full_ballot_item_display_name:
                        # If any synonym in this one_synonym_list is found within full_ballot_item_display_name,
                        #  then use the entire synonym list for matching in other areas of the code
                        one_measure_light['alternate_names'] = one_synonym_list
                        raise break_exception
        except BreakException:
            pass

        measure_list_light_modified.append(one_measure_light)

    results = {
        'success':              success,
        'status':               status,
        'measure_list_light':   measure_list_light_modified,
    }
    return results

def merge_if_duplicate_measures(measure1, measure2, conflict_values):
    """
    See also figure_out_measure_conflict_values
    :param measure1:
    :param measure2:
    :param conflict_values:
    :return:
    """
    success = True
    status = "MERGE_IF_DUPLICATE_MEASURES"
    measures_merged = False
    decisions_required = False
    measure1_we_vote_id = measure1.we_vote_id
    measure2_we_vote_id = measure2.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    clear_these_attributes_from_measure2 = []
    for attribute in CONTEST_MEASURE_UNIQUE_IDENTIFIERS:
        if attribute == "ballotpedia_id" or attribute == "maplight_id" or attribute == "vote_smart_id":
            if positive_value_exists(getattr(measure1, attribute)):
                # We can proceed because measure1 has a valid attribute, so we can default to choosing that one
                if attribute in CONTEST_MEASURE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_measure2.append(attribute)
            elif positive_value_exists(getattr(measure2, attribute)):
                # If we are here, measure1 does NOT have a valid attribute, but measure2 does
                merge_choices[attribute] = getattr(measure2, attribute)
                if attribute in CONTEST_MEASURE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_measure2.append(attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                if attribute == "measure_title":
                    # If the lower case versions of the name attribute are identical, choose the name
                    #  that has upper and lower case letters, and do not require a decision
                    measure1_attribute_value = getattr(measure1, attribute)
                    try:
                        measure1_attribute_value_lower_case = measure1_attribute_value.lower()
                    except Exception:
                        measure1_attribute_value_lower_case = None
                    measure2_attribute_value = getattr(measure2, attribute)
                    try:
                        measure2_attribute_value_lower_case = measure2_attribute_value.lower()
                    except Exception:
                        measure2_attribute_value_lower_case = None
                    if positive_value_exists(measure1_attribute_value_lower_case) \
                            and measure1_attribute_value_lower_case == measure2_attribute_value_lower_case:
                        # Give preference to value with both upper and lower case letters (as opposed to all uppercase)
                        if any(char.isupper() for char in measure1_attribute_value) \
                                and any(char.islower() for char in measure1_attribute_value):
                            merge_choices[attribute] = getattr(measure1, attribute)
                        else:
                            merge_choices[attribute] = getattr(measure2, attribute)
                    else:
                        decisions_required = True
                        break
                else:
                    decisions_required = True
                    break
            elif conflict_value == "CONTEST_MEASURE2":
                merge_choices[attribute] = getattr(measure2, attribute)
                if attribute in CONTEST_MEASURE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_measure2.append(attribute)

    if not decisions_required:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = merge_these_two_measures(
            measure1_we_vote_id,
            measure2_we_vote_id,
            merge_choices,
            clear_these_attributes_from_measure2
        )

        if not merge_results['success']:
            success = False
            status += merge_results['status']
        elif merge_results['measures_merged']:
            measures_merged = True
        else:
            status += "NOT_MERGED "

    results = {
        'success':              success,
        'status':               status,
        'measures_merged':      measures_merged,
        'decisions_required':   decisions_required,
        'measure':              measure1,
    }
    return results


def merge_these_two_measures(
        measure1_we_vote_id,
        measure2_we_vote_id,
        admin_merge_choices={},
        clear_these_attributes_from_measure2=[]):
    """
    Process the merging of two measures
    :param measure1_we_vote_id:
    :param measure2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :param clear_these_attributes_from_measure2:
    :return:
    """
    status = ""
    measure_manager = ContestMeasureManager()

    # Measure 1 is the one we keep, and Measure 2 is the one we will merge into Measure 1
    measure1_results = measure_manager.retrieve_contest_measure(measure_we_vote_id=measure1_we_vote_id)
    if measure1_results['contest_measure_found']:
        measure1 = measure1_results['contest_measure']
        contest_measure1_id = measure1.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_MEASURES-COULD_NOT_RETRIEVE_MEASURE1 ",
            'measures_merged': False,
            'measure': None,
        }
        return results

    measure2_results = measure_manager.retrieve_contest_measure(measure_we_vote_id=measure2_we_vote_id)
    if measure2_results['contest_measure_found']:
        measure2 = measure2_results['contest_measure']
        contest_measure2_id = measure2.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_MEASURES-COULD_NOT_RETRIEVE_MEASURE2 ",
            'measures_merged': False,
            'measure': None,
        }
        return results

    # Merge attribute values chosen by the admin
    for attribute in CONTEST_MEASURE_UNIQUE_IDENTIFIERS:
        try:
            if attribute in admin_merge_choices:
                setattr(measure1, attribute, admin_merge_choices[attribute])
        except Exception as e:
            # Don't completely fail if in attribute can't be saved.
            status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "
    
    # Preserve unique google_civic_measure_title, _title2, _title3, _title4 and _title5
    if positive_value_exists(measure2.google_civic_measure_title):
        measure1 = add_contest_measure_title_to_next_spot(
            measure1, measure2.google_civic_measure_title)
    if positive_value_exists(measure2.google_civic_measure_title2):
        measure1 = add_contest_measure_title_to_next_spot(
            measure1, measure2.google_civic_measure_title2)
    if positive_value_exists(measure2.google_civic_measure_title3):
        measure1 = add_contest_measure_title_to_next_spot(
            measure1, measure2.google_civic_measure_title3)
    if positive_value_exists(measure2.google_civic_measure_title4):
        measure1 = add_contest_measure_title_to_next_spot(
            measure1, measure2.google_civic_measure_title4)
    if positive_value_exists(measure2.google_civic_measure_title5):
        measure1 = add_contest_measure_title_to_next_spot(
            measure1, measure2.google_civic_measure_title5)

     # Merge ballot item's measure details
    ballot_items_results = move_ballot_items_to_another_measure(contest_measure2_id, measure2_we_vote_id,
                                                                contest_measure1_id, measure1_we_vote_id,
                                                                measure1)
    if not ballot_items_results['success']:
        status += ballot_items_results['status']
        status += "COULD_NOT_MOVE_BALLOT_ITEMS_TO_MEASURE1 "
        results = {
            'success': False,
            'status': status,
            'measures_merged': False,
            'measure': None,
        }
        return results

    # Merge public positions
    public_positions_results = move_positions_to_another_measure(contest_measure2_id, measure2_we_vote_id,
                                                                 contest_measure1_id, measure1_we_vote_id,
                                                                 True)
    if not public_positions_results['success']:
        status += public_positions_results['status']
        status += "COULD_NOT_MOVE_PUBLIC_POSITIONS_TO_MEASURE1 "
        results = {
            'success': False,
            'status': status,
            'measures_merged': False,
            'measure': None,
        }
        return results


    # Merge friends-only positions
    friends_positions_results = move_positions_to_another_measure(contest_measure2_id, measure2_we_vote_id,
                                                                  contest_measure1_id, measure1_we_vote_id,
                                                                  False)
    if not friends_positions_results['success']:
        status += friends_positions_results['status']
        status += "COULD_NOT_MOVE_FRIENDS_POSITIONS_TO_MEASURE1 "
        results = {
            'success': False,
            'status': status,
            'measures_merged': False,
            'measure': None,
        }
        return results

    # Clear 'unique=True' fields in measure2, which need to be Null before measure1 can be saved
    #  with updated values
    measure2_updated = False
    for attribute in clear_these_attributes_from_measure2:
        setattr(measure2, attribute, None)
        measure2_updated = True
    if measure2_updated:
        measure2.save()

    # Note: wait to wrap in try/except block
    measure1.save()
    # 2021-10-16 Uses image data from master table which we aren't updating with the merge yet
    # refresh_measure_data_from_master_tables(measure1.we_vote_id)

    # Remove measure 2
    measure2.delete()

    results = {
        'success': True,
        'status': status,
        'measures_merged': True,
        'measure': measure1,
    }
    return results

def add_contest_measure_title_to_next_spot(contest_measure_to_update, google_civic_measure_title_to_add):
    if not positive_value_exists(google_civic_measure_title_to_add):
        return contest_measure_to_update

    if not positive_value_exists(contest_measure_to_update.google_civic_measure_title):
        contest_measure_to_update.google_civic_measure_title = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title2):
        contest_measure_to_update.google_civic_measure_title2 = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title2:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title3):
        contest_measure_to_update.google_civic_measure_title3 = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title3:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title4):
        contest_measure_to_update.google_civic_measure_title4 = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title4:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title5):
        contest_measure_to_update.google_civic_measure_title5 = google_civic_measure_title_to_add
    return contest_measure_to_update