# issue/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_last_issue_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


class IssueListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Issues
    """

    def retrieve_issues(self):
        issue_list = []
        issue_list_found = False

        try:
            issue_queryset = Issue.objects.all()
            # if positive_value_exists(issue_id):
            #     issue_queryset = issue_queryset.filter(issue_id=issue_id)
            # elif positive_value_exists(issue_we_vote_id):
            #     issue_queryset = issue_queryset.filter(issue_we_vote_id=issue_we_vote_id)
            issue_queryset = issue_queryset.order_by('-issue_followers_count')
            issue_list = issue_queryset

            if len(issue_list):
                issue_list_found = True
                status = 'ISSUES_RETRIEVED'
            else:
                status = 'NO_ISSUES_RETRIEVED'
        except Issue.DoesNotExist:
            # No issues found. Not a problem.
            status = 'NO_ISSUES_FOUND_DoesNotExist'
            issue_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_issues_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':              True if issue_list_found else False,
            'status':               status,
            'issue_list_found': issue_list_found,
            'issue_list':       issue_list,
        }
        return results

    def retrieve_issue_count(self):
        try:
            issue_queryset = Issue.objects.all()
            issue_list = issue_queryset

            issue_count = issue_list.count()
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


class Issue(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "issue", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_issue_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this issue", max_length=255, default=None, null=True,
        blank=True, unique=True)
    issue_name = models.CharField(verbose_name="name of the issue", max_length=255, null=True, blank=True)
    # The description of the issue.
    issue_description = models.TextField(verbose_name="description of the issue",
                                         null=True, blank=True, default="")
    issue_followers_count = models.PositiveIntegerField(verbose_name="number of followers of this issue",
                                                        null=False, blank=True, default=0)
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
            next_local_integer = fetch_next_we_vote_id_last_issue_integer()
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

        if not positive_value_exists(issue_name) and not positive_value_exists(issue_we_vote_id):
            success = False
            status += 'MISSING_ISSUE_NAME_AND_WE_VOTE_ID '
        else:
            # Given we might have the office listed by google_civic_office_name
            # OR office_name, we need to check both before we try to create a new entry
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
                    for key, value in updated_issue_values.items():
                        if hasattr(issue_on_stage, key):
                            setattr(issue_on_stage, key, value)
                    issue_on_stage.save()
                    new_issue_created = False
                    success = True
                    status += "ISSUE_UPDATED "
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_ISSUE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    issue_on_stage = Issue.objects.create()
                    for key, value in updated_issue_values.items():
                        if hasattr(issue_on_stage, key):
                            setattr(issue_on_stage, key, value)
                    issue_on_stage.save()
                    new_issue_created = True
                    success = True
                    status += "ISSUE_CREATED "
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
