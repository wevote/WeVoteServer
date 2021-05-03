# apis_v1/views/views_election.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
from election.controllers import elections_retrieve_for_api, elections_sync_out_list_for_api
import json
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def elections_retrieve_view(request):  # electionsRetrieve
    """
    :param request:
    :return:
    """

    results = elections_retrieve_for_api()
    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'election_list':        results['election_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def elections_sync_out_view(request):  # electionsSyncOut
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
        election_list_dict = election_list.values(
            'ballotpedia_election_id', 'ballotpedia_kind_of_election', 'candidate_photos_finished', 'ctcl_uuid',
            'election_day_text', 'election_name', 'election_preparation_finished',
            'google_civic_election_id', 'ignore_this_election', 'include_in_list_for_voters', 'internal_notes',
            'is_national_election', 'ocd_division_id', 'state_code', 'use_ballotpedia_as_data_source',
            'use_ctcl_as_data_source', 'use_google_civic_as_data_source', 'use_vote_usa_as_data_source')
        if election_list_dict:
            election_list_json = list(election_list_dict)
            return HttpResponse(json.dumps(election_list_json), content_type='application/json')
        else:
            json_data = {
                'success': False,
                'status': 'ELECTION_LIST_MISSING',
                'voter_device_id': voter_device_id
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')
