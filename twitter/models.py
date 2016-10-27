# twitter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/models.py for the code that interfaces with twitter (or other) servers

from django.db import models
from import_export_twitter.functions import retrieve_twitter_user_info
from wevote_functions.functions import convert_to_int, generate_random_string, positive_value_exists


class TwitterLinkToOrganization(models.Model):
    """
    This is the link between a Twitter account and an organization
    """
    organization_we_vote_id = models.CharField(verbose_name="we vote id for the org owner", max_length=255, unique=True)
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, unique=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=False, auto_now=True)

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
        return self.retrieve_twitter_link_to_organization(twitter_user_id, twitter_handle)

    def retrieve_twitter_link_to_organization_from_organization_we_vote_id(self, organization_we_vote_id):
        twitter_user_id = 0
        twitter_handle = ""
        return self.retrieve_twitter_link_to_organization(twitter_user_id, twitter_handle, organization_we_vote_id)

    def retrieve_twitter_link_to_organization(self, twitter_id=0, twitter_handle='', organization_we_vote_id=''):
        """

        :param twitter_id:
        :param twitter_handle:
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
            elif positive_value_exists(twitter_handle):
                twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                    twitter_handle__iexact=twitter_handle,
                )
                twitter_link_to_organization_id = twitter_link_to_organization.id
                twitter_link_to_organization_found = True
                success = True
                status = "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_HANDLE"
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
            twitter_save_results = self.save_new_twitter_user_from_twitter_json(twitter_results['twitter_json'])
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

    def save_new_twitter_user_from_twitter_json(self, twitter_json):

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
            twitter_followers_count = twitter_json['followers_count'] if 'followers_count' in twitter_json else ""
            twitter_handle = twitter_json['screen_name'] if 'screen_name' in twitter_json else ""
            twitter_id = twitter_json['id'] if 'id' in twitter_json else ""
            twitter_location = twitter_json['location'] if 'location' in twitter_json else ""
            twitter_name = twitter_json['name'] if 'name' in twitter_json else ""
            twitter_profile_background_image_url_https = twitter_json['profile_background_image_url_https'] \
                if 'profile_background_image_url_https' in twitter_json else ""
            twitter_profile_banner_url_https = twitter_json['profile_banner_url_https'] \
                if 'profile_banner_url_https' in twitter_json else ""
            twitter_profile_image_url_https = twitter_json['profile_image_url_https'] \
                if 'profile_image_url_https' in twitter_json else ""
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

    def update_or_create_twitter_user(self, twitter_id, twitter_user_we_vote_id,  # TODO DALE To be built
                                    ballot_item_display_name,
                                    contest_office_we_vote_id,
                                    candidate_campaign_we_vote_id,
                                    politician_we_vote_id,
                                    contest_measure_we_vote_id,
                                    info_html,
                                    info_text,
                                    language,
                                    last_editor_we_vote_id,
                                    twitter_user_master_we_vote_id,
                                    more_info_url,
                                    more_info_credit,
                                    google_civic_election_id
                                    ):

        # TODO DALE Remove voter.twitter_id value
        # Does a twitter_user entry already exist?
        twitter_user_manager = TwitterUserManager()
        results = twitter_user_manager.retrieve_twitter_user(twitter_id, twitter_user_we_vote_id,
                                                         contest_office_we_vote_id,
                                                         candidate_campaign_we_vote_id,
                                                         politician_we_vote_id,
                                                         contest_measure_we_vote_id)

        twitter_user_on_stage_found = False
        twitter_user_on_stage_id = 0
        twitter_user_on_stage = TwitterUser()
        if results['twitter_user_found']:
            twitter_user_on_stage = results['twitter_user']

            # Update this twitter_user entry with new values - we do not delete because we might be able to use
            # noinspection PyBroadException
            try:
                # Figure out if the update is a change to a master entry
                if positive_value_exists(twitter_user_master_we_vote_id):
                    uses_master_entry = True
                elif (info_html is not False) or (info_text is not False) or (more_info_url is not False):
                    uses_master_entry = False
                elif positive_value_exists(twitter_user_on_stage.info_textx) or \
                        positive_value_exists(twitter_user_on_stage.info_html) or \
                        positive_value_exists(twitter_user_on_stage.more_info_url):
                    uses_master_entry = False
                elif positive_value_exists(twitter_user_on_stage.twitter_user_master_we_vote_id):
                    uses_master_entry = True
                else:
                    uses_master_entry = True

                if ballot_item_display_name is not False:
                    twitter_user_on_stage.ballot_item_display_name = ballot_item_display_name
                if language is not False:
                    twitter_user_on_stage.language = language
                if last_editor_we_vote_id is not False:
                    twitter_user_on_stage.last_editor_we_vote_id = last_editor_we_vote_id
                if contest_office_we_vote_id is not False:
                    twitter_user_on_stage.contest_office_we_vote_id = contest_office_we_vote_id
                if candidate_campaign_we_vote_id is not False:
                    twitter_user_on_stage.candidate_campaign_we_vote_id = candidate_campaign_we_vote_id
                if politician_we_vote_id is not False:
                    twitter_user_on_stage.politician_we_vote_id = politician_we_vote_id
                if contest_measure_we_vote_id is not False:
                    twitter_user_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                if google_civic_election_id is not False:
                    twitter_user_on_stage.google_civic_election_id = google_civic_election_id
                if uses_master_entry:
                    if twitter_user_master_we_vote_id is not False:
                        twitter_user_on_stage.twitter_user_master_we_vote_id = twitter_user_master_we_vote_id
                    # Clear out unique entry values
                    twitter_user_on_stage.info_text = ""
                    twitter_user_on_stage.info_html = ""
                    twitter_user_on_stage.more_info_url = ""
                else:
                    # If here, this is NOT a master entry
                    if info_text is not False:
                        twitter_user_on_stage.info_text = info_text
                    if info_html is not False:
                        twitter_user_on_stage.info_html = info_html
                    if more_info_url is not False:
                        twitter_user_on_stage.more_info_url = more_info_url
                    if more_info_credit is not False:
                        twitter_user_on_stage.more_info_credit = more_info_credit
                    # Clear out master entry value
                    twitter_user_on_stage.twitter_user_master_we_vote_id = ""
                if google_civic_election_id is not False:
                    twitter_user_on_stage.google_civic_election_id = google_civic_election_id
                # We don't need to update date_last_changed here because set set auto_now=True in the field
                twitter_user_on_stage.save()
                twitter_user_on_stage_id = twitter_user_on_stage.id
                twitter_user_on_stage_found = True
                status = 'TWITTER_USER_UPDATED'
            except Exception as e:
                status = 'FAILED_TO_UPDATE_TWITTER_USER'
        elif results['MultipleObjectsReturned']:
            status = 'TWITTER_USER MultipleObjectsReturned'
        elif results['DoesNotExist']:
            try:
                # Create new twitter_user entry
                if ballot_item_display_name is False:
                    ballot_item_display_name = ""
                if last_editor_we_vote_id is False:
                    last_editor_we_vote_id = ""
                if contest_office_we_vote_id is False:
                    contest_office_we_vote_id = ""
                if candidate_campaign_we_vote_id is False:
                    candidate_campaign_we_vote_id = ""
                if politician_we_vote_id is False:
                    politician_we_vote_id = ""
                if contest_measure_we_vote_id is False:
                    contest_measure_we_vote_id = ""
                if google_civic_election_id is False:
                    google_civic_election_id = 0
                # Master related data
                if twitter_user_master_we_vote_id is False:
                    twitter_user_master_we_vote_id = ""
                # Unique related data
                if info_html is False:
                    info_html = ""
                if info_text is False:
                    info_text = ""
                if more_info_url is False:
                    more_info_url = ""
                if more_info_credit is False:
                    more_info_credit = None
                twitter_user_on_stage = TwitterUser(
                    ballot_item_display_name=ballot_item_display_name,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                    politician_we_vote_id=politician_we_vote_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    info_html=info_html,
                    info_text=info_text,
                    language=language,
                    last_editor_we_vote_id=last_editor_we_vote_id,
                    twitter_user_master_we_vote_id=twitter_user_master_we_vote_id,
                    more_info_url=more_info_url,
                    more_info_credit=more_info_credit,
                    google_civic_election_id=google_civic_election_id
                    # We don't need to update last_updated here because set set auto_now=True in the field
                )
                twitter_user_on_stage.save()
                twitter_user_on_stage_id = twitter_user_on_stage.id
                twitter_user_on_stage_found = True
                status = 'CREATED_TWITTER_USER'
            except Exception as e:
                status = 'FAILED_TO_CREATE_NEW_TWITTER_USER'
        else:
            status = results['status']

        results = {
            'success':            True if twitter_user_on_stage_found else False,
            'status':             status,
            'twitter_user_found':   twitter_user_on_stage_found,
            'twitter_id':      twitter_user_on_stage_id,
            'twitter_user':         twitter_user_on_stage,
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
    Other Twitter handles that I follow, from the perspective of handle_of_me
    """
    handle_of_me = models.CharField(max_length=15, verbose_name='from this twitter handle\'s perspective...')
    handle_i_follow = models.CharField(max_length=15, verbose_name='twitter handle being followed')


# This is a we vote copy (for speed) of Twitter handles that follow me. We should have self-healing scripts that set up
#  entries in TwitterWhoIFollow for everyone following someone in the We Vote network, so this table could be flushed
#  and rebuilt at any time
class TwitterWhoFollowMe(models.Model):
    handle_of_me = models.CharField(max_length=15, verbose_name='from this twitter handle\'s perspective...')
    handle_that_follows_me = models.CharField(max_length=15, verbose_name='twitter handle of this tweet\'s author')
