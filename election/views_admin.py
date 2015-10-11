# election/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Election
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from import_export_google_civic.controllers import retrieve_from_google_civic_api_election_query, \
    store_results_from_google_civic_api_election_query
import wevote_functions.admin
from wevote_functions.models import convert_to_int

logger = wevote_functions.admin.get_logger(__name__)


@login_required()
def election_all_ballots_retrieve_view(request):
    """
    Reach out to Google and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through those polling locations
    :param request:
    :return:
    """
    structured_json = retrieve_from_google_civic_api_all_polling_places_for_one_election()
    results = store_results_from_google_civic_api_all_ballots_query(structured_json)

    messages.add_message(request, messages.INFO, 'Upcoming elections retrieved from Google Civic.')
    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_edit_view(request, election_id):
    messages_on_stage = get_messages(request)
    election_id = convert_to_int(election_id)
    election_on_stage_found = False
    try:
        election_on_stage = Election.objects.get(id=election_id)
        election_on_stage_found = True
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Election.DoesNotExist:
        # This is fine, create new
        pass

    if election_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'election': election_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'election/election_edit.html', template_values)


@login_required()
def election_edit_process_view(request):
    """
    Process the new or edit election forms
    :param request:
    :return:
    """
    election_id = convert_to_int(request.POST['election_id'])
    election_name = request.POST['election_name']

    # Check to see if this election is already being used anywhere
    election_on_stage_found = False
    try:
        election_query = Election.objects.filter(id=election_id)
        if len(election_query):
            election_on_stage = election_query[0]
            election_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if election_on_stage_found:
            # Update
            election_on_stage.election_name = election_name
            election_on_stage.save()
            messages.add_message(request, messages.INFO, 'Election updated.')
        else:
            # Create new
            election_on_stage = Election(
                election_name=election_name,
            )
            election_on_stage.save()
            messages.add_message(request, messages.INFO, 'New election saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save election.')

    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_list_view(request):
    messages_on_stage = get_messages(request)
    election_list = Election.objects.order_by('election_name')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'election_list': election_list,
    }
    return render(request, 'election/election_list.html', template_values)


@login_required()
def election_remote_retrieve_view(request):
    """
    Reach out to Google and retrieve the latest list of available elections
    :param request:
    :return:
    """
    structured_json = retrieve_from_google_civic_api_election_query()
    results = store_results_from_google_civic_api_election_query(structured_json)

    messages.add_message(request, messages.INFO, 'Upcoming elections retrieved from Google Civic.')
    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_summary_view(request, election_id):
    messages_on_stage = get_messages(request)
    election_id = convert_to_int(election_id)
    election_on_stage_found = False
    try:
        election_on_stage = Election.objects.get(id=election_id)
        election_on_stage_found = True
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Election.DoesNotExist:
        # This is fine, create new
        pass

    if election_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'election': election_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'election/election_summary.html', template_values)
