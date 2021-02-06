# google_custom_search/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import delete_possible_google_search_users, retrieve_possible_google_search_users, \
    bulk_possible_google_search_users_do_not_match, possible_google_search_user_do_not_match
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateManager, CandidateCampaign
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from google_custom_search.models import GoogleSearchUser
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists, get_voter_api_device_id
import wevote_functions.admin
from wevote_settings.models import RemoteRequestHistory, RETRIEVE_POSSIBLE_GOOGLE_LINKS

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def delete_possible_google_search_users_view(request, candidate_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id)

    if not results['candidate_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_we_vote_id,)))

    candidate = results['candidate']

    results = delete_possible_google_search_users(candidate)
    messages.add_message(request, messages.INFO, 'Possibilities deleted.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)))


@login_required
def possible_google_search_user_do_not_match_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    item_link = request.GET.get('item_link', '')

    results = possible_google_search_user_do_not_match(candidate_we_vote_id, item_link)
    messages.add_message(request, messages.INFO, 'Candidate possibility updated with no match.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)))


@login_required
def bulk_possible_google_search_users_do_not_match_view(request, candidate_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id)

    if not results['candidate_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_we_vote_id,)))

    candidate = results['candidate']

    results = bulk_possible_google_search_users_do_not_match(candidate)
    messages.add_message(request, messages.INFO, 'Candidate possibilities updated with no match.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)))


@login_required
def retrieve_possible_google_search_users_view(request, candidate_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_device_id = get_voter_api_device_id(request)
    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id)

    if not results['candidate_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_we_vote_id,)))

    candidate = results['candidate']

    results = retrieve_possible_google_search_users(candidate, voter_device_id)
    messages.add_message(request, messages.INFO, 'Number of possibilities found: ' + results['num_of_possibilities'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)))


@login_required
def bulk_retrieve_possible_google_search_users_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_device_id = get_voter_api_device_id(request)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    limit = convert_to_int(request.GET.get('show_all', 0))

    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code) \
            and not positive_value_exists(limit):
        messages.add_message(request, messages.ERROR,
                             'bulk_retrieve_possible_google_search_users_view, LIMITING_VARIABLE_REQUIRED')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    try:
        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            candidate_list = candidate_list.filter(state_code__iexact=state_code)
        candidate_list = candidate_list.order_by('candidate_name')
        if positive_value_exists(limit):
            candidate_list = candidate_list[:limit]
        candidate_list_count = candidate_list.count()

        # Run google search and analysis on candidates without a linked or possible google search
        number_of_candidates_to_search = 20
        current_candidate_index = 0
        while positive_value_exists(number_of_candidates_to_search) \
                and (current_candidate_index < candidate_list_count):
            one_candidate = candidate_list[current_candidate_index]
            if not positive_value_exists(one_candidate.candidate_twitter_handle):
                # Candidate does not have a Twitter account linked - only search for these
                # Check to see if we have already tried to find their information from Twitter. We don't want to
                #  search Twitter more than once.
                request_history_query = RemoteRequestHistory.objects.filter(
                    candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
                    kind_of_action=RETRIEVE_POSSIBLE_GOOGLE_LINKS)
                request_history_list = list(request_history_query)

                if not positive_value_exists(request_history_list):
                    google_search_possibility_list = []
                    try:
                        google_search_possibility_query = GoogleSearchUser.objects.filter(
                            candidate_campaign_we_vote_id=one_candidate.we_vote_id)
                        google_search_possibility_query = google_search_possibility_query.order_by(
                            '-chosen_and_updated', '-likelihood_score')
                        google_search_possibility_list = list(google_search_possibility_query)
                    except Exception as e:
                        pass

                    if not positive_value_exists(google_search_possibility_list):
                        # Google search and analysis has not been run on this candidate yet
                        # (or no results have been found for this candidate, at least)
                        results = retrieve_possible_google_search_users(one_candidate, voter_device_id)
                        number_of_candidates_to_search -= 1
            current_candidate_index += 1
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page))
