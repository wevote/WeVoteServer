# apis_v1/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from exception.models import handle_exception
from follow.models import FOLLOW_IGNORE, FOLLOWING, STOP_FOLLOWING
import json
from organization.models import Organization, OrganizationManager
from organization.controllers import organization_follow_or_unfollow_or_ignore
from voter.models import fetch_voter_id_from_voter_device_link, Voter, VoterManager, VoterMetricsManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def organization_count():
    organization_count_all = 0
    try:
        organization_list_all = Organization.objects.all()
        organization_count_all = organization_list_all.count()
        success = True

        # We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
        # a bottle neck as we grow)
    except Exception as e:
        exception_message = "organizationCount: Unable to count list of Organizations from db."
        handle_exception(e, logger=logger, exception_message=exception_message)
        success = False

    json_data = {
        'success': success,
        'organization_count': organization_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_follow(voter_device_id, organization_id=0, organization_we_vote_id='',  # organizationFollow
                        organization_twitter_handle='', organization_follow_based_on_issue=None,
                        user_agent_string='', user_agent_object=None):
    """
    Save that the voter wants to follow this org
    :param voter_device_id: 
    :param organization_id: 
    :param organization_we_vote_id:
    :param organization_twitter_handle;
    :param organization_follow_based_on_issue:
    :param user_agent_string:
    :param user_agent_object:
    :return: 
    """
    if positive_value_exists(organization_twitter_handle):
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_twitter_handle(
            organization_twitter_handle)
        if organization_results['organization_found']:
            organization_we_vote_id = organization_results['organization'].we_vote_id

    results = organization_follow_or_unfollow_or_ignore(
        voter_device_id, organization_id, organization_we_vote_id, follow_kind=FOLLOWING,
        organization_follow_based_on_issue=organization_follow_based_on_issue, user_agent_string=user_agent_string,
        user_agent_object=user_agent_object)

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': results['voter_device_id'],
        'organization_id': results['organization_id'],
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'voter_linked_organization_we_vote_id': results['voter_linked_organization_we_vote_id'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


# TODO Update organization_stop_following to match organization_follow (and include "organization_twitter_handle")
def organization_stop_following(voter_device_id, organization_id=0, organization_we_vote_id='',
                                user_agent_string='', user_agent_object=None):
    """
    Save that the voter wants to stop following this org, organizationStopFollowing
    :param voter_device_id:
    :param organization_id:
    :param organization_we_vote_id
    :param user_agent_string:
    :param user_agent_object:
    :return:
    """
    json_data = organization_follow_or_unfollow_or_ignore(voter_device_id, organization_id, organization_we_vote_id,
                                                          follow_kind=STOP_FOLLOWING,
                                                          user_agent_string=user_agent_string,
                                                          user_agent_object=user_agent_object)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_follow_ignore(voter_device_id, organization_id=0, organization_we_vote_id='',
                               user_agent_string='', user_agent_object=None):
    """
    Save that the voter wants to ignore this org, organizationFollowIgnore
    :param voter_device_id:
    :param organization_id:
    :param organization_we_vote_id
    :param user_agent_string:
    :param user_agent_object:
    :return:
    """
    json_data = organization_follow_or_unfollow_or_ignore(voter_device_id, organization_id, organization_we_vote_id,
                                                          follow_kind=FOLLOW_IGNORE,
                                                          user_agent_string=user_agent_string,
                                                          user_agent_object=user_agent_object)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_count():
    voter_metrics_manager = VoterMetricsManager()
    voter_count_all = voter_metrics_manager.fetch_voter_count()
    success = True

    json_data = {
        'success': success,
        'voter_count': voter_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_retrieve_list_for_api(voter_device_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results2 = {
            'success': False,
            'json_data': results['json_data'],
        }
        return results2

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id > 0:
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter_id = results['voter_id']
    else:
        # If we are here, the voter_id could not be found from the voter_device_id
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        results = {
            'success': False,
            'json_data': json_data,
        }
        return results

    if voter_id:
        voter_list = Voter.objects.all()
        voter_list = voter_list.filter(id=voter_id)

        if len(voter_list):
            results = {
                'success': True,
                'voter_list': voter_list,
            }
            return results

    # Trying to mimic the Google Civic error codes scheme
    errors_list = [
        {
            'domain':  "TODO global",
            'reason':  "TODO reason",
            'message':  "TODO Error message here",
            'locationType':  "TODO Error message here",
            'location':  "TODO location",
        }
    ]
    error_package = {
        'errors':   errors_list,
        'code':     400,
        'message':  "Error message here",
    }
    json_data = {
        'error': error_package,
        'status': "VOTER_ID_COULD_NOT_BE_RETRIEVED",
        'success': False,
        'voter_device_id': voter_device_id,
    }
    results = {
        'success': False,
        'json_data': json_data,
    }
    return results
