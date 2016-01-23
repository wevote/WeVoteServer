# import_export_twitter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_twitter_user_info, scrape_social_media_from_one_site, \
    scrape_and_save_social_media_from_all_organizations
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from organization.models import OrganizationManager
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# @login_required()  # Commented out while we are developing login process()
def scrape_website_for_social_media_view(request, organization_id, force_retrieve=False):
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

    if (not positive_value_exists(organization.organization_twitter_handle)) or force_retrieve:
        scrape_results = scrape_social_media_from_one_site(organization.organization_website)

        if scrape_results['twitter_handle_found']:
            twitter_handle = scrape_results['twitter_handle']
            messages.add_message(request, messages.INFO, "Twitter handle found: " + twitter_handle)
        else:
            messages.add_message(request, messages.INFO, "No Twitter handle found: " + scrape_results['status'])

    organization_facebook = ''

    save_results = organization_manager.update_organization_social_media(organization, twitter_handle,
                                                                         organization_facebook)
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
                results = organization_manager.update_social_media_statistics_in_other_tables(organization)
    # ######################################

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))


# @login_required()  # Commented out while we are developing login process()
def scrape_social_media_from_all_organizations_view(request):
    results = scrape_and_save_social_media_from_all_organizations()

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        twitter_handles_found = results['twitter_handles_found']
        messages.add_message(request, messages.INFO, 
                             "Social media retrieved. Twitter handles found: {twitter_handles_found}".format(
                                 twitter_handles_found=twitter_handles_found))

    return HttpResponseRedirect(reverse('organization:organization_list', args=()))
