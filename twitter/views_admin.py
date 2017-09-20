# twitter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_possible_twitter_handles
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaignManager
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from voter.models import voter_has_authority, VoterManager
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


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

    # TODO Uncomment this and work within here
    results = retrieve_possible_twitter_handles(candidate_campaign)
    number_of_possibilities_found = 0
    messages.add_message(request, messages.INFO, 'Number of possibilities found: ' + str(number_of_possibilities_found))

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_campaign_we_vote_id,)))

