# import_export_twitter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from wevote_functions.functions import positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


# See also WeVoteServer/twitter/models.py for routines that manage internal twitter data

# https://dev.twitter.com/overview/api/users

# https://dev.twitter.com/overview/general/user-profile-images-and-banners
# Variant	Dimensions	Example URL
# normal	48px by 48px	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png
# bigger	73px by 73px	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_bigger.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_bigger.png
# mini	24px by 24px	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_mini.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_mini.png
# original	original	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3.png
# Omit the underscore and variant to retrieve the original image. The images can be very large.


class TwitterAuthResponse(models.Model):
    """
    This is the authResponse data from a Twitter authentication
    """
    voter_device_id = models.CharField(
        verbose_name="voter_device_id initiating Twitter Auth", max_length=255, null=False, blank=False, unique=True)
    datetime_of_authorization = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)

    # Twitter session information
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, blank=True)
    twitter_screen_name = models.CharField(verbose_name='twitter screen name / handle',
                                           max_length=255, null=True, unique=False)
    twitter_name = models.CharField(verbose_name="display name from twitter", max_length=255, null=True, blank=True)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)

    twitter_request_token = models.TextField(verbose_name='twitter request token', null=True, blank=True)
    twitter_request_secret = models.TextField(verbose_name='twitter request secret', null=True, blank=True)
    twitter_access_token = models.TextField(verbose_name='twitter access token', null=True, blank=True)
    twitter_access_secret = models.TextField(verbose_name='twitter access secret', null=True, blank=True)


class TwitterAuthManager(models.Model):
    def __unicode__(self):
        return "TwitterAuthManager"

    def update_or_create_twitter_auth_response(self, voter_device_id, twitter_id=0, twitter_screen_name='',
                                               twitter_profile_image_url_https='', twitter_request_token='',
                                               twitter_request_secret='', twitter_access_token='',
                                               twitter_access_secret=''):

        defaults = {
            "voter_device_id": voter_device_id,
        }
        if positive_value_exists(twitter_id):
            defaults["twitter_id"] = twitter_id
        if positive_value_exists(twitter_screen_name):
            defaults["twitter_screen_name"] = twitter_screen_name
        if positive_value_exists(twitter_profile_image_url_https):
            defaults["twitter_profile_image_url_https"] = twitter_profile_image_url_https
        if positive_value_exists(twitter_request_token):
            defaults["twitter_request_token"] = twitter_request_token
        if positive_value_exists(twitter_request_secret):
            defaults["twitter_request_secret"] = twitter_request_secret
        if positive_value_exists(twitter_access_token):
            defaults["twitter_access_token"] = twitter_access_token
        if positive_value_exists(twitter_access_secret):
            defaults["twitter_access_secret"] = twitter_access_secret

        try:
            twitter_auth_response, created = TwitterAuthResponse.objects.update_or_create(
                voter_device_id__iexact=voter_device_id,
                defaults=defaults,
            )
            twitter_auth_response_saved = True
            success = True
            status = "TWITTER_AUTH_RESPONSE_UPDATED_OR_CREATED"
        except Exception as e:
            twitter_auth_response_saved = False
            twitter_auth_response = TwitterAuthResponse()
            success = False
            created = False
            status = "TWITTER_AUTH_RESPONSE_NOT_UPDATED_OR_CREATED"

        results = {
            'success': success,
            'status': status,
            'twitter_auth_response_saved': twitter_auth_response_saved,
            'twitter_auth_response_created': created,
            'twitter_auth_response': twitter_auth_response,
        }
        return results

    def retrieve_twitter_auth_response(self, voter_device_id):
        """

        :param voter_device_id:
        :return:
        """
        twitter_auth_response = TwitterAuthResponse()
        twitter_auth_response_id = 0

        try:
            if positive_value_exists(voter_device_id):
                twitter_auth_response = TwitterAuthResponse.objects.get(
                    voter_device_id__iexact=voter_device_id,
                )
                twitter_auth_response_id = twitter_auth_response.id
                twitter_auth_response_found = True
                success = True
                status = "RETRIEVE_TWITTER_AUTH_RESPONSE_FOUND_BY_VOTER_DEVICE_ID"
            else:
                twitter_auth_response_found = False
                success = False
                status = "RETRIEVE_TWITTER_AUTH_RESPONSE_VARIABLES_MISSING"
        except TwitterAuthResponse.DoesNotExist:
            twitter_auth_response_found = False
            success = True
            status = "RETRIEVE_TWITTER_AUTH_RESPONSE_NOT_FOUND"
        except Exception as e:
            twitter_auth_response_found = False
            success = False
            status = 'FAILED retrieve_twitter_auth_response'

        results = {
            'success': success,
            'status': status,
            'twitter_auth_response_found': twitter_auth_response_found,
            'twitter_auth_response_id': twitter_auth_response_id,
            'twitter_auth_response': twitter_auth_response,
        }
        return results

    @staticmethod
    def save_twitter_auth_values(twitter_auth_response, twitter_user_object):
        """
        This is used to store the cached values in the TwitterAuthResponse record during authentication.
        Please also see voter/models.py VoterManager->save_twitter_user_values

        :param twitter_auth_response:
        :param twitter_user_object:
        :return:
        """
        try:
            twitter_auth_value_to_save = False
            if hasattr(twitter_user_object, "id") and positive_value_exists(twitter_user_object.id):
                twitter_auth_response.twitter_id = twitter_user_object.id
                twitter_auth_value_to_save = True
            # 'id_str': '132728535',
            # 'utc_offset': 32400,
            # 'description': "Cars, Musics, Games, Electronics, toys, food, etc... I'm just a typical boy!",
            # 'profile_image_url': 'http://a1.twimg.com/profile_images/1213351752/_2_2__normal.jpg',
            if hasattr(twitter_user_object, "profile_image_url_https") and \
                    positive_value_exists(twitter_user_object.profile_image_url_https):
                twitter_auth_response.twitter_profile_image_url_https = twitter_user_object.profile_image_url_https
                twitter_auth_value_to_save = True
            # 'profile_background_image_url': 'http://a2.twimg.com/a/1294785484/images/themes/theme15/bg.png',
            if hasattr(twitter_user_object, "screen_name") and positive_value_exists(twitter_user_object.screen_name):
                twitter_auth_response.twitter_screen_name = twitter_user_object.screen_name
                twitter_auth_value_to_save = True
            # 'lang': 'en',
            if hasattr(twitter_user_object, "name") and positive_value_exists(twitter_user_object.name):
                twitter_auth_response.twitter_name = twitter_user_object.name
                twitter_auth_value_to_save = True
            # 'url': 'http://www.carbonize.co.kr',
            # 'time_zone': 'Seoul',
            if hasattr(twitter_user_object, "profile_banner_url") and \
                    positive_value_exists(twitter_user_object.profile_banner_url):
                twitter_auth_response.profile_banner_url = twitter_user_object.profile_banner_url
                twitter_auth_value_to_save = True
            if twitter_auth_value_to_save:
                twitter_auth_response.save()
            success = True
            status = "SAVED_TWITTER_AUTH_VALUES"
        except Exception as e:
            status = "UNABLE_TO_SAVE_TWITTER_AUTH_VALUES"
            logger.error("save_twitter_auth_values threw " + str(e))
            success = False

        results = {
            'status':                   status,
            'success':                  success,
            'twitter_auth_response':    twitter_auth_response,
        }
        return results
