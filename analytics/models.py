# analytics/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime, now
from election.models import Election
from exception.models import print_to_log
from follow.models import FollowOrganizationList
from organization.models import Organization
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

ACTION_VOTER_GUIDE_VISIT = 1
ACTION_VOTER_GUIDE_ENTRY = 2  # DEPRECATED: Now we use ACTION_VOTER_GUIDE_VISIT + first_visit
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
ACTION_ORGANIZATION_FOLLOW_IGNORE = 13
ACTION_ORGANIZATION_STOP_FOLLOWING = 14
ACTION_ISSUE_FOLLOW_IGNORE = 15
ACTION_ISSUE_STOP_FOLLOWING = 16
ACTION_MODAL_ISSUES = 17
ACTION_MODAL_ORGANIZATIONS = 18
ACTION_MODAL_POSITIONS = 19
ACTION_MODAL_FRIENDS = 20
ACTION_MODAL_SHARE = 21
ACTION_MODAL_VOTE = 22
ACTION_NETWORK = 23
ACTION_FACEBOOK_INVITABLE_FRIENDS = 24
ACTION_DONATE_VISIT = 25
ACTION_ACCOUNT_PAGE = 26
ACTION_INVITE_BY_EMAIL = 27
ACTION_ABOUT_GETTING_STARTED = 28
ACTION_ABOUT_VISION = 29
ACTION_ABOUT_ORGANIZATION = 30
ACTION_ABOUT_TEAM = 31
ACTION_ABOUT_MOBILE = 32
ACTION_OFFICE = 33
ACTION_CANDIDATE = 34
ACTION_VOTER_GUIDE_GET_STARTED = 35
ACTION_FACEBOOK_AUTHENTICATION_EXISTS = 36
ACTION_GOOGLE_AUTHENTICATION_EXISTS = 37
ACTION_TWITTER_AUTHENTICATION_EXISTS = 38
ACTION_EMAIL_AUTHENTICATION_EXISTS = 39
ACTION_ELECTIONS = 40
ACTION_ORGANIZATION_STOP_IGNORING = 41

ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS = \
    [ACTION_ORGANIZATION_AUTO_FOLLOW,
     ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_FOLLOW_IGNORE, ACTION_ORGANIZATION_STOP_FOLLOWING,
     ACTION_ORGANIZATION_STOP_IGNORING, ACTION_VOTER_GUIDE_VISIT]


logger = wevote_functions.admin.get_logger(__name__)


class AnalyticsAction(models.Model):
    """
    This is an incoming action we want to track
    """
    action_constant = models.PositiveSmallIntegerField(
        verbose_name="constant representing action", null=True, unique=False, db_index=True)

    exact_time = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now_add=True)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(
        verbose_name="YYYYMMDD of the action", null=True, unique=False, db_index=True)

    # We store both
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=False,
        db_index=True)
    voter_id = models.PositiveIntegerField(verbose_name="voter internal id", null=True, unique=False)

    # This voter is linked to a sign in account (Facebook, Twitter, Google, etc.)
    is_signed_in = models.BooleanField(verbose_name='', default=False)

    state_code = models.CharField(
        verbose_name="state_code", max_length=255, null=True, blank=True, unique=False)

    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False, db_index=True)
    organization_id = models.PositiveIntegerField(null=True, blank=True)

    ballot_item_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False, db_index=True)
    # This entry was the first entry on this day, used for tracking direct links to We Vote
    first_visit_today = models.BooleanField(verbose_name='', default=False)

    # We only want to store voter_device_id if we haven't verified the session yet. Set to null once verified.
    voter_device_id = models.CharField(
        verbose_name="voter_device_id of initiating voter", max_length=255, null=True, blank=True, unique=False)
    # When analytics comes into Analytics Application server, we need to authenticate the request. We authenticate
    #  the voter_device_id against a read-only database server, which might run seconds behind the master. Because of
    #  this, if a voter_device_id is not found the first time, we want to try again minutes later. BUT if that
    #  fails we want to invalidate the analytics.
    authentication_failed_twice = models.BooleanField(verbose_name='', default=False)
    user_agent = models.CharField(verbose_name="https request user agent", max_length=255, null=True, blank=True,
                                  unique=False)
    is_bot = models.BooleanField(verbose_name="request came from web-bots or spider", default=False)
    is_mobile = models.BooleanField(verbose_name="request came from mobile device", default=False)
    is_desktop = models.BooleanField(verbose_name="request came from desktop device", default=False)
    is_tablet = models.BooleanField(verbose_name="request came from tablet device", default=False)

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
        if not self.organization_we_vote_id:
            return
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

    def fetch_ballot_views(self, google_civic_election_id=0, limit_to_one_date_as_integer=0):
        """
        Count the number of voters that viewed at least one ballot
        :param google_civic_election_id:
        :param limit_to_one_date_as_integer:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(limit_to_one_date_as_integer):
                count_query = count_query.filter(date_as_integer=limit_to_one_date_as_integer)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_organization_entrants_list(self, organization_we_vote_id, google_civic_election_id=0):
        """
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """

        voters_who_visited_organization_first_simple_list = []
        try:
            first_visit_query = AnalyticsAction.objects.using('analytics').all()
            first_visit_query = first_visit_query.filter(Q(action_constant=ACTION_VOTER_GUIDE_VISIT) |
                                                         Q(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW))
            first_visit_query = first_visit_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                first_visit_query = first_visit_query.filter(google_civic_election_id=google_civic_election_id)
            first_visit_query = first_visit_query.filter(first_visit_today=True)
            first_visit_query = first_visit_query.values('voter_we_vote_id').distinct()
            voters_who_visited_organization_first = list(first_visit_query)

            for voter_dict in voters_who_visited_organization_first:
                if positive_value_exists(voter_dict['voter_we_vote_id']):
                    voters_who_visited_organization_first_simple_list.append(voter_dict['voter_we_vote_id'])

        except Exception as e:
            pass

        return voters_who_visited_organization_first_simple_list

    def fetch_organization_entrants_took_position(
            self, organization_we_vote_id, google_civic_election_id=0):
        """
        Count the voters who entered on an organization's voter guide, and then took a position
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """

        voters_who_visited_organization_first_simple_list = \
            self.fetch_organization_entrants_list(organization_we_vote_id, google_civic_election_id)

        if not len(voters_who_visited_organization_first_simple_list):
            return 0

        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_POSITION_TAKEN)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voters_who_visited_organization_first_simple_list)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_organization_entrants_visited_ballot(
            self, organization_we_vote_id, google_civic_election_id=0):
        """
        Count the voters who entered on an organization's voter guide, and then who proceeded to ballot
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        voters_who_visited_organization_first_simple_list = \
            self.fetch_organization_entrants_list(organization_we_vote_id, google_civic_election_id)

        if not len(voters_who_visited_organization_first_simple_list):
            return 0

        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voters_who_visited_organization_first_simple_list)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_organization_followers_took_position(self, organization_we_vote_id, google_civic_election_id=0):
        follow_organization_list = FollowOrganizationList()
        return_voter_we_vote_id = True
        voter_we_vote_ids_of_organization_followers = \
            follow_organization_list.fetch_followers_list_by_organization_we_vote_id(
                organization_we_vote_id, return_voter_we_vote_id)

        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_POSITION_TAKEN)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voter_we_vote_ids_of_organization_followers)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_organization_followers_visited_ballot(self, organization_we_vote_id, google_civic_election_id=0):
        follow_organization_list = FollowOrganizationList()
        return_voter_we_vote_id = True
        voter_we_vote_ids_of_organization_followers = \
            follow_organization_list.fetch_followers_list_by_organization_we_vote_id(
                organization_we_vote_id, return_voter_we_vote_id)
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voter_we_vote_ids_of_organization_followers)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_visitors(self, google_civic_election_id=0, organization_we_vote_id='',
                       limit_to_one_date_as_integer=0, count_through_this_date_as_integer=0,
                       limit_to_authenticated=False):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(limit_to_one_date_as_integer):
                count_query = count_query.filter(date_as_integer=limit_to_one_date_as_integer)
            elif positive_value_exists(count_through_this_date_as_integer):
                count_query = count_query.filter(date_as_integer__lte=count_through_this_date_as_integer)
            if limit_to_authenticated:
                count_query = count_query.filter(is_signed_in=True)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_visitors_first_visit_to_organization_in_election(self, organization_we_vote_id, google_civic_election_id):
        """
        Entries are marked "first_visit_today" if it is the first visit in one day
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(Q(action_constant=ACTION_VOTER_GUIDE_VISIT) |
                                             Q(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW))
            count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(first_visit_today=True)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_new_followers_in_election(self, google_civic_election_id, organization_we_vote_id=""):
        """
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(Q(action_constant=ACTION_ORGANIZATION_FOLLOW) |
                                             Q(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW))
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_new_auto_followers_in_election(self, google_civic_election_id, organization_we_vote_id=""):
        """
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW)
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_action_count(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_ballot_visited(self, voter_we_vote_id, google_civic_election_id=0, organization_we_vote_id=''):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_welcome_visited(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(action_constant=ACTION_WELCOME_VISIT)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_days_visited(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.values('date_as_integer').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_last_action_date(self, voter_we_vote_id):
        last_action_date = None
        try:
            fetch_query = AnalyticsAction.objects.using('analytics').all()
            fetch_query = fetch_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            fetch_query = fetch_query.order_by('-id')
            fetch_query = fetch_query[:1]
            fetch_result = list(fetch_query)
            analytics_action = fetch_result.pop()
            last_action_date = analytics_action.exact_time
        except Exception as e:
            pass
        return last_action_date

    def fetch_voter_voter_guides_viewed(self, voter_we_vote_id):
        count_result = 0
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
            count_query = count_query.values('organization_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_guides_viewed(
            self, google_civic_election_id=0, limit_to_one_date_as_integer=0, count_through_this_date_as_integer=0):
        count_result = 0
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
            if positive_value_exists(limit_to_one_date_as_integer):
                count_query = count_query.filter(date_as_integer=limit_to_one_date_as_integer)
            elif positive_value_exists(count_through_this_date_as_integer):
                count_query = count_query.filter(date_as_integer__lte=count_through_this_date_as_integer)
            count_query = count_query.values('organization_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result


class AnalyticsManager(models.Model):

    def create_action_type1(
            self, action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
            organization_we_vote_id, organization_id, google_civic_election_id,
            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
            ballot_item_we_vote_id="", voter_device_id=None):
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
                is_signed_in=is_signed_in,
                state_code=state_code,
                organization_we_vote_id=organization_we_vote_id,
                organization_id=organization_id,
                google_civic_election_id=google_civic_election_id,
                ballot_item_we_vote_id=ballot_item_we_vote_id,
                user_agent=user_agent_string,
                is_bot=is_bot,
                is_mobile=is_mobile,
                is_desktop=is_desktop,
                is_tablet=is_tablet
            )
            success = True
            action_saved = True
            status += 'ACTION_TYPE1_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_ACTION_TYPE1 ' + str(e) + ' '

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results

    def create_action_type2(
            self, action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
            organization_we_vote_id, google_civic_election_id,
            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
            ballot_item_we_vote_id, voter_device_id=None):
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
                is_signed_in=is_signed_in,
                state_code=state_code,
                organization_we_vote_id=organization_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                ballot_item_we_vote_id=ballot_item_we_vote_id,
                user_agent=user_agent_string,
                is_bot=is_bot,
                is_mobile=is_mobile,
                is_desktop=is_desktop,
                is_tablet=is_tablet
            )
            success = True
            action_saved = True
            status += 'ACTION_TYPE2_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_ACTION_TYPE2 '

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results

    def retrieve_analytics_action_list(self, voter_we_vote_id='', voter_we_vote_id_list=[], google_civic_election_id=0,
                                       organization_we_vote_id='', action_constant='', distinct_for_members=False):
        success = False
        status = ""
        analytics_action_list = []

        try:
            list_query = AnalyticsAction.objects.using('analytics').all()
            if positive_value_exists(voter_we_vote_id):
                list_query = list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            elif len(voter_we_vote_id_list):
                list_query = list_query.filter(voter_we_vote_id__in=voter_we_vote_id_list)
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                list_query = list_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(action_constant):
                list_query = list_query.filter(action_constant=action_constant)
            if positive_value_exists(distinct_for_members):
                list_query = list_query.distinct(
                    'google_civic_election_id', 'organization_we_vote_id', 'voter_we_vote_id')
            analytics_action_list = list(list_query)
            analytics_action_list_found = True
        except Exception as e:
            analytics_action_list_found = False

        results = {
            'success':                      success,
            'status':                       status,
            'analytics_action_list':        analytics_action_list,
            'analytics_action_list_found':  analytics_action_list_found,
        }
        return results

    def retrieve_organization_election_metrics_list(self, google_civic_election_id=0):
        success = False
        status = ""
        organization_election_metrics_list = []

        try:
            list_query = OrganizationElectionMetrics.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            organization_election_metrics_list = list(list_query)
            organization_election_metrics_list_found = True
        except Exception as e:
            organization_election_metrics_list_found = False

        results = {
            'success':                      success,
            'status':                       status,
            'organization_election_metrics_list':        organization_election_metrics_list,
            'organization_election_metrics_list_found':  organization_election_metrics_list_found,
        }
        return results

    def retrieve_sitewide_election_metrics_list(self, google_civic_election_id=0):
        success = False
        status = ""
        sitewide_election_metrics_list = []

        try:
            list_query = SitewideElectionMetrics.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            sitewide_election_metrics_list = list(list_query)
            success = True
            sitewide_election_metrics_list_found = True
        except Exception as e:
            sitewide_election_metrics_list_found = False

        results = {
            'success':                      success,
            'status':                       status,
            'sitewide_election_metrics_list':        sitewide_election_metrics_list,
            'sitewide_election_metrics_list_found':  sitewide_election_metrics_list_found,
        }
        return results

    def retrieve_list_of_dates_with_actions(self, date_as_integer, through_date_as_integer=0):
        success = False
        status = ""
        date_list = []

        try:
            date_list_query = AnalyticsAction.objects.using('analytics').all()
            date_list_query = date_list_query.filter(date_as_integer__gte=date_as_integer)
            if positive_value_exists(through_date_as_integer):
                date_list_query = date_list_query.filter(date_as_integer__lte=through_date_as_integer)
            date_list_query = date_list_query.values('date_as_integer').distinct()
            date_list = list(date_list_query)
            date_list_found = True
        except Exception as e:
            date_list_found = False

        modified_date_list = []
        for date_as_integer_dict in date_list:
            if positive_value_exists(date_as_integer_dict['date_as_integer']):
                modified_date_list.append(date_as_integer_dict['date_as_integer'])

        results = {
            'success':                      success,
            'status':                       status,
            'date_as_integer_list':         modified_date_list,
            'date_as_integer_list_found':   date_list_found,
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

        modified_organization_list = []
        for organization_dict in organization_list:
            if positive_value_exists(organization_dict['organization_we_vote_id']):
                modified_organization_list.append(organization_dict['organization_we_vote_id'])

        results = {
            'success':                              success,
            'status':                               status,
            'organization_we_vote_id_list':         modified_organization_list,
            'organization_we_vote_id_list_found':   organization_list_found,
        }
        return results

    def retrieve_voter_we_vote_id_list_with_changes_since(self, date_as_integer, through_date_as_integer):
        success = True
        status = ""
        voter_list = []

        try:
            voter_list_query = AnalyticsAction.objects.using('analytics').all()
            voter_list_query = voter_list_query.filter(date_as_integer__gte=date_as_integer)
            voter_list_query = voter_list_query.filter(date_as_integer__lte=through_date_as_integer)
            voter_list_query = voter_list_query.values('voter_we_vote_id').distinct()
            # voter_list_query = voter_list_query[:5]  # TEMP limit to 5
            voter_list = list(voter_list_query)
            voter_list_found = True
        except Exception as e:
            success = False
            voter_list_found = False

        modified_voter_list = []
        for voter_dict in voter_list:
            if positive_value_exists(voter_dict['voter_we_vote_id']):
                modified_voter_list.append(voter_dict['voter_we_vote_id'])

        results = {
            'success':                       success,
            'status':                        status,
            'voter_we_vote_id_list':         modified_voter_list,
            'voter_we_vote_id_list_found':   voter_list_found,
        }
        return results

    def save_action(self, action_constant, voter_we_vote_id, voter_id, is_signed_in=False, state_code="",
                    organization_we_vote_id="", organization_id=0, google_civic_election_id=0,
                    user_agent_string="", is_bot=False, is_mobile=False, is_desktop=False, is_tablet=False,
                    ballot_item_we_vote_id="", voter_device_id=None):
        # If a voter_device_id is passed in, it is because this action may be coming from
        #  https://analytics.wevoteusa.org and hasn't been authenticated yet
        # Confirm that we have a valid voter_device_id. If not, store the action with the voter_device_id so we can
        #  look up later.

        # If either voter identifier comes in, make sure we have both

        # If either organization identifier comes in, make sure we have both

        if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS:
            # In the future we could reduce clutter in the AnalyticsAction table by only storing one entry per day
            return self.create_action_type1(action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
                                            organization_we_vote_id, organization_id, google_civic_election_id,
                                            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
                                            ballot_item_we_vote_id, voter_device_id)
        else:
            return self.create_action_type2(action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
                                            organization_we_vote_id, google_civic_election_id,
                                            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
                                            ballot_item_we_vote_id, voter_device_id)

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
        success = True
        status = ""
        sitewide_daily_metrics_saved = False
        sitewide_daily_metrics = SitewideDailyMetrics()

        if positive_value_exists(sitewide_daily_metrics_values['date_as_integer']):
            date_as_integer = sitewide_daily_metrics_values['date_as_integer']

            try:
                sitewide_daily_metrics, created = SitewideDailyMetrics.objects.using('analytics').update_or_create(
                    date_as_integer=date_as_integer,
                    defaults=sitewide_daily_metrics_values
                )
                sitewide_daily_metrics_saved = True
            except Exception as e:
                success = False
                status += 'SITEWIDE_DAILY_METRICS_UPDATE_OR_CREATE_FAILED '
        else:
            status += "SITEWIDE_DAILY_METRICS-MISSING_DATE_AS_INTEGER "

        results = {
            'success':                      success,
            'status':                       status,
            'sitewide_daily_metrics_saved': sitewide_daily_metrics_saved,
            'sitewide_daily_metrics':       sitewide_daily_metrics,
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

    def save_sitewide_voter_metrics_values_for_one_voter(self, sitewide_voter_metrics_values):
        success = False
        status = ""
        metrics_saved = False

        if positive_value_exists(sitewide_voter_metrics_values['voter_we_vote_id']):
            voter_we_vote_id = sitewide_voter_metrics_values['voter_we_vote_id']

            try:
                metrics_saved, created = SitewideVoterMetrics.objects.using('analytics').update_or_create(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    defaults=sitewide_voter_metrics_values
                )
                success = True
            except Exception as e:
                success = False
                status += 'SITEWIDE_VOTER_METRICS_UPDATE_OR_CREATE_FAILED ' + str(e) + ' '
                results = {
                    'success': success,
                    'status': status,
                    'metrics_saved': metrics_saved,
                }
                return results

        else:
            status += "SITEWIDE_VOTER_METRICS_SAVE-MISSING_VOTER_WE_VOTE_ID "

        results = {
            'success': success,
            'status': status,
            'metrics_saved': metrics_saved,
        }
        return results

    def sitewide_voter_metrics_for_this_voter_updated_this_date(self, voter_we_vote_id, updated_date_integer):
        updated_on_date_query = SitewideVoterMetrics.objects.using('analytics').filter(
            voter_we_vote_id__iexact=voter_we_vote_id,
            last_calculated_date_as_integer=updated_date_integer
        )
        return positive_value_exists(updated_on_date_query.count())

    def update_first_visit_today_for_all_voters_since_date(self, date_as_integer, through_date_as_integer):
        success = True
        status = ""
        distinct_days_list = []
        first_visit_today_count = 0

        # Get distinct days
        try:
            distinct_days_query = AnalyticsAction.objects.using('analytics').all()
            distinct_days_query = distinct_days_query.filter(date_as_integer__gte=date_as_integer)
            distinct_days_query = distinct_days_query.filter(date_as_integer__lte=through_date_as_integer)
            distinct_days_query = distinct_days_query.values('date_as_integer').distinct()
            # distinct_days_query = distinct_days_query[:5]  # TEMP limit to 5
            distinct_days_list = list(distinct_days_query)
            distinct_days_found = True
        except Exception as e:
            success = False
            status += "UPDATE_FIRST_VISIT_TODAY-DISTINCT_DAY_QUERY_ERROR "
            distinct_days_found = False

        simple_distinct_days_list = []
        for day_dict in distinct_days_list:
            if positive_value_exists(day_dict['date_as_integer']):
                simple_distinct_days_list.append(day_dict['date_as_integer'])

        # Loop through each day
        for one_date_as_integer in simple_distinct_days_list:
            # Get distinct voters on that day
            if not positive_value_exists(one_date_as_integer):
                continue

            voter_list = []
            try:
                voter_list_query = AnalyticsAction.objects.using('analytics').all()
                voter_list_query = voter_list_query.filter(date_as_integer=one_date_as_integer)
                voter_list_query = voter_list_query.values('voter_we_vote_id').distinct()
                # voter_list_query = voter_list_query[:5]  # TEMP limit to 5
                voter_list = list(voter_list_query)
                voter_list_found = True
            except Exception as e:
                success = False
                status += "UPDATE_FIRST_VISIT_TODAY-DISTINCT_VOTER_QUERY_ERROR "
                voter_list_found = False

            simple_voter_list = []
            for voter_dict in voter_list:
                if positive_value_exists(voter_dict['voter_we_vote_id']) and \
                        voter_dict['voter_we_vote_id'] not in simple_voter_list:
                    simple_voter_list.append(voter_dict['voter_we_vote_id'])

            if not voter_list_found:
                continue

            # Loop through each voter per day, and update the first entry for that day with "first_visit_today=True"
            for voter_we_vote_id in simple_voter_list:
                if not positive_value_exists(voter_we_vote_id):
                    continue

                try:
                    first_visit_query = AnalyticsAction.objects.using('analytics').all()
                    first_visit_query = first_visit_query.order_by("id")  # order by oldest first
                    first_visit_query = first_visit_query.filter(date_as_integer=one_date_as_integer)
                    first_visit_query = first_visit_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
                    analytics_action = first_visit_query.first()

                    if not analytics_action.first_visit_today:
                        analytics_action.first_visit_today = True
                        analytics_action.save()
                        first_visit_saved = True
                        first_visit_today_count += 1
                except Exception as e:
                    success = False
                    status += "UPDATE_FIRST_VISIT_TODAY-VOTER_ON_DATE_QUERY_ERROR "
                    print_to_log(logger=logger, exception_message_optional=status)
                    first_visit_found = False

        results = {
            'success':                  success,
            'status':                   status,
            'first_visit_today_count':  first_visit_today_count,
        }
        return results

    def update_first_visit_today_for_one_voter(self, voter_we_vote_id):
        success = False
        status = ""
        distinct_days_list = []
        first_visit_today_count = 0

        # Get distinct days
        try:
            distinct_days_query = AnalyticsAction.objects.using('analytics').all()
            distinct_days_query = distinct_days_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            distinct_days_query = distinct_days_query.values('date_as_integer').distinct()
            distinct_days_list = list(distinct_days_query)
        except Exception as e:
            pass

        simple_distinct_days_list = []
        for day_dict in distinct_days_list:
            if positive_value_exists(day_dict['date_as_integer']):
                simple_distinct_days_list.append(day_dict['date_as_integer'])

        # Loop through each day
        for one_date_as_integer in simple_distinct_days_list:
            try:
                first_visit_query = AnalyticsAction.objects.using('analytics').all()
                first_visit_query = first_visit_query.order_by("id")  # order by oldest first
                first_visit_query = first_visit_query.filter(date_as_integer=one_date_as_integer)
                first_visit_query = first_visit_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
                analytics_action = first_visit_query.first()

                analytics_action.first_visit_today = True
                analytics_action.save()
                first_visit_today_count += 1
            except Exception as e:
                pass

        results = {
            'success': success,
            'status': status,
            'first_visit_today_count': first_visit_today_count,
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
    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today", null=True, unique=False)
    authenticated_visitors_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
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

    auto_followers_total = models.PositiveIntegerField(verbose_name="all",
                                                                   null=True, unique=False)
    new_auto_followers_today = models.PositiveIntegerField(verbose_name="today",
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
    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_entrants = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_at_time_of_election = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    new_followers = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    new_auto_followers = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_visited_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_visited_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    entrants_took_position = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_public_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_public_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_friends_only_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_friends_only_positions_with_comments = models.PositiveIntegerField(
        verbose_name="", null=True, unique=False)

    followers_took_position = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_public_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_public_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_friends_only_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_friends_only_positions_with_comments = models.PositiveIntegerField(
        verbose_name="", null=True, unique=False)

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            # We retrieve this from the read-only database (as opposed to the analytics database)
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            return
        except Election.DoesNotExist:
            return
        return election

    def organization(self):
        if positive_value_exists(self.organization_we_vote_id):
            try:
                organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
            except Organization.MultipleObjectsReturned as e:
                logger.error("analytics.organization Found multiple")
                return
            except Organization.DoesNotExist:
                logger.error("analytics.organization did not find")
                return
            return organization
        else:
            return Organization()


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

    ballot_views_today = models.PositiveIntegerField(verbose_name="number of voters who viewed a ballot today",
                                                       null=True, unique=False)
    voter_guides_viewed_total = models.PositiveIntegerField(verbose_name="number of voter guides viewed, all time",
                                                            null=True, unique=False)
    voter_guides_viewed_today = models.PositiveIntegerField(verbose_name="number of voter guides viewed, today",
                                                            null=True, unique=False)

    issues_followed_total = models.PositiveIntegerField(verbose_name="number of issues followed, all time",
                                                        null=True, unique=False)
    issues_followed_today = models.PositiveIntegerField(verbose_name="issues followed today, today",
                                                        null=True, unique=False)

    issue_follows_total = models.PositiveIntegerField(verbose_name="one follow for one issue, all time",
                                                      null=True, unique=False)
    issue_follows_today = models.PositiveIntegerField(verbose_name="one follow for one issue, today",
                                                      null=True, unique=False)

    organizations_followed_total = models.PositiveIntegerField(verbose_name="voter follow organizations, all time",
                                                               null=True, unique=False)
    organizations_followed_today = models.PositiveIntegerField(verbose_name="voter follow organizations, today",
                                                               null=True, unique=False)

    organizations_auto_followed_total = models.PositiveIntegerField(verbose_name="auto_follow organizations, all",
                                                                    null=True, unique=False)
    organizations_auto_followed_today = models.PositiveIntegerField(verbose_name="auto_follow organizations, today",
                                                                    null=True, unique=False)

    organizations_with_linked_issues = models.PositiveIntegerField(verbose_name="organizations linked to issues, all",
                                                                   null=True, unique=False)

    issues_linked_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    issues_linked_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

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
    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_entries = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_views = models.PositiveIntegerField(verbose_name="one person viewed one voter guide, this election",
                                                    null=True, unique=False)
    voter_guides_viewed = models.PositiveIntegerField(verbose_name="one org, seen at least once, this election",
                                                      null=True, unique=False)

    issues_followed = models.PositiveIntegerField(verbose_name="follow issue connections, all time",
                                                  null=True, unique=False)

    unique_voters_that_followed_organizations = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    unique_voters_that_auto_followed_organizations = models.PositiveIntegerField(verbose_name="",
                                                                                 null=True, unique=False)
    organizations_followed = models.PositiveIntegerField(verbose_name="voter follow organizations, today",
                                                               null=True, unique=False)
    organizations_auto_followed = models.PositiveIntegerField(verbose_name="auto_follow organizations, today",
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
    public_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    public_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    friends_only_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    friends_only_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entered_full_address = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            # We retrieve this from the read-only database (as opposed to the analytics database)
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            return
        except Election.DoesNotExist:
            return
        return election

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


class SitewideVoterMetrics(models.Model):
    """
    A single entry per voter summarizing all activity every done on We Vote
    """
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id",
        max_length=255, default=None, null=True, blank=True, unique=False, db_index=True)
    actions_count = models.PositiveIntegerField(verbose_name="all", null=True, unique=False, db_index=True)
    elections_viewed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    voter_guides_viewed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    ballot_visited = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    welcome_visited = models.PositiveIntegerField(verbose_name="all", null=True, unique=False, db_index=True)
    entered_full_address = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    issues_followed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    organizations_followed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    time_until_sign_in = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    positions_entered_friends_only = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    positions_entered_public = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    comments_entered_friends_only = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    comments_entered_public = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    signed_in_twitter = models.BooleanField(verbose_name='', default=False)
    signed_in_facebook = models.BooleanField(verbose_name='', default=False)
    signed_in_with_email = models.BooleanField(verbose_name='', default=False)
    seconds_on_site = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    days_visited = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    last_action_date = models.DateTimeField(verbose_name='last action date and time', null=True, db_index=True)
    last_calculated_date_as_integer = models.PositiveIntegerField(
        verbose_name="YYYYMMDD of the last time stats calculated", null=True, unique=False, db_index=True)

    def generate_last_calculated_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        day_as_string = "{:d}{:02d}{:02d}".format(
            datetime_now.year,
            datetime_now.month,
            datetime_now.day,
        )
        self.last_calculated_date_as_integer = convert_to_int(day_as_string)
        return


def display_action_constant_human_readable(action_constant):
    if action_constant == ACTION_ABOUT_GETTING_STARTED:
        return "ABOUT_GETTING_STARTED"
    if action_constant == ACTION_ABOUT_MOBILE:
        return "ABOUT_MOBILE"
    if action_constant == ACTION_ABOUT_ORGANIZATION:
        return "ABOUT_ORGANIZATION"
    if action_constant == ACTION_ABOUT_TEAM:
        return "ABOUT_TEAM"
    if action_constant == ACTION_ABOUT_VISION:
        return "ABOUT_VISION"
    if action_constant == ACTION_ACCOUNT_PAGE:
        return "ACCOUNT_PAGE"
    if action_constant == ACTION_BALLOT_VISIT:
        return "BALLOT_VISIT"
    if action_constant == ACTION_CANDIDATE:
        return "CANDIDATE"
    if action_constant == ACTION_DONATE_VISIT:
        return "DONATE_VISIT"
    if action_constant == ACTION_ELECTIONS:
        return "ELECTIONS"
    if action_constant == ACTION_EMAIL_AUTHENTICATION_EXISTS:
        return "EMAIL_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_FACEBOOK_AUTHENTICATION_EXISTS:
        return "FACEBOOK_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_FACEBOOK_INVITABLE_FRIENDS:
        return "FACEBOOK_INVITABLE_FRIENDS"
    if action_constant == ACTION_FRIEND_ENTRY:
        return "FRIEND_ENTRY"
    if action_constant == ACTION_GOOGLE_AUTHENTICATION_EXISTS:
        return "GOOGLE_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_INVITE_BY_EMAIL:
        return "INVITE_BY_EMAIL"
    if action_constant == ACTION_ISSUE_FOLLOW:
        return "ISSUE_FOLLOW"
    if action_constant == ACTION_ISSUE_FOLLOW_IGNORE:
        return "ISSUE_FOLLOW_IGNORE"
    if action_constant == ACTION_ISSUE_STOP_FOLLOWING:
        return "ISSUE_STOP_FOLLOWING"
    if action_constant == ACTION_MODAL_ISSUES:
        return "MODAL_ISSUES"
    if action_constant == ACTION_MODAL_ORGANIZATIONS:
        return "MODAL_ORGANIZATIONS"
    if action_constant == ACTION_MODAL_POSITIONS:
        return "MODAL_POSITIONS"
    if action_constant == ACTION_MODAL_FRIENDS:
        return "MODAL_FRIENDS"
    if action_constant == ACTION_MODAL_SHARE:
        return "MODAL_SHARE"
    if action_constant == ACTION_MODAL_VOTE:
        return "MODAL_VOTE"
    if action_constant == ACTION_NETWORK:
        return "NETWORK"
    if action_constant == ACTION_OFFICE:
        return "OFFICE"
    if action_constant == ACTION_ORGANIZATION_AUTO_FOLLOW:
        return "ORGANIZATION_AUTO_FOLLOW"
    if action_constant == ACTION_ORGANIZATION_FOLLOW:
        return "ORGANIZATION_FOLLOW"
    if action_constant == ACTION_ORGANIZATION_FOLLOW_IGNORE:
        return "ORGANIZATION_FOLLOW_IGNORE"
    if action_constant == ACTION_ORGANIZATION_STOP_FOLLOWING:
        return "ORGANIZATION_STOP_FOLLOWING"
    if action_constant == ACTION_ORGANIZATION_STOP_IGNORING:
        return "ORGANIZATION_STOP_IGNORING"
    if action_constant == ACTION_POSITION_TAKEN:
        return "POSITION_TAKEN"
    if action_constant == ACTION_TWITTER_AUTHENTICATION_EXISTS:
        return "TWITTER_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_VOTER_FACEBOOK_AUTH:
        return "VOTER_FACEBOOK_AUTH"
    if action_constant == ACTION_VOTER_GUIDE_ENTRY:
        return "VOTER_GUIDE_ENTRY"
    if action_constant == ACTION_VOTER_GUIDE_GET_STARTED:
        return "VOTER_GUIDE_GET_STARTED"
    if action_constant == ACTION_VOTER_GUIDE_VISIT:
        return "VOTER_GUIDE_VISIT"
    if action_constant == ACTION_VOTER_TWITTER_AUTH:
        return "VOTER_TWITTER_AUTH"
    if action_constant == ACTION_WELCOME_ENTRY:
        return "WELCOME_ENTRY"
    if action_constant == ACTION_WELCOME_VISIT:
        return "WELCOME_VISIT"

    return "ACTION_CONSTANT:" + str(action_constant)
