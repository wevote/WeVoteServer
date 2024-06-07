# import_export_batches/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ACTIVITY_NOTICE_PROCESS, API_REFRESH_REQUEST, \
    BatchDescription, BatchHeader, BatchHeaderMap, BatchManager, \
    BatchProcess, BatchProcessAnalyticsChunk, BatchProcessBallotItemChunk, BatchProcessLogEntry, BatchProcessManager, \
    BatchProcessRepresentativesChunk, BatchRow, BatchRowActionBallotItem, BatchRowActionPollingLocation, \
    BatchSet, \
    CONTEST_OFFICE, OFFICE_HELD, IMPORT_BALLOT_ITEM, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_OFFICES_HELD, BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS, \
    BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS, BATCH_SET_SOURCE_IMPORT_CTCL_BALLOT_ITEMS, \
    BATCH_SET_SOURCE_IMPORT_GOOGLE_CIVIC_REPRESENTATIVES, BATCH_SET_SOURCE_IMPORT_VOTE_USA_BALLOT_ITEMS, \
    IMPORT_CREATE, IMPORT_DELETE, IMPORT_ALREADY_DELETED, IMPORT_ADD_TO_EXISTING, IMPORT_POLLING_LOCATION, \
    IMPORT_VOTER, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, \
    REFRESH_BALLOT_ITEMS_FROM_VOTERS, RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, \
    RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS
from .controllers import create_batch_header_translation_suggestions, create_batch_row_actions, \
    update_or_create_batch_header_mapping, export_voter_list_with_emails, import_data_from_batch_row_actions
from .controllers_batch_process import pass_through_batch_list_incoming_variables, process_next_activity_notices, \
    process_next_ballot_items, process_next_general_maintenance
from .controllers_ballotpedia import store_ballotpedia_json_response_to_import_batch_system
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager, BallotReturnedManager, MEASURE, CANDIDATE, POLITICIAN
import csv
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db.models import Q
from django.utils.timezone import now
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from urllib.parse import quote
from election.models import Election, ElectionManager
from exception.models import handle_exception
from import_export_ballotpedia.controllers import groom_ballotpedia_data_for_processing, \
    process_ballotpedia_voter_districts, BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL
from import_export_ctcl.controllers import CTCL_VOTER_INFO_URL
from import_export_google_civic.controllers import REPRESENTATIVES_BY_ADDRESS_URL
from import_export_vote_usa.controllers import VOTE_USA_VOTER_INFO_URL
import json
import math
from polling_location.models import KIND_OF_LOG_ENTRY_BALLOT_RECEIVED, KIND_OF_LOG_ENTRY_REPRESENTATIVES_RECEIVED, \
    MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK, PollingLocation, PollingLocationManager
from position.models import POSITION
import random
import requests
from volunteer_task.models import VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED, VolunteerTaskManager
from voter.models import voter_has_authority
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, positive_value_exists, STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def batches_home_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # Create a voter_device_id and voter in the database if one doesn't exist yet
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    template_values = {
        'google_civic_election_id': google_civic_election_id,
    }
    response = render(request, 'import_export_batches/index.html', template_values)

    return response


@login_required
def batch_list_view(request):
    """
    Display a list of import batches
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    kind_of_batch = request.GET.get('kind_of_batch', '')
    batch_file = request.GET.get('batch_file', '')
    batch_uri = request.GET.get('batch_uri', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', '')
    polling_location_city = request.GET.get('polling_location_city', '')
    polling_location_zip = request.GET.get('polling_location_zip', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))

    messages_on_stage = get_messages(request)
    batch_list_found = False
    modified_batch_list = []
    batch_manager = BatchManager()
    try:
        batch_list_query = BatchDescription.objects.order_by('-batch_header_id')
        if positive_value_exists(kind_of_batch):
            batch_list_query = batch_list_query.filter(kind_of_batch__iexact=kind_of_batch)
        if positive_value_exists(google_civic_election_id):
            batch_list_query = batch_list_query.filter(google_civic_election_id=google_civic_election_id)

        if positive_value_exists(google_civic_election_id):
            batch_list = list(batch_list_query)
        else:
            batch_list = batch_list_query[:50]

        if len(batch_list):
            batch_list_found = True
            for one_batch in batch_list:
                one_batch.batch_row_action_count = batch_manager.fetch_batch_row_action_count(
                    one_batch.batch_header_id, kind_of_batch)
                one_batch.batch_row_action_to_update_count = batch_manager.fetch_batch_row_action_count(
                    one_batch.batch_header_id, kind_of_batch, IMPORT_ADD_TO_EXISTING)
                one_batch.batch_row_count = batch_manager.fetch_batch_row_count(one_batch.batch_header_id)
                modified_batch_list.append(one_batch)

    except BatchDescription.DoesNotExist:
        # This is fine
        batch_list_found = False
        pass

    polling_location_found = False
    polling_location = PollingLocation()
    polling_location_manager = PollingLocationManager()
    election_state = ''
    if not polling_location_found and positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_we_vote_id = polling_location.we_vote_id
            polling_location_id = polling_location.id
            polling_location_found = True
            election_state = polling_location.state

    election_manager = ElectionManager()
    if google_civic_election_id:
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            election_state = election.get_election_state()
    polling_location_list = []
    results = polling_location_manager.retrieve_polling_locations_in_city_or_state(
        election_state, polling_location_city, polling_location_zip)
    if results['polling_location_list_found']:
        polling_location_list = results['polling_location_list']

    if kind_of_batch == ORGANIZATION_WORD or kind_of_batch == OFFICE_HELD \
            or kind_of_batch == POLITICIAN or kind_of_batch == IMPORT_POLLING_LOCATION:
        # We do not want to ask the person importing the file for an election, because it isn't used
        ask_for_election = False
        election_list = []
    else:
        ask_for_election = True

        if positive_value_exists(show_all_elections):
            results = election_manager.retrieve_elections()
            election_list = results['election_list']
        else:
            results = election_manager.retrieve_upcoming_elections()
            election_list = results['election_list']
            # Make sure we always include the current election in the election_list, even if it is older
            if positive_value_exists(google_civic_election_id):
                this_election_found = False
                for one_election in election_list:
                    if convert_to_int(one_election.google_civic_election_id) == \
                            convert_to_int(google_civic_election_id):
                        this_election_found = True
                        break
                if not this_election_found:
                    results = election_manager.retrieve_election(google_civic_election_id)
                    if results['election_found']:
                        one_election = results['election']
                        election_list.append(one_election)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'batch_list':               modified_batch_list,
        'ask_for_election':         ask_for_election,
        'election_list':            election_list,
        'kind_of_batch':            kind_of_batch,
        'batch_file':               batch_file,
        'batch_uri':                batch_uri,
        'google_civic_election_id': convert_to_int(google_civic_election_id),
        'polling_location_we_vote_id': polling_location_we_vote_id,
        'polling_location':         polling_location,
        'polling_location_list':    polling_location_list,
        'polling_location_city':    polling_location_city,
        'polling_location_zip':     polling_location_zip,
        'show_all_elections':       show_all_elections,
    }
    return render(request, 'import_export_batches/batch_list.html', template_values)


@login_required
def batch_list_process_view(request):
    """
    Load in a new batch to start the importing process
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    kind_of_batch = request.POST.get('kind_of_batch', '')
    batch_uri = request.POST.get('batch_uri', '')
    batch_uri_encoded = quote(batch_uri) if positive_value_exists(batch_uri) else ""
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    polling_location_we_vote_id = request.POST.get('polling_location_we_vote_id', "")
    polling_location_city = request.POST.get('polling_location_city', '')
    polling_location_zip = request.POST.get('polling_location_zip', '')
    show_all_elections = positive_value_exists(request.POST.get('show_all_elections', ""))
    state_code = request.POST.get('state_code', "")
    if kind_of_batch not in (CANDIDATE, CONTEST_OFFICE, OFFICE_HELD, IMPORT_BALLOT_ITEM, IMPORT_POLLING_LOCATION,
                             MEASURE, ORGANIZATION_WORD, POSITION, POLITICIAN):
        messages.add_message(request, messages.ERROR, 'The kind_of_batch is required for a batch import.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&polling_location_city=" + str(polling_location_city) +
                                    "&polling_location_zip=" + str(polling_location_zip) +
                                    "&show_all_elections=" + str(show_all_elections) +
                                    "&batch_uri=" + batch_uri_encoded)

    # If here we know we have the required variables
    organization_we_vote_id = request.POST.get('organization_we_vote_id', '')
    # Was form submitted, or was election just changed?
    import_batch_button = request.POST.get('import_batch_button', '')
    batch_file = None

    if positive_value_exists(import_batch_button):
        try:
            if request.method == 'POST' and request.FILES['batch_file']:
                batch_file = request.FILES['batch_file']
        except KeyError:
            pass

    # Make sure we have a file to process  // Used to only be able to import IMPORT_BALLOT_ITEM from file
    if kind_of_batch in [IMPORT_POLLING_LOCATION, ORGANIZATION_WORD] and not batch_file:
        messages.add_message(request, messages.ERROR, 'Please select a file to import.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&polling_location_city=" + str(polling_location_city) +
                                    "&polling_location_zip=" + str(polling_location_zip) +
                                    "&show_all_elections=" + str(show_all_elections) +
                                    "&batch_uri=" + batch_uri_encoded)

    # Make sure we have a Google Civic Election ID *unless* we are uploading an organization
    if kind_of_batch not in [IMPORT_POLLING_LOCATION, ORGANIZATION_WORD] \
            and not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'This kind_of_batch (\"{kind_of_batch}\") requires you '
                                                      'to choose an election.'.format(kind_of_batch=kind_of_batch))
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&polling_location_city=" + str(polling_location_city) +
                                    "&polling_location_zip=" + str(polling_location_zip) +
                                    "&show_all_elections=" + str(show_all_elections) +
                                    "&batch_uri=" + batch_uri_encoded)

    # Make sure we have a polling_location_we_vote_id
    # if kind_of_batch in IMPORT_BALLOT_ITEM and not positive_value_exists(polling_location_we_vote_id):
    #     messages.add_message(request, messages.ERROR, 'This kind_of_batch (\"{kind_of_batch}\") requires you '
    #                                                   'to choose a map point.'
    #                                                   ''.format(kind_of_batch=kind_of_batch))
    #     return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
    #                                 "?kind_of_batch=" + str(kind_of_batch) +
    #                                 "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
    #                                 "&google_civic_election_id=" + str(google_civic_election_id) +
    #                                 "&polling_location_city=" + str(polling_location_city) +
    #                                 "&polling_location_zip=" + str(polling_location_zip) +
    #                                 "&show_all_elections=" + str(show_all_elections) +
    #                                 "&batch_uri=" + batch_uri_encoded)

    election_name = ""  # For printing status
    if positive_value_exists(google_civic_election_id):
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            election_name = election.election_name

    batch_header_id = 0
    if positive_value_exists(import_batch_button):  # If the button was pressed...
        batch_manager = BatchManager()

        if batch_file is not None:
            results = batch_manager.create_batch_from_local_file_upload(
                batch_file, kind_of_batch, google_civic_election_id, organization_we_vote_id,
                polling_location_we_vote_id)
            if results['batch_saved']:
                messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
                                                             ''.format(election_name=election_name))
                batch_header_id = results['batch_header_id']
            else:
                messages.add_message(request, messages.ERROR, results['status'])
        elif positive_value_exists(batch_uri):
            if "api.ballotpedia.org" in batch_uri:
                # response = requests.get(VOTER_INFO_URL, params={
                #     "key": GOOGLE_CIVIC_API_KEY,
                #     "address": text_for_map_search,
                #     "electionId": incoming_google_civic_election_id,
                # })
                response = requests.get(batch_uri)
                structured_json = json.loads(response.text)

                if "api/contains" in batch_uri:
                    contains_api = True
                else:
                    contains_api = False

                groom_results = groom_ballotpedia_data_for_processing(structured_json, google_civic_election_id,
                                                                      state_code, contains_api)
                modified_json_list = groom_results['modified_json_list']
                kind_of_batch = groom_results['kind_of_batch']

                if contains_api:
                    ballot_items_results = process_ballotpedia_voter_districts(
                        google_civic_election_id, state_code, modified_json_list, polling_location_we_vote_id)

                    if ballot_items_results['ballot_items_found']:
                        modified_json_list = ballot_items_results['ballot_item_dict_list']

                results = store_ballotpedia_json_response_to_import_batch_system(
                    modified_json_list, google_civic_election_id, kind_of_batch)  # Add state_code=state_code ?
            else:
                # check file type
                filetype = batch_manager.find_file_type(batch_uri)
                if "xml" in filetype:
                    # file is XML
                    # Retrieve the VIP data from XML
                    results = batch_manager.create_batch_vip_xml(batch_uri, kind_of_batch, google_civic_election_id,
                                                                 organization_we_vote_id)
                else:
                    results = batch_manager.create_batch_from_uri(
                        batch_uri, kind_of_batch, google_civic_election_id, organization_we_vote_id)

            if results['batch_saved']:
                messages.add_message(request, messages.INFO, 'Import batch-batch_saved for '
                                                             '{election_name} election saved.'
                                                             ''.format(election_name=election_name))
                batch_header_id = results['batch_header_id']
            else:
                messages.add_message(request, messages.ERROR, results['status'])

    if positive_value_exists(batch_header_id):
        # Go straight to the new batch
        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    "?batch_header_id=" + str(batch_header_id) +
                                    "&kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&batch_uri=" + batch_uri_encoded)
    else:
        # Go to the batch listing page
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&polling_location_city=" + str(polling_location_city) +
                                    "&polling_location_zip=" + str(polling_location_zip) +
                                    "&show_all_elections=" + str(show_all_elections) +
                                    "&batch_uri=" + batch_uri_encoded)


@login_required
def batch_action_list_view(request):
    """
    Display row-by-row details of batch actions being reviewed, leading up to processing an entire batch.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_set_list = []
    polling_location_we_vote_id = ""
    status = ""

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    show_all = request.GET.get('show_all', False)
    state_code = request.GET.get('state_code', '')
    position_owner_organization_we_vote_id = request.GET.get('position_owner_organization_we_vote_id', '')

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    batch_set_id = 0
    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
        batch_set_id = batch_description.batch_set_id
        google_civic_election_id = batch_description.google_civic_election_id
        polling_location_we_vote_id = batch_description.polling_location_we_vote_id
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    batch_set_list_found = False
    # if batch_set_id exists, send data sets associated with this batch_set_id
    if positive_value_exists(batch_set_id):
        try:
            batch_set_list = BatchSet.objects.get(id=batch_set_id)
            if batch_set_list:
                batch_set_list_found = True
        except BatchSet.DoesNotExist:
            # This is fine
            batch_set_list = BatchSet()
            batch_set_list_found = False

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()

    batch_list_found = False
    batch_row_count = 0
    try:
        batch_row_count_query = BatchRow.objects.order_by('id')
        batch_row_count_query = batch_row_count_query.filter(batch_header_id=batch_header_id)
        if positive_value_exists(state_code):
            batch_row_count_query = batch_row_count_query.filter(state_code__iexact=state_code)

        batch_row_count = batch_row_count_query.count()

        batch_row_query = BatchRow.objects.order_by('id')
        batch_row_query = batch_row_query.filter(batch_header_id=batch_header_id)

        if positive_value_exists(state_code):
            batch_row_query = batch_row_query.filter(state_code__iexact=state_code)
            batch_row_list = list(batch_row_query)
        else:
            if positive_value_exists(show_all):
                batch_row_list = list(batch_row_query)
            else:
                batch_row_list = batch_row_query[:200]
        if len(batch_row_list):
            batch_list_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_row_list = []
        batch_list_found = False

    modified_batch_row_list = []
    active_state_codes = []
    batch_manager = BatchManager()
    if batch_list_found:
        for one_batch_row in batch_row_list:
            if positive_value_exists(one_batch_row.state_code):
                if one_batch_row.state_code not in active_state_codes:
                    active_state_codes.append(one_batch_row.state_code)

            if kind_of_batch == CANDIDATE:
                existing_results = batch_manager.retrieve_batch_row_action_candidate(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_candidate']
                    one_batch_row.kind_of_batch = CANDIDATE
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == CONTEST_OFFICE:
                existing_results = batch_manager.retrieve_batch_row_action_contest_office(batch_header_id,
                                                                                          one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_contest_office']
                    one_batch_row.kind_of_batch = CONTEST_OFFICE
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == OFFICE_HELD:
                existing_results = batch_manager.retrieve_batch_row_action_office_held(batch_header_id,
                                                                                          one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_office_held']
                    one_batch_row.kind_of_batch = OFFICE_HELD
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == IMPORT_BALLOT_ITEM:
                # Retrieve Creates and Updates
                existing_results = \
                    batch_manager.retrieve_batch_row_action_ballot_item(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_ballot_item']
                    one_batch_row.kind_of_batch = IMPORT_BALLOT_ITEM
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
                # Retrieve Deletes
            elif kind_of_batch == IMPORT_POLLING_LOCATION:
                # Retrieve Creates and Updates
                existing_results = \
                    batch_manager.retrieve_batch_row_action_polling_location(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_polling_location']
                    one_batch_row.kind_of_batch = IMPORT_POLLING_LOCATION
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == IMPORT_VOTER:
                existing_results = \
                    batch_manager.retrieve_batch_row_action_ballot_item(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_ballot_item']
                    one_batch_row.kind_of_batch = IMPORT_VOTER
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == MEASURE:
                existing_results = batch_manager.retrieve_batch_row_action_measure(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_measure']
                    one_batch_row.kind_of_batch = MEASURE
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == ORGANIZATION_WORD:
                existing_results = batch_manager.retrieve_batch_row_action_organization(batch_header_id,
                                                                                        one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_organization']
                    one_batch_row.kind_of_batch = ORGANIZATION_WORD
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == POLITICIAN:
                existing_results = batch_manager.retrieve_batch_row_action_politician(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_politician']
                    one_batch_row.kind_of_batch = POLITICIAN
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)
            elif kind_of_batch == POSITION:
                existing_results = batch_manager.retrieve_batch_row_action_position(batch_header_id, one_batch_row.id)
                status += existing_results['status']
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_position']
                    one_batch_row.kind_of_batch = POSITION
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)

    if kind_of_batch == IMPORT_BALLOT_ITEM:
        results = batch_manager.retrieve_batch_row_action_ballot_item_list(
            batch_header_id, limit_to_kind_of_action_list=[IMPORT_DELETE, IMPORT_ALREADY_DELETED])
        if results['batch_row_action_list_found']:
            batch_row_action_list = results['batch_row_action_list']
            for batch_row_action_ballot_item in batch_row_action_list:
                one_batch_row = BatchRow()
                one_batch_row.batch_header_id = batch_header_id
                one_batch_row.batch_row_action = batch_row_action_ballot_item
                one_batch_row.kind_of_batch = IMPORT_BALLOT_ITEM
                one_batch_row.batch_row_action_exists = True
                modified_batch_row_list.append(one_batch_row)

    election_query = Election.objects.order_by('-election_day_text')
    election_list = list(election_query)

    # TODO Retrieve and send a list of polling_locations to choose from into the template
    polling_location_list = []
    if kind_of_batch == IMPORT_BALLOT_ITEM:
        polling_location_list = []

    filtered_state_list = []
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())
    for one_state in sorted_state_list:
        if one_state[0].lower() in active_state_codes:
            filtered_state_list.append(one_state)

    messages.add_message(request, messages.INFO, 'Batch Row Count: {batch_row_count}, status: {status}'
                                                 ''.format(batch_row_count=batch_row_count, status=status))

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'batch_header_id':          batch_header_id,
        'batch_description':        batch_description,
        'batch_set_id':             batch_set_id,
        'batch_header_map':         batch_header_map,
        'batch_set_list':           batch_set_list,
        'batch_row_list':           modified_batch_row_list,
        'election_list':            election_list,
        'kind_of_batch':            kind_of_batch,
        'google_civic_election_id': google_civic_election_id,
        'polling_location_we_vote_id':  polling_location_we_vote_id,
        'state_code':               state_code,
        'state_list':               filtered_state_list,
        'position_owner_organization_we_vote_id': position_owner_organization_we_vote_id,
    }
    return render(request, 'import_export_batches/batch_action_list.html', template_values)


@login_required
def batch_action_list_export_view(request):
    """
    Export batch list as a csv file.

    :param request: HTTP request object.
    :return response: HttpResponse object with csv export data.
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_set_list = []
    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    batch_set_id = 0
    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()

    # if batch_set_id exists, send data sets associated with this batch_set_id
    if positive_value_exists(batch_set_id):
        try:
            batch_set_list = BatchSet.objects.get(id=batch_set_id)
            if batch_set_list:
                batch_set_list_found = True
        except BatchSet.DoesNotExist:
            # This is fine
            batch_set_list = BatchSet()
            batch_set_list_found = False

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()

    batch_list_found = False
    try:
        batch_row_query = BatchRow.objects.order_by('id')
        batch_row_query = batch_row_query.filter(batch_header_id=batch_header_id)
        if positive_value_exists(state_code):
            batch_row_query = batch_row_query.filter(state_code__iexact=state_code)
        batch_row_list = list(batch_row_query)
        if len(batch_row_list):
            batch_list_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_row_list = []
        batch_list_found = False

    if not batch_list_found:
        messages.add_message(request, messages.ERROR, 'No voters found to export.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&batch_header_id=" + str(batch_header_id)
                                    )

    # get header/first row information
    header_opts = BatchHeaderMap._meta
    header_field_names = []
    for field in header_opts.fields:
        if field.name not in ['id', 'batch_header_id']:
            header_field_names.append(field.name)

    # get row information
    # Dale 2020-July This isn't very robust. Shifts over the rows when exporting Polling locations.
    row_opts = BatchRow._meta
    row_field_names = []
    for field in row_opts.fields:
        if field.name not in ['id', 'batch_header_id', 'batch_row_analyzed', 'batch_row_created']:
            if kind_of_batch == 'IMPORT_VOTER':
                if field.name not in \
                        ['state_code', 'google_civic_election_id', 'polling_location_we_vote_id', 'voter_id']:
                    row_field_names.append(field.name)
            else:
                row_field_names.append(field.name)

    header_list = [getattr(batch_header_map, field) for field in header_field_names]
    if kind_of_batch not in ['IMPORT_POLLING_LOCATION', 'IMPORT_VOTER']:
        header_list.insert(0, 'google_civic_election_id')
        header_list.insert(0, 'state_code')
    # - Filter out headers that are None.
    header_list = list(filter(None, header_list))

    # create response for csv file
    response = export_csv(batch_row_list, header_list, row_field_names, batch_description)
    
    return response


@login_required
def batch_row_action_list_export_view(request):
    """
    Export the batch_row_action's (as opposed to the raw incoming values) as a csv file.

    :param request: HTTP request object.
    :return response: HttpResponse object with csv export data.
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_set_list = []
    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    batch_set_id = 0
    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()

    # if batch_set_id exists, send data sets associated with this batch_set_id
    if positive_value_exists(batch_set_id):
        try:
            batch_set_list = BatchSet.objects.get(id=batch_set_id)
            if batch_set_list:
                batch_set_list_found = True
        except BatchSet.DoesNotExist:
            # This is fine
            batch_set_list = BatchSet()
            batch_set_list_found = False

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()

    batch_list_found = False
    batch_row_list = []
    try:
        if kind_of_batch == 'IMPORT_POLLING_LOCATION':
            batch_row_action_query = BatchRowActionPollingLocation.objects.order_by('id')
            batch_row_action_query = batch_row_action_query.filter(batch_header_id=batch_header_id)
            if positive_value_exists(state_code):
                batch_row_action_query = batch_row_action_query.filter(state_code__iexact=state_code)
            batch_row_list = list(batch_row_action_query)
            if len(batch_row_list):
                batch_list_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_row_list = []
        batch_list_found = False

    if not batch_list_found:
        messages.add_message(request, messages.ERROR, 'No voters found to export.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&batch_header_id=" + str(batch_header_id)
                                    )

    # # get header/first row information
    # header_opts = BatchHeaderMap._meta
    header_field_names = []
    # for field in header_opts.fields:
    #     if field.name not in ['id', 'batch_header_id']:
    #         header_field_names.append(field.name)

    # get row information
    header_list = []
    row_field_names = []
    if kind_of_batch == 'IMPORT_POLLING_LOCATION':
        row_opts = BatchRowActionPollingLocation._meta
        for field in row_opts.fields:
            row_field_names.append(field.name)
        header_list = row_field_names

    # header_list = [getattr(batch_header_map, field) for field in header_field_names]
    # if kind_of_batch not in ['IMPORT_POLLING_LOCATION', 'IMPORT_VOTER']:
    #     header_list.insert(0, 'google_civic_election_id')
    #     header_list.insert(0, 'state_code')
    # # - Filter out headers that are None.
    # header_list = list(filter(None, header_list))

    # create response for csv file
    response = export_csv(batch_row_list, header_list, row_field_names, batch_description)

    return response


def export_csv(batch_row_list, header_list, row_field_names, batch_description=None, filename=None):
    """
    Helper function that creates a HttpResponse with csv data

    :param batch_row_list: list of objects to export as csv
    :param header_list: list of column headers for csv data
    :param row_field_names: list of the object fields to be exported
    :param batch_description: optional description of the batch to export
    :param filename: optional name of csv file
    :return response: HttpResponse with text/csv data
    """
    export_filename = "voter_export"
    if batch_description and not filename:
        export_filename = batch_description.batch_name
    elif filename:
        export_filename = filename

    export_filename += ".csv"

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{0}"'.format(export_filename)
    csv_writer = csv.writer(response)
    csv_writer.writerow(header_list)

    # output header/first row to csv
    for obj in batch_row_list:
        # csv_writer.writerow([getattr(obj, field) for field in row_field_names])
        one_row = []
        for field in row_field_names:
            one_row.append(getattr(obj, field))
        csv_writer.writerow(one_row)

    return response


@login_required
def batch_action_list_export_voters_view(request):
    """
    View used to create a csv export file of voters registered for the newsletter
    :param request:
    :return: HttpResponse with csv information of voters
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # get parameters from request object
    kind_of_batch = request.GET.get('kind_of_batch', IMPORT_VOTER)
    batch_header_id = request.GET.get('batch_header_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')

    result = export_voter_list_with_emails()
    messages.add_message(request, messages.INFO, 'Batch Action Export Voters: '
                                                 'Batch kind: {kind_of_batch}'
                                                 ''.format(kind_of_batch=kind_of_batch))

    filename = 'voter_export.csv'
    batch_manager = BatchManager()
    batch_created_result = dict()
    if result and result['voter_list']:
        # Create batch of voters registered for newsletter
        batch_created_result = batch_manager.create_batch_from_voter_object_list(result['voter_list'])

    if batch_created_result and batch_created_result['batch_header_id']:
        batch_header_id = batch_created_result['batch_header_id']

    return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id)
                                )


@login_required
def batch_action_list_analyze_process_view(request):
    """
    Create BatchRowActions for either all the BatchRows for batch_header_id, or only one with batch_row_id
    :param request:
    :return:
    """

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    batch_row_id = convert_to_int(request.GET.get('batch_row_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    state_code = request.GET.get('state_code', '')
    delete_analysis_only = positive_value_exists(request.GET.get('delete_analysis_only', False))
    if state_code == "None":
        state_code = ""

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    # if create_actions_button in (MEASURE, OFFICE_HELD, CANDIDATE, ORGANIZATION_WORD,
    # POSITION, POLITICIAN, IMPORT_BALLOT_ITEM)
    # Run the analysis of either A) every row in this batch, or B) Just the batch_row_id specified within this batch
    results = create_batch_row_actions(
        batch_header_id=batch_header_id,
        batch_description=None,
        batch_row_id=batch_row_id,
        state_code=state_code,
        delete_analysis_only=delete_analysis_only)
    kind_of_batch = results['kind_of_batch']

    messages.add_message(request, messages.INFO, 'Batch Actions: '
                                                 'Batch kind: {kind_of_batch}, '
                                                 'Created:{created} '
                                                 ''.format(kind_of_batch=kind_of_batch,
                                                           created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id) +
                                "&state_code=" + str(state_code)
                                )


@login_required
def batch_header_mapping_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    batch_set_id = 0
    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_set_id = batch_description.batch_set_id
        kind_of_batch = batch_description.kind_of_batch
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()

    # if batch_set_id exists, send data sets associated with this batch_set_id
    if positive_value_exists(batch_set_id):
        try:
            batch_set_list = BatchSet.objects.get(id=batch_set_id)
        except BatchSet.DoesNotExist:
            # This is fine
            batch_set_list = BatchSet()

    try:
        batch_header = BatchHeader.objects.get(id=batch_header_id)
    except BatchHeader.DoesNotExist:
        # This is fine
        batch_header = BatchHeader()

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()

    if kind_of_batch == CANDIDATE:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES
    elif kind_of_batch == CONTEST_OFFICE:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES
    elif kind_of_batch == OFFICE_HELD:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_OFFICES_HELD
    elif kind_of_batch == MEASURE:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES
    elif kind_of_batch == ORGANIZATION_WORD:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS
    elif kind_of_batch == POLITICIAN:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS
    elif kind_of_batch == POSITION:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS
    elif kind_of_batch == IMPORT_BALLOT_ITEM:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS
    else:
        batch_import_keys_accepted = {}

    sorted_batch_import_keys_accepted = sorted(batch_import_keys_accepted.items())

    try:
        batch_row_list = BatchRow.objects.all()
        batch_row_list = batch_row_list.filter(batch_header_id=batch_header_id)[:3]  # Limit to 3 rows
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_row_list = []

    election_list = Election.objects.order_by('-election_day_text')
    messages_on_stage = get_messages(request)

    if batch_set_id:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'batch_header_id':          batch_header_id,
            'batch_description':        batch_description,
            'batch_set_id':             batch_set_id,
            'batch_header':             batch_header,
            'batch_header_map':         batch_header_map,
            'batch_import_keys_accepted':   sorted_batch_import_keys_accepted,
            'batch_row_list':           batch_row_list,
            'batch_set_list':           batch_set_list,
            'election_list':            election_list,
            'kind_of_batch':            kind_of_batch,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'batch_header_id':          batch_header_id,
            'batch_description':        batch_description,
            'batch_set_id':             batch_set_id,
            'batch_header':             batch_header,
            'batch_header_map':         batch_header_map,
            'batch_import_keys_accepted':   sorted_batch_import_keys_accepted,
            'batch_row_list':           batch_row_list,
            'election_list':            election_list,
            'kind_of_batch':            kind_of_batch,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'import_export_batches/batch_header_mapping.html', template_values)


@login_required
def batch_header_mapping_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    save_header_mapping_button = request.GET.get('save_header_mapping_button', '')

    kind_of_batch = ""
    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    batch_set_id = 0
    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_set_id = batch_description.batch_set_id
        kind_of_batch = batch_description.kind_of_batch
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()

    # Put all incoming header_mapping values into a dict
    incoming_header_map_values = {
        'batch_header_map_000': request.GET.get('batch_header_map_000', ''),
        'batch_header_map_001': request.GET.get('batch_header_map_001', ''),
        'batch_header_map_002': request.GET.get('batch_header_map_002', ''),
        'batch_header_map_003': request.GET.get('batch_header_map_003', ''),
        'batch_header_map_004': request.GET.get('batch_header_map_004', ''),
        'batch_header_map_005': request.GET.get('batch_header_map_005', ''),
        'batch_header_map_006': request.GET.get('batch_header_map_006', ''),
        'batch_header_map_007': request.GET.get('batch_header_map_007', ''),
        'batch_header_map_008': request.GET.get('batch_header_map_008', ''),
        'batch_header_map_009': request.GET.get('batch_header_map_009', ''),
        'batch_header_map_010': request.GET.get('batch_header_map_010', ''),
        'batch_header_map_011': request.GET.get('batch_header_map_011', ''),
        'batch_header_map_012': request.GET.get('batch_header_map_012', ''),
        'batch_header_map_013': request.GET.get('batch_header_map_013', ''),
        'batch_header_map_014': request.GET.get('batch_header_map_014', ''),
        'batch_header_map_015': request.GET.get('batch_header_map_015', ''),
        'batch_header_map_016': request.GET.get('batch_header_map_016', ''),
        'batch_header_map_017': request.GET.get('batch_header_map_017', ''),
        'batch_header_map_018': request.GET.get('batch_header_map_018', ''),
        'batch_header_map_019': request.GET.get('batch_header_map_019', ''),
        'batch_header_map_020': request.GET.get('batch_header_map_020', ''),
    }

    batch_header_mapping_results = update_or_create_batch_header_mapping(
        batch_header_id, kind_of_batch, incoming_header_map_values)

    try:
        batch_header = BatchHeader.objects.get(id=batch_header_id)
        batch_header_found = True
    except BatchHeader.DoesNotExist:
        # This is fine
        batch_header = BatchHeader()
        batch_header_found = False

    suggestions_created = 0
    if batch_header_found:
        batch_header_translation_results = create_batch_header_translation_suggestions(
            batch_header, kind_of_batch, incoming_header_map_values)
        suggestions_created = batch_header_translation_results['suggestions_created']

    messages.add_message(request, messages.INFO, 'Batch Header Mapping Updated: '
                                                 'Batch kind: {kind_of_batch}, '
                                                 'suggestions_created: {suggestions_created}, '
                                                 ''.format(kind_of_batch=kind_of_batch,
                                                           suggestions_created=suggestions_created))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id))


@login_required
def batch_action_list_assign_election_to_rows_process_view(request):
    """
    :param request:
    :return: 
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_row_list_found = False
    batch_row_list = []

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    batch_row_id = convert_to_int(request.GET.get('batch_row_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    kind_of_action = request.GET.get('kind_of_action')
    state_code = request.GET.get('state_code', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    # do for entire batch_rows
    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if batch_header_map_found:
        try:
            batch_row_query = BatchRow.objects.all()
            batch_row_query = batch_row_query.filter(batch_header_id=batch_header_id)
            if positive_value_exists(batch_row_id):
                batch_row_query = batch_row_query.filter(id=batch_row_id)
            if positive_value_exists(state_code):
                batch_row_query = batch_row_query.filter(state_code__iexact=state_code)

            batch_row_list = list(batch_row_query)
            if len(batch_row_list):
                batch_row_list_found = True
        except BatchDescription.DoesNotExist:
            # This is fine
            batch_row_list_found = False
            pass

    if batch_header_map_found and batch_row_list_found:
        for one_batch_row in batch_row_list:
            try:
                one_batch_row.google_civic_election_id = google_civic_election_id
                one_batch_row.save()
            except Exception as e:
                pass
        # messages.add_message(request, messages.INFO,
        #                      'Kind of Batch: {kind_of_batch}, ' 'Number Created: {created} '
        #                      ''.format(kind_of_batch=kind_of_batch,
        #                                created=results['number_of_table_rows_created']))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id) +
                                "&state_code=" + str(state_code) +
                                "&google_civic_election_id=" + str(google_civic_election_id)
                                )


@login_required
def batch_action_list_update_or_create_process_view(request):
    """
    Use batch_row_action entries and create live data
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_row_list_found = False
    status = ""

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    batch_row_id = convert_to_int(request.GET.get('batch_row_id', 0))
    ballot_item_id = convert_to_int(request.GET.get('ballot_item_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    kind_of_action = request.GET.get('kind_of_action')
    state_code = request.GET.get('state_code', '')

    voter_device_id = get_voter_api_device_id(request)
    # do for entire batch_rows
    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if batch_header_map_found:
        try:
            batch_row_query = BatchRow.objects.all()
            batch_row_query = batch_row_query.filter(batch_header_id=batch_header_id)
            if positive_value_exists(batch_row_id):
                batch_row_query = batch_row_query.filter(id=batch_row_id)
            if positive_value_exists(state_code):
                batch_row_query = batch_row_query.filter(state_code__iexact=state_code)

            batch_row_list = list(batch_row_query)
            if len(batch_row_list):
                batch_row_list_found = True
        except BatchDescription.DoesNotExist:
            # This is fine
            batch_row_list_found = False
            pass

    if batch_header_map_found and batch_row_list_found:
        results = import_data_from_batch_row_actions(
            kind_of_batch,
            kind_of_action,
            batch_header_id,
            batch_row_id,
            state_code,
            ballot_item_id=ballot_item_id,
            voter_device_id=voter_device_id)
        if kind_of_action == IMPORT_CREATE:
            if results['success']:
                messages.add_message(request, messages.INFO,
                                     'Kind of Batch: {kind_of_batch}, ' 'Number Created: {created} '
                                     ''.format(kind_of_batch=kind_of_batch,
                                               created=results['number_of_table_rows_created']))
            else:
                status += results['status']
                messages.add_message(request, messages.ERROR, 'Batch kind: {kind_of_batch} create failed: {status}'
                                                              ''.format(kind_of_batch=kind_of_batch,
                                                                        status=status))
        elif kind_of_action == IMPORT_ADD_TO_EXISTING:
            if results['success']:
                messages.add_message(request, messages.INFO,
                                     'Kind of Batch: {kind_of_batch}, ' 'Number Updated: {updated} '
                                     ''.format(kind_of_batch=kind_of_batch,
                                               updated=results['number_of_table_rows_updated']))
            else:
                status += results['status']
                messages.add_message(request, messages.ERROR,
                                     'Batch kind: {kind_of_batch} UPDATE_FAILED-UPDATE_MAY_NOT_BE_SUPPORTED_YET, '
                                     'status: {status} '
                                     ''.format(kind_of_batch=kind_of_batch, status=status))
        elif kind_of_action == IMPORT_DELETE:
            if results['success']:
                messages.add_message(request, messages.INFO,
                                     'Kind of Batch: {kind_of_batch}, ' 'Number Deleted: {deleted} '
                                     ''.format(kind_of_batch=kind_of_batch,
                                               deleted=results['number_of_table_rows_deleted']))
            else:
                status += results['status']
                messages.add_message(request, messages.ERROR, 'Batch kind: {kind_of_batch} delete failed: {status}'
                                                              ''.format(kind_of_batch=kind_of_batch,
                                                                        status=status))
        else:
            status += results['status']
            messages.add_message(request, messages.ERROR, 'Batch kind: {kind_of_batch} import status: {status}'
                                                          ''.format(kind_of_batch=kind_of_batch,
                                                                    status=status))
            return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id) +
                                "&state_code=" + str(state_code)
                                )


@login_required
def batch_set_list_view(request):
    """
    Display a list of import batch set
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # kind_of_batch = request.GET.get('kind_of_batch', '')
    batch_file = request.GET.get('batch_file', '')
    batch_uri = request.GET.get('batch_uri', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    batch_set_id = convert_to_int(request.GET.get('batch_set_id', 0))
    batch_process_id = convert_to_int(request.GET.get('batch_process_id', 0))
    limit = request.GET.get('limit', 25)
    show_status_statistics = request.GET.get('show_status_statistics', False)
    show_status_statistics = positive_value_exists(show_status_statistics)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    batch_set_list_found = False
    try:
        batch_set_query = BatchSet.objects.order_by('-import_date')
        # batch_set_list = batch_set_list.exclude(batch_set_id__isnull=True)
        if positive_value_exists(google_civic_election_id):
            batch_set_query = batch_set_query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(batch_process_id):
            batch_set_query = batch_set_query.filter(batch_process_id=batch_process_id)
        if positive_value_exists(batch_set_id):
            batch_set_query = batch_set_query.filter(id=batch_set_id)
        if positive_value_exists(state_code):
            batch_set_query = batch_set_query.filter(state_code__iexact=state_code)

        batch_set_list = batch_set_query[:limit]
        if len(batch_set_list):
            batch_set_list_found = True
    except BatchSet.DoesNotExist:
        # This is fine
        batch_set_list = []
        batch_set_list_found = False
        pass

    if positive_value_exists(show_status_statistics):
        for one_batch_set in batch_set_list:
            batch_description_query = BatchDescription.objects.filter(batch_set_id=one_batch_set.id)
            batch_description = batch_description_query.first()

            batch_description_query = BatchDescription.objects.filter(batch_set_id=one_batch_set.id)
            one_batch_set.batch_description_total_rows_count = batch_description_query.count()

            batch_description_query = BatchDescription.objects.filter(batch_set_id=one_batch_set.id)
            batch_description_query = batch_description_query.exclude(batch_description_analyzed=True)
            one_batch_set.batch_description_not_analyzed_count = batch_description_query.count()

            batch_row_action_query = BatchRowActionBallotItem.objects.filter(batch_set_id=one_batch_set.id)
            batch_row_action_query = batch_row_action_query.filter(kind_of_action__iexact=IMPORT_DELETE)
            one_batch_set.batch_description_to_delete_count = batch_row_action_query.count()

            batch_row_action_query = BatchRowActionBallotItem.objects.filter(batch_set_id=one_batch_set.id)
            batch_row_action_query = batch_row_action_query.filter(kind_of_action__iexact=IMPORT_ALREADY_DELETED)
            one_batch_set.batch_description_already_deleted_count = batch_row_action_query.count()

            if positive_value_exists(one_batch_set.batch_description_total_rows_count):
                try:
                    if batch_description.kind_of_batch == IMPORT_BALLOT_ITEM:
                        batch_row_action_query = BatchRowActionBallotItem.objects.filter(batch_set_id=one_batch_set.id)
                        batch_row_action_query = batch_row_action_query.filter(kind_of_action=IMPORT_CREATE)
                        one_batch_set.batch_description_not_created_count = batch_row_action_query.count()
                except Exception as e:
                    pass

    election_list = Election.objects.order_by('-election_day_text')

    if batch_set_list_found:
        template_values = {
            'batch_file':               batch_file,
            'batch_process_id':         batch_process_id,
            'batch_set_id':             batch_set_id,
            'batch_set_list':           batch_set_list,
            'batch_uri':                batch_uri,
            'google_civic_election_id': google_civic_election_id,
            'election_list':            election_list,
            'messages_on_stage':        messages_on_stage,
            'show_status_statistics':   show_status_statistics,
            'state_code':               state_code,
        }
    else:
        template_values = {
            'batch_file':               batch_file,
            'batch_process_id':         batch_process_id,
            'batch_set_id':             batch_set_id,
            'batch_uri':                batch_uri,
            'election_list':            election_list,
            'google_civic_election_id': google_civic_election_id,
            'messages_on_stage':        messages_on_stage,
            'show_status_statistics':   show_status_statistics,
            'state_code':               state_code,
        }
    return render(request, 'import_export_batches/batch_set_list.html', template_values)


@login_required
def batch_set_list_process_view(request):
    """
    Load in a new batch set to start the importing process
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_uri = request.POST.get('batch_uri', '')
    batch_process_id = convert_to_int(request.POST.get('batch_process_id', 0))
    batch_set_id = convert_to_int(request.POST.get('batch_set_id', 0))
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    organization_we_vote_id = request.POST.get('organization_we_vote_id', '')
    # Was form submitted, or was election just changed?
    import_batch_button = request.POST.get('import_batch_button', '')
    show_status_statistics = request.POST.get('show_status_statistics', False)
    show_status_statistics = positive_value_exists(show_status_statistics)
    state_code = request.POST.get('state_code', '')

    batch_uri_encoded = quote(batch_uri) if positive_value_exists(batch_uri) else ""
    batch_file = None

    # Store contents of spreadsheet?
    # if not positive_value_exists(google_civic_election_id):
    #     messages.add_message(request, messages.ERROR, 'This batch set requires you to choose an election.')
    #     return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
    #                                 "?batch_uri=" + batch_uri_encoded)

    election_manager = ElectionManager()
    election_name = ""
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        election_name = election.election_name

    if positive_value_exists(import_batch_button):  # If the button was pressed...
        batch_manager = BatchManager()
        try:
            if request.method == 'POST' and request.FILES['batch_file']:
                batch_file = request.FILES['batch_file']
        except KeyError:
            pass

        if batch_file is not None:
            results = batch_manager.create_batch_set_vip_xml(
                batch_file, batch_uri, google_civic_election_id, organization_we_vote_id)
            if results['batch_saved']:
                messages.add_message(request, messages.INFO, 'Import batch_set_list for {election_name} election saved.'
                                                             ''.format(election_name=election_name))
            else:
                messages.add_message(request, messages.ERROR, results['status'])
        elif positive_value_exists(batch_uri):
            # check file type
            filetype = batch_manager.find_file_type(batch_uri)
            if "xml" in filetype:
                # file is XML
                # Retrieve the VIP data from XML
                results = batch_manager.create_batch_set_vip_xml(
                    batch_file, batch_uri, google_civic_election_id, organization_we_vote_id)
            else:
                pass
                # results = batch_manager.create_batch(batch_uri, google_civic_election_id, organization_we_vote_id)

        if 'batch_saved' in results and results['batch_saved']:
            messages.add_message(request, messages.INFO, 'Import batch_set_list-batch_saved for '
                                                         '{election_name} election saved.'
                                                         ''.format(election_name=election_name))
        else:
            messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&batch_process_id=" + str(batch_process_id) +
                                "&batch_set_id=" + str(batch_set_id) +
                                "&state_code=" + str(state_code) +
                                "&show_status_statistics=" + str(show_status_statistics) +
                                "&batch_uri=" + batch_uri_encoded)


@login_required
def batch_process_system_toggle_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # ACTIVITY_NOTICE_PROCESS, API_REFRESH_REQUEST, BALLOT_ITEMS, SEARCH_TWITTER
    kind_of_process = request.GET.get('kind_of_process', '')

    from wevote_settings.models import WeVoteSettingsManager
    we_vote_settings_manager = WeVoteSettingsManager()
    if kind_of_process == 'ACTIVITY_NOTICE_PROCESS':
        setting_name = 'batch_process_system_activity_notices_on'
    elif kind_of_process == 'API_REFRESH_REQUEST':
        setting_name = 'batch_process_system_api_refresh_on'
    elif kind_of_process == 'BALLOT_ITEMS':
        setting_name = 'batch_process_system_ballot_items_on'
    elif kind_of_process == 'REPRESENTATIVES':
        setting_name = 'batch_process_system_representatives_on'
    elif kind_of_process == 'CALCULATE_ANALYTICS':
        setting_name = 'batch_process_system_calculate_analytics_on'
    elif kind_of_process == 'GENERATE_VOTER_GUIDES':
        setting_name = 'batch_process_system_generate_voter_guides_on'
    elif kind_of_process == 'SEARCH_TWITTER':
        setting_name = 'batch_process_system_search_twitter_on'
    elif kind_of_process == 'UPDATE_TWITTER_DATA':
        setting_name = 'batch_process_system_update_twitter_on'
    else:
        setting_name = 'batch_process_system_on'
    results = we_vote_settings_manager.fetch_setting_results(setting_name=setting_name, read_only=False)
    if results['we_vote_setting_found']:
        we_vote_setting = results['we_vote_setting']
        we_vote_setting.boolean_value = not we_vote_setting.boolean_value
        we_vote_setting.save()
    else:
        messages.add_message(request, messages.ERROR, "CANNOT_FIND_WE_VOTE_SETTING-batch_process_system_on")

    url_variables = pass_through_batch_list_incoming_variables(request)
    return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) + url_variables)


@login_required
def batch_process_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True

    select_for_changing_batch_process_ids = []
    which_marking = None
    if request.method == 'POST':
        batch_process_id = convert_to_int(request.POST.get('batch_process_id', 0))
        batch_process_search = request.POST.get('batch_process_search', '')
        google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
        include_frequent_processes = request.POST.get('include_frequent_processes', False)
        kind_of_processes_to_show = request.POST.get('kind_of_processes_to_show', '')
        show_all_elections = positive_value_exists(request.POST.get('show_all_elections', False))
        show_active_processes_only = request.POST.get('show_active_processes_only', False)
        show_paused_processes_only = request.POST.get('show_paused_processes_only', False)
        show_checked_out_processes_only = request.POST.get('show_checked_out_processes_only', False)
        state_code = request.POST.get('state_code', '')

        select_for_changing_batch_process_ids = request.POST.getlist('select_for_marking_checks[]')
        which_marking = request.POST.get("which_marking", None)  # What to do with check marks
    else:
        batch_process_id = convert_to_int(request.GET.get('batch_process_id', 0))
        batch_process_search = request.GET.get('batch_process_search', '')
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
        include_frequent_processes = request.GET.get('include_frequent_processes', False)
        kind_of_processes_to_show = request.GET.get('kind_of_processes_to_show', '')
        show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
        show_active_processes_only = request.GET.get('show_active_processes_only', False)
        show_paused_processes_only = request.GET.get('show_paused_processes_only', False)
        show_checked_out_processes_only = request.GET.get('show_checked_out_processes_only', False)
        state_code = request.GET.get('state_code', '')

    batch_process_list = []

    # Make sure 'which_marking' is one of the allowed Filter fields
    if which_marking and which_marking not in ["pause_process", "unpause_process", None]:
        messages.add_message(request, messages.ERROR,
                             'The filter you are trying to update is not recognized: {which_marking}'
                             ''.format(which_marking=which_marking))
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()))

    error_count = 0
    items_processed_successfully = 0
    if which_marking and select_for_changing_batch_process_ids:
        for one_batch_process_id in select_for_changing_batch_process_ids:
            try:
                one_batch_process = BatchProcess.objects.get(id=one_batch_process_id)
                if which_marking == "pause_process":
                    one_batch_process.batch_process_paused = True
                elif which_marking == "unpause_process":
                    one_batch_process.batch_process_paused = False
                one_batch_process.save()
                items_processed_successfully += 1
                status += 'BATCH_PROCESS_UPDATED '
            except BatchProcess.MultipleObjectsReturned as e:
                status += 'MULTIPLE_MATCHING_BATCH_PROCESSES_FOUND '
                error_count += 1
            except BatchProcess.DoesNotExist:
                status += "RETRIEVE_BATCH_PROCESS_NOT_FOUND "
                error_count += 1
            except Exception as e:
                status += 'BATCH_PROCESS_GENERAL_ERROR ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                error_count += 1

        messages.add_message(request, messages.INFO,
                             'Batch Processes paused/unpaused successfully: {items_processed_successfully}, '
                             'errors: {error_count}'
                             ''.format(error_count=error_count,
                                       items_processed_successfully=items_processed_successfully))

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    try:
        batch_process_queryset = BatchProcess.objects.all()
        if positive_value_exists(batch_process_id):
            batch_process_queryset = batch_process_queryset.filter(id=batch_process_id)
        if positive_value_exists(google_civic_election_id):
            batch_process_queryset = batch_process_queryset.filter(google_civic_election_id=google_civic_election_id)
        elif positive_value_exists(show_all_elections):
            # Return offices from all elections
            pass
        else:
            # Limit this search to upcoming_elections only
            google_civic_election_id_list = [0]
            for one_election in election_list:
                google_civic_election_id_list.append(one_election.google_civic_election_id)
            batch_process_queryset = batch_process_queryset.filter(
                google_civic_election_id__in=google_civic_election_id_list)
        if positive_value_exists(state_code):
            batch_process_queryset = batch_process_queryset.filter(state_code__iexact=state_code)
        if positive_value_exists(show_active_processes_only):
            batch_process_queryset = batch_process_queryset.filter(date_completed__isnull=True)
            batch_process_queryset = batch_process_queryset.exclude(batch_process_paused=True)
        if positive_value_exists(show_paused_processes_only):
            batch_process_queryset = batch_process_queryset.filter(batch_process_paused=True)
        if positive_value_exists(show_checked_out_processes_only):
            batch_process_queryset = batch_process_queryset.filter(date_completed__isnull=True)
            batch_process_queryset = batch_process_queryset.filter(date_started__isnull=False)
            batch_process_queryset = batch_process_queryset.exclude(batch_process_paused=True)
        if positive_value_exists(kind_of_processes_to_show):
            if kind_of_processes_to_show == "ACTIVITY_NOTICE_PROCESS":
                activity_notice_processes = ['ACTIVITY_NOTICE_PROCESS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=activity_notice_processes)
            elif kind_of_processes_to_show == "ANALYTICS_ACTION":
                analytics_processes = [
                    'AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID',
                    'AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT',
                    'CALCULATE_ORGANIZATION_DAILY_METRICS',
                    'CALCULATE_ORGANIZATION_ELECTION_METRICS',
                    'CALCULATE_SITEWIDE_DAILY_METRICS',
                    'CALCULATE_SITEWIDE_VOTER_METRICS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=analytics_processes)
            elif kind_of_processes_to_show == "API_REFRESH_REQUEST":
                api_refresh_processes = ['API_REFRESH_REQUEST']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=api_refresh_processes)
            elif kind_of_processes_to_show == "BALLOT_ITEMS":
                ballot_item_processes = [
                    'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS',
                    'REFRESH_BALLOT_ITEMS_FROM_VOTERS',
                    'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=ballot_item_processes)
            elif kind_of_processes_to_show == "GENERATE_VOTER_GUIDES":
                processes = ['GENERATE_VOTER_GUIDES']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=processes)
            elif kind_of_processes_to_show == "REPRESENTATIVES":
                processes = ['RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=processes)
            elif kind_of_processes_to_show == "SEARCH_TWITTER":
                search_twitter_processes = ['SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=search_twitter_processes)
            elif kind_of_processes_to_show == "UPDATE_TWITTER_DATA":
                batch_process_queryset = batch_process_queryset.filter(
                    kind_of_process__in=['UPDATE_TWITTER_DATA_FROM_TWITTER'])
        elif positive_value_exists(include_frequent_processes):
            # Don't modify the query
            pass
        else:
            exclude_list = [ACTIVITY_NOTICE_PROCESS, API_REFRESH_REQUEST]
            batch_process_queryset = batch_process_queryset.exclude(kind_of_process__in=exclude_list)
        batch_process_queryset = batch_process_queryset.order_by("-id")

        if positive_value_exists(batch_process_search):
            search_words = batch_process_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(wikipedia_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_office_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_race_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    batch_process_queryset = batch_process_queryset.filter(final_filters)

        batch_process_list_count = batch_process_queryset.count()

        batch_process_queryset = batch_process_queryset[:100]
        batch_process_list = list(batch_process_queryset)

        if len(batch_process_list):
            batch_process_list_found = True
            status += 'BATCH_PROCESS_LIST_RETRIEVED '
        else:
            status += 'BATCH_PROCESS_LIST_NOT_RETRIEVED '
    except BatchProcess.DoesNotExist:
        # No offices found. Not a problem.
        status += 'NO_OFFICES_FOUND_DoesNotExist '
        batch_process_list = []
    except Exception as e:
        status += 'FAILED retrieve_all_offices_for_upcoming_election: ' + str(e) + ' '
        success = False

    state_codes_map_point_counts_dict = {}
    polling_location_manager = PollingLocationManager()
    map_points_retrieved_each_batch_chunk = 102  # Signals that a batch_process wasn't found
    for batch_process in batch_process_list:
        if batch_process.kind_of_process in [
            RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS,
            RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS,
        ]:
            state_code_lower_case = ''
            map_points_retrieved_each_batch_chunk = 101  # Signals that a state_code wasn't found
            if positive_value_exists(batch_process.state_code):
                state_code_lower_case = batch_process.state_code.lower()
                if batch_process.kind_of_process in [
                    RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS, REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS,
                ]:
                    # For both REFRESH and RETRIEVE, see if number of map points for state exceeds the "large" threshold
                    map_points_retrieved_each_batch_chunk = \
                        polling_location_manager.calculate_number_of_map_points_to_retrieve_with_each_batch_chunk(
                            state_code_lower_case)
                elif batch_process.kind_of_process in [RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS]:
                    from polling_location.models import MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_REPRESENTATIVES_API
                    map_points_retrieved_each_batch_chunk = \
                        MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_REPRESENTATIVES_API
            if state_code_lower_case in state_codes_map_point_counts_dict:
                batch_process.polling_location_count = state_codes_map_point_counts_dict[state_code_lower_case]
                batch_process.ballot_item_chunks_expected = \
                    int(math.ceil(batch_process.polling_location_count / map_points_retrieved_each_batch_chunk)) + 1
            else:
                state_codes_map_point_counts_dict[state_code_lower_case] = \
                    polling_location_manager.fetch_polling_location_count(state_code=state_code_lower_case)
                batch_process.polling_location_count = state_codes_map_point_counts_dict[state_code_lower_case]
                batch_process.ballot_item_chunks_expected = \
                    int(math.ceil(batch_process.polling_location_count / map_points_retrieved_each_batch_chunk)) + 1
        # Add the processing "chunks" under each Batch Process
        batch_process_analytics_chunk_list = []
        batch_process_analytics_chunk_list_found = False
        batch_process_ballot_item_chunk_list = []
        batch_process_ballot_item_chunk_list_found = False
        batch_process_representatives_chunk_list = []
        batch_process_representatives_chunk_list_found = False
        try:
            batch_process_chunk_queryset = BatchProcessBallotItemChunk.objects.all()
            batch_process_chunk_queryset = batch_process_chunk_queryset.filter(batch_process_id=batch_process.id)
            batch_process_chunk_queryset = batch_process_chunk_queryset.order_by("-id")
            batch_process_ballot_item_chunk_list = list(batch_process_chunk_queryset)
            batch_process_ballot_item_chunk_list_found = \
                positive_value_exists(len(batch_process_ballot_item_chunk_list))
        except BatchProcessBallotItemChunk.DoesNotExist:
            # BatchProcessBallotItemChunk not found. Not a problem.
            status += 'NO_BatchProcessBallotItemChunk_FOUND_DoesNotExist '
        except Exception as e:
            status += 'FAILED BatchProcessBallotItemChunk ' + str(e) + ' '
        batch_process.batch_process_ballot_item_chunk_list = batch_process_ballot_item_chunk_list
        batch_process.batch_process_ballot_item_chunk_list_found = batch_process_ballot_item_chunk_list_found
        batch_process.ballot_item_chunk_count = len(batch_process.batch_process_ballot_item_chunk_list)

        if not positive_value_exists(batch_process_ballot_item_chunk_list_found):
            # Now check to see if this is an analytics
            try:
                batch_process_chunk_queryset = BatchProcessAnalyticsChunk.objects.all()
                batch_process_chunk_queryset = batch_process_chunk_queryset.filter(batch_process_id=batch_process.id)
                batch_process_chunk_queryset = batch_process_chunk_queryset.order_by("-id")
                batch_process_analytics_chunk_list = list(batch_process_chunk_queryset)
                batch_process_analytics_chunk_list_found = \
                    positive_value_exists(len(batch_process_analytics_chunk_list))
            except Exception as e:
                status += 'FAILED BatchProcessAnalyticsChunk: ' + str(e) + ' '
            batch_process.batch_process_analytics_chunk_list = batch_process_analytics_chunk_list
            batch_process.batch_process_analytics_chunk_list_found = batch_process_analytics_chunk_list_found

        if not positive_value_exists(batch_process_analytics_chunk_list_found):
            try:
                batch_process_chunk_queryset = BatchProcessRepresentativesChunk.objects.all()
                batch_process_chunk_queryset = batch_process_chunk_queryset.filter(batch_process_id=batch_process.id)
                batch_process_chunk_queryset = batch_process_chunk_queryset.order_by("-id")
                batch_process_representatives_chunk_list = list(batch_process_chunk_queryset)
                batch_process_representatives_chunk_list_found = \
                    positive_value_exists(len(batch_process_representatives_chunk_list))
            except Exception as e:
                status += 'FAILED BatchProcessRepresentativesChunk: ' + str(e) + ' '
            batch_process.batch_process_representatives_chunk_list = batch_process_representatives_chunk_list
            batch_process.batch_process_representatives_chunk_list_found = \
                batch_process_representatives_chunk_list_found
            batch_process.ballot_item_chunk_count = len(batch_process.batch_process_representatives_chunk_list)

    # Make sure we always include the current election in the election_list, even if it is older
    use_ballotpedia_as_data_source = False
    use_ctcl_as_data_source = False
    use_ctcl_as_data_source_override = False
    use_vote_usa_as_data_source = False
    if positive_value_exists(google_civic_election_id):
        this_election_found = False
        for one_election in election_list:
            if convert_to_int(one_election.google_civic_election_id) == convert_to_int(google_civic_election_id):
                this_election_found = True
                use_ballotpedia_as_data_source = one_election.use_ballotpedia_as_data_source
                use_ctcl_as_data_source = one_election.use_ctcl_as_data_source
                use_ctcl_as_data_source_by_state_code = one_election.use_ctcl_as_data_source_by_state_code
                if positive_value_exists(state_code) and positive_value_exists(use_ctcl_as_data_source_by_state_code):
                    if state_code.lower() in use_ctcl_as_data_source_by_state_code.lower():
                        use_ctcl_as_data_source_override = True
                use_vote_usa_as_data_source = one_election.use_vote_usa_as_data_source
                break
        if not this_election_found:
            results = election_manager.retrieve_election(google_civic_election_id)
            if results['election_found']:
                election = results['election']
                use_ballotpedia_as_data_source = election.use_ballotpedia_as_data_source
                use_ctcl_as_data_source = election.use_ctcl_as_data_source
                use_ctcl_as_data_source_by_state_code = election.use_ctcl_as_data_source_by_state_code
                if positive_value_exists(state_code) and positive_value_exists(use_ctcl_as_data_source_by_state_code):
                    if state_code.lower() in use_ctcl_as_data_source_by_state_code.lower():
                        use_ctcl_as_data_source_override = True
                use_vote_usa_as_data_source = election.use_vote_usa_as_data_source
                election_list.append(election)

    state_list = STATE_CODE_MAP
    state_list_modified = {}
    for one_state_code, one_state_name in state_list.items():
        # office_count = batch_process_manager.fetch_office_count(google_civic_election_id, one_state_code)
        batch_process_count = 0
        state_name_modified = one_state_name
        if positive_value_exists(batch_process_count):
            state_name_modified += " - " + str(batch_process_count)
            state_list_modified[one_state_code] = state_name_modified
        else:
            state_name_modified += ""
            state_list_modified[one_state_code] = state_name_modified
    sorted_state_list = sorted(state_list_modified.items())

    # status_print_list = ""
    # status_print_list += "batch_process_list_count: " + \
    #                      str(batch_process_list_count) + " "
    #
    # messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    from wevote_settings.models import fetch_batch_process_system_on, fetch_batch_process_system_activity_notices_on, \
        fetch_batch_process_system_api_refresh_on, fetch_batch_process_system_ballot_items_on, \
        fetch_batch_process_system_calculate_analytics_on, fetch_batch_process_system_generate_voter_guides_on, \
        fetch_batch_process_system_representatives_on, fetch_batch_process_system_search_twitter_on, \
        fetch_batch_process_system_update_twitter_on

    ballot_returned_oldest_date = ""
    ballot_returned_voter_oldest_date = ""
    if positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        ballot_returned_list_manager = BallotReturnedListManager()
        ballot_returned_oldest_date = ballot_returned_list_manager.fetch_oldest_date_last_updated(
            google_civic_election_id, state_code)

        ballot_returned_voter_oldest_date = ballot_returned_list_manager.fetch_oldest_date_last_updated(
            google_civic_election_id, state_code, for_voter=True)

    toggle_system_url_variables = "s=1"  # Add a dummy variable at the start so all remaining variables have &
    if positive_value_exists(batch_process_search):
        toggle_system_url_variables += "&batch_process_search=" + str(batch_process_search)
    if positive_value_exists(google_civic_election_id):
        toggle_system_url_variables += "&google_civic_election_id=" + str(google_civic_election_id)
    if positive_value_exists(include_frequent_processes):
        toggle_system_url_variables += "&include_frequent_processes=1"
    if positive_value_exists(kind_of_processes_to_show):
        toggle_system_url_variables += "&kind_of_processes_to_show=" + str(kind_of_processes_to_show)
    if positive_value_exists(show_active_processes_only):
        toggle_system_url_variables += "&show_active_processes_only=1"
    if positive_value_exists(show_all_elections):
        toggle_system_url_variables += "&show_all_elections=1"
    if positive_value_exists(show_checked_out_processes_only):
        toggle_system_url_variables += "&show_checked_out_processes_only=1"
    if positive_value_exists(show_paused_processes_only):
        toggle_system_url_variables += "&show_paused_processes_only=1"
    if positive_value_exists(state_code):
        toggle_system_url_variables += "&state_code=" + str(state_code)
    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'ballot_returned_oldest_date':          ballot_returned_oldest_date,
        'ballot_returned_voter_oldest_date':    ballot_returned_voter_oldest_date,
        'batch_process_id':                     batch_process_id,
        'batch_process_list':                   batch_process_list,
        'batch_process_system_on':                      fetch_batch_process_system_on(),
        'batch_process_system_activity_notices_on':     fetch_batch_process_system_activity_notices_on(),
        'batch_process_system_api_refresh_on':          fetch_batch_process_system_api_refresh_on(),
        'batch_process_system_ballot_items_on':         fetch_batch_process_system_ballot_items_on(),
        'batch_process_system_calculate_analytics_on':  fetch_batch_process_system_calculate_analytics_on(),
        'batch_process_system_generate_voter_guides_on': fetch_batch_process_system_generate_voter_guides_on(),
        'batch_process_system_representatives_on':      fetch_batch_process_system_representatives_on(),
        'batch_process_system_search_twitter_on':       fetch_batch_process_system_search_twitter_on(),
        'batch_process_system_update_twitter_on':       fetch_batch_process_system_update_twitter_on(),
        'batch_process_search':                 batch_process_search,
        'election_list':                        election_list,
        'google_civic_election_id':             google_civic_election_id,
        'include_frequent_processes':           include_frequent_processes,
        'kind_of_processes_to_show':            kind_of_processes_to_show,
        'map_points_retrieved_each_batch_chunk':    map_points_retrieved_each_batch_chunk,
        'show_all_elections':                   show_all_elections,
        'show_active_processes_only':           show_active_processes_only,
        'show_paused_processes_only':           show_paused_processes_only,
        'show_checked_out_processes_only':      show_checked_out_processes_only,
        'state_code':                           state_code,
        'state_list':                           sorted_state_list,
        'toggle_system_url_variables':          toggle_system_url_variables,
        'use_ballotpedia_as_data_source':       use_ballotpedia_as_data_source,
        'use_ctcl_as_data_source':              use_ctcl_as_data_source,
        'use_ctcl_as_data_source_override':     use_ctcl_as_data_source_override,
        'use_vote_usa_as_data_source':          use_vote_usa_as_data_source,
    }
    return render(request, 'import_export_batches/batch_process_list.html', template_values)


def batch_process_next_steps_view(request):
    # json_results = batch_process_next_steps()
    status = "batch_process_next_steps_view-DEPRECATED "
    json_results = {
        'success': False,
        'status': status,
    }
    response = HttpResponse(json.dumps(json_results), content_type='application/json')
    return response


@login_required
def import_ballot_items_for_location_view(request):
    """
    Reach out to external data source API to retrieve a ballot for one location.
    """
    status = ""
    success = True

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', "")
    use_ballotpedia = positive_value_exists(request.GET.get('use_ballotpedia', False))
    use_ctcl = positive_value_exists(request.GET.get('use_ctcl', False))
    use_vote_usa = positive_value_exists(request.GET.get('use_vote_usa', False))

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR,
                             'Google Civic Election Id missing.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    ctcl_election_uuid = ''
    election = None
    election_manager = ElectionManager()
    election_day_text = ''
    election_found = False
    use_ballotpedia_as_data_source = False
    use_ctcl_as_data_source = False
    use_ctcl_as_data_source_override = False
    use_vote_usa_as_data_source = False
    results = election_manager.retrieve_election(google_civic_election_id=google_civic_election_id)
    if results['election_found']:
        election_found = True
        election = results['election']
        ctcl_election_uuid = election.ctcl_uuid
        election_day_text = election.election_day_text
        use_ballotpedia_as_data_source = election.use_ballotpedia_as_data_source
        use_ctcl_as_data_source = election.use_ctcl_as_data_source
        use_vote_usa_as_data_source = election.use_vote_usa_as_data_source
        if positive_value_exists(state_code) and positive_value_exists(election.use_ctcl_as_data_source_by_state_code):
            if state_code.lower() in election.use_ctcl_as_data_source_by_state_code.lower():
                use_ctcl_as_data_source_override = True

    polling_location_manager = PollingLocationManager()
    polling_location_state_code = ""
    if positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_we_vote_id = polling_location.we_vote_id
            polling_location_state_code = polling_location.state

    if positive_value_exists(polling_location_state_code) and positive_value_exists(election_found):
        if not positive_value_exists(use_ctcl_as_data_source_override) \
                and positive_value_exists(election.use_ctcl_as_data_source_by_state_code):
            if polling_location_state_code.lower() in election.use_ctcl_as_data_source_by_state_code.lower():
                use_ctcl_as_data_source_override = True

    if positive_value_exists(use_ballotpedia):
        if not positive_value_exists(use_ballotpedia_as_data_source):
            success = False
            status += "USE_BALLOTPEDIA-BUT_NOT_USE_BALLOTPEDIA_AS_DATA_SOURCE "
            results = {
                'status': status,
                'success': success,
            }
    elif positive_value_exists(use_ctcl):
        if not positive_value_exists(use_ctcl_as_data_source) \
                and not positive_value_exists(use_ctcl_as_data_source_override):
            success = False
            status += "USE_CTCL-BUT_NOT_USE_CTCL_AS_DATA_SOURCE "
            results = {
                'status': status,
                'success': success,
            }
    elif positive_value_exists(use_vote_usa):
        if not positive_value_exists(use_vote_usa_as_data_source):
            success = False
            status += "USE_VOTE_USA-BUT_NOT_USE_VOTE_USA_AS_DATA_SOURCE "
            results = {
                'status': status,
                'success': success,
            }

    kind_of_batch = ""
    if success:
        update_or_create_rules = {
            'create_candidates':    True,
            'create_offices':       True,
            'create_measures':      True,
            'update_candidates':    False,
            'update_offices':       False,
            'update_measures':      False,
        }

        if positive_value_exists(use_ballotpedia):
            from import_export_ballotpedia.controllers import \
                retrieve_ballotpedia_ballot_items_from_polling_location_api_v4
            results = retrieve_ballotpedia_ballot_items_from_polling_location_api_v4(
                google_civic_election_id,
                election_day_text=election_day_text,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
            )
            status += results['status']
        elif positive_value_exists(use_ctcl):
            from import_export_ctcl.controllers import retrieve_ctcl_ballot_items_from_polling_location_api
            results = retrieve_ctcl_ballot_items_from_polling_location_api(
                google_civic_election_id=google_civic_election_id,
                ctcl_election_uuid=ctcl_election_uuid,
                election_day_text=election_day_text,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                update_or_create_rules=update_or_create_rules,
            )
            status += results['status']
        elif positive_value_exists(use_vote_usa):
            from import_export_vote_usa.controllers import retrieve_vote_usa_ballot_items_from_polling_location_api
            results = retrieve_vote_usa_ballot_items_from_polling_location_api(
                google_civic_election_id=google_civic_election_id,
                election_day_text=election_day_text,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                update_or_create_rules=update_or_create_rules,
            )
            status += results['status']
        else:
            # Should not be possible to get here
            pass

        if 'kind_of_batch' in results:
            kind_of_batch = results['kind_of_batch']
        if not positive_value_exists(kind_of_batch):
            kind_of_batch = IMPORT_BALLOT_ITEM

    batch_header_id = 0
    messages.add_message(request, messages.INFO, status)
    if 'batch_saved' in results and results['batch_saved']:
        messages.add_message(request, messages.INFO, 'Ballot items import batch for {google_civic_election_id} '
                                                     'election saved.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    elif 'batch_header_id' in results and results['batch_header_id']:
        messages.add_message(request, messages.INFO, 'Ballot items import batch for {google_civic_election_id} '
                                                     'election saved, batch_header_id.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    elif 'ballot_items_count' in results and results['ballot_items_count'] == 0:
        messages.add_message(request, messages.INFO, 'No ballot_items found. ' + results['status'])
        if positive_value_exists(polling_location_we_vote_id):
            return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                                args=(polling_location_we_vote_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&state_code=" + str(state_code)
                                        )
    else:
        messages.add_message(request, messages.ERROR, status)

    if positive_value_exists(batch_header_id):
        # Go straight to the new batch
        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    "?batch_header_id=" + str(batch_header_id) +
                                    "&kind_of_batch=" + str(kind_of_batch) +
                                    "&google_civic_election_id=" + str(google_civic_election_id))
    else:
        # Go to the ballot_item_list_edit page
        if positive_value_exists(polling_location_we_vote_id):
            return HttpResponseRedirect(reverse('ballot:ballot_item_list_by_polling_location_edit',
                                                args=(polling_location_we_vote_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&state_code=" + str(state_code)
                                        )
        else:
            messages.add_message(request, messages.ERROR, "Missing polling_location_we_vote_id.")
            return HttpResponseRedirect(reverse('election:election_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&state_code=" + str(state_code)
                                        )


def process_next_activity_notices_view(request):
    json_results = process_next_activity_notices()

    response = HttpResponse(json.dumps(json_results), content_type='application/json')
    return response


def process_next_ballot_items_view(request):
    json_results = process_next_ballot_items()

    response = HttpResponse(json.dumps(json_results), content_type='application/json')
    return response


def process_next_general_maintenance_view(request):
    json_results = process_next_general_maintenance()

    response = HttpResponse(json.dumps(json_results), content_type='application/json')
    return response


@login_required
def batch_process_pause_toggle_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_process_id = request.GET.get('batch_process_id', 0)

    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.retrieve_batch_process(batch_process_id=batch_process_id)
    if results['batch_process_found']:
        batch_process = results['batch_process']
        try:
            current_setting = batch_process.batch_process_paused
            batch_process.batch_process_paused = not current_setting
            batch_process.save()
            message = "BATCH_PROCESS_PAUSED: " + str(batch_process.batch_process_paused) + " "
            messages.add_message(request, messages.INFO, message)
        except Exception as e:
            message = "COULD_NOT_SAVE_BATCH_PROCESS-BATCH_PROCESS_PAUSED " + str(e) + " "
            messages.add_message(request, messages.ERROR, message)
    else:
        message = "BATCH_PROCESS_COULD_NOT_BE_FOUND: " + str(batch_process_id)
        messages.add_message(request, messages.ERROR, message)

    url_variables = pass_through_batch_list_incoming_variables(request)
    return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) + url_variables)


@login_required
def batch_process_log_entry_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    batch_process_log_entry_search = request.GET.get('batch_process_log_entry_search', '')
    batch_process_id = convert_to_int(request.GET.get('batch_process_id', 0))
    batch_process_chunk_id = convert_to_int(request.GET.get('batch_process_chunk_id', 0))

    batch_process_log_entry_list_found = False
    batch_process_log_entry_list = []

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    try:
        batch_process_queryset = BatchProcessLogEntry.objects.all()
        if positive_value_exists(batch_process_id):
            batch_process_queryset = batch_process_queryset.filter(batch_process_id=batch_process_id)
        if positive_value_exists(batch_process_chunk_id):
            batch_process_queryset = batch_process_queryset.filter(
                Q(batch_process_ballot_item_chunk_id=batch_process_chunk_id) |
                Q(batch_process_representatives_chunk_id=batch_process_chunk_id)
            )
        if positive_value_exists(google_civic_election_id):
            batch_process_queryset = batch_process_queryset.filter(google_civic_election_id=google_civic_election_id)
        elif positive_value_exists(show_all_elections):
            # Return offices from all elections
            pass
        else:
            # Limit this search to upcoming_elections only, or entries with no election
            google_civic_election_id_list = [0]
            for one_election in election_list:
                google_civic_election_id_list.append(one_election.google_civic_election_id)
            batch_process_queryset = batch_process_queryset.filter(
                google_civic_election_id__in=google_civic_election_id_list)
        if positive_value_exists(state_code):
            batch_process_queryset = batch_process_queryset.filter(state_code__iexact=state_code)
        batch_process_queryset = batch_process_queryset.order_by("-id")

        if positive_value_exists(batch_process_log_entry_search):
            search_words = batch_process_log_entry_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(batch_process_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(batch_set_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(google_civic_election_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(polling_location_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(state_code__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(status__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    batch_process_queryset = batch_process_queryset.filter(final_filters)

        batch_process_log_entry_list_count = batch_process_queryset.count()

        batch_process_queryset = batch_process_queryset[:200]
        batch_process_log_entry_list = list(batch_process_queryset)

        if len(batch_process_log_entry_list):
            batch_process_log_entry_list_found = True
            status += 'BATCH_PROCESS_LOG_ENTRY_LIST_RETRIEVED '
        else:
            status += 'BATCH_PROCESS_LOG_ENTRY_LIST_NOT_RETRIEVED '
    except BatchProcessLogEntry.DoesNotExist:
        # No offices found. Not a problem.
        status += 'BATCH_PROCESS_LOG_ENTRY_DoesNotExist '
        batch_process_log_entry_list = []
    except Exception as e:
        status += 'FAILED-[retrieve_all_offices_for_upcoming_election]-ERROR ' + str(e) + " "
        success = False
        handle_exception(e, logger=logger, exception_message=status)

    # Make sure we always include the current election in the election_list, even if it is older
    if positive_value_exists(google_civic_election_id):
        this_election_found = False
        for one_election in election_list:
            if convert_to_int(one_election.google_civic_election_id) == convert_to_int(google_civic_election_id):
                this_election_found = True
                break
        if not this_election_found:
            results = election_manager.retrieve_election(google_civic_election_id)
            if results['election_found']:
                election = results['election']
                election_list.append(election)

    state_list = STATE_CODE_MAP
    state_list_modified = {}
    for one_state_code, one_state_name in state_list.items():
        # office_count = batch_process_manager.fetch_office_count(google_civic_election_id, one_state_code)
        batch_process_log_entry_count = 0
        state_name_modified = one_state_name
        if positive_value_exists(batch_process_log_entry_count):
            state_name_modified += " - " + str(batch_process_log_entry_count)
            state_list_modified[one_state_code] = state_name_modified
        else:
            state_name_modified += ""
            state_list_modified[one_state_code] = state_name_modified
    sorted_state_list = sorted(state_list_modified.items())

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'batch_process_id':         batch_process_id,
        'batch_process_chunk_id':   batch_process_chunk_id,
        'batch_process_log_entry_list':       batch_process_log_entry_list,
        'batch_process_log_entry_search':     batch_process_log_entry_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'show_all_elections':       show_all_elections,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'import_export_batches/batch_process_log_entry_list.html', template_values)


@login_required
def batch_set_batch_list_view(request):
    """
    Display row-by-row details of batch_set actions being reviewed, leading up to processing an entire batch_set.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_set_id = convert_to_int(request.GET.get('batch_set_id', 0))

    if not positive_value_exists(batch_set_id):
        messages.add_message(request, messages.ERROR, 'Batch_set_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()))

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    analyze_all_button = request.GET.get('analyze_all_button', 0)
    create_all_button = request.GET.get('create_all_button', 0)
    analyze_for_deletes_button = request.GET.get('analyze_for_deletes_button', 0)
    delete_all_button = request.GET.get('delete_all_button', 0)
    show_all_batches = request.GET.get('show_all_batches', False)
    state_code = request.GET.get('state_code', "")
    update_all_button = request.GET.get('update_all_button', 0)

    batch_list_modified = []
    batch_manager = BatchManager()
    batch_set_count = 0
    batch_set_kind_of_batch = ""

    # Store static data in memory so we don't have to use the database
    election_objects_dict = {}
    office_objects_dict = {}
    measure_objects_dict = {}

    voter_device_id = get_voter_api_device_id(request)

    try:
        if positive_value_exists(analyze_all_button):
            batch_actions_analyzed = 0
            batch_actions_not_analyzed = 0
            batch_header_id_created_list = []
            start_each_batch_time_tracker = []  # Array of times
            summary_of_create_batch_row_action_time_tracker = []  # Array of arrays

            batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
            batch_description_query = batch_description_query.filter(batch_description_analyzed=False)
            batch_list = list(batch_description_query)
            batch_list_not_analyzed_count = len(batch_list)

            # For this batch set, cycle through each batch. Within each batch, cycle through each batch_row
            # and decide whether the action required is create or update.
            for one_batch_description in batch_list:
                start_each_batch_time_tracker.append(now().strftime("%H:%M:%S:%f"))
                results = create_batch_row_actions(
                    one_batch_description.batch_header_id,
                    batch_description=one_batch_description,
                    election_objects_dict=election_objects_dict,
                    measure_objects_dict=measure_objects_dict,
                    office_objects_dict=office_objects_dict,
                )
                if results['batch_actions_created']:
                    batch_actions_analyzed += 1
                    try:
                        # If BatchRowAction's were created for BatchDescription, this batch_description was analyzed
                        one_batch_description.batch_description_analyzed = True
                        one_batch_description.save()
                        batch_header_id_created_list.append(one_batch_description.batch_header_id)
                    except Exception as e:
                        pass
                else:
                    batch_actions_not_analyzed += 1
                # Keep building up these dicts so we don't have to retrieve data again-and-again from the database
                election_objects_dict = results['election_objects_dict']
                measure_objects_dict = results['measure_objects_dict']
                office_objects_dict = results['office_objects_dict']
                start_create_batch_row_action_time_tracker = results['start_create_batch_row_action_time_tracker']
                summary_of_create_batch_row_action_time_tracker.append(start_create_batch_row_action_time_tracker)

            # If there were not any entries with batch_description_analyzed set to False, then retrieve all
            if not positive_value_exists(batch_list_not_analyzed_count):
                batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
                if positive_value_exists(len(batch_header_id_created_list)):
                    batch_description_query = batch_description_query.exclude(
                        batch_header_id__in=batch_header_id_created_list)
                batch_list = list(batch_description_query)

                for one_batch_description in batch_list:
                    start_each_batch_time_tracker.append(now().strftime("%H:%M:%S:%f"))
                    results = create_batch_row_actions(
                        one_batch_description.batch_header_id,
                        batch_description=one_batch_description,
                        election_objects_dict=election_objects_dict,
                        measure_objects_dict=measure_objects_dict,
                        office_objects_dict=office_objects_dict,
                    )
                    if results['batch_actions_created']:
                        batch_actions_analyzed += 1
                        try:
                            # If BatchRowAction's were created for BatchDescription, this batch_description was analyzed
                            one_batch_description.batch_description_analyzed = True
                            one_batch_description.save()
                        except Exception as e:
                            pass
                    else:
                        batch_actions_not_analyzed += 1
                    # Keep building up these dicts so we don't have to retrieve data again-and-again from the database
                    election_objects_dict = results['election_objects_dict']
                    measure_objects_dict = results['measure_objects_dict']
                    office_objects_dict = results['office_objects_dict']
                    start_create_batch_row_action_time_tracker = results['start_create_batch_row_action_time_tracker']
                    summary_of_create_batch_row_action_time_tracker.append(start_create_batch_row_action_time_tracker)

            if positive_value_exists(batch_actions_analyzed):
                messages.add_message(request, messages.INFO, "Analyze All, BatchRows Analyzed: "
                                                             "" + str(batch_actions_analyzed))

            if positive_value_exists(batch_actions_not_analyzed):
                messages.add_message(request, messages.ERROR, "Analyze All, BatchRows NOT Analyzed: "
                                                              "" + str(batch_actions_not_analyzed))

            return HttpResponseRedirect(reverse('import_export_batches:batch_set_batch_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&batch_set_id=" + str(batch_set_id) +
                                        "&state_code=" + state_code)

        if positive_value_exists(update_all_button):
            batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
            batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
            batch_list = list(batch_description_query)

            batch_actions_updated = 0
            batch_actions_not_updated = 0
            for one_batch_description in batch_list:
                results = import_data_from_batch_row_actions(
                    one_batch_description.kind_of_batch,
                    IMPORT_ADD_TO_EXISTING,
                    one_batch_description.batch_header_id,
                    voter_device_id=voter_device_id)
                if results['number_of_table_rows_updated']:
                    batch_actions_updated += 1
                else:
                    batch_actions_not_updated += 1

            if positive_value_exists(batch_actions_updated):
                messages.add_message(request, messages.INFO, "Update in All Batches: "
                                                             "" + str(batch_actions_updated) + ". ")

            if positive_value_exists(batch_actions_not_updated):
                messages.add_message(request, messages.ERROR, "Update in All Batches, Failed Updates: "
                                                              "" + str(batch_actions_not_updated))

            return HttpResponseRedirect(reverse('import_export_batches:batch_set_batch_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&batch_set_id=" + str(batch_set_id) +
                                        "&state_code=" + state_code)

        if positive_value_exists(create_all_button):
            batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
            batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
            batch_list = list(batch_description_query)

            batch_actions_created = 0
            not_created_status = ""
            for one_batch_description in batch_list:
                results = import_data_from_batch_row_actions(
                    one_batch_description.kind_of_batch,
                    IMPORT_CREATE,
                    one_batch_description.batch_header_id,
                    voter_device_id=voter_device_id)
                if results['number_of_table_rows_created']:
                    batch_actions_created += 1

                if not positive_value_exists(results['success']):
                    if len(not_created_status) < 1024:
                        not_created_status += results['status']

            if positive_value_exists(batch_actions_created):
                messages.add_message(request, messages.INFO, "Create in All Batches: "
                                                             "" + str(batch_actions_created) + ". ")

            if positive_value_exists(not_created_status):
                messages.add_message(request, messages.ERROR,
                                     "Create in All Batches, FAILED Creates: {not_created_status} "
                                     "".format(not_created_status=not_created_status))

            return HttpResponseRedirect(reverse('import_export_batches:batch_set_batch_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&batch_set_id=" + str(batch_set_id) +
                                        "&state_code=" + state_code)

        if positive_value_exists(analyze_for_deletes_button):
            batch_actions_analyzed_for_deletes = 0
            batch_header_id_created_list = []

            batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
            batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
            batch_list = list(batch_description_query)

            for one_batch_description in batch_list:
                results = create_batch_row_actions(
                    one_batch_description.batch_header_id,
                    batch_description=one_batch_description,
                    delete_analysis_only=True,
                    election_objects_dict=election_objects_dict,
                    measure_objects_dict=measure_objects_dict,
                    office_objects_dict=office_objects_dict,
                )
                if results['batch_actions_created']:
                    batch_actions_analyzed_for_deletes += 1
                    batch_header_id_created_list.append(one_batch_description.batch_header_id)

                election_objects_dict = results['election_objects_dict']
                measure_objects_dict = results['measure_objects_dict']
                office_objects_dict = results['office_objects_dict']

            if positive_value_exists(batch_actions_analyzed_for_deletes):
                messages.add_message(request, messages.INFO, "Analyze For Deletes: "
                                                             "" + str(batch_actions_analyzed_for_deletes))

            return HttpResponseRedirect(reverse('import_export_batches:batch_set_batch_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&batch_set_id=" + str(batch_set_id) +
                                        "&state_code=" + state_code)

        if positive_value_exists(delete_all_button):
            batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
            batch_description_query = batch_description_query.filter(batch_description_analyzed=True)
            batch_list = list(batch_description_query)

            batch_actions_deleted = 0
            not_deleted_status = ""
            for one_batch_description in batch_list:
                results = import_data_from_batch_row_actions(
                    one_batch_description.kind_of_batch, IMPORT_DELETE, one_batch_description.batch_header_id)
                if results['number_of_table_rows_deleted']:
                    batch_actions_deleted += 1

                if not positive_value_exists(results['success']):
                    if len(not_deleted_status) < 1024:
                        not_deleted_status += results['status']

            if positive_value_exists(batch_actions_deleted):
                messages.add_message(request, messages.INFO, "Deletes in All Batches: "
                                                             "" + str(batch_actions_deleted) + ", ")

            if positive_value_exists(not_deleted_status):
                messages.add_message(request, messages.ERROR,
                                     "Create in All Batches, FAILED Creates: {not_deleted_status} "
                                     "".format(not_deleted_status=not_deleted_status))

            return HttpResponseRedirect(reverse('import_export_batches:batch_set_batch_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&batch_set_id=" + str(batch_set_id) +
                                        "&state_code=" + state_code)

        batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
        batch_set_count = batch_description_query.count()

        if not positive_value_exists(show_all_batches):
            batch_list = batch_description_query[:10]
        else:
            batch_list = list(batch_description_query)

        # Loop through all batches and add count data
        for one_batch_description in batch_list:
            batch_header_id = one_batch_description.batch_header_id
            one_batch_description.number_of_batch_rows_imported = batch_manager.fetch_batch_row_count(batch_header_id)
            one_batch_description.number_of_batch_rows_analyzed = \
                batch_manager.fetch_batch_row_action_count(batch_header_id, one_batch_description.kind_of_batch)
            one_batch_description.number_of_batch_actions_to_create = \
                batch_manager.fetch_batch_row_action_count(batch_header_id, one_batch_description.kind_of_batch,
                                                           IMPORT_CREATE)
            one_batch_description.number_of_table_rows_to_update = \
                batch_manager.fetch_batch_row_action_count(batch_header_id, one_batch_description.kind_of_batch,
                                                           IMPORT_ADD_TO_EXISTING)
            one_batch_description.number_of_table_rows_to_delete = \
                batch_manager.fetch_batch_row_action_count(batch_header_id, one_batch_description.kind_of_batch,
                                                           IMPORT_DELETE)
            one_batch_description.number_of_table_rows_already_deleted = \
                batch_manager.fetch_batch_row_action_count(batch_header_id, one_batch_description.kind_of_batch,
                                                           IMPORT_ALREADY_DELETED)
            one_batch_description.number_of_batch_actions_cannot_act = \
                one_batch_description.number_of_batch_rows_analyzed - \
                one_batch_description.number_of_batch_actions_to_create - \
                one_batch_description.number_of_table_rows_to_update - \
                one_batch_description.number_of_table_rows_to_delete - \
                one_batch_description.number_of_table_rows_already_deleted

            batch_set_kind_of_batch = one_batch_description.kind_of_batch

            batch_list_modified.append(one_batch_description)
    except BatchDescription.DoesNotExist:
        # This is fine
        pass

    election_list = Election.objects.order_by('-election_day_text')

    status_message = '{batch_set_count} batches in this batch set. '.format(batch_set_count=batch_set_count)

    batch_row_items_to_create_for_this_set = batch_manager.fetch_batch_row_action_count_in_batch_set(
        batch_set_id, batch_set_kind_of_batch, IMPORT_CREATE)
    if positive_value_exists(batch_row_items_to_create_for_this_set):
        status_message += 'BatchRowActions to create: {batch_row_items_to_create_for_this_set} '.format(
            batch_row_items_to_create_for_this_set=batch_row_items_to_create_for_this_set)

    batch_row_items_to_update_for_this_set = batch_manager.fetch_batch_row_action_count_in_batch_set(
        batch_set_id, batch_set_kind_of_batch, IMPORT_ADD_TO_EXISTING)
    if positive_value_exists(batch_row_items_to_update_for_this_set):
        status_message += 'BatchRowActions to update: {batch_row_items_to_update_for_this_set} '.format(
            batch_row_items_to_update_for_this_set=batch_row_items_to_update_for_this_set)

    batch_row_items_to_delete_for_this_set = batch_manager.fetch_batch_row_action_count_in_batch_set(
        batch_set_id, batch_set_kind_of_batch, IMPORT_DELETE)
    if positive_value_exists(batch_row_items_to_delete_for_this_set):
        status_message += 'BatchRowActions to delete: {batch_row_items_to_delete_for_this_set} '.format(
            batch_row_items_to_delete_for_this_set=batch_row_items_to_delete_for_this_set)

    messages.add_message(request, messages.INFO, status_message)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'batch_set_id':                     batch_set_id,
        'batch_list':                       batch_list_modified,
        'election_list':                    election_list,
        'google_civic_election_id':         google_civic_election_id,
        'show_all_batches':                 show_all_batches,
    }
    return render(request, 'import_export_batches/batch_set_batch_list.html', template_values)


@login_required
def refresh_ballots_for_voters_api_v4_view(request):
    """
    :param request:
    :return:
    """
    status = ""
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    use_batch_process = request.GET.get('use_batch_process', False)
    use_ballotpedia = request.GET.get('use_ballotpedia', False)
    use_ballotpedia = positive_value_exists(use_ballotpedia)
    use_ctcl = request.GET.get('use_ctcl', False)
    use_ctcl = positive_value_exists(use_ctcl)
    use_vote_usa = request.GET.get('use_vote_usa', False)
    use_vote_usa = positive_value_exists(use_vote_usa)

    try:
        # Give the volunteer who entered this credit
        volunteer_task_manager = VolunteerTaskManager()
        task_results = volunteer_task_manager.create_volunteer_task_completed(
            action_constant=VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED,
            request=request,
        )
    except Exception as e:
        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    if positive_value_exists(use_batch_process):
        from import_export_batches.controllers_batch_process import schedule_refresh_ballots_for_voters_api_v4
        results = schedule_refresh_ballots_for_voters_api_v4(
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            use_ballotpedia=use_ballotpedia,
            use_ctcl=use_ctcl,
            use_vote_usa=use_vote_usa)
        messages.add_message(request, messages.INFO, results['status'])
        url_variables = pass_through_batch_list_incoming_variables(request)
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    url_variables)
    else:
        return refresh_ballots_for_voters_api_v4_internal_view(
            request=request,
            from_browser=True,
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            use_ballotpedia=use_ballotpedia,
            use_ctcl=use_ctcl,
            use_vote_usa=use_vote_usa)


@login_required
def retrieve_ballots_for_entire_election_api_v4_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code_list = []
    status = ''
    batch_process_manager = BatchProcessManager()
    use_ballotpedia = request.GET.get('use_ballotpedia', False)
    use_ballotpedia = positive_value_exists(use_ballotpedia)
    use_ctcl = request.GET.get('use_ctcl', False)
    use_ctcl = positive_value_exists(use_ctcl)
    use_vote_usa = request.GET.get('use_vote_usa', False)
    use_vote_usa = positive_value_exists(use_vote_usa)

    if not positive_value_exists(google_civic_election_id):
        status += "GOOGLE_CIVIC_ELECTION_ID_MISSING "
        messages.add_message(request, messages.INFO, status)
        url_variables = pass_through_batch_list_incoming_variables(request)
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    url_variables)

    # Retrieve list of states in this election, and then loop through each state
    election_manager = ElectionManager()
    election_results = election_manager.retrieve_election(google_civic_election_id)
    if election_results['election_found']:
        election = election_results['election']
        state_code_list = election.state_code_list()
        status += "STATE_CODE_LIST: " + str(state_code_list) + " "

    if not positive_value_exists(len(state_code_list)):
        status += "STATE_CODE_LIST_MISSING "
        messages.add_message(request, messages.INFO, status)
        url_variables = pass_through_batch_list_incoming_variables(request)
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    url_variables)

    for state_code in state_code_list:
        # Refresh based on map points
        if batch_process_manager.is_batch_process_currently_scheduled(
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                kind_of_process=REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS):
            status += "(" + str(state_code) + ")-ALREADY_SCHEDULED_REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS "
        else:
            from import_export_batches.controllers_batch_process import \
                schedule_retrieve_ballots_for_polling_locations_api_v4
            results = schedule_retrieve_ballots_for_polling_locations_api_v4(
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                refresh_ballot_returned=True,
                use_ballotpedia=use_ballotpedia,
                use_ctcl=use_ctcl,
                use_vote_usa=use_vote_usa,
            )
            if not positive_value_exists(results['success']):
                status += results['status']

        # Refresh based on voter's who requested their own address
        if batch_process_manager.is_batch_process_currently_scheduled(
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                kind_of_process=REFRESH_BALLOT_ITEMS_FROM_VOTERS):
            status += "(" + str(state_code) + ")-ALREADY_SCHEDULED_REFRESH_BALLOT_ITEMS_FROM_VOTERS "
        else:
            from import_export_batches.controllers_batch_process import schedule_refresh_ballots_for_voters_api_v4
            results = schedule_refresh_ballots_for_voters_api_v4(
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                use_ballotpedia=use_ballotpedia,
                use_ctcl=use_ctcl,
                use_vote_usa=use_vote_usa,
            )
            if not positive_value_exists(results['success']):
                status += results['status']

        # Retrieve first time for each map point
        if batch_process_manager.is_batch_process_currently_scheduled(
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                kind_of_process=RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS):
            status += "(" + str(state_code) + ")-ALREADY_SCHEDULED_RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS "
        else:
            results = schedule_retrieve_ballots_for_polling_locations_api_v4(
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                refresh_ballot_returned=False,
                use_ballotpedia=use_ballotpedia,
                use_ctcl=use_ctcl,
                use_vote_usa=use_vote_usa,
            )
            if not positive_value_exists(results['success']):
                status += results['status']

    messages.add_message(request, messages.INFO, status)
    url_variables = pass_through_batch_list_incoming_variables(request)
    return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) + url_variables)


def refresh_ballots_for_voters_api_v4_internal_view(
        request=None,
        from_browser=False,
        google_civic_election_id="",
        state_code="",
        date_last_updated_should_not_exceed=None,
        batch_process_ballot_item_chunk=None,
        use_ballotpedia=False,
        use_ctcl=False,
        use_vote_usa=False,
):
    status = ""
    success = True
    batch_process_id = 0
    batch_process_ballot_item_chunk_id = 0
    batch_set_id = 0
    retrieve_row_count = 0

    if positive_value_exists(use_ballotpedia) or positive_value_exists(use_ctcl) or positive_value_exists(use_vote_usa):
        # Continue
        pass
    else:
        status += "MISSING_REQUIRED_BALLOT_DATA_PROVIDER "
        success = False
        results = {
            'status': status,
            'success': success,
            'batch_set_id': batch_set_id,
            'retrieve_row_count': retrieve_row_count,
        }
        return results

    try:
        if positive_value_exists(google_civic_election_id):
            election_on_stage = \
                Election.objects.using('readonly').get(google_civic_election_id=google_civic_election_id)
            ballotpedia_election_id = election_on_stage.ballotpedia_election_id
            ctcl_election_uuid = election_on_stage.ctcl_uuid
            election_day_text = election_on_stage.election_day_text
            election_local_id = election_on_stage.id
            election_state_code = election_on_stage.get_election_state()
            election_name = election_on_stage.election_name
            is_national_election = election_on_stage.is_national_election
        else:
            message = 'Could not retrieve Ballotpedia ballots. Missing google_civic_election_id.'
            if from_browser:
                messages.add_message(request, messages.ERROR, message)
                return HttpResponseRedirect(reverse('election:election_list', args=()))
            else:
                success = False
                status += message + " "
                results = {
                    'status':               status,
                    'success':              success,
                    'batch_set_id':         batch_set_id,
                    'retrieve_row_count':   retrieve_row_count,
                }
                return results
    except Election.MultipleObjectsReturned as e:
        message = 'Could not retrieve Ballotpedia ballots. More than one election found.'
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status':               status,
                'success':              success,
                'batch_set_id':         batch_set_id,
                'retrieve_row_count':   retrieve_row_count,
            }
            return results
    except Election.DoesNotExist:
        message = 'Could not retrieve Ballotpedia ballots. Election could not be found.'
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status':               status,
                'success':              success,
                'batch_set_id':         batch_set_id,
                'retrieve_row_count':   retrieve_row_count,
            }
            return results

    # Check to see if we have map point data related to the region(s) covered by this election
    # We request the ballot data for each map point as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    # if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
    #     messages.add_message(request, messages.ERROR,
    #                          'For National elections, a State Code is required in order to run any '
    #                          'Ballotpedia ballots preparation.')
    #     return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    ballot_returned_list_manager = BallotReturnedListManager()
    limit_voters_retrieved = MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK  # 125. Formerly 250 and 111

    # Retrieve voter_id entries from ballot_returned table, from oldest to newest
    if positive_value_exists(is_national_election) and positive_value_exists(state_code):
        results = ballot_returned_list_manager.retrieve_ballot_returned_list(
            google_civic_election_id=google_civic_election_id,
            for_voters=True,
            state_code=state_code,
            date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
            limit=limit_voters_retrieved)
    else:
        results = ballot_returned_list_manager.retrieve_ballot_returned_list(
            google_civic_election_id=google_civic_election_id,
            for_voters=True,
            date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
            limit=limit_voters_retrieved)
    if results['ballot_returned_list_found']:
        ballot_returned_list = results['ballot_returned_list']
    else:
        ballot_returned_list = []

    if len(ballot_returned_list) == 0:
        message = 'No ballot_returned items found for {election_name} for the state \'{state}\' earlier than ' \
                  'date_last_updated_should_not_exceed: \'{date_last_updated_should_not_exceed}\'. ' \
                  '(refresh_ballots_for_voters_api_v4_internal_view)'.format(
                    election_name=election_name,
                    date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
                    state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
        else:
            status += message + " "
            results = {
                'status':               status,
                'success':              success,
                'batch_set_id':         batch_set_id,
                'retrieve_row_count':   retrieve_row_count,
            }
            return results

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # If here, we assume we have already retrieved races for this election, and now we want to
    # put ballot items for this location onto a ballot
    existing_offices_by_election_dict = {}
    existing_candidate_objects_dict = {}
    existing_candidate_to_office_links_dict = {}
    existing_measure_objects_dict = {}
    new_office_we_vote_ids_list = []
    new_candidate_we_vote_ids_list = []
    new_measure_we_vote_ids_list = []

    batch_set_id = 0
    # Create Batch Set for ballot items
    import_date = date.today()
    batch_set_name = "Ballot items (from Voters v4) for " + election_name
    if positive_value_exists(state_code):
        batch_set_name += " (state " + str(state_code.upper()) + ")"
    if positive_value_exists(ballotpedia_election_id):
        batch_set_name += " - ballotpedia: " + str(ballotpedia_election_id)
    if positive_value_exists(ctcl_election_uuid):
        batch_set_name += " - CTCL "
    batch_set_name += " - " + str(import_date)

    try:
        batch_process_ballot_item_chunk_id = batch_process_ballot_item_chunk.id
        batch_process_id = batch_process_ballot_item_chunk.batch_process_id
        batch_set_id = batch_process_ballot_item_chunk.batch_set_id
    except Exception as e:
        pass

    batch_set_source = ''
    kind_of_batch = ''
    source_uri = ''
    if positive_value_exists(use_ballotpedia):
        batch_set_source = BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS
        kind_of_batch = 'IMPORT_BALLOTPEDIA_BALLOT_ITEMS'
        source_uri = BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL
    elif positive_value_exists(use_ctcl):
        batch_set_source = BATCH_SET_SOURCE_IMPORT_CTCL_BALLOT_ITEMS
        kind_of_batch = 'IMPORT_CTCL_BALLOT_ITEMS'
        source_uri = CTCL_VOTER_INFO_URL
    elif positive_value_exists(use_vote_usa):
        batch_set_source = BATCH_SET_SOURCE_IMPORT_VOTE_USA_BALLOT_ITEMS
        kind_of_batch = 'IMPORT_VOTE_USA_BALLOT_ITEMS'
        source_uri = VOTE_USA_VOTER_INFO_URL

    if not positive_value_exists(batch_set_id):
        # create batch_set object
        try:
            batch_set = BatchSet.objects.create(
                batch_set_description_text="",
                batch_set_name=batch_set_name,
                batch_set_source=batch_set_source,
                batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
                batch_process_id=batch_process_id,
                google_civic_election_id=google_civic_election_id,
                source_uri=source_uri,
                import_date=import_date,
                state_code=state_code)
            batch_set_id = batch_set.id
            if positive_value_exists(batch_set_id):
                status += " BATCH_SET_SAVED-BALLOTS_FOR_VOTERS "
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            status += " EXCEPTION_BATCH_SET " + str(e) + " "

        try:
            if positive_value_exists(batch_process_ballot_item_chunk_id):
                batch_process_ballot_item_chunk.batch_set_id = batch_set_id
                batch_process_ballot_item_chunk.save()
        except Exception as e:
            status += "UNABLE_TO_SAVE_BATCH_SET_ID_EARLY " + str(e) + " "

    if positive_value_exists(use_ballotpedia):
        from import_export_ballotpedia.controllers import retrieve_ballotpedia_ballot_items_for_one_voter_api_v4
    elif positive_value_exists(use_ctcl):
        from import_export_ctcl.controllers import retrieve_ctcl_ballot_items_for_one_voter_api
    elif positive_value_exists(use_vote_usa):
        pass
    for ballot_returned in ballot_returned_list:
        if positive_value_exists(use_ballotpedia):
            one_ballot_results = retrieve_ballotpedia_ballot_items_for_one_voter_api_v4(
                google_civic_election_id,
                election_day_text=election_day_text,
                ballot_returned=ballot_returned,
                state_code=state_code,
                batch_set_id=batch_set_id,
                existing_offices_by_election_dict=existing_offices_by_election_dict,
                existing_candidate_objects_dict=existing_candidate_objects_dict,
                existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                existing_measure_objects_dict=existing_measure_objects_dict,
                new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                new_measure_we_vote_ids_list=new_measure_we_vote_ids_list
            )
        elif positive_value_exists(use_ctcl):
            one_ballot_results = retrieve_ctcl_ballot_items_for_one_voter_api(
                google_civic_election_id,
                ctcl_election_uuid=ctcl_election_uuid,
                election_day_text=election_day_text,
                ballot_returned=ballot_returned,
                state_code=state_code,
                batch_set_id=batch_set_id,
                existing_offices_by_election_dict=existing_offices_by_election_dict,
                existing_candidate_objects_dict=existing_candidate_objects_dict,
                existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                existing_measure_objects_dict=existing_measure_objects_dict,
                new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                update_or_create_rules={})
        else:
            # It shouldn't be possible to get here
            pass
        success = False
        if one_ballot_results['success']:
            success = True

        if len(status) < 1024:
            status += one_ballot_results['status']

        existing_offices_by_election_dict = one_ballot_results['existing_offices_by_election_dict']
        existing_candidate_objects_dict = one_ballot_results['existing_candidate_objects_dict']
        existing_candidate_to_office_links_dict = one_ballot_results['existing_candidate_to_office_links_dict']
        existing_measure_objects_dict = one_ballot_results['existing_measure_objects_dict']
        new_office_we_vote_ids_list = one_ballot_results['new_office_we_vote_ids_list']
        new_candidate_we_vote_ids_list = one_ballot_results['new_candidate_we_vote_ids_list']
        new_measure_we_vote_ids_list = one_ballot_results['new_measure_we_vote_ids_list']

        if success:
            ballots_retrieved += 1
        else:
            ballots_not_retrieved += 1

    existing_offices_found = 0
    if google_civic_election_id in existing_offices_by_election_dict:
        existing_offices_found = len(existing_offices_by_election_dict[google_civic_election_id])
    existing_candidates_found = len(existing_candidate_objects_dict)
    existing_measures_found = len(existing_measure_objects_dict)
    new_offices_found = len(new_office_we_vote_ids_list)
    new_candidates_found = len(new_candidate_we_vote_ids_list)
    new_measures_found = len(new_measure_we_vote_ids_list)

    retrieve_row_count = ballots_retrieved

    message = \
        'Ballot data retrieved (Voters) for the {election_name}. ' \
        'ballots retrieved: {ballots_retrieved}. ' \
        'ballots not retrieved: {ballots_not_retrieved}. ' \
        'new offices: {new_offices_found} (existing: {existing_offices_found}) ' \
        'new candidates: {new_candidates_found} (existing: {existing_candidates_found}) ' \
        'new measures: {new_measures_found} (existing: {existing_measures_found}) ' \
        ''.format(
             ballots_retrieved=ballots_retrieved,
             ballots_not_retrieved=ballots_not_retrieved,
             election_name=election_name,
             existing_offices_found=existing_offices_found,
             existing_candidates_found=existing_candidates_found,
             existing_measures_found=existing_measures_found,
             new_offices_found=new_offices_found,
             new_candidates_found=new_candidates_found,
             new_measures_found=new_measures_found,
        )
    if from_browser:
        messages.add_message(request, messages.INFO, message)

        messages.add_message(request, messages.INFO, 'status: {status}'.format(status=status))

        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=' + str(kind_of_batch) +
                                    '&google_civic_election_id=' + str(google_civic_election_id))
    else:
        status += message + " "
        results = {
            'status':               status,
            'success':              success,
            'batch_set_id':         batch_set_id,
            'retrieve_row_count':   retrieve_row_count,
            'batch_process_ballot_item_chunk':  batch_process_ballot_item_chunk,
        }
        return results


@login_required
def retrieve_ballots_for_polling_locations_api_v4_view(request):
    """
    This is different than retrieve_ballotpedia_data_for_polling_locations_view because it is getting the districts
    from lat/long, and then the ballot items. Ballotpedia API v4
    Reach out to Ballotpedia and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those map points, enough that we are caching all the possible ballot items
    :param request:
    :return:
    """
    status = ""

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    refresh_ballot_returned = request.GET.get('refresh_ballot_returned', False)
    use_batch_process = request.GET.get('use_batch_process', False)
    use_ballotpedia = request.GET.get('use_ballotpedia', False)
    use_ballotpedia = positive_value_exists(use_ballotpedia)
    use_ctcl = request.GET.get('use_ctcl', False)
    use_ctcl = positive_value_exists(use_ctcl)
    use_vote_usa = request.GET.get('use_vote_usa', False)
    use_vote_usa = positive_value_exists(use_vote_usa)
    # import_limit = convert_to_int(request.GET.get('import_limit', 1000))  # If > 1000, we get error 414 (url too long)

    try:
        # Give the volunteer who entered this credit
        volunteer_task_manager = VolunteerTaskManager()
        task_results = volunteer_task_manager.create_volunteer_task_completed(
            action_constant=VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED,
            request=request,
        )
    except Exception as e:
        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    if positive_value_exists(use_batch_process):
        from import_export_batches.controllers_batch_process import \
            schedule_retrieve_ballots_for_polling_locations_api_v4
        results = schedule_retrieve_ballots_for_polling_locations_api_v4(
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            refresh_ballot_returned=refresh_ballot_returned,
            use_ballotpedia=use_ballotpedia,
            use_ctcl=use_ctcl,
            use_vote_usa=use_vote_usa)
        messages.add_message(request, messages.INFO, results['status'])
        url_variables = pass_through_batch_list_incoming_variables(request)
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    url_variables)
    else:
        return retrieve_ballots_for_polling_locations_api_v4_internal_view(
            request=request,
            from_browser=True,
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            refresh_ballot_returned=refresh_ballot_returned,
            use_ballotpedia=use_ballotpedia,
            use_ctcl=use_ctcl,
            use_vote_usa=use_vote_usa)


def retrieve_ballots_for_polling_locations_api_v4_internal_view(
        request=None,
        batch_process_id=0,
        from_browser=False,
        google_civic_election_id="",
        state_code="",
        refresh_ballot_returned=False,
        date_last_updated_should_not_exceed=None,
        batch_process_ballot_item_chunk=None,
        batch_process_date_started=None,
        use_ballotpedia=False,
        use_ctcl=False,
        use_vote_usa=False):
    status = ""
    success = True

    batch_process_ballot_item_chunk_id = 0
    batch_set_id = 0
    retrieve_row_count = 0
    ballot_returned_manager = BallotReturnedManager()

    try:
        if positive_value_exists(google_civic_election_id):
            election_on_stage = \
                Election.objects.using('readonly').get(google_civic_election_id=google_civic_election_id)
            ballotpedia_election_id = election_on_stage.ballotpedia_election_id
            ctcl_election_uuid = election_on_stage.ctcl_uuid
            election_day_text = election_on_stage.election_day_text
            election_local_id = election_on_stage.id
            election_state_code = election_on_stage.get_election_state()
            election_name = election_on_stage.election_name
            is_national_election = election_on_stage.is_national_election
            use_ballotpedia_as_data_source = election_on_stage.use_ballotpedia_as_data_source
            use_ctcl_as_data_source = election_on_stage.use_ctcl_as_data_source
            use_ctcl_as_data_source_by_state_code = election_on_stage.use_ctcl_as_data_source_by_state_code
            use_ctcl_as_data_source_override = False
            if positive_value_exists(state_code) and positive_value_exists(use_ctcl_as_data_source_by_state_code):
                if state_code.lower() in use_ctcl_as_data_source_by_state_code.lower():
                    use_ctcl_as_data_source_override = True
            use_vote_usa_as_data_source = election_on_stage.use_vote_usa_as_data_source
        else:
            message = 'Could not retrieve (as opposed to refresh) ballots. ' \
                      'Missing google_civic_election_id. '
            if from_browser:
                messages.add_message(request, messages.ERROR, message)
                return HttpResponseRedirect(reverse('election:election_list', args=()))
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
    except Election.MultipleObjectsReturned as e:
        message = 'Could not retrieve (as opposed to refresh) ballots. ' \
                  'More than one election found. ' + str(e) + ' '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
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
    except Election.DoesNotExist:
        message = 'Could not retrieve (as opposed to refresh) ballots. Election could not be found. '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
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
        message = 'Could not retrieve (as opposed to refresh) ballots. ERROR: ' + str(e) + ' '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
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

    if positive_value_exists(use_ballotpedia):
        if not positive_value_exists(use_ballotpedia_as_data_source):
            success = False
            status += "USE_BALLOTPEDIA-BUT_NOT_USE_BALLOTPEDIA_AS_DATA_SOURCE "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results
    elif positive_value_exists(use_ctcl):
        if not positive_value_exists(use_ctcl_as_data_source) \
                and not positive_value_exists(use_ctcl_as_data_source_override):
            success = False
            status += "USE_CTCL-BUT_NOT_USE_CTCL_AS_DATA_SOURCE "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results
    elif positive_value_exists(use_vote_usa):
        if not positive_value_exists(use_vote_usa_as_data_source):
            success = False
            status += "USE_VOTE_USA-BUT_NOT_USE_VOTE_USA_AS_DATA_SOURCE "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    # Check to see if we have map point data related to the region(s) covered by this election
    # We request the ballot data for each map point as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
        message = \
            'For National elections, a State Code is required in order to run any ballot preparation. '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
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

    polling_location_manager = PollingLocationManager()
    try:
        if positive_value_exists(refresh_ballot_returned):
            kind_of_process = REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS
        else:
            kind_of_process = RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS

        ballot_returned_list_manager = BallotReturnedListManager()
        batch_process_manager = BatchProcessManager()
        if not positive_value_exists(batch_process_date_started) or not positive_value_exists(batch_process_id):
            try:
                if not positive_value_exists(batch_process_id):
                    batch_process_id = batch_process_ballot_item_chunk.batch_process_id
                results = batch_process_manager.retrieve_batch_process(
                    batch_process_id=batch_process_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_process=kind_of_process,
                    state_code=state_code,
                    use_ctcl=use_ctcl,
                    use_vote_usa=use_vote_usa,
                )
                if results['batch_process_found']:
                    batch_process = results['batch_process']
                    batch_process_date_started = batch_process.date_started
            except Exception as e:
                status += "COULD_NOT_GET_BATCH_PROCESS_ID_FROM_BATCH_PROCESS_BALLOT_ITEM_CHUNK: " + str(e) + ' '
        if not positive_value_exists(batch_process_date_started):
            try:
                results = batch_process_manager.retrieve_batch_process(
                    google_civic_election_id=google_civic_election_id,
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

        # Retrieve the polling locations/map points already in ballot_returned table
        if positive_value_exists(is_national_election) and positive_value_exists(state_code):
            status += "NATIONAL_WITH_STATE (" + str(state_code) + ") "
        else:
            status += "WITHOUT_STATE "
        results = ballot_returned_list_manager.retrieve_polling_location_we_vote_id_list_from_ballot_returned(
            google_civic_election_id=google_civic_election_id,
            state_code=state_code,
            limit=0,
        )
        status += results['status']
        if results['polling_location_we_vote_id_list_found']:
            polling_location_we_vote_id_list_from_ballot_returned = results['polling_location_we_vote_id_list']
        else:
            polling_location_we_vote_id_list_from_ballot_returned = []

        # Find polling_location_we_vote_ids already used in this batch_process, which returned a ballot
        polling_location_we_vote_id_list_already_retrieved = []
        if positive_value_exists(batch_process_id):
            polling_location_log_entry_list = polling_location_manager.retrieve_polling_location_log_entry_list(
                batch_process_id=batch_process_id,
                is_from_ctcl=use_ctcl,
                is_from_vote_usa=use_vote_usa,
                kind_of_log_entry_list=[KIND_OF_LOG_ENTRY_BALLOT_RECEIVED],
            )
            for one_log_entry in polling_location_log_entry_list:
                if one_log_entry.polling_location_we_vote_id not in polling_location_we_vote_id_list_already_retrieved:
                    polling_location_we_vote_id_list_already_retrieved.append(one_log_entry.polling_location_we_vote_id)

        # For both REFRESH and RETRIEVE, find polling locations/map points which have come up empty
        #  (from this data source) in previous chunks since when this process started
        polling_location_we_vote_id_list_returned_empty = []
        results = ballot_returned_list_manager.\
            retrieve_polling_location_we_vote_id_list_from_ballot_returned_empty(
                batch_process_date_started=batch_process_date_started,
                is_from_ctcl=use_ctcl,
                is_from_vote_usa=use_vote_usa,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
            )
        if results['polling_location_we_vote_id_list_found']:
            polling_location_we_vote_id_list_returned_empty = results['polling_location_we_vote_id_list']

        status += "REFRESH_BALLOT_RETURNED: " + str(refresh_ballot_returned) + " "

        # For both REFRESH and RETRIEVE, see if the number of map points for this state exceed the "large" threshold
        refresh_or_retrieve_limit = \
            polling_location_manager.calculate_number_of_map_points_to_retrieve_with_each_batch_chunk(state_code)

        if positive_value_exists(refresh_ballot_returned):
            # REFRESH branch
            polling_location_query = PollingLocation.objects.using('readonly').all()
            # In this "Refresh" branch, use polling locations we already have a ballot returned entry for, and
            # exclude map points already retrieved in this batch and those returned empty since this process started
            polling_location_we_vote_id_list_to_exclude = \
                list(set(polling_location_we_vote_id_list_already_retrieved +
                         polling_location_we_vote_id_list_returned_empty))
            polling_location_we_vote_id_list_to_retrieve = \
                list(set(polling_location_we_vote_id_list_from_ballot_returned) -
                     set(polling_location_we_vote_id_list_to_exclude))
            polling_location_we_vote_id_list_to_retrieve_limited = \
                polling_location_we_vote_id_list_to_retrieve[:refresh_or_retrieve_limit]
            polling_location_query = \
                polling_location_query.filter(we_vote_id__in=polling_location_we_vote_id_list_to_retrieve_limited)
            if positive_value_exists(use_ctcl):
                # CTCL only supports full addresses, so don't bother trying to pass addresses without line1
                polling_location_query = \
                    polling_location_query.exclude(Q(line1__isnull=True) | Q(line1__exact=''))
            # We don't exclude the deleted map points because we need to know to delete the ballot returned entry
            # polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            polling_location_list = list(polling_location_query)
        else:
            # RETRIEVE branch
            polling_location_query = PollingLocation.objects.using('readonly').all()
            polling_location_query = \
                polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            polling_location_query = \
                polling_location_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                               Q(zip_long__exact=''))
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            # In this "Retrieve" branch, exclude polling locations we already have a ballot returned entry for, and
            # exclude map points already retrieved in this batch and those returned empty since this process started
            polling_location_we_vote_id_list_to_exclude = \
                list(set(polling_location_we_vote_id_list_from_ballot_returned +
                         polling_location_we_vote_id_list_already_retrieved +
                         polling_location_we_vote_id_list_returned_empty))
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
        # Cycle through -- if the polling_location is deleted, delete the associated ballot_returned,
        #  and then remove the polling_location from the list
        modified_polling_location = []
        for one_polling_location in polling_location_list:
            if positive_value_exists(one_polling_location.polling_location_deleted):
                delete_results = ballot_returned_manager.delete_ballot_returned_by_identifier(
                    google_civic_election_id=google_civic_election_id,
                    polling_location_we_vote_id=one_polling_location.we_vote_id)
                if delete_results['ballot_deleted']:
                    status += "BR_PL_DELETED (" + str(one_polling_location.we_vote_id) + ") "
                else:
                    status += "BR_PL_NOT_DELETED (" + str(one_polling_location.we_vote_id) + ") "
            else:
                modified_polling_location.append(one_polling_location)
        polling_location_list = modified_polling_location
        polling_location_count = len(polling_location_list)
    except PollingLocation.DoesNotExist:
        message = 'Could not retrieve (as opposed to refresh) ballot data for the {election_name}. ' \
                  'Ballots-No map points exist for the state \'{state}\'. ' \
                  ''.format(
                     election_name=election_name,
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
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
        message = 'Could not retrieve (as opposed to refresh) ballot data for the {election_name}. ' \
                  'Ballots-No map points exist for the state \'{state}\'. ERROR: {error}' \
                  ''.format(
                     election_name=election_name,
                     error=str(e),
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
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
        message = 'Data for all map points for the state \'{state}\' for the {election_name} ' \
                  'have been retrieved once. Please use RETRIEVE to get latest data. ' \
                  'date_last_updated_should_not_exceed: \'{date_last_updated_should_not_exceed}\'. ' \
                  '(result 2 - retrieve_ballots_for_polling_locations_api_v4_view)'.format(
                     election_name=election_name,
                     date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
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
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # If here, we assume we have already retrieved races for this election, and now we want to
    # put ballot items for this location onto a ballot
    existing_offices_by_election_dict = {}
    existing_candidate_objects_dict = {}
    existing_candidate_to_office_links_dict = {}
    existing_measure_objects_dict = {}
    new_office_we_vote_ids_list = []
    new_candidate_we_vote_ids_list = []
    new_measure_we_vote_ids_list = []

    batch_set_source = ''
    source_uri = ''
    if positive_value_exists(use_ballotpedia):
        batch_set_source = BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS
        source_uri = BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL
    elif positive_value_exists(use_ctcl):
        batch_set_source = BATCH_SET_SOURCE_IMPORT_CTCL_BALLOT_ITEMS
        source_uri = CTCL_VOTER_INFO_URL
    elif positive_value_exists(use_vote_usa):
        batch_set_source = BATCH_SET_SOURCE_IMPORT_VOTE_USA_BALLOT_ITEMS
        source_uri = VOTE_USA_VOTER_INFO_URL

    batch_set_id = 0
    if len(polling_location_list) > 0:
        status += "POLLING_LOCATIONS_FOR_THIS_BATCH_SET: " + str(len(polling_location_list)) + " "
        # Create Batch Set for ballot items
        import_date = date.today()
        batch_set_name = "Ballot items (from Map Points v4) for " + election_name
        if positive_value_exists(state_code):
            batch_set_name += " (state " + str(state_code.upper()) + ")"
        if positive_value_exists(ballotpedia_election_id):
            batch_set_name += " - ballotpedia: " + str(ballotpedia_election_id)
        elif positive_value_exists(use_ctcl):
            batch_set_name += " - ctcl"
        elif positive_value_exists(use_vote_usa):
            batch_set_name += " - vote usa"
        batch_set_name += " - " + str(import_date)

        try:
            batch_process_ballot_item_chunk_id = batch_process_ballot_item_chunk.id
            batch_process_id = batch_process_ballot_item_chunk.batch_process_id
            batch_set_id = batch_process_ballot_item_chunk.batch_set_id
        except Exception as e:
            status += "BATCH_PROCESS_BALLOT_ITEM_CHUNK: " + str(e) + ' '

        if not positive_value_exists(batch_set_id):
            # create batch_set object
            try:
                batch_set = BatchSet.objects.create(
                    batch_set_description_text="",
                    batch_set_name=batch_set_name,
                    batch_set_source=batch_set_source,
                    batch_process_id=batch_process_id,
                    batch_process_ballot_item_chunk_id=batch_process_ballot_item_chunk_id,
                    google_civic_election_id=google_civic_election_id,
                    source_uri=source_uri,
                    import_date=import_date,
                    state_code=state_code)
                batch_set_id = batch_set.id
                status += " BATCH_SET_CREATED-BALLOTS_FOR_POLLING_LOCATIONS "
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_SET " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                success = False

            try:
                if positive_value_exists(batch_process_ballot_item_chunk_id) and positive_value_exists(batch_set_id):
                    batch_process_ballot_item_chunk.batch_set_id = batch_set_id
                    batch_process_ballot_item_chunk.save()
            except Exception as e:
                status += "UNABLE_TO_SAVE_BATCH_SET_ID_EARLY " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)

    update_or_create_rules = {
        'create_candidates':    True,
        'create_offices':       True,
        'create_measures':      True,
        'update_candidates':    False,
        'update_offices':       False,
        'update_measures':      False,
    }

    if success:
        if positive_value_exists(use_ballotpedia):
            from import_export_ballotpedia.controllers import \
                retrieve_ballotpedia_ballot_items_from_polling_location_api_v4
        elif positive_value_exists(use_ctcl):
            from import_export_ctcl.controllers import retrieve_ctcl_ballot_items_from_polling_location_api
        elif positive_value_exists(use_vote_usa):
            from import_export_vote_usa.controllers import retrieve_vote_usa_ballot_items_from_polling_location_api
        contest_not_returned_from_data_source_polling_location_we_vote_id_list = []
        contest_returned_from_data_source_polling_location_we_vote_id_list = []
        for polling_location in polling_location_list:
            one_ballot_results = {}
            if positive_value_exists(use_ballotpedia):
                one_ballot_results = retrieve_ballotpedia_ballot_items_from_polling_location_api_v4(
                    google_civic_election_id,
                    election_day_text=election_day_text,
                    polling_location_we_vote_id=polling_location.we_vote_id,
                    polling_location=polling_location,
                    state_code=state_code,
                    batch_set_id=batch_set_id,
                    existing_offices_by_election_dict=existing_offices_by_election_dict,
                    existing_candidate_objects_dict=existing_candidate_objects_dict,
                    existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                    existing_measure_objects_dict=existing_measure_objects_dict,
                    new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                    new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                    new_measure_we_vote_ids_list=new_measure_we_vote_ids_list
                )
            elif positive_value_exists(use_ctcl):
                one_ballot_results = retrieve_ctcl_ballot_items_from_polling_location_api(
                    batch_process_id=batch_process_id,
                    google_civic_election_id=google_civic_election_id,
                    ctcl_election_uuid=ctcl_election_uuid,
                    election_day_text=election_day_text,
                    polling_location_we_vote_id=polling_location.we_vote_id,
                    polling_location=polling_location,
                    state_code=state_code,
                    batch_set_id=batch_set_id,
                    existing_offices_by_election_dict=existing_offices_by_election_dict,
                    existing_candidate_objects_dict=existing_candidate_objects_dict,
                    existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                    existing_measure_objects_dict=existing_measure_objects_dict,
                    new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                    new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                    new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                    update_or_create_rules=update_or_create_rules,
                )
            elif positive_value_exists(use_vote_usa):
                one_ballot_results = retrieve_vote_usa_ballot_items_from_polling_location_api(
                    google_civic_election_id=google_civic_election_id,
                    election_day_text=election_day_text,
                    polling_location_we_vote_id=polling_location.we_vote_id,
                    polling_location=polling_location,
                    state_code=state_code,
                    batch_process_id=batch_process_id,
                    batch_set_id=batch_set_id,
                    existing_offices_by_election_dict=existing_offices_by_election_dict,
                    existing_candidate_objects_dict=existing_candidate_objects_dict,
                    existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                    existing_measure_objects_dict=existing_measure_objects_dict,
                    new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                    new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                    new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                    update_or_create_rules=update_or_create_rules,
                )
            else:
                # Should not be possible to get here
                pass

            if one_ballot_results and 'success' in one_ballot_results and one_ballot_results['success']:
                success = True

            existing_offices_by_election_dict = one_ballot_results['existing_offices_by_election_dict']
            existing_candidate_objects_dict = one_ballot_results['existing_candidate_objects_dict']
            existing_candidate_to_office_links_dict = one_ballot_results['existing_candidate_to_office_links_dict']
            existing_measure_objects_dict = one_ballot_results['existing_measure_objects_dict']
            new_office_we_vote_ids_list = one_ballot_results['new_office_we_vote_ids_list']
            new_candidate_we_vote_ids_list = one_ballot_results['new_candidate_we_vote_ids_list']
            new_measure_we_vote_ids_list = one_ballot_results['new_measure_we_vote_ids_list']

            if one_ballot_results['batch_header_id']:
                ballots_retrieved += 1
                contest_returned_from_data_source_polling_location_we_vote_id_list.append(
                    polling_location.we_vote_id)
                if ballots_retrieved < 5:
                    # Only show this error message status for the first 4 times so we don't overwhelm the log
                    status += "BALLOT_ITEMS_RETRIEVED: [[[" + one_ballot_results['status'] + "]]] "
            else:
                ballots_not_retrieved += 1
                contest_not_returned_from_data_source_polling_location_we_vote_id_list.append(
                    polling_location.we_vote_id)
                if ballots_not_retrieved < 5:
                    # Only show this error message status for the first 4 times so we don't overwhelm the log
                    status += "BALLOT_ITEMS_NOT_RETRIEVED: [[[" + one_ballot_results['status'] + "]]] "
        if positive_value_exists(len(contest_returned_from_data_source_polling_location_we_vote_id_list)):
            status += "contest_returned_from_data_source_polling_location_we_vote_id_list: " + \
                      str(contest_returned_from_data_source_polling_location_we_vote_id_list) + " "
        if positive_value_exists(len(contest_not_returned_from_data_source_polling_location_we_vote_id_list)):
            status += "contest_not_returned_from_data_source_polling_location_we_vote_id_list: " + \
                      str(contest_not_returned_from_data_source_polling_location_we_vote_id_list) + " "
    else:
        status += "CANNOT_CALL_RETRIEVE_BECAUSE_OF_ERRORS " \
                  "[retrieve_ballots_for_polling_locations_api_v4_internal_view] "
    retrieve_row_count = ballots_retrieved

    existing_offices_found = 0
    if google_civic_election_id in existing_offices_by_election_dict:
        existing_offices_found = len(existing_offices_by_election_dict[google_civic_election_id])
    existing_candidates_found = len(existing_candidate_objects_dict)
    existing_measures_found = len(existing_measure_objects_dict)
    new_offices_found = len(new_office_we_vote_ids_list)
    new_candidates_found = len(new_candidate_we_vote_ids_list)
    new_measures_found = len(new_measure_we_vote_ids_list)

    if from_browser:
        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Map Points for the {election_name}. '
                             'ballots retrieved: {ballots_retrieved}, '
                             'ballots NOT retrieved: {ballots_not_retrieved}. '
                             'new offices: {new_offices_found} (existing: {existing_offices_found}) '
                             'new candidates: {new_candidates_found} (existing: {existing_candidates_found}) '
                             'new measures: {new_measures_found} (existing: {existing_measures_found}) '
                             ''.format(
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 election_name=election_name,
                                 existing_offices_found=existing_offices_found,
                                 existing_candidates_found=existing_candidates_found,
                                 existing_measures_found=existing_measures_found,
                                 new_offices_found=new_offices_found,
                                 new_candidates_found=new_candidates_found,
                                 new_measures_found=new_measures_found,
                             ))

        messages.add_message(request, messages.INFO, 'status: {status}'.format(status=status))

        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=IMPORT_BALLOTPEDIA_BALLOT_ITEMS' +
                                    '&google_civic_election_id=' + str(google_civic_election_id))
    else:
        status += \
            'Ballot data retrieved for the {election_name} (from Map Points). ' \
            'ballots retrieved: {ballots_retrieved}. ' \
            'ballots NOT retrieved: {ballots_not_retrieved}. ' \
            'new offices: {new_offices_found} (existing: {existing_offices_found}) ' \
            'new candidates: {new_candidates_found} (existing: {existing_candidates_found}) ' \
            'new measures: {new_measures_found} (existing: {existing_measures_found}) ' \
            ''.format(
                ballots_retrieved=ballots_retrieved,
                ballots_not_retrieved=ballots_not_retrieved,
                election_name=election_name,
                existing_offices_found=existing_offices_found,
                existing_candidates_found=existing_candidates_found,
                existing_measures_found=existing_measures_found,
                new_offices_found=new_offices_found,
                new_candidates_found=new_candidates_found,
                new_measures_found=new_measures_found,
            )
        results = {
            'status':               status,
            'success':              success,
            'batch_set_id':         batch_set_id,
            'retrieve_row_count':   retrieve_row_count,
            'batch_process_ballot_item_chunk':  batch_process_ballot_item_chunk,
        }
        return results
