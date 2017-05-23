# issue/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import IssueListManager, Issue, IssueManager
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_exception
import json
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ISSUES_SYNC_URL = get_environment_variable("ISSUES_SYNC_URL")


def issues_import_from_master_server(request):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    messages.add_message(request, messages.INFO, "Loading Issues from We Vote Master servers")
    logger.info("Loading Issues from We Vote Master servers")
    # Request json file from We Vote servers
    request = requests.get(ISSUES_SYNC_URL, params={
        "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    })
    structured_json = json.loads(request.text)

    import_results = issues_import_from_structured_json(structured_json)

    return import_results


def issues_import_from_structured_json(structured_json):
    issues_saved = 0
    issues_updated = 0
    issues_not_processed = 0
    for one_issue in structured_json:
        # We have already removed duplicate issues

        # Make sure we have the minimum required variables
        if not positive_value_exists(one_issue["we_vote_id"]) or \
                not positive_value_exists(one_issue["issue_name"]):
            issues_not_processed += 1
            continue

        # Check to see if this issue is already being used anywhere
        issue_on_stage_found = False
        try:
            if positive_value_exists(one_issue["we_vote_id"]):
                issue_query = Issue.objects.filter(we_vote_id=one_issue["we_vote_id"])
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
            we_vote_id = one_issue["we_vote_id"]
            issue_name = one_issue["issue_name"] \
                if 'issue_name' in one_issue else False
            issue_description = one_issue["issue_description"] \
                if 'issue_description' in one_issue else False

            if issue_on_stage_found:
                # Update existing issue in the database
                if we_vote_id is not False:
                    issue_on_stage.we_vote_id = we_vote_id
                if issue_name is not False:
                    issue_on_stage.issue_name = issue_name
            else:
                # Create new
                issue_on_stage = Issue(
                    we_vote_id=one_issue["we_vote_id"],
                    issue_name=one_issue["issue_name"],
                )

            # Now save all of the fields in common to updating an existing entry vs. creating a new entry
            if issue_description is not False:
                issue_on_stage.issue_description = issue_description

            issue_on_stage.save()
            if issue_on_stage_found:
                issues_updated += 1
            else:
                issues_saved += 1
        except Exception as e:
            issues_not_processed += 1

    issues_results = {
        'success':          True,
        'status':           "ISSUE_IMPORT_PROCESS_COMPLETE",
        'saved':            issues_saved,
        'updated':          issues_updated,
        'not_processed':    issues_not_processed,
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


def issues_retrieve_for_api():
    """
    Used by the api
    :return:
    """
    # NOTE: Issues retrieve is independent of *who* wants to see the data. Issues retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItems does

    issue_list = []
    issues_to_display = []
    google_civic_election_id = 0
    try:
        issue_list_object = IssueListManager()
        results = issue_list_object.retrieve_issues()
        success = results['success']
        status = results['status']
        issue_list = results['issue_list']
    except Exception as e:
        status = 'FAILED issues_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        # Reset office_we_vote_id and office_id so we are sure that it matches what we pull from the database
        office_id = 0
        office_we_vote_id = ''
        for issue in issue_list:
            one_issue = {
                'id':                           issue.id,
                'we_vote_id':                   issue.we_vote_id,
                'issue_name':     issue.issue_name,
                'issue_photo_url_large':    issue.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(issue.we_vote_hosted_profile_image_url_large)
                    else issue.issue_photo_url(),
                'issue_photo_url_medium':   issue.we_vote_hosted_profile_image_url_medium,
                'issue_photo_url_tiny':     issue.we_vote_hosted_profile_image_url_tiny,
            }
            issues_to_display.append(one_issue.copy())
            # Capture the office_we_vote_id and google_civic_election_id so we can return
            if not positive_value_exists(office_id) and issue.contest_office_id:
                office_id = issue.contest_office_id
            if not positive_value_exists(office_we_vote_id) and issue.contest_office_we_vote_id:
                office_we_vote_id = issue.contest_office_we_vote_id
            if not positive_value_exists(google_civic_election_id) and issue.google_civic_election_id:
                google_civic_election_id = issue.google_civic_election_id

        if len(issues_to_display):
            status = 'ISSUES_RETRIEVED'
        else:
            status = 'NO_ISSUES_RETRIEVED'

        json_data = {
            'status':                   status,
            'success':                  True,
            'issue_list':           issues_to_display,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'issue_list':           [],
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
