# activity/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from config.base import get_environment_variable
from django.utils.timezone import now
from django.db.models import Q
from datetime import timedelta
from wevote_functions.functions import generate_random_string, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_sms_integer, fetch_site_unique_id_prefix

# Kind of Seeds
NOTICE_FRIEND_ENDORSEMENTS_SEED = 'NOTICE_FRIEND_ENDORSEMENTS_SEED'

# Kind of Notices
NOTICE_FRIEND_ENDORSEMENTS = 'NOTICE_FRIEND_ENDORSEMENTS'


class ActivityNotice(models.Model):
    """
    This is a notice for the notification drop-down menu, for one person
    """
    activity_notice_seed_id = models.PositiveIntegerField(default=None, null=True)
    date_of_notice = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True)
    deleted = models.BooleanField(default=False)
    kind_of_notice = models.CharField(max_length=50, default=None, null=True)
    kind_of_seed = models.CharField(max_length=50, default=None, null=True)
    new_positions_entered_count = models.PositiveIntegerField(default=None, null=True)
    position_we_vote_id = models.CharField(max_length=255, default=None, null=True)
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


class ActivityNoticeSeed(models.Model):
    """
    This is the "seed" for a notice for the notification drop-down menu, which is used before we "distribute" it
    out to an ActivityNotice, which gets shown to an individual voter.
    """
    activity_notices_created = models.BooleanField(default=False)
    activity_notices_updated = models.BooleanField(default=False)
    activity_notices_scheduled = models.BooleanField(default=False)
    date_of_notice = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True)
    deleted = models.BooleanField(default=False)
    kind_of_seed = models.CharField(max_length=50, default=None, null=True)
    position_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    new_positions_entered_count = models.PositiveIntegerField(default=None, null=True)
    speaker_name = models.CharField(max_length=255, default=None, null=True)
    speaker_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_profile_image_url_medium = models.TextField(blank=True, null=True)
    speaker_profile_image_url_tiny = models.TextField(blank=True, null=True)


class ActivityTidbit(models.Model):
    """
    An article or chunk of information to show on the Activity feed
    """
    date_of_tidbit = models.DateTimeField(null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    position_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_name = models.CharField(max_length=255, default=None, null=True)
    speaker_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_photo_url_large = models.TextField(null=True)
    speaker_photo_url_medium = models.TextField(null=True)
    speaker_photo_url_tiny = models.TextField(null=True)
    speaker_twitter_followers_count = models.PositiveIntegerField(default=None, null=True)
    speaker_twitter_handle = models.CharField(max_length=255, default=None, null=True)
    speaker_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    speaker_profile_image_url_medium = models.TextField(blank=True, null=True)
    speaker_profile_image_url_tiny = models.TextField(blank=True, null=True)


class ActivityManager(models.Manager):

    def __unicode__(self):
        return "ActivityManager"

    def create_activity_notice(
            self,
            activity_notice_seed_id=0,
            date_of_notice=None,
            kind_of_notice=None,
            kind_of_seed=None,
            new_positions_entered_count=0,
            position_we_vote_id='',
            recipient_voter_we_vote_id='',
            send_to_email=False,
            send_to_sms=False,
            speaker_name='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id='',
            speaker_profile_image_url_medium='',
            speaker_profile_image_url_tiny=''):
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
            if new_positions_entered_count == 0:
                new_positions_entered_count = 1
            activity_notice = ActivityNotice.objects.create(
                activity_notice_seed_id=activity_notice_seed_id,
                date_of_notice=date_of_notice,
                kind_of_notice=kind_of_notice,
                kind_of_seed=kind_of_seed,
                new_positions_entered_count=new_positions_entered_count,
                position_we_vote_id=position_we_vote_id,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                send_to_email=send_to_email,
                send_to_sms=send_to_sms,
                speaker_name=speaker_name,
                speaker_organization_we_vote_id=speaker_organization_we_vote_id,
                speaker_voter_we_vote_id=speaker_voter_we_vote_id,
                speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                speaker_profile_image_url_tiny=speaker_profile_image_url_tiny
            )
            activity_notice_saved = True
            success = True
            status += "ACTIVITY_NOTICE_CREATED "
        except Exception as e:
            activity_notice_saved = False
            activity_notice = None
            success = False
            status += "ACTIVITY_NOTICE_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'activity_notice_saved':    activity_notice_saved,
            'activity_notice':          activity_notice,
        }
        return results

    def create_activity_notice_seed(
            self,
            date_of_notice=None,
            kind_of_seed=None,
            new_positions_entered_count=0,
            position_we_vote_id='',
            speaker_name='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id='',
            speaker_profile_image_url_medium='',
            speaker_profile_image_url_tiny=''):
        status = ''

        if not positive_value_exists(speaker_organization_we_vote_id):
            activity_notice_seed = None
            results = {
                'success':                      False,
                'status':                       "ACTIVITY_NOTICE_SEED_MISSING_SPEAKER_ORG_ID ",
                'activity_notice_seed_saved':   False,
                'activity_notice_seed':         activity_notice_seed,
            }
            return results

        try:
            if new_positions_entered_count == 0:
                new_positions_entered_count = 1
            activity_notice_seed = ActivityNoticeSeed.objects.create(
                date_of_notice=date_of_notice,
                kind_of_seed=kind_of_seed,
                new_positions_entered_count=new_positions_entered_count,
                position_we_vote_id=position_we_vote_id,
                speaker_name=speaker_name,
                speaker_organization_we_vote_id=speaker_organization_we_vote_id,
                speaker_voter_we_vote_id=speaker_voter_we_vote_id,
                speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                speaker_profile_image_url_tiny=speaker_profile_image_url_tiny
            )
            activity_notice_seed_saved = True
            success = True
            status += "ACTIVITY_NOTICE_SEED_CREATED "
        except Exception as e:
            activity_notice_seed_saved = False
            activity_notice_seed = None
            success = False
            status += "ACTIVITY_NOTICE_SEED_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_notice_seed_saved':   activity_notice_seed_saved,
            'activity_notice_seed':         activity_notice_seed,
        }
        return results

    def create_activity_tidbit(
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
            activity_tidbit = ActivityTidbit.objects.create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                sender_voter_sms=sender_voter_sms,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                recipient_sms_we_vote_id=recipient_sms_we_vote_id,
                recipient_voter_sms=recipient_voter_sms,
                kind_of_sms_template=kind_of_sms_template,
                template_variables_in_json=template_variables_in_json,
            )
            activity_tidbit_saved = True
            success = True
            status += "SMS_DESCRIPTION_CREATED "
        except Exception as e:
            activity_tidbit_saved = False
            activity_tidbit = ActivityTidbit()
            success = False
            status += "SMS_DESCRIPTION_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'activity_tidbit_saved':    activity_tidbit_saved,
            'activity_tidbit':          activity_tidbit,
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

    def retrieve_recent_activity_notice_from_speaker_and_recipient(
            self,
            activity_notice_seed_id=0,
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

    def retrieve_recent_activity_notice_seed_from_speaker(
            self,
            kind_of_seed='',
            speaker_organization_we_vote_id='',
            speaker_voter_we_vote_id=''):
        """

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
            status += 'FAILED retrieve_recent_activity_notice_seed_from_speaker ActivityNoticeSeed ' + str(e) + ' '

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
            queryset = queryset.order_by('-id')  # Put most recent sms at top of list
            activity_notice_list = list(queryset)

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
            'success': success,
            'status': status,
            'recipient_voter_we_vote_id': recipient_voter_we_vote_id,
            'activity_notice_list_found': activity_notice_list_found,
            'activity_notice_list': activity_notice_list,
        }
        return results

    def retrieve_next_activity_notice_seed_to_process(
            self,
            notices_to_be_created=False,
            notices_to_be_scheduled=False,
            notices_to_be_updated=False,
            activity_notice_seed_id_already_reviewed_list=[]):
        status = ""

        activity_notice_seed = None
        try:
            queryset = ActivityNoticeSeed.objects.all()
            queryset = queryset.filter(deleted=False)
            if positive_value_exists(notices_to_be_created):
                queryset = queryset.filter(activity_notices_created=False)
            elif positive_value_exists(notices_to_be_scheduled):
                queryset = queryset.filter(activity_notices_scheduled=False)
            elif positive_value_exists(notices_to_be_updated):
                queryset = queryset.filter(activity_notices_updated=False)
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
            status += 'FAILED retrieve_activity_notice_seed ActivityNoticeSeed ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'activity_notice_seed_found':   activity_notice_seed_found,
            'activity_notice_seed':         activity_notice_seed,
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
                if 'new_positions_entered_count' in update_values:
                    existing_entry.new_positions_entered_count = update_values['new_positions_entered_count']
                    values_changed = True
                if 'position_we_vote_id' in update_values:
                    existing_entry.position_we_vote_id = update_values['position_we_vote_id']
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


def get_lifespan_of_seed(kind_of_seed):
    if kind_of_seed == NOTICE_FRIEND_ENDORSEMENTS_SEED:
        return 1800  # 30 minutes * 60 seconds/minute
    return 0
