# import_export_facebook/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from candidate.controllers import FACEBOOK, save_image_to_candidate_table
from candidate.models import CandidateCampaign, CandidateListManager, \
    PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_UNKNOWN
from image.controllers import organize_object_photo_fields_based_on_image_type_currently_active
from organization.controllers import save_image_to_organization_table
from organization.models import Organization
from volunteer_task.models import VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE, VolunteerTaskManager
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import RemoteRequestHistory, RemoteRequestHistoryManager, RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS
from .controllers import get_facebook_photo_url_from_facebook_url

logger = wevote_functions.admin.get_logger(__name__)

MAXIMUM_FACEBOOK_IMAGES_TO_RECEIVE_AT_ONCE = 50


def get_photo_url_from_facebook_graphapi(
        incoming_object=None,
        request={},
        remote_request_history_manager=None,
        save_to_database=False,
        add_messages=False):
    status = ""
    success = True
    facebook_photo_saved = False
    is_candidate = False
    is_organization = False
    is_politician = False
    if remote_request_history_manager is None:
        remote_request_history_manager = RemoteRequestHistoryManager()

    if hasattr(incoming_object, 'facebook_url'):
        facebook_url = incoming_object.facebook_url
        google_civic_election_id = incoming_object.google_civic_election_id
        is_candidate = True
    else:
        facebook_url = incoming_object.organization_facebook
        google_civic_election_id = ''
        is_organization = True

    results = get_facebook_photo_url_from_facebook_url(facebook_url)
    if results.get('success'):
        photo_url = results.get('photo_url')
        incoming_object_changes = False
        if results.get('is_silhouette'):
            if is_candidate or is_organization or is_politician:
                incoming_object_changes = True
                incoming_object.facebook_photo_url = None
                incoming_object.facebook_photo_url_is_broken = False
                incoming_object.facebook_photo_url_is_placeholder = True
                if incoming_object.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                    incoming_object.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                    incoming_object.we_vote_hosted_profile_image_url_large = None
                    incoming_object.we_vote_hosted_profile_image_url_medium = None
                    incoming_object.we_vote_hosted_profile_image_url_tiny = None
                    results = organize_object_photo_fields_based_on_image_type_currently_active(
                        object_with_photo_fields=incoming_object)
                    if results['success']:
                        incoming_object = results['object_with_photo_fields']
                    else:
                        status += "ORGANIZE_OBJECT_PROBLEM2: " + results['status']
        elif results['photo_url_found']:
            if is_candidate or is_organization:
                incoming_object_changes = True
                incoming_object.facebook_photo_url = photo_url
                incoming_object.facebook_photo_url_is_placeholder = False
                incoming_object.facebook_url_is_broken = False
                if incoming_object.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                    incoming_object.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                    incoming_object.we_vote_hosted_profile_image_url_large = None
                    incoming_object.we_vote_hosted_profile_image_url_medium = None
                    incoming_object.we_vote_hosted_profile_image_url_tiny = None
                    results = organize_object_photo_fields_based_on_image_type_currently_active(
                        object_with_photo_fields=incoming_object)
                    if results['success']:
                        incoming_object = results['object_with_photo_fields']
                    else:
                        status += "ORGANIZE_OBJECT_PROBLEM1: " + results['status']
        elif not results.get('photo_url_found'):
            if is_candidate or is_organization or is_politician:
                incoming_object_changes = True
                incoming_object.facebook_photo_url = None
                incoming_object.facebook_photo_url_is_broken = True
                # If we have an earlier photo, we don't want to remove it
                # if incoming_object.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                #     incoming_object.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN
                #     incoming_object.we_vote_hosted_profile_image_url_large = None
                #     incoming_object.we_vote_hosted_profile_image_url_medium = None
                #     incoming_object.we_vote_hosted_profile_image_url_tiny = None
                #     results = organize_object_photo_fields_based_on_image_type_currently_active(
                #         object_with_photo_fields=incoming_object)
                #     if results['success']:
                #         incoming_object = results['object_with_photo_fields']
                #     else:
                #         status += "ORGANIZE_OBJECT_PROBLEM2: " + results['status']
        else:
            status += "FACEBOOK_PHOTO_URL_NOT_FOUND_AND_NOT_SILHOUETTE: " + facebook_url + " "
            status += results['status']

        if save_to_database and incoming_object_changes:
            incoming_object.save()

        # link_is_broken = results.get('http_response_code') == 404
        is_placeholder_photo = results.get('is_silhouette')
        if is_placeholder_photo:
            # status += results['status']
            status += "IS_PLACEHOLDER_PHOTO "
            logger.info("Placeholder/Silhouette: " + photo_url)
            if add_messages:
                messages.add_message(
                    request, messages.INFO,
                    'Failed to retrieve Facebook picture:  The Facebook URL is for placeholder/Silhouette image.')
            # Create a record denoting that we have retrieved from Facebook for this candidate
            if is_candidate:
                save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                    kind_of_action=RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS,
                    google_civic_election_id=google_civic_election_id,
                    candidate_campaign_we_vote_id=incoming_object.we_vote_id,
                    number_of_results=1,
                    status="CANDIDATE_FACEBOOK_URL_IS_PLACEHOLDER_SILHOUETTE:" + str(photo_url))
        elif results['photo_url_found']:
            # Success!
            logger.info("Queried URL: " + facebook_url + " ==> " + photo_url)
            if add_messages:
                messages.add_message(request, messages.INFO, 'Facebook photo retrieved.')
            if is_candidate:
                results = save_image_to_candidate_table(
                    candidate=incoming_object,
                    image_url=photo_url,
                    source_link=facebook_url,
                    url_is_broken=False,
                    kind_of_source_website=FACEBOOK)
                if results['success']:
                    facebook_photo_saved = True
                # When saving to candidate object, update:
                # we_vote_hosted_profile_facebook_image_url_tiny
            elif is_organization:
                results = save_image_to_organization_table(
                    incoming_object,
                    photo_url,
                    facebook_url,
                    False,
                    FACEBOOK)
                if results['success']:
                    facebook_photo_saved = True

            if facebook_photo_saved:
                status += "SAVED_FB_IMAGE "
                # Create a record denoting that we have retrieved from Facebook for this candidate

                if is_candidate:
                    save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                        kind_of_action=RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS,
                        google_civic_election_id=google_civic_election_id,
                        candidate_campaign_we_vote_id=incoming_object.we_vote_id,
                        number_of_results=1,
                        status="CANDIDATE_FACEBOOK_URL_PARSED_HTTP:" + facebook_url)
            elif is_placeholder_photo:
                pass
            else:
                success = False
                status += results['status']
                status += "SAVE_IMAGE_TO_CANDIDATE_TABLE_FAILED "

    else:
        success = False
        status += results['status']
        status += "GET_FACEBOOK_FAILED "

        if add_messages:
            if len(results.get('clean_message')) > 0:
                messages.add_message(request, messages.ERROR, results.get('clean_message'))
            else:
                messages.add_message(
                    request, messages.ERROR, 'Facebook photo NOT retrieved (2). status: ' + results.get('status'))

    results = {
        'success': success,
        'status': status,
    }
    return results


# Test SQL for pgAdmin 4
# Find all eligible rows
#   SELECT * FROM public.candidate_candidatecampaign
#     where google_civic_election_id = '4456' and facebook_profile_image_url_https is null and
#     (facebook_url is not null or facebook_url != '');
# Set all the facebook facebook_profile_image_url_https picture urls to null
#   UPDATE public.candidate_candidatecampaign SET facebook_profile_image_url_https = NULL;
# Set all the  all the facebook_urls that are '' to null
#   UPDATE public.candidate_candidatecampaign SET facebook_url = NULL where facebook_url = '';
# Count all the facebook_profile_image_url_https picture urls
#   SELECT COUNT(facebook_profile_image_url_https) FROM public.candidate_candidatecampaign;
# Count how many facebook_urls exist
#   SELECT COUNT(facebook_url) FROM public.candidate_candidatecampaign;
# Get all the lines for a specific google_civic_election_id
#   SELECT * FROM public.candidate_candidatecampaign where google_civic_election_id = '1000052';
# Ignoring remote_request_history_manager, how many facebook_urls are there to process?
#   SELECT COUNT(facebook_url) FROM public.candidate_candidatecampaign where
# facebook_profile_image_url_https is null and google_civic_election_id = '1000052'; … 17
# Clear the wevote_settings_remoterequesthistory table to allow all lines to be processed, by right clicking
# on the table in pgAdmin and choosing truncate


@login_required
def bulk_retrieve_facebook_photos_view(request):
    status = ""
    remote_request_history_manager = RemoteRequestHistoryManager()

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    limit = convert_to_int(request.GET.get('show_all', MAXIMUM_FACEBOOK_IMAGES_TO_RECEIVE_AT_ONCE))

    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code) \
            and not positive_value_exists(limit):
        messages.add_message(request, messages.ERROR,
                             'bulk_retrieve_facebook_photos_view, LIMITING_VARIABLE_REQUIRED')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    try:
        # Give the volunteer who entered this credit
        volunteer_task_manager = VolunteerTaskManager()
        task_results = volunteer_task_manager.create_volunteer_task_completed(
            action_constant=VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE,
            request=request,
        )
    except Exception as e:
        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    # #############################################################
    # Get candidates in the elections we care about - used below
    candidate_list_manager = CandidateListManager()
    if positive_value_exists(google_civic_election_id):
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=[google_civic_election_id])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    else:
        # Only look at candidates for this year
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_year_list(
            year_list=[2024])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    already_retrieved = 0
    already_stored = 0
    try:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(we_vote_id__in=candidate_we_vote_id_list)
        queryset = queryset.exclude(facebook_photo_url_is_broken=True)
        queryset = queryset.exclude(facebook_photo_url_is_placeholder=True)
        queryset = queryset.exclude(facebook_url_is_broken=True)
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        # queryset = queryset.filter(facebook_url_is_broken=False)
        # queryset = queryset.order_by('candidate_name')

        # Exclude candidates without facebook_url
        queryset = queryset.exclude(Q(facebook_url__isnull=True) | Q(facebook_url__iexact=''))

        # facebook_photo_url_is_broken

        # Find candidates that don't have a photo (i.e. that are null or '')
        queryset = queryset. \
            filter(Q(facebook_profile_image_url_https__isnull=True) | Q(facebook_profile_image_url_https__exact=''))
        candidate_list_count = queryset.count()
        if positive_value_exists(limit):
            candidate_list = list(queryset[:limit])
        else:
            candidate_list = list(queryset)

        # Run Facebook account search and analysis on candidates with a linked or possible Facebook account
        for one_candidate in candidate_list:
            # Check to see if we have already tried to find their photo link from Facebook. We don't want to
            #  search Facebook more than once.
            # request_history_query = RemoteRequestHistory.objects.filter(
            #     candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
            #     kind_of_action=RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS)
            # request_history_list = list(request_history_query)
            request_history_list = []
            if not positive_value_exists(request_history_list):
                get_results = get_photo_url_from_facebook_graphapi(
                    incoming_object=one_candidate,
                    request=request,
                    remote_request_history_manager=remote_request_history_manager,
                    save_to_database=True,
                    add_messages=False)
                status += get_results['status']
            else:
                logger.info("Skipped URL: " + one_candidate.facebook_url)
                already_stored += 1
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    if positive_value_exists(already_stored):
        status += "ALREADY_STORED_TOTAL-(" + str(already_stored) + ") "
    if positive_value_exists(already_retrieved):
        status += "ALREADY_RETRIEVED_TOTAL-(" + str(already_retrieved) + ") "

    messages.add_message(request, messages.INFO, status)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )


@login_required
def get_and_save_facebook_photo_view(request):
    remote_request_history_manager = RemoteRequestHistoryManager()

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    we_vote_id = request.GET.get('candidate_we_vote_id', "")
    if positive_value_exists(we_vote_id):
        is_candidate = True
        reverse_path = 'candidate:candidate_edit_we_vote_id'
        msg_base = 'get_and_save_facebook_photo_view, Candidate '
        reverse_id = we_vote_id
    else:
        is_candidate = False
        we_vote_id = request.GET.get('organization_we_vote_id', "")
        reverse_path = 'organization:organization_position_list'
        msg_base = 'get_and_save_facebook_photo_view, Organization '
        reverse_id = ''
    if positive_value_exists(request.GET.get('reverse_path', "")):
        reverse_path = request.GET.get('reverse_path', "").replace('\'', '')

    if not positive_value_exists(we_vote_id):
        messages.add_message(request, messages.ERROR, msg_base + 'not specified')
        return HttpResponseRedirect(reverse(reverse_path, args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    try:
        query = CandidateCampaign.objects.all() if is_candidate else Organization.objects.all()

        query = query.filter(we_vote_id__iexact=we_vote_id)
        entity_list = list(query)
        one_entity = entity_list[0]

        # If the entity has a facebook_url, but no facebook_profile_image_url_https,
        # see if we already tried to scrape them
        if not positive_value_exists(one_entity.facebook_url if is_candidate else one_entity.organization_facebook):
            messages.add_message(request, messages.ERROR, msg_base + ', No facebook_url found.')
            return HttpResponseRedirect(
                reverse(reverse_path, args=(reverse_id,)) +
                '?google_civic_election_id=' + str(google_civic_election_id) +
                '&state_code=' + str(state_code) +
                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                '&page=' + str(page)
                )

        add_messages = True
        results = get_photo_url_from_facebook_graphapi(
            incoming_object=one_entity,
            request=request,
            remote_request_history_manager=remote_request_history_manager,
            save_to_database=True,
            add_messages=add_messages)

    except (CandidateCampaign.DoesNotExist, Organization.DoesNotExist):
        # This is fine, do nothing
        messages.add_message(request, messages.ERROR, msg_base + ' not found')
        return HttpResponseRedirect(reverse(reverse_path, args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    if not is_candidate:
        reverse_id = one_entity.id
    return HttpResponseRedirect(reverse(reverse_path, args=(reverse_id,)) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )
