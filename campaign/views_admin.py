# campaign/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import localtime, now
from django.views.decorators.csrf import csrf_protect

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import datetime, timedelta
from election.models import ElectionManager
from organization.models import Organization, OrganizationManager
from politician.models import PoliticianManager
from stripe_donations.models import StripeManager
from voter.models import voter_has_authority, VoterManager
from wevote_functions.functions import convert_state_code_to_state_text, convert_to_int, \
    positive_value_exists, STATE_CODE_MAP
from wevote_functions.functions_date import generate_date_as_integer
from .controllers import create_campaignx_supporters_from_positions, figure_out_campaignx_conflict_values, \
    refresh_campaignx_supporters_count_in_all_children, merge_these_two_campaignx_entries
from .models import CampaignX, CampaignXManager, CampaignXOwner, CampaignXPolitician, CampaignXSupporter, \
    CAMPAIGNX_UNIQUE_IDENTIFIERS, FINAL_ELECTION_DATE_COOL_DOWN, SUPPORTERS_COUNT_MINIMUM_FOR_LISTING

logger = wevote_functions.admin.get_logger(__name__)
CAMPAIGNS_ROOT_URL = get_environment_variable("CAMPAIGNS_ROOT_URL", no_exception=True)
if not positive_value_exists(CAMPAIGNS_ROOT_URL):
    CAMPAIGNS_ROOT_URL = "https://campaigns.wevote.us"
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")


@csrf_protect
@login_required
def campaign_delete_process_view(request):
    """
    Delete a campaign
    :param request:
    :return:
    """
    status = ""
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', 0)
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this Campaign. '
                             'Please check the checkbox to confirm you want to delete this organization.')
        return HttpResponseRedirect(reverse('campaign:campaignx_edit', args=(campaignx_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    campaign_manager = CampaignXManager()
    results = campaign_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)
    if results['campaignx_found']:
        campaignx = results['campaignx']

        campaignx.delete()
        messages.add_message(request, messages.INFO, 'CampaignX deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'CampaignX not found.')

    return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()))


@csrf_protect
@login_required
def campaign_edit_owners_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', None)
    campaignx_owner_visible_to_public = \
        positive_value_exists(request.POST.get('campaignx_owner_visible_to_public', False))
    campaignx_owner_feature_this_profile_image = \
        positive_value_exists(request.POST.get('campaignx_owner_feature_this_profile_image', False))
    campaignx_owner_organization_we_vote_id_filter = request.POST.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.POST.get('campaignx_search', '')
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    incoming_campaignx_owner_we_vote_id = request.POST.get('incoming_campaignx_owner_we_vote_id', None)
    if positive_value_exists(incoming_campaignx_owner_we_vote_id):
        incoming_campaignx_owner_we_vote_id = incoming_campaignx_owner_we_vote_id.strip()
    state_code = request.POST.get('state_code', '')

    organization_manager = OrganizationManager()
    voter_manager = VoterManager()
    campaignx_owner_organization_we_vote_id = ''
    campaignx_owner_voter_we_vote_id = ''

    if positive_value_exists(incoming_campaignx_owner_we_vote_id):
        # We allow either organization_we_vote_id or voter_we_vote_id
        if 'org' in incoming_campaignx_owner_we_vote_id:
            campaignx_owner_organization_we_vote_id = incoming_campaignx_owner_we_vote_id
            campaignx_owner_voter_we_vote_id = \
                voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                    campaignx_owner_organization_we_vote_id)
        elif 'voter' in incoming_campaignx_owner_we_vote_id:
            campaignx_owner_voter_we_vote_id = incoming_campaignx_owner_we_vote_id
            campaignx_owner_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(campaignx_owner_voter_we_vote_id)

    # Create new CampaignXOwner
    if positive_value_exists(campaignx_owner_organization_we_vote_id) or \
            positive_value_exists(campaignx_owner_voter_we_vote_id):
        do_not_create = False
        link_already_exists = False
        status = ""
        # Does it already exist?
        try:
            if positive_value_exists(campaignx_owner_organization_we_vote_id):
                CampaignXOwner.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    organization_we_vote_id=campaignx_owner_organization_we_vote_id)
                link_already_exists = True
            elif positive_value_exists(campaignx_owner_voter_we_vote_id):
                CampaignXOwner.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    voter_we_vote_id=campaignx_owner_voter_we_vote_id)
                link_already_exists = True
        except CampaignXOwner.DoesNotExist:
            link_already_exists = False
        except Exception as e:
            do_not_create = True
            messages.add_message(request, messages.ERROR, 'CampaignXOwner already exists.')
            status += "ADD_CAMPAIGN_OWNER_ALREADY_EXISTS " + str(e) + " "

        if not do_not_create and not link_already_exists:
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(campaignx_owner_organization_we_vote_id)
            if organization_results['organization_found']:
                organization_name = organization_results['organization'].organization_name
                we_vote_hosted_profile_image_url_medium = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_medium
                we_vote_hosted_profile_image_url_tiny = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_tiny
            else:
                organization_name = ''
                we_vote_hosted_profile_image_url_medium = ''
                we_vote_hosted_profile_image_url_tiny = ''
            # Now create new link
            try:
                # Create the CampaignXOwner
                CampaignXOwner.objects.create(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    organization_name=organization_name,
                    organization_we_vote_id=campaignx_owner_organization_we_vote_id,
                    feature_this_profile_image=campaignx_owner_feature_this_profile_image,
                    voter_we_vote_id=campaignx_owner_voter_we_vote_id,
                    we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    visible_to_public=campaignx_owner_visible_to_public)

                messages.add_message(request, messages.INFO, 'New CampaignXOwner created.')
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     'Could not create CampaignXOwner.'
                                     ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or editing a CampaignXOwner
    campaignx_manager = CampaignXManager()
    campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
        campaignx_we_vote_id_list=[campaignx_we_vote_id],
        viewer_is_owner=True
    )
    for campaignx_owner in campaignx_owner_list:
        if positive_value_exists(campaignx_owner.campaignx_we_vote_id):
            delete_variable_name = "delete_campaignx_owner_" + str(campaignx_owner.id)
            delete_campaignx_owner = positive_value_exists(request.POST.get(delete_variable_name, False))
            if positive_value_exists(delete_campaignx_owner):
                campaignx_owner.delete()
                messages.add_message(request, messages.INFO, 'Deleted CampaignXOwner.')
            else:
                owner_changed = False
                visible_to_public_exists_variable_name = \
                    "campaignx_owner_visible_to_public_" + str(campaignx_owner.id) + "_exists"
                campaignx_owner_visible_to_public_exists = \
                    request.POST.get(visible_to_public_exists_variable_name, None)
                visible_to_public_variable_name = "campaignx_owner_visible_to_public_" + str(campaignx_owner.id)
                campaignx_owner_visible_to_public = \
                    positive_value_exists(request.POST.get(visible_to_public_variable_name, False))
                feature_this_profile_image_variable_name = \
                    "campaignx_owner_feature_this_profile_image_" + str(campaignx_owner.id)
                campaignx_owner_feature_this_profile_image = \
                    positive_value_exists(request.POST.get(feature_this_profile_image_variable_name, False))
                if campaignx_owner_visible_to_public_exists is not None:
                    campaignx_owner.feature_this_profile_image = campaignx_owner_feature_this_profile_image
                    campaignx_owner.visible_to_public = campaignx_owner_visible_to_public
                    owner_changed = True

                # Now refresh organization cached data
                organization_results = \
                    organization_manager.retrieve_organization_from_we_vote_id(campaignx_owner.organization_we_vote_id)
                if organization_results['organization_found']:
                    organization_name = organization_results['organization'].organization_name
                    if positive_value_exists(organization_name) and \
                            campaignx_owner.organization_name != organization_name:
                        campaignx_owner.organization_name = organization_name
                        owner_changed = True
                    we_vote_hosted_profile_image_url_medium = \
                        organization_results['organization'].we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium) and \
                            campaignx_owner.we_vote_hosted_profile_image_url_medium != \
                            we_vote_hosted_profile_image_url_medium:
                        campaignx_owner.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                        owner_changed = True
                    we_vote_hosted_profile_image_url_tiny = \
                        organization_results['organization'].we_vote_hosted_profile_image_url_tiny
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny) and \
                            campaignx_owner.we_vote_hosted_profile_image_url_tiny != \
                            we_vote_hosted_profile_image_url_tiny:
                        campaignx_owner.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                        owner_changed = True
                if not positive_value_exists(campaignx_owner.voter_we_vote_id):
                    voter_we_vote_id = voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                        campaignx_owner.organization_we_vote_id)
                    if positive_value_exists(voter_we_vote_id):
                        campaignx_owner.voter_we_vote_id = voter_we_vote_id
                        owner_changed = True
                if owner_changed:
                    campaignx_owner.save()

    return HttpResponseRedirect(reverse('campaign:campaignx_edit_owners', args=(campaignx_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&campaignx_owner_organization_we_vote_id=" +
                                str(campaignx_owner_organization_we_vote_id_filter) +
                                "&campaignx_search=" + str(campaignx_search) +
                                "&state_code=" + str(state_code))


@login_required
def campaign_edit_owners_view(request, campaignx_id=0, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.GET.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.GET.get('campaignx_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    campaignx_id = convert_to_int(campaignx_id)
    campaignx_manager = CampaignXManager()
    campaignx = None
    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)

    if results['campaignx_found']:
        campaignx = results['campaignx']

    campaignx_owner_list_modified = []
    campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
        campaignx_we_vote_id_list=[campaignx_we_vote_id],
        viewer_is_owner=True
    )

    # voter_manager = VoterManager()
    for campaignx_owner in campaignx_owner_list:
        campaignx_owner_list_modified.append(campaignx_owner)

    template_values = {
        'campaignx':                                campaignx,
        'campaignx_owner_list':                     campaignx_owner_list_modified,
        'campaignx_owner_organization_we_vote_id':  campaignx_owner_organization_we_vote_id,
        'campaignx_search':                         campaignx_search,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'state_code':                               state_code,
    }
    return render(request, 'campaign/campaignx_edit_owners.html', template_values)


@csrf_protect
@login_required
def campaign_edit_politicians_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.POST.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.POST.get('campaignx_search', '')
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', None)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', None)
    if positive_value_exists(politician_we_vote_id):
        politician_we_vote_id = politician_we_vote_id.strip()
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    state_code = request.POST.get('state_code', '')

    # Create new CampaignXPolitician
    if positive_value_exists(politician_we_vote_id):
        if 'pol' not in politician_we_vote_id:
            messages.add_message(request, messages.ERROR, 'Valid PoliticianWeVoteId missing.')
        else:
            do_not_create = False
            link_already_exists = False
            status = ""
            # Does it already exist?
            try:
                CampaignXPolitician.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    politician_we_vote_id=politician_we_vote_id)
                link_already_exists = True
            except CampaignXPolitician.DoesNotExist:
                link_already_exists = False
            except Exception as e:
                do_not_create = True
                messages.add_message(request, messages.ERROR, 'Link already exists.')
                status += "ADD_CAMPAIGN_POLITICIAN_ALREADY_EXISTS " + str(e) + " "

            if not do_not_create and not link_already_exists:
                politician_manager = PoliticianManager()
                politician_results = \
                    politician_manager.retrieve_politician_from_we_vote_id(politician_we_vote_id)
                if politician_results['politician_found']:
                    politician_name = politician_results['politician'].politician_name
                    state_code = politician_results['politician'].state_code
                    we_vote_hosted_profile_image_url_large = \
                        politician_results['politician'].we_vote_hosted_profile_image_url_large
                    we_vote_hosted_profile_image_url_medium = \
                        politician_results['politician'].we_vote_hosted_profile_image_url_medium
                    we_vote_hosted_profile_image_url_tiny = \
                        politician_results['politician'].we_vote_hosted_profile_image_url_tiny
                else:
                    politician_name = ''
                    we_vote_hosted_profile_image_url_large = ''
                    we_vote_hosted_profile_image_url_medium = ''
                    we_vote_hosted_profile_image_url_tiny = ''
                voter_we_vote_id = ''
                try:
                    # Create the CampaignXPolitician
                    CampaignXPolitician.objects.create(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        politician_name=politician_name,
                        politician_we_vote_id=politician_we_vote_id,
                        state_code=state_code,
                        we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    )

                    messages.add_message(request, messages.INFO, 'New CampaignXPolitician created.')
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         'Could not create CampaignXPolitician.'
                                         ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or editing a CampaignXPolitician
    campaignx_manager = CampaignXManager()
    campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
        campaignx_we_vote_id=campaignx_we_vote_id,
        read_only=False,
    )
    for campaignx_politician in campaignx_politician_list:
        if positive_value_exists(campaignx_politician.campaignx_we_vote_id):
            delete_variable_name = "delete_campaignx_politician_" + str(campaignx_politician.id)
            delete_campaignx_politician = positive_value_exists(request.POST.get(delete_variable_name, False))
            if positive_value_exists(delete_campaignx_politician):
                campaignx_politician.delete()
                messages.add_message(request, messages.INFO, 'Deleted CampaignXPolitician.')
            else:
                pass

    return HttpResponseRedirect(reverse('campaign:campaignx_edit_politicians', args=(campaignx_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&campaignx_owner_organization_we_vote_id=" +
                                str(campaignx_owner_organization_we_vote_id) +
                                "&campaignx_search=" + str(campaignx_search) +
                                "&state_code=" + str(state_code))


@login_required
def campaign_edit_politicians_view(request, campaignx_id=0, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.GET.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.GET.get('campaignx_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    campaignx_id = convert_to_int(campaignx_id)
    campaignx_manager = CampaignXManager()
    campaignx = None
    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)

    if results['campaignx_found']:
        campaignx = results['campaignx']

    campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
        campaignx_we_vote_id=campaignx_we_vote_id,
    )

    template_values = {
        'campaignx':                                campaignx,
        'campaignx_owner_organization_we_vote_id':  campaignx_owner_organization_we_vote_id,
        'campaignx_search':                         campaignx_search,
        'campaignx_politician_list':                campaignx_politician_list,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'state_code':                               state_code,
    }
    return render(request, 'campaign/campaignx_edit_politicians.html', template_values)


@csrf_protect
@login_required
def campaign_edit_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_id = convert_to_int(request.POST.get('campaignx_id', 0))
    campaignx_owner_organization_we_vote_id = request.POST.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.POST.get('campaignx_search', '')
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', None)
    campaign_title = request.POST.get('campaign_title', None)
    campaign_description = request.POST.get('campaign_description', None)
    final_election_date_as_integer = convert_to_int(request.POST.get('final_election_date_as_integer', 0))
    final_election_date_as_integer = None if final_election_date_as_integer == 0 else final_election_date_as_integer
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    take_out_of_draft_mode = request.POST.get('take_out_of_draft_mode', None)
    is_blocked_by_we_vote = request.POST.get('is_blocked_by_we_vote', False)
    is_blocked_by_we_vote_reason = request.POST.get('is_blocked_by_we_vote_reason', None)
    is_in_team_review_mode = request.POST.get('is_in_team_review_mode', False)
    is_not_promoted_by_we_vote = request.POST.get('is_not_promoted_by_we_vote', False)
    is_not_promoted_by_we_vote_reason = request.POST.get('is_not_promoted_by_we_vote_reason', None)
    is_ok_to_promote_on_we_vote = request.POST.get('is_ok_to_promote_on_we_vote', False)
    ocd_id_state_mismatch_resolved = request.POST.get('ocd_id_state_mismatch_resolved', False)
    politician_starter_list_serialized = request.POST.get('politician_starter_list_serialized', None)
    seo_friendly_path = request.POST.get('seo_friendly_path', None)
    state_code = request.POST.get('state_code', None)
    supporters_count_minimum_ignored = request.POST.get('supporters_count_minimum_ignored', False)

    # Check to see if this campaign is already being used anywhere
    campaignx = None
    campaignx_found = False
    campaignx_manager = CampaignXManager()
    politician_manager = PoliticianManager()
    status = ""
    try:
        if positive_value_exists(campaignx_id):
            campaignx = CampaignX.objects.get(id=campaignx_id)
            campaignx_we_vote_id = campaignx.we_vote_id
        else:
            campaignx = CampaignX.objects.get(we_vote_id=campaignx_we_vote_id)
        campaignx_found = True
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'CampaignX can only be edited for existing organization.')
        status += "EDIT_CAMPAIGN_PROCESS_NOT_FOUND " + str(e) + " "

    push_seo_friendly_path_changes = False
    try:
        if campaignx_found:
            # Update
            if campaign_title is not None:
                campaignx.campaign_title = campaign_title
            if campaign_description is not None:
                campaignx.campaign_description = campaign_description.strip()
            if take_out_of_draft_mode is not None and positive_value_exists(take_out_of_draft_mode):
                # Take a campaign out of draft mode. Do not support taking it back to draft mode.
                campaignx.in_draft_mode = False
            campaignx.is_blocked_by_we_vote = positive_value_exists(is_blocked_by_we_vote)
            campaignx.final_election_date_as_integer = final_election_date_as_integer
            if is_blocked_by_we_vote_reason is not None:
                campaignx.is_blocked_by_we_vote_reason = is_blocked_by_we_vote_reason.strip()
            campaignx.is_in_team_review_mode = positive_value_exists(is_in_team_review_mode)
            campaignx.is_not_promoted_by_we_vote = positive_value_exists(is_not_promoted_by_we_vote)
            if is_not_promoted_by_we_vote_reason is not None:
                campaignx.is_not_promoted_by_we_vote_reason = is_not_promoted_by_we_vote_reason.strip()
            campaignx.is_ok_to_promote_on_we_vote = positive_value_exists(is_ok_to_promote_on_we_vote)
            # Only change ocd_id_state_mismatch_resolved if ocd_id_state_mismatch_found
            if positive_value_exists(campaignx.ocd_id_state_mismatch_found) \
                    and ocd_id_state_mismatch_resolved is not None:
                campaignx.ocd_id_state_mismatch_resolved = positive_value_exists(ocd_id_state_mismatch_resolved)
            if politician_starter_list_serialized is not None:
                campaignx.politician_starter_list_serialized = politician_starter_list_serialized.strip()
            if positive_value_exists(campaignx.linked_politician_we_vote_id):
                politician_results = politician_manager.retrieve_politician(
                    politician_we_vote_id=campaignx.linked_politician_we_vote_id)
                if politician_results['politician_found']:
                    politician = politician_results['politician']
                    from campaign.controllers import update_campaignx_from_politician
                    results = update_campaignx_from_politician(campaignx=campaignx, politician=politician)
                    if results['success']:
                        campaignx = results['campaignx']
                        campaignx.date_last_updated_from_politician = localtime(now()).date()
                elif politician_results['success']:
                    # It was a successful query, but politician wasn't found. Remove the linked_politician_we_vote_id
                    campaignx.linked_politician_we_vote_id = None
            if seo_friendly_path is not None:
                # If path isn't passed in, create one. If provided, verify it is unique.
                seo_results = campaignx_manager.generate_seo_friendly_path(
                    base_pathname_string=seo_friendly_path,
                    campaignx_title=campaignx.campaign_title,
                    campaignx_we_vote_id=campaignx.we_vote_id)
                if seo_results['success']:
                    seo_friendly_path = seo_results['seo_friendly_path']
                if not positive_value_exists(seo_friendly_path):
                    seo_friendly_path = None
                campaignx.seo_friendly_path = seo_friendly_path
            if supporters_count_minimum_ignored is not None:
                campaignx.supporters_count_minimum_ignored = positive_value_exists(supporters_count_minimum_ignored)
            campaignx.save()

            messages.add_message(request, messages.INFO, 'CampaignX updated.')
        else:
            # We do not create campaigns in this view
            pass
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save CampaignX.'
                                                      ' {error} [type: {error_type}]'.format(error=e,
                                                                                             error_type=type(e)))
        return HttpResponseRedirect(reverse('campaign:campaignx_edit', args=(campaignx_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&campaignx_owner_organization_we_vote_id=" +
                                    str(campaignx_owner_organization_we_vote_id) +
                                    "&campaignx_search=" + str(campaignx_search) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('campaign:campaignx_summary', args=(campaignx_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&campaignx_owner_organization_we_vote_id=" +
                                str(campaignx_owner_organization_we_vote_id) +
                                "&campaignx_search=" + str(campaignx_search) +
                                "&state_code=" + str(state_code))


@login_required
def campaign_edit_view(request, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.GET.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.GET.get('campaignx_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    campaignx_manager = CampaignXManager()
    campaignx = None
    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)

    if results['campaignx_found']:
        campaignx = results['campaignx']

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    politician_state_code = ''
    related_campaignx_list = []
    if campaignx and positive_value_exists(campaignx.linked_politician_we_vote_id):
        try:
            from politician.models import Politician
            politician_queryset = Politician.objects.using('readonly').all()
            politician = politician_queryset.get(we_vote_id=campaignx.linked_politician_we_vote_id)
            if positive_value_exists(politician.last_name):
                from campaign.models import CampaignX
                queryset = CampaignX.objects.using('readonly').all()
                queryset = queryset.exclude(we_vote_id=campaignx_we_vote_id)
                queryset = queryset.filter(campaign_title__icontains=politician.first_name)
                queryset = queryset.filter(campaign_title__icontains=politician.last_name)
                related_campaignx_list = list(queryset)
            if positive_value_exists(politician.state_code):
                politician_state_code = politician.state_code
        except Exception as e:
            related_campaignx_list = []

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'campaignx':                                campaignx,
        'campaignx_owner_organization_we_vote_id':  campaignx_owner_organization_we_vote_id,
        'campaignx_search':                         campaignx_search,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'politician_state_code':                    politician_state_code,
        'related_campaignx_list':                   related_campaignx_list,
        'state_list':                               sorted_state_list,
        'upcoming_election_list':                   upcoming_election_list,
        'web_app_root_url':                         web_app_root_url,
    }
    return render(request, 'campaign/campaignx_edit.html', template_values)


@login_required
def campaign_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.GET.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.GET.get('campaignx_search', '')
    campaignx_type_filter = request.GET.get('campaignx_type_filter', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    hide_campaigns_not_visible_yet = \
        positive_value_exists(request.GET.get('hide_campaigns_not_visible_yet', False))
    include_campaigns_from_prior_elections = \
        positive_value_exists(request.GET.get('include_campaigns_from_prior_elections', False))
    save_changes = request.GET.get('save_changes', False)
    save_changes = positive_value_exists(save_changes)
    show_all = request.GET.get('show_all', False)
    show_blocked_campaigns = \
        positive_value_exists(request.GET.get('show_blocked_campaigns', False))
    show_campaigns_in_draft = \
        positive_value_exists(request.GET.get('show_campaigns_in_draft', False))
    show_campaigns_linked_to_politicians = \
        positive_value_exists(request.GET.get('show_campaigns_linked_to_politicians', False))
    show_more = request.GET.get('show_more', False)  # Show up to 1,000 organizations
    show_issues = request.GET.get('show_issues', '')
    show_ocd_id_state_mismatch = positive_value_exists(request.GET.get('show_ocd_id_state_mismatch', False))
    show_organizations_without_email = positive_value_exists(request.GET.get('show_organizations_without_email', False))
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    status = ''
    success = True

    messages_on_stage = get_messages(request)
    campaignx_manager = CampaignXManager()

    update_campaigns_from_politicians_script = True
    # Bring over updated politician profile photos to the campaignx entries with linked_politician_we_vote_id
    if update_campaigns_from_politicians_script:
        campaignx_list = []
        number_to_update = 5000  # Set to 5,000 at a time
        total_to_update_after = 0
        try:
            queryset = CampaignX.objects.all()
            queryset = queryset.exclude(
                Q(linked_politician_we_vote_id__isnull=True) | Q(linked_politician_we_vote_id=''))
            # if positive_value_exists(state_code):
            #     queryset = queryset.filter(state_code__iexact=state_code)
            # Ignore Campaigns which have been updated in the last 6 months: date_last_updated_from_politician
            today = datetime.now().date()
            six_months_ago = today - timedelta(weeks=26)
            queryset = queryset.exclude(date_last_updated_from_politician__gt=six_months_ago)
            total_to_update = queryset.count()
            total_to_update_after = total_to_update - number_to_update if total_to_update > number_to_update else 0
            campaignx_list = list(queryset[:number_to_update])
        except Exception as e:
            status += "CAMPAIGNX_QUERY_FAILED: " + str(e) + " "

        # Retrieve all related politicians with one query
        politician_we_vote_id_list = []
        for campaignx in campaignx_list:
            if positive_value_exists(campaignx.linked_politician_we_vote_id):
                if campaignx.linked_politician_we_vote_id not in politician_we_vote_id_list:
                    politician_we_vote_id_list.append(campaignx.linked_politician_we_vote_id)

        politician_list_by_campaignx_we_vote_id = {}
        if len(politician_we_vote_id_list) > 0:
            from politician.models import Politician
            queryset = Politician.objects.all()
            queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
            politician_list = list(queryset)
            for one_politician in politician_list:
                if positive_value_exists(one_politician.linked_campaignx_we_vote_id) and \
                        one_politician.linked_campaignx_we_vote_id not in politician_list_by_campaignx_we_vote_id:
                    politician_list_by_campaignx_we_vote_id[one_politician.linked_campaignx_we_vote_id] = one_politician

        # Loop through all the campaigns, and update them with some politician data
        if len(campaignx_list) > 0:
            campaignx_update_errors = 0
            campaigns_updated = 0
            campaigns_without_changes = 0
            update_list = []
            from campaign.controllers import update_campaignx_from_politician
            for campaignx in campaignx_list:
                if campaignx.we_vote_id in politician_list_by_campaignx_we_vote_id:
                    politician = politician_list_by_campaignx_we_vote_id[campaignx.we_vote_id]
                else:
                    politician = None
                    campaignx.date_last_updated_from_politician = localtime(now()).date()
                    campaignx.save()
                if not politician or not hasattr(politician, 'we_vote_id'):
                    continue
                results = update_campaignx_from_politician(campaignx=campaignx, politician=politician)
                if results['success']:
                    save_changes = results['save_changes']
                    campaignx = results['campaignx']
                    campaignx.date_last_updated_from_politician = localtime(now()).date()
                    update_list.append(campaignx)
                    # campaignx.save()
                    if save_changes:
                        campaigns_updated += 1
                    else:
                        campaigns_without_changes += 1
                else:
                    campaignx_update_errors += 1
                    status += results['status']
            if campaigns_updated > 0:
                try:
                    CampaignX.objects.bulk_update(
                        update_list,
                        ['we_vote_hosted_campaign_photo_large_url',
                         'we_vote_hosted_campaign_photo_medium_url',
                         'we_vote_hosted_campaign_photo_small_url',
                         'date_last_updated_from_politician',
                         'seo_friendly_path',
                         'we_vote_hosted_profile_image_url_large',
                         'we_vote_hosted_profile_image_url_medium',
                         'we_vote_hosted_profile_image_url_tiny'])
                    messages.add_message(request, messages.INFO,
                                         "{updates_made:,} campaignx entries updated from politicians. "
                                         "{total_to_update_after:,} remaining."
                                         "".format(total_to_update_after=total_to_update_after,
                                                   updates_made=campaigns_updated))
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         "ERROR with update_campaignx_list_from_politicians_script: {e} "
                                         "".format(e=e))

    campaignx_we_vote_ids_in_order = []
    if campaignx_owner_organization_we_vote_id:
        # Find existing order
        campaignx_owner_list_with_order = campaignx_manager.retrieve_campaignx_owner_list(
            organization_we_vote_id=campaignx_owner_organization_we_vote_id,
            has_order_in_list=True,
            read_only=False)
        for campaignx_owner in campaignx_owner_list_with_order:
            campaignx_we_vote_ids_in_order.append(campaignx_owner.campaignx_we_vote_id)

        if save_changes:
            campaignx_we_vote_id_list_from_owner_organization_we_vote_id = \
                campaignx_manager.fetch_campaignx_we_vote_id_list_from_owner_organization_we_vote_id(
                    campaignx_owner_organization_we_vote_id)
            for one_campaignx_we_vote_id in campaignx_we_vote_id_list_from_owner_organization_we_vote_id:
                one_campaign_order_changed_name = str(one_campaignx_we_vote_id) + '_order_changed'
                order_changed = positive_value_exists(request.GET.get(one_campaign_order_changed_name, 0))
                if positive_value_exists(order_changed):
                    # Remove existing
                    try:
                        campaignx_we_vote_ids_in_order.remove(one_campaignx_we_vote_id)
                    except Exception as e:
                        pass
                    # Find out the new placement for this item
                    one_campaign_order_in_list_name = str(one_campaignx_we_vote_id) + '_order_in_list'
                    order_in_list = request.GET.get(one_campaign_order_in_list_name, '')
                    if positive_value_exists(order_in_list):
                        order_in_list = convert_to_int(order_in_list)
                        index_from_order = order_in_list - 1
                        campaignx_we_vote_ids_in_order.insert(index_from_order, one_campaignx_we_vote_id)
                    else:
                        # Reset existing value
                        for campaignx_owner in campaignx_owner_list_with_order:
                            if campaignx_owner.campaignx_we_vote_id == one_campaignx_we_vote_id:
                                campaignx_owner.order_in_list = None
                                campaignx_owner.save()

        if len(campaignx_we_vote_ids_in_order) > 0:
            # Re-save the order of all of the campaigns
            campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
                campaignx_we_vote_id_list=campaignx_we_vote_ids_in_order,
                organization_we_vote_id=campaignx_owner_organization_we_vote_id,
                read_only=False)
            new_order = 0
            for campaignx_we_vote_id in campaignx_we_vote_ids_in_order:
                for campaignx_owner in campaignx_owner_list:
                    if campaignx_we_vote_id == campaignx_owner.campaignx_we_vote_id:
                        new_order += 1
                        campaignx_owner.order_in_list = new_order
                        campaignx_owner.save()

    campaignx_list_query = CampaignX.objects.all()
    if positive_value_exists(hide_campaigns_not_visible_yet):
        campaignx_list_query = campaignx_list_query.filter(
            Q(supporters_count__gte=SUPPORTERS_COUNT_MINIMUM_FOR_LISTING) |
            Q(supporters_count_minimum_ignored=True))

    final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
    if positive_value_exists(include_campaigns_from_prior_elections):
        pass
    else:
        campaignx_list_query = campaignx_list_query.filter(
            Q(final_election_date_as_integer__isnull=True) |
            Q(final_election_date_as_integer__gt=final_election_date_plus_cool_down))

    if positive_value_exists(show_ocd_id_state_mismatch):
        # If we are looking for bad data, ignore the filters below
        campaignx_list_query = campaignx_list_query.filter(ocd_id_state_mismatch_found=True)
    else:
        if positive_value_exists(show_blocked_campaigns):
            campaignx_list_query = campaignx_list_query.filter(is_blocked_by_we_vote=True)
        else:
            campaignx_list_query = campaignx_list_query.filter(is_blocked_by_we_vote=False)

        if positive_value_exists(show_campaigns_in_draft):
            campaignx_list_query = campaignx_list_query.filter(in_draft_mode=True)
        else:
            campaignx_list_query = campaignx_list_query.filter(in_draft_mode=False)

        if positive_value_exists(show_campaigns_linked_to_politicians):
            campaignx_list_query = campaignx_list_query.filter(linked_politician_we_vote_id__isnull=False)
        else:
            campaignx_list_query = campaignx_list_query.filter(
                Q(linked_politician_we_vote_id__isnull=True) | Q(linked_politician_we_vote_id__exact=''))

    if positive_value_exists(campaignx_owner_organization_we_vote_id):
        campaignx_we_vote_id_list_from_owner_organization_we_vote_id = \
            campaignx_manager.fetch_campaignx_we_vote_id_list_from_owner_organization_we_vote_id(
                campaignx_owner_organization_we_vote_id)
        campaignx_list_query = campaignx_list_query.filter(
            we_vote_id__in=campaignx_we_vote_id_list_from_owner_organization_we_vote_id)

    client_list_query = Organization.objects.all()
    client_list_query = client_list_query.filter(chosen_feature_package__isnull=False)
    client_organization_list = list(client_list_query)

    campaignx_to_repair_count = 0
    if positive_value_exists(show_ocd_id_state_mismatch):
        campaignx_queryset_not_resolved = campaignx_list_query.exclude(ocd_id_state_mismatch_resolved=True)
        campaignx_to_repair_count = campaignx_queryset_not_resolved.count()
        campaignx_list_query = campaignx_list_query.order_by('ocd_id_state_mismatch_resolved')
    elif positive_value_exists(sort_by):
        # if sort_by == "twitter":
        #     campaignx_list_query = \
        #         campaignx_list_query.order_by('organization_name').order_by('-twitter_followers_count')
        # else:
        campaignx_list_query = campaignx_list_query.order_by('-supporters_count')
    else:
        campaignx_list_query = campaignx_list_query.order_by('-supporters_count')

    if positive_value_exists(campaignx_search):
        search_words = campaignx_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(campaign_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(campaign_description__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(linked_politician_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(seo_friendly_path__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(started_by_voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                campaignx_list_query = campaignx_list_query.filter(final_filters)

    campaignx_count = campaignx_list_query.count()
    messages.add_message(request, messages.INFO,
                         '{campaignx_count:,} campaigns found.'.format(campaignx_count=campaignx_count))
    if positive_value_exists(campaignx_to_repair_count):
        messages.add_message(request, messages.INFO,
                             '{campaignx_to_repair_count:,} campaigns to repair.'
                             ''.format(campaignx_to_repair_count=campaignx_to_repair_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        campaignx_list = campaignx_list_query[:1000]
    elif positive_value_exists(show_all):
        campaignx_list = campaignx_list_query
    else:
        campaignx_list = campaignx_list_query[:50]

    if len(campaignx_we_vote_ids_in_order) > 0:
        modified_campaignx_list = []
        campaignx_we_vote_id_already_placed = []
        for campaignx_we_vote_id in campaignx_we_vote_ids_in_order:
            for campaignx in campaignx_list:
                if campaignx_we_vote_id == campaignx.we_vote_id:
                    modified_campaignx_list.append(campaignx)
                    campaignx_we_vote_id_already_placed.append(campaignx.we_vote_id)
        # Now add the rest
        for campaignx in campaignx_list:
            if campaignx.we_vote_id not in campaignx_we_vote_id_already_placed:
                modified_campaignx_list.append(campaignx)
                campaignx_we_vote_id_already_placed.append(campaignx.we_vote_id)
        campaignx_list = modified_campaignx_list

    # Now loop through these organizations and add owners
    modified_campaignx_list = []
    politician_we_vote_id_list = []
    for campaignx in campaignx_list:
        campaignx.campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
            campaignx_we_vote_id_list=[campaignx.we_vote_id],
            viewer_is_owner=True)
        campaignx.chip_in_total = StripeManager.retrieve_chip_in_total('', campaignx.we_vote_id)
        modified_campaignx_list.append(campaignx)
        if positive_value_exists(campaignx.linked_politician_we_vote_id):
            politician_we_vote_id_list.append(campaignx.linked_politician_we_vote_id)

    if len(politician_we_vote_id_list) > 0:
        modified_campaignx_list2 = []
        from politician.models import Politician
        queryset = Politician.objects.all()
        queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        for campaignx in modified_campaignx_list:
            for one_politician in politician_list:
                if one_politician.we_vote_id == campaignx.linked_politician_we_vote_id:
                    campaignx.linked_politician_state_code = one_politician.state_code
            modified_campaignx_list2.append(campaignx)
        modified_campaignx_list = modified_campaignx_list2

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'campaignx_list':                           modified_campaignx_list,
        'campaignx_owner_organization_we_vote_id':  campaignx_owner_organization_we_vote_id,
        'campaignx_search':                         campaignx_search,
        'campaignx_type_filter':                    campaignx_type_filter,
        'campaignx_types':                          [],
        'client_organization_list':                 client_organization_list,
        'final_election_date_plus_cool_down':       final_election_date_plus_cool_down,
        'google_civic_election_id':                 google_civic_election_id,
        'hide_campaigns_not_visible_yet':           hide_campaigns_not_visible_yet,
        'include_campaigns_from_prior_elections':   include_campaigns_from_prior_elections,
        'limit_to_opinions_in_state_code':          limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year':           limit_to_opinions_in_this_year,
        'messages_on_stage':                        messages_on_stage,
        'show_all':                                 show_all,
        'show_blocked_campaigns':                   show_blocked_campaigns,
        'show_campaigns_in_draft':                  show_campaigns_in_draft,
        'show_campaigns_linked_to_politicians':     show_campaigns_linked_to_politicians,
        'show_issues':                              show_issues,
        'show_more':                                show_more,
        'show_ocd_id_state_mismatch':               show_ocd_id_state_mismatch,
        'show_organizations_without_email':         show_organizations_without_email,
        'sort_by':                                  sort_by,
        'state_code':                               state_code,
        'state_list':                               sorted_state_list,
        'web_app_root_url':                         web_app_root_url,
    }
    return render(request, 'campaign/campaignx_list.html', template_values)


@login_required
def campaign_summary_view(request, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.GET.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.GET.get('campaignx_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')
    status = ''

    messages_on_stage = get_messages(request)
    campaignx_manager = CampaignXManager()
    campaignx = None

    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)

    if results['campaignx_found']:
        campaignx = results['campaignx']
    else:
        status += results['status']
        messages.add_message(request, messages.ERROR,
                             'CampaignX \'{campaignx_we_vote_id}\' not found: {status}.'
                             ''.format(
                                 campaignx_we_vote_id=campaignx_we_vote_id,
                                 status=status))
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # ##################################
    # Show the seo friendly paths for this campaignx
    path_count = 0
    path_list = []
    if positive_value_exists(campaignx_we_vote_id):
        from campaign.models import CampaignXSEOFriendlyPath
        try:
            path_query = CampaignXSEOFriendlyPath.objects.all()
            path_query = path_query.filter(campaignx_we_vote_id__iexact=campaignx_we_vote_id)
            path_count = path_query.count()
            path_list = list(path_query[:4])
        except Exception as e:
            status += 'ERROR_RETRIEVING_FROM_CampaignXSEOFriendlyPath: ' + str(e) + ' '

        if positive_value_exists(campaignx.seo_friendly_path):
            path_list_modified = []
            for one_path in path_list:
                if campaignx.seo_friendly_path != one_path.final_pathname_string:
                    path_list_modified.append(one_path)
            path_list = path_list_modified
        path_list = path_list[:3]

    campaignx_owner_list_modified = []
    campaignx_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
        campaignx_we_vote_id_list=[campaignx_we_vote_id],
        viewer_is_owner=True
    )

    for campaignx_owner in campaignx_owner_list:
        campaignx_owner_list_modified.append(campaignx_owner)

    campaignx_politician_list_modified = []
    campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
        campaignx_we_vote_id=campaignx_we_vote_id,
    )

    for campaignx_politician in campaignx_politician_list:
        campaignx_politician_list_modified.append(campaignx_politician)

    supporters_query = CampaignXSupporter.objects.all()
    supporters_query = supporters_query.filter(campaignx_we_vote_id__iexact=campaignx_we_vote_id)
    supporters_query = supporters_query.exclude(
        Q(supporter_endorsement__isnull=True) |
        Q(supporter_endorsement__exact='')
    )
    campaignx_supporter_list = list(supporters_query[:4])

    campaignx_supporters_count = campaignx_manager.fetch_campaignx_supporter_count(campaignx_we_vote_id)
    if 'localhost' in CAMPAIGNS_ROOT_URL:
        campaigns_site_root_url = 'https://localhost:3000'
    else:
        campaigns_site_root_url = 'https://campaigns.WeVote.US'
    template_values = {
        'campaigns_site_root_url':                  campaigns_site_root_url,
        'campaignx':                                campaignx,
        'campaignx_owner_list':                     campaignx_owner_list_modified,
        'campaignx_owner_organization_we_vote_id':  campaignx_owner_organization_we_vote_id,
        'campaignx_politician_list':                campaignx_politician_list_modified,
        'campaignx_search':                         campaignx_search,
        'campaignx_supporters_count':               campaignx_supporters_count,
        'campaignx_supporter_list':                 campaignx_supporter_list,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'path_count':                               path_count,
        'path_list':                                path_list,
        'state_code':                               state_code,
    }
    return render(request, 'campaign/campaignx_summary.html', template_values)


@login_required
def campaign_supporters_list_view(request, campaignx_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.GET.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.GET.get('campaignx_search', '')
    campaignx_type_filter = request.GET.get('campaignx_type_filter', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_more = request.GET.get('show_more', False)  # Show up to 1,000 organizations
    show_issues = request.GET.get('show_issues', '')
    only_show_supporters_with_endorsements = \
        positive_value_exists(request.GET.get('only_show_supporters_with_endorsements', False))
    show_supporters_not_visible_to_public = \
        positive_value_exists(request.GET.get('show_supporters_not_visible_to_public', False))

    messages_on_stage = get_messages(request)

    campaignx = CampaignX.objects.get(we_vote_id__iexact=campaignx_we_vote_id)
    campaignx_title = campaignx.campaign_title

    supporters_query = CampaignXSupporter.objects.all()
    supporters_query = supporters_query.filter(campaignx_we_vote_id__iexact=campaignx_we_vote_id)

    if positive_value_exists(only_show_supporters_with_endorsements):
        supporters_query = supporters_query.exclude(
            Q(supporter_endorsement__isnull=True) |
            Q(supporter_endorsement__exact='')
        )

    supporters_query = supporters_query.order_by('-date_supported')

    if positive_value_exists(show_supporters_not_visible_to_public):
        pass
    else:
        # Default to only show visible_to_public
        supporters_query = supporters_query.filter(visible_to_public=True)

    # if positive_value_exists(state_code):
    #     supporters_query = supporters_query.filter(state_served_code__iexact=state_code)
    #
    # if positive_value_exists(campaignx_type_filter):
    #     if campaignx_type_filter == UNKNOWN:
    #         # Make sure to also show organizations that are not specified
    #         supporters_query = supporters_query.filter(
    #             Q(organization_type__iexact=campaignx_type_filter) |
    #             Q(organization_type__isnull=True) |
    #             Q(organization_type__exact='')
    #         )
    #     else:
    #         supporters_query = supporters_query.filter(organization_type__iexact=campaignx_type_filter)
    # else:
    #     # By default, don't show individuals
    #     supporters_query = supporters_query.exclude(organization_type__iexact=INDIVIDUAL)

    if positive_value_exists(campaignx_search):
        search_words = campaignx_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(supporter_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(supporter_endorsement__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                supporters_query = supporters_query.filter(final_filters)

    supporters_count = supporters_query.count()
    messages.add_message(request, messages.INFO,
                         'Showing {supporters_count:,} campaign supporters.'.format(supporters_count=supporters_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        supporters_list = supporters_query[:1000]
    elif positive_value_exists(show_all):
        supporters_list = supporters_query
    else:
        supporters_list = supporters_query[:200]

    for supporter in supporters_list:
        supporter.chip_in_total = StripeManager.retrieve_chip_in_total(supporter.voter_we_vote_id,
                                                                       supporter.campaignx_we_vote_id)


    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'campaignx_owner_organization_we_vote_id':  campaignx_owner_organization_we_vote_id,
        'campaignx_search':                         campaignx_search,
        'campaignx_we_vote_id':                     campaignx_we_vote_id,
        'campaignx_title':                          campaignx_title,
        'google_civic_election_id':                 google_civic_election_id,
        'limit_to_opinions_in_state_code':          limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year':           limit_to_opinions_in_this_year,
        'messages_on_stage':                        messages_on_stage,
        'campaignx_type_filter':                    campaignx_type_filter,
        'campaignx_types':                          [],
        'supporters_list':                          supporters_list,
        'show_all':                                 show_all,
        'show_issues':                              show_issues,
        'show_more':                                show_more,
        'show_supporters_not_visible_to_public':    show_supporters_not_visible_to_public,
        'only_show_supporters_with_endorsements':     only_show_supporters_with_endorsements,
        'sort_by':                                  sort_by,
        'state_code':                               state_code,
        'state_list':                               sorted_state_list,
    }
    return render(request, 'campaign/campaignx_supporters_list.html', template_values)


@csrf_protect
@login_required
def campaign_supporters_list_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_owner_organization_we_vote_id = request.POST.get('campaignx_owner_organization_we_vote_id', '')
    campaignx_search = request.POST.get('campaignx_search', '')
    campaignx_we_vote_id = request.POST.get('campaignx_we_vote_id', '')
    google_civic_election_id = request.POST.get('google_civic_election_id', '')
    incoming_campaignx_supporter_we_vote_id = request.POST.get('incoming_campaignx_supporter_we_vote_id', '')
    incoming_campaignx_supporter_endorsement = request.POST.get('incoming_campaignx_supporter_endorsement', '')
    incoming_campaignx_supporter_wants_visibility = request.POST.get('incoming_campaignx_supporter_wants_visibility', '')
    incoming_visibility_blocked_by_we_vote = request.POST.get('incoming_visibility_blocked_by_we_vote', '')
    state_code = request.POST.get('state_code', '')
    show_all = request.POST.get('show_all', False)
    show_more = request.POST.get('show_more', False)  # Show up to 1,000 organizations
    only_show_supporters_with_endorsements = \
        positive_value_exists(request.POST.get('only_show_supporters_with_endorsements', False))
    show_supporters_not_visible_to_public = \
        positive_value_exists(request.POST.get('show_supporters_not_visible_to_public', False))

    update_message = ''
    voter_manager = VoterManager()
    organization_manager = OrganizationManager()

    campaignx_supporter_organization_we_vote_id = ''
    campaignx_supporter_voter_we_vote_id = ''
    if positive_value_exists(incoming_campaignx_supporter_we_vote_id):
        # We allow either organization_we_vote_id or voter_we_vote_id
        if 'org' in incoming_campaignx_supporter_we_vote_id:
            campaignx_supporter_organization_we_vote_id = incoming_campaignx_supporter_we_vote_id
            campaignx_supporter_voter_we_vote_id = \
                voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                    campaignx_supporter_organization_we_vote_id)
        elif 'voter' in incoming_campaignx_supporter_we_vote_id:
            campaignx_supporter_voter_we_vote_id = incoming_campaignx_supporter_we_vote_id
            campaignx_supporter_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(
                    incoming_campaignx_supporter_we_vote_id)

    politician_we_vote_id = ''
    if positive_value_exists(campaignx_we_vote_id):
        try:
            campaignx_on_stage = CampaignX.objects.get(we_vote_id=campaignx_we_vote_id)
            politician_we_vote_id = campaignx_on_stage.linked_politician_we_vote_id
        except Exception as e:
            politician_we_vote_id = ''
    politician_we_vote_id_list = []
    if positive_value_exists(politician_we_vote_id):
        politician_we_vote_id_list.append(politician_we_vote_id)

    supporters_query = CampaignXSupporter.objects.all()
    supporters_query = supporters_query.filter(campaignx_we_vote_id__iexact=campaignx_we_vote_id)

    if positive_value_exists(only_show_supporters_with_endorsements):
        supporters_query = supporters_query.exclude(
            Q(supporter_endorsement__isnull=True) |
            Q(supporter_endorsement__exact='')
        )

    supporters_query = supporters_query.order_by('-date_supported')

    if positive_value_exists(show_supporters_not_visible_to_public):
        pass
    else:
        # Default to only show visible_to_public
        supporters_query = supporters_query.filter(visible_to_public=True)

    if positive_value_exists(campaignx_search):
        search_words = campaignx_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(supporter_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(supporter_endorsement__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                supporters_query = supporters_query.filter(final_filters)

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        supporters_list = supporters_query[:1000]
    elif positive_value_exists(show_all):
        supporters_list = supporters_query
    else:
        supporters_list = supporters_query[:200]

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    # Create new CampaignXSupporter
    if positive_value_exists(campaignx_supporter_organization_we_vote_id) or \
            positive_value_exists(campaignx_supporter_voter_we_vote_id):
        do_not_create = False
        supporter_already_exists = False
        status = ""
        # Does it already exist?
        try:
            if positive_value_exists(campaignx_supporter_organization_we_vote_id):
                CampaignXSupporter.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    organization_we_vote_id=campaignx_supporter_organization_we_vote_id)
                supporter_already_exists = True
            elif positive_value_exists(campaignx_supporter_voter_we_vote_id):
                CampaignXSupporter.objects.get(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    voter_we_vote_id=campaignx_supporter_voter_we_vote_id)
                supporter_already_exists = True
        except CampaignXSupporter.DoesNotExist:
            supporter_already_exists = False
        except Exception as e:
            do_not_create = True
            messages.add_message(request, messages.ERROR, 'CampaignXSupporter already exists.')
            status += "ADD_CAMPAIGN_SUPPORTER_ALREADY_EXISTS " + str(e) + " "

        if not do_not_create and not supporter_already_exists:
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(campaignx_supporter_organization_we_vote_id)
            if organization_results['organization_found']:
                supporter_name = organization_results['organization'].supporter_name
                we_vote_hosted_profile_image_url_medium = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_medium
                we_vote_hosted_profile_image_url_tiny = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_tiny
            else:
                supporter_name = ''
                we_vote_hosted_profile_image_url_medium = ''
                we_vote_hosted_profile_image_url_tiny = ''
            try:
                # Create the CampaignXSupporter
                CampaignXSupporter.objects.create(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    supporter_name=supporter_name,
                    organization_we_vote_id=campaignx_supporter_organization_we_vote_id,
                    supporter_endorsement=incoming_campaignx_supporter_endorsement,
                    voter_we_vote_id=campaignx_supporter_voter_we_vote_id,
                    we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    visibility_blocked_by_we_vote=incoming_visibility_blocked_by_we_vote,
                    visible_to_public=incoming_campaignx_supporter_wants_visibility)

                messages.add_message(request, messages.INFO, 'New CampaignXSupporter created.')
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     'Could not create CampaignXSupporter.'
                                     ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or editing a CampaignXSupporter
    update_campaignx_supporter_count = False
    results = deleting_or_editing_campaignx_supporter_list(
        request=request,
        supporters_list=supporters_list,
    )
    update_campaignx_supporter_count = update_campaignx_supporter_count or results['update_campaignx_supporter_count']
    update_message = results['update_message']
    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    campaignx_we_vote_id_list_to_refresh = [campaignx_we_vote_id]
    if len(politician_we_vote_id_list) > 0:
        # #############################
        # Create campaignx_supporters
        create_from_friends_only_positions = False
        results = create_campaignx_supporters_from_positions(
            request,
            friends_only_positions=False,
            politician_we_vote_id_list=politician_we_vote_id_list)
        campaignx_we_vote_id_list_changed = results['campaignx_we_vote_id_list_to_refresh']
        if len(campaignx_we_vote_id_list_changed) > 0:
            campaignx_we_vote_id_list_to_refresh = \
                list(set(campaignx_we_vote_id_list_changed + campaignx_we_vote_id_list_to_refresh))
        if not positive_value_exists(results['campaignx_supporter_entries_created']):
            create_from_friends_only_positions = True
        if create_from_friends_only_positions:
            results = create_campaignx_supporters_from_positions(
                request,
                friends_only_positions=True,
                politician_we_vote_id_list=politician_we_vote_id_list)
            campaignx_we_vote_id_list_changed = results['campaignx_we_vote_id_list_to_refresh']
            if len(campaignx_we_vote_id_list_changed) > 0:
                campaignx_we_vote_id_list_to_refresh = \
                    list(set(campaignx_we_vote_id_list_changed + campaignx_we_vote_id_list_to_refresh))

    # We update here only if we didn't save above
    if update_campaignx_supporter_count and positive_value_exists(campaignx_we_vote_id):
        campaignx_manager = CampaignXManager()
        supporter_count = campaignx_manager.fetch_campaignx_supporter_count(campaignx_we_vote_id)
        results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)
        if results['campaignx_found']:
            campaignx = results['campaignx']
            campaignx.supporters_count = supporter_count
            campaignx.save()

    results = refresh_campaignx_supporters_count_in_all_children(
        request,
        campaignx_we_vote_id_list=campaignx_we_vote_id_list_to_refresh)
    if positive_value_exists(results['update_message']):
        update_message += results['update_message']

    return HttpResponseRedirect(reverse('campaign:supporters_list', args=(campaignx_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&campaignx_owner_organization_we_vote_id=" +
                                str(campaignx_owner_organization_we_vote_id) +
                                "&campaignx_search=" + str(campaignx_search) +
                                "&state_code=" + str(state_code) +
                                "&only_show_supporters_with_endorsements=" + str(only_show_supporters_with_endorsements) +
                                "&show_supporters_not_visible_to_public=" + str(show_supporters_not_visible_to_public)
                                )


@login_required
def compare_two_campaigns_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # campaignx_year = request.GET.get('campaignx_year', 0)
    campaignx1_we_vote_id = request.GET.get('campaignx1_we_vote_id', 0)
    campaignx2_we_vote_id = request.GET.get('campaignx2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    if campaignx1_we_vote_id == campaignx2_we_vote_id:
        messages.add_message(request, messages.ERROR,
                             "CampaignX1 and CampaignX2 are the same -- can't compare.")
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    campaignx_manager = CampaignXManager()
    campaignx_results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx1_we_vote_id, read_only=True)
    if not campaignx_results['campaignx_found']:
        messages.add_message(request, messages.ERROR, "CampaignX1 not found.")
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    campaignx_option1_for_template = campaignx_results['campaignx']

    campaignx_results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx2_we_vote_id, read_only=True)
    if not campaignx_results['campaignx_found']:
        messages.add_message(request, messages.ERROR, "CampaignX2 not found.")
        return HttpResponseRedirect(reverse('campaign:campaignx_summary',
                                            args=(campaignx_option1_for_template.we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    campaignx_option2_for_template = campaignx_results['campaignx']

    campaignx_merge_conflict_values = figure_out_campaignx_conflict_values(
        campaignx_option1_for_template, campaignx_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_campaignx_merge_form(
        request,
        campaignx_option1_for_template,
        campaignx_option2_for_template,
        campaignx_merge_conflict_values,
        # campaignx_year=campaignx_year,
        remove_duplicate_process=remove_duplicate_process)


def render_campaignx_merge_form(
        request,
        campaignx_option1_for_template,
        campaignx_option2_for_template,
        campaignx_merge_conflict_values,
        campaignx_year=0,
        remove_duplicate_process=True):
    from politician.models import Politician

    politician1_full_name = ''
    politician1_state_code = ''
    if campaignx_option1_for_template and \
            positive_value_exists(campaignx_option1_for_template.linked_politician_we_vote_id):
        try:
            politician_queryset = Politician.objects.using('readonly').all()
            politician = politician_queryset.get(we_vote_id=campaignx_option1_for_template.linked_politician_we_vote_id)
            if politician and positive_value_exists(politician.first_name):
                politician1_full_name = politician.display_full_name()
            if politician and positive_value_exists(politician.state_code):
                politician1_state_code = politician.state_code
        except Exception as e:
            pass

    politician2_full_name = ''
    politician2_state_code = ''
    if campaignx_option1_for_template and \
            positive_value_exists(campaignx_option2_for_template.linked_politician_we_vote_id):
        try:
            politician_queryset = Politician.objects.using('readonly').all()
            politician = politician_queryset.get(we_vote_id=campaignx_option2_for_template.linked_politician_we_vote_id)
            if politician and positive_value_exists(politician.first_name):
                politician2_full_name = politician.display_full_name()
            if politician and positive_value_exists(politician.state_code):
                politician2_state_code = politician.state_code
        except Exception as e:
            pass

    messages_on_stage = get_messages(request)
    template_values = {
        'campaignx_option1':        campaignx_option1_for_template,
        'campaignx_option2':        campaignx_option2_for_template,
        'campaignx_year':           campaignx_year,
        'conflict_values':          campaignx_merge_conflict_values,
        'messages_on_stage':        messages_on_stage,
        'remove_duplicate_process': remove_duplicate_process,
        'politician1_full_name':    politician1_full_name,
        'politician1_state_code':   politician1_state_code,
        'politician2_full_name':    politician2_full_name,
        'politician2_state_code':   politician2_state_code,
    }
    return render(request, 'campaign/campaignx_merge.html', template_values)


@csrf_protect
@login_required
def campaignx_merge_process_view(request):
    """
    Process the merging of two campaignx entries
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaignx_manager = CampaignXManager()

    is_post = True if request.method == 'POST' else False

    if is_post:
        merge = request.POST.get('merge', False)
        skip = request.POST.get('skip', False)

        # CampaignX 1 is the one we keep, and CampaignX 2 is the one we will merge into CampaignX 1
        campaignx_year = request.POST.get('campaignx_year', 0)
        campaignx1_we_vote_id = request.POST.get('campaignx1_we_vote_id', 0)
        campaignx2_we_vote_id = request.POST.get('campaignx2_we_vote_id', 0)
        google_civic_election_id = request.POST.get('google_civic_election_id', 0)
        redirect_to_campaignx_list = request.POST.get('redirect_to_campaignx_list', False)
        regenerate_campaign_title = positive_value_exists(request.POST.get('regenerate_campaign_title', False))
        remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
        state_code = request.POST.get('state_code', '')
    else:
        merge = request.GET.get('merge', False)
        skip = request.GET.get('skip', False)

        # CampaignX 1 is the one we keep, and CampaignX 2 is the one we will merge into CampaignX 1
        campaignx_year = request.GET.get('campaignx_year', 0)
        campaignx1_we_vote_id = request.GET.get('campaignx1_we_vote_id', 0)
        campaignx2_we_vote_id = request.GET.get('campaignx2_we_vote_id', 0)
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        redirect_to_campaignx_list = request.GET.get('redirect_to_campaignx_list', False)
        regenerate_campaign_title = positive_value_exists(request.GET.get('regenerate_campaign_title', False))
        remove_duplicate_process = request.GET.get('remove_duplicate_process', False)
        state_code = request.GET.get('state_code', '')

    if positive_value_exists(skip):
        results = campaignx_manager.update_or_create_campaignx_entries_are_not_duplicates(
            campaignx1_we_vote_id, campaignx2_we_vote_id)
        if not results['new_campaignx_entries_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save campaignx_entries_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior campaignx entries skipped, and not merged.')
        # When implemented, consider directing here: find_and_merge_duplicate_campaignx_entries
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    "?campaignx_year=" + str(campaignx_year) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    campaignx1_results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx1_we_vote_id, read_only=True)
    if campaignx1_results['campaignx_found']:
        campaignx1_on_stage = campaignx1_results['campaignx']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve campaignx 1.')
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_campaignx_entries=' + str(campaignx_year) +
                                    '&state_code=' + str(state_code))

    campaignx2_results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx2_we_vote_id, read_only=True)
    if campaignx2_results['campaignx_found']:
        campaignx2_on_stage = campaignx2_results['campaignx']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve campaignx 2.')
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_campaignx_entries=' + str(campaignx_year) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_values = figure_out_campaignx_conflict_values(campaignx1_on_stage, campaignx2_on_stage)
    admin_merge_choices = {}
    for attribute in CAMPAIGNX_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            if is_post:
                choice = request.POST.get(attribute + '_choice', '')
            else:
                choice = request.GET.get(attribute + '_choice', '')
            if campaignx2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(campaignx2_on_stage, attribute)
        elif conflict_value == "CANDIDATE2":
            admin_merge_choices[attribute] = getattr(campaignx2_on_stage, attribute)

    merge_results = merge_these_two_campaignx_entries(
        campaignx1_we_vote_id,
        campaignx2_we_vote_id,
        admin_merge_choices,
        regenerate_campaign_title=regenerate_campaign_title)

    if positive_value_exists(merge_results['campaignx_entries_merged']):
        campaignx = merge_results['campaignx']
        messages.add_message(request, messages.INFO, "CampaignX '{campaignx_title}' merged."
                                                     "".format(campaignx_title=campaignx.campaign_title))
    else:
        # NOTE: We could also redirect to a page to look specifically at these two campaignx entries, but this should
        # also get you back to looking at the two campaignx entries
        messages.add_message(request, messages.ERROR, merge_results['status'])
        return HttpResponseRedirect(reverse('campaign:find_and_merge_duplicate_campaignx_entries', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    '&campaignx_year=' + str(campaignx_year) +
                                    "&auto_merge_off=1" +
                                    "&state_code=" + str(state_code))

    if redirect_to_campaignx_list:
        return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_campaignx_entries=' + str(campaignx_year) +
                                    '&state_code=' + str(state_code))

    # To be implemented
    # if remove_duplicate_process:
    #     return HttpResponseRedirect(reverse('campaign:find_and_merge_duplicate_campaignx_entries', args=()) +
    #                                 "?google_civic_election_id=" + str(google_civic_election_id) +
    #                                 '&campaignx_year=' + str(campaignx_year) +
    #                                 "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('campaign:campaignx_edit', args=(campaignx.we_vote_id,)))


def deleting_or_editing_campaignx_supporter_list(
        request=None,
        supporters_list=[],
):
    organization_dict_by_we_vote_id = {}
    organization_manager = OrganizationManager()
    update_campaignx_supporter_count = False
    update_message = ''
    voter_manager = VoterManager()
    for campaignx_supporter in supporters_list:
        if positive_value_exists(campaignx_supporter.campaignx_we_vote_id):
            delete_variable_name = "delete_campaignx_supporter_" + str(campaignx_supporter.id)
            delete_campaignx_supporter = positive_value_exists(request.POST.get(delete_variable_name, False))
            if positive_value_exists(delete_campaignx_supporter):
                campaignx_supporter.delete()
                update_campaignx_supporter_count = True
                update_message += 'Deleted CampaignXSupporter. '
            else:
                supporter_changed = False
                data_exists_variable_name = \
                    "campaignx_supporter_" + str(campaignx_supporter.id) + "_exists"
                campaignx_supporter_exists = request.POST.get(data_exists_variable_name, None)
                # Supporter Wants Visibility
                visible_to_public_variable_name = "campaignx_supporter_visible_to_public_" + str(campaignx_supporter.id)
                campaignx_supporter_visible_to_public = \
                    positive_value_exists(request.POST.get(visible_to_public_variable_name, False))
                # Visibility Blocked by We Vote
                blocked_by_we_vote_variable_name = \
                    "campaignx_supporter_visibility_blocked_by_we_vote_" + str(campaignx_supporter.id)
                campaignx_supporter_visibility_blocked_by_we_vote = \
                    positive_value_exists(request.POST.get(blocked_by_we_vote_variable_name, False))
                if campaignx_supporter_exists is not None:
                    campaignx_supporter.visibility_blocked_by_we_vote = \
                        campaignx_supporter_visibility_blocked_by_we_vote
                    campaignx_supporter.visible_to_public = campaignx_supporter_visible_to_public
                    supporter_changed = True

                # Now refresh organization cached data
                organization = None
                organization_found = False
                if campaignx_supporter.organization_we_vote_id in organization_dict_by_we_vote_id:
                    organization = organization_dict_by_we_vote_id[campaignx_supporter.organization_we_vote_id]
                    if hasattr(organization, 'we_vote_hosted_profile_image_url_medium'):
                        organization_found = True
                else:
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        campaignx_supporter.organization_we_vote_id,
                        read_only=True)
                    if organization_results['organization_found']:
                        organization = organization_results['organization']
                        organization_dict_by_we_vote_id[campaignx_supporter.organization_we_vote_id] = organization
                        organization_found = True
                if organization_found:
                    supporter_name = organization.organization_name
                    if positive_value_exists(supporter_name) and \
                            campaignx_supporter.supporter_name != supporter_name:
                        campaignx_supporter.supporter_name = supporter_name
                        supporter_changed = True
                    we_vote_hosted_profile_image_url_medium = \
                        organization.we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium) and \
                            campaignx_supporter.we_vote_hosted_profile_image_url_medium != \
                            we_vote_hosted_profile_image_url_medium:
                        campaignx_supporter.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                        supporter_changed = True
                    we_vote_hosted_profile_image_url_tiny = organization.we_vote_hosted_profile_image_url_tiny
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny) and \
                            campaignx_supporter.we_vote_hosted_profile_image_url_tiny != \
                            we_vote_hosted_profile_image_url_tiny:
                        campaignx_supporter.we_vote_hosted_profile_image_url_tiny = \
                            we_vote_hosted_profile_image_url_tiny
                        supporter_changed = True
                if not positive_value_exists(campaignx_supporter.voter_we_vote_id):
                    voter_we_vote_id = voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                        campaignx_supporter.organization_we_vote_id)
                    if positive_value_exists(voter_we_vote_id):
                        campaignx_supporter.voter_we_vote_id = voter_we_vote_id
                        supporter_changed = True
                if supporter_changed:
                    campaignx_supporter.save()
                    update_message += 'Updated CampaignXSupporter. '
    results = {
        'update_campaignx_supporter_count': update_campaignx_supporter_count,
        'update_message': update_message,
    }
    return results


@login_required
def repair_ocd_id_mismatch_damage_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    bulk_update_campaignx_list = []
    campaignx_list_count = 0
    campaignx_list_remaining_count = 0
    campaignx_db_error_count = 0
    politician_db_error_count = 0
    campaignx_politician_ids_removed_count = 0
    campaignx_politician_id_to_be_removed_count = 0
    seo_friendly_path_failed_error_count = 0
    status = ''
    try:
        queryset = CampaignX.objects.all()
        queryset = queryset.exclude(
            Q(linked_politician_we_vote_id__isnull=True) | Q(linked_politician_we_vote_id=''))
        # queryset = queryset.filter(ocd_id_state_mismatch_checked_politician=False)
        queryset = queryset.filter(ocd_id_state_mismatch_found=True)
        queryset = queryset.filter(ocd_id_state_mismatch_resolved=False)
        queryset = queryset.filter(ocd_id_state_mismatch_checked_campaign_title=False)
        campaignx_list = list(queryset[:100])
        campaignx_list_count = len(campaignx_list)
        campaignx_list_remaining_count = queryset.count() - campaignx_list_count
        from campaign.controllers import update_campaignx_from_politician
        from politician.models import Politician, PoliticianManager
        politician_manager = PoliticianManager()
        for one_campaignx in campaignx_list:
            save_campaignx_changes = True  # Default to saving
            if positive_value_exists(one_campaignx.linked_politician_we_vote_id):
                politician_results = politician_manager.retrieve_politician(
                    politician_we_vote_id=one_campaignx.linked_politician_we_vote_id,
                    read_only=True)
                if politician_results['politician_found']:
                    politician = politician_results['politician']
                    try:
                        if positive_value_exists(politician.seo_friendly_path):
                            one_campaignx.seo_friendly_path = politician.seo_friendly_path
                            one_campaignx.save()
                        else:
                            one_campaignx.seo_friendly_path = None
                    except Exception as e:
                        # If the save failed, it is because the seo_friendly_path is already used by another CampaignX
                        one_campaignx.seo_friendly_path = None
                        seo_friendly_path_failed_error_count += 1
                        if seo_friendly_path_failed_error_count < 10:
                            status += "SEO_FRIENDLY_PATH_COLLISION "
                    # Check to make sure the campaign_title contains the State name
                    if positive_value_exists(politician.state_code) \
                            and positive_value_exists(one_campaignx.campaign_title):
                        new_state_name = convert_state_code_to_state_text(politician.state_code)
                        if positive_value_exists(new_state_name) and new_state_name not in one_campaignx.campaign_title:
                            # Cycle through
                            for state_code, state_name in STATE_CODE_MAP.items():
                                if state_name in one_campaignx.campaign_title:
                                    temp_new_campaign_title = \
                                        one_campaignx.campaign_title.replace(state_name, new_state_name)
                                    if temp_new_campaign_title != one_campaignx.campaign_title:
                                        # Update to the new campaign_title and break out of the for loop
                                        save_campaignx_changes = True
                                        one_campaignx.campaign_title = temp_new_campaign_title
                                        break
                elif politician_results['success']:
                    campaignx_politician_id_to_be_removed_count += 1
                    one_campaignx.linked_politician_we_vote_id = None
                    save_campaignx_changes = True
                    campaignx_politician_ids_removed_count += 1
                else:
                    save_campaignx_changes = False
                    politician_db_error_count += 1
                    if politician_db_error_count < 10:
                        status += "ERROR_RETRIEVING_POLITICIAN: " + str(politician_results['status']) + " "
            if save_campaignx_changes:
                try:
                    one_campaignx.ocd_id_state_mismatch_checked_campaign_title = True
                    one_campaignx.ocd_id_state_mismatch_checked_politician = True
                    one_campaignx.date_last_updated_from_politician = localtime(now()).date()
                    # one_campaignx.save()
                    bulk_update_campaignx_list.append(one_campaignx)
                except Exception as e:
                    campaignx_db_error_count += 1
                    if campaignx_db_error_count < 10:
                        status += "ERROR_SAVING_CAMPAIGNX: " + str(e) + " "
    except Exception as e:
        status += "GENERAL_ERROR: " + str(e) + " "

    if len(bulk_update_campaignx_list) > 0:
        try:
            CampaignX.objects.bulk_update(
                bulk_update_campaignx_list,
                [
                 'campaign_title',
                 'date_last_updated_from_politician',
                 'linked_politician_we_vote_id',
                 'ocd_id_state_mismatch_checked_campaign_title',
                 'ocd_id_state_mismatch_checked_politician',
                 # 'we_vote_hosted_campaign_photo_large_url',
                 # 'we_vote_hosted_campaign_photo_medium_url',
                 # 'we_vote_hosted_campaign_photo_small_url',
                 'seo_friendly_path',
                 # 'we_vote_hosted_profile_image_url_large',
                 # 'we_vote_hosted_profile_image_url_medium',
                 # 'we_vote_hosted_profile_image_url_tiny'
                 ])
            # messages.add_message(request, messages.INFO,
            #                      "{updates_made:,} campaignx entries updated from politicians. "
            #                      "".format(updates_made=len(bulk_update_campaignx_list)))
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with campaigns repair_ocd_id_mismatch_damage: {e} "
                                 "".format(e=e))

    messages.add_message(request, messages.INFO,
                         "CampaignX entries analyzed: {campaignx_list_count:,}. "
                         "campaignx_politician_id_to_be_removed_count: {campaignx_politician_id_to_be_removed_count} "
                         "campaignx_politician_ids_removed_count: {campaignx_politician_ids_removed_count:,}. "
                         "bulk_update_count: {bulk_update_count:,}. "
                         "campaignx_list_remaining_count: {campaignx_list_remaining_count:,}. "
                         "status: {status}"
                         "".format(
                             bulk_update_count=len(bulk_update_campaignx_list),
                             campaignx_list_count=campaignx_list_count,
                             campaignx_list_remaining_count=campaignx_list_remaining_count,
                             campaignx_politician_ids_removed_count=campaignx_politician_ids_removed_count,
                             campaignx_politician_id_to_be_removed_count=campaignx_politician_id_to_be_removed_count,
                             status=status))

    return HttpResponseRedirect(reverse('campaign:campaignx_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "&show_ocd_id_state_mismatch=1"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    state_code=state_code))
