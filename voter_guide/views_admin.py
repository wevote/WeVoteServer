# voter_guide/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import voter_guides_import_from_master_server
from .models import VoterGuide, VoterGuideListManager, VoterGuideManager
from .serializers import VoterGuideSerializer
from admin_tools.views import redirect_to_sign_in_page
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from election.models import Election, ElectionManager, TIME_SPAN_LIST
from organization.models import Organization, OrganizationListManager
from organization.views_admin import organization_edit_process_view
from position.models import PositionEntered
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists, \
    STATE_CODE_MAP


# This page does not need to be protected.
class VoterGuidesSyncOutView(APIView):
    def get(self, request, format=None):
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

        voter_guide_list = VoterGuide.objects.all()
        if positive_value_exists(google_civic_election_id):
            voter_guide_list = voter_guide_list.filter(google_civic_election_id=google_civic_election_id)

        serializer = VoterGuideSerializer(voter_guide_list, many=True)
        return Response(serializer.data)


@login_required
def voter_guides_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = voter_guides_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Voter Guides import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Master data not imported (local duplicates found): '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def generate_voter_guides_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                        organization.we_vote_id, election.google_civic_election_id)
                    if results['success']:
                        if results['new_voter_guide_created']:
                            voter_guide_created_count += 1
                        else:
                            voter_guide_updated_count += 1

            for time_span in TIME_SPAN_LIST:
                # organization hasn't had voter guides stored yet.
                # Search for positions with this organization_id and time_span
                positions_count = PositionEntered.objects.filter(
                    organization_id=organization.id,
                    vote_smart_time_span=time_span).count()
                if positions_count > 0:
                    voter_guide_manager = VoterGuideManager()
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_time_span(
                        organization.we_vote_id, time_span)
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


@login_required
def generate_voter_guides_for_one_election_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR,
                             'Cannot generate voter guides for one election: google_civic_election_id missing')
        return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))

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
            # organization hasn't had voter guides stored yet in this run through.
            # Search for positions with this organization_id and google_civic_election_id
            positions_count = PositionEntered.objects.filter(
                organization_id=organization.id,
                google_civic_election_id=google_civic_election_id).count()
            if positions_count > 0:
                voter_guide_manager = VoterGuideManager()
                results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                    organization.we_vote_id, google_civic_election_id)
                if results['success']:
                    if results['new_voter_guide_created']:
                        voter_guide_created_count += 1
                    else:
                        voter_guide_updated_count += 1

            for time_span in TIME_SPAN_LIST:
                # organization hasn't had voter guides stored yet.
                # Search for positions with this organization_id and time_span
                positions_count = PositionEntered.objects.filter(
                    organization_id=organization.id,
                    vote_smart_time_span=time_span).count()
                if positions_count > 0:
                    voter_guide_manager = VoterGuideManager()
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_time_span(
                        organization.we_vote_id, time_span)
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


@login_required
def refresh_existing_voter_guides_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_guide_updated_count = 0

    # Cycle through existing voter_guides
    voter_guide_list_manager = VoterGuideListManager()
    voter_guide_manager = VoterGuideManager()
    results = voter_guide_list_manager.retrieve_all_voter_guides()
    if results['voter_guide_list_found']:
        voter_guide_list = results['voter_guide_list']
        for voter_guide in voter_guide_list:
            if positive_value_exists(voter_guide.organization_we_vote_id):
                if positive_value_exists(voter_guide.google_civic_election_id):
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                        voter_guide.organization_we_vote_id, voter_guide.google_civic_election_id)
                    if results['success']:
                        voter_guide_updated_count += 1
                elif positive_value_exists(voter_guide.vote_smart_time_span):
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_time_span(
                        voter_guide.organization_we_vote_id, voter_guide.vote_smart_time_span)
                    if results['success']:
                        voter_guide_updated_count += 1

    messages.add_message(request, messages.INFO,
                         '{voter_guide_updated_count} updated.'.format(
                             voter_guide_updated_count=voter_guide_updated_count,
                         ))
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))


@login_required
def voter_guide_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    voter_guide_list = []
    voter_guide_list_object = VoterGuideListManager()
    if positive_value_exists(google_civic_election_id):
        results = voter_guide_list_object.retrieve_voter_guides_for_election(
            google_civic_election_id=google_civic_election_id)

        if results['success']:
            voter_guide_list = results['voter_guide_list']
    else:
        order_by = "google_civic_election_id"
        results = voter_guide_list_object.retrieve_all_voter_guides(order_by)

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


@login_required
def voter_guide_search_view(request):
    """
    Before creating a voter guide, search for an existing organization
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # A positive value in google_civic_election_id means we want to create a voter guide for this org for this election
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'messages_on_stage': messages_on_stage,
        'upcoming_election_list':   upcoming_election_list,
        'google_civic_election_id': google_civic_election_id,
        'state_list':               sorted_state_list,
    }
    return render(request, 'voter_guide/voter_guide_search.html', template_values)


@login_required
def voter_guide_search_process_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    add_organization_button = request.POST.get('add_organization_button', False)
    if add_organization_button:
        return organization_edit_process_view(request)

    organization_name = request.POST.get('organization_name', '')
    organization_twitter_handle = request.POST.get('organization_twitter_handle', '')
    organization_facebook = request.POST.get('organization_facebook', '')
    organization_website = request.POST.get('organization_website', '')
    # state_served_code = request.POST.get('state_served_code', False)

    # Save this variable so we have it on the "Add New Position" page
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)

    # Filter incoming data
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)

    # Search for organizations that match
    organization_email = ''
    organization_list_manager = OrganizationListManager()
    results = organization_list_manager.organization_search_find_any_possibilities(
        organization_name, organization_twitter_handle, organization_website, organization_email,
        organization_facebook)

    if results['organizations_found']:
        organizations_list = results['organizations_list']
        organizations_count = len(organizations_list)

        messages.add_message(request, messages.INFO, 'We found {count} existing organization(s) '
                                                     'that might match.'.format(count=organizations_count))
    else:
        organizations_list = []
        messages.add_message(request, messages.INFO, 'No voter guides found with those search terms. '
                                                     'Please try again. ')

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':            messages_on_stage,
        'organizations_list':           organizations_list,
        'organization_name':            organization_name,
        'organization_twitter_handle':  organization_twitter_handle,
        'organization_facebook':        organization_facebook,
        'organization_website':         organization_website,
        'upcoming_election_list':       upcoming_election_list,
        'google_civic_election_id':     google_civic_election_id,
    }
    return render(request, 'voter_guide/voter_guide_search.html', template_values)
