# support_oppose_deciding/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching
from ballot.models import CANDIDATE, MEASURE, OFFICE, BallotItemListManager
from candidate.models import CandidateManager, CandidateListManager
from friend.models import FriendManager
from measure.models import ContestMeasureManager
from django.http import HttpResponse
from follow.models import FollowOrganizationList
import json
from position.models import ANY_STANCE, FRIENDS_ONLY, SUPPORT, OPPOSE, PositionManager, PositionListManager, PUBLIC_ONLY
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def position_oppose_count_for_ballot_item_for_api(voter_device_id,
                                                  candidate_id, candidate_we_vote_id,
                                                  measure_id, measure_we_vote_id):

    stance_we_are_looking_for = OPPOSE
    return positions_count_for_api(voter_device_id,
                                   candidate_id, candidate_we_vote_id,
                                   measure_id, measure_we_vote_id, stance_we_are_looking_for)


def positions_count_for_api(voter_device_id,
                            candidate_id, candidate_we_vote_id,
                            measure_id, measure_we_vote_id,
                            stance_we_are_looking_for):
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
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        results = positions_count_for_candidate(voter_id,
                                                candidate_id, candidate_we_vote_id,
                                                stance_we_are_looking_for,
                                                show_positions_this_voter_follows)
        json_data = results['json_data']
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        results = positions_count_for_contest_measure(voter_id,
                                                      measure_id, measure_we_vote_id,
                                                      stance_we_are_looking_for,
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


def positions_count_for_candidate(voter_id, candidate_id, candidate_we_vote_id, stance_we_are_looking_for,
                                  show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the number of orgs, friends and public figures the voter follows who support
    this particular candidate's campaign
    """
    # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the candidate object
    # so we make sure we have both of these values to return
    if positive_value_exists(candidate_id):
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate_from_id(candidate_id)
        if results['candidate_found']:
            candidate = results['candidate']
            candidate_we_vote_id = candidate.we_vote_id
    elif positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id)
        if results['candidate_found']:
            candidate = results['candidate']
            candidate_id = candidate.id

    position_list_manager = PositionListManager()
    ############################
    # Retrieve public positions
    retrieve_public_positions_now = True  # The alternate is positions for friends-only
    most_recent_only = True
    public_positions_list_for_candidate = \
        position_list_manager.retrieve_all_positions_for_candidate(
            retrieve_public_positions_now, candidate_id, candidate_we_vote_id,
            stance_we_are_looking_for, most_recent_only
        )

    organizations_followed_by_voter_by_id = []
    if len(public_positions_list_for_candidate):
        follow_organization_list_manager = FollowOrganizationList()
        organizations_followed_by_voter_by_id = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    if show_positions_this_voter_follows:
        position_objects = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, public_positions_list_for_candidate, organizations_followed_by_voter_by_id)

        ##################################
        # Now retrieve friend's positions
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_by_id(voter_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_we_vote_id = voter.we_vote_id
        else:
            voter_we_vote_id = ""

        friends_we_vote_id_list = []
        if positive_value_exists(voter_we_vote_id):
            retrieve_public_positions_now = False  # Retrieve positions intended for friends-only
            most_recent_only = False
            friend_manager = FriendManager()
            friend_results = friend_manager.retrieve_friends_we_vote_id_list(voter_we_vote_id)
            if friend_results['friends_we_vote_id_list_found']:
                friends_we_vote_id_list = friend_results['friends_we_vote_id_list']

        # Add yourself as a friend so your opinions show up
        friends_we_vote_id_list.append(voter_we_vote_id)
        friends_positions_list_for_candidate = \
            position_list_manager.retrieve_all_positions_for_candidate(
                retrieve_public_positions_now, candidate_id, candidate_we_vote_id,
                stance_we_are_looking_for, most_recent_only,
                friends_we_vote_id_list)

        if len(friends_positions_list_for_candidate):
            position_objects = friends_positions_list_for_candidate + position_objects

        positions_followed_count = len(position_objects)

        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_FOLLOWED_COUNT_FOR_CANDIDATE',
            'success': True,
            'count': positions_followed_count,
            'ballot_item_id': convert_to_int(candidate_id),
            'ballot_item_we_vote_id': candidate_we_vote_id,
            'kind_of_ballot_item': CANDIDATE,
        }
        results = {
            'json_data': json_data,
        }
        return results
    else:
        positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
            public_positions_list_for_candidate, organizations_followed_by_voter_by_id)
        positions_not_followed_count = len(positions_not_followed)
        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED_COUNT_FOR_CANDIDATE',
            'success': True,
            'count': positions_not_followed_count,
            'ballot_item_id': convert_to_int(candidate_id),
            'ballot_item_we_vote_id': candidate_we_vote_id,
            'kind_of_ballot_item': CANDIDATE,
        }
        results = {
            'json_data': json_data,
        }
        return results


def positions_count_for_contest_measure(voter_id, measure_id, measure_we_vote_id, stance_we_are_looking_for,
                                        show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the number of orgs, friends and public figures the voter follows who support
    this particular measure
    """
    # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the measure object
    # so we make sure we have both of these values to return
    if positive_value_exists(measure_id):
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure_from_id(measure_id)
        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            measure_we_vote_id = contest_measure.we_vote_id
    elif positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            measure_id = contest_measure.id

    position_list_manager = PositionListManager()
    ############################
    # Retrieve public positions
    retrieve_public_positions_now = True  # The alternate is positions for friends-only
    most_recent_only = True
    public_positions_list_for_contest_measure = \
        position_list_manager.retrieve_all_positions_for_contest_measure(
            retrieve_public_positions_now, measure_id, measure_we_vote_id,
            stance_we_are_looking_for, most_recent_only)

    organizations_followed_by_voter_by_id = []
    if len(public_positions_list_for_contest_measure):
        follow_organization_list_manager = FollowOrganizationList()
        organizations_followed_by_voter_by_id = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    if show_positions_this_voter_follows:
        position_objects = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, public_positions_list_for_contest_measure, organizations_followed_by_voter_by_id)

        ##################################
        # Now retrieve friend's positions
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_by_id(voter_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_we_vote_id = voter.we_vote_id
        else:
            voter_we_vote_id = ""

        friends_we_vote_id_list = []
        if positive_value_exists(voter_we_vote_id):
            retrieve_public_positions_now = False  # Retrieve positions intended for friends-only
            most_recent_only = False
            friend_manager = FriendManager()
            friend_results = friend_manager.retrieve_friends_we_vote_id_list(voter_we_vote_id)
            if friend_results['friends_we_vote_id_list_found']:
                friends_we_vote_id_list = friend_results['friends_we_vote_id_list']

        # Add yourself as a friend so your opinions show up
        friends_we_vote_id_list.append(voter_we_vote_id)
        friends_positions_list_for_contest_measure = \
            position_list_manager.retrieve_all_positions_for_contest_measure(
                retrieve_public_positions_now, measure_id, measure_we_vote_id,
                stance_we_are_looking_for, most_recent_only,
                friends_we_vote_id_list)

        if len(friends_positions_list_for_contest_measure):
            position_objects = friends_positions_list_for_contest_measure + position_objects

        positions_followed_count = len(position_objects)

        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITION_COUNT_FOR_CONTEST_MEASURE',
            'success': True,
            'count': positions_followed_count,
            'ballot_item_id': convert_to_int(measure_id),
            'ballot_item_we_vote_id': measure_we_vote_id,
            'kind_of_ballot_item': MEASURE,
        }
        results = {
            'json_data': json_data,
        }
        return results
    else:
        positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
            public_positions_list_for_contest_measure, organizations_followed_by_voter_by_id)
        positions_not_followed_count = len(positions_not_followed)
        json_data = {
            'status': 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED_COUNT_FOR_CONTEST_MEASURE',
            'success': True,
            'count': positions_not_followed_count,
            'ballot_item_id': convert_to_int(measure_id),
            'ballot_item_we_vote_id': measure_we_vote_id,
            'kind_of_ballot_item': MEASURE,
        }
        results = {
            'json_data': json_data,
        }
        return results


def position_support_count_for_ballot_item_for_api(voter_device_id,
                                                   candidate_id, candidate_we_vote_id,
                                                   measure_id, measure_we_vote_id):
    stance_we_are_looking_for = SUPPORT
    return positions_count_for_api(voter_device_id,
                                   candidate_id, candidate_we_vote_id,
                                   measure_id, measure_we_vote_id, stance_we_are_looking_for)


def position_public_oppose_count_for_ballot_item_for_api(candidate_id, candidate_we_vote_id,
                                                         measure_id, measure_we_vote_id):
    stance_we_are_looking_for = OPPOSE
    return positions_public_count_for_api(candidate_id, candidate_we_vote_id,
                                          measure_id, measure_we_vote_id, stance_we_are_looking_for)


def position_public_support_count_for_ballot_item_for_api(candidate_id, candidate_we_vote_id,
                                                          measure_id, measure_we_vote_id):
    stance_we_are_looking_for = SUPPORT
    return positions_public_count_for_api(candidate_id, candidate_we_vote_id,
                                          measure_id, measure_we_vote_id, stance_we_are_looking_for)


def finalize_support_and_oppose_positions_count(voter_id, show_positions_this_voter_follows,
                                                organizations_followed_by_voter_by_id, friends_we_vote_id_list,
                                                support_positions_list_for_one_ballot_item,
                                                oppose_positions_list_for_one_ballot_item):
    oppose_positions_followed = []
    position_list_manager = PositionListManager()
    support_positions_followed = []
    if show_positions_this_voter_follows:
        support_positions_followed = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, support_positions_list_for_one_ballot_item, organizations_followed_by_voter_by_id,
            friends_we_vote_id_list)
        support_positions_count = len(support_positions_followed)

        oppose_positions_followed = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, oppose_positions_list_for_one_ballot_item, organizations_followed_by_voter_by_id,
            friends_we_vote_id_list)
        oppose_positions_count = len(oppose_positions_followed)

    else:
        support_positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
            support_positions_list_for_one_ballot_item, organizations_followed_by_voter_by_id,
            friends_we_vote_id_list)
        support_positions_count = len(support_positions_not_followed)

        oppose_positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
            oppose_positions_list_for_one_ballot_item, organizations_followed_by_voter_by_id,
            friends_we_vote_id_list)
        oppose_positions_count = len(oppose_positions_not_followed)

    results = {
        'support_positions_count':      support_positions_count,
        'support_positions_followed':   support_positions_followed,
        'oppose_positions_count':       oppose_positions_count,
        'oppose_positions_followed':    oppose_positions_followed,
    }
    return results


def positions_public_count_for_api(candidate_id, candidate_we_vote_id, measure_id, measure_we_vote_id,
                                   stance_we_are_looking_for):
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        results = positions_public_count_for_candidate(candidate_id, candidate_we_vote_id,
                                                       stance_we_are_looking_for)
        json_data = results['json_data']
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        results = positions_public_count_for_contest_measure(measure_id, measure_we_vote_id,
                                                             stance_we_are_looking_for)
        json_data = results['json_data']
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        pass

    json_data = {
        'status': 'UNABLE_TO_RETRIEVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING',
        'success': False,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_public_count_for_candidate(candidate_id, candidate_we_vote_id, stance_we_are_looking_for):
    """
    We want to return a JSON file with the number of orgs and public figures who support
    this particular candidate's campaign
    """
    # This implementation is built to make only two database calls. All other calculations are done here in the
    #  application layer

    position_list_manager = PositionListManager()
    all_positions_count_for_candidate = \
        position_list_manager.fetch_public_positions_count_for_candidate(
            candidate_id,
            candidate_we_vote_id,
            stance_we_are_looking_for)

    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

    json_data = {
        'status':                   'SUCCESSFUL_RETRIEVE_OF_PUBLIC_POSITION_COUNT_RE_CANDIDATE',
        'success':                  True,
        'count':                    all_positions_count_for_candidate,
        'ballot_item_id':           convert_to_int(candidate_id),
        'ballot_item_we_vote_id':   candidate_we_vote_id,
        'kind_of_ballot_item':      CANDIDATE,

    }
    results = {
        'json_data': json_data,
    }
    return results


def positions_public_count_for_contest_measure(measure_id, measure_we_vote_id, stance_we_are_looking_for):
    """
    We want to return a JSON file with the number of orgs and public figures who support
    this particular measure
    """
    # This implementation is built to make only two database calls. All other calculations are done here in the
    #  application layer

    position_list_manager = PositionListManager()
    all_positions_count_for_contest_measure = \
        position_list_manager.fetch_public_positions_count_for_contest_measure(
            measure_id, measure_we_vote_id, stance_we_are_looking_for)

    if positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

    json_data = {
        'status':                   'SUCCESSFUL_RETRIEVE_OF_PUBLIC_POSITION_COUNT_FOR_CONTEST_MEASURE',
        'success':                  True,
        'count':                    all_positions_count_for_contest_measure,
        'ballot_item_id':           convert_to_int(measure_id),
        'ballot_item_we_vote_id':   measure_we_vote_id,
        'kind_of_ballot_item':      MEASURE,
    }
    results = {
        'json_data': json_data,
    }
    return results


def voter_opposing_save(voter_device_id, candidate_id, candidate_we_vote_id,  # voterOpposingSave
                        measure_id, measure_we_vote_id, user_agent_string, user_agent_object):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        results = position_manager.toggle_on_voter_oppose_for_candidate(voter_id, candidate_id,
                                                                        user_agent_string, user_agent_object)
        # toggle_off_voter_support_for_candidate
        status = "OPPOSING_CANDIDATE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        results = position_manager.toggle_on_voter_oppose_for_contest_measure(voter_id, measure_id,
                                                                              user_agent_string, user_agent_object)
        status = "OPPOSING_MEASURE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
            'position_we_vote_id': results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status':                   status,
        'success':                  success,
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
        'position_we_vote_id':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_opposing_save(voter_device_id, candidate_id, candidate_we_vote_id,  # voterStopOpposingSave
                             measure_id, measure_we_vote_id, user_agent_string, user_agent_object):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        results = position_manager.toggle_off_voter_oppose_for_candidate(voter_id, candidate_id,
                                                                                  user_agent_string, user_agent_object)
        status = "STOP_OPPOSING_CANDIDATE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        results = position_manager.toggle_off_voter_oppose_for_contest_measure(voter_id, measure_id,
                                                                               user_agent_string, user_agent_object)
        status = "STOP_OPPOSING_MEASURE" + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
        'position_we_vote_id':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_supporting_save(voter_device_id, candidate_id, candidate_we_vote_id,  # voterStopSupportingSave
                               measure_id, measure_we_vote_id, user_agent_string, user_agent_object):
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        results = position_manager.toggle_off_voter_support_for_candidate(voter_id, candidate_id,
                                                                          user_agent_string, user_agent_object)
        status = "STOP_SUPPORTING_CANDIDATE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        results = position_manager.toggle_off_voter_support_for_contest_measure(voter_id, measure_id,
                                                                                user_agent_string, user_agent_object)
        status = "STOP_SUPPORTING_MEASURE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
        'position_we_vote_id':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_supporting_save_for_api(voter_device_id,  # voterSupportingSave
                                  candidate_id, candidate_we_vote_id,
                                  measure_id, measure_we_vote_id, user_agent_string, user_agent_object):
    """
    Default to this being a private position
    :param voter_device_id:
    :param candidate_id:
    :param candidate_we_vote_id:
    :param measure_id:
    :param measure_we_vote_id:
    :param user_agent_string:
    :param user_agent_object:
    :return:
    """
    status = ""
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING ',
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'position_we_vote_id':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        results = position_manager.toggle_on_voter_support_for_candidate(voter_id, candidate_id,
                                                                         user_agent_string, user_agent_object)
        status += "SUPPORTING_CANDIDATE " + results['status'] + " "
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        results = position_manager.toggle_on_voter_support_for_contest_measure(
            voter_id, measure_id, user_agent_string, user_agent_object)
        status += "SUPPORTING_MEASURE: " + results['status'] + " "
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
            'position_we_vote_id':      results['position_we_vote_id'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status += 'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING '
        success = False

    json_data = {
        'status': status,
        'success': success,
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
        'position_we_vote_id':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
