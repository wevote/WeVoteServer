# representative/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import fetch_duplicate_representative_count, figure_out_representative_conflict_values, \
    find_duplicate_representative, merge_if_duplicate_representatives, merge_these_two_representatives, \
    representative_politician_match, update_representative_from_politician
from .models import attach_defaults_values_to_representative_object, Representative, RepresentativeManager, \
    REPRESENTATIVE_UNIQUE_IDENTIFIERS
from exception.models import handle_record_not_found_exception, handle_record_found_more_than_one_exception, \
    print_to_log, handle_record_not_saved_exception
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import datetime, timedelta
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.timezone import localtime, now
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from django.db.models import Q
from office_held.models import OfficeHeld, OfficeHeldManager
from election.models import Election
from politician.models import Politician, PoliticianManager
from twitter.models import TwitterUserManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP, \
    extract_instagram_handle_from_text_string, extract_twitter_handle_from_text_string, \
    convert_to_political_party_constant
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE, OFFICE_HELD_YEARS_AVAILABLE

OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

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

    ignore_representative_we_vote_id_list = []
    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', "")
    representative_manager = RepresentativeManager()

    representative_list = []
    try:
        representative_query = Representative.objects.all()
        representative_query = representative_query.filter(state_code__iexact=state_code)
        if positive_value_exists(ignore_representative_we_vote_id_list):
            representative_query = representative_query.exclude(we_vote_id__in=ignore_representative_we_vote_id_list)
        representative_list = list(representative_query)
    except Exception as e:
        status += "REPRESENTATIVE_QUERY_FAILED: " + str(e) + " "

    # Loop through all the representatives in this election to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
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
def representative_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    representative_search = request.GET.get('representative_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = request.GET.get('show_all', False)
    representative_count = 0
    representative_list = []
    show_this_year = convert_to_int(request.GET.get('show_this_year', 0))

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        queryset = Representative.objects.all()
        if positive_value_exists(state_code):
            if state_code.lower() == 'na':
                queryset = queryset.filter(
                    Q(state_code__isnull=True) |
                    Q(state_code='')
                )
            else:
                queryset = queryset.filter(state_code__iexact=state_code)

        if positive_value_exists(show_this_year):
            if show_this_year in OFFICE_HELD_YEARS_AVAILABLE:
                year_field_name = 'year_in_office_' + str(show_this_year)
                queryset = queryset.filter(**{year_field_name: True})

        if positive_value_exists(representative_search):
            search_words = representative_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(representative_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(representative_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(political_party__icontains=one_word)
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
        if not positive_value_exists(show_all):
            representative_list = list(queryset.order_by('representative_name')[:100])
        elif positive_value_exists(representative_search):
            representative_list = list(queryset)
        else:
            representative_list = list(queryset[:500])
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
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'election_list':            election_list,
        'representative_list':      representative_list,
        'representative_search':    representative_search,
        'show_this_year':           show_this_year,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
        'years_available':          OFFICE_HELD_YEARS_AVAILABLE,
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
    vote_smart_id = request.GET.get('vote_smart_id', False)
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
        duplicate_representative_query = Representative.objects.all()
        duplicate_representative_query = duplicate_representative_query.exclude(
            we_vote_id__iexact=representative_on_stage.we_vote_id)

        filter_list = Q(representative_name__icontains=representative_on_stage.representative_name)

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
            we_vote_id=politician_we_vote_id,
            read_only=True,
        )
        if results['politician_found']:
            defaults['politician_id'] = results['politician'].id
        elif results['success']:
            defaults['politician_we_vote_id'] = None

    try:
        if representative_on_stage_found:
            # Update
            representative_on_stage = attach_defaults_values_to_representative_object(representative_on_stage, defaults)

            representative_on_stage.save()
            messages.add_message(request, messages.INFO, 'Representative updated.')
        else:
            # Create new
            required_representative_variables = True \
                if positive_value_exists(representative_name) and \
                positive_value_exists(office_held_we_vote_id) and \
                positive_value_exists(ocd_division_id) \
                else False
            if required_representative_variables:
                representative_on_stage = Representative(
                    ocd_division_id=ocd_division_id,
                    office_held_we_vote_id=office_held_we_vote_id,
                    representative_name=representative_name,
                )
                representative_on_stage = attach_defaults_values_to_representative_object(representative_on_stage, defaults)

                representative_on_stage.save()
                representative_id = representative_on_stage.id
                messages.add_message(request, messages.INFO, 'New representative saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
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
    retrieve_representative_results = retrieve_representative_photos(we_vote_representative, force_retrieve)

    if retrieve_representative_results['status'] and display_messages:
        messages.add_message(request, messages.INFO, retrieve_representative_results['status'])
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
        results = update_representative_from_politician(representative=representative, politician=politician)
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
        representative_list = list(queryset[:1000])
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
            we_vote_representative.date_last_updated_from_politician = datetime.now()
            we_vote_representative.save()
        if not politician or not hasattr(politician, 'we_vote_id'):
            continue
        results = update_representative_from_politician(representative=we_vote_representative, politician=politician)
        if results['success']:
            save_changes = results['save_changes']
            we_vote_representative = results['representative']
            we_vote_representative.date_last_updated_from_politician = datetime.now()
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
