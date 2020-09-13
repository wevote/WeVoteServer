# import_export_batches/controllers_batch_process.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import create_batch_row_actions, import_data_from_batch_row_actions
from .models import ACTIVITY_NOTICE_PROCESS, API_REFRESH_REQUEST, \
    AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID, AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT, \
    BatchDescription, BatchManager, BatchProcessManager, \
    CALCULATE_ORGANIZATION_DAILY_METRICS, \
    CALCULATE_ORGANIZATION_ELECTION_METRICS, \
    CALCULATE_SITEWIDE_DAILY_METRICS, \
    CALCULATE_SITEWIDE_ELECTION_METRICS, \
    CALCULATE_SITEWIDE_VOTER_METRICS, \
    IMPORT_CREATE, IMPORT_DELETE, \
    RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, \
    REFRESH_BALLOT_ITEMS_FROM_VOTERS, SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE
from activity.controllers import process_activity_notice_seeds_triggered_by_batch_process
from analytics.controllers import calculate_sitewide_daily_metrics, \
    process_one_analytics_batch_process_augment_with_election_id, \
    process_one_analytics_batch_process_augment_with_first_visit, process_sitewide_voter_metrics, \
    retrieve_analytics_processing_next_step
from analytics.models import AnalyticsManager
from api_internal_cache.models import ApiInternalCacheManager
from ballot.models import BallotReturnedListManager
from datetime import timedelta
from django.utils.timezone import now
from election.models import ElectionManager
from exception.models import handle_exception
from import_export_twitter.controllers import fetch_number_of_candidates_needing_twitter_search, \
    retrieve_possible_twitter_handles_in_bulk
from issue.controllers import update_issue_statistics
import json
from voter_guide.controllers import voter_guides_upcoming_retrieve_for_api
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_batch_process_system_on

logger = wevote_functions.admin.get_logger(__name__)

CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
ELECTED_OFFICE = 'ELECTED_OFFICE'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'

NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES = 4  # Four processes at a time

def batch_process_next_steps():
    success = True
    status = ""
    batch_process_manager = BatchProcessManager()

    # If we have more than NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES batch_processes that are still active,
    # don't start a new import ballot item batch_process
    total_active_batch_processes = batch_process_manager.count_active_batch_processes()
    status += "TOTAL_ACTIVE_BATCH_PROCESSES: " + str(total_active_batch_processes) + ", "

    total_checked_out_batch_processes = batch_process_manager.count_checked_out_batch_processes()
    status += "CHECKED_OUT_BATCH_PROCESSES: " + str(total_checked_out_batch_processes) + ", "

    if not fetch_batch_process_system_on():
        status += "BATCH_PROCESS_SYSTEM_TURNED_OFF "
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve list of active BatchProcess
    results = batch_process_manager.retrieve_batch_process_list(process_active=True, process_queued=False)
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
    batch_process_list = []
    batch_process_list_count = 0
    if positive_value_exists(results['batch_process_list_found']):
        full_batch_process_list = results['batch_process_list']
        # How many processes currently running?
        batch_process_list_count = len(full_batch_process_list)
        if positive_value_exists(batch_process_list_count):
            batch_process_list.append(full_batch_process_list[0])
    status += "BATCH_PROCESS_COUNT: " + str(batch_process_list_count) + ", "

    # ############################
    # Are there any Api's that need to have their internal cache updated?
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
            # Increase these counters so the code below can react correctly
            batch_process_list_count += 1
            total_active_batch_processes += 1
            batch_process = results['batch_process']
            batch_process_list.append(batch_process)
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
                status += "COULD_NOT_MARK_API_REFRESH_REQUEST_WITH_DATE_CHECKED_OUT " + str(e) + " "
        else:
            status += "FAILED_TO_SCHEDULE-" + str(API_REFRESH_REQUEST) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=0,
                kind_of_process=API_REFRESH_REQUEST,
                status=status,
            )

    # ############################
    # Twitter Search
    number_of_candidates_to_analyze = fetch_number_of_candidates_needing_twitter_search()
    if positive_value_exists(number_of_candidates_to_analyze):
        results = batch_process_manager.create_batch_process(
            kind_of_process=SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE)
        status += results['status']
        success = results['success']
        if results['batch_process_saved']:
            batch_process = results['batch_process']
            batch_process_list.append(batch_process)
            status += "SCHEDULED_SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE "
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
    # Processing Analytics
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
                    batch_process_list.append(batch_process)
                    status += "SCHEDULED_PROCESS: " + str(kind_of_process) + " "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=batch_process.kind_of_process,
                        status=status,
                    )
                except Exception as e:
                    status += "BATCH_PROCESS_ANALYTICS-CANNOT_SAVE_DATE_STARTED " + str(e) + " "
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

    # ##################################
    # Generate or Update ActivityNotice entries from ActivityNoticeSeed entries
    activity_notice_process_is_currently_running = batch_process_manager.is_activity_notice_process_currently_running()
    if not activity_notice_process_is_currently_running:
        results = batch_process_manager.create_batch_process(kind_of_process=ACTIVITY_NOTICE_PROCESS)
        status += results['status']
        success = results['success']
        if results['batch_process_saved']:
            batch_process = results['batch_process']
            batch_process_list.insert(0, batch_process)  # Put at the start of the list
            status += "SCHEDULED_ACTIVITY_NOTICE_PROCESS "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=batch_process.kind_of_process,
                status=status,
            )
        else:
            status += "FAILED_TO_SCHEDULE-" + str(ACTIVITY_NOTICE_PROCESS) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=0,
                kind_of_process=ACTIVITY_NOTICE_PROCESS,
                status=status,
            )

    # ############################
    # Processing Ballot Items
    # If less than NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES total active processes,
    #  and we aren't working on a current process chunk,
    #  then add a new batch_process (importing ballot items) to the current queue
    status += "TOTAL_ACTIVE_BATCH_PROCESSES-BEFORE_RETRIEVE: " + str(total_active_batch_processes) + " "
    if total_active_batch_processes < NUMBER_OF_SIMULTANEOUS_BATCH_PROCESSES:
        results = batch_process_manager.retrieve_batch_process_list(process_active=False, process_queued=True)
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
            for new_batch in new_batch_process_list:
                # Bring the batch_process_list up by 1 item
                kind_of_process = ""
                try:
                    kind_of_process = new_batch.kind_of_process
                    new_batch.date_started = now()
                    new_batch.save()
                    batch_process_list.append(new_batch)
                    total_active_batch_processes += 1
                except Exception as e:
                    status += "BATCH_PROCESS-CANNOT_SAVE_DATE_STARTED " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=new_batch.id,
                        kind_of_process=kind_of_process,
                        status=status,
                    )
                break
    status += "TOTAL_ACTIVE_BATCH_PROCESSES_BEFORE_PROCESS_LOOP: " + str(total_active_batch_processes) + " "

    for batch_process in batch_process_list:
        if batch_process.kind_of_process in \
                [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
                 RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]:
            results = process_one_ballot_item_batch_process(batch_process)
            status += results['status']

            # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
            #  When the process is complete, we should reset this to "NULL"
            try:
                # Before saving batch_process, make sure we have the latest version. (For example, it might have been
                #  paused since it was first retrieved.)
                batch_process_results = batch_process_manager.retrieve_batch_process(batch_process.id)
                if positive_value_exists(batch_process_results['batch_process_found']):
                    batch_process = batch_process_results['batch_process']

                batch_process.date_checked_out = None
                batch_process.save()
            except Exception as e:
                status += "COULD_NOT_SET_CHECKED_OUT_TIME_TO_NULL " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    google_civic_election_id=batch_process.google_civic_election_id,
                    kind_of_process=batch_process.kind_of_process,
                    state_code=batch_process.state_code,
                    status=status,
                )
        elif batch_process.kind_of_process in [ACTIVITY_NOTICE_PROCESS]:
            results = process_activity_notice_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [API_REFRESH_REQUEST]:
            results = process_one_api_refresh_request_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [
                AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID, AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT,
                CALCULATE_SITEWIDE_VOTER_METRICS,
                CALCULATE_SITEWIDE_ELECTION_METRICS, CALCULATE_ORGANIZATION_DAILY_METRICS,
                CALCULATE_ORGANIZATION_ELECTION_METRICS]:
            results = process_one_analytics_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [CALCULATE_SITEWIDE_DAILY_METRICS]:
            results = process_one_sitewide_daily_analytics_batch_process(batch_process)
            status += results['status']
        elif batch_process.kind_of_process in [SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE]:
            results = process_one_search_twitter_batch_process(batch_process)
            status += results['status']
        else:
            status += "KIND_OF_PROCESS_NOT_RECOGNIZED "

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
        status += "ANALYTICS_BATCH-CHECKED_OUT_TIME_NOT_SAVED " + str(e) + " "
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
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            kind_of_process=batch_process.kind_of_process,
            analytics_date_as_integer=batch_process.analytics_date_as_integer,
            status=results['status'],
        )
        status += results['status']
        results = {
            'success': success,
            'status': status,
        }
        return results
    if results['batch_process_analytics_chunk_found']:
        batch_process_analytics_chunk = results['batch_process_analytics_chunk']
    else:
        # We need to create a new batch_process_analytics_chunk here.
        # We don't consider a batch_process completed until
        # a batch_process_analytics_chunk reports that there are no more items retrieved
        results = batch_process_manager.create_batch_process_analytics_chunk(batch_process=batch_process)
        if results['batch_process_analytics_chunk_created']:
            batch_process_analytics_chunk = results['batch_process_analytics_chunk']
        else:
            status += results['status']
            status += "UNABLE_TO_CREATE_ANALYTICS_CHUNK "
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
            status += "BATCH_PROCESS_ANALYTICS_CHUNK_TIMED_OUT-DATE_COMPLETED_TIME_NOT_SAVED " + str(e) + " "
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
            batch_process_results = batch_process_manager.retrieve_batch_process(batch_process.id)
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
            status += "TIMED_OUT-DATE_COMPLETED_TIME_NOT_SAVED " + str(e) + " "
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
        status += "ANALYTICS_CHUNK_DATE_STARTED_TIME_NOT_SAVED " + str(e) + " "
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
        # Before saving batch_process, make sure we have the latest version. (For example, it might have been
        #  paused since it was first retrieved.)
        batch_process_results = batch_process_manager.retrieve_batch_process(batch_process.id)
        if positive_value_exists(batch_process_results['batch_process_found']):
            batch_process = batch_process_results['batch_process']

        if mark_as_completed:
            # Not implemented yet -- mark as completed
            batch_process.date_completed = now()
        batch_process.date_checked_out = None
        batch_process.save()
    except Exception as e:
        status += "CHECKED_OUT_TIME_NOT_RESET: " + str(e) + " "
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
        status += "API_REFRESH_REQUEST-CHECKED_OUT_TIME_NOT_SAVED " + str(e) + " "
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
            status += "DATE_COMPLETED_TIME_NOT_SAVED " + str(e) + " "
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
        batch_process_results = batch_process_manager.retrieve_batch_process(batch_process.id)
        if positive_value_exists(batch_process_results['batch_process_found']):
            batch_process = batch_process_results['batch_process']

        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "CHECKED_OUT_TIME_NOT_SAVED " + str(e) + " "
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
        batch_process_id=batch_process.id)
    if not results['success']:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
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
            batch_process_manager.create_batch_process_ballot_item_chunk(batch_process_id=batch_process.id)
        if results['batch_process_ballot_item_chunk_created']:
            batch_process_ballot_item_chunk = results['batch_process_ballot_item_chunk']
        else:
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_STARTED " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
            from import_export_ballotpedia.views_admin import \
                retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view
            results = retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view(
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                refresh_ballot_returned=True,
                date_last_updated_should_not_exceed=batch_process.date_started,
                batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
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
            from import_export_ballotpedia.views_admin import \
                refresh_ballotpedia_ballots_for_voters_api_v4_internal_view
            results = refresh_ballotpedia_ballots_for_voters_api_v4_internal_view(
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                date_last_updated_should_not_exceed=batch_process.date_started,
                batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
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
            from import_export_ballotpedia.views_admin import \
                retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view
            results = retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view(
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                refresh_ballot_returned=False,
                batch_process_ballot_item_chunk=batch_process_ballot_item_chunk,
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
                        batch_process_id=batch_process.id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                except Exception as e:
                    status += "RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
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
                if not positive_value_exists(retrieve_row_count):
                    if batch_process.kind_of_process == RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS \
                            or batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS \
                            or batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
                        # If no batch rows were found, we know the entire batch_process is finished.
                        # Update batch_process.date_completed to now
                        status += "RETRIEVE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE "
                        results = mark_batch_process_as_complete(batch_process, batch_process_ballot_item_chunk,
                                                                 batch_set_id=batch_set_id,
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
                status += "RETRIEVE_DATE_STARTED-NO_BATCH_SET_ID_FOUND-BATCH_IS_COMPLETE "
                results = mark_batch_process_as_complete(batch_process, batch_process_ballot_item_chunk,
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
                        batch_process_id=batch_process.id,
                        batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                        batch_set_id=batch_set_id,
                        critical_failure=True,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=results['status'],
                    )
                except Exception as e:
                    status += "CANNOT_SAVE_RETRIEVE_DATE_STARTED " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
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
                        batch_process_id=batch_process.id,
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
                if not positive_value_exists(number_of_batches):
                    if batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS or \
                            batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
                        # If no batch rows were found, we know the entire batch_process is finished.
                        # Update batch_process.date_completed to now
                        status += "ANALYZE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE "
                        results = mark_batch_process_as_complete(
                            batch_process, batch_process_ballot_item_chunk,
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
            else:
                status += "PROBLEM-BATCH_SET_ID_IS_MISSING_FROM_BALLOT_ITEM_CHUNK "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
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
                status += "RETRIEVE_DATE_COMPLETED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
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
                    batch_process_id=batch_process.id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
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
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_STARTED " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
            if not positive_value_exists(analyze_row_count):
                if batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
                    # If no batch rows were found, we know the entire batch_process is finished.
                    # Update batch_process.date_completed to now
                    status += "ANALYZE_DATE_STARTED-REFRESH_BALLOT_ITEMS_FROM_VOTERS-ANALYZE_ROW_COUNT_ZERO "
                    results = mark_batch_process_as_complete(batch_process, batch_process_ballot_item_chunk,
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
        else:
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
                    batch_process_id=batch_process.id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ANALYZE_DATE_COMPLETED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
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
                            batch_process, batch_process_ballot_item_chunk,
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
                            batch_process_id=batch_process.id,
                            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_process=kind_of_process,
                            state_code=state_code,
                            status=status,
                        )
                    except Exception as e:
                        status += "RESTARTED_FAILED_ANALYZE_PROCESS-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " \
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
                            batch_process_id=batch_process.id,
                            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                            batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_process=kind_of_process,
                            state_code=state_code,
                            status=status,
                        )
                    except Exception as e:
                        status += "ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " + str(e) + " "
                        handle_exception(e, logger=logger, exception_message=status)
                        results = {
                            'success': success,
                            'status': status,
                        }
                        return results
            else:
                status += "PROCESS_BATCH_SET-FALSE "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
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
            status += "CREATE_DATE_STARTED-CREATE_DATE_STARTED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_STARTED " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
                batch_process_id=batch_process.id,
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
                batch_process_id=batch_process.id,
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
                                status += "COULD_NOT_SAVE_ELECTION: " + str(e) + " "
                        else:
                            status += results['status']
                else:
                    status += results['status']

            status += "CREATE_DATE_STARTED-CREATE_DATE_COMPLETED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_COMPLETED " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
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
                                    status += "COULD_NOT_SAVE_ELECTION: " + str(e) + " "
                            else:
                                status += results['status']
                    else:
                        status += results['status']

                status += "CREATE_DATE_STARTED-CREATE_DATE_COMPLETED_SAVED "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_COMPLETED " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
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
            status += "ACTIVITY_NOTICE-CHECKED_OUT_TIME_NOT_SAVED " + str(e) + " "
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
                batch_process,
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
                batch_process.completion_summary = "ACTIVITY_NOTICE_RESULTS, " \
                                                   "activity_notice_seed_count: {activity_notice_seed_count} " \
                                                   "activity_notice_count: {activity_notice_count}" \
                                                   "".format(activity_notice_seed_count=activity_notice_seed_count,
                                                             activity_notice_count=activity_notice_count)
                batch_process.date_checked_out = None
                batch_process.date_completed = now()
                batch_process.save()

                if positive_value_exists(activity_notice_seed_count) or positive_value_exists(activity_notice_count):
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process.id,
                        kind_of_process=kind_of_process,
                        status=status,
                    )
            except Exception as e:
                status += "ACTIVITY_NOTICE-DATE_COMPLETED_TIME_NOT_SAVED " + str(e) + " "
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


def process_one_search_twitter_batch_process(batch_process):
    status = ""
    success = True
    batch_process_manager = BatchProcessManager()

    kind_of_process = batch_process.kind_of_process

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        batch_process.date_started = now()
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "CHECKED_OUT_TIME_NOT_SAVED " + str(e) + " "
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
            batch_process.completion_summary = "Candidates Analyzed: {candidates_analyzed} " \
                                               "out of {candidates_to_analyze}" \
                                               "".format(candidates_analyzed=candidates_analyzed,
                                                         candidates_to_analyze=candidates_to_analyze)
            batch_process.date_checked_out = None
            batch_process.date_completed = now()
            batch_process.save()

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                kind_of_process=kind_of_process,
                status=status,
            )
        except Exception as e:
            status += "DATE_COMPLETED_TIME_NOT_SAVED " + str(e) + " "
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
        status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES_FAILED "
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


def process_one_sitewide_daily_analytics_batch_process(batch_process):
    from import_export_batches.models import BatchProcessManager
    analytics_manager = AnalyticsManager()
    batch_process_manager = BatchProcessManager()
    status = ""
    success = True

    # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
    #  When the process is complete, we should reset this to "NULL"
    try:
        batch_process.date_checked_out = now()
        batch_process.date_started = now()
        batch_process.save()
    except Exception as e:
        status += "CHECKED_OUT_TIME_NOT_SAVED-SITEWIDE_DAILY " + str(e) + " "
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
    else:
        status += "SAVE_SITEWIDE_DAILY_METRICS-FAILED_TO_CALCULATE "

    try:
        if daily_metrics_calculated:
            batch_process.date_completed = now()
            batch_process.completion_summary = "Sitewide daily metrics SAVED"
        else:
            batch_process.completion_summary = "Sitewide daily metrics NOT saved"
        batch_process.date_checked_out = None
        batch_process.save()
    except Exception as e:
        status += "CHECKED_OUT_TIME_NOT_RESET: " + str(e) + " "
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


def mark_batch_process_as_complete(batch_process=None,
                                   batch_process_ballot_item_chunk=None,
                                   batch_set_id=0,
                                   google_civic_election_id=None,
                                   kind_of_process="",
                                   state_code=None,
                                   status=""):
    success = True
    batch_process_updated = False
    batch_process_ballot_item_chunk_updated = False
    batch_process_manager = BatchProcessManager()
    batch_process_id = 0
    batch_process_ballot_item_chunk_id = 0

    if batch_process:
        try:
            # Before saving batch_process, make sure we have the latest version. (For example, it might have been
            #  paused since it was first retrieved.)
            batch_process_results = batch_process_manager.retrieve_batch_process(batch_process.id)
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
            status += "CANNOT_MARK_BATCH_PROCESS_AS_COMPLETE " + str(e) + " "
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
            status += "CANNOT_MARK_BATCH_PROCESS_BALLOT_ITEM_CHUNK_AS_COMPLETE " + str(e) + " "
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

    if batch_process_ballot_item_chunk_updated or batch_process_ballot_item_chunk_updated:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
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
    }
    return results


def schedule_retrieve_ballotpedia_ballots_for_polling_locations_api_v4(
        google_civic_election_id="", state_code="", refresh_ballot_returned=False):
    status = ""

    # [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
    #  RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]
    if positive_value_exists(refresh_ballot_returned):
        kind_of_process = REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
    else:
        kind_of_process = RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
    status += "SCHEDULING " + str(kind_of_process) + " "

    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.create_batch_process(google_civic_election_id=google_civic_election_id,
                                                         kind_of_process=kind_of_process,
                                                         state_code=state_code)
    status += results['status']
    success = results['success']
    if results['batch_process_saved']:
        batch_process = results['batch_process']
        status += "SCHEDULED_REFRESH_BALLOTPEDIA_BALLOTS_FOR_VOTERS "
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


def schedule_refresh_ballotpedia_ballots_for_voters_api_v4(google_civic_election_id="", state_code="", voter_id=0):
    status = ""

    # [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
    #  RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]
    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.create_batch_process(google_civic_election_id=google_civic_election_id,
                                                         kind_of_process=REFRESH_BALLOT_ITEMS_FROM_VOTERS,
                                                         state_code=state_code,
                                                         voter_id=voter_id)
    status += results['status']
    success = results['success']
    if results['batch_process_saved']:
        batch_process = results['batch_process']
        status += "SCHEDULED_REFRESH_BALLOTPEDIA_BALLOTS_FOR_VOTERS "
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process.id,
            google_civic_election_id=batch_process.google_civic_election_id,
            kind_of_process=batch_process.kind_of_process,
            state_code=batch_process.state_code,
            status=status,
        )
    else:
        status += "FAILED_TO_SCHEDULE_REFRESH_BALLOTPEDIA_BALLOTS_FOR_VOTERS "
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
