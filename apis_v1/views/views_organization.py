# apis_v1/views/views_organization.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from follow.models import UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW, \
    UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER, UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS, \
    UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS_ON_TWITTER, UPDATE_SUGGESTIONS_ALL, \
    FOLLOW_SUGGESTIONS_FROM_FRIENDS_ON_TWITTER, FOLLOW_SUGGESTIONS_FROM_FRIENDS, \
    FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW
from apis_v1.controllers import organization_count, organization_follow, organization_follow_ignore, \
    organization_stop_following
from config.base import get_environment_variable
from django.http import HttpResponse
from follow.controllers import organization_suggestion_tasks_for_api
import json
from organization.controllers import organization_retrieve_for_api, organization_save_for_api, \
    organization_search_for_api, organizations_followed_retrieve_for_api
from voter.models import voter_has_authority, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def organization_count_view(request):
    return organization_count()


def organization_follow_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_follow(voter_device_id=voter_device_id, organization_id=organization_id,
                               organization_we_vote_id=organization_we_vote_id)


def organization_stop_following_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_stop_following(voter_device_id=voter_device_id, organization_id=organization_id,
                                       organization_we_vote_id=organization_we_vote_id)


def organization_follow_ignore_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_follow_ignore(voter_device_id=voter_device_id, organization_id=organization_id,
                                      organization_we_vote_id=organization_we_vote_id)


def organization_retrieve_view(request):
    """
    Retrieve a single organization based on unique identifier
    :param request:
    :return:
    """
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_retrieve_for_api(
        organization_id=organization_id, organization_we_vote_id=organization_we_vote_id)


def organization_save_view(request):  # organizationSave
    """
    Save a single organization based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_name = request.GET.get('organization_name', False)
    organization_email = request.GET.get('organization_email', False)
    organization_website = request.GET.get('organization_website', False)
    organization_facebook = request.GET.get('organization_facebook', False)
    organization_image = request.GET.get('organization_image', False)

    # We only want to allow save if either this is your organization (i.e., you have the Twitter handle)
    voter_owns_twitter_handle = False
    voter_owns_facebook_id = False

    # Twitter specific
    organization_twitter_handle = request.GET.get('organization_twitter_handle', False)
    refresh_from_twitter = request.GET.get('refresh_from_twitter', False)

    # Facebook specific
    facebook_id = request.GET.get('facebook_id', False)
    if facebook_id is not False:
        facebook_id = convert_to_int(facebook_id)
    facebook_email = request.GET.get('facebook_email', False)
    facebook_profile_image_url_https = request.GET.get('facebook_profile_image_url_https', False)

    #  or if you are a verified volunteer or admin
    authority_required = {'admin', 'verified_volunteer'}  # admin, verified_volunteer
    voter_is_admin_or_verified_volunteer = False
    if voter_has_authority(request, authority_required):
        voter_is_admin_or_verified_volunteer = True
    else:
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']

            # Does this voter have the same Facebook id as this organization? If so, link this organization to
            #  this particular voter
            voter_facebook_id = voter_manager.fetch_facebook_id_from_voter_we_vote_id(voter.we_vote_id)
            if positive_value_exists(voter_facebook_id) \
                    and positive_value_exists(facebook_id) \
                    and voter_facebook_id == facebook_id:
                voter_owns_facebook_id = True

            # Does this voter have the same Twitter handle as this organization? If so, link this organization to
            #  this particular voter
            voter_twitter_handle = voter_manager.fetch_twitter_handle_from_voter_we_vote_id(voter.we_vote_id)
            if positive_value_exists(voter_twitter_handle) \
                    and positive_value_exists(organization_twitter_handle) \
                    and voter_twitter_handle.lower() == organization_twitter_handle.lower():
                voter_owns_twitter_handle = True

    if not voter_is_admin_or_verified_volunteer:
        if not voter_owns_twitter_handle and not voter_owns_facebook_id:
            # Only refuse entry if *both* conditions are not met
            results = {
                'status': "VOTER_LACKS_AUTHORITY_TO_SAVE_ORGANIZATION",
                'success': False,
                'organization_id': organization_id,
                'organization_we_vote_id': organization_we_vote_id,
                'new_organization_created': False,
                'organization_name': organization_name,
                'organization_email': organization_email,
                'organization_website': organization_website,
                'organization_facebook': organization_facebook,
                'organization_photo_url': organization_image,
                'organization_twitter_handle': organization_twitter_handle,
                'refresh_from_twitter': refresh_from_twitter,
                'twitter_followers_count': 0,
                'twitter_description': "",
                'facebook_id': facebook_id,
                'facebook_email': facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }
            return HttpResponse(json.dumps(results), content_type='application/json')

    results = organization_save_for_api(
        voter_device_id=voter_device_id, organization_id=organization_id,
        organization_we_vote_id=organization_we_vote_id,
        organization_name=organization_name, organization_email=organization_email,
        organization_website=organization_website, organization_twitter_handle=organization_twitter_handle,
        organization_facebook=organization_facebook, organization_image=organization_image,
        refresh_from_twitter=refresh_from_twitter,
        facebook_id=facebook_id, facebook_email=facebook_email,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def organization_search_view(request):
    """
    Search for organizations based on a few search terms
    :param request:
    :return:
    """
    organization_name = request.GET.get('organization_name', '')
    organization_twitter_handle = request.GET.get('organization_twitter_handle', '')
    organization_website = request.GET.get('organization_website', '')
    organization_email = request.GET.get('organization_email', '')
    return organization_search_for_api(organization_name=organization_name,
                                       organization_twitter_handle=organization_twitter_handle,
                                       organization_website=organization_website,
                                       organization_email=organization_email)


def organization_suggestion_tasks_view(request):
    """
    This will provide list of suggested organizations to follow.
    These suggestions are generated from twitter ids i follow, or organization of my friends follow.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_suggestion_task = request.GET.get('kind_of_suggestion_task',
                                              UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW)
    kind_of_follow_task = request.GET.get('kind_of_follow_task', '')
    if kind_of_suggestion_task not in (UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW,
                                       UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW,
                                       UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER,
                                       UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS,
                                       UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS_ON_TWITTER,
                                       UPDATE_SUGGESTIONS_ALL):
        kind_of_suggestion_task = UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW
    if kind_of_follow_task not in (FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, FOLLOW_SUGGESTIONS_FROM_FRIENDS,
                                   FOLLOW_SUGGESTIONS_FROM_FRIENDS_ON_TWITTER):
        kind_of_follow_task = ''
    results = organization_suggestion_tasks_for_api(voter_device_id=voter_device_id,
                                                    kind_of_suggestion_task=kind_of_suggestion_task,
                                                    kind_of_follow_task=kind_of_follow_task)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'kind_of_suggestion_task': kind_of_suggestion_task,
        'kind_of_follow_task': kind_of_follow_task,
        'organization_suggestion_task_saved': results['organization_suggestion_task_saved'],
        'organization_suggestion_list': results['organization_suggestion_list'],
        'organization_suggestion_followed_list': results['organization_suggestion_followed_list']
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organizations_followed_retrieve_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    auto_followed_from_twitter_suggestion = request.GET.get('auto_followed_from_twitter_suggestion', False)
    return organizations_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                   maximum_number_to_retrieve=maximum_number_to_retrieve,
                                                   auto_followed_from_twitter_suggestio=
                                                   auto_followed_from_twitter_suggestion)


def get_maximum_number_to_retrieve_from_request(request):
    if 'maximum_number_to_retrieve' in request.GET:
        maximum_number_to_retrieve = request.GET['maximum_number_to_retrieve']
    else:
        maximum_number_to_retrieve = 40
    if maximum_number_to_retrieve is "":
        maximum_number_to_retrieve = 40
    else:
        maximum_number_to_retrieve = convert_to_int(maximum_number_to_retrieve)

    return maximum_number_to_retrieve
