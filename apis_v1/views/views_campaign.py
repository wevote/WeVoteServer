# apis_v1/views/views_campaign.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from campaign.controllers import campaignx_list_retrieve_for_api, campaignx_news_item_save_for_api, \
    campaignx_retrieve_for_api, campaignx_save_for_api, \
    campaignx_supporter_retrieve_for_api, campaignx_supporter_save_for_api
from config.base import get_environment_variable
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_user_agents.utils import get_user_agent
from exception.models import handle_exception
from follow.controllers import voter_campaignx_follow_for_api
import json
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def campaignx_list_retrieve_view(request):  # campaignListRetrieve (No CDN)
    hostname = request.GET.get('hostname', '')
    limit_to_this_state_code = request.GET.get('state_code', '')
    recommended_campaigns_for_campaignx_we_vote_id = \
        request.GET.get('recommended_campaigns_for_campaignx_we_vote_id', '')
    search_text = request.GET.get('search_text', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    json_data = campaignx_list_retrieve_for_api(
        hostname=hostname,
        limit_to_this_state_code=limit_to_this_state_code,
        recommended_campaigns_for_campaignx_we_vote_id=recommended_campaigns_for_campaignx_we_vote_id,
        request=request,
        search_text=search_text,
        voter_device_id=voter_device_id,
    )
    json_string = ''
    try:
        # March 24, 2021: Throwing "TypeError: Object of type 'HttpResponse' is not JSON serializable"
        json_string = json.dumps(json_data)
    except Exception as e:
        status = "Caught error for voter_device_id " + voter_device_id
        handle_exception(e, logger=logger, exception_message=status)

    return HttpResponse(json_string, content_type='application/json')


def campaignx_news_item_save_view(request):  # campaignNewsItemSave
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaign_news_subject = request.GET.get('campaign_news_subject', '')
    campaign_news_subject_changed = positive_value_exists(request.GET.get('campaign_news_subject_changed', False))
    campaign_news_text = request.GET.get('campaign_news_text', '')
    campaign_news_text_changed = positive_value_exists(request.GET.get('campaign_news_text_changed', False))
    campaignx_news_item_we_vote_id = request.GET.get('campaignx_news_item_we_vote_id', '')
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    in_draft_mode = positive_value_exists(request.GET.get('in_draft_mode', False))
    in_draft_mode_changed = positive_value_exists(request.GET.get('in_draft_mode_changed', False))
    send_now = positive_value_exists(request.GET.get('send_now', False))
    visible_to_public = positive_value_exists(request.GET.get('visible_to_public', True))
    visible_to_public_changed = positive_value_exists(request.GET.get('visible_to_public_changed', False))
    json_data = campaignx_news_item_save_for_api(
        campaign_news_subject=campaign_news_subject,
        campaign_news_subject_changed=campaign_news_subject_changed,
        campaign_news_text=campaign_news_text,
        campaign_news_text_changed=campaign_news_text_changed,
        campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        in_draft_mode=in_draft_mode,
        in_draft_mode_changed=in_draft_mode_changed,
        send_now=send_now,
        visible_to_public=visible_to_public,
        visible_to_public_changed=visible_to_public_changed,
        voter_device_id=voter_device_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def campaignx_supporter_retrieve_view(request):  # campaignSupporterRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    json_data = campaignx_supporter_retrieve_for_api(
        voter_device_id=voter_device_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def campaignx_retrieve_view(request):  # campaignRetrieve (CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    hostname = request.GET.get('hostname', '')
    seo_friendly_path = request.GET.get('seo_friendly_path', '')
    json_data = campaignx_retrieve_for_api(
        voter_device_id=voter_device_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        hostname=hostname,
        seo_friendly_path=seo_friendly_path,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def campaignx_retrieve_as_owner_view(request):  # campaignRetrieveAsOwner (No CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    hostname = request.GET.get('hostname', '')
    json_data = campaignx_retrieve_for_api(
        voter_device_id=voter_device_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        as_owner=True,
        hostname=hostname,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@csrf_exempt
def campaignx_save_view(request):  # campaignSave & campaignStartSave
    # This is set in /config/base.py: DATA_UPLOAD_MAX_MEMORY_SIZE = 6000000
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    campaign_description = request.POST.get('campaign_description', '')
    campaign_description_changed = positive_value_exists(request.POST.get('campaign_description_changed', False))
    in_draft_mode = positive_value_exists(request.POST.get('in_draft_mode', True))
    in_draft_mode_changed = positive_value_exists(request.POST.get('in_draft_mode_changed', False))
    campaign_photo_from_file_reader = request.POST.get('campaign_photo_from_file_reader', '')
    campaign_photo_changed = positive_value_exists(request.POST.get('campaign_photo_changed', False))
    campaign_photo_delete = request.POST.get('campaign_photo_delete', '')
    campaign_photo_delete_changed = positive_value_exists(request.POST.get('campaign_photo_delete_changed', False))
    campaign_title = request.POST.get('campaign_title', '')
    campaign_title_changed = positive_value_exists(request.POST.get('campaign_title_changed', False))
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', '')
    hostname = request.POST.get('hostname', '')
    politician_delete_list_serialized = request.POST.get('politician_delete_list', '')
    politician_starter_list_serialized = request.POST.get('politician_starter_list', '')
    politician_starter_list_changed = positive_value_exists(request.POST.get('politician_starter_list_changed', False))
    json_data = campaignx_save_for_api(
        campaign_description=campaign_description,
        campaign_description_changed=campaign_description_changed,
        in_draft_mode=in_draft_mode,
        in_draft_mode_changed=in_draft_mode_changed,
        campaign_photo_from_file_reader=campaign_photo_from_file_reader,
        campaign_photo_changed=campaign_photo_changed,
        campaign_photo_delete=campaign_photo_delete,
        campaign_photo_delete_changed=campaign_photo_delete_changed,
        campaign_title=campaign_title,
        campaign_title_changed=campaign_title_changed,
        campaignx_we_vote_id=campaignx_we_vote_id,
        hostname=hostname,
        politician_delete_list_serialized=politician_delete_list_serialized,
        politician_starter_list_serialized=politician_starter_list_serialized,
        politician_starter_list_changed=politician_starter_list_changed,
        request=request,
        voter_device_id=voter_device_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def campaignx_supporter_save_view(request):  # campaignSupporterSave
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    supporter_endorsement = request.GET.get('supporter_endorsement', '')
    supporter_endorsement_changed = positive_value_exists(request.GET.get('supporter_endorsement_changed', False))
    visible_to_public = positive_value_exists(request.GET.get('visible_to_public', True))
    visible_to_public_changed = positive_value_exists(request.GET.get('visible_to_public_changed', False))
    campaign_supported = positive_value_exists(request.GET.get('campaign_supported', False))
    campaign_supported_changed = positive_value_exists(request.GET.get('campaign_supported_changed', False))
    campaignx_we_vote_id = request.GET.get('campaignx_we_vote_id', '')
    json_data = campaignx_supporter_save_for_api(
        campaignx_we_vote_id=campaignx_we_vote_id,
        campaign_supported=campaign_supported,
        campaign_supported_changed=campaign_supported_changed,
        supporter_endorsement=supporter_endorsement,
        supporter_endorsement_changed=supporter_endorsement_changed,
        visible_to_public=visible_to_public,
        visible_to_public_changed=visible_to_public_changed,
        voter_device_id=voter_device_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_campaignx_follow_view(request):  # campaignFollow
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    issue_we_vote_id = request.GET.get('issue_we_vote_id', False)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    follow_value = positive_value_exists(request.GET.get('follow', False))
    user_agent_string = request.headers['user-agent']
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

