# wevote_social/utils.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib.auth import logout
from social.apps.django_app.views import _do_login
from voter.models import Voter, VoterManager
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def authenticate_associate_by_email(**kwargs):
    try:
        # Find the voter account that actually matches this twitter_id
        twitter_id = kwargs['uid']
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_twitter_id(twitter_id)
        if results['voter_found']:
            kwargs['user'] = results['voter']
        else:
            kwargs['user'] = None
    except:
        pass
    return kwargs


# We replace the default social_user pipeline entry so we can switch to an existing account:
# http://www.scriptscoop.net/t/08c148b90d9a/python-authalreadyassociated-exception-in-django-social-auth.html (jacob)
def social_user(backend, uid, details, user=None, *args, **kwargs):
    voter_manager = VoterManager()
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)

    if backend.name == 'twitter':
        # Twitter: Check to see if we have a voter with a matching twitter_id
        local_user_matches = user and user.twitter_id == uid
    else:
        local_user_matches = user and user.email != details.get('email')
    switch_user = not local_user_matches
    if switch_user:
        # Logout the current Django user
        logout(backend.strategy.request)

        user = None

        voter_that_matches_auth = None
        voter_found_that_matches_auth = False
        if social:
            if social.user:
                if backend.name == 'twitter':
                    if social.user.twitter_id == uid:
                        voter_that_matches_auth = social.user
                        voter_found_that_matches_auth = True
                    else:
                        pass

        if not voter_found_that_matches_auth:
            # Find the voter account that actually matches this twitter_id
            results = voter_manager.retrieve_voter_by_twitter_id(uid)
            if results['voter_found']:
                voter_that_matches_auth = results['voter']
                voter_found_that_matches_auth = True

        if voter_found_that_matches_auth:
            user = voter_that_matches_auth
        else:
            # No other account matches this, so we want to save basic information in social.user
            if backend.name == 'twitter':
                if social and social.user:
                    twitter_user_dict = {
                        'id': uid,
                        'profile_image_url_https': kwargs['response']['profile_image_url_https'],
                        'screen_name': kwargs['response']['screen_name']
                    }
                    results = voter_manager.save_twitter_user_values_from_dict(social.user, twitter_user_dict)
                    if results['success']:
                        social.user = results['voter']

    return {'social': social,
            'user': user,
            'is_new': user is None,
            'switch_user': True,
            'new_association': False}

# DATA FROM TWITTER SIGN IN
# access_token = {dict} {'screen_name': 'WeVoteUSA', 'user_id': '2860808066', 'x_auth_expires': '0',
# 'oauth_token': '2860808066-OYDIwFb8YTDg3tHcdWw8tkJc6ZnzZu5pzZ7zClt',
# 'oauth_token_secret': 'mOzin2QWoVk886JZdaWUxteMvTjpNo6L0qE489R5xQJcu'}
#  __len__ = {int} 5
#  'oauth_token' (4426310384) = {str} '2860808066-OYDIwFb8YTDg3tHcdWw8tkJc6ZnzZu5pzZ7zClt'
#  'oauth_token_secret' (4426305728) = {str} 'mOzin2QWoVk886JZdaWUxteMvTjpNo6L0qE489R5xQJcu'
#  'screen_name' (4426310256) = {str} 'WeVoteUSA'
#  'user_id' (4426263944) = {str} '2860808066'
#  'x_auth_expires' (4426310448) = {str} '0'
# extra_data = {dict} {'id': 2860808066, 'access_token': {'screen_name': 'WeVoteUSA', 'user_id': '2860808066',
# 'x_auth_expires': '0', 'oauth_token': '2860808066-OYDIwFb8YTDg3tHcdWw8tkJc6ZnzZu5pzZ7zClt',
# 'oauth_token_secret': 'mOzin2QWoVk886JZdaWUxteMvTjpNo6L0qE489R5xQJcu'}}
#  __len__ = {int} 2
#  'access_token' (4426310064) = {dict} {'screen_name': 'WeVoteUSA', 'user_id': '2860808066', 'x_auth_expires': '0',
# 'oauth_token': '2860808066-OYDIwFb8YTDg3tHcdWw8tkJc6ZnzZu5pzZ7zClt',
# 'oauth_token_secret': 'mOzin2QWoVk886JZdaWUxteMvTjpNo6L0qE489R5xQJcu'}
#   __len__ = {int} 5
#   'oauth_token' (4426310384) = {str} '2860808066-OYDIwFb8YTDg3tHcdWw8tkJc6ZnzZu5pzZ7zClt'
#   'oauth_token_secret' (4426305728) = {str} 'mOzin2QWoVk886JZdaWUxteMvTjpNo6L0qE489R5xQJcu'
#   'screen_name' (4426310256) = {str} 'WeVoteUSA'
#   'user_id' (4426263944) = {str} '2860808066'
#   'x_auth_expires' (4426310448) = {str} '0'
#  'id' (4426263888) = {int} 2860808066


def switch_user(backend, switch_user=False, user=None, social=None, *args, **kwargs):

    if switch_user and social:
        logger.warn('[authplus.social_pipeline.switch_user] switch to user %s' % user.email)

        # Do we have a voter who's twitter_id matches the incoming user_id?
        # Is social.user_id the Twitter id?

        #
        # social.actions.do_complete will not login second user because of prior user, so we'll do it here.
        #
        user.social_user = social
        user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
        _do_login(backend, user, social)
        # store last login backend name in session
        backend.strategy.session_set('social_auth_last_login_backend', social.provider)
