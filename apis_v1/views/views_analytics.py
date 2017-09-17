# apis_v1/views/views_analytics.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from analytics.controllers import save_analytics_action_for_api
from analytics.models import ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from organization.models import OrganizationManager
from voter.models import fetch_voter_we_vote_id_from_voter_id, VoterDeviceLinkManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, is_voter_device_id_valid, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def save_analytics_action_view(request):  # saveAnalyticsAction
    status = ""
    success = False
    missing_required_variable = False
    voter_id = 0
    voter_we_vote_id = ""
    state_code_from_ip_address = ""  # If a state_code is NOT passed in, we want to get the state_code from ip address
    voter_device_id_for_storage = ""
    date_as_integer = 0

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    action_constant = convert_to_int(request.GET.get('action_constant', 0))
    state_code = request.GET.get('state_code', '')  # If a state code is passed in, we want to use it
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_id = convert_to_int(request.GET.get('organization_id', 0))
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', '')

    # We use the lighter call to VoterDeviceLinkManager instead of VoterManager until we know there is an entry
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        voter_id = voter_device_link.voter_id
        state_code_from_ip_address = voter_device_link.state_code
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_id(voter_id)
    else:
        voter_device_id_for_storage = voter_device_id

    action_requires_organization_ids = True if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS else False
    if action_requires_organization_ids:
        # If here, make sure we have both organization ids
        organization_manager = OrganizationManager()
        if positive_value_exists(organization_we_vote_id) and not positive_value_exists(organization_id):
            organization_id = organization_manager.fetch_organization_id(organization_we_vote_id)
        elif positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
            organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(organization_id)

        if not positive_value_exists(organization_we_vote_id):
            status += "MISSING_ORGANIZATION_WE_VOTE_ID "
            success = False
            missing_required_variable = True
        if not positive_value_exists(organization_id):
            status += "MISSING_ORGANIZATION_ID "
            success = False
            missing_required_variable = True

    if not positive_value_exists(state_code):
        state_code = state_code_from_ip_address

    if missing_required_variable:
        json_data = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'action_constant':          action_constant,
            'state_code':               state_code,
            'google_civic_election_id': google_civic_election_id,
            'organization_we_vote_id':  organization_we_vote_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'organization_id':          organization_id,
            'date_as_integer':          date_as_integer
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = save_analytics_action_for_api(action_constant, voter_we_vote_id, voter_id, state_code,
                                            organization_we_vote_id, organization_id,
                                            google_civic_election_id, ballot_item_we_vote_id,
                                            voter_device_id_for_storage)

    status += results['status']
    json_data = {
        'status':                   status,
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'action_constant':          action_constant,
        'state_code':               state_code,
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'organization_id':          organization_id,
        'date_as_integer':          results['date_as_integer']
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
