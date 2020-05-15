# import_export_batches/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BatchDescription, BatchHeader, BatchHeaderMap, BatchManager, \
    BatchProcess, BatchProcessAnalyticsChunk, BatchProcessBallotItemChunk, BatchProcessLogEntry, BatchProcessManager, \
    BatchRow, BatchRowActionBallotItem, \
    BatchSet, \
    CONTEST_OFFICE, ELECTED_OFFICE, IMPORT_BALLOT_ITEM, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS, \
    IMPORT_CREATE, IMPORT_DELETE, IMPORT_ALREADY_DELETED, IMPORT_ADD_TO_EXISTING, IMPORT_VOTER
from .controllers import create_batch_header_translation_suggestions, create_batch_row_actions, \
    create_or_update_batch_header_mapping, export_voter_list_with_emails, import_data_from_batch_row_actions
from .controllers_batch_process import batch_process_next_steps
from .controllers_ballotpedia import store_ballotpedia_json_response_to_import_batch_system
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import MEASURE, CANDIDATE, POLITICIAN
import csv
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db.models import Q
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.utils.http import urlquote
from election.models import Election, ElectionManager
from import_export_ballotpedia.controllers import groom_ballotpedia_data_for_processing, \
    process_ballotpedia_voter_districts
import json
from polling_location.models import PollingLocation, PollingLocationManager
from position.models import POSITION
import requests
from voter.models import voter_has_authority
from voter_guide.models import ORGANIZATION_WORD
# import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP


# logger = wevote_functions.admin.get_logger(__name__)


@login_required
def batches_home_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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

    if kind_of_batch == ORGANIZATION_WORD or kind_of_batch == ELECTED_OFFICE or kind_of_batch == POLITICIAN:
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
                    if convert_to_int(one_election.google_civic_election_id) == convert_to_int(google_civic_election_id):
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    kind_of_batch = request.POST.get('kind_of_batch', '')
    batch_uri = request.POST.get('batch_uri', '')
    batch_uri_encoded = urlquote(batch_uri) if positive_value_exists(batch_uri) else ""
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    polling_location_we_vote_id = request.POST.get('polling_location_we_vote_id', "")
    polling_location_city = request.POST.get('polling_location_city', '')
    polling_location_zip = request.POST.get('polling_location_zip', '')
    show_all_elections = positive_value_exists(request.POST.get('show_all_elections', ""))
    state_code = request.POST.get('state_code', "")
    if kind_of_batch not in (MEASURE, ELECTED_OFFICE, CONTEST_OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION,
                             POLITICIAN, IMPORT_BALLOT_ITEM):
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
    if kind_of_batch in ORGANIZATION_WORD and not batch_file:
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
    if kind_of_batch not in ORGANIZATION_WORD and not positive_value_exists(google_civic_election_id):
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
    #                                                   'to choose a polling location.'
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
                messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_set_list = []
    polling_location_we_vote_id = ""

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
            elif kind_of_batch == ELECTED_OFFICE:
                existing_results = batch_manager.retrieve_batch_row_action_elected_office(batch_header_id,
                                                                                          one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_elected_office']
                    one_batch_row.kind_of_batch = ELECTED_OFFICE
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

    messages.add_message(request, messages.INFO, 'Batch Row Count: {batch_row_count}'
                                                 ''.format(batch_row_count=batch_row_count))

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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    row_opts = BatchRow._meta
    row_field_names = []
    for field in row_opts.fields:
        if field.name not in ['id', 'batch_header_id', 'batch_row_analyzed', 'batch_row_created']:
            if kind_of_batch == 'IMPORT_VOTER':
                if field.name not in ['state_code', 'google_civic_election_id', 'polling_location_we_vote_id', 'voter_id']:
                    row_field_names.append(field.name)
            else:
                row_field_names.append(field.name)

    header_list = [getattr(batch_header_map, field) for field in header_field_names]
    if kind_of_batch != 'IMPORT_VOTER':
        header_list.insert(0, 'google_civic_election_id')
        header_list.insert(0, 'state_code')
    # - Filter out headers that are None.
    header_list = list(filter(None, header_list))

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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    Create BatchRowActions for either all of the BatchRows for batch_header_id, or only one with batch_row_id
    :param request:
    :return:
    """

    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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

    # if create_actions_button in (MEASURE, ELECTED_OFFICE, CANDIDATE, ORGANIZATION_WORD,
    # POSITION, POLITICIAN, IMPORT_BALLOT_ITEM)
    # Run the analysis of either A) every row in this batch, or B) Just the batch_row_id specified within this batch
    results = create_batch_row_actions(batch_header_id=batch_header_id, batch_description=None,
                                       batch_row_id=batch_row_id, state_code=state_code,
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    elif kind_of_batch == ELECTED_OFFICE:
        batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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

    batch_header_mapping_results = create_or_update_batch_header_mapping(
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
def batch_action_list_create_or_update_process_view(request):
    """
    Use batch_row_action entries and create live data
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
            kind_of_batch, kind_of_action, batch_header_id, batch_row_id, state_code, ballot_item_id=ballot_item_id)
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # kind_of_batch = request.GET.get('kind_of_batch', '')
    batch_file = request.GET.get('batch_file', '')
    batch_uri = request.GET.get('batch_uri', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    limit = request.GET.get('limit', 25)

    messages_on_stage = get_messages(request)
    batch_set_list_found = False
    try:
        batch_set_query = BatchSet.objects.order_by('-import_date')
        # batch_set_list = batch_set_list.exclude(batch_set_id__isnull=True)
        if positive_value_exists(google_civic_election_id):
            batch_set_query = batch_set_query.filter(google_civic_election_id=google_civic_election_id)

        batch_set_list = batch_set_query[:limit]
        if len(batch_set_list):
            batch_set_list_found = True
    except BatchSet.DoesNotExist:
        # This is fine
        batch_set_list = []
        batch_set_list_found = False
        pass

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
            'messages_on_stage':        messages_on_stage,
            'batch_set_list':           batch_set_list,
            'election_list':            election_list,
            'batch_file':               batch_file,
            'batch_uri':                batch_uri,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'election_list':            election_list,
            'batch_file':               batch_file,
            'batch_uri':                batch_uri,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'import_export_batches/batch_set_list.html', template_values)


@login_required
def batch_set_list_process_view(request):
    """
    Load in a new batch set to start the importing process
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_uri = request.POST.get('batch_uri', '')
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    organization_we_vote_id = request.POST.get('organization_we_vote_id', '')
    # Was form submitted, or was election just changed?
    import_batch_button = request.POST.get('import_batch_button', '')

    batch_uri_encoded = urlquote(batch_uri) if positive_value_exists(batch_uri) else ""
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
                messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
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
            messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
                                                         ''.format(election_name=election_name))
        else:
            messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&batch_uri=" + batch_uri_encoded)


@login_required
def batch_process_system_toggle_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    batch_process_search = request.GET.get('batch_process_search', '')

    from wevote_settings.models import WeVoteSettingsManager
    we_vote_settings_manager = WeVoteSettingsManager()
    results = we_vote_settings_manager.fetch_setting_results(setting_name='batch_process_system_on', read_only=False)
    if results['we_vote_setting_found']:
        we_vote_setting = results['we_vote_setting']
        we_vote_setting.boolean_value = not we_vote_setting.boolean_value
        we_vote_setting.save()
    else:
        messages.add_message(request, messages.ERROR, "CANNOT_FIND_WE_VOTE_SETTING-batch_process_system_on")

    return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def batch_process_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    kind_of_processes_to_show = request.GET.get('kind_of_processes_to_show', '')
    state_code = request.GET.get('state_code', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_active_processes_only = request.GET.get('show_active_processes_only', False)
    show_paused_processes_only = request.GET.get('show_paused_processes_only', False)
    batch_process_search = request.GET.get('batch_process_search', '')

    batch_process_list = []

    election_manager = ElectionManager()
    batch_process_manager = BatchProcessManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    try:
        batch_process_queryset = BatchProcess.objects.all()
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
        if positive_value_exists(kind_of_processes_to_show):
            if kind_of_processes_to_show == "BALLOT_ITEMS":
                ballot_item_processes = [
                    'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS',
                    'REFRESH_BALLOT_ITEMS_FROM_VOTERS',
                    'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=ballot_item_processes)
            if kind_of_processes_to_show == "SEARCH_TWITTER":
                search_twitter_processes = [
                    'SEARCH_TWITTER_FOR_CANDIDATE_TWITTER_HANDLE']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=search_twitter_processes)
        batch_process_queryset = batch_process_queryset.order_by("-id")

        if positive_value_exists(batch_process_search):
            search_words = batch_process_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__icontains=one_word)
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
        status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e)) + " "
        success = False

    # Add the processing "chunks" under each Batch Process
    for batch_process in batch_process_list:
        batch_process_ballot_item_chunk_list = []
        batch_process_ballot_item_chunk_list_found = False
        batch_process_analytics_chunk_list = []
        batch_process_analytics_chunk_list_found = False
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
            status += 'FAILED BatchProcessBallotItemChunk ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e)) + " "
        batch_process.batch_process_ballot_item_chunk_list = batch_process_ballot_item_chunk_list
        batch_process.batch_process_ballot_item_chunk_list_found = batch_process_ballot_item_chunk_list_found

        if not positive_value_exists(batch_process_ballot_item_chunk_list_found):
            # Now check to see if this is an analytics
            try:
                batch_process_chunk_queryset = BatchProcessAnalyticsChunk.objects.all()
                batch_process_chunk_queryset = batch_process_chunk_queryset.filter(batch_process_id=batch_process.id)
                batch_process_chunk_queryset = batch_process_chunk_queryset.order_by("-id")
                batch_process_analytics_chunk_list = list(batch_process_chunk_queryset)
                batch_process_analytics_chunk_list_found = \
                    positive_value_exists(len(batch_process_analytics_chunk_list))
            except BatchProcessBallotItemChunk.DoesNotExist:
                # BatchProcessBallotItemChunk not found. Not a problem.
                status += 'NO_BatchProcessAnalyticsChunk_FOUND_DoesNotExist '
            except Exception as e:
                status += 'FAILED BatchProcessAnalyticsChunk ' \
                          '{error} [type: {error_type}] '.format(error=e, error_type=type(e)) + " "
            batch_process.batch_process_analytics_chunk_list = batch_process_analytics_chunk_list
            batch_process.batch_process_analytics_chunk_list_found = batch_process_analytics_chunk_list_found

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

    from wevote_settings.models import fetch_batch_process_system_on
    batch_process_system_on = fetch_batch_process_system_on()

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'batch_process_list':       batch_process_list,
        'batch_process_system_on':  batch_process_system_on,
        'batch_process_search':     batch_process_search,
        'election_list':            election_list,
        'kind_of_processes_to_show':    kind_of_processes_to_show,
        'state_code':               state_code,
        'show_all_elections':       show_all_elections,
        'show_active_processes_only':   show_active_processes_only,
        'show_paused_processes_only':   show_paused_processes_only,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'import_export_batches/batch_process_list.html', template_values)


def batch_process_next_steps_view(request):
    json_results = batch_process_next_steps()

    response = HttpResponse(json.dumps(json_results), content_type='application/json')
    return response


@login_required
def batch_process_pause_toggle_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_process_id = request.GET.get('batch_process_id', 0)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    batch_process_manager = BatchProcessManager()
    results = batch_process_manager.retrieve_batch_process(batch_process_id)
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

    return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def batch_process_log_entry_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    batch_process_log_entry_search = request.GET.get('batch_process_log_entry_search', '')

    batch_process_log_entry_list_found = False
    batch_process_log_entry_list = []

    election_manager = ElectionManager()
    batch_process_manager = BatchProcessManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    try:
        batch_process_queryset = BatchProcessLogEntry.objects.all()
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
                new_filter = Q(office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__icontains=one_word)
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
        status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                 '{error} [type: {error_type}] '.format(error=e, error_type=type(e)) + " "
        success = False

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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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

    try:
        if positive_value_exists(analyze_all_button):
            batch_actions_analyzed = 0
            batch_actions_not_analyzed = 0
            batch_header_id_created_list = []

            batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
            batch_description_query = batch_description_query.filter(batch_description_analyzed=False)
            batch_list = list(batch_description_query)
            batch_list_not_analyzed_count = len(batch_list)

            for one_batch_description in batch_list:
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

            # If there were not any entries with batch_description_analyzed set to False, then retrieve all
            if not positive_value_exists(batch_list_not_analyzed_count):
                batch_description_query = BatchDescription.objects.filter(batch_set_id=batch_set_id)
                if positive_value_exists(len(batch_header_id_created_list)):
                    batch_description_query = batch_description_query.exclude(
                        batch_header_id__in=batch_header_id_created_list)
                batch_list = list(batch_description_query)

                for one_batch_description in batch_list:
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
                    one_batch_description.kind_of_batch, IMPORT_ADD_TO_EXISTING, one_batch_description.batch_header_id)
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
                    one_batch_description.kind_of_batch, IMPORT_CREATE, one_batch_description.batch_header_id)
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
        batch_list = list(batch_description_query)

        if not positive_value_exists(show_all_batches):
            batch_list = batch_list[:10]

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
