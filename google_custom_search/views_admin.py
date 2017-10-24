# google_custom_search/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import delete_possible_google_search_users, retrieve_possible_google_search_users
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaignManager
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from voter.models import voter_has_authority
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
