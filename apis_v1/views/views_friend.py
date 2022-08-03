# apis_v1/views/views_friend.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
from friend.controllers import friend_acceptance_email_should_be_sent, \
    friend_invitation_by_email_send_for_api, friend_invitation_by_email_verify_for_api, \
    friend_invitation_by_we_vote_id_send_for_api, friend_invite_response_for_api, friend_list_for_api, \
    friend_lists_all_for_api, friend_invitation_by_facebook_send_for_api, \
    friend_invitation_by_facebook_verify_for_api, friend_invitation_information_for_api, message_to_friend_send_for_api
from friend.models import ACCEPT_INVITATION, CURRENT_FRIENDS, DELETE_INVITATION_EMAIL_SENT_BY_ME, \
    DELETE_INVITATION_VOTER_SENT_BY_ME, \
    FRIENDS_IN_COMMON, FRIEND_INVITATIONS_PROCESSED, FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_SENT_BY_ME, \
    FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION, \
    IGNORED_FRIEND_INVITATIONS, IGNORE_INVITATION, IGNORE_SUGGESTION, \
    SUGGESTED_FRIEND_LIST, UNFRIEND_CURRENT_FRIEND
import json
from wevote_functions.functions import get_voter_device_id, positive_value_exists, wevote_functions


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
    hostname = request.GET.get('hostname', "")
    results = friend_invitation_by_email_send_for_api(
        voter_device_id=voter_device_id,
        email_address_array=email_address_array,
        first_name_array=first_name_array,
        last_name_array=last_name_array,
        email_addresses_raw=email_addresses_raw,
        invitation_message=invitation_message,
        sender_email_address=sender_email_address,
        web_app_root_url=hostname)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
        'error_message_to_show_voter':          results['error_message_to_show_voter'],
        'success_message_to_show_voter':        results['success_message_to_show_voter'],
        'number_of_messages_sent':              results['number_of_messages_sent'],
        'sender_voter_email_address_missing':   results['sender_voter_email_address_missing'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invitation_by_email_verify_view(request):  # friendInvitationByEmailVerify
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    acceptance_email_should_be_sent = positive_value_exists(request.GET.get('acceptance_email_should_be_sent', False))
    invitation_secret_key = request.GET.get('invitation_secret_key', "")
    hostname = request.GET.get('hostname', "")
    if acceptance_email_should_be_sent:
        results = friend_acceptance_email_should_be_sent(
            voter_device_id,
            invitation_secret_key,
            web_app_root_url=hostname)
        json_data = {
            'status':                               results['status'],
            'success':                              results['success'],
            'acceptance_email_should_be_sent':      results['acceptance_email_should_be_sent'],
            'attempted_to_approve_own_invitation':  results['attempted_to_approve_own_invitation'],
            'invitation_found':                     results['invitation_found'],
            'invitation_secret_key':                invitation_secret_key,
            'voter_device_id':                      voter_device_id,
            'voter_has_data_to_preserve':           results['voter_has_data_to_preserve'],
        }
    else:
        results = friend_invitation_by_email_verify_for_api(
            voter_device_id,
            invitation_secret_key)
        json_data = {
            'status':                               results['status'],
            'success':                              results['success'],
            'acceptance_email_should_be_sent':      results['acceptance_email_should_be_sent'],
            'attempted_to_approve_own_invitation':  results['attempted_to_approve_own_invitation'],
            'invitation_found':                     results['invitation_found'],
            'invitation_secret_key':                invitation_secret_key,
            'voter_device_id':                      voter_device_id,
            'voter_has_data_to_preserve':           results['voter_has_data_to_preserve'],
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
    hostname = request.GET.get('hostname', "")
    results = friend_invitation_by_we_vote_id_send_for_api(
        voter_device_id=voter_device_id,
        other_voter_we_vote_id=other_voter_we_vote_id,
        invitation_message=invitation_message,
        web_app_root_url=hostname)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invitation_information_view(request):  # friendInvitationInformation
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    invitation_secret_key = request.GET.get('invitation_secret_key', "")
    results = friend_invitation_information_for_api(voter_device_id, invitation_secret_key)
    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'friend_first_name':                results['friend_first_name'],
        'friend_last_name':                 results['friend_last_name'],
        'friend_image_url_https_large':     results['friend_image_url_https_large'],
        'friend_image_url_https_tiny':      results['friend_image_url_https_tiny'],
        'friend_issue_we_vote_id_list':     results['friend_issue_we_vote_id_list'],
        'friend_we_vote_id':                results['friend_we_vote_id'],
        'friend_organization_we_vote_id':   results['friend_organization_we_vote_id'],
        'invitation_found':                 results['invitation_found'],
        'invitation_message':               results['invitation_message'],
        'invitation_secret_key':            invitation_secret_key,
        'invitation_secret_key_belongs_to_this_voter':  results['invitation_secret_key_belongs_to_this_voter'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def friend_invite_response_view(request):  # friendInviteResponse
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_invite_response = request.GET.get('kind_of_invite_response', ACCEPT_INVITATION)
    if kind_of_invite_response not in (ACCEPT_INVITATION, DELETE_INVITATION_EMAIL_SENT_BY_ME,
                                       DELETE_INVITATION_VOTER_SENT_BY_ME, IGNORE_INVITATION, IGNORE_SUGGESTION,
                                       UNFRIEND_CURRENT_FRIEND):
        kind_of_invite_response = ACCEPT_INVITATION
    other_voter_we_vote_id = request.GET.get('voter_we_vote_id', "")
    recipient_voter_email = request.GET.get('recipient_voter_email', "")
    hostname = request.GET.get('hostname', "")
    results = friend_invite_response_for_api(voter_device_id=voter_device_id,
                                             kind_of_invite_response=kind_of_invite_response,
                                             other_voter_we_vote_id=other_voter_we_vote_id,
                                             recipient_voter_email=recipient_voter_email,
                                             web_app_root_url=hostname)

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
    if kind_of_list in (CURRENT_FRIENDS, FRIEND_INVITATIONS_PROCESSED,
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


def friend_lists_all_view(request):  # friendList
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    state_code = request.GET.get('state_code', "")
    results = friend_lists_all_for_api(voter_device_id=voter_device_id, state_code=state_code)

    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
        'state_code':                           state_code,
        'current_friends':                      results['current_friends'],
        'invitations_processed':                results['invitations_processed'],
        'invitations_sent_to_me':               results['invitations_sent_to_me'],
        'invitations_sent_by_me':               results['invitations_sent_by_me'],
        'invitations_waiting_for_verify':       results['invitations_waiting_for_verify'],
        'suggested_friends':                    results['suggested_friends'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def message_to_friend_send_view(request):  # messageToFriendSend
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    election_date_in_future_formatted = request.GET.get('election_date_in_future_formatted', "")
    election_date_is_today = positive_value_exists(request.GET.get('election_date_is_today', False))
    message_to_friend = request.GET.get('message_to_friend', "")
    other_voter_we_vote_id = request.GET.get('other_voter_we_vote_id', "")
    hostname = request.GET.get('hostname', "")
    results = message_to_friend_send_for_api(
        election_date_in_future_formatted=election_date_in_future_formatted,
        election_date_is_today=election_date_is_today,
        other_voter_we_vote_id=other_voter_we_vote_id,
        message_to_friend=message_to_friend,
        voter_device_id=voter_device_id,
        web_app_root_url=hostname)
    json_data = {
        'status':                               results['status'],
        'success':                              results['success'],
        'voter_device_id':                      voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
