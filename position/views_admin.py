# position/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered
from .serializers import PositionSerializer
from candidate.models import CandidateCampaign
from django.core.urlresolvers import reverse
from django.contrib import messages
# from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from rest_framework.views import APIView
from rest_framework.response import Response
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportPositionDataView(APIView):
    def get(self, request, format=None):
        position_list = PositionEntered.objects.all()
        serializer = PositionSerializer(position_list, many=True)
        return Response(serializer.data)


# @login_required()  # Commented out while we are developing login process()
def position_list_view(request):
    messages_on_stage = get_messages(request)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    position_list = PositionEntered.objects.order_by('position_id')  # This order_by is temp
    if positive_value_exists(google_civic_election_id):
        position_list = PositionEntered.objects.filter(google_civic_election_id=google_civic_election_id)

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'position_list': position_list,
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'position/position_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def position_new_view(request):
    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'position/position_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def position_edit_view(request, position_id):
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


# @login_required()  # Commented out while we are developing login process()
def position_edit_process_view(request):
    """
    Process the new or edit position forms
    :param request:
    :return:
    """
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


# @login_required()  # Commented out while we are developing login process()
def position_summary_view(request, position_id):
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
    return render(request, 'position/position_summary.html', template_values)


def relink_candidates_measures_view(request):
    messages.add_message(request, messages.INFO, 'TO BE BUILT: relink_candidates_measures_view')
    return HttpResponseRedirect(reverse('position:position_list', args=()))

# # @login_required()  # Commented out while we are developing login process()
# def positions_display_list_related_to_candidate_campaign_any_position_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = ANY
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# # @login_required()  # Commented out while we are developing login process()
# def positions_display_list_related_to_candidate_campaign_supporters_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = SUPPORT
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# # @login_required()  # Commented out while we are developing login process()
# def positions_display_list_related_to_candidate_campaign_opposers_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = OPPOSE
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# # @login_required()  # Commented out while we are developing login process()
# def positions_display_list_related_to_candidate_campaign_information_only_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = INFORMATION_ONLY
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# # @login_required()  # Commented out while we are developing login process()
# def positions_display_list_related_to_candidate_campaign_deciders_view(request, candidate_campaign_id):
#     stance_we_are_looking_for = STILL_DECIDING
#     return positions_display_list_related_to_candidate_campaign(
#         request, candidate_campaign_id, stance_we_are_looking_for)


# # @login_required()  # Commented out while we are developing login process()
# def positions_display_list_related_to_candidate_campaign(request, candidate_campaign_id, stance_we_are_looking_for):
#     show_only_followed_positions = convert_to_int(request.GET.get('f', 0))
#     show_only_not_followed_positions = convert_to_int(request.GET.get('nf', 0))
#
#     messages_on_stage = get_messages(request)
#     candidate_campaign_id = convert_to_int(candidate_campaign_id)
#
#     position_list_manager = PositionListManager()
#     all_positions_list_for_candidate_campaign = \
#         position_list_manager.retrieve_all_positions_for_candidate_campaign(
#             candidate_campaign_id, stance_we_are_looking_for)
#
#     voter_device_id = get_voter_device_id(request)
#     voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
#
#     follow_organization_list_manager = FollowOrganizationList()
#     organizations_followed_by_voter = \
#         follow_organization_list_manager.retrieve_follow_organization_info_for_voter_simple_array(voter_id)
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
