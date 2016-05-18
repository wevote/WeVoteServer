# office/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import offices_import_from_master_server
from .models import ContestOffice
from .serializers import ContestOfficeSerializer
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign, fetch_candidate_count_for_office
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from office.models import ContestOfficeListManager
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class OfficesSyncOutView(APIView):
    def get(self, request, format=None):
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

        contest_office_list = ContestOffice.objects.all()
        if positive_value_exists(google_civic_election_id):
            contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
        serializer = ContestOfficeSerializer(contest_office_list, many=True)
        return Response(serializer.data)


@login_required
def offices_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = offices_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Offices import completed. '
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
def office_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    office_list_manager = ContestOfficeListManager()
    updated_office_list = []
    results = office_list_manager.retrieve_all_offices_for_upcoming_election(google_civic_election_id, True)
    if results['office_list_found']:
        office_list = results['office_list_objects']
        for office in office_list:
            office.candidate_count = fetch_candidate_count_for_office(office.id)
            updated_office_list.append(office)

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'office_list': updated_office_list,
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'office/office_list.html', template_values)


@login_required
def office_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    office_list_manager = ContestOfficeListManager()
    updated_office_list = []
    results = office_list_manager.retrieve_all_offices_for_upcoming_election(google_civic_election_id, True)
    if results['office_list_found']:
        office_list = results['office_list_objects']
        for office in office_list:
            office.candidate_count = fetch_candidate_count_for_office(office.id)
            updated_office_list.append(office)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'office_list':              updated_office_list,
    }
    return render(request, 'office/office_edit.html', template_values)


@login_required
def office_edit_view(request, office_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_id = convert_to_int(office_id)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    office_on_stage_found = False
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    if office_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'office':                   office_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'office/office_edit.html', template_values)


@login_required
def office_edit_process_view(request):
    """
    Process the new or edit office forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_id = convert_to_int(request.POST.get('office_id', 0))
    office_name = request.POST.get('office_name', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    primary_party = request.POST.get('primary_party', False)

    election_state = ''
    if google_civic_election_id:
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            election_state = election.get_election_state()

    # Check to see if this office is already in the database
    office_on_stage_found = False
    try:
        office_query = ContestOffice.objects.filter(id=office_id)
        if len(office_query):
            office_on_stage = office_query[0]
            office_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if office_on_stage_found:
            # Update
            if convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and office_name is not False:
                office_on_stage.office_name = office_name
            if convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and primary_party is not False:
                office_on_stage.primary_party = primary_party
            if positive_value_exists(election_state):
                office_on_stage.state_code = election_state
            office_on_stage.save()
            messages.add_message(request, messages.INFO, 'Office updated.')
            google_civic_election_id = office_on_stage.google_civic_election_id

            return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                        "?google_civic_election_id=" + google_civic_election_id)
        else:
            # Create new
            office_on_stage = ContestOffice(
                office_name=office_name,
                google_civic_election_id=google_civic_election_id,
                state_code=election_state,
            )
            if convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and primary_party is not False:
                office_on_stage.primary_party = primary_party
            office_on_stage.save()
            messages.add_message(request, messages.INFO, 'New office saved.')

            # Come back to the "Create New Office" page
            new_office_id = 0
            return HttpResponseRedirect(reverse('office:office_new', args=()) +
                                        "?google_civic_election_id=" + google_civic_election_id)
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save office.')

    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                "?google_civic_election_id=" + google_civic_election_id)


@login_required
def office_summary_view(request, office_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_id = convert_to_int(office_id)
    office_on_stage_found = False
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
        google_civic_election_id = office_on_stage.google_civic_election_id
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    try:
        candidate_list = CandidateCampaign.objects.filter(contest_office_id=office_id)
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        candidate_list = candidate_list.order_by('candidate_name')
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')

    if office_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'office': office_on_stage,
            'candidate_list': candidate_list,
            'election_list': election_list,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'office/office_summary.html', template_values)


@login_required
def office_delete_process_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_id = convert_to_int(request.GET.get('office_id', 0))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    office_on_stage_found = False
    office_on_stage = ContestOffice()
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
        google_civic_election_id = office_on_stage.google_civic_election_id
    except ContestOffice.MultipleObjectsReturned as e:
        pass
    except ContestOffice.DoesNotExist:
        pass

    candidates_found_for_this_office = False
    if office_on_stage_found:
        try:
            candidate_list = CandidateCampaign.objects.filter(contest_office_id=office_id)
            # if positive_value_exists(google_civic_election_id):
            #     candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
            candidate_list = candidate_list.order_by('candidate_name')
            if len(candidate_list):
                candidates_found_for_this_office = True
        except CandidateCampaign.DoesNotExist:
            pass

    try:
        if not candidates_found_for_this_office:
            # Delete the office
            office_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Office deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'candidates still attached to this office.')
            return HttpResponseRedirect(reverse('office:office_summary', args=(office_id,)))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete office -- exception.')
        return HttpResponseRedirect(reverse('office:office_summary', args=(office_id,)))

    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))
