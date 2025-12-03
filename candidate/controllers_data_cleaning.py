# candidate/controllers_data_cleaning.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import datetime
import pytz

from django.db.models import Q
from config.base import get_environment_variable
from django.db.models.functions import Length
from django.utils.timezone import localtime, now

from import_export_batches.controllers_data_cleaning import full_deduplication_for_next_state
from politician.models import Politician, PoliticianManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_functions.functions_date import convert_date_to_date_as_integer, \
    convert_we_vote_date_string_to_date_as_integer, \
    generate_localized_datetime_from_obj, get_current_year_as_integer
from .controllers import candidate_politician_match, find_duplicate_candidate, merge_if_duplicate_candidates
from .models import CandidateCampaign, CandidateListManager, CandidateManager, CandidatesArePossibleDuplicates, \
    DeduplicationNeededForStateToday

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def augment_candidate_with_ultimate_election_date(candidate, elections_dict={}):
    """
    Update the values in the candidate object with new "candidate_ultimate_election_date" and "candidate_year"
    but don't save. (Saving happens outside of this function.)
    NOTE: Similar to generate_candidate_position_sorting_dates - perhaps refactor both?
    :param candidate:
    :param elections_dict:
    :return:
    """
    candidate_ultimate_election_date = None
    candidate_year = None
    status = ''
    success = True
    values_changed = False

    if not candidate or not hasattr(candidate, 'candidate_ultimate_election_date'):
        status += "CANDIDATE_MISSING "
        success = False
        return {
            'candidate':        candidate,
            'elections_dict':   elections_dict,
            # 'latest_office_we_vote_id': latest_office_we_vote_id,
            'success':          success,
            'status':           status,
            'values_changed':   values_changed,
        }
    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=[candidate.we_vote_id],
        read_only=True)
    candidate_to_office_link_list = results['candidate_to_office_link_list']
    latest_election_date = 0
    # latest_office_we_vote_id = ''
    for candidate_to_office_link in candidate_to_office_link_list:
        try:
            if candidate_to_office_link.google_civic_election_id in elections_dict:
                this_election = elections_dict[candidate_to_office_link.google_civic_election_id]
            else:
                this_election = candidate_to_office_link.election()
                try:
                    if positive_value_exists(this_election.google_civic_election_id) \
                            and this_election.google_civic_election_id not in elections_dict:
                        elections_dict[this_election.google_civic_election_id] = this_election
                except Exception as e:
                    status += "COULD_NOT_ADD_ELECTION_TO_DICT: " + str(e) + " "
            election_day_as_integer = convert_we_vote_date_string_to_date_as_integer(this_election.election_day_text)
            if election_day_as_integer > latest_election_date:
                candidate_ultimate_election_date = election_day_as_integer
                election_day_as_string = str(election_day_as_integer)
                year = election_day_as_string[:4]
                if year:
                    candidate_year = convert_to_int(year)
                latest_election_date = election_day_as_integer
                # latest_office_we_vote_id = candidate_to_office_link.contest_office_we_vote_id
        except Exception as e:
            status += "PROBLEM_GETTING_ELECTION_INFORMATION: " + str(e) + " "

    # Now that we have cycled through all the candidate_to_office_link_list, augment the candidate
    if positive_value_exists(candidate_ultimate_election_date) \
            and candidate_ultimate_election_date != candidate.candidate_ultimate_election_date:
        candidate.candidate_ultimate_election_date = candidate_ultimate_election_date
        values_changed = True
    if positive_value_exists(candidate_year) \
            and candidate_year != candidate.candidate_year:
        candidate.candidate_year = candidate_year
        values_changed = True
    return {
        'candidate':                candidate,
        'elections_dict':           elections_dict,
        # 'latest_office_we_vote_id': latest_office_we_vote_id,
        'success':                  success,
        'status':                   status,
        'values_changed':           values_changed,
    }


def augment_candidate_with_contest_office_data(candidate, office):
    """
    Update the values in the candidate object with new "contest_office_name" and "district_name"
    but don't save. (Saving happens outside this function.)
    :param candidate:
    :param office:
    :return:
    """
    status = ''
    success = True
    values_changed = False

    error_results = {
        'candidate':        candidate,
        'success':          success,
        'status':           status,
        'values_changed':   values_changed,
    }

    if not candidate or not hasattr(candidate, 'contest_office_name'):
        status += "CANDIDATE_MISSING "
        error_results['status'] = status
        error_results['success'] = False
        return error_results

    if not office or not hasattr(office, 'google_civic_election_id'):
        status += "OFFICE_MISSING "
        error_results['status'] = status
        error_results['success'] = False
        return error_results

    if positive_value_exists(office.office_name) \
            and office.office_name != candidate.contest_office_name:
        candidate.contest_office_name = office.office_name
        values_changed = True
    if positive_value_exists(office.district_name) \
            and office.district_name != candidate.district_name:
        candidate.district_name = office.district_name
        values_changed = True
    if positive_value_exists(office.ballotpedia_race_office_level) \
            and office.ballotpedia_race_office_level != candidate.race_office_level:
        candidate.race_office_level = office.ballotpedia_race_office_level
        values_changed = True
    return {
        'candidate':                candidate,
        'status':                   status,
        'success':                  success,
        'values_changed':           values_changed,
    }


def campaignx_we_vote_id_updates(
        google_civic_election_id_list=None,
        number_to_update=1000,
        state_code=None,
):
    cleaning_candidate_list = []
    current_year = get_current_year_as_integer()
    starting_year = current_year - 1  # Start with prior year
    status = ''
    success = True
    total_to_convert_after = 0

    # After initial updates to all candidates, include in the search logic to find candidates with
    # linked_campaignx_we_vote_id_date_last_updated older than:
    # Politician.linked_campaignx_we_vote_id_date_last_updated

    # Find all candidates in this election
    candidates_to_update_we_vote_id_list = []
    if google_civic_election_id_list and len(google_civic_election_id_list) > 0:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            google_civic_election_id_list=google_civic_election_id_list,
            read_only=True)
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        candidates_to_update_we_vote_id_list = []
        for candidate_to_office_link in candidate_to_office_link_list:
            if candidate_to_office_link.candidate_we_vote_id not in candidates_to_update_we_vote_id_list:
                candidates_to_update_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)

    try:
        queryset = CandidateCampaign.objects.all()
        if candidates_to_update_we_vote_id_list and len(candidates_to_update_we_vote_id_list) > 0:
            queryset = queryset.filter(we_vote_id__in=candidates_to_update_we_vote_id_list)
        elif positive_value_exists(starting_year):
            queryset = queryset.filter(candidate_year__gte=starting_year)
        queryset = queryset.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        queryset = queryset.filter(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        total_to_convert = queryset.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        queryset = queryset.order_by('-id')
        cleaning_candidate_list = list(queryset[:number_to_update])
    except Exception as e:
        status += "COULD_NOT_UPDATE_CANDIDATE_CAMPAIGNX_WE_VOTE_ID: " + str(e) + " "
        success = False

    politician_we_vote_id_list = []
    # Retrieve all relevant politicians in a single query
    for one_candidate in cleaning_candidate_list:
        politician_we_vote_id_list.append(one_candidate.politician_we_vote_id)
    politician_manager = PoliticianManager()
    politician_list = []
    if politician_we_vote_id_list and len(politician_we_vote_id_list) > 0:
        politician_results = politician_manager.retrieve_politician_list(
            politician_we_vote_id_list=politician_we_vote_id_list)
        politician_list = politician_results['politician_list']
    politician_dict_list = {}
    for one_politician in politician_list:
        politician_dict_list[one_politician.we_vote_id] = one_politician

    datetime_now = generate_localized_datetime_from_obj()[1]
    linked_campaignx_we_vote_id_missing = 0
    update_list = []
    updates_needed = False
    updates_made = 0
    candidate_without_linked_campaignx_we_vote_id_status = ""
    for one_candidate in cleaning_candidate_list:
        one_politician = politician_dict_list.get(one_candidate.politician_we_vote_id)
        if one_politician and hasattr(one_politician, 'linked_campaignx_we_vote_id') \
                and positive_value_exists(one_politician.linked_campaignx_we_vote_id):
            one_candidate.linked_campaignx_we_vote_id = one_politician.linked_campaignx_we_vote_id
            one_candidate.linked_campaignx_we_vote_id_date_last_updated = datetime_now
            update_list.append(one_candidate)
            updates_needed = True
            updates_made += 1
        else:
            linked_campaignx_we_vote_id_missing += 1
            if linked_campaignx_we_vote_id_missing < 10:
                candidate_without_linked_campaignx_we_vote_id_status += \
                    one_candidate.display_candidate_name() + \
                    " (" + one_candidate.we_vote_id + "/" + one_candidate.politician_we_vote_id + ") "
    if positive_value_exists(linked_campaignx_we_vote_id_missing):
        status += (
            f"{linked_campaignx_we_vote_id_missing:,} "
            f"politicians attached to candidates missing linked_campaignx_we_vote_id. "
            f"(Add campaigns by visiting Campaigns list.) "
            f"EXAMPLES: {candidate_without_linked_campaignx_we_vote_id_status}"
        )
    if updates_needed:
        try:
            CandidateCampaign.objects.bulk_update(
                update_list, ['linked_campaignx_we_vote_id', 'linked_campaignx_we_vote_id_date_last_updated'])
            status += \
                "{updates_made:,} candidates updated with new linked_campaignx_we_vote_id. " \
                "{total_to_convert_after:,} remaining." \
                "".format(
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += \
                "{updates_made:,} candidates NOT updated with new linked_campaignx_we_vote_id. " \
                "{total_to_convert_after:,} remaining. ERROR: {error}" \
                "".format(
                    error=str(e),
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
    else:
        status += "NO_CAMPAIGNX_WE_VOTE_ID_UPDATES_NEEDED "
    if positive_value_exists(status):
        status = \
            "SCRIPT campaignx_we_vote_id_updates: " + status + " "

    return {
        'status':                   status,
        'success':                  success,
    }


def populate_candidates_ultimate_election_date(
        google_civic_election_id_list=None,
        number_to_populate=1000,
        state_code=None,
):
    candidate_bulk_update_list = []
    candidates_updated = 0
    candidates_not_updated = 0
    cleaning_candidate_list = []
    current_year = get_current_year_as_integer()
    starting_year = current_year - 1  # Start with prior year
    elections_dict = {}
    status = ''
    success = True

    # Find all candidates in this election
    candidates_to_update_we_vote_id_list = []
    if google_civic_election_id_list and len(google_civic_election_id_list) > 0:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            google_civic_election_id_list=google_civic_election_id_list,
            read_only=True)
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        candidates_to_update_we_vote_id_list = []
        for candidate_to_office_link in candidate_to_office_link_list:
            if candidate_to_office_link.candidate_we_vote_id not in candidates_to_update_we_vote_id_list:
                candidates_to_update_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)

    # Now get all candidates we want to update, with a single query
    try:
        queryset = CandidateCampaign.objects.all()
        if candidates_to_update_we_vote_id_list and len(candidates_to_update_we_vote_id_list) > 0:
            queryset = queryset.filter(we_vote_id__in=candidates_to_update_we_vote_id_list)
        elif positive_value_exists(starting_year):
            queryset = queryset.filter(candidate_year__gte=starting_year)
        queryset = queryset.filter(candidate_ultimate_election_date_calculated=False)
        # For now, restrict to those who don't have candidate_ultimate_election_date. In the future, we could remove
        #  this to refresh the candidate_ultimate_election_date data for all candidates.
        queryset = queryset.filter(
            Q(candidate_ultimate_election_date=0) | Q(candidate_ultimate_election_date__isnull=True))
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)

        candidate_ultimate_count = queryset.count()
        if positive_value_exists(candidate_ultimate_count):
            status += \
                "SCRIPT: {entries_to_process:,} entries to process (populate_candidates_ultimate_election_date) " \
                "".format(entries_to_process=candidate_ultimate_count) + " "
        # Now process
        cleaning_candidate_list = queryset[:number_to_populate]
    except Exception as e:
        status += "FAILED_RETRIEVING_CANDIDATES: " + str(e) + " "

    for one_candidate in cleaning_candidate_list:
        results = augment_candidate_with_ultimate_election_date(
            candidate=one_candidate,
            elections_dict=elections_dict)
        if results['success']:
            elections_dict = results['elections_dict']
        if results['values_changed']:
            candidate_to_update = results['candidate']
            candidate_to_update.candidate_ultimate_election_date_calculated = True
            candidate_bulk_update_list.append(candidate_to_update)
            candidates_updated += 1
        else:
            one_candidate.candidate_ultimate_election_date_calculated = True
            candidate_bulk_update_list.append(one_candidate)
            candidates_not_updated += 1
    if candidate_bulk_update_list and len(candidate_bulk_update_list) > 0:
        try:
            CandidateCampaign.objects.bulk_update(
                candidate_bulk_update_list,
                ['candidate_ultimate_election_date',
                 'candidate_ultimate_election_date_calculated',
                 'candidate_year'])
        except Exception as e:
            status += "FAILED_BULK_UPDATE: " + str(e) + " "
    else:
        status += "NO_CANDIDATE_ULTIMATE_ELECTION_DATE_UPDATES_NEEDED "

    if positive_value_exists(candidates_updated):
        status += \
            "candidates_updated: " + str(candidates_updated) + " "
    if positive_value_exists(candidates_not_updated):
        status += \
            "candidates_not_updated: " + str(candidates_not_updated) + " "

    results = {
        'status': status,
        'success': success,
    }
    return results


def populate_contest_office_data(
        google_civic_election_id_list=None,
        number_to_populate=1000,
        show_candidates_with_email=False,
        state_code=None,
):
    candidate_bulk_update_list = []
    cleaning_candidate_list = []
    current_year = get_current_year_as_integer()
    starting_year = current_year - 1  # Start with prior year
    status = ''
    success = True

    # Find all candidates in this election
    candidates_to_update_we_vote_id_list = []
    if google_civic_election_id_list and len(google_civic_election_id_list) > 0:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            google_civic_election_id_list=google_civic_election_id_list,
            read_only=True)
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        candidates_to_update_we_vote_id_list = []
        for candidate_to_office_link in candidate_to_office_link_list:
            if candidate_to_office_link.candidate_we_vote_id not in candidates_to_update_we_vote_id_list:
                candidates_to_update_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)

    try:
        datetime_now = datetime.now()
        date_string = datetime_now.strftime('%Y%m%d')
        date_int = int(date_string)
    except Exception as e:
        date_int = 20240101

    try:
        queryset = CandidateCampaign.objects.all()
        if candidates_to_update_we_vote_id_list and len(candidates_to_update_we_vote_id_list) > 0:
            queryset = queryset.filter(we_vote_id__in=candidates_to_update_we_vote_id_list)
        else:
            queryset = queryset.filter(
                Q(candidate_ultimate_election_date__gt=date_int) |
                Q(candidate_year__gte=starting_year)
            )
        queryset = queryset.filter(contest_office_name_calculated=False)
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        # Restrict to entries with BOTH contest_office_name and district_name empty
        #  OR race_office_level null or empty
        queryset = queryset.filter(
            ((Q(contest_office_name__isnull=True) | Q(contest_office_name='')) &
             (Q(district_name__isnull=True) | Q(district_name=''))) |
            (Q(race_office_level__isnull=True) | Q(race_office_level=''))
        )
        candidate_ultimate_count = queryset.count()
        if positive_value_exists(candidate_ultimate_count):
            status += \
                "SCRIPT: {entries_to_process:,} entries to process (populate_contest_office_data). " \
                "".format(entries_to_process=candidate_ultimate_count) + " "

        # Filter candidates based on whether they have an email address
        if positive_value_exists(show_candidates_with_email):
            queryset = queryset.annotate(candidate_email_length=Length('candidate_email'))
            queryset = queryset.filter(
                Q(candidate_email_length__gt=2)
            )

        # Now process
        cleaning_candidate_list = queryset[:number_to_populate]
    except Exception as e:
        status += "FAILED_RETRIEVING_CANDIDATES_POPULATE_CONTEST_OFFICE: " + str(e) + " "

    candidates_updated = 0
    candidates_not_matched = 0
    candidates_not_updated = 0
    candidate_to_office_link_list = []
    cleaning_candidate_we_vote_id_list = []
    contest_office_by_we_vote_id_dict = {}
    contest_office_list = []
    contest_office_we_vote_id_list = []
    office_by_candidate_we_vote_id_dict = {}
    for candidate in cleaning_candidate_list:
        # Collect candidate_we_vote_id_list, so we can retrieve linked offices first
        if candidate.we_vote_id not in cleaning_candidate_we_vote_id_list:
            cleaning_candidate_we_vote_id_list.append(candidate.we_vote_id)

    # Retrieve all CandidateToOfficeLink objects for these candidates
    if cleaning_candidate_we_vote_id_list and len(cleaning_candidate_we_vote_id_list) > 0:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            candidate_we_vote_id_list=cleaning_candidate_we_vote_id_list,
            read_only=True
        )
        if results['candidate_to_office_link_list_found']:
            candidate_to_office_link_list = results['candidate_to_office_link_list']

    for one_link in candidate_to_office_link_list:
        if positive_value_exists(one_link.contest_office_we_vote_id) \
                and one_link.contest_office_we_vote_id not in contest_office_we_vote_id_list:
            contest_office_we_vote_id_list.append(one_link.contest_office_we_vote_id)

    # Retrieve all the offices for these candidates
    from office.models import ContestOfficeListManager
    contest_office_list_manager = ContestOfficeListManager()
    if contest_office_we_vote_id_list and len(contest_office_we_vote_id_list) > 0:
        results = contest_office_list_manager.retrieve_offices(
            retrieve_from_this_office_we_vote_id_list=contest_office_we_vote_id_list,
            return_list_of_objects=True,
            read_only=True)
        if results['office_list_found']:
            contest_office_list = results['office_list_objects']
            for one_office in contest_office_list:
                if hasattr(one_office, 'district_name'):  # Make sure legit office object
                    contest_office_by_we_vote_id_dict[one_office.we_vote_id] = one_office

    # Take CandidateToOfficeLink entries for each candidate, and figure out the contest_office object
    #  furthest in the future. We will use this to find the district_name and contest_office_name
    for office in contest_office_list:
        for candidate in cleaning_candidate_list:
            for one_link in candidate_to_office_link_list:
                # If the candidate and office match this candidate_to_office_link, proceed
                if candidate.we_vote_id == one_link.candidate_we_vote_id \
                        and office.we_vote_id == one_link.contest_office_we_vote_id:
                    if candidate.we_vote_id in office_by_candidate_we_vote_id_dict:
                        # If this office is further in the future, replace the earlier version
                        try:
                            office_election_date_as_integer = convert_to_int(office.election_date_as_integer)
                        except Exception as e:
                            office_election_date_as_integer = 0
                        try:
                            office_by_candidate_we_vote_id = \
                                office_by_candidate_we_vote_id_dict[candidate.we_vote_id]
                            if hasattr(office_by_candidate_we_vote_id, 'office_name'):
                                office_election_date_from_dict_as_integer = \
                                    office_by_candidate_we_vote_id.election_date_as_integer
                                office_election_date_from_dict_as_integer = \
                                    convert_to_int(office_election_date_from_dict_as_integer)
                            else:
                                office_election_date_from_dict_as_integer = 0
                        except Exception as e:
                            office_election_date_from_dict_as_integer = 0
                        try:
                            if office_election_date_as_integer > office_election_date_from_dict_as_integer:
                                office_by_candidate_we_vote_id_dict[candidate.we_vote_id] = office
                        except Exception as e:
                            pass
                    else:
                        office_by_candidate_we_vote_id_dict[candidate.we_vote_id] = office

    why_candidates_did_not_update = "WHY_CANDIDATES_DID_NOT_UPDATE_EXAMPLES: [["
    for candidate in cleaning_candidate_list:
        if positive_value_exists(candidate.we_vote_id) and \
                candidate.we_vote_id in office_by_candidate_we_vote_id_dict:
            contest_office = office_by_candidate_we_vote_id_dict[candidate.we_vote_id]
            if hasattr(contest_office, 'district_name'):  # Make sure legit office object
                results = augment_candidate_with_contest_office_data(
                    candidate=candidate,
                    office=contest_office)
                if results['values_changed']:
                    candidate_augmented = results['candidate']
                    candidate_augmented.contest_office_name_calculated = True
                    candidate_bulk_update_list.append(candidate_augmented)
                    candidates_updated += 1
                else:
                    candidate.contest_office_name_calculated = True
                    candidate_bulk_update_list.append(candidate)
                    candidates_not_updated += 1
                    if candidates_not_updated < 5:
                        why_candidates_did_not_update += "[" + contest_office.office_name + " (" + \
                                                         contest_office.we_vote_id + ") "
                        why_candidates_did_not_update += "/ " + candidate.candidate_name + " (" + \
                                                         candidate.we_vote_id + ")] "
        else:
            candidate.contest_office_name_calculated = True
            candidate_bulk_update_list.append(candidate)
            candidates_not_matched += 1
            if candidates_not_matched < 5:
                why_candidates_did_not_update += "[ " + candidate.candidate_name + " (" + \
                                                 candidate.we_vote_id + ")] "
    why_candidates_did_not_update += "]] "
    if candidate_bulk_update_list and len(candidate_bulk_update_list) > 0:
        try:
            CandidateCampaign.objects.bulk_update(
                candidate_bulk_update_list, [
                    'contest_office_name', 'contest_office_name_calculated', 'district_name', 'race_office_level',
                ])
        except Exception as e:
            success = False
            status += "FAILED_BULK_UPDATE_POPULATE_CONTEST_OFFICE: " + str(e) + " "
    else:
        status += "POPULATE_CONTEST_OFFICE_DATA_NO_CANDIDATES_UPDATED "

    # If there are some leftover entries which we can't update, we don't want to show a message like this forever:
    #  SCRIPT: 7 entries to process (populate_contest_office_data).
    candidates_updated_or_not_updated = False
    if positive_value_exists(candidates_updated):
        status += "candidates_updated: " + str(candidates_updated) + " "
        candidates_updated_or_not_updated = True
    if positive_value_exists(candidates_not_updated) or positive_value_exists(candidates_not_matched):
        status += \
            "candidates_not_updated: " + str(candidates_not_updated) + " " + \
            "candidates_not_matched: " + str(candidates_not_matched) + " " + \
            why_candidates_did_not_update + " "
        candidates_updated_or_not_updated = True

    results = {
        'candidates_updated_or_not_updated': candidates_updated_or_not_updated,
        'status': status,
        'success': success,
    }
    return results


def batch_process_deduplication_scripts_candidate():  # DEDUPLICATION_SCRIPTS_CANDIDATE
    all_states_deduplication_complete = False
    status = ':||: '
    success = True

    # ##################
    # Every day, we go through all states and run a duplication check so we end up with a list of Candidates
    #  that might be duplicates. Every time this script runs, we check one more state.
    results = full_deduplication_for_next_state(is_for_candidates=True)
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "
        all_states_deduplication_complete = results['all_states_deduplication_complete']

    # ##################
    # After all states have been checked once per day for duplicates, we check to see if there have been any
    #  manual deduplication in any states. If so, run the full_deduplication_for_next_state again for that state
    #  the next time batch_process_deduplication_scripts_candidate is run.
    if all_states_deduplication_complete:
        results = find_states_that_need_new_candidate_deduplication()
        if positive_value_exists(results['success']):
            state_code_list = results['state_code_list']
            if state_code_list and len(state_code_list) > 0:
                # Update the DeduplicationNeededForStateToday entry for today with the
                #  states that need to be deduplicated again.
                try:
                    pacific_tz = pytz.timezone('US/Pacific')
                    date_now = now().astimezone(pacific_tz)
                    date_now_as_integer = convert_date_to_date_as_integer(date_now)
                    deduplication_needed_for_state_today, created = \
                        DeduplicationNeededForStateToday.objects.get_or_create(
                            date_now_as_integer=date_now_as_integer,
                        )
                    # Set the deduplication_needed flag to True for each state in the list
                    for state_code in state_code_list:
                        field_name = f"{state_code.lower()}_deduplication_needed"
                        setattr(deduplication_needed_for_state_today, field_name, True)

                    deduplication_needed_for_state_today.save()
                    status += f"UPDATED_DeduplicationNeededForStateToday for states: {', '.join(state_code_list)} "
                except Exception as e:
                    status += "FAILED_TO_UPDATE_DeduplicationNeededForStateToday: {e} ".format(e=e)
                    success = False
        if positive_value_exists(results['status']):
            status += results['status'] + " :||: "

    results = {
        'status': status,
        'success': success,
    }
    return results


def batch_process_maintenance_scripts_candidate():
    status = ' :||: '
    success = True

    # ##################
    # Update the Candidate's ultimate election date
    results = populate_candidates_ultimate_election_date(
        number_to_populate=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + ":||: "

    # ##################
    # We use contest_office_name and/or district_name some places. Update candidates missing this data.
    results = populate_contest_office_data(
        number_to_populate=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Update candidates who currently don't have seo_friendly_path, if there is seo_friendly_path
    #  in linked politician
    results = seo_friendly_path_updates(
        number_to_update=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Update candidates who currently don't have linked_campaignx_we_vote_id, with value from linked politician
    results = campaignx_we_vote_id_updates(
        number_to_update=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # If there are any candidates who don't have a linked_politician_we_vote_id, match them to an existing politician
    #  or create a new politician if none exists.
    results = candidate_politician_match_batch_process()
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # In the right circumstance, update the candidate record from the newly linked politician record (first time)
    results = update_candidate_from_politician_batch_process()
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # In the right circumstance, update the politician record from the newly imported candidate record
    results = update_politician_from_candidate_batch_process()
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # In the right circumstance, update the candidate record from the newly linked politician record (second time)
    results = update_candidate_from_politician_batch_process(second_pass=True)
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    results = {
        'status': status,
        'success': success,
    }
    return results


def candidate_deduplication_for_one_state(candidate_year=0, state_code=''):
    status = ''
    success = True

    if not positive_value_exists(state_code):
        status += "STATE_CODE_IS_REQUIRED: "
        success = False
        return {
            'status': status,
            'success': success,
        }

    # Delete all existing duplicates
    try:
        from candidate.models import CandidatesArePossibleDuplicates
        queryset = CandidatesArePossibleDuplicates.objects.filter(
            state_code__iexact=state_code,
        )
        number_deleted, unused = queryset.delete()
        status += f"[Deleted {number_deleted:,} PoliticiansArePossibleDuplicates entries for state {state_code}] "
    except Exception as e:
        status += "ERROR_DELETING_POSSIBLE_DUPLICATES: {e} ".format(e=e)
        success = False

    if success:
        merge_results = find_and_merge_duplicate_candidates(
            candidate_year=candidate_year,
            state_code=state_code)
        status += merge_results['status']
        if merge_results['candidates_merged_found']:
            candidates_merged_list = merge_results['candidates_merged_list']
            for candidate in candidates_merged_list:
                status += f"[Candidate {candidate.candidate_name} merged.] "
        if merge_results['duplicate_check_complete_candidate_we_vote_id_list']:
            try:
                we_vote_ids_to_update = merge_results['duplicate_check_complete_candidate_we_vote_id_list']
                CandidateCampaign.objects.filter(we_vote_id__in=we_vote_ids_to_update)\
                    .update(duplicate_check_last_completed=now())
                status += f"DUPLICATE_CHECK_COMPLETE_FOR-{len(we_vote_ids_to_update)}-CANDIDATES "
            except Exception as e:
                status += f"COULD_NOT_UPDATE_DUPLICATE_CHECK_LAST_COMPLETED: {e} "
        if merge_results['reset_duplicate_check_last_completed_we_vote_id_list']:
            try:
                we_vote_ids_to_update = merge_results['reset_duplicate_check_last_completed_we_vote_id_list']
                if len(we_vote_ids_to_update) > 0:
                    CandidateCampaign.objects.filter(we_vote_id__in=we_vote_ids_to_update)\
                        .update(duplicate_check_last_completed=None)
                    status += f"RESET_DUPLICATE_CHECK_FOR-{len(we_vote_ids_to_update)}-CANDIDATES "
            except Exception as e:
                status += f"COULD_NOT_RESET_DUPLICATE_CHECK_LAST_COMPLETED: {e} "

    results = {
        'status': status,
        'success': success,
    }
    return results


def candidate_politician_match_this_year(candidate_year='', state_code='', limit=0):
    num_candidates_reviewed = 0
    num_that_already_have_politician_we_vote_id = 0
    new_politician_created = 0
    existing_politician_found = 0
    multiple_politicians_found = 0
    other_results = 0
    status = ""
    success = True
    error_results = {
        'existing_politician_found': existing_politician_found,
        'multiple_politicians_found': multiple_politicians_found,
        'new_politician_created': new_politician_created,
        'num_that_already_have_politician_we_vote_id': num_that_already_have_politician_we_vote_id,
        'num_candidates_reviewed': num_candidates_reviewed,
        'other_results': other_results,
        'status': status,
        'success': False,
    }

    # We only want to process if a year comes in
    if not positive_value_exists(candidate_year):
        status += "CANDIDATE_YEAR_IS_REQUIRED "
        error_results['status'] = status
        return error_results

    # We only want to process if a state_code comes in
    if not positive_value_exists(state_code):
        status += "STATE_CODE_IS_REQUIRED "
        error_results['status'] = status
        return error_results

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_all_candidates_for_one_year(
        candidate_year=candidate_year,
        has_been_deduplicated=True,
        is_missing_politician_we_vote_id=True,
        limit_to_this_state_code=state_code,
        return_list_of_objects=True,
    )
    candidate_list = results['candidate_list_objects']
    if positive_value_exists(limit):
        candidate_list = candidate_list[:limit]  # Limit so we don't take too long with each run

    if candidate_list and len(candidate_list) > 0:
        status += "LOOPING_THROUGH_CANDIDATES_MISSING_POLITICIAN_WE_VOTE_ID "
        # Loop through all the candidates from this year
        for we_vote_candidate in candidate_list:
            num_candidates_reviewed += 1
            if we_vote_candidate.politician_we_vote_id:
                # We shouldn't ever reach this code given our is_missing_politician_we_vote_id rule above
                num_that_already_have_politician_we_vote_id += 1
            try:
                match_results = candidate_politician_match(we_vote_candidate)
            except Exception as e:
                status += (
                    f"ERROR_MATCHING_POLITICIAN-{we_vote_candidate.candidate_name}-"
                    f"{we_vote_candidate.we_vote_id}: {e} "
                )
                continue
            if match_results['politician_created']:
                new_politician_created += 1
            elif match_results['politician_found']:
                existing_politician_found += 1
            elif match_results['politician_list_found']:
                multiple_politicians_found += 1
            else:
                other_results += 1
    else:
        status += "ALL_CANDIDATES_HAVE_POLITICIAN_WE_VOTE_ID_THIS_YEAR "

    results = {
        'existing_politician_found': existing_politician_found,
        'multiple_politicians_found': multiple_politicians_found,
        'new_politician_created': new_politician_created,
        'num_that_already_have_politician_we_vote_id': num_that_already_have_politician_we_vote_id,
        'num_candidates_reviewed': num_candidates_reviewed,
        'other_results': other_results,
        'status': status,
        'success': success,
    }
    return results


def candidate_politician_match_batch_process():
    candidate_year = get_current_year_as_integer()
    state_code = ""
    status = ""
    success = True

    candidate_query = CandidateCampaign.objects.using('readonly').all()
    candidate_query = candidate_query.filter(candidate_year=candidate_year)
    candidate_query = candidate_query.exclude(duplicate_check_last_completed=None)
    candidate_query = candidate_query.filter(
        Q(politician_we_vote_id__isnull=True) |
        Q(politician_we_vote_id='')
    )
    # Get distinct state codes
    state_code_list = list(
        candidate_query.values_list('state_code', flat=True).distinct()
    )
    if len(state_code_list) > 0:
        state_code = state_code_list[0]

    if positive_value_exists(state_code):
        status += f"POLITICIAN_MATCH_PROCESSING_STATE_CODE-{state_code} "
        results = candidate_politician_match_this_year(candidate_year=candidate_year, state_code=state_code, limit=500)
        status += results['status']

        num_candidates_reviewed = results['num_candidates_reviewed']
        num_that_already_have_politician_we_vote_id = results['num_that_already_have_politician_we_vote_id']
        new_politician_created = results['new_politician_created']
        existing_politician_found = results['existing_politician_found']
        multiple_politicians_found = results['multiple_politicians_found']
        other_results = results['other_results']

        status += "[[Year: {candidate_year}, State: {state_code}: " \
                  "{num_candidates_reviewed} candidates reviewed, " \
                  "{num_that_already_have_politician_we_vote_id} Candidates that already have Politician Ids, " \
                  "{new_politician_created} politicians just created, " \
                  "{existing_politician_found} politicians found that already exist, " \
                  "{multiple_politicians_found} times we found multiple politicians and could not link, " \
                  "{other_results} other results.]] ". \
                  format(candidate_year=candidate_year,
                         num_candidates_reviewed=num_candidates_reviewed,
                         num_that_already_have_politician_we_vote_id=num_that_already_have_politician_we_vote_id,
                         new_politician_created=new_politician_created,
                         existing_politician_found=existing_politician_found,
                         multiple_politicians_found=multiple_politicians_found,
                         other_results=other_results,
                         state_code=state_code)
    else:
        status += "POLITICIAN_MATCH_NO_STATE_CODE "

    return {
        'status':                   status,
        'success':                  success,
    }


def find_and_merge_duplicate_candidates(
        candidate_year=0,
        google_civic_election_id=0,
        state_code=''):
    duplicate_check_complete_candidate_we_vote_id_list = []
    candidates_merged_found = False
    candidates_merged_list = []
    reset_duplicate_check_last_completed_we_vote_id_list = []
    status = ""
    success = True
    error_results = {
        "duplicate_check_complete_candidate_we_vote_id_list": duplicate_check_complete_candidate_we_vote_id_list,
        "candidates_merged_found": candidates_merged_found,
        "candidates_merged_list": candidates_merged_list,
        "reset_duplicate_check_last_completed_we_vote_id_list": reset_duplicate_check_last_completed_we_vote_id_list,
        "status": status,
        "success": False,
    }

    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()

    retrieve_by_candidate_year = False
    retrieve_by_election_id_list = False
    google_civic_election_id_list = []
    if positive_value_exists(candidate_year):
        retrieve_by_candidate_year = True
    elif positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [google_civic_election_id]
        retrieve_by_election_id_list = True
    else:
        retrieve_by_candidate_year = True
        candidate_year = get_current_year_as_integer()

    # ################################
    # Assemble a list of candidates that we already think might be duplicates
    try:
        queryset = CandidatesArePossibleDuplicates.objects.using('readonly').all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        queryset = queryset.exclude(candidate1_we_vote_id=None)
        queryset = queryset.exclude(candidate2_we_vote_id=None)
        queryset_candidate1 = queryset.values_list('candidate1_we_vote_id', flat=True).distinct()
        exclude_candidate1_we_vote_id_list = list(queryset_candidate1)
        queryset_candidate2 = queryset.values_list('candidate2_we_vote_id', flat=True).distinct()
        exclude_candidate2_we_vote_id_list = list(queryset_candidate2)
        exclude_candidate_we_vote_id_list = \
            list(set(exclude_candidate1_we_vote_id_list + exclude_candidate2_we_vote_id_list))
    except Exception as e:
        status += f"COULD_NOT_RETRIEVE_POSSIBLE_DUPLICATES: {str(e)} "
        error_results['status'] = status
        return error_results

    # ################################
    # Retrieve list of candidates to compare
    try:
        candidate_list = []
        if retrieve_by_candidate_year:
            results = candidate_list_manager.retrieve_all_candidates_for_one_year(
                candidate_year=candidate_year,
                limit_to_this_state_code=state_code,
                return_list_of_objects=True,
                read_only=True,
            )
            candidate_list = results['candidate_list_objects']
        elif retrieve_by_election_id_list:
            if positive_value_exists(state_code):
                results = candidate_list_manager.retrieve_candidates_for_specific_elections(
                    google_civic_election_id_list=google_civic_election_id_list,
                    limit_to_this_state_code=state_code,
                    return_list_of_objects=True)
                candidate_list = results['candidate_list_objects']
            else:
                results = candidate_list_manager.retrieve_candidates_for_specific_elections(
                    google_civic_election_id_list=google_civic_election_id_list,
                    return_list_of_objects=True)
                candidate_list = results['candidate_list_objects']
    except Exception as e:
        status += f"COULD_NOT_RETRIEVE_CANDIDATES: {str(e)} "
        error_results['status'] = status
        return error_results

    # ################################
    # Loop through all the candidates in this year or election (filtered by state)
    try:
        for we_vote_candidate in candidate_list:
            if we_vote_candidate.we_vote_id in exclude_candidate_we_vote_id_list:
                continue
            # Start ignore list with entries already reviewed
            ignore_candidate_id_list = exclude_candidate_we_vote_id_list.copy()
            # Add current entry to ignore list
            ignore_candidate_id_list.append(we_vote_candidate.we_vote_id)
            # Now check for others we have already labeled as "not a duplicate"
            duplicates_results = \
                candidate_manager.retrieve_candidates_are_not_duplicates_list(we_vote_candidate.we_vote_id)
            if duplicates_results['success']:
                not_a_duplicate_list = duplicates_results['candidates_are_not_duplicates_list_we_vote_ids']
                # Add current entry to ignore list
                ignore_candidate_id_list += not_a_duplicate_list
            else:
                status += f"COULD_NOT_RETRIEVE_CANDIDATES_ARE_NOT_DUPLICATES: {duplicates_results['status']} "

            results = find_duplicate_candidate(we_vote_candidate, ignore_candidate_id_list, read_only=True)

            # If we find candidates to merge, store them for review
            if results['candidate_merge_possibility_found']:
                candidate_option1_for_template = we_vote_candidate
                candidate_option2_for_template = results['candidate_merge_possibility']

                # Can we automatically merge these candidates?
                merge_results = merge_if_duplicate_candidates(
                    candidate_option1_for_template,
                    candidate_option2_for_template,
                    results['candidate_merge_conflict_values'])

                if merge_results['candidates_merged']:
                    candidate = merge_results['candidate']
                    if candidate.we_vote_id not in exclude_candidate_we_vote_id_list:
                        exclude_candidate_we_vote_id_list.append(candidate.we_vote_id)
                    if we_vote_candidate.we_vote_id not in exclude_candidate_we_vote_id_list:
                        exclude_candidate_we_vote_id_list.append(we_vote_candidate.we_vote_id)
                    CandidatesArePossibleDuplicates.objects.create(
                        candidate1_we_vote_id=candidate.we_vote_id,
                        candidate2_we_vote_id=None,
                        state_code=candidate.state_code,
                    )
                    CandidatesArePossibleDuplicates.objects.create(
                        candidate1_we_vote_id=we_vote_candidate.we_vote_id,
                        candidate2_we_vote_id=None,
                        state_code=we_vote_candidate.state_code,
                    )
                    candidates_merged_list.append(candidate)
                    candidates_merged_found = True
                    if candidate.we_vote_id not in reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(candidate.we_vote_id)
                else:
                    # Add an entry showing that this is a possible match
                    status += (
                        f"[Candidate {we_vote_candidate.candidate_name} "
                        f"({we_vote_candidate.we_vote_id}) has possible match.] "
                    )
                    state_code_local = state_code
                    if not positive_value_exists(state_code_local):
                        if positive_value_exists(we_vote_candidate.state_code):
                            state_code_local = we_vote_candidate.state_code
                        else:
                            state_code_local = candidate_option2_for_template.state_code
                    CandidatesArePossibleDuplicates.objects.create(
                        candidate1_we_vote_id=we_vote_candidate.we_vote_id,
                        candidate2_we_vote_id=candidate_option2_for_template.we_vote_id,
                        state_code=state_code_local,
                    )
                    if candidate_option2_for_template.we_vote_id not in exclude_candidate_we_vote_id_list:
                        exclude_candidate_we_vote_id_list.append(candidate_option2_for_template.we_vote_id)
                    if we_vote_candidate.we_vote_id not in reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(we_vote_candidate.we_vote_id)
                    if candidate_option2_for_template.we_vote_id not in \
                            reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(
                            candidate_option2_for_template.we_vote_id)
            else:
                # No matches found
                CandidatesArePossibleDuplicates.objects.create(
                    candidate1_we_vote_id=we_vote_candidate.we_vote_id,
                    candidate2_we_vote_id=None,
                    state_code=we_vote_candidate.state_code,
                )
                duplicate_check_complete_candidate_we_vote_id_list.append(we_vote_candidate.we_vote_id)
    except Exception as e:
        status += f"CRASHED_IN_CANDIDATE_LIST_LOOP: {str(e)} "
        # Fall through to exit function

    return {
        "duplicate_check_complete_candidate_we_vote_id_list": duplicate_check_complete_candidate_we_vote_id_list,
        "candidates_merged_found": candidates_merged_found,
        "candidates_merged_list": candidates_merged_list,
        "reset_duplicate_check_last_completed_we_vote_id_list": reset_duplicate_check_last_completed_we_vote_id_list,
        "status": status,
        "success": success,
    }


def find_states_that_need_new_candidate_deduplication():
    """
    Check to see if there are any states with that have new candidates that haven't been checked for duplicates
    """
    state_codes_for_deduplication = [
        "ak", "al", "ar", "az", "ca", "co", "ct", "dc", "de", "fl", "ga", "hi", "ia", "id", "il", "in", "ks",
        "ky", "la", "ma", "md", "me", "mi", "mn", "mo", "ms", "mt", "na", "nc", "nd", "ne", "nh", "nj", "nm",
        "nv", "ny", "oh", "ok", "or", "pa", "pr", "ri", "sc", "sd", "tn", "tx", "ut", "va", "vt", "wa", "wi",
        "wv", "wy"
    ]
    state_code_list = []
    status = ''
    success = True

    # Return all candidates from any state in state_codes_for_deduplication
    #  that have a null duplicate_check_last_completed value
    # We want to identify new candidates that haven't been deduplicated yet
    current_year_as_integer = get_current_year_as_integer()
    candidate_query = CandidateCampaign.objects.using('readonly').filter(
        candidate_year=current_year_as_integer,
        state_code__in=state_codes_for_deduplication,
        duplicate_check_last_completed__isnull=True,
    )
    # Extract a list of candidate we_vote_id values from the candidate_query organized by state_code
    candidate_list = list(candidate_query)
    candidates_by_state_code = {}
    for candidate in candidate_list:
        if candidate.state_code not in candidates_by_state_code:
            candidates_by_state_code[candidate.state_code] = []
        candidates_by_state_code[candidate.state_code].append(candidate.we_vote_id)

    # Now cycle through each state in state_codes_for_deduplication and make sure
    # that none of the we_vote_id values in candidates_by_state_code appear in PoliticiansArePossibleDuplicates
    for state_code in candidates_by_state_code:
        candidate_we_vote_id_list = candidates_by_state_code[state_code]
        candidate_we_vote_id_remaining_list = candidate_we_vote_id_list.copy()
        candidate_duplicate_check_query = CandidatesArePossibleDuplicates.objects.using('readonly').filter(
            (
                Q(candidate1_we_vote_id__in=candidate_we_vote_id_list) &
                Q(candidate2_we_vote_id__isnull=False)
            ) | (
                Q(candidate2_we_vote_id__in=candidate_we_vote_id_list) &
                Q(candidate1_we_vote_id__isnull=False)
            )
        )
        candidate_duplicate_check_list = list(candidate_duplicate_check_query)
        # Cycle through candidate_duplicate_check_list and remove one-by-one the values in candidate_we_vote_id_list.
        #  If there are values left, then we can run the deduplication process for the state again
        for candidate_duplicate_check in candidate_duplicate_check_list:
            if candidate_duplicate_check.candidate1_we_vote_id in candidate_we_vote_id_remaining_list:
                candidate_we_vote_id_remaining_list.remove(candidate_duplicate_check.candidate1_we_vote_id)
            if candidate_duplicate_check.candidate2_we_vote_id in candidate_we_vote_id_remaining_list:
                candidate_we_vote_id_remaining_list.remove(candidate_duplicate_check.candidate2_we_vote_id)

        if len(candidate_we_vote_id_remaining_list) > 0:
            # We need to run the deduplication process for this state again
            state_code_list.append(state_code)

    return {
        "state_code_list": state_code_list,
        "status": status,
        "success": success,
    }


def seo_friendly_path_updates(
        google_civic_election_id_list=None,
        number_to_update=1000,
        state_code=None,
):
    cleaning_candidate_list = []
    current_year = get_current_year_as_integer()
    starting_year = current_year - 1  # Start with prior year
    status = ''
    success = True
    total_to_convert_after = 0

    # Find all candidates in this election
    candidates_to_update_we_vote_id_list = []
    if google_civic_election_id_list and len(google_civic_election_id_list) > 0:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            google_civic_election_id_list=google_civic_election_id_list,
            read_only=True)
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        candidates_to_update_we_vote_id_list = []
        for candidate_to_office_link in candidate_to_office_link_list:
            if candidate_to_office_link.candidate_we_vote_id not in candidates_to_update_we_vote_id_list:
                candidates_to_update_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)

    # Now get all candidates we want to update, with a single query
    try:
        queryset = CandidateCampaign.objects.all()
        if candidates_to_update_we_vote_id_list and len(candidates_to_update_we_vote_id_list) > 0:
            queryset = queryset.filter(we_vote_id__in=candidates_to_update_we_vote_id_list)
        elif positive_value_exists(starting_year):
            queryset = queryset.filter(candidate_year__gte=starting_year)

        queryset = queryset.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        queryset = queryset.filter(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )

        # After initial updates to all candidates, include in the search logic to find candidates with
        # seo_friendly_path_date_last_updated older than Politician.seo_friendly_path_date_last_updated
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        total_to_convert = queryset.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        queryset = queryset.order_by('-id')
        cleaning_candidate_list = list(queryset[:number_to_update])
    except Exception as e:
        status += "FAILED_RETRIEVING_CANDIDATES_FOR_SEO_FRIENDLY_PATH: " + str(e) + " "

    politician_we_vote_id_list = []
    # Retrieve all relevant politicians in a single query
    for one_candidate in cleaning_candidate_list:
        politician_we_vote_id_list.append(one_candidate.politician_we_vote_id)
    politician_manager = PoliticianManager()
    politician_list = []
    if politician_we_vote_id_list and len(politician_we_vote_id_list) > 0:
        politician_results = politician_manager.retrieve_politician_list(
            politician_we_vote_id_list=politician_we_vote_id_list)
        politician_list = politician_results['politician_list']
    politician_dict_list = {}
    for one_politician in politician_list:
        politician_dict_list[one_politician.we_vote_id] = one_politician

    datetime_now = generate_localized_datetime_from_obj()[1]
    seo_friendly_path_missing = 0
    update_list = []
    updates_needed = False
    updates_made = 0
    for one_candidate in cleaning_candidate_list:
        one_politician = politician_dict_list.get(one_candidate.politician_we_vote_id)
        if hasattr(one_politician, 'seo_friendly_path') and positive_value_exists(one_politician.seo_friendly_path):
            one_candidate.seo_friendly_path = one_politician.seo_friendly_path
            one_candidate.seo_friendly_path_date_last_updated = datetime_now
            update_list.append(one_candidate)
            updates_needed = True
            updates_made += 1
        else:
            seo_friendly_path_missing += 1
    if positive_value_exists(seo_friendly_path_missing):
        status += \
            "{seo_friendly_path_missing:,} missing seo_friendly_path (not found in Politician). " \
            "".format(seo_friendly_path_missing=seo_friendly_path_missing)

    if updates_needed:
        try:
            CandidateCampaign.objects.bulk_update(
                update_list, ['seo_friendly_path', 'seo_friendly_path_date_last_updated'])
            status += \
                "{updates_made:,} candidates updated with new seo_friendly_path. " \
                "{total_to_convert_after:,} remaining." \
                "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made)
        except Exception as e:
            status += "FAILED_MAKING_CANDIDATES_SEO_FRIENDLY_PATH_UPDATES: " + str(e) + " "
            success = False
    else:
        status += "NO_SEO_FRIENDLY_PATH_UPDATES_NEEDED "

    if positive_value_exists(status):
        status += "(SEO_UPDATE_SCRIPT) "

    results = {
        'status': status,
        'success': success,
    }
    return results


def update_candidate_from_politician_batch_process(second_pass=False):
    candidate_list = []
    candidate_year = get_current_year_as_integer()
    politician_dict_list = {}
    status = ""
    success = True

    try:
        candidate_query = CandidateCampaign.objects.all()
        candidate_query = candidate_query.filter(candidate_year=candidate_year)
        candidate_query = candidate_query.exclude(duplicate_check_last_completed=None)
        if second_pass:
            candidate_query = candidate_query.exclude(updated_from_politician_completed_first=None)
            candidate_query = candidate_query.filter(updated_from_politician_completed_second=None)
        else:
            candidate_query = candidate_query.filter(updated_from_politician_completed_first=None)
        candidate_query = candidate_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id='')
        )
        candidate_query = candidate_query[:500]  # Limit to 500 to throttle this process
        candidate_list = list(candidate_query)
    except Exception as e:
        status += "FAILED_RETRIEVING_CANDIDATES_FOR_UPDATE_FROM_POLITICIAN: " + str(e) + " "

    if candidate_list and len(candidate_list) > 0:
        politician_we_vote_id_list = [
            candidate.politician_we_vote_id for candidate in candidate_list
            if candidate.politician_we_vote_id
        ]
        if second_pass:
            status += "UPDATE_CANDIDATE_FROM_POLITICIAN_SECOND "
        else:
            status += "UPDATE_CANDIDATE_FROM_POLITICIAN_FIRST "
        status += "CANDIDATES_FOUND-" + str(len(candidate_list)) + " "
        status += "POLITICIAN_WE_VOTE_IDS_FOUND-" + str(len(politician_we_vote_id_list)) + " "
    else:
        if second_pass:
            status += "UPDATE_CANDIDATE_FROM_POLITICIAN_SECOND_NONE_FOUND "
        else:
            status += "UPDATE_CANDIDATE_FROM_POLITICIAN_FIRST_NONE_FOUND "
        return {
            'status':                   status,
            'success':                  success,
        }

    try:
        from politician.models import Politician
        queryset = Politician.objects.using('readonly').filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
    except Exception as e:
        status += "FAILED_RETRIEVING_POLITICIANS: " + str(e) + " "
        success = False

    all_candidate_fields_updated = []
    candidate_bulk_update_list = []
    candidates_updated_count = 0
    candidates_not_updated_count = 0
    candidate_update_problem_count = 0
    from candidate.controllers import update_candidate_details_from_politician
    for one_candidate in candidate_list:
        politician = politician_dict_list.get(one_candidate.politician_we_vote_id)
        if politician:
            if not hasattr(politician, 'date_last_updated_from_candidate'):
                candidates_not_updated_count += 1
                status += "COMPLETE_POLITICIAN_NOT_FOUND "
                continue
            if politician.duplicate_check_last_completed is None:
                # We don't want to update the candidate if the politician hasn't been checked for duplicates
                candidates_not_updated_count += 1
                status += f"POLITICIAN_NEEDS_TO_BE_DEDUPLICATED_FIRST-{politician.we_vote_id} "
                continue
            results = update_candidate_details_from_politician(politician=politician, candidate=one_candidate)
            if results['success']:
                save_changes = results['save_changes']
                changed_candidate = results['candidate']
                if second_pass:
                    changed_candidate.updated_from_politician_completed_second = localtime(now()).date()
                    if 'updated_from_politician_completed_second' not in all_candidate_fields_updated:
                        all_candidate_fields_updated.append('updated_from_politician_completed_second')
                else:
                    changed_candidate.updated_from_politician_completed_first = localtime(now()).date()
                    if 'updated_from_politician_completed_first' not in all_candidate_fields_updated:
                        all_candidate_fields_updated.append('updated_from_politician_completed_first')
                if save_changes:
                    changed_candidate.date_last_updated = localtime(now()).date()
                    if 'date_last_updated' not in all_candidate_fields_updated:
                        all_candidate_fields_updated.append('date_last_updated')
                    if not second_pass:
                        # Reset duplicate_check_last_completed so we check for duplicate Candidates again
                        changed_candidate.duplicate_check_last_completed = None
                        if 'duplicate_check_last_completed' not in all_candidate_fields_updated:
                            all_candidate_fields_updated.append('duplicate_check_last_completed')
                    candidates_updated_count += 1
                    fields_updated = results['fields_updated']
                    for field in fields_updated:
                        if field not in all_candidate_fields_updated:
                            all_candidate_fields_updated.append(field)
                else:
                    candidates_not_updated_count += 1
                candidate_bulk_update_list.append(changed_candidate)
            else:
                candidate_update_problem_count += 1
                candidates_not_updated_count += 1
                if candidate_update_problem_count <= 5:
                    status += results['status']
        else:
            status += f"POLITICIAN_NOT_FOUND_IN_DB-{one_candidate.politician_we_vote_id} "
            candidates_not_updated_count += 1

    if len(candidate_bulk_update_list) > 0:
        try:
            CandidateCampaign.objects.bulk_update(candidate_bulk_update_list, all_candidate_fields_updated)
            status += \
                "[[CANDIDATES_UPDATED: {candidates_updated_count:,} " \
                "NOT_UPDATED: {candidates_not_updated_count:,}]] \n" \
                "".format(
                    candidates_not_updated_count=candidates_not_updated_count,
                    candidates_updated_count=candidates_updated_count,
                )
        except Exception as e:
            status += "FAILED_BULK_UPDATE_OF_CANDIDATES: " + str(e) + " "

    return {
        'status':                   status,
        'success':                  success,
    }


def update_politician_from_candidate_batch_process():
    candidate_list = []
    candidate_year = get_current_year_as_integer()
    politician_dict_list = {}
    status = ""
    success = True

    try:
        candidate_query = CandidateCampaign.objects.all()
        candidate_query = candidate_query.filter(candidate_year=candidate_year)
        candidate_query = candidate_query.exclude(duplicate_check_last_completed=None)
        candidate_query = candidate_query.exclude(updated_from_politician_completed_first=None)
        candidate_query = candidate_query.filter(updates_to_politician_completed=None)
        candidate_query = candidate_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id='')
        )
        candidate_query = candidate_query[:500]  # Limit to 500 to throttle this process
        candidate_list = list(candidate_query)
    except Exception as e:
        status += "FAILED_RETRIEVING_CANDIDATES_FOR_POLITICIAN_UPDATE: " + str(e) + " "

    if candidate_list and len(candidate_list) > 0:
        politician_we_vote_id_list = [
            candidate.politician_we_vote_id for candidate in candidate_list
            if candidate.politician_we_vote_id
        ]
        status += "UPDATE_POLITICIAN_FROM_CANDIDATE "
        status += "CANDIDATES_FOUND-" + str(len(candidate_list)) + " "
        status += "POLITICIAN_WE_VOTE_IDS_FOUND-" + str(len(politician_we_vote_id_list)) + " "
    else:
        status += "UPDATE_POLITICIAN_FROM_CANDIDATE_NONE_FOUND "
        return {
            'status':                   status,
            'success':                  success,
        }

    try:
        queryset = Politician.objects.filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
    except Exception as e:
        status += "FAILED_RETRIEVING_POLITICIANS: " + str(e) + " "
        success = False

    # Loop through all the politicians in this year, and update them with some data from the new candidate entry
    all_politician_fields_updated = []
    candidate_bulk_update_list = []
    politician_bulk_update_list = []
    politician_update_errors = 0
    politicians_not_updated = 0
    politicians_updated = 0
    from politician.controllers import update_politician_details_from_candidate
    for one_candidate in candidate_list:
        politician = politician_dict_list.get(one_candidate.politician_we_vote_id)
        if politician:
            if not hasattr(politician, 'date_last_updated_from_candidate'):
                politicians_not_updated += 1
                status += "COMPLETE_POLITICIAN_NOT_FOUND "
                continue
            if politician.duplicate_check_last_completed is None:
                # We don't want to update the politician if the politician hasn't been checked for duplicates
                politicians_not_updated += 1
                status += f"POLITICIAN_NEEDS_TO_BE_DEDUPLICATED_FIRST-{politician.we_vote_id} "
                continue
            results = update_politician_details_from_candidate(politician=politician, candidate=one_candidate)
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
                one_candidate.updates_to_politician_completed = localtime(now()).date()
                candidate_bulk_update_list.append(one_candidate)
                if save_changes:
                    politicians_updated += 1
                else:
                    politicians_not_updated += 1
            else:
                politician_update_errors += 1
                status += results['status']

    politicians_saved = False
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
            politicians_saved = True
        except Exception as e:
            politicians_saved = False
            status += "FAILED_BULK_UPDATE_OF_POLITICIANS: " + str(e) + " "
            success = False

    if politicians_saved and len(candidate_bulk_update_list) > 0:
        try:
            CandidateCampaign.objects.bulk_update(
                candidate_bulk_update_list,
                ['updates_to_politician_completed'])
            status += \
                "[[Candidates saved: {candidates_updated:,}]] " \
                "".format(
                    candidates_updated=len(candidate_bulk_update_list))
        except Exception as e:
            status += "FAILED_BULK_UPDATE_OF_CANDIDATES: " + str(e) + " "
            success = False

    return {
        'status':                   status,
        'success':                  success,
    }
