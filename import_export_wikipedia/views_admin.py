# import_export_wikipedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_all_organizations_logos_from_wikipedia, \
    retrieve_organization_logo_from_wikipedia_page, retrieve_wikipedia_page_from_wikipedia
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from organization.models import OrganizationManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# @login_required()  # Commented out while we are developing login process()
def import_organization_logo_from_wikipedia_view(request, organization_id):
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


# @login_required()  # Commented out while we are developing login process()
def retrieve_all_organizations_logos_from_wikipedia_view(request):
    results = retrieve_all_organizations_logos_from_wikipedia()

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        logos_found = results['logos_found']
        messages.add_message(request, messages.INFO, "Wikipedia logos retrieved. "
                                                     "Logos found: {logos_found}".format(logos_found=logos_found))

    return HttpResponseRedirect(reverse('organization:organization_list', args=()))
