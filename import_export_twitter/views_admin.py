# import_export_twitter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

import wevote_functions.admin
import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateManager
from image.controllers import delete_cached_images_for_voter, delete_cached_images_for_candidate, \
    delete_cached_images_for_organization, delete_stored_images_for_voter
from organization.controllers import update_social_media_statistics_in_other_tables
from organization.models import OrganizationManager
from politician.models import PoliticianManager
from representative.models import RepresentativeManager
from twitter.functions import retrieve_twitter_user_info
from volunteer_task.models import VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE, VolunteerTaskManager
from voter.models import voter_has_authority, VoterManager
from wevote_functions.functions import convert_to_int, positive_value_exists
from .controllers import delete_possible_twitter_handles, make_item_in_list_primary, \
    retrieve_possible_twitter_handles, retrieve_possible_twitter_handles_in_bulk
from .controllers import refresh_twitter_candidate_details, refresh_twitter_data_for_organizations, \
    refresh_twitter_organization_details, refresh_twitter_politician_details, refresh_twitter_representative_details, \
    scrape_social_media_from_one_site, refresh_twitter_candidate_details_for_election, \
    scrape_and_save_social_media_for_candidates_in_one_election, scrape_and_save_social_media_from_all_organizations, \
    transfer_candidate_twitter_handles_from_google_civic

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def delete_possible_twitter_handles_view(request, candidate_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)

    if not results['candidate_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_we_vote_id,)))

    candidate = results['candidate']

    results = delete_possible_twitter_handles(candidate)
    messages.add_message(request, messages.INFO, 'Possibilities deleted.')

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)))


@login_required
def retrieve_possible_twitter_handles_view(request, candidate_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)

    if not results['candidate_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id',
                                            args=(candidate_we_vote_id,)))

    candidate = results['candidate']

    results = retrieve_possible_twitter_handles(candidate)
    messages.add_message(request, messages.INFO, 'Number of possibilities found: ' + results['num_of_possibilities'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit_we_vote_id', args=(candidate_we_vote_id,)) +
                                '?show_all_twitter_search_results=1')


@login_required
def bulk_retrieve_possible_twitter_handles_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
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
                             'bulk_retrieve_possible_twitter_handles_view, LIMITING_VARIABLE_REQUIRED')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    results = retrieve_possible_twitter_handles_in_bulk(
        google_civic_election_id=google_civic_election_id,
        state_code=state_code,
        limit=limit)
    candidates_to_analyze = results['candidates_to_analyze']
    messages.add_message(request, messages.INFO,
                         'candidates_to_analyze:' + str(candidates_to_analyze))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )


@login_required
def delete_images_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    candidate_id = request.GET.get('candidate_id', 0)
    organization_id = request.GET.get('organization_id', 0)
    voter_id = request.GET.get('voter_id', 0)

    if positive_value_exists(candidate_id):
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate(candidate_id)
        if not results['candidate_found']:
            messages.add_message(request, messages.INFO, results['status'])
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                        '?google_civic_election_id=' + str(google_civic_election_id))
        candidate = results['candidate']
        delete_image_results = delete_cached_images_for_candidate(candidate)
    elif positive_value_exists(organization_id):
        organization_manager = OrganizationManager()
        results = organization_manager.retrieve_organization(organization_id)
        if not results['organization_found']:
            messages.add_message(request, messages.INFO, results['status'])
            return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)) +
                                        '?google_civic_election_id=' + str(google_civic_election_id))
        organization = results['organization']
        delete_image_results = delete_cached_images_for_organization(organization)
    elif positive_value_exists(voter_id):
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if not results['voter_found']:
            messages.add_message(request, messages.INFO, results['status'])
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                        '?google_civic_election_id=' + str(google_civic_election_id))
        voter = results['voter']
        delete_image_results = delete_cached_images_for_voter(voter)
        hard_delete_image_results = delete_stored_images_for_voter(voter)

    delete_image_count = delete_image_results['delete_image_count']
    not_deleted_image_count = delete_image_results['not_deleted_image_count']

    messages.add_message(request, messages.INFO,
                         "Images Deleted: {delete_image_count},"
                         .format(delete_image_count=delete_image_count))
    if positive_value_exists(candidate_id):
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
    elif positive_value_exists(organization_id):
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)) +
                                    '?google_civic_election_id=' + str(google_civic_election_id))
    else:
        return HttpResponseRedirect(reverse('voter:voter_list'))


@login_required
def refresh_twitter_candidate_details_view(request, candidate_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    twitter_handle_to_make_primary = request.GET.get('twitter_handle', '')

    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate(candidate_id)

    if not results['candidate_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    candidate = results['candidate']
    if positive_value_exists(twitter_handle_to_make_primary):
        results = make_item_in_list_primary(
            field_name_base='candidate_twitter_handle',
            representative=candidate,
            value_to_make_primary=twitter_handle_to_make_primary
        )
        if results['values_changed']:
            candidate = results['representative']
            candidate.save()

    results = refresh_twitter_candidate_details(candidate, use_cached_data_if_within_x_days=1)
    messages.add_message(request, messages.INFO, "REFRESH_TWITTER_CANDIDATE_DETAILS: " + results['status'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def refresh_twitter_organization_details_view(request, organization_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id)

    if not results['organization_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)) +
                                    '?google_civic_election_id=' + str(google_civic_election_id))

    organization = results['organization']

    results = refresh_twitter_organization_details(organization, use_cached_data_if_within_x_days=0)
    messages.add_message(request, messages.INFO, "REFRESH_TWITTER_ORGANIZATION_DETAILS: " + results['status'])

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)) +
                                '?google_civic_election_id=' + str(google_civic_election_id))


@login_required
def refresh_twitter_politician_details_view(request, politician_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    twitter_handle_to_make_primary = request.GET.get('twitter_handle', '')

    politician_manager = PoliticianManager()
    results = politician_manager.retrieve_politician(politician_id=politician_id, read_only=False)

    if not results['politician_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    politician = results['politician']
    if positive_value_exists(twitter_handle_to_make_primary):
        results = make_item_in_list_primary(
            field_name_base='politician_twitter_handle',
            representative=politician,
            value_to_make_primary=twitter_handle_to_make_primary
        )
        if results['values_changed']:
            politician = results['representative']
            politician.save()

    results = refresh_twitter_politician_details(politician, use_cached_data_if_within_x_days=0)
    messages.add_message(request, messages.INFO, "REFRESH_TWITTER_POLITICIAN_DETAILS: " + results['status'])

    return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))


@login_required
def refresh_twitter_representative_details_view(request, representative_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    twitter_handle_to_make_primary = request.GET.get('twitter_handle', '')

    representative_manager = RepresentativeManager()
    results = representative_manager.retrieve_representative(representative_id=representative_id)

    if not results['representative_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))

    representative = results['representative']
    if positive_value_exists(twitter_handle_to_make_primary):
        results = make_item_in_list_primary(
            field_name_base='representative_twitter_handle',
            representative=representative,
            value_to_make_primary=twitter_handle_to_make_primary
        )
        if results['values_changed']:
            representative = results['representative']
            representative.save()

    results = refresh_twitter_representative_details(representative, use_cached_data_if_within_x_days=0)
    messages.add_message(request, messages.INFO, "REFRESH_TWITTER_REPRESENTATIVE_DETAILS: " + results['status'])

    return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))


@login_required
def scrape_website_for_social_media_view(request, organization_id, force_retrieve=False):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    facebook_page = False
    twitter_handle = False

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id)

    if not results['organization_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_id,)))

    organization = results['organization']

    if not organization.organization_website:
        messages.add_message(request, messages.ERROR, "No organizational website found.")
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))

    if (not positive_value_exists(organization.organization_twitter_handle)) or \
            (not positive_value_exists(organization.organization_facebook)) or force_retrieve:
        scrape_results = scrape_social_media_from_one_site(organization.organization_website)

        if scrape_results['twitter_handle_found']:
            twitter_handle = scrape_results['twitter_handle']
            messages.add_message(request, messages.INFO, "Twitter handle found: " + twitter_handle)
        else:
            messages.add_message(request, messages.INFO, "No Twitter handle found: " + scrape_results['status'])

        if scrape_results['facebook_page_found']:
            facebook_page = scrape_results['facebook_page']
            messages.add_message(request, messages.INFO, "Facebook page found: " + facebook_page)

    save_results = organization_manager.update_organization_social_media(organization, twitter_handle,
                                                                         facebook_page)
    if save_results['success']:
        organization = save_results['organization']
    else:
        organization.organization_twitter_handle = twitter_handle  # Store it temporarily

    # ######################################
    # TODO DALE We should stop saving organization_twitter_handle without saving a TwitterLinkToOrganization
    if organization.organization_twitter_handle:
        twitter_user_id = 0
        from twitter.models import TwitterApiCounterManager
        twitter_api_counter_manager = TwitterApiCounterManager()
        results = retrieve_twitter_user_info(
            twitter_user_id,
            organization.organization_twitter_handle,
            twitter_api_counter_manager=twitter_api_counter_manager,
            parent='parent = scrape_website_for_social_media_view'
        )

        if results['success']:
            save_results = organization_manager.update_organization_twitter_details(
                organization, results['twitter_dict'])

            if save_results['success']:
                organization = save_results['organization']
                results = update_social_media_statistics_in_other_tables(organization)
    # ######################################

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))


@login_required
def refresh_twitter_data_for_organizations_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_state_code = request.GET.get('organization_state', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    first_retrieve_only = request.GET.get('first_retrieve_only', True)
    return_to_voter_guide_list = request.GET.get('return_to_voter_guide_list', False)

    results = refresh_twitter_data_for_organizations(
        state_code=organization_state_code,
        google_civic_election_id=google_civic_election_id,
        first_retrieve_only=first_retrieve_only)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        number_of_twitter_accounts_queried = results['number_of_twitter_accounts_queried']
        number_of_organizations_updated = results['number_of_organizations_updated']
        messages.add_message(request, messages.INFO,
                             "Twitter accounts queried: {number_of_twitter_accounts_queried}, "
                             "Endorsers updated: {number_of_organizations_updated}".format(
                                 number_of_twitter_accounts_queried=number_of_twitter_accounts_queried,
                                 number_of_organizations_updated=number_of_organizations_updated))

    if positive_value_exists(return_to_voter_guide_list):
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()) +
                                    '?google_civic_election_id=' + google_civic_election_id)
    else:
        return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                    '?organization_state=' + organization_state_code)


@login_required
def scrape_social_media_from_all_organizations_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_state_code = request.GET.get('organization_state', '')
    force_retrieve = request.GET.get('force_retrieve', False)  # Retrieve data again even if we already have data

    results = scrape_and_save_social_media_from_all_organizations(state_code=organization_state_code,
                                                                  force_retrieve=force_retrieve)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        twitter_handles_found = results['twitter_handles_found']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Twitter handles found: {twitter_handles_found}".format(
                                 twitter_handles_found=twitter_handles_found))

    return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                '?organization_state=' + organization_state_code)


@login_required
def scrape_social_media_for_candidates_in_one_election_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    results = scrape_and_save_social_media_for_candidates_in_one_election(
        google_civic_election_id=google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        twitter_handles_found = results['twitter_handles_found']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Twitter handles found: {twitter_handles_found}".format(
                                 twitter_handles_found=twitter_handles_found))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id))


@login_required
def refresh_twitter_candidate_details_for_election_view(request, election_id):
    status = ""
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(election_id)
    state_code = request.GET.get('state_code', '')

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

    results = refresh_twitter_candidate_details_for_election(google_civic_election_id=google_civic_election_id,
                                                             state_code=state_code)

    if len(results['twitter_handles_not_valid_list']) > 0:
        not_valid_list_status = \
            "TWITTER_HANDLES_NOT_VALID_LIST: " + str(results['twitter_handles_not_valid_list']) + " "
        messages.add_message(request, messages.ERROR, not_valid_list_status)
    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, results['status'])
        twitter_handles_added = results['twitter_handles_added']
        profiles_refreshed_with_twitter_data = results['profiles_refreshed_with_twitter_data']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Twitter handles added: {twitter_handles_added}, "
                             "Profiles refreshed with Twitter data: {profiles_refreshed_with_twitter_data}".format(
                                twitter_handles_added=twitter_handles_added,
                                profiles_refreshed_with_twitter_data=profiles_refreshed_with_twitter_data))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + election_id +
                                '&state_code=' + str(state_code))


@login_required
def transfer_candidate_twitter_handles_from_google_civic_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    results = transfer_candidate_twitter_handles_from_google_civic(
        google_civic_election_id=google_civic_election_id, state_code=state_code)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        twitter_handles_transferred = results['twitter_handles_transferred']
        messages.add_message(request, messages.INFO,
                             "Twitter handles transferred: {twitter_handles_transferred}".format(
                                 twitter_handles_transferred=twitter_handles_transferred))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code)
                                )
