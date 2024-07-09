# representative/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import fetch_duplicate_representative_count, figure_out_representative_conflict_values, \
    find_duplicate_representative, merge_if_duplicate_representatives, merge_these_two_representatives, \
    representative_politician_match, update_representative_details_from_politician
from .models import attach_defaults_values_to_representative_object, Representative, RepresentativeManager, \
    REPRESENTATIVE_UNIQUE_IDENTIFIERS
from exception.models import handle_record_not_found_exception, handle_record_found_more_than_one_exception, \
    print_to_log, handle_record_not_saved_exception
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import datetime, timedelta
import pytz
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.timezone import localtime, now
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from django.db.models import Q
from django.db.models.functions import Length
import json
from office_held.models import OfficeHeld, OfficeHeldManager
from election.models import Election
from politician.models import Politician, PoliticianManager
from twitter.models import TwitterUserManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP, \
    extract_instagram_handle_from_text_string, extract_twitter_handle_from_text_string, \
    convert_to_political_party_constant, \
    extract_first_name_from_full_name, \
    extract_last_name_from_full_name, extract_state_from_ocd_division_id
from wevote_functions.functions_date import generate_localized_datetime_from_obj
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE, OFFICE_HELD_YEARS_AVAILABLE

OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
REPRESENTATIVES_SYNC_URL = "https://api.wevoteusa.org/apis/v1/representativesSyncOut/"
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def compare_two_representatives_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    representative_year = request.GET.get('representative_year', 0)
    representative1_we_vote_id = request.GET.get('representative1_we_vote_id', '')
    representative2_we_vote_id = request.GET.get('representative2_we_vote_id', '')
    state_code = request.GET.get('state_code', '')

    representative_manager = RepresentativeManager()
    representative_results = representative_manager.retrieve_representative_from_we_vote_id(
        representative1_we_vote_id, read_only=True)
    if not representative_results['representative_found']:
        messages.add_message(request, messages.ERROR, "Representative1 not found.")
        return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    representative_option1_for_template = representative_results['representative']

    representative_results = representative_manager.retrieve_representative_from_we_vote_id(
        representative2_we_vote_id, read_only=True)
    if not representative_results['representative_found']:
        messages.add_message(request, messages.ERROR, "Representative2 not found.")
        return HttpResponseRedirect(reverse('representative:representative_edit',
                                            args=(representative_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    representative_option2_for_template = representative_results['representative']

    representative_merge_conflict_values = figure_out_representative_conflict_values(
        representative_option1_for_template, representative_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_representative_merge_form(
        request,
        representative_option1_for_template,
        representative_option2_for_template,
        representative_merge_conflict_values,
        state_code=state_code,
        remove_duplicate_process=remove_duplicate_process)


@login_required
def find_and_merge_duplicate_representatives_view(request):
    status = ""
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', "")
    representative_manager = RepresentativeManager()

    representative_list = []
    try:
        representative_query = Representative.objects.all()
        representative_query = representative_query.filter(state_code__iexact=state_code)
        representative_list = list(representative_query)
    except Exception as e:
        status += "REPRESENTATIVE_QUERY_FAILED: " + str(e) + " "

    # Loop through all the representatives in this election to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
        ignore_representative_we_vote_id_list = []
        duplicate_representative_count = 0
        for we_vote_representative in representative_list:
            # Note that we don't reset the ignore_representative_list. We don't search for a duplicate both directions
            ignore_representative_we_vote_id_list.append(we_vote_representative.we_vote_id)
            duplicate_representative_count_temp = \
                fetch_duplicate_representative_count(we_vote_representative, ignore_representative_we_vote_id_list)
            duplicate_representative_count += duplicate_representative_count_temp

        if positive_value_exists(duplicate_representative_count):
            messages.add_message(request, messages.INFO,
                                 "There are approximately {duplicate_representative_count} possible duplicates."
                                 "".format(duplicate_representative_count=duplicate_representative_count))

    # Loop through all the representatives in this year or election
    ignore_representative_we_vote_id_list = []
    for we_vote_representative in representative_list:
        # Add current representative entry to ignore list
        ignore_representative_we_vote_id_list.append(we_vote_representative.we_vote_id)
        # Now check to for other representatives we have labeled as "not a duplicate"
        not_a_duplicate_list = representative_manager.fetch_representatives_are_not_duplicates_list_we_vote_ids(
            we_vote_representative.we_vote_id)

        ignore_representative_we_vote_id_list += not_a_duplicate_list

        results = find_duplicate_representative(
            we_vote_representative, ignore_representative_we_vote_id_list, read_only=True)
        ignore_representative_we_vote_id_list = []

        # If we find representatives to merge, stop and ask for confirmation (if we need to)
        if results['representative_merge_possibility_found']:
            representative_option1_for_template = we_vote_representative
            representative_option2_for_template = results['representative_merge_possibility']

            # Can we automatically merge these representatives?
            merge_results = merge_if_duplicate_representatives(
                representative_option1_for_template,
                representative_option2_for_template,
                results['representative_merge_conflict_values'])

            if not merge_results['success']:
                status += merge_results['status']
                messages.add_message(request, messages.ERROR, status)
                return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                            "?google_civic_election_id={google_civic_election_id}"
                                            "&state_code={state_code}"
                                            "".format(
                                                google_civic_election_id=google_civic_election_id,
                                                state_code=state_code))

            elif merge_results['representatives_merged']:
                representative = merge_results['representative']
                messages.add_message(request, messages.INFO,
                                     "Representative {representative_name} automatically merged."
                                     "".format(representative_name=representative.representative_name))
            else:
                messages.add_message(request, messages.INFO, merge_results['status'])
                remove_duplicate_process = True  # Try to find another representative to merge after finishing
                return render_representative_merge_form(
                    request,
                    representative_option1_for_template,
                    representative_option2_for_template,
                    results['representative_merge_conflict_values'],
                    remove_duplicate_process=remove_duplicate_process)

    if positive_value_exists(state_code):
        message = "No more duplicate representatives found"
        message += " in {state_code}.".format(state_code=state_code)
    else:
        message = 'Please filter by a state before trying to find duplicate representatives.'

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    state_code=state_code))


@login_required
def find_duplicate_representative_view(request, representative_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    number_of_duplicate_representatives_processed = 0
    number_of_duplicate_representatives_failed = 0
    number_of_duplicates_could_not_process = 0

    representative_year = request.GET.get('representative_year', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    representative_manager = RepresentativeManager()
    representative_results = representative_manager.retrieve_representative_from_id(representative_id)
    if not representative_results['representative_found']:
        messages.add_message(request, messages.ERROR, "Representative not found.")
        return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    representative = representative_results['representative']

    ignore_representative_we_vote_id_list = []
    ignore_representative_we_vote_id_list.append(representative.we_vote_id)

    results = find_duplicate_representative(representative, ignore_representative_we_vote_id_list, read_only=True)

    # If we find representatives to merge, stop and ask for confirmation
    if results['representative_merge_possibility_found']:
        representative_option1_for_template = representative
        representative_option2_for_template = results['representative_merge_possibility']

        # This view function takes us to displaying a template
        remove_duplicate_process = True  # Try to find another representative to merge after finishing
        return render_representative_merge_form(
            request,
            representative_option1_for_template,
            representative_option2_for_template,
            results['representative_merge_conflict_values'],
            representative_year=representative_year,
            remove_duplicate_process=remove_duplicate_process)

    message = "Duplicate Representative: " \
              "{number_of_duplicate_representatives_processed} duplicates processed, " \
              "{number_of_duplicate_representatives_failed} duplicate merges failed, " \
              "{number_of_duplicates_could_not_process} could not be processed " \
              "".format(election_id=google_civic_election_id,
                        number_of_duplicate_representatives_processed=number_of_duplicate_representatives_processed,
                        number_of_duplicate_representatives_failed=number_of_duplicate_representatives_failed,
                        number_of_duplicates_could_not_process=number_of_duplicates_could_not_process)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)) +
                                "?google_civic_election_id={var}".format(
                                var=google_civic_election_id))


def render_representative_merge_form(
        request,
        representative_option1_for_template,
        representative_option2_for_template,
        representative_merge_conflict_values,
        representative_year=0,
        remove_duplicate_process=True,
        state_code=''):
    if not positive_value_exists(state_code):
        if hasattr(representative_option1_for_template, 'state_code'):
            state_code = representative_option1_for_template.state_code
        if hasattr(representative_option2_for_template, 'state_code'):
            state_code = representative_option2_for_template.state_code

    representative_manager = RepresentativeManager()
    # position_list_manager = PositionListManager()
    #
    # # Get positions counts for both representatives
    # representative_option1_for_template.public_positions_count = \
    #     position_list_manager.fetch_public_positions_count_for_representative(
    #         representative_option1_for_template.id, representative_option1_for_template.we_vote_id)
    # representative_option1_for_template.friends_positions_count = \
    #     position_list_manager.fetch_friends_only_positions_count_for_representative(
    #         representative_option1_for_template.id, representative_option1_for_template.we_vote_id)
    #
    # representative_option2_for_template.public_positions_count = \
    #     position_list_manager.fetch_public_positions_count_for_representative(
    #         representative_option2_for_template.id, representative_option2_for_template.we_vote_id)
    # representative_option2_for_template.friends_positions_count = \
    #     position_list_manager.fetch_friends_only_positions_count_for_representative(
    #         representative_option2_for_template.id, representative_option2_for_template.we_vote_id)

    # # Which elections is this representative in?
    # results = representative_manager.retrieve_representative_to_office_link_list(
    #     representative_we_vote_id_list=[representative_option1_for_template.we_vote_id])
    # representative_option1_representative_to_office_link_list = results['representative_to_office_link_list']
    # results = representative_manager.retrieve_representative_to_office_link_list(
    #     representative_we_vote_id_list=[representative_option2_for_template.we_vote_id])
    # representative_option2_representative_to_office_link_list = results['representative_to_office_link_list']

    # contest_office_mismatch = True
    # for option1_link in representative_option1_representative_to_office_link_list:
    #     for option2_link in representative_option2_representative_to_office_link_list:
    #         if option1_link.contest_office_we_vote_id == option2_link.contest_office_we_vote_id:
    #             contest_office_mismatch = False

    messages_on_stage = get_messages(request)
    template_values = {
        'representative_option1':   representative_option1_for_template,
        'representative_option2':   representative_option2_for_template,
        'representative_year':      representative_year,
        'conflict_values':          representative_merge_conflict_values,
        'messages_on_stage':        messages_on_stage,
        'remove_duplicate_process': remove_duplicate_process,
        'state_code':               state_code,
    }
    return render(request, 'representative/representative_merge.html', template_values)


@login_required
def repair_ocd_id_mismatch_damage_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    representative_we_vote_id_list = []
    representatives_dict = {}

    representative_error_count = 0
    representative_list_count = 0
    states_already_match_count = 0
    states_fixed_count = 0
    states_to_be_fixed_count = 0
    status = ''
    try:
        queryset = Representative.objects.all()
        queryset = queryset.filter(ocd_id_state_mismatch_found=True)
        representative_list = list(queryset[:1000])
        representative_list_count = len(representative_list)
        for one_representative in representative_list:
            # Now find all representative ids related to this representative
            try:
                if positive_value_exists(one_representative.ocd_division_id) and \
                        positive_value_exists(one_representative.state_code):
                    # Is there a mismatch between the ocd_id and the representative.state_code?
                    state_code_from_ocd_id = extract_state_from_ocd_division_id(one_representative.ocd_division_id)
                    if not positive_value_exists(state_code_from_ocd_id):
                        # Cannot compare
                        pass
                    elif one_representative.state_code.lower() == state_code_from_ocd_id.lower():
                        # Already ok
                        states_already_match_count += 1
                    else:
                        # Fix
                        states_to_be_fixed_count += 1
                        one_representative.state_code = state_code_from_ocd_id
                        one_representative.seo_friendly_path = None
                        one_representative.seo_friendly_path_date_last_updated = now()
                        one_representative.save()
                        states_fixed_count += 1
            except Exception as e:
                representative_error_count += 1
                if representative_error_count < 10:
                    status += "COULD_NOT_SAVE_REPRESENTATIVE: " + str(e) + " "
            representatives_dict[one_representative.we_vote_id] = one_representative
            representative_we_vote_id_list.append(one_representative.we_vote_id)
    except Exception as e:
        status += "GENERAL_ERROR: " + str(e) + " "

    messages.add_message(request, messages.INFO,
                         "Representatives analyzed: {representative_list_count:,}. "
                         "states_already_match_count: {states_already_match_count:,}. "
                         "states_to_be_fixed_count: {states_to_be_fixed_count} "
                         "status: {status}"
                         "".format(
                             representative_list_count=representative_list_count,
                             states_already_match_count=states_already_match_count,
                             states_to_be_fixed_count=states_to_be_fixed_count,
                             status=status))

    return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                "?google_civic_election_id={google_civic_election_id}"
                                "&state_code={state_code}"
                                "&show_ocd_id_state_mismatch=1"
                                "".format(
                                    google_civic_election_id=google_civic_election_id,
                                    state_code=state_code))


@login_required
def representatives_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    status = ""
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in REPRESENTATIVES_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')

    from representative.controllers import representatives_import_from_master_server
    results = representatives_import_from_master_server(request, state_code)
    if results['success']:
        messages.add_message(request, messages.INFO, 'Representatives import completed. '
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

    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" + str(google_civic_election_id) +  "&state_code=" + str(state_code))


@login_required
def representative_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    messages_on_stage = get_messages(request)
    missing_politician = positive_value_exists(request.GET.get('missing_politician', False))
    representative_search = request.GET.get('representative_search', '')
    show_all = positive_value_exists(request.GET.get('show_all', False))
    show_battleground = positive_value_exists(request.GET.get('show_battleground', False))
    show_representatives_with_email = positive_value_exists(request.GET.get('show_representatives_with_email', False))
    show_this_year = convert_to_int(request.GET.get('show_this_year', 9999))
    if show_this_year == 9999:
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        show_this_year = datetime_now.year
    show_ocd_id_state_mismatch = positive_value_exists(request.GET.get('show_ocd_id_state_mismatch', False))
    state_code = request.GET.get('state_code', '')

    # Update representatives who currently don't have seo_friendly_path, with value from linked politician
    number_to_update = 1000
    seo_friendly_path_updates = True
    if seo_friendly_path_updates:
        seo_update_query = Representative.objects.all()
        seo_update_query = seo_update_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        seo_update_query = seo_update_query.filter(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        # After initial updates to all representatives, include in the search logic to find representatives with
        # seo_friendly_path_date_last_updated older than Politician.seo_friendly_path_date_last_updated
        if positive_value_exists(state_code):
            seo_update_query = seo_update_query.filter(state_code__iexact=state_code)
        total_to_convert = seo_update_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        representative_list = list(seo_update_query[:number_to_update])
        update_list = []
        updates_needed = False
        updates_made = 0
        politician_we_vote_id_list = []
        # Retrieve all relevant politicians in a single query
        for one_representative in representative_list:
            politician_we_vote_id_list.append(one_representative.politician_we_vote_id)
        politician_manager = PoliticianManager()
        politician_list = []
        if len(politician_we_vote_id_list) > 0:
            politician_results = politician_manager.retrieve_politician_list(
                politician_we_vote_id_list=politician_we_vote_id_list)
            politician_list = politician_results['politician_list']
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        datetime_now = generate_localized_datetime_from_obj()[1]
        for one_representative in representative_list:
            one_politician = politician_dict_list.get(one_representative.politician_we_vote_id)
            if one_politician and positive_value_exists(one_politician.seo_friendly_path):
                one_representative.seo_friendly_path = one_politician.seo_friendly_path
                one_representative.seo_friendly_path_date_last_updated = datetime_now
                update_list.append(one_representative)
                updates_needed = True
                updates_made += 1
        if updates_needed:
            Representative.objects.bulk_update(
                update_list, ['seo_friendly_path', 'seo_friendly_path_date_last_updated'])
            messages.add_message(request, messages.INFO,
                                 "{updates_made:,} representatives updated with new seo_friendly_path. "
                                 "{total_to_convert_after:,} remaining."
                                 "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made))

    # Update representatives who don't have representative.office_held_district_name
    number_to_update = 1000
    populate_once_with_cached_data = True
    if populate_once_with_cached_data:
        cache_query = Representative.objects.all()
        cache_query = cache_query.exclude(
            Q(office_held_we_vote_id__isnull=True) |
            Q(office_held_we_vote_id="")
        )
        cache_query = cache_query.filter(
            Q(office_held_district_name__isnull=True) |
            Q(office_held_district_name="")
        )
        cache_query = cache_query.values_list('office_held_we_vote_id', flat=True).distinct()
        total_to_convert = cache_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        office_held_we_vote_id_list = cache_query[:number_to_update]

        office_held_dict_list = {}
        if len(office_held_we_vote_id_list) > 0:
            office_held_queryset = OfficeHeld.objects.all()
            office_held_queryset = office_held_queryset.filter(we_vote_id__in=office_held_we_vote_id_list)
            office_held_list = list(office_held_queryset)
            for office_held in office_held_list:
                if office_held.we_vote_id not in office_held_dict_list:
                    office_held_dict_list[office_held.we_vote_id] = office_held

        cache_query2 = Representative.objects.all()
        cache_query2 = cache_query2.filter(office_held_we_vote_id__in=office_held_we_vote_id_list)
        cache_query2 = cache_query2.filter(
            Q(office_held_district_name__isnull=True) |
            Q(office_held_district_name="")
        )
        representative_list_to_update = list(cache_query2)
        update_list = []
        updates_made = 0
        updates_needed = False
        for representative in representative_list_to_update:
            one_office_held = office_held_dict_list.get(representative.office_held_we_vote_id)
            if positive_value_exists(one_office_held.district_name):
                representative.office_held_district_name = one_office_held.district_name
                update_list.append(representative)
                updates_needed = True
                updates_made += 1
        if updates_needed:
            Representative.objects.bulk_update(update_list, ['office_held_district_name'])
            messages.add_message(request, messages.INFO,
                                 "{updates_made:,} representatives updated with new district_name. "
                                 "{total_to_convert_after:,} remaining."
                                 "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made))

    # Update candidates who currently don't have linked_campaignx_we_vote_id, with value from linked politician
    number_to_update = 1000
    campaignx_we_vote_id_updates = True
    if campaignx_we_vote_id_updates:
        campaignx_update_query = Representative.objects.all()
        campaignx_update_query = campaignx_update_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        campaignx_update_query = campaignx_update_query.filter(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        # After initial updates to all representatives, include in the search logic to find representatives with
        # linked_campaignx_we_vote_id_date_last_updated older than
        # Politician.linked_campaignx_we_vote_id_date_last_updated
        if positive_value_exists(state_code):
            campaignx_update_query = campaignx_update_query.filter(state_code__iexact=state_code)
        total_to_convert = campaignx_update_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        campaignx_update_query = campaignx_update_query.order_by('-id')
        representative_list = list(campaignx_update_query[:number_to_update])
        politician_we_vote_id_list = []
        # Retrieve all relevant politicians in a single query
        for one_representative in representative_list:
            if positive_value_exists(one_representative.politician_we_vote_id):
                politician_we_vote_id_list.append(one_representative.politician_we_vote_id)
        politician_manager = PoliticianManager()
        politician_list = []
        if len(politician_we_vote_id_list) > 0:
            politician_results = politician_manager.retrieve_politician_list(
                politician_we_vote_id_list=politician_we_vote_id_list)
            politician_list = politician_results['politician_list']
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        datetime_now = generate_localized_datetime_from_obj()[1]
        linked_campaignx_we_vote_id_missing = 0
        update_list = []
        updates_needed = False
        updates_made = 0
        for one_representative in representative_list:
            one_politician = politician_dict_list.get(one_representative.politician_we_vote_id)
            if not hasattr(one_politician, 'linked_campaignx_we_vote_id'):
                continue
            if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
                one_representative.linked_campaignx_we_vote_id = one_politician.linked_campaignx_we_vote_id
                one_representative.linked_campaignx_we_vote_id_date_last_updated = datetime_now
                update_list.append(one_representative)
                updates_needed = True
                updates_made += 1
            else:
                linked_campaignx_we_vote_id_missing += 1
        if positive_value_exists(linked_campaignx_we_vote_id_missing):
            messages.add_message(request, messages.ERROR,
                                 "{linked_campaignx_we_vote_id_missing:,} missing linked_campaignx_we_vote_id."
                                 "".format(linked_campaignx_we_vote_id_missing=linked_campaignx_we_vote_id_missing))
        if updates_needed:
            Representative.objects.bulk_update(
                update_list, ['linked_campaignx_we_vote_id', 'linked_campaignx_we_vote_id_date_last_updated'])
            messages.add_message(request, messages.INFO,
                                 "{updates_made:,} representatives updated with new linked_campaignx_we_vote_id. "
                                 "{total_to_convert_after:,} remaining."
                                 "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made))

    representative_count = 0
    representative_list = []
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        queryset = Representative.objects.all()
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
                queryset = queryset.filter(final_filters)
        if positive_value_exists(state_code):
            if state_code.lower() == 'na':
                queryset = queryset.filter(
                    Q(state_code__isnull=True) |
                    Q(state_code='')
                )
            else:
                queryset = queryset.filter(state_code__iexact=state_code)

        if positive_value_exists(show_representatives_with_email):
            queryset = queryset.annotate(representative_email_length=Length('representative_email'))
            queryset = queryset.annotate(representative_email2_length=Length('representative_email2'))
            queryset = queryset.annotate(representative_email3_length=Length('representative_email3'))
            queryset = queryset.filter(
                Q(representative_email_length__gt=2) |
                Q(representative_email2_length__gt=2) |
                Q(representative_email3_length__gt=2)
            )

        if positive_value_exists(missing_politician):
            queryset = queryset.filter(
                Q(politician_we_vote_id__isnull=True) |
                Q(politician_we_vote_id='')
            )

        if positive_value_exists(show_this_year):
            if show_this_year in OFFICE_HELD_YEARS_AVAILABLE:
                year_field_name = 'year_in_office_' + str(show_this_year)
                queryset = queryset.filter(**{year_field_name: True})

        if positive_value_exists(show_ocd_id_state_mismatch):
            queryset = queryset.filter(
                Q(ocd_id_state_mismatch_found=True)
            )

        if positive_value_exists(representative_search):
            search_words = representative_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(office_held_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(office_held_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                new_filter = Q(political_party__icontains=one_word)
                filters.append(new_filter)

                new_filter = (
                    Q(representative_email__icontains=one_word) |
                    Q(representative_email2__icontains=one_word) |
                    Q(representative_email3__icontains=one_word)
                )
                filters.append(new_filter)

                new_filter = Q(representative_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = (
                    Q(representative_twitter_handle__icontains=one_word) |
                    Q(representative_twitter_handle2__icontains=one_word) |
                    Q(representative_twitter_handle3__icontains=one_word)
                )
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    queryset = queryset.filter(final_filters)

        representative_count = queryset.count()
        if positive_value_exists(show_all):
            representative_list = list(queryset[:1000])
        else:
            representative_list = list(queryset[:200])
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Cycle through all Representatives and find unlinked Candidates that *might* be "children" of this
    # representative
    temp_representative_list = []
    for one_representative in representative_list:
        try:
            filters = []
            if positive_value_exists(one_representative.representative_twitter_handle):
                new_filter = (
                    Q(candidate_twitter_handle__iexact=one_representative.representative_twitter_handle) |
                    Q(candidate_twitter_handle2__iexact=one_representative.representative_twitter_handle) |
                    Q(candidate_twitter_handle3__iexact=one_representative.representative_twitter_handle)
                )
                filters.append(new_filter)

            if positive_value_exists(one_representative.vote_smart_id):
                new_filter = Q(vote_smart_id=one_representative.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

        except Exception as e:
            related_candidate_list_count = 0

        temp_representative_list.append(one_representative)

    representative_list = temp_representative_list

    election_list = Election.objects.order_by('-election_day_text')

    if positive_value_exists(representative_count):
        messages.add_message(request, messages.INFO,
                             "{representative_count:,} representatives found."
                             "".format(representative_count=representative_count))

    template_values = {
        'messages_on_stage':                messages_on_stage,
        'missing_politician':               missing_politician,
        'google_civic_election_id':         google_civic_election_id,
        'election_list':                    election_list,
        'representative_list':              representative_list,
        'representative_search':            representative_search,
        'show_all':                         show_all,
        'show_battleground':                show_battleground,
        'show_representatives_with_email':  show_representatives_with_email,
        'show_this_year':                   show_this_year,
        'show_ocd_id_state_mismatch':       show_ocd_id_state_mismatch,
        'state_code':                       state_code,
        'state_list':                       sorted_state_list,
        'years_available':                  OFFICE_HELD_YEARS_AVAILABLE,
    }
    return render(request, 'representative/representative_list.html', template_values)


@login_required
def representative_merge_process_view(request):
    """
    Process the merging of two representatives
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    representative_manager = RepresentativeManager()

    is_post = True if request.method == 'POST' else False

    if is_post:
        merge = request.POST.get('merge', False)
        skip = request.POST.get('skip', False)

        # Representative 1 is the one we keep, and Representative 2 is the one we will merge into Representative 1
        representative_year = request.POST.get('representative_year', 0)
        representative1_we_vote_id = request.POST.get('representative1_we_vote_id', 0)
        representative2_we_vote_id = request.POST.get('representative2_we_vote_id', 0)
        google_civic_election_id = request.POST.get('google_civic_election_id', 0)
        redirect_to_representative_list = request.POST.get('redirect_to_representative_list', False)
        remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
        state_code = request.POST.get('state_code', '')
    else:
        merge = request.GET.get('merge', False)
        skip = request.GET.get('skip', False)

        # Representative 1 is the one we keep, and Representative 2 is the one we will merge into Representative 1
        representative_year = request.GET.get('representative_year', 0)
        representative1_we_vote_id = request.GET.get('representative1_we_vote_id', 0)
        representative2_we_vote_id = request.GET.get('representative2_we_vote_id', 0)
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        redirect_to_representative_list = request.GET.get('redirect_to_representative_list', False)
        remove_duplicate_process = request.GET.get('remove_duplicate_process', False)
        state_code = request.GET.get('state_code', '')

    if positive_value_exists(skip):
        results = representative_manager.update_or_create_representatives_are_not_duplicates(
            representative1_we_vote_id, representative2_we_vote_id)
        if not results['new_representatives_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save representatives_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior representatives skipped, and not merged.')
        return HttpResponseRedirect(reverse('representative:find_and_merge_duplicate_representatives', args=()) +
                                    "?representative_year=" + str(representative_year) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    representative1_results = \
        representative_manager.retrieve_representative_from_we_vote_id(representative1_we_vote_id, read_only=True)
    if representative1_results['representative_found']:
        representative1_on_stage = representative1_results['representative']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve representative 1.')
        return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_representatives=' + str(representative_year) +
                                    '&state_code=' + str(state_code))

    representative2_results = \
        representative_manager.retrieve_representative_from_we_vote_id(representative2_we_vote_id, read_only=True)
    if representative2_results['representative_found']:
        representative2_on_stage = representative2_results['representative']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve representative 2.')
        return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_representatives=' + str(representative_year) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_values = figure_out_representative_conflict_values(representative1_on_stage, representative2_on_stage)
    admin_merge_choices = {}
    for attribute in REPRESENTATIVE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            if is_post:
                choice = request.POST.get(attribute + '_choice', '')
            else:
                choice = request.GET.get(attribute + '_choice', '')
            if representative2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(representative2_on_stage, attribute)
        elif conflict_value == "REPRESENTATIVE2":
            admin_merge_choices[attribute] = getattr(representative2_on_stage, attribute)
        elif conflict_value == "REPRESENTATIVE1":
            admin_merge_choices[attribute] = getattr(representative1_on_stage, attribute)

    merge_results = merge_these_two_representatives(
        representative1_we_vote_id,
        representative2_we_vote_id,
        admin_merge_choices)

    if positive_value_exists(merge_results['representatives_merged']):
        representative = merge_results['representative']
        messages.add_message(request, messages.INFO, "Representative '{representative_name}' merged."
                                                     "".format(representative_name=representative.representative_name))
    else:
        # NOTE: We could also redirect to a page to look specifically at these two representatives, but this should
        # also get you back to looking at the two representatives
        messages.add_message(request, messages.ERROR, merge_results['status'])
        return HttpResponseRedirect(reverse('representative:find_and_merge_duplicate_representatives', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    '&representative_year=' + str(representative_year) +
                                    "&auto_merge_off=1" +
                                    "&state_code=" + str(state_code))

    if redirect_to_representative_list:
        return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_representatives=' + str(representative_year) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('representative:find_and_merge_duplicate_representatives', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    '&representative_year=' + str(representative_year) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative1_on_stage.id,)))


@login_required
def representative_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    office_held_id = request.GET.get('office_held_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    representative_name = request.GET.get('representative_name', "")
    google_civic_representative_name = request.GET.get('google_civic_representative_name', "")
    state_code = request.GET.get('state_code', "")
    representative_twitter_handle = request.GET.get('representative_twitter_handle', "")
    representative_url = request.GET.get('representative_url', "")
    political_party = request.GET.get('political_party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    representative_we_vote_id = request.GET.get('representative_we_vote_id', "")

    # These are the Offices Held already entered for this election
    try:
        office_held_list = OfficeHeld.objects.order_by('office_held_name')
        office_held_list = office_held_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        office_held_list = []

    # Its helpful to see existing representatives when entering a new representative
    representative_list = []
    try:
        representative_list = Representative.objects.all()
        if positive_value_exists(google_civic_election_id):
            representative_list = representative_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(office_held_id):
            representative_list = representative_list.filter(office_held_id=office_held_id)
        representative_list = representative_list.order_by('representative_name')[:500]
    except Representative.DoesNotExist:
        # This is fine, create new
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'office_held_list':                  office_held_list,
        # We need to always pass in separately for the template to work
        'office_held_id':                    office_held_id,
        'google_civic_election_id':             google_civic_election_id,
        'representative_list':                representative_list,
        # Incoming variables, not saved yet
        'representative_name':                representative_name,
        'google_civic_representative_name':   google_civic_representative_name,
        'state_code':                           state_code,
        'representative_twitter_handle':      representative_twitter_handle,
        'representative_url':                 representative_url,
        'political_party':                      political_party,
        'ballot_guide_official_statement':      ballot_guide_official_statement,
        'vote_smart_id':                        vote_smart_id,
        'maplight_id':                          maplight_id,
        'representative_we_vote_id':          representative_we_vote_id,
    }
    return render(request, 'representative/representative_edit.html', template_values)


@login_required
def representative_edit_view(request, representative_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    representative_name = request.GET.get('representative_name', False)
    state_code = request.GET.get('state_code', '')
    google_civic_representative_name = request.GET.get('google_civic_representative_name', False)
    representative_twitter_handle = request.GET.get('representative_twitter_handle', False)
    representative_url = request.GET.get('representative_url', False)
    political_party = request.GET.get('political_party', False)
    show_this_year = request.GET.get('show_this_year', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    representative_id = convert_to_int(representative_id)
    representative_on_stage_found = False
    representative_on_stage = Representative()
    duplicate_representative_list = []

    try:
        representative_on_stage = Representative.objects.get(id=representative_id)
        state_code = representative_on_stage.state_code
        representative_on_stage_found = True
    except Representative.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Representative.DoesNotExist:
        # This is fine, create new below
        pass

    # Find possible duplicate representatives
    try:
        at_least_one_filter = False
        duplicate_representative_query = Representative.objects.using('readonly').all()
        duplicate_representative_query = \
            duplicate_representative_query.filter(state_code=representative_on_stage.state_code)
        duplicate_representative_query = duplicate_representative_query.exclude(
            we_vote_id__iexact=representative_on_stage.we_vote_id)
        filter_list = Q(representative_name__icontains=representative_on_stage.representative_name)
        filter_list |= Q(google_civic_representative_name__iexact=representative_on_stage.representative_name)
        filter_list |= Q(google_civic_representative_name2__iexact=representative_on_stage.representative_name)
        filter_list |= Q(google_civic_representative_name3__iexact=representative_on_stage.representative_name)
        if positive_value_exists(representative_on_stage.google_civic_representative_name):
            at_least_one_filter = True
            filter_list |= Q(representative_name__iexact=representative_on_stage.google_civic_representative_name)
            filter_list |= \
                Q(google_civic_representative_name__iexact=representative_on_stage.google_civic_representative_name)
            filter_list |= \
                Q(google_civic_representative_name2__iexact=representative_on_stage.google_civic_representative_name)
            filter_list |= \
                Q(google_civic_representative_name3__iexact=representative_on_stage.google_civic_representative_name)

        if positive_value_exists(representative_on_stage.facebook_url):
            at_least_one_filter = True
            filter_list |= Q(representative_twitter_handle=representative_on_stage.facebook_url)

        if positive_value_exists(representative_on_stage.instagram_handle):
            at_least_one_filter = True
            filter_list |= Q(instagram_handle__iexact=representative_on_stage.instagram_handle)
        if positive_value_exists(representative_on_stage.representative_email):
            at_least_one_filter = True
            filter_list |= Q(representative_email=representative_on_stage.representative_email)
            filter_list |= Q(representative_email2=representative_on_stage.representative_email)
            filter_list |= Q(representative_email3=representative_on_stage.representative_email)
        if positive_value_exists(representative_on_stage.representative_email2):
            at_least_one_filter = True
            filter_list |= Q(representative_email=representative_on_stage.representative_email2)
            filter_list |= Q(representative_email2=representative_on_stage.representative_email2)
            filter_list |= Q(representative_email3=representative_on_stage.representative_email2)
        if positive_value_exists(representative_on_stage.representative_email3):
            at_least_one_filter = True
            filter_list |= Q(representative_email=representative_on_stage.representative_email3)
            filter_list |= Q(representative_email2=representative_on_stage.representative_email3)
            filter_list |= Q(representative_email3=representative_on_stage.representative_email3)
        if positive_value_exists(representative_on_stage.representative_twitter_handle):
            at_least_one_filter = True
            filter_list |= Q(representative_twitter_handle=representative_on_stage.representative_twitter_handle)
            filter_list |= Q(representative_twitter_handle2=representative_on_stage.representative_twitter_handle)
            filter_list |= Q(representative_twitter_handle3=representative_on_stage.representative_twitter_handle)
        if positive_value_exists(representative_on_stage.representative_twitter_handle2):
            at_least_one_filter = True
            filter_list |= Q(representative_twitter_handle=representative_on_stage.representative_twitter_handle2)
            filter_list |= Q(representative_twitter_handle2=representative_on_stage.representative_twitter_handle2)
            filter_list |= Q(representative_twitter_handle3=representative_on_stage.representative_twitter_handle2)
        if positive_value_exists(representative_on_stage.representative_twitter_handle3):
            at_least_one_filter = True
            filter_list |= Q(representative_twitter_handle=representative_on_stage.representative_twitter_handle3)
            filter_list |= Q(representative_twitter_handle2=representative_on_stage.representative_twitter_handle3)
            filter_list |= Q(representative_twitter_handle3=representative_on_stage.representative_twitter_handle3)
        if positive_value_exists(representative_on_stage.wikipedia_url):
            at_least_one_filter = True
            filter_list |= Q(wikipedia_url__iexact=representative_on_stage.wikipedia_url)

        if at_least_one_filter:
            duplicate_representative_query = duplicate_representative_query.filter(filter_list)

        duplicate_representative_list = duplicate_representative_query.order_by('representative_name')[:20]
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Find possible politicians to match with representative
    possible_politician_list = []
    if positive_value_exists(representative_on_stage.politician_we_vote_id):
        # Don't search for
        pass
    elif positive_value_exists(representative_on_stage.representative_name) or \
            positive_value_exists(representative_on_stage.facebook_url) or \
            positive_value_exists(representative_on_stage.google_civic_representative_name) or \
            positive_value_exists(representative_on_stage.representative_twitter_handle) or \
            positive_value_exists(representative_on_stage.representative_email):
        try:
            possible_politician_list = Politician.objects.using('readonly').all()
            possible_politician_list = possible_politician_list.filter(state_code=representative_on_stage.state_code)

            filters = []
            if positive_value_exists(representative_on_stage.representative_name):
                new_filter = (
                    Q(google_civic_candidate_name__icontains=representative_on_stage.representative_name) |
                    Q(google_civic_candidate_name2__icontains=representative_on_stage.representative_name) |
                    Q(google_civic_candidate_name3__icontains=representative_on_stage.representative_name) |
                    Q(politician_name__icontains=representative_on_stage.representative_name)
                )
                filters.append(new_filter)

            first_name = extract_first_name_from_full_name(representative_on_stage.representative_name)
            last_name = extract_last_name_from_full_name(representative_on_stage.representative_name)
            if positive_value_exists(first_name) or positive_value_exists(last_name):
                new_filter = Q(first_name__icontains=first_name) & Q(last_name__icontains=last_name)
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_email):
                new_filter = (
                    Q(politician_email__icontains=representative_on_stage.representative_email) |
                    Q(politician_email2__icontains=representative_on_stage.representative_email) |
                    Q(politician_email3__icontains=representative_on_stage.representative_email)
                )
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_email2):
                new_filter = (
                    Q(politician_email__icontains=representative_on_stage.representative_email2) |
                    Q(politician_email2__icontains=representative_on_stage.representative_email2) |
                    Q(politician_email3__icontains=representative_on_stage.representative_email2)
                )
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_email3):
                new_filter = (
                    Q(politician_email__icontains=representative_on_stage.representative_email3) |
                    Q(politician_email2__icontains=representative_on_stage.representative_email3) |
                    Q(politician_email3__icontains=representative_on_stage.representative_email3)
                )
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_twitter_handle):
                new_filter = (
                    Q(politician_twitter_handle__icontains=representative_on_stage.representative_twitter_handle) |
                    Q(politician_twitter_handle2__icontains=representative_on_stage.representative_twitter_handle) |
                    Q(politician_twitter_handle3__icontains=representative_on_stage.representative_twitter_handle) |
                    Q(politician_twitter_handle4__icontains=representative_on_stage.representative_twitter_handle) |
                    Q(politician_twitter_handle5__icontains=representative_on_stage.representative_twitter_handle)
                )
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_twitter_handle2):
                new_filter = (
                    Q(politician_twitter_handle__icontains=representative_on_stage.representative_twitter_handle2) |
                    Q(politician_twitter_handle2__icontains=representative_on_stage.representative_twitter_handle2) |
                    Q(politician_twitter_handle3__icontains=representative_on_stage.representative_twitter_handle2) |
                    Q(politician_twitter_handle4__icontains=representative_on_stage.representative_twitter_handle2) |
                    Q(politician_twitter_handle5__icontains=representative_on_stage.representative_twitter_handle2)
                )
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.representative_twitter_handle3):
                new_filter = (
                    Q(politician_twitter_handle__icontains=representative_on_stage.representative_twitter_handle3) |
                    Q(politician_twitter_handle2__icontains=representative_on_stage.representative_twitter_handle3) |
                    Q(politician_twitter_handle3__icontains=representative_on_stage.representative_twitter_handle3) |
                    Q(politician_twitter_handle4__icontains=representative_on_stage.representative_twitter_handle3) |
                    Q(politician_twitter_handle5__icontains=representative_on_stage.representative_twitter_handle3)
                )
                filters.append(new_filter)

            if positive_value_exists(representative_on_stage.facebook_url):
                new_filter = (
                    Q(facebook_url__icontains=representative_on_stage.facebook_url) |
                    Q(facebook_url2__icontains=representative_on_stage.facebook_url) |
                    Q(facebook_url3__icontains=representative_on_stage.facebook_url)
                )
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                possible_politician_list = possible_politician_list.filter(final_filters)

            possible_politician_list = possible_politician_list.order_by('politician_name')[:20]
        except ObjectDoesNotExist:
            # This is fine, create new
            pass

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'messages_on_stage':                messages_on_stage,
        'representative':                   representative_on_stage,
        'duplicate_representative_list':    duplicate_representative_list,
        # Incoming variables, not saved yet
        'representative_name':              representative_name,
        'state_code':                       state_code,
        'google_civic_representative_name': google_civic_representative_name,
        'representative_twitter_handle':    representative_twitter_handle,
        'representative_url':               representative_url,
        'political_party':                  political_party,
        'possible_politician_list':         possible_politician_list,
        'show_this_year':                   show_this_year,
        'web_app_root_url':                 web_app_root_url,
    }
    return render(request, 'representative/representative_edit.html', template_values)


@login_required
def representative_edit_process_view(request):
    """
    Process the new or edit representative forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    defaults = {}
    status = ""

    ballotpedia_representative_url = request.POST.get('ballotpedia_representative_url', False)
    if ballotpedia_representative_url is not False:
        defaults['ballotpedia_representative_url'] = ballotpedia_representative_url
    # ctcl_uuid = request.POST.get('ctcl_uuid', False)  # Not editing yet
    facebook_url = request.POST.get('facebook_url', False)
    if facebook_url is not False:
        defaults['facebook_url'] = facebook_url
    google_civic_representative_name = request.POST.get('google_civic_representative_name', False)
    if google_civic_representative_name is not False:
        defaults['google_civic_representative_name'] = google_civic_representative_name
    google_civic_representative_name2 = request.POST.get('google_civic_representative_name2', False)
    if google_civic_representative_name2 is not False:
        defaults['google_civic_representative_name2'] = google_civic_representative_name2
    google_civic_representative_name3 = request.POST.get('google_civic_representative_name3', False)
    if google_civic_representative_name3 is not False:
        defaults['google_civic_representative_name3'] = google_civic_representative_name3
    instagram_handle = request.POST.get('instagram_handle', False)
    if positive_value_exists(instagram_handle):
        instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
    if instagram_handle is not False:
        defaults['instagram_handle'] = instagram_handle
    is_battleground_years_list = IS_BATTLEGROUND_YEARS_AVAILABLE
    years_false_list = []
    years_true_list = []
    for year in is_battleground_years_list:
        is_battleground_race_key = 'is_battleground_race_' + str(year)
        incoming_is_battleground_race = positive_value_exists(request.POST.get(is_battleground_race_key, False))
        if incoming_is_battleground_race:
            years_true_list.append(year)
        else:
            years_false_list.append(year)
        defaults[is_battleground_race_key] = incoming_is_battleground_race
    years_list = list(set(years_false_list + years_true_list))
    linkedin_url = request.POST.get('linkedin_url', False)
    if linkedin_url is not False:
        defaults['linkedin_url'] = linkedin_url
    ocd_division_id = request.POST.get('ocd_division_id', False)
    if ocd_division_id is not False:
        defaults['ocd_division_id'] = ocd_division_id
    office_held_we_vote_id = request.POST.get('office_held_we_vote_id', False)
    if office_held_we_vote_id is not False:
        defaults['office_held_we_vote_id'] = office_held_we_vote_id
    political_party = request.POST.get('political_party', False)
    if political_party is not False:
        defaults['political_party'] = political_party
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    if politician_we_vote_id is not False:
        defaults['politician_we_vote_id'] = politician_we_vote_id
    profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
    if profile_image_type_currently_active is not False:
        defaults['profile_image_type_currently_active'] = profile_image_type_currently_active
    representative_email = request.POST.get('representative_email', False)
    if representative_email is not False:
        defaults['representative_email'] = representative_email
    representative_email2 = request.POST.get('representative_email2', False)
    if representative_email2 is not False:
        defaults['representative_email2'] = representative_email2
    representative_email3 = request.POST.get('representative_email3', False)
    if representative_email3 is not False:
        defaults['representative_email3'] = representative_email3
    representative_id = convert_to_int(request.POST['representative_id'])
    representative_name = request.POST.get('representative_name', False)
    if representative_name is not False:
        defaults['representative_name'] = representative_name
    representative_phone = request.POST.get('representative_phone', False)
    if representative_phone is not False:
        defaults['representative_phone'] = representative_phone
    representative_phone2 = request.POST.get('representative_phone2', False)
    if representative_phone2 is not False:
        defaults['representative_phone2'] = representative_phone2
    representative_phone3 = request.POST.get('representative_phone3', False)
    if representative_phone3 is not False:
        defaults['representative_phone3'] = representative_phone3
    representative_twitter_handle = request.POST.get('representative_twitter_handle', False)
    if positive_value_exists(representative_twitter_handle):
        representative_twitter_handle = extract_twitter_handle_from_text_string(representative_twitter_handle)
    if representative_twitter_handle is not False:
        defaults['representative_twitter_handle'] = representative_twitter_handle
    representative_twitter_handle2 = request.POST.get('representative_twitter_handle2', False)
    if positive_value_exists(representative_twitter_handle2):
        representative_twitter_handle2 = extract_twitter_handle_from_text_string(representative_twitter_handle2)
    if representative_twitter_handle2 is not False:
        defaults['representative_twitter_handle2'] = representative_twitter_handle2
    representative_twitter_handle3 = request.POST.get('representative_twitter_handle3', False)
    if positive_value_exists(representative_twitter_handle3):
        representative_twitter_handle3 = extract_twitter_handle_from_text_string(representative_twitter_handle3)
    if representative_twitter_handle3 is not False:
        defaults['representative_twitter_handle3'] = representative_twitter_handle3
    representative_url = request.POST.get('representative_url', False)
    if representative_url is not False:
        defaults['representative_url'] = representative_url
    representative_url2 = request.POST.get('representative_url2', False)
    if representative_url2 is not False:
        defaults['representative_url2'] = representative_url2
    representative_url3 = request.POST.get('representative_url3', False)
    if representative_url3 is not False:
        defaults['representative_url3'] = representative_url3
    state_code = request.POST.get('state_code', False)
    if state_code is not False:
        defaults['state_code'] = state_code
    # We don't allow editing seo_friendly_path from the edit representative form.
    # The master data for seo_friendly_path lives in Politician, and we refresh it below.
    twitter_handle_updates_failing = request.POST.get('twitter_handle_updates_failing', None)
    if twitter_handle_updates_failing is not None:
        defaults['twitter_handle_updates_failing'] = positive_value_exists(twitter_handle_updates_failing)
        twitter_handle_updates_failing = positive_value_exists(twitter_handle_updates_failing)
    twitter_handle2_updates_failing = request.POST.get('twitter_handle2_updates_failing', None)
    if twitter_handle2_updates_failing is not None:
        defaults['twitter_handle2_updates_failing'] = positive_value_exists(twitter_handle2_updates_failing)
        twitter_handle2_updates_failing = positive_value_exists(twitter_handle2_updates_failing)
    wikipedia_url = request.POST.get('wikipedia_url', False)
    if wikipedia_url is not False:
        defaults['wikipedia_url'] = wikipedia_url
    years_in_office_list = OFFICE_HELD_YEARS_AVAILABLE
    for year in years_in_office_list:
        year_in_office_key = 'year_in_office_' + str(year)
        incoming_year_in_office = request.POST.get(year_in_office_key, False)
        defaults[year_in_office_key] = positive_value_exists(incoming_year_in_office)

    # Get the latest local cache of twitter data
    if not twitter_handle_updates_failing:
        twitter_user_manager = TwitterUserManager()
        results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
            twitter_handle=representative_twitter_handle)
        if results['twitter_user_found']:
            twitter_user = results['twitter_user']
            defaults['twitter_description'] = twitter_user.twitter_description
            defaults['twitter_followers_count'] = twitter_user.twitter_followers_count
            defaults['twitter_location'] = twitter_user.twitter_location
            defaults['twitter_name'] = twitter_user.twitter_name
            defaults['twitter_profile_background_image_url_https'] = twitter_user.twitter_profile_background_image_url_https
            defaults['twitter_profile_banner_url_https'] = twitter_user.twitter_profile_banner_url_https
            defaults['twitter_profile_image_url_https'] = twitter_user.twitter_profile_image_url_https
            defaults['twitter_url'] = twitter_user.twitter_url
    # Check to see if this representative is already being used anywhere
    representative_on_stage_found = False
    representative_on_stage = None
    if positive_value_exists(representative_id):
        try:
            representative_query = Representative.objects.filter(id=representative_id)
            if len(representative_query):
                representative_on_stage = representative_query[0]
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_on_stage_found = True
        except Exception as e:
            status += "COULD_NOT_RETRIEVE_REPRESENTATIVE_FROM_ID: " + str(e) + " "

    if positive_value_exists(office_held_we_vote_id):
        office_held_manager = OfficeHeldManager()
        results = office_held_manager.retrieve_office_held(
            office_held_we_vote_id=office_held_we_vote_id,
            read_only=True,
        )
        if results['office_held_found']:
            defaults['office_held_id'] = results['office_held'].id

    if positive_value_exists(politician_we_vote_id):
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(
            politician_we_vote_id=politician_we_vote_id,
            read_only=True,
        )
        if results['politician_found']:
            defaults['politician_id'] = results['politician'].id
            defaults['profile_image_background_color'] = results['politician'].profile_image_background_color
            defaults['seo_friendly_path'] = results['politician'].seo_friendly_path
        elif results['success']:
            defaults['politician_we_vote_id'] = None

    try:
        if representative_on_stage_found:
            # Update
            representative_on_stage = attach_defaults_values_to_representative_object(representative_on_stage, defaults)

            representative_on_stage.save()
            representative_we_vote_id = representative_on_stage.we_vote_id
            messages.add_message(request, messages.INFO, 'Representative updated.')
        else:
            # Create new
            required_representative_variables = True \
                if positive_value_exists(representative_name) and \
                positive_value_exists(office_held_we_vote_id) and \
                positive_value_exists(ocd_division_id) \
                else False
            representative_on_stage_found = True
            if required_representative_variables:
                representative_on_stage = Representative(
                    ocd_division_id=ocd_division_id,
                    office_held_we_vote_id=office_held_we_vote_id,
                    representative_name=representative_name,
                )
                representative_on_stage = \
                    attach_defaults_values_to_representative_object(representative_on_stage, defaults)

                representative_on_stage.save()
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                messages.add_message(request, messages.INFO, 'New representative saved.')
            else:
                messages.add_message(request, messages.ERROR, 'Could not save -- missing required variables.')
                url_variables = "?representative_name=" + str(representative_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_representative_name=" + str(google_civic_representative_name) + \
                                "&representative_twitter_handle=" + str(representative_twitter_handle) + \
                                "&representative_url=" + str(representative_url) + \
                                "&political_party=" + str(political_party)
                if positive_value_exists(representative_id):
                    return HttpResponseRedirect(reverse('representative:representative_edit',
                                                        args=(representative_id,)) + url_variables)
                else:
                    return HttpResponseRedirect(reverse('representative:representative_new', args=()) +
                                                url_variables)
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save representative.')
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))

    if representative_on_stage_found:
        if positive_value_exists(representative_we_vote_id) and len(years_list) > 0:
            from politician.controllers import update_parallel_fields_with_years_in_related_objects
            results = update_parallel_fields_with_years_in_related_objects(
                field_key_root='is_battleground_race_',
                master_we_vote_id_updated=representative_we_vote_id,
                years_false_list=years_false_list,
                years_true_list=years_true_list,
            )
            if not results['success']:
                status += results['status']
                status += "FAILED_TO_UPDATE_PARALLEL_FIELDS_FROM_REPRESENTATIVE "
                messages.add_message(request, messages.ERROR, status)

    if representative_id:
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))
    else:
        return HttpResponseRedirect(reverse('representative:representative_new', args=()))


@login_required
def representative_politician_match_view(request):
    """
    Try to match the current representative to an existing politician entry. If a politician entry isn't found,
    create an entry.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    representative_id = request.GET.get('representative_id', 0)
    representative_id = convert_to_int(representative_id)
    representative_we_vote_id = request.GET.get('representative_we_vote_id', '')
    # google_civic_election_id is included for interface usability reasons and isn't used in the processing
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    we_vote_representative = None

    representative_manager = RepresentativeManager()
    if positive_value_exists(representative_we_vote_id):
        results = representative_manager.retrieve_representative(representative_we_vote_id=representative_we_vote_id)
        if not positive_value_exists(results['representative_found']):
            messages.add_message(request, messages.ERROR,
                                 "Representative '{representative_we_vote_id}' not found."
                                 "".format(representative_we_vote_id=representative_we_vote_id))
            return HttpResponseRedirect(reverse('representative:representative_edit_we_vote_id',
                                                args=(representative_we_vote_id,)))
        we_vote_representative = results['representative']
    elif positive_value_exists(representative_id):
        results = representative_manager.retrieve_representative_from_id(representative_id)
        if not positive_value_exists(results['representative_found']):
            messages.add_message(request, messages.ERROR,
                                 "Representative '{representative_id}' not found."
                                 "".format(representative_id=representative_id))
            return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))
        we_vote_representative = results['representative']
    else:
        messages.add_message(request, messages.ERROR, "Representative identifier was not passed in.")
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))

    # Try to find existing politician for this representative. If none found, create politician.
    results = representative_politician_match(we_vote_representative)

    display_messages = True
    if results['status'] and display_messages:
        messages.add_message(request, messages.INFO, results['status'])
    return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def representative_politician_match_this_year_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    show_this_year = request.GET.get('show_this_year', 0)
    state_code = request.GET.get('state_code', '')

    # We only want to process if a year comes in
    if not positive_value_exists(show_this_year):
        messages.add_message(request, messages.ERROR, "Year required.")
        return HttpResponseRedirect(reverse('representative:representative_list', args=()))

    queryset = Representative.objects.all()
    queryset = queryset.exclude(
        Q(politician_we_vote_id__isnull=True) |
        Q(politician_we_vote_id="")
    )
    if positive_value_exists(state_code):
        queryset = queryset.filter(state_code__iexact=state_code)
    year_field_name = 'year_in_office_' + str(show_this_year)
    queryset = queryset.filter(**{year_field_name: True})
    representative_list = list(queryset)

    if len(representative_list) == 0:
        messages.add_message(request, messages.INFO, "No representatives found for year: {show_this_year}.".format(
            show_this_year=show_this_year))
        return HttpResponseRedirect(
            reverse('representative:representative_list', args=()) +
            "?show_this_year={show_this_year}"
            "".format(show_this_year=show_this_year))

    num_representatives_reviewed = 0
    num_that_already_have_politician_we_vote_id = 0
    new_politician_created = 0
    existing_politician_found = 0
    multiple_politicians_found = 0
    other_results = 0

    message = "About to loop through all of the representatives this year to make sure we have a politician record."
    print_to_log(logger, exception_message_optional=message)

    # Loop through all the representatives from this year
    for we_vote_representative in representative_list:
        num_representatives_reviewed += 1
        if we_vote_representative.politician_we_vote_id:
            num_that_already_have_politician_we_vote_id += 1
        match_results = representative_politician_match(we_vote_representative)
        if match_results['politician_created']:
            new_politician_created += 1
        elif match_results['politician_found']:
            existing_politician_found += 1
        elif match_results['politician_list_found']:
            multiple_politicians_found += 1
        else:
            other_results += 1

    message = "Year: {show_this_year}, " \
              "{num_representatives_reviewed} representatives reviewed, " \
              "{num_that_already_have_politician_we_vote_id} Candidates that already have Politician Ids, " \
              "{new_politician_created} politicians just created, " \
              "{existing_politician_found} politicians found that already exist, " \
              "{multiple_politicians_found} times we found multiple politicians and could not link, " \
              "{other_results} other results". \
              format(show_this_year=show_this_year,
                     num_representatives_reviewed=num_representatives_reviewed,
                     num_that_already_have_politician_we_vote_id=num_that_already_have_politician_we_vote_id,
                     new_politician_created=new_politician_created,
                     existing_politician_found=existing_politician_found,
                     multiple_politicians_found=multiple_politicians_found,
                     other_results=other_results)

    print_to_log(logger, exception_message_optional=message)
    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                "?show_this_year={show_this_year}"
                                "&state_code={state_code}"
                                "".format(
                                show_this_year=show_this_year,
                                state_code=state_code))


@login_required
def representative_retrieve_photos_view(request, representative_id):  # TODO DALE Transition fully to representative
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    representative_id = convert_to_int(representative_id)
    force_retrieve = request.GET.get('force_retrieve', 0)

    representative_manager = RepresentativeManager()

    results = representative_manager.retrieve_representative_from_id(representative_id)
    if not positive_value_exists(results['representative_found']):
        messages.add_message(request, messages.ERROR,
                             "Representative '{representative_id}' not found."
                             "".format(representative_id=representative_id))
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))

    we_vote_representative = results['representative']

    display_messages = True
    # retrieve_representative_results = retrieve_representative_photos(we_vote_representative, force_retrieve)
    # if retrieve_representative_results['status'] and display_messages:
    #     messages.add_message(request, messages.INFO, retrieve_representative_results['status'])
    return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))


@login_required
def representative_delete_process_view(request):  # TODO DALE Transition fully to representative
    """
    Delete this representative
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    representative_id = convert_to_int(request.GET.get('representative_id', 0))

    # Retrieve this representative
    representative_on_stage_found = False
    representative_on_stage = Representative()
    if positive_value_exists(representative_id):
        try:
            representative_query = Representative.objects.filter(id=representative_id)
            if len(representative_query):
                representative_on_stage = representative_query[0]
                representative_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find representative -- exception.')

    if not representative_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find representative.')
        return HttpResponseRedirect(reverse('representative:representative_list', args=()))

    try:
        # Delete the representative
        representative_on_stage.delete()
        messages.add_message(request, messages.INFO, 'Representative deleted.')
        return HttpResponseRedirect(reverse('representative:representative_list', args=()))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete representative -- exception.')
        return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
def representatives_sync_out_view(request):  # representativesSyncOut
    state_code = request.GET.get('state_code', '')

    try:
        representative_list = Representative.objects.using('readonly').all()
        representative_list = representative_list.filter(state_code__iexact=state_code)
        # get the data using values_list
        representative_list_dict = representative_list.values(
            'ballotpedia_representative_url',
            'ctcl_uuid',
            'date_last_updated',
            'date_last_updated_from_politician',
            'facebook_url',
            'facebook_url_is_broken',
            'google_civic_profile_image_url_https',
            'google_civic_representative_name',
            'google_civic_representative_name2',
            'google_civic_representative_name3',
            'instagram_followers_count',
            'instagram_handle',
            'is_battleground_race_2019',
            'is_battleground_race_2020',
            'is_battleground_race_2021',
            'is_battleground_race_2022',
            'is_battleground_race_2023',
            'is_battleground_race_2024',
            'is_battleground_race_2025',
            'is_battleground_race_2026',
            'linkedin_url',
            'ocd_division_id',
            'office_held_district_name',
            'office_held_id',
            'office_held_name',
            'office_held_we_vote_id',
            'photo_url_from_google_civic',
            'political_party',
            'politician_deduplication_attempted',
            'politician_id',
            'politician_match_attempted',
            'politician_we_vote_id',
            'profile_image_type_currently_active',
            'representative_contact_form_url',
            'representative_email',
            'representative_email2',
            'representative_email3',
            'representative_phone',
            'representative_phone2',
            'representative_phone3',
            'representative_twitter_handle',
            'representative_twitter_handle2',
            'representative_twitter_handle3',
            'representative_url',
            'representative_url2',
            'representative_url3',
            'seo_friendly_path',
            'seo_friendly_path_date_last_updated',
            'state_code',
            'twitter_description',
            'twitter_handle_updates_failing',
            'twitter_handle2_updates_failing',
            'twitter_name',
            'twitter_location',
            'twitter_followers_count',
            'twitter_profile_image_url_https',
            'twitter_profile_background_image_url_https',
            'twitter_profile_banner_url_https',
            'twitter_url',
            'twitter_user_id',
            'vote_usa_politician_id',
            'we_vote_hosted_profile_facebook_image_url_large',
            'we_vote_hosted_profile_facebook_image_url_medium',
            'we_vote_hosted_profile_facebook_image_url_tiny',
            'we_vote_hosted_profile_image_url_large',
            'we_vote_hosted_profile_image_url_medium',
            'we_vote_hosted_profile_image_url_tiny',
            'we_vote_hosted_profile_twitter_image_url_large',
            'we_vote_hosted_profile_twitter_image_url_medium',
            'we_vote_hosted_profile_twitter_image_url_tiny',
            'we_vote_hosted_profile_uploaded_image_url_large',
            'we_vote_hosted_profile_uploaded_image_url_medium',
            'we_vote_hosted_profile_uploaded_image_url_tiny',
            'we_vote_hosted_profile_vote_usa_image_url_large',
            'we_vote_hosted_profile_vote_usa_image_url_medium',
            'we_vote_hosted_profile_vote_usa_image_url_tiny',
            'we_vote_id',
            'wikipedia_url',
            'year_in_office_2023',
            'year_in_office_2024',
            'year_in_office_2025',
            'year_in_office_2026',
            'youtube_url',
        )
        if representative_list_dict:
            modified_representative_list_dict = []
            for one_dict in representative_list_dict:
                date_last_updated = one_dict.get('date_last_updated', '')
                if positive_value_exists(date_last_updated):
                    one_dict['date_last_updated'] = date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
                date_last_updated_from_politician = one_dict.get('date_last_updated_from_politician', '')
                if positive_value_exists(date_last_updated_from_politician):
                    one_dict['date_last_updated_from_politician'] = \
                        date_last_updated_from_politician.strftime('%Y-%m-%d %H:%M:%S')
                seo_friendly_path_date_last_updated = one_dict.get('seo_friendly_path_date_last_updated', '')
                if positive_value_exists(seo_friendly_path_date_last_updated):
                    one_dict['seo_friendly_path_date_last_updated'] = \
                        seo_friendly_path_date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
                modified_representative_list_dict.append(one_dict)
            representative_list_json = list(modified_representative_list_dict)
            return HttpResponse(json.dumps(representative_list_json), content_type='application/json')
    except Representative.DoesNotExist:
        pass

    json_data = {
        'success': False,
        'status': 'OFFICE_HELD_SYNC_OUT_VIEW-LIST_MISSING '
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def update_representative_from_politician_view(request):
    politician_we_vote_id = request.GET.get('politician_we_vote_id', '')
    representative_id = request.GET.get('representative_id', 0)
    representative_we_vote_id = request.GET.get('representative_we_vote_id', '')
    if not positive_value_exists(representative_id) and not positive_value_exists(representative_we_vote_id):
        message = "Unable to update representative from politician. Missing representative_id and we_vote_id."
        messages.add_message(request, messages.INFO, message)
        return HttpResponseRedirect(reverse('representative:representative_list', args=()))

    if positive_value_exists(representative_we_vote_id):
        representative = Representative.objects.get(we_vote_id=representative_we_vote_id)
    else:
        representative = Representative.objects.get(id=representative_id)
    representative_id = representative.id

    queryset = Politician.objects.using('readonly').all()
    queryset = queryset.filter(we_vote_id__iexact=politician_we_vote_id)
    politician_list = list(queryset)

    if len(politician_list) > 0:
        politician = politician_list[0]
        results = update_representative_details_from_politician(representative=representative, politician=politician)
        if results['success']:
            save_changes = results['save_changes']
            representative = results['representative']
            if save_changes:
                representative.date_last_updated_from_politician = localtime(now()).date()
                representative.save()
                message = "Representative updated."
                messages.add_message(request, messages.INFO, message)
            else:
                message = "Representative not updated. No changes found."
                messages.add_message(request, messages.INFO, message)
        else:
            message = "Representative not updated. Error: " + str(results['status'])
            messages.add_message(request, messages.INFO, message)
    else:
        message = "Representative not updated. No politician found to update representative from."
        messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('representative:representative_edit', args=(representative_id,)))


@login_required
def update_representatives_from_politicians_view(request):
    status = ""
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    show_this_year = convert_to_int(request.GET.get('show_this_year', 0))
    state_code = request.GET.get('state_code', "")

    representative_list = []
    try:
        queryset = Representative.objects.all()
        if positive_value_exists(show_this_year):
            if show_this_year in OFFICE_HELD_YEARS_AVAILABLE:
                year_field_name = 'year_in_office_' + str(show_this_year)
                queryset = queryset.filter(**{year_field_name: True})
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        queryset = queryset.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id='')
        )
        # Ignore representatives who have been updated in the last 6 months: date_last_updated_from_politician
        today = datetime.now().date()
        six_months = timedelta(weeks=26)
        six_months_ago = today - six_months
        queryset = queryset.exclude(date_last_updated_from_politician__gt=six_months_ago)
        representative_list = list(queryset[:3000])
    except Exception as e:
        status += "REPRESENTATIVE_QUERY_FAILED: " + str(e) + " "

    # Retrieve all related politicians with one query
    politician_we_vote_id_list = []
    for representative in representative_list:
        if positive_value_exists(representative.politician_we_vote_id):
            if representative.politician_we_vote_id not in politician_we_vote_id_list:
                politician_we_vote_id_list.append(representative.politician_we_vote_id)

    politician_list_by_we_vote_id = {}
    if len(politician_we_vote_id_list) > 0:
        queryset = Politician.objects.all()
        queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        for one_politician in politician_list:
            politician_list_by_we_vote_id[one_politician.we_vote_id] = one_politician

    # Loop through all the representatives in this year, and update them with some politician data
    representatives_updated = 0
    representatives_without_changes = 0
    for we_vote_representative in representative_list:
        if we_vote_representative.politician_we_vote_id in politician_list_by_we_vote_id:
            politician = politician_list_by_we_vote_id[we_vote_representative.politician_we_vote_id]
        else:
            politician = None
            we_vote_representative.date_last_updated_from_politician = localtime(now()).date()
            we_vote_representative.save()
        if not politician or not hasattr(politician, 'we_vote_id'):
            continue
        results = update_representative_details_from_politician(
            representative=we_vote_representative,
            politician=politician)
        if results['success']:
            save_changes = results['save_changes']
            we_vote_representative = results['representative']
            we_vote_representative.date_last_updated_from_politician = localtime(now()).date()
            we_vote_representative.save()
            if save_changes:
                representatives_updated += 1
            else:
                representatives_without_changes += 1

    message = \
        "Representatives updated: {representatives_updated:,}. " \
        "Representatives without changes: {representatives_without_changes:,}. " \
        "".format(
            representatives_updated=representatives_updated,
            representatives_without_changes=representatives_without_changes)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('representative:representative_list', args=()) +
                                "?show_this_year={show_this_year}"
                                "&state_code={state_code}"
                                "".format(
                                    show_this_year=show_this_year,
                                    state_code=state_code))


@login_required
def update_ocd_id_state_mismatch_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    queryset = Representative.objects.all()
    queryset = queryset.exclude(ocd_id_state_mismatch_checked=True)
    representative_list = list(queryset[:10000])

    bulk_update_list = []
    politician_we_vote_id_with_mismatch_list = []
    representatives_updated = 0
    representatives_without_mismatches = 0
    for representative in representative_list:
        representative.ocd_id_state_mismatch_checked = True
        state_code_lower_case = representative.state_code.lower() \
            if positive_value_exists(representative.state_code) else ''
        mismatch_found = (
                positive_value_exists(state_code_lower_case) and
                positive_value_exists(representative.ocd_division_id) and
                state_code_lower_case != extract_state_from_ocd_division_id(representative.ocd_division_id))
        mismatch_update_needed_on_politician = False
        if mismatch_found:
            if not representative.ocd_id_state_mismatch_found:
                representative.ocd_id_state_mismatch_found = True
                representatives_updated += 1
                # Only update the Politician table if there is a positive mismatch found,
                #  and we have not previously found a mismatch
                mismatch_update_needed_on_politician = True
            else:
                representatives_without_mismatches += 1
        else:
            if representative.ocd_id_state_mismatch_found:
                representative.ocd_id_state_mismatch_found = False
                representatives_updated += 1
            else:
                representatives_without_mismatches += 1
        if mismatch_update_needed_on_politician:
            # We don't want to unset 'ocd_id_state_mismatch_found' in the Politician table here,
            #  since there may be repairs we need to complete on the Politician data.
            if positive_value_exists(representative.politician_we_vote_id):
                if representative.politician_we_vote_id not in politician_we_vote_id_with_mismatch_list:
                    politician_we_vote_id_with_mismatch_list.append(representative.politician_we_vote_id)
        bulk_update_list.append(representative)
    try:
        Representative.objects.bulk_update(bulk_update_list, [
            'ocd_id_state_mismatch_checked',
            'ocd_id_state_mismatch_found',
        ])
        message = \
            "Representatives updated: {representatives_updated:,}. " \
            "Representatives without mismatches: {representatives_without_mismatches:,}. " \
            "".format(
                representatives_updated=representatives_updated,
                representatives_without_mismatches=representatives_without_mismatches)
        messages.add_message(request, messages.INFO, message)
    except Exception as e:
        messages.add_message(request, messages.ERROR,
                             "ERROR with update_ocd_id_state_mismatch_view: {e} "
                             "".format(e=e))

    return HttpResponseRedirect(reverse('representative:representative_list', args=()))


@login_required
def update_ocd_id_state_mismatch_related_tables_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    queryset = Representative.objects.all()
    queryset = queryset.filter(ocd_id_state_mismatch_found=True)
    representative_list = list(queryset[:10000])

    office_held_we_vote_id_with_mismatch_list = []
    politician_we_vote_id_with_mismatch_list = []
    for representative in representative_list:
        if positive_value_exists(representative.office_held_we_vote_id) and \
                representative.office_held_we_vote_id not in office_held_we_vote_id_with_mismatch_list:
            office_held_we_vote_id_with_mismatch_list.append(representative.office_held_we_vote_id)
        if positive_value_exists(representative.politician_we_vote_id) and \
                representative.politician_we_vote_id not in politician_we_vote_id_with_mismatch_list:
            politician_we_vote_id_with_mismatch_list.append(representative.politician_we_vote_id)

    # Now transfer ocd_id_state_mismatch_found to all linked OfficeHeld records
    #  using office_held_we_vote_id_with_mismatch_list.
    queryset = OfficeHeld.objects.all()
    queryset = queryset.filter(we_vote_id__in=office_held_we_vote_id_with_mismatch_list)
    queryset = queryset.exclude(ocd_id_state_mismatch_found=True)
    office_held_list = list(queryset[:1000])
    bulk_update_list = []
    for office_held in office_held_list:
        office_held.ocd_id_state_mismatch_found = True
        bulk_update_list.append(office_held)
    OfficeHeld.objects.bulk_update(bulk_update_list, ['ocd_id_state_mismatch_found'])
    message = "Office Held entries marked with ocd_id_state_mismatch_found: {office_held_list_updated:,}.".format(
        office_held_list_updated=len(office_held_list)
    )
    messages.add_message(request, messages.INFO, message)

    # Now transfer ocd_id_state_mismatch_found to all linked Politician records
    #  using politician_we_vote_id_with_mismatch_list. We have to do it here, because the ocd_division_id
    #  data does not exist in the Politician table.
    queryset = Politician.objects.all()
    queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_with_mismatch_list)
    queryset = queryset.exclude(ocd_id_state_mismatch_found=True)
    politician_list = list(queryset[:1000])
    bulk_update_list = []
    for politician in politician_list:
        politician.ocd_id_state_mismatch_found = True
        bulk_update_list.append(politician)
    Politician.objects.bulk_update(bulk_update_list, ['ocd_id_state_mismatch_found'])
    message = "Politicians marked with ocd_id_state_mismatch_found: {politicians_updated:,}.".format(
        politicians_updated=len(politician_list)
    )
    messages.add_message(request, messages.INFO, message)

    # Now transfer ocd_id_state_mismatch_found to all linked CampaignX records
    #  using politician_we_vote_id_with_mismatch_list.
    from campaign.models import CampaignX
    queryset = CampaignX.objects.all()
    queryset = queryset.filter(linked_politician_we_vote_id__in=politician_we_vote_id_with_mismatch_list)
    queryset = queryset.exclude(ocd_id_state_mismatch_found=True)
    campaignx_list = list(queryset[:1000])
    bulk_update_list = []
    for campaignx in campaignx_list:
        campaignx.ocd_id_state_mismatch_found = True
        bulk_update_list.append(campaignx)
    CampaignX.objects.bulk_update(bulk_update_list, ['ocd_id_state_mismatch_found'])
    message = "CampaignX marked with ocd_id_state_mismatch_found: {campaignx_updated:,}.".format(
        campaignx_updated=len(campaignx_list)
    )
    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('representative:representative_list', args=()))