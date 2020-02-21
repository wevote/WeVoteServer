# import_export_batches/controllers_batch_process.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import create_batch_row_actions, import_data_from_batch_row_actions
from .models import BatchDescription, BatchManager, BatchProcessManager, \
    IMPORT_CREATE, \
    RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, \
    REFRESH_BALLOT_ITEMS_FROM_VOTERS
from datetime import datetime, timedelta
from django.utils.timezone import localtime, now
import pytz
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


def batch_process_next_steps():
    success = True
    status = ""
    batch_manager = BatchManager()
    batch_process_manager = BatchProcessManager()

    if not fetch_batch_process_system_on():
        status += "BATCH_PROCESS_SYSTEM_TURNED_OFF "
        results = {
            'success': success,
            'status': status,
        }
        return results

    # If we have more than 3 batch_processes that are still active, don't start a new batch_process
    total_active_batch_processes = batch_process_manager.count_active_batch_processes()
    status += "TOTAL_ACTIVE_BATCH_PROCESSES: " + str(total_active_batch_processes) + ", "

    total_checked_out_batch_processes = batch_process_manager.count_checked_out_batch_processes()
    status += "CHECKED_OUT_BATCH_PROCESSES: " + str(total_checked_out_batch_processes) + ", "

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

    # If less than 1 start a new one
    if total_active_batch_processes < 3 and batch_process_list_count < 1:
        new_batch_process_list_count = 0
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
            for new_batch in new_batch_process_list:
                # Bring the batch_process_list up to 1 item
                if len(batch_process_list) < 1:
                    kind_of_process = ""
                    try:
                        kind_of_process = new_batch.kind_of_process
                        new_batch.date_started = now()
                        new_batch.save()
                        batch_process_list.append(new_batch)
                    except Exception as e:
                        status += "BATCH_PROCESS-CANNOT_SAVE_DATE_STARTED " + str(e) + " "
                        batch_process_manager.create_batch_process_log_entry(
                            batch_process_id=new_batch.id,
                            kind_of_process=kind_of_process,
                            status=status,
                        )
        status += "NEW_BATCH_PROCESS_COUNT: " + str(new_batch_process_list_count) + ", "

    for batch_process in batch_process_list:
        if batch_process.kind_of_process in \
                [REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_VOTERS,
                 RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS]:
            results = process_one_ballot_item_batch_process(batch_process)
            status += results['status']

            # When a batch_process is running, we mark when it was "taken off the shelf" to be worked on.
            #  When the process is complete, we should reset this to "NULL"
            try:
                batch_process.date_checked_out = None
                batch_process.save()
            except Exception as e:
                status += "COULD_NOT_SET_CHECKED_OUT_TIME_TO_NULL " + str(e) + " "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    google_civic_election_id=batch_process.google_civic_election_id,
                    kind_of_process=batch_process.kind_of_process,
                    state_code=batch_process.state_code,
                    status=status,
                )
        else:
            status += "KIND_OF_PROCESS_NOT_RECOGNIZED "

    results = {
        'success': success,
        'status': status,
    }
    return results


def process_one_ballot_item_batch_process(batch_process):
    status = ""
    success = True
    batch_manager = BatchManager()
    batch_process_manager = BatchProcessManager()
    retrieve_time_out_duration = 30 * 60  # 30 minutes * 60 seconds
    analyze_time_out_duration = 30 * 60  # 30 minutes
    create_time_out_duration = 20 * 60  # 30 minutes

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
        batch_process.date_checked_out = now()
        batch_process.save()
    except Exception as e:
        status += "CHECKED_OUT_TIME_NOT_SAVED " + str(e) + " "
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
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']
        elif batch_process.kind_of_process == REFRESH_BALLOT_ITEMS_FROM_VOTERS:
            # Retrieving ballot items and cache in import_export_batches tables
            from import_export_ballotpedia.views_admin import \
                refresh_ballotpedia_ballots_for_voters_api_v4_internal_view
            results = refresh_ballotpedia_ballots_for_voters_api_v4_internal_view(
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                date_last_updated_should_not_exceed=batch_process.date_started,
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']
        elif batch_process.kind_of_process == RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS:
            from import_export_ballotpedia.views_admin import \
                retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view
            results = retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view(
                google_civic_election_id=batch_process.google_civic_election_id,
                state_code=batch_process.state_code,
                refresh_ballot_returned=False,
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']

        if retrieve_success:
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
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                except Exception as e:
                    status += "RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED " + str(e) + " "
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
                if not positive_value_exists(retrieve_row_count):
                    # If no batch rows were found, we know the entire batch_process is finished.
                    # Update batch_process.date_completed to now
                    status += "RETRIEVE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE "
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
                        critical_failure=True,
                        google_civic_election_id=google_civic_election_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=results['status'],
                    )
                except Exception as e:
                    status += "CANNOT_SAVE_RETRIEVE_DATE_STARTED " + str(e) + " "
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
    elif batch_process_ballot_item_chunk.retrieve_date_completed is None:
        # Check to see if retrieve process has timed out
        date_when_retrieve_has_timed_out = \
            batch_process_ballot_item_chunk.retrieve_date_started + timedelta(seconds=retrieve_time_out_duration)
        if now() > date_when_retrieve_has_timed_out:
            # If so, set retrieve_date_completed to now and set retrieve_timed_out to True
            # But first, see if any rows were found
            number_of_batches = 0
            if not positive_value_exists(batch_process_ballot_item_chunk.retrieve_row_count):
                # Were there batches created in the batch set from the retrieve?
                if positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
                    number_of_batches = batch_manager.count_number_of_batches_in_batch_set(
                        batch_set_id=batch_process_ballot_item_chunk.batch_set_id)
                if not positive_value_exists(number_of_batches):
                    # If no batch rows were found, we know the entire batch_process is finished.
                    # Update batch_process.date_completed to now
                    status += "ANALYZE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE "
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
            try:
                if not positive_value_exists(batch_process_ballot_item_chunk.retrieve_row_count):
                    # Make sure to store the retrieve_row_count if it wasn't already stored
                    batch_process_ballot_item_chunk.retrieve_row_count = number_of_batches
                batch_process_ballot_item_chunk.retrieve_date_completed = now()
                batch_process_ballot_item_chunk.retrieve_timed_out = True
                batch_process_ballot_item_chunk.save()
            except Exception as e:
                status += "RETRIEVE_DATE_COMPLETED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED " + str(e) + " "
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
        else:
            # Wait
            results = {
                'success': success,
                'status': status,
            }
            return results
    elif batch_process_ballot_item_chunk.analyze_date_started is None:
        # If here, we know that the retrieve_date_completed has a value
        number_of_batches = 0
        if not positive_value_exists(batch_process_ballot_item_chunk.retrieve_row_count):
            # Were there batches created in the batch set from the retrieve?
            if positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
                number_of_batches = batch_manager.count_number_of_batches_in_batch_set(
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id)
            if not positive_value_exists(number_of_batches):
                # If no batch rows were found, we know the entire batch_process is finished.
                # Update batch_process.date_completed to now
                status += "ANALYZE_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE "
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
        try:
            # If here we know we have batches that need to be analyzed
            if not positive_value_exists(batch_process_ballot_item_chunk.retrieve_row_count):
                # Make sure to store the retrieve_row_count if it wasn't already stored
                batch_process_ballot_item_chunk.retrieve_row_count = number_of_batches
            batch_process_ballot_item_chunk.analyze_date_started = now()
            batch_process_ballot_item_chunk.save()
            status += "ANALYZE_DATE_STARTED-ANALYZE_DATE_STARTED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_STARTED " + str(e) + " "
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
        # Now analyze the batch that was stored in the "refresh_ballotpedia_ballots..." function
        results = process_batch_set(
            batch_set_id=batch_process_ballot_item_chunk.batch_set_id, analyze_all=True)
        analyze_row_count = results['batch_rows_analyzed']
        status += results['status']
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
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
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ANALYZE_DATE_STARTED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " + str(e) + " "
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

    elif batch_process_ballot_item_chunk.analyze_date_completed is None:
        # Check to see if analyze process has timed out
        date_when_analyze_has_timed_out = \
            batch_process_ballot_item_chunk.analyze_date_started + timedelta(seconds=analyze_time_out_duration)
        if now() > date_when_analyze_has_timed_out:
            # Before seeing if we should mark analyze_date_completed, are there are still items in the
            # batch set that need to be analyzed?
            if positive_value_exists(batch_process_ballot_item_chunk.batch_set_id):
                number_not_analyzed = batch_manager.count_number_of_batches_in_batch_set(
                    batch_set_id=batch_process_ballot_item_chunk.batch_set_id, batch_row_analyzed=False)
                if positive_value_exists(number_not_analyzed):
                    # Now analyze the batch that was stored in the "refresh_ballotpedia_ballots..." function
                    results = process_batch_set(
                        batch_set_id=batch_process_ballot_item_chunk.batch_set_id, analyze_all=True)
                    status += results['status']
                # We have time for this to run before the time out check above is run again,
                # since we have this batch checked out
            try:
                # Set analyze_date_completed to now and set analyze_timed_out to True
                batch_process_ballot_item_chunk.analyze_date_completed = now()
                batch_process_ballot_item_chunk.analyze_timed_out = True
                # Update analyze_row_count
                batch_process_ballot_item_chunk.analyze_row_count = \
                    batch_manager.count_number_of_batches_in_batch_set(
                        batch_set_id=batch_process_ballot_item_chunk.batch_set_id, batch_row_analyzed=True)
                batch_process_ballot_item_chunk.save()
                status += "ANALYZE_DATE_COMPLETED-ANALYZE_DATE_COMPLETED_SAVED "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ANALYZE_DATE_COMPLETED-CANNOT_SAVE_ANALYZE_DATE_COMPLETED " + str(e) + " "
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
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_STARTED " + str(e) + " "
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
        results = process_batch_set(
            batch_set_id=batch_process_ballot_item_chunk.batch_set_id, create_all=True)
        create_row_count = results['batch_rows_created']
        status += results['status']
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
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
            # If here, we know that the process_batch_set has been created
            batch_process_ballot_item_chunk.create_row_count = create_row_count
            batch_process_ballot_item_chunk.create_date_completed = now()
            batch_process_ballot_item_chunk.save()
            status += "CREATE_DATE_STARTED-CREATE_DATE_COMPLETED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process.id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_COMPLETED " + str(e) + " "
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
                status += "CREATE_DATE_STARTED-CREATE_DATE_COMPLETED_SAVED "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process.id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk.id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "CREATE_DATE_STARTED-CANNOT_SAVE_CREATE_DATE_COMPLETED " + str(e) + " "
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


def process_batch_set(batch_set_id=0, analyze_all=False, create_all=False):
    """

    :param batch_set_id:
    :param analyze_all:
    :param create_all:
    :return:
    """
    status = ""
    success = True
    batch_rows_analyzed = 0
    batch_rows_created = 0

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
        batch_description_query = batch_description_query.filter(batch_description_analyzed=False)
        batch_list = list(batch_description_query)

        for one_batch_description in batch_list:
            results = create_batch_row_actions(
                one_batch_description.batch_header_id,
                election_objects_dict=election_objects_dict,
                measure_objects_dict=measure_objects_dict,
                office_objects_dict=office_objects_dict,
            )
            if results['batch_actions_created']:
                batch_rows_analyzed += 1
                try:
                    # If BatchRowAction's were created for BatchDescription, this batch_description was analyzed
                    one_batch_description.batch_description_analyzed = True
                    one_batch_description.save()
                    batch_header_id_created_list.append(one_batch_description.batch_header_id)
                except Exception as e:
                    status += "ANALYZE-COULD_NOT_SAVE_BATCH_DESCRIPTION " + str(e) + " "

            election_objects_dict = results['election_objects_dict']
            measure_objects_dict = results['measure_objects_dict']
            office_objects_dict = results['office_objects_dict']
        status += "BATCH_ROWS_ANALYZED: " + str(batch_rows_analyzed) + ", "
    elif positive_value_exists(create_all):
        batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
        batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
        batch_list = list(batch_description_query)

        batch_rows_created = 0
        for one_batch_description in batch_list:
            results = import_data_from_batch_row_actions(
                one_batch_description.kind_of_batch, IMPORT_CREATE, one_batch_description.batch_header_id)
            if results['number_of_table_rows_created']:
                batch_rows_created += 1

            if not positive_value_exists(results['success']) and len(status) < 1024:
                status += results['status']
        status += "BATCH_ROWS_CREATED: " + str(batch_rows_created) + ", "
    else:
        status += "MUST_SPECIFY_ANALYZE_OR_CREATE "

    results = {
        'success':              success,
        'status':               status,
        'batch_rows_analyzed':  batch_rows_analyzed,
        'batch_rows_created':   batch_rows_created,
    }
    return results


def mark_batch_process_as_complete(batch_process=None,
                                   batch_process_ballot_item_chunk=None,
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
            batch_process_id = batch_process.id
            if batch_process.date_started is None:
                batch_process.date_started = now()
            if batch_process.date_completed is None:
                batch_process.date_completed = now()
            batch_process.save()
            batch_process_updated = True
            status += "BATCH_PROCESS_MARKED_COMPLETE "
        except Exception as e:
            success = False
            status += "CANNOT_MARK_BATCH_PROCESS_AS_COMPLETE " + str(e) + " "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
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
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )

    if batch_process_ballot_item_chunk_updated or batch_process_ballot_item_chunk_updated:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
            batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
            google_civic_election_id=google_civic_election_id,
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )

    results = {
        'success':              success,
        'status':               status,
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
