# import_export_vote_smart/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoteSmartCandidate, candidate_object_filter, VoteSmartCandidateBio, candidate_bio_object_filter, \
    VoteSmartOfficial, official_object_filter, VoteSmartState, state_filter
from .votesmart_local import votesmart, VotesmartApiError
from config.base import get_environment_variable
import requests
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
VOTE_SMART_API_URL = get_environment_variable("VOTE_SMART_API_URL")

votesmart.apikey = VOTE_SMART_API_KEY


def get_vote_smart_candidate(last_name):
    try:
        candidates_list = votesmart.candidates.getByLastname(last_name)
        for one_candidate in candidates_list:
            one_candidate_filtered = candidate_object_filter(one_candidate)
            candidate, created = VoteSmartCandidate.objects.update_or_create(
                candidateId=one_candidate.candidateId, defaults=one_candidate_filtered)
            candidate.save()
        status = "VOTE_SMART_CANDIDATES_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def get_vote_smart_candidate_bio(candidate_id):
    try:
        one_candidate_bio = votesmart.candidatebio.getBio(candidate_id)
        candidate_bio_filtered = candidate_bio_object_filter(one_candidate_bio)
        candidate_bio, created = VoteSmartCandidateBio.objects.update_or_create(
            candidateId=one_candidate_bio.candidateId, defaults=candidate_bio_filtered)
        candidate_bio.save()
        status = "VOTE_SMART_CANDIDATE_BIO_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def get_vote_smart_official(last_name):
    try:
        officials_list = votesmart.officials.getByLastname(last_name)
        for one_official in officials_list:
            one_official_filtered = official_object_filter(one_official)
            official, created = VoteSmartOfficial.objects.update_or_create(
                candidateId=one_official.candidateId, defaults=one_official_filtered)
            official.save()
        status = "VOTE_SMART_OFFICIALS_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def _get_state_by_id_as_dict(state_id):
    """Access Vote Smart API and return dictionary representing state."""
    return votesmart.state.getState(state_id).__dict__


def _get_state_names():
    """Access Vote Smart API and return generator of all stateIds."""
    state_ids_dict = votesmart.state.getStateIDs()
    return (state.stateId for state in state_ids_dict)


def retrieve_and_save_vote_smart_states():
    """Load/Update all states into database."""
    state_names_dict = _get_state_names()
    state_count = 0
    for stateId in state_names_dict:
        one_state = _get_state_by_id_as_dict(stateId)
        one_state_filtered = state_filter(one_state)
        state, created = VoteSmartState.objects.get_or_create(**one_state_filtered)
        # state, created = State.objects.get_or_create(**_get_state_by_id_as_dict(stateId))
        state.save()
        if state_count > 3:
            break
        state_count += 1


def get_api_route(cls, method):
    """Return full URI."""
    return "{url}/{cls}.{method}".format(
        url=VOTE_SMART_API_URL,
        cls=cls,
        method=method
    )


def make_request(cls, method, **kwargs):
    kwargs['key'] = VOTE_SMART_API_KEY
    if not kwargs.get('o'):
        kwargs['o'] = "JSON"
    url = get_api_route(cls, method)
    resp = requests.get(url, params=kwargs)
    if resp.status_code == 200:
        return resp.json()
    else:
        return resp.text
