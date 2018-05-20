# elected_office/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ElectedOffice, ElectedOfficeListManager
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from django.db.models import Q
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from position.models import PositionListManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP

OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def elected_office_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_all_elections = request.GET.get('show_all_elections', False)
    elected_office_search = request.GET.get('elected_office_search', '')

    elected_office_list_found = False
    elected_office_list = []
    updated_elected_office_list = []
    elected_office_list_count = 0
    try:
        elected_office_queryset = ElectedOffice.objects.all()
        if positive_value_exists(google_civic_election_id):
            elected_office_queryset = elected_office_queryset.filter(google_civic_election_id=google_civic_election_id)
        else:
            # TODO Limit this search to upcoming_elections only
            pass
        if positive_value_exists(state_code):
            elected_office_queryset = elected_office_queryset.filter(state_code__iexact=state_code)
        elected_office_queryset = elected_office_queryset.order_by("elected_office_name")

        if positive_value_exists(elected_office_search):
            search_words = elected_office_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(elected_office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(wikipedia_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    elected_office_queryset = elected_office_queryset.filter(final_filters)

        elected_office_list = list(elected_office_queryset)

        if len(elected_office_list):
            elected_office_list_found = True
            status = 'ELECTED_OFFICES_RETRIEVED'
            success = True
        else:
            status = 'NO_ELECTED_OFFICES_RETRIEVED'
            success = True
    except ElectedOffice.DoesNotExist:
        # No elected_offices found. Not a problem.
        status = 'NO_ELECTED_OFFICES_FOUND_DoesNotExist'
        elected_office_list = []
        success = True
    except Exception as e:
        status = 'FAILED retrieve_all_elected_offices_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    if elected_office_list_found:
        for elected_office in elected_office_list:
            # TODO fetch elected officials count instead candidate
            # elected_office.candidate_count = fetch_candidate_count_for_office(elected_office.id)
            updated_elected_office_list.append(elected_office)

            elected_office_list_count = len(updated_elected_office_list)
            if elected_office_list_count >= 500:
                # Limit to showing only 500
                break

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    status_print_list = ""
    status_print_list += "elected_office_list_count: " + \
                         str(elected_office_list_count) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'elected_office_list':      updated_elected_office_list,
        'elected_office_search':    elected_office_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'show_all_elections':       show_all_elections,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'elected_office/elected_office_list.html', template_values)


@login_required
def elected_office_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    elected_office_list_manager = ElectedOfficeListManager()
    updated_elected_office_list = []
    results = elected_office_list_manager.retrieve_all_elected_offices_for_upcoming_election(
        google_civic_election_id, state_code, True)
    if results['elected_office_list_found']:
        elected_office_list = results['elected_office_list_objects']
        # TODO fetch elected officials count instead candidate
        # for elected_office in elected_office_list:
        #     elected_office.candidate_count = fetch_candidate_count_for_office(elected_office.id)
        #     updated_elected_office_list.append(elected_office)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'elected_office_list':      updated_elected_office_list,
    }
    return render(request, 'elected_office/elected_office_edit.html', template_values)


@login_required
def elected_office_edit_view(request, elected_office_id=0, elected_office_we_vote_id=""):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    elected_office_id = convert_to_int(elected_office_id)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    elected_office_on_stage = ElectedOffice()
    elected_office_on_stage_found = False
    try:
        if positive_value_exists(elected_office_id):
            elected_office_on_stage = ElectedOffice.objects.get(id=elected_office_id)
        else:
            elected_office_on_stage = ElectedOffice.objects.get(we_vote_id=elected_office_we_vote_id)
        elected_office_on_stage_found = True
    except ElectedOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ElectedOffice.DoesNotExist:
        # This is fine, create new
        pass

    if elected_office_on_stage_found:
        # Was a elected_office_merge_possibility_found?
        elected_office_on_stage.contest_office_merge_possibility_found = True  # TODO DALE Make dynamic
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'elected_office':           elected_office_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'elected_office/elected_office_edit.html', template_values)


@login_required
def elected_office_summary_view(request, elected_office_id):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    elected_office_id = convert_to_int(elected_office_id)
    elected_office_on_stage_found = False
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', "")
    try:
        elected_office_on_stage = ElectedOffice.objects.get(id=elected_office_id)
        elected_office_on_stage_found = True
        google_civic_election_id = elected_office_on_stage.google_civic_election_id
    except ElectedOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ElectedOffice.DoesNotExist:
        # This is fine, create new
        pass

    candidate_list_modified = []
    position_list_manager = PositionListManager()

    # TODO Get elected officials count instead candidate
    # try:
    #     candidate_list = CandidateCampaign.objects.filter(contest_office_id=elected_office_id)
    #     if positive_value_exists(google_civic_election_id):
    #         candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
    #     candidate_list = candidate_list.order_by('candidate_name')
    #     support_total = 0
    #     for one_candidate in candidate_list:
    #         # Find the count of Voters that support this candidate (Organizations are not included in this)
    #         one_candidate.support_count = position_list_manager.fetch_voter_positions_count_for_candidate_campaign(
    #             one_candidate.id, "", SUPPORT)
    #         one_candidate.oppose_count = position_list_manager.fetch_voter_positions_count_for_candidate_campaign(
    #             one_candidate.id, "", OPPOSE)
    #         support_total += one_candidate.support_count
    #
    #     for one_candidate in candidate_list:
    #         if positive_value_exists(support_total):
    #             percentage_of_support_number = one_candidate.support_count / support_total * 100
    #             one_candidate.percentage_of_support = "%.1f" % percentage_of_support_number
    #
    #         candidate_list_modified.append(one_candidate)
    #
    # except CandidateCampaign.DoesNotExist:
    #     # This is fine, create new
    #     pass

    election_list = Election.objects.order_by('-election_day_text')

    if positive_value_exists(google_civic_election_id):
        election = Election.objects.get(google_civic_election_id=google_civic_election_id)

    if elected_office_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'elected_office':           elected_office_on_stage,
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
    return render(request, 'elected_office/elected_office_summary.html', template_values)


@login_required
def elected_office_edit_process_view(request):
    """
    Process the new or edit elected office forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    elected_office_id = convert_to_int(request.POST.get('elected_office_id', 0))
    elected_office_name = request.POST.get('elected_office_name', False)
    google_civic_elected_office_name = request.POST.get('google_civic_elected_office_name', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    ocd_division_id = request.POST.get('ocd_division_id', False)
    primary_party = request.POST.get('primary_party', False)
    state_code = request.POST.get('state_code', False)
    # ballotpedia_office_id = request.POST.get('ballotpedia_office_id', False)
    # ballotpedia_office_name = request.POST.get('ballotpedia_office_name', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    redirect_to_elected_office_list = convert_to_int(request.POST['redirect_to_elected_office_list'])

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
    elected_office_on_stage_found = False
    try:
        elected_office_query = ElectedOffice.objects.filter(id=elected_office_id)
        if len(elected_office_query):
            elected_office_on_stage = elected_office_query[0]
            elected_office_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if elected_office_on_stage_found:
            # Update
            # Removed for now: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
            if elected_office_name is not False:
                elected_office_on_stage.elected_office_name = elected_office_name
            if google_civic_elected_office_name is not False:
                elected_office_on_stage.google_civic_elected_office_name = google_civic_elected_office_name
            if ocd_division_id is not False:
                elected_office_on_stage.ocd_division_id = ocd_division_id
            if primary_party is not False:
                elected_office_on_stage.primary_party = primary_party
            if election_state is not False:
                elected_office_on_stage.state_code = election_state
            # if ballotpedia_office_id is not False:
            #     office_on_stage.ballotpedia_office_id = ballotpedia_office_id
            # if ballotpedia_office_name is not False:
            #     office_on_stage.ballotpedia_office_name = ballotpedia_office_name
            elected_office_on_stage.save()
            elected_office_on_stage_id = elected_office_on_stage.id
            messages.add_message(request, messages.INFO, 'Office updated.')
            google_civic_election_id = elected_office_on_stage.google_civic_election_id

            return HttpResponseRedirect(reverse('elected_office:elected_office_summary', args=(elected_office_on_stage_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
        else:
            # Create new
            elected_office_on_stage = ElectedOffice(
                elected_office_name=elected_office_name,
                google_civic_election_id=google_civic_election_id,
                state_code=election_state,
            )
            # Removing this limitation: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
            if google_civic_elected_office_name is not False:
                elected_office_on_stage.google_civic_office_name = google_civic_elected_office_name
            if ocd_division_id is not False:
                elected_office_on_stage.ocd_division_id = ocd_division_id
            if primary_party is not False:
                elected_office_on_stage.primary_party = primary_party
            # if ballotpedia_office_id is not False:
            #     office_on_stage.ballotpedia_office_id = ballotpedia_office_id
            # if ballotpedia_office_name is not False:
            #     office_on_stage.ballotpedia_office_name = ballotpedia_office_name
            elected_office_on_stage.save()
            messages.add_message(request, messages.INFO, 'New elected office saved.')

            # Come back to the "Create New Office" page
            return HttpResponseRedirect(reverse('elected_office:elected_office_new', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save office.')

    if redirect_to_elected_office_list:
        return HttpResponseRedirect(reverse('elected_office:elected_office_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))
    else:
        return HttpResponseRedirect(reverse('elected_office:elected_office_edit', args=(elected_office_id,)))


@login_required
def elected_office_delete_process_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    elected_office_id = convert_to_int(request.GET.get('elected_office_id', 0))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    elected_office_on_stage_found = False
    elected_office_on_stage = ElectedOffice()
    try:
        elected_office_on_stage = ElectedOffice.objects.get(id=elected_office_id)
        elected_office_on_stage_found = True
        google_civic_election_id = elected_office_on_stage.google_civic_election_id
    except ElectedOffice.MultipleObjectsReturned as e:
        pass
    except ElectedOffice.DoesNotExist:
        pass

    # TODO fetch elected officials instead candidate
    candidates_found_for_this_office = False
    # if elected_office_on_stage_found:
    #     try:
    #         candidate_list = CandidateCampaign.objects.filter(contest_office_id=elected_office_id)
    #         # if positive_value_exists(google_civic_election_id):
    #         #     candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
    #         candidate_list = candidate_list.order_by('candidate_name')
    #         if len(candidate_list):
    #             candidates_found_for_this_office = True
    #     except CandidateCampaign.DoesNotExist:
    #         pass

    try:
        if not candidates_found_for_this_office:
            # Delete the office
            elected_office_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Elected Office deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'candidates still attached to this elected office.')
            return HttpResponseRedirect(reverse('elected_office:elected_office_summary', args=(elected_office_id,)))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete elected office -- exception.')
        return HttpResponseRedirect(reverse('elected_office:elected_office_summary', args=(elected_office_id,)))

    return HttpResponseRedirect(reverse('elected_office:elected_office_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))
