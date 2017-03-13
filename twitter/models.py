# twitter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/models.py for the code that interfaces with twitter (or other) servers
import tweepy
from django.db import models

from config.base import get_environment_variable
from import_export_twitter.functions import retrieve_twitter_user_info
from wevote_functions.functions import convert_to_int, generate_random_string, positive_value_exists

TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_FRIENDS_IDS_MAX_LIMIT = 5000
TWITTER_API_NAME_FRIENDS_ID = "friends_ids"


class TwitterLinkToOrganization(models.Model):
    """
    This is the link between a Twitter account and an organization
    """
    organization_we_vote_id = models.CharField(verbose_name="we vote id for the org owner", max_length=255, unique=True)
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, unique=True)
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

        return twitter_handle


class TwitterLinkToVoter(models.Model):
    """
    This is the link between a Twitter account and a We Vote voter account
    """
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

        return twitter_handle


class TwitterUser(models.Model):
    """
    We cache the Twitter info for one handle here.
    """
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, blank=True)
    twitter_handle = models.CharField(verbose_name='twitter screen name / handle',
                                      max_length=255, null=False, unique=True)
    twitter_name = models.CharField(verbose_name="display name from twitter", max_length=255, null=True, blank=True)
    twitter_url = models.URLField(blank=True, null=True, verbose_name='url of user\'s website')
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)
    twitter_location = models.CharField(verbose_name="location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_profile_background_image_url_https = models.URLField(verbose_name='tile-able background from twitter',
                                                                 blank=True, null=True)
    twitter_profile_banner_url_https = models.URLField(verbose_name='profile banner image from twitter',
                                                       blank=True, null=True)
    we_vote_hosted_profile_image_url_large = models.URLField(verbose_name='we vote hosted large image url',
                                                             blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(verbose_name='we vote hosted medium image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(verbose_name='we vote hosted tiny image url',
                                                            blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)


class TwitterUserManager(models.Model):

    def __unicode__(self):
        return "TwitterUserManager"

    def create_twitter_link_to_organization(self, twitter_id, organization_we_vote_id):
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

        # Any attempts to save a twitter_link using either twitter_id or voter_we_vote_id that already
        #  exist in the table will fail, since those fields are required to be unique.
        try:
            twitter_link_to_organization = TwitterLinkToOrganization.objects.create(
                twitter_id=twitter_id,
                organization_we_vote_id=organization_we_vote_id,
            )
            twitter_link_to_organization_saved = True
            success = True
            status = "TWITTER_LINK_TO_ORGANIZATION_CREATED"
        except Exception as e:
            twitter_link_to_organization_saved = False
            twitter_link_to_organization = TwitterLinkToOrganization()
            success = False
            status = "TWITTER_LINK_TO_ORGANIZATION_NOT_CREATED"

        results = {
            'success':                              success,
            'status':                               status,
            'twitter_link_to_organization_saved':   twitter_link_to_organization_saved,
            'twitter_link_to_organization':         twitter_link_to_organization,
        }
        return results

    def create_twitter_link_to_voter(self, twitter_id, voter_we_vote_id):

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
            status = "TWITTER_LINK_TO_VOTER_CREATED"

            # TODO DALE Remove voter.twitter_id value here?
        except Exception as e:
            twitter_link_to_voter_saved = False
            twitter_link_to_voter = TwitterLinkToVoter()
            success = False
            status = "TWITTER_LINK_TO_VOTER_NOT_CREATED"

        results = {
            'success':                      success,
            'status':                       status,
            'twitter_link_to_voter_saved':  twitter_link_to_voter_saved,
            'twitter_link_to_voter':        twitter_link_to_voter,
        }
        return results

    def retrieve_twitter_link_to_organization_from_twitter_user_id(self, twitter_user_id):
        return self.retrieve_twitter_link_to_organization(twitter_user_id)

    def retrieve_twitter_link_to_organization_from_twitter_handle(self, twitter_handle):
        twitter_user_id = 0
        results = self.retrieve_twitter_user_locally_or_remotely(twitter_user_id, twitter_handle)
        if results['twitter_user_found']:
            twitter_user = results['twitter_user']
            twitter_user_id = twitter_user.twitter_id

        return self.retrieve_twitter_link_to_organization(twitter_user_id)

    def fetch_twitter_handle_from_organization_we_vote_id(self, organization_we_vote_id):
        organization_twitter_handle = ''
        twitter_results = self.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization_we_vote_id)
        if twitter_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_results['twitter_link_to_organization']
            organization_twitter_handle = twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
        return organization_twitter_handle

    def fetch_twitter_id_from_organization_we_vote_id(self, organization_we_vote_id):
        organization_twitter_id = 0
        twitter_results = self.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization_we_vote_id)
        if twitter_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_results['twitter_link_to_organization']
            organization_twitter_id = twitter_link_to_organization.fetch_twitter_id_locally_or_remotely()
        return organization_twitter_id

    def fetch_twitter_handle_from_voter_we_vote_id(self, voter_we_vote_id):
        voter_twitter_handle = ''
        twitter_results = self.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
            voter_we_vote_id)
        if twitter_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_results['twitter_link_to_voter']
            voter_twitter_handle = twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
        return voter_twitter_handle

    def fetch_twitter_id_from_voter_we_vote_id(self, voter_we_vote_id):
        voter_twitter_id = 0
        twitter_results = self.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
            voter_we_vote_id)
        if twitter_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_results['twitter_link_to_voter']
            voter_twitter_id = twitter_link_to_voter.fetch_twitter_id_locally_or_remotely()
        return voter_twitter_id

    def retrieve_twitter_link_to_organization_from_organization_we_vote_id(self, organization_we_vote_id):
        twitter_user_id = 0
        return self.retrieve_twitter_link_to_organization(twitter_user_id, organization_we_vote_id)

    def retrieve_twitter_link_to_organization(self, twitter_id=0, organization_we_vote_id=''):
        """

        :param twitter_id:
        :param organization_we_vote_id:
        :return:
        """
        twitter_link_to_organization = TwitterLinkToOrganization()
        twitter_link_to_organization_id = 0

        try:
            if positive_value_exists(twitter_id):
                twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                    twitter_id=twitter_id,
                )
                twitter_link_to_organization_id = twitter_link_to_organization.id
                twitter_link_to_organization_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_USER_ID"
            elif positive_value_exists(organization_we_vote_id):
                twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                    organization_we_vote_id__iexact=organization_we_vote_id,
                )
                twitter_link_to_organization_id = twitter_link_to_organization.id
                twitter_link_to_organization_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_ORGANIZATION_WE_VOTE_ID"
            else:
                twitter_link_to_organization_found = False
                success = False
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_VARIABLES_MISSING"
        except TwitterLinkToVoter.DoesNotExist:
            twitter_link_to_organization_found = False
            success = True
            status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_NOT_FOUND"
        except Exception as e:
            twitter_link_to_organization_found = False
            success = False
            status = 'FAILED retrieve_twitter_link_to_organization'

        results = {
            'success':      success,
            'status':       status,
            'twitter_link_to_organization_found':   twitter_link_to_organization_found,
            'twitter_link_to_organization_id':      twitter_link_to_organization_id,
            'twitter_link_to_organization':         twitter_link_to_organization,
        }
        return results

    def retrieve_twitter_link_to_voter_from_twitter_user_id(self, twitter_user_id):
        return self.retrieve_twitter_link_to_voter(twitter_user_id)

    def retrieve_twitter_link_to_voter_from_twitter_handle(self, twitter_handle):
        twitter_user_id = 0
        twitter_user_results = self.retrieve_twitter_user_locally_or_remotely(twitter_user_id, twitter_handle)
        if twitter_user_results['twitter_user_found']:
            twitter_user = twitter_user_results['twitter_user']
            if positive_value_exists(twitter_user.twitter_id):
                return self.retrieve_twitter_link_to_voter(twitter_user.twitter_id)

        twitter_link_to_voter = TwitterLinkToVoter()
        results = {
            'success':                      False,
            'status':                       "COULD_NOT_FIND_TWITTER_ID_FROM_TWITTER_HANDLE",
            'twitter_link_to_voter_found':  False,
            'twitter_link_to_voter_id':     0,
            'twitter_link_to_voter':        twitter_link_to_voter,
        }
        return results

    def retrieve_twitter_link_to_voter_from_voter_we_vote_id(self, voter_we_vote_id):
        twitter_id = 0
        twitter_secret_key = ""
        return self.retrieve_twitter_link_to_voter(twitter_id, voter_we_vote_id, twitter_secret_key)

    def retrieve_twitter_link_to_voter_from_twitter_secret_key(self, twitter_secret_key):
        twitter_id = 0
        voter_we_vote_id = ""
        return self.retrieve_twitter_link_to_voter(twitter_id, voter_we_vote_id, twitter_secret_key)

    def retrieve_twitter_link_to_voter(self, twitter_id=0, voter_we_vote_id='', twitter_secret_key=''):
        """

        :param twitter_id:
        :param voter_we_vote_id:
        :param twitter_secret_key:
        :return:
        """
        twitter_link_to_voter = TwitterLinkToVoter()
        twitter_link_to_voter_id = 0

        try:
            if positive_value_exists(twitter_id):
                twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                    twitter_id=twitter_id,
                )
                twitter_link_to_voter_id = twitter_link_to_voter.id
                twitter_link_to_voter_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_VOTER_FOUND_BY_TWITTER_USER_ID"
            elif positive_value_exists(voter_we_vote_id):
                twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                )
                twitter_link_to_voter_id = twitter_link_to_voter.id
                twitter_link_to_voter_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_VOTER_FOUND_BY_VOTER_WE_VOTE_ID"
            elif positive_value_exists(twitter_secret_key):
                twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                    secret_key=twitter_secret_key,
                )
                twitter_link_to_voter_id = twitter_link_to_voter.id
                twitter_link_to_voter_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_VOTER_FOUND_BY_TWITTER_SECRET_KEY"
            else:
                twitter_link_to_voter_found = False
                success = False
                status = "RETRIEVE_TWITTER_LINK_TO_VOTER_VARIABLES_MISSING"
        except TwitterLinkToVoter.DoesNotExist:
            twitter_link_to_voter_found = False
            success = True
            status = "RETRIEVE_TWITTER_LINK_TO_VOTER_NOT_FOUND"
        except Exception as e:
            twitter_link_to_voter_found = False
            success = False
            status = 'FAILED retrieve_twitter_link_to_voter'

        results = {
            'success': success,
            'status': status,
            'twitter_link_to_voter_found': twitter_link_to_voter_found,
            'twitter_link_to_voter_id': twitter_link_to_voter_id,
            'twitter_link_to_voter': twitter_link_to_voter,
        }
        return results

    def retrieve_twitter_user_locally_or_remotely(self, twitter_user_id, twitter_handle=''):
        """
        We use this routine to quickly store and retrieve twitter user information, whether it is already in the
        database, or if we have to reach out to Twitter to get it.
        :param twitter_user_id:
        :param twitter_handle:
        :return:
        """
        twitter_user_found = False
        twitter_user = TwitterUser()
        success = False
        status = "TWITTER_USER_NOT_FOUND"

        # Is this twitter_handle already stored locally? If so, return that
        twitter_results = self.retrieve_twitter_user(twitter_user_id, twitter_handle)
        if twitter_results['twitter_user_found']:
            return twitter_results

        # If here, we want to reach out to Twitter to get info for this twitter_handle
        twitter_results = retrieve_twitter_user_info(twitter_user_id, twitter_handle)
        if twitter_results['twitter_handle_found']:
            twitter_save_results = self.update_or_create_twitter_user(twitter_results['twitter_json'])
            if twitter_save_results['twitter_user_found']:
                # If saved, pull the fresh results from the database and return
                twitter_second_results = self.retrieve_twitter_user(twitter_user_id, twitter_handle)
                if twitter_second_results['twitter_user_found']:
                    return twitter_second_results

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_found':       twitter_user_found,
            'twitter_user':             twitter_user,
        }
        return results

    def retrieve_twitter_user(self, twitter_user_id, twitter_handle=''):
        twitter_user_on_stage = TwitterUser()
        twitter_user_found = False
        success = False

        try:
            if positive_value_exists(twitter_user_id):
                status = "RETRIEVE_TWITTER_USER_FOUND_WITH_TWITTER_USER_ID"
                twitter_user_on_stage = TwitterUser.objects.get(twitter_id=twitter_user_id)
                twitter_user_found = True
                success = True
            elif positive_value_exists(twitter_handle):
                status = "RETRIEVE_TWITTER_USER_FOUND_WITH_HANDLE"
                twitter_user_on_stage = TwitterUser.objects.get(twitter_handle__iexact=twitter_handle)
                twitter_user_found = True
                success = True
            else:
                status = "RETRIEVE_TWITTER_USER_INSUFFICIENT_VARIABLES"
        except TwitterUser.MultipleObjectsReturned as e:
            success = False
            status = "RETRIEVE_TWITTER_USER_MULTIPLE_FOUND"
        except TwitterUser.DoesNotExist:
            success = True
            status = "RETRIEVE_TWITTER_USER_NONE_FOUND"

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_found':       twitter_user_found,
            'twitter_user':             twitter_user_on_stage,
        }
        return results

    def retrieve_twitter_ids_i_follow_from_twitter(self, twitter_id_of_me, twitter_access_token, twitter_access_secret):
        """
        We use this routine to retrieve twitter ids who i follow and updating the next cursor state in
        TwitterCursorState table
        :param twitter_id_of_me:
        :param twitter_access_token:
        :param twitter_access_secret:
        :return: twitter_ids_i_follow
        """
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(twitter_access_token, twitter_access_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True)

        twitter_next_cursor_state_results = self.retrieve_twitter_next_cursor_state(twitter_id_of_me)
        status = twitter_next_cursor_state_results['status']
        twitter_next_cursor = twitter_next_cursor_state_results['twitter_next_cursor']
        if TWITTER_FRIENDS_IDS_MAX_LIMIT <= twitter_next_cursor:
            twitter_next_cursor = 0

        twitter_ids_i_follow = list()
        try:
            cursor = tweepy.Cursor(
                api.friends_ids, id=twitter_id_of_me, count=TWITTER_FRIENDS_IDS_MAX_LIMIT, since_id=twitter_next_cursor)
            for twitter_ids in cursor.pages():
                twitter_next_cursor += len(twitter_ids)
                twitter_ids_i_follow.extend(twitter_ids)
            success = True
            twitter_next_cursor_state = self.create_twitter_next_cursor_state(
                twitter_id_of_me, TWITTER_API_NAME_FRIENDS_ID, twitter_next_cursor)
            status = status + ' ' + twitter_next_cursor_state['status']
        except tweepy.RateLimitError:
            success = False
            status += ' RETRIEVE_TWITTER_IDS_I_FOLLOW_RATE_LIMIT_ERROR '
        except tweepy.error.TweepError as error_instance:
            success = 'RETRIEVE_TWITTER_IDS_I_FOLLOW_TWEEPY_ERROR: {} '.format(error_instance.reason)

        results = {
            'success':              success,
            'status':               status + ' RETRIEVE_TWITTER_IDS_I_FOLLOW_COMPLETED',
            'twitter_next_cursor':  twitter_next_cursor,
            'twitter_ids_i_follow': twitter_ids_i_follow,
        }
        return results

    def retrieve_twitter_who_i_follow_list(self, twitter_id_of_me):
        """
        Retrieve twitter ids that twitter_id_of_me follows from TwitterWhoIFollow table.
        :param twitter_id_of_me:
        :return:
        """
        status = ""
        twitter_who_i_follow_list = []

        if not positive_value_exists(twitter_id_of_me):
            success = False
            status = 'RETRIEVE_TWITTER_WHO_I_FOLLOW-MISSING_TWITTER_ID '
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

    def retrieve_twitter_next_cursor_state(self, twitter_id_of_me):
        """
        We use this subroutine to get twitter next cursor value from TwitterCursorState table
        :param twitter_id_of_me:
        :return: twitter_next_cursor
        """
        try:
            twitter_next_cursor_state = TwitterCursorState.objects.get(
                twitter_id_of_me=twitter_id_of_me,)
            twitter_next_cursor = twitter_next_cursor_state.twitter_next_cursor
            success = True
            status = "RETRIEVE_TWITTER_NEXT_CURSOR_FOUND_WITH_TWITTER_ID"
        except TwitterCursorState.DoesNotExist:
            twitter_next_cursor = 0
            twitter_next_cursor_state = TwitterCursorState()
            success = True
            status = "RETRIEVE_TWITTER_NEXT_CURSOR_NONE_FOUND"

        results = {
            'success':              success,
            'status':               status,
            'twitter_next_cursor':  twitter_next_cursor,
            'twitter_cursor_state': twitter_next_cursor_state,
        }
        return results

    def create_twitter_who_i_follow_entries(self, twitter_id_of_me, twitter_ids_i_follow, organization_found=False):
        """
        We use this subroutine to create or update TwitterWhoIFollow table with twitter ids i follow.
        :param organization_found:
        :param twitter_id_of_me:
        :param twitter_ids_i_follow:
        :return:
        """
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
            status = "TWITTER_WHO_I_FOLLOW_CREATED"
        except Exception:
            twitter_who_i_follow_saved = False
            twitter_who_i_follow = TwitterWhoIFollow()
            success = False
            status = "TWITTER_WHO_I_FOLLOW_NOT_CREATED"
        results = {
            'success':                      success,
            'status':                       status,
            'twitter_who_i_follow_saved':   twitter_who_i_follow_saved,
            'twitter_who_i_follow':         twitter_who_i_follow,
            }
        return results

    def create_twitter_next_cursor_state(self, twitter_id_of_me, twitter_api_name, twitter_next_cursor):
        """
        We use this subroutine to create or update TwitterCursorState table with next cursor value
        :param twitter_id_of_me:
        :param twitter_api_name:
        :param twitter_next_cursor:
        :return:
        """
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
            status = "TWITTER_NEXT_CURSOR_STATE_CREATED"
        except Exception:
            twitter_next_cursor_state_saved = False
            twitter_next_cursor_state = TwitterCursorState()
            success = False
            status = "TWITTER_NEXT_CURSOR_STATE_NOT_CREATED"
        results = {
            'success':                          success,
            'status':                           status,
            'twitter_next_cursor_state_saved':  twitter_next_cursor_state_saved,
            'twitter_cursor_state':             twitter_next_cursor_state,
        }
        return results

    def save_new_twitter_user_from_twitter_json(self, twitter_json, cached_twitter_profile_image_url_https=None,
                                                cached_twitter_profile_background_image_url_https=None,
                                                cached_twitter_profile_banner_url_https=None,
                                                we_vote_hosted_profile_image_url_large=None,
                                                we_vote_hosted_profile_image_url_medium=None,
                                                we_vote_hosted_profile_image_url_tiny=None):

        if 'screen_name' not in twitter_json:
            results = {
                'success':              False,
                'status':               "SAVE_NEW_TWITTER_USER_MISSING_HANDLE",
                'twitter_user_found':   False,
                'twitter_user':         TwitterUser(),
            }
            return results

        try:
            # Create new twitter_user entry
            twitter_description = twitter_json['description'] if 'description' in twitter_json else ""
            twitter_followers_count = twitter_json['followers_count'] if 'followers_count' in twitter_json else 0
            twitter_handle = twitter_json['screen_name'] if 'screen_name' in twitter_json else ""
            twitter_id = twitter_json['id'] if 'id' in twitter_json else None
            twitter_location = twitter_json['location'] if 'location' in twitter_json else ""
            twitter_name = twitter_json['name'] if 'name' in twitter_json else ""

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                twitter_profile_background_image_url_https = cached_twitter_profile_background_image_url_https
            elif 'profile_background_image_url_https' in twitter_json:
                twitter_profile_background_image_url_https = twitter_json['profile_background_image_url_https']
            else:
                twitter_profile_background_image_url_https = ""

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
            elif 'profile_banner_url' in twitter_json:
                twitter_profile_banner_url_https = twitter_json['profile_banner_url']
            else:
                twitter_profile_banner_url_https = ""

            if positive_value_exists(cached_twitter_profile_image_url_https):
                twitter_profile_image_url_https = cached_twitter_profile_image_url_https
            elif 'profile_image_url_https' in twitter_json:
                twitter_profile_image_url_https = twitter_json['profile_image_url_https']
            else:
                twitter_profile_image_url_https = ""
            twitter_url = twitter_json['url'] if 'url' in twitter_json else ""

            twitter_user_on_stage = TwitterUser(
                twitter_description=twitter_description,
                twitter_followers_count=twitter_followers_count,
                twitter_handle=twitter_handle,
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
            status = 'CREATED_TWITTER_USER'
        except Exception as e:
            success = False
            twitter_user_found = False
            status = 'FAILED_TO_CREATE_NEW_TWITTER_USER'
            twitter_user_on_stage = TwitterUser()

        results = {
            'success':                  success,
            'status':                   status,
            'twitter_user_found':       twitter_user_found,
            'twitter_user':             twitter_user_on_stage,
        }
        return results

    def update_or_create_twitter_user(self, twitter_json, twitter_id=None, cached_twitter_profile_image_url_https=None,
                                      cached_twitter_profile_background_image_url_https=None,
                                      cached_twitter_profile_banner_url_https=None,
                                      we_vote_hosted_profile_image_url_large=None,
                                      we_vote_hosted_profile_image_url_medium=None,
                                      we_vote_hosted_profile_image_url_tiny=None):
        """
        Update a twitter user entry with details retrieved from the Twitter API or
        create a twitter user entry if not exists.
        :param twitter_id:
        :param twitter_json:
        :param cached_twitter_profile_image_url_https:
        :param cached_twitter_profile_background_image_url_https:
        :param cached_twitter_profile_banner_url_https:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny
        :return:
        """
        values_changed = False

        twitter_results = self.retrieve_twitter_user(twitter_id)
        twitter_user_found = twitter_results['twitter_user_found']
        if twitter_user_found:
            # Twitter user already exists so update twitter user details
            twitter_user = twitter_results['twitter_user']
            if 'id' in twitter_json and positive_value_exists(twitter_json['id']):
                if convert_to_int(twitter_json['id']) != twitter_user.twitter_id:
                    twitter_user.twitter_id = convert_to_int(twitter_json['id'])
                    values_changed = True
            if 'screen_name' in twitter_json and positive_value_exists(twitter_json['screen_name']):
                if twitter_json['screen_name'] != twitter_user.twitter_handle:
                    twitter_user.twitter_handle = twitter_json['screen_name']
                    values_changed = True
            if 'name' in twitter_json and positive_value_exists(twitter_json['name']):
                if twitter_json['name'] != twitter_user.twitter_name:
                    twitter_user.twitter_name = twitter_json['name']
                    values_changed = True
            if 'url' in twitter_json and positive_value_exists(twitter_json['url']):
                if twitter_json['url'] != twitter_user.twitter_url:
                    twitter_user.twitter_url = twitter_json['url']
                    values_changed = True
            if 'followers_count' in twitter_json and positive_value_exists(twitter_json['followers_count']):
                if convert_to_int(twitter_json['followers_count']) != twitter_user.twitter_followers_count:
                    twitter_user.twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                twitter_user.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url_https' in twitter_json and \
                    positive_value_exists(twitter_json['profile_image_url_https']):
                if twitter_json['profile_image_url_https'] != twitter_user.twitter_profile_image_url_https:
                    twitter_user.twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                twitter_user.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            elif ('profile_banner_url' in twitter_json) and positive_value_exists(twitter_json['profile_banner_url']):
                if twitter_json['profile_banner_url'] != twitter_user.twitter_profile_banner_url_https:
                    twitter_user.twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                twitter_user.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            elif 'profile_background_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_background_image_url_https']):
                if twitter_json['profile_background_image_url_https'] != \
                        twitter_user.twitter_profile_background_image_url_https:
                    twitter_user.twitter_profile_background_image_url_https = \
                        twitter_json['profile_background_image_url_https']
                    values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                twitter_user.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                twitter_user.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                twitter_user.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_json and positive_value_exists(twitter_json['description']):
                if twitter_json['description'] != twitter_user.twitter_description:
                    twitter_user.twitter_description = twitter_json['description']
                    values_changed = True
            if 'location' in twitter_json and positive_value_exists(twitter_json['location']):
                if twitter_json['location'] != twitter_user.twitter_location:
                    twitter_user.twitter_location = twitter_json['location']
                    values_changed = True

            if values_changed:
                twitter_user.save()
                success = True
                status = "SAVED_TWITTER_USER_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_USER_TWITTER_DETAILS"
            results = {
                'success':              success,
                'status':               status,
                'twitter_user_found':   twitter_user_found,
                'twitter_user':         twitter_user,
            }
            return results

        else:
            # Twitter user does not exist so create new twitter user with latest twitter details
            twitter_save_results = self.save_new_twitter_user_from_twitter_json(
                twitter_json, cached_twitter_profile_image_url_https,
                cached_twitter_profile_background_image_url_https, cached_twitter_profile_banner_url_https,
                we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny)
            return twitter_save_results

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
    # twitter_tweet_id # (unique id from twitter for tweet?)
    author_handle = models.CharField(max_length=15, verbose_name='twitter handle of this tweet\'s author')
    # (stored quickly before we look up voter_id)
    # author_voter_id = models.ForeignKey(Voter, null=True, blank=True, related_name='we vote id of tweet author')
    is_retweet = models.BooleanField(default=False, verbose_name='is this a retweet?')
    # parent_tweet_id # If this is a retweet, what is the id of the originating tweet?
    body = models.CharField(blank=True, null=True, max_length=255, verbose_name='')
    date_published = models.DateTimeField(null=True, verbose_name='date published')


class TweetFavorite(models.Model):
    """
    This table tells us who favorited a tweet
    """
    tweet_id = models.ForeignKey(Tweet, null=True, blank=True, verbose_name='we vote tweet id')
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
    twitter_id_of_me = models.BigIntegerField(verbose_name="twitter id of viewer", null=False, unique=False)
    twitter_id_i_follow = models.BigIntegerField(verbose_name="twitter id of the friend", null=False, unique=False)
    # organization_found = models.BooleanField(verbose_name="organization found in twitterLinkToOrganization",
    #                                          default=False)


class TwitterCursorState(models.Model):
    """
    Maintaining next cursor state of twitter ids that i follow
    """
    twitter_id_of_me = models.BigIntegerField(verbose_name="twitter id of viewer", null=False, unique=False)
    twitter_api_name = models.CharField(verbose_name="twitter api name", max_length=255, null=False, unique=False)
    twitter_next_cursor = models.BigIntegerField(verbose_name="twitter next cursor state", null=False, unique=False)


# This is a we vote copy (for speed) of Twitter handles that follow me. We should have self-healing scripts that set up
#  entries in TwitterWhoIFollow for everyone following someone in the We Vote network, so this table could be flushed
#  and rebuilt at any time
class TwitterWhoFollowMe(models.Model):
    handle_of_me = models.CharField(max_length=15, verbose_name='from this twitter handle\'s perspective...')
    handle_that_follows_me = models.CharField(max_length=15, verbose_name='twitter handle of this tweet\'s author')
