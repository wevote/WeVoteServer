# organization/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import base64
import json
import re
from io import BytesIO

import robot_detection
import tweepy
from PIL import Image, ImageOps
from django.db.models import Q
from django.http import HttpResponse

import wevote_functions.admin
from analytics.models import ACTION_BALLOT_VISIT, ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_FOLLOW_IGNORE, \
    ACTION_ORGANIZATION_STOP_FOLLOWING, ACTION_ORGANIZATION_STOP_IGNORING, AnalyticsManager
from campaign.controllers import move_campaignx_to_another_organization
from config.base import get_environment_variable
from election.models import ElectionManager
from exception.models import handle_record_not_found_exception
from follow.controllers import delete_organization_followers_for_organization, \
    move_organization_followers_to_another_organization
from follow.models import FollowOrganizationManager, FollowOrganizationList, FOLLOW_IGNORE, FOLLOWING, \
    STOP_FOLLOWING, STOP_IGNORING
from image.controllers import cache_image_object_to_aws, cache_master_and_resized_image, FACEBOOK, \
    PROFILE_IMAGE_ORIGINAL_MAX_WIDTH, PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT
from image.controllers import cache_organization_sharing_image, retrieve_all_images_for_one_organization
from import_export_facebook.models import FacebookManager
from politician.models import PoliticianManager
from position.controllers import delete_positions_for_organization, move_positions_to_another_organization, \
    update_position_entered_details_from_organization
from position.models import PositionListManager
from stripe_donations.controllers import move_donation_info_to_another_organization
from twitter.models import TwitterUserManager, create_detailed_counter_entry, mark_detailed_counter_entry
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager, Voter
from voter_guide.models import VoterGuide, VoterGuideManager, VoterGuideListManager
from wevote_functions.functions import convert_to_int, \
    extract_twitter_handle_from_text_string, positive_value_exists, \
    process_request_from_master, extract_website_from_url
from .controllers_fastly import add_wevote_subdomain_to_fastly, add_subdomain_route53_record, \
    get_wevote_subdomain_status
from .models import Organization, OrganizationListManager, OrganizationManager, OrganizationMembershipLinkToVoter, \
    OrganizationReservedDomain, OrganizationTeamMember, ORGANIZATION_UNIQUE_IDENTIFIERS

logger = wevote_functions.admin.get_logger(__name__)

CAMPAIGNS_ROOT_URL = get_environment_variable("CAMPAIGNS_ROOT_URL", no_exception=True)
if not positive_value_exists(CAMPAIGNS_ROOT_URL):
    CAMPAIGNS_ROOT_URL = "https://campaigns.wevote.us"
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")
ORGANIZATIONS_SYNC_URL = get_environment_variable("ORGANIZATIONS_SYNC_URL")  # organizationsSyncOut
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")
CHOSEN_FAVICON_MAX_WIDTH = 32
CHOSEN_FAVICON_MAX_HEIGHT = 32
CHOSEN_LOGO_MAX_WIDTH = 132
CHOSEN_LOGO_MAX_HEIGHT = 42
CHOSEN_SOCIAL_SHARE_MASTER_MAX_WIDTH = 1600
CHOSEN_SOCIAL_SHARE_MASTER_MAX_HEIGHT = 900


def delete_membership_link_entries_for_voter(from_voter_we_vote_id):
    status = ''
    success = True
    voter_member_entries_deleted = 0
    voter_member_entries_not_deleted = 0

    if not positive_value_exists(from_voter_we_vote_id):
        status += "MOVE_MEMBERSHIP_LINK_ENTRIES_TO_ANOTHER_VOTER-Missing from_voter_we_vote_id "
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'voter_member_entries_deleted':     voter_member_entries_deleted,
            'voter_member_entries_not_deleted': voter_member_entries_not_deleted,
        }
        return results

    voter_members_query = OrganizationMembershipLinkToVoter.objects.all()
    voter_members_query = voter_members_query.filter(voter_we_vote_id__iexact=from_voter_we_vote_id)
    voter_members_list = list(voter_members_query)
    for voter_member_link in voter_members_list:
        try:
            voter_member_link.delete()
            voter_member_entries_deleted += 1
        except Exception as e:
            status += "COULD_NOT_SAVE_ORGANIZATION_MEMBERSHIP_LINK: " + str(e) + ' '
            success = False
            voter_member_entries_not_deleted += 1

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'voter_member_entries_deleted':       voter_member_entries_deleted,
        'voter_member_entries_not_deleted':   voter_member_entries_not_deleted,
    }
    return results


def delete_organization_membership_link_for_organization(from_organization_we_vote_id):
    status = ''
    success = True
    membership_link_entries_deleted = 0
    membership_link_entries_not_deleted = 0

    organization_members_query = OrganizationMembershipLinkToVoter.objects.all()
    organization_members_query = organization_members_query.filter(
        organization_we_vote_id__iexact=from_organization_we_vote_id)
    organization_members_list = list(organization_members_query)
    for organization_member_link in organization_members_list:
        try:
            organization_member_link.delete()
            membership_link_entries_deleted += 1
        except Exception as e:
            membership_link_entries_not_deleted += 1
            status += "COULD_NOT_DELETE_MEMBERSHIP_LINK: " + str(e) + " "
            success = False

    results = {
        'status':                               status,
        'success':                              success,
        'from_organization_we_vote_id':         from_organization_we_vote_id,
        'membership_link_entries_deleted':      membership_link_entries_deleted,
        'membership_link_entries_not_deleted':  membership_link_entries_not_deleted,
    }
    return results


def delete_organization_complete(from_organization_id, from_organization_we_vote_id):
    status = ""
    success = True

    if not positive_value_exists(from_organization_id) and not positive_value_exists(from_organization_we_vote_id):
        status += "MISSING_BOTH_ORGANIZATION_IDS "
        results = {
            'status': status,
            'success': success,
        }
        return results

    # Make sure we have both from_organization values
    organization_manager = OrganizationManager()
    if positive_value_exists(from_organization_id) and not positive_value_exists(from_organization_we_vote_id):
        from_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(from_organization_id)
    elif positive_value_exists(from_organization_we_vote_id) and not positive_value_exists(from_organization_id):
        from_organization_id = organization_manager.fetch_organization_id(from_organization_we_vote_id)

    # If anyone is following the old voter's organization, delete those followers
    delete_organization_followers_results = delete_organization_followers_for_organization(
        from_organization_id, from_organization_we_vote_id)
    status += " " + delete_organization_followers_results['status']

    # If anyone has been linked with external_voter_id as a member of the old voter's organization,
    #  move those followers to the new voter's organization
    delete_organization_membership_link_results = delete_organization_membership_link_for_organization(
        from_organization_we_vote_id)
    status += " " + delete_organization_membership_link_results['status']

    # Delete positions from "from" organization
    delete_positions_to_another_org_results = delete_positions_for_organization(
        from_organization_id, from_organization_we_vote_id)
    status += " " + delete_positions_to_another_org_results['status']

    # delete_donation_results = move_donation_info_to_another_organization(
    #     from_organization_we_vote_id, to_organization_we_vote_id)
    # status += " " + delete_donation_results['status']

    # Finally, delete the from_voter's organization
    results = organization_manager.retrieve_organization_from_we_vote_id(from_organization_we_vote_id)
    if results['organization_found']:
        organization_to_delete = results['organization']
        try:
            organization_to_delete.delete()
        except Exception as e:
            status += "UNABLE_TO_DELETE_FROM_ORGANIZATION: " + str(e) + " "

    results = {
        'status':                   status,
        'success':                  success,
    }
    return results


def figure_out_organization_conflict_values(organization1, organization2):
    organization_merge_conflict_values = {}

    for attribute in ORGANIZATION_UNIQUE_IDENTIFIERS:
        try:
            organization1_attribute_value = getattr(organization1, attribute)
            organization2_attribute_value = getattr(organization2, attribute)
            if organization1_attribute_value is None and organization2_attribute_value is None:
                organization_merge_conflict_values[attribute] = 'MATCHING'
            elif organization1_attribute_value == "" and organization2_attribute_value == "":
                organization_merge_conflict_values[attribute] = 'MATCHING'
            elif organization1_attribute_value is None or organization1_attribute_value == "":
                organization_merge_conflict_values[attribute] = 'CANDIDATE2'
            elif organization2_attribute_value is None or organization2_attribute_value == "":
                organization_merge_conflict_values[attribute] = 'CANDIDATE1'
            else:
                if attribute == "organization_twitter_handle" or attribute == "state_serving_code":
                    if organization1_attribute_value.lower() == organization2_attribute_value.lower():
                        organization_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        organization_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    if organization1_attribute_value == organization2_attribute_value:
                        organization_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        organization_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return organization_merge_conflict_values


def full_domain_string_available(full_domain_string, requesting_organization_id):
    """
    Make sure this full domain name (website address) isn't already taken
    :param full_domain_string:
    :param requesting_organization_id:
    :return:
    """
    status = ""
    if not positive_value_exists(full_domain_string):
        status += "MISSING_FULL_DOMAIN_STRING "
        results = {
            'full_domain_string_available': False,
            'status':                       status,
            'success':                      False,
        }
        return results
    try:
        organization_list_query = Organization.objects.using('readonly').all()
        organization_list_query = organization_list_query.exclude(id=requesting_organization_id)
        organization_list_query = organization_list_query.filter(
            Q(chosen_domain_string__iexact=full_domain_string) |
            Q(chosen_domain_string2__iexact=full_domain_string) |
            Q(chosen_domain_string3__iexact=full_domain_string))
        organization_domain_match_count = organization_list_query.count()
        if positive_value_exists(organization_domain_match_count):
            status += "FULL_DOMAIN_STRING_FOUND-OWNED_BY_ORGANIZATION "
            results = {
                'full_domain_string_available': False,
                'status': status,
                'success': True,
            }
            return results
    except Exception as e:
        status += 'PROBLEM_QUERYING_ORGANIZATION_TABLE {error} [type: {error_type}] ' \
                  ''.format(error=str(e), error_type=type(e))
        results = {
            'full_domain_string_available': False,
            'status':                       status,
            'success':                      False,
        }
        return results

    # Double-check that we don't have a reserved entry already in the OrganizationReservedDomain table
    try:
        reserved_domain_list_query = OrganizationReservedDomain.objects.using('readonly').all()
        reserved_domain_list_query = reserved_domain_list_query.filter(full_domain_string__iexact=full_domain_string)
        reserved_domain_match_count = reserved_domain_list_query.count()
        if positive_value_exists(reserved_domain_match_count):
            status += "FULL_DOMAIN_STRING_FOUND-RESERVED "
            results = {
                'full_domain_string_available': False,
                'status': status,
                'success': True,
            }
            return results
    except Exception as e:
        status += 'PROBLEM_QUERYING_ORGANIZATION_RESERVED_DOMAIN_TABLE {error} [type: {error_type}] ' \
                  ''.format(error=e, error_type=type(e))
        results = {
            'full_domain_string_available': False,
            'status':                       status,
            'success':                      False,
        }
        return results

    status += "FULL_DOMAIN_STRING_AVAILABLE "
    results = {
        'full_domain_string_available': True,
        'status': status,
        'success': True,
    }
    return results


def subdomain_string_available(subdomain_string, requesting_organization_id):
    """
    Make sure this sub domain name (website address) isn't already taken
    :param subdomain_string:
    :param requesting_organization_id:
    :return:
    """
    status = ""
    if not positive_value_exists(subdomain_string):
        status += "MISSING_SUBDOMAIN_STRING "
        results = {
            'subdomain_string_available':   False,
            'status':                       status,
            'success':                      False,
        }
        return results
    try:
        organization_list_query = Organization.objects.using('readonly').all()
        organization_list_query = organization_list_query.exclude(id=requesting_organization_id)
        organization_list_query = organization_list_query.filter(chosen_subdomain_string__iexact=subdomain_string)
        organization_domain_match_count = organization_list_query.count()
        if positive_value_exists(organization_domain_match_count):
            status += "SUBDOMAIN_STRING_FOUND-OWNED_BY_ORGANIZATION "
            results = {
                'subdomain_string_available':   False,
                'status':                       status,
                'success':                      True,
            }
            return results
    except Exception as e:
        status += 'PROBLEM_QUERYING_ORGANIZATION_TABLE {error} [type: {error_type}] ' \
                  ''.format(error=e, error_type=type(e))
        results = {
            'subdomain_string_available':   False,
            'status':                       status,
            'success':                      False,
        }
        return results

    # Double-check that we don't have a reserved entry already in the OrganizationReservedDomain table
    try:
        reserved_domain_list_query = OrganizationReservedDomain.objects.using('readonly').all()
        reserved_domain_list_query = reserved_domain_list_query.filter(subdomain_string__iexact=subdomain_string)
        reserved_domain_match_count = reserved_domain_list_query.count()
        if positive_value_exists(reserved_domain_match_count):
            status += "SUBDOMAIN_STRING_FOUND-RESERVED "
            results = {
                'subdomain_string_available':   False,
                'status':                       status,
                'success':                      True,
            }
            return results
    except Exception as e:
        status += 'PROBLEM_QUERYING_ORGANIZATION_RESERVED_DOMAIN_TABLE {error} [type: {error_type}] ' \
                  ''.format(error=e, error_type=type(e))
        results = {
            'subdomain_string_available':   False,
            'status':                       status,
            'success':                      False,
        }
        return results

    status += "SUBDOMAIN_STRING_AVAILABLE "
    results = {
        'subdomain_string_available':   True,
        'status':                       status,
        'success':                      True,
    }
    return results


def organization_analytics_by_voter_for_api(voter_device_id='',
                                            organization_we_vote_id='', organization_api_pass_code='',
                                            external_voter_id='', voter_we_vote_id='',
                                            google_civic_election_id=0):
    status = ""
    success = True
    is_signed_into_organization_account = False
    election_list = []
    voter_list = []

    voter_manager = VoterManager()
    status += "ORGANIZATION_ANALYTICS_BY_VOTER "
    if positive_value_exists(voter_device_id):
        read_only = True
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            linked_organization_we_vote_id = voter.linked_organization_we_vote_id
            if not positive_value_exists(organization_we_vote_id):
                organization_we_vote_id = linked_organization_we_vote_id
            elif organization_we_vote_id == linked_organization_we_vote_id:
                is_signed_into_organization_account = True

    if not positive_value_exists(organization_we_vote_id):
        status += "ORGANIZATION_WE_VOTE_ID_MISSING "
        success = False
        results = {
            'success':                  success,
            'status':                   status,
            'organization_we_vote_id':  organization_we_vote_id,
            'voter_list':               voter_list,
        }
        return results

    has_authorization_variables_required = is_signed_into_organization_account \
        or positive_value_exists(organization_api_pass_code)
    if not has_authorization_variables_required:
        status += "ORGANIZATION_PASS_CODE_MISSING "
        success = False
        results = {
            'success':                  success,
            'status':                   status,
            'organization_we_vote_id':  organization_we_vote_id,
            'voter_list':               voter_list,
        }
        return results

    organization_manager = OrganizationManager()
    if is_signed_into_organization_account:
        results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if results['organization_found']:
            organization_found = True
            organization = results['organization']
        else:
            status += "ORGANIZATION_ANALYTICS_BY_VOTER_NOT_FOUND "
            results = {
                'success':                  success,
                'status':                   status,
                'organization_we_vote_id':  organization_we_vote_id,
                'voter_list':               voter_list,
            }
            return results
    else:
        results = organization_manager.retrieve_organization_from_we_vote_id_and_pass_code(
            organization_we_vote_id, organization_api_pass_code)
        if results['organization_found']:
            organization_found = True
            organization = results['organization']
        else:
            status += "ORGANIZATION_ANALYTICS_BY_VOTER_NOT_FOUND_WITH_PASS_CODE "
            results = {
                'success':                  success,
                'status':                   status,
                'organization_we_vote_id':  organization_we_vote_id,
                'voter_list':               voter_list,
                'election_list':            election_list,
            }
            return results

    voter_we_vote_id_list = []
    if positive_value_exists(external_voter_id) and not positive_value_exists(voter_we_vote_id):
        link_query = OrganizationMembershipLinkToVoter.objects.all()
        link_query = link_query.filter(organization_we_vote_id=organization_we_vote_id)
        link_query = link_query.filter(external_voter_id=external_voter_id)
        link_list = list(link_query)
        if len(link_list) == 0:
            voter_we_vote_id_list = ['EXTERNAL_VOTER_ID_NOT_FOUND']
            status += "NO_VOTERS_FOUND_WITH_EXTERNAL_ID: " + str(external_voter_id) + " "
        else:
            for external_voter in link_list:
                voter_we_vote_id_list.append(external_voter.voter_we_vote_id)
    elif positive_value_exists(voter_we_vote_id):
        voter_we_vote_id_list = [voter_we_vote_id]

    elections_retrieved_from_database = {}
    analytics_manager = AnalyticsManager()
    election_manager = ElectionManager()
    results = analytics_manager.retrieve_analytics_action_list(
        voter_we_vote_id_list=voter_we_vote_id_list,
        google_civic_election_id=google_civic_election_id,
        organization_we_vote_id=organization_we_vote_id,
        action_constant=ACTION_BALLOT_VISIT,
        distinct_for_members=True)
    election_participation_list = results['analytics_action_list']
    # Split up this one list into multiple lists, organized by voter
    election_participation_dict_with_we_vote_id_lists = {}
    election_participation_dict_with_external_id_lists = {}
    for election_participation in election_participation_list:
        link_query = OrganizationMembershipLinkToVoter.objects.all()
        link_query = link_query.filter(organization_we_vote_id=organization_we_vote_id)
        link_query = link_query.filter(voter_we_vote_id__iexact=election_participation.voter_we_vote_id)
        link_list = list(link_query)
        if len(link_list) > 0:
            for external_voter in link_list:
                if positive_value_exists(external_voter_id):
                    # If one external_voter_id was requested, only return that one
                    if external_voter_id == external_voter.external_voter_id:
                        if external_voter.external_voter_id not in election_participation_dict_with_external_id_lists:
                            election_participation_dict_with_external_id_lists[external_voter.external_voter_id] = []
                        election_participation_dict_with_external_id_lists[external_voter.external_voter_id].append(
                            election_participation)
                else:
                    if external_voter.external_voter_id not in election_participation_dict_with_external_id_lists:
                        election_participation_dict_with_external_id_lists[external_voter.external_voter_id] = []
                    election_participation_dict_with_external_id_lists[external_voter.external_voter_id].append(
                        election_participation)
        else:
            if election_participation.voter_we_vote_id not in election_participation_dict_with_we_vote_id_lists:
                election_participation_dict_with_we_vote_id_lists[election_participation.voter_we_vote_id] = []
            election_participation_dict_with_we_vote_id_lists[election_participation.voter_we_vote_id].\
                append(election_participation)

    # Cycle through each voter pivoting on external_voter_id
    for external_voter_id_key in election_participation_dict_with_external_id_lists.keys():
        election_participation_list_for_one_voter = \
            election_participation_dict_with_external_id_lists[external_voter_id_key]
        this_election_already_seen_by_voter = []  # Reset for each voter
        elections_visited = []
        voter_we_vote_id_from_analytics = ''
        for election_participation in election_participation_list_for_one_voter:
            if not positive_value_exists(election_participation.google_civic_election_id):
                continue
            voter_we_vote_id_from_analytics = election_participation.voter_we_vote_id
            if election_participation.google_civic_election_id not in elections_retrieved_from_database:
                election_results = election_manager.retrieve_election(election_participation.google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    elections_retrieved_from_database[election_participation.google_civic_election_id] = election
            if election_participation.google_civic_election_id not in this_election_already_seen_by_voter:
                this_election_already_seen_by_voter.append(election_participation.google_civic_election_id)
                election_visited_dict = {
                    'election_id': election_participation.google_civic_election_id,
                }
                elections_visited.append(election_visited_dict)

        one_voter_dict = {
            'external_voter_id':    external_voter_id_key,
            'voter_we_vote_id':     voter_we_vote_id_from_analytics,
            'elections_visited':    elections_visited,
        }
        voter_list.append(one_voter_dict)

    # Now cycle through each voter with only voter_we_vote_id
    for voter_we_vote_id_key in election_participation_dict_with_we_vote_id_lists.keys():
        election_participation_list_for_one_voter = \
            election_participation_dict_with_we_vote_id_lists[voter_we_vote_id_key]
        this_election_already_seen_by_voter = []  # Reset for each voter
        elections_visited = []
        voter_we_vote_id_from_analytics = ''
        for election_participation in election_participation_list_for_one_voter:
            if not positive_value_exists(election_participation.google_civic_election_id):
                continue
            voter_we_vote_id_from_analytics = election_participation.voter_we_vote_id
            if election_participation.google_civic_election_id not in elections_retrieved_from_database:
                election_results = election_manager.retrieve_election(election_participation.google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    elections_retrieved_from_database[election_participation.google_civic_election_id] = election
            if election_participation.google_civic_election_id not in this_election_already_seen_by_voter:
                this_election_already_seen_by_voter.append(election_participation.google_civic_election_id)
                election_visited_dict = {
                    'election_id': election_participation.google_civic_election_id,
                }
                elections_visited.append(election_visited_dict)

        if positive_value_exists(voter_we_vote_id_from_analytics):
            external_voter_id = organization_manager.fetch_external_voter_id(
                organization_we_vote_id, voter_we_vote_id_from_analytics)
            one_voter_dict = {
                'external_voter_id':    external_voter_id,
                'voter_we_vote_id':     voter_we_vote_id_from_analytics,
                'elections_visited':    elections_visited,
            }
            voter_list.append(one_voter_dict)

    for election_id in elections_retrieved_from_database.keys():
        election = elections_retrieved_from_database[election_id]
        election_dict = {
            'election_id': election.google_civic_election_id,
            'election_name': election.election_name,
            'election_date': election.election_day_text,
            'election_state': election.state_code,
        }
        election_list.append(election_dict)
    results = {
        'success':                  success,
        'status':                   status,
        'organization_we_vote_id':  organization_we_vote_id,
        'election_list':            election_list,
        'voter_list':               voter_list,
    }
    return results


def organization_retrieve_tweets_from_twitter(organization_we_vote_id):
    """
    For one organization, retrieve X Tweets, and capture all #Hashtags used.
    Sample code: Search for tweepy http://tweepy.readthedocs.io/en/v3.5.0/

    :param organization_we_vote_id:
    :return:
    """
    success = True
    status = ""
    counter = None
    tweets_saved = None
    tweets_not_saved = None

    if not positive_value_exists(organization_we_vote_id):
        status = "ORGANIZATION_WE_VOTE_ID_MISSING"
        success = False
        results = {
            'success':          success,
            'status':           status,
            'tweets_saved':     tweets_saved,
            'tweets_not_saved': tweets_not_saved
        }
        return results

    # December 2021: Using the Twitter 1.1 API for user_timeline, since it is not yet available in 2.0
    # https://developer.twitter.com/en/docs/twitter-api/migrate/twitter-api-endpoint-map
    print("tweepy OAuth1UserHandler (Old API, probably in deprecated code) in organization_retrieve_tweets_from_twitter"
          " -- organization_we_vote_id: ", organization_we_vote_id)
    auth = tweepy.OAuth1UserHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)   # This uses the Twitter apiv1, not the apiv2

    organization_manager = OrganizationManager()
    new_tweets = []
    try:
        organization_twitter_id = organization_manager.fetch_twitter_handle_from_organization_we_vote_id(
            organization_we_vote_id)
        print("tweepy api.user_timeline (Old API, probably in deprecated code) in "
              "organization_retrieve_tweets_from_twitter -- organization_we_vote_id: ", organization_we_vote_id)
        counter = create_detailed_counter_entry('user_timeline', 'organization_retrieve_tweets_from_twitter', success,
                                                {'voter_we_vote_id': organization_we_vote_id,
                                                'text': 'Suspect that this code is deprecated'})

        new_tweets = api.user_timeline(username=organization_twitter_id)
    except tweepy.TooManyRequests:
        success = False
        status = 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_RATE_LIMIT_ERROR '
        mark_detailed_counter_entry(counter, success, status)
    except tweepy.errors.HTTPException as e:
        status = "ORGANIZATION_RETRIEVE_TWEETS_FROM_TWITTER_AUTH_FAIL_HTTPException: " + str(e) + " "
        success = False
        results = {
            'success': success,
            'status': status,
            'tweets_saved': tweets_saved,
            'tweets_not_saved': tweets_not_saved
        }
        mark_detailed_counter_entry(counter, success, status)
        return results
    except tweepy.TweepyException as e:
        status = "ORGANIZATION_RETRIEVE_TWEETS_FROM_TWITTER_AUTH_FAIL: " + str(e) + " "
        success = False
        mark_detailed_counter_entry(counter, success, status)
        results = {
            'success': success,
            'status': status,
            'tweets_saved': tweets_saved,
            'tweets_not_saved': tweets_not_saved
        }
        return results
    except Exception as e:
        success = False
        status += "ORGANIZATION_RETRIEVE_TWEETS_FROM_TWITTER_AUTH_FAIL_TWEEPY_EXCEPTION: " + str(e) + " "

    twitter_user_manager = TwitterUserManager()
    tweets_saved = 0
    tweets_not_saved = 0
    for tweet_json in new_tweets:
        results = twitter_user_manager.update_or_create_tweet(tweet_json, organization_we_vote_id)
        if results['success']:
            tweets_saved += 1
        else:
            tweets_not_saved += 1
            success = False

    results = {
        'success':          success,
        'status':           status,
        'tweets_saved':     tweets_saved,
        'tweets_not_saved': tweets_not_saved,
    }
    return results


def organization_analyze_tweets(organization_we_vote_id):
    """
    For one organization, retrieve X Tweets, and capture all #Hashtags used.
    Loop through Tweets and create OrganizationLinkToHashtag and OrganizationLinkToWordOrPhrase

    :param organization_we_vote_id:
    :return:
    """
    status = ""
    success = True
    hastags_retrieved = None
    cached_tweets = None
    unique_hashtags = None
    organization_link_to_hashtag_results = None

    if not positive_value_exists(organization_we_vote_id):
        success = False
        results = {
            'status': status,
            'success': success,
            'hash_tags_retrieved': hastags_retrieved,
            'cached_tweets': cached_tweets,
            'unique_hashtags': unique_hashtags,
            'organization_link_to_hashtag_results': organization_link_to_hashtag_results,
        }
        return results

    twitter_user_manager = TwitterUserManager()
    retrieve_tweets_cached_locally_results = twitter_user_manager.retrieve_tweets_cached_locally(
        organization_we_vote_id)
    if not retrieve_tweets_cached_locally_results['success']:
        status += retrieve_tweets_cached_locally_results['status']
        success = False
    if retrieve_tweets_cached_locally_results['status'] == 'NO_TWEETS_FOUND':
        status = "NO_TWEETS_CACHED_LOCALLY",
        results = {
            'status':                               status,
            'success':                              success,
            'hash_tags_retrieved':                  hastags_retrieved,
            'cached_tweets':                        cached_tweets,
            'unique_hashtags':                      unique_hashtags,
            'organization_link_to_hashtag_results': organization_link_to_hashtag_results,
        }
        return results
    cached_tweets = retrieve_tweets_cached_locally_results["tweet_list"]
    all_hashtags = []

    for i in range(0, len(cached_tweets)):
        if re.findall(r"#(\w+)", cached_tweets[i].tweet_text):
            all_hashtags.append(re.findall(r"#(\w+)", cached_tweets[i].tweet_text))

    all_hashtags_list = []  # all_hashtags is a nested list, flattened here prior to building frequency distribution
    [[all_hashtags_list.append(hashtag) for hashtag in hashtag_list]for hashtag_list in all_hashtags]
    unique_hashtags_count_dict = dict(zip(all_hashtags_list, [0] * len(all_hashtags_list)))
    for hashtag in all_hashtags_list:
        unique_hashtags_count_dict[hashtag] += 1

    hashtags_retrieved = len(all_hashtags)
    cached_tweets = len(cached_tweets)
    unique_hashtags = len(unique_hashtags_count_dict)

    # TODO (eayoungs@gmail.com) This is Abed's code; left to be considered for future work
    # This is giving a weird output!
    # Populate a dictionary with the frequency of words in all tweets 
    # counts = dict()
    # for tweet in tweet_list:
    #    words = str(tweet.tweet_text).split()
    #    # return tweet.tweet_text, str(tweet.tweet_text).split(), tweet.tweet_text.split(), words
    #    for word in words:
    #        if word in counts:
    #            counts[word] += 1
    #        else:
    #            counts[word] = 1

    # THIS PART IS STILL UNDERDEV
    # organization_link_to_hashtag = OrganizationLinkToHashtag()
    # organization_link_to_hashtag.organization_we_vote_id = organization_we_vote_id

    organization_manager = OrganizationManager()
    for key, value in unique_hashtags_count_dict.items():
        organization_link_to_hashtag_results = organization_manager.update_or_create_organization_link_to_hashtag(
            organization_we_vote_id, key)

    results = {
        'status':                               status,
        'success':                              success,
        'hash_tags_retrieved':                  hashtags_retrieved,
        'cached_tweets':                        cached_tweets,
        'unique_hashtags':                      unique_hashtags,
        'organization_link_to_hashtag_results': organization_link_to_hashtag_results,
    }
    return results


def merge_these_two_organizations(organization1_we_vote_id, organization2_we_vote_id, admin_merge_choices={}):
    """
    Process the merging of two organizations. Note: Organization1 is saved at the end. Organization2 is deleted at end.
    :param organization1_we_vote_id:
    :param organization2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :return:
    """
    status = ""
    organization_manager = OrganizationManager()
    voter_manager = VoterManager()

    # Check to make sure that organization2 isn't linked to a voter. If so, cancel out for now.
    results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization2_we_vote_id, read_only=True)
    if results['voter_found']:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_ORGANIZATIONS-ORGANIZATION2_LINKED_TO_A_VOTER ",
            'organizations_merged': False,
            'organization': None,
        }
        return results

    # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
    organization1_results = \
        organization_manager.retrieve_organization_from_we_vote_id(organization1_we_vote_id)
    if organization1_results['organization_found']:
        organization1_on_stage = organization1_results['organization']
        organization1_id = organization1_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_ORGANIZATIONS-COULD_NOT_RETRIEVE_ORGANIZATION1 ",
            'organizations_merged': False,
            'organization': None,
        }
        return results

    organization2_results = \
        organization_manager.retrieve_organization_from_we_vote_id(organization2_we_vote_id)
    if organization2_results['organization_found']:
        organization2_on_stage = organization2_results['organization']
        organization2_id = organization2_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_ORGANIZATIONS-COULD_NOT_RETRIEVE_ORGANIZATION2 ",
            'organizations_merged': False,
            'organization': None,
        }
        return results

    # TODO: Migrate images?

    # Merge attribute values chosen by the admin
    org2_attributes_to_be_removed = False
    for attribute in ORGANIZATION_UNIQUE_IDENTIFIERS:
        try:
            if attribute in admin_merge_choices:
                setattr(organization1_on_stage, attribute, admin_merge_choices[attribute])
                # Clear out the attributes in organization2_on_stage which need to be unique in the database
                if hasattr(organization2_on_stage, attribute) and attribute in ['vote_smart_id', 'fb_username']:
                    org2_attributes_to_be_removed = True
                    setattr(organization2_on_stage, attribute, None)
        except Exception as e:
            # Break out
            status += "ATTRIBUTE_SETATTR_FAILED (" + str(attribute) + "): " + str(e) + " "
            results = {
                'success': False,
                'status': status,
                'organizations_merged': False,
                'organization': None,
            }
            return results

    # Remove attributes in organization2 which must be unique
    if org2_attributes_to_be_removed:
        try:
            organization2_on_stage.save()
        except Exception as e:
            status += "ORG2_ATTRIBUTE_CLEAR_FAILED: " + str(e) + " "

    # Merge public positions
    public_positions_results = move_positions_to_another_organization(
        from_organization_id=organization2_id,
        from_organization_we_vote_id=organization2_we_vote_id,
        to_organization_id=organization1_id,
        to_organization_we_vote_id=organization1_we_vote_id)
    if not public_positions_results['success'] \
            or positive_value_exists(public_positions_results['position_entries_not_moved']) \
            or positive_value_exists(public_positions_results['position_entries_not_deleted']):
        status += public_positions_results['status']
        status += "MERGE_THESE_TWO_ORGANIZATIONS-COULD_NOT_MOVE_PUBLIC_POSITIONS_TO_ORGANIZATION1 "
        results = {
            'success': False,
            'status': status,
            'organizations_merged': False,
            'organization': None,
        }
        return results

    # Merge friends-only positions
    friends_positions_results = move_positions_to_another_organization(
        organization2_id, organization2_we_vote_id,
        organization1_id, organization1_we_vote_id,
        False)
    if not friends_positions_results['success'] \
            or positive_value_exists(public_positions_results['position_entries_not_moved']) \
            or positive_value_exists(public_positions_results['position_entries_not_deleted']):
        status += friends_positions_results['status']
        status += "MERGE_THESE_TWO_ORGANIZATIONS-COULD_NOT_MOVE_FRIENDS_POSITIONS_TO_ORGANIZATION1 "
        results = {
            'success': False,
            'status': status,
            'organizations_merged': False,
            'organization': None,
        }
        return results

    # Note: wait to wrap in try/except block
    organization1_on_stage.save()
    refresh_organization_data_from_master_tables(organization1_on_stage.we_vote_id)

    # Remove organization 2
    organization2_on_stage.delete()

    results = {
        'success': True,
        'status': status,
        'organizations_merged': True,
        'organization': organization1_on_stage,
    }
    return results


def move_membership_link_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    voter_member_entries_moved = 0
    voter_member_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_MEMBERSHIP_LINK_ENTRIES_TO_ANOTHER_VOTER-" \
                  "Missing either from_voter_we_vote_id or to_voter_we_vote_id "
        success = False
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_we_vote_id':    from_voter_we_vote_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'voter_member_entries_moved':     voter_member_entries_moved,
            'voter_member_entries_not_moved': voter_member_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_MEMBERSHIP_LINK_ENTRIES_TO_ANOTHER_VOTER-" \
                  "from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_we_vote_id':    from_voter_we_vote_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'voter_member_entries_moved':     voter_member_entries_moved,
            'voter_member_entries_not_moved': voter_member_entries_not_moved,
        }
        return results

    voter_members_query = OrganizationMembershipLinkToVoter.objects.all()
    voter_members_query = voter_members_query.filter(
        voter_we_vote_id__iexact=from_voter_we_vote_id)
    voter_members_list = list(voter_members_query)
    for voter_member_link in voter_members_list:
        try:
            voter_member_link.voter_we_vote_id = to_voter_we_vote_id
            voter_member_link.save()
            voter_member_entries_moved += 1
        except Exception as e:
            status += "COULD_NOT_SAVE_ORGANIZATION_MEMBERSHIP_LINK: " + str(e) + ' '
            success = False
            voter_member_entries_not_moved += 1

    results = {
        'status':                   status,
        'success':                  success,
        'from_voter_we_vote_id':    from_voter_we_vote_id,
        'to_voter_we_vote_id':      to_voter_we_vote_id,
        'voter_member_entries_moved':     voter_member_entries_moved,
        'voter_member_entries_not_moved': voter_member_entries_not_moved,
    }
    return results


def move_organization_data_to_another_organization(from_organization_we_vote_id, to_organization_we_vote_id):
    status = ""
    success = True
    from_organization = None
    to_organization = None
    to_organization_found = False
    data_transfer_complete = False

    if not positive_value_exists(from_organization_we_vote_id):
        results = {
            'status': 'MOVE_ORGANIZATION-FROM_ORGANIZATION_WE_VOTE_ID_MISSING ',
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'to_organization_found': to_organization_found,
            'data_transfer_complete': data_transfer_complete,
        }
        return results

    if not positive_value_exists(to_organization_we_vote_id):
        results = {
            'status': 'MOVE_ORGANIZATION-TO_ORGANIZATION_WE_VOTE_ID_MISSING ',
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'to_organization_found': to_organization_found,
            'data_transfer_complete': data_transfer_complete,
        }
        return results

    organization_manager = OrganizationManager()
    from_organization_results = organization_manager.retrieve_organization_from_we_vote_id(from_organization_we_vote_id)
    if from_organization_results['organization_found']:
        from_organization = from_organization_results['organization']
    else:
        status += 'MOVE_ORGANIZATION_DATA_COULD_NOT_RETRIEVE_FROM_ORGANIZATION: ' \
            + str(from_organization_we_vote_id) + ": " + from_organization_results['status']
        results = {
            'status': status,
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'to_organization_found': to_organization_found,
            'data_transfer_complete': False,
        }
        return results

    to_organization_results = organization_manager.retrieve_organization_from_we_vote_id(to_organization_we_vote_id)
    if to_organization_results['organization_found']:
        to_organization_found = True
        to_organization = to_organization_results['organization']
    else:
        status += 'MOVE_ORGANIZATION_DATA_COULD_NOT_RETRIEVE_TO_ORGANIZATION: ' \
            + str(to_organization_we_vote_id) + " " + to_organization_results['status']
        results = {
            'status': status,
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'to_organization_found': to_organization_found,
            'data_transfer_complete': False,
        }
        return results

    # If here we know that we have both from_organization and to_organization
    save_to_organization = False
    if transfer_to_organization_if_missing(from_organization, to_organization, 'ballotpedia_page_title'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'ballotpedia_photo_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'facebook_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'facebook_email'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'facebook_profile_image_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'fb_username'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_website'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_email'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_contact_form_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_contact_name'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_facebook'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_image'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'state_served_code'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'vote_smart_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_description'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_address'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_city'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_state'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_zip'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_phone1'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_phone2'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_fax'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_type'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_endorsements_api_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_user_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_twitter_handle'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_name'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_location'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_followers_count'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_profile_image_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization,
                                           'twitter_profile_background_image_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_profile_banner_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_description'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization,
                                           'we_vote_hosted_profile_image_url_large'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization,
                                           'we_vote_hosted_profile_image_url_medium'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'we_vote_hosted_profile_image_url_tiny'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_page_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_page_title'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_thumbnail_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_thumbnail_width'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_thumbnail_height'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_photo_url'):
        save_to_organization = True

    if save_to_organization:
        try:
            to_organization.save()
            to_organization_found = True
            data_transfer_complete = True
        except Exception as e:
            status += "COULD_NOT_SAVE_TO_ORGANIZATION: " + str(e) + " "
            success = False
    else:
        data_transfer_complete = True

    results = {
        'status': status,
        'success': success,
        'from_organization': from_organization,
        'to_organization': to_organization,
        'to_organization_found': to_organization_found,
        'data_transfer_complete': data_transfer_complete,
    }
    return results


def move_organization_team_member_entries_to_another_organization(
        from_organization_we_vote_id,
        to_organization_we_vote_id):
    status = ''
    success = True
    organization_team_member_entries_moved = 0

    if not positive_value_exists(from_organization_we_vote_id) or not positive_value_exists(to_organization_we_vote_id):
        status += "MOVE_ORG_TEAM_MEMBER-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                                   status,
            'success':                                  success,
            'from_organization_we_vote_id':             from_organization_we_vote_id,
            'to_organization_we_vote_id':               to_organization_we_vote_id,
            'organization_team_member_entries_moved':   organization_team_member_entries_moved,
        }
        return results

    if from_organization_we_vote_id == to_organization_we_vote_id:
        status += "MOVE_ORG_TEAM_MEMBER-FROM_AND_TO_ORGANIZATION_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                                   status,
            'success':                                  success,
            'from_organization_we_vote_id':             from_organization_we_vote_id,
            'to_organization_we_vote_id':               to_organization_we_vote_id,
            'organization_team_member_entries_moved':   organization_team_member_entries_moved,
        }
        return results

    # #############################################
    # Move based on organization_we_vote_id
    try:
        organization_team_member_entries_moved += OrganizationTeamMember.objects \
            .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .update(organization_we_vote_id=to_organization_we_vote_id)
    except Exception as e:
        status += "FAILED-ORG_TEAM_MEMBER_UPDATE_ORG-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        success = False

    results = {
        'status':                                   status,
        'success':                                  success,
        'from_organization_we_vote_id':             from_organization_we_vote_id,
        'to_organization_we_vote_id':               to_organization_we_vote_id,
        'organization_team_member_entries_moved':   organization_team_member_entries_moved,
    }
    return results


def move_organization_team_member_entries_to_another_voter(
        from_voter_we_vote_id,
        to_voter_we_vote_id,
        from_organization_we_vote_id,
        to_organization_we_vote_id,
        to_organization_name=''):
    status = ''
    success = True
    organization_team_member_entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        # We still proceed even if we don't have organization_we_vote_id's
        status += "MOVE_ORG_TEAM_MEMBER-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                                   status,
            'success':                                  success,
            'from_voter_we_vote_id':                    from_voter_we_vote_id,
            'to_voter_we_vote_id':                      to_voter_we_vote_id,
            'organization_team_member_entries_moved':   organization_team_member_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_ORG_TEAM_MEMBER-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                                   status,
            'success':                                  success,
            'from_voter_we_vote_id':                    from_voter_we_vote_id,
            'to_voter_we_vote_id':                      to_voter_we_vote_id,
            'organization_team_member_entries_moved':   organization_team_member_entries_moved,
        }
        return results

    # ######################
    # Move based on voter_we_vote_id
    try:
        organization_team_member_entries_moved += OrganizationTeamMember.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-ORG_TEAM_MEMBER_VOTER_UPDATE: " + str(e) + " "

    if positive_value_exists(from_organization_we_vote_id) and positive_value_exists(to_organization_we_vote_id):
        # #############################################
        # Move based on team_member_organization_we_vote_id
        if positive_value_exists(to_organization_name):
            try:
                organization_team_member_entries_moved += OrganizationTeamMember.objects \
                    .filter(team_member_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                    .update(organization_name=to_organization_name,
                            team_member_organization_we_vote_id=to_organization_we_vote_id)
            except Exception as e:
                status += "FAILED-ORG_TEAM_MEMBER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
        else:
            try:
                organization_team_member_entries_moved += OrganizationTeamMember.objects \
                    .filter(team_member_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                    .update(team_member_organization_we_vote_id=to_organization_we_vote_id)
            except Exception as e:
                status += "FAILED-ORG_TEAM_MEMBER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        # #############################################
        # Move based on organization_we_vote_id
        try:
            organization_team_member_entries_moved += OrganizationTeamMember.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-ORG_TEAM_MEMBER_UPDATE_ORG-FROM_ORG_WE_VOTE_ID: " + str(e) + " "

    results = {
        'status':                                   status,
        'success':                                  success,
        'from_voter_we_vote_id':                    from_voter_we_vote_id,
        'to_voter_we_vote_id':                      to_voter_we_vote_id,
        'organization_team_member_entries_moved':   organization_team_member_entries_moved,
    }
    return results


def move_organization_to_another_complete(
        from_organization_id,
        from_organization_we_vote_id,
        to_organization_id,
        to_organization_we_vote_id,
        to_voter_id,
        to_voter_we_vote_id):
    status = ""
    success = True
    to_organization_found = False
    to_organization = None

    # Make sure we have both from_organization values
    organization_manager = OrganizationManager()
    if positive_value_exists(from_organization_id) and not positive_value_exists(from_organization_we_vote_id):
        from_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(from_organization_id)
    elif positive_value_exists(from_organization_we_vote_id) and not positive_value_exists(from_organization_id):
        from_organization_id = organization_manager.fetch_organization_id(from_organization_we_vote_id)

    # Make sure we have both to_organization values
    if positive_value_exists(to_organization_id) and not positive_value_exists(to_organization_we_vote_id):
        to_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(to_organization_id)
    elif positive_value_exists(to_organization_we_vote_id) and not positive_value_exists(to_organization_id):
        to_organization_id = organization_manager.fetch_organization_id(to_organization_we_vote_id)

    # Make sure we have both to_voter values
    voter_manager = VoterManager()
    if positive_value_exists(to_voter_id) and not positive_value_exists(to_voter_we_vote_id):
        to_voter_we_vote_id = voter_manager.fetch_we_vote_id_from_local_id(to_voter_id)
    elif positive_value_exists(to_voter_we_vote_id) and not positive_value_exists(to_voter_id):
        to_voter_id = voter_manager.fetch_local_id_from_we_vote_id(to_voter_we_vote_id)

    identical_variables = False
    if from_organization_id == to_organization_id:
        status += "MOVE_ORGANIZATION_TO_ANOTHER_COMPLETE-from_organization_id and to_organization_id identical "
        identical_variables = True
    if from_organization_we_vote_id == to_organization_we_vote_id:
        status += "MOVE_ORGANIZATION_TO_ANOTHER_COMPLETE-" \
                  "from_organization_we_vote_id and to_organization_we_vote_id identical "
        identical_variables = True

    if identical_variables:
        results = {
            'status':                   status,
            'success':                  success,
            'to_organization_found':    to_organization_found,
            'to_organization':          to_organization,
        }
        return results

    # If anyone is following the old voter's organization, move those followers to the new voter's organization
    move_organization_followers_results = move_organization_followers_to_another_organization(
        from_organization_id, from_organization_we_vote_id,
        to_organization_id, to_organization_we_vote_id)
    status += " " + move_organization_followers_results['status']
    if not move_organization_followers_results['success']:
        success = False

    # If anyone has been linked with external_voter_id as a member of the old voter's organization,
    #  move those followers to the new voter's organization
    move_organization_membership_link_results = move_organization_membership_link_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_organization_membership_link_results['status']
    if not move_organization_membership_link_results['success']:
        success = False

    move_organization_team_member_results = move_organization_team_member_entries_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_organization_team_member_results['status']
    if not move_organization_team_member_results['success']:
        success = False

    # Transfer positions from "from" organization to the "to" organization
    move_positions_to_another_org_results = move_positions_to_another_organization(
        from_organization_id,
        from_organization_we_vote_id,
        to_organization_id,
        to_organization_we_vote_id,
        to_voter_id,
        to_voter_we_vote_id)
    status += " " + move_positions_to_another_org_results['status']
    if not move_positions_to_another_org_results['success']:
        success = False

    move_donation_results = move_donation_info_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_donation_results['status']
    if not move_donation_results['success']:
        success = False

    # There might be some useful information in the from_voter's organization that needs to be moved
    move_organization_results = move_organization_data_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_organization_results['status']
    if not move_organization_results['success']:
        success = False
    if positive_value_exists(move_organization_results['to_organization_found']):
        to_organization_found = True
        to_organization = move_organization_results['to_organization']
        to_organization_name = to_organization.organization_name

        move_campaignx_results = move_campaignx_to_another_organization(
            from_organization_we_vote_id, to_organization_we_vote_id, to_organization_name)
        status += " " + move_campaignx_results['status']
        if not move_campaignx_results['success']:
            success = False

    # Finally, delete the from_voter's organization
    if success and move_organization_results['data_transfer_complete']:
        from_organization = move_organization_results['from_organization']
        try:
            from_organization.delete()
        except Exception as e:
            status += "UNABLE_TO_DELETE_FROM_ORGANIZATION: " + str(e) + " "
            success = False

    # We need to make sure to update voter.linked_organization_we_vote_id outside this routine

    results = {
        'status':                   status,
        'success':                  success,
        'to_organization_found':    to_organization_found,
        'to_organization':          to_organization,
    }
    return results


def move_organization_membership_link_to_another_organization(from_organization_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = True
    membership_link_entries_moved = 0
    membership_link_entries_not_moved = 0

    organization_members_query = OrganizationMembershipLinkToVoter.objects.all()
    organization_members_query = organization_members_query.filter(
        organization_we_vote_id__iexact=from_organization_we_vote_id)
    organization_members_list = list(organization_members_query)
    for organization_member_link in organization_members_list:
        try:
            organization_member_link.organization_we_vote_id = to_organization_we_vote_id
            organization_member_link.save()
            membership_link_entries_moved += 1
        except Exception as e:
            membership_link_entries_not_moved += 1
            status += "COULD_NOT_UPDATE_MEMBER_LINK: " + str(e) + " "
            success = False

    results = {
        'status': status,
        'success': success,
        'from_organization_we_vote_id': from_organization_we_vote_id,
        'to_organization_we_vote_id': to_organization_we_vote_id,
        'membership_link_entries_moved': membership_link_entries_moved,
        'membership_link_entries_not_moved': membership_link_entries_not_moved,
    }
    return results


def transfer_voter_images_to_organization(voter):
    status = ''
    success = True
    try:
        if voter.linked_organization_we_vote_id:
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization_from_we_vote_id(voter.linked_organization_we_vote_id)
            if not results['success']:
                status += results['status']
                success = False
            if results['organization_found']:
                organization = results['organization']
                organization.we_vote_hosted_profile_image_url_large = voter.we_vote_hosted_profile_image_url_large
                organization.we_vote_hosted_profile_image_url_medium = voter.we_vote_hosted_profile_image_url_medium
                organization.we_vote_hosted_profile_image_url_tiny = voter.we_vote_hosted_profile_image_url_tiny
                organization.save()
    except Exception as e:
        status += "FAILED_TO_TRANSFER_IMAGES: " + str(e) + " "
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def transfer_to_organization_if_missing(from_organization, to_organization, field):
    save_to_organization = False
    if positive_value_exists(getattr(from_organization, field)):
        if not positive_value_exists(getattr(to_organization, field)):
            setattr(to_organization, field, getattr(from_organization, field))
            save_to_organization = True

    return save_to_organization


def organization_follow_or_unfollow_or_ignore(voter_device_id, organization_id, organization_we_vote_id,
                                              follow_kind=FOLLOWING,
                                              organization_follow_based_on_issue=None,
                                              user_agent_string='', user_agent_object=None):
    status = ""
    if organization_follow_based_on_issue is None:
        organization_follow_based_on_issue = False

    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING ',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': "",
        }
        return json_data

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING ',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': "",
        }
        return json_data

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if not results['voter_found']:
        json_data = {
            'status': 'VOTER_NOT_FOUND ',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': "",
        }
        return json_data

    voter = results['voter']
    voter_we_vote_id = voter.we_vote_id
    is_signed_in = voter.is_signed_in()
    voter_linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    organization_id = convert_to_int(organization_id)
    if not positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
        json_data = {
            'status': 'VALID_ORGANIZATION_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': voter_linked_organization_we_vote_id,
        }
        return json_data
    is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
    analytics_manager = AnalyticsManager()
    follow_organization_manager = FollowOrganizationManager()
    position_list_manager = PositionListManager()
    if follow_kind == FOLLOWING:
        results = follow_organization_manager.toggle_on_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status += 'FOLLOWING '
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id

            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_FOLLOW, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status += results['status'] + ' '
            success = False

    elif follow_kind == FOLLOW_IGNORE:
        results = follow_organization_manager.toggle_ignore_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status += 'IGNORING '
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id

            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_FOLLOW_IGNORE, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status += results['status'] + ' '
            success = False
    elif follow_kind == STOP_FOLLOWING:
        results = follow_organization_manager.toggle_off_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status += 'STOPPED_FOLLOWING '
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id

            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_STOP_FOLLOWING, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status += results['status'] + ' '
            success = False
    elif follow_kind == STOP_IGNORING:
        results = follow_organization_manager.toggle_off_voter_ignoring_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status += 'STOPPED_IGNORING '
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id

            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_STOP_IGNORING, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status += results['status'] + ' '
            success = False
    else:
        status += 'INCORRECT_FOLLOW_KIND'
        success = False

    if positive_value_exists(voter_id):
        number_of_organizations_followed = \
            follow_organization_manager.fetch_number_of_organizations_followed(voter_id)

        voter_manager = VoterManager()
        voter_manager.update_organizations_interface_status(voter_we_vote_id, number_of_organizations_followed)

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'organization_id': organization_id,
        'organization_we_vote_id': organization_we_vote_id,
        'organization_follow_based_on_issue': organization_follow_based_on_issue,
        'voter_linked_organization_we_vote_id': voter_linked_organization_we_vote_id,
    }
    return json_data


def organizations_followed_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0,
                                            auto_followed_from_twitter_suggestion=False):
    """
    organizationsFollowedRetrieve Return a list of the organizations followed. See also
    voter_guides_followed_retrieve_for_api, which starts with organizations followed, but returns data as a list of
    voter guides.
    :param voter_device_id:
    :param maximum_number_to_retrieve:
    :param auto_followed_from_twitter_suggestion:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = retrieve_organizations_followed(voter_id, auto_followed_from_twitter_suggestion)
    status = results['status']
    organizations_for_api = []
    if results['organization_list_found']:
        organization_list = results['organization_list']
        number_added_to_list = 0
        for organization in organization_list:
            one_organization = {
                'organization_id': organization.id,
                'organization_we_vote_id': organization.we_vote_id,
                'organization_name':
                    organization.organization_name if positive_value_exists(organization.organization_name) else '',
                'organization_website': organization.organization_website if positive_value_exists(
                    organization.organization_website) else '',
                'organization_twitter_handle':
                    organization.organization_twitter_handle if positive_value_exists(
                        organization.organization_twitter_handle) else '',
                'twitter_followers_count':
                    organization.twitter_followers_count if positive_value_exists(
                        organization.twitter_followers_count) else 0,
                'twitter_description':
                    organization.twitter_description
                    if positive_value_exists(organization.twitter_description) else '',
                'organization_email':
                    organization.organization_email if positive_value_exists(organization.organization_email) else '',
                'organization_facebook': organization.organization_facebook
                    if positive_value_exists(organization.organization_facebook) else '',
                'organization_photo_url_large': organization.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(organization.we_vote_hosted_profile_image_url_large)
                    else organization.organization_photo_url(),
                'organization_photo_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                'organization_photo_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
            }
            organizations_for_api.append(one_organization.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(organizations_for_api):
            status = 'ORGANIZATIONS_FOLLOWED_RETRIEVED'
            success = True
        else:
            status = 'NO_ORGANIZATIONS_FOLLOWED_FOUND'
            success = True
    else:
        success = False

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'organization_list': organizations_for_api,
        'auto_followed_from_twitter_suggestion': auto_followed_from_twitter_suggestion
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organizations_import_from_sample_file():  # TODO FINISH BUILDING/TESTING THIS
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    logger.info("Loading organizations from local file")

    with open('organization/import_data/organizations_sample.json') as json_data:
        structured_json = json.load(json_data)

    request = None
    return organizations_import_from_structured_json(structured_json)


def organizations_import_from_master_server(request, state_code=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading endorsers from We Vote Master servers",
        ORGANIZATIONS_SYNC_URL, {
            "key":               WE_VOTE_API_KEY,  # This comes from an environment variable
            "format":            'json',
            "state_served_code": state_code,
        }
    )

    if import_results['success']:
        results = filter_organizations_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        # filtered_structured_json = structured_json
        # duplicates_removed = 0

        import_results = organizations_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_organizations_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove organizations that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    organization_list_manager = OrganizationListManager()
    for one_organization in structured_json:
        organization_name = one_organization['organization_name'] if 'organization_name' in one_organization else ''
        we_vote_id = one_organization['we_vote_id'] if 'we_vote_id' in one_organization else ''
        organization_twitter_handle = one_organization['organization_twitter_handle'] \
            if 'organization_twitter_handle' in one_organization else ''
        twitter_handle_list = []
        if positive_value_exists(organization_twitter_handle):
            twitter_handle_list.append(organization_twitter_handle)
        vote_smart_id = one_organization['vote_smart_id'] if 'vote_smart_id' in one_organization else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id
        ignore_we_vote_id_list = [we_vote_id_from_master]

        results = organization_list_manager.retrieve_organizations_from_non_unique_identifiers(
            ignore_we_vote_id_list=ignore_we_vote_id_list,
            organization_name=organization_name,
            twitter_handle_list=twitter_handle_list,
            vote_smart_id=vote_smart_id)

        if results['organization_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_organization)

    organizations_results = {
        'success':              True,
        'status':               "FILTER_ORGANIZATIONS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return organizations_results


def organizations_import_from_structured_json(structured_json):
    organizations_saved = 0
    organizations_updated = 0
    organizations_not_processed = 0
    for one_organization in structured_json:
        # We have already removed duplicate organizations
        twitter_user_id = 0
        we_vote_id = ""

        # Make sure we have the minimum required variables
        if not positive_value_exists(one_organization["we_vote_id"]) or \
                not positive_value_exists(one_organization["organization_name"]):
            organizations_not_processed += 1
            continue

        # Check to see if this organization is already being used anywhere
        organization_on_stage_found = False
        try:
            if positive_value_exists(one_organization["we_vote_id"]):
                organization_query = Organization.objects.filter(we_vote_id=one_organization["we_vote_id"])
                if len(organization_query):
                    organization_on_stage = organization_query[0]
                    organization_on_stage_found = True
        except Organization.DoesNotExist:
            # No problem that we aren't finding existing organization
            pass
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            # We want to skip to the next org
            continue

        try:
            we_vote_id = one_organization["we_vote_id"]
            organization_name = one_organization["organization_name"] \
                if 'organization_name' in one_organization else False
            organization_website = one_organization["organization_website"] \
                if 'organization_website' in one_organization else False
            organization_email = one_organization["organization_email"] \
                if 'organization_email' in one_organization else False
            organization_contact_form_url = one_organization["organization_contact_form_url"] \
                if 'organization_contact_form_url' in one_organization else False
            organization_contact_name = one_organization["organization_contact_name"] \
                if 'organization_contact_name' in one_organization else False
            organization_facebook = one_organization["organization_facebook"] \
                if 'organization_facebook' in one_organization else False
            organization_image = one_organization["organization_image"] \
                if 'organization_image' in one_organization else False
            state_served_code = one_organization["state_served_code"] \
                if 'state_served_code' in one_organization else False
            vote_smart_id = one_organization["vote_smart_id"] \
                if 'vote_smart_id' in one_organization else False
            organization_description = one_organization["organization_description"] \
                if 'organization_description' in one_organization else False
            organization_address = one_organization["organization_address"] \
                if 'organization_address' in one_organization else False
            organization_city = one_organization["organization_city"] \
                if 'organization_city' in one_organization else False
            organization_state = one_organization["organization_state"] \
                if 'organization_state' in one_organization else False
            organization_zip = one_organization["organization_zip"] \
                if 'organization_zip' in one_organization else False
            organization_phone1 = one_organization["organization_phone1"] \
                if 'organization_phone1' in one_organization else False
            organization_phone2 = one_organization["organization_phone2"] \
                if 'organization_phone2' in one_organization else False
            organization_fax = one_organization["organization_fax"] \
                if 'organization_fax' in one_organization else False
            twitter_user_id = one_organization["twitter_user_id"] \
                if 'twitter_user_id' in one_organization else False
            organization_twitter_handle = one_organization["organization_twitter_handle"] \
                if 'organization_twitter_handle' in one_organization else False
            twitter_name = one_organization["twitter_name"] \
                if 'twitter_name' in one_organization else False
            twitter_location = one_organization["twitter_location"] \
                if 'twitter_location' in one_organization else False
            twitter_followers_count = one_organization["twitter_followers_count"] \
                if 'twitter_followers_count' in one_organization else False
            twitter_profile_image_url_https = one_organization["twitter_profile_image_url_https"] \
                if 'twitter_profile_image_url_https' in one_organization else False
            twitter_profile_background_image_url_https = \
                one_organization["twitter_profile_background_image_url_https"] \
                if 'twitter_profile_background_image_url_https' in one_organization else False
            twitter_profile_banner_url_https = one_organization["twitter_profile_banner_url_https"] \
                if 'twitter_profile_banner_url_https' in one_organization else False
            twitter_description = one_organization["twitter_description"] \
                if 'twitter_description' in one_organization else False
            wikipedia_page_id = one_organization["wikipedia_page_id"] \
                if 'wikipedia_page_id' in one_organization else False
            wikipedia_page_title = one_organization["wikipedia_page_title"] \
                if 'wikipedia_page_title' in one_organization else False
            wikipedia_thumbnail_url = one_organization["wikipedia_thumbnail_url"] \
                if 'wikipedia_thumbnail_url' in one_organization else False
            wikipedia_thumbnail_width = one_organization["wikipedia_thumbnail_width"] \
                if 'wikipedia_thumbnail_width' in one_organization else False
            wikipedia_thumbnail_height = one_organization["wikipedia_thumbnail_height"] \
                if 'wikipedia_thumbnail_height' in one_organization else False
            wikipedia_photo_url = one_organization["wikipedia_photo_url"] \
                if 'wikipedia_photo_url' in one_organization else False
            ballotpedia_page_title = one_organization["ballotpedia_page_title"] \
                if 'ballotpedia_page_title' in one_organization else False
            ballotpedia_photo_url = one_organization["ballotpedia_photo_url"] \
                if 'ballotpedia_photo_url' in one_organization else False
            organization_type = one_organization["organization_type"] \
                if 'organization_type' in one_organization else False
            we_vote_hosted_profile_image_url_large = one_organization['we_vote_hosted_profile_image_url_large'] \
                if 'we_vote_hosted_profile_image_url_large' in one_organization else False
            we_vote_hosted_profile_image_url_medium = one_organization['we_vote_hosted_profile_image_url_medium'] \
                if 'we_vote_hosted_profile_image_url_medium' in one_organization else False
            we_vote_hosted_profile_image_url_tiny = one_organization['we_vote_hosted_profile_image_url_tiny'] \
                if 'we_vote_hosted_profile_image_url_tiny' in one_organization else False

            if organization_on_stage_found:
                # Update existing organization in the database
                if we_vote_id is not False:
                    organization_on_stage.we_vote_id = we_vote_id
                if organization_name is not False:
                    organization_on_stage.organization_name = organization_name
            else:
                # Create new
                organization_on_stage = Organization(
                    we_vote_id=one_organization["we_vote_id"],
                    organization_name=one_organization["organization_name"],
                )

            # Now save all the fields in common to updating an existing entry vs. creating a new entry
            if organization_website is not False:
                organization_on_stage.organization_website = organization_website
            if organization_email is not False:
                organization_on_stage.organization_email = organization_email
            if organization_contact_form_url is not False:
                organization_on_stage.organization_contact_form_url = organization_contact_form_url
            if organization_contact_name is not False:
                organization_on_stage.organization_contact_name = organization_contact_name
            if organization_facebook is not False:
                organization_on_stage.organization_facebook = organization_facebook
            if organization_image is not False:
                organization_on_stage.organization_image = organization_image
            if state_served_code is not False:
                organization_on_stage.state_served_code = state_served_code
            if vote_smart_id is not False:
                organization_on_stage.vote_smart_id = vote_smart_id
            if organization_description is not False:
                organization_on_stage.organization_description = organization_description
            if organization_address is not False:
                organization_on_stage.organization_address = organization_address
            if organization_city is not False:
                organization_on_stage.organization_city = organization_city
            if organization_state is not False:
                organization_on_stage.organization_state = organization_state
            if organization_zip is not False:
                organization_on_stage.organization_zip = organization_zip
            if organization_phone1 is not False:
                organization_on_stage.organization_phone1 = organization_phone1
            if organization_phone2 is not False:
                organization_on_stage.organization_phone2 = organization_phone2
            if organization_fax is not False:
                organization_on_stage.organization_fax = organization_fax
            if twitter_user_id is not False:
                organization_on_stage.twitter_user_id = twitter_user_id
            if organization_twitter_handle is not False:
                organization_on_stage.organization_twitter_handle = organization_twitter_handle
            if twitter_name is not False:
                organization_on_stage.twitter_name = twitter_name
            if twitter_location is not False:
                organization_on_stage.twitter_location = twitter_location
            if twitter_followers_count is not False:
                organization_on_stage.twitter_followers_count = twitter_followers_count
            if twitter_profile_image_url_https is not False:
                organization_on_stage.twitter_profile_image_url_https = twitter_profile_image_url_https
            if twitter_profile_background_image_url_https is not False:
                organization_on_stage.twitter_profile_background_image_url_https = \
                    twitter_profile_background_image_url_https
            if twitter_profile_banner_url_https is not False:
                organization_on_stage.twitter_profile_banner_url_https = twitter_profile_banner_url_https
            if twitter_description is not False:
                organization_on_stage.twitter_description = twitter_description
            if wikipedia_page_id is not False:
                organization_on_stage.wikipedia_page_id = wikipedia_page_id
            if wikipedia_page_title is not False:
                organization_on_stage.wikipedia_page_title = wikipedia_page_title
            if wikipedia_thumbnail_url is not False:
                organization_on_stage.wikipedia_thumbnail_url = wikipedia_thumbnail_url
            if wikipedia_thumbnail_width is not False:
                organization_on_stage.wikipedia_thumbnail_width = wikipedia_thumbnail_width
            if wikipedia_thumbnail_height is not False:
                organization_on_stage.wikipedia_thumbnail_height = wikipedia_thumbnail_height
            if wikipedia_photo_url is not False:
                organization_on_stage.wikipedia_photo_url = wikipedia_photo_url
            if ballotpedia_page_title is not False:
                organization_on_stage.ballotpedia_page_title = ballotpedia_page_title
            if ballotpedia_photo_url is not False:
                organization_on_stage.ballotpedia_photo_url = ballotpedia_photo_url
            if organization_type is not False:
                organization_on_stage.organization_type = organization_type
            if we_vote_hosted_profile_image_url_large is not False:
                organization_on_stage.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
            if we_vote_hosted_profile_image_url_medium is not False:
                organization_on_stage.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
            if we_vote_hosted_profile_image_url_tiny is not False:
                organization_on_stage.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny

            organization_on_stage.save()
            if organization_on_stage_found:
                organizations_updated += 1
            else:
                organizations_saved += 1
        except Exception as e:
            organizations_not_processed += 1

        # Now create a TwitterLinkToOrganization entry if one doesn't exist
        twitter_user_manager = TwitterUserManager()
        try:
            if positive_value_exists(twitter_user_id) and positive_value_exists(we_vote_id):
                results = twitter_user_manager.create_twitter_link_to_organization(twitter_user_id, we_vote_id)
        except Exception as e:
            pass

    organizations_results = {
        'success': True,
        'status': "ORGANIZATION_IMPORT_PROCESS_COMPLETE",
        'saved': organizations_saved,
        'updated': organizations_updated,
        'not_processed': organizations_not_processed,
    }
    return organizations_results


def organization_photos_save_for_api(  # organizationPhotosSave
        organization_id=0, organization_we_vote_id='',
        chosen_favicon_from_file_reader='',
        chosen_logo_from_file_reader='',
        chosen_social_share_master_image_from_file_reader='',
        delete_chosen_favicon=False,
        delete_chosen_logo=False,
        delete_chosen_social_share_master_image=False,
        prior_status=''):
    status = ''
    status += prior_status

    organization_id = convert_to_int(organization_id)
    organization_we_vote_id = organization_we_vote_id.strip().lower()

    organization_manager = OrganizationManager()
    unique_identifier_found = positive_value_exists(organization_id) \
        or positive_value_exists(organization_we_vote_id)
    if not unique_identifier_found:
        status += "ORGANIZATION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'chosen_favicon_url_https':     '',
            'chosen_logo_url_https':        '',
            'chosen_social_share_master_image_url_https': '',
            'organization_id':              organization_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'organization_updated':         False,
        }
        return results

    kind_of_image_chosen_favicon = positive_value_exists(chosen_favicon_from_file_reader)
    kind_of_image_chosen_logo = positive_value_exists(chosen_logo_from_file_reader)
    kind_of_image_chosen_social_share_master = positive_value_exists(chosen_social_share_master_image_from_file_reader)

    # Now convert the file_reader data (from Javascript) into a URL stored in our AWS bucket
    chosen_favicon_url_https = False
    chosen_logo_url_https = False
    chosen_social_share_master_image_url_https = False

    if kind_of_image_chosen_favicon:
        image_data_found = False
        python_image_library_image = None
        img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                            chosen_favicon_from_file_reader).groupdict()
        if img_dict['encoding'] == 'base64':
            try:
                base64_data = img_dict['data']
                byte_data = base64.b64decode(base64_data)
                image_data = BytesIO(byte_data)
                original_image = Image.open(image_data)
                format_to_cache = original_image.format
                python_image_library_image = ImageOps.exif_transpose(original_image)
                python_image_library_image.thumbnail((CHOSEN_FAVICON_MAX_WIDTH, CHOSEN_FAVICON_MAX_HEIGHT),
                                                     Image.Resampling.LANCZOS)
                # python_image_library_image = ImageOps.fit(
                #    python_image_library_image, (CHOSEN_FAVICON_MAX_WIDTH, CHOSEN_FAVICON_MAX_HEIGHT),
                #    Image.Resampling.LANCZOS)
                python_image_library_image.format = format_to_cache
                image_data_found = True
            except Exception as e:
                status += 'PROBLEM_DECODING_CHOSEN_FAVICON: {error} [type: {error_type}] ' \
                          ''.format(error=e, error_type=type(e))
        else:
            status += "INCOMING_CHOSEN_FAVICON-BASE64_NOT_FOUND "

        if image_data_found:
            cache_results = cache_organization_sharing_image(
                python_image_library_image=python_image_library_image,
                organization_we_vote_id=organization_we_vote_id,
                kind_of_image_chosen_favicon=True,
                kind_of_image_original=True)
            status += cache_results['status']
            if cache_results['success']:
                cached_master_we_vote_image = cache_results['we_vote_image']
                chosen_favicon_url_https = cached_master_we_vote_image.we_vote_image_url
    elif delete_chosen_favicon:
        pass

    if kind_of_image_chosen_logo:
        image_data_found = False
        python_image_library_image = None
        img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                            chosen_logo_from_file_reader).groupdict()
        if img_dict['encoding'] == 'base64':
            try:
                base64_data = img_dict['data']
                byte_data = base64.b64decode(base64_data)
                image_data = BytesIO(byte_data)
                original_image = Image.open(image_data)
                format_to_cache = original_image.format
                python_image_library_image = ImageOps.exif_transpose(original_image)
                python_image_library_image.thumbnail(
                    (CHOSEN_LOGO_MAX_WIDTH, CHOSEN_LOGO_MAX_HEIGHT), Image.Resampling.LANCZOS)
                # Did not keep image within size limit
                # python_image_library_image = ImageOps.fit(
                # python_image_library_image, (CHOSEN_LOGO_MAX_WIDTH, CHOSEN_LOGO_MAX_HEIGHT), Image.Resampling.LANCZOS)
                python_image_library_image.format = format_to_cache
                image_data_found = True
            except Exception as e:
                status += 'PROBLEM_DECODING_CHOSEN_LOGO: {error} [type: {error_type}] ' \
                          ''.format(error=e, error_type=type(e))
        else:
            status += "INCOMING_CHOSEN_LOGO-BASE64_NOT_FOUND "

        if image_data_found:
            cache_results = cache_organization_sharing_image(
                python_image_library_image=python_image_library_image,
                organization_we_vote_id=organization_we_vote_id,
                kind_of_image_chosen_logo=True,
                kind_of_image_original=True)
            status += cache_results['status']
            if cache_results['success']:
                cached_master_we_vote_image = cache_results['we_vote_image']
                chosen_logo_url_https = cached_master_we_vote_image.we_vote_image_url
    elif delete_chosen_logo:
        # For now we aren't actually deleting these images here -- we just remove them from the organization
        pass

    if kind_of_image_chosen_social_share_master:
        image_data_found = False
        python_image_library_image = None
        img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                            chosen_social_share_master_image_from_file_reader).groupdict()
        if img_dict['encoding'] == 'base64':
            try:
                base64_data = img_dict['data']
                byte_data = base64.b64decode(base64_data)
                image_data = BytesIO(byte_data)
                original_image = Image.open(image_data)
                format_to_cache = original_image.format
                python_image_library_image = ImageOps.exif_transpose(original_image)
                python_image_library_image.thumbnail(
                    (CHOSEN_SOCIAL_SHARE_MASTER_MAX_WIDTH, CHOSEN_SOCIAL_SHARE_MASTER_MAX_HEIGHT),
                    Image.Resampling.LANCZOS)
                # python_image_library_image = ImageOps.fit(
                #     python_image_library_image,
                #     (CHOSEN_SOCIAL_SHARE_MASTER_MAX_WIDTH, CHOSEN_SOCIAL_SHARE_MASTER_MAX_HEIGHT),
                #     Image.Resampling.LANCZOS)
                python_image_library_image.format = format_to_cache
                image_data_found = True
            except Exception as e:
                status += 'PROBLEM_DECODING_CHOSEN_SOCIAL_SHARE_MASTER: {error} [type: {error_type}] ' \
                          ''.format(error=e, error_type=type(e))
        else:
            status += "INCOMING_CHOSEN_SOCIAL_SHARE_MASTER-BASE64_NOT_FOUND "

        if image_data_found:
            cache_results = cache_organization_sharing_image(
                python_image_library_image=python_image_library_image,
                organization_we_vote_id=organization_we_vote_id,
                kind_of_image_chosen_social_share_master=True,
                kind_of_image_original=True)
            status += cache_results['status']
            if cache_results['success']:
                cached_master_we_vote_image = cache_results['we_vote_image']
                chosen_social_share_master_image_url_https = cached_master_we_vote_image.we_vote_image_url
    elif delete_chosen_social_share_master_image:
        # For now we aren't actually deleting these images here -- we just remove them from the organization
        pass

    # And finally, save the locally stored URLs in the organization object
    save_results = organization_manager.update_organization_photos(
        organization_id=organization_id, organization_we_vote_id=organization_we_vote_id,
        chosen_favicon_url_https=chosen_favicon_url_https,
        chosen_logo_url_https=chosen_logo_url_https,
        chosen_social_share_master_image_url_https=chosen_social_share_master_image_url_https,
        delete_chosen_favicon=delete_chosen_favicon,
        delete_chosen_logo=delete_chosen_logo,
        delete_chosen_social_share_master_image=delete_chosen_social_share_master_image)

    success = save_results['success']
    status += save_results['status']
    organization_updated = save_results['organization_updated']

    results = {
        'success':                              success,
        'status':                               status,
        'chosen_favicon_url_https':             chosen_favicon_url_https if chosen_favicon_url_https else '',
        'chosen_logo_url_https':                chosen_logo_url_https if chosen_logo_url_https else '',
        'chosen_social_share_master_image_url_https': chosen_social_share_master_image_url_https
        if chosen_social_share_master_image_url_https else '',
        'delete_chosen_favicon':                delete_chosen_favicon,
        'delete_chosen_logo':                   delete_chosen_logo,
        'delete_chosen_social_share_master_image':  delete_chosen_social_share_master_image,
        'organization_id':                      organization_id,
        'organization_we_vote_id':              organization_we_vote_id,
        'organization_updated':                 organization_updated,
    }
    return results


def organization_retrieve_for_api(  # organizationRetrieve
        organization_id, organization_we_vote_id, voter_device_id, prior_status=''):
    """
    Called from organizationRetrieve api
    :param organization_id:
    :param organization_we_vote_id:
    :param voter_device_id:
    :param prior_status:
    :return:
    """
    status = ''
    status += prior_status
    organization_id = convert_to_int(organization_id)

    organization_we_vote_id = organization_we_vote_id.strip().lower()
    if not positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
        status += "ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING "
        json_data = {
            'status':                           status,
            'success':                          False,
            'chosen_domain_string':             '',
            'chosen_domain_string2':             '',
            'chosen_domain_string3':             '',
            'chosen_favicon_url_https':         '',
            'chosen_feature_package':           '',
            'chosen_google_analytics_tracking_id': '',
            'chosen_html_verification_string':  '',
            'chosen_hide_we_vote_logo':         '',
            'chosen_logo_url_https':            '',
            'chosen_prevent_sharing_opinions':  '',
            'chosen_ready_introduction_text':   '',
            'chosen_ready_introduction_title':  '',
            'chosen_social_share_description':  '',
            'chosen_social_share_image_256x256_url_https': '',
            'chosen_social_share_master_image_url_https': '',
            'chosen_subdomain_string':          '',
            'chosen_subscription_plan':         '',
            'subscription_plan_end_day_text':   '',
            'subscription_plan_features_active': '',  # Replace with features_provided_bitmap
            'features_provided_bitmap':         '',
            'facebook_id':                      0,
            'organization_banner_url':          '',
            'organization_description':         '',
            'organization_email':               '',
            'organization_facebook':            '',
            'organization_id':                  organization_id,
            'organization_instagram_handle':    '',
            'organization_name':                '',
            'organization_photo_url_large':     '',
            'organization_photo_url_medium':    '',
            'organization_photo_url_tiny':      '',
            'organization_type':                '',
            'organization_twitter_handle':      '',
            'organization_we_vote_id':          organization_we_vote_id,
            'organization_website':             '',
            'twitter_description':              '',
            'twitter_followers_count':          '',
            'linked_voter_we_vote_id':          '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)
    status += results['status']

    if results['organization_found']:
        organization = results['organization']

        # Heal data: If the organization_name is a placeholder name, repair it with fresh data
        if organization_manager.organization_name_needs_repair(organization):
            organization = organization_manager.repair_organization(organization)
            position_list_manager = PositionListManager()
            position_list_manager.refresh_cached_position_info_for_organization(organization_we_vote_id)

        # Favor the Twitter banner and profile image if they exist
        # From Dale September 1, 2017:  Eventually we would like to let a person choose which they want to display,
        # but for now Twitter always wins out.
        we_vote_hosted_profile_image_url_large = organization.we_vote_hosted_profile_image_url_large if \
            positive_value_exists(organization.we_vote_hosted_profile_image_url_large) else \
            organization.organization_photo_url()

        if positive_value_exists(organization.twitter_profile_banner_url_https):
            organization_banner_url = organization.twitter_profile_banner_url_https
        else:
            organization_banner_url = organization.facebook_background_image_url_https

        if isinstance(organization_banner_url, list):
            # If a list, just return the first one
            organization_banner_url = organization_banner_url.pop()
        elif isinstance(organization_banner_url, tuple):
            # If a tuple, just return the first one
            organization_banner_url = organization_banner_url[0]
        voter_manager = VoterManager()
        linked_voter_we_vote_id = voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
            organization.we_vote_id)

        json_data = {
            'success': True,
            'status': status,
            'chosen_domain_string':             organization.chosen_domain_string,
            'chosen_domain_string2':             organization.chosen_domain_string2,
            'chosen_domain_string3':             organization.chosen_domain_string3,
            'chosen_favicon_url_https':         organization.chosen_favicon_url_https,
            'chosen_feature_package':           organization.chosen_feature_package,
            'chosen_google_analytics_tracking_id': organization.chosen_google_analytics_tracking_id,
            'chosen_html_verification_string':  organization.chosen_html_verification_string,
            'chosen_hide_we_vote_logo':         organization.chosen_hide_we_vote_logo,
            'chosen_logo_url_https':            organization.chosen_logo_url_https,
            'chosen_prevent_sharing_opinions':  organization.chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text':   organization.chosen_ready_introduction_text,
            'chosen_ready_introduction_title':  organization.chosen_ready_introduction_title,
            'chosen_social_share_description':  organization.chosen_social_share_description,
            'chosen_social_share_master_image_url_https':   organization.chosen_social_share_master_image_url_https,
            'chosen_social_share_image_256x256_url_https':  organization.chosen_social_share_image_256x256_url_https,
            'chosen_subdomain_string':          organization.chosen_subdomain_string,
            'chosen_subscription_plan':         organization.chosen_subscription_plan,
            'subscription_plan_end_day_text':   organization.subscription_plan_end_day_text,
            'subscription_plan_features_active': organization.subscription_plan_features_active,  # Replace
            'features_provided_bitmap':         organization.features_provided_bitmap,
            'organization_banner_url':          organization_banner_url,
            'organization_id':                  organization.id,
            'organization_we_vote_id':          organization.we_vote_id,  # this is the we_vote_id for this organization
            'organization_description':
                organization.organization_description if positive_value_exists(organization.organization_description)
                else '',
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
            'organization_instagram_handle':
                organization.organization_instagram_handle
                if positive_value_exists(organization.organization_instagram_handle) else '',
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_type':
                organization.organization_type if positive_value_exists(organization.organization_type) else '',
            'organization_twitter_handle':
                organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'organization_website': organization.organization_website if positive_value_exists(
                organization.organization_website) else '',
            'facebook_id':
                organization.facebook_id if positive_value_exists(organization.facebook_id) else 0,
            'organization_photo_url_large': we_vote_hosted_profile_image_url_large,
            'organization_photo_url_medium': organization.we_vote_hosted_profile_image_url_medium,
            'organization_photo_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
            'twitter_description':
                organization.twitter_description if positive_value_exists(
                    organization.twitter_description) else '',
            'twitter_followers_count':
                organization.twitter_followers_count if positive_value_exists(
                    organization.twitter_followers_count) else 0,
            'linked_voter_we_vote_id':      linked_voter_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                           status,
            'success':                          False,
            'chosen_domain_string':             '',
            'chosen_domain_string2':            '',
            'chosen_domain_string3':            '',
            'chosen_favicon_url_https':         '',
            'chosen_google_analytics_tracking_id': '',
            'chosen_html_verification_string':  '',
            'chosen_hide_we_vote_logo':         '',
            'chosen_logo_url_https':            '',
            'chosen_prevent_sharing_opinions':  '',
            'chosen_ready_introduction_text':   '',
            'chosen_ready_introduction_title':  '',
            'chosen_social_share_description':  '',
            'chosen_social_share_image_256x256_url_https': '',
            'chosen_social_share_master_image_url_https': '',
            'chosen_subdomain_string':          '',
            'chosen_subscription_plan':         '',
            'subscription_plan_end_day_text':   '',
            'subscription_plan_features_active': '',  # Replace with features_provided_bitmap
            'chosen_feature_package':           '',
            'features_provided_bitmap':         '',
            'facebook_id':                      0,
            'organization_banner_url':          '',
            'organization_description':         '',
            'organization_email':               '',
            'organization_facebook':            '',
            'organization_id':                  organization_id,
            'organization_instagram_handle':    '',
            'organization_name':                '',
            'organization_photo_url_large':     '',
            'organization_photo_url_medium':    '',
            'organization_photo_url_tiny':      '',
            'organization_twitter_handle':      '',
            'organization_type':                '',
            'organization_website':             '',
            'organization_we_vote_id':          organization_we_vote_id,
            'twitter_description':              '',
            'twitter_followers_count':          '',
            'linked_voter_we_vote_id':          '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_save_photo_from_file_reader(
        organization_we_vote_id='',
        organization_photo_binary_file=None,
        organization_photo_from_file_reader=None):
    image_data_found = False
    python_image_library_image = None
    status = ""
    success = True
    we_vote_hosted_organization_photo_original_url = ''

    if not positive_value_exists(organization_we_vote_id):
        status += "MISSING_ORGANIZATION_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_organization_photo_original_url': we_vote_hosted_organization_photo_original_url,
        }
        return results

    if not positive_value_exists(organization_photo_from_file_reader) \
            and not positive_value_exists(organization_photo_binary_file):
        status += "MISSING_ORGANIZATION_PHOTO_FROM_FILE_READER "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_organization_photo_original_url': we_vote_hosted_organization_photo_original_url,
        }
        return results

    if not organization_photo_binary_file:
        try:
            img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                                organization_photo_from_file_reader).groupdict()
            if img_dict['encoding'] == 'base64':
                organization_photo_binary_file = img_dict['data']
            else:
                status += "INCOMING_ORGANIZATION_UPLOADED_PHOTO-BASE64_NOT_FOUND "
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_BINARY_DATA_FROM_INCOMING_ORGANIZATION_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if organization_photo_binary_file:
        try:
            byte_data = base64.b64decode(organization_photo_binary_file)
            image_data = BytesIO(byte_data)
            original_image = Image.open(image_data)
            format_to_cache = original_image.format
            python_image_library_image = ImageOps.exif_transpose(original_image)
            python_image_library_image.thumbnail(
                (PROFILE_IMAGE_ORIGINAL_MAX_WIDTH, PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT), Image.Resampling.LANCZOS)
            python_image_library_image.format = format_to_cache
            image_data_found = True
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_ORGANIZATION_PHOTO_FROM_BINARY_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if image_data_found:
        cache_results = cache_image_object_to_aws(
            python_image_library_image=python_image_library_image,
            organization_we_vote_id=organization_we_vote_id,
            kind_of_image_organization_uploaded_profile=True,
            kind_of_image_original=True)
        status += cache_results['status']
        if cache_results['success']:
            cached_master_we_vote_image = cache_results['we_vote_image']
            try:
                we_vote_hosted_organization_photo_original_url = cached_master_we_vote_image.we_vote_image_url
            except Exception as e:
                status += "FAILED_TO_CACHE_ORGANIZATION_IMAGE: " + str(e) + ' '
                success = False
        else:
            success = False
    results = {
        'status':                   status,
        'success':                  success,
        'we_vote_hosted_organization_photo_original_url': we_vote_hosted_organization_photo_original_url,
    }
    return results


def organization_save_for_api(  # organizationSave
        voter_device_id='',
        organization_id=0,
        organization_we_vote_id='',
        organization_name=False,
        organization_description=False,
        organization_email=False,
        organization_website=False,
        organization_twitter_handle=False,
        organization_facebook=False,
        organization_instagram_handle=False,
        organization_image=False,
        organization_type=False,
        refresh_from_twitter=False,
        facebook_id=False,
        facebook_email=False,
        facebook_profile_image_url_https=False,
        chosen_domain_string=False,
        chosen_domain_string2=False,
        chosen_domain_string3=False,
        chosen_google_analytics_tracking_id=False,
        chosen_html_verification_string=False,
        chosen_hide_we_vote_logo=None,
        chosen_prevent_sharing_opinions=None,
        chosen_ready_introduction_text=False,
        chosen_ready_introduction_title=False,
        chosen_social_share_description=False,
        chosen_subdomain_string=False,
        chosen_subscription_plan=False):
    """
    We use this to store displayable organization data
    TODO: Make sure voter's can't change their Twitter handles here.
    :param voter_device_id:
    :param organization_id:
    :param organization_we_vote_id:
    :param organization_name:
    :param organization_description:
    :param organization_email:
    :param organization_website:
    :param organization_twitter_handle:
    :param organization_facebook:
    :param organization_instagram_handle:
    :param organization_image:
    :param organization_type
    :param refresh_from_twitter:
    :param facebook_id:
    :param facebook_email:
    :param facebook_profile_image_url_https:
    :param chosen_domain_string:
    :param chosen_domain_string2:
    :param chosen_domain_string3:
    :param chosen_google_analytics_tracking_id:
    :param chosen_html_verification_string:
    :param chosen_hide_we_vote_logo:
    :param chosen_prevent_sharing_opinions:
    :param chosen_ready_introduction_text:
    :param chosen_ready_introduction_title:
    :param chosen_social_share_description:
    :param chosen_subdomain_string:
    :param chosen_subscription_plan:
    :return:
    """
    organization_id = convert_to_int(organization_id)
    organization_we_vote_id = organization_we_vote_id.strip().lower()

    # Make sure we are only working with the twitter handle, and not the "https" or "@"
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)

    facebook_id = convert_to_int(facebook_id)

    existing_unique_identifier_found = positive_value_exists(organization_id) \
        or positive_value_exists(organization_we_vote_id) or positive_value_exists(facebook_id)
    new_unique_identifier_found = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website) or positive_value_exists(facebook_id)
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have one of these: twitter_handle or website, AND organization_name
    required_variables_for_new_entry = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website) or positive_value_exists(facebook_id) \
        and positive_value_exists(organization_name)
    if not unique_identifier_found:
        results = {
            'status':                       "ORGANIZATION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                      False,
            'chosen_domain_string':         chosen_domain_string,
            'chosen_domain_string2':        chosen_domain_string2,
            'chosen_domain_string3':        chosen_domain_string3,
            'chosen_favicon_url_https':     '',
            'chosen_google_analytics_tracking_id': chosen_google_analytics_tracking_id,
            'chosen_html_verification_string':  chosen_html_verification_string,
            'chosen_hide_we_vote_logo':     chosen_hide_we_vote_logo,
            'chosen_logo_url_https':        '',
            'chosen_prevent_sharing_opinions':  chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text': chosen_ready_introduction_text,
            'chosen_ready_introduction_title': chosen_ready_introduction_title,
            'chosen_social_share_description': chosen_social_share_description,
            'chosen_social_share_image_256x256_url_https': '',
            'chosen_subdomain_string':      chosen_subdomain_string,
            'chosen_subscription_plan':     chosen_subscription_plan,
            'subscription_plan_end_day_text':   '',  # Not something that can be saved directly from WebApp
            'subscription_plan_features_active': '',  # Replace
            'chosen_feature_package':       '',  # Not something that can be saved directly from WebApp
            'facebook_id':                  facebook_id,
            'new_organization_created':     False,
            'organization_description':     organization_description,
            'organization_email':           organization_email,
            'organization_facebook':        organization_facebook,
            'organization_id':              organization_id,
            'organization_instagram_handle': organization_instagram_handle,
            'organization_name':            organization_name,
            'organization_photo_url':       organization_image,
            'organization_twitter_handle':  organization_twitter_handle,
            'organization_type':            organization_type,
            'organization_we_vote_id':      organization_we_vote_id,
            'organization_website':         organization_website,
            'refresh_from_twitter':         refresh_from_twitter,
            'twitter_followers_count':      0,
            'twitter_description':          "",
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                       "NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING",
            'success':                      False,
            'chosen_domain_string':         chosen_domain_string,
            'chosen_domain_string2':        chosen_domain_string2,
            'chosen_domain_string3':        chosen_domain_string3,
            'chosen_favicon_url_https':     '',
            'chosen_google_analytics_tracking_id': chosen_google_analytics_tracking_id,
            'chosen_html_verification_string':  chosen_html_verification_string,
            'chosen_hide_we_vote_logo':     chosen_hide_we_vote_logo,
            'chosen_logo_url_https':        '',
            'chosen_prevent_sharing_opinions':  chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text':   chosen_ready_introduction_text,
            'chosen_ready_introduction_title':  chosen_ready_introduction_title,
            'chosen_social_share_description':  chosen_social_share_description,
            'chosen_social_share_image_256x256_url_https': '',
            'chosen_subdomain_string':      chosen_subdomain_string,
            'chosen_subscription_plan':     chosen_subscription_plan,
            'subscription_plan_end_day_text':       '',  # Not something that can be saved directly from WebApp
            'subscription_plan_features_active':    '',  # Replace
            'chosen_feature_package':       '',  # Not something that can be saved directly from WebApp
            'features_provided_bitmap':     '',  # Not something that can be saved directly from WebApp
            'new_organization_created':     False,
            'organization_description':     organization_description,
            'organization_email':           organization_email,
            'organization_facebook':        organization_facebook,
            'organization_id':              organization_id,
            'organization_instagram_handle': organization_instagram_handle,
            'organization_name':            organization_name,
            'organization_photo_url':       organization_image,
            'organization_twitter_handle':  organization_twitter_handle,
            'organization_type':            organization_type,
            'organization_we_vote_id':      organization_we_vote_id,
            'organization_website':         organization_website,
            'twitter_followers_count':      0,
            'twitter_description':          "",
            'refresh_from_twitter':         refresh_from_twitter,
            'facebook_id':                  facebook_id,
        }
        return results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)  # Cannot be read_only
    if voter_results['voter_found']:
        voter_found = True
        voter = voter_results['voter']
    else:
        voter_found = False
        voter = Voter()

    facebook_background_image_url_https = False
    facebook_manager = FacebookManager()
    facebook_auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    facebook_auth_response = facebook_auth_response_results['facebook_auth_response']

    if organization_name is False:
        # If the variable comes in as a literal value "False" then don't create an organization_name
        pass
    else:
        if not positive_value_exists(organization_name) or organization_name == "null null":
            organization_name = ""
            if voter_found:
                # First see if there is a Twitter name
                organization_name = voter.twitter_name

                # Check to see if the voter has a name
                if not positive_value_exists(organization_name):
                    organization_name = voter.get_full_name()

            # If not, check the FacebookAuthResponse table
            if not positive_value_exists(organization_name):
                organization_name = facebook_auth_response.get_full_name()

    # Add in the facebook email if we have it
    if facebook_auth_response:
        if not positive_value_exists(facebook_email):
            facebook_email = facebook_auth_response.facebook_email

    organization_manager = OrganizationManager()
    chosen_subdomain_string_previous = ''
    if positive_value_exists(organization_we_vote_id):
        # Retrieve existing organization so we can check to see if the updated chosen_subdomain_string has just been
        # added or removed.
        retrieve_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if retrieve_results['organization_found']:
            organization_previous_state = retrieve_results['organization']
            chosen_subdomain_string_previous = organization_previous_state.chosen_subdomain_string

    save_results = organization_manager.update_or_create_organization(
        organization_id=organization_id,
        we_vote_id=organization_we_vote_id,
        organization_website_search=organization_website,
        organization_twitter_search=organization_twitter_handle,
        organization_name=organization_name,
        organization_description=organization_description,
        organization_website=organization_website,
        organization_twitter_handle=organization_twitter_handle,
        organization_email=organization_email,
        organization_facebook=organization_facebook,
        organization_instagram_handle=organization_instagram_handle,
        organization_image=organization_image,
        organization_type=organization_type,
        refresh_from_twitter=refresh_from_twitter,
        facebook_id=facebook_id,
        facebook_email=facebook_email,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
        chosen_domain_string=chosen_domain_string,
        chosen_domain_string2=chosen_domain_string2,
        chosen_domain_string3=chosen_domain_string3,
        chosen_google_analytics_tracking_id=chosen_google_analytics_tracking_id,
        chosen_html_verification_string=chosen_html_verification_string,
        chosen_hide_we_vote_logo=chosen_hide_we_vote_logo,
        chosen_prevent_sharing_opinions=chosen_prevent_sharing_opinions,
        chosen_ready_introduction_text=chosen_ready_introduction_text,
        chosen_ready_introduction_title=chosen_ready_introduction_title,
        chosen_social_share_description=chosen_social_share_description,
        chosen_subdomain_string=chosen_subdomain_string,
        chosen_subscription_plan=chosen_subscription_plan,
    )

    success = save_results['success']
    if save_results['success']:
        organization = save_results['organization']
        status = save_results['status']

        # Create TwitterLinkToOrganization
        twitter_user_manager = TwitterUserManager()
        retrieve_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
            organization.twitter_user_id, organization.organization_twitter_handle)
        if retrieve_results['twitter_user_found']:
            twitter_user = retrieve_results['twitter_user']
            if positive_value_exists(twitter_user.twitter_id):
                link_to_organization_results = \
                    twitter_user_manager.retrieve_twitter_link_to_organization(twitter_user.twitter_id)
                if link_to_organization_results['twitter_link_to_organization_found']:
                    # TwitterLinkToOrganization already exists
                    pass
                else:
                    # Create a TwitterLinkToOrganization entry
                    twitter_user_manager.create_twitter_link_to_organization(twitter_user.twitter_id,
                                                                             organization.we_vote_id)

        # Now update the voter record with the organization_we_vote_id
        if voter_found:
            # Does this voter have the same Twitter handle as this organization? If so, link this organization to
            #  this particular voter
            results = twitter_user_manager.retrieve_twitter_link_to_voter_from_twitter_handle(
                organization.organization_twitter_handle, read_only=True)
            if results['twitter_link_to_voter_found']:
                twitter_link_to_voter = results['twitter_link_to_voter']
                # Check to make sure another voter isn't hanging onto this organization_we_vote_id
                # TODO DALE UPDATE linked_organization_we_vote_id
                voter_manager.clear_out_collisions_for_linked_organization_we_vote_id(voter.we_vote_id,
                                                                                      organization.we_vote_id)
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()

                    # TODO DALE UPDATE positions to add voter_we_vote_id - Any position with
                    # the organization_we_vote_id should get the voter_we_vote_id added,
                    # and any position with the voter_we_vote_id should get the organization_we_vote_id added
                except Exception as e:
                    success = False
                    status += " UNABLE_TO_UPDATE_VOTER_WITH_ORGANIZATION_WE_VOTE_ID_FROM_TWITTER "
            elif positive_value_exists(facebook_id):
                # Check to make sure another voter isn't hanging onto this organization_we_vote_id
                voter_manager.clear_out_collisions_for_linked_organization_we_vote_id(voter.we_vote_id,
                                                                                      organization.we_vote_id)
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()

                    # TODO DALE UPDATE positions to add voter_we_vote_id - Any position with
                    # the organization_we_vote_id should get the voter_we_vote_id added,
                    # and any position with the voter_we_vote_id should get the organization_we_vote_id added
                except Exception as e:
                    success = False
                    status += " UNABLE_TO_UPDATE_VOTER_WITH_ORGANIZATION_WE_VOTE_ID_FROM_FACEBOOK "

        # Now see about adding chosen_subdomain_string networking information
        if positive_value_exists(chosen_subdomain_string) or positive_value_exists(chosen_subdomain_string_previous):
            if positive_value_exists(chosen_subdomain_string):
                subdomain_results = get_wevote_subdomain_status(chosen_subdomain_string)
                status += subdomain_results['status']
                if not subdomain_results['success']:
                    status += "COULD_NOT_GET_SUBDOMAIN_STATUS "
                elif not positive_value_exists(subdomain_results['subdomain_exists']):
                    # If here, this is a new chosen_subdomain_string to add to our network
                    status += "NEW_CHOSEN_SUBDOMAIN_STRING_DOES_NOT_EXIST "
                    add_results = add_wevote_subdomain_to_fastly(chosen_subdomain_string)
                    status += add_results['status']
                else:
                    status += "CHOSEN_SUBDOMAIN_ALREADY_EXISTS "
            if positive_value_exists(chosen_subdomain_string_previous):
                if chosen_subdomain_string_previous is not chosen_subdomain_string:
                    # Any benefit to deleting prior subdomain from Fastly?
                    pass

        if positive_value_exists(chosen_subdomain_string):
            # add domain to aws route53 DNS
            route53_results = add_subdomain_route53_record(chosen_subdomain_string)
            if route53_results['success']:
                status += "SUBDOMAIN_ROUTE53_ADDED "
            else:
                status += route53_results['status']
                status += "SUBDOMAIN_ROUTE53_NOT_ADDED "
            # We don't delete subdomain records from our DNS

        # Voter guide names are currently locked to the organization name, so we want to update all voter guides
        voter_guide_manager = VoterGuideManager()
        results = voter_guide_manager.update_organization_voter_guides_with_organization_data(organization)
        position_results = update_position_entered_details_from_organization(organization)

        # Favor the Twitter banner and profile image if they exist
        # From Dale September 1, 2017:  Eventually we would like to let a person choose which they want to display,
        # but for now Twitter always wins out.
        we_vote_hosted_profile_image_url_large = organization.we_vote_hosted_profile_image_url_large if \
            positive_value_exists(organization.we_vote_hosted_profile_image_url_large) else \
            organization.organization_photo_url()

        if positive_value_exists(organization.twitter_profile_banner_url_https):
            organization_banner_url = organization.twitter_profile_banner_url_https
        else:
            organization_banner_url = organization.facebook_background_image_url_https

        if isinstance(organization_banner_url, list):
            # If a list, just return the first one
            organization_banner_url = organization_banner_url.pop()
        elif isinstance(organization_banner_url, tuple):
            # If a tuple, just return the first one
            organization_banner_url = organization_banner_url[0]

        results = {
            'success':                          success,
            'status':                           status,
            'voter_device_id':                  voter_device_id,
            'chosen_domain_string':             organization.chosen_domain_string,
            'chosen_domain_string2':            organization.chosen_domain_string2,
            'chosen_domain_string3':            organization.chosen_domain_string3,
            'chosen_favicon_url_https':         organization.chosen_favicon_url_https,
            'chosen_google_analytics_tracking_id': organization.chosen_google_analytics_tracking_id,
            'chosen_html_verification_string':  organization.chosen_html_verification_string,
            'chosen_hide_we_vote_logo':         organization.chosen_hide_we_vote_logo,
            'chosen_logo_url_https':            organization.chosen_logo_url_https,
            'chosen_prevent_sharing_opinions':  organization.chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text':   organization.chosen_ready_introduction_text,
            'chosen_ready_introduction_title':  organization.chosen_ready_introduction_title,
            'chosen_social_share_description':  organization.chosen_social_share_description,
            'chosen_social_share_image_256x256_url_https': organization.chosen_social_share_image_256x256_url_https,
            'chosen_subdomain_string':          organization.chosen_subdomain_string,
            'chosen_subscription_plan':         organization.chosen_subscription_plan,
            'subscription_plan_end_day_text':   organization.subscription_plan_end_day_text,
            'subscription_plan_features_active': organization.subscription_plan_features_active,
            'chosen_feature_package':           organization.chosen_feature_package,
            'features_provided_bitmap':         organization.features_provided_bitmap,
            'organization_id':                  organization.id,
            'organization_we_vote_id':          organization.we_vote_id,
            'new_organization_created':         save_results['new_organization_created'],
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_description':
                organization.organization_description if positive_value_exists(organization.organization_description)
                else '',
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_website':
                organization.organization_website if positive_value_exists(organization.organization_website) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
            'organization_instagram_handle':
                organization.organization_instagram_handle
                if positive_value_exists(organization.organization_instagram_handle) else '',
            'organization_banner_url':          organization_banner_url,
            'organization_photo_url':           organization.organization_photo_url()
                if positive_value_exists(organization.organization_photo_url()) else '',
            'organization_photo_url_large':     we_vote_hosted_profile_image_url_large,
            'organization_photo_url_medium':    organization.we_vote_hosted_profile_image_url_medium,
            'organization_photo_url_tiny':      organization.we_vote_hosted_profile_image_url_tiny,
            'organization_twitter_handle':      organization.organization_twitter_handle if positive_value_exists(
                organization.organization_twitter_handle) else '',
            'organization_type':                organization.organization_type if positive_value_exists(
                organization.organization_type) else '',
            'twitter_followers_count':          organization.twitter_followers_count if positive_value_exists(
                organization.twitter_followers_count) else 0,
            'twitter_description':              organization.twitter_description if positive_value_exists(
                organization.twitter_description) else '',
            'refresh_from_twitter':             refresh_from_twitter,
            'facebook_id':                      organization.facebook_id if positive_value_exists(
                organization.facebook_id) else 0,
        }
        return results
    else:
        results = {
            'success':                              False,
            'status':                               save_results['status'],
            'voter_device_id':                      voter_device_id,
            'chosen_domain_string':                 chosen_domain_string,
            'chosen_domain_string2':                chosen_domain_string2,
            'chosen_domain_string3':                chosen_domain_string3,
            'chosen_favicon_url_https':             '',
            'chosen_google_analytics_tracking_id':  chosen_google_analytics_tracking_id,
            'chosen_html_verification_string':      chosen_html_verification_string,
            'chosen_hide_we_vote_logo':             chosen_hide_we_vote_logo,
            'chosen_logo_url_https':                '',
            'chosen_prevent_sharing_opinions':      chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text':       chosen_ready_introduction_text,
            'chosen_ready_introduction_title':      chosen_ready_introduction_title,
            'chosen_social_share_description':      chosen_social_share_description,
            'chosen_social_share_image_256x256_url_https': '',
            'chosen_subdomain_string':              chosen_subdomain_string,
            'chosen_subscription_plan':             chosen_subscription_plan,
            'subscription_plan_end_day_text':       '',
            'subscription_plan_features_active':    '',
            'chosen_feature_package':               '',
            'features_provided_bitmap':             '',
            'organization_id':                      organization_id,
            'organization_we_vote_id':              organization_we_vote_id,
            'new_organization_created':             save_results['new_organization_created'],
            'organization_name':                    organization_name,
            'organization_email':                   organization_email,
            'organization_website':                 organization_website,
            'organization_facebook':                organization_facebook,
            'organization_photo_url':               organization_image,
            'organization_twitter_handle':          organization_twitter_handle,
            'organization_type':                    organization_type,
            'twitter_followers_count':              0,
            'twitter_description':                  "",
            'refresh_from_twitter':                 refresh_from_twitter,
            'facebook_id':                          facebook_id,
        }
        return results


def organization_search_for_api(organization_name, organization_twitter_handle, organization_website,
                                organization_email, organization_search_term, exact_match):
    """
    organization_search_for_api  # organizationSearch
    :param organization_name:
    :param organization_twitter_handle:
    :param organization_website:
    :param organization_email:
    :param organization_search_term:
    :param exact_match:
    :return:
    """
    organization_search_term = organization_search_term.strip()
    organization_name = organization_name.strip()
    organization_twitter_handle = organization_twitter_handle.strip()
    organization_website = organization_website.strip()
    organization_email = organization_email.strip()

    # We need at least one term to search for
    if not positive_value_exists(organization_search_term) \
            and not positive_value_exists(organization_name)\
            and not positive_value_exists(organization_twitter_handle)\
            and not positive_value_exists(organization_website)\
            and not positive_value_exists(organization_email):
        json_data = {
            'status':                       "ORGANIZATION_SEARCH_ALL_TERMS_MISSING",
            'success':                      False,
            'exact_match':                  exact_match,
            'organization_search_term':     organization_search_term,
            'organization_name':            organization_name,
            'organization_twitter_handle':  organization_twitter_handle,
            'organization_website':         organization_website,
            'organization_email':           organization_email,
            'organizations_list':           [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_list_manager = OrganizationListManager()
    organization_facebook = None
    results = organization_list_manager.organization_search_find_any_possibilities(
        organization_name, organization_twitter_handle, organization_website, organization_email,
        organization_facebook, organization_search_term, exact_match=exact_match)

    organizations_list = []
    if results['organizations_found']:
        organizations_list = results['organizations_list']
    json_data = {
        'status':                       results['status'],
        'success':                      True,
        'exact_match':                  exact_match,
        'organization_search_term':     organization_search_term,
        'organization_name':            organization_name,
        'organization_twitter_handle':  organization_twitter_handle,
        'organization_website':         organization_website,
        'organization_email':           organization_email,
        'organizations_list':           organizations_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def refresh_organizations_for_one_election(google_civic_election_id):
    success = True
    status = ""

    voter_guide_list_manager = VoterGuideListManager()
    google_civic_election_id_list = [google_civic_election_id]
    results = voter_guide_list_manager.retrieve_voter_guides_for_election(google_civic_election_id_list)

    if results['voter_guide_list_found']:
        voter_guide_list = results['voter_guide_list']
        for one_voter_guide in voter_guide_list:
            if positive_value_exists(one_voter_guide.organization_we_vote_id):
                refresh_results = refresh_organization_data_from_master_tables(one_voter_guide.organization_we_vote_id)

    results = {
        'success': success,
        'status': status,
    }
    return results


def refresh_organization_data_from_master_tables(organization_we_vote_id):
    twitter_profile_image_url_https = None
    twitter_profile_background_image_url_https = None
    twitter_profile_banner_url_https = None
    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None
    twitter_dict = {}
    success = False
    status = ""
    organization_updated = True

    organization_manager = OrganizationManager()
    twitter_user_manager = TwitterUserManager()
    voter_manager = VoterManager()

    results = organization_manager.retrieve_organization(0, organization_we_vote_id)
    status += results['status']
    if not results['organization_found']:
        status += "REFRESH_ORGANIZATION_FROM_MASTER_TABLES-ORGANIZATION_NOT_FOUND "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    organization = results['organization']

    # Retrieve voter data from Voter table
    # voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization_we_vote_id)

    twitter_id_belongs_to_this_organization = False
    twitter_user_id = organization.twitter_user_id
    twitter_link_to_org_results = twitter_user_manager.\
        retrieve_twitter_link_to_organization_from_organization_we_vote_id(organization_we_vote_id)
    if twitter_link_to_org_results['twitter_link_to_organization_found']:
        # If here, we have found a twitter_link_to_organization entry for this organization
        twitter_user_id = twitter_link_to_org_results['twitter_link_to_organization'].twitter_id
        twitter_id_belongs_to_this_organization = True
    else:
        # If here, a twitter_link_to_organization entry was not found for the organization
        # Is the organization.twitter_user_id stored in the organization object in use by any other group?
        if positive_value_exists(organization.twitter_user_id):
            results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
                organization.twitter_user_id)
            if results['twitter_link_to_organization_found']:
                # If here, then we know that the Twitter id is being used by another group, so we want to wipe out the
                # value from this organization.
                try:
                    organization.organization_twitter_handle = None
                    organization.twitter_user_id = None
                    organization.twitter_followers_count = 0
                    organization.save()
                except Exception as e:
                    status += "COULD_NOT_SAVE_ORGANIZATION: " + str(e) + " "
            else:
                # Not attached to other group, so create a TwitterLinkToOrganization entry
                results = twitter_user_manager.create_twitter_link_to_organization(
                    twitter_user_id, organization_we_vote_id)
                if results['twitter_link_to_organization_saved']:
                    twitter_id_belongs_to_this_organization = True

    # Retrieve twitter user data from TwitterUser Table
    if twitter_id_belongs_to_this_organization:
        twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_user_id)
        if twitter_user_results['twitter_user_found']:
            twitter_user = twitter_user_results['twitter_user']
            if twitter_user.twitter_handle != organization.organization_twitter_handle or \
                    twitter_user.twitter_name != organization.twitter_name or \
                    twitter_user.twitter_location != organization.twitter_location or \
                    twitter_user.twitter_followers_count != organization.twitter_followers_count or \
                    twitter_user.twitter_description != organization.twitter_description:
                twitter_dict = {
                    'id':               twitter_user.twitter_id,
                    'username':      twitter_user.twitter_handle,
                    'name':             twitter_user.twitter_name,
                    'followers_count':  twitter_user.twitter_followers_count,
                    'location':         twitter_user.twitter_location,
                    'description':      twitter_user.twitter_description,
                }

        # Retrieve organization images data from WeVoteImage table
        we_vote_image_list = retrieve_all_images_for_one_organization(organization.we_vote_id)
        if len(we_vote_image_list):
            # Retrieve all cached image for this organization
            for we_vote_image in we_vote_image_list:
                if we_vote_image.kind_of_image_twitter_profile:
                    if we_vote_image.kind_of_image_original:
                        twitter_profile_image_url_https = we_vote_image.we_vote_image_url
                    if we_vote_image.kind_of_image_large:
                        we_vote_hosted_profile_image_url_large = we_vote_image.we_vote_image_url
                    if we_vote_image.kind_of_image_medium:
                        we_vote_hosted_profile_image_url_medium = we_vote_image.we_vote_image_url
                    if we_vote_image.kind_of_image_tiny:
                        we_vote_hosted_profile_image_url_tiny = we_vote_image.we_vote_image_url
                elif we_vote_image.kind_of_image_twitter_background and we_vote_image.kind_of_image_original:
                    twitter_profile_background_image_url_https = we_vote_image.we_vote_image_url
                elif we_vote_image.kind_of_image_twitter_banner and we_vote_image.kind_of_image_original:
                    twitter_profile_banner_url_https = we_vote_image.we_vote_image_url

        update_organization_results = organization_manager.update_organization_twitter_details(
            organization, twitter_dict, twitter_profile_image_url_https,
            twitter_profile_background_image_url_https, twitter_profile_banner_url_https,
            we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny)
        success = update_organization_results['success']
        if success:
            organization_updated = True
        status += update_organization_results['status']

    results = {
        'success':              success,
        'status':               status,
        'organization_updated': organization_updated,
    }
    return results


def push_organization_data_to_other_table_caches(organization_we_vote_id):
    organization_manager = OrganizationManager()
    voter_guide_manager = VoterGuideManager()
    results = organization_manager.retrieve_organization(0, organization_we_vote_id)
    organization = results['organization']

    save_voter_guide_from_organization_results = \
        voter_guide_manager.update_organization_voter_guides_with_organization_data(organization)

    save_position_from_organization_results = update_position_entered_details_from_organization(organization)


def retrieve_organizations_followed(voter_id, auto_followed_from_twitter_suggestion=False):
    organization_list_found = False
    organization_list = []
    status = ''
    success = True

    follow_organization_list_manager = FollowOrganizationList()
    try:
        organization_ids_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
                voter_id, auto_followed_from_twitter_suggestion=auto_followed_from_twitter_suggestion)
    except Exception as e:
        organization_ids_followed_by_voter = []
        status += "RETRIEVE_FOLLOW_ORGANIZATION_FAILED: " + str(e) + " "
        success = False

    if success:
        organization_list_manager = OrganizationListManager()
        results = organization_list_manager.retrieve_organizations_by_id_list(organization_ids_followed_by_voter)
        if results['organization_list_found']:
            organization_list = results['organization_list']
            if len(organization_list):
                organization_list_found = True
                status = 'SUCCESSFUL_RETRIEVE_OF_ORGANIZATIONS_FOLLOWED'
            else:
                status = 'ORGANIZATIONS_FOLLOWED_NOT_FOUND'
        else:
            status = results['status']
            if not results['success']:
                success = False

    results = {
        'success':                      success,
        'status':                       status,
        'organization_list_found':      organization_list_found,
        'organization_list':            organization_list,
    }
    return results


def retrieve_organization_list_for_all_upcoming_elections(limit_to_this_state_code="",
                                                          return_list_of_objects=False,
                                                          super_light_organization_list=False,
                                                          candidate_we_vote_id_to_include=""):

    status = ""
    success = True
    organization_list_objects = []
    organization_list_light = []
    organization_list_found = False

    organization_list_manager = OrganizationListManager()
    results = organization_list_manager.retrieve_public_organizations_for_upcoming_elections(
        limit_to_this_state_code=limit_to_this_state_code,
        return_list_of_objects=return_list_of_objects,
        super_light_organization_list=super_light_organization_list,
        candidate_we_vote_id_to_include=candidate_we_vote_id_to_include,
    )
    if results['organization_list_found']:
        organization_list_found = True
        organization_list_light = results['organization_list_light']
    else:
        status += results['status']
        success = results['success']

    results = {
        'success': success,
        'status': status,
        'organization_list_found':          organization_list_found,
        'organization_list_objects':        organization_list_objects if return_list_of_objects else [],
        'organization_list_light':          organization_list_light,
        'return_list_of_objects':           return_list_of_objects,
        'super_light_candidate_list':       super_light_organization_list,
    }
    return results


def site_configuration_retrieve_for_api(hostname):  # siteConfigurationRetrieve
    """
    Called from siteConfigurationRetrieve api
    :param hostname:
    :return:
    """
    status = ""
    success = True
    chosen_about_organization_external_url = ''
    chosen_domain_type_is_campaign = False
    chosen_google_analytics_tracking_id = False
    chosen_hide_we_vote_logo = False
    chosen_logo_url_https = ''
    chosen_prevent_sharing_opinions = False
    chosen_ready_introduction_text = ''
    chosen_ready_introduction_title = ''
    chosen_website_name = ''
    features_provided_bitmap = 0
    organization_we_vote_id = ''
    reserved_by_we_vote = False
    if not positive_value_exists(hostname):
        status += "HOSTNAME_MISSING "
        results = {
            'success':                                  success,
            'status':                                   status,
            'chosen_about_organization_external_url':   chosen_about_organization_external_url,
            'chosen_domain_type_is_campaign':           chosen_domain_type_is_campaign,
            'chosen_google_analytics_tracking_id':      chosen_google_analytics_tracking_id,
            'chosen_hide_we_vote_logo':                 chosen_hide_we_vote_logo,
            'chosen_logo_url_https':                    chosen_logo_url_https,
            'chosen_prevent_sharing_opinions':          chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text':           chosen_ready_introduction_text,
            'chosen_ready_introduction_title':          chosen_ready_introduction_title,
            'chosen_website_name':                      chosen_website_name,
            'features_provided_bitmap':                 features_provided_bitmap,
            'hostname':                                 hostname,
            'organization_we_vote_id':                  organization_we_vote_id,
            'reserved_by_we_vote':                      reserved_by_we_vote,
        }
        return results

    organization_manager = OrganizationManager()
    try:
        hostname = hostname.strip().lower()
        hostname = hostname.replace('http://', '')
        hostname = hostname.replace('https://', '')
    except Exception as e:
        status += "COULD_NOT_MODIFY_HOSTNAME: " + str(e) + " "
        success = False
        hostname = ""
        results = {
            'success':                                  success,
            'status':                                   status,
            'chosen_about_organization_external_url':   chosen_about_organization_external_url,
            'chosen_domain_type_is_campaign':           chosen_domain_type_is_campaign,
            'chosen_google_analytics_tracking_id':      chosen_google_analytics_tracking_id,
            'chosen_hide_we_vote_logo':                 chosen_hide_we_vote_logo,
            'chosen_logo_url_https':                    chosen_logo_url_https,
            'chosen_prevent_sharing_opinions':          chosen_prevent_sharing_opinions,
            'chosen_ready_introduction_text':           chosen_ready_introduction_text,
            'chosen_ready_introduction_title':          chosen_ready_introduction_title,
            'chosen_website_name':                      chosen_website_name,
            'features_provided_bitmap':                 features_provided_bitmap,
            'hostname':                                 hostname,
            'organization_we_vote_id':                  organization_we_vote_id,
            'reserved_by_we_vote':                      reserved_by_we_vote,
        }
        return results
    results = organization_manager.retrieve_organization_from_incoming_hostname(hostname, read_only=True)
    organization_found = results['organization_found']
    organization = results['organization']
    status += results['status']

    if organization_found:
        chosen_about_organization_external_url = organization.chosen_about_organization_external_url
        chosen_domain_type_is_campaign = organization.chosen_domain_type_is_campaign
        chosen_google_analytics_tracking_id = organization.chosen_google_analytics_tracking_id
        chosen_hide_we_vote_logo = organization.chosen_hide_we_vote_logo
        chosen_logo_url_https = organization.chosen_logo_url_https
        chosen_prevent_sharing_opinions = organization.chosen_prevent_sharing_opinions
        chosen_ready_introduction_text = organization.chosen_ready_introduction_text
        chosen_ready_introduction_title = organization.chosen_ready_introduction_title
        chosen_website_name = organization.chosen_website_name
        features_provided_bitmap = organization.features_provided_bitmap
        organization_we_vote_id = organization.we_vote_id
    else:
        reserved_results = organization_manager.retrieve_organization_reserved_hostname(hostname, read_only=True)
        if reserved_results['hostname_is_reserved']:
            reserved_by_we_vote = True
            status += "HOSTNAME_RESERVED_BY_WE_VOTE "

    if not positive_value_exists(organization_we_vote_id) and not reserved_by_we_vote:
        # If this hostname is not owned by organization or reserved by We Vote, return empty string so the WebApp
        # knows to default to WeVote.US
        hostname = ""
        status += "HOSTNAME_NOT_OWNED_BY_ORG_OR_RESERVED_BY_WE_VOTE "

    results = {
        'success':                                  success,
        'status':                                   status,
        'chosen_about_organization_external_url':   chosen_about_organization_external_url,
        'chosen_domain_type_is_campaign':           chosen_domain_type_is_campaign,
        'chosen_google_analytics_tracking_id':      chosen_google_analytics_tracking_id,
        'chosen_hide_we_vote_logo':                 chosen_hide_we_vote_logo,
        'chosen_logo_url_https':                    chosen_logo_url_https,
        'chosen_prevent_sharing_opinions':          chosen_prevent_sharing_opinions,
        'chosen_ready_introduction_text':           chosen_ready_introduction_text,
        'chosen_ready_introduction_title':          chosen_ready_introduction_title,
        'chosen_website_name':                      chosen_website_name,
        'features_provided_bitmap':                 features_provided_bitmap,
        'hostname':                                 hostname,
        'organization_we_vote_id':                  organization_we_vote_id,
        'reserved_by_we_vote':                      reserved_by_we_vote,
    }
    return results


def transform_campaigns_url(campaigns_root_url):
    campaigns_root_url_verified = CAMPAIGNS_ROOT_URL
    if positive_value_exists(campaigns_root_url):
        configuration_results = site_configuration_retrieve_for_api(campaigns_root_url)
        # Make sure hostname is allowed or success if False -- we clear it out if it is not allowed
        if positive_value_exists(configuration_results['hostname']):
            # If this hostname is either reserved by We Vote or a current organization is found, then use the custom URL
            if positive_value_exists(configuration_results['reserved_by_we_vote']) \
                    or positive_value_exists(configuration_results['organization_we_vote_id']):
                campaigns_root_url_verified = 'https://{hostname}'.format(hostname=configuration_results['hostname'])
    return campaigns_root_url_verified


def transform_web_app_url(web_app_root_url):
    web_app_root_url_verified = WEB_APP_ROOT_URL
    if positive_value_exists(web_app_root_url):
        configuration_results = site_configuration_retrieve_for_api(web_app_root_url)
        # Make sure hostname is allowed or success if False -- we clear it out if it is not allowed
        if positive_value_exists(configuration_results['hostname']):
            # If this hostname is either reserved by We Vote or a current organization is found, then use the custom URL
            if positive_value_exists(configuration_results['reserved_by_we_vote']) \
                    or positive_value_exists(configuration_results['organization_we_vote_id']):
                web_app_root_url_verified = 'https://{hostname}'.format(hostname=configuration_results['hostname'])
    return web_app_root_url_verified


def organization_politician_match(organization):
    politician_manager = PoliticianManager()
    status = ''
    success = True

    # Does this organization already have a we_vote_id for a politician?
    if positive_value_exists(organization.politician_we_vote_id):
        # Find existing politician. No update here for now.
        results = politician_manager.retrieve_politician(
            politician_we_vote_id=organization.politician_we_vote_id,
            read_only=True)
        status += results['status']
        if not results['success']:
            results = {
                'success':                  False,
                'status':                   status,
                'politician_list_found':    False,
                'politician_list':          [],
                'politician_found':         False,
                'politician_created':       False,
                'politician':               None,
            }
            return results
        elif results['politician_found']:
            politician = results['politician']
            # Save politician_we_vote_id in organization
            organization.politician_we_vote_id = politician.we_vote_id
            organization.save()

            results = {
                'success':                  results['success'],
                'status':                   status,
                'politician_list_found':    False,
                'politician_list':          [],
                'politician_found':         results['politician_found'],
                'politician_created':       False,
                'politician':               results['politician'],
            }
            return results
        else:
            # Politician wasn't found, so clear out politician_we_vote_id and politician_id
            organization.politician_we_vote_id = None
            organization.save()

    # Search the politician table for a stricter match (don't match on "dan" if "dan smith" passed in)
    #  so we set return_close_matches to False
    from wevote_functions.functions import add_to_list_if_positive_value_exists
    facebook_url_list = []
    facebook_url_list = add_to_list_if_positive_value_exists(organization.organization_facebook, facebook_url_list)
    full_name_list = []
    full_name_list = add_to_list_if_positive_value_exists(organization.organization_name, full_name_list)
    twitter_handle_list = []
    twitter_handle_list = \
        add_to_list_if_positive_value_exists(organization.organization_twitter_handle, twitter_handle_list)
    results = politician_manager.retrieve_all_politicians_that_might_match_similar_object(
        facebook_url_list=facebook_url_list,
        full_name_list=full_name_list,
        instagram_handle=organization.organization_instagram_handle,
        return_close_matches=False,
        state_code=organization.state_served_code,
        twitter_handle_list=twitter_handle_list,
        vote_smart_id=organization.vote_smart_id,
    )
    status += results['status']
    if not results['success']:
        results = {
            'success':                  False,
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_list_found']:
        # If here, return the list but don't link the organization
        politician_list = results['politician_list']

        results = {
            'success':                  True,
            'status':                   status,
            'politician_list_found':    True,
            'politician_list':          politician_list,
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_found']:
        # Save this politician_we_vote_id with the organization
        politician = results['politician']
        # Save politician_we_vote_id in we_vote_representative
        organization.politician_we_vote_id = politician.we_vote_id
        organization.politician_id = politician.id
        organization.save()

        results = {
            'success':                  True,
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         True,
            'politician_created':       False,
            'politician':               politician,
        }
        return results
    else:
        # Create new politician for this organization
        create_results = politician_manager.create_politician_from_similar_object(organization)
        status += create_results['status']
        if create_results['politician_found']:
            politician = create_results['politician']
            # Save politician_we_vote_id in we_vote_representative
            organization.politician_we_vote_id = politician.we_vote_id
            organization.politician_id = politician.id
            organization.save()

        results = {
            'success':                      create_results['success'],
            'status':                       status,
            'politician_list_found':        False,
            'politician_list':              [],
            'politician_found':             create_results['politician_found'],
            'politician_created':           create_results['politician_created'],
            'politician':                   create_results['politician'],
        }
        return results


def update_social_media_statistics_in_other_tables(organization):
    """
    Update other tables that use any of these social media statistics
    DALE 2017-11-06 This function is used several places, but I don't think it is doing what is implied by its name
    :param organization:
    :return:
    """

    voter_guide_manager = VoterGuideManager()
    voter_guide_results = voter_guide_manager.update_voter_guide_social_media_statistics(organization)

    if voter_guide_results['success'] and voter_guide_results['voter_guide']:
        voter_guide = voter_guide_results['voter_guide']
    else:
        voter_guide = VoterGuide()

    status = "FINISHED_UPDATE_SOCIAL_MEDIA_STATISTICS_IN_OTHER_TABLES"

    results = {
        'success':      True,
        'status':       status,
        'organization': organization,
        'voter_guide':  voter_guide,
    }
    return results


def save_image_to_organization_table(organization, image_url, source_link, url_is_broken, kind_of_source_website=None):
    status = ''
    success = True
    cache_results = {
        'we_vote_hosted_profile_image_url_large':   None,
        'we_vote_hosted_profile_image_url_medium':  None,
        'we_vote_hosted_profile_image_url_tiny':    None
    }

    if not positive_value_exists(kind_of_source_website):
        kind_of_source_website = extract_website_from_url(source_link)
    # if IMAGE_SOURCE_BALLOTPEDIA in kind_of_source_website:
    #     cache_results = cache_master_and_resized_image(
    #         organization_id=organization.id, organization_we_vote_id=organization.we_vote_id,
    #         ballotpedia_profile_image_url=image_url,
    #         image_source=IMAGE_SOURCE_BALLOTPEDIA)
    #     cached_ballotpedia_profile_image_url_https = cache_results['cached_ballotpedia_image_url_https']
    #     organization.ballotpedia_photo_url = cached_ballotpedia_profile_image_url_https
    #     organization.ballotpedia_page_title = source_link
    #
    # elif LINKEDIN in kind_of_source_website:
    #     cache_results = cache_master_and_resized_image(
    #         organization_id=organization.id, organization_we_vote_id=organization.we_vote_id,
    #         linkedin_profile_image_url=image_url,
    #         image_source=LINKEDIN)
    #     cached_linkedin_profile_image_url_https = cache_results['cached_linkedin_image_url_https']
    #     organization.linkedin_url = source_link
    #     organization.linkedin_photo_url = cached_linkedin_profile_image_url_https
    #
    # elif WIKIPEDIA in kind_of_source_website:
    #     cache_results = cache_master_and_resized_image(
    #         organization_id=organization.id, organization_we_vote_id=organization.we_vote_id,
    #         wikipedia_profile_image_url=image_url,
    #         image_source=WIKIPEDIA)
    #     cached_wikipedia_profile_image_url_https = cache_results['cached_wikipedia_image_url_https']
    #     organization.wikipedia_photo_url = cached_wikipedia_profile_image_url_https
    #     organization.wikipedia_page_title = source_link
    #
    # elif TWITTER in kind_of_source_website:
    #     twitter_screen_name = extract_twitter_handle_from_text_string(source_link)
    #     organization.twitter_name = twitter_screen_name
    #     organization.twitter_url = source_link

    if FACEBOOK in kind_of_source_website:
        # organization.facebook_url_is_broken = url_is_broken
        if not url_is_broken:
            cache_results = cache_master_and_resized_image(
                organization_id=organization.id,
                organization_we_vote_id=organization.we_vote_id,
                facebook_profile_image_url_https=image_url,
                image_source=FACEBOOK)
            cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
            organization.facebook_url = source_link
            organization.facebook_profile_image_url_https = cached_facebook_profile_image_url_https
        else:
            organization.facebook_profile_image_url_https = None

    # else:
    #     cache_results = cache_master_and_resized_image(
    #         organization_id=organization.id,
    #         organization_we_vote_id=organization.we_vote_id,
    #         other_source_image_url=image_url,
    #         other_source=kind_of_source_website)
    #     cached_other_source_image_url_https = cache_results['cached_other_source_image_url_https']
    #     organization.other_source_url = source_link
    #     organization.other_source_photo_url = cached_other_source_image_url_https

    try:
        if not url_is_broken:
            we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
            we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
            organization.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
            organization.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
            organization.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
        organization.save()
    except Exception as e:
        status += "ORGANIZATION_NOT_SAVED: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
    }
    return results
