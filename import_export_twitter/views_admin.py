# import_export_twitter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import refresh_twitter_candidate_details, retrieve_twitter_data_for_all_organizations, \
    refresh_twitter_organization_details, \
    scrape_social_media_from_one_site, refresh_twitter_candidate_details_for_election, \
    scrape_and_save_social_media_for_candidates_in_one_election, scrape_and_save_social_media_from_all_organizations, \
    transfer_candidate_twitter_handles_from_google_civic
from .functions import retrieve_twitter_user_info
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaignManager
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from organization.controllers import update_social_media_statistics_in_other_tables
from organization.models import OrganizationManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def refresh_twitter_candidate_details_view(request, candidate_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign(candidate_id)

    if not results['candidate_campaign_found']:
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    candidate_campaign = results['candidate_campaign']

    results = refresh_twitter_candidate_details(candidate_campaign)

    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def refresh_twitter_organization_details_view(request, organization_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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

    results = refresh_twitter_organization_details(organization)

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)) +
                                '?google_civic_election_id=' + str(google_civic_election_id))


@login_required
def scrape_website_for_social_media_view(request, organization_id, force_retrieve=False):
    authority_required = {'admin'}  # admin, verified_volunteer
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
    if organization.organization_twitter_handle:
        results = retrieve_twitter_user_info(organization.organization_twitter_handle)

        if results['success']:
            save_results = organization_manager.update_organization_twitter_details(
                organization, results['twitter_json'])

            if save_results['success']:
                organization = save_results['organization']
                results = update_social_media_statistics_in_other_tables(organization)
    # ######################################

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))


@login_required
def retrieve_twitter_data_for_all_organizations_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_state_code = request.GET.get('organization_state', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    first_retrieve_only = request.GET.get('first_retrieve_only', True)

    results = retrieve_twitter_data_for_all_organizations(state_code=organization_state_code,
                                                          google_civic_election_id=google_civic_election_id,
                                                          first_retrieve_only=first_retrieve_only)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        number_of_twitter_accounts_queried = results['number_of_twitter_accounts_queried']
        number_of_organizations_updated = results['number_of_organizations_updated']
        messages.add_message(request, messages.INFO,
                             "Twitter accounts queried: {number_of_twitter_accounts_queried}, "
                             "Organizations updated: {number_of_organizations_updated}".format(
                                 number_of_twitter_accounts_queried=number_of_twitter_accounts_queried,
                                 number_of_organizations_updated=number_of_organizations_updated))

    return HttpResponseRedirect(reverse('organization:organization_list', args=()) +
                                '?organization_state=' + organization_state_code)


@login_required
def scrape_social_media_from_all_organizations_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
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
    authority_required = {'admin'}  # admin, verified_volunteer
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
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(election_id)

    results = refresh_twitter_candidate_details_for_election(google_civic_election_id=google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        twitter_handles_added = results['twitter_handles_added']
        profiles_refreshed_with_twitter_data = results['profiles_refreshed_with_twitter_data']
        messages.add_message(request, messages.INFO,
                             "Social media retrieved. Twitter handles added: {twitter_handles_added}, "
                             "Profiles refreshed with Twitter data: {profiles_refreshed_with_twitter_data}".format(
                                twitter_handles_added=twitter_handles_added,
                                profiles_refreshed_with_twitter_data=profiles_refreshed_with_twitter_data))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + election_id)


@login_required
def transfer_candidate_twitter_handles_from_google_civic_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    results = transfer_candidate_twitter_handles_from_google_civic(
        google_civic_election_id=google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        twitter_handles_transferred = results['twitter_handles_transferred']
        messages.add_message(request, messages.INFO,
                             "Twitter handles transferred: {twitter_handles_transferred}".format(
                                 twitter_handles_transferred=twitter_handles_transferred))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id))
