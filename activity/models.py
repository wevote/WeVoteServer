# activity/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from datetime import timedelta
import json
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_activity_notice_seed_integer, \
    fetch_next_we_vote_id_activity_comment_integer, fetch_next_we_vote_id_activity_post_integer, \
    fetch_site_unique_id_prefix

# Kind of Seeds (value should not exceed 50 chars)
NOTICE_ACTIVITY_POST_SEED = 'NOTICE_ACTIVITY_POST_SEED'
NOTICE_CAMPAIGNX_NEWS_ITEM_SEED = 'NOTICE_CAMPAIGNX_NEWS_ITEM_SEED'
NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED = 'NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED'
NOTICE_FRIEND_ENDORSEMENTS_SEED = 'NOTICE_FRIEND_ENDORSEMENTS_SEED'
NOTICE_VOTER_DAILY_SUMMARY_SEED = 'NOTICE_VOTER_DAILY_SUMMARY_SEED'  # Activity that touches each voter, for each day

# Kind of Notices (value should not exceed 50 chars)
NOTICE_CAMPAIGNX_FRIEND_HAS_SUPPORTED = 'NOTICE_CAMPAIGNX_FRIEND_HAS_SUPPORTED'
NOTICE_CAMPAIGNX_NEWS_ITEM = 'NOTICE_CAMPAIGNX_NEWS_ITEM'
NOTICE_CAMPAIGNX_NEWS_ITEM_AUTHORED = 'NOTICE_CAMPAIGNX_NEWS_ITEM_AUTHORED'
NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE = 'NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE'
NOTICE_FRIEND_ACTIVITY_POSTS = 'NOTICE_FRIEND_ACTIVITY_POSTS'  # Notice shown in header menu, no email sent
NOTICE_FRIEND_ENDORSEMENTS = 'NOTICE_FRIEND_ENDORSEMENTS'
NOTICE_VOTER_DAILY_SUMMARY = 'NOTICE_VOTER_DAILY_SUMMARY'  # Email sent, not shown in header menu

FRIENDS_ONLY = 'FRIENDS_ONLY'
SHOW_PUBLIC = 'SHOW_PUBLIC'


class ActivityComment(models.Model):
    """
    A voter-created comment on another item (like an ActivityPost)
    """
    # The ultimate parent of all comments
    parent_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    # The comment that is the parent of this comment (only used when a comment on a comment)
    parent_comment_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    commenter_name = models.CharField(max_length=255, default=None, null=True)
    commenter_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    commenter_twitter_followers_count = models.PositiveIntegerField(default=None, null=True)
    commenter_twitter_handle = models.CharField(max_length=255, default=None, null=True)
    commenter_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    commenter_profile_image_url_medium = models.TextField(blank=True, null=True)
    commenter_profile_image_url_tiny = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    deleted = models.BooleanField(default=False)
    statement_text = models.TextField(null=True, blank=True)
    visibility_is_public = models.BooleanField(default=False)
    we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=True, db_index=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_activity_comment_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "comment" = tells us this is a unique id for an ActivityPost
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}comment{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ActivityComment, self).save(*args, **kwargs)


class ActivityManager(models.Manager):

    def __unicode__(self):
        return "ActivityManager"

    def create_activity_notice(
            self,
            activity_notice_seed_id=0,
            activity_tidbit_we_vote_id='',
            campaignx_news_item_we_vote_id=None,
            campaignx_we_vote_id=None,
            date_of_notice=None,
            kind_of_notice=None,
            kind_of_seed=None,
            number_of_comments=0,
            number_of_likes=0,
            position_name_list_serialized=None,
            position_we_vote_id_list_serialized=None,
            recipient_voter_we_vote_id='',
            send_to_email=False,
            send_to_sms=False,
            speaker_name='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id='',
            speaker_profile_image_url_medium='',
            speaker_profile_image_url_tiny='',
            statement_subject=None,
            statement_text_preview=None):
        status = ''

        if not positive_value_exists(speaker_organization_we_vote_id):
            activity_notice = None
            results = {
                'success':                  False,
                'status':                   "ACTIVITY_NOTICE_MISSING_SPEAKER_ORG_ID ",
                'activity_notice_saved':    False,
                'activity_notice':          activity_notice,
            }
            return results

        try:
            new_positions_entered_count = 0
            if positive_value_exists(position_we_vote_id_list_serialized):
                position_we_vote_id_list = json.loads(position_we_vote_id_list_serialized)
                new_positions_entered_count += len(position_we_vote_id_list)
            activity_notice = ActivityNotice.objects.create(
                activity_notice_seed_id=activity_notice_seed_id,
                activity_tidbit_we_vote_id=activity_tidbit_we_vote_id,
                campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
                campaignx_we_vote_id=campaignx_we_vote_id,
                date_of_notice=date_of_notice,
                kind_of_notice=kind_of_notice,
                kind_of_seed=kind_of_seed,
                new_positions_entered_count=new_positions_entered_count,
                number_of_comments=number_of_comments,
                number_of_likes=number_of_likes,
                position_name_list_serialized=position_name_list_serialized,
                position_we_vote_id_list_serialized=position_we_vote_id_list_serialized,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                send_to_email=send_to_email,
                send_to_sms=send_to_sms,
                speaker_name=speaker_name,
                speaker_organization_we_vote_id=speaker_organization_we_vote_id,
                speaker_voter_we_vote_id=speaker_voter_we_vote_id,
                speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
                statement_subject=statement_subject,
                statement_text_preview=statement_text_preview,
            )
            activity_notice_saved = True
            success = True
            status += "ACTIVITY_NOTICE_CREATED "
        except Exception as e:
            activity_notice_saved = False
            activity_notice = None
            success = False
            status += "ACTIVITY_NOTICE_NOT_CREATED: " + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'activity_notice_saved':    activity_notice_saved,
            'activity_notice':          activity_notice,
        }
        return results

    def create_activity_notice_seed(
            self,
            activity_notices_created=False,
            activity_notices_scheduled=False,
            activity_tidbit_we_vote_ids_for_friends_serialized='',
            activity_tidbit_we_vote_ids_for_public_serialized='',
            campaignx_news_item_we_vote_id=None,
            campaignx_we_vote_id=None,
            date_of_notice=None,
            kind_of_seed=None,
            position_names_for_friends_serialized='',
            position_names_for_public_serialized='',
            position_we_vote_ids_for_friends_serialized='',
            position_we_vote_ids_for_public_serialized='',
            recipient_name=None,
            recipient_voter_we_vote_id=None,
            send_to_email=False,  # For VOTER_DAILY_SUMMARY
            send_to_sms=False,  # For VOTER_DAILY_SUMMARY
            speaker_name='',
            speaker_organization_we_vote_id='',
            speaker_organization_we_vote_ids_serialized=None,
            speaker_voter_we_vote_id='',
            speaker_voter_we_vote_ids_serialized=None,
            speaker_profile_image_url_medium='',
            speaker_profile_image_url_tiny='',
            statement_subject='',
            statement_text_preview=''):
        status = ''

        if not positive_value_exists(speaker_organization_we_vote_id):
            activity_notice_seed = None
            results = {
                'success':                      False,
                'status':                       "ACTIVITY_NOTICE_SEED_MISSING_SPEAKER ",
                'activity_notice_seed_saved':   False,
                'activity_notice_seed':         activity_notice_seed,
            }
            return results

        date_sent_to_email = None
        if positive_value_exists(send_to_email):
            date_sent_to_email = now()

        try:
            activity_notice_seed = ActivityNoticeSeed.objects.create(
                activity_notices_created=activity_notices_created,
                activity_notices_scheduled=activity_notices_scheduled,
                activity_tidbit_we_vote_ids_for_friends_serialized=activity_tidbit_we_vote_ids_for_friends_serialized,
                activity_tidbit_we_vote_ids_for_public_serialized=activity_tidbit_we_vote_ids_for_public_serialized,
                campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
                campaignx_we_vote_id=campaignx_we_vote_id,
                date_of_notice=date_of_notice,
                date_sent_to_email=date_sent_to_email,
                kind_of_seed=kind_of_seed,
                position_names_for_friends_serialized=position_names_for_friends_serialized,
                position_names_for_public_serialized=position_names_for_public_serialized,
                position_we_vote_ids_for_friends_serialized=position_we_vote_ids_for_friends_serialized,
                position_we_vote_ids_for_public_serialized=position_we_vote_ids_for_public_serialized,
                recipient_name=recipient_name,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                send_to_email=send_to_email,
                send_to_sms=send_to_sms,
                speaker_name=speaker_name,
                speaker_organization_we_vote_id=speaker_organization_we_vote_id,
                speaker_organization_we_vote_ids_serialized=speaker_organization_we_vote_ids_serialized,
                speaker_voter_we_vote_id=speaker_voter_we_vote_id,
                speaker_voter_we_vote_ids_serialized=speaker_voter_we_vote_ids_serialized,
                speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
                statement_subject=statement_subject,
                statement_text_preview=statement_text_preview,
            )
            activity_notice_seed_saved = True
            success = True
            status += "ACTIVITY_NOTICE_SEED_CREATED "
        except Exception as e:
            activity_notice_seed_saved = False
            activity_notice_seed = None
            success = False
            status += "ACTIVITY_NOTICE_SEED_NOT_CREATED: " + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_notice_seed_saved':   activity_notice_seed_saved,
            'activity_notice_seed':         activity_notice_seed,
        }
        return results

    def create_activity_post(
            self,
            sender_voter_we_vote_id,
            sender_voter_sms,
            recipient_voter_we_vote_id='',
            recipient_sms_we_vote_id='',
            recipient_voter_sms='',
            template_variables_in_json='',
            kind_of_sms_template=''):
        status = ""
        success = True

        try:
            activity_post = ActivityPost.objects.create(
                kind_of_sms_template=kind_of_sms_template,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                recipient_sms_we_vote_id=recipient_sms_we_vote_id,
                recipient_voter_sms=recipient_voter_sms,
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                sender_voter_sms=sender_voter_sms,
                template_variables_in_json=template_variables_in_json,
            )
            activity_post_saved = True
            success = True
            status += "SMS_DESCRIPTION_CREATED "
        except Exception as e:
            activity_post_saved = False
            activity_post = ActivityPost()
            success = False
            status += "SMS_DESCRIPTION_NOT_CREATED " + str(e) + ' '

        results = {
            'success':              success,
            'status':               status,
            'activity_post_saved':  activity_post_saved,
            'activity_post':        activity_post,
        }
        return results

    def fetch_activity_notice_count(
            self,
            activity_in_last_x_seconds=None,
            kind_of_notice='',
            recipient_voter_we_vote_id='',
            send_to_email=None,
            speaker_voter_we_vote_id='',
    ):
        """
        We use this to figure out how many prior notices have been emailed in a period of time
        :param activity_in_last_x_seconds:
        :param kind_of_notice:
        :param recipient_voter_we_vote_id:
        :param send_to_email:
        :param speaker_voter_we_vote_id:
        :return:
        """
        try:
            queryset = ActivityNotice.objects.using('readonly').all()
            queryset = queryset.filter(deleted=False)
            if activity_in_last_x_seconds is not None:
                activity_in_last_x_seconds = convert_to_int(activity_in_last_x_seconds)
                earliest_date_of_notice = now() - timedelta(seconds=activity_in_last_x_seconds)
                queryset = queryset.filter(date_of_notice__gte=earliest_date_of_notice)
            if positive_value_exists(kind_of_notice):
                queryset = queryset.filter(kind_of_notice=kind_of_notice)
            if positive_value_exists(recipient_voter_we_vote_id):
                queryset = queryset.filter(recipient_voter_we_vote_id=recipient_voter_we_vote_id)
            if send_to_email is not None:
                send_to_email = positive_value_exists(send_to_email)
                queryset = queryset.filter(send_to_email=send_to_email)
            if positive_value_exists(speaker_voter_we_vote_id):
                queryset = queryset.filter(speaker_voter_we_vote_id=speaker_voter_we_vote_id)

            activity_notice_count = queryset.count()
        except Exception as e:
            activity_notice_count = 0

        return activity_notice_count

    def fetch_number_of_comments(self, parent_we_vote_id='', parent_comment_we_vote_id=''):
        results = self.retrieve_number_of_comments(
            parent_we_vote_id=parent_we_vote_id,
            parent_comment_we_vote_id=parent_comment_we_vote_id)
        return results['number_of_comments']

    def retrieve_number_of_comments(self, parent_we_vote_id='', parent_comment_we_vote_id=''):
        """

        :param parent_we_vote_id:
        :param parent_comment_we_vote_id:
        :return:
        """
        status = ""
        success = True
        if not positive_value_exists(parent_we_vote_id) and not positive_value_exists(parent_comment_we_vote_id):
            success = False
            status += 'VALID_PARENT_OR_PARENT_COMMENT_WE_VOTE_ID_MISSING-NUMBER_OF_COMMENTS '
            results = {
                'success':                      success,
                'status':                       status,
                'parent_we_vote_id':            parent_we_vote_id,
                'parent_comment_we_vote_id':    parent_comment_we_vote_id,
                'number_of_comments':           0,
            }
            return results

        number_of_comments = 0
        try:
            if positive_value_exists(parent_comment_we_vote_id):
                queryset = ActivityComment.objects.using('readonly').all()
                queryset = queryset.filter(
                    parent_comment_we_vote_id__iexact=parent_comment_we_vote_id,
                    deleted=False
                )
            else:
                queryset = ActivityComment.objects.all()
                queryset = queryset.filter(
                    parent_we_vote_id__iexact=parent_we_vote_id,
                    deleted=False
                )
                # Don't retrieve entries where there is a value for parent_comment_we_vote_id
                queryset = queryset.filter(
                    Q(parent_comment_we_vote_id=None) | Q(parent_comment_we_vote_id=""))
            queryset = queryset.exclude(
                Q(parent_we_vote_id=None) | Q(parent_we_vote_id=""))
            number_of_comments = queryset.count()
        except Exception as e:
            success = False
            status += 'FAILED retrieve_number_of_comments ActivityComment: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'parent_we_vote_id':            parent_we_vote_id,
            'parent_comment_we_vote_id':    parent_comment_we_vote_id,
            'number_of_comments':           number_of_comments,
        }
        return results

    def retrieve_activity_comment_list(self, parent_we_vote_id='', parent_comment_we_vote_id=''):
        """

        :param parent_we_vote_id:
        :param parent_comment_we_vote_id:
        :return:
        """
        status = ""
        success = True
        if not positive_value_exists(parent_we_vote_id) and not positive_value_exists(parent_comment_we_vote_id):
            success = False
            status += 'VALID_PARENT_OR_PARENT_COMMENT_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
                'parent_we_vote_id':            parent_we_vote_id,
                'parent_comment_we_vote_id':    parent_comment_we_vote_id,
                'activity_comment_list_found':  False,
                'activity_comment_list':        [],
            }
            return results

        activity_comment_list = []
        try:
            if positive_value_exists(parent_comment_we_vote_id):
                queryset = ActivityComment.objects.all()
                queryset = queryset.filter(
                    parent_comment_we_vote_id__iexact=parent_comment_we_vote_id,
                    deleted=False
                )
            else:
                queryset = ActivityComment.objects.all()
                queryset = queryset.filter(
                    parent_we_vote_id__iexact=parent_we_vote_id,
                    deleted=False
                )
                # Don't retrieve entries where there is a value for parent_comment_we_vote_id
                queryset = queryset.filter(
                    Q(parent_comment_we_vote_id=None) | Q(parent_comment_we_vote_id=""))
            queryset = queryset.exclude(
                Q(parent_we_vote_id=None) | Q(parent_we_vote_id=""))
            queryset = queryset.order_by('-id')  # Put most recent at top of list
            activity_comment_list = list(queryset)

            if len(activity_comment_list):
                activity_comment_list_found = True
                status += 'ACTIVITY_COMMENT_LIST_RETRIEVED '
            else:
                activity_comment_list_found = False
                status += 'NO_ACTIVITY_COMMENT_LIST_RETRIEVED '
        except ActivityComment.DoesNotExist:
            # No data found. Not a problem.
            activity_comment_list_found = False
            status += 'NO_ACTIVITY_COMMENT_LIST_RETRIEVED_DoesNotExist '
            activity_comment_list = []
        except Exception as e:
            success = False
            activity_comment_list_found = False
            status += 'FAILED retrieve_activity_comment_list ActivityComment: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'parent_we_vote_id':            parent_we_vote_id,
            'parent_comment_we_vote_id': parent_comment_we_vote_id,
            'activity_comment_list_found':  activity_comment_list_found,
            'activity_comment_list':        activity_comment_list,
        }
        return results

    def retrieve_activity_notice_for_campaignx(
            self,
            campaignx_news_item_we_vote_id=None,
            campaignx_we_vote_id=None,
            kind_of_notice='',
            recipient_voter_we_vote_id='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id=''):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        activity_notice = None
        activity_notice_found = False
        activity_notice_id = 0
        status = ""

        try:
            query = ActivityNotice.objects.filter(
                campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
                campaignx_we_vote_id=campaignx_we_vote_id,
                deleted=False,
                kind_of_notice=kind_of_notice,
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
            )
            if positive_value_exists(speaker_organization_we_vote_id):
                query = query.filter(
                    speaker_organization_we_vote_id__iexact=speaker_organization_we_vote_id,
                )
                activity_notice = query.get()
                activity_notice_id = activity_notice.id
                activity_notice_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_FOUND_BY_ORG_WE_VOTE_ID "
            elif positive_value_exists(speaker_voter_we_vote_id):
                query = query.filter(
                    speaker_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                )
                activity_notice = query.get()
                activity_notice_id = activity_notice.id
                activity_notice_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_FOUND_BY_VOTER_WE_VOTE_ID "
            else:
                activity_notice = query.get()
                activity_notice_id = activity_notice.id
                activity_notice_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_FOUND "
        except ActivityNotice.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_recent_activity_notice_from_speaker_and_recipient: ' + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'activity_notice_found':    activity_notice_found,
            'activity_notice_id':       activity_notice_id,
            'activity_notice':          activity_notice,
        }
        return results

    def retrieve_activity_notice_seed_list(
            self,
            notices_to_be_created=False):
        status = ""

        activity_notice_seed_list = []
        try:
            queryset = ActivityNoticeSeed.objects.all()
            queryset = queryset.filter(deleted=False)
            if positive_value_exists(notices_to_be_created):
                queryset = queryset.filter(activity_notices_created=False)

            queryset = queryset.order_by('-id')  # Put most recent at top of list
            activity_notice_seed_list = list(queryset)

            if len(activity_notice_seed_list):
                success = True
                activity_notice_seed_list_found = True
                status += 'ACTIVITY_NOTICE_SEED_LIST_RETRIEVED '
            else:
                success = True
                activity_notice_seed_list_found = False
                status += 'NO_ACTIVITY_NOTICE_SEED_LIST_RETRIEVED '
        except Exception as e:
            success = False
            activity_notice_seed_list_found = False
            status += 'FAILED retrieve_activity_notice_seed_list ActivityNoticeSeed ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'activity_notice_seed_list_found':  activity_notice_seed_list_found,
            'activity_notice_seed_list':        activity_notice_seed_list,
        }
        return results

    def retrieve_activity_notice_list(
            self,
            activity_notice_seed_id=0,
            to_be_sent_to_email=False,
            to_be_sent_to_sms=False,
            retrieve_count_limit=0,
            activity_notice_id_already_reviewed_list=[]):
        status = ""

        activity_notice_list = []
        try:
            queryset = ActivityNotice.objects.all()
            queryset = queryset.filter(deleted=False)
            if positive_value_exists(activity_notice_seed_id):
                queryset = queryset.filter(activity_notice_seed_id=activity_notice_seed_id)
            if positive_value_exists(to_be_sent_to_email):
                queryset = queryset.filter(send_to_email=True)
                queryset = queryset.filter(scheduled_to_email=False)
                queryset = queryset.filter(sent_to_email=False)
            elif positive_value_exists(to_be_sent_to_sms):
                queryset = queryset.filter(send_to_sms=True)
                queryset = queryset.filter(scheduled_to_sms=False)
                queryset = queryset.filter(sent_to_sms=False)
            if activity_notice_id_already_reviewed_list and len(activity_notice_id_already_reviewed_list) > 0:
                queryset = queryset.exclude(id__in=activity_notice_id_already_reviewed_list)

            queryset = queryset.order_by('-id')  # Put most recent at top of list
            if positive_value_exists(retrieve_count_limit):
                activity_notice_list = queryset[:retrieve_count_limit]
            else:
                activity_notice_list = list(queryset)

            if len(activity_notice_list):
                success = True
                activity_notice_list_found = True
                status += 'ACTIVITY_NOTICE_LIST_RETRIEVED '
            else:
                success = True
                activity_notice_list_found = False
                status += 'NO_ACTIVITY_NOTICE_LIST_RETRIEVED '
        except Exception as e:
            success = False
            activity_notice_list_found = False
            status += 'FAILED retrieve_activity_notice_list: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_notice_list_found':   activity_notice_list_found,
            'activity_notice_list':         activity_notice_list,
        }
        return results

    def retrieve_recent_activity_notice_seed_from_listener(
            self,
            kind_of_seed='',
            recipient_voter_we_vote_id=''):
        """

        :param kind_of_seed:
        :param recipient_voter_we_vote_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        activity_notice_seed_found = False
        activity_notice_seed = None
        activity_notice_seed_id = 0
        status = ""

        lifespan_of_seed_in_seconds = get_lifespan_of_seed(kind_of_seed)  # In seconds
        earliest_date_of_notice = now() - timedelta(seconds=lifespan_of_seed_in_seconds)

        try:
            if positive_value_exists(recipient_voter_we_vote_id):
                activity_notice_seed = ActivityNoticeSeed.objects.get(
                    date_of_notice__gte=earliest_date_of_notice,
                    deleted=False,
                    kind_of_seed=kind_of_seed,
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                )
                activity_notice_seed_id = activity_notice_seed.id
                activity_notice_seed_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_FOUND_BY_LISTENER_VOTER_WE_VOTE_ID "
            else:
                activity_notice_seed_found = False
                success = False
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_LISTENER_VOTER_WE_VOTE_ID_MISSING "
        except ActivityNoticeSeed.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_recent_activity_notice_seed_from_listener ActivityNoticeSeed: ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'activity_notice_seed_found':       activity_notice_seed_found,
            'activity_notice_seed_id':          activity_notice_seed_id,
            'activity_notice_seed':             activity_notice_seed,
        }
        return results

    def retrieve_recent_activity_notice_from_speaker_and_recipient(
            self,
            activity_notice_seed_id=0,
            campaignx_we_vote_id=None,
            kind_of_notice='',
            recipient_voter_we_vote_id='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id=''):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        activity_notice = None
        activity_notice_found = False
        activity_notice_id = 0
        status = ""

        try:
            if positive_value_exists(speaker_organization_we_vote_id):
                activity_notice = ActivityNotice.objects.get(
                    activity_notice_seed_id=activity_notice_seed_id,
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    deleted=False,
                    kind_of_notice=kind_of_notice,
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                    speaker_organization_we_vote_id__iexact=speaker_organization_we_vote_id,
                )
                activity_notice_id = activity_notice.id
                activity_notice_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_FOUND_BY_ORG_WE_VOTE_ID "
            elif positive_value_exists(speaker_voter_we_vote_id):
                activity_notice = ActivityNotice.objects.get(
                    activity_notice_seed_id=activity_notice_seed_id,
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    deleted=False,
                    kind_of_notice=kind_of_notice,
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                    speaker_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                )
                activity_notice_id = activity_notice.id
                activity_notice_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_FOUND_BY_VOTER_WE_VOTE_ID "
            else:
                activity_notice_found = False
                success = False
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_VARIABLES_MISSING "
        except ActivityNotice.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_recent_activity_notice_from_speaker_and_recipient: ' + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'activity_notice_found':    activity_notice_found,
            'activity_notice_id':       activity_notice_id,
            'activity_notice':          activity_notice,
        }
        return results

    def retrieve_activity_notice_seed(
            self,
            campaignx_news_item_we_vote_id=None,
            campaignx_we_vote_id=None,
            kind_of_seed=''):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        activity_notice_seed_found = False
        activity_notice_seed = None
        activity_notice_seed_id = 0
        status = ""

        try:
            if positive_value_exists(campaignx_news_item_we_vote_id):
                activity_notice_seed = ActivityNoticeSeed.objects.get(
                    campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    deleted=False,
                    kind_of_seed=kind_of_seed,
                )
                activity_notice_seed_id = activity_notice_seed.id
                activity_notice_seed_found = True
                success = True
                status += "RETRIEVE_ACTIVITY_NOTICE_SEED_FOUND "
            else:
                activity_notice_seed_found = False
                success = False
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_VARIABLES_MISSING "
        except ActivityNoticeSeed.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_activity_notice_seed ActivityNoticeSeed: ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'activity_notice_seed_found':       activity_notice_seed_found,
            'activity_notice_seed_id':          activity_notice_seed_id,
            'activity_notice_seed':             activity_notice_seed,
        }
        return results

    def retrieve_recent_activity_notice_seed_from_speaker(
            self,
            campaignx_we_vote_id=None,
            kind_of_seed='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id=''):
        """

        :param campaignx_we_vote_id:
        :param kind_of_seed:
        :param speaker_organization_we_vote_id:
        :param speaker_voter_we_vote_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        activity_notice_seed_found = False
        activity_notice_seed = None
        activity_notice_seed_id = 0
        status = ""

        lifespan_of_seed_in_seconds = get_lifespan_of_seed(kind_of_seed)  # In seconds
        earliest_date_of_notice = now() - timedelta(seconds=lifespan_of_seed_in_seconds)

        try:
            if positive_value_exists(speaker_organization_we_vote_id):
                activity_notice_seed = ActivityNoticeSeed.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    date_of_notice__gte=earliest_date_of_notice,
                    deleted=False,
                    kind_of_seed=kind_of_seed,
                    speaker_organization_we_vote_id__iexact=speaker_organization_we_vote_id,
                )
                activity_notice_seed_id = activity_notice_seed.id
                activity_notice_seed_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_FOUND_BY_ORG_WE_VOTE_ID "
            elif positive_value_exists(speaker_voter_we_vote_id):
                activity_notice_seed = ActivityNoticeSeed.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    date_of_notice__gte=earliest_date_of_notice,
                    deleted=False,
                    kind_of_seed=kind_of_seed,
                    speaker_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                )
                activity_notice_seed_id = activity_notice_seed.id
                activity_notice_seed_found = True
                success = True
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_FOUND_BY_VOTER_WE_VOTE_ID "
            else:
                activity_notice_seed_found = False
                success = False
                status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_VARIABLES_MISSING "
        except ActivityNoticeSeed.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_RECENT_ACTIVITY_NOTICE_SEED_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_recent_activity_notice_seed_from_speaker ActivityNoticeSeed: ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'activity_notice_seed_found':       activity_notice_seed_found,
            'activity_notice_seed_id':          activity_notice_seed_id,
            'activity_notice_seed':             activity_notice_seed,
        }
        return results

    def retrieve_activity_notice_list_for_recipient(self, recipient_voter_we_vote_id=''):
        """

        :param recipient_voter_we_vote_id:
        :return:
        """
        status = ""
        if not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
                'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
                'activity_notice_list_found':   False,
                'activity_notice_list':         [],
            }
            return results

        activity_notice_list = []
        try:
            queryset = ActivityNotice.objects.all()
            queryset = queryset.filter(
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                deleted=False
            )
            queryset = queryset.exclude(
                Q(recipient_voter_we_vote_id=None) | Q(recipient_voter_we_vote_id=""))
            queryset = queryset.order_by('-id')  # Put most recent at top of list
            activity_notice_list = queryset[:30]

            if len(activity_notice_list):
                success = True
                activity_notice_list_found = True
                status += 'ACTIVITY_NOTICE_LIST_RETRIEVED '
            else:
                success = True
                activity_notice_list_found = False
                status += 'NO_ACTIVITY_NOTICE_LIST_RETRIEVED '
        except ActivityNotice.DoesNotExist:
            # No data found. Not a problem.
            success = True
            activity_notice_list_found = False
            status += 'NO_ACTIVITY_NOTICE_LIST_RETRIEVED_DoesNotExist '
            activity_notice_list = []
        except Exception as e:
            success = False
            activity_notice_list_found = False
            status += 'FAILED retrieve_voter_activity_notice_list ActivityNotice ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_notice_list_found':   activity_notice_list_found,
            'activity_notice_list':         activity_notice_list,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
        }
        return results

    def retrieve_activity_notice_seed_list_for_recipient(
            self,
            recipient_voter_we_vote_id='',
            kind_of_seed_list=None,
            limit_to_activity_tidbit_we_vote_id_list=[]):
        """

        :param recipient_voter_we_vote_id:
        :param kind_of_seed_list:
        :param limit_to_activity_tidbit_we_vote_id_list:
        :return:
        """
        status = ""
        if not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                          success,
                'status':                           status,
                'recipient_voter_we_vote_id':       recipient_voter_we_vote_id,
                'activity_notice_seed_list_found':  False,
                'activity_notice_seed_list':        [],
                'voter_friend_we_vote_id_list':     [],
            }
            return results

        activity_notice_seed_list = []
        voter_friend_we_vote_id_list = []
        voter_friend_we_vote_id_list.append(recipient_voter_we_vote_id)
        from friend.models import FriendManager
        friend_manager = FriendManager()
        friend_results = friend_manager.retrieve_friends_we_vote_id_list(recipient_voter_we_vote_id)
        if friend_results['friends_we_vote_id_list_found']:
            friends_we_vote_id_list = friend_results['friends_we_vote_id_list']
            voter_friend_we_vote_id_list += friends_we_vote_id_list
        try:
            queryset = ActivityNoticeSeed.objects.all()
            queryset = queryset.filter(deleted=False)
            queryset = queryset.filter(speaker_voter_we_vote_id__in=voter_friend_we_vote_id_list)
            if limit_to_activity_tidbit_we_vote_id_list and len(limit_to_activity_tidbit_we_vote_id_list) > 0:
                queryset = queryset.filter(we_vote_id__in=limit_to_activity_tidbit_we_vote_id_list)
            if kind_of_seed_list and len(kind_of_seed_list) > 0:
                queryset = queryset.filter(kind_of_seed__in=kind_of_seed_list)
            queryset = queryset.exclude(
                Q(speaker_voter_we_vote_id=None) | Q(speaker_voter_we_vote_id=""))
            queryset = queryset.order_by('-id')  # Put most recent at top of list
            activity_notice_seed_list = queryset[:200]

            if len(activity_notice_seed_list):
                success = True
                activity_notice_seed_list_found = True
                status += 'ACTIVITY_NOTICE_SEED_LIST_RETRIEVED '
            else:
                success = True
                activity_notice_seed_list_found = False
                status += 'NO_ACTIVITY_NOTICE_SEED_LIST_RETRIEVED '
        except ActivityNoticeSeed.DoesNotExist:
            # No data found. Not a problem.
            success = True
            activity_notice_seed_list_found = False
            status += 'NO_ACTIVITY_NOTICE_SEED_LIST_RETRIEVED_DoesNotExist '
            activity_notice_seed_list = []
        except Exception as e:
            success = False
            activity_notice_seed_list_found = False
            status += 'FAILED retrieve_voter_activity_notice_seed_list: ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'recipient_voter_we_vote_id':       recipient_voter_we_vote_id,
            'activity_notice_seed_list_found':  activity_notice_seed_list_found,
            'activity_notice_seed_list':        activity_notice_seed_list,
            'voter_friend_we_vote_id_list':     voter_friend_we_vote_id_list,
        }
        return results

    def retrieve_next_activity_notice_seed_to_process(
            self,
            notices_to_be_created=False,
            notices_to_be_scheduled=False,
            notices_to_be_updated=False,
            to_be_added_to_voter_daily_summary=False,
            activity_notice_seed_id_already_reviewed_list=[]):
        status = ""

        activity_notice_seed = None
        try:
            queryset = ActivityNoticeSeed.objects.all()
            queryset = queryset.filter(deleted=False)
            if positive_value_exists(notices_to_be_created):
                queryset = queryset.filter(activity_notices_created=False)
                queryset = \
                    queryset.filter(kind_of_seed__in=[
                        NOTICE_ACTIVITY_POST_SEED,
                        NOTICE_CAMPAIGNX_NEWS_ITEM_SEED,
                        NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED,
                        NOTICE_FRIEND_ENDORSEMENTS_SEED
                    ])
            elif positive_value_exists(notices_to_be_scheduled):
                queryset = queryset.filter(activity_notices_scheduled=False)
                queryset = queryset.filter(
                    kind_of_seed__in=[
                        NOTICE_CAMPAIGNX_NEWS_ITEM_SEED,
                        NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED,
                        NOTICE_FRIEND_ENDORSEMENTS_SEED,
                        NOTICE_VOTER_DAILY_SUMMARY_SEED
                    ])
            elif positive_value_exists(notices_to_be_updated):
                queryset = queryset.filter(activity_notices_created=True)
                queryset = queryset.filter(date_of_notice_earlier_than_update_window=False)
                queryset = queryset.filter(
                    kind_of_seed__in=[
                        NOTICE_ACTIVITY_POST_SEED,
                        NOTICE_FRIEND_ENDORSEMENTS_SEED
                    ])
            elif positive_value_exists(to_be_added_to_voter_daily_summary):
                queryset = queryset.filter(added_to_voter_daily_summary=False)
                queryset = queryset.filter(
                    kind_of_seed__in=[
                        NOTICE_ACTIVITY_POST_SEED,
                        NOTICE_FRIEND_ENDORSEMENTS_SEED
                    ])
                # TODO Add: NOTICE_CAMPAIGNX_NEWS_ITEM_SEED, NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED
            if activity_notice_seed_id_already_reviewed_list and len(activity_notice_seed_id_already_reviewed_list) > 0:
                queryset = queryset.exclude(id__in=activity_notice_seed_id_already_reviewed_list)

            queryset = queryset.order_by('-id')  # Put most recent at top of list
            activity_notice_seed_list = queryset[:1]

            if len(activity_notice_seed_list):
                success = True
                activity_notice_seed = activity_notice_seed_list[0]
                activity_notice_seed_found = True
                status += 'ACTIVITY_NOTICE_SEED_RETRIEVED '
            else:
                success = True
                activity_notice_seed = None
                activity_notice_seed_found = False
                status += 'NO_ACTIVITY_NOTICE_SEED_RETRIEVED '
        except Exception as e:
            success = False
            activity_notice_seed_found = False
            status += 'FAILED retrieve_activity_notice_seed ActivityNoticeSeed: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_notice_seed_found':   activity_notice_seed_found,
            'activity_notice_seed':         activity_notice_seed,
        }
        return results

    def retrieve_activity_post_list(
            self,
            speaker_voter_we_vote_id_list=[],
            limit_to_visibility_is_friends_only=False,
            limit_to_visibility_is_public=False,
            since_date=None):
        """

        :param speaker_voter_we_vote_id_list:
        :param limit_to_visibility_is_friends_only:
        :param limit_to_visibility_is_public:
        :param since_date:
        :return:
        """
        status = ""
        if not speaker_voter_we_vote_id_list or len(speaker_voter_we_vote_id_list) == 0:
            success = False
            status += 'VALID_VOTER_WE_VOTE_IDS_MISSING '
            results = {
                'success':                          success,
                'status':                           status,
                'activity_post_list_found':  False,
                'activity_post_list':        [],
            }
            return results

        activity_post_list = []
        try:
            queryset = ActivityPost.objects.all()
            queryset = queryset.filter(
                speaker_voter_we_vote_id__in=speaker_voter_we_vote_id_list,
                deleted=False
            )
            if positive_value_exists(since_date):
                queryset = queryset.filter(date_created__gte=since_date)
            if positive_value_exists(limit_to_visibility_is_friends_only):
                queryset = queryset.filter(visibility_is_public=False)
            elif positive_value_exists(limit_to_visibility_is_public):
                queryset = queryset.filter(visibility_is_public=True)
            queryset = queryset.exclude(
                Q(speaker_voter_we_vote_id=None) | Q(speaker_voter_we_vote_id=""))
            queryset = queryset.order_by('-id')  # Put most recent ActivityPost at top of list
            activity_post_list = queryset[:200]

            if len(activity_post_list):
                success = True
                activity_post_list_found = True
                status += 'ACTIVITY_POST_LIST_RETRIEVED '
            else:
                success = True
                activity_post_list_found = False
                status += 'NO_ACTIVITY_POST_LIST_RETRIEVED '
        except ActivityPost.DoesNotExist:
            # No data found. Not a problem.
            success = True
            activity_post_list_found = False
            status += 'NO_ACTIVITY_POST_LIST_RETRIEVED_DoesNotExist '
            activity_post_list = []
        except Exception as e:
            success = False
            activity_post_list_found = False
            status += 'FAILED retrieve_activity_post_list: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_post_list_found':     activity_post_list_found,
            'activity_post_list':           activity_post_list,
        }
        return results

    def retrieve_activity_post_list_for_recipient(
            self,
            recipient_voter_we_vote_id='',
            limit_to_activity_tidbit_we_vote_id_list=[],
            voter_friend_we_vote_id_list=[]):
        """

        :param recipient_voter_we_vote_id:
        :param limit_to_activity_tidbit_we_vote_id_list:
        :param voter_friend_we_vote_id_list:
        :return:
        """
        status = ""
        if not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                          success,
                'status':                           status,
                'recipient_voter_we_vote_id':       recipient_voter_we_vote_id,
                'activity_post_list_found':  False,
                'activity_post_list':        [],
            }
            return results

        activity_post_list = []
        if not positive_value_exists(len(voter_friend_we_vote_id_list)):
            voter_friend_we_vote_id_list = []
            voter_friend_we_vote_id_list.append(recipient_voter_we_vote_id)
            from friend.models import FriendManager
            friend_manager = FriendManager()
            friend_results = friend_manager.retrieve_friends_we_vote_id_list(recipient_voter_we_vote_id)
            if friend_results['friends_we_vote_id_list_found']:
                friends_we_vote_id_list = friend_results['friends_we_vote_id_list']
                voter_friend_we_vote_id_list += friends_we_vote_id_list
        try:
            queryset = ActivityPost.objects.all()
            queryset = queryset.filter(deleted=False)
            if limit_to_activity_tidbit_we_vote_id_list and len(limit_to_activity_tidbit_we_vote_id_list) > 0:
                queryset = queryset.filter(we_vote_id__in=limit_to_activity_tidbit_we_vote_id_list)
                # Allow the public ActivityPosts to be found
                queryset = queryset.filter(
                    Q(speaker_voter_we_vote_id__in=voter_friend_we_vote_id_list) | Q(visibility_is_public=True))
            else:
                queryset = queryset.filter(speaker_voter_we_vote_id__in=voter_friend_we_vote_id_list)
            queryset = queryset.exclude(
                Q(speaker_voter_we_vote_id=None) | Q(speaker_voter_we_vote_id=""))
            queryset = queryset.order_by('-id')  # Put most recent ActivityPost at top of list
            activity_post_list = queryset[:200]

            if len(activity_post_list):
                success = True
                activity_post_list_found = True
                status += 'ACTIVITY_POST_LIST_FOR_RECIPIENT_RETRIEVED '
            else:
                success = True
                activity_post_list_found = False
                status += 'NO_ACTIVITY_POST_LIST_FOR_RECIPIENT_RETRIEVED '
        except ActivityPost.DoesNotExist:
            # No data found. Not a problem.
            success = True
            activity_post_list_found = False
            status += 'NO_ACTIVITY_POST_LIST_FOR_RECIPIENT_RETRIEVED_DoesNotExist '
            activity_post_list = []
        except Exception as e:
            success = False
            activity_post_list_found = False
            status += 'FAILED retrieve_activity_post_list_for_recipient: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
            'activity_post_list_found':     activity_post_list_found,
            'activity_post_list':           activity_post_list,
        }
        return results

    def update_activity_notice_list_in_bulk(
            self,
            recipient_voter_we_vote_id='',
            activity_notice_id_list=[],
            activity_notice_seen=False,
            activity_notice_clicked=False):
        status = ""
        if not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
                'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
                'activity_notice_list_updated': False,
            }
            return results

        try:
            if activity_notice_clicked and activity_notice_seen:
                ActivityNotice.objects.all().filter(
                    id__in=activity_notice_id_list,
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                    deleted=False
                ).update(
                    activity_notice_seen=True,
                    activity_notice_clicked=True)
            elif activity_notice_clicked:
                ActivityNotice.objects.all().filter(
                    id__in=activity_notice_id_list,
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                    deleted=False
                ).update(
                    activity_notice_clicked=True)
            elif activity_notice_seen:
                ActivityNotice.objects.all().filter(
                    id__in=activity_notice_id_list,
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                    deleted=False
                ).update(
                    activity_notice_seen=True)
            success = True
            activity_notice_list_updated = True
            status += 'ACTIVITY_NOTICE_LIST_UPDATED '
        except ActivityNotice.DoesNotExist:
            # No data found. Not a problem.
            success = True
            activity_notice_list_updated = False
            status += 'NO_ACTIVITY_NOTICE_LIST_ENTRIES_FOUND '
        except Exception as e:
            success = False
            activity_notice_list_updated = False
            status += 'FAILED update_activity_notice_list_in_bulk ActivityNotice ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
            'activity_notice_list_updated': activity_notice_list_updated,
        }
        return results

    def update_activity_notice_seed(self, activity_notice_seed_id, update_values):
        """
        :param activity_notice_seed_id:
        :param update_values:
        :return:
        """

        success = False
        status = ""
        activity_notice_seed_updated = False
        existing_entry = ''

        try:
            existing_entry = ActivityNoticeSeed.objects.get(id=activity_notice_seed_id)
            values_changed = False

            if existing_entry:
                # found the existing entry, update the values
                if 'date_of_notice' in update_values:
                    existing_entry.date_of_notice = update_values['ballotpedia_activity_notice_seed_id']
                    values_changed = True
                if 'deleted' in update_values:
                    existing_entry.deleted = update_values['deleted']
                    values_changed = True
                if 'kind_of_seed' in update_values:
                    existing_entry.kind_of_seed = update_values['kind_of_seed']
                    values_changed = True
                if 'position_names_for_friends_serialized' in update_values:
                    existing_entry.position_names_for_friends_serialized = \
                        update_values['position_names_for_friends_serialized']
                    values_changed = True
                if 'position_names_for_public_serialized' in update_values:
                    existing_entry.position_names_for_public_serialized = \
                        update_values['position_names_for_public_serialized']
                    values_changed = True
                if 'position_we_vote_ids_for_friends_serialized' in update_values:
                    existing_entry.position_we_vote_ids_for_friends_serialized = \
                        update_values['position_we_vote_ids_for_friends_serialized']
                    values_changed = True
                if 'position_we_vote_ids_for_public_serialized' in update_values:
                    existing_entry.position_we_vote_ids_for_public_serialized = \
                        update_values['position_we_vote_ids_for_public_serialized']
                    values_changed = True
                if 'speaker_name' in update_values:
                    existing_entry.speaker_name = update_values['speaker_name']
                    values_changed = True
                if 'speaker_organization_we_vote_id' in update_values:
                    existing_entry.speaker_organization_we_vote_id = update_values['speaker_organization_we_vote_id']
                    values_changed = True
                if 'speaker_voter_we_vote_id' in update_values:
                    existing_entry.speaker_voter_we_vote_id = update_values['speaker_voter_we_vote_id']
                    values_changed = True

                # now go ahead and save this entry (update)
                if values_changed:
                    existing_entry.save()
                    activity_notice_seed_updated = True
                    success = True
                    status += "ACTIVITY_NOTICE_SEED_UPDATED "
                else:
                    activity_notice_seed_updated = False
                    success = True
                    status += "ACTIVITY_NOTICE_SEED_NOT_UPDATED-NO_CHANGES "
        except Exception as e:
            success = False
            activity_notice_seed_updated = False
            status += "ACTIVITY_NOTICE_SEED_RETRIEVE_ERROR " + str(e) + ' '

        results = {
                'success':                      success,
                'status':                       status,
                'activity_notice_seed_updated': activity_notice_seed_updated,
                'updated_activity_notice_seed': existing_entry,
            }
        return results

    def update_or_create_activity_comment(
            self,
            activity_comment_we_vote_id='',
            updated_values={},
            commenter_voter_we_vote_id='',
    ):
        """
        Either update or create an ActivityComment.
        """
        activity_comment = None
        activity_comment_created = False
        activity_comment_found = False
        missing_variable = False
        status = ""

        statement_text = updated_values['statement_text'] if 'statement_text' in updated_values else ''

        if not commenter_voter_we_vote_id:
            missing_variable = True
            status += 'MISSING_VOTER_WE_VOTE_ID '
        if not positive_value_exists(activity_comment_we_vote_id) and not positive_value_exists(statement_text):
            missing_variable = True
            status += 'MISSING_BOTH_ID_AND_STATEMENT_TEXT '

        if missing_variable:
            success = False
            results = {
                'success':                  success,
                'status':                   status,
                'activity_comment':            activity_comment,
                'activity_comment_found':      activity_comment_found,
                'activity_comment_created':    activity_comment_created,
            }
            return results

        if positive_value_exists(activity_comment_we_vote_id):
            try:
                activity_comment = ActivityComment.objects.get(
                    we_vote_id=activity_comment_we_vote_id,
                    commenter_voter_we_vote_id=updated_values['commenter_voter_we_vote_id'])
                activity_comment_found = True
                # Instead of manually mapping them above, we do it this way for flexibility
                for key, value in updated_values.items():
                    setattr(activity_comment, key, value)
                activity_comment.save()
                success = True
                status += 'ACTIVITY_COMMENT_UPDATED '
            except Exception as e:
                success = False
                status += "ACTIVITY_COMMENT_UPDATE_FAILURE: " + str(e) + " "
        else:
            try:
                activity_comment = ActivityComment.objects.create(
                    date_created=now(),
                    commenter_voter_we_vote_id=updated_values['commenter_voter_we_vote_id'])
                activity_comment_created = True
                # Instead of manually mapping them above, we do it this way for flexibility
                for key, value in updated_values.items():
                    setattr(activity_comment, key, value)
                activity_comment.save()
                activity_comment_found = True
                success = True
                status += 'ACTIVITY_COMMENT_CREATED '
            except Exception as e:
                success = False
                status += "ACTIVITY_COMMENT_CREATE_FAILURE: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'activity_comment':         activity_comment,
            'activity_comment_found':   activity_comment_found,
            'activity_comment_created': activity_comment_created,
        }
        return results

    def update_or_create_activity_post(
            self,
            activity_post_we_vote_id='',
            updated_values={},
            speaker_voter_we_vote_id='',
    ):
        """
        Either update or create an ActivityPost.
        """
        activity_post = None
        activity_post_created = False
        activity_post_found = False
        missing_variable = False
        status = ""

        statement_text = updated_values['statement_text'] if 'statement_text' in updated_values else ''

        if not speaker_voter_we_vote_id:
            missing_variable = True
            status += 'MISSING_VOTER_WE_VOTE_ID '
        if not positive_value_exists(activity_post_we_vote_id) and not positive_value_exists(statement_text):
            missing_variable = True
            status += 'MISSING_BOTH_ID_AND_STATEMENT_TEXT '

        if missing_variable:
            success = False
            results = {
                'success':                  success,
                'status':                   status,
                'activity_post':            activity_post,
                'activity_post_found':      activity_post_found,
                'activity_post_created':    activity_post_created,
            }
            return results

        if positive_value_exists(activity_post_we_vote_id):
            try:
                activity_post = ActivityPost.objects.get(
                    we_vote_id=activity_post_we_vote_id,
                    speaker_voter_we_vote_id=updated_values['speaker_voter_we_vote_id'])
                activity_post_found = True
                # Instead of manually mapping them above, we do it this way for flexibility
                for key, value in updated_values.items():
                    setattr(activity_post, key, value)
                activity_post.save()
                success = True
                status += 'ACTIVITY_POST_UPDATED '
            except Exception as e:
                success = False
                status += "ACTIVITY_POST_UPDATE_FAILURE: " + str(e) + " "
        else:
            try:
                activity_post = ActivityPost.objects.create(
                    date_created=now(),
                    speaker_voter_we_vote_id=updated_values['speaker_voter_we_vote_id'])
                activity_post_created = True
                # Instead of manually mapping them above, we do it this way for flexibility
                for key, value in updated_values.items():
                    setattr(activity_post, key, value)
                activity_post.save()
                activity_post_found = True
                success = True
                status += 'ACTIVITY_POST_CREATED '
            except Exception as e:
                success = False
                status += "ACTIVITY_POST_CREATE_FAILURE: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'activity_post':            activity_post,
            'activity_post_found':      activity_post_found,
            'activity_post_created':    activity_post_created,
        }
        return results

    def update_speaker_name_in_bulk(
            self,
            speaker_voter_we_vote_id='',
            speaker_name=''):
        status = ""
        success = True
        if not positive_value_exists(speaker_voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
            }
            return results

        if not positive_value_exists(speaker_name):
            success = False
            status += 'SPEAKER_NAME_MUST_EXIST '
            results = {
                'success':                      success,
                'status':                       status,
            }
            return results

        try:
            updated_count = ActivityComment.objects.all().filter(
                commenter_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                deleted=False
            ).update(
                commenter_name=speaker_name)
            status += 'ACTIVITY_COMMENTS_UPDATED: (' + str(updated_count) + ') '
        except ActivityComment.DoesNotExist:
            # No data found. Not a problem.
            status += 'NO_ACTIVITY_COMMENTS_FOUND '
        except Exception as e:
            success = False
            status += 'FAILED update_speaker_name_in_bulk ActivityComment ' + str(e) + ' '

        try:
            updated_count = ActivityNotice.objects.all().filter(
                speaker_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                deleted=False
            ).update(
                speaker_name=speaker_name)
            status += 'ACTIVITY_NOTICES_UPDATED: (' + str(updated_count) + ') '
        except ActivityNotice.DoesNotExist:
            # No data found. Not a problem.
            status += 'NO_ACTIVITY_NOTICES_FOUND '
        except Exception as e:
            success = False
            status += 'FAILED update_speaker_name_in_bulk ActivityNotice ' + str(e) + ' '

        try:
            updated_seed_count1 = ActivityNoticeSeed.objects.all().filter(
                speaker_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                deleted=False
            ).update(
                speaker_name=speaker_name)
            updated_seed_count2 = ActivityNoticeSeed.objects.all().filter(
                recipient_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                deleted=False
            ).update(
                recipient_name=speaker_name)
            status += 'ACTIVITY_NOTICE_SEEDS_UPDATED: ' \
                      '(' + str(updated_seed_count1) + '/' + str(updated_seed_count2) + ') '
        except ActivityNoticeSeed.DoesNotExist:
            # No data found. Not a problem.
            status += 'NO_ACTIVITY_NOTICE_SEEDS_FOUND '
        except Exception as e:
            success = False
            status += 'FAILED update_speaker_name_in_bulk ActivityNoticeSeed ' + str(e) + ' '

        try:
            updated_count = ActivityPost.objects.all().filter(
                speaker_voter_we_vote_id__iexact=speaker_voter_we_vote_id,
                deleted=False
            ).update(
                speaker_name=speaker_name)
            status += 'ACTIVITY_POSTS_UPDATED: (' + str(updated_count) + ') '
        except ActivityPost.DoesNotExist:
            # No data found. Not a problem.
            status += 'NO_ACTIVITY_POSTS_FOUND '
        except Exception as e:
            success = False
            status += 'FAILED update_speaker_name_in_bulk ActivityPost ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
        }
        return results


class ActivityNotice(models.Model):
    """
    This is a notice for the notification drop-down menu, for one person
    """
    activity_notice_seed_id = models.PositiveIntegerField(default=None, null=True)
    activity_tidbit_we_vote_id = models.CharField(max_length=255, default=None, null=True)  # subject of notice
    campaignx_news_item_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    campaignx_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    date_of_notice = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True)
    activity_notice_clicked = models.BooleanField(default=False)
    activity_notice_seen = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    kind_of_notice = models.CharField(max_length=50, default=None, null=True)
    kind_of_seed = models.CharField(max_length=50, default=None, null=True)
    new_positions_entered_count = models.PositiveIntegerField(default=None, null=True)
    number_of_comments = models.PositiveIntegerField(default=None, null=True)
    number_of_likes = models.PositiveIntegerField(default=None, null=True)
    position_name_list_serialized = models.TextField(default=None, null=True)
    position_we_vote_id_list_serialized = models.TextField(default=None, null=True)
    speaker_name = models.CharField(max_length=255, default=None, null=True)
    speaker_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    recipient_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    is_in_app = models.BooleanField(default=False)
    # Track Email send progress
    send_to_email = models.BooleanField(default=False)
    scheduled_to_email = models.BooleanField(default=False)
    sent_to_email = models.BooleanField(default=False)
    # Track SMS send progress
    send_to_sms = models.BooleanField(default=False)
    scheduled_to_sms = models.BooleanField(default=False)
    sent_to_sms = models.BooleanField(default=False)
    speaker_profile_image_url_medium = models.TextField(blank=True, null=True)
    speaker_profile_image_url_tiny = models.TextField(blank=True, null=True)
    statement_subject = models.CharField(max_length=255, default=None, null=True)
    statement_text_preview = models.CharField(max_length=255, default=None, null=True)


class ActivityNoticeSeed(models.Model):
    """
    This is the "seed" for a notice for the notification drop-down menu, which is used before we "distribute" it
    out to an ActivityNotice, which gets shown to an individual voter.
    """
    activity_notices_created = models.BooleanField(default=False)
    activity_tidbit_we_vote_ids_for_friends_serialized = models.TextField(default=None, null=True)
    activity_tidbit_we_vote_ids_for_public_serialized = models.TextField(default=None, null=True)
    date_of_notice_earlier_than_update_window = models.BooleanField(default=False)
    activity_notices_scheduled = models.BooleanField(default=False)
    added_to_voter_daily_summary = models.BooleanField(default=False)
    campaignx_news_item_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    campaignx_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    date_of_notice = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True)
    date_sent_to_email = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)
    kind_of_seed = models.CharField(max_length=50, default=None, null=True)
    # Positions that were changed: NOTICE_FRIEND_ENDORSEMENTS
    position_names_for_friends_serialized = models.TextField(default=None, null=True)
    position_names_for_public_serialized = models.TextField(default=None, null=True)
    position_we_vote_ids_for_friends_serialized = models.TextField(default=None, null=True)
    position_we_vote_ids_for_public_serialized = models.TextField(default=None, null=True)
    # Voter receiving the daily summary: NOTICE_VOTER_DAILY_SUMMARY
    recipient_name = models.CharField(max_length=255, default=None, null=True)
    recipient_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_voter_we_vote_ids_serialized = models.TextField(default=None, null=True)
    speaker_organization_we_vote_ids_serialized = models.TextField(default=None, null=True)
    # Track Email send progress for NOTICE_VOTER_DAILY_SUMMARY_SEED
    send_to_email = models.BooleanField(default=False)
    scheduled_to_email = models.BooleanField(default=False)
    sent_to_email = models.BooleanField(default=False)
    # Track SMS send progress for NOTICE_VOTER_DAILY_SUMMARY_SEED
    send_to_sms = models.BooleanField(default=False)
    scheduled_to_sms = models.BooleanField(default=False)
    sent_to_sms = models.BooleanField(default=False)
    # Voter who took the action: NOTICE_ACTIVITY_POST_SEED, NOTICE_FRIEND_ENDORSEMENTS_SEED
    speaker_name = models.CharField(max_length=255, default=None, null=True)
    speaker_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_profile_image_url_medium = models.TextField(blank=True, null=True)
    speaker_profile_image_url_tiny = models.TextField(blank=True, null=True)
    speaker_twitter_handle = models.CharField(max_length=255, null=True, unique=False, default=None)
    speaker_twitter_followers_count = models.IntegerField(default=0)
    statement_subject = models.CharField(max_length=255, default=None, null=True)
    statement_text_preview = models.CharField(max_length=255, default=None, null=True)
    # we_vote_id of this SEED
    we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_activity_notice_seed_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "actseed" = tells us this is a unique id for an ActivityNoticeSeed
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}actseed{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ActivityNoticeSeed, self).save(*args, **kwargs)


class ActivityPost(models.Model):
    """
    A voter-created post for the activity list
    """
    date_created = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    deleted = models.BooleanField(default=False)
    speaker_name = models.CharField(max_length=255, default=None, null=True)
    speaker_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_twitter_followers_count = models.PositiveIntegerField(default=None, null=True)
    speaker_twitter_handle = models.CharField(max_length=255, default=None, null=True)
    speaker_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_profile_image_url_medium = models.TextField(blank=True, null=True)
    speaker_profile_image_url_tiny = models.TextField(blank=True, null=True)
    statement_text = models.TextField(null=True, blank=True)
    visibility_is_public = models.BooleanField(default=False)
    we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_activity_post_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "post" = tells us this is a unique id for an ActivityPost
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}post{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ActivityPost, self).save(*args, **kwargs)


def get_lifespan_of_seed(kind_of_seed):
    if kind_of_seed == NOTICE_ACTIVITY_POST_SEED:
        return 14400  # 4 hours * 60 minutes * 60 seconds/minute
    if kind_of_seed == NOTICE_CAMPAIGNX_NEWS_ITEM_SEED:
        return 7776000  # 3 months * 30 days * 24 hours * 60 minutes * 60 seconds/minute
    if kind_of_seed == NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED:
        return 7776000  # 3 months * 30 days * 24 hours * 60 minutes * 60 seconds/minute
    if kind_of_seed == NOTICE_FRIEND_ENDORSEMENTS_SEED:
        return 21600  # 6 hours * 60 minutes * 60 seconds/minute
    if kind_of_seed == NOTICE_VOTER_DAILY_SUMMARY_SEED:
        return 43200  # 12 hours * 60 minutes * 60 seconds/minute
    return 0
