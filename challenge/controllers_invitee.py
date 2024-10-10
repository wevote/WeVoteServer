# challenge/controllers_invitee.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Challenge, ChallengeManager, ChallengeInvitee
from django.contrib import messages
from django.db.models import Q
from follow.models import FOLLOW_DISLIKE, FOLLOWING, FollowOrganizationManager
from position.models import OPPOSE, SUPPORT
from share.models import ShareManager
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import generate_random_string, positive_value_exists
from wevote_functions.functions_date import generate_date_as_integer, get_current_date_as_integer, DATE_FORMAT_YMD_HMS

logger = wevote_functions.admin.get_logger(__name__)


def challenge_invitee_retrieve_for_api(  # challengeInviteeRetrieve
        voter_device_id='',
        invitee_url_code=''):
    status = ''

    return_results = generate_challenge_invitee_dict_from_challenge_invitee_object()
    status += return_results['status']
    error_results = return_results['challenge_invitee_dict']
    error_results['status'] = status
    error_results['success'] = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        error_results['status'] = status
        return error_results

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge_invitee(
        invitee_url_code=invitee_url_code,
        read_only=True,
    )
    status += results['status']
    random_string = generate_random_string(8)
    # TODO: Confirm its not in use
    next_invitee_url_code = random_string
    if not results['success']:
        status += "CHALLENGE_INVITEE_RETRIEVE_ERROR "
        error_results['status'] = status
        return error_results
    elif not results['challenge_invitee_found']:
        status += "CHALLENGE_INVITEE_NOT_FOUND: "
        error_results['status'] = status
        error_results['next_invitee_url_code'] = next_invitee_url_code
        return error_results

    challenge_invitee = results['challenge_invitee']
    dict_results = generate_challenge_invitee_dict_from_challenge_invitee_object(challenge_invitee=challenge_invitee)
    status += dict_results['status']
    if dict_results['success']:
        results = dict_results['challenge_invitee_dict']
        results['status'] = status
        results['success'] = True
        results['next_invitee_url_code'] = next_invitee_url_code
        return results
    else:
        status += "CHALLENGE_INVITEE_GENERATE_RESULTS_ERROR "
        error_results['status'] = status
        return error_results


def challenge_invitee_list_retrieve_for_api(  # challengeInviteeListRetrieve
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
            'challenge_invitee_list':   [],
            'challenge_we_vote_id':         challenge_we_vote_id,
            'voter_we_vote_id':             '',
        }
        return results

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge_invitee_list(
        challenge_we_vote_id=challenge_we_vote_id,
        inviter_voter_we_vote_id=voter_we_vote_id,
        read_only=True,
    )
    status += results['status']
    random_string = generate_random_string(8)
    # TODO: Confirm its not in use
    next_invitee_url_code = random_string
    if not results['success']:
        status += "CHALLENGE_INVITEE_LIST_RETRIEVE_ERROR "
        results = {
            'status':                       status,
            'success':                      False,
            'challenge_invitee_list':   [],
            'challenge_we_vote_id':         challenge_we_vote_id,
            'voter_we_vote_id':             '',
        }
        return results
    elif not results['invitee_list_found']:
        status += "CHALLENGE_INVITEE_LIST_NOT_FOUND: "
        status += results['status'] + " "

    challenge_invitee_list = []
    for challenge_invitee in results['invitee_list']:
        generate_results = generate_challenge_invitee_dict_from_challenge_invitee_object(
            challenge_invitee=challenge_invitee)
        if generate_results['success']:
            challenge_invitee_list.append(generate_results['challenge_invitee_dict'])
    results = {
        'status':                   status,
        'success':                  True,
        'challenge_invitee_list':   challenge_invitee_list,
        'challenge_we_vote_id':     challenge_we_vote_id,
        'next_invitee_url_code':    next_invitee_url_code,
        'voter_we_vote_id':         voter_we_vote_id,
    }
    return results


def challenge_invitee_save_for_api(  # challengeInviteeSave
        challenge_we_vote_id='',
        destination_full_url=None,
        google_civic_election_id=None,
        invite_sent=None,
        invite_sent_changed=False,
        invitee_id=None,
        invitee_name=None,
        invitee_name_changed=False,
        invitee_text_from_inviter=None,
        invitee_text_from_inviter_changed=False,
        invitee_url_code=None,
        invitee_url_code_changed=False,
        voter_device_id=''):
    status = ''
    success = True
    voter_first_name = ''
    voter_full_name = ''
    voter_last_name = ''
    we_vote_hosted_profile_image_url_large = ''
    we_vote_hosted_profile_image_url_medium = ''
    we_vote_hosted_profile_image_url_tiny = ''

    return_results = generate_challenge_invitee_dict_from_challenge_invitee_object()
    status += return_results['status']
    error_results = return_results['challenge_invitee_dict']
    error_results['status'] = status
    error_results['success'] = success

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_full_name = voter.get_full_name(real_name_only=True)
        if positive_value_exists(voter.first_name):
            voter_first_name = voter.first_name
        if positive_value_exists(voter.last_name):
            voter_last_name = voter.last_name
        voter_we_vote_id = voter.we_vote_id
        we_vote_hosted_profile_image_url_large = voter.we_vote_hosted_profile_image_url_large
        we_vote_hosted_profile_image_url_medium = voter.we_vote_hosted_profile_image_url_medium
        we_vote_hosted_profile_image_url_tiny = voter.we_vote_hosted_profile_image_url_tiny
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = error_results
        results['status'] = status
        return results

    # To participate in a challenge, voter must be signed in
    if not voter.is_signed_in():
        status += "INVITEE_NOT_SIGNED_IN "
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
        'invite_sent': invite_sent,
        'invite_sent_changed': invite_sent_changed,
        'invitee_name': invitee_name,
        'invitee_name_changed': invitee_name_changed,
        'invitee_text_from_inviter': invitee_text_from_inviter,
        'invitee_text_from_inviter_changed': invitee_text_from_inviter_changed,
        'invitee_url_code': invitee_url_code,
        'invitee_url_code_changed': invitee_url_code_changed,
        'inviter_name': voter_full_name,
        'inviter_name_changed': True,
    }
    invitee_results = challenge_manager.update_or_create_challenge_invitee(
        challenge_we_vote_id=challenge_we_vote_id,
        invitee_id=invitee_id,
        inviter_voter_we_vote_id=voter_we_vote_id,
        update_values=update_values,
    )

    status += invitee_results['status']

    share_manager = ShareManager()
    defaults = {
        'is_challenge_share':                   True,
        'other_voter_display_name':             invitee_name,
        # 'other_voter_first_name':               other_voter_first_name,
        # 'other_voter_last_name':                other_voter_last_name,
        'shared_by_display_name':               voter_full_name,
        'shared_by_first_name':                 voter_first_name,
        'shared_by_last_name':                  voter_last_name,
        # 'shared_by_organization_type':          shared_by_organization_type,
        # 'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           voter_we_vote_id,
        'shared_by_we_vote_hosted_profile_image_url_large':     we_vote_hosted_profile_image_url_large,
        'shared_by_we_vote_hosted_profile_image_url_medium':    we_vote_hosted_profile_image_url_medium,
        'shared_by_we_vote_hosted_profile_image_url_tiny':      we_vote_hosted_profile_image_url_tiny,
        'shared_item_code_challenge':           invitee_url_code,
        # 'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
    }
    shared_item_results = share_manager.update_or_create_shared_item(
        destination_full_url=destination_full_url,
        force_create_new=True,
        shared_by_voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        defaults=defaults,
    )
    status += shared_item_results['status']
    if shared_item_results['success']:
        # shared_item_code_challenge = shared_item_results['shared_item_code']
        pass

    count_results = challenge_manager.update_challenge_invitees_count(challenge_we_vote_id)

    from challenge.controllers_participant import update_challenge_participant_with_invitee_stats
    stats_results = update_challenge_participant_with_invitee_stats(
        challenge_we_vote_id=challenge_we_vote_id,
        inviter_voter=voter,
        inviter_voter_we_vote_id=voter_we_vote_id,
    )
    status += stats_results['status']

    challenge_we_vote_id_list = [challenge_we_vote_id]
    from challenge.controllers_scoring import refresh_participant_points_for_challenge
    for one_challenge_we_vote_id in challenge_we_vote_id_list:
        results = refresh_participant_points_for_challenge(
            challenge_we_vote_id=one_challenge_we_vote_id)
        status += results['status']

    random_string = generate_random_string(8)
    # TODO: Confirm its not in use
    next_invitee_url_code = random_string
    if invitee_results['challenge_invitee_found']:
        challenge_invitee = invitee_results['challenge_invitee']
        return_results = generate_challenge_invitee_dict_from_challenge_invitee_object(
            challenge_invitee=challenge_invitee)
        status += return_results['status']
        results = return_results['challenge_invitee_dict']
        results['status'] = status
        results['success'] = True
        results['next_invitee_url_code'] = next_invitee_url_code
        return results
    else:
        status += "CHALLENGE_INVITEE_SAVE_ERROR "
        results = error_results
        results['status'] = status
        results['success'] = False
        return results


def retrieve_invitee_stats_to_store_in_participant(
        challenge_we_vote_id='',
        inviter_voter_we_vote_id=''):
    status = ''
    success = True
    invitees_count = 0
    invitees_who_joined = 0
    invitees_who_viewed = 0
    # invitees_who_viewed_plus = 0
    invites_sent_count = 0
    error_results = {
        'challenge_we_vote_id': challenge_we_vote_id,
        'inviter_voter_we_vote_id': inviter_voter_we_vote_id,
        'status': status,
        'success': False,
        'update_values': {},
    }
    try:
        queryset = ChallengeInvitee.objects.using('readonly').all()
        queryset = queryset.filter(challenge_we_vote_id=challenge_we_vote_id)
        queryset = queryset.filter(inviter_voter_we_vote_id=inviter_voter_we_vote_id)
        invitee_list = list(queryset)
    except Exception as e:
        status += "FAILED_RETRIEVING_INVITEE_STATS: " + str(e) + ' '
        success = False
        error_results['status'] += status
        error_results['success'] += success
        return error_results

    for one_invitee in invitee_list:
        invitees_count += 1
        if one_invitee.challenge_joined:
            invitees_who_joined += 1
        if one_invitee.invite_viewed:
            invitees_who_viewed += 1
        # Will take another routine to calculate
        # if one_invitee.is_viewed_plus:
        #     invitees_who_viewed_plus += 1
        if one_invitee.invite_sent:
            invites_sent_count += 1

    update_values = {
        'invitees_count':       invitees_count,
        'invitees_who_joined':  invitees_who_joined,
        'invitees_who_viewed':  invitees_who_viewed,
        'invites_sent_count':   invites_sent_count,
    }

    results = {
        'challenge_we_vote_id':     challenge_we_vote_id,
        'inviter_voter_we_vote_id': inviter_voter_we_vote_id,
        'update_values':            update_values,
        'status':                   status,
        'success':                  success,
    }
    return results


def move_invitee_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    invitee_entries_moved = 0
    invitee_entries_not_moved = 0
    error_results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'invitee_entries_moved': invitee_entries_moved,
        'invitee_entries_not_moved': invitee_entries_not_moved,
    }

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_INVITEE_ENTRIES_TO_ANOTHER_VOTER-" \
                  "Missing either from_voter_we_vote_id or to_voter_we_vote_id "
        error_results['status'] = status
        return error_results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_INVITEE_ENTRIES_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        error_results['status'] = status
        return error_results

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge_invitee_list(
        inviter_voter_we_vote_id=from_voter_we_vote_id,
        limit=0,
        read_only=False)
    from_invitee_list = results['invitee_list']
    results = challenge_manager.retrieve_challenge_invitee_list(
        inviter_voter_we_vote_id=to_voter_we_vote_id,
        limit=0,
        read_only=False)
    to_invitee_list = results['invitee_list']
    to_invitee_we_vote_id_list = []
    for to_invitee in to_invitee_list:
        if to_invitee.inviter_voter_we_vote_id not in to_invitee_we_vote_id_list:
            to_invitee_we_vote_id_list.append(to_invitee.inviter_voter_we_vote_id)

    bulk_update_list = []
    for from_invitee_entry in from_invitee_list:
        # See if the "to_voter" already has an entry for this issue
        if from_invitee_entry.inviter_voter_we_vote_id in to_invitee_we_vote_id_list:
            # Don't move this entry. We already have an entry for this inviter_voter_we_vote_id in the to_voter's list
            pass
        else:
            # Change the from_voter_we_vote_id to to_voter_we_vote_id
            try:
                from_invitee_entry.inviter_voter_we_vote_id = to_voter_we_vote_id
                bulk_update_list.append(from_invitee_entry)
                invitee_entries_moved += 1
            except Exception as e:
                invitee_entries_not_moved += 1
                status += "FAILED_FROM_INVITEE_SAVE: " + str(e) + " "
                success = False
    if positive_value_exists(invitee_entries_moved):
        try:
            ChallengeInvitee.objects.bulk_update(bulk_update_list, ['inviter_voter_we_vote_id'])
        except Exception as e:
            status += "FAILED_BULK_INVITEE_SAVE: " + str(e) + " "
            success = False

    results = {
        'status':                       status,
        'success':                      success,
        'from_voter_we_vote_id':        from_voter_we_vote_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'invitee_entries_moved':        invitee_entries_moved,
        'invitee_entries_not_moved':    invitee_entries_not_moved,
    }
    return results


def refresh_challenge_invitees_count_for_challenge_we_vote_id_list(challenge_we_vote_id_list=[]):
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

                    invitees_count = follow_organization_manager.fetch_follow_organization_count(
                        following_status=FOLLOWING,
                        organization_we_vote_id_being_followed=one_challenge.organization_we_vote_id)
                else:
                    error_message_to_print += "CHALLENGE_MISSING_ORGANIZATION: " + str(one_challenge.we_vote_id) + " "
                    continue
            else:
                invitees_count = challenge_manager.fetch_challenge_invitee_count(
                    challenge_we_vote_id=one_challenge.we_vote_id)
            if opposers_count != one_challenge.opposers_count:
                one_challenge.opposers_count = opposers_count
                changes_found = True
            if invitees_count != one_challenge.invitees_count:
                one_challenge.invitees_count = invitees_count
                changes_found = True
            if changes_found:
                challenge_bulk_update_list.append(one_challenge)
                challenges_need_to_be_updated = True
                challenge_updates_made += 1
    if challenges_need_to_be_updated:
        try:
            Challenge.objects.bulk_update(challenge_bulk_update_list, ['opposers_count', 'invitees_count'])
            update_message += \
                "{challenge_updates_made:,} Challenge entries updated with fresh invitees_count, " \
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


def generate_challenge_invitee_dict_from_challenge_invitee_object(challenge_invitee=None):
    status = ""
    success = True

    challenge_invitee_dict = {
        'challenge_joined': False,
        'challenge_we_vote_id': '',
        'date_invite_sent': '',
        'date_invite_viewed': '',
        'date_challenge_joined': '',
        'invitee_id': '',
        'invitee_name': '',
        'invitee_url_code': '',
        'inviter_name': '',
        'inviter_voter_we_vote_id': '',
        'invite_sent': False,
        'invite_text_from_inviter': '',
        'invite_viewed': False,
        'invite_viewed_count': 0,
        'we_vote_hosted_profile_image_url_medium': '',
        'we_vote_hosted_profile_image_url_tiny': '',
    }

    if not hasattr(challenge_invitee, 'inviter_voter_we_vote_id'):
        status += "VALID_CHALLENGE_INVITEE_OBJECT_MISSING "
        results = {
            'challenge_invitee_dict': challenge_invitee_dict,
            'status': status,
            'success': False,
        }
        return results

    # If smaller sizes weren't stored, use large image
    if challenge_invitee:
        if challenge_invitee.we_vote_hosted_profile_image_url_medium:
            we_vote_hosted_profile_image_url_medium = challenge_invitee.we_vote_hosted_profile_image_url_medium
        else:
            we_vote_hosted_profile_image_url_medium = ''
        if challenge_invitee.we_vote_hosted_profile_image_url_tiny:
            we_vote_hosted_profile_image_url_tiny = challenge_invitee.we_vote_hosted_profile_image_url_tiny
        elif challenge_invitee.we_vote_hosted_profile_image_url_medium:
            we_vote_hosted_profile_image_url_tiny = challenge_invitee.we_vote_hosted_profile_image_url_medium
        else:
            we_vote_hosted_profile_image_url_tiny = ''
    else:
        we_vote_hosted_profile_image_url_medium = ''
        we_vote_hosted_profile_image_url_tiny = ''

    date_invite_viewed_string = ''
    date_challenge_joined_string = ''
    date_invite_sent_string = ''
    try:
        date_invite_sent_string = challenge_invitee.date_invite_sent.strftime(DATE_FORMAT_YMD_HMS)
        date_invite_viewed_string = challenge_invitee.date_invite_viewed.strftime(DATE_FORMAT_YMD_HMS)
        date_challenge_joined_string = challenge_invitee.date_challenge_joined.strftime(DATE_FORMAT_YMD_HMS)
    except Exception as e:
        status += "DATE_CONVERSION_ERROR-INVITEE: " + str(e) + " "
    challenge_invitee_dict['challenge_joined'] = challenge_invitee.challenge_joined
    challenge_invitee_dict['challenge_we_vote_id'] = challenge_invitee.challenge_we_vote_id
    challenge_invitee_dict['invite_text_from_inviter'] = challenge_invitee.invite_text_from_inviter
    challenge_invitee_dict['date_invite_sent'] = date_invite_sent_string
    challenge_invitee_dict['date_invite_viewed'] = date_invite_viewed_string
    challenge_invitee_dict['date_challenge_joined'] = date_challenge_joined_string
    challenge_invitee_dict['invitee_id'] = challenge_invitee.id
    challenge_invitee_dict['invitee_name'] = challenge_invitee.invitee_name
    challenge_invitee_dict['invitee_url_code'] = challenge_invitee.invitee_url_code
    challenge_invitee_dict['inviter_name'] = challenge_invitee.inviter_name
    challenge_invitee_dict['inviter_voter_we_vote_id'] = challenge_invitee.inviter_voter_we_vote_id
    challenge_invitee_dict['invite_sent'] = challenge_invitee.invite_sent
    challenge_invitee_dict['invite_viewed'] = challenge_invitee.invite_viewed
    challenge_invitee_dict['invite_viewed_count'] = challenge_invitee.invite_viewed_count
    challenge_invitee_dict['we_vote_hosted_profile_image_url_medium'] = we_vote_hosted_profile_image_url_medium
    challenge_invitee_dict['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny

    results = {
        'challenge_invitee_dict':   challenge_invitee_dict,
        'status':                   status,
        'success':                  success,
    }
    return results


def delete_challenge_invitees_after_positions_removed(
        request,
        friends_only_positions=False,
        state_code=''):
    # Create default variables needed below
    challenge_invitee_entries_deleted_count = 0
    challenge_we_vote_id_list_to_refresh = []
    number_to_delete = 20  # 1000
    from position.models import PositionEntered, PositionForFriends
    position_objects_to_set_challenge_invitee_created_true = []  # Field is 'challenge_invitee_created'
    position_updates_made = 0
    position_we_vote_id_list_to_remove_from_challenge_invitees = []
    challenge_invitee_id_list_to_delete = []
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
        position_query = position_query.exclude(challenge_invitee_created=True)
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
        position_we_vote_id_list_to_remove_from_challenge_invitees.append(one_position.we_vote_id)

    challenge_invitee_search_success = True
    if len(position_we_vote_id_list_to_remove_from_challenge_invitees) > 0:
        try:
            queryset = ChallengeInvitee.objects.using('readonly').all()
            queryset = queryset.filter(
                linked_position_we_vote_id__in=position_we_vote_id_list_to_remove_from_challenge_invitees)
            challenge_invitee_entries_to_delete = list(queryset)
            for one_challenge_invitee in challenge_invitee_entries_to_delete:
                challenge_invitee_id_list_to_delete.append(one_challenge_invitee.id)
        except Exception as e:
            challenge_invitee_search_success = False
            update_message += "CHALLENGE_INVITEE_RETRIEVE_BY_POSITION_WE_VOTE_ID-FAILED: " + str(e) + " "

    position_updates_needed = False
    if challenge_invitee_search_success:
        # As long as there haven't been any errors above, we can prepare to mark
        #  all positions 'challenge_invitee_created' = True
        for one_position in position_list_with_support_removed:
            one_position.challenge_invitee_created = True
            position_objects_to_set_challenge_invitee_created_true.append(one_position)
            position_updates_made += 1
            position_updates_needed = True

    challenge_invitee_bulk_delete_success = True
    if len(challenge_invitee_id_list_to_delete) > 0:
        try:
            queryset = ChallengeInvitee.objects.all()
            queryset = queryset.filter(id__in=challenge_invitee_id_list_to_delete)
            challenge_invitee_entries_deleted_count, challenges_dict = queryset.delete()
            challenge_invitee_bulk_delete_success = True
            update_message += \
                "{challenge_invitee_entries_deleted_count:,} ChallengeInvitee entries deleted, " \
                "".format(challenge_invitee_entries_deleted_count=challenge_invitee_entries_deleted_count)
        except Exception as e:
            challenge_invitee_bulk_delete_success = False
            update_message += "CHALLENGE_INVITEE_BULK_DELETE-FAILED: " + str(e) + " "

    if position_updates_needed and challenge_invitee_bulk_delete_success:
        try:
            if friends_only_positions:
                PositionForFriends.objects.bulk_update(
                    position_objects_to_set_challenge_invitee_created_true, ['challenge_invitee_created'])
            else:
                PositionEntered.objects.bulk_update(
                    position_objects_to_set_challenge_invitee_created_true, ['challenge_invitee_created'])
            update_message += \
                "{position_updates_made:,} positions updated with challenge_invitee_created=True, " \
                "".format(position_updates_made=position_updates_made)
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with PositionEntered.objects.bulk_update: {e}, "
                                 "".format(e=e))

    total_to_convert_after = total_to_convert - number_to_delete if total_to_convert > number_to_delete else 0
    if positive_value_exists(total_to_convert_after):
        update_message += \
            "{total_to_convert_after:,} positions remaining in 'delete ChallengeInvitee' process. " \
            "".format(total_to_convert_after=total_to_convert_after)

    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    results = {
        'challenge_invitee_entries_deleted':  challenge_invitee_entries_deleted_count,
        'challenge_we_vote_id_list_to_refresh': challenge_we_vote_id_list_to_refresh,
        'status':   status,
        'success':  success,
    }
    return results


def delete_challenge_invitee(voter_to_delete=None):
    
    status = ""
    success = True
    challenge_invitee_deleted = 0
    challenge_invitee_not_deleted = 0
    voter_to_delete_id = voter_to_delete.we_vote_id

    if not positive_value_exists(voter_to_delete_id):
        status += "DELETE_CHALLENGE_INVITEE-MISSING_VOTER_ID"
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'voter_to_delete_we_vote_id':       voter_to_delete_id,
            'challenge_invitee_deleted':       challenge_invitee_deleted,
            'challenge_invitee_not_deleted':   challenge_invitee_not_deleted,
        }
        return results
    
    try:
        number_deleted, details = ChallengeInvitee.objects\
            .filter(voter_we_vote_id=voter_to_delete_id, )\
            .delete()
        challenge_invitee_deleted += number_deleted
    except Exception as e:
        status += "ChallengeInvitee CHALLENGE INVITEE NOT DELETED: " + str(e) + " "
        challenge_invitee_not_deleted += 1

    results = {
        'status':                           status,
        'success':                          success,
        'challenge_invitee_deleted':      challenge_invitee_deleted,
        'challenge_invitee_not_deleted':  challenge_invitee_not_deleted,
    }
    
    return results
