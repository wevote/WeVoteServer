# import_export_ballotpedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_candidates_from_api, retrieve_districts_to_which_address_belongs_from_api
from candidate.models import CandidateCampaignManager
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from exception.models import handle_record_not_saved_exception
from import_export_batches.models import BatchManager, \
    CANDIDATE, CONTEST_OFFICE, ELECTED_OFFICE, IMPORT_BALLOT_ITEM, MEASURE
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def import_ballot_items_for_location_view(request):
    """
    Reach out to Ballotpedia API to retrieve a short list of districts the voter can vote in.
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', "")

    results = retrieve_districts_to_which_address_belongs_from_api(
        google_civic_election_id, polling_location_we_vote_id)

    kind_of_batch = ""
    if 'kind_of_batch' in results:
        kind_of_batch = results['kind_of_batch']
    if not positive_value_exists(kind_of_batch):
        kind_of_batch = IMPORT_BALLOT_ITEM

    batch_header_id = 0
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
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    if positive_value_exists(batch_header_id):
        # Go straight to the new batch
        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    "?batch_header_id=" + str(batch_header_id) +
                                    "&kind_of_batch=" + str(kind_of_batch) +
                                    "&google_civic_election_id=" + str(google_civic_election_id))
    else:
        # Go to the ballot_item_list_edit page
        return HttpResponseRedirect(reverse('ballot:ballot_item_list_by_polling_location_edit',
                                            args=(polling_location_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                    "&state_code=" + str(state_code)
                                    )


def import_export_ballotpedia_index_view(request):
    """
    Provide an index of import/export actions (for We Vote data maintenance)
    """
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':    messages_on_stage,
    }
    return render(request, 'import_export_ballotpedia/index.html', template_values)


def retrieve_candidates_from_api_view(request):
    """
    Reach out to Ballotpedia API to retrieve candidates.
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    zero_entries = request.GET.get('zero_entries', True)

    results = retrieve_candidates_from_api(google_civic_election_id, zero_entries)

    kind_of_batch = ""
    if 'kind_of_batch' in results:
        kind_of_batch = results['kind_of_batch']
    if not positive_value_exists(kind_of_batch):
        kind_of_batch = CANDIDATE

    batch_header_id = 0
    if 'batch_saved' in results and results['batch_saved']:
        messages.add_message(request, messages.INFO, 'Import batch for {google_civic_election_id} election saved.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    elif 'batch_header_id' in results and results['batch_header_id']:
        messages.add_message(request, messages.INFO, 'Import batch for {google_civic_election_id} election saved, '
                                                     'batch_header_id.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    if positive_value_exists(batch_header_id):
        # Go straight to the new batch
        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    "?batch_header_id=" + str(batch_header_id) +
                                    "&kind_of_batch=" + str(kind_of_batch) +
                                    "&google_civic_election_id=" + str(google_civic_election_id))
    else:
        # Go to the office listing page
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))
