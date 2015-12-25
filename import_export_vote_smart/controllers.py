# import_export_vote_smart/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import requests
from .models import State, state_filter
from config.base import get_environment_variable
from django.contrib import messages
#from votesmart import votesmart
from .votesmart_local import votesmart  # Modified to work with Python 3
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
VOTE_SMART_API_URL = get_environment_variable("VOTE_SMART_API_URL")

votesmart.apikey = VOTE_SMART_API_KEY


def get_vote_smart_candidate():
    return


def _get_state_by_id_as_dict(stateId):
    """Access Vote Smart API and return dictionary representing state."""
    return votesmart.state.getState(stateId).__dict__


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
        logger.error("one state found")
        one_state_filtered = state_filter(one_state)
        state, created = State.objects.get_or_create(**one_state_filtered)
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
