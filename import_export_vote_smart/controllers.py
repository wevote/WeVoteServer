# import_export_vote_smart/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoteSmartCandidate, VoteSmartCandidateManager, candidate_object_filter, VoteSmartCandidateBio, \
    candidate_bio_object_filter, VoteSmartOfficial, VoteSmartOfficialManager, official_object_filter, \
    VoteSmartState, state_filter
from .votesmart_local import votesmart, VotesmartApiError
from config.base import get_environment_variable
import requests
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
VOTE_SMART_API_URL = get_environment_variable("VOTE_SMART_API_URL")

votesmart.apikey = VOTE_SMART_API_KEY


def retrieve_and_match_candidate_from_vote_smart(we_vote_candidate, force_retrieve=False):
    status = ""
    # Has this candidate already been linked to a Vote Smart candidate?
    if positive_value_exists(we_vote_candidate.vote_smart_id) and not force_retrieve:
        vote_smart_candidate_id = we_vote_candidate.vote_smart_id
        status += 'VOTE_SMART_CANDIDATE_ID_PREVIOUSLY_RETRIEVED '
        results = {
            'success':                  True,
            'status':                   status,
            'message_type':             'INFO',
            'message':                  'Vote Smart candidate id already retrieved previously.',
            'we_vote_candidate_id':     we_vote_candidate.id,
            'we_vote_candidate':        we_vote_candidate,
            'vote_smart_candidate_id':  vote_smart_candidate_id,
        }
        return results

    first_name = we_vote_candidate.extract_first_name()
    last_name = we_vote_candidate.extract_last_name()

    # Fill the VoteSmartCandidate table with politicians that might match this candidate
    candidate_results = retrieve_vote_smart_candidates_into_local_db(last_name)
    if not candidate_results['success']:
        status += 'VOTE_SMART_CANDIDATES_NOT_RETRIEVED_TO_LOCAL_DB: '
        status += candidate_results['status']
    else:
        # Now look through those Vote Smart candidates and match them
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate_from_name_components(
            first_name, last_name, we_vote_candidate.state_code)
        if results['vote_smart_candidate_found']:
            status += 'VOTE_SMART_CANDIDATE_MATCHED '
            vote_smart_candidate = results['vote_smart_candidate']
            vote_smart_candidate_id = convert_to_int(vote_smart_candidate.candidateId)
            we_vote_candidate.vote_smart_id = vote_smart_candidate_id
            we_vote_candidate.save()
            # messages.add_message(request, messages.INFO,
            #                      "Vote Smart Candidate db entry found for '{first_name} {last_name}'.".format(
            #                          first_name=first_name, last_name=last_name))
            # If here, we were able to match this candidate from the We Vote database to a candidate
            # from the Vote Smart database with this last name
            results = {
                'success':                  True,
                'status':                   status,
                'message_type':             'INFO',
                'message':                  candidate_results['status'],
                'we_vote_candidate_id':     we_vote_candidate.id,
                'we_vote_candidate':        we_vote_candidate,
                'vote_smart_candidate_id':  vote_smart_candidate_id,
            }
            return results
        else:
            # If here, we were NOT able to find any possible candidates from the Vote Smart database,
            # but we still will look in the Vote Smart Officials table below
            status += 'MATCHING_CANDIDATE_NOT_FOUND_FROM_VOTE_SMART_OPTIONS (first_name: {first_name}, ' \
                      'last_name: {last_name}) '.format(first_name=first_name, last_name=last_name)

    # If we didn't find a person from the Vote Smart candidate search, look through Vote Smart officials

    # Fill the VoteSmartOfficial table with politicians that might match this candidate
    officials_results = retrieve_vote_smart_officials_into_local_db(last_name)
    if not officials_results['success']:
        success = False
        vote_smart_candidate_id = 0
        status += 'VOTE_SMART_OFFICIALS_NOT_RETRIEVED_TO_LOCAL_DB: '
        status += officials_results['status']
    else:
        vote_smart_official_manager = VoteSmartOfficialManager()
        results = vote_smart_official_manager.retrieve_vote_smart_official_from_name_components(
            first_name, last_name, we_vote_candidate.state_code)
        if results['vote_smart_official_found']:
            vote_smart_official = results['vote_smart_official']
            vote_smart_candidate_id = convert_to_int(vote_smart_official.candidateId)
            we_vote_candidate.vote_smart_id = vote_smart_candidate_id
            we_vote_candidate.save()
            success = True
            status += 'VOTE_SMART_OFFICIAL_MATCHED '
        else:
            vote_smart_candidate_id = 0
            success = False
            status += 'MATCHING_OFFICIAL_NOT_FOUND_FROM_VOTE_SMART_OPTIONS (first_name: {first_name}, ' \
                      'last_name: {last_name}) '.format(first_name=first_name, last_name=last_name)

    results = {
        'success':                  success,
        'status':                   status,
        'message_type':             'INFO',
        'message':                  candidate_results['status'],
        'we_vote_candidate_id':     we_vote_candidate.id,
        'vote_smart_candidate_id':  vote_smart_candidate_id,
        'we_vote_candidate':        we_vote_candidate,
    }
    return results


def retrieve_candidate_photo_from_vote_smart(we_vote_candidate, force_retrieve=False):
    status = ""
    vote_smart_candidate_id = we_vote_candidate.vote_smart_id
    # Has this candidate been linked to a Vote Smart candidate? If not, error out
    if not positive_value_exists(vote_smart_candidate_id):
        status += 'VOTE_SMART_CANDIDATE_ID_REQUIRED '
        results = {
            'success':                  False,
            'status':                   status,
            'message_type':             'INFO',
            'message':                  'Vote Smart candidate id needs to be retrieved before the photo '
                                        'can be retrieved.',
            'we_vote_candidate_id':     we_vote_candidate.id,
            'vote_smart_candidate_id':  vote_smart_candidate_id,
        }
        return results

    # Have we already retrieved a Vote Smart photo?
    if positive_value_exists(we_vote_candidate.photo_url_from_vote_smart) and not force_retrieve:
        status += 'VOTE_SMART_CANDIDATE_ID_PREVIOUSLY_RETRIEVED '
        results = {
            'success':                      True,
            'status':                       status,
            'message_type':                 'INFO',
            'message':                      'Vote Smart candidate photo already retrieved previously.',
            'we_vote_candidate_id':         we_vote_candidate.id,
            'vote_smart_candidate_id':      vote_smart_candidate_id,
            'photo_url_from_vote_smart':    we_vote_candidate.photo_url_from_vote_smart,
        }
        return results

    candidate_results = retrieve_vote_smart_candidate_bio_into_local_db(vote_smart_candidate_id)

    photo_url_from_vote_smart = ""
    if not candidate_results['success']:
        status += 'VOTE_SMART_CANDIDATE_BIO_NOT_RETRIEVED_TO_LOCAL_DB: '
        status += candidate_results['status']
        success = False
    else:
        # Now look through those Vote Smart candidates and match them
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate_bio(vote_smart_candidate_id)
        if results['vote_smart_candidate_bio_found']:
            status += 'VOTE_SMART_CANDIDATE_BIO_MATCHED '
            vote_smart_candidate_bio = results['vote_smart_candidate_bio']
            we_vote_candidate.photo_url_from_vote_smart = vote_smart_candidate_bio.photo
            we_vote_candidate.save()
            # If here, we were able to match this candidate from the We Vote database to a candidate
            # from the Vote Smart database
            photo_url_from_vote_smart = vote_smart_candidate_bio.photo
            success = True
        else:
            # If here, we were NOT able to find any possible candidates from the Vote Smart database,
            # but we still will look in the Vote Smart Officials table below
            status += 'MATCHING_CANDIDATE_BIO_NOT_FOUND_FROM_ID ' \
                      '(vote_smart_candidate_id: ' \
                      '{vote_smart_candidate_id}) '.format(vote_smart_candidate_id=vote_smart_candidate_id)
            success = False

    results = {
        'success':                      success,
        'status':                       status,
        'message_type':                 'INFO',
        'message':                      status,
        'we_vote_candidate_id':         we_vote_candidate.id,
        'vote_smart_candidate_id':      vote_smart_candidate_id,
        'photo_url_from_vote_smart':    photo_url_from_vote_smart,
    }
    return results


def retrieve_vote_smart_candidates_into_local_db(last_name):
    try:
        last_name = last_name.replace("`", "'")  # Vote Smart doesn't like this kind of apostrophe: `
        candidates_list = votesmart.candidates.getByLastname(last_name)
        for one_candidate in candidates_list:
            one_candidate_filtered = candidate_object_filter(one_candidate)
            vote_smart_candidate, created = VoteSmartCandidate.objects.update_or_create(
                candidateId=one_candidate.candidateId, defaults=one_candidate_filtered)
            vote_smart_candidate.save()
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


def retrieve_vote_smart_candidate_bio_into_local_db(candidate_id):
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


def retrieve_vote_smart_officials_into_local_db(last_name):
    try:
        officials_list = votesmart.officials.getByLastname(last_name)
        for one_official in officials_list:
            one_official_filtered = official_object_filter(one_official)
            vote_smart_official, created = VoteSmartOfficial.objects.update_or_create(
                candidateId=one_official.candidateId, defaults=one_official_filtered)
            vote_smart_official.save()
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
