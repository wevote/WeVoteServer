# voter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from .models import BALLOT_ADDRESS, fetch_voter_id_from_voter_device_link, Voter, VoterAddressManager, \
    VoterDeviceLinkManager, VoterManager
from django.http import HttpResponse
from email_outbound.controllers import move_email_address_entries_to_another_voter
from email_outbound.models import EmailManager
from follow.controllers import duplicate_follow_entries_to_another_voter, move_follow_entries_to_another_voter, \
    duplicate_organization_followers_to_another_organization
from friend.controllers import fetch_friend_invitation_recipient_voter_we_vote_id, friend_accepted_invitation_send, \
    move_friend_invitations_to_another_voter, move_friends_to_another_voter
from friend.models import FriendManager
from image.controllers import cache_original_and_resized_image, TWITTER, FACEBOOK
from import_export_facebook.models import FacebookManager
from import_export_twitter.models import TwitterAuthManager
import json
from organization.controllers import move_organization_to_another_complete
from organization.models import OrganizationListManager, OrganizationManager
from position.controllers import duplicate_positions_to_another_voter, move_positions_to_another_voter
from position.models import PositionListManager
from twitter.models import TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from voter_guide.controllers import duplicate_voter_guides
import wevote_functions.admin
from wevote_functions.functions import generate_voter_device_id, is_voter_device_id_valid, positive_value_exists
from donate.controllers import donation_history_for_a_voter, move_donation_info_to_another_voter


logger = wevote_functions.admin.get_logger(__name__)


def merge_voter_accounts(from_voter, to_voter):
    status = "MOVE_VOTER_TABLE_INFO "  # Deal with situation where destination account already has facebook_id
    success = False

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_VOTER_INFO_MISSING_FROM_OR_TO_VOTER_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    # Transfer data in voter records
    # first_name
    # middle_name
    # last_name
    # interface_status_flags
    # is_admin
    # is_verified_volunteer
    # primary_email_we_vote_id

    # Is there data we should migrate?
    if positive_value_exists(from_voter.first_name) or positive_value_exists(from_voter.middle_name) \
            or positive_value_exists(from_voter.last_name) \
            or positive_value_exists(from_voter.interface_status_flags) \
            or positive_value_exists(from_voter.notification_settings_flags) \
            or positive_value_exists(from_voter.is_admin) or positive_value_exists(from_voter.is_verified_volunteer) \
            or positive_value_exists(from_voter.primary_email_we_vote_id):
        from_voter_data_to_migrate_exists = True
    else:
        from_voter_data_to_migrate_exists = False
    if from_voter_data_to_migrate_exists:
        # Remove info from the from_voter and then move Twitter info to the to_voter
        try:
            # Now move values to new entry and save if the to_voter doesn't have any data
            if positive_value_exists(from_voter.first_name) and not positive_value_exists(to_voter.first_name):
                to_voter.first_name = from_voter.first_name
            if positive_value_exists(from_voter.middle_name) and not positive_value_exists(to_voter.middle_name):
                to_voter.middle_name = from_voter.middle_name
            if positive_value_exists(from_voter.last_name) and not positive_value_exists(to_voter.last_name):
                to_voter.last_name = from_voter.last_name
            # Set all bits that have a value in either from_voter or to_voter
            to_voter.interface_status_flags = to_voter.interface_status_flags | from_voter.interface_status_flags
            to_voter.notification_settings_flags = \
                to_voter.notification_settings_flags | from_voter.notification_settings_flags
            if positive_value_exists(from_voter.is_admin) and not positive_value_exists(to_voter.is_admin):
                to_voter.is_admin = from_voter.is_admin
            if positive_value_exists(from_voter.is_verified_volunteer) \
                    and not positive_value_exists(to_voter.is_verified_volunteer):
                to_voter.is_verified_volunteer = from_voter.is_verified_volunteer
            if positive_value_exists(from_voter.primary_email_we_vote_id) \
                    and not positive_value_exists(to_voter.primary_email_we_vote_id):
                to_voter.primary_email_we_vote_id = from_voter.primary_email_we_vote_id
            to_voter.save()
            status += "TO_VOTER_MERGE_SAVED "
        except Exception as e:
            # Fail silently
            status += "TO_VOTER_MERGE_SAVE_FAILED "

    else:
        success = True
        status += "FROM_VOTER_DATA_TO_MIGRATE_NOT_FOUND "

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'to_voter': to_voter,
    }
    return results


def move_facebook_info_to_another_voter(from_voter, to_voter):
    status = "MOVE_FACEBOOK_INFO "  # Deal with situation where destination account already has facebook_id
    success = False

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_FACEBOOK_INFO_MISSING_FROM_OR_TO_VOTER_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    facebook_manager = FacebookManager()
    to_voter_facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        to_voter.we_vote_id)
    # if to_voter_facebook_results['facebook_link_to_voter_found']:
    #     to_voter_facebook_link = to_voter_facebook_results['facebook_link_to_voter']
    from_voter_facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        from_voter.we_vote_id)

    # Move facebook_link_to_voter
    if to_voter_facebook_results['facebook_link_to_voter_found']:
        # Don't try to move from the from_voter
        success = True
        status += "TO_VOTER_ALREADY_HAS_FACEBOOK_LINK "
    elif from_voter_facebook_results['facebook_link_to_voter_found']:
        from_voter_facebook_link = from_voter_facebook_results['facebook_link_to_voter']
        try:
            from_voter_facebook_link.voter_we_vote_id = to_voter.we_vote_id
            from_voter_facebook_link.save()
            success = True
            status += "FROM_VOTER_FACEBOOK_LINK_MOVED "
        except Exception as e:
            status += "FROM_VOTER_FACEBOOK_LINK_COULD_NOT_BE_MOVED "
    elif positive_value_exists(from_voter.facebook_id):
        create_results = facebook_manager.create_facebook_link_to_voter(from_voter.facebook_id, to_voter.we_vote_id)
        status += " " + create_results['status']

    # Transfer data in voter records
    temp_facebook_email = ""
    temp_facebook_id = 0
    temp_facebook_profile_image_url_https = ""
    temp_fb_username = None
    if positive_value_exists(to_voter.facebook_id):
        # Don't try to move from the from_voter
        success = True
        status += "TO_VOTER_ALREADY_HAS_FACEBOOK_ID "
    elif positive_value_exists(from_voter.facebook_id):
        # Remove info from the from_voter and then move facebook info to the to_voter
        try:
            # Copy values
            temp_facebook_email = from_voter.facebook_email
            temp_facebook_id = from_voter.facebook_id
            temp_facebook_profile_image_url_https = from_voter.facebook_profile_image_url_https
            temp_fb_username = from_voter.fb_username
            # Now delete it and save so we can save the unique facebook_id in the to_voter
            from_voter.facebook_email = ""
            from_voter.facebook_id = 0
            from_voter.facebook_profile_image_url_https = ""
            from_voter.fb_username = None
            from_voter.save()
            status += "FROM_VOTER_FACEBOOK_DATA_REMOVED "
        except Exception as e:
            status += "FROM_VOTER_FACEBOOK_DATA_COULD_NOT_BE_REMOVED "

        try:
            # Now move values to new entry and save
            to_voter.facebook_email = temp_facebook_email
            to_voter.facebook_id = temp_facebook_id
            to_voter.facebook_profile_image_url_https = temp_facebook_profile_image_url_https
            to_voter.fb_username = temp_fb_username
            to_voter.save()
            status += "TO_VOTER_FACEBOOK_DATA_SAVED "
        except Exception as e:
            status += "TO_VOTER_FACEBOOK_DATA_COULD_NOT_BE_SAVED "

    else:
        success = True
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
    success = False

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += "MOVE_TWITTER_INFO_MISSING_FROM_OR_TO_VOTER_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    twitter_user_manager = TwitterUserManager()
    to_voter_twitter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        to_voter.we_vote_id)
    from_voter_twitter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        from_voter.we_vote_id)

    # Move twitter_link_to_voter
    if to_voter_twitter_results['twitter_link_to_voter_found']:
        if from_voter_twitter_results['twitter_link_to_voter_found']:
            success = False
            status += "FROM_AND_TO_VOTER_BOTH_HAVE_TWITTER_LINKS "
        else:
            success = True
            status += "TO_VOTER_ALREADY_HAS_TWITTER_LINK "
    elif from_voter_twitter_results['twitter_link_to_voter_found']:
        from_voter_twitter_link = from_voter_twitter_results['twitter_link_to_voter']
        try:
            from_voter_twitter_link.voter_we_vote_id = to_voter.we_vote_id
            from_voter_twitter_link.save()
            success = True
            status += "FROM_VOTER_TWITTER_LINK_MOVED "
        except Exception as e:
            # Fail silently
            status += "FROM_VOTER_TWITTER_LINK_NOT_MOVED "
    elif positive_value_exists(from_voter.twitter_id):
        # If this is the only voter with twitter_id, heal the data and create a TwitterLinkToVoter entry
        voter_manager = VoterManager()
        duplicate_twitter_results = voter_manager.retrieve_voter_by_twitter_id_old(from_voter.twitter_id)
        if duplicate_twitter_results['voter_found']:
            # If here, we know that this was the only voter with this twitter_id
            test_duplicate_voter = duplicate_twitter_results['voter']
            if test_duplicate_voter.we_vote_id == from_voter.we_vote_id:
                create_results = twitter_user_manager.create_twitter_link_to_voter(from_voter.twitter_id,
                                                                                   to_voter.we_vote_id)
                status += " " + create_results['status']
                # We remove from_voter.twitter_id value below

    # Transfer data in voter records
    temp_twitter_id = 0
    temp_twitter_name = ""
    temp_twitter_profile_image_url_https = ""
    temp_twitter_screen_name = ""
    if positive_value_exists(to_voter.twitter_id):
        # Don't try to move from the from_voter
        success = True
        status += "TO_VOTER_ALREADY_HAS_TWITTER_ID "
    elif positive_value_exists(from_voter.twitter_id):
        # Remove info from the from_voter and then move Twitter info to the to_voter
        try:
            # Copy values
            temp_twitter_id = from_voter.twitter_id
            temp_twitter_name = from_voter.twitter_name
            temp_twitter_profile_image_url_https = from_voter.twitter_profile_image_url_https
            temp_twitter_screen_name = from_voter.twitter_screen_name
            # Now delete it and save so we can save the unique facebook_id in the to_voter
            from_voter.twitter_id = None
            from_voter.twitter_name = ""
            from_voter.twitter_profile_image_url_https = ""
            from_voter.twitter_screen_name = ""
            from_voter.save()
            status += "FROM_VOTER_TWITTER_DATA_REMOVED "
        except Exception as e:
            # Fail silently
            status += "FROM_VOTER_TWITTER_DATA_NOT_REMOVED "

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

    voter_address_manager = VoterAddressManager()
    results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)

    if results['voter_address_found']:
        voter_address = results['voter_address']
        status = "VOTER_ADDRESS_RETRIEVE-ADDRESS_FOUND"

        voter_address_retrieve_results = {
            'voter_device_id': voter_device_id,
            'address_type': voter_address.address_type if voter_address.address_type else '',
            'text_for_map_search': voter_address.text_for_map_search if voter_address.text_for_map_search else '',
            'google_civic_election_id': voter_address.google_civic_election_id if voter_address.google_civic_election_id
            else 0,
            'latitude': voter_address.latitude if voter_address.latitude else '',
            'longitude': voter_address.longitude if voter_address.longitude else '',
            'normalized_line1': voter_address.normalized_line1 if voter_address.normalized_line1 else '',
            'normalized_line2': voter_address.normalized_line2 if voter_address.normalized_line2 else '',
            'normalized_city': voter_address.normalized_city if voter_address.normalized_city else '',
            'normalized_state': voter_address.normalized_state if voter_address.normalized_state else '',
            'normalized_zip': voter_address.normalized_zip if voter_address.normalized_zip else '',
            'address_found': True,
            'success': True,
            'status': status,
        }
        return voter_address_retrieve_results
    else:
        voter_address_retrieve_results = {
            'status': "VOTER_ADDRESS_NOT_FOUND",
            'success': False,
            'address_found': False,
            'voter_device_id': voter_device_id,
            'address_type': '',
            'text_for_map_search': '',
            'google_civic_election_id': 0,
            'latitude': '',
            'longitude': '',
            'normalized_line1': '',
            'normalized_line2': '',
            'normalized_city': '',
            'normalized_state': '',
            'normalized_zip': '',
        }
        return voter_address_retrieve_results


# No longer in use
# def voter_address_save_for_api(voter_device_id, voter_id, address_raw_text):
#     # At this point, we have a valid voter
#
#     voter_address_manager = VoterAddressManager()
#     address_type = BALLOT_ADDRESS
#
#     # We wrap get_or_create because we want to centralize error handling
#     results = voter_address_manager.update_or_create_voter_address(voter_id, address_type, address_raw_text.strip())
#
#     if results['success']:
#         if positive_value_exists(address_raw_text):
#             status = "VOTER_ADDRESS_SAVED"
#         else:
#             status = "VOTER_ADDRESS_EMPTY_SAVED"
#
#         results = {
#                 'status': status,
#                 'success': True,
#                 'voter_device_id': voter_device_id,
#                 'text_for_map_search': address_raw_text,
#             }
#     # elif results['status'] == 'MULTIPLE_MATCHING_ADDRESSES_FOUND':
#         # delete all currently matching addresses and save again
#     else:
#         results = {
#                 'status': results['status'],
#                 'success': False,
#                 'voter_device_id': voter_device_id,
#                 'text_for_map_search': address_raw_text,
#             }
#     return results


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
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
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


def voter_merge_two_accounts_for_api(  # voterMergeTwoAccounts
        voter_device_id, email_secret_key, facebook_secret_key, twitter_secret_key, invitation_secret_key):
    current_voter_found = False
    email_owner_voter_found = False
    facebook_owner_voter_found = False
    twitter_owner_voter_found = False
    invitation_owner_voter_found = False
    new_owner_voter = Voter()
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
        }
        return error_results

    # We need this below
    voter_device_link = voter_device_link_results['voter_device_link']

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                       "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'current_voter_found':          current_voter_found,
            'email_owner_voter_found':      email_owner_voter_found,
            'facebook_owner_voter_found':   facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
        }
        return error_results

    voter = voter_results['voter']
    current_voter_found = True

    if not positive_value_exists(email_secret_key) \
            and not positive_value_exists(facebook_secret_key) \
            and not positive_value_exists(twitter_secret_key) \
            and not positive_value_exists(invitation_secret_key):
        error_results = {
            'status':                       "VOTER_SPLIT_INTO_TWO_ACCOUNTS_SECRET_KEY_NOT_PASSED_IN",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'current_voter_found':          current_voter_found,
            'email_owner_voter_found':      email_owner_voter_found,
            'facebook_owner_voter_found':   facebook_owner_voter_found,
            'invitation_owner_voter_found': False,
        }
        return error_results

    from_voter_id = 0
    from_voter_we_vote_id = ""
    to_voter_id = 0
    to_voter_we_vote_id = ""
    email_manager = EmailManager()

    # ############# EMAIL SIGN IN #####################################
    if positive_value_exists(email_secret_key):
        email_results = email_manager.retrieve_email_address_object_from_secret_key(email_secret_key)
        if email_results['email_address_object_found']:
            email_address_object = email_results['email_address_object']

            email_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                email_address_object.voter_we_vote_id)
            if email_owner_voter_results['voter_found']:
                email_owner_voter_found = True
                email_owner_voter = email_owner_voter_results['voter']

        if not email_owner_voter_found:
            error_results = {
                'status':                       "EMAIL_OWNER_VOTER_NOT_FOUND",
                'success':                      False,
                'voter_device_id':              voter_device_id,
                'current_voter_found':          current_voter_found,
                'email_owner_voter_found':      email_owner_voter_found,
                'facebook_owner_voter_found':   False,
                'invitation_owner_voter_found': False,
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
            }
            return error_results

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        from_voter_id = voter.id
        from_voter_we_vote_id = voter.we_vote_id
        to_voter_id = email_owner_voter.id
        to_voter_we_vote_id = email_owner_voter.we_vote_id
        new_owner_voter = email_owner_voter

    # ############# FACEBOOK SIGN IN #####################################
    elif positive_value_exists(facebook_secret_key):
        facebook_manager = FacebookManager()
        facebook_results = facebook_manager.retrieve_facebook_link_to_voter_from_facebook_secret_key(
            facebook_secret_key)
        if facebook_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_results['facebook_link_to_voter']

            facebook_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                facebook_link_to_voter.voter_we_vote_id)
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
            }
            return error_results

        auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
        if auth_response_results['facebook_auth_response_found']:
            facebook_auth_response = auth_response_results['facebook_auth_response']

        # Double-check they aren't the same voter account
        if voter.id == facebook_owner_voter.id:
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
                }
                return error_results

        # Cache original and resized images
        cache_results = cache_original_and_resized_image(
            voter_we_vote_id=facebook_owner_voter.we_vote_id,
            facebook_user_id=facebook_auth_response.facebook_user_id,
            facebook_profile_image_url_https=facebook_auth_response.facebook_profile_image_url_https,
            image_source=FACEBOOK)
        cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

        # Update the facebook photo
        save_facebook_results = voter_manager.save_facebook_user_values(
            facebook_owner_voter, facebook_auth_response, cached_facebook_profile_image_url_https,
            we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny)
        status += " " + save_facebook_results['status']
        facebook_owner_voter = save_facebook_results['voter']

        # ##### Store the facebook_email as a verified email for facebook_owner_voter
        if positive_value_exists(facebook_auth_response.facebook_email):
            # Check to make sure there isn't an account already using the facebook_email
            facebook_email_address_verified = False
            temp_voter_we_vote_id = ""
            email_results = email_manager.retrieve_primary_email_with_ownership_verified(
                temp_voter_we_vote_id, facebook_auth_response.facebook_email)
            if email_results['email_address_object_found']:
                # If here, then it turns out the facebook_email is verified, and we can
                #   update_voter_email_ownership_verified if a verified email is already stored in the voter record
                email_address_object = email_results['email_address_object']
                facebook_email_address_verified = True
            else:
                # See if an unverified email exists for this voter
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
                    status += "UNABLE_TO_MAKE_FACEBOOK_EMAIL_THE_PRIMARY "

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        from_voter_id = voter.id
        from_voter_we_vote_id = voter.we_vote_id
        to_voter_id = facebook_owner_voter.id
        to_voter_we_vote_id = facebook_owner_voter.we_vote_id
        new_owner_voter = facebook_owner_voter

    # ############# TWITTER SIGN IN #####################################
    elif positive_value_exists(twitter_secret_key):
        twitter_user_manager = TwitterUserManager()
        twitter_link_to_voter = TwitterLinkToVoter()

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
            }
            return error_results

        twitter_auth_manager = TwitterAuthManager()
        auth_response_results = twitter_auth_manager.retrieve_twitter_auth_response(voter_device_id)
        if auth_response_results['twitter_auth_response_found']:
            twitter_auth_response = auth_response_results['twitter_auth_response']

        # Double-check they aren't the same voter account
        if voter.id == twitter_owner_voter.id:
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
                }
                return error_results

        # Cache original and resized images
        cache_results = cache_original_and_resized_image(
            voter_we_vote_id=twitter_owner_voter.we_vote_id,
            twitter_id=twitter_auth_response.twitter_id,
            twitter_screen_name=twitter_auth_response.twitter_screen_name,
            twitter_profile_image_url_https=twitter_auth_response.twitter_profile_image_url_https,
            image_source=TWITTER)
        cached_twitter_profile_image_url_https = cache_results['cached_twitter_profile_image_url_https']
        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

        # Update the Twitter photo
        save_twitter_results = voter_manager.save_twitter_user_values_from_twitter_auth_response(
            twitter_owner_voter, twitter_auth_response, cached_twitter_profile_image_url_https,
            we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny)
        status += " " + save_twitter_results['status']
        twitter_owner_voter = save_twitter_results['voter']

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
                                status += "UNABLE_TO_UPDATE_LINKED_ORGANIZATION_WE_VOTE_ID "
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
                                status += "UNABLE_TO_UPDATE_LINKED_ORGANIZATION_WE_VOTE_ID "
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
                    status += "UNABLE_TO_TWITTER_LINK_ORGANIZATION_TO_VOTER "
            else:
                # Create new organization
                organization_name = twitter_owner_voter.get_full_name()
                organization_website = ""
                organization_twitter_handle = ""
                organization_email = ""
                organization_facebook = ""
                organization_image = twitter_owner_voter.voter_photo_url()
                organization_manager = OrganizationManager()
                create_results = organization_manager.create_organization(
                    organization_name, organization_website, organization_twitter_handle,
                    organization_email, organization_facebook, organization_image)
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
                        status += "UNABLE_TO_LINK_NEW_ORGANIZATION_TO_VOTER "

        # Make sure we end up with the organization referred to in twitter_link_to_organization ends up as
        # voter.linked_organization_we_vote_id

        if repair_twitter_related_organization_caching_now:
            organization_list_manager = OrganizationListManager()
            repair_results = organization_list_manager.repair_twitter_related_organization_caching(
                twitter_link_to_organization.twitter_id)
            status += repair_results['status']

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        from_voter_id = voter.id
        from_voter_we_vote_id = voter.we_vote_id
        to_voter_id = twitter_owner_voter.id
        to_voter_we_vote_id = twitter_owner_voter.we_vote_id
        new_owner_voter = twitter_owner_voter

    # ############# INVITATION SIGN IN #####################################
    elif positive_value_exists(invitation_secret_key):
        friend_manager = FriendManager()
        invitation_owner_voter = Voter()
        for_merge_accounts = True
        sender_voter_we_vote_id = ""
        friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(
            invitation_secret_key, for_merge_accounts)
        if friend_invitation_results['friend_invitation_found']:
            friend_invitation = friend_invitation_results['friend_invitation']
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
        friend_accepted_invitation_send(accepting_voter_we_vote_id, original_sender_we_vote_id)

        # Now we have voter (from voter_device_id) and invitation_owner_voter (from invitation_secret_key)
        # We are going to make the email_owner_voter the new master
        from_voter_id = voter.id
        from_voter_we_vote_id = voter.we_vote_id
        to_voter_id = invitation_owner_voter.id
        to_voter_we_vote_id = invitation_owner_voter.we_vote_id
        new_owner_voter = invitation_owner_voter

    # The from_voter and to_voter may both have their own linked_organization_we_vote_id
    organization_manager = OrganizationManager()
    from_voter_linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    from_voter_linked_organization_id = 0
    if positive_value_exists(from_voter_linked_organization_we_vote_id):
        from_linked_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            from_voter_linked_organization_we_vote_id)
        if from_linked_organization_results['organization_found']:
            from_linked_organization = from_linked_organization_results['organization']
            from_voter_linked_organization_id = from_linked_organization.id

    to_voter_linked_organization_we_vote_id = new_owner_voter.linked_organization_we_vote_id
    to_voter_linked_organization_id = 0
    if positive_value_exists(to_voter_linked_organization_we_vote_id):
        to_linked_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            to_voter_linked_organization_we_vote_id)
        if to_linked_organization_results['organization_found']:
            to_linked_organization = to_linked_organization_results['organization']
            to_voter_linked_organization_id = to_linked_organization.id

    # If the to_voter does not have a linked_organization_we_vote_id, then we should move the from_voter's
    #  organization_we_vote_id
    if not positive_value_exists(to_voter_linked_organization_we_vote_id):
        # Use the from_voter's linked_organization_we_vote_id
        to_voter_linked_organization_we_vote_id = from_voter_linked_organization_we_vote_id
        to_voter_linked_organization_id = from_voter_linked_organization_id

    # Transfer positions from voter to new_owner_voter
    move_positions_results = move_positions_to_another_voter(
        from_voter_id, from_voter_we_vote_id,
        to_voter_id, to_voter_we_vote_id,
        to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id)
    status += " " + move_positions_results['status']

    if positive_value_exists(from_voter_linked_organization_we_vote_id) and \
            positive_value_exists(to_voter_linked_organization_we_vote_id) and \
            from_voter_linked_organization_we_vote_id != to_voter_linked_organization_we_vote_id:
        move_organization_to_another_complete_results = move_organization_to_another_complete(
            from_voter_linked_organization_id, from_voter_linked_organization_we_vote_id,
            to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id,
            to_voter_id, to_voter_we_vote_id
        )
        status += " " + move_organization_to_another_complete_results['status']

    # Transfer friends from voter to new_owner_voter
    move_friends_results = move_friends_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id)
    status += " " + move_friends_results['status']

    # Transfer friend invitations from voter to email_owner_voter
    move_friend_invitations_results = move_friend_invitations_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id)
    status += " " + move_friend_invitations_results['status']

    if positive_value_exists(voter.linked_organization_we_vote_id):
        # Remove the link to the organization so we don't have a future conflict
        try:
            voter.linked_organization_we_vote_id = None
            voter.save()
            # All positions should have already been moved with move_positions_to_another_voter
        except Exception as e:
            # Fail silently
            pass

    # Transfer the organizations the from_voter is following to the new_owner_voter
    move_follow_results = move_follow_entries_to_another_voter(from_voter_id, to_voter_id, to_voter_we_vote_id)
    status += " " + move_follow_results['status']

    # Transfer the issues that the voter is following
    # TODO Create move_follow_issue_entries_to_another_voter

    # Make sure we bring over all emails from the from_voter over to the to_voter
    move_email_addresses_results = move_email_address_entries_to_another_voter(from_voter_we_vote_id,
                                                                               to_voter_we_vote_id)
    status += " " + move_email_addresses_results['status']

    if positive_value_exists(voter.primary_email_we_vote_id):
        # Remove the email information so we don't have a future conflict
        try:
            voter.email = None
            voter.primary_email_we_vote_id = None
            voter.email_ownership_is_verified = False
            voter.save()
        except Exception as e:
            # Fail silently
            pass

    # Bring over Facebook information
    move_facebook_results = move_facebook_info_to_another_voter(voter, new_owner_voter)
    status += " " + move_facebook_results['status']

    # Bring over Twitter information
    move_twitter_results = move_twitter_info_to_another_voter(voter, new_owner_voter)
    status += " " + move_twitter_results['status']

    # Bring over any donations that have been made in this session by the new_owner_voter to the voter, subscriptions
    # are complicated.  See the comments in the donate/controllers.py
    move_donation_results = move_donation_info_to_another_voter(voter, new_owner_voter)
    status += " " + move_donation_results['status']

    # Bring over the voter-table data
    merge_voter_accounts_results = merge_voter_accounts(voter, new_owner_voter)
    status += " " + merge_voter_accounts_results['status']

    # TODO Keep a record of voter_we_vote_id's associated with this voter, so we can find the
    #  latest we_vote_id

    # TODO If no errors, delete the voter account

    # And finally, relink the current voter_device_id to email_owner_voter
    update_link_results = voter_device_link_manager.update_voter_device_link(voter_device_link, new_owner_voter)
    if update_link_results['voter_device_link_updated']:
        success = True
        status += " MERGE_TWO_ACCOUNTS_VOTER_DEVICE_LINK_UPDATED"

    # Data healing scripts
    position_list_manager = PositionListManager()
    repair_results = position_list_manager.repair_all_positions_for_voter(new_owner_voter.id)
    status += repair_results['status']

    results = {
        'status':                       status,
        'success':                      success,
        'voter_device_id':              voter_device_id,
        'current_voter_found':          current_voter_found,
        'email_owner_voter_found':      email_owner_voter_found,
        'facebook_owner_voter_found':   facebook_owner_voter_found,
        'invitation_owner_voter_found': invitation_owner_voter_found,
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
                'status': "MISSING_VARIABLE-AT_LEAST_ONE_PHOTO",
                'success': False,
                'voter_device_id': voter_device_id,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id < 0:
        results = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
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
            status = "VOTER_FACEBOOK_PHOTO_SAVED"
        else:
            status = "VOTER_PHOTOS_EMPTY_SAVED"

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


def voter_retrieve_for_api(voter_device_id):  # voterRetrieve
    """
    Used by the api
    :param voter_device_id:
    :return:
    """
    voter_manager = VoterManager()
    voter_id = 0
    voter_created = False
    twitter_link_to_voter = TwitterLinkToVoter()
    repair_twitter_link_to_voter_caching_now = False

    if positive_value_exists(voter_device_id):
        # If a voter_device_id is passed in that isn't valid, we want to throw an error
        device_id_results = is_voter_device_id_valid(voter_device_id)
        if not device_id_results['success']:
            json_data = {
                    'status':           device_id_results['status'],
                    'success':          False,
                    'voter_device_id':  voter_device_id,
                    'voter_created':    False,
                    'voter_found':      False,
                }
            return json_data

        voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
        if not positive_value_exists(voter_id):
            json_data = {
                'status':           "VOTER_NOT_FOUND_FROM_DEVICE_ID",
                'success':          False,
                'voter_device_id':  voter_device_id,
                'voter_created':    False,
                'voter_found':      False,
            }
            return json_data
    else:
        # If a voter_device_id isn't passed in, automatically create a new voter_device_id and voter
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
            }
            return json_data

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
                    voter_id = voter_device_link.voter_id
                    voter_created = True

        if not positive_value_exists(voter_id):
            json_data = {
                'status':                           "VOTER_NOT_FOUND_AFTER_BEING_CREATED",
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'voter_created':                    False,
                'voter_found':                      False,
            }
            return json_data

    # At this point, we should have a valid voter_id
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if results['voter_found']:
        voter = results['voter']

        if voter_created:
            status = 'VOTER_CREATED '
        else:
            status = 'VOTER_FOUND '

        twitter_user_manager = TwitterUserManager()
        twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_voter(0, voter.we_vote_id)
        twitter_link_to_voter_twitter_id = 0
        if voter.is_signed_in():
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
                if voter.linked_organization_we_vote_id != twitter_link_to_organization_we_vote_id:
                    # If here there is a mismatch to fix
                    try:
                        voter.linked_organization_we_vote_id = twitter_link_to_organization_we_vote_id
                        voter.save()
                        repair_twitter_link_to_voter_caching_now = True
                        status += "VOTER_LINKED_ORGANIZATION_FIXED "
                    except Exception as e:
                        status += "VOTER_LINKED_ORGANIZATION_COULD_NOT_BE_FIXED "

            if not positive_value_exists(voter.linked_organization_we_vote_id):
                existing_organization_for_this_voter_found = False
                create_twitter_link_to_organization = False
                organization_twitter_handle = ""
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
                            if positive_value_exists(twitter_link_to_organization.organization_we_vote_id):
                                if twitter_link_to_organization.organization_we_vote_id \
                                        != voter.linked_organization_we_vote_id:
                                    try:
                                        voter.linked_organization_we_vote_id = \
                                            twitter_link_to_organization.organization_we_vote_id
                                        voter.save()
                                        existing_organization_for_this_voter_found = True

                                    except Exception as e:
                                        status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_FROM_TWITTER_LINK_TO_VOTER "
                        else:
                            # If an existing TwitterLinkToOrganization was not found,
                            # create the organization below, and then create TwitterLinkToOrganization
                            organization_twitter_handle = twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
                            create_twitter_link_to_organization = True

                if not existing_organization_for_this_voter_found:
                    # If we are here, we need to create an organization for this voter
                    organization_name = voter.get_full_name()
                    organization_website = ""
                    organization_email = ""
                    organization_facebook = ""
                    organization_image = voter.we_vote_hosted_profile_image_url_large \
                        if positive_value_exists(voter.we_vote_hosted_profile_image_url_large) \
                        else voter.voter_photo_url()
                    organization_manager = OrganizationManager()
                    create_results = organization_manager.create_organization(
                        organization_name, organization_website, organization_twitter_handle,
                        organization_email, organization_facebook, organization_image)
                    if create_results['organization_created']:
                        # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                        organization = create_results['organization']
                        try:
                            voter.linked_organization_we_vote_id = organization.we_vote_id
                            voter.save()

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
                            status += "UNABLE_TO_CREATE_NEW_ORGANIZATION_TO_VOTER_FROM_RETRIEVE_VOTER "

        # Heal Facebook data
        auth_response_results = FacebookManager().retrieve_facebook_auth_response(voter_device_id)
        if auth_response_results['facebook_auth_response_found']:
            facebook_auth_response = auth_response_results['facebook_auth_response']
            facebook_user_results = FacebookManager().retrieve_facebook_user_by_facebook_user_id(
                facebook_auth_response.facebook_user_id)
            if facebook_user_results['facebook_user_found']:
                facebook_user = facebook_user_results['facebook_user']

                organization_dict = \
                    OrganizationManager().retrieve_organization_from_we_vote_id(voter.linked_organization_we_vote_id)
                try:
                    organization = organization_dict['organization']
                    if not positive_value_exists(organization.facebook_id) or \
                            not positive_value_exists(organization.facebook_background_image_url_https):
                        organization_manager.update_or_create_organization(
                            organization.id,
                            we_vote_id=organization.we_vote_id,
                            organization_website_search=None,
                            organization_twitter_search=None,
                            facebook_id=facebook_user.facebook_user_id,
                            facebook_email=facebook_user.facebook_email,
                            facebook_profile_image_url_https=facebook_user.facebook_profile_image_url_https,
                            facebook_background_image_url_https=facebook_user.facebook_background_image_url_https
                        )
                except Exception as e:
                    logger.error('FAILED organization_manager.update_or_create_organization. '
                                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e)))


        if repair_twitter_link_to_voter_caching_now:
            # If here then we know that we have a twitter_link_to_voter, and there was some data cleanup done
            repair_results = voter_manager.repair_twitter_related_voter_caching(
                twitter_link_to_voter.twitter_id)
            status += repair_results['status']

        donation_list = donation_history_for_a_voter(voter.we_vote_id)
        json_data = {
            'status':                           status,
            'success':                          True,
            'voter_device_id':                  voter_device_id,
            'voter_created':                    voter_created,
            'voter_found':                      True,
            'we_vote_id':                       voter.we_vote_id,
            'facebook_id':                      voter.facebook_id,
            'email':                            voter.email,
            'facebook_email':                   voter.facebook_email,
            'facebook_profile_image_url_https': voter.facebook_profile_image_url_https,
            'full_name':                        voter.get_full_name(),
            'first_name':                       voter.first_name,
            'last_name':                        voter.last_name,
            'twitter_screen_name':              voter.twitter_screen_name,
            'is_signed_in':                     voter.is_signed_in(),
            'is_admin':                         voter.is_admin,
            'is_verified_volunteer':            voter.is_verified_volunteer,
            'signed_in_facebook':               voter.signed_in_facebook(),
            'signed_in_google':                 voter.signed_in_google(),
            'signed_in_twitter':                voter.signed_in_twitter(),
            'signed_in_with_email':             voter.signed_in_with_email(),
            'has_valid_email':                  voter.has_valid_email(),
            'has_data_to_preserve':             voter.has_data_to_preserve(),
            'has_email_with_verified_ownership':    voter.has_email_with_verified_ownership(),
            'linked_organization_we_vote_id':   voter.linked_organization_we_vote_id,
            'voter_photo_url_large':            voter.we_vote_hosted_profile_image_url_large if positive_value_exists(
                voter.we_vote_hosted_profile_image_url_large) else voter.voter_photo_url(),
            'voter_photo_url_medium':           voter.we_vote_hosted_profile_image_url_medium,
            'voter_photo_url_tiny':             voter.we_vote_hosted_profile_image_url_tiny,
            'voter_donation_history_list':      donation_list,
            'interface_status_flags':           voter.interface_status_flags,
            'notification_settings_flags':      voter.notification_settings_flags
        }
        return json_data

    else:
        status = results['status']
        json_data = {
            'status':                           status,
            'success':                          False,
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
            'is_verified_volunteer':            False,
            'signed_in_facebook':               False,
            'signed_in_google':                 False,
            'signed_in_twitter':                False,
            'signed_in_with_email':             False,
            'has_valid_email':                  False,
            'has_data_to_preserve':             False,
            'has_email_with_verified_ownership':    False,
            'linked_organization_we_vote_id':   '',
            'voter_photo_url_large':            '',
            'voter_photo_url_medium':           '',
            'voter_photo_url_tiny':             '',
            'interface_status_flags':           0,
            'notification_settings_flags':        0
        }
        return json_data


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
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
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
                        # We tried to update the voter found by the voter_we_vote_id stored in the EmailAddress table,
                        #  but got an error, so assume it was because of a collision with the primary_email_we_vote_id
                        # Here, we retrieve the voter already "claiming" this email entry so we can wipe the
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
            # Remove the email information so we don't have a future conflict
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
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
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
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':               "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    from_voter = voter_results['voter']

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
    twitter_link_to_voter_results = twitter_user_manager.retrieve_twitter_link_to_voter(
        twitter_id, from_voter.we_vote_id)
    if not twitter_link_to_voter_results['twitter_link_to_voter_found']:
        error_results = {
            'status':               "VOTER_SPLIT_INTO_TWO_ACCOUNTS_TWITTER_LINK_TO_VOTER_NOT_FOUND",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    # Make sure this voter has another way to sign in once twitter is split off
    if from_voter.signed_in_facebook() or from_voter.signed_in_with_email():
        pass
    else:
        error_results = {
            'status':               "VOTER_SPLIT_INTO_TWO_ACCOUNTS-NO_OTHER_WAY_TO_SIGN_IN",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'split_off_twitter':    split_off_twitter,
        }
        return error_results

    from_voter_id = from_voter.id
    from_voter_we_vote_id = from_voter.we_vote_id
    to_voter = Voter
    to_voter_id = 0
    to_voter_we_vote_id = ""

    # Make sure we start the process with a from_voter_organization and correct TwitterLinkToVoter
    # and TwitterLinkToOrganization entries
    organization_manager = OrganizationManager()
    repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(from_voter)
    if repair_results['voter_repaired']:
        from_voter = repair_results['voter']

    # Create a duplicate voter
    voter_duplicate_results = voter_manager.duplicate_voter(from_voter)
    if not voter_duplicate_results['voter_duplicated']:
        status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS_NEW_VOTER_NOT_DUPLICATED "
    else:
        to_voter = voter_duplicate_results['voter']
        to_voter_id = to_voter.id
        to_voter_we_vote_id = to_voter.we_vote_id

        # Make sure we remove any legacy of Twitter
        from_voter.twitter_id = 0
        from_voter.twitter_screen_name = ""
        try:
            from_voter.save()
        except Exception as e:
            status += "VOTER_SPLIT_INTO_TWO_ACCOUNTS_NEW_VOTER_NOT_UPDATED "

    if not positive_value_exists(to_voter_we_vote_id):
        error_results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'split_off_twitter':            split_off_twitter,
        }
        return error_results

    # Move TwitterLinkToVoter to the new voter "to_voter"
    twitter_link_moved = False
    twitter_link_to_voter = twitter_link_to_voter_results['twitter_link_to_voter']
    twitter_link_to_voter_twitter_id = twitter_link_to_voter.twitter_id
    try:
        twitter_link_to_voter.voter_we_vote_id = to_voter.we_vote_id
        twitter_link_to_voter.save()
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

    # The facebook link should not require a change, since this link should still be to the from_voter
    # facebook_manager = FacebookManager()
    # facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(0, from_voter.we_vote_id)
    # if facebook_link_results['facebook_link_to_voter_found']:
    #     facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']

    # Get the organization linked to the twitter_id
    # Next, link that organization connected to the Twitter account to the to_voter
    # Then duplicate that org, and connect the duplicate to the from_voter
    organization_manager = OrganizationManager()
    twitter_link_to_organization_exists = False
    twitter_link_to_organization_moved = False
    to_voter_linked_organization_id = 0
    to_voter_linked_organization_we_vote_id = ""
    from_voter_linked_organization_id = 0
    from_voter_linked_organization_we_vote_id = from_voter.linked_organization_we_vote_id

    twitter_organization_name = ""
    if positive_value_exists(twitter_link_to_voter_twitter_id):
        twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_link_to_voter_twitter_id)
        if twitter_user_results['twitter_user_found']:
            twitter_user = twitter_user_results['twitter_user']
            twitter_organization_name = twitter_user.twitter_name

    twitter_link_to_organization_results = \
        twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
            twitter_link_to_voter_twitter_id)
    if not twitter_link_to_organization_results['twitter_link_to_organization_found']:
        status += "NO_LINKED_ORGANIZATION_WE_VOTE_ID_FOUND "
        organization_name = from_voter.get_full_name()
        organization_website = ""
        organization_twitter_handle = ""
        organization_email = ""
        organization_facebook = ""
        organization_image = from_voter.voter_photo_url()
        create_results = organization_manager.create_organization(
            organization_name, organization_website, organization_twitter_handle,
            organization_email, organization_facebook, organization_image)
        if create_results['organization_created']:
            from_voter_linked_organization = create_results['organization']
            from_voter_linked_organization_id = from_voter_linked_organization.id
            from_voter_linked_organization_we_vote_id = from_voter_linked_organization.we_vote_id
    else:
        twitter_link_to_organization = twitter_link_to_organization_results['twitter_link_to_organization']
        twitter_link_to_organization_exists = True
        organization_associated_with_twitter_id_we_vote_id = twitter_link_to_organization.organization_we_vote_id
        twitter_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            organization_associated_with_twitter_id_we_vote_id)
        if not twitter_organization_results['organization_found']:
            status += "NO_LINKED_ORGANIZATION_FOUND "
            # Create new organization
            # Update the twitter_link_to_organization with new organization_we_vote_id
            organization_name = from_voter.get_full_name()
            organization_website = ""
            organization_twitter_handle = ""
            organization_email = ""
            organization_facebook = ""
            organization_image = from_voter.voter_photo_url()
            create_results = organization_manager.create_organization(
                organization_name, organization_website, organization_twitter_handle,
                organization_email, organization_facebook, organization_image)
            if create_results['organization_created']:
                from_voter_linked_organization = create_results['organization']
                from_voter_linked_organization_id = from_voter_linked_organization.id
                from_voter_linked_organization_we_vote_id = from_voter_linked_organization.we_vote_id
        else:
            # Error checking successful. The existing organization that is tied to this twitter_id will be put in
            #  the "from_voter" and we will duplicate an organization for use with the Twitter account
            from_voter_linked_organization = twitter_organization_results['organization']
            from_voter_linked_organization_id = from_voter_linked_organization.id
            from_voter_linked_organization_we_vote_id = from_voter_linked_organization.we_vote_id

    if positive_value_exists(from_voter_linked_organization_we_vote_id):
        # Now that we have the organization linked to the Twitter account, we want to duplicate it,
        #  and then remove data
        #  that shouldn't be in both
        duplicate_organization_results = organization_manager.duplicate_organization_destination_twitter(
            from_voter_linked_organization)
        if not duplicate_organization_results['organization_duplicated']:
            status += "NOT_ABLE_TO_DUPLICATE_ORGANIZATION "
        else:
            to_voter_linked_organization = duplicate_organization_results['organization']
            to_voter_linked_organization_id = to_voter_linked_organization.id
            to_voter_linked_organization_we_vote_id = to_voter_linked_organization.we_vote_id

            if positive_value_exists(to_voter_linked_organization_we_vote_id):
                # Remove the Twitter information from the from_voter_linked_organization
                # and update the name to be voter focused
                try:
                    from_voter_linked_organization.organization_name = from_voter.get_full_name()
                    from_voter_linked_organization.twitter_user_id = 0
                    from_voter_linked_organization.twitter_followers_count = 0
                    from_voter_linked_organization.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_FROM_ORGANIZATION "

                # Update the link to the organization on the to_voter
                try:
                    to_voter.linked_organization_we_vote_id = to_voter_linked_organization_we_vote_id
                    to_voter.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_WE_VOTE_ID_IN_TO_VOTER "

                # Update the TwitterLinkToOrganization to the organization on the to_voter
                if twitter_link_to_organization_exists:
                    try:
                        twitter_link_to_organization.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                        twitter_link_to_organization.save()
                        repair_twitter_related_organization_caching_now = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_TWITTER_LINK_TO_ORGANIZATION "
                else:
                    results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_link_to_voter_twitter_id, to_voter_linked_organization_we_vote_id)
                    status += results['status']
                    if results['twitter_link_to_organization_found']:
                        twitter_link_to_organization = results['twitter_link_to_organization']
                        repair_twitter_related_organization_caching_now = True

                # Update the link to the organization on the from_voter
                try:
                    from_voter.linked_organization_we_vote_id = from_voter_linked_organization_we_vote_id
                    from_voter.save()
                except Exception as e:
                    status += "UNABLE_TO_SAVE_LINKED_ORGANIZATION_WE_VOTE_ID_IN_FROM_VOTER "

                # Update the name of the organization to match Twitter name
                if positive_value_exists(twitter_organization_name):
                    try:
                        to_voter_linked_organization.organization_name = twitter_organization_name
                        to_voter_linked_organization.save()
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_TO_VOTER_ORGANIZATION_NAME "

                twitter_link_to_organization_moved = True

    if not twitter_link_to_organization_moved:
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
            twitter_link_to_voter.twitter_id)
        status += repair_results['status']

    # Make sure to clean up the twitter information in the organization table
    if repair_twitter_related_organization_caching_now:
        organization_list_manager = OrganizationListManager()
        repair_results = organization_list_manager.repair_twitter_related_organization_caching(
            twitter_link_to_organization.twitter_id)
        status += repair_results['status']

    # Duplicate VoterAddress (we are not currently bringing over ballot_items)
    voter_address_manager = VoterAddressManager()
    duplicate_voter_address_results = \
        voter_address_manager.duplicate_voter_address_from_voter_id(from_voter_id, to_voter_id)
    status += " " + duplicate_voter_address_results['status']

    # If anyone is following the from_voter's organization, move those followers to the to_voter's organization
    move_organization_followers_results = duplicate_organization_followers_to_another_organization(
        from_voter_linked_organization_id, from_voter_linked_organization_we_vote_id,
        to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id)
    status += " " + move_organization_followers_results['status']

    # If from_voter is following organizations, copy the follow_organization entries to the to_voter
    duplicate_follow_entries_results = duplicate_follow_entries_to_another_voter(
        from_voter_id, from_voter_we_vote_id, to_voter_id, to_voter_we_vote_id)
    status += " " + duplicate_follow_entries_results['status']

    # Transfer the issues that the voter is following
    # TODO Create duplicate_follow_issue_entries_to_another_voter

    # If from_voter has any position, duplicate positions from_voter to to_voter
    move_positions_results = duplicate_positions_to_another_voter(
        from_voter_id, from_voter_we_vote_id,
        to_voter_id, to_voter_we_vote_id,
        to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id)
    status += " " + move_positions_results['status']

    # We do not transfer friends or friend invitations from voter to new_owner_voter

    # Duplicate and repair both voter guides to have updated names and photos
    voter_guide_results = duplicate_voter_guides(
        from_voter_id, from_voter_we_vote_id, from_voter_linked_organization_we_vote_id,
        to_voter_id, to_voter_we_vote_id, to_voter_linked_organization_we_vote_id)
    status += " " + voter_guide_results['status']

    # We do not bring over all emails from the from_voter over to the to_voter

    # We do not bring over Facebook information

    # We do not duplicate any donations that have been made

    results = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'split_off_twitter': split_off_twitter,
    }

    return results
