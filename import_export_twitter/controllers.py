# import_export_twitter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/controllers.py for routines that manage internal twitter data

from candidate.models import CandidateCampaignManager, CandidateCampaignListManager
from config.base import get_environment_variable
from organization.controllers import update_social_media_statistics_in_other_tables
from organization.models import Organization, OrganizationManager
import re
from socket import timeout
import tweepy
import urllib.request
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

RE_FACEBOOK = r'//www\.facebook\.com/(?:#!/)?(\w+)'
# RE_FACEBOOK = r'/(?:https?:\/\/)?(?:www\.)?facebook\.com\/(?:(?:\w)*#!\/)?(?:pages\/)?(?:[\w\-]*\/)*?(\/)?([^/?]*)/'
FACEBOOK_BLACKLIST = ['group', 'group.php', 'None']
# NOTE: Scraping a website for the Facebook handle is more complicated than Twitter. There must be an existing
#  solution available? My attempt turned off for now.

# Only pays attention to https://twitter.com or http://twitter.com and ignores www.twitter.com
RE_TWITTER = r'//twitter\.com/(?:#!/)?(\w+)'
TWITTER_BLACKLIST = ['home', 'https', 'intent', 'none', 'search', 'share', 'twitterapi']
TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


class GetOutOfLoop(Exception):
    pass


class GetOutOfLoopLocal(Exception):
    pass


def refresh_twitter_candidate_details(candidate_campaign):
    candidate_campaign_manager = CandidateCampaignManager()

    if not candidate_campaign:
        status = "TWITTER_CANDIDATE_DETAILS_NOT_RETRIEVED-CANDIDATE_MISSING"
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if candidate_campaign.candidate_twitter_handle:
        status = "TWITTER_CANDIDATE_DETAILS-REACHING_OUT_TO_TWITTER"
        results = retrieve_twitter_user_info(candidate_campaign.candidate_twitter_handle)

        if results['success']:
            status = "TWITTER_CANDIDATE_DETAILS_RETRIEVED_FROM_TWITTER"
            save_results = candidate_campaign_manager.update_candidate_twitter_details(
                candidate_campaign, results['twitter_json'])
    else:
        status = "TWITTER_CANDIDATE_DETAILS-CLEARING_DETAILS"
        save_results = candidate_campaign_manager.clear_candidate_twitter_details(candidate_campaign)

    results = {
        'success':                  True,
        'status':                   status,
    }
    return results


def refresh_twitter_organization_details(organization):
    organization_manager = OrganizationManager()

    if not organization:
        status = "ORGANIZATION_TWITTER_DETAILS_NOT_RETRIEVED-ORG_MISSING"
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if organization.organization_twitter_handle:
        status = "ORGANIZATION_TWITTER_DETAILS-REACHING_OUT_TO_TWITTER"
        results = retrieve_twitter_user_info(organization.organization_twitter_handle)

        if results['success']:
            status = "ORGANIZATION_TWITTER_DETAILS_RETRIEVED_FROM_TWITTER"
            save_results = organization_manager.update_organization_twitter_details(
                organization, results['twitter_json'])

            if save_results['success']:
                results = update_social_media_statistics_in_other_tables(organization)
                status = "ORGANIZATION_TWITTER_DETAILS_RETRIEVED_FROM_TWITTER_AND_SAVED"
    else:
        status = "ORGANIZATION_TWITTER_DETAILS-CLEARING_DETAILS"
        save_results = organization_manager.clear_organization_twitter_details(organization)

        if save_results['success']:
            results = update_social_media_statistics_in_other_tables(organization)
            status = "ORGANIZATION_TWITTER_DETAILS_CLEARED_FROM_DB"

    results = {
        'success':                  True,
        'status':                   status,
    }
    return results


def retrieve_twitter_user_info(twitter_handle):
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)

    twitter_handle_found = False
    twitter_json = []
    try:
        twitter_user = api.get_user(twitter_handle)
        twitter_json = twitter_user._json
        success = True
        status = 'TWITTER_RETRIEVE_SUCCESSFUL'
        twitter_handle_found = True
    except tweepy.RateLimitError:
        success = False
        status = 'TWITTER_RATE_LIMIT_ERROR'
    except tweepy.error.TweepError as error_instance:
        success = False
        status = ''
        error_tuple = error_instance.args
        for error_dict in error_tuple:
            for one_error in error_dict:
                status += '[' + one_error['message'] + '] '

    results = {
        'status':               status,
        'success':              success,
        'twitter_handle':       twitter_handle,
        'twitter_handle_found': twitter_handle_found,
        'twitter_json':         twitter_json,
    }
    return results


def scrape_social_media_from_one_site(site_url):
    twitter_handle = ''
    twitter_handle_found = False
    facebook_page = ''
    facebook_page_found = False
    success = False
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
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        for line in page.readlines():
            try:
                if not twitter_handle_found:
                    for m in re.finditer(RE_TWITTER, line.decode()):
                        if m:
                            name = m.group(1)
                            if name not in TWITTER_BLACKLIST:
                                twitter_handle = name
                                twitter_handle_found = True
                                raise GetOutOfLoopLocal
            except GetOutOfLoopLocal:
                pass
            # SEE NOTE ABOUT FACEBOOK SCRAPING ABOVE
            # try:
            #     if not facebook_page_found:
            #         for m2 in re.finditer(RE_FACEBOOK, line.decode()):
            #             if m2:
            #                 possible_page1 = m2.group(1)
            #                 if possible_page1 not in FACEBOOK_BLACKLIST:
            #                     facebook_page = possible_page1
            #                     facebook_page_found = True
            #                     raise GetOutOfLoopLocal
            #                 try:
            #                     possible_page2 = m2.group(2)
            #                     if possible_page2 not in FACEBOOK_BLACKLIST:
            #                         facebook_page = possible_page2
            #                         facebook_page_found = True
            #                         raise GetOutOfLoopLocal
            #                     # ATTEMPT 1
            #                     # start_of_close_tag_index = possible_page2.find('"')
            #                     # possible_page2 = possible_page2[:start_of_close_tag_index]
            #                     # ATTEMPT 2
            #                     # fb_re = re.compile(r'facebook.com([^"]+)')
            #                     # results = fb_re.findall(possible_page2)
            #                 except Exception as error_instance:
            #                     pass
            #                 # possible_page3 = m2.group(3)
            #                 # possible_page4 = m2.group(4)
            # except GetOutOfLoopLocal:
            #     pass
            if twitter_handle_found:  # and facebook_page_found:
                raise GetOutOfLoop
        success = True
        status = 'FINISHED_SCRAPING_PAGE'
    except timeout:
        status = "SCRAPE_TIMEOUT_ERROR"
        success = False
    except GetOutOfLoop:
        success = True
        status = 'TWITTER_HANDLE_FOUND-BREAK_OUT'
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status = "SCRAPE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status = "SCRAPE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status':               status,
        'success':              success,
        'page_redirected':      twitter_handle,
        'twitter_handle':       twitter_handle,
        'twitter_handle_found': twitter_handle_found,
        'facebook_page':        facebook_page,
        'facebook_page_found':  facebook_page_found,
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


def retrieve_twitter_data_for_all_organizations(state_code='', google_civic_election_id=0, first_retrieve_only=False):
    number_of_twitter_accounts_queried = 0
    number_of_organizations_updated = 0

    organization_manager = OrganizationManager()
    organization_list_query = Organization.objects.order_by('organization_name')
    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code=state_code)

    # TODO DALE limit this to organizations that have a voter guide in a particular election

    organization_list = organization_list_query
    for organization in organization_list:
        # ######################################
        # If we have a Twitter handle for this org, refresh the data
        if organization.organization_twitter_handle:
            retrieved_twitter_data = False
            if first_retrieve_only:
                if not positive_value_exists(organization.twitter_followers_count):
                    results = retrieve_twitter_user_info(organization.organization_twitter_handle)
                    retrieved_twitter_data = results['success']
                    number_of_twitter_accounts_queried += 1
            else:
                results = retrieve_twitter_user_info(organization.organization_twitter_handle)
                retrieved_twitter_data = results['success']
                number_of_twitter_accounts_queried += 1

            if retrieved_twitter_data:
                number_of_organizations_updated += 1
                save_results = organization_manager.update_organization_twitter_details(
                    organization, results['twitter_json'])

                if save_results['success']:
                    results = update_social_media_statistics_in_other_tables(organization)

    status = "ALL_ORGANIZATION_TWITTER_DATA_RETRIEVED"
    results = {
        'success':                              True,
        'status':                               status,
        'number_of_twitter_accounts_queried':   number_of_twitter_accounts_queried,
        'number_of_organizations_updated':      number_of_organizations_updated,
    }
    return results


def scrape_and_save_social_media_for_candidates_in_one_election(google_civic_election_id=0):
    facebook_pages_found = 0
    twitter_handles_found = 0
    force_retrieve = False
    status = ""
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_manager = CandidateCampaignManager()
    candidate_list_manager = CandidateCampaignListManager()
    return_list_of_objects = True
    results = candidate_list_manager.retrieve_all_candidates_for_upcoming_election(google_civic_election_id,
                                                                                   return_list_of_objects)
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


def refresh_twitter_candidate_details_for_election(google_civic_election_id):
    twitter_handles_added = 0
    profiles_refreshed_with_twitter_data = 0

    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_list_manager = CandidateCampaignListManager()
    return_list_of_objects = True
    candidates_results = candidate_list_manager.retrieve_all_candidates_for_upcoming_election(
        google_civic_election_id, return_list_of_objects)
    if candidates_results['candidate_list_found']:
        candidate_list = candidates_results['candidate_list_objects']

        for candidate in candidate_list:
            # Extract twitter_handle from google_civic_election information
            if positive_value_exists(candidate.twitter_url) \
                    and not positive_value_exists(candidate.candidate_twitter_handle):
                # If we got a twitter_url from Google Civic, and we haven't already stored a twitter handle, move it
                candidate.candidate_twitter_handle = candidate.twitter_url.replace("https://twitter.com/", "")
                candidate.save()
                twitter_handles_added += 1
            if positive_value_exists(candidate.candidate_twitter_handle):
                refresh_twitter_candidate_details(candidate)
                profiles_refreshed_with_twitter_data += 1

    status = "CANDIDATE_SOCIAL_MEDIA_RETRIEVED"
    results = {
        'success':                              True,
        'status':                               status,
        'twitter_handles_added':                twitter_handles_added,
        'profiles_refreshed_with_twitter_data': profiles_refreshed_with_twitter_data,
    }
    return results


def transfer_candidate_twitter_handles_from_google_civic(google_civic_election_id=0):
    twitter_handles_transferred = 0
    status = ""
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_list_object = CandidateCampaignListManager()
    return_list_of_objects = True
    results = candidate_list_object.retrieve_all_candidates_for_upcoming_election(google_civic_election_id,
                                                                                  return_list_of_objects)
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


def twitter_sign_in_start_for_api(voter_device_id, return_url):  # twitterSignInStart
    """

    :param voter_device_id:
    :param return_url: Where to direct the browser at the very end of the process
    :return:
    """
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':              False,
            'status':               "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id':      voter_device_id,
            'twitter_redirect_url': '',
            'voter_info_retrieved': False,
            'switch_accounts':      False,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status':               "VALID_VOTER_MISSING",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'twitter_redirect_url': '',
            'voter_info_retrieved': False,
            'switch_accounts':      False,
        }
        return results

    voter = results['voter']

    if voter.twitter_access_token and voter.twitter_access_secret:
        # If here the voter might already be signed in, so we don't want to ask them to approve again
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(voter.twitter_access_token, voter.twitter_access_secret)

        api = tweepy.API(auth)

        try:
            tweepy_user_object = api.me()
            success = True
        # What is the error situation where the twitter_access_token and twitter_access_secret are no longer valid?
        # We need to deal with this (wipe them from the database and rewind to the right place in the process
        except tweepy.RateLimitError:
            success = False
            status = 'TWITTER_RATE_LIMIT_ERROR'
        except tweepy.error.TweepError as error_instance:
            success = False
            status = ''
            error_tuple = error_instance.args
            for error_dict in error_tuple:
                for one_error in error_dict:
                    status += '[' + one_error['message'] + '] '

        if success:
            # Reach out to the twitterSignInRequestVoterInfo -- no need to redirect
            empty_return_url = ""
            voter_info_results = twitter_sign_in_request_voter_info_for_api(voter_device_id, empty_return_url)

            success = voter_info_results['success']
            status = "SKIPPED_AUTH_DIRECT_REQUEST_VOTER_INFO: " + voter_info_results['status']
            results = {
                'status':               status,
                'success':              success,
                'voter_device_id':      voter_device_id,
                'twitter_redirect_url': '',
                'voter_info_retrieved': voter_info_results['voter_info_retrieved'],
                'switch_accounts':      voter_info_results['switch_accounts'],  # If true, new voter_device_id returned
            }
            return results
        else:
            # Somehow reset tokens and start over.
            pass

    callback_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequestAccessToken/"
    callback_url += "?voter_device_id=" + voter_device_id
    callback_url += "&return_url=" + return_url

    # This is where
    twitter_authorization_url = ''

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

        # We save these values in the Voter table, and then return a twitter_authorization_url where the voter signs in
        # Once they sign in to the Twitter login, they are redirected back to the We Vote callback_url
        # On that callback_url page, we are told if they are signed in
        #  on Twitter or not, and capture an access key we can use to retrieve information about the Twitter user
        # NOTE: Regarding the callback url, I think this can just be a direct call to the API server,
        #  since we have the voter_device_id
        if positive_value_exists(twitter_request_token) and positive_value_exists(twitter_request_token_secret):
            voter.twitter_request_token = twitter_request_token
            voter.twitter_request_secret = twitter_request_token_secret
            voter.save()

            success = True
            status = "TWITTER_REDIRECT_URL_RETRIEVED"
        else:
            success = False
            status = "TWITTER_REDIRECT_URL_NOT_RETRIEVED"

    except tweepy.RateLimitError:
        success = False
        status = 'TWITTER_RATE_LIMIT_ERROR'
    except tweepy.error.TweepError as error_instance:
        success = False
        status = 'TWITTER_SIGN_IN_START: '
        error_tuple = error_instance.args
        for error_dict in error_tuple:
            for one_error in error_dict:
                status += '[' + one_error['message'] + '] '

    if success:
        results = {
            'status':               status,
            'success':              True,
            'voter_device_id':      voter_device_id,
            'twitter_redirect_url': twitter_authorization_url,
            'voter_info_retrieved': False,
            'switch_accounts':      False,
        }
    else:
        results = {
            'status':               status,
            'success':              False,
            'voter_device_id':      voter_device_id,
            'twitter_redirect_url': '',
            'voter_info_retrieved': False,
            'switch_accounts':      False,
        }
    return results


def twitter_sign_in_request_access_token_for_api(voter_device_id,
                                                 incoming_request_token, incoming_oauth_verifier,
                                                 return_url):
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
    :return:
    """
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success': False,
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id': voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url':                   return_url,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status': "VALID_VOTER_MISSING",
            'success': False,
            'voter_device_id': voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url': return_url,
        }
        return results

    voter = results['voter']

    if not voter.twitter_request_token == incoming_request_token:
        results = {
            'status': "TWITTER_REQUEST_TOKEN_DOES_NOT_MATCH_STORED_VOTER_VALUE",
            'success': False,
            'voter_device_id': voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url': return_url,
        }
        return results

    twitter_access_token = ''
    twitter_access_token_secret = ''
    try:
        # We take the Request Token, Request Secret, and OAuth Verifier and request an access_token
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.request_token = {'oauth_token': voter.twitter_request_token,
                              'oauth_token_secret': voter.twitter_request_secret}
        auth.get_access_token(incoming_oauth_verifier)
        if positive_value_exists(auth.access_token) and positive_value_exists(auth.access_token_secret):
            twitter_access_token = auth.access_token
            twitter_access_token_secret = auth.access_token_secret

    except tweepy.RateLimitError:
        success = False
        status = 'TWITTER_RATE_LIMIT_ERROR'
    except tweepy.error.TweepError as error_instance:
        success = False
        status = 'TWITTER_SIGN_IN_REQUEST_ACCESS_TOKEN: '
        error_tuple = error_instance.args
        for error_dict in error_tuple:
            count = 0
            # for one_error in error_dict:
            #     status += '[' + one_error[count] + '] '
            #     count += 1

    try:
        # We save these values in the Voter table
        if positive_value_exists(twitter_access_token) and positive_value_exists(twitter_access_token_secret):
            voter.twitter_access_token = twitter_access_token
            voter.twitter_access_secret = twitter_access_token_secret
            voter.save()

            success = True
            status = "TWITTER_ACCESS_TOKEN_RETRIEVED_AND_SAVED"
        else:
            success = False
            status = "TWITTER_ACCESS_TOKEN_NOT_RETRIEVED"
    except Exception as e:
        success = False
        status = "TWITTER_ACCESS_TOKEN_NOT_SAVED"

    if success:
        results = {
            'status':                           status,
            'success':                          True,
            'voter_device_id':                  voter_device_id,
            'access_token_and_secret_returned': True,
            'return_url':                       return_url,
        }
    else:
        results = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'access_token_and_secret_returned': False,
            'return_url': return_url,
        }
    return results


def twitter_sign_in_request_voter_info_for_api(voter_device_id, return_url, switch_accounts_if_needed=True):
    """
    twitterSignInRequestVoterInfo
    When here, the incoming voter_device_id should already be authenticated
    :param voter_device_id:
    :param return_url: Where to return the browser when sign in process is complete
    :param switch_accounts_if_needed:
    :return:
    """

    twitter_handle = ''
    twitter_handle_found = False
    tweepy_user_object = None
    twitter_user_object_found = False
    twitter_json = []
    voter_info_retrieved = False
    switch_accounts = False

    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success': False,
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id': voter_device_id,
            'twitter_handle': twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'twitter_json': twitter_json,
            'twitter_user_object': tweepy_user_object,
            'twitter_user_object_found': twitter_user_object_found,
            'voter_info_retrieved': voter_info_retrieved,
            'switch_accounts': switch_accounts,
            'return_url':                   return_url,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'status': "VALID_VOTER_MISSING",
            'success': False,
            'voter_device_id': voter_device_id,
            'twitter_handle': twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'twitter_json': twitter_json,
            'twitter_user_object': tweepy_user_object,
            'twitter_user_object_found': twitter_user_object_found,
            'voter_info_retrieved': voter_info_retrieved,
            'switch_accounts': switch_accounts,
            'return_url':                return_url,
        }
        return results

    voter = results['voter']

    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(voter.twitter_access_token, voter.twitter_access_secret)

    api = tweepy.API(auth)

    try:
        tweepy_user_object = api.me()
        twitter_json = tweepy_user_object._json

        success = True
        status = 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_SUCCESSFUL'
        twitter_handle = tweepy_user_object.screen_name
        twitter_handle_found = True
        twitter_user_object_found = True
    except tweepy.RateLimitError:
        success = False
        status = 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_RATE_LIMIT_ERROR'
    except tweepy.error.TweepError as error_instance:
        success = False
        status = 'TWITTER_SIGN_IN_REQUEST_VOTER_INFO_TWEEPY_ERROR: '
        error_tuple = error_instance.args
        for error_dict in error_tuple:
            for one_error in error_dict:
                status += '[' + one_error['message'] + '] '

    if twitter_user_object_found:
        # We need to deal with these cases

        # 1) Does account already exist?
        results = voter_manager.retrieve_voter_by_twitter_id(tweepy_user_object.id)
        if results['voter_found'] and switch_accounts_if_needed:
            voter_found_with_twitter_id = results['voter']

            switch_accounts = True

            # Relink this voter_device_id to the original account
            voter_device_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_manager.retrieve_voter_device_link(voter_device_id)
            voter_device_link = voter_device_link_results['voter_device_link']

            update_voter_device_link_results = voter_device_manager.update_voter_device_link(
                voter_device_link, voter_found_with_twitter_id)
            if update_voter_device_link_results['voter_device_link_updated']:
                # Transfer access token and secret
                voter_found_with_twitter_id.twitter_access_token = voter.twitter_access_token
                voter_found_with_twitter_id.twitter_access_secret = voter.twitter_access_secret
                voter_found_with_twitter_id.save()

                status += "TWITTER_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT-TRANSFERRED "
                success = True
                save_user_results = voter_manager.save_twitter_user_values(voter_found_with_twitter_id,
                                                                           tweepy_user_object)

                if save_user_results['success']:
                    voter_info_retrieved = True
                status += save_user_results['status']
            else:
                status = "TWITTER_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT-COULD_NOT_TRANSFER "
                success = False

        # 2) If account doesn't exist for this person, save
        else:
            save_user_results = voter_manager.save_twitter_user_values(voter, tweepy_user_object)

            if save_user_results['success']:
                voter_info_retrieved = True

    results = {
        'status':                       status,
        'success':                      success,
        'voter_device_id':              voter_device_id,
        'twitter_handle':               twitter_handle,
        'twitter_handle_found':         twitter_handle_found,
        'twitter_json':                 twitter_json,
        'twitter_user_object':          tweepy_user_object,
        'twitter_user_object_found':    twitter_user_object_found,
        'voter_info_retrieved':         voter_info_retrieved,
        'switch_accounts':              switch_accounts,
        'return_url':                   return_url,
    }
    return results
