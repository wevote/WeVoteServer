# issue/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import IssueListManager, Issue, IssueManager, MOST_LINKED_ORGANIZATIONS, OrganizationLinkToIssue
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_exception
import json
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ISSUES_SYNC_URL = get_environment_variable("ISSUES_SYNC_URL")
ORGANIZATION_LINK_TO_ISSUE_SYNC_URL = get_environment_variable("ORGANIZATION_LINK_TO_ISSUE_SYNC_URL")


def issues_import_from_master_server(request):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Issues from We Vote Master servers",
        ISSUES_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
        }
    )

    if import_results['success']:
        import_results = issues_import_from_structured_json(structured_json)

    return import_results


def issues_import_from_structured_json(structured_json):
    issues_saved = 0
    issues_updated = 0
    issues_not_processed = 0
    for one_issue in structured_json:
        # Bring variables from the structure_json in, with error checking
        we_vote_id = one_issue["we_vote_id"] if "we_vote_id" in one_issue else False
        issue_name = one_issue["issue_name"] if "issue_name" in one_issue else False
        issue_description = one_issue["issue_description"] if "issue_description" in one_issue else False
        issue_followers_count = one_issue["issue_followers_count"] if "issue_followers_count" in one_issue else False
        linked_organization_count = \
            one_issue["linked_organization_count"] if "linked_organization_count" in one_issue else False
        we_vote_hosted_image_url_large = \
            one_issue["we_vote_hosted_image_url_large"] if "we_vote_hosted_image_url_large" in one_issue else False
        we_vote_hosted_image_url_medium = \
            one_issue["we_vote_hosted_image_url_medium"] if "we_vote_hosted_image_url_medium" in one_issue else False
        we_vote_hosted_image_url_tiny = \
            one_issue["we_vote_hosted_image_url_tiny"] if "we_vote_hosted_image_url_tiny" in one_issue else False

        # Make sure we have the minimum required variables
        if not positive_value_exists(we_vote_id) or not positive_value_exists(issue_name):
            issues_not_processed += 1
            continue

        # Check to see if this issue is already being used anywhere
        issue_on_stage_found = False
        try:
            if positive_value_exists(we_vote_id):
                issue_query = Issue.objects.filter(we_vote_id__iexact=we_vote_id)
                if len(issue_query):
                    issue_on_stage = issue_query[0]
                    issue_on_stage_found = True
        except Issue.DoesNotExist:
            # No problem that we aren't finding existing issue
            pass
        except Exception as e:
            # handle_record_not_found_exception(e, logger=logger)
            # We want to skip to the next org
            continue

        try:
            if issue_on_stage_found:
                # Update existing issue in the database
                if issue_name is not False:
                    issue_on_stage.issue_name = issue_name
            else:
                # Create new
                issue_on_stage = Issue(
                    we_vote_id=we_vote_id,
                    issue_name=issue_name,
                )

            # Now save all of the fields in common to updating an existing entry vs. creating a new entry
            if issue_description is not False:
                issue_on_stage.issue_description = issue_description
            if issue_followers_count is not False:
                issue_on_stage.issue_followers_count = issue_followers_count
            if linked_organization_count is not False:
                issue_on_stage.linked_organization_count = linked_organization_count
            if we_vote_hosted_image_url_large is not False:
                issue_on_stage.we_vote_hosted_image_url_large = we_vote_hosted_image_url_large
            if we_vote_hosted_image_url_medium is not False:
                issue_on_stage.we_vote_hosted_image_url_medium = we_vote_hosted_image_url_medium
            if we_vote_hosted_image_url_tiny is not False:
                issue_on_stage.we_vote_hosted_image_url_tiny = we_vote_hosted_image_url_tiny

            issue_on_stage.save()
            if issue_on_stage_found:
                issues_updated += 1
            else:
                issues_saved += 1
        except Exception as e:
            issues_not_processed += 1

    issues_results = {
        'success':              True,
        'status':               "ISSUE_IMPORT_PROCESS_COMPLETE",
        'issues_saved':         issues_saved,
        'issues_updated':       issues_updated,
        'issues_not_processed': issues_not_processed,
    }
    return issues_results


def issue_retrieve_for_api(issue_id, issue_we_vote_id):  # issueRetrieve
    """
    Used by the api
    :param issue_id:
    :param issue_we_vote_id:
    :return:
    """
    # NOTE: Issues retrieve is independent of *who* wants to see the data. Issues retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItems does

    if not positive_value_exists(issue_id) and not positive_value_exists(issue_we_vote_id):
        status = 'VALID_ISSUE_ID_AND_ISSUE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'id':                       issue_id,
            'we_vote_id':               issue_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    issue_manager = IssueManager()
    if positive_value_exists(issue_id):
        results = issue_manager.retrieve_issue_from_id(issue_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(issue_we_vote_id):
        results = issue_manager.retrieve_issue_from_we_vote_id(issue_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_ISSUE_ID_AND_ISSUE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'id':                       issue_id,
            'we_vote_id':               issue_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        issue = results['issue']
        json_data = {
            'status':                       status,
            'success':                      True,
            'we_vote_id':                   issue.we_vote_id,
            'issue_name':     issue.issue_name,
            'issue_description':              issue.issue_description,
            'issue_photo_url_large':    issue.we_vote_hosted_profile_image_url_large
                if positive_value_exists(issue.we_vote_hosted_profile_image_url_large)
                else issue.issue_photo_url(),
            'issue_photo_url_medium':   issue.we_vote_hosted_profile_image_url_medium,
            'issue_photo_url_tiny':     issue.we_vote_hosted_profile_image_url_tiny,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'we_vote_id':               issue_we_vote_id,
            'issue_name':               "",
            'issue_description': "",
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issues_retrieve_for_api(sort_formula):  # issuesRetrieve
    """
    Used by the api
    :return:
    """
    # NOTE: Issues retrieve is independent of *who* wants to see the data.

    issue_list = []
    issues_to_display = []
    try:
        issue_list_object = IssueListManager()
        results = issue_list_object.retrieve_issues(sort_formula)
        success = results['success']
        status = results['status']
        issue_list = results['issue_list']
    except Exception as e:
        status = 'FAILED issues_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        for issue in issue_list:
            one_issue = {
                'issue_we_vote_id':         issue.we_vote_id,
                'issue_name':               issue.issue_name,
                'issue_photo_url_large':    issue.we_vote_hosted_image_url_large,
                'issue_photo_url_medium':   issue.we_vote_hosted_image_url_medium,
                'issue_photo_url_tiny':     issue.we_vote_hosted_image_url_tiny,
            }
            issues_to_display.append(one_issue.copy())
        json_data = {
            'status':                   status,
            'success':                  True,
            'issue_list':               issues_to_display,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'issue_list':               [],
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_link_to_issue_import_from_master_server(request):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Organization's Links To Issues data from We Vote Master servers",
        ORGANIZATION_LINK_TO_ISSUE_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
        }
    )

    if import_results['success']:
        import_results = organization_link_to_issue_import_from_structured_json(structured_json)

    return import_results


def organization_link_to_issue_import_from_structured_json(structured_json):
    organization_link_to_issue_saved = 0
    organization_link_to_issue_updated = 0
    organization_link_to_issue_not_processed = 0
    issue_manager = IssueManager()
    for one_entry in structured_json:
        # Bring variables from the structure_json in, with error checking
        organization_we_vote_id = \
            one_entry["organization_we_vote_id"] if "organization_we_vote_id" in one_entry else False
        issue_we_vote_id = one_entry["issue_we_vote_id"] if "issue_we_vote_id" in one_entry else False
        link_active = one_entry["link_active"] if "link_active" in one_entry else False
        reason_for_link = one_entry["reason_for_link"] if "reason_for_link" in one_entry else False
        link_blocked = one_entry["link_blocked"] if "link_blocked" in one_entry else False
        reason_link_is_blocked = one_entry["reason_link_is_blocked"] if "reason_link_is_blocked" in one_entry else False

        # Make sure we have the minimum required variables
        if not positive_value_exists(organization_we_vote_id) or not positive_value_exists(issue_we_vote_id):
            organization_link_to_issue_not_processed += 1
            continue

        # Check to see if this organization_link_to_issue is already being used anywhere
        organization_link_found = False
        try:
            organization_link_query = OrganizationLinkToIssue.objects.filter(
                organization_we_vote_id__iexact=organization_we_vote_id)
            organization_link_query = organization_link_query.filter(issue_we_vote_id__iexact=issue_we_vote_id)
            if len(organization_link_query):
                organization_link = organization_link_query[0]
                organization_link_found = True
        except OrganizationLinkToIssue.DoesNotExist:
            # No problem that we aren't finding existing issue
            pass
        except Exception as e:
            # handle_record_not_found_exception(e, logger=logger)
            # We want to skip to the next org link
            continue

        try:
            if not organization_link_found:
                # Create new
                organization_link = OrganizationLinkToIssue(
                    organization_we_vote_id=organization_we_vote_id,
                    issue_we_vote_id=issue_we_vote_id,
                )

            # Now save all of the fields in common to updating an existing entry vs. creating a new entry
            if not positive_value_exists(organization_link.issue_id):
                issue_id = issue_manager.fetch_issue_id_from_we_vote_id(organization_link.issue_we_vote_id)
                if issue_id != 0:
                    organization_link.issue_id = issue_id
            if link_active is not False:
                organization_link.link_active = link_active
            if reason_for_link is not False:
                organization_link.reason_for_link = reason_for_link
            if link_blocked is not False:
                organization_link.link_blocked = link_blocked
            if reason_link_is_blocked is not False:
                organization_link.reason_link_is_blocked = reason_link_is_blocked

            organization_link.save()
            if organization_link_found:
                organization_link_to_issue_updated += 1
            else:
                organization_link_to_issue_saved += 1
        except Exception as e:
            organization_link_to_issue_not_processed += 1

    issues_results = {
        'success':                                  True,
        'status':                                   "ORGANIZATION_LINK_TO_ISSUE_IMPORT_PROCESS_COMPLETE",
        'organization_link_to_issue_saved':         organization_link_to_issue_saved,
        'organization_link_to_issue_updated':       organization_link_to_issue_updated,
        'organization_link_to_issue_not_processed': organization_link_to_issue_not_processed,
    }
    return issues_results
