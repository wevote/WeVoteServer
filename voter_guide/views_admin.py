# voter_guide/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoterGuideList, VoterGuideManager
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from election.models import Election
from organization.models import Organization, OrganizationManager
from position.models import PositionEntered
from wevote_functions.models import positive_value_exists


# @login_required()  # Commented out while we are developing login process()
def generate_voter_guides_view(request):

    voter_guide_stored_for_this_organization = []
    # voter_guide_stored_for_this_public_figure = []
    # voter_guide_stored_for_this_voter = []

    voter_guide_created_count = 0
    voter_guide_updated_count = 0

    # What elections do we want to generate voter_guides for?
    election_list = Election.objects.all()

    # Cycle through organizations
    organization_list = Organization.objects.all()
    for organization in organization_list:
        # Cycle through elections. Find out position count for this org for each election.
        # If > 0, then create a voter_guide entry
        if organization.id not in voter_guide_stored_for_this_organization:
            for election in election_list:
                # organization hasn't had voter guides stored yet.
                # Search for positions with this organization_id and google_civic_election_id
                google_civic_election_id = int(election.google_civic_election_id)  # Convert VarChar to Integer
                positions_count = PositionEntered.objects.filter(
                    organization_id=organization.id,
                    google_civic_election_id=google_civic_election_id).count()
                if positions_count > 0:
                    voter_guide_manager = VoterGuideManager()
                    results = voter_guide_manager.update_or_create_organization_voter_guide(
                        election.google_civic_election_id, organization.we_vote_id)
                    if results['success']:
                        if results['new_voter_guide_created']:
                            voter_guide_created_count += 1
                        else:
                            voter_guide_updated_count += 1

            voter_guide_stored_for_this_organization.append(organization.id)

    # Cycle through public figures
    # voter_guide_manager = VoterGuideManager()
    # voter_guide_manager.update_or_create_public_figure_voter_guide(1234, 'wv02')

    # Cycle through voters
    # voter_guide_manager = VoterGuideManager()
    # voter_guide_manager.update_or_create_voter_voter_guide(1234, 'wv03')

    messages.add_message(request, messages.INFO,
                         '{voter_guide_created_count} voter guides created, '
                         '{voter_guide_updated_count} updated.'.format(
                             voter_guide_created_count=voter_guide_created_count,
                             voter_guide_updated_count=voter_guide_updated_count,
                         ))
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def voter_guide_list_view(request):
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    voter_guide_list = []
    voter_guide_list_object = VoterGuideList()
    if positive_value_exists(google_civic_election_id):
        results = voter_guide_list_object.retrieve_voter_guides_for_election(
            google_civic_election_id=google_civic_election_id)

        if results['success']:
            voter_guide_list = results['voter_guide_list']
    else:
        results = voter_guide_list_object.retrieve_all_voter_guides()

        if results['success']:
            voter_guide_list = results['voter_guide_list']

    election_list = Election.objects.order_by('-election_day_text')

    messages_on_stage = get_messages(request)
    template_values = {
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage': messages_on_stage,
        'voter_guide_list': voter_guide_list,
    }
    return render(request, 'voter_guide/voter_guide_list.html', template_values)
