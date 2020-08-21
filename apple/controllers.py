# apple/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from apple.models import AppleUser
from voter.controllers import voter_merge_two_accounts_action
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists
import wevote_functions.admin
from .jwt_apple_signin import retrieve_user

logger = wevote_functions.admin.get_logger(__name__)


def apple_sign_in_save_merge_if_needed(
        email_from_apple='',
        previously_signed_in_apple_voter_found=False,
        previously_signed_in_apple_voter_we_vote_id='',
        voter_device_link=None,
        voter_starting_process=None):
    status = ''
    success = True
    previously_signed_in_voter = None
    previously_signed_in_voter_found = False
    previously_signed_in_voter_we_vote_id = ''
    voter_manager = VoterManager()

    try:
        # Test to see if we have a valid voter_starting_process object
        voter_starting_process_we_vote_id = voter_starting_process.we_vote_id
    except Exception as e:
        status += "VOTER_STARTING_PROCESS_NOT_FOUND: " + str(e) + ' '
        results = {
            'status': status,
            'success': False,
            'previously_signed_in_voter': previously_signed_in_voter,
            'previously_signed_in_voter_found': previously_signed_in_voter_found,
            'previously_signed_in_voter_we_vote_id': previously_signed_in_voter_we_vote_id,
        }
        return results

    try:
        # Test to see if we have a valid voter_device_link object
        voter_id_in_voter_device_link = voter_device_link.voter_id
    except Exception as e:
        status += "VOTER_DEVICE_LINK_NOT_FOUND: " + str(e) + ' '
        results = {
            'status': status,
            'success': False,
            'previously_signed_in_voter': previously_signed_in_voter,
            'previously_signed_in_voter_found': previously_signed_in_voter_found,
            'previously_signed_in_voter_we_vote_id': previously_signed_in_voter_we_vote_id,
        }
        return results

    status += "EMAIL_FROM_APPLE(" + str(email_from_apple) + ") "
    if previously_signed_in_apple_voter_found and positive_value_exists(previously_signed_in_apple_voter_we_vote_id):
        results = voter_manager.retrieve_voter_by_we_vote_id(
            previously_signed_in_apple_voter_we_vote_id, read_only=False)
        if results['voter_found']:
            # This is the voter account the person is using when they click "Sign in with Apple"
            previously_signed_in_voter = results['voter']
            previously_signed_in_voter_we_vote_id = previously_signed_in_voter.we_vote_id
            previously_signed_in_voter_found = True
            status += "PREVIOUSLY_SIGNED_IN_VOTER_FOUND_BY_APPLE_WE_VOTE_ID "
        else:
            status += results['status']
            status += "PREVIOUSLY_SIGNED_IN_VOTER_NOT_FOUND_BY_APPLE_WE_VOTE_ID "
    elif positive_value_exists(email_from_apple):
        # This is a new sign in, so we want to check to make sure we don't have an account with this email already
        results = voter_manager.retrieve_voter_by_email(email_from_apple, read_only=False)
        if results['voter_found']:
            previously_signed_in_voter = results['voter']
            previously_signed_in_voter_we_vote_id = previously_signed_in_voter.we_vote_id
            previously_signed_in_voter_found = True
            status += "VOTER_WITH_MATCHING_EMAIL_FOUND(" + str(email_from_apple) + ") "
        else:
            status += results['status']
            status += "VOTER_WITH_MATCHING_EMAIL_NOT_FOUND(" + str(email_from_apple) + ") "
    else:
        status += "NO_PRIOR_VOTER_FOUND "

    if previously_signed_in_voter_found:
        status += "PREVIOUSLY_SIGNED_IN_VOTER-" + str(previously_signed_in_voter_we_vote_id) + " "
        merge_results = voter_merge_two_accounts_action(
            voter_starting_process,
            previously_signed_in_voter,
            voter_device_link,
            status=status,
            email_owner_voter_found=False,
            facebook_owner_voter_found=False,
            invitation_owner_voter_found=False)
        status += merge_results['status']

    results = {
        'status':                                   status,
        'success':                                  success,
        'previously_signed_in_voter':               previously_signed_in_voter,
        'previously_signed_in_voter_found':         previously_signed_in_voter_found,
        'previously_signed_in_voter_we_vote_id':    previously_signed_in_voter_we_vote_id,
    }
    return results


# def apple_sign_in_retrieve_voter_id(email, first_name, last_name):
#
#     # look for an email match in voters
#     voter_results = voter_manager.retrieve_voter_list_with_emails()
#     for voter in voter_results['voter_list']:
#         if voter.email == email:
#             voter_we_vote_id = voter.we_vote_id
#             if positive_value_exists(voter_we_vote_id):
#                 success = True
#                 results = {
#                     'success': success,
#                     'status': "APPLE_SIGN_IN_FOUND_A_VOTER_ID_BY_EMAIL ",
#                     'voter_device_id': voter_device_id,
#                     'voter_we_vote_id': voter_we_vote_id,
#                 }
#                 return results
#
#     # next look for a name match in voters
#     voter_results = voter_manager.retrieve_voter_list_by_name(first_name, last_name)
#     for voter in voter_results['voter_list']:
#         voter_we_vote_id = voter.we_vote_id
#         if positive_value_exists(voter_we_vote_id):
#             success = True
#             results = {
#                 'success': success,
#                 'status': "APPLE_SIGN_IN_FOUND_A_VOTER_ID_BY_NAME_MATCH ",
#                 'voter_device_id': voter_device_id,
#                 'voter_we_vote_id': voter_we_vote_id,
#             }
#             return results
#
#     return True


def move_apple_user_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = False
    apple_user_entries_moved = 0
    apple_user_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_APPLE_USER_ENTRIES_TO_ANOTHER_VOTER-" \
                  "Missing either from_voter_we_vote_id or to_voter_we_vote_id "
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_we_vote_id':    from_voter_we_vote_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'apple_user_entries_moved':     apple_user_entries_moved,
            'apple_user_entries_not_moved': apple_user_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_APPLE_USER_ENTRIES_TO_ANOTHER_VOTER-" \
                  "from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_we_vote_id':    from_voter_we_vote_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'apple_user_entries_moved':     apple_user_entries_moved,
            'apple_user_entries_not_moved': apple_user_entries_not_moved,
        }
        return results

    apple_users_query = AppleUser.objects.all()
    apple_users_query = apple_users_query.filter(
        voter_we_vote_id__iexact=from_voter_we_vote_id)
    apple_users_list = list(apple_users_query)
    for apple_user_link in apple_users_list:
        try:
            apple_user_link.voter_we_vote_id = to_voter_we_vote_id
            apple_user_link.save()
            apple_user_entries_moved += 1
        except Exception as e:
            # This might just mean that another entry already exists for the "to" voter
            status += "COULD_NOT_SAVE_APPLE_USER: " + str(e) + ' '
            apple_user_entries_not_moved += 1

    results = {
        'status':                   status,
        'success':                  success,
        'from_voter_we_vote_id':    from_voter_we_vote_id,
        'to_voter_we_vote_id':      to_voter_we_vote_id,
        'apple_user_entries_moved':     apple_user_entries_moved,
        'apple_user_entries_not_moved': apple_user_entries_not_moved,
    }
    return results


def validate_sign_in_with_apple_token_for_api(apple_oauth_code):
    # apple.jwt_apple_signin.retrieve_user(apple_oauth_code)
    appleUser = retrieve_user(apple_oauth_code)
    print(appleUser)
    logger.debug('appleuser: ', appleUser)
