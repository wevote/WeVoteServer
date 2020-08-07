# apis_v1/views/views_apple.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import date, datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from exception.models import print_to_log, handle_exception
import json
from apple.AppleResolver import AppleResolver
from apple.controllers import apple_sign_in_retrieve_voter_id, validate_sign_in_with_apple_token_for_api
from apple.models import AppleUser
from config.base import get_environment_variable
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
    email = request.GET.get('email', '')
    first_name = request.GET.get('first_name', '')
    middle_name = request.GET.get('middle_name', '')
    last_name = request.GET.get('last_name', '')
    apple_platform = request.GET.get('apple_platform', '')
    apple_os_version = request.GET.get('apple_os_version', '')
    apple_model = request.GET.get('apple_model', '')
    voter_we_vote_id = request.GET.get('voter_we_vote_id', '')

    results = sign_in_with_apple_for_api(
        voter_device_id=voter_device_id,
        user_code=user_code,
        email=email,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        apple_platform=apple_platform,
        apple_os_version=apple_os_version,
        apple_model=apple_model,
        voter_we_vote_id=voter_we_vote_id,
    )

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'voter_we_vote_id': results['voter_we_vote_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def payload(message, status):
    return HttpResponse(
        json.dumps({"status": status, "payload": message} if not message == None else {"status": status})
    )


def success(message=None): return payload(message, "success")


def sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name,
                               middle_name, last_name, apple_platform, apple_os_version,
                               apple_model, voter_we_vote_id):
    status = ""
    success_siwa = False
    if not positive_value_exists(user_code) or not positive_value_exists(email):
        status += "CREATE_APPLE_LINK_MISSING_REQUIRED_VARIABLE_USER_CODE_OR_EMAIL "
        print_to_log(logger=logger, exception_message_optional=status)
        results = {
            'success': success_siwa,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
        }
        return results

    apple_object = AppleUser.objects.get_or_create(
        user_code__iexact=user_code,
        voter_device_id=voter_device_id,
        defaults={
            'user_code': user_code,
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
    try:
        apple_user = apple_object[0]  # there can only be one unique match for voter_device_id AND apple user_code
        apple_user.date_last_referenced = datetime.today()
        if not positive_value_exists(voter_we_vote_id):
            results_id = apple_sign_in_retrieve_voter_id(voter_device_id, email, first_name, last_name)
            if positive_value_exists(results_id['voter_we_vote_id']):
                voter_we_vote_id = results_id['voter_we_vote_id']
                apple_user.voter_we_vote_id = voter_we_vote_id
                status += results_id['status']
        apple_user.save()
        success_siwa = True
        status += "APPLE_USER_ID_RECORD_CREATED_OR_UPDATED "
    except Exception as e:
        success_siwa = False
        status += "ERROR_APPLE_USER_NOT_CREATED_OR_NOT_UPDATED "
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success_siwa,
        'status': status,
        'voter_we_vote_id': voter_we_vote_id,
    }
    return results

@csrf_exempt
def sign_in_with_apple_oauth_redirect_view(request):  # appleSignInOauthRedirectDestination
    # These are going to the error log so that I can see them on Splunk  (for now)
    logger.error('appleSignInOauthRedirectDestination dump GET: ' + json.dumps(request.GET))
    logger.error('appleSignInOauthRedirectDestination dump POST: ' + json.dumps(request.POST))
    logger.error('appleSignInOauthRedirectDestination dump body: ' + request.body.decode('utf-8'))

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
        # First time
        # <QueryDict: {'state': ['steve'], 'code': ['cae6bae43fae8490d8c69b99950db4e7c.0.nruqx.ovW0z46777pdzB6777qwRA'],
        #              'id_token': ['eyJraW...1P9S_vgWJHn4SMNjrujasVxWN7JSdDLuxrXN-6CCQ22Iqeg']}>
        user = request.POST['user']
        first_name = user['name']['firstName']
        if 'middle_name' in user['name']:
            middle_name = user['name']['middleName']
        last_name = user['name']['lastName']
        email = user['email']

    results = AppleResolver().authenticate(access_token)
    if results:
        user_code = results['subject_registered_claim']
        email = results['email']

    voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_we_vote_id):
        logger.error('did not receive a voter_we_vote_id from voter_device_id in sign_in_with_apple_oauth_redirect_view ')

    sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name,
                               middle_name, last_name, 'Web WeVoteWebApp', 'n/a',
                               'n/a', voter_we_vote_id)

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
