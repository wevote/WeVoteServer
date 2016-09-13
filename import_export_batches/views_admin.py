# import_export_batches/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BatchDescription, BatchHeaderMap, BatchManager, BatchRow
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import MEASURE, OFFICE, CANDIDATE
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
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP

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
    batch_uri = request.GET.get('batch_uri', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    batch_list_found = False
    try:
        batch_list = BatchDescription.objects.order_by('-google_civic_election_id')
        if positive_value_exists(google_civic_election_id):
            batch_list = batch_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(kind_of_batch):
            batch_list = batch_list.filter(kind_of_batch__iexact=kind_of_batch)
        if len(batch_list):
            batch_list_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_list = BatchDescription()
        batch_list_found = False
        pass

    election_list = Election.objects.order_by('-election_day_text')

    if batch_list_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'batch_list':               batch_list,
            'election_list':            election_list,
            'kind_of_batch':            kind_of_batch,
            'batch_uri':                batch_uri,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'election_list':            election_list,
            'kind_of_batch':            kind_of_batch,
            'batch_uri':                batch_uri,
            'google_civic_election_id': google_civic_election_id,
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
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    organization_we_vote_id = request.POST.get('organization_we_vote_id', '')
    # Was form submitted, or was election just changed?
    import_batch_button = request.POST.get('import_batch_button', '')

    batch_uri_encoded = urlquote(batch_uri) if positive_value_exists(batch_uri) else ""

    if kind_of_batch not in (MEASURE, OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION):
        messages.add_message(request, messages.ERROR, 'The kind_of_batch is required for a batch import.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&batch_uri=" + batch_uri_encoded)

    # Store contents of spreadsheet?
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'This kind_of_batch (\"{kind_of_batch}\") requires you '
                                                      'to choose an election.'.format(kind_of_batch=kind_of_batch))
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch) +
                                    "&batch_uri=" + batch_uri_encoded)

    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']

        if positive_value_exists(import_batch_button):  # If the button was pressed...
            batch_manager = BatchManager()
            results = batch_manager.create_batch(batch_uri, kind_of_batch, google_civic_election_id,
                                                 organization_we_vote_id)
            if results['batch_saved']:
                messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
                                                             ''.format(election_name=election.election_name))
            else:
                messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
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

    batch_header_id = convert_to_int(request.GET.get('batch_header_id', 0))
    kind_of_batch = request.GET.get('kind_of_batch', '')

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

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
        pass

    modified_batch_row_list = []
    batch_manager = BatchManager()
    if batch_list_found:
        for one_batch_row in batch_row_list:
            existing_results = batch_manager.retrieve_batch_row_action_organization(batch_header_id, one_batch_row.id)
            if existing_results['batch_row_action_found']:
                one_batch_row.batch_row_action = existing_results['batch_row_action_organization']
                one_batch_row.kind_of_batch = ORGANIZATION_WORD
                one_batch_row.batch_row_action_exists = True
            else:
                one_batch_row.batch_row_action_exists = False
            modified_batch_row_list.append(one_batch_row)

    election_list = Election.objects.order_by('-election_day_text')
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'batch_header_id':          batch_header_id,
        'batch_description':        batch_description,
        'batch_header_map':         batch_header_map,
        'batch_row_list':           modified_batch_row_list,
        'election_list':            election_list,
        'kind_of_batch':            kind_of_batch,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'import_export_batches/batch_action_list.html', template_values)


@login_required
def batch_action_list_process_view(request):
    """
    Work with the BatchRows and BatchActionXXXs of an existing batch
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    batch_header_id = convert_to_int(request.POST.get('batch_header_id', 0))
    kind_of_batch = request.POST.get('kind_of_batch', '')
    create_actions_button = request.POST.get('create_actions_button', '')

    if create_actions_button in (MEASURE, OFFICE, CANDIDATE, ORGANIZATION_WORD, POSITION):
        # Analyze the data based on the kind of data
        batch_manager = BatchManager()
        results = batch_manager.create_batch_row_actions(batch_header_id)
        if results['batch_actions_created']:
            pass

    if not positive_value_exists(batch_header_id):
        messages.add_message(request, messages.ERROR, 'Batch_header_id required.')
        return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                    "?kind_of_batch=" + str(kind_of_batch))

    return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                "?kind_of_batch=" + str(kind_of_batch) +
                                "&batch_header_id=" + str(batch_header_id))
