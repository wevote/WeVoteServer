# activity/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ActivityComment, ActivityNoticeSeed, ActivityManager, ActivityNotice, ActivityPost, \
    NOTICE_ACTIVITY_POST_SEED, \
    NOTICE_CAMPAIGNX_FRIEND_HAS_SUPPORTED, \
    NOTICE_CAMPAIGNX_NEWS_ITEM, NOTICE_CAMPAIGNX_NEWS_ITEM_AUTHORED, NOTICE_CAMPAIGNX_NEWS_ITEM_SEED, \
    NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_AUTHORED, NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED, \
    NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE, NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED, \
    NOTICE_FRIEND_ACTIVITY_POSTS, \
    NOTICE_FRIEND_ENDORSEMENTS, NOTICE_FRIEND_ENDORSEMENTS_SEED, \
    NOTICE_VOTER_DAILY_SUMMARY, NOTICE_VOTER_DAILY_SUMMARY_SEED
from config.base import get_environment_variable
from django.utils.timezone import now
from friend.models import FriendManager
import json
from datetime import timedelta
from reaction.models import ReactionManager
from voter.models import \
    NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL, NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS, \
    NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL, NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_SMS,\
    NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL, NOTIFICATION_VOTER_DAILY_SUMMARY_SMS, \
    VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists, return_first_x_words

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def delete_activity_comments_for_voter(voter_to_delete_we_vote_id, from_organization_we_vote_id):
    status = ''
    success = True
    activity_comment_entries_deleted = 0

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_ACTIVITY_COMMENTS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
            'activity_comment_entries_deleted': activity_comment_entries_deleted,
        }
        return results

    try:
        activity_comment_entries_deleted += ActivityComment.objects\
            .filter(commenter_voter_we_vote_id__iexact=voter_to_delete_we_vote_id)\
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_COMMENT_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
    # #############################################
    # Delete based on organization_we_vote_id
    try:
        activity_comment_entries_deleted += ActivityComment.objects \
            .filter(commenter_organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_COMMENT_DELETE-FROM_ORG_WE_VOTE_ID " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
        'activity_comment_entries_deleted': activity_comment_entries_deleted,
    }
    return results


def delete_activity_notices_for_voter(voter_to_delete_we_vote_id, from_organization_we_vote_id):
    status = ''
    success = True
    activity_notice_seed_entries_deleted = 0
    activity_notice_entries_deleted = 0

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_ACTIVITY_NOTICE_SEEDS-MISSING_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
            'activity_notice_seed_entries_deleted': activity_notice_seed_entries_deleted,
            'activity_notice_entries_deleted': activity_notice_entries_deleted,
        }
        return results

    try:
        activity_notice_seed_entries_deleted += ActivityNoticeSeed.objects\
            .filter(speaker_voter_we_vote_id__iexact=voter_to_delete_we_vote_id)\
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
    try:
        activity_notice_entries_deleted += ActivityNotice.objects\
            .filter(speaker_voter_we_vote_id__iexact=voter_to_delete_we_vote_id) \
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
    # #############################################
    # Delete based on speaker_organization_we_vote_id
    try:
        activity_notice_seed_entries_deleted += ActivityNoticeSeed.objects \
            .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-FROM_ORG_WE_VOTE_ID " + str(e) + " "
    try:
        activity_notice_entries_deleted += ActivityNotice.objects \
            .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_UPDATE-FROM_ORG_WE_VOTE_ID " + str(e) + " "

    # Now move ActivityNotice recipient_voter_we_vote_id
    try:
        activity_notice_entries_deleted += ActivityNotice.objects \
            .filter(recipient_voter_we_vote_id__iexact=voter_to_delete_we_vote_id) \
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_UPDATE-RECIPIENT " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
        'activity_notice_seed_entries_deleted': activity_notice_seed_entries_deleted,
        'activity_notice_entries_deleted': activity_notice_entries_deleted,
    }
    return results


def delete_activity_posts_for_voter(voter_to_delete_we_vote_id, from_organization_we_vote_id):
    status = ''
    success = True
    activity_post_entries_deleted = 0

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_ACTIVITY_POSTS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
            'activity_post_entries_deleted': activity_post_entries_deleted,
        }
        return results

    try:
        activity_post_entries_deleted += ActivityPost.objects\
            .filter(speaker_voter_we_vote_id__iexact=voter_to_delete_we_vote_id)\
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_POST_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
    # #############################################
    # Delete based on speaker_organization_we_vote_id
    try:
        activity_post_entries_deleted += ActivityPost.objects \
            .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .delete()
    except Exception as e:
        status += "FAILED-ACTIVITY_POST_DELETE-FROM_ORG_WE_VOTE_ID " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
        'activity_post_entries_deleted': activity_post_entries_deleted,
    }
    return results


def move_activity_comments_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, from_organization_we_vote_id, to_organization_we_vote_id,
        to_voter=None):
    status = ''
    success = True
    activity_comment_entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_ACTIVITY_COMMENTS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'to_voter_we_vote_id':              to_voter_we_vote_id,
            'activity_comment_entries_moved':   activity_comment_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_ACTIVITY_COMMENTS-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'to_voter_we_vote_id':              to_voter_we_vote_id,
            'activity_comment_entries_moved':   activity_comment_entries_moved,
        }
        return results

    # ######################
    # Migrations
    to_voter_commenter_name = ''
    commenter_profile_image_url_medium = None
    commenter_profile_image_url_tiny = None
    try:
        to_voter_commenter_name = to_voter.get_full_name()
        commenter_profile_image_url_medium = to_voter.we_vote_hosted_profile_image_url_medium
        commenter_profile_image_url_tiny = to_voter.we_vote_hosted_profile_image_url_tiny
    except Exception as e:
        status += "UNABLE_TO_GET_NAME_OR_PHOTOS: " + str(e) + " "

    if positive_value_exists(to_organization_we_vote_id):
        # Move based on commenter_voter_we_vote_id
        try:
            activity_comment_entries_moved += ActivityComment.objects\
                .filter(commenter_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(commenter_name=to_voter_commenter_name,
                        commenter_voter_we_vote_id=to_voter_we_vote_id,
                        commenter_organization_we_vote_id=to_organization_we_vote_id,
                        commenter_profile_image_url_medium=commenter_profile_image_url_medium,
                        commenter_profile_image_url_tiny=commenter_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_COMMENT_UPDATE-INCLUDING_ORG_UPDATE: " + str(e) + " "
        # #############################################
        # Move based on commenter_organization_we_vote_id
        try:
            activity_comment_entries_moved += ActivityComment.objects \
                .filter(commenter_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(commenter_name=to_voter_commenter_name,
                        commenter_voter_we_vote_id=to_voter_we_vote_id,
                        commenter_organization_we_vote_id=to_organization_we_vote_id,
                        commenter_profile_image_url_medium=commenter_profile_image_url_medium,
                        commenter_profile_image_url_tiny=commenter_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_COMMENT_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
    else:
        try:
            activity_comment_entries_moved += ActivityComment.objects\
                .filter(commenter_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(commenter_name=to_voter_commenter_name,
                        commenter_voter_we_vote_id=to_voter_we_vote_id,
                        commenter_profile_image_url_medium=commenter_profile_image_url_medium,
                        commenter_profile_image_url_tiny=commenter_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_COMMENT_UPDATE-MISSING_ORG: " + str(e) + " "

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'activity_comment_entries_moved':   activity_comment_entries_moved,
    }
    return results


def move_activity_notices_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, from_organization_we_vote_id, to_organization_we_vote_id,
        to_voter=None):
    status = ''
    success = True
    activity_notice_seed_entries_moved = 0
    activity_notice_entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_ACTIVITY_NOTICE_SEEDS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'activity_notice_seed_entries_moved':   activity_notice_seed_entries_moved,
            'activity_notice_entries_moved':        activity_notice_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_ACTIVITY_NOTICE_SEEDS-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'activity_notice_seed_entries_moved':   activity_notice_seed_entries_moved,
            'activity_notice_entries_moved':        activity_notice_entries_moved,
        }
        return results

    # ######################
    # Migrations
    to_voter_speaker_name = ''
    speaker_profile_image_url_medium = None
    speaker_profile_image_url_tiny = None
    try:
        to_voter_speaker_name = to_voter.get_full_name()
        speaker_profile_image_url_medium = to_voter.we_vote_hosted_profile_image_url_medium
        speaker_profile_image_url_tiny = to_voter.we_vote_hosted_profile_image_url_tiny
    except Exception as e:
        status += "UNABLE_TO_GET_NAME_OR_PHOTOS: " + str(e) + " "

    if positive_value_exists(to_organization_we_vote_id):
        # Move based on speaker_voter_we_vote_id
        try:
            activity_notice_seed_entries_moved += ActivityNoticeSeed.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-INCLUDING_ORG_UPDATE: " + str(e) + " "
        try:
            activity_notice_entries_moved += ActivityNotice.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
        # #############################################
        # Move based on speaker_organization_we_vote_id
        try:
            activity_notice_seed_entries_moved += ActivityNoticeSeed.objects \
                .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        try:
            activity_notice_entries_moved += ActivityNotice.objects \
                .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
    else:
        try:
            activity_notice_seed_entries_moved += ActivityNoticeSeed.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-MISSING_ORG: " + str(e) + " "
        try:
            activity_notice_entries_moved += ActivityNotice.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_UPDATE-MISSING_ORG: " + str(e) + " "

    # Now move ActivityNotice recipient_voter_we_vote_id
    try:
        activity_notice_entries_moved += ActivityNotice.objects \
            .filter(recipient_voter_we_vote_id__iexact=from_voter_we_vote_id) \
            .update(speaker_name=to_voter_speaker_name,
                    recipient_voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_UPDATE-RECIPIENT: " + str(e) + " "

    results = {
        'status':                               status,
        'success':                              success,
        'from_voter_we_vote_id':                from_voter_we_vote_id,
        'to_voter_we_vote_id':                  to_voter_we_vote_id,
        'activity_notice_seed_entries_moved':   activity_notice_seed_entries_moved,
        'activity_notice_entries_moved':        activity_notice_entries_moved,
    }
    return results


def move_activity_posts_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, from_organization_we_vote_id, to_organization_we_vote_id,
        to_voter=None):
    status = ''
    success = True
    activity_post_entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_ACTIVITY_POSTS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'activity_post_entries_moved': activity_post_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_ACTIVITY_POSTS-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'activity_post_entries_moved': activity_post_entries_moved,
        }
        return results

    # ######################
    # Migrations
    to_voter_speaker_name = ''
    speaker_profile_image_url_medium = None
    speaker_profile_image_url_tiny = None
    try:
        to_voter_speaker_name = to_voter.get_full_name()
        speaker_profile_image_url_medium = to_voter.we_vote_hosted_profile_image_url_medium
        speaker_profile_image_url_tiny = to_voter.we_vote_hosted_profile_image_url_tiny
    except Exception as e:
        status += "UNABLE_TO_GET_NAME_OR_PHOTOS: " + str(e) + " "

    if positive_value_exists(to_organization_we_vote_id):
        # Move based on speaker_voter_we_vote_id
        try:
            activity_post_entries_moved += ActivityPost.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_POST_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
        # #############################################
        # Move based on speaker_organization_we_vote_id
        try:
            activity_post_entries_moved += ActivityPost.objects \
                .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_POST_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
    else:
        try:
            activity_post_entries_moved += ActivityPost.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_name=to_voter_speaker_name,
                        speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_POST_UPDATE-MISSING_ORG: " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'activity_post_entries_moved': activity_post_entries_moved,
    }
    return results


def notice_friend_endorsements_send(
        speaker_voter_we_vote_id='',
        recipient_voter_we_vote_id='',
        invitation_message='',
        activity_tidbit_we_vote_id='',
        position_name_list=[]):
    """
    We are sending an email to the speaker's friends who are
    subscribed to NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT or NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS
    :param speaker_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param invitation_message:
    :param activity_tidbit_we_vote_id:
    :param position_name_list:
    :return:
    """
    from email_outbound.controllers import schedule_email_with_email_outbound_description
    from email_outbound.models import EmailManager, NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE
    status = ""
    success = True

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_we_vote_id(speaker_voter_we_vote_id)
    from organization.controllers import transform_web_app_url
    web_app_root_url_verified = transform_web_app_url('')  # Change to client URL if needed

    if not voter_results['voter_found']:
        error_results = {
            'status':                               "SPEAKER_VOTER_NOT_FOUND ",
            'success':                              False,
        }
        return error_results

    speaker_voter = voter_results['voter']

    recipient_voter_results = voter_manager.retrieve_voter_by_we_vote_id(recipient_voter_we_vote_id)
    if not recipient_voter_results['voter_found']:
        error_results = {
            'status':                               "RECIPIENT_VOTER_NOT_FOUND ",
            'success':                              False,
        }
        return error_results

    recipient_voter = recipient_voter_results['voter']

    email_manager = EmailManager()

    # Retrieve the email address of the original_sender (which is the person we are sending this notification to)
    recipient_email_we_vote_id = ""
    recipient_email = ""
    recipient_email_subscription_secret_key = ""
    if recipient_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(recipient_voter_we_vote_id)
        success = results['success']
        if results['email_address_object_found']:
            recipient_email_object = results['email_address_object']
            recipient_email_we_vote_id = recipient_email_object.we_vote_id
            recipient_email = recipient_email_object.normalized_email_address
            if positive_value_exists(recipient_email_object.subscription_secret_key):
                recipient_email_subscription_secret_key = recipient_email_object.subscription_secret_key
            else:
                recipient_email_subscription_secret_key = \
                    email_manager.update_email_address_with_new_subscription_secret_key(
                        email_we_vote_id=recipient_email_we_vote_id)
    else:
        # The recipient must have a valid email
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VALID_EMAIL "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Retrieve the email address of the speaker_voter - used in invitation to help the recipient understand who sent
    speaker_voter_email = ""
    speaker_voter_we_vote_id = speaker_voter.we_vote_id
    if speaker_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(speaker_voter_we_vote_id)
        if results['email_address_object_found']:
            speaker_voter_email_object = results['email_address_object']
            speaker_voter_email = speaker_voter_email_object.normalized_email_address
    else:
        # Not having an email is ok now, since the speaker_voter could have signed in with SMS or Twitter
        status += "SPEAKER_VOTER_DOES_NOT_HAVE_VALID_EMAIL "

    if positive_value_exists(recipient_email_we_vote_id):
        recipient_voter_we_vote_id = recipient_voter.we_vote_id

        # Template variables
        real_name_only = True
        recipient_name = recipient_voter.get_full_name(real_name_only)
        speaker_voter_name = speaker_voter.get_full_name(real_name_only)
        speaker_voter_photo = speaker_voter.voter_photo_url()
        speaker_voter_description = ""
        speaker_voter_network_details = ""

        if positive_value_exists(speaker_voter_name):
            subject = speaker_voter_name
        else:
            subject = "Your friend"

        activity_description = ''
        subject += " is getting ready to vote"
        if position_name_list and len(position_name_list) > 0:
            if len(position_name_list) == 1:
                # subject += " added opinion about "
                # subject += position_name_list[0]

                activity_description += "added opinion about "
                activity_description += position_name_list[0]
            elif len(position_name_list) == 2:
                # subject += " added opinions about "
                # subject += position_name_list[0]
                # subject += " and "
                # subject += position_name_list[1]

                activity_description += "added opinions about "
                activity_description += position_name_list[0]
                activity_description += " and "
                activity_description += position_name_list[1]
            elif len(position_name_list) >= 3:
                # subject += " added opinions about "
                # subject += position_name_list[0]
                # subject += ", "
                # subject += position_name_list[1]
                # subject += " and "
                # subject += position_name_list[2]

                activity_description += "added opinions about "
                activity_description += position_name_list[0]
                activity_description += ", "
                activity_description += position_name_list[1]
                activity_description += " and "
                activity_description += position_name_list[2]
            else:
                # subject += " has added new opinion"
                activity_description += "has added new opinion"
        else:
            # subject += " is getting ready to vote"
            activity_description += "is reviewing the ballot"

        # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
        # recipient_email_subscription_secret_key,

        # Unsubscribe link in email
        recipient_unsubscribe_url = \
            "{root_url}/unsubscribe/{email_secret_key}/friendopinionsall" \
            "".format(
                email_secret_key=recipient_email_subscription_secret_key,
                root_url=web_app_root_url_verified,
            )
        # Instant unsubscribe link in email header
        list_unsubscribe_url = \
            "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/friendopinionsall" \
            "".format(
                email_secret_key=recipient_email_subscription_secret_key,
                root_url=WE_VOTE_SERVER_ROOT_URL,
            )
        # Instant unsubscribe email address in email header
        # from voter.models import NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL
        list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                                  "".format(setting='friendopinionsall')

        # Variables used by templates/email_outbound/email_templates/notice_friend_endorsements.txt and .html
        template_variables_for_json = {
            "activity_description":         activity_description,
            "subject":                      subject,
            "invitation_message":           invitation_message,
            "sender_name":                  speaker_voter_name,
            "sender_photo":                 speaker_voter_photo,
            "sender_email_address":         speaker_voter_email,  # Does not affect the "From" email header
            "sender_description":           speaker_voter_description,
            "sender_network_details":       speaker_voter_network_details,
            "recipient_name":               recipient_name,
            "recipient_unsubscribe_url":    recipient_unsubscribe_url,
            "recipient_voter_email":        recipient_email,
            "view_new_endorsements_url":    web_app_root_url_verified + "/news/a/" + activity_tidbit_we_vote_id,
            "view_your_ballot_url":         web_app_root_url_verified + "/ballot",
        }
        template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

        # Create the outbound email description, then schedule it
        kind_of_email_template = NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE
        outbound_results = email_manager.create_email_outbound_description(
            sender_voter_we_vote_id=speaker_voter_we_vote_id,
            sender_voter_email=speaker_voter_email,
            sender_voter_name=speaker_voter_name,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            recipient_email_we_vote_id=recipient_email_we_vote_id,
            recipient_voter_email=recipient_email,
            template_variables_in_json=template_variables_in_json,
            kind_of_email_template=kind_of_email_template,
            list_unsubscribe_mailto=list_unsubscribe_mailto,
            list_unsubscribe_url=list_unsubscribe_url,
        )
        status += outbound_results['status'] + " "
        success = outbound_results['success']
        if outbound_results['email_outbound_description_saved']:
            email_outbound_description = outbound_results['email_outbound_description']
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
            status += schedule_results['status'] + " "
            success = schedule_results['success']
            if schedule_results['email_scheduled_saved']:
                # messages_to_send.append(schedule_results['email_scheduled_id'])
                email_scheduled = schedule_results['email_scheduled']
                send_results = email_manager.send_scheduled_email(email_scheduled)
                email_scheduled_sent = send_results['email_scheduled_sent']
                status += send_results['status']
                success = send_results['success']

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results


def assemble_voter_daily_summary(
        assemble_activity_start_date=None,
        recipient_voter_we_vote_id='',
        number_of_friends_to_display=3):
    status = ''
    success = True
    activity_manager = ActivityManager()
    friend_manager = FriendManager()
    friend_activity_dict_list = []
    reaction_manager = ReactionManager()
    subject = 'Discussion(s) have been added'
    introduction_line = 'At least one friend has added a discussion.'

    # Collect all of the data about activity in this voter's network since the last daily_summary
    current_friends_results = friend_manager.retrieve_friends_we_vote_id_list(recipient_voter_we_vote_id)
    success = current_friends_results['success']
    status += current_friends_results['status']
    if not current_friends_results['friends_we_vote_id_list_found']:
        status += "ASSEMBLE_VOTER_DAILY_SUMMARY_NO_FRIENDS_FOUND "
        results = {
            'success':                      success,
            'status':                       status,
            'friend_activity_dict_list':    friend_activity_dict_list,
            'introduction_line':            introduction_line,
            'subject':                      subject,
        }
        return results
    else:
        friends_we_vote_id_list = current_friends_results['friends_we_vote_id_list']

    # ##########################
    # Each activity post, with name, first line, # of comments and # of likes
    highest_priority_by_friend_we_vote_id = {}
    raw_list_by_friend_we_vote_id = {}
    post_results = activity_manager.retrieve_activity_post_list(
        speaker_voter_we_vote_id_list=friends_we_vote_id_list,
        since_date=assemble_activity_start_date)
    if post_results['success']:
        friends_post_list = post_results['activity_post_list']
        for one_post in friends_post_list:
            number_of_comments = activity_manager.fetch_number_of_comments(one_post.we_vote_id)
            number_of_likes = reaction_manager.fetch_number_of_likes(one_post.we_vote_id)
            # Higher priority score makes it more likely this post is at top of list
            priority_score = 0
            if not one_post.speaker_name or one_post.speaker_name.startswith('Voter-'):
                priority_score -= 20
            if one_post.speaker_profile_image_url_medium and len(one_post.speaker_profile_image_url_medium) > 1:
                priority_score += 10
            if number_of_comments > 0:
                priority_score += number_of_comments * 3
            if number_of_likes > 0:
                priority_score += number_of_likes * 1
            highlight_item_dict = {
                # 'date_created':                     one_post.date_created.strftime('%Y-%m-%d %H:%M:%S'),
                'number_of_comments':               number_of_comments,
                'number_of_likes':                  number_of_likes,
                'priority_score':                   priority_score,
                'speaker_name':                     one_post.speaker_name,
                'speaker_profile_image_url_medium': one_post.speaker_profile_image_url_medium,
                'speaker_voter_we_vote_id':         one_post.speaker_voter_we_vote_id,
                'statement_text':                   one_post.statement_text,
                'we_vote_id':                       one_post.we_vote_id,
            }
            if one_post.speaker_voter_we_vote_id in highest_priority_by_friend_we_vote_id and \
                    highest_priority_by_friend_we_vote_id[one_post.speaker_voter_we_vote_id] > priority_score:
                # Do not add this highlight_item_dict because the highlight item captured for this person
                #  already has a higher priority_score
                pass
            else:
                raw_list_by_friend_we_vote_id[one_post.speaker_voter_we_vote_id] = highlight_item_dict
                highest_priority_by_friend_we_vote_id[one_post.speaker_voter_we_vote_id] = priority_score

    # ##########################
    # Endorsements made

    # ##########################
    # Now that we know raw_list_by_friend_we_vote_id only has one highlight_item_dict per friend,
    #  drop them into simple friend_activity_dict_list so we can sort them by priority_score
    friend_activity_dict_list = raw_list_by_friend_we_vote_id.values()
    sorted(friend_activity_dict_list, key=lambda item: item['priority_score'], reverse=True)

    friend_name_list_in_order = []
    names_stored = 0
    for one_activity_dict in friend_activity_dict_list:
        if names_stored < number_of_friends_to_display:
            friend_name_list_in_order.append(one_activity_dict['speaker_name'])
            names_stored += 1

    if len(friend_name_list_in_order) > 0:
        introduction_line = ''
        subject = ''
        if len(friend_name_list_in_order) == 1:
            subject += friend_name_list_in_order[0]
            subject += " added a discussion"

            introduction_line += "Your friend "
            introduction_line += friend_name_list_in_order[0]
            introduction_line += " has added one or more discussion."
        elif len(friend_name_list_in_order) == 2:
            subject += friend_name_list_in_order[0]
            subject += " and "
            subject += friend_name_list_in_order[1]
            subject += " added discussions"

            introduction_line += "Your friends "
            introduction_line += friend_name_list_in_order[0]
            introduction_line += " and "
            introduction_line += friend_name_list_in_order[1]
            introduction_line += " have added discussions."
        elif len(friend_name_list_in_order) >= 3:
            subject += friend_name_list_in_order[0]
            subject += ", "
            subject += friend_name_list_in_order[1]
            subject += " and "
            subject += friend_name_list_in_order[2]
            subject += " added discussions"

            introduction_line += "Your friends "
            introduction_line += friend_name_list_in_order[0]
            introduction_line += ", "
            introduction_line += friend_name_list_in_order[1]
            introduction_line += " and "
            introduction_line += friend_name_list_in_order[2]
            introduction_line += " have added discussions."
    results = {
        'success':                      success,
        'status':                       status,
        'friend_activity_dict_list':    friend_activity_dict_list,
        'introduction_line':            introduction_line,
        'subject':                      subject,
    }
    return results


def notice_voter_daily_summary_send(  # NOTICE_VOTER_DAILY_SUMMARY
        recipient_voter_we_vote_id='',
        friend_activity_dict_list=[],
        introduction_line='',
        subject=''):
    """

    :param recipient_voter_we_vote_id:
    :param friend_activity_dict_list:
    :param subject:
    :param introduction_line:
    :return:
    """
    from email_outbound.controllers import schedule_email_with_email_outbound_description
    from email_outbound.models import EmailManager, NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE
    status = ""

    voter_manager = VoterManager()
    from organization.controllers import transform_web_app_url
    web_app_root_url_verified = transform_web_app_url('')  # Change to client URL if needed

    recipient_voter_results = voter_manager.retrieve_voter_by_we_vote_id(recipient_voter_we_vote_id)
    if not recipient_voter_results['voter_found']:
        error_results = {
            'status':                               "RECIPIENT_VOTER_NOT_FOUND ",
            'success':                              False,
        }
        return error_results

    recipient_voter = recipient_voter_results['voter']

    email_manager = EmailManager()

    # Retrieve the email address of the original_sender (which is the person we are sending this notification to)
    recipient_email_we_vote_id = ""
    recipient_email = ""
    recipient_email_subscription_secret_key = ""
    if recipient_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(recipient_voter_we_vote_id)
        success = results['success']
        if results['email_address_object_found']:
            recipient_email_object = results['email_address_object']
            recipient_email_we_vote_id = recipient_email_object.we_vote_id
            recipient_email = recipient_email_object.normalized_email_address
            if positive_value_exists(recipient_email_object.subscription_secret_key):
                recipient_email_subscription_secret_key = recipient_email_object.subscription_secret_key
            else:
                recipient_email_subscription_secret_key = \
                    email_manager.update_email_address_with_new_subscription_secret_key(
                        email_we_vote_id=recipient_email_we_vote_id)
    else:
        # The recipient must have a valid email
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VALID_EMAIL "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    if positive_value_exists(recipient_email_we_vote_id):
        recipient_voter_we_vote_id = recipient_voter.we_vote_id

        # Trim down friend_activity_dict_list to only x items
        number_of_highlights_to_show = 3
        number_shown = 0
        friend_activity_dict_list_modified = []
        for highlight_dict in friend_activity_dict_list:
            if number_shown < number_of_highlights_to_show:
                highlight_dict['view_activity_tidbit_url'] = \
                    web_app_root_url_verified + "/news/a/" + highlight_dict['we_vote_id']
                friend_activity_dict_list_modified.append(highlight_dict)
                number_shown += 1

        # Template variables
        real_name_only = True
        recipient_name = recipient_voter.get_full_name(real_name_only)
        # speaker_voter_name = speaker_voter.get_full_name(real_name_only)
        # speaker_voter_photo = speaker_voter.voter_photo_url()
        # speaker_voter_description = ""
        # speaker_voter_network_details = ""

        # Variables used by templates/email_outbound/email_templates/friend_accepted_invitation.txt and .html
        if not positive_value_exists(subject):
            subject = "Your friends have commented"

        # Unsubscribe link in email
        # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
        # recipient_email_subscription_secret_key,
        recipient_unsubscribe_url = \
            "{root_url}/unsubscribe/{email_secret_key}/dailyfriendactivity" \
            "".format(
                email_secret_key=recipient_email_subscription_secret_key,
                root_url=web_app_root_url_verified,
            )
        # Instant unsubscribe link in email header
        list_unsubscribe_url = \
            "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/dailyfriendactivity" \
            "".format(
                email_secret_key=recipient_email_subscription_secret_key,
                root_url=WE_VOTE_SERVER_ROOT_URL,
            )
        # Instant unsubscribe email address in email header
        # from voter.models import NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL
        list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                                  "".format(setting='dailyfriendactivity')

        template_variables_for_json = {
            "introduction_line":                introduction_line,
            "subject":                          subject,
            "friend_activity_dict_list":        friend_activity_dict_list_modified,
            # "sender_name":                  speaker_voter_name,
            # "sender_photo":                 speaker_voter_photo,
            # "sender_email_address":         speaker_voter_email,  # Does not affect the "From" email header
            # "sender_description":           speaker_voter_description,
            # "sender_network_details":       speaker_voter_network_details,
            "recipient_name":                   recipient_name,
            "recipient_unsubscribe_url":        recipient_unsubscribe_url,
            "recipient_voter_email":            recipient_email,
            "view_main_discussion_page_url":    web_app_root_url_verified + "/news",
            "view_your_ballot_url":             web_app_root_url_verified + "/ballot",
        }
        template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
        from_email_for_daily_summary = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

        # Create the outbound email description, then schedule it
        kind_of_email_template = NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE
        outbound_results = email_manager.create_email_outbound_description(
            sender_voter_we_vote_id=recipient_voter_we_vote_id,
            sender_voter_email=from_email_for_daily_summary,
            sender_voter_name='',
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            recipient_email_we_vote_id=recipient_email_we_vote_id,
            recipient_voter_email=recipient_email,
            template_variables_in_json=template_variables_in_json,
            kind_of_email_template=kind_of_email_template,
            list_unsubscribe_mailto=list_unsubscribe_mailto,
            list_unsubscribe_url=list_unsubscribe_url,
        )
        status += outbound_results['status'] + " "
        success = outbound_results['success']
        if outbound_results['email_outbound_description_saved']:
            email_outbound_description = outbound_results['email_outbound_description']
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
            status += schedule_results['status'] + " "
            success = schedule_results['success']
            if schedule_results['email_scheduled_saved']:
                # messages_to_send.append(schedule_results['email_scheduled_id'])
                email_scheduled = schedule_results['email_scheduled']
                send_results = email_manager.send_scheduled_email(email_scheduled)
                email_scheduled_sent = send_results['email_scheduled_sent']
                status += send_results['status']
                success = send_results['success']

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results


def process_activity_notice_seeds_triggered_by_batch_process():
    """
    We assume only one of this function is running at any time.
    :return:
    """
    status = ''
    success = True
    activity_notice_seed_count = 0
    activity_notice_count = 0

    # Retrieve ActivityNoticeSeeds that need to have some processing done, including ActivityNotice entries created
    activity_manager = ActivityManager()
    # We want this process to stop before it has run for 5 minutes, so that we don't collide with another process
    #  starting. Please also see: activity_notice_processing_time_out_duration & checked_out_expiration_time
    # We adjust timeout for ACTIVITY_NOTICE_PROCESS in retrieve_batch_process_list
    longest_activity_notice_processing_run_time_allowed = 270  # 4.5 minutes * 60 seconds
    when_process_must_stop = now() + timedelta(seconds=longest_activity_notice_processing_run_time_allowed)

    # Update existing ActivityNoticeSeed entries (notices_to_be_updated=True)
    # Only run this when the minutes are divisible by "5"
    # Note: Because of other processes running we cannot count on every entry updating every 5 minutes -- there
    #  is some randomness to when they get updated
    update_interval = 5
    time_now = now()
    if time_now.minute % update_interval == 0:
        continue_retrieving_notices_to_be_updated = True
        activity_notice_seed_id_already_reviewed_list = []
        safety_valve_count = 0
        while continue_retrieving_notices_to_be_updated and \
                safety_valve_count < 1000 and \
                when_process_must_stop > now():
            safety_valve_count += 1
            results = activity_manager.retrieve_next_activity_notice_seed_to_process(
                notices_to_be_updated=True,
                activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
            if results['activity_notice_seed_found']:
                # We retrieve from these seed types:
                #   NOTICE_ACTIVITY_POST_SEED
                #   NOTICE_FRIEND_ENDORSEMENTS_SEED
                # We do not need to update (we create once elsewhere and do not update):
                #   NOTICE_CAMPAIGNX_NEWS_ITEM_SEED
                #   NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED
                #   NOTICE_VOTER_DAILY_SUMMARY_SEED
                activity_notice_seed = results['activity_notice_seed']
                activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
                activity_notice_seed_count += 1
                status += "[updated:: "
                status += "activity_notice_seed_id: " + str(activity_notice_seed.id) + " "
                status += "kind_of_seed: " + str(activity_notice_seed.kind_of_seed) + ""
                status += "] "
                update_activity_notices = False

                if activity_notice_seed.kind_of_seed == NOTICE_ACTIVITY_POST_SEED:
                    # We are storing number_of_comments and number_of_likes in NOTICE_ACTIVITY_POST_SEED, so we need
                    #  to update in case there have been changes.
                    update_seed_results = \
                        update_activity_notice_seed_date_of_notice_earlier_than_update_window(activity_notice_seed)
                    status += update_seed_results['status']
                    if update_seed_results['success']:
                        activity_notice_seed = update_seed_results['activity_notice_seed']
                    if not activity_notice_seed.date_of_notice_earlier_than_update_window:
                        update_activity_notices = True
                elif activity_notice_seed.kind_of_seed == NOTICE_FRIEND_ENDORSEMENTS_SEED:
                    update_seed_results = \
                        update_activity_notice_seed_date_of_notice_earlier_than_update_window(activity_notice_seed)
                    status += update_seed_results['status']
                    if update_seed_results['success']:
                        activity_notice_seed = update_seed_results['activity_notice_seed']
                    if not activity_notice_seed.date_of_notice_earlier_than_update_window:
                        # Only update if the number of positions has changed
                        update_seed_results = update_activity_notice_seed_with_positions(activity_notice_seed)
                        activity_notice_seed = update_seed_results['activity_notice_seed']
                        update_activity_notices = True

                if update_activity_notices:
                    # Update the activity drop down in each voter touched (friends of the voter acting)
                    update_results = update_or_create_activity_notices_from_seed(activity_notice_seed)
                    status += update_results['status']  # Show all status for now
                    # if not update_results['success']:
                    #     status += update_results['status']
            else:
                continue_retrieving_notices_to_be_updated = False

    # Create new ActivityNotice entries, which appear in header notification menu (notices_to_be_created=True)
    continue_retrieving_notices_to_be_created = True
    activity_notice_seed_id_already_reviewed_list = []  # Reset
    safety_valve_count = 0
    while continue_retrieving_notices_to_be_created and safety_valve_count < 1000 and when_process_must_stop > now():
        safety_valve_count += 1
        results = activity_manager.retrieve_next_activity_notice_seed_to_process(
            notices_to_be_created=True,
            activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
        if results['activity_notice_seed_found']:
            # We retrieve from these seed types:
            #   NOTICE_ACTIVITY_POST_SEED
            #   NOTICE_CAMPAIGNX_NEWS_ITEM_SEED
            #   NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED
            #   NOTICE_FRIEND_ENDORSEMENTS_SEED
            activity_notice_seed = results['activity_notice_seed']
            activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
            activity_notice_seed_count += 1
            status += "[created:: "
            status += "activity_notice_seed_id: " + str(activity_notice_seed.id) + " "
            status += "kind_of_seed: " + str(activity_notice_seed.kind_of_seed) + ""
            status += "] "

            # Create the activity drop down in each voter's header for each voter touched (friends of the voter acting)
            create_results = update_or_create_activity_notices_from_seed(activity_notice_seed)
            # activity_notice_seed.activity_notices_created = True  # Marked in function immediately above
            activity_notice_count += create_results['activity_notice_count']

            # NOTE: Since the daily summary is only sent once per day, wait to create NOTICE_VOTER_DAILY_SUMMARY_SEED
            #  in the update step above
        else:
            continue_retrieving_notices_to_be_created = False

    # Create NOTICE_VOTER_DAILY_SUMMARY_SEED entries for any other SEED that needs to go into the DAILY_SUMMARY
    # We retrieve from these seed types: NOTICE_ACTIVITY_POST_SEED, NOTICE_FRIEND_ENDORSEMENTS_SEED
    continue_retrieving_to_be_added_to_voter_summary = True
    activity_notice_seed_id_already_reviewed_list = []
    safety_valve_count = 0
    while continue_retrieving_to_be_added_to_voter_summary and \
            safety_valve_count < 1000 and \
            when_process_must_stop > now():
        safety_valve_count += 1
        results = activity_manager.retrieve_next_activity_notice_seed_to_process(
            to_be_added_to_voter_daily_summary=True,
            activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
        if results['activity_notice_seed_found']:
            # We retrieve from these seed types: NOTICE_ACTIVITY_POST_SEED, NOTICE_FRIEND_ENDORSEMENTS_SEED
            activity_notice_seed = results['activity_notice_seed']
            activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
            activity_notice_seed_count += 1
            status += "[daily_summary:: "
            status += "activity_notice_seed_id: " + str(activity_notice_seed.id) + " "
            status += "kind_of_seed: " + str(activity_notice_seed.kind_of_seed) + ""
            status += "] "
            # Create the seeds (one for each voter touched) which will be used to send a daily summary
            #  to each voter touched. So we end up with new NOTICE_VOTER_DAILY_SUMMARY_SEED entries for the friends
            #  of the creators of these seeds: NOTICE_ACTIVITY_POST_SEED, NOTICE_FRIEND_ENDORSEMENTS_SEED
            update_results = update_or_create_voter_daily_summary_seeds_from_seed(activity_notice_seed)
            # if not update_results['success']:
            status += update_results['status']
        else:
            continue_retrieving_to_be_added_to_voter_summary = False

    # Send email notifications (notices_to_be_scheduled=True)
    continue_retrieving_notices_to_be_scheduled = True
    activity_notice_seed_id_already_reviewed_list = []  # Reset
    safety_valve_count = 0
    while continue_retrieving_notices_to_be_scheduled and safety_valve_count < 1000 and when_process_must_stop > now():
        safety_valve_count += 1
        results = activity_manager.retrieve_next_activity_notice_seed_to_process(
            notices_to_be_scheduled=True,
            activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
        if results['activity_notice_seed_found']:
            # We retrieve from these seed types:
            #  NOTICE_CAMPAIGNX_NEWS_ITEM_SEED
            #  NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED
            #  NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED
            #  NOTICE_FRIEND_ENDORSEMENTS_SEED
            #  NOTICE_VOTER_DAILY_SUMMARY_SEED
            activity_notice_seed = results['activity_notice_seed']
            activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
            # activity_notice_seed_count += 1
            schedule_results = schedule_activity_notices_from_seed(activity_notice_seed)
            # activity_notice_seed.activity_notices_scheduled = True  # Marked in function immediately above
            # if not schedule_results['success']:
            status += schedule_results['status']
            # activity_notice_count += create_results['activity_notice_count']
        else:
            continue_retrieving_notices_to_be_scheduled = False

    results = {
        'success':                      success,
        'status':                       status,
        'activity_notice_seed_count':   activity_notice_seed_count,
        'activity_notice_count':        activity_notice_count,
    }
    return results


def update_or_create_activity_notices_from_seed(activity_notice_seed):
    status = ''
    success = True
    activity_notice_count = 0
    from campaign.models import CampaignXManager
    campaignx_manager = CampaignXManager()
    activity_manager = ActivityManager()
    friend_manager = FriendManager()
    reaction_manager = ReactionManager()

    # Create or update ActivityNotice entries for the person who generated activity_notice_seed
    if positive_value_exists(activity_notice_seed.campaignx_we_vote_id):
        if activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_NEWS_ITEM_SEED:
            # #########
            # Notice to the creator for drop down.
            results = campaignx_manager.retrieve_campaignx(
                campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                read_only=True
            )
            statement_subject = ''
            if results['campaignx_found']:
                statement_subject = results['campaignx'].campaign_title
            kind_of_notice = NOTICE_CAMPAIGNX_NEWS_ITEM_AUTHORED
            activity_results = update_or_create_activity_notice_for_campaignx_news_item(
                activity_notice_seed_id=activity_notice_seed.id,
                campaignx_news_item_we_vote_id=activity_notice_seed.campaignx_news_item_we_vote_id,
                campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                kind_of_seed=activity_notice_seed.kind_of_seed,
                kind_of_notice=kind_of_notice,
                recipient_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                send_to_email=False,
                send_to_sms=False,
                speaker_name=activity_notice_seed.speaker_name,
                speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                speaker_profile_image_url_medium=activity_notice_seed.speaker_profile_image_url_medium,
                speaker_profile_image_url_tiny=activity_notice_seed.speaker_profile_image_url_tiny,
                statement_subject=statement_subject,
                statement_text_preview=activity_notice_seed.statement_text_preview)
            if activity_results['success']:
                activity_notice_count += 1
                status += activity_results['status']  # We may be able to remove this later to reduce log size
            else:
                status += activity_results['status']
            # Note there are more activity_notice entries for NOTICE_CAMPAIGNX_NEWS_ITEM_SEED created below
        elif activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED:
            # #########
            # Notice to the creator for drop down. Email is sent by the processing of the ActivityNoticeSeed.
            kind_of_notice = NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE
            activity_results = update_or_create_activity_notice_for_campaignx_supporter_initial_response(
                activity_notice_seed_id=activity_notice_seed.id,
                campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                kind_of_seed=activity_notice_seed.kind_of_seed,
                kind_of_notice=kind_of_notice,
                recipient_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                send_to_email=False,
                send_to_sms=False,
                speaker_name=activity_notice_seed.speaker_name,
                speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                speaker_profile_image_url_medium=activity_notice_seed.speaker_profile_image_url_medium,
                speaker_profile_image_url_tiny=activity_notice_seed.speaker_profile_image_url_tiny,
                statement_text_preview=activity_notice_seed.statement_text_preview)
            if activity_results['success']:
                activity_notice_count += 1
                status += activity_results['status']  # We may be able to remove this later to reduce log size
            else:
                status += activity_results['status']

    # Seeds that require a friend list to be found
    if activity_notice_seed.kind_of_seed in [
        NOTICE_ACTIVITY_POST_SEED,
        NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED,
        NOTICE_FRIEND_ENDORSEMENTS_SEED,
    ]:
        # Retrieve all friends of activity_notice_seed.speaker_voter_we_vote_id
        status += "KIND_OF_LIST_CURRENT_FRIENDS_ACTIVITY_NOTICES "
        retrieve_current_friends_as_voters_results = \
            friend_manager.retrieve_current_friends_as_voters(
                voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id, read_only=True)
        success = retrieve_current_friends_as_voters_results['success']
        status += retrieve_current_friends_as_voters_results['status']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friend_list = retrieve_current_friends_as_voters_results['friend_list']
            if activity_notice_seed.kind_of_seed == NOTICE_ACTIVITY_POST_SEED:
                # Pop the last activity_tidbit_we_vote_id
                activity_tidbit_we_vote_id = ''
                if positive_value_exists(activity_notice_seed.activity_tidbit_we_vote_ids_for_friends_serialized):
                    activity_tidbit_we_vote_id_list_for_friends = \
                        json.loads(activity_notice_seed.activity_tidbit_we_vote_ids_for_friends_serialized)
                    if len(activity_tidbit_we_vote_id_list_for_friends) > 0:
                        activity_tidbit_we_vote_id = activity_tidbit_we_vote_id_list_for_friends.pop()
                if not positive_value_exists(activity_tidbit_we_vote_id):
                    if positive_value_exists(activity_notice_seed.activity_tidbit_we_vote_ids_for_public_serialized):
                        activity_tidbit_we_vote_id_list_for_public = \
                            json.loads(activity_notice_seed.activity_tidbit_we_vote_ids_for_public_serialized)
                        if len(activity_tidbit_we_vote_id_list_for_public) > 0:
                            activity_tidbit_we_vote_id = activity_tidbit_we_vote_id_list_for_public.pop()
                if positive_value_exists(activity_tidbit_we_vote_id):
                    number_of_comments = activity_manager.fetch_number_of_comments(
                        parent_we_vote_id=activity_tidbit_we_vote_id)
                    number_of_likes = reaction_manager.fetch_number_of_likes(activity_tidbit_we_vote_id)
                    kind_of_notice = NOTICE_FRIEND_ACTIVITY_POSTS
                    for friend_voter in current_friend_list:
                        # ###########################
                        # NOTE: We call update_or_create_voter_daily_summary_seeds_from_seed from the same place
                        #  (process_activity_notice_seeds_triggered_by_batch_process) we call the function
                        #  we are currently in. We don't do it here.

                        # ###########################
                        # This is the entry that goes in the header drop-down
                        activity_results = update_or_create_activity_notice_for_friend_posts(
                            activity_notice_seed_id=activity_notice_seed.id,
                            activity_tidbit_we_vote_id=activity_tidbit_we_vote_id,
                            kind_of_seed=activity_notice_seed.kind_of_seed,
                            kind_of_notice=kind_of_notice,
                            number_of_comments=number_of_comments,
                            number_of_likes=number_of_likes,
                            recipient_voter_we_vote_id=friend_voter.we_vote_id,
                            send_to_email=False,
                            send_to_sms=False,
                            speaker_name=activity_notice_seed.speaker_name,
                            speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                            speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                            speaker_profile_image_url_medium=activity_notice_seed.speaker_profile_image_url_medium,
                            speaker_profile_image_url_tiny=activity_notice_seed.speaker_profile_image_url_tiny,
                            statement_text_preview=activity_notice_seed.statement_text_preview)
                        if activity_results['success']:
                            activity_notice_count += 1
                        else:
                            status += activity_results['status']
            elif activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED:
                if positive_value_exists(activity_notice_seed.campaignx_we_vote_id):
                    # #########
                    # Notices (and emails) to the creator's friends
                    kind_of_notice = NOTICE_CAMPAIGNX_FRIEND_HAS_SUPPORTED
                    twelve_hours_of_seconds = 12 * 60 * 60
                    for friend_voter in current_friend_list:
                        # Has the friend already signed this campaign? If so, don't send another email.
                        is_voter_campaignx_supporter = campaignx_manager.is_voter_campaignx_supporter(
                            campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                            voter_we_vote_id=friend_voter.we_vote_id)
                        # Has the friend already received an email about this supporter signing a campaign recently?
                        # If so, don't email any more notices for twelve_hours_of_seconds
                        activity_notice_count = activity_manager.fetch_activity_notice_count(
                            activity_in_last_x_seconds=twelve_hours_of_seconds,
                            kind_of_notice=kind_of_notice,
                            recipient_voter_we_vote_id=friend_voter.we_vote_id,
                            send_to_email=True,
                            speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                        )
                        if is_voter_campaignx_supporter or activity_notice_count > 0:
                            send_to_email = False
                            send_to_sms = False
                        else:
                            # Decide whether to send email or sms based on friend's notification settings
                            # We will need to figure out if this endorsement is on this voter's ballot
                            # NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL
                            # NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL
                            send_to_email = friend_voter.is_notification_status_flag_set(
                                NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL)
                            # NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_SMS
                            # NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS
                            send_to_sms = friend_voter.is_notification_status_flag_set(
                                NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS)

                        # ###########################
                        # This is the entry that goes in the header drop-down
                        activity_results = update_or_create_activity_notice_for_friend_campaignx_support(
                            activity_notice_seed_id=activity_notice_seed.id,
                            campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                            kind_of_seed=activity_notice_seed.kind_of_seed,
                            kind_of_notice=kind_of_notice,
                            recipient_voter_we_vote_id=friend_voter.we_vote_id,
                            send_to_email=send_to_email,
                            send_to_sms=send_to_sms,
                            speaker_name=activity_notice_seed.speaker_name,
                            speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                            speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                            speaker_profile_image_url_medium=activity_notice_seed.speaker_profile_image_url_medium,
                            speaker_profile_image_url_tiny=activity_notice_seed.speaker_profile_image_url_tiny,
                            statement_text_preview=activity_notice_seed.statement_text_preview)
                        if activity_results['success']:
                            activity_notice_count += 1
                        else:
                            status += activity_results['status']
            elif activity_notice_seed.kind_of_seed == NOTICE_FRIEND_ENDORSEMENTS_SEED:
                kind_of_notice = NOTICE_FRIEND_ENDORSEMENTS
                # Names for quick summaries
                position_name_list = []
                if positive_value_exists(activity_notice_seed.position_names_for_friends_serialized):
                    position_name_list_for_friends = \
                        json.loads(activity_notice_seed.position_names_for_friends_serialized)
                    position_name_list += position_name_list_for_friends
                if positive_value_exists(activity_notice_seed.position_names_for_public_serialized):
                    position_name_list_for_public = \
                        json.loads(activity_notice_seed.position_names_for_public_serialized)
                    position_name_list += position_name_list_for_public
                position_name_list_serialized = json.dumps(position_name_list)
                # We Vote Ids for full position display
                position_we_vote_id_list = []
                if positive_value_exists(
                        activity_notice_seed.position_we_vote_ids_for_friends_serialized):
                    position_we_vote_id_list_for_friends = \
                        json.loads(activity_notice_seed.position_we_vote_ids_for_friends_serialized)
                    position_we_vote_id_list += position_we_vote_id_list_for_friends
                if positive_value_exists(
                        activity_notice_seed.position_we_vote_ids_for_public_serialized):
                    position_we_vote_id_list_for_public = \
                        json.loads(activity_notice_seed.position_we_vote_ids_for_public_serialized)
                    position_we_vote_id_list += position_we_vote_id_list_for_public
                position_we_vote_id_list_serialized = json.dumps(position_we_vote_id_list)

                for friend_voter in current_friend_list:
                    # Add switch for NOTICE_FRIEND_ACTIVITY_POSTS here

                    # Decide whether to send email or sms based on friend's notification settings
                    # We will need to figure out if this endorsement is on this voter's ballot
                    # NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL
                    # NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL
                    send_to_email = friend_voter.is_notification_status_flag_set(
                        NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL)
                    # NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_SMS
                    # NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS
                    send_to_sms = friend_voter.is_notification_status_flag_set(
                        NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS)

                    # ###########################
                    # This is the entry that goes in the header drop-down
                    activity_results = update_or_create_activity_notice_for_friend_endorsements(
                        activity_notice_seed_id=activity_notice_seed.id,
                        activity_tidbit_we_vote_id=activity_notice_seed.we_vote_id,
                        kind_of_seed=activity_notice_seed.kind_of_seed,
                        kind_of_notice=kind_of_notice,
                        position_name_list_serialized=position_name_list_serialized,
                        position_we_vote_id_list_serialized=position_we_vote_id_list_serialized,
                        recipient_voter_we_vote_id=friend_voter.we_vote_id,
                        send_to_email=send_to_email,
                        send_to_sms=send_to_sms,
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
            status += "CREATE_ACTIVITY_NOTICES_FROM_SEED_NO_FRIENDS "

    # These do not require friends for the notices
    if activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_NEWS_ITEM_SEED:
        if positive_value_exists(activity_notice_seed.campaignx_we_vote_id):
            # #########
            # Notices (and emails) to the campaignx subscribers
            kind_of_notice = NOTICE_CAMPAIGNX_NEWS_ITEM
            campaignx_supporter_list = []
            results = campaignx_manager.retrieve_campaignx_supporter_list(
                campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                limit=0,
                read_only=True,
            )
            if results['supporter_list_found']:
                campaignx_supporter_list = results['supporter_list']
            for campaignx_supporter in campaignx_supporter_list:
                if positive_value_exists(campaignx_supporter.is_subscribed_by_email):
                    send_to_email = True
                    send_to_sms = False
                else:
                    send_to_email = False
                    send_to_sms = False

                # ###########################
                # This is the entry that goes in the header drop-down
                activity_results = update_or_create_activity_notice_for_campaignx_news_item(
                    activity_notice_seed_id=activity_notice_seed.id,
                    campaignx_news_item_we_vote_id=activity_notice_seed.campaignx_news_item_we_vote_id,
                    campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                    kind_of_seed=activity_notice_seed.kind_of_seed,
                    kind_of_notice=kind_of_notice,
                    recipient_voter_we_vote_id=campaignx_supporter.voter_we_vote_id,
                    send_to_email=send_to_email,
                    send_to_sms=send_to_sms,
                    speaker_name=activity_notice_seed.speaker_name,
                    speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                    speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                    speaker_profile_image_url_medium=activity_notice_seed.speaker_profile_image_url_medium,
                    speaker_profile_image_url_tiny=activity_notice_seed.speaker_profile_image_url_tiny,
                    statement_subject=activity_notice_seed.statement_subject,
                    statement_text_preview=activity_notice_seed.statement_text_preview)
                if activity_results['success']:
                    activity_notice_count += 1
                else:
                    status += activity_results['status']

    # Note: We don't create notices for: NOTICE_VOTER_DAILY_SUMMARY_SEED

    try:
        activity_notice_seed.activity_notices_created = True
        activity_notice_seed.save()
        status += "CREATE_ACTIVITY_NOTICES_FROM_SEED_MARKED_CREATED "
    except Exception as e:
        status += "CREATE_ACTIVITY_NOTICES_FROM_SEED_CANNOT_MARK_NOTICES_CREATED: " + str(e) + " "
        success = False

    results = {
        'success':                  success,
        'status':                   status,
        'activity_notice_count':    activity_notice_count,
    }
    return results


def update_or_create_voter_daily_summary_seed(
        recipient_name='',
        recipient_voter_we_vote_id='',
        send_to_email=False,
        send_to_sms=False,
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        update_only=False):
    """

    :param recipient_name:
    :param recipient_voter_we_vote_id:
    :param send_to_email:
    :param send_to_sms:
    :param speaker_organization_we_vote_id: The person's organization who has done something
    :param speaker_voter_we_vote_id: The person who has done something
    :param update_only:
    :return:
    """
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_seed_from_listener(
        kind_of_seed=NOTICE_VOTER_DAILY_SUMMARY_SEED,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
    )
    if results['activity_notice_seed_found']:
        status += "WE_DO_NOT_NEED_TO_UPDATE_NOTICE_VOTER_DAILY_SUMMARY_SEED "
        # activity_notice_seed = results['activity_notice_seed']
        # change_detected = False
        # try:
        #     # DALE Sept 6, 2020: I'm not 100% sure we need to update NOTICE_VOTER_DAILY_SUMMARY_SEED with this data
        #     #  since when we generate the daily summary email we are just querying against activity since the last
        #     #  summary was sent.
        #     if positive_value_exists(speaker_organization_we_vote_id):
        #         speaker_organization_we_vote_ids = []
        #         if positive_value_exists(activity_notice_seed.speaker_organization_we_vote_ids_serialized):
        #             # Deserialize
        #             speaker_organization_we_vote_ids = \
        #                 json.loads(activity_notice_seed.speaker_organization_we_vote_ids_serialized)
        #         if speaker_organization_we_vote_id not in speaker_organization_we_vote_ids:
        #             speaker_organization_we_vote_ids.append(speaker_organization_we_vote_id)
        #             change_detected = True
        #         # Then serialize
        #         speaker_organization_we_vote_ids_serialized = json.dumps(speaker_organization_we_vote_ids)
        #         activity_notice_seed.speaker_organization_we_vote_ids_serialized = \
        #             speaker_organization_we_vote_ids_serialized
        #
        #     if positive_value_exists(speaker_voter_we_vote_id):
        #         speaker_voter_we_vote_ids = []
        #         if positive_value_exists(activity_notice_seed.speaker_voter_we_vote_ids_serialized):
        #             # Deserialize
        #             speaker_voter_we_vote_ids = json.loads(activity_notice_seed.speaker_voter_we_vote_ids_serialized)
        #         if speaker_voter_we_vote_id not in speaker_voter_we_vote_ids:
        #             speaker_voter_we_vote_ids.append(speaker_voter_we_vote_id)
        #             change_detected = True
        #         # Then serialize
        #         speaker_voter_we_vote_ids_serialized = json.dumps(speaker_voter_we_vote_ids)
        #         activity_notice_seed.speaker_voter_we_vote_ids_serialized = speaker_voter_we_vote_ids_serialized
        #
        #     if activity_notice_seed.recipient_name != recipient_name:
        #         activity_notice_seed.recipient_name = recipient_name
        #         change_detected = True
        #     if positive_value_exists(change_detected):
        #         activity_notice_seed.save()
        # except Exception as e:
        #     status += "COULD_NOT_UPDATE_ACTIVITY_NOTICE_SEED_FOR_POSTS: " + str(e) + " "
        # status += results['status']
    elif update_only:
        status += "DID_NOT_CREATE_SEED-UPDATE_ONLY_MODE "
    elif results['success']:
        if positive_value_exists(send_to_email) or positive_value_exists(send_to_sms):
            date_of_notice = now()
            speaker_organization_we_vote_ids = [speaker_organization_we_vote_id]
            speaker_organization_we_vote_ids_serialized = json.dumps(speaker_organization_we_vote_ids)
            speaker_voter_we_vote_ids = [speaker_voter_we_vote_id]
            speaker_voter_we_vote_ids_serialized = json.dumps(speaker_voter_we_vote_ids)

            create_results = activity_manager.create_activity_notice_seed(
                date_of_notice=date_of_notice,
                kind_of_seed=NOTICE_VOTER_DAILY_SUMMARY_SEED,
                recipient_name=recipient_name,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                send_to_email=send_to_email,
                send_to_sms=send_to_sms,
                speaker_organization_we_vote_ids_serialized=speaker_organization_we_vote_ids_serialized,
                speaker_voter_we_vote_ids_serialized=speaker_voter_we_vote_ids_serialized)
            status += create_results['status']
        else:
            status += "NOT_SENDING-NEITHER_SEND_TO_EMAIL_NOR_SMS_SET "
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_voter_daily_summary_seeds_from_seed(activity_notice_seed):
    """
    Take in seeds like NOTICE_ACTIVITY_POST_SEED and create a NOTICE_VOTER_DAILY_SUMMARY_SEED for
    each of the speaker_voter's friends
    :param activity_notice_seed:
    :return:
    """
    status = ''
    success = True
    activity_notice_count = 0
    friend_manager = FriendManager()
    seed_types_that_always_cause_the_creation_of_voter_daily_summary_seed = [NOTICE_ACTIVITY_POST_SEED]

    # Who needs to see a notice?
    audience = 'FRIENDS'
    # audience = 'ONE_FRIEND'
    if audience == 'FRIENDS':
        # Retrieve all friends of activity_notice_seed.speaker_voter_we_vote_id
        status += "KIND_OF_LIST_CURRENT_FRIENDS_DAILY_SUMMARY "
        retrieve_current_friends_as_voters_results = \
            friend_manager.retrieve_current_friends_as_voters(
                voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id, read_only=True)
        success = retrieve_current_friends_as_voters_results['success']
        status += retrieve_current_friends_as_voters_results['status']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friend_list = retrieve_current_friends_as_voters_results['friend_list']
            for friend_voter in current_friend_list:
                create_voter_daily_summary_seed_for_this_voter = False
                update_only = False
                if activity_notice_seed.kind_of_seed == NOTICE_FRIEND_ENDORSEMENTS_SEED:
                    # Add friend endorsements to a daily summary of activity: NOTICE_VOTER_DAILY_SUMMARY
                    #  if a NOTICE_VOTER_DAILY_SUMMARY has already been created
                    #  OR if this voter has this notification setting turned off
                    create_voter_daily_summary_seed_for_this_voter = True
                    opinions_email_turned_on = friend_voter.is_notification_status_flag_set(
                        NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL)
                    if positive_value_exists(opinions_email_turned_on):
                        # Since the friend_voter is already getting a notice about the speaker_voter's endorsements
                        #  don't create a VOTER_DAILY_SUMMARY *just* for NOTICE_FRIEND_ENDORSEMENTS
                        #  but updating is ok.
                        update_only = True
                elif activity_notice_seed.kind_of_seed \
                        in seed_types_that_always_cause_the_creation_of_voter_daily_summary_seed:
                    create_voter_daily_summary_seed_for_this_voter = True

                # Decide whether to send email or sms based on friend's notification settings
                send_to_email = friend_voter.is_notification_status_flag_set(
                    NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL)
                send_to_sms = friend_voter.is_notification_status_flag_set(
                    NOTIFICATION_VOTER_DAILY_SUMMARY_SMS)

                if create_voter_daily_summary_seed_for_this_voter:
                    results = update_or_create_voter_daily_summary_seed(
                        recipient_name=friend_voter.get_full_name(real_name_only=True),
                        recipient_voter_we_vote_id=friend_voter.we_vote_id,
                        send_to_email=send_to_email,
                        send_to_sms=send_to_sms,
                        speaker_organization_we_vote_id=activity_notice_seed.speaker_organization_we_vote_id,
                        speaker_voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
                        update_only=update_only,
                    )
                    status += results['status']
        else:
            status += "CREATE_DAILY_SUMMARY_FROM_SEED_NO_FRIENDS "

    try:
        activity_notice_seed.added_to_voter_daily_summary = True
        activity_notice_seed.save()
        status += "MARKED_ADDED_TO_VOTER_DAILY_SUMMARY "
    except Exception as e:
        status += "ADDED_TO_VOTER_DAILY_SUMMARY-CANNOT_MARK_CREATED: " + str(e) + " "
        success = False

    results = {
        'success':                  success,
        'status':                   status,
        'activity_notice_count':    activity_notice_count,
    }
    return results


def schedule_activity_notices_from_seed(activity_notice_seed):
    status = ''
    success = True
    activity_notice_count = 0
    activity_manager = ActivityManager()

    # This is a switch with different branches for:
    #  NOTICE_CAMPAIGNX_NEWS_ITEM_SEED
    #  NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED
    #  NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED
    #  NOTICE_FRIEND_ENDORSEMENTS_SEED
    #  NOTICE_VOTER_DAILY_SUMMARY_SEED
    if activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_NEWS_ITEM_SEED:
        from campaign.controllers_email_outbound import campaignx_news_item_send
        from campaign.controllers import fetch_sentence_string_from_politician_list
        from campaign.models import CampaignXManager
        from organization.controllers import transform_campaigns_url
        campaignx_manager = CampaignXManager()
        voter_manager = VoterManager()

        campaigns_root_url_verified = transform_campaigns_url('')  # Change to client URL if needed
        results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id)
        campaignx_title = ''
        campaignx_url = campaigns_root_url_verified + '/id/' + activity_notice_seed.campaignx_we_vote_id  # Default link
        we_vote_hosted_campaign_photo_large_url = ''
        if results['campaignx_found']:
            campaignx = results['campaignx']
            campaignx_title = campaignx.campaign_title
            if positive_value_exists(campaignx.seo_friendly_path):
                campaignx_url = campaigns_root_url_verified + '/c/' + campaignx.seo_friendly_path
            we_vote_hosted_campaign_photo_large_url = campaignx.we_vote_hosted_campaign_photo_large_url

        speaker_voter_name = ''
        if positive_value_exists(activity_notice_seed.speaker_voter_we_vote_id):
            speaker_voter_results = \
                voter_manager.retrieve_voter_by_we_vote_id(activity_notice_seed.speaker_voter_we_vote_id)
            if speaker_voter_results['voter_found']:
                speaker_voter = speaker_voter_results['voter']
                speaker_voter_name = speaker_voter.get_full_name(real_name_only=True)

        politician_list = campaignx_manager.retrieve_campaignx_politician_list(
            campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id)
        politician_count = len(politician_list)
        if politician_count > 0:
            politician_full_sentence_string = fetch_sentence_string_from_politician_list(
                politician_list=politician_list,
            )
        else:
            politician_full_sentence_string = ''

        # Send to the campaignX supporters (which includes the campaign owner)
        continue_retrieving = True
        activity_notice_id_already_reviewed_list = []
        safety_valve_count = 0
        while continue_retrieving and success \
                and safety_valve_count < 5000:  # Current limit: 500,000 supporters (5000 loops)
            safety_valve_count += 1
            results = activity_manager.retrieve_activity_notice_list(
                activity_notice_seed_id=activity_notice_seed.id,
                to_be_sent_to_email=True,
                retrieve_count_limit=100,
                activity_notice_id_already_reviewed_list=activity_notice_id_already_reviewed_list,
            )
            if not results['success']:
                status += results['status']
                success = False
            elif results['activity_notice_list_found']:
                activity_notice_list = results['activity_notice_list']
                for activity_notice in activity_notice_list:
                    send_results = campaignx_news_item_send(
                        campaignx_news_item_we_vote_id=activity_notice_seed.campaignx_news_item_we_vote_id,
                        campaigns_root_url_verified=campaigns_root_url_verified,
                        campaignx_title=campaignx_title,
                        campaignx_url=campaignx_url,
                        campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                        politician_count=politician_count,
                        politician_full_sentence_string=politician_full_sentence_string,
                        recipient_voter_we_vote_id=activity_notice.recipient_voter_we_vote_id,
                        speaker_voter_name=speaker_voter_name,
                        speaker_voter_we_vote_id=activity_notice.speaker_voter_we_vote_id,
                        statement_subject=activity_notice_seed.statement_subject,
                        statement_text_preview=activity_notice_seed.statement_text_preview,
                        we_vote_hosted_campaign_photo_large_url=we_vote_hosted_campaign_photo_large_url,
                    )
                    activity_notice_id_already_reviewed_list.append(activity_notice.id)
                    try:
                        activity_notice.scheduled_to_email = True
                        activity_notice.save()
                    except Exception as e:
                        status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_NEWS_ITEM_SCHEDULED: " + str(e) + " "
                        success = False
                    if send_results['success']:
                        try:
                            activity_notice.sent_to_email = True
                            activity_notice.scheduled_to_sms = True
                            activity_notice.sent_to_sms = True
                            activity_notice.save()
                            activity_notice_count += 1
                            # We'll want to create a routine that connects up to the SendGrid API to tell us
                            #  when the message was received or bounced
                        except Exception as e:
                            status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_NEWS_ITEM: " + str(e) + " "
                            success = False
                    else:
                        status += send_results['status']
                        success = False
            else:
                continue_retrieving = False

        try:
            activity_notice_seed.activity_notices_scheduled = True
            activity_notice_seed.save()
        except Exception as e:
            status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_NEWS_ITEM_SEED_SCHEDULED: " + str(e) + " "
            success = False
        if success:
            try:
                activity_notice_seed.scheduled_to_email = True
                activity_notice_seed.sent_to_email = True
                # activity_notice_seed.scheduled_to_sms = True
                # activity_notice_seed.sent_to_sms = True
                activity_notice_seed.save()
                activity_notice_count += 1
                # We'll want to create a routine that connects up to the SendGrid API to tell us
                #  when the message was received or bounced
            except Exception as e:
                status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_NEWS_ITEM_SEED: " + str(e) + " "
                success = False
    elif activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED:
        from campaign.controllers_email_outbound import campaignx_friend_has_supported_send, \
            campaignx_supporter_initial_response_send
        # Send to the person who just signed
        send_results = campaignx_supporter_initial_response_send(
            campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
            recipient_voter_we_vote_id=activity_notice_seed.recipient_voter_we_vote_id,
        )
        status += send_results['status']
        if not send_results['success']:
            success = False
        # Successful or not, we need to mark this activity_notice_seed.activity_notices_scheduled as True to prevent
        #  infinite loop
        try:
            activity_notice_seed.activity_notices_scheduled = True
            activity_notice_seed.save()
        except Exception as e:
            status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED_AS_SCHEDULED: " \
                      "" + str(e) + " "
            success = False

        # Send to the person who signed the campaign's friends
        continue_retrieving = True
        activity_notice_id_already_reviewed_list = []
        safety_valve_count = 0
        while continue_retrieving and success \
                and safety_valve_count < 500:  # Current limit: 5,000 friends (500 loops with 100 per)
            safety_valve_count += 1
            results = activity_manager.retrieve_activity_notice_list(
                activity_notice_seed_id=activity_notice_seed.id,
                to_be_sent_to_email=True,
                retrieve_count_limit=100,
                activity_notice_id_already_reviewed_list=activity_notice_id_already_reviewed_list,
            )
            if not results['success']:
                status += results['status']
                success = False
            elif results['activity_notice_list_found']:
                activity_notice_list = results['activity_notice_list']
                for activity_notice in activity_notice_list:
                    send_results = campaignx_friend_has_supported_send(
                        campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id,
                        recipient_voter_we_vote_id=activity_notice.recipient_voter_we_vote_id,
                        speaker_voter_we_vote_id=activity_notice.speaker_voter_we_vote_id)
                    activity_notice_id_already_reviewed_list.append(activity_notice.id)
                    if send_results['success']:
                        try:
                            activity_notice.scheduled_to_email = True
                            activity_notice.sent_to_email = True
                            activity_notice.scheduled_to_sms = True
                            activity_notice.sent_to_sms = True
                            activity_notice.save()
                            activity_notice_count += 1
                            # We'll want to create a routine that connects up to the SendGrid API to tell us
                            #  when the message was received or bounced
                        except Exception as e:
                            status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_FRIEND_HAS_SUPPORTED: " + str(e) + " "
                            success = False
                    else:
                        status += send_results['status']
                        success = False
            else:
                continue_retrieving = False
        if success:
            try:
                # activity_notice_seed.activity_notices_scheduled = True  # Saved above
                activity_notice_seed.scheduled_to_email = True
                activity_notice_seed.sent_to_email = True
                # activity_notice_seed.scheduled_to_sms = True
                # activity_notice_seed.sent_to_sms = True
                activity_notice_seed.save()
                activity_notice_count += 1
                # We'll want to create a routine that connects up to the SendGrid API to tell us
                #  when the message was received or bounced
            except Exception as e:
                status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED: " + str(e) + " "
                success = False
    elif activity_notice_seed.kind_of_seed == NOTICE_FRIEND_ENDORSEMENTS_SEED:
        # Schedule/send emails
        # For these kind of seeds, we just send an email notification for the activity_notice (that is displayed
        #  to each voter in the header bar
        continue_retrieving = True
        activity_notice_id_already_reviewed_list = []
        safety_valve_count = 0
        while continue_retrieving and success \
                and safety_valve_count < 500:  # Current limit: 5,000 friends (500 loops with 100 per)
            safety_valve_count += 1
            results = activity_manager.retrieve_activity_notice_list(
                activity_notice_seed_id=activity_notice_seed.id,
                to_be_sent_to_email=True,
                retrieve_count_limit=100,
                activity_notice_id_already_reviewed_list=activity_notice_id_already_reviewed_list,
            )
            if not results['success']:
                status += results['status']
                success = False
            elif results['activity_notice_list_found']:
                position_name_list = []
                if positive_value_exists(activity_notice_seed.position_names_for_friends_serialized):
                    position_name_list_for_friends = \
                        json.loads(activity_notice_seed.position_names_for_friends_serialized)
                    position_name_list += position_name_list_for_friends
                if positive_value_exists(activity_notice_seed.position_names_for_public_serialized):
                    position_name_list_for_public = \
                        json.loads(activity_notice_seed.position_names_for_public_serialized)
                    position_name_list += position_name_list_for_public

                activity_notice_list = results['activity_notice_list']
                for activity_notice in activity_notice_list:
                    send_results = notice_friend_endorsements_send(
                        speaker_voter_we_vote_id=activity_notice.speaker_voter_we_vote_id,
                        recipient_voter_we_vote_id=activity_notice.recipient_voter_we_vote_id,
                        activity_tidbit_we_vote_id=activity_notice_seed.we_vote_id,
                        position_name_list=position_name_list)
                    activity_notice_id_already_reviewed_list.append(activity_notice.id)
                    if send_results['success']:
                        try:
                            activity_notice.scheduled_to_email = True
                            activity_notice.sent_to_email = True
                            activity_notice.scheduled_to_sms = True
                            activity_notice.sent_to_sms = True
                            activity_notice.save()
                            activity_notice_count += 1
                            # We'll want to create a routine that connects up to the SendGrid API to tell us
                            #  when the message was received or bounced
                        except Exception as e:
                            status += "FAILED_SAVING_ACTIVITY_NOTICE: " + str(e) + " "
                    else:
                        status += send_results['status']
                        success = False
            else:
                continue_retrieving = False
        try:
            activity_notice_seed.activity_notices_scheduled = True
            activity_notice_seed.save()
            status += "SCHEDULE_ACTIVITY_NOTICE_FRIEND_ENDORSEMENTS_SEED_AS_SCHEDULED "
        except Exception as e:
            status += "SCHEDULE_ACTIVITY_NOTICES_FRIEND_ENDORSEMENTS_SEED-CANNOT_MARK_NOTICES_CREATED: " + str(e) + " "
            success = False
    elif activity_notice_seed.kind_of_seed == NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED:
        from campaign.controllers_email_outbound import campaignx_super_share_item_send
        from campaign.controllers import fetch_sentence_string_from_politician_list
        from campaign.models import CampaignXManager
        from organization.controllers import transform_campaigns_url
        from share.models import ShareManager
        campaignx_manager = CampaignXManager()
        voter_manager = VoterManager()
        share_manager = ShareManager()

        campaigns_root_url_verified = transform_campaigns_url('')  # Change to client URL if needed
        results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=activity_notice_seed.campaignx_we_vote_id)
        campaignx_title = ''
        campaignx_url = campaigns_root_url_verified + '/id/' + activity_notice_seed.campaignx_we_vote_id  # Default link
        we_vote_hosted_campaign_photo_large_url = ''
        if results['campaignx_found']:
            campaignx = results['campaignx']
            campaignx_title = campaignx.campaign_title
            if positive_value_exists(campaignx.seo_friendly_path):
                campaignx_url = campaigns_root_url_verified + '/c/' + campaignx.seo_friendly_path
            we_vote_hosted_campaign_photo_large_url = campaignx.we_vote_hosted_campaign_photo_large_url

        speaker_email_address = ''
        speaker_photo = ''
        speaker_voter_name = ''
        if positive_value_exists(activity_notice_seed.speaker_voter_we_vote_id):
            speaker_voter_results = \
                voter_manager.retrieve_voter_by_we_vote_id(activity_notice_seed.speaker_voter_we_vote_id)
            if speaker_voter_results['voter_found']:
                speaker_voter = speaker_voter_results['voter']
                if positive_value_exists(speaker_voter.email_ownership_is_verified):
                    speaker_email_address = speaker_voter.email
                speaker_photo = speaker_voter.we_vote_hosted_profile_image_url_large
                speaker_voter_name = speaker_voter.get_full_name(real_name_only=True)

        if not positive_value_exists(activity_notice_seed.super_share_item_id):
            status += "MISSING_SUPER_SHARE_ITEM_ID_FROM_ACTIVITY_NOTICE_SEED "
            success = False

        # Send to the SuperShareEmailRecipients
        continue_retrieving = True
        super_share_email_recipient_already_reviewed_list = []
        safety_valve_count = 0
        while continue_retrieving and success \
                and safety_valve_count < 5000:  # Current limit: 500,000 supporters (5000 loops)
            safety_valve_count += 1
            results = share_manager.retrieve_super_share_email_recipient_list(
                read_only=False,
                retrieve_count_limit=100,
                retrieve_only_if_not_sent=True,
                super_share_email_recipient_already_reviewed_list=super_share_email_recipient_already_reviewed_list,
                super_share_item_id=activity_notice_seed.super_share_item_id,
            )
            if not results['success']:
                status += results['status']
                success = False
            elif results['email_recipient_list_found']:
                email_recipient_list = results['email_recipient_list']
                for super_share_email_recipient in email_recipient_list:
                    send_results = campaignx_super_share_item_send(
                        campaignx_news_item_we_vote_id=activity_notice_seed.campaignx_news_item_we_vote_id,
                        campaigns_root_url_verified=campaigns_root_url_verified,
                        campaignx_title=campaignx_title,
                        recipient_email_address=super_share_email_recipient.email_address_text,
                        recipient_first_name=super_share_email_recipient.recipient_first_name,
                        recipient_voter_we_vote_id=super_share_email_recipient.recipient_voter_we_vote_id,
                        speaker_email_address=speaker_email_address,
                        speaker_photo=speaker_photo,
                        speaker_voter_name=speaker_voter_name,
                        speaker_voter_we_vote_id=super_share_email_recipient.shared_by_voter_we_vote_id,
                        statement_subject=activity_notice_seed.statement_subject,
                        statement_text_preview=activity_notice_seed.statement_text_preview,
                        view_shared_campaignx_url=campaignx_url,
                        we_vote_hosted_campaign_photo_large_url=we_vote_hosted_campaign_photo_large_url,
                    )
                    super_share_email_recipient_already_reviewed_list.append(super_share_email_recipient.id)
                    if send_results['success']:
                        try:
                            super_share_email_recipient.date_sent_to_email = now()
                            super_share_email_recipient.save()
                            activity_notice_count += 1
                            # We'll want to create a routine that connects up to the SendGrid API to tell us
                            #  when the message was received or bounced
                        except Exception as e:
                            status += "FAILED_SAVING_ACTIVITY_NOTICE_CAMPAIGNX_NEWS_ITEM: " + str(e) + " "
                            success = False
                    else:
                        status += send_results['status']
                        success = False
            else:
                continue_retrieving = False

        # Mark activity_notices_scheduled as True whether success or not
        try:
            activity_notice_seed.activity_notices_scheduled = True
            activity_notice_seed.scheduled_to_email = True
            activity_notice_seed.save()
            activity_notice_count += 1
        except Exception as e:
            status += "FAILED_SAVING_NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED_AS_SCHEDULED: " + str(e) + " "
            success = False
        if success:
            try:
                activity_notice_seed.sent_to_email = True
                activity_notice_seed.save()
                activity_notice_count += 1
                # We'll want to create a routine that connects up to the SendGrid API to tell us
                #  when the message was received or bounced
            except Exception as e:
                status += "FAILED_SAVING_NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED_AS_SENT: " + str(e) + " "
                success = False
    elif activity_notice_seed.kind_of_seed == NOTICE_VOTER_DAILY_SUMMARY_SEED:
        # Make this either when the last SEED was created OR 24 hours ago
        assemble_activity_start_date = now() - timedelta(hours=24)

        assemble_results = assemble_voter_daily_summary(
            assemble_activity_start_date=assemble_activity_start_date,
            recipient_voter_we_vote_id=activity_notice_seed.recipient_voter_we_vote_id,
        )

        send_results = notice_voter_daily_summary_send(
            recipient_voter_we_vote_id=activity_notice_seed.recipient_voter_we_vote_id,
            friend_activity_dict_list=assemble_results['friend_activity_dict_list'],
            introduction_line=assemble_results['introduction_line'],
            subject=assemble_results['subject'])
        try:
            activity_notice_seed.activity_notices_scheduled = True
            activity_notice_seed.save()
            activity_notice_count += 1
        except Exception as e:
            status += "FAILED_SAVING_NOTICE_VOTER_DAILY_SUMMARY_SEED_AS_SCHEDULED: " + str(e) + " "
            success = False
        if send_results['success']:
            try:
                activity_notice_seed.scheduled_to_email = True
                activity_notice_seed.sent_to_email = True
                activity_notice_seed.save()
                activity_notice_count += 1
                # We'll want to create a routine that connects up to the SendGrid API to tell us
                #  when the message was received or bounced
            except Exception as e:
                status += "FAILED_SAVING_NOTICE_VOTER_DAILY_SUMMARY_SEED_AS_SENT: " + str(e) + " "
                success = False
        else:
            status += send_results['status']
            success = False

    results = {
        'success':                  success,
        'status':                   status,
        'activity_notice_count':    activity_notice_count,
    }
    return results


def update_or_create_activity_notice_for_campaignx_news_item(
        activity_notice_seed_id=0,
        campaignx_news_item_we_vote_id='',
        campaignx_we_vote_id='',
        kind_of_seed='',
        kind_of_notice='',
        number_of_comments=0,
        number_of_likes=0,
        recipient_voter_we_vote_id='',
        send_to_email=True,
        send_to_sms=True,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_subject='',
        statement_text_preview=''):
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_activity_notice_for_campaignx(
        campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        kind_of_notice=kind_of_notice,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_found']:
        try:
            activity_notice = results['activity_notice']
            change_found = False
            if positive_value_exists(campaignx_we_vote_id) and \
                    campaignx_we_vote_id != activity_notice.campaignx_we_vote_id:
                activity_notice.campaignx_we_vote_id = campaignx_we_vote_id
                change_found = True
            if positive_value_exists(number_of_comments) and number_of_comments != activity_notice.number_of_comments:
                activity_notice.number_of_comments = number_of_comments
                change_found = True
            if positive_value_exists(number_of_likes) and number_of_likes != activity_notice.number_of_likes:
                activity_notice.number_of_likes = number_of_likes
                change_found = True
            if positive_value_exists(speaker_name) and speaker_name != activity_notice.speaker_name:
                activity_notice.speaker_name = speaker_name
                change_found = True
            if positive_value_exists(speaker_profile_image_url_medium) and \
                    speaker_profile_image_url_medium != activity_notice.speaker_profile_image_url_medium:
                activity_notice.speaker_profile_image_url_medium = speaker_profile_image_url_medium
                change_found = True
            if positive_value_exists(speaker_profile_image_url_tiny) and \
                    speaker_profile_image_url_tiny != activity_notice.speaker_profile_image_url_tiny:
                activity_notice.speaker_profile_image_url_tiny = speaker_profile_image_url_tiny
                change_found = True
            if positive_value_exists(statement_subject) and \
                    statement_subject != activity_notice.statement_subject:
                activity_notice.statement_subject = statement_subject
                change_found = True
            if positive_value_exists(statement_text_preview) and \
                    statement_text_preview != activity_notice.statement_text_preview:
                activity_notice.statement_text_preview = statement_text_preview
                change_found = True
            if change_found:
                activity_notice.save()
        except Exception as e:
            status += "FAILED_ACTIVITY_NOTICE_SAVE_CAMPAIGNX_NEWS_ITEM: " + str(e) + ' '
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice(
            activity_notice_seed_id=activity_notice_seed_id,
            campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_notice=kind_of_notice,
            kind_of_seed=kind_of_seed,
            number_of_comments=number_of_comments,
            number_of_likes=number_of_likes,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            send_to_email=send_to_email,
            send_to_sms=send_to_sms,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_subject=statement_subject,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_for_campaignx_supporter_initial_response(
        activity_notice_seed_id=0,
        campaignx_we_vote_id='',
        kind_of_seed='',
        kind_of_notice='',
        number_of_comments=0,
        number_of_likes=0,
        recipient_voter_we_vote_id='',
        send_to_email=True,
        send_to_sms=True,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_text_preview=''):
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_from_speaker_and_recipient(
        activity_notice_seed_id=activity_notice_seed_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        kind_of_notice=kind_of_notice,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_found']:
        try:
            activity_notice = results['activity_notice']
            change_found = False
            if positive_value_exists(campaignx_we_vote_id) and \
                    campaignx_we_vote_id != activity_notice.campaignx_we_vote_id:
                activity_notice.campaignx_we_vote_id = campaignx_we_vote_id
                change_found = True
            if positive_value_exists(number_of_comments) and number_of_comments != activity_notice.number_of_comments:
                activity_notice.number_of_comments = number_of_comments
                change_found = True
            if positive_value_exists(number_of_likes) and number_of_likes != activity_notice.number_of_likes:
                activity_notice.number_of_likes = number_of_likes
                change_found = True
            if positive_value_exists(speaker_name) and speaker_name != activity_notice.speaker_name:
                activity_notice.speaker_name = speaker_name
                change_found = True
            if positive_value_exists(statement_text_preview) and \
                    statement_text_preview != activity_notice.statement_text_preview:
                activity_notice.statement_text_preview = statement_text_preview
                change_found = True
            if change_found:
                activity_notice.save()
        except Exception as e:
            status += "FAILED_ACTIVITY_NOTICE_SAVE_CAMPAIGNX_INITIAL_RESPONSE: " + str(e) + ' '
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice(
            activity_notice_seed_id=activity_notice_seed_id,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_notice=kind_of_notice,
            kind_of_seed=kind_of_seed,
            number_of_comments=number_of_comments,
            number_of_likes=number_of_likes,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            send_to_email=send_to_email,
            send_to_sms=send_to_sms,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_for_friend_campaignx_support(
        activity_notice_seed_id=0,
        campaignx_we_vote_id='',
        kind_of_seed='',
        kind_of_notice='',
        number_of_comments=0,
        number_of_likes=0,
        recipient_voter_we_vote_id='',
        send_to_email=False,
        send_to_sms=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_text_preview=''):
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_from_speaker_and_recipient(
        activity_notice_seed_id=activity_notice_seed_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        kind_of_notice=kind_of_notice,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_found']:
        try:
            activity_notice = results['activity_notice']
            change_found = False
            if positive_value_exists(campaignx_we_vote_id) and \
                    campaignx_we_vote_id != activity_notice.campaignx_we_vote_id:
                activity_notice.campaignx_we_vote_id = campaignx_we_vote_id
                change_found = True
            if positive_value_exists(number_of_comments) and number_of_comments != activity_notice.number_of_comments:
                activity_notice.number_of_comments = number_of_comments
                change_found = True
            if positive_value_exists(number_of_likes) and number_of_likes != activity_notice.number_of_likes:
                activity_notice.number_of_likes = number_of_likes
                change_found = True
            if positive_value_exists(speaker_name) and speaker_name != activity_notice.speaker_name:
                activity_notice.speaker_name = speaker_name
                change_found = True
            if positive_value_exists(statement_text_preview) and \
                    statement_text_preview != activity_notice.statement_text_preview:
                activity_notice.statement_text_preview = statement_text_preview
                change_found = True
            if change_found:
                activity_notice.save()
        except Exception as e:
            status += "FAILED_ACTIVITY_NOTICE_SAVE: " + str(e) + ' '
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice(
            activity_notice_seed_id=activity_notice_seed_id,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_notice=kind_of_notice,
            kind_of_seed=kind_of_seed,
            number_of_comments=number_of_comments,
            number_of_likes=number_of_likes,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            send_to_email=send_to_email,
            send_to_sms=send_to_sms,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_for_friend_endorsements(
        activity_notice_seed_id=0,
        activity_tidbit_we_vote_id='',
        kind_of_seed='',
        kind_of_notice='',
        position_name_list_serialized='',
        position_we_vote_id_list_serialized='',
        recipient_voter_we_vote_id='',
        send_to_email=False,
        send_to_sms=False,
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
        kind_of_notice=kind_of_notice,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    # Combine friends and public into single position_we_vote_id_list_serialized
    if results['activity_notice_found']:
        try:
            activity_notice = results['activity_notice']
            activity_notice.position_name_list_serialized = position_name_list_serialized
            activity_notice.position_we_vote_id_list_serialized = position_we_vote_id_list_serialized
            if positive_value_exists(activity_tidbit_we_vote_id):
                activity_notice.activity_tidbit_we_vote_id = activity_tidbit_we_vote_id
            activity_notice.save()
        except Exception as e:
            status += "FAILED_ACTIVITY_NOTICE_SAVE: " + str(e) + ' '
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice(
            activity_notice_seed_id=activity_notice_seed_id,
            activity_tidbit_we_vote_id=activity_tidbit_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_notice=kind_of_notice,
            kind_of_seed=kind_of_seed,
            position_name_list_serialized=position_name_list_serialized,
            position_we_vote_id_list_serialized=position_we_vote_id_list_serialized,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            send_to_email=send_to_email,
            send_to_sms=send_to_sms,
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


def update_or_create_activity_notice_for_friend_posts(
        activity_notice_seed_id=0,
        activity_tidbit_we_vote_id='',
        kind_of_seed='',
        kind_of_notice='',
        number_of_comments=0,
        number_of_likes=0,
        recipient_voter_we_vote_id='',
        send_to_email=False,
        send_to_sms=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_text_preview=''):
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_from_speaker_and_recipient(
        activity_notice_seed_id=activity_notice_seed_id,
        kind_of_notice=kind_of_notice,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_found']:
        try:
            activity_notice = results['activity_notice']
            change_found = False
            if positive_value_exists(activity_tidbit_we_vote_id) and \
                    activity_tidbit_we_vote_id != activity_notice.activity_tidbit_we_vote_id:
                activity_notice.activity_tidbit_we_vote_id = activity_tidbit_we_vote_id
                change_found = True
            if positive_value_exists(number_of_comments) and number_of_comments != activity_notice.number_of_comments:
                activity_notice.number_of_comments = number_of_comments
                change_found = True
            if positive_value_exists(number_of_likes) and number_of_likes != activity_notice.number_of_likes:
                activity_notice.number_of_likes = number_of_likes
                change_found = True
            if positive_value_exists(speaker_name) and speaker_name != activity_notice.speaker_name:
                activity_notice.speaker_name = speaker_name
                change_found = True
            if positive_value_exists(statement_text_preview) and \
                    statement_text_preview != activity_notice.statement_text_preview:
                activity_notice.statement_text_preview = statement_text_preview
                change_found = True
            if change_found:
                activity_notice.save()
        except Exception as e:
            status += "FAILED_ACTIVITY_NOTICE_SAVE: " + str(e) + ' '
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        create_results = activity_manager.create_activity_notice(
            activity_notice_seed_id=activity_notice_seed_id,
            activity_tidbit_we_vote_id=activity_tidbit_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_notice=kind_of_notice,
            kind_of_seed=kind_of_seed,
            number_of_comments=number_of_comments,
            number_of_likes=number_of_likes,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            send_to_email=send_to_email,
            send_to_sms=send_to_sms,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_seed_for_activity_posts(
        activity_post_we_vote_id='',
        visibility_is_public=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_text=''):
    """
    NOTE: This is tied to ANY activity_posts
    :param activity_post_we_vote_id: Not used for updates
    :param visibility_is_public: Not used for updates
    :param speaker_name:
    :param speaker_organization_we_vote_id:
    :param speaker_voter_we_vote_id:
    :param speaker_profile_image_url_medium:
    :param speaker_profile_image_url_tiny:
    :param statement_text:
    :return:
    """
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_seed_from_speaker(
        kind_of_seed=NOTICE_ACTIVITY_POST_SEED,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_seed_found']:
        activity_notice_seed = results['activity_notice_seed']
        try:
            # This SEED might have multiple ActivityPost entries associated with it
            most_recent_activity_post = None
            most_recent_activity_post_date = None
            # Since the activity is being saved microseconds before the activity_notice_seed is stored, we want to
            #  "rewind" the date_of_notice by 60 seconds
            since_date = activity_notice_seed.date_of_notice - timedelta(seconds=60)
            post_results = activity_manager.retrieve_activity_post_list(
                speaker_voter_we_vote_id_list=[speaker_voter_we_vote_id],
                since_date=since_date,
                limit_to_visibility_is_friends_only=True)
            activity_tidbit_we_vote_ids_for_friends = []
            activity_tidbit_we_vote_ids_for_friends_serialized = None
            if post_results['success']:
                friends_post_list = post_results['activity_post_list']
                for one_post in friends_post_list:
                    activity_tidbit_we_vote_ids_for_friends.append(one_post.we_vote_id)
                    if not one_post.date_created:
                        pass
                    elif most_recent_activity_post_date and one_post.date_created < most_recent_activity_post_date:
                        pass
                    else:
                        most_recent_activity_post_date = one_post.date_created
                        most_recent_activity_post = one_post
                activity_tidbit_we_vote_ids_for_friends_serialized = json.dumps(activity_tidbit_we_vote_ids_for_friends)

            post_results = activity_manager.retrieve_activity_post_list(
                speaker_voter_we_vote_id_list=[speaker_voter_we_vote_id],
                since_date=since_date,
                limit_to_visibility_is_public=True)
            activity_tidbit_we_vote_ids_for_public = []
            activity_tidbit_we_vote_ids_for_public_serialized = None
            if post_results['success']:
                public_post_list = post_results['activity_post_list']
                for one_post in public_post_list:
                    activity_tidbit_we_vote_ids_for_public.append(one_post.we_vote_id)
                    if not one_post.date_created:
                        pass
                    elif most_recent_activity_post_date and one_post.date_created < most_recent_activity_post_date:
                        pass
                    else:
                        most_recent_activity_post_date = one_post.date_created
                        most_recent_activity_post = one_post
                activity_tidbit_we_vote_ids_for_public_serialized = json.dumps(activity_tidbit_we_vote_ids_for_public)
            activity_notice_seed.activity_tidbit_we_vote_ids_for_friends_serialized = \
                activity_tidbit_we_vote_ids_for_friends_serialized
            activity_notice_seed.activity_tidbit_we_vote_ids_for_public_serialized = \
                activity_tidbit_we_vote_ids_for_public_serialized

            activity_notice_seed.speaker_name = speaker_name
            activity_notice_seed.speaker_profile_image_url_medium = speaker_profile_image_url_medium
            activity_notice_seed.speaker_profile_image_url_tiny = speaker_profile_image_url_tiny
            if most_recent_activity_post and most_recent_activity_post.statement_text:
                activity_notice_seed.statement_text_preview = return_first_x_words(
                    most_recent_activity_post.statement_text,
                    number_of_words_to_return=20,
                    include_ellipses=True)

            activity_notice_seed.save()
        except Exception as e:
            status += "COULD_NOT_UPDATE_ACTIVITY_NOTICE_SEED_FOR_POSTS: " + str(e) + " "
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        activity_tidbit_we_vote_ids_for_friends = []
        activity_tidbit_we_vote_ids_for_friends_serialized = None
        activity_tidbit_we_vote_ids_for_public = []
        activity_tidbit_we_vote_ids_for_public_serialized = None
        if positive_value_exists(visibility_is_public):
            activity_tidbit_we_vote_ids_for_public.append(activity_post_we_vote_id)
            activity_tidbit_we_vote_ids_for_public_serialized = json.dumps(activity_tidbit_we_vote_ids_for_public)
        else:
            activity_tidbit_we_vote_ids_for_friends.append(activity_post_we_vote_id)
            activity_tidbit_we_vote_ids_for_friends_serialized = json.dumps(activity_tidbit_we_vote_ids_for_friends)
        if positive_value_exists(statement_text):
            statement_text_preview = return_first_x_words(
                statement_text,
                number_of_words_to_return=30,
                include_ellipses=True)
        else:
            statement_text_preview = ''

        create_results = activity_manager.create_activity_notice_seed(
            activity_notices_scheduled=True,  # Set this to true so it gets ignored by the email-sending routine
            activity_tidbit_we_vote_ids_for_friends_serialized=activity_tidbit_we_vote_ids_for_friends_serialized,
            activity_tidbit_we_vote_ids_for_public_serialized=activity_tidbit_we_vote_ids_for_public_serialized,
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_ACTIVITY_POST_SEED,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_seed_for_campaignx_news_item(
        campaignx_news_item_we_vote_id='',
        campaignx_we_vote_id='',
        send_campaignx_news_item=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_subject='',
        statement_text=''):
    status = ''
    success = True
    activity_notice_seed = None
    activity_notice_seed_found = False
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_activity_notice_seed(
        campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        kind_of_seed=NOTICE_CAMPAIGNX_NEWS_ITEM_SEED,
    )
    if results['activity_notice_seed_found']:
        activity_notice_seed = results['activity_notice_seed']
        try:
            if positive_value_exists(send_campaignx_news_item):
                activity_notice_seed.send_to_email = True
                if not positive_value_exists(activity_notice_seed.date_sent_to_email):
                    activity_notice_seed.date_sent_to_email = now()
            activity_notice_seed.speaker_name = speaker_name
            activity_notice_seed.speaker_profile_image_url_medium = speaker_profile_image_url_medium
            activity_notice_seed.speaker_profile_image_url_tiny = speaker_profile_image_url_tiny
            activity_notice_seed.statement_subject = statement_subject
            if statement_text:
                activity_notice_seed.statement_text_preview = return_first_x_words(
                    statement_text,
                    number_of_words_to_return=40,
                    include_ellipses=True)
            else:
                activity_notice_seed.statement_text_preview = ''

            activity_notice_seed.save()
            activity_notice_seed_found = True
        except Exception as e:
            status += "COULD_NOT_UPDATE_NOTICE_CAMPAIGNX_NEWS_ITEM_SEED: " + str(e) + " "
            success = False
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        if positive_value_exists(statement_text):
            statement_text_preview = return_first_x_words(
                statement_text,
                number_of_words_to_return=40,
                include_ellipses=True)
        else:
            statement_text_preview = ''

        create_results = activity_manager.create_activity_notice_seed(
            activity_notices_scheduled=False,  # Set this to false so the email-sending routine picks it up
            campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_CAMPAIGNX_NEWS_ITEM_SEED,
            send_to_email=positive_value_exists(send_campaignx_news_item),
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_subject=statement_subject,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
        activity_notice_seed_found = create_results['activity_notice_seed_found']
        activity_notice_seed = create_results['activity_notice_seed']
    else:
        status += results['status']
        success = False

    results = {
        'activity_notice_seed_found':   activity_notice_seed_found,
        'activity_notice_seed':         activity_notice_seed,
        'success':                      success,
        'status':                       status,
    }
    return results


def update_or_create_activity_notice_seed_for_campaignx_supporter_initial_response(
        campaignx_we_vote_id='',
        visibility_is_public=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_text=''):
    """

    :param campaignx_we_vote_id:
    :param visibility_is_public: Not used for updates
    :param speaker_name:
    :param speaker_organization_we_vote_id:
    :param speaker_voter_we_vote_id:
    :param speaker_profile_image_url_medium:
    :param speaker_profile_image_url_tiny:
    :param statement_text:
    :return:
    """
    status = ''
    success = True
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_recent_activity_notice_seed_from_speaker(
        campaignx_we_vote_id=campaignx_we_vote_id,
        kind_of_seed=NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_seed_found']:
        activity_notice_seed = results['activity_notice_seed']
        try:
            activity_notice_seed.speaker_name = speaker_name
            activity_notice_seed.speaker_profile_image_url_medium = speaker_profile_image_url_medium
            activity_notice_seed.speaker_profile_image_url_tiny = speaker_profile_image_url_tiny
            if statement_text:
                activity_notice_seed.statement_text_preview = return_first_x_words(
                    statement_text,
                    number_of_words_to_return=20,
                    include_ellipses=True)

            activity_notice_seed.save()
        except Exception as e:
            status += "COULD_NOT_UPDATE_NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED: " + str(e) + " "
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        if positive_value_exists(statement_text):
            statement_text_preview = return_first_x_words(
                statement_text,
                number_of_words_to_return=20,
                include_ellipses=True)
        else:
            statement_text_preview = ''

        create_results = activity_manager.create_activity_notice_seed(
            activity_notices_scheduled=False,  # Set this to false so the email-sending routine picks it up
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_SEED,
            recipient_name=speaker_name,
            recipient_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_text_preview=statement_text_preview)
        status += create_results['status']
    else:
        status += results['status']

    results = {
        'success':              success,
        'status':               status,
    }
    return results


def update_or_create_activity_notice_seed_for_super_share_item(
        campaignx_news_item_we_vote_id='',
        campaignx_we_vote_id='',
        send_super_share_item=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny='',
        statement_subject='',
        statement_text='',
        super_share_item_id=0):
    status = ''
    success = True
    activity_notice_seed = None
    activity_notice_seed_found = False
    activity_manager = ActivityManager()

    results = activity_manager.retrieve_activity_notice_seed(
        kind_of_seed=NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED,
        super_share_item_id=super_share_item_id,
    )
    if results['activity_notice_seed_found']:
        activity_notice_seed = results['activity_notice_seed']
        try:
            if positive_value_exists(send_super_share_item):
                activity_notice_seed.send_to_email = True
                if not positive_value_exists(activity_notice_seed.date_sent_to_email):
                    activity_notice_seed.date_sent_to_email = now()
            activity_notice_seed.speaker_name = speaker_name
            activity_notice_seed.speaker_profile_image_url_medium = speaker_profile_image_url_medium
            activity_notice_seed.speaker_profile_image_url_tiny = speaker_profile_image_url_tiny
            activity_notice_seed.statement_subject = statement_subject
            if statement_text:
                activity_notice_seed.statement_text_preview = return_first_x_words(
                    statement_text,
                    number_of_words_to_return=40,
                    include_ellipses=True)
            else:
                activity_notice_seed.statement_text_preview = ''

            activity_notice_seed.save()
            activity_notice_seed_found = True
        except Exception as e:
            status += "COULD_NOT_UPDATE_NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED: " + str(e) + " "
            success = False
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        if positive_value_exists(statement_text):
            statement_text_preview = statement_text
        else:
            statement_text_preview = ''

        create_results = activity_manager.create_activity_notice_seed(
            activity_notices_scheduled=False,  # Set this to false so the email-sending routine picks it up
            campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_CAMPAIGNX_SUPER_SHARE_ITEM_SEED,
            send_to_email=positive_value_exists(send_super_share_item),
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=speaker_organization_we_vote_id,
            speaker_voter_we_vote_id=speaker_voter_we_vote_id,
            speaker_profile_image_url_medium=speaker_profile_image_url_medium,
            speaker_profile_image_url_tiny=speaker_profile_image_url_tiny,
            statement_subject=statement_subject,
            statement_text_preview=statement_text_preview,
            super_share_item_id=super_share_item_id)
        status += create_results['status']
        activity_notice_seed_found = create_results['activity_notice_seed_found']
        activity_notice_seed = create_results['activity_notice_seed']
    else:
        status += results['status']
        success = False

    results = {
        'activity_notice_seed_found':   activity_notice_seed_found,
        'activity_notice_seed':         activity_notice_seed,
        'success':                      success,
        'status':                       status,
    }
    return results


def update_or_create_activity_notice_seed_for_voter_position(
        position_ballot_item_display_name='',
        position_we_vote_id='',
        is_public_position=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny=''):
    """

    :param position_ballot_item_display_name: Not used for updates
    :param position_we_vote_id: Not used for updates
    :param is_public_position: Not used for updates
    :param speaker_name:
    :param speaker_organization_we_vote_id:
    :param speaker_voter_we_vote_id:
    :param speaker_profile_image_url_medium:
    :param speaker_profile_image_url_tiny:
    :return:
    """
    status = ''
    success = True
    activity_manager = ActivityManager()
    from position.models import PositionListManager
    position_list_manager = PositionListManager()

    results = activity_manager.retrieve_recent_activity_notice_seed_from_speaker(
        kind_of_seed=NOTICE_FRIEND_ENDORSEMENTS_SEED,
        speaker_organization_we_vote_id=speaker_organization_we_vote_id,
        speaker_voter_we_vote_id=speaker_voter_we_vote_id,
    )
    if results['activity_notice_seed_found']:
        activity_notice_seed = results['activity_notice_seed']
        try:
            # Since the position is being saved microseconds before the activity_notice_seed is stored, we want to
            #  "rewind" the date_of_notice by 60 seconds
            since_date = activity_notice_seed.date_of_notice - timedelta(seconds=60)
            position_results = position_list_manager.retrieve_all_positions_for_voter(
                voter_we_vote_id=speaker_voter_we_vote_id,
                since_date=since_date)
            if position_results['success']:
                friends_positions_list = position_results['friends_positions_list']
                position_name_list_for_friends = []
                position_we_vote_id_list_for_friends = []
                for one_position in friends_positions_list:
                    position_name_list_for_friends.append(one_position.ballot_item_display_name)
                    position_we_vote_id_list_for_friends.append(one_position.we_vote_id)
                position_names_for_friends_serialized = json.dumps(position_name_list_for_friends)
                position_we_vote_ids_for_friends_serialized = json.dumps(position_we_vote_id_list_for_friends)

                public_positions_list = position_results['public_positions_list']
                position_name_list_for_public = []
                position_we_vote_id_list_for_public = []
                for one_position in public_positions_list:
                    position_name_list_for_public.append(one_position.ballot_item_display_name)
                    position_we_vote_id_list_for_public.append(one_position.we_vote_id)
                position_names_for_public_serialized = json.dumps(position_name_list_for_public)
                position_we_vote_ids_for_public_serialized = json.dumps(position_we_vote_id_list_for_public)
            else:
                # If here, there was a problem retrieving positions since the activity_notice_seed was saved,
                #  so we just work with the one position_we_vote_id
                if is_public_position:
                    position_names_for_friends_serialized = None
                    position_name_list_for_public = [position_ballot_item_display_name]
                    position_names_for_public_serialized = json.dumps(position_name_list_for_public)
                    position_we_vote_ids_for_friends_serialized = None
                    position_we_vote_id_list_for_public = [position_we_vote_id]
                    position_we_vote_ids_for_public_serialized = json.dumps(position_we_vote_id_list_for_public)
                else:
                    position_name_list_for_friends = [position_ballot_item_display_name]
                    position_names_for_friends_serialized = json.dumps(position_name_list_for_friends)
                    position_names_for_public_serialized = None
                    position_we_vote_id_list_for_friends = [position_we_vote_id]
                    position_we_vote_ids_for_friends_serialized = json.dumps(position_we_vote_id_list_for_friends)
                    position_we_vote_ids_for_public_serialized = None

            activity_notice_seed.position_names_for_friends_serialized = position_names_for_friends_serialized
            activity_notice_seed.position_names_for_public_serialized = position_names_for_public_serialized
            activity_notice_seed.position_we_vote_ids_for_friends_serialized = \
                position_we_vote_ids_for_friends_serialized
            activity_notice_seed.position_we_vote_ids_for_public_serialized = \
                position_we_vote_ids_for_public_serialized
            activity_notice_seed.speaker_name = speaker_name
            activity_notice_seed.speaker_profile_image_url_medium = speaker_profile_image_url_medium
            activity_notice_seed.speaker_profile_image_url_tiny = speaker_profile_image_url_tiny

            activity_notice_seed.save()
        except Exception as e:
            status += "COULD_NOT_UPDATE_SPEAKER_IMAGES " + str(e) + " "
        status += results['status']
    elif results['success']:
        date_of_notice = now()
        if is_public_position:
            position_name_list_for_public = [position_ballot_item_display_name]
            position_names_for_public_serialized = json.dumps(position_name_list_for_public)
            position_names_for_friends_serialized = None
            position_we_vote_id_list_for_public = [position_we_vote_id]
            position_we_vote_ids_for_public_serialized = json.dumps(position_we_vote_id_list_for_public)
            position_we_vote_ids_for_friends_serialized = None
        else:
            position_name_list_for_friends = [position_ballot_item_display_name]
            position_names_for_friends_serialized = json.dumps(position_name_list_for_friends)
            position_names_for_public_serialized = None
            position_we_vote_id_list_for_friends = [position_we_vote_id]
            position_we_vote_ids_for_friends_serialized = json.dumps(position_we_vote_id_list_for_friends)
            position_we_vote_ids_for_public_serialized = None
        create_results = activity_manager.create_activity_notice_seed(
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_FRIEND_ENDORSEMENTS_SEED,
            position_names_for_friends_serialized=position_names_for_friends_serialized,
            position_names_for_public_serialized=position_names_for_public_serialized,
            position_we_vote_ids_for_friends_serialized=position_we_vote_ids_for_friends_serialized,
            position_we_vote_ids_for_public_serialized=position_we_vote_ids_for_public_serialized,
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


def update_activity_notice_seed_date_of_notice_earlier_than_update_window(activity_notice_seed):
    status = ''
    success = True
    activity_notice_seed_changed = False

    from activity.models import get_lifespan_of_seed
    lifespan_of_seed_in_seconds = get_lifespan_of_seed(activity_notice_seed.kind_of_seed)  # In seconds
    earliest_date_of_notice = now() - timedelta(seconds=lifespan_of_seed_in_seconds)
    # Is this activity_notice_seed.date_of_notice older than earliest_date_of_notice?
    if activity_notice_seed.date_of_notice < earliest_date_of_notice:
        try:
            activity_notice_seed.date_of_notice_earlier_than_update_window = True
            activity_notice_seed.save()
            activity_notice_seed_changed = True
            status += "DATE_OF_NOTICE_EARLIER_THAN_UPDATE_WINDOW_SET_TRUE "
        except Exception as e:
            status += "COULD_NOT_UPDATE-date_of_notice_earlier_than_update_window: " + str(e) + ' '
            success = False
    results = {
        'success':                                      success,
        'status':                                       status,
        'activity_notice_seed':                         activity_notice_seed,
        'activity_notice_seed_changed':                 activity_notice_seed_changed,
        'date_of_notice_earlier_than_update_window':    activity_notice_seed.date_of_notice_earlier_than_update_window,
    }
    return results


def update_activity_notice_seed_with_positions(activity_notice_seed):
    status = ''
    success = True
    activity_notice_seed_changed = False

    # What values currently exist? We deserialize so we can compare with latest positions
    # Position names
    position_name_list_for_friends = []
    if positive_value_exists(activity_notice_seed.position_names_for_friends_serialized):
        position_name_list_for_friends = json.loads(activity_notice_seed.position_names_for_friends_serialized)
    position_name_list_for_public = []
    if positive_value_exists(activity_notice_seed.position_names_for_public_serialized):
        position_name_list_for_public = json.loads(activity_notice_seed.position_names_for_public_serialized)
    # Position we_vote_ids
    position_we_vote_id_list_for_friends = []
    if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_friends_serialized):
        position_we_vote_id_list_for_friends = \
            json.loads(activity_notice_seed.position_we_vote_ids_for_friends_serialized)
    position_we_vote_id_list_for_public = []
    if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_public_serialized):
        position_we_vote_id_list_for_public = \
            json.loads(activity_notice_seed.position_we_vote_ids_for_public_serialized)

    from position.models import PositionListManager
    position_list_manager = PositionListManager()
    since_date = activity_notice_seed.date_of_notice - timedelta(seconds=60)
    position_results = position_list_manager.retrieve_all_positions_for_voter(
        voter_we_vote_id=activity_notice_seed.speaker_voter_we_vote_id,
        since_date=since_date)
    if position_results['success']:
        friends_positions_list = position_results['friends_positions_list']
        position_name_list_for_friends_latest = []
        position_we_vote_id_list_for_friends_latest = []
        for one_position in friends_positions_list:
            position_name_list_for_friends_latest.append(one_position.ballot_item_display_name)
            position_we_vote_id_list_for_friends_latest.append(one_position.we_vote_id)
        public_positions_list = position_results['public_positions_list']
        position_name_list_for_public_latest = []
        position_we_vote_id_list_for_public_latest = []
        for one_position in public_positions_list:
            position_name_list_for_public_latest.append(one_position.ballot_item_display_name)
            position_we_vote_id_list_for_public_latest.append(one_position.we_vote_id)

        friends_name_list_different = set(position_name_list_for_friends) != \
            set(position_name_list_for_friends_latest)
        public_name_list_different = set(position_name_list_for_public) != \
            set(position_name_list_for_public_latest)
        friends_we_vote_id_list_different = set(position_we_vote_id_list_for_friends) != \
            set(position_we_vote_id_list_for_friends_latest)
        public_we_vote_id_list_different = set(position_we_vote_id_list_for_public) != \
            set(position_we_vote_id_list_for_public_latest)
        if friends_name_list_different or public_name_list_different or \
                friends_we_vote_id_list_different or public_we_vote_id_list_different:
            try:
                activity_notice_seed.position_names_for_friends_serialized = \
                    json.dumps(position_name_list_for_friends_latest)
                activity_notice_seed.position_names_for_public_serialized = \
                    json.dumps(position_name_list_for_public_latest)
                activity_notice_seed.position_we_vote_ids_for_friends_serialized = \
                    json.dumps(position_we_vote_id_list_for_friends_latest)
                activity_notice_seed.position_we_vote_ids_for_public_serialized = \
                    json.dumps(position_we_vote_id_list_for_public_latest)
                activity_notice_seed.save()
                activity_notice_seed_changed = True
            except Exception as e:
                success = False
                status += "COULD_NOT_SAVE: " + str(e) + ' '
    results = {
        'success':                                      success,
        'status':                                       status,
        'activity_notice_seed':                         activity_notice_seed,
        'activity_notice_seed_changed':                 activity_notice_seed_changed,
    }
    return results
