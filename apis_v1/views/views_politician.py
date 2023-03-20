# apis_v1/views/views_politician.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from politician.controllers import politician_retrieve_for_api
# from politician.controllers import politician_list_retrieve_for_api, politician_news_item_save_for_api, \
#     politician_save_for_api, \
#     politician_supporter_retrieve_for_api, politician_supporter_save_for_api
from config.base import get_environment_variable
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_user_agents.utils import get_user_agent
from exception.models import handle_exception
# from follow.controllers import voter_politician_follow_for_api
import json
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


# def politician_news_item_save_view(request):  # politicianNewsItemSave
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     politician_news_subject = request.GET.get('politician_news_subject', '')
#     politician_news_subject_changed = positive_value_exists(request.GET.get('politician_news_subject_changed', False))
#     politician_news_text = request.GET.get('politician_news_text', '')
#     politician_news_text_changed = positive_value_exists(request.GET.get('politician_news_text_changed', False))
#     politician_news_item_we_vote_id = request.GET.get('politician_news_item_we_vote_id', '')
#     politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
#     in_draft_mode = positive_value_exists(request.GET.get('in_draft_mode', False))
#     in_draft_mode_changed = positive_value_exists(request.GET.get('in_draft_mode_changed', False))
#     send_now = positive_value_exists(request.GET.get('send_now', False))
#     visible_to_public = positive_value_exists(request.GET.get('visible_to_public', True))
#     visible_to_public_changed = positive_value_exists(request.GET.get('visible_to_public_changed', False))
#     json_data = politician_news_item_save_for_api(
#         politician_news_subject=politician_news_subject,
#         politician_news_subject_changed=politician_news_subject_changed,
#         politician_news_text=politician_news_text,
#         politician_news_text_changed=politician_news_text_changed,
#         politician_news_item_we_vote_id=politician_news_item_we_vote_id,
#         politician_we_vote_id=politician_we_vote_id,
#         in_draft_mode=in_draft_mode,
#         in_draft_mode_changed=in_draft_mode_changed,
#         send_now=send_now,
#         visible_to_public=visible_to_public,
#         visible_to_public_changed=visible_to_public_changed,
#         voter_device_id=voter_device_id,
#     )
#     return HttpResponse(json.dumps(json_data), content_type='application/json')


# def politician_supporter_retrieve_view(request):  # politicianSupporterRetrieve
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
#     json_data = politician_supporter_retrieve_for_api(
#         voter_device_id=voter_device_id,
#         politician_we_vote_id=politician_we_vote_id,
#     )
#     return HttpResponse(json.dumps(json_data), content_type='application/json')


def politician_retrieve_view(request):  # politicianRetrieve (CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
    hostname = request.GET.get('hostname', '')
    seo_friendly_path = request.GET.get('seo_friendly_path', '')
    json_data = politician_retrieve_for_api(
        request=request,
        voter_device_id=voter_device_id,
        politician_we_vote_id=politician_we_vote_id,
        hostname=hostname,
        seo_friendly_path=seo_friendly_path,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def politician_retrieve_as_owner_view(request):  # politicianRetrieveAsOwner (No CDN)
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
    hostname = request.GET.get('hostname', '')
    json_data = politician_retrieve_for_api(
        request=request,
        voter_device_id=voter_device_id,
        politician_we_vote_id=politician_we_vote_id,
        as_owner=True,
        hostname=hostname,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


# @csrf_exempt
# def politician_save_view(request):  # politicianSave & politicianStartSave
#     # This is set in /config/base.py: DATA_UPLOAD_MAX_MEMORY_SIZE = 6000000
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     politician_description = request.POST.get('politician_description', '')
#     politician_description_changed = positive_value_exists(request.POST.get('politician_description_changed', False))
#     in_draft_mode = positive_value_exists(request.POST.get('in_draft_mode', True))
#     in_draft_mode_changed = positive_value_exists(request.POST.get('in_draft_mode_changed', False))
#     politician_photo_from_file_reader = request.POST.get('politician_photo_from_file_reader', '')
#     politician_photo_changed = positive_value_exists(request.POST.get('politician_photo_changed', False))
#     politician_photo_delete = request.POST.get('politician_photo_delete', '')
#     politician_photo_delete_changed = positive_value_exists(request.POST.get('politician_photo_delete_changed', False))
#     politician_title = request.POST.get('politician_title', '')
#     politician_title_changed = positive_value_exists(request.POST.get('politician_title_changed', False))
#     politician_we_vote_id = request.POST.get('politician_we_vote_id', '')
#     politician_delete_list_serialized = request.POST.get('politician_delete_list', '')
#     politician_starter_list_serialized = request.POST.get('politician_starter_list', '')
#     politician_starter_list_changed = positive_value_exists(request.POST.get('politician_starter_list_changed', False))
#     json_data = politician_save_for_api(
#         politician_description=politician_description,
#         politician_description_changed=politician_description_changed,
#         in_draft_mode=in_draft_mode,
#         in_draft_mode_changed=in_draft_mode_changed,
#         politician_photo_from_file_reader=politician_photo_from_file_reader,
#         politician_photo_changed=politician_photo_changed,
#         politician_photo_delete=politician_photo_delete,
#         politician_photo_delete_changed=politician_photo_delete_changed,
#         politician_title=politician_title,
#         politician_title_changed=politician_title_changed,
#         politician_we_vote_id=politician_we_vote_id,
#         politician_delete_list_serialized=politician_delete_list_serialized,
#         politician_starter_list_serialized=politician_starter_list_serialized,
#         politician_starter_list_changed=politician_starter_list_changed,
#         voter_device_id=voter_device_id,
#     )
#     return HttpResponse(json.dumps(json_data), content_type='application/json')


# def politician_supporter_save_view(request):  # politicianSupporterSave
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     supporter_endorsement = request.GET.get('supporter_endorsement', '')
#     supporter_endorsement_changed = positive_value_exists(request.GET.get('supporter_endorsement_changed', False))
#     visible_to_public = positive_value_exists(request.GET.get('visible_to_public', True))
#     visible_to_public_changed = positive_value_exists(request.GET.get('visible_to_public_changed', False))
#     politician_supported = positive_value_exists(request.GET.get('politician_supported', False))
#     politician_supported_changed = positive_value_exists(request.GET.get('politician_supported_changed', False))
#     politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
#     json_data = politician_supporter_save_for_api(
#         politician_we_vote_id=politician_we_vote_id,
#         politician_supported=politician_supported,
#         politician_supported_changed=politician_supported_changed,
#         supporter_endorsement=supporter_endorsement,
#         supporter_endorsement_changed=supporter_endorsement_changed,
#         visible_to_public=visible_to_public,
#         visible_to_public_changed=visible_to_public_changed,
#         voter_device_id=voter_device_id,
#     )
#     return HttpResponse(json.dumps(json_data), content_type='application/json')


# def voter_politician_follow_view(request):  # politicianFollow
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     issue_we_vote_id = request.GET.get('issue_we_vote_id', False)
#     google_civic_election_id = request.GET.get('google_civic_election_id', 0)
#     follow_value = positive_value_exists(request.GET.get('follow', False))
#     user_agent_string = request.META['HTTP_USER_AGENT']
#     user_agent_object = get_user_agent(request)
#     ignore_value = positive_value_exists(request.GET.get('ignore', False))
#
#     result = voter_politician_follow_for_api(
#         voter_device_id=voter_device_id,
#         issue_we_vote_id=issue_we_vote_id,
#         follow_value=follow_value,
#         ignore_value=ignore_value, user_agent_string=user_agent_string,
#         user_agent_object=user_agent_object)
#     result['google_civic_election_id'] = google_civic_election_id
#     return HttpResponse(json.dumps(result), content_type='application/json')

