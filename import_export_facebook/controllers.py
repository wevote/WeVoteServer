# import_export_facebook/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from email_outbound.models import EmailManager
from import_export_facebook.models import FacebookManager
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def voter_facebook_save_to_current_account_for_api(voter_device_id):  # voterFacebookSaveToCurrentAccount
    """

    :param voter_device_id:
    :return:
    """
    status = ""
    success = False
    # Get voter_id from the voter_device_id
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'success': False,
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id': voter_device_id,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'success': False,
            'status': "VALID_VOTER_MISSING",
            'voter_device_id': voter_device_id,
        }
        return results

    voter = results['voter']

    facebook_manager = FacebookManager()
    facebook_results = facebook_manager.retrieve_facebook_link_to_voter(voter.we_vote_id)
    if facebook_results['facebook_link_to_voter_found']:
        error_results = {
            'status': "FACEBOOK_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return error_results

    auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    if not auth_response_results['facebook_auth_response_found']:
        error_results = {
            'status': "FACEBOOK_OWNER_VOTER_FOUND_WHEN_NOT_EXPECTED",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return error_results

    facebook_auth_response = auth_response_results['facebook_auth_response']

    link_results = facebook_manager.create_facebook_link_to_voter(facebook_auth_response.facebook_user_id,
                                                                  voter.we_vote_id)

    if not link_results['facebook_link_to_voter_saved']:
        error_results = {
            'status': link_results['status'],
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return error_results

    facebook_link_to_voter = link_results['facebook_link_to_voter']

    # Update voter with Facebook info (not including email -- that is done below)
    results = voter_manager.save_facebook_user_values(voter, facebook_auth_response)
    status += results['status'] + ", "
    success = results['success']
    voter = results['voter']

    # ##### Make the facebook_email the primary email for the current voter
    # Does the current voter already have a primary email?
    if not voter.email_ownership_is_verified:
        email_manager = EmailManager()
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
                    voter.we_vote_id)
                if email_retrieve_results['email_address_object_found']:
                    email_address_object = email_retrieve_results['email_address_object']
                    email_address_object = email_manager.update_email_address_object_to_be_verified(
                        email_address_object)
                else:
                    email_ownership_is_verified = True
                    email_create_results = email_manager.create_email_address(
                        facebook_auth_response.facebook_email, voter.we_vote_id,
                        email_ownership_is_verified)
                    if email_create_results['email_address_object_saved']:
                        email_address_object = email_create_results['email_address_object']
                try:
                    # Attach the email_address_object to voter
                    voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
                except Exception as e:
                    # Fail silently
                    pass

    results = {
        'success': success,
        'status': status,
        'voter_device_id': voter_device_id,
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

    :param voter_device_id:
    :return:
    """
    facebook_manager = FacebookManager()
    auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    status = auth_response_results['status']
    if not auth_response_results['facebook_auth_response_found']:
        success = False
        error_results = {
            'success':                                  success,
            'status':                                   status,
            'voter_device_id':                          voter_device_id,
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
        }
        return error_results

    facebook_sign_in_verified = True
    facebook_sign_in_failed = False
    facebook_secret_key = ""
    voter_we_vote_id_attached_to_facebook = ""

    facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(facebook_auth_response.facebook_user_id)
    if facebook_link_results['facebook_link_to_voter_found']:
        facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
        status += " " + facebook_link_results['status']
        voter_we_vote_id_attached_to_facebook = facebook_link_to_voter.voter_we_vote_id
        facebook_secret_key = facebook_link_to_voter.secret_key
    else:
        # See if we need to heal the data - look in the voter table for any records with a facebook_user_id
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_by_facebook_id(facebook_auth_response.facebook_user_id)
        if voter_results['voter_found']:
            voter_with_facebook_user_id = voter_results['voter']
            voter_we_vote_id_attached_to_facebook = voter_with_facebook_user_id.we_vote_id
            if positive_value_exists(voter_we_vote_id_attached_to_facebook):
                save_results = facebook_manager.create_facebook_link_to_voter(
                    facebook_auth_response.facebook_user_id, voter_we_vote_id_attached_to_facebook)
                status += " " + save_results['status']

    # Now we want to check on the incoming facebook_email to see if it is already in use with another account
    # We do not want to allow people to separate their facebook_email from their facebook account, but
    #  there are conditions where it might happen and we can't prevent it. (Like someone signs in with Email A,
    #  then signs into Facebook which uses Email B, then changes their Facebook email to Email A.)
    email_manager = EmailManager()
    temp_voter_we_vote_id = ""
    email_results = email_manager.retrieve_primary_email_with_ownership_verified(
        temp_voter_we_vote_id, facebook_auth_response.facebook_email)
    if email_results['email_address_object_found']:
        email_address_object = email_results['email_address_object']
        voter_we_vote_id_attached_to_facebook_email = email_address_object.voter_we_vote_id
    else:
        voter_we_vote_id_attached_to_facebook_email = ""

    json_data = {
        'success':                                  success,
        'status':                                   status,
        'voter_device_id':                          voter_device_id,
        'voter_we_vote_id_attached_to_facebook':    voter_we_vote_id_attached_to_facebook,
        'voter_we_vote_id_attached_to_facebook_email':    voter_we_vote_id_attached_to_facebook_email,
        'facebook_sign_in_found':                   auth_response_results['facebook_auth_response_found'],
        'facebook_sign_in_verified':                facebook_sign_in_verified,
        'facebook_sign_in_failed':                  facebook_sign_in_failed,
        'facebook_secret_key':                      facebook_secret_key,
        'facebook_access_token':                    facebook_auth_response.facebook_access_token,
        'facebook_signed_request':                  facebook_auth_response.facebook_signed_request,
        'facebook_user_id':                         facebook_auth_response.facebook_user_id,
        'facebook_email':                           facebook_auth_response.facebook_email,
        'facebook_first_name':                      facebook_auth_response.facebook_first_name,
        'facebook_middle_name':                     facebook_auth_response.facebook_middle_name,
        'facebook_last_name':                       facebook_auth_response.facebook_last_name,
        'facebook_profile_image_url_https':         facebook_auth_response.facebook_profile_image_url_https,
    }
    return json_data


def voter_facebook_sign_in_save_for_api(voter_device_id,  # voterFacebookSignInSave
                                        save_auth_data,
                                        facebook_access_token, facebook_user_id, facebook_expires_in,
                                        facebook_signed_request,
                                        save_profile_data,
                                        facebook_email, facebook_first_name, facebook_middle_name, facebook_last_name,
                                        facebook_profile_image_url_https):
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
    :param facebook_profile_image_url_https:
    :return:
    """
    status = ""

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                       device_id_results['status'],
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'facebook_sign_in_saved':       False,
            'save_auth_data':               save_auth_data,
            'save_profile_data':            save_profile_data,
        }
        return json_data

    if not save_auth_data and not save_profile_data:
        error_results = {
            'status':                       "VOTER_FACEBOOK_SIGN_IN_SAVE_MUST_SPECIFY_AUTH_OR_PROFILE ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'facebook_sign_in_saved':       False,
            'save_auth_data':               save_auth_data,
            'save_profile_data':            save_profile_data,
        }
        return error_results

    facebook_manager = FacebookManager()
    auth_data_results = facebook_manager.update_or_create_facebook_auth_response(
        voter_device_id, facebook_access_token, facebook_user_id, facebook_expires_in,
        facebook_signed_request,
        facebook_email, facebook_first_name, facebook_middle_name, facebook_last_name,
        facebook_profile_image_url_https)
    # Look to see if there is an EmailAddress entry for the incoming text_for_email_address or email_we_vote_id
    if not auth_data_results['facebook_auth_response_saved']:
        error_results = {
            'status':                       "FACEBOOK_AUTH_NOT_SAVED ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'facebook_sign_in_saved':       False,
            'save_auth_data':               save_auth_data,
            'save_profile_data':            save_profile_data,
        }
        return error_results

    success = auth_data_results['success']
    status += auth_data_results['status']

    json_data = {
        'status':                   status,
        'success':                  success,
        'voter_device_id':          voter_device_id,
        'facebook_sign_in_saved':   auth_data_results['facebook_auth_response_saved'],
        'save_auth_data':           save_auth_data,
        'save_profile_data':        save_profile_data,
    }
    return json_data
