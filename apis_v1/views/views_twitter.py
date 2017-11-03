# apis_v1/views/views_twitter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse, HttpResponseRedirect
from import_export_twitter.controllers import twitter_sign_in_start_for_api, \
    twitter_sign_in_request_access_token_for_api, twitter_sign_in_request_voter_info_for_api, \
    twitter_sign_in_retrieve_for_api, twitter_retrieve_ids_i_follow_for_api, twitter_native_sign_in_save_for_api
import json
from twitter.controllers import twitter_identity_retrieve_for_api
from urllib.parse import quote
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def twitter_identity_retrieve_view(request):  # twitterIdentityRetrieve
    """
    Find the kind of owner and unique id of this twitter handle. We use this to take an incoming URI like
    https://wevote.guide/RepBarbaraLee and return the owner of 'RepBarbaraLee'. (twitterIdentityRetrieve)
    :param request:
    :return:
    """
    twitter_handle = request.GET.get('twitter_handle', '')

    if not positive_value_exists(twitter_handle):
        status = 'VALID_TWITTER_HANDLE_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'twitter_handle':           twitter_handle,
            'owner_found':              False,
            'kind_of_owner':            '',
            'owner_we_vote_id':         '',
            'owner_id':                 0,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = twitter_identity_retrieve_for_api(twitter_handle, voter_device_id)
    json_data = {
        'status':                                   results['status'],
        'success':                                  results['success'],
        'twitter_handle':                           results['twitter_handle'],
        'owner_found':                              results['owner_found'],
        'kind_of_owner':                            results['kind_of_owner'],
        'owner_we_vote_id':                         results['owner_we_vote_id'],
        'owner_id':                                 results['owner_id'],
        'google_civic_election_id':                 results['google_civic_election_id'],
        # These values only returned if kind_of_owner == TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE
        'twitter_description':                      results['twitter_description'],
        'twitter_followers_count':                  results['twitter_followers_count'],
        'twitter_photo_url':                        results['twitter_photo_url'],
        'we_vote_hosted_profile_image_url_large':   results['we_vote_hosted_profile_image_url_large'],
        'we_vote_hosted_profile_image_url_medium':  results['we_vote_hosted_profile_image_url_medium'],
        'we_vote_hosted_profile_image_url_tiny':    results['we_vote_hosted_profile_image_url_tiny'],
        'twitter_profile_banner_url_https':         results['twitter_profile_banner_url_https'],
        'twitter_user_website':                     results['twitter_user_website'],
        'twitter_name':                             results['twitter_name'],
        }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_start_view(request):  # twitterSignInStart
    """
    Step 1 of the Twitter Sign In Process for the WebApp
    Start off the process of signing in with Twitter (twitterSignInStart)
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return_url = request.GET.get('return_url', '')

    results = twitter_sign_in_start_for_api(voter_device_id, return_url)

    if positive_value_exists(results['jump_to_request_voter_info']) and positive_value_exists(results['return_url']):
        next_step_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequestVoterInfo/"
        next_step_url += "?voter_device_id=" + voter_device_id
        next_step_url += "&return_url=" + quote(results['return_url'], safe='')
        return HttpResponseRedirect(next_step_url)

    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      voter_device_id,
        'twitter_redirect_url': results['twitter_redirect_url'],
        'voter_info_retrieved': results['voter_info_retrieved'],
        'switch_accounts':      results['switch_accounts'],  # If true, new voter_device_id returned
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_request_access_token_view(request):  # twitterSignInRequestAccessToken
    """
    Step 2 of the Twitter Sign In Process (twitterSignInRequestAccessToken) for the WebApp
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    incoming_request_token = request.GET.get('oauth_token', '')
    incoming_oauth_verifier = request.GET.get('oauth_verifier', '')
    return_url = request.GET.get('return_url', '')

    results = twitter_sign_in_request_access_token_for_api(voter_device_id,
                                                           incoming_request_token, incoming_oauth_verifier,
                                                           return_url)

    if positive_value_exists(results['return_url']):
        next_step_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequestVoterInfo/"
        next_step_url += "?voter_device_id=" + voter_device_id
        next_step_url += "&return_url=" + quote(results['return_url'], safe='')
        return HttpResponseRedirect(next_step_url)

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'access_token_and_secret_returned': results['access_token_and_secret_returned'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_native_sign_in_save_view(request):  # twitterNativeSignInSave
    """
    For the native "app" react-native-oauth, replaces Steps 1 & 2 of the WebApp Twitter Sign In Process.
    Receives twitter_access_token and twitter_access_token_secret from the native app's authenticate() call
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    twitter_access_token = request.GET.get('twitter_access_token', '')
    twitter_access_token_secret = request.GET.get('twitter_access_token_secret', '')
    resultsNative = twitter_native_sign_in_save_for_api(voter_device_id, twitter_access_token, twitter_access_token_secret)

    if resultsNative['success'] != True:
        logger.error("Bad save in twitter_native_sign_in_save_view: " + resultsNative['status'])

    # Call equivalent of oAuth for WebApp Step 3
    resultsVoterInfo = twitter_sign_in_request_voter_info_for_api(voter_device_id, "Native API Call, No Return URL")

    json_data = {
        'status':               resultsVoterInfo['status'] + ' '  + resultsNative['status'],
        'success':              resultsVoterInfo['success'],
        'twitter_handle':       resultsVoterInfo['twitter_handle'],
        'twitter_handle_found': resultsVoterInfo['twitter_handle_found'],
        'twitter_secret_key':   resultsVoterInfo['twitter_secret_key'],
        'voter_device_id':      resultsVoterInfo['voter_device_id'],
        'voter_info_retrieved': resultsVoterInfo['voter_info_retrieved'],
        'switch_accounts':      resultsVoterInfo['switch_accounts'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_request_voter_info_view(request):  # twitterSignInRequestVoterInfo
    """
    Step 3 of the Twitter Sign In Process (twitterSignInRequestVoterInfo)
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return_url = request.GET.get('return_url', '')

    results = twitter_sign_in_request_voter_info_for_api(voter_device_id, return_url)

    if positive_value_exists(results['return_url']):
        return HttpResponseRedirect(results['return_url'])

    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      results['voter_device_id'],
        'twitter_handle':       results['twitter_handle'],
        'twitter_handle_found': results['twitter_handle_found'],
        'voter_info_retrieved': results['voter_info_retrieved'],
        'switch_accounts':      results['switch_accounts'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_retrieve_view(request):  # twitterSignInRetrieve
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    results = twitter_sign_in_retrieve_for_api(voter_device_id=voter_device_id)

    json_data = {
        'status':                                   results['status'],
        'success':                                  results['success'],
        'existing_twitter_account_found':           results['existing_twitter_account_found'],
        'twitter_profile_image_url_https':          results['twitter_profile_image_url_https'],
        'twitter_retrieve_attempted':               True,
        'twitter_secret_key':                       results['twitter_secret_key'],
        'twitter_sign_in_failed':                   results['twitter_sign_in_failed'],
        'twitter_sign_in_found':                    results['twitter_sign_in_found'],
        'twitter_sign_in_verified':                 results['twitter_sign_in_verified'],
        'voter_device_id':                          voter_device_id,
        'voter_has_data_to_preserve':               results['voter_has_data_to_preserve'],
        'voter_we_vote_id':                         results['voter_we_vote_id'],
        'voter_we_vote_id_attached_to_twitter':     results['voter_we_vote_id_attached_to_twitter'],
        'we_vote_hosted_profile_image_url_large':   results['we_vote_hosted_profile_image_url_large'],
        'we_vote_hosted_profile_image_url_medium':  results['we_vote_hosted_profile_image_url_medium'],
        'we_vote_hosted_profile_image_url_tiny':    results['we_vote_hosted_profile_image_url_tiny'],
        # 'twitter_who_i_follow':                   results['twitter_who_i_follow'],
        # There are more values we currently aren't returning
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_retrieve_ids_i_follow_view(request): # twitterRetrieveIdsIFollow
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    results = twitter_retrieve_ids_i_follow_for_api(voter_device_id=voter_device_id)

    json_data = {
        'status':                   results['status'],
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'twitter_ids_i_follow':     results['twitter_ids_i_follow'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
