# volunteer_task/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.utils.timezone import localtime, now

from voter.models import fetch_voter_from_voter_device_link
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_functions.functions_date import convert_date_as_integer_to_date, convert_date_to_date_as_integer

VOLUNTEER_ACTION_POSITION_SAVED = 1
VOLUNTEER_ACTION_POSITION_COMMENT_SAVED = 2
VOLUNTEER_ACTION_CANDIDATE_CREATED = 3
VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED = 4
VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION = 5


class VolunteerTaskCompleted(models.Model):
    # This is volunteer action_constant (as opposed to Analytics action_constant)
    action_constant = models.PositiveSmallIntegerField(null=True, db_index=True)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(
        verbose_name="YYYYMMDD of the action", null=True, db_index=True)
    exact_time = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now_add=True)

    voter_id = models.PositiveIntegerField(default=None, null=True)
    voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)

    # We override the save function to auto-generate date_as_integer
    def save(self, *args, **kwargs):
        if self.date_as_integer:
            self.date_as_integer = convert_to_int(self.date_as_integer)
        if self.date_as_integer == "" or self.date_as_integer is None:  # If there isn't a value...
            self.generate_date_as_integer()
        super(VolunteerTaskCompleted, self).save(*args, **kwargs)

    def display_action_constant_human_readable(self):
        return display_action_constant_human_readable(self.action_constant)

    def generate_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        day_as_string = "{:d}{:02d}{:02d}".format(
            datetime_now.year,
            datetime_now.month,
            datetime_now.day,
        )
        self.date_as_integer = convert_to_int(day_as_string)
        return


class VolunteerTaskManager(models.Manager):

    @staticmethod
    def create_volunteer_task_completed(
            action_constant=None,
            voter_we_vote_id=None,
            voter_id=None,
            voter_device_id=None):
        """
        Create VolunteerTaskCompleted data
        """
        success = True
        status = "ACTION_CONSTANT:" + display_action_constant_human_readable(action_constant) + " "
        action_saved = False
        action = VolunteerTaskCompleted()
        missing_required_variable = False

        if voter_device_id and not positive_value_exists(voter_we_vote_id):
            voter = fetch_voter_from_voter_device_link(voter_device_id)
            if hasattr(voter, 'we_vote_id'):
                voter_id = voter.id
                voter_we_vote_id = voter.we_vote_id
            else:
                voter_id = 0
                voter_we_vote_id = ""

        if not action_constant:
            missing_required_variable = True
            status += 'MISSING_ACTION_CONSTANT '
        if not positive_value_exists(voter_we_vote_id):
            missing_required_variable = True
            status += 'MISSING_VOTER_WE_VOTE_ID '

        if missing_required_variable:
            results = {
                'success': success,
                'status': status,
                'action_saved': action_saved,
                'action': action,
            }
            return results

        try:
            action = VolunteerTaskCompleted.objects.using('analytics').create(
                action_constant=action_constant,
                voter_we_vote_id=voter_we_vote_id,
                voter_id=voter_id,
            )
            success = True
            action_saved = True
            status += 'VOLUNTEER_TASK_COMPLETED_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_VOLUNTEER_TASK_COMPLETED: ' + str(e) + ' '

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results


class VolunteerWeeklyMetrics(models.Model):
    """
    This is a summary of a volunteer's activity for one week
    """
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    #  And this end-of-week date is Sunday from ISO 8601 Standard
    end_of_week_date_integer = models.PositiveIntegerField(null=True, db_index=True)
    candidates_created = models.PositiveIntegerField(null=True)
    politicians_deduplicated = models.PositiveIntegerField(null=True)
    positions_saved = models.PositiveIntegerField(null=True)
    position_comments_saved = models.PositiveIntegerField(null=True)
    # We create this unique identifier to we can prevent duplicates: voter_we_vote_id + "-" + end_of_week_date_integer
    voter_date_unique_string = models.CharField(max_length=255, null=True, db_index=True, unique=True)
    voter_display_name = models.CharField(max_length=255, null=True, db_index=True)
    voter_guide_possibilities_created = models.PositiveIntegerField(null=True)
    voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)


def display_action_constant_human_readable(action_constant):
    if action_constant == VOLUNTEER_ACTION_CANDIDATE_CREATED:
        return "CANDIDATE_CREATED"
    if action_constant == VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED:
        return "VOTER_GUIDE_POSSIBILITY_CREATED"
    if action_constant == VOLUNTEER_ACTION_POSITION_COMMENT_SAVED:
        return "POSITION_COMMENT_SAVED"
    if action_constant == VOLUNTEER_ACTION_POSITION_SAVED:
        return "POSITION_SAVED"

    return "VOLUNTEER_ACTION_CONSTANT:" + str(action_constant)
