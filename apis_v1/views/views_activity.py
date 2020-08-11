# apis_v1/views/views_activity.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from activity.models import ActivityManager
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from voter.models import fetch_voter_we_vote_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, is_voter_device_id_valid, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def activity_list_retrieve_view(request):  # activityListRetrieve
    """
    Retrieve activity so we can populate the news page
    :param request:
    :return:
    """
    status = ''
    activity_list = []
    activity_manager = ActivityManager()
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)

    if not positive_value_exists(voter_we_vote_id):
        status += "RETRIEVE_ACTIVITY_NOTICE_LIST_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
            'activity_list': activity_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = activity_manager.retrieve_activity_notice_seed_list_for_recipient(
        recipient_voter_we_vote_id=voter_we_vote_id)
    if not results['success']:
        status += results['status']
        status += "RETRIEVE_ACTIVITY_NOTICE_LIST_FAILED "
        json_data = {
            'status': status,
            'success': False,
            'activity_list': activity_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    activity_list = []
    activity_notice_seed_list = results['activity_notice_seed_list']
    for activity_notice_seed in activity_notice_seed_list:
        new_positions_entered_count = 0
        position_we_vote_id_list = []
        # In this scenario we want to return both friends and public values
        if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_friends_serialized):
            position_we_vote_id_list += json.loads(activity_notice_seed.position_we_vote_ids_for_friends_serialized)
        if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_public_serialized):
            position_we_vote_id_list += json.loads(activity_notice_seed.position_we_vote_ids_for_public_serialized)
        new_positions_entered_count += len(position_we_vote_id_list)
        activity_notice_seed_dict = {
            'date_last_changed':                activity_notice_seed.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'date_of_notice':                   activity_notice_seed.date_of_notice.strftime('%Y-%m-%d %H:%M:%S'),
            'id':                               activity_notice_seed.id,
            'kind_of_activity':                 "ACTIVITY_NOTICE_SEED",
            'kind_of_seed':                     activity_notice_seed.kind_of_seed,
            'new_positions_entered_count':      new_positions_entered_count,
            'position_we_vote_id_list':         position_we_vote_id_list,
            'speaker_name':                     activity_notice_seed.speaker_name,
            'speaker_organization_we_vote_id':  activity_notice_seed.speaker_organization_we_vote_id,
            'speaker_voter_we_vote_id':         activity_notice_seed.speaker_voter_we_vote_id,
            'speaker_profile_image_url_medium': activity_notice_seed.speaker_profile_image_url_medium,
            'speaker_profile_image_url_tiny':   activity_notice_seed.speaker_profile_image_url_tiny,
            'speaker_twitter_handle':           activity_notice_seed.speaker_twitter_handle,
            'speaker_twitter_followers_count':  activity_notice_seed.speaker_twitter_followers_count,
        }
        activity_list.append(activity_notice_seed_dict)
    json_data = {
        'status': status,
        'success': True,
        'activity_list': activity_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def activity_notice_list_retrieve_view(request):  # activityNoticeListRetrieve
    """
    Retrieve activity notices so we can show the voter recent activity
    :param request:
    :return:
    """
    status = ''
    activity_notice_list = []
    activity_manager = ActivityManager()
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)

    if not positive_value_exists(voter_we_vote_id):
        status += "RETRIEVE_ACTIVITY_NOTICE_LIST_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
            'activity_notice_list': activity_notice_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = activity_manager.retrieve_activity_notice_list_for_recipient(recipient_voter_we_vote_id=voter_we_vote_id)
    if not results['success']:
        status += results['status']
        status += "RETRIEVE_ACTIVITY_NOTICE_LIST_FAILED "
        json_data = {
            'status': status,
            'success': False,
            'activity_notice_list': activity_notice_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    modified_activity_notice_list = []
    activity_notice_list = results['activity_notice_list']
    for activity_notice in activity_notice_list:
        position_we_vote_id_list = []
        if positive_value_exists(activity_notice.position_we_vote_id_list_serialized):
            position_we_vote_id_list = json.loads(activity_notice.position_we_vote_id_list_serialized)
        new_positions_entered_count = activity_notice.new_positions_entered_count
        if new_positions_entered_count > 0:
            activity_notice_dict = {
                'date_last_changed':                activity_notice.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
                'date_of_notice':                   activity_notice.date_of_notice.strftime('%Y-%m-%d %H:%M:%S'),
                'id':                               activity_notice.id,
                'kind_of_notice':                   activity_notice.kind_of_notice,
                'new_positions_entered_count':      new_positions_entered_count,
                'position_we_vote_id_list':         position_we_vote_id_list,
                'speaker_name':                     activity_notice.speaker_name,
                'speaker_organization_we_vote_id':  activity_notice.speaker_organization_we_vote_id,
                'speaker_voter_we_vote_id':         activity_notice.speaker_voter_we_vote_id,
                'speaker_profile_image_url_medium': activity_notice.speaker_profile_image_url_medium,
                'speaker_profile_image_url_tiny':   activity_notice.speaker_profile_image_url_tiny,
            }
            modified_activity_notice_list.append(activity_notice_dict)
    json_data = {
        'status': status,
        'success': True,
        'activity_notice_list': modified_activity_notice_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
