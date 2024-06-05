# import_export_facebook/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import re
from time import time

import wevote_functions.admin
from aws.controllers import submit_web_function_job
from config.base import get_environment_variable, get_environment_variable_default
from email_outbound.models import EmailManager
from friend.models import FriendManager
from import_export_facebook.models import FacebookManager
from organization.models import OrganizationManager, INDIVIDUAL
from voter.controllers import voter_cache_facebook_images_process
from voter.models import VoterManager, Voter
from wevote_functions.functions import is_voter_device_id_valid, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
LOG_OAUTH = get_environment_variable_default("TWITTER_LOG_OAUTH_STEPS", False)


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
    facebook_results = facebook_manager.retrieve_facebook_link_to_voter(
        voter_we_vote_id=voter.we_vote_id, read_only=True)
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

    facebook_account_created = True
    facebook_link_to_voter = link_results['facebook_link_to_voter']

    if not positive_value_exists(facebook_auth_response.facebook_profile_image_url_https):
        results = get_facebook_photo_url_from_facebook_url('', facebook_auth_response.facebook_user_id)
        if results['photo_url_found']:
            photo_url = results['photo_url']
            if positive_value_exists(photo_url):
                facebook_auth_response.facebook_profile_image_url_https = photo_url
    # Cache original and resized images in a SQS job
    # print('------------------------ submit_web_function_job in process', os.getpid())
    process_in_sqs_job = True  # Switch to 'False' to test locally without an SQS job
    if process_in_sqs_job:
        submit_web_function_job('voter_cache_facebook_images_process', {
                        'voter_id': voter.id,
                        'facebook_auth_response_id': facebook_auth_response.id,
                        'is_retrieve': False,
                    })
        status += " FACEBOOK_IMAGES_SCHEDULED_TO_BE_CACHED_VIA_SQS "
    else:
        voter_cache_facebook_images_process(voter.id, facebook_auth_response.id, False)
        status += " FACEBOOK_IMAGES_CACHED_DURING_SIGN_IN_PROCESS "

    success = True

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
    However, we use the Facebook "games" api "invitable_friends" data on the fly from the webapp, to invite facebook
    friends who are not using we vote.
    :param voter_device_id:
    :return:
    """
    status = ''
    success = True
    facebook_friends_using_we_vote_list = []
    facebook_friend_suggestion_found = False
    facebook_suggested_friend_count = 0

    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        success = False
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
        if not auth_response_results['success']:
            success = False
        error_results = {
            'status':                               "FACEBOOK_AUTH_RESPONSE_NOT_FOUND ",
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
    if not facebook_friends_from_facebook_results['success']:
        success = False
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
            if not facebook_user_results['success']:
                success = False

    # Find facebook_link_to_voter for all users and then updating SuggestedFriend table
    facebook_auth_response = auth_response_results['facebook_auth_response']
    my_facebook_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter(
        facebook_auth_response.facebook_user_id, read_only=True)
    status += ' ' + my_facebook_link_to_voter_results['status']
    if not my_facebook_link_to_voter_results['success']:
        success = False
    if my_facebook_link_to_voter_results['facebook_link_to_voter_found']:
        friend_manager = FriendManager()
        viewer_voter_we_vote_id = my_facebook_link_to_voter_results['facebook_link_to_voter'].voter_we_vote_id
        for facebook_user_entry in facebook_friends_using_we_vote_list:
            facebook_user_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter(
                facebook_user_entry['facebook_user_id'], read_only=True)
            status += ' ' + facebook_user_link_to_voter_results['status']
            if not facebook_user_link_to_voter_results['success']:
                success = False
            if facebook_user_link_to_voter_results['facebook_link_to_voter_found']:
                viewee_voter_we_vote_id = facebook_user_link_to_voter_results['facebook_link_to_voter'].voter_we_vote_id
                # Are they already friends?
                already_friend_results = friend_manager.retrieve_current_friend(viewer_voter_we_vote_id,
                                                                                viewee_voter_we_vote_id)
                if not already_friend_results['success']:
                    success = False
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


def caching_facebook_images_for_retrieve_process(repair_facebook_related_voter_caching_now,
                                                 facebook_auth_response_id,
                                                 voter_we_vote_id_attached_to_facebook,
                                                 voter_we_vote_id_attached_to_facebook_email,
                                                 voter_we_vote_id):
    # Invoked from a SQS queue message (job)
    # Cache original and resized images

    t0 = time()
    status = ''

    # print('----------- INSIDE SQS PROCESS caching_facebook_images_for_retrieve_process 369  facebook_auth_response_id ', facebook_auth_response_id)
    facebook_manager = FacebookManager()
    facebook_auth_response = facebook_manager.retrieve_facebook_auth_response_by_id(facebook_auth_response_id)
    voter = Voter.objects.get(we_vote_id=voter_we_vote_id)  # Voter existed immediately before the call, so safe
    if LOG_OAUTH:
        logger.error('(Ok) caching_facebook_images_for_retrieve_process voter %s' % voter.we_vote_id)

    results = voter_cache_facebook_images_process(voter.id, facebook_auth_response_id, True)

    facebook_manager = FacebookManager()
    facebook_user_results = facebook_manager.update_or_create_facebook_user(
        facebook_auth_response.facebook_user_id, facebook_auth_response.facebook_first_name,
        facebook_auth_response.facebook_middle_name, facebook_auth_response.facebook_last_name,
        facebook_profile_image_url_https=facebook_auth_response.facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_auth_response.facebook_background_image_url_https,
        we_vote_hosted_profile_image_url_large=results['we_vote_hosted_profile_image_url_large'],
        we_vote_hosted_profile_image_url_medium=results['we_vote_hosted_profile_image_url_medium'],
        we_vote_hosted_profile_image_url_tiny=results['we_vote_hosted_profile_image_url_tiny'],
        facebook_email=facebook_auth_response.facebook_email)
    status += facebook_user_results['status']

    update_organization_facebook_images(facebook_auth_response.facebook_user_id,
                                        facebook_auth_response.facebook_profile_image_url_https,
                                        facebook_auth_response.facebook_background_image_url_https)
    dtc = time() - t0
    logger.error(
        '(Ok) SQS Processing the facebook images for a RETRIEVE for voter %s %s (%s) took %.3f seconds' %
        (facebook_auth_response.facebook_first_name, facebook_auth_response.facebook_last_name,
         voter_we_vote_id, dtc))
    logger.debug('caching_facebook_images_for_retrieve_process status: ' + status)


def voter_facebook_sign_in_retrieve_for_api(voter_device_id):  # voterFacebookSignInRetrieve
    """
    After signing into facebook, retrieve the voter information for use in the WebApp
    :param voter_device_id:
    :return:
    """
    t0 = time()
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
    t1 = time()

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

    facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(
        facebook_auth_response.facebook_user_id, read_only=True)
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
                    facebook_auth_response.facebook_user_id, read_only=True)
                if facebook_link_results['facebook_link_to_voter_found']:
                    facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
                    repair_facebook_related_voter_caching_now = True

    t2 = time()
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
    t3 = time()

    # Cache original and resized images in a SQS message (job) for read

    process_in_sqs_job = True  # Switch to 'False' to test locally without an SQS job
    if process_in_sqs_job:
        # print('----- BEFORE SQS CALL caching_facebook_images_for_retrieve_process in process', os.getpid())
        submit_web_function_job('caching_facebook_images_for_retrieve_process', {
                            'repair_facebook_related_voter_caching_now': repair_facebook_related_voter_caching_now,
                            'facebook_auth_response_id': facebook_auth_response.id,
                            'voter_we_vote_id_attached_to_facebook': voter_we_vote_id_attached_to_facebook,
                            'voter_we_vote_id_attached_to_facebook_email': voter_we_vote_id_attached_to_facebook_email,
                            'voter_we_vote_id': voter_we_vote_id,
                        })
        status += " FACEBOOK_IMAGES_SCHEDULED_TO_BE_CACHED_VIA_SQS_BY_RETRIEVE"
    else:
        caching_facebook_images_for_retrieve_process(
            repair_facebook_related_voter_caching_now,
            facebook_auth_response.id,
            voter_we_vote_id_attached_to_facebook,
            voter_we_vote_id_attached_to_facebook_email,
            voter_we_vote_id)

    t4 = time()

    fbuser = None
    facebook_user_results = facebook_manager.retrieve_facebook_user_by_facebook_user_id(
        facebook_auth_response.facebook_user_id)
    if facebook_user_results['facebook_user_found']:
        fbuser = facebook_user_results['facebook_user']

    facebook_profile_image_url_https = fbuser.facebook_profile_image_url_https if fbuser else ''
    facebook_background_image_url_https = fbuser.facebook_background_image_url_https if fbuser else ''
    we_vote_hosted_profile_image_url_large = fbuser.we_vote_hosted_profile_image_url_large if fbuser else ''
    we_vote_hosted_profile_image_url_medium = fbuser.we_vote_hosted_profile_image_url_medium if fbuser else ''
    we_vote_hosted_profile_image_url_tiny = fbuser.we_vote_hosted_profile_image_url_tiny if fbuser else ''

    t5 = time()
    dt0 = t1 - t0
    dt1 = t2 - t1
    dt2 = t3 - t2
    dt3 = t4 - t3
    dt4 = t5 - t4
    dt = t5 - t0
    logger.error('(Ok) RETRIEVE voter_facebook_sign_in_retrieve_for_api step 1 took ' + "{:.6f}".format(dt0) +
                 ' seconds, step 2 took ' + "{:.6f}".format(dt1) +
                 ' seconds, step 3 (SQS queueing) took ' + "{:.6f}".format(dt2) +
                 ' seconds, step 4 took ' + "{:.6f}".format(dt3) +
                 ' seconds, step 5 took ' + "{:.6f}".format(dt4) +
                 ' seconds, total took ' + "{:.6f}".format(dt) + ' seconds')
    json_data = {
        'success':                                  success,
        'status':                                   status,
        'voter_device_id':                          voter_device_id,
        'voter_we_vote_id':                         voter_we_vote_id,
        'voter_has_data_to_preserve':               voter_has_data_to_preserve,
        'existing_facebook_account_found':          positive_value_exists(facebook_auth_response.facebook_user_id),
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


def voter_facebook_sign_in_save_auth_for_api(
        voter_device_id,  # voterFacebookSignInSave
        save_auth_data,
        facebook_access_token,
        facebook_user_id,
        facebook_expires_in,
        facebook_signed_request,
        save_profile_data,
        facebook_email,
        facebook_first_name,
        facebook_middle_name,
        facebook_last_name,
        save_photo_data,
        facebook_profile_image_url_https,
        facebook_background_image_url_https,
        facebook_background_image_offset_x,
        facebook_background_image_offset_y):
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


def get_facebook_photo_url_from_facebook_url(
        facebook_candidate_url,
        facebook_id=False):
    clean_message = ''
    fb_id_or_login_name = ''
    is_silhouette = False
    photo_url = ""
    photo_url_found = False
    status = ""
    success = True

    if facebook_id:
        fb_id_or_login_name = facebook_id
    elif facebook_candidate_url:
        try:
            m = re.search(r'^.*?facebook.com/(.*?)((/$)|($)|(/.*?$))', facebook_candidate_url)
            fb_id_or_login_name = m.group(1)
            if len(m.groups()) < 2:
                status += 'GET_FACEBOOK_PHOTO_URL_FROM_GRAPHAPI-PROPER_URL_NOT_PROVIDED: ' + facebook_candidate_url + " "
        except Exception as e:
            status += "ERROR_TRYING_TO_GET_FACEBOOK_PHOTO_ID_OR_LOGIN_NAME: " + str(e) + " "
            success = False
    else:
        status += "MISSING_BOTH_FACEBOOK_ID_AND_URL "

    if positive_value_exists(fb_id_or_login_name):
        results = FacebookManager.retrieve_facebook_photo_from_person_id(fb_id_or_login_name)
        try:
            is_silhouette = results['is_silhouette']
            status += results['status']
            photo_url = results['url']
        except Exception as e:
            status += "UNEXPECTED_RESULTS: " + str(e) + " "
            success = False

        if len(photo_url) < 1:
            photo_url_found = False
            status += 'GET_FACEBOOK_PHOTO_URL_FROM_GRAPHAPI-PHOTO_RETRIEVE_FAILED: ' + facebook_candidate_url + " "
            clean_message = "Facebook did not return a photo for '{}' for the Facebook URL entered on this page. " \
                            "Possible reasons: \n " \
                            "1) The campaign has not granted 'apps' access permission for this page.\n " \
                            "2) The page is no longer published.  \n3) The Facebook URL is incorrect.".\
                            format(fb_id_or_login_name)
        else:
            photo_url_found = True
            status += 'GET_FACEBOOK_PHOTO_URL_FROM_GRAPHAPI-SUCCESS '

    results = {
        'clean_message':        clean_message,
        'is_silhouette':        is_silhouette,
        'photo_url':            photo_url,
        'photo_url_found':      photo_url_found,
        'status':               status,
        'success':              success,
    }
    return results
