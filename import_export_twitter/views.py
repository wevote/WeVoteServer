# import_export_twitter/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/views.py for routines that manage internal twitter data

from config.base import get_environment_variable
from django.http import HttpResponseRedirect
import tweepy
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists

TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")


def process_sign_in_response_view(request):
    oauth_token = request.GET.get('oauth_token', '')
    oauth_verifier = request.GET.get('oauth_verifier', '')

    if not positive_value_exists(oauth_token) or not positive_value_exists(oauth_verifier):
        # Redirect back to ReactJS so we can display failure message
        return HttpResponseRedirect('http://localhost:3001/twitter/missing_variables')  # TODO Convert to env variable

    voter_manager = VoterManager()
    # Look in the Voter table for a matching request_token, placed by the API endpoint twitterSignInStart
    results = voter_manager.retrieve_voter_by_twitter_request_token(oauth_token)

    if not results['voter_found']:
        # Redirect back to ReactJS so we can display failure message if the token wasn't found
        return HttpResponseRedirect('http://localhost:3001/twitter/token_missing')  # TODO Convert to env variable

    voter = results['voter']

    # Fetch the access token
    try:
        # Set up a tweepy auth handler
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.request_token = {'oauth_token': voter.twitter_request_token,
                              'oauth_token_secret': voter.twitter_request_secret}
        auth.get_access_token(oauth_verifier)

        if not positive_value_exists(auth.access_token) or not positive_value_exists(auth.access_token_secret):
            # Redirect back with error
            return HttpResponseRedirect('http://localhost:3001/twitter/access_token_missing')  # TODO Convert to env var

        voter.twitter_access_token = auth.access_token
        voter.twitter_access_secret = auth.access_token_secret
        voter.save()

        # Next use the access_token and access_secret to retrieve Twitter user info
        api = tweepy.API(auth)
        tweepy_user_object = api.me()

        voter_manager.save_twitter_user_values(voter, tweepy_user_object)

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

    # Redirect back, success
    return HttpResponseRedirect('http://localhost:3001/ballot')  # TODO Convert to env var
