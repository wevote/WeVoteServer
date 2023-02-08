# import_export_batches/views_representatives.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BatchProcessManager, \
    BatchSet, \
    BATCH_SET_SOURCE_IMPORT_GOOGLE_CIVIC_REPRESENTATIVES, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, \
    RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS
from .controllers_batch_process import process_next_representatives
from admin_tools.views import redirect_to_sign_in_page
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db.models import Q
from django.utils.timezone import now
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from exception.models import handle_exception
from import_export_google_civic.controllers import REPRESENTATIVES_BY_ADDRESS_URL
import json
from polling_location.models import KIND_OF_LOG_ENTRY_REPRESENTATIVES_RECEIVED, PollingLocation, PollingLocationManager
import random
import requests
from representative.models import RepresentativeManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def import_representatives_for_location_view(request):
    """
    Reach out to external data source API to retrieve the current representatives for one location.
    """
    status = ""
    success = True

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', "")
    use_google_civic = positive_value_exists(request.GET.get('use_google_civic', False))
    use_ballotpedia = positive_value_exists(request.GET.get('use_ballotpedia', False))
    use_ctcl = positive_value_exists(request.GET.get('use_ctcl', False))
    use_vote_usa = positive_value_exists(request.GET.get('use_vote_usa', False))

    polling_location_manager = PollingLocationManager()
    polling_location_state_code = ""
    if positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_we_vote_id = polling_location.we_vote_id
            polling_location_state_code = polling_location.state
        else:
            status += results['status']
            success = False
    else:
        success = False

    kind_of_batch = ""

    update_or_create_rules = {
        'create_office_helds':      True,
        'create_representatives':   True,
        'update_office_helds':      False,
        'update_representatives':   False,
    }

    # See pattern in 'import_ballot_items_for_location_view' if we want to support other data providers
    if not success:
        status += "FAILED_RETRIEVING_POLLING_LOCATION_PRIOR_TO_IMPORTING_REPRESENTATIVES "
    elif positive_value_exists(use_ballotpedia):
        status += "BALLOTPEDIA_NOT_SUPPORTED_AS_DATA_SOURCE "
    elif positive_value_exists(use_ctcl):
        status += "CTCL_NOT_SUPPORTED_AS_DATA_SOURCE "
    elif positive_value_exists(use_google_civic):
        status += "USE_GOOGLE_CIVIC_IS_DATA_SOURCE "
        from import_export_google_civic.controllers_representatives \
            import retrieve_google_civic_representatives_from_polling_location_api
        results = retrieve_google_civic_representatives_from_polling_location_api(
            polling_location_we_vote_id=polling_location_we_vote_id,
            state_code=state_code,
            update_or_create_rules=update_or_create_rules,
        )
        status += results['status']
    elif positive_value_exists(use_vote_usa):
        status += "VOTE_USA_NOT_SUPPORTED_AS_DATA_SOURCE "
    else:
        # Should not be possible to get here
        pass

    messages.add_message(request, messages.INFO, status)
    if positive_value_exists(polling_location_we_vote_id):
        return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                            args=(polling_location_we_vote_id,)) +
                                    "?polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&state_code=" + str(state_code)
                                    )
    else:
        return HttpResponseRedirect(reverse('polling_location:polling_location_list',
                                            args=()) +
                                    "?polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&state_code=" + str(state_code)
                                    )


def process_next_representatives_view(request):
    json_results = process_next_representatives()

    response = HttpResponse(json.dumps(json_results), content_type='application/json')
    return response


@login_required
def retrieve_representatives_for_polling_locations_view(request):
    """
    Reach out to Google Civic and loop through:
    1) Polling locations/Map Points (so we can use those addresses to retrieve the
    elected representatives all over the country)
    2) Cycle through those map points
    :param request:
    :return:
    """
    status = ""

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    kind_of_processes_to_show = request.GET.get('kind_of_processes_to_show', '')
    state_code = request.GET.get('state_code', '')
    refresh_representatives = request.GET.get('refresh_representatives', False)
    use_batch_process = request.GET.get('use_batch_process', False)
    use_ballotpedia = request.GET.get('use_ballotpedia', False)
    use_ballotpedia = positive_value_exists(use_ballotpedia)
    use_ctcl = request.GET.get('use_ctcl', False)
    use_ctcl = positive_value_exists(use_ctcl)
    use_vote_usa = request.GET.get('use_vote_usa', False)
    use_vote_usa = positive_value_exists(use_vote_usa)
    # import_limit = convert_to_int(request.GET.get('import_limit', 1000))  # If > 1000, we get error 414 (url too long)

    if positive_value_exists(use_batch_process):
        from import_export_batches.controllers_batch_process import \
            schedule_retrieve_representatives_for_polling_locations
        results = schedule_retrieve_representatives_for_polling_locations(
            state_code=state_code,
            refresh_representatives=refresh_representatives,
            use_ballotpedia=use_ballotpedia,
            use_ctcl=use_ctcl,
            use_vote_usa=use_vote_usa)
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    '?state_code=' + str(state_code) +
                                    '&kind_of_processes_to_show=' + str(kind_of_processes_to_show)
                                    )
    else:
        return retrieve_representatives_for_polling_locations_internal_view(
            request=request,
            from_browser=True,
            state_code=state_code,
            refresh_representatives=refresh_representatives,
            use_ballotpedia=use_ballotpedia,
            use_ctcl=use_ctcl,
            use_vote_usa=use_vote_usa)


def retrieve_representatives_for_polling_locations_internal_view(
        request=None,
        batch_process_id=0,
        from_browser=False,
        state_code="",
        refresh_representatives=False,
        date_last_updated_should_not_exceed=None,
        batch_process_representatives_chunk=None,
        batch_process_date_started=None,
        use_ballotpedia=False,
        use_ctcl=False,
        use_vote_usa=False):
    status = ""
    success = True

    batch_process_representatives_chunk_id = 0
    batch_set_id = 0
    retrieve_row_count = 0
    batch_process_manager = BatchProcessManager()
    polling_location_manager = PollingLocationManager()
    representative_manager = RepresentativeManager()
    try:
        if positive_value_exists(refresh_representatives):
            kind_of_process = REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
        else:
            kind_of_process = RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS

        if not positive_value_exists(batch_process_date_started) or not positive_value_exists(batch_process_id):
            try:
                if not positive_value_exists(batch_process_id):
                    batch_process_id = batch_process_representatives_chunk.batch_process_id
                results = batch_process_manager.retrieve_batch_process(
                    batch_process_id=batch_process_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    use_ctcl=use_ctcl,
                    use_vote_usa=use_vote_usa,
                )
                if results['batch_process_found']:
                    batch_process = results['batch_process']
                    batch_process_date_started = batch_process.date_started
            except Exception as e:
                status += "COULD_NOT_GET_BATCH_PROCESS_ID_FROM_BATCH_PROCESS_REPRESENTATIVES_CHUNK: " + str(e) + ' '
        if not positive_value_exists(batch_process_date_started):
            try:
                results = batch_process_manager.retrieve_batch_process(
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    use_ctcl=use_ctcl,
                    use_vote_usa=use_vote_usa,
                )
                if results['batch_process_found']:
                    batch_process = results['batch_process']
                    batch_process_date_started = batch_process.date_started
            except Exception as e:
                status += "COULD_NOT_GET_BATCH_PROCESS_FROM_ASSORTED_VARIABLES: " + str(e) + ' '

        # Retrieve the polling locations/map points already in OfficesHeldForLocation table
        # results = ballot_returned_list_manager.retrieve_polling_location_we_vote_id_list_from_ballot_returned(
        from import_export_batches.controllers_representatives import \
            retrieve_polling_location_we_vote_id_list_from_offices_held_for_location
        results = retrieve_polling_location_we_vote_id_list_from_offices_held_for_location(
            state_code=state_code,
            limit=0,
        )
        status += results['status']
        if results['polling_location_we_vote_id_list_found']:
            polling_location_we_vote_id_list_from_offices_held_for_location = results['polling_location_we_vote_id_list']
        else:
            polling_location_we_vote_id_list_from_offices_held_for_location = []

        # Find polling_location_we_vote_ids already used in this batch_process, which returned a ballot
        polling_location_we_vote_id_list_already_retrieved = []
        if positive_value_exists(batch_process_id):
            polling_location_log_entry_list = polling_location_manager.retrieve_polling_location_log_entry_list(
                batch_process_id=batch_process_id,
                is_from_ctcl=use_ctcl,
                is_from_vote_usa=use_vote_usa,
                kind_of_log_entry_list=[KIND_OF_LOG_ENTRY_REPRESENTATIVES_RECEIVED],
            )
            for one_log_entry in polling_location_log_entry_list:
                if one_log_entry.polling_location_we_vote_id not in polling_location_we_vote_id_list_already_retrieved:
                    polling_location_we_vote_id_list_already_retrieved.append(one_log_entry.polling_location_we_vote_id)

        # Find polling locations/map points which have come up empty
        #  (from this data source) in previous chunks since when this process started
        polling_location_we_vote_id_list_representatives_missing = []
        results = representative_manager.\
            retrieve_polling_location_we_vote_id_list_from_representatives_are_missing(
                batch_process_date_started=batch_process_date_started,
                is_from_google_civic=True,
                state_code=state_code,
            )
        if results['polling_location_we_vote_id_list_found']:
            polling_location_we_vote_id_list_representatives_missing = results['polling_location_we_vote_id_list']

        status += "REFRESH_REPRESENTATIVES: " + str(refresh_representatives) + " "

        # # For both REFRESH and RETRIEVE, see if the number of map points for this state exceed the "large" threshold
        # refresh_or_retrieve_limit = \
        #     polling_location_manager.calculate_number_of_map_points_to_retrieve_with_each_batch_chunk(state_code)
        # Because of Google Civic rate limits per minute, we want to limit to 50 per process.
        from polling_location.models import MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_REPRESENTATIVES_API
        refresh_or_retrieve_limit = MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_REPRESENTATIVES_API

        # if positive_value_exists(refresh_representatives):
        #     # REFRESH branch
        #     polling_location_query = PollingLocation.objects.using('readonly').all()
        #     # In this "Refresh" branch, use polling locations we already have a ballot returned entry for, and
        #     # exclude map points already retrieved in this batch and those returned empty since this process started
        #     polling_location_we_vote_id_list_to_exclude = \
        #         list(set(polling_location_we_vote_id_list_already_retrieved +
        #                  polling_location_we_vote_id_list_representatives_missing))
        #     polling_location_we_vote_id_list_to_retrieve = \
        #         list(set(polling_location_we_vote_id_list_from_offices_held_for_location) -
        #              set(polling_location_we_vote_id_list_to_exclude))
        #     polling_location_we_vote_id_list_to_retrieve_limited = \
        #         polling_location_we_vote_id_list_to_retrieve[:refresh_or_retrieve_limit]
        #     polling_location_query = \
        #         polling_location_query.filter(we_vote_id__in=polling_location_we_vote_id_list_to_retrieve_limited)
        #     if positive_value_exists(use_ctcl):
        #         # CTCL only supports full addresses, so don't bother trying to pass addresses without line1
        #         polling_location_query = \
        #             polling_location_query.exclude(Q(line1__isnull=True) | Q(line1__exact=''))
        #     # We don't exclude the deleted map points because we need to know to delete the ballot returned entry
        #     # polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        #     polling_location_list = list(polling_location_query)
        # else:
        # RETRIEVE branch
        polling_location_query = PollingLocation.objects.using('readonly').all()
        polling_location_query = \
            polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_query = \
            polling_location_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                           Q(zip_long__exact=''))
        polling_location_query = polling_location_query.filter(state__iexact=state_code)
        # In this "Retrieve" branch, exclude polling locations we already have a representative returned entry for, and
        # exclude map points already retrieved in this batch and those returned empty since this process started
        polling_location_we_vote_id_list_to_exclude = \
            list(set(polling_location_we_vote_id_list_from_offices_held_for_location +
                     polling_location_we_vote_id_list_already_retrieved +
                     polling_location_we_vote_id_list_representatives_missing))
        polling_location_query = \
            polling_location_query.exclude(we_vote_id__in=polling_location_we_vote_id_list_to_exclude)
        polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        if positive_value_exists(use_ctcl):
            # CTCL only supports full addresses, so don't bother trying to pass addresses without line1
            polling_location_query = \
                polling_location_query.exclude(Q(line1__isnull=True) | Q(line1__exact=''))

        # Randomly change the sort order, so we over time load different map points (before timeout)
        random_sorting = random.randint(1, 5)
        if random_sorting == 1:
            # Ordering by "line1" creates a bit of (locational) random order
            polling_location_list = polling_location_query.order_by('line1')[:refresh_or_retrieve_limit]
            status += "RANDOM_SORTING-LINE1-ASC: " + str(random_sorting) + " "
        elif random_sorting == 2:
            polling_location_list = polling_location_query.order_by('-line1')[:refresh_or_retrieve_limit]
            status += "RANDOM_SORTING-LINE1-DESC: " + str(random_sorting) + " "
        elif random_sorting == 3:
            polling_location_list = polling_location_query.order_by('city')[:refresh_or_retrieve_limit]
            status += "RANDOM_SORTING-CITY-ASC: " + str(random_sorting) + " "
        else:
            polling_location_list = polling_location_query.order_by('-city')[:refresh_or_retrieve_limit]
            status += "RANDOM_SORTING-CITY-DESC: " + str(random_sorting) + " "
        # END OF ELSE BRANCH - if positive_value_exists(refresh_representatives):

        # # Cycle through -- if the polling_location is deleted, delete the associated ballot_returned,
        # #  and then remove the polling_location from the list
        # modified_polling_location = []
        # for one_polling_location in polling_location_list:
        #     if positive_value_exists(one_polling_location.polling_location_deleted):
        #         delete_results = ballot_returned_manager.delete_ballot_returned_by_identifier(
        #             google_civic_election_id=google_civic_election_id,
        #             polling_location_we_vote_id=one_polling_location.we_vote_id)
        #         if delete_results['ballot_deleted']:
        #             status += "BR_PL_DELETED (" + str(one_polling_location.we_vote_id) + ") "
        #         else:
        #             status += "BR_PL_NOT_DELETED (" + str(one_polling_location.we_vote_id) + ") "
        #     else:
        #         modified_polling_location.append(one_polling_location)
        # polling_location_list = modified_polling_location
        polling_location_count = len(polling_location_list)
    except PollingLocation.DoesNotExist:
        message = 'Could not retrieve (as opposed to refresh) ballot data for the state \'{state}\'. ' \
                  ''.format(
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results
    except Exception as e:
        message = 'Could not retrieve (as opposed to refresh) representatives for the state \'{state}\'. ' \
                  'ERROR: {error}' \
                  ''.format(
                     error=str(e),
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    if polling_location_count == 0:
        message = 'Data for all map points for the state \'{state}\' ' \
                  'have been retrieved once. Please use RETRIEVE to get latest data. ' \
                  'date_last_updated_should_not_exceed: \'{date_last_updated_should_not_exceed}\'. ' \
                  '(result 2 - retrieve_ballots_for_polling_locations_api_v4_view)'.format(
                     date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()))
        else:
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    successful_representatives_api_call = 0
    failed_representatives_api_call = 0

    existing_offices_held_by_ocd_and_name_dict = {}
    existing_representative_objects_dict = {}
    existing_representative_to_office_held_links_dict = {}
    new_office_held_we_vote_ids_list = []
    new_representative_we_vote_ids_list = []

    # if positive_value_exists(use_ballotpedia):
    #     batch_set_source = BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_REPRESENTATIVES
    #     source_uri = BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL
    # elif positive_value_exists(use_ctcl):
    #     batch_set_source = BATCH_SET_SOURCE_IMPORT_CTCL_REPRESENTATIVES
    #     source_uri = CTCL_VOTER_INFO_URL
    # elif positive_value_exists(use_vote_usa):
    #     batch_set_source = BATCH_SET_SOURCE_IMPORT_VOTE_USA_REPRESENTATIVES
    #     source_uri = VOTE_USA_VOTER_INFO_URL
    # else:
    batch_set_source = BATCH_SET_SOURCE_IMPORT_GOOGLE_CIVIC_REPRESENTATIVES
    source_uri = REPRESENTATIVES_BY_ADDRESS_URL

    batch_set_id = 0
    if len(polling_location_list) > 0:
        status += "POLLING_LOCATIONS_FOR_THIS_BATCH_SET: " + str(len(polling_location_list)) + " "
        # Create Batch Set for ballot items
        import_date = date.today()
        batch_set_name = "Representatives for"
        if positive_value_exists(state_code):
            batch_set_name += " (state " + str(state_code.upper()) + ")"
        if positive_value_exists(use_ballotpedia):
            batch_set_name += " - ballotpedia"
        elif positive_value_exists(use_ctcl):
            batch_set_name += " - ctcl"
        elif positive_value_exists(use_vote_usa):
            batch_set_name += " - vote usa"
        else:
            batch_set_name += " - google civic"
        batch_set_name += " - " + str(import_date)

        try:
            batch_process_representatives_chunk_id = batch_process_representatives_chunk.id
            batch_process_id = batch_process_representatives_chunk.batch_process_id
            batch_set_id = batch_process_representatives_chunk.batch_set_id
        except Exception as e:
            status += "BATCH_PROCESS_REPRESENTATIVES_CHUNK: " + str(e) + ' '

        if not positive_value_exists(batch_set_id):
            # create batch_set object
            try:
                batch_set = BatchSet.objects.create(
                    batch_set_description_text="",
                    batch_set_name=batch_set_name,
                    batch_set_source=batch_set_source,
                    batch_process_id=batch_process_id,
                    batch_process_representatives_chunk_id=batch_process_representatives_chunk_id,
                    source_uri=source_uri,
                    import_date=import_date,
                    state_code=state_code)
                batch_set_id = batch_set.id
                status += " BATCH_SET_CREATED-REPRESENTATIVES_FOR_POLLING_LOCATIONS "
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_SET: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                success = False

            try:
                if positive_value_exists(batch_process_representatives_chunk_id) and positive_value_exists(batch_set_id):
                    batch_process_representatives_chunk.batch_set_id = batch_set_id
                    batch_process_representatives_chunk.save()
            except Exception as e:
                status += "UNABLE_TO_SAVE_BATCH_SET_ID_EARLY: " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)

    update_or_create_rules = {
        'create_office_helds':      True,
        'create_representatives':   True,
        'update_office_helds':      False,
        'update_representatives':   False,
    }

    if success:
        # if positive_value_exists(use_ballotpedia):
        #     from import_export_ballotpedia.controllers import \
        #         retrieve_ballotpedia_ballot_items_from_polling_location_api_v4
        # elif positive_value_exists(use_ctcl):
        #     from import_export_ctcl.controllers import retrieve_ctcl_ballot_items_from_polling_location_api
        # elif positive_value_exists(use_vote_usa):
        #     from import_export_vote_usa.controllers import retrieve_vote_usa_ballot_items_from_polling_location_api
        # else:
        from import_export_google_civic.controllers_representatives \
            import retrieve_google_civic_representatives_from_polling_location_api
        reps_not_returned_from_these_polling_location_we_vote_ids = []
        reps_returned_from_these_polling_location_we_vote_ids = []
        for polling_location in polling_location_list:
            # If we start retrieving from other data sources (than Google Civic), add the switches here
            # if positive_value_exists(use_vote_usa):
            one_location_results = retrieve_google_civic_representatives_from_polling_location_api(
                polling_location_we_vote_id=polling_location.we_vote_id,
                polling_location=polling_location,
                state_code=state_code,
                batch_process_id=batch_process_id,
                batch_set_id=batch_set_id,
                existing_offices_held_by_ocd_and_name_dict=existing_offices_held_by_ocd_and_name_dict,
                existing_representative_objects_dict=existing_representative_objects_dict,
                existing_representative_to_office_held_links_dict=existing_representative_to_office_held_links_dict,
                new_office_held_we_vote_ids_list=new_office_held_we_vote_ids_list,
                new_representative_we_vote_ids_list=new_representative_we_vote_ids_list,
                update_or_create_rules=update_or_create_rules,
            )

            if one_location_results and 'success' in one_location_results and one_location_results['success']:
                success = True

            existing_offices_held_by_ocd_and_name_dict = \
                one_location_results['existing_offices_held_by_ocd_and_name_dict']
            existing_representative_objects_dict = one_location_results['existing_representative_objects_dict']
            existing_representative_to_office_held_links_dict = \
                one_location_results['existing_representative_to_office_held_links_dict']
            new_office_held_we_vote_ids_list = one_location_results['new_office_held_we_vote_ids_list']
            new_representative_we_vote_ids_list = one_location_results['new_representative_we_vote_ids_list']

            if one_location_results['successful_representatives_api_call']:
                successful_representatives_api_call += 1
                reps_returned_from_these_polling_location_we_vote_ids.append(
                    polling_location.we_vote_id)
                if successful_representatives_api_call < 5 and positive_value_exists(one_location_results['status']):
                    # Only show this error message status for the first 4 times, so we don't overwhelm the log
                    status += "REPRESENTATIVES_RETRIEVED: [[[" + one_location_results['status'] + "]]] "
            else:
                failed_representatives_api_call += 1
                reps_not_returned_from_these_polling_location_we_vote_ids.append(
                    polling_location.we_vote_id)
                if failed_representatives_api_call < 5 and positive_value_exists(one_location_results['status']):
                    # Only show this error message status for the first 4 times, so we don't overwhelm the log
                    status += "REPRESENTATIVES_NOT_RETRIEVED: [[[" + one_location_results['status'] + "]]] "
        if positive_value_exists(len(reps_returned_from_these_polling_location_we_vote_ids)):
            status += "reps_returned_from_these_polling_location_we_vote_ids: " + \
                      str(reps_returned_from_these_polling_location_we_vote_ids) + " "
        if positive_value_exists(len(reps_not_returned_from_these_polling_location_we_vote_ids)):
            status += "reps_not_returned_from_these_polling_location_we_vote_ids: " + \
                      str(reps_not_returned_from_these_polling_location_we_vote_ids) + " "
    else:
        status += "CANNOT_CALL_RETRIEVE_BECAUSE_OF_ERRORS " \
                  "[retrieve_ballots_for_polling_locations_api_v4_internal_view] "
    retrieve_row_count = successful_representatives_api_call

    existing_offices_found = 0
    # if google_civic_election_id in existing_offices_held_by_ocd_and_name_dict:
    #     existing_offices_found = len(existing_offices_held_by_ocd_and_name_dict[google_civic_election_id])
    existing_representatives_found = len(existing_representative_objects_dict)
    new_office_helds_found = len(new_office_held_we_vote_ids_list)
    new_representatives_found = len(new_representative_we_vote_ids_list)

    if from_browser:
        messages.add_message(request, messages.INFO,
                             'OfficesHeldForLocation retrieved from Map Points for the {state_code}. '
                             'Successful API calls: {successful_representatives_api_call}, '
                             'Failed API calls: {failed_representatives_api_call}. '
                             'new office_helds: {new_office_helds_found} (existing: {existing_offices_found}) '
                             'new reps: {new_representatives_found} (existing: {existing_representatives_found}) '
                             ''.format(
                                 successful_representatives_api_call=successful_representatives_api_call,
                                 failed_representatives_api_call=failed_representatives_api_call,
                                 existing_offices_found=existing_offices_found,
                                 existing_representatives_found=existing_representatives_found,
                                 new_office_helds_found=new_office_helds_found,
                                 new_representatives_found=new_representatives_found,
                                 state_code=state_code,
                             ))

        messages.add_message(request, messages.INFO, 'status: {status}'.format(status=status))

        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=IMPORT_BALLOTPEDIA_REPRESENTATIVES')
    else:
        status += \
            'Representatives retrieved for {state_code} (from Map Points). ' \
            'Successful API calls: {successful_representatives_api_call}. ' \
            'Failed API calls: {failed_representatives_api_call}. ' \
            'new office_helds: {new_office_helds_found} (existing: {existing_offices_found}) ' \
            'new reps: {new_representatives_found} (existing: {existing_representatives_found}) ' \
            ''.format(
                successful_representatives_api_call=successful_representatives_api_call,
                failed_representatives_api_call=failed_representatives_api_call,
                existing_offices_found=existing_offices_found,
                existing_representatives_found=existing_representatives_found,
                new_office_helds_found=new_office_helds_found,
                new_representatives_found=new_representatives_found,
                state_code=state_code,
            )
        results = {
            'status':               status,
            'success':              success,
            'batch_set_id':         batch_set_id,
            'retrieve_row_count':   retrieve_row_count,
            'batch_process_representatives_chunk':  batch_process_representatives_chunk,
        }
        return results
