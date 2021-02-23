# apis_v1/views/views_campaign.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from campaign.controllers import campaignx_list_retrieve_for_api, campaignx_retrieve_for_api, campaignx_save_for_api
from config.base import get_environment_variable
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_user_agents.utils import get_user_agent
from follow.controllers import voter_campaignx_follow_for_api
import json
import wevote_functions.admin
from wevote_functions.functions import convert_to_bool, get_voter_device_id,  \
    is_speaker_type_organization, is_speaker_type_public_figure, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def campaignx_list_retrieve_view(request):  # campaignListRetrieve (No CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    json_data = campaignx_list_retrieve_for_api(
        voter_device_id=voter_device_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def campaignx_retrieve_view(request):  # campaignRetrieve (CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    json_data = campaignx_retrieve_for_api(
        voter_device_id=voter_device_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def campaignx_retrieve_as_owner_view(request):  # campaignRetrieveAsOwner (No CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    json_data = campaignx_retrieve_for_api(
        voter_device_id=voter_device_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        as_owner=True,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@csrf_exempt
def campaignx_save_view(request):  # campaignSave & campaignStartSave
    # This is set in /config/base.py: DATA_UPLOAD_MAX_MEMORY_SIZE = 6000000
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaign_description = request.POST.get('campaign_description', '')
    campaign_description_changed = positive_value_exists(request.POST.get('campaign_description_changed', False))
    campaign_photo_from_file_reader = request.POST.get('campaign_photo_from_file_reader', '')
    campaign_photo_changed = positive_value_exists(request.POST.get('campaign_photo_changed', False))
    campaign_title = request.POST.get('campaign_title', '')
    campaign_title_changed = positive_value_exists(request.POST.get('campaign_title_changed', False))
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', '')
    politician_list_serialized = request.POST.get('politician_list', '')
    politician_list_changed = positive_value_exists(request.POST.get('politician_list_changed', False))
    json_data = campaignx_save_for_api(
        campaign_description=campaign_description,
        campaign_description_changed=campaign_description_changed,
        campaign_photo_from_file_reader=campaign_photo_from_file_reader,
        campaign_photo_changed=campaign_photo_changed,
        campaign_title=campaign_title,
        campaign_title_changed=campaign_title_changed,
        campaignx_we_vote_id=campaignx_we_vote_id,
        politician_list_serialized=politician_list_serialized,
        politician_list_changed=politician_list_changed,
        voter_device_id=voter_device_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_campaignx_follow_view(request):  # campaignFollow
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    issue_we_vote_id = request.GET.get('issue_we_vote_id', False)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    follow_value = positive_value_exists(request.GET.get('follow', False))
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    ignore_value = positive_value_exists(request.GET.get('ignore', False))

    result = voter_campaignx_follow_for_api(
        voter_device_id=voter_device_id,
        issue_we_vote_id=issue_we_vote_id,
        follow_value=follow_value,
        ignore_value=ignore_value, user_agent_string=user_agent_string,
        user_agent_object=user_agent_object)
    result['google_civic_election_id'] = google_civic_election_id
    return HttpResponse(json.dumps(result), content_type='application/json')

