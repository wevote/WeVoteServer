# apis_v1/views/views_apple.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from exception.models import print_to_log, handle_exception
import json
from apple.AppleResolver import AppleResolver
from apple.controllers import apple_sign_in_retrieve_voter_id, validate_sign_in_with_apple_token_for_api
from apple.models import AppleUser
from config.base import get_environment_variable, get_environment_variable_default
from voter.models import fetch_voter_we_vote_id_from_voter_device_link
from wevote_functions.functions import get_voter_device_id, positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def sign_in_with_apple_view(request):  # appleSignInSave appleSignInSaveView
    """
    Handle and store the data from a "Sign In With Apple" login in iOS through Cordova
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    user_code = request.GET.get('user_code', '')
    identity_token = request.GET.get('identity_token', '')
    email = request.GET.get('email', '')
    first_name = request.GET.get('first_name', '')
    middle_name = request.GET.get('middle_name', '')
    last_name = request.GET.get('last_name', '')
    apple_platform = request.GET.get('apple_platform', '')
    apple_os_version = request.GET.get('apple_os_version', '')
    apple_model = request.GET.get('apple_model', '')
    voter_we_vote_id = request.GET.get('voter_we_vote_id', '')

    if not positive_value_exists(email):
        client_id = get_environment_variable_default('SOCIAL_AUTH_APPLE_CLIENT_ID_IOS', 'org.wevote.cordova')
        results = AppleResolver().authenticate(identity_token, client_id)
        if results:
            user_code = results['subject_registered_claim']
            email = results['email']

    results = sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name, middle_name, last_name,
                                         apple_platform, apple_os_version, apple_model, voter_we_vote_id)

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_we_vote_id': results['voter_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def payload(message, status):
    return HttpResponse(
        json.dumps({"status": status, "payload": message} if message is not None else {"status": status})
    )


def success(message=None):
    return payload(message, "success")


def sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name,
                               middle_name, last_name, apple_platform, apple_os_version,
                               apple_model, voter_we_vote_id):
    status = ""
    success_siwa = False
    if not positive_value_exists(user_code):
        status += "CREATE_APPLE_USER_MISSING_REQUIRED_VARIABLE_USER_CODE "
        print_to_log(logger=logger, exception_message_optional=status)
        results = {
            'success': success_siwa,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
        }
        return results


    #
    # The presence of a matching voter_device_id indicates signed in status on the specific device
    #
    try:
        # I may need to delete any row prior to this change 8/14/20
        # # Force kill any legacy duplicates, from now on only one row per user code
        # # to test this you will have to navigate to https://appleid.apple.com/account/manage and remove the wevote cordova app from the list
        # usr = AppleUser.objects.filter(user_code=user_code)[:1].values_list("id", flat=True)  # only retrieve ids.
        # AppleUser.objects.exclude(pk__in=list(usr)).delete()

        # Get the last row that matches user_code and voter_device_id
        apple_user = AppleUser.objects.filter(user_code=user_code, voter_device_id=voter_device_id).last()
        if not apple_user:
            if not last_name:
                apple_user_first = AppleUser.objects.filter(user_code=user_code).first()
                first_name = apple_user_first.first_name
                middle_name = apple_user_first.middle_name
                last_name = apple_user_first.last_name
            apple_user = AppleUser.objects.get_or_create(
                user_code=user_code,
                voter_device_id=voter_device_id,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'middle_name': middle_name,
                    'last_name': last_name,
                    'apple_platform': apple_platform,
                    'apple_os_version': apple_os_version,
                    'apple_model': apple_model,
                    'voter_we_vote_id': voter_we_vote_id,
                }
            )
            apple_user = apple_user[0]
            status += "APPLE_USER_ID_RECORD_CREATED "
        else:
            status += "APPLE_USER_ID_RECORD_UPDATED "

        apple_user.date_last_referenced = datetime.today()
        if not positive_value_exists(voter_we_vote_id):
            results_id = apple_sign_in_retrieve_voter_id(voter_device_id, email, first_name, last_name)
            if positive_value_exists(results_id['voter_we_vote_id']):
                voter_we_vote_id = results_id['voter_we_vote_id']
                apple_user.voter_we_vote_id = voter_we_vote_id
                status += voter_we_vote_id + " " + results_id['status'] + " "
        apple_user.save()
        success_siwa = True
    except Exception as e:
        success_siwa = False
        status += "ERROR_APPLE_USER_NOT_CREATED_OR_UPDATED "
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success_siwa,
        'status': status,
        'voter_we_vote_id': voter_we_vote_id,
    }
    return results


@csrf_exempt
def sign_in_with_apple_oauth_redirect_view(request):  # appleSignInOauthRedirectDestination
    # This is part of the OAuth flow for the WebApp (This is NOT part of the flow for iOS!)

    print("Method is", request.method)
    if not request.method == 'POST':
        logger.error('appleSignInOauthRedirectDestination WRONG Method: ' + request.method)

    access_token = request.POST['id_token']
    state_dict = json.loads(request.POST['state'])
    voter_device_id = state_dict['voter_device_id']
    return_url = state_dict['return_url']
    # print('id_token renamed as access_token: ', access_token)

    first_name = ''
    middle_name = ''
    last_name = ''
    email = ''
    user_code = ''
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

        first_name = user['name']['firstName']
        if 'middle_name' in user['name']:
            middle_name = user['name']['middleName']
        last_name = user['name']['lastName']
        email = user['email']

    client_id = get_environment_variable_default('SOCIAL_AUTH_APPLE_CLIENT_ID_WEB', 'us.wevote.webapp')
    results = AppleResolver().authenticate(access_token, client_id)
    if results:
        user_code = results['subject_registered_claim']
        email = results['email']

    voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_we_vote_id):
        logger.error('did not receive a voter_we_vote_id from voter_device_id in sign_in_with_apple_oauth_redirect_view ')

    sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name, middle_name, last_name,
                               'Web WeVoteWebApp', 'n/a', 'n/a', voter_we_vote_id)

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
        voter_device_id=voter_device_id,
        apple_oauth_code=apple_oauth_code,
    )

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'voter_we_vote_id': results['voter_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
