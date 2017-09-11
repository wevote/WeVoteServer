# analytics/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.utils.timezone import localtime, now
from election.models import Election
from organization.models import Organization
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
ACTION_WELCOME_VISIT = 12

ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS = [ACTION_VOTER_GUIDE_VISIT]


logger = wevote_functions.admin.get_logger(__name__)


class AnalyticsAction(models.Model):
    """
    This is an incoming action we want to track
    """
    action_constant = models.PositiveSmallIntegerField(
        verbose_name="constant representing action", null=True, unique=False)

    exact_time = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now_add=True)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(
        verbose_name="YYYYMMDD of the action", null=True, unique=False, db_index=True)

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

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            logger.error("position.election Found multiple")
            return
        except Election.DoesNotExist:
            return
        return election

    def organization(self):
        try:
            organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            logger.error("analytics.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("analytics.organization did not find")
            return
        return organization


class AnalyticsCountManager(models.Model):

    def fetch_visitors_to_organization_in_election(self, organization_we_vote_id, google_civic_election_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
            count_query = count_query.filter(organization_we_vote_id=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result


class AnalyticsManager(models.Model):

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
        missing_required_variable = False

        if not action_constant:
            missing_required_variable = True
            status += 'MISSING_ACTION_CONSTANT '
        if not voter_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_VOTER_WE_VOTE_ID '
        if not organization_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_ORGANIZATION_WE_VOTE_ID '

        if missing_required_variable:
            results = {
                'success': success,
                'status': status,
                'action_saved': action_saved,
                'action': action,
            }
            return results

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
            status += 'COULD_NOT_SAVE_ACTION_TYPE1'

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results

    def create_action_type2(
            self, action_constant, voter_we_vote_id, voter_id,
            google_civic_election_id, voter_device_id=None):
        """
        Create AnalyticsAction data
        """
        success = True
        status = "ACTION_CONSTANT:" + display_action_constant_human_readable(action_constant) + " "
        action_saved = False
        action = AnalyticsAction()
        missing_required_variable = False

        if not action_constant:
            missing_required_variable = True
            status += 'MISSING_ACTION_CONSTANT '
        if not voter_we_vote_id:
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
            action = AnalyticsAction.objects.using('analytics').create(
                action_constant=action_constant,
                voter_we_vote_id=voter_we_vote_id,
                voter_id=voter_id,
                google_civic_election_id=google_civic_election_id,
            )
            success = True
            action_saved = True
            status += 'ACTION_TYPE2_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_ACTION_TYPE2'

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results

    def retrieve_organization_list_with_election_activity(self, google_civic_election_id):
        success = False
        status = ""
        organization_list = []

        try:
            organization_list_query = AnalyticsAction.objects.using('analytics').all()
            organization_list_query = organization_list_query.filter(google_civic_election_id=google_civic_election_id)
            organization_list_query = organization_list_query.values('organization_we_vote_id').distinct()
            organization_list = list(organization_list_query)
            organization_list_found = True
        except Exception as e:
            organization_list_found = False

        results = {
            'success':                  success,
            'status':                   status,
            'organization_list':        organization_list,
            'organization_list_found':  organization_list_found,
        }
        return results

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

        if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS:
            # In the future we could reduce clutter in the AnalyticsAction table by only storing one entry per day
            return self.create_action_type1(action_constant, voter_we_vote_id, voter_id,
                                            organization_we_vote_id, organization_id, google_civic_election_id,
                                            voter_device_id)
        else:
            return self.create_action_type2(action_constant, voter_we_vote_id, voter_id,
                                            google_civic_election_id,
                                            voter_device_id)

    def save_organization_daily_metrics_values(self, organization_daily_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = OrganizationDailyMetrics()
        missing_required_variables = False
        date_as_integer = 0
        organization_we_vote_id = ''

        if positive_value_exists(organization_daily_metrics_values['organization_we_vote_id']):
            organization_we_vote_id = organization_daily_metrics_values['organization_we_vote_id']
        else:
            missing_required_variables = True
        if positive_value_exists(organization_daily_metrics_values['date_as_integer']):
            date_as_integer = organization_daily_metrics_values['date_as_integer']
        else:
            missing_required_variables = True

        if not missing_required_variables:
            try:
                metrics_saved, created = OrganizationDailyMetrics.objects.using('analytics').update_or_create(
                    organization_we_vote_id=organization_we_vote_id,
                    date_as_integer=date_as_integer,
                    defaults=organization_daily_metrics_values
                )
            except Exception as e:
                success = False
                status += 'ORGANIZATION_DAILY_METRICS_UPDATE_OR_CREATE_FAILED '

        results = {
            'success':          success,
            'status':           status,
            'metrics_saved':    metrics_saved,
            'metrics':          metrics,
        }
        return results

    def save_organization_election_metrics_values(self, organization_election_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = OrganizationElectionMetrics()
        missing_required_variables = False
        google_civic_election_id = 0
        organization_we_vote_id = ''

        if positive_value_exists(organization_election_metrics_values['google_civic_election_id']):
            google_civic_election_id = organization_election_metrics_values['google_civic_election_id']
        else:
            missing_required_variables = True
        if positive_value_exists(organization_election_metrics_values['organization_we_vote_id']):
            organization_we_vote_id = organization_election_metrics_values['organization_we_vote_id']
        else:
            missing_required_variables = True

        if not missing_required_variables:
            try:
                metrics_saved, created = OrganizationElectionMetrics.objects.using('analytics').update_or_create(
                    google_civic_election_id=google_civic_election_id,
                    organization_we_vote_id__iexact=organization_we_vote_id,
                    defaults=organization_election_metrics_values
                )
            except Exception as e:
                success = False
                status += 'ORGANIZATION_ELECTION_METRICS_UPDATE_OR_CREATE_FAILED '

        results = {
            'success':          success,
            'status':           status,
            'metrics_saved':    metrics_saved,
            'metrics':          metrics,
        }
        return results

    def save_sitewide_daily_metrics_values(self, sitewide_daily_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = SitewideDailyMetrics()

        if positive_value_exists(sitewide_daily_metrics_values['date_as_integer']):
            date_as_integer = sitewide_daily_metrics_values['date_as_integer']

            try:
                metrics_saved, created = SitewideDailyMetrics.objects.using('analytics').update_or_create(
                    date_as_integer=date_as_integer,
                    defaults=sitewide_daily_metrics_values
                )
            except Exception as e:
                success = False
                status += 'SITEWIDE_DAILY_METRICS_UPDATE_OR_CREATE_FAILED '

        results = {
            'success':          success,
            'status':           status,
            'metrics_saved':    metrics_saved,
            'metrics':          metrics,
        }
        return results

    def save_sitewide_election_metrics_values(self, sitewide_election_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = SitewideElectionMetrics()

        if positive_value_exists(sitewide_election_metrics_values['google_civic_election_id']):
            google_civic_election_id = sitewide_election_metrics_values['google_civic_election_id']

            try:
                metrics_saved, created = SitewideElectionMetrics.objects.using('analytics').update_or_create(
                    google_civic_election_id=google_civic_election_id,
                    defaults=sitewide_election_metrics_values
                )
            except Exception as e:
                success = False
                status += 'SITEWIDE_ELECTION_METRICS_UPDATE_OR_CREATE_FAILED '

        results = {
            'success': success,
            'status': status,
            'metrics_saved': metrics_saved,
            'metrics': metrics,
        }
        return results


class OrganizationDailyMetrics(models.Model):
    """
    This is a summary of the organization activity on one day.
    """
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(verbose_name="YYYYMMDD of the action",
                                                  null=True, unique=False, db_index=True)
    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id",
                                               max_length=255, null=True, blank=True, unique=False)
    visitors_total = models.PositiveIntegerField(verbose_name="number of visitors, all time", null=True, unique=False)
    visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today", null=True, unique=False)
    new_visitors_today = models.PositiveIntegerField(verbose_name="new visitors, today", null=True, unique=False)

    voter_guide_entrants_today = models.PositiveIntegerField(verbose_name="first touch, voter guide",
                                                             null=True, unique=False)
    voter_guide_entrants = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_visiting_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_visiting_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    followers_total = models.PositiveIntegerField(verbose_name="all time",
                                                               null=True, unique=False)
    new_followers_today = models.PositiveIntegerField(verbose_name="today",
                                                               null=True, unique=False)

    autofollowers_total = models.PositiveIntegerField(verbose_name="all",
                                                                   null=True, unique=False)
    new_autofollowers_today = models.PositiveIntegerField(verbose_name="today",
                                                                   null=True, unique=False)

    issues_linked_total = models.PositiveIntegerField(verbose_name="organization classifications, all time",
                                                      null=True, unique=False)

    organization_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                null=True, unique=False)

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


class OrganizationElectionMetrics(models.Model):
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_entrants = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    new_followers = models.PositiveIntegerField(verbose_name="today",
                                                      null=True, unique=False)
    new_autofollowers = models.PositiveIntegerField(verbose_name="all",
                                                      null=True, unique=False)
    entrants_visited_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_visited_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            # We retrieve this from the read-only database (as opposed to the analytics database)
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            logger.error("position.election Found multiple")
            return
        except Election.DoesNotExist:
            return
        return election

    def organization(self):
        try:
            organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            logger.error("analytics.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("analytics.organization did not find")
            return
        return organization


class SitewideDailyMetrics(models.Model):
    """
    This is a summary of the sitewide activity on one day.
    """
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(verbose_name="YYYYMMDD of the action",
                                                  null=True, unique=False, db_index=True)
    visitors_total = models.PositiveIntegerField(verbose_name="number of visitors, all time", null=True, unique=False)
    visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today", null=True, unique=False)
    new_visitors_today = models.PositiveIntegerField(verbose_name="new visitors, today", null=True, unique=False)

    voter_guide_entrants_today = models.PositiveIntegerField(verbose_name="first touch, voter guide",
                                                            null=True, unique=False)
    welcome_page_entrants_today = models.PositiveIntegerField(verbose_name="first touch, welcome page",
                                                             null=True, unique=False)
    friend_entrants_today = models.PositiveIntegerField(verbose_name="first touch, response to friend",
                                                       null=True, unique=False)

    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="number of visitors, all time",
                                                               null=True, unique=False)
    authenticated_visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today",
                                                               null=True, unique=False)

    ballots_viewed_today = models.PositiveIntegerField(verbose_name="number of voters who viewed a ballot today",
                                                       null=True, unique=False)
    voter_guides_viewed_total = models.PositiveIntegerField(verbose_name="number of voter guides viewed, all time",
                                                            null=True, unique=False)
    voter_guides_viewed_today = models.PositiveIntegerField(verbose_name="number of voter guides viewed, today",
                                                            null=True, unique=False)

    issues_followed_total = models.PositiveIntegerField(verbose_name="follow issue connections, all time",
                                                        null=True, unique=False)
    issues_followed_today = models.PositiveIntegerField(verbose_name="follow issue connections, today",
                                                        null=True, unique=False)

    organizations_followed_total = models.PositiveIntegerField(verbose_name="voter follow organizations, all time",
                                                               null=True, unique=False)
    organizations_followed_today = models.PositiveIntegerField(verbose_name="voter follow organizations, today",
                                                               null=True, unique=False)

    organizations_autofollowed_total = models.PositiveIntegerField(verbose_name="autofollow organizations, all",
                                                                   null=True, unique=False)
    organizations_autofollowed_today = models.PositiveIntegerField(verbose_name="autofollow organizations, today",
                                                                   null=True, unique=False)

    organizations_with_linked_issues = models.PositiveIntegerField(verbose_name="organizations linked to issues, all",
                                                                   null=True, unique=False)

    issues_linked_total = models.PositiveIntegerField(verbose_name="organization classifications, all time",
                                                      null=True, unique=False)
    issues_linked_today = models.PositiveIntegerField(verbose_name="organization classifications, today",
                                                      null=True, unique=False)

    organizations_signed_in_total = models.PositiveIntegerField(verbose_name="organizations signed in, all",
                                                                null=True, unique=False)

    organizations_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                               null=True, unique=False)
    organizations_with_new_positions_today = models.PositiveIntegerField(verbose_name="today",
                                                                         null=True, unique=False)
    organization_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                null=True, unique=False)
    individuals_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                             null=True, unique=False)
    individuals_with_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                    null=True, unique=False)
    individuals_with_friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                                          null=True, unique=False)
    friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                         null=True, unique=False)
    entered_full_address = models.PositiveIntegerField(verbose_name="all",
                                                       null=True, unique=False)

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


class SitewideElectionMetrics(models.Model):
    """
    This is a summary of the sitewide activity for one election.
    """
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_entrants = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guides_viewed = models.PositiveIntegerField(verbose_name="number of voter guides viewed, this election",
                                                            null=True, unique=False)

    issues_followed = models.PositiveIntegerField(verbose_name="follow issue connections, all time",
                                                        null=True, unique=False)
    organizations_followed = models.PositiveIntegerField(verbose_name="voter follow organizations, today",
                                                               null=True, unique=False)
    organizations_autofollowed = models.PositiveIntegerField(verbose_name="autofollow organizations, today",
                                                                   null=True, unique=False)
    organizations_signed_in = models.PositiveIntegerField(verbose_name="organizations signed in, all",
                                                                null=True, unique=False)

    organizations_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                               null=True, unique=False)
    organization_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                null=True, unique=False)
    individuals_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                             null=True, unique=False)
    individuals_with_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                    null=True, unique=False)
    individuals_with_friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                                          null=True, unique=False)
    friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                         null=True, unique=False)
    entered_full_address = models.PositiveIntegerField(verbose_name="all",
                                                       null=True, unique=False)

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
