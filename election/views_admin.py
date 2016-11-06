# election/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import election_remote_retrieve, elections_import_from_master_server, elections_sync_out_list_for_api
from .models import Election
from .serializers import ElectionSerializer
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager, BallotReturnedManager
from candidate.models import CandidateCampaignListManager
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import ElectionManager
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from import_export_google_civic.controllers import retrieve_one_ballot_from_google_civic_api, \
    store_one_ballot_from_google_civic_api
import json
from office.models import ContestOfficeListManager
from polling_location.models import PollingLocation
from position.models import PositionListManager
from rest_framework.views import APIView
from rest_framework.response import Response
import time
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, positive_value_exists, STATE_CODE_MAP
from wevote_settings.models import fetch_next_we_vote_election_id_integer

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

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

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
    if not positive_value_exists(state_code):
        state_code = election_on_stage.get_election_state()
        if not positive_value_exists(state_code):
            state_code = "CA"  # TODO DALE Temp for 2016

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count = polling_location_count_query.count()

        polling_location_list = PollingLocation.objects.all()
        polling_location_list = polling_location_list.filter(state__iexact=state_code)
        # We used to have a limit of 500 ballots to pull per election, but now retrieve all
        # Ordering by "location_name" creates a bit of (locational) random order
        polling_location_list = polling_location_list.order_by('location_name')  # [:500]  For testing smaller batches
    except PollingLocation.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations returned for the state \'{state}\'. (error 2)'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    ballots_retrieved = 0
    ballots_not_retrieved = 0
    ballots_with_contests_retrieved = 0
    # We used to only retrieve up to 500 locations from each state, but we don't limit now
    # # We retrieve 10% of the total polling locations, which should give us coverage of the entire election
    # number_of_polling_locations_to_retrieve = int(.1 * polling_location_count)
    ballot_returned_manager = BallotReturnedManager()
    rate_limit_count = 0
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
                # NOTE: We don't support retrieving ballots for polling locations AND geocoding simultaneously
                # if store_one_ballot_results['ballot_returned_found']:
                #     ballot_returned = store_one_ballot_results['ballot_returned']
                #     ballot_returned_results = \
                #         ballot_returned_manager.populate_latitude_and_longitude_for_ballot_returned(ballot_returned)
                #     if ballot_returned_results['success']:
                #         rate_limit_count += 1
                #         if rate_limit_count >= 10:  # Avoid problems with the geocoder rate limiting
                #             time.sleep(1)
                #             # After pause, reset the limit count
                #             rate_limit_count = 0

        if success:
            ballots_retrieved += 1
        else:
            ballots_not_retrieved += 1

        if one_ballot_results['contests_retrieved']:
            ballots_with_contests_retrieved += 1

        # We used to only retrieve up to 500 locations from each state, but we don't limit now
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

    if positive_value_exists(election_local_id):
        try:
            election_on_stage = Election.objects.get(id=election_local_id)
            election_on_stage_found = True
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except Election.DoesNotExist:
            # This is fine, create new
            pass
    else:
        # If here we are creating a
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

    election_local_id = convert_to_int(request.POST.get('election_local_id', 0))
    election_name = request.POST.get('election_name', False)
    election_day_text = request.POST.get('election_day_text', False)
    state_code = request.POST.get('state_code', False)

    election_on_stage = Election()
    election_changed = False

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
            if convert_to_int(election_on_stage.google_civic_election_id) < 1000000:
                # If here, this is an election created by Google Civic and we limit what fields to update
                # Update
                if state_code is not False:
                    election_on_stage.state_code = state_code
                    election_changed = True

                if election_changed:
                    election_on_stage.save()
                    messages.add_message(request, messages.INFO, 'Google Civic-created election updated.')
            else:
                # If here, this is a We Vote created election
                # Update
                if election_name is not False:
                    election_on_stage.election_name = election_name
                    election_changed = True

                if election_day_text is not False:
                    election_on_stage.election_day_text = election_day_text
                    election_changed = True

                if state_code is not False:
                    election_on_stage.state_code = state_code
                    election_changed = True

                if election_changed:
                    election_on_stage.save()
                    messages.add_message(request, messages.INFO, 'We Vote-created election updated.')
        else:
            # Create new
            next_local_election_id_integer = fetch_next_we_vote_election_id_integer()

            election_on_stage = Election(
                google_civic_election_id=next_local_election_id_integer,
                election_name=election_name,
                election_day_text=election_day_text,
                state_code=state_code,
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

    election_local_id = convert_to_int(election_local_id)
    election_on_stage_found = False
    election_on_stage = Election()

    try:
        election_on_stage = Election.objects.get(id=election_local_id)
        election_on_stage_found = True
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Election.DoesNotExist:
        # This is fine, proceed anyways
        pass

    state_code = request.GET.get('state_code', '')
    status_print_list = ""
    ballot_returned_count = 0
    ballot_returned_list_manager = BallotReturnedListManager()

    state_list = STATE_CODE_MAP
    state_list_modified = {}
    for one_state_code, one_state_name in state_list.items():
        ballot_returned_count = ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
            election_on_stage.google_civic_election_id, one_state_code)

        state_name_modified = one_state_name
        if positive_value_exists(ballot_returned_count):
            state_name_modified += " - " + str(ballot_returned_count)
        state_list_modified[one_state_code] = state_name_modified

    sorted_state_list = sorted(state_list_modified.items())

    if election_on_stage_found:
        ballot_returned_list_results = ballot_returned_list_manager.retrieve_ballot_returned_list_for_election(
            election_on_stage.google_civic_election_id, state_code)

        if ballot_returned_list_results['success']:
            ballot_returned_list = ballot_returned_list_results['ballot_returned_list']
            ballot_returned_count = len(ballot_returned_list)
            if not positive_value_exists(state_code):
                ballot_returned_list = ballot_returned_list[:1000]
        else:
            ballot_returned_list = []

        status_print_list += "ballot_returned_count: " + str(ballot_returned_count) + "<br />"
        messages.add_message(request, messages.INFO, status_print_list)
        messages_on_stage = get_messages(request)

        template_values = {
            'ballot_returned_list': ballot_returned_list,
            'election':             election_on_stage,
            'messages_on_stage':    messages_on_stage,
            'state_code':           state_code,
            'state_list':           sorted_state_list,
        }
    else:
        messages_on_stage = get_messages(request)

        template_values = {
            'messages_on_stage':    messages_on_stage,
            'state_code':           state_code,
            'state_list':           sorted_state_list,
        }
    return render(request, 'election/election_summary.html', template_values)


# TODO Which of these two do we standardize on?
class ElectionsSyncOutView(APIView):
    """
    Export raw voter data to JSON format
    """
    def get(self, request):  # Removed: , format=None
        voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
        results = elections_sync_out_list_for_api(voter_device_id)

        if 'success' not in results:
            json_data = results['json_data']
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        elif not results['success']:
            json_data = results['json_data']
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        else:
            election_list = results['election_list']
            serializer = ElectionSerializer(election_list, many=True)
            return Response(serializer.data)


# This page does not need to be protected.
class ExportElectionDataView(APIView):
    def get(self, request, format=None):
        election_list = Election.objects.all()
        serializer = ElectionSerializer(election_list, many=True)
        return Response(serializer.data)


@login_required
def elections_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = elections_import_from_master_server()

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Elections import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required()
def election_migration_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_manager = ElectionManager()
    we_vote_election = Election()
    office_list_manager = ContestOfficeListManager()
    candidate_list_manager = CandidateCampaignListManager()
    position_list_manager = PositionListManager()
    we_vote_election_office_list = []
    google_civic_election_office_list = []

    results = election_manager.retrieve_we_vote_elections()
    we_vote_election_list = results['election_list']
    state_code_list = []
    for election in we_vote_election_list:
        if election.state_code not in state_code_list:
            state_code_list.append(election.state_code)

    google_civic_election = Election()
    results = election_manager.retrieve_google_civic_elections_in_state_list(state_code_list)
    google_civic_election_list = results['election_list']

    we_vote_election_id = convert_to_int(request.GET.get('we_vote_election_id', 0))
    if not positive_value_exists(we_vote_election_id):
        we_vote_election_id = convert_to_int(request.POST.get('we_vote_election_id', 0))
    if positive_value_exists(we_vote_election_id):
        results = election_manager.retrieve_election(we_vote_election_id)
        if results['election_found']:
            we_vote_election = results['election']

            return_list_of_objects = True
            results = office_list_manager.retrieve_all_offices_for_upcoming_election(we_vote_election_id,
                                                                                     return_list_of_objects)
            if results['office_list_found']:
                we_vote_election_office_list = results['office_list_objects']

    # Go through each office and attach a list of candidates under this office
    we_vote_election_office_list_new = []
    for one_office in we_vote_election_office_list:
        candidate_results = candidate_list_manager.retrieve_all_candidates_for_office(0, one_office.we_vote_id)
        if candidate_results['candidate_list_found']:
            candidate_list = candidate_results['candidate_list']
            new_candidate_list = []
            # Go through candidate_list and find the number of positions saved for each candidate
            for candidate in candidate_list:
                retrieve_public_positions = True  # The alternate is positions for friends-only
                position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                    retrieve_public_positions, 0, candidate.we_vote_id)
                candidate.position_count = len(position_list)  # This is wasteful (instead of using count), but ok

                # Now find the candidates from the Google Civic Election that we might want to transfer data to

                new_candidate_list.append(candidate)

            one_office.candidate_list = new_candidate_list
        else:
            one_office.candidate_list = []
        we_vote_election_office_list_new.append(one_office)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    if not positive_value_exists(google_civic_election_id):
        google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    if positive_value_exists(google_civic_election_id):
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            google_civic_election = results['election']

            return_list_of_objects = True
            results = office_list_manager.retrieve_all_offices_for_upcoming_election(google_civic_election_id,
                                                                                     return_list_of_objects)
            if results['office_list_found']:
                google_civic_election_office_list = results['office_list_objects']

    # We want to transfer the
    transfer_array = {}
    transfer_array['wv01off1461'] = "wv02off269"

    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'we_vote_election':                     we_vote_election,
        'we_vote_election_id':                  we_vote_election_id,
        'we_vote_election_list':                we_vote_election_list,
        'we_vote_election_office_list':         we_vote_election_office_list_new,
        'google_civic_election':                google_civic_election,
        'google_civic_election_id':             google_civic_election_id,
        'google_civic_election_list':           google_civic_election_list,
        'google_civic_election_office_list':    google_civic_election_office_list,
    }

    return render(request, 'election/election_migration.html', template_values)
