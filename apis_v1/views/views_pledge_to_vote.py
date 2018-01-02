# apis_v1/views/views_pledge_to_vote.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from django.http import HttpResponse
import json
from pledge_to_vote.controllers import pledge_to_vote_with_voter_guide_for_api
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def pledge_to_vote_with_voter_guide_view(request):  # pledgeToVoteWithVoterGuide
    status = ""
    success = False
    missing_required_variable = False

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_we_vote_id = request.GET.get('voter_guide_we_vote_id', '')
    delete_pledge = request.GET.get('ballot_item_we_vote_id', False)

    if not positive_value_exists(voter_guide_we_vote_id):
        status += "MISSING_VOTER_GUIDE_WE_VOTE_ID "
        success = False
        missing_required_variable = True

    if missing_required_variable:
        json_data = {
            'status':                   status,
            'success':                  success,
            'delete_pledge':            delete_pledge,
            'google_civic_election_id': 0,
            'organization_we_vote_id':  "",
            'pledge_statistics_found':  False,
            'pledge_goal':              0,
            'pledge_count':             0,
            'voter_has_pledged':        False,
            'voter_device_id': voter_device_id,
            'voter_guide_we_vote_id': voter_guide_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    pledge_results = pledge_to_vote_with_voter_guide_for_api(voter_device_id, voter_guide_we_vote_id, delete_pledge)

    status += pledge_results['status']
    json_data = {
        'status':                   status,
        'success':                  pledge_results['success'],
        'delete_pledge':            delete_pledge,
        'google_civic_election_id': pledge_results['google_civic_election_id'],
        'organization_we_vote_id':  pledge_results['organization_we_vote_id'],
        'pledge_statistics_found':  pledge_results['pledge_statistics_found'],
        'pledge_goal':              pledge_results['pledge_goal'],
        'pledge_count':             pledge_results['pledge_count'],
        'voter_has_pledged':        pledge_results['voter_has_pledged'],
        'voter_device_id':          voter_device_id,
        'voter_guide_we_vote_id':   voter_guide_we_vote_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
