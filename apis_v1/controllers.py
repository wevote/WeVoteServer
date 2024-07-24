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
        direct_api_call=False,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter=None,
        voter_device_id=None,
        voter_id=0):
    """
    Save that the voter dislikes this org. Used by HeartFavoriteToggle.
    :param direct_api_call:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter:
    :param voter_device_id:
    :param voter_id:
    :return:
    """
    status = ""
    results = organization_follow_or_unfollow_or_ignore(
        follow_kind=FOLLOW_DISLIKE,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object,
        voter=voter,
        voter_device_id=voter_device_id,
        voter_id=voter_id,
    )
    status += results['status']
    voter = results['voter']
    voter_id = results['voter_id']
    # When we dislike an organization, also create an Oppose position IFF a position doesn't already exist.
    # It is possible to choose a candidate and at the same time Dislike them.
    # This organization_we_vote_id may be linked to a Politician.
    # This organization may also be linked to a Candidate in an upcoming election
    # Does a position exist for this politician_we_vote_id

    # if kind_of_ballot_item == CANDIDATE:
    #     candidate_id = ballot_item_id
    #     candidate_we_vote_id = ballot_item_we_vote_id
    # elif kind_of_ballot_item == MEASURE:
    #     measure_id = ballot_item_id
    #     measure_we_vote_id = ballot_item_we_vote_id
    # elif kind_of_ballot_item == POLITICIAN:
    #     politician_id = ballot_item_id
    #     politician_we_vote_id = ballot_item_we_vote_id
    save_oppose_position = False
    if positive_value_exists(direct_api_call):
        if positive_value_exists(politician_we_vote_id):
            save_oppose_position = True
    if save_oppose_position:
        from support_oppose_deciding.controllers import voter_opposing_save
        position_results = voter_opposing_save(
            # candidate_id=candidate_id,
            # candidate_we_vote_id=candidate_we_vote_id,
            direct_api_call=False,
            # measure_id=measure_id,
            # measure_we_vote_id=measure_we_vote_id,
            # politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id,
            user_agent_string=user_agent_string,
            user_agent_object=user_agent_object,
            voter=voter,
            voter_device_id=voter_device_id,
            voter_id=voter_id,
        )
        status += position_results['status']
        voter = position_results['voter']
        voter_id = position_results['voter_id']
    final_results_dict = {
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'organization_id': results['organization_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_we_vote_id_that_is_following': results['organization_we_vote_id_that_is_following'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': status,
        'success': results['success'],
        'voter': voter,
        'voter_device_id': voter_device_id,
        'voter_id': voter_id,
        'voter_linked_organization_we_vote_id': results['organization_we_vote_id_that_is_following'],  # Backward compat
    }
    return final_results_dict


def organization_stop_disliking(  # organizationStopDisliking
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter=None,
        voter_device_id=None,
        voter_id=0):
    """
    Save that the voter wants to stop disliking this org, organizationStopDisliking
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter:
    :param voter_id:
    :param voter_device_id:
    :return:
    """
    status = ""
    results = organization_follow_or_unfollow_or_ignore(
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        follow_kind=STOP_DISLIKING,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object,
        voter=voter,
        voter_device_id=voter_device_id,
        voter_id=voter_id,
    )
    status += results['status']
    voter = results['voter']
    voter_id = results['voter_id']
    final_results_dict = {
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'organization_id': results['organization_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_we_vote_id_that_is_following': results['organization_we_vote_id_that_is_following'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': status,
        'success': results['success'],
        'voter': voter,
        'voter_device_id': voter_device_id,
        'voter_id': voter_id,
        'voter_linked_organization_we_vote_id': results['organization_we_vote_id_that_is_following'],  # Backward compat
    }
    return final_results_dict


def organization_follow(  # organizationFollow
        direct_api_call=False,
        organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter=None,
        voter_device_id=None,
        voter_id=0):
    """
    Save that the voter wants to follow this org. Used by HeartFavoriteToggle.
    :param direct_api_call:
    :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter:
    :param voter_device_id:
    :param voter_id:
    :return:
    """
    status = ""
    results = organization_follow_or_unfollow_or_ignore(
        follow_kind=FOLLOWING,
        organization_follow_based_on_issue=organization_follow_based_on_issue,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object,
        voter=voter,
        voter_device_id=voter_device_id,
        voter_id=voter_id,
    )
    status += results['status']
    voter = results['voter']
    voter_id = results['voter_id']
    # When we dislike an organization, also create an Oppose position IFF a position doesn't already exist.
    # It is possible to choose a candidate and at the same time Dislike them.
    # This organization_we_vote_id may be linked to a Politician.
    # This organization may also be linked to a Candidate in an upcoming election
    # Does a position exist for this politician_we_vote_id

    save_support_position = False
    if positive_value_exists(direct_api_call):
        if positive_value_exists(politician_we_vote_id):
            save_support_position = True
    if save_support_position:
        from support_oppose_deciding.controllers import voter_supporting_save
        position_results = voter_supporting_save(
            # candidate_id=candidate_id,
            # candidate_we_vote_id=candidate_we_vote_id,
            direct_api_call=False,
            # measure_id=measure_id,
            # measure_we_vote_id=measure_we_vote_id,
            # politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id,
            user_agent_string=user_agent_string,
            user_agent_object=user_agent_object,
            voter=voter,
            voter_device_id=voter_device_id,
            voter_id=voter_id,
        )
        status += position_results['status']
        voter = position_results['voter']
        voter_id = position_results['voter_id']
    final_results_dict = {
        'organization_id': results['organization_id'],
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': status,
        'success': results['success'],
        'voter': voter,
        'voter_device_id': voter_device_id,
        'voter_id': voter_id,
        'organization_we_vote_id_that_is_following': results['organization_we_vote_id_that_is_following'],
        'voter_linked_organization_we_vote_id': results['organization_we_vote_id_that_is_following'],  # Backward compat
    }
    return final_results_dict


def organization_stop_following(  # organizationStopFollowing
        organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter=None,
        voter_device_id=None,
        voter_id=0):
    """
    Save that the voter wants to stop following this org, organizationStopFollowing
    :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter:
    :param voter_device_id:
    :param voter_id:
    :return:
    """
    status = ''
    results = organization_follow_or_unfollow_or_ignore(
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        follow_kind=STOP_FOLLOWING,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object,
        voter=voter,
        voter_device_id=voter_device_id,
        voter_id=voter_id,
    )
    status += results['status']
    voter = results['voter']
    voter_id = results['voter_id']
    final_results_dict = {
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'organization_id': results['organization_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_we_vote_id_that_is_following': results['organization_we_vote_id_that_is_following'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': status,
        'success': results['success'],
        'voter': voter,
        'voter_device_id': voter_device_id,
        'voter_id': voter_id,
        'voter_linked_organization_we_vote_id': results['organization_we_vote_id_that_is_following'],  # Backward compat
    }
    return final_results_dict


def organization_stop_ignoring(
        # organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter=None,
        voter_device_id=None,
        voter_id=0):
    """
    Save that the voter wants to stop following this org, organizationStopIgnoring
    # :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter:
    :param voter_device_id:
    :param voter_id:
    :return:
    """
    status = ""
    results = organization_follow_or_unfollow_or_ignore(
        follow_kind=STOP_IGNORING,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_object=user_agent_object,
        user_agent_string=user_agent_string,
        voter=voter,
        voter_device_id=voter_device_id,
        voter_id=voter_id)
    status += results['status']
    voter = results['voter']
    voter_id = results['voter_id']
    final_results_dict = {
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'organization_id': results['organization_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_we_vote_id_that_is_following': results['organization_we_vote_id_that_is_following'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': status,
        'success': results['success'],
        'voter': voter,
        'voter_device_id': voter_device_id,
        'voter_id': voter_id,
        'voter_linked_organization_we_vote_id': results['organization_we_vote_id_that_is_following'],  # Backward compat
    }
    return final_results_dict


def organization_follow_ignore(  # organizationFollowIgnore
        organization_follow_based_on_issue=None,
        organization_id=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        user_agent_object=None,
        user_agent_string=None,
        voter=None,
        voter_device_id=None,
        voter_id=0):
    """
    Save that the voter wants to ignore this org, organizationFollowIgnore
    :param organization_follow_based_on_issue:
    :param organization_id:
    :param organization_twitter_handle;
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param user_agent_object:
    :param user_agent_string:
    :param voter:
    :param voter_device_id:
    :param voter_id:
    :return:
    """
    status = ''
    results = organization_follow_or_unfollow_or_ignore(
        follow_kind=FOLLOW_IGNORE,
        organization_id=organization_id,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        user_agent_object=user_agent_object,
        user_agent_string=user_agent_string,
        voter=voter,
        voter_device_id=voter_device_id,
        voter_id=voter_id)
    status += results['status']
    final_results_dict = {
        'organization_follow_based_on_issue': results['organization_follow_based_on_issue'],
        'organization_id': results['organization_id'],
        'organization_twitter_handle': organization_twitter_handle,
        'organization_we_vote_id': results['organization_we_vote_id'],
        'organization_we_vote_id_that_is_following': results['organization_we_vote_id_that_is_following'],
        'politician_we_vote_id': results['politician_we_vote_id'],
        'status': status,
        'success': results['success'],
        'voter': voter,
        'voter_device_id': voter_device_id,
        'voter_id': voter_id,
        'voter_linked_organization_we_vote_id': results['organization_we_vote_id_that_is_following'],  # Backward compat
    }
    return final_results_dict


def voter_count():  # voterCountView
    voter_metrics_manager = VoterMetricsManager()
    voter_count_all = voter_metrics_manager.fetch_voter_count()
    success = True

    json_data = {
        'success': success,
        'voter_count': voter_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
