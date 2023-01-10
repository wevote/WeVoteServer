# import_export_facebook/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import re

import facebook
import requests
from django.core.validators import RegexValidator
from django.db import models

import wevote_functions.admin
from config.base import get_environment_variable_default
from email_outbound.models import SEND_STATUS_CHOICES, TO_BE_PROCESSED
from exception.models import handle_exception, print_to_log
from wevote_functions.functions import generate_random_string, positive_value_exists, convert_to_int

logger = wevote_functions.admin.get_logger(__name__)

FRIEND_INVITATION_FACEBOOK_TEMPLATE = 'FRIEND_INVITATION_FACEBOOK_TEMPLATE'
GENERIC_EMAIL_FACEBOOK_TEMPLATE = 'GENERIC_EMAIL_FACEBOOK_TEMPLATE'
KIND_OF_FACEBOOK_TEMPLATE_CHOICES = (
    (GENERIC_EMAIL_FACEBOOK_TEMPLATE,  'Generic Email'),
    (FRIEND_INVITATION_FACEBOOK_TEMPLATE, 'Invite Friend'),
)


class FacebookAuthResponse(models.Model):
    """
    This is the authResponse data from a Facebook authentication
    """
    objects = None
    DoesNotExist = None
    voter_device_id = models.CharField(
        verbose_name="voter_device_id initiating Facebook Auth", max_length=255, null=False, blank=False, unique=True)
    datetime_of_authorization = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)

    # Comes from Facebook authResponse FACEBOOK_LOGGED_IN
    facebook_access_token = models.CharField(
        verbose_name="accessToken from Facebook", max_length=512, null=True, blank=True, unique=False)
    facebook_expires_in = models.IntegerField(verbose_name="expiresIn from Facebook", null=True, blank=True)
    facebook_signed_request = models.TextField(verbose_name="signedRequest from Facebook", null=True, blank=True)
    facebook_user_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)

    # Comes from FACEBOOK_RECEIVED_DATA
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    facebook_first_name = models.CharField(
        verbose_name="first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_middle_name = models.CharField(
        verbose_name="first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_last_name = models.CharField(
        verbose_name="first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_profile_image_url_https = models.URLField(
        verbose_name='url of voter&apos;s image from facebook', blank=True, null=True)
    facebook_background_image_url_https = models.URLField(
        verbose_name='url of voter&apos;s background &apos;cover&apos; image from facebook \
        (like the twitter banner photo)', blank=True, null=True)
    facebook_background_image_offset_x = models.IntegerField(verbose_name="x offset of facebook cover image", default=0,
                                                             null=True, blank=True)
    facebook_background_image_offset_y = models.IntegerField(verbose_name="y offset of facebook cover image", default=0,
                                                             null=True, blank=True)

    def get_full_name(self):
        full_name = self.facebook_first_name if positive_value_exists(self.facebook_first_name) else ''
        full_name += " " if positive_value_exists(self.facebook_first_name) \
            and positive_value_exists(self.facebook_last_name) else ''
        full_name += self.facebook_last_name if positive_value_exists(self.facebook_last_name) else ''

        if not positive_value_exists(full_name) and positive_value_exists(self.facebook_email):
            full_name = self.email.split("@", 1)[0]

        return full_name


class FacebookLinkToVoter(models.Model):
    """
    This is the link between a Facebook account and a We Vote voter account
    """
    DoesNotExist = None
    objects = None
    voter_we_vote_id = models.CharField(verbose_name="we vote id for the email owner", max_length=255, unique=True)
    facebook_user_id = models.BigIntegerField(verbose_name="facebook big integer id", null=False, unique=True)
    secret_key = models.CharField(
        verbose_name="secret key to verify ownership facebook account", max_length=255, null=False, unique=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=False, auto_now=True)


class FacebookMessageOutboundDescription(models.Model):
    """
    A description of the Facebook direct message we want to send.
    """
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

    kind_of_send_template = models.CharField(max_length=50, choices=KIND_OF_FACEBOOK_TEMPLATE_CHOICES,
                                             default=GENERIC_EMAIL_FACEBOOK_TEMPLATE)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    recipient_facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    recipient_facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                                 null=True, blank=True)
    recipient_fb_username = models.CharField(unique=True, max_length=50, validators=[alphanumeric], null=True)
    send_status = models.CharField(max_length=50, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)


class FacebookUser(models.Model):
    """
    My facebook friends details, from the perspective of facebook id of me
    """
    DoesNotExist = None
    objects = None
    facebook_user_id = models.BigIntegerField(verbose_name="facebook id of user", null=False, unique=False)
    facebook_user_name = models.CharField(
        verbose_name="User name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_user_first_name = models.CharField(
        verbose_name="User's first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_user_middle_name = models.CharField(
        verbose_name="User's middle_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    facebook_user_location_id = models.BigIntegerField(
        verbose_name="location id of Facebook user", null=True, unique=False)
    facebook_user_location_name = models.CharField(
        verbose_name="User's location name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_user_gender = models.CharField(
        verbose_name="User's gender from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_user_birthday = models.CharField(
        verbose_name="User's birthday from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_user_last_name = models.CharField(
        verbose_name="User's last_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of voter image from facebook',
                                                       blank=True, null=True)
    facebook_background_image_url_https = models.URLField(verbose_name='url of cover image from facebook',
                                                          blank=True, null=True)
    facebook_background_image_offset_x = models.IntegerField(verbose_name="x offset of facebook cover image", default=0,
                                                             null=True, blank=True)
    facebook_background_image_offset_y = models.IntegerField(verbose_name="y offset of facebook cover image", default=0,
                                                             null=True, blank=True)
    we_vote_hosted_profile_image_url_large = models.URLField(verbose_name='we vote hosted large image url',
                                                             blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(verbose_name='we vote hosted medium image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(verbose_name='we vote hosted tiny image url',
                                                            blank=True, null=True)
    facebook_user_about = models.CharField(
        verbose_name="User's About from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_user_is_verified = models.BooleanField(
        verbose_name="User is verfired from Facebook", default=False)
    facebook_user_friend_total_count = models.BigIntegerField(
        verbose_name="total count of friends from facebook", null=True, unique=False)


class FacebookFriendsUsingWeVote(models.Model):
    """
    My facebook friends ids who are already using Wevote App, from the perspective of facebook id of me
    """
    DoesNotExist = None
    objects = None
    facebook_id_of_me = models.BigIntegerField(verbose_name="facebook id of viewer", null=False, unique=False)
    facebook_id_of_my_friend = models.BigIntegerField(verbose_name="facebook id of my friend", null=False, unique=False)


class FacebookManager(models.Manager):

    def __unicode__(self):
        return "FacebookManager"

    def create_facebook_link_to_voter(self, facebook_user_id, voter_we_vote_id):
        create_new_facebook_link = True
        facebook_link_to_voter = None
        facebook_link_to_voter_saved = False
        status = ""
        success = True

        if not positive_value_exists(facebook_user_id) or not positive_value_exists(voter_we_vote_id):
            status += "CREATE_FACEBOOK_LINK_MISSING_REQUIRED_VARIABLES "
            print_to_log(logger=logger, exception_message_optional=status)
            success = False
            results = {
                'success': success,
                'status': status,
                'facebook_link_to_voter_saved': facebook_link_to_voter_saved,
                'facebook_link_to_voter': facebook_link_to_voter,
            }
            return results

        # Does a link already exist?
        try:
            facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                facebook_user_id=facebook_user_id,
            )
            success = True
            status += "FACEBOOK_LINK_TO_VOTER_ALREADY_EXISTS "
            if voter_we_vote_id == facebook_link_to_voter.voter_we_vote_id:
                facebook_link_to_voter_saved = True
                create_new_facebook_link = False
                success = True
            else:
                # Write over existing voter_we_vote_id
                create_new_facebook_link = False
                try:
                    facebook_link_to_voter.voter_we_vote_id = voter_we_vote_id
                    facebook_link_to_voter.save()
                    success = True
                except Exception as e:
                    status += "FACEBOOK_LINK_TO_VOTER-UPDATE_VOTER_WE_VOTE_ID_FAILED (" + str(voter_we_vote_id) + ") "
                    handle_exception(e, logger=logger, exception_message=status)
                    success = False
        except FacebookAuthResponse.DoesNotExist:
            status += "EXISTING_FACEBOOK_LINK_TO_VOTER_DOES_NOT_EXIST "
        except Exception as e:
            status += "FACEBOOK_LINK_TO_VOTER-GET_FAILED "
            handle_exception(e, logger=logger, exception_message=status)

        # Any attempts to save a facebook_link using either facebook_user_id or voter_we_vote_id that already
        #  exist in the table will fail, since those fields are required to be unique.
        if create_new_facebook_link:
            facebook_secret_key = generate_random_string(12)

            try:
                facebook_link_to_voter = FacebookLinkToVoter.objects.create(
                    facebook_user_id=facebook_user_id,
                    voter_we_vote_id=voter_we_vote_id,
                    secret_key=facebook_secret_key,
                )
                facebook_link_to_voter_saved = True
                success = True
                status += "FACEBOOK_LINK_TO_VOTER_CREATED "
            except Exception as e:
                facebook_link_to_voter_saved = False
                facebook_link_to_voter = FacebookLinkToVoter()
                success = False
                status += "FACEBOOK_LINK_TO_VOTER_NOT_CREATED "
                handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                      success,
            'status':                       status,
            'facebook_link_to_voter_saved': facebook_link_to_voter_saved,
            'facebook_link_to_voter':       facebook_link_to_voter,
        }
        return results

    def delete_facebook_link_to_voter(self, voter_we_vote_id):
        success = False
        facebook_user_id = ""

        try:
            facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                voter_we_vote_id__iexact=voter_we_vote_id)
            facebook_user_id = facebook_link_to_voter.facebook_user_id
            facebook_link_to_voter.delete()
            success = positive_value_exists(facebook_user_id)
        except FacebookLinkToVoter.DoesNotExist:
            pass
        except Exception as e:
            handle_exception(e, logger=logger, exception_message="delete_facebook_link_to_voter")

        results = {
            'success':           success,
            'facebook_user_id':  facebook_user_id,
        }
        return results

    def update_or_create_facebook_auth_response(
            self, voter_device_id, facebook_access_token, facebook_user_id, facebook_expires_in,
            facebook_signed_request,
            facebook_email, facebook_first_name, facebook_middle_name, facebook_last_name,
            facebook_profile_image_url_https, facebook_background_image_url_https,
            facebook_background_image_offset_x, facebook_background_image_offset_y):
        """

        :param voter_device_id:
        :param facebook_access_token:
        :param facebook_user_id:
        :param facebook_expires_in:
        :param facebook_signed_request:
        :param facebook_email:
        :param facebook_first_name:
        :param facebook_middle_name:
        :param facebook_last_name:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :param facebook_background_image_offset_x:
        :param facebook_background_image_offset_y:
        :return:
        """

        defaults = {
            "voter_device_id": voter_device_id,
        }
        if positive_value_exists(facebook_access_token):
            defaults["facebook_access_token"] = facebook_access_token
        if positive_value_exists(facebook_user_id):
            defaults["facebook_user_id"] = facebook_user_id
        if positive_value_exists(facebook_expires_in):
            defaults["facebook_expires_in"] = facebook_expires_in
        if positive_value_exists(facebook_signed_request):
            defaults["facebook_signed_request"] = facebook_signed_request
        if positive_value_exists(facebook_email):
            defaults["facebook_email"] = facebook_email
        if positive_value_exists(facebook_first_name):
            defaults["facebook_first_name"] = facebook_first_name
        if positive_value_exists(facebook_middle_name):
            defaults["facebook_middle_name"] = facebook_middle_name
        if positive_value_exists(facebook_last_name):
            defaults["facebook_last_name"] = facebook_last_name
        if positive_value_exists(facebook_profile_image_url_https):
            defaults["facebook_profile_image_url_https"] = facebook_profile_image_url_https
        if positive_value_exists(facebook_background_image_url_https):
            defaults["facebook_background_image_url_https"] = facebook_background_image_url_https
            # A zero value for the offsets can be a valid value.  If we received an image, we also received the offsets.
            try:
                defaults["facebook_background_image_offset_x"] = int(facebook_background_image_offset_x)
            except Exception:
                defaults["facebook_background_image_offset_x"] = 0
            try:
                defaults["facebook_background_image_offset_y"] = int(facebook_background_image_offset_y)
            except Exception:
                defaults["facebook_background_image_offset_y"] = 0
        try:
            facebook_auth_response, created = FacebookAuthResponse.objects.update_or_create(
                voter_device_id__iexact=voter_device_id,
                defaults=defaults,
            )
            facebook_auth_response_saved = True
            success = True
            status = "FACEBOOK_AUTH_RESPONSE_UPDATED_OR_CREATED"
        except Exception as e:
            facebook_auth_response_saved = False
            facebook_auth_response = FacebookAuthResponse()
            success = False
            created = False
            status = "FACEBOOK_AUTH_RESPONSE_NOT_UPDATED_OR_CREATED"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success': success,
            'status': status,
            'facebook_auth_response_saved': facebook_auth_response_saved,
            'facebook_auth_response_created': created,
            'facebook_auth_response': facebook_auth_response,
        }
        return results


    def retrieve_facebook_auth_response_by_id(self, facebook_auth_response_id, read_only=False):
        facebook_auth_response_on_stage = FacebookAuthResponse.objects.get(id=facebook_auth_response_id)
        return facebook_auth_response_on_stage


    def delete_facebook_auth_responses(self, facebook_user_id):
        """
        Delete all facebookauthresponse rows that have this facebook_user_id
        :param facebook_user_id:
        :return:
        """

        facebook_auth_rows_deleted = 0
        try:
            facebook_auth_response = FacebookAuthResponse()
            facebook_auth_response = FacebookAuthResponse.objects.all()
            facebook_auth_response = facebook_auth_response.filter(facebook_user_id__exact=facebook_user_id)
            facebook_auth_response_list = list(facebook_auth_response)
            for one_facebook_auth_response in facebook_auth_response_list:
                logger.debug("DELETING one_facebook_auth_response " + str(one_facebook_auth_response.facebook_user_id))
                one_facebook_auth_response.delete()
                facebook_auth_rows_deleted = facebook_auth_rows_deleted + 1
            success = True
            status = " FACEBOOK_AUTH_RESPONSES_DELETED"
        except Exception as e:
            facebook_users_deleted = False
            success = False
            status = " FACEBOOK_AUTH_RESPONSES_NOT_DELETED"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success': success,
            'status': status,
            'facebook_auth_rows_deleted': facebook_auth_rows_deleted,
        }
        return results

    def update_or_create_facebook_friends_using_we_vote(self, facebook_id_of_me, facebook_id_of_my_friend):
        """
        We use this subroutine to create or update FacebookFriendsUsingWeVote table with my friends facebook id.
        :param facebook_id_of_me:
        :param facebook_id_of_my_friend:
        :return:
        """
        try:
            facebook_friends_using_we_vote, created = FacebookFriendsUsingWeVote.objects.update_or_create(
                facebook_id_of_me=facebook_id_of_me,
                facebook_id_of_my_friend=facebook_id_of_my_friend,
                defaults={
                    'facebook_id_of_me':        facebook_id_of_me,
                    'facebook_id_of_my_friend': facebook_id_of_my_friend
                }
            )
            facebook_friends_using_we_vote_saved = True
            success = True
            status = "FACEBOOK_FRIENDS_USING_WE_VOTE_CREATED"
        except Exception as e:
            facebook_friends_using_we_vote_saved = False
            facebook_friends_using_we_vote = FacebookFriendsUsingWeVote()
            success = False
            status = "FACEBOOK_FRIENDS_USING_WE_VOTE_CREATED"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                              success,
            'status':                               status,
            'facebook_friends_using_we_vote_saved': facebook_friends_using_we_vote_saved,
            'facebook_friends_using_we_vote':       facebook_friends_using_we_vote,
            }
        return results

    def update_or_create_facebook_user(self, facebook_user_id, facebook_user_first_name, facebook_user_middle_name,
                                       facebook_user_last_name, facebook_user_name=None, facebook_user_location_id=None,
                                       facebook_user_location_name=None, facebook_user_gender=None,
                                       facebook_user_birthday=None, facebook_profile_image_url_https=None,
                                       facebook_background_image_url_https=None, facebook_user_about=None,
                                       facebook_user_is_verified=False, facebook_user_friend_total_count=None,
                                       we_vote_hosted_profile_image_url_large=None,
                                       we_vote_hosted_profile_image_url_medium=None,
                                       we_vote_hosted_profile_image_url_tiny=None,
                                       facebook_email=None):
        """
        We use this subroutine to create or update FacebookUser table with my friends details.
        :param facebook_user_id:
        :param facebook_user_first_name:
        :param facebook_user_middle_name:
        :param facebook_user_last_name:
        :param facebook_user_name:
        :param facebook_user_location_id:
        :param facebook_user_location_name:
        :param facebook_user_gender:
        :param facebook_user_birthday:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :param facebook_user_about:
        :param facebook_user_is_verified:
        :param facebook_user_friend_total_count:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny:
        :param facebook_email:
        :return:
        """

        try:
            # for facebook_user_entry in facebook_users:
            facebook_user, created = FacebookUser.objects.update_or_create(
                facebook_user_id=facebook_user_id,
                defaults={
                    'facebook_user_id':                         facebook_user_id,
                    'facebook_user_name':                       facebook_user_name,
                    'facebook_user_first_name':                 facebook_user_first_name,
                    'facebook_user_middle_name':                facebook_user_middle_name,
                    'facebook_user_last_name':                  facebook_user_last_name,
                    'facebook_email':                           facebook_email,
                    'facebook_user_location_id':                facebook_user_location_id,
                    'facebook_user_location_name':              facebook_user_location_name,
                    'facebook_user_gender':                     facebook_user_gender,
                    'facebook_user_birthday':                   facebook_user_birthday,
                    'facebook_profile_image_url_https':         facebook_profile_image_url_https,
                    'facebook_background_image_url_https':      facebook_background_image_url_https,
                    'facebook_user_about':                      facebook_user_about,
                    'facebook_user_is_verified':                facebook_user_is_verified,
                    'facebook_user_friend_total_count':         facebook_user_friend_total_count,
                    'we_vote_hosted_profile_image_url_large':   we_vote_hosted_profile_image_url_large,
                    'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny
                }
            )
            facebook_user_saved = True
            success = True
            status = " FACEBOOK_USER_CREATED"
        except Exception as e:
            facebook_user_saved = False
            facebook_user = FacebookUser()
            success = False
            status = " FACEBOOK_USER_NOT_CREATED"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':              success,
            'status':               status,
            'facebook_user_saved':  facebook_user_saved,
            'facebook_user':        facebook_user,
            }
        return results

    def delete_facebook_users(self, facebook_user_id):
        """
        We use this subroutine to delete FacebookUser table row(s) with a specific facebook_user_id value.
        :param facebook_user_id:
        :return:
        """
        facebook_users_deleted = 0
        try:
            facebook_user = FacebookUser()
            facebook_user_query = FacebookUser.objects.all()
            facebook_user_query = facebook_user_query.filter(facebook_user_id__exact=facebook_user_id)

            facebook_user_list = list(facebook_user_query)
            for one_facebook_user in facebook_user_list:
                name = one_facebook_user.facebook_user_name
                if not name:
                    name = one_facebook_user.facebook_user_first_name
                if not name:
                    name = "Entry does not contain a name"

                logger.debug("DELETING one_facebook_user " + name)
                one_facebook_user.delete()
                facebook_users_deleted = facebook_users_deleted + 1
            success = True
            status = " FACEBOOK_USERS_DELETED"
        except Exception as e:
            facebook_users_deleted = False
            success = False
            status = " FACEBOOK_USERS_NOT_DELETED"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                 success,
            'status':                  status,
            'facebook_users_deleted':  facebook_users_deleted,
            }
        return results

    def reset_facebook_user_image_details(self, facebook_user_id, facebook_profile_image_url_https,
                                          facebook_background_image_url_https):
        """
         Reset an facebook user entry with original image details from we vote image.
        :param facebook_user_id:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :return:
        """
        success = False
        status = "ENTERING_RESET_FACEBOOK_USER_IMAGE_DETAILS"
        values_changed = False
        facebook_user_results = self.retrieve_facebook_user_by_facebook_user_id(facebook_user_id)
        facebook_user = facebook_user_results['facebook_user']
        if facebook_user_results['facebook_user_found']:
            if positive_value_exists(facebook_profile_image_url_https):
                facebook_user.facebook_profile_image_url_https = facebook_profile_image_url_https
                values_changed = True
            if positive_value_exists(facebook_background_image_url_https):
                facebook_user.facebook_background_image_url_https = facebook_background_image_url_https
                values_changed = True

            facebook_user.we_vote_hosted_profile_image_url_large = ''
            facebook_user.we_vote_hosted_profile_image_url_medium = ''
            facebook_user.we_vote_hosted_profile_image_url_tiny = ''

            if values_changed:
                facebook_user.save()
                success = True
                status = "RESET_FACEBOOK_USER_IMAGE_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_RESET_TO_FACEBOOK_USER_IMAGE_DETAILS"

        results = {
            'success':                  success,
            'status':                   status,
            'facebook_user':            facebook_user,
        }
        return results

    def update_facebook_user_details(self, facebook_user,
                                     cached_facebook_profile_image_url_https=False,
                                     cached_facebook_background_image_url_https=False,
                                     we_vote_hosted_profile_image_url_large=False,
                                     we_vote_hosted_profile_image_url_medium=False,
                                     we_vote_hosted_profile_image_url_tiny=False):
        """
        Update an facebook user entry with cached image urls
        :param facebook_user:
        :param cached_facebook_profile_image_url_https:
        :param cached_facebook_background_image_url_https:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny:
        :return:
        """

        success = False
        status = "ENTERING_UPDATE_FACEBOOK_USER_DETAILS"
        values_changed = False

        if facebook_user:
            if positive_value_exists(cached_facebook_profile_image_url_https):
                facebook_user.facebook_profile_image_url_https = cached_facebook_profile_image_url_https
                values_changed = True
            if positive_value_exists(cached_facebook_background_image_url_https):
                facebook_user.facebook_background_image_url_https = cached_facebook_background_image_url_https
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                facebook_user.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                facebook_user.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                facebook_user.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if values_changed:
                facebook_user.save()
                success = True
                status = "SAVED_FACEBOOK_USER_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_FACBOOK_USER_DETAILS"

        results = {
            'success':                  success,
            'status':                   status,
            'facebook_user':            facebook_user,
        }
        return results

    def retrieve_facebook_auth_response(self, voter_device_id):
        """

        :param voter_device_id:
        :return:
        """
        facebook_auth_response = FacebookAuthResponse()
        facebook_auth_response_id = 0

        try:
            if positive_value_exists(voter_device_id):
                facebook_auth_response = FacebookAuthResponse.objects.get(
                    voter_device_id__iexact=voter_device_id,
                )
                facebook_auth_response_id = facebook_auth_response.id
                facebook_auth_response_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_FOUND_BY_VOTER_DEVICE_ID "
            else:
                facebook_auth_response_found = False
                success = False
                status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_VARIABLES_MISSING "
        except FacebookAuthResponse.DoesNotExist:
            facebook_auth_response_found = False
            success = True
            status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_NOT_FOUND "
        except Exception as e:
            facebook_auth_response_found = False
            success = False
            status = 'FAILED retrieve_facebook_auth_response '
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success': success,
            'status': status,
            'facebook_auth_response_found': facebook_auth_response_found,
            'facebook_auth_response_id': facebook_auth_response_id,
            'facebook_auth_response': facebook_auth_response,
        }
        return results

    def retrieve_facebook_auth_response_from_facebook_id(self, facebook_user_id):
        """
        Retrieve facebook auth response from facebook user id
        :param facebook_user_id:
        :return:
        """
        facebook_auth_response = FacebookAuthResponse()
        facebook_auth_response_id = 0

        try:
            if positive_value_exists(facebook_user_id):
                facebook_auth_response = FacebookAuthResponse.objects.get(
                    facebook_user_id=facebook_user_id,
                )
                facebook_auth_response_id = facebook_auth_response.id
                facebook_auth_response_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_FOUND_BY_FACEBOOK_USER_ID "
            else:
                facebook_auth_response_found = False
                success = False
                status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_VARIABLES_MISSING "
        except FacebookAuthResponse.DoesNotExist:
            facebook_auth_response_found = False
            success = True
            status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_NOT_FOUND "
        except Exception as e:
            facebook_auth_response_found = False
            success = False
            status = 'FAILED retrieve_facebook_auth_response'
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                      success,
            'status':                       status,
            'facebook_auth_response_found': facebook_auth_response_found,
            'facebook_auth_response_id':    facebook_auth_response_id,
            'facebook_auth_response':       facebook_auth_response,
        }
        return results

    def fetch_facebook_id_from_voter_we_vote_id(self, voter_we_vote_id):
        facebook_user_id = 0
        facebook_results = self.retrieve_facebook_link_to_voter(facebook_user_id, voter_we_vote_id, read_only=True)
        if facebook_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_results['facebook_link_to_voter']
            facebook_user_id = facebook_link_to_voter.facebook_user_id
        return facebook_user_id

    def retrieve_facebook_link_to_voter_from_facebook_id(self, facebook_user_id, read_only=False):
        return self.retrieve_facebook_link_to_voter(facebook_user_id, read_only=read_only)

    def retrieve_facebook_link_to_voter_from_voter_we_vote_id(self, voter_we_vote_id, read_only=False):
        facebook_user_id = 0
        facebook_secret_key = ""
        return self.retrieve_facebook_link_to_voter(
            facebook_user_id, voter_we_vote_id, facebook_secret_key, read_only=read_only)

    def retrieve_facebook_link_to_voter_from_facebook_secret_key(self, facebook_secret_key, read_only=False):
        facebook_user_id = 0
        voter_we_vote_id = ""
        return self.retrieve_facebook_link_to_voter(
            facebook_user_id, voter_we_vote_id, facebook_secret_key, read_only=read_only)

    def retrieve_facebook_link_to_voter(
            self,
            facebook_user_id=0,
            voter_we_vote_id='',
            facebook_secret_key='',
            read_only=False,
        ):
        """

        :param facebook_user_id:
        :param voter_we_vote_id:
        :param facebook_secret_key:
        :param read_only:
        :return:
        """
        facebook_link_to_voter = FacebookLinkToVoter()
        facebook_link_to_voter_id = 0

        try:
            if positive_value_exists(facebook_user_id):
                if positive_value_exists(read_only):
                    facebook_link_to_voter = FacebookLinkToVoter.objects.using('readonly').get(
                        facebook_user_id=facebook_user_id,
                    )
                else:
                    facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                        facebook_user_id=facebook_user_id,
                    )
                facebook_link_to_voter_id = facebook_link_to_voter.id
                facebook_link_to_voter_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_FOUND_BY_FACEBOOK_USER_ID "
            elif positive_value_exists(voter_we_vote_id):
                if positive_value_exists(read_only):
                    facebook_link_to_voter = FacebookLinkToVoter.objects.using('readonly').get(
                        voter_we_vote_id__iexact=voter_we_vote_id,
                    )
                else:
                    facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                        voter_we_vote_id__iexact=voter_we_vote_id,
                    )
                facebook_link_to_voter_id = facebook_link_to_voter.id
                facebook_link_to_voter_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
            elif positive_value_exists(facebook_secret_key):
                if positive_value_exists(read_only):
                    facebook_link_to_voter = FacebookLinkToVoter.objects.using('readonly').get(
                        secret_key=facebook_secret_key,
                    )
                else:
                    facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                        secret_key=facebook_secret_key,
                    )
                facebook_link_to_voter_id = facebook_link_to_voter.id
                facebook_link_to_voter_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_FOUND_BY_FACEBOOK_SECRET_KEY "
            else:
                facebook_link_to_voter_found = False
                success = False
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_VARIABLES_MISSING "
        except FacebookLinkToVoter.DoesNotExist:
            facebook_link_to_voter_found = False
            success = True
            status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_NOT_FOUND"
        except Exception as e:
            facebook_link_to_voter_found = False
            success = False
            status = 'FAILED retrieve_facebook_link_to_voter '
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success': success,
            'status': status,
            'facebook_link_to_voter_found': facebook_link_to_voter_found,
            'facebook_link_to_voter_id': facebook_link_to_voter_id,
            'facebook_link_to_voter': facebook_link_to_voter,
        }
        return results

    def extract_facebook_details_data(self, facebook_friend_api_details_entry):
        """
        Extracting facebook friend details with required fields
        :param facebook_friend_api_details_entry:
        :return:
        """
        facebook_friend_dict = {}
        facebook_friend_dict['facebook_user_id'] = (facebook_friend_api_details_entry.get('id')
                                                    if 'id' in facebook_friend_api_details_entry.keys() else None)
        facebook_friend_dict['facebook_user_name'] = (facebook_friend_api_details_entry.get('name')
                                                      if 'name' in facebook_friend_api_details_entry.keys() else "")
        facebook_friend_dict['facebook_user_first_name'] = (facebook_friend_api_details_entry.get('first_name')
                                                            if 'first_name' in facebook_friend_api_details_entry.keys()
                                                            else "")
        facebook_friend_dict['facebook_user_middle_name'] = (facebook_friend_api_details_entry.get('middle_name')
                                                             if 'middle_name' in facebook_friend_api_details_entry.
                                                             keys() else "")
        facebook_friend_dict['facebook_user_last_name'] = (facebook_friend_api_details_entry.get('last_name')
                                                           if 'last_name' in facebook_friend_api_details_entry.keys()
                                                           else "")
        facebook_friend_dict['facebook_user_location_id'] = (facebook_friend_api_details_entry.get('location').get('id')
                                                             if 'location' in facebook_friend_api_details_entry.keys()
                                                                and facebook_friend_api_details_entry.
                                                             get('location', {}).get('id', {}) else None)
        facebook_friend_dict['facebook_user_location_name'] = (facebook_friend_api_details_entry.get('location').get(
            'name') if 'location' in facebook_friend_api_details_entry.keys() and facebook_friend_api_details_entry.get(
            'location', {}).get('name', {}) else "")
        facebook_friend_dict['facebook_user_gender'] = (facebook_friend_api_details_entry.get('gender')
                                                        if 'gender' in facebook_friend_api_details_entry.keys() else "")
        facebook_friend_dict['facebook_user_birthday'] = (facebook_friend_api_details_entry.get('birthday')
                                                          if 'birthday' in facebook_friend_api_details_entry.keys()
                                                          else "")
        # is_silhouette is true for default image of facebook
        facebook_friend_dict['facebook_profile_image_url_https'] = \
            (facebook_friend_api_details_entry.get(
                'picture').get('data').get('url') if 'picture' in facebook_friend_api_details_entry.keys() and
                facebook_friend_api_details_entry.get('picture', {}).get('data', {}).get('url', {}) and
                not facebook_friend_api_details_entry.get('picture', {}).get('data', {}).get('is_silhouette', True)
                else "")
        facebook_friend_dict['facebook_background_image_url_https'] = \
            (facebook_friend_api_details_entry.get('cover').get('source')
             if 'cover' in facebook_friend_api_details_entry.keys() and
                facebook_friend_api_details_entry.get('cover', {}).get('source', {}) else "")
        facebook_friend_dict['facebook_user_about'] = (facebook_friend_api_details_entry.get('about')
                                                       if 'about' in facebook_friend_api_details_entry.keys() else "")
        facebook_friend_dict['facebook_user_is_verified'] = (facebook_friend_api_details_entry.get('is_verified')
                                                             if 'is_verified' in facebook_friend_api_details_entry.
                                                             keys() else "")
        return facebook_friend_dict

    def retrieve_facebook_friends_from_facebook(self, facebook_candidate_url):
        success = False
        status = ''
        facebook_friends_list_found = False
        facebook_friends_list = []
        facebook_api_fields = "id, name, first_name, middle_name, last_name, location{id, name}, gender, birthday, " \
                              "cover{source}, picture.width(200).height(200){url, is_silhouette}, about, is_verified "

        # auth_response_results = self.retrieve_facebook_auth_response(voter_device_id)
        # if not auth_response_results['facebook_auth_response_found']:
        #     error_results = {
        #         'status':                           "FACEBOOK_AUTH_RESPONSE_NOT_FOUND",
        #         'success':                          success,
        #         'facebook_friends_list_found':      facebook_friends_list_found,
        #         'facebook_friends_list': facebook_friends_list,
        #     }
        #     return error_results
        #
        # facebook_auth_response = auth_response_results['facebook_auth_response']
        # try:
        #     facebook_graph = facebook.GraphAPI(facebook_auth_response.facebook_access_token, version='3.1')
        #     facebook_friends_api_details = facebook_graph.get_connections(id=facebook_auth_response.facebook_user_id,
        #                                                                   connection_name="friends",
        #                                                                   fields=facebook_api_fields)
        #
        #     # graph.get_connections returns three dictionary keys i.e. data, paging, summary,
        #     # here data key contains list of friends with the given fields values and paging contains cursors position
        #     # and summary contains total_count of your friends, for ex:
        #     # {"data": [{"name": "Micheal", "first_name": "Micheal", "id": "16086981492"},
        #     # {"name": "John", "first_name": "John", "id": "1263984"],
        #     # "paging": {"cursors": {"before": "QVFmc0QVBsZAk1KWmNwRVFoRzB1MGFDWlpoa3J0NFR6VTQZD",
        #     # "after": "QVFIUlAzdGplaWV5YTZAmeUNCNzVuRk1iPZAnhUNjltUldoSjR5aWZAxdGJ2UktEUHQzNWpBeHRmcEkZD"}},
        #     # "summary": {'total_count': 10}}
        #     for facebook_friend_api_details_entry in facebook_friends_api_details.get('data', []):
        #         # Extract required details for each facebook friend and then updating FacebookFriendsUsingWeVote table
        #         facebook_friend_dict = self.extract_facebook_details_data(facebook_friend_api_details_entry)
        #         facebook_friend_dict['facebook_user_friend_total_count'] = (
        #             facebook_friend_api_details_entry.get('friends').get('summary').get('total_count')
        #             if facebook_friend_api_details_entry.get('friends', {}).get('summary', {}).get('total_count', {})
        #             else None)
        #         if facebook_friend_dict not in facebook_friends_list:
        #             facebook_friends_list.append(facebook_friend_dict)
        #         facebook_friends_saved_results = self.update_or_create_facebook_friends_using_we_vote(
        #             facebook_auth_response.facebook_user_id, facebook_friend_dict.get('facebook_user_id'))
        #         status += ' ' + facebook_friends_saved_results['status']
        #
        #     if facebook_friends_api_details.get('data', []).__len__() == 0:
        #         logger.debug("retrieve_facebook_friends_from_facebook  received zero friends from the API")
        #     success = True
        #     status += " " + "FACEBOOK_FRIENDS_LIST_FOUND"
        #     facebook_friends_list_found = True
        # except Exception as e:
        #     success = False
        #     status += " " + "FACEBOOK_FRIENDS_LIST_FAILED_WITH_EXCEPTION"
        #     facebook_friends_list_found = False
        #     handle_exception(e, logger=logger, exception_message=status)
        #
        # results = {
        #     'success':                          success,
        #     'status':                           status,
        #     'facebook_friends_list_found':      facebook_friends_list_found,
        #     'facebook_friends_list':            facebook_friends_list,
        # }
        # return results
        return True

    @staticmethod
    def retrieve_facebook_photo_from_person_id(person_id):
        """
        person_id can be either id number like '106677724821943' or a login name like 'Bob4Delegate'
        The app_secret is for server based queries only, it is specifically the "App Secret" not the "Client Secret"
        Uses Facebook API 11.0
        """
        try:
            # Fall back to old env var names, if they are still defined on developers machines
            app_id = get_environment_variable_default(
                "SOCIAL_AUTH_FACEBOOK_APP_ID", get_environment_variable_default("SOCIAL_AUTH_FACEBOOK_KEY", ""))
            app_secret = get_environment_variable_default(
                "SOCIAL_AUTH_FACEBOOK_APP_SECRET", get_environment_variable_default("SOCIAL_AUTH_FACEBOOK_SECRET", ""))

            url = "https://graph.facebook.com/v11.0/{}/picture?height=256&access_token={}|{}&redirect=0".format(
                person_id, app_id, app_secret)
            # print(url)
            source = requests.get(url)
            data = json.loads(source.text)
            # print(data)
            if 'error' in data:
                # handle https://facebook.com/andrea-nelson-moore-for-judge-145896229538232
                m = re.search(r'-(\d{6,})$', person_id)
                if bool(m):
                    tail_fb_id = m.group(1)    # e.g.  145896229538232
                    return FacebookManager.retrieve_facebook_photo_from_person_id(tail_fb_id)  # recursive call

                logger.error("retrieve_facebook_photo {}, {}, for person_id == {}".
                             format(data['error']['type'], data['error']['message'], person_id))
                results = {
                    'url': '',
                    'is_silhouette': False,
                    'status': 'FACEBOOK_OBJECT_WITH_ID-{}-DOES_NOT_EXIST  '.format(person_id),
                }
                return results
            url = data['data']['url']
            is_silhouette = data['data']['is_silhouette']
            if is_silhouette:
                logger.error("retrieve_facebook_photo is_silhouette == True, for person_id == {}, indicating a "
                             "facebook auth problem".format(person_id))
                results = {
                    'url': url,
                    'is_silhouette': is_silhouette,
                    'status': 'FB_API_RETURNED_SILOHOUETTE ',
                }
                return results
            # print(url)
            results = {
                'url': url,
                'is_silhouette': is_silhouette,
                'status': 'FB_API_SUCCESS ',
            }
            return results

        except Exception as e:
            logger.error('retrieve_facebook_photo_from_person_id threw ', e)
            results = {
                'url': '',
                'is_silhouette': False,
                'status': 'FB_API_RETURNED_ERROR' + str(e) + ' ',
            }
            return results

    def retrieve_facebook_picture_from_facebook(self, voter_device_id):
        """
        NOTE August 2021: This was written for fb API 3, and we now are at fb API 11.  This does not work.
        This function is for getting facebook friends who are already using WeVote
        NOTE August 2017:  The facebook "friends" API call when called from the server now only returns that subset of
        your facebook friends who are already on WeVote, it will not show your friends who do not have the facebook
        app on their facebook settings page.  It is unclear if this code even works at all.  The code that does the
        job is in the WebApp using the "games" api "invitiable_friends" call.
        If having problems see the note in client side WebApp FacebookInvitableFriends.jsx

        Technical discussion:  https://stackoverflow.com/questions/23417356

        We use this routine to retrieve my facebook friends details and updating FacebookFriendsUsingWeVote table
        :param voter_device_id:
        :return: facebook_friends_list
        """

        success = False
        status = ''
        facebook_friends_list_found = False
        facebook_friends_list = []
        facebook_api_fields = "id, name, first_name, middle_name, last_name, location{id, name}, gender, birthday, " \
                              "cover{source}, picture.width(200).height(200){url, is_silhouette}, about, is_verified "

        auth_response_results = self.retrieve_facebook_auth_response(voter_device_id)
        if not auth_response_results['facebook_auth_response_found']:
            error_results = {
                'status':                           "FACEBOOK_AUTH_RESPONSE_NOT_FOUND",
                'success':                          success,
                'facebook_friends_list_found':      facebook_friends_list_found,
                'facebook_friends_list': facebook_friends_list,
            }
            return error_results

        facebook_auth_response = auth_response_results['facebook_auth_response']
        try:
            facebook_graph = facebook.GraphAPI(facebook_auth_response.facebook_access_token, version='3.1')
            facebook_friends_api_details = facebook_graph.get_connections(id=facebook_auth_response.facebook_user_id,
                                                                          connection_name="friends",
                                                                          fields=facebook_api_fields)

            # graph.get_connections returns three dictionary keys i.e. data, paging, summary,
            # here data key contains list of friends with the given fields values and paging contains cursors positions
            # and summary contains total_count of your friends, for ex:
            # {"data": [{"name": "Micheal", "first_name": "Micheal", "id": "16086981492"},
            # {"name": "John", "first_name": "John", "id": "1263984"],
            # "paging": {"cursors": {"before": "QVFmc0QVBsZAk1KWmNwRVFoRzB1MGFDWlpoa3J0NFR6VTQZD",
            # "after": "QVFIUlAzdGplaWV5YTZAmeUNCNzVuRk1iPZAnhUNjltUldoSjR5aWZAxdGJ2UktEUHQzNWpBeHRmcEkZD"}},
            # "summary": {'total_count': 10}}
            for facebook_friend_api_details_entry in facebook_friends_api_details.get('data', []):
                # Extract required details for each facebook friend and then updating FacebookFriendsUsingWeVote table
                facebook_friend_dict = self.extract_facebook_details_data(facebook_friend_api_details_entry)
                facebook_friend_dict['facebook_user_friend_total_count'] = (
                    facebook_friend_api_details_entry.get('friends').get('summary').get('total_count')
                    if facebook_friend_api_details_entry.get('friends', {}).get('summary', {}).get('total_count', {})
                    else None)
                if facebook_friend_dict not in facebook_friends_list:
                    facebook_friends_list.append(facebook_friend_dict)
                facebook_friends_saved_results = self.update_or_create_facebook_friends_using_we_vote(
                    facebook_auth_response.facebook_user_id, facebook_friend_dict.get('facebook_user_id'))
                status += ' ' + facebook_friends_saved_results['status']

            if facebook_friends_api_details.get('data', []).__len__() == 0:
                logger.debug("retrieve_facebook_friends_from_facebook  received zero friends from the API")
            success = True
            status += " " + "FACEBOOK_FRIENDS_LIST_FOUND"
            facebook_friends_list_found = True
        except Exception as e:
            success = False
            status += " " + "FACEBOOK_FRIENDS_LIST_FAILED_WITH_EXCEPTION"
            facebook_friends_list_found = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                          success,
            'status':                           status,
            'facebook_friends_list_found':      facebook_friends_list_found,
            'facebook_friends_list':            facebook_friends_list,
        }
        return results

    def retrieve_facebook_friends_using_we_vote_list(self, facebook_id_of_me):
        """
        Reterive my friends facebook ids from FacebookFriendsUsingWeVote table.
        :param facebook_id_of_me:
        :return:
        """
        status = ""
        facebook_friends_using_we_vote_list = []

        if not positive_value_exists(facebook_id_of_me):
            success = False
            status = 'RETRIEVE_FACEBOOK_FRIENDS_USING_WE_VOTE-MISSING_FACEBOOK_ID '
            results = {
                'success':                                      success,
                'status':                                       status,
                'facebook_friends_using_we_vote_list_found':    False,
                'facebook_friends_using_we_vote_list':          [],
            }
            return results

        try:
            facebook_friends_using_we_vote_queryset = FacebookFriendsUsingWeVote.objects.all()
            facebook_friends_using_we_vote_queryset = facebook_friends_using_we_vote_queryset.filter(
                facebook_id_of_me=facebook_id_of_me)
            facebook_friends_using_we_vote_list = facebook_friends_using_we_vote_queryset

            if len(facebook_friends_using_we_vote_list):
                success = True
                facebook_friends_using_we_vote_list_found = True
                status += ' FACEBOOK_FRIENDS_USING_WE_VOTE_LIST_RETRIEVED '
            else:
                success = True
                facebook_friends_using_we_vote_list_found = False
                status += ' NO_FACEBOOK_FRIENDS_USING_WE_VOTE_LIST_RETRIEVED '
        except FacebookFriendsUsingWeVote.DoesNotExist:
            # No data found. Not a problem.
            success = True
            facebook_friends_using_we_vote_list_found = False
            status += ' NO_FACEBOOK_FRIENDS_USING_WE_VOTE_LIST_RETRIEVED_DoesNotExist '
            facebook_friends_using_we_vote_list = []
        except Exception as e:
            success = False
            facebook_friends_using_we_vote_list_found = False
            status += ' FAILED retrieve_facebook_friends_using_we_vote_list FacebookFriendsUsingWeVote '
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                                      success,
            'status':                                       status,
            'facebook_friends_using_we_vote_list_found':    facebook_friends_using_we_vote_list_found,
            'facebook_friends_using_we_vote_list':          facebook_friends_using_we_vote_list,
        }
        return results

    def extract_facebook_user_details(self, facebook_user_api_details):
        """
        Extracting facebook user details with required fields
        :param facebook_user_api_details:
        :return:
        """
        facebook_user_details_dict = {
            'facebook_search_found':    True
        }
        facebook_user_details_dict['about'] = (facebook_user_api_details.get('about')
                                               if 'about' in facebook_user_api_details.keys() else "")

        facebook_user_details_dict['location'] = ""
        if 'location' in facebook_user_api_details.keys():
            if 'city' in facebook_user_api_details.get('location'):
                facebook_user_details_dict['location'] += facebook_user_api_details.get('location').get('city')
            if 'street' in facebook_user_api_details.get('location'):
                facebook_user_details_dict['location'] += ", " + facebook_user_api_details.get('location').get('street')
            if 'zip' in facebook_user_api_details.get('location'):
                facebook_user_details_dict['location'] += ", " + facebook_user_api_details.get('location').get('zip')

        photos = (facebook_user_api_details.get('photos').get(
            'data') if 'photos' in facebook_user_api_details.keys() and facebook_user_api_details.get(
            'photos', {}).get('data', []) else "")
        facebook_user_details_dict['photos'] = " ".join([str(photo.get('picture'))
                                                         for photo in photos if 'picture' in photo.keys()])

        facebook_user_details_dict['bio'] = (facebook_user_api_details.get('bio')
                                             if 'bio' in facebook_user_api_details.keys() else "")

        facebook_user_details_dict['general_info'] = (facebook_user_api_details.get('general_info')
                                                      if 'general_info' in facebook_user_api_details.
                                                      keys() else "")
        facebook_user_details_dict['description'] = (facebook_user_api_details.get('description')
                                                     if 'description' in facebook_user_api_details.keys()
                                                     else "")
        facebook_user_details_dict['features'] = (facebook_user_api_details.get('features')
                                                  if 'features' in facebook_user_api_details.keys() else "")
        facebook_user_details_dict['contact_address'] = (facebook_user_api_details.get('contact_address')
                                                         if 'contact_address' in
                                                            facebook_user_api_details.keys() else "")
        facebook_user_details_dict['emails'] = " ".join(facebook_user_api_details.get('emails')
                                                        if 'emails' in facebook_user_api_details.keys() else [])
        facebook_user_details_dict['name'] = (facebook_user_api_details.get('name')
                                              if 'name' in facebook_user_api_details.keys() else "")
        facebook_user_details_dict['mission'] = (facebook_user_api_details.get('mission')
                                                 if 'mission' in facebook_user_api_details.keys() else "")
        facebook_user_details_dict['category'] = (facebook_user_api_details.get('category')
                                                  if 'category' in facebook_user_api_details.keys() else "")
        facebook_user_details_dict['website'] = (facebook_user_api_details.get('website')
                                                 if 'website' in facebook_user_api_details.keys() else "")
        facebook_user_details_dict['personal_interests'] = (facebook_user_api_details.get('personal_interests')
                                                            if 'personal_interests' in
                                                               facebook_user_api_details.keys() else "")
        facebook_user_details_dict['personal_info'] = (facebook_user_api_details.get('personal_info')
                                                       if 'personal_info' in facebook_user_api_details.keys()
                                                       else "")
        posts = (facebook_user_api_details.get('posts').get(
            'data') if 'posts' in facebook_user_api_details.keys() and facebook_user_api_details.get(
            'posts', {}).get('data', []) else "")
        facebook_user_details_dict['posts'] = " ".join([str(post.get('message'))
                                                        for post in posts if 'message' in post.keys()])

        return facebook_user_details_dict

    def retrieve_facebook_user_details_from_facebook(self, voter_device_id, facebook_user_name):
        """
        :param voter_device_id:
        :param facebook_user_name:
        :return:
        """

        success = False
        status = ''
        facebook_user_details_found = False
        facebook_user_details_dict = {
            'facebook_search_found':    facebook_user_details_found
        }
        facebook_api_fields = "about, location, photos{picture}, bio, general_info, description, features, " \
                              "contact_address, emails, posts.limit(10){message}, name, mission, category," \
                              "website, personal_interests, personal_info"
        auth_response_results = self.retrieve_facebook_auth_response(voter_device_id)
        if not auth_response_results['facebook_auth_response_found']:
            error_results = {
                'status':                           "FACEBOOK_AUTH_RESPONSE_NOT_FOUND",
                'success':                          success,
                'facebook_user_details_found':      facebook_user_details_found,
                'facebook_user_details':            facebook_user_details_dict,
            }
            return error_results

        facebook_auth_response = auth_response_results['facebook_auth_response']
        try:
            facebook_graph = facebook.GraphAPI(facebook_auth_response.facebook_access_token, version='3.1')
            facebook_user_api_details = facebook_graph.get_object(id=facebook_user_name,
                                                                  fields=facebook_api_fields)
            facebook_user_details_dict = self.extract_facebook_user_details(facebook_user_api_details)
            success = True
            status += " " + "FACEBOOK_USER_DETAILS_FOUND"
            facebook_user_details_found = True
        except Exception as e:
            success = False
            status += " " + "FACEBOOK_USER_DETAILS_FAILED_WITH_EXCEPTION"
            facebook_user_details_found = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                          success,
            'status':                           status,
            'facebook_user_details_found':      facebook_user_details_found,
            'facebook_user_details':            facebook_user_details_dict,
        }
        return results

    def retrieve_facebook_user_by_facebook_user_id(self, facebook_user_id):
        """
        Retrieve facebook user from FacebookUser table.
        :param facebook_user_id:
        :return:
        """
        status = ""
        facebook_user = FacebookUser()
        try:
            facebook_user = FacebookUser.objects.get(
                facebook_user_id=facebook_user_id
            )
            success = True
            facebook_user_found = True
            status += ' FACEBOOK_USER_RETRIEVED '
        except FacebookUser.DoesNotExist:
            # No data found. Not a problem.
            success = True
            facebook_user_found = False
            status += ' NO_FACEBOOK_USER_RETRIEVED_DoesNotExist '
        except Exception as e:
            success = False
            facebook_user_found = False
            status += ' FAILED retrieve_facebook_user FacebookUser '
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                     success,
            'status':                      status,
            'facebook_user_found':         facebook_user_found,
            'facebook_user':               facebook_user,
        }
        return results

    def remove_my_facebook_entry_from_suggested_friends_list(self, facebook_suggested_friends_list, facebook_id_of_me):
        """
        Facebook graph API method for friends friend return own user entry thats why removing it from
        suggested friend list
        :param facebook_suggested_friends_list:
        :param facebook_id_of_me:
        :return:
        """
        for facebook_user_entry in facebook_suggested_friends_list:
            if convert_to_int(facebook_user_entry['facebook_user_id']) == facebook_id_of_me:
                facebook_suggested_friends_list.remove(facebook_user_entry)
        return facebook_suggested_friends_list
