# analytics/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import AnalyticsAction, AnalyticsCountManager, AnalyticsManager, \
    ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS
from candidate.models import CandidateManager
from config.base import get_environment_variable
from datetime import date, datetime, timedelta
from django.db.models import Q
from django.utils.timezone import localtime, now
from exception.models import print_to_log
from follow.models import FollowMetricsManager, FollowOrganizationList
from import_export_batches.models import AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID, \
    AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT, \
    BatchProcessManager, \
    CALCULATE_ORGANIZATION_DAILY_METRICS, \
    CALCULATE_ORGANIZATION_ELECTION_METRICS, \
    CALCULATE_SITEWIDE_DAILY_METRICS, \
    CALCULATE_SITEWIDE_ELECTION_METRICS, \
    CALCULATE_SITEWIDE_VOTER_METRICS
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from position.models import PositionMetricsManager
from share.models import ShareManager
from voter.models import VoterManager, VoterMetricsManager
import wevote_functions.admin
from wevote_functions.functions import convert_date_to_date_as_integer, convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")


def augment_voter_analytics_action_entries_without_election_id(date_as_integer, through_date_as_integer):
    """
    Retrieve list of voters with AnalyticsAction entries that have an empty google_civic_election_id
     and then loop through those entries to do the following:
     1) Look for the oldest entry with an election_id
     2) For that day, loop forward (while on the same day) and fill in the empty google_civic_election_ids
        until we find a new election id
     3) Then continue looping forward using the different election_id (while on the same day)
     4) Mark all of the entries prior to the first election entry as NULL
    :return:
    """
    success = False
    status = ""

    # Get distinct voters in the time period
    voter_analytics_list = []
    try:
        voter_list_query = AnalyticsAction.objects.using('analytics').all()
        voter_list_query = voter_list_query.filter(date_as_integer__gte=date_as_integer)
        voter_list_query = voter_list_query.filter(date_as_integer__lte=through_date_as_integer)
        # Find entries where there is at least one empty google_civic_election_id
        voter_list_query = voter_list_query.filter(Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
        voter_list_query = voter_list_query.values('voter_we_vote_id').distinct()
        # voter_list_query = voter_list_query[:5]  # TEMP limit to 5
        voter_analytics_list = list(voter_list_query)
        voter_list_found = True
    except Exception as e:
        voter_list_found = False

    simple_voter_list = []
    for voter_dict in voter_analytics_list:
        if positive_value_exists(voter_dict['voter_we_vote_id']):
            simple_voter_list.append(voter_dict['voter_we_vote_id'])

    # Loop through each voter that has at least one empty google_civic_election_id entry
    analytics_updated_count = 0
    for voter_we_vote_id in simple_voter_list:
        # Start and end time are not needed
        results = augment_one_voter_analytics_action_entries_without_election_id(voter_we_vote_id)
        analytics_updated_count += results['analytics_updated_count']

    # TODO Outside of this function, call it recursively as long as we break out due to too much time passing
    #  between entries
    results = {
        'success':                  success,
        'status':                   status,
        'analytics_updated_count':  analytics_updated_count,
    }
    return results


def process_one_analytics_batch_process_augment_with_election_id(batch_process, batch_process_analytics_chunk):
    status = ""
    success = True

    if not batch_process or not batch_process_analytics_chunk or not batch_process.analytics_date_as_integer:
        status += "MISSING_REQUIRED_VARIABLES "
        results = {
            'success':              success,
            'status':               status,
        }
        return results

    analytics_manager = AnalyticsManager()
    batch_process_manager = BatchProcessManager()

    # Start by finding voters already processed for analytics_date_as_integer
    exclude_voter_we_vote_id_list = []
    results = analytics_manager.retrieve_analytics_processed_list(
        analytics_date_as_integer=batch_process.analytics_date_as_integer,
        kind_of_process=AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID)
    if results['retrieved_voter_we_vote_id_list_found']:
        # Exclude the voters already processed for analytics_date_as_integer
        exclude_voter_we_vote_id_list = results['retrieved_voter_we_vote_id_list']

    # Find voters who haven't been processed yet for analytics_date_as_integer
    try:
        voter_list_query = AnalyticsAction.objects.using('analytics').all()
        voter_list_query = voter_list_query.filter(date_as_integer=batch_process.analytics_date_as_integer)
        if len(exclude_voter_we_vote_id_list):
            voter_list_query = voter_list_query.exclude(voter_we_vote_id__in=exclude_voter_we_vote_id_list)
        # Find entries where there is at least one empty google_civic_election_id
        voter_list_query = voter_list_query.filter(Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
        voter_list_query = voter_list_query.values_list('voter_we_vote_id', flat=True).distinct()
        voter_analytics_list = voter_list_query[:250]  # Limit to 250 voters at a time
    except Exception as e:
        status += "ANALYTICS_ACTION_ERROR_FIND_VOTERS: " + str(e) + " "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success':              success,
            'status':               status,
        }
        return results

    if len(voter_analytics_list):
        try:
            batch_process_analytics_chunk.number_of_rows_being_reviewed = len(voter_analytics_list)
            batch_process_analytics_chunk.save()

            status += "ROWS_BEING_REVIEWED: " + str(len(voter_analytics_list)) + " "
        except Exception as e:
            status += "NUMBER_OF_ROWS_BEING_REVIEWED_NOT_SAVED " + str(e) + " "

    candidate_election_cache = {}
    origin_elections_reviewed = []
    measure_cache = {}
    analytics_updated_count = 0
    number_of_rows_successfully_reviewed = 0
    for voter_we_vote_id in voter_analytics_list:
        retrieve_results = augment_analytics_action_with_election_id_one_voter(
            voter_we_vote_id,
            analytics_date_as_integer=batch_process.analytics_date_as_integer,
            candidate_election_cache=candidate_election_cache,
            origin_elections_reviewed=origin_elections_reviewed,
            measure_cache=measure_cache,
        )
        candidate_election_cache = retrieve_results['candidate_election_cache']
        origin_elections_reviewed = retrieve_results['origin_elections_reviewed']
        measure_cache = retrieve_results['measure_cache']

        status += retrieve_results['status']
        analytics_updated_count += retrieve_results['analytics_updated_count']
        if results['success']:
            number_of_rows_successfully_reviewed += 1

    try:
        batch_process_analytics_chunk.number_of_rows_successfully_reviewed = number_of_rows_successfully_reviewed
        batch_process_analytics_chunk.date_completed = now()
        batch_process_analytics_chunk.save()

        status += "BATCH_PROCESS_ANALYTICS_CHUNK, ROWS_REVIEWED: " \
                  "" + str(number_of_rows_successfully_reviewed) + " "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
    except Exception as e:
        status += "BATCH_PROCESS_ANALYTICS_CHUNK_TIMED_OUT-DATE_COMPLETED_TIME_NOT_SAVED " + str(e) + " "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )

    if not len(voter_analytics_list):
        try:
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()
        except Exception as e:
            status += "BATCH_PROCESS_DATE_COMPLETED_NOT_SAVED: " + str(e) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                analytics_date_as_integer=batch_process.analytics_date_as_integer,
                status=status,
            )

        # If here, there aren't any more analytics to process for augment_with_election_id for this date
        defaults = {
            'finished_augment_analytics_action_with_election_id': True,
        }
        status_results = analytics_manager.save_analytics_processing_status(
            batch_process.analytics_date_as_integer,
            defaults=defaults)
        status += status_results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_one_analytics_batch_process_augment_with_first_visit(batch_process, batch_process_analytics_chunk):
    status = ""
    success = True
    first_visit_today_count = 0

    if not batch_process or not batch_process_analytics_chunk or not batch_process.analytics_date_as_integer:
        status += "MISSING_REQUIRED_VARIABLES-FIRST_VISIT "
        results = {
            'success':              success,
            'status':               status,
        }
        return results

    analytics_manager = AnalyticsManager()
    batch_process_manager = BatchProcessManager()

    # Start by finding voters already processed for analytics_date_as_integer
    exclude_voter_we_vote_id_list = []
    results = analytics_manager.retrieve_analytics_processed_list(
        analytics_date_as_integer=batch_process.analytics_date_as_integer,
        kind_of_process=AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT)
    if results['retrieved_voter_we_vote_id_list_found']:
        # Exclude the voters already processed for analytics_date_as_integer
        exclude_voter_we_vote_id_list = results['retrieved_voter_we_vote_id_list']

    # Find voters who haven't been processed yet for analytics_date_as_integer
    try:
        voter_list_query = AnalyticsAction.objects.using('analytics').all()
        voter_list_query = voter_list_query.filter(date_as_integer=batch_process.analytics_date_as_integer)
        if len(exclude_voter_we_vote_id_list):
            voter_list_query = voter_list_query.exclude(voter_we_vote_id__in=exclude_voter_we_vote_id_list)
        # Find entries where there is at least one empty google_civic_election_id
        voter_list_query = voter_list_query.values_list('voter_we_vote_id', flat=True).distinct()
        voter_analytics_list = voter_list_query[:250]  # Limit to 250 voters at a time
    except Exception as e:
        status += "ANALYTICS_ACTION_ERROR_FIND_VOTERS-FIRST_VISIT: " + str(e) + " "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success':              success,
            'status':               status,
        }
        return results

    if len(voter_analytics_list):
        try:
            batch_process_analytics_chunk.number_of_rows_being_reviewed = len(voter_analytics_list)
            batch_process_analytics_chunk.save()

            status += "ROWS_BEING_REVIEWED-FIRST_VISIT: " + str(len(voter_analytics_list)) + " "
        except Exception as e:
            status += "NUMBER_OF_ROWS_BEING_REVIEWED_NOT_SAVED-FIRST_VISIT " + str(e) + " "

    for voter_we_vote_id in voter_analytics_list:
        analysis_success = True
        try:
            first_visit_query = AnalyticsAction.objects.using('analytics').all()
            first_visit_query = first_visit_query.order_by("id")  # order by oldest first
            first_visit_query = first_visit_query.filter(date_as_integer=batch_process.analytics_date_as_integer)
            first_visit_query = first_visit_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            analytics_action = first_visit_query.first()

            analytics_action.first_visit_today = True
            analytics_action.save()
            first_visit_today_count += 1
        except Exception as e:
            status += "FAILED_SAVING_ANALYTICS_ACTION " + str(e) + " "
            analysis_success = False
        if analysis_success:
            defaults = {
                'analytics_date_as_integer': batch_process.analytics_date_as_integer,
                'voter_we_vote_id': voter_we_vote_id,
                'kind_of_process': AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT,
            }
            results = analytics_manager.save_analytics_processed(
                analytics_date_as_integer=batch_process.analytics_date_as_integer,
                voter_we_vote_id=voter_we_vote_id,
                defaults=defaults)

    try:
        batch_process_analytics_chunk.number_of_rows_successfully_reviewed = first_visit_today_count
        batch_process_analytics_chunk.date_completed = now()
        batch_process_analytics_chunk.save()

        status += "BATCH_PROCESS_ANALYTICS_CHUNK, ROWS_REVIEWED-FIRST_VISIT: " \
                  "" + str(first_visit_today_count) + " "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
    except Exception as e:
        status += "DATE_COMPLETED_TIME_NOT_SAVED-FIRST_VISIT " + str(e) + " "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )

    if not len(voter_analytics_list):
        try:
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()
        except Exception as e:
            status += "BATCH_PROCESS_DATE_COMPLETED_NOT_SAVED-FIRST_VISIT: " + str(e) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                analytics_date_as_integer=batch_process.analytics_date_as_integer,
                status=status,
            )

        # If here, there aren't any more analytics to process for augment_with_election_id for this date
        defaults = {
            'finished_augment_analytics_action_with_first_visit': True,
        }
        status_results = analytics_manager.save_analytics_processing_status(
            batch_process.analytics_date_as_integer,
            defaults=defaults)
        status += status_results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def augment_analytics_action_with_election_id_one_voter(
        voter_we_vote_id, analytics_date_as_integer=0,
        candidate_election_cache={},
        origin_elections_reviewed=[],
        measure_cache={}):
    success = True
    status = ""
    voter_history_list = []
    analytics_updated_count = 0
    try:
        voter_history_query = AnalyticsAction.objects.using('analytics').all()
        voter_history_query = voter_history_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
        voter_history_query = voter_history_query.filter(date_as_integer=analytics_date_as_integer)
        voter_history_query = voter_history_query.order_by("id")  # order by oldest first
        voter_history_list = list(voter_history_query)
    except Exception as e:
        status += "COULD_NOT_RETRIEVE_ANALYTICS_FOR_VOTER-ONE_VOTER: " + str(e) + " "

    # First loop through and assign election for candidates and measures associated with specific election
    analytics_manager = AnalyticsManager()
    candidate_manager = CandidateManager()
    contest_measure_manager = ContestMeasureManager()
    for analytics_action in voter_history_list:
        analysis_success = True
        if positive_value_exists(analytics_action.ballot_item_we_vote_id) \
                and not positive_value_exists(analytics_action.google_civic_election_id):
            if "cand" in analytics_action.ballot_item_we_vote_id:
                # If we are looking at a candidate without a google_civic_election_id...
                if analytics_action.ballot_item_we_vote_id in candidate_election_cache:
                    candidate_google_civic_election_id = \
                        candidate_election_cache[analytics_action.ballot_item_we_vote_id]
                else:
                    candidate_google_civic_election_id = \
                        candidate_manager.fetch_next_upcoming_election_id_for_candidate(
                            analytics_action.ballot_item_we_vote_id)
                    candidate_election_cache[analytics_action.ballot_item_we_vote_id] = \
                        candidate_google_civic_election_id
                if positive_value_exists(candidate_google_civic_election_id):
                    try:
                        analytics_action.google_civic_election_id = candidate_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ANALYTICS_ACTION-CANDIDATE_CAMPAIGN: " + str(e) + " "
            elif "meas" in analytics_action.ballot_item_we_vote_id:
                measure_found = False
                # If we are looking at a measure without a google_civic_election_id
                contest_measure_google_civic_election_id = 0
                if analytics_action.ballot_item_we_vote_id in measure_cache:
                    measure_found = True
                    contest_measure = measure_cache[analytics_action.ballot_item_we_vote_id]
                    contest_measure_google_civic_election_id = contest_measure.google_civic_election_id
                else:
                    results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                        analytics_action.ballot_item_we_vote_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        measure_cache[analytics_action.ballot_item_we_vote_id] = contest_measure
                        measure_found = True
                        contest_measure_google_civic_election_id = contest_measure.google_civic_election_id
                if measure_found and positive_value_exists(contest_measure_google_civic_election_id):
                    try:
                        analytics_action.google_civic_election_id = contest_measure_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ANALYTICS_ACTION-CONTEST_MEASURE: " + str(e) + " "
        if analysis_success:
            defaults = {
                'analytics_date_as_integer': analytics_date_as_integer,
                'voter_we_vote_id': voter_we_vote_id,
                'kind_of_process': AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID,
            }
            results = analytics_manager.save_analytics_processed(
                analytics_date_as_integer=analytics_date_as_integer,
                voter_we_vote_id=voter_we_vote_id,
                defaults=defaults)

    # Now "fill-in-the-gaps"
    leading_edge_google_civic_election_id = 0  # The very first google_civic_election_id found
    latest_google_civic_election_id = 0  # As we go from oldest-to-newest, update this to the next id found
    analytics_action_list_before_first_election = []
    datetime_of_last_analytics_action_entry = None
    one_week = timedelta(days=7)
    for analytics_action in voter_history_list:
        if positive_value_exists(analytics_action.google_civic_election_id):
            # If the next-newest analytics_action entry has a google_civic_election_id,
            #  reset the latest_google_civic_election_id
            latest_google_civic_election_id = analytics_action.google_civic_election_id
            if not positive_value_exists(leading_edge_google_civic_election_id):
                # Only set this once
                leading_edge_google_civic_election_id = analytics_action.google_civic_election_id
        else:
            if positive_value_exists(latest_google_civic_election_id):
                # If within 1 week of last analytics_action entry, set the google_civic_election_id
                # to the leading_edge_google_civic_election_id
                is_within_one_week = False
                if datetime_of_last_analytics_action_entry:
                    time_passed_since_last_entry = \
                        analytics_action.exact_time - datetime_of_last_analytics_action_entry
                    if time_passed_since_last_entry < one_week:
                        is_within_one_week = True

                if is_within_one_week:
                    try:
                        analytics_action.google_civic_election_id = latest_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ANALYTICS_ACTION-WITHIN_ONE_WEEK: " + str(e) + " "
                else:
                    # Recursively start up the process starting from this entry, and then break out of this loop
                    new_starting_analytics_action_id = analytics_action.id
                    results = augment_one_voter_analytics_action_entries_without_election_id(
                        voter_we_vote_id, new_starting_analytics_action_id)
                    analytics_updated_count += results['analytics_updated_count']
                    break
            else:
                # If here, we have not set the leading_edge_google_civic_election_id yet
                #  so we want to save these entries into a "precursor" list
                analytics_action_list_before_first_election.append(analytics_action)

        datetime_of_last_analytics_action_entry = analytics_action.exact_time

    if positive_value_exists(leading_edge_google_civic_election_id):
        for analytics_action in analytics_action_list_before_first_election:
            # Loop through these and set to leading_edge_google_civic_election_id
            if not positive_value_exists(analytics_action.google_civic_election_id):  # Make sure it is empty
                try:
                    analytics_action.google_civic_election_id = leading_edge_google_civic_election_id
                    analytics_action.save()
                    analytics_updated_count += 1
                except Exception as e:
                    status += "COULD_NOT_SAVE_ANALYTICS_ACTION-BEFORE_FIRST_ELECTION: " + str(e) + " "

    # 2017-09-21 As of now, we are not going to guess the election if there wasn't any election-related activity.

    results = {
        'success': success,
        'status': status,
        'analytics_updated_count': analytics_updated_count,
        'candidate_election_cache': candidate_election_cache,
        'origin_elections_reviewed': origin_elections_reviewed,
        'measure_cache': measure_cache,
    }
    return results


def augment_one_voter_analytics_action_entries_without_election_id(voter_we_vote_id, starting_analytics_action_id=0):
    success = True
    status = ""
    voter_history_list = []
    analytics_updated_count = 0
    try:
        voter_history_query = AnalyticsAction.objects.using('analytics').all()
        voter_history_query = voter_history_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
        if positive_value_exists(starting_analytics_action_id):
            voter_history_query = voter_history_query.filter(id__gte=starting_analytics_action_id)
        voter_history_query = voter_history_query.order_by("id")  # order by oldest first
        voter_history_list = list(voter_history_query)
    except Exception as e:
        status += "COULD_NOT_RETRIEVE_ANALYTICS_FOR_VOTER-gte=starting_analytics_action: " + str(e) + " "

    # First loop through and assign election for candidates and measures associated with specific election
    candidate_manager = CandidateManager()
    contest_measure_manager = ContestMeasureManager()
    candidate_election_cache = {}
    measure_found_list = []
    measure_cache = {}
    for analytics_action in voter_history_list:
        if positive_value_exists(analytics_action.ballot_item_we_vote_id) \
                and not positive_value_exists(analytics_action.google_civic_election_id):
            if "cand" in analytics_action.ballot_item_we_vote_id:
                # If we are looking at a candidate without a google_civic_election_id...
                if analytics_action.ballot_item_we_vote_id in candidate_election_cache:
                    candidate_google_civic_election_id = \
                        candidate_election_cache[analytics_action.ballot_item_we_vote_id]
                else:
                    candidate_google_civic_election_id = \
                        candidate_manager.fetch_next_upcoming_election_id_for_candidate(
                            analytics_action.ballot_item_we_vote_id)
                    candidate_election_cache[analytics_action.ballot_item_we_vote_id] = \
                        candidate_google_civic_election_id
                if positive_value_exists(candidate_google_civic_election_id):
                    try:
                        analytics_action.google_civic_election_id = candidate_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ANALYTICS_ACTION-CANDIDATE_CAMPAIGN: " + str(e) + " "
            elif "meas" in analytics_action.ballot_item_we_vote_id:
                measure_found = False
                # If we are looking at a measure without a google_civic_election_id
                contest_measure_google_civic_election_id = 0
                if analytics_action.ballot_item_we_vote_id in measure_found_list:
                    measure_found = True
                    contest_measure = measure_cache[analytics_action.ballot_item_we_vote_id]
                    contest_measure_google_civic_election_id = contest_measure.google_civic_election_id
                else:
                    results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                        analytics_action.ballot_item_we_vote_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        measure_cache[analytics_action.ballot_item_we_vote_id] = contest_measure
                        measure_found_list.append(analytics_action.ballot_item_we_vote_id)
                        measure_found = True
                        contest_measure_google_civic_election_id = contest_measure.google_civic_election_id
                if measure_found and positive_value_exists(contest_measure_google_civic_election_id):
                    try:
                        analytics_action.google_civic_election_id = contest_measure_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ANALYTICS_ACTION-CONTEST_MEASURE: " + str(e) + " "

    # Now "fill-in-the-gaps"
    leading_edge_google_civic_election_id = 0  # The very first google_civic_election_id found
    latest_google_civic_election_id = 0  # As we go from oldest-to-newest, update this to the next id found
    analytics_action_list_before_first_election = []
    datetime_of_last_analytics_action_entry = None
    one_week = timedelta(days=7)
    for analytics_action in voter_history_list:
        if positive_value_exists(analytics_action.google_civic_election_id):
            # If the next-newest analytics_action entry has a google_civic_election_id,
            #  reset the latest_google_civic_election_id
            latest_google_civic_election_id = analytics_action.google_civic_election_id
            if not positive_value_exists(leading_edge_google_civic_election_id):
                # Only set this once
                leading_edge_google_civic_election_id = analytics_action.google_civic_election_id
        else:
            if positive_value_exists(latest_google_civic_election_id):
                # If within 1 week of last analytics_action entry, set the google_civic_election_id
                # to the leading_edge_google_civic_election_id
                is_within_one_week = False
                if datetime_of_last_analytics_action_entry:
                    time_passed_since_last_entry = \
                        analytics_action.exact_time - datetime_of_last_analytics_action_entry
                    if time_passed_since_last_entry < one_week:
                        is_within_one_week = True

                if is_within_one_week:
                    try:
                        analytics_action.google_civic_election_id = latest_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        status += "COULD_NOT_SAVE_ANALYTICS_ACTION-WITHIN_ONE_WEEK: " + str(e) + " "
                else:
                    # Recursively start up the process starting from this entry, and then break out of this loop
                    new_starting_analytics_action_id = analytics_action.id
                    results = augment_one_voter_analytics_action_entries_without_election_id(
                        voter_we_vote_id, new_starting_analytics_action_id)
                    analytics_updated_count += results['analytics_updated_count']
                    break
            else:
                # If here, we have not set the leading_edge_google_civic_election_id yet
                #  so we want to save these entries into a "precursor" list
                analytics_action_list_before_first_election.append(analytics_action)

        datetime_of_last_analytics_action_entry = analytics_action.exact_time

    if positive_value_exists(leading_edge_google_civic_election_id):
        for analytics_action in analytics_action_list_before_first_election:
            # Loop through these and set to leading_edge_google_civic_election_id
            if not positive_value_exists(analytics_action.google_civic_election_id):  # Make sure it is empty
                try:
                    analytics_action.google_civic_election_id = leading_edge_google_civic_election_id
                    analytics_action.save()
                    analytics_updated_count += 1
                except Exception as e:
                    status += "COULD_NOT_SAVE_ANALYTICS_ACTION-BEFORE_FIRST_ELECTION: " + str(e) + " "

    # 2017-09-21 As of now, we are not going to guess the election if there wasn't any election-related activity.

    results = {
        'success': success,
        'status': status,
        'analytics_updated_count': analytics_updated_count,
    }
    return results


def process_sitewide_voter_metrics(batch_process, batch_process_analytics_chunk):
    status = ""
    success = True
    sitewide_voter_metrics_updated = 0

    analytics_manager = AnalyticsManager()
    batch_process_manager = BatchProcessManager()

    if not batch_process or not batch_process_analytics_chunk or not batch_process.analytics_date_as_integer:
        status += "MISSING_REQUIRED_VARIABLES-VOTER_METRICS "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success':              success,
            'status':               status,
        }
        return results

    # Start by finding voters already processed for analytics_date_as_integer or more recent
    exclude_voter_we_vote_id_list = []
    results = analytics_manager.retrieve_analytics_processed_list(
        analytics_date_as_integer_more_recent_than=batch_process.analytics_date_as_integer,
        kind_of_process=CALCULATE_SITEWIDE_VOTER_METRICS)
    if results['retrieved_voter_we_vote_id_list_found']:
        # Exclude the voters already processed for analytics_date_as_integer
        exclude_voter_we_vote_id_list = results['retrieved_voter_we_vote_id_list']

    # Find voters who haven't been processed yet for analytics_date_as_integer
    try:
        voter_list_query = AnalyticsAction.objects.using('analytics').all()
        voter_list_query = voter_list_query.filter(date_as_integer=batch_process.analytics_date_as_integer)
        if len(exclude_voter_we_vote_id_list):
            voter_list_query = voter_list_query.exclude(voter_we_vote_id__in=exclude_voter_we_vote_id_list)
        # Find entries where there is at least one empty google_civic_election_id
        voter_list_query = voter_list_query.values_list('voter_we_vote_id', flat=True).distinct()
        voter_analytics_list = voter_list_query[:250]  # Limit to 250 voters at a time
    except Exception as e:
        status += "ANALYTICS_ACTION_ERROR_FIND_VOTERS-VOTER_METRICS: " + str(e) + " "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success':              success,
            'status':               status,
        }
        return results

    if len(voter_analytics_list):
        try:
            batch_process_analytics_chunk.number_of_rows_being_reviewed = len(voter_analytics_list)
            batch_process_analytics_chunk.save()

            status += "ROWS_BEING_REVIEWED-VOTER_METRICS: " + str(len(voter_analytics_list)) + " "
        except Exception as e:
            status += "NUMBER_OF_ROWS_BEING_REVIEWED_NOT_SAVED-VOTER_METRICS: " + str(e) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
            results = {
                'success':              success,
                'status':               status,
            }
            return results

    for voter_we_vote_id in voter_analytics_list:
        analysis_success = True
        results = calculate_sitewide_voter_metrics_for_one_voter(voter_we_vote_id)
        status += results['status']
        if positive_value_exists(results['success']):
            sitewide_voter_metrics_values = results['sitewide_voter_metrics_values']
            sitewide_voter_metrics_values['last_calculated_date_as_integer'] = batch_process.analytics_date_as_integer

            analytics_manager = AnalyticsManager()
            update_results = analytics_manager.save_sitewide_voter_metrics_values_for_one_voter(
                sitewide_voter_metrics_values)
            status += update_results['status']
            if positive_value_exists(update_results['success']):
                sitewide_voter_metrics_updated += 1
            else:
                status += "SAVE_SITEWIDE_VOTER_METRICS-FAILED_TO_SAVE "
                analysis_success = False
        else:
            # So we can set a breakpoint in case of problems
            status += "SAVE_SITEWIDE_VOTER_METRICS-FAILED_TO_CALCULATE "
            analysis_success = False
        if analysis_success:
            # We save analytics_date_as_integer as today since the statistics saved are all based on today
            # We check to see if there is an entry greater than or equal to the analytics_date_as_integer,
            # so it doesn't re-calculate metrics that are already up-to-date
            today = datetime.now().date()
            today_date_as_integer = convert_date_to_date_as_integer(today)
            defaults = {
                'analytics_date_as_integer': today_date_as_integer,
                'voter_we_vote_id': voter_we_vote_id,
                'kind_of_process': CALCULATE_SITEWIDE_VOTER_METRICS,
            }
            results = analytics_manager.save_analytics_processed(
                analytics_date_as_integer=today_date_as_integer,
                voter_we_vote_id=voter_we_vote_id,
                defaults=defaults)

    try:
        batch_process_analytics_chunk.number_of_rows_successfully_reviewed = sitewide_voter_metrics_updated
        batch_process_analytics_chunk.date_completed = now()
        batch_process_analytics_chunk.save()

        status += "BATCH_PROCESS_ANALYTICS_CHUNK, ROWS_REVIEWED-VOTER_METRICS: " \
                  "" + str(sitewide_voter_metrics_updated) + " "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
    except Exception as e:
        status += "DATE_COMPLETED_TIME_NOT_SAVED-VOTER_METRICS " + str(e) + " "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )

    if not len(voter_analytics_list):
        try:
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()
        except Exception as e:
            status += "BATCH_PROCESS_DATE_COMPLETED_NOT_SAVED-VOTER_METRICS: " + str(e) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                analytics_date_as_integer=batch_process.analytics_date_as_integer,
                status=status,
            )

        # If here, there aren't any more analytics to process for augment_with_election_id for this date
        defaults = {
            'finished_calculate_sitewide_voter_metrics': True,
        }
        status_results = analytics_manager.save_analytics_processing_status(
            batch_process.analytics_date_as_integer,
            defaults=defaults)
        status += status_results['status']

    batch_process_manager.create_batch_process_log_entry(
        batch_process_id=batch_process.id,
        kind_of_process=batch_process.kind_of_process,
        status=status,
    )

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def save_analytics_action_for_api(action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
                                  organization_we_vote_id, organization_id, google_civic_election_id,
                                  user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
                                  ballot_item_we_vote_id=None, voter_device_id=None):  # saveAnalyticsAction
    analytics_manager = AnalyticsManager()
    success = True
    status = "SAVE_ANALYTICS_ACTION "
    date_as_integer = 0
    required_variables_missing = False

    action_requires_organization_ids = True if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS else False

    if not positive_value_exists(action_constant):
        success = False
        required_variables_missing = True
        status += "MISSING_ACTION_CONSTANT "
    if not positive_value_exists(voter_we_vote_id):
        success = False
        required_variables_missing = True
        status += "MISSING_VOTER_WE_VOTE_ID "
    if not positive_value_exists(voter_id):
        success = False
        required_variables_missing = True
        status += "MISSING_VOTER_ID "
    if action_requires_organization_ids:
        # For these actions, make sure we have organization ids
        if not positive_value_exists(organization_we_vote_id):
            success = False
            required_variables_missing = True
            status += "MISSING_ORGANIZATION_WE_VOTE_ID "
        if not positive_value_exists(organization_id):
            success = False
            required_variables_missing = True
            status += "MISSING_ORGANIZATION_ID "

    if required_variables_missing:
        results = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'action_constant':          action_constant,
            'is_signed_in':             is_signed_in,
            'state_code':               state_code,
            'google_civic_election_id': google_civic_election_id,
            'organization_we_vote_id':  organization_we_vote_id,
            'organization_id':          organization_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'date_as_integer':          date_as_integer,
            'user_agent':               user_agent_string,
            'is_bot':                   is_bot,
            'is_mobile':                is_mobile,
            'is_desktop':               is_desktop,
            'is_tablet':                is_tablet,
        }
        return results

    save_results = analytics_manager.save_action(
            action_constant,
            voter_we_vote_id, voter_id, is_signed_in, state_code,
            organization_we_vote_id, organization_id, google_civic_election_id,
            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
            ballot_item_we_vote_id, voter_device_id)
    if save_results['action_saved']:
        action = save_results['action']
        date_as_integer = action.date_as_integer
        status += save_results['status']
        success = save_results['success']
    else:
        status += "ACTION_VOTER_GUIDE_VISIT-NOT_SAVED "
        success = False

    results = {
        'status':                   status,
        'success':                  success,
        'voter_device_id':          voter_device_id,
        'action_constant':          action_constant,
        'is_signed_in':             is_signed_in,
        'state_code':               state_code,
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'organization_id':          organization_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'date_as_integer':          date_as_integer,
        'user_agent':               user_agent_string,
        'is_bot':                   is_bot,
        'is_mobile':                is_mobile,
        'is_desktop':               is_desktop,
        'is_tablet':                is_tablet,
    }
    return results


def calculate_organization_election_metrics(google_civic_election_id, organization_we_vote_id):
    status = ""
    success = False

    analytics_count_manager = AnalyticsCountManager()
    follow_count_manager = FollowMetricsManager()
    position_metrics_manager = PositionMetricsManager()
    follow_organization_list = FollowOrganizationList()

    limit_to_authenticated = True
    return_voter_we_vote_id = True

    google_civic_election_id = convert_to_int(google_civic_election_id)
    visitors_total = analytics_count_manager.fetch_visitors(google_civic_election_id, organization_we_vote_id)
    authenticated_visitors_total = analytics_count_manager.fetch_visitors(
        google_civic_election_id, organization_we_vote_id, 0, 0, limit_to_authenticated)
    voter_guide_entrants = analytics_count_manager.fetch_visitors_first_visit_to_organization_in_election(
        organization_we_vote_id, google_civic_election_id)
    followers_at_time_of_election = follow_count_manager.fetch_organization_followers(
        organization_we_vote_id, google_civic_election_id)
    new_followers = analytics_count_manager.fetch_new_followers_in_election(
        google_civic_election_id, organization_we_vote_id)
    new_auto_followers = analytics_count_manager.fetch_new_auto_followers_in_election(
        google_civic_election_id, organization_we_vote_id)
    entrants_visited_ballot = analytics_count_manager.fetch_organization_entrants_visited_ballot(
        organization_we_vote_id, google_civic_election_id)
    followers_visited_ballot = analytics_count_manager.fetch_organization_followers_visited_ballot(
        organization_we_vote_id, google_civic_election_id)

    entrants_took_position = analytics_count_manager.fetch_organization_entrants_took_position(
        organization_we_vote_id, google_civic_election_id)
    entrants_voter_we_vote_ids = analytics_count_manager.fetch_organization_entrants_list(
        organization_we_vote_id, google_civic_election_id)
    entrants_public_positions = position_metrics_manager.fetch_positions_public(
        google_civic_election_id, entrants_voter_we_vote_ids)
    entrants_public_positions_with_comments = position_metrics_manager.fetch_positions_public_with_comments(
        google_civic_election_id, entrants_voter_we_vote_ids)
    entrants_friends_only_positions = position_metrics_manager.fetch_positions_friends_only(
        google_civic_election_id, entrants_voter_we_vote_ids)
    entrants_friends_only_positions_with_comments = position_metrics_manager.fetch_positions_friends_only_with_comments(
        google_civic_election_id, entrants_voter_we_vote_ids)

    followers_took_position = analytics_count_manager.fetch_organization_followers_took_position(
        organization_we_vote_id, google_civic_election_id)
    followers_voter_we_vote_ids = follow_organization_list.fetch_followers_list_by_organization_we_vote_id(
        organization_we_vote_id, return_voter_we_vote_id)
    followers_public_positions = position_metrics_manager.fetch_positions_public(
        google_civic_election_id, followers_voter_we_vote_ids)
    followers_public_positions_with_comments = position_metrics_manager.fetch_positions_public_with_comments(
        google_civic_election_id, followers_voter_we_vote_ids)
    followers_friends_only_positions = position_metrics_manager.fetch_positions_friends_only(
        google_civic_election_id, followers_voter_we_vote_ids)
    followers_friends_only_positions_with_comments = \
        position_metrics_manager.fetch_positions_friends_only_with_comments(
            google_civic_election_id, followers_voter_we_vote_ids)


    success = True
    status += "CALCULATED_ORGANIZATION_ELECTION_METRICS "

    organization_election_metrics_values = {
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'visitors_total':           visitors_total,
        'authenticated_visitors_total':     authenticated_visitors_total,
        'voter_guide_entrants':     voter_guide_entrants,
        'followers_at_time_of_election':    followers_at_time_of_election,
        'new_followers':            new_followers,
        'new_auto_followers':        new_auto_followers,
        'entrants_visited_ballot':  entrants_visited_ballot,
        'followers_visited_ballot': followers_visited_ballot,
        'entrants_took_position':                           entrants_took_position,
        'entrants_public_positions':                        entrants_public_positions,
        'entrants_public_positions_with_comments':          entrants_public_positions_with_comments,
        'entrants_friends_only_positions':                  entrants_friends_only_positions,
        'entrants_friends_only_positions_with_comments':    entrants_friends_only_positions_with_comments,
        'followers_took_position':                          followers_took_position,
        'followers_public_positions':                       followers_public_positions,
        'followers_public_positions_with_comments':         followers_public_positions_with_comments,
        'followers_friends_only_positions':                 followers_friends_only_positions,
        'followers_friends_only_positions_with_comments':   followers_friends_only_positions_with_comments,
    }
    results = {
        'status':                               status,
        'success':                              success,
        'organization_election_metrics_values': organization_election_metrics_values,
    }
    return results


def calculate_organization_daily_metrics(organization_we_vote_id, limit_to_one_date_as_integer):
    status = ""
    success = False
    google_civic_election_id_zero = 0
    limit_to_authenticated = True

    analytics_count_manager = AnalyticsCountManager()
    follow_count_manager = FollowMetricsManager()
    position_metrics_manager = PositionMetricsManager()
    follow_organization_list = FollowOrganizationList()

    date_as_integer = convert_to_int(date)
    visitors_total = analytics_count_manager.fetch_visitors(google_civic_election_id_zero, organization_we_vote_id)
    authenticated_visitors_total = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id, 0, 0, limit_to_authenticated)

    visitors_today = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id, limit_to_one_date_as_integer)
    authenticated_visitors_today = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id, limit_to_one_date_as_integer, 0, limit_to_authenticated)

    new_visitors_today = None
    voter_guide_entrants_today = None
    entrants_visiting_ballot = None
    followers_visiting_ballot = None
    followers_total = None
    new_followers_today = None
    auto_followers_total = None
    new_auto_followers_today = None
    issues_linked_total = None
    organization_public_positions = None

    success = True

    organization_daily_metrics_values = {
        'date_as_integer':                          date_as_integer,
        'organization_we_vote_id':                  organization_we_vote_id,
        'visitors_total':                           visitors_total,
        'visitors_today':                           visitors_today,
        'new_visitors_today':                       new_visitors_today,
        'authenticated_visitors_total':             authenticated_visitors_total,
        'authenticated_visitors_today':             authenticated_visitors_today,
        'voter_guide_entrants_today':               voter_guide_entrants_today,
        'entrants_visiting_ballot':                 entrants_visiting_ballot,
        'followers_visiting_ballot':                followers_visiting_ballot,
        'followers_total':                          followers_total,
        'new_followers_today':                      new_followers_today,
        'auto_followers_total':                     auto_followers_total,
        'new_auto_followers_today':                 new_auto_followers_today,
        'issues_linked_total':                      issues_linked_total,
        'organization_public_positions':            organization_public_positions,
    }
    results = {
        'status':                               status,
        'success':                              success,
        'organization_daily_metrics_values':    organization_daily_metrics_values,
    }
    return results


def calculate_sitewide_daily_metrics(limit_to_one_date_as_integer):
    status = ""
    success = False

    analytics_count_manager = AnalyticsCountManager()
    follow_metrics_manager = FollowMetricsManager()
    share_manager = ShareManager()

    google_civic_election_id_zero = 0
    organization_we_vote_id_empty = ""
    voter_we_vote_id_empty = ""
    limit_to_authenticated = True
    date_as_integer_zero = 0
    limit_to_one_date_as_integer = convert_to_int(limit_to_one_date_as_integer)
    count_through_this_date_as_integer = limit_to_one_date_as_integer

    visitors_total = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id_empty, date_as_integer_zero,
        count_through_this_date_as_integer)
    visitors_today = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id_empty, limit_to_one_date_as_integer)
    new_visitors_today = None
    voter_guide_entrants_today = None
    welcome_page_entrants_today = None
    friend_entrants_today = None
    authenticated_visitors_total = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id_empty,
        date_as_integer_zero, count_through_this_date_as_integer, limit_to_authenticated)
    authenticated_visitors_today = analytics_count_manager.fetch_visitors(
        google_civic_election_id_zero, organization_we_vote_id_empty,
        limit_to_one_date_as_integer, date_as_integer_zero, limit_to_authenticated)
    ballot_views_today = analytics_count_manager.fetch_ballot_views(
        google_civic_election_id_zero, limit_to_one_date_as_integer)
    voter_guides_viewed_total = analytics_count_manager.fetch_voter_guides_viewed(
        google_civic_election_id_zero, date_as_integer_zero, count_through_this_date_as_integer)
    voter_guides_viewed_today = analytics_count_manager.fetch_voter_guides_viewed(
        google_civic_election_id_zero, limit_to_one_date_as_integer)

    issues_followed_total = follow_metrics_manager.fetch_issues_followed(
        voter_we_vote_id_empty, date_as_integer_zero, count_through_this_date_as_integer)
    issues_followed_today = follow_metrics_manager.fetch_issues_followed(
        voter_we_vote_id_empty, limit_to_one_date_as_integer, count_through_this_date_as_integer)

    shared_items_clicked_today = share_manager.fetch_shared_items_clicked_count_for_one_day(
        date_as_integer=limit_to_one_date_as_integer)
    shared_link_clicked_count_today = share_manager.fetch_shared_link_clicked_count_for_one_day(
        date_as_integer=limit_to_one_date_as_integer)
    shared_link_clicked_unique_viewers_today = share_manager.fetch_shared_link_clicked_unique_viewers_one_day(
        date_as_integer=limit_to_one_date_as_integer)

    organizations_followed_total = None
    organizations_followed_today = None
    organizations_auto_followed_total = None
    organizations_auto_followed_today = None
    organizations_with_linked_issues = None
    issues_linked_total = None
    issues_linked_today = None
    organizations_signed_in_total = None
    organizations_with_positions = None
    organizations_with_new_positions_today = None
    organization_public_positions = None
    individuals_with_positions = None
    individuals_with_public_positions = None
    individuals_with_friends_only_positions = None
    friends_only_positions = None
    entered_full_address = None

    success = True

    sitewide_daily_metrics_values = {
        'date_as_integer':                          limit_to_one_date_as_integer,
        'visitors_total':                           visitors_total,
        'visitors_today':                           visitors_today,
        'new_visitors_today':                       new_visitors_today,
        'voter_guide_entrants_today':               voter_guide_entrants_today,
        'welcome_page_entrants_today':              welcome_page_entrants_today,
        'friend_entrants_today':                    friend_entrants_today,
        'authenticated_visitors_total':             authenticated_visitors_total,
        'authenticated_visitors_today':             authenticated_visitors_today,
        'ballot_views_today':                       ballot_views_today,
        'voter_guides_viewed_total':                voter_guides_viewed_total,
        'voter_guides_viewed_today':                voter_guides_viewed_today,
        'issues_followed_total':                    issues_followed_total,
        'issues_followed_today':                    issues_followed_today,
        'organizations_followed_total':             organizations_followed_total,
        'organizations_followed_today':             organizations_followed_today,
        'organizations_auto_followed_total':        organizations_auto_followed_total,
        'organizations_auto_followed_today':        organizations_auto_followed_today,
        'organizations_with_linked_issues':         organizations_with_linked_issues,
        'issues_linked_total':                      issues_linked_total,
        'issues_linked_today':                      issues_linked_today,
        'organizations_signed_in_total':            organizations_signed_in_total,
        'organizations_with_positions':             organizations_with_positions,
        'organizations_with_new_positions_today':   organizations_with_new_positions_today,
        'organization_public_positions':            organization_public_positions,
        'individuals_with_positions':               individuals_with_positions,
        'individuals_with_public_positions':        individuals_with_public_positions,
        'individuals_with_friends_only_positions':  individuals_with_friends_only_positions,
        'friends_only_positions':                   friends_only_positions,
        'entered_full_address':                     entered_full_address,
        'shared_items_clicked_today':               shared_items_clicked_today,
        'shared_link_clicked_count_today':          shared_link_clicked_count_today,
        'shared_link_clicked_unique_viewers_today': shared_link_clicked_unique_viewers_today,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_daily_metrics_values':    sitewide_daily_metrics_values,
    }
    return results


def calculate_sitewide_election_metrics(google_civic_election_id):
    status = ""
    success = False

    analytics_count_manager = AnalyticsCountManager()
    follow_metrics_manager = FollowMetricsManager()
    position_metrics_manager = PositionMetricsManager()
    voter_metrics_manager = VoterMetricsManager()

    google_civic_election_id = convert_to_int(google_civic_election_id)
    visitors_total = analytics_count_manager.fetch_visitors(google_civic_election_id)
    voter_guide_entries = None
    voter_guide_views = None
    voter_guides_viewed = analytics_count_manager.fetch_voter_guides_viewed(google_civic_election_id)
    issues_followed = None
    unique_voters_that_followed_organizations = analytics_count_manager.fetch_new_followers_in_election(
        google_civic_election_id)
    unique_voters_that_auto_followed_organizations = analytics_count_manager.fetch_new_auto_followers_in_election(
        google_civic_election_id)
    organizations_followed = None
    organizations_auto_followed = None
    organizations_signed_in = None
    organizations_with_positions = None
    organization_public_positions = None
    individuals_with_positions = None
    individuals_with_public_positions = None
    individuals_with_friends_only_positions = None
    public_positions = position_metrics_manager.fetch_positions_public(google_civic_election_id)
    public_positions_with_comments = position_metrics_manager.fetch_positions_public_with_comments(
        google_civic_election_id)
    friends_only_positions = position_metrics_manager.fetch_positions_friends_only(google_civic_election_id)
    friends_only_positions_with_comments = position_metrics_manager.fetch_positions_friends_only_with_comments(
        google_civic_election_id)
    entered_full_address = None

    success = True

    sitewide_election_metrics_values = {
        'google_civic_election_id':                 google_civic_election_id,
        'visitors_total':                           visitors_total,
        'voter_guide_entries':                      voter_guide_entries,
        'voter_guide_views':                        voter_guide_views,
        'voter_guides_viewed':                      voter_guides_viewed,
        'issues_followed':                          issues_followed,
        'unique_voters_that_followed_organizations':        unique_voters_that_followed_organizations,
        'unique_voters_that_auto_followed_organizations':   unique_voters_that_auto_followed_organizations,
        'organizations_followed':                   organizations_followed,
        'organizations_auto_followed':              organizations_auto_followed,
        'organizations_signed_in':                  organizations_signed_in,
        'organizations_with_positions':             organizations_with_positions,
        'organization_public_positions':            organization_public_positions,
        'individuals_with_positions':               individuals_with_positions,
        'individuals_with_public_positions':        individuals_with_public_positions,
        'individuals_with_friends_only_positions':  individuals_with_friends_only_positions,
        'public_positions':                         public_positions,
        'public_positions_with_comments':           public_positions_with_comments,
        'friends_only_positions':                   friends_only_positions,
        'friends_only_positions_with_comments':     friends_only_positions_with_comments,
        'entered_full_address':                     entered_full_address,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_election_metrics_values': sitewide_election_metrics_values,
    }
    return results


def calculate_sitewide_voter_metrics_for_one_voter(voter_we_vote_id):
    """
    This voter's statistics across their entire history on We Vote
    :param voter_we_vote_id:
    :return:
    """
    status = ""
    success = False
    voter_id = 0
    signed_in_twitter = False
    signed_in_facebook = False
    signed_in_with_email = False
    signed_in_with_sms_phone_number = False
    analytics_count_manager = AnalyticsCountManager()
    follow_metrics_manager = FollowMetricsManager()
    position_metrics_manager = PositionMetricsManager()
    voter_metrics_manager = VoterMetricsManager()

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id)
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        signed_in_twitter = voter.signed_in_twitter()
        signed_in_facebook = voter.signed_in_facebook()
        signed_in_with_email = voter.signed_in_with_email()
        signed_in_with_sms_phone_number = voter.signed_in_with_sms_phone_number()

    actions_count = analytics_count_manager.fetch_voter_action_count(voter_we_vote_id)
    seconds_on_site = None
    elections_viewed = None
    voter_guides_viewed = analytics_count_manager.fetch_voter_voter_guides_viewed(voter_we_vote_id)
    ballot_visited = analytics_count_manager.fetch_voter_ballot_visited(voter_we_vote_id)
    welcome_visited = analytics_count_manager.fetch_voter_welcome_visited(voter_we_vote_id)
    entered_full_address = voter_metrics_manager.fetch_voter_entered_full_address(voter_id)
    issues_followed = follow_metrics_manager.fetch_issues_followed(voter_we_vote_id)
    organizations_followed = follow_metrics_manager.fetch_voter_organizations_followed(voter_id)
    time_until_sign_in = None
    positions_entered_friends_only = position_metrics_manager.fetch_voter_positions_entered_friends_only(
        voter_we_vote_id)
    positions_entered_public = position_metrics_manager.fetch_voter_positions_entered_public(voter_we_vote_id)
    comments_entered_friends_only = position_metrics_manager.fetch_voter_comments_entered_friends_only(
        voter_we_vote_id)
    comments_entered_public = position_metrics_manager.fetch_voter_comments_entered_public(voter_we_vote_id)
    days_visited = analytics_count_manager.fetch_voter_days_visited(voter_we_vote_id)
    last_action_date = analytics_count_manager.fetch_voter_last_action_date(voter_we_vote_id)

    success = True

    sitewide_voter_metrics_values = {
        'voter_we_vote_id':         voter_we_vote_id,
        'actions_count':            actions_count,
        'seconds_on_site':          seconds_on_site,
        'elections_viewed':         elections_viewed,
        'voter_guides_viewed':      voter_guides_viewed,
        'issues_followed':          issues_followed,
        'organizations_followed':   organizations_followed,
        'ballot_visited':           ballot_visited,
        'welcome_visited':          welcome_visited,
        'entered_full_address':     entered_full_address,
        'time_until_sign_in':       time_until_sign_in,
        'positions_entered_friends_only':   positions_entered_friends_only,
        'positions_entered_public':         positions_entered_public,
        'comments_entered_friends_only':    comments_entered_friends_only,
        'comments_entered_public':          comments_entered_public,
        'signed_in_twitter':        signed_in_twitter,
        'signed_in_facebook':       signed_in_facebook,
        'signed_in_with_email':     signed_in_with_email,
        'signed_in_with_sms_phone_number':  signed_in_with_sms_phone_number,
        'days_visited':             days_visited,
        'last_action_date': last_action_date,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_voter_metrics_values':    sitewide_voter_metrics_values,
    }
    return results


def delete_analytics_info_for_voter(voter_to_delete_we_vote_id):
    status = "DELETE_ANALYTICS_ACTION_DATA"
    success = False
    analytics_action_deleted = 0
    analytics_action_not_deleted = 0

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_ANALYTICS_ACTION-MISSING_FROM_OR_TO_VOTER_ID"
        results = {
            'status':                       status,
            'success':                      success,
            'voter_to_delete_we_vote_id':   voter_to_delete_we_vote_id,
            'analytics_action_deleted':     analytics_action_deleted,
            'analytics_action_not_deleted': analytics_action_not_deleted,
        }
        return results

    analytics_manager = AnalyticsManager()
    analytics_action_list_results = analytics_manager.retrieve_analytics_action_list(voter_to_delete_we_vote_id)
    if analytics_action_list_results['analytics_action_list_found']:
        analytics_action_list = analytics_action_list_results['analytics_action_list']

        for analytics_action_object in analytics_action_list:
            try:
                analytics_action_object.delete()
                analytics_action_deleted += 1
            except Exception as e:
                analytics_action_not_deleted += 1
                status += "UNABLE_TO_SAVE_ANALYTICS_ACTION "

        status += " DELETE_ANALYTICS_ACTION, moved: " + str(analytics_action_deleted) + \
                  ", not moved: " + str(analytics_action_not_deleted)
    else:
        status += " " + analytics_action_list_results['status']

    results = {
        'status':                       status,
        'success':                      success,
        'voter_to_delete_we_vote_id':   voter_to_delete_we_vote_id,
        'analytics_action_deleted':     analytics_action_deleted,
        'analytics_action_not_deleted': analytics_action_not_deleted,
    }
    return results


def move_analytics_info_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = " MOVE_ANALYTICS_ACTION_DATA"
    success = False
    analytics_action_moved = 0
    analytics_action_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_ANALYTICS_ACTION-MISSING_FROM_OR_TO_VOTER_ID"
        results = {
            'status':                       status,
            'success':                      success,
            'from_voter_we_vote_id':        from_voter_we_vote_id,
            'to_voter_we_vote_id':          to_voter_we_vote_id,
            'analytics_action_moved':       analytics_action_moved,
            'analytics_action_not_moved':   analytics_action_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_ANALYTICS_ACTION-FROM_AND_TO_VOTER_WE_VOTE_ID_IDENTICAL "
        results = {
            'status':                       status,
            'success':                      success,
            'from_voter_we_vote_id':        from_voter_we_vote_id,
            'to_voter_we_vote_id':          to_voter_we_vote_id,
            'analytics_action_moved':       analytics_action_moved,
            'analytics_action_not_moved':   analytics_action_not_moved,
        }
        return results

    analytics_manager = AnalyticsManager()
    analytics_action_list_results = analytics_manager.retrieve_analytics_action_list(from_voter_we_vote_id)
    if analytics_action_list_results['analytics_action_list_found']:
        analytics_action_list = analytics_action_list_results['analytics_action_list']

        for analytics_action_object in analytics_action_list:
            # Change the voter_we_vote_id
            try:
                analytics_action_object.voter_we_vote_id = to_voter_we_vote_id
                analytics_action_object.save()
                analytics_action_moved += 1
            except Exception as e:
                analytics_action_not_moved += 1
                status += "UNABLE_TO_SAVE_ANALYTICS_ACTION "

        status += " MOVE_ANALYTICS_ACTION, moved: " + str(analytics_action_moved) + \
                  ", not moved: " + str(analytics_action_not_moved)
    else:
        status += " " + analytics_action_list_results['status']

    results = {
        'status':                       status,
        'success':                      success,
        'from_voter_we_vote_id':        from_voter_we_vote_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'analytics_action_moved':       analytics_action_moved,
        'analytics_action_not_moved':   analytics_action_not_moved,
    }
    return results


def retrieve_analytics_processing_next_step():
    """
    What is the next processing required to bring our analytics data up-to-date?
    Start by augmenting voter_analytics data
    Then move through each of these for one day:
    save_sitewide_daily_metrics
    save_sitewide_election_metrics
    save_sitewide_voter_metrics
    save_organization_daily_metrics
    save_organization_election_metrics
    :return:
    """
    status = ""
    analytics_processing_status_found = False

    analytics_date_as_integer = 0
    calculate_sitewide_voter_metrics = False
    calculate_sitewide_election_metrics = False
    calculate_sitewide_daily_metrics = False
    calculate_organization_election_metrics = False
    calculate_organization_daily_metrics = False
    augment_analytics_action_with_first_visit = False
    augment_analytics_action_with_election_id = False

    analytics_manager = AnalyticsManager()
    results = analytics_manager.retrieve_or_create_next_analytics_processing_status()
    success = results['success']
    if not success:
        status += results['status']
    if results['analytics_processing_status_found']:
        analytics_processing_status_found = True
        analytics_processing_status = results['analytics_processing_status']

        # TEMP Mark some of these steps as temporarily done
        analytics_processing_status.finished_calculate_organization_daily_metrics = True
        analytics_processing_status.finished_calculate_organization_election_metrics = True
        analytics_processing_status.finished_calculate_sitewide_election_metrics = True

        analytics_date_as_integer = analytics_processing_status.analytics_date_as_integer
        if analytics_processing_status.finished_augment_analytics_action_with_election_id and \
                analytics_processing_status.finished_augment_analytics_action_with_first_visit and \
                analytics_processing_status.finished_calculate_organization_daily_metrics and \
                analytics_processing_status.finished_calculate_organization_election_metrics and \
                analytics_processing_status.finished_calculate_sitewide_daily_metrics and \
                analytics_processing_status.finished_calculate_sitewide_election_metrics and \
                analytics_processing_status.finished_calculate_sitewide_voter_metrics:
            # If here, then all of the steps have been processed
            pass
        elif analytics_processing_status.finished_augment_analytics_action_with_election_id and \
                analytics_processing_status.finished_augment_analytics_action_with_first_visit and \
                analytics_processing_status.finished_calculate_organization_daily_metrics and \
                analytics_processing_status.finished_calculate_organization_election_metrics and \
                analytics_processing_status.finished_calculate_sitewide_daily_metrics and \
                analytics_processing_status.finished_calculate_sitewide_election_metrics:
            # CALCULATE_SITEWIDE_VOTER_METRICS
            calculate_sitewide_voter_metrics = True
        # elif analytics_processing_status.finished_augment_analytics_action_with_election_id and \
        #         analytics_processing_status.finished_augment_analytics_action_with_first_visit and \
        #         analytics_processing_status.finished_calculate_organization_daily_metrics and \
        #         analytics_processing_status.finished_calculate_organization_election_metrics and \
        #         analytics_processing_status.finished_calculate_sitewide_daily_metrics:
        #     # CALCULATE_SITEWIDE_ELECTION_METRICS
        #     calculate_sitewide_election_metrics = True
        elif analytics_processing_status.finished_augment_analytics_action_with_election_id and \
                analytics_processing_status.finished_augment_analytics_action_with_first_visit and \
                analytics_processing_status.finished_calculate_organization_daily_metrics and \
                analytics_processing_status.finished_calculate_organization_election_metrics:
            # CALCULATE_SITEWIDE_DAILY_METRICS
            calculate_sitewide_daily_metrics = True
        # elif analytics_processing_status.finished_augment_analytics_action_with_election_id and \
        #         analytics_processing_status.finished_augment_analytics_action_with_first_visit and \
        #         analytics_processing_status.finished_calculate_organization_daily_metrics:
        #     # CALCULATE_ORGANIZATION_ELECTION_METRICS
        #     calculate_organization_election_metrics = True
        # elif analytics_processing_status.finished_augment_analytics_action_with_election_id and \
        #         analytics_processing_status.finished_augment_analytics_action_with_first_visit:
        #     # CALCULATE_ORGANIZATION_DAILY_METRICS
        #     calculate_organization_daily_metrics = True
        elif analytics_processing_status.finished_augment_analytics_action_with_election_id:
            # AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT
            augment_analytics_action_with_first_visit = True
        elif not analytics_processing_status.finished_augment_analytics_action_with_election_id:
            # AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID
            augment_analytics_action_with_election_id = True
        else:
            # None of them need to be processed
            pass

    results = {
        'status':                                       status,
        'success':                                      success,
        'analytics_processing_status_found':            analytics_processing_status_found,
        'analytics_date_as_integer':                    analytics_date_as_integer,
        'calculate_sitewide_voter_metrics':             calculate_sitewide_voter_metrics,
        'calculate_sitewide_election_metrics':          calculate_sitewide_election_metrics,
        'calculate_sitewide_daily_metrics':             calculate_sitewide_daily_metrics,
        'calculate_organization_election_metrics':      calculate_organization_election_metrics,
        'calculate_organization_daily_metrics':         calculate_organization_daily_metrics,
        'augment_analytics_action_with_first_visit':    augment_analytics_action_with_first_visit,
        'augment_analytics_action_with_election_id':    augment_analytics_action_with_election_id,
    }
    return results


def save_organization_daily_metrics(organization_we_vote_id, date):
    status = ""
    success = False

    results = calculate_organization_daily_metrics(organization_we_vote_id, date)
    status += results['status']
    if results['success']:
        organization_daily_metrics_values = results['organization_daily_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = analytics_manager.save_organization_daily_metrics_values(organization_daily_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def save_organization_election_metrics(google_civic_election_id, organization_we_vote_id):
    status = "SAVE_ORGANIZATION_ELECTION_METRICS, " \
             "google_civic_election_id: " + str(google_civic_election_id) + \
             ", organization_we_vote_id: " + str(organization_we_vote_id) + " "
    success = False

    results = calculate_organization_election_metrics(google_civic_election_id, organization_we_vote_id)
    status += results['status']
    if results['success']:
        organization_election_metrics_values = results['organization_election_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = \
            analytics_manager.save_organization_election_metrics_values(organization_election_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def save_sitewide_daily_metrics(date_as_integer, through_date_as_integer=0):
    status = ""
    success = True
    date_as_integer_list = []

    analytics_manager = AnalyticsManager()
    date_as_integer_results = \
        analytics_manager.retrieve_list_of_dates_with_actions(date_as_integer, through_date_as_integer)
    if positive_value_exists(date_as_integer_results['date_as_integer_list_found']):
        date_as_integer_list = date_as_integer_results['date_as_integer_list']

    sitewide_daily_metrics_saved_count = 0
    for one_date_as_integer in date_as_integer_list:
        results = calculate_sitewide_daily_metrics(one_date_as_integer)
        status += results['status']
        if positive_value_exists(results['success']):
            sitewide_daily_metrics_values = results['sitewide_daily_metrics_values']

            analytics_manager = AnalyticsManager()
            update_results = analytics_manager.save_sitewide_daily_metrics_values(sitewide_daily_metrics_values)
            status += update_results['status']
            if positive_value_exists(update_results['success']):
                sitewide_daily_metrics_saved_count += 1
            else:
                status += "SAVE_SITEWIDE_DAILY_METRICS-FAILED_TO_SAVE "
                success = False
        else:
            status += "SAVE_SITEWIDE_DAILY_METRICS-FAILED_TO_CALCULATE "

    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_daily_metrics_saved_count':   sitewide_daily_metrics_saved_count,
    }
    return results


def save_sitewide_election_metrics(google_civic_election_id):
    status = ""
    success = False

    results = calculate_sitewide_election_metrics(google_civic_election_id)
    status += results['status']
    if results['success']:
        sitewide_election_metrics_values = results['sitewide_election_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = \
            analytics_manager.save_sitewide_election_metrics_values(sitewide_election_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def save_sitewide_voter_metrics(look_for_changes_since_this_date_as_integer, through_date_as_integer):
    status = ""
    success = True
    last_calculated_date_as_integer = 0
    sitewide_voter_metrics_updated = 0
    voter_we_vote_id_list = []
    voter_we_vote_id_list_found = False

    analytics_manager = AnalyticsManager()
    voter_list_results = analytics_manager.retrieve_voter_we_vote_id_list_with_changes_since(
        look_for_changes_since_this_date_as_integer, through_date_as_integer)
    if voter_list_results['voter_we_vote_id_list_found']:
        voter_we_vote_id_list = voter_list_results['voter_we_vote_id_list']
        voter_we_vote_id_list_found = True

    if positive_value_exists(voter_we_vote_id_list_found):
        # Remove the voter_we_vote_id's that have been updated already today
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        day_as_string = "{:d}{:02d}{:02d}".format(
            datetime_now.year,
            datetime_now.month,
            datetime_now.day,
        )
        last_calculated_date_as_integer = convert_to_int(day_as_string)
        updated_voter_we_vote_id_list = []
        for voter_we_vote_id in voter_we_vote_id_list:
            if analytics_manager.sitewide_voter_metrics_for_this_voter_updated_this_date(
                    voter_we_vote_id, last_calculated_date_as_integer):
                # Don't calculate metrics for this voter
                updated_today = True
                pass
            else:
                updated_voter_we_vote_id_list.append(voter_we_vote_id)
        voter_we_vote_id_list = updated_voter_we_vote_id_list
        voter_we_vote_id_list_found = positive_value_exists(len(voter_we_vote_id_list))

    if positive_value_exists(voter_we_vote_id_list_found):
        for voter_we_vote_id in voter_we_vote_id_list:
            results = calculate_sitewide_voter_metrics_for_one_voter(voter_we_vote_id)
            status += results['status']
            if positive_value_exists(results['success']):
                sitewide_voter_metrics_values = results['sitewide_voter_metrics_values']
                sitewide_voter_metrics_values['last_calculated_date_as_integer'] = last_calculated_date_as_integer

                analytics_manager = AnalyticsManager()
                update_results = analytics_manager.save_sitewide_voter_metrics_values_for_one_voter(
                    sitewide_voter_metrics_values)
                status += update_results['status']
                if positive_value_exists(update_results['success']):
                    sitewide_voter_metrics_updated += 1
                else:
                    status += "SAVE_SITEWIDE_VOTER_METRICS-FAILED_TO_SAVE "
                    success = False
                    print_to_log(logger=logger, exception_message_optional=status)
            else:
                # So we can set a breakpoint in case of problems
                status += "SAVE_SITEWIDE_VOTER_METRICS-FAILED_TO_CALCULATE "

    results = {
        'status':   status,
        'success':  success,
        'sitewide_voter_metrics_updated': sitewide_voter_metrics_updated,
    }
    return results
