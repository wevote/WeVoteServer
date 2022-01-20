# import_export_twitter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/controllers.py for routines that manage internal twitter data
import os
import re
import ssl
import urllib.request
from datetime import timedelta
from math import floor, log2
from re import sub
from socket import timeout
from time import time

import tweepy
from django.db.models import Q
from django.utils.timezone import now

import wevote_functions.admin
from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching
from candidate.controllers import refresh_candidate_data_from_master_tables
from candidate.models import CandidateCampaign, CandidateManager, CandidateListManager
from config.base import get_environment_variable
from election.models import ElectionManager
from image.controllers import TWITTER, cache_master_and_resized_image
from image.models import WeVoteImageManager
from import_export_batches.models import BatchProcessManager, UPDATE_TWITTER_DATA_FROM_TWITTER
from import_export_twitter.models import TwitterAuthManager
from office.models import ContestOfficeManager
from organization.controllers import move_organization_to_another_complete, \
    update_social_media_statistics_in_other_tables
from organization.models import Organization, OrganizationListManager, OrganizationManager, INDIVIDUAL
from politician.models import PoliticianManager
from position.controllers import update_all_position_details_from_candidate, \
    update_position_entered_details_from_organization, update_position_for_friends_details_from_voter
from twitter.functions import retrieve_twitter_user_info
from twitter.models import TwitterLinkPossibility, TwitterUserManager
from voter.models import VoterManager
from voter_guide.models import VoterGuideListManager
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, \
    is_voter_device_id_valid, positive_value_exists, convert_state_code_to_state_text, \
    convert_state_code_to_utc_offset, \
    POSITIVE_SEARCH_KEYWORDS, NEGATIVE_SEARCH_KEYWORDS, \
    POSITIVE_TWITTER_HANDLE_SEARCH_KEYWORDS, NEGATIVE_TWITTER_HANDLE_SEARCH_KEYWORDS
from wevote_settings.models import RemoteRequestHistory, RemoteRequestHistoryManager, \
    RETRIEVE_POSSIBLE_TWITTER_HANDLES, RETRIEVE_UPDATE_DATA_FROM_TWITTER

logger = wevote_functions.admin.get_logger(__name__)

TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")


# We added this so that we don't get stopped by SSL certificate complaints
if not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
    ssl._create_default_https_context = ssl._create_unverified_context

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

# RE_FACEBOOK = r'//www\.twitter\.com/(?:#!/)?(\w+)'
RE_FACEBOOK = r'/(?:https?:\/\/)?(?:www\.)?facebook\.com\/(?:(?:\w)*#!\/)?(?:pages\/)?(?:[\w\-]*\/)*?(\/)?([^/?]*)/'
FACEBOOK_BLACKLIST = ['group', 'group.php', 'None']
# NOTE: Scraping a website for the Facebook handle is more complicated than Twitter. There must be an existing
#  solution available? My attempt turned off for now.

# Only pays attention to https://twitter.com or http://twitter.com and ignores www.twitter.com
RE_TWITTER = r'//twitter\.com/(?:#!/)?(\w+)'
RE_TWITTER_WWW = r'//www\.twitter\.com/(?:#!/)?(\w+)'
TWITTER_BLACKLIST = ['home', 'https', 'intent', 'none', 'search', 'share', 'twitterapi', 'wix']
TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_NATIVE_INDICATOR = 'native'


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


class GetOutOfLoop(Exception):
    pass


class GetOutOfLoopLocal(Exception):
    pass


def analyze_twitter_search_results(
        search_results=[],
        candidate_name={},
        candidate=None,
        possible_twitter_handles_list=[]):
    search_term = candidate.candidate_name
    state_code = candidate.state_code
    state_full_name = convert_state_code_to_state_text(state_code)
    search_results_length = 0
    if search_results and len(search_results) > 0:
        search_results_length = len(search_results)

    for possible_candidate_index in range(search_results_length):
        one_result = search_results[possible_candidate_index]
        likelihood_score = 0

        # Increase the score with increased followers count
        if positive_value_exists(one_result.followers_count):
            #  125 followers =  0 points
            #  250 followers = 10 points
            #  500 followers = 20 points
            # 1000 followers = 30 points
            followers_likelihood = floor(10.0 * log2(one_result.followers_count / 125.0))
            if positive_value_exists(followers_likelihood):
                if followers_likelihood > 30:
                    likelihood_score += 30
                else:
                    likelihood_score += followers_likelihood

        # Check if name (or parts of name) are in Twitter name and handle
        name_found_in_name = False
        name_found_in_screen_name = False
        screen_name_handling_regex = r"[^a-zA-Z]"
        for name in candidate_name.values():
            if len(name) and name in one_result.name:
                likelihood_score += 10
                name_found_in_name = True
            if len(name) and sub(screen_name_handling_regex, "", name).lower() in \
                             sub(screen_name_handling_regex, "", one_result.screen_name).lower():
                likelihood_score += 10
                name_found_in_screen_name = True

        if not name_found_in_name:
            likelihood_score -= 30
        if not name_found_in_screen_name:
            likelihood_score -= 20

        # Check if state or state code is in location or description
        if one_result.location and positive_value_exists(state_full_name) and state_full_name in one_result.location:
            likelihood_score += 30
        elif one_result.location and positive_value_exists(state_code) and state_code in one_result.location:
            likelihood_score += 20

        if one_result.description and positive_value_exists(state_full_name) and \
                state_full_name in one_result.description:
            likelihood_score += 20
        if one_result.description and positive_value_exists(state_code) and \
                state_code in one_result.description:
            likelihood_score += 10

        # Check if user time zone is close to election/state time zone
        state_utc_offset = convert_state_code_to_utc_offset(state_code)
        if one_result.utc_offset and state_utc_offset and abs(state_utc_offset - one_result.utc_offset) > 7200:
            likelihood_score -= 30

        # Check if candidate's party is in description
        political_party = candidate.political_party_display()
        if one_result.description and positive_value_exists(political_party) and \
                political_party in one_result.description:
            likelihood_score += 20

        # Check (each word individually) if office name is in description
        office_name = candidate.contest_office_name
        if positive_value_exists(office_name) and one_result.description:
            office_name = office_name.split()
            office_found_in_description = False
            for word in office_name:
                if len(word) > 1 and word in one_result.description:
                    likelihood_score += 10
                    office_found_in_description = True
            if not office_found_in_description:
                likelihood_score -= 10

        # Increase the score for every positive twitter handle keyword we find
        for keyword in POSITIVE_TWITTER_HANDLE_SEARCH_KEYWORDS:
            if one_result.screen_name and keyword in one_result.screen_name.lower():
                likelihood_score += 20

        # Decrease the score for every negative twitter handle keyword we find
        for keyword in NEGATIVE_TWITTER_HANDLE_SEARCH_KEYWORDS:
            if one_result.screen_name and keyword in one_result.screen_name.lower():
                likelihood_score -= 20

        # Increase the score for every positive keyword we find
        for keyword in POSITIVE_SEARCH_KEYWORDS:
            if one_result.description and keyword in one_result.description.lower():
                likelihood_score += 5

        # Decrease the score for every negative keyword we find
        for keyword in NEGATIVE_SEARCH_KEYWORDS:
            if one_result.description and keyword in one_result.description.lower():
                likelihood_score -= 20

        # Decrease the score for inactive accounts
        try:
            time_last_active = one_result.status.created_at.timestamp()
            time_difference = time() - time_last_active
            if positive_value_exists(time_difference):
                #  30 days = 2,592,000 seconds
                #  30 days inactive =   0 points
                #  60 days inactive = -10 points
                # 120 days inactive = -20 points
                # 240 days inactive = -30 points (etc.)
                inactivity_likelihood = floor(10.0 * log2(time_difference / 2.592e6))
                if positive_value_exists(inactivity_likelihood):
                    if inactivity_likelihood > 60:
                        likelihood_score -= 60
                    else:
                        likelihood_score -= inactivity_likelihood
        except AttributeError:
            # 'User' object (one_result) has no attribute 'status'
            # So the account likely has no tweets
            likelihood_score -= 60

        if not positive_value_exists(likelihood_score):
            likelihood_score = 0

        current_candidate_twitter_info = {
            'search_term': search_term,
            'likelihood_score': likelihood_score,
            'twitter_json': one_result._json,
        }

        possible_twitter_handles_list.append(current_candidate_twitter_info)


def fetch_number_of_candidates_needing_twitter_search():
    candidate_list_manager = CandidateListManager()
    election_manager = ElectionManager()
    status = ''
    # Run Twitter account search and analysis on candidates without a linked or possible Twitter account
    candidate_queryset = CandidateCampaign.objects.using('readonly').all()
    # Limit this search to upcoming_elections only
    results = election_manager.retrieve_upcoming_google_civic_election_id_list()
    if not positive_value_exists(results['success']):
        status += results['status']
    google_civic_election_id_list = results['upcoming_google_civic_election_id_list']
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list)
    if not positive_value_exists(results['success']):
        status += results['status']
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    candidate_queryset = candidate_queryset.filter(we_vote_id__in=candidate_we_vote_id_list)
    candidate_queryset = candidate_queryset.filter(
        Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))
    # Exclude candidates we have already have TwitterLinkPossibility data for
    try:
        twitter_possibility_list = TwitterLinkPossibility.objects.using('readonly'). \
            values_list('candidate_campaign_we_vote_id', flat=True).distinct()
        if len(twitter_possibility_list):
            candidate_queryset = candidate_queryset.exclude(we_vote_id__in=twitter_possibility_list)
    except Exception as e:
        pass
    # Exclude candidates we have requested information for in the last month
    try:
        # Exclude candidates searched for in the last month
        remote_request_query = RemoteRequestHistory.objects.using('readonly').all()
        one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
        one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
        remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
        remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_POSSIBLE_TWITTER_HANDLES)
        remote_request_list = remote_request_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
        if len(remote_request_list):
            candidate_queryset = candidate_queryset.exclude(we_vote_id__in=remote_request_list)
    except Exception as e:
        pass

    try:
        candidate_count = candidate_queryset.count()
    except Exception as e:
        candidate_count = 0

    return candidate_count


def fetch_number_of_candidates_needing_twitter_update():
    candidate_we_vote_id_list_to_exclude = []
    candidate_list_manager = CandidateListManager()
    election_manager = ElectionManager()
    status = ''
    # Run Twitter account search and analysis on candidates without a linked or possible Twitter account

    # Limit this search to upcoming_elections only
    results = election_manager.retrieve_upcoming_google_civic_election_id_list()
    if not positive_value_exists(results['success']):
        status += results['status']
    google_civic_election_id_list = results['upcoming_google_civic_election_id_list']
    # google_civic_election_id_list = [1000130]  # Temp for testing
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list)
    if not positive_value_exists(results['success']):
        status += results['status']
    upcoming_candidate_we_vote_id_list_to_include = results['candidate_we_vote_id_list']

    if len(upcoming_candidate_we_vote_id_list_to_include) > 0:
        # Exclude candidates we have requested information for in the last month
        try:
            # Exclude candidates searched for in the last month
            remote_request_query = RemoteRequestHistory.objects.using('readonly').all()
            one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
            one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
            remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
            remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_UPDATE_DATA_FROM_TWITTER)
            remote_request_query = remote_request_query.exclude(
                Q(candidate_campaign_we_vote_id__isnull=True) | Q(candidate_campaign_we_vote_id=""))
            remote_request_query = \
                remote_request_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
            candidate_we_vote_id_list_to_exclude = list(remote_request_query)
        except Exception as e:
            status += "FAILED_FETCHING_CANDIDATES_FROM_REMOTE_REQUEST_HISTORY: " + str(e) + " "

    candidate_we_vote_id_list = \
        list(set(upcoming_candidate_we_vote_id_list_to_include) - set(candidate_we_vote_id_list_to_exclude))

    candidate_count = 0
    if len(candidate_we_vote_id_list) > 0:
        try:
            candidate_queryset = CandidateCampaign.objects.using('readonly').all()
            candidate_queryset = candidate_queryset.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_queryset = candidate_queryset.exclude(candidate_twitter_updates_failing=True)
            candidate_queryset = candidate_queryset.exclude(
                Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))
            candidate_count = candidate_queryset.count()
        except Exception as e:
            candidate_count = 0

    return candidate_count


def fetch_number_of_organizations_needing_twitter_update():
    """
    Do not include individuals in this.
    :return: 
    """
    organization_we_vote_id_list_to_exclude = []
    status = ''

    # Limit to organizations with a TwitterLinkToOrganization entry
    twitter_user_manager = TwitterUserManager()
    results = twitter_user_manager.retrieve_twitter_link_to_organization_list(
        return_we_vote_id_list_only=True, read_only=True)
    organization_we_vote_id_list_to_include = results['organization_we_vote_id_list']
    
    if len(organization_we_vote_id_list_to_include):
        try:
            # Exclude organizations searched for in the last month
            remote_request_query = RemoteRequestHistory.objects.using('readonly').all()
            one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
            one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
            remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
            remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_UPDATE_DATA_FROM_TWITTER)
            remote_request_query = remote_request_query.exclude(
                Q(organization_we_vote_id__isnull=True) | Q(organization_we_vote_id=""))
            remote_request_query = remote_request_query.values_list('organization_we_vote_id', flat=True).distinct()
            organization_we_vote_id_list_to_exclude = list(remote_request_query)
        except Exception as e:
            status += "FAILED_FETCHING_ORGANIZATIONS_FROM_REMOTE_REQUEST_HISTORY: " + str(e) + " "
            return 0

    organization_we_vote_id_list = \
        list(set(organization_we_vote_id_list_to_include) - set(organization_we_vote_id_list_to_exclude))

    queryset = Organization.objects.using('readonly').all()
    queryset = queryset.filter(we_vote_id__in=organization_we_vote_id_list)
    queryset = queryset.exclude(organization_twitter_updates_failing=True)
    # Limit this search to non-individuals
    queryset = queryset.exclude(organization_type__in=INDIVIDUAL)

    try:
        organization_count = queryset.count()
    except Exception as e:
        organization_count = 0

    return organization_count


def twitter_identity_retrieve_for_api(twitter_handle, voter_device_id=''):  # twitterIdentityRetrieve
    status = "TWITTER_HANDLE_DOES_NOT_EXIST"  # Default to this
    success = True
    kind_of_owner = "TWITTER_HANDLE_DOES_NOT_EXIST"
    owner_we_vote_id = ''
    owner_id = 0
    google_civic_election_id = 0
    google_civic_election_id_voter_is_watching = 0
    twitter_description = ''
    twitter_followers_count = ''
    twitter_photo_url = ''
    we_vote_hosted_profile_image_url_large = ''
    we_vote_hosted_profile_image_url_medium = ''
    we_vote_hosted_profile_image_url_tiny = ''
    twitter_profile_banner_url_https = ''
    twitter_user_website = ''
    twitter_name = ''

    owner_found = False

    # Check Politician table for Twitter Handle
    # NOTE: It would be better to retrieve from the Politician, and then bring "up" information we need from the
    #  CandidateCampaign table. 2016-05-11 We haven't implemented Politician's yet though.

    # Check Candidate table
    if not positive_value_exists(owner_found):
        # Find out the election the voter is looking at
        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
        if positive_value_exists(results['google_civic_election_id']):
            google_civic_election_id_voter_is_watching = results['google_civic_election_id']
        state_code = ""
        candidate_name = ""

        candidate_list_manager = CandidateListManager()
        google_civic_election_id_list = [google_civic_election_id_voter_is_watching]
        candidate_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=state_code,
            candidate_twitter_handle=twitter_handle,
            candidate_name=candidate_name)
        if candidate_results['candidate_list_found']:
            candidate_list = candidate_results['candidate_list']

            # ...and then find the candidate entry for that election
            most_recent_candidate = candidate_list[0]
            for one_candidate in candidate_list:
                if google_civic_election_id_voter_is_watching == convert_to_int(one_candidate.google_civic_election_id):
                    kind_of_owner = "CANDIDATE"
                    owner_we_vote_id = one_candidate.we_vote_id
                    owner_id = one_candidate.id
                    google_civic_election_id = one_candidate.google_civic_election_id
                    owner_found = True
                    status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-CANDIDATE"
                    # Now that we have candidate, break out of for-loop
                    break
            if not owner_found:
                kind_of_owner = "CANDIDATE"
                owner_we_vote_id = most_recent_candidate.we_vote_id
                owner_id = most_recent_candidate.id
                google_civic_election_id = most_recent_candidate.google_civic_election_id
                owner_found = True
                status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-CANDIDATE"

    if not positive_value_exists(owner_found):
        organization_list_manager = OrganizationListManager()
        organization_results = organization_list_manager.retrieve_organizations_from_twitter_handle(
            twitter_handle=twitter_handle)
        if organization_results['organization_list_found']:
            organization_list = organization_results['organization_list']
            one_organization = organization_list[0]
            kind_of_owner = "ORGANIZATION"
            owner_we_vote_id = one_organization.we_vote_id
            owner_id = one_organization.id
            google_civic_election_id = 0
            owner_found = True
            status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-ORGANIZATION"
            twitter_description = one_organization.twitter_description
            twitter_followers_count = one_organization.twitter_followers_count
            twitter_photo_url = one_organization.twitter_profile_image_url_https
            we_vote_hosted_profile_image_url_large = one_organization.we_vote_hosted_profile_image_url_large
            we_vote_hosted_profile_image_url_medium = one_organization.we_vote_hosted_profile_image_url_medium
            we_vote_hosted_profile_image_url_tiny = one_organization.we_vote_hosted_profile_image_url_tiny
            twitter_profile_banner_url_https = one_organization.twitter_profile_banner_url_https
            twitter_user_website = one_organization.organization_website
            twitter_name = one_organization.twitter_name

    # Reach out to Twitter (or our Twitter account cache) to retrieve some information we can display
    if not positive_value_exists(owner_found):
        twitter_user_manager = TwitterUserManager()
        twitter_user_id = 0
        twitter_results = \
            twitter_user_manager.retrieve_twitter_user_locally_or_remotely(twitter_user_id, twitter_handle)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_description = twitter_user.twitter_description
            twitter_followers_count = twitter_user.twitter_followers_count
            twitter_photo_url = twitter_user.twitter_profile_image_url_https
            we_vote_hosted_profile_image_url_large = twitter_user.we_vote_hosted_profile_image_url_large
            we_vote_hosted_profile_image_url_medium = twitter_user.we_vote_hosted_profile_image_url_medium
            we_vote_hosted_profile_image_url_tiny = twitter_user.we_vote_hosted_profile_image_url_tiny
            twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
            twitter_user_website = twitter_user.twitter_url
            twitter_name = twitter_user.twitter_name
            kind_of_owner = "TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE"
            status = "TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE"

    results = {
        'status':                                   status,
        'success':                                  success,
        'twitter_handle':                           twitter_handle,
        'kind_of_owner':                            kind_of_owner,
        'owner_found':                              owner_found,
        'owner_we_vote_id':                         owner_we_vote_id,
        'owner_id':                                 owner_id,
        'google_civic_election_id':                 google_civic_election_id,
        'twitter_description':                      twitter_description,
        'twitter_followers_count':                  twitter_followers_count,
        'twitter_photo_url':                        twitter_photo_url,
        'we_vote_hosted_profile_image_url_large':   we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny,
        'twitter_profile_banner_url_https':         twitter_profile_banner_url_https,
        'twitter_user_website':                     twitter_user_website,
        'twitter_name':                             twitter_name,
    }
    return results


def delete_possible_twitter_handles(candidate):
    status = ""
    twitter_user_manager = TwitterUserManager()

    if not candidate:
        status += "DELETE_POSSIBLE_TWITTER_HANDLES-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    results = twitter_user_manager.delete_twitter_link_possibilities(candidate.we_vote_id)
    status += results['status']

    results = {
        'success':                  True,
        'status':                   status,
    }

    return results


def refresh_twitter_candidate_details(candidate):
    status = ""
    candidate_manager = CandidateManager()
    politician_manager = PoliticianManager()
    twitter_user_manager = TwitterUserManager()
    we_vote_image_manager = WeVoteImageManager()

    if not candidate:
        status += "TWITTER_CANDIDATE_DETAILS_NOT_RETRIEVED-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if candidate.candidate_twitter_handle:
        status += "TWITTER_CANDIDATE_DETAILS-REACHING_OUT_TO_TWITTER "
        twitter_user_id = 0
        results = retrieve_twitter_user_info(twitter_user_id, candidate.candidate_twitter_handle)

        if results['success']:
            status += "TWITTER_CANDIDATE_DETAILS_RETRIEVED_FROM_TWITTER "

            # Get original image url for cache original size image
            twitter_profile_image_url_https = we_vote_image_manager.twitter_profile_image_url_https_original(
                results['twitter_json']['profile_image_url_https'])
            twitter_profile_background_image_url_https = results['twitter_json']['profile_background_image_url_https'] \
                if 'profile_background_image_url_https' in results['twitter_json'] else None
            twitter_profile_banner_url_https = results['twitter_json']['profile_banner_url'] \
                if 'profile_banner_url' in results['twitter_json'] else None
            cache_results = cache_master_and_resized_image(
                candidate_id=candidate.id,
                candidate_we_vote_id=candidate.we_vote_id,
                twitter_id=candidate.twitter_user_id,
                twitter_screen_name=candidate.candidate_twitter_handle,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                image_source=TWITTER)
            cached_twitter_profile_image_url_https = cache_results['cached_twitter_profile_image_url_https']
            cached_twitter_profile_background_image_url_https = \
                cache_results['cached_twitter_profile_background_image_url_https']
            cached_twitter_profile_banner_url_https = cache_results['cached_twitter_profile_banner_url_https']
            we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
            we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

            save_candidate_results = candidate_manager.update_candidate_twitter_details(
                candidate=candidate,
                twitter_json=results['twitter_json'],
                cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
                cached_twitter_profile_background_image_url_https=cached_twitter_profile_background_image_url_https,
                cached_twitter_profile_banner_url_https=cached_twitter_profile_banner_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
            candidate = save_candidate_results['candidate']
            save_twitter_user_results = twitter_user_manager.update_or_create_twitter_user(
                twitter_json=results['twitter_json'],
                twitter_id=candidate.twitter_user_id,
                cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
                cached_twitter_profile_background_image_url_https=cached_twitter_profile_background_image_url_https,
                cached_twitter_profile_banner_url_https=cached_twitter_profile_banner_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
            # Need to update voter twitter details for the candidate in future
            save_politician_details_results = politician_manager.update_politician_details_from_candidate(
                candidate)
            save_position_from_candidate_results = update_all_position_details_from_candidate(candidate)
        elif results['twitter_user_not_found_in_twitter'] or results['twitter_user_suspended_by_twitter']:
            try:
                candidate.candidate_twitter_updates_failing = True
                candidate.save()
            except Exception as e:
                status += "COULD_NOT_MARK_TWITTER_UPDATES_FAILING: " + str(e) + " "
    else:
        status += "TWITTER_CANDIDATE_DETAILS-CLEARING_DETAILS "
        save_candidate_results = candidate_manager.clear_candidate_twitter_details(candidate)

    results = {
        'success':                  True,
        'status':                   status,
    }
    return results


def process_twitter_images(twitter_image_load_info):
    status = ''
    organization = twitter_image_load_info['organization']
    twitter_user_id = twitter_image_load_info
    twitter_profile_image_url_https = twitter_image_load_info['twitter_profile_image_url_https']
    twitter_profile_background_image_url_https = twitter_image_load_info['twitter_profile_background_image_url_https']
    twitter_profile_banner_url_https = twitter_image_load_info['twitter_profile_banner_url_https']
    twitter_json = twitter_image_load_info['twitter_json']
    cached_twitter_profile_image_url_https = None
    cached_twitter_profile_background_image_url_https = None
    cached_twitter_profile_banner_url_https = None
    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None

    try:
        # Cache original and resized images
        we_vote_image_manager = WeVoteImageManager()
        cache_results = cache_master_and_resized_image(
            organization_id=organization.id,
            organization_we_vote_id=organization.we_vote_id,
            twitter_id=organization.twitter_user_id,
            twitter_screen_name=organization.organization_twitter_handle,
            twitter_profile_image_url_https=twitter_profile_image_url_https,
            twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
            twitter_profile_banner_url_https=twitter_profile_banner_url_https, image_source=TWITTER)
        cached_twitter_profile_image_url_https = cache_results['cached_twitter_profile_image_url_https']
        cached_twitter_profile_background_image_url_https = \
            cache_results['cached_twitter_profile_background_image_url_https']
        cached_twitter_profile_banner_url_https = cache_results['cached_twitter_profile_banner_url_https']
        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

        # If we didn't just generate image urls for tiny, medium or large, we want to retrieve them from the image
        # cache so we can store them in the organization table below in update_organization_twitter_details
        # NOTE: In the future, we may only want to update the organization with these photos if there isn't
        # already a we_vote_hosted_profile_image already stored in the organization.
        # For now, we overwrite with a resized We Vote image if we have one
        if not positive_value_exists(we_vote_hosted_profile_image_url_tiny) or \
                not positive_value_exists(we_vote_hosted_profile_image_url_medium) or \
                not positive_value_exists(we_vote_hosted_profile_image_url_large):
            # ANISHA Consider adding an option to only retrieve active images from
            # the function retrieve_we_vote_image_list_from_we_vote_id (That is, if a "retrieve_active_only"
            # setting is passed into the function, then don't return images that are active=False)
            voter_we_vote_id = None
            candidate_we_vote_id = None
            image_results = we_vote_image_manager.retrieve_we_vote_image_list_from_we_vote_id(
                voter_we_vote_id, candidate_we_vote_id, organization.we_vote_id)
            if image_results['we_vote_image_list_found']:
                we_vote_image_list = image_results['we_vote_image_list']
                for one_image in we_vote_image_list:
                    # For now we aren't checking to see if the image is marked active or not
                    # ANISHA The we_vote_image_url is always coming back empty
                    if not positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                        if one_image.kind_of_image_tiny:
                            we_vote_hosted_profile_image_url_tiny = one_image.we_vote_image_url
                    if not positive_value_exists(we_vote_hosted_profile_image_url_medium):
                        if one_image.kind_of_image_medium:
                            we_vote_hosted_profile_image_url_tiny = one_image.we_vote_image_url
                    if not positive_value_exists(we_vote_hosted_profile_image_url_large):
                        if one_image.kind_of_image_large:
                            we_vote_hosted_profile_image_url_large = one_image.we_vote_image_url
    except Exception as e:
        status += "ERROR_CACHING_TWITTER_IMAGES: " + str(e) + " "

    try:
        organization_manager = OrganizationManager()
        save_organization_results = organization_manager.update_organization_twitter_details(
            organization,
            twitter_json,
            cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
            cached_twitter_profile_background_image_url_https=cached_twitter_profile_background_image_url_https,
            cached_twitter_profile_banner_url_https=cached_twitter_profile_banner_url_https,
            we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
            we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        if save_organization_results['success']:
            # status += "ORGANIZATION_TWITTER_DETAILS_SUCCESS "

            # Now update the Twitter statistics information in other We Vote tables
            organization = save_organization_results['organization']
            save_voter_guide_from_organization_results = update_social_media_statistics_in_other_tables(
                organization)

            # Make sure we have a TwitterUser
            twitter_user_manager = TwitterUserManager()
            save_twitter_user_results = twitter_user_manager.update_or_create_twitter_user(
                twitter_json=twitter_json,
                twitter_id=organization.twitter_user_id,
                cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
                cached_twitter_profile_background_image_url_https=cached_twitter_profile_background_image_url_https,
                cached_twitter_profile_banner_url_https=cached_twitter_profile_banner_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)

            # If there is a voter with this Twitter id, then update the voter information in other tables
            voter_manager = VoterManager()
            save_voter_twitter_details_results = voter_manager.update_voter_twitter_details(
                twitter_id=organization.twitter_user_id,
                twitter_json=twitter_json,
                cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
            if save_voter_twitter_details_results['success']:
                save_position_from_voter_results = update_position_for_friends_details_from_voter(
                    save_voter_twitter_details_results['voter'])
            update_positions_results = update_position_entered_details_from_organization(organization)
            from voter_guide.models import VoterGuideManager
            voter_guide_manager = VoterGuideManager()
            voter_guide_results = \
                voter_guide_manager.update_organization_voter_guides_with_organization_data(organization)
        else:
            status += "ORGANIZATION_TWITTER_DETAILS_RETRIEVED_FROM_TWITTER_BUT_NOT_SAVED "
    except Exception as e:
        status += "UPDATE_TWITTER_ORGANIZATION_DETAILS_FAILED: " + str(e) + " "
        print(status)

    results = {
        'success':              True,
        'status':               status,
        'organization':         organization,
        'twitter_user_id':      twitter_user_id,
    }
    return results


def refresh_twitter_organization_details(organization, twitter_user_id=0):
    """
    This function assumes TwitterLinkToOrganization is happening outside of this function. It relies on our caching
    organization_twitter_handle in the organization object.
    :param organization:
    :param twitter_user_id:
    :return:
    """
    organization_manager = OrganizationManager()
    we_vote_image_manager = WeVoteImageManager()
    status = ""
    organization_twitter_handle = ""
    twitter_image_load_info = {}

    if not organization:
        status += "ORGANIZATION_TWITTER_DETAILS_NOT_RETRIEVED-ORG_MISSING "
        results = {
            'success':              False,
            'status':               status,
            'organization':         organization,
            'twitter_user_found':   False,
            'twitter_user_id':      twitter_user_id,
            'twitter_handle':       organization_twitter_handle,
        }
        return results

    twitter_user_found = False
    twitter_json = {}
    if positive_value_exists(twitter_user_id):
        try:
            status += "REACHING_OUT_TO_TWITTER_BY_USER_ID "
            results = retrieve_twitter_user_info(twitter_user_id)
            if results['success']:
                twitter_json = results['twitter_json']
                twitter_user_found = True
                twitter_user_id = results['twitter_user_id']
            elif results['twitter_user_not_found_in_twitter'] or results['twitter_user_suspended_by_twitter']:
                try:
                    organization.organization_twitter_updates_failing = True
                    organization.save()
                except Exception as e:
                    status += "COULD_NOT_MARK_ORGANIZATION_TWITTER_UPDATES_FAILING1: " + str(e) + " "
        except Exception as e:
            status += "RETRIEVE_TWITTER_USER_INFO_BY_USER_ID_FAILS: " + str(e) + " "

    if not twitter_user_found and positive_value_exists(organization.organization_twitter_handle):
        # status += "REACHING_OUT_TO_TWITTER-BY_HANDLE "
        # organization_twitter_handle = organization.organization_twitter_handle
        twitter_user_id_zero = 0
        try:
            results = retrieve_twitter_user_info(twitter_user_id_zero, organization.organization_twitter_handle)
            status += results['status']
            if results['success']:
                twitter_json = results['twitter_json']
                twitter_user_found = True
                twitter_user_id = results['twitter_user_id']
            elif results['twitter_user_not_found_in_twitter'] or results['twitter_user_suspended_by_twitter']:
                try:
                    organization.organization_twitter_updates_failing = True
                    organization.save()
                except Exception as e:
                    status += "COULD_NOT_MARK_ORGANIZATION_TWITTER_UPDATES_FAILING2: " + str(e) + " "
        except Exception as e:
            status += "RETRIEVE_TWITTER_USER_INFO_BY_HANDLE_FAILS: " + str(e) + " "

    if twitter_user_found:
        status += str(organization.organization_twitter_handle) + "-RETRIEVED_FROM_TWITTER "

        # Get original image url for cache original size image
        profile_image_url_https = twitter_json['profile_image_url_https'] \
            if 'profile_image_url_https' in twitter_json else None
        twitter_profile_image_url_https = we_vote_image_manager.twitter_profile_image_url_https_original(
            profile_image_url_https)
        twitter_profile_background_image_url_https = twitter_json['profile_background_image_url_https'] \
            if 'profile_background_image_url_https' in twitter_json else None
        twitter_profile_banner_url_https = twitter_json['profile_banner_url'] \
            if 'profile_banner_url' in twitter_json else None

        # Test hack
        twitter_image_load_info = {
            'organization': organization,
            'twitter_user_id': organization.twitter_user_id,
            'twitter_profile_image_url_https': twitter_profile_image_url_https,
            'twitter_profile_background_image_url_https': twitter_profile_background_image_url_https,
            'twitter_profile_banner_url_https': twitter_profile_banner_url_https,
            'twitter_json': twitter_json,
        }
        try:
            results = process_twitter_images(twitter_image_load_info)
            status += results['status']
        except Exception as e:
            status += "FAILURE_WITHIN_PROCESS_TWITTER_IMAGES: " + str(e) + " "
            print(status)
    else:
        status += str(organization.organization_twitter_handle) + "-NOT_RETRIEVED_CLEARING_TWITTER_DETAILS "
        save_organization_results = organization_manager.clear_organization_twitter_details(organization)

        if save_organization_results['success']:
            results = update_social_media_statistics_in_other_tables(organization)
        else:
            status += "ORGANIZATION_TWITTER_DETAILS_NOT_CLEARED_FROM_DB "

    results = {
        'success':              True,
        'status':               status,
        'organization':         organization,
        'twitter_user_found':   twitter_user_found,
        'twitter_user_id':      twitter_user_id,
        'twitter_handle':       organization_twitter_handle,
        'twitter_image_load_info':  twitter_image_load_info,
    }
    return results


def retrieve_possible_twitter_handles(candidate):
    status = ""
    success = True
    twitter_user_manager = TwitterUserManager()
    remote_request_history_manager = RemoteRequestHistoryManager()

    if not candidate:
        status = "RETRIEVE_POSSIBLE_TWITTER_HANDLES-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if positive_value_exists(candidate.contest_office_we_vote_id) and not \
            positive_value_exists(candidate.contest_office_name):
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
            candidate.contest_office_we_vote_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            try:
                candidate.contest_office_name = contest_office.office_name
                candidate.save()
            except Exception as e:
                status += "FAILED_TO_SAVE_CANDIDATE_CAMPAIGN: " + str(e) + " "

    name_handling_regex = r"[^ \w'-]"
    candidate_name = {
        'title': sub(name_handling_regex, "", candidate.extract_title()),
        'first_name': sub(name_handling_regex, "", candidate.extract_first_name()),
        'middle_name': sub(name_handling_regex, "", candidate.extract_middle_name()),
        'last_name': sub(name_handling_regex, "", candidate.extract_last_name()),
        'suffix': sub(name_handling_regex, "", candidate.extract_suffix()),
        'nickname': sub(name_handling_regex, "", candidate.extract_nickname()),
    }

    # December 2021: Using the Twitter 1.1 API for search_users, since it is not yet available in 2.0
    # https://developer.twitter.com/en/docs/twitter-api/migrate/twitter-api-endpoint-map
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, timeout=20)
    # results = {'possible_twitter_handles_list': []}
    possible_twitter_handles_list = []

    # ##############
    # Search 1
    search_term = candidate.candidate_name
    try:
        search_results = api.search_users(q=search_term, page=1)

        search_results.sort(key=lambda possible_candidate: possible_candidate.followers_count, reverse=True)
        search_results_length = len(search_results)
        search_results_found = len(search_results) > 0

        if search_results_found:
            analyze_twitter_search_results(
                search_results=search_results,
                candidate_name=candidate_name,
                candidate=candidate,
                possible_twitter_handles_list=possible_twitter_handles_list)
    except Exception as e:
        status += "ERROR_RETURNED_FROM_TWITTER_SEARCH1: " + str(e) + " "

    # ##############
    # Search 2
    # Also include search results omitting any single-letter initials and periods in name.
    # Example: "A." is ignored while "A.J." becomes "AJ"
    modified_search_term = ""
    modified_search_term_base = ""
    if len(candidate_name['first_name']) > 1:
        modified_search_term += candidate_name['first_name'] + " "
    if len(candidate_name['middle_name']) > 1:
        modified_search_term_base += candidate_name['middle_name'] + " "
    if len(candidate_name['last_name']) > 1:
        modified_search_term_base += candidate_name['last_name']
    if len(candidate_name['suffix']):
        modified_search_term_base += " " + candidate_name['suffix']
    modified_search_term += modified_search_term_base
    if search_term != modified_search_term:
        try:
            modified_search_results = api.search_users(q=modified_search_term, page=1)
            modified_search_results.sort(key=lambda possible_candidate: possible_candidate.followers_count, reverse=True)
            modified_search_results_found = len(modified_search_results) > 0
            if modified_search_results_found:
                analyze_twitter_search_results(
                    search_results=modified_search_results,
                    candidate_name=candidate_name,
                    candidate=candidate,
                    possible_twitter_handles_list=possible_twitter_handles_list)
        except Exception as e:
            status += "ERROR_RETURNED_FROM_TWITTER_SEARCH2: " + str(e) + " "

    # ##############
    # Search 3
    # If nickname exists, try searching with nickname instead of first name
    if len(candidate_name['nickname']):
        modified_search_term_2 = candidate_name['nickname'] + " " + modified_search_term_base

        try:
            modified_search_results_2 = api.search_users(q=modified_search_term_2, page=1)
            modified_search_results_2.sort(key=lambda possible_candidate: possible_candidate.followers_count, reverse=True)
            modified_search_results_2_found = len(modified_search_results_2) > 0
            if modified_search_results_2_found:
                analyze_twitter_search_results(
                    search_results=modified_search_results_2,
                    candidate_name=candidate_name,
                    candidate=candidate,
                    possible_twitter_handles_list=possible_twitter_handles_list)
        except Exception as e:
            status += "ERROR_RETURNED_FROM_TWITTER_SEARCH3: " + str(e) + " "

    twitter_handles_found = len(possible_twitter_handles_list) > 0
    status += "NUMBER_POSSIBLE_TWITTER_HANDLES_FOUND: " + str(len(possible_twitter_handles_list)) + " "

    if twitter_handles_found:
        for possibility_result in possible_twitter_handles_list:
            save_twitter_user_results = \
                twitter_user_manager.update_or_create_twitter_link_possibility_from_twitter_json(
                    candidate.we_vote_id, possibility_result['twitter_json'],
                    possibility_result['search_term'], possibility_result['likelihood_score'])
            if save_twitter_user_results['multiple_objects_returned']:
                twitter_json = possibility_result['twitter_json']
                twitter_user_manager.delete_twitter_link_possibility(candidate.we_vote_id, twitter_json['id'])
                # Now try again
                save_twitter_user_results = \
                    twitter_user_manager.update_or_create_twitter_link_possibility_from_twitter_json(
                        candidate.we_vote_id, possibility_result['twitter_json'],
                        possibility_result['search_term'], possibility_result['likelihood_score'])
            if not save_twitter_user_results['success']:
                status += save_twitter_user_results['status']
                success = False

    # Create a record denoting that we have retrieved from Twitter for this candidate
    save_results_history = remote_request_history_manager.create_remote_request_history_entry(
        RETRIEVE_POSSIBLE_TWITTER_HANDLES, candidate.google_civic_election_id,
        candidate.we_vote_id, None, len(possible_twitter_handles_list), status)
    if not save_results_history['success']:
        status += save_results_history['status']
        success = False

    results = {
        'success':                  success,
        'status':                   status,
        'num_of_possibilities':     str(len(possible_twitter_handles_list)),
    }

    return results


def retrieve_and_update_candidates_needing_twitter_update(
        google_civic_election_id=0,
        state_code='',
        limit=0):
    candidate_we_vote_id_list_to_exclude = []
    status = ""
    success = True

    election_manager = ElectionManager()
    candidate_list_manager = CandidateListManager()
    # Run Twitter account search and analysis on candidates without a linked or possible Twitter account
    candidate_queryset = CandidateCampaign.objects.all()  # Cannot be readonly
    google_civic_election_id_list = []
    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list.append(google_civic_election_id)
    else:
        # Limit this search to upcoming_elections only
        results = election_manager.retrieve_upcoming_google_civic_election_id_list()
        if not positive_value_exists(results['success']):
            status += results['status']
        google_civic_election_id_list = results['upcoming_google_civic_election_id_list']
    # google_civic_election_id_list = [1000130]  # Temp for testing
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list)
    if not positive_value_exists(results['success']):
        status += results['status']
        success = False
    upcoming_candidate_we_vote_id_list_to_include = results['candidate_we_vote_id_list']

    if len(upcoming_candidate_we_vote_id_list_to_include):
        try:
            # Exclude candidates we have requested updates from in the last month
            remote_request_query = RemoteRequestHistory.objects.all()
            one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
            one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
            remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
            remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_UPDATE_DATA_FROM_TWITTER)
            remote_request_query = remote_request_query.exclude(
                Q(candidate_campaign_we_vote_id__isnull=True) | Q(candidate_campaign_we_vote_id=""))
            remote_request_query = \
                remote_request_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
            candidate_we_vote_id_list_to_exclude = list(remote_request_query)
        except Exception as e:
            status += "PROBLEM_RETRIEVING_REMOTE_REQUEST_HISTORY_RETRIEVE_UPDATE_DATA_FROM_TWITTER: " + str(e) + " "
            success = False

    candidates_to_update = 0
    candidates_updated = 0
    if not success or len(upcoming_candidate_we_vote_id_list_to_include) == 0:
        results = {
            'success':              success,
            'status':               status,
            'candidates_to_update': candidates_to_update,
            'candidates_updated':   candidates_updated,
        }
        return results

    candidate_we_vote_id_list = \
        list(set(upcoming_candidate_we_vote_id_list_to_include) - set(candidate_we_vote_id_list_to_exclude))

    try:
        candidate_queryset = candidate_queryset.filter(we_vote_id__in=candidate_we_vote_id_list)
        candidate_queryset = candidate_queryset.exclude(
            Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))
        candidate_queryset = candidate_queryset.exclude(candidate_twitter_updates_failing=True)
        if positive_value_exists(state_code):
            candidate_queryset = candidate_queryset.filter(state_code__iexact=state_code)
        candidates_to_update = candidate_queryset.count()
    except Exception as e:
        status += "CANDIDATE_RETRIEVE_FAILED: " + str(e) + " "
        success = False

    if positive_value_exists(success):
        # Limit so we don't overwhelm Twitter's rate limiting
        # https://developer.twitter.com/en/docs/basics/rate-limits
        # GET users/search is limited to 900 per 15 minutes
        # Since we run one batch per minute, that means that 900 / 15 = 60
        # We have other processes which might reach out to Twitter, so we limit the number of
        # candidates we analyze to 20 per minute
        if positive_value_exists(limit):
            number_of_candidates_limit = limit
        else:
            number_of_candidates_limit = 20
        candidate_list = candidate_queryset[:number_of_candidates_limit]

        candidates_updated = 0
        status += "RETRIEVE_UPDATE_DATA_FROM_TWITTER_LOOP-TOTAL: " + str(candidates_to_update) + " "
        remote_request_history_manager = RemoteRequestHistoryManager()
        for candidate in candidate_list:
            results = refresh_twitter_candidate_details(candidate)
            status += results['status']
            if results['success']:
                candidates_updated += 1
                refresh_candidate_results = refresh_candidate_data_from_master_tables(candidate.we_vote_id)

            # Create a record denoting that we have retrieved from Twitter for this candidate
            save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                kind_of_action=RETRIEVE_UPDATE_DATA_FROM_TWITTER,
                candidate_campaign_we_vote_id=candidate.we_vote_id)
            if not save_results_history['success']:
                status += save_results_history['status']
                success = False

    results = {
        'success':              success,
        'status':               status,
        'candidates_to_update': candidates_to_update,
        'candidates_updated':   candidates_updated,
    }
    return results


def retrieve_and_update_organizations_needing_twitter_update(batch_process_id=0):
    organization_we_vote_id_list_to_exclude = []
    organizations_not_updated = 0
    status = ''
    success = True

    # Limit to organizations with a TwitterLinkToOrganization entry
    twitter_user_manager = TwitterUserManager()
    results = twitter_user_manager.retrieve_twitter_link_to_organization_list(
        return_we_vote_id_list_only=True, read_only=True)
    organization_we_vote_id_list_to_include = results['organization_we_vote_id_list']

    if len(organization_we_vote_id_list_to_include):
        try:
            # Exclude organizations searched for in the last month
            remote_request_query = RemoteRequestHistory.objects.using('readonly').all()
            one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
            one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
            remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
            remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_UPDATE_DATA_FROM_TWITTER)
            remote_request_query = remote_request_query.exclude(
                Q(organization_we_vote_id__isnull=True) | Q(organization_we_vote_id=""))
            remote_request_query = remote_request_query.values_list('organization_we_vote_id', flat=True).distinct()
            organization_we_vote_id_list_to_exclude = list(remote_request_query)
        except Exception as e:
            status += "FAILED_RETRIEVING_ORGANIZATIONS_FROM_REMOTE_REQUEST_HISTORY: " + str(e) + " "
            success = False

    organizations_to_update = 0
    organizations_updated = 0
    if not success or len(organization_we_vote_id_list_to_include) == 0:
        results = {
            'success':                      success,
            'status':                       status,
            'organizations_to_update':      organizations_to_update,
            'organizations_updated':        organizations_updated,
            'organizations_not_updated':    organizations_not_updated,
        }
        return results

    organization_we_vote_id_list = \
        list(set(organization_we_vote_id_list_to_include) - set(organization_we_vote_id_list_to_exclude))

    try:
        organization_queryset = Organization.objects.all()
        organization_queryset = organization_queryset.filter(we_vote_id__in=organization_we_vote_id_list)
        organization_queryset = organization_queryset.exclude(organization_twitter_updates_failing=True)
        # Limit this search to non-individuals
        organization_queryset = organization_queryset.exclude(organization_type__in=INDIVIDUAL)
        organizations_to_update = organization_queryset.count()
    except Exception as e:
        status += "ORGANIZATION_RETRIEVE_FAILED: " + str(e) + " "
        success = False

    if positive_value_exists(success):
        # Limit so we don't overwhelm Twitter's rate limiting
        # https://developer.twitter.com/en/docs/basics/rate-limits
        # GET users/search is limited to 900 per 15 minutes
        # Since we run one batch per minute, that means that 900 / 15 = 60
        # We have other processes which might reach out to Twitter, so we limit the number of
        # candidates we analyze to 20 per minute
        number_of_organizations_limit = 20
        organization_list = organization_queryset[:number_of_organizations_limit]

        organizations_updated = 0
        status += "RETRIEVE_ORGANIZATION_UPDATE_DATA_FROM_TWITTER_LOOP_TOTAL: " + str(organizations_to_update) + " "
        for organization in organization_list:
            status += "[" + str(organization.organization_twitter_handle) + "]"

        batch_process_manager = BatchProcessManager()
        batch_process_manager.create_batch_process_log_entry(
            batch_process_id=batch_process_id,
            kind_of_process=UPDATE_TWITTER_DATA_FROM_TWITTER,
            status=status,
        )
        remote_request_history_manager = RemoteRequestHistoryManager()
        for organization in organization_list:
            try:
                results = refresh_twitter_organization_details(organization)
                status += results['status']
                if results['twitter_user_found']:
                    organizations_updated += 1
                else:
                    organizations_not_updated += 1
            except Exception as e:
                status += "REFRESH_TWITTER_ORGANIZATION_DETAILS_FAILED: " + str(e) + " "
                organizations_not_updated += 1

            batch_process_manager.create_batch_process_log_entry(
                batch_process_id=batch_process_id,
                kind_of_process=UPDATE_TWITTER_DATA_FROM_TWITTER,
                status=status,
            )

            # Create a record denoting that we have retrieved from Twitter for this candidate
            save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                kind_of_action=RETRIEVE_UPDATE_DATA_FROM_TWITTER,
                organization_we_vote_id=organization.we_vote_id)
            if not save_results_history['success']:
                status += save_results_history['status']
                success = False

    results = {
        'success':                  success,
        'status':                   status,
        'organizations_to_update':  organizations_to_update,
        'organizations_updated':    organizations_updated,
        'organizations_not_updated': organizations_not_updated,
    }

    return results


def retrieve_possible_twitter_handles_in_bulk(
        google_civic_election_id=0,
        state_code='',
        limit=0):
    status = ""
    success = True

    election_manager = ElectionManager()
    candidate_list_manager = CandidateListManager()
    # Run Twitter account search and analysis on candidates without a linked or possible Twitter account
    candidate_queryset = CandidateCampaign.objects.all()  # Cannot be readonly
    google_civic_election_id_list = []
    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list.append(google_civic_election_id)
    else:
        # Limit this search to upcoming_elections only
        results = election_manager.retrieve_upcoming_google_civic_election_id_list()
        if not positive_value_exists(results['success']):
            status += results['status']
        google_civic_election_id_list = results['upcoming_google_civic_election_id_list']
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list)
    if not positive_value_exists(results['success']):
        status += results['status']
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    candidate_queryset = candidate_queryset.filter(we_vote_id__in=candidate_we_vote_id_list)
    candidate_queryset = candidate_queryset.filter(
        Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle=""))
    if positive_value_exists(state_code):
        candidate_queryset = candidate_queryset.filter(state_code__iexact=state_code)

    # Exclude candidates we have already have TwitterLinkPossibility data for
    try:
        twitter_possibility_list = TwitterLinkPossibility.objects. \
            values_list('candidate_campaign_we_vote_id', flat=True).distinct()
        if len(twitter_possibility_list):
            candidate_queryset = candidate_queryset.exclude(we_vote_id__in=twitter_possibility_list)
    except Exception as e:
        status += "PROBLEM_RETRIEVING_TWITTER_LINK_POSSIBILITY " + str(e) + " "
    # Exclude candidates we have requested information for in the last month
    try:
        # Exclude candidates searched for in the last month
        remote_request_query = RemoteRequestHistory.objects.all()
        one_month_of_seconds = 60 * 60 * 24 * 30  # 60 seconds, 60 minutes, 24 hours, 30 days
        one_month_ago = now() - timedelta(seconds=one_month_of_seconds)
        remote_request_query = remote_request_query.filter(datetime_of_action__gt=one_month_ago)
        remote_request_query = remote_request_query.filter(kind_of_action__iexact=RETRIEVE_POSSIBLE_TWITTER_HANDLES)
        remote_request_list = remote_request_query.values_list('candidate_campaign_we_vote_id', flat=True).distinct()
        if len(remote_request_list):
            candidate_queryset = candidate_queryset.exclude(we_vote_id__in=remote_request_list)
    except Exception as e:
        status += "PROBLEM_RETRIEVING_TWITTER_LINK_POSSIBILITY " + str(e) + " "
        success = False

    candidates_to_analyze = 0
    candidates_analyzed = 0
    if positive_value_exists(success):
        # Limit so we don't overwhelm Twitter's rate limiting
        # https://developer.twitter.com/en/docs/basics/rate-limits
        # GET users/search is limited to 900 per 15 minutes
        # Since we run one batch per minute, that means that 900 / 15 = 60
        # retrieve_possible_twitter_handles *might* search as many as 3 times per candidate, so we limit the number of
        # candidates we analyze to 20 per minute
        if positive_value_exists(limit):
            number_of_candidates_limit = limit
        else:
            number_of_candidates_limit = 20
        candidates_to_analyze = candidate_queryset.count()
        candidate_list = candidate_queryset[:number_of_candidates_limit]

        candidates_analyzed = 0
        status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES_LOOP-TOTAL: " + str(candidates_to_analyze) + " "
        for one_candidate in candidate_list:
            # Twitter account search and analysis has not been run on this candidate yet
            results = retrieve_possible_twitter_handles(one_candidate)
            if results['success']:
                candidates_analyzed += 1
            status += results['status']

    results = {
        'success':                  success,
        'status':                   status,
        'candidates_to_analyze':    candidates_to_analyze,
        'candidates_analyzed':      candidates_analyzed,
    }

    return results


def scrape_social_media_from_one_site(site_url, retrieve_list=False):
    twitter_handle = ''
    twitter_handle_found = False
    twitter_handle_list = []
    facebook_page = ''
    facebook_page_found = False
    facebook_page_list = []
    success = False
    status = ""
    if len(site_url) < 10:
        status = 'PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':               status,
            'success':              success,
            'twitter_handle':       twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'facebook_page':        facebook_page,
            'facebook_page_found':  facebook_page_found,
        }
        return results

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Encoding': 'none',
    # 'Accept-Language': 'en-US,en;q=0.8',
    # 'Connection': 'keep-alive'
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',

    # ##########
    # Twitter
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        for line in page.readlines():
            try:
                decoded_line = line.decode()
                proceed = positive_value_exists(retrieve_list) or not twitter_handle_found
                if proceed:
                    for m in re.finditer(RE_TWITTER, decoded_line):
                        if m:
                            name = m.group(1)
                            if name not in TWITTER_BLACKLIST:
                                twitter_handle = name
                                twitter_handle_found = True
                                if twitter_handle not in twitter_handle_list:
                                    twitter_handle_list.append(twitter_handle)
                                if not positive_value_exists(retrieve_list):
                                    raise GetOutOfLoopLocal
                proceed = positive_value_exists(retrieve_list) or not twitter_handle_found
                if proceed:
                    for m in re.finditer(RE_TWITTER_WWW, decoded_line):
                        if m:
                            name = m.group(1)
                            if name not in TWITTER_BLACKLIST:
                                twitter_handle = name
                                twitter_handle_found = True
                                if twitter_handle not in twitter_handle_list:
                                    twitter_handle_list.append(twitter_handle)
                                if not positive_value_exists(retrieve_list):
                                    raise GetOutOfLoopLocal
            except GetOutOfLoopLocal:
                pass
            if twitter_handle_found and not positive_value_exists(retrieve_list):  # and facebook_page_found:
                raise GetOutOfLoop
        success = True
        status += 'FINISHED_SCRAPING_PAGE-TWITTER '
    except timeout:
        status += "SCRAPE_TIMEOUT_ERROR-TWITTER "
        success = False
    except GetOutOfLoop:
        success = True
        status += 'TWITTER_HANDLE_FOUND-BREAK_OUT-TWITTER '
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "SCRAPE_SOCIAL_IO_ERROR-TWITTER: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "SCRAPE_GENERAL_EXCEPTION_ERROR-TWITTER: {error_message}".format(error_message=error_message)
        success = False

    # #########
    # Facebook
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        for line in page.readlines():
            try:
                decoded_line = line.decode()
                # decoded_line = '<div class="fb-page" data-href="https://www.facebook.com/ImmigrantAction/" data-small-header="true" data-adapt-container-width="true" data-hide-cover="false" data-show-facepile="true" data-show-posts="false"><div class="fb-xfbml-parse-ignore"><blockquote cite="https://www.facebook.com/ImmigrantAction/"><a href="https://www.facebook.com/ImmigrantAction/">ImmigrantAction</a></blockquote></div></div>'
                proceed = positive_value_exists(retrieve_list) or not facebook_page_found
                if proceed:
                    for m2 in re.finditer(RE_FACEBOOK, decoded_line):
                        if m2:
                            possible_page1 = m2.group(0)
                            if possible_page1 not in FACEBOOK_BLACKLIST:
                                facebook_page = possible_page1
                                if facebook_page not in facebook_page_list:
                                    facebook_page_list.append(facebook_page)
                                facebook_page_found = True
                                if not positive_value_exists(retrieve_list):
                                    raise GetOutOfLoopLocal
                            try:
                                possible_page2 = m2.group(2)
                                if possible_page2 not in FACEBOOK_BLACKLIST:
                                    facebook_page = possible_page2
                                    if facebook_page not in facebook_page_list:
                                        facebook_page_list.append(facebook_page)
                                    facebook_page_found = True
                                    if not positive_value_exists(retrieve_list):
                                        raise GetOutOfLoopLocal
                            except Exception as error_instance:
                                pass
                            # possible_page3 = m2.group(3)
                            # possible_page4 = m2.group(4)
            except GetOutOfLoopLocal:
                pass
            if facebook_page_found and not positive_value_exists(retrieve_list):
                raise GetOutOfLoop
        success = True
        status += 'FINISHED_SCRAPING_PAGE-FACEBOOK '
    except timeout:
        success = False
        status += "SCRAPE_TIMEOUT_ERROR-TWITTER "
    except GetOutOfLoop:
        success = True
        status += 'FACEBOOK_PAGE_FOUND-BREAK_OUT '
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        success = False
        error_message = error_instance
        status += "SCRAPE_SOCIAL_IO_ERROR-FACEBOOK: {error_message}".format(error_message=error_message)
    except Exception as error_instance:
        success = False
        error_message = error_instance
        status += "SCRAPE_GENERAL_EXCEPTION_ERROR-FACEBOOK: {error_message}".format(error_message=error_message)

    results = {
        'status':               status,
        'success':              success,
        'page_redirected':      twitter_handle,
        'twitter_handle':       twitter_handle,
        'twitter_handle_list':  twitter_handle_list,
        'twitter_handle_found': twitter_handle_found,
        'facebook_page':        facebook_page,
        'facebook_page_found':  facebook_page_found,
        'facebook_page_list':   facebook_page_list,
    }
    return results


def scrape_and_save_social_media_from_all_organizations(state_code='', force_retrieve=False):
    facebook_pages_found = 0
    twitter_handles_found = 0

    organization_manager = OrganizationManager()
    organization_list_query = Organization.objects.order_by('organization_name')
    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code=state_code)

    organization_list = organization_list_query
    for organization in organization_list:
        twitter_handle = False
        facebook_page = False
        if not organization.organization_website:
            continue
        if (not positive_value_exists(organization.organization_twitter_handle)) or force_retrieve:
            scrape_results = scrape_social_media_from_one_site(organization.organization_website)

            # Only include a change if we have a new value (do not try to save blank value)
            if scrape_results['twitter_handle_found'] and positive_value_exists(scrape_results['twitter_handle']):
                twitter_handle = scrape_results['twitter_handle']
                twitter_handles_found += 1

            if scrape_results['facebook_page_found'] and positive_value_exists(scrape_results['facebook_page']):
                facebook_page = scrape_results['facebook_page']
                facebook_pages_found += 1

            save_results = organization_manager.update_organization_social_media(organization, twitter_handle,
                                                                                 facebook_page)

        # ######################################
        # We refresh the Twitter information in another function

    status = "ORGANIZATION_SOCIAL_MEDIA_SCRAPED"
    results = {
        'success':                  True,
        'status':                   status,
        'twitter_handles_found':    twitter_handles_found,
        'facebook_pages_found':     facebook_pages_found,
    }
    return results


def refresh_twitter_data_for_organizations(state_code='', google_civic_election_id=0, first_retrieve_only=False):
    status = ""
    number_of_twitter_accounts_queried = 0
    number_of_organizations_updated = 0

    organization_list_query = Organization.objects.order_by('organization_name')
    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code=state_code)

    # Limit this to organizations that have a voter guide in a particular election
    if positive_value_exists(google_civic_election_id):
        voter_guide_list_manager = VoterGuideListManager()
        google_civic_election_id_list = [google_civic_election_id]
        results = voter_guide_list_manager.retrieve_voter_guides_for_election(google_civic_election_id_list)
        if results['voter_guide_list_found']:
            organization_we_vote_ids_in_this_election = []
            voter_guide_list = results['voter_guide_list']
            for one_voter_guide in voter_guide_list:
                if positive_value_exists(one_voter_guide.organization_we_vote_id):
                    organization_we_vote_ids_in_this_election.append(one_voter_guide.organization_we_vote_id)
            # Only return the organizations with a voter guide for this election
            organization_list_query = organization_list_query.filter(
                we_vote_id__in=organization_we_vote_ids_in_this_election)
        else:
            status += "NO_VOTER_GUIDES_FOUND_FOR_THIS_ELECTION "
            results = {
                'success': False,
                'status': status,
                'number_of_twitter_accounts_queried': number_of_twitter_accounts_queried,
                'number_of_organizations_updated': number_of_organizations_updated,
            }
            return results

    organization_list = list(organization_list_query)

    twitter_user_manager = TwitterUserManager()
    for organization in organization_list:
        # ######################################
        # Do we have a TwitterLinkToOrganization for this org?
        twitter_user_id_found = False
        twitter_id = 0
        results = twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization.we_vote_id)
        if results['twitter_link_to_organization_found']:
            twitter_link_to_organization = results['twitter_link_to_organization']
            twitter_id = twitter_link_to_organization.twitter_id
            twitter_user_id_found = True

        # If we can find a twitter_id from the TwitterLinkToOrganization table, we want to use that
        if twitter_user_id_found or organization.organization_twitter_handle:
            retrieved_twitter_data = False
            if positive_value_exists(first_retrieve_only):
                if not positive_value_exists(organization.twitter_followers_count):
                    refresh_results = refresh_twitter_organization_details(organization, twitter_id)
                    # twitter_user_id = 0
                    # results = retrieve_twitter_user_info(twitter_user_id, organization.organization_twitter_handle)
                    retrieved_twitter_data = refresh_results['success']
                    organization = refresh_results['organization']
                    number_of_twitter_accounts_queried += 1
            else:
                refresh_results = refresh_twitter_organization_details(organization, twitter_id)
                # twitter_user_id = 0
                # results = retrieve_twitter_user_info(twitter_user_id, organization.organization_twitter_handle)
                retrieved_twitter_data = refresh_results['success']
                organization = refresh_results['organization']
                number_of_twitter_accounts_queried += 1

            if retrieved_twitter_data:
                number_of_organizations_updated += 1
                # save_results = organization_manager.update_organization_twitter_details(
                #     organization, twitter_json)

                # if save_results['success']:
                update_results = update_social_media_statistics_in_other_tables(organization)

    status = "ALL_ORGANIZATION_TWITTER_DATA_RETRIEVED"
    results = {
        'success':                              True,
        'status':                               status,
        'number_of_twitter_accounts_queried':   number_of_twitter_accounts_queried,
        'number_of_organizations_updated':      number_of_organizations_updated,
    }
    return results


def scrape_and_save_social_media_for_candidates_in_one_election(google_civic_election_id=0, state_code=''):
    facebook_pages_found = 0
    twitter_handles_found = 0
    force_retrieve = False
    status = ""
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    return_list_of_objects = True
    google_civic_election_id_list = [google_civic_election_id]
    results = candidate_list_manager.retrieve_all_candidates_for_upcoming_election(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=state_code,
        return_list_of_objects=return_list_of_objects)
    status += results['status']
    if results['success']:
        candidate_list = results['candidate_list_objects']
    else:
        candidate_list = []

    for candidate in candidate_list:
        twitter_handle = False
        facebook_page = False
        if not candidate.candidate_url:
            continue
        if (not positive_value_exists(candidate.candidate_twitter_handle)) or force_retrieve:
            scrape_results = scrape_social_media_from_one_site(candidate.candidate_url)

            # Only include a change if we have a new value (do not try to save blank value)
            if scrape_results['twitter_handle_found'] and positive_value_exists(scrape_results['twitter_handle']):
                twitter_handle = scrape_results['twitter_handle']
                twitter_handles_found += 1

            if scrape_results['facebook_page_found'] and positive_value_exists(scrape_results['facebook_page']):
                facebook_page = scrape_results['facebook_page']
                facebook_pages_found += 1

            save_results = candidate_manager.update_candidate_social_media(candidate, twitter_handle, facebook_page)

        # ######################################
        # We refresh the Twitter information in another function

    status = "ORGANIZATION_SOCIAL_MEDIA_RETRIEVED"
    results = {
        'success':                  True,
        'status':                   status,
        'twitter_handles_found':    twitter_handles_found,
        'facebook_pages_found':     facebook_pages_found,
    }
    return results


def refresh_twitter_candidate_details_for_election(google_civic_election_id, state_code):
    twitter_handles_added = 0
    profiles_refreshed_with_twitter_data = 0

    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_list_manager = CandidateListManager()
    return_list_of_objects = True
    google_civic_election_id_list = [google_civic_election_id]
    candidates_results = candidate_list_manager.retrieve_all_candidates_for_upcoming_election(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=state_code,
        return_list_of_objects=return_list_of_objects)
    if candidates_results['candidate_list_found']:
        candidate_list = candidates_results['candidate_list_objects']

        for candidate in candidate_list:
            # logger.info("refresh_twitter_candidate_details_for_election: " + candidate.candidate_name)
            # Extract twitter_handle from google_civic_election information
            if positive_value_exists(candidate.twitter_url) \
                    and not positive_value_exists(candidate.candidate_twitter_handle):
                # If we got a twitter_url from Google Civic, and we haven't already stored a twitter handle, move it
                candidate.candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate.twitter_url)
                candidate.save()
                twitter_handles_added += 1
            if positive_value_exists(candidate.candidate_twitter_handle) and not positive_value_exists(candidate.twitter_url):
                candidate.twitter_url = 'https://twitter.com/' + candidate.candidate_twitter_handle
                # logger.info(
                #     'refresh_twitter_candidate_details_for_election, twitter_url set to ' + candidate.twitter_url)
                candidate.save()
            if positive_value_exists(candidate.twitter_url) and not positive_value_exists(candidate.candidate_url):
                candidate.candidate_url = candidate.twitter_url
                # logger.info(
                #     'refresh_twitter_candidate_details_for_election, candidate_url set to ' + candidate.candidate_url)
                candidate.save()

            if positive_value_exists(candidate.candidate_twitter_handle):
                refresh_twitter_candidate_details(candidate)
                profiles_refreshed_with_twitter_data += 1
                refresh_candidate_results = refresh_candidate_data_from_master_tables(candidate.we_vote_id)

    status = "CANDIDATE_SOCIAL_MEDIA_RETRIEVED"
    results = {
        'success':                              True,
        'status':                               status,
        'twitter_handles_added':                twitter_handles_added,
        'profiles_refreshed_with_twitter_data': profiles_refreshed_with_twitter_data,
    }
    return results


def transfer_candidate_twitter_handles_from_google_civic(google_civic_election_id=0, state_code=''):
    twitter_handles_transferred = 0
    status = ""
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_list_object = CandidateListManager()
    return_list_of_objects = True
    google_civic_election_id_list = [google_civic_election_id]
    results = candidate_list_object.retrieve_all_candidates_for_upcoming_election(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=state_code,
        return_list_of_objects=return_list_of_objects)
    status += results['status']
    if results['success']:
        candidate_list = results['candidate_list_objects']
    else:
        candidate_list = []

    for candidate in candidate_list:
        if not candidate.twitter_url:
            continue
        # Only proceed if we don't already have a twitter_handle
        if not positive_value_exists(candidate.candidate_twitter_handle):
            candidate.candidate_twitter_handle = candidate.twitter_url.replace("https://twitter.com/", "")
            candidate.save()
            twitter_handles_transferred += 1

        # ######################################
        # We refresh the Twitter information in another function

    status += " CANDIDATE_TWITTER_HANDLES_TRANSFERRED"
    results = {
        'success':                      True,
        'status':                       status,
        'twitter_handles_transferred':  twitter_handles_transferred,
    }
    return results


def twitter_sign_in_start_for_api(voter_device_id, return_url, cordova):  # twitterSignInStart
    """

    :param voter_device_id:
    :param return_url: Where to direct the browser at the very end of the process
    :param cordova:
    :return:
    """
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':                      False,
            'status':                       "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id':              voter_device_id,
            'twitter_redirect_url':         '',
            'voter_info_retrieved':         False,
            'switch_accounts':              False,
            'jump_to_request_voter_info':   False,
            'return_url':                   return_url,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status':                       "VALID_VOTER_MISSING",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'twitter_redirect_url':         '',
            'voter_info_retrieved':         False,
            'switch_accounts':              False,
            'jump_to_request_voter_info':   False,
            'return_url':                   return_url,
        }
        return results

    voter = results['voter']

    twitter_user_manager = TwitterUserManager()
    twitter_user_results = twitter_user_manager.retrieve_twitter_link_to_voter(voter.we_vote_id, read_only=True)
    if twitter_user_results['twitter_link_to_voter_found']:
        error_results = {
            'status':                       "TWITTER_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'twitter_redirect_url':         '',
            'voter_info_retrieved':         False,
            'switch_accounts':              False,  # If true, new voter_device_id returned
            'jump_to_request_voter_info':   False,
            'return_url':                   return_url,
        }
        return error_results

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
    if auth_response_results['twitter_auth_response_found']:
        twitter_auth_response = auth_response_results['twitter_auth_response']
    else:
        # Create a new twitter_auth_response entry with only the voter_device_id
        auth_create_results = twitter_auth_manager.update_or_create_twitter_auth_response(voter_device_id)

        if not auth_create_results['twitter_auth_response_created']:
            error_results = {
                'status':                       auth_create_results['status'],
                'success':                      False,
                'voter_device_id':              voter_device_id,
                'twitter_redirect_url':         '',
                'voter_info_retrieved':         False,
                'switch_accounts':              False,  # If true, new voter_device_id returned
                'jump_to_request_voter_info':   False,
                'return_url':                   return_url,
            }
            return error_results

        twitter_auth_response = auth_create_results['twitter_auth_response']

    callback_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequest/"  # twitterSignInRequestAccessToken
    callback_url += "?voter_info_mode=0"
    callback_url += "&voter_device_id=" + voter_device_id
    callback_url += "&return_url=" + return_url
    callback_url += "&cordova=" + str(cordova)

    try:
        # We take the Consumer Key and the Consumer Secret, and request a token & token_secret
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, callback_url)
        twitter_authorization_url = auth.get_authorization_url()
        request_token_dict = auth.request_token
        twitter_request_token = ''
        twitter_request_token_secret = ''

        if 'oauth_token' in request_token_dict:
            twitter_request_token = request_token_dict['oauth_token']
        if 'oauth_token_secret' in request_token_dict:
            twitter_request_token_secret = request_token_dict['oauth_token_secret']

        # We save these values in the TwitterAuthResponse table, and then return a twitter_authorization_url
        # where the voter signs in
        # Once they sign in to the Twitter login, they are redirected back to the We Vote callback_url
        # On that callback_url page, we are told if they are signed in
        #  on Twitter or not, and capture an access key we can use to retrieve information about the Twitter user
        # NOTE: Regarding the callback url, I think this can just be a direct call to the API server,
        #  since we have the voter_device_id
        if positive_value_exists(twitter_request_token) and positive_value_exists(twitter_request_token_secret):
            twitter_auth_response.twitter_request_token = twitter_request_token
            twitter_auth_response.twitter_request_secret = twitter_request_token_secret
            twitter_auth_response.save()

            success = True
            status = "TWITTER_REDIRECT_URL_RETRIEVED"
        else:
            success = False
            status = "TWITTER_REDIRECT_URL_NOT_RETRIEVED"

    except tweepy.TooManyRequests:
        success = False
        status = 'TWITTER_RATE_LIMIT_ERROR'
    except tweepy.TweepyException as error_instance:
        success = False
        err_string = 'GENERAL_TWEEPY_EXCEPTION'
        try:
            # Yuck, we should iterate down until we get the first string
            err_string = error_instance.args[0].args[0].args[0]
        except Exception:
            pass
        print(err_string)
        status = 'TWITTER_SIGN_IN_START: {}'.format(err_string)
    except Exception as e1:
        success = False
        status = 'TWITTER_SIGN_IN_START: {}'.format(e1)

    if success:
        results = {
            'status':                       status,
            'success':                      True,
            'voter_device_id':              voter_device_id,
            'twitter_redirect_url':         twitter_authorization_url,
            'voter_info_retrieved':         False,
            'switch_accounts':              False,
            'jump_to_request_voter_info':   False,
            'return_url':                   return_url,
        }
    else:
        results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'twitter_redirect_url':         '',
            'voter_info_retrieved':         False,
            'switch_accounts':              False,
            'jump_to_request_voter_info':   False,
            'return_url':                   return_url,
        }
    return results


def twitter_native_sign_in_save_for_api(voter_device_id, twitter_access_token, twitter_access_secret):
    """
    For react-native-oauth, we receive the tokens from a single authenticate() call, and save them to the
    TwitterAuthManager().  This is equivalent to Steps 1 & 2 in the WebApp oAuth processing

    :param voter_device_id:
    :param twitter_access_token:  react-native-oauth refers to this as the "access_token"
    :param twitter_access_secret: react-native-oauth refers to this as the "access_token_secret"
    :return:
    """
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':                      False,
            'status':                       "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id':              voter_device_id,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status':                       "VALID_VOTER_MISSING",
            'success':                      False,
            'voter_device_id':              voter_device_id,
        }
        return results

    voter = results['voter']

    twitter_user_manager = TwitterUserManager()
    twitter_user_results = twitter_user_manager.retrieve_twitter_link_to_voter(voter.we_vote_id, read_only=True)
    if twitter_user_results['twitter_link_to_voter_found']:
        error_results = {
            'status':                       "TWITTER_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success':                      False,
            'voter_device_id':              voter_device_id,
         }
        return error_results

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
    if auth_response_results['twitter_auth_response_found']:
        twitter_auth_response = auth_response_results['twitter_auth_response']
    else:
        # Create a new twitter_auth_response entry with only the voter_device_id
        auth_create_results = twitter_auth_manager.update_or_create_twitter_auth_response(voter_device_id)

        if not auth_create_results['twitter_auth_response_created']:
            error_results = {
                'status':                       auth_create_results['status'],
                'success':                      False,
                'voter_device_id':              voter_device_id,
            }
            return error_results

        twitter_auth_response = auth_create_results['twitter_auth_response']

    try:
        if positive_value_exists(twitter_access_token) and positive_value_exists(twitter_access_secret):
            twitter_auth_response.twitter_access_token = twitter_access_token
            twitter_auth_response.twitter_access_secret = twitter_access_secret
            twitter_auth_response.twitter_request_token = TWITTER_NATIVE_INDICATOR
            twitter_auth_response.twitter_request_secret = TWITTER_NATIVE_INDICATOR
            twitter_auth_response.save()

            success = True
            status = 'TWITTER_TOKENS_STORED'
        else:
            success = False
            status = 'TWITTER_TOKENS_NOT_STORED_DUE_TO_BAD_PASSED_IN_TOKENS'
            logger.error('twitter_native_sign_in_save_for_api -- TWITTER_TOKENS_NOT_STORED_BAD_PASSED_IN_TOKENS')

    except Exception as e:
        success = False
        status = 'TWITTER_TOKEN_EXCEPTION_ON_FAILED_SAVE'
        logger.error('twitter_native_sign_in_save_for_api -- save threw exception: ' + str(e))

    if success:
        results = {
            'status':                       status,
            'success':                      True,
            'voter_device_id':              voter_device_id,
            'voter_info_retrieved':         False,
            'switch_accounts':              False,
            'jump_to_request_voter_info':   False,
        }
    else:
        results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'voter_info_retrieved':         False,
            'switch_accounts':              False,
            'jump_to_request_voter_info':   False,
        }
    return results


def twitter_sign_in_request_access_token_for_api(voter_device_id,
                                                 incoming_request_token, incoming_oauth_verifier,
                                                 return_url, cordova):
    """
    twitterSignInRequestAccessToken
    After signing in and agreeing to the application's terms, the user is redirected back to the application with
    the same request token and another value, this time the OAuth verifier.

    Within this function we use
    1) the request token and
    2) request secret along with the
    3) OAuth verifier to get an access token, also from Twitter.
    :param voter_device_id:
    :param incoming_request_token:
    :param incoming_oauth_verifier:
    :param return_url: If a value is provided, return to this URL when the whole process is complete
    :param cordova:
    :return:
    """
    status = ''
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':                          False,
            'status':                           "VALID_VOTER_DEVICE_ID_MISSING ",
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url':                       return_url,
            'cordova':                          cordova,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status':                           "VALID_VOTER_MISSING",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url':                       return_url,
            'cordova':                          cordova,
        }
        return results

    voter = results['voter']

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
    if not auth_response_results['twitter_auth_response_found']:
        results = {
            'status':                           "REQUEST_ACCESS_TOKEN-TWITTER_AUTH_RESPONSE_NOT_FOUND ",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url':                       return_url,
            'cordova':                          cordova,
        }
        return results

    twitter_auth_response = auth_response_results['twitter_auth_response']

    if not twitter_auth_response.twitter_request_token == incoming_request_token:
        results = {
            'status':                           "TWITTER_REQUEST_TOKEN_DOES_NOT_MATCH_STORED_VOTER_VALUE ",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url':                       return_url,
            'cordova':                          cordova,
        }
        return results

    twitter_access_token = ''
    twitter_access_token_secret = ''
    try:
        # We take the Request Token, Request Secret, and OAuth Verifier and request an access_token
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.request_token = {'oauth_token': twitter_auth_response.twitter_request_token,
                              'oauth_token_secret': twitter_auth_response.twitter_request_secret}
        auth.get_access_token(incoming_oauth_verifier)
        if positive_value_exists(auth.access_token) and positive_value_exists(auth.access_token_secret):
            twitter_access_token = auth.access_token
            twitter_access_token_secret = auth.access_token_secret

    except tweepy.TooManyRequests:
        success = False
        status = 'TWITTER_RATE_LIMIT_ERROR'
    except tweepy.TweepyException as error_instance:
        success = False
        err_string = 'GENERAL_TWEEPY_EXCEPTION'
        try:
            # Dec 2012: Tweepy V$ (Twitter V2) returns these errors as (yuck): List[dict[str, Union[int, str]]]
            err_string = error_instance.args[0].args[0].args[0]
        except Exception:
            pass
        print(err_string)
        status = 'TWITTER_SIGN_IN_REQUEST_ACCESS_TOKEN: {}'.format(err_string)
    except Exception as e:
        success = False
        status += "TWEEPY_EXCEPTION: " + str(e) + " "

    try:
        # We save these values in the TwitterAuthResponse table
        if positive_value_exists(twitter_access_token) and positive_value_exists(twitter_access_token_secret):
            twitter_auth_response.twitter_access_token = twitter_access_token
            twitter_auth_response.twitter_access_secret = twitter_access_token_secret
            twitter_auth_response.save()

            success = True
            status += "TWITTER_ACCESS_TOKEN_RETRIEVED_AND_SAVED "
        else:
            success = False
            status += "TWITTER_ACCESS_TOKEN_NOT_RETRIEVED "
    except Exception as e:
        success = False
        status += "TWITTER_ACCESS_TOKEN_NOT_SAVED "

    if success:
        results = {
            'status':                           status,
            'success':                          True,
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': True,
            'return_url':                       return_url,
            'cordova':                          cordova,
        }
    else:
        results = {
            'status':                           status,
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url':                       return_url,
            'cordova':                          cordova,
        }
    return results


def twitter_sign_in_request_voter_info_for_api(voter_device_id, return_url):
    """
    (not directly called by) twitterSignInRequestVoterInfo
    When here, the incoming voter_device_id should already be authenticated
    :param voter_device_id:
    :param return_url: Where to return the browser when sign in process is complete
    :return:
    """
    status = ''
    twitter_handle = ''
    twitter_handle_found = False
    tweepy_user_object = None
    twitter_user_object_found = False
    voter_info_retrieved = False
    switch_accounts = False
    twitter_secret_key = ""

    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':              False,
            'status':               "VALID_VOTER_DEVICE_ID_MISSING ",
            'voter_device_id':      voter_device_id,
            'twitter_handle':       twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'voter_info_retrieved': voter_info_retrieved,
            'switch_accounts':      switch_accounts,
            'return_url':           return_url,
            'twitter_secret_key':   twitter_secret_key,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status':               "VALID_VOTER_MISSING ",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'twitter_handle':       twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'voter_info_retrieved': voter_info_retrieved,
            'switch_accounts':      switch_accounts,
            'return_url':           return_url,
            'twitter_secret_key':   twitter_secret_key,
        }
        return results

    voter = results['voter']
    voter_we_vote_id = voter.we_vote_id

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
    if not auth_response_results['twitter_auth_response_found']:
        results = {
            'status':               "TWITTER_AUTH_RESPONSE_NOT_FOUND ",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'twitter_handle':       twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'voter_info_retrieved': voter_info_retrieved,
            'switch_accounts':      switch_accounts,
            'return_url':           return_url,
            'twitter_secret_key':   twitter_secret_key,
        }
        return results

    twitter_auth_response = auth_response_results['twitter_auth_response']
    success = True

    # December 2021: Using the Twitter 1.1 API for verify_credentials, since it is not yet available in 2.0
    # https://developer.twitter.com/en/docs/twitter-api/migrate/twitter-api-endpoint-map
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(twitter_auth_response.twitter_access_token, twitter_auth_response.twitter_access_secret)

    api = tweepy.API(auth)

    try:
        tweepy_user_object = api.verify_credentials()
        twitter_json = tweepy_user_object._json

        status += 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_SUCCESSFUL '
        twitter_handle = tweepy_user_object.screen_name
        twitter_handle_found = True
        twitter_user_object_found = True
    except tweepy.TooManyRequests:
        success = False
        status = 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_RATE_LIMIT_ERROR '
    except tweepy.TweepyException as error_instance:
        err_string = 'GENERAL_TWEEPY_EXCEPTION'
        try:
            # Dec 2012: Tweepy V$ (Twitter V2) returns these errors as (yuck): List[dict[str, Union[int, str]]]
            err_string = error_instance.args[0].args[0].args[0]
        except Exception:
            pass
        print(err_string)
        status = 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_TWEEPY_ERROR: {}'.format(err_string)
    except Exception as e:
        success = False
        status += "TWEEPY_EXCEPTION: " + str(e) + " "

    if twitter_user_object_found:
        status += "TWITTER_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT "
        success = True
        save_user_results = twitter_auth_manager.save_twitter_auth_values(twitter_auth_response, tweepy_user_object)

        if save_user_results['success']:
            voter_info_retrieved = True
        status += save_user_results['status']

    twitter_user_manager = TwitterUserManager()
    twitter_link_to_voter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        voter_we_vote_id, read_only=True)
    if twitter_link_to_voter_results['twitter_link_to_voter_found']:
        twitter_link_to_voter = twitter_link_to_voter_results['twitter_link_to_voter']
        twitter_secret_key = twitter_link_to_voter.secret_key

    results = {
        'status':               status,
        'success':              success,
        'voter_device_id':      voter_device_id,
        'twitter_handle':       twitter_handle,
        'twitter_handle_found': twitter_handle_found,
        'voter_info_retrieved': voter_info_retrieved,
        'switch_accounts':      switch_accounts,
        'return_url':           return_url,
        'twitter_secret_key':   twitter_secret_key,
    }
    return results


def twitter_process_deferred_images_for_api(status, success, twitter_id, twitter_name, twitter_profile_banner_url_https,
                                            twitter_profile_image_url_https, twitter_secret_key, twitter_screen_name,
                                            voter_we_vote_id_for_cache):
    # After the voter signs in, and the ballot page (or other) is displayed, then we process the images, to speed up signin
    status = ''
    if (not positive_value_exists(success)):
        return {
            'status': 'twitter_process_deferred_images_for_api_received_empty_dictionary',
            'success': False,
            'twitter_images_were_processed': False,
        }
    # voter_we_vote_id_for_cache = voter_we_vote_id_for_cache
    # twitter_id = twitter_imagtwitter_id
    # success = twitter_image_load_info['success']
    t0 = time()

    # Cache original and resized images
    cache_results = cache_master_and_resized_image(
        voter_we_vote_id=voter_we_vote_id_for_cache,
        twitter_id=twitter_id,
        twitter_screen_name=twitter_screen_name,
        twitter_profile_image_url_https=twitter_profile_image_url_https,
        twitter_profile_banner_url_https=twitter_profile_banner_url_https,
        image_source=TWITTER)
    cached_twitter_profile_image_url_https = cache_results['cached_twitter_profile_image_url_https']
    cached_twitter_profile_banner_url_https = cache_results['cached_twitter_profile_banner_url_https']
    we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
    we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
    we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

    # Retrieve twitter user details from twitter
    results = retrieve_twitter_user_info(twitter_id, twitter_screen_name)
    if not results['success']:
        twitter_json = {
            'id': twitter_id,
            'name': twitter_name,
            'screen_name': twitter_screen_name,
            'profile_image_url_https': twitter_profile_image_url_https,
            'twitter_profile_image_url_https': twitter_profile_image_url_https,
        }
    else:
        twitter_json = results['twitter_json']

    twitter_user_manager = TwitterUserManager()
    twitter_user_results = twitter_user_manager.update_or_create_twitter_user(
        twitter_json=twitter_json,
        twitter_id=twitter_id,
        cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
        cached_twitter_profile_banner_url_https=cached_twitter_profile_banner_url_https,
        we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)

    status += twitter_user_results['status']
    if positive_value_exists(cached_twitter_profile_image_url_https):
        twitter_profile_image_url_https = cached_twitter_profile_image_url_https
    else:
        twitter_profile_image_url_https = twitter_profile_image_url_https

    if success:
        twitter_profile_banner_url_https = ""
        try:
            twitter_profile_banner_url_https = twitter_user_results['twitter_user'].twitter_profile_banner_url_https
        except Exception:
            pass

        try:
            OrganizationManager.update_organization_single_voter_data(twitter_id,
                                                                      we_vote_hosted_profile_image_url_large,
                                                                      we_vote_hosted_profile_image_url_medium,
                                                                      we_vote_hosted_profile_image_url_tiny,
                                                                      twitter_profile_banner_url_https)
        except Exception as e:
            logger.error('twitter_process_deferred_images caught exception calling '
                         'update_organization_single_voter_data: '
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e)))

        try:
            voter_manager = VoterManager()
            voter_results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id_for_cache)
            voter_manager.save_twitter_user_values(
                voter=voter_results['voter'],
                twitter_user_object=twitter_json,
                cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        except Exception as e:
            logger.error('twitter_process_deferred_images caught exception calling '
                         'save_twitter_user_values: '
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    t6 = time()
    print('twitter_process_deferred_images total time {:.3f}'.format(t6 - t0))

    return {
        'status':                                   status,
        'success':                                  success,
        'twitter_secret_key':                       twitter_secret_key,
        'twitter_images_were_processed':            True,
        'twitter_profile_image_url_https':          twitter_profile_image_url_https,
        'we_vote_hosted_profile_image_url_large':   we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny,
    }


def twitter_sign_in_retrieve_for_api(voter_device_id, image_load_deferred):  # twitterSignInRetrieve
    """
    We are asking for the results of the most recent Twitter authentication

    July 2017: We want the TwitterUser class/table to be the authoritative source of twitter info, ideally
    TwitterUser feeds the duplicated columns in voter, organization, candidate, etc.
    Unfortunately Django Auth, pre-populates voter with some key info first, which is fine, but makes it less clean.

    December 2021:  This function used to process the incoming image URLs from twitter, resize them and store them in
    AWS inline, which took more than 5 seconds.  Then we would merge the temporary voter record with a record we found
    on disk, and process the images again, for another 5 seconds.  Now the processing of the images is initiated after
    the signin is complete via a call to twitter_process_deferred_images_for_api

    :param voter_device_id:
    :return:
    """
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   "TWITTER_SIGN_IN_NO_VOTER",
            'existing_twitter_account_found':           False,
            'twitter_access_secret':                    "",
            'twitter_access_token':                     "",
            'twitter_id':                               0,
            'twitter_image_load_info':                  "",
            'twitter_name':                             "",
            'twitter_profile_image_url_https':          "",
            'twitter_request_secret':                   "",
            'twitter_request_token':                    "",
            'twitter_screen_name':                      "",
            'twitter_secret_key':                       "",
            'twitter_sign_in_failed':                   True,
            'twitter_sign_in_found':                    False,
            'twitter_sign_in_verified':                 False,
            'voter_device_id':                          voter_device_id,
            'voter_has_data_to_preserve':               False,
            'voter_we_vote_id':                         "",
            'voter_we_vote_id_attached_to_twitter':     "",
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    "",
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_has_data_to_preserve = voter.has_data_to_preserve()

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
    status = auth_response_results['status']
    if not auth_response_results['twitter_auth_response_found']:
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   status,
            'existing_twitter_account_found':           False,
            'twitter_access_secret':                    "",
            'twitter_access_token':                     "",
            'twitter_id':                               0,
            'twitter_image_load_info':                  "",
            'twitter_name':                             "",
            'twitter_profile_image_url_https':          "",
            'twitter_request_secret':                   "",
            'twitter_request_token':                    "",
            'twitter_screen_name':                      "",
            'twitter_secret_key':                       "",
            'twitter_sign_in_failed':                   True,
            'twitter_sign_in_found':                    False,
            'twitter_sign_in_verified':                 False,
            'voter_device_id':                          voter_device_id,
            'voter_has_data_to_preserve':               False,
            'voter_we_vote_id':                         voter_we_vote_id,
            'voter_we_vote_id_attached_to_twitter':     "",
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    "",
        }
        return error_results

    success = True
    twitter_auth_response = auth_response_results['twitter_auth_response']
    twitter_id = twitter_auth_response.twitter_id

    if not twitter_id:
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   status,
            'existing_twitter_account_found':           False,
            'twitter_access_secret':                    "",
            'twitter_access_token':                     "",
            'twitter_id':                               0,
            'twitter_image_load_info':                  "",
            'twitter_name':                             "",
            'twitter_profile_image_url_https':          "",
            'twitter_request_secret':                   "",
            'twitter_request_token':                    "",
            'twitter_screen_name':                      "",
            'twitter_secret_key':                       "",
            'twitter_sign_in_failed':                   True,
            'twitter_sign_in_found':                    False,
            'twitter_sign_in_verified':                 False,
            'voter_device_id':                          voter_device_id,
            'voter_has_data_to_preserve':               False,
            'voter_we_vote_id':                         voter_we_vote_id,
            'voter_we_vote_id_attached_to_twitter':     "",
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    "",
        }
        return error_results

    twitter_user_manager = TwitterUserManager()
    twitter_sign_in_verified = True
    twitter_sign_in_failed = False
    twitter_secret_key = ""
    existing_twitter_account_found = False
    voter_we_vote_id_attached_to_twitter = ""
    repair_twitter_related_voter_caching_now = False

    t0 = time()

    twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_voter(twitter_id, read_only=True)
    if twitter_link_results['twitter_link_to_voter_found']:
        twitter_link_to_voter = twitter_link_results['twitter_link_to_voter']
        status += " " + twitter_link_results['status']
        voter_we_vote_id_attached_to_twitter = twitter_link_to_voter.voter_we_vote_id
        twitter_secret_key = twitter_link_to_voter.secret_key
        existing_twitter_account_found = True
        repair_twitter_related_voter_caching_now = True
    else:
        # See if we need to heal the data - look in the voter table for any records with twitter_id
        voter_results = voter_manager.retrieve_voter_by_twitter_id_old(twitter_id)
        if voter_results['voter_found']:
            voter_with_twitter_id = voter_results['voter']
            voter_we_vote_id_attached_to_twitter = voter_with_twitter_id.we_vote_id
            if positive_value_exists(voter_we_vote_id_attached_to_twitter):
                save_results = twitter_user_manager.create_twitter_link_to_voter(
                    twitter_id, voter_we_vote_id_attached_to_twitter)
                status += " " + save_results['status']
                if save_results['success']:
                    repair_twitter_related_voter_caching_now = True
        else:
            # The very first time a new twitter user signs in
            save_results = twitter_user_manager.create_twitter_link_to_voter(
                twitter_id, voter_we_vote_id)
    t1 = time()

    if twitter_id:
        # We do this here as part of the Twitter sign in process, to make sure we don't have multiple organizations
        #  using the same twitter_id (once there is a TwitterLinkToOrganization).
        organization_list_manager = OrganizationListManager()
        repair_results = organization_list_manager.repair_twitter_related_organization_caching(
            twitter_id)
        status += repair_results['status']
        if repair_twitter_related_voter_caching_now:
            # And make sure we don't have multiple voters using same twitter_id (once there is a TwitterLinkToVoter)
            repair_results = voter_manager.repair_twitter_related_voter_caching(
                twitter_id)
            status += repair_results['status']

    t2 = time()

    if positive_value_exists(voter_we_vote_id_attached_to_twitter):
        voter_we_vote_id_for_cache = voter_we_vote_id_attached_to_twitter
    else:
        voter_we_vote_id_for_cache = voter_we_vote_id

    twitter_image_load_info = {
        'status': status,
        'success': success,
        'twitter_id': twitter_id,
        'twitter_name': twitter_auth_response.twitter_name,
        'twitter_profile_banner_url_https': twitter_auth_response.twitter_profile_banner_url_https,
        'twitter_profile_image_url_https': twitter_auth_response.twitter_profile_banner_url_https,
        'twitter_secret_key': twitter_secret_key,
        'twitter_screen_name': twitter_auth_response.twitter_screen_name,
        'voter_we_vote_id_for_cache': voter_we_vote_id_for_cache,
    }
    if not positive_value_exists(image_load_deferred):
        # For compatibility with legacy apps, load the images inline (ie not deferred)
        twitter_process_deferred_images_for_api(status, success, twitter_id, twitter_auth_response.twitter_name,
                                                twitter_auth_response.twitter_profile_banner_url_https,
                                                twitter_auth_response.twitter_profile_banner_url_https,
                                                twitter_secret_key,
                                                twitter_auth_response.twitter_screen_name,
                                                voter_we_vote_id_for_cache)

    # Retrieve twitter user details from twitter
    results = retrieve_twitter_user_info(twitter_id, twitter_auth_response.twitter_screen_name)
    if not results['success']:
        twitter_json = {
            'id': twitter_id,
            'name': twitter_auth_response.twitter_name,
            'screen_name': twitter_auth_response.twitter_screen_name,
            'profile_image_url_https': twitter_auth_response.twitter_profile_image_url_https,
        }
    else:
        twitter_json = results['twitter_json']

    twitter_user_results = twitter_user_manager.update_or_create_twitter_user(
        twitter_json=twitter_json,
        twitter_id=twitter_id)

    json_data = {
        'success':                                  success,
        'status':                                   status,
        'existing_twitter_account_found':           existing_twitter_account_found,
        'twitter_access_secret':                    twitter_auth_response.twitter_access_secret,
        'twitter_access_token':                     twitter_auth_response.twitter_access_token,
        'twitter_id':                               twitter_id,
        'twitter_image_load_info':                  twitter_image_load_info,
        'twitter_name':                             twitter_auth_response.twitter_name,
        'twitter_profile_image_url_https':          None,
        'twitter_request_secret':                   twitter_auth_response.twitter_request_secret,
        'twitter_request_token':                    twitter_auth_response.twitter_request_token,
        'twitter_screen_name':                      twitter_auth_response.twitter_screen_name,
        'twitter_secret_key':                       twitter_secret_key,
        'twitter_sign_in_failed':                   twitter_sign_in_failed,
        'twitter_sign_in_found':                    auth_response_results['twitter_auth_response_found'],
        'twitter_sign_in_verified':                 twitter_sign_in_verified,
        'voter_device_id':                          voter_device_id,
        'voter_has_data_to_preserve':               voter_has_data_to_preserve,
        'voter_we_vote_id':                         voter_we_vote_id,
        'voter_we_vote_id_attached_to_twitter':     voter_we_vote_id_attached_to_twitter,
        'we_vote_hosted_profile_image_url_large':   None,
        'we_vote_hosted_profile_image_url_medium':  None,
        'we_vote_hosted_profile_image_url_tiny':    None,
    }

    t6 = time()

    # print('twitter_sign_in_retrieve_for_api total time {:.3f}'.format(t6 - t0) +
    #              ', t0 -> t1 {:.3f}'.format(t1 - t0) + ', t0 -> t2 {:.3f}'.format(t2 - t0) +
    #              ', t0 -> t6 {:.3f}'.format(t6 - t0))

    return json_data


def twitter_retrieve_ids_i_follow_for_api(voter_device_id):     # twitterRetrieveIdsIFollow
    """

    :param voter_device_id:
    :return:
    """
    success = False

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
    status = auth_response_results['status']
    if not auth_response_results['twitter_auth_response_found']:
        error_results = {
            'success':                  success,
            'status':                   status,
            'voter_device_id':          voter_device_id,
            'twitter_ids_i_follow':     [],
        }
        return error_results

    twitter_auth_response = auth_response_results['twitter_auth_response']

    if not twitter_auth_response.twitter_id:
        success = False
        error_results = {
            'success':                  success,
            'status':                   status,
            'voter_device_id':          voter_device_id,
            'twitter_ids_i_follow':     [],
        }
        return error_results

    twitter_user_manager = TwitterUserManager()

    # Now that voter is signed in, reach out to twitter to get up to 5000 ids of other twitter users
    twitter_ids_i_follow_results = twitter_user_manager.retrieve_twitter_ids_i_follow_from_twitter(
        twitter_auth_response.twitter_id, twitter_auth_response.twitter_access_token,
        twitter_auth_response.twitter_access_secret)
    status += ' ' + twitter_ids_i_follow_results['status']
    twitter_ids_i_follow = twitter_ids_i_follow_results['twitter_ids_i_follow']
    if twitter_ids_i_follow_results['success']:
        twitter_who_i_follow_results = twitter_user_manager.create_twitter_who_i_follow_entries(
            twitter_auth_response.twitter_id, twitter_ids_i_follow)
        status += ' ' + twitter_who_i_follow_results['status']
        success = twitter_who_i_follow_results['success']
    results = {
        'success':              success,
        'status':               status,
        'voter_device_id':      voter_device_id,
        'twitter_ids_i_follow': twitter_ids_i_follow
    }
    return results


def voter_twitter_save_to_current_account_for_api(voter_device_id):  # voterTwitterSaveToCurrentAccount
    """

    :param voter_device_id:
    :return:
    """
    status = ""
    success = False
    twitter_account_created = False
    twitter_link_to_organization_exists = False
    twitter_link_to_organization_twitter_id = 0

    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':                  False,
            'status':                   "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id':          voter_device_id,
            'twitter_account_created':  twitter_account_created,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)  # Cannot be read_only
    if not positive_value_exists(results['voter_found']):
        results = {
            'success':                  False,
            'status':                   "VALID_VOTER_MISSING",
            'voter_device_id':          voter_device_id,
            'twitter_account_created':  twitter_account_created,
        }
        return results

    voter = results['voter']

    twitter_user_manager = TwitterUserManager()
    twitter_results = twitter_user_manager.retrieve_twitter_link_to_voter(0, voter.we_vote_id, read_only=True)
    if twitter_results['twitter_link_to_voter_found']:
        # We are surprised to be here because we try to only call this routine from the WebApp if the Twitter Account
        #  isn't currently linked to any voter
        error_results = {
            'status':                   "TWITTER_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'twitter_account_created':  twitter_account_created,
        }
        return error_results

    twitter_auth_manager = TwitterAuthManager()
    auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)  # Cannot be read_only
    if not auth_response_results['twitter_auth_response_found']:
        error_results = {
            'status':                   "TWITTER_AUTH_RESPONSE_COULD_NOT_BE_FOUND",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'twitter_account_created':  twitter_account_created,
        }
        return error_results

    twitter_auth_response = auth_response_results['twitter_auth_response']

    # Make sure this Twitter id isn't linked to another voter
    twitter_collision_results = twitter_user_manager.retrieve_twitter_link_to_voter(twitter_auth_response.twitter_id,
                                                                                    read_only=True)
    if twitter_collision_results['twitter_link_to_voter_found']:
        # If we are here, then there is in fact a twitter_link_to_voter tied to another voter account
        # We are surprised to be here because we try to only call this routine from the WebApp if the Twitter Account
        #  isn't currently linked to any voter
        error_results = {
            'status':                   "TWITTER_OWNER_VOTER_FOUND_FOR_ANOTHER_VOTER_WHEN_NOT_EXPECTED",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'twitter_account_created':  twitter_account_created,
        }
        return error_results

    link_results = twitter_user_manager.create_twitter_link_to_voter(twitter_auth_response.twitter_id,
                                                                     voter.we_vote_id)

    if not link_results['twitter_link_to_voter_saved']:
        error_results = {
            'status':                   link_results['status'],
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'twitter_account_created':  twitter_account_created,
        }
        return error_results

    twitter_account_created = True
    twitter_link_to_voter = link_results['twitter_link_to_voter']

    # Update voter with cached Twitter info
    results = voter_manager.save_twitter_user_values(voter, twitter_auth_response)
    status += results['status'] + ", "
    success = results['success']
    voter = results['voter']

    # Now find out if there is an organization already linked to this Twitter account
    twitter_results = twitter_user_manager.retrieve_twitter_link_to_organization(voter.we_vote_id, read_only=True)
    if twitter_results['twitter_link_to_organization_found']:
        twitter_link_to_organization = twitter_results['twitter_link_to_organization']
        twitter_link_to_organization_exists = True
        twitter_link_to_organization_twitter_id = twitter_link_to_organization.twitter_id

        # If here, we know that this organization is not linked to another voter, so we can update the
        #  voter to connect to this organization
        # Is this voter already linked to another organization?
        if voter.linked_organization_we_vote_id:
            # We need to merge the twitter_link_to_organization.organization_we_vote_id with
            #  voter.linked_organization_we_vote_id
            if positive_value_exists(twitter_link_to_organization.organization_we_vote_id) and \
                    positive_value_exists(voter.linked_organization_we_vote_id) and \
                    twitter_link_to_organization.organization_we_vote_id != voter.linked_organization_we_vote_id:
                # We are here, so we know that we found a twitter_link_to_organization, but it doesn't match
                # the org linked to this voter. So we want to merge these two organizations.
                twitter_link_to_organization_organization_id = 0  # We calculate this in move_organization...
                voter_linked_to_organization_organization_id = 0  # We calculate this in move_organization...
                move_organization_to_another_complete_results = move_organization_to_another_complete(
                    twitter_link_to_organization_organization_id,
                    twitter_link_to_organization.organization_we_vote_id,
                    voter_linked_to_organization_organization_id,
                    voter.linked_organization_we_vote_id,
                    voter.id, voter.we_vote_id
                )
                status += " " + move_organization_to_another_complete_results['status']
                # We do not need to change voter.linked_organization_we_vote_id since we merged into that organization
        else:
            # Connect voter.linked_organization_we_vote_id with twitter_link_to_organization.organization_we_vote_id
            try:
                voter.linked_organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id
                voter.save()
            except Exception as e:
                success = False
                status += "VOTER_LINKED_ORGANIZATION_WE_VOTE_ID_NOT_UPDATED "
    else:
        # If here, we know that a twitter_link_to_organization does not exist
        # 1) Try to find existing organization with twitter_user_id
        organization_manager = OrganizationManager()
        organization_from_twitter_id_old_results = organization_manager.retrieve_organization_from_twitter_user_id_old(
            twitter_auth_response.twitter_id
        )
        new_organization_ready = False
        if organization_from_twitter_id_old_results['organization_found']:
            new_organization = organization_from_twitter_id_old_results['organization']
            new_organization_ready = True
        else:
            # 2) Create organization with twitter_user_id
            organization_manager = OrganizationManager()
            create_results = organization_manager.create_organization(
                organization_name=voter.get_full_name(),
                organization_image=voter.voter_photo_url(),
                twitter_id=twitter_auth_response.twitter_id,
                organization_type=INDIVIDUAL,
                we_vote_hosted_profile_image_url_large=voter.we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny
            )
            if create_results['organization_created']:
                # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                new_organization = create_results['organization']
                new_organization_ready = True
            else:
                new_organization = Organization()
                status += "NEW_ORGANIZATION_COULD_NOT_BE_CREATED "

        if new_organization_ready:
            try:
                voter.linked_organization_we_vote_id = new_organization.organization_we_vote_id
                voter.save()
            except Exception as e:
                status += "UNABLE_TO_UPDATE_VOTER_LINKED_ORGANIZATION_WE_VOTE_ID "

            try:
                # Create TwitterLinkToOrganization
                results = twitter_user_manager.create_twitter_link_to_organization(
                    twitter_auth_response.twitter_id, voter.linked_organization_we_vote_id)
                if results['twitter_link_to_organization_saved']:
                    status += "TwitterLinkToOrganization_CREATED_AFTER_ORGANIZATION_CREATE "
                    twitter_link_to_organization_exists = True
                    twitter_link_to_organization_twitter_id = twitter_auth_response.twitter_id
                else:
                    status += results['status']
                    status += "TwitterLinkToOrganization_NOT_CREATED_AFTER_ORGANIZATION_CREATE "
            except Exception as e:
                status += results['status']
                status += "UNABLE_TO_CREATE_TWITTER_LINK_TO_ORG "

    if twitter_link_to_organization_exists:
        organization_list_manager = OrganizationListManager()
        repair_results = organization_list_manager.repair_twitter_related_organization_caching(
            twitter_link_to_organization_twitter_id)
        status += repair_results['status']

    results = {
        'success':                  success,
        'status':                   status,
        'voter_device_id':          voter_device_id,
        'twitter_account_created':  twitter_account_created,
    }
    return results
