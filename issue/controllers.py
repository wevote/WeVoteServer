# issue/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import IssueListManager, Issue, IssueManager, MOST_LINKED_ORGANIZATIONS, OrganizationLinkToIssue
from config.base import get_environment_variable
from django.http import HttpResponse
from exception.models import handle_exception
import json
from ballot.models import BallotReturnedManager
from follow.models import FollowIssueList, FOLLOWING
from issue.models import OrganizationLinkToIssueList
from position.models import ANY_STANCE, PositionListManager
from voter.models import fetch_voter_we_vote_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ISSUES_SYNC_URL = get_environment_variable("ISSUES_SYNC_URL")  # issuesSyncOut
ORGANIZATION_LINK_TO_ISSUE_SYNC_URL = \
    get_environment_variable("ORGANIZATION_LINK_TO_ISSUE_SYNC_URL")  # organizationLinkToIssueSyncOut


def update_issue_statistics():
    follow_issue_list_manager = FollowIssueList()
    organization_link_to_issue_list_manager = OrganizationLinkToIssueList()
    issues_not_updated_count = 0
    issues_updated_count = 0
    status = ''

    try:
        issue_list_query = Issue.objects.all()
        issue_list_query = issue_list_query.filter(hide_issue=False)
        issue_list = list(issue_list_query)

        for one_issue in issue_list:
            try:
                one_issue.issue_followers_count = \
                    follow_issue_list_manager.fetch_follow_issue_count_by_issue_we_vote_id(one_issue.we_vote_id)
                one_issue.linked_organization_count = \
                    organization_link_to_issue_list_manager.fetch_linked_organization_count(one_issue.we_vote_id)
                one_issue.save()
                issues_updated_count += 1
            except Exception as e:
                issues_not_updated_count += 1
                status += "FAILED: " + str(e) + " "
    except Exception as e:
        pass

    status += "ISSUE_IMPORT_PROCESS_COMPLETE, " \
              "updated: " + str(issues_updated_count) + \
              ', not_updated: ' + str(issues_not_updated_count) + ' '
    results = {
        'success':                  issues_updated_count > 0,
        'status':                   status,
        'issues_updated_count':     issues_updated_count,
        'issues_not_updated_count': issues_not_updated_count,
    }
    return results


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
        considered_left = one_issue["considered_left"] if "considered_left" in one_issue else False
        considered_right = one_issue["considered_right"] if "considered_right" in one_issue else False
        hide_issue = one_issue["hide_issue"] if "hide_issue" in one_issue else True  # We want to default to hiding
        issue_name = one_issue["issue_name"] if "issue_name" in one_issue else False
        issue_description = one_issue["issue_description"] if "issue_description" in one_issue else False
        issue_icon_local_path = one_issue["issue_icon_local_path"] if "issue_icon_local_path" in one_issue else False
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

            # Now save all the fields in common to updating an existing entry vs. creating a new entry
            if issue_description is not False:
                issue_on_stage.issue_description = issue_description
            if issue_icon_local_path is not False:
                issue_on_stage.issue_icon_local_path = issue_icon_local_path
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
            issue_on_stage.considered_left = considered_left
            issue_on_stage.considered_right = considered_right
            issue_on_stage.hide_issue = hide_issue

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
            'status':                   status,
            'success':                  True,
            'we_vote_id':               issue.we_vote_id,
            'issue_name':               issue.issue_name,
            'issue_description':        issue.issue_description,
            'issue_icon_local_path':    issue.issue_icon_local_path,
            'issue_image_url':          issue.we_vote_hosted_image_url_medium
            if positive_value_exists(issue.we_vote_hosted_image_url_medium)
            else issue.we_vote_hosted_image_url_large,
            'issue_photo_url_large':    issue.we_vote_hosted_image_url_large
            if positive_value_exists(issue.we_vote_hosted_image_url_large)
            else issue.we_vote_hosted_image_url_medium,
            'issue_photo_url_medium':   issue.we_vote_hosted_image_url_medium,
            'issue_photo_url_tiny':     issue.we_vote_hosted_image_url_tiny,
            'hide_issue':               issue.hide_issue,
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


def issue_descriptions_retrieve_for_api():  # issueDescriptionsRetrieve
    issue_list = []
    issues_to_display = []

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

    if not success:
        json_data = {
            'status': status,
            'success': False,
            'issue_list': [],
        }

        return HttpResponse(json.dumps(json_data), content_type='application/json')

    for issue in issue_list:
        linked_organization_preview_list = []
        results = retrieve_organization_preview_list(issue.we_vote_id)
        if results['success']:
            linked_organization_preview_list = results['linked_organization_preview_list']
        one_issue = {
            'considered_left':                  issue.considered_left,
            'considered_right':                 issue.considered_right,
            'issue_we_vote_id':                 issue.we_vote_id,
            'issue_name':                       issue.issue_name,
            'issue_description':                issue.issue_description,
            'issue_followers_count':            issue.issue_followers_count,
            'issue_icon_local_path':            issue.issue_icon_local_path,
            'linked_organization_count':        issue.linked_organization_count,
            'linked_organization_preview_list': linked_organization_preview_list,
        }
        issues_to_display.append(one_issue)

    json_data = {
        'status':                       status,
        'success':                      True,
        'issue_list':                   issues_to_display,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issue_organizations_retrieve_for_api(issue_we_vote_id=''):  # issueOrganizationsRetrieve
    issue_list = []
    issues_to_display = []

    try:
        issue_list_object = IssueListManager()
        if positive_value_exists(issue_we_vote_id):
            results = issue_list_object.retrieve_issues(
                issue_we_vote_id_list_to_filter=[issue_we_vote_id],
                read_only=True)
        else:
            results = issue_list_object.retrieve_issues(
                read_only=True)
        success = results['success']
        status = results['status']
        issue_list = results['issue_list']
    except Exception as e:
        status = 'FAILED issue_organizations_retrieve_for_api. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if not success:
        json_data = {
            'status':               status,
            'success':              False,
            'issue_list':           [],
            'organization_list':    [],
        }

        return HttpResponse(json.dumps(json_data), content_type='application/json')

    link_manager = OrganizationLinkToIssueList()
    complete_organization_we_vote_id_list = []
    for issue in issue_list:
        linked_organization_we_vote_id_list = []
        one_issue_list = [issue.we_vote_id]
        results = link_manager.retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(one_issue_list)
        if results['organization_we_vote_id_list_found']:
            linked_organization_we_vote_id_list = results['organization_we_vote_id_list']
            temp_combined_list = complete_organization_we_vote_id_list + linked_organization_we_vote_id_list
            values_as_keys = dict.fromkeys(temp_combined_list)
            complete_organization_we_vote_id_list = list(values_as_keys)
        one_issue = {
            'issue_we_vote_id':                 issue.we_vote_id,
            'linked_organization_we_vote_id_list': linked_organization_we_vote_id_list,
        }
        issues_to_display.append(one_issue)

    organization_list = []
    organization_list_found = False
    from organization.models import Organization
    try:
        organization_queryset = Organization.objects.all()
        organization_queryset = organization_queryset.filter(we_vote_id__in=complete_organization_we_vote_id_list)
        organization_queryset = organization_queryset.order_by('-twitter_followers_count')
        organization_list = list(organization_queryset)

        if len(organization_list):
            organization_list_found = True
            status += 'ORGANIZATIONS_FOUND '
        else:
            status += 'NO_ORGANIZATIONS_FOUND '
    except Exception as e:
        status += 'issue_organizations_retrieve_for_api: Unable to retrieve organizations from db. ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    simple_organization_list = []
    if organization_list_found:
        for organization in organization_list:
            organization_dict = {
                'organization_name': organization.organization_name,
                'organization_we_vote_id': organization.we_vote_id,
                'twitter_description': organization.twitter_description,
                'twitter_followers_count': organization.twitter_followers_count,
                'organization_twitter_handle': organization.organization_twitter_handle,
                'we_vote_hosted_profile_image_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
            }
            simple_organization_list.append(organization_dict)

    json_data = {
        'status':               status,
        'success':              success,
        'issue_list':           issues_to_display,
        'organization_list':    simple_organization_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issues_retrieve_for_api(  # issuesRetrieve  # DEPRECATED
        voter_device_id, sort_formula, google_civic_election_id=0,
        voter_issues_only=None,  # Deprecated
        include_voter_follow_status=None,
        ballot_location_shortcut=None, ballot_returned_we_vote_id=None,
        hide_ballot_item_list=False):
    """
    Used by the api
    :return:
    """

    issue_list = []
    all_issue_we_vote_ids = []
    issues_to_display = []
    issues_under_ballot_items_list = []
    issue_score_list = []  # Deprecated
    follow_issue_we_vote_id_list_for_voter = []
    ignore_issue_we_vote_id_list_for_voter = []

    if voter_issues_only is None:  # Deprecated
        voter_issues_only = False  # Deprecated
    if include_voter_follow_status is None:
        include_voter_follow_status = False

    if positive_value_exists(voter_issues_only) or positive_value_exists(include_voter_follow_status):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        if not positive_value_exists(voter_we_vote_id):
            status = 'FAILED issues_retrieve VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED'
            json_data = {
                'status': status,
                'success': False,
                'google_civic_election_id': google_civic_election_id,
                'ballot_location_shortcut': ballot_location_shortcut,
                'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
                'voter_issues_only': voter_issues_only,  # Deprecated
                'include_voter_follow_status': include_voter_follow_status,
                'issue_list': [],
                'issue_score_list': [],  # Deprecated
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')

        follow_issue_list_manager = FollowIssueList()
        follow_issue_we_vote_id_list_for_voter = follow_issue_list_manager. \
            retrieve_follow_issue_following_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id)

        if positive_value_exists(include_voter_follow_status):
            ignore_issue_we_vote_id_list_for_voter = follow_issue_list_manager. \
                retrieve_follow_issue_ignore_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id)

    try:
        issue_list_object = IssueListManager()
        if positive_value_exists(voter_issues_only):  # Deprecated
            results = issue_list_object.retrieve_issues(sort_formula, follow_issue_we_vote_id_list_for_voter)
        else:
            results = issue_list_object.retrieve_issues(sort_formula)
        success = results['success']
        status = results['status']
        issue_list = results['issue_list']
    except Exception as e:
        status = 'FAILED issues_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if not success:
        json_data = {
            'status': status,
            'success': False,
            'google_civic_election_id': google_civic_election_id,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
            'voter_issues_only': voter_issues_only,  # Deprecated
            'include_voter_follow_status': include_voter_follow_status,
            'issue_list': [],
            'issue_score_list': [],  # Deprecated
            'issues_under_ballot_items_list': [],  # Deprecated
        }

        return HttpResponse(json.dumps(json_data), content_type='application/json')

    for issue in issue_list:
        all_issue_we_vote_ids.append(issue.we_vote_id)
        if positive_value_exists(include_voter_follow_status):
            is_issue_followed = issue.we_vote_id in follow_issue_we_vote_id_list_for_voter
            is_issue_ignored = issue.we_vote_id in ignore_issue_we_vote_id_list_for_voter
        else:
            is_issue_followed = False
            is_issue_ignored = False
        one_issue = {
            'considered_left':          issue.considered_left,
            'considered_right':         issue.considered_right,
            'issue_we_vote_id':         issue.we_vote_id,
            'issue_name':               issue.issue_name,
            'issue_description':        issue.issue_description,
            'issue_icon_local_path':    issue.issue_icon_local_path,
            'issue_image_url':          issue.we_vote_hosted_image_url_medium
            if positive_value_exists(issue.we_vote_hosted_image_url_medium)
            else issue.we_vote_hosted_image_url_large,
            'issue_photo_url_large':    issue.we_vote_hosted_image_url_large,
            'issue_photo_url_medium':   issue.we_vote_hosted_image_url_medium,
            'issue_photo_url_tiny':     issue.we_vote_hosted_image_url_tiny,
            'is_issue_followed':        is_issue_followed,
            'is_issue_ignored':         is_issue_ignored,
        }
        issues_to_display.append(one_issue)

    # Now find the issue_score for each ballot_item
    if not positive_value_exists(google_civic_election_id):
        ballot_returned_manager = BallotReturnedManager()
        if positive_value_exists(ballot_location_shortcut):
            results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_location_shortcut(
                ballot_location_shortcut)
            if results['ballot_returned_found']:
                ballot_returned = results['ballot_returned']
                google_civic_election_id = ballot_returned.google_civic_election_id
        elif positive_value_exists(ballot_returned_we_vote_id):
            results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(
                ballot_returned_we_vote_id)
            if results['ballot_returned_found']:
                ballot_returned = results['ballot_returned']
                google_civic_election_id = ballot_returned.google_civic_election_id

    if positive_value_exists(follow_issue_we_vote_id_list_for_voter) \
            and positive_value_exists(google_civic_election_id):
        # Retrieve the issue_score_list for issues that the voter is following
        issue_score_list_results = retrieve_issue_score_list(follow_issue_we_vote_id_list_for_voter,  # Deprecated
                                                             google_civic_election_id)
        issue_score_list = issue_score_list_results['issue_score_list']  # Deprecated

    if positive_value_exists(all_issue_we_vote_ids) and positive_value_exists(google_civic_election_id):
        if not hide_ballot_item_list:
            # Retrieve the issue_score_list for issues that the voter is following
            issue_list_results = retrieve_issues_under_ballot_items_list(
                all_issue_we_vote_ids, google_civic_election_id)
            issues_under_ballot_items_list = issue_list_results['issues_under_ballot_items_list']

    json_data = {
        'status':                       status,
        'success':                      True,
        'google_civic_election_id':     google_civic_election_id,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
        'voter_issues_only':            voter_issues_only,  # Deprecated
        'include_voter_follow_status':  include_voter_follow_status,
        'issue_list':                   issues_to_display,
        'issue_score_list':             issue_score_list,  # Deprecated
        'issues_under_ballot_items_list': issues_under_ballot_items_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issues_followed_retrieve_for_api(voter_device_id):  # issuesFollowedRetrieve
    issues_followed_list = []
    all_issue_we_vote_ids = []

    voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_we_vote_id):
        status = 'FAILED issues_retrieve VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED'
        json_data = {
            'status': status,
            'success': False,
            'issues_followed_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    follow_issue_list_manager = FollowIssueList()
    follow_issue_we_vote_id_list_for_voter = follow_issue_list_manager. \
        retrieve_follow_issue_following_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id)

    # Not currently used in WebApp
    # ignore_issue_we_vote_id_list_for_voter = follow_issue_list_manager. \
    #     retrieve_follow_issue_ignore_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id)

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

    if not success:
        json_data = {
            'status': status,
            'success': False,
            'issues_followed_list': [],
        }

        return HttpResponse(json.dumps(json_data), content_type='application/json')

    for issue in issue_list:
        all_issue_we_vote_ids.append(issue.we_vote_id)
        is_issue_followed = issue.we_vote_id in follow_issue_we_vote_id_list_for_voter
        # is_issue_ignored = issue.we_vote_id in ignore_issue_we_vote_id_list_for_voter
        one_issue = {
            'issue_we_vote_id':         issue.we_vote_id,
            'issue_name':               issue.issue_name,
            'is_issue_followed':        is_issue_followed,
            # 'is_issue_ignored':         is_issue_ignored,  # Not currently used in WebApp
        }
        issues_followed_list.append(one_issue)

    json_data = {
        'status':                   status,
        'success':                  True,
        'issues_followed_list':     issues_followed_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issues_under_ballot_items_retrieve_for_api(  # issuesUnderBallotItemsRetrieve
        google_civic_election_id=0,
        ballot_location_shortcut=None,
        ballot_returned_we_vote_id=None):
    """
    Used by the api
    :return:
    """

    issue_list = []
    all_issue_we_vote_ids = []
    issues_under_ballot_items_list = []
    status = ""

    required_variable_exists = \
        positive_value_exists(google_civic_election_id) or positive_value_exists(ballot_location_shortcut) or \
        positive_value_exists(ballot_returned_we_vote_id)
    if not required_variable_exists:
        status += "MISSING_REQUIRED_VARIABLE "
        json_data = {
            'status': status,
            'success': False,
            'google_civic_election_id': google_civic_election_id,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
            'issues_under_ballot_items_list': [],
        }

        return HttpResponse(json.dumps(json_data), content_type='application/json')

    try:
        issue_list_object = IssueListManager()
        results = issue_list_object.retrieve_issues()
        success = results['success']
        status += results['status']
        issue_list = results['issue_list']
    except Exception as e:
        status += 'FAILED issues_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if not success:
        json_data = {
            'status': status,
            'success': False,
            'google_civic_election_id': google_civic_election_id,
            'ballot_location_shortcut': ballot_location_shortcut,
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
            'issues_under_ballot_items_list': [],
        }

        return HttpResponse(json.dumps(json_data), content_type='application/json')

    for issue in issue_list:
        all_issue_we_vote_ids.append(issue.we_vote_id)

    if not positive_value_exists(google_civic_election_id):
        ballot_returned_manager = BallotReturnedManager()
        if positive_value_exists(ballot_location_shortcut):
            results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_location_shortcut(
                ballot_location_shortcut)
            if results['ballot_returned_found']:
                ballot_returned = results['ballot_returned']
                google_civic_election_id = ballot_returned.google_civic_election_id
        elif positive_value_exists(ballot_returned_we_vote_id):
            results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(
                ballot_returned_we_vote_id)
            if results['ballot_returned_found']:
                ballot_returned = results['ballot_returned']
                google_civic_election_id = ballot_returned.google_civic_election_id

    if positive_value_exists(all_issue_we_vote_ids) \
            and positive_value_exists(google_civic_election_id):
        issue_list_results = retrieve_issues_under_ballot_items_list(all_issue_we_vote_ids, google_civic_election_id)
        issues_under_ballot_items_list = issue_list_results['issues_under_ballot_items_list']

    json_data = {
        'status':                       status,
        'success':                      True,
        'google_civic_election_id':     google_civic_election_id,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
        'issues_under_ballot_items_list': issues_under_ballot_items_list,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_issue_score_list(voters_issue_we_vote_ids, google_civic_election_id):  # Deprecated
    """

    :param voters_issue_we_vote_ids: This should be issues the voter is following
    :param google_civic_election_id:
    :return:
    """
    success = True
    status = ""
    issue_score_list = []  # Deprecated
    ballot_item_we_vote_ids_list = []
    organization_we_vote_ids_for_all_voter_issues = []

    organization_we_vote_id_support_by_ballot_item_list = {}  # key ballot_item_we_vote_id, value list of organizations
    organization_we_vote_id_oppose_by_ballot_item_list = {}  # key ballot_item_we_vote_id, value list of organizations
    organization_name_support_by_ballot_item_list = {}  # key ballot_item_we_vote_id, value list of organizations
    organization_name_oppose_by_ballot_item_list = {}  # key ballot_item_we_vote_id, value list of organizations
    organizations_included_by_issue_list = {}  # key is issue_we_vote_id, value is list of organizations
    issue_support_score_list = {}  # key is ballot_item_we_vote_id, value is support score of all groups issue tagged
    issue_oppose_score_list = {}  # key is ballot_item_we_vote_id, value is oppose score of all groups issue tagged

    organization_link_to_issue_list = OrganizationLinkToIssueList()
    # By issue, return a list of organization_we_vote_ids tagged with that issue
    for issue_we_vote_id in voters_issue_we_vote_ids:
        one_issue_list = [issue_we_vote_id]
        organization_we_vote_id_list = \
            organization_link_to_issue_list.fetch_organization_we_vote_id_list_by_issue_we_vote_id_list(one_issue_list)
        organizations_included_by_issue_list[issue_we_vote_id] = organization_we_vote_id_list
        for organization_we_vote_id in organization_we_vote_id_list:
            if organization_we_vote_id not in organization_we_vote_ids_for_all_voter_issues:
                organization_we_vote_ids_for_all_voter_issues.append(organization_we_vote_id)

    # Retrieve public positions for this election from every group linked to an issue the voter is following
    # (We sort them below)
    stance_we_are_looking_for = ANY_STANCE
    retrieve_public_positions = True
    position_list_manager = PositionListManager()
    # This function returns a list, not a results dict
    public_position_list = position_list_manager.retrieve_all_positions_for_election(
        google_civic_election_id, stance_we_are_looking_for, retrieve_public_positions,
        organization_we_vote_ids_for_all_voter_issues)

    # Now we loop through all of these positions and assemble a list of ballot_item_we_vote_ids for all positions
    for one_position in public_position_list:
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            ballot_item_we_vote_ids_list.append(one_position.candidate_campaign_we_vote_id)

            # Update the score for this ballot item
            if one_position.is_support_or_positive_rating():
                if one_position.candidate_campaign_we_vote_id not in issue_support_score_list:
                    issue_support_score_list[one_position.candidate_campaign_we_vote_id] = 0
                issue_support_score_list[one_position.candidate_campaign_we_vote_id] += 1
                # Store the organization_we_vote_id adding to the score
                if one_position.candidate_campaign_we_vote_id \
                        not in organization_we_vote_id_support_by_ballot_item_list:
                    organization_we_vote_id_support_by_ballot_item_list[one_position.candidate_campaign_we_vote_id] = []
                organization_we_vote_id_support_by_ballot_item_list[one_position.candidate_campaign_we_vote_id].append(
                    one_position.organization_we_vote_id)
                # Store the organization_name adding to the score
                if one_position.candidate_campaign_we_vote_id \
                        not in organization_name_support_by_ballot_item_list:
                    organization_name_support_by_ballot_item_list[one_position.candidate_campaign_we_vote_id] = []
                organization_name_support_by_ballot_item_list[one_position.candidate_campaign_we_vote_id].append(
                    one_position.speaker_display_name)
            elif one_position.is_oppose_or_negative_rating():
                if one_position.candidate_campaign_we_vote_id not in issue_oppose_score_list:
                    issue_oppose_score_list[one_position.candidate_campaign_we_vote_id] = 0
                issue_oppose_score_list[one_position.candidate_campaign_we_vote_id] += 1
                # Store the organization_we_vote_id adding to the score
                if one_position.candidate_campaign_we_vote_id not in organization_we_vote_id_oppose_by_ballot_item_list:
                    organization_we_vote_id_oppose_by_ballot_item_list[one_position.candidate_campaign_we_vote_id] = []
                organization_we_vote_id_oppose_by_ballot_item_list[one_position.candidate_campaign_we_vote_id].append(
                    one_position.organization_we_vote_id)
                # Store the organization_name adding to the score
                if one_position.candidate_campaign_we_vote_id not in organization_name_oppose_by_ballot_item_list:
                    organization_name_oppose_by_ballot_item_list[one_position.candidate_campaign_we_vote_id] = []
                organization_name_oppose_by_ballot_item_list[one_position.candidate_campaign_we_vote_id].append(
                    one_position.speaker_display_name)
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            ballot_item_we_vote_ids_list.append(one_position.contest_measure_we_vote_id)
            # Update the score for this ballot item
            if one_position.is_support_or_positive_rating():
                if one_position.contest_measure_we_vote_id not in issue_support_score_list:
                    issue_support_score_list[one_position.contest_measure_we_vote_id] = 0
                issue_support_score_list[one_position.contest_measure_we_vote_id] += 1
                # Store the organization_we_vote_id adding to the score
                if one_position.contest_measure_we_vote_id not in organization_we_vote_id_support_by_ballot_item_list:
                    organization_we_vote_id_support_by_ballot_item_list[one_position.contest_measure_we_vote_id] = []
                organization_we_vote_id_support_by_ballot_item_list[one_position.contest_measure_we_vote_id].append(
                    one_position.organization_we_vote_id)
                # Store the organization_name adding to the score
                if one_position.contest_measure_we_vote_id not in organization_name_support_by_ballot_item_list:
                    organization_name_support_by_ballot_item_list[one_position.contest_measure_we_vote_id] = []
                organization_name_support_by_ballot_item_list[one_position.contest_measure_we_vote_id].append(
                    one_position.speaker_display_name)
            elif one_position.is_oppose_or_negative_rating():
                if one_position.contest_measure_we_vote_id not in issue_oppose_score_list:
                    issue_oppose_score_list[one_position.contest_measure_we_vote_id] = 0
                issue_oppose_score_list[one_position.contest_measure_we_vote_id] += 1
                # Store the organization_we_vote_id adding to the score
                if one_position.contest_measure_we_vote_id not in organization_we_vote_id_oppose_by_ballot_item_list:
                    organization_we_vote_id_oppose_by_ballot_item_list[one_position.contest_measure_we_vote_id] = []
                organization_we_vote_id_oppose_by_ballot_item_list[one_position.contest_measure_we_vote_id].append(
                    one_position.organization_we_vote_id)
                # Store the organization_name adding to the score
                if one_position.contest_measure_we_vote_id not in organization_name_oppose_by_ballot_item_list:
                    organization_name_oppose_by_ballot_item_list[one_position.contest_measure_we_vote_id] = []
                organization_name_oppose_by_ballot_item_list[one_position.contest_measure_we_vote_id].append(
                    one_position.speaker_display_name)

    for one_ballot_item_we_vote_id in ballot_item_we_vote_ids_list:
        issue_support_score = issue_support_score_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in issue_support_score_list else 0
        issue_oppose_score = issue_oppose_score_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in issue_oppose_score_list else 0
        organization_we_vote_id_support_list = \
            organization_we_vote_id_support_by_ballot_item_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in organization_we_vote_id_support_by_ballot_item_list else []
        organization_we_vote_id_oppose_list = \
            organization_we_vote_id_oppose_by_ballot_item_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in organization_we_vote_id_oppose_by_ballot_item_list else []
        organization_name_support_list = \
            organization_name_support_by_ballot_item_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in organization_name_support_by_ballot_item_list else []
        organization_name_oppose_list = \
            organization_name_oppose_by_ballot_item_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in organization_name_oppose_by_ballot_item_list else []
        one_ballot_item = {
            "ballot_item_we_vote_id":               one_ballot_item_we_vote_id,
            "issue_support_score":                  issue_support_score,
            "issue_oppose_score":                   issue_oppose_score,
            "organization_we_vote_id_support_list": organization_we_vote_id_support_list,
            "organization_name_support_list":       organization_name_support_list,
            "organization_we_vote_id_oppose_list":  organization_we_vote_id_oppose_list,
            "organization_name_oppose_list":        organization_name_oppose_list,
        }
        issue_score_list.append(one_ballot_item)  # Deprecated

    results = {
        'success':          success,
        'status':           status,
        'issue_score_list': issue_score_list,  # Deprecated
    }
    return results


def retrieve_issues_under_ballot_items_list(all_issue_we_vote_ids, google_civic_election_id):
    """

    :param all_issue_we_vote_ids: This should be all issues
    :param google_civic_election_id:
    :return:
    """
    success = True
    status = ""
    issues_under_ballot_items_list = []
    ballot_item_we_vote_ids_list = []
    organization_we_vote_ids_for_all_issues = []

    cached_issue_we_vote_ids_under_each_organization = {}  # key organization_we_vote_id, value list issue_we_vote_ids
    organizations_included_by_issue_list = {}  # key is issue_we_vote_id, value is list of organizations
    issue_we_vote_id_list_by_ballot_item_list = {}  # key is ballot_item_we_vote_id, value is list of issue_we_vote_ids
    oppose_issue_we_vote_id_list = {}  # key is ballot_item_we_vote_id, value is list of issue_we_vote_ids opposing
    support_issue_we_vote_id_list = {}  # key is ballot_item_we_vote_id, value is list of issue_we_vote_ids supporting

    organization_link_to_issue_list = OrganizationLinkToIssueList()
    # By issue, return a list of organization_we_vote_ids tagged with that issue
    for issue_we_vote_id in all_issue_we_vote_ids:
        one_issue_list = [issue_we_vote_id]
        organization_we_vote_id_list = \
            organization_link_to_issue_list.fetch_organization_we_vote_id_list_by_issue_we_vote_id_list(one_issue_list)
        organizations_included_by_issue_list[issue_we_vote_id] = organization_we_vote_id_list
        for organization_we_vote_id in organization_we_vote_id_list:
            if organization_we_vote_id not in organization_we_vote_ids_for_all_issues:
                organization_we_vote_ids_for_all_issues.append(organization_we_vote_id)

    # Retrieve public positions for this election from every group linked to an issue the voter is following
    # (We sort them below)
    stance_we_are_looking_for = ANY_STANCE
    retrieve_public_positions = True
    position_list_manager = PositionListManager()
    # This function returns a list, not a results dict
    public_position_list = position_list_manager.retrieve_all_positions_for_election(
        google_civic_election_id, stance_we_are_looking_for, retrieve_public_positions,
        organization_we_vote_ids_for_all_issues)

    # Now we loop through all of these positions and assemble a list of ballot_item_we_vote_ids for all positions
    for one_position in public_position_list:
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            ballot_item_we_vote_ids_list.append(one_position.candidate_campaign_we_vote_id)

            # If there is a position on the voter's ballot, we want to retrieve the issues from the organization
            #  taking the position
            if one_position.is_support_or_positive_rating() or one_position.is_oppose_or_negative_rating():
                if one_position.organization_we_vote_id not in cached_issue_we_vote_ids_under_each_organization:
                    # Only retrieve this once per organization
                    cached_issue_we_vote_ids_under_each_organization[one_position.organization_we_vote_id] = \
                        organization_link_to_issue_list.fetch_issue_we_vote_id_list_by_organization_we_vote_id(
                            one_position.organization_we_vote_id)

                # Deprecate in late 2022
                if one_position.candidate_campaign_we_vote_id not in issue_we_vote_id_list_by_ballot_item_list:
                    issue_we_vote_id_list_by_ballot_item_list[one_position.candidate_campaign_we_vote_id] = []
                for issue_we_vote_id in \
                        cached_issue_we_vote_ids_under_each_organization[one_position.organization_we_vote_id]:
                    if issue_we_vote_id not in \
                            issue_we_vote_id_list_by_ballot_item_list[one_position.candidate_campaign_we_vote_id]:
                        issue_we_vote_id_list_by_ballot_item_list[one_position.candidate_campaign_we_vote_id].append(
                            issue_we_vote_id)

            if one_position.is_support_or_positive_rating():
                if one_position.candidate_campaign_we_vote_id not in support_issue_we_vote_id_list:
                    support_issue_we_vote_id_list[one_position.candidate_campaign_we_vote_id] = []
                for issue_we_vote_id in \
                        cached_issue_we_vote_ids_under_each_organization[one_position.organization_we_vote_id]:
                    if issue_we_vote_id not in \
                            support_issue_we_vote_id_list[one_position.candidate_campaign_we_vote_id]:
                        support_issue_we_vote_id_list[one_position.candidate_campaign_we_vote_id].append(
                            issue_we_vote_id)
            elif one_position.is_oppose_or_negative_rating():
                if one_position.candidate_campaign_we_vote_id not in oppose_issue_we_vote_id_list:
                    oppose_issue_we_vote_id_list[one_position.candidate_campaign_we_vote_id] = []
                for issue_we_vote_id in \
                        cached_issue_we_vote_ids_under_each_organization[one_position.organization_we_vote_id]:
                    if issue_we_vote_id not in \
                            oppose_issue_we_vote_id_list[one_position.candidate_campaign_we_vote_id]:
                        oppose_issue_we_vote_id_list[one_position.candidate_campaign_we_vote_id].append(
                            issue_we_vote_id)

        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            ballot_item_we_vote_ids_list.append(one_position.contest_measure_we_vote_id)

    for one_ballot_item_we_vote_id in ballot_item_we_vote_ids_list:
        issue_we_vote_id_list_for_one_ballot_item = \
            issue_we_vote_id_list_by_ballot_item_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in issue_we_vote_id_list_by_ballot_item_list else []
        oppose_by_ballot_item_list = \
            oppose_issue_we_vote_id_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in oppose_issue_we_vote_id_list else []
        support_by_ballot_item_list = \
            support_issue_we_vote_id_list[one_ballot_item_we_vote_id] \
            if one_ballot_item_we_vote_id in support_issue_we_vote_id_list else []
        one_ballot_item = {
            "ballot_item_we_vote_id":   one_ballot_item_we_vote_id,  # DEPRECATE in late 2022
            "ballot_item":              one_ballot_item_we_vote_id,
            "issue_we_vote_id_list":    issue_we_vote_id_list_for_one_ballot_item,  # DEPRECATE in late 2022
            "oppose":                   oppose_by_ballot_item_list,
            "support":                  support_by_ballot_item_list,
        }
        issues_under_ballot_items_list.append(one_ballot_item)

    results = {
        'success':          success,
        'status':           status,
        'issues_under_ballot_items_list': issues_under_ballot_items_list,
    }
    return results


def retrieve_issues_to_follow_for_api(voter_device_id, sort_formula):  # retrieveIssuesToFollow # DEPRECATED
    """
    Instead of this function, please use issuesFollowedRetrieve
    :param voter_device_id:
    :param sort_formula:
    :return:
    """
    issue_list = []
    issues_to_display = []
    status = ""

    voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_we_vote_id):
        status += 'retrieve_issues_to_follow VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED '
        # We want to always retrieve issues, even if there isn't a valid voter_we_vote_id
        # json_data = {
        #     'status': status,
        #     'success': False,
        #     'issue_list': [],
        # }
        # return HttpResponse(json.dumps(json_data), content_type='application/json')

    follow_issue_list_manager = FollowIssueList()
    if positive_value_exists(voter_we_vote_id):
        follow_issue_we_vote_id_list_for_voter = follow_issue_list_manager. \
            retrieve_follow_issue_following_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id)
        ignore_issue_we_vote_id_list_for_voter = follow_issue_list_manager. \
            retrieve_follow_issue_ignore_we_vote_id_list_by_voter_we_vote_id(voter_we_vote_id)
        issue_we_vote_id_list_to_exclude = follow_issue_we_vote_id_list_for_voter + \
            ignore_issue_we_vote_id_list_for_voter
    else:
        issue_we_vote_id_list_to_exclude = []

    try:
        issue_list_object = IssueListManager()
        issue_we_vote_id_list_to_filter = None
        results = issue_list_object.retrieve_issues(sort_formula, issue_we_vote_id_list_to_filter,
                                                    issue_we_vote_id_list_to_exclude)
        success = results['success']
        status += results['status']
        issue_list = results['issue_list']
    except Exception as e:
        status = 'FAILED retrieve_issues_to_follow ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        for issue in issue_list:
            one_issue = {
                'issue_we_vote_id':             issue.we_vote_id,
                'issue_name':                   issue.issue_name,
                'issue_description':            issue.issue_description,
                'issue_icon_local_path':        issue.issue_icon_local_path,
                'issue_image_url':              issue.we_vote_hosted_image_url_medium
                if positive_value_exists(issue.we_vote_hosted_image_url_medium)
                else issue.we_vote_hosted_image_url_large,
                'issue_photo_url_large':        issue.we_vote_hosted_image_url_large,
                'issue_photo_url_medium':       issue.we_vote_hosted_image_url_medium,
                'issue_photo_url_tiny':         issue.we_vote_hosted_image_url_tiny,
                'linked_organization_count':    issue.linked_organization_count,
                'issue_followers_count':        issue.issue_followers_count,
            }
            issues_to_display.append(one_issue)

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
        request, "Loading Endorser's Links To Issues data from We Vote Master servers",
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

            # Now save all the fields in common to updating an existing entry vs. creating a new entry
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


def retrieve_issues_linked_to_organization_for_api(organization_we_vote_id):
    organization_link_to_issue_list = OrganizationLinkToIssueList()
    issue_we_vote_ids_linked = organization_link_to_issue_list. \
        fetch_issue_we_vote_id_list_by_organization_we_vote_id(organization_we_vote_id)

    issue_list_manager = IssueListManager()
    sort_formula = None
    empty_issue_we_vote_id_list_to_exclude = None
    require_filter_or_exclude = True
    issues_linked_result = issue_list_manager.retrieve_issues(
        sort_formula, issue_we_vote_ids_linked, empty_issue_we_vote_id_list_to_exclude, require_filter_or_exclude)

    issues_linked = []
    if issues_linked_result['issue_list_found']:
        for issue in issues_linked_result['issue_list']:
            one_issue = {
                'issue_we_vote_id':         issue.we_vote_id,
                'issue_name':               issue.issue_name,
                'issue_description':        issue.issue_description,
                'issue_photo_url_large':    issue.we_vote_hosted_image_url_large,
                'issue_photo_url_medium':   issue.we_vote_hosted_image_url_medium,
                'issue_photo_url_tiny':     issue.we_vote_hosted_image_url_tiny,
                'hide_issue':               issue.hide_issue,
            }
            issues_linked.append(one_issue)

    issues_linked_result['issue_list'] = issues_linked
    return issues_linked_result


def retrieve_issues_not_linked_to_organization_for_api(organization_we_vote_id):
    organization_link_to_issue_list = OrganizationLinkToIssueList()
    issue_we_vote_ids_linked = organization_link_to_issue_list. \
        fetch_issue_we_vote_id_list_by_organization_we_vote_id(organization_we_vote_id)

    issue_list_manager = IssueListManager()
    sort_formula = None
    empty_issue_we_vote_id_list_to_filter = None
    require_filter_or_exclude = True
    issues_linked_result = issue_list_manager.retrieve_issues(
        sort_formula, empty_issue_we_vote_id_list_to_filter, issue_we_vote_ids_linked, require_filter_or_exclude)

    issues_not_linked = []
    if issues_linked_result['issue_list_found']:
        for issue in issues_linked_result['issue_list']:
            one_issue = {
                'issue_we_vote_id':         issue.we_vote_id,
                'issue_name':               issue.issue_name,
                'issue_description':        issue.issue_description,
                'issue_photo_url_large':    issue.we_vote_hosted_image_url_large,
                'issue_photo_url_medium':   issue.we_vote_hosted_image_url_medium,
                'issue_photo_url_tiny':     issue.we_vote_hosted_image_url_tiny,
            }
            issues_not_linked.append(one_issue)

    issues_linked_result['issue_list'] = issues_not_linked
    return issues_linked_result


def retrieve_organization_preview_list(issue_we_vote_id):
    status = ''
    success = True
    issue_we_vote_id_list = [issue_we_vote_id]
    linked_organization_preview_list = []
    organization_list = []
    organization_list_found = False

    link_manager = OrganizationLinkToIssueList()
    results = link_manager.retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(issue_we_vote_id_list)
    if results['organization_we_vote_id_list_found']:
        organization_we_vote_id_list = results['organization_we_vote_id_list']
        from organization.models import Organization
        try:
            organization_queryset = Organization.objects.all()
            organization_queryset = organization_queryset.filter(we_vote_id__in=organization_we_vote_id_list)
            organization_queryset = organization_queryset.order_by('-twitter_followers_count')
            organization_list = organization_queryset[:5]

            if len(organization_list):
                organization_list_found = True
                status += 'ORGANIZATIONS_FOUND '
            else:
                status += 'NO_ORGANIZATIONS_FOUND '
        except Exception as e:
            status += 'retrieve_organizations_by_id_list: Unable to retrieve organizations from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if organization_list_found:
            for organization in organization_list:
                organization_dict = {
                    'organization_name':                        organization.organization_name,
                    'organization_we_vote_id':                  organization.we_vote_id,
                    'twitter_description':                      organization.twitter_description,
                    'twitter_followers_count':                  organization.twitter_followers_count,
                    'organization_twitter_handle':              organization.organization_twitter_handle,
                    'we_vote_hosted_profile_image_url_medium':  organization.we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_image_url_tiny':    organization.we_vote_hosted_profile_image_url_tiny,
                }
                linked_organization_preview_list.append(organization_dict)

    results = {
        'success':                                  success,
        'status':                                   status,
        'linked_organization_preview_list':         linked_organization_preview_list,
    }
    return results


# Steve, Temporary location for this function, as of July 16, 2018 --
# It could be left "as is" as a "pinger" that keeps the load balancer channel open (Keeps it from rotating to another
# node in mid request) or we could move this to the place where it can read a global value with progress statistics
# that you want to display for some script
global_dot_string = ""
global_dot_string_increasing = True


def test_real_time_update(request):  # testRealTimeUpdate

    global global_dot_string
    global global_dot_string_increasing
    length = len(global_dot_string)

    if global_dot_string_increasing:
        if length == 10:
            global_dot_string_increasing = False
            global_dot_string = global_dot_string[0:9]
        else:
            global_dot_string = global_dot_string + "."
    else:
        if length == 0:
            global_dot_string_increasing = True
            global_dot_string = "."
        else:
            global_dot_string = global_dot_string[0:length-1]

    json_data = {
        'text': global_dot_string,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
