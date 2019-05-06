# apis_v1/views/views_candidate.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from measure.controllers import add_measure_name_alternatives_to_measure_list_light, measure_retrieve_for_api, \
    retrieve_measure_list_for_all_upcoming_elections
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def measure_list_for_upcoming_elections_retrieve_api_view(request):  # measureListForUpcomingElectionsRetrieve
    """
    Ask for all measures for the elections in google_civic_election_id_list
    :param request:
    :return:
    """
    status = ""
    google_civic_election_id_list = request.GET.getlist('google_civic_election_id_list[]')
    state_code = request.GET.get('state_code', '')

    # We will need all candidates for all upcoming elections so we can search the HTML of
    #  the possible voter guide for these names
    measure_list_light = []
    results = retrieve_measure_list_for_all_upcoming_elections(google_civic_election_id_list,
                                                               limit_to_this_state_code=state_code)
    if results['measure_list_found']:
        measure_list_light = results['measure_list_light']

        expand_results = add_measure_name_alternatives_to_measure_list_light(measure_list_light)
        if expand_results['success']:
            measure_list_light = expand_results['measure_list_light']

    google_civic_election_id_list = results['google_civic_election_id_list']

    status += results['status']
    success = results['success']

    json_data = {
        'status':                           status,
        'success':                          success,
        'google_civic_election_id_list':    google_civic_election_id_list,
        'measure_list':                   measure_list_light,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def measure_retrieve_view(request):  # measureRetrieve
    measure_id = request.GET.get('measure_id', 0)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', None)
    return measure_retrieve_for_api(measure_id, measure_we_vote_id)
