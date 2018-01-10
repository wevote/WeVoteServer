# pledge_to_vote/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PledgeToVoteManager
from follow.models import FollowOrganizationManager
from friend.models import FriendManager
from organization.models import OrganizationManager
from position.models import ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING, \
    FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC, PositionForFriends, PositionListManager, PositionManager
from voter.models import VoterManager
from voter_guide.models import VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def pledge_to_vote_with_voter_guide_for_api(voter_device_id, voter_guide_we_vote_id, delete_pledge,
                                            pledge_to_vote_we_vote_id=""):
    """
    pledgeToVoteWithVoterGuide
    :param voter_device_id:
    :param voter_guide_we_vote_id:
    :param delete_pledge:
    :param pledge_to_vote_we_vote_id:
    :return:
    """
    status = ""
    success = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                  False,
            'delete_pledge':            delete_pledge,
            'google_civic_election_id': 0,
            'organization_we_vote_id':  "",
            'pledge_statistics_found':  False,
            'pledge_goal':              0,
            'pledge_count':             0,
            'voter_device_id':          voter_device_id,
            'voter_guide_we_vote_id':   voter_guide_we_vote_id,
            'voter_has_pledged':        False,
        }
        return error_results

    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    voter_guide_manager = VoterGuideManager()
    voter_guide_id = 0
    results = voter_guide_manager.retrieve_voter_guide(voter_guide_id, voter_guide_we_vote_id)
    if not positive_value_exists(results['voter_guide_found']):
        error_results = {
            'status':                   "VOTER_GUIDE_NOT_FOUND",
            'success':                  False,
            'delete_pledge':            delete_pledge,
            'google_civic_election_id': 0,
            'organization_we_vote_id':  "",
            'pledge_statistics_found':  False,
            'pledge_goal':              0,
            'pledge_count':             0,
            'voter_device_id':          voter_device_id,
            'voter_guide_we_vote_id':   voter_guide_we_vote_id,
            'voter_has_pledged':        False,
        }
        return error_results

    voter_guide = results['voter_guide']

    pledge_to_vote_manager = PledgeToVoteManager()
    take_same_positions = True
    visible_to_public = True
    pledge_save_results = pledge_to_vote_manager.update_or_create_pledge_to_vote(
        voter_we_vote_id, voter_guide_we_vote_id, voter_guide.organization_we_vote_id,
        voter_guide.google_civic_election_id,
        take_same_positions, visible_to_public, pledge_to_vote_we_vote_id)
    status += pledge_save_results['status']

    success = pledge_save_results['success']
    voter_has_pledged = pledge_save_results['voter_has_pledged']

    # Now return updated stats for the pledge bar
    pledge_results = pledge_to_vote_manager.retrieve_pledge_statistics(voter_guide_we_vote_id)
    status += pledge_results['status']
    pledge_statistics_found = pledge_results['pledge_statistics_found']
    pledge_goal = pledge_results['pledge_goal']
    pledge_count = pledge_results['pledge_count']

    # And save the the updated pledge_count in the VoterGuide
    voter_guide.pledge_count = pledge_count
    voter_guide_manager.save_voter_guide_object(voter_guide)

    # Make sure we are following this organization
    organization_manager = OrganizationManager()
    # Retrieve the organization the voter_guide is for, so we have the organization_id
    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
        voter_guide.organization_we_vote_id)
    if organization_results['organization_found']:
        organization = organization_results['organization']
        voter_guide_organization_id = organization.id
    else:
        voter_guide_organization_id = 0

    follow_manager = FollowOrganizationManager()
    results = follow_manager.toggle_on_voter_following_organization(
        voter_id, voter_guide_organization_id, voter_guide.organization_we_vote_id, voter.linked_organization_we_vote_id)
    status += results['status']

    # Now support or oppose everything this org does for this election

    # Default to copying the public position
    friends_vs_public = PUBLIC_ONLY

    # ...but check to see if the voter is friends with this organization
    friend_manager = FriendManager()
    voter_for_organization_results = voter_manager.retrieve_voter_by_organization_we_vote_id(
        voter_guide.organization_we_vote_id)
    if voter_for_organization_results['voter_found']:
        voter_for_organization = voter_for_organization_results['voter']
        results = friend_manager.retrieve_current_friend(voter.we_vote_id, voter_for_organization.we_vote_id)
        # Is a friend? If so, copy all positions
        if results['current_friend_found']:
            friends_vs_public = FRIENDS_AND_PUBLIC

    position_manager = PositionManager()
    position_list_manager = PositionListManager()
    # Retrieve all of the positions for current election
    show_positions_current_voter_election = True
    exclude_positions_current_voter_election = False
    position_list = position_list_manager.retrieve_all_positions_for_organization(
        organization_id=voter_guide_organization_id,
        organization_we_vote_id=voter_guide.organization_we_vote_id,
        stance_we_are_looking_for=ANY_STANCE,
        friends_vs_public=friends_vs_public,
        show_positions_current_voter_election=show_positions_current_voter_election,
        exclude_positions_current_voter_election=exclude_positions_current_voter_election,
        voter_device_id=voter_device_id,
        google_civic_election_id=voter_guide.google_civic_election_id)

    for organization_position in position_list:
        # Check to see if voter already has a position on this candidate or measure
        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id="",
            organization_id=0,
            organization_we_vote_id=voter.linked_organization_we_vote_id,
            voter_id=voter.id,
            contest_office_id=organization_position.contest_office_id,
            candidate_campaign_id=organization_position.candidate_campaign_id,
            contest_measure_id=organization_position.contest_measure_id,
            google_civic_election_id=voter_guide.google_civic_election_id)
        if results['position_found']:
            if results['is_support_or_positive_rating'] or \
                    results['is_oppose_or_negative_rating']:
                # If here there has been a conflict with this position, and we can't update automatically
                # If information only, we do update
                pass
            else:
                voter_position = results['position']
                try:
                    voter_position.stance = organization_position.stance
                    voter_position.save()
                except Exception as e:
                    # handle_record_not_saved_exception(e, logger=logger)
                    status += 'NEW_STANCE_COULD_NOT_BE_SAVED '
        else:
            # Create a new position
            voter_organization_id = 0
            if positive_value_exists(voter.linked_organization_we_vote_id):
                organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    voter.linked_organization_we_vote_id)
                if organization_results['organization_found']:
                    organization = organization_results['organization']
                    voter_organization_id = organization.id

            position_on_stage = PositionForFriends(
                voter_id=voter.id,
                voter_we_vote_id=voter.we_vote_id,
                candidate_campaign_id=organization_position.candidate_campaign_id,
                candidate_campaign_we_vote_id=organization_position.candidate_campaign_we_vote_id,
                contest_measure_id=organization_position.contest_measure_id,
                contest_measure_we_vote_id=organization_position.contest_measure_we_vote_id,
                contest_office_id=organization_position.contest_office_id,
                contest_office_we_vote_id=organization_position.contest_office_we_vote_id,
                google_civic_election_id=organization_position.google_civic_election_id,
                state_code=organization_position.state_code,
                organization_id=voter_organization_id,
                organization_we_vote_id=voter.linked_organization_we_vote_id,
                ballot_item_display_name=organization_position.ballot_item_display_name,
                speaker_display_name=voter.get_full_name(True),
                stance=organization_position.stance,
                # We are not currently supporting vote smart ratings
                # vote_smart_time_span=organization_position.vote_smart_time_span,
                # vote_smart_rating_id=organization_position.vote_smart_rating_id,
                # vote_smart_rating=organization_position.vote_smart_rating,
                # vote_smart_rating_name=organization_position.vote_smart_rating_name,
            )
            # Save again so the we_vote_id is created
            position_on_stage.save()
            status += "NEW_POSITION_SAVED "

    results = {
        'status':                   status,
        'success':                  success,
        'delete_pledge':            delete_pledge,
        'google_civic_election_id': voter_guide.google_civic_election_id,
        'organization_we_vote_id':  voter_guide.organization_we_vote_id,
        'pledge_statistics_found':  pledge_statistics_found,
        'pledge_goal':              pledge_goal,
        'pledge_count':             pledge_count,
        'voter_device_id':          voter_device_id,
        'voter_guide_we_vote_id':   voter_guide_we_vote_id,
        'voter_has_pledged':        voter_has_pledged,
    }
    return results
