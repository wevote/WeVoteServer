# challenge/controllers_scoring.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Challenge, ChallengeManager, ChallengeParticipant
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

POINT_VALUES_PER_ATTRIBUTE = {
    'invitees_count':           1,
    'invitees_who_joined':      10,
    'invitees_who_viewed':      5,
    # 'invitees_who_viewed_plus': 0,
    'invites_sent_count':       2,
    'participant_photo_exists': 5,
}

logger = wevote_functions.admin.get_logger(__name__)


def refresh_participant_points_for_challenge(
        challenge_we_vote_id='',
        challenge_participant_list=[]):
    status = ''
    success = True

    if not challenge_participant_list or len(challenge_participant_list) == 0:
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
            challenge_participant_list = []
        else:
            challenge_participant_list = results['participant_list']

    participants_with_points_changed_list = []
    for challenge_participant in challenge_participant_list:
        generate_results = calculate_points_from_challenge_participant_object(
            challenge_participant=challenge_participant)
        if generate_results['success'] and generate_results['score_changed']:
            participants_with_points_changed_list.append(generate_results['challenge_participant'])
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
    participant_points = 0
    score_changed = False
    status = ''
    success = True

    if not challenge_participant or not hasattr(challenge_participant, 'invite_text_for_friends'):
        success = False
        status += "VALID_CHALLENGE_PARTICIPANT_OBJECT_MISSING "
        results = {
            'challenge_participant':    challenge_participant,
            'score_changed':            score_changed,
            'status':                   status,
            'success':                  success,
        }
        return results

    participant_points += challenge_participant.invitees_count * POINT_VALUES_PER_ATTRIBUTE['invitees_count']
    participant_points += challenge_participant.invitees_who_joined * POINT_VALUES_PER_ATTRIBUTE['invitees_who_joined']
    participant_points += challenge_participant.invitees_who_viewed * POINT_VALUES_PER_ATTRIBUTE['invitees_who_viewed']
    # participant_points += \
    #     challenge_participant.invitees_who_viewed_plus * POINT_VALUES_PER_ATTRIBUTE['invitees_who_viewed_plus']
    participant_points += challenge_participant.invites_sent_count * POINT_VALUES_PER_ATTRIBUTE['invites_sent_count']
    if positive_value_exists(challenge_participant.we_vote_hosted_profile_image_url_medium):
        participant_points += POINT_VALUES_PER_ATTRIBUTE['participant_photo_exists']

    if participant_points != challenge_participant.points:
        score_changed = True
        challenge_participant.points = participant_points

    results = {
        'challenge_participant':    challenge_participant,
        'score_changed':            score_changed,
        'status':                   status,
        'success':                  success,
    }
    return results
