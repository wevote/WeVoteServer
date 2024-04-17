# office/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import add_contest_office_name_to_next_spot, fetch_duplicate_office_count, \
    find_duplicate_contest_office, figure_out_office_conflict_values, merge_if_duplicate_offices, \
    offices_import_from_master_server
from .models import ContestOffice, ContestOfficeListManager, ContestOfficeManager, CONTEST_OFFICE_UNIQUE_IDENTIFIERS
from admin_tools.views import redirect_to_sign_in_page
from ballot.controllers import move_ballot_items_to_another_office
from bookmark.models import BookmarkItemList
from candidate.controllers import create_candidate_from_politician, move_candidates_to_another_office
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager, fetch_candidate_count_for_office
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.text import slugify
from django.utils.timezone import localtime, now
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from django.db.models import Q
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from position.controllers import move_positions_to_another_office
from position.models import OPPOSE, PositionListManager, SUPPORT
from volunteer_task.models import VOLUNTEER_ACTION_CANDIDATE_CREATED, VolunteerTaskManager
from voter.models import fetch_voter_from_voter_device_link, voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, \
    extract_first_name_from_full_name, extract_middle_name_from_full_name, extract_last_name_from_full_name, \
    is_candidate_we_vote_id, is_politician_we_vote_id, positive_value_exists, \
    STATE_CODE_MAP
from wevote_functions.functions_date import convert_we_vote_date_string_to_date_as_integer
from django.http import HttpResponse
import json

OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def compare_two_offices_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_office1_we_vote_id = request.GET.get('contest_office1_we_vote_id', 0)
    contest_office2_we_vote_id = request.GET.get('contest_office2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', 0)

    contest_office_manager = ContestOfficeManager()
    contest_office_results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office1_we_vote_id)
    if not contest_office_results['contest_office_found']:
        messages.add_message(request, messages.ERROR, "Contest Office1 not found.")
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    contest_office_option1_for_template = contest_office_results['contest_office']

    contest_office_results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office2_we_vote_id)
    if not contest_office_results['contest_office_found']:
        messages.add_message(request, messages.ERROR, "Contest Office2 not found.")
        return HttpResponseRedirect(reverse('office:office_summary', args=(contest_office_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    contest_office_option2_for_template = contest_office_results['contest_office']

    contest_office_merge_conflict_values = figure_out_office_conflict_values(
        contest_office_option1_for_template, contest_office_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_contest_office_merge_form(request, contest_office_option1_for_template,
                                            contest_office_option2_for_template,
                                            contest_office_merge_conflict_values,
                                            remove_duplicate_process)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
# class OfficesSyncOutView(APIView):
#     def get(self, request, format=None):
def offices_sync_out_view(request):  # officesSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    try:
        contest_office_list = ContestOffice.objects.using('readonly').all()
        if positive_value_exists(google_civic_election_id):
            contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            contest_office_list = contest_office_list.filter(state_code__iexact=state_code)
        # serializer = ContestOfficeSerializer(contest_office_list, many=True)
        # return Response(serializer.data)
        # get the data using values_list
        contest_office_list_dict = contest_office_list.values(
            'ballotpedia_district_id',
            'ballotpedia_election_id',
            'ballotpedia_id',
            'ballotpedia_is_marquee',
            'ballotpedia_office_id',
            'ballotpedia_office_name',
            'ballotpedia_office_url',
            'ballotpedia_race_id',
            'ballotpedia_race_office_level',
            'ballotpedia_race_url',
            'contest_level0',
            'contest_level1',
            'contest_level2',
            'ctcl_uuid',
            'district_id',
            'district_name',
            'district_scope',
            'electorate_specifications',
            'facebook_url_is_broken',
            'google_ballot_placement',
            'google_civic_election_id',
            'google_civic_office_name',
            'google_civic_office_name2',
            'google_civic_office_name3',
            'google_civic_office_name4',
            'google_civic_office_name5',
            'is_ballotpedia_general_election',
            'is_ballotpedia_general_runoff_election',
            'is_ballotpedia_primary_election',
            'is_ballotpedia_primary_runoff_election',
            'is_battleground_race',
            'maplight_id',
            'number_elected',
            'number_voting_for',
            'ocd_division_id',
            'office_facebook_url',
            'office_held_description',
            'office_held_description_es',
            'office_held_name',
            'office_held_we_vote_id',
            'office_name',
            'office_twitter_handle',
            'office_url',
            'primary_party',
            'special',
            'state_code',
            'vote_usa_office_id',
            'we_vote_id',
            'wikipedia_id',
        )
        if contest_office_list_dict:
            contest_office_list_json = list(contest_office_list_dict)
            return HttpResponse(json.dumps(contest_office_list_json), content_type='application/json')
    except ContestOffice.DoesNotExist:
        pass

    json_data = {
        'success': False,
        'status': 'OFFICES_SYNC_OUT_VIEW-CONTEST_OFFICE_LIST_MISSING '
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def offices_copy_to_another_election_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    confirm_copy_candidates = positive_value_exists(request.GET.get('confirm_copy_candidates', False))
    confirm_copy_offices = positive_value_exists(request.GET.get('confirm_copy_offices', False))
    from_election_name = ''
    from_google_civic_election_id = request.GET.get('from_google_civic_election_id', 0)
    from_google_civic_election_id = convert_to_int(from_google_civic_election_id)
    has_ctcl_data = positive_value_exists(request.GET.get('has_ctcl_data', False))
    has_vote_usa_data = positive_value_exists(request.GET.get('has_vote_usa_data', False))
    office_search = request.GET.get('office_search', '')
    race_office_level = request.GET.get('race_office_level', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_marquee_or_battleground = request.GET.get('show_marquee_or_battleground', False)
    show_offices_with_zero_candidates_in_to_election = \
        positive_value_exists(request.GET.get('show_offices_with_zero_candidates_in_to_election', False))
    state_code = request.GET.get('state_code', "")
    to_election_name = ''
    to_google_civic_election_id = request.GET.get('to_google_civic_election_id', 0)
    to_google_civic_election_id = convert_to_int(to_google_civic_election_id)

    candidate_list_manager = CandidateListManager()
    candidate_manager = CandidateManager()
    office_display_list = []
    office_display_list_found = False
    office_list_count = 0
    office_list_manager = ContestOfficeListManager()
    office_processing_list = []
    status = ''

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(from_google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('office:office_list', args=()))

    # Whether we are just displaying some offices, or actually doing the conversion, we want to retrieve
    try:
        office_queryset = ContestOffice.objects.all()

        if show_offices_with_zero_candidates_in_to_election:
            office_queryset = office_queryset.filter(google_civic_election_id=to_google_civic_election_id)
        else:
            office_queryset = office_queryset.filter(google_civic_election_id=from_google_civic_election_id)

        from django.db.models.functions import Length
        if positive_value_exists(has_ctcl_data):
            office_queryset = \
                office_queryset.annotate(ctcl_uuid_length=Length('ctcl_uuid'))\
                .filter(ctcl_uuid_length__gt=1)
        if positive_value_exists(has_vote_usa_data):
            office_queryset = \
                office_queryset.annotate(vote_usa_office_id_length=Length('vote_usa_office_id'))\
                .filter(vote_usa_office_id_length__gt=1)
        if positive_value_exists(race_office_level):
            office_queryset = office_queryset.filter(ballotpedia_race_office_level__iexact=race_office_level)
        if positive_value_exists(state_code):
            office_queryset = office_queryset.filter(state_code__iexact=state_code)
        if positive_value_exists(show_marquee_or_battleground):
            office_queryset = office_queryset.filter(Q(ballotpedia_is_marquee=True) | Q(is_battleground_race=True))
        office_queryset = office_queryset.order_by("office_name")

        if positive_value_exists(office_search):
            search_words = office_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(ballotpedia_office_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_race_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(vote_usa_office_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(wikipedia_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    office_queryset = office_queryset.filter(final_filters)

        office_list_count = office_queryset.count()
        office_processing_list = list(office_queryset)

        office_display_list = list(office_queryset[:50])

        if len(office_display_list):
            office_display_list_found = True
            status += 'OFFICES_RETRIEVED '
            success = True
        else:
            status += 'NO_OFFICES_RETRIEVED '
            success = True
    except ContestOffice.DoesNotExist:
        # No offices found. Not a problem.
        status += 'NO_OFFICES_FOUND_DoesNotExist '
        office_display_list = []
        success = True
    except Exception as e:
        status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e)) + " "
        success = False

    updated_office_display_list = []
    offices_with_zero_candidates_count = 0
    if show_offices_with_zero_candidates_in_to_election:
        if office_processing_list:
            for contest_office in office_processing_list:
                contest_office.candidate_count = fetch_candidate_count_for_office(contest_office.id)
                if contest_office.candidate_count == 0:
                    offices_with_zero_candidates_count += 1
                    if offices_with_zero_candidates_count <= 20:
                        # Search in the "from" election for this office
                        results = office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
                            ballotpedia_race_id=contest_office.ballotpedia_race_id,
                            ctcl_uuid=contest_office.ctcl_uuid,
                            contest_office_name=contest_office.office_name,
                            google_civic_election_id=from_google_civic_election_id,
                            incoming_state_code=contest_office.state_code,
                            vote_usa_office_id=contest_office.vote_usa_office_id,
                            read_only=True,
                        )
                        if results['success']:
                            if results['contest_office_found']:
                                from_contest_office_we_vote_id = results['contest_office'].we_vote_id
                                candidate_results = candidate_list_manager.retrieve_all_candidates_for_office(
                                    office_we_vote_id=from_contest_office_we_vote_id)
                                if candidate_results['success']:
                                    if candidate_results['candidate_list_found']:
                                        contest_office.prior_candidate_list = candidate_results['candidate_list']

                        updated_office_display_list.append(contest_office)
    else:
        if office_display_list_found:
            for office in office_display_list:
                office.candidate_count = fetch_candidate_count_for_office(office.id)
                updated_office_display_list.append(office)

    candidates_linked_count = 0
    offices_copied_count = 0
    if positive_value_exists(to_google_civic_election_id) and \
            (positive_value_exists(confirm_copy_candidates) or positive_value_exists(confirm_copy_offices)):
        import copy
        # Loop through the contest offices in this election
        office_save_success = True
        if show_offices_with_zero_candidates_in_to_election:
            pass
        else:
            for contest_office in office_processing_list:
                if not office_save_success:
                    break
                from_contest_office_we_vote_id = contest_office.we_vote_id
                to_contest_office_we_vote_id = ''
                to_state_code = None
                office_created = False
                office_found = False

                # Search in the new "to" election for this office
                results = office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
                    ballotpedia_race_id=contest_office.ballotpedia_race_id,
                    ctcl_uuid=contest_office.ctcl_uuid,
                    contest_office_name=contest_office.office_name,
                    google_civic_election_id=to_google_civic_election_id,
                    incoming_state_code=contest_office.state_code,
                    vote_usa_office_id=contest_office.vote_usa_office_id,
                    read_only=True,
                )
                if results['success']:
                    office_found = results['contest_office_found'] or results['contest_office_list_found']
                    if results['contest_office_found']:
                        to_contest_office_we_vote_id = results['contest_office'].we_vote_id
                    office_search_success = True
                else:
                    office_search_success = False
                    status += results['status']

                if office_search_success and not office_found:
                    if confirm_copy_offices:
                        try:
                            new_contest_office = copy.deepcopy(contest_office)
                            new_contest_office.ballotpedia_election_id = None
                            new_contest_office.ballotpedia_id = None
                            new_contest_office.ballotpedia_race_id = None
                            new_contest_office.google_civic_election_id = to_google_civic_election_id
                            new_contest_office.google_civic_election_id_new = convert_to_int(to_google_civic_election_id)
                            new_contest_office.is_ballotpedia_general_election = False
                            new_contest_office.is_ballotpedia_general_runoff_election = False
                            new_contest_office.is_ballotpedia_primary_election = False
                            new_contest_office.is_ballotpedia_primary_runoff_election = False
                            new_contest_office.pk = None
                            new_contest_office.we_vote_id = None
                            new_contest_office.save()

                            to_contest_office_we_vote_id = new_contest_office.we_vote_id
                            office_created = True

                            offices_copied_count += 1
                        except Exception as e:
                            office_save_success = False
                            status += "FAILED_COPY: " + str(e) + " "
                            success = False
                if office_search_success and (office_found or office_created) and \
                        positive_value_exists(to_contest_office_we_vote_id):
                    if confirm_copy_candidates:
                        # How many "from" candidates? If only one, proceed
                        candidate_to_copy_we_vote_id = ''
                        only_one_to_copy = False
                        # Retrieve from "from" election
                        candidate_results = candidate_list_manager.retrieve_all_candidates_for_office(
                            office_we_vote_id=from_contest_office_we_vote_id)
                        if candidate_results['success']:
                            if candidate_results['candidate_list_found']:
                                candidate_list = candidate_results['candidate_list']
                                if len(candidate_list) == 1:
                                    only_one_to_copy = True
                                    candidate_to_copy_we_vote_id = candidate_list[0].we_vote_id
                                    to_state_code = candidate_list[0].state_code

                        if only_one_to_copy and positive_value_exists(candidate_to_copy_we_vote_id):
                            # See if the "from" candidate is linked to the "to" election. If not, link.
                            link_results = candidate_manager.retrieve_candidate_to_office_link(
                                candidate_we_vote_id=candidate_to_copy_we_vote_id,
                                contest_office_we_vote_id=to_contest_office_we_vote_id,
                                google_civic_election_id=to_google_civic_election_id,
                            )
                            if link_results['success']:
                                if not link_results['list_found'] and not link_results['only_one_found']:
                                    # Link not found. Create new link.
                                    new_link_results = candidate_manager.get_or_create_candidate_to_office_link(
                                        candidate_we_vote_id=candidate_to_copy_we_vote_id,
                                        contest_office_we_vote_id=to_contest_office_we_vote_id,
                                        google_civic_election_id=to_google_civic_election_id,
                                        state_code=to_state_code,
                                    )
                                    if new_link_results['success']:
                                        candidates_linked_count += 1
                                    else:
                                        status += "FAILED_LINK: " + new_link_results['status']
                            else:
                                status += "FAILED_LINK_RETRIEVE: " + link_results['status']

    election_manager = ElectionManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    # Make sure we always include the current election in the election_list, even if it is older
    if positive_value_exists(from_google_civic_election_id):
        from_election_found = False
        for one_election in election_list:
            if convert_to_int(one_election.google_civic_election_id) == convert_to_int(from_google_civic_election_id):
                from_election_found = True
                from_election_name = one_election.election_name
        if not from_election_found:
            results = election_manager.retrieve_election(from_google_civic_election_id)
            if results['election_found']:
                election = results['election']
                from_election_name = election.election_name
                election_list.append(election)
    if positive_value_exists(to_google_civic_election_id):
        to_election_found = False
        for one_election in election_list:
            if convert_to_int(one_election.google_civic_election_id) == convert_to_int(to_google_civic_election_id):
                to_election_found = True
                to_election_name = one_election.election_name
        if not to_election_found:
            results = election_manager.retrieve_election(to_google_civic_election_id)
            if results['election_found']:
                election = results['election']
                to_election_name = election.election_name
                election_list.append(election)

    state_list = STATE_CODE_MAP
    state_list_modified = {}
    office_list_manager = ContestOfficeListManager()
    for one_state_code, one_state_name in state_list.items():
        office_count = office_list_manager.fetch_office_count(from_google_civic_election_id, one_state_code)
        state_name_modified = one_state_name
        if positive_value_exists(office_count):
            state_name_modified += " - " + str(office_count)
            state_list_modified[one_state_code] = state_name_modified
        elif str(one_state_code.lower()) == str(state_code.lower()):
            state_name_modified += " - 0"
            state_list_modified[one_state_code] = state_name_modified
        else:
            # Do not include state in drop-down if there aren't any offices in that state
            pass
    sorted_state_list = sorted(state_list_modified.items())

    office_list_count_str = f'{office_list_count:,}'

    status_print_list = ""
    status_print_list += "office_list_count: " + office_list_count_str + " "

    if confirm_copy_offices:
        status_print_list += "offices_copied_count: " + str(offices_copied_count) + " "
    if confirm_copy_candidates:
        status_print_list += "candidates_linked_count: " + str(candidates_linked_count) + " "
    if show_offices_with_zero_candidates_in_to_election:
        status_print_list += "offices_with_zero_candidates_count: " + str(offices_with_zero_candidates_count) + " "
    if not success:
        status_print_list += "NOT success: " + status + " "

    if show_offices_with_zero_candidates_in_to_election:
        election_shown_name = to_election_name
    else:
        election_shown_name = from_election_name

    messages.add_message(request, messages.INFO, status_print_list)

    template_values = {
        'election_list':                    election_list,
        'election_shown_name':              election_shown_name,
        'from_google_civic_election_id':    from_google_civic_election_id,
        'has_ctcl_data':                    has_ctcl_data,
        'has_vote_usa_data':                has_vote_usa_data,
        'office_display_list':              updated_office_display_list,
        'office_search':                    office_search,
        'race_office_level':                race_office_level,
        'show_all_elections':               show_all_elections,
        'show_offices_with_zero_candidates_in_to_election': show_offices_with_zero_candidates_in_to_election,
        'show_marquee_or_battleground':     show_marquee_or_battleground,
        'state_code':                       state_code,
        'state_list':                       sorted_state_list,
        'to_google_civic_election_id':      to_google_civic_election_id,
    }
    return render(request, 'office/offices_copy.html', template_values)


@login_required
def offices_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    status = ""
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in OFFICES_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = offices_import_from_master_server(request, google_civic_election_id, state_code)
    if results['success']:
        messages.add_message(request, messages.INFO, 'Offices import completed. '
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

    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def office_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    fix_office_district_ids = positive_value_exists(request.GET.get('fix_office_district_ids', False))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    has_ctcl_data = positive_value_exists(request.GET.get('has_ctcl_data', False))
    has_vote_usa_data = positive_value_exists(request.GET.get('has_vote_usa_data', False))
    office_search = request.GET.get('office_search', '')
    race_office_level = request.GET.get('race_office_level', '')
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    show_battleground = positive_value_exists(request.GET.get('show_battleground', False))
    show_marquee_or_battleground = request.GET.get('show_marquee_or_battleground', False)
    state_code = request.GET.get('state_code', '')

    office_list_found = False
    office_list = []
    updated_office_list = []
    office_list_count = 0

    election_manager = ElectionManager()
    office_manager = ContestOfficeManager()
    if positive_value_exists(show_all_elections):
        results = election_manager.retrieve_elections()
        election_list = results['election_list']
    else:
        results = election_manager.retrieve_upcoming_elections()
        election_list = results['election_list']

    add_election_date_as_integer_to_all_offices = True
    number_to_update = 10000
    if add_election_date_as_integer_to_all_offices:
        add_election_date_as_integer_to_all_offices_status = ''
        # We need all the elections in the election_list
        google_civic_election_id_list = []
        election_day_text_by_election_id_dict = {}
        for one_election in election_list:
            google_civic_election_id_list.append(one_election.google_civic_election_id)
            if positive_value_exists(one_election.election_day_text) \
                    and positive_value_exists(one_election.google_civic_election_id):
                election_day_text_by_election_id_dict[one_election.google_civic_election_id] = \
                    convert_we_vote_date_string_to_date_as_integer(one_election.election_day_text)
        # Now get ContestOffice objects we want to update
        office_queryset = ContestOffice.objects.all()
        office_queryset = office_queryset.filter(
            Q(election_date_as_integer__isnull=True) |
            Q(election_date_as_integer=0)
        )
        if positive_value_exists(google_civic_election_id):
            office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
        elif positive_value_exists(show_all_elections):
            # Exclude offices without a google_civic_election_id
            office_queryset = office_queryset.exclude(google_civic_election_id='')
        else:
            # Limit this search to upcoming_elections only
            office_queryset = office_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
        total_to_update = office_queryset.count()
        total_to_update_after = total_to_update - number_to_update if total_to_update > number_to_update else 0
        if positive_value_exists(total_to_update):
            add_election_date_as_integer_to_all_offices_status += \
                "SCRIPT: {entries_to_process:,} entries to process (add_election_date_as_integer_to_all_offices) " \
                "".format(entries_to_process=total_to_update) + " "
        # Now process
        bulk_update_list = []
        office_list = office_queryset[:number_to_update]
        offices_updated = 0
        offices_not_updated = 0
        updates_needed = False
        for one_office in office_list:
            if one_office.google_civic_election_id in election_day_text_by_election_id_dict:
                election_date_as_integer = election_day_text_by_election_id_dict[one_office.google_civic_election_id]
                if positive_value_exists(election_date_as_integer):
                    one_office.election_date_as_integer = election_date_as_integer
                    bulk_update_list.append(one_office)
                    offices_updated += 1
                    updates_needed = True
                else:
                    offices_not_updated += 1
            else:
                offices_not_updated += 1
        if updates_needed:
            ContestOffice.objects.bulk_update(bulk_update_list, ['election_date_as_integer'])
            add_election_date_as_integer_to_all_offices_status += \
                "{updates_made:,} offices updated with new election_date_as_integer. " \
                "{total_to_update_after:,} remaining. " \
                "".format(
                    total_to_update_after=total_to_update_after,
                    updates_made=offices_updated)
        if positive_value_exists(offices_not_updated):
            add_election_date_as_integer_to_all_offices_status += \
                "{offices_not_updated:,} offices not updated." \
                "".format(offices_not_updated=offices_not_updated)
        if positive_value_exists(add_election_date_as_integer_to_all_offices_status):
            messages.add_message(request, messages.INFO, add_election_date_as_integer_to_all_offices_status)

    office_repair_list = []
    try:
        office_queryset = ContestOffice.objects.all()
        if positive_value_exists(google_civic_election_id):
            office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
        elif positive_value_exists(show_all_elections):
            # Return offices from all elections
            pass
        else:
            # Limit this search to upcoming_elections only
            google_civic_election_id_list = []
            for one_election in election_list:
                google_civic_election_id_list.append(one_election.google_civic_election_id)
            office_queryset = office_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
        from django.db.models.functions import Length
        if positive_value_exists(has_ctcl_data):
            office_queryset = \
                office_queryset.annotate(ctcl_uuid_length=Length('ctcl_uuid'))\
                .filter(ctcl_uuid_length__gt=1)
        if positive_value_exists(has_vote_usa_data):
            office_queryset = \
                office_queryset.annotate(vote_usa_office_id_length=Length('vote_usa_office_id'))\
                .filter(vote_usa_office_id_length__gt=1)
        if positive_value_exists(race_office_level):
            office_queryset = office_queryset.filter(ballotpedia_race_office_level__iexact=race_office_level)
        if positive_value_exists(state_code):
            office_queryset = office_queryset.filter(state_code__iexact=state_code)
        if positive_value_exists(show_marquee_or_battleground):
            office_queryset = office_queryset.filter(Q(ballotpedia_is_marquee=True) | Q(is_battleground_race=True))
        office_queryset = office_queryset.order_by("office_name")

        if positive_value_exists(office_search):
            search_words = office_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                new_filter = Q(ballotpedia_office_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(ballotpedia_race_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(ocd_division_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(vote_usa_office_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(wikipedia_id__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    office_queryset = office_queryset.filter(final_filters)

        office_list_count = office_queryset.count()
        if show_marquee_or_battleground:
            office_repair_list = list(office_queryset)

        office_queryset = office_queryset[:200]
        office_list = list(office_queryset)

        if len(office_list):
            office_list_found = True
            status += 'OFFICES_RETRIEVED '
            success = True
        else:
            status += 'NO_OFFICES_RETRIEVED '
            success = True
    except ContestOffice.DoesNotExist:
        # No offices found. Not a problem.
        status += 'NO_OFFICES_FOUND_DoesNotExist '
        office_list = []
        success = True
    except Exception as e:
        status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e)) + " "
        success = False

    if office_list_found:
        position_list_manager = PositionListManager()
        for office in office_list:
            office.candidate_count = fetch_candidate_count_for_office(office.id)
            office.positions_count = position_list_manager.fetch_public_positions_count_for_contest_office(
                office.id, office.we_vote_id)

            updated_office_list.append(office)

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
                election = results['election']
                election_list.append(election)

    state_list = STATE_CODE_MAP
    state_list_modified = {}
    office_list_manager = ContestOfficeListManager()
    for one_state_code, one_state_name in state_list.items():
        office_count = office_list_manager.fetch_office_count(google_civic_election_id, one_state_code)
        state_name_modified = one_state_name
        if positive_value_exists(office_count):
            state_name_modified += " - " + str(office_count)
            state_list_modified[one_state_code] = state_name_modified
        elif str(one_state_code.lower()) == str(state_code.lower()):
            state_name_modified += " - 0"
            state_list_modified[one_state_code] = state_name_modified
        else:
            # Do not include state in drop-down if there aren't any offices in that state
            pass
    sorted_state_list = sorted(state_list_modified.items())

    office_list_count_str = f'{office_list_count:,}'

    status_print_list = ""
    status_print_list += "office_list_count: " + office_list_count_str + " "

    messages.add_message(request, messages.INFO, status_print_list)

    if office_list_found and fix_office_district_ids:
        # Do some data clean up
        office_list = updated_office_list
        updated_office_list = []
        for office in office_list:
            if not positive_value_exists(office.district_id):
                if office.vote_usa_office_id and office.vote_usa_office_id.startswith('VAStateHouse'):
                    calculated_district_id = office.vote_usa_office_id.replace('VAStateHouse', '')
                    office.district_id = calculated_district_id
                    office.ballotpedia_race_office_level = 'State'
                    office.save()
            updated_office_list.append(office)

    office_repair_success = True

    if len(office_repair_list) > 0:
        from politician.controllers import update_parallel_fields_with_years_in_related_objects
        for office_on_stage in office_repair_list:
            if office_repair_success and not office_on_stage.is_battleground_race_spread_to_all_objects:
                election_day_text = office_on_stage.get_election_day_text()
                year = 0
                years_false_list = []
                years_true_list = []
                if positive_value_exists(election_day_text):
                    date_as_integer = convert_we_vote_date_string_to_date_as_integer(election_day_text)
                    year = date_as_integer // 10000
                if positive_value_exists(year):
                    if positive_value_exists(office_on_stage.is_battleground_race):
                        years_true_list = [year]
                    else:
                        # For this update script we only want to propagate True values (i.e. years_true_list)
                        # years_false_list = [year]
                        pass
                years_list = list(set(years_false_list + years_true_list))
                if len(years_list) > 0:
                    results = update_parallel_fields_with_years_in_related_objects(
                        field_key_root='is_battleground_race_',
                        master_we_vote_id_updated=office_on_stage.we_vote_id,
                        years_false_list=years_false_list,
                        years_true_list=years_true_list,
                    )
                    office_repair_success = results['success']
                    if office_repair_success:
                        office_on_stage.is_battleground_race_spread_to_all_objects = True
                        office_on_stage.save()
                    else:
                        status += results['status']
                        messages.add_message(request, messages.ERROR, status)

    messages_on_stage = get_messages(request)

    template_values = {
        'election_list':                election_list,
        'google_civic_election_id':     google_civic_election_id,
        'has_ctcl_data':                has_ctcl_data,
        'has_vote_usa_data':            has_vote_usa_data,
        'messages_on_stage':            messages_on_stage,
        'office_list':                  updated_office_list,
        'office_search':                office_search,
        'race_office_level':            race_office_level,
        'show_all_elections':           show_all_elections,
        'show_battleground':            show_battleground,
        'show_marquee_or_battleground': show_marquee_or_battleground,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
    }
    return render(request, 'office/office_list.html', template_values)


@login_required
def office_list_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    state_code = request.POST.get('state_code', '')
    show_all_elections = positive_value_exists(request.POST.get('show_all_elections', False))
    show_marquee_or_battleground = request.POST.get('show_marquee_or_battleground', False)
    office_search = request.POST.get('office_search', '')

    # On redirect, we want to maintain the "state" of the page
    url_variables = "?google_civic_election_id=" + str(google_civic_election_id)
    if positive_value_exists(state_code):
        url_variables += "&state_code=" + str(state_code)
    if positive_value_exists(show_all_elections):
        url_variables += "&show_all_elections=" + str(show_all_elections)
    if positive_value_exists(show_marquee_or_battleground):
        url_variables += "&show_marquee_or_battleground=" + str(show_marquee_or_battleground)
    if positive_value_exists(office_search):
        url_variables += "&office_search=" + str(office_search)

    select_for_marking_office_we_vote_ids = request.POST.getlist('select_for_marking_checks[]')
    which_marking = request.POST.get("which_marking")

    # Make sure 'which_marking' is one of the allowed Filter fields
    if which_marking not in "is_battleground_race":
        messages.add_message(request, messages.ERROR,
                             'The filter you are trying to update is not recognized: {which_marking}'
                             ''.format(which_marking=which_marking))
        return HttpResponseRedirect(reverse('office:office_list', args=()))

    print(f"office_list_process_view {which_marking}")
    print(f"marked:{select_for_marking_office_we_vote_ids}")

    error_count = 0
    items_processed_successfully = 0
    if which_marking and select_for_marking_office_we_vote_ids:
        for organization_we_vote_id in select_for_marking_office_we_vote_ids:
            try:
                contest_office_on_stage = ContestOffice.objects.get(
                    we_vote_id__iexact=organization_we_vote_id)
                if which_marking == "is_battleground_race":
                    contest_office_on_stage.is_battleground_race = True
                contest_office_on_stage.save()
                items_processed_successfully += 1
                status += 'CONTEST_OFFICE_UPDATED '
            except ContestOffice.MultipleObjectsReturned as e:
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND '
                error_count += 1
            except ContestOffice.DoesNotExist:
                status += "RETRIEVE_OFFICE_NOT_FOUND "
                error_count += 1
            except Exception as e:
                status += 'GENERAL_ERROR ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                error_count += 1

        messages.add_message(request, messages.INFO,
                             'Endorsers processed successfully: {items_processed_successfully}, '
                             'errors: {error_count}'
                             ''.format(error_count=error_count,
                                       items_processed_successfully=items_processed_successfully))

    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                url_variables)


@login_required
def office_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")
    ballotpedia_office_id = request.GET.get('ballotpedia_office_id', '')
    ballotpedia_office_name = request.GET.get('ballotpedia_office_name', '')
    ballotpedia_race_id = request.GET.get('ballotpedia_race_id', '')
    ctcl_uuid = request.GET.get('ctcl_uuid', '')
    district_id = request.GET.get('district_id', '')
    ocd_division_id = request.GET.get('ocd_division_id', '')
    google_civic_office_name = request.GET.get('google_civic_office_name', '')
    google_civic_office_name2 = request.GET.get('google_civic_office_name2', '')
    google_civic_office_name3 = request.GET.get('google_civic_office_name3', '')
    google_civic_office_name4 = request.GET.get('google_civic_office_name4', '')
    google_civic_office_name5 = request.GET.get('google_civic_office_name5', '')

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR,
                             'Could not find election -- required to save office.')
        url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                        "&state_code=" + str(state_code)
        return HttpResponseRedirect(reverse('office:office_list', args=()) + url_variables)

    office_list_manager = ContestOfficeListManager()
    updated_office_list = []
    return_list_of_objects = True
    read_only = True
    results = office_list_manager.retrieve_all_offices_for_upcoming_election(google_civic_election_id, state_code,
                                                                             return_list_of_objects, read_only)
    if results['office_list_found']:
        office_list = results['office_list_objects']
        for office in office_list:
            office.candidate_count = fetch_candidate_count_for_office(office.id)
            updated_office_list.append(office)

    messages_on_stage = get_messages(request)
    template_values = {
        'ballotpedia_office_id_dict':              
        {
            'label':    'Ballotpedia Office Id (Office Held)',
            'id':       'ballotpedia_office_id_id',
            'name':     'ballotpedia_office_id',
            'value':     ballotpedia_office_id
        },
        'ballotpedia_office_name_dict':              
        {
            'label':    'Office Name (for Ballotpedia matching)',
            'id':       'ballotpedia_office_name_id',
            'name':     'ballotpedia_office_name',
            'value':     ballotpedia_office_name
        },
        'ballotpedia_race_id_dict':              
        {
            'label':    'Ballotpedia Race Id (Contest Office)',
            'id':       'ballotpedia_race_id_id',
            'name':     'ballotpedia_race_id',
            'value':     ballotpedia_race_id
        },
        'ctcl_uuid_dict':              
        {
            'label':    'CTCL UUID',
            'id':       'ctcl_uuid_id',
            'name':     'ctcl_uuid',
            'value':     ctcl_uuid
        },
        'district_id_dict':              
        {
            'label':    'District ID',
            'id':       'district_id_id',
            'name':     'district_id',
            'value':     district_id
        },
        'google_civic_election_id':         google_civic_election_id,
        'google_civic_office_name_dict':              
        {
            'label':    'Office Name 1 (for Google Civic matching)',
            'id':       'google_civic_office_name_id',
            'name':     'google_civic_office_name',
            'value':     google_civic_office_name
        },
        'google_civic_office_name2_dict':              
        {
            'label':    'Office Name 2',
            'id':       'google_civic_office_name2_id',
            'name':     'google_civic_office_name2',
            'value':     google_civic_office_name2
        },
        'google_civic_office_name3_dict':              
        {
            'label':    'Office Name 3',
            'id':       'google_civic_office_name3_id',
            'name':     'google_civic_office_name3',
            'value':     google_civic_office_name3
        },
        'google_civic_office_name4_dict':              
        {
            'label':    'Office Name 4',
            'id':       'google_civic_office_name4_id',
            'name':     'google_civic_office_name4',
            'value':     google_civic_office_name4
        },
        'google_civic_office_name5_dict':              
        {
            'label':    'Office Name 5',
            'id':       'google_civic_office_name5_id',
            'name':     'google_civic_office_name5',
            'value':     google_civic_office_name5
        },
        'messages_on_stage':        messages_on_stage,
        'ocd_division_id_dict':              
        {
            'label':    'OCD Division ID',
            'id':       'ocd_division_id_id',
            'name':     'ocd_division_id',
            'value':     ocd_division_id
        },
        'office_list':              updated_office_list,
        'state_code':               state_code,
    }
    return render(request, 'office/office_edit.html', template_values)


@login_required
def office_edit_view(request, office_id=0, contest_office_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ballotpedia_office_id = request.GET.get('ballotpedia_office_id', '')
    ballotpedia_office_name = request.GET.get('ballotpedia_office_name', '')
    ballotpedia_race_id = request.GET.get('ballotpedia_race_id', '')
    ctcl_uuid = request.GET.get('ctcl_uuid', '')
    district_id = request.GET.get('district_id', '')
    messages_on_stage = get_messages(request)
    ocd_division_id = request.GET.get('ocd_division_id', '')
    office_id = convert_to_int(office_id)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_office_name = request.GET.get('google_civic_office_name', '')
    google_civic_office_name2 = request.GET.get('google_civic_office_name2', '')
    google_civic_office_name3 = request.GET.get('google_civic_office_name3', '')
    google_civic_office_name4 = request.GET.get('google_civic_office_name4', '')
    google_civic_office_name5 = request.GET.get('google_civic_office_name5', '')
    
    office_on_stage = ContestOffice()
    office_on_stage_found = False
    try:
        if positive_value_exists(office_id):
            office_on_stage = ContestOffice.objects.get(id=office_id)
        else:
            office_on_stage = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
        office_on_stage_found = True
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    if office_on_stage_found:
        # Was a contest_office_merge_possibility_found?
        office_on_stage.contest_office_merge_possibility_found = True  # TODO DALE Make dynamic
        template_values = {
            'ballotpedia_office_id_dict':              
            {
                'label':    'Ballotpedia Office Id (Office Held)',
                'id':       'ballotpedia_office_id_id',
                'name':     'ballotpedia_office_id',
                'value':     ballotpedia_office_id if ballotpedia_office_id else office_on_stage.ballotpedia_office_id
            },
            'ballotpedia_office_name_dict':              
            {
                'label':    'Office Name (for Ballotpedia matching)',
                'id':       'ballotpedia_office_name_id',
                'name':     'ballotpedia_office_name',
                'value':     ballotpedia_office_name if ballotpedia_office_name else office_on_stage.ballotpedia_office_name
            },
            'ballotpedia_race_id_dict':              
            {
                'label':    'Ballotpedia Race Id (Contest Office)',
                'id':       'ballotpedia_race_id_id',
                'name':     'ballotpedia_race_id',
                'value':     ballotpedia_race_id if ballotpedia_race_id else office_on_stage.ballotpedia_race_id
            },
            'ctcl_uuid_dict':              
            {
                'label':    'CTCL UUID',
                'id':       'ctcl_uuid_id',
                'name':     'ctcl_uuid',
                'value':     ctcl_uuid if ctcl_uuid else office_on_stage.ctcl_uuid
            },
            'district_id_dict':              
            {
                'label':    'District ID',
                'id':       'district_id_id',
                'name':     'district_id',
                'value':     district_id if district_id else office_on_stage.district_id
            },
            'google_civic_election_id':         google_civic_election_id,
            'google_civic_office_name_dict':              
            {
                'label':    'Office Name 1 (for Google Civic matching)',
                'id':       'google_civic_office_name_id',
                'name':     'google_civic_office_name',
                'value':     google_civic_office_name if google_civic_office_name else office_on_stage.google_civic_office_name
            },
            'google_civic_office_name2_dict':              
            {
                'label':    'Office Name 2',
                'id':       'google_civic_office_name2_id',
                'name':     'google_civic_office_name2',
                'value':     google_civic_office_name2 if google_civic_office_name2 else office_on_stage.google_civic_office_name2
            },
            'google_civic_office_name3_dict':              
            {
                'label':    'Office Name 3',
                'id':       'google_civic_office_name3_id',
                'name':     'google_civic_office_name3',
                'value':     google_civic_office_name3 if google_civic_office_name3 else office_on_stage.google_civic_office_name3
            },
            'google_civic_office_name4_dict':              
            {
                'label':    'Office Name 4',
                'id':       'google_civic_office_name4_id',
                'name':     'google_civic_office_name4',
                'value':     google_civic_office_name4 if google_civic_office_name4 else office_on_stage.google_civic_office_name4
            },
            'google_civic_office_name5_dict':              
            {
                'label':    'Office Name 5',
                'id':       'google_civic_office_name5_id',
                'name':     'google_civic_office_name5',
                'value':     google_civic_office_name5 if google_civic_office_name5 else office_on_stage.google_civic_office_name5
            },
            'messages_on_stage':        messages_on_stage,
            'ocd_division_id_dict':              
            {
                'label':    'OCD Division ID',
                'id':       'ocd_division_id_id',
                'name':     'ocd_division_id',
                'value':     ocd_division_id if ocd_division_id else office_on_stage.ocd_division_id
            },
            'office':                   office_on_stage,
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
    status = ''
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ballotpedia_office_id = request.POST.get('ballotpedia_office_id', False)  # Related to office_held
    ballotpedia_race_id = request.POST.get('ballotpedia_race_id', False)  # Related to contest_office
    ballotpedia_race_office_level = request.POST.get('ballotpedia_race_office_level', False)
    ballotpedia_office_name = request.POST.get('ballotpedia_office_name', False)
    ballotpedia_is_marquee = request.POST.get('ballotpedia_is_marquee', False)
    ctcl_uuid = request.POST.get('ctcl_uuid', False)
    district_id = request.POST.get('district_id', False)
    google_civic_office_name = request.POST.get('google_civic_office_name', False)
    google_civic_office_name2 = request.POST.get('google_civic_office_name2', False)
    google_civic_office_name3 = request.POST.get('google_civic_office_name3', False)
    google_civic_office_name4 = request.POST.get('google_civic_office_name4', False)
    google_civic_office_name5 = request.POST.get('google_civic_office_name5', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    ocd_division_id = request.POST.get('ocd_division_id', False)
    office_held_we_vote_id = request.POST.get('office_held_we_vote_id', False)
    office_id = convert_to_int(request.POST.get('office_id', 0))
    office_name = request.POST.get('office_name', False)
    primary_party = request.POST.get('primary_party', False)
    state_code = request.POST.get('state_code', False)
    vote_usa_office_id = request.POST.get('vote_usa_office_id', False)
    is_battleground_race = request.POST.get('is_battleground_race', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    redirect_to_contest_office_list = convert_to_int(request.POST.get('redirect_to_contest_office_list', 0))

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
    office_on_stage = None
    try:
        office_query = ContestOffice.objects.filter(id=office_id)
        if len(office_query):
            office_on_stage = office_query[0]
            office_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        success = False

    if success:
        try:
            if office_on_stage_found:
                office_on_stage_id = office_on_stage.id
                google_civic_election_id = office_on_stage.google_civic_election_id
            else:
                # Create new
                office_on_stage = ContestOffice(
                    office_name=office_name,
                    google_civic_election_id=google_civic_election_id,
                    state_code=election_state,
                )
                office_on_stage_id = office_on_stage.id
                google_civic_election_id = office_on_stage.google_civic_election_id
                office_on_stage_found = True
            if office_on_stage_found:
                # Update
                # Removing this limitation: convert_to_int(office_on_stage.google_civic_election_id) >= 1000000 and
                office_on_stage.ballotpedia_is_marquee = positive_value_exists(ballotpedia_is_marquee)
                if ballotpedia_office_id is not False:
                    office_on_stage.ballotpedia_office_id = convert_to_int(ballotpedia_office_id)
                if ballotpedia_office_name is not False:
                    office_on_stage.ballotpedia_office_name = ballotpedia_office_name
                if ballotpedia_race_id is not False:
                    office_on_stage.ballotpedia_race_id = convert_to_int(ballotpedia_race_id)
                if ballotpedia_race_office_level is not False:
                    office_on_stage.ballotpedia_race_office_level = ballotpedia_race_office_level
                if ctcl_uuid is not False:
                    office_on_stage.ctcl_uuid = ctcl_uuid
                if district_id is not False:
                    office_on_stage.district_id = district_id
                if positive_value_exists(election_state):
                    office_on_stage.state_code = election_state
                if google_civic_office_name is not False:
                    office_on_stage.google_civic_office_name = google_civic_office_name
                if google_civic_office_name2 is not False:
                    office_on_stage.google_civic_office_name2 = google_civic_office_name2
                if google_civic_office_name3 is not False:
                    office_on_stage.google_civic_office_name3 = google_civic_office_name3
                if google_civic_office_name4 is not False:
                    office_on_stage.google_civic_office_name4 = google_civic_office_name4
                if google_civic_office_name5 is not False:
                    office_on_stage.google_civic_office_name5 = google_civic_office_name5
                # Save office is_battleground_race for this year, and then prepare to update all related objects
                office_on_stage.is_battleground_race = positive_value_exists(is_battleground_race)
                election_day_text = office_on_stage.get_election_day_text()
                year = 0
                years_false_list = []
                years_true_list = []
                if positive_value_exists(election_day_text):
                    date_as_integer = convert_we_vote_date_string_to_date_as_integer(election_day_text)
                    year = date_as_integer // 10000
                if positive_value_exists(year):
                    if positive_value_exists(is_battleground_race):
                        years_false_list = []
                        years_true_list = [year]
                    else:
                        years_false_list = [year]
                        years_true_list = []
                years_list = list(set(years_false_list + years_true_list))
                if ocd_division_id is not False:
                    office_on_stage.ocd_division_id = ocd_division_id
                if office_held_we_vote_id is not False:
                    office_on_stage.office_held_we_vote_id = office_held_we_vote_id
                    from office_held.models import OfficeHeldManager
                    office_held_manager = OfficeHeldManager()
                    office_held_results = office_held_manager.retrieve_office_held(
                        office_held_we_vote_id=office_held_we_vote_id,
                        read_only=True)
                    if office_held_results['office_held_found']:
                        office_held = office_held_results['office_held']
                        office_on_stage.office_held_name = office_held.office_held_name
                if office_name is not False:
                    office_on_stage.office_name = office_name
                if primary_party is not False:
                    office_on_stage.primary_party = primary_party
                if vote_usa_office_id is not False:
                    office_on_stage.vote_usa_office_id = vote_usa_office_id

                office_on_stage.save()
                office_on_stage_id = office_on_stage.id
                office_on_stage_we_vote_id = office_on_stage.we_vote_id
                messages.add_message(request, messages.INFO, 'Office updated.')
                # ##################################
                # Update "is_battleground_race" for candidates under this office through the link CandidateToOfficeLink
                # We can't automatically update all of these candidates with the office's setting,
                # because we may be saving a primary election office which isn't a battleground race,
                # and the candidate may have made it through to the general election which
                # *is* a battleground.
                # from candidate.controllers import update_candidates_with_is_battleground_race
                # results = update_candidates_with_is_battleground_race(office_we_vote_id=office_on_stage.we_vote_id)
                if positive_value_exists(office_on_stage_we_vote_id) and len(years_list) > 0:
                    from politician.controllers import update_parallel_fields_with_years_in_related_objects
                    results = update_parallel_fields_with_years_in_related_objects(
                        field_key_root='is_battleground_race_',
                        master_we_vote_id_updated=office_on_stage_we_vote_id,
                        years_false_list=years_false_list,
                        years_true_list=years_true_list,
                    )
                    if not results['success']:
                        status += results['status']
                        status += "FAILED_TO_UPDATE_PARALLEL_FIELDS_FROM_OFFICE "
                        messages.add_message(request, messages.ERROR, status)

            return HttpResponseRedirect(reverse('office:office_summary', args=(office_on_stage_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save office (create new): ' + str(e))
    else:
        messages.add_message(request, messages.ERROR, 'Could not save office, success = False from above: ' + status)

    if redirect_to_contest_office_list:
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))
    else:
        return HttpResponseRedirect(reverse('office:office_edit', args=(office_id,)))


@login_required
def office_summary_view(request, office_id=0, contest_office_we_vote_id=''):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    office_id = convert_to_int(office_id)
    contest_office = None
    contest_office_found = False
    state_code_for_template = ''

    candidate_possibility_search = request.GET.get('candidate_possibility_search', "")
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    office_search = request.GET.get('office_search', "")

    try:
        if positive_value_exists(office_id):
            contest_office = ContestOffice.objects.get(id=office_id)
        else:
            contest_office = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
        contest_office_found = True
        contest_office_we_vote_id = contest_office.we_vote_id
        google_civic_election_id = contest_office.google_civic_election_id
        state_code_for_template = contest_office.state_code
    except ContestOffice.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestOffice.DoesNotExist:
        # This is fine, create new
        pass

    candidate_list_modified = []
    position_list_manager = PositionListManager()
    # Cache the full names of candidates for the root contest_office so we can check to see if possible duplicate
    # offices share the same candidates
    root_office_candidate_last_names = ""
    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_office_list(
        contest_office_we_vote_id_list=[contest_office_we_vote_id])
    existing_candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    try:
        candidate_query = CandidateCampaign.objects.all()
        candidate_query = candidate_query.filter(we_vote_id__in=existing_candidate_we_vote_id_list)
        candidate_query = candidate_query.order_by('candidate_name')
        candidate_list = list(candidate_query)
        support_total = 0
        for one_candidate in candidate_list:
            # Find the count of Voters that support this candidate (Endorsers are not included in this)
            one_candidate.support_count = position_list_manager.fetch_voter_positions_count_for_candidate(
                one_candidate.id, "", SUPPORT)
            one_candidate.oppose_count = position_list_manager.fetch_voter_positions_count_for_candidate(
                one_candidate.id, "", OPPOSE)
            support_total += one_candidate.support_count
            root_office_candidate_last_names += " " + one_candidate.extract_last_name()

        for one_candidate in candidate_list:
            if positive_value_exists(support_total):
                percentage_of_support_number = one_candidate.support_count / support_total * 100
                one_candidate.percentage_of_support = "%.1f" % percentage_of_support_number

            candidate_list_modified.append(one_candidate)

    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    root_office_candidate_last_names = root_office_candidate_last_names.lower()

    election_list = Election.objects.order_by('-election_day_text')

    if positive_value_exists(google_civic_election_id):
        election = Election.objects.get(google_civic_election_id=google_civic_election_id)

    # ##############################################################
    # Office Add Candidates
    results = office_summary_add_candidates_process_view(
        request,
        contest_office=contest_office,
        existing_candidate_we_vote_id_list=existing_candidate_we_vote_id_list,
    )
    at_least_one_candidate_created = results['at_least_one_candidate_created']
    search_result_options_list = results['search_result_options_list']

    # ##############################################################
    # Office Merging
    results = office_summary_merge_with_other_office_process_view(
        request,
        contest_office=contest_office,
        contest_office_found=contest_office_found,
        contest_office_we_vote_id=contest_office_we_vote_id,
        root_office_candidate_last_names=root_office_candidate_last_names,
    )
    office_search_results_list = results['office_search_results_list']

    if positive_value_exists(at_least_one_candidate_created):
        return HttpResponseRedirect(reverse('office:office_summary', args=(office_id,)) +
                                    "?candidate_possibility_search=" + str(candidate_possibility_search) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(contest_office.state_code))

    if contest_office_found:
        template_values = {
            'candidate_possibility_search': candidate_possibility_search,
            'candidate_list':               candidate_list_modified,
            'existing_candidate_we_vote_id_list':    existing_candidate_we_vote_id_list,
            'election':                     election,
            'election_list':                election_list,
            'google_civic_election_id':     google_civic_election_id,
            'messages_on_stage':            messages_on_stage,
            'office':                       contest_office,
            'office_search':                office_search,
            'office_search_results_list':   office_search_results_list,
            'search_result_options_list':   search_result_options_list,
            'state_code':                   state_code_for_template,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'state_code':           state_code_for_template,
        }
    return render(request, 'office/office_summary.html', template_values)


def office_summary_merge_with_other_office_process_view(
        request,
        contest_office=None,
        contest_office_found=False,
        contest_office_we_vote_id='',
        root_office_candidate_last_names=''):
    """

    :param request:
    :param contest_office:
    :param contest_office_found:
    :param contest_office_we_vote_id:
    :param root_office_candidate_last_names:
    :return:
    """
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    office_search = request.GET.get('office_search', "")
    select_for_marking_office_we_vote_ids = request.GET.getlist('select_for_marking_office_we_vote_ids[]')
    state_code = request.GET.get('state_code', "")
    which_marking = request.GET.get('which_marking')
    office_manager = ContestOfficeManager()
    # ##############################################################
    # Office Merging
    # Make sure 'which_marking' is one of the allowed Filter fields
    if positive_value_exists(which_marking) \
            and which_marking not in ["not_a_duplicate", "skip"]:
        messages.add_message(request, messages.ERROR,
                             'The filter you are trying to update is not recognized: {which_marking}'
                             ''.format(which_marking=which_marking))
    if positive_value_exists(which_marking) and which_marking in ["not_a_duplicate"]:
        items_processed_successfully = 0
        update = False
        not_a_duplicate = False
        if which_marking == 'not_a_duplicate':
            not_a_duplicate = True
            update = True
        if update:
            if not_a_duplicate:
                for not_a_duplicate_office_we_vote_id in select_for_marking_office_we_vote_ids:
                    results = office_manager.update_or_create_contest_offices_are_not_duplicates(
                        contest_office1_we_vote_id=contest_office_we_vote_id,
                        contest_office2_we_vote_id=not_a_duplicate_office_we_vote_id,
                    )
                    if results['success']:
                        items_processed_successfully += 1
                    else:
                        messages.add_message(request, messages.ERROR,
                                             'ContestOfficesAreNotDuplicates: {status} '
                                             ''.format(status=results['status']))
        messages.add_message(request, messages.INFO,
                             'ContestOfficesAreNotDuplicates added/updated: {items_processed_successfully}'
                             ''.format(items_processed_successfully=items_processed_successfully))

    office_search_results_list = []
    if positive_value_exists(office_search):
        office_queryset = ContestOffice.objects.all()
        office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
        office_queryset = office_queryset.exclude(we_vote_id__iexact=contest_office_we_vote_id)

        if positive_value_exists(state_code):
            office_queryset = office_queryset.filter(state_code__iexact=state_code)

        search_words = office_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(district_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(office_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(vote_usa_office_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(wikipedia_id__iexact=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                office_queryset = office_queryset.filter(final_filters)

        office_search_results_list = list(office_queryset)
    elif contest_office_found:
        ignore_office_we_vote_id_list = [contest_office.we_vote_id]
        results = find_duplicate_contest_office(contest_office, ignore_office_we_vote_id_list)
        if results['contest_office_merge_possibility_found']:
            office_search_results_list = results['contest_office_list']

    # Show the candidates under each office
    candidate_list_manager = CandidateListManager()
    office_search_results_list_modified = []
    for one_office in office_search_results_list:
        if positive_value_exists(one_office.we_vote_id):
            contest_office_option1_results = candidate_list_manager.retrieve_all_candidates_for_office(
                office_we_vote_id=one_office.we_vote_id, read_only=True)
            if contest_office_option1_results['candidate_list_found']:
                one_office.candidates_string = ""
                candidate_list = contest_office_option1_results['candidate_list']
                for one_candidate in candidate_list:
                    one_office.candidates_string += one_candidate.display_candidate_name() + ", "
                    candidate_last_name = one_candidate.extract_last_name()
                    candidate_last_name_lower = candidate_last_name.lower()
                    if candidate_last_name_lower in root_office_candidate_last_names:
                        one_office.candidates_match_root_office = True

        office_search_results_list_modified.append(one_office)

    results = office_manager.retrieve_offices_are_not_duplicates_list(
        contest_office_we_vote_id=contest_office_we_vote_id,
        read_only=True)
    office_search_results_list = office_search_results_list_modified
    office_search_results_list_modified = []
    offices_are_not_duplicates_list_we_vote_ids = results['contest_offices_are_not_duplicates_list_we_vote_ids']
    for one_office in office_search_results_list:
        if one_office.we_vote_id in offices_are_not_duplicates_list_we_vote_ids:
            one_office.not_a_duplicate = True
        office_search_results_list_modified.append(one_office)
    results = {
        'office_search_results_list':   office_search_results_list_modified,
    }
    return results


def office_summary_add_candidates_process_view(
        request,
        contest_office=None,
        existing_candidate_we_vote_id_list=[],
    ):
    """

    :param request:
    :param contest_office:
    :param existing_candidate_we_vote_id_list:
    :return:
    """
    candidate_possibility_search = request.GET.get('candidate_possibility_search', "")
    state_code = request.GET.get('state_code', "")
    status = ''
    volunteer_task_manager = VolunteerTaskManager()
    voter_device_id = get_voter_api_device_id(request)
    voter = fetch_voter_from_voter_device_link(voter_device_id)
    if hasattr(voter, 'we_vote_id'):
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    at_least_one_candidate_created = False
    names_to_search_list = []
    # Break up multiple lines
    candidate_possibility_search_list = candidate_possibility_search.splitlines()
    for one_line in candidate_possibility_search_list:
        one_line_stripped = one_line.strip()
        if positive_value_exists(one_line_stripped) and one_line_stripped not in names_to_search_list:
            names_to_search_list.append(one_line_stripped)

    if contest_office and positive_value_exists(contest_office.state_code):
        state_code = contest_office.state_code
        state_code = state_code.lower()
        if state_code in ['na']:
            state_code = ''

    election_year_as_integer = 0
    if contest_office and positive_value_exists(contest_office.election_date_as_integer):
        election_year_as_integer = contest_office.election_date_as_integer // 10000

    choices_made = {}
    for one_name_to_search in names_to_search_list:
        one_name_slug = slugify(one_name_to_search)
        choices_made[one_name_slug] = request.GET.get("select_for_{one_name_slug}"
                                                      "".format(one_name_slug=one_name_slug))

    # Search among candidates in upcoming elections
    allowed_years = []
    if positive_value_exists(election_year_as_integer):
        allowed_years.append(election_year_as_integer)
    else:
        # Calculate this year
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        current_year = datetime_now.year
        allowed_years.append(current_year)

    # We list all options in a single list of dicts, so we can display complex options
    from candidate.models import CandidateCampaign, CandidateManager
    from politician.models import PoliticianManager
    candidate_manager = CandidateManager()
    politician_manager = PoliticianManager()
    search_result_options_dict = {}
    for one_name_to_search in names_to_search_list:
        candidate_list_limited = []
        candidate_name_already_linked = False
        candidate_name_created = False

        if ' ' not in one_name_to_search:
            last_name = one_name_to_search
        else:
            last_name = extract_last_name_from_full_name(one_name_to_search)
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(candidate_year__in=allowed_years)
        # Find any upcoming candidate with the last name in the name
        queryset = queryset.filter(candidate_name__icontains=last_name)
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        candidate_list = list(queryset)
        candidate_by_we_vote_id_dict = {}
        exclude_politician_we_vote_id_list = []
        for one_candidate in candidate_list:
            if one_candidate.we_vote_id not in candidate_by_we_vote_id_dict:
                candidate_by_we_vote_id_dict[one_candidate.we_vote_id] = one_candidate
            if one_candidate.we_vote_id in existing_candidate_we_vote_id_list:
                candidate_list_limited.append(one_candidate)
                candidate_name_already_linked = True
            if positive_value_exists(one_candidate.politician_we_vote_id):
                exclude_politician_we_vote_id_list.append(one_candidate.politician_we_vote_id)

        # Find all politicians that match the last name
        politician_by_we_vote_id_dict = {}
        from politician.models import Politician
        queryset = Politician.objects.all()
        queryset = queryset.filter(last_name__iexact=last_name)
        if len(exclude_politician_we_vote_id_list) > 0:
            queryset = queryset.exclude(we_vote_id__in=exclude_politician_we_vote_id_list)
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        politician_list = list(queryset)
        for one_politician in politician_list:
            if one_politician.we_vote_id not in politician_by_we_vote_id_dict:
                politician_by_we_vote_id_dict[one_politician.we_vote_id] = one_politician

        # ############################
        # Now process incoming choices for candidate, politician, or "create new"
        create_candidate_for_politician_we_vote_id = None
        create_this_politician = ''
        new_politician = None
        new_politician_created = False
        link_candidate_we_vote_id_to_office = None
        one_name_slug = slugify(one_name_to_search)
        if one_name_slug in choices_made:
            value = choices_made[one_name_slug]
            if is_politician_we_vote_id(value):
                create_candidate_for_politician_we_vote_id = value
            elif is_candidate_we_vote_id(value):
                link_candidate_we_vote_id_to_office = value
            elif value not in ['skip', None]:
                create_this_politician = value
        if positive_value_exists(create_this_politician):
            first_name = extract_first_name_from_full_name(create_this_politician)
            middle_name = extract_middle_name_from_full_name(create_this_politician)
            last_name = extract_last_name_from_full_name(create_this_politician)
            results = politician_manager.create_politician_row_entry(
                politician_name=create_this_politician,
                politician_first_name=first_name,
                politician_middle_name=middle_name,
                politician_last_name=last_name,
                state_code=state_code,
            )
            if not results['success']:
                status += results['status']
                messages.add_message(request, messages.ERROR,
                                     'UNABLE TO CREATE POLITICIAN: {status}'
                                     ''.format(status=status))
            elif results['new_politician_created']:
                messages.add_message(request, messages.INFO,
                                     'Created Politician: {create_this_politician}'
                                     ''.format(create_this_politician=create_this_politician))
                new_politician_created = True
                new_politician = results['new_politician']
                create_candidate_for_politician_we_vote_id = new_politician.we_vote_id
            else:
                status += results['status']
                messages.add_message(request, messages.ERROR,
                                     'Did not create politician: {status}'
                                     ''.format(status=status))

        if new_politician_created:
            politician_list.append(new_politician)
            politician_by_we_vote_id_dict[new_politician.we_vote_id] = new_politician

        if positive_value_exists(create_candidate_for_politician_we_vote_id):
            if create_candidate_for_politician_we_vote_id in politician_by_we_vote_id_dict:
                politician = politician_by_we_vote_id_dict[create_candidate_for_politician_we_vote_id]
                if not hasattr(politician, 'politician_name'):
                    messages.add_message(request, messages.ERROR,
                                         'Did not create candidate from politician-politician object problem: {status}'
                                         ''.format(status=status))
                else:
                    # Create candidate from this politician
                    results = create_candidate_from_politician(create_candidate_for_politician_we_vote_id)
                    if results['success']:
                        one_candidate = results['candidate']
                        candidate_list_limited.append(one_candidate)
                        at_least_one_candidate_created = True
                        candidate_name_created = True
                        if one_candidate.we_vote_id not in candidate_by_we_vote_id_dict:
                            candidate_by_we_vote_id_dict[one_candidate.we_vote_id] = one_candidate
                        link_candidate_we_vote_id_to_office = one_candidate.we_vote_id
                    else:
                        status += results['status']
                        messages.add_message(request, messages.ERROR,
                                             'Did not create candidate from politician: {status}'
                                             ''.format(status=status))
            else:
                messages.add_message(request, messages.ERROR,
                                     'Did not create candidate from politician-object not retrieved: {status}'
                                     ''.format(status=status))

        if (new_politician_created or candidate_name_created or link_candidate_we_vote_id_to_office) \
                and positive_value_exists(voter_we_vote_id):
            try:
                # Give the volunteer who entered this credit
                task_results = volunteer_task_manager.create_volunteer_task_completed(
                    action_constant=VOLUNTEER_ACTION_CANDIDATE_CREATED,
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        if positive_value_exists(link_candidate_we_vote_id_to_office):
            results = candidate_manager.get_or_create_candidate_to_office_link(
                candidate_we_vote_id=link_candidate_we_vote_id_to_office,
                contest_office_we_vote_id=contest_office.we_vote_id,
                google_civic_election_id=contest_office.google_civic_election_id,
                state_code=contest_office.state_code,
            )
            if results['success']:
                if link_candidate_we_vote_id_to_office in candidate_by_we_vote_id_dict:
                    one_candidate = candidate_by_we_vote_id_dict[link_candidate_we_vote_id_to_office]
                    candidate_list_limited.append(one_candidate)
                    at_least_one_candidate_created = True
                    candidate_name_already_linked = True
            else:
                status += results['status']
                messages.add_message(request, messages.ERROR,
                                     'Did not create candidate link to office: {status}'
                                     ''.format(status=status))

        # Bundle up the options into data package
        search_result_option_dict = {
            'candidate_name_created':           candidate_name_created,
            'candidate_name_already_linked':    candidate_name_already_linked,
            'candidate_name_to_search':         one_name_to_search,
            'candidate_slug':                   slugify(one_name_to_search),
            'candidate_list':                   candidate_list_limited
            if candidate_name_already_linked else candidate_list,
            'politician_list':                  politician_list,
        }
        search_result_options_dict[one_name_to_search] = search_result_option_dict

    search_result_options_list = list(search_result_options_dict.values())
    results = {
        'at_least_one_candidate_created':   at_least_one_candidate_created,
        'search_result_options_list':       search_result_options_list,
    }
    return results


@login_required
def office_delete_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    office_id = convert_to_int(request.GET.get('office_id', 0))
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    office_on_stage_found = False
    office_on_stage = ContestOffice()
    office_on_stage_we_vote_id = ''
    try:
        office_on_stage = ContestOffice.objects.get(id=office_id)
        office_on_stage_found = True
        google_civic_election_id = office_on_stage.google_civic_election_id
        office_on_stage_we_vote_id = office_on_stage.we_vote_id
    except ContestOffice.MultipleObjectsReturned as e:
        pass
    except ContestOffice.DoesNotExist:
        pass

    candidates_found_for_this_office = False
    if office_on_stage_found:
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            contest_office_we_vote_id_list=[office_on_stage_we_vote_id])
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        if len(candidate_to_office_link_list):
            candidates_found_for_this_office = True

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
        messages.add_message(request, messages.ERROR, 'Could not delete office -- exception: ' + str(e))
        return HttpResponseRedirect(reverse('office:office_summary', args=(office_id,)))

    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def find_duplicate_office_view(request, office_id=0):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # office_list = []

    number_of_duplicate_contest_offices_processed = 0
    number_of_duplicate_contest_offices_failed = 0
    number_of_duplicates_could_not_process = 0

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    contest_office_manager = ContestOfficeManager()
    contest_office_results = contest_office_manager.retrieve_contest_office_from_id(office_id)
    if not contest_office_results['contest_office_found']:
        messages.add_message(request, messages.ERROR, "Contest Office not found.")
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    contest_office = contest_office_results['contest_office']

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR,
                             "Contest Office must have a google_civic_election_id in order to merge.")
        return HttpResponseRedirect(reverse('office:office_edit', args=(office_id,)))

    ignore_office_we_vote_id_list = [contest_office.we_vote_id]

    results = find_duplicate_contest_office(contest_office, ignore_office_we_vote_id_list)

    # If we find contest offices to merge, stop and ask for confirmation
    if results['contest_office_merge_possibility_found']:
        contest_office_option1_for_template = contest_office
        contest_office_option2_for_template = results['contest_office_merge_possibility']

        # This view function takes us to displaying a template
        remove_duplicate_process = True  # Try to find another office to merge after finishing
        return render_contest_office_merge_form(request, contest_office_option1_for_template,
                                                contest_office_option2_for_template,
                                                results['contest_office_merge_conflict_values'],
                                                remove_duplicate_process)

    message = "Duplicate Offices: Google Civic Election ID: {election_id}, " \
              "{number_of_duplicate_contest_offices_processed} duplicates processed, " \
              "{number_of_duplicate_contest_offices_failed} duplicate merges failed, " \
              "{number_of_duplicates_could_not_process} could not be processed " \
              "".format(election_id=google_civic_election_id,
                        number_of_duplicate_contest_offices_processed=number_of_duplicate_contest_offices_processed,
                        number_of_duplicate_contest_offices_failed=number_of_duplicate_contest_offices_failed,
                        number_of_duplicates_could_not_process=number_of_duplicates_could_not_process)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('office:office_edit', args=(office_id,)) +
                                "?google_civic_election_id={var}".format(
                                var=google_civic_election_id))


@login_required
def find_and_merge_duplicate_offices_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_office_list = []
    ignore_office_we_vote_id_list = []
    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', "")
    contest_office_manager = ContestOfficeManager()

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('office:office_list', args=()))

    try:
        # We sort by ID so that the entry which was saved first becomes the "master"
        contest_office_query = ContestOffice.objects.order_by('id')
        contest_office_query = contest_office_query.filter(google_civic_election_id=google_civic_election_id)
        contest_office_list = list(contest_office_query)
    except ContestOffice.DoesNotExist:
        pass

    # Loop through all the offices in this election to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
        duplicate_office_count = 0
        for contest_office in contest_office_list:
            # Note that we don't reset the ignore_office_we_vote_id_list, so we don't search for a duplicate
            # both directions
            ignore_office_we_vote_id_list.append(contest_office.we_vote_id)
            duplicate_office_count_temp = fetch_duplicate_office_count(contest_office,
                                                                       ignore_office_we_vote_id_list)
            duplicate_office_count += duplicate_office_count_temp

        if positive_value_exists(duplicate_office_count):
            messages.add_message(request, messages.INFO, "There are approximately {duplicate_office_count} "
                                                         "possible duplicates."
                                                         "".format(duplicate_office_count=duplicate_office_count))

    # Loop through all the contest offices in this election
    ignore_office_we_vote_id_list = []
    for contest_office in contest_office_list:
        # Add current contest office entry to the ignore list
        ignore_office_we_vote_id_list.append(contest_office.we_vote_id)
        # Now check to for other contest offices we have labeled as "not a duplicate"
        not_a_duplicate_list = contest_office_manager.fetch_offices_are_not_duplicates_list_we_vote_ids(
            contest_office.we_vote_id)

        ignore_office_we_vote_id_list += not_a_duplicate_list

        results = find_duplicate_contest_office(contest_office, ignore_office_we_vote_id_list)
        ignore_office_we_vote_id_list = []

        # If we find contest offices to merge, stop and ask for confirmation
        if results['contest_office_merge_possibility_found']:
            contest_office_option1_for_template = contest_office
            contest_office_option2_for_template = results['contest_office_merge_possibility']

            # Can we automatically merge these offices?
            merge_results = merge_if_duplicate_offices(
                contest_office_option1_for_template, contest_office_option2_for_template,
                results['contest_office_merge_conflict_values'])

            if merge_results['offices_merged']:
                office = merge_results['office']
                message = "Office '{office_name}' automatically merged.".format(office_name=office.office_name)
                # print_to_log(logger, exception_message_optional=message)
                print("Offices merged:", message)
                # try:
                #     messages.add_message(request, messages.INFO, "Office {office_name} automatically merged."
                #                                                  "".format(office_name=office.office_name))
                # except Exception as e:
                #     pass
                return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                            "?google_civic_election_id=" + str(google_civic_election_id) +
                                            "&state_code=" + str(state_code))
            else:
                if merge_results['success'] is False:
                    messages.add_message(request, messages.INFO, "AUTO_MERGE_ATTEMPT_FAILED: {status} "
                                                                 "".format(status=merge_results['status']))
                # This view function takes us to displaying a template
                remove_duplicate_process = True  # Try to find another office to merge after finishing
                return render_contest_office_merge_form(request, contest_office_option1_for_template,
                                                        contest_office_option2_for_template,
                                                        results['contest_office_merge_conflict_values'],
                                                        remove_duplicate_process)

    message = "Google Civic Election ID: {election_id}, " \
              "No duplicate contest offices found for this election." \
              "".format(election_id=google_civic_election_id)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    state_code=state_code,
                                    ))


def render_contest_office_merge_form(
        request, contest_office_option1_for_template, contest_office_option2_for_template,
        contest_office_merge_conflict_values, remove_duplicate_process=True):
    position_list_manager = PositionListManager()

    bookmark_item_list_manager = BookmarkItemList()

    state_code = ''
    if hasattr(contest_office_option1_for_template, 'state_code'):
        state_code = contest_office_option1_for_template.state_code
    if hasattr(contest_office_option2_for_template, 'state_code'):
        state_code = contest_office_option1_for_template.state_code

    # Get positions counts for both offices
    contest_office_option1_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_contest_office(
            contest_office_option1_for_template.id, contest_office_option1_for_template.we_vote_id)
    contest_office_option1_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_contest_office(
            contest_office_option1_for_template.id, contest_office_option1_for_template.we_vote_id)
    # Bookmarks for option 1
    bookmark_results1 = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_office(
        contest_office_option1_for_template.we_vote_id)
    if bookmark_results1['bookmark_item_list_found']:
        bookmark_item_list = bookmark_results1['bookmark_item_list']
        contest_office_option1_bookmark_count = len(bookmark_item_list)
    else:
        contest_office_option1_bookmark_count = 0
    contest_office_option1_for_template.bookmarks_count = contest_office_option1_bookmark_count

    contest_office_option2_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_contest_office(
            contest_office_option2_for_template.id, contest_office_option2_for_template.we_vote_id)
    contest_office_option2_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_contest_office(
            contest_office_option2_for_template.id, contest_office_option2_for_template.we_vote_id)
    # Bookmarks for option 2
    bookmark_results2 = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_office(
        contest_office_option2_for_template.we_vote_id)
    if bookmark_results2['bookmark_item_list_found']:
        bookmark_item_list = bookmark_results2['bookmark_item_list']
        contest_office_option2_bookmark_count = len(bookmark_item_list)
    else:
        contest_office_option2_bookmark_count = 0
    contest_office_option2_for_template.bookmarks_count = contest_office_option2_bookmark_count

    # Show the candidates under each office
    candidate_list_manager = CandidateListManager()
    if positive_value_exists(contest_office_option1_for_template.we_vote_id):
        contest_office_option1_results = candidate_list_manager.retrieve_all_candidates_for_office(
            office_we_vote_id=contest_office_option1_for_template.we_vote_id, read_only=True)
        if contest_office_option1_results['candidate_list_found']:
            contest_office_option1_for_template.candidates_string = ""
            candidate_list = contest_office_option1_results['candidate_list']
            for one_candidate in candidate_list:
                contest_office_option1_for_template.candidates_string += one_candidate.display_candidate_name() + ", "

    if positive_value_exists(contest_office_option2_for_template.we_vote_id):
        contest_office_option2_results = candidate_list_manager.retrieve_all_candidates_for_office(
            office_we_vote_id=contest_office_option2_for_template.we_vote_id, read_only=True)
        if contest_office_option2_results['candidate_list_found']:
            contest_office_option2_for_template.candidates_string = ""
            candidate_list = contest_office_option2_results['candidate_list']
            for one_candidate in candidate_list:
                contest_office_option2_for_template.candidates_string += one_candidate.display_candidate_name() + ", "

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'contest_office_option1':   contest_office_option1_for_template,
        'contest_office_option2':   contest_office_option2_for_template,
        'conflict_values':          contest_office_merge_conflict_values,
        'google_civic_election_id': contest_office_option1_for_template.google_civic_election_id,
        'remove_duplicate_process': remove_duplicate_process,
        'state_code':               state_code,
    }
    return render(request, 'office/office_merge.html', template_values)


@login_required
def office_merge_process_view(request):
    """
    Process the merging of two offices. Note this is similar to office/controllers.py "merge_these_two_offices"
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_office_manager = ContestOfficeManager()

    is_post = True if request.method == 'POST' else False

    if is_post:
        # merge = request.POST.get('merge', False)
        skip = request.POST.get('skip', False)
        # Contest office 1 is the one we keep, and Contest office 2 is the one we will merge into Contest office 1
        contest_office1_we_vote_id = request.POST.get('contest_office1_we_vote_id', 0)
        contest_office2_we_vote_id = request.POST.get('contest_office2_we_vote_id', 0)
        google_civic_election_id = request.POST.get('google_civic_election_id', 0)
        redirect_to_contest_office_list = positive_value_exists(request.POST.get('redirect_to_contest_office_list', False))
        remove_duplicate_process = positive_value_exists(request.POST.get('remove_duplicate_process', False))
        state_code = request.POST.get('state_code', '')
    else:
        # merge = request.GET.get('merge', False)
        skip = request.GET.get('skip', False)
        # Contest office 1 is the one we keep, and Contest office 2 is the one we will merge into Contest office 1
        contest_office1_we_vote_id = request.GET.get('contest_office1_we_vote_id', 0)
        contest_office2_we_vote_id = request.GET.get('contest_office2_we_vote_id', 0)
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        redirect_to_contest_office_list = positive_value_exists(request.GET.get('redirect_to_contest_office_list', False))
        remove_duplicate_process = positive_value_exists(request.GET.get('remove_duplicate_process', False))
        state_code = request.GET.get('state_code', '')

    if positive_value_exists(skip):
        results = contest_office_manager.update_or_create_contest_offices_are_not_duplicates(
            contest_office1_we_vote_id, contest_office2_we_vote_id)
        if not results['new_contest_offices_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save contest_offices_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior contest offices skipped, and not merged.')
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    contest_office1_results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office1_we_vote_id)
    if contest_office1_results['contest_office_found']:
        contest_office1_on_stage = contest_office1_results['contest_office']
        contest_office1_id = contest_office1_on_stage.id
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve office 1.')
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    contest_office2_results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office2_we_vote_id)
    if contest_office2_results['contest_office_found']:
        contest_office2_on_stage = contest_office2_results['contest_office']
        contest_office2_id = contest_office2_on_stage.id
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve contest office 2.')
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    # # TODO: Migrate bookmarks
    # bookmark_item_list_manager = BookmarkItemList()
    # bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_office(
    #     contest_office2_we_vote_id)
    # if bookmark_results['bookmark_item_list_found']:
    #     messages.add_message(request, messages.ERROR, "Bookmarks found for Contest Office 2 - "
    #                                                   "automatic merge not working yet.")
    #     return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
    #                                 "?google_civic_election_id=" + str(google_civic_election_id) +
    #                                 "&state_code=" + str(state_code))

    # Merge attribute values
    conflict_values = figure_out_office_conflict_values(contest_office1_on_stage, contest_office2_on_stage)

    for attribute in CONTEST_OFFICE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            if is_post:
                choice = request.POST.get(attribute + '_choice', '')
            else:
                choice = request.GET.get(attribute + '_choice', '')
            if contest_office2_we_vote_id == choice:
                setattr(contest_office1_on_stage, attribute, getattr(contest_office2_on_stage, attribute))
        elif conflict_value == "CONTEST_OFFICE2":
            setattr(contest_office1_on_stage, attribute, getattr(contest_office2_on_stage, attribute))
        else:
            pass

    # Preserve unique google_civic_office_name, _name2, _name3, _name4, and _name5
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name2):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name2)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name3):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name3)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name4):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name4)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name5):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name5)

    # TODO: Merge quick_info's office details in future

    # Merge ballot item's office details
    ballot_items_results = move_ballot_items_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                               contest_office1_id, contest_office1_we_vote_id,
                                                               contest_office1_on_stage)
    if not ballot_items_results['success']:
        messages.add_message(request, messages.ERROR, ballot_items_results['status'])
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Merge public positions - DALE 2020-06-04 I think we will want to alter this soon
    public_positions_results = move_positions_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                                contest_office1_id, contest_office1_we_vote_id,
                                                                True)
    if not public_positions_results['success']:
        messages.add_message(request, messages.ERROR, public_positions_results['status'])
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Merge friends-only positions - DALE 2020-06-04 I think we will want to alter this soon
    friends_positions_results = move_positions_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                                 contest_office1_id, contest_office1_we_vote_id,
                                                                 False)
    if not friends_positions_results['success']:
        messages.add_message(request, messages.ERROR, friends_positions_results['status'])
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # TODO: Migrate images?

    # Finally, move candidates last
    candidates_results = move_candidates_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                           contest_office1_id, contest_office1_we_vote_id)
    if not candidates_results['success']:
        messages.add_message(request, messages.ERROR, candidates_results['status'])
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Save contest_office2_on_stage to remove maplight_id, which much be unique,
    #  before we try to save contest_office1_on_stage below
    if positive_value_exists(contest_office2_on_stage.maplight_id):
        contest_office2_on_stage.maplight_id = None
        contest_office2_on_stage.save()

    # Note: wait to wrap in try/except block
    contest_office1_on_stage.save()
    # There isn't any office data to refresh from other master tables

    # Remove contest office 2
    contest_office2_on_stage.delete()

    if redirect_to_contest_office_list:
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('office:find_and_merge_duplicate_offices', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('office:office_summary', args=(contest_office1_on_stage.id,)))
