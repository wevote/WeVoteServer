# volunteer_task/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models

import wevote_functions.functions_date
from voter.models import fetch_voter_from_voter_device_link, Voter
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_volunteer_team_integer, fetch_site_unique_id_prefix

VOLUNTEER_ACTION_POSITION_SAVED = 1
VOLUNTEER_ACTION_POSITION_COMMENT_SAVED = 2
VOLUNTEER_ACTION_CANDIDATE_CREATED = 3
VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED = 4
VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION = 5  # Including starting process
VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION = 6  # Candidate or Politician
VOLUNTEER_ACTION_POLITICIAN_PHOTO = 7  # Candidate or Politician: Photo related change
VOLUNTEER_ACTION_POLITICIAN_REQUEST = 8  # Politician sends in personal statement
VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED = 9
VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS = 10  # Candidate or Politician
VOLUNTEER_ACTION_MATCH_CANDIDATES_TO_POLITICIANS = 11
VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE = 12


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
        # We Vote uses Pacific Time for TIME_ZONE
        self.date_as_integer = wevote_functions.functions_date.generate_date_as_integer()
        return


class VolunteerTaskManager(models.Manager):

    @staticmethod
    def create_volunteer_task_completed(
            action_constant=None,
            request=None,
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

        if request and not positive_value_exists(voter_we_vote_id):
            voter_device_id = get_voter_api_device_id(request)
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


class VolunteerTeam(models.Model):
    """
    A team of volunteers
    """
    team_name = models.CharField(max_length=255, null=True, unique=True, db_index=True)
    team_description = models.TextField(null=True)
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "team", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_volunteer_team_integer
    we_vote_id = models.CharField(
        max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)
    which_day_is_end_of_week = models.PositiveIntegerField(default=6, null=False)  # Monday is 0 and Sunday is 6

    # We override the save function, so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_volunteer_team_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "team" = tells us this is a unique id for a VolunteerTeam
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}team{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(VolunteerTeam, self).save(*args, **kwargs)


class VolunteerTeamMember(models.Model):
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None

    @staticmethod
    def __unicode__():
        return "VolunteerTeamMember"

    date_last_changed = models.DateTimeField(null=True, auto_now=True, db_index=True)
    team_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)

    def voter(self):
        if not self.voter_we_vote_id:
            return
        try:
            voter = Voter.objects.using('readonly').get(we_vote_id=self.voter_we_vote_id)
        except Voter.MultipleObjectsReturned as e:
            return
        except Voter.DoesNotExist:
            return
        return voter


class VolunteerWeeklyMetrics(models.Model):
    """
    This is a summary of a volunteer's activity for one week
    """
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    #  And this end-of-week date is Sunday from ISO 8601 Standard
    end_of_week_date_integer = models.PositiveIntegerField(null=True, db_index=True)
    candidates_created = models.PositiveIntegerField(default=0)
    duplicate_politician_analysis = models.PositiveIntegerField(default=0)
    election_retrieve_started = models.PositiveIntegerField(default=0)
    match_candidates_to_politicians = models.PositiveIntegerField(default=0)
    politicians_augmented = models.PositiveIntegerField(default=0)
    politicians_deduplicated = models.PositiveIntegerField(default=0)
    politicians_photo_added = models.PositiveIntegerField(default=0)
    politicians_requested_changes = models.PositiveIntegerField(default=0)
    positions_saved = models.PositiveIntegerField(default=0)
    position_comments_saved = models.PositiveIntegerField(default=0)
    twitter_bulk_retrieve = models.PositiveIntegerField(default=0)
    # We create this unique identifier to we can prevent duplicates: voter_we_vote_id + "-" + end_of_week_date_integer
    voter_date_unique_string = models.CharField(max_length=255, null=True, db_index=True, unique=True)
    voter_display_name = models.CharField(max_length=255, null=True, db_index=True)
    voter_guide_possibilities_created = models.PositiveIntegerField(default=0)
    voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    # For teams that meet on Friday, we want Thursday to be the end-of-week. Note Monday is 0 and Sunday is 6
    which_day_is_end_of_week = models.PositiveIntegerField(default=6, null=False, db_index=True)


def display_action_constant_human_readable(action_constant):
    if action_constant == VOLUNTEER_ACTION_CANDIDATE_CREATED:
        return "CANDIDATE_CREATED"
    if action_constant == VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS:
        return "DUPLICATE_POLITICIAN_ANALYSIS"
    if action_constant == VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED:
        return "ELECTION_RETRIEVE"
    if action_constant == VOLUNTEER_ACTION_MATCH_CANDIDATES_TO_POLITICIANS:
        return "MATCH_TO_POLITICIANS"
    if action_constant == VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION:
        return "POLITICIAN_AUGMENTATION"
    if action_constant == VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION:
        return "POLITICIAN_DEDUPLICATION"
    if action_constant == VOLUNTEER_ACTION_POLITICIAN_PHOTO:
        return "POLITICIAN_PHOTO"
    if action_constant == VOLUNTEER_ACTION_POLITICIAN_REQUEST:
        return "POLITICIAN_REQUEST"
    if action_constant == VOLUNTEER_ACTION_POSITION_COMMENT_SAVED:
        return "POSITION_COMMENT_SAVED"
    if action_constant == VOLUNTEER_ACTION_POSITION_SAVED:
        return "POSITION_SAVED"
    if action_constant == VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE:
        return "PHOTO_BULK_RETRIEVE"
    if action_constant == VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED:
        return "VOTER_GUIDE_POSSIBILITY_CREATED"

    return "VOLUNTEER_ACTION_CONSTANT:" + str(action_constant)
