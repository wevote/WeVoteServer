# activity/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ActivityNoticeSeed, ActivityManager, ActivityNotice, ActivityPost, \
    NOTICE_FRIEND_ENDORSEMENTS, NOTICE_FRIEND_ENDORSEMENTS_SEED
from config.base import get_environment_variable
from django.utils.timezone import now
from friend.models import FriendManager
import json
from datetime import timedelta
from voter.models import \
    NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL, NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL, \
    NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_SMS, NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS, \
    VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


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
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'activity_notice_seed_entries_moved': activity_notice_seed_entries_moved,
            'activity_notice_entries_moved': activity_notice_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_ACTIVITY_NOTICE_SEEDS-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'activity_notice_seed_entries_moved': activity_notice_seed_entries_moved,
            'activity_notice_entries_moved': activity_notice_entries_moved,
        }
        return results

    # ######################
    # Migrations
    speaker_profile_image_url_medium = None
    speaker_profile_image_url_tiny = None
    try:
        speaker_profile_image_url_medium = to_voter.we_vote_hosted_profile_image_url_medium
        speaker_profile_image_url_tiny = to_voter.we_vote_hosted_profile_image_url_tiny
    except Exception as e:
        status += "UNABLE_TO_GET_PHOTOS " + str(e) + " "

    if positive_value_exists(to_organization_we_vote_id):
        # Move based on speaker_voter_we_vote_id
        try:
            activity_notice_seed_entries_moved += ActivityNoticeSeed.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-INCLUDING_ORG_UPDATE " + str(e) + " "
        try:
            activity_notice_entries_moved += ActivityNotice.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
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
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-FROM_ORG_WE_VOTE_ID " + str(e) + " "
        try:
            activity_notice_entries_moved += ActivityNotice.objects \
                .filter(speaker_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_UPDATE-FROM_ORG_WE_VOTE_ID " + str(e) + " "
    else:
        try:
            activity_notice_seed_entries_moved += ActivityNoticeSeed.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_SEED_UPDATE-MISSING_ORG " + str(e) + " "
        try:
            activity_notice_entries_moved += ActivityNotice.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_NOTICE_UPDATE-MISSING_ORG " + str(e) + " "

    # Now move ActivityNotice recipient_voter_we_vote_id
    try:
        activity_notice_entries_moved += ActivityNotice.objects \
            .filter(recipient_voter_we_vote_id__iexact=from_voter_we_vote_id) \
            .update(recipient_voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-ACTIVITY_NOTICE_UPDATE-RECIPIENT " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'activity_notice_seed_entries_moved': activity_notice_seed_entries_moved,
        'activity_notice_entries_moved': activity_notice_entries_moved,
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
    speaker_profile_image_url_medium = None
    speaker_profile_image_url_tiny = None
    try:
        speaker_profile_image_url_medium = to_voter.we_vote_hosted_profile_image_url_medium
        speaker_profile_image_url_tiny = to_voter.we_vote_hosted_profile_image_url_tiny
    except Exception as e:
        status += "UNABLE_TO_GET_PHOTOS " + str(e) + " "

    if positive_value_exists(to_organization_we_vote_id):
        # Move based on speaker_voter_we_vote_id
        try:
            activity_post_entries_moved += ActivityPost.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
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
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_organization_we_vote_id=to_organization_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_POST_UPDATE-FROM_ORG_WE_VOTE_ID " + str(e) + " "
    else:
        try:
            activity_post_entries_moved += ActivityPost.objects\
                .filter(speaker_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(speaker_voter_we_vote_id=to_voter_we_vote_id,
                        speaker_profile_image_url_medium=speaker_profile_image_url_medium,
                        speaker_profile_image_url_tiny=speaker_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-ACTIVITY_POST_UPDATE-MISSING_ORG " + str(e) + " "

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
        activity_tidbit_we_vote_id=''):
    """
    We are sending an email to the speaker's friends who are subscribed to NOTICE_FRIEND_ENDORSEMENTS
    :param speaker_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param invitation_message:
    :param activity_tidbit_we_vote_id:
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

        # Variables used by templates/email_outbound/email_templates/friend_accepted_invitation.txt and .html
        if positive_value_exists(speaker_voter_name):
            subject = speaker_voter_name + " has added a new opinion"
        else:
            subject = "Your friend added new opinion"

        template_variables_for_json = {
            "subject":                      subject,
            "invitation_message":           invitation_message,
            "sender_name":                  speaker_voter_name,
            "sender_photo":                 speaker_voter_photo,
            "sender_email_address":         speaker_voter_email,  # Does not affect the "From" email header
            "sender_description":           speaker_voter_description,
            "sender_network_details":       speaker_voter_network_details,
            "recipient_name":               recipient_name,
            "recipient_voter_email":        recipient_email,
            "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
            recipient_email_subscription_secret_key,
            "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
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
            kind_of_email_template=kind_of_email_template)
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


def update_or_create_activity_notices_triggered_by_batch_process():
    """
    We assume only one of this function is running at any time.
    :return:
    """
    status = ''
    success = True
    activity_notice_seed_count = 0
    activity_notice_count = 0

    # Retrieve ActivityNoticeSeeds that need to have ActivityNotice entries created
    activity_manager = ActivityManager()
    # We want this process to stop before it has run for 5 minutes, so that we don't collide with another process
    #  starting. Please also see: activity_notice_processing_time_out_duration & checked_out_expiration_time
    # We adjust timeout for ACTIVITY_NOTICE_PROCESS in retrieve_batch_process_list
    longest_activity_notice_processing_run_time_allowed = 270  # 4.5 minutes * 60 seconds
    when_process_must_stop = now() + timedelta(seconds=longest_activity_notice_processing_run_time_allowed)

    # Update existing ActivityNoticeSeed entries
    # Only run this when the minutes are divisible by "5"
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
                activity_notice_seed = results['activity_notice_seed']
                activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
                activity_notice_seed_count += 1
                update_seed_results = update_activity_notice_seed_with_positions(activity_notice_seed)
                if update_seed_results['success'] and \
                        update_seed_results['activity_notice_seed_changed'] and not \
                        update_seed_results['date_of_notice_earlier_than_update_window']:
                    activity_notice_seed = update_seed_results['activity_notice_seed']
                    update_results = update_or_create_activity_notices_from_seed(activity_notice_seed)
                    if not update_results['success']:
                        status += update_results['status']
            else:
                continue_retrieving_notices_to_be_updated = False

    # Create new ActivityNoticeSeed entries
    continue_retrieving_notices_to_be_created = True
    activity_notice_seed_id_already_reviewed_list = []  # Reset
    safety_valve_count = 0
    while continue_retrieving_notices_to_be_created and safety_valve_count < 1000 and when_process_must_stop > now():
        safety_valve_count += 1
        results = activity_manager.retrieve_next_activity_notice_seed_to_process(
            notices_to_be_created=True,
            activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
        if results['activity_notice_seed_found']:
            activity_notice_seed = results['activity_notice_seed']
            activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
            activity_notice_seed_count += 1
            create_results = update_or_create_activity_notices_from_seed(activity_notice_seed)
            # activity_notice_seed.activity_notices_created = True  # Marked in function immediately above
            activity_notice_count += create_results['activity_notice_count']
        else:
            continue_retrieving_notices_to_be_created = False

    # Send email notifications
    continue_retrieving_notices_to_be_scheduled = True
    activity_notice_seed_id_already_reviewed_list = []  # Reset
    safety_valve_count = 0
    while continue_retrieving_notices_to_be_scheduled and safety_valve_count < 1000 and when_process_must_stop > now():
        safety_valve_count += 1
        results = activity_manager.retrieve_next_activity_notice_seed_to_process(
            notices_to_be_scheduled=True,
            activity_notice_seed_id_already_reviewed_list=activity_notice_seed_id_already_reviewed_list)
        if results['activity_notice_seed_found']:
            activity_notice_seed = results['activity_notice_seed']
            activity_notice_seed_id_already_reviewed_list.append(activity_notice_seed.id)
            # activity_notice_seed_count += 1
            schedule_results = schedule_activity_notices_from_seed(activity_notice_seed)
            # activity_notice_seed.activity_notices_scheduled = True  # Marked in function immediately above
            if not schedule_results['success']:
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

            position_we_vote_id_list = []
            if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_friends_serialized):
                position_we_vote_id_list_for_friends = \
                    json.loads(activity_notice_seed.position_we_vote_ids_for_friends_serialized)
                position_we_vote_id_list += position_we_vote_id_list_for_friends
            if positive_value_exists(activity_notice_seed.position_we_vote_ids_for_public_serialized):
                position_we_vote_id_list_for_public = \
                    json.loads(activity_notice_seed.position_we_vote_ids_for_public_serialized)
                position_we_vote_id_list += position_we_vote_id_list_for_public
            position_we_vote_id_list_serialized = json.dumps(position_we_vote_id_list)

            for friend_voter in current_friend_list:
                kind_of_notice = NOTICE_FRIEND_ENDORSEMENTS  # Figure this out from activity_notice_seed.kind_of_seed
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

                activity_results = update_or_create_activity_notice_for_friend(
                    activity_notice_seed_id=activity_notice_seed.id,
                    activity_tidbit_we_vote_id=activity_notice_seed.we_vote_id,
                    kind_of_seed=activity_notice_seed.kind_of_seed,
                    kind_of_notice=kind_of_notice,
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


def schedule_activity_notices_from_seed(activity_notice_seed):
    status = ''
    success = True
    activity_notice_count = 0
    activity_manager = ActivityManager()

    # Schedule/send emails
    # Retrieve activity notices for this activity_notice_seed in blocks of 100
    continue_retrieving = True
    activity_notice_id_already_reviewed_list = []
    safety_valve_count = 0
    while continue_retrieving and safety_valve_count < 1000:
        safety_valve_count += 1
        results = activity_manager.retrieve_activity_notice_list(
            activity_notice_seed_id=activity_notice_seed.id,
            to_be_sent_to_email=True,
            retrieve_count_limit=100,
            activity_notice_id_already_reviewed_list=activity_notice_id_already_reviewed_list,
        )
        if not results['success']:
            status += results['status']
        if results['activity_notice_list_found']:
            activity_notice_list = results['activity_notice_list']
            for activity_notice in activity_notice_list:
                send_results = notice_friend_endorsements_send(
                    speaker_voter_we_vote_id=activity_notice.speaker_voter_we_vote_id,
                    recipient_voter_we_vote_id=activity_notice.recipient_voter_we_vote_id,
                    activity_tidbit_we_vote_id=activity_notice_seed.we_vote_id)
                activity_notice_id_already_reviewed_list.append(activity_notice.id)
                if send_results['success']:
                    try:
                        activity_notice.scheduled_to_email = True
                        activity_notice.sent_to_email = True
                        activity_notice.scheduled_to_sms = True
                        activity_notice.sent_to_sms = True
                        activity_notice.save()
                        activity_notice_count += 1
                        # We will want to create another routine that connects up to the SendGrid API for more accuracy
                    except Exception as e:
                        status += "FAILED_SAVING_ACTIVITY_NOTICE: " + str(e) + " "
                        pass
                else:
                    status += send_results['status']
        else:
            continue_retrieving = False

    # # Schedule/send sms
    # results = activity_manager.retrieve_activity_notice_list(
    #     activity_notice_seed_id=activity_notice_seed.id,
    #     to_be_sent_to_sms=True,
    # )

    try:
        activity_notice_seed.activity_notices_scheduled = True
        activity_notice_seed.save()
        status += "SCHEDULE_ACTIVITY_NOTICES_FROM_SEED-MARKED_CREATED "
    except Exception as e:
        status += "SCHEDULE_ACTIVITY_NOTICES_FROM_SEED-CANNOT_MARK_NOTICES_CREATED: " + str(e) + " "
        success = False

    results = {
        'success':                  success,
        'status':                   status,
        'activity_notice_count':    activity_notice_count,
    }
    return results


def update_or_create_activity_notice_for_friend(
        activity_notice_seed_id=0,
        activity_tidbit_we_vote_id='',
        kind_of_seed='',
        kind_of_notice='',
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


def update_or_create_activity_notice_seed_for_voter_position(
        position_we_vote_id='',
        is_public_position=False,
        speaker_name='',
        speaker_organization_we_vote_id='',
        speaker_voter_we_vote_id='',
        speaker_profile_image_url_medium='',
        speaker_profile_image_url_tiny=''):
    """

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
                position_we_vote_id_list_for_friends = []
                for one_position in friends_positions_list:
                    position_we_vote_id_list_for_friends.append(one_position.we_vote_id)
                position_we_vote_ids_for_friends_serialized = json.dumps(position_we_vote_id_list_for_friends)

                public_positions_list = position_results['public_positions_list']
                position_we_vote_id_list_for_public = []
                for one_position in public_positions_list:
                    position_we_vote_id_list_for_public.append(one_position.we_vote_id)
                position_we_vote_ids_for_public_serialized = json.dumps(position_we_vote_id_list_for_public)
            else:
                # If here, there was a problem retrieving positions since the activity_notice_seed was saved,
                #  so we just work with the one position_we_vote_id
                if is_public_position:
                    position_we_vote_ids_for_friends_serialized = None
                    position_we_vote_id_list_for_public = [position_we_vote_id]
                    position_we_vote_ids_for_public_serialized = json.dumps(position_we_vote_id_list_for_public)
                else:
                    position_we_vote_id_list_for_friends = [position_we_vote_id]
                    position_we_vote_ids_for_friends_serialized = json.dumps(position_we_vote_id_list_for_friends)
                    position_we_vote_ids_for_public_serialized = None

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
            position_we_vote_ids_for_friends_serialized = None
            position_we_vote_id_list_for_public = [position_we_vote_id]
            position_we_vote_ids_for_public_serialized = json.dumps(position_we_vote_id_list_for_public)
        else:
            position_we_vote_id_list_for_friends = [position_we_vote_id]
            position_we_vote_ids_for_friends_serialized = json.dumps(position_we_vote_id_list_for_friends)
            position_we_vote_ids_for_public_serialized = None
        create_results = activity_manager.create_activity_notice_seed(
            date_of_notice=date_of_notice,
            kind_of_seed=NOTICE_FRIEND_ENDORSEMENTS_SEED,
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


def update_activity_notice_seed_with_positions(activity_notice_seed):
    status = ''
    success = True
    activity_notice_seed_changed = False

    from activity.models import get_lifespan_of_seed
    kind_of_seed = NOTICE_FRIEND_ENDORSEMENTS_SEED
    lifespan_of_seed_in_seconds = get_lifespan_of_seed(kind_of_seed)  # In seconds
    earliest_date_of_notice = now() - timedelta(seconds=lifespan_of_seed_in_seconds)
    # Is this activity_notice_seed.date_of_notice older than earliest_date_of_notice?
    if activity_notice_seed.date_of_notice < earliest_date_of_notice:
        try:
            activity_notice_seed.date_of_notice_earlier_than_update_window = True
            activity_notice_seed.save()
            activity_notice_seed_changed = True
        except Exception as e:
            status += "COULD_NOT_UPDATE-date_of_notice_earlier_than_update_window: " + str(e) + ' '
        results = {
            'success':                                      success,
            'status':                                       status,
            'activity_notice_seed':                         activity_notice_seed,
            'activity_notice_seed_changed':                 activity_notice_seed_changed,
            'date_of_notice_earlier_than_update_window':    True,
        }
        return results

    # What values currently exist?
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
        position_we_vote_id_list_for_friends_latest = []
        for one_position in friends_positions_list:
            position_we_vote_id_list_for_friends_latest.append(one_position.we_vote_id)
        public_positions_list = position_results['public_positions_list']
        position_we_vote_id_list_for_public_latest = []
        for one_position in public_positions_list:
            position_we_vote_id_list_for_public_latest.append(one_position.we_vote_id)

        friends_list_different = set(position_we_vote_id_list_for_friends) != \
            set(position_we_vote_id_list_for_friends_latest)
        public_list_different = set(position_we_vote_id_list_for_public) != \
            set(position_we_vote_id_list_for_public_latest)
        if friends_list_different or public_list_different:
            try:
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
        'date_of_notice_earlier_than_update_window':    False,
    }
    return results


def voter_activity_notice_list_retrieve_for_api(voter_device_id):  # voterActivityNoticeListRetrieve
    """
    See: activity_notice_list_retrieve_view in apis_v1/views/views_activity.py
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
            'activity_notice_list_found':   False,
            'activity_notice_list':         [],
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
