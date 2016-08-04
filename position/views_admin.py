# position/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import positions_import_from_master_server
from .models import ANY_STANCE, PositionEntered
from .serializers import PositionSerializer
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from position.models import PositionListManager
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class PositionsSyncOutView(APIView):
    def get(self, request, format=None):
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

        position_list_manager = PositionListManager()
        public_only = True
        position_list = position_list_manager.retrieve_all_positions_for_election(google_civic_election_id, ANY_STANCE,
                                                                                  public_only)
        serializer = PositionSerializer(position_list, many=True)
        return Response(serializer.data)


@login_required
def positions_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.INFO, 'Google civic election id is required for Positions import.')
        return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                    str(google_civic_election_id) + "&state_code=" + str(state_code))

    results = positions_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Positions import completed. '
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
def position_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    position_list_manager = PositionListManager()

    if positive_value_exists(google_civic_election_id):
        public_only = True
        position_list = position_list_manager.retrieve_all_positions_for_election(google_civic_election_id, ANY_STANCE,
                                                                                  public_only)
    else:
        position_list = PositionEntered.objects.order_by('position_id')[:500]  # This order_by is temp

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'position_list': position_list,
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'position/position_list.html', template_values)


@login_required
def position_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'position/position_edit.html', template_values)


@login_required
def position_edit_view(request, position_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    position_id = convert_to_int(position_id)
    position_on_stage_found = False
    try:
        position_on_stage = CandidateCampaign.objects.get(id=position_id)
        position_on_stage_found = True
    except CandidateCampaign.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    if position_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'position': position_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'position/position_edit.html', template_values)


@login_required
def position_edit_process_view(request):  # TODO DALE I don't think this is correct
    """
    Process the new or edit position forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    position_id = convert_to_int(request.POST['position_id'])
    position_name = request.POST['position_name']
    twitter_handle = request.POST['twitter_handle']
    position_website = request.POST['position_website']

    # Check to see if this position is already being used anywhere
    position_on_stage_found = False
    try:
        position_query = CandidateCampaign.objects.filter(id=position_id)
        if len(position_query):
            position_on_stage = position_query[0]
            position_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if position_on_stage_found:
            # Update
            position_on_stage.position_name = position_name
            position_on_stage.twitter_handle = twitter_handle
            position_on_stage.position_website = position_website
            position_on_stage.save()
            messages.add_message(request, messages.INFO, 'CandidateCampaign updated.')
        else:
            # Create new
            position_on_stage = CandidateCampaign(
                position_name=position_name,
                twitter_handle=twitter_handle,
                position_website=position_website,
            )
            position_on_stage.save()
            messages.add_message(request, messages.INFO, 'New position saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save position.')

    return HttpResponseRedirect(reverse('position:position_list', args=()))


@login_required
def position_summary_view(request, position_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    position_id = convert_to_int(position_id)
    position_on_stage_found = False
    position_on_stage = PositionEntered()
    try:
        position_on_stage = PositionEntered.objects.get(id=position_id)
        position_on_stage_found = True
    except PositionEntered.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except PositionEntered.DoesNotExist:
        # This is fine, create new
        pass

    if position_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'position': position_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'position/position_summary.html', template_values)


@login_required
def relink_candidates_measures_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages.add_message(request, messages.INFO, 'TO BE BUILT: relink_candidates_measures_view')
    return HttpResponseRedirect(reverse('position:position_list', args=()))


@login_required
def position_delete_process_view(request):
    """
    Delete a position
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    position_id = convert_to_int(request.GET.get('position_id', 0))
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    # Retrieve this position
    position_on_stage_found = False
    position_on_stage = PositionEntered()
    organization_id = 0
    try:
        position_query = PositionEntered.objects.filter(id=position_id)
        if len(position_query):
            position_on_stage = position_query[0]
            organization_id = position_on_stage.organization_id
            position_on_stage_found = True
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not find position -- exception.')

    if not position_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find position.')
        return HttpResponseRedirect(reverse('position:position_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    try:
        if position_on_stage_found:
            # Delete
            position_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Position deleted.')
            if positive_value_exists(organization_id):
                return HttpResponseRedirect(reverse('organization:organization_position_list',
                                                    args=([organization_id])) +
                                            "?google_civic_election_id=" + str(google_civic_election_id))
        else:
            messages.add_message(request, messages.ERROR, 'Could not find position.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save position.')

    return HttpResponseRedirect(reverse('position:position_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))

# @login_required
# def positions_display_list_related_to_candidate_campaign_any_position_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = ANY
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# @login_required
# def positions_display_list_related_to_candidate_campaign_supporters_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = SUPPORT
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# @login_required
# def positions_display_list_related_to_candidate_campaign_opposers_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = OPPOSE
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# @login_required
# def positions_display_list_related_to_candidate_campaign_information_only_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = INFORMATION_ONLY
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# @login_required
# def positions_display_list_related_to_candidate_campaign_deciders_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = STILL_DECIDING
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# @login_required
# def positions_display_list_related_to_candidate_campaign(request, candidate_campaign_id, stance_we_are_looking_for):
#     show_only_followed_positions = convert_to_int(request.GET.get('f', 0))
#     show_only_not_followed_positions = convert_to_int(request.GET.get('nf', 0))
#
#     messages_on_stage = get_messages(request)
#     candidate_campaign_id = convert_to_int(candidate_campaign_id)
#
#     position_list_manager = PositionListManager()
#     public_positions = True  # The alternate is positions for friends-only
#     all_positions_list_for_candidate_campaign = \
#         position_list_manager.retrieve_all_positions_for_candidate_campaign(
#             public_positions, candidate_campaign_id, stance_we_are_looking_for)
#
#     voter_api_device_id = get_voter_api_device_id(request)
#     voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
#
#     follow_organization_list_manager = FollowOrganizationList()
#     organizations_followed_by_voter = \
#         follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)
#
#     if show_only_followed_positions == 1:
#         logger.debug("positions_display_list: show only followed positions")
#         list_to_display = position_list_manager.calculate_positions_followed_by_voter(
#             voter_id, all_positions_list_for_candidate_campaign, organizations_followed_by_voter)
#     elif show_only_not_followed_positions == 1:
#         logger.debug("positions_display_list: show only NOT followed positions")
#         list_to_display = position_list_manager.calculate_positions_not_followed_by_voter(
#             all_positions_list_for_candidate_campaign, organizations_followed_by_voter)
#     else:
#         list_to_display = all_positions_list_for_candidate_campaign
#
#     template_values = {
#         'error':                            True,
#         'messages_on_stage':                messages_on_stage,
#         'position_list':                    list_to_display,
#         'organizations_followed_by_voter':  organizations_followed_by_voter,
#     }
#     return render(request, 'position/voter_position_list.html', template_values)
