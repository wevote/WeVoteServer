# apis_v1/views/views_twitter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json
from urllib.parse import quote
from urllib.parse import urlencode

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

import wevote_functions.admin
from config.base import get_environment_variable, get_environment_variable_default
from import_export_twitter.controllers import twitter_identity_retrieve_for_api, twitter_sign_in_start_for_api, \
    twitter_sign_in_request_access_token_for_api, twitter_sign_in_request_voter_info_for_api, \
    twitter_process_deferred_images_for_api, twitter_sign_in_retrieve_for_api, twitter_retrieve_ids_i_follow_for_api, \
    twitter_oauth1_user_handler_for_api
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
LOG_OAUTH = get_environment_variable_default("TWITTER_LOG_OAUTH_STEPS", False)


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

    # 2022-12-04 We are moving twitterIdentityRetrieve over to the CDN, and removing anything custom to voter
    # voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = twitter_identity_retrieve_for_api(twitter_handle)
    json_data = {
        'status':                                   results['status'],
        'success':                                  results['success'],
        'twitter_handle':                           results['twitter_handle'],
        'owner_found':                              results['owner_found'],
        'kind_of_owner':                            results['kind_of_owner'],
        'owner_we_vote_id':                         results['owner_we_vote_id'],
        'owner_id':                                 results['owner_id'],
        'google_civic_election_id':                 results['google_civic_election_id'],
        'twitter_description':                      results['twitter_description'],
        'twitter_followers_count':                  results['twitter_followers_count'],
        'twitter_photo_url':                        results['twitter_photo_url'],
        'we_vote_hosted_profile_image_url_large':   results['we_vote_hosted_profile_image_url_large'],
        'we_vote_hosted_profile_image_url_medium':  results['we_vote_hosted_profile_image_url_medium'],
        'we_vote_hosted_profile_image_url_tiny':    results['we_vote_hosted_profile_image_url_tiny'],
        'twitter_profile_banner_url_https':         results['twitter_profile_banner_url_https'],
        'twitter_user_website':                     results['twitter_user_website'],
        'twitter_id':                               results['twitter_id'],
        'twitter_name':                             results['twitter_name'],
        }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_oauth1_user_handler_view(request):  # twitterOauth1UserHandler March 2024 for Twitter API 2
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    oauth_token = request.GET.get('oauth_token', '')
    oauth_verifier = request.GET.get('oauth_verifier', '')

    if LOG_OAUTH:
        logger.error('(Ok) twitter_oauth1_user_handler_view oauth_token: %s   oauth_verifier %s', oauth_token,
                     oauth_verifier)

    results = twitter_oauth1_user_handler_for_api(voter_device_id, oauth_token, oauth_verifier)

    return HttpResponse(json.dumps(results), content_type='application/json')


def twitter_sign_in_start_view(request):  # twitterSignInStart (Step 1)
    """
    Step 1 of the Twitter Sign In Process for the WebApp
    Start off the process of signing in with Twitter (twitterSignInStart)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return_url = request.GET.get('return_url', '')
    cordova = request.GET.get('cordova', False)
    if LOG_OAUTH:
        logger.error('(Ok) twitter_sign_in_start_view twitterSignInStart (Step 1) entry point: %s', str(request.GET))

    results = twitter_sign_in_start_for_api(voter_device_id, return_url, cordova)

    if positive_value_exists(results['jump_to_request_voter_info']) and positive_value_exists(results['return_url']):
        next_step_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequest/"  # twitterSignInRequestVoterInfo
        next_step_url += "?voter_info_mode=1"
        next_step_url += "&voter_device_id=" + voter_device_id
        next_step_url += "&return_url=" + quote(results['return_url'], safe='')
        next_step_url += "&cordova=" + str(cordova)
        return HttpResponseRedirect(next_step_url)

    if cordova:
        return_url = results['return_url']
        if return_url == 'http://nonsense.com':
            return_url = ''
        elif return_url.startswith('http://nonsense.com/?'):
            return_url = return_url.replace('http://nonsense.com/?', '')
    else:
        return_url = None


    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      voter_device_id,
        'twitter_redirect_url': results['twitter_redirect_url'],
        'voter_info_retrieved': results['voter_info_retrieved'],
        'switch_accounts':      results['switch_accounts'],  # If true, new voter_device_id returned
        'cordova':              cordova,
        'return_url':           return_url,
    }

    if cordova:
        return twitter_cordova_signin_response(request, json_data)
    else:
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_request_view(request):  # twitterSignInRequest (Switch for Step 1 & Step 2)
    if LOG_OAUTH:
        logger.error('(Ok) twitter_sign_in_request_view entry point: %s', str(request.GET))
    voter_info_mode = request.GET.get('voter_info_mode', 0)
    if positive_value_exists(voter_info_mode):
        return twitter_sign_in_request_voter_info_view(request)
    else:
        return twitter_sign_in_request_access_token_view(request)


def twitter_sign_in_request_access_token_view(request):  # twitterSignInRequestAccessToken (Step 2)
    """
    Step 2 of the Twitter Sign In Process (twitterSignInRequestAccessToken) for the WebApp
    :param request:
    :return:
    """

    voter_info_mode = request.GET.get('voter_info_mode', 0)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    incoming_request_token = request.GET.get('oauth_token', '')
    incoming_oauth_verifier = request.GET.get('oauth_verifier', '')
    return_url = request.GET.get('return_url', '')
    cordova = request.GET.get('cordova', False)
    if LOG_OAUTH:
        logger.error('(Ok) twitter_sign_in_request_access_token_view entry point: %s', str(request.GET))

    results = twitter_sign_in_request_access_token_for_api(voter_device_id,
                                                           incoming_request_token, incoming_oauth_verifier,
                                                           return_url, cordova)

    if positive_value_exists(results['return_url']):
        next_step_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequest/"  # twitterSignInRequestVoterInfo
        next_step_url += "?voter_info_mode=1"
        next_step_url += "&voter_device_id=" + voter_device_id
        next_step_url += "&return_url=" + quote(results['return_url'], safe='')
        next_step_url += "&cordova=" + str(cordova)
        return HttpResponseRedirect(next_step_url)

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'access_token_and_secret_returned': results['access_token_and_secret_returned'],
        'cordova':                          cordova,
        'voter_info_mode':                  voter_info_mode,
    }

    if cordova:
        return twitter_cordova_signin_response(request, json_data)
    else:
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_request_voter_info_view(request):  # twitterSignInRequestVoterInfo (Step 3)
    """
    Step 3 of the Twitter Sign In Process (twitterSignInRequestVoterInfo)
    :param request:
    :return:
    """

    cordova = request.GET.get('cordova', False)
    return_url = request.GET.get('return_url', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_info_mode = request.GET.get('voter_info_mode', 0)
    if LOG_OAUTH:
        logger.error('(Ok) twitter_sign_in_request_voter_info_view: %s', str(request.GET))

    results = twitter_sign_in_request_voter_info_for_api(voter_device_id, return_url)

    if positive_value_exists(results['return_url']) and not positive_value_exists(cordova):
        return HttpResponseRedirect(results['return_url'])

    if cordova:
        return_url = results['return_url'].replace('http://nonsense.com/?', '')

    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      results['voter_device_id'],
        'twitter_handle':       results['twitter_handle'],
        'twitter_handle_found': results['twitter_handle_found'],
        'voter_info_mode':      voter_info_mode,
        'voter_info_retrieved': results['voter_info_retrieved'],
        'switch_accounts':      results['switch_accounts'],
        'return_url':           return_url
    }

    if cordova:
        return twitter_cordova_signin_response(request, json_data)
    else:
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_cordova_signin_response(request, json_data):
    """
    https://medium.com/@jlchereau/stop-using-inappbrowser-for-your-cordova-phonegap-oauth-flow-a806b61a2dc5
    :param request:
    :return: A webpage that initiates a native scheme for iOS (received in Application.js in the WebApp)
    """
    logger.debug("twitter_cordova_signin_response: " + urlencode(json_data))

    if positive_value_exists(json_data['return_url']):
        template_values = {
            'query_string': json_data['return_url'],
        }
    else:
        template_values = {
            'query_string': urlencode(json_data),
        }

    # return render(request, 'cordova/cordova_ios_redirect_to_scheme.html', template_values,
    #               content_type='text/html')
    return render(request, 'cordova/cordova_ios_redirect_to_scheme.html', template_values,
                  content_type='text/html')


def twitter_process_deferred_images_view(request):  # twitterProcessDeferredImages
    """
    Deferred processing of the twitter image URLs, to save 5 or 10 seconds on initial sign in
    :param request:
    :return:
    """
    results = twitter_process_deferred_images_for_api(
        organization_we_vote_id=request.GET.get('organization_we_vote_id'),
        status=request.GET.get('status'),
        success=request.GET.get('success'),
        twitter_id=request.GET.get('twitter_id'),
        twitter_name=request.GET.get('twitter_name'),
        twitter_profile_banner_url_https=request.GET.get('twitter_profile_banner_url_https'),
        twitter_profile_image_url_https=request.GET.get('twitter_profile_image_url_https'),
        twitter_secret_key=request.GET.get('twitter_secret_key'),
        twitter_screen_name=request.GET.get('twitter_screen_name'),
        voter_we_vote_id_for_cache=request.GET.get('voter_we_vote_id_for_cache')
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def twitter_sign_in_retrieve_view(request):  # twitterSignInRetrieve
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    image_load_deferred = request.GET.get('image_load_deferred'),
    load_deferred = image_load_deferred and image_load_deferred[0] == 'true'

    results = twitter_sign_in_retrieve_for_api(voter_device_id=voter_device_id, image_load_deferred=load_deferred)

    json_data = {
        'status':                                   results['status'],
        'success':                                  results['success'],
        'existing_twitter_account_found':           results['existing_twitter_account_found'],
        'twitter_image_load_info':                  results['twitter_image_load_info'],
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
