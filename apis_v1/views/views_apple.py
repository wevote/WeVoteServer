# apis_v1/views/views_apple.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from exception.models import print_to_log, handle_exception
import json
from apple.AppleResolver import AppleResolver
from apple.controllers import apple_sign_in_save_merge_if_needed, \
    validate_sign_in_with_apple_token_for_api  # apple_sign_in_retrieve_voter_id,
from apple.models import AppleUser
from config.base import get_environment_variable, get_environment_variable_default
from voter.controllers import voter_merge_two_accounts_action_schedule
from voter.models import VoterDeviceLinkManager, VoterManager  # fetch_voter_we_vote_id_from_voter_device_link,
from wevote_functions.functions import get_voter_device_id, positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
DEBUG_LOGGING = False


def sign_in_with_apple_view(request):  # appleSignInSave appleSignInSaveView
    """
    Handle and store the data from a "Sign In With Apple" login in iOS through Cordova
    :param request:
    :return:
    """
    status = ""
    status += "STARTING-appleSignInSave "
    previously_signed_in_voter = None
    previously_signed_in_voter_found = False
    previously_signed_in_voter_we_vote_id = ''

    # voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    user_code = request.GET.get('user_code', '')
    identity_token = request.GET.get('identity_token', '')
    email = request.GET.get('email', '')
    first_name = request.GET.get('first_name', '')
    middle_name = request.GET.get('middle_name', '')
    last_name = request.GET.get('last_name', '')
    apple_platform = request.GET.get('apple_platform', '')
    apple_os_version = request.GET.get('apple_os_version', '')
    apple_model = request.GET.get('apple_model', '')
    # voter_we_vote_id = request.GET.get('voter_we_vote_id', '')

    if not positive_value_exists(email):
        client_id = get_environment_variable_default('SOCIAL_AUTH_APPLE_CLIENT_ID_IOS', 'org.wevote.cordova')
        results = AppleResolver().authenticate(identity_token, client_id)
        if results:
            user_code = results['subject_registered_claim']
            email = results['email']
            if DEBUG_LOGGING:
                logger.error("awsApple Not an error: Sign in with Apple iOS, (no email decrypted jwt: " + user_code +
                             "  " + email)

    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()

    voter_device_id = get_voter_device_id(request)
    results = voter_device_link_manager.retrieve_voter_device_link(
        voter_device_id, read_only=False)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
    else:
        voter_device_link = None

    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=False)
    if results['voter_found']:
        # This is the voter account the person is using when they click "Sign in with Apple"
        voter_starting_process = results['voter']
        voter_starting_process_we_vote_id = voter_starting_process.we_vote_id
    else:
        voter_starting_process = None
        voter_starting_process_we_vote_id = ''

    if not positive_value_exists(voter_starting_process_we_vote_id):
        status += "VOTER_WE_VOTE_ID_FROM_VOTER_STARTING_PROCESS_MISSING "
        json_data = {
            'status':                                   status,
            'success':                                  False,
            'previously_signed_in_voter':               previously_signed_in_voter,
            'previously_signed_in_voter_found':         previously_signed_in_voter_found,
            'previously_signed_in_voter_we_vote_id':    previously_signed_in_voter_we_vote_id,
        }
        if DEBUG_LOGGING:
            logger.error('awsApple (no voter_starting_process_we_vote_id): ' + status)
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = sign_in_with_apple_for_api(
        user_code=user_code,
        email=email,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        apple_platform=apple_platform,
        apple_os_version=apple_os_version,
        apple_model=apple_model,
        voter_starting_process_we_vote_id=voter_starting_process_we_vote_id)
    previously_signed_in_voter_we_vote_id = results['previously_signed_in_voter_we_vote_id']
    status += results['status']

    merge_results = apple_sign_in_save_merge_if_needed(
        email_from_apple=email,
        previously_signed_in_apple_voter_found=results['previously_signed_in_voter_found'],
        previously_signed_in_apple_voter_we_vote_id=previously_signed_in_voter_we_vote_id,
        voter_device_link=voter_device_link,
        voter_starting_process=voter_starting_process,
    )
    status += merge_results['status']

    merge_from_voter_we_vote_id = voter_starting_process_we_vote_id
    merge_to_voter_we_vote_id = previously_signed_in_voter_we_vote_id
    status += "IOS_VOTER_STARTING_PROCESS_WE_VOTE_ID-" + str(voter_starting_process_we_vote_id) + " "
    status += "IOS_PREVIOUSLY_SIGNED_IN_WE_VOTE_ID-" + str(previously_signed_in_voter_we_vote_id) + " "
    if positive_value_exists(merge_from_voter_we_vote_id) and positive_value_exists(merge_to_voter_we_vote_id):
        voter_results = voter_manager.retrieve_voter_by_we_vote_id(merge_to_voter_we_vote_id)
        if voter_results['success'] and voter_results['voter_found']:
            to_voter = voter_results['voter']
            merge_results = voter_merge_two_accounts_action_schedule(
                from_voter=voter_starting_process,
                to_voter=to_voter,
                voter_device_link=voter_device_link)
            status += merge_results['status']

    if DEBUG_LOGGING:
        logger.error('awsApple (after apple_sign_in_save_merge_if_needed): ' + status)

    json_data = {
        'merge_from_voter_we_vote_id':              merge_from_voter_we_vote_id,
        'merge_to_voter_we_vote_id':                merge_to_voter_we_vote_id,
        'previously_signed_in_voter':               previously_signed_in_voter,
        'previously_signed_in_voter_found':         previously_signed_in_voter_found,
        'previously_signed_in_voter_we_vote_id':    previously_signed_in_voter_we_vote_id,
        'status':                                   status,
        'success':                                  True,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def payload(message, status):
    return HttpResponse(
        json.dumps({"status": status, "payload": message} if message is not None else {"status": status})
    )


def success(message=None):
    return payload(message, "success")


def sign_in_with_apple_for_api(
        user_code='',
        email='',
        first_name='',
        middle_name='',
        last_name='',
        apple_platform='',
        apple_os_version='',
        apple_model='',
        voter_starting_process_we_vote_id=''):
    status = ""
    success_siwa = False
    previously_signed_in_voter_found = False
    previously_signed_in_voter_we_vote_id = ''
    signed_in_voter_we_vote_id = ''

    if not positive_value_exists(user_code):
        status += "CREATE_APPLE_USER_MISSING_REQUIRED_VARIABLE_USER_CODE "
        print_to_log(logger=logger, exception_message_optional=status)
        results = {
            'success': success_siwa,
            'status': status,
            'previously_signed_in_voter_found': '',
            'previously_signed_in_voter_we_vote_id': '',
            'signed_in_voter_we_vote_id': '',
        }
        return results

    #
    # The presence of a matching voter_device_id indicates signed in status on the specific device
    #
    try:
        # I may need to delete any row prior to this change 8/14/20
        # Force kill any legacy duplicates, from now on only one row per user code
        # to test this you will have to navigate to https://appleid.apple.com/account/manage
        # and remove the wevote cordova app from the list
        # usr = AppleUser.objects.filter(user_code=user_code)[:1].values_list("id", flat=True)  # only retrieve ids.
        # AppleUser.objects.exclude(pk__in=list(usr)).delete()

        # Get the last row that matches user_code
        apple_user = AppleUser.objects.filter(user_code=user_code).last()
        if apple_user:
            status += "APPLE_USER_ID_RECORD_UPDATED "
            previously_signed_in_voter_found = True
            previously_signed_in_voter_we_vote_id = apple_user.voter_we_vote_id
            signed_in_voter_we_vote_id = apple_user.voter_we_vote_id
        else:
            # user_code not found: Create new AppleUser entry
            # if not last_name:
            #     apple_user_first = AppleUser.objects.filter(user_code=user_code).first()
            #     first_name = apple_user_first.first_name
            #     middle_name = apple_user_first.middle_name
            #     last_name = apple_user_first.last_name
            apple_user = AppleUser.objects.create(
                email=email,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                apple_platform=apple_platform,
                apple_os_version=apple_os_version,
                apple_model=apple_model,
                voter_we_vote_id=voter_starting_process_we_vote_id,
                user_code=user_code,
            )
            status += "APPLE_USER_ID_RECORD_CREATED "
            previously_signed_in_voter_found = False
            previously_signed_in_voter_we_vote_id = ''
            signed_in_voter_we_vote_id = apple_user.voter_we_vote_id

        # If you Signed in with Apple first on another device, and we didn't catch the email or name the first time
        # through, catch them on subsequent "first sign ins on a device"
        if not positive_value_exists(apple_user.email) and positive_value_exists(email):
            apple_user.email = email
        if not positive_value_exists(apple_user.first_name) and positive_value_exists(first_name):
            apple_user.first_name = first_name
        if not positive_value_exists(apple_user.middle_name) and positive_value_exists(middle_name):
            apple_user.middle_name = middle_name
        if not positive_value_exists(apple_user.last_name) and positive_value_exists(last_name):
            apple_user.last_name = last_name
        apple_user.date_last_referenced = datetime.today()
        # We match to existing voter outside this function
        # if not positive_value_exists(previously_signed_in_voter_we_vote_id):
        #     results_id = apple_sign_in_retrieve_voter_id(email, first_name, last_name)
        #     if positive_value_exists(results_id['voter_we_vote_id']):
        #         previously_signed_in_voter_we_vote_id = results_id['voter_we_vote_id']
        #         apple_user.voter_we_vote_id = previously_signed_in_voter_we_vote_id
        #         status += previously_signed_in_voter_we_vote_id + " " + results_id['status'] + " "
        apple_user.save()
        success_siwa = True
    except Exception as e:
        success_siwa = False
        status += "ERROR_APPLE_USER_NOT_CREATED_OR_UPDATED: " + str(e) + ' '
        if DEBUG_LOGGING:
            logger.error("awsApple: ", status)
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                                  success_siwa,
        'status':                                   status,
        'previously_signed_in_voter_found':         previously_signed_in_voter_found,
        'previously_signed_in_voter_we_vote_id':    previously_signed_in_voter_we_vote_id,
        'signed_in_voter_we_vote_id':               signed_in_voter_we_vote_id,
    }
    return results


@csrf_exempt
def sign_in_with_apple_oauth_redirect_view(request):  # appleSignInOauthRedirectDestination
    # This is part of the OAuth flow for the WebApp (This is NOT part of the flow for iOS!)
    status = ''
    status += "STARTING-appleSignInOauthRedirectDestination "
    access_token = ''
    critical_variable_missing = False
    first_name = ''
    middle_name = ''
    last_name = ''
    email = ''
    return_url = ''
    user_code = ''
    voter_device_id = ''

    print("Method is", request.method)
    if not request.method == 'POST':
        logger.error('awsApple appleSignInOauthRedirectDestination WRONG Method: ' + request.method)

    try:
        access_token = request.POST['id_token']
    except Exception as e:
        status += "ID_TOKEN_MISSING: " + str(e) + ' '
        critical_variable_missing = True
    try:
        state_dict = json.loads(request.POST['state'])
        if DEBUG_LOGGING:
            logger.error('awsApple post params on redirect:' + json.dumps(state_dict))

        voter_device_id = state_dict['voter_device_id']
        return_url = state_dict['return_url']
    except Exception as e:
        status += "STATE_DICT_MISSING: " + str(e) + ' '
        critical_variable_missing = True
    # print('id_token renamed as access_token: ', access_token)

    if critical_variable_missing:
        logger.error('awsApple ' + status)
        return HttpResponseRedirect('https://WeVote.US/applesigninprocess')

    if 'user' in request.POST:
        # Apple only sends this user name in the clear on the very first time the voter signs in with Apple on a device
        # <QueryDict: {
        #   'state': [
        #     '{"voter_device_id":"WHEQYCQ...hWFUs6RJ1k",
        #     "return_url":"https://localhost:3000/ready"}'
        #   ],
        #   'code': ['cfd1436ca8c8d463d94e55f4a2bdbfbf8.0.nruqx.bg8M64KEkoUOBwmddufJLA'],
        #   'id_token': ['eyJraW...JO4aJMpGGtN2q8L1kJG7AQV1sgRg'],
        #   'user': [
        #     '{"name":
        #       {"firstName":"Steve",
        #        "lastName":"Podell"},
        #        "email":"stevepodell11@yahoo.com"}'
        #   ]}>
        # On subsequent calls it looks like
        # <QueryDict: {
        #   'state': [
        #     '{"voter_device_id": "eHUgOyy...8ho2uvPZWmGY4mNWNn6U9VKVhthrh7MHiurhNwwDoirgSR",
        #     "return_url":"https://localhost:3000/ready"}'
        #   ],
        #   'code': ['cfd1436ca8c8d463d94e55f4a2bdbfbf8.0.nruqx.bg8M64KEkoUOBwmddufJLA'],
        #   'id_token': ['eyJraW...JO4aJMpGGtN2q8L1kJG7AQV1sgRg'],
        # But the voter's email that is registered with SIWA is received encrypted in the id_token on subsequent logins
        # To re-test the initial login message, goto https://appleid.apple.com/account/manage and under
        #   Security/"APPS & WEBSITES USING APPLE ID" click "Manage..." and "Stop Using Apple ID" for
        #      "We Vote Ballot Guide, @WeVote"

        user_string = request.POST['user']
        user = json.loads(user_string)

        if 'firstName' in user['name']:
            first_name = user['name']['firstName']
        if 'middleName' in user['name']:
            middle_name = user['name']['middleName']
        if 'lastName' in user['name']:
            last_name = user['name']['lastName']
        if 'email' in user:
            email = user['email']

    client_id = get_environment_variable_default('SOCIAL_AUTH_APPLE_CLIENT_ID_WEB', 'us.wevote.webapp')
    results = AppleResolver().authenticate(access_token, client_id)
    if results:
        user_code = results['subject_registered_claim']
        email = results['email']
        if DEBUG_LOGGING:
            logger.error("awsApple Not an error: Sign in with Apple WebApp, decrypted jwt", results)

    # voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()

    results = voter_device_link_manager.retrieve_voter_device_link(
        voter_device_id, read_only=False)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
    else:
        voter_device_link = None

    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=False)
    if results['voter_found']:
        # This is the voter account the person is using when they click "Sign in with Apple"
        voter_starting_process = results['voter']
        voter_starting_process_we_vote_id = voter_starting_process.we_vote_id
    else:
        voter_starting_process = None
        voter_starting_process_we_vote_id = ''

    if not positive_value_exists(voter_starting_process_we_vote_id):
        logger.error(
            'awsApple didnt receive a voter_we_vote_id from voter_device_id in sign_in_with_apple_oauth_redirect_view')

    results = sign_in_with_apple_for_api(
        user_code=user_code,
        email=email,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        apple_platform='Web WeVoteWebApp',
        apple_os_version='n/a',
        apple_model='n/a',
        voter_starting_process_we_vote_id=voter_starting_process_we_vote_id)
    previously_signed_in_voter_we_vote_id = results['previously_signed_in_voter_we_vote_id']
    status += results['status']

    merge_results = apple_sign_in_save_merge_if_needed(
        email_from_apple=email,
        previously_signed_in_apple_voter_found=results['previously_signed_in_voter_found'],
        previously_signed_in_apple_voter_we_vote_id=previously_signed_in_voter_we_vote_id,
        voter_device_link=voter_device_link,
        voter_starting_process=voter_starting_process,
    )

    merge_from_voter_we_vote_id = voter_starting_process_we_vote_id
    merge_to_voter_we_vote_id = previously_signed_in_voter_we_vote_id
    status += "VOTER_STARTING_PROCESS_WE_VOTE_ID-" + str(voter_starting_process_we_vote_id) + " "
    status += "PREVIOUSLY_SIGNED_IN_WE_VOTE_ID-" + str(previously_signed_in_voter_we_vote_id) + " "
    if positive_value_exists(merge_from_voter_we_vote_id) and positive_value_exists(merge_to_voter_we_vote_id):
        voter_results = voter_manager.retrieve_voter_by_we_vote_id(merge_to_voter_we_vote_id)
        if voter_results['success'] and voter_results['voter_found']:
            to_voter = voter_results['voter']
            merge_results = voter_merge_two_accounts_action_schedule(
                from_voter=voter_starting_process,
                to_voter=to_voter,
                voter_device_link=voter_device_link)
            status += merge_results['status']

    status += merge_results['status']
    if DEBUG_LOGGING:
        logger.error('awsApple ' + status)

    return HttpResponseRedirect(return_url)


def validate_sign_in_with_apple_token(request):  # appleValidateSignInWithAppleToken
    """
    Handle and store the data from a "Sign In With Apple" login via the WebApp
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    apple_oauth_code = request.GET.get('code', '')

    results = validate_sign_in_with_apple_token_for_api(
        apple_oauth_code=apple_oauth_code,
    )

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'voter_we_vote_id': results['voter_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
