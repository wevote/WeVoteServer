# apis_v1/views/views_friend.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
from friend.controllers import friend_invitation_by_email_send_for_api, friend_invitation_by_email_verify_for_api, \
    friend_invitation_by_we_vote_id_send_for_api, friend_invite_response_for_api, friend_list_for_api, \
    friend_invitation_by_facebook_send_for_api, friend_invitation_by_facebook_verify_for_api
from friend.models import CURRENT_FRIENDS, DELETE_INVITATION_EMAIL_SENT_BY_ME, DELETE_INVITATION_VOTER_SENT_BY_ME, \
    FRIEND_INVITATIONS_PROCESSED, FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_SENT_BY_ME, \
    FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION, SUGGESTED_FRIEND_LIST, \
    FRIENDS_IN_COMMON, IGNORED_FRIEND_INVITATIONS, ACCEPT_INVITATION, IGNORE_INVITATION, \
    UNFRIEND_CURRENT_FRIEND
import json
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id


logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def friend_invitation_by_email_send_view(request):  # friendInvitationByEmailSend
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    email_address_array = request.GET.getlist('email_address_array[]', "")
    first_name_array = request.GET.getlist('first_name_array[]', "")
    last_name_array = request.GET.getlist('last_name_array[]', "")
    email_addresses_raw = request.GET.get('email_addresses_raw', "")
    invitation_message = request.GET.get('invitation_message', "")
    sender_email_address = request.GET.get('sender_email_address', "")
    results = friend_invitation_by_email_send_for_api(voter_device_id, email_address_array, first_name_array,
                                                      last_name_array, email_addresses_raw,
                                                      invitation_message, sender_email_address)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
        'error_message_to_show_voter':          results['error_message_to_show_voter'],
        'sender_voter_email_address_missing':   results['sender_voter_email_address_missing'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invitation_by_email_verify_view(request):  # friendInvitationByEmailVerify
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    invitation_secret_key = request.GET.get('invitation_secret_key', "")
    results = friend_invitation_by_email_verify_for_api(voter_device_id, invitation_secret_key)
    json_data = {
        'status':                       results['status'],
        'success':                      results['success'],
        'voter_device_id':              voter_device_id,
        'voter_has_data_to_preserve':   results['voter_has_data_to_preserve'],
        'invitation_found':             results['invitation_found'],
        'attempted_to_approve_own_invitation':          results['attempted_to_approve_own_invitation'],
        'invitation_secret_key':                        invitation_secret_key,
        'invitation_secret_key_belongs_to_this_voter':  results['invitation_secret_key_belongs_to_this_voter'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invitation_by_facebook_send_view(request):  # friendInvitationByFacebookSend
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    recipients_facebook_id_array = request.GET.getlist('recipients_facebook_id_array[]', "")
    recipients_facebook_name_array = request.GET.getlist('recipients_facebook_name_array[]', "")
    facebook_request_id = request.GET.get('facebook_request_id', "")
    results = friend_invitation_by_facebook_send_for_api(voter_device_id, recipients_facebook_id_array,
                                                         recipients_facebook_name_array, facebook_request_id)
    json_data = {
        'status':                                       results['status'],
        'success':                                      results['success'],
        'voter_device_id':                              voter_device_id,
        'all_friends_facebook_link_created_results':    results['all_friends_facebook_link_created_results'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invitation_by_facebook_verify_view(request):  # friendInvitationByFacebookVerify
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    facebook_request_id = request.GET.get('facebook_request_id', "")
    recipient_facebook_id = request.GET.get('recipient_facebook_id', "")
    sender_facebook_id = request.GET.get('sender_facebook_id', "")
    results = friend_invitation_by_facebook_verify_for_api(voter_device_id, facebook_request_id,
                                                           recipient_facebook_id, sender_facebook_id)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
        'voter_has_data_to_preserve':           results['voter_has_data_to_preserve'],
        'invitation_found':                     results['invitation_found'],
        'attempted_to_approve_own_invitation':  results['attempted_to_approve_own_invitation'],
        'facebook_request_id':                  facebook_request_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invitation_by_we_vote_id_send_view(request):  # friendInvitationByWeVoteIdSend
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    invitation_message = request.GET.get('invitation_message', "")
    other_voter_we_vote_id = request.GET.get('other_voter_we_vote_id', "")
    results = friend_invitation_by_we_vote_id_send_for_api(voter_device_id, other_voter_we_vote_id, invitation_message)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invite_response_view(request):  # friendInviteResponse
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_invite_response = request.GET.get('kind_of_invite_response', ACCEPT_INVITATION)
    if not kind_of_invite_response in(ACCEPT_INVITATION, DELETE_INVITATION_EMAIL_SENT_BY_ME,
                                      DELETE_INVITATION_VOTER_SENT_BY_ME, IGNORE_INVITATION, UNFRIEND_CURRENT_FRIEND):
        kind_of_invite_response = ACCEPT_INVITATION
    other_voter_we_vote_id = request.GET.get('voter_we_vote_id', "")
    recipient_voter_email = request.GET.get('recipient_voter_email', "")
    results = friend_invite_response_for_api(voter_device_id=voter_device_id,
                                             kind_of_invite_response=kind_of_invite_response,
                                             other_voter_we_vote_id=other_voter_we_vote_id,
                                             recipient_voter_email=recipient_voter_email)

    json_data = {
        'status':                   results['status'],
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'voter_we_vote_id':         other_voter_we_vote_id,
        'kind_of_invite_response':  kind_of_invite_response,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_list_view(request):  # friendList
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_list = request.GET.get('kind_of_list', CURRENT_FRIENDS)
    if kind_of_list in(CURRENT_FRIENDS, FRIEND_INVITATIONS_PROCESSED,
                       FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_SENT_BY_ME,
                       FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION, FRIENDS_IN_COMMON,
                       IGNORED_FRIEND_INVITATIONS, SUGGESTED_FRIEND_LIST):
        kind_of_list_we_are_looking_for = kind_of_list
    else:
        kind_of_list_we_are_looking_for = CURRENT_FRIENDS
    state_code = request.GET.get('state_code', "")
    results = friend_list_for_api(voter_device_id=voter_device_id,
                                  kind_of_list_we_are_looking_for=kind_of_list_we_are_looking_for,
                                  state_code=state_code)

    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      voter_device_id,
        'state_code':           state_code,
        'kind_of_list':         kind_of_list_we_are_looking_for,
        'friend_list_found':    results['friend_list_found'],
        'friend_list':          results['friend_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
