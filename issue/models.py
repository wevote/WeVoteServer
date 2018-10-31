# issue/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_exception, handle_record_found_more_than_one_exception, \
    handle_record_not_found_exception, handle_record_not_saved_exception
from wevote_settings.models import fetch_next_we_vote_id_issue_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

# sort_formula
MOST_LINKED_ORGANIZATIONS = "MOST_LINKED_ORGANIZATIONS"
ALPHABETICAL_ASCENDING = "ALPHABETICAL_ASCENDING"

LINKED = 'LINKED'
UNLINKED = 'UNLINKED'
LINK_CHOICES = (
    (LINKED,     'Linked'),
    (UNLINKED,   'Unlinked'),
)

# Reason for linking issue
NO_REASON = 'NO_REASON'
LINKED_BY_ORGANIZATION = 'LINKED_BY_ORGANIZATION'
LINKED_BY_WE_VOTE = 'LINKED_BY_WE_VOTE'
AUTO_LINKED_BY_HASHTAG = 'AUTO_LINKED_BY_HASHTAG'
AUTO_LINKED_BY_TEXT = 'AUTO_LINKED_BY_TEXT'
LINKING_REASON_CHOICES = (
    (NO_REASON,                 'No reason'),
    (LINKED_BY_ORGANIZATION,    'Linked by organization'),
    (LINKED_BY_WE_VOTE,         'Linked by We Vote'),
    (AUTO_LINKED_BY_HASHTAG,    'Auto-linked by hashtag'),
    (AUTO_LINKED_BY_TEXT,       'Auto-linked by text'),
)

# Reason linking option is blocked
# NO_REASON = 'NO_REASON'  # Defined above
BLOCKED_BY_ORGANIZATION = 'BLOCKED_BY_ORGANIZATION'
BLOCKED_BY_WE_VOTE = 'BLOCKED_BY_WE_VOTE'
FLAGGED_BY_VOTERS = 'FLAGGED_BY_VOTERS'
LINKING_BLOCKED_REASON_CHOICES = (
    (NO_REASON,                 'No reason'),
    (BLOCKED_BY_ORGANIZATION,   'Blocked by organization'),
    (BLOCKED_BY_WE_VOTE,        'Blocked by We Vote'),
    (FLAGGED_BY_VOTERS,         'Flagged by voters'),
)

# Kinds of lists of suggested organization
# UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW = 'UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW'

logger = wevote_functions.admin.get_logger(__name__)


class TrackedWordOrPhrase():
    # word_or_phrase
    # ignored
    pass


class HashtagLinkedToIssue():
    """ If this hashtag is found in an organization’s Twitter Feed a certain number of times, link an organization to
    this issue automatically """
    # hashtag_text
    # issue_we_vote_id
    pass


class IssueListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Issues
    """

    def fetch_visible_issue_we_vote_ids(self):
        issue_we_vote_ids_list = []
        results = self.retrieve_issues()
        if results['issue_list_found']:
            issue_list = results['issue_list']
            for issue in issue_list:
                issue_we_vote_ids_list.append(issue.we_vote_id)

        return issue_we_vote_ids_list

    def retrieve_issues(self, sort_formula=None, issue_we_vote_id_list_to_filter=None,
                        issue_we_vote_id_list_to_exclude=None, require_filter_or_exclude=False,
                        show_hidden_issues=False):
        issue_list = []
        issue_list_found = False
        success = False

        if require_filter_or_exclude and issue_we_vote_id_list_to_filter is None and \
                issue_we_vote_id_list_to_exclude is None:
            status = 'RETRIEVE_ISSUE_FILTERS_NOT_FOUND'
            results = {
                'success':          success,
                'status':           status,
                'issue_list_found': issue_list_found,
                'issue_list':       issue_list,
            }
            return results

        try:
            issue_queryset = Issue.objects.using('readonly').all()
            # By default, we only show the issues marked "hide_issue=False"
            if not show_hidden_issues:
                issue_queryset = issue_queryset.filter(hide_issue=False)
            if issue_we_vote_id_list_to_filter is not None:
                issue_queryset = issue_queryset.filter(we_vote_id__in=issue_we_vote_id_list_to_filter)
            if issue_we_vote_id_list_to_exclude is not None:
                issue_queryset = issue_queryset.exclude(we_vote_id__in=issue_we_vote_id_list_to_exclude)
            if sort_formula == MOST_LINKED_ORGANIZATIONS:
                issue_queryset = issue_queryset.order_by(
                    '-linked_organization_count', 'we_vote_hosted_image_url_tiny', 'issue_name')
            elif sort_formula == ALPHABETICAL_ASCENDING:
                issue_queryset = issue_queryset.order_by('issue_name')
            else:
                issue_queryset = issue_queryset.order_by('issue_name')

            issue_list = list(issue_queryset)

            if len(issue_list):
                issue_list_found = True
                status = 'ISSUES_RETRIEVED'
            else:
                status = 'NO_ISSUES_RETRIEVED'
            success = True
        except Issue.DoesNotExist:
            # No issues found. Not a problem.
            status = 'NO_ISSUES_FOUND'
            issue_list = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_issues_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':              success,
            'status':               status,
            'issue_list_found':     issue_list_found,
            'issue_list':           issue_list,
        }
        return results

    def retrieve_issue_count(self):
        try:
            issue_queryset = Issue.objects.using('readonly').all()
            # We only show the issues marked "hide_issue=False"
            issue_queryset = issue_queryset.filter(hide_issue=False)
            issue_count = issue_queryset.count()
            success = True
            status = "ISSUE_COUNT_FOUND"
        except Issue.DoesNotExist:
            # No issues found. Not a problem.
            status = 'NO_ISSUES_FOUND_DoesNotExist'
            issue_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_issues_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False
            issue_count = 0

        results = {
            'success':      success,
            'status':       status,
            'issue_count':  issue_count,
        }
        return results

    def fetch_organization_issues_for_display(self, organization_we_vote_id, sort_formula=None,
                                              show_hidden_issues=False):
        results = self.retrieve_organization_issues_for_display(organization_we_vote_id, sort_formula,
                                                                show_hidden_issues)
        return results['issues_display_string']

    def retrieve_organization_issues_for_display(self, organization_we_vote_id, sort_formula=None,
                                                 show_hidden_issues=False):
        issue_list_found = False
        success = False
        status = ""
        issues_display_string = ""

        if not positive_value_exists(organization_we_vote_id):
            status += 'RETRIEVE_ISSUES_ORGANIZATION_NOT_FOUND '
            results = {
                'success': success,
                'status': status,
                'issue_list_found': issue_list_found,
                'issues_display_string': issues_display_string,
            }
            return results

        organization_link_to_issue_list = OrganizationLinkToIssueList()
        issues_list = organization_link_to_issue_list.fetch_issue_we_vote_id_list_by_organization_we_vote_id(
            organization_we_vote_id)

        if len(issues_list) == 0:
            status += 'RETRIEVE_ISSUES_FOR_ORGANIZATION_NO_ISSUES '
            results = {
                'success': success,
                'status': status,
                'issue_list_found': issue_list_found,
                'issues_display_string': issues_display_string,
            }
            return results

        try:
            issue_queryset = Issue.objects.using('readonly').all()
            # By default, we only show the issues marked "hide_issue=False"
            if not show_hidden_issues:
                issue_queryset = issue_queryset.filter(hide_issue=False)
            issue_queryset = issue_queryset.filter(we_vote_id__in=issues_list)
            if sort_formula == MOST_LINKED_ORGANIZATIONS:
                issue_queryset = issue_queryset.order_by(
                    '-linked_organization_count', 'we_vote_hosted_image_url_tiny', 'issue_name')
            elif sort_formula == ALPHABETICAL_ASCENDING:
                issue_queryset = issue_queryset.order_by('issue_name')
            else:
                issue_queryset = issue_queryset.order_by('issue_name')

            issue_list = list(issue_queryset)

            if len(issue_list):
                issue_list_found = True
                status += 'RETRIEVE_ISSUES_FOR_ORGANIZATION_ISSUES_RETRIEVED '
                for one_issue in issue_list:
                    issues_display_string += one_issue.issue_name + ", "
                issues_display_string = issues_display_string[:-2]
            else:
                status += 'RETRIEVE_ISSUES_FOR_ORGANIZATION_NO_ISSUES_RETRIEVED '
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED fetch_organization_issues_for_display ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        results = {
            'success': success,
            'status': status,
            'issue_list_found': issue_list_found,
            'issues_display_string': issues_display_string,
        }
        return results


class Issue(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "issue", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_issue_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this issue", max_length=255, default=None, null=True,
        blank=True, unique=True)
    issue_name = models.CharField(verbose_name="name of the issue",
                                  max_length=255, null=True, blank=True, db_index=True)
    # The description of the issue.
    issue_description = models.TextField(verbose_name="description of the issue",
                                         null=True, blank=True, default="")
    issue_followers_count = models.PositiveIntegerField(verbose_name="number of followers of this issue",
                                                        null=False, blank=True, default=0)
    linked_organization_count = models.PositiveIntegerField(verbose_name="number of organizations linked to the issue",
                                                            null=False, blank=True, default=0)
    hide_issue = models.BooleanField(default=True)  # Do not show issue to voters or partners (admins/volunteers only)

    # For audit reasons, would this issue broadly be considered "left" or "right"
    considered_left = models.BooleanField(default=False)
    considered_right = models.BooleanField(default=False)

    # A default image field for hard-coded local images
    issue_icon_local_path = models.TextField(
        verbose_name='path in web app for the issue icon', blank=True, null=True, default="")
    we_vote_hosted_image_url_large = models.URLField(
        verbose_name='we vote hosted large image url', blank=True, null=True)
    we_vote_hosted_image_url_medium = models.URLField(
        verbose_name='we vote hosted medium image url', blank=True, null=True)
    we_vote_hosted_image_url_tiny = models.URLField(
        verbose_name='we vote hosted tiny image url', blank=True, null=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_issue_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "issue" = tells us this is a unique id for a Issue
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}issue{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(Issue, self).save(*args, **kwargs)


class IssueManager(models.Model):

    def __unicode__(self):
        return "IssueManager"

    def retrieve_issue_from_id(self, issue_id):
        issue_manager = IssueManager()
        return issue_manager.retrieve_issue(issue_id)

    def retrieve_issue_from_we_vote_id(self, we_vote_id):
        issue_id = 0
        issue_manager = IssueManager()
        return issue_manager.retrieve_issue(issue_id, we_vote_id)

    def fetch_issue_id_from_we_vote_id(self, we_vote_id):
        issue_id = 0
        issue_manager = IssueManager()
        results = issue_manager.retrieve_issue(issue_id, we_vote_id)
        if results['success']:
            return results['issue_id']
        return 0

    def fetch_issue_name_from_we_vote_id(self, we_vote_id):
        issue_id = 0
        issue_manager = IssueManager()
        results = issue_manager.retrieve_issue(issue_id, we_vote_id)
        if results['success']:
            return results['issue_name']
        return ''

    def fetch_issue_we_vote_id_from_id(self, issue_id):
        we_vote_id = ''
        issue_manager = IssueManager()
        results = issue_manager.retrieve_issue(issue_id, we_vote_id)
        if results['success']:
            return results['issue_we_vote_id']
        return ''

    def fetch_issue_from_we_vote_id(self, we_vote_id):
        issue_id = 0
        issue_manager = IssueManager()
        results = issue_manager.retrieve_issue(issue_id, we_vote_id)
        if results['issue_found']:
            return results['issue']
        return None

    def retrieve_issue_from_issue_name(self, issue_name):
        issue_id = 0
        we_vote_id = ''
        issue_manager = IssueManager()

        results = issue_manager.retrieve_issue(issue_id, we_vote_id, issue_name)
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_issue(self, issue_id, issue_we_vote_id=None, issue_name=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        issue_on_stage = Issue()

        try:
            if positive_value_exists(issue_id):
                issue_on_stage = Issue.objects.get(id=issue_id)
                issue_id = issue_on_stage.id
                issue_we_vote_id = issue_on_stage.we_vote_id
                issue_name = issue_on_stage.issue_name
                issue_found = True
                status = "RETRIEVE_ISSUE_FOUND_BY_ID"
            elif positive_value_exists(issue_we_vote_id):
                issue_on_stage = Issue.objects.get(we_vote_id=issue_we_vote_id)
                issue_id = issue_on_stage.id
                issue_we_vote_id = issue_on_stage.we_vote_id
                issue_name = issue_on_stage.issue_name
                issue_found = True
                status = "RETRIEVE_ISSUE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(issue_name):
                issue_on_stage = Issue.objects.get(issue_name=issue_name)
                issue_id = issue_on_stage.id
                issue_we_vote_id = issue_on_stage.we_vote_id
                issue_name = issue_on_stage.issue_name
                issue_found = True
                status = "RETRIEVE_ISSUE_FOUND_BY_NAME"
            else:
                issue_found = False
                status = "RETRIEVE_ISSUE_SEARCH_INDEX_MISSING"
        except Issue.MultipleObjectsReturned as e:
            issue_found = False
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_ISSUE_MULTIPLE_OBJECTS_RETURNED"
        except Issue.DoesNotExist:
            issue_found = False
            exception_does_not_exist = True
            status = "RETRIEVE_ISSUE_NOT_FOUND"
        except Exception as e:
            issue_found = False
            status = "RETRIEVE_ISSUE_NOT_FOUND_EXCEPTION"

        results = {
            'success':                  True if convert_to_int(issue_id) > 0 else False,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'issue_found':              issue_found,
            'issue_id':                 convert_to_int(issue_id),
            'issue_name':               issue_name,
            'issue_we_vote_id':         issue_we_vote_id,
            'issue':                    issue_on_stage,
        }
        return results

    def update_or_create_issue(self, issue_we_vote_id, issue_name='', issue_description=''):
        """
        Either update or create a issue entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_issue_created = False
        issue_on_stage = Issue()
        status = ""
        updated_issue_values = {
        }
        if positive_value_exists(issue_we_vote_id):
            updated_issue_values["we_vote_id"] = issue_we_vote_id
        if positive_value_exists(issue_name):
            updated_issue_values["issue_name"] = issue_name
        if positive_value_exists(issue_description):
            updated_issue_values["issue_description"] = issue_description
        # Should we deal with hide_issue?

        if not positive_value_exists(issue_name) and not positive_value_exists(issue_we_vote_id):
            success = False
            status += 'MISSING_ISSUE_NAME_AND_WE_VOTE_ID '
        else:
            # Check before we try to create a new entry
            issue_found = False
            try:
                issue_on_stage = Issue.objects.get(
                    we_vote_id__iexact=issue_we_vote_id,
                )
                issue_found = True
                success = True
                status += 'ISSUE_FOUND_BY_WE_VOTE_ID '
            except Issue.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ISSUES_FOUND_BY_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Issue.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_ISSUE_NOT_FOUND_BY_WE_VOTE_ID "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_ISSUE_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

            if not issue_found:
                try:
                    issue_on_stage = Issue.objects.get(
                        issue_name__iexact=issue_name,
                    )
                    issue_found = True
                    success = True
                    status += 'ISSUE_FOUND_BY_ISSUE_NAME '
                except Issue.MultipleObjectsReturned as e:
                    success = False
                    status += 'MULTIPLE_MATCHING_ISSUES_FOUND_BY_ISSUE_NAME '
                    exception_multiple_object_returned = True
                except Issue.DoesNotExist:
                    exception_does_not_exist = True
                    status += "RETRIEVE_ISSUE_NOT_FOUND_BY_ISSUE_NAME "
                except Exception as e:
                    status += 'FAILED_TO_RETRIEVE_ISSUE_BY_ISSUE_NAME ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

            if issue_found:
                # Update record
                # Note: When we decide to start updating issue_name elsewhere within We Vote, we should stop
                #  updating issue_name via subsequent Google Civic imports
                try:
                    new_issue_created = False
                    issue_updated = False
                    issue_has_changes = False
                    for key, value in updated_issue_values.items():
                        if hasattr(issue_on_stage, key):
                            issue_has_changes = True
                            setattr(issue_on_stage, key, value)
                    if issue_has_changes and positive_value_exists(issue_on_stage.we_vote_id):
                        issue_on_stage.save()
                        issue_updated = True
                    if issue_updated:
                        success = True
                        status += "ISSUE_UPDATED "
                    else:
                        success = False
                        status += "ISSUE_NOT_UPDATED "
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_ISSUE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    new_issue_created = False
                    issue_on_stage = Issue.objects.create(
                        issue_name=issue_name,
                        issue_description=issue_description)
                    if positive_value_exists(issue_on_stage.id):
                        for key, value in updated_issue_values.items():
                            if hasattr(issue_on_stage, key):
                                setattr(issue_on_stage, key, value)
                        issue_on_stage.save()
                        new_issue_created = True
                    if new_issue_created:
                        success = True
                        status += "ISSUE_CREATED "
                    else:
                        success = False
                        status += "ISSUE_NOT_CREATED "
                except Exception as e:
                    status += 'FAILED_TO_CREATE_ISSUE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_issue_created':        new_issue_created,
            'issue':                    issue_on_stage,
        }
        return results

    def reset_issue_image_details(self, issue, issue_icon_local_path=False):
        """
        Reset an issue entry with original image details from we vote image.
        """
        success = False
        status = "ENTERING_RESET_ISSUE_IMAGE_DETAILS"

        if issue:
            if issue_icon_local_path is not False:
                issue.issue_icon_local_path = issue_icon_local_path
            issue.we_vote_hosted_image_url_large = None
            issue.we_vote_hosted_image_url_medium = None
            issue.we_vote_hosted_image_url_tiny = None
            issue.save()
            success = True
            status = "RESET_ISSUE_IMAGE_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'candidate':    issue,
        }
        return results


class OrganizationLinkToIssue(models.Model):
    # This class represent the link between an organization and an issue
    # We are relying on built-in Python id field

    # The organization's we_vote_id linked to the issue
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False, db_index=True)

    # The issue being linked
    issue_id = models.PositiveIntegerField(null=True, blank=True)

    # we_vote_id of the issue
    issue_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False, db_index=True)

    # Are the organization and the issue linked?
    link_active = models.BooleanField(verbose_name='', default=True)

    # AUTO_TAGGED_BY_TEXT, AUTO_TAGGED_BY_HASHTAG, TAGGED_BY_ORGANIZATION, TAGGED_BY_WE_VOTE, NO_REASON
    reason_for_link = models.CharField(max_length=25, choices=LINKING_REASON_CHOICES,
                                       default=NO_REASON)

    # There are some cases where we want to prevent auto-linking of an issue
    link_blocked = models.BooleanField(verbose_name='', default=False)

    # FLAGGED_BY_VOTERS, BLOCKED_BY_WE_VOTE, BLOCKED_BY_ORGANIZATION, NOT_BLOCKED
    reason_link_is_blocked = models.CharField(max_length=25, choices=LINKING_BLOCKED_REASON_CHOICES,
                                              default=NO_REASON)

    # The date the the issue link was modified
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def __unicode__(self):
        return self.issue_we_vote_id

    def is_linked(self):
        if self.link_active:
            return True
        return False

    def is_not_linked(self):
        return not self.is_linked()


class OrganizationLinkToIssueList(models.Model):
    # A way to retrieve all of the organization and issue linking information

    def retrieve_issue_list_by_organization_we_vote_id(self, organization_we_vote_id, show_hidden_issues=False,
                                                       read_only=False):
        # Retrieve a list of active issues linked to organization
        link_issue_list_found = False
        link_active = True
        link_issue_list = {}

        try:
            if read_only:
                link_issue_query = OrganizationLinkToIssue.objects.using('readonly').all()
            else:
                link_issue_query = OrganizationLinkToIssue.objects.all()
            link_issue_query = link_issue_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            link_issue_query = link_issue_query.filter(link_active=link_active)
            link_issue_list = list(link_issue_query)
            if len(link_issue_list):
                link_issue_list_found = True
        except Exception as e:
            pass

        if link_issue_list_found:
            if show_hidden_issues:
                return link_issue_list
            else:
                link_issue_list_filtered = []
                # Get a complete list of visible issues
                issue_list_manager = IssueListManager()
                visible_issue_we_vote_ids = issue_list_manager.fetch_visible_issue_we_vote_ids()
                for link_issue in link_issue_list:
                    if link_issue.issue_we_vote_id in visible_issue_we_vote_ids:
                        link_issue_list_filtered.append(link_issue)
                return link_issue_list_filtered
        else:
            link_issue_list = {}
            return link_issue_list

    def retrieve_issue_blocked_list_by_organization_we_vote_id(self, organization_we_vote_id, read_only=False):
        # Retrieve a list of issues bocked for an organization
        link_issue_list_found = False
        link_blocked = True
        link_issue_list = {}
        try:
            if read_only:
                link_issue_query = OrganizationLinkToIssue.objects.using('readonly').all()
            else:
                link_issue_query = OrganizationLinkToIssue.objects.all()
            link_issue_query = link_issue_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            link_issue_query = link_issue_query.filter(link_blocked=link_blocked)
            link_issue_list = list(link_issue_query)
            if len(link_issue_list):
                link_issue_list_found = True
        except Exception as e:
            pass

        if link_issue_list_found:
            return link_issue_list
        else:
            link_issue_list = {}
            return link_issue_list

    def fetch_issue_we_vote_id_list_by_organization_we_vote_id(self, organization_we_vote_id):
        link_issue_we_vote_id_list = []
        link_issue_list = self.retrieve_issue_list_by_organization_we_vote_id(organization_we_vote_id, read_only=True)
        for issue in link_issue_list:
            link_issue_we_vote_id_list.append(issue.issue_we_vote_id)
        return link_issue_we_vote_id_list

    def fetch_organization_we_vote_id_list_by_issue_we_vote_id_list(self, issue_we_vote_id_list):
        organization_we_vote_id_list = []
        results = self.retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(
            issue_we_vote_id_list)  # Already read_only
        if results['organization_we_vote_id_list_found']:
            organization_we_vote_id_list = results['organization_we_vote_id_list']
        return organization_we_vote_id_list

    def fetch_issue_count_for_organization(self, organization_id=0, organization_we_vote_id=''):
        link_active = True
        link_issue_list_count = 0
        try:
            link_issue_list = OrganizationLinkToIssue.objects.using('readonly').all()
            link_issue_list = link_issue_list.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            link_issue_list = link_issue_list.filter(link_active=link_active)
            link_issue_list_count = link_issue_list.count()

        except Exception as e:
            pass

        return link_issue_list_count

    def fetch_organization_count_for_issue(self, issue_we_vote_id=''):
        link_active = True
        link_issue_list_count = 0
        try:
            link_issue_list = OrganizationLinkToIssue.objects.using('readonly').all()
            link_issue_list = link_issue_list.filter(issue_we_vote_id__iexact=issue_we_vote_id)
            link_issue_list = link_issue_list.filter(link_active=link_active)
            link_issue_list_count = link_issue_list.count()

        except Exception as e:
            pass

        return link_issue_list_count

    def fetch_linked_organization_count(self, issue_we_vote_id):
        number_of_organizations_following_this_issue = 0

        try:
            if positive_value_exists(issue_we_vote_id):
                organization_link_to_issue_query = OrganizationLinkToIssue.objects.using('readonly').filter(
                    issue_we_vote_id__iexact=issue_we_vote_id,
                    link_active=True
                )
                number_of_organizations_following_this_issue = organization_link_to_issue_query.count()
        except Exception as e:
            pass

        return number_of_organizations_following_this_issue

    def retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(self, issue_we_vote_id_list):
        organization_we_vote_id_list = []
        organization_we_vote_id_list_found = False
        link_active = True
        try:
            link_queryset = OrganizationLinkToIssue.objects.using('readonly').all()
            # we decided not to use case-insensitivity in favour of '__in'
            link_queryset = link_queryset.filter(issue_we_vote_id__in=issue_we_vote_id_list)
            link_queryset = link_queryset.filter(link_active=link_active)
            link_queryset = link_queryset.values('organization_we_vote_id').distinct()
            organization_link_to_issue_results = list(link_queryset)
            if len(organization_link_to_issue_results):
                organization_we_vote_id_list_found = True
                for one_link in organization_link_to_issue_results:
                    organization_we_vote_id_list.append(one_link['organization_we_vote_id'])
                status = 'ORGANIZATION_WE_VOTE_ID_LIST_RETRIEVED '
            else:
                status = 'NO_ORGANIZATION_WE_VOTE_IDS_RETRIEVED '
        except Issue.DoesNotExist:
            # No issues found. Not a problem.
            status = 'NO_ORGANIZATION_WE_VOTE_IDS_DO_NOT_EXIST '
            organization_we_vote_id_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list' \
                     '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success': True if organization_we_vote_id_list else False,
            'status': status,
            'organization_we_vote_id_list_found': organization_we_vote_id_list_found,
            'organization_we_vote_id_list': organization_we_vote_id_list,
        }
        return results


class OrganizationLinkToIssueManager(models.Model):

    def __unicode__(self):
        return "OrganizationLinkToIssueManager"

    def link_organization_to_issue(self, organization_we_vote_id, issue_id, issue_we_vote_id,
                                   reason_for_link=NO_REASON):
        link_active = True
        link_blocked = False
        if reason_for_link is None:
            reason_for_link = LINKED_BY_WE_VOTE
        reason_for_block = NO_REASON
        return self.toggle_issue_link(organization_we_vote_id, issue_id, issue_we_vote_id, link_active, link_blocked,
                                      reason_for_link, reason_for_block)

    def unlink_organization_to_issue(self, organization_we_vote_id, issue_id, issue_we_vote_id,
                                     reason_for_unlink=NO_REASON):
        link_active = False
        link_blocked = False
        reason_for_link = NO_REASON
        reason_for_block = NO_REASON
        return self.toggle_issue_link(organization_we_vote_id, issue_id, issue_we_vote_id, link_active, link_blocked,
                                      reason_for_link, reason_for_block)

    def toggle_issue_link(self, organization_we_vote_id, issue_id, issue_we_vote_id, link_active, link_blocked,
                          reason_for_link=NO_REASON, reason_for_block=NO_REASON):

        link_issue_on_stage_found = False
        link_issue_on_stage_we_vote_id = 0
        link_issue_on_stage = OrganizationLinkToIssue()
        status = ''
        issue_identifier_exists = positive_value_exists(issue_we_vote_id) or positive_value_exists(issue_id)
        if not positive_value_exists(organization_we_vote_id) and not issue_identifier_exists:
            results = {
                'success': True if link_issue_on_stage_found else False,
                'status': 'Insufficient inputs to toggle issue link, try passing ids for organization and issue ',
                'link_issue_found': link_issue_on_stage_found,
                'issue_we_vote_id': link_issue_on_stage_we_vote_id,
                'link_issue': link_issue_on_stage,
            }
            return results

        # First make sure that issue_id is for a valid issue
        issue_manager = IssueManager()
        if positive_value_exists(issue_id):
            results = issue_manager.retrieve_issue(issue_id)
        else:
            results = issue_manager.retrieve_issue(0, issue_we_vote_id)
        if results['issue_found']:
            issue = results['issue']
            issue_found = True
            issue_we_vote_id = issue.we_vote_id
            issue_id = issue.id
        else:
            issue_found = False

        # Does a link_issue entry exist from this organization already?
        link_issue_id = 0
        results = self.retrieve_issue_link(link_issue_id, organization_we_vote_id, issue_id, issue_we_vote_id)

        if results['link_issue_found']:
            link_issue_on_stage = results['link_issue']

            # Update this follow_issue entry with new values - we do not delete because we might be able to use
            try:
                link_issue_on_stage.link_active = link_active
                link_issue_on_stage.link_blocked = link_blocked
                if link_active:
                    link_issue_on_stage.reason_for_link = reason_for_link
                    link_issue_on_stage.reason_link_is_blocked = NO_REASON
                else:
                    link_issue_on_stage.reason_for_link = NO_REASON
                    link_issue_on_stage.reason_link_is_blocked = reason_for_block
                link_issue_on_stage.auto_linked_from_twitter_suggestion = False
                # We don't need to update here because set set auto_now=True in the field
                # follow_issue_on_stage.date_last_changed =
                link_issue_on_stage.save()
                link_issue_on_stage_we_vote_id = link_issue_on_stage.issue_we_vote_id
                link_issue_on_stage_found = True
                status += 'UPDATE ' + str(link_active)
            except Exception as e:
                status += 'FAILED_TO_UPDATE ' + str(link_active)
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        elif results['MultipleObjectsReturned']:
            logger.warning("link_issue: delete all but one and take it over?")
            status += 'TOGGLE_LINKING MultipleObjectsReturned ' + str(link_active)
        else:
            # Create new link_issue entry
            if issue_found:
                try:
                    if positive_value_exists(organization_we_vote_id) \
                            and positive_value_exists(issue_id) and positive_value_exists(issue_we_vote_id):
                        link_issue_on_stage = OrganizationLinkToIssue(
                            organization_we_vote_id=organization_we_vote_id,
                            issue_id=issue_id,
                            issue_we_vote_id=issue_we_vote_id,
                        )
                        link_issue_on_stage.link_active = link_active
                        link_issue_on_stage.reason_for_link = reason_for_link
                        link_issue_on_stage.link_blocked = link_blocked
                        link_issue_on_stage.reason_for_block = reason_for_block

                        link_issue_on_stage.save()
                        link_issue_on_stage_we_vote_id = link_issue_on_stage.issue_we_vote_id
                        link_issue_on_stage_found = True
                        status += 'CREATE ' + str(link_active)
                    else:
                        status += "ORGANIZATION_LINK_TO_ISSUE_COULD_NOT_BE_CREATED-MISSING_ORGANIZATION "
                except Exception as e:
                    status = 'FAILED_TO_UPDATE ' + str(link_active)
                    handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

            else:
                status += 'ISSUE_NOT_FOUND_ON_CREATE ' + str(link_active)

        if positive_value_exists(link_issue_on_stage_we_vote_id) and issue_found:
            # If a link issue was saved, update the linked_organization_count
            organization_link_issue_list_manager = OrganizationLinkToIssueList()
            linked_organization_count = organization_link_issue_list_manager.fetch_linked_organization_count(
                link_issue_on_stage_we_vote_id)
            try:
                issue.linked_organization_count = linked_organization_count
                issue.save()
                status += "LINKED_ORGANIZATION_COUNT_UPDATED "
            except Exception as e:
                pass

        results = {
            'success': True if link_issue_on_stage_found else False,
            'status': status,
            'link_issue_found': link_issue_on_stage_found,
            'issue_we_vote_id': link_issue_on_stage_we_vote_id,
            'link_issue': link_issue_on_stage,
        }
        return results

    def retrieve_issue_link(self, link_issue_id, organization_we_vote_id, issue_id, issue_we_vote_id):
        """
        link_issue_id is the identifier for records stored in this table (it is NOT the issue_id)
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        link_issue_on_stage = OrganizationLinkToIssue()
        link_issue_on_stage_we_vote_id = 0

        try:
            if positive_value_exists(link_issue_id):
                link_issue_on_stage = OrganizationLinkToIssue.objects.get(id=link_issue_id)
                link_issue_on_stage_we_vote_id = link_issue_on_stage.issue_we_vote_id
                success = True
                status = 'LINK_ISSUE_FOUND_WITH_ID'
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(issue_id):
                link_issue_on_stage = OrganizationLinkToIssue.objects.get(
                    organization_we_vote_id__iexact=organization_we_vote_id,
                    issue_id=issue_id)
                link_issue_on_stage_we_vote_id = link_issue_on_stage.issue_we_vote_id
                success = True
                status = 'LINK_ISSUE_FOUND_WITH_ORGANIZATION_ID_WE_VOTE_ID_AND_ISSUE_ID'
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(issue_we_vote_id):
                link_issue_on_stage = OrganizationLinkToIssue.objects.get(
                    organization_we_vote_id__iexact=organization_we_vote_id,
                    issue_we_vote_id__iexact=issue_we_vote_id)
                link_issue_on_stage_we_vote_id = link_issue_on_stage.issue_we_vote_id
                success = True
                status = 'LINK_ISSUE_FOUND_WITH_ORGANIZATION_ID_WE_VOTE_ID_AND_ISSUE_WE_VOTE_ID'
            else:
                success = False
                status = 'LINK_ISSUE_MISSING_REQUIRED_VARIABLES'
        except OrganizationLinkToIssue.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = 'LINK_ISSUE_NOT_FOUND_MultipleObjectsReturned'
        except OrganizationLinkToIssue.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = 'LINK_ISSUE_NOT_FOUND_DoesNotExist'

        if positive_value_exists(link_issue_on_stage_we_vote_id):
            link_issue_on_stage_found = True
            is_linked = link_issue_on_stage.is_linked()
            is_not_linked = link_issue_on_stage.is_not_linked()
        else:
            link_issue_on_stage_found = False
            is_linked = False
            is_not_linked = True
        results = {
            'status':                   status,
            'success':                  success,
            'link_issue_found':         link_issue_on_stage_found,
            'link_issue_id':            link_issue_on_stage_we_vote_id,
            'link_issue':               link_issue_on_stage,
            'is_linked':                is_linked,
            'is_not_linked':            is_not_linked,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results
