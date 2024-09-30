# challenge/controllers_scoring.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Challenge, ChallengeManager, ChallengeParticipant
from django.contrib import messages
from django.db.models import Q
from follow.models import FOLLOW_DISLIKE, FOLLOWING, FollowOrganizationManager
from position.models import OPPOSE, SUPPORT
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import generate_date_as_integer, get_current_date_as_integer, DATE_FORMAT_YMD_HMS

logger = wevote_functions.admin.get_logger(__name__)


def refresh_participant_points_for_challenge(
        challenge_we_vote_id='',
        challenge_participant_list=[]):
    status = ''
    success = True

    if len(challenge_participant_list) > 0:
        challenge_manager = ChallengeManager()
        results = challenge_manager.retrieve_challenge_participant_list(
            challenge_we_vote_id=challenge_we_vote_id,
            read_only=False,
        )
        status += results['status']
        if not results['success']:
            status += "CHALLENGE_PARTICIPANT_LIST_RETRIEVE_ERROR "
            results = {
                'status':                       status,
                'success':                      False,
                'challenge_participant_list':   [],
                'challenge_we_vote_id':         challenge_we_vote_id,
                'voter_we_vote_id':             '',
            }
            return results
        elif not results['participant_list_found']:
            status += "CHALLENGE_PARTICIPANT_LIST_NOT_FOUND: "
        else:
            challenge_participant_list = results['participant_list']

    participants_with_points_changed_list = []
    for challenge_participant in challenge_participant_list:
        generate_results = calculate_points_from_challenge_participant_object(
            challenge_participant=challenge_participant)
        if generate_results['success']:
            participants_with_points_changed_list.append(generate_results['challenge_participant_dict'])
    if len(participants_with_points_changed_list) > 0:
        try:
            rows_updated = ChallengeParticipant.objects.bulk_update(
                participants_with_points_changed_list,
                ['points'])
            status += "BULK_CHALLENGE_PARTICIPANT_UPDATES: " + str(rows_updated) + " "
        except Exception as e:
            status += "BULK_CHALLENGE_PARTICIPANT_UPDATE_FAILED: " + str(e)
            success = False

    results = {
        'status':                       status,
        'success':                      success,
        'challenge_participant_list':   challenge_participant_list,
        'challenge_we_vote_id':         challenge_we_vote_id,
    }
    return results


def calculate_points_from_challenge_participant_object(challenge_participant=None):
    results = {
        'status':                       status,
        'success':                      True,
        'challenge_participant_list':   challenge_participant_list,
        'challenge_we_vote_id':         challenge_we_vote_id,
    }
    return results
