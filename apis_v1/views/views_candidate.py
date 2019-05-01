# apis_v1/views/views_candidate.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from candidate.controllers import candidate_retrieve_for_api, candidates_retrieve_for_api, \
    retrieve_candidate_list_for_all_upcoming_elections
from config.base import get_environment_variable
from django.http import HttpResponse
import json
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def candidate_retrieve_view(request):  # candidateRetrieve
    candidate_id = request.GET.get('candidate_id', 0)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', None)
    return candidate_retrieve_for_api(candidate_id, candidate_we_vote_id)


def candidates_retrieve_view(request):  # candidatesRetrieve
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', '')
    return candidates_retrieve_for_api(office_id, office_we_vote_id)


def candidate_list_for_upcoming_elections_retrieve_api_view(request):  # candidateListForUpcomingElectionsRetrieve
    """
    Ask for all candidates running for the elections in google_civic_election_id_list
    :param request:
    :return:
    """
    status = ""
    google_civic_election_id_list = request.GET.getlist('google_civic_election_id_list[]', "")
    state_code = request.GET.get('state_code', '')

    # We will need all candidates for all upcoming elections so we can search the HTML of
    #  the possible voter guide for these names
    candidate_list_light = []
    results = retrieve_candidate_list_for_all_upcoming_elections(google_civic_election_id_list,
                                                                 limit_to_this_state_code=state_code)
    if results['candidate_list_found']:
        candidate_list_light = results['candidate_list_light']

    google_civic_election_id_list = results['google_civic_election_id_list']

    status += results['status']
    success = results['success']

    json_data = {
        'status':                           status,
        'success':                          success,
        'google_civic_election_id_list':    google_civic_election_id_list,
        'candidate_list':                   candidate_list_light,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
