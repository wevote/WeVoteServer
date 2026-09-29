import json
import requests
from django.utils.timezone import localtime, now

from election.models import ElectionManager
from exception.models import handle_exception
from office.models import ContestOffice
from politician.controllers import update_politician_details_from_candidate
from wevote_functions.functions import extract_vote_usa_office_id_with_suffix, positive_value_exists
import wevote_functions.admin

from .models import VoteUSAApiCounterManager
from import_export_vote_usa.controllers import (
    VOTE_USA_API_KEY,
    VOTE_USA_CANDIDATE_QUERY_URL,
    HEADERS_FOR_VOTE_USA_API_CALL,
    VOTE_USA_CANDIDATE_QUERY_TYPE,
)


logger = wevote_functions.admin.get_logger(__name__)


def update_existing_candidates_from_candidates_api(google_civic_election_id=0, state_code=''):
    status = ""
    success = True
    changed_candidate_we_vote_id_list = []
    existing_candidate_objects_dict = {}

    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if not results['election_found']:
        success = False
        status += 'ELECTION_NOT_FOUND '
        results = {'success': success, 'status': status}
        return results
    
    election = results['election']
    election_day = election.election_day_text
    if not positive_value_exists(election_day):
        success = False
        status += 'ELECTION_DAY_MISSING '
        results = {'success': success, 'status': status}
        return results
    election_year_integer = int(election_day[:4])

    if not positive_value_exists(state_code):
        success = False
        status += 'STATE_CODE_MISSING '
        results = {'success': success, 'status': status}
        return results
    
    try:
        api_key = VOTE_USA_API_KEY
        response = requests.get(
            VOTE_USA_CANDIDATE_QUERY_URL,
            headers=HEADERS_FOR_VOTE_USA_API_CALL,
            params={
                "accessKey": api_key,
                "electionDay": election_day,
                "state": state_code,
            },
            timeout=30
        )
        
        try:
            structured_json = json.loads(response.text)
            status += "RESPONSE_FROM_VOTE_USA_RECEIVED "
        except json.JSONDecodeError:
            success = False
            if 'maxJsonLength' in response.text:
                status += 'VOTE_USA_CANDIDATES_API_RESPONSE_TOO_LARGE_FOR_VOTE_USA_SERVER '
            else:
                status += f"VOTE_USA_CANDIDATES_API_INVALID_RESPONSE: {response.text} "
            logger.error(f"VoteUSA API unparsable response: {response.text}")
            results = {'success': success, 'status': status}
            return results

        candidates_structured_json = structured_json.get('candidates', [])
        if positive_value_exists(candidates_structured_json):
            status += "CANDIDATES_FOUND_IN_API_RESPONSE-" + str(len(candidates_structured_json)) + " "
        else:
            status += 'NO_CANDIDATES_FOUND_IN_API_RESPONSE '
            results = {'success': success, 'status': status}
            return results
    except Exception as e:
        success = False
        status += 'VOTE_USA_CANDIDATES_API_END_POINT_CRASH: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)
        results = {'success': success, 'status': status}
        return results
    
    if 'success' in structured_json and structured_json['success'] is False:
        success = False
        status += 'VOTE_USA_CANDIDATES_API_ERROR: ' + structured_json.get('status', '') + ' '
        results = {'success': success, 'status': status}
        return results
    
    try:
        # Use Vote USA API call counter to track the number of queries we are doing each day
        api_counter_manager = VoteUSAApiCounterManager()
        api_counter_manager.create_counter_entry(
            VOTE_USA_CANDIDATE_QUERY_TYPE,
            google_civic_election_id=google_civic_election_id)
        
        vote_usa_candidates_list_by_raw_office_id = {}
        for candidate in candidates_structured_json:
            contests = candidate.get('contests', [])
            if not contests:
                continue
            raw_vote_usa_office_id = contests[0].get('id', '')
            if not raw_vote_usa_office_id:
                continue
            if raw_vote_usa_office_id not in vote_usa_candidates_list_by_raw_office_id:
                vote_usa_candidates_list_by_raw_office_id[raw_vote_usa_office_id] = []
            vote_usa_candidates_list_by_raw_office_id[raw_vote_usa_office_id].append(candidate)
        
        # Raw VoteUSA office IDs include the election ID prefix (e.g. 'CA20221108GA|CAStateHouse51')
        # We extract the base ID and re-append the party suffix for primaries (e.g. 'CAStateHouse51|PD'),
        # or we use base ID as-is for general elections, special elections, and runoffs.
        raw_vote_usa_office_id_to_simple_office_id = {}
        for raw_vote_usa_office_id in vote_usa_candidates_list_by_raw_office_id.keys():
            vote_usa_office_id = extract_vote_usa_office_id_with_suffix(raw_vote_usa_office_id)
            raw_vote_usa_office_id_to_simple_office_id[raw_vote_usa_office_id] = vote_usa_office_id
            
        contest_offices = ContestOffice.objects.filter(
            google_civic_election_id=google_civic_election_id,
            vote_usa_office_id__in=raw_vote_usa_office_id_to_simple_office_id.values()
        )
        
        contest_office_dict = {office.vote_usa_office_id: office for office in contest_offices}

        from import_export_google_civic.controllers import groom_and_store_google_civic_candidates_json_2021
        for raw_vote_usa_office_id, office_candidates in vote_usa_candidates_list_by_raw_office_id.items():
            vote_usa_office_id = extract_vote_usa_office_id_with_suffix(raw_vote_usa_office_id)
            contest_office = contest_office_dict.get(vote_usa_office_id)
            if not contest_office:
                status += 'CONTEST_OFFICE_NOT_FOUND_FOR_VOTE_USA_OFFICE_ID: ' + str(raw_vote_usa_office_id) + \
                    ' (' + str(len(office_candidates)) + ' candidates skipped) '
                continue
            groom_results = groom_and_store_google_civic_candidates_json_2021(
                candidates_structured_json=office_candidates,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                changed_candidate_we_vote_id_list=changed_candidate_we_vote_id_list,
                contest_office_id=contest_office.id,
                contest_office_we_vote_id=contest_office.we_vote_id,
                contest_office_name=contest_office.office_name,
                election_year_integer=election_year_integer,
                existing_candidate_objects_dict=existing_candidate_objects_dict,
                update_or_create_rules={
                    'create_candidates': False,     # don't create new ones
                    'reset_photos_on_update': True, # do full reset of all candidate photos during updates
                    'update_candidates': True,      # do full update on found ones
                },
                use_vote_usa=True,
                vote_usa_office_id=vote_usa_office_id,
            )
            if groom_results['success']:
                status += '::RESULTS_FOR-' + str(vote_usa_office_id) + ' '
                status += groom_results['status']
                changed_candidate_we_vote_id_list = groom_results['changed_candidate_we_vote_id_list']
                existing_candidate_objects_dict = groom_results['existing_candidate_objects_dict']
            else:
                success = False
                status += '||GROOM_CANDIDATES_FAILED_FOR_OFFICE: ' + str(vote_usa_office_id) + ' '
                status += groom_results['status']
        if len(changed_candidate_we_vote_id_list) > 0:
            results = update_politicians_from_candidate_list(existing_candidate_objects_dict, changed_candidate_we_vote_id_list)
            status += results['status']
    except Exception as e:
        success = False
        status += 'UPDATE_EXISTING_CANDIDATES_FROM_CANDIDATES_API_ERROR: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)
        results = {'success': success, 'status': status}
        return results

    return {
        'success': success,
        'status': status,
    }


def update_politicians_from_candidate_list(existing_candidate_objects_dict, changed_candidate_we_vote_id_list, ):
    from politician.models import Politician
    status = ''
    success = True

    # Assemble politician_we_vote_id_list with Politician records we might want to update
    politician_dict_list = {}
    politician_list = []
    politician_we_vote_id_list = []
    for one_candidate in existing_candidate_objects_dict.values():
        if one_candidate.we_vote_id in changed_candidate_we_vote_id_list:
            if positive_value_exists(one_candidate.politician_we_vote_id):
                politician_we_vote_id_list.append(one_candidate.politician_we_vote_id)
    try:
        if len(politician_we_vote_id_list) > 0:
            queryset = Politician.objects.filter(we_vote_id__in=politician_we_vote_id_list)
            politician_list = list(queryset)
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
    except Exception as e:
        status += "UPDATE_FAILED_RETRIEVING_POLITICIANS: " + str(e) + " "
        success = False

    # Update politician records if there was a change
    all_politician_fields_updated = []
    politician_bulk_update_list = []
    politician_update_errors = 0
    politicians_not_updated = 0
    politicians_updated = 0
    for one_candidate in existing_candidate_objects_dict.values():
        if one_candidate.we_vote_id in changed_candidate_we_vote_id_list:
            if one_candidate.politician_we_vote_id in politician_dict_list:
                one_politician = politician_dict_list[one_candidate.politician_we_vote_id]

                results = update_politician_details_from_candidate(politician=one_politician, candidate=one_candidate)
                if results['success']:
                    save_changes = results['save_changes']
                    we_vote_politician = results['politician']
                    if save_changes:
                        fields_updated = results['fields_updated']
                        for field in fields_updated:
                            if field not in all_politician_fields_updated:
                                all_politician_fields_updated.append(field)
                        we_vote_politician.date_last_updated_from_candidate = localtime(now()).date()
                        if 'date_last_updated_from_candidate' not in all_politician_fields_updated:
                            all_politician_fields_updated.append('date_last_updated_from_candidate')
                        # Reset duplicate_check_last_completed so we check for duplicate Politicians again
                        we_vote_politician.duplicate_check_last_completed = None
                        if 'duplicate_check_last_completed' not in all_politician_fields_updated:
                            all_politician_fields_updated.append('duplicate_check_last_completed')
                        politician_bulk_update_list.append(we_vote_politician)

                    # Update the candidate updates_to_politician_completed flag even if politician not updated
                    if save_changes:
                        politicians_updated += 1
                    else:
                        politicians_not_updated += 1
                else:
                    politician_update_errors += 1
                    status += results['status']

    if len(politician_bulk_update_list) > 0:
        try:
            Politician.objects.bulk_update(politician_bulk_update_list, all_politician_fields_updated)
            status += \
                "[[Politicians updated: {politicians_updated:,}. " \
                "Politicians not updated: {politicians_not_updated:,}. " \
                "Politician update errors: {politician_update_errors:,}.]] " \
                "".format(
                    politician_update_errors=politician_update_errors,
                    politicians_updated=politicians_updated,
                    politicians_not_updated=politicians_not_updated)
        except Exception as e:
            status += "FAILED_BULK_UPDATE_OF_POLITICIANS: " + str(e) + " "
            success = False

    return {
        'success': success,
        'status': status,
    }
