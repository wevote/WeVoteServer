# twitter/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from exception.models import handle_exception
import tweepy
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

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

def retrieve_twitter_user_info(twitter_user_id, twitter_handle=''):
    status = ""
    twitter_user_not_found_in_twitter = False
    twitter_user_suspended_by_twitter = False
    write_to_server_logs = False
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)

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
    twitter_json = []
    try:
        if positive_value_exists(twitter_user_id):
            twitter_user = api.get_user(user_id=twitter_user_id)
            twitter_json = twitter_user._json
            success = True
            status += 'TWITTER_RETRIEVE_SUCCESSFUL-TWITTER_USER_ID ' + str(twitter_user_id) + " "
            twitter_handle_found = True
        elif positive_value_exists(twitter_handle):
            twitter_user = api.get_user(screen_name=twitter_handle)
            twitter_json = twitter_user._json
            success = True
            status += 'TWITTER_RETRIEVE_SUCCESSFUL-TWITTER_HANDLE ' + str(twitter_handle) + " "
            twitter_handle_found = True
            twitter_user_id = twitter_user.id  # Integer value. id_str would be the String value
        else:
            twitter_json = {}
            success = False
            status += 'TWITTER_RETRIEVE_NOT_SUCCESSFUL-MISSING_VARIABLE '
            twitter_handle_found = False
    except tweepy.RateLimitError as rate_limit_error:
        success = False
        status += 'TWITTER_RATE_LIMIT_ERROR '
        handle_exception(rate_limit_error, logger=logger, exception_message=status)
    except tweepy.error.TweepError as error_instance:
        success = False
        status += twitter_handle + " " if positive_value_exists(twitter_handle) else ""
        status += str(twitter_user_id) + " " if positive_value_exists(twitter_user_id) else " "
        status += str(error_instance) + " "
        if hasattr(error_instance, 'args'):
            try:
                error_tuple = error_instance.args
                for error_dict in error_tuple:
                    for one_error in error_dict:
                        status += '[' + one_error['message'] + '] '
                        if one_error['message'] in TWITTER_USER_NOT_FOUND_LOG_RESPONSES:
                            twitter_user_not_found_in_twitter = True
                        elif one_error['message'] in TWITTER_USER_SUSPENDED_LOG_RESPONSES:
                            twitter_user_suspended_by_twitter = True
                        else:
                            write_to_server_logs = True
            except Exception as e:
                status += "PROBLEM_PARSING_TWEEP_ERROR: " + str(e) + " "
                write_to_server_logs = True
        else:
            write_to_server_logs = True
        if write_to_server_logs:
            handle_exception(error_instance, logger=logger, exception_message=status)

    try:
        if positive_value_exists(twitter_json.get('profile_banner_url')):
            # Dec 2019, https://developer.twitter.com/en/docs/accounts-and-users/user-profile-images-and-banners
            banner = twitter_json.get('profile_banner_url') + '/1500x500'
            twitter_json['profile_banner_url'] = banner
    except Exception as e:
        status += "FAILED_PROFILE_BANNER_URL: " + str(e) + " "

    results = {
        'status':                               status,
        'success':                              success,
        'twitter_handle':                       twitter_handle,
        'twitter_handle_found':                 twitter_handle_found,
        'twitter_json':                         twitter_json,
        'twitter_user_id':                      twitter_user_id,
        'twitter_user_not_found_in_twitter':    twitter_user_not_found_in_twitter,
        'twitter_user_suspended_by_twitter':    twitter_user_suspended_by_twitter,
    }
    return results
