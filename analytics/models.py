# analytics/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.utils.timezone import localtime, now
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

ACTION_VOTER_GUIDE_VISIT = 1
ACTION_VOTER_GUIDE_ENTRY = 2
ACTION_ORGANIZATION_FOLLOW = 3
ACTION_ORGANIZATION_AUTO_FOLLOW = 4
ACTION_ISSUE_FOLLOW = 5
ACTION_BALLOT_VISIT = 6
ACTION_POSITION_TAKEN = 7
ACTION_VOTER_TWITTER_AUTH = 8
ACTION_VOTER_FACEBOOK_AUTH = 9
ACTION_WELCOME_ENTRY = 10
ACTION_FRIEND_ENTRY = 11

logger = wevote_functions.admin.get_logger(__name__)


class AnalyticsAction(models.Model):
    """
    This is an incoming action we want to track
    """
    action_constant = models.PositiveSmallIntegerField(
        verbose_name="constant representing action", null=True, unique=False)

    exact_time = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now_add=True)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017
    date_as_integer = models.PositiveIntegerField(
        verbose_name="voter internal id", null=True, unique=False, db_index=True)

    # We store both
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=False)
    voter_id = models.PositiveIntegerField(verbose_name="voter internal id", null=True, unique=False)

    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)
    organization_id = models.PositiveIntegerField(null=True, blank=True)

    ballot_item_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)

    # We only want to store voter_device_id if we haven't verified the session yet. Set to null once verified.
    voter_device_id = models.CharField(
        verbose_name="voter_device_id of initiating voter", max_length=255, null=True, blank=True, unique=False)
    # When analytics comes into Analytics Application server, we need to authenticate the request. We authenticate
    #  the voter_device_id against a read-only database server, which might run seconds behind the master. Because of
    #  this, if a voter_device_id is not found the first time, we want to try again minutes later. BUT if that
    #  fails we want to invalidate the analytics.
    authentication_failed_twice = models.BooleanField(verbose_name='', default=False)

    # We override the save function to auto-generate date_as_integer
    def save(self, *args, **kwargs):
        if self.date_as_integer:
            self.date_as_integer = convert_to_int(self.date_as_integer)
        if self.date_as_integer == "" or self.date_as_integer is None:  # If there isn't a value...
            self.generate_date_as_integer()
        super(AnalyticsAction, self).save(*args, **kwargs)

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


class AnalyticsManager(models.Model):

    def save_action_voter_guide_visit(
            self, voter_we_vote_id, voter_id, organization_we_vote_id, organization_id, google_civic_election_id,
            ballot_item_we_vote_id=None, voter_device_id=None):
        return self.save_action(ACTION_VOTER_GUIDE_VISIT, voter_we_vote_id, voter_id,
                                organization_we_vote_id, organization_id, google_civic_election_id,
                                ballot_item_we_vote_id, voter_device_id)

    def save_action(self, action_constant, voter_we_vote_id, voter_id,
                    organization_we_vote_id, organization_id, google_civic_election_id, ballot_item_we_vote_id,
                    voter_device_id=None):
        # If a voter_device_id is passed in, it is because this action may be coming from
        #  https://analytics.wevoteusa.org and hasn't been authenticated yet
        # Confirm that we have a valid voter_device_id. If not, store the action with the voter_device_id so we can
        #  look up later.

        # If either voter identifier comes in, make sure we have both

        # If either organization identifier comes in, make sure we have both

        if action_constant == ACTION_VOTER_GUIDE_VISIT:
            # In the future we could reduce clutter in the AnalyticsAction table by only storing one entry per day
            return self.create_action_type1(action_constant, voter_we_vote_id, voter_id,
                                            organization_we_vote_id, organization_id, google_civic_election_id,
                                            voter_device_id)

        success = False
        status = "SAVE_ACTION-ACTION_NOT_FOUND "
        results = {
            'success':      success,
            'status':       status,
            'action_saved': False,
            'action':       AnalyticsAction(),
        }
        return results

    def create_action_type1(
            self, action_constant, voter_we_vote_id, voter_id,
            organization_we_vote_id, organization_id, google_civic_election_id, voter_device_id=None):
        """
        Create AnalyticsAction data
        """
        success = True
        status = "ACTION_CONSTANT:" + display_action_constant_human_readable(action_constant) + " "
        action_saved = False
        action = AnalyticsAction()

        if not action_constant:
            success = False
            status += 'MISSING_ACTION_CONSTANT '
        if not voter_we_vote_id:
            success = False
            status += 'MISSING_VOTER_WE_VOTE_ID '
        if not organization_we_vote_id:
            success = False
            status += 'MISSING_ORGANIZATION_WE_VOTE_ID '

        if success:
            try:
                action = AnalyticsAction.objects.using('analytics').create(
                    action_constant=action_constant,
                    voter_we_vote_id=voter_we_vote_id,
                    voter_id=voter_id,
                    organization_we_vote_id=organization_we_vote_id,
                    organization_id=organization_id,
                    google_civic_election_id=google_civic_election_id,
                )
                success = True
                action_saved = True
                status += 'ACTION_TYPE1_SAVED '
            except Exception as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTIONS_FOUND'

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results


def display_action_constant_human_readable(action_constant):
    if action_constant == ACTION_VOTER_GUIDE_VISIT:
        return "ACTION_VOTER_GUIDE_VISIT"
    if action_constant == ACTION_VOTER_GUIDE_ENTRY:
        return "ACTION_VOTER_GUIDE_ENTRY"
    if action_constant == ACTION_ORGANIZATION_FOLLOW:
        return "ACTION_ORGANIZATION_FOLLOW"
    if action_constant == ACTION_ORGANIZATION_AUTO_FOLLOW:
        return "ACTION_ORGANIZATION_AUTO_FOLLOW"
    if action_constant == ACTION_ISSUE_FOLLOW:
        return "ACTION_ISSUE_FOLLOW"
    if action_constant == ACTION_BALLOT_VISIT:
        return "ACTION_BALLOT_VISIT"
    if action_constant == ACTION_POSITION_TAKEN:
        return "ACTION_POSITION_TAKEN"
    if action_constant == ACTION_VOTER_TWITTER_AUTH:
        return "ACTION_VOTER_TWITTER_AUTH"
    if action_constant == ACTION_VOTER_FACEBOOK_AUTH:
        return "ACTION_VOTER_FACEBOOK_AUTH"
    if action_constant == ACTION_WELCOME_ENTRY:
        return "ACTION_WELCOME_ENTRY"
    if action_constant == ACTION_FRIEND_ENTRY:
        return "ACTION_FRIEND_ENTRY"

    return "ACTION_CONSTANT:" + str(action_constant)


def save_action_voter_guide_visit(
        voter_we_vote_id, voter_id, organization_we_vote_id, organization_id, google_civic_election_id,
        voter_device_id=None):
    """
    We break out this function so we can call it without creating a local analytics_manager
    :param voter_we_vote_id:
    :param voter_id:
    :param organization_we_vote_id:
    :param organization_id:
    :param google_civic_election_id:
    :param voter_device_id:
    :return:
    """
    analytics_manager = AnalyticsManager()
    return analytics_manager.save_action_voter_guide_visit(
        voter_we_vote_id, voter_id,
        organization_we_vote_id, organization_id, google_civic_election_id, voter_device_id)
