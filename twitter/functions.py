# twitter/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json
import re
from datetime import datetime

import tweepy
from dateutil.tz import tz

import wevote_functions.admin
from config.base import get_environment_variable
from exception.models import handle_exception
from twitter.models import create_detailed_counter_entry, mark_detailed_counter_entry
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

TWITTER_BEARER_TOKEN = get_environment_variable("TWITTER_BEARER_TOKEN")
TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")

TWITTER_USER_NOT_FOUND_LOG_RESPONSES = [
    "{'code': 50, 'message': 'User not found.'}",
    "User not found."
]

TWITTER_USER_SUSPENDED_LOG_RESPONSES = [
    "{'code': 63, 'message': 'User has been suspended.'}",
    "User has been suspended."
]


def convert_twitter_user_object_data_to_we_vote_dict(twitter_user_data):
    if twitter_user_data is None:
        twitter_user_data = {}
    twitter_dict = {
        'description': twitter_user_data['description']
        if 'description' in twitter_user_data else '',
        'entities': twitter_user_data['entities']
        if 'entities' in twitter_user_data else '',
        'id': twitter_user_data['id']
        if 'id' in twitter_user_data else '',
        'location': twitter_user_data['location']
        if 'location' in twitter_user_data else '',
        'name': twitter_user_data['name']
        if 'name' in twitter_user_data else '',
        'profile_image_url': twitter_user_data['profile_image_url']
        if 'profile_image_url' in twitter_user_data else '',
        'public_metrics': twitter_user_data['public_metrics']
        if 'public_metrics' in twitter_user_data else '',
        'username': twitter_user_data['username']
        if 'username' in twitter_user_data else '',
        'verified': twitter_user_data['verified']
        if 'verified' in twitter_user_data else '',
        'verified_type': twitter_user_data['verified_type']
        if 'verified_type' in twitter_user_data else '',
        'withheld': twitter_user_data['withheld']
        if 'withheld' in twitter_user_data else '',
    }
    return twitter_dict


def expand_twitter_entities(twitter_dict):
    expanded_url_count = 1
    if 'entities' in twitter_dict:
        # Support for 'expanded_url' and 'expanded_url2'
        if 'url' in twitter_dict['entities']:
            if 'urls' in twitter_dict['entities']['url']:
                if len(twitter_dict['entities']['url']['urls']) > 0:
                    for one_url_dict in twitter_dict['entities']['url']['urls']:
                        if 'expanded_url' in one_url_dict:
                            if expanded_url_count > 1:
                                expanded_url_name = \
                                    "expanded_url{expanded_url_count}".format(expanded_url_count=expanded_url_count)
                                # TODO: Make dynamic -- running into: 'User' object does not support item assignment
                                twitter_dict[expanded_url_name] = one_url_dict['expanded_url']
                            else:
                                twitter_dict['expanded_url'] = one_url_dict['expanded_url']
                            expanded_url_count += 1
    return twitter_dict


def expand_twitter_public_metrics(twitter_dict):
    if 'public_metrics' in twitter_dict:
        public_metrics = twitter_dict['public_metrics']
        if 'followers_count' in public_metrics:
            twitter_dict['followers_count'] = public_metrics['followers_count']
        if 'following_count' in public_metrics:
            twitter_dict['following_count'] = public_metrics['following_count']
    return twitter_dict


def is_valid_twitter_handle_format(twitter_handle):
    if len(twitter_handle) > 15:
        return False
    return True
    # We need to make this function more robust, something like the following...
    # if not positive_value_exists(twitter_handle):
    #     return False
    # pattern = re.compile(r'^[a-zA-Z0-9_]{1,15}$')  # There are some older Twitter handles that are shorter
    # results = pattern.match(twitter_handle)
    # if hasattr(results, 'match'):
    #     if getattr(results, 'match') == twitter_handle:
    #         return True
    # return False


def retrieve_twitter_rate_limit_info():
    try:
        # auth = tweepy.OAuth2BearerHandler(TWITTER_BEARER_TOKEN)  # Theory is that this auth only reports rate_limit_status for requests made with a bearer token
        # See "This limit is considered completely separate from per-application Bearer Token limits."  At https://developer.twitter.com/en/docs/twitter-api/v1/rate-limits
        auth = tweepy.OAuth2AppHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)

        api = tweepy.API(auth)   # This uses the Twitter apiv1, not the apiv2
        limits_json = api.rate_limit_status()   # March 2023, this api is not yet available in Twitter API V2
        # print(json.dumps(limits_json))
        output = []
        for key, value in limits_json['resources'].items():
            for endpoint, value2 in value.items():
                from_zone = tz.tzutc()
                to_zone = tz.tzlocal()
                utc_naive = datetime.fromtimestamp(value2['reset'])
                utc_dt = utc_naive.replace(tzinfo=from_zone)
                local_dt = utc_dt.astimezone(to_zone)
                local_tz = datetime.utcnow().astimezone().tzinfo
                local_tzname = local_tz.tzname(local_dt)
                reset = local_dt.strftime("%Y-%m-%d  %H:%M:%S") + "  " + local_tzname

                output.append({
                    'endpoint': endpoint,
                    'limit': value2['limit'],
                    'remaining': value2['remaining'],
                    'reset': reset,
                })
        return json.dumps(output)
    except Exception as e:
        logger.error('retrieve_twitter_rate_limit_info caught: ' + str(e))
        return ""


def retrieve_twitter_user_info(twitter_user_id=0, twitter_handle='', twitter_api_counter_manager=None, parent=None):
    """
    :param twitter_user_id:
    :param twitter_handle:
    :param twitter_api_counter_manager:
    :param parent, calling function
    :return:
    """
    success = True
    status = ""
    counter = None
    twitter_user_not_found_in_twitter = False
    twitter_user_suspended_by_twitter = False
    write_to_server_logs = False

    twitter_handle_format_valid = is_valid_twitter_handle_format(twitter_handle)

    if not twitter_handle_format_valid:
        status += "TWITTER_HANDLE_TOO_LONG "
        twitter_user_not_found_in_twitter = True
        twitter_dict = {
            'twitter_handle_updates_failing': True,
            'username': twitter_handle,
        }
        twitter_handle_found = False
        results = {
            'status': status,
            'success': success,
            'twitter_handle': twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'twitter_dict': twitter_dict,
            'twitter_user_id': twitter_user_id,
            'twitter_user_not_found_in_twitter': twitter_user_not_found_in_twitter,
            'twitter_user_suspended_by_twitter': twitter_user_suspended_by_twitter,
        }
        return results

    print("tweepy client init. in retrieve_twitter_user_info -- twitter_handle: ", twitter_handle)
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_CONSUMER_KEY,
        consumer_secret=TWITTER_CONSUMER_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)

    # Strip out the twitter handles "False" or "None"
    if twitter_handle is False:
        twitter_handle = ''
    elif twitter_handle is None:
        twitter_handle = ''
    elif twitter_handle:
        twitter_handle_lower = twitter_handle.lower()
        if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
            twitter_handle = ''

    twitter_handle_found = False
    twitter_dict = {}
    from wevote_functions.functions import convert_to_int
    twitter_user_id = convert_to_int(twitter_user_id)
    try:
        if positive_value_exists(twitter_handle):
            # Use Twitter API call counter to track the number of queries we are doing each day
            # if hasattr(twitter_api_counter_manager, 'create_counter_entry'):
            #     twitter_api_counter_manager.create_counter_entry('get_user')

            print("tweepy client get_user #1 in retrieve_twitter_user_info -- twitter_handle: ", twitter_handle)
            counter = create_detailed_counter_entry(
                kind_of_action='get_user',
                function='retrieve_twitter_user_info',
                success=success,
                elements={'username': twitter_handle, 'disambiguator': 1, 'text': parent})
            twitter_user = client.get_user(
                username=twitter_handle,
                user_fields=[
                    'description',
                    'entities',
                    'id',
                    'location',
                    'name',
                    'profile_image_url',
                    'public_metrics',
                    'username',
                    'verified',
                    'verified_type',
                    'withheld',
                ])
            # 'url', We only take in the url from the 'entities' data since 'url' is always a Twitter shortened url

            # [connection_status, created_at, description, entities, id, location, most_recent_tweet_id, name,
            #  pinned_tweet_id, profile_image_url, protected, public_metrics, receives_your_dm, subscription_type, url,
            #  username, verified, verified_type, withheld]
            try:
                twitter_dict = convert_twitter_user_object_data_to_we_vote_dict(twitter_user.data)
                twitter_user_id = getattr(twitter_user.data, 'id')  # Integer value. id_str would be the String value
                twitter_handle_found = positive_value_exists(twitter_user_id)
            except Exception as e:
                status += 'TWITTER_DICT_DATA_NOT_FOUND-' + str(e) + " "
                twitter_dict = {
                    'twitter_handle_updates_failing': True,
                    'username': twitter_handle,
                }
                twitter_user_id = 0
                twitter_handle_found = False
                twitter_user_not_found_in_twitter = True
            success = True
            # status += 'TWITTER_HANDLE_SUCCESS-' + str(twitter_handle) + " "
        elif positive_value_exists(twitter_user_id):
            # Use Twitter API call counter to track the number of queries we are doing each day
            # if hasattr(twitter_api_counter_manager, 'create_counter_entry'):
            #     twitter_api_counter_manager.create_counter_entry('get_user')

            # twitter_user = api.get_user(user_id=twitter_user_id)
            print("tweepy client get_user #2 in retrieve_twitter_user_info -- twitter_handle: ", twitter_handle)
            try:
                counter = create_detailed_counter_entry(
                    kind_of_action='get_user',
                    function='retrieve_twitter_user_info',
                    success=success,
                    elements={
                        'username': twitter_handle,
                        'disambiguator': 2,
                        'text': str(twitter_user_id) + ' - ' + parent
                    },
                )
            except Exception as e:
                logger.error('retrieve_twitter_user_info create_detailed_counter_entry threw ' + str(e))
                counter = None
            try:
                twitter_user = client.get_user(id=twitter_user_id)
                twitter_dict = convert_twitter_user_object_data_to_we_vote_dict(twitter_user.data)
                twitter_user_id = getattr(twitter_user.data, 'id')  # Integer value. id_str would be the String value
                twitter_handle = getattr(twitter_user.data, 'username')
                twitter_handle_found = True
            except Exception as e:
                status += 'TWITTER_JSON_DATA_NOT_FOUND_FROM_ID-' + str(e) + " "
                twitter_dict = {}
                twitter_user_id = 0
            success = True
            # status += 'TWITTER_USER_ID_SUCCESS-' + str(twitter_user_id) + " "
            twitter_handle_found = True
        else:
            twitter_dict = {}
            success = False
            status += 'TWITTER_RETRIEVE_NOT_SUCCESSFUL-MISSING_VARIABLE '
            twitter_handle_found = False
    except tweepy.TooManyRequests as rate_limit_error:
        success = False
        user = twitter_handle if twitter_handle else 'NO_HANDLE'
        status += 'TWITTER_RATE_LIMIT_ERROR (' + user + '): ' + str(rate_limit_error) + " "
        mark_detailed_counter_entry(counter, success, status)
        handle_exception(rate_limit_error, logger=logger, exception_message=status)
        # March 7, 2024 TODO:  We might be able to get useful info in this situation
        #  https://docs.tweepy.org/en/stable/api.html#tweepy.API.rate_limit_status
        # https://developer.twitter.com/en/docs/twitter-api/v1/developer-utilities/rate-limit-status/api-reference/get-application-rate_limit_status
    except tweepy.errors.HTTPException as error_instance:
        if 'User not found.' in error_instance.api_messages:
            status += 'TWITTER_USER_NOT_FOUND_ON_TWITTER: ' + str(error_instance) + ' '
            twitter_user_not_found_in_twitter = True
        else:
            success = False
            status += 'TWITTER_HTTP_EXCEPTION: ' + str(error_instance) + ' '
            handle_exception(error_instance, logger=logger, exception_message=status)
        mark_detailed_counter_entry(counter, False, status)
    except tweepy.errors.TweepyException as error_instance:
        success = False
        status += "TWEEPY_EXCEPTION_ERROR: "
        status += twitter_handle + " " if positive_value_exists(twitter_handle) else ""
        status += str(twitter_user_id) + " " if positive_value_exists(twitter_user_id) else " "
        mark_detailed_counter_entry(counter, success, status)
        if error_instance:
            status += str(error_instance) + " "
        if error_instance and hasattr(error_instance, 'args'):
            try:
                error_tuple = error_instance.args
                for error_dict in error_tuple:
                    for one_error in error_dict:
                        if 'message' in one_error:
                            status += '[' + str(one_error['message']) + '] '
                        if one_error['message'] in TWITTER_USER_NOT_FOUND_LOG_RESPONSES:
                            twitter_user_not_found_in_twitter = True
                        elif one_error['message'] in TWITTER_USER_SUSPENDED_LOG_RESPONSES:
                            twitter_user_suspended_by_twitter = True
                        else:
                            write_to_server_logs = True
            except Exception as e:
                status += "PROBLEM_PARSING_TWEEPY_ERROR: " + str(e) + " "
                write_to_server_logs = True
        else:
            write_to_server_logs = True
        status += "]"
        if write_to_server_logs:
            handle_exception(error_instance, logger=logger, exception_message=status)
    except Exception as e:
        success = False
        status += "TWEEPY_EXCEPTION: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)

    twitter_dict = expand_twitter_entities(twitter_dict)
    twitter_dict = expand_twitter_public_metrics(twitter_dict)
    # profile_banner_url no longer provided by Twitter
    # try:
    #     if positive_value_exists(twitter_dict.get('profile_banner_url')):
    #         # Dec 2019, https://developer.twitter.com/en/docs/accounts-and-users/user-profile-images-and-banners
    #         banner = twitter_dict.get('profile_banner_url') + '/1500x500'
    #         twitter_dict['profile_banner_url'] = banner
    # except Exception as e:
    #     status += "FAILED_PROFILE_BANNER_URL: " + str(e) + " "

    results = {
        'status':                               status,
        'success':                              success,
        'twitter_handle':                       twitter_handle,
        'twitter_handle_found':                 twitter_handle_found,
        'twitter_dict':                         twitter_dict,
        'twitter_user_id':                      twitter_user_id,
        'twitter_user_not_found_in_twitter':    twitter_user_not_found_in_twitter,
        'twitter_user_suspended_by_twitter':    twitter_user_suspended_by_twitter,
    }
    return results


def retrieve_twitter_user_info_from_handles_list(
        twitter_handles_list=None,
        google_civic_api_counter_manager=None,
        parent=""):
    success = True
    status = ""
    counter = None
    twitter_response_dict_list = []
    retrieve_from_twitter = len(twitter_handles_list) > 0
    twitter_handles_not_found_list = []
    twitter_handles_suspended_list = []

    if retrieve_from_twitter:
        try:
            print("tweepy client init in retrieve_twitter_user_info_from_handles_list")
            client = tweepy.Client(
                bearer_token=TWITTER_BEARER_TOKEN,
                consumer_key=TWITTER_CONSUMER_KEY,
                consumer_secret=TWITTER_CONSUMER_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)

            # Use Twitter API call counter to track the number of queries we are doing each day
            # if hasattr(google_civic_api_counter_manager, 'create_counter_entry'):
            #     google_civic_api_counter_manager.create_counter_entry('get_users')

            counter = create_detailed_counter_entry(
                'get_users', 'retrieve_twitter_user_info_from_handles_list', success,
                {'text': "".join(twitter_handles_list)})
            print("tweepy client get_users in retrieve_twitter_user_info_from_handles_list")
            twitter_response = client.get_users(
                usernames=twitter_handles_list,
                user_fields=[
                    'description',
                    'entities',
                    'id',
                    'location',
                    'name',
                    'profile_image_url',
                    'public_metrics',
                    'username',
                    'verified',
                    'verified_type',
                    'withheld',
                ])
            if hasattr(twitter_response, 'data'):
                if twitter_response.data is None:
                    status += "TWITTER_RESPONSE_HAS_NO_DATA: " + str(twitter_response) + " "
                    success = False
                    if hasattr(twitter_response, 'errors'):
                        # TODO: return these handles as having problems so we can stop trying to retrieve them
                        # errors = [{'value': 'conklinforpa',
                        #            'detail': 'Could not find user with usernames: [conklinforpa].',
                        #            'title': 'Not Found Error', 'resource_type': 'user', 'parameter': 'usernames',
                        #            'resource_id': 'conklinforpa',
                        #            'type': 'https://api.twitter.com/2/problems/resource-not-found'},
                        #           {'value': 'ronigreenfor190',
                        #            'detail': 'Could not find user with usernames: [ronigreenfor190].',
                        #            'title': 'Not Found Error', 'resource_type': 'user', 'parameter': 'usernames',
                        #            'resource_id': 'ronigreenfor190',
                        #            'type': 'https://api.twitter.com/2/problems/resource-not-found'}]
                        for error_result in twitter_response.errors:
                            if error_result['resource_type'] == 'user':
                                if positive_value_exists(error_result['value']) \
                                        and error_result['title'] in ['Forbidden']:
                                    if error_result['value'] not in twitter_handles_suspended_list:
                                        twitter_handles_suspended_list.append(error_result['value'])
                                if positive_value_exists(error_result['value']) \
                                        and error_result['title'] in ['Not Found Error']:
                                    if error_result['value'] not in twitter_handles_not_found_list:
                                        twitter_handles_not_found_list.append(error_result['value'])
                else:
                    status += "TWITTER_RESPONSE_HAS_DATA "
                    twitter_response_object_list = twitter_response.data
                    for twitter_user in twitter_response_object_list:
                        try:
                            if twitter_user is None:
                                status += "TWITTER_USER_EQUALS_NONE "
                            elif hasattr(twitter_user, 'data'):
                                twitter_dict = convert_twitter_user_object_data_to_we_vote_dict(twitter_user.data)
                                twitter_dict = expand_twitter_entities(twitter_dict)
                                twitter_dict = expand_twitter_public_metrics(twitter_dict)
                                twitter_response_dict_list.append(twitter_dict)
                            else:
                                status += "HAS_NO_DATA: " + str(twitter_user) + " "
                        except Exception as e:
                            status += "PROBLEM_LOOPING_THROUGH_TWITTER_RESPONSE: " + str(e) + " "
            else:
                status += "TWITTER_RESPONSE_HAS_NO_DATA_FIELD "
        except tweepy.TooManyRequests as rate_limit_error:
            success = False
            status += 'TWITTER_RATE_LIMIT_ERROR: ' + str(rate_limit_error) + " "
            mark_detailed_counter_entry(counter, success, status)

        except Exception as e:
            status += "PROBLEM_RETRIEVING_TWITTER_DETAILS: " + str(e) + " "
            success = False

    twitter_response_list_retrieved = len(twitter_response_dict_list) > 0
    results = {
        'success':                          success,
        'status':                           status,
        'twitter_handles_not_found_list':   twitter_handles_not_found_list,
        'twitter_handles_suspended_list':   twitter_handles_suspended_list,
        'twitter_response_list':            twitter_response_dict_list,
        'twitter_response_list_retrieved':  twitter_response_list_retrieved,
    }
    return results
