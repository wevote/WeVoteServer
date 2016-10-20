# voter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BALLOT_ADDRESS, fetch_voter_id_from_voter_device_link, Voter, VoterAddressManager, \
    VoterDeviceLinkManager, VoterManager
from django.http import HttpResponse
from email_outbound.controllers import move_email_address_entries_to_another_voter
from email_outbound.models import EmailManager
from follow.controllers import move_follow_entries_to_another_voter, move_organization_followers_to_another_organization
from friend.controllers import fetch_friend_invitation_recipient_voter_we_vote_id, \
    move_friend_invitations_to_another_voter, move_friends_to_another_voter
from friend.models import FriendManager
from import_export_facebook.models import FacebookManager
from import_export_twitter.models import TwitterAuthManager
import json
from organization.controllers import move_organization_data_to_another_organization
from organization.models import OrganizationManager
from position.controllers import move_positions_to_another_voter
from twitter.models import TwitterUserManager
import wevote_functions.admin
from wevote_functions.functions import generate_voter_device_id, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


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
            # Fail silently
            pass
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
            # Fail silently
            status += "FROM_VOTER_FACEBOOK_DATA_NOT_REMOVED "

        try:
            # Now move values to new entry and save
            to_voter.facebook_email = temp_facebook_email
            to_voter.facebook_id = temp_facebook_id
            to_voter.facebook_profile_image_url_https = temp_facebook_profile_image_url_https
            to_voter.fb_username = temp_fb_username
            to_voter.save()
            status += "TO_VOTER_FACEBOOK_DATA_SAVED "
        except Exception as e:
            # Fail silently
            status += "TO_VOTER_FACEBOOK_DATA_NOT_SAVED "

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
        status += "MOVE_TWITTER_INFO_MISSING_FROM_OR_TO_VOTER_ID "
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

    # Move facebook_link_to_voter
    if to_voter_twitter_results['twitter_link_to_voter_found']:
        # Don't try to move from the from_voter
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
        create_results = twitter_user_manager.create_twitter_link_to_voter(from_voter.twitter_id, to_voter.we_vote_id)
        status += " " + create_results['status']

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
        # Remove info from the from_voter and then move facebook info to the to_voter
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
def voter_address_retrieve_for_api(voter_device_id):
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


def voter_address_save_for_api(voter_device_id, voter_id, address_raw_text):
    # At this point, we have a valid voter

    voter_address_manager = VoterAddressManager()
    address_type = BALLOT_ADDRESS

    # We wrap get_or_create because we want to centralize error handling
    results = voter_address_manager.update_or_create_voter_address(voter_id, address_type, address_raw_text.strip())

    if results['success']:
        if positive_value_exists(address_raw_text):
            status = "VOTER_ADDRESS_SAVED"
        else:
            status = "VOTER_ADDRESS_EMPTY_SAVED"

        results = {
                'status': status,
                'success': True,
                'voter_device_id': voter_device_id,
                'text_for_map_search': address_raw_text,
            }
    # elif results['status'] == 'MULTIPLE_MATCHING_ADDRESSES_FOUND':
        # delete all currently matching addresses and save again
    else:
        results = {
                'status': results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
                'text_for_map_search': address_raw_text,
            }
    return results


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
            'status':                       "VOTER_MERGE_TWO_ACCOUNTS_SECRET_KEY_NOT_PASSED_IN",
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

        # Update the facebook photo
        save_facebook_results = voter_manager.save_facebook_user_values(facebook_owner_voter, facebook_auth_response)
        status += " " + save_facebook_results['status']
        facebook_owner_voter = save_facebook_results['voter']

        # ##### Make the facebook_email the primary email for facebook_owner_voter TODO DALE
        # Does facebook_owner_voter already have a primary email? If not, update it
        if not facebook_owner_voter.email_ownership_is_verified:
            if positive_value_exists(facebook_auth_response.facebook_email):
                # Check to make sure there isn't an account already using the facebook_email
                temp_voter_we_vote_id = ""
                email_results = email_manager.retrieve_primary_email_with_ownership_verified(
                    temp_voter_we_vote_id, facebook_auth_response.facebook_email)
                if not email_results['email_address_object_found']:
                    # See if an unverified email exists for this voter
                    email_address_object_we_vote_id = ""
                    email_retrieve_results = email_manager.retrieve_email_address_object(
                        facebook_auth_response.facebook_email, email_address_object_we_vote_id,
                        facebook_owner_voter.we_vote_id)
                    if email_retrieve_results['email_address_object_found']:
                        email_address_object = email_retrieve_results['email_address_object']
                        email_address_object = email_manager.update_email_address_object_to_be_verified(
                            email_address_object)
                    else:
                        email_ownership_is_verified = True
                        email_create_results = email_manager.create_email_address(
                            facebook_auth_response.facebook_email, facebook_owner_voter.we_vote_id,
                            email_ownership_is_verified)
                        if email_create_results['email_address_object_saved']:
                            email_address_object = email_create_results['email_address_object']
                    try:
                        # Attach the email_address_object to facebook_owner_voter
                        voter_manager.update_voter_email_ownership_verified(facebook_owner_voter,
                                                                            email_address_object)
                    except Exception as e:
                        # Fail silently
                        pass

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        from_voter_id = voter.id
        from_voter_we_vote_id = voter.we_vote_id
        to_voter_id = facebook_owner_voter.id
        to_voter_we_vote_id = facebook_owner_voter.we_vote_id
        new_owner_voter = facebook_owner_voter
    elif positive_value_exists(twitter_secret_key):
        twitter_user_manager = TwitterUserManager()
        twitter_user_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_twitter_secret_key(
            twitter_secret_key)
        if twitter_user_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_user_results['twitter_link_to_voter']

            twitter_owner_voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                twitter_link_to_voter.voter_we_vote_id)
            if twitter_owner_voter_results['voter_found']:
                twitter_owner_voter_found = True
                twitter_owner_voter = twitter_owner_voter_results['voter']

        if not twitter_owner_voter_found:
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
                # Get the recent twitter_id
                voter_manager.update_voter_with_twitter_link_verified(
                    twitter_owner_voter,
                    twitter_auth_response.twitter_id)

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

        # Update the Twitter photo
        save_twitter_results = voter_manager.save_twitter_user_values_from_twitter_auth_response(
            twitter_owner_voter, twitter_auth_response)
        status += " " + save_twitter_results['status']
        twitter_owner_voter = save_twitter_results['voter']

        # Now we have voter (from voter_device_id) and email_owner_voter (from email_secret_key)
        # We are going to make the email_owner_voter the new master
        from_voter_id = voter.id
        from_voter_we_vote_id = voter.we_vote_id
        to_voter_id = twitter_owner_voter.id
        to_voter_we_vote_id = twitter_owner_voter.we_vote_id
        new_owner_voter = twitter_owner_voter
    elif positive_value_exists(invitation_secret_key):
        friend_manager = FriendManager()
        for_merge_accounts = True
        friend_invitation_results = friend_manager.retrieve_friend_invitation_from_secret_key(
            invitation_secret_key, for_merge_accounts)
        if not friend_invitation_results['friend_invitation_found']:
            friend_invitation = friend_invitation_results['friend_invitation']
            recipient_voter_we_vote_id = fetch_friend_invitation_recipient_voter_we_vote_id(friend_invitation)

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
        to_voter_id, to_voter_we_vote_id, to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id)
    status += " " + move_positions_results['status']

    if from_voter_linked_organization_we_vote_id != to_voter_linked_organization_we_vote_id:
        # If anyone is following the old voter's organization, move those followers to the new voter's organization
        move_organization_followers_results = move_organization_followers_to_another_organization(
            from_voter_linked_organization_id, from_voter_linked_organization_we_vote_id,
            to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id)
        status += " " + move_organization_followers_results['status']

        # There might be some useful information in the from_voter's organization that needs to be moved
        move_organization_results = move_organization_data_to_another_organization(
            from_voter_linked_organization_we_vote_id, to_voter_linked_organization_we_vote_id)
        status += " " + move_organization_results['status']

        # Finally, delete the from_voter's organization
        if move_organization_results['data_transfer_complete']:
            from_organization = move_organization_results['from_organization']
            try:
                from_organization.delete()
            except Exception as e:
                # Fail silently
                pass

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
        except Exception as e:
            # Fail silently
            pass

    # Transfer the organizations the from_voter is following to the new_owner_voter
    move_follow_results = move_follow_entries_to_another_voter(from_voter_id, to_voter_id, to_voter_we_vote_id)
    status += " " + move_follow_results['status']

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

    # And finally, relink the current voter_device_id to email_owner_voter
    update_link_results = voter_device_link_manager.update_voter_device_link(voter_device_link, new_owner_voter)
    if update_link_results['voter_device_link_updated']:
        success = True
        status += " MERGE_TWO_ACCOUNTS_VOTER_DEVICE_LINK_UPDATED"

    results = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'current_voter_found': current_voter_found,
        'email_owner_voter_found': email_owner_voter_found,
        'facebook_owner_voter_found': facebook_owner_voter_found,
        'invitation_owner_voter_found': invitation_owner_voter_found,
    }

    return results


def voter_photo_save_for_api(voter_device_id, facebook_profile_image_url_https, facebook_photo_variable_exists):
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
                'status':           "VOTER_NOT_FOUND_AFTER_BEING_CREATED",
                'success':          False,
                'voter_device_id':  voter_device_id,
                'voter_created':    False,
                'voter_found':      False,
            }
            return json_data

    # At this point, we should have a valid voter_id
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if results['voter_found']:
        voter = results['voter']

        if voter_created:
            status = 'VOTER_CREATED'
        else:
            status = 'VOTER_FOUND'
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
            'signed_in_personal':               voter.signed_in_personal(),
            'signed_in_facebook':               voter.signed_in_facebook(),
            'signed_in_google':                 voter.signed_in_google(),
            'signed_in_twitter':                voter.signed_in_twitter(),
            'signed_in_with_email':             voter.signed_in_with_email(),
            'has_valid_email':                  voter.has_valid_email(),
            'has_data_to_preserve':             voter.has_data_to_preserve(),
            'has_email_with_verified_ownership':    voter.has_email_with_verified_ownership(),
            'linked_organization_we_vote_id':   voter.linked_organization_we_vote_id,
            'voter_photo_url':                  voter.voter_photo_url(),
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
            'signed_in_personal':               False,
            'signed_in_facebook':               False,
            'signed_in_google':                 False,
            'signed_in_twitter':                False,
            'signed_in_with_email':             False,
            'has_valid_email':                  False,
            'has_data_to_preserve':             False,
            'has_email_with_verified_ownership':    False,
            'linked_organization_we_vote_id':   '',
            'voter_photo_url':                  '',
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
