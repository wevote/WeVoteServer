# image/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from django.db import models
from exception.models import handle_record_found_more_than_one_exception
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
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", default=0,
                                                           null=False, blank=False)
    facebook_user_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of image from facebook', blank=True, null=True)
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
    is_active_version = models.BooleanField(verbose_name="True if image is newest", default=False)
    kind_of_image_twitter_background = models.BooleanField(verbose_name="image is twitter background", default=False)
    kind_of_image_twitter_banner = models.BooleanField(verbose_name="image is twitter banner", default=False)
    kind_of_image_twitter_profile = models.BooleanField(verbose_name="image is twitter profile", default=False)
    kind_of_image_profile_medium = models.BooleanField(verbose_name="is image profile medium", default=False)
    kind_of_image_profile_tiny = models.BooleanField(verbose_name="is image profile tiny", default=False)


class WeVoteImageManager(models.Model):

    def __unicode__(self):
        return "WeVoteImageManager"

    def create_we_vote_image(self, voter_we_vote_id, google_civic_election_id, kind_of_image_twitter_profile=False,
                             kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                             kind_of_image_profile_medium=False, kind_of_image_profile_tiny=False):
        """

        :param voter_we_vote_id:
        :param google_civic_election_id:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_profile_medium:
        :param kind_of_image_profile_tiny:
        :return:
        """
        we_vote_image = WeVoteImage()
        try:
            if positive_value_exists(voter_we_vote_id):
                we_vote_image, created = WeVoteImage.objects.get_or_create(
                    voter_we_vote_id=voter_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                    kind_of_image_twitter_background=kind_of_image_twitter_background,
                    kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                    kind_of_image_profile_medium=kind_of_image_profile_medium,
                    kind_of_image_profile_tiny=kind_of_image_profile_tiny,
                )
                we_vote_image_saved = True
                success = True
                status = "We_VOTE_IMAGE_CREATED"
            else:
                we_vote_image_saved = False
                success = False
                status = "WE_VOTE_IMAGE_NOT_CREATED_VOTER_WE_VOTE_ID_NOT_VALID"
        except Exception as e:
            we_vote_image_saved = False
            success = False
            status = "WE_VOTE_IMAGE_NOT_CREATED"

        results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_saved':          we_vote_image_saved,
            'we_vote_image':                we_vote_image,
        }
        return results

    def save_we_vote_image_facebook_info(self, we_vote_image, voter):
        """
        Save facebook information to WeVoteImage
        :param we_vote_image:
        :param voter:
        :return:
        """
        try:
            we_vote_image.facebook_user_id = voter.facebook_id
            we_vote_image.facebook_profile_image_url_https = voter.facebook_profile_image_url_https
            we_vote_image.save()
            success = True
            status = "SAVED_WE_VOTE_IMAGE_FACEBOOK_INFO"
        except Exception as e:
            status = "UNABLE_TO_SAVE_WE_VOE_IMAGE_FACEBOOK_INFO"
            success = False

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

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
        }
        return results

    def save_we_vote_image_twitter_info(self, we_vote_image, twitter_user_images_dict):
        """
        Save twitter information to WeVoteImage
        :param we_vote_image:
        :param twitter_user_images_dict:
        :return:
        """
        try:
            we_vote_image.twitter_id = twitter_user_images_dict['twitter_id']
            we_vote_image.twitter_profile_image_url_https = twitter_user_images_dict['twitter_profile_image_url_https']
            we_vote_image.twitter_profile_background_image_url_https = \
                twitter_user_images_dict['twitter_profile_background_image_url_https']
            we_vote_image.twitter_profile_banner_url_https = \
                twitter_user_images_dict['twitter_profile_banner_url_https']
            we_vote_image.image_width = twitter_user_images_dict['analyze_image_url_results']['image_width']
            we_vote_image.image_height = twitter_user_images_dict['analyze_image_url_results']['image_height']
            we_vote_image.source_image_still_valid = \
                twitter_user_images_dict['analyze_image_url_results']['image_url_valid']

            we_vote_image.save()
            success = True
            status = "SAVED_WE_VOTE_IMAGE_TWITTER_INFO"
        except Exception as e:
            status = "UNABLE_TO_SAVE_WE_VOTE_IMAGE_TWITTER_INFO"
            success = False

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
            'already_saved':    False
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

        results = {
            'status':           status,
            'success':          success,
            'we_vote_image':    we_vote_image,
        }
        return results

    def retrieve_we_vote_image_from_id(self, we_vote_image_id):
        """
        :param we_vote_image_id:
        :return:
        """
        we_vote_image_manager = WeVoteImageManager()
        return we_vote_image_manager.retrieve_we_vote_image(we_vote_image_id, 0)

    def retrieve_we_vote_image_from_voter_we_vote_id(self, voter_we_vote_id, kind_of_image_twitter_profile=False,
                                                     kind_of_image_twitter_background=False,
                                                     kind_of_image_twitter_banner=False,
                                                     kind_of_image_profile_medium=False,
                                                     kind_of_image_profile_tiny=False):
        """
        :param voter_we_vote_id:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_profile_medium:
        :param kind_of_image_profile_tiny:
        :return:
        """
        we_vote_image_id = 0
        we_vote_image_manager = WeVoteImageManager()
        return we_vote_image_manager.retrieve_we_vote_image(
            we_vote_image_id, voter_we_vote_id, kind_of_image_twitter_profile, kind_of_image_twitter_background,
            kind_of_image_twitter_banner, kind_of_image_profile_medium, kind_of_image_profile_tiny)

    def retrieve_we_vote_image(self, we_vote_image_id, voter_we_vote_id, kind_of_image_twitter_profile=False,
                               kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                               kind_of_image_profile_medium=False, kind_of_image_profile_tiny=False):
        """
        :param we_vote_image_id:
        :param voter_we_vote_id:
        :param kind_of_image_twitter_profile:
        :param kind_of_image_twitter_background:
        :param kind_of_image_twitter_banner:
        :param kind_of_image_profile_medium:
        :param kind_of_image_profile_tiny:
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
            elif positive_value_exists(voter_we_vote_id):
                we_vote_image_on_stage = WeVoteImage.objects.get(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                    kind_of_image_twitter_background=kind_of_image_twitter_background,
                    kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                    kind_of_image_profile_medium=kind_of_image_profile_medium,
                    kind_of_image_profile_tiny=kind_of_image_profile_tiny)
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

    def save_image_locally(self, image_url_https, image_local_path):
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
        except Exception as e:
            image_stored = False

        return image_stored

    def store_image_to_aws(self, we_vote_image_file_name, we_vote_image_file_location):
        """
        Upload image to aws
        :param we_vote_image_file_name:
        :param we_vote_image_file_location:
        :return:
        """
        try:
            client = boto3.client(AWS_STORAGE_SERVICE, region_name=AWS_REGION_NAME,
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            upload_image_from_location = "/tmp/" + we_vote_image_file_name
            client.upload_file(upload_image_from_location, AWS_STORAGE_BUCKET_NAME, we_vote_image_file_location)
            image_stored_to_aws = True
        except Exception as e:
            image_stored_to_aws = False

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

        return image_retrieved_from_aws
