# analytics/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import AnalyticsAction, AnalyticsCountManager, AnalyticsManager, \
    ACTION_VOTER_GUIDE_VISIT, ACTION_VOTER_GUIDE_ENTRY, \
    ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_AUTO_FOLLOW, \
    ACTION_ISSUE_FOLLOW, ACTION_BALLOT_VISIT, \
    ACTION_POSITION_TAKEN, ACTION_VOTER_TWITTER_AUTH, ACTION_VOTER_FACEBOOK_AUTH, \
    ACTION_WELCOME_ENTRY, ACTION_FRIEND_ENTRY, ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils.timezone import localtime, now
from follow.models import FollowMetricsManager
from measure.models import ContestMeasureManager
from position.models import PositionMetricsManager
import pytz
from voter.models import VoterManager, VoterMetricsManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")


def augment_voter_analytics_action_entries_without_election_id(date_as_integer):
    """
    Retrieve list of voters with AnalyticsAction entries that have an empty google_civic_election_id
     and then loop through those entries to do the following:
     1) Look for the oldest entry with an election_id
     2) For that day, loop forward (while on the same day) and fill in the empty google_civic_election_ids
        until we find a new election id
     3) Then continue looping forward using the different election_id (while on the same day)
     4) Mark all of the entries prior to the first election entry as NULL
    :return:
    """
    success = False
    status = ""

    # Get distinct elections in this period of time so we can have access to election data
    # timezone = pytz.timezone("America/Los_Angeles")
    # election_dates = {
    #     4389: timezone.localize(datetime.strptime("2017-09-12", "%Y-%m-%d")),
    #     5000: timezone.localize(datetime.strptime("2016-11-08", "%Y-%m-%d")),
    # }

    # Get distinct voters in the time period
    voter_list = []
    try:
        voter_list_query = AnalyticsAction.objects.using('analytics').all()
        voter_list_query = voter_list_query.filter(date_as_integer__gte=date_as_integer)
        # Find entries where there is at least one empty google_civic_election_id
        voter_list_query = voter_list_query.filter(Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
        voter_list_query = voter_list_query.values('voter_we_vote_id').distinct()
        # voter_list_query = voter_list_query[:5]  # TEMP limit to 5
        voter_list = list(voter_list_query)
        voter_list_found = True
    except Exception as e:
        voter_list_found = False

    simple_voter_list = []
    for voter_dict in voter_list:
        if positive_value_exists(voter_dict['voter_we_vote_id']):
            simple_voter_list.append(voter_dict['voter_we_vote_id'])

    # Loop through each voter that has at least one empty google_civic_election_id entry
    analytics_updated_count = 0
    for voter_we_vote_id in simple_voter_list:
        results = augment_one_voter_analytics_action_entries_without_election_id(voter_we_vote_id)
        analytics_updated_count += results['analytics_updated_count']

    # TODO Outside of this function, call it recursively as long as we break out due to too much time passing
    #  between entries
    results = {
        'success':                  success,
        'status':                   status,
        'analytics_updated_count':  analytics_updated_count,
    }
    return results


def augment_one_voter_analytics_action_entries_without_election_id(voter_we_vote_id):
    success = False
    status = ""
    voter_history_list = []
    analytics_updated_count = 0
    try:
        voter_history_query = AnalyticsAction.objects.using('analytics').all()
        voter_history_query.order_by("id")  # order by oldest first
        voter_history_query = voter_history_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
        voter_history_list = list(voter_history_query)
    except Exception as e:
        pass

    # First loop through and assign election for candidates and measures associated with specific election
    candidate_campaign_manager = CandidateCampaignManager()
    contest_measure_manager = ContestMeasureManager()
    for analytics_action in voter_history_list:
        if positive_value_exists(analytics_action.ballot_item_we_vote_id) \
                and not positive_value_exists(analytics_action.google_civic_election_id):
            if "cand" in analytics_action.ballot_item_we_vote_id:
                # If we are looking at a candidate without a google_civic_election_id
                results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                    analytics_action.ballot_item_we_vote_id)
                if results['candidate_campaign_found']:
                    candidate_campaign = results['candidate_campaign']
                    try:
                        analytics_action.google_civic_election_id = candidate_campaign.google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        pass
            elif "meas" in analytics_action.ballot_item_we_vote_id:
                # If we are looking at a measure without a google_civic_election_id
                results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                    analytics_action.ballot_item_we_vote_id)
                if results['contest_measure_found']:
                    contest_measure = results['contest_measure']
                    try:
                        analytics_action.google_civic_election_id = contest_measure.google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        pass

    # Now "fill-in-the-gaps"
    leading_edge_google_civic_election_id = 0  # The very first google_civic_election_id found
    latest_google_civic_election_id = 0  # As we go from oldest-to-newest, update this to the next id found
    leading_edge_state_code = ''
    leading_edge_date_as_integer = 0
    analytics_action_list_before_first_election = []
    datetime_of_last_analytics_action_entry = None
    one_week = timedelta(days=7)
    for analytics_action in voter_history_list:
        if positive_value_exists(analytics_action.google_civic_election_id):
            # If the next-newest analytics_action entry has a google_civic_election_id,
            #  reset the latest_google_civic_election_id
            latest_google_civic_election_id = analytics_action.google_civic_election_id
            if not positive_value_exists(leading_edge_google_civic_election_id):
                # Only set this once
                leading_edge_google_civic_election_id = analytics_action.google_civic_election_id
        else:
            if positive_value_exists(latest_google_civic_election_id):
                # If within 1 week of last analytics_action entry, set the google_civic_election_id
                # to the leading_edge_google_civic_election_id
                is_within_one_week = False
                if datetime_of_last_analytics_action_entry:
                    time_passed_since_last_entry = \
                        analytics_action.exact_time - datetime_of_last_analytics_action_entry
                    if time_passed_since_last_entry < one_week:
                        is_within_one_week = True

                # if election_dates[latest_google_civic_election_id]:
                #     election_plus_one_week = election_dates[latest_google_civic_election_id] + one_week
                #     is_within_one_week = analytics_action.exact_time < election_plus_one_week

                if is_within_one_week:
                    try:
                        analytics_action.google_civic_election_id = latest_google_civic_election_id
                        analytics_action.save()
                        analytics_updated_count += 1
                    except Exception as e:
                        pass
            else:
                # If here, we have not set the leading_edge_google_civic_election_id yet
                #  so we want to save these entries into a "precursor" list
                analytics_action_list_before_first_election.append(analytics_action)

        if positive_value_exists(analytics_action.state_code):
            if not positive_value_exists(leading_edge_state_code):
                # Only set this once
                leading_edge_state_code = analytics_action.state_code

        if positive_value_exists(analytics_action.date_as_integer):
            if not positive_value_exists(leading_edge_date_as_integer):
                # Only set this once
                leading_edge_date_as_integer = analytics_action.date_as_integer

        datetime_of_last_analytics_action_entry = analytics_action.exact_time

    if positive_value_exists(leading_edge_google_civic_election_id):
        for analytics_action in analytics_action_list_before_first_election:
            # Loop through these and set to leading_edge_google_civic_election_id
            if not positive_value_exists(analytics_action.google_civic_election_id):  # Make sure it is empty
                try:
                    analytics_action.google_civic_election_id = leading_edge_google_civic_election_id
                    analytics_action.save()
                    analytics_updated_count += 1
                except Exception as e:
                    pass
    # 2017-09-21 As of now, we are not going to guess the election if there wasn't any election-related activity.
    # elif positive_value_exists(leading_edge_state_code) and positive_value_exists(leading_edge_date_as_integer):
    #     # Figure out the google_civic_election_id for state in question either 5 weeks before or 1 week after
    #     possible_elections_in_state = {
    #         20170911: 4389,
    #         20170912: 4389,
    #         20170913: 4389,
    #         20170914: 4389,
    #     }
    #     most_likely_google_civic_election_id = possible_elections_in_state[leading_edge_date_as_integer]
    #     if positive_value_exists(most_likely_google_civic_election_id):
    #         for analytics_action in analytics_action_list_before_first_election:
    #             # Loop through these and set to most_likely_google_civic_election_id
    #             if not positive_value_exists(analytics_action.google_civic_election_id):  # Make sure it is empty
    #                 try:
    #                     analytics_action.google_civic_election_id = most_likely_google_civic_election_id
    #                     analytics_action.save()
    #                     analytics_updated_count += 1
    #                 except Exception as e:
    #                     pass

    results = {
        'success': success,
        'status': status,
        'analytics_updated_count': analytics_updated_count,
    }
    return results


def save_analytics_action_for_api(action_constant, voter_we_vote_id, voter_id, state_code,
                                  organization_we_vote_id, organization_id,
                                  google_civic_election_id, ballot_item_we_vote_id=None,
                                  voter_device_id=None):  # saveAnalyticsAction
    analytics_manager = AnalyticsManager()
    success = True
    status = "SAVE_ANALYTICS_ACTION "
    date_as_integer = 0
    required_variables_missing = False

    action_requires_organization_ids = True if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS else False

    if not positive_value_exists(action_constant):
        success = False
        required_variables_missing = True
        status += "MISSING_ACTION_CONSTANT "
    if not positive_value_exists(voter_we_vote_id):
        success = False
        required_variables_missing = True
        status += "MISSING_VOTER_WE_VOTE_ID "
    if not positive_value_exists(voter_id):
        success = False
        required_variables_missing = True
        status += "MISSING_VOTER_ID "
    if action_requires_organization_ids:
        # For these actions, make sure we have organization ids
        if not positive_value_exists(organization_we_vote_id):
            success = False
            required_variables_missing = True
            status += "MISSING_ORGANIZATION_WE_VOTE_ID "
        if not positive_value_exists(organization_id):
            success = False
            required_variables_missing = True
            status += "MISSING_ORGANIZATION_ID "

    if required_variables_missing:
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

    save_results = analytics_manager.save_action(
            action_constant,
            voter_we_vote_id, voter_id, state_code,
            organization_we_vote_id, organization_id, google_civic_election_id,
            ballot_item_we_vote_id, voter_device_id)
    if save_results['action_saved']:
        action = save_results['action']
        date_as_integer = action.date_as_integer
        status += save_results['status']
        success = save_results['success']
    else:
        status += "ACTION_VOTER_GUIDE_VISIT-NOT_SAVED "
        success = False

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
    follow_count_manager = FollowMetricsManager()

    google_civic_election_id = convert_to_int(google_civic_election_id)
    visitors_total = analytics_count_manager.fetch_visitors_to_organization_in_election(
        organization_we_vote_id, google_civic_election_id)
    voter_guide_entrants = analytics_count_manager.fetch_visitors_first_visit_to_organization_in_election(
        organization_we_vote_id, google_civic_election_id)
    followers_at_time_of_election = follow_count_manager.fetch_organization_followers(
        organization_we_vote_id, google_civic_election_id)
    new_followers = analytics_count_manager.fetch_new_followers_in_election(
        google_civic_election_id, organization_we_vote_id)
    new_autofollowers = analytics_count_manager.fetch_new_auto_followers_in_election(
        google_civic_election_id, organization_we_vote_id)
    entrants_visited_ballot = analytics_count_manager.fetch_organization_entrants_visited_ballot(
        organization_we_vote_id, google_civic_election_id)
    followers_visited_ballot = analytics_count_manager.fetch_organization_followers_visited_ballot(
        organization_we_vote_id, google_civic_election_id)
    entrants_took_position = analytics_count_manager.fetch_organization_entrants_took_position(
        organization_we_vote_id, google_civic_election_id)
    followers_took_position = analytics_count_manager.fetch_organization_followers_took_position(
        organization_we_vote_id, google_civic_election_id)

    success = True
    status += "CALCULATED_ORGANIZATION_ELECTION_METRICS "

    organization_election_metrics_values = {
        'google_civic_election_id': google_civic_election_id,
        'organization_we_vote_id':  organization_we_vote_id,
        'visitors_total':           visitors_total,
        'voter_guide_entrants':     voter_guide_entrants,
        'followers_at_time_of_election':    followers_at_time_of_election,
        'new_followers':            new_followers,
        'new_autofollowers':        new_autofollowers,
        'entrants_visited_ballot':  entrants_visited_ballot,
        'followers_visited_ballot': followers_visited_ballot,
        'entrants_took_position':   entrants_took_position,
        'followers_took_position':  followers_took_position,
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

    analytics_count_manager = AnalyticsCountManager()
    follow_metrics_manager = FollowMetricsManager()
    position_metrics_manager = PositionMetricsManager()
    voter_metrics_manager = VoterMetricsManager()

    google_civic_election_id = convert_to_int(google_civic_election_id)
    visitors_total = analytics_count_manager.fetch_visitors_in_election(google_civic_election_id)
    voter_guide_entries = None
    voter_guide_views = None
    voter_guides_viewed = analytics_count_manager.fetch_voter_guides_viewed(google_civic_election_id)
    issues_followed = None
    unique_voters_that_followed_organizations = analytics_count_manager.fetch_new_followers_in_election(
        google_civic_election_id)
    unique_voters_that_auto_followed_organizations = analytics_count_manager.fetch_new_auto_followers_in_election(
        google_civic_election_id)
    organizations_followed = None
    organizations_autofollowed = None
    organizations_signed_in = None
    organizations_with_positions = None
    organization_public_positions = None
    individuals_with_positions = None
    individuals_with_public_positions = None
    individuals_with_friends_only_positions = None
    public_positions = position_metrics_manager.fetch_positions_public(google_civic_election_id)
    public_positions_with_comments = position_metrics_manager.fetch_positions_public_with_comments(
        google_civic_election_id)
    friends_only_positions = position_metrics_manager.fetch_positions_friends_only(google_civic_election_id)
    friends_only_positions_with_comments = position_metrics_manager.fetch_positions_friends_only_with_comments(
        google_civic_election_id)
    entered_full_address = None

    success = True

    sitewide_election_metrics_values = {
        'google_civic_election_id':                 google_civic_election_id,
        'visitors_total':                           visitors_total,
        'voter_guide_entries':                      voter_guide_entries,
        'voter_guide_views':                        voter_guide_views,
        'voter_guides_viewed':                      voter_guides_viewed,
        'issues_followed':                          issues_followed,
        'unique_voters_that_followed_organizations':        unique_voters_that_followed_organizations,
        'unique_voters_that_auto_followed_organizations':   unique_voters_that_auto_followed_organizations,
        'organizations_followed':                   organizations_followed,
        'organizations_autofollowed':               organizations_autofollowed,
        'organizations_signed_in':                  organizations_signed_in,
        'organizations_with_positions':             organizations_with_positions,
        'organization_public_positions':            organization_public_positions,
        'individuals_with_positions':               individuals_with_positions,
        'individuals_with_public_positions':        individuals_with_public_positions,
        'individuals_with_friends_only_positions':  individuals_with_friends_only_positions,
        'public_positions':                         public_positions,
        'public_positions_with_comments':           public_positions_with_comments,
        'friends_only_positions':                   friends_only_positions,
        'friends_only_positions_with_comments':     friends_only_positions_with_comments,
        'entered_full_address':                     entered_full_address,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_election_metrics_values': sitewide_election_metrics_values,
    }
    return results


def calculate_sitewide_voter_metrics_for_one_voter(voter_we_vote_id):
    status = ""
    success = False
    voter_id = 0
    signed_in_twitter = False
    signed_in_facebook = False
    signed_in_with_email = False
    analytics_count_manager = AnalyticsCountManager()
    follow_metrics_manager = FollowMetricsManager()
    position_metrics_manager = PositionMetricsManager()
    voter_metrics_manager = VoterMetricsManager()

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id)
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        signed_in_twitter = voter.signed_in_twitter()
        signed_in_facebook = voter.signed_in_facebook()
        signed_in_with_email = voter.signed_in_with_email()

    actions_count = analytics_count_manager.fetch_voter_action_count(voter_we_vote_id)
    seconds_on_site = None
    elections_viewed = None
    voter_guides_viewed = analytics_count_manager.fetch_voter_voter_guides_viewed(voter_we_vote_id)
    ballot_visited = analytics_count_manager.fetch_voter_ballot_visited(voter_we_vote_id)
    welcome_visited = analytics_count_manager.fetch_voter_welcome_visited(voter_we_vote_id)
    entered_full_address = voter_metrics_manager.fetch_voter_entered_full_address(voter_id)
    issues_followed = follow_metrics_manager.fetch_voter_issues_followed(voter_we_vote_id)
    organizations_followed = follow_metrics_manager.fetch_voter_organizations_followed(voter_id)
    time_until_sign_in = None
    positions_entered_friends_only = position_metrics_manager.fetch_voter_positions_entered_friends_only(
        voter_we_vote_id)
    positions_entered_public = position_metrics_manager.fetch_voter_positions_entered_public(voter_we_vote_id)
    comments_entered_friends_only = position_metrics_manager.fetch_voter_comments_entered_friends_only(
        voter_we_vote_id)
    comments_entered_public = position_metrics_manager.fetch_voter_comments_entered_public(voter_we_vote_id)
    days_visited = analytics_count_manager.fetch_voter_days_visited(voter_we_vote_id)
    last_action_date = analytics_count_manager.fetch_voter_last_action_date(voter_we_vote_id)

    success = True

    sitewide_voter_metrics_values = {
        'voter_we_vote_id':         voter_we_vote_id,
        'actions_count':            actions_count,
        'seconds_on_site':          seconds_on_site,
        'elections_viewed':         elections_viewed,
        'voter_guides_viewed':      voter_guides_viewed,
        'issues_followed':          issues_followed,
        'organizations_followed':   organizations_followed,
        'ballot_visited':           ballot_visited,
        'welcome_visited':          welcome_visited,
        'entered_full_address':     entered_full_address,
        'time_until_sign_in':       time_until_sign_in,
        'positions_entered_friends_only':   positions_entered_friends_only,
        'positions_entered_public':         positions_entered_public,
        'comments_entered_friends_only':    comments_entered_friends_only,
        'comments_entered_public':          comments_entered_public,
        'signed_in_twitter':        signed_in_twitter,
        'signed_in_facebook':       signed_in_facebook,
        'signed_in_with_email':     signed_in_with_email,
        'days_visited':             days_visited,
        'last_action_date': last_action_date,
    }
    results = {
        'status':                           status,
        'success':                          success,
        'sitewide_voter_metrics_values':    sitewide_voter_metrics_values,
    }
    return results


def move_analytics_info_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = " MOVE_ANALYTICS_ACTION_DATA"
    success = False
    analytics_action_moved = 0
    analytics_action_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status = "MOVE_ANALYTICS_ACTION-MISSING_FROM_OR_TO_VOTER_ID"
        results = {
            'status':                       status,
            'success':                      success,
            'from_voter_we_vote_id':        from_voter_we_vote_id,
            'to_voter_we_vote_id':          to_voter_we_vote_id,
            'analytics_action_moved':       analytics_action_moved,
            'analytics_action_not_moved':   analytics_action_not_moved,
        }
        return results

    analytics_manager = AnalyticsManager()
    analytics_action_list_results = analytics_manager.retrieve_analytics_action_list(from_voter_we_vote_id)
    if analytics_action_list_results['analytics_action_list_found']:
        analytics_action_list = analytics_action_list_results['analytics_action_list']

        for analytics_action_object in analytics_action_list:
            # Change the voter_we_vote_id
            try:
                analytics_action_object.voter_we_vote_id = to_voter_we_vote_id
                analytics_action_object.save()
                analytics_action_moved += 1
            except Exception as e:
                analytics_action_not_moved += 1
                status += "UNABLE_TO_SAVE_ANALYTICS_ACTION "

        status += " MOVE_ANALYTICS_ACTION, moved: " + str(analytics_action_moved) + \
                  ", not moved: " + str(analytics_action_not_moved)
    else:
        status += " " + analytics_action_list_results['status']

    results = {
        'status':                       status,
        'success':                      success,
        'from_voter_we_vote_id':        from_voter_we_vote_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'analytics_action_moved':       analytics_action_moved,
        'analytics_action_not_moved':   analytics_action_not_moved,
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
    status = "SAVE_ORGANIZATION_ELECTION_METRICS, " \
             "google_civic_election_id: " + str(google_civic_election_id) + \
             ", organization_we_vote_id: " + str(organization_we_vote_id) + " "
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


def save_sitewide_voter_metrics(look_for_changes_since_this_date_as_integer):
    status = ""
    success = False
    sitewide_voter_metrics_updated = 0

    analytics_manager = AnalyticsManager()
    voter_list_results = analytics_manager.retrieve_voter_we_vote_id_list_with_changes_since(
        look_for_changes_since_this_date_as_integer)
    if voter_list_results['voter_we_vote_id_list_found']:
        voter_we_vote_id_list = voter_list_results['voter_we_vote_id_list']
        for voter_we_vote_id in voter_we_vote_id_list:
            results = calculate_sitewide_voter_metrics_for_one_voter(voter_we_vote_id)
            status += results['status']
            if results['success']:
                sitewide_voter_metrics_values = results['sitewide_voter_metrics_values']

                analytics_manager = AnalyticsManager()
                update_results = analytics_manager.save_sitewide_voter_metrics_values_for_one_voter(
                    sitewide_voter_metrics_values)
                status += update_results['status']
                success = update_results['success']
                if success:
                    sitewide_voter_metrics_updated += 1

    results = {
        'status':   status,
        'success':  success,
        'sitewide_voter_metrics_updated': sitewide_voter_metrics_updated,
    }
    return results
