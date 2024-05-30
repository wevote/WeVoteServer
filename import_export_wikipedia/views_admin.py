# import_export_wikipedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaign, CandidateListManager
from import_export_ballotpedia.views_admin import MAXIMUM_BALLOTPEDIA_IMAGES_TO_RECEIVE_AT_ONCE
from wevote_settings.models import RemoteRequestHistoryManager
from .controllers import retrieve_all_organizations_logos_from_wikipedia, \
    retrieve_organization_logo_from_wikipedia_page, retrieve_wikipedia_page_from_wikipedia, \
    retrieve_candidate_images_from_wikipedia_page, get_photo_url_from_wikipedia
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from election.models import Election, ElectionManager
from import_export_batches.models import BatchSet, BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS


from organization.models import OrganizationManager
from polling_location.models import PollingLocation
from volunteer_task.models import VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE, VolunteerTaskManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_valid_state_code, positive_value_exists
from wevote_settings.models import RemoteRequestHistory, RETRIEVE_POSSIBLE_BALLOTPEDIA_PHOTOS


logger = wevote_functions.admin.get_logger(__name__)

MAXIMUM_WIKIPEDIA_IMAGES_TO_RECEIVE_AT_ONCE = 50


def bulk_retrieve_wikipedia_photos_view(request):
    import codecs
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
    limit = convert_to_int(request.GET.get('limit', MAXIMUM_WIKIPEDIA_IMAGES_TO_RECEIVE_AT_ONCE))
    print(google_civic_election_id, hide_candidate_tools, state_code, limit)
    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code) \
            and not positive_value_exists(limit):
        messages.add_message(request, messages.ERROR,
                             'bulk_retrieve_wikipedia_photos_view, LIMITING_VARIABLE_REQUIRED')
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

    candidate_list = []
    already_retrieved = 0
    already_stored = 0
    try:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(we_vote_id__in=candidate_we_vote_id_list)  # Candidates for election or this year
        # Don't include candidates that have wikipedia photos
        queryset = queryset.exclude(wikipedia_photo_does_not_exist=True)
        # queryset = queryset.filter(ballotpedia_photo_url_is_broken=False)
        # Don't include candidates that do not have wikipedia_url
        queryset = queryset. \
            exclude(Q(wikipedia_url__isnull=True) | Q(wikipedia_url__exact=''))
        # Only include candidates that don't have a photo
        queryset = queryset.filter(
            Q(wikipedia_photo_url__isnull=True) | Q(wikipedia_photo_url__iexact=''))
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        if positive_value_exists(limit):
            candidate_list = queryset[:limit]
        else:
            candidate_list = list(queryset)
        print(candidate_list)
        # Run search in wikipedia candidates
        for one_candidate in candidate_list:
            # Check to see if we have already tried to find their photo link from Wikipedia. We don't want to
            #  search Wikipedia more than once.
            # request_history_query = RemoteRequestHistory.objects.using('readonly').filter(
            #     candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
            #     kind_of_action=RETRIEVE_POSSIBLE_WIKIPEDIA_PHOTOS)
            # request_history_list = list(request_history_query)
            request_history_list = []
            if not positive_value_exists(len(request_history_list)):
                add_messages = False
                get_results = get_photo_url_from_wikipedia(
                    incoming_object=one_candidate,
                    request=request,
                    remote_request_history_manager=remote_request_history_manager,
                    save_to_database=True,
                    add_messages=add_messages)
                status += get_results['status']
            else:
                logger.info("Skipped URL: " + one_candidate.wikipedia_url)
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
def import_organization_logo_from_wikipedia_view(request, organization_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    logo_found = False

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id)

    if not results['organization_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)))

    organization = results['organization']

    # When looking up logos one at a time, we want to force a retrieve
    force_retrieve = True
    organization_results = retrieve_wikipedia_page_from_wikipedia(organization, force_retrieve)

    if organization_results['wikipedia_page_found']:
        wikipedia_page = organization_results['wikipedia_page']

        logo_results = retrieve_organization_logo_from_wikipedia_page(organization, wikipedia_page, force_retrieve)
        if logo_results['logo_found']:
            logo_found = True

        if positive_value_exists(force_retrieve):
            if 'image_options' in logo_results:
                for one_image in logo_results['image_options']:
                    link_to_image = "<a href='{one_image}' target='_blank'>{one_image}</a>".format(one_image=one_image)
                    messages.add_message(request, messages.INFO, link_to_image)

        if not logo_results['success']:
            messages.add_message(request, messages.ERROR, logo_results['status'])
    else:
        messages.add_message(request, messages.ERROR, "Wikipedia page not found. " + organization_results['status'])

    if logo_found:
        messages.add_message(request, messages.INFO, "Wikipedia logo retrieved.")
    else:
        messages.add_message(request, messages.ERROR, "Wikipedia logo not retrieved.")

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))


@login_required
def retrieve_all_organizations_logos_from_wikipedia_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_state_code = request.GET.get('organization_state', '')

    results = retrieve_all_organizations_logos_from_wikipedia(organization_state_code)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        logos_found = results['logos_found']
        messages.add_message(request, messages.INFO, "Wikipedia logos retrieved. "
                                                     "Logos found: {logos_found}".format(logos_found=logos_found))

    return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                "?organization_state=" + organization_state_code)
