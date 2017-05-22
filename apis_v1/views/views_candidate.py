# apis_v1/views/views_candidate.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from candidate.controllers import candidate_retrieve_for_api, candidates_retrieve_for_api
from config.base import get_environment_variable
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
