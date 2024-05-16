# twitter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import date, timedelta

# See also WeVoteServer/import_export_twitter/models.py for the code that interfaces with twitter (or other) servers
import tweepy
from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime, now

import wevote_functions.admin
from config.base import get_environment_variable
from exception.models import handle_record_found_more_than_one_exception
from wevote_functions.functions import convert_to_int, generate_random_string, positive_value_exists

TWITTER_BEARER_TOKEN = get_environment_variable("TWITTER_BEARER_TOKEN")

logger = wevote_functions.admin.get_logger(__name__)


class TwitterLinkToOrganization(models.Model):
    """
    This is the link between a Twitter account and an organization
    """
    DoesNotExist = None
    objects = None
    organization_we_vote_id = models.CharField(verbose_name="we vote id for the org owner", max_length=255, unique=True)
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, unique=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=False, auto_now=True)

    def fetch_twitter_id_locally_or_remotely(self):
        twitter_id = 0
        twitter_user_manager = TwitterUserManager()
        twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
            self.twitter_id,
            read_only=True)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_id = twitter_user.twitter_id

        return twitter_id

    def fetch_twitter_handle_locally_or_remotely(self):
        twitter_handle = ""
        twitter_user_manager = TwitterUserManager()
        twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
            self.twitter_id,
            read_only=True)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_handle = twitter_user.twitter_handle

            # Strip out the twitter handles "False" or "None"
            if twitter_handle:
                twitter_handle_lower = twitter_handle.lower()
                if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
                    twitter_handle = ''

        return twitter_handle


class TwitterLinkToVoter(models.Model):
    """
    This is the link between a Twitter account and a We Vote voter account
    """
    DoesNotExist = None
    objects = None
    voter_we_vote_id = models.CharField(verbose_name="we vote id for the voter owner", max_length=255, unique=True)
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=False, unique=True)
    secret_key = models.CharField(
        verbose_name="secret key to verify ownership twitter account", max_length=255, null=False, unique=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=False, auto_now=True)

    def fetch_twitter_id_locally_or_remotely(self):
        twitter_id = 0
        twitter_user_manager = TwitterUserManager()
        twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(self.twitter_id)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_id = twitter_user.twitter_id

        return twitter_id

    def fetch_twitter_handle_locally_or_remotely(self):
        twitter_handle = ""
        twitter_user_manager = TwitterUserManager()
        twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(self.twitter_id)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_handle = twitter_user.twitter_handle

            # Strip out the twitter handles "False" or "None"
            if twitter_handle:
                twitter_handle_lower = twitter_handle.lower()
                if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
                    twitter_handle = ''

        return twitter_handle


class TwitterLinkPossibility(models.Model):
    """
    These are Twitter Accounts that might match a candidate or organization
    """
    MultipleObjectsReturned = None
    objects = None
    candidate_campaign_we_vote_id = models.CharField(verbose_name="candidate we vote id", max_length=255, unique=False)

    search_term_used = models.CharField(verbose_name="", max_length=255, unique=False)
    twitter_name = models.CharField(verbose_name="display name from twitter", max_length=255, null=True, blank=True)
    not_a_match = models.BooleanField(default=False, verbose_name="")
    likelihood_score = models.IntegerField(verbose_name="", null=True, unique=False)

    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, unique=False)
    twitter_handle = models.CharField(verbose_name='twitter screen name / handle',
                                      max_length=255, null=True, unique=False)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)
    twitter_url = models.URLField(blank=True, null=True, verbose_name='url of website from twitter account')
    twitter_location = models.CharField(verbose_name="location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_utc_offset = models.IntegerField(verbose_name="utc_offset from twitter",
                                             null=True, blank=True, default=0)


class TwitterUser(models.Model):
    """
    We cache the Twitter info for one handle here.
    """
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None
    date_last_updated_from_twitter = models.DateTimeField(null=True, db_index=True)
    twitter_description = models.CharField(
        verbose_name="Text description of this organization from twitter.", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(
        verbose_name="number of twitter followers", null=False, blank=True, default=0)
    twitter_handle = models.CharField(
        verbose_name='twitter screen name / handle', max_length=255, null=False, unique=True)
    twitter_handle_updates_failing = models.BooleanField(default=None, null=True)
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, blank=True, db_index=True)
    twitter_location = models.CharField(verbose_name="location from twitter", max_length=255, null=True, blank=True)
    twitter_name = models.CharField(verbose_name="display name from twitter", max_length=255, null=True, blank=True)
    twitter_profile_image_url_https = models.TextField(verbose_name='url of logo from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.TextField(
        verbose_name='tile-able background from twitter', blank=True, null=True)
    twitter_profile_banner_url_https = models.TextField(
        verbose_name='profile banner image from twitter', blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True, verbose_name='url of user\'s website')
    we_vote_hosted_profile_image_url_large = models.TextField(
        verbose_name='we vote hosted large image url', blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(
        verbose_name='we vote hosted medium image url', blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(
        verbose_name='we vote hosted tiny image url', blank=True, null=True)


class TwitterUserManager(models.Manager):

    def __unicode__(self):
        return "TwitterUserManager"

    @staticmethod
    def update_or_create_tweet(tweet_json, organization_we_vote_id):
        """
        Either update or create a tweet entry.
        """

        created = False
        status = ""
        is_retweet_boolean = False
        if "retweeted_status" in tweet_json._json:
            is_retweet_boolean = True

        if not tweet_json: 
            success = False
            status += 'MISSING_TWEET_JSON '
        else:
            new_tweet, created = Tweet.objects.update_or_create(
                author_handle=tweet_json.user._json['username'],
                twitter_id=tweet_json.user._json['id'],
                tweet_id=tweet_json.id,
                is_retweet=is_retweet_boolean,
                tweet_text=tweet_json.text,
                # RuntimeWarning: DateTimeField Tweet.date_published received a naive datetime (2017-11-30 21:32:35)
                # while time zone support is active.
                date_published=tweet_json.created_at,
                organization_we_vote_id=organization_we_vote_id)
            if new_tweet or len(new_tweet):
                success = True
                status += 'TWEET_SAVED '
            else:
                success = False
                created = False
                status += 'TWEET_NOT_UPDATED_OR_CREATED '

        results = {
            'success':                  success,
            'status':                   status,
            'new_tweet_created':        created,
        }
        return results

    @staticmethod
    def retrieve_tweets_cached_locally(organization_we_vote_id):
        """

        :param organization_we_vote_id:
        :return:
        """
        status = ""
        tweet_list = []
        try:
            tweet_list_query = Tweet.objects.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            tweet_list_query = tweet_list_query.order_by('date_published').reverse()
            tweet_list = list(tweet_list_query)
            status += "TWEET_FOUND "
            success = True
        except Exception as e:
            status += "RETRIEVE_TWEETS_CACHED_LOCALLY_FAILED "
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'tweet_list':               tweet_list,
        }
        return results

    @staticmethod
    def update_or_create_twitter_link_possibility(
            twitter_link_possibility_id=0,
            candidate_campaign_we_vote_id='',
            twitter_handle='',
            defaults=None):
        if defaults is None:
            defaults = {}
        status = ""
        try:
            if positive_value_exists(twitter_link_possibility_id):
                twitter_link_possibility = TwitterLinkPossibility.objects.get(id=twitter_link_possibility_id)
                change_to_save = False
                if 'not_a_match' in defaults:
                    change_to_save = True
                    twitter_link_possibility.not_a_match = defaults['not_a_match']
                if positive_value_exists(change_to_save):
                    twitter_link_possibility.save()
            else:
                TwitterLinkPossibility.objects.update_or_create(
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                    twitter_handle__iexact=twitter_handle,
                    defaults=defaults,
                    )
            status += "TWITTER_LINK_TO_POSSIBILITY_UPDATE_OR_CREATED "
            success = True

        except Exception as e:
            status += "TWITTER_LINK_TO_POSSIBILITY_NOT_UPDATE_OR_CREATED " + str(e) + ' '
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    @staticmethod
    def update_or_create_twitter_link_possibility_from_twitter_json(
            candidate_campaign_we_vote_id,
            twitter_dict,
            search_term,
            likelihood_score):
        created = False
        status = ""
        multiple_objects_returned = False
        twitter_link_possibility = None
        try:
            twitter_link_possibility, created = TwitterLinkPossibility.objects.update_or_create(
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                twitter_id=twitter_dict['id'],
                defaults={
                    'likelihood_score': likelihood_score,
                    'search_term_used': search_term,
                    'twitter_name': twitter_dict['name'],
                    'twitter_handle': twitter_dict['username'],
                    'twitter_id': twitter_dict['id'],
                    'twitter_description': twitter_dict['description'],
                    'twitter_profile_image_url_https': twitter_dict['profile_image_url'],
                    'twitter_url': twitter_dict['expanded_url'],
                    'twitter_location': twitter_dict['location'],
                    'twitter_followers_count': twitter_dict['followers_count'],
                    # 'twitter_utc_offset': twitter_dict['utc_offset'], # No longer provided by Twitter API v2
                    }
                )
            status += "TWITTER_LINK_TO_POSSIBILITY_CREATED "
            success = True
            twitter_link_possibility_found = True
        except TwitterLinkPossibility.MultipleObjectsReturned as e:
            status += "MORE_THAN_ONE_FOUND "
            success = False
            twitter_link_possibility_found = False
            multiple_objects_returned = True
        except Exception as e:
            status += "TWITTER_LINK_TO_POSSIBILITY_NOT_CREATED " + str(e) + ' '
            success = False
            twitter_link_possibility_found = False

        results = {
            'success':                          success,
            'status':                           status,
            'multiple_objects_returned':        multiple_objects_returned,
            'twitter_link_possibility':         twitter_link_possibility,
            'twitter_link_possibility_created': created,
            'twitter_link_possibility_found':   twitter_link_possibility_found,
        }
        return results

    def create_twitter_link_to_organization_from_twitter_handle(self, twitter_handle, organization_we_vote_id):
        twitter_user_id = 0
        results = self.retrieve_twitter_user_locally_or_remotely(twitter_user_id, twitter_handle, read_only=True)
        if results['twitter_user_found']:
            twitter_user = results['twitter_user']
            twitter_user_id = twitter_user.twitter_id
        return self.create_twitter_link_to_organization(
            twitter_id=twitter_user_id,
            organization_we_vote_id=organization_we_vote_id)

    @staticmethod
    def create_twitter_link_to_organization(twitter_id, organization_we_vote_id):
        status = ""
        if not positive_value_exists(twitter_id) or not \
                positive_value_exists(organization_we_vote_id):
            twitter_link_to_organization = TwitterLinkToOrganization()
            results = {
                'success':                              False,
                'status': 'CREATE_TWITTER_LINK_TO_ORGANIZATION_FAILED-MISSING_REQUIRED_VARIABLES',
                'twitter_link_to_organization_saved':   False,
                'twitter_link_to_organization':         twitter_link_to_organization,
            }
            return results

        # Any attempts to save a twitter_link using either twitter_id or organization_we_vote_id that already
        #  exist in the table will fail, since those fields are required to be unique.
        try:
            twitter_link_to_organization = TwitterLinkToOrganization.objects.create(
                twitter_id=twitter_id,
                organization_we_vote_id=organization_we_vote_id,
            )
            twitter_link_to_organization_saved = True
            success = True
            status += "TWITTER_LINK_TO_ORGANIZATION_CREATED "
        except Exception as e:
            twitter_link_to_organization_saved = False
            twitter_link_to_organization = TwitterLinkToOrganization()
            success = False
            status += "TWITTER_LINK_TO_ORGANIZATION_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                              success,
            'status':                               status,
            'twitter_link_to_organization_saved':   twitter_link_to_organization_saved,
            'twitter_link_to_organization':         twitter_link_to_organization,
        }
        return results

    @staticmethod
    def create_twitter_link_to_voter(twitter_id, voter_we_vote_id):
        status = ""
        # Any attempts to save a twitter_link using either twitter_id or voter_we_vote_id that already
        #  exist in the table will fail, since those fields are required to be unique.
        twitter_secret_key = generate_random_string(12)

        try:
            twitter_link_to_voter = TwitterLinkToVoter.objects.create(
                twitter_id=twitter_id,
                voter_we_vote_id=voter_we_vote_id,
                secret_key=twitter_secret_key,
            )
            twitter_link_to_voter_saved = True
            success = True
            status += "TWITTER_LINK_TO_VOTER_CREATED "
        except Exception as e:
            twitter_link_to_voter_saved = False
            twitter_link_to_voter = TwitterLinkToVoter()
            success = False
            status += "TWITTER_LINK_TO_VOTER_NOT_CREATED "

        results = {
            'success':                      success,
            'status':                       status,
            'twitter_link_to_voter_saved':  twitter_link_to_voter_saved,
            'twitter_link_to_voter':        twitter_link_to_voter,
        }
        return results

    @staticmethod
    def delete_twitter_link_possibilities(candidate_campaign_we_vote_id):
        status = ""
        try:
            TwitterLinkPossibility.objects.filter(candidate_campaign_we_vote_id=candidate_campaign_we_vote_id).delete()
            status += "TWITTER_LINK_TO_POSSIBILITY_DELETED "
            success = True
        except Exception as e:
            status += "TWITTER_LINK_TO_POSSIBILITY_NOT_DELETED "
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    @staticmethod
    def delete_twitter_link_possibility(candidate_campaign_we_vote_id, twitter_id):
        status = ""
        try:
            TwitterLinkPossibility.objects.filter(
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                twitter_id=twitter_id,
            ).delete()
            status += "TWITTER_LINK_TO_POSSIBILITY_DELETED "
            success = True
        except Exception as e:
            status += "TWITTER_LINK_TO_POSSIBILITY_NOT_DELETED " + str(e) + ' '
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    def retrieve_twitter_link_to_organization_from_twitter_user_id(self, twitter_user_id):
        return self.retrieve_twitter_link_to_organization(twitter_user_id)

    def retrieve_twitter_link_to_organization_from_twitter_handle(self, twitter_handle, read_only=False):
        status = ""
        success = True
        twitter_user_id = 0
        results = self.retrieve_twitter_user_locally_or_remotely(twitter_user_id, twitter_handle, read_only=read_only)
        if not results['success']:
            status += "SUCCESS_FALSE_RETRIEVING_TWITTER_USER: " + results['status'] + " "
            success = False
            results = {
                'success': success,
                'status': status,
                'twitter_link_to_organization_found': False,
            }
            return results
        elif results['twitter_user_found']:
            twitter_user = results['twitter_user']
            twitter_user_id = twitter_user.twitter_id
        else:
            status += "TWITTER_USER_NOT_FOUND: " + results['status'] + " "
            results = {
                'success':  success,
                'status':   status,
                'twitter_link_to_organization_found': False,
            }
            return results

        return self.retrieve_twitter_link_to_organization(twitter_user_id)

    def fetch_twitter_handle_from_organization_we_vote_id(self, organization_we_vote_id):
        organization_twitter_handle = ''
        twitter_results = self.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization_we_vote_id, read_only=True)
        if twitter_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_results['twitter_link_to_organization']
            organization_twitter_handle = twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
        return organization_twitter_handle

    def fetch_twitter_id_from_organization_we_vote_id(self, organization_we_vote_id):
        organization_twitter_id = 0
        twitter_results = self.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization_we_vote_id, read_only=True)
        if twitter_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_results['twitter_link_to_organization']
            organization_twitter_id = twitter_link_to_organization.fetch_twitter_id_locally_or_remotely()
        return organization_twitter_id

    def fetch_twitter_handle_from_voter_we_vote_id(self, voter_we_vote_id):
        voter_twitter_handle = ''
        twitter_results = self.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
            voter_we_vote_id, read_only=True)
        if twitter_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_results['twitter_link_to_voter']
            voter_twitter_handle = twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
        return voter_twitter_handle

    def fetch_twitter_id_from_voter_we_vote_id(self, voter_we_vote_id):
        voter_twitter_id = 0
        twitter_results = self.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
            voter_we_vote_id, read_only=True)
        if twitter_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_results['twitter_link_to_voter']
            voter_twitter_id = twitter_link_to_voter.fetch_twitter_id_locally_or_remotely()
        return voter_twitter_id

    def fetch_twitter_id_from_twitter_handle(self, twitter_handle):
        twitter_user_id = 0
        results = self.retrieve_twitter_user(twitter_user_id, twitter_handle)
        if results['twitter_user_found']:
            twitter_user = results['twitter_user']
            return twitter_user.twitter_id
        return 0

    def retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            self,
            organization_we_vote_id,
            read_only=False):
        twitter_user_id = 0
        return self.retrieve_twitter_link_to_organization(twitter_user_id, organization_we_vote_id, read_only=read_only)

    @staticmethod
    def retrieve_twitter_link_to_organization(twitter_id=0, organization_we_vote_id='', read_only=False):
        """

        :param twitter_id:
        :param organization_we_vote_id:
        :param read_only:
        :return:
        """
        status = ""
        twitter_link_to_organization = TwitterLinkToOrganization()
        twitter_link_to_organization_id = 0

        try:
            if positive_value_exists(twitter_id):
                if read_only:
                    twitter_link_to_organization = TwitterLinkToOrganization.objects.using('readonly').get(
                        twitter_id=twitter_id)
                else:
                    twitter_link_to_organization = TwitterLinkToOrganization.objects.get(twitter_id=twitter_id)
                twitter_link_to_organization_id = twitter_link_to_organization.id
                twitter_link_to_organization_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_USER_ID"
            elif positive_value_exists(organization_we_vote_id):
                if read_only:
                    twitter_link_to_organization = TwitterLinkToOrganization.objects.using('readonly').get(
                        organization_we_vote_id__iexact=organization_we_vote_id)
                else:
                    twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                        organization_we_vote_id__iexact=organization_we_vote_id)
                twitter_link_to_organization_id = twitter_link_to_organization.id
                twitter_link_to_organization_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_ORGANIZATION_WE_VOTE_ID"
            else:
                twitter_link_to_organization_found = False
                success = False
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_VARIABLES_MISSING"
        except TwitterLinkToOrganization.DoesNotExist:
            twitter_link_to_organization_found = False
            success = True
            status += "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_NOT_FOUND"
        except Exception as e:
            twitter_link_to_organization_found = False
            success = False
            status += 'FAILED retrieve_twitter_link_to_organization: ' + str(e) + " "

        results = {
            'success':      success,
            'status':       status,
            'twitter_link_to_organization_found':   twitter_link_to_organization_found,
            'twitter_link_to_organization_id':      twitter_link_to_organization_id,
            'twitter_link_to_organization':         twitter_link_to_organization,
        }
        return results

    @staticmethod
    def retrieve_twitter_link_to_organization_list(read_only=True, return_we_vote_id_list_only=False):
        """

        :param read_only:
        :param return_we_vote_id_list_only:
        :return:
        """
        organization_we_vote_id_list = []
        organization_we_vote_id_list_found = False
        status = ''
        twitter_link_to_organization_list = []
        twitter_link_to_organization_list_found = False
        try:
            if read_only:
                queryset = TwitterLinkToOrganization.objects.using('readonly').all()
            else:
                queryset = TwitterLinkToOrganization.objects.all()
            if positive_value_exists(return_we_vote_id_list_only):
                queryset = queryset.values_list('organization_we_vote_id', flat=True).distinct()
                organization_we_vote_id_list = list(queryset)
                if len(organization_we_vote_id_list):
                    status += "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_WE_VOTE_ID_LIST_FOUND "
                    organization_we_vote_id_list_found = True
                else:
                    status += "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_WE_VOTE_ID_LIST_NOT_FOUND "
            else:
                twitter_link_to_organization_list = list(queryset)
                if len(twitter_link_to_organization_list):
                    status += "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_LIST_FOUND "
                    twitter_link_to_organization_list_found = True
                else:
                    status += "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_LIST_NOT_FOUND "
            success = True
        except Exception as e:
            success = False
            status += 'FAILED retrieve_twitter_link_to_organization_list: ' + str(e) + " "

        results = {
            'success':                                  success,
            'status':                                   status,
            'organization_we_vote_id_list':             organization_we_vote_id_list,
            'organization_we_vote_id_list_found':       organization_we_vote_id_list_found,
            'twitter_link_to_organization_list_found':  twitter_link_to_organization_list_found,
            'twitter_link_to_organization_list':        twitter_link_to_organization_list,
        }
        return results

    def retrieve_twitter_link_to_voter_from_twitter_user_id(self, twitter_user_id, read_only=False):
        return self.retrieve_twitter_link_to_voter(twitter_user_id, read_only=read_only)

    def retrieve_twitter_link_to_voter_from_twitter_handle(self, twitter_handle, read_only=False):
        twitter_user_id = 0
        twitter_user_results = self.retrieve_twitter_user_locally_or_remotely(
            twitter_user_id,
            twitter_handle,
            read_only=False)
        if twitter_user_results['twitter_user_found']:
            twitter_user = twitter_user_results['twitter_user']
            if positive_value_exists(twitter_user.twitter_id):
                return self.retrieve_twitter_link_to_voter(twitter_user.twitter_id, read_only=read_only)

        twitter_link_to_voter = TwitterLinkToVoter()
        results = {
            'success':                      False,
            'status':                       "COULD_NOT_FIND_TWITTER_ID_FROM_TWITTER_HANDLE",
            'twitter_link_to_voter_found':  False,
            'twitter_link_to_voter_id':     0,
            'twitter_link_to_voter':        twitter_link_to_voter,
        }
        return results

    def retrieve_twitter_link_to_voter_from_voter_we_vote_id(self, voter_we_vote_id, read_only=False):
        twitter_id = 0
        twitter_secret_key = ""
        return self.retrieve_twitter_link_to_voter(
            twitter_id,
            voter_we_vote_id,
            twitter_secret_key,
            read_only=read_only)

    def retrieve_twitter_link_to_voter_from_twitter_secret_key(self, twitter_secret_key, read_only=False):
        twitter_id = 0
        voter_we_vote_id = ""
        return self.retrieve_twitter_link_to_voter(
            twitter_id,
            voter_we_vote_id,
            twitter_secret_key,
            read_only=read_only)

    @staticmethod
    def retrieve_twitter_link_to_voter(twitter_id=0, voter_we_vote_id='', twitter_secret_key='', read_only=False):
        """

        :param twitter_id:
        :param voter_we_vote_id:
        :param twitter_secret_key:
        :param read_only:
        :return:
        """
        status = ""
        success = True
        twitter_link_to_voter = TwitterLinkToVoter()
        twitter_link_to_voter_id = 0

        try:
            if positive_value_exists(twitter_id):
                if read_only:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.using('readonly').get(twitter_id=twitter_id)
                else:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.get(twitter_id=twitter_id)
                twitter_link_to_voter_id = twitter_link_to_voter.id
                twitter_link_to_voter_found = True
                status += "RETRIEVE_TWITTER_LINK_TO_VOTER_FOUND_BY_TWITTER_USER_ID "
            elif positive_value_exists(voter_we_vote_id):
                if read_only:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.using('readonly').get(
                        voter_we_vote_id__iexact=voter_we_vote_id)
                else:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.get(voter_we_vote_id__iexact=voter_we_vote_id)
                twitter_link_to_voter_id = twitter_link_to_voter.id
                twitter_link_to_voter_found = True
                status += "RETRIEVE_TWITTER_LINK_TO_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
            elif positive_value_exists(twitter_secret_key):
                if read_only:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.using('readonly').get(
                        secret_key=twitter_secret_key)
                else:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.get(secret_key=twitter_secret_key)
                twitter_link_to_voter_id = twitter_link_to_voter.id
                twitter_link_to_voter_found = True
                status += "RETRIEVE_TWITTER_LINK_TO_VOTER_FOUND_BY_TWITTER_SECRET_KEY "
            else:
                twitter_link_to_voter_found = False
                success = False
                status += "RETRIEVE_TWITTER_LINK_TO_VOTER_VARIABLES_MISSING "
        except TwitterLinkToVoter.DoesNotExist:
            twitter_link_to_voter_found = False
            status += "RETRIEVE_TWITTER_LINK_TO_VOTER_NOT_FOUND "
        except Exception as e:
            twitter_link_to_voter_found = False
            success = False
            status += 'FAILED retrieve_twitter_link_to_voter: ' + str(e) + ' '

        results = {
            'success': success,
            'status': status,
            'twitter_link_to_voter_found': twitter_link_to_voter_found,
            'twitter_link_to_voter_id': twitter_link_to_voter_id,
            'twitter_link_to_voter': twitter_link_to_voter,
        }
        return results

    def retrieve_twitter_user_locally_or_remotely(self, twitter_user_id=0, twitter_handle='', read_only=False):
        """
        We use this routine to quickly store and retrieve twitter user information, whether it is already in the
        database, or if we have to reach out to Twitter to get it.
        :param twitter_user_id:
        :param twitter_handle:
        :param read_only:
        :return:
        """
        twitter_user_found = False
        twitter_user = None
        success = True
        status = ""

        # Strip out the twitter handles "False" or "None"
        if twitter_handle:
            twitter_handle_lower = twitter_handle.lower()
            if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
                twitter_handle = ''

        # Is this twitter_handle already stored locally? If so, return that
        twitter_results = self.retrieve_twitter_user(twitter_user_id, twitter_handle, read_only=read_only)
        if twitter_results['success'] is False:
            status += twitter_results['status']
        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            if positive_value_exists(twitter_user.twitter_profile_image_url_https):
                # If we have sufficient values, stop here. Otherwise, retrieve from Twitter again.
                return twitter_results
        else:
            status += "TWITTER_USER_NOT_FOUND_LOCALLY "

        # If here, we want to reach out to Twitter to get info for this twitter_handle
        from twitter.functions import retrieve_twitter_user_info
        twitter_api_counter_manager = TwitterApiCounterManager()
        twitter_results = retrieve_twitter_user_info(
            twitter_user_id,
            twitter_handle,
            twitter_api_counter_manager=twitter_api_counter_manager,
            parent='retrieve_twitter_user_locally_or_remotely'
        )
        if twitter_results['success'] is False:
            status += twitter_results['status']
            success = False
        if twitter_results['twitter_handle_found']:
            twitter_save_results = self.update_or_create_twitter_user(
                twitter_dict=twitter_results['twitter_dict'],
                twitter_id=twitter_user_id)
            if twitter_save_results['twitter_user_found']:
                twitter_user = twitter_save_results['twitter_user']
                # If saved, pull the fresh results from the database and return
                twitter_second_results = self.retrieve_twitter_user(twitter_user.twitter_id,
                                                                    twitter_user.twitter_handle)
                if twitter_second_results['twitter_user_found']:
                    status += "TWITTER_USER_FOUND_LOCALLY2: " + twitter_second_results['status']
                    return twitter_second_results
                else:
                    status += "TWITTER_USER_NOT_FOUND_LOCALLY2: " + twitter_second_results['status']
            else:
                status += "TWITTER_UPDATE_OR_CREATE_PROBLEM: " + twitter_save_results['status']
        else:
            status += "TWITTER_USER_NOT_FOUND_FROM_TWITTER: " + twitter_results['status']

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_found':       twitter_user_found,
            'twitter_user':             twitter_user,
        }
        return results

    @staticmethod
    def retrieve_twitter_user(twitter_user_id=0, twitter_handle='', read_only=False):
        twitter_user_on_stage = None
        twitter_user_found = False
        twitter_user_retrieve = False
        success = True
        status = ""
        queryset = None

        # Strip out the twitter handles "False" or "None"
        if twitter_handle:
            twitter_handle_lower = twitter_handle.lower()
            if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
                twitter_handle = ''

        try:
            if positive_value_exists(twitter_user_id):
                status += "RETRIEVE_TWITTER_USER_FOUND_WITH_TWITTER_USER_ID "
                if read_only:
                    queryset = TwitterUser.objects.using('readonly').filter(twitter_id=twitter_user_id).order_by('-id')
                else:
                    queryset = TwitterUser.objects.filter(twitter_id=twitter_user_id).order_by('-id')
                twitter_user_retrieve = True
            elif positive_value_exists(twitter_handle):
                status += "RETRIEVE_TWITTER_USER_FOUND_WITH_HANDLE "
                if read_only:
                    queryset = TwitterUser.objects.using('readonly').filter(
                        twitter_handle__iexact=twitter_handle).order_by('-id')
                else:
                    queryset = TwitterUser.objects.filter(twitter_handle__iexact=twitter_handle).order_by('-id')
                twitter_user_retrieve = True
            else:
                status += "RETRIEVE_TWITTER_USER_INSUFFICIENT_VARIABLES "
            if twitter_user_retrieve:
                success = True
                twitter_user_list = list(queryset)
                twitter_user_found = len(twitter_user_list) > 0
                if twitter_user_found:
                    twitter_user_on_stage = twitter_user_list[0]
                if len(twitter_user_list) > 1:
                    status += "RETRIEVE_TWITTER_USER_FOUND_" + str(len(twitter_user_list)) + "_MATCHING_USERS "
                    log_line = ("TwitterUser.MultipleObjectsReturned for twitter_user_id={0}, twitter_handle={1}, ids=".
                                format(twitter_user_id, twitter_handle))
                    for twitter_user in twitter_user_list:
                        pgid = str(twitter_user.twitter_handle.lower())
                        log_line += pgid + ", "
                    logger.warn(log_line)
                    status += "RETRIEVE_TWITTER_USER_FOUND_WITH_HANDLE_MULTIPLE_RECORDS_RETURNED_USING"
                    if positive_value_exists(twitter_user_id):
                        status += "_ID_" + str(twitter_user_on_stage.id) + " "
                    else:
                        status += "_HANDLE_" + str(twitter_user_on_stage.twitter_handle) + " "

        except TwitterUser.DoesNotExist:
            success = True
            status += "RETRIEVE_TWITTER_USER_NONE_FOUND "
        except Exception as e:
            success = False
            status += "RETRIEVE_TWITTER_UNTRAPPED_EXCEPTION: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_found':       twitter_user_found,
            'twitter_user':             twitter_user_on_stage,
        }
        return results

    @staticmethod
    def retrieve_twitter_user_list(twitter_user_id_list=None, twitter_handle_list=None, read_only=False):
        twitter_user_list = []
        twitter_user_list_found = False
        success = True
        status = ""

        if twitter_user_id_list is None:
            twitter_user_id_list = []
        if twitter_handle_list is None:
            twitter_handle_list = []

        # Strip out the twitter handles "False" or "None"
        twitter_handle_list_cleaned = []
        for twitter_handle in twitter_handle_list:
            if twitter_handle:
                twitter_handle_lower = twitter_handle.lower()
                if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
                    pass
                elif positive_value_exists(twitter_handle_lower) and \
                        twitter_handle_lower not in twitter_handle_list_cleaned:
                    twitter_handle_list_cleaned.append(twitter_handle_lower)
        twitter_handle_list = twitter_handle_list_cleaned

        # Strip out the twitter ids 0, "False" or "None"
        twitter_user_id_list_cleaned = []
        for twitter_user_id in twitter_user_id_list:
            if twitter_user_id:
                twitter_user_id_integer = convert_to_int(twitter_user_id)
                if positive_value_exists(twitter_user_id_integer) and \
                        twitter_user_id_integer not in twitter_user_id_list_cleaned:
                    twitter_user_id_list_cleaned.append(twitter_user_id_integer)
        twitter_user_id_list = twitter_user_id_list_cleaned

        try:
            if read_only:
                queryset = TwitterUser.objects.using('readonly').all()
            else:
                queryset = TwitterUser.objects.all()
            filters = []

            # We want to find twitter_users with *any* of these values
            for twitter_handle in twitter_handle_list:
                new_filter = Q(twitter_handle__iexact=twitter_handle)
                filters.append(new_filter)

            for twitter_user_id in twitter_user_id_list:
                new_filter = Q(twitter_id=twitter_user_id)
                filters.append(new_filter)

            if len(filters) > 0:
                # Add the first query
                final_filters = filters.pop()
                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                queryset = queryset.filter(final_filters)
                twitter_user_list = list(queryset)
                twitter_user_list_found = len(twitter_user_list) > 0
                status += "RETRIEVE_TWITTER_USER_LIST_COUNT: " + str(len(twitter_user_list)) + " "
            else:
                status += "RETRIEVE_TWITTER_USER_LIST_NO_FILTERS_FOUND "
        except Exception as e:
            success = False
            status += "RETRIEVE_TWITTER_USER_LIST_EXCEPTION: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_list_found':  twitter_user_list_found,
            'twitter_user_list':        twitter_user_list,
        }
        return results

    @staticmethod
    def retrieve_twitter_ids_i_follow_from_twitter(
            twitter_id_of_me,
            twitter_voters_access_token_secret,
            twitter_voters_access_secret):
        """
        We use this routine to retrieve twitter ids who i (the voter) follow
        3/1/22: TwitterCursorState and Cursor is not currently used, we load the first 5000 "follows" in line
        3/1/22: This can take a 1/4 to 2 seconds to execute, but does not block/slow down login on the WebApp
        :param twitter_id_of_me:
        :param twitter_voters_access_token_secret:
        :param twitter_voters_access_secret:
        :return: twitter_ids_i_follow
        """

        status = ""
        success = False
        list_of_usernames = []
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            wait_on_rate_limit=True)

        # TODO: Add counter
        # # Use Twitter API call counter to track the number of queries we are doing each day
        # google_civic_api_counter_manager = TwitterApiCounterManager()
        # google_civic_api_counter_manager.create_counter_entry('get_users')

        try:
            tid = twitter_id_of_me
            for response in tweepy.Paginator(client.get_users_following, tid, max_results=1000, limit=5000):
                if response and response.data:
                    lst = response.data
                    for i in range(len(lst)):
                        list_of_usernames.append(lst[i].username)
            status += "TWEEPY_LOADED_" + str(len(list_of_usernames)) + "_TWITTER_USERNAMES "
            success = True

        except tweepy.TooManyRequests:
            success = False
            status += ' RETRIEVE_TWITTER_IDS_I_FOLLOW_RATE_LIMIT_ERROR '
        except tweepy.errors.HTTPException as error_instance:
            success = False
            status += 'RETRIEVE_TWITTER_IDS_I_FOLLOW_TWEEPY_ERROR_HTTPException: {} '.format('GENERAL_ERROR')
        except tweepy.TweepyException as error_instance:
            success = False
            status += 'RETRIEVE_TWITTER_IDS_I_FOLLOW_TWEEPY_ERROR: {} '.format('GENERAL_ERROR')
        except Exception as e:
            success = False
            status += "TWEEPY_EXCEPTION: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status + ' RETRIEVE_TWITTER_IDS_I_FOLLOW_COMPLETED ',
            'twitter_next_cursor':  "",
            'twitter_ids_i_follow': list_of_usernames,
        }
        return results

    @staticmethod
    def retrieve_twitter_who_i_follow_list(twitter_id_of_me):
        """
        Retrieve twitter ids that twitter_id_of_me follows from TwitterWhoIFollow table.
        :param twitter_id_of_me:
        :return:
        """
        status = ""
        twitter_who_i_follow_list = []

        if not positive_value_exists(twitter_id_of_me):
            success = False
            status += 'RETRIEVE_TWITTER_WHO_I_FOLLOW-MISSING_TWITTER_ID '
            results = {
                'success':                          success,
                'status':                           status,
                'twitter_who_i_follow_list_found':  False,
                'twitter_who_i_follow_list':        [],
            }
            return results

        try:
            twitter_who_i_follow_queryset = TwitterWhoIFollow.objects.all()
            twitter_who_i_follow_queryset = twitter_who_i_follow_queryset.filter(
                twitter_id_of_me=twitter_id_of_me)
            twitter_who_i_follow_list = twitter_who_i_follow_queryset

            if len(twitter_who_i_follow_list):
                success = True
                twitter_who_i_follow_list_found = True
                status += ' TWITTER_WHO_I_FOLLOW_LIST_RETRIEVED '
            else:
                success = True
                twitter_who_i_follow_list_found = False
                status += ' NO_TWIITER_WHO_I_FOLLOW_LIST_RETRIEVED '
        except TwitterWhoIFollow.DoesNotExist:
            # No data found. Not a problem.
            success = True
            twitter_who_i_follow_list_found = False
            status += ' NO_TWIITER_WHO_I_FOLLOW_LIST_RETRIEVED_DoesNotExist '
            twitter_who_i_follow_list = []
        except Exception as e:
            success = False
            twitter_who_i_follow_list_found = False
            status += ' FAILED retrieve_twitter_who_i_follow0_list TwitterWhoIFollow '

        results = {
            'success':                          success,
            'status':                           status,
            'twitter_who_i_follow_list_found':  twitter_who_i_follow_list_found,
            'twitter_who_i_follow_list':        twitter_who_i_follow_list,
        }
        return results

    @staticmethod
    def retrieve_twitter_next_cursor_state(twitter_id_of_me):
        """
        We use this subroutine to get twitter next cursor value from TwitterCursorState table
        :param twitter_id_of_me:
        :return: twitter_next_cursor
        """
        status = ""
        try:
            twitter_next_cursor_state = TwitterCursorState.objects.get(
                twitter_id_of_me=twitter_id_of_me,)
            twitter_next_cursor = twitter_next_cursor_state.twitter_next_cursor
            success = True
            status += "RETRIEVE_TWITTER_NEXT_CURSOR_FOUND_WITH_TWITTER_ID "
        except TwitterCursorState.DoesNotExist:
            twitter_next_cursor = 0
            twitter_next_cursor_state = TwitterCursorState()
            success = True
            status += "RETRIEVE_TWITTER_NEXT_CURSOR_NONE_FOUND "
        except Exception as e:
            success = False
            status += "RETRIEVE_TWITTER_NEXT_CURSOR_EXCEPTION: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'twitter_next_cursor':  twitter_next_cursor,
            'twitter_cursor_state': twitter_next_cursor_state,
        }
        return results

    @staticmethod
    def create_twitter_who_i_follow_entries(twitter_id_of_me, twitter_ids_i_follow, organization_found=False):
        """
        We use this subroutine to create or update TwitterWhoIFollow table with twitter ids i follow.
        :param organization_found:
        :param twitter_id_of_me:
        :param twitter_ids_i_follow:
        :return:
        """
        status = ""
        twitter_who_i_follow = TwitterWhoIFollow()
        try:
            for twitter_id_i_follow in twitter_ids_i_follow:
                # TODO anisha Need to check how to get reference for all twitter_who_i_follow
                twitter_who_i_follow, created = TwitterWhoIFollow.objects.update_or_create(
                    twitter_id_of_me=twitter_id_of_me,
                    twitter_id_i_follow=twitter_id_i_follow,
                    # organization_found=organization_found,
                    defaults={
                        'twitter_id_of_me':     twitter_id_of_me,
                        'twitter_id_i_follow':  twitter_id_i_follow
                        # 'organization_found': organization_found
                    }
                )
            twitter_who_i_follow_saved = True
            success = True
            status += "TWITTER_WHO_I_FOLLOW_CREATED "
        except Exception:
            twitter_who_i_follow_saved = False
            twitter_who_i_follow = TwitterWhoIFollow()
            success = False
            status += "TWITTER_WHO_I_FOLLOW_NOT_CREATED "
        results = {
            'success':                      success,
            'status':                       status,
            'twitter_who_i_follow_saved':   twitter_who_i_follow_saved,
            'twitter_who_i_follow':         twitter_who_i_follow,
            }
        return results

    @staticmethod
    def create_twitter_next_cursor_state(twitter_id_of_me, twitter_api_name, twitter_next_cursor):
        """
        We use this subroutine to create or update TwitterCursorState table with next cursor value
        :param twitter_id_of_me:
        :param twitter_api_name:
        :param twitter_next_cursor:
        :return:
        """
        status = ""
        try:
            twitter_next_cursor_state, created = TwitterCursorState.objects.update_or_create(
                twitter_id_of_me=twitter_id_of_me,
                twitter_api_name__iexact=twitter_api_name,
                defaults={
                    'twitter_id_of_me':     twitter_id_of_me,
                    'twitter_api_name':     twitter_api_name,
                    'twitter_next_cursor':  twitter_next_cursor,
                }
            )
            twitter_next_cursor_state_saved = True
            success = True
            status += "TWITTER_NEXT_CURSOR_STATE_CREATED "
        except Exception:
            twitter_next_cursor_state_saved = False
            twitter_next_cursor_state = TwitterCursorState()
            success = False
            status += "TWITTER_NEXT_CURSOR_STATE_NOT_CREATED "
        results = {
            'success':                          success,
            'status':                           status,
            'twitter_next_cursor_state_saved':  twitter_next_cursor_state_saved,
            'twitter_cursor_state':             twitter_next_cursor_state,
        }
        return results

    def reset_twitter_user_image_details(
            self,
            twitter_id,
            twitter_profile_image_url_https,
            twitter_profile_background_image_url_https,
            twitter_profile_banner_url_https):
        """
        Reset a Twitter user entry with original image details from we vote image.
        """
        status = ""
        if positive_value_exists(twitter_id):
            twitter_results = self.retrieve_twitter_user(twitter_id)
            twitter_user_found = twitter_results['twitter_user_found']
            twitter_user = twitter_results['twitter_user']
            if twitter_user_found:
                if positive_value_exists(twitter_profile_image_url_https):
                    twitter_user.twitter_profile_image_url_https = twitter_profile_image_url_https
                if positive_value_exists(twitter_profile_background_image_url_https):
                    twitter_user.twitter_profile_background_image_url_https = twitter_profile_background_image_url_https
                if positive_value_exists(twitter_profile_banner_url_https):
                    twitter_user.twitter_profile_banner_url_https = twitter_profile_banner_url_https

                twitter_user.we_vote_hosted_profile_image_url_large = ''
                twitter_user.we_vote_hosted_profile_image_url_medium = ''
                twitter_user.we_vote_hosted_profile_image_url_tiny = ''
                twitter_user.save()

                success = True
                status += 'RESET_TWITTER_USER_IMAGE_DETAILS '
            else:
                success = False
                status += 'TWITTER_USER_NOT_FOUND '
        else:
            success = False
            status += 'TWITTER_ID_MISSING '
            twitter_user = ''

        results = {
            'success':      success,
            'status':       status,
            'twitter_user': twitter_user,
        }
        return results

    @staticmethod
    def save_new_twitter_user_from_twitter_json(
            twitter_dict,
            cached_twitter_profile_image_url_https=None,
            cached_twitter_profile_background_image_url_https=None,
            cached_twitter_profile_banner_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        status = ""
        if 'username' not in twitter_dict:
            results = {
                'success':              False,
                'status':               "SAVE_NEW_TWITTER_USER_MISSING_HANDLE ",
                'twitter_user_found':   False,
                'twitter_user':         TwitterUser(),
            }
            return results

        try:
            # Create new twitter_user entry
            twitter_description = twitter_dict['description'] if 'description' in twitter_dict else ""
            twitter_followers_count = twitter_dict['followers_count'] if 'followers_count' in twitter_dict else 0
            twitter_handle = twitter_dict['username'] if 'username' in twitter_dict else ""

            # Strip out the twitter handles "False" or "None"
            if twitter_handle:
                twitter_handle_lower = twitter_handle.lower()
                if twitter_handle_lower == 'false' or twitter_handle_lower == 'none':
                    twitter_handle = ''

            twitter_id = twitter_dict['id'] if 'id' in twitter_dict else None
            twitter_location = twitter_dict['location'] if 'location' in twitter_dict else ""
            twitter_name = twitter_dict['name'] if 'name' in twitter_dict else ""
            twitter_handle_updates_failing = twitter_dict['twitter_handle_updates_failing'] \
                if 'twitter_handle_updates_failing' in twitter_dict else False

            # Twitter API v2 removed these fields
            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                twitter_profile_background_image_url_https = cached_twitter_profile_background_image_url_https
            elif 'profile_background_image_url_https' in twitter_dict:
                twitter_profile_background_image_url_https = twitter_dict['profile_background_image_url_https']
            else:
                twitter_profile_background_image_url_https = ""

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
            elif 'profile_banner_url' in twitter_dict:
                twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
            else:
                twitter_profile_banner_url_https = ""

            if positive_value_exists(cached_twitter_profile_image_url_https):
                twitter_profile_image_url_https = cached_twitter_profile_image_url_https
            elif 'profile_image_url' in twitter_dict:
                twitter_profile_image_url_https = twitter_dict['profile_image_url']
            else:
                twitter_profile_image_url_https = ""
            twitter_url = twitter_dict['expanded_url'] if 'expanded_url' in twitter_dict else ""
            date_last_updated_from_twitter = localtime(now()).date()

            twitter_user_on_stage = TwitterUser(
                date_last_updated_from_twitter=date_last_updated_from_twitter,
                twitter_description=twitter_description,
                twitter_followers_count=twitter_followers_count,
                twitter_handle=twitter_handle,
                twitter_handle_updates_failing=twitter_handle_updates_failing,
                twitter_id=twitter_id,
                twitter_location=twitter_location,
                twitter_name=twitter_name,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                twitter_url=twitter_url,
            )
            twitter_user_on_stage.save()
            success = True
            twitter_user_found = True
            status += 'CREATED_TWITTER_USER '
        except Exception as e:
            success = False
            twitter_user_found = False
            logger.error("save_new_twitter_user_from_twitter_json caught: ", str(e))

            status += 'FAILED_TO_CREATE_NEW_TWITTER_USER '
            twitter_user_on_stage = TwitterUser()

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_found':       twitter_user_found,
            'twitter_user':             twitter_user_on_stage,
        }
        return results

    def update_or_create_twitter_user(
            self,
            twitter_dict=None,
            twitter_id=None,
            cached_twitter_profile_image_url_https=None,
            cached_twitter_profile_background_image_url_https=None,
            cached_twitter_profile_banner_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        """
        Update a twitter user entry with details retrieved from the Twitter API or
        create a twitter user entry if not exists.
        :param twitter_id:
        :param twitter_dict:
        :param cached_twitter_profile_image_url_https:
        :param cached_twitter_profile_background_image_url_https:
        :param cached_twitter_profile_banner_url_https:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny
        :return:
        """
        if twitter_dict is None:
            twitter_dict = {}
        status = ""
        values_changed = False

        twitter_results = self.retrieve_twitter_user(twitter_id)
        twitter_user_found = twitter_results['twitter_user_found']

        if not twitter_user_found:
            # Make sure the handle isn't in use, under a different twitter_id
            if 'username' in twitter_dict and positive_value_exists(twitter_dict['username']):
                twitter_handle = twitter_dict['username']
                twitter_results = self.retrieve_twitter_user(0, twitter_handle)
                twitter_user_found = twitter_results['twitter_user_found']

        if twitter_user_found:
            # Twitter user already exists so update Twitter user details
            twitter_user = twitter_results['twitter_user']
            if 'id' in twitter_dict and positive_value_exists(twitter_dict['id']):
                if convert_to_int(twitter_dict['id']) != twitter_user.twitter_id:
                    twitter_user.twitter_id = convert_to_int(twitter_dict['id'])
                    values_changed = True
            if 'username' in twitter_dict and positive_value_exists(twitter_dict['username']):
                if twitter_dict['username'] != twitter_user.twitter_handle:
                    twitter_user.twitter_handle = twitter_dict['username']
                    values_changed = True
            if 'name' in twitter_dict and positive_value_exists(twitter_dict['name']):
                if twitter_dict['name'] != twitter_user.twitter_name:
                    twitter_user.twitter_name = twitter_dict['name']
                    values_changed = True
            # Upgraded to assume we transform raw Twitter incoming format to include 'expanded_url'
            if 'expanded_url' in twitter_dict and positive_value_exists(twitter_dict['expanded_url']):
                if twitter_dict['expanded_url'] != twitter_user.twitter_url:
                    twitter_user.twitter_url = twitter_dict['expanded_url']
                    values_changed = True
            # if 'entities' in twitter_dict and positive_value_exists(twitter_dict['entities']):
            #     if 'url' in twitter_dict['entities']:
            #         if 'urls' in twitter_dict['entities']['url'] \
            #                 and positive_value_exists(twitter_dict['entities']['url']['urls']):
            #             urls_list = twitter_dict['entities']['url']['urls']
            #             for url_dict in urls_list:
            #                 if twitter_user.twitter_url != url_dict['expanded_url']:
            #                     twitter_user.twitter_url = url_dict['expanded_url']
            #                     values_changed = True
            #                 break
            # elif 'url' in twitter_dict and positive_value_exists(twitter_dict['url']):
            #     if twitter_dict['url'] != twitter_user.twitter_url:
            #         twitter_user.twitter_url = twitter_dict['url']
            #         values_changed = True
            if 'followers_count' in twitter_dict and positive_value_exists(twitter_dict['followers_count']):
                if convert_to_int(twitter_dict['followers_count']) != twitter_user.twitter_followers_count:
                    twitter_user.twitter_followers_count = convert_to_int(twitter_dict['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                twitter_user.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url' in twitter_dict and \
                    positive_value_exists(twitter_dict['profile_image_url']):
                if twitter_dict['profile_image_url'] != twitter_user.twitter_profile_image_url_https:
                    twitter_user.twitter_profile_image_url_https = twitter_dict['profile_image_url']
                    values_changed = True

            # Twitter API v2 no longer returns twitter_profile_banner_url_https
            if positive_value_exists(cached_twitter_profile_banner_url_https):
                twitter_user.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            # elif ('profile_banner_url' in twitter_dict) and positive_value_exists(twitter_dict['profile_banner_url']):
            #     if twitter_dict['profile_banner_url'] != twitter_user.twitter_profile_banner_url_https:
            #         twitter_user.twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
            #         values_changed = True

            # Twitter API v2 no longer returns profile_background_image_url_https
            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                twitter_user.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            # elif 'profile_background_image_url_https' in twitter_dict and positive_value_exists(
            #         twitter_dict['profile_background_image_url_https']):
            #     if twitter_dict['profile_background_image_url_https'] != \
            #             twitter_user.twitter_profile_background_image_url_https:
            #         twitter_user.twitter_profile_background_image_url_https = \
            #             twitter_dict['profile_background_image_url_https']
            #         values_changed = True

            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                twitter_user.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                twitter_user.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                twitter_user.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_dict:  # No value required to update description (so we can clear out)
                if twitter_dict['description'] != twitter_user.twitter_description:
                    twitter_user.twitter_description = twitter_dict['description']
                    values_changed = True
            if 'location' in twitter_dict:  # No value required to update location (so we can clear out)
                if twitter_dict['location'] != twitter_user.twitter_location:
                    twitter_user.twitter_location = twitter_dict['location']
                    values_changed = True
            if 'twitter_handle_updates_failing' in twitter_dict:
                if twitter_dict['twitter_handle_updates_failing'] != twitter_user.twitter_handle_updates_failing:
                    twitter_user.twitter_handle_updates_failing = twitter_dict['twitter_handle_updates_failing']
                    values_changed = True
            if values_changed:
                try:
                    twitter_user.date_last_updated_from_twitter = localtime(now()).date()
                    twitter_user.save()
                    success = True
                    status += "SAVED_TWITTER_USER_DETAILS "
                except Exception as e:
                    status += "COULD_NOT_SAVE_TWITTER_USER_DETAILS: " + str(e) + " "
                    success = False
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_USER_TWITTER_DETAILS "
            results = {
                'success':              success,
                'status':               status,
                'twitter_user_created': False,
                'twitter_user_found':   twitter_user_found,
                'twitter_user':         twitter_user,
            }
            return results

        else:
            # Twitter user does not exist so create new Twitter user with latest twitter details
            twitter_save_results = self.save_new_twitter_user_from_twitter_json(
                twitter_dict,
                cached_twitter_profile_image_url_https,
                cached_twitter_profile_background_image_url_https,
                cached_twitter_profile_banner_url_https,
                we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny)
            twitter_save_results['twitter_user_created'] = True
            return twitter_save_results

    def delete_twitter_link_to_organization(self, twitter_id, organization_we_vote_id):
        status = ""
        success = True
        twitter_id = convert_to_int(twitter_id)
        twitter_link_to_organization_deleted = False
        twitter_link_to_organization_not_found = False

        try:
            if positive_value_exists(twitter_id):
                results = self.retrieve_twitter_link_to_organization_from_twitter_user_id(twitter_id)
                if results['twitter_link_to_organization_found']:
                    twitter_link_to_organization = results['twitter_link_to_organization']
                    twitter_link_to_organization.delete()
                    twitter_link_to_organization_deleted = True
                else:
                    twitter_link_to_organization_not_found = True

            elif positive_value_exists(organization_we_vote_id):
                results = self.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
                    organization_we_vote_id)
                if results['twitter_link_to_organization_found']:
                    twitter_link_to_organization = results['twitter_link_to_organization']
                    twitter_link_to_organization.delete()
                    twitter_link_to_organization_deleted = True
                else:
                    twitter_link_to_organization_not_found = True
            else:
                twitter_link_to_organization_not_found = True

        except Exception as e:
            success = False
            status += "UNABLE_TO_DELETE_TWITTER_LINK_TO_ORGANIZATION "

        results = {
            'status':                               status,
            'success':                              success,
            'twitter_link_to_organization_deleted': twitter_link_to_organization_deleted,
            'twitter_link_to_organization_not_found':   twitter_link_to_organization_not_found,
        }
        return results

    def delete_twitter_user(self, twitter_id):
        twitter_id = convert_to_int(twitter_id)
        twitter_user_deleted = False

        try:
            if twitter_id:
                results = self.retrieve_twitter_user(twitter_id)
                if results['twitter_user_found']:
                    twitter_user = results['twitter_user']
                    twitter_id = twitter_user.id
                    twitter_user.delete()
                    twitter_user_deleted = True
        except Exception as e:
            pass

        results = {
            'success':            twitter_user_deleted,
            'twitter_user_deleted': twitter_user_deleted,
            'twitter_id':      twitter_id,
        }
        return results


class Tweet(models.Model):
    """
    A tweet referenced somewhere by a We Vote tag. We store it (once - not every time it is referenced by a tag)
    locally so we can publish JSON from for consumption on the We Vote newsfeed.
    """
    # twitter_tweet_id # (unique id from twitter for tweet?) - TODO ADD This
    # author_twitter_id - TODO ADD This
    objects = None
    author_handle = models.CharField(default='', max_length=15, verbose_name='twitter handle of this tweet\'s author')
    twitter_id = models.BigIntegerField(default=0, verbose_name='twitter user\'s id of this tweet\'s author')
    tweet_id = models.BigIntegerField(default=0, verbose_name='id of this tweet\'s author')
    # (stored quickly before we look up voter_id)
    # author_voter_id = models.ForeignKey(Voter, null=True, blank=True, related_name='we vote id of tweet author')
    is_retweet = models.BooleanField(default=False, verbose_name='is this a retweet?')
    # parent_tweet_id # If this is a retweet, what is the id of the originating tweet?
    tweet_text = models.CharField(default='', blank=False, null=False, max_length=280,
                                  verbose_name='text field from twitter tweet api')
    date_published = models.DateTimeField(null=True, verbose_name='date published')
    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id", max_length=255, null=True,
                                               blank=True, unique=False)


class TweetFavorite(models.Model):
    """
    This table tells us who favorited a tweet
    """
    tweet_id = models.BigIntegerField(default=0, verbose_name='id of this tweet\'s author')
    # twitter_tweet_id # (unique id from twitter for tweet?)
    # TODO Should favorited_by_handle be a ForeignKey link to the Twitter User? I'm concerned this will slow saving,
    #  and it might be better to ForeignKey against voter_id
    favorited_by_handle = models.CharField(
        max_length=15, verbose_name='twitter handle of person who favorited this tweet')
    # (stored quickly before we look up voter_id)
    # favorited_by_voter_id = models.ForeignKey(
    # Voter, null=True, blank=True, related_name='tweet favorited by voter_id')
    date_favorited = models.DateTimeField(null=True, verbose_name='date favorited')


# This should be the master table
class TwitterWhoIFollow(models.Model):
    """
    Other Twitter ids that I follow, from the perspective of twitter id of me
    """
    DoesNotExist = None
    objects = None
    twitter_id_of_me = models.BigIntegerField(verbose_name="twitter id of viewer", null=False, unique=False)
    twitter_id_i_follow = models.BigIntegerField(verbose_name="twitter id of the friend", null=False, unique=False)
    # organization_found = models.BooleanField(verbose_name="organization found in twitterLinkToOrganization",
    #                                          default=False)


class TwitterCursorState(models.Model):
    """
    Maintaining next cursor state of twitter ids that i follow
    """
    DoesNotExist = None
    objects = None
    twitter_id_of_me = models.BigIntegerField(verbose_name="twitter id of viewer", null=False, unique=False)
    twitter_api_name = models.CharField(verbose_name="twitter api name", max_length=255, null=False, unique=False)
    twitter_next_cursor = models.BigIntegerField(verbose_name="twitter next cursor state", null=False, unique=False)


# This is a wevote copy (for speed) of Twitter handles that follow me. We should have self-healing scripts that set up
#  entries in TwitterWhoIFollow for everyone following someone in the We Vote network, so this table could be flushed
#  and rebuilt at any time
class TwitterWhoFollowMe(models.Model):
    handle_of_me = models.CharField(max_length=15, verbose_name='from this twitter handle\'s perspective...')
    handle_that_follows_me = models.CharField(max_length=15, verbose_name='twitter handle of this tweet\'s author')


class TwitterApiCounter(models.Model):
    objects = None
    datetime_of_action = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)
    kind_of_action = models.CharField(
        verbose_name="kind of call to Twitter", max_length=50, null=True, blank=True, db_index=True)
    function = models.CharField(verbose_name='function', max_length=255, null=True, unique=False)
    success = models.BooleanField(verbose_name='api call succeeded', default=True, db_index=True)
    disambiguator = models.PositiveIntegerField(verbose_name="disambiguate within the function", default=0, null=True)
    candidate_name = models.CharField(verbose_name='twitter screen name / handle', max_length=255, null=True,
                                      unique=False)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, db_index=True)
    search_term = models.CharField(verbose_name='search term to API', max_length=255, null=True, unique=False)
    text = models.CharField(verbose_name='text', max_length=255, null=True, unique=False)
    username = models.CharField(verbose_name='twitter screen name / handle', max_length=64, null=True, unique=False)
    voter_we_vote_id = models.CharField(verbose_name='voter we vote id', max_length=255, null=True, unique=False)


class TwitterApiCounterDailySummary(models.Model):
    date_of_action = models.DateField(verbose_name='date of action', null=False, auto_now=False)
    kind_of_action = models.CharField(verbose_name="kind of call to Twitter", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


class TwitterApiCounterWeeklySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    week_of_action = models.SmallIntegerField(verbose_name='number of the week', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call to Twitter", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


class TwitterApiCounterMonthlySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    month_of_action = models.SmallIntegerField(verbose_name='number of the month', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call to Twitter", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


# noinspection PyBroadException
class TwitterApiCounterManager(models.Manager):

    @staticmethod
    def create_counter_entry(kind_of_action, google_civic_election_id=0):
        """
        Create an entry that records that a call to the Twitter Api was made.
        """
        try:
            google_civic_election_id = convert_to_int(google_civic_election_id)

            # TODO: We need to work out the timezone questions
            TwitterApiCounter.objects.create(
                kind_of_action=kind_of_action,
                google_civic_election_id=google_civic_election_id,
            )
            success = True
            status = 'ENTRY_SAVED'
        except Exception:
            success = False
            status = 'SOME_ERROR'

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    @staticmethod
    def retrieve_daily_summaries(kind_of_action='', google_civic_election_id=0, days_to_display=30):
        # Start with today and cycle backwards in time
        daily_summaries = []
        day_on_stage = date.today()  # TODO: We need to work out the timezone questions
        number_found = 0
        maximum_attempts = 365
        attempt_count = 0

        try:
            while number_found <= days_to_display and attempt_count <= maximum_attempts:
                attempt_count += 1
                counter_queryset = TwitterApiCounter.objects.using('readonly').all()
                if positive_value_exists(kind_of_action):
                    counter_queryset = counter_queryset.filter(kind_of_action=kind_of_action)
                if positive_value_exists(google_civic_election_id):
                    counter_queryset = counter_queryset.filter(google_civic_election_id=google_civic_election_id)

                # Find the number of these entries on that particular day
                # counter_queryset = counter_queryset.filter(datetime_of_action__contains=day_on_stage)
                counter_queryset = counter_queryset.filter(
                    datetime_of_action__year=day_on_stage.year,
                    datetime_of_action__month=day_on_stage.month,
                    datetime_of_action__day=day_on_stage.day)
                total_api_call_count = counter_queryset.count()
                fail_counter_queryset = counter_queryset.filter(success=False)
                failing_api_call_count = fail_counter_queryset.count()
                succeeding_api_call_count = total_api_call_count - failing_api_call_count

                # If any api calls were found on that date, pass it out for display
                if positive_value_exists(total_api_call_count):
                    daily_summary = {
                        'date_string': day_on_stage,
                        'total_count': total_api_call_count,
                        'succeeding_count': succeeding_api_call_count,
                        'failing_count': failing_api_call_count,
                    }
                    daily_summaries.append(daily_summary)
                    number_found += 1

                day_on_stage -= timedelta(days=1)
        except Exception:
            pass

        return daily_summaries


def create_detailed_counter_entry(kind_of_action=None, function=None, success=True, elements=None):
    """
    Create a detailed entry that records that a call to the Twitter Api was made.
    """
    idt = 0
    try:
        # TODO: We need to work out the timezone questions
        counter = TwitterApiCounter.objects.create(
            kind_of_action=kind_of_action,
            google_civic_election_id=elements.get('google_civic_election_id', None),
            function=function,
            success=success,
            disambiguator=elements.get('disambiguator', None),
            candidate_name=elements.get('candidate_name', None),
            search_term=elements.get('search_term', None),
            text=elements.get('text', None),
            username=elements.get('username', None),
            voter_we_vote_id=elements.get('voter_we_vote_id', None),
        )
        success = True
        status = 'ENTRY_SAVED'
        idt = counter.id
    except Exception as e:
        print('create_detailed_counter_entry error ' + str(e))
        success = False
        status = 'CREATE_DETAILED_COUNTER_ENTRY_ERROR: ' + str(e) + " "
    results = {
        'success':                  success,
        'status':                   status,
        'id':                       idt,
    }
    return results


# If we got a tweepy error, mark the row as NOT success
def mark_detailed_counter_entry(counter, success, status):
    try:
        idt = counter['id']
        print('mark_detailed_counter_entry id: ', idt, ', success: ', success, ', status: ', status)
        counter_queryset = TwitterApiCounter.objects.filter(id=idt)
        counter_row = counter_queryset.first()
        counter_row.success = success
        counter_row.text = status + counter_row.text
        counter_row.save()

    except Exception as e:
        print('mark_detailed_counter_entry exception (' + status + ')' + str(e))
