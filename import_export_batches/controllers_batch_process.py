# import_export_batches/controllers_batch_process.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import create_batch_row_actions, import_data_from_batch_row_actions
from .controllers_representatives import process_one_representatives_batch_process
from .models import ACTIVITY_NOTICE_PROCESS, API_REFRESH_REQUEST, \
    AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID, AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT, \
    BatchDescription, BatchManager, BatchProcessManager, \
    CALCULATE_ORGANIZATION_DAILY_METRICS, \
    CALCULATE_ORGANIZATION_ELECTION_METRICS, \
    CALCULATE_SITEWIDE_DAILY_METRICS, \
    CALCULATE_SITEWIDE_ELECTION_METRICS, \
    CALCULATE_SITEWIDE_VOTER_METRICS, \
    GENERATE_VOTER_GUIDES, IMPORT_CREATE, IMPORT_DELETE, \
    RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, \
    RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS, \
    SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE, UPDATE_TWITTER_DATA_FROM_TWITTER
from activity.controllers import process_activity_notice_seeds_triggered_by_batch_process
from analytics.controllers import calculate_sitewide_daily_metrics, \
    process_one_analytics_batch_process_augment_with_election_id, \
    process_one_analytics_batch_process_augment_with_first_visit, process_sitewide_voter_metrics, \
    retrieve_analytics_processing_next_step
from analytics.models import AnalyticsManager
from api_internal_cache.models import ApiInternalCacheManager
from ballot.models import BallotReturnedListManager
from candidate.models import CandidateListManager
from datetime import timedelta
from django.db.models import Q
from django.utils.timezone import localtime, now
from election.models import ElectionManager
from exception.models import handle_exception
from import_export_twitter.controllers import fetch_number_of_candidates_needing_twitter_search, \
    fetch_number_of_candidates_needing_twitter_update, fetch_number_of_organizations_needing_twitter_update, \
    fetch_number_of_representatives_needing_twitter_update, \
    retrieve_and_update_candidates_needing_twitter_update, retrieve_and_update_organizations_needing_twitter_update, \
    retrieve_and_update_representatives_needing_twitter_update, retrieve_possible_twitter_handles_in_bulk
from issue.controllers import update_issue_statistics
import json
from position.models import PositionEntered
from voter_guide.controllers import voter_guides_upcoming_retrieve_for_api
from voter_guide.models import VoterGuideManager, VoterGuidesGenerated
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_batch_process_system_on, fetch_batch_process_system_activity_notices_on, \
    fetch_batch_process_system_api_refresh_on, fetch_batch_process_system_ballot_items_on, \
    fetch_batch_process_system_representatives_on, fetch_batch_process_system_calculate_analytics_on, \
    fetch_batch_process_system_search_twitter_on, \
    fetch_batch_process_system_generate_voter_guides_on, fetch_batch_process_system_update_twitter_on

logger = wevote_functions.admin.get_logger(__name__)

CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
OFFICE_HELD = 'OFFICE_HELD'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'

# Note that as of Sept 2020 we are running 6 API servers. Each API server can be running up to
#  7 processes simultaneously. Since each new batch processes could be started on any of these 6 servers,
#  in the worst case, all of these NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES processes could get bunched up
#  on only one server. Since incoming API calls might get routed to the API server with the bunched up processes,
#  we could see voter-driven API calls rejected. That is why we keep the NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES
#  relatively low.
NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES = 4  # Four processes at a time
NUMBER_OF_SIMULTANEOUS_BALLOT_ITEM_BATCH_PROCESSES = 4  # Four processes at a time
NUMBER_OF_SIMULTANEOUS_GENERAL_MAINTENANCE_BATCH_PROCESSES = 1
NUMBER_OF_SIMULTANEOUS_REPRESENTATIVE_BATCH_PROCESSES = 1  # One processes at a time because of rate limiting


def pass_through_batch_list_incoming_variables(request):
    batch_process_search = request.GET.get('batch_process_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    # ACTIVITY_NOTICE_PROCESS, API_REFRESH_REQUEST, BALLOT_ITEMS, SEARCH_TWITTER
    kind_of_process = request.GET.get('kind_of_process', '')
    kind_of_processes_to_show = request.GET.get('kind_of_processes_to_show', '')
    show_checked_out_processes_only = request.GET.get('show_checked_out_processes_only', '')
    show_active_processes_only = request.GET.get('show_active_processes_only', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_paused_processes_only = request.GET.get('show_paused_processes_only', '')
    include_frequent_processes = request.GET.get('include_frequent_processes', '')

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&batch_process_search=" + str(batch_process_search) + \
                    "&kind_of_processes_to_show=" + str(kind_of_processes_to_show) + \
                    "&show_active_processes_only=" + str(show_active_processes_only) + \
                    "&show_all_elections=" + str(show_all_elections) + \
                    "&show_checked_out_processes_only=" + str(show_checked_out_processes_only) + \
                    "&show_paused_processes_only=" + str(show_paused_processes_only) + \
                    "&state_code=" + str(state_code) + \
                    "&include_frequent_processes=" + str(include_frequent_processes)
    return url_variables


def process_next_activity_notices():
    success = True
    status = ""
    batch_process_manager = BatchProcessManager()

    activity_notice_kind_of_processes = [ACTIVITY_NOTICE_PROCESS]

    if not fetch_batch_process_system_on():
        status += "BATCH_PROCESS_SYSTEM_TURNED_OFF-ACTIVITY_NOTICES "
        results = {
            'success': success,
            'status': status,
        }
        return results

    if not fetch_batch_process_system_activity_notices_on():
        status += "BATCH_PROCESS_SYSTEM_ACTIVITY_NOTICES_TURNED_OFF "
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve list of all active ActivityNotice BatchProcess so we can decide what new batches to schedule
    #  NOTE: We do not run directly from this list below
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=activity_notice_kind_of_processes,
        process_needs_to_be_run=True,
        for_upcoming_elections=False)
    if not positive_value_exists(results['success']):
        success = False
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results

    # We only want to process one batch_process at a time. The next time this script runs, the next one will be
    # picked up and processed.
    batch_process_list_already_in_queue = []
    if positive_value_exists(results['batch_process_list_found']):
        batch_process_list_already_in_queue = results['batch_process_list']

    status += "BATCH_PROCESSES_ALREADY_IN_QUEUED: " + str(len(batch_process_list_already_in_queue)) + ", "

    # ##################################
    # Generate or Update ActivityNotice entries from ActivityNoticeSeed entries
    # We only want one API Refresh process to be running at a time
    # Check to see if one of the existing batches is for API Refresh. If so, skip creating a new one.
    activity_notice_process_is_already_in_queue = False
    for batch_process in batch_process_list_already_in_queue:
        if batch_process.kind_of_process in activity_notice_kind_of_processes:
            activity_notice_process_is_already_in_queue = True
    if not activity_notice_process_is_already_in_queue:
        activity_notice_process_is_currently_running = \
            batch_process_manager.is_activity_notice_process_currently_running()
        if not activity_notice_process_is_currently_running:
            results = batch_process_manager.create_batch_process(
                kind_of_process=ACTIVITY_NOTICE_PROCESS)
            status += results['status']
            success = results['success']
            if results['success']:
                batch_process = results['batch_process']
                status += "SCHEDULED_ACTIVITY_NOTICE_PROCESS "
                # batch_process_manager.create_batch_process_log_entry(
                #     batch_process_id=batch_process.id,
                #     kind_of_process=batch_process.kind_of_process,
                #     status=status,
                # )
            else:
                status += "FAILED_TO_SCHEDULE-" + str(ACTIVITY_NOTICE_PROCESS) + " "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=0,
                    kind_of_process=ACTIVITY_NOTICE_PROCESS,
                    status=status,
                )

    # Finally, retrieve the ActivityNotice BatchProcess to run, and only use the first one returned
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=activity_notice_kind_of_processes,
        process_needs_to_be_run=True,
        for_upcoming_elections=False)
    if not positive_value_exists(results['success']):
        success = False
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results

    batch_process = None
    batch_process_found = False
    batch_process_full_list = []
    if positive_value_exists(results['batch_process_list_found']):
        batch_process_found = True
        batch_process_full_list = results['batch_process_list']
        # Only use the first one
        batch_process = batch_process_full_list[0]
    status += "BATCH_PROCESS_LIST_NEEDS_TO_BE_RUN_ACTIVITY_NOTICES_COUNT: " + str(len(batch_process_full_list)) + ", "

    # We should only run one per minute
    if batch_process_found:
        if batch_process.kind_of_process in [ACTIVITY_NOTICE_PROCESS]:
            results = process_activity_notice_batch_process(batch_process)
            status += results['status']
        else:
            status += "KIND_OF_PROCESS_NOT_RECOGNIZED "
            try:
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    kind_of_process=batch_process.kind_of_process,
                    status=status,
                )
            except Exception as e:
                pass

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_next_ballot_items():
    success = True
    status = ""

    if not fetch_batch_process_system_on():
        status += "BATCH_PROCESS_SYSTEM_TURNED_OFF-BALLOT_ITEMS "
        results = {
            'success': success,
            'status': status,
        }
        return results

    if not fetch_batch_process_system_ballot_items_on():
        status += "BATCH_PROCESS_SYSTEM_BALLOT_ITEMS_TURNED_OFF "
        results = {
            'success': success,
            'status': status,
        }
        return results

    batch_process_manager = BatchProcessManager()
    # If we have more than NUMBER_OF_SIMULTANEOUS_BALLOT_ITEM_BATCH_PROCESSES batch_processes that are still active,
    # don't start a new import ballot item batch_process
    ballot_item_kind_of_processes = [
        REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS,
        REFRESH_BALLOT_ITEMS_FROM_VOTERS,
        RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]

    # Retrieve list of all ballot item BatchProcesses which have been started but not completed, so we can decide
    #  our next steps
    # TODO: This logic needs to be looked at. How do we know this batch isn't already running on another process?
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=ballot_item_kind_of_processes,
        process_active=True,
        for_upcoming_elections=True)
    if not positive_value_exists(results['success']):
        success = False
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Note this batch_process_list does not included checked out items that haven't timed out
    #  These are all batch processes that need to be worked on
    batch_process_list = []
    if positive_value_exists(results['batch_process_list_found']):
        batch_process_list = results['batch_process_list']
    status += "BATCH_PROCESSES_TO_BE_RESTARTED: " + str(len(batch_process_list)) + ", "

    # If there are any started processes that are not currently checked out, or checked out but timed out
    process_restarted = False
    if batch_process_list and len(batch_process_list) > 0:
        for batch_process in batch_process_list:
            if batch_process.kind_of_process in \
                    [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
                     RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]:
                process_restarted = True
                # When a batch_process is running, we set date_checked_out to show it is being worked on
                results = process_one_ballot_item_batch_process(batch_process)
                status += results['status']
                # Now that the process is complete, we reset date_checked_out to "NULL"
                try:
                    # Before saving batch_process, make sure we have the latest version, since there were
                    #  updates in process_one_ballot_item_batch_process
                    batch_process_results = \
                        batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
                    if positive_value_exists(batch_process_results['batch_process_found']):
                        batch_process = batch_process_results['batch_process']
                    batch_process.date_checked_out = None
                    batch_process.save()
                except Exception as e:
                    status += "ERROR-COULD_NOT_SET_CHECKED_OUT_TIME_TO_NULL: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        google_civic_election_id=batch_process.google_civic_election_id,
                        kind_of_process=batch_process.kind_of_process,
                        state_code=batch_process.state_code,
                        status=status,
                    )
            else:
                status += "KIND_OF_PROCESS_NOT_RECOGNIZED "

    # If a process was started immediately above, exit
    if process_restarted:
        status += "BATCH_PROCESS_STARTED_PREVIOUSLY_WAS_RESTARTED "
        results = {
            'success': success,
            'status': status,
        }
        return results

    # ############################
    # Processing Ballot Items
    results = batch_process_manager.count_next_steps(
        kind_of_process_list=ballot_item_kind_of_processes,
        is_active=True)
    if not results['success']:
        # Exit out -- we have database problem
        status += "PROBLEM_COUNTING_BATCH_PROCESSES-RUNNING: "
        status += results['status']
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results
    batch_processes_running_count = results['batch_process_count']
    status += "BATCH_PROCESSES_RUNNING_COUNT: " + str(batch_processes_running_count) + ", "

    # If less than NUMBER_OF_SIMULTANEOUS_BALLOT_ITEM_BATCH_PROCESSES total active processes,
    #  then add a new batch_process (importing ballot items) to the current queue
    if batch_processes_running_count < NUMBER_OF_SIMULTANEOUS_BALLOT_ITEM_BATCH_PROCESSES:
        results = batch_process_manager.retrieve_batch_process_list(
            kind_of_process_list=ballot_item_kind_of_processes,
            process_active=False,
            process_queued=True,
            for_upcoming_elections=True)
        if not positive_value_exists(results['success']):
            success = False
            batch_process_manager.create_batch_process_log_entry(
                critical_failure=True,
                status=results['status'],
            )
            status += results['status']
            results = {
                'success': success,
                'status': status,
            }
            return results

        if positive_value_exists(results['batch_process_list_found']):
            new_batch_process_list = results['batch_process_list']
            new_batch_process_list_count = len(new_batch_process_list)
            status += "NEW_BATCH_PROCESS_LIST_COUNT: " + str(new_batch_process_list_count) + ", ADDING ONE "
            for batch_process in new_batch_process_list:
                # Bring the batch_process_list up by 1 item
                batch_process_started = False
                kind_of_process = ""
                try:
                    kind_of_process = batch_process.kind_of_process
                    batch_process.date_started = now()
                    batch_process.save()
                    batch_process_started = True
                except Exception as e:
                    status += "ERROR-BATCH_PROCESS-CANNOT_SAVE_DATE_STARTED: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=kind_of_process,
                        status=status,
                    )

                if batch_process_started:
                    if batch_process.kind_of_process in \
                            [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
                             RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]:
                        # Now process the batch
                        results = process_one_ballot_item_batch_process(batch_process)
                        status += results['status']

                        # Before a batch_process runs, we set `date_checked_out`, like you check out a library book
                        #  When the process is complete, we reset `date_checked_out` to "NULL"
                        try:
                            # Before saving batch_process, make sure we have the latest version.
                            # (For example, it might have been paused since it was first retrieved.)
                            batch_process_results = \
                                batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
                            if positive_value_exists(batch_process_results['batch_process_found']):
                                batch_process = batch_process_results['batch_process']

                            batch_process.date_checked_out = None
                            batch_process.save()
                        except Exception as e:
                            status += "ERROR-COULD_NOT_SET_CHECKED_OUT_TIME_TO_NULL: " + str(e) + " "
                            handle_exception(e, logger=logger, exception_message=status)
                            batch_process_manager.create_batch_process_log_entry(
                                batch_process_id=batch_process.id,
                                google_civic_election_id=batch_process.google_civic_election_id,
                                kind_of_process=batch_process.kind_of_process,
                                state_code=batch_process.state_code,
                                status=status,
                            )
                    else:
                        status += "KIND_OF_PROCESS_NOT_RECOGNIZED "

                break

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_next_general_maintenance():
    success = True
    status = ""
    batch_process_manager = BatchProcessManager()

    # Only include the processes if the process system is turned on
    kind_of_processes_to_run = []
    if fetch_batch_process_system_api_refresh_on():
        api_refresh_process_list = [API_REFRESH_REQUEST]
        kind_of_processes_to_run = kind_of_processes_to_run + api_refresh_process_list
    if fetch_batch_process_system_calculate_analytics_on():
        analytics_process_list = [
            AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID,
            AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT,
            CALCULATE_SITEWIDE_VOTER_METRICS,
            CALCULATE_SITEWIDE_DAILY_METRICS,
            CALCULATE_SITEWIDE_ELECTION_METRICS,
            CALCULATE_ORGANIZATION_DAILY_METRICS,
            CALCULATE_ORGANIZATION_ELECTION_METRICS]
        kind_of_processes_to_run = kind_of_processes_to_run + analytics_process_list
    if fetch_batch_process_system_generate_voter_guides_on():
        generate_voter_guides_process_list = [GENERATE_VOTER_GUIDES]
        kind_of_processes_to_run = kind_of_processes_to_run + generate_voter_guides_process_list
    if fetch_batch_process_system_search_twitter_on():
        search_twitter_process_list = [SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE]
        kind_of_processes_to_run = kind_of_processes_to_run + search_twitter_process_list
    if fetch_batch_process_system_update_twitter_on():
        update_twitter_process_list = [UPDATE_TWITTER_DATA_FROM_TWITTER]
        kind_of_processes_to_run = kind_of_processes_to_run + update_twitter_process_list

    if not fetch_batch_process_system_on():
        status += "BATCH_PROCESS_SYSTEM_TURNED_OFF-GENERAL "
        results = {
            'success': success,
            'status': status,
        }
        return results

    if not positive_value_exists(len(kind_of_processes_to_run)):
        status += "ALL_BATCH_PROCESS_SYSTEM_KINDS_TURNED_OFF "
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve list of all General Maintenance BatchProcess scheduled or running
    #  NOTE: We do not run directly from this list below
    batch_process_list_already_scheduled = []
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=kind_of_processes_to_run,
        process_needs_to_be_run=True,
        for_upcoming_elections=True)
    if not positive_value_exists(results['success']):
        success = False
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results
    elif positive_value_exists(results['batch_process_list_found']):
        batch_process_list_already_scheduled = results['batch_process_list']
    status += "BATCH_PROCESSES_ALREADY_SCHEDULED: " + str(len(batch_process_list_already_scheduled)) + ", "

    batch_process_list_already_running = []
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=kind_of_processes_to_run,
        process_active=True,
        for_upcoming_elections=False)
    if not positive_value_exists(results['success']):
        success = False
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results
    elif positive_value_exists(results['batch_process_list_found']):
        batch_process_list_already_running = results['batch_process_list']
    status += "BATCH_PROCESSES_ALREADY_RUNNING: " + str(len(batch_process_list_already_running)) + ", "

    # ############################
    # Are there any API's that need to have their internal cache updated?
    if not fetch_batch_process_system_api_refresh_on():
        status += "BATCH_PROCESS_SYSTEM_API_REFRESH_TURNED_OFF "
    else:
        # We only want one API Refresh process to be running at a time
        # Check to see if one of the existing batches is for API Refresh. If so, skip creating a new one.
        api_refresh_process_is_already_in_queue = False
        for batch_process in batch_process_list_already_scheduled:
            if batch_process.kind_of_process in [API_REFRESH_REQUEST]:
                api_refresh_process_is_already_in_queue = True
        for batch_process in batch_process_list_already_running:
            if batch_process.kind_of_process in [API_REFRESH_REQUEST]:
                api_refresh_process_is_already_in_queue = True
        if not api_refresh_process_is_already_in_queue:
            api_internal_cache_manager = ApiInternalCacheManager()
            results = api_internal_cache_manager.retrieve_next_api_refresh_request()
            if positive_value_exists(results['api_refresh_request_found']):
                api_refresh_request = results['api_refresh_request']
                results = batch_process_manager.create_batch_process(
                    kind_of_process=API_REFRESH_REQUEST,
                    api_name=api_refresh_request.api_name,
                    election_id_list_serialized=api_refresh_request.election_id_list_serialized)
                status += results['status']
                success = results['success']
                if results['batch_process_saved']:
                    batch_process = results['batch_process']
                    status += "SCHEDULED_API_REFRESH_REQUEST "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=batch_process.kind_of_process,
                        status=status,
                    )

                    # Now mark api_refresh_request as checked out
                    try:
                        api_refresh_request.date_checked_out = now()
                        api_refresh_request.save()
                    except Exception as e:
                        status += "ERROR-COULD_NOT_MARK_API_REFRESH_REQUEST_WITH_DATE_CHECKED_OUT: " + str(e) + " "
                else:
                    status += "FAILED_TO_SCHEDULE-" + str(API_REFRESH_REQUEST) + " "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=0,
                        kind_of_process=API_REFRESH_REQUEST,
                        status=status,
                    )

    # ############################
    # Generate voter guides - make sure we have a voter guide for every Organization + Election pair
    #  if an endorsement has been added since the last voter guides were generated
    if not fetch_batch_process_system_generate_voter_guides_on():
        status += "BATCH_PROCESS_SYSTEM_GENERATE_VOTER_GUIDES_TURNED_OFF "
    else:
        # We only want one GENERATE_VOTER_GUIDES process to be running at a time
        generate_voter_guides_process_is_already_in_queue = False
        for batch_process in batch_process_list_already_scheduled:
            if batch_process.kind_of_process in [GENERATE_VOTER_GUIDES]:
                status += "GENERATE_VOTER_GUIDES_ALREADY_SCHEDULED(" + str(batch_process.id) + ") "
                generate_voter_guides_process_is_already_in_queue = True
        for batch_process in batch_process_list_already_running:
            if batch_process.kind_of_process in [GENERATE_VOTER_GUIDES]:
                status += "GENERATE_VOTER_GUIDES_ALREADY_RUNNING(" + str(batch_process.id) + ") "
                generate_voter_guides_process_is_already_in_queue = True
        if generate_voter_guides_process_is_already_in_queue:
            pass
        else:
            # Get list of upcoming elections we should generate voter guides for (minus those already generated)
            election_ids_that_need_voter_guides_generated = []
            election_manager = ElectionManager()
            results = election_manager.retrieve_upcoming_google_civic_election_id_list()
            if results['upcoming_google_civic_election_id_list_found']:
                upcoming_google_civic_election_id_list = results['upcoming_google_civic_election_id_list']
                # Make sure they are all integer
                upcoming_google_civic_election_id_list_converted = []
                for one_google_civic_election_id in upcoming_google_civic_election_id_list:
                    upcoming_google_civic_election_id_list_converted\
                        .append(convert_to_int(one_google_civic_election_id))
                upcoming_google_civic_election_id_list = upcoming_google_civic_election_id_list_converted
                if positive_value_exists(len(upcoming_google_civic_election_id_list)):
                    # Get list of elections we have generated voter guides for in the last 24 hours (so we can remove)
                    time_threshold = localtime(now() - timedelta(hours=24)).date()  # Pacific Time for TIME_ZONE
                    query = VoterGuidesGenerated.objects.using('readonly').all()
                    query = query.filter(date_last_changed__gte=time_threshold)
                    election_ids_already_generated_list = query.values_list('google_civic_election_id',
                                                                            flat=True).distinct()

                    if positive_value_exists(len(election_ids_already_generated_list)):
                        election_ids_that_need_voter_guides_generated = \
                            list(set(upcoming_google_civic_election_id_list) - set(election_ids_already_generated_list))
                    else:
                        election_ids_that_need_voter_guides_generated = upcoming_google_civic_election_id_list

            if positive_value_exists(len(election_ids_that_need_voter_guides_generated)):
                first_election_id = election_ids_that_need_voter_guides_generated[0]
                status += "CREATING_GENERATE_VOTER_GUIDES_BATCH_PROCESS_FOR_ELECTION-" + str(first_election_id) + " "
                results = batch_process_manager.create_batch_process(
                    google_civic_election_id=first_election_id,
                    kind_of_process=GENERATE_VOTER_GUIDES)
                status += results['status']
                success = results['success']
                if results['batch_process_saved']:
                    batch_process = results['batch_process']
                    status += "SCHEDULED_NEW_GENERATE_VOTER_GUIDES "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=batch_process.kind_of_process,
                        google_civic_election_id=batch_process.google_civic_election_id,
                        status=status,
                    )
                else:
                    status += "FAILED_TO_SCHEDULE-" + str(GENERATE_VOTER_GUIDES) + " "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=0,
                        kind_of_process=GENERATE_VOTER_GUIDES,
                        google_civic_election_id=first_election_id,
                        status=status,
                    )

    # ############################
    # Twitter Search - Possible Twitter Handle Matches
    if not fetch_batch_process_system_search_twitter_on():
        status += "BATCH_PROCESS_SYSTEM_SEARCH_TWITTER_TURNED_OFF "
    else:
        # We only want one SEARCH_TWITTER process to be running at a time
        # Check to see if one of the existing batches is for SEARCH_TWITTER. If so, skip creating a new one.
        search_twitter_process_is_already_in_queue = False
        for batch_process in batch_process_list_already_scheduled:
            if batch_process.kind_of_process in [SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE]:
                status += "SEARCH_TWITTER_ALREADY_SCHEDULED(" + str(batch_process.id) + ") "
                search_twitter_process_is_already_in_queue = True
        for batch_process in batch_process_list_already_running:
            if batch_process.kind_of_process in [SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE]:
                status += "SEARCH_TWITTER_ALREADY_RUNNING(" + str(batch_process.id) + ") "
                search_twitter_process_is_already_in_queue = True
        if search_twitter_process_is_already_in_queue:
            pass  # See SEARCH_TWITTER_TIMED_OUT
            # status += "DO_NOT_CREATE_SEARCH_TWITTER-ALREADY_RUNNING "
            # batch_process_manager.create_batch_process_log_entry(
            #     batch_process_id=local_batch_process_id,
            #     kind_of_process=SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE,
            #     status=status,
            # )
        else:
            number_of_candidates_to_analyze = fetch_number_of_candidates_needing_twitter_search()
            if positive_value_exists(number_of_candidates_to_analyze):
                results = batch_process_manager.create_batch_process(
                    kind_of_process=SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE)
                status += results['status']
                success = results['success']
                if results['batch_process_saved']:
                    batch_process = results['batch_process']
                    status += "SCHEDULED_NEW_SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=batch_process.kind_of_process,
                        status=status,
                    )
                else:
                    status += "FAILED_TO_SCHEDULE-" + str(SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE) + " "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=0,
                        kind_of_process=SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE,
                        status=status,
                    )

    # ############################
    # Twitter Update Data from Twitter
    if not fetch_batch_process_system_update_twitter_on():
        status += "BATCH_PROCESS_SYSTEM_UPDATE_TWITTER_TURNED_OFF "
    else:
        # We only want one UPDATE_TWITTER process to be running at a time
        # Check to see if one of the existing batches is for UPDATE_TWITTER. If so, skip creating a new one.
        local_batch_process_id = 0
        update_twitter_process_is_already_in_queue = False
        for batch_process in batch_process_list_already_scheduled:
            if batch_process.kind_of_process in [UPDATE_TWITTER_DATA_FROM_TWITTER]:
                local_batch_process_id = batch_process.id
                status += "DO_NOT_CREATE_UPDATE_TWITTER-ALREADY_SCHEDULED(" + str(batch_process.id) + ") "
                update_twitter_process_is_already_in_queue = True
        for batch_process in batch_process_list_already_running:
            if batch_process.kind_of_process in [UPDATE_TWITTER_DATA_FROM_TWITTER]:
                local_batch_process_id = batch_process.id
                status += "DO_NOT_CREATE_UPDATE_TWITTER_ALREADY_RUNNING(" + str(batch_process.id) + ") "
                update_twitter_process_is_already_in_queue = True

        if update_twitter_process_is_already_in_queue:  # See UPDATE_TWITTER_TIMED_OUT
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=local_batch_process_id,
                kind_of_process=UPDATE_TWITTER_DATA_FROM_TWITTER,
                status=status,
            )
        else:
            number_of_candidates_to_analyze = fetch_number_of_candidates_needing_twitter_update()
            number_of_organizations_to_analyze = 0
            number_of_representatives_to_analyze = 0
            if positive_value_exists(number_of_candidates_to_analyze):
                status += "CANDIDATES_NEED_TWITTER_UPDATE "
            else:
                number_of_representatives_to_analyze = fetch_number_of_representatives_needing_twitter_update()
                if positive_value_exists(number_of_representatives_to_analyze):
                    status += "REPRESENTATIVES_NEED_TWITTER_UPDATE "
                else:
                    number_of_organizations_to_analyze = fetch_number_of_organizations_needing_twitter_update()
                    if positive_value_exists(number_of_organizations_to_analyze):
                        status += "ORGANIZATIONS_NEED_TWITTER_UPDATE "
            if positive_value_exists(number_of_candidates_to_analyze) \
                    or positive_value_exists(number_of_organizations_to_analyze) \
                    or positive_value_exists(number_of_representatives_to_analyze):
                results = batch_process_manager.create_batch_process(
                    kind_of_process=UPDATE_TWITTER_DATA_FROM_TWITTER)
                status += results['status']
                success = results['success']
                if results['batch_process_saved']:
                    batch_process = results['batch_process']
                    status += "SCHEDULED_NEW_UPDATE_TWITTER_DATA_FROM_TWITTER "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=batch_process.kind_of_process,
                        status=status,
                    )
                else:
                    status += "FAILED_TO_SCHEDULE-" + str(UPDATE_TWITTER_DATA_FROM_TWITTER) + " "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=0,
                        kind_of_process=UPDATE_TWITTER_DATA_FROM_TWITTER,
                        status=status,
                    )

    # ############################
    # Processing Analytics - Generate Next BatchProcess to run
    if not fetch_batch_process_system_calculate_analytics_on():
        status += "BATCH_PROCESS_SYSTEM_CALCULATE_ANALYTICS_TURNED_OFF "
    else:
        # We only want one analytics process to be running at a time
        # Check to see if one of the existing batches is for analytics. If so,
        analytics_process_is_already_in_queue = False
        for batch_process in batch_process_list_already_running:
            if batch_process.kind_of_process in [
                    AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID, AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT,
                    CALCULATE_ORGANIZATION_DAILY_METRICS, CALCULATE_ORGANIZATION_ELECTION_METRICS,
                    CALCULATE_SITEWIDE_ELECTION_METRICS, CALCULATE_SITEWIDE_VOTER_METRICS]:
                analytics_process_is_already_in_queue = True

        if not analytics_process_is_already_in_queue:
            analytics_process_is_currently_running = batch_process_manager.is_analytics_process_currently_running()
            if not analytics_process_is_currently_running:
                analytics_processing_status = retrieve_analytics_processing_next_step()
                kind_of_process = None
                analytics_date_as_integer = 0
                status += analytics_processing_status['status']
                if not analytics_processing_status['success']:
                    status += "FAILURE_TRYING_TO_RETRIEVE_ANALYTICS_PROCESSING_NEXT_STEP "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=0,
                        kind_of_process=kind_of_process,
                        status=status,
                    )
                elif analytics_processing_status['analytics_processing_status_found']:
                    analytics_date_as_integer = analytics_processing_status['analytics_date_as_integer']
                    if analytics_processing_status['augment_analytics_action_with_election_id']:
                        kind_of_process = AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID
                    elif analytics_processing_status['augment_analytics_action_with_first_visit']:
                        kind_of_process = AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT
                    elif analytics_processing_status['calculate_sitewide_voter_metrics']:
                        kind_of_process = CALCULATE_SITEWIDE_VOTER_METRICS
                    elif analytics_processing_status['calculate_sitewide_daily_metrics']:
                        kind_of_process = CALCULATE_SITEWIDE_DAILY_METRICS
                    elif analytics_processing_status['calculate_sitewide_election_metrics']:
                        kind_of_process = CALCULATE_SITEWIDE_ELECTION_METRICS
                    elif analytics_processing_status['calculate_organization_daily_metrics']:
                        kind_of_process = CALCULATE_ORGANIZATION_DAILY_METRICS
                    elif analytics_processing_status['calculate_organization_election_metrics']:
                        kind_of_process = CALCULATE_ORGANIZATION_ELECTION_METRICS
                if kind_of_process:
                    results = batch_process_manager.create_batch_process(
                        kind_of_process=kind_of_process,
                        analytics_date_as_integer=analytics_date_as_integer)
                    status += results['status']
                    success = results['success']
                    if results['batch_process_saved']:
                        batch_process = results['batch_process']
                        try:
                            batch_process.date_started = now()
                            batch_process.save()
                            status += "SCHEDULED_PROCESS: " + str(kind_of_process) + " "
                            batch_process_manager.create_batch_process_log_entry(
                                batch_process_id=batch_process.id,
                                kind_of_process=batch_process.kind_of_process,
                                status=status,
                            )
                        except Exception as e:
                            status += "ERROR-BATCH_PROCESS_ANALYTICS-CANNOT_SAVE_DATE_STARTED: " + str(e) + " "
                            handle_exception(e, logger=logger, exception_message=status)
                            batch_process_manager.create_batch_process_log_entry(
                                batch_process_id=batch_process.id,
                                kind_of_process=kind_of_process,
                                status=status,
                            )
                    else:
                        status += "FAILED_TO_SCHEDULE-" + str(kind_of_process) + " "
                        batch_process_manager.create_batch_process_log_entry(
                            batch_process_id=0,
                            kind_of_process=kind_of_process,
                            status=status,
                        )

    # Finally, retrieve the General Maintenance BatchProcess to run, and only use the first one returned
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=kind_of_processes_to_run,
        process_needs_to_be_run=True,
        for_upcoming_elections=False)
    if not positive_value_exists(results['success']):
        success = False
        status += "FAILED_TO_RETRIEVE_BATCH_PROCESS_LIST: "
        status += results['status']
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    batch_process = None
    batch_process_found = False
    batch_process_full_list = []
    if positive_value_exists(results['batch_process_list_found']):
        batch_process_found = True
        batch_process_full_list = results['batch_process_list']
        status += "KINDS_OF_BATCH_PROCESSES_IN_QUEUE: [ "
        for temp_batch in batch_process_full_list:
            if temp_batch.kind_of_process:
                status += str(temp_batch.kind_of_process) + " "
        status += "] (ONLY_USING_FIRST) "
        # Only use the first one
        batch_process = batch_process_full_list[0]
    status += "BATCH_PROCESSES_NEED_TO_BE_RUN_GENERAL_MAINT: " + str(len(batch_process_full_list)) + ", "

    # We should only start one per minute
    if batch_process_found:
        if batch_process.kind_of_process in [API_REFRESH_REQUEST]:
            results = process_one_api_refresh_request_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [
                AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID, AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT,
                CALCULATE_ORGANIZATION_DAILY_METRICS, CALCULATE_ORGANIZATION_ELECTION_METRICS,
                CALCULATE_SITEWIDE_ELECTION_METRICS, CALCULATE_SITEWIDE_VOTER_METRICS]:
            results = process_one_analytics_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [CALCULATE_SITEWIDE_DAILY_METRICS]:
            results = process_one_sitewide_daily_analytics_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [GENERATE_VOTER_GUIDES]:
            results = process_one_generate_voter_guides_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE]:
            results = process_one_search_twitter_batch_process(batch_process, status=status)
            status = results['status']  # Not additive since we pass status into function
        elif batch_process.kind_of_process in [UPDATE_TWITTER_DATA_FROM_TWITTER]:
            results = process_one_update_twitter_batch_process(batch_process, status=status)
            status = results['status']  # Not additive since we pass status into function
        else:
            status += "KIND_OF_PROCESS_NOT_RECOGNIZED "

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_next_representatives():
    success = True
    status = ""

    if not fetch_batch_process_system_on():
        status += "BATCH_PROCESS_SYSTEM_TURNED_OFF-REPRESENTATIVES "
        results = {
            'success': success,
            'status': status,
        }
        return results

    if not fetch_batch_process_system_representatives_on():
        status += "BATCH_PROCESS_SYSTEM_REPRESENTATIVES_TURNED_OFF "
        results = {
            'success': success,
            'status': status,
        }
        return results

    batch_process_manager = BatchProcessManager()
    # If we have more than NUMBER_OF_SIMULTANEOUS_REPRESENTATIVE_BATCH_PROCESSES batch_processes that are still active,
    # don't start a new import ballot item batch_process
    representatives_kind_of_processes = [RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS]

    # Retrieve list of all BatchProcess scheduled or running
    #  NOTE: We do not run directly from this list below
    batch_process_list_already_scheduled = []
    results = batch_process_manager.retrieve_batch_process_list(
        kind_of_process_list=representatives_kind_of_processes,
        process_needs_to_be_run=True,
        for_upcoming_elections=False)
    if not positive_value_exists(results['success']):
        success = False
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results
    elif positive_value_exists(results['batch_process_list_found']):
        batch_process_list_already_scheduled = results['batch_process_list']
    status += "BATCH_PROCESSES_ALREADY_SCHEDULED: " + str(len(batch_process_list_already_scheduled)) + ", "

    batch_process_list = []
    if len(batch_process_list_already_scheduled) > 0:
        batch_process_list = results['batch_process_list']
    else:
        # Retrieve list of all ballot item BatchProcesses which have been started but not completed, so we can decide
        #  our next steps
        results = batch_process_manager.retrieve_batch_process_list(
            kind_of_process_list=representatives_kind_of_processes,
            process_active=True,
            for_upcoming_elections=False)
        if not positive_value_exists(results['success']):
            success = False
            batch_process_manager.create_batch_process_log_entry(
                critical_failure=True,
                status=results['status'],
            )
            status += results['status']
            results = {
                'success': success,
                'status': status,
            }
            return results

        # Note this batch_process_list does not included checked out items that haven't timed out
        #  These are all batch processes that need to be worked on
        if positive_value_exists(results['batch_process_list_found']):
            batch_process_list = results['batch_process_list']
        status += "BATCH_PROCESSES_TO_BE_RESTARTED: " + str(len(batch_process_list)) + ", "

    # If there are any started processes that are not currently checked out, or checked out but timed out
    process_restarted = False
    if batch_process_list and len(batch_process_list) > 0:
        for batch_process in batch_process_list:
            if batch_process.kind_of_process in \
                    [RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS]:
                process_restarted = True
                # When a batch_process is running, we set date_checked_out to show it is being worked on
                results = process_one_representatives_batch_process(batch_process)
                status += results['status']
                # Now that the process is complete, we reset date_checked_out to "NULL"
                try:
                    # Before saving batch_process, make sure we have the latest version, since there were
                    #  updates in process_one_representatives_batch_process
                    batch_process_results = \
                        batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
                    if positive_value_exists(batch_process_results['batch_process_found']):
                        batch_process = batch_process_results['batch_process']
                    batch_process.date_checked_out = None
                    batch_process.save()
                except Exception as e:
                    status += "ERROR-COULD_NOT_SET_REPRESENTATIVES_CHECKED_OUT_TIME_TO_NULL: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        google_civic_election_id=batch_process.google_civic_election_id,
                        kind_of_process=batch_process.kind_of_process,
                        state_code=batch_process.state_code,
                        status=status,
                    )
            else:
                status += "KIND_OF_REPRESENTATIVES_PROCESS_NOT_RECOGNIZED1 "

    # If a process was started immediately above, exit
    if process_restarted:
        status += "BATCH_PROCESS_REPRESENTATIVES_STARTED_PREVIOUSLY_WAS_RESTARTED "
        results = {
            'success': success,
            'status': status,
        }
        return results

    # ############################
    # Processing Representatives
    results = batch_process_manager.count_next_steps(
        kind_of_process_list=representatives_kind_of_processes,
        is_active=True)
    if not results['success']:
        # Exit out -- we have database problem
        status += "PROBLEM_COUNTING_BATCH_PROCESSES_REPRESENTATIVES-RUNNING: "
        status += results['status']
        batch_process_manager.create_batch_process_log_entry(
            critical_failure=True,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results
    batch_processes_running_count = results['batch_process_count']
    status += "REPRESENTATIVE_BATCH_PROCESSES_RUNNING_COUNT: " + str(batch_processes_running_count) + ", "

    # If less than NUMBER_OF_SIMULTANEOUS_REPRESENTATIVE_BATCH_PROCESSES total active processes,
    #  then add a new batch_process (importing ballot items) to the current queue
    if batch_processes_running_count < NUMBER_OF_SIMULTANEOUS_REPRESENTATIVE_BATCH_PROCESSES:
        results = batch_process_manager.retrieve_batch_process_list(
            for_upcoming_elections=False,
            kind_of_process_list=representatives_kind_of_processes,
            process_active=False,
            process_queued=True)
        if not positive_value_exists(results['success']):
            success = False
            batch_process_manager.create_batch_process_log_entry(
                critical_failure=True,
                status=results['status'],
            )
            status += results['status']
            results = {
                'success': success,
                'status': status,
            }
            return results

        if positive_value_exists(results['batch_process_list_found']):
            new_batch_process_list = results['batch_process_list']
            new_batch_process_list_count = len(new_batch_process_list)
            status += "NEW_BATCH_PROCESS_LIST_COUNT: " + str(new_batch_process_list_count) + ", ADDING ONE REP "
            for batch_process in new_batch_process_list:
                # Bring the batch_process_list up by 1 item
                batch_process_started = False
                kind_of_process = ""
                try:
                    kind_of_process = batch_process.kind_of_process
                    batch_process.date_started = now()
                    batch_process.save()
                    batch_process_started = True
                except Exception as e:
                    status += "ERROR-BATCH_PROCESS_REPRESENTATIVES-CANNOT_SAVE_DATE_STARTED: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=kind_of_process,
                        status=status,
                    )

                if batch_process_started:
                    if batch_process.kind_of_process in [RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS]:
                        # Now process the batch
                        results = process_one_representatives_batch_process(batch_process)
                        status += results['status']

                        # Before a batch_process runs, we set `date_checked_out`, like you check out a library book
                        #  When the process is complete, we reset `date_checked_out` to "NULL"
                        try:
                            # Before saving batch_process, make sure we have the latest version.
                            # (For example, it might have been paused since it was first retrieved.)
                            batch_process_results = \
                                batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
                            if positive_value_exists(batch_process_results['batch_process_found']):
                                batch_process = batch_process_results['batch_process']

                            batch_process.date_checked_out = None
                            batch_process.save()
                        except Exception as e:
                            status += "ERROR-COULD_NOT_SET_REPRESENTATIVES_CHECKED_OUT_TIME_TO_NULL: " + str(e) + " "
                            handle_exception(e, logger=logger, exception_message=status)
                            batch_process_manager.create_batch_process_log_entry(
                                batch_process_id=batch_process.id,
                                google_civic_election_id=batch_process.google_civic_election_id,
                                kind_of_process=batch_process.kind_of_process,
                                state_code=batch_process.state_code,
                                status=status,
                            )
                    else:
                        status += "KIND_OF_REPRESENTATIVES_PROCESS_NOT_RECOGNIZED2 "

                break

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_one_analytics_batch_process(batch_process):
    from import_export_batches.models import BatchProcessManager
    batch_process_manager = BatchProcessManager()
    status = ""
    success = True

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "ERROR-ANALYTICS_BATCH-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve any existing BatchProcessAnalyticsChunk that has not completed
    # (this could include ones that haven't started yet)
    results = batch_process_manager.retrieve_analytics_action_chunk_not_completed(batch_process_id=batch_process.id)
    if not results['success']:
        status += "RETRIEVE_ANALYTICS_ACTION_CHUNK-NOT_SUCCESSFUL: "
        status += results['status']
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            analytics_date_as_integer=batch_process.analytics_date_as_integer,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results
    if results['batch_process_analytics_chunk_found']:
        batch_process_analytics_chunk = results['batch_process_analytics_chunk']
        status += "ANALYTICS_ACTION_CHUNK_FOUND "
    else:
        # We need to create a new batch_process_analytics_chunk here.
        # We don't consider a batch_process completed until
        # a batch_process_analytics_chunk reports that there are no more items retrieved
        results = batch_process_manager.create_batch_process_analytics_chunk(batch_process=batch_process)
        if results['batch_process_analytics_chunk_created']:
            batch_process_analytics_chunk = results['batch_process_analytics_chunk']
            status += "ANALYTICS_ACTION_CHUNK_CREATED "
        else:
            status += "UNABLE_TO_CREATE_ANALYTICS_CHUNK: "
            status += results['status']
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                analytics_date_as_integer=batch_process.analytics_date_as_integer,
                status=status,
            )
            status += results['status']
            results = {
                'success': success,
                'status': status,
            }
            return results

    # If the batch_process_analytics_chunk has been started but not completed, figure out how many got
    # processed before failing
    analytics_manager = AnalyticsManager()
    if batch_process_analytics_chunk.date_started is not None and batch_process_analytics_chunk.date_completed is None:
        status += "ANALYTICS_CHUNK_PREVIOUSLY_STARTED_BUT_NOT_FINISHED "
        results = analytics_manager.retrieve_analytics_processed_list(
            batch_process_id=batch_process.id,
            batch_process_analytics_chunk_id=batch_process_analytics_chunk.id)
        analytics_processed_count = 0
        if results['analytics_processed_list_found']:
            # Exclude the voters already processed for analytics_date_as_integer
            analytics_processed_list = results['analytics_processed_list']
            analytics_processed_count = len(analytics_processed_list)
        else:
            status += results['status']
        try:
            batch_process_analytics_chunk.number_of_rows_successfully_reviewed = analytics_processed_count
            batch_process_analytics_chunk.timed_out = True
            batch_process_analytics_chunk.date_completed = now()
            batch_process_analytics_chunk.save()

            status += "BATCH_PROCESS_ANALYTICS_CHUNK_TIMED_OUT, ROWS_REVIEWED: " + str(analytics_processed_count) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "ERROR-BATCH_PROCESS_ANALYTICS_CHUNK_TIMED_OUT-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

        # Now free up the batch_process to process in the next loop
        try:
            # Before saving batch_process, make sure we have the latest version. (For example, it might have been
            #  paused since it was first retrieved.)
            batch_process_results = \
                batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
            if positive_value_exists(batch_process_results['batch_process_found']):
                batch_process = batch_process_results['batch_process']

            batch_process.date_checked_out = None
            batch_process.save()
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        except Exception as e:
            status += "ERROR-TIMED_OUT-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

    try:
        batch_process_analytics_chunk.date_started = now()
        batch_process_analytics_chunk.save()
    except Exception as e:
        status += "ERROR-ANALYTICS_CHUNK_DATE_STARTED_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    mark_as_completed = False
    if batch_process.kind_of_process in [AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID]:
        results = process_one_analytics_batch_process_augment_with_election_id(
            batch_process, batch_process_analytics_chunk)
        status += results['status']
    elif batch_process.kind_of_process in [AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT]:
        results = process_one_analytics_batch_process_augment_with_first_visit(
            batch_process, batch_process_analytics_chunk)
        status += results['status']
    elif batch_process.kind_of_process in [CALCULATE_SITEWIDE_VOTER_METRICS]:
        results = process_sitewide_voter_metrics(batch_process, batch_process_analytics_chunk)
        status += results['status']
    # elif batch_process.kind_of_process in [CALCULATE_SITEWIDE_DAILY_METRICS]:
    #     # Should not be here
    #     pass
    elif batch_process.kind_of_process in [CALCULATE_SITEWIDE_ELECTION_METRICS]:
        # Not implemented yet -- mark as completed
        mark_as_completed = True
    elif batch_process.kind_of_process in [CALCULATE_ORGANIZATION_DAILY_METRICS]:
        # Not implemented yet -- mark as completed
        mark_as_completed = True
    elif batch_process.kind_of_process in [CALCULATE_ORGANIZATION_ELECTION_METRICS]:
        # Not implemented yet -- mark as completed
        mark_as_completed = True
    else:
        status += "MISSING_KIND_OF_PROCESS "

    try:
        # Before saving batch_process as completed, make sure we have the latest version.
        #  (For example, it might have been paused since it was first retrieved.)
        batch_process_results = \
            batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
        if positive_value_exists(batch_process_results['batch_process_found']):
            batch_process = batch_process_results['batch_process']

        if mark_as_completed:
            # Not implemented yet -- mark as completed
            batch_process.date_completed = now()
        batch_process.date_checked_out = None
        batch_process.save()
    except Exception as e:
        status += "ERROR-CHECKED_OUT_TIME_NOT_RESET: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            analytics_date_as_integer=batch_process.analytics_date_as_integer,
            status=status,
        )

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_one_api_refresh_request_batch_process(batch_process):
    status = ""
    success = True
    api_internal_cache_manager = ApiInternalCacheManager()
    batch_process_manager = BatchProcessManager()

    kind_of_process = batch_process.kind_of_process

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        batch_process.date_started = now()
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "ERROR-API_REFRESH_REQUEST-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    api_internal_cache_id = 0
    api_internal_cache_saved = False
    api_results_retrieved = False
    if batch_process.api_name == 'voterGuidesUpcoming':
        status += "STARTING_PROCESS_ONE_API_REFRESH_REQUESTED-voterGuidesUpcoming-" \
                  "(" + str(batch_process.election_id_list_serialized) + ") "
        google_civic_election_id_list = json.loads(batch_process.election_id_list_serialized)
        results = voter_guides_upcoming_retrieve_for_api(google_civic_election_id_list=google_civic_election_id_list)
        status += results['status']
        api_results_retrieved = results['success']
        json_data = results['json_data']
        if json_data['success'] and api_results_retrieved:
            # Save the json in the cache
            status += "NEW_API_RESULTS_RETRIEVED-CREATING_API_INTERNAL_CACHE "
            cached_api_response_serialized = json.dumps(json_data)
            results = api_internal_cache_manager.create_api_internal_cache(
                api_name=batch_process.api_name,
                cached_api_response_serialized=cached_api_response_serialized,
                election_id_list_serialized=batch_process.election_id_list_serialized,
            )
            status += results['status']
            api_internal_cache_saved = results['success']
            api_internal_cache_id = results['api_internal_cache_id']
        else:
            status += "NEW_API_RESULTS_RETRIEVE_FAILED "
    else:
        status += "API_NAME_NOT_RECOGNIZED: " + str(batch_process.api_name) + " "

    if api_results_retrieved and api_internal_cache_saved:
        try:
            batch_process.completion_summary = status
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "ERROR-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

        # Mark all refresh requests prior to now as satisfied
        if positive_value_exists(api_internal_cache_id):
            results = api_internal_cache_manager.mark_prior_api_internal_cache_entries_as_replaced(
                api_name=batch_process.api_name,
                election_id_list_serialized=batch_process.election_id_list_serialized,
                excluded_api_internal_cache_id=api_internal_cache_id)
            status += results['status']

        # Mark all refresh requests prior to now as satisfied
        results = api_internal_cache_manager.mark_refresh_completed_for_prior_api_refresh_requested(
            api_name=batch_process.api_name,
            election_id_list_serialized=batch_process.election_id_list_serialized)
        status += results['status']
    else:
        status += "API_REFRESH_REQUEST_FAILED "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            status=status,
        )

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_one_ballot_item_batch_process(batch_process):
    status = ""
    success = True
    batch_manager = BatchManager()
    batch_process_manager = BatchProcessManager()
    election_manager = ElectionManager()
    retrieve_time_out_duration = 20 * 60  # 20 minutes * 60 seconds
    analyze_time_out_duration = 30 * 60  # 30 minutes
    create_time_out_duration = 20 * 60  # 20 minutes

    kind_of_process = batch_process.kind_of_process
    google_civic_election_id = None
    if positive_value_exists(batch_process.google_civic_election_id):
        google_civic_election_id = batch_process.google_civic_election_id
    state_code = None
    if positive_value_exists(batch_process.state_code):
        state_code = batch_process.state_code

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        # Before saving batch_process, make sure we have the latest version. (For example, it might have been
        #  paused since it was first retrieved.)
        # DALE 2020-October after transition to three batches roots, we can get rid of retrieving this again
        batch_process_results = \
            batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
        if positive_value_exists(batch_process_results['batch_process_found']):
            batch_process = batch_process_results['batch_process']

        batch_process.date_checked_out = now()
        batch_process.save()
        batch_process_id = batch_process.id
    except Exception as e:
        status += "ERROR-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve BatchProcessBallotItemChunk that has started but not completed
    results = batch_process_manager.retrieve_active_ballot_item_chunk_not_completed(
        batch_process_id=batch_process_id)
    if not results['success']:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results
    if results['batch_process_ballot_item_chunk_found']:
        batch_process_ballot_item_chunk = results['batch_process_ballot_item_chunk']
    else:
        # We need to create a new batch_process_ballot_item_chunk here.
        # We don't consider a batch_process completed until
        # a batch_process_ballot_item_chunk reports that there are no more items retrieved
        results = \
            batch_process_manager.create_batch_process_ballot_item_chunk(batch_process_id=batch_process_id)
        if results['batch_process_ballot_item_chunk_created']:
            batch_process_ballot_item_chunk = results['batch_process_ballot_item_chunk']
        else:
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=results['status'],
            )
            status += results['status']
            results = {
                'success': success,
                'status': status,
            }
            return results

    # If here, we have a batch_process_ballot_item_chunk to work on
    if batch_process_ballot_item_chunk.retrieve_date_started is None:
        # Kick off retrieve
        retrieve_success = False
        retrieve_row_count = 0
        batch_set_id = 0
        try:
            # If here, we are about to retrieve ballot items
            batch_process_ballot_item_chunk.retrieve_date_started = now()
            batch_process_ballot_item_chunk.save()
            status += "RETRIEVE_DATE_STARTED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_STARTED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        if batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS:
            from import_export_batches.views_admin import \
                retrieve_ballots_for_polling_locations_api_v4_internal_view
            results = retrieve_ballots_for_polling_locations_api_v4_internal_view(
                batch_process_id=batch_process_id,
                batch_process_date_started=batch_process.date_started,
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                refresh_ballot_returned=True,
                date_last_updated_should_not_exceed=batch_process.date_started,
                batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
                use_ballotpedia=batch_process.use_ballotpedia,
                use_ctcl=batch_process.use_ctcl,
                use_vote_usa=batch_process.use_vote_usa,
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']
            if 'batch_process_ballot_item_chunk' in results:
                if results['batch_process_ballot_item_chunk'] and \
                        hasattr(results['batch_process_ballot_item_chunk'], 'batch_set_id'):
                    batch_process_ballot_item_chunk = results['batch_process_ballot_item_chunk']
        elif batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
            # Retrieving ballot items and cache in import_export_batches tables
            from import_export_batches.views_admin import refresh_ballots_for_voters_api_v4_internal_view
            results = refresh_ballots_for_voters_api_v4_internal_view(
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                date_last_updated_should_not_exceed=batch_process.date_started,
                batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
                use_ballotpedia=batch_process.use_ballotpedia,
                use_ctcl=batch_process.use_ctcl,
                use_vote_usa=batch_process.use_vote_usa,
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']
            if 'batch_process_ballot_item_chunk' in results:
                if results['batch_process_ballot_item_chunk'] and \
                        hasattr(results['batch_process_ballot_item_chunk'], 'batch_set_id'):
                    batch_process_ballot_item_chunk = results['batch_process_ballot_item_chunk']
        elif batch_process.kind_of_process == RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS:
            from import_export_batches.views_admin import \
                retrieve_ballots_for_polling_locations_api_v4_internal_view
            # Steve, Oct 2020: This line took 35 seconds to execute on my local, in the debugger
            results = retrieve_ballots_for_polling_locations_api_v4_internal_view(
                batch_process_date_started=batch_process.date_started,
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                refresh_ballot_returned=False,
                batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
                use_ballotpedia=batch_process.use_ballotpedia,
                use_ctcl=batch_process.use_ctcl,
                use_vote_usa=batch_process.use_vote_usa,
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']
            if 'batch_process_ballot_item_chunk' in results:
                if results['batch_process_ballot_item_chunk'] and \
                        hasattr(results['batch_process_ballot_item_chunk'], 'batch_set_id'):
                    batch_process_ballot_item_chunk = results['batch_process_ballot_item_chunk']

        if batch_process.kind_of_process in \
                [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
                 RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]:
            pass
        if retrieve_success:  # I think this is exclusively Ballot Items
            if positive_value_exists(batch_set_id):
                try:
                    # If here, then ballots were retrieved, so we can set retrieve_date_completed
                    batch_process_ballot_item_chunk.batch_set_id = batch_set_id
                    batch_process_ballot_item_chunk.retrieve_row_count = retrieve_row_count
                    batch_process_ballot_item_chunk.retrieve_date_completed = now()
                    batch_process_ballot_item_chunk.save()
                    status += "RETRIEVE_DATE_STARTED-RETRIEVE_DATE_COMPLETED_SAVED "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                except Exception as e:
                    status += "ERROR-RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                    results = {
                        'success': success,
                        'status': status,
                    }
                    return results

                # Now clear out date_checked_out so it can be picked up by the next step
                try:
                    batch_process.date_checked_out = None
                    batch_process.save()
                except Exception as e:
                    status += "CANNOT_CLEAR_OUT_DATE_CHECKED_OUT: " + str(e) + " "

                # We don't want to stop these processes this way any more
                # if not positive_value_exists(retrieve_row_count):
                #     if batch_process.kind_of_process == RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS \
                #             or batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS \
                #             or batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
                #         # If no batch rows were found, we know the entire batch_process is finished.
                #         # Update batch_process.date_completed to now
                #         status += "RETRIEVE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE1 "
                #         results = mark_batch_process_as_complete(batch_process, batch_process_ballot_item_chunk,
                #                                                  batch_set_id=batch_set_id,
                #                                                  google_civic_election_id=google_civic_election_id,
                #                                                  kind_of_process=kind_of_process,
                #                                                  state_code=state_code,
                #                                                  status=status)
                #         status += results['status']
                #         results = {
                #             'success': success,
                #             'status': status,
                #         }
                #         return results
            else:
                status += "RETRIEVE_DATE_STARTED-NO_BATCH_SET_ID_FOUND-BATCH_IS_COMPLETE "
                results = mark_batch_process_as_complete(
                    batch_process=batch_process,
                    batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status)
                status += results['status']
                results = {
                    'success': success,
                    'status': status,
                }
                return results
        else:
            if not positive_value_exists(batch_set_id):
                # Reset the retrieve_date_started to None
                try:
                    status += results['status']
                    batch_process_ballot_item_chunk.retrieve_date_started = None
                    batch_process_ballot_item_chunk.save()
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        critical_failure=True,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=results['status'],
                    )
                except Exception as e:
                    status += "ERROR-CANNOT_SAVE_RETRIEVE_DATE_STARTED: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                results = {
                    'success': success,
                    'status': status,
                }
                return results
            else:
                try:
                    status += results['status']
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        critical_failure=True,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                except Exception as e:
                    status += "ERROR-CANNOT_WRITE_TO_BATCH_PROCESS_LOG: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)

    elif batch_process_ballot_item_chunk.retrieve_date_completed is None:
        # Check to see if retrieve process has timed out
        date_when_retrieve_has_timed_out = \
            batch_process_ballot_item_chunk.retrieve_date_started + timedelta(seconds=retrieve_time_out_duration)
        if now() > date_when_retrieve_has_timed_out:
            # If so, set retrieve_date_completed to now and set retrieve_timed_out to True
            # But first, see if any rows were found
            # Were there batches created in the batch set from the retrieve?
            number_of_batches = 0
            if positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
                number_of_batches = batch_manager.count_number_of_batches_in_batch_set(
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id)
                # if not positive_value_exists(number_of_batches):
                #     # We don't want to stop here any more
                #     if batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS or \
                #             batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
                #         # If no batch rows were found, we know the entire batch_process is finished.
                #         # Update batch_process.date_completed to now
                #         status += "ANALYZE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE2 "
                #         results = mark_batch_process_as_complete(
                #             batch_process=batch_process,
                #             batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
                #             batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                #             google_civic_election_id=google_civic_election_id,
                #             kind_of_process=kind_of_process,
                #             state_code=state_code,
                #             status=status)
                #         status += results['status']
                #         results = {
                #             'success': success,
                #             'status': status,
                #         }
                #         return results
            else:
                status += "PROBLEM-BATCH_SET_ID_IS_MISSING_FROM_BALLOT_ITEM_CHUNK "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
                # But proceed so we can mark the retrieve part of batch_process_ballot_item_chunk as complete
            try:
                if not positive_value_exists(batch_process_ballot_item_chunk.retrieve_row_count):
                    # Make sure to store the retrieve_row_count if it wasn't already stored
                    batch_process_ballot_item_chunk.retrieve_row_count = number_of_batches
                batch_process_ballot_item_chunk.retrieve_date_completed = now()
                batch_process_ballot_item_chunk.retrieve_timed_out = True
                batch_process_ballot_item_chunk.save()
            except Exception as e:
                status += "ERROR-RETRIEVE_DATE_COMPLETED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
                results = {
                    'success': success,
                    'status': status,
                }
                return results
        else:
            # Wait
            results = {
                'success': success,
                'status': status,
            }
            return results
    elif batch_process_ballot_item_chunk.analyze_date_started is None:
        # ###################
        # This is the first pass through ANALYZE
        status += "STARTING_ANALYZE_WITH_ANALYZE_DATE_STARTED_NONE "

        if not positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
            status += "MISSING_BALLOT_ITEM_CHUNK_BATCH_SET_ID "
            try:
                batch_process_ballot_item_chunk.analyze_date_started = now()
                batch_process_ballot_item_chunk.analyze_date_completed = now()
                batch_process_ballot_item_chunk.save()
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            results = {
                'success': success,
                'status': status,
            }
            return results

        # If here, we know that the retrieve_date_completed has a value
        number_of_batches = 0
        try:
            # If here we know we have batches that need to be analyzed
            if not positive_value_exists(batch_process_ballot_item_chunk.retrieve_row_count):
                # Were there batches created in the batch set from the retrieve?
                number_of_batches = batch_manager.count_number_of_batches_in_batch_set(
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id)
                # Were there batches created in the batch set from the retrieve?
                batch_process_ballot_item_chunk.retrieve_row_count = number_of_batches
            batch_process_ballot_item_chunk.analyze_date_started = now()
            batch_process_ballot_item_chunk.save()
            status += "ANALYZE_DATE_STARTED-ANALYZE_DATE_STARTED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_STARTED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # Now analyze the batch that was stored in the "refresh_ballotpedia_ballots..." function
        results = process_batch_set(
            batch_set_id=batch_process_ballot_item_chunk.batch_set_id, analyze_all=True)
        analyze_row_count = results['batch_rows_analyzed']
        status += results['status']
        if positive_value_exists(results['success']):
            # 2021-07-16 Given so many regional elections where thousands of map point may not
            # have a ballot for a particular election, we don't want to stop when one set of
            # 125 map points does not return any ballot items

            # if not positive_value_exists(analyze_row_count):
            #     if batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
            #         # If no batch rows were found, we know the entire batch_process is finished.
            #         # Update batch_process.date_completed to now
            #         status += "ANALYZE_DATE_STARTED-REFRESH_BALLOT_ITEMS_FROM_VOTERS-ANALYZE_ROW_COUNT_ZERO "
            #         results = mark_batch_process_as_complete(
            #             batch_process=batch_process,
            #             batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
            #             batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
            #             google_civic_election_id=google_civic_election_id,
            #             kind_of_process=kind_of_process,
            #             state_code=state_code,
            #             status=status)
            #         status += results['status']
            #         results = {
            #             'success': success,
            #             'status': status,
            #         }
            #         return results
            pass
        else:
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                critical_failure=True,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        try:
            batch_process_ballot_item_chunk.analyze_row_count = analyze_row_count
            batch_process_ballot_item_chunk.analyze_date_completed = now()
            batch_process_ballot_item_chunk.save()
            status += "ANALYZE_DATE_STARTED-ANALYZE_DATE_COMPLETED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

    elif batch_process_ballot_item_chunk.analyze_date_completed is None:
        # ###################
        # This is an ANALYZE process that failed part way through
        status += "RESTARTING_FAILED_ANALYZE_PROCESS "

        if not positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
            status += "MISSING_BALLOT_ITEM_CHUNK_BATCH_SET_ID "
            try:
                batch_process_ballot_item_chunk.analyze_date_completed = now()
                batch_process_ballot_item_chunk.save()
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-ANALYZE_DATE_COMPLETED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            results = {
                'success': success,
                'status': status,
            }
            return results

        # Check to see if analyze process has timed out
        date_when_analyze_has_timed_out = \
            batch_process_ballot_item_chunk.analyze_date_started + timedelta(seconds=analyze_time_out_duration)
        if now() > date_when_analyze_has_timed_out:
            # Continue processing where we left off
            # We have time for this to run before the time out check above is run again,
            # since we have this batch checked out
            results = process_batch_set(
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id, analyze_all=True)
            status += results['status']
            if positive_value_exists(results['success']):
                not_analyzed_row_count = batch_manager.count_number_of_batches_in_batch_set(
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id, batch_row_analyzed=False)
                if not positive_value_exists(not_analyzed_row_count):
                    if batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
                        # If no batch rows were found, we know the entire batch_process is finished.
                        # Update batch_process.date_completed to now
                        status += "ANALYZE_DATE_STARTED-REFRESH_BALLOT_ITEMS_FROM_VOTERS-ANALYZE_ROW_COUNT_ZERO "
                        results = mark_batch_process_as_complete(
                            batch_process=batch_process,
                            batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_process=kind_of_process,
                            state_code=state_code,
                            status=status)
                        status += results['status']
                        results = {
                            'success': success,
                            'status': status,
                        }
                        return results

                if positive_value_exists(not_analyzed_row_count):
                    try:
                        status += "RESTARTED_FAILED_ANALYZE_PROCESS-STILL_HAS_ROWS_TO_ANALYZE "
                        batch_process_manager.create_batch_process_log_entry(
                            batch_process_id=batch_process_id,
                            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_process=kind_of_process,
                            state_code=state_code,
                            status=status,
                        )
                    except Exception as e:
                        status += "ERROR-RESTARTED_FAILED_ANALYZE_PROCESS-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " \
                                  "" + str(e) + " "
                        handle_exception(e, logger=logger, exception_message=status)
                        results = {
                            'success': success,
                            'status': status,
                        }
                        return results
                else:
                    # All batches in set have been analyzed
                    try:
                        analyze_row_count = batch_manager.count_number_of_batches_in_batch_set(
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id, batch_row_analyzed=True)
                        batch_process_ballot_item_chunk.analyze_row_count = analyze_row_count
                        batch_process_ballot_item_chunk.analyze_date_completed = now()
                        batch_process_ballot_item_chunk.save()
                        status += "ANALYZE_DATE_COMPLETED-ANALYZE_DATE_COMPLETED_SAVED "
                        batch_process_manager.create_batch_process_log_entry(
                            batch_process_id=batch_process_id,
                            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_process=kind_of_process,
                            state_code=state_code,
                            status=status,
                        )
                    except Exception as e:
                        status += "ERROR-ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED: " + str(e) + " "
                        handle_exception(e, logger=logger, exception_message=status)
                        results = {
                            'success': success,
                            'status': status,
                        }
                        return results
            else:
                status += "PROCESS_BATCH_SET-FALSE "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    critical_failure=True,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
                results = {
                    'success': success,
                    'status': status,
                }
                return results
        else:
            # Wait
            results = {
                'success': success,
                'status': status,
            }
            return results
    elif batch_process_ballot_item_chunk.create_date_started is None:
        try:
            # If here, we know that the analyze_date_completed has a value
            batch_process_ballot_item_chunk.create_date_started = now()
            batch_process_ballot_item_chunk.save()
            status += "CREATE_DATE_STARTED-SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_STARTED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # Process the create entries
        results = process_batch_set(batch_set_id=batch_process_ballot_item_chunk.batch_set_id, create_all=True)
        create_row_count = results['batch_rows_created']
        status += results['status']
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                critical_failure=True,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # Process the delete entries
        results = process_batch_set(batch_set_id=batch_process_ballot_item_chunk.batch_set_id, delete_all=True)
        status += results['status']
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                critical_failure=True,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # If here, we know that the process_batch_set has run
        try:
            batch_process_ballot_item_chunk.create_row_count = create_row_count
            batch_process_ballot_item_chunk.create_date_completed = now()
            batch_process_ballot_item_chunk.save()

            if positive_value_exists(google_civic_election_id):
                results = election_manager.retrieve_election(
                    google_civic_election_id=google_civic_election_id, read_only=False)
                if results['election_found']:
                    election_on_stage = results['election']
                    if election_on_stage and hasattr(election_on_stage, 'state_code_list_raw'):
                        ballot_returned_list_manager = BallotReturnedListManager()
                        results = \
                            ballot_returned_list_manager.retrieve_state_codes_in_election(google_civic_election_id)
                        if results['success']:
                            state_code_list = results['state_code_list']
                            try:
                                state_code_list_raw = ','.join(state_code_list)
                                election_on_stage.state_code_list_raw = state_code_list_raw
                                election_on_stage.save()
                            except Exception as e:
                                status += "ERROR-COULD_NOT_SAVE_ELECTION: " + str(e) + " "
                        else:
                            status += results['status']
                else:
                    status += results['status']

            status += "CREATE_DATE_STARTED-CREATE_DATE_COMPLETED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_COMPLETED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

    elif batch_process_ballot_item_chunk.create_date_completed is None:
        date_when_create_has_timed_out = \
            batch_process_ballot_item_chunk.create_date_started + timedelta(seconds=create_time_out_duration)
        if now() > date_when_create_has_timed_out:
            if not positive_value_exists(batch_process_ballot_item_chunk.create_row_count):
                # Were there batches created in the batch set from the retrieve?
                if positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
                    batch_process_ballot_item_chunk.create_row_count = \
                        batch_manager.count_number_of_batches_in_batch_set(
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id, batch_row_created=True)
            try:
                # If here, set create_date_completed to now and set create_timed_out to True
                batch_process_ballot_item_chunk.create_date_completed = now()
                batch_process_ballot_item_chunk.create_timed_out = True
                batch_process_ballot_item_chunk.save()

                if positive_value_exists(google_civic_election_id):
                    results = election_manager.retrieve_election(
                        google_civic_election_id=google_civic_election_id, read_only=False)
                    if results['election_found']:
                        election_on_stage = results['election']
                        if election_on_stage and hasattr(election_on_stage, 'state_code_list_raw'):
                            ballot_returned_list_manager = BallotReturnedListManager()
                            results = \
                                ballot_returned_list_manager.retrieve_state_codes_in_election(google_civic_election_id)
                            if results['success']:
                                state_code_list = results['state_code_list']
                                try:
                                    state_code_list_raw = ','.join(state_code_list)
                                    election_on_stage.state_code_list_raw = state_code_list_raw
                                    election_on_stage.save()
                                except Exception as e:
                                    status += "ERROR-COULD_NOT_SAVE_ELECTION: " + str(e) + " "
                            else:
                                status += results['status']
                    else:
                        status += results['status']

                status += "CREATE_DATE_STARTED-CREATE_DATE_COMPLETED_SAVED "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
                results = {
                    'success': success,
                    'status': status,
                }
                return results
        else:
            # Wait
            results = {
                'success': success,
                'status': status,
            }
            return results
    else:
        # All steps have been completed
        pass

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_activity_notice_batch_process(batch_process):
    status = ""
    success = True
    batch_process_manager = BatchProcessManager()

    kind_of_process = batch_process.kind_of_process
    process_now = False
    # Please also see: longest_activity_notice_processing_run_time_allowed & checked_out_expiration_time
    # We adjust timeout for ACTIVITY_NOTICE_PROCESS in retrieve_batch_process_list
    activity_notice_processing_time_out_duration = 270  # 4.5 minutes * 60 seconds

    if batch_process.date_started is None:
        # When a batch_process is running, we mark it "taken off the shelf" to be worked on ("date_checked_out").
        #  When the process is complete, we should reset this to "NULL"
        process_now = True
        try:
            batch_process.date_started = now()
            batch_process.date_checked_out = now()
            batch_process.save()
        except Exception as e:
            status += "ERROR-ACTIVITY_NOTICE-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            success = False
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
    elif batch_process.date_completed is None:
        # Check to see if process has timed out
        date_when_timed_out = \
            batch_process.date_started + timedelta(seconds=activity_notice_processing_time_out_duration)
        if now() > date_when_timed_out:
            # Update batch_process.date_completed to now
            status += "ACTIVITY_NOTICE-TIMED_OUT "
            results = mark_batch_process_as_complete(
                batch_process=batch_process,
                kind_of_process=kind_of_process,
                status=status)
            status += results['status']

    if process_now:
        activity_notice_results = process_activity_notice_seeds_triggered_by_batch_process()
        status += activity_notice_results['status']

        if activity_notice_results['success']:
            activity_notice_seed_count = activity_notice_results['activity_notice_seed_count']
            activity_notice_count = activity_notice_results['activity_notice_count']
            try:
                if activity_notice_seed_count == 0 and activity_notice_count == 0:
                    # We don't want to leave a bunch of empty batch_processes around
                    batch_process.delete()
                else:
                    batch_process.completion_summary = "ACTIVITY_NOTICE_RESULTS, " \
                                                       "activity_notice_seed_count: {activity_notice_seed_count} " \
                                                       "activity_notice_count: {activity_notice_count}" \
                                                       "".format(activity_notice_seed_count=activity_notice_seed_count,
                                                                 activity_notice_count=activity_notice_count)
                    batch_process.date_checked_out = None
                    batch_process.date_completed = now()
                    batch_process.save()
                    status += "ACTIVITY_NOTICE_BATCH_PROCESS_SAVED "
                if positive_value_exists(activity_notice_seed_count) or positive_value_exists(activity_notice_count):
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=kind_of_process,
                        status=status,
                    )
            except Exception as e:
                status += "ERROR-ACTIVITY_NOTICE-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    kind_of_process=kind_of_process,
                    status=status,
                )
                results = {
                    'success': success,
                    'status': status,
                }
                return results
        else:
            status += "CREATE_OR_UPDATE_ACTIVITY_NOTICES_FAILED "
            success = False
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_one_generate_voter_guides_batch_process(batch_process):
    status = ""
    success = True
    voter_guide_manager = VoterGuideManager()
    batch_process_manager = BatchProcessManager()

    kind_of_process = batch_process.kind_of_process

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        batch_process.date_started = now()
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "ERROR-GENERATE_VOTER_GUIDES-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            google_civic_election_id=batch_process.google_civic_election_id,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Generate voter guides for one election
    google_civic_election_id = batch_process.google_civic_election_id

    # Query PositionEntered table in this election for unique organization_we_vote_ids
    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list=[google_civic_election_id])
    if not positive_value_exists(results['success']):
        success = False
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    positions_exist_query = PositionEntered.objects.using('readonly').all()
    positions_exist_query = positions_exist_query.filter(
        Q(google_civic_election_id=google_civic_election_id) |
        Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
    positions_exist_query = positions_exist_query.filter(
        Q(vote_smart_rating__isnull=True) | Q(vote_smart_rating=""))
    # NOTE: There is a bug here to address -- this is not returning a list of distinct 'organization_we_vote_id' values
    positions_exist_query = positions_exist_query.values_list('organization_we_vote_id', flat=True).distinct()
    organization_we_vote_ids_with_positions = list(positions_exist_query)
    # status += str(organization_we_vote_ids_with_positions)
    # Add extra filter for safety while figuring out why distinct didn't work
    organization_we_vote_ids_with_positions_filtered = []
    for organization_we_vote_id in organization_we_vote_ids_with_positions:
        if organization_we_vote_id not in organization_we_vote_ids_with_positions_filtered:
            organization_we_vote_ids_with_positions_filtered.append(organization_we_vote_id)

    elections_dict = {}
    voter_guides_generated_count = 0
    for organization_we_vote_id in organization_we_vote_ids_with_positions_filtered:
        results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
            organization_we_vote_id=organization_we_vote_id,
            google_civic_election_id=google_civic_election_id,
            elections_dict=elections_dict,
        )
        if results['success']:
            voter_guides_generated_count += 1
        else:
            status += results['status']
        elections_dict = results['elections_dict']

    if success:
        status += "VOTER_GUIDES_GENERATED_COUNT: " + str(voter_guides_generated_count) + " "
        results = voter_guide_manager.update_or_create_voter_guides_generated(
            google_civic_election_id=google_civic_election_id,
            number_of_voter_guides=voter_guides_generated_count,
        )
        status += results['status']

        try:
            batch_process.completion_summary = status
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                google_civic_election_id=google_civic_election_id,
                status=status,
            )
        except Exception as e:
            status += "ERROR-VOTER_GUIDES_GENERATED_DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                google_civic_election_id=google_civic_election_id,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
    else:
        status += "VOTER_GUIDES_GENERATED_FAILED "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            google_civic_election_id=google_civic_election_id,
            status=status,
        )

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_one_search_twitter_batch_process(batch_process, status=""):
    success = True
    batch_process_manager = BatchProcessManager()

    kind_of_process = batch_process.kind_of_process

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        if batch_process.date_started is None:
            batch_process.date_started = now()
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "ERROR-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    retrieve_results = retrieve_possible_twitter_handles_in_bulk()
    status += retrieve_results['status']

    if retrieve_results['success']:
        candidates_analyzed = retrieve_results['candidates_analyzed']
        candidates_to_analyze = retrieve_results['candidates_to_analyze']
        try:
            completion_summary = \
                "Candidates Analyzed: {candidates_analyzed} " \
                "out of {candidates_to_analyze}" \
                "".format(candidates_analyzed=candidates_analyzed,
                          candidates_to_analyze=candidates_to_analyze)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "ERROR-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
    else:
        status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES_FAILED-MARKED_COMPLETED "
        success = False
        try:
            completion_summary = \
                "retrieve_possible_twitter_handles_in_bulk FAILED: {status}" \
                "".format(status=status)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "ERROR-COMPLETION_SUMMARY_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_one_update_twitter_batch_process(batch_process, status=""):
    candidates_updated = 0
    organizations_updated = 0
    representatives_updated = 0
    success = True
    batch_process_manager = BatchProcessManager()

    kind_of_process = batch_process.kind_of_process

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        if batch_process.date_started is None:
            batch_process.date_started = now()
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "CANDIDATE_TWITTER_DATA_TO_UPDATE_ERROR-CHECKED_OUT_TIME_NOT_SAVED: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    retrieve_results = retrieve_and_update_candidates_needing_twitter_update(batch_process_id=batch_process.id)
    status += retrieve_results['status']

    if retrieve_results['success']:
        candidates_updated = retrieve_results['candidates_updated']
        candidates_to_update = retrieve_results['candidates_to_update']
        if positive_value_exists(candidates_to_update):
            try:
                completion_summary = \
                    "Candidates Updated: {candidates_updated} " \
                    "out of {candidates_to_update}" \
                    "".format(candidates_updated=candidates_updated,
                              candidates_to_update=candidates_to_update)
                status += completion_summary + " "
                batch_process.completion_summary = completion_summary
                batch_process.date_checked_out = None
                batch_process.date_completed = now()
                batch_process.save()

                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    kind_of_process=kind_of_process,
                    status=status,
                )
            except Exception as e:
                status += "CANDIDATE_TWITTER_DATA_TO_UPDATE_ERROR-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
                success = False
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    kind_of_process=kind_of_process,
                    status=status,
                )
        else:
            # Drop through
            pass
    else:
        status += "CANDIDATE_TWITTER_DATA_TO_UPDATE_FAILED-MARKED_COMPLETED "
        success = False
        try:
            completion_summary = \
                "retrieve_and_update_candidates_needing_twitter_update FAILED: {status}" \
                "".format(status=status)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "CANDIDATE_TWITTER_DATA_TO_UPDATE_ERROR-COMPLETION_SUMMARY_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )

    if not success or positive_value_exists(candidates_updated):
        results = {
            'success':  success,
            'status':   status,
        }
        return results

    # If there weren't any candidates to update, move on to representatives
    try:
        retrieve_results = retrieve_and_update_representatives_needing_twitter_update(batch_process_id=batch_process.id)
        status += retrieve_results['status']
    except Exception as e:
        status += "retrieve_and_update_representatives_needing_twitter_update: " + str(e) + " "
        success = False
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            status=status,
        )

    if success and retrieve_results['success']:
        representatives_updated = retrieve_results['representatives_updated']
        representatives_to_update = retrieve_results['representatives_to_update']
        try:
            completion_summary = \
                "Representatives updated: {representatives_updated} " \
                "out of {representatives_to_update}" \
                "".format(representatives_updated=representatives_updated,
                          representatives_to_update=representatives_to_update)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "REPRESENTATIVE_TWITTER_DATA_TO_UPDATE_ERROR-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            success = False
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
    else:
        status += "REPRESENTATIVE_TWITTER_DATA_TO_UPDATE_FAILED-MARKED_COMPLETED "
        success = False
        try:
            completion_summary = \
                "retrieve_and_update_representatives_needing_twitter_update FAILED: {status}" \
                "".format(status=status)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "REPRESENTATIVE_TWITTER_DATA_TO_UPDATE_ERROR-COMPLETION_SUMMARY_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )

    if not success or positive_value_exists(representatives_updated):
        results = {
            'success':  success,
            'status':   status,
        }
        return results

    # If there weren't any representatives to update, move on to organizations
    try:
        retrieve_results = retrieve_and_update_organizations_needing_twitter_update(batch_process_id=batch_process.id)
        status += retrieve_results['status']
    except Exception as e:
        status += "FAILED_retrieve_and_update_organizations_needing_twitter_update: " + str(e) + " "
        success = False
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=kind_of_process,
            status=status,
        )

    if success and retrieve_results['success']:
        organizations_updated = retrieve_results['organizations_updated']
        organizations_to_update = retrieve_results['organizations_to_update']
        try:
            completion_summary = \
                "Organizations updated: {organizations_updated} " \
                "out of {organizations_to_update}" \
                "".format(organizations_updated=organizations_updated,
                          organizations_to_update=organizations_to_update)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "ORGANIZATION_TWITTER_DATA_TO_UPDATE_ERROR-DATE_COMPLETED_TIME_NOT_SAVED: " + str(e) + " "
            success = False
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
    else:
        status += "ORGANIZATION_TWITTER_DATA_TO_UPDATE_FAILED-MARKED_COMPLETED "
        success = False
        try:
            completion_summary = \
                "retrieve_and_update_organizations_needing_twitter_update FAILED: {status}" \
                "".format(status=status)
            status += completion_summary + " "
            batch_process.completion_summary = completion_summary
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "ORGANIZATION_TWITTER_DATA_TO_UPDATE_ERROR-COMPLETION_SUMMARY_NOT_SAVED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
    results = {
        'success':              success,
        'status':               status,
    }
    return results


def process_one_sitewide_daily_analytics_batch_process(batch_process):
    from import_export_batches.models import BatchProcessManager
    analytics_manager = AnalyticsManager()
    batch_process_manager = BatchProcessManager()
    status = ""
    success = True

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        if batch_process.date_started is None:
            batch_process.date_started = now()
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "ERROR-CHECKED_OUT_TIME_NOT_SAVED-SITEWIDE_DAILY: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    update_results = update_issue_statistics()
    status += update_results['status']

    daily_metrics_calculated = False
    results = calculate_sitewide_daily_metrics(batch_process.analytics_date_as_integer)
    status += results['status']
    if positive_value_exists(results['success']):
        sitewide_daily_metrics_values = results['sitewide_daily_metrics_values']
        update_results = analytics_manager.save_sitewide_daily_metrics_values(sitewide_daily_metrics_values)
        status += update_results['status']
        if positive_value_exists(update_results['success']):
            daily_metrics_calculated = True
        else:
            status += "SAVE_SITEWIDE_DAILY_METRICS-FAILED_TO_SAVE "
            success = False
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
    else:
        status += "SAVE_SITEWIDE_DAILY_METRICS-FAILED_TO_CALCULATE "
        success = False
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    try:
        if daily_metrics_calculated:
            batch_process.date_completed = now()
            batch_process.completion_summary = "Sitewide daily metrics SAVED"
        else:
            batch_process.completion_summary = "Sitewide daily metrics NOT saved"
        batch_process.date_checked_out = None
        batch_process.save()
    except Exception as e:
        status += "ERROR-CHECKED_OUT_TIME_NOT_RESET: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            analytics_date_as_integer=batch_process.analytics_date_as_integer,
            status=status,
        )

    if daily_metrics_calculated:
        # If here, there aren't any more sitewide_daily_metrics to process for this date
        defaults = {
            'finished_calculate_sitewide_daily_metrics': True,
        }
        status_results = analytics_manager.save_analytics_processing_status(
            batch_process.analytics_date_as_integer,
            defaults=defaults)
        status += status_results['status']
    else:
        status += "COULD_NOT_CALCULATE_SITEWIDE_DAILY_METRICS "

    batch_process_manager.create_batch_process_log_entry(
        batch_process_id=batch_process.id,
        kind_of_process=batch_process.kind_of_process,
        status=status,
    )

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_batch_set(batch_set_id=0, analyze_all=False, create_all=False, delete_all=False):
    """

    :param batch_set_id:
    :param analyze_all:
    :param create_all:
    :param delete_all:
    :return:
    """
    status = ""
    success = True
    batch_rows_analyzed = 0
    batch_rows_created = 0
    batch_rows_deleted = 0
    start_each_batch_time_tracker = []  # Array of times
    summary_of_create_batch_row_action_time_tracker = []  # Array of arrays

    if not positive_value_exists(batch_set_id):
        status += "BATCH_SET_ID_REQUIRED "
        success = False
        results = {
            'success': success,
            'status': status,
            'batch_rows_analyzed':   batch_rows_analyzed,
            'batch_rows_created':    batch_rows_created,
        }
        return results

    # Store static data in memory so we don't have to use the database
    election_objects_dict = {}
    office_objects_dict = {}
    measure_objects_dict = {}

    if positive_value_exists(analyze_all):
        batch_rows_analyzed = 0
        batch_header_id_created_list = []

        batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
        batch_description_query = batch_description_query.exclude(batch_description_analyzed=True)
        # Note that this needs to be read_only=False
        batch_list = list(batch_description_query)

        batch_description_rows_reviewed = 0
        for one_batch_description in batch_list:
            start_each_batch_time_tracker.append(now().strftime("%H:%M:%S:%f"))
            results = create_batch_row_actions(
                one_batch_description.batch_header_id,
                batch_description=one_batch_description,
                election_objects_dict=election_objects_dict,
                measure_objects_dict=measure_objects_dict,
                office_objects_dict=office_objects_dict,
            )
            batch_description_rows_reviewed += 1
            if results['batch_actions_created']:
                batch_rows_analyzed += 1
                batch_header_id_created_list.append(one_batch_description.batch_header_id)
            if not results['success']:
                status += results['status']
            election_objects_dict = results['election_objects_dict']
            measure_objects_dict = results['measure_objects_dict']
            office_objects_dict = results['office_objects_dict']
            start_create_batch_row_action_time_tracker = results['start_create_batch_row_action_time_tracker']
            summary_of_create_batch_row_action_time_tracker.append(start_create_batch_row_action_time_tracker)
        status += "CREATE_BATCH_ROW_ACTIONS_BATCH_ROWS_ANALYZED: " + str(batch_rows_analyzed) + \
                  " OUT_OF " + str(batch_description_rows_reviewed) + ", "
    elif positive_value_exists(create_all):
        batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
        batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
        batch_list = list(batch_description_query)

        batch_rows_created = 0
        batch_rows_not_created = 0
        for one_batch_description in batch_list:
            results = import_data_from_batch_row_actions(
                one_batch_description.kind_of_batch, IMPORT_CREATE, one_batch_description.batch_header_id)
            if results['number_of_table_rows_created']:
                batch_rows_created += 1
            else:
                batch_rows_not_created += 1
                if batch_rows_not_created < 10:
                    status += results['status']
            if not positive_value_exists(results['success']) and len(status) < 1024:
                status += results['status']
        status += "BATCH_ROWS_CREATED: " + str(batch_rows_created) + ", "
        if positive_value_exists(batch_rows_not_created):
            status += "BATCH_ROWS_NOT_CREATED: " + str(batch_rows_not_created) + ", "
    elif positive_value_exists(delete_all):
        batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
        batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
        batch_list = list(batch_description_query)

        batch_rows_deleted = 0
        for one_batch_description in batch_list:
            results = import_data_from_batch_row_actions(
                one_batch_description.kind_of_batch, IMPORT_DELETE, one_batch_description.batch_header_id)
            if results['number_of_table_rows_deleted']:
                batch_rows_deleted += 1

            if not positive_value_exists(results['success']) and len(status) < 1024:
                status += results['status']
        status += "BATCH_ROWS_DELETED: " + str(batch_rows_deleted) + ", "
    else:
        status += "MUST_SPECIFY_ANALYZE_CREATE_OR_DELETE "

    results = {
        'success':              success,
        'status':               status,
        'batch_rows_analyzed':  batch_rows_analyzed,
        'batch_rows_created':   batch_rows_created,
        'batch_rows_deleted':   batch_rows_deleted,
    }
    return results


def mark_batch_process_as_complete(
        batch_process=None,
        batch_process_ballot_item_chunk=None,
        batch_process_representatives_chunk=None,
        batch_set_id=0,
        google_civic_election_id=None,
        kind_of_process="",
        state_code=None,
        status=""):
    success = True
    batch_process_updated = False
    batch_process_ballot_item_chunk_updated = False
    batch_process_representatives_chunk_updated = False
    batch_process_manager = BatchProcessManager()
    batch_process_id = 0
    batch_process_ballot_item_chunk_id = 0
    batch_process_representatives_chunk_id = 0

    if batch_process:
        try:
            # Before saving batch_process, make sure we have the latest version. (For example, it might have been
            #  paused since it was first retrieved.)
            batch_process_results = \
                batch_process_manager.retrieve_batch_process(batch_process_id=batch_process.id)
            if positive_value_exists(batch_process_results['batch_process_found']):
                batch_process = batch_process_results['batch_process']

            batch_process_id = batch_process.id
            if batch_process.date_started is None:
                batch_process.date_started = now()
            if batch_process.date_completed is None:
                batch_process.date_checked_out = None
                batch_process.date_completed = now()
            batch_process.save()
            batch_process_updated = True
            status += "BATCH_PROCESS_MARKED_COMPLETE "
        except Exception as e:
            success = False
            status += "ERROR-CANNOT_MARK_BATCH_PROCESS_AS_COMPLETE: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk_id,
                batch_set_id=batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )

    if batch_process_ballot_item_chunk:
        try:
            batch_process_ballot_item_chunk_id = batch_process_ballot_item_chunk.id
            if batch_process_ballot_item_chunk.retrieve_date_started is None:
                batch_process_ballot_item_chunk.retrieve_date_started = now()
            if batch_process_ballot_item_chunk.retrieve_date_completed is None:
                batch_process_ballot_item_chunk.retrieve_date_completed = now()
            if batch_process_ballot_item_chunk.analyze_date_started is None:
                batch_process_ballot_item_chunk.analyze_date_started = now()
            if batch_process_ballot_item_chunk.analyze_date_completed is None:
                batch_process_ballot_item_chunk.analyze_date_completed = now()
            if batch_process_ballot_item_chunk.create_date_started is None:
                batch_process_ballot_item_chunk.create_date_started = now()
            if batch_process_ballot_item_chunk.create_date_completed is None:
                batch_process_ballot_item_chunk.create_date_completed = now()
            batch_process_ballot_item_chunk.save()
            batch_process_ballot_item_chunk_updated = True
            status += "BATCH_PROCESS_BALLOT_ITEM_CHUNK_MARKED_COMPLETE "
        except Exception as e:
            success = False
            status += "ERROR-CANNOT_MARK_BATCH_PROCESS_BALLOT_ITEM_CHUNK_AS_COMPLETE: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
                batch_set_id=batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
    elif batch_process_representatives_chunk:
        try:
            batch_process_representatives_chunk_id = batch_process_representatives_chunk.id
            if batch_process_representatives_chunk.retrieve_date_started is None:
                batch_process_representatives_chunk.retrieve_date_started = now()
            if batch_process_representatives_chunk.retrieve_date_completed is None:
                batch_process_representatives_chunk.retrieve_date_completed = now()
            if batch_process_representatives_chunk.analyze_date_started is None:
                batch_process_representatives_chunk.analyze_date_started = now()
            if batch_process_representatives_chunk.analyze_date_completed is None:
                batch_process_representatives_chunk.analyze_date_completed = now()
            if batch_process_representatives_chunk.create_date_started is None:
                batch_process_representatives_chunk.create_date_started = now()
            if batch_process_representatives_chunk.create_date_completed is None:
                batch_process_representatives_chunk.create_date_completed = now()
            batch_process_representatives_chunk.save()
            batch_process_representatives_chunk_updated = True
            status += "BATCH_PROCESS_REPRESENTATIVES_CHUNK_MARKED_COMPLETE "
        except Exception as e:
            success = False
            status += "ERROR-CANNOT_MARK_BATCH_PROCESS_REPRESENTATIVES_CHUNK_AS_COMPLETE: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk_id,
                batch_set_id=batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )

    if batch_process_ballot_item_chunk or batch_process_ballot_item_chunk_updated:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
            batch_set_id=batch_set_id,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )
    elif batch_process_representatives_chunk or batch_process_representatives_chunk_updated:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
            batch_process_representatives_chunk_id=batch_process_representatives_chunk_id,
            batch_set_id=batch_set_id,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )

    results = {
        'success':                                  success,
        'status':                                   status,
        'batch_process':                            batch_process,
        'batch_process_updated':                    batch_process_updated,
        'batch_process_ballot_item_chunk':          batch_process_ballot_item_chunk,
        'batch_process_ballot_item_chunk_updated':  batch_process_ballot_item_chunk_updated,
        'batch_process_representatives_chunk':      batch_process_representatives_chunk,
        'batch_process_representatives_chunk_updated': batch_process_representatives_chunk_updated,
    }
    return results


def schedule_retrieve_ballots_for_polling_locations_api_v4(
        google_civic_election_id="",
        state_code="",
        refresh_ballot_returned=False,
        use_ballotpedia=False,
        use_ctcl=False,
        use_vote_usa=False):
    status = ""

    # [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
    #  RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]
    if positive_value_exists(refresh_ballot_returned):
        kind_of_process = REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
    else:
        kind_of_process = RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
    status += "SCHEDULING: " + str(kind_of_process) + " "

    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.create_batch_process(
        google_civic_election_id=google_civic_election_id,
        kind_of_process=kind_of_process,
        state_code=state_code,
        use_ballotpedia=use_ballotpedia,
        use_ctcl=use_ctcl,
        use_vote_usa=use_vote_usa)
    status += results['status']
    success = results['success']
    if results['batch_process_saved']:
        batch_process = results['batch_process']
        status += "RETRIEVE_BALLOTS_BATCH_PROCESS_SAVED "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            google_civic_election_id=batch_process.google_civic_election_id,
            kind_of_process=batch_process.kind_of_process,
            state_code=batch_process.state_code,
            status=status,
        )
    else:
        status += "FAILED_TO_SCHEDULE-" + str(kind_of_process) + " "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=0,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def schedule_refresh_ballots_for_voters_api_v4(
        google_civic_election_id="",
        state_code="",
        voter_id=0,
        use_ballotpedia=False,
        use_ctcl=False,
        use_vote_usa=False):
    status = ""

    # [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
    #  RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]
    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.create_batch_process(
        google_civic_election_id=google_civic_election_id,
        kind_of_process=REFRESH_BALLOT_ITEMS_FROM_VOTERS,
        state_code=state_code,
        voter_id=voter_id,
        use_ballotpedia=use_ballotpedia,
        use_ctcl=use_ctcl,
        use_vote_usa=use_vote_usa)
    status += results['status']
    success = results['success']
    if results['batch_process_saved']:
        batch_process = results['batch_process']
        status += "SCHEDULED_REFRESH_BALLOTS_FOR_VOTERS "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            google_civic_election_id=batch_process.google_civic_election_id,
            kind_of_process=batch_process.kind_of_process,
            state_code=batch_process.state_code,
            status=status,
        )
    else:
        status += "FAILED_TO_SCHEDULE_REFRESH_BALLOTS_FOR_VOTERS "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=0,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=REFRESH_BALLOT_ITEMS_FROM_VOTERS,
            state_code=state_code,
            status=status,
        )

    results = {
        'success':  success,
        'status':   status,
    }
    return results


def schedule_retrieve_representatives_for_polling_locations(
        state_code="",
        refresh_representatives=False,
        use_ballotpedia=False,
        use_ctcl=False,
        use_vote_usa=False):
    status = ""

    if positive_value_exists(refresh_representatives):
        kind_of_process = REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
    else:
        kind_of_process = RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS
    status += "SCHEDULING: " + str(kind_of_process) + " "

    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.create_batch_process(
        kind_of_process=kind_of_process,
        state_code=state_code,
        use_ballotpedia=use_ballotpedia,
        use_ctcl=use_ctcl,
        use_vote_usa=use_vote_usa)
    status += results['status']
    success = results['success']
    if results['batch_process_saved']:
        batch_process = results['batch_process']
        status += "RETRIEVE_REPRESENTATIVES_BATCH_PROCESS_SAVED "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            state_code=batch_process.state_code,
            status=status,
        )
    else:
        status += "FAILED_TO_SCHEDULE_RETRIEVE_REPRESENTATIVES-" + str(kind_of_process) + " "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=0,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )

    results = {
        'success':              success,
        'status':               status,
    }
    return results
