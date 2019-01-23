# import_export_endorsements/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_endorsements, import_candidate_position, import_measure_position
from admin_tools.views import redirect_to_sign_in_page
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from organization.models import OrganizationManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def import_organization_endorsements(request, organization_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
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
    results = retrieve_endorsements(organization)
    batch_set_id = 0
    google_civic_election_id=0
    election_name=''

    if results['success']:
        messages.add_message(request, messages.INFO, 'Import batch for {election_name} election saved.'
                                                     ''.format(election_name=results['election_name']))
    else:
        messages.add_message(request, messages.ERROR, 'Import batch for organization endorsements failed: {status}.'
                                                      ''.format(status=results['status']))

    return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                "?google_civic_election_id=" + str(results['google_civic_election_id']) +
                                "&batch_set_id=" + str(results['batch_set_id']))
