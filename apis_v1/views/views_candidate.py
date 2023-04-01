# apis_v1/views/views_candidate.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from candidate.controllers import candidate_retrieve_for_api, candidates_query_for_api, candidates_retrieve_for_api, \
    retrieve_candidate_list_for_all_upcoming_elections
from candidate.views_admin import candidate_change_names
from politician.views_admin import politician_change_names
from django.contrib.auth.decorators import login_required
from config.base import get_environment_variable
from django.http import HttpResponse
import json
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def candidate_retrieve_view(request):  # candidateRetrieve
    candidate_id = request.GET.get('candidate_id', 0)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', None)
    return candidate_retrieve_for_api(candidate_id, candidate_we_vote_id)


def candidates_query_view(request):  # candidatesQuery
    index_start = convert_to_int(request.GET.get('indexStart', 0))
    number_requested = convert_to_int(request.GET.get('numberRequested', 300))
    election_day = request.GET.get('electionDay', '')
    race_office_level_list = request.GET.getlist('raceOfficeLevel[]', False)
    search_text = request.GET.get('searchText', '')
    use_we_vote_format = positive_value_exists(request.GET.get('useWeVoteFormat', False))
    limit_to_this_state_code = request.GET.get('state', '')
    return candidates_query_for_api(
        index_start=index_start,
        number_requested=number_requested,
        election_day=election_day,
        limit_to_this_state_code=limit_to_this_state_code,
        race_office_level_list=race_office_level_list,
        search_text=search_text,
        use_we_vote_format=use_we_vote_format)


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
    google_civic_election_id_list = request.GET.getlist('google_civic_election_id_list[]')
    state_code = request.GET.get('state_code', '')

    # We will need all candidates for all upcoming elections so we can search the HTML of
    #  the possible voter guide for these names
    candidate_list_light = []
    super_light = True  # limit the response package
    results = retrieve_candidate_list_for_all_upcoming_elections(google_civic_election_id_list,
                                                                 limit_to_this_state_code=state_code,
                                                                 super_light_candidate_list=super_light)
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


@login_required
def candidate_or_politician_repair_names(request):  # candidateOrPoliticianRepairNames
    """
    Change the names of misformatted candidates or politicians
    :param request:
    :return:
    """
    status = ""
    is_candidate = True
    body = request.body.decode('utf-8')
    payload = json.loads(body)
    is_candidate = payload['is_candidate']
    changes = payload['changes']

    if is_candidate:
        return_count = candidate_change_names(changes)
    else:
        return_count = politician_change_names(changes)

    json_data = {
        'count':                            return_count,
        'success':                          return_count > 0,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')

