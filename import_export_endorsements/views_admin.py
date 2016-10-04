# import_export_endorsements/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_endorsments, import_candidate_position, import_measure_position
from admin_tools.views import redirect_to_sign_in_page
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from organization.models import OrganizationManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def import_organization_endorsements(request, organization_id):
    authority_required = {'admin'}  # admin, verified_volunteer
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
    organization_results = retrieve_endorsments(organization)

    if organization_results['success']:
        endorsments_json = organization_results['endorsments']

        if 'candidate_positions' in endorsments_json:
            for position in endorsments_json['candidate_positions']:
                import_candidate_position(position)

        if 'measure_positions' in endorsments_json:
            for position in endorsments_json['measure_positions']:
                import_measure_position(position)

        messages.add_message(request, messages.SUCCESS, "Endorsments imported")
    else:
        messages.add_message(request, messages.ERROR, "Endorsments import failed: "+organization_results['status'])

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))
