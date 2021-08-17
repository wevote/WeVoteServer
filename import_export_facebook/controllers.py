# import_export_facebook/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import re

import wevote_functions.admin
from config.base import get_environment_variable
from email_outbound.models import EmailManager
from friend.models import FriendManager
from image.controllers import FACEBOOK, cache_master_and_resized_image
from import_export_facebook.models import FacebookManager
from organization.models import OrganizationManager, INDIVIDUAL
from voter.models import VoterManager
from wevote_functions.functions import is_voter_device_id_valid, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def voter_facebook_save_to_current_account_for_api(voter_device_id):  # voterFacebookSaveToCurrentAccount
    """

    :param voter_device_id:
    :return:
    """
    status = ""
    facebook_account_created = False

    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success':                  False,
            'status':                   "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id':          voter_device_id,
            'facebook_account_created': facebook_account_created,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'success':                  False,
            'status':                   "VALID_VOTER_MISSING",
            'voter_device_id':          voter_device_id,
            'facebook_account_created': facebook_account_created,
        }
        return results

    voter = results['voter']

    facebook_manager = FacebookManager()
    facebook_results = facebook_manager.retrieve_facebook_link_to_voter(voter_we_vote_id=voter.we_vote_id)
    if facebook_results['facebook_link_to_voter_found']:
        error_results = {
            'status':                   "FACEBOOK_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'facebook_account_created': facebook_account_created,
        }
        return error_results

    auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    if not auth_response_results['facebook_auth_response_found']:
        error_results = {
            'status':                   "FACEBOOK_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'facebook_account_created': facebook_account_created,
        }
        return error_results

    facebook_auth_response = auth_response_results['facebook_auth_response']

    link_results = facebook_manager.create_facebook_link_to_voter(facebook_auth_response.facebook_user_id,
                                                                  voter.we_vote_id)

    if not link_results['facebook_link_to_voter_saved']:
        error_results = {
            'status':                   link_results['status'],
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'facebook_account_created': facebook_account_created,
        }
        return error_results

    facebook_account_created = True
    facebook_link_to_voter = link_results['facebook_link_to_voter']

    # Cache original and resized images
    cache_results = cache_master_and_resized_image(
        voter_we_vote_id=voter.we_vote_id,
        facebook_user_id=facebook_auth_response.facebook_user_id,
        facebook_profile_image_url_https=facebook_auth_response.facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_auth_response.facebook_background_image_url_https,
        image_source=FACEBOOK)
    cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
    # cached_facebook_background_image_url_https is cached, but is not stored in voter_voter
    we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
    we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
    we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

    # Update voter with Facebook info (not including email -- that is done below)
    results = voter_manager.save_facebook_user_values(
        voter, facebook_auth_response, cached_facebook_profile_image_url_https, we_vote_hosted_profile_image_url_large,
        we_vote_hosted_profile_image_url_medium, we_vote_hosted_profile_image_url_tiny)

    status += results['status'] + ", "
    success = results['success']
    voter = results['voter']

    # ##### Make the facebook_email an email for the current voter (and possibly the primary email)
    email_manager = EmailManager()
    email_address_object = {}
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
            # See if an unverified copy of this email exists for this voter
            email_address_object_we_vote_id = ""
            email_retrieve_results = email_manager.retrieve_email_address_object(
                facebook_auth_response.facebook_email, email_address_object_we_vote_id,
                voter.we_vote_id)
            if email_retrieve_results['email_address_object_found']:
                email_address_object = email_retrieve_results['email_address_object']
                email_address_object = email_manager.update_email_address_object_as_verified(
                    email_address_object)
                facebook_email_address_verified = True
            else:
                email_ownership_is_verified = True
                email_create_results = email_manager.create_email_address(
                    facebook_auth_response.facebook_email, voter.we_vote_id,
                    email_ownership_is_verified)
                if email_create_results['email_address_object_saved']:
                    email_address_object = email_create_results['email_address_object']
                    facebook_email_address_verified = True

        # Does the current voter already have a primary email?
        if not voter.email_ownership_is_verified and facebook_email_address_verified:
            try:
                # Attach the email_address_object to voter
                voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
            except Exception as e:
                status += "UNABLE_TO_MAKE_FACEBOOK_EMAIL_THE_PRIMARY "

    # Does this voter already have an organization associated with their account?
    if positive_value_exists(voter.linked_organization_we_vote_id):
        # TODO DALE Do we need to do anything if they already have a linked_organization_we_vote_id?
        status += "VOTER_LINKED_ORGANIZATION_WE_VOTE_ID_ALREADY_EXISTS: " + voter.linked_organization_we_vote_id + " "
    else:
        organization_manager = OrganizationManager()
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
            new_organization = create_results['organization']
            # Connect voter.linked_organization_we_vote_id with new organization
            try:
                voter.linked_organization_we_vote_id = new_organization.we_vote_id
                voter.save()
                status += "VOTER_LINKED_ORGANIZATION_WE_VOTE_ID_UPDATED "
            except Exception as e:
                success = False
                status += "VOTER_LINKED_ORGANIZATION_WE_VOTE_ID_NOT_UPDATED: " + str(e) + " "
        else:
            status += "NEW_ORGANIZATION_COULD_NOT_BE_CREATED "

    results = {
        'success':                  success,
        'status':                   status,
        'voter_device_id':          voter_device_id,
        'facebook_account_created': facebook_account_created,
    }
    return results


def facebook_friends_action_for_api(voter_device_id):   # facebookFriendsAction
    """
    This is used to retrieve facebook friends who are using WeVote app by facebook 'friends' API.
    However we use the Facebook "games" api "invitable_friends" data on the fly from the webapp, to invite facebook
    friends who are not using we vote.
    :param voter_device_id:
    :return:
    """
    status = ''
    success = False
    facebook_friends_using_we_vote_list = []
    facebook_friend_suggestion_found = False
    facebook_suggested_friend_count = 0

    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                               "VALID_VOTER_DEVICE_ID_MISSING",
            'success':                              success,
            'voter_device_id':                      voter_device_id,
            'facebook_friend_suggestion_found':     facebook_friend_suggestion_found,
            'facebook_suggested_friend_count':      facebook_suggested_friend_count,
            'facebook_friends_using_we_vote_list':  facebook_friends_using_we_vote_list,
        }
        return error_results

    facebook_manager = FacebookManager()
    auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    if not auth_response_results['facebook_auth_response_found']:
        error_results = {
            'status':                               "FACEBOOK_AUTH_RESPONSE_NOT_FOUND",
            'success':                              success,
            'voter_device_id':                      voter_device_id,
            'facebook_friend_suggestion_found':     facebook_friend_suggestion_found,
            'facebook_suggested_friend_count':      facebook_suggested_friend_count,
            'facebook_friends_using_we_vote_list':  facebook_friends_using_we_vote_list,
        }
        return error_results

    facebook_friends_from_facebook_results = facebook_manager.retrieve_facebook_friends_from_facebook(voter_device_id)
    facebook_friends_using_we_vote_list = facebook_friends_from_facebook_results['facebook_friends_list']
    status += facebook_friends_from_facebook_results['status']
    success = facebook_friends_from_facebook_results['success']
    if facebook_friends_from_facebook_results['facebook_friends_list_found']:
        # Update FacebookUser table with all users
        for facebook_user_entry in facebook_friends_using_we_vote_list:
            facebook_user_id = facebook_user_entry['facebook_user_id']
            facebook_user_name = facebook_user_entry['facebook_user_name']
            facebook_user_first_name = facebook_user_entry['facebook_user_first_name']
            facebook_user_middle_name = facebook_user_entry['facebook_user_middle_name']
            facebook_user_last_name = facebook_user_entry['facebook_user_last_name']
            facebook_user_location_id = facebook_user_entry['facebook_user_location_id']
            facebook_user_location_name = facebook_user_entry['facebook_user_location_name']
            facebook_user_gender = facebook_user_entry['facebook_user_gender']
            facebook_user_birthday = facebook_user_entry['facebook_user_birthday']
            facebook_profile_image_url_https = facebook_user_entry['facebook_profile_image_url_https']
            facebook_background_image_url_https = facebook_user_entry['facebook_background_image_url_https']
            facebook_user_about = facebook_user_entry['facebook_user_about']
            facebook_user_is_verified = facebook_user_entry['facebook_user_is_verified']
            facebook_user_friend_total_count = facebook_user_entry['facebook_user_friend_total_count']
            facebook_user_results = facebook_manager.update_or_create_facebook_user(
                facebook_user_id, facebook_user_first_name, facebook_user_middle_name, facebook_user_last_name,
                facebook_user_name, facebook_user_location_id, facebook_user_location_name, facebook_user_gender,
                facebook_user_birthday, facebook_profile_image_url_https, facebook_background_image_url_https,
                facebook_user_about, facebook_user_is_verified, facebook_user_friend_total_count)
            status += ' ' + facebook_user_results['status']
            success = facebook_user_results['success']

    # Find facebook_link_to_voter for all users and then updating SuggestedFriend table
    facebook_auth_response = auth_response_results['facebook_auth_response']
    my_facebook_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter(
        facebook_auth_response.facebook_user_id)
    status += ' ' + my_facebook_link_to_voter_results['status']
    if my_facebook_link_to_voter_results['facebook_link_to_voter_found']:
        friend_manager = FriendManager()
        viewer_voter_we_vote_id = my_facebook_link_to_voter_results['facebook_link_to_voter'].voter_we_vote_id
        for facebook_user_entry in facebook_friends_using_we_vote_list:
            facebook_user_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter(
                facebook_user_entry['facebook_user_id'])
            status += ' ' + facebook_user_link_to_voter_results['status']
            if facebook_user_link_to_voter_results['facebook_link_to_voter_found']:
                viewee_voter_we_vote_id = facebook_user_link_to_voter_results['facebook_link_to_voter'].voter_we_vote_id
                # Are they already friends?
                already_friend_results = friend_manager.retrieve_current_friend(viewer_voter_we_vote_id,
                                                                                viewee_voter_we_vote_id)
                if not already_friend_results['current_friend_found']:
                    update_suggested_friend_results = friend_manager.update_or_create_suggested_friend(
                        viewer_voter_we_vote_id, viewee_voter_we_vote_id)
                    facebook_suggested_friend_count += 1
                    facebook_friend_suggestion_found = update_suggested_friend_results['success']
    else:
        # TODO if facebook_link_to_voter does not exist then check how to add those friends in SuggestedFriend
        pass

    results = {
        'status':                               status,
        'success':                              success,
        'voter_device_id':                      voter_device_id,
        'facebook_friend_suggestion_found':     facebook_friend_suggestion_found,
        'facebook_suggested_friend_count':      facebook_suggested_friend_count,
        'facebook_friends_using_we_vote_list':  facebook_friends_using_we_vote_list,
    }
    return results


def facebook_disconnect_for_api(voter_device_id):  # facebookDisconnect
    """

    :param voter_device_id:
    :return:
    """
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'success': False,
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id': voter_device_id,
        }
        return error_results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        error_results = {
            'success': False,
            'status': "VALID_VOTER_MISSING",
            'voter_device_id': voter_device_id,
        }
        return error_results

    voter = results['voter']

    facebook_id = 0
    results = voter_manager.save_facebook_user_values(voter)  # THIS IS BROKEN
    status = results['status']
    success = results['success']

    if success:
        results = {
            'success': True,
            'status': status,
            'voter_device_id': voter_device_id,
        }
    else:
        results = {
            'success': False,
            'status': status,
            'voter_device_id': voter_device_id,
        }
    return results


def voter_facebook_sign_in_retrieve_for_api(voter_device_id):  # voterFacebookSignInRetrieve
    """
    After signing into facebook, retrieve the voter information for use in the WebApp
    :param voter_device_id:
    :return:
    """
    voter_manager = VoterManager()
    repair_facebook_related_voter_caching_now = False
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   "VOTER_FACEBOOK_SIGN_IN_NO_VOTER ",
            'voter_device_id':                          voter_device_id,
            'voter_we_vote_id':                         "",
            'voter_has_data_to_preserve':               False,
            'existing_facebook_account_found':          False,
            'voter_we_vote_id_attached_to_facebook':    "",
            'voter_we_vote_id_attached_to_facebook_email':  "",
            'facebook_sign_in_found':                   False,
            'facebook_sign_in_verified':                False,
            'facebook_sign_in_failed':                  True,
            'facebook_secret_key':                      "",
            'facebook_access_token':                    "",
            'facebook_signed_request':                  "",
            'facebook_user_id':                         0,
            'facebook_email':                           "",
            'facebook_first_name':                      "",
            'facebook_middle_name':                     "",
            'facebook_last_name':                       "",
            'facebook_profile_image_url_https':         "",
            'facebook_background_image_url_https':      "",
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    ""
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_has_data_to_preserve = voter.has_data_to_preserve()

    facebook_manager = FacebookManager()
    auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    status = auth_response_results['status']
    if not auth_response_results['facebook_auth_response_found']:
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   status,
            'voter_device_id':                          voter_device_id,
            'voter_we_vote_id':                         voter_we_vote_id,
            'voter_has_data_to_preserve':               False,
            'existing_facebook_account_found':          False,
            'voter_we_vote_id_attached_to_facebook':    "",
            'voter_we_vote_id_attached_to_facebook_email':  "",
            'facebook_sign_in_found':                   False,
            'facebook_sign_in_verified':                False,
            'facebook_sign_in_failed':                  True,
            'facebook_secret_key':                      "",
            'facebook_access_token':                    "",
            'facebook_signed_request':                  "",
            'facebook_user_id':                         0,
            'facebook_email':                           "",
            'facebook_first_name':                      "",
            'facebook_middle_name':                     "",
            'facebook_last_name':                       "",
            'facebook_profile_image_url_https':         "",
            'facebook_background_image_url_https':      "",
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    ""
        }
        return error_results

    success = True
    facebook_auth_response = auth_response_results['facebook_auth_response']

    if not facebook_auth_response.facebook_user_id:
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   status,
            'voter_device_id':                          voter_device_id,
            'voter_we_vote_id':                         voter_we_vote_id,
            'voter_has_data_to_preserve':               False,
            'existing_facebook_account_found':          False,
            'voter_we_vote_id_attached_to_facebook':    "",
            'voter_we_vote_id_attached_to_facebook_email': "",
            'facebook_sign_in_found':                   False,
            'facebook_sign_in_verified':                False,
            'facebook_sign_in_failed':                  True,
            'facebook_secret_key':                      "",
            'facebook_access_token':                    "",
            'facebook_signed_request':                  "",
            'facebook_user_id':                         0,
            'facebook_email':                           "",
            'facebook_first_name':                      "",
            'facebook_middle_name':                     "",
            'facebook_last_name':                       "",
            'facebook_profile_image_url_https':         "",
            'facebook_background_image_url_https':      "",
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    ""
        }
        return error_results

    facebook_linked_voter_found = False
    facebook_sign_in_verified = True
    facebook_sign_in_failed = False
    facebook_secret_key = ""
    voter_we_vote_id_attached_to_facebook = ""
    voter_manager = VoterManager()
    organization_manager = OrganizationManager()

    facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(facebook_auth_response.facebook_user_id)
    if facebook_link_results['facebook_link_to_voter_found']:
        status += "FACEBOOK_SIGN_IN_RETRIEVE-FACEBOOK_LINK_TO_VOTER_FOUND "
        facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
        status += facebook_link_results['status']
        voter_we_vote_id_attached_to_facebook = facebook_link_to_voter.voter_we_vote_id
        facebook_secret_key = facebook_link_to_voter.secret_key
        repair_facebook_related_voter_caching_now = True
        if positive_value_exists(voter_we_vote_id_attached_to_facebook):
            facebook_linked_voter_results = \
                voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id_attached_to_facebook)
            if facebook_linked_voter_results['voter_found']:
                facebook_linked_voter = facebook_linked_voter_results['voter']
                facebook_linked_voter_found = True

    else:
        # See if we need to heal the data - look in the voter table for any records with a facebook_user_id
        voter_results = voter_manager.retrieve_voter_by_facebook_id_old(facebook_auth_response.facebook_user_id)
        if voter_results['voter_found']:
            facebook_linked_voter = voter_results['voter']
            facebook_linked_voter_found = True
            voter_we_vote_id_attached_to_facebook = facebook_linked_voter.we_vote_id
            if positive_value_exists(voter_we_vote_id_attached_to_facebook):
                status += "FACEBOOK_LINK_TO_VOTER_FOUND-FACEBOOK_USER_ID_IN_VOTER_ENTRY "
                save_results = facebook_manager.create_facebook_link_to_voter(
                    facebook_auth_response.facebook_user_id, voter_we_vote_id_attached_to_facebook)
                status += " " + save_results['status']
                facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(
                    facebook_auth_response.facebook_user_id)
                if facebook_link_results['facebook_link_to_voter_found']:
                    facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
                    repair_facebook_related_voter_caching_now = True

    voter_we_vote_id_attached_to_facebook_email = ""
    if not positive_value_exists(voter_we_vote_id_attached_to_facebook) \
            and positive_value_exists(facebook_auth_response.facebook_email) \
            and positive_value_exists(facebook_auth_response.facebook_user_id):
        # If here, we haven't been able to find the voter based on facebook_link_to_voter
        # or voter.facebook_user_id

        # Now we want to check on the incoming facebook_email to see if it is already in use with another account

        # We do not want to allow people to separate their facebook_email from their facebook account, but
        #  there are conditions where it might happen and we can't prevent it. (Like someone signs in with Email A,
        #  then signs into Facebook which uses Email B, then changes their Facebook email to Email A.)
        status += "CHECK_EMAIL_FOR_LINK_TO_FACEBOOK "
        email_manager = EmailManager()
        temp_voter_we_vote_id = ""
        email_results = email_manager.retrieve_primary_email_with_ownership_verified(
            temp_voter_we_vote_id, facebook_auth_response.facebook_email)
        if email_results['email_address_object_found']:
            status += "FACEBOOK_EMAIL_FOUND_IN_DATABASE "
            # See if we need to heal the data - look in the email table for any records with a facebook_email
            email_address_object = email_results['email_address_object']
            voter_we_vote_id_attached_to_facebook_email = email_address_object.voter_we_vote_id
            voter_we_vote_id_attached_to_facebook = voter_we_vote_id_attached_to_facebook_email

            # Make sure we have the voter that was referred to in the email table
            facebook_linked_voter_results = \
                voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id_attached_to_facebook_email)
            if facebook_linked_voter_results['voter_found']:
                facebook_linked_voter = facebook_linked_voter_results['voter']
                facebook_linked_voter_found = True

                save_results = facebook_manager.create_facebook_link_to_voter(
                    facebook_auth_response.facebook_user_id, voter_we_vote_id_attached_to_facebook_email)
                status += " " + save_results['status']

                if save_results['facebook_link_to_voter_saved']:
                    facebook_link_to_voter = save_results['facebook_link_to_voter']
                    facebook_secret_key = facebook_link_to_voter.secret_key
                else:
                    # else for: if save_results['facebook_link_to_voter_saved']
                    status += save_results['results']
                    status += "UNABLE_TO_SAVE_FACEBOOK_LINK_TO_VOTER "
            else:
                # else for: facebook_linked_voter_results['voter_found']
                status += facebook_linked_voter_results['results']
                status += "UNABLE_TO_FIND_VOTER_REFERRED_TO_BY_EMAIL_TABLE "
        else:
            status += "EMAIL_NOT_FOUND "
            voter_we_vote_id_attached_to_facebook_email = ""

    # Verify we have the organization from facebook_linked_voter
    if facebook_linked_voter_found:
        if positive_value_exists(facebook_linked_voter.linked_organization_we_vote_id):
            organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                facebook_linked_voter.linked_organization_we_vote_id)
            if organization_results['organization_found']:
                # All is good
                facebook_linked_organization = organization_results['organization']
            else:
                # Organization referred to in linked_organization_we_vote_id could not be retrieved.
                # Remove the link to the missing organization so we don't have a future conflict
                try:
                    facebook_linked_voter.linked_organization_we_vote_id = None
                    facebook_linked_voter.save()
                    # All positions should have already been moved with move_positions_to_another_voter
                except Exception as e:
                    status += \
                        "FAILED_TO_REMOVE_FROM_FACEBOOK_LINKED_VOTER-LINKED_ORGANIZATION_WE_VOTE_ID " \
                        "" + str(e) + " "

        # Make sure the facebook voter has an organization
        if not positive_value_exists(facebook_linked_voter.linked_organization_we_vote_id):
            # Heal the data
            repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(
                facebook_linked_voter)
            status += repair_results['status']
            if repair_results['voter_repaired']:
                facebook_linked_voter = repair_results['voter']
            else:
                status += "FACEBOOK_LINKED_VOTER_NOT_REPAIRED "

    if repair_facebook_related_voter_caching_now:
        repair_results = voter_manager.repair_facebook_related_voter_caching(facebook_auth_response.facebook_user_id)
        status += repair_results['status']

    if positive_value_exists(voter_we_vote_id_attached_to_facebook):
        existing_facebook_account_found = True
        voter_we_vote_id_for_cache = voter_we_vote_id_attached_to_facebook
    elif positive_value_exists(voter_we_vote_id_attached_to_facebook_email):
        existing_facebook_account_found = True
        voter_we_vote_id_for_cache = voter_we_vote_id_attached_to_facebook_email
    else:
        existing_facebook_account_found = False
        voter_we_vote_id_for_cache = voter_we_vote_id

    # Cache original and resized images
    cache_results = cache_master_and_resized_image(
        voter_we_vote_id=voter_we_vote_id_for_cache,
        facebook_user_id=facebook_auth_response.facebook_user_id,
        facebook_profile_image_url_https=facebook_auth_response.facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_auth_response.facebook_background_image_url_https,
        facebook_background_image_offset_x=facebook_auth_response.facebook_background_image_offset_x,
        facebook_background_image_offset_y=facebook_auth_response.facebook_background_image_offset_y,
        image_source=FACEBOOK)
    cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
    cached_facebook_background_image_url_https = cache_results['cached_facebook_background_image_url_https']
    we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
    we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
    we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

    if positive_value_exists(cached_facebook_profile_image_url_https):
        facebook_profile_image_url_https = cached_facebook_profile_image_url_https
    else:
        facebook_profile_image_url_https = facebook_auth_response.facebook_profile_image_url_https

    if positive_value_exists(cached_facebook_background_image_url_https):
        facebook_background_image_url_https = cached_facebook_background_image_url_https
    else:
        facebook_background_image_url_https = facebook_auth_response.facebook_background_image_url_https

    facebook_user_results = facebook_manager.update_or_create_facebook_user(
        facebook_auth_response.facebook_user_id, facebook_auth_response.facebook_first_name,
        facebook_auth_response.facebook_middle_name, facebook_auth_response.facebook_last_name,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
        we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
        facebook_email=facebook_auth_response.facebook_email)
    status += facebook_user_results['status']

    update_organization_facebook_images(facebook_auth_response.facebook_user_id,
                                        facebook_profile_image_url_https,
                                        facebook_background_image_url_https)

    json_data = {
        'success':                                  success,
        'status':                                   status,
        'voter_device_id':                          voter_device_id,
        'voter_we_vote_id':                         voter_we_vote_id,
        'voter_has_data_to_preserve':               voter_has_data_to_preserve,
        'existing_facebook_account_found':          existing_facebook_account_found,
        'voter_we_vote_id_attached_to_facebook':    voter_we_vote_id_attached_to_facebook,
        'voter_we_vote_id_attached_to_facebook_email':    voter_we_vote_id_attached_to_facebook_email,
        'facebook_sign_in_found':                   auth_response_results['facebook_auth_response_found'],
        'facebook_sign_in_verified':                facebook_sign_in_verified,
        'facebook_sign_in_failed':                  facebook_sign_in_failed,
        'facebook_secret_key':                      facebook_secret_key,
        'facebook_access_token':                    facebook_auth_response.facebook_access_token,
        'facebook_signed_request':                  facebook_auth_response.facebook_signed_request,
        'facebook_user_id':                         facebook_auth_response.facebook_user_id,
        'facebook_email':                           facebook_auth_response.facebook_email if
        positive_value_exists(facebook_auth_response.facebook_email) else "",
        'facebook_first_name':                      facebook_auth_response.facebook_first_name if
        positive_value_exists(facebook_auth_response.facebook_first_name) else "",
        'facebook_middle_name':                     facebook_auth_response.facebook_middle_name if
        positive_value_exists(facebook_auth_response.facebook_middle_name) else "",
        'facebook_last_name':                       facebook_auth_response.facebook_last_name if
        positive_value_exists(facebook_auth_response.facebook_last_name) else "",
        'facebook_profile_image_url_https':         facebook_profile_image_url_https,
        'facebook_background_image_url_https':      facebook_background_image_url_https,
        'we_vote_hosted_profile_image_url_large':   we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny,
    }
    return json_data


def update_organization_facebook_images(facebook_user_id, facebook_profile_image_url_https,
                                        facebook_background_image_url_https):
    """
    Store the links to the cached facebook images in the Organization
    :param facebook_user_id:
    :param facebook_profile_image_url_https:
    :param facebook_background_image_url_https:
    :return:
    """
    organization_manager = OrganizationManager()
    organization_results = organization_manager.retrieve_organization_from_facebook_id(facebook_id=facebook_user_id)
    if organization_results['success']:
        organization = organization_results['organization']

        organization_updated = False
        if positive_value_exists(facebook_profile_image_url_https):
            organization.facebook_profile_image_url_https = facebook_profile_image_url_https
            organization_updated = True
        if positive_value_exists(facebook_background_image_url_https):
            organization.facebook_background_image_url_https = facebook_background_image_url_https
            organization_updated = True

        if organization_updated:
            try:
                organization.save()
                logger.info("update_organization_facebook_images saved updated images for organization: " +
                            organization.we_vote_id + ", facebook_id: " + str(organization.facebook_id))
                return
            except Exception as e:
                logger.error("update_organization_facebook_images threw: " + str(e))
        return
    logger.error("update_organization_facebook_images unable to retrieve Organization with facebook_user_id: " +
                 str(facebook_user_id))
    return


def voter_facebook_sign_in_save_for_api(voter_device_id,  # voterFacebookSignInSave
                                        save_auth_data,
                                        facebook_access_token, facebook_user_id, facebook_expires_in,
                                        facebook_signed_request,
                                        save_profile_data,
                                        facebook_email, facebook_first_name, facebook_middle_name, facebook_last_name,
                                        save_photo_data,
                                        facebook_profile_image_url_https, facebook_background_image_url_https,
                                        facebook_background_image_offset_x, facebook_background_image_offset_y):
    """

    :param voter_device_id:
    :param save_auth_data:
    :param facebook_access_token:
    :param facebook_user_id:
    :param facebook_expires_in:
    :param facebook_signed_request:
    :param save_profile_data:
    :param facebook_email:
    :param facebook_first_name:
    :param facebook_middle_name:
    :param facebook_last_name:
    :param save_photo_data:
    :param facebook_profile_image_url_https:
    :param facebook_background_image_url_https:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :return:
    """
    status = ""

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                   device_id_results['status'],
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'facebook_sign_in_saved':   False,
            'save_auth_data':           save_auth_data,
            'save_profile_data':        save_profile_data,
            'minimum_data_saved':       False,
        }
        return json_data

    if not save_auth_data and not save_profile_data and not save_photo_data:
        error_results = {
            'status':                   "VOTER_FACEBOOK_SIGN_IN_SAVE_MUST_SPECIFY_AUTH_OR_PROFILE ",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'facebook_sign_in_saved':   False,
            'save_auth_data':           save_auth_data,
            'save_profile_data':        save_profile_data,
            'minimum_data_saved':       False,
        }
        return error_results

    facebook_manager = FacebookManager()
    auth_data_results = facebook_manager.update_or_create_facebook_auth_response(
        voter_device_id, facebook_access_token, facebook_user_id, facebook_expires_in,
        facebook_signed_request,
        facebook_email, facebook_first_name, facebook_middle_name, facebook_last_name,
        facebook_profile_image_url_https, facebook_background_image_url_https,
        facebook_background_image_offset_x, facebook_background_image_offset_y)
    # Look to see if there is an EmailAddress entry for the incoming text_for_email_address or email_we_vote_id
    if not auth_data_results['facebook_auth_response_saved']:
        error_results = {
            'status':                   "FACEBOOK_AUTH_NOT_SAVED ",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'facebook_sign_in_saved':   False,
            'save_auth_data':           save_auth_data,
            'save_profile_data':        save_profile_data,
            'minimum_data_saved':       False,
        }
        return error_results

    success = auth_data_results['success']
    status += auth_data_results['status']

    # Is this the last save for this Facebook user?
    # facebook_profile_image_url_https could have some error that's why marking minimum_data_saved
    # minimum_data_saved = positive_value_exists(facebook_profile_image_url_https)
    # if facebook_user_id value is positive we know there was a save
    minimum_data_saved = positive_value_exists(facebook_user_id)

    json_data = {
        'status':                   status,
        'success':                  success,
        'voter_device_id':          voter_device_id,
        'facebook_sign_in_saved':   auth_data_results['facebook_auth_response_saved'],
        'save_auth_data':           save_auth_data,
        'save_profile_data':        save_profile_data,
        'minimum_data_saved':       minimum_data_saved,
    }
    return json_data


def get_facebook_photo_url_from_graphapi(facebook_candidate_url):
    photo_url = ""
    status = ""
    clean_message = ''
    success = False

    m = re.search(r'^.*?facebook.com/(.*?)((/$)|($)|(/.*?$))', facebook_candidate_url)
    fb_id_or_login_name = m.group(1)

    if len(m.groups()) < 2:
        status += 'GET_FACEBOOK_PHOTO_URL_FROM_GRAPHAPI-PROPER_URL_NOT_PROVIDED: ' + facebook_candidate_url + " "
    else:
        results = FacebookManager.retrieve_facebook_photo_from_person_id(fb_id_or_login_name)
        status += results['status']
        photo_url = results['url']

        if len(photo_url) < 1:
            status += 'GET_FACEBOOK_PHOTO_URL_FROM_GRAPHAPI-PHOTO_RETRIEVE_FAILED: ' + facebook_candidate_url + " "
            clean_message = "Facebook did not return a photo for '{}' for the URL entered on this page. " \
                            "Possible reasons:  " \
                            "1) The campaign has not granted 'apps' access permission for this page. " \
                            "2) The page is no longer published.  3) The URL is incorrect.".format(fb_id_or_login_name)
        else:
            status += 'GET_FACEBOOK_PHOTO_URL_FROM_GRAPHAPI-SUCCESS '
            success = True

    results = {
        'status':               status,
        'success':              success,
        'photo_url':            photo_url,
        'is_silhouette':        results['is_silhouette'],
        'clean_message':        clean_message,
    }
    return results
