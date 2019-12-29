# position/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered, PositionForFriends, PositionManager, PositionListManager, ANY_STANCE, \
    FRIENDS_AND_PUBLIC, FRIENDS_ONLY, PUBLIC_ONLY, SHOW_PUBLIC, THIS_ELECTION_ONLY, ALL_OTHER_ELECTIONS, \
    ALL_ELECTIONS, SUPPORT, OPPOSE, INFORMATION_ONLY, NO_STANCE
from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching, \
    figure_out_google_civic_election_id_voter_is_watching_by_voter_id
from ballot.models import BallotItemListManager, OFFICE, CANDIDATE, MEASURE
from candidate.models import CandidateCampaignManager, CandidateCampaignListManager
from config.base import get_environment_variable
from django.db.models import Q
from django.http import HttpResponse
from election.models import fetch_election_state
from exception.models import handle_record_not_saved_exception
from follow.models import FollowOrganizationManager, FollowOrganizationList
from friend.models import FriendManager
from measure.models import ContestMeasureManager, ContestMeasureList
from office.models import ContestOfficeManager, ContestOfficeListManager
from operator import itemgetter
from organization.models import Organization, OrganizationManager, PUBLIC_FIGURE, UNKNOWN
import json
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
from voter_guide.models import ORGANIZATION, VOTER, VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists, process_request_from_master, \
    convert_to_int, is_link_to_video, is_speaker_type_organization, is_speaker_type_public_figure

logger = wevote_functions.admin.get_logger(__name__)

UNKNOWN = 'U'
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POSITIONS_SYNC_URL = get_environment_variable("POSITIONS_SYNC_URL")  # positionsSyncOut


def add_position_network_count_entries_for_one_organization(voter_id, organization_we_vote_id,
                                                            google_civic_election_id=0):
    """
    This is called when a voter follows an organization.
    :param voter_id:
    :param organization_we_vote_id:
    :param google_civic_election_id:
    :return:
    """
    status = "ADD_POSITION_NETWORK_COUNT_FOR_ONE_ORGANIZATION "
    public_positions_updated = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        status += "VALID_VOTER_ID_MISSING "
        json_data = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'public_positions_updated': public_positions_updated,
        }
        return json_data

    position_manager = PositionManager()
    position_list_manager = PositionListManager()

    if not positive_value_exists(google_civic_election_id):
        # Look up the current google_civic_election_id for this voter
        results = figure_out_google_civic_election_id_voter_is_watching_by_voter_id(voter_id)
        google_civic_election_id = results['google_civic_election_id']

    organization_id = 0
    show_positions_current_voter_election = True
    exclude_positions_current_voter_election = False
    position_results = position_list_manager.retrieve_all_positions_for_organization(
        organization_id, organization_we_vote_id,
        ANY_STANCE, PUBLIC_ONLY,
        show_positions_current_voter_election,
        exclude_positions_current_voter_election,
        google_civic_election_id=google_civic_election_id)

    # ballot_item_list is populated with contest_office and contest_measure entries
    for one_position in position_results:
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            # Add entry to position_network_score table
            ignore_friend_voter_we_vote_id = None
            ignore_measure_we_vote_id = None
            if one_position.is_support_or_positive_rating():
                support_or_oppose = True
            elif one_position.is_oppose_or_negative_rating():
                support_or_oppose = False
            else:
                # If not support or oppose, continue to next position
                continue
            update_results = position_manager.update_or_create_position_network_score(
                voter_id, voter_we_vote_id,
                google_civic_election_id,
                one_position.organization_we_vote_id, ignore_friend_voter_we_vote_id,
                one_position.speaker_display_name,
                one_position.candidate_campaign_we_vote_id, ignore_measure_we_vote_id,
                support_or_oppose)
            if update_results['position_network_score_updated']:
                public_positions_updated = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            # Add entry to position_network_score table
            ignore_friend_voter_we_vote_id = None
            ignore_candidate_we_vote_id = None
            if one_position.is_support_or_positive_rating():
                support_or_oppose = True
            elif one_position.is_oppose_or_negative_rating():
                support_or_oppose = False
            else:
                # If not support or oppose, continue to next position
                continue
            update_results = position_manager.update_or_create_position_network_score(
                voter_id, voter_we_vote_id,
                google_civic_election_id,
                one_position.organization_we_vote_id, ignore_friend_voter_we_vote_id,
                one_position.speaker_display_name,
                ignore_candidate_we_vote_id, one_position.contest_measure_we_vote_id,
                support_or_oppose)
            if update_results['position_network_score_updated']:
                public_positions_updated = True

    json_data = {
        'success':                  True,
        'status':                   status,
        'google_civic_election_id': google_civic_election_id,
        'public_positions_updated': public_positions_updated,
    }
    return json_data


def add_position_network_count_entries_for_one_friend(voter_id, friend_voter_we_vote_id,
                                                      google_civic_election_id=0, voter_we_vote_id=""):
    """
    This is called when a voter adds a friend.
    :param voter_id:
    :param friend_voter_we_vote_id:
    :param google_civic_election_id:
    :param voter_we_vote_id:
    :return:
    """
    status = "ADD_POSITION_NETWORK_COUNT_FOR_ONE_FRIEND "
    friends_only_positions_updated = False
    public_positions_updated = False

    voter_manager = VoterManager()
    if positive_value_exists(voter_id):
        voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    else:
        voter_results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        status += "VALID_VOTER_ID_MISSING "
        json_data = {
            'status':                           status,
            'success':                          False,
            'google_civic_election_id':         google_civic_election_id,
            'friends_only_positions_updated':   friends_only_positions_updated,
            'public_positions_updated':         public_positions_updated,
        }
        return json_data

    if not positive_value_exists(google_civic_election_id):
        # Look up the current google_civic_election_id for this voter
        results = figure_out_google_civic_election_id_voter_is_watching_by_voter_id(voter_id)
        google_civic_election_id = results['google_civic_election_id']

    friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(friend_voter_we_vote_id)
    if friend_voter_results['voter_found']:
        friend_voter = friend_voter_results['voter']
        friend_voter_linked_organization_we_vote_id = friend_voter.linked_organization_we_vote_id
    else:
        friend_voter_linked_organization_we_vote_id = ""

    position_list_manager = PositionListManager()

    # Start with the publicly visible positions from the friend
    if positive_value_exists(friend_voter_linked_organization_we_vote_id):
        organization_id = 0
        show_positions_current_voter_election = True
        exclude_positions_current_voter_election = False
        position_list = position_list_manager.retrieve_all_positions_for_organization(
            organization_id, friend_voter_linked_organization_we_vote_id,
            ANY_STANCE, PUBLIC_ONLY,
            show_positions_current_voter_election,
            exclude_positions_current_voter_election,
            google_civic_election_id=google_civic_election_id)

        for one_position in position_list:
            results = update_or_create_position_network_score_wrapper(voter_id, voter_we_vote_id, one_position)

            if results['public_position_updated']:
                public_positions_updated = True

    # Then find friends-only positions
    if positive_value_exists(friend_voter_linked_organization_we_vote_id):
        friend_voter_id = 0
        position_results = position_list_manager.retrieve_all_positions_for_voter(
            friend_voter_id, friend_voter_we_vote_id,
            ANY_STANCE, FRIENDS_ONLY,
            google_civic_election_id, THIS_ELECTION_ONLY)

        # ballot_item_list is populated with contest_office and contest_measure entries
        if position_results['position_list_found']:
            position_list = position_results['position_list']
            for one_position in position_list:
                results = update_or_create_position_network_score_wrapper(voter_id, voter_we_vote_id, one_position)

                if results['friends_only_position_updated']:
                    friends_only_positions_updated = True

    json_data = {
        'success':                  True,
        'status':                   status,
        'google_civic_election_id': google_civic_election_id,
        'friends_only_positions_updated': friends_only_positions_updated,
        'public_positions_updated': public_positions_updated,
    }
    return json_data


def calculate_positions_count_for_all_ballot_items_for_api(
        voter_device_id, google_civic_election_id=0):
    """
    We want to return a JSON file with the list of the support and oppose counts from the orgs, friends and
    public figures the voter follows, and be caching the results as we look them up.
    This API call refreshes the data, and is not meant to be used when we just want the latest count.
    """
    status = "CALCULATE_POSITIONS_COUNT_FOR_ALL_BALLOT_ITEMS "
    support_or_oppose_exists = False
    # Get voter_id from the voter_device_id so we can know whose bookmarks to retrieve
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':                   "VALID_VOTER_DEVICE_ID_MISSING-CALCULATE_COUNT_FOR_ALL_BALLOT_ITEMS",
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'support_or_oppose_exists': support_or_oppose_exists,
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        status += "VALID_VOTER_ID_MISSING-CALCULATE_COUNT_FOR_ALL_BALLOT_ITEMS"
        json_data = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'support_or_oppose_exists': support_or_oppose_exists,
        }
        return json_data

    position_manager = PositionManager()
    position_list_manager = PositionListManager()
    candidate_list_object = CandidateCampaignListManager()

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organizations_followed_by_voter_by_we_vote_id = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
            voter_id, return_we_vote_id)

    # Get a list of all candidates and measures from this election (in the active election)
    ballot_item_list_manager = BallotItemListManager()
    if positive_value_exists(google_civic_election_id):
        results = ballot_item_list_manager.retrieve_all_ballot_items_for_voter(voter_id, google_civic_election_id)
        status += results['status']
        ballot_item_list = results['ballot_item_list']
    else:
        # Look up the current google_civic_election_id for this voter
        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
        google_civic_election_id_local_scope = results['google_civic_election_id']

        if not positive_value_exists(google_civic_election_id_local_scope):
            status += "GOOGLE_CIVIC_ELECTION_ID_LOCAL_SCOPE_MISSING-CALCULATE_COUNT_FOR_ALL_BALLOT_ITEMS"
            json_data = {
                'status': status,
                'success': False,
                'google_civic_election_id': google_civic_election_id_local_scope,
                'support_or_oppose_exists': support_or_oppose_exists,
            }
            return json_data

        results = ballot_item_list_manager.retrieve_all_ballot_items_for_voter(
            voter_id, google_civic_election_id_local_scope)
        status += results['status']
        ballot_item_list = results['ballot_item_list']
        google_civic_election_id = google_civic_election_id_local_scope

    friends_we_vote_id_list = []
    if positive_value_exists(voter_we_vote_id):
        friend_manager = FriendManager()
        friend_results = friend_manager.retrieve_friends_we_vote_id_list(voter_we_vote_id)
        if friend_results['friends_we_vote_id_list_found']:
            friends_we_vote_id_list = friend_results['friends_we_vote_id_list']

    # Add yourself as a friend so your opinions show up
    friends_we_vote_id_list.append(voter_we_vote_id)

    # ballot_item_list is populated with contest_office and contest_measure entries
    for one_ballot_item in ballot_item_list:
        # Retrieve all positions for each ballot item
        if one_ballot_item.is_contest_office():
            results = candidate_list_object.retrieve_all_candidates_for_office(
                0, one_ballot_item.contest_office_we_vote_id)
            success = results['success']
            candidate_list = results['candidate_list']

            if success:
                for candidate in candidate_list:
                    # Loop through all candidates under this office

                    # Delete all prior position_network_score entries for this voter + candidate
                    ignore_measure_we_vote_id = None
                    position_list_manager.delete_position_network_scores_for_voter_one_ballot_item(
                        voter_id, voter_we_vote_id,
                        candidate.we_vote_id, ignore_measure_we_vote_id)

                    # Public Positions
                    retrieve_public_positions_now = True  # The alternate is positions for friends-only
                    most_recent_only = True
                    public_positions_list_for_one_ballot_item = \
                        position_list_manager.retrieve_all_positions_for_candidate_campaign(
                            retrieve_public_positions_now, 0, candidate.we_vote_id,
                            ANY_STANCE, most_recent_only,
                            organizations_followed_we_vote_id_list=organizations_followed_by_voter_by_we_vote_id,
                            read_only=True)

                    # Add entry to position_network_score table
                    ignore_friend_voter_we_vote_id = None
                    ignore_measure_we_vote_id = None
                    for one_position in public_positions_list_for_one_ballot_item:
                        if one_position.is_support_or_positive_rating():
                            support_or_oppose = True
                        elif one_position.is_oppose_or_negative_rating():
                            support_or_oppose = False
                        else:
                            # If not support or oppose, continue to next position
                            continue
                        support_or_oppose_exists = True
                        position_manager.update_or_create_position_network_score(
                            voter_id, voter_we_vote_id,
                            google_civic_election_id,
                            one_position.organization_we_vote_id, ignore_friend_voter_we_vote_id,
                            one_position.speaker_display_name,
                            candidate.we_vote_id, ignore_measure_we_vote_id,
                            support_or_oppose)

                    # Friend's-only Positions
                    retrieve_public_positions_now = False  # Return friends-only positions counts
                    most_recent_only = True
                    friends_only_positions_list_for_one_ballot_item = \
                        position_list_manager.retrieve_all_positions_for_candidate_campaign(
                            retrieve_public_positions_now, 0, candidate.we_vote_id,
                            ANY_STANCE, most_recent_only, friends_we_vote_id_list, read_only=True)

                    # Add entry to position_network_score table
                    ignore_organization_voter_we_vote_id = None
                    ignore_measure_we_vote_id = None
                    for one_position in friends_only_positions_list_for_one_ballot_item:
                        if one_position.is_support_or_positive_rating():
                            support_or_oppose = True
                        elif one_position.is_oppose_or_negative_rating():
                            support_or_oppose = False
                        else:
                            # If not support or oppose, continue to next position
                            continue
                        support_or_oppose_exists = True
                        position_manager.update_or_create_position_network_score(
                            voter_id, voter_we_vote_id,
                            google_civic_election_id,
                            ignore_organization_voter_we_vote_id, one_position.voter_we_vote_id,
                            one_position.speaker_display_name,
                            candidate.we_vote_id, ignore_measure_we_vote_id,
                            support_or_oppose)
        elif one_ballot_item.is_contest_measure():
            # Delete all prior position_network_score entries for this voter + candidate
            ignore_candidate_we_vote_id = None
            position_list_manager.delete_position_network_scores_for_voter_one_ballot_item(
                voter_id, voter_we_vote_id,
                ignore_candidate_we_vote_id, one_ballot_item.contest_measure_we_vote_id)

            # Public Positions
            retrieve_public_positions_now = True  # The alternate is positions for friends-only
            most_recent_only = True
            public_positions_list_for_one_ballot_item = \
                position_list_manager.retrieve_all_positions_for_contest_measure(
                    retrieve_public_positions_now, 0, one_ballot_item.contest_measure_we_vote_id,
                    ANY_STANCE, most_recent_only,
                    organizations_followed_we_vote_id_list=organizations_followed_by_voter_by_we_vote_id,
                    read_only=True)

            # Add entry to position_network_score table
            ignore_friend_voter_we_vote_id = None
            ignore_candidate_we_vote_id = None
            for one_position in public_positions_list_for_one_ballot_item:
                if one_position.is_support_or_positive_rating():
                    support_or_oppose = True
                elif one_position.is_oppose_or_negative_rating():
                    support_or_oppose = False
                else:
                    # If not support or oppose, continue to next position
                    continue
                support_or_oppose_exists = True
                position_manager.update_or_create_position_network_score(
                    voter_id, voter_we_vote_id,
                    google_civic_election_id,
                    one_position.organization_we_vote_id, ignore_friend_voter_we_vote_id,
                    one_position.speaker_display_name,
                    ignore_candidate_we_vote_id, one_ballot_item.contest_measure_we_vote_id,
                    support_or_oppose)

            # Friend's-only Positions
            retrieve_public_positions_now = False  # Return friends-only positions counts
            most_recent_only = True
            friends_only_positions_list_for_one_ballot_item = \
                position_list_manager.retrieve_all_positions_for_contest_measure(
                    retrieve_public_positions_now, 0, one_ballot_item.contest_measure_we_vote_id,
                    ANY_STANCE, most_recent_only, friends_we_vote_id_list, read_only=True)

            # Add entry to position_network_score table
            ignore_organization_voter_we_vote_id = None
            ignore_candidate_we_vote_id = None
            for one_position in friends_only_positions_list_for_one_ballot_item:
                if one_position.is_support_or_positive_rating():
                    support_or_oppose = True
                elif one_position.is_oppose_or_negative_rating():
                    support_or_oppose = False
                else:
                    # If not support or oppose, continue to next position
                    continue
                support_or_oppose_exists = True
                position_manager.update_or_create_position_network_score(
                    voter_id, voter_we_vote_id,
                    google_civic_election_id,
                    ignore_organization_voter_we_vote_id, one_position.voter_we_vote_id,
                    one_position.speaker_display_name,
                    ignore_candidate_we_vote_id, one_ballot_item.contest_measure_we_vote_id,
                    support_or_oppose)
        else:
            # Skip the rest of this loop
            continue

    json_data = {
        'success':                  True,
        'status':                   status,
        'google_civic_election_id': google_civic_election_id,
        'support_or_oppose_exists': support_or_oppose_exists,
    }
    return json_data


def count_for_all_ballot_items_from_position_network_score_for_api(  # positionsCountForAllBallotItems
        voter_device_id, google_civic_election_id=0):
    """
    We want to return a JSON file with the a list of the support and oppose counts from the orgs, friends and
    public figures the voter follows
    """
    status = ""
    # Get voter_id from the voter_device_id so we can know whose bookmarks to retrieve
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':                   "VALID_VOTER_DEVICE_ID_MISSING-COUNT_FOR_ALL_BALLOT_ITEMS_FROM_CACHE",
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'position_counts_list':     [],
            'support_or_oppose_exists': False,
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VALID_VOTER_ID_MISSING-COUNT_FOR_ALL_BALLOT_ITEMS_FROM_CACHE",
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'position_counts_list':     [],
            'support_or_oppose_exists': False,
        }
        return json_data

    if not positive_value_exists(google_civic_election_id):
        # Look up the current google_civic_election_id for this voter
        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
        google_civic_election_id = results['google_civic_election_id']

    # A google_civic_election_id is required to do any more work here (This API requires too much CPU work
    #  when a google_civic_election_id is missing.)
    if not positive_value_exists(google_civic_election_id):
        json_data = {
            'status':                   "VALID_GOOGLE_CIVIC_ELECTION_ID_MISSING-COUNT_FOR_ALL_BALLOT_ITEMS_FROM_CACHE",
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'position_counts_list':     [],
            'support_or_oppose_exists': False,
        }
        return json_data

    position_list_manager = PositionListManager()
    # The list where we capture results
    position_counts_list_results = []

    # Get all of the individual scores for this entire election
    position_network_score_list = position_list_manager.fetch_position_network_score_list(
        voter_id, google_civic_election_id)

    # Now organize the scores by ballot item
    raw_entries_by_ballot_item = {}
    for position_network_score in position_network_score_list:
        ballot_item_we_vote_id = position_network_score.get_ballot_item_we_vote_id()
        if ballot_item_we_vote_id not in raw_entries_by_ballot_item:
            temp_list = []
        else:
            temp_list = raw_entries_by_ballot_item[ballot_item_we_vote_id]
        temp_list.append(position_network_score)
        raw_entries_by_ballot_item[ballot_item_we_vote_id] = temp_list

    # Get a list of all candidates and measures from this election (in the active election)
    ballot_item_list_manager = BallotItemListManager()
    candidate_list_manager = CandidateCampaignListManager()
    read_only = True
    ballot_item_list = []
    if google_civic_election_id:
        results = ballot_item_list_manager.retrieve_all_ballot_items_for_voter(
            voter_id, google_civic_election_id, read_only)
        status += results['status']
        ballot_item_list = results['ballot_item_list']

    # ballot_item_list is populated with contest_office and contest_measure entries
    support_or_oppose_exists = False
    for one_ballot_item in ballot_item_list:
        # Retrieve all positions for each ballot item
        if one_ballot_item.is_contest_office():
            results = candidate_list_manager.retrieve_all_candidates_for_office(
                0, one_ballot_item.contest_office_we_vote_id, read_only)
            success = results['success']
            candidate_list = results['candidate_list']

            if success:
                # Loop through all candidates under this office
                for candidate in candidate_list:
                    support_count_for_one_ballot_item = 0
                    oppose_count_for_one_ballot_item = 0
                    support_we_vote_id_list = []
                    oppose_we_vote_id_list = []
                    support_name_list = []
                    oppose_name_list = []

                    if candidate.we_vote_id in raw_entries_by_ballot_item:
                        for position_network_score in raw_entries_by_ballot_item[candidate.we_vote_id]:
                            if position_network_score.is_support:
                                support_or_oppose_exists = True
                                support_count_for_one_ballot_item += 1
                                support_we_vote_id_list.append(position_network_score.get_speaker_we_vote_id())
                                support_name_list.append(position_network_score.speaker_display_name)
                            elif position_network_score.is_oppose:
                                support_or_oppose_exists = True
                                oppose_count_for_one_ballot_item += 1
                                oppose_we_vote_id_list.append(position_network_score.get_speaker_we_vote_id())
                                oppose_name_list.append(position_network_score.speaker_display_name)

                    one_ballot_item_results = {
                        'ballot_item_we_vote_id':   candidate.we_vote_id,
                        'support_count':            support_count_for_one_ballot_item,
                        'oppose_count':             oppose_count_for_one_ballot_item,
                        'support_we_vote_id_list':  support_we_vote_id_list,
                        'support_name_list':        support_name_list,
                        'oppose_we_vote_id_list':   oppose_we_vote_id_list,
                        'oppose_name_list':         oppose_name_list,
                    }
                    position_counts_list_results.append(one_ballot_item_results)
        elif one_ballot_item.is_contest_measure():
            support_count_for_one_ballot_item = 0
            oppose_count_for_one_ballot_item = 0
            support_we_vote_id_list = []
            oppose_we_vote_id_list = []
            support_name_list = []
            oppose_name_list = []

            if one_ballot_item.contest_measure_we_vote_id in raw_entries_by_ballot_item:
                for position_network_score in raw_entries_by_ballot_item[one_ballot_item.contest_measure_we_vote_id]:
                    if position_network_score.is_support:
                        support_or_oppose_exists = True
                        support_count_for_one_ballot_item += 1
                        support_we_vote_id_list.append(position_network_score.get_speaker_we_vote_id())
                        support_name_list.append(position_network_score.speaker_display_name)
                    elif position_network_score.is_oppose:
                        support_or_oppose_exists = True
                        oppose_count_for_one_ballot_item += 1
                        oppose_we_vote_id_list.append(position_network_score.get_speaker_we_vote_id())
                        oppose_name_list.append(position_network_score.speaker_display_name)

            one_ballot_item_results = {
                'ballot_item_we_vote_id':   one_ballot_item.contest_measure_we_vote_id,
                'support_count':            support_count_for_one_ballot_item,
                'oppose_count':             oppose_count_for_one_ballot_item,
                'support_we_vote_id_list':  support_we_vote_id_list,
                'support_name_list':        support_name_list,
                'oppose_we_vote_id_list':   oppose_we_vote_id_list,
                'oppose_name_list':         oppose_name_list,
            }
            position_counts_list_results.append(one_ballot_item_results)
        else:
            # Skip the rest of this loop
            continue

    json_data = {
        'success':                  True,
        'status':                   "POSITIONS_COUNT_FOR_ALL_BALLOT_ITEMS",
        'google_civic_election_id': google_civic_election_id,
        'position_counts_list':     position_counts_list_results,
        'support_or_oppose_exists': support_or_oppose_exists,
    }
    return json_data


def find_organizations_referenced_in_positions_for_this_voter(voter):
    related_organizations = []

    position_filters = []
    final_position_filters = []
    if positive_value_exists(voter.we_vote_id):
        new_position_filter = Q(voter_we_vote_id__iexact=voter.we_vote_id)
        position_filters.append(new_position_filter)
    if positive_value_exists(voter.id):
        new_position_filter = Q(voter_id=voter.id)
        position_filters.append(new_position_filter)
    if positive_value_exists(voter.linked_organization_we_vote_id):
        new_position_filter = Q(organization_we_vote_id=voter.linked_organization_we_vote_id)
        position_filters.append(new_position_filter)

    if len(position_filters):
        final_position_filters = position_filters.pop()

        # ...and "OR" the remaining items in the list
        for item in position_filters:
            final_position_filters |= item

    organization_filters = []
    organization_ids_found = []
    organization_we_vote_ids_found = []

    # PositionEntered
    position_list_query = PositionEntered.objects.all()
    # As of Aug 2018 we are no longer using PERCENT_RATING
    position_list_query = position_list_query.exclude(stance__iexact='PERCENT_RATING')
    position_list_query = position_list_query.filter(final_position_filters)

    for one_position in position_list_query:
        # Find organization(s) linked in one_position
        if positive_value_exists(one_position.organization_id) and \
                one_position.organization_id not in organization_ids_found:
            organization_ids_found.append(one_position.organization_id)
            new_organization_filter = Q(id=one_position.organization_id)
            organization_filters.append(new_organization_filter)
        if positive_value_exists(one_position.organization_we_vote_id) and \
                one_position.organization_we_vote_id not in organization_we_vote_ids_found:
            organization_we_vote_ids_found.append(one_position.organization_we_vote_id)
            new_organization_filter = Q(we_vote_id__iexact=one_position.organization_we_vote_id)
            organization_filters.append(new_organization_filter)

    # PositionForFriends
    position_list_query = PositionForFriends.objects.all()
    # As of Aug 2018 we are no longer using PERCENT_RATING
    position_list_query = position_list_query.exclude(stance__iexact='PERCENT_RATING')
    position_list_query = position_list_query.filter(final_position_filters)

    for one_position in position_list_query:
        # Find organization(s) linked in one_position
        if positive_value_exists(one_position.organization_id) and \
                one_position.organization_id not in organization_ids_found:
            organization_ids_found.append(one_position.organization_id)
            new_organization_filter = Q(id=one_position.organization_id)
            organization_filters.append(new_organization_filter)
        if positive_value_exists(one_position.organization_we_vote_id) and \
                one_position.organization_we_vote_id not in organization_we_vote_ids_found:
            organization_we_vote_ids_found.append(one_position.organization_we_vote_id)
            new_organization_filter = Q(we_vote_id__iexact=one_position.organization_we_vote_id)
            organization_filters.append(new_organization_filter)

    # Now that we have a list of all possible organization_id or organization_we_vote_id entries, retrieve all
    if len(organization_filters):
        final_organization_filters = organization_filters.pop()

        # ...and "OR" the remaining items in the list
        for item in organization_filters:
            final_organization_filters |= item

        # Finally, retrieve all of the organizations from any of these positions
        organization_list_query = Organization.objects.all()
        organization_list_query = organization_list_query.filter(final_organization_filters)

        for organization in organization_list_query:
            related_organizations.append(organization)

    return related_organizations


def merge_duplicate_positions_for_voter(position_list_for_one_voter):

    removed = []
    included = []
    position_list_for_one_voter_to_return = []
    for one_position in position_list_for_one_voter:
        for position_to_compare in position_list_for_one_voter:
            if one_position.we_vote_id != position_to_compare.we_vote_id and \
                    one_position.we_vote_id not in removed and position_to_compare not in removed:
                if do_these_match(one_position, position_to_compare, "candidate_campaign_we_vote_id"):
                    # These need to be merged
                    combine_two_positions_for_voter_and_save(position_to_compare, one_position)
                    removed.append(position_to_compare.we_vote_id)
                if do_these_match(one_position, position_to_compare, "contest_measure_we_vote_id"):
                    # These need to be merged
                    one_position = combine_two_positions_for_voter_and_save(position_to_compare, one_position)
                    removed.append(position_to_compare.we_vote_id)
                    # We do not add one_position to the "removed" list because there might be more
                    #  position_to_compare duplicates
                # We should end up with only the non-duplicate positions
                if one_position.we_vote_id not in included:
                    position_list_for_one_voter_to_return.append(one_position)
                    included.append(one_position.we_vote_id)

    return position_list_for_one_voter_to_return


def combine_two_positions_for_voter_and_save(from_position, to_position):
    """
    We want to move all values over to the "to_position". If anything gets in the way of a merge, it fails silently
    and returns the original to_position.
    :param from_position:
    :param to_position:
    :return:
    """

    # If these two positions are not for the same ballot item, and for the same person, we do not proceed
    if do_these_match(from_position, to_position, "candidate_campaign_we_vote_id"):
        # This is good
        pass
    elif do_these_match(from_position, to_position, "contest_measure_we_vote_id"):
        # This is good
        pass
    else:
        return to_position

    if do_these_match(from_position, to_position, "voter_we_vote_id") or \
            do_these_match(from_position, to_position, "organization_we_vote_id"):
        # This is required
        pass
    else:
        # We only want to merge duplicate positions for a voter or organization - at least one of them must match
        return to_position

    # If here we have made sure that we can proceed without damaging data
    # Voter entered data
    to_position.statement_html = return_most_likely_data(from_position, to_position, "statement_html")
    to_position.statement_text = return_most_likely_data(from_position, to_position, "statement_text")
    to_position.volunteer_certified = return_most_likely_data(from_position, to_position, "volunteer_certified")
    if positive_value_exists(getattr(from_position, "stance")) and \
            positive_value_exists(getattr(to_position, "stance")):
        if to_position.stance in (SUPPORT, OPPOSE):
            # Leave to_position.stance as-is
            pass
        elif from_position.stance in (SUPPORT, OPPOSE):
            to_position.stance = from_position.stance
        elif to_position.stance in (INFORMATION_ONLY, NO_STANCE):
            # Leave to_position.stance as-is
            pass
        elif from_position.stance in (INFORMATION_ONLY, NO_STANCE):
            to_position.stance = from_position.stance
        else:
            # Leave to_position.stance alone
            pass
    elif positive_value_exists(getattr(from_position, "stance")):
        to_position.stance = getattr(from_position, "stance")
    elif positive_value_exists(getattr(to_position, "stance")):
        to_position.stance = getattr(to_position, "stance")

    # Cached data like: ballot_item_display_name, ballot_item_image_url_https, ballot_item_twitter_handle,
    #  contest_office_name,
    position_manager = PositionManager()
    results = position_manager.refresh_cached_position_info(to_position)
    to_position = results['position']

    try:
        to_position.save()
        try:
            from_position.delete()
            pass
        except Exception as e:
            pass
    except Exception as e:
        pass

    return to_position


def do_these_match(from_position, to_position, attribute):
    if positive_value_exists(getattr(from_position, attribute)) and \
            positive_value_exists(getattr(to_position, attribute)):
        if getattr(from_position, attribute) == getattr(to_position, attribute):
            return True
    return False


def return_most_likely_data(from_position, to_position, attribute):
    if positive_value_exists(getattr(from_position, attribute)) and \
            positive_value_exists(getattr(to_position, attribute)):
        # Merge
        pass
    elif positive_value_exists(getattr(from_position, attribute)):
        return getattr(from_position, attribute)
    elif positive_value_exists(getattr(to_position, attribute)):
        return getattr(to_position, attribute)
    return getattr(to_position, attribute)


def move_positions_to_another_candidate(from_candidate_id, from_candidate_we_vote_id,
                                        to_candidate_id, to_candidate_we_vote_id,
                                        public_or_private):
    """

    :param from_candidate_id:
    :param from_candidate_we_vote_id:
    :param to_candidate_id:
    :param to_candidate_we_vote_id:
    :param public_or_private: If true, move public positions. If false, move friends only positions.
    :return:
    """
    status = ''
    success = True
    position_entries_moved = 0
    position_entries_not_moved = 0
    position_manager = PositionManager()
    position_list_manager = PositionListManager()

    stance_we_are_looking_for = ANY_STANCE
    most_recent_only = False
    friends_we_vote_id_list = False
    retrieve_all_admin_override = True

    # Get all positions for the "from_candidate" that we are moving away from
    from_position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
        public_or_private, from_candidate_id, from_candidate_we_vote_id, stance_we_are_looking_for,
        most_recent_only, friends_we_vote_id_list, retrieve_all_admin_override=retrieve_all_admin_override)

    # Get all positions for the "to_candidate" that we need to check
    to_position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
        public_or_private, to_candidate_id, to_candidate_we_vote_id, stance_we_are_looking_for,
        most_recent_only, friends_we_vote_id_list, retrieve_all_admin_override=retrieve_all_admin_override)

    # Put the organization_we_vote_id's of the orgs that have opinions about this candidate in a simple array
    # These are existing positions attached to the candidate we are going to keep
    to_organization_we_vote_ids = []
    to_voter_we_vote_ids = []
    for position_object in to_position_list:
        if positive_value_exists(position_object.organization_we_vote_id):
            to_organization_we_vote_ids.append(position_object.organization_we_vote_id)
        if positive_value_exists(position_object.voter_we_vote_id):
            to_voter_we_vote_ids.append(position_object.voter_we_vote_id)

    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    for position_object in from_position_list:
        # Check organization_we_vote_ids for duplicate positions
        # This is a list of positions that we want to migrate to the candidate we are planning to keep

        # If the position is friends only and doesn't have an organization_we_vote_id stored with it,
        #  we want to check the voter record to see if there is a linked_organization_we_vote_id

        if positive_value_exists(position_object.organization_we_vote_id) or \
                positive_value_exists(position_object.voter_we_vote_id):
            if position_object.organization_we_vote_id in to_organization_we_vote_ids:
                # We have an existing position for the same organization already attached to the "to" candidate,
                # so just delete the one from "from" candidate
                # In the future we could see if one has a comment that needs to be saved.
                try:
                    position_object.delete()
                    position_entries_not_moved += 1
                except Exception:
                    if public_or_private:
                        status += \
                            "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_DELETE_DUPLICATE_PUBLIC_POSITION-BY_ORGANIZATION "
                    else:
                        status += \
                            "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_DELETE_DUPLICATE_FRIENDS_POSITION-BY_ORGANIZATION "
                    success = False
                    break  # stop merge, exit for loop
            elif position_object.voter_we_vote_id in to_voter_we_vote_ids:
                # We have an existing position for the same voter already attached to the "to" candidate,
                # so just delete the one from "from" candidate
                # In the future we could see if one has a comment that needs to be saved.
                try:
                    position_object.delete()
                    position_entries_not_moved += 1
                except Exception:
                    if public_or_private:
                        status += "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_DELETE_DUPLICATE_PUBLIC_POSITION-BY_VOTER "
                    else:
                        status += "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_DELETE_DUPLICATE_FRIENDS_POSITION-BY_VOTER "
                    success = False
                    break  # stop merge, exit for loop
            else:
                # Update candidate's ids for this position
                position_object.candidate_campaign_id = to_candidate_id
                position_object.candidate_campaign_we_vote_id = to_candidate_we_vote_id
                try:
                    position_object.save()
                    position_entries_moved += 1
                    # And finally, refresh the position to use the latest information
                    force_update = True
                    results = position_manager.refresh_cached_position_info(
                        position_object, force_update,
                        offices_dict=offices_dict,
                        candidates_dict=candidates_dict,
                        measures_dict=measures_dict,
                        organizations_dict=organizations_dict,
                        voters_by_linked_org_dict=voters_by_linked_org_dict,
                        voters_dict=voters_dict)
                    offices_dict = results['offices_dict']
                    candidates_dict = results['candidates_dict']
                    measures_dict = results['measures_dict']
                    organizations_dict = results['organizations_dict']
                    voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                    voters_dict = results['voters_dict']
                except Exception:
                    if public_or_private:
                        status += "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_SAVE_NEW_PUBLIC_POSITION "
                    else:
                        status += "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_SAVE_NEW_FRIENDS_POSITION "
                    success = False
                    break  # stop merge, exit for loop
        else:
            if public_or_private:
                status += \
                    "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_FIND_ORGANIZATION_OR_VOTER_WE_VOTE_ID_FOR_PUBLIC_POSITION "
            else:
                status += \
                    "MOVE_TO_ANOTHER_CANDIDATE-UNABLE_TO_FIND_ORGANIZATION_OR_VOTER_WE_VOTE_ID_FOR_FRIENDS_POSITION "
            success = False
            break  # stop merge, exit for loop

    results = {
        'status':                       status,
        'success':                      success,
        'from_candidate_id':            from_candidate_id,
        'from_candidate_we_vote_id':    from_candidate_we_vote_id,
        'to_candidate_id':              to_candidate_id,
        'to_candidate_we_vote_id':      to_candidate_we_vote_id,
        'position_entries_moved':       position_entries_moved,
        'position_entries_not_moved':   position_entries_not_moved,
    }
    return results


def move_positions_to_another_measure(from_contest_measure_id, from_contest_measure_we_vote_id,
                                      to_contest_measure_id, to_contest_measure_we_vote_id, public_or_private):
    status = ''
    success = True
    position_entries_moved = 0
    position_entries_not_moved = 0
    position_manager = PositionManager()
    position_list_manager = PositionListManager()

    stance_we_are_looking_for = ANY_STANCE
    most_recent_only = False
    friends_we_vote_id_list = False

    # Get all positions for the "from_office" that we are moving away from
    from_position_list = position_list_manager.retrieve_all_positions_for_contest_measure(
        public_or_private, from_contest_measure_id, from_contest_measure_we_vote_id, stance_we_are_looking_for,
        most_recent_only, friends_we_vote_id_list)

    # Get all positions for the "to_office" that we need to check
    to_position_list = position_list_manager.retrieve_all_positions_for_contest_measure(
        public_or_private, to_contest_measure_id, to_contest_measure_we_vote_id, stance_we_are_looking_for,
        most_recent_only, friends_we_vote_id_list)

    # Put the organization_we_vote_id's of the orgs that have opinions about this contest measure in a simple array
    # These are existing positions attached to the contest_measure we are going to keep
    to_organization_we_vote_ids = []
    to_voter_we_vote_ids = []
    for position_object in to_position_list:
        if positive_value_exists(position_object.organization_we_vote_id):
            to_organization_we_vote_ids.append(position_object.organization_we_vote_id)
        if positive_value_exists(position_object.voter_we_vote_id):
            to_voter_we_vote_ids.append(position_object.voter_we_vote_id)

    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    for position_object in from_position_list:
        # Check organization_we_vote_ids for duplicate positions
        # This is a list of positions that we want to migrate to the contest_measure we are planning to keep

        # If the position is friends only and doesn't have an organization_we_vote_id stored with it,
        #  we want to check the voter record to see if there is a linked_organization_we_vote_id

        if positive_value_exists(position_object.organization_we_vote_id) or \
                positive_value_exists(position_object.voter_we_vote_id):
            if position_object.organization_we_vote_id in to_organization_we_vote_ids:
                # We have an existing position for the same organization already attached to the "to" contest office,
                # so just delete the one from "from" contest_measure
                # In the future we could see if one has a comment that needs to be saved.
                try:
                    position_object.delete()
                    position_entries_not_moved += 1
                except Exception:
                    if public_or_private:
                        status += \
                            "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_DELETE_DUPLICATE_PUBLIC_POSITION-BY_ORG "
                    else:
                        status += \
                            "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_DELETE_DUPLICATE_FRIENDS_POSITION-BY_ORG "
                    success = False
                    break  # stop merge, exit for loop
            elif position_object.voter_we_vote_id in to_voter_we_vote_ids:
                # We have an existing position for the same voter already attached to the "to" contest_measure,
                # so just delete the one from "from" contest_measure
                # In the future we could see if one has a comment that needs to be saved.
                try:
                    position_object.delete()
                    position_entries_not_moved += 1
                except Exception:
                    if public_or_private:
                        status += "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_DELETE_DUPLICATE_PUBLIC_POSITION-BY_VOTER "
                    else:
                        status += "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_DELETE_DUPLICATE_FRNDS_POSITION-BY_VOTER "
                    success = False
                    break  # stop merge, exit for loop
            else:
                # Update contest_measure's ids for this position
                position_object.contest_measure_id = to_contest_measure_id
                position_object.contest_measure_we_vote_id = to_contest_measure_we_vote_id
                try:
                    position_object.save()
                    position_entries_moved += 1
                    # And finally, refresh the position to use the latest information
                    force_update = True
                    results = position_manager.refresh_cached_position_info(
                        position_object, force_update,
                        offices_dict=offices_dict,
                        candidates_dict=candidates_dict,
                        measures_dict=measures_dict,
                        organizations_dict=organizations_dict,
                        voters_by_linked_org_dict=voters_by_linked_org_dict,
                        voters_dict=voters_dict)
                    offices_dict = results['offices_dict']
                    candidates_dict = results['candidates_dict']
                    measures_dict = results['measures_dict']
                    organizations_dict = results['organizations_dict']
                    voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                    voters_dict = results['voters_dict']
                except Exception:
                    if public_or_private:
                        status += "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_SAVE_NEW_PUBLIC_POSITION "
                    else:
                        status += "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_SAVE_NEW_FRIENDS_POSITION "
                    success = False
                    break  # stop merge, exit for loop
        else:
            if public_or_private:
                status += \
                    "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_FIND_ORGANIZATION_OR_VOTER_WE_VOTE_ID_" \
                    "FOR_PUBLIC_POSITION "
            else:
                status += \
                    "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_FIND_ORGANIZATION_OR_VOTER_WE_VOTE_ID_" \
                    "FOR_FRIENDS_POSITION "
            success = False
            break  # stop merge, exit for loop

    results = {
        'status':                           status,
        'success':                          success,
        'from_contest_measure_id':          from_contest_measure_id,
        'from_contest_measure_we_vote_id':  from_contest_measure_we_vote_id,
        'to_contest_measure_id':            to_contest_measure_id,
        'to_contest_measure_we_vote_id':    to_contest_measure_we_vote_id,
        'position_entries_moved':           position_entries_moved,
        'position_entries_not_moved':       position_entries_not_moved,
    }
    return results


def move_positions_to_another_office(from_contest_office_id, from_contest_office_we_vote_id,
                                     to_contest_office_id, to_contest_office_we_vote_id, public_or_private):
    status = ''
    success = True
    position_entries_moved = 0
    position_entries_not_moved = 0
    position_manager = PositionManager()
    position_list_manager = PositionListManager()

    stance_we_are_looking_for = ANY_STANCE
    most_recent_only = False
    friends_we_vote_id_list = False

    # Get all positions for the "from_office" that we are moving away from
    from_position_list = position_list_manager.retrieve_all_positions_for_contest_office(
        public_or_private, from_contest_office_id, from_contest_office_we_vote_id, stance_we_are_looking_for,
        most_recent_only, friends_we_vote_id_list)

    # Get all positions for the "to_office" that we need to check
    to_position_list = position_list_manager.retrieve_all_positions_for_contest_office(
        public_or_private, to_contest_office_id, to_contest_office_we_vote_id, stance_we_are_looking_for,
        most_recent_only, friends_we_vote_id_list)

    # Put the organization_we_vote_id's of the orgs that have opinions about this contest office in a simple array
    # These are existing positions attached to the contest office we are going to keep
    to_organization_we_vote_ids = []
    to_voter_we_vote_ids = []
    for position_object in to_position_list:
        if positive_value_exists(position_object.organization_we_vote_id):
            to_organization_we_vote_ids.append(position_object.organization_we_vote_id)
        if positive_value_exists(position_object.voter_we_vote_id):
            to_voter_we_vote_ids.append(position_object.voter_we_vote_id)

    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    for position_object in from_position_list:
        # Check organization_we_vote_ids for duplicate positions
        # This is a list of positions that we want to migrate to the contest office we are planning to keep

        # If the position is friends only and doesn't have an organization_we_vote_id stored with it,
        #  we want to check the voter record to see if there is a linked_organization_we_vote_id

        if positive_value_exists(position_object.organization_we_vote_id) or \
                positive_value_exists(position_object.voter_we_vote_id):
            if position_object.organization_we_vote_id in to_organization_we_vote_ids:
                # We have an existing position for the same organization already attached to the "to" contest office,
                # so just delete the one from "from" contest office
                # In the future we could see if one has a comment that needs to be saved.
                try:
                    position_object.delete()
                    position_entries_not_moved += 1
                except Exception:
                    if public_or_private:
                        status += \
                            "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_DELETE_DUPLICATE_PUBLIC_POSITION-BY_ORGANIZATION "
                    else:
                        status += \
                            "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_DELETE_DUPLICATE_FRIENDS_POSITION-" \
                            "BY_ORGANIZATION "
                    success = False
                    break  # stop merge, exit for loop
            elif position_object.voter_we_vote_id in to_voter_we_vote_ids:
                # We have an existing position for the same voter already attached to the "to" contest office,
                # so just delete the one from "from" contest office
                # In the future we could see if one has a comment that needs to be saved.
                try:
                    position_object.delete()
                    position_entries_not_moved += 1
                except Exception:
                    if public_or_private:
                        status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_DELETE_DUPLICATE_PUBLIC_POSITION-BY_VOTER "
                    else:
                        status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_DELETE_DUPLICATE_FRIENDS_POSITION-BY_VOTER "
                    success = False
                    break  # stop merge, exit for loop
            else:
                # Update contest_office's ids for this position
                position_object.contest_office_id = to_contest_office_id
                position_object.contest_office_we_vote_id = to_contest_office_we_vote_id
                try:
                    position_object.save()
                    position_entries_moved += 1
                    # And finally, refresh the position to use the latest information
                    force_update = True
                    results = position_manager.refresh_cached_position_info(
                        position_object, force_update,
                        offices_dict=offices_dict,
                        candidates_dict=candidates_dict,
                        measures_dict=measures_dict,
                        organizations_dict=organizations_dict,
                        voters_by_linked_org_dict=voters_by_linked_org_dict,
                        voters_dict=voters_dict)
                    offices_dict = results['offices_dict']
                    candidates_dict = results['candidates_dict']
                    measures_dict = results['measures_dict']
                    organizations_dict = results['organizations_dict']
                    voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                    voters_dict = results['voters_dict']
                except Exception:
                    if public_or_private:
                        status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_SAVE_NEW_PUBLIC_POSITION "
                    else:
                        status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_SAVE_NEW_FRIENDS_POSITION "
                    success = False
                    break  # stop merge, exit for loop
        else:
            if public_or_private:
                status += \
                    "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_FIND_ORGANIZATION_OR_VOTER_WE_VOTE_ID_" \
                    "FOR_PUBLIC_POSITION "
            else:
                status += \
                    "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_FIND_ORGANIZATION_OR_VOTER_WE_VOTE_ID_" \
                    "FOR_FRIENDS_POSITION "
            success = False
            break  # stop merge, exit for loop

    results = {
        'status':                           status,
        'success':                          success,
        'from_contest_office_id':           from_contest_office_id,
        'from_contest_office_we_vote_id':   from_contest_office_we_vote_id,
        'to_contest_office_id':             to_contest_office_id,
        'to_contest_office_we_vote_id':     to_contest_office_we_vote_id,
        'position_entries_moved':           position_entries_moved,
        'position_entries_not_moved':       position_entries_not_moved,
    }
    return results


def move_positions_to_another_organization(from_organization_id, from_organization_we_vote_id,
                                           to_organization_id, to_organization_we_vote_id,
                                           to_voter_id, to_voter_we_vote_id):
    status = ''
    success = False
    position_entries_moved = 0
    position_entries_not_moved = 0
    position_manager = PositionManager()
    position_list_manager = PositionListManager()
    organization_manager = OrganizationManager()
    to_organization_name = ""
    to_organization_type = None
    to_twitter_followers_count = None
    if positive_value_exists(to_organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(to_organization_we_vote_id)
        if results['organization_found']:
            to_voter_organization = results['organization']
            to_organization_name = to_voter_organization.organization_name
            to_organization_type = to_voter_organization.organization_type
            to_twitter_followers_count = to_voter_organization.twitter_followers_count

    # Find private positions for the "from_organization" that we are moving away from
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = FRIENDS_ONLY

    from_position_private_list = position_list_manager.retrieve_all_positions_for_organization(
        from_organization_id, from_organization_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)

    for from_position_entry in from_position_private_list:
        # See if the "to_organization" already has the same entry
        position_we_vote_id = ""
        # We do not want the voter information to change this retrieve
        empty_voter_id = 0
        empty_voter_we_vote_id = ''

        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id, to_organization_id, to_organization_we_vote_id,
            empty_voter_id,
            from_position_entry.contest_office_id, from_position_entry.candidate_campaign_id,
            from_position_entry.contest_measure_id,
            empty_voter_we_vote_id,
            from_position_entry.contest_office_we_vote_id,
            from_position_entry.candidate_campaign_we_vote_id, from_position_entry.contest_measure_we_vote_id)

        if results['position_found']:
            # Look to see if there is a statement that can be preserved (i.e., moved from from_position to to_position
            to_position_entry = results['position']
            if not positive_value_exists(to_position_entry.statement_html):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_html):
                    to_position_entry.statement_html = from_position_entry.statement_html
            if not positive_value_exists(to_position_entry.statement_text):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_text):
                    to_position_entry.statement_text = from_position_entry.statement_text
            # Update the voter values to the new "to" voter
            to_position_entry.voter_id = to_voter_id
            to_position_entry.voter_we_vote_id = to_voter_we_vote_id
            # Update cached organization information
            if positive_value_exists(to_organization_name):
                to_position_entry.speaker_display_name = to_organization_name
            if positive_value_exists(to_organization_type):
                to_position_entry.speaker_type = to_organization_type
            if positive_value_exists(to_twitter_followers_count):
                to_position_entry.twitter_followers_count = to_twitter_followers_count
            try:
                to_position_entry.save()
            except Exception as e:
                pass
        else:
            # Change the position values to the new we_vote_id
            try:
                from_position_entry.organization_id = to_organization_id
                from_position_entry.organization_we_vote_id = to_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                # Update cached organization information
                if positive_value_exists(to_organization_name):
                    from_position_entry.speaker_display_name = to_organization_name
                if positive_value_exists(to_organization_type):
                    from_position_entry.speaker_type = to_organization_type
                if positive_value_exists(to_twitter_followers_count):
                    from_position_entry.twitter_followers_count = to_twitter_followers_count

                from_position_entry.save()
                position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1

    from_position_private_list_remaining = position_list_manager.retrieve_all_positions_for_organization(
        from_organization_id, from_organization_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    for from_position_entry in from_position_private_list_remaining:
        # Delete the remaining position values
        try:
            from_position_entry.delete()
        except Exception as e:
            pass

    # Find public positions for the "from_voter" that we are moving away from
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = PUBLIC_ONLY
    from_position_public_list = position_list_manager.retrieve_all_positions_for_organization(
        from_organization_id, from_organization_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)

    for from_position_entry in from_position_public_list:
        # See if the "to_organization" already has the same entry
        position_we_vote_id = ""
        # We do not want the voter information to change this retrieve
        empty_voter_id = 0
        empty_voter_we_vote_id = ''
        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id, to_organization_id, to_organization_we_vote_id,
            empty_voter_id,
            from_position_entry.contest_office_id, from_position_entry.candidate_campaign_id,
            from_position_entry.contest_measure_id,
            empty_voter_we_vote_id,
            from_position_entry.contest_office_we_vote_id,
            from_position_entry.candidate_campaign_we_vote_id, from_position_entry.contest_measure_we_vote_id)

        if results['position_found']:
            # Look to see if there is a statement that can be preserved
            to_position_entry = results['position']
            if not positive_value_exists(to_position_entry.statement_html):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_html):
                    to_position_entry.statement_html = from_position_entry.statement_html
            if not positive_value_exists(to_position_entry.statement_text):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_text):
                    to_position_entry.statement_text = from_position_entry.statement_text
            # Update the voter values to the new "to" voter
            to_position_entry.voter_id = to_voter_id
            to_position_entry.voter_we_vote_id = to_voter_we_vote_id
            # Update cached organization information
            if positive_value_exists(to_organization_name):
                to_position_entry.speaker_display_name = to_organization_name
            if positive_value_exists(to_organization_type):
                to_position_entry.speaker_type = to_organization_type
            if positive_value_exists(to_twitter_followers_count):
                to_position_entry.twitter_followers_count = to_twitter_followers_count
            try:
                to_position_entry.save()
            except Exception as e:
                pass
        else:
            # Change the position values to the new we_vote_id
            try:
                from_position_entry.organization_id = to_organization_id
                from_position_entry.organization_we_vote_id = to_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                # Update cached organization information
                if positive_value_exists(to_organization_name):
                    from_position_entry.speaker_display_name = to_organization_name
                if positive_value_exists(to_organization_type):
                    from_position_entry.speaker_type = to_organization_type
                if positive_value_exists(to_twitter_followers_count):
                    from_position_entry.twitter_followers_count = to_twitter_followers_count

                from_position_entry.save()
                position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1

    from_position_public_list_remaining = position_list_manager.retrieve_all_positions_for_organization(
        from_organization_id, from_organization_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    for from_position_entry in from_position_public_list_remaining:
        # Delete the remaining position values
        try:
            # Leave this turned off until testing is finished
            from_position_entry.delete()
        except Exception as e:
            pass

    results = {
        'status':                       status,
        'success':                      success,
        'from_organization_id':         from_organization_id,
        'from_organization_we_vote_id': from_organization_we_vote_id,
        'to_voter_id':                  to_voter_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'position_entries_moved':       position_entries_moved,
        'position_entries_not_moved':   position_entries_not_moved,
    }
    return results


def move_positions_to_another_voter(from_voter_id, from_voter_we_vote_id,
                                    to_voter_id, to_voter_we_vote_id,
                                    to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id):
    status = ''
    success = False
    position_entries_moved = 0
    position_entries_not_moved = 0
    position_manager = PositionManager()
    position_list_manager = PositionListManager()
    organization_manager = OrganizationManager()
    to_organization_name = ""
    to_organization_type = None
    to_twitter_followers_count = None

    if from_voter_id == to_voter_id:
        status += "MOVE_POSITIONS_TO_ANOTHER_VOTER-from_voter_id and to_voter_id identical "
        results = {
            'status': status,
            'success': success,
            'from_voter_id': from_voter_id,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_id': to_voter_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'position_entries_moved': position_entries_moved,
            'position_entries_not_moved': position_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_POSITIONS_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status': status,
            'success': success,
            'from_voter_id': from_voter_id,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_id': to_voter_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'position_entries_moved': position_entries_moved,
            'position_entries_not_moved': position_entries_not_moved,
        }
        return results

    if positive_value_exists(to_voter_linked_organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(to_voter_linked_organization_we_vote_id)
        if results['organization_found']:
            to_voter_organization = results['organization']
            to_organization_name = to_voter_organization.organization_name
            to_organization_type = to_voter_organization.organization_type
            to_twitter_followers_count = to_voter_organization.twitter_followers_count

    # Find private positions for the "from_voter" that we are moving away from
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = FRIENDS_ONLY
    from_position_private_list_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_private_list = from_position_private_list_results['position_list']

    position_we_vote_id = ""
    # We don't want the organization_id to affect the retrieve
    empty_organization_id = 0
    empty_organization_we_vote_id = 0
    for from_position_entry in from_position_private_list:
        # See if the "to_voter" already has the same entry
        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id, empty_organization_id, empty_organization_we_vote_id,
            to_voter_id,
            from_position_entry.contest_office_id, from_position_entry.candidate_campaign_id,
            from_position_entry.contest_measure_id,
            to_voter_we_vote_id,
            from_position_entry.contest_office_we_vote_id,
            from_position_entry.candidate_campaign_we_vote_id, from_position_entry.contest_measure_we_vote_id)

        if results['position_found']:
            # Look to see if there is a statement that can be preserved (i.e., moved from from_position to to_position
            to_position_entry = results['position']
            if not positive_value_exists(to_position_entry.statement_html):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_html):
                    to_position_entry.statement_html = from_position_entry.statement_html
            if not positive_value_exists(to_position_entry.statement_text):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_text):
                    to_position_entry.statement_text = from_position_entry.statement_text
            # Update the organization values
            to_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
            to_position_entry.organization_id = to_voter_linked_organization_id
            # Update cached organization information
            if positive_value_exists(to_organization_name):
                to_position_entry.speaker_display_name = to_organization_name
            if positive_value_exists(to_organization_type):
                to_position_entry.speaker_type = to_organization_type
            if positive_value_exists(to_twitter_followers_count):
                to_position_entry.twitter_followers_count = to_twitter_followers_count
            try:
                to_position_entry.save()
            except Exception as e:
                status += "MOVE_TO_ANOTHER_VOTER-UNABLE_TO_SAVE_FRIENDS_ONLY_ORGANIZATION_UPDATE "
        else:
            # Change the position values to the new values
            try:
                from_position_entry.organization_id = to_voter_linked_organization_id
                from_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                # Update cached organization information
                if positive_value_exists(to_organization_name):
                    from_position_entry.speaker_display_name = to_organization_name
                if positive_value_exists(to_organization_type):
                    from_position_entry.speaker_type = to_organization_type
                if positive_value_exists(to_twitter_followers_count):
                    from_position_entry.twitter_followers_count = to_twitter_followers_count

                from_position_entry.save()
                position_entries_moved += 1
            except Exception as e:
                status += "MOVE_TO_ANOTHER_VOTER-UNABLE_TO_SAVE_FRIENDS_ONLY_ORGANIZATION_UPDATE2 "
                position_entries_not_moved += 1

    from_position_private_list_remaining_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_private_list_remaining = from_position_private_list_remaining_results['position_list']
    for from_position_entry in from_position_private_list_remaining:
        # Delete the remaining position values
        try:
            from_position_entry.delete()
        except Exception as e:
            pass

    # Find public positions for the "from_voter" that we are moving away from
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = PUBLIC_ONLY
    from_position_public_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_public_list = from_position_public_results['position_list']

    position_we_vote_id = ""
    # We don't want the organization_id to affect the retrieve
    empty_organization_id = 0
    empty_organization_we_vote_id = 0
    for from_position_entry in from_position_public_list:
        # See if the "to_voter" already has the same entry
        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id, empty_organization_id, empty_organization_we_vote_id,
            to_voter_id,
            from_position_entry.contest_office_id, from_position_entry.candidate_campaign_id,
            from_position_entry.contest_measure_id,
            to_voter_we_vote_id,
            from_position_entry.contest_office_we_vote_id,
            from_position_entry.candidate_campaign_we_vote_id, from_position_entry.contest_measure_we_vote_id)

        if results['position_found']:
            # Look to see if there is a statement that can be preserved
            to_position_entry = results['position']
            if not positive_value_exists(to_position_entry.statement_html):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_html):
                    to_position_entry.statement_html = from_position_entry.statement_html
            if not positive_value_exists(to_position_entry.statement_text):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_text):
                    to_position_entry.statement_text = from_position_entry.statement_text
            # Update the organization values
            to_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
            to_position_entry.organization_id = to_voter_linked_organization_id
            try:
                to_position_entry.save()
            except Exception as e:
                status += "MOVE_TO_ANOTHER_VOTER-UNABLE_TO_SAVE_PUBLIC_ORGANIZATION_UPDATE "
        else:
            # Change the position values to the new we_vote_id
            try:
                from_position_entry.organization_id = to_voter_linked_organization_id
                from_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                # Update cached organization information
                if positive_value_exists(to_organization_name):
                    from_position_entry.speaker_display_name = to_organization_name
                if positive_value_exists(to_organization_type):
                    from_position_entry.speaker_type = to_organization_type
                if positive_value_exists(to_twitter_followers_count):
                    from_position_entry.twitter_followers_count = to_twitter_followers_count

                from_position_entry.save()
                position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1
                status += "MOVE_TO_ANOTHER_VOTER-UNABLE_TO_SAVE_PUBLIC_ORGANIZATION_UPDATE2 "

    from_position_public_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_public_list_remaining = from_position_public_results['position_list']
    for from_position_entry in from_position_public_list_remaining:
        # Delete the remaining position values
        try:
            from_position_entry.delete()
        except Exception as e:
            pass

    results = {
        'status':                       status,
        'success':                      success,
        'from_voter_id':                from_voter_id,
        'from_voter_we_vote_id':        from_voter_we_vote_id,
        'to_voter_id':                  to_voter_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'position_entries_moved':       position_entries_moved,
        'position_entries_not_moved':   position_entries_not_moved,
    }
    return results


def duplicate_positions_to_another_voter(from_voter_id, from_voter_we_vote_id,
                                         to_voter_id, to_voter_we_vote_id,
                                         to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id):
    status = ''
    success = False
    total_position_entries_moved = 0
    total_position_entries_not_moved = 0
    position_list_manager = PositionListManager()
    copy_private_positions = True
    copy_public_positions = True

    # Find private positions for the "from_voter" that we are duplicating
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = FRIENDS_ONLY
    from_position_private_list_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_private_list = from_position_private_list_results['position_list']

    to_position_private_list_results = position_list_manager.retrieve_all_positions_for_voter(
        to_voter_id, to_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    to_position_private_list = to_position_private_list_results['position_list']
    if len(to_position_private_list):
        # If the to_voter already has private positions, we don't want to copy because we might create collisions
        copy_private_positions = False

    # These are entries found from the from_voter identifiers. May not include positions
    #  stored with the from_organization identifiers
    if copy_private_positions:
        position_entries_moved = 0
        position_entries_not_moved = 0
        for from_position_entry in from_position_private_list:
            # Change the position values to the new values
            try:
                from_position_entry.id = None
                from_position_entry.pk = None
                from_position_entry.we_vote_id = None
                from_position_entry.generate_new_we_vote_id()
                from_position_entry.organization_id = to_voter_linked_organization_id
                from_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                from_position_entry.save()
                position_entries_moved += 1
                total_position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1
                total_position_entries_not_moved += 1
        status += "DUPLICATE_TO_ANOTHER_VOTER-SAVED_FRIENDS_ONLY_POSITIONS, " \
                  "moved: {moved} " \
                  "not moved: {not_moved}" \
                  "".format(moved=position_entries_moved, not_moved=position_entries_not_moved)

    # Find public positions for the "from_voter" that we are duplicating
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = PUBLIC_ONLY
    from_position_public_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_public_list = from_position_public_results['position_list']

    to_position_public_list_results = position_list_manager.retrieve_all_positions_for_voter(
        to_voter_id, to_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    to_position_public_list = to_position_public_list_results['position_list']
    if len(to_position_public_list):
        # If the to_voter already has public positions, we don't want to copy because we might create collisions
        copy_public_positions = False

    if copy_public_positions:
        position_entries_moved = 0
        position_entries_not_moved = 0
        for from_position_entry in from_position_public_list:
            # Change the position values to the new values
            try:
                from_position_entry.id = None
                from_position_entry.pk = None
                from_position_entry.we_vote_id = None
                from_position_entry.generate_new_we_vote_id()
                from_position_entry.organization_id = to_voter_linked_organization_id
                from_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                from_position_entry.save()
                position_entries_moved += 1
                total_position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1
                total_position_entries_not_moved += 1
        status += "DUPLICATE_TO_ANOTHER_VOTER-SAVED_PUBLIC_POSITIONS, " \
                  "moved: {moved} " \
                  "not moved: {not_moved}" \
                  "".format(moved=position_entries_moved, not_moved=position_entries_not_moved)

    results = {
        'status':                       status,
        'success':                      success,
        'from_voter_id':                from_voter_id,
        'from_voter_we_vote_id':        from_voter_we_vote_id,
        'to_voter_id':                  to_voter_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'position_entries_moved':       total_position_entries_moved,
        'position_entries_not_moved':   total_position_entries_not_moved,
    }
    return results


# We retrieve from only one of the two possible variables
def position_retrieve_for_api(position_we_vote_id, voter_device_id):  # positionRetrieve
    position_we_vote_id = position_we_vote_id.strip().lower()

    # TODO for certain positions (voter positions), we need to restrict the retrieve based on voter_device_id / voter_id
    if voter_device_id:
        pass

    we_vote_id = position_we_vote_id.strip().lower()
    if not positive_value_exists(position_we_vote_id):
        json_data = {
            'status':                           "POSITION_RETRIEVE_BOTH_IDS_MISSING",
            'success':                          False,
            'position_we_vote_id':              position_we_vote_id,
            'ballot_item_display_name':         '',
            'speaker_display_name':             '',
            'speaker_image_url_https_large':    '',
            'speaker_image_url_https_medium':   '',
            'speaker_image_url_https_tiny':     '',
            'speaker_twitter_handle':           '',
            'twitter_followers_count':          '',
            'speaker_type':                     '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':              False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'state_code':               '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'vote_smart_rating':        '',
            'vote_smart_time_span':     '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()
    organization_id = 0
    organization_we_vote_id = ''
    contest_office_id = 0
    candidate_campaign_id = 0
    contest_measure_id = 0
    position_voter_id = 0
    results = position_manager.retrieve_position_table_unknown(
        position_we_vote_id, organization_id, organization_we_vote_id, position_voter_id,
        contest_office_id, candidate_campaign_id, contest_measure_id)

    if results['position_found']:
        position = results['position']
        json_data = {
            'success':                          True,
            'status':                           results['status'],
            'position_we_vote_id':              position.we_vote_id,
            'ballot_item_display_name':         position.ballot_item_display_name,
            'speaker_display_name':             position.speaker_display_name,
            'speaker_image_url_https_large':    position.speaker_image_url_https_large
                if positive_value_exists(position.speaker_image_url_https_large)
                else position.speaker_image_url_https,
            'speaker_image_url_https_medium':   position.speaker_image_url_https_medium,
            'speaker_image_url_https_tiny':     position.speaker_image_url_https_tiny,
            'speaker_twitter_handle':           position.speaker_twitter_handle,
            'twitter_followers_count':          '',
            'speaker_type':                     position.speaker_type,
            'is_support':                       results['is_support'],
            'is_positive_rating':               results['is_positive_rating'],
            'is_support_or_positive_rating':    results['is_support_or_positive_rating'],
            'is_oppose':                        results['is_oppose'],
            'is_negative_rating':               results['is_negative_rating'],
            'is_oppose_or_negative_rating':     results['is_oppose_or_negative_rating'],
            'is_information_only':      results['is_information_only'],
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'state_code':               position.state_code,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'vote_smart_rating':        position.vote_smart_rating,
            'vote_smart_time_span':     position.vote_smart_time_span,
            'last_updated':             position.last_updated(),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                           results['status'],
            'success':                          results['success'],
            'position_we_vote_id':              we_vote_id,
            'ballot_item_display_name':         '',
            'speaker_display_name':             '',
            'speaker_image_url_https_large':    '',
            'speaker_image_url_https_medium':   '',
            'speaker_image_url_https_tiny':     '',
            'speaker_twitter_handle':           '',
            'twitter_followers_count':          '',
            'speaker_type':                     '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'state_code':               '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   NO_STANCE,
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'vote_smart_rating':        '',
            'vote_smart_time_span':     '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_save_for_api(  # positionSave
        voter_device_id, position_we_vote_id,
        organization_we_vote_id,
        public_figure_we_vote_id,
        voter_we_vote_id,
        google_civic_election_id,
        state_code,
        ballot_item_display_name,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        stance,
        set_as_public_position,
        statement_text,
        statement_html,
        more_info_url):
    position_we_vote_id = position_we_vote_id.strip().lower()

    existing_unique_identifier_found = positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        results = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'twitter_followers_count':  '',
            'speaker_type':             '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'is_public_position':       False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'twitter_followers_count':  '',
            'speaker_type':             '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'is_public_position':       False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results

    # Look up the state_code from the election
    if not positive_value_exists(state_code):
        state_code = fetch_election_state(google_civic_election_id)

    position_manager = PositionManager()
    save_results = position_manager.update_or_create_position(
        position_we_vote_id=position_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        public_figure_we_vote_id=public_figure_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        state_code=state_code,
        ballot_item_display_name=ballot_item_display_name,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        stance=stance,
        set_as_public_position=set_as_public_position,
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    if save_results['success']:
        position = save_results['position']
        results = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position.we_vote_id,
            'new_position_created':     save_results['new_position_created'],
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'twitter_followers_count':  position.twitter_followers_count,
            'speaker_type':             position.speaker_type,
            'is_support':                       position.is_support(),
            'is_positive_rating':               position.is_positive_rating(),
            'is_support_or_positive_rating':    position.is_support_or_positive_rating(),
            'is_oppose':                        position.is_oppose(),
            'is_negative_rating':               position.is_negative_rating(),
            'is_oppose_or_negative_rating':     position.is_oppose_or_negative_rating(),
            'is_information_only':      position.is_information_only(),
            'is_public_position':       position.is_public_position(),
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'state_code':               position.state_code,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'twitter_followers_count':  '',
            'speaker_type':             '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'is_public_position':       False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results


def position_list_for_ballot_item_for_api(office_id, office_we_vote_id,  # positionListForBallotItem
                                          candidate_id, candidate_we_vote_id,
                                          measure_id, measure_we_vote_id,
                                          stance_we_are_looking_for=ANY_STANCE,
                                          private_citizens_only=False):
    """
    We want to return a JSON file with the public positions from organizations and public figures
    """
    status = "POSITION_LIST_FOR_BALLOT_ITEM "
    success = True

    position_manager = PositionManager()
    position_list_manager = PositionListManager()
    ballot_item_found = False
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        kind_of_ballot_item = CANDIDATE
        status += "KIND_OF_BALLOT_ITEM_CANDIDATE "

        ############################
        # Retrieve public positions
        retrieve_public_positions_now = True  # The alternate is positions for friends-only
        return_only_latest_position_per_speaker = True
        position_objects = position_list_manager.retrieve_all_positions_for_candidate_campaign(
            retrieve_public_positions_now, candidate_id, candidate_we_vote_id, stance_we_are_looking_for,
            return_only_latest_position_per_speaker, read_only=False)
        # is_public_position_setting = True
        # public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
        #                                                                      is_public_position_setting)

        # Since we want to return the id and we_vote_id for this ballot item, and we don't know for sure that
        # there are any positions for this ballot_item (which would include both the id and we_vote_id),
        # we retrieve the following so we can get the ballot item's id and we_vote_id (per the request of
        # the WebApp team)
        candidate_campaign_manager = CandidateCampaignManager()
        if positive_value_exists(candidate_id):
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        else:
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)

        if results['candidate_campaign_found']:
            candidate_campaign = results['candidate_campaign']
            ballot_item_id = candidate_campaign.id
            ballot_item_we_vote_id = candidate_campaign.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = candidate_id
            ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        kind_of_ballot_item = MEASURE
        status += "KIND_OF_BALLOT_ITEM_MEASURE "

        ############################
        # Retrieve public positions
        retrieve_public_positions_now = True  # The alternate is positions for friends-only
        return_only_latest_position_per_speaker = True
        position_objects = position_list_manager.retrieve_all_positions_for_contest_measure(
            retrieve_public_positions_now,
            measure_id, measure_we_vote_id, stance_we_are_looking_for,
            return_only_latest_position_per_speaker, read_only=False)
        # is_public_position_setting = True
        # public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
        #                                                                      is_public_position_setting)

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        contest_measure_manager = ContestMeasureManager()
        if positive_value_exists(measure_id):
            results = contest_measure_manager.retrieve_contest_measure_from_id(measure_id)
        else:
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)

        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            ballot_item_id = contest_measure.id
            ballot_item_we_vote_id = contest_measure.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = measure_id
            ballot_item_we_vote_id = measure_we_vote_id
    elif positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        kind_of_ballot_item = OFFICE

        ############################
        # Retrieve public positions
        retrieve_public_positions_now = True  # The alternate is positions for friends-only
        return_only_latest_position_per_speaker = True
        position_objects = position_list_manager.retrieve_all_positions_for_contest_office(
            retrieve_public_positions_now, office_id, office_we_vote_id, stance_we_are_looking_for,
            return_only_latest_position_per_speaker, read_only=False)
        # is_public_position_setting = True
        # public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
        #                                                                      is_public_position_setting)

        # Since we want to return the id and we_vote_id for this ballot item, and we don't know for sure that
        # there are any positions for this ballot_item (which would include both the id and we_vote_id),
        # we retrieve the following so we can get the ballot item's id and we_vote_id (per the request of
        # the WebApp team)
        contest_office_manager = ContestOfficeManager()
        if positive_value_exists(office_id):
            results = contest_office_manager.retrieve_contest_office_from_id(office_id)
        else:
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)

        if results['contest_office_found']:
            contest_office = results['contest_office']
            ballot_item_id = contest_office.id
            ballot_item_we_vote_id = contest_office.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = office_id
            ballot_item_we_vote_id = office_we_vote_id
    else:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not ballot_item_found:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_BALLOT_ITEM_NOT_FOUND',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    positions_count = len(position_objects)

    position_list = []
    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    for one_position in position_objects:
        # Is there sufficient information in the position to display it?
        some_data_exists = True if one_position.is_support() \
                           or one_position.is_oppose() \
                           or one_position.is_information_only() \
                           or positive_value_exists(one_position.vote_smart_rating) \
                           or positive_value_exists(one_position.statement_text) \
                           or positive_value_exists(one_position.more_info_url) else False
        if not some_data_exists:
            # Skip this position if there isn't any data to display
            continue

        # Whose position is it?
        if positive_value_exists(one_position.organization_we_vote_id):
            speaker_id = one_position.organization_id
            speaker_we_vote_id = one_position.organization_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https_large) \
                    or not positive_value_exists(one_position.speaker_image_url_https_medium) \
                    or not positive_value_exists(one_position.speaker_image_url_https_tiny) \
                    or not positive_value_exists(one_position.speaker_twitter_handle) \
                    or one_position.speaker_type == UNKNOWN:
                results = position_manager.refresh_cached_position_info(
                    one_position,
                    offices_dict=offices_dict,
                    candidates_dict=candidates_dict,
                    measures_dict=measures_dict,
                    organizations_dict=organizations_dict,
                    voters_by_linked_org_dict=voters_by_linked_org_dict,
                    voters_dict=voters_dict)
                one_position = results['position']
                offices_dict = results['offices_dict']
                candidates_dict = results['candidates_dict']
                measures_dict = results['measures_dict']
                organizations_dict = results['organizations_dict']
                voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                voters_dict = results['voters_dict']
            speaker_display_name = one_position.speaker_display_name
        else:
            speaker_display_name = "Unknown"
            speaker_id = None
            speaker_we_vote_id = None
            one_position_success = False

        if one_position_success:
            one_position_dict_for_api = {
                'position_we_vote_id':              one_position.we_vote_id,
                'ballot_item_display_name':         one_position.ballot_item_display_name,
                'kind_of_ballot_item':              one_position.get_kind_of_ballot_item(),
                'ballot_item_id':                   one_position.get_ballot_item_id(),
                'ballot_item_we_vote_id':           one_position.get_ballot_item_we_vote_id(),
                'speaker_display_name':             speaker_display_name,
                'speaker_image_url_https_large':    one_position.speaker_image_url_https_large
                if positive_value_exists(one_position.speaker_image_url_https_large)
                else one_position.speaker_image_url_https,
                'speaker_image_url_https_medium':   one_position.speaker_image_url_https_medium,
                'speaker_image_url_https_tiny':     one_position.speaker_image_url_https_tiny,
                'speaker_twitter_handle':           one_position.speaker_twitter_handle,
                'twitter_followers_count':          one_position.twitter_followers_count,
                'speaker_type':                     one_position.speaker_type,
                'speaker_id':                       speaker_id,
                'speaker_we_vote_id':               speaker_we_vote_id,
                'voter_we_vote_id':                 one_position.voter_we_vote_id,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'is_information_only':              one_position.is_information_only(),
                'is_public_position':               one_position.is_public_position(),
                'has_video':                        is_link_to_video(one_position.more_info_url),
                'vote_smart_rating':                one_position.vote_smart_rating,
                'vote_smart_time_span':             one_position.vote_smart_time_span,
                'statement_text':                   one_position.statement_text,
                'more_info_url':                    one_position.more_info_url,
                'last_updated':                     one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    json_data = {
        'status':                   status,
        'success':                  success,
        'count':                    positions_count,
        'kind_of_ballot_item':      kind_of_ballot_item,
        'ballot_item_id':           ballot_item_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'position_list':            position_list,
        'private_citizens_only':    private_citizens_only,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_list_for_ballot_item_for_one_voter_for_api(voter_device_id, friends_vs_public,  # positionListForBallotItem
                                          office_id, office_we_vote_id,
                                          candidate_id, candidate_we_vote_id,
                                          measure_id, measure_we_vote_id,
                                          stance_we_are_looking_for=ANY_STANCE,
                                          show_positions_this_voter_follows=False):
    """
    We want to return a JSON file with the position identifiers from orgs and public figures
    This list of information is used to retrieve the detailed information
    """
    status = "POSITION_LIST_FOR_BALLOT_ITEM "
    success = True

    position_manager = PositionManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':               'VALID_VOTER_DEVICE_ID_MISSING',
            'success':              False,
            'count':                0,
            'kind_of_ballot_item':  "UNKNOWN",
            'ballot_item_id':       0,
            'position_list':        position_list,
            'show_positions_this_voter_follows': show_positions_this_voter_follows,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':               "VALID_VOTER_ID_MISSING ",
            'success':              False,
            'count':                0,
            'kind_of_ballot_item':  "UNKNOWN",
            'ballot_item_id':       0,
            'position_list':        position_list,
            'show_positions_this_voter_follows': show_positions_this_voter_follows,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # If we are looking for positions that the voter is following, we can also show friend's opinions
    # If show_positions_this_voter_follows = False, then we are looking for positions we can follow
    retrieve_friends_positions = friends_vs_public in (FRIENDS_ONLY, FRIENDS_AND_PUBLIC) \
        and show_positions_this_voter_follows
    retrieve_public_positions = friends_vs_public in (PUBLIC_ONLY, FRIENDS_AND_PUBLIC)

    friends_we_vote_id_list = []
    if positive_value_exists(voter_we_vote_id):
        friend_manager = FriendManager()
        friend_results = friend_manager.retrieve_friends_we_vote_id_list(voter_we_vote_id)
        if friend_results['friends_we_vote_id_list_found']:
            friends_we_vote_id_list = friend_results['friends_we_vote_id_list']

    # Add yourself as a friend so your opinions show up
    friends_we_vote_id_list.append(voter_we_vote_id)

    position_list_manager = PositionListManager()
    ballot_item_found = False
    friends_positions_list = []
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        kind_of_ballot_item = CANDIDATE
        status += "KIND_OF_BALLOT_ITEM_CANDIDATE "

        ############################
        # Retrieve public positions
        if retrieve_public_positions:
            retrieve_public_positions_now = True  # The alternate is positions for friends-only
            return_only_latest_position_per_speaker = True
            public_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                retrieve_public_positions_now, candidate_id, candidate_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker)
            # is_public_position_setting = True
            # public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
            #                                                                      is_public_position_setting)
        else:
            public_positions_list = []

        ##################################
        # Now retrieve friend's positions
        if retrieve_friends_positions:
            retrieve_public_positions_now = False  # This being False means: "Positions from friends-only"
            return_only_latest_position_per_speaker = True
            friends_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                retrieve_public_positions_now, candidate_id, candidate_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker, friends_we_vote_id_list=friends_we_vote_id_list)
            # Now add is_public_position to each value
            # is_public_position_setting = False
            # friends_positions_list = position_list_manager.add_is_public_position(friends_positions_list,
            #                                                                       is_public_position_setting)
        else:
            friends_positions_list = []

        # Since we want to return the id and we_vote_id for this ballot item, and we don't know for sure that
        # there are any positions for this ballot_item (which would include both the id and we_vote_id),
        # we retrieve the following so we can get the ballot item's id and we_vote_id (per the request of
        # the WebApp team)
        candidate_campaign_manager = CandidateCampaignManager()
        if positive_value_exists(candidate_id):
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        else:
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)

        if results['candidate_campaign_found']:
            candidate_campaign = results['candidate_campaign']
            ballot_item_id = candidate_campaign.id
            ballot_item_we_vote_id = candidate_campaign.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = candidate_id
            ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        kind_of_ballot_item = MEASURE
        status += "KIND_OF_BALLOT_ITEM_MEASURE "

        ############################
        # Retrieve public positions
        if retrieve_public_positions:
            retrieve_public_positions_now = True  # The alternate is positions for friends-only
            return_only_latest_position_per_speaker = True
            public_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                retrieve_public_positions_now,
                measure_id, measure_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker)
            # is_public_position_setting = True
            # public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
            #                                                                      is_public_position_setting)
        else:
            public_positions_list = []

        ##################################
        # Now retrieve friend's positions
        if retrieve_friends_positions:
            retrieve_public_positions_now = False  # This being False means: "Positions from friends-only"
            return_only_latest_position_per_speaker = True
            friends_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                retrieve_public_positions_now,
                measure_id, measure_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker, friends_we_vote_id_list)
            # is_public_position_setting = False
            # friends_positions_list = position_list_manager.add_is_public_position(friends_positions_list,
            #                                                                       is_public_position_setting)
        else:
            friends_positions_list = []

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        contest_measure_manager = ContestMeasureManager()
        if positive_value_exists(measure_id):
            results = contest_measure_manager.retrieve_contest_measure_from_id(measure_id)
        else:
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)

        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            ballot_item_id = contest_measure.id
            ballot_item_we_vote_id = contest_measure.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = measure_id
            ballot_item_we_vote_id = measure_we_vote_id
    elif positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        kind_of_ballot_item = OFFICE

        ############################
        # Retrieve public positions
        if retrieve_public_positions:
            retrieve_public_positions_now = True  # The alternate is positions for friends-only
            return_only_latest_position_per_speaker = True
            public_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                retrieve_public_positions_now, office_id, office_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker)
            # is_public_position_setting = True
            # public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
            #                                                                      is_public_position_setting)
        else:
            public_positions_list = []

        ##################################
        # Now retrieve friend's positions
        if retrieve_friends_positions:
            retrieve_public_positions_now = False  # This being False means: "Positions from friends-only"
            return_only_latest_position_per_speaker = True
            friends_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                retrieve_public_positions_now, office_id, office_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker, friends_we_vote_id_list)
            # Now add is_public_position to each value
            # is_public_position_setting = False
            # friends_positions_list = position_list_manager.add_is_public_position(friends_positions_list,
            #                                                                       is_public_position_setting)
        else:
            friends_positions_list = []

        # Since we want to return the id and we_vote_id for this ballot item, and we don't know for sure that
        # there are any positions for this ballot_item (which would include both the id and we_vote_id),
        # we retrieve the following so we can get the ballot item's id and we_vote_id (per the request of
        # the WebApp team)
        contest_office_manager = ContestOfficeManager()
        if positive_value_exists(office_id):
            results = contest_office_manager.retrieve_contest_office_from_id(office_id)
        else:
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)

        if results['contest_office_found']:
            contest_office = results['contest_office']
            ballot_item_id = contest_office.id
            ballot_item_we_vote_id = contest_office.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = office_id
            ballot_item_we_vote_id = office_we_vote_id
    else:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'position_list':            position_list,
            'show_positions_this_voter_follows': show_positions_this_voter_follows,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not ballot_item_found:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_BALLOT_ITEM_NOT_FOUND',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'position_list':            position_list,
            'show_positions_this_voter_follows': show_positions_this_voter_follows,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if len(public_positions_list):
        follow_organization_list_manager = FollowOrganizationList()
        organizations_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

        if show_positions_this_voter_follows:
            position_objects = position_list_manager.calculate_positions_followed_by_voter(
                voter_id, public_positions_list, organizations_followed_by_voter)
            status += 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_FOLLOWED'
            success = True
        else:
            position_objects = position_list_manager.calculate_positions_not_followed_by_voter(
                public_positions_list, organizations_followed_by_voter)
            status += 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED'
            success = True
    else:
        position_objects = []

    if len(friends_positions_list):
        position_objects = friends_positions_list + position_objects

    positions_count = len(position_objects)

    # We need the linked_organization_we_vote_id so we can remove the viewer's positions from the list.
    linked_organization_we_vote_id = ""
    if positive_value_exists(positions_count):
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter = results['voter']
            linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    position_list = []
    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    for one_position in position_objects:
        # Is there sufficient information in the position to display it?
        some_data_exists = True if one_position.is_support() \
                           or one_position.is_oppose() \
                           or one_position.is_information_only() \
                           or positive_value_exists(one_position.vote_smart_rating) \
                           or positive_value_exists(one_position.statement_text) \
                           or positive_value_exists(one_position.more_info_url) else False
        if not some_data_exists:
            # Skip this position if there isn't any data to display
            continue

        # Whose position is it?
        if positive_value_exists(one_position.organization_we_vote_id):
            if linked_organization_we_vote_id == one_position.organization_we_vote_id:
                # Do not show your own position on the position list, since it will be in the edit spot already
                continue
            speaker_id = one_position.organization_id
            speaker_we_vote_id = one_position.organization_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https_large) \
                    or not positive_value_exists(one_position.speaker_image_url_https_medium) \
                    or not positive_value_exists(one_position.speaker_image_url_https_tiny) \
                    or not positive_value_exists(one_position.speaker_twitter_handle) \
                    or one_position.speaker_type == UNKNOWN:
                results = position_manager.refresh_cached_position_info(
                    one_position,
                    offices_dict=offices_dict,
                    candidates_dict=candidates_dict,
                    measures_dict=measures_dict,
                    organizations_dict=organizations_dict,
                    voters_by_linked_org_dict=voters_by_linked_org_dict,
                    voters_dict=voters_dict)
                one_position = results['position']
                offices_dict = results['offices_dict']
                candidates_dict = results['candidates_dict']
                measures_dict = results['measures_dict']
                organizations_dict = results['organizations_dict']
                voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                voters_dict = results['voters_dict']
            speaker_display_name = one_position.speaker_display_name
        elif positive_value_exists(one_position.voter_id):
            if voter_id == one_position.voter_id:
                # Do not show your own position on the position list, since it will be in the edit spot already
                continue
            speaker_id = one_position.voter_id
            speaker_we_vote_id = one_position.voter_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.voter_we_vote_id) \
                    or not positive_value_exists(one_position.speaker_image_url_https_large) \
                    or not positive_value_exists(one_position.speaker_image_url_https_medium) \
                    or not positive_value_exists(one_position.speaker_image_url_https_tiny) \
                    or one_position.speaker_type == UNKNOWN:
                results = position_manager.refresh_cached_position_info(
                    one_position,
                    offices_dict=offices_dict,
                    candidates_dict=candidates_dict,
                    measures_dict=measures_dict,
                    organizations_dict=organizations_dict,
                    voters_by_linked_org_dict=voters_by_linked_org_dict,
                    voters_dict=voters_dict)
                one_position = results['position']
                offices_dict = results['offices_dict']
                candidates_dict = results['candidates_dict']
                measures_dict = results['measures_dict']
                organizations_dict = results['organizations_dict']
                voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                voters_dict = results['voters_dict']
            if positive_value_exists(one_position.speaker_display_name):
                speaker_display_name = one_position.speaker_display_name
            else:
                speaker_display_name = "Your Friend (Missing Name)"
        elif positive_value_exists(one_position.public_figure_we_vote_id):
            speaker_id = one_position.public_figure_id
            speaker_we_vote_id = one_position.public_figure_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https_large) \
                    or not positive_value_exists(one_position.speaker_image_url_https_medium) \
                    or not positive_value_exists(one_position.speaker_image_url_https_tiny) \
                    or not positive_value_exists(one_position.speaker_twitter_handle) \
                    or one_position.speaker_type == UNKNOWN:
                results = position_manager.refresh_cached_position_info(
                    one_position,
                    offices_dict=offices_dict,
                    candidates_dict=candidates_dict,
                    measures_dict=measures_dict,
                    organizations_dict=organizations_dict,
                    voters_by_linked_org_dict=voters_by_linked_org_dict,
                    voters_dict=voters_dict)
                one_position = results['position']
                offices_dict = results['offices_dict']
                candidates_dict = results['candidates_dict']
                measures_dict = results['measures_dict']
                organizations_dict = results['organizations_dict']
                voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                voters_dict = results['voters_dict']
            speaker_display_name = one_position.speaker_display_name
        else:
            speaker_display_name = "Unknown"
            speaker_id = None
            speaker_we_vote_id = None
            one_position_success = False

        if one_position_success:
            one_position_dict_for_api = {
                'position_we_vote_id':              one_position.we_vote_id,
                'ballot_item_display_name':         one_position.ballot_item_display_name,
                'kind_of_ballot_item':              one_position.get_kind_of_ballot_item(),
                'ballot_item_id':                   one_position.get_ballot_item_id(),
                'ballot_item_we_vote_id':           one_position.get_ballot_item_we_vote_id(),
                'speaker_display_name':             speaker_display_name,
                'speaker_image_url_https_large':    one_position.speaker_image_url_https_large
                if positive_value_exists(one_position.speaker_image_url_https_large)
                else one_position.speaker_image_url_https,
                'speaker_image_url_https_medium':   one_position.speaker_image_url_https_medium,
                'speaker_image_url_https_tiny':     one_position.speaker_image_url_https_tiny,
                'speaker_twitter_handle':           one_position.speaker_twitter_handle,
                'twitter_followers_count':          one_position.twitter_followers_count,
                'speaker_type':                     one_position.speaker_type,
                'speaker_id':                       speaker_id,
                'speaker_we_vote_id':               speaker_we_vote_id,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'is_information_only':              one_position.is_information_only(),
                'is_public_position':               one_position.is_public_position(),
                'has_video':                        is_link_to_video(one_position.more_info_url),
                'vote_smart_rating':                one_position.vote_smart_rating,
                'vote_smart_time_span':             one_position.vote_smart_time_span,
                'statement_text':                   one_position.statement_text,
                'more_info_url':                    one_position.more_info_url,
                'last_updated':                     one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    json_data = {
        'status':                   status,
        'success':                  success,
        'count':                    positions_count,
        'kind_of_ballot_item':      kind_of_ballot_item,
        'ballot_item_id':           ballot_item_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'position_list':            position_list,
        'show_positions_this_voter_follows': show_positions_this_voter_follows,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_list_for_opinion_maker_for_api(voter_device_id,  # positionListForOpinionMaker
                                            organization_id, organization_we_vote_id,
                                            public_figure_id, public_figure_we_vote_id,
                                            friends_vs_public=FRIENDS_AND_PUBLIC,
                                            stance_we_are_looking_for=ANY_STANCE,
                                            filter_for_voter=False,
                                            filter_out_voter=False,
                                            google_civic_election_id=0,
                                            state_code=''):
    """
    We want to return a JSON file with a list of positions held by orgs, and friends public figures.
    We can limit the positions to friend's only if needed.
    """
    is_following = False
    is_ignoring = False
    opinion_maker_display_name = ''
    opinion_maker_image_url_https_large = ''
    opinion_maker_image_url_https_medium = ''
    opinion_maker_image_url_https_tiny = ''
    status = ''
    position_list_raw = []

    # Convert incoming variables to "opinion_maker"
    if positive_value_exists(organization_id) or positive_value_exists(organization_we_vote_id):
        kind_of_opinion_maker = ORGANIZATION
        kind_of_opinion_maker_text = "ORGANIZATION"  # For returning a value via the API
        opinion_maker_id = organization_id
        opinion_maker_we_vote_id = organization_we_vote_id
    elif positive_value_exists(public_figure_id) or positive_value_exists(public_figure_we_vote_id):
        kind_of_opinion_maker = PUBLIC_FIGURE
        kind_of_opinion_maker_text = "PUBLIC_FIGURE"
        opinion_maker_id = public_figure_id
        opinion_maker_we_vote_id = public_figure_we_vote_id
    else:
        kind_of_opinion_maker = UNKNOWN
        kind_of_opinion_maker_text = "UNKNOWN_VOTER_GUIDE"
        opinion_maker_id = 0
        opinion_maker_we_vote_id = ''

    position_manager = PositionManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':                               'VALID_VOTER_DEVICE_ID_MISSING_OPINION_MAKER_POSITION_LIST',
            'success':                              False,
            'count':                                0,
            'kind_of_opinion_maker':                kind_of_opinion_maker_text,
            'opinion_maker_id':                     opinion_maker_id,
            'opinion_maker_we_vote_id':             opinion_maker_we_vote_id,
            'opinion_maker_display_name':           opinion_maker_display_name,
            'opinion_maker_image_url_https_large':  opinion_maker_image_url_https_large,
            'opinion_maker_image_url_https_medium': opinion_maker_image_url_https_medium,
            'opinion_maker_image_url_https_tiny':   opinion_maker_image_url_https_tiny,
            'is_following':                         is_following,
            'is_ignoring':                          is_ignoring,
            'google_civic_election_id':             google_civic_election_id,
            'state_code':                           state_code,
            'position_list':                        position_list,
            'filter_for_voter':                     filter_for_voter,
            'filter_out_voter':                     filter_out_voter,
            'friends_vs_public':                    friends_vs_public,
        }
        return json_data

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':                               "VALID_VOTER_ID_MISSING_OPINION_MAKER_POSITION_LIST ",
            'success':                              False,
            'count':                                0,
            'kind_of_opinion_maker':                kind_of_opinion_maker_text,
            'opinion_maker_id':                     opinion_maker_id,
            'opinion_maker_we_vote_id':             opinion_maker_we_vote_id,
            'opinion_maker_display_name':           opinion_maker_display_name,
            'opinion_maker_image_url_https_large':  opinion_maker_image_url_https_large,
            'opinion_maker_image_url_https_medium': opinion_maker_image_url_https_medium,
            'opinion_maker_image_url_https_tiny':   opinion_maker_image_url_https_tiny,
            'is_following':                         is_following,
            'is_ignoring':                          is_ignoring,
            'google_civic_election_id':             google_civic_election_id,
            'state_code':                           state_code,
            'position_list':                        position_list,
            'filter_for_voter':                     filter_for_voter,
            'filter_out_voter':                     filter_out_voter,
            'friends_vs_public':                    friends_vs_public,
        }
        return json_data

    position_list_manager = PositionListManager()
    opinion_maker_found = False
    if is_speaker_type_organization(kind_of_opinion_maker):
        status += "SPEAKER_IS_ORGANIZATION " + str(kind_of_opinion_maker) + " "
        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this opinion_maker, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        organization_manager = OrganizationManager()
        if positive_value_exists(organization_id):
            results = organization_manager.retrieve_organization_from_id(organization_id)
        else:
            results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)

        if results['organization_found']:
            organization = results['organization']
            opinion_maker_id = organization.id
            opinion_maker_we_vote_id = organization.we_vote_id
            opinion_maker_display_name = organization.organization_name
            opinion_maker_image_url_https_large = organization.we_vote_hosted_profile_image_url_large \
                if positive_value_exists(organization.we_vote_hosted_profile_image_url_large) \
                else organization.organization_photo_url()
            opinion_maker_image_url_https_medium = organization.we_vote_hosted_profile_image_url_medium
            opinion_maker_image_url_https_tiny = organization.we_vote_hosted_profile_image_url_tiny
            opinion_maker_found = True

            follow_organization_manager = FollowOrganizationManager()
            voter_we_vote_id = ''
            following_results = follow_organization_manager.retrieve_voter_following_org_status(
                voter_id, voter_we_vote_id, opinion_maker_id, opinion_maker_we_vote_id)
            if following_results['is_following']:
                is_following = True
            elif following_results['is_ignoring']:
                is_ignoring = True

            position_list_raw = position_list_manager.retrieve_all_positions_for_organization(
                    organization_id, organization_we_vote_id, stance_we_are_looking_for, friends_vs_public,
                    filter_for_voter, filter_out_voter, voter_device_id, google_civic_election_id)
        else:
            opinion_maker_id = organization_id
            opinion_maker_we_vote_id = organization_we_vote_id
    elif is_speaker_type_public_figure(kind_of_opinion_maker):
        status += "SPEAKER_IS_PUBLIC_FIGURE " + str(kind_of_opinion_maker) + " "
        # TODO retrieve_all_positions_for_public_figure is just a stub, and doesn't do anything.  The list is empty.
        position_list_raw = position_list_manager.retrieve_all_positions_for_public_figure(
                public_figure_id, public_figure_we_vote_id, stance_we_are_looking_for,
                filter_for_voter, filter_out_voter, voter_device_id, google_civic_election_id, state_code)

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this opinion_maker, we retrieve the following so we can have the id and we_vote_id (per the request of
        # the WebApp team)
        # TODO Do we want to give public figures an entry separate from their voter account? Needs to be implemented.
        # candidate_campaign_manager = CandidateCampaignManager()
        # if positive_value_exists(candidate_id):
        #     results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        # else:
        #     results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        #
        # if results['candidate_campaign_found']:
        #     candidate_campaign = results['candidate_campaign']
        #     ballot_item_id = candidate_campaign.id
        #     ballot_item_we_vote_id = candidate_campaign.we_vote_id
        #     opinion_maker_found = True
        # else:
        #     ballot_item_id = candidate_id
        #     ballot_item_we_vote_id = candidate_we_vote_id
    else:
        position_list = []
        status += 'POSITION_LIST_RETRIEVE_MISSING_OPINION_MAKER_ID '
        json_data = {
            'status':                               status,
            'success':                              False,
            'count':                                0,
            'kind_of_opinion_maker':                kind_of_opinion_maker_text,
            'opinion_maker_id':                     opinion_maker_id,
            'opinion_maker_we_vote_id':             opinion_maker_we_vote_id,
            'opinion_maker_display_name':           opinion_maker_display_name,
            'opinion_maker_image_url_https_large':  opinion_maker_image_url_https_large,
            'opinion_maker_image_url_https_medium': opinion_maker_image_url_https_medium,
            'opinion_maker_image_url_https_tiny':   opinion_maker_image_url_https_tiny,
            'is_following':                         is_following,
            'is_ignoring':                          is_ignoring,
            'google_civic_election_id':             google_civic_election_id,
            'state_code':                           state_code,
            'position_list':                        position_list,
            'filter_for_voter':                     filter_for_voter,
            'filter_out_voter':                     filter_out_voter,
            'friends_vs_public':                    friends_vs_public,
        }
        return json_data

    if not opinion_maker_found:
        position_list = []
        status += 'POSITION_LIST_RETRIEVE_OPINION_MAKER_NOT_FOUND '
        json_data = {
            'status':                               status,
            'success':                              False,
            'count':                                0,
            'kind_of_opinion_maker':                kind_of_opinion_maker_text,
            'opinion_maker_id':                     opinion_maker_id,
            'opinion_maker_we_vote_id':             opinion_maker_we_vote_id,
            'opinion_maker_display_name':           opinion_maker_display_name,
            'opinion_maker_image_url_https_large':  opinion_maker_image_url_https_large,
            'opinion_maker_image_url_https_medium': opinion_maker_image_url_https_medium,
            'opinion_maker_image_url_https_tiny':   opinion_maker_image_url_https_tiny,
            'is_following':                         is_following,
            'is_ignoring':                          is_ignoring,
            'google_civic_election_id':             google_civic_election_id,
            'state_code':                           state_code,
            'position_list':                        position_list,
            'filter_for_voter':                     filter_for_voter,
            'filter_out_voter':                     filter_out_voter,
            'friends_vs_public':                    friends_vs_public,
        }
        return json_data

    position_list = []
    all_elections_that_have_positions = []
    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    status += "POSITION_LIST_RAW_COUNT: " + str(len(position_list_raw)) + " "
    for one_position in position_list_raw:
        # Whose position is it?
        missing_ballot_item_image = False
        missing_office_information = False
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            if not positive_value_exists(one_position.contest_office_we_vote_id) \
                    or not positive_value_exists(one_position.contest_office_name):
                missing_office_information = True
            if not positive_value_exists(one_position.ballot_item_image_url_https):
                missing_ballot_item_image = True
            one_position_success = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = one_position.contest_measure_id
            ballot_item_we_vote_id = one_position.contest_measure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.contest_office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = one_position.contest_office_id
            ballot_item_we_vote_id = one_position.contest_office_we_vote_id
            one_position_success = True
        else:
            status += "UNKNOWN_BALLOT_ITEM "
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            # Make sure we have this data to display. If we don't, refresh PositionEntered table from other tables.
            if position_manager.position_speaker_name_needs_repair(one_position, opinion_maker_display_name):
                force_update = True
            else:
                force_update = False
            race_office_level_missing = not positive_value_exists(one_position.race_office_level) \
                and positive_value_exists(one_position.candidate_campaign_we_vote_id)
            if force_update or not positive_value_exists(one_position.ballot_item_display_name) \
                    or not positive_value_exists(one_position.state_code) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or one_position.speaker_type == UNKNOWN \
                    or missing_ballot_item_image \
                    or missing_office_information \
                    or race_office_level_missing:
                results = position_manager.refresh_cached_position_info(
                    one_position, force_update,
                    offices_dict=offices_dict,
                    candidates_dict=candidates_dict,
                    measures_dict=measures_dict,
                    organizations_dict=organizations_dict,
                    voters_by_linked_org_dict=voters_by_linked_org_dict,
                    voters_dict=voters_dict)
                one_position = results['position']
                offices_dict = results['offices_dict']
                candidates_dict = results['candidates_dict']
                measures_dict = results['measures_dict']
                organizations_dict = results['organizations_dict']
                voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                voters_dict = results['voters_dict']
            one_position_dict_for_api = {
                'position_we_vote_id':                  one_position.we_vote_id,
                'ballot_item_display_name':
                    one_position.ballot_item_display_name
                    if positive_value_exists(one_position.ballot_item_display_name) else "",  # Candidate or Measure
                'ballot_item_image_url_https_large':    one_position.ballot_item_image_url_https_large
                    if positive_value_exists(one_position.ballot_item_image_url_https_large)
                    else one_position.ballot_item_image_url_https,
                'ballot_item_image_url_https_medium':   one_position.ballot_item_image_url_https_medium,
                'ballot_item_image_url_https_tiny':     one_position.ballot_item_image_url_https_tiny,
                'ballot_item_twitter_handle':           one_position.ballot_item_twitter_handle,
                'ballot_item_political_party':          one_position.political_party,
                'kind_of_ballot_item':                  kind_of_ballot_item,
                'ballot_item_id':                       ballot_item_id,
                'ballot_item_we_vote_id':               ballot_item_we_vote_id,
                'ballot_item_state_code':               one_position.state_code,
                'contest_office_id':                    one_position.contest_office_id,
                'contest_office_we_vote_id':            one_position.contest_office_we_vote_id,
                'contest_office_name':                  one_position.contest_office_name,
                'race_office_level':                    one_position.race_office_level,
                'is_support':                           one_position.is_support(),
                'is_positive_rating':                   one_position.is_positive_rating(),
                'is_support_or_positive_rating':        one_position.is_support_or_positive_rating(),
                'is_oppose':                            one_position.is_oppose(),
                'is_negative_rating':                   one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':         one_position.is_oppose_or_negative_rating(),
                'is_information_only':                  one_position.is_information_only(),
                'is_public_position':                   one_position.is_public_position(),
                'speaker_display_name':                 one_position.speaker_display_name,  # Organization name
                'speaker_image_url_https_large':        one_position.speaker_image_url_https_large,
                'speaker_image_url_https_medium':       one_position.speaker_image_url_https_medium,
                'speaker_image_url_https_tiny':         one_position.speaker_image_url_https_tiny,
                'speaker_twitter_handle':               one_position.speaker_twitter_handle,
                'twitter_followers_count':              one_position.twitter_followers_count,
                'speaker_type':                         one_position.speaker_type,
                'organization_we_vote_id':              one_position.organization_we_vote_id,
                'speaker_we_vote_id':                   one_position.organization_we_vote_id,
                'vote_smart_rating':                    one_position.vote_smart_rating,
                'vote_smart_time_span':                 one_position.vote_smart_time_span,
                'google_civic_election_id':             one_position.google_civic_election_id,
                'state_code':                           one_position.state_code,
                'more_info_url':                        one_position.more_info_url,
                'statement_text':                       one_position.statement_text,
                'last_updated':                         one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

            if positive_value_exists(one_position.google_civic_election_id) \
                    and one_position.google_civic_election_id not in all_elections_that_have_positions:
                all_elections_that_have_positions.append(one_position.google_civic_election_id)

    # Now change the sort order
    if len(position_list):
        status += "SORTING_POSITION_LIST "
        sorted_position_list = sorted(position_list, key=itemgetter('ballot_item_display_name'))
        # Add reverse=True to sort descending
    else:
        sorted_position_list = []

    # Now make sure a voter_guide entry exists for the organization for each election
    voter_guide_manager = VoterGuideManager()
    if positive_value_exists(opinion_maker_we_vote_id) and len(all_elections_that_have_positions):
        for one_google_civic_election_id in all_elections_that_have_positions:
            if not voter_guide_manager.voter_guide_exists(opinion_maker_we_vote_id, one_google_civic_election_id):
                voter_guide_we_vote_id = ''
                voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                    voter_guide_we_vote_id, opinion_maker_we_vote_id, one_google_civic_election_id, state_code)

    status += 'POSITION_LIST_FOR_OPINION_MAKER_SUCCEEDED '
    success = True
    json_data = {
        'status':                               status,
        'success':                              success,
        'count':                                len(position_list),
        'kind_of_opinion_maker':                kind_of_opinion_maker_text,
        'opinion_maker_id':                     opinion_maker_id,
        'opinion_maker_we_vote_id':             opinion_maker_we_vote_id,
        'opinion_maker_display_name':           opinion_maker_display_name,
        'opinion_maker_image_url_https_large':  opinion_maker_image_url_https_large,
        'opinion_maker_image_url_https_medium': opinion_maker_image_url_https_medium,
        'opinion_maker_image_url_https_tiny':   opinion_maker_image_url_https_tiny,
        'is_following':                         is_following,
        'is_ignoring':                          is_ignoring,
        'google_civic_election_id':             google_civic_election_id,
        'state_code':                           state_code,
        'position_list':                        sorted_position_list,
        'filter_for_voter':                     filter_for_voter,
        'filter_out_voter':                     filter_out_voter,
        'friends_vs_public':                    friends_vs_public,
    }
    return json_data


def position_list_for_voter_for_api(voter_device_id,
                                    friends_vs_public=FRIENDS_AND_PUBLIC,
                                    stance_we_are_looking_for=ANY_STANCE,
                                    show_only_this_election=False,
                                    show_all_other_elections=False,
                                    google_civic_election_id=0,
                                    state_code=''):  # positionListForVoter
    """
    We want to return a JSON file with a list of positions held by this voter.
    We can limit the positions to friend's only if needed.
    """
    voter_we_vote_id = ""
    voter_display_name = ''
    voter_image_url_https_large = ''
    voter_image_url_https_medium = ''
    voter_image_url_https_tiny= ''
    status = ''
    position_list_raw = []

    position_manager = PositionManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':                           'VALID_VOTER_DEVICE_ID_MISSING_VOTER_POSITION_LIST',
            'success':                          False,
            'count':                            0,
            'friends_vs_public':                friends_vs_public,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
            'show_all_other_elections':         show_all_other_elections,
            'show_only_this_election':          show_only_this_election,
            'voter_we_vote_id':                 voter_we_vote_id,
            'voter_display_name':               voter_display_name,
            'voter_image_url_https_large':      voter_image_url_https_large,
            'voter_image_url_https_medium':     voter_image_url_https_medium,
            'voter_image_url_https_tiny':       voter_image_url_https_tiny,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':                           "VALID_VOTER_ID_MISSING_VOTER_POSITION_LIST ",
            'success':                          False,
            'count':                            0,
            'friends_vs_public':                friends_vs_public,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
            'show_all_other_elections':         show_all_other_elections,
            'show_only_this_election':          show_only_this_election,
            'voter_we_vote_id':                 voter_we_vote_id,
            'voter_display_name':               voter_display_name,
            'voter_image_url_https_large':      voter_image_url_https_large,
            'voter_image_url_https_medium':     voter_image_url_https_medium,
            'voter_image_url_https_tiny':       voter_image_url_https_tiny,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter = voter_results['voter']
    '''
    voter_display_name = voter.first_name
    voter_image_url_https_large = voter.we_vote_hosted_profile_image_url_large
    voter_image_url_https_medium = voter.we_vote_hosted_profile_image_url_medium
    voter_image_url_https_tiny = voter.we_vote_hosted_profile_image_url_tiny
    '''
    position_list_manager = PositionListManager()
    if show_only_this_election:
        this_election_vs_others = THIS_ELECTION_ONLY
    elif show_all_other_elections:
        this_election_vs_others = ALL_OTHER_ELECTIONS
    else:
        this_election_vs_others = ALL_ELECTIONS

    position_list_results = position_list_manager.retrieve_all_positions_for_voter(
        voter.id, voter.we_vote_id, stance_we_are_looking_for, friends_vs_public, google_civic_election_id,
        this_election_vs_others)
    if position_list_results['position_list_found']:
        position_list_retrieved = position_list_results['position_list']
    else:
        position_list_retrieved = []

    position_list = []
    offices_dict = {}
    candidates_dict = {}
    measures_dict = {}
    organizations_dict = {}
    voters_by_linked_org_dict = {}
    voters_dict = {}
    for one_position in position_list_retrieved:
        # Whose position is it?
        missing_ballot_item_image = False
        missing_office_information = False
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            if not positive_value_exists(one_position.contest_office_we_vote_id) \
                    or not positive_value_exists(one_position.contest_office_name):
                missing_office_information = True
            if not positive_value_exists(one_position.ballot_item_image_url_https):
                missing_ballot_item_image = True
            one_position_success = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = one_position.contest_measure_id
            ballot_item_we_vote_id = one_position.contest_measure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.contest_office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = one_position.contest_office_id
            ballot_item_we_vote_id = one_position.contest_office_we_vote_id
            one_position_success = True
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            # Make sure we have this data to display. If we don't, refresh PositionEntered table from other tables.
            race_office_level_missing = not positive_value_exists(one_position.race_office_level) \
                and positive_value_exists(one_position.candidate_campaign_we_vote_id)
            if not positive_value_exists(one_position.ballot_item_display_name) \
                    or not positive_value_exists(one_position.state_code) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or missing_ballot_item_image \
                    or missing_office_information \
                    or race_office_level_missing:
                results = position_manager.refresh_cached_position_info(
                    one_position,
                    offices_dict=offices_dict,
                    candidates_dict=candidates_dict,
                    measures_dict=measures_dict,
                    organizations_dict=organizations_dict,
                    voters_by_linked_org_dict=voters_by_linked_org_dict,
                    voters_dict=voters_dict)
                one_position = results['position']
                offices_dict = results['offices_dict']
                candidates_dict = results['candidates_dict']
                measures_dict = results['measures_dict']
                organizations_dict = results['organizations_dict']
                voters_by_linked_org_dict = results['voters_by_linked_org_dict']
                voters_dict = results['voters_dict']
            one_position_dict_for_api = {
                'position_we_vote_id':                  one_position.we_vote_id,
                'ballot_item_display_name':             one_position.ballot_item_display_name,  # Candidate name or
                                                                                                # Measure
                'ballot_item_image_url_https_large':    one_position.ballot_item_image_url_https_large
                if positive_value_exists(one_position.ballot_item_image_url_https_large)
                else one_position.ballot_item_image_url_https,
                'ballot_item_image_url_https_medium':   one_position.ballot_item_image_url_https_medium,
                'ballot_item_image_url_https_tiny':     one_position.ballot_item_image_url_https_tiny,
                'ballot_item_twitter_handle':           one_position.ballot_item_twitter_handle,
                'ballot_item_political_party':          one_position.political_party,
                'ballot_item_state_code':               one_position.state_code,
                'kind_of_ballot_item':                  kind_of_ballot_item,
                'ballot_item_id':                       ballot_item_id,
                'ballot_item_we_vote_id':               ballot_item_we_vote_id,
                'contest_office_id':                    one_position.contest_office_id,
                'contest_office_we_vote_id':            one_position.contest_office_we_vote_id,
                'contest_office_name':                  one_position.contest_office_name,
                'race_office_level':                    one_position.race_office_level,
                'is_support':                           one_position.is_support(),
                'is_positive_rating':                   one_position.is_positive_rating(),
                'is_support_or_positive_rating':        one_position.is_support_or_positive_rating(),
                'is_oppose':                            one_position.is_oppose(),
                'is_negative_rating':                   one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':         one_position.is_oppose_or_negative_rating(),
                'is_information_only':                  one_position.is_information_only(),
                'is_public_position':                   one_position.is_public_position(),
                'speaker_display_name':                 one_position.speaker_display_name,  # Voter name
                'google_civic_election_id':             one_position.google_civic_election_id,
                'state_code':                           one_position.state_code,
                'more_info_url':                        one_position.more_info_url,
                'statement_text':                       one_position.statement_text,
                'last_updated':                         one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)
            if not positive_value_exists(state_code):
                state_code = one_position.state_code

    status += ' POSITION_LIST_FOR_VOTER_SUCCEEDED'
    success = True
    json_data = {
        'status':                           status,
        'success':                          success,
        'count':                            len(position_list),
        'friends_vs_public':                friends_vs_public,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
        'position_list':                    position_list,
        'show_all_other_elections':         show_all_other_elections,
        'show_only_this_election':          show_only_this_election,
        'voter_we_vote_id':                 voter_we_vote_id,
        'voter_display_name':               voter_display_name,
        'voter_image_url_https_large':      voter_image_url_https_large,
        'voter_image_url_https_medium':     voter_image_url_https_medium,
        'voter_image_url_https_tiny':       voter_image_url_https_tiny,
        # 'voter_we_vote_id':                 voter.we_vote_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_import_from_sample_file(request=None):  # , load_from_uri=False
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Load saved json from local file
    with open("position/import_data/positions_sample.json") as json_data:
        structured_json = json.load(json_data)

    request = None
    return positions_import_from_structured_json(request, structured_json)


def positions_import_from_master_server(request, google_civic_election_id=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """

    import_results, structured_json = process_request_from_master(
        request, "Loading Positions from We Vote Master servers",
        POSITIONS_SYNC_URL, {
            "key":                      WE_VOTE_API_KEY,  # This comes from an environment variable
            "format":                   'json',
            "google_civic_election_id": str(google_civic_election_id),
        }
    )

    if import_results['success']:
        results = filter_positions_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        import_results = positions_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_positions_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove positions that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    position_list_manager = PositionListManager()
    for one_position in structured_json:
        we_vote_id = one_position['we_vote_id'] if 'we_vote_id' in one_position else ''
        google_civic_election_id = \
            one_position['google_civic_election_id'] if 'google_civic_election_id' in one_position else ''
        organization_we_vote_id = \
            one_position['organization_we_vote_id'] if 'organization_we_vote_id' in one_position else ''
        candidate_campaign_we_vote_id = one_position['candidate_campaign_we_vote_id'] \
            if 'candidate_campaign_we_vote_id' in one_position else ''
        contest_measure_we_vote_id = one_position['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_position else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = position_list_manager.retrieve_possible_duplicate_positions(
            google_civic_election_id, organization_we_vote_id,
            candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            we_vote_id_from_master)

        if results['position_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_position)

    positions_results = {
        'success':              True,
        'status':               "FILTER_POSITIONS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return positions_results


def positions_import_from_structured_json(structured_json):
    positions_saved = 0
    positions_updated = 0
    positions_not_processed = 0
    for one_position in structured_json:
        # Make sure we have the minimum required variables
        if positive_value_exists(one_position["we_vote_id"]) \
                and (positive_value_exists(one_position["organization_we_vote_id"]) or positive_value_exists(
                        one_position["public_figure_we_vote_id"])) \
                and positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            # organization position on candidate
            pass
        elif positive_value_exists(one_position["we_vote_id"]) \
                and (positive_value_exists(one_position["organization_we_vote_id"]) or positive_value_exists(
                    one_position["public_figure_we_vote_id"])) \
                and positive_value_exists(one_position["contest_measure_we_vote_id"]):
            # organization position on measure
            pass
        else:
            # Note that we do not import voter_we_vote_id positions at this point because they are considered private
            positions_not_processed += 1
            continue

        # Check to see if this position had been imported previously
        position_on_stage_found = False
        try:
            if len(one_position["we_vote_id"]) > 0:
                position_query = PositionEntered.objects.filter(we_vote_id=one_position["we_vote_id"])
                if len(position_query):
                    position_on_stage = position_query[0]
                    position_on_stage_found = True
        except PositionEntered.DoesNotExist as e:
            pass
        except Exception as e:
            print("exception thrown in positions_import_from_structured_json" + e)
            pass

        # We need to look up the local organization_id and store for internal use
        organization_id = 0
        if positive_value_exists(one_position["organization_we_vote_id"]):
            organization_manager = OrganizationManager()
            organization_id = organization_manager.fetch_organization_id(one_position["organization_we_vote_id"])
            if not positive_value_exists(organization_id):
                # If an id does not exist, then we don't have this organization locally
                positions_not_processed += 1
                continue
        elif positive_value_exists(one_position["public_figure_we_vote_id"]):
            # TODO Build this for public_figure - skip for now
            continue

        candidate_campaign_manager = CandidateCampaignManager()
        candidate_campaign_id = 0
        contest_measure_id = 0
        if positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            # We need to look up the local candidate_campaign_id and store for internal use
            candidate_campaign_id = candidate_campaign_manager.fetch_candidate_campaign_id_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])
            if not positive_value_exists(candidate_campaign_id):
                # If an id does not exist, then we don't have this candidate locally
                # print("positions_import did not find a candidate_campaign_id for candidate_campaign_we_vote_id: " +
                #       one_position["candidate_campaign_we_vote_id"])
                positions_not_processed += 1
                continue
        elif positive_value_exists(one_position["contest_measure_we_vote_id"]):
            contest_measure_manager = ContestMeasureManager()
            contest_measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(
                one_position["contest_measure_we_vote_id"])
            if not positive_value_exists(contest_measure_id):
                # If an id does not exist, then we don't have this measure locally
                # print("positions_import did not find a contest_measure_id for contest_measure_we_vote_id: " +
                #       one_position["contest_measure_we_vote_id"])
                positions_not_processed += 1
                continue

        contest_office_id = 0
        if positive_value_exists(one_position['contest_office_we_vote_id']):
            # TODO
            pass

        politician_id = 0
        if positive_value_exists(one_position['politician_we_vote_id']):
            # TODO
            pass

        voter_id = 0
        if positive_value_exists(one_position['voter_we_vote_id']):
            # TODO
            pass

        # Find the google_civic_candidate_name so we have a backup way to link position if the we_vote_id is lost
        google_civic_candidate_name = one_position["google_civic_candidate_name"] if \
            "google_civic_candidate_name" in one_position else ''
        if not positive_value_exists(google_civic_candidate_name):
            google_civic_candidate_name = candidate_campaign_manager.fetch_google_civic_candidate_name_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])

        try:
            if position_on_stage_found:
                # Update
                position_on_stage.we_vote_id = one_position["we_vote_id"]
                position_on_stage.candidate_campaign_id = candidate_campaign_id
                position_on_stage.candidate_campaign_we_vote_id = one_position["candidate_campaign_we_vote_id"]
                position_on_stage.contest_measure_id = contest_measure_id
                position_on_stage.contest_measure_we_vote_id = one_position["contest_measure_we_vote_id"]
                position_on_stage.contest_office_id = contest_office_id
                position_on_stage.contest_office_we_vote_id = one_position["contest_office_we_vote_id"]
                position_on_stage.race_office_level = one_position["race_office_level"]
                position_on_stage.date_entered = one_position["date_entered"]
                position_on_stage.google_civic_candidate_name = google_civic_candidate_name
                position_on_stage.google_civic_election_id = one_position["google_civic_election_id"]
                position_on_stage.state_code = one_position["state_code"]
                position_on_stage.more_info_url = one_position["more_info_url"]
                position_on_stage.organization_id = organization_id
                position_on_stage.organization_we_vote_id = one_position["organization_we_vote_id"]
                position_on_stage.stance = one_position["stance"]
                position_on_stage.statement_text = one_position["statement_text"]
                position_on_stage.statement_html = one_position["statement_html"]
                position_on_stage.is_private_citizen = one_position["is_private_citizen"]
            else:
                # Create new
                position_on_stage = PositionEntered(
                    we_vote_id=one_position["we_vote_id"],
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=one_position["candidate_campaign_we_vote_id"],
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=one_position["contest_measure_we_vote_id"],
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=one_position["contest_office_we_vote_id"],
                    date_entered=one_position["date_entered"],
                    google_civic_candidate_name=google_civic_candidate_name,
                    google_civic_election_id=one_position["google_civic_election_id"],
                    state_code=one_position["state_code"],
                    more_info_url=one_position["more_info_url"],
                    organization_id=organization_id,
                    organization_we_vote_id=one_position["organization_we_vote_id"],
                    stance=one_position["stance"],
                    statement_html=one_position["statement_html"],
                    statement_text=one_position["statement_text"],
                    is_private_citizen=one_position["is_private_citizen"],
                )

            position_on_stage.ballot_item_display_name = one_position["ballot_item_display_name"]
            position_on_stage.ballot_item_image_url_https = one_position["ballot_item_image_url_https"]
            position_on_stage.ballot_item_twitter_handle = one_position["ballot_item_twitter_handle"]
            position_on_stage.from_scraper = one_position["from_scraper"]
            position_on_stage.date_last_changed = one_position["date_last_changed"]
            position_on_stage.organization_certified = one_position["organization_certified"]
            position_on_stage.politician_id = politician_id
            position_on_stage.politician_we_vote_id = one_position["politician_we_vote_id"]
            position_on_stage.public_figure_we_vote_id = one_position["public_figure_we_vote_id"]
            position_on_stage.speaker_display_name = one_position["speaker_display_name"]
            position_on_stage.speaker_image_url_https = one_position["speaker_image_url_https"]
            position_on_stage.speaker_twitter_handle = one_position["speaker_twitter_handle"]
            position_on_stage.twitter_followers_count = one_position["twitter_followers_count"]
            position_on_stage.speaker_type = one_position["speaker_type"]
            position_on_stage.tweet_source_id = one_position["tweet_source_id"]
            position_on_stage.twitter_user_entered_position = one_position["twitter_user_entered_position"]
            position_on_stage.volunteer_certified = one_position["volunteer_certified"]
            position_on_stage.vote_smart_rating = one_position["vote_smart_rating"]
            position_on_stage.vote_smart_rating_id = one_position["vote_smart_rating_id"]
            position_on_stage.vote_smart_rating_name = one_position["vote_smart_rating_name"]
            position_on_stage.vote_smart_time_span = one_position["vote_smart_time_span"]
            position_on_stage.voter_entering_position = one_position["voter_entering_position"]
            position_on_stage.voter_id = voter_id
            position_on_stage.voter_we_vote_id = one_position["voter_we_vote_id"]

            position_on_stage.save()
            if position_on_stage_found:
                # Update
                positions_updated += 1
            else:
                # New
                positions_saved += 1
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            positions_not_processed += 1

    positions_results = {
        'success': True,
        'status': "POSITIONS_IMPORT_PROCESS_COMPLETE",
        'saved': positions_saved,
        'updated': positions_updated,
        'not_processed': positions_not_processed,
    }
    return positions_results


# We retrieve the position for this voter for one ballot item. Could just be the stance, but for now we are
# retrieving the entire position
def voter_position_retrieve_for_api(voter_device_id, office_we_vote_id, candidate_we_vote_id, measure_we_vote_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if positive_value_exists(office_we_vote_id):
        kind_of_ballot_item = OFFICE
        ballot_item_we_vote_id = office_we_vote_id
    elif positive_value_exists(candidate_we_vote_id):
        kind_of_ballot_item = CANDIDATE
        ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_we_vote_id):
        kind_of_ballot_item = MEASURE
        ballot_item_we_vote_id = candidate_we_vote_id
    else:
        kind_of_ballot_item = ''
        ballot_item_we_vote_id = ''

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                  False,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'twitter_followers_count':  '',
            'speaker_type':             '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'state_code':               '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_we_vote_id = office_we_vote_id.strip().lower()
    candidate_we_vote_id = candidate_we_vote_id.strip().lower()
    measure_we_vote_id = measure_we_vote_id.strip().lower()

    if not positive_value_exists(office_we_vote_id) and \
            not positive_value_exists(candidate_we_vote_id) and \
            not positive_value_exists(measure_we_vote_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "POSITION_RETRIEVE_MISSING_AT_LEAST_ONE_BALLOT_ITEM_ID",
            'success':                  False,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'twitter_followers_count':  '',
            'speaker_type':             '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'state_code':               '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()

    if positive_value_exists(office_we_vote_id):
        results = position_manager.retrieve_voter_contest_office_position_with_we_vote_id(
            voter_id, office_we_vote_id)

    elif positive_value_exists(candidate_we_vote_id):
        results = position_manager.retrieve_voter_candidate_campaign_position_with_we_vote_id(
            voter_id, candidate_we_vote_id)

    elif positive_value_exists(measure_we_vote_id):
        results = position_manager.retrieve_voter_contest_measure_position_with_we_vote_id(
            voter_id, measure_we_vote_id)

    if results['position_found']:
        position = results['position']
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'twitter_followers_count':  position.twitter_followers_count,
            'speaker_type':             position.speaker_type,
            'is_support':               results['is_support'],
            'is_oppose':                results['is_oppose'],
            'is_information_only':      results['is_information_only'],
            'google_civic_election_id': position.google_civic_election_id,
            'state_code':               position.state_code,
            'office_we_vote_id':        position.contest_office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   results['status'],
            'success':                  True,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'twitter_followers_count':  '',
            'speaker_type':             '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'state_code':               '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


# We retrieve the position for this voter for all ballot items. Could just be the stance, but for now we are
# retrieving the entire position
def voter_all_positions_retrieve_for_api(voter_device_id, google_civic_election_id):  # voterAllPositionsRetrieve
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':                   "VOTER_DEVICE_ID_NOT_VALID-VOTER_ALL_POSITIONS",
            'success':                  False,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_ALL_POSITIONS",
            'success':                  False,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    voter_we_vote_id = ''

    results = position_list_manager.retrieve_all_positions_for_voter_simple(voter_id, voter_we_vote_id,
                                                                            google_civic_election_id)

    if results['position_list_found']:
        position_list = results['position_list']
        json_data = {
            'status':                   results['status'],
            'success':                  True,
            'position_list_found':      True,
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   "VOTER_POSITIONS_NOT_FOUND-NONE_EXIST",
            'success':                  True,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_comment_save_for_api(  # voterPositionCommentSave
        voter_device_id, position_we_vote_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        statement_text,
        statement_html,
        ):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_POSITION_COMMENT",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data

    voter = voter_results['voter']
    position_we_vote_id = position_we_vote_id.strip().lower()

    existing_unique_identifier_found = positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(voter_id) \
        and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
        )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(voter_id) \
        and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
        )
    if not unique_identifier_found:
        json_data = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data

    position_manager = PositionManager()
    save_results = position_manager.update_or_create_position_comment(
        position_we_vote_id=position_we_vote_id,
        voter_id=voter_id,
        voter_we_vote_id=voter.we_vote_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html
    )

    if save_results['success']:
        position = save_results['position']

        is_public_position = save_results['is_public_position']

        if positive_value_exists(position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = position.candidate_campaign_id
            ballot_item_we_vote_id = position.candidate_campaign_we_vote_id
        elif positive_value_exists(position.contest_measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = position.contest_measure_id
            ballot_item_we_vote_id = position.contest_measure_we_vote_id
        elif positive_value_exists(position.contest_office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = position.contest_office_id
            ballot_item_we_vote_id = position.contest_office_we_vote_id
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None

        json_data = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'is_public_position':       is_public_position
        }
        return json_data
    else:
        json_data = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      '',
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   "",
            'kind_of_ballot_item':      "",
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'is_public_position':       False
        }
        return json_data


def voter_position_visibility_save_for_api(  # voterPositionVisibilitySave
        voter_device_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        visibility_setting
        ):
    status = ''
    status += "ENTERING_VOTER_POSITION_VISIBILITY "
    is_public_position = None

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_POSITION_VISIBILITY "
        json_data = {
            'status':                   status,
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data

    voter = voter_results['voter']
    unique_identifier_found = positive_value_exists(voter_id) \
        and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
        )
    if not unique_identifier_found:
        status += "VOTER_POSITION_VISIBILITY-REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING "
        json_data = {
            'status':                   status,
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data

    switch_to_show_position_to_public = visibility_setting == SHOW_PUBLIC
    switch_to_show_position_to_friends = visibility_setting == FRIENDS_ONLY

    if not switch_to_show_position_to_public and not switch_to_show_position_to_friends:
        status += "VOTER_POSITION_VISIBILITY-NO_VISIBILITY_SETTING_PROVIDED "
        json_data = {
            'status':                   status,
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data

    if switch_to_show_position_to_public:
        # Check to see if this voter has a linked_organization_we_vote_id. If not, try to repair the data (Heal data).
        if not positive_value_exists(voter.linked_organization_we_vote_id):
            organization_manager = OrganizationManager()
            repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(voter)
            status += repair_results['status']
            if repair_results['voter_repaired']:
                voter = repair_results['voter']

        # Check to see if this voter has a linked_organization_we_vote_id. If not, don't proceed.
        if not positive_value_exists(voter.linked_organization_we_vote_id):
            status += "VOTER_POSITION_VISIBILITY-VOTER_DOES_NOT_HAVE_LINKED_ORG_WE_VOTE_ID "
            json_data = {
                'status':                   status,
                'success':                  False,
                'voter_device_id':          voter_device_id,
                'position_we_vote_id':      '',
                'ballot_item_id':           0,
                'ballot_item_we_vote_id':   "",
                'kind_of_ballot_item':      "",
                'visibility_setting':       visibility_setting,
                'is_public_position':       is_public_position,
            }
            return json_data

    # Make sure we can lay our hands on the existing position entry
    success = False
    position_manager = PositionManager()
    if positive_value_exists(candidate_we_vote_id):
        results = position_manager.retrieve_voter_candidate_campaign_position_with_we_vote_id(
            voter_id, candidate_we_vote_id)
    elif positive_value_exists(measure_we_vote_id):
        results = position_manager.retrieve_voter_contest_measure_position_with_we_vote_id(
            voter_id, measure_we_vote_id)
    elif positive_value_exists(office_we_vote_id):
        results = position_manager.retrieve_voter_contest_office_position_with_we_vote_id(
            voter_id, office_we_vote_id)

    if not results['position_found']:
        # If here, an existing position does not exist and a new position needs to be created
        results = position_manager.create_position_for_visibility_change(
            voter_id, office_we_vote_id, candidate_we_vote_id, measure_we_vote_id, visibility_setting)
        if results['position_found']:
            is_public_position = results['is_public_position']
            position = results['position']
            status += results['status']
            success = results['success']
        else:
            status += "VOTER_POSITION_VISIBILITY-POSITION_NOT_FOUND_AND_NOT_CREATED "
            success = False

    elif results['position_found']:
        is_public_position = results['is_public_position']
        position = results['position']

        if positive_value_exists(switch_to_show_position_to_public):
            if positive_value_exists(is_public_position):
                status += "VOTER_POSITION_VISIBILITY-ALREADY_PUBLIC_POSITION "
                merge_results = position_manager.merge_into_public_position(position)
                success = merge_results['success']
                status += " " + merge_results['status']
            else:
                # If here, copy the position from the PositionForFriends table to the PositionEntered table
                status += "VOTER_POSITION_VISIBILITY-SWITCHING_TO_PUBLIC_POSITION "
                change_results = position_manager.transfer_to_public_position(position)
                success = change_results['success']
                status += " " + change_results['status']
                if success:
                    is_public_position = True
        elif positive_value_exists(switch_to_show_position_to_friends):
            if positive_value_exists(is_public_position):
                # If here, copy the position from the PositionEntered to the PositionForFriends table
                status += "VOTER_POSITION_VISIBILITY-SWITCHING_TO_FRIENDS_ONLY_POSITION "
                change_results = position_manager.transfer_to_friends_only_position(position)
                success = change_results['success']
                status += " " + change_results['status']
                if success:
                    is_public_position = False
            else:
                status += "VOTER_POSITION_VISIBILITY-ALREADY_FRIENDS_ONLY_POSITION "
                merge_results = position_manager.merge_into_friends_only_position(position)
                success = merge_results['success']
                status += " " + merge_results['status']
    else:
        status += "VOTER_POSITION_VISIBILITY-POSITION_NOT_FOUND-COULD_NOT_BE_CREATED"
        # If here, an existing position could not be created
        position_manager.create_position_for_visibility_change()

    if success:
        # Prepare return values
        if positive_value_exists(candidate_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = position.candidate_campaign_id
            ballot_item_we_vote_id = position.candidate_campaign_we_vote_id
        elif positive_value_exists(measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = position.contest_measure_id
            ballot_item_we_vote_id = measure_we_vote_id
        elif positive_value_exists(office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = position.contest_office_id
            ballot_item_we_vote_id = position.contest_office_we_vote_id
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None

        json_data = {
            'success':                  success,
            'status':                   status,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data
    else:
        if positive_value_exists(candidate_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = 0
            ballot_item_we_vote_id = candidate_we_vote_id
        elif positive_value_exists(measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = 0
            ballot_item_we_vote_id = measure_we_vote_id
        elif positive_value_exists(office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = 0
            ballot_item_we_vote_id = office_we_vote_id
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None

        json_data = {
            'success':                  success,
            'status':                   status,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      '',
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data


def refresh_cached_position_info_for_election(google_civic_election_id, state_code=''):
    google_civic_election_id = convert_to_int(google_civic_election_id)

    position_list_manager = PositionListManager()

    results = position_list_manager.refresh_cached_position_info_for_election(google_civic_election_id, state_code)
    public_positions_updated = results['public_positions_updated']
    friends_only_positions_updated = results['friends_only_positions_updated']

    status = "REFRESH_CACHED_POSITION_INFO_FOR_ELECTION-public:" + str(public_positions_updated) + \
             ",friends_only:" + str(friends_only_positions_updated)
    results = {
        'success':                          True,
        'status':                           status,
        'public_positions_updated':         public_positions_updated,
        'friends_only_positions_updated':   friends_only_positions_updated,
    }
    return results


def refresh_positions_with_candidate_details_for_election(google_civic_election_id, state_code):
    update_all_positions_results = []
    positions_updated_count = 0
    google_civic_election_id = convert_to_int(google_civic_election_id)

    candidate_list_manager = CandidateCampaignListManager()
    return_list_of_objects = True
    candidates_results = candidate_list_manager.retrieve_all_candidates_for_upcoming_election(
        google_civic_election_id, state_code, return_list_of_objects)
    if candidates_results['candidate_list_found']:
        candidate_list = candidates_results['candidate_list_objects']

        for candidate in candidate_list:
            update_position_results = update_all_position_details_from_candidate(candidate)
            positions_updated_count += update_position_results['positions_updated_count']
            update_all_positions_results.append(update_position_results)

    status = "POSITION_WITH_CANDIDATE_DETAILS_UPATED"
    results = {
        'success':                      True,
        'status':                       status,
        'positions_updated_count':      positions_updated_count,
        'update_all_positions_results': update_all_positions_results,
    }
    return results


def refresh_positions_with_contest_office_details_for_election(google_civic_election_id, state_code):
    update_all_positions_results = []
    positions_updated_count = 0
    google_civic_election_id = convert_to_int(google_civic_election_id)

    contest_office_list_manager = ContestOfficeListManager()
    return_list_of_objects = True
    contest_offices_results = contest_office_list_manager.retrieve_all_offices_for_upcoming_election(
        google_civic_election_id, state_code, return_list_of_objects)
    if contest_offices_results['office_list_found']:
        office_list = contest_offices_results['office_list_objects']

        for office in office_list:
            update_position_results = update_all_position_details_from_contest_office(office)
            positions_updated_count += update_position_results['positions_updated_count']
            update_all_positions_results.append(update_position_results)

    status = "POSITION_WITH_CONTEST_OFFICE_DETAILS_UPATED"
    results = {
        'success':                      True,
        'status':                       status,
        'positions_updated_count':      positions_updated_count,
        'update_all_positions_results': update_all_positions_results,
    }
    return results


def refresh_positions_with_contest_measure_details_for_election(google_civic_election_id, state_code):
    update_all_positions_results = []
    positions_updated_count = 0
    google_civic_election_id = convert_to_int(google_civic_election_id)

    contest_measure_list_manager = ContestMeasureList()
    return_list_of_objects = True
    contest_measures_results = contest_measure_list_manager.retrieve_all_measures_for_upcoming_election(
        google_civic_election_id, state_code, return_list_of_objects)
    if contest_measures_results['measure_list_found']:
        measure_list = contest_measures_results['measure_list_objects']

        for measure in measure_list:
            update_position_results = update_all_position_details_from_contest_measure(measure)
            positions_updated_count += update_position_results['positions_updated_count']
            update_all_positions_results.append(update_position_results)

    status = "POSITION_WITH_CONTEST_MEASURE_DETAILS_UPATED"
    results = {
        'success':                      True,
        'status':                       status,
        'positions_updated_count':      positions_updated_count,
        'update_all_positions_results': update_all_positions_results,
    }
    return results


def retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(voter_id,
                                                                 organization_id, organization_we_vote_id,
                                                                 stance_we_are_looking_for=SUPPORT,
                                                                 google_civic_election_id=0,
                                                                 state_code=''):
    """
    For each organization, we want to return a list of ballot_items that this organization has
    an opinion about for the current election.
    We also want to be able to limit the position list by google_civic_election_id.
    """
    is_following = False
    is_ignoring = False
    status = ''
    position_list_raw = []

    if not positive_value_exists(voter_id):
        ballot_item_we_vote_ids_list = []
        results = {
            'status':                       "VALID_VOTER_ID_MISSING ",
            'success':                      False,
            'count':                        0,
            'organization_id':              organization_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   state_code,
            'ballot_item_we_vote_ids_list': ballot_item_we_vote_ids_list,
        }
        return results

    position_list_manager = PositionListManager()
    # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
    # for this opinion_maker, we retrieve the following so we can get the id and we_vote_id (per the request of
    # the WebApp team)
    organization_manager = OrganizationManager()
    if positive_value_exists(organization_id):
        results = organization_manager.retrieve_organization_from_id(organization_id, read_only=True)
    else:
        results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id,
                                                                             read_only=True)

    if results['organization_found']:
        organization = results['organization']
        opinion_maker_id = organization.id
        opinion_maker_we_vote_id = organization.we_vote_id
        opinion_maker_found = True

        follow_organization_manager = FollowOrganizationManager()
        voter_we_vote_id = ''
        following_results = follow_organization_manager.retrieve_voter_following_org_status(
            voter_id, voter_we_vote_id, opinion_maker_id, opinion_maker_we_vote_id, read_only=True)
        if following_results['is_following']:
            is_following = True
        elif following_results['is_ignoring']:
            is_ignoring = True

        if is_following or is_ignoring:
            ballot_item_we_vote_ids_list = []
            results = {
                'status': 'RETRIEVE_BALLOT_ITEM_WE_VOTE_IDS-ALREADY_FOLLOWING_OR_IGNORING',
                'success': False,
                'count': 0,
                'organization_id': organization_id,
                'organization_we_vote_id': organization_we_vote_id,
                'google_civic_election_id': google_civic_election_id,
                'state_code': state_code,
                'ballot_item_we_vote_ids_list': ballot_item_we_vote_ids_list,
            }
            return results

        friends_vs_public = PUBLIC_ONLY
        show_positions_current_voter_election = True
        exclude_positions_current_voter_election = False
        voter_device_id = ''

        position_list_raw = position_list_manager.retrieve_all_positions_for_organization(
            organization_id, organization_we_vote_id, stance_we_are_looking_for, friends_vs_public,
            show_positions_current_voter_election, exclude_positions_current_voter_election, voter_device_id,
            google_civic_election_id, read_only=True)
    else:
        opinion_maker_found = False

    if not opinion_maker_found:
        ballot_item_we_vote_ids_list = []
        results = {
            'status':                       'RETRIEVE_BALLOT_ITEM_WE_VOTE_IDS-ORGANIZATION_NOT_FOUND',
            'success':                      False,
            'count':                        0,
            'organization_id':              organization_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   state_code,
            'ballot_item_we_vote_ids_list': ballot_item_we_vote_ids_list,
        }
        return results

    # Now change the sort order
    if len(position_list_raw):
        sorted_position_list = position_list_raw
        # TODO FIX: sorted_position_list = sorted(position_list_raw, key=itemgetter('ballot_item_display_name'))
        # Add reverse=True to sort descending
    else:
        sorted_position_list = []

    ballot_item_we_vote_ids_list = []
    all_elections_that_have_positions = []
    for one_position in sorted_position_list:
        # Collect the ballot_item_we_vote_id
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            # kind_of_ballot_item = CANDIDATE
            # ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            # if not positive_value_exists(one_position.contest_office_we_vote_id) \
            #         or not positive_value_exists(one_position.contest_office_name):
            #     missing_office_information = True
            # if not positive_value_exists(one_position.ballot_item_image_url_https):
            #     missing_ballot_item_image = True
            one_position_success = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            # kind_of_ballot_item = MEASURE
            # ballot_item_id = one_position.contest_measure_id
            ballot_item_we_vote_id = one_position.contest_measure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.contest_office_we_vote_id):
            # kind_of_ballot_item = OFFICE
            # ballot_item_id = one_position.contest_office_id
            ballot_item_we_vote_id = one_position.contest_office_we_vote_id
            one_position_success = True
        else:
            # kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            # ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            ballot_item_we_vote_ids_list.append(ballot_item_we_vote_id)

            # if positive_value_exists(one_position.google_civic_election_id) \
            #         and one_position.google_civic_election_id not in all_elections_that_have_positions:
            #     all_elections_that_have_positions.append(one_position.google_civic_election_id)

    # DALE 2017-02-10 Turning this off here for now -- may turn back on later
    # # Now make sure a voter_guide entry exists for the organization for each election
    # voter_guide_manager = VoterGuideManager()
    # if positive_value_exists(opinion_maker_we_vote_id) and len(all_elections_that_have_positions):
    #     for one_google_civic_election_id in all_elections_that_have_positions:
    #         if not voter_guide_manager.voter_guide_exists(opinion_maker_we_vote_id, one_google_civic_election_id):
    #             voter_guide_we_vote_id = ''
    #             voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
    #                 voter_guide_we_vote_id, opinion_maker_we_vote_id, one_google_civic_election_id)

    status += ' RETRIEVE_BALLOT_ITEM_WE_VOTE_IDS-SUCCESS'
    success = True
    results = {
        'status':                       status,
        'success':                      success,
        'count':                        len(sorted_position_list),
        'organization_id':              organization_id,
        'organization_we_vote_id':      organization_we_vote_id,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'ballot_item_we_vote_ids_list': ballot_item_we_vote_ids_list,
    }
    return results


def retrieve_ballot_item_we_vote_ids_for_organization_static(
        organization, google_civic_election_id,
        stance_we_are_looking_for=SUPPORT,
        state_code='', friends_vs_public=PUBLIC_ONLY):
    """
    For this organization, we want to return a list of ballot_items that this organization has
    an opinion about for one election.
    """
    status = ''
    organization_found = True
    try:
        if not organization.id or not organization.we_vote_id:
            organization_found = False
    except Exception as e:
        organization_found = False

    if not organization_found:
        results = {
            'status':                           'RETRIEVE_BALLOT_ITEM_WE_VOTE_IDS_STATIC-ORGANIZATION_NOT_FOUND',
            'success':                          False,
            'count':                            0,
            'organization_id':                  0,
            'organization_we_vote_id':          "",
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'ballot_item_we_vote_ids_list':     [],
        }
        return results

    if not positive_value_exists(google_civic_election_id):
        results = {
            'status':                           'RETRIEVE_BALLOT_ITEM_WE_VOTE_IDS_STATIC-ELECTION_NOT_FOUND',
            'success':                          False,
            'count':                            0,
            'organization_id':                  0,
            'organization_we_vote_id':          "",
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'ballot_item_we_vote_ids_list':     [],
        }
        return results

    position_list_manager = PositionListManager()

    organization_id = organization.id
    organization_we_vote_id = organization.we_vote_id

    position_list_raw = position_list_manager.retrieve_all_positions_for_organization(
        organization_id, organization_we_vote_id, stance_we_are_looking_for, friends_vs_public,
        google_civic_election_id=google_civic_election_id, read_only=True)

    ballot_item_we_vote_ids_list = []
    for one_position in position_list_raw:
        # Collect the ballot_item_we_vote_id
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            # kind_of_ballot_item = CANDIDATE
            # ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            # if not positive_value_exists(one_position.contest_office_we_vote_id) \
            #         or not positive_value_exists(one_position.contest_office_name):
            #     missing_office_information = True
            # if not positive_value_exists(one_position.ballot_item_image_url_https):
            #     missing_ballot_item_image = True
            one_position_success = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            # kind_of_ballot_item = MEASURE
            # ballot_item_id = one_position.contest_measure_id
            ballot_item_we_vote_id = one_position.contest_measure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.contest_office_we_vote_id):
            # kind_of_ballot_item = OFFICE
            # ballot_item_id = one_position.contest_office_id
            ballot_item_we_vote_id = one_position.contest_office_we_vote_id
            one_position_success = True
        else:
            # kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            # ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            ballot_item_we_vote_ids_list.append(ballot_item_we_vote_id)

    status += 'RETRIEVE_BALLOT_ITEM_WE_VOTE_IDS-SUCCESS '
    success = True
    results = {
        'status':                       status,
        'success':                      success,
        'count':                        len(position_list_raw),
        'organization_id':              organization_id,
        'organization_we_vote_id':      organization_we_vote_id,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'ballot_item_we_vote_ids_list': ballot_item_we_vote_ids_list,
    }
    return results


def reset_all_position_image_details_from_candidate(candidate_campaign, twitter_profile_image_url_https):
    """
    Reset all position image urls PositionEntered and PositionForFriends from candidate details
    :param candidate_campaign:
    :param twitter_profile_image_url_https
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    reset_all_position_image_urls_results = []

    retrieve_public_positions = True
    public_position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
        retrieve_public_positions, candidate_campaign.id, candidate_campaign.we_vote_id)
    for position_object in public_position_list:
        reset_position_image_urls_results = position_manager.reset_position_image_details(
            position_object, twitter_profile_image_url_https)
        reset_all_position_image_urls_results.append(reset_position_image_urls_results)

    retrieve_public_positions = False
    friends_position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
        retrieve_public_positions, candidate_campaign.id, candidate_campaign.we_vote_id,
        retrieve_all_admin_override=True)
    for position_object in friends_position_list:
        reset_position_image_urls_results = position_manager.reset_position_image_details(
            position_object, twitter_profile_image_url_https)
        reset_all_position_image_urls_results.append(reset_position_image_urls_results)

    results = {
        'success':                     True,
        'reset_all_position_results':  reset_all_position_image_urls_results
    }
    return results


def update_all_position_details_from_candidate(candidate_campaign):
    """
    Update all position image urls PositionEntered and PositionForFriends from candidate details
    :param candidate_campaign:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    positions_updated_count = 0
    positions_not_updated_count = 0
    update_all_position_image_urls_results = []
    update_all_position_candidate_data_results = []

    retrieve_public_positions = True
    public_position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
        retrieve_public_positions, candidate_campaign.id, candidate_campaign.we_vote_id)
    for position_object in public_position_list:
        update_position_image_urls_results = position_manager.update_position_image_urls_from_candidate(
            position_object, candidate_campaign)
        update_all_position_image_urls_results.append(update_position_image_urls_results)
        update_position_candidate_data_results = position_manager.update_position_ballot_data_from_candidate(
            position_object, candidate_campaign)
        update_all_position_candidate_data_results.append(update_position_candidate_data_results)
        if update_position_image_urls_results['success'] and update_position_candidate_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1

    retrieve_public_positions = False
    friends_position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
        retrieve_public_positions, candidate_campaign.id, candidate_campaign.we_vote_id,
        retrieve_all_admin_override=True)
    for position_object in friends_position_list:
        update_position_image_urls_results = position_manager.update_position_image_urls_from_candidate(
            position_object, candidate_campaign)
        update_all_position_image_urls_results.append(update_position_image_urls_results)
        update_position_candidate_data_results = position_manager.update_position_ballot_data_from_candidate(
            position_object, candidate_campaign)
        update_all_position_candidate_data_results.append(update_position_candidate_data_results)
        if update_position_image_urls_results['success'] and update_position_candidate_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1

    update_all_position_results = [update_all_position_image_urls_results, update_all_position_candidate_data_results]

    results = {
        'success':                      True,
        'positions_updated_count':      positions_updated_count,
        'positions_not_updated_count':  positions_not_updated_count,
        'update_all_position_results':  update_all_position_results
    }
    return results


def update_all_position_details_from_contest_office(contest_office):
    """
    Update all position office name in PositionEntered and PositionForFriends from contest office details
    :param contest_office:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    positions_updated_count = 0
    positions_not_updated_count = 0
    update_all_position_office_data_results = []

    retrieve_public_positions = True
    stance_we_are_looking_for = ANY_STANCE
    public_position_list = position_list_manager.retrieve_all_positions_for_contest_office(
        retrieve_public_positions, contest_office.id, contest_office.we_vote_id,
        stance_we_are_looking_for, most_recent_only=True)
    for position_object in public_position_list:
        update_position_office_data_results = position_manager.update_position_office_data_from_contest_office(
            position_object, contest_office)
        if update_position_office_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1
        update_all_position_office_data_results.append(update_position_office_data_results)

    retrieve_public_positions = False
    friends_position_list = position_list_manager.retrieve_all_positions_for_contest_office(
        retrieve_public_positions, contest_office.id, contest_office.we_vote_id,
        stance_we_are_looking_for, most_recent_only=True)
    for position_object in friends_position_list:
        update_position_office_data_results = position_manager.update_position_office_data_from_contest_office(
            position_object, contest_office)
        if update_position_office_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1
        update_all_position_office_data_results.append(update_position_office_data_results)

    results = {
        'success':                      True,
        'positions_updated_count':      positions_updated_count,
        'positions_not_updated_count':  positions_not_updated_count,
        'update_all_position_results':  update_all_position_office_data_results
    }
    return results


def update_all_position_details_from_contest_measure(contest_measure):
    """
    Update all position measure name in PositionEntered and PositionForFriends from contest measure details
    :param contest_measure:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    positions_updated_count = 0
    positions_not_updated_count = 0
    update_all_position_measure_data_results = []

    retrieve_public_positions = True
    stance_we_are_looking_for = ANY_STANCE
    public_position_list = position_list_manager.retrieve_all_positions_for_contest_measure(
        retrieve_public_positions, contest_measure.id, contest_measure.we_vote_id,
        stance_we_are_looking_for, most_recent_only=True)
    for position_object in public_position_list:
        update_position_measure_data_results = position_manager.update_position_measure_data_from_contest_measure(
            position_object, contest_measure)
        if update_position_measure_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1
        update_all_position_measure_data_results.append(update_position_measure_data_results)

    retrieve_public_positions = False
    friends_position_list = position_list_manager.retrieve_all_positions_for_contest_measure(
        retrieve_public_positions, contest_measure.id, contest_measure.we_vote_id,
        stance_we_are_looking_for, most_recent_only=True)
    for position_object in friends_position_list:
        update_position_measure_data_results = position_manager.update_position_measure_data_from_contest_measure(
            position_object, contest_measure)
        if update_position_measure_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1
        update_all_position_measure_data_results.append(update_position_measure_data_results)

    results = {
        'success':                      True,
        'positions_updated_count':      positions_updated_count,
        'positions_not_updated_count':  positions_not_updated_count,
        'update_all_position_results':  update_all_position_measure_data_results
    }
    return results


def reset_position_entered_image_details_from_organization(organization, twitter_profile_image_url_https,
                                                           facebook_profile_image_url_https):
    """
    Reset all position image urls in PositionEntered from organization details
    :param organization:
    :param twitter_profile_image_url_https:
    :param facebook_profile_image_url_https:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    reset_all_position_org_data_results = []
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = PUBLIC_ONLY
    speaker_image_url_https = None
    if positive_value_exists(twitter_profile_image_url_https):
        speaker_image_url_https = twitter_profile_image_url_https
    elif positive_value_exists(facebook_profile_image_url_https):
        speaker_image_url_https = facebook_profile_image_url_https

    public_position_list = position_list_manager.retrieve_all_positions_for_organization(
        organization.id, organization.we_vote_id, stance_we_are_looking_for, friends_vs_public)
    for position_object in public_position_list:
        reset_position_image_urls_results = position_manager.reset_position_image_details(
            position_object, speaker_image_url_https=speaker_image_url_https)
        reset_all_position_org_data_results.append(reset_position_image_urls_results)

    results = {
        'success':                      True,
        'reset_all_position_results':  reset_all_position_org_data_results
    }
    return results


def update_position_entered_details_from_organization(organization):
    """
    Update all position image urls PositionEntered from organization details
    :param organization:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    positions_updated_count = 0
    positions_not_updated_count = 0
    update_all_position_image_urls_results = []
    update_all_position_org_data_results = []
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = PUBLIC_ONLY

    public_position_list = position_list_manager.retrieve_all_positions_for_organization(
        organization.id, organization.we_vote_id, stance_we_are_looking_for, friends_vs_public)
    for position_object in public_position_list:
        update_position_image_urls_results = position_manager.update_position_image_urls_from_organization(
            position_object, organization)
        update_all_position_image_urls_results.append(update_position_image_urls_results)
        update_position_org_data_results = position_manager.update_position_speaker_data_from_organization(
            position_object, organization)
        update_all_position_org_data_results.append(update_position_org_data_results)
        if update_position_image_urls_results['success'] and update_position_org_data_results['success']:
            positions_updated_count += 1
        else:
            positions_not_updated_count += 1

    update_all_position_results = [update_all_position_image_urls_results, update_all_position_org_data_results]
    results = {
        'success':                      True,
        'positions_updated_count':      positions_updated_count,
        'positions_not_updated_count':  positions_not_updated_count,
        'update_all_position_results':  update_all_position_results
    }
    return results


def reset_position_for_friends_image_details_from_voter(voter, twitter_profile_image_url_https,
                                                        facebook_profile_image_url_https):
    """
    Reset all position image urls in PositionForFriends from we vote image details
    :param voter:
    :param twitter_profile_image_url_https:
    :param facebook_profile_image_url_https:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = FRIENDS_ONLY
    speaker_image_url_https = None
    reset_all_position_image_urls_results = []
    if positive_value_exists(twitter_profile_image_url_https):
        speaker_image_url_https = twitter_profile_image_url_https
    elif positive_value_exists(facebook_profile_image_url_https):
        speaker_image_url_https = facebook_profile_image_url_https

    positions_for_voter_results = position_list_manager.retrieve_all_positions_for_voter(
        voter.id, voter.we_vote_id, stance_we_are_looking_for, friends_vs_public)
    if positions_for_voter_results['position_list_found']:
        friends_position_list = positions_for_voter_results['position_list']
        for position_object in friends_position_list:

            reset_position_image_urls_results = position_manager.reset_position_image_details(
                position_object, speaker_image_url_https=speaker_image_url_https)
            reset_all_position_image_urls_results.append(reset_position_image_urls_results)
    results = {
        'success':                      True,
        'reset_all_position_results':   reset_all_position_image_urls_results
    }
    return results


def update_position_for_friends_details_from_voter(voter):
    """
    Update all position image urls PositionForFriends from voter details
    :param voter:
    :return:
    """
    position_list_manager = PositionListManager()
    position_manager = PositionManager()
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = FRIENDS_ONLY
    positions_updated_count = 0
    positions_not_updated_count = 0

    positions_for_voter_results = position_list_manager.retrieve_all_positions_for_voter(
        voter.id, voter.we_vote_id, stance_we_are_looking_for, friends_vs_public)

    if positions_for_voter_results['position_list_found']:
        friends_position_list = positions_for_voter_results['position_list']
        for position_object in friends_position_list:
            update_position_image_urls_results = position_manager.update_position_image_urls_from_voter(
                position_object, voter)
            if update_position_image_urls_results['success']:
                positions_updated_count += 1
            else:
                positions_not_updated_count += 1

    results = {
        'success':                      True,
        'positions_updated_count':      positions_updated_count,
        'positions_not_updated_count':  positions_not_updated_count,
    }
    return results


def update_or_create_position_network_score_wrapper(voter_id, voter_we_vote_id, one_position):
    status = ""
    position_manager = PositionManager()
    friends_only_position_updated = False
    public_position_updated = False

    if one_position.is_support_or_positive_rating():
        support_or_oppose = True
    elif one_position.is_oppose_or_negative_rating():
        support_or_oppose = False
    else:
        # If not support or oppose, exit
        status += "UPDATE_POSITION_NETWORK_SCORE_WRAPPER_NOT_SUPPORT_OR_OPPOSE "
        results = {
            'success': True,
            'status': status,
            'google_civic_election_id': one_position.google_civic_election_id,
            'position_network_score_updated': friends_only_position_updated or public_position_updated,
            'friends_only_position_updated': friends_only_position_updated,
            'public_position_updated': public_position_updated,
        }
        return results

    friend_voter_we_vote_id = None
    organization_we_vote_id = None
    voter_looking_at_self = False
    if one_position.is_public_position():
        organization_we_vote_id = one_position.organization_we_vote_id
    elif one_position.is_friends_only_position():
        friend_voter_we_vote_id = one_position.voter_we_vote_id
        voter_looking_at_self = voter_we_vote_id == friend_voter_we_vote_id
    else:
        status += "UPDATE_POSITION_NETWORK_SCORE_WRAPPER-MISSING_ORG_AND_FRIEND "
        results = {
            'success': True,
            'status': status,
            'google_civic_election_id': one_position.google_civic_election_id,
            'position_network_score_updated': friends_only_position_updated or public_position_updated,
            'friends_only_position_updated': friends_only_position_updated,
            'public_position_updated': public_position_updated,
        }
        return results

    speaker_display_name = one_position.speaker_display_name
    if voter_looking_at_self and speaker_display_name.startswith("Voter-"):
        speaker_display_name = "You"

    if positive_value_exists(one_position.candidate_campaign_we_vote_id):
        # Add entry to position_network_score table
        ignore_measure_we_vote_id = None

        update_results = position_manager.update_or_create_position_network_score(
            voter_id, voter_we_vote_id,
            one_position.google_civic_election_id,
            organization_we_vote_id, friend_voter_we_vote_id,
            speaker_display_name,
            one_position.candidate_campaign_we_vote_id, ignore_measure_we_vote_id,
            support_or_oppose)
        results = {
            'success': True,
            'status': status,
            'google_civic_election_id': one_position.google_civic_election_id,
            'position_network_score_updated': update_results['position_network_score_updated'],
            'friends_only_position_updated':
            friend_voter_we_vote_id and update_results['position_network_score_updated'],
            'public_position_updated': organization_we_vote_id and update_results['position_network_score_updated'],
        }
        return results
    elif positive_value_exists(one_position.contest_measure_we_vote_id):
        # Add entry to position_network_score table
        ignore_candidate_we_vote_id = None

        update_results = position_manager.update_or_create_position_network_score(
            voter_id, voter_we_vote_id,
            one_position.google_civic_election_id,
            organization_we_vote_id, friend_voter_we_vote_id,
            speaker_display_name,
            ignore_candidate_we_vote_id, one_position.contest_measure_we_vote_id,
            support_or_oppose)
        results = {
            'success': True,
            'status': status,
            'google_civic_election_id': one_position.google_civic_election_id,
            'position_network_score_updated': update_results['position_network_score_updated'],
            'friends_only_position_updated':
            friend_voter_we_vote_id and update_results['position_network_score_updated'],
            'public_position_updated': organization_we_vote_id and update_results['position_network_score_updated'],
        }
        return results
    else:
        status += "UPDATE_POSITION_NETWORK_SCORE_WRAPPER_NOT_CANDIDATE_OR_MEASURE "
        public_position_updated = False
        results = {
            'success': True,
            'status': status,
            'google_civic_election_id': one_position.google_civic_election_id,
            'position_network_score_updated': friends_only_position_updated or public_position_updated,
            'friends_only_position_updated': friends_only_position_updated,
            'public_position_updated': public_position_updated,
        }
        return results

