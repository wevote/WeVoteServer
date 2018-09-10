# follow/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from django.db import models
from election.models import ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from issue.models import IssueManager
from organization.models import OrganizationManager
import pytz
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from voter.models import VoterManager


FOLLOWING = 'FOLLOWING'
STOP_FOLLOWING = 'STOP_FOLLOWING'
FOLLOW_IGNORE = 'FOLLOW_IGNORE'
FOLLOWING_CHOICES = (
    (FOLLOWING,         'Following'),
    (STOP_FOLLOWING,    'Not Following'),
    (FOLLOW_IGNORE,     'Ignoring'),
)

# Kinds of lists of suggested organization
UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW = 'UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW'
UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW = 'UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW'
UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER = \
    'UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER'
UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS = 'UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS'
UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS_ON_TWITTER = \
    'UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS_ON_TWITTER'
UPDATE_SUGGESTIONS_ALL = 'UPDATE_SUGGESTIONS_ALL'

FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW = 'FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW'
FOLLOW_SUGGESTIONS_FROM_FRIENDS = 'FOLLOW_SUGGESTIONS_FROM_FRIENDS'
FOLLOW_SUGGESTIONS_FROM_FRIENDS_ON_TWITTER = 'FOLLOW_SUGGESTIONS_FROM_FRIENDS_ON_TWITTER'

logger = wevote_functions.admin.get_logger(__name__)


class FollowIssue(models.Model):
    # We are relying on built-in Python id field
    # The voter following the issue
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False, db_index=True)

    # NOTE: we will use the organization_we_vote_id in FollowIssue if we decide to let a voter publish to
    # the public the issues they follow. 2017-09 NOT CURRENTLY SUPPORTED
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # The issue being followed
    issue_id = models.PositiveIntegerField(null=True, blank=True)

    # This is used when we want to export the issues that are being following
    issue_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # Is this person following, not following, or ignoring this issue?
    following_status = models.CharField(max_length=15, choices=FOLLOWING_CHOICES, default=FOLLOWING, db_index=True)

    # Is the fact that this issue is being followed visible to the public (if linked to organization)?
    is_follow_visible_publicly = models.BooleanField(verbose_name='', default=False)

    # The date the voter followed or stopped following this issue
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)

    def __unicode__(self):
        return self.issue_we_vote_id

    def is_following(self):
        if self.following_status == FOLLOWING:
            return True
        return False

    def is_not_following(self):
        if self.following_status == STOP_FOLLOWING:
            return True
        return False

    def is_ignoring(self):
        if self.following_status == FOLLOW_IGNORE:
            return True
        return False


class FollowIssueManager(models.Model):

    def __unicode__(self):
        return "FollowIssueManager"

    def toggle_on_voter_following_issue(self, voter_we_vote_id, issue_id, issue_we_vote_id):
        following_status = FOLLOWING
        follow_issue_manager = FollowIssueManager()
        return follow_issue_manager.toggle_following_issue(voter_we_vote_id, issue_id, issue_we_vote_id,
                                                           following_status)

    def toggle_off_voter_following_issue(self, voter_we_vote_id, issue_id, issue_we_vote_id):
        following_status = STOP_FOLLOWING
        follow_issue_manager = FollowIssueManager()
        return follow_issue_manager.toggle_following_issue(voter_we_vote_id, issue_id, issue_we_vote_id,
                                                           following_status)

    def toggle_ignore_voter_following_issue(self, voter_we_vote_id, issue_id, issue_we_vote_id):
        following_status = FOLLOW_IGNORE
        follow_issue_manager = FollowIssueManager()
        return follow_issue_manager.toggle_following_issue(voter_we_vote_id, issue_id, issue_we_vote_id,
                                                           following_status)

    def toggle_following_issue(self, voter_we_vote_id, issue_id, issue_we_vote_id, following_status):
        follow_issue_on_stage_found = False
        follow_issue_changed = False
        follow_issue_on_stage_id = 0
        follow_issue_on_stage = FollowIssue()
        status = ''

        issue_identifier_exists = positive_value_exists(issue_we_vote_id) or positive_value_exists(issue_id)
        if not positive_value_exists(voter_we_vote_id) and not issue_identifier_exists:
            results = {
                'success': True if follow_issue_on_stage_found else False,
                'status': 'Insufficient inputs to toggle issue link, try passing ids for voter and issue ',
                'follow_issue_found': follow_issue_on_stage_found,
                'follow_issue_id': follow_issue_on_stage_id,
                'follow_issue': follow_issue_on_stage,
            }
            return results

        # Does a follow_issue entry exist from this voter already exist?
        follow_issue_manager = FollowIssueManager()
        follow_issue_id = 0
        results = follow_issue_manager.retrieve_follow_issue(follow_issue_id, voter_we_vote_id, issue_id,
                                                             issue_we_vote_id)
        if results['MultipleObjectsReturned']:
            status += 'TOGGLE_FOLLOWING_ISSUE MultipleObjectsReturned ' + following_status
            delete_results = follow_issue_manager.delete_follow_issue(
                follow_issue_id, voter_we_vote_id, issue_id, issue_we_vote_id)
            status += delete_results['status']

            results = follow_issue_manager.retrieve_follow_issue(follow_issue_id, voter_we_vote_id, issue_id,
                                                                 issue_we_vote_id)

        if results['follow_issue_found']:
            follow_issue_on_stage = results['follow_issue']

            # Update this follow_issue entry with new values - we do not delete because we might be able to use
            try:
                follow_issue_on_stage.following_status = following_status
                # We don't need to update here because set set auto_now=True in the field
                # follow_issue_on_stage.date_last_changed =
                follow_issue_on_stage.save()
                follow_issue_changed = True
                follow_issue_on_stage_id = follow_issue_on_stage.id
                follow_issue_on_stage_found = True
                status += 'FOLLOW_STATUS_UPDATED_AS ' + following_status
            except Exception as e:
                status += 'FAILED_TO_UPDATE ' + following_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        elif results['DoesNotExist']:
            try:
                # Create new follow_issue entry
                # First make sure that issue_id is for a valid issue
                issue_manager = IssueManager()
                if positive_value_exists(issue_id):
                    results = issue_manager.retrieve_issue(issue_id)
                else:
                    results = issue_manager.retrieve_issue(0, issue_we_vote_id)
                if results['issue_found']:
                    issue = results['issue']
                    follow_issue_on_stage = FollowIssue(
                        voter_we_vote_id=voter_we_vote_id,
                        issue_id=issue.id,
                        issue_we_vote_id=issue.we_vote_id,
                        following_status=following_status,
                    )
                    # if auto_followed_from_twitter_suggestion:
                    #     follow_issue_on_stage.auto_followed_from_twitter_suggestion = True
                    follow_issue_on_stage.save()
                    follow_issue_changed = True
                    follow_issue_on_stage_id = follow_issue_on_stage.id
                    follow_issue_on_stage_found = True
                    status += 'CREATE ' + following_status
                else:
                    status = 'ISSUE_NOT_FOUND_ON_CREATE ' + following_status
            except Exception as e:
                status += 'FAILED_TO_UPDATE ' + following_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status += results['status']

        results = {
            'success':               True if follow_issue_on_stage_found else False,
            'status':                status,
            'follow_issue_found':    follow_issue_on_stage_found,
            'follow_issue_id':       follow_issue_on_stage_id,
            'follow_issue':          follow_issue_on_stage,
        }
        return results

    def retrieve_follow_issue(self, follow_issue_id, voter_we_vote_id, issue_id, issue_we_vote_id):
        """
        follow_issue_id is the identifier for records stored in this table (it is NOT the issue_id)
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        follow_issue_on_stage = FollowIssue()
        follow_issue_on_stage_id = 0

        try:
            if positive_value_exists(follow_issue_id):
                follow_issue_on_stage = FollowIssue.objects.get(id=follow_issue_id)
                follow_issue_on_stage_id = issue_id.id
                success = True
                status = 'FOLLOW_ISSUE_FOUND_WITH_ID'
            elif positive_value_exists(voter_we_vote_id) and positive_value_exists(issue_id):
                follow_issue_on_stage = FollowIssue.objects.get(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    issue_id=issue_id)
                follow_issue_on_stage_id = follow_issue_on_stage.id
                success = True
                status = 'FOLLOW_ISSUE_FOUND_WITH_VOTER_WE_VOTE_ID_AND_ISSUE_ID'
            elif positive_value_exists(voter_we_vote_id) and positive_value_exists(issue_we_vote_id):
                follow_issue_on_stage = FollowIssue.objects.get(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    issue_we_vote_id__iexact=issue_we_vote_id)
                follow_issue_on_stage_id = follow_issue_on_stage.id
                success = True
                status = 'FOLLOW_ISSUE_FOUND_WITH_VOTER_WE_VOTE_ID_AND_ISSUE_WE_VOTE_ID'
            else:
                success = False
                status = 'FOLLOW_ISSUE_MISSING_REQUIRED_VARIABLES'
        except FollowIssue.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = 'FOLLOW_ISSUE_NOT_FOUND_MultipleObjectsReturned'
        except FollowIssue.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = 'FOLLOW_ISSUE_NOT_FOUND_DoesNotExist'

        if positive_value_exists(follow_issue_on_stage_id):
            follow_issue_on_stage_found = True
            is_following = follow_issue_on_stage.is_following()
            is_not_following = follow_issue_on_stage.is_not_following()
            is_ignoring = follow_issue_on_stage.is_ignoring()
        else:
            follow_issue_on_stage_found = False
            is_following = False
            is_not_following = True
            is_ignoring = False
        results = {
            'status':                       status,
            'success':                      success,
            'follow_issue_found':           follow_issue_on_stage_found,
            'follow_issue_id':              follow_issue_on_stage_id,
            'follow_issue':                 follow_issue_on_stage,
            'is_following':                 is_following,
            'is_not_following':             is_not_following,
            'is_ignoring':                  is_ignoring,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def delete_follow_issue(self, follow_issue_id, voter_we_vote_id, issue_id, issue_we_vote_id):
        """
        Remove any follow issue entries (we may have duplicate entries)
        """
        follow_issue_deleted = False
        status = ''

        try:
            if positive_value_exists(follow_issue_id):
                follow_issue_on_stage = FollowIssue.objects.get(id=follow_issue_id)
                follow_issue_on_stage.delete()
                follow_issue_deleted = True
                success = True
                status += 'FOLLOW_ISSUE_DELETED_BY_ID '
            elif positive_value_exists(voter_we_vote_id) and positive_value_exists(issue_id):
                follow_issue_query = FollowIssue.objects.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    issue_id=issue_id)
                follow_issue_list = list(follow_issue_query)
                for one_follow_issue in follow_issue_list:
                    one_follow_issue.delete()
                    follow_issue_deleted = True
                success = True
                status += 'FOLLOW_ISSUE_DELETED_BY_VOTER_WE_VOTE_ID_AND_ISSUE_ID '
            elif positive_value_exists(voter_we_vote_id) and positive_value_exists(issue_we_vote_id):
                follow_issue_query = FollowIssue.objects.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    issue_we_vote_id__iexact=issue_we_vote_id)
                follow_issue_list = list(follow_issue_query)
                for one_follow_issue in follow_issue_list:
                    one_follow_issue.delete()
                    follow_issue_deleted = True
                success = True
                status += 'FOLLOW_ISSUE_DELETE_BY_VOTER_WE_VOTE_ID_AND_ISSUE_WE_VOTE_ID '
            else:
                success = False
                status += 'FOLLOW_ISSUE_DELETE_MISSING_REQUIRED_VARIABLES '
        except FollowIssue.DoesNotExist:
            success = True
            status = 'FOLLOW_ISSUE_DELETE_NOT_FOUND_DoesNotExist '

        results = {
            'status':               status,
            'success':              success,
            'follow_issue_deleted': follow_issue_deleted,
        }
        return results

    def create_or_update_suggested_issue_to_follow(self, viewer_voter_we_vote_id, issue_we_vote_id,
                                                   from_twitter=False):
        """
        Create or update the SuggestedIssueToFollow table with suggested issues from twitter ids i follow
        or issue of my friends follow.
        :param viewer_voter_we_vote_id:
        :param issue_we_vote_id:
        :param from_twitter:
        :return:
        """
        try:
            suggested_issue_to_follow, created = SuggestedIssueToFollow.objects.update_or_create(
                viewer_voter_we_vote_id=viewer_voter_we_vote_id,
                issue_we_vote_id=issue_we_vote_id,
                defaults={
                    'viewer_voter_we_vote_id':  viewer_voter_we_vote_id,
                    'issue_we_vote_id':  issue_we_vote_id,
                    'from_twitter':             from_twitter
                }
            )
            suggested_issue_to_follow_saved = True
            success = True
            status = "SUGGESTED_ISSUE_TO_FOLLOW_UPDATED"
        except Exception:
            suggested_issue_to_follow_saved = False
            suggested_issue_to_follow = SuggestedIssueToFollow()
            success = False
            status = "SUGGESTED_ISSUE_TO_FOLLOW_NOT_UPDATED"
        results = {
            'success':                                  success,
            'status':                                   status,
            'suggested_issue_to_follow_saved':   suggested_issue_to_follow_saved,
            'suggested_issue_to_follow':         suggested_issue_to_follow,
        }
        return results

    def retrieve_suggested_issue_to_follow_list(self, viewer_voter_we_vote_id, from_twitter=False):
        """
        Retrieving suggested issues who i follow from SuggestedOrganizationToFollow table.
        :param viewer_voter_we_vote_id:
        :param from_twitter:
        :return:
        """
        suggested_issue_to_follow_list = []
        try:
            suggested_issue_to_follow_queryset = SuggestedIssueToFollow.objects.all()
            suggested_issue_to_follow_list = suggested_issue_to_follow_queryset.filter(
                viewer_voter_we_vote_id__iexact=viewer_voter_we_vote_id,
                from_twitter=from_twitter)
            if len(suggested_issue_to_follow_list):
                success = True
                suggested_issue_to_follow_list_found = True
                status = "SUGGESTED_ISSUE_TO_FOLLOW_RETRIEVED"
            else:
                success = True
                suggested_issue_to_follow_list_found = False
                status = "NO_SUGGESTED_ISSUE_TO_FOLLOW_LIST_RETRIEVED"
        except SuggestedIssueToFollow.DoesNotExist:
            # No data found. Try again below
            success = True
            suggested_issue_to_follow_list_found = False
            status = 'NO_SUGGESTED_ISSUE_TO_FOLLOW_LIST_RETRIEVED_DoesNotExist'
        except Exception as e:
            success = False
            suggested_issue_to_follow_list_found = False
            status = "SUGGESTED_ISSUE_TO_FOLLOW_LIST_NOT_RETRIEVED"

        results = {
            'success':                               success,
            'status':                                status,
            'suggested_issue_to_follow_list_found':  suggested_issue_to_follow_list_found,
            'suggested_issue_to_follow_list':        suggested_issue_to_follow_list,
        }
        return results


class FollowMetricsManager(models.Model):

    def __unicode__(self):
        return "FollowMetricsManager"

    def fetch_organization_followers(self, organization_we_vote_id, google_civic_election_id=0):
        count_result = None
        try:
            count_query = FollowOrganization.objects.using('readonly').all()
            count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(following_status=FOLLOWING)
            count_query = count_query.values("voter_id").distinct()
            if positive_value_exists(google_civic_election_id):
                election_manager = ElectionManager()
                election_result = election_manager.retrieve_election(google_civic_election_id)
                if election_result['election_found']:
                    election = election_result['election']
                    timezone = pytz.timezone("America/Los_Angeles")
                    date_of_election = timezone.localize(datetime.strptime(election.election_day_text, "%Y-%m-%d"))
                    date_of_election += timedelta(days=1)  # Add one day, to catch the entire election day
                    # Find all of the follow entries before or on the day of the election
                    count_query = count_query.filter(date_last_changed__lte=date_of_election)
                else:
                    # Failed retrieving date, so we return 0
                    return 0
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_issues_followed(self, voter_we_vote_id='',
                              limit_to_one_date_as_integer=0, count_through_this_date_as_integer=0):
        timezone = pytz.timezone("America/Los_Angeles")
        if positive_value_exists(limit_to_one_date_as_integer):
            one_date_string = str(limit_to_one_date_as_integer)
            limit_to_one_date = timezone.localize(datetime.strptime(one_date_string, "%Y%m%d"))
        if positive_value_exists(count_through_this_date_as_integer):
            count_through_date_string = str(count_through_this_date_as_integer)
            count_through_this_date = timezone.localize(datetime.strptime(count_through_date_string, "%Y%m%d"))
        count_result = None
        try:
            count_query = FollowIssue.objects.using('readonly').all()
            if positive_value_exists(voter_we_vote_id):
                count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(following_status=FOLLOWING)
            if positive_value_exists(limit_to_one_date_as_integer):
                # TODO DALE THIS NEEDS WORK TO FIND ALL ENTRIES ON ONE DAY
                count_query = count_query.filter(date_last_changed=limit_to_one_date)
            elif positive_value_exists(count_through_this_date_as_integer):
                count_query = count_query.filter(date_last_changed__lte=count_through_this_date)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_organizations_followed(self, voter_id):
        count_result = None
        try:
            count_query = FollowOrganization.objects.using('readonly').all()
            count_query = count_query.filter(voter_id=voter_id)
            count_query = count_query.filter(following_status=FOLLOWING)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result


class FollowIssueList(models.Model):
    """
    A way to retrieve all of the follow_issue information
    """

    def fetch_follow_issue_count_by_voter_we_vote_id(self, voter_we_vote_id, following_status=None):
        if following_status is None:
            following_status = FOLLOWING
        follow_issue_list_length = 0
        try:
            follow_issue_list_query = FollowIssue.objects.using('readonly').all()
            follow_issue_list_query = follow_issue_list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            follow_issue_list_query = follow_issue_list_query.filter(following_status=following_status)
            follow_issue_list_length = follow_issue_list_query.count()

        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        return follow_issue_list_length

    def retrieve_follow_issue_list_by_voter_we_vote_id(self, voter_we_vote_id, following_status=None):
        """
        Retrieve a list of follow_issue entries for this voter
        :param voter_we_vote_id: 
        :param following_status:
        :return: a list of follow_issue objects for the voter_we_vote_id
        """
        follow_issue_list_found = False
        if following_status is None:
            following_status = FOLLOWING
        follow_issue_list = {}
        try:
            follow_issue_list_query = FollowIssue.objects.using('readonly').all()
            follow_issue_list_query = follow_issue_list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            if positive_value_exists(following_status):
                follow_issue_list = follow_issue_list_query.filter(following_status=following_status)
            if len(follow_issue_list):
                follow_issue_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if follow_issue_list_found:
            return follow_issue_list
        else:
            follow_issue_list = {}
            return follow_issue_list

    def retrieve_follow_issue_we_vote_id_list_by_voter_we_vote_id(self, voter_we_vote_id, following_status=None):
        follow_issue_we_vote_id_list = []
        follow_issue_we_vote_id_list_result = []
        if following_status is None:
            following_status = FOLLOWING

        try:
            follow_issue_list_query = FollowIssue.objects.using('readonly').all()
            follow_issue_list_query = follow_issue_list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            if positive_value_exists(following_status):
                follow_issue_list_query = follow_issue_list_query.filter(following_status=following_status)
            follow_issue_list_query = follow_issue_list_query.values("issue_we_vote_id").distinct()
            follow_issue_we_vote_id_list_result = list(follow_issue_list_query)

        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        for query in follow_issue_we_vote_id_list_result:
            follow_issue_we_vote_id_list.append(query["issue_we_vote_id"])

        return follow_issue_we_vote_id_list

    def fetch_follow_issue_following_count_by_voter_we_vote_id(self, voter_we_vote_id):
        following_status = FOLLOWING
        return self.fetch_follow_issue_count_by_voter_we_vote_id(voter_we_vote_id, following_status)

    def fetch_follow_issue_ignore_count_by_voter_we_vote_id(self, voter_we_vote_id):
        following_status = FOLLOW_IGNORE
        return self.fetch_follow_issue_count_by_voter_we_vote_id(voter_we_vote_id, following_status)

    def retrieve_follow_issue_ignore_list_by_voter_we_vote_id(self, voter_we_vote_id):
        following_status = FOLLOW_IGNORE
        return self.retrieve_follow_issue_list_by_voter_we_vote_id(voter_we_vote_id, following_status)

    def retrieve_follow_issue_following_we_vote_id_list_by_voter_we_vote_id(self, voter_we_vote_id):
        following_status = FOLLOWING
        return self.retrieve_follow_issue_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id, following_status)

    def retrieve_follow_issue_ignore_we_vote_id_list_by_voter_we_vote_id(self, voter_we_vote_id):
        following_status = FOLLOW_IGNORE
        return self.retrieve_follow_issue_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id, following_status)

    def retrieve_follow_issue_list_by_issue_id(self, issue_id):
        issue_we_vote_id = None
        following_status = FOLLOWING
        return self.retrieve_follow_issue_list(issue_id, issue_we_vote_id, following_status)

    def retrieve_follow_issue_following_list_by_issue_we_vote_id(self, issue_we_vote_id):
        issue_id = None
        following_status = FOLLOWING
        return self.retrieve_follow_issue_list(issue_id, issue_we_vote_id, following_status)

    def retrieve_follow_issue_list(self, issue_id, issue_we_vote_id, following_status):
        follow_issue_list_found = False
        follow_issue_list = {}
        try:
            follow_issue_list = FollowIssue.objects.using('readonly').all()
            if positive_value_exists(issue_id):
                follow_issue_list = follow_issue_list.filter(issue_id=issue_id)
            else:
                follow_issue_list = follow_issue_list.filter(issue_we_vote_id__iexact=issue_we_vote_id)
            if positive_value_exists(following_status):
                follow_issue_list = follow_issue_list.filter(following_status=following_status)
            if len(follow_issue_list):
                follow_issue_list_found = True
        except Exception as e:
            pass

        if follow_issue_list_found:
            return follow_issue_list
        else:
            follow_issue_list = {}
            return follow_issue_list


class FollowOrganization(models.Model):
    # We are relying on built-in Python id field
    # The voter following the organization
    voter_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    # The organization being followed
    organization_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    voter_linked_organization_we_vote_id = models.CharField(
        verbose_name="organization we vote permanent id",
        max_length=255, null=True, blank=True, unique=False, db_index=True)

    # This is used when we want to export the organizations that a voter is following
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False, db_index=True)

    # Is this person following or ignoring this organization?
    following_status = models.CharField(max_length=15, choices=FOLLOWING_CHOICES, default=FOLLOWING, db_index=True)

    # Is this person automatically following the suggested twitter organization?
    auto_followed_from_twitter_suggestion = models.BooleanField(verbose_name='', default=False)

    # Is the fact that this organization is being followed by voter visible to the public?
    is_follow_visible_publicly = models.BooleanField(verbose_name='', default=False)

    # The date the voter followed or stopped following this organization
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # This is used when we want to export the organizations that a voter is following
    def voter_we_vote_id(self):
        voter_manager = VoterManager()
        return voter_manager.fetch_we_vote_id_from_local_id(self.voter_id)

    def __unicode__(self):
        return self.organization_id

    def is_following(self):
        if self.following_status == FOLLOWING:
            return True
        return False

    def is_not_following(self):
        if self.following_status == STOP_FOLLOWING:
            return True
        return False

    def is_ignoring(self):
        if self.following_status == FOLLOW_IGNORE:
            return True
        return False


class FollowOrganizationManager(models.Model):

    def __unicode__(self):
        return "FollowOrganizationManager"

    def fetch_number_of_organizations_followed(self, voter_id):
        number_of_organizations_followed = 0

        try:
            if positive_value_exists(voter_id):
                follow_organization_query = FollowOrganization.objects.filter(
                    voter_id=voter_id,
                    following_status=FOLLOWING
                )
                number_of_organizations_followed = follow_organization_query.count()
        except Exception as e:
            pass

        return number_of_organizations_followed

    def toggle_on_voter_following_organization(self, voter_id, organization_id, organization_we_vote_id,
                                               voter_linked_organization_we_vote_id,
                                               auto_followed_from_twitter_suggestion=False):
        following_status = FOLLOWING
        follow_organization_manager = FollowOrganizationManager()
        return follow_organization_manager.toggle_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id, following_status,
            auto_followed_from_twitter_suggestion)

    def toggle_off_voter_following_organization(self, voter_id, organization_id, organization_we_vote_id,
                                                voter_linked_organization_we_vote_id):
        following_status = STOP_FOLLOWING
        follow_organization_manager = FollowOrganizationManager()
        return follow_organization_manager.toggle_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id, following_status)

    def toggle_ignore_voter_following_organization(self, voter_id, organization_id, organization_we_vote_id,
                                                   voter_linked_organization_we_vote_id):
        following_status = FOLLOW_IGNORE
        follow_organization_manager = FollowOrganizationManager()
        return follow_organization_manager.toggle_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id, following_status)

    def toggle_voter_following_organization(self, voter_id, organization_id, organization_we_vote_id,
                                            voter_linked_organization_we_vote_id, following_status,
                                            auto_followed_from_twitter_suggestion=False):
        status = ""
        # Does a follow_organization entry exist from this voter already exist?
        follow_organization_manager = FollowOrganizationManager()
        results = follow_organization_manager.retrieve_follow_organization(0, voter_id,
                                                                           organization_id, organization_we_vote_id)

        follow_organization_on_stage_found = False
        follow_organization_on_stage_id = 0
        follow_organization_on_stage = FollowOrganization()
        if results['follow_organization_found']:
            follow_organization_on_stage = results['follow_organization']

            # Update this follow_organization entry with new values - we do not delete because we might be able to use
            try:
                if auto_followed_from_twitter_suggestion:
                    # If here we are auto-following because the voter follows this organization on Twitter
                    if follow_organization_on_stage.following_status == "STOP_FOLLOWING" or \
                                    follow_organization_on_stage.following_status == "FOLLOW_IGNORE":
                        # Do not follow again
                        pass
                    else:
                        follow_organization_on_stage.following_status = following_status
                else:
                    follow_organization_on_stage.following_status = following_status
                    follow_organization_on_stage.auto_followed_from_twitter_suggestion = False
                follow_organization_on_stage.voter_linked_organization_we_vote_id = voter_linked_organization_we_vote_id
                # We don't need to update here because set set auto_now=True in the field
                # follow_organization_on_stage.date_last_changed =
                follow_organization_on_stage.save()
                follow_organization_on_stage_id = follow_organization_on_stage.id
                follow_organization_on_stage_found = True
                status += 'UPDATE ' + following_status
            except Exception as e:
                status += 'FAILED_TO_UPDATE ' + following_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        elif results['MultipleObjectsReturned']:
            logger.warning("follow_organization: delete all but one and take it over?")
            status += 'TOGGLE_FOLLOWING_ORGANIZATION MultipleObjectsReturned ' + following_status
        elif results['DoesNotExist']:
            try:
                # Create new follow_organization entry
                # First make sure that organization_id is for a valid organization
                organization_manager = OrganizationManager()
                if positive_value_exists(organization_id):
                    results = organization_manager.retrieve_organization(organization_id)
                else:
                    results = organization_manager.retrieve_organization(0, organization_we_vote_id)
                if results['organization_found']:
                    organization = results['organization']
                    follow_organization_on_stage = FollowOrganization(
                        voter_id=voter_id,
                        organization_id=organization.id,
                        organization_we_vote_id=organization.we_vote_id,
                        voter_linked_organization_we_vote_id=voter_linked_organization_we_vote_id,
                        following_status=following_status,
                    )
                    if auto_followed_from_twitter_suggestion:
                        follow_organization_on_stage.auto_followed_from_twitter_suggestion = True
                    follow_organization_on_stage.save()
                    follow_organization_on_stage_id = follow_organization_on_stage.id
                    follow_organization_on_stage_found = True
                    status += 'CREATE ' + following_status
                else:
                    status += 'ORGANIZATION_NOT_FOUND_ON_CREATE ' + following_status
            except Exception as e:
                status += 'FAILED_TO_UPDATE ' + following_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status += results['status']

        results = {
            'success':                              True if follow_organization_on_stage_found else False,
            'status':                               status,
            'follow_organization_found':            follow_organization_on_stage_found,
            'follow_organization_id':               follow_organization_on_stage_id,
            'follow_organization':                  follow_organization_on_stage,
            'voter_linked_organization_we_vote_id': voter_linked_organization_we_vote_id,
        }
        return results

    def retrieve_follow_organization(self, follow_organization_id, voter_id, organization_id, organization_we_vote_id,
                                     read_only=False):
        """
        follow_organization_id is the identifier for records stored in this table (it is NOT the organization_id)
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        follow_organization_on_stage = FollowOrganization()
        follow_organization_on_stage_id = 0

        try:
            if positive_value_exists(follow_organization_id):
                if read_only:
                    follow_organization_on_stage = FollowOrganization.objects.using('readonly').get(
                        id=follow_organization_id)
                else:
                    follow_organization_on_stage = FollowOrganization.objects.get(id=follow_organization_id)
                follow_organization_on_stage_id = organization_id.id
                success = True
                status = 'FOLLOW_ORGANIZATION_FOUND_WITH_ID'
            elif positive_value_exists(voter_id) and positive_value_exists(organization_id):
                if read_only:
                    follow_organization_on_stage = FollowOrganization.objects.using('readonly').get(
                        voter_id=voter_id, organization_id=organization_id)
                else:
                    follow_organization_on_stage = FollowOrganization.objects.get(
                        voter_id=voter_id, organization_id=organization_id)
                follow_organization_on_stage_id = follow_organization_on_stage.id
                success = True
                status = 'FOLLOW_ORGANIZATION_FOUND_WITH_VOTER_ID_AND_ORGANIZATION_ID'
            elif positive_value_exists(voter_id) and positive_value_exists(organization_we_vote_id):
                if read_only:
                    follow_organization_on_stage = FollowOrganization.objects.using('readonly').get(
                        voter_id=voter_id, organization_we_vote_id=organization_we_vote_id)
                else:
                    follow_organization_on_stage = FollowOrganization.objects.get(
                        voter_id=voter_id, organization_we_vote_id=organization_we_vote_id)
                follow_organization_on_stage_id = follow_organization_on_stage.id
                success = True
                status = 'FOLLOW_ORGANIZATION_FOUND_WITH_VOTER_ID_AND_ORGANIZATION_WE_VOTE_ID'
            else:
                success = False
                status = 'FOLLOW_ORGANIZATION_MISSING_REQUIRED_VARIABLES'
        except FollowOrganization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = 'FOLLOW_ORGANIZATION_NOT_FOUND_MultipleObjectsReturned'
        except FollowOrganization.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = 'FOLLOW_ORGANIZATION_NOT_FOUND_DoesNotExist'

        if positive_value_exists(follow_organization_on_stage_id):
            follow_organization_on_stage_found = True
            is_following = follow_organization_on_stage.is_following()
            is_not_following = follow_organization_on_stage.is_not_following()
            is_ignoring = follow_organization_on_stage.is_ignoring()
        else:
            follow_organization_on_stage_found = False
            is_following = False
            is_not_following = True
            is_ignoring = False
        results = {
            'status':                       status,
            'success':                      success,
            'follow_organization_found':    follow_organization_on_stage_found,
            'follow_organization_id':       follow_organization_on_stage_id,
            'follow_organization':          follow_organization_on_stage,
            'is_following':                 is_following,
            'is_not_following':             is_not_following,
            'is_ignoring':                  is_ignoring,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_voter_following_org_status(self, voter_id, voter_we_vote_id,
                                            organization_id, organization_we_vote_id, read_only=False):
        """
        Retrieve one follow entry so we can see if a voter is following or ignoring a particular org
        """

        if not positive_value_exists(voter_id) and positive_value_exists(voter_we_vote_id):
            # We need voter_id to call retrieve_follow_organization
            voter_manager = VoterManager()
            voter_id = voter_manager.fetch_local_id_from_we_vote_id(voter_we_vote_id)

        if not positive_value_exists(voter_id) and \
                not (positive_value_exists(organization_id) or positive_value_exists(organization_we_vote_id)):
            results = {
                'status':                       'RETRIEVE_VOTER_FOLLOWING_MISSING_VARIABLES',
                'success':                      False,
                'follow_organization_found':    False,
                'follow_organization_id':       0,
                'follow_organization':          FollowOrganization(),
                'is_following':                 False,
                'is_not_following':             True,
                'is_ignoring':                  False,
                'error_result':                 True,
                'DoesNotExist':                 False,
                'MultipleObjectsReturned':      False,
            }
            return results

        return self.retrieve_follow_organization(
            0, voter_id, organization_id, organization_we_vote_id, read_only=read_only)

    def create_or_update_suggested_organization_to_follow(self, viewer_voter_we_vote_id, organization_we_vote_id,
                                                          from_twitter=False):
        """
        Create or update the SuggestedOrganizationToFollow table with suggested organizations from twitter ids i follow
        or organization of my friends follow.
        :param viewer_voter_we_vote_id:
        :param organization_we_vote_id:
        :param from_twitter:
        :return:
        """
        try:
            suggested_organization_to_follow, created = SuggestedOrganizationToFollow.objects.update_or_create(
                viewer_voter_we_vote_id=viewer_voter_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                defaults={
                    'viewer_voter_we_vote_id':  viewer_voter_we_vote_id,
                    'organization_we_vote_id':  organization_we_vote_id,
                    'from_twitter':             from_twitter
                }
            )
            suggested_organization_to_follow_saved = True
            success = True
            status = "SUGGESTED_ORGANIZATION_TO_FOLLOW_UPDATED"
        except Exception:
            suggested_organization_to_follow_saved = False
            suggested_organization_to_follow = SuggestedOrganizationToFollow()
            success = False
            status = "SUGGESTED_ORGANIZATION_TO_FOLLOW_NOT_UPDATED"
        results = {
            'success':                                  success,
            'status':                                   status,
            'suggested_organization_to_follow_saved':   suggested_organization_to_follow_saved,
            'suggested_organization_to_follow':         suggested_organization_to_follow,
        }
        return results

    def retrieve_suggested_organization_to_follow_list(self, viewer_voter_we_vote_id, from_twitter=False):
        """
        Retrieving suggested organizations who i follow from SuggestedOrganizationToFollow table.
        :param viewer_voter_we_vote_id:
        :param from_twitter:
        :return:
        """
        suggested_organization_to_follow_list = []
        try:
            suggested_organization_to_follow_queryset = SuggestedOrganizationToFollow.objects.all()
            suggested_organization_to_follow_list = suggested_organization_to_follow_queryset.filter(
                viewer_voter_we_vote_id__iexact=viewer_voter_we_vote_id,
                from_twitter=from_twitter)
            if len(suggested_organization_to_follow_list):
                success = True
                suggested_organization_to_follow_list_found = True
                status = "SUGGESTED_ORGANIZATION_TO_FOLLOW_RETRIEVED"
            else:
                success = True
                suggested_organization_to_follow_list_found = False
                status = "NO_SUGGESTED_ORGANIZATION_TO_FOLLOW_LIST_RETRIEVED"
        except SuggestedOrganizationToFollow.DoesNotExist:
            # No data found. Try again below
            success = True
            suggested_organization_to_follow_list_found = False
            status = 'NO_SUGGESTED_ORGANIZATION_TO_FOLLOW_LIST_RETRIEVED_DoesNotExist'
        except Exception as e:
            success = False
            suggested_organization_to_follow_list_found = False
            status = "SUGGESTED_ORGANIZATION_TO_FOLLOW_LIST_NOT_RETRIEVED"

        results = {
            'success':                                      success,
            'status':                                       status,
            'suggested_organization_to_follow_list_found':  suggested_organization_to_follow_list_found,
            'suggested_organization_to_follow_list':        suggested_organization_to_follow_list,
        }
        return results


class FollowOrganizationList(models.Model):
    """
    A way to retrieve all of the follow_organization information
    """

    def fetch_follow_organization_by_voter_id_count(self, voter_id):
        follow_organization_list = self.retrieve_follow_organization_by_voter_id(voter_id)
        return len(follow_organization_list)

    def retrieve_follow_organization_by_voter_id(self, voter_id, auto_followed_from_twitter_suggestion=False,
                                                 read_only=False):
        # Retrieve a list of follow_organization entries for this voter
        follow_organization_list_found = False
        following_status = FOLLOWING
        follow_organization_list = {}
        try:
            # Should not default to 'readonly' since we sometimes save the results of this call
            if read_only:
                follow_organization_list = FollowOrganization.objects.using('readonly').all()
            else:
                follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(voter_id=voter_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if auto_followed_from_twitter_suggestion:
                follow_organization_list = follow_organization_list.filter(
                    auto_followed_from_twitter_suggestion=auto_followed_from_twitter_suggestion)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = {}
            return follow_organization_list

    def retrieve_follow_organization_by_own_organization_we_vote_id(self, organization_we_vote_id,
                                                                    auto_followed_from_twitter_suggestion=False):
        # Retrieve a list of followed organizations entries by voter_linked_organization_we_vote_id for voter guides
        follow_organization_list_found = False
        following_status = FOLLOWING
        follow_organization_list = []
        try:
            follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(
                voter_linked_organization_we_vote_id=organization_we_vote_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if auto_followed_from_twitter_suggestion:
                follow_organization_list = follow_organization_list.filter(
                    auto_followed_from_twitter_suggestion=auto_followed_from_twitter_suggestion)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = []
            return follow_organization_list

    def retrieve_ignore_organization_by_voter_id(self, voter_id, read_only=False):
        # Retrieve a list of follow_organization entries for this voter
        follow_organization_list_found = False
        following_status = FOLLOW_IGNORE
        follow_organization_list = {}
        try:
            if positive_value_exists(read_only):
                follow_organization_list = FollowOrganization.objects.using('readonly').all()
            else:
                follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(voter_id=voter_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = {}
            return follow_organization_list

    def retrieve_follow_organization_by_voter_id_simple_id_array(self, voter_id, return_we_vote_id=False,
                                                                 auto_followed_from_twitter_suggestion=False,
                                                                 read_only=False):
        follow_organization_list_manager = FollowOrganizationList()
        follow_organization_list = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id(
                voter_id, auto_followed_from_twitter_suggestion, read_only)
        follow_organization_list_simple_array = []
        if len(follow_organization_list):
            voter_manager = VoterManager()
            voter_linked_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_from_local_id(voter_id)
            for follow_organization in follow_organization_list:
                if not read_only:
                    # Heal the data by making sure the voter's linked_organization_we_vote_id exists and is accurate
                    if positive_value_exists(voter_linked_organization_we_vote_id) \
                        and voter_linked_organization_we_vote_id != \
                            follow_organization.voter_linked_organization_we_vote_id:
                        try:
                            follow_organization.voter_linked_organization_we_vote_id = \
                                voter_linked_organization_we_vote_id
                            follow_organization.save()
                        except Exception as e:
                            status = 'FAILED_TO_UPDATE_FOLLOW_ISSUE-voter_id ' + str(voter_id)
                            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

                if return_we_vote_id:
                    follow_organization_list_simple_array.append(follow_organization.organization_we_vote_id)
                else:
                    follow_organization_list_simple_array.append(follow_organization.organization_id)
        return follow_organization_list_simple_array

    def retrieve_followed_organization_by_organization_we_vote_id_simple_id_array(
            self, organization_we_vote_id, return_we_vote_id=False,
            auto_followed_from_twitter_suggestion=False):
        follow_organization_list_manager = FollowOrganizationList()
        follow_organization_list = \
            follow_organization_list_manager.retrieve_follow_organization_by_own_organization_we_vote_id(
                organization_we_vote_id, auto_followed_from_twitter_suggestion)
        follow_organization_list_simple_array = []
        if len(follow_organization_list):
            for follow_organization in follow_organization_list:
                if return_we_vote_id:
                    follow_organization_list_simple_array.append(follow_organization.organization_we_vote_id)
                else:
                    follow_organization_list_simple_array.append(follow_organization.organization_id)
        return follow_organization_list_simple_array

    def fetch_followers_list_by_organization_we_vote_id(
            self, organization_we_vote_id, return_voter_we_vote_id=False):
        """
        Fetch a list of the voter_id or voter_we_vote_id of followers of organization_we_vote_id.
        :param organization_we_vote_id:
        :param return_voter_we_vote_id:
        :return:
        """
        follow_organization_list_manager = FollowOrganizationList()
        followers_list = \
            follow_organization_list_manager.retrieve_follow_organization_by_organization_we_vote_id(
                organization_we_vote_id)
        followers_list_simple_array = []
        if len(followers_list):
            voter_manager = VoterManager()
            for follow_organization in followers_list:
                if return_voter_we_vote_id:
                    voter_we_vote_id = voter_manager.fetch_we_vote_id_from_local_id(follow_organization.voter_id)
                    if positive_value_exists(voter_we_vote_id):
                        followers_list_simple_array.append(voter_we_vote_id)
                else:
                    if positive_value_exists(follow_organization.voter_id):
                        followers_list_simple_array.append(follow_organization.voter_id)
        return followers_list_simple_array

    def retrieve_followers_organization_by_organization_we_vote_id_simple_id_array(
            self, organization_we_vote_id, return_we_vote_id=False,
            auto_followed_from_twitter_suggestion=False):
        """
        Retrieve the organization_id (or organization_we_vote_id) for each voter that follows organization_we_vote_id.
        :param organization_we_vote_id:
        :param return_we_vote_id:
        :param auto_followed_from_twitter_suggestion:
        :return:
        """
        follow_organization_list_manager = FollowOrganizationList()
        followers_organization_list = \
            follow_organization_list_manager.retrieve_follow_organization_by_organization_we_vote_id(
                organization_we_vote_id)
        followers_organization_list_simple_array = []
        if len(followers_organization_list):
            for follow_organization in followers_organization_list:
                if return_we_vote_id:
                    if positive_value_exists(follow_organization.voter_linked_organization_we_vote_id):
                        followers_organization_list_simple_array.append(
                            follow_organization.voter_linked_organization_we_vote_id)
                else:
                    followers_organization_list_simple_array.append(follow_organization.organization_id)
        return followers_organization_list_simple_array

    def retrieve_ignore_organization_by_voter_id_simple_id_array(
            self, voter_id, return_we_vote_id=False, read_only=False):
        follow_organization_list_manager = FollowOrganizationList()
        ignore_organization_list = \
            follow_organization_list_manager.retrieve_ignore_organization_by_voter_id(voter_id, read_only)
        ignore_organization_list_simple_array = []
        if len(ignore_organization_list):
            for ignore_organization in ignore_organization_list:
                if return_we_vote_id:
                    ignore_organization_list_simple_array.append(ignore_organization.organization_we_vote_id)
                else:
                    ignore_organization_list_simple_array.append(ignore_organization.organization_id)
        return ignore_organization_list_simple_array

    def retrieve_follow_organization_by_organization_id(self, organization_id):
        # Retrieve a list of follow_organization entries for this organization
        follow_organization_list_found = False
        following_status = FOLLOWING
        follow_organization_list = {}
        try:
            follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(organization_id=organization_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            pass

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = {}
            return follow_organization_list

    def retrieve_follow_organization_by_organization_we_vote_id(self, organization_we_vote_id):
        # Retrieve a list of follow_organization entries for this organization
        follow_organization_list_found = False
        following_status = FOLLOWING
        follow_organization_list = {}
        try:
            follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(organization_we_vote_id=organization_we_vote_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            pass

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = {}
            return follow_organization_list


class SuggestedIssueToFollow(models.Model):
    """
    This table stores possible suggested issues to follow
    """
    viewer_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id", max_length=255, null=True, blank=True, unique=False)
    issue_we_vote_id = models.CharField(
        verbose_name="issue we vote id", max_length=255, null=True, blank=True, unique=False)
    # organization_we_vote_id_making_suggestion = models.CharField(
    #    verbose_name="organization we vote id making decision", max_length=255, null=True, blank=True, unique=False)
    # from_twitter = models.BooleanField(verbose_name="from twitter", default=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # def fetch_other_organization_we_vote_id(self, one_we_vote_id):
    #     if one_we_vote_id == self.viewer_voter_we_vote_id:
    #         return self.viewee_voter_we_vote_id
    #     else:
    #         # If the we_vote_id passed in wasn't found, don't return another we_vote_id
    #         return ""


class SuggestedOrganizationToFollow(models.Model):
    """
    This table stores possible suggested organization from twitter ids i follow or organization of my friends follow.
    """
    viewer_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False)
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id person 2", max_length=255, null=True, blank=True, unique=False)
    # organization_we_vote_id_making_suggestion = models.CharField(
    #    verbose_name="organization we vote id making decision", max_length=255, null=True, blank=True, unique=False)
    from_twitter = models.BooleanField(verbose_name="from twitter", default=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def fetch_other_organization_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.viewer_voter_we_vote_id:
            return self.viewee_voter_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""
