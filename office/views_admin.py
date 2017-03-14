# office/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import offices_import_from_master_server
from .models import ContestOffice
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
from position.models import OPPOSE, PositionListManager, SUPPORT
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from django.http import HttpResponse
import json

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
# class OfficesSyncOutView(APIView):
#     def get(self, request, format=None):
def offices_sync_out_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    try:
        contest_office_list = ContestOffice.objects.all()
        if positive_value_exists(google_civic_election_id):
            contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            contest_office_list = contest_office_list.filter(state_code__iexact=state_code)
        # serializer = ContestOfficeSerializer(contest_office_list, many=True)
        # return Response(serializer.data)
        # get the data using values_list
        contest_office_list_dict = contest_office_list.values('we_vote_id', 'office_name', 'google_civic_election_id',
                                                              'ocd_division_id', 'maplight_id', 'ballotpedia_id',
                                                              'wikipedia_id', 'number_voting_for', 'number_elected',
                                                              'state_code', 'primary_party', 'district_name',
                                                              'district_scope', 'district_id', 'contest_level0',
                                                              'contest_level1', 'contest_level2',
                                                              'electorate_specifications', 'special', 'state_code')
        if contest_office_list_dict:
            contest_office_list_json = list(contest_office_list_dict)
            return HttpResponse(json.dumps(contest_office_list_json), content_type='application/json')
    except ContestOffice.DoesNotExist:
        pass

    json_data = {
        'success': False,
        'status': 'CONTEST_OFFICE_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def offices_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = offices_import_from_master_server(request, google_civic_election_id, state_code)

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

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)

    office_list_manager = ContestOfficeListManager()
    updated_office_list = []
    office_list_count = 0
    results = office_list_manager.retrieve_all_offices_for_upcoming_election(google_civic_election_id, state_code, True)
    if results['office_list_found']:
        office_list = results['office_list_objects']
        for office in office_list:
            office.candidate_count = fetch_candidate_count_for_office(office.id)
            updated_office_list.append(office)

            office_list_count = len(updated_office_list)

    election_list = Election.objects.order_by('-election_day_text')

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    status_print_list = ""
    status_print_list += "office_list_count: " + \
                         str(office_list_count) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_list':              updated_office_list,
        'election_list':            election_list,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'office/office_list.html', template_values)


@login_required
def office_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    office_list_manager = ContestOfficeListManager()
    updated_office_list = []
    results = office_list_manager.retrieve_all_offices_for_upcoming_election(google_civic_election_id, state_code, True)
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
    google_civic_office_name = request.POST.get('google_civic_office_name', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    primary_party = request.POST.get('primary_party', False)
    state_code = request.POST.get('state_code', False)

    election_state = ''
    if state_code is not False:
        election_state = state_code
    elif google_civic_election_id:
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
            # Removed for now: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
            if office_name is not False:
                office_on_stage.office_name = office_name
            if google_civic_office_name is not False:
                office_on_stage.google_civic_office_name = google_civic_office_name
            if primary_party is not False:
                office_on_stage.primary_party = primary_party
            if positive_value_exists(election_state):
                office_on_stage.state_code = election_state
            office_on_stage.save()
            office_on_stage_id = office_on_stage.id
            messages.add_message(request, messages.INFO, 'Office updated.')
            google_civic_election_id = office_on_stage.google_civic_election_id

            return HttpResponseRedirect(reverse('office:office_summary', args=(office_on_stage_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id))
        else:
            # Create new
            office_on_stage = ContestOffice(
                office_name=office_name,
                google_civic_election_id=google_civic_election_id,
                state_code=election_state,
            )
            # Removing this limitation: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
            if primary_party is not False:
                office_on_stage.primary_party = primary_party
            office_on_stage.save()
            messages.add_message(request, messages.INFO, 'New office saved.')

            # Come back to the "Create New Office" page
            return HttpResponseRedirect(reverse('office:office_new', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id))
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
    state_code = request.GET.get('state_code', "")
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
        google_civic_election_id = office_on_stage.google_civic_election_id
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    candidate_list_modified = []
    position_list_manager = PositionListManager()
    try:
        candidate_list = CandidateCampaign.objects.filter(contest_office_id=office_id)
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        candidate_list = candidate_list.order_by('candidate_name')
        support_total = 0
        for one_candidate in candidate_list:
            # Find the count of Voters that support this candidate (Organizations are not included in this)
            one_candidate.support_count = position_list_manager.fetch_voter_positions_count_for_candidate_campaign(
                one_candidate.id, "", SUPPORT)
            one_candidate.oppose_count = position_list_manager.fetch_voter_positions_count_for_candidate_campaign(
                one_candidate.id, "", OPPOSE)
            support_total += one_candidate.support_count

        for one_candidate in candidate_list:
            if positive_value_exists(support_total):
                percentage_of_support_number = one_candidate.support_count / support_total * 100
                one_candidate.percentage_of_support = "%.1f" % percentage_of_support_number

            candidate_list_modified.append(one_candidate)

    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')

    if positive_value_exists(google_civic_election_id):
        election = Election.objects.get(google_civic_election_id=google_civic_election_id)

    if office_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'office':                   office_on_stage,
            'candidate_list':           candidate_list_modified,
            'state_code':               state_code,
            'election':                 election,
            'election_list':            election_list,
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
