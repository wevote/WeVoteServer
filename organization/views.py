# organization/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponseRedirect, JsonResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.messages import get_messages
from django.shortcuts import redirect, render
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception, handle_record_not_saved_exception
from election_office_measure.models import CandidateCampaign, CandidateCampaignList
from follow.models import FollowOrganizationManager
from .models import Organization
from position.models import PositionEntered, PositionEnteredManager, INFORMATION_ONLY, OPPOSE, \
    STILL_DECIDING, SUPPORT
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.models import convert_to_int, get_voter_device_id


ORGANIZATION_STANCE_CHOICES = (
    (SUPPORT,           'We Support'),
    (OPPOSE,            'We Oppose'),
    (INFORMATION_ONLY,  'Information Only - No stance'),
    (STILL_DECIDING,    'We Are Still Deciding Our Stance'),
)

logger = wevote_functions.admin.get_logger(__name__)


def organization_list_view(request):
    messages_on_stage = get_messages(request)
    organization_list = Organization.objects.order_by('name')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'organization_list': organization_list,
    }
    return render(request, 'organization/organization_list.html', template_values)


def organization_new_view(request):
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'organization/organization_edit.html', template_values)


def organization_edit_view(request, organization_id):
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    organization_on_stage_found = False
    try:
        organization_on_stage = Organization.objects.get(id=organization_id)
        organization_on_stage_found = True
    except Organization.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Organization.DoesNotExist:
        # This is fine, create new
        pass

    if organization_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'organization': organization_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'organization/organization_edit.html', template_values)


def organization_edit_process_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    organization_id = convert_to_int(request.POST['organization_id'])
    organization_name = request.POST['organization_name']

    # Check to see if this organization is already being used anywhere
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if len(organization_query):
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if organization_on_stage_found:
            # Update
            organization_on_stage.name = organization_name
            organization_on_stage.save()
            messages.add_message(request, messages.INFO, 'Organization updated.')
        else:
            # Create new
            organization_on_stage = Organization(
                name=organization_name,
            )
            organization_on_stage.save()
            messages.add_message(request, messages.INFO, 'New organization saved.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save organization.')

    return HttpResponseRedirect(reverse('organization:organization_list', args=()))


def organization_position_list_view(request, organization_id):
    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    # election_id = 1  # TODO We will need to provide the election_id somehow, perhaps as a global variable?
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if len(organization_query):
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        organization_on_stage_found = False

    if not organization_on_stage_found:
        messages.add_message(request, messages.ERROR,
                             'Could not find organization when trying to retrieve positions.')
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))
    else:
        organization_position_list_found = False
        try:
            organization_position_list = PositionEntered.objects.order_by('stance')
            organization_position_list = organization_position_list.filter(organization_id=organization_id)
            if len(organization_position_list):
                organization_position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if organization_position_list_found:
            template_values = {
                'messages_on_stage': messages_on_stage,
                'organization': organization_on_stage,
                'organization_position_list': organization_position_list,
            }
        else:
            template_values = {
                'messages_on_stage': messages_on_stage,
                'organization': organization_on_stage,
            }
    return render(request, 'organization/organization_position_list.html', template_values)


def organization_add_new_position_form_view(request, organization_id):
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    all_is_well = True
    organization_on_stage_found = False
    try:
        organization_on_stage = Organization.objects.get(id=organization_id)
        organization_on_stage_found = True
    except Organization.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Organization.DoesNotExist:
        # This is fine, create new
        pass

    if not organization_on_stage_found:
        messages.add_message(request, messages.INFO,
                             'Could not find organization when trying to create a new position.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    # Prepare a drop down of candidates competing in this election
    candidate_campaign_list = CandidateCampaignList()
    candidate_campaigns_for_this_election_list \
        = candidate_campaign_list.retrieve_candidate_campaigns_for_this_election_list()

    if all_is_well:
        template_values = {
            'candidate_campaigns_for_this_election_list':   candidate_campaigns_for_this_election_list,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position_candidate_campaign_id':  0,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
            'stance_selected':                              SUPPORT,  # Default stance
        }
    return render(request, 'organization/organization_position_edit.html', template_values)


def organization_delete_existing_position_process_form_view(request, organization_id, position_id):
    """

    :param request:
    :param organization_id:
    :param position_id:
    :return:
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    organization_id = convert_to_int(organization_id)
    position_id = convert_to_int(position_id)

    # Get the existing position
    organization_position_on_stage_found = False
    if position_id > 0:
        organization_position_on_stage = PositionEntered()
        organization_position_on_stage_found = False
        position_entered_manager = PositionEnteredManager()
        results = position_entered_manager.retrieve_position_from_id(position_id)
        if results['position_found']:
            organization_position_on_stage_found = True
            organization_position_on_stage = results['position']

    if not organization_position_on_stage_found:
        messages.add_message(request, messages.INFO,
                             "Could not find this organization's position when trying to delete.")
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    try:
        organization_position_on_stage.delete()
    except Exception as e:
        handle_record_not_deleted_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR,
                             'Could not delete position.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    messages.add_message(request, messages.INFO,
                         'Position deleted.')
    return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))


def organization_edit_existing_position_form_view(request, organization_id, position_id):
    """
    In edit, you can only change your stance and comments, not who or what the position is about
    :param request:
    :param organization_id:
    :param position_id:
    :return:
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    position_id = convert_to_int(position_id)
    organization_on_stage_found = False
    try:
        organization_on_stage = Organization.objects.get(id=organization_id)
        organization_on_stage_found = True
    except Organization.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Organization.DoesNotExist:
        # This is fine, create new
        pass

    if not organization_on_stage_found:
        messages.add_message(request, messages.INFO,
                             'Could not find organization when trying to edit a position.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    # Get the existing position
    organization_position_on_stage = PositionEntered()
    organization_position_on_stage_found = False
    position_entered_manager = PositionEnteredManager()
    results = position_entered_manager.retrieve_position_from_id(position_id)
    if results['position_found']:
        organization_position_on_stage_found = True
        organization_position_on_stage = results['position']

    if not organization_position_on_stage_found:
        messages.add_message(request, messages.INFO,
                             'Could not find organization position when trying to edit.')
        return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))

    # Note: We have access to the candidate campaign through organization_position_on_stage.candidate_campaign

    if organization_position_on_stage_found:
        template_values = {
            'is_in_edit_mode':                              True,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position':                        organization_position_on_stage,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
            'stance_selected':                              organization_position_on_stage.stance,
        }

    return render(request, 'organization/organization_position_edit.html', template_values)


def organization_save_new_or_edit_existing_position_process_form_view(request):
    """

    :param request:
    :return:
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    organization_id = convert_to_int(request.POST['organization_id'])
    position_id = convert_to_int(request.POST['position_id'])
    candidate_campaign_id = convert_to_int(request.POST['candidate_campaign_id'])
    measure_campaign_id = convert_to_int(request.POST['measure_campaign_id'])
    stance = request.POST.get('stance', SUPPORT)  # Set a default if stance comes in empty
    statement_text = request.POST.get('statement_text', '')  # Set a default if stance comes in empty
    more_info_url = request.POST.get('more_info_url', '')

    # Make sure this is a valid organization before we try to save a position
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if len(organization_query):
            # organization_on_stage = organization_query[0]
            organization_on_stage_found = True
    except Exception as e:
        # If we can't retrieve the organization, we cannot proceed
        handle_record_not_found_exception(e, logger=logger)

    if not organization_on_stage_found:
        messages.add_message(
            request, messages.ERROR,
            "Could not find the organization when trying to create or edit a new position.")
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))

    # Now retrieve the CandidateCampaign or the MeasureCampaign so we can save it with the Position
    # We need either candidate_campaign_id or measure_campaign_id
    if candidate_campaign_id:
        try:
            candidate_campaign_on_stage = CandidateCampaign.objects.get(id=candidate_campaign_id)
            candidate_campaign_on_stage_found = True
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except CandidateCampaign.DoesNotExist as e:
            handle_record_not_found_exception(e, logger=logger)

        if not candidate_campaign_on_stage_found:
            messages.add_message(
                request, messages.ERROR,
                "Could not find Candidate's campaign when trying to create or edit a new position.")
            if position_id:
                return HttpResponseRedirect(
                    reverse('organization:organization_position_edit', args=([organization_id], [position_id]))
                )
            else:
                return HttpResponseRedirect(
                    reverse('organization:organization_position_new', args=([organization_id]))
                )
    elif measure_campaign_id:
        logger.warn("measure_campaign_id FOUND. Look for MeasureCampaign here.")

    else:
        logger.warn("Neither candidate_campaign_id nor measure_campaign_id found")
        messages.add_message(
            request, messages.ERROR,
            "Unable to find either Candidate or Measure.")
        return HttpResponseRedirect(
            reverse('organization:organization_position_list', args=([organization_id]))
        )

    organization_position_on_stage_found = False
    logger.info("position_id: {position_id}".format(position_id=position_id))

    # Retrieve position from position_id if it exists already
    if position_id > 0:
        position_entered_manager = PositionEnteredManager()
        results = position_entered_manager.retrieve_position_from_id(position_id)
        if results['position_found']:
            organization_position_on_stage_found = True
            organization_position_on_stage = results['position']

    if not organization_position_on_stage_found:
        # If a position_id hasn't been passed in, then we are trying to create a new position.
        # Check to make sure a position for this org and candidate doesn't already exist

        position_entered_manager = PositionEnteredManager()
        results = position_entered_manager.retrieve_organization_candidate_campaign_position(
            organization_id, candidate_campaign_id)

        if results['MultipleObjectsReturned']:
            messages.add_message(
                request, messages.ERROR,
                "We found more than one existing positions for this candidate. Please delete all but one position.")
            return HttpResponseRedirect(
                reverse('organization:organization_position_list', args=([organization_id]))
            )
        elif results['position_found']:
            organization_position_on_stage_found = True
            organization_position_on_stage = results['position']

    # Now save existing, or create new
    try:
        if organization_position_on_stage_found:
            # Update the position
            organization_position_on_stage.stance = stance
            organization_position_on_stage.statement_text = statement_text
            organization_position_on_stage.more_info_url = more_info_url
            organization_position_on_stage.save()
            messages.add_message(
                request, messages.INFO,
                "Position on {candidate_name} updated.".format(
                    candidate_name=candidate_campaign_on_stage.candidate_name))
        else:
            # Create new
            organization_position_on_stage = PositionEntered(
                organization_id=organization_id,
                candidate_campaign_id=candidate_campaign_on_stage.id,
                stance=stance,
                statement_text=statement_text,
                more_info_url=more_info_url,
            )
            organization_position_on_stage.save()
            messages.add_message(
                request, messages.INFO,
                "New position on {candidate_name} saved.".format(
                    candidate_name=candidate_campaign_on_stage.candidate_name))
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        logger.error("Problem saving PositionEntered for CandidateCampaign")

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=([organization_id])))


def organization_follow_view(request, organization_id):
    logger.debug("organization_follow_view {organization_id}".format(
        organization_id=organization_id
    ))
    voter_device_id = get_voter_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

    follow_organization_manager = FollowOrganizationManager()
    results = follow_organization_manager.toggle_on_voter_following_organization(voter_id, organization_id)
    if results['success']:
        return JsonResponse({0: "success"})
    else:
        return JsonResponse({0: "failure"})


def organization_unfollow_view(request, organization_id):
    logger.debug("organization_unfollow_view {organization_id}".format(
        organization_id=organization_id
    ))
    voter_device_id = get_voter_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

    follow_organization_manager = FollowOrganizationManager()
    results = follow_organization_manager.toggle_off_voter_following_organization(voter_id, organization_id)
    if results['success']:
        return JsonResponse({0: "success"})
    else:
        return JsonResponse({0: "failure"})
