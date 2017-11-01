# google_custom_search/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import delete_possible_google_search_users, retrieve_possible_google_search_users, \
    bulk_possible_google_search_users_do_not_match, possible_google_search_user_do_not_match
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaignManager, CandidateCampaign
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from google_custom_search.models import GoogleSearchUser
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def delete_possible_google_search_users_view(request, candidate_campaign_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_campaign_we_vote_id)

    if not results['candidate_campaign_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_campaign_we_vote_id,)))

    candidate_campaign = results['candidate_campaign']

    results = delete_possible_google_search_users(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Possibilities deleted.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def possible_google_search_user_do_not_match_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_campaign_we_vote_id = request.GET.get('candidate_we_vote_id', '')
    item_link = request.GET.get('item_link', '')

    results = possible_google_search_user_do_not_match(candidate_campaign_we_vote_id, item_link)
    messages.add_message(request, messages.INFO, 'Candidate possibility updated with no match.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def bulk_possible_google_search_users_do_not_match_view(request, candidate_campaign_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_campaign_we_vote_id)

    if not results['candidate_campaign_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_campaign_we_vote_id,)))

    candidate_campaign = results['candidate_campaign']

    results = bulk_possible_google_search_users_do_not_match(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Candidate possibilities updated with no match.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def retrieve_possible_google_search_users_view(request, candidate_campaign_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_campaign_we_vote_id)

    if not results['candidate_campaign_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_campaign_we_vote_id,)))

    candidate_campaign = results['candidate_campaign']

    results = retrieve_possible_google_search_users(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Number of possibilities found: ' + results['num_of_possibilities'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def bulk_retrieve_possible_google_search_users_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)

    try:
        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            candidate_list = candidate_list.filter(state_code__iexact=state_code)
        candidate_list = candidate_list.order_by('candidate_name')
        if not positive_value_exists(show_all):
            candidate_list = candidate_list[:200]
        candidate_list_count = candidate_list.count()

        # Run google search and analysis on candidates without a linked or possible google search
        number_of_candidates_to_search = 20
        current_candidate_index = 0
        while positive_value_exists(number_of_candidates_to_search) \
                and (current_candidate_index < candidate_list_count):
            one_candidate = candidate_list[current_candidate_index]
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
                results = retrieve_possible_google_search_users(one_candidate)
                number_of_candidates_to_search -= 1
            current_candidate_index += 1
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code))
