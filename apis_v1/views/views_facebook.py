# apis_v1/views/views_facebook.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
from import_export_facebook.controllers import facebook_disconnect_for_api, \
    voter_facebook_save_to_current_account_for_api, facebook_friends_action_for_api
import json
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def facebook_friends_action_view(request):  # facebookFriendsActions
    """
    This is used to retrieve facebook friends who are using WeVote app by facebook 'friends' API.
    However we use the Facebook "games" api "invitable_friends" data on the fly from the webapp, to invite facebook
    friends who are not using we vote.
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = facebook_friends_action_for_api(voter_device_id)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
        'facebook_friend_suggestion_found':     results['facebook_friend_suggestion_found'],
        'facebook_suggested_friend_count':      results['facebook_suggested_friend_count'],
        'facebook_friends_using_we_vote_list':  results['facebook_friends_using_we_vote_list'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def facebook_disconnect_view(request):
    """
    Disconnect this We Vote account from current Facebook account
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = facebook_disconnect_for_api(voter_device_id)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_facebook_save_to_current_account_view(request):  # voterFacebookSaveToCurrentAccount
    """
    Saving the results of signing in with Facebook
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = voter_facebook_save_to_current_account_for_api(voter_device_id)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
