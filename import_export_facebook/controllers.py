# import_export_facebook/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def facebook_sign_in_for_api(voter_device_id, facebook_id=None, facebook_email=None):  # facebookSignIn
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
            'facebook_id': facebook_id,
            'facebook_email': facebook_email,
        }
        return results

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not positive_value_exists(results['voter_found']):
        results = {
            'success': False,
            'status': "VALID_VOTER_MISSING",
            'voter_device_id': voter_device_id,
            'facebook_id': facebook_id,
            'facebook_email': facebook_email,
        }
        return results

    voter = results['voter']

    results_from_facebook_id = voter_manager.retrieve_voter_by_facebook_id(facebook_id)
    if positive_value_exists(results_from_facebook_id['voter_found']):
        voter_found_with_facebook_id = results_from_facebook_id['voter']
        if voter_found_with_facebook_id.id == voter.id:
            # If here, the owner of the facebook_id is already the current primary voter
            status += "FACEBOOK_SIGN_IN-ALREADY_LINKED_TO_THIS_FACEBOOK_ACCOUNT "
            success = True
            # Only save if the email is different than what is saved
            if positive_value_exists(facebook_email) or facebook_email == '':
                results = voter_manager.save_facebook_user_values(voter, facebook_id, facebook_email)
                status += results['status']
                success = results['success']
        else:
            # If here, we need to merge accounts TODO

            # ...but for now we are simply going to switch to the earlier account and abandon
            # the newer account
            if positive_value_exists(facebook_email) or facebook_email == '':
                results = voter_manager.save_facebook_user_values(voter_found_with_facebook_id,
                                                                  facebook_id, facebook_email)
                status += results['status'] + ", "
                success = results['success']

            # Relink this voter_device_id to the original account
            voter_device_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_manager.retrieve_voter_device_link(voter_device_id)
            voter_device_link = voter_device_link_results['voter_device_link']

            update_voter_device_link_results = voter_device_manager.update_voter_device_link(
                voter_device_link, voter_found_with_facebook_id)
            if update_voter_device_link_results['voter_device_link_updated']:
                status += "FACEBOOK_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT-TRANSFERRED "
                success = True
            else:
                status = "FACEBOOK_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT-COULD_NOT_TRANSFER "
                success = False
    else:
        # An existing account linked to this facebook account was not found
        results = voter_manager.save_facebook_user_values(voter, facebook_id, facebook_email)
        status = results['status']
        success = results['success']

    if success:
        results = {
            'success': True,
            'status': status,
            'voter_device_id': voter_device_id,
            'facebook_id': facebook_id,
            'facebook_email': facebook_email,
        }
    else:
        results = {
            'success': False,
            'status': status,
            'voter_device_id': voter_device_id,
            'facebook_id': facebook_id,
            'facebook_email': facebook_email,
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

    facebook_id = 0
    results = voter_manager.save_facebook_user_values(voter, facebook_id)
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
