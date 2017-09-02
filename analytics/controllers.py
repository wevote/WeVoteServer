# analytics/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import AnalyticsManager, ACTION_VOTER_GUIDE_VISIT, ACTION_VOTER_GUIDE_ENTRY, \
    ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_AUTO_FOLLOW, \
    ACTION_ISSUE_FOLLOW, ACTION_BALLOT_VISIT, \
    ACTION_POSITION_TAKEN, ACTION_VOTER_TWITTER_AUTH, ACTION_VOTER_FACEBOOK_AUTH, \
    ACTION_WELCOME_ENTRY, ACTION_FRIEND_ENTRY

from config.base import get_environment_variable
from import_export_google_civic.controllers import retrieve_from_google_civic_api_election_query, \
    store_results_from_google_civic_api_election_query
import json
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")


def save_analytics_action_for_api(action_constant, voter_we_vote_id, voter_id,
                                  organization_we_vote_id, organization_id,
                                  google_civic_election_id, ballot_item_we_vote_id=None,
                                  voter_device_id=None):  # saveAnalyticsAction
    analytics_manager = AnalyticsManager()
    success = True
    status = "SAVE_ANALYTICS_ACTION "
    date_as_integer = 0

    if not positive_value_exists(action_constant):
        success = False
        status += "MISSING_ACTION_CONSTANT "
    if not positive_value_exists(voter_we_vote_id):
        success = False
        status += "MISSING_VOTER_WE_VOTE_ID "
    if not positive_value_exists(voter_id):
        success = False
        status += "MISSING_VOTER_ID "
    if action_constant == ACTION_VOTER_GUIDE_VISIT:
        # For these actions, make sure we have organization ids
        if not positive_value_exists(organization_we_vote_id):
            success = False
            status += "MISSING_ORGANIZATION_WE_VOTE_ID "
        if not positive_value_exists(organization_id):
            success = False
            status += "MISSING_ORGANIZATION_ID "

    if not success:
        results = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'action_constant':          action_constant,
            'google_civic_election_id': google_civic_election_id,
            'organization_we_vote_id':  organization_we_vote_id,
            'organization_id':          organization_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'date_as_integer':          date_as_integer
        }
        return results

    if action_constant == ACTION_VOTER_GUIDE_VISIT:
        save_results = analytics_manager.save_action_voter_guide_visit(
                voter_we_vote_id, voter_id, organization_we_vote_id, organization_id, google_civic_election_id,
                ballot_item_we_vote_id, voter_device_id)
        if save_results['action_saved']:
            action = save_results['action']
            date_as_integer = action.date_as_integer

    results = {
        'status':                   status,
        'success':                  success,
        'voter_device_id':          voter_device_id,
        'action_constant':          action_constant,
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'organization_id':          organization_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'date_as_integer':          date_as_integer
    }
    return results
