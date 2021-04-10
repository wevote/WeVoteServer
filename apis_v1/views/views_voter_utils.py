# apis_v1/views/views_voter_utils.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from voter.models import VoterDeviceLinkManager, VoterManager

from voter_guide.controllers import voter_follow_all_organizations_followed_by_organization_for_api
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_maximum_number_to_retrieve_from_request, \
    get_voter_device_id, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def get_voter_from_request(request, status):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter = None
    voter_found = False
    voter_device_link = None
    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()
    link_results = voter_device_link_manager.retrieve_voter_device_link(
        voter_device_id=voter_device_id)
    if link_results['voter_device_link_found']:
        voter_device_link = link_results['voter_device_link']
        if positive_value_exists(voter_device_link.voter_id):
            results = voter_manager.retrieve_voter_by_id(voter_device_link.voter_id, read_only=False)
            if results['voter_found']:
                voter = results['voter']
                voter_found = True
            else:
                status += results['status']
    else:
        status += link_results['status']

    return status, voter, voter_found, voter_device_link

