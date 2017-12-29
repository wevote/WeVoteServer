# pledge_to_vote/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PledgeToVoteManager
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
