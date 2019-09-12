# apis_v1/views/views_organization.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from follow.models import UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW, \
    UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER, UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS, \
    UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS_ON_TWITTER, UPDATE_SUGGESTIONS_ALL, \
    FOLLOW_SUGGESTIONS_FROM_FRIENDS_ON_TWITTER, FOLLOW_SUGGESTIONS_FROM_FRIENDS, \
    FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW
from apis_v1.controllers import organization_count, organization_follow, organization_follow_ignore, \
    organization_stop_following, organization_stop_ignoring
from config.base import get_environment_variable
from django.http import HttpResponse
from django_user_agents.utils import get_user_agent
from django.views.decorators.csrf import csrf_exempt
from follow.controllers import organization_suggestion_tasks_for_api
import json
from organization.controllers import full_domain_string_available, organization_analytics_by_voter_for_api, \
    organization_retrieve_for_api, organization_photos_save_for_api, \
    organization_save_for_api, organization_search_for_api, organizations_followed_retrieve_for_api, \
    site_configuration_retrieve_for_api, sub_domain_string_available
from organization.models import OrganizationManager
from voter.models import voter_has_authority, VoterManager
from voter_guide.controllers_possibility import organizations_found_on_url
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, \
    get_maximum_number_to_retrieve_from_request, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def organization_analytics_by_voter_view(request):  # organizationAnalyticsByVoter
    """
    Retrieve analytics for an organization's members.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_api_pass_code = request.GET.get('organization_api_pass_code', '')
    external_voter_id = request.GET.get('external_voter_id', '')
    voter_we_vote_id = request.GET.get('voter_we_vote_id', '')
    google_civic_election_id = request.GET.get('election_id', 0)

    results = organization_analytics_by_voter_for_api(
        voter_device_id=voter_device_id,
        organization_we_vote_id=organization_we_vote_id,
        organization_api_pass_code=organization_api_pass_code,
        external_voter_id=external_voter_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
    )
    return HttpResponse(json.dumps(results), content_type='application/json')


def organization_count_view(request):
    return organization_count()


def organization_follow_api_view(request):  # organizationFollow
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_twitter_handle = request.GET.get('organization_twitter_handle', '')
    organization_follow_based_on_issue = request.GET.get('organization_follow_based_on_issue', False)
    organization_follow_based_on_issue = positive_value_exists(organization_follow_based_on_issue)
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    return organization_follow(voter_device_id=voter_device_id, organization_id=organization_id,
                               organization_we_vote_id=organization_we_vote_id,
                               organization_twitter_handle=organization_twitter_handle,
                               organization_follow_based_on_issue=organization_follow_based_on_issue,
                               user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def organization_stop_following_api_view(request):  # organizationStopFollowing
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    return organization_stop_following(voter_device_id=voter_device_id, organization_id=organization_id,
                                       organization_we_vote_id=organization_we_vote_id,
                                       user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def organization_stop_ignoring_api_view(request):  # organizationStopIgnoring
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    return organization_stop_ignoring(voter_device_id=voter_device_id, organization_id=organization_id,
                                      organization_we_vote_id=organization_we_vote_id,
                                      user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def organization_follow_ignore_api_view(request):  # organizationFollowIgnore
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    return organization_follow_ignore(voter_device_id=voter_device_id, organization_id=organization_id,
                                      organization_we_vote_id=organization_we_vote_id,
                                      user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def organizations_found_on_url_api_view(request):  # organizationsFoundOnUrl
    """
    Take in a web page and find all organizations that have a Twitter handle or Facebook page listed on that web page
    :param request:
    :return:
    """
    url_to_scan = request.GET.get('url_to_scan', '')
    state_code = request.GET.get('state_code', '')
    scan_results = organizations_found_on_url(
        url_to_scan=url_to_scan,
        state_code=state_code,
    )

    organization_list_for_json = []
    success = scan_results['success']
    status = scan_results['status']
    if positive_value_exists(scan_results['organization_count']):
        organization_list_for_json = scan_results['organization_list']

    json_data = {
        'status':               status,
        'success':              success,
        'url_to_scan':          url_to_scan,
        'organization_count':   scan_results['organization_count'],
        'organization_list':    organization_list_for_json,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@csrf_exempt
def organization_photos_save_view(request):  # organizationPhotosSave
    """
    Save 'external' photos for an organization. These are currently photos which are manually uploaded by an org.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.POST.get('organization_id', 0)
    organization_twitter_handle = request.POST.get('organization_twitter_handle', False)
    organization_we_vote_id = request.POST.get('organization_we_vote_id', '')

    status = ''
    chosen_favicon_from_file_reader = request.POST.get('chosen_favicon_from_file_reader', False)
    chosen_logo_from_file_reader = request.POST.get('chosen_logo_from_file_reader', False)
    chosen_social_share_master_image_from_file_reader = \
        request.POST.get('chosen_social_share_master_image_from_file_reader', False)
    delete_chosen_favicon = positive_value_exists(request.POST.get('delete_chosen_favicon', False))
    delete_chosen_logo = positive_value_exists(request.POST.get('delete_chosen_logo', False))
    delete_chosen_social_share_master_image = \
        positive_value_exists(request.POST.get('delete_chosen_social_share_master_image', False))

    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'political_data_manager'}
    voter_has_authority_required = False
    if voter_has_authority(request, authority_required):
        voter_has_authority_required = True
    else:
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_is_signed_in = voter.is_signed_in()

            if positive_value_exists(voter_is_signed_in):
                voter_twitter_handle = voter_manager.fetch_twitter_handle_from_voter_we_vote_id(voter.we_vote_id)
                # Is this voter linked to this organization?
                if positive_value_exists(voter.linked_organization_we_vote_id) \
                        and positive_value_exists(organization_we_vote_id) \
                        and voter.linked_organization_we_vote_id == organization_we_vote_id:
                    # organization_linked_to_this_voter = True
                    voter_has_authority_required = True
                # Does this voter have the same Twitter handle as this organization?
                elif positive_value_exists(voter_twitter_handle) \
                        and positive_value_exists(organization_twitter_handle) \
                        and voter_twitter_handle.lower() == organization_twitter_handle.lower():
                    # voter_owns_twitter_handle = True
                    voter_has_authority_required = True

    if not voter_has_authority_required:
        status += "VOTER_LACKS_AUTHORITY_TO_SAVE_ORGANIZATION "
        results = {
            'status': status,
            'success': False,
            'chosen_favicon_url_https': '',
            'chosen_logo_url_https': '',
            'chosen_social_share_image_256x256_url_https': '',
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
        }
        return HttpResponse(json.dumps(results), content_type='application/json')

    # By the time we are here, we know that this voter has the authority to update the organization's photos
    json_data = organization_photos_save_for_api(
        organization_id=organization_id,
        organization_we_vote_id=organization_we_vote_id,
        chosen_favicon_from_file_reader=chosen_favicon_from_file_reader,
        chosen_logo_from_file_reader=chosen_logo_from_file_reader,
        chosen_social_share_master_image_from_file_reader=chosen_social_share_master_image_from_file_reader,
        delete_chosen_favicon=delete_chosen_favicon,
        delete_chosen_logo=delete_chosen_logo,
        delete_chosen_social_share_master_image=delete_chosen_social_share_master_image,
        prior_status=status)

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_retrieve_view(request):  # organizationRetrieve
    """
    Retrieve a single organization based on unique identifier
    :param request:
    :return:
    """
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return organization_retrieve_for_api(
        organization_id=organization_id,
        organization_we_vote_id=organization_we_vote_id,
        voter_device_id=voter_device_id,
    )


def organization_save_view(request):  # organizationSave
    """
    Save a single organization based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_email = request.GET.get('organization_email', False)
    organization_description = request.GET.get('organization_description', False)
    organization_facebook = request.GET.get('organization_facebook', False)
    organization_id = request.GET.get('organization_id', 0)
    organization_image = request.GET.get('organization_image', False)
    organization_instagram_handle = request.GET.get('organization_instagram_handle', False)
    organization_name = request.GET.get('organization_name', False)
    organization_type = request.GET.get('organization_type', False)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_website = request.GET.get('organization_website', False)
    # We only want to allow save if either this is your organization (i.e., you have the Twitter handle)
    organization_linked_to_this_voter = False
    voter_is_signed_in = False
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

    organization_manager = OrganizationManager()
    chosen_domain_string = request.GET.get('chosen_domain_string', False)
    chosen_sub_domain_string = request.GET.get('chosen_sub_domain_string', False)

    chosen_google_analytics_account_number = request.GET.get('chosen_google_analytics_account_number', False)
    chosen_html_verification_string = request.GET.get('chosen_html_verification_string', False)
    chosen_hide_we_vote_logo = request.GET.get('chosen_hide_we_vote_logo', None)
    chosen_social_share_description = request.GET.get('chosen_social_share_description', False)
    chosen_subscription_plan = request.GET.get('chosen_subscription_plan', False)

    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'political_data_manager', 'verified_volunteer'}
    voter_has_authority_required = False
    if voter_has_authority(request, authority_required):
        voter_has_authority_required = True
    else:
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_is_signed_in = voter.is_signed_in()

            # Is this voter linked to this organization?
            if positive_value_exists(voter.linked_organization_we_vote_id) \
                    and positive_value_exists(organization_we_vote_id) \
                    and voter.linked_organization_we_vote_id == organization_we_vote_id:
                organization_linked_to_this_voter = True

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

    if not voter_has_authority_required:
        if not voter_owns_twitter_handle and not voter_owns_facebook_id and not organization_linked_to_this_voter:
            # Only refuse entry if *both* conditions are not met
            results = {
                'status': "VOTER_LACKS_AUTHORITY_TO_SAVE_ORGANIZATION",
                'success': False,
                'chosen_domain_string': '',
                'full_domain_string_already_taken': None,
                'chosen_favicon_url_https': '',
                'chosen_google_analytics_account_number': '',
                'chosen_html_verification_string': '',
                'chosen_hide_we_vote_logo': '',
                'chosen_logo_url_https': '',
                'chosen_social_share_description': '',
                'chosen_social_share_image_256x256_url_https': '',
                'chosen_sub_domain_string': '',
                'sub_domain_string_already_taken': None,
                'chosen_subscription_plan': '',
                'facebook_id': facebook_id,
                'facebook_email': facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
                'new_organization_created': False,
                'organization_description': organization_description,
                'organization_email': organization_email,
                'organization_facebook': organization_facebook,
                'organization_id': organization_id,
                'organization_instagram_handle': organization_instagram_handle,
                'organization_name': organization_name,
                'organization_photo_url': organization_image,
                'organization_twitter_handle': organization_twitter_handle,
                'organization_type': organization_type,
                'organization_we_vote_id': organization_we_vote_id,
                'organization_website': organization_website,
                'refresh_from_twitter': refresh_from_twitter,
                'twitter_followers_count': 0,
                'twitter_description': "",
            }
            return HttpResponse(json.dumps(results), content_type='application/json')

    full_domain_string_already_taken = None
    sub_domain_string_already_taken = None
    if voter_is_signed_in and organization_linked_to_this_voter:
        # Check to make sure it is ok to assign this full_domain or sub_domain to this organization
        # Voter must be signed in to save this
        if positive_value_exists(chosen_domain_string) or positive_value_exists(chosen_sub_domain_string):
            if not positive_value_exists(organization_id) and positive_value_exists(organization_we_vote_id):
                results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)
                if results['success']:
                    organization_id = results['organization_id']
        full_domain_string_already_taken = False
        if positive_value_exists(chosen_domain_string):
            domain_results = full_domain_string_available(chosen_domain_string, organization_id)
            if not domain_results['full_domain_string_available']:
                full_domain_string_already_taken = True
                # Do not save it
                chosen_domain_string = False
        sub_domain_string_already_taken = False
        if positive_value_exists(chosen_sub_domain_string):
            domain_results = sub_domain_string_available(chosen_sub_domain_string, organization_id)
            if not domain_results['sub_domain_string_available']:
                sub_domain_string_already_taken = True
                # Do not save it
                chosen_sub_domain_string = False
    else:
        chosen_domain_string = False
        chosen_sub_domain_string = False

    results = organization_save_for_api(
        voter_device_id=voter_device_id,
        organization_id=organization_id,
        organization_we_vote_id=organization_we_vote_id,
        organization_name=organization_name,
        organization_description=organization_description,
        organization_email=organization_email,
        organization_website=organization_website,
        organization_twitter_handle=organization_twitter_handle,
        organization_facebook=organization_facebook,
        organization_instagram_handle=organization_instagram_handle,
        organization_image=organization_image,
        organization_type=organization_type,
        refresh_from_twitter=refresh_from_twitter,
        facebook_id=facebook_id,
        facebook_email=facebook_email,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        chosen_domain_string=chosen_domain_string,
        chosen_google_analytics_account_number=chosen_google_analytics_account_number,
        chosen_html_verification_string=chosen_html_verification_string,
        chosen_hide_we_vote_logo=chosen_hide_we_vote_logo,
        chosen_social_share_description=chosen_social_share_description,
        chosen_sub_domain_string=chosen_sub_domain_string,
        chosen_subscription_plan=chosen_subscription_plan,
    )
    results['full_domain_string_already_taken'] = full_domain_string_already_taken
    results['sub_domain_string_already_taken'] = sub_domain_string_already_taken

    return HttpResponse(json.dumps(results), content_type='application/json')


def organization_search_view(request):  # organizationSearch
    """
    Search for organizations based on a few search terms
    :param request:
    :return:
    """
    organization_search_term = request.GET.get('organization_search_term', '')
    organization_name = request.GET.get('organization_name', '')
    organization_twitter_handle = request.GET.get('organization_twitter_handle', '')
    organization_website = request.GET.get('organization_website', '')
    organization_email = request.GET.get('organization_email', '')
    exact_match = positive_value_exists(request.GET.get('exact_match', False))
    return organization_search_for_api(organization_search_term=organization_search_term,
                                       organization_name=organization_name,
                                       organization_twitter_handle=organization_twitter_handle,
                                       organization_website=organization_website,
                                       organization_email=organization_email,
                                       exact_match=exact_match)


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


def organizations_followed_retrieve_api_view(request):  # organizationsFollowedRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    auto_followed_from_twitter_suggestion = request.GET.get('auto_followed_from_twitter_suggestion', False)
    return organizations_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                   maximum_number_to_retrieve=maximum_number_to_retrieve,
                                                   auto_followed_from_twitter_suggestion=
                                                   auto_followed_from_twitter_suggestion)


def site_configuration_retrieve_view(request):  # siteConfigurationRetrieve
    """
    Retrieve the configuration settings for a private-labeled site set up by one organization
    :param request:
    :return:
    """
    hostname = request.GET.get('hostname', '')
    return site_configuration_retrieve_for_api(hostname)
