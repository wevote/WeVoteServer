# election/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import election_remote_retrieve
from .models import Election
from .serializers import ElectionSerializer
from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from import_export_google_civic.controllers import retrieve_one_ballot_from_google_civic_api, \
    store_one_ballot_from_google_civic_api
from polling_location.models import PollingLocation
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def election_all_ballots_retrieve_view(request, election_local_id=0):
    """
    Reach out to Google and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those polling locations, enough that we are caching all of the possible ballot items
    :param request:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    try:
        if positive_value_exists(election_local_id):
            election_on_stage = Election.objects.get(id=election_local_id)
        else:
            election_on_stage = Election.objects.get(google_civic_election_id=google_civic_election_id)
            election_local_id = election_on_stage.id
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    state = election_on_stage.get_election_state()
    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state)
        polling_location_count = polling_location_count_query.count()

        polling_location_list = PollingLocation.objects.all()
        polling_location_list = polling_location_list.filter(state__iexact=state)
        # Include a limit of 500 ballots to pull per election
        # Ordering by "location_name" creates a bit of (locational) random order
        polling_location_list = polling_location_list.order_by('location_name')[:500]
    except PollingLocation.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations returned for the state \'{state}\'. (error 2)'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    ballots_retrieved = 0
    ballots_not_retrieved = 0
    ballots_with_contests_retrieved = 0
    # DEPRECATED: We now retrieve up to 500 locations from each state
    # # We retrieve 10% of the total polling locations, which should give us coverage of the entire election
    # number_of_polling_locations_to_retrieve = int(.1 * polling_location_count)
    for polling_location in polling_location_list:
        success = False
        # Get the address for this polling place, and then retrieve the ballot from Google Civic API
        text_for_map_search = polling_location.get_text_for_map_search()
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(
            text_for_map_search, election_on_stage.google_civic_election_id)
        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']
            store_one_ballot_results = store_one_ballot_from_google_civic_api(one_ballot_json, 0,
                                                                              polling_location.we_vote_id)
            if store_one_ballot_results['success']:
                success = True

        if success:
            ballots_retrieved += 1
        else:
            ballots_not_retrieved += 1

        if one_ballot_results['contests_retrieved']:
            ballots_with_contests_retrieved += 1

        # # DEPRECATED: We now retrieve up to 500 locations from each state
        # # Break out of this loop, assuming we have a minimum number of ballots with contests retrieved
        # #  If we don't achieve the minimum number of ballots_with_contests_retrieved, break out at the emergency level
        # emergency = (ballots_retrieved + ballots_not_retrieved) >= (3 * number_of_polling_locations_to_retrieve)
        # if ((ballots_retrieved + ballots_not_retrieved) >= number_of_polling_locations_to_retrieve and
        #         ballots_with_contests_retrieved > 20) or emergency:
        #     break

    if ballots_retrieved > 0:
        total_retrieved = ballots_retrieved + ballots_not_retrieved
        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Google Civic for the {election_name}. '
                             '(ballots retrieved: {ballots_retrieved} '
                             '(with contests: {ballots_with_contests_retrieved}), '
                             'not retrieved: {ballots_not_retrieved}, '
                             'total: {total})'.format(
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 ballots_with_contests_retrieved=ballots_with_contests_retrieved,
                                 election_name=election_on_stage.election_name,
                                 total=total_retrieved))
    else:
        messages.add_message(request, messages.ERROR,
                             'Ballot data NOT retrieved from Google Civic for the {election_name}.'
                             ' (not retrieved: {ballots_not_retrieved})'.format(
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 election_name=election_on_stage.election_name))
    return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))


@login_required
def election_edit_view(request, election_local_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_local_id = convert_to_int(election_local_id)
    election_on_stage_found = False
    election_on_stage = Election()

    try:
        election_on_stage = Election.objects.get(id=election_local_id)
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
    return render(request, "election/election_edit.html", template_values)


@login_required()
def election_edit_process_view(request):
    """
    Process the new or edit election forms
    :param request:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    election_local_id = convert_to_int(request.POST['election_local_id'])
    election_name = request.POST['election_name']
    election_on_stage = Election()

    # Check to see if this election is already being used anywhere
    election_on_stage_found = False
    try:
        election_query = Election.objects.filter(id=election_local_id)
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
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_list_query = Election.objects.all()
    election_list_query = election_list_query.order_by('election_day_text').reverse()
    election_list = election_list_query

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
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    results = election_remote_retrieve()

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Upcoming elections retrieved from Google Civic.')
    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_summary_view(request, election_local_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_local_id = convert_to_int(election_local_id)
    election_on_stage_found = False
    election_on_stage = Election()

    try:
        election_on_stage = Election.objects.get(id=election_local_id)
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


# This page does not need to be protected.
class ExportElectionDataView(APIView):
    def get(self, request, format=None):
        election_list = Election.objects.all()
        serializer = ElectionSerializer(election_list, many=True)
        return Response(serializer.data)
