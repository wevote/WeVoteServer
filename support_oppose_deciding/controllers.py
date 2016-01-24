# support_oppose_deciding/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from follow.models import FollowOrganizationList
import json
from position.models import SUPPORT, OPPOSE, \
    PositionEnteredManager, PositionListManager
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def position_oppose_count_for_ballot_item_for_api(voter_device_id, candidate_id, measure_id):

    stance_we_are_looking_for = OPPOSE
    return positions_count_for_api(voter_device_id, candidate_id, measure_id, stance_we_are_looking_for)


def positions_count_for_api(voter_device_id, candidate_id, measure_id, stance_we_are_looking_for):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    show_positions_this_voter_follows = True
    if positive_value_exists(candidate_id):
        results = positions_count_for_candidate_campaign(voter_id, candidate_id, stance_we_are_looking_for,
                                                         show_positions_this_voter_follows)
        json_data = results['json_data']
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id):
        results = positions_count_for_contest_measure(voter_id, measure_id, stance_we_are_looking_for,
                                                      show_positions_this_voter_follows)
        json_data = results['json_data']
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_RETRIEVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_count_for_candidate_campaign(voter_id, candidate_id, stance_we_are_looking_for,
                                           show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the number of orgs, friends and public figures the voter follows who support
    this particular candidate's campaign
    """
    # This implementation is built to make only two database calls. All other calculations are done here in the
    #  application layer

    position_list_manager = PositionListManager()
    candidate_we_vote_id = ''
    all_positions_list_for_candidate_campaign = \
        position_list_manager.retrieve_all_positions_for_candidate_campaign(
            candidate_id, candidate_we_vote_id, stance_we_are_looking_for)

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    if show_positions_this_voter_follows:
        positions_followed = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, all_positions_list_for_candidate_campaign, organizations_followed_by_voter)
        positions_followed_count = len(positions_followed)
        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_FOLLOWED_RE_CANDIDATE',
            'success': True,
            'count': positions_followed_count,
        }
        results = {
            'json_data': json_data,
        }
        return results
    else:
        positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
            all_positions_list_for_candidate_campaign, organizations_followed_by_voter)
        positions_not_followed_count = len(positions_not_followed)
        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED_CC',
            'success': True,
            'count': positions_not_followed_count,
        }
        results = {
            'json_data': json_data,
        }
        return results


def positions_count_for_contest_measure(voter_id, measure_id, stance_we_are_looking_for,
                                        show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the number of orgs, friends and public figures the voter follows who support
    this particular measure
    """
    # This implementation is built to make only two database calls. All other calculations are done here in the
    #  application layer

    position_list_manager = PositionListManager()
    measure_we_vote_id = ''
    all_positions_list_for_contest_measure = \
        position_list_manager.retrieve_all_positions_for_contest_measure(
            measure_id, measure_we_vote_id, stance_we_are_looking_for)

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    if show_positions_this_voter_follows:
        positions_followed = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, all_positions_list_for_contest_measure, organizations_followed_by_voter)
        positions_followed_count = len(positions_followed)
        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITION_COUNT_FOR_CONTEST_MEASURE',
            'success': True,
            'count': positions_followed_count,
        }
        results = {
            'json_data': json_data,
        }
        return results
    else:
        positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
            all_positions_list_for_contest_measure, organizations_followed_by_voter)
        positions_not_followed_count = len(positions_not_followed)
        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED_COUNT_FOR_CONTEST_MEASURE',
            'success': True,
            'count': positions_not_followed_count,
        }
        results = {
            'json_data': json_data,
        }
        return results


def position_support_count_for_ballot_item_for_api(voter_device_id, candidate_id, measure_id):
    stance_we_are_looking_for = SUPPORT
    return positions_count_for_api(voter_device_id, candidate_id, measure_id, stance_we_are_looking_for)


def voter_opposing_save(voter_device_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_entered_manager = PositionEnteredManager()
    if positive_value_exists(candidate_id):
        results = position_entered_manager.toggle_on_voter_oppose_for_candidate_campaign(voter_id, candidate_id)
        # toggle_off_voter_support_for_candidate_campaign
        status = "OPPOSING_CANDIDATE " + results['status']
        success = results['success']
    elif positive_value_exists(measure_id):
        results = position_entered_manager.toggle_on_voter_oppose_for_contest_measure(voter_id, measure_id)
        status = "OPPOSING_MEASURE " + results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_opposing_save(voter_device_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_entered_manager = PositionEnteredManager()
    if positive_value_exists(candidate_id):
        results = position_entered_manager.toggle_off_voter_oppose_for_candidate_campaign(voter_id, candidate_id)
        status = "STOP_OPPOSING_CANDIDATE " + results['status']
        success = results['success']
    elif positive_value_exists(measure_id):
        results = position_entered_manager.toggle_off_voter_oppose_for_contest_measure(voter_id, measure_id)
        status = "STOP_OPPOSING_MEASURE" + results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_supporting_save(voter_device_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_entered_manager = PositionEnteredManager()
    if positive_value_exists(candidate_id):
        results = position_entered_manager.toggle_off_voter_support_for_candidate_campaign(voter_id, candidate_id)
        status = "STOP_SUPPORTING_CANDIDATE " + results['status']
        success = results['success']
    elif positive_value_exists(measure_id):
        results = position_entered_manager.toggle_off_voter_support_for_contest_measure(voter_id, measure_id)
        status = "STOP_SUPPORTING_MEASURE" + results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_supporting_save_for_api(voter_device_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_entered_manager = PositionEnteredManager()
    if positive_value_exists(candidate_id):
        results = position_entered_manager.toggle_on_voter_support_for_candidate_campaign(voter_id, candidate_id)
        status = "SUPPORTING_CANDIDATE " + results['status']
        success = results['success']
    elif positive_value_exists(measure_id):
        results = position_entered_manager.toggle_on_voter_support_for_contest_measure(voter_id, measure_id)
        status = "SUPPORTING_MEASURE " + results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
