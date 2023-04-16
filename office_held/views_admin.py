# office_held/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q
from election.models import Election, ElectionManager
import exception.models
import json
from office_held.models import OfficeHeld, OfficeHeldManager, OfficesHeldForLocation
from politician.controllers import update_parallel_fields_with_years_in_related_objects
from representative.models import Representative, RepresentativeManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE

OFFICE_HELD_SYNC_URL = "https://api.wevoteusa.org/apis/v1/officeHeldSyncOut/"
OFFICES_HELD_FOR_LOCATION_SYNC_URL = "https://api.wevoteusa.org/apis/v1/officesHeldForLocationSyncOut/"
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
office_held_status_string = ""

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def office_held_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_battleground = positive_value_exists(request.GET.get('show_battleground', False))
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    office_held_search = request.GET.get('office_held_search', '')

    office_held_list_found = False
    office_held_list = []
    updated_office_held_list = []
    office_held_list_count = 0
    try:
        office_held_queryset = OfficeHeld.objects.all()
        if positive_value_exists(google_civic_election_id):
            office_held_queryset = office_held_queryset.filter(google_civic_election_id=google_civic_election_id)
        else:
            # TODO Limit this search to upcoming_elections only
            pass
        if positive_value_exists(show_battleground):
            year_filters = []
            for year_integer in IS_BATTLEGROUND_YEARS_AVAILABLE:
                if positive_value_exists(year_integer):
                    is_battleground_race_key = 'is_battleground_race_' + str(year_integer)
                    one_year_filter = Q(**{is_battleground_race_key: True})
                    year_filters.append(one_year_filter)
            if len(year_filters) > 0:
                # Add the first query
                final_filters = year_filters.pop()
                # ...and "OR" the remaining items in the list
                for item in year_filters:
                    final_filters |= item
                office_held_queryset = office_held_queryset.filter(final_filters)
        if positive_value_exists(state_code):
            office_held_queryset = office_held_queryset.filter(state_code__iexact=state_code)
        office_held_queryset = office_held_queryset.order_by("office_held_name")

        if positive_value_exists(office_held_search):
            search_words = office_held_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(district_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(district_scope__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_held_description__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_held_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_held_facebook_url__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_held_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_held_url__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(state_code__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    office_held_queryset = office_held_queryset.filter(final_filters)

        office_held_list_count = office_held_queryset.count()
        office_held_list = list(office_held_queryset)

        if len(office_held_list):
            office_held_list_found = True
            status = 'OFFICES_HELD_RETRIEVED'
            success = True
        else:
            status = 'NO_OFFICES_HELD_RETRIEVED'
            success = True
    except OfficeHeld.DoesNotExist:
        # No offices_held found. Not a problem.
        status = 'NO_OFFICES_HELD_FOUND_DoesNotExist'
        office_held_list = []
        success = True
    except Exception as e:
        status = 'FAILED retrieve_all_offices_held_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    if office_held_list_found:
        for office_held in office_held_list:
            # TODO fetch representatives count instead candidate
            # office_held.candidate_count = fetch_candidate_count_for_office(office_held.id)
            updated_office_held_list.append(office_held)

            display_count = len(updated_office_held_list)
            if display_count >= 500:
                # Limit to showing only 500
                break

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']
        # Make sure we always include the current election in the election_list, even if it is older
        if positive_value_exists(google_civic_election_id):
            this_election_found = False
            for one_election in election_list:
                if convert_to_int(one_election.google_civic_election_id) == convert_to_int(google_civic_election_id):
                    this_election_found = True
                    break
            if not this_election_found:
                results = election_manager.retrieve_election(google_civic_election_id)
                if results['election_found']:
                    one_election = results['election']
                    election_list.append(one_election)

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    office_held_list_count_str = f'{office_held_list_count:,}'

    status_print_list = ""
    status_print_list += "office_held_list_count: " + office_held_list_count_str + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_held_list':         updated_office_held_list,
        'office_held_search':       office_held_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'show_all_elections':       show_all_elections,
        'show_battleground':        show_battleground,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
        'status':                   status,
        'success':                  success
    }
    return render(request, 'office_held/office_held_list.html', template_values)


@login_required
def office_held_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', "")

    office_held_manager = OfficeHeldManager()
    updated_office_held_list = []
    # results = office_held_manager.retrieve_all_offices_held_for_upcoming_election(
    #     google_civic_election_id, state_code, True)
    # if results['office_held_list_found']:
    #     office_held_list = results['office_held_list_objects']
    #     # TODO fetch representatives count instead candidate
    #     # for office_held in office_held_list:
    #     #     office_held.candidate_count = fetch_candidate_count_for_office(office_held.id)
    #     #     updated_office_held_list.append(office_held)

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_held_list':      updated_office_held_list,
    }
    return render(request, 'office_held/office_held_edit.html', template_values)


@login_required
def office_held_edit_view(request, office_held_id=0, office_held_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_held_id = convert_to_int(office_held_id)
    state_code = request.GET.get('state_code', 0)
    twitter_handle = request.GET.get('twitter_handle', '')

    office_held = None
    office_held_found = False
    try:
        if positive_value_exists(office_held_id):
            office_held = OfficeHeld.objects.get(id=office_held_id)
        else:
            office_held = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
        office_held_found = True
    except OfficeHeld.MultipleObjectsReturned as e:
        exception.models.handle_record_found_more_than_one_exception(e, logger=logger)
    except OfficeHeld.DoesNotExist:
        # This is fine, create new
        pass

    if office_held_found:
        # Was office_held_merge_possibility_found?
        office_held.contest_office_merge_possibility_found = True  # TODO DALE Make dynamic
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'office_held':          office_held,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'state_code':           state_code,
            'twitter_handle':       twitter_handle,
        }
    return render(request, 'office_held/office_held_edit.html', template_values)


@login_required
def office_held_summary_view(request, office_held_we_vote_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_held = None
    representative_list = []
    state_code = request.GET.get('state_code', "")
    try:
        office_held = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
    except OfficeHeld.MultipleObjectsReturned as e:
        exception.models.handle_record_found_more_than_one_exception(e, logger=logger)
    except OfficeHeld.DoesNotExist:
        # This is fine, create new
        pass

    try:
        query = Representative.objects.using('readonly').all().filter(office_held_we_vote_id=office_held_we_vote_id)
        query = query.order_by('id')
        representative_list = list(query)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not retrieve representatives:' + str(e))

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_held':              office_held,
        'representative_list':      representative_list,
        'state_code':               state_code,
        'election_list':            election_list,
    }
    return render(request, 'office_held/office_held_summary.html', template_values)


@login_required
def office_held_edit_process_view(request):
    """
    Process the new or edit office held forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_held_id = convert_to_int(request.POST.get('office_held_id', 0))
    office_held_name = request.POST.get('office_held_name', False)
    google_civic_office_held_name = request.POST.get('google_civic_office_held_name', False)
    google_civic_office_held_name2 = request.POST.get('google_civic_office_held_name2', False)
    google_civic_office_held_name3 = request.POST.get('google_civic_office_held_name3', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    ocd_division_id = request.POST.get('ocd_division_id', False)
    primary_party = request.POST.get('primary_party', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    redirect_to_office_held_list = convert_to_int(request.POST['redirect_to_office_held_list'])
    state_code = request.POST.get('state_code', False)
    office_held_facebook_url = request.POST.get('office_held_facebook_url', False)
    office_held_twitter_handle = request.POST.get('office_held_twitter_handle', False)
    office_held_url = request.POST.get('office_held_url', False)
    # is_battleground_race_ values taken in below

    office_held_found = False
    office_held = None
    office_held_we_vote_id = ''
    status = ''
    success = True
    years_false_list = []
    years_true_list = []

    # Check to see if this office is already in the database
    try:
        office_held_query = OfficeHeld.objects.filter(id=office_held_id)
        if len(office_held_query):
            office_held = office_held_query[0]
            office_held_we_vote_id = office_held.we_vote_id
            office_held_found = True
    except Exception as e:
        exception.models.handle_record_not_found_exception(e, logger=logger)
        success = False

    if success:
        try:
            if office_held_found:
                office_held_id = office_held.id
            else:
                # Create new
                office_held = OfficeHeld(
                    office_held_name=office_held_name,
                    state_code=state_code,
                )
                office_held_id = office_held.id
                office_held_we_vote_id = office_held.we_vote_id
            # Update
            if office_held_name is not False:
                office_held.office_held_name = office_held_name
            if google_civic_office_held_name is not False:
                office_held.google_civic_office_held_name = google_civic_office_held_name
            if google_civic_office_held_name2 is not False:
                office_held.google_civic_office_held_name2 = google_civic_office_held_name2
            if google_civic_office_held_name is not False:
                office_held.google_civic_office_held_name3 = google_civic_office_held_name3
            if ocd_division_id is not False:
                office_held.ocd_division_id = ocd_division_id
            if primary_party is not False:
                office_held.primary_party = primary_party
            if state_code is not False:
                office_held.state_code = state_code
            if office_held_facebook_url is not False:
                office_held.office_held_facebook_url = office_held_facebook_url
            if office_held_twitter_handle is not False:
                office_held.office_held_twitter_handle = office_held_twitter_handle
            if office_held_url is not False:
                office_held.office_held_url = office_held_url
            is_battleground_years_list = IS_BATTLEGROUND_YEARS_AVAILABLE
            for year in is_battleground_years_list:
                is_battleground_race_key = 'is_battleground_race_' + str(year)
                incoming_is_battleground_race = positive_value_exists(request.POST.get(is_battleground_race_key, False))
                if hasattr(office_held, is_battleground_race_key):
                    if incoming_is_battleground_race:
                        years_true_list.append(year)
                    else:
                        years_false_list.append(year)
                    setattr(office_held, is_battleground_race_key, incoming_is_battleground_race)
            office_held.save()
        except Exception as e:
            exception.models.handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save office held:' + str(e))
            success = False

    if success and positive_value_exists(office_held_we_vote_id):
        results = update_parallel_fields_with_years_in_related_objects(
            field_key_root='is_battleground_race_',
            master_we_vote_id_updated=office_held_we_vote_id,
            years_false_list=years_false_list,
            years_true_list=years_true_list,
        )
        if not results['success']:
            status += results['status']
            status += "FAILED_TO_UPDATE_PARALLEL_FIELDS_FROM_OFFICE_HELD "
            messages.add_message(request, messages.ERROR, status)

    if success:
        if office_held_found:
            messages.add_message(request, messages.INFO, 'Office updated.')

            return HttpResponseRedirect(reverse('office_held:office_held_summary', args=(office_held_we_vote_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
        else:
            messages.add_message(request, messages.INFO, 'New office held saved.')

            # Come back to the "Create New Office" page
            return HttpResponseRedirect(reverse('office_held:office_held_new', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))

    if redirect_to_office_held_list:
        return HttpResponseRedirect(reverse('office_held:office_held_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))
    else:
        return HttpResponseRedirect(reverse('office_held:office_held_edit', args=(office_held_id,)))


@login_required
def office_held_delete_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_held_id = convert_to_int(request.GET.get('office_held_id', 0))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    # office_held_found = False
    office_held = OfficeHeld()
    office_held_we_vote_id = ''
    try:
        office_held = OfficeHeld.objects.get(id=office_held_id)
        office_held_we_vote_id = office_held.we_vote_id
        # office_held_found = True
        google_civic_election_id = office_held.google_civic_election_id
    except OfficeHeld.MultipleObjectsReturned:
        pass
    except OfficeHeld.DoesNotExist:
        pass

    # TODO fetch representatives instead candidate
    candidates_found_for_this_office = False
    # if office_held_found:
    #     try:
    #         candidate_list = CandidateCampaign.objects.filter(contest_office_id=office_held_id)
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
            office_held.delete()
            messages.add_message(request, messages.INFO, 'Office Held deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'candidates still attached to this office held.')
            return HttpResponseRedirect(reverse('office_held:office_held_summary', args=(office_held_we_vote_id,)))
    except Exception:
        messages.add_message(request, messages.ERROR, 'Could not delete office held -- exception.')
        return HttpResponseRedirect(reverse('office_held:office_held_summary', args=(office_held_we_vote_id,)))

    return HttpResponseRedirect(reverse('office_held:office_held_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def office_held_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    status = ""
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in OFFICE_HELD_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
    state_code = request.GET.get('state_code', '')

    from office_held.controllers import office_held_import_from_master_server
    results = office_held_import_from_master_server(request, state_code)
    if results['success']:
        messages.add_message(request, messages.INFO, 'Offices Held import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Duplicates skipped: '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?state_code=" + str(state_code))


@login_required
def offices_held_for_location_import_from_master_server_view(request):  # officesHeldForLocationSyncOut
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    status = ""
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in OFFICES_HELD_FOR_LOCATION_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
    state_code = request.GET.get('state_code', '')

    from office_held.controllers import offices_held_for_location_import_from_master_server
    results = offices_held_for_location_import_from_master_server(request, state_code)
    if results['success']:
        messages.add_message(request, messages.INFO, 'Offices Held for Location import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Duplicates skipped: '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?state_code=" + str(state_code))


def office_held_update_status(request):
    global office_held_status_string

    if 'office_held_status_string' not in globals():
        office_held_status_string = ""

    json_data = {
        'text': office_held_status_string,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def offices_held_for_location_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_battleground = positive_value_exists(request.GET.get('show_battleground', False))
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    location_search = request.GET.get('location_search', '')

    location_list_found = False
    location_list = []
    updated_location_list = []
    location_list_count = 0
    try:
        queryset = OfficesHeldForLocation.objects.all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)

        if positive_value_exists(location_search):
            search_words = location_search.split()
            filters = []  # Reset for each search word
            for one_word in search_words:
                new_filter = Q(polling_location_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(voter_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                count = 1
                while count <= 30:
                    office_held_we_vote_id_key = 'office_held_we_vote_id_' + str(f"{count:02}") + '__icontains'
                    new_filter = Q(**{office_held_we_vote_id_key: one_word})
                    filters.append(new_filter)

                    office_held_name_key = 'office_held_name_' + str(f"{count:02}") + '__icontains'
                    new_filter = Q(**{office_held_name_key: one_word})
                    filters.append(new_filter)

                    count += 1

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                queryset = queryset.filter(final_filters)

        location_list_count = queryset.count()
        location_list = list(queryset[:20])

        if len(location_list):
            location_list_found = True
            status = 'OFFICES_HELD_FOR_LOCATION_RETRIEVED'
            success = True
        else:
            status = 'NO_OFFICES_HELD_FOR_LOCATION_RETRIEVED'
            success = True
    except OfficeHeld.DoesNotExist:
        # No offices_held found. Not a problem.
        status = 'NO_OFFICES_HELD_FOR_LOCATION_FOUND_DoesNotExist'
        location_list = []
        success = True
    except Exception as e:
        status = 'FAILED retrieve_all_offices_held_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    offices_held_for_location_list_modified = []
    for offices_held_for_location in location_list:
        # Generate a list of office_held_name/office_held_we_vote_id pairs for easier display in the template
        office_held_pair_list = []
        count = 1
        while count <= 30:
            office_held_name_name = 'office_held_name_' + str(f"{count:02}")
            office_held_we_vote_id_name = 'office_held_we_vote_id_' + str(f"{count:02}")
            office_held_pair = {
                'office_held_name_name': office_held_name_name,
                'office_held_name_value': getattr(offices_held_for_location, office_held_name_name),
                'office_held_we_vote_id_name': office_held_we_vote_id_name,
                'office_held_we_vote_id_value': getattr(offices_held_for_location, office_held_we_vote_id_name),
            }
            office_held_pair_list.append(office_held_pair)
            count += 1
        offices_held_for_location.office_held_pair_list = office_held_pair_list
        offices_held_for_location_list_modified.append(offices_held_for_location)

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    location_list_count_str = f'{location_list_count:,}'

    status_print_list = ""
    status_print_list += "offices_held_for_location_list_count: " + location_list_count_str + " "

    messages.add_message(request, messages.INFO, status_print_list)
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'location_list':            offices_held_for_location_list_modified,
        'location_search':          location_search,
        'state_code':               state_code,
        'show_all_elections':       show_all_elections,
        'show_battleground':        show_battleground,
        'state_list':               sorted_state_list,
        'google_civic_election_id': google_civic_election_id,
        'status':                   status,
        'success':                  success
    }
    return render(request, 'office_held/offices_held_for_location_list.html', template_values)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
def office_held_sync_out_view(request):  # officeHeldSyncOut
    state_code = request.GET.get('state_code', '')

    try:
        office_held_list = OfficeHeld.objects.using('readonly').all()
        office_held_list = office_held_list.filter(state_code__iexact=state_code)
        office_held_list_dict = office_held_list.values(
            'district_id',
            'district_name',
            'district_scope',
            'facebook_url_is_broken',
            'google_civic_office_held_name',
            'google_civic_office_held_name2',
            'google_civic_office_held_name3',
            'is_battleground_race_2019',
            'is_battleground_race_2020',
            'is_battleground_race_2021',
            'is_battleground_race_2022',
            'is_battleground_race_2023',
            'is_battleground_race_2024',
            'is_battleground_race_2025',
            'is_battleground_race_2026',
            'number_elected',
            'ocd_division_id',
            'office_held_description',
            'office_held_description_es',
            'office_held_facebook_url',
            'office_held_is_partisan',
            'office_held_level0',
            'office_held_level1',
            'office_held_level2',
            'office_held_name',
            'office_held_name_es',
            'office_held_role0',
            'office_held_role1',
            'office_held_role2',
            'office_held_twitter_handle',
            'office_held_url',
            'primary_party',
            'race_office_level',
            'state_code',
            'we_vote_id',
            'year_with_data_2023',
            'year_with_data_2024',
            'year_with_data_2025',
            'year_with_data_2026',
        )
        if office_held_list_dict:
            office_held_list_json = list(office_held_list_dict)
            return HttpResponse(json.dumps(office_held_list_json), content_type='application/json')
    except OfficeHeld.DoesNotExist:
        pass

    json_data = {
        'success': False,
        'status': 'OFFICE_HELD_SYNC_OUT_VIEW-LIST_MISSING '
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
def offices_held_for_location_sync_out_view(request):  # officesHeldForLocationSyncOut
    state_code = request.GET.get('state_code', '')

    try:
        queryset = OfficesHeldForLocation.objects.using('readonly').all()
        queryset = queryset.filter(state_code__iexact=state_code)
        offices_held_for_location_list_dict = queryset.values(
            'date_last_retrieved',
            'date_last_updated',
            'office_held_name_01',
            'office_held_name_02',
            'office_held_name_03',
            'office_held_name_04',
            'office_held_name_05',
            'office_held_name_06',
            'office_held_name_07',
            'office_held_name_08',
            'office_held_name_09',
            'office_held_name_10',
            'office_held_name_11',
            'office_held_name_12',
            'office_held_name_13',
            'office_held_name_14',
            'office_held_name_15',
            'office_held_name_16',
            'office_held_name_17',
            'office_held_name_18',
            'office_held_name_19',
            'office_held_name_20',
            'office_held_name_21',
            'office_held_name_22',
            'office_held_name_23',
            'office_held_name_24',
            'office_held_name_25',
            'office_held_name_26',
            'office_held_name_27',
            'office_held_name_28',
            'office_held_name_29',
            'office_held_name_30',
            'office_held_we_vote_id_01',
            'office_held_we_vote_id_02',
            'office_held_we_vote_id_03',
            'office_held_we_vote_id_04',
            'office_held_we_vote_id_05',
            'office_held_we_vote_id_06',
            'office_held_we_vote_id_07',
            'office_held_we_vote_id_08',
            'office_held_we_vote_id_09',
            'office_held_we_vote_id_10',
            'office_held_we_vote_id_11',
            'office_held_we_vote_id_12',
            'office_held_we_vote_id_13',
            'office_held_we_vote_id_14',
            'office_held_we_vote_id_15',
            'office_held_we_vote_id_16',
            'office_held_we_vote_id_17',
            'office_held_we_vote_id_18',
            'office_held_we_vote_id_19',
            'office_held_we_vote_id_20',
            'office_held_we_vote_id_21',
            'office_held_we_vote_id_22',
            'office_held_we_vote_id_23',
            'office_held_we_vote_id_24',
            'office_held_we_vote_id_25',
            'office_held_we_vote_id_26',
            'office_held_we_vote_id_27',
            'office_held_we_vote_id_28',
            'office_held_we_vote_id_29',
            'office_held_we_vote_id_30',
            'polling_location_we_vote_id',
            'state_code',
            'voter_we_vote_id',
            'year_with_data_2023',
            'year_with_data_2024',
            'year_with_data_2025',
            'year_with_data_2026',
        )
        if offices_held_for_location_list_dict:
            modified_list_dict = []
            for one_dict in offices_held_for_location_list_dict:
                date_last_retrieved = one_dict.get('date_last_retrieved', '')
                if positive_value_exists(date_last_retrieved):
                    one_dict['date_last_retrieved'] = date_last_retrieved.strftime('%Y-%m-%d')
                date_last_updated = one_dict.get('date_last_updated', '')
                if positive_value_exists(date_last_updated):
                    one_dict['date_last_updated'] = date_last_updated.strftime('%Y-%m-%d')
                modified_list_dict.append(one_dict)
            list_json = list(modified_list_dict)
            return HttpResponse(json.dumps(list_json), content_type='application/json')
    except OfficesHeldForLocation.DoesNotExist:
        pass

    json_data = {
        'success': False,
        'status': 'OFFICES_HELD_FOR_LOCATION_SYNC_OUT_VIEW-LIST_MISSING '
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
