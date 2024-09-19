# voter/controllers_changes.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from wevote_functions.functions import positive_value_exists
from candidate.models import CandidateChangeLog
from voter.models import VoterChangeLog


def move_candidate_change_log_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_CANDIDATE_CHANGE_LOG-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_we_vote_id':    from_voter_we_vote_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'entries_moved':            entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_CANDIDATE_CHANGE_LOG-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_we_vote_id':    from_voter_we_vote_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'entries_moved':            entries_moved,
        }
        return results

    # ######################
    # Migrations
    try:
        entries_moved += CandidateChangeLog.objects\
            .filter(changed_by_voter_we_vote_id=from_voter_we_vote_id)\
            .update(changed_by_voter_we_vote_id=to_voter_we_vote_id)

        entries_deleted = \
            CandidateChangeLog.objects.filter(changed_by_voter_we_vote_id=from_voter_we_vote_id).delete()
        status += "ENTRIES_DELETED: " + str(entries_deleted) + " "
    except Exception as e:
        status += "FAILED-CANDIDATE_CHANGE_LOG_UPDATE: " + str(e) + " "
        success = False

    results = {
        'status':                   status,
        'success':                  success,
        'from_voter_we_vote_id':    from_voter_we_vote_id,
        'to_voter_we_vote_id':      to_voter_we_vote_id,
        'entries_moved':            entries_moved,
    }
    return results


def move_voter_change_log_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_VOTER_CHANGE_LOG-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'to_voter_we_vote_id':              to_voter_we_vote_id,
            'entries_moved':   entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_VOTER_CHANGE_LOG-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'to_voter_we_vote_id':              to_voter_we_vote_id,
            'entries_moved':   entries_moved,
        }
        return results

    # ######################
    # Migrations
    try:
        entries_moved += VoterChangeLog.objects\
            .filter(voter_we_vote_id=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)

        entries_deleted = \
            VoterChangeLog.objects.filter(voter_we_vote_id=from_voter_we_vote_id).delete()
        status += "ENTRIES_DELETED: " + str(entries_deleted) + " "
    except Exception as e:
        status += "FAILED-VOTER_CHANGE_LOG_UPDATE: " + str(e) + " "
        success = False

    results = {
        'status':                   status,
        'success':                  success,
        'from_voter_we_vote_id':    from_voter_we_vote_id,
        'to_voter_we_vote_id':      to_voter_we_vote_id,
        'entries_moved':            entries_moved,
    }
    return results
