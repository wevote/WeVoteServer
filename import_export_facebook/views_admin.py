# import_export_facebook/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import get_facebook_photo_url_from_graphapi
from admin_tools.views import redirect_to_sign_in_page
from candidate.controllers import FACEBOOK, save_image_to_candidate_table
from candidate.models import CandidateCampaign, CandidateCampaignListManager
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
import wevote_functions.admin
from wevote_settings.models import RemoteRequestHistory, RemoteRequestHistoryManager, RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS


logger = wevote_functions.admin.get_logger(__name__)


def get_one_picture_from_facebook_graphapi(one_candidate, request, remote_request_history_manager, add_messages):
    status = ""
    success = True
    results = get_facebook_photo_url_from_graphapi(one_candidate.facebook_url)
    if results.get('success'):
        photo_url = results.get('photo_url')
        link_is_broken = results.get('http_response_code') == 404
        is_placeholder_photo = not photo_url.startswith('https://scontent')
        if link_is_broken:
            success = False
            # status += results['status']
            status += "IS_BROKEN_URL-(" + str(photo_url) + " / " + str(one_candidate.facebook_url) + ") "
            logger.info("Broken URL: " + photo_url)
            if add_messages:
                messages.add_message(
                    request, messages.INFO,
                    'Failed to retrieve Facebook picture:  The Facebook URL is broken, or is not a '
                    'legal Facebook alias')
        elif is_placeholder_photo:
            success = False
            # status += results['status']
            status += "IS_PLACEHOLDER_PHOTO "
            logger.info("Placeholder: " + photo_url)
            if add_messages:
                messages.add_message(
                    request, messages.INFO,
                    'Failed to retrieve Facebook picture:  The Facebook URL is for placeholder image.')
            # Create a record denoting that we have retrieved from Facebook for this candidate
            save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS, one_candidate.google_civic_election_id,
                one_candidate.we_vote_id, None, 1, "CANDIDATE_FACEBOOK_URL_IS_PLACEHOLDER:" + photo_url)
        else:
            logger.info("Queried URL: " + one_candidate.facebook_url + " ==> " + photo_url)
            if add_messages:
                messages.add_message(request, messages.INFO, 'Facebook photo retrieved.')
            results = save_image_to_candidate_table(
                one_candidate, photo_url, one_candidate.facebook_url, link_is_broken, FACEBOOK)
            if not positive_value_exists(results['success']):
                success = False
                status += results['status']
                status += "SAVE_IMAGE_TO_CANDIDATE_TABLE_FAILED "
            else:
                status += "SAVED_FB_IMAGE "
                # Create a record denoting that we have retrieved from Facebook for this candidate
                save_results_history = remote_request_history_manager.create_remote_request_history_entry(
                    RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS, one_candidate.google_civic_election_id,
                    one_candidate.we_vote_id, None, 1, "CANDIDATE_FACEBOOK_URL_PARSED_HTTP:" +
                                                       str(link_is_broken) + ", " + one_candidate.facebook_url)
    else:
        success = False
        status += results['status']
        status += "GET_FACEBOOK_FAILED "

        if add_messages:
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

    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    candidate_list_manager = CandidateCampaignListManager()
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

    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', "")

    if not positive_value_exists(candidate_we_vote_id):
        messages.add_message(request, messages.ERROR,
                             'get_and_save_facebook_photo_view, Candidate not specified')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    try:
        candidate_query = CandidateCampaign.objects.all()
        candidate_query = candidate_query.filter(we_vote_id__iexact=candidate_we_vote_id)
        candidate_list = list(candidate_query)
        one_candidate = candidate_list[0]

        # If the candidate has a facebook_url, but no facebook_profile_image_url_https,
        # see if we already tried to scrape them
        if not positive_value_exists(one_candidate.facebook_url):
            messages.add_message(request, messages.ERROR,
                                 'get_and_save_facebook_photo_view, No facebook_url found.')
            return HttpResponseRedirect(
                reverse('candidate:candidate_edit_we_vote_id', args=(one_candidate.we_vote_id,)) +
                '?google_civic_election_id=' + str(google_civic_election_id) +
                '&state_code=' + str(state_code) +
                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                '&page=' + str(page)
                )

        add_messages = True
        get_one_picture_from_facebook_graphapi(one_candidate, request, remote_request_history_manager, add_messages)

    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        messages.add_message(request, messages.ERROR,
                             'get_and_save_facebook_photo_view, Candidate not found.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(one_candidate.we_vote_id,)) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )
