# sign_in_with_apple/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from django.db.models import Q
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists
import wevote_functions.admin
from .jwt_apple_signin import retrieve_user, AppleUser

logger = wevote_functions.admin.get_logger(__name__)


def apple_sign_in_retrieve_voter_id(voter_device_id, email, first_name, last_name):
    # First find out if there is an existing voter_id for the existing device_id
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    voter_id = voter_results['voter_id']
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    if positive_value_exists(voter_id):
        success = True
        results = {
            'success': success,
            'status': "APPLE_SIGN_IN_FOUND_A_VOTER_ID_BY_DEVICE_ID ",
            'voter_device_id': voter_device_id,
            'voter_we_vote_id': voter_we_vote_id,
        }
        return results

    # next look for an email match in voters

    voter_results = voter_manager.retrieve_voter_list_with_emails()
    for voter in voter_results['voter_list']:
        if voter.email == email:
            voter_we_vote_id = voter.we_vote_id
            if positive_value_exists(voter_we_vote_id):
                success = True
                results = {
                    'success': success,
                    'status': "APPLE_SIGN_IN_FOUND_A_VOTER_ID_BY_EMAIL ",
                    'voter_device_id': voter_device_id,
                    'voter_we_vote_id': voter_we_vote_id,
                }
                return results

    # next look for a name match in voters
    voter_results = voter_manager.retrieve_voter_list_by_name(first_name, last_name)
    for voter in voter_results['voter_list']:
        voter_we_vote_id = voter.we_vote_id
        if positive_value_exists(voter_we_vote_id):
            success = True
            results = {
                'success': success,
                'status': "APPLE_SIGN_IN_FOUND_A_VOTER_ID_BY_NAME_MATCH ",
                'voter_device_id': voter_device_id,
                'voter_we_vote_id': voter_we_vote_id,
            }
            return results

    return True


def validate_sign_in_with_apple_token_for_api(voter_device_id, apple_oauth_code):
    # apple.jwt_apple_signin.retrieve_user(apple_oauth_code)
    appleUser = retrieve_user(apple_oauth_code)
    print(appleUser)
    logger.debug('appleuser: ', appleUser)