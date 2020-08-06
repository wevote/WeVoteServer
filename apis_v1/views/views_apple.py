# apis_v1/views/views_apple.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import date, datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
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

# https://medium.com/@aamishbaloch/sign-in-with-apple-in-your-django-python-backend-b501daa835a9
# https://github.com/pastre/backend-challenge-python/blob/f387a94cafbec8c404d2d9e0eb05a9cc0eefd208/reflections/views.py
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
    voter_device_id = request.POST['state']
    print('id_token renamed as access_token: ', access_token)

    first_name = ''
    middle_name = ''
    last_name = ''
    email = ''
    user_code = ''
    if 'user' in request.POST:
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

    sign_in_with_apple_for_api(voter_device_id, user_code, email, first_name,
                               middle_name, last_name, 'Web WeVoteWebApp', 'n/a',
                               'n/a', voter_we_vote_id)

    return HttpResponseRedirect('https://localhost:3000/ballot')

# <QueryDict: {'state': ['steve'], 'code': ['cae6bae43fae8490d8c69b99950db4e7c.0.nruqx.ovW0z46HMKpdzB69RNqwRA'], 'id_token': ['eyJraWQiOiJlWGF1bm1MIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwiYXVkIjoidXMud2V2b3RlLndlYmFwcCIsImV4cCI6MTU5NjY0NDQ3NCwiaWF0IjoxNTk2NjQzODc0LCJzdWIiOiIwMDE0MDcuODcxMGMxZmMwYmY4NDMyOGJjYzg1YWMxY2EyNWU5YWEuMDQxNiIsImNfaGFzaCI6ImxjMXhjZ2NyY1RvRGp4YWFrYjZvYWciLCJlbWFpbCI6InN0ZXZlcG9kZWxsQHlhaG9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjoidHJ1ZSIsImF1dGhfdGltZSI6MTU5NjY0Mzg3NCwibm9uY2Vfc3VwcG9ydGVkIjp0cnVlfQ.EQK13mKJHq0J6qpertr8VQ95ORI-j8klxUH0aaBEpKWEJ2IMksaQgCqDQOsP1Bi0nJ-IFPZivgPju8axlRtXf0XCWF4h4HYqMy7xciSq6eNUK9Yej6Xb6BZFd5ITt76tfiFnzVfYMdL8mZSSlV9reED_rxODyWcbBcRzwHYFtfjY1AqEhC-ePKfeVorRAN8FMV1X_XYy1cVNshFulX3iofaVxvOpeS6CPuWA9K9DsJ2xBvcFMPXg15Tl2C8mFOraj6pQ862YlB41jkSF1sjQEAqRp4sshPIa96AjghG1P9S_vgWJHn4SMNjrujasVxWN7JSdDLuxrXN-6CCQ22Iqeg']}>



# First TimeoutError[2020-08-04 15:57:48,909] [ERROR] Steves-MacBook-Pro-32GB-Oct-2109.local:apis_v1.views.views_apple: appleSignInOauthRedirectDestination dump GET: {}
# [2020-08-04 15:57:48,911] [ERROR] Steves-MacBook-Pro-32GB-Oct-2109.local:apis_v1.views.views_apple: appleSignInOauthRedirectDestination dump POST: {"state": "steve", "code": "c67a2ea5e60ff4b03bcfb3ccb6fef8bd9.0.nruqx.hFm55XIyU6at0kc5aj6xSg", "id_token": "eyJraWQiOiI4NkQ4OEtmIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwiYXVkIjoidXMud2V2b3RlLndlYmFwcCIsImV4cCI6MTU5NjU4MjQ2OCwiaWF0IjoxNTk2NTgxODY4LCJzdWIiOiIwMDE0MDcuODcxMGMxZmMwYmY4NDMyOGJjYzg1YWMxY2EyNWU5YWEuMDQxNiIsImNfaGFzaCI6IjVsOEU2aEQteUN2N0M2MmpSWWMzSmciLCJlbWFpbCI6InN0ZXZlcG9kZWxsQHlhaG9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjoidHJ1ZSIsImF1dGhfdGltZSI6MTU5NjU4MTg2OCwibm9uY2Vfc3VwcG9ydGVkIjp0cnVlfQ.Qvw3A1EloqQcM7f-4qa9D1zfiO5ospymHz9RPFJvP0mD3dEyJLUu5rJfOnJfcY52Pvzb-K9wYwkVd3kv_R7w1vY1MHDbEsX3gBhoCXcsIvfxEx8RVVnoo2cIsGrWy7JB_FBuJkSQMW3QuPqxmYzr4IOiULGj3tFV4vHmzbpPMOTz8VQkEGYOnpqtrj8sgsk47AMZypbU-cMgmlMnG5VjjT4LsZVFVIXF80gydX8tqXmAd7npJivgFs2xF8973UeT7M5t8jKQQf9yVWi_aTOFxMSd2e1n7lYnWPsUDdVPWgIu8DD714WBUze18sx3FkgvpBoKNtc9d84nDfh3qaKyZw", "user": "{\"name\":{\"firstName\":\"Steve\",\"lastName\":\"Podell\"},\"email\":\"stevepodell@yahoo.com\"}"}
# [2020-08-04 15:57:48,911] [ERROR] Steves-MacBook-Pro-32GB-Oct-2109.local:apis_v1.views.views_apple: appleSignInOauthRedirectDestination dump body: state=steve&code=c67a2ea5e60ff4b03bcfb3ccb6fef8bd9.0.nruqx.hFm55XIyU6at0kc5aj6xSg&id_token=eyJraWQiOiI4NkQ4OEtmIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwiYXVkIjoidXMud2V2b3RlLndlYmFwcCIsImV4cCI6MTU5NjU4MjQ2OCwiaWF0IjoxNTk2NTgxODY4LCJzdWIiOiIwMDE0MDcuODcxMGMxZmMwYmY4NDMyOGJjYzg1YWMxY2EyNWU5YWEuMDQxNiIsImNfaGFzaCI6IjVsOEU2aEQteUN2N0M2MmpSWWMzSmciLCJlbWFpbCI6InN0ZXZlcG9kZWxsQHlhaG9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjoidHJ1ZSIsImF1dGhfdGltZSI6MTU5NjU4MTg2OCwibm9uY2Vfc3VwcG9ydGVkIjp0cnVlfQ.Qvw3A1EloqQcM7f-4qa9D1zfiO5ospymHz9RPFJvP0mD3dEyJLUu5rJfOnJfcY52Pvzb-K9wYwkVd3kv_R7w1vY1MHDbEsX3gBhoCXcsIvfxEx8RVVnoo2cIsGrWy7JB_FBuJkSQMW3QuPqxmYzr4IOiULGj3tFV4vHmzbpPMOTz8VQkEGYOnpqtrj8sgsk47AMZypbU-cMgmlMnG5VjjT4LsZVFVIXF80gydX8tqXmAd7npJivgFs2xF8973UeT7M5t8jKQQf9yVWi_aTOFxMSd2e1n7lYnWPsUDdVPWgIu8DD714WBUze18sx3FkgvpBoKNtc9d84nDfh3qaKyZw&user=%7B%22name%22%3A%7B%22firstName%22%3A%22Steve%22%2C%22lastName%22%3A%22Podell%22%7D%2C%22email%22%3A%22stevepodell%40yahoo.com%22%7D
# '{"name":{"firstName":"Steve","lastName":"Podell"},"email":"stevepodell@yahoo.com"}'
# request.POST['user'] = '{"name":{"firstName":"Steve","lastName":"Podell"},"email":"stevepodell@yahoo.com"}'

# <QueryDict: {'state': ['steve'], 'code': ['c4510d342610f400ab4cb78158da3251a.0.nruqx.dDDRUMMrcteqW-pY_XhEYA'], 'id_token': ['eyJraWQiOiI4NkQ4OEtmIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwiYXVkIjoidXMud2V2b3RlLndlYmFwcCIsImV4cCI6MTU5NjU4Mjk4MiwiaWF0IjoxNTk2NTgyMzgyLCJzdWIiOiIwMDE0MDcuODcxMGMxZmMwYmY4NDMyOGJjYzg1YWMxY2EyNWU5YWEuMDQxNiIsImNfaGFzaCI6Im81c3BLRWdYN0ZNQUM3MEdXTVJDSEEiLCJlbWFpbCI6InN0ZXZlcG9kZWxsQHlhaG9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjoidHJ1ZSIsImF1dGhfdGltZSI6MTU5NjU4MjM4Miwibm9uY2Vfc3VwcG9ydGVkIjp0cnVlfQ.Y1JWnv71iwF3QvH0YpxGfH5igEkc01cTHZ8MaeBqHv1dQ66PRkS2ykkCX_oiIqtfCyqPB3UVR3oDiGo_K2czV_fdvnydJKiJPQeRExc5iiBjmHmZ4s_IZl_fDghHq0HQRRtWuxQ1JvV9CD1bf990J7uwBPm0Atmjbp2fQbaetF6MFChPa_EhXeptIEU0QQw3rtyXgltIRzz0bZOmL2MTPvzuOjPo89z0cVFMV4Y7HNNyPKbbdJeZ8LgwsO_4EQ9rOhJog2wQ-HBhV1raCBmoltflh7GamuNayBkBdbbr1Vt8EVMOx3tnhPxx1_uoLM3w-n-SMFDn0Qp4owbEL7-dOw']}>
# eyJraWQiOiI4NkQ4OEtmIiwiYWxnIjoiUlMyNTYifQ.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwiYXVkIjoidXMud2V2b3RlLndlYmFwcCIsImV4cCI6MTU5NjU4Mjk4MiwiaWF0IjoxNTk2NTgyMzgyLCJzdWIiOiIwMDE0MDcuODcxMGMxZmMwYmY4NDMyOGJjYzg1YWMxY2EyNWU5YWEuMDQxNiIsImNfaGFzaCI6Im81c3BLRWdYN0ZNQUM3MEdXTVJDSEEiLCJlbWFpbCI6InN0ZXZlcG9kZWxsQHlhaG9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjoidHJ1ZSIsImF1dGhfdGltZSI6MTU5NjU4MjM4Miwibm9uY2Vfc3VwcG9ydGVkIjp0cnVlfQ.Y1JWnv71iwF3QvH0YpxGfH5igEkc01cTHZ8MaeBqHv1dQ66PRkS2ykkCX_oiIqtfCyqPB3UVR3oDiGo_K2czV_fdvnydJKiJPQeRExc5iiBjmHmZ4s_IZl_fDghHq0HQRRtWuxQ1JvV9CD1bf990J7uwBPm0Atmjbp2fQbaetF6MFChPa_EhXeptIEU0QQw3rtyXgltIRzz0bZOmL2MTPvzuOjPo89z0cVFMV4Y7HNNyPKbbdJeZ8LgwsO_4EQ9rOhJog2wQ-HBhV1raCBmoltflh7GamuNayBkBdbbr1Vt8EVMOx3tnhPxx1_uoLM3w-n-SMFDn0Qp4owbEL7-dOw
# verified_payload {'iss': 'https://appleid.apple.com', 'aud': 'us.wevote.webapp', 'exp': 1596643481, 'iat': 1596642881, 'sub': '001407.8710c1fc0bf84328bcc85ac1ca25e9aa.0416', 'c_hash': 'd2v3DNRwymB3aFaPgS8lXA', 'email': 'stevepodell@yahoo.com', 'email_verified': 'true', 'auth_time': 1596642881, 'nonce_supported': True}
# verified_payload {
#   'iss': 'https://appleid.apple.com',
#   'aud': 'us.wevote.webapp',
#   'exp': 1596643481,
#   'iat': 1596642881,
#   'sub': '001407.8710c1fc0bf84328bcc85ac1ca25e9aa.0416',
#   'c_hash': 'd2v3DNRwymB3aFaPgS8lXA',
#   'email': 'stevepodell@yahoo.com',
#   'email_verified': 'true',
#   'auth_time': 1596642881,
#   'nonce_supported': True}


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
