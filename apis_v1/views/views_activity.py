# apis_v1/views/views_activity.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from activity.models import ActivityManager
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from twitter.models import TwitterUserManager
from voter.models import fetch_voter_we_vote_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, is_voter_device_id_valid, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def activity_comment_save_view(request):  # activityCommentSave
    """
    Save comment about an existing ActivityPost or other parent item.
    :param request:
    :return:
    """
    status = ''
    activity_manager = ActivityManager()

    activity_comment_we_vote_id = request.GET.get('activity_comment_we_vote_id', False)
    parent_we_vote_id = request.GET.get('parent_we_vote_id', False)
    parent_comment_we_vote_id = request.GET.get('parent_comment_we_vote_id', False)
    statement_text = request.GET.get('statement_text', False)
    visibility_setting = request.GET.get('visibility_setting', False)

    if visibility_setting not in ['FRIENDS_ONLY', 'SHOW_PUBLIC']:
        visibility_setting = 'FRIENDS_ONLY'

    visibility_is_public = visibility_setting == 'SHOW_PUBLIC'

    updated_values = {
        'commenter_name':                       '',
        'commenter_organization_we_vote_id':    '',
        'commenter_twitter_followers_count':    0,
        'commenter_twitter_handle':             '',
        'commenter_voter_we_vote_id':           '',
        'commenter_profile_image_url_medium':   '',
        'commenter_profile_image_url_tiny':     '',
        'parent_we_vote_id':                    parent_we_vote_id,
        'parent_comment_we_vote_id':            parent_comment_we_vote_id,
        'statement_text':                       statement_text,
        'visibility_is_public':                 visibility_is_public,
    }

    voter_device_id = get_voter_device_id(request)
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        commenter_twitter_followers_count = 0

        if positive_value_exists(voter.linked_organization_we_vote_id):
            # Is there a Twitter handle linked to this organization? If so, update the information.
            twitter_user_manager = TwitterUserManager()
            twitter_link_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
                    voter.linked_organization_we_vote_id)
            if twitter_link_results['twitter_link_to_organization_found']:
                twitter_link_to_organization = twitter_link_results['twitter_link_to_organization']

                twitter_results = \
                    twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                        twitter_link_to_organization.twitter_id)

                if twitter_results['twitter_user_found']:
                    twitter_user = twitter_results['twitter_user']
                    try:
                        commenter_twitter_followers_count = twitter_user.twitter_followers_count \
                            if positive_value_exists(twitter_user.twitter_followers_count) else 0
                    except Exception as e:
                        status += "FAILED_TO_RETRIEVE_TWITTER_FOLLOWERS_COUNT " + str(e) + ' '

        updated_values['commenter_name'] = voter.get_full_name(real_name_only=True)
        updated_values['commenter_voter_we_vote_id'] = voter.we_vote_id
        updated_values['commenter_organization_we_vote_id'] = voter.linked_organization_we_vote_id
        updated_values['commenter_profile_image_url_medium'] = voter.we_vote_hosted_profile_image_url_medium
        updated_values['commenter_profile_image_url_tiny'] = voter.we_vote_hosted_profile_image_url_tiny
        updated_values['commenter_twitter_followers_count'] = commenter_twitter_followers_count
        updated_values['commenter_twitter_handle'] = voter.twitter_screen_name
        updated_values['parent_we_vote_id'] = parent_we_vote_id
        updated_values['parent_comment_we_vote_id'] = parent_comment_we_vote_id

    if not positive_value_exists(updated_values['commenter_voter_we_vote_id']):
        status += "ACTIVITY_COMMENT_SAVE_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = activity_manager.update_or_create_activity_comment(
        activity_comment_we_vote_id=activity_comment_we_vote_id,
        updated_values=updated_values,
        commenter_voter_we_vote_id=updated_values['commenter_voter_we_vote_id'],
    )
    status += results['status']
    success = results['success']
    activity_comment_dict = {}
    if results['activity_comment_found']:
        activity_comment = results['activity_comment']
        activity_comment_dict = {
            'date_created':                         activity_comment.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            'date_last_changed':                    activity_comment.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'commenter_name':                       activity_comment.commenter_name,
            'commenter_organization_we_vote_id':    activity_comment.commenter_organization_we_vote_id,
            'commenter_voter_we_vote_id':           activity_comment.commenter_voter_we_vote_id,
            'commenter_profile_image_url_medium':   activity_comment.commenter_profile_image_url_medium,
            'commenter_profile_image_url_tiny':     activity_comment.commenter_profile_image_url_tiny,
            'commenter_twitter_handle':             activity_comment.commenter_twitter_handle,
            'commenter_twitter_followers_count':    activity_comment.commenter_twitter_followers_count,
            'statement_text':                       activity_comment.statement_text,
            'visibility_is_public':                 activity_comment.visibility_is_public,
            'we_vote_id':                           activity_comment.we_vote_id,
        }

    activity_comment_dict['status'] = status
    activity_comment_dict['success'] = success
    return HttpResponse(json.dumps(activity_comment_dict), content_type='application/json')


def activity_list_retrieve_view(request):  # activityListRetrieve
    """
    Retrieve activity so we can populate the news page
    :param request:
    :return:
    """
    status = ''
    activity_list = []
    activity_manager = ActivityManager()
    activity_notice_seed_list = []
    activity_post_list = []
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_friend_we_vote_id_list = []
    voter_we_vote_id = ''

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)

    if not positive_value_exists(voter_we_vote_id):
        status += "RETRIEVE_ACTIVITY_LIST_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
            'activity_list': activity_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = activity_manager.retrieve_activity_notice_seed_list_for_recipient(
        recipient_voter_we_vote_id=voter_we_vote_id)
    if results['success']:
        activity_notice_seed_list = results['activity_notice_seed_list']
        voter_friend_we_vote_id_list = results['voter_friend_we_vote_id_list']
    else:
        status += results['status']
        status += "RETRIEVE_ACTIVITY_LIST_FAILED "

    for activity_notice_seed in activity_notice_seed_list:
        new_positions_entered_count = 0
        position_we_vote_id_list = []
        # In this scenario we want to return both friends and public values
        if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_friends_serialized):
            position_we_vote_id_list += json.loads(activity_notice_seed.position_we_vote_ids_for_friends_serialized)
        if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_public_serialized):
            position_we_vote_id_list += json.loads(activity_notice_seed.position_we_vote_ids_for_public_serialized)
        new_positions_entered_count += len(position_we_vote_id_list)
        if not positive_value_exists(activity_notice_seed.we_vote_id):
            try:
                activity_notice_seed.save()
            except Exception as e:
                status += "COULD_NOT_UPDATE_SEED_WE_VOTE_ID: " + str(e) + ' '
        activity_notice_seed_dict = {
            'date_created':                     activity_notice_seed.date_of_notice.strftime('%Y-%m-%d %H:%M:%S'),
            'date_last_changed':                activity_notice_seed.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'date_of_notice':                   activity_notice_seed.date_of_notice.strftime('%Y-%m-%d %H:%M:%S'),
            'id':                               activity_notice_seed.id,  # We normalize to generate activityTidbitKey
            'activity_notice_seed_id':          activity_notice_seed.id,
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
            'we_vote_id':                       activity_notice_seed.we_vote_id,
        }
        activity_list.append(activity_notice_seed_dict)

    # ####################################################
    # Retrieve entries directly in the ActivityPost table
    results = activity_manager.retrieve_activity_post_list_for_recipient(
        recipient_voter_we_vote_id=voter_we_vote_id,
        voter_friend_we_vote_id_list=voter_friend_we_vote_id_list)
    if results['success']:
        activity_post_list = results['activity_post_list']
    else:
        status += results['status']
        status += "RETRIEVE_ACTIVITY_POST_LIST_FAILED "

    for activity_post in activity_post_list:
        date_created_string = ''
        if activity_post.date_created:
            date_created_string = activity_post.date_created.strftime('%Y-%m-%d %H:%M:%S')
        if not positive_value_exists(activity_post.we_vote_id):
            try:
                activity_post.save()
            except Exception as e:
                status += "COULD_NOT_UPDATE_POST_WE_VOTE_ID: " + str(e) + ' '
        activity_post_dict = {
            'date_created':                     date_created_string,
            'date_last_changed':                activity_post.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'date_of_notice':                   date_created_string,
            'id':                               activity_post.id,  # We normalize to generate activityTidbitKey
            'activity_post_id':                 activity_post.id,
            'kind_of_activity':                 'ACTIVITY_POST',
            'kind_of_seed':                     '',
            'new_positions_entered_count':      0,
            'position_we_vote_id_list':         [],
            'speaker_name':                     activity_post.speaker_name,
            'speaker_organization_we_vote_id':  activity_post.speaker_organization_we_vote_id,
            'speaker_voter_we_vote_id':         activity_post.speaker_voter_we_vote_id,
            'speaker_profile_image_url_medium': activity_post.speaker_profile_image_url_medium,
            'speaker_profile_image_url_tiny':   activity_post.speaker_profile_image_url_tiny,
            'speaker_twitter_handle':           activity_post.speaker_twitter_handle,
            'speaker_twitter_followers_count':  activity_post.speaker_twitter_followers_count,
            'statement_text':                   activity_post.statement_text,
            'visibility_is_public':             activity_post.visibility_is_public,
            'we_vote_id':                       activity_post.we_vote_id,
        }
        activity_list.append(activity_post_dict)

    # Now cycle through these activities and retrieve all related comments
    activity_list_with_comments = []
    for activity_tidbit_dict in activity_list:
        results = activity_manager.retrieve_activity_comment_list(
            parent_we_vote_id=activity_tidbit_dict['we_vote_id'])
        activity_comment_list = []
        if results['success']:
            activity_comment_object_list = results['activity_comment_list']
            for activity_comment in activity_comment_object_list:
                activity_comment_dict = {
                    'date_created': activity_comment.date_created.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_last_changed': activity_comment.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
                    'commenter_name': activity_comment.commenter_name,
                    'commenter_organization_we_vote_id': activity_comment.commenter_organization_we_vote_id,
                    'commenter_voter_we_vote_id': activity_comment.commenter_voter_we_vote_id,
                    'commenter_profile_image_url_medium': activity_comment.commenter_profile_image_url_medium,
                    'commenter_profile_image_url_tiny': activity_comment.commenter_profile_image_url_tiny,
                    'commenter_twitter_handle': activity_comment.commenter_twitter_handle,
                    'commenter_twitter_followers_count': activity_comment.commenter_twitter_followers_count,
                    'statement_text': activity_comment.statement_text,
                    'visibility_is_public': activity_comment.visibility_is_public,
                    'we_vote_id': activity_comment.we_vote_id,
                }
                activity_comment_list.append(activity_comment_dict)
        activity_tidbit_dict['activity_comment_list'] = activity_comment_list
        activity_list_with_comments.append(activity_tidbit_dict)

    # Order entries in the activity_list by "date_created"
    from operator import itemgetter
    activity_list_ordered = sorted(activity_list_with_comments, key=itemgetter('date_created'), reverse=True)

    json_data = {
        'status': status,
        'success': True,
        'activity_list': activity_list_ordered,
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

    activity_notice_id_list_clicked = request.GET.getlist('activity_notice_id_list_clicked[]')
    activity_notice_id_list_seen = request.GET.getlist('activity_notice_id_list_seen[]')

    if activity_notice_id_list_clicked and len(activity_notice_id_list_clicked):
        results = activity_manager.update_activity_notice_list_in_bulk(
            recipient_voter_we_vote_id=voter_we_vote_id,
            activity_notice_id_list=activity_notice_id_list_clicked,
            activity_notice_clicked=True
        )
        status += results['status']
    if activity_notice_id_list_seen and len(activity_notice_id_list_seen):
        results = activity_manager.update_activity_notice_list_in_bulk(
            recipient_voter_we_vote_id=voter_we_vote_id,
            activity_notice_id_list=activity_notice_id_list_seen,
            activity_notice_seen=True,
        )
        status += results['status']

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
                'activity_notice_clicked':          activity_notice.activity_notice_clicked,
                'activity_notice_seen':             activity_notice.activity_notice_seen,
                'date_last_changed':                activity_notice.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
                'date_of_notice':                   activity_notice.date_of_notice.strftime('%Y-%m-%d %H:%M:%S'),
                'activity_notice_id':               activity_notice.id,
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


def activity_post_save_view(request):  # activityPostSave
    """
    Save new Tidbit, or edit existing.
    :param request:
    :return:
    """
    status = ''
    activity_manager = ActivityManager()

    activity_post_we_vote_id = request.GET.get('activity_post_we_vote_id', False)
    statement_text = request.GET.get('statement_text', False)
    visibility_setting = request.GET.get('visibility_setting', False)

    if visibility_setting not in ['FRIENDS_ONLY', 'SHOW_PUBLIC']:
        visibility_setting = 'FRIENDS_ONLY'

    visibility_is_public = visibility_setting == 'SHOW_PUBLIC'

    updated_values = {
        'speaker_name':                     '',
        'speaker_organization_we_vote_id':  '',
        'speaker_twitter_followers_count':  0,
        'speaker_twitter_handle':           '',
        'speaker_voter_we_vote_id':         '',
        'speaker_profile_image_url_medium': '',
        'speaker_profile_image_url_tiny':   '',
        'statement_text':                   statement_text,
        'visibility_is_public':             visibility_is_public,
    }

    voter_device_id = get_voter_device_id(request)
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        speaker_twitter_followers_count = 0

        if positive_value_exists(voter.linked_organization_we_vote_id):
            # Is there a Twitter handle linked to this organization? If so, update the information.
            twitter_user_manager = TwitterUserManager()
            twitter_link_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
                    voter.linked_organization_we_vote_id)
            if twitter_link_results['twitter_link_to_organization_found']:
                twitter_link_to_organization = twitter_link_results['twitter_link_to_organization']

                twitter_results = \
                    twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                        twitter_link_to_organization.twitter_id)

                if twitter_results['twitter_user_found']:
                    twitter_user = twitter_results['twitter_user']
                    try:
                        speaker_twitter_followers_count = twitter_user.twitter_followers_count \
                            if positive_value_exists(twitter_user.twitter_followers_count) else 0
                    except Exception as e:
                        status += "FAILED_TO_RETRIEVE_TWITTER_FOLLOWERS_COUNT " + str(e) + ' '

        updated_values['speaker_name'] = voter.get_full_name(real_name_only=True)
        updated_values['speaker_voter_we_vote_id'] = voter.we_vote_id
        updated_values['speaker_organization_we_vote_id'] = voter.linked_organization_we_vote_id
        updated_values['speaker_profile_image_url_medium'] = voter.we_vote_hosted_profile_image_url_medium
        updated_values['speaker_profile_image_url_tiny'] = voter.we_vote_hosted_profile_image_url_tiny
        updated_values['speaker_twitter_followers_count'] = speaker_twitter_followers_count
        updated_values['speaker_twitter_handle'] = voter.twitter_screen_name

    if not positive_value_exists(updated_values['speaker_voter_we_vote_id']):
        status += "ACTIVITY_TIDBIT_SAVE_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = activity_manager.update_or_create_activity_post(
        activity_post_we_vote_id=activity_post_we_vote_id,
        updated_values=updated_values,
        speaker_voter_we_vote_id=updated_values['speaker_voter_we_vote_id'],
    )
    status += results['status']
    success = results['success']
    activity_post_dict = {}
    if results['activity_post_found']:
        activity_post = results['activity_post']
        activity_post_dict = {
            'date_created':                     activity_post.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            'date_last_changed':                activity_post.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'date_of_notice':                   activity_post.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            'id':                               activity_post.id,  # We normalize to generate activityTidbitKey
            'activity_post_id':                 activity_post.id,
            'kind_of_activity':                 'ACTIVITY_POST',
            'kind_of_seed':                     '',
            'new_positions_entered_count':      0,
            'position_we_vote_id_list':         [],
            'speaker_name':                     activity_post.speaker_name,
            'speaker_organization_we_vote_id':  activity_post.speaker_organization_we_vote_id,
            'speaker_voter_we_vote_id':         activity_post.speaker_voter_we_vote_id,
            'speaker_profile_image_url_medium': activity_post.speaker_profile_image_url_medium,
            'speaker_profile_image_url_tiny':   activity_post.speaker_profile_image_url_tiny,
            'speaker_twitter_handle':           activity_post.speaker_twitter_handle,
            'speaker_twitter_followers_count':  activity_post.speaker_twitter_followers_count,
            'statement_text':                   activity_post.statement_text,
            'visibility_is_public':             activity_post.visibility_is_public,
            'we_vote_id':                       activity_post.we_vote_id,
        }

    activity_post_dict['status'] = status
    activity_post_dict['success'] = success
    return HttpResponse(json.dumps(activity_post_dict), content_type='application/json')
