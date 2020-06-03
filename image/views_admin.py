# image/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import cache_all_kind_of_images_locally_for_all_organizations, \
    cache_all_kind_of_images_locally_for_all_voters, \
    cache_and_create_resized_images_for_organization, create_resized_images_for_all_organizations, \
    cache_and_create_resized_images_for_voter, create_resized_images_for_all_voters, \
    retrieve_all_images_for_one_candidate, retrieve_all_images_for_one_organization, retrieve_all_images_for_one_voter
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaignManager
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from organization.models import OrganizationManager
from voter.models import fetch_voter_id_from_voter_device_link, voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def cache_images_locally_for_all_organizations_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)

    cache_images_locally_for_all_organizations_results = cache_all_kind_of_images_locally_for_all_organizations()

    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'cache_images_for_all_organizations':   cache_images_locally_for_all_organizations_results,
    }
    return render(request, 'image/cache_images_locally_for_all_organizations.html', template_values)


@login_required
def cache_images_locally_for_all_voters_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    voter_id = convert_to_int(voter_id)

    messages_on_stage = get_messages(request)

    cache_images_locally_for_all_voters_results = cache_all_kind_of_images_locally_for_all_voters()

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'cache_images_for_all_voters':      cache_images_locally_for_all_voters_results,
        'voter_id_signed_in':               voter_id
    }
    return render(request, 'image/cache_images_locally_for_all_voters.html', template_values)


@login_required
def create_resized_images_for_all_organizations_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    create_resized_images_for_organization_results = create_resized_images_for_all_organizations()
    template_values = {
        'messages_on_stage':                        messages_on_stage,
        'create_resized_images_for_organization':   create_resized_images_for_organization_results,
        'organization_we_vote_id':                  ""
    }
    return render(request, 'image/create_resized_images_for_organization.html', template_values)


@login_required
def create_resized_images_for_organization_view(request, organization_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    if positive_value_exists(organization_we_vote_id):
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['success']:
            organization = organization_results['organization']
        create_resized_images_for_organization_results = cache_and_create_resized_images_for_organization(
            organization_we_vote_id)
    else:
        create_resized_images_for_organization_results = {}
    template_values = {
        'messages_on_stage':                        messages_on_stage,
        'create_resized_images_for_organization':   create_resized_images_for_organization_results,
        'organization_we_vote_id':                  organization_we_vote_id,
        'organization':                             organization
    }
    return render(request, 'image/create_resized_images_for_organization.html', template_values)


@login_required
def create_resized_images_for_voters_view(request, voter_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_id = convert_to_int(voter_id)
    messages_on_stage = get_messages(request)
    if positive_value_exists(voter_id):
        create_resized_images_for_voters_results = cache_and_create_resized_images_for_voter(voter_id)
    else:
        create_resized_images_for_voters_results = create_resized_images_for_all_voters()
    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'create_resized_images_for_voters':     create_resized_images_for_voters_results,
        'voter_id_signed_in':                   voter_id
    }
    return render(request, 'image/create_resized_images_for_voters.html', template_values)


@login_required
def images_for_one_voter_view(request, voter_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_id = convert_to_int(voter_id)
    messages_on_stage = get_messages(request)
    we_vote_image_list = retrieve_all_images_for_one_voter(voter_id)
    template_values = {
        'messages_on_stage':    messages_on_stage,
        'images_for_one_voter': we_vote_image_list,
        'voter_id':             voter_id
    }
    return render(request, 'image/images_for_one_voter.html', template_values)


@login_required
def images_for_one_candidate_view(request, candidate_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if positive_value_exists(candidate_we_vote_id):
        candidate_campaign_manager = CandidateCampaignManager()
        candidate_campaign_results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
            candidate_we_vote_id)
        if candidate_campaign_results['success']:
            candidate_campaign = candidate_campaign_results['candidate_campaign']

    messages_on_stage = get_messages(request)
    we_vote_image_list = retrieve_all_images_for_one_candidate(candidate_we_vote_id)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'images_for_one_candidate': we_vote_image_list,
        'candidate_we_vote_id':     candidate_we_vote_id,
        'candidate_campaign':       candidate_campaign
    }
    return render(request, 'image/images_for_one_candidate.html', template_values)


@login_required
def images_for_one_organization_view(request, organization_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if positive_value_exists(organization_we_vote_id):
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['success']:
            organization = organization_results['organization']

    messages_on_stage = get_messages(request)
    we_vote_image_list = retrieve_all_images_for_one_organization(organization_we_vote_id)
    template_values = {
        'messages_on_stage':            messages_on_stage,
        'images_for_one_organization':  we_vote_image_list,
        'organization_we_vote_id':      organization_we_vote_id,
        'organization':                 organization
    }
    return render(request, 'image/images_for_one_organization.html', template_values)
