# import_export_batches/controllers_representatives.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


from .models import BatchDescription, BatchManager, BatchProcessManager, BatchProcessRepresentativesChunk, \
    RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS
# REFRESH_REPRESENTATIVES_FROM_POLLING_LOCATIONS, REFRESH_REPRESENTATIVES_FROM_VOTERS
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils.timezone import localtime, now
from exception.models import handle_exception
from office_held.models import OfficesHeldForLocation
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def process_one_representatives_batch_process(batch_process):
    status = ""
    success = True
    batch_manager = BatchManager()
    batch_process_manager = BatchProcessManager()
    from .controllers_batch_process import mark_batch_process_as_complete, process_batch_set
    # These should be less than checked_out_expiration_time in retrieve_batch_process_list
    retrieve_time_out_duration = 3 * 60  # 3 minutes
    politician_match_time_out_duration = 3 * 60  # 3 minutes
    politician_deduplication_time_out_duration = 3 * 60  # 3 minutes

    kind_of_process = batch_process.kind_of_process
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
            kind_of_process=kind_of_process,
            state_code=state_code,
            status=status,
        )
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve BatchProcessRepresentativesChunk that has started but not completed
    results = retrieve_active_representatives_chunk_not_completed(
        batch_process_id=batch_process_id)
    if not results['success']:
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
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
    if results['batch_process_representatives_chunk_found']:
        batch_process_representatives_chunk = results['batch_process_representatives_chunk']
    else:
        # We need to create a new batch_process_representatives_chunk here.
        # We don't consider a batch_process completed until
        # a batch_process_representatives_chunk reports that there are no more items retrieved
        results = create_batch_process_representatives_chunk(batch_process_id=batch_process_id)
        if results['batch_process_representatives_chunk_created']:
            batch_process_representatives_chunk = results['batch_process_representatives_chunk']
        else:
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
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

    # If here, we have a batch_process_representatives_chunk to work on
    if batch_process_representatives_chunk.retrieve_date_started is None:
        # Kick off retrieve
        retrieve_success = False
        retrieve_row_count = 0
        batch_set_id = 0
        try:
            # If here, we are about to retrieve representatives
            batch_process_representatives_chunk.retrieve_date_started = now()
            batch_process_representatives_chunk.save()
            status += "RETRIEVE_DATE_STARTED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_STARTED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # If we have additional steps in processing representatives, get these two blocks working
        # if batch_process.kind_of_process == REFRESH_REPRESENTATIVES_FROM_POLLING_LOCATIONS:
        #     from import_export_batches.views_admin import \
        #         retrieve_ballots_for_polling_locations_api_v4_internal_view
        #     results = retrieve_ballots_for_polling_locations_api_v4_internal_view(
        #         batch_process_id=batch_process_id,
        #         batch_process_date_started=batch_process.date_started,
        #         google_civic_election_id=batch_process.google_civic_election_id,
        #         state_code=batch_process.state_code,
        #         refresh_ballot_returned=True,
        #         date_last_updated_should_not_exceed=batch_process.date_started,
        #         batch_process_representatives_chunk=batch_process_representatives_chunk,
        #         use_ballotpedia=batch_process.use_ballotpedia,
        #         use_ctcl=batch_process.use_ctcl,
        #         use_vote_usa=batch_process.use_vote_usa,
        #     )
        #     retrieve_success = positive_value_exists(results['success'])
        #     batch_set_id = results['batch_set_id']
        #     retrieve_row_count = results['retrieve_row_count']
        #     status += results['status']
        #     if 'batch_process_representatives_chunk' in results:
        #         if results['batch_process_representatives_chunk'] and \
        #                 hasattr(results['batch_process_representatives_chunk'], 'batch_set_id'):
        #             batch_process_representatives_chunk = results['batch_process_representatives_chunk']
        # elif batch_process.kind_of_process == REFRESH_REPRESENTATIVES_FROM_VOTERS:
        #     # Retrieving ballot items and cache in import_export_batches tables
        #     from import_export_batches.views_admin import refresh_ballots_for_voters_api_v4_internal_view
        #     results = refresh_ballots_for_voters_api_v4_internal_view(
        #         google_civic_election_id=batch_process.google_civic_election_id,
        #         state_code=batch_process.state_code,
        #         date_last_updated_should_not_exceed=batch_process.date_started,
        #         batch_process_representatives_chunk=batch_process_representatives_chunk,
        #         use_ballotpedia=batch_process.use_ballotpedia,
        #         use_ctcl=batch_process.use_ctcl,
        #         use_vote_usa=batch_process.use_vote_usa,
        #     )
        #     retrieve_success = positive_value_exists(results['success'])
        #     batch_set_id = results['batch_set_id']
        #     retrieve_row_count = results['retrieve_row_count']
        #     status += results['status']
        #     if 'batch_process_representatives_chunk' in results:
        #         if results['batch_process_representatives_chunk'] and \
        #                 hasattr(results['batch_process_representatives_chunk'], 'batch_set_id'):
        #             batch_process_representatives_chunk = results['batch_process_representatives_chunk']
        # el
        if batch_process.kind_of_process == RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS:
            from import_export_batches.views_representatives import \
                retrieve_representatives_for_polling_locations_internal_view
            results = retrieve_representatives_for_polling_locations_internal_view(
                batch_process_date_started=batch_process.date_started,
                state_code=batch_process.state_code,
                refresh_representatives=False,
                batch_process_representatives_chunk=batch_process_representatives_chunk,
                use_ballotpedia=batch_process.use_ballotpedia,
                use_ctcl=batch_process.use_ctcl,
                use_vote_usa=batch_process.use_vote_usa,
            )
            retrieve_success = positive_value_exists(results['success'])
            batch_set_id = results['batch_set_id']
            retrieve_row_count = results['retrieve_row_count']
            status += results['status']
            if 'batch_process_representatives_chunk' in results:
                if results['batch_process_representatives_chunk'] and \
                        hasattr(results['batch_process_representatives_chunk'], 'batch_set_id'):
                    batch_process_representatives_chunk = results['batch_process_representatives_chunk']

        if batch_process.kind_of_process in \
                [RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS]:
            pass
        if retrieve_success:
            if positive_value_exists(batch_set_id):
                try:
                    # If here, then ballots were retrieved, so we can set retrieve_date_completed
                    batch_process_representatives_chunk.batch_set_id = batch_set_id
                    batch_process_representatives_chunk.retrieve_row_count = retrieve_row_count
                    batch_process_representatives_chunk.retrieve_date_completed = now()
                    batch_process_representatives_chunk.save()
                    status += "RETRIEVE_DATE_STARTED-RETRIEVE_DATE_COMPLETED_SAVED "
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                        batch_set_id=batch_set_id,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                except Exception as e:
                    status += "ERROR-RETRIEVE_DATE_STARTED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                        batch_set_id=batch_set_id,
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
            else:
                status += "RETRIEVE_DATE_STARTED-NO_BATCH_SET_ID_FOUND-BATCH_IS_COMPLETE "
                results = mark_batch_process_as_complete(
                    batch_process=batch_process,
                    batch_process_representatives_chunk=batch_process_representatives_chunk,
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
                    batch_process_representatives_chunk.retrieve_date_started = None
                    batch_process_representatives_chunk.save()
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                        batch_set_id=batch_set_id,
                        critical_failure=True,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=results['status'],
                    )
                except Exception as e:
                    status += "ERROR-CANNOT_SAVE_RETRIEVE_DATE_STARTED: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    batch_process_manager.create_batch_process_log_entry(
                        batch_process_id=batch_process_id,
                        batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                        batch_set_id=batch_set_id,
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
                        batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                        batch_set_id=batch_set_id,
                        critical_failure=True,
                        kind_of_process=kind_of_process,
                        state_code=state_code,
                        status=status,
                    )
                except Exception as e:
                    status += "ERROR-CANNOT_WRITE_TO_BATCH_PROCESS_LOG: " + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)

    elif batch_process_representatives_chunk.retrieve_date_completed is None:
        # Check to see if retrieve process has timed out
        date_when_retrieve_has_timed_out = \
            batch_process_representatives_chunk.retrieve_date_started + timedelta(seconds=retrieve_time_out_duration)
        if now() > date_when_retrieve_has_timed_out:
            # If so, set retrieve_date_completed to now and set retrieve_timed_out to True
            # But first, see if any rows were found
            # Were there batches created in the batch set from the retrieve?
            number_of_batches = 0
            if positive_value_exists(batch_process_representatives_chunk.batch_set_id):
                number_of_batches = batch_manager.count_number_of_batches_in_batch_set(
                    batch_set_id=batch_process_representatives_chunk.batch_set_id)
                # if not positive_value_exists(number_of_batches):
                #     # We don't want to stop here anymore
                #     if batch_process.kind_of_process == REFRESH_REPRESENTATIVES_FROM_POLLING_LOCATIONS or \
                #             batch_process.kind_of_process == REFRESH_REPRESENTATIVES_FROM_VOTERS:
                #         # If no batch rows were found, we know the entire batch_process is finished.
                #         # Update batch_process.date_completed to now
                #         status += "POLITICIAN_MATCH_DATE_STARTED-NO_RETRIEVE_VALUES_FOUND-BATCH_IS_COMPLETE2 "
                #         results = mark_batch_process_as_complete(
                #             batch_process=batch_process,
                #             batch_process_representatives_chunk=batch_process_representatives_chunk,
                #             batch_set_id=batch_process_representatives_chunk.batch_set_id,
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
                status += "PROBLEM-BATCH_SET_ID_IS_MISSING_FROM_REPRESENTATIVES_CHUNK "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
                # But proceed so we can mark the retrieve part of batch_process_representatives_chunk as complete
            try:
                if not positive_value_exists(batch_process_representatives_chunk.retrieve_row_count):
                    # Make sure to store the retrieve_row_count if it wasn't already stored
                    batch_process_representatives_chunk.retrieve_row_count = number_of_batches
                batch_process_representatives_chunk.retrieve_date_completed = now()
                batch_process_representatives_chunk.retrieve_timed_out = True
                batch_process_representatives_chunk.save()
            except Exception as e:
                status += "ERROR-RETRIEVE_DATE_COMPLETED-CANNOT_SAVE_RETRIEVE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
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
    elif batch_process_representatives_chunk.politician_matching_date_started is None:
        # ###################
        # This is where we start POLITICIAN_MATCH
        status += "STARTING_POLITICIAN_MATCH_WITH_DATE_STARTED_NONE "

        if not positive_value_exists(batch_process_representatives_chunk.batch_set_id):
            status += "MISSING_REPRESENTATIVES_CHUNK_BATCH_SET_ID "
            try:
                batch_process_representatives_chunk.politician_matching_date_started = now()
                batch_process_representatives_chunk.politician_matching_date_completed = now()
                batch_process_representatives_chunk.save()
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-POLITICIAN_MATCH_DATE_STARTED-CANNOT_SAVE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
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
            if not positive_value_exists(batch_process_representatives_chunk.retrieve_row_count):
                # Were there OfficesHeldForLocation stored?
                pass
            batch_process_representatives_chunk.politician_matching_date_started = now()
            batch_process_representatives_chunk.save()
            status += "POLITICIAN_MATCH_DATE_STARTED-DATE_STARTED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-POLITICIAN_MATCH_DATE_STARTED-CANNOT_SAVE_DATE_STARTED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # Now run the process to match politicians to all new representatives with False "politician_match_attempted"
        from representative.controllers import match_representatives_to_politicians_first_attempt
        results = match_representatives_to_politicians_first_attempt(state_code=state_code)
        status += results['status']
        activity_summary = \
            "number_of_representatives_reviewed: {number_of_representatives_reviewed}, " \
            "matched_to_existing_politician: {matched_to_existing_politician}, " \
            "new_politicians_created: {new_politicians_created}, " \
            "multiple_possible_politicians_found: {multiple_possible_politicians_found}, " \
            "".format(
                matched_to_existing_politician=results['matched_to_existing_politician'],
                multiple_possible_politicians_found=results['multiple_possible_politicians_found'],
                new_politicians_created=results['new_politicians_created'],
                number_of_representatives_reviewed=results['number_of_representatives_reviewed'],
            )
        status += activity_summary
        politician_matching_row_count = results['matched_to_existing_politician'] + results['new_politicians_created']
        status += "[politician_matching_row_count: " + str(politician_matching_row_count) + "] "
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                critical_failure=True,
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
            batch_process_representatives_chunk.politician_matching_row_count = politician_matching_row_count
            batch_process_representatives_chunk.politician_matching_date_completed = now()
            batch_process_representatives_chunk.save()
            status += "POLITICIAN_MATCH_DATE_STARTED-DATE_COMPLETED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-POLITICIAN_MATCH_DATE_STARTED-CANNOT_SAVE_DATE_COMPLETED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

    elif batch_process_representatives_chunk.politician_matching_date_completed is None:
        # ###################
        # This is an POLITICIAN_MATCH process that failed part way through
        status += "RESTARTING_FAILED_POLITICIAN_MATCH_PROCESS "

        if not positive_value_exists(batch_process_representatives_chunk.batch_set_id):
            status += "MISSING_REPRESENTATIVES_CHUNK_BATCH_SET_ID "
            try:
                batch_process_representatives_chunk.politician_matching_date_completed = now()
                batch_process_representatives_chunk.save()
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-POLITICIAN_MATCH_DATE_COMPLETED-CANNOT_SAVE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
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
        date_when_politician_match_has_timed_out = \
            batch_process_representatives_chunk.politician_matching_date_started + \
            timedelta(seconds=politician_match_time_out_duration)
        if now() > date_when_politician_match_has_timed_out:
            # Mark it as completed, since future processes will do the same task
            try:
                batch_process_representatives_chunk.politician_matching_date_completed = now()
                batch_process_representatives_chunk.save()
                status += "POLITICIAN_MATCH_DATE_COMPLETED-DATE_COMPLETED_SAVED "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-POLITICIAN_MATCH_DATE_STARTED-CANNOT_SAVE_DATE_COMPLETED: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                results = {
                    'success': success,
                    'status': status,
                }
                return results
        else:
            # Wait
            status += "WAIT_BECAUSE_FORMER_POLITICIAN_MATCH_PROCESS_COULD_STILL_BE_RUNNING "
            results = {
                'success': success,
                'status': status,
            }
            return results
    elif batch_process_representatives_chunk.politician_deduplication_date_started is None:
        try:
            # If here, we know that the politician_matching_date_completed has a value
            batch_process_representatives_chunk.politician_deduplication_date_started = now()
            batch_process_representatives_chunk.save()
            status += "POLITICIAN_DEDUPLICATION_DATE_STARTED-SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-POLITICIAN_DEDUPLICATION_DATE_STARTED-CANNOT_SAVE_DATE_STARTED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # Now run the process to match politicians to all new representatives with False "politician_match_attempted"
        from representative.controllers import deduplicate_politicians_first_attempt
        results = deduplicate_politicians_first_attempt(state_code=state_code)
        # results = {
        #     'decisions_required': decisions_required,
        #     'merge_errors': merge_errors,
        #     'multiple_possible_politicians_found': multiple_possible_politicians_found,
        #     'politicians_merged': politicians_merged,
        #     'politicians_not_merged': politicians_not_merged,
        #     'success': success,
        #     'status': status,
        # }
        status += results['status']
        activity_summary = \
            "number_of_politicians_reviewed: {number_of_politicians_reviewed}, " \
            "politicians_merged: {politicians_merged}, " \
            "politicians_not_merged: {politicians_not_merged}, " \
            "decisions_required: {decisions_required}, " \
            "multiple_possible_politicians_found: {multiple_possible_politicians_found}, " \
            "".format(
                decisions_required=results['decisions_required'],
                multiple_possible_politicians_found=results['multiple_possible_politicians_found'],
                politicians_merged=results['politicians_merged'],
                politicians_not_merged=results['politicians_not_merged'],
                number_of_politicians_reviewed=results['number_of_politicians_reviewed'],
            )
        status += activity_summary
        politician_deduplication_row_count = results['politicians_merged']
        status += "[politician_deduplication_row_count: " + str(politician_deduplication_row_count) + "] "
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                critical_failure=True,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results
        # Process "delete" entries
        results = process_batch_set(batch_set_id=batch_process_representatives_chunk.batch_set_id, delete_all=True)
        status += results['status']
        if not positive_value_exists(results['success']):
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                critical_failure=True,
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
            batch_process_representatives_chunk.politician_deduplication_row_count = politician_deduplication_row_count
            batch_process_representatives_chunk.politician_deduplication_date_completed = now()
            batch_process_representatives_chunk.save()

            status += "POLITICIAN_DEDUPLICATION_DATE_STARTED-DATE_COMPLETED_SAVED "
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
        except Exception as e:
            status += "ERROR-POLITICIAN_DEDUPLICATION_DATE_STARTED-CANNOT_SAVE_DATE_COMPLETED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                batch_set_id=batch_process_representatives_chunk.batch_set_id,
                kind_of_process=kind_of_process,
                state_code=state_code,
                status=status,
            )
            results = {
                'success': success,
                'status': status,
            }
            return results

    elif batch_process_representatives_chunk.politician_deduplication_date_completed is None:
        date_when_politician_deduplication_has_timed_out = \
            batch_process_representatives_chunk.politician_deduplication_date_started + \
            timedelta(seconds=politician_deduplication_time_out_duration)
        if now() > date_when_politician_deduplication_has_timed_out:
            try:
                batch_process_representatives_chunk.politician_deduplication_date_completed = now()
                batch_process_representatives_chunk.politician_deduplication_timed_out = True
                batch_process_representatives_chunk.save()

                status += "POLITICIAN_DEDUPLICATION_DATE_STARTED-DATE_COMPLETED_SAVED "
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    status=status,
                )
            except Exception as e:
                status += "ERROR-POLITICIAN_DEDUPLICATION_DATE_STARTED-CANNOT_SAVE_DATE_COMPLETED2: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                batch_process_manager.create_batch_process_log_entry(
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk.id,
                    batch_set_id=batch_process_representatives_chunk.batch_set_id,
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


def create_batch_process_representatives_chunk(batch_process_id=0, batch_set_id=0):
    status = ""
    success = True
    batch_process_representatives_chunk = None
    batch_process_representatives_chunk_created = False

    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.retrieve_batch_process(batch_process_id=batch_process_id)
    if not results['batch_process_found']:
        status += results['status'] + "BATCH_PROCESS_REPRESENTATIVES_CHUNK_NOT_FOUND "
        results = {
            'success':                                      success,
            'status':                                       status,
            'batch_process_representatives_chunk':          batch_process_representatives_chunk,
            'batch_process_representatives_chunk_created':  batch_process_representatives_chunk_created,
        }
        return results

    batch_process = results['batch_process']

    try:
        batch_process_representatives_chunk = BatchProcessRepresentativesChunk.objects.create(
            batch_process_id=batch_process.id,
            batch_set_id=batch_set_id,
            state_code=batch_process.state_code,
        )
        if batch_process_representatives_chunk:
            status += 'BATCH_PROCESS_REPRESENTATIVES_CHUNK_SAVED '
            batch_process_representatives_chunk_created = True
        else:
            status += 'FAILED_TO_POLITICIAN_DEDUPLICATION_BATCH_PROCESS_REPRESENTATIVES_CHUNK '
    except Exception as e:
        success = False
        status += 'COULD_NOT_SAVE_BATCH_PROCESS_REPRESENTATIVES_CHUNK: ' + str(e) + ' '

    results = {
        'success':                                      success,
        'status':                                       status,
        'batch_process_representatives_chunk':          batch_process_representatives_chunk,
        'batch_process_representatives_chunk_created':  batch_process_representatives_chunk_created,
    }
    return results


def retrieve_active_representatives_chunk_not_completed(batch_process_id=0):
    status = ""
    success = True
    batch_process_representatives_chunk = None
    batch_process_representatives_chunk_found = False
    try:
        batch_process_queryset = BatchProcessRepresentativesChunk.objects.all()
        batch_process_queryset = batch_process_queryset.filter(batch_process_id=batch_process_id)

        # Limit to chunks that have at least one completed_date == NULL
        filters = []  # Reset for each search word
        new_filter = Q(retrieve_date_completed__isnull=True)
        filters.append(new_filter)

        new_filter = Q(politician_matching_date_completed__isnull=True)
        filters.append(new_filter)

        new_filter = Q(politician_deduplication_date_completed__isnull=True)
        filters.append(new_filter)

        # Add the first query
        final_filters = filters.pop()
        # ...and "OR" the remaining items in the list
        for item in filters:
            final_filters |= item
        batch_process_queryset = batch_process_queryset.filter(final_filters)

        batch_process_queryset = batch_process_queryset.order_by("id")
        batch_process_representatives_chunk = batch_process_queryset.first()
        if batch_process_representatives_chunk:
            batch_process_representatives_chunk_found = True
            status += 'BATCH_PROCESS_REPRESENTATIVES_CHUNK_RETRIEVED '
        else:
            status += 'BATCH_PROCESS_REPRESENTATIVES_CHUNK_NOT_FOUND '
    except BatchProcessRepresentativesChunk.DoesNotExist:
        # No chunk found. Not a problem.
        status += 'BATCH_PROCESS_REPRESENTATIVES_CHUNK_NOT_FOUND_DoesNotExist '
    except Exception as e:
        status += 'FAILED_BATCH_PROCESS_REPRESENTATIVES_CHUNK_RETRIEVE: ' + str(e) + " "
        success = False

    results = {
        'success':                                  success,
        'status':                                   status,
        'batch_process_representatives_chunk':      batch_process_representatives_chunk,
        'batch_process_representatives_chunk_found': batch_process_representatives_chunk_found,
    }
    return results


def retrieve_polling_location_we_vote_id_list_from_offices_held_for_location(
        state_code='',
        limit=750):
    polling_location_we_vote_id_list = []
    status = ''
    success = True
    status += "OfficesHeldForLocation LIMIT: " + str(limit) + " "

    try:
        if positive_value_exists(state_code):
            query = OfficesHeldForLocation.objects.using('readonly')\
                .order_by('-date_last_updated')\
                .filter(state_code__iexact=state_code)\
                .exclude(Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
        else:
            query = OfficesHeldForLocation.objects.using('readonly')\
                .order_by('-date_last_updated') \
                .exclude(Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
        query = \
            query.values_list('polling_location_we_vote_id', flat=True).distinct()
        if positive_value_exists(limit):
            polling_location_we_vote_id_list = query[:limit]
        else:
            polling_location_we_vote_id_list = list(query)
    except Exception as e:
        status += "COULD_NOT_RETRIEVE_POLLING_LOCATION_LIST " + str(e) + " "
    # status += "PL_LIST: " + str(polling_location_we_vote_id_list) + " "
    polling_location_we_vote_id_list_found = positive_value_exists(len(polling_location_we_vote_id_list))
    results = {
        'success':                                  success,
        'status':                                   status,
        'polling_location_we_vote_id_list_found':   polling_location_we_vote_id_list_found,
        'polling_location_we_vote_id_list':         polling_location_we_vote_id_list,
    }
    return results
