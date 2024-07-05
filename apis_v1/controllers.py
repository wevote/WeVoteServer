# apis_v1/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from exception.models import handle_exception
from follow.models import FOLLOW_DISLIKE, FOLLOW_IGNORE, FOLLOWING, STOP_DISLIKING, STOP_FOLLOWING, STOP_IGNORING
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
        organization_list_all = Organization.objects.using('readonly').all()
        organization_count_all = organization_list_all.count()
        success = True

        # We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
        # a bottle neck as we grow)
    except Exception as e:
        exception_message = "organizationCount: Unable to count list of endorsers from db."
        handle_exception(e, logger=logger, exception_message=exception_message)
        success = False

    json_data = {
        'success': success,
        'organization_count': organization_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_dislike(  # organizationDislike
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter_device_id=None):
    """
    Save that the voter dislikes this org. Used by HeartFavoriteToggle.
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter_device_id:
    :return:
    """

    results = organization_follow_or_unfollow_or_ignore(
        follow_kind=FOLLOW_DISLIKE,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object,
        voter_device_id=voter_device_id,
    )
    json_data = {
        'organization_id': results['organization_id'],
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': results['voter_device_id'],
        'voter_linked_organization_we_vote_id': results['voter_linked_organization_we_vote_id'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_stop_disliking(  # organizationStopDisliking
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter_device_id=None):
    """
    Save that the voter wants to stop disliking this org, organizationStopDisliking
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter_device_id:
    :return:
    """
    results = organization_follow_or_unfollow_or_ignore(
        voter_device_id=voter_device_id,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        follow_kind=STOP_DISLIKING,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object)
    json_data = {
        'organization_id': results['organization_id'],
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': results['voter_device_id'],
        'voter_linked_organization_we_vote_id': results['voter_linked_organization_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_follow(  # organizationFollow
        organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter_device_id=None):
    """
    Save that the voter wants to follow this org. Used by HeartFavoriteToggle.
    :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter_device_id:
    :return:
    """

    results = organization_follow_or_unfollow_or_ignore(
        follow_kind=FOLLOWING,
        organization_follow_based_on_issue=organization_follow_based_on_issue,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object,
        voter_device_id=voter_device_id,
    )
    json_data = {
        'organization_id': results['organization_id'],
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': results['voter_device_id'],
        'voter_linked_organization_we_vote_id': results['voter_linked_organization_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_stop_following(  # organizationStopFollowing
        organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter_device_id=None):
    """
    Save that the voter wants to stop following this org, organizationStopFollowing
    :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter_device_id:
    :return:
    """
    results = organization_follow_or_unfollow_or_ignore(
        voter_device_id=voter_device_id,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        follow_kind=STOP_FOLLOWING,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object)
    json_data = {
        'organization_id': results['organization_id'],
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': results['voter_device_id'],
        'voter_linked_organization_we_vote_id': results['voter_linked_organization_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_stop_ignoring(
        # organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter_device_id=None):
    """
    Save that the voter wants to stop following this org, organizationStopIgnoring
    # :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter_device_id:
    :return:
    """
    json_data = organization_follow_or_unfollow_or_ignore(
        follow_kind=STOP_IGNORING,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_object=user_agent_object,
        user_agent_string=user_agent_string,
        voter_device_id=voter_device_id)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_follow_ignore(  # organizationFollowIgnore
        organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter_device_id=None):
    """
    Save that the voter wants to ignore this org, organizationFollowIgnore
    :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter_device_id:
    :return:
    """
    json_data = organization_follow_or_unfollow_or_ignore(
        follow_kind=FOLLOW_IGNORE,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_object=user_agent_object,
        user_agent_string=user_agent_string,
        voter_device_id=voter_device_id)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_count():  # voterCountView
    voter_metrics_manager = VoterMetricsManager()
    voter_count_all = voter_metrics_manager.fetch_voter_count()
    success = True

    json_data = {
        'success': success,
        'voter_count': voter_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
