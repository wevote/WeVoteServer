# analytics/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import AnalyticsCountManager, AnalyticsManager, ACTION_VOTER_GUIDE_VISIT, ACTION_VOTER_GUIDE_ENTRY, \
    ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_AUTO_FOLLOW, \
    ACTION_ISSUE_FOLLOW, ACTION_BALLOT_VISIT, \
    ACTION_POSITION_TAKEN, ACTION_VOTER_TWITTER_AUTH, ACTION_VOTER_FACEBOOK_AUTH, \
    ACTION_WELCOME_ENTRY, ACTION_FRIEND_ENTRY

from config.base import get_environment_variable
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

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


def calculate_organization_election_metrics(google_civic_election_id, organization_we_vote_id):
    status = ""
    success = False

    analytics_count_manager = AnalyticsCountManager()

    google_civic_election_id = convert_to_int(google_civic_election_id)
    visitors_total = \
        analytics_count_manager.fetch_visitors_to_organization_in_election(organization_we_vote_id,
                                                                           google_civic_election_id)
    voter_guide_entrants = None
    new_followers = None
    new_autofollowers = None
    entrants_visited_ballot = None
    followers_visited_ballot = None

    success = True

    organization_election_metrics_values = {
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'visitors_total':           visitors_total,
        'voter_guide_entrants':     voter_guide_entrants,
        'new_followers':            new_followers,
        'new_autofollowers':        new_autofollowers,
        'entrants_visited_ballot':  entrants_visited_ballot,
        'followers_visited_ballot': followers_visited_ballot,
    }
    results = {
        'status':                               status,
        'success':                              success,
        'organization_election_metrics_values': organization_election_metrics_values,
    }
    return results


def calculate_organization_daily_metrics(organization_we_vote_id, date):
    status = ""
    success = False

    date_as_integer = convert_to_int(date)
    visitors_total = None
    visitors_today = None
    new_visitors_today = None
    voter_guide_entrants_today = None
    entrants_visiting_ballot = None
    followers_visiting_ballot = None
    followers_total = None
    new_followers_today = None
    autofollowers_total = None
    new_autofollowers_today = None
    issues_linked_total = None
    organization_public_positions = None

    success = True

    organization_daily_metrics_values = {
        'date_as_integer':                          date_as_integer,
        'organization_we_vote_id':                  organization_we_vote_id,
        'visitors_total':                           visitors_total,
        'visitors_today':                           visitors_today,
        'new_visitors_today':                       new_visitors_today,
        'voter_guide_entrants_today':               voter_guide_entrants_today,
        'entrants_visiting_ballot':                 entrants_visiting_ballot,
        'followers_visiting_ballot':                followers_visiting_ballot,
        'followers_total':                          followers_total,
        'new_followers_today':                      new_followers_today,
        'autofollowers_total':                      autofollowers_total,
        'new_autofollowers_today':                  new_autofollowers_today,
        'issues_linked_total':                      issues_linked_total,
        'organization_public_positions':            organization_public_positions,
    }
    results = {
        'status':                               status,
        'success':                              success,
        'organization_daily_metrics_values':    organization_daily_metrics_values,
    }
    return results


def calculate_sitewide_daily_metrics(date):
    status = ""
    success = False

    date_as_integer = convert_to_int(date)
    visitors_total = None
    visitors_today = None
    new_visitors_today = None
    voter_guide_entrants_today = None
    welcome_page_entrants_today = None
    friend_entrants_today = None
    authenticated_visitors_total = None
    authenticated_visitors_today = None
    ballots_viewed_today = None
    voter_guides_viewed_total = None
    voter_guides_viewed_today = None
    issues_followed_total = None
    issues_followed_today = None
    organizations_followed_total = None
    organizations_followed_today = None
    organizations_autofollowed_total = None
    organizations_autofollowed_today = None
    organizations_with_linked_issues = None
    issues_linked_total = None
    issues_linked_today = None
    organizations_signed_in_total = None
    organizations_with_positions = None
    organizations_with_new_positions_today = None
    organization_public_positions = None
    individuals_with_positions = None
    individuals_with_public_positions = None
    individuals_with_friends_only_positions = None
    friends_only_positions = None
    entered_full_address = None

    success = True

    sitewide_daily_metrics_values = {
        'date_as_integer':                          date_as_integer,
        'visitors_total':                           visitors_total,
        'visitors_today':                           visitors_today,
        'new_visitors_today':                       new_visitors_today,
        'voter_guide_entrants_today':               voter_guide_entrants_today,
        'welcome_page_entrants_today':               welcome_page_entrants_today,
        'friend_entrants_today':                     friend_entrants_today,
        'authenticated_visitors_total':             authenticated_visitors_total,
        'authenticated_visitors_today':             authenticated_visitors_today,
        'ballots_viewed_today':                     ballots_viewed_today,
        'voter_guides_viewed_total':                voter_guides_viewed_total,
        'voter_guides_viewed_today':                voter_guides_viewed_today,
        'issues_followed_total':                    issues_followed_total,
        'issues_followed_today':                    issues_followed_today,
        'organizations_followed_total':             organizations_followed_total,
        'organizations_followed_today':             organizations_followed_today,
        'organizations_autofollowed_total':         organizations_autofollowed_total,
        'organizations_autofollowed_today':         organizations_autofollowed_today,
        'organizations_with_linked_issues':         organizations_with_linked_issues,
        'issues_linked_total':                      issues_linked_total,
        'issues_linked_today':                      issues_linked_today,
        'organizations_signed_in_total':            organizations_signed_in_total,
        'organizations_with_positions':             organizations_with_positions,
        'organizations_with_new_positions_today':   organizations_with_new_positions_today,
        'organization_public_positions':            organization_public_positions,
        'individuals_with_positions':               individuals_with_positions,
        'individuals_with_public_positions':        individuals_with_public_positions,
        'individuals_with_friends_only_positions':  individuals_with_friends_only_positions,
        'friends_only_positions':                   friends_only_positions,
        'entered_full_address':                     entered_full_address,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_daily_metrics_values':    sitewide_daily_metrics_values,
    }
    return results


def calculate_sitewide_election_metrics(google_civic_election_id):
    status = ""
    success = False

    google_civic_election_id = convert_to_int(google_civic_election_id)
    visitors_total = None
    voter_guide_entrants = None
    voter_guides_viewed = None
    issues_followed = None
    organizations_followed = None
    organizations_autofollowed = None
    organizations_signed_in = None
    organizations_with_positions = None
    organization_public_positions = None
    individuals_with_positions = None
    individuals_with_public_positions = None
    individuals_with_friends_only_positions = None
    friends_only_positions = None
    entered_full_address = None

    success = True

    sitewide_election_metrics_values = {
        'google_civic_election_id':                 google_civic_election_id,
        'visitors_total':                           visitors_total,
        'voter_guide_entrants':                     voter_guide_entrants,
        'voter_guides_viewed':                      voter_guides_viewed,
        'issues_followed':                          issues_followed,
        'organizations_followed':                   organizations_followed,
        'organizations_autofollowed':               organizations_autofollowed,
        'organizations_signed_in':                  organizations_signed_in,
        'organizations_with_positions':             organizations_with_positions,
        'organization_public_positions':            organization_public_positions,
        'individuals_with_positions':               individuals_with_positions,
        'individuals_with_public_positions':        individuals_with_public_positions,
        'individuals_with_friends_only_positions':  individuals_with_friends_only_positions,
        'friends_only_positions':                   friends_only_positions,
        'entered_full_address':                     entered_full_address,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_election_metrics_values': sitewide_election_metrics_values,
    }
    return results


def save_organization_daily_metrics(organization_we_vote_id, date):
    status = ""
    success = False

    results = calculate_organization_daily_metrics(organization_we_vote_id, date)
    status += results['status']
    if results['success']:
        organization_daily_metrics_values = results['organization_daily_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = analytics_manager.save_organization_daily_metrics_values(organization_daily_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def save_organization_election_metrics(google_civic_election_id, organization_we_vote_id):
    status = ""
    success = False

    results = calculate_organization_election_metrics(google_civic_election_id, organization_we_vote_id)
    status += results['status']
    if results['success']:
        organization_election_metrics_values = results['organization_election_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = \
            analytics_manager.save_organization_election_metrics_values(organization_election_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def save_sitewide_daily_metrics(date):
    status = ""
    success = False

    results = calculate_sitewide_daily_metrics(date)
    status += results['status']
    if results['success']:
        sitewide_daily_metrics_values = results['sitewide_daily_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = analytics_manager.save_sitewide_daily_metrics_values(sitewide_daily_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def save_sitewide_election_metrics(google_civic_election_id):
    status = ""
    success = False

    results = calculate_sitewide_election_metrics(google_civic_election_id)
    status += results['status']
    if results['success']:
        sitewide_election_metrics_values = results['sitewide_election_metrics_values']

        analytics_manager = AnalyticsManager()
        update_results = \
            analytics_manager.save_sitewide_election_metrics_values(sitewide_election_metrics_values)
        status += update_results['status']
        success = update_results['success']

    results = {
        'status':   status,
        'success':  success,
    }
    return results
