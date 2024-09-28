# challenge/controllers_participant.py
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


def challenge_participant_retrieve_for_api(  # challengeParticipantRetrieve
        voter_device_id='',
        challenge_we_vote_id=''):
    status = ''
    voter_signed_in_with_email = False

    dict_results = generate_challenge_participant_dict_from_challenge_participant_object()
    error_results = dict_results['challenge_participant_dict']

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        error_results['status'] = status
        error_results['success'] = False
        return error_results

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge_participant(
        challenge_we_vote_id=challenge_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        read_only=True,
    )
    status += results['status']
    if not results['success']:
        status += "CHALLENGE_PARTICIPANT_RETRIEVE_ERROR "
        error_results['status'] = status
        error_results['success'] = False
        return error_results
    elif not results['challenge_participant_found']:
        status += "CHALLENGE_PARTICIPANT_NOT_FOUND: "
        status += results['status'] + " "
        error_results['status'] = status
        error_results['success'] = True
        return error_results

    challenge_participant = results['challenge_participant']
    dict_results = generate_challenge_participant_dict_from_challenge_participant_object(
        challenge_participant=challenge_participant)
    status += dict_results['status']
    if dict_results['success']:
        results = dict_results['challenge_participant_dict']
        results['status'] = status
        results['success'] = True
        return results
    else:
        status += "CHALLENGE_INVITEE_GENERATE_RESULTS_ERROR "
        error_results['status'] = status
        return error_results


def challenge_participant_list_retrieve_for_api(  # challengeParticipantListRetrieve
        voter_device_id='',
        challenge_we_vote_id=''):
    status = ''

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_we_vote_id = voter.we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'challenge_participant_list':   [],
            'challenge_we_vote_id':         challenge_we_vote_id,
            'voter_we_vote_id':             '',
        }
        return results

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge_participant_list(
        challenge_we_vote_id=challenge_we_vote_id,
        read_only=True,
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
        status += results['status'] + " "

    challenge_participant_list = []
    for challenge_participant in results['participant_list']:
        generate_results = generate_challenge_participant_dict_from_challenge_participant_object(
            challenge_participant=challenge_participant)
        if generate_results['success']:
            challenge_participant_list.append(generate_results['challenge_participant_dict'])
    results = {
        'status':                       status,
        'success':                      True,
        'challenge_participant_list':   challenge_participant_list,
        'challenge_we_vote_id':         challenge_we_vote_id,
        'voter_we_vote_id':             voter_we_vote_id,
    }
    return results


def challenge_participant_save_for_api(  # challengeParticipantSave
        challenge_we_vote_id='',
        visible_to_public=False,
        visible_to_public_changed=False,
        voter_device_id=''):
    challenge_participant = None
    status = ''
    success = True

    generate_results = generate_challenge_participant_dict_from_challenge_participant_object(challenge_participant)
    error_results = generate_results['challenge_participant_dict']

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']

        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = error_results
        results['status'] = status
        return results
    # To participate in a challenge, voter must be signed in
    if not voter.is_signed_in():
        status += "PARTICIPANT_NOT_SIGNED_IN "
        results = error_results
        results['status'] = status
        return results

    if not positive_value_exists(challenge_we_vote_id):
        status += "CHALLENGE_WE_VOTE_ID_REQUIRED "
        results = error_results
        results['status'] = status
        return results

    challenge_manager = ChallengeManager()
    update_values = {
        'visible_to_public':                visible_to_public,
        'visible_to_public_changed':        visible_to_public_changed,
    }
    create_results = challenge_manager.update_or_create_challenge_participant(
        challenge_we_vote_id=challenge_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        organization_we_vote_id=linked_organization_we_vote_id,
        update_values=update_values,
    )

    # if create_results['challenge_participant_found']:
    #     challenge_participant = create_results['challenge_participant']
    #
    #     results = challenge_manager.retrieve_challenge(
    #         challenge_we_vote_id=challenge_we_vote_id,
    #         read_only=True,
    #     )
    #     notice_seed_statement_text = ''
    #     if results['challenge_found']:
    #         challenge = results['challenge']
    #         notice_seed_statement_text = challenge.challenge_title
    #
    #     # TODO
    #     activity_results = update_or_create_activity_notice_seed_for_challenge_participant_initial_response(
    #         challenge_we_vote_id=challenge_participant.challenge_we_vote_id,
    #         visibility_is_public=challenge_participant.visible_to_public,
    #         speaker_name=challenge_participant.participant_name,
    #         speaker_organization_we_vote_id=challenge_participant.organization_we_vote_id,
    #         speaker_voter_we_vote_id=challenge_participant.voter_we_vote_id,
    #         speaker_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
    #         speaker_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny,
    #         statement_text=notice_seed_statement_text)
    #     status += activity_results['status']

    status += create_results['status']
    if create_results['challenge_participant_found']:
        count_results = challenge_manager.update_challenge_participants_count(challenge_we_vote_id)

        challenge_participant = create_results['challenge_participant']
        generate_results = generate_challenge_participant_dict_from_challenge_participant_object(challenge_participant)
        challenge_participant_results = generate_results['challenge_participant_dict']
        status += generate_results['status']
        challenge_participant_results['status'] = status
        challenge_participant_results['success'] = generate_results['success']
        return challenge_participant_results
    else:
        status += "CHALLENGE_PARTICIPANT_SAVE_ERROR "
        results = error_results
        results['status'] = status
        results['success'] = False
        return results


def move_participant_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = True
    participant_entries_moved = 0
    participant_entries_not_moved = 0
    error_results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'participant_entries_moved': participant_entries_moved,
        'participant_entries_not_moved': participant_entries_not_moved,
    }

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_PARTICIPANT_ENTRIES_TO_ANOTHER_VOTER-" \
                  "Missing either from_voter_we_vote_id or to_voter_we_vote_id "
        error_results['status'] = status
        return error_results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_PARTICIPANT_ENTRIES_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        error_results['status'] = status
        return error_results

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge_participant_list(
        voter_we_vote_id=from_voter_we_vote_id,
        limit=0,
        require_custom_message_for_friends=False,
        require_visible_to_public=False,
        require_not_blocked_by_we_vote=False,
        read_only=False)
    from_participant_list = results['participant_list']
    results = challenge_manager.retrieve_challenge_participant_list(
        voter_we_vote_id=to_voter_we_vote_id,
        limit=0,
        require_custom_message_for_friends=False,
        require_visible_to_public=False,
        require_not_blocked_by_we_vote=False,
        read_only=False)
    to_participant_list = results['participant_list']
    to_participant_we_vote_id_list = []
    for to_participant in to_participant_list:
        if to_participant.voter_we_vote_id not in to_participant_we_vote_id_list:
            to_participant_we_vote_id_list.append(to_participant.voter_we_vote_id)

    bulk_update_list = []
    for from_participant_entry in from_participant_list:
        # See if the "to_voter" already has an entry for this issue
        if from_participant_entry.voter_we_vote_id in to_participant_we_vote_id_list:
            # Do not move this entry, since we already have an entry for this voter_we_vote_id the to_voter's list
            pass
        else:
            # Change the from_voter_we_vote_id to to_voter_we_vote_id
            try:
                from_participant_entry.voter_we_vote_id = to_voter_we_vote_id
                if positive_value_exists(to_organization_we_vote_id):
                    from_participant_entry.organization_we_vote_id = to_organization_we_vote_id
                bulk_update_list.append(from_participant_entry)
                participant_entries_moved += 1
            except Exception as e:
                participant_entries_not_moved += 1
                status += "FAILED_FROM_PARTICIPANT_SAVE: " + str(e) + " "
                success = False
    if positive_value_exists(participant_entries_moved):
        try:
            ChallengeParticipant.objects.bulk_update(bulk_update_list, ['organization_we_vote_id', 'voter_we_vote_id'])
        except Exception as e:
            status += "FAILED_BULK_PARTICIPANT_SAVE: " + str(e) + " "
            success = False

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'participant_entries_moved':        participant_entries_moved,
        'participant_entries_not_moved':    participant_entries_not_moved,
    }
    return results


def refresh_challenge_participants_count_for_challenge_we_vote_id_list(challenge_we_vote_id_list=[]):
    error_message_to_print = ''
    status = ''
    success = True
    update_message = ''
    challenges_need_to_be_updated = False
    challenge_manager = ChallengeManager()
    challenge_bulk_update_list = []
    challenge_updates_made = 0
    if len(challenge_we_vote_id_list) > 0:
        follow_organization_manager = FollowOrganizationManager()
        queryset = Challenge.objects.all()  # Cannot be readonly because of bulk_update below
        queryset = queryset.filter(we_vote_id__in=challenge_we_vote_id_list)
        challenge_list = list(queryset)
        for one_challenge in challenge_list:
            changes_found = False
            opposers_count = 0
            if positive_value_exists(one_challenge.politician_we_vote_id):
                if positive_value_exists(one_challenge.organization_we_vote_id):
                    opposers_count = follow_organization_manager.fetch_follow_organization_count(
                        following_status=FOLLOW_DISLIKE,
                        organization_we_vote_id_being_followed=one_challenge.organization_we_vote_id)

                    participants_count = follow_organization_manager.fetch_follow_organization_count(
                        following_status=FOLLOWING,
                        organization_we_vote_id_being_followed=one_challenge.organization_we_vote_id)
                else:
                    error_message_to_print += "CHALLENGE_MISSING_ORGANIZATION: " + str(one_challenge.we_vote_id) + " "
                    continue
            else:
                participants_count = challenge_manager.fetch_challenge_participant_count(
                    challenge_we_vote_id=one_challenge.we_vote_id)
            if opposers_count != one_challenge.opposers_count:
                one_challenge.opposers_count = opposers_count
                changes_found = True
            if participants_count != one_challenge.participants_count:
                one_challenge.participants_count = participants_count
                changes_found = True
            if changes_found:
                challenge_bulk_update_list.append(one_challenge)
                challenges_need_to_be_updated = True
                challenge_updates_made += 1
    if challenges_need_to_be_updated:
        try:
            Challenge.objects.bulk_update(challenge_bulk_update_list, ['opposers_count', 'participants_count'])
            update_message += \
                "{challenge_updates_made:,} Challenge entries updated with fresh participants_count, " \
                "".format(challenge_updates_made=challenge_updates_made)
        except Exception as e:
            status += "ERROR with Challenge.objects.bulk_update: {e}, ".format(e=e)
            error_message_to_print += "ERROR with Challenge.objects.bulk_update: {e}, ".format(e=e)
            success = False

    results = {
        'error_message_to_print':   error_message_to_print,
        'status':                   status,
        'success':                  success,
        'update_message':           update_message,
    }
    return results


def generate_challenge_participant_dict_from_challenge_participant_object(challenge_participant=None):
    status = ""
    success = True

    participant_dict = {
        'challenge_we_vote_id': '',
        'date_joined': '',
        'date_last_changed': '',
        'friends_invited': '',
        'friends_who_joined': '',
        'friends_who_viewed': '',
        'friends_who_viewed_plus': '',
        'organization_we_vote_id': '',
        'participant_name': '',
        'points': '',
        'rank': '',
        'visible_to_public': '',
        'voter_we_vote_id': '',
        'we_vote_hosted_profile_image_url_medium': '',
        'we_vote_hosted_profile_image_url_tiny': '',
    }

    if not hasattr(challenge_participant, 'visible_to_public'):
        status += "VALID_CHALLENGE_PARTICIPANT_OBJECT_MISSING "
        results = {
            'challenge_participant_dict': participant_dict,
            'status': status,
            'success': False,
        }
        return results

    # If smaller sizes weren't stored, use large image
    if challenge_participant:
        if challenge_participant.we_vote_hosted_profile_image_url_medium:
            we_vote_hosted_profile_image_url_medium = challenge_participant.we_vote_hosted_profile_image_url_medium
        else:
            we_vote_hosted_profile_image_url_medium = ''
        if challenge_participant.we_vote_hosted_profile_image_url_tiny:
            we_vote_hosted_profile_image_url_tiny = challenge_participant.we_vote_hosted_profile_image_url_tiny
        else:
            we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_medium
    else:
        we_vote_hosted_profile_image_url_medium = ''
        we_vote_hosted_profile_image_url_tiny = ''

    date_last_changed_string = ''
    date_joined_string = ''
    try:
        date_last_changed_string = challenge_participant.date_last_changed.strftime(DATE_FORMAT_YMD_HMS)
        date_joined_string = challenge_participant.date_joined.strftime(DATE_FORMAT_YMD_HMS)
    except Exception as e:
        status += "DATE_CONVERSION_ERROR: " + str(e) + " "
    participant_dict['challenge_we_vote_id'] = challenge_participant.challenge_we_vote_id
    participant_dict['date_joined'] = date_joined_string
    participant_dict['date_last_changed'] = date_last_changed_string
    participant_dict['friends_invited'] = challenge_participant.friends_invited
    participant_dict['friends_who_joined'] = challenge_participant.friends_who_joined
    participant_dict['friends_who_viewed'] = challenge_participant.friends_who_viewed
    participant_dict['friends_who_viewed_plus'] = challenge_participant.friends_who_viewed_plus
    participant_dict['organization_we_vote_id'] = challenge_participant.organization_we_vote_id
    participant_dict['participant_name'] = challenge_participant.participant_name
    participant_dict['points'] = challenge_participant.points
    participant_dict['rank'] = challenge_participant.rank
    participant_dict['visible_to_public'] = challenge_participant.visible_to_public
    participant_dict['voter_we_vote_id'] = challenge_participant.voter_we_vote_id
    participant_dict['we_vote_hosted_profile_image_url_medium'] = we_vote_hosted_profile_image_url_medium
    participant_dict['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny

    results = {
        'challenge_participant_dict':   participant_dict,
        'status':                       status,
        'success':                      success,
    }
    return results


def delete_challenge_participants_after_positions_removed(
        request,
        friends_only_positions=False,
        state_code=''):
    # Create default variables needed below
    challenge_participant_entries_deleted_count = 0
    challenge_we_vote_id_list_to_refresh = []
    number_to_delete = 20  # 1000
    from position.models import PositionEntered, PositionForFriends
    position_objects_to_set_challenge_participant_created_true = []  # Field is 'challenge_participant_created'
    position_updates_made = 0
    position_we_vote_id_list_to_remove_from_challenge_participants = []
    challenge_participant_id_list_to_delete = []
    status = ''
    success = True
    # timezone = pytz.timezone("America/Los_Angeles")
    # datetime_now = timezone.localize(datetime.now())
    # datetime_now = generate_localized_datetime_from_obj()[1]
    # date_today_as_integer = convert_date_to_date_as_integer(datetime_now)
    date_today_as_integer = get_current_date_as_integer()
    update_message = ''

    try:
        if positive_value_exists(friends_only_positions):
            position_query = PositionForFriends.objects.all()  # Cannot be readonly, since we bulk_update at the end
        else:
            position_query = PositionEntered.objects.all()  # Cannot be readonly, since we bulk_update at the end
        position_query = position_query.exclude(challenge_participant_created=True)
        position_query = position_query.exclude(stance=SUPPORT)
        position_query = position_query.filter(
            Q(position_ultimate_election_not_linked=True) |
            Q(position_ultimate_election_date__gte=date_today_as_integer)
        )
        if positive_value_exists(state_code):
            position_query = position_query.filter(state_code__iexact=state_code)
        total_to_convert = position_query.count()
        position_list_with_support_removed = list(position_query[:number_to_delete])
    except Exception as e:
        position_list_with_support_removed = []
        total_to_convert = 0
        update_message += "POSITION_LIST_WITH_SUPPORT_RETRIEVE_FAILED: " + str(e) + " "

    for one_position in position_list_with_support_removed:
        position_we_vote_id_list_to_remove_from_challenge_participants.append(one_position.we_vote_id)

    challenge_participant_search_success = True
    if len(position_we_vote_id_list_to_remove_from_challenge_participants) > 0:
        try:
            queryset = ChallengeParticipant.objects.using('readonly').all()
            queryset = queryset.filter(
                linked_position_we_vote_id__in=position_we_vote_id_list_to_remove_from_challenge_participants)
            challenge_participant_entries_to_delete = list(queryset)
            for one_challenge_participant in challenge_participant_entries_to_delete:
                challenge_participant_id_list_to_delete.append(one_challenge_participant.id)
        except Exception as e:
            challenge_participant_search_success = False
            update_message += "CHALLENGE_PARTICIPANT_RETRIEVE_BY_POSITION_WE_VOTE_ID-FAILED: " + str(e) + " "

    position_updates_needed = False
    if challenge_participant_search_success:
        # As long as there haven't been any errors above, we can prepare to mark
        #  all positions 'challenge_participant_created' = True
        for one_position in position_list_with_support_removed:
            one_position.challenge_participant_created = True
            position_objects_to_set_challenge_participant_created_true.append(one_position)
            position_updates_made += 1
            position_updates_needed = True

    challenge_participant_bulk_delete_success = True
    if len(challenge_participant_id_list_to_delete) > 0:
        try:
            queryset = ChallengeParticipant.objects.all()
            queryset = queryset.filter(id__in=challenge_participant_id_list_to_delete)
            challenge_participant_entries_deleted_count, challenges_dict = queryset.delete()
            challenge_participant_bulk_delete_success = True
            update_message += \
                "{challenge_participant_entries_deleted_count:,} ChallengeParticipant entries deleted, " \
                "".format(challenge_participant_entries_deleted_count=challenge_participant_entries_deleted_count)
        except Exception as e:
            challenge_participant_bulk_delete_success = False
            update_message += "CHALLENGE_PARTICIPANT_BULK_DELETE-FAILED: " + str(e) + " "

    if position_updates_needed and challenge_participant_bulk_delete_success:
        try:
            if friends_only_positions:
                PositionForFriends.objects.bulk_update(
                    position_objects_to_set_challenge_participant_created_true, ['challenge_participant_created'])
            else:
                PositionEntered.objects.bulk_update(
                    position_objects_to_set_challenge_participant_created_true, ['challenge_participant_created'])
            update_message += \
                "{position_updates_made:,} positions updated with challenge_participant_created=True, " \
                "".format(position_updates_made=position_updates_made)
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with PositionEntered.objects.bulk_update: {e}, "
                                 "".format(e=e))

    total_to_convert_after = total_to_convert - number_to_delete if total_to_convert > number_to_delete else 0
    if positive_value_exists(total_to_convert_after):
        update_message += \
            "{total_to_convert_after:,} positions remaining in 'delete ChallengeParticipant' process. " \
            "".format(total_to_convert_after=total_to_convert_after)

    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    results = {
        'challenge_participant_entries_deleted':  challenge_participant_entries_deleted_count,
        'challenge_we_vote_id_list_to_refresh': challenge_we_vote_id_list_to_refresh,
        'status':   status,
        'success':  success,
    }
    return results


def delete_challenge_participant(voter_to_delete=None):
    
    status = ""
    success = True
    challenge_participant_deleted = 0
    challenge_participant_not_deleted = 0
    voter_to_delete_id = voter_to_delete.we_vote_id

    if not positive_value_exists(voter_to_delete_id):
        status += "DELETE_CHALLENGE_PARTICIPANT-MISSING_VOTER_ID"
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'voter_to_delete_we_vote_id':       voter_to_delete_id,
            'challenge_participant_deleted':       challenge_participant_deleted,
            'challenge_participant_not_deleted':   challenge_participant_not_deleted,
        }
        return results
    
    try:
        number_deleted, details = ChallengeParticipant.objects\
            .filter(voter_we_vote_id=voter_to_delete_id, )\
            .delete()
        challenge_participant_deleted += number_deleted
    except Exception as e:
        status += "ChallengeParticipant CHALLENGE PARTICIPANT NOT DELETED: " + str(e) + " "
        challenge_participant_not_deleted += 1

    results = {
        'status':                           status,
        'success':                          success,
        'challenge_participant_deleted':      challenge_participant_deleted,
        'challenge_participant_not_deleted':  challenge_participant_not_deleted,
    }
    
    return results
