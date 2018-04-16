# twitter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import delete_possible_twitter_handles, retrieve_possible_twitter_handles
from .models import TwitterLinkPossibility
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign, CandidateCampaignManager
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
import wevote_functions.admin
from wevote_settings.models import RemoteRequestHistory, RETRIEVE_POSSIBLE_TWITTER_HANDLES

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def delete_possible_twitter_handles_view(request, candidate_campaign_we_vote_id):
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

    results = delete_possible_twitter_handles(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Possibilities deleted.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def retrieve_possible_twitter_handles_view(request, candidate_campaign_we_vote_id):
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

    results = retrieve_possible_twitter_handles(candidate_campaign)
    messages.add_message(request, messages.INFO, 'Number of possibilities found: ' + results['num_of_possibilities'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))


@login_required
def bulk_retrieve_possible_twitter_handles_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    limit = convert_to_int(request.GET.get('show_all', 0))

    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code) \
            and not positive_value_exists(limit):
        messages.add_message(request, messages.ERROR,
                             'bulk_retrieve_possible_twitter_handles_view, LIMITING_VARIABLE_REQUIRED')
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

        # Run Twitter account search and analysis on candidates without a linked or possible Twitter account
        number_of_candidates_to_search = 25
        current_candidate_index = 0
        while positive_value_exists(number_of_candidates_to_search) \
                and (current_candidate_index < candidate_list_count):
            one_candidate = candidate_list[current_candidate_index]
            if not positive_value_exists(one_candidate.candidate_twitter_handle):
                # Candidate does not have a Twitter account linked
                # Check to see if we have already tried to find their information from Twitter. We don't want to
                #  search Twitter more than once.
                request_history_query = RemoteRequestHistory.objects.filter(
                    candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
                    kind_of_action=RETRIEVE_POSSIBLE_TWITTER_HANDLES)
                request_history_list = list(request_history_query)

                if not positive_value_exists(request_history_list):
                    # Twitter account search and analysis has not been run on this candidate yet
                    results = retrieve_possible_twitter_handles(one_candidate)
                    number_of_candidates_to_search -= 1

            current_candidate_index += 1
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )
