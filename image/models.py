# image/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import date
from django.db import models
from exception.models import handle_record_found_more_than_one_exception, handle_exception, \
    handle_record_not_saved_exception, handle_record_not_deleted_exception
from PIL import Image
from urllib.request import urlretrieve
from urllib.error import HTTPError
from wevote_functions.functions import convert_to_int, positive_value_exists
import boto3
import wevote_functions.admin

AWS_ACCESS_KEY_ID = get_environment_variable("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_environment_variable("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
AWS_STORAGE_BUCKET_NAME = get_environment_variable("AWS_STORAGE_BUCKET_NAME")
AWS_STORAGE_SERVICE = "s3"

logger = wevote_functions.admin.get_logger(__name__)


class WeVoteImage(models.Model):
    """
    We cache we vote images info for one handle here.
    """
    voter_we_vote_id = models.CharField(
        verbose_name="voter we vote permanent id", max_length=255, null=True, blank=True)
    candidate_we_vote_id = models.CharField(
        verbose_name="candidate we vote permanent id", max_length=255, null=True, blank=True)
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote permanent id", max_length=255, null=True, blank=True)

    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", default=0,
                                                           null=False, blank=False)
    facebook_user_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of profile image from facebook',
                                                       blank=True, null=True)
    facebook_background_image_url_https = models.URLField(verbose_name='url of background image from facebook',
                                                          blank=True, null=True)
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, blank=True)
    twitter_profile_banner_url_https = models.URLField(verbose_name='profile banner image from twitter',
                                                       blank=True, null=True)
    twitter_profile_background_image_url_https = models.URLField(verbose_name='tile-able background from twitter',
                                                                 blank=True, null=True)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)
    other_source = models.CharField(verbose_name="other source of image", max_length=255, null=True, blank=True)
    other_source_image_url = models.URLField(verbose_name='other source url of image', blank=True, null=True)
    source_image_still_valid = models.BooleanField(verbose_name="is the url of source image still valid", default=False)
    image_height = models.BigIntegerField(verbose_name="height of image in pixel", null=True, blank=True)
    image_width = models.BigIntegerField(verbose_name="width of image in pixel", null=True, blank=True)
    we_vote_image_url = models.URLField(verbose_name="url of image on AWS", blank=True, null=True)
    we_vote_image_file_location = models.CharField(verbose_name="image file path on AWS", max_length=255,
                                                   null=True, blank=True)
    we_vote_parent_image_id = models.BigIntegerField(verbose_name="Local id of parent image", null=True, blank=True)
    date_image_saved = models.DateTimeField(verbose_name="date when image saved on wevote", auto_now_add=True)
    same_day_image_version = models.BigIntegerField(verbose_name="image version on same day", null=True, blank=True)
    is_active_version = models.BooleanField(verbose_name="True if image is newest", default=False)
    kind_of_image_twitter_background = models.BooleanField(verbose_name="image is twitter background", default=False)
    kind_of_image_twitter_banner = models.BooleanField(verbose_name="image is twitter banner", default=False)
    kind_of_image_twitter_profile = models.BooleanField(verbose_name="image is twitter profile", default=False)
    kind_of_image_original = models.BooleanField(verbose_name="is image size original", default=False)
    kind_of_image_facebook_profile = models.BooleanField(verbose_name="image is facebook profile", default=False)
    kind_of_image_facebook_background = models.BooleanField(verbose_name="image is facebook background", default=False)
    kind_of_image_large = models.BooleanField(verbose_name="is image size large", default=False)
    kind_of_image_medium = models.BooleanField(verbose_name="is image size medium", default=False)
    kind_of_image_tiny = models.BooleanField(verbose_name="is image size tiny", default=False)


class WeVoteImageManager(models.Model):

    def __unicode__(self):
        return "WeVoteImageManager"

    def create_we_vote_image(self, google_civic_election_id, voter_we_vote_id=None, candidate_we_vote_id=None,
                             organization_we_vote_id=None, kind_of_image_twitter_profile=False,
                             kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                             kind_of_image_facebook_profile=False, kind_of_image_facebook_background=False,
                             kind_of_image_original=False, kind_of_image_large=False,
                             kind_of_image_medium=False, kind_of_image_tiny=False):
        """

        :param voter_we_vote_id:
        :param candidate_we_vote_id:
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_facebook_profile:
        :param kind_of_image_facebook_background:
        :param kind_of_image_original:
        :param kind_of_image_large:
        :param kind_of_image_medium:
        :param kind_of_image_tiny:
        :return:
        """
        we_vote_image = WeVoteImage()
        try:
            we_vote_image = WeVoteImage.objects.create(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background,
                kind_of_image_original=kind_of_image_original,
                kind_of_image_large=kind_of_image_large,
                kind_of_image_medium=kind_of_image_medium,
                kind_of_image_tiny=kind_of_image_tiny,
            )
            we_vote_image_saved = True
            success = True
            status = "We_VOTE_IMAGE_CREATED"
        except Exception as e:
            we_vote_image_saved = False
            success = False
            status = "WE_VOTE_IMAGE_NOT_CREATED"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_saved':          we_vote_image_saved,
            'we_vote_image':                we_vote_image,
        }
        return results

    def delete_we_vote_image(self, we_vote_image):
        """
        Delete we vote image entry from WeVoteImage table.
        :param we_vote_image:
        :return:
        """
        try:
            we_vote_image.delete()
            success = True
            status = " WE_VOTE_IMAGE_DELETED"
        except Exception as e:
            success = False
            status = "WE_VOTE_IMAGE_NOT_DELETED"
            handle_record_not_deleted_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'success':  success,
            'status':   status
        }
        return results

    def save_we_vote_image_facebook_info(self, we_vote_image, facebook_user_id, image_width, image_height,
                                         facebook_image_url_https, same_day_image_version, kind_of_image_facebook_profile,
                                         kind_of_image_facebook_background, image_url_valid=False):
        """
        Save facebook information to WeVoteImage
        :param we_vote_image:
        :param facebook_user_id:
        :param image_width:
        :param image_height:
        :param facebook_image_url_https:
        :param same_day_image_version:
        :param kind_of_image_facebook_profile:
        :param kind_of_image_facebook_background:
        :param image_url_valid:
        :return:
        """
        try:
            we_vote_image.facebook_user_id = facebook_user_id
            we_vote_image.image_width = image_width
            we_vote_image.image_height = image_height
            we_vote_image.source_image_still_valid = image_url_valid
            we_vote_image.same_day_image_version = same_day_image_version
            if kind_of_image_facebook_profile:
                we_vote_image.facebook_profile_image_url_https = facebook_image_url_https
            elif kind_of_image_facebook_background:
                we_vote_image.facebook_background_image_url_https = facebook_image_url_https
            we_vote_image.save()
            success = True
            status = "SAVED_WE_VOTE_IMAGE_FACEBOOK_INFO"
        except Exception as e:
            status = "UNABLE_TO_SAVE_WE_VOE_IMAGE_FACEBOOK_INFO"
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
        }
        return results

    def save_we_vote_image_other_source_info(self, we_vote_image, other_source, other_source_profile_image_url):
        """
        Save other source information to WeVoteImage
        :param we_vote_image:
        :param other_source:
        :param other_source_profile_image_url:
        :return:
        """
        try:
            we_vote_image.other_source = other_source
            we_vote_image.other_source_profile_image_url = other_source_profile_image_url
            we_vote_image.save()
            success = True
            status = "SAVED_WE_VOTE_IMAGE_OTHER_SOURCE_INFO"
        except Exception as e:
            status = "UNABLE_TO_SAVE_WE_VOE_IMAGE_OTHER_SOURCE_INFO"
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
        }
        return results

    def save_we_vote_image_twitter_info(self, we_vote_image, twitter_id, image_width, image_height,
                                        twitter_image_url_https, same_day_image_version, kind_of_image_twitter_profile,
                                        kind_of_image_twitter_background, kind_of_image_twitter_banner,
                                        image_url_valid=False):
        """
        Save twitter information to WeVoteImage
        :param we_vote_image:
        :param twitter_id:
        :param image_width:
        :param image_height:
        :param image_url_valid:
        :param twitter_image_url_https:
        :param same_day_image_version:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :return:
        """
        try:
            we_vote_image.twitter_id = twitter_id
            we_vote_image.image_width = image_width
            we_vote_image.image_height = image_height
            we_vote_image.source_image_still_valid = image_url_valid
            we_vote_image.same_day_image_version = same_day_image_version
            if kind_of_image_twitter_profile:
                we_vote_image.twitter_profile_image_url_https = twitter_image_url_https
            elif kind_of_image_twitter_background:
                we_vote_image.twitter_profile_background_image_url_https = twitter_image_url_https
            elif kind_of_image_twitter_banner:
                we_vote_image.twitter_profile_banner_url_https = twitter_image_url_https
            we_vote_image.save()
            success = True
            status = "SAVED_WE_VOTE_IMAGE_TWITTER_INFO"
        except Exception as e:
            status = "UNABLE_TO_SAVE_WE_VOTE_IMAGE_TWITTER_INFO"
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
        }
        return results

    def save_we_vote_image_aws_info(self, we_vote_image, we_vote_image_url, we_vote_image_file_location,
                                    we_vote_parent_image_id, is_active_version):
        """
        Save aws specific information to WeVoteImage
        :param we_vote_image:
        :param we_vote_image_url:
        :param we_vote_image_file_location:
        :param we_vote_parent_image_id:
        :param is_active_version:
        :return:
        """
        try:
            we_vote_image.we_vote_image_url = we_vote_image_url
            we_vote_image.we_vote_image_file_location = we_vote_image_file_location
            we_vote_image.we_vote_parent_image_id = we_vote_parent_image_id
            we_vote_image.is_active_version = is_active_version

            we_vote_image.save()
            success = True
            status = "SAVED_WE_VOTE_IMAGE_AWS_INFO"
        except Exception as e:
            status = "UNABLE_TO_SAVE_WE_VOTE_IMAGE_AWS_INFO"
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
        }
        return results

    def set_active_version_false_for_other_images(self, voter_we_vote_id=None, candidate_we_vote_id=None,
                                                  organization_we_vote_id=None, twitter_profile_image_url_https=None,
                                                  twitter_profile_background_image_url_https=None,
                                                  twitter_profile_banner_url_https=None,
                                                  facebook_profile_image_url_https=None,
                                                  facebook_background_image_url_https=None,
                                                  kind_of_image_twitter_profile=False,
                                                  kind_of_image_twitter_background=False,
                                                  kind_of_image_twitter_banner=False,
                                                  kind_of_image_facebook_profile=False,
                                                  kind_of_image_facebook_background=False):
        """
        Set active version false for all other images except for current latest image of a candidate/organization
        :param candidate_we_vote_id:
        :param organization_we_vote_id:
        :param twitter_profile_image_url_https:
        :param twitter_profile_background_image_url_https:
        :param twitter_profile_banner_url_https:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_facebook_profile:
        :param kind_of_image_facebook_background:
        :return:
        """
        try:
            we_vote_image_list = WeVoteImage.objects.all()
            we_vote_image_list = we_vote_image_list.filter(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id, organization_we_vote_id=organization_we_vote_id,
                is_active_version=True, kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background
            )
            we_vote_image_list = we_vote_image_list.exclude(
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                facebook_background_image_url_https=facebook_background_image_url_https
            )

            for we_vote_image in we_vote_image_list:
                we_vote_image.is_active_version = False
                we_vote_image.save()
            status = "SET_ACTIVE_VERSION_FALSE_FOR_OTHER_IMAGES"
            success=True
        except Exception as e:
            status = "UNABLE_TO_SET_ACTIVE_VERSION_FALSE_FOR_OTHER_IMAGES"
            success = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'status':   status,
            'success':  success,
        }
        return results

    def retrieve_we_vote_image_from_id(self, we_vote_image_id):
        """
        :param we_vote_image_id:
        :return:
        """
        we_vote_image_on_stage = WeVoteImage()
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        we_vote_image_id = convert_to_int(we_vote_image_id)
        try:
            if positive_value_exists(we_vote_image_id):
                we_vote_image_on_stage = WeVoteImage.objects.get(
                    id=we_vote_image_id
                )
                we_vote_image_id = we_vote_image_on_stage.id
                success = True
            else:
                we_vote_image_on_stage = WeVoteImage()
                we_vote_image_id = 0
                success = False
        except WeVoteImage.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
        except WeVoteImage.DoesNotExist as e:
            error_result = True
            exception_does_not_exist = True
            success = True

        results = {
            'success':                  success,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'we_vote_image_found':      True if we_vote_image_id > 0 else False,
            'we_vote_image_id':         we_vote_image_id,
            'we_vote_image':            we_vote_image_on_stage
        }
        return results

    def retrieve_we_vote_image_list_from_we_vote_id(self, voter_we_vote_id=None, candidate_we_vote_id=None,
                                                    organization_we_vote_id=None):
        """
        Retrieve a voter's, candidate's or organization's we vote image list from the we_vote_id
        :param voter_we_vote_id:
        :param candidate_we_vote_id:
        :param organization_we_vote_id:
        :return:
        """
        we_vote_image_list = []
        status = ""
        try:
            we_vote_image_queryset = WeVoteImage.objects.all()
            we_vote_image_queryset = we_vote_image_queryset.filter(
                voter_we_vote_id__iexact=voter_we_vote_id,
                candidate_we_vote_id__iexact=candidate_we_vote_id,
                organization_we_vote_id__iexact=organization_we_vote_id,
            )
            we_vote_image_list = we_vote_image_queryset

            if len(we_vote_image_list):
                success = True
                we_vote_image_list_found = True
                status += ' CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED '
            else:
                success = True
                we_vote_image_list_found = False
                status += ' NO_CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED '

        except WeVoteImage.DoesNotExist as e:
            status += " WE_VOTE_IMAGE_DOES_NOT_EXIST "
            success = True
            we_vote_image_list_found = False
        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_WE_VOTE_IMAGE_LIST "
            success = False
            we_vote_image_list_found = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_list_found': we_vote_image_list_found,
            'we_vote_image_list':       we_vote_image_list
        }
        return results

    def twitter_profile_image_url_https_original(self, twitter_profile_image_url_https):
        if twitter_profile_image_url_https:
            return twitter_profile_image_url_https.replace("_normal", "")
        else:
            return None

    def retrieve_we_vote_image_from_url(self, voter_we_vote_id=None, candidate_we_vote_id=None,
                                        organization_we_vote_id=None, twitter_profile_image_url_https=None,
                                        twitter_profile_background_image_url_https=None,
                                        twitter_profile_banner_url_https=None, facebook_profile_image_url_https=None,
                                        facebook_background_image_url_https=None, kind_of_image_original=False,
                                        kind_of_image_large=False, kind_of_image_medium=False,
                                        kind_of_image_tiny=False):
        """
        Retrieve  we vote image from a url match
        :param voter_we_vote_id:
        :param candidate_we_vote_id:
        :param organization_we_vote_id:
        :param twitter_profile_image_url_https:
        :param twitter_profile_background_image_url_https:
        :param twitter_profile_banner_url_https:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :param kind_of_image_original:
        :param kind_of_image_large:
        :param kind_of_image_medium:
        :param kind_of_image_tiny:
        :return:
        """
        we_vote_image_on_stage = WeVoteImage()
        we_vote_image_found = False
        # Getting original image url
        twitter_profile_image_url_https = self.twitter_profile_image_url_https_original(twitter_profile_image_url_https)
        try:
            we_vote_image_on_stage = WeVoteImage.objects.get(
                voter_we_vote_id__iexact=voter_we_vote_id,
                candidate_we_vote_id__iexact=candidate_we_vote_id,
                organization_we_vote_id__iexact=organization_we_vote_id,
                twitter_profile_image_url_https__iexact=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https__iexact=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https__iexact=twitter_profile_banner_url_https,
                facebook_profile_image_url_https__iexact=facebook_profile_image_url_https,
                facebook_background_image_url_https__iexact=facebook_background_image_url_https,
                kind_of_image_original=kind_of_image_original,
                kind_of_image_large=kind_of_image_large,
                kind_of_image_medium=kind_of_image_medium,
                kind_of_image_tiny=kind_of_image_tiny
            )
            we_vote_image_found = True
            success = True
        except WeVoteImage.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
        except WeVoteImage.DoesNotExist as e:
            success = True
            exception_message = "retrieve_we_vote_image_from_url failed"

        results = {
            'success':                  success,
            'we_vote_image_found':      we_vote_image_found,
            'we_vote_image':            we_vote_image_on_stage
        }
        return results

    def retrieve_we_vote_image_list_from_url(self, voter_we_vote_id=None, candidate_we_vote_id=None,
                                             organization_we_vote_id=None, twitter_profile_image_url_https=None,
                                             twitter_profile_background_image_url_https=None,
                                             twitter_profile_banner_url_https=None,
                                             facebook_profile_image_url_https=None,
                                             facebook_background_image_url_https=None):
        """
        Retrieve voter's we vote image list as per image url
        :param voter_we_vote_id:
        :param candidate_we_vote_id:
        :param organization_we_vote_id
        :param twitter_profile_image_url_https:
        :param twitter_profile_background_image_url_https:
        :param twitter_profile_banner_url_https:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :return:
        """
        we_vote_image_list = []
        status = ""
        try:
            we_vote_image_queryset = WeVoteImage.objects.all()
            we_vote_image_queryset = we_vote_image_queryset.filter(
                voter_we_vote_id__iexact=voter_we_vote_id,
                candidate_we_vote_id__iexact=candidate_we_vote_id,
                organization_we_vote_id__iexact=organization_we_vote_id,
                twitter_profile_image_url_https__iexact=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https__iexact=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https__iexact=twitter_profile_banner_url_https,
                facebook_profile_image_url_https__iexact=facebook_profile_image_url_https,
                facebook_background_image_url_https__iexact=facebook_background_image_url_https
                )
            we_vote_image_list = we_vote_image_queryset

            if len(we_vote_image_list):
                success = True
                we_vote_image_list_found = True
                status += ' CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED_FROM_URL '
            else:
                success = True
                we_vote_image_list_found = False
                status += ' NO_CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED_FROM_URL '

        except WeVoteImage.DoesNotExist as e:
            status += " WE_VOTE_IMAGE_DOES_NOT_EXIST "
            success = True
            we_vote_image_list_found = False
        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_WE_VOTE_IMAGE_LIST_FROM_URL "
            success = False
            we_vote_image_list_found = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_list_found': we_vote_image_list_found,
            'we_vote_image_list':       we_vote_image_list
        }
        return results

    def retrieve_cached_we_vote_image_list(self, voter_we_vote_id=None, candidate_we_vote_id=None,
                                           organization_we_vote_id=None, kind_of_image_twitter_profile=False,
                                           kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                                           kind_of_image_facebook_profile=False,
                                           kind_of_image_facebook_background=False,
                                           kind_of_image_original=False, kind_of_image_large=False,
                                           kind_of_image_medium=False, kind_of_image_tiny=False):
        """
        Retrieve cached we vote image list as per kind of image
        :param voter_we_vote_id:
        :param candidate_we_vote_id:
        :param organization_we_vote_id
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_facebook_profile:
        :param kind_of_image_facebook_background:
        :param kind_of_image_original:
        :param kind_of_image_large:
        :param kind_of_image_medium:
        :param kind_of_image_tiny:
        :return:
        """
        we_vote_image_list = []
        status = ""
        try:
            we_vote_image_queryset = WeVoteImage.objects.all()
            we_vote_image_queryset = we_vote_image_queryset.filter(
                voter_we_vote_id__iexact=voter_we_vote_id,
                candidate_we_vote_id__iexact=candidate_we_vote_id,
                organization_we_vote_id__iexact=organization_we_vote_id,
                kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background,
                kind_of_image_original=kind_of_image_original,
                kind_of_image_large=kind_of_image_large,
                kind_of_image_medium=kind_of_image_medium,
                kind_of_image_tiny=kind_of_image_tiny)
            we_vote_image_list = we_vote_image_queryset

            if len(we_vote_image_list):
                success = True
                we_vote_image_list_found = True
                status += ' CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED '
            else:
                success = True
                we_vote_image_list_found = False
                status += ' NO_CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED '

        except WeVoteImage.DoesNotExist as e:
            status += " WE_VOTE_IMAGE_DOES_NOT_EXIST "
            success = True
            we_vote_image_list_found = False
        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_WE_VOTE_IMAGE_LIST "
            success = False
            we_vote_image_list_found = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_list_found': we_vote_image_list_found,
            'we_vote_image_list':       we_vote_image_list
        }
        return results

    def retrieve_todays_cached_we_vote_image_list(self, voter_we_vote_id=None, candidate_we_vote_id=None,
                                                  organization_we_vote_id=None, kind_of_image_twitter_profile=False,
                                                  kind_of_image_twitter_background=False,
                                                  kind_of_image_twitter_banner=False,
                                                  kind_of_image_facebook_profile=False,
                                                  kind_of_image_facebook_background=False,
                                                  kind_of_image_original=False, kind_of_image_large=False,
                                                  kind_of_image_medium=False, kind_of_image_tiny=False):
        """
        Retrieve today's cached images according to the kind of image
        :param voter_we_vote_id:
        :param candidate_we_vote_id:
        :param organization_we_vote_id:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_facebook_profile:
        :param kind_of_image_facebook_background:
        :param kind_of_image_original:
        :param kind_of_image_large:
        :param kind_of_image_medium:
        :param kind_of_image_tiny:
        :return:
        """
        we_vote_image_list = []
        status = ""
        today_date = date.today()
        try:
            we_vote_image_queryset = WeVoteImage.objects.all()
            we_vote_image_queryset = we_vote_image_queryset.filter(
                voter_we_vote_id__iexact=voter_we_vote_id,
                candidate_we_vote_id__iexact=candidate_we_vote_id,
                organization_we_vote_id__iexact=organization_we_vote_id,
                date_image_saved__contains=today_date,
                kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background,
                kind_of_image_original=kind_of_image_original,
                kind_of_image_large=kind_of_image_large,
                kind_of_image_medium=kind_of_image_medium,
                kind_of_image_tiny=kind_of_image_tiny)
            we_vote_image_list = we_vote_image_queryset

            if len(we_vote_image_list):
                success = True
                we_vote_image_list_found = True
                status += ' TODAYS_CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED '
            else:
                success = True
                we_vote_image_list_found = False
                status += ' NO_TODAYS_CACHED_WE_VOTE_IMAGE_LIST_RETRIEVED '

        except WeVoteImage.DoesNotExist as e:
            status += " WE_VOTE_IMAGE_DOES_NOT_EXIST "
            success = True
            we_vote_image_list_found = False
        except Exception as e:
            status += " FAILED_TO RETRIEVE_TODAYS_CACHED_WE_VOTE_IMAGE_LIST "
            success = False
            we_vote_image_list_found = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_list_found': we_vote_image_list_found,
            'we_vote_image_list':       we_vote_image_list
        }
        return results

    def resize_we_vote_master_image(self, image_local_path, image_width, image_height):
        """
        Resize image and save it to the same location
        :param image_local_path:
        :param image_width:
        :param image_height:
        :return:
        """
        try:
            image_local_path = "/tmp/" + image_local_path
            image = Image.open(image_local_path)
            image = image.resize((image_width, image_height), Image.ANTIALIAS)
            image.save(image_local_path)
            resized_image_created = True
        except Exception as e:
            resized_image_created = False
            exception_message = "resize_we_vote_master_image failed"
            handle_exception(e, logger=logger, exception_message=exception_message)

        return resized_image_created

    def store_image_locally(self, image_url_https, image_local_path):
        """
        Save image locally at /tmp/ folder
        :param image_url_https:
        :param image_local_path:
        :return:
        """
        try:
            image_local_path = "/tmp/" + image_local_path
            urlretrieve(image_url_https, image_local_path)
            image_stored = True
        except HTTPError as error:  # something wrong with url
            image_stored = False
            exception_message = "store_image_locally failed because of http error"
            handle_exception(error, logger=logger, exception_message=exception_message)
        except Exception as e:
            image_stored = False
            exception_message = "store_image_locally failed"
            handle_exception(e, logger=logger, exception_message=exception_message)

        return image_stored

    def store_image_to_aws(self, we_vote_image_file_name, we_vote_image_file_location, image_format):
        """
        Upload image to aws
        :param we_vote_image_file_name:
        :param we_vote_image_file_location:
        :param image_format:
        :return:
        """
        try:
            client = boto3.client(AWS_STORAGE_SERVICE, region_name=AWS_REGION_NAME,
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            upload_image_from_location = "/tmp/" + we_vote_image_file_name
            content_type = "image/{image_format}".format(image_format=image_format)
            client.upload_file(upload_image_from_location, AWS_STORAGE_BUCKET_NAME, we_vote_image_file_location,
                               ExtraArgs={'ContentType': content_type})
            image_stored_to_aws = True
        except Exception as e:
            image_stored_to_aws = False
            exception_message = "store_image_to_aws failed"
            handle_exception(e, logger=logger, exception_message=exception_message)

        return image_stored_to_aws

    def retrieve_image_from_aws(self, we_vote_image_file_location):
        """
        Download image from aws
        :param we_vote_image_file_location:
        :return:
        """
        try:
            client = boto3.client(AWS_STORAGE_SERVICE, region_name=AWS_REGION_NAME,
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            download_image_at_location = "/tmp/" + we_vote_image_file_location
            client.download_file(AWS_STORAGE_BUCKET_NAME, we_vote_image_file_location, download_image_at_location)
            image_retrieved_from_aws = True
        except Exception as e:
            image_retrieved_from_aws = False
            exception_message = "retrieve_image_from_aws failed"
            handle_exception(e, logger=logger, exception_message=exception_message)

        return image_retrieved_from_aws
