# wevote_social/utils.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib.auth import logout
# from social.apps.django_app.views import _do_login
from social_django.views import _do_login

from image.controllers import TWITTER, cache_master_and_resized_image
from import_export_facebook.models import FacebookManager
from twitter.models import TwitterUserManager
from voter.models import Voter, VoterManager
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def authenticate_associate_by_email(**kwargs):
    voter_manager = VoterManager()
    results = {'voter_found': False}
    try:
        # Find the voter account that actually matches this twitter_id
        if kwargs['backend'].name == "twitter":
            twitter_id = kwargs['uid']
            results = voter_manager.retrieve_voter_by_twitter_id(twitter_id)
        elif kwargs['backend'].name == 'facebook':
            facebook_id = kwargs['uid']
            # results = voter_manager.retrieve_voter_by_facebook_id_old(facebook_id)
            results = voter_manager.retrieve_voter_by_facebook_id(facebook_id)
        if results['voter_found']:
            kwargs['user'] = results['voter']
        else:
            kwargs['user'] = None
    except:
        pass
    return kwargs


# We replace the default social_user pipeline entry so we can switch to an existing account:
def social_user(backend, uid, details, user=None, *args, **kwargs):
    """
    Handles:
    socialcomplete/facebook
    socialcomplete/twitter
    :param backend:
    :param uid:
    :param details:
    :param user:
    :param args:
    :param kwargs:
    :return:
    """
    twitter_user_manager = TwitterUserManager()
    facebook_user_manager = FacebookManager()
    voter_manager = VoterManager()
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)

    if backend.name == 'twitter':
        # Twitter: Check to see if we have a voter with a matching twitter_id
        results = voter_manager.retrieve_voter_by_twitter_id(uid)
        if results['voter_found']:
            user = results['voter']
            local_user_matches = True
        else:
            local_user_matches = False
        # Was this:
        # local_user_matches = user and user.twitter_id == uid
    elif backend.name == 'facebook':
        # Facebook: Check to see if we have a voter with a matching facebook_id
        # results = voter_manager.retrieve_voter_by_facebook_id_old(uid)
        results = voter_manager.retrieve_voter_by_facebook_id(uid)
        if results['voter_found']:
            user = results['voter']
            local_user_matches = True
        else:
            local_user_matches = False
        # Was this:
        # local_user_matches = user and user.facebook_id == uid
    else:
        local_user_matches = user and user.email != details.get('email')
    switch_user = not local_user_matches
    if switch_user:
        # When logging into the Admin site we don't have to worry about merging current data with Twitter account
        # Logout the current Django user
        logout(backend.strategy.request)

        user = None

        voter_that_matches_auth = None
        voter_found_that_matches_auth = False
        if social:
            if social.user:
                if backend.name == 'twitter':
                    # if social.user.we_vote_id = owner_of_twitter_id_voter_we_vote_id
                    if social.user.twitter_id == uid:
                        voter_that_matches_auth = social.user
                        voter_found_that_matches_auth = True
                    else:
                        pass
                elif backend.name == 'facebook':
                    # if social.user.we_vote_id = owner_of_facebook_id_voter_we_vote_id
                    if social.user.facebook_id == uid:
                        voter_that_matches_auth = social.user
                        voter_found_that_matches_auth = True
                    else:
                        pass

        if not voter_found_that_matches_auth:
            if backend.name == 'twitter':
                # Find the voter account that actually matches this twitter_id
                results = voter_manager.retrieve_voter_by_twitter_id(uid)
                if results['voter_found']:
                    voter_that_matches_auth = results['voter']
                    voter_found_that_matches_auth = True
            elif backend.name == 'facebook':
                # Find the voter account that actually matches this facebook_id
                # results = voter_manager.retrieve_voter_by_facebook_id_old(uid)
                results = voter_manager.retrieve_voter_by_facebook_id(uid)
                if results['voter_found']:
                    voter_that_matches_auth = results['voter']
                    voter_found_that_matches_auth = True

        if voter_found_that_matches_auth:
            user = voter_that_matches_auth
        else:
            # No other account matches this, so we want to save basic information in social.user
            if backend.name == 'twitter':
                if social and social.user:
                    if user is None:
                        user = social.user
                    twitter_user_dict = {
                        'id': uid,
                        'profile_image_url_https': kwargs['response']['profile_image_url_https'],
                        'screen_name': kwargs['response']['screen_name']
                    }
                    if hasattr(user, 'we_vote_id'):
                        # Cache original and resized images
                        cache_results = cache_master_and_resized_image(
                            voter_we_vote_id=user.we_vote_id,
                            twitter_id=twitter_user_dict['id'],
                            twitter_screen_name=twitter_user_dict['screen_name'],
                            twitter_profile_image_url_https=twitter_user_dict['profile_image_url_https'],
                            image_source=TWITTER)
                        cached_twitter_profile_image_url_https = cache_results['cached_twitter_profile_image_url_https']
                        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
                        we_vote_hosted_profile_image_url_medium = \
                            cache_results['we_vote_hosted_profile_image_url_medium']
                        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
                    else:
                        cached_twitter_profile_image_url_https = ""
                        we_vote_hosted_profile_image_url_large = ""
                        we_vote_hosted_profile_image_url_medium = ""
                        we_vote_hosted_profile_image_url_tiny = ""

                    results = voter_manager.save_twitter_user_values_from_dict(
                        social.user, twitter_user_dict, cached_twitter_profile_image_url_https,
                        we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny)
                    if results['success']:
                        social.user = results['voter']
                        user = results['voter']
                        twitter_link_results = twitter_user_manager.create_twitter_link_to_voter(uid, user.we_vote_id)
            elif backend.name == 'facebook':
                if social and social.user:
                    if user is None:
                        user = social.user
                    facebook_user_dict = {
                        'id':           uid,
                        'fb_username':  social.user.fb_username
                    }

                    results = voter_manager.save_facebook_user_values_from_dict(
                        social.user, facebook_user_dict)
                    if results['success']:
                        social.user = results['voter']
                        user = results['voter']
                        facebook_link_results = facebook_user_manager.create_facebook_link_to_voter(uid,
                                                                                                    user.we_vote_id)

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
        logger.warning('[authplus.social_pipeline.switch_user] switch to user %s' % user.email)

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
