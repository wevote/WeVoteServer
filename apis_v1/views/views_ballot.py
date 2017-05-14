# apis_v1/views/views_ballot.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from ballot.controllers import ballot_item_options_retrieve_for_api
from candidate.controllers import candidate_retrieve_for_api
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from measure.controllers import measure_retrieve_for_api
from office.controllers import office_retrieve_for_api
from ballot.models import OFFICE, CANDIDATE, MEASURE
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def ballot_item_options_retrieve_view(request):  # ballotItemOptionsRetrieve
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    results = ballot_item_options_retrieve_for_api(google_civic_election_id, state_code)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')
    return response


def ballot_item_retrieve_view(request):  # ballotItemRetrieve
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', '')
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)

    if not positive_value_exists(kind_of_ballot_item) or kind_of_ballot_item not in(OFFICE, CANDIDATE, MEASURE):
        status = 'VALID_BALLOT_ITEM_TYPE_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':         kind_of_ballot_item,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if kind_of_ballot_item == OFFICE:
        return office_retrieve_for_api(ballot_item_id, ballot_item_we_vote_id)
    elif kind_of_ballot_item == CANDIDATE:
        return candidate_retrieve_for_api(ballot_item_id, ballot_item_we_vote_id)
    elif kind_of_ballot_item == MEASURE:
        return measure_retrieve_for_api(ballot_item_id, ballot_item_we_vote_id)
    else:
        status = 'BALLOT_ITEM_RETRIEVE_UNKNOWN_ERROR'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
