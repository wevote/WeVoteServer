# organization/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import organizations_import_from_sample_file
from .models import Organization
from .serializers import OrganizationSerializer
from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception, handle_record_not_saved_exception
from candidate.models import CandidateCampaign, CandidateCampaignList
from election.models import Election
from organization.models import OrganizationManager
from position.models import PositionEntered, PositionEnteredManager, ANY_STANCE, INFORMATION_ONLY, OPPOSE, \
    STILL_DECIDING, SUPPORT
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
from voter_guide.models import VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP


ORGANIZATION_STANCE_CHOICES = (
    (SUPPORT,           'We Support'),
    (OPPOSE,            'We Oppose'),
    (INFORMATION_ONLY,  'Information Only - No stance'),
    (STILL_DECIDING,    'We Are Still Deciding Our Stance'),
)

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportOrganizationDataView(APIView):
    def get(self, request, format=None):
        organization_list = Organization.objects.all()
        serializer = OrganizationSerializer(organization_list, many=True)
        return Response(serializer.data)


@login_required
def organization_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_state_code = request.GET.get('organization_state')

    messages_on_stage = get_messages(request)
    organization_list_query = Organization.objects.all()
    if positive_value_exists(organization_state_code):
        organization_list_query = organization_list_query.filter(state_served_code__iexact=organization_state_code)
    organization_list_query = organization_list_query.order_by('organization_name')

    organization_list = organization_list_query

    template_values = {
        'messages_on_stage':    messages_on_stage,
        'organization_list':    organization_list,
        'state_list':           STATE_CODE_MAP,
        'organization_state':   organization_state_code,
    }
    return render(request, 'organization/organization_list.html', template_values)


@login_required
def organization_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'organization/organization_edit.html', template_values)


@login_required
def organization_edit_view(request, organization_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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


@login_required
def organization_edit_process_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_id = convert_to_int(request.POST['organization_id'])
    organization_name = request.POST['organization_name']
    organization_twitter_handle = request.POST.get('organization_twitter_handle', '')
    organization_facebook = request.POST.get('organization_facebook', '')
    organization_website = request.POST['organization_website']
    wikipedia_page_title = request.POST.get('wikipedia_page_title', '')
    wikipedia_photo_url = request.POST.get('wikipedia_photo_url', '')

    # Check to see if this organization is already being used anywhere
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if organization_query.count():
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if organization_on_stage_found:
            # Update
            organization_on_stage.organization_name = organization_name
            organization_on_stage.organization_twitter_handle = organization_twitter_handle
            organization_on_stage.organization_facebook = organization_facebook
            organization_on_stage.organization_website = organization_website
            organization_on_stage.wikipedia_page_title = wikipedia_page_title
            organization_on_stage.wikipedia_photo_url = wikipedia_photo_url
            organization_on_stage.save()
            organization_id = organization_on_stage.id
            messages.add_message(request, messages.INFO, 'Organization updated.')
            return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))
        else:
            # Create new
            organization_on_stage = Organization(
                organization_name=organization_name,
                organization_twitter_handle=organization_twitter_handle,
                organization_facebook=organization_facebook,
                organization_website=organization_website,
                wikipedia_page_title=wikipedia_page_title,
                wikipedia_photo_url=wikipedia_photo_url,
            )
            organization_on_stage.save()
            organization_id = organization_on_stage.id
            messages.add_message(request, messages.INFO, 'New organization saved.')
            return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_id,)))
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save organization.'
                                                      ' {error} [type: {error_type}]'.format(error=e.message,
                                                                                             error_type=type(e)))

    return HttpResponseRedirect(reverse('organization:organization_list', args=()))


@login_required
def organization_position_list_view(request, organization_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    organization_id = convert_to_int(organization_id)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if organization_query.count():
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
            if positive_value_exists(google_civic_election_id):
                organization_position_list = organization_position_list.filter(
                    google_civic_election_id=google_civic_election_id)
            if len(organization_position_list):
                organization_position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        election_list = Election.objects.order_by('-election_day_text')

        if organization_position_list_found:
            template_values = {
                'messages_on_stage': messages_on_stage,
                'organization': organization_on_stage,
                'organization_position_list': organization_position_list,
                'election_list': election_list,
                'google_civic_election_id': google_civic_election_id,
            }
        else:
            template_values = {
                'messages_on_stage': messages_on_stage,
                'organization': organization_on_stage,
                'election_list': election_list,
                'google_civic_election_id': google_civic_election_id,
            }
    return render(request, 'organization/organization_position_list.html', template_values)


@login_required
def organization_add_new_position_form_view(request, organization_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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
        election_list = Election.objects.all()
        template_values = {
            'candidate_campaigns_for_this_election_list':   candidate_campaigns_for_this_election_list,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position_candidate_campaign_id':  0,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
            'stance_selected':                              SUPPORT,  # Default stance
            'election_list':                                election_list,
        }
    return render(request, 'organization/organization_position_edit.html', template_values)


@login_required
def organization_delete_existing_position_process_form_view(request, organization_id, position_id):
    """

    :param request:
    :param organization_id:
    :param position_id:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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


@login_required
def organization_edit_existing_position_form_view(request, organization_id, position_id):
    """
    In edit, you can only change your stance and comments, not who or what the position is about
    :param request:
    :param organization_id:
    :param position_id:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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

    election_list = Election.objects.all()

    if organization_position_on_stage_found:
        template_values = {
            'is_in_edit_mode':                              True,
            'messages_on_stage':                            messages_on_stage,
            'organization':                                 organization_on_stage,
            'organization_position':                        organization_position_on_stage,
            'possible_stances_list':                        ORGANIZATION_STANCE_CHOICES,
            'stance_selected':                              organization_position_on_stage.stance,
            'election_list':                                election_list,
        }

    return render(request, 'organization/organization_position_edit.html', template_values)


@login_required
def organization_save_new_or_edit_existing_position_process_form_view(request):
    """

    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.POST['google_civic_election_id'])
    organization_id = convert_to_int(request.POST['organization_id'])
    position_id = convert_to_int(request.POST['position_id'])
    candidate_campaign_id = convert_to_int(request.POST['candidate_campaign_id'])
    contest_measure_id = convert_to_int(request.POST['contest_measure_id'])
    stance = request.POST.get('stance', SUPPORT)  # Set a default if stance comes in empty
    statement_text = request.POST.get('statement_text', '')  # Set a default if stance comes in empty
    more_info_url = request.POST.get('more_info_url', '')

    # Make sure this is a valid organization before we try to save a position
    organization_on_stage_found = False
    try:
        organization_query = Organization.objects.filter(id=organization_id)
        if organization_query.count():
            organization_on_stage = organization_query[0]
            organization_on_stage_found = True
    except Exception as e:
        # If we can't retrieve the organization, we cannot proceed
        handle_record_not_found_exception(e, logger=logger)

    if not organization_on_stage_found:
        messages.add_message(
            request, messages.ERROR,
            "Could not find the organization when trying to create or edit a new position.")
        return HttpResponseRedirect(reverse('organization:organization_list', args=()))

    # Now retrieve the CandidateCampaign or the ContestMeasure so we can save it with the Position
    # We need either candidate_campaign_id or contest_measure_id
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
    elif contest_measure_id:
        logger.warn("contest_measure_id FOUND. Look for ContestMeasure here.")

    else:
        logger.warn("Neither candidate_campaign_id nor contest_measure_id found")
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
    success = False
    try:
        if organization_position_on_stage_found:
            # Update the position
            organization_position_on_stage.stance = stance
            organization_position_on_stage.google_civic_election_id = google_civic_election_id
            organization_position_on_stage.more_info_url = more_info_url
            organization_position_on_stage.statement_text = statement_text
            if not positive_value_exists(organization_position_on_stage.organization_we_vote_id):
                organization_position_on_stage.organization_we_vote_id = organization_on_stage.we_vote_id
            if not positive_value_exists(organization_position_on_stage.candidate_campaign_we_vote_id):
                organization_position_on_stage.candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
            if not positive_value_exists(organization_position_on_stage.google_civic_candidate_name):
                organization_position_on_stage.google_civic_candidate_name = \
                    candidate_campaign_on_stage.google_civic_candidate_name
            organization_position_on_stage.save()
            success = True
            messages.add_message(
                request, messages.INFO,
                "Position on {candidate_name} updated.".format(
                    candidate_name=candidate_campaign_on_stage.candidate_name))
        else:
            # Create new
            organization_position_on_stage = PositionEntered(
                organization_id=organization_id,
                organization_we_vote_id=organization_on_stage.we_vote_id,
                candidate_campaign_id=candidate_campaign_on_stage.id,
                candidate_campaign_we_vote_id=candidate_campaign_on_stage.we_vote_id,
                # Save candidate_campaign_on_stage so we can re-link candidates to positions if we_vote_id is lost
                google_civic_candidate_name=candidate_campaign_on_stage.google_civic_candidate_name,
                google_civic_election_id=google_civic_election_id,
                stance=stance,
                statement_text=statement_text,
                more_info_url=more_info_url,
            )
            organization_position_on_stage.save()
            success = True
            messages.add_message(
                request, messages.INFO,
                "New position on {candidate_name} saved.".format(
                    candidate_name=candidate_campaign_on_stage.candidate_name))
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        logger.error("Problem saving PositionEntered for CandidateCampaign")

    # If the position was saved, then update the voter_guide entry
    if success:
        voter_guide_manager = VoterGuideManager()
        results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
            organization_on_stage.we_vote_id, google_civic_election_id)
        # if results['success']:

    return HttpResponseRedirect(reverse('organization:organization_position_list', args=(organization_on_stage.id,)))


# def retrieve_organization_logos_from_wikipedia_view(request, organization_id):
#     authority_required = {'verified_volunteer'}  # admin, verified_volunteer
#     if not voter_has_authority(request, authority_required):
#         return redirect_to_sign_in_page(request, authority_required)
#
#     organization_id = convert_to_int(organization_id)
#     organization_manager = OrganizationManager()
#     results = organization_manager.retrieve_organization(organization_id)
#     if results['success']:
#         organization_on_stage = results['organization']
#         organization_on_stage.retrieve_organization_logos_from_wikipedia()
#
#     return HttpResponseRedirect(reverse('organization:organization_edit', args=(organization_on_stage.id,)))
