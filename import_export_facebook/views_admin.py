# import_export_facebook/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from candidate.controllers import FACEBOOK, save_image_to_candidate_table
from candidate.models import CandidateCampaign, CandidateListManager
from organization.controllers import save_image_to_organization_table
from organization.models import Organization
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import RemoteRequestHistory, RemoteRequestHistoryManager, RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS
from .controllers import get_facebook_photo_url_from_graphapi

logger = wevote_functions.admin.get_logger(__name__)


def get_one_picture_from_facebook_graphapi(one_entity, request, remote_request_history_manager, add_messages):
    status = ""
    success = True

    we_vote_id = one_entity.we_vote_id
    if hasattr(one_entity, 'facebook_url'):
        facebook_url = one_entity.facebook_url
        google_civic_election_id = one_entity.google_civic_election_id
        is_candidate = True
    else:
        facebook_url = one_entity.organization_facebook
        google_civic_election_id = ''
        is_candidate = False

    results = get_facebook_photo_url_from_graphapi(facebook_url)
    if results.get('success'):
        photo_url = results.get('photo_url')
        # link_is_broken = results.get('http_response_code') == 404
        is_placeholder_photo = results.get('is_silhouette')
        if is_placeholder_photo:
            success = False
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
                    RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS, google_civic_election_id,
                    we_vote_id, None, 1, "CANDIDATE_FACEBOOK_URL_IS_PLACEHOLDER_SILHOUETTE:" + photo_url)
        else:
            # Success!
            logger.info("Queried URL: " + facebook_url + " ==> " + photo_url)
            if add_messages:
                messages.add_message(request, messages.INFO, 'Facebook photo retrieved.')
            if is_candidate:
                results = save_image_to_candidate_table(
                    one_entity, photo_url, facebook_url, False, FACEBOOK)
            else:
                results = save_image_to_organization_table(
                    one_entity, photo_url, facebook_url, False, FACEBOOK)

            if not positive_value_exists(results['success']):
                success = False
                status += results['status']
                status += "SAVE_IMAGE_TO_CANDIDATE_TABLE_FAILED "
            else:
                status += "SAVED_FB_IMAGE "
                # Create a record denoting that we have retrieved from Facebook for this candidate

                if is_candidate:
                    save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                        RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS, google_civic_election_id,
                        we_vote_id, None, 1, "CANDIDATE_FACEBOOK_URL_PARSED_HTTP:" + facebook_url)
    else:
        success = False
        status += results['status']
        status += "GET_FACEBOOK_FAILED "

        if add_messages:
            if len(results.get('clean_message')) > 0:
                messages.add_message(request, messages.ERROR, results.get('clean_message'))
            else:
                messages.add_message(request, messages.ERROR, 'Facebook photo NOT retrieved (2). status: ' +
                                 results.get('status'))

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
    number_of_candidates_to_search = 75
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
    limit = convert_to_int(request.GET.get('show_all', 0))

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
    candidate_list_manager = CandidateListManager()
    already_retrieved = 0
    already_stored = 0
    try:
        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=[google_civic_election_id])
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']
            candidate_list = candidate_list.filter(we_vote_id__in=candidate_we_vote_id_list)
        if positive_value_exists(state_code):
            candidate_list = candidate_list.filter(state_code__iexact=state_code)
        candidate_list = candidate_list.order_by('candidate_name')
        if positive_value_exists(limit):
            candidate_list = candidate_list[:limit]
        candidate_list_count = candidate_list.count()

        # Run Facebook account search and analysis on candidates with a linked or possible Facebook account
        current_candidate_index = 0
        while positive_value_exists(number_of_candidates_to_search) \
                and (current_candidate_index < candidate_list_count):
            one_candidate = candidate_list[current_candidate_index]
            # If the candidate has a facebook_url, but no facebook_profile_image_url_https,
            # see if we already tried to scrape them
            if positive_value_exists(one_candidate.facebook_url) \
                    and not positive_value_exists(one_candidate.facebook_profile_image_url_https):
                # Check to see if we have already tried to find their photo link from Facebook. We don't want to
                #  search Facebook more than once.
                request_history_query = RemoteRequestHistory.objects.filter(
                    candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
                    kind_of_action=RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS)
                request_history_list = list(request_history_query)

                if not positive_value_exists(request_history_list):
                    add_messages = False
                    get_results = get_one_picture_from_facebook_graphapi(
                        one_candidate, request, remote_request_history_manager, add_messages)
                    status += get_results['status']
                    number_of_candidates_to_search -= 1
                else:
                    logger.info("Skipped URL: " + one_candidate.facebook_url)
                    already_stored += 1
            else:
                already_stored += 1

            current_candidate_index += 1
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
        get_one_picture_from_facebook_graphapi(one_entity, request, remote_request_history_manager, add_messages)

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
