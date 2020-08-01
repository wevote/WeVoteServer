# activity/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ActivityNoticeSeed, ActivityManager, ActivityNotice, ActivityTidbit, \
    NOTICE_FRIEND_ENDORSEMENTS, NOTICE_FRIEND_ENDORSEMENTS_SEED
from config.base import get_environment_variable
from django.utils.timezone import now
from friend.models import FriendManager
import json
from datetime import timedelta
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def update_or_create_activity_notices_triggered_by_batch_process():
    """
    We assume only one of this function is running at any time. Please see:
    :return:
    """
    status = ''
    success = True
    activity_notice_seed_count = 0
    activity_notice_count = 0
    activity_notice_seed_id_already_reviewed_list = []

    # Retrieve ActivityNoticeSeeds that need to have ActivityNotice entries created
    activity_manager = ActivityManager()
    safety_valve_count = 0
    # We want this process to stop before it has run for 5 minutes, so that we don't collide with another process
    #  starting. Please also see: activity_notice_processing_time_out_duration & checked_out_expiration_time
    # We adjust timeout for ACTIVITY_NOTICE_PROCESS in retrieve_batch_process_list
    longest_activity_notice_processing_run_time_allowed = 270  # 4.5 minutes * 60 seconds
    when_process_must_stop = now() + timedelta(seconds=longest_activity_notice_processing_run_time_allowed)
    continue_retrieving = True
    while continue_retrieving and safety_valve_count < 1000 and when_process_must_stop > now():
        safety_valve_count += 1
        results = activity_manager.retrieve_next_activity_notice_seed_to_process(
            notices_to_be_created=True,
            activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
        if results['activity_notice_seed_found']:
            activity_notice_seed = results['activity_notice_seed']
            activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
            activity_notice_seed_count += 1
            create_results = create_activity_notices_from_seed(activity_notice_seed)
            # activity_notice_seed.activity_notices_created = True  # Marked in create_activity_notices_from_seed
            activity_notice_count += create_results['activity_notice_count']
        else:
            continue_retrieving = False

    results = {
        'success':                      success,
        'status':                       status,
        'activity_notice_seed_count':   activity_notice_seed_count,
        'activity_notice_count':        activity_notice_count,
    }
    return results


def create_activity_notices_from_seed(activity_notice_seed):
    status = ''
    success = True
    activity_notice_count = 0
    activity_manager = ActivityManager
    friend_manager = FriendManager()

    # Create ActivityNotice entries that haven't been created yet
    # Who needs to see a notice?
    audience = 'FRIENDS'
    # audience = 'ONE_FRIEND'
    if audience == 'FRIENDS':
        # Retrieve all friends of activity_notice_seed.speaker_voter_we_vote_id
        status += "KIND_OF_LIST-CURRENT_FRIENDS "
        retrieve_current_friends_as_voters_results = \
            friend_manager.retrieve_current_friends_as_voters(activity_notice_seed.speaker_voter_we_vote_id)
        success = retrieve_current_friends_as_voters_results['success']
        status += retrieve_current_friends_as_voters_results['status']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friend_list = retrieve_current_friends_as_voters_results['friend_list']
            for friend_voter in current_friend_list:
                activity_results = update_or_create_activity_notice_for_friend(
                    activity_notice_seed_id=activity_notice_seed.id,
                    position_we_vote_id=activity_notice_seed.position_we_vote_id,
                    recipient_voter_we_vote_id=friend_voter.we_vote_id,
                    speaker_name=activity_notice_seed.speaker_name,
                    speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                    speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                    speaker_profile_image_url_medium=activity_notice_seed.speaker_profile_image_url_medium,
                    speaker_profile_image_url_tiny=activity_notice_seed.speaker_profile_image_url_tiny)
                if activity_results['success']:
                    activity_notice_count += 1
                else:
                    status += activity_results['status']
        else:
            status += "CREATE_ACTIVITY_NOTICES_FROM_SEED-NO_FRIENDS "

    try:
        activity_notice_seed.activity_notices_created = True
        activity_notice_seed.save()
        status += "CREATE_ACTIVITY_NOTICES_FROM_SEED-MARKED_CREATED "
    except Exception as e:
        status += "CREATE_ACTIVITY_NOTICES_FROM_SEED-CANNOT_MARK_NOTICES_CREATED: " + str(e) + " "
        success = False

    results = {
        'success':                  success,
        'status':                   status,
        'activity_notice_count':    activity_notice_count,
    }
    return results


def update_or_create_activity_notice_for_friend(
        activity_notice_seed_id=0,
        position_we_vote_id='',
        recipient_voter_we_vote_id='',
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny=''):
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_from_speaker_and_recipient(
        activity_notice_seed_id=activity_notice_seed_id,
        kind_of_notice=NOTICE_FRIEND_ENDORSEMENTS,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_found']:
        # activity_notice = results['activity_notice_seed']
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice(
            activity_notice_seed_id=activity_notice_seed_id,
            date_of_notice=date_of_notice,
            kind_of_notice=NOTICE_FRIEND_ENDORSEMENTS,
            kind_of_seed=NOTICE_FRIEND_ENDORSEMENTS_SEED,
            position_we_vote_id=position_we_vote_id,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_seed_for_voter_position(
        position_we_vote_id='',
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny=''):
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_seed_from_speaker(
        kind_of_seed=NOTICE_FRIEND_ENDORSEMENTS_SEED,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_seed_found']:
        # activity_notice_seed = results['activity_notice_seed']
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice_seed(
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_FRIEND_ENDORSEMENTS_SEED,
            position_we_vote_id=position_we_vote_id,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_activity_notices_from_seed(activity_notice_seed):
    status = ''
    success = True

    # Update the ActivityNotice before email send

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def voter_activity_notice_list_retrieve_for_api(voter_device_id):  # voterActivityNoticeListRetrieve
    """

    :param voter_device_id:
    :return:
    """
    activity_notice_list_found = False
    status = ""
    success = True

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                       device_id_results['status'],
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'activity_notice_list_found':  False,
            'activity_notice_list':        [],
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not voter_results['voter_found']:
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'activity_notice_list_found':   False,
            'activity_notice_list':         [],
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    activity_notice_list_augmented = []
    # sms_manager = SMSManager()
    # merge_results = sms_manager.find_and_merge_all_duplicate_sms(voter_we_vote_id)
    # status += merge_results['status']
    #
    #
    # sms_results = sms_manager.retrieve_voter_activity_notice_list(voter_we_vote_id)
    # status += sms_results['status']
    # if sms_results['activity_notice_list_found']:
    #     activity_notice_list_found = True
    #     activity_notice_list = sms_results['activity_notice_list']
    #
    #     # Remove duplicates: sms_we_vote_id
    #     merge_results = heal_primary_sms_data_for_voter(activity_notice_list, voter)
    #     activity_notice_list = merge_results['activity_notice_list']
    #     status += merge_results['status']
    #
    #     augment_results = augment_activity_notice_list(activity_notice_list, voter)
    #     activity_notice_list_augmented = augment_results['activity_notice_list']
    #     status += augment_results['status']

    json_data = {
        'status':                       status,
        'success':                      success,
        'voter_device_id':              voter_device_id,
        'activity_notice_list_found':   activity_notice_list_found,
        'activity_notice_list':         activity_notice_list_augmented,
    }
    return json_data
