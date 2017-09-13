# import_export_batches/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BatchDescription, BatchHeader, BatchHeaderMap, BatchManager, BatchRow, BatchSet, \
    CONTEST_OFFICE, ELECTED_OFFICE, IMPORT_BALLOT_ITEM, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS, \
    IMPORT_CREATE, IMPORT_ADD_TO_EXISTING, IMPORT_QUERY_ERROR, IMPORT_TO_BE_DETERMINED
from .controllers import create_batch_header_translation_suggestions, create_batch_row_actions, \
    create_or_update_batch_header_mapping, \
    import_data_from_batch_row_actions, import_create_or_update_elected_office_entry
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import MEASURE, CANDIDATE, POLITICIAN
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.http import urlquote
from election.models import Election, ElectionManager
from position.models import POSITION
from voter.models import voter_has_authority
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


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

    messages_on_stage = get_messages(request)
    batch_list_found = False
    try:
        batch_list = BatchDescription.objects.order_by('-batch_header_id')
        if positive_value_exists(google_civic_election_id):
            batch_list = batch_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(kind_of_batch):
            batch_list = batch_list.filter(kind_of_batch__iexact=kind_of_batch)
        if len(batch_list):
            batch_list_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_list = []
        batch_list_found = False
        pass

    if kind_of_batch == ORGANIZATION_WORD or kind_of_batch == ELECTED_OFFICE or kind_of_batch == POLITICIAN:
        # We do not want to ask the person importing the file for an election, because it isn't used
        ask_for_election = False
        election_list = []
    else:
        ask_for_election = True
        election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'batch_list':               batch_list,
        'ask_for_election':         ask_for_election,
        'election_list':            election_list,
        'kind_of_batch':            kind_of_batch,
        'batch_file':               batch_file,
        'batch_uri':                batch_uri,
        'google_civic_election_id': convert_to_int(google_civic_election_id),
        'polling_location_we_vote_id': polling_location_we_vote_id,
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
    if kind_of_batch not in (MEASURE, ELECTED_OFFICE, CONTEST_OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION,
                             POLITICIAN, IMPORT_BALLOT_ITEM):
        messages.add_message(request, messages.ERROR, 'The kind_of_batch is required for a batch import.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
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

    # Make sure we have a file to process
    if kind_of_batch in (ORGANIZATION_WORD, IMPORT_BALLOT_ITEM) and not batch_file:
        messages.add_message(request, messages.ERROR, 'Please select a file to import.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&batch_uri=" + batch_uri_encoded)

    # Make sure we have a Google Civic Election ID *unless* we are uploading an organization
    if kind_of_batch not in ORGANIZATION_WORD and not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'This kind_of_batch (\"{kind_of_batch}\") requires you '
                                                      'to choose an election.'.format(kind_of_batch=kind_of_batch))
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&batch_uri=" + batch_uri_encoded)

    # Make sure we have a polling_location_we_vote_id
    if kind_of_batch in IMPORT_BALLOT_ITEM and not positive_value_exists(polling_location_we_vote_id):
        messages.add_message(request, messages.ERROR, 'This kind_of_batch (\"{kind_of_batch}\") requires you '
                                                      'to choose a polling location.'
                                                      ''.format(kind_of_batch=kind_of_batch))
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&batch_uri=" + batch_uri_encoded)

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
                batch_file, kind_of_batch, google_civic_election_id, organization_we_vote_id)
            if results['batch_saved']:
                messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
                                                             ''.format(election_name=election_name))
                batch_header_id = results['batch_header_id']
            else:
                messages.add_message(request, messages.ERROR, results['status'])
        elif positive_value_exists(batch_uri):
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

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
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
        batch_row_list = BatchRow.objects.order_by('id')
        batch_row_list = batch_row_list.filter(batch_header_id=batch_header_id)
        if len(batch_row_list):
            batch_list_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_row_list = []
        batch_list_found = False

    modified_batch_row_list = []
    batch_manager = BatchManager()
    if batch_list_found:
        for one_batch_row in batch_row_list:
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
            elif kind_of_batch == IMPORT_BALLOT_ITEM:
                existing_results = \
                    batch_manager.retrieve_batch_row_action_ballot_item(batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    one_batch_row.batch_row_action = existing_results['batch_row_action_ballot_item']
                    one_batch_row.kind_of_batch = IMPORT_BALLOT_ITEM
                    one_batch_row.batch_row_action_exists = True
                else:
                    one_batch_row.batch_row_action_exists = False
                modified_batch_row_list.append(one_batch_row)

    election_query = Election.objects.order_by('-election_day_text')
    election_list = list(election_query)
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
        'position_owner_organization_we_vote_id': position_owner_organization_we_vote_id,
    }
    return render(request, 'import_export_batches/batch_action_list.html', template_values)


@login_required
def batch_action_list_analyze_process_view(request):
    """
    Work with the BatchRows and BatchActionXXXs of an existing batch
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    batch_row_id = convert_to_int(request.GET.get('batch_row_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    # if create_actions_button in (MEASURE, ELECTED_OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION, POLITICIAN)
    # Run the analysis of either A) every row in this batch, or B) Just the batch_row_id specified within this batch
    results = create_batch_row_actions(batch_header_id, batch_row_id)
    kind_of_batch = results['kind_of_batch']

    messages.add_message(request, messages.INFO, 'Batch Actions:'
                                                 'Batch kind:{kind_of_batch}, '
                                                 'Created:{created} '
                                                 ''.format(kind_of_batch=kind_of_batch,
                                                           created=results['number_of_batch_actions_created']))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id))


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
    batch_row_list = []

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    batch_row_id = convert_to_int(request.GET.get('batch_row_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')
    kind_of_action = request.GET.get('kind_of_action')
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
            batch_row_list = BatchRow.objects.all()
            batch_row_list = batch_row_list.filter(batch_header_id=batch_header_id)
            if positive_value_exists(batch_row_id):
                batch_row_list = batch_row_list.filter(id=batch_row_id)

            if len(batch_row_list):
                batch_row_list_found = True
        except BatchDescription.DoesNotExist:
            # This is fine
            batch_row_list_found = False
            pass

    if batch_header_map_found and batch_row_list_found:
        results = import_data_from_batch_row_actions(kind_of_batch, kind_of_action, batch_header_id, batch_row_id)

        if kind_of_action == IMPORT_CREATE:
            if results['success']:
                messages.add_message(request, messages.INFO,
                                     'Kind of Batch: {kind_of_batch}, ' 'Number Created: {created} '
                                     ''.format(kind_of_batch=kind_of_batch,
                                               created=results['number_of_table_rows_created']))
            else:
                messages.add_message(request, messages.ERROR, 'Batch kind: {kind_of_batch} create failed: {status}'
                                                              ''.format(kind_of_batch=kind_of_batch,
                                                                        status=results['status']))
        elif kind_of_action == IMPORT_ADD_TO_EXISTING:
            if results['success']:
                messages.add_message(request, messages.INFO,
                                     'Kind of Batch: {kind_of_batch}, ' 'Number Updated: {updated} '
                                     ''.format(kind_of_batch=kind_of_batch,
                                               updated=results['number_of_table_rows_updated']))
            else:
                messages.add_message(request, messages.ERROR, 'Batch kind: {kind_of_batch} update failed--'
                                                              'UPDATE may not be supported yet.'
                                                              ''.format(kind_of_batch=kind_of_batch))
        else:
            messages.add_message(request, messages.ERROR, 'Batch kind: {kind_of_batch} import status: {status}'
                                                          ''.format(kind_of_batch=kind_of_batch,
                                                                    status=results['status']))
            return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id))


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
    batch_uri = request.GET.get('batch_uri', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    batch_set_list_found = False
    try:
        batch_set_list = BatchSet.objects.order_by('-import_date')
        # batch_set_list = batch_set_list.exclude(batch_set_id__isnull=True)
        if positive_value_exists(google_civic_election_id):
            batch_set_list = batch_set_list.filter(google_civic_election_id=google_civic_election_id)
        if len(batch_set_list):
            batch_set_list_found = True
    except BatchSet.DoesNotExist:
        # This is fine
        batch_set_list = BatchSet()
        batch_set_list_found = False
        pass

    election_list = Election.objects.order_by('-election_day_text')

    if batch_set_list_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'batch_set_list':           batch_set_list,
            'election_list':            election_list,
            'batch_uri':                batch_uri,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'election_list':            election_list,
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

    # Store contents of spreadsheet?
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'This batch set requires you '
                                                      'to choose an election.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    "?batch_uri=" + batch_uri_encoded)

    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']

        if positive_value_exists(import_batch_button):  # If the button was pressed...
            batch_manager = BatchManager()

            # check file type
            filetype = batch_manager.find_file_type(batch_uri)
            if "xml" in filetype:
                # file is XML
                # Retrieve the VIP data from XML
                results = batch_manager.create_batch_set_vip_xml(batch_uri, google_civic_election_id,
                                                             organization_we_vote_id)
            else:
                pass
                # results = batch_manager.create_batch(batch_uri, google_civic_election_id, organization_we_vote_id)
            if results['batch_saved']:
                messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
                                                             ''.format(election_name=election.election_name))
            else:
                messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&batch_uri=" + batch_uri_encoded)


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
    number_of_batch_actions_created = 0

    try:
        batch_description = BatchDescription.objects.filter(batch_set_id=batch_set_id)
        batch_description_found = True

        batch_list = list(batch_description)
        # loop through all data sets in this batch
        for one_batch_set_row in batch_list:
            batch_header_id = one_batch_set_row.batch_header_id
            results = create_batch_row_actions(batch_header_id, 0)
            if results['success']:
                # number_of_batch_actions_created += results['number_of_batch_actions_created']
                # status += results['status']
                one_batch_set_row.number_of_batch_actions_created = results['number_of_batch_actions_created']
                pass
            else:
                # rows must be existing in the action table, get the count
                batch_manager = BatchManager()
                kind_of_batch = one_batch_set_row.kind_of_batch
                one_batch_set_row.number_of_batch_actions_created = batch_manager.count_number_of_batch_action_rows(
                    batch_header_id, kind_of_batch)
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    election_list = Election.objects.order_by('-election_day_text')
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'batch_set_id':                     batch_set_id,
        'batch_description':                batch_description,
        'batch_list':                       batch_list,
        'election_list':                    election_list,
        'google_civic_election_id':         google_civic_election_id,
    }
    return render(request, 'import_export_batches/batch_set_batch_list.html', template_values)
