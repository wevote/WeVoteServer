# voter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import base64
import json
import re
from datetime import timedelta
from io import BytesIO
from time import time

import robot_detection
from PIL import Image, ImageOps
from django.db.models import F
from django.http import HttpResponse
from django.utils.timezone import now
from validate_email import validate_email

import wevote_functions.admin
from activity.controllers import delete_activity_comments_for_voter, delete_activity_notices_for_voter, \
    delete_activity_posts_for_voter, \
    move_activity_comments_to_another_voter, move_activity_notices_to_another_voter, \
    move_activity_posts_to_another_voter
from analytics.controllers import delete_analytics_info_for_voter, move_analytics_info_to_another_voter
from analytics.models import AnalyticsManager, ACTION_FACEBOOK_AUTHENTICATION_EXISTS, \
    ACTION_GOOGLE_AUTHENTICATION_EXISTS, \
    ACTION_TWITTER_AUTHENTICATION_EXISTS, ACTION_EMAIL_AUTHENTICATION_EXISTS
from aws.controllers import submit_web_function_job
from campaign.controllers import move_campaignx_to_another_voter
from email_outbound.controllers import delete_email_address_entries_for_voter, \
    move_email_address_entries_to_another_voter, schedule_verification_email, \
    WE_VOTE_SERVER_ROOT_URL, schedule_email_with_email_outbound_description
from email_outbound.models import EmailManager, EmailAddress, FRIEND_INVITATION_TEMPLATE, TO_BE_PROCESSED, \
    WAITING_FOR_VERIFICATION, SEND_BALLOT_TO_FRIENDS, SEND_BALLOT_TO_SELF
from follow.controllers import \
    delete_follow_issue_entries_for_voter, delete_follow_entries_for_voter, \
    duplicate_follow_entries_to_another_voter, \
    duplicate_follow_issue_entries_to_another_voter, \
    move_follow_issue_entries_to_another_voter, move_follow_entries_to_another_voter, \
    duplicate_organization_followers_to_another_organization
from friend.controllers import delete_friend_invitations_for_voter, delete_friends_for_voter, \
    delete_suggested_friends_for_voter, \
    fetch_friend_invitation_recipient_voter_we_vote_id, friend_accepted_invitation_send, \
    move_friend_invitations_to_another_voter, move_friends_to_another_voter, move_suggested_friends_to_another_voter, \
    retrieve_voter_and_email_address, \
    store_internal_friend_invitation_with_two_voters, store_internal_friend_invitation_with_unknown_email
from friend.models import FriendManager
from geoip.controllers import voter_location_retrieve_from_ip_for_api
from image.controllers import cache_voter_master_uploaded_image, PROFILE_IMAGE_ORIGINAL_MAX_WIDTH, \
    PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT, cache_image_locally, create_resized_images
from image.models import WeVoteImageManager
from import_export_facebook.models import FacebookManager
from import_export_twitter.models import TwitterAuthManager
from organization.controllers import delete_membership_link_entries_for_voter, delete_organization_complete, \
    move_membership_link_entries_to_another_voter, move_organization_team_member_entries_to_another_voter, \
    move_organization_to_another_complete, transfer_voter_images_to_organization, transform_web_app_url
from organization.models import OrganizationListManager, OrganizationManager, INDIVIDUAL
from position.controllers import delete_positions_for_voter, duplicate_positions_to_another_voter, \
    move_positions_to_another_voter
from position.models import PositionListManager
from share.controllers import move_shared_items_to_another_voter
from sms.controllers import delete_sms_phone_number_entries_for_voter, move_sms_phone_number_entries_to_another_voter
from stripe_donations.controllers import move_donation_info_to_another_voter
from twitter.models import TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from voter.controllers_contacts import delete_all_voter_contact_emails_for_voter
from voter.models import Voter, VoterAddress, VoterDeviceLinkManager, VoterManager, VoterMergeLog, \
    MAINTENANCE_STATUS_FLAGS_TASK_ONE, \
    NOTIFICATION_FRIEND_REQUESTS_EMAIL, NOTIFICATION_SUGGESTED_FRIENDS_EMAIL, \
    NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL, NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS, \
    NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL, MAINTENANCE_STATUS_FLAGS_TASK_TWO, \
    NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL, fetch_voter_id_from_voter_device_link, VoterAddressManager, \
    VoterDeviceLink, BALLOT_ADDRESS
from voter_guide.controllers import delete_voter_guides_for_voter, duplicate_voter_guides, \
    move_voter_guides_to_another_voter
from wevote_functions.functions import generate_voter_device_id, is_voter_device_id_valid, positive_value_exists
from campaign.controllers import delete_campaign_supporter


logger = wevote_functions.admin.get_logger(__name__)


def add_state_code_for_display_to_voter_list(voter_we_vote_id_list=None):
    if voter_we_vote_id_list is None:
        voter_we_vote_id_list = []
    status = ''
    success = True
    address_list_found = False
    voter_list = []
    voter_list_found = False

    try:
        voter_queryset = Voter.objects.all()
        voter_queryset = voter_queryset.filter(state_code_for_display_updated=False)
        if voter_we_vote_id_list and len(voter_we_vote_id_list) > 0:
            voter_queryset = voter_queryset.filter(we_vote_id__in=voter_we_vote_id_list)

        voter_list = voter_queryset[:1000]
        voter_list_found = len(voter_list)
    except Exception as e:
        status += "PROBLEM_RETRIEVING_VOTER_LIST: " + str(e) + " "

    address_dict_by_voter_id = {}
    if voter_list_found:
        updated_voter_id_list = []
        for one_voter in voter_list:
            updated_voter_id_list.append(one_voter.id)
        # Now retrieve all addresses related to any of these voter_we_vote_id's
        if updated_voter_id_list and len(updated_voter_id_list) > 0:
            try:
                address_queryset = VoterAddress.objects.all()
                address_queryset = address_queryset.filter(voter_id__in=updated_voter_id_list)
                address_queryset = address_queryset.order_by('-date_last_changed')

                address_list = list(address_queryset)
                address_list_found = len(address_list)
                if address_list_found:
                    for voter_address in address_list:
                        # Only use the most recently saved address
                        if voter_address.voter_id not in address_dict_by_voter_id:
                            address_dict_by_voter_id[voter_address.voter_id] = voter_address
            except Exception as e:
                status += "PROBLEM_RETRIEVING_VOTER_ADDRESS_LIST: " + str(e) + " "

    if voter_list_found and address_list_found:
        for one_voter in voter_list:
            one_voter_changed = False
            if one_voter.id in address_dict_by_voter_id:
                voter_address = address_dict_by_voter_id[one_voter.id]
                if hasattr(voter_address, 'normalized_state') and positive_value_exists(voter_address.normalized_state):
                    one_voter.state_code_for_display = voter_address.normalized_state
                    one_voter.state_code_for_display_updated = True
                    one_voter_changed = True
                elif hasattr(voter_address, 'text_for_map_search') and \
                        positive_value_exists(voter_address.text_for_map_search):
                    one_voter.state_code_for_display = voter_address.get_state_code_from_text_for_map_search()
                    one_voter.state_code_for_display_updated = True
                    one_voter_changed = True
            if one_voter_changed:
                one_voter.save()

    results = {
        'status':                       status,
        'success':                      success,
    }
    return results


def delete_all_voter_information_permanently(voter_to_delete=None, user=None):  # voterDeleteAccount
    success = True
    status = ""

    error_results = {
        'status':   status,
        'success':  success,
    }

    try:
        voter_to_delete_id = voter_to_delete.id
        voter_to_delete_we_vote_id = voter_to_delete.we_vote_id
    except Exception as e:
        status += "PROBLEM_WITH_INCOMING_VOTER_CANNOT_PROCEED_WITH_DELETE: " + str(e) + " "
        error_results['status'] = status
        error_results['success'] = False
        return error_results

    voter_device_link_manager = VoterDeviceLinkManager()

    # The voter_to_delete and to_voter may both have their own linked_organization_we_vote_id
    organization_manager = OrganizationManager()
    voter_to_delete_linked_organization_we_vote_id = voter_to_delete.linked_organization_we_vote_id
    voter_to_delete_linked_organization_id = 0
    if positive_value_exists(voter_to_delete_linked_organization_we_vote_id):
        from_linked_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            voter_to_delete_linked_organization_we_vote_id)
        if from_linked_organization_results['organization_found']:
            from_linked_organization = from_linked_organization_results['organization']
            voter_to_delete_linked_organization_id = from_linked_organization.id
        else:
            # Remove the link to the organization, so we don't have a future conflict
            try:
                voter_to_delete_linked_organization_we_vote_id = None
                voter_to_delete.linked_organization_we_vote_id = None
                voter_to_delete.save()
                # All positions should have already been moved with move_positions_to_another_voter
            except Exception as e:
                status += "FAILED_TO_REMOVE_LINKED_ORGANIZATION_WE_VOTE_ID-VOTER_TO_DELETE: " + str(e) + " "

    # Delete the apple_user entries
    from apple.controllers import delete_apple_user_entries_for_voter
    delete_apple_user_results = delete_apple_user_entries_for_voter(voter_to_delete_we_vote_id)
    status += delete_apple_user_results['status']

    # Data healing scripts before we try to delete the positions
    position_list_manager = PositionListManager()
    if positive_value_exists(voter_to_delete_id):
        repair_results = position_list_manager.repair_all_positions_for_voter(voter_to_delete_id)
        status += repair_results['status']

    # Delete positions from voter
    delete_positions_results = delete_positions_for_voter(voter_to_delete_id, voter_to_delete_we_vote_id)
    status += " " + delete_positions_results['status']

    # Delete voter's organization
    delete_organization_results = delete_organization_complete(
        voter_to_delete_linked_organization_id, voter_to_delete_linked_organization_we_vote_id)
    status += " " + delete_organization_results['status']

    # Delete friends
    delete_friends_results = delete_friends_for_voter(voter_to_delete_we_vote_id)
    status += " " + delete_friends_results['status']

    # Delete suggested friends
    delete_suggested_friends_results = delete_suggested_friends_for_voter(voter_to_delete_we_vote_id)

    # make delete suggested for

    status += " " + delete_suggested_friends_results['status']

    # Delete friend invitations
    delete_friend_invitations_results = delete_friend_invitations_for_voter(voter_to_delete_we_vote_id)
    status += " " + delete_friend_invitations_results['status']

    if positive_value_exists(voter_to_delete.linked_organization_we_vote_id):
        # Remove the link to the organization, so we don't have a future conflict
        try:
            voter_to_delete.linked_organization_we_vote_id = None
            voter_to_delete.save()
            # All positions should have already been moved with move_positions_to_another_voter
        except Exception as e:
            status += "CANNOT_DELETE_LINKED_ORGANIZATION_WE_VOTE_ID: " + str(e) + " "

    # Delete the organizations that voter_to_delete is following
    delete_follow_results = delete_follow_entries_for_voter(voter_to_delete_id)
    status += delete_follow_results['status']

    # Delete the organizations the voter_to_delete is a member of (with external_voter_id entry)
    delete_membership_link_results = delete_membership_link_entries_for_voter(voter_to_delete_we_vote_id)
    status += delete_membership_link_results['status']

    # Delete the issues that the voter is following
    delete_follow_issue_results = delete_follow_issue_entries_for_voter(voter_to_delete_we_vote_id)
    status += delete_follow_issue_results['status']

    # Make sure we delete all emails
    delete_email_addresses_results = delete_email_address_entries_for_voter(
        voter_to_delete_we_vote_id, voter_to_delete=voter_to_delete)
    status += delete_email_addresses_results['status']
    if delete_email_addresses_results['success']:
        voter_to_delete = delete_email_addresses_results['voter_to_delete']

    # Delete all sms phone numbers from the voter_to_delete
    delete_sms_phone_number_results = delete_sms_phone_number_entries_for_voter(
        voter_to_delete_we_vote_id, voter_to_delete=voter_to_delete)
    status += " " + delete_sms_phone_number_results['status']
    if delete_sms_phone_number_results['success']:
        voter_to_delete = delete_sms_phone_number_results['voter_to_delete']

    # Delete Facebook information
    delete_facebook_results = delete_facebook_info_for_voter(voter_to_delete)
    status += " " + delete_facebook_results['status']

    # Delete Twitter information
    delete_twitter_results = delete_twitter_info_for_voter(voter_to_delete)
    status += " " + delete_twitter_results['status']

    # Delete the voter's plans to vote
    delete_voter_plan_results = delete_voter_plan_for_voter(voter_to_delete)
    status += " " + delete_voter_plan_results['status']

    # # Bring over any donations that have been made in this session by the new_owner_voter to the voter, subscriptions
    # # are complicated.  See the comments in the donate/controllers.py
    # delete_donation_results = move_donation_info_to_another_voter(voter_to_delete, new_owner_voter)
    # status += " " + delete_donation_results['status']

    # Delete Voter Guides
    delete_voter_guide_results = delete_voter_guides_for_voter(
        voter_to_delete_we_vote_id, voter_to_delete_linked_organization_we_vote_id)
    status += " " + delete_voter_guide_results['status']

    # # Bring over SharedItems
    # delete_shared_items_results = move_shared_items_to_another_voter(
    #     voter_to_delete_we_vote_id, to_voter_we_vote_id,
    #     voter_to_delete_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id)
    # status += " " + delete_shared_items_results['status']

    # Delete ActivityNoticeSeed and ActivityNotice entries for voter
    delete_activity_results = delete_activity_notices_for_voter(
        voter_to_delete_we_vote_id, voter_to_delete_linked_organization_we_vote_id)
    status += " " + delete_activity_results['status']

    # Delete ActivityPost entries for voter
    delete_activity_post_results = delete_activity_posts_for_voter(
        voter_to_delete_we_vote_id, voter_to_delete_linked_organization_we_vote_id)
    status += " " + delete_activity_post_results['status']

    # Delete ActivityComment entries for voter
    delete_activity_comment_results = delete_activity_comments_for_voter(
        voter_to_delete_we_vote_id, voter_to_delete_linked_organization_we_vote_id)
    status += " " + delete_activity_comment_results['status']

    # Delete VoterContactEmail entries
    delete_voter_contact_email_results = delete_all_voter_contact_emails_for_voter(
        voter_we_vote_id=voter_to_delete_we_vote_id)
    status += " " + delete_voter_contact_email_results['status']

    # Delete Analytics information
    delete_analytics_results = delete_analytics_info_for_voter(voter_to_delete_we_vote_id)
    status += " " + delete_analytics_results['status']

    # Delete the voter-table data
    delete_voter_accounts_results = delete_voter_table_information(voter_to_delete)
    status += " " + delete_voter_accounts_results['status']

    # Delete Campaign Supporter
    delete_campaign_supporter_results = delete_campaign_supporter(voter_to_delete)
    status += " " + delete_campaign_supporter_results['status']

    # And finally, delete all voter_device_links for this voter
    update_link_results = voter_device_link_manager.delete_all_voter_device_links_by_voter_id(voter_to_delete_id)
    if update_link_results['success']:
        success = True
        status += "VOTER_DEVICE_LINK_DELETED "
    else:
        status += update_link_results['status']
        status += "VOTER_DEVICE_LINK_NOT_UPDATED "

    log = ''
    try:
        log += "VOTER_PERMANENTLY_DELETED: " + str(voter_to_delete_id) + " " + voter_to_delete_we_vote_id + " " + \
              voter_to_delete.first_name + " " + voter_to_delete.last_name + " " + voter_to_delete.email + \
              " " + str(voter_to_delete.date_joined)[:16]
        if user:
            log += ', deleted by ' + user.first_name + " " + user.last_name + " " + user.we_vote_id + " "
    except Exception as e:
        log += 'LOGGING_PROBLEM ' + str(e) + " "
    log += 'STATUS: ' + status + ' '
    logger.info(log)

    results = {
        'status':                       status,
        'success':                      success,
    }
    return results


def voter_delete_account_for_api(  # voterDeleteAccount
        voter_device_id=''):
    current_voter_found = False
    email_owner_voter_found = False
    facebook_owner_voter_found = False
    twitter_owner_voter_found = False
    invitation_owner_voter_found = False
    new_owner_voter = None
    success = False
    status = ""

    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        error_results = {
            'status': voter_device_link_results['status'],
            'success': False,
            'voter_device_id': voter_device_id,
            'current_voter_found': current_voter_found,
            'email_owner_voter_found': email_owner_voter_found,
            'facebook_owner_voter_found': facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
        }
        return error_results

    # We need this below
    voter_device_link = voter_device_link_results['voter_device_link']

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=False)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'current_voter_found': current_voter_found,
            'email_owner_voter_found': email_owner_voter_found,
            'facebook_owner_voter_found': facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
        }
        return error_results

    voter = voter_results['voter']
    status += "DELETE_VOTER-" + str(voter.we_vote_id) + " "

    # if not positive_value_exists(email_secret_key) \
    #         and not positive_value_exists(facebook_secret_key) \
    #         and not positive_value_exists(twitter_secret_key) \
    #         and not positive_value_exists(invitation_secret_key):
    #     error_results = {
    #         'status': "VOTER_SPLIT_INTO_TWO_ACCOUNTS_SECRET_KEY_NOT_PASSED_IN",
    #         'success': False,
    #         'voter_device_id': voter_device_id,
    #         'current_voter_found': current_voter_found,
    #         'email_owner_voter_found': email_owner_voter_found,
    #         'facebook_owner_voter_found': facebook_owner_voter_found,
    #         'invitation_owner_voter_found': False,
    #     }
    #     return error_results

    results = delete_all_voter_information_permanently(voter_to_delete=voter)

    return results


def delete_facebook_info_for_voter(voter_to_delete):
    status = "DELETE_FACEBOOK_INFO "
    success = False

    if not hasattr(voter_to_delete, "we_vote_id") or not positive_value_exists(voter_to_delete.we_vote_id):
        status += "DELETE_FACEBOOK_INFO_MISSING_FROM_OR_TO_VOTER_ID "
        results = {
            'status': status,
            'success': success,
            'voter_to_delete': voter_to_delete,
        }
        return results

    facebook_manager = FacebookManager()
    voter_to_delete_facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        voter_to_delete.we_vote_id, read_only=False)

    if voter_to_delete_facebook_results['facebook_link_to_voter_found']:
        voter_to_delete_facebook_link = voter_to_delete_facebook_results['facebook_link_to_voter']
        try:
            voter_to_delete_facebook_link.delete()
            success = True
            status += "FROM_VOTER_FACEBOOK_LINK_MOVED "
        except Exception as e:
            status += "FROM_VOTER_FACEBOOK_LINK_COULD_NOT_BE_MOVED "

    if positive_value_exists(voter_to_delete.facebook_id):
        # Delete any facebook_user records (That contains cached links to the voter's picture)
        facebook_manager.delete_facebook_users(voter_to_delete.facebook_id)
        # Delete facebook_link_to_voter  (That contains cached links to the voter's picture)
        facebook_manager.delete_facebook_link_to_voter(voter_to_delete.we_vote_id)

        # Remove info from the voter_to_delete and then move facebook info to the to_voter
        try:
            voter_to_delete.facebook_email = ""
            voter_to_delete.facebook_id = 0
            voter_to_delete.facebook_profile_image_url_https = ""
            voter_to_delete.fb_username = None
            voter_to_delete.save()
            status += "FROM_VOTER_FACEBOOK_DATA_REMOVED "
        except Exception as e:
            status += "FROM_VOTER_FACEBOOK_DATA_COULD_NOT_BE_DELETED: " + str(e) + " "
    else:
        success = True
        status += "NO_FACEBOOK_ID_FOUND "

    results = {
        'status':           status,
        'success':          success,
        'voter_to_delete':  voter_to_delete,
    }
    return results


def delete_twitter_info_for_voter(voter_to_delete):
    status = "DELETE_TWITTER_INFO "
    success = True

    if not hasattr(voter_to_delete, "we_vote_id") or not positive_value_exists(voter_to_delete.we_vote_id):
        status += "DELETE_TWITTER_INFO_MISSING_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'voter_to_delete': voter_to_delete,
        }
        return results

    twitter_user_manager = TwitterUserManager()
    voter_to_delete_twitter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        voter_to_delete.we_vote_id)  # Cannot be read_only

    if voter_to_delete_twitter_results['twitter_link_to_voter_found']:
        voter_to_delete_twitter_link = voter_to_delete_twitter_results['twitter_link_to_voter']
        try:
            voter_to_delete_twitter_link.delete()
            success = True
            status += "FROM_VOTER_TWITTER_LINK_DELETED "
        except Exception as e:
            # Fail silently
            status += "FROM_VOTER_TWITTER_LINK_NOT_DELETED: " + str(e) + " "
            success = False

    try:
        voter_to_delete.twitter_id = None
        voter_to_delete.twitter_name = ""
        voter_to_delete.twitter_profile_image_url_https = ""
        voter_to_delete.twitter_screen_name = ""
        voter_to_delete.save()
        status += "FROM_VOTER_TWITTER_DATA_REMOVED "
    except Exception as e:
        status += "FROM_VOTER_TWITTER_DATA_NOT_REMOVED: " + str(e) + " "
        success = False

    results = {
        'status': status,
        'success': success,
        'voter_to_delete': voter_to_delete,
    }
    return results


def delete_voter_plan_for_voter(voter_to_delete):
    status = "DELETE_VOTER_PLAN "
    success = True
    entries_deleted = 0
    entries_not_deleted = 0

    if not hasattr(voter_to_delete, "we_vote_id") or not positive_value_exists(voter_to_delete.we_vote_id):
        status += "DELETE_VOTER_PLAN_MISSING_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':               status,
            'success':              success,
            'entries_deleted':      entries_deleted,
            'entries_not_deleted':  entries_not_deleted,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_plan_list(voter_we_vote_id=voter_to_delete.we_vote_id, read_only=False)
    voter_to_delete_plan_list = results['voter_plan_list']

    for voter_to_delete_plan in voter_to_delete_plan_list:
        try:
            voter_to_delete_plan.delete()
        except Exception as e:
            status += "FAILED_DELETE_VOTER_PLAN: " + str(e) + " "
            success = False

    results = {
        'status':               status,
        'success':              success,
        'entries_deleted':      entries_deleted,
        'entries_not_deleted':  entries_not_deleted,
    }
    return results


def delete_voter_table_information(voter_to_delete):
    status = "DELETE_VOTER_TABLE_INFO "
    success = True

    if not hasattr(voter_to_delete, "we_vote_id") or not positive_value_exists(voter_to_delete.we_vote_id):
        status += "DELETE_VOTER_INFO_MISSING_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':           status,
            'success':          success,
            'voter_to_delete':  voter_to_delete,
        }
        return results

    try:
        voter_to_delete.delete()
        status += "VOTER_DELETED "
    except Exception as e:
        status += "VOTER_MERGE_SAVE_FAILED " + str(e) + " "
        success = False

    results = {
        'status':           status,
        'success':          success,
        'voter_to_delete':  voter_to_delete,
    }
    return results


def email_ballot_data_for_api(voter_device_id, email_address_array, first_name_array, last_name_array,
                              email_addresses_raw, invitation_message, ballot_link,
                              sender_email_address, verification_email_sent, web_app_root_url=''):  # emailBallotData
    """

    :param voter_device_id:
    :param email_address_array:
    :param first_name_array:
    :param last_name_array:
    :param email_addresses_raw:
    :param invitation_message:
    :param ballot_link:
    :param sender_email_address:
    :param verification_email_sent
    :param web_app_root_url
    :return:
    """
    success = False
    status = ""
    error_message_to_show_voter = ""

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                               results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    sender_voter_id = voter_results['voter_id']
    if not positive_value_exists(sender_voter_id):
        error_results = {
            'status':                               "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    sender_voter = voter_results['voter']
    email_manager = EmailManager()

    send_now = False
    valid_new_sender_email_address = False
    sender_email_with_ownership_verified = ""
    if sender_voter.has_email_with_verified_ownership():
        send_now = True
        sender_email_with_ownership_verified = \
            email_manager.fetch_primary_email_with_ownership_verified(sender_voter.we_vote_id)
    else:
        # If here, check to see if a sender_email_address was passed in
        valid_new_sender_email_address = False
        if not positive_value_exists(sender_email_address) or not validate_email(sender_email_address):
            error_results = {
                'status':                               "VOTER_DOES_NOT_HAVE_VALID_EMAIL",
                'success':                              False,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   True,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results
        else:
            valid_new_sender_email_address = True

    sender_email_address_object = EmailAddress()
    if valid_new_sender_email_address:
        # If here then the sender has entered an email address in the "Email a Friend" form.
        # Is this email owned and verified by another voter? If so, then save the invitations with this
        # voter_id and send a verification email.
        # TODO If that email is verified we will want to send the invitations *then*
        # Does this email exist in the EmailAddress database for this voter?
        email_address_object_found = False
        results = email_manager.retrieve_email_address_object(sender_email_address, '', sender_voter.we_vote_id)
        if results['email_address_object_found']:
            sender_email_address_object = results['email_address_object']
            email_address_object_found = True
        elif results['email_address_list_found']:
            # The case where there is more than one email entry for one voter shouldn't be possible, but if so,
            # just use the first one returned
            email_address_list = results['email_address_list']
            sender_email_address_object = email_address_list[0]
            email_address_object_found = True
        else:
            # Create email address object
            email_results = email_manager.create_email_address_for_voter(sender_email_address, sender_voter)

            if email_results['email_address_object_saved']:
                # We recognize the email
                email_address_object_found = True
                sender_email_address_object = email_results['email_address_object']
            else:
                valid_new_sender_email_address = False

        # double-check that we have email_address_object
        if not email_address_object_found:
            success = False
            status = "EMAIL_BALLOT_DATA_SEND-EMAIL_ADDRESS_OBJECT_MISSING"
            error_results = {
                'success':                              success,
                'status':                               status,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   True,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results

    if not verification_email_sent and valid_new_sender_email_address:
        # Send verification email, and store the rest of the data without processing until sender_email is verified
        recipient_voter_we_vote_id = sender_voter.we_vote_id
        recipient_email_we_vote_id = sender_email_address_object.we_vote_id
        recipient_voter_email = sender_email_address_object.normalized_email_address
        if positive_value_exists(sender_email_address_object.secret_key):
            recipient_email_address_secret_key = sender_email_address_object.secret_key
        else:
            recipient_email_address_secret_key = \
                email_manager.update_email_address_with_new_secret_key(recipient_email_we_vote_id)
        if positive_value_exists(sender_email_address_object.subscription_secret_key):
            recipient_email_subscription_secret_key = sender_email_address_object.subscription_secret_key
        else:
            recipient_email_subscription_secret_key = \
                email_manager.update_email_address_with_new_subscription_secret_key(
                    email_we_vote_id=recipient_email_we_vote_id)
        send_now = False

        verifications_send_results = schedule_verification_email(
            sender_voter_we_vote_id=sender_voter.we_vote_id,
            recipient_voter_we_vote_id=recipient_voter_we_vote_id,
            recipient_email_we_vote_id=recipient_email_we_vote_id,
            recipient_voter_email=recipient_voter_email,
            recipient_email_address_secret_key=recipient_email_address_secret_key,
            recipient_email_subscription_secret_key=recipient_email_subscription_secret_key,
            web_app_root_url=web_app_root_url)
        status += verifications_send_results['status']
        email_scheduled_saved = verifications_send_results['email_scheduled_saved']
        email_scheduled_id = verifications_send_results['email_scheduled_id']
        # if email_scheduled_saved:
        #     messages_to_send.append(email_scheduled_id)

    if sender_voter.has_valid_email() or valid_new_sender_email_address:
        # We can continue. Note that we are not checking for "voter.has_email_with_verified_ownership()"
        pass
    else:
        error_results = {
            'status':                               "VOTER_DOES_NOT_HAVE_VALID_EMAIL",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   True,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return error_results

    if not isinstance(first_name_array, (list, tuple)):
        first_name_array = []

    if not isinstance(last_name_array, (list, tuple)):
        last_name_array = []

    if email_address_array:
        # Reconstruct dictionary array from lists
        for n in range(len(email_address_array)):
            first_name = first_name_array[n]
            last_name = last_name_array[n]
            one_normalized_raw_email = email_address_array[n]
            send_results = send_ballot_email(voter_device_id, sender_voter, send_now, sender_email_address,
                                             sender_email_with_ownership_verified,
                                             one_normalized_raw_email, first_name, last_name, invitation_message,
                                             ballot_link, web_app_root_url=web_app_root_url)
            status += send_results['status']

    else:
        # Break apart all the emails in email_addresses_raw input from the voter
        results = email_manager.parse_raw_emails_into_list(email_addresses_raw)
        if results['at_least_one_email_found']:
            raw_email_list_to_invite = results['email_list']
            first_name = ""
            last_name = ""
            for one_normalized_raw_email in raw_email_list_to_invite:
                send_results = send_ballot_email(voter_device_id, sender_voter, send_now, sender_email_address,
                                                 sender_email_with_ownership_verified,
                                                 one_normalized_raw_email, first_name, last_name, invitation_message,
                                                 ballot_link, web_app_root_url=web_app_root_url)
                status += send_results['status']
        else:
            error_message_to_show_voter = "Please enter the email address of at least one friend."
            error_results = {
                'status':                               "LIST_OF_EMAILS_NOT_RECEIVED " + results['status'],
                'success':                              False,
                'voter_device_id':                      voter_device_id,
                'sender_voter_email_address_missing':   False,
                'error_message_to_show_voter':          error_message_to_show_voter
            }
            return error_results

    # When we are done scheduling all email, send it with a single connection to the smtp server
    # if send_now:
    #     send_results = email_manager.send_scheduled_email_list(messages_to_send)

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   False,
        'error_message_to_show_voter':          error_message_to_show_voter
    }
    return results


def merge_voter_accounts(from_voter, to_voter):
    status = "MOVE_VOTER_TABLE_INFO "  # Deal with situation where destination account already has facebook_id
    success = True

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_VOTER_INFO_MISSING_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':       status,
            'success':      success,
            'from_voter':   from_voter,
            'to_voter':     to_voter,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_VOTER_INFO_FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':       status,
            'success':      success,
            'from_voter':   from_voter,
            'to_voter':     to_voter,
        }
        return results

    # Transfer data in voter records
    # first_name
    # middle_name
    # last_name
    # interface_status_flags
    # is_admin
    # is_analytics_admin
    # is_partner_organization
    # is_political_data_manager
    # is_political_data_viewer
    # is_verified_volunteer

    # Is there data we should migrate?
    if positive_value_exists(from_voter.first_name) \
            or positive_value_exists(from_voter.interface_status_flags) \
            or positive_value_exists(from_voter.is_admin) \
            or positive_value_exists(from_voter.is_analytics_admin) \
            or positive_value_exists(from_voter.is_partner_organization) \
            or positive_value_exists(from_voter.is_political_data_manager) \
            or positive_value_exists(from_voter.is_political_data_viewer) \
            or positive_value_exists(from_voter.is_verified_volunteer) \
            or positive_value_exists(from_voter.is_voter_manager) \
            or positive_value_exists(from_voter.last_name) \
            or positive_value_exists(from_voter.middle_name) \
            or positive_value_exists(from_voter.notification_settings_flags) \
            or positive_value_exists(from_voter.profile_image_type_currently_active) \
            or positive_value_exists(from_voter.twitter_profile_image_url_https) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_facebook_image_url_large) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_facebook_image_url_medium) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_facebook_image_url_tiny) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_image_url_large) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_image_url_medium) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_image_url_tiny) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_twitter_image_url_large) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_twitter_image_url_medium) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_twitter_image_url_tiny) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_uploaded_image_url_large) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_uploaded_image_url_medium) \
            or positive_value_exists(from_voter.we_vote_hosted_profile_uploaded_image_url_tiny):
        from_voter_data_to_migrate_exists = True
    else:
        from_voter_data_to_migrate_exists = False
    if from_voter_data_to_migrate_exists:
        # Remove info from the from_voter and then move Twitter info to the to_voter
        try:
            # Now move values to new entry and save if the to_voter doesn't have any data
            if positive_value_exists(from_voter.first_name) and not positive_value_exists(to_voter.first_name):
                to_voter.first_name = from_voter.first_name
            # Set all bits that have a value in either from_voter or to_voter
            to_voter.interface_status_flags = to_voter.interface_status_flags | from_voter.interface_status_flags
            if positive_value_exists(from_voter.is_admin) and not positive_value_exists(to_voter.is_admin):
                to_voter.is_admin = from_voter.is_admin
            if positive_value_exists(from_voter.is_analytics_admin) \
                    and not positive_value_exists(to_voter.is_analytics_admin):
                to_voter.is_analytics_admin = from_voter.is_analytics_admin
            if positive_value_exists(from_voter.is_partner_organization) \
                    and not positive_value_exists(to_voter.is_partner_organization):
                to_voter.is_partner_organization = from_voter.is_partner_organization
            if positive_value_exists(from_voter.is_political_data_manager) \
                    and not positive_value_exists(to_voter.is_political_data_manager):
                to_voter.is_political_data_manager = from_voter.is_political_data_manager
            if positive_value_exists(from_voter.is_political_data_viewer) \
                    and not positive_value_exists(to_voter.is_political_data_viewer):
                to_voter.is_political_data_viewer = from_voter.is_political_data_viewer
            if positive_value_exists(from_voter.is_verified_volunteer) \
                    and not positive_value_exists(to_voter.is_verified_volunteer):
                to_voter.is_verified_volunteer = from_voter.is_verified_volunteer
            if positive_value_exists(from_voter.is_voter_manager) \
                    and not positive_value_exists(to_voter.is_voter_manager):
                to_voter.is_voter_manager = from_voter.is_voter_manager
            if positive_value_exists(from_voter.last_name) and not positive_value_exists(to_voter.last_name):
                to_voter.last_name = from_voter.last_name
            if positive_value_exists(from_voter.middle_name) and not positive_value_exists(to_voter.middle_name):
                to_voter.middle_name = from_voter.middle_name
            # Set all bits that have a value in either from_voter or to_voter
            to_voter.notification_settings_flags = \
                to_voter.notification_settings_flags | from_voter.notification_settings_flags
            if positive_value_exists(from_voter.profile_image_type_currently_active) \
                    and not positive_value_exists(to_voter.profile_image_type_currently_active):
                to_voter.profile_image_type_currently_active = from_voter.profile_image_type_currently_active
            if positive_value_exists(from_voter.twitter_profile_image_url_https) \
                    and not positive_value_exists(to_voter.twitter_profile_image_url_https):
                to_voter.twitter_profile_image_url_https = from_voter.twitter_profile_image_url_https
            if positive_value_exists(from_voter.we_vote_hosted_profile_facebook_image_url_large) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_facebook_image_url_large):
                to_voter.we_vote_hosted_profile_facebook_image_url_large = \
                    from_voter.we_vote_hosted_profile_facebook_image_url_large
            if positive_value_exists(from_voter.we_vote_hosted_profile_facebook_image_url_medium) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_facebook_image_url_medium):
                to_voter.we_vote_hosted_profile_facebook_image_url_medium = \
                    from_voter.we_vote_hosted_profile_facebook_image_url_medium
            if positive_value_exists(from_voter.we_vote_hosted_profile_facebook_image_url_tiny) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_facebook_image_url_tiny):
                to_voter.we_vote_hosted_profile_facebook_image_url_tiny = \
                    from_voter.we_vote_hosted_profile_facebook_image_url_tiny
            if positive_value_exists(from_voter.we_vote_hosted_profile_image_url_large) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_image_url_large):
                to_voter.we_vote_hosted_profile_image_url_large = from_voter.we_vote_hosted_profile_image_url_large
            if positive_value_exists(from_voter.we_vote_hosted_profile_image_url_medium) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_image_url_medium):
                to_voter.we_vote_hosted_profile_image_url_medium = from_voter.we_vote_hosted_profile_image_url_medium
            if positive_value_exists(from_voter.we_vote_hosted_profile_image_url_tiny) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_image_url_tiny):
                to_voter.we_vote_hosted_profile_image_url_tiny = from_voter.we_vote_hosted_profile_image_url_tiny
            if positive_value_exists(from_voter.we_vote_hosted_profile_twitter_image_url_large) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_twitter_image_url_large):
                to_voter.we_vote_hosted_profile_twitter_image_url_large = \
                    from_voter.we_vote_hosted_profile_twitter_image_url_large
            if positive_value_exists(from_voter.we_vote_hosted_profile_twitter_image_url_medium) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_twitter_image_url_medium):
                to_voter.we_vote_hosted_profile_twitter_image_url_medium = \
                    from_voter.we_vote_hosted_profile_twitter_image_url_medium
            if positive_value_exists(from_voter.we_vote_hosted_profile_twitter_image_url_tiny) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_twitter_image_url_tiny):
                to_voter.we_vote_hosted_profile_twitter_image_url_tiny = \
                    from_voter.we_vote_hosted_profile_twitter_image_url_tiny
            if positive_value_exists(from_voter.we_vote_hosted_profile_uploaded_image_url_large) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_uploaded_image_url_large):
                to_voter.we_vote_hosted_profile_uploaded_image_url_large = \
                    from_voter.we_vote_hosted_profile_uploaded_image_url_large
            if positive_value_exists(from_voter.we_vote_hosted_profile_uploaded_image_url_medium) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_uploaded_image_url_medium):
                to_voter.we_vote_hosted_profile_uploaded_image_url_medium = \
                    from_voter.we_vote_hosted_profile_uploaded_image_url_medium
            if positive_value_exists(from_voter.we_vote_hosted_profile_uploaded_image_url_tiny) \
                    and not positive_value_exists(to_voter.we_vote_hosted_profile_uploaded_image_url_tiny):
                to_voter.we_vote_hosted_profile_uploaded_image_url_tiny = \
                    from_voter.we_vote_hosted_profile_uploaded_image_url_tiny
            to_voter.save()
            status += "TO_VOTER_MERGE_SAVED "
        except Exception as e:
            status += "TO_VOTER_MERGE_SAVE_FAILED: " + str(e) + " "
            success = False

    else:
        status += "FROM_VOTER_DATA_TO_MIGRATE_NOT_FOUND "

    results = {
        'status':       status,
        'success':      success,
        'from_voter':   from_voter,
        'to_voter':     to_voter,
    }
    return results


def move_facebook_info_to_another_voter(from_voter, to_voter):
    status = "MOVE_FACEBOOK_INFO "  # Deal with situation where destination account already has facebook_id
    success = True

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_FACEBOOK_INFO_MISSING_FROM_OR_TO_VOTER_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_FACEBOOK_INFO_TO_ANOTHER_VOTER-from_voter.we_vote_id and to_voter.we_vote_id identical "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    facebook_manager = FacebookManager()
    to_voter_facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        to_voter.we_vote_id, read_only=False)
    if not to_voter_facebook_results['success']:
        status += to_voter_facebook_results['status']
        success = False
    # if to_voter_facebook_results['facebook_link_to_voter_found']:
    #     to_voter_facebook_link = to_voter_facebook_results['facebook_link_to_voter']
    from_voter_facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        from_voter.we_vote_id, read_only=False)
    if not from_voter_facebook_results['success']:
        status += from_voter_facebook_results['status']
        success = False

    # Move facebook_link_to_voter
    if to_voter_facebook_results['facebook_link_to_voter_found']:
        # Don't try to move from the from_voter
        status += "TO_VOTER_ALREADY_HAS_FACEBOOK_LINK "
    elif from_voter_facebook_results['facebook_link_to_voter_found']:
        from_voter_facebook_link = from_voter_facebook_results['facebook_link_to_voter']
        try:
            from_voter_facebook_link.voter_we_vote_id = to_voter.we_vote_id
            from_voter_facebook_link.save()
            status += "FROM_VOTER_FACEBOOK_LINK_MOVED "
        except Exception as e:
            status += "FROM_VOTER_FACEBOOK_LINK_COULD_NOT_BE_MOVED: " + str(e) + " "
            success = False
    elif positive_value_exists(from_voter.facebook_id):
        create_results = facebook_manager.create_facebook_link_to_voter(from_voter.facebook_id, to_voter.we_vote_id)
        status += " " + create_results['status']
        if not create_results['success']:
            success = False

    # Transfer data in voter records
    temp_facebook_email = ""
    temp_facebook_id = 0
    temp_facebook_profile_image_url_https = ""
    temp_fb_username = None
    if positive_value_exists(to_voter.facebook_id):
        # Don't try to move from the from_voter
        status += "TO_VOTER_ALREADY_HAS_FACEBOOK_ID "
    elif positive_value_exists(from_voter.facebook_id):
        # Remove info from the from_voter and then move facebook info to the to_voter
        try:
            # Copy values
            temp_facebook_email = from_voter.facebook_email
            temp_facebook_id = from_voter.facebook_id
            temp_facebook_profile_image_url_https = from_voter.facebook_profile_image_url_https
            temp_fb_username = from_voter.fb_username
            # Now delete it and save, so we can save the unique facebook_id in the to_voter
            from_voter.facebook_email = ""
            from_voter.facebook_id = 0
            from_voter.facebook_profile_image_url_https = ""
            from_voter.fb_username = None
            from_voter.save()
            status += "FROM_VOTER_FACEBOOK_DATA_REMOVED "
        except Exception as e:
            status += "FROM_VOTER_FACEBOOK_DATA_COULD_NOT_BE_REMOVED: " + str(e) + " "
            success = False

        try:
            # Now move values to new entry and save
            to_voter.facebook_email = temp_facebook_email
            to_voter.facebook_id = temp_facebook_id
            to_voter.facebook_profile_image_url_https = temp_facebook_profile_image_url_https
            to_voter.fb_username = temp_fb_username
            to_voter.save()
            status += "TO_VOTER_FACEBOOK_DATA_SAVED "
        except Exception as e:
            status += "TO_VOTER_FACEBOOK_DATA_COULD_NOT_BE_SAVED: " + str(e) + " "
            success = False

    else:
        status += "NO_FACEBOOK_ID_FOUND "

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'to_voter': to_voter,
    }
    return results


def move_twitter_info_to_another_voter(from_voter, to_voter):
    status = "MOVE_TWITTER_INFO "  # Deal with situation where destination account already has facebook_id
    success = True

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_TWITTER_INFO_MISSING_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_TWITTER_INFO_TO_ANOTHER_VOTER-from_voter.we_vote_id and to_voter.we_vote_id identical "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    twitter_user_manager = TwitterUserManager()
    to_voter_twitter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        to_voter.we_vote_id)  # Cannot be read_only
    if not to_voter_twitter_results['success']:
        status += to_voter_twitter_results['status']
        success = False
    from_voter_twitter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        from_voter.we_vote_id)  # Cannot be read_only
    if not from_voter_twitter_results['success']:
        status += from_voter_twitter_results['status']
        success = False

    # Move twitter_link_to_voter
    if to_voter_twitter_results['twitter_link_to_voter_found']:
        if from_voter_twitter_results['twitter_link_to_voter_found']:
            success = False
            status += "FROM_AND_TO_VOTER_BOTH_HAVE_TWITTER_LINKS "
        else:
            status += "TO_VOTER_ALREADY_HAS_TWITTER_LINK "
    elif from_voter_twitter_results['twitter_link_to_voter_found']:
        from_voter_twitter_link = from_voter_twitter_results['twitter_link_to_voter']
        try:
            from_voter_twitter_link.voter_we_vote_id = to_voter.we_vote_id
            from_voter_twitter_link.save()
            status += "FROM_VOTER_TWITTER_LINK_MOVED "
        except Exception as e:
            status += "FROM_VOTER_TWITTER_LINK_NOT_MOVED: " + str(e) + " "
            success = False
    elif positive_value_exists(from_voter.twitter_id):
        # If this is the only voter with twitter_id, heal the data and create a TwitterLinkToVoter entry
        voter_manager = VoterManager()
        duplicate_twitter_results = voter_manager.retrieve_voter_by_twitter_id_old(from_voter.twitter_id)
        if not duplicate_twitter_results['success']:
            status += duplicate_twitter_results['status']
            success = False
        if duplicate_twitter_results['voter_found']:
            # If here, we know that this was the only voter with this twitter_id
            test_duplicate_voter = duplicate_twitter_results['voter']
            if test_duplicate_voter.we_vote_id == from_voter.we_vote_id:
                create_results = twitter_user_manager.create_twitter_link_to_voter(from_voter.twitter_id,
                                                                                   to_voter.we_vote_id)
                if not create_results['success']:
                    status += create_results['status']
                    success = False
                status += " " + create_results['status']
                # We remove from_voter.twitter_id value below

    # Transfer data in voter records
    temp_twitter_id = 0
    temp_twitter_name = ""
    temp_twitter_profile_image_url_https = ""
    temp_twitter_screen_name = ""
    if positive_value_exists(to_voter.twitter_id):
        # Don't try to move from the from_voter
        status += "TO_VOTER_ALREADY_HAS_TWITTER_ID "
    elif positive_value_exists(from_voter.twitter_id):
        # Remove info from the from_voter and then move Twitter info to the to_voter
        try:
            # Copy values
            temp_twitter_id = from_voter.twitter_id
            temp_twitter_name = from_voter.twitter_name
            temp_twitter_profile_image_url_https = from_voter.twitter_profile_image_url_https
            temp_twitter_screen_name = from_voter.twitter_screen_name
            # Now delete it and save, so we can save the unique facebook_id in the to_voter
            from_voter.twitter_id = None
            from_voter.twitter_name = ""
            from_voter.twitter_profile_image_url_https = ""
            from_voter.twitter_screen_name = ""
            from_voter.save()
            status += "FROM_VOTER_TWITTER_DATA_REMOVED "
        except Exception as e:
            status += "FROM_VOTER_TWITTER_DATA_NOT_REMOVED: " + str(e) + " "
            success = False

        try:
            # Now move values to new entry and save
            to_voter.twitter_id = temp_twitter_id
            to_voter.twitter_name = temp_twitter_name
            to_voter.twitter_profile_image_url_https = temp_twitter_profile_image_url_https
            to_voter.twitter_screen_name = temp_twitter_screen_name
            to_voter.save()
            status += "TO_VOTER_TWITTER_DATA_SAVED "
        except Exception as e:
            # Fail silently
            status += "TO_VOTER_TWITTER_DATA_NOT_SAVED "

    else:
        success = True
        status += "NO_TWITTER_ID_FOUND "

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'to_voter': to_voter,
    }
    return results


def move_voter_plan_to_another_voter(from_voter, to_voter):
    status = "MOVE_VOTER_PLAN "
    success = True
    entries_moved = 0
    entries_not_moved = 0

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_VOTER_PLAN_MISSING_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'entries_moved': entries_moved,
            'entries_not_moved': entries_not_moved,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_VOTER_PLAN_TO_ANOTHER_VOTER-from_voter.we_vote_id and to_voter.we_vote_id identical "
        success = False
        results = {
            'status': status,
            'success': success,
            'entries_moved': entries_moved,
            'entries_not_moved': entries_not_moved,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_plan_list(voter_we_vote_id=from_voter.we_vote_id, read_only=False)
    if not results['success']:
        status += results['status']
        success = False
    from_voter_plan_list = results['voter_plan_list']

    results = voter_manager.retrieve_voter_plan_list(voter_we_vote_id=to_voter.we_vote_id, read_only=False)
    to_voter_plan_list = results['voter_plan_list']
    if not results['success']:
        status += results['status']
        success = False

    from_voter_plan_ids_matched_list = []
    for from_voter_plan in from_voter_plan_list:
        for to_voter_plan in to_voter_plan_list:
            if from_voter_plan.google_civic_election_id == to_voter_plan.google_civic_election_id:
                from_voter_plan_ids_matched_list.append(from_voter_plan.id)
        if from_voter_plan.id in from_voter_plan_ids_matched_list:
            # Delete the from_voter_plan since there is already a to_voter_plan
            try:
                from_voter_plan.delete()
            except Exception as e:
                status += "FAILED_DELETE_VOTER_PLAN: " + str(e) + " "
                success = False
        else:
            # Change the from_voter_we_vote_id to to_voter_we_vote_id
            try:
                from_voter_plan.voter_we_vote_id = to_voter.we_vote_id
                from_voter_plan.save()
                entries_moved += 1
            except Exception as e:
                entries_not_moved += 1
                status += "FAILED_MOVE_VOTER_PLAN: " + str(e) + " "
                success = False

    results = {
        'status':               status,
        'success':              success,
        'entries_moved':        entries_moved,
        'entries_not_moved':    entries_not_moved,
    }
    return results


def process_maintenance_status_flags():
    status = ""
    success = True
    longest_activity_notice_processing_run_time_allowed = 900  # 15 minutes * 60 seconds
    when_process_must_stop = now() + timedelta(seconds=longest_activity_notice_processing_run_time_allowed)

    # Task 1 (bit 1, integer 1) MAINTENANCE_STATUS_FLAGS_TASK_ONE
    continue_retrieving_for_task_one = True
    no_more_task1_voters_found = False
    safety_valve_count = 0
    voters_updated_task_one = 0
    while continue_retrieving_for_task_one and safety_valve_count < 1000 and when_process_must_stop > now():
        safety_valve_count += 1
        # Retrieve voters. Exclude rows where MAINTENANCE_STATUS_FLAGS_TASK_ONE bit is already set
        #  in maintenance_status_flags field.
        query = Voter.objects.annotate(
            task_one_flag_already_set=F('maintenance_status_flags').bitand(MAINTENANCE_STATUS_FLAGS_TASK_ONE)
        ).exclude(task_one_flag_already_set=MAINTENANCE_STATUS_FLAGS_TASK_ONE)
        task_one_voter_list = query[:100]
        if len(task_one_voter_list) == 0:
            continue_retrieving_for_task_one = False
            no_more_task1_voters_found = True
        for voter_on_stage in task_one_voter_list:
            updated_flags = voter_on_stage.notification_settings_flags

            # Since these are all new settings, we don't need to see if they have been set or unset by voter.
            updated_flags = updated_flags | NOTIFICATION_FRIEND_REQUESTS_EMAIL
            updated_flags = updated_flags | NOTIFICATION_SUGGESTED_FRIENDS_EMAIL
            updated_flags = updated_flags | NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL
            updated_flags = updated_flags | NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS
            updated_flags = updated_flags | NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL
            voter_on_stage.notification_settings_flags = updated_flags

            # Set the TASK_ONE bit as true in maintenance_status_flags to show it is complete for this voter
            voter_on_stage.maintenance_status_flags = \
                voter_on_stage.maintenance_status_flags | MAINTENANCE_STATUS_FLAGS_TASK_ONE
            voter_on_stage.save()
            voters_updated_task_one += 1

    # Task 2 (bit 2, integer 2) MAINTENANCE_STATUS_FLAGS_TASK_TWO
    continue_retrieving_for_task_two = True
    no_more_task2_voters_found = False
    safety_valve_count = 0
    voters_updated_task_two = 0
    if no_more_task1_voters_found:
        while continue_retrieving_for_task_two and safety_valve_count < 1000 and when_process_must_stop > now():
            safety_valve_count += 1
            # Retrieve voters. Exclude rows where MAINTENANCE_STATUS_FLAGS_TASK_TWO bit is already set
            #  in maintenance_status_flags field.
            query = Voter.objects.annotate(
                task_two_flag_already_set=F('maintenance_status_flags').bitand(MAINTENANCE_STATUS_FLAGS_TASK_TWO)
            ).exclude(task_two_flag_already_set=MAINTENANCE_STATUS_FLAGS_TASK_TWO)
            task_two_voter_list = query[:100]
            if len(task_two_voter_list) == 0:
                continue_retrieving_for_task_two = False
                no_more_task2_voters_found = True
            for voter_on_stage in task_two_voter_list:
                updated_flags = voter_on_stage.notification_settings_flags

                # Since these are new settings, we don't need to see if they have been set or unset by voter.
                updated_flags = updated_flags | NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL
                voter_on_stage.notification_settings_flags = updated_flags

                # Set the TASK_TWO bit as true in maintenance_status_flags to show it is complete for this voter
                voter_on_stage.maintenance_status_flags = \
                    voter_on_stage.maintenance_status_flags | MAINTENANCE_STATUS_FLAGS_TASK_TWO
                voter_on_stage.save()
                voters_updated_task_two += 1

    # Task 3
    if no_more_task2_voters_found:
        pass

    results = {
        'status':                   status,
        'success':                  success,
        'voters_updated_task_one':  voters_updated_task_one,
        'voters_updated_task_two':  voters_updated_task_two,
    }
    return results


def send_ballot_email(voter_device_id, sender_voter, send_now, sender_email_address,
                      sender_email_with_ownership_verified, one_normalized_raw_email, first_name, last_name,
                      invitation_message, ballot_link, web_app_root_url=''):
    # Starting with a raw email address, find (or create) the EmailAddress entry
    # and the owner (Voter) if exists
    status = ""
    real_name_only = True
    sender_name = sender_voter.get_full_name(real_name_only)
    sender_photo = sender_voter.voter_photo_url()
    sender_description = ""
    sender_network_details = ""
    email_manager = EmailManager()
    error_message_to_show_voter = ''
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

    # Variables used by templates/email_outbound/email_templates/friend_invitation.txt and .html
    subject = "Ballot from We Vote"
    if positive_value_exists(sender_email_with_ownership_verified):
        sender_email_address = sender_email_with_ownership_verified

    retrieve_results = retrieve_voter_and_email_address(one_normalized_raw_email)
    if not retrieve_results['success']:
        error_message_to_show_voter = "There was an error retrieving one of your friend's email addresses. " \
                                      "Please try again."
        results = {
            'success':                              False,
            'status':                               retrieve_results['status'],
            'voter_device_id':                      voter_device_id,
            'sender_voter_email_address_missing':   False,
            'error_message_to_show_voter':          error_message_to_show_voter
        }
        return results
    status += retrieve_results['status'] + " "

    recipient_email_address_object = retrieve_results['email_address_object']

    if positive_value_exists(recipient_email_address_object.subscription_secret_key):
        recipient_email_subscription_secret_key = recipient_email_address_object.subscription_secret_key
    else:
        recipient_email_subscription_secret_key = \
            email_manager.update_email_address_with_new_subscription_secret_key(
                email_we_vote_id=recipient_email_address_object.we_vote_id)

    # Store the friend invitation linked to voter (if the email address has had its ownership verified),
    # or to an email that isn't linked to a voter
    invitation_secret_key = ""
    if one_normalized_raw_email != sender_email_address:
        # If voter is sending ballot data to friends
        if retrieve_results['voter_found']:
            # Store the friend invitation in FriendInvitationVoterLink table
            voter_friend = retrieve_results['voter']
            existing_first_name = ''
            existing_last_name = ''
            try:
                existing_first_name = voter_friend.first_name
                existing_last_name = voter_friend.last_name
                voter_friend_found = True
            except AttributeError:
                voter_friend_found = False
            # See if voter_friend has a first_name and last_name already stored. If not, add the names used by friend.
            if positive_value_exists(voter_friend_found) \
                    and not positive_value_exists(existing_first_name) and \
                    not positive_value_exists(existing_last_name):
                # Save the voter_friend with new info
                voter_manager = VoterManager
                facebook_email = False
                facebook_profile_image_url_https = False
                middle_name = False
                update_voter_results = voter_manager.update_voter_by_object(
                        voter_friend, facebook_email, facebook_profile_image_url_https,
                        first_name, middle_name, last_name)
                if update_voter_results['voter_updated']:
                    voter_friend = update_voter_results['voter']

            friend_invitation_results = store_internal_friend_invitation_with_two_voters(
                sender_voter, invitation_message, voter_friend)
            status += friend_invitation_results['status'] + " "
            success = friend_invitation_results['success']
            if friend_invitation_results['friend_invitation_saved']:
                friend_invitation = friend_invitation_results['friend_invitation']
                invitation_secret_key = friend_invitation.secret_key
            sender_voter_we_vote_id = sender_voter.we_vote_id
            recipient_voter_we_vote_id = voter_friend.we_vote_id
            recipient_email_we_vote_id = recipient_email_address_object.we_vote_id
            recipient_voter_email = recipient_email_address_object.normalized_email_address

            # Template variables
            real_name_only = True
            recipient_name = voter_friend.get_full_name(real_name_only)
        else:
            # Store the friend invitation in FriendInvitationEmailLink table
            friend_invitation_results = store_internal_friend_invitation_with_unknown_email(
                voter=sender_voter,
                invitation_message=invitation_message,
                email_address_object=recipient_email_address_object,
                first_name=first_name,
                last_name=last_name)
            status += friend_invitation_results['status'] + " "
            success = friend_invitation_results['success']
            if friend_invitation_results['friend_invitation_saved']:
                friend_invitation = friend_invitation_results['friend_invitation']
                invitation_secret_key = friend_invitation.secret_key
            sender_voter_we_vote_id = sender_voter.we_vote_id
            recipient_voter_we_vote_id = ""
            recipient_email_we_vote_id = recipient_email_address_object.we_vote_id
            recipient_voter_email = recipient_email_address_object.normalized_email_address

            # Template variables
            recipient_name = ""

        # Check if recipient is already friend of sender
        friend_manager = FriendManager()
        already_friend_results = friend_manager.retrieve_current_friend(sender_voter_we_vote_id,
                                                                        recipient_voter_we_vote_id)
        # If recipient is not friend of sender then send two emails, friend invitation and ballot data
        if not already_friend_results['current_friend_found']:
            # Send friend invitation email before sending ballot link to friends
            if friend_invitation_results['friend_invitation_saved']:
                # Variables used by templates/email_outbound/email_templates/friend_invitation.txt and .html
                if positive_value_exists(sender_name):
                    subject = sender_name + " wants to be friends on We Vote"
                else:
                    subject = "Invitation to be friends on We Vote"
                friend_invitation_message = "Please join me in preparing for the upcoming election."

                # Unsubscribe link in email
                # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
                # recipient_email_subscription_secret_key,
                recipient_unsubscribe_url = \
                    "{root_url}/unsubscribe/{email_secret_key}/friendmessage" \
                    "".format(
                        email_secret_key=recipient_email_subscription_secret_key,
                        root_url=web_app_root_url_verified,
                    )
                # Instant unsubscribe link in email header
                list_unsubscribe_url = \
                    "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/friendmessage/" \
                    "".format(
                        email_secret_key=recipient_email_subscription_secret_key,
                        root_url=WE_VOTE_SERVER_ROOT_URL,
                    )
                # Instant unsubscribe email address in email header
                # from voter.models import NOTIFICATION_FRIEND_MESSAGES_EMAIL
                list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                                          "".format(setting='friendmessage')
                template_variables_for_json = {
                    "subject":                      subject,
                    "invitation_message":           friend_invitation_message,
                    "sender_name":                  sender_name,
                    "sender_photo":                 sender_photo,
                    "sender_email_address":         sender_email_address,  # Does not affect the "From" email header
                    "sender_description":           sender_description,
                    "sender_network_details":       sender_network_details,
                    "recipient_name":               recipient_name,
                    "recipient_unsubscribe_url":    recipient_unsubscribe_url,
                    "recipient_voter_email":        recipient_voter_email,
                    "see_all_friend_requests_url":  web_app_root_url_verified + "/friends",
                    "confirm_friend_request_url":   web_app_root_url_verified + "/more/network/key/" +
                    invitation_secret_key,
                }
                template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

                # TODO DALE - What kind of policy do we want re: sending a second email to a person?
                # Create the outbound email description, then schedule it
                kind_of_email_template = FRIEND_INVITATION_TEMPLATE
                outbound_results = email_manager.create_email_outbound_description(
                    sender_voter_we_vote_id=sender_voter_we_vote_id,
                    sender_voter_email=sender_email_address,
                    sender_voter_name=sender_name,
                    recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                    recipient_email_we_vote_id=recipient_email_we_vote_id,
                    recipient_voter_email=recipient_voter_email,
                    template_variables_in_json=template_variables_in_json,
                    kind_of_email_template=kind_of_email_template,
                    list_unsubscribe_mailto=list_unsubscribe_mailto,
                    list_unsubscribe_url=list_unsubscribe_url,
                )
                status += outbound_results['status'] + " "
                email_outbound_description = outbound_results['email_outbound_description']
                # If send_now is true then send email immediately else schedule email for later with
                # WAITING_FOR_VERIFICATION status
                if outbound_results['email_outbound_description_saved'] and send_now:
                    send_status = TO_BE_PROCESSED
                    schedule_results = schedule_email_with_email_outbound_description(email_outbound_description,
                                                                                      send_status)
                    status += schedule_results['status'] + " "
                    if schedule_results['email_scheduled_saved']:
                        # messages_to_send.append(schedule_results['email_scheduled_id'])
                        email_scheduled = schedule_results['email_scheduled']
                        send_results = email_manager.send_scheduled_email(email_scheduled)
                        email_scheduled_sent = send_results['email_scheduled_sent']
                        status += send_results['status']
                elif not send_now:
                    send_status = WAITING_FOR_VERIFICATION
                    schedule_results = schedule_email_with_email_outbound_description(email_outbound_description,
                                                                                      send_status)
                    status += schedule_results['status'] + " "

        # After sending friend invitation, send email about ballot data
        kind_of_email_template = SEND_BALLOT_TO_FRIENDS
        if positive_value_exists(sender_name):
            subject = sender_name + " sent Ballot from We Vote"
        else:
            subject = "Ballot from We Vote"
    else:
        # sending ballot email to herself/himself
        kind_of_email_template = SEND_BALLOT_TO_SELF
        invitation_secret_key = ""
        sender_voter_we_vote_id = sender_voter.we_vote_id
        recipient_voter_we_vote_id = ""
        recipient_email_we_vote_id = recipient_email_address_object.we_vote_id
        recipient_voter_email = recipient_email_address_object.normalized_email_address

        # Template variables
        recipient_name = ""
        success = True

    # Unsubscribe link in email
    # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
    # recipient_email_subscription_secret_key,
    recipient_unsubscribe_url = \
        "{root_url}/unsubscribe/{email_secret_key}/friendmessage" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=web_app_root_url_verified,
        )
    # Instant unsubscribe link in email header
    list_unsubscribe_url = \
        "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/friendmessage/" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=WE_VOTE_SERVER_ROOT_URL,
        )
    # Instant unsubscribe email address in email header
    # from voter.models import NOTIFICATION_FRIEND_MESSAGES_EMAIL
    list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                              "".format(setting='friendmessage')

    template_variables_for_json = {
        "subject":                      subject,
        "invitation_message":           invitation_message,
        "ballot_link":                  ballot_link,
        "sender_name":                  sender_name,
        "sender_photo":                 sender_photo,
        "sender_email_address":         sender_email_address,  # Does not affect the "From" email header
        "sender_description":           sender_description,
        "sender_network_details":       sender_network_details,
        "recipient_name":               recipient_name,
        "recipient_unsubscribe_url":    recipient_unsubscribe_url,
        "recipient_voter_email":        recipient_voter_email,
        "see_all_friend_requests_url":  web_app_root_url_verified + "/friends",
        "confirm_friend_request_url":   web_app_root_url_verified + "/more/network/key/" + invitation_secret_key,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)

    # TODO DALE - What kind of policy do we want re: sending a second email to a person?
    # Create the outbound email description, then schedule it
    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=sender_voter_we_vote_id,
        sender_voter_email=sender_email_address,
        sender_voter_name=sender_name,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_voter_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        list_unsubscribe_mailto=list_unsubscribe_mailto,
        list_unsubscribe_url=list_unsubscribe_url,
    )
    status += outbound_results['status'] + " "
    email_outbound_description = outbound_results['email_outbound_description']
    if outbound_results['email_outbound_description_saved']:
        # If send_now is true then send email immediately else schedule email for later with
        # WAITING_FOR_VERIFICATION status
        if send_now or kind_of_email_template == SEND_BALLOT_TO_SELF:
            send_status = TO_BE_PROCESSED
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description, send_status)
            status += schedule_results['status'] + " "
            if schedule_results['email_scheduled_saved']:
                # messages_to_send.append(schedule_results['email_scheduled_id'])
                email_scheduled = schedule_results['email_scheduled']
                send_results = email_manager.send_scheduled_email(email_scheduled)
                email_scheduled_sent = send_results['email_scheduled_sent']
                status += send_results['status']
        elif not send_now:
            send_status = WAITING_FOR_VERIFICATION
            schedule_results = schedule_email_with_email_outbound_description(email_outbound_description, send_status)
            status += schedule_results['status'] + " "

    results = {
        'success':                              success,
        'status':                               status,
        'voter_device_id':                      voter_device_id,
        'sender_voter_email_address_missing':   False,
        'error_message_to_show_voter':          error_message_to_show_voter
    }
    return results


# We are going to start retrieving only the ballot address
# Eventually we will want to allow saving former addresses, and mailing addresses for overseas voters
def voter_address_retrieve_for_api(voter_device_id):  # voterAddressRetrieve
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        voter_address_retrieve_results = {
            'status': results['status'],
            'success': False,
            'address_found': False,
            'voter_device_id': voter_device_id,
        }
        return voter_address_retrieve_results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        voter_address_retrieve_results = {
            'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'address_found': False,
            'voter_device_id': voter_device_id,
        }
        return voter_address_retrieve_results
    return voter_address_retrieve_for_voter_id(voter_id, voter_device_id)


def voter_address_retrieve_for_voter_id(voter_id, voter_device_id=''):
    voter_address_manager = VoterAddressManager()
    results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
    success = results['success']

    if results['voter_address_found']:
        voter_address = results['voter_address']
        status = "VOTER_ADDRESS_RETRIEVE-ADDRESS_FOUND"

        voter_address_retrieve_results = {
            'voter_device_id': voter_device_id,
            'address_type': voter_address.address_type if voter_address.address_type else '',
            'text_for_map_search': voter_address.text_for_map_search if voter_address.text_for_map_search else '',
            'google_civic_election_id': voter_address.google_civic_election_id if voter_address.google_civic_election_id
            else 0,
            'ballot_location_display_name': voter_address.ballot_location_display_name if
            voter_address.ballot_location_display_name else '',
            'ballot_returned_we_vote_id': voter_address.ballot_returned_we_vote_id if
            voter_address.ballot_returned_we_vote_id else '',
            'latitude': voter_address.latitude if voter_address.latitude else '',
            'longitude': voter_address.longitude if voter_address.longitude else '',
            'normalized_line1': voter_address.normalized_line1 if voter_address.normalized_line1 else '',
            'normalized_line2': voter_address.normalized_line2 if voter_address.normalized_line2 else '',
            'normalized_city': voter_address.normalized_city if voter_address.normalized_city else '',
            'normalized_state': voter_address.normalized_state if voter_address.normalized_state else '',
            'normalized_zip': voter_address.normalized_zip if voter_address.normalized_zip else '',
            'voter_entered_address': voter_address.voter_entered_address,
            'voter_specific_ballot_from_google_civic': voter_address.refreshed_from_google,
            'address_found': True,
            'success': success,
            'status': status,
        }
        return voter_address_retrieve_results
    else:
        voter_address_retrieve_results = {
            'status': "VOTER_ADDRESS_NOT_FOUND",
            'success': success,
            'address_found': False,
            'voter_device_id': voter_device_id,
            'address_type': '',
            'text_for_map_search': '',
            'google_civic_election_id': 0,
            'ballot_returned_we_vote_id': '',
            'latitude': '',
            'longitude': '',
            'normalized_line1': '',
            'normalized_line2': '',
            'normalized_city': '',
            'normalized_state': '',
            'normalized_zip': '',
            'voter_entered_address': False,
            'voter_specific_ballot_from_google_civic': False,
        }
        return voter_address_retrieve_results


def voter_create_for_api(voter_device_id):  # voterCreate
    # If a voter_device_id isn't passed in, automatically create a new voter_device_id
    if not positive_value_exists(voter_device_id):
        voter_device_id = generate_voter_device_id()
    else:
        # If a voter_device_id is passed in that isn't valid, we want to throw an error
        results = is_voter_device_id_valid(voter_device_id)
        if not results['success']:
            return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = 0
    voter_we_vote_id = ''
    # Make sure a voter record hasn't already been created for this
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
        json_data = {
            'status': "VOTER_ALREADY_EXISTS",
            'success': True,
            'voter_device_id': voter_device_id,
            'voter_id':         voter_id,
            'voter_we_vote_id': voter_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Create a new voter and return the voter_device_id
    voter_manager = VoterManager()
    results = voter_manager.create_voter()

    if results['voter_created']:
        voter = results['voter']

        # Now save the voter_device_link
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.save_new_voter_device_link(voter_device_id, voter.id)

        if results['voter_device_link_created']:
            voter_device_link = results['voter_device_link']
            voter_id_found = True if voter_device_link.voter_id > 0 else False

            if voter_id_found:
                voter_id = voter.id
                voter_we_vote_id = voter.we_vote_id

    if voter_id:
        json_data = {
            'status':           "VOTER_CREATED",
            'success':          True,
            'voter_device_id':  voter_device_id,
            'voter_id':         voter_id,
            'voter_we_vote_id': voter_we_vote_id,

        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':           "VOTER_NOT_CREATED",
            'success':          False,
            'voter_device_id':  voter_device_id,
            'voter_id':         0,
            'voter_we_vote_id': '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_cache_facebook_images_process(voter_id, facebook_auth_response_id, is_retrieve):
    # Invoked from an SQS queue message (job) when voter signs in "for the first time" on a device, ie there is no
    # Facebook tab that is already signed in, or cookies/local storage/session storage that are equiv. to a sign in
    # It is also called with is_retrieve True when a redirect is not needed to sign in via Facebook
    # Cache original and resized images

    t0 = time()
    status = ""
    # print("process started")
    facebook_manager = FacebookManager()
    facebook_auth_response = facebook_manager.retrieve_facebook_auth_response_by_id(facebook_auth_response_id)
    voter = Voter.objects.get(id=voter_id)  # This voter existed immediately before the call -- so this is safe
    voter.last_login = now()                # TODO: 1/12/2023, We should do this for the other sign in methods too
    # voter.profile_image_type_currently_active = "FACEBOOK"  # This is handled in save_facebook_user_values
    voter.save()

    # print('^^^ voter_cache_facebook_images_process BEFORE in process', os.getpid())

    initial_cache_results = cache_image_locally(
        image_url_https=facebook_auth_response.facebook_profile_image_url_https,
        is_active_version=True,
        kind_of_image_facebook_profile=True,
        voter_we_vote_id=voter.we_vote_id)
    try:
        image_url_https = initial_cache_results['image_url_https']
    except Exception as e:
        status += "FACEBOOK_IMAGE_URL_NOT_RETURNED: " + str(e) + " " + str(initial_cache_results) + " "
        image_url_https = ''

    if not positive_value_exists(image_url_https):
        status += "VOTER_CACHE_FACEBOOK_IMAGES_PROCESS_NO_URL "
        logger.error(status)
        return {
            'we_vote_hosted_profile_image_url_large': '',
            'we_vote_hosted_profile_image_url_medium': '',
            'we_vote_hosted_profile_image_url_tiny': '',
        }

    we_vote_image_manager = WeVoteImageManager()
    set_active_results = we_vote_image_manager.set_active_version_false_for_other_images(
        kind_of_image_facebook_profile=True,
        image_url_https=image_url_https,
        voter_we_vote_id=voter.we_vote_id)

    create_resized_image_results = create_resized_images(
        voter_we_vote_id=voter.we_vote_id,
        facebook_profile_image_url_https=image_url_https,
        we_vote_image_url=image_url_https,
    )

    #  Get the latest Facebook images from the wevoteimage table
    we_vote_image_manager = WeVoteImageManager()
    latest_image_results = we_vote_image_manager.retrieve_latest_facebook_images_for_voter(
        voter.we_vote_id, facebook_auth_response.facebook_profile_image_url_https)
    cached_facebook_profile_image_url_https = latest_image_results['cached_facebook_profile_image_url_https']
    we_vote_hosted_profile_image_url_large = latest_image_results['we_vote_hosted_profile_image_url_large']
    we_vote_hosted_profile_image_url_medium = latest_image_results['we_vote_hosted_profile_image_url_medium']
    we_vote_hosted_profile_image_url_tiny = latest_image_results['we_vote_hosted_profile_image_url_tiny']

    # Update the facebook photos in the Voter record
    voter_manager = VoterManager()
    voter_manager.save_facebook_user_values(
        voter,
        facebook_auth_response,
        cached_facebook_profile_image_url_https=cached_facebook_profile_image_url_https,
        we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
    dtc = time() - t0
    # 12/20/22: This takes 1.2 seconds on my local postgres, but 5 to 15 seconds in production,
    # leave this logger active for a few months, so we can gather data
    method = "(For a new Facebook sign in)" if is_retrieve else "(Facebook sign in without redirect)"

    logger.error(
        '(Ok) SQS Processing the facebook images for voter %s %s %s (%s) took %.3f seconds' %
        (method, voter.first_name, voter.last_name, voter.we_vote_id, dtc))
    return {
        'we_vote_hosted_profile_image_url_large': we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium': we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny': we_vote_hosted_profile_image_url_tiny,
    }


def voter_merge_two_accounts_for_facebook(facebook_secret_key, facebook_user_id, from_voter, voter_device_id,
                                          current_voter_found, status):
    voter_manager = VoterManager()
    facebook_owner_voter_found = False
    facebook_owner_voter = {'id': 0}
    facebook_manager = FacebookManager()
    merge_from_voter_we_vote_id = ''
    merge_to_voter_we_vote_id = ''

    if positive_value_exists(facebook_secret_key):
        status += "FACEBOOK_SECRET_KEY "
        facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_facebook_secret_key(
            facebook_secret_key, read_only=True)
        if facebook_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_results['facebook_link_to_voter']

            facebook_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                facebook_link_to_voter.voter_we_vote_id)
            if facebook_owner_voter_results['voter_found']:
                facebook_owner_voter_found = True
                facebook_owner_voter = facebook_owner_voter_results['voter']
    elif positive_value_exists(facebook_user_id):
        status += "FACEBOOK_USER_ID "
        facebook_owner_voter_results = voter_manager.retrieve_voter_by_facebook_id(facebook_user_id)   # The "to" voter
        if facebook_owner_voter_results['voter_found']:
            facebook_owner_voter_found = True
            facebook_owner_voter = facebook_owner_voter_results['voter']

    if not facebook_owner_voter_found:
        error_results = {
            'status': "FACEBOOK_OWNER_VOTER_NOT_FOUND",
            'success': False,
            'voter_device_id': voter_device_id,
            'current_voter_found': current_voter_found,
            'email_owner_voter_found': False,
            'facebook_owner_voter_found': facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
            'merge_from_voter_we_vote_id': merge_from_voter_we_vote_id,
            'merge_to_voter_we_vote_id': merge_to_voter_we_vote_id,
        }
        return None, None, error_results

    facebook_auth_response = None
    auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    if auth_response_results['facebook_auth_response_found']:
        facebook_auth_response = auth_response_results['facebook_auth_response']

    # Double-check they aren't the same voter account
    if from_voter.id == facebook_owner_voter.id and facebook_auth_response:
        # If here, we probably have some bad data and need to update the voter record to reflect that
        #  it is signed in with Facebook
        if auth_response_results['facebook_auth_response_found']:
            # Get the recent facebook_user_id and facebook_email
            voter_manager.update_voter_with_facebook_link_verified(
                facebook_owner_voter,
                facebook_auth_response.facebook_user_id, facebook_auth_response.facebook_email)

        else:
            error_results = {
                'status': "CURRENT_VOTER_AND_EMAIL_OWNER_VOTER_ARE_SAME",
                'success': True,
                'voter_device_id': voter_device_id,
                'current_voter_found': current_voter_found,
                'email_owner_voter_found': False,
                'facebook_owner_voter_found': facebook_owner_voter_found,
                'invitation_owner_voter_found': False,
                'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
                'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
            }
            return None, None, error_results

    # Cache original and resized images in a SQS message (job)
    process_in_sqs_job = True  # Switch to 'False' to test locally without an SQS job
    if process_in_sqs_job:
        submit_web_function_job('voter_cache_facebook_images_process', {
                        'voter_id': facebook_owner_voter.id,
                        'facebook_auth_response_id': facebook_auth_response.id,
                        'is_retrieve': False,
                    })
    else:
        voter_cache_facebook_images_process(facebook_owner_voter.id, facebook_auth_response.id, False)

    status += " FACEBOOK_IMAGES_SCHEDULED_TO_BE_CACHED_VIA_SQS"

    # ##### Store the facebook_email as a verified email for facebook_owner_voter
    if positive_value_exists(facebook_auth_response.facebook_email):
        # Check to make sure there isn't an account already using the facebook_email
        facebook_email_address_verified = False
        temp_voter_we_vote_id = ""
        email_manager = EmailManager()
        email_results = email_manager.retrieve_primary_email_with_ownership_verified(
            temp_voter_we_vote_id, facebook_auth_response.facebook_email)
        if email_results['email_address_object_found']:
            # If here, then it turns out the facebook_email is verified, and we can
            #   update_voter_email_ownership_verified if a verified email is already stored in the voter record
            email_address_object = email_results['email_address_object']
            facebook_email_address_verified = True
        else:
            # See if an unverified email exists for this voter
            email_address_object = None
            email_address_object_we_vote_id = ""
            email_retrieve_results = email_manager.retrieve_email_address_object(
                facebook_auth_response.facebook_email, email_address_object_we_vote_id,
                facebook_owner_voter.we_vote_id)
            if email_retrieve_results['email_address_object_found']:
                email_address_object = email_retrieve_results['email_address_object']
                email_address_object = email_manager.update_email_address_object_as_verified(
                    email_address_object)
                facebook_email_address_verified = True
            else:
                email_ownership_is_verified = True
                email_create_results = email_manager.create_email_address(
                    facebook_auth_response.facebook_email, facebook_owner_voter.we_vote_id,
                    email_ownership_is_verified)
                if email_create_results['email_address_object_saved']:
                    email_address_object = email_create_results['email_address_object']
                    facebook_email_address_verified = True

        # Does facebook_owner_voter already have a primary email? If not, update it
        if not facebook_owner_voter.email_ownership_is_verified and facebook_email_address_verified:
            try:
                # Attach the email_address_object to facebook_owner_voter
                voter_manager.update_voter_email_ownership_verified(facebook_owner_voter,
                                                                    email_address_object)
            except Exception as e:
                status += "UNABLE_TO_MAKE_FACEBOOK_EMAIL_THE_PRIMARY " + str(e) + " "

    # Now we have voter (from voter_device_id) and email_owner_voter (from facebook_secret_key)
    # We are going to make the email_owner_voter the new master
    to_voter_we_vote_id = facebook_owner_voter.we_vote_id     # No need to return to_voter_we_vote_id from this func
    new_owner_voter = facebook_owner_voter
    status += "TO_VOTER-" + str(to_voter_we_vote_id) + " "
    return status, new_owner_voter, None


def voter_merge_two_accounts_for_api(  # voterMergeTwoAccounts
        voter_device_id='',
        email_secret_key='',
        facebook_secret_key='',
        twitter_secret_key='',
        invitation_secret_key='',
        web_app_root_url='',
        do_not_merge_if_currently_signed_in=False):
    current_voter_found = False
    email_owner_voter_found = False
    facebook_owner_voter_found = False
    twitter_owner_voter_found = False
    invitation_owner_voter_found = False
    merge_from_voter_we_vote_id = ''
    merge_to_voter_we_vote_id = ''
    new_owner_voter = None
    success = False
    status = ""

    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        error_results = {
            'status':                       voter_device_link_results['status'],
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'current_voter_found':          current_voter_found,
            'email_owner_voter_found':      email_owner_voter_found,
            'facebook_owner_voter_found':   facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
            'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
            'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
        }
        return error_results

    # We need this below
    voter_device_link = voter_device_link_results['voter_device_link']

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                       "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'current_voter_found':          current_voter_found,
            'email_owner_voter_found':      email_owner_voter_found,
            'facebook_owner_voter_found':   facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
            'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
            'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
        }
        return error_results

    voter = voter_results['voter']
    status += "VOTER_MERGE_FROM-" + str(voter.we_vote_id) + "-TO... "
    current_voter_found = True

    if not positive_value_exists(email_secret_key) \
            and not positive_value_exists(facebook_secret_key) \
            and not positive_value_exists(twitter_secret_key) \
            and not positive_value_exists(invitation_secret_key):
        status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS_SECRET_KEY_NOT_PASSED_IN "
        error_results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'current_voter_found':          current_voter_found,
            'email_owner_voter_found':      email_owner_voter_found,
            'facebook_owner_voter_found':   facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
            'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
            'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
        }
        return error_results

    if do_not_merge_if_currently_signed_in and voter.is_signed_in():
        status += "VOTER_MERGE_STOPPED-ALREADY_SIGNED_IN "
        error_results = {
            'status': status,
            'success': True,
            'voter_device_id': voter_device_id,
            'current_voter_found': current_voter_found,
            'email_owner_voter_found': email_owner_voter_found,
            'facebook_owner_voter_found': facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
            'merge_from_voter_we_vote_id': merge_from_voter_we_vote_id,
            'merge_to_voter_we_vote_id': merge_to_voter_we_vote_id,
        }
        return error_results

    email_manager = EmailManager()
    friend_manager = FriendManager()
    organization_manager = OrganizationManager()

    # ############# EMAIL SIGN IN #####################################
    if positive_value_exists(email_secret_key):
        status += "EMAIL_SECRET_KEY "
        email_owner_voter = None
        email_results = email_manager.retrieve_email_address_object_from_secret_key(email_secret_key=email_secret_key)
        success = email_results['success']
        if email_results['email_address_object_found']:
            email_address_object = email_results['email_address_object']
            if positive_value_exists(email_address_object.voter_we_vote_id):
                email_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                    email_address_object.voter_we_vote_id)
                if email_owner_voter_results['voter_found']:
                    email_owner_voter_found = True
                    email_owner_voter = email_owner_voter_results['voter']
                    # TODO Pull the first/last name out of FriendInvitationEmailLink

        if not email_owner_voter_found or not success:
            error_results = {
                'status':                       "VOTER_MERGE_EMAIL_OWNER_VOTER_NOT_FOUND",
                'success':                      success,
                'voter_device_id':              voter_device_id,
                'current_voter_found':          current_voter_found,
                'email_owner_voter_found':      email_owner_voter_found,
                'facebook_owner_voter_found':   False,
                'invitation_owner_voter_found': False,
                'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
                'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
            }
            return error_results

        # Double-check they aren't the same voter account
        if voter.id == email_owner_voter.id:
            error_results = {
                'status':                       "CURRENT_VOTER_AND_EMAIL_OWNER_VOTER_ARE_SAME",
                'success':                      True,
                'voter_device_id':              voter_device_id,
                'current_voter_found':          current_voter_found,
                'email_owner_voter_found':      email_owner_voter_found,
                'facebook_owner_voter_found':   False,
                'invitation_owner_voter_found': False,
                'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
                'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
            }
            return error_results

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        to_voter_we_vote_id = email_owner_voter.we_vote_id
        new_owner_voter = email_owner_voter
        status += "TO_VOTER-" + str(to_voter_we_vote_id) + " "

    # ############# FACEBOOK SIGN IN #####################################
    elif positive_value_exists(facebook_secret_key):
        facebook_user_id = None
        status, new_owner_voter, error_results = voter_merge_two_accounts_for_facebook(
            facebook_secret_key, facebook_user_id, voter, voter_device_id, current_voter_found, status)
        if error_results:
            return error_results

    # ############# TWITTER SIGN IN #####################################
    elif positive_value_exists(twitter_secret_key):
        status += "TWITTER_SECRET_KEY "
        twitter_user_manager = TwitterUserManager()
        twitter_link_to_voter = TwitterLinkToVoter()
        twitter_owner_voter = None

        twitter_link_to_organization = TwitterLinkToOrganization()
        repair_twitter_related_organization_caching_now = False

        twitter_user_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_twitter_secret_key(
            twitter_secret_key)
        if twitter_user_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_user_results['twitter_link_to_voter']

            twitter_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                twitter_link_to_voter.voter_we_vote_id)
            if twitter_owner_voter_results['voter_found']:
                twitter_owner_voter_found = True
                twitter_owner_voter = twitter_owner_voter_results['voter']
                # And make sure we don't have multiple voters using same twitter_id (since we have TwitterLinkToVoter)
                repair_results = voter_manager.repair_twitter_related_voter_caching(
                    twitter_link_to_voter.twitter_id)
                status += repair_results['status']

        if not twitter_owner_voter_found:
            # Since we are in the "voterMergeTwoAccounts" we don't want to try to create
            #  another TwitterLinkToVoter entry
            error_results = {
                'status': "TWITTER_OWNER_VOTER_NOT_FOUND",
                'success': False,
                'voter_device_id': voter_device_id,
                'current_voter_found': current_voter_found,
                'email_owner_voter_found': False,
                'facebook_owner_voter_found': False,
                'twitter_owner_voter_found': twitter_owner_voter_found,
                'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
                'merge_to_voter_we_vote_id':    merge_to_voter_we_vote_id,
            }
            return error_results

        twitter_auth_manager = TwitterAuthManager()
        auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
        twitter_auth_response = None
        if auth_response_results['twitter_auth_response_found']:
            twitter_auth_response = auth_response_results['twitter_auth_response']

        # Double-check they aren't the same voter account
        if twitter_owner_voter and twitter_auth_response and voter.id == twitter_owner_voter.id:
            # If here, we probably have some bad data and need to update the voter record to reflect that
            #  it is signed in with Twitter
            if auth_response_results['twitter_auth_response_found']:
                # Save the Twitter Id in the voter record
                voter_manager.update_voter_with_twitter_link_verified(
                    twitter_owner_voter,
                    twitter_auth_response.twitter_id)
                # TODO DALE Remove voter.twitter_id value
            else:
                error_results = {
                    'status': "CURRENT_VOTER_AND_TWITTER_OWNER_VOTER_ARE_SAME",
                    'success': True,
                    'voter_device_id': voter_device_id,
                    'current_voter_found': current_voter_found,
                    'email_owner_voter_found': False,
                    'facebook_owner_voter_found': False,
                    'twitter_owner_voter_found': twitter_owner_voter_found,
                    'merge_from_voter_we_vote_id': merge_from_voter_we_vote_id,
                    'merge_to_voter_we_vote_id': merge_to_voter_we_vote_id,
                }
                return error_results

        # Make sure we have a twitter_link_to_organization entry for the destination voter
        if positive_value_exists(twitter_owner_voter.linked_organization_we_vote_id):
            twitter_link_to_organization_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
                    twitter_owner_voter.linked_organization_we_vote_id)
            # Do we have an existing organization linked to this twitter_id?
            if twitter_link_to_organization_results['twitter_link_to_organization_found']:
                twitter_link_to_organization = twitter_link_to_organization_results['twitter_link_to_organization']
                # Make sure the twitter_id in twitter_link_to_voter matches the one in twitter_link_to_organization
                if twitter_link_to_voter.twitter_id == twitter_link_to_organization.twitter_id:
                    # We are happy
                    repair_twitter_related_organization_caching_now = True
                else:
                    # We are here, so we know that we found a twitter_link_to_organization, but it doesn't match
                    # the org linked to this voter. So we want to merge these two organizations.
                    # Since linked_organization_we_vote_id must be unique, and this organization came from
                    #  that value, we don't have to look to see if any other voters "claim" this organization.
                    # Merge twitter_owner_voter.linked_organization_we_vote_id
                    #  with twitter_link_to_organization.organization_we_vote_id
                    # MERGE Positions
                    if positive_value_exists(twitter_owner_voter.linked_organization_we_vote_id) and \
                            positive_value_exists(twitter_link_to_organization.organization_we_vote_id) and \
                            twitter_owner_voter.linked_organization_we_vote_id != \
                            twitter_link_to_organization.organization_we_vote_id:
                        twitter_link_to_organization_organization_id = 0  # We calculate this in move_organization...
                        twitter_owner_voter_linked_organization_id = 0  # We calculate this in move_organization...
                        move_organization_to_another_complete_results = move_organization_to_another_complete(
                            twitter_owner_voter_linked_organization_id,
                            twitter_owner_voter.linked_organization_we_vote_id,
                            twitter_link_to_organization_organization_id,
                            twitter_link_to_organization.organization_we_vote_id,
                            twitter_owner_voter.id, twitter_owner_voter.we_vote_id
                        )
                        status += " " + move_organization_to_another_complete_results['status']
                        if move_organization_to_another_complete_results['success']:
                            try:
                                twitter_owner_voter.linked_organization_we_vote_id = \
                                    twitter_link_to_organization.organization_we_vote_id
                                twitter_owner_voter.save()
                                repair_twitter_related_organization_caching_now = True
                            except Exception as e:
                                status += "UNABLE_TO_UPDATE_LINKED_ORGANIZATION_WE_VOTE_ID " + str(e) + " "
            else:
                # If we don't have an organization linked to this twitter_id...
                # Check to see if there is a LinkToOrganization entry that matches this twitter_id
                twitter_link_to_organization_results = \
                    twitter_user_manager.retrieve_twitter_link_to_organization(twitter_link_to_voter.twitter_id)
                # Do we have an existing organization linked to this twitter_id?
                if twitter_link_to_organization_results['twitter_link_to_organization_found']:
                    twitter_link_to_organization = twitter_link_to_organization_results['twitter_link_to_organization']
                    # Because we are here, we know that the twitter_owner_voter.linked_organization_we_vote_id
                    # doesn't have a TwitterLinkToOrganization entry that matched the organization_we_vote_id.
                    # But we did find another organization linked to that Twitter id, so we need to merge
                    # Merge twitter_owner_voter.linked_organization_we_vote_id
                    #  with twitter_link_to_organization.organization_we_vote_id
                    #  and make sure twitter_owner_voter.linked_organization_we_vote_id is correct at the end
                    # MERGE Positions
                    if positive_value_exists(twitter_owner_voter.linked_organization_we_vote_id) and \
                            positive_value_exists(twitter_link_to_organization.organization_we_vote_id) and \
                            twitter_owner_voter.linked_organization_we_vote_id != \
                            twitter_link_to_organization.organization_we_vote_id:
                        twitter_link_to_organization_organization_id = 0  # We calculate this in move_organization...
                        twitter_owner_voter_linked_organization_id = 0  # We calculate this in move_organization...
                        move_organization_to_another_complete_results = move_organization_to_another_complete(
                            twitter_owner_voter_linked_organization_id,
                            twitter_owner_voter.linked_organization_we_vote_id,
                            twitter_link_to_organization_organization_id,
                            twitter_link_to_organization.organization_we_vote_id,
                            twitter_owner_voter.id, twitter_owner_voter.we_vote_id
                        )
                        status += " " + move_organization_to_another_complete_results['status']
                        if move_organization_to_another_complete_results['success']:
                            try:
                                twitter_owner_voter.linked_organization_we_vote_id = \
                                    twitter_link_to_organization.organization_we_vote_id
                                twitter_owner_voter.save()
                                repair_twitter_related_organization_caching_now = True
                            except Exception as e:
                                status += "UNABLE_TO_UPDATE_LINKED_ORGANIZATION_WE_VOTE_ID " + str(e) + " "
                else:
                    # Create TwitterLinkToOrganization and for the org
                    # in twitter_owner_voter.linked_organization_we_vote_id
                    results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_link_to_voter.twitter_id, twitter_owner_voter.linked_organization_we_vote_id)
                    if results['twitter_link_to_organization_saved']:
                        repair_twitter_related_organization_caching_now = True
                        status += "TwitterLinkToOrganization_CREATED "
                    else:
                        status += "TwitterLinkToOrganization_NOT_CREATED "
        else:
            # In this branch, no need to merge organizations
            # Check to see if TwitterLinkToOrganization entry exists that matches this twitter_id
            twitter_link_to_organization_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization(twitter_link_to_voter.twitter_id)
            # Do we have an existing organization linked to this twitter_id?
            if twitter_link_to_organization_results['twitter_link_to_organization_found']:
                twitter_link_to_organization = twitter_link_to_organization_results['twitter_link_to_organization']
                try:
                    twitter_owner_voter.linked_organization_we_vote_id = \
                        twitter_link_to_organization.organization_we_vote_id
                    twitter_owner_voter.save()
                    repair_twitter_related_organization_caching_now = True
                except Exception as e:
                    status += "UNABLE_TO_TWITTER_LINK_ORGANIZATION_TO_VOTER " + str(e) + " "
            else:
                # Create new organization
                create_results = organization_manager.create_organization(
                    organization_name=twitter_owner_voter.get_full_name(),
                    organization_image=twitter_owner_voter.voter_photo_url(),
                    organization_type=INDIVIDUAL,
                )
                if create_results['organization_created']:
                    # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                    organization = create_results['organization']
                    try:
                        twitter_owner_voter.linked_organization_we_vote_id = organization.we_vote_id
                        twitter_owner_voter.save()
                        # Create TwitterLinkToOrganization
                        results = twitter_user_manager.create_twitter_link_to_organization(
                            twitter_link_to_voter.twitter_id, twitter_owner_voter.linked_organization_we_vote_id)
                        if results['twitter_link_to_organization_saved']:
                            repair_twitter_related_organization_caching_now = True
                            status += "TwitterLinkToOrganization_CREATED_AFTER_ORGANIZATION_CREATE "
                        else:
                            status += "TwitterLinkToOrganization_NOT_CREATED_AFTER_ORGANIZATION_CREATE "
                    except Exception as e:
                        status += "UNABLE_TO_LINK_NEW_ORGANIZATION_TO_VOTER: " + str(e) + " "

        # Make sure we end up with the organization referred to in twitter_link_to_organization ends up as
        # voter.linked_organization_we_vote_id

        if repair_twitter_related_organization_caching_now:
            organization_list_manager = OrganizationListManager()
            repair_results = organization_list_manager.repair_twitter_related_organization_caching(
                twitter_link_to_organization.twitter_id)
            status += repair_results['status']

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        to_voter_we_vote_id = twitter_owner_voter.we_vote_id
        new_owner_voter = twitter_owner_voter
        status += "TO_VOTER-" + str(to_voter_we_vote_id) + " "

    # ############# INVITATION SIGN IN #####################################
    elif positive_value_exists(invitation_secret_key):
        status += "INVITATION_SECRET_KEY "
        invitation_owner_voter = Voter()
        recipient_voter_we_vote_id = ""
        sender_voter_we_vote_id = ""
        friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(
            invitation_secret_key, for_merge_accounts=True)
        if friend_invitation_results['friend_invitation_found']:
            if friend_invitation_results['friend_invitation_voter_link_found']:
                friend_invitation = friend_invitation_results['friend_invitation_voter_link']
                recipient_voter_we_vote_id = fetch_friend_invitation_recipient_voter_we_vote_id(friend_invitation)
                sender_voter_we_vote_id = friend_invitation.sender_voter_we_vote_id
            elif friend_invitation_results['friend_invitation_email_link_found']:
                friend_invitation = friend_invitation_results['friend_invitation_email_link']
                recipient_voter_we_vote_id = fetch_friend_invitation_recipient_voter_we_vote_id(friend_invitation)
                sender_voter_we_vote_id = friend_invitation.sender_voter_we_vote_id

            invitation_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(recipient_voter_we_vote_id)
            if invitation_owner_voter_results['voter_found']:
                invitation_owner_voter_found = True
                invitation_owner_voter = invitation_owner_voter_results['voter']

        if not invitation_owner_voter_found:
            error_results = {
                'status':                       "INVITATION_OWNER_VOTER_NOT_FOUND",
                'success':                      False,
                'voter_device_id':              voter_device_id,
                'current_voter_found':          current_voter_found,
                'email_owner_voter_found':      False,
                'facebook_owner_voter_found':   False,
                'invitation_owner_voter_found': invitation_owner_voter_found,
            }
            return error_results

        # Double-check they aren't the same voter account
        if voter.id == invitation_owner_voter.id:
            error_results = {
                'status':                       "CURRENT_VOTER_AND_INVITATION_OWNER_VOTER_ARE_SAME",
                'success':                      True,
                'voter_device_id':              voter_device_id,
                'current_voter_found':          current_voter_found,
                'email_owner_voter_found':      False,
                'facebook_owner_voter_found':   False,
                'invitation_owner_voter_found': invitation_owner_voter_found,
            }
            return error_results

        # We want to send an email letting the original inviter know that the person accepted
        accepting_voter_we_vote_id = invitation_owner_voter.we_vote_id
        original_sender_we_vote_id = sender_voter_we_vote_id
        results = friend_accepted_invitation_send(accepting_voter_we_vote_id, original_sender_we_vote_id,
                                                  web_app_root_url=web_app_root_url)
        status += results['status']

        # Now we have voter (from voter_device_id) and invitation_owner_voter (from invitation_secret_key)
        # We are going to make the email_owner_voter the new master
        to_voter_we_vote_id = invitation_owner_voter.we_vote_id
        new_owner_voter = invitation_owner_voter
        status += "TO_VOTER-" + str(to_voter_we_vote_id) + " "

    results = voter_merge_two_accounts_action_schedule(
        from_voter=voter,
        to_voter=new_owner_voter,
        voter_device_link=voter_device_link)
    status += results['status']
    if not results['success']:
        success = False
    merge_from_voter_we_vote_id = ''
    merge_to_voter_we_vote_id = ''
    try:
        merge_from_voter_we_vote_id = voter.we_vote_id
    except Exception as e:
        status += "COULD_NOT_RETURN_MERGE_FROM_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False
    try:
        merge_to_voter_we_vote_id = new_owner_voter.we_vote_id
    except Exception as e:
        status += "COULD_NOT_RETURN_MERGE_TO_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False
    # Now update the friend invitation entry -- we only want to allow a voter merge once per invitation
    if positive_value_exists(invitation_secret_key):
        status += "INVITATION_SECRET_KEY "
        friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(
            invitation_secret_key, for_merge_accounts=True, read_only=False)
        if friend_invitation_results['friend_invitation_found']:
            try:
                if friend_invitation_results['friend_invitation_voter_link_found']:
                    friend_invitation_voter_link = friend_invitation_results['friend_invitation_voter_link']
                    friend_invitation_voter_link.merge_by_secret_key_allowed = False
                    friend_invitation_voter_link.save()
                    status += "VOTER_LINK-MERGE_BY_SECRET_KEY_ALLOWED-SET_TO_FALSE "
                elif friend_invitation_results['friend_invitation_email_link_found']:
                    friend_invitation_email_link = friend_invitation_results['friend_invitation_email_link']
                    friend_invitation_email_link.merge_by_secret_key_allowed = False
                    friend_invitation_email_link.save()
                    status += "EMAIL_LINK-MERGE_BY_SECRET_KEY_ALLOWED-SET_TO_FALSE "
            except Exception as e:
                status += "COULD_NOT_UPDATE-merge_by_secret_key_allowed " + str(e) + " "
                success = False
    results = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'current_voter_found': current_voter_found,
        'email_owner_voter_found': email_owner_voter_found,
        'facebook_owner_voter_found': facebook_owner_voter_found,
        'invitation_owner_voter_found': invitation_owner_voter_found,
        'merge_from_voter_we_vote_id':  merge_from_voter_we_vote_id,
        'merge_to_voter_we_vote_id': merge_to_voter_we_vote_id,
    }
    return results


def voter_merge_two_accounts_action_schedule(
        from_voter=None,
        to_voter=None,
        voter_device_link=None):
    voter_device_link_manager = VoterDeviceLinkManager()
    from voter.models import VoterMergeStatus
    status = ''
    success = True

    try:
        voter_merge_status = VoterMergeStatus.objects.create(
            from_linked_organization_we_vote_id=from_voter.linked_organization_we_vote_id,
            from_voter_we_vote_id=from_voter.we_vote_id,
            to_linked_organization_we_vote_id=to_voter.linked_organization_we_vote_id,
            to_voter_we_vote_id=to_voter.we_vote_id,
        )
    except Exception as e:
        status += "SAVE_VOTER_MERGE_STATUS_FAILED: " + str(e) + " "
        results = voter_merge_two_accounts_action(from_voter, to_voter)
        status += results['status']
        if not results['success']:
            success = False

    if success:
        # And finally, relink the current voter_device_id to email_owner_voter
        update_link_results = voter_device_link_manager.update_voter_device_link(voter_device_link, to_voter)
        if update_link_results['voter_device_link_updated']:
            status += "MERGE_TWO_ACCOUNTS_VOTER_DEVICE_LINK_UPDATED "
        else:
            status += update_link_results['status']
            status += "VOTER_DEVICE_LINK_NOT_UPDATED "
            success = False

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def voter_merge_tracking(
        end_time=0.0,
        from_voter_we_vote_id='',
        start_time=0.0,
        status='',
        step_name='',
        success=False,
        to_voter_we_vote_id='',
        voter_merge_status=None,
        write_to_log=False,
):
    step_duration = 0
    tracking_success = True
    if success:
        try:
            setattr(voter_merge_status, f"{step_name}_complete", True)
            delta = end_time - start_time
            step_duration = int(delta * 1000)
            setattr(voter_merge_status, f"{step_name}_milliseconds", step_duration)
            voter_merge_status.save()
        except Exception as e:
            status += "FAILED_SAVING_VOTER_MERGE_RESULTS-" + str(step_name) + ": " + str(e) + " "
            tracking_success = False
    if write_to_log or not success or not tracking_success:
        try:
            success_for_log = success and tracking_success
            VoterMergeLog.objects.create(
                from_voter_we_vote_id=from_voter_we_vote_id,
                status=status,
                step_duration=step_duration,
                step_name=step_name,
                success=success_for_log,
                to_voter_we_vote_id=to_voter_we_vote_id,
            )
        except Exception as e:
            status += "FAILED_SAVING_VOTER_MERGE_LOG-" + str(step_name) + ": " + str(e) + " "
            tracking_success = False
    results = {
        'success':              tracking_success,
        'voter_merge_status':   voter_merge_status,
    }
    return results


def voter_merge_two_accounts_action(  # voterMergeTwoAccounts, part 2
        from_voter=None,
        to_voter=None,
        voter_merge_status=None):

    status = ""
    success = True
    from_voter_id = 0
    from_voter_we_vote_id = ""
    to_voter_id = 0
    to_voter_we_vote_id = ""
    script_start_time = time()

    try:
        from_voter_id = from_voter.id
        from_voter_we_vote_id = from_voter.we_vote_id
    except Exception as e:
        status += "MISSING_FROM_VOTER: " + str(e) + " "
        success = False

    try:
        to_voter_id = to_voter.id
        to_voter_we_vote_id = to_voter.we_vote_id
    except Exception as e:
        status += "MISSING_TO_VOTER: " + str(e) + " "
        success = False

    if not positive_value_exists(from_voter_id) or not positive_value_exists(from_voter_we_vote_id) \
            or not positive_value_exists(to_voter_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MISSING_TO_OR_FROM_VOTER_IDS "
        success = False
        results = {
            'status': status,
            'success': success,
        }
        return results

    if not hasattr(voter_merge_status, 'from_voter_we_vote_id'):
        status += "VOTER_MERGE_STATUS_NOT_PROVIDED "
        success = False
        results = {
            'status': status,
            'success': success,
        }
        return results

    voter_linked_org_start_time = time()
    # The from_voter and to_voter may both have their own linked_organization_we_vote_id
    organization_manager = OrganizationManager()
    from_voter_linked_organization_we_vote_id = from_voter.linked_organization_we_vote_id
    from_voter_linked_organization_id = 0
    if positive_value_exists(from_voter_linked_organization_we_vote_id):
        from_linked_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            from_voter_linked_organization_we_vote_id)
        if not from_linked_organization_results['success']:
            status += from_linked_organization_results['status']
            success = False
        if from_linked_organization_results['organization_found']:
            from_linked_organization = from_linked_organization_results['organization']
            from_voter_linked_organization_id = from_linked_organization.id
        else:
            from_voter_linked_organization_we_vote_id = None

    to_voter_linked_organization_we_vote_id = to_voter.linked_organization_we_vote_id
    to_voter_linked_organization_id = 0
    if positive_value_exists(to_voter_linked_organization_we_vote_id):
        to_linked_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            to_voter_linked_organization_we_vote_id)
        if not to_linked_organization_results['success']:
            status += to_linked_organization_results['status']
            success = False
        if to_linked_organization_results['organization_found']:
            to_linked_organization = to_linked_organization_results['organization']
            to_voter_linked_organization_id = to_linked_organization.id
        else:
            to_voter_linked_organization_we_vote_id = None

    if not positive_value_exists(success):
        status += "STOP_ENTIRE_PROCESS_IF_RETRIEVE_ORGANIZATION_FAILED "
        VoterMergeLog.objects.create(
            from_voter_we_vote_id=from_voter_we_vote_id,
            status=status,
            step_duration=None,
            step_name="retrieve_organization_failed",
            success=success,
            to_voter_we_vote_id=to_voter_we_vote_id,
        )
        results = {
            'status': status,
            'success': success,
        }
        return results

    # If the to_voter does not have a linked_organization_we_vote_id, then we should move the from_voter's
    #  organization_we_vote_id
    if not positive_value_exists(to_voter_linked_organization_we_vote_id):
        # Use the from_voter's linked_organization_we_vote_id
        to_voter_linked_organization_we_vote_id = from_voter_linked_organization_we_vote_id
        to_voter_linked_organization_id = from_voter_linked_organization_id
    voter_linked_org_end_time = time()

    move_apple_user_start_time = time()
    if not voter_merge_status.move_apple_user_complete:
        # Transfer the apple_user entries to the to_voter
        from apple.controllers import move_apple_user_entries_to_another_voter
        move_apple_user_results = move_apple_user_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_apple_user_end_time = time()
        status += move_apple_user_results['status']
        local_success = move_apple_user_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_apple_user_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_apple_user_start_time,
            status=status,
            step_name='move_apple_user',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_apple_user_end_time = time()

    position_list_manager = PositionListManager()
    repair_positions_start_time = time()
    if not voter_merge_status.repair_positions_complete:
        # Data healing scripts before we try to move the positions
        local_success = False
        if positive_value_exists(from_voter_id):
            repair_results = position_list_manager.repair_all_positions_for_voter(from_voter_id)
            status += repair_results['status']
            local_success = repair_results['success']
        if success and positive_value_exists(to_voter_id):
            repair_results = position_list_manager.repair_all_positions_for_voter(to_voter_id)
            status += repair_results['status']
            local_success = repair_results['success']
        if not local_success:
            success = False
        # Log the results
        repair_positions_end_time = time()
        results = voter_merge_tracking(
            end_time=repair_positions_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=repair_positions_start_time,
            status=status,
            step_name='repair_positions',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        repair_positions_end_time = time()

    move_positions_start_time = time()
    if success and not voter_merge_status.move_positions_complete:
        # Transfer positions from voter to to_voter
        move_positions_results = move_positions_to_another_voter(
            from_voter_id,
            from_voter_we_vote_id,
            to_voter_id,
            to_voter_we_vote_id,
            to_voter_linked_organization_id,
            to_voter_linked_organization_we_vote_id)
        # Log the results
        move_positions_end_time = time()
        status += move_positions_results['status']
        local_success = move_positions_results['success']
        if not local_success:
            success = False
        write_to_log = move_positions_results['write_to_log']
        results = voter_merge_tracking(
            end_time=move_positions_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_positions_start_time,
            status=status,
            step_name='move_positions',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status,
            write_to_log=write_to_log)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_positions_end_time = time()

    is_organization = False
    organization_full_name = ''
    move_organization_start_time = time()
    if success and not voter_merge_status.move_organization_complete:
        local_success = False
        if positive_value_exists(from_voter_linked_organization_we_vote_id) and \
                positive_value_exists(to_voter_linked_organization_we_vote_id) and \
                from_voter_linked_organization_we_vote_id != to_voter_linked_organization_we_vote_id:
            move_organization_to_another_complete_results = move_organization_to_another_complete(
                from_voter_linked_organization_id,
                from_voter_linked_organization_we_vote_id,
                to_voter_linked_organization_id,
                to_voter_linked_organization_we_vote_id,
                to_voter_id,
                to_voter_we_vote_id
            )
            if positive_value_exists(move_organization_to_another_complete_results['to_organization_found']):
                to_organization = move_organization_to_another_complete_results['to_organization']
                if to_organization.is_organization():
                    is_organization = True
                    organization_full_name = to_organization.organization_name

            status += " " + move_organization_to_another_complete_results['status']
            local_success = move_organization_to_another_complete_results['success']
        if not local_success:
            success = False
        # Log the results
        move_organization_end_time = time()
        results = voter_merge_tracking(
            end_time=move_organization_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_organization_start_time,
            status=status,
            step_name='move_organization',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_organization_end_time = time()

    move_friends_start_time = time()
    if not voter_merge_status.move_friends_complete:  # Proceed even if process above has failed
        # Transfer friends from voter to to_voter
        move_friends_results = move_friends_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id, to_voter_linked_organization_we_vote_id)
        status += " " + move_friends_results['status']

        # Transfer suggested friends from voter to to_voter
        move_suggested_friends_results = move_suggested_friends_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        status += " " + move_suggested_friends_results['status']

        # Transfer friend invitations from voter to email_owner_voter
        move_friend_invitations_results = move_friend_invitations_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        status += move_friend_invitations_results['status']
        # Log the results
        move_friends_end_time = time()
        local_success = move_friends_results['success'] and move_suggested_friends_results['success'] and \
            move_friend_invitations_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_friends_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_friends_start_time,
            status=status,
            step_name='move_friends',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_friends_end_time = time()

    move_follows_start_time = time()
    if not voter_merge_status.move_follows_complete:  # Proceed even if process above has failed
        move_follow_results = move_follow_entries_to_another_voter(from_voter_id, to_voter_id, to_voter_we_vote_id)
        # Log the results
        move_follows_end_time = time()
        status += move_follow_results['status']
        local_success = move_follow_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_follows_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_follows_start_time,
            status=status,
            step_name='move_follows',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_follows_end_time = time()

    move_membership_link_start_time = time()
    if not voter_merge_status.move_membership_link_complete:  # Proceed even if process above has failed
        move_membership_link_results = move_membership_link_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_membership_link_end_time = time()
        status += move_membership_link_results['status']
        local_success = move_membership_link_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_membership_link_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_membership_link_start_time,
            status=status,
            step_name='move_membership_link',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_membership_link_end_time = time()

    move_org_team_start_time = time()
    if not voter_merge_status.move_org_team_complete:  # Proceed even if process above has failed
        # Transfer the OrganizationTeamMember entries to new voter
        move_organization_team_member_results = move_organization_team_member_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id,
            from_voter_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id)
        # Log the results
        move_org_team_end_time = time()
        status += move_organization_team_member_results['status']
        local_success = move_organization_team_member_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_org_team_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_org_team_start_time,
            status=status,
            step_name='move_org_team',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_org_team_end_time = time()

    move_follow_issues_start_time = time()
    if not voter_merge_status.move_follow_issues_complete:  # Proceed even if process above has failed
        # Transfer the issues that the voter is following
        move_follow_issue_results = move_follow_issue_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_follow_issues_end_time = time()
        status += move_follow_issue_results['status']
        local_success = move_follow_issue_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_follow_issues_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_follow_issues_start_time,
            status=status,
            step_name='move_follow_issues',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_follow_issues_end_time = time()

    move_email_start_time = time()
    if not voter_merge_status.move_email_complete:  # Proceed even if process above has failed
        # Make sure we bring over all emails from the from_voter over to the to_voter
        move_email_addresses_results = move_email_address_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id, from_voter=from_voter, to_voter=to_voter)
        if move_email_addresses_results['success']:
            from_voter = move_email_addresses_results['from_voter']
            to_voter = move_email_addresses_results['to_voter']
        # Log the results
        move_email_end_time = time()
        status += move_email_addresses_results['status']
        local_success = move_email_addresses_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_email_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_email_start_time,
            status=status,
            step_name='move_email',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_email_end_time = time()

    move_sms_start_time = time()
    if not voter_merge_status.move_sms_complete:  # Proceed even if process above has failed
        # Bring over all sms phone numbers from the from_voter over to the to_voter
        move_sms_phone_number_results = move_sms_phone_number_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id, from_voter=from_voter, to_voter=to_voter)
        if move_sms_phone_number_results['success']:
            from_voter = move_sms_phone_number_results['from_voter']
            to_voter = move_sms_phone_number_results['to_voter']
        # Log the results
        move_sms_end_time = time()
        status += move_sms_phone_number_results['status']
        local_success = move_sms_phone_number_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_sms_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_sms_start_time,
            status=status,
            step_name='move_sms',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_sms_end_time = time()

    move_facebook_start_time = time()
    if not voter_merge_status.move_facebook_complete:  # Proceed even if process above has failed
        # Bring over Facebook information
        move_facebook_results = move_facebook_info_to_another_voter(from_voter, to_voter)
        # Log the results
        move_facebook_end_time = time()
        status += move_facebook_results['status']
        local_success = move_facebook_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_facebook_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_facebook_start_time,
            status=status,
            step_name='move_facebook',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_facebook_end_time = time()

    move_twitter_start_time = time()
    if not voter_merge_status.move_twitter_complete:  # Proceed even if process above has failed
        # Bring over Twitter information
        move_twitter_results = move_twitter_info_to_another_voter(from_voter, to_voter)
        # Log the results
        move_twitter_end_time = time()
        status += move_twitter_results['status']
        local_success = move_twitter_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_twitter_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_twitter_start_time,
            status=status,
            step_name='move_twitter',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_twitter_end_time = time()

    move_candidate_change_log_start_time = time()
    if not voter_merge_status.move_candidate_change_log_complete:  # Proceed even if process above has failed
        from voter.controllers_changes import move_candidate_change_log_entries_to_another_voter
        move_candidate_change_log_results = move_candidate_change_log_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_candidate_change_log_end_time = time()
        status += move_candidate_change_log_results['status']
        local_success = move_candidate_change_log_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_candidate_change_log_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_candidate_change_log_start_time,
            status=status,
            step_name='move_candidate_change_log',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_candidate_change_log_end_time = time()

    move_voter_change_log_start_time = time()
    if not voter_merge_status.move_voter_change_log_complete:  # Proceed even if process above has failed
        from voter.controllers_changes import move_voter_change_log_entries_to_another_voter
        move_voter_change_log_results = move_voter_change_log_entries_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_voter_change_log_end_time = time()
        status += move_voter_change_log_results['status']
        local_success = move_voter_change_log_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_voter_change_log_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_voter_change_log_start_time,
            status=status,
            step_name='move_voter_change_log',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_voter_change_log_end_time = time()

    move_voter_contact_start_time = time()
    if not voter_merge_status.move_voter_contact_complete:  # Proceed even if process above has failed
        from voter.controllers_contacts import move_voter_contact_email_to_another_voter
        move_voter_contact_email_results = move_voter_contact_email_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_voter_contact_end_time = time()
        status += move_voter_contact_email_results['status']
        local_success = move_voter_contact_email_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_voter_contact_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_voter_contact_start_time,
            status=status,
            step_name='move_voter_contact',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_voter_contact_end_time = time()

    move_voter_plan_start_time = time()
    if not voter_merge_status.move_voter_plan_complete:  # Proceed even if process above has failed
        # Bring over the voter's plans to vote
        move_voter_plan_results = move_voter_plan_to_another_voter(from_voter, to_voter)
        # Log the results
        move_voter_plan_end_time = time()
        status += move_voter_plan_results['status']
        local_success = move_voter_plan_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_voter_plan_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_voter_plan_start_time,
            status=status,
            step_name='move_voter_plan',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_voter_plan_end_time = time()

    move_donations_start_time = time()
    if success and not voter_merge_status.move_donations_complete:
        # Bring over any donations that have been made in this session by the to_voter to the voter, subscriptions
        # are complicated.  See the comments in the donate/controllers.py
        move_donation_results = move_donation_info_to_another_voter(from_voter, to_voter)
        # Log the results
        move_donations_end_time = time()
        status += move_donation_results['status']
        local_success = move_donation_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_donations_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_donations_start_time,
            status=status,
            step_name='move_donations',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_donations_end_time = time()

    move_voter_guides_start_time = time()
    if not voter_merge_status.move_voter_guides_complete:  # Proceed even if process above has failed
        # Bring over Voter Guides
        move_voter_guide_results = move_voter_guides_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id,
            to_voter_linked_organization_we_vote_id)
        # Log the results
        move_voter_guides_end_time = time()
        status += move_voter_guide_results['status']
        local_success = move_voter_guide_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_voter_guides_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_voter_guides_start_time,
            status=status,
            step_name='move_voter_guides',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_voter_guides_end_time = time()

    move_shared_items_start_time = time()
    if not voter_merge_status.move_shared_items_complete:  # Proceed even if process above has failed
        # Bring over SharedItems
        move_shared_items_results = move_shared_items_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id,
            from_voter_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id)
        # Log the results
        move_shared_items_end_time = time()
        status += move_shared_items_results['status']
        local_success = move_shared_items_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_shared_items_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_shared_items_start_time,
            status=status,
            step_name='move_shared_items',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_shared_items_end_time = time()

    move_activity_notices_start_time = time()
    if not voter_merge_status.move_activity_notices_complete:  # Proceed even if process above has failed
        # Transfer ActivityNoticeSeed and ActivityNotice entries from voter to to_voter
        move_activity_results = move_activity_notices_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id,
            from_voter_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id,
            to_voter=to_voter)
        # Log the results
        move_activity_notices_end_time = time()
        status += move_activity_results['status']
        local_success = move_activity_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_activity_notices_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_activity_notices_start_time,
            status=status,
            step_name='move_activity_notices',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_activity_notices_end_time = time()

    move_activity_posts_start_time = time()
    if success and not voter_merge_status.move_activity_posts_complete:
        # Transfer ActivityPost entries from voter to to_voter
        move_activity_post_results = move_activity_posts_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id,
            from_voter_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id,
            to_voter=to_voter)
        # Log the results
        move_activity_posts_end_time = time()
        status += move_activity_post_results['status']
        local_success = move_activity_post_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_activity_posts_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_activity_posts_start_time,
            status=status,
            step_name='move_activity_posts',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_activity_posts_end_time = time()

    move_activity_comments_start_time = time()
    if success and not voter_merge_status.move_activity_comments_complete:
        # Transfer ActivityComment entries from voter to to_voter
        move_activity_comment_results = move_activity_comments_to_another_voter(
            from_voter_we_vote_id, to_voter_we_vote_id,
            from_voter_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id,
            to_voter=to_voter)
        # Log the results
        move_activity_comments_end_time = time()
        status += move_activity_comment_results['status']
        local_success = move_activity_comment_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_activity_comments_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_activity_comments_start_time,
            status=status,
            step_name='move_activity_comments',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_activity_comments_end_time = time()

    move_campaignx_start_time = time()
    if not voter_merge_status.move_campaignx_complete:  # Proceed even if process above has failed
        # Transfer CampaignX related info from voter to to_voter
        move_campaignx_results = move_campaignx_to_another_voter(
            from_voter_we_vote_id,
            to_voter_we_vote_id,
            from_voter_linked_organization_we_vote_id,
            to_voter_linked_organization_we_vote_id,
            to_organization_name=organization_full_name)
        # Log the results
        move_campaignx_end_time = time()
        status += move_campaignx_results['status']
        local_success = move_campaignx_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_campaignx_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_campaignx_start_time,
            status=status,
            step_name='move_campaignx',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_campaignx_end_time = time()

    move_analytics_start_time = time()
    if not voter_merge_status.move_analytics_complete:  # Proceed even if process above has failed
        # Bring over Analytics information
        move_analytics_results = move_analytics_info_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id)
        # Log the results
        move_analytics_end_time = time()
        status += move_analytics_results['status']
        local_success = move_analytics_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_analytics_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_analytics_start_time,
            status=status,
            step_name='move_analytics',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_analytics_end_time = time()

    merge_voter_start_time = time()
    if success and not voter_merge_status.merge_voter_complete:
        if not positive_value_exists(from_voter_linked_organization_we_vote_id):
            # Remove the link to the organization, so we don't have a future conflict
            try:
                from_voter.linked_organization_we_vote_id = None
                from_voter.save()
                # All positions should have already been moved with move_positions_to_another_voter
            except Exception as e:
                status += "FAILED_TO_REMOVE_LINKED_ORGANIZATION_WE_VOTE_ID-FROM_VOTER " + str(e) + " "
                success = False
                VoterMergeLog.objects.create(
                    from_voter_we_vote_id=from_voter_we_vote_id,
                    status=status,
                    step_duration=None,
                    step_name="from_voter_linked_org_clear",
                    success=success,
                    to_voter_we_vote_id=to_voter_we_vote_id,
                )
        if not positive_value_exists(to_voter_linked_organization_we_vote_id):
            # Remove the link to the organization, so we don't have a future conflict
            try:
                to_voter.linked_organization_we_vote_id = None
                to_voter.save()
                # All positions should have already been moved with move_positions_to_another_voter
            except Exception as e:
                status += "FAILED_TO_REMOVE_LINKED_ORGANIZATION_WE_VOTE_ID-TO_VOTER " + str(e) + " "
                success = False
                VoterMergeLog.objects.create(
                    from_voter_we_vote_id=from_voter_we_vote_id,
                    status=status,
                    step_duration=None,
                    step_name="to_voter_linked_org_clear",
                    success=success,
                    to_voter_we_vote_id=to_voter_we_vote_id,
                )

        if not success:
            # We kill the process here because we couldn't save one or both of the voters
            status += "KILLED_ENTIRE_PROCESS "
            results = {
                'status': status,
                'success': success,
            }
            return results

        # Bring over the voter-table data
        merge_voter_accounts_results = merge_voter_accounts(from_voter, to_voter)
        to_voter = merge_voter_accounts_results['to_voter']
        # Log the results
        merge_voter_end_time = time()
        status += merge_voter_accounts_results['status']
        local_success = merge_voter_accounts_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=merge_voter_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=merge_voter_start_time,
            status=status,
            step_name='merge_voter',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        merge_voter_end_time = time()

    move_images_start_time = time()
    if not voter_merge_status.move_images_complete:  # Proceed even if process above has failed
        # Make sure the organization has the latest profile image from the voter record
        transfer_voter_images_results = transfer_voter_images_to_organization(voter=to_voter)
        # Log the results
        move_images_end_time = time()
        status += transfer_voter_images_results['status']
        local_success = transfer_voter_images_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=move_images_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=move_images_start_time,
            status=status,
            step_name='move_images',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        move_images_end_time = time()

    send_emails_start_time = time()
    if success and not voter_merge_status.send_emails_complete:
        # Send any friend invitations set up before sign in
        email_manager = EmailManager()
        real_name_only = True
        local_success = True
        if is_organization:
            if positive_value_exists(organization_full_name) and 'Voter-' not in organization_full_name:
                # Only send if the organization name exists
                send_results = email_manager.send_scheduled_emails_waiting_for_verification(
                    from_voter_we_vote_id, organization_full_name)
                status += send_results['status']
                local_success = send_results['success']
            else:
                status += "CANNOT_SEND_SCHEDULED_EMAILS_WITHOUT_ORGANIZATION_NAME-VOTER_CONTROLLER "
        elif positive_value_exists(from_voter.get_full_name(real_name_only)):
            # Only send if the sender's full name exists
            send_results = email_manager.send_scheduled_emails_waiting_for_verification(
                from_voter_we_vote_id, from_voter.get_full_name(real_name_only))
            status += send_results['status']
            local_success = send_results['success']
        else:
            status += "CANNOT_SEND_SCHEDULED_EMAILS_WITHOUT_NAME-VOTER_CONTROLLER "
        # Log the results
        if not local_success:
            success = False
        send_emails_end_time = time()
        results = voter_merge_tracking(
            end_time=send_emails_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=send_emails_start_time,
            status=status,
            step_name='send_emails',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        send_emails_end_time = time()

    # TODO Do similar send for SMS

    # TODO Keep a record of voter_we_vote_id's associated with this voter, so we can find the
    #  latest we_vote_id

    # TODO If no errors, delete the voter account

    final_position_repair_start_time = time()
    if not voter_merge_status.final_position_repair_complete:  # Proceed even if process above has failed
        # Data healing scripts
        repair_results = position_list_manager.repair_all_positions_for_voter(to_voter.id)
        # Log the results
        final_position_repair_end_time = time()
        status += repair_results['status']
        local_success = repair_results['success']
        if not local_success:
            success = False
        results = voter_merge_tracking(
            end_time=final_position_repair_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=final_position_repair_start_time,
            status=status,
            step_name='final_position_repair',
            success=local_success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        final_position_repair_end_time = time()

    if not voter_merge_status.total_merge_complete:  # Proceed even if process above has failed
        # Log the results
        script_end_time = time()
        results = voter_merge_tracking(
            end_time=script_end_time,
            from_voter_we_vote_id=from_voter_we_vote_id,
            start_time=script_start_time,
            status=status,
            step_name='total_merge',
            success=success,
            to_voter_we_vote_id=to_voter_we_vote_id,
            voter_merge_status=voter_merge_status,
            write_to_log=True)
        if results['success']:
            voter_merge_status = results['voter_merge_status']
        else:
            success = False
    else:
        script_end_time = time()

    voter_linked_org_duration = voter_linked_org_end_time - voter_linked_org_start_time
    move_apple_duration = move_apple_user_end_time - move_apple_user_start_time
    repair_positions_duration = repair_positions_end_time - repair_positions_start_time
    move_candidate_change_log_duration = move_candidate_change_log_end_time - move_candidate_change_log_start_time
    move_positions_duration = move_positions_end_time - move_positions_start_time
    move_organization_duration = move_organization_end_time - move_organization_start_time
    move_friends_duration = move_friends_end_time - move_friends_start_time
    move_follows_duration = move_follows_end_time - move_follows_start_time
    move_membership_link_duration = move_membership_link_end_time - move_membership_link_start_time
    move_org_team_duration = move_org_team_end_time - move_org_team_start_time
    move_follow_issues_duration = move_follow_issues_end_time - move_follow_issues_start_time
    move_email_duration = move_email_end_time - move_email_start_time
    move_sms_duration = move_sms_end_time - move_sms_start_time
    move_facebook_duration = move_facebook_end_time - move_facebook_start_time
    move_twitter_duration = move_twitter_end_time - move_twitter_start_time
    move_voter_change_log_duration = move_voter_change_log_end_time - move_voter_change_log_start_time
    move_voter_contact_duration = move_voter_contact_end_time - move_voter_contact_start_time
    move_voter_plan_duration = move_voter_plan_end_time - move_voter_plan_start_time
    move_donations_duration = move_donations_end_time - move_donations_start_time
    move_voter_guides_duration = move_voter_guides_end_time - move_voter_guides_start_time
    move_shared_items_duration = move_shared_items_end_time - move_shared_items_start_time
    move_activity_notices_duration = move_activity_notices_end_time - move_activity_notices_start_time
    move_activity_posts_duration = move_activity_posts_end_time - move_activity_posts_start_time
    move_activity_comments_duration = move_activity_comments_end_time - move_activity_comments_start_time
    move_campaignx_duration = move_campaignx_end_time - move_campaignx_start_time
    move_analytics_duration = move_analytics_end_time - move_analytics_start_time
    merge_voter_duration = merge_voter_end_time - merge_voter_start_time
    move_images_duration = move_images_end_time - move_images_start_time
    send_emails_duration = send_emails_end_time - send_emails_start_time
    final_position_repair_duration = final_position_repair_end_time - final_position_repair_start_time
    time_difference = script_end_time - script_start_time
    logger.error('(Ok) voter_merge_two_accounts_action'
                 ' voter_linked_org took ' + "{:.6f}".format(voter_linked_org_duration) +
                 ' seconds, move_apple took ' + "{:.6f}".format(move_apple_duration) +
                 ' seconds, repair_positions took ' + "{:.6f}".format(repair_positions_duration) +
                 ' seconds, move_positions took ' + "{:.6f}".format(move_positions_duration) +
                 ' seconds, move_organization took ' + "{:.6f}".format(move_organization_duration) +
                 ' seconds, move_friends took ' + "{:.6f}".format(move_friends_duration) +
                 ' seconds, move_follows ' + "{:.6f}".format(move_follows_duration) +
                 ' seconds, move_membership_link took ' + "{:.6f}".format(move_membership_link_duration) +
                 ' seconds, move_org_team took ' + "{:.6f}".format(move_org_team_duration) +
                 ' seconds, move_follow_issues took ' + "{:.6f}".format(move_follow_issues_duration) +
                 ' seconds, move_email took ' + "{:.6f}".format(move_email_duration) +
                 ' seconds, move_sms took ' + "{:.6f}".format(move_sms_duration) +
                 ' seconds, move_facebook took ' + "{:.6f}".format(move_facebook_duration) +
                 ' seconds, move_twitter took ' + "{:.6f}".format(move_twitter_duration) +
                 ' seconds, move_candidate_change_log took ' + "{:.6f}".format(move_candidate_change_log_duration) +
                 ' seconds, move_voter_change_log took ' + "{:.6f}".format(move_voter_change_log_duration) +
                 ' seconds, move_voter_contact took ' + "{:.6f}".format(move_voter_contact_duration) +
                 ' seconds, move_voter_plan took ' + "{:.6f}".format(move_voter_plan_duration) +
                 ' seconds, move_donations took ' + "{:.6f}".format(move_donations_duration) +
                 ' seconds, move_voter_guides took ' + "{:.6f}".format(move_voter_guides_duration) +
                 ' seconds, move_shared_items took ' + "{:.6f}".format(move_shared_items_duration) +
                 ' seconds, move_activity_notices took ' + "{:.6f}".format(move_activity_notices_duration) +
                 ' seconds, move_activity_posts took ' + "{:.6f}".format(move_activity_posts_duration) +
                 ' seconds, move_activity_comments took ' + "{:.6f}".format(move_activity_comments_duration) +
                 ' seconds, move_campaignx took ' + "{:.6f}".format(move_campaignx_duration) +
                 ' seconds, move_analytics took ' + "{:.6f}".format(move_analytics_duration) +
                 ' seconds, merge_voter took ' + "{:.6f}".format(merge_voter_duration) +
                 ' seconds, move_images took ' + "{:.6f}".format(move_images_duration) +
                 ' seconds, send_emails took ' + "{:.6f}".format(send_emails_duration) +
                 ' seconds, final_position_repair took ' + "{:.6f}".format(final_position_repair_duration) +
                 ' seconds, total took ' + "{:.6f}".format(time_difference) + ' seconds')

    results = {
        'status':   status,
        'success':  success,
    }
    return results


def voter_photo_save_for_api(voter_device_id, facebook_profile_image_url_https, facebook_photo_variable_exists):
    """
    voterPhotoSave - this API is deprecated. Please do not extend.
    :param voter_device_id:
    :param facebook_profile_image_url_https:
    :param facebook_photo_variable_exists:
    :return:
    """
    facebook_profile_image_url_https = facebook_profile_image_url_https.strip()

    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        results = {
                'status': device_id_results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }
        return results

    if not facebook_photo_variable_exists:
        results = {
                'status': "MISSING_VARIABLE-AT_LEAST_ONE_PHOTO ",
                'success': False,
                'voter_device_id': voter_device_id,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id < 0:
        results = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_PHOTO_SAVE ",
            'success': False,
            'voter_device_id': voter_device_id,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
        }
        return results

    # At this point, we have a valid voter

    voter_manager = VoterManager()
    results = voter_manager.update_voter_photos(voter_id,
                                                facebook_profile_image_url_https, facebook_photo_variable_exists)

    if results['success']:
        if positive_value_exists(facebook_profile_image_url_https):
            status = "VOTER_FACEBOOK_PHOTO_SAVED "
        else:
            status = "VOTER_PHOTOS_EMPTY_SAVED "

        results = {
                'status': status,
                'success': True,
                'voter_device_id': voter_device_id,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }

    else:
        results = {
                'status': results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }
    return results


def voter_retrieve_for_api(  # voterRetrieve
        request=None,
        state_code_from_ip_address='',
        user_agent_string='',
        user_agent_object=None,
        voter_device_id='',
        voter_location_results=None,
):
    """
    Used by the api
    :param request:
    :param voter_device_id:
    :param state_code_from_ip_address:
    :param user_agent_string:
    :param user_agent_object:
    :param voter_location_results:
    :return:
    """
    if voter_location_results is None:
        voter_location_results = {}
    if voter_location_results is None:
        voter_location_results = {}
    organization_manager = OrganizationManager()
    voter_manager = VoterManager()
    voter_device_link = VoterDeviceLink()
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_id = 0
    voter_created = False
    twitter_link_to_voter = TwitterLinkToVoter()
    repair_twitter_link_to_voter_caching_now = False
    repair_facebook_link_to_voter_caching_now = False
    facebook_user = None

    status = "VOTER_RETRIEVE_START "

    if positive_value_exists(voter_device_id):
        status += "VOTER_DEVICE_ID_RECEIVED "
        # If a voter_device_id is passed in that isn't valid, we want to throw an error
        device_id_results = is_voter_device_id_valid(voter_device_id)
        if not device_id_results['success']:
            json_data = {
                    'status':           device_id_results['status'],
                    'success':          False,
                    'voter_device_id':  voter_device_id,
                    'voter_created':    False,
                    'voter_found':      False,
                    'state_code_from_ip_address': state_code_from_ip_address,
            }
            return json_data

        voter_device_link_results = \
            voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id)
        if voter_device_link_results['voter_device_link_found']:
            voter_device_link = voter_device_link_results['voter_device_link']
            voter_id = voter_device_link.voter_id
        if not positive_value_exists(voter_id):
            json_data = {
                'status':           "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_RETRIEVE ",
                'success':          False,
                'voter_device_id':  voter_device_id,
                'voter_created':    False,
                'voter_found':      False,
                'state_code_from_ip_address': state_code_from_ip_address,
            }
            return json_data
    else:
        # If a voter_device_id isn't passed in, automatically create a new voter_device_id and voter
        status += "VOTER_DEVICE_NOT_PASSED_IN "
        voter_device_id = generate_voter_device_id()

        # We make sure a voter record hasn't already been created for this new voter_device_id, so we don't create a
        # security hole by giving a new person access to an existing account. This should never happen because it is
        # so unlikely that we will ever generate an existing voter_device_id with generate_voter_device_id.
        existing_voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
        if existing_voter_id:
            json_data = {
                'status':           "VOTER_ALREADY_EXISTS_BUT_ACCESS_RESTRICTED",
                'success':          False,
                'voter_device_id':  voter_device_id,
                'voter_created':    False,
                'voter_found':      False,
                'state_code_from_ip_address':   state_code_from_ip_address,
            }
            return json_data

        results = voter_manager.create_voter()

        if results['voter_created']:
            status += "VOTER_CREATED "
            voter = results['voter']

            # Now save the voter_device_link
            results = voter_device_link_manager.save_new_voter_device_link(voter_device_id, voter.id)

            if results['voter_device_link_created']:
                voter_device_link = results['voter_device_link']
                voter_id_found = True if voter_device_link.voter_id > 0 else False

                if voter_id_found:
                    voter_id = voter_device_link.voter_id
                    voter_created = True

        if not positive_value_exists(voter_id):
            json_data = {
                'status':                           "VOTER_NOT_FOUND_AFTER_BEING_CREATED",
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'voter_created':                    False,
                'voter_found':                      False,
                'state_code_from_ip_address':       state_code_from_ip_address,
            }
            return json_data

    # At this point, we should have a valid voter_id
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if results['voter_found']:
        voter = results['voter']

        if voter_created:
            status += 'VOTER_CREATED '
        else:
            status += 'VOTER_FOUND '

        # Save state_code found via IP address
        if positive_value_exists(state_code_from_ip_address):
            voter_device_link_manager.update_voter_device_link_with_state_code(
                voter_device_link, state_code_from_ip_address)

        twitter_link_to_voter_twitter_id = 0
        # 2018-07-17 DALE Trying with this off
        # if voter.is_signed_in():
        twitter_user_manager = TwitterUserManager()
        twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_voter(0, voter.we_vote_id)
        if twitter_link_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_link_results['twitter_link_to_voter']
            twitter_link_to_voter_twitter_id = twitter_link_to_voter.twitter_id

        twitter_link_to_organization_we_vote_id = ""
        twitter_link_to_organization_twitter_id = 0
        if positive_value_exists(twitter_link_to_voter_twitter_id):
            twitter_org_link_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
                    twitter_link_to_voter_twitter_id)
            if twitter_org_link_results['twitter_link_to_organization_found']:
                twitter_link_to_organization = twitter_org_link_results['twitter_link_to_organization']
                twitter_link_to_organization_twitter_id = twitter_link_to_organization.twitter_id
                twitter_link_to_organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id
        else:
            if positive_value_exists(voter.twitter_screen_name) or positive_value_exists(voter.twitter_id):
                # If the voter has cached twitter information, delete it now because there isn't a
                #  twitter_link_to_voter entry
                try:
                    voter.twitter_id = 0
                    voter.twitter_screen_name = ""
                    voter.save()
                    status += "VOTER_TWITTER_CLEARED1 "
                    repair_twitter_link_to_voter_caching_now = True
                except Exception as e:
                    status += "UNABLE_TO_CLEAR_TWITTER_SCREEN_NAME1 "

        if positive_value_exists(twitter_link_to_voter_twitter_id) and \
                positive_value_exists(twitter_link_to_organization_twitter_id) and \
                twitter_link_to_voter_twitter_id == twitter_link_to_organization_twitter_id:
            # If we have a twitter link to both the voter and the organization, then we want to make sure the
            #  voter is linked to the correct organization
            status += "VERIFYING_TWITTER_LINK_TO_ORGANIZATION "
            if voter.linked_organization_we_vote_id != twitter_link_to_organization_we_vote_id:
                # If here there is a mismatch to fix
                try:
                    voter.linked_organization_we_vote_id = twitter_link_to_organization_we_vote_id
                    voter.save()
                    repair_twitter_link_to_voter_caching_now = True
                    status += "VOTER_LINKED_ORGANIZATION_FIXED "
                except Exception as e:
                    status += "VOTER_LINKED_ORGANIZATION_COULD_NOT_BE_FIXED " + str(e) + " "

        if positive_value_exists(voter.linked_organization_we_vote_id):
            existing_organization_for_this_voter_found = True
        else:
            status += "VOTER.LINKED_ORGANIZATION_WE_VOTE_ID-MISSING "
            existing_organization_for_this_voter_found = False
            create_twitter_link_to_organization = False
            organization_twitter_handle = ""
            organization_twitter_id = ""
            twitter_link_to_voter_twitter_id = 0

            # Is this voter associated with a Twitter account?
            # If so, check to see if an organization entry exists for this voter.
            if twitter_link_results['twitter_link_to_voter_found']:
                twitter_link_to_voter = twitter_link_results['twitter_link_to_voter']
                if not positive_value_exists(twitter_link_to_voter.twitter_id):
                    if positive_value_exists(voter.twitter_screen_name) or positive_value_exists(voter.twitter_id):
                        try:
                            voter.twitter_id = 0
                            voter.twitter_screen_name = ""
                            voter.save()
                            status += "VOTER_TWITTER_CLEARED2 "
                        except Exception as e:
                            status += "UNABLE_TO_CLEAR_TWITTER_SCREEN_NAME2 "
                else:
                    # If here there is a twitter_link_to_voter to possibly update
                    try:
                        value_to_save = False
                        twitter_link_to_voter_twitter_id = twitter_link_to_voter.twitter_id
                        if voter.twitter_id == twitter_link_to_voter_twitter_id:
                            status += "VOTER_TWITTER_ID_MATCHES "
                        else:
                            status += "VOTER_TWITTER_ID_DOES_NOT_MATCH_LINKED_TO_VOTER "
                            voter.twitter_id = twitter_link_to_voter_twitter_id
                            value_to_save = True

                        voter_twitter_screen_name = twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
                        if voter.twitter_screen_name == voter_twitter_screen_name:
                            status += "VOTER_TWITTER_SCREEN_NAME_MATCHES "
                        else:
                            status += "VOTER_TWITTER_SCREEN_NAME_DOES_NOT_MATCH_LINKED_TO_VOTER "
                            voter.twitter_screen_name = voter_twitter_screen_name
                            value_to_save = True

                        if value_to_save:
                            voter.save()
                            repair_twitter_link_to_voter_caching_now = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_VOTER_TWITTER_CACHED_INFO "

                    twitter_link_to_voter_twitter_id = twitter_link_to_voter.twitter_id
                    # Since we know this voter has authenticated for a Twitter account,
                    #  check to see if there is an organization associated with this Twitter account
                    # If an existing TwitterLinkToOrganization is found, link this org to this voter
                    twitter_org_link_results = \
                        twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
                            twitter_link_to_voter.twitter_id)
                    if twitter_org_link_results['twitter_link_to_organization_found']:
                        twitter_link_to_organization = twitter_org_link_results['twitter_link_to_organization']
                        organization_twitter_id = twitter_link_to_organization.twitter_id
                        if positive_value_exists(twitter_link_to_organization.organization_we_vote_id):
                            if twitter_link_to_organization.organization_we_vote_id \
                                    != voter.linked_organization_we_vote_id:
                                try:
                                    voter.linked_organization_we_vote_id = \
                                        twitter_link_to_organization.organization_we_vote_id
                                    voter.save()
                                    existing_organization_for_this_voter_found = True

                                except Exception as e:
                                    status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_FROM_TWITTER_LINK_TO_VOTER " + \
                                              str(e) + " "
                    else:
                        # If an existing TwitterLinkToOrganization was not found,
                        # create the organization below, and then create TwitterLinkToOrganization
                        organization_twitter_handle = twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
                        organization_twitter_id = twitter_link_to_voter.twitter_id
                        create_twitter_link_to_organization = True

            if not existing_organization_for_this_voter_found:
                status += "EXISTING_ORGANIZATION_NOT_FOUND "
                # If we are here, we need to create an organization for this voter
                create_results = organization_manager.create_organization(
                    organization_name=voter.get_full_name(),
                    organization_twitter_handle=organization_twitter_handle,
                    organization_image=voter.voter_photo_url(),
                    organization_type=INDIVIDUAL,
                    twitter_id=organization_twitter_id,
                    we_vote_hosted_profile_image_url_large=voter.we_vote_hosted_profile_image_url_large,
                    we_vote_hosted_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny
                )
                if create_results['organization_created']:
                    # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                    organization = create_results['organization']
                    status += "ORGANIZATION_CREATED "
                    try:
                        voter.linked_organization_we_vote_id = organization.we_vote_id
                        voter.save()
                        existing_organization_for_this_voter_found = True
                        if create_twitter_link_to_organization:
                            create_results = twitter_user_manager.create_twitter_link_to_organization(
                                twitter_link_to_voter_twitter_id, organization.we_vote_id)

                            if create_results['twitter_link_to_organization_saved']:
                                twitter_link_to_organization = create_results['twitter_link_to_organization']
                                organization_list_manager = OrganizationListManager()
                                repair_results = \
                                    organization_list_manager.repair_twitter_related_organization_caching(
                                        twitter_link_to_organization.twitter_id)
                                status += repair_results['status']

                    except Exception as e:
                        status += "UNABLE_TO_CREATE_NEW_ORGANIZATION_TO_VOTER_FROM_RETRIEVE_VOTER: " + str(e) + " "
                else:
                    status += "ORGANIZATION_NOT_CREATED "

        # Check to see if there is a FacebookLinkToVoter for this voter, and if so, see if we need to make
        #  organization update with latest Facebook data
        facebook_manager = FacebookManager()
        facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
            voter.we_vote_id, read_only=True)
        if facebook_link_results['facebook_link_to_voter_found']:
            status += "FACEBOOK_LINK_TO_VOTER_FOUND "
            facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
            facebook_link_to_voter_facebook_user_id = facebook_link_to_voter.facebook_user_id
            if positive_value_exists(facebook_link_to_voter_facebook_user_id):
                facebook_user_results = FacebookManager().retrieve_facebook_user_by_facebook_user_id(
                    facebook_link_to_voter_facebook_user_id)
                if facebook_user_results['facebook_user_found']:
                    status += "FACEBOOK_USER_FOUND "
                    facebook_user = facebook_user_results['facebook_user']

                    organization_results = \
                        OrganizationManager().retrieve_organization_from_we_vote_id(
                            voter.linked_organization_we_vote_id)
                    if organization_results['organization_found']:
                        try:
                            organization = organization_results['organization']
                            status += "FACEBOOK-ORGANIZATION_FOUND "
                            save_organization = False
                            # Look at the linked_organization for the voter and update with latest
                            if positive_value_exists(facebook_user.facebook_profile_image_url_https):
                                facebook_profile_image_different = \
                                    not positive_value_exists(organization.facebook_profile_image_url_https) \
                                    or facebook_user.facebook_profile_image_url_https != \
                                    organization.facebook_profile_image_url_https
                                if facebook_profile_image_different:
                                    organization.facebook_profile_image_url_https = \
                                        facebook_user.facebook_profile_image_url_https
                                    save_organization = True
                            if positive_value_exists(facebook_user.facebook_background_image_url_https) and \
                                    not positive_value_exists(organization.facebook_background_image_url_https):
                                organization.facebook_background_image_url_https = \
                                    facebook_user.facebook_background_image_url_https
                                save_organization = True
                            if positive_value_exists(facebook_user.facebook_user_id) and \
                                    not positive_value_exists(organization.facebook_id):
                                organization.facebook_id = facebook_user.facebook_user_id
                                save_organization = True
                            if positive_value_exists(facebook_user.facebook_email) and \
                                    not positive_value_exists(organization.facebook_email):
                                organization.facebook_email = facebook_user.facebook_email
                                save_organization = True
                            if save_organization:
                                repair_facebook_link_to_voter_caching_now = True
                                organization.save()
                                status += "FACEBOOK-ORGANIZATION_SAVED "
                        except Exception as e:
                            status += "FAILED_UPDATE_OR_CREATE_ORGANIZATION: " + str(e)
                            logger.error('FAILED organization_manager.update_or_create_organization. '
                                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e)))
                    else:
                        status += "FACEBOOK_RELATED_ORGANIZATION_NOT_FOUND "
                else:
                    status += "FACEBOOK_USER_NOT_FOUND "

        else:
            status += "FACEBOOK_LINK_TO_VOTER_NOT_FOUND "

        if not positive_value_exists(voter.linked_organization_we_vote_id):
            # If we are here, we need to create an organization for this voter
            status += "NEED_TO_CREATE_ORGANIZATION_FOR_THIS_VOTER "
            create_results = organization_manager.create_organization(
                organization_name=voter.get_full_name(),
                organization_image=voter.voter_photo_url(),
                organization_type=INDIVIDUAL,
                we_vote_hosted_profile_image_url_large=voter.we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny
            )
            if create_results['organization_created']:
                # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                organization = create_results['organization']
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()
                    status += "ORGANIZATION_CREATED "
                except Exception as e:
                    status += "UNABLE_TO_CREATE_NEW_ORGANIZATION_TO_VOTER_FROM_RETRIEVE_VOTER2 "

        if repair_twitter_link_to_voter_caching_now:
            # If here then we know that we have a twitter_link_to_voter, and there was some data cleanup done
            repair_results = voter_manager.repair_twitter_related_voter_caching(
                twitter_link_to_voter.twitter_id)
            status += repair_results['status']

        # TODO DALE: Add if repair_facebook_link_to_voter_caching_now
        is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
        analytics_manager = AnalyticsManager()
        if voter.signed_in_facebook():
            is_signed_in = True
            analytics_manager.save_action(ACTION_FACEBOOK_AUTHENTICATION_EXISTS, voter.we_vote_id, voter_id,
                                          is_signed_in, user_agent_string=user_agent_string, is_bot=is_bot,
                                          is_mobile=user_agent_object.is_mobile,
                                          is_desktop=user_agent_object.is_pc,
                                          is_tablet=user_agent_object.is_tablet)
        if voter.signed_in_google():
            is_signed_in = True
            analytics_manager.save_action(ACTION_GOOGLE_AUTHENTICATION_EXISTS, voter.we_vote_id, voter_id,
                                          is_signed_in, user_agent_string=user_agent_string, is_bot=is_bot,
                                          is_mobile=user_agent_object.is_mobile,
                                          is_desktop=user_agent_object.is_pc,
                                          is_tablet=user_agent_object.is_tablet)
        if voter.signed_in_twitter():
            is_signed_in = True
            analytics_manager.save_action(ACTION_TWITTER_AUTHENTICATION_EXISTS, voter.we_vote_id, voter_id,
                                          is_signed_in, user_agent_string=user_agent_string, is_bot=is_bot,
                                          is_mobile=user_agent_object.is_mobile,
                                          is_desktop=user_agent_object.is_pc,
                                          is_tablet=user_agent_object.is_tablet)
        if voter.signed_in_with_email():
            is_signed_in = True
            analytics_manager.save_action(ACTION_EMAIL_AUTHENTICATION_EXISTS, voter.we_vote_id, voter_id,
                                          is_signed_in, user_agent_string=user_agent_string, is_bot=is_bot,
                                          is_mobile=user_agent_object.is_mobile,
                                          is_desktop=user_agent_object.is_pc,
                                          is_tablet=user_agent_object.is_tablet)

        facebook_profile_image_url_https, \
            we_vote_hosted_profile_image_url_large, \
            we_vote_hosted_profile_image_url_medium = \
            get_displayable_images(voter, facebook_user)

        address_results = voter_address_retrieve_for_voter_id(voter_id)
        if address_results['success'] and not address_results['address_found']:
            # Create new address
            if 'voter_location_found' not in voter_location_results:
                voter_location_results = voter_location_retrieve_from_ip_for_api(request)
            if voter_location_results['voter_location_found']:
                status += 'VOTER_RETRIEVE-VOTER_LOCATION_FOUND_FROM_IP '
                text_for_map_search = voter_location_results['voter_location']
                status += '*** ' + text_for_map_search + ' ***, '

                from voter.models import VoterAddressManager
                voter_address_manager = VoterAddressManager()
                voter_address_save_results = voter_address_manager.update_or_create_voter_address(
                    voter_id, BALLOT_ADDRESS, text_for_map_search)
                status += voter_address_save_results['status'] + ", "

                if voter_address_save_results['success'] and voter_address_save_results['voter_address_found']:
                    address_results = voter_address_retrieve_for_voter_id(voter_id)

        team_member_list = organization_manager.retrieve_team_member_list(
            can_edit_campaignx_owned_by_organization=True,
            voter_we_vote_id=voter.we_vote_id)
        can_edit_campaignx_owned_by_organization_list = []
        for team_member in team_member_list:
            can_edit_campaignx_owned_by_organization_list.append(team_member.organization_we_vote_id)

        # print('voterRetrieve status', status, ', voter.email ', voter.email, ', full name ', voter.get_full_name(), ',
        #   voter_photo_url_medium', we_vote_hosted_profile_image_url_medium )
        json_data = {
            'status':                           status,
            'success':                          True,
            'address':                          address_results,
            'can_edit_campaignx_owned_by_organization_list': can_edit_campaignx_owned_by_organization_list,
            'date_joined':                      voter.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'email':                            voter.email,
            'facebook_email':                   voter.facebook_email,
            'facebook_id':                      voter.facebook_id,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
            'first_name':                       voter.first_name,
            'full_name':                        voter.get_full_name(),
            'has_data_to_preserve':             voter.has_data_to_preserve(),
            'has_email_with_verified_ownership':    voter.has_email_with_verified_ownership(),
            'has_valid_email':                  voter.has_valid_email(),
            'interface_status_flags':           voter.interface_status_flags,
            'is_admin':                         voter.is_admin,
            'is_analytics_admin':               voter.is_analytics_admin,
            'is_partner_organization':          voter.is_partner_organization,
            'is_political_data_manager':        voter.is_political_data_manager,
            'is_political_data_viewer':         voter.is_political_data_viewer,
            'is_signed_in':                     voter.is_signed_in(),
            'is_verified_volunteer':            voter.is_verified_volunteer,
            'is_voter_manager':                 voter.is_voter_manager,
            'last_name':                        voter.last_name,
            'linked_organization_we_vote_id':   voter.linked_organization_we_vote_id,
            'notification_settings_flags':      voter.notification_settings_flags,
            'profile_image_type_currently_active':  voter.profile_image_type_currently_active,
            'signed_in':                        voter.is_signed_in(),            # Extra field for debugging the WebApp
            'signed_in_facebook':               voter.signed_in_facebook(),
            'signed_in_google':                 voter.signed_in_google(),
            'signed_in_twitter':                voter.signed_in_twitter(),
            'signed_in_with_apple':             voter.signed_in_with_apple(),
            'signed_in_with_email':             voter.signed_in_with_email(),
            'signed_in_with_sms_phone_number':  voter.signed_in_with_sms_phone_number(),
            'state_code_from_ip_address':       state_code_from_ip_address,
            'text_for_map_search':              address_results['text_for_map_search'],
            'twitter_screen_name':              voter.twitter_screen_name,
            'voter_created':                    voter_created,
            'voter_device_id':                  voter_device_id,
            'voter_found':                      True,
            'voter_photo_url_large':            we_vote_hosted_profile_image_url_large,
            'voter_photo_url_medium':           we_vote_hosted_profile_image_url_medium,
            'voter_photo_url_tiny':             voter.we_vote_hosted_profile_image_url_tiny,
            'we_vote_hosted_profile_facebook_image_url_large':  voter.we_vote_hosted_profile_facebook_image_url_large,
            'we_vote_hosted_profile_twitter_image_url_large':   voter.we_vote_hosted_profile_twitter_image_url_large,
            'we_vote_hosted_profile_uploaded_image_url_large':  voter.we_vote_hosted_profile_uploaded_image_url_large,
            'we_vote_id':                       voter.we_vote_id,
        }
        return json_data

    else:
        status = results['status']
        json_data = {
            'status':                           status,
            'success':                          False,
            'can_edit_campaignx_owned_by_organization_list': [],
            'date_joined':                      '',
            'voter_device_id':                  voter_device_id,
            'voter_created':                    False,
            'voter_found':                      False,
            'we_vote_id':                       '',
            'facebook_id':                      '',
            'email':                            '',
            'facebook_email':                   '',
            'facebook_profile_image_url_https': '',
            'full_name':                        '',
            'first_name':                       '',
            'last_name':                        '',
            'twitter_screen_name':              '',
            'is_signed_in':                     False,
            'is_admin':                         False,
            'is_analytics_admin':               False,
            'is_partner_organization':          False,
            'is_political_data_manager':        False,
            'is_political_data_viewer':         False,
            'is_verified_volunteer':            False,
            'is_voter_manager':                 False,
            'profile_image_type_currently_active':  '',
            'signed_in':                        False,
            'signed_in_facebook':               False,
            'signed_in_google':                 False,
            'signed_in_twitter':                False,
            'signed_in_with_apple':             False,
            'signed_in_with_email':             False,
            'signed_in_with_sms_phone_number':  False,
            'has_valid_email':                  False,
            'has_data_to_preserve':             False,
            'has_email_with_verified_ownership':    False,
            'linked_organization_we_vote_id':   '',
            'voter_photo_url_large':            '',
            'voter_photo_url_medium':           '',
            'voter_photo_url_tiny':             '',
            'we_vote_hosted_profile_facebook_image_url_large':   '',
            'we_vote_hosted_profile_twitter_image_url_large':    '',
            'we_vote_hosted_profile_uploaded_image_url_large':   '',
            'interface_status_flags':           0,
            'notification_settings_flags':      0,
            'state_code_from_ip_address':       state_code_from_ip_address,
        }
        return json_data


def get_displayable_images(voter, facebook_user):
    # Hack to find any usable voter images.
    # We have too many duplicate image urls setters, repairers, and healers -- some of those setters are broken
    facebook_profile_image_url_https = voter.facebook_profile_image_url_https
    if not positive_value_exists(facebook_profile_image_url_https) and facebook_user is not None:
        facebook_profile_image_url_https = facebook_user.facebook_profile_image_url_https
    we_vote_hosted_profile_image_url_large = voter.we_vote_hosted_profile_image_url_large
    if not positive_value_exists(we_vote_hosted_profile_image_url_large):
        we_vote_hosted_profile_image_url_large = facebook_profile_image_url_https
    we_vote_hosted_profile_image_url_medium = voter.we_vote_hosted_profile_image_url_medium
    if not positive_value_exists(we_vote_hosted_profile_image_url_medium):
        we_vote_hosted_profile_image_url_medium = facebook_profile_image_url_https
    return facebook_profile_image_url_https, we_vote_hosted_profile_image_url_large, \
        we_vote_hosted_profile_image_url_medium


def voter_retrieve_list_for_api(voter_device_id):
    """
    This is used for voterExportView
    :param voter_device_id:
    :return:
    """
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results2 = {
            'success': False,
            'json_data': results['json_data'],
        }
        return results2

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id > 0:
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter_id = results['voter_id']
    else:
        # If we are here, the voter_id could not be found from the voter_device_id
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_RETRIEVE_LIST ",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        results = {
            'success': False,
            'json_data': json_data,
        }
        return results

    if voter_id:
        voter_list = Voter.objects.all()
        voter_list = voter_list.filter(id=voter_id)

        if len(voter_list):
            results = {
                'success': True,
                'voter_list': voter_list,
            }
            return results

    # Trying to mimic the Google Civic error codes scheme
    errors_list = [
        {
            'domain':  "TODO global",
            'reason':  "TODO reason",
            'message':  "TODO Error message here",
            'locationType':  "TODO Error message here",
            'location':  "TODO location",
        }
    ]
    error_package = {
        'errors':   errors_list,
        'code':     400,
        'message':  "Error message here",
    }
    json_data = {
        'error': error_package,
        'status': "VOTER_ID_COULD_NOT_BE_RETRIEVED",
        'success': False,
        'voter_device_id': voter_device_id,
    }
    results = {
        'success': False,
        'json_data': json_data,
    }
    return results


def refresh_voter_primary_email_cached_information_by_email(normalized_email_address):
    """
    Make sure all voter records at all connected to this email address are updated to reflect accurate information
    :param normalized_email_address:
    :return:
    """
    success = True  # Assume success unless we hit a problem
    status = "REFRESH_VOTER_PRIMARY_EMAIL_CACHED_INFORMATION_BY_EMAIL "
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_email(normalized_email_address)
    voter_found_by_email_boolean = False
    voter_found_by_email = Voter()
    if voter_results['voter_found']:
        voter_found_by_email_boolean = True
        voter_found_by_email = voter_results['voter']

    email_manager = EmailManager()
    email_results = email_manager.retrieve_primary_email_with_ownership_verified("", normalized_email_address)
    if email_results['email_address_object_found']:
        verified_email_address_object = email_results['email_address_object']
        if voter_found_by_email_boolean:
            if verified_email_address_object.voter_we_vote_id == voter_found_by_email.we_vote_id:
                status += "EMAIL_TABLE_AND_VOTER_TABLE_VOTER_MATCHES "
                # Make sure the link back to the email_address_object is correct
                try:
                    if voter_found_by_email_boolean:
                        voter_found_by_email.primary_email_we_vote_id = verified_email_address_object.we_vote_id
                        voter_found_by_email.email_ownership_is_verified = True
                        voter_found_by_email.save()
                        status += "ABLE_TO_UPDATE_VOTER_FOUND_BY_EMAIL1 "
                except Exception as e:
                    status = "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL1 "
                    # We already tried to retrieve the email by normalized_email_address, and the only other
                    # required unique value is primary_email_we_vote_id, so we retrieve by that
                    voter_by_primary_email_results = voter_manager.retrieve_voter_by_primary_email_we_vote_id(
                        verified_email_address_object.we_vote_id)
                    if voter_by_primary_email_results['voter_found']:
                        voter_found_by_primary_email_we_vote_id = voter_results['voter']

                        # Wipe this voter...
                        try:
                            voter_found_by_primary_email_we_vote_id.email = None
                            voter_found_by_primary_email_we_vote_id.primary_email_we_vote_id = None
                            voter_found_by_primary_email_we_vote_id.email_ownership_is_verified = False
                            voter_found_by_primary_email_we_vote_id.save()
                            status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID "

                            # ...and now update voter_found_by_email
                            try:
                                # We don't need to check again for voter_found_by_email
                                voter_found_by_email.primary_email_we_vote_id = \
                                    verified_email_address_object.we_vote_id
                                voter_found_by_email.email_ownership_is_verified = True
                                voter_found_by_email.save()
                                status += "ABLE_TO_UPDATE_VOTER_FOUND_BY_EMAIL "
                            except Exception as e:
                                success = False
                                status += "UNABLE_TO_UPDATE_VOTER_FOUND_BY_EMAIL "
                        except Exception as e:
                            success = False
                            status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID "
            else:
                # The voter_we_vote id in the email table doesn't match the voter_we_vote_id
                #  in voter_found_by_email. The email table value is master, so we want to update the voter
                #  record.
                # Wipe this voter...
                try:
                    voter_found_by_voter_we_vote_id2 = None
                    voter_found_by_email.email = None
                    voter_found_by_email.primary_email_we_vote_id = None
                    voter_found_by_email.email_ownership_is_verified = False
                    voter_found_by_email.save()
                    status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL "

                    # ...and now update the voter referenced in the EmailAddress table
                    try:
                        voter_found_by_voter_we_vote_id_results2 = voter_manager.retrieve_voter_by_we_vote_id(
                            verified_email_address_object.voter_we_vote_id)
                        if voter_found_by_voter_we_vote_id_results2['voter_found']:
                            voter_found_by_voter_we_vote_id2 = voter_found_by_voter_we_vote_id_results2['voter']
                            voter_found_by_voter_we_vote_id2.email = \
                                verified_email_address_object.normalized_email_address
                            voter_found_by_voter_we_vote_id2.primary_email_we_vote_id = \
                                verified_email_address_object.we_vote_id
                            voter_found_by_voter_we_vote_id2.email_ownership_is_verified = True
                            voter_found_by_voter_we_vote_id2.save()
                            status += "ABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                        else:
                            # Could not find voter by voter_we_vote_id in EmailAddress table
                            status += "UNABLE_TO_FIND_VOTER_BY_VOTER_WE_VOTE_ID "
                    except Exception as e:
                        status += "UNABLE_TO_UPDATE_VOTER_FOUND_BY_EMAIL "
                        # voter_found_by_voter_we_vote_id2 = None
                        # We tried to update the voter found by the voter_we_vote_id stored in the EmailAddress table,
                        #  but got an error, so assume it was because of a collision with the primary_email_we_vote_id
                        # Here, we retrieve the voter already "claiming" this email entry, so we can wipe the
                        #  email values.
                        voter_by_primary_email_results = voter_manager.retrieve_voter_by_primary_email_we_vote_id(
                            verified_email_address_object.we_vote_id)
                        if voter_by_primary_email_results['voter_found']:
                            voter_found_by_primary_email_we_vote_id2 = voter_results['voter']

                            # Wipe this voter's email values...
                            try:
                                voter_found_by_primary_email_we_vote_id2.email = None
                                voter_found_by_primary_email_we_vote_id2.primary_email_we_vote_id = None
                                voter_found_by_primary_email_we_vote_id2.email_ownership_is_verified = False
                                voter_found_by_primary_email_we_vote_id2.save()
                                status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID2 "

                                # ...and now update voter_found_by_voter_we_vote_id
                                try:
                                    # We don't need to check again for voter_found_by_voter_we_vote_id
                                    voter_found_by_voter_we_vote_id2.primary_email_we_vote_id = \
                                        verified_email_address_object.we_vote_id
                                    voter_found_by_voter_we_vote_id2.email_ownership_is_verified = True
                                    voter_found_by_voter_we_vote_id2.save()
                                    status += "ABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                                except Exception as e:
                                    success = False
                                    status += "UNABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                            except Exception as e:
                                success = False
                                status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID2 "
                except Exception as e:
                    success = False
                    status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL "
        else:
            # If here we need to look up the voter based on the values in the email table
            voter_found_by_voter_we_vote_id_results = voter_manager.retrieve_voter_by_we_vote_id(
                verified_email_address_object.voter_we_vote_id)
            if voter_found_by_voter_we_vote_id_results['voter_found']:
                voter_found_by_voter_we_vote_id = voter_found_by_voter_we_vote_id_results['voter']
                try:
                    voter_found_by_voter_we_vote_id.email = verified_email_address_object.normalized_email_address
                    voter_found_by_voter_we_vote_id.primary_email_we_vote_id = verified_email_address_object.we_vote_id
                    voter_found_by_voter_we_vote_id.email_ownership_is_verified = True
                    voter_found_by_voter_we_vote_id.save()
                    status += "ABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                except Exception as e:
                    status = "UNABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                    # We already tried to retrieve the email by normalized_email_address, and the only other
                    # required unique value is primary_email_we_vote_id, so we retrieve by that
                    voter_by_primary_email_results = voter_manager.retrieve_voter_by_primary_email_we_vote_id(
                        verified_email_address_object.we_vote_id)
                    if voter_by_primary_email_results['voter_found']:
                        voter_found_by_primary_email_we_vote_id2 = voter_results['voter']

                        # Wipe this voter...
                        try:
                            voter_found_by_primary_email_we_vote_id2.email = None
                            voter_found_by_primary_email_we_vote_id2.primary_email_we_vote_id = None
                            voter_found_by_primary_email_we_vote_id2.email_ownership_is_verified = False
                            voter_found_by_primary_email_we_vote_id2.save()
                            status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID2 "

                            # ...and now update voter_found_by_voter_we_vote_id
                            try:
                                # We don't need to check again for voter_found_by_voter_we_vote_id
                                voter_found_by_voter_we_vote_id.primary_email_we_vote_id = \
                                    verified_email_address_object.we_vote_id
                                voter_found_by_voter_we_vote_id.email_ownership_is_verified = True
                                voter_found_by_voter_we_vote_id.save()
                                status += "ABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                            except Exception as e:
                                success = False
                                status += "UNABLE_TO_UPDATE_VOTER_FOUND_BY_VOTER_WE_VOTE_ID "
                        except Exception as e:
                            success = False
                            status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID2 "

    else:
        # Email address was not found. As long as "success" is true, we want to make sure the voter found has the
        #  email address removed.
        if positive_value_exists(email_results['success']):
            # Make sure no voter's think they are using this email address
            # Remove the email information, so we don't have a future conflict
            try:
                if voter_found_by_email_boolean:
                    voter_found_by_email.email = None
                    voter_found_by_email.primary_email_we_vote_id = None
                    voter_found_by_email.email_ownership_is_verified = False
                    voter_found_by_email.save()
                    status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL2 "
                else:
                    status += "NO_VOTER_FOUND_BY_EMAIL "
            except Exception as e:
                success = False
                status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL2 "
        else:
            status += "PROBLEM_RETRIEVING_EMAIL_ADDRESS_OBJECT"

    results = {
        'success':  success,
        'status':   status,
    }
    return results


def refresh_voter_primary_email_cached_information_by_voter_we_vote_id(voter_we_vote_id):
    """
    Make sure this voter record has accurate cached email information.
    :param voter_we_vote_id:
    :return:
    """
    results = {
        'success':  False,
        'status':   "TO_BE_IMPLEMENTED",
    }
    return results


def voter_save_photo_from_file_reader(
        voter_we_vote_id='',
        voter_photo_binary_file=None,
        voter_photo_from_file_reader=None):
    image_data_found = False
    python_image_library_image = None
    status = ""
    success = True
    we_vote_hosted_voter_photo_original_url = ''

    if not positive_value_exists(voter_we_vote_id):
        status += "MISSING_VOTER_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_voter_photo_original_url': we_vote_hosted_voter_photo_original_url,
        }
        return results

    if not positive_value_exists(voter_photo_from_file_reader) and not positive_value_exists(voter_photo_binary_file):
        status += "MISSING_VOTER_PHOTO_FROM_FILE_READER "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_voter_photo_original_url': we_vote_hosted_voter_photo_original_url,
        }
        return results

    if not voter_photo_binary_file:
        try:
            img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                                voter_photo_from_file_reader).groupdict()
            if img_dict['encoding'] == 'base64':
                voter_photo_binary_file = img_dict['data']
            else:
                status += "INCOMING_VOTER_PHOTO_LARGE-BASE64_NOT_FOUND "
        except Exception as e:
            status += "PROBLEM_EXTRACTING_BINARY_DATA_FROM_INCOMING_VOTER_DATA: {error}".format(error=e)

    if voter_photo_binary_file:
        try:
            byte_data = base64.b64decode(voter_photo_binary_file)
            image_data = BytesIO(byte_data)
            original_image = Image.open(image_data)
            format_to_cache = original_image.format
            python_image_library_image = ImageOps.exif_transpose(original_image)
            python_image_library_image.thumbnail(
                (PROFILE_IMAGE_ORIGINAL_MAX_WIDTH, PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT), Image.Resampling.LANCZOS)
            python_image_library_image.format = format_to_cache
            image_data_found = True
        except Exception as e:
            status += "PROBLEM_EXTRACTING_PHOTO_FROM_BINARY_DATA: {error}".format(error=e)

    if image_data_found:
        cache_results = cache_voter_master_uploaded_image(
            python_image_library_image=python_image_library_image,
            voter_we_vote_id=voter_we_vote_id)
        status += cache_results['status']
        if cache_results['success']:
            cached_master_we_vote_image = cache_results['we_vote_image']
            try:
                we_vote_hosted_voter_photo_original_url = cached_master_we_vote_image.we_vote_image_url
            except Exception as e:
                status += "FAILED_TO_CACHE_VOTER_IMAGE: " + str(e) + ' '
                success = False
        else:
            success = False
    results = {
        'status':                   status,
        'success':                  success,
        'we_vote_hosted_voter_photo_original_url': we_vote_hosted_voter_photo_original_url,
    }
    return results


def voter_sign_out_for_api(voter_device_id, sign_out_all_devices=False):  # voterSignOut
    """
    This gives us a chance to clean up some data
    :param voter_device_id:
    :param sign_out_all_devices:
    :return:
    """
    status = ""

    voter_device_link_manager = VoterDeviceLinkManager()

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if results['voter_found']:
        voter_signing_out = results['voter']
        if positive_value_exists(voter_signing_out.email):
            refresh_results = refresh_voter_primary_email_cached_information_by_email(voter_signing_out.email)
            status += refresh_results['status']
        elif positive_value_exists(voter_signing_out.primary_email_we_vote_id):
            email_manager = EmailManager()
            email_results = email_manager.retrieve_email_address_object("", voter_signing_out.primary_email_we_vote_id)
            if email_results['email_address_object_found']:
                email_address_object = email_results['email_address_object']
                if positive_value_exists(email_address_object.normalized_email_address):
                    refresh_results = refresh_voter_primary_email_cached_information_by_email(
                        email_address_object.normalized_email_address)
                    status += refresh_results['status']

    if positive_value_exists(sign_out_all_devices):
        results = voter_device_link_manager.delete_all_voter_device_links(voter_device_id)
    else:
        results = voter_device_link_manager.delete_voter_device_link(voter_device_id)
    status += results['status']

    results = {
        'success':  results['success'],
        'status':   status,
    }
    return results


def voter_split_into_two_accounts_for_api(voter_device_id, split_off_twitter):  # voterSplitIntoTwoAccounts
    """

    :param voter_device_id:
    :param split_off_twitter: Create a new account separate from this one, that we can log into later
    :return:
    """
    success = False
    status = ""
    repair_twitter_related_voter_caching_now = False
    repair_twitter_related_organization_caching_now = False

    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        error_results = {
            'status':               voter_device_link_results['status'],
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=False)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':               "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    current_voter = voter_results['voter']

    if not positive_value_exists(split_off_twitter):
        error_results = {
            'status':               "VOTER_SPLIT_INTO_TWO_ACCOUNTS_TWITTER_NOT_PASSED_IN",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    # Make sure this voter has a TwitterLinkToVoter entry
    twitter_user_manager = TwitterUserManager()
    twitter_id = 0
    twitter_link_to_current_voter_results = twitter_user_manager.retrieve_twitter_link_to_voter(
        twitter_id, current_voter.we_vote_id)
    if not twitter_link_to_current_voter_results['twitter_link_to_voter_found']:
        error_results = {
            'status':               "VOTER_SPLIT_INTO_TWO_ACCOUNTS_TWITTER_LINK_TO_VOTER_NOT_FOUND",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    # Make sure this voter has another way to sign in once twitter is split off
    if current_voter.signed_in_facebook() or current_voter.signed_in_with_email():
        status += "CONFIRMED-VOTER_HAS_ANOTHER_WAY_TO_SIGN_IN "
    else:
        error_results = {
            'status':               "VOTER_SPLIT_INTO_TWO_ACCOUNTS-NO_OTHER_WAY_TO_SIGN_IN",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    current_voter_id = current_voter.id
    current_voter_we_vote_id = current_voter.we_vote_id
    split_off_voter = Voter
    split_off_voter_id = 0
    split_off_voter_we_vote_id = ""

    # Make sure we start the process with a current_voter_organization and correct TwitterLinkToVoter
    # and TwitterLinkToOrganization entries
    organization_manager = OrganizationManager()
    repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(current_voter)
    if repair_results['voter_repaired']:
        current_voter = repair_results['voter']

    # Temporarily store Twitter values from current_voter
    split_off_twitter_voters_access_token = current_voter.twitter_voters_access_token
    split_off_twitter_voters_access_token_secret = current_voter.twitter_voters_access_token_secret
    split_off_twitter_connection_active = current_voter.twitter_connection_active
    split_off_twitter_id = current_voter.twitter_id
    split_off_twitter_request_token = current_voter.twitter_request_token
    split_off_twitter_request_secret = current_voter.twitter_request_secret
    split_off_twitter_screen_name = current_voter.twitter_screen_name

    # Create a duplicate voter that we can split off for Twitter
    voter_duplicate_results = voter_manager.duplicate_voter(current_voter)
    if not voter_duplicate_results['voter_duplicated']:
        status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS_NEW_VOTER_NOT_DUPLICATED "
    else:
        split_off_voter = voter_duplicate_results['voter']
        split_off_voter_id = split_off_voter.id
        split_off_voter_we_vote_id = split_off_voter.we_vote_id

        # Make sure we remove any legacy of Twitter
        try:
            current_voter.twitter_voters_access_token = None
            current_voter.twitter_voters_access_token_secret = None
            current_voter.twitter_connection_active = False
            current_voter.twitter_id = None
            current_voter.twitter_request_token = None
            current_voter.twitter_request_secret = None
            current_voter.twitter_screen_name = None
            current_voter.save()
        except Exception as e:
            status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS-CURRENT_VOTER_TWITTER_VALUES_NOT_REMOVED "

        # And now update split_off_voter with the twitter values originally in current_voter
        try:
            split_off_voter.twitter_voters_access_token = split_off_twitter_voters_access_token
            split_off_voter.twitter_voters_access_token_secret = split_off_twitter_voters_access_token_secret
            split_off_voter.twitter_connection_active = split_off_twitter_connection_active
            split_off_voter.twitter_id = split_off_twitter_id
            split_off_voter.twitter_request_token = split_off_twitter_request_token
            split_off_voter.twitter_request_secret = split_off_twitter_request_secret
            split_off_voter.twitter_screen_name = split_off_twitter_screen_name
            split_off_voter.save()
        except Exception as e:
            status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS-SPLIT_OFF_VOTER_TWITTER_VALUES_NOT_UPDATED "

    if not positive_value_exists(split_off_voter_we_vote_id):
        error_results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'split_off_twitter':            split_off_twitter,
        }
        return error_results

    # Move TwitterLinkToVoter to the new voter "split_off_voter"
    twitter_link_moved = False
    twitter_link_to_split_off_voter = twitter_link_to_current_voter_results['twitter_link_to_voter']
    twitter_link_to_split_off_voter_twitter_id = twitter_link_to_split_off_voter.twitter_id
    try:
        twitter_link_to_split_off_voter.voter_we_vote_id = split_off_voter.we_vote_id
        twitter_link_to_split_off_voter.save()
        repair_twitter_related_voter_caching_now = True
        twitter_link_moved = True
    except Exception as e:
        status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS_TWITTER_LINK_TO_VOTER_NOT_CREATED "

    if not twitter_link_moved:
        error_results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'split_off_twitter':            split_off_twitter,
        }
        return error_results

    # The facebook link should not require a change, since this link should still be to the current_voter
    # facebook_manager = FacebookManager()
    # facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(0, current_voter.we_vote_id)
    # if facebook_link_results['facebook_link_to_voter_found']:
    #     facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']

    # Get the organization linked to the twitter_id
    # Next, link that organization connected to the Twitter account to the split_off_voter
    # Then duplicate that org, and connect the duplicate to the current_voter
    organization_manager = OrganizationManager()
    twitter_link_to_current_organization = None
    twitter_link_to_current_organization_exists = False
    twitter_link_to_current_organization_moved = False
    split_off_voter_linked_organization_id = 0
    split_off_voter_linked_organization_we_vote_id = ""
    current_voter_linked_organization = None
    current_voter_linked_organization_id = 0
    current_voter_linked_organization_we_vote_id = current_voter.linked_organization_we_vote_id

    twitter_organization_name = ""
    if positive_value_exists(twitter_link_to_split_off_voter_twitter_id):
        twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_link_to_split_off_voter_twitter_id)
        if twitter_user_results['twitter_user_found']:
            twitter_user = twitter_user_results['twitter_user']
            twitter_organization_name = twitter_user.twitter_name

    # We want to isolate the twitter_link_to_organization entry
    twitter_link_to_current_organization_results = \
        twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
            twitter_link_to_split_off_voter_twitter_id)
    if twitter_link_to_current_organization_results['twitter_link_to_organization_found']:
        # We have a Twitter link to this organization
        twitter_link_to_current_organization = \
            twitter_link_to_current_organization_results['twitter_link_to_organization']
        twitter_link_to_current_organization_exists = True
        organization_associated_with_twitter_id_we_vote_id = \
            twitter_link_to_current_organization.organization_we_vote_id
        twitter_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            organization_associated_with_twitter_id_we_vote_id)
        if twitter_organization_results['organization_found']:
            # Error checking successful. The existing organization that is tied to this twitter_id will be put in
            #  the "current_voter" and we will duplicate an organization for use with the Twitter account
            current_voter_linked_organization = twitter_organization_results['organization']
            current_voter_linked_organization_id = current_voter_linked_organization.id
            current_voter_linked_organization_we_vote_id = current_voter_linked_organization.we_vote_id
        else:
            status += "NO_LINKED_ORGANIZATION_FOUND "
            # Create new organization
            # Update the twitter_link_to_current_organization with new organization_we_vote_id
            create_results = organization_manager.create_organization(
                organization_name=current_voter.get_full_name(),
                organization_image=current_voter.voter_photo_url(),
                organization_type=INDIVIDUAL,
                we_vote_hosted_profile_image_url_large=current_voter.we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=current_voter.we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=current_voter.we_vote_hosted_profile_image_url_tiny
            )
            if create_results['organization_created']:
                current_voter_linked_organization = create_results['organization']
                current_voter_linked_organization_id = current_voter_linked_organization.id
                current_voter_linked_organization_we_vote_id = current_voter_linked_organization.we_vote_id
    elif positive_value_exists(current_voter_linked_organization_we_vote_id):
        # Retrieve organization based on current_voter_linked_organization_we_vote_id
        current_voter_linked_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            current_voter_linked_organization_we_vote_id)
        if current_voter_linked_organization_results['organization_found']:
            current_voter_linked_organization = current_voter_linked_organization_results['organization']
            current_voter_linked_organization_id = current_voter_linked_organization.id
            current_voter_linked_organization_we_vote_id = current_voter_linked_organization.we_vote_id

    if not positive_value_exists(current_voter_linked_organization_we_vote_id):
        # If for some reason there isn't an organization tied to the Twitter account, create a new organization
        # for the split_off_voter
        status += "NO_LINKED_ORGANIZATION_WE_VOTE_ID_FOUND "
        create_results = organization_manager.create_organization(
            organization_name=current_voter.get_full_name(),
            organization_image=current_voter.voter_photo_url(),
            organization_type=INDIVIDUAL,
            we_vote_hosted_profile_image_url_large=current_voter.we_vote_hosted_profile_image_url_large,
            we_vote_hosted_profile_image_url_medium=current_voter.we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny=current_voter.we_vote_hosted_profile_image_url_tiny
        )
        if create_results['organization_created']:
            current_voter_linked_organization = create_results['organization']
            current_voter_linked_organization_id = current_voter_linked_organization.id
            current_voter_linked_organization_we_vote_id = current_voter_linked_organization.we_vote_id

    if positive_value_exists(current_voter_linked_organization_we_vote_id):
        # Now that we have the organization linked to the Twitter account, we want to duplicate it,
        #  and then remove data that shouldn't be in both

        # Start by saving aside the Twitter-related values
        split_off_organization_twitter_handle = current_voter_linked_organization.organization_twitter_handle
        split_off_twitter_description = current_voter_linked_organization.twitter_description
        split_off_twitter_followers_count = current_voter_linked_organization.twitter_followers_count
        split_off_twitter_location = current_voter_linked_organization.twitter_location
        split_off_twitter_user_id = current_voter_linked_organization.twitter_user_id

        duplicate_organization_results = organization_manager.duplicate_organization(
            current_voter_linked_organization)
        if not duplicate_organization_results['organization_duplicated']:
            status += "NOT_ABLE_TO_DUPLICATE_ORGANIZATION: " + duplicate_organization_results['status']
        else:
            split_off_voter_linked_organization = duplicate_organization_results['organization']
            split_off_voter_linked_organization_id = split_off_voter_linked_organization.id
            split_off_voter_linked_organization_we_vote_id = split_off_voter_linked_organization.we_vote_id

            if positive_value_exists(split_off_voter_linked_organization_we_vote_id):
                # Remove the Twitter information from the current_voter_linked_organization
                # and update the name to be voter focused
                try:
                    current_voter_linked_organization.organization_name = current_voter.get_full_name()
                    current_voter_linked_organization.organization_twitter_handle = None
                    current_voter_linked_organization.twitter_description = None
                    current_voter_linked_organization.twitter_user_id = 0
                    current_voter_linked_organization.twitter_followers_count = 0
                    current_voter_linked_organization.twitter_location = None
                    current_voter_linked_organization.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_FROM_ORGANIZATION: " + str(e) + " "

                # Update the link to the organization on the split_off_voter, and other Twitter values
                try:
                    split_off_voter.linked_organization_we_vote_id = split_off_voter_linked_organization_we_vote_id
                    split_off_voter.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_WE_VOTE_ID_IN_TO_VOTER "

                # Update the TwitterLinkToOrganization to the organization on the split_off_voter
                if twitter_link_to_current_organization_exists:
                    try:
                        twitter_link_to_current_organization.organization_we_vote_id = \
                            split_off_voter_linked_organization_we_vote_id
                        twitter_link_to_current_organization.save()
                        repair_twitter_related_organization_caching_now = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_TWITTER_LINK_TO_ORGANIZATION "
                else:
                    results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_link_to_split_off_voter_twitter_id, split_off_voter_linked_organization_we_vote_id)
                    status += results['status']
                    if results['twitter_link_to_organization_found']:
                        twitter_link_to_current_organization = results['twitter_link_to_organization']
                        repair_twitter_related_organization_caching_now = True

                # Update the link to the organization on the current_voter
                try:
                    current_voter.linked_organization_we_vote_id = current_voter_linked_organization_we_vote_id
                    current_voter.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_WE_VOTE_ID_IN_FROM_VOTER "
                    # Clear out all other voters
                    voter_manager.clear_out_collisions_for_linked_organization_we_vote_id(
                        current_voter.we_vote_id,
                        current_voter_linked_organization_we_vote_id)
                    try:
                        current_voter.linked_organization_we_vote_id = current_voter_linked_organization_we_vote_id
                        current_voter.save()
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_WE_VOTE_ID_IN_FROM_VOTER2 "

                # Update the organization with the Twitter values
                try:
                    split_off_voter_linked_organization.organization_name = twitter_organization_name
                    split_off_voter_linked_organization.organization_twitter_handle = \
                        split_off_organization_twitter_handle
                    split_off_voter_linked_organization.twitter_description = split_off_twitter_description
                    split_off_voter_linked_organization.twitter_followers_count = split_off_twitter_followers_count
                    split_off_voter_linked_organization.twitter_location = split_off_twitter_location
                    split_off_voter_linked_organization.twitter_user_id = split_off_twitter_user_id
                    split_off_voter_linked_organization.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_TO_SPLIT_OFF_VOTER_ORGANIZATION "

                twitter_link_to_current_organization_moved = True

    if not twitter_link_to_current_organization_moved:
        error_results = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'split_off_twitter': split_off_twitter,
        }
        return error_results

    if repair_twitter_related_voter_caching_now:
        # And make sure we don't have multiple voters using same twitter_id (once there is a TwitterLinkToVoter)
        repair_results = voter_manager.repair_twitter_related_voter_caching(
            twitter_link_to_split_off_voter.twitter_id)
        status += repair_results['status']

    # Make sure to clean up the twitter information in the organization table
    if repair_twitter_related_organization_caching_now:
        organization_list_manager = OrganizationListManager()
        repair_results = organization_list_manager.repair_twitter_related_organization_caching(
            twitter_link_to_current_organization.twitter_id)
        status += repair_results['status']

    # Duplicate VoterAddress (we are not currently bringing over ballot_items)
    voter_address_manager = VoterAddressManager()
    duplicate_voter_address_results = \
        voter_address_manager.duplicate_voter_address_from_voter_id(current_voter_id, split_off_voter_id)
    status += " " + duplicate_voter_address_results['status']

    # If anyone is following current_voter's organization, move those followers to the split_off_voter's organization
    move_organization_followers_results = duplicate_organization_followers_to_another_organization(
        current_voter_linked_organization_id, current_voter_linked_organization_we_vote_id,
        split_off_voter_linked_organization_id, split_off_voter_linked_organization_we_vote_id)
    status += " " + move_organization_followers_results['status']

    # If current_voter is following organizations, copy the follow_organization entries to the split_off_voter
    duplicate_follow_entries_results = duplicate_follow_entries_to_another_voter(
        current_voter_id, current_voter_we_vote_id, split_off_voter_id, split_off_voter_we_vote_id)
    status += " " + duplicate_follow_entries_results['status']

    # If current_voter is following issues, copy the follow_issue entries to the split_off_voter
    duplicate_follow_issue_entries_results = duplicate_follow_issue_entries_to_another_voter(
        current_voter_we_vote_id, split_off_voter_we_vote_id)
    status += " " + duplicate_follow_issue_entries_results['status']

    # If current_voter has any position, duplicate positions current_voter to split_off_voter
    move_positions_results = duplicate_positions_to_another_voter(
        current_voter_id, current_voter_we_vote_id,
        split_off_voter_id, split_off_voter_we_vote_id,
        split_off_voter_linked_organization_id, split_off_voter_linked_organization_we_vote_id)
    status += " " + move_positions_results['status']

    # We do not transfer friends or friend invitations from from_voter to to_voter

    # Duplicate and repair both voter guides to have updated names and photos
    voter_guide_results = duplicate_voter_guides(
        current_voter_id, current_voter_we_vote_id, current_voter_linked_organization_we_vote_id,
        split_off_voter_id, split_off_voter_we_vote_id, split_off_voter_linked_organization_we_vote_id)
    status += " " + voter_guide_results['status']

    # We do not bring over all emails from the current_voter over to the split_off_voter

    # We do not bring over Facebook information

    # We do not duplicate any donations that have been made

    results = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'split_off_twitter': split_off_twitter,
    }

    return results
