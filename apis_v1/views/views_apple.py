# apis_v1/views/views_apple.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import date, datetime

from config.base import get_environment_variable
from django.http import HttpResponse
from exception.models import print_to_log, handle_exception
import json
import wevote_functions.admin
from apple.models import AppleUser
from apple.controllers import apple_sign_in_retrieve_voter_id
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def sign_in_with_apple_view(request):  # appleSignInSave
    """
    Step 1 of the Twitter Sign In Process for the WebApp
    Start off the process of signing in with Twitter (twitterSignInStart)
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


def sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name,
                               middle_name, last_name, apple_platform, apple_os_version,
                               apple_model, voter_we_vote_id):
    status = ""
    success = False
    if not positive_value_exists(user_code) or not positive_value_exists(email):
        status += "CREATE_APPLE_LINK_MISSING_REQUIRED_VARIABLE_USER_CODE_OR_EMAIL "
        print_to_log(logger=logger, exception_message_optional=status)
        results = {
            'success': success,
            'status': status,
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
        success = True
        status += "APPLE_USER_ID_RECORD_CREATED_OR_UPDATED "
    except Exception as e:
        success = False
        status += "ERROR_APPLE_USER_NOT_CREATED_OR_NOT_UPDATED "
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'voter_we_vote_id': voter_we_vote_id,
    }
    return results

