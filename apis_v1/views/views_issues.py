# apis_v1/views/views_organization.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from issue.models import *
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from issue.controllers import retrieve_issues_not_linked_to_organization_for_api, \
    retrieve_issues_linked_to_organization_for_api
from issue.models import LINKED_BY_ORGANIZATION, BLOCKED_BY_ORGANIZATION
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def issues_linked_to_organization_view(request):
    organization_we_vote_id = request.GET.get('organization_we_vote_id')
    issues_linked_result = retrieve_issues_linked_to_organization_for_api(organization_we_vote_id)

    success = False
    status = issues_linked_result['status']
    issues_linked = []
    if issues_linked_result['success'] and issues_linked_result['issue_list_found']:
        success = True
        issues_linked = issues_linked_result['issue_list']

    json_data = {
        'success': success,
        'status': status,
        'issue_list': issues_linked,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def issues_to_link_to_for_organization_view(request):
    organization_we_vote_id = request.GET.get('organization_we_vote_id')
    issues_linked_result = retrieve_issues_not_linked_to_organization_for_api(organization_we_vote_id)

    success = False
    status = issues_linked_result['status']
    issues_to_be_linked_to = []
    if issues_linked_result['success'] and issues_linked_result['issue_list_found']:
        success = True
        issues_to_be_linked_to = issues_linked_result['issue_list']

    json_data = {
        'success': success,
        'status': status,
        'issue_list': issues_to_be_linked_to,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_link_to_issue_view(request):
    organization_we_vote_id = request.GET.get('organization_we_vote_id', False)
    issue_we_vote_id = request.GET.get('issue_we_vote_id', False)
    organization_linked_to_issue = request.GET.get('organization_linked_to_issue', True)
    reason_for_link = request.GET.get('reason_for_link', LINKED_BY_ORGANIZATION)
    reason_for_unlink = request.GET.get('reason_for_unlink', BLOCKED_BY_ORGANIZATION)

    status = ''
    success = True

    if not positive_value_exists(organization_we_vote_id):
        status += ' ORGANIZATION_WE_VOTE_ID_NOT_PROVIDED'
        success = False
    if not positive_value_exists(issue_we_vote_id):
        status += ' ISSUE_WE_VOTE_ID_NOT_PROVIDED'
        success = False
    if not success:
        json_data = {
            'success': False,
            'status': status,
            'organization_we_vote_id': organization_we_vote_id,
            'issue_we_vote_id': issue_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if organization_linked_to_issue == 'true':
        organization_linked_to_issue = True
    elif organization_linked_to_issue == 'false':
        organization_linked_to_issue = False
    issue_id = False

    link_manager = OrganizationLinkToIssueManager()
    if organization_linked_to_issue:
        link_result = link_manager.link_organization_to_issue(
            organization_we_vote_id, issue_id, issue_we_vote_id, reason_for_link)
    else:
        link_result = link_manager.unlink_organization_to_issue(
            organization_we_vote_id, issue_id, issue_we_vote_id, reason_for_unlink)

    link_issue_on_stage = {}
    organization_linked_to_issue = False
    if link_result['success']:
        link_issue_from_result = link_result['link_issue']
        link_issue_on_stage = {
            'organization_we_vote_id': link_issue_from_result.organization_we_vote_id,
            'issue_id': link_issue_from_result.issue_id,
            'issue_we_vote_id': link_issue_from_result.issue_we_vote_id,
            'link_active': link_issue_from_result.link_active,
            'reason_for_link': link_issue_from_result.reason_for_link,
            'link_blocked': link_issue_from_result.link_blocked,
            'reason_link_is_blocked': link_issue_from_result.reason_link_is_blocked
        }
        organization_linked_to_issue = link_issue_from_result.link_active
    link_result['organization_linked_to_issue'] = organization_linked_to_issue
    link_result['link_issue'] = link_issue_on_stage
    return HttpResponse(json.dumps(link_result), content_type='application/json')
