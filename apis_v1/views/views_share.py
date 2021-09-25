# apis_v1/views/views_share.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from share.controllers import shared_item_retrieve_for_api, shared_item_save_for_api, super_share_item_save_for_api, \
    super_share_item_send_for_api
from config.base import get_environment_variable
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_user_agents.utils import get_user_agent
import json
import wevote_functions.admin
from wevote_functions.functions import convert_to_bool, get_voter_device_id,  \
    is_speaker_type_organization, is_speaker_type_public_figure, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def shared_item_retrieve_view(request):  # sharedItemRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    destination_full_url = request.GET.get('destination_full_url', '')
    shared_item_code = request.GET.get('shared_item_code', '')
    shared_item_clicked = positive_value_exists(request.GET.get('shared_item_clicked', False))
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    json_data = shared_item_retrieve_for_api(
        voter_device_id=voter_device_id,
        destination_full_url=destination_full_url,
        shared_item_code=shared_item_code,
        shared_item_clicked=shared_item_clicked,
        user_agent_string=user_agent_string,
        user_agent_object=user_agent_object
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def shared_item_save_view(request):  # sharedItemSave
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    destination_full_url = request.GET.get('destination_full_url', '')
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    google_civic_election_id = request.GET.get('google_civic_election_id', None)
    is_ballot_share = positive_value_exists(request.GET.get('is_ballot_share', False))
    is_candidate_share = positive_value_exists(request.GET.get('is_candidate_share', False))
    is_measure_share = positive_value_exists(request.GET.get('is_measure_share', False))
    is_office_share = positive_value_exists(request.GET.get('is_office_share', False))
    is_organization_share = positive_value_exists(request.GET.get('is_organization_share', False))
    is_ready_share = positive_value_exists(request.GET.get('is_ready_share', False))
    organization_we_vote_id = request.GET.get('organization_we_vote_id', None)
    json_data = shared_item_save_for_api(
        voter_device_id=voter_device_id,
        destination_full_url=destination_full_url,
        ballot_item_we_vote_id=ballot_item_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        is_ballot_share=is_ballot_share,
        is_candidate_share=is_candidate_share,
        is_measure_share=is_measure_share,
        is_office_share=is_office_share,
        is_organization_share=is_organization_share,
        is_ready_share=is_ready_share,
        organization_we_vote_id=organization_we_vote_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@csrf_exempt
def super_share_item_save_view(request):  # superShareItemSave
    """
    We use superShareItemSave for saving data, retrieving the saved data, and sending the email.
    :param request:
    :return:
    """
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', None)
    campaignx_news_item_we_vote_id = request.POST.get('campaignx_news_item_we_vote_id', None)
    destination_full_url = request.POST.get('destination_full_url', '')
    # See also politician_starter_list_serialized
    email_recipient_list_serialized = request.POST.get('email_recipient_list', '')
    email_recipient_list_changed = positive_value_exists(request.POST.get('email_recipient_list_changed', False))
    personalized_subject = request.POST.get('personalized_subject', '')
    personalized_subject_changed = positive_value_exists(request.POST.get('personalized_subject_changed', False))
    personalized_message = request.POST.get('personalized_message', '')
    personalized_message_changed = positive_value_exists(request.POST.get('personalized_message_changed', False))
    send_now = positive_value_exists(request.POST.get('send_now', False))
    supers_share_item_id = request.POST.get('supers_share_item_id', 0)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    if send_now:
        json_data = super_share_item_send_for_api(
            supers_share_item_id=supers_share_item_id,
            voter_device_id=voter_device_id,
        )
    else:
        json_data = super_share_item_save_for_api(
            campaignx_we_vote_id=campaignx_we_vote_id,
            campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
            destination_full_url=destination_full_url,
            email_recipient_list_serialized=email_recipient_list_serialized,
            email_recipient_list_changed=email_recipient_list_changed,
            personalized_message=personalized_message,
            personalized_message_changed=personalized_message_changed,
            personalized_subject=personalized_subject,
            personalized_subject_changed=personalized_subject_changed,
            voter_device_id=voter_device_id,
        )
    return HttpResponse(json.dumps(json_data), content_type='application/json')
