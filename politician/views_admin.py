# politician/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import string
from datetime import datetime
import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from candidate.controllers import retrieve_candidate_photos
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager
from config.base import get_environment_variable
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception, \
    handle_record_not_found_exception, handle_record_not_saved_exception, print_to_log
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from office.models import ContestOffice
from position.models import PositionEntered, PositionListManager
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, convert_to_political_party_constant, \
    extract_first_name_from_full_name, \
    extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_twitter_handle_from_text_string, \
    positive_value_exists, STATE_CODE_MAP, display_full_name_with_correct_capitalization
from .controllers import fetch_duplicate_politician_count, figure_out_politician_conflict_values, \
    find_duplicate_politician, \
    merge_if_duplicate_politicians, merge_these_two_politicians, politicians_import_from_master_server
from .models import Politician, PoliticianManager, POLITICIAN_UNIQUE_IDENTIFIERS

POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def compare_two_politicians_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician1_we_vote_id = request.GET.get('politician1_we_vote_id', 0)
    politician2_we_vote_id = request.GET.get('politician2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    politician_manager = PoliticianManager()
    politician_results = politician_manager.retrieve_politician(we_vote_id=politician1_we_vote_id)
    if not politician_results['politician_found']:
        messages.add_message(request, messages.ERROR, "Politician1 not found.")
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    politician_option1_for_template = politician_results['politician']

    politician_results = politician_manager.retrieve_politician(we_vote_id=politician2_we_vote_id)
    if not politician_results['politician_found']:
        messages.add_message(request, messages.ERROR, "Politician2 not found.")
        return HttpResponseRedirect(reverse('politician:politician_summary', args=(politician_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    politician_option2_for_template = politician_results['politician']

    politician_merge_conflict_values = figure_out_politician_conflict_values(
        politician_option1_for_template, politician_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_politician_merge_form(
        request,
        politician_option1_for_template,
        politician_option2_for_template,
        politician_merge_conflict_values,
        remove_duplicate_process)


@login_required
def find_and_merge_duplicate_politicians_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    state_code = request.GET.get('state_code', "")
    politician_manager = PoliticianManager()

    results = politician_manager.retrieve_politicians(
        limit_to_this_state_code=state_code,
        read_only=False)
    politician_list = results['politician_list']

    # Loop through all of the politicians to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
        ignore_politician_id_list = []
        duplicate_politician_count = 0
        for we_vote_politician in politician_list:
            # Note that we don't reset the ignore_politician_list, so we don't search for a duplicate both directions
            ignore_politician_id_list.append(we_vote_politician.we_vote_id)
            duplicate_politician_count_temp = fetch_duplicate_politician_count(
                we_vote_politician, ignore_politician_id_list)
            duplicate_politician_count += duplicate_politician_count_temp

        if positive_value_exists(duplicate_politician_count):
            messages.add_message(request, messages.INFO,
                                 "There are approximately {duplicate_politician_count} "
                                 "possible duplicates."
                                 "".format(duplicate_politician_count=duplicate_politician_count))

    # Loop through all of the politicians in this election
    for we_vote_politician in politician_list:
        ignore_politician_id_list = []
        # Add current politician entry to the ignore list
        ignore_politician_id_list.append(we_vote_politician.we_vote_id)
        # Now check to for other politicians we have labeled as "not a duplicate"
        not_a_duplicate_list = politician_manager.fetch_politicians_are_not_duplicates_list_we_vote_ids(
            we_vote_politician.we_vote_id)

        ignore_politician_id_list += not_a_duplicate_list

        results = find_duplicate_politician(we_vote_politician, ignore_politician_id_list)

        # If we find politicians to merge, stop and ask for confirmation
        if results['politician_merge_possibility_found']:
            politician_option1_for_template = we_vote_politician
            politician_option2_for_template = results['politician_merge_possibility']

            # Can we automatically merge these politicians?
            merge_results = merge_if_duplicate_politicians(
                politician_option1_for_template,
                politician_option2_for_template,
                results['politician_merge_conflict_values'])

            if merge_results['politicians_merged']:
                politician = merge_results['politician']
                messages.add_message(request, messages.INFO, "Politician {politician_name} automatically merged."
                                                             "".format(politician_name=politician.politician_name))
                return HttpResponseRedirect(reverse('politician:find_and_merge_duplicate_politicians', args=()) +
                                            "?state_code=" + str(state_code))
            else:
                # This view function takes us to displaying a template
                remove_duplicate_process = True  # Try to find another politician to merge after finishing
                return render_politician_merge_form(
                    request,
                    politician_option1_for_template,
                    politician_option2_for_template,
                    results['politician_merge_conflict_values'],
                    remove_duplicate_process)

    message = "No duplicate politicians found. State: {state_code}" \
              "".format(state_code=state_code)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                "?state_code={state_code}"
                                "".format(
                                    state_code=state_code))


def render_politician_merge_form(
        request, politician_option1_for_template,
        politician_option2_for_template,
        politician_merge_conflict_values,
        remove_duplicate_process=True):
    candidate_list_manager = CandidateListManager()

    state_code = ''
    if hasattr(politician_option1_for_template, 'state_code'):
        state_code = politician_option1_for_template.state_code
    if hasattr(politician_option2_for_template, 'state_code'):
        state_code = politician_option2_for_template.state_code

    # Get info about candidates linked to each politician
    politician1_linked_candidates_count = 0
    politician1_linked_candidate_district_names = ''
    politician1_linked_candidate_names = ''
    politician1_linked_candidate_offices = ''
    politician1_linked_candidate_photos = []
    politician1_candidate_results = candidate_list_manager.retrieve_candidates_from_politician(
        politician_id=politician_option1_for_template.id,
        politician_we_vote_id=politician_option1_for_template.we_vote_id)
    if politician1_candidate_results['candidate_list_found']:
        is_first = True
        is_first_office = True
        for one_candidate in politician1_candidate_results['candidate_list']:
            politician1_linked_candidates_count += 1
            if is_first:
                is_first = False
            else:
                politician1_linked_candidate_names += ', '
            politician1_linked_candidate_names += one_candidate.candidate_name
            if positive_value_exists(one_candidate.we_vote_hosted_profile_image_url_large):
                politician1_linked_candidate_photos.append(one_candidate.we_vote_hosted_profile_image_url_large)
            results = candidate_list_manager.retrieve_all_offices_for_candidate(
                candidate_we_vote_id=one_candidate.we_vote_id,
                read_only=True)
            if results['office_list_found']:
                for one_office in results['office_list']:
                    if is_first_office:
                        is_first_office = False
                    else:
                        politician1_linked_candidate_offices += ', '
                        politician1_linked_candidate_district_names += ', '
                    politician1_linked_candidate_offices += one_office.office_name
                    politician1_linked_candidate_district_names += str(one_office.district_name)
    politician_option1_for_template.linked_candidates_count = politician1_linked_candidates_count
    politician_option1_for_template.linked_candidate_district_names = politician1_linked_candidate_district_names
    politician_option1_for_template.linked_candidate_names = politician1_linked_candidate_names
    politician_option1_for_template.linked_candidate_offices = politician1_linked_candidate_offices
    politician_option1_for_template.linked_candidate_photos = politician1_linked_candidate_photos

    politician2_linked_candidates_count = 0
    politician2_linked_candidate_district_names = ''
    politician2_linked_candidate_names = ''
    politician2_linked_candidate_offices = ''
    politician2_linked_candidate_photos = []
    politician2_candidate_results = candidate_list_manager.retrieve_candidates_from_politician(
        politician_id=politician_option2_for_template.id,
        politician_we_vote_id=politician_option2_for_template.we_vote_id)
    if politician2_candidate_results['candidate_list_found']:
        is_first = True
        is_first_office = True
        for one_candidate in politician2_candidate_results['candidate_list']:
            politician2_linked_candidates_count += 1
            if is_first:
                is_first = False
            else:
                politician2_linked_candidate_names += ', '
            politician2_linked_candidate_names += one_candidate.candidate_name
            if positive_value_exists(one_candidate.we_vote_hosted_profile_image_url_large):
                politician2_linked_candidate_photos.append(one_candidate.we_vote_hosted_profile_image_url_large)
            results = candidate_list_manager.retrieve_all_offices_for_candidate(
                candidate_we_vote_id=one_candidate.we_vote_id,
                read_only=True)
            if results['office_list_found']:
                for one_office in results['office_list']:
                    if is_first_office:
                        is_first_office = False
                    else:
                        politician2_linked_candidate_offices += ', '
                        politician2_linked_candidate_district_names += ', '
                    politician2_linked_candidate_offices += one_office.office_name
                    politician2_linked_candidate_district_names += str(one_office.district_name)
    politician_option2_for_template.linked_candidates_count = politician2_linked_candidates_count
    politician_option2_for_template.linked_candidate_district_names = politician2_linked_candidate_district_names
    politician_option2_for_template.linked_candidate_names = politician2_linked_candidate_names
    politician_option2_for_template.linked_candidate_offices = politician2_linked_candidate_offices
    politician_option2_for_template.linked_candidate_photos = politician2_linked_candidate_photos

    messages_on_stage = get_messages(request)
    template_values = {
        'conflict_values':          politician_merge_conflict_values,
        'messages_on_stage':        messages_on_stage,
        'politician_option1':       politician_option1_for_template,
        'politician_option2':       politician_option2_for_template,
        'remove_duplicate_process': remove_duplicate_process,
        'state_code':               state_code,
    }
    return render(request, 'politician/politician_merge.html', template_values)


@login_required
def politicians_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in POLITICIANS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = politicians_import_from_master_server(request, state_code)

    if not results['success']:
        if 'POLITICIAN_LIST_MISSING' in results['status']:
            messages.add_message(request, messages.INFO,
                                 'Politician import completed, and it returned no politicians, but this is not '
                                 'necessarily a problem!  It might be that are no local politicians running for office '
                                 'in this election.')
        else:
            messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Politician import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Duplicates skipped: '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def politician_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = request.GET.get('show_all', False)

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        politician_query = Politician.objects.all()
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)

        if positive_value_exists(politician_search):
            search_words = politician_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(politician_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(political_party__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(vote_usa_politician_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    politician_query = politician_query.filter(final_filters)

        politician_list_count = politician_query.count()
        if not positive_value_exists(show_all):
            politician_query = politician_query.order_by('politician_name')[:25]
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Cycle through all Politicians and find unlinked Candidates that *might* be "children" of this politician
    temp_politician_list = []
    politician_list = list(politician_query)
    for one_politician in politician_list:
        try:
            linked_candidate_query = CandidateCampaign.objects.all()
            linked_candidate_query = linked_candidate_query.filter(
                Q(politician_we_vote_id__iexact=one_politician.we_vote_id) |
                Q(politician_id=one_politician.id))
            linked_candidate_list_count = linked_candidate_query.count()
            one_politician.linked_candidate_list_count = linked_candidate_list_count

            related_candidate_list = CandidateCampaign.objects.all()
            related_candidate_list = related_candidate_list.exclude(politician_we_vote_id=one_politician.we_vote_id)

            filters = []
            new_filter = Q(candidate_name__icontains=one_politician.first_name) & \
                Q(candidate_name__icontains=one_politician.last_name)
            filters.append(new_filter)

            if positive_value_exists(one_politician.politician_twitter_handle):
                new_filter = Q(candidate_twitter_handle__iexact=one_politician.politician_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(one_politician.vote_smart_id):
                new_filter = Q(vote_smart_id=one_politician.vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                related_candidate_list = related_candidate_list.filter(final_filters)

            related_candidate_list_count = related_candidate_list.count()
        except Exception as e:
            related_candidate_list_count = 0

        one_politician.related_candidate_list_count = related_candidate_list_count
        temp_politician_list.append(one_politician)

    politician_list = temp_politician_list

    election_list = Election.objects.order_by('-election_day_text')

    messages.add_message(request, messages.INFO, "Politician Count: " + str(politician_list_count))

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'politician_list':          politician_list,
        'politician_search':        politician_search,
        'election_list':            election_list,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
    }
    return render(request, 'politician/politician_list.html', template_values)


@login_required
def politician_merge_process_view(request):
    """
    Process the merging of two politicians
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician_manager = PoliticianManager()

    merge = request.POST.get('merge', False)
    skip = request.POST.get('skip', False)

    # Politician 1 is the one we keep, and Politician 2 is the one we will merge into Politician 1
    politician1_we_vote_id = request.POST.get('politician1_we_vote_id', 0)
    politician2_we_vote_id = request.POST.get('politician2_we_vote_id', 0)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    redirect_to_politician_list = request.POST.get('redirect_to_politician_list', False)
    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    state_code = request.POST.get('state_code', '')

    if positive_value_exists(skip):
        results = politician_manager.update_or_create_politicians_are_not_duplicates(
            politician1_we_vote_id, politician2_we_vote_id)
        if not results['new_politicians_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save politicians_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior politicians skipped, and not merged.')
        return HttpResponseRedirect(reverse('politician:find_and_merge_duplicate_politicians', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    politician1_results = politician_manager.retrieve_politician(we_vote_id=politician1_we_vote_id)
    if politician1_results['politician_found']:
        politician1_on_stage = politician1_results['politician']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve politician 1.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    politician2_results = politician_manager.retrieve_politician_from_we_vote_id(politician2_we_vote_id)
    if politician2_results['politician_found']:
        politician2_on_stage = politician2_results['politician']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve politician 2.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_values = figure_out_politician_conflict_values(politician1_on_stage, politician2_on_stage)
    admin_merge_choices = {}
    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            choice = request.POST.get(attribute + '_choice', '')
            if politician2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(politician2_on_stage, attribute)
        elif conflict_value == "CANDIDATE2":
            admin_merge_choices[attribute] = getattr(politician2_on_stage, attribute)

    merge_results = merge_these_two_politicians(politician1_we_vote_id, politician2_we_vote_id, admin_merge_choices)

    if positive_value_exists(merge_results['politicians_merged']):
        politician = merge_results['politician']
        messages.add_message(request, messages.INFO, "Politician '{politician_name}' merged."
                                                     "".format(politician_name=politician.politician_name))
    else:
        # NOTE: We could also redirect to a page to look specifically at these two politicians, but this should
        # also get you back to looking at the two politicians
        messages.add_message(request, messages.ERROR, merge_results['status'])
        return HttpResponseRedirect(reverse('politician:find_and_merge_duplicate_politicians', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&auto_merge_off=1" +
                                    "&state_code=" + str(state_code))

    if redirect_to_politician_list:
        return HttpResponseRedirect(reverse('politician:politician_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('politician:find_and_merge_duplicate_politicians', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician1_on_stage.id,)))


@login_required
def politician_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    contest_office_id = request.GET.get('contest_office_id', 0)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    politician_name = request.GET.get('politician_name', "")
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', "")
    google_civic_candidate_name2 = request.GET.get('google_civic_candidate_name2', "")
    google_civic_candidate_name3 = request.GET.get('google_civic_candidate_name3', "")
    state_code = request.GET.get('state_code', "")
    politician_twitter_handle = request.GET.get('politician_twitter_handle', "")
    politician_url = request.GET.get('politician_url', "")
    political_party = request.GET.get('political_party', "")
    ballot_guide_official_statement = request.GET.get('ballot_guide_official_statement', "")
    vote_smart_id = request.GET.get('vote_smart_id', "")
    maplight_id = request.GET.get('maplight_id', "")
    politician_we_vote_id = request.GET.get('politician_we_vote_id', "")

    # These are the Offices already entered for this election
    try:
        contest_office_list = ContestOffice.objects.order_by('office_name')
        contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        contest_office_list = []

    # Its helpful to see existing politicians when entering a new politician
    politician_list = []
    try:
        politician_list = Politician.objects.all()
        if positive_value_exists(google_civic_election_id):
            politician_list = politician_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(contest_office_id):
            politician_list = politician_list.filter(contest_office_id=contest_office_id)
        politician_list = politician_list.order_by('politician_name')[:500]
    except Politician.DoesNotExist:
        # This is fine, create new
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_list':              contest_office_list,
        'contest_office_id':        contest_office_id,  # We need to always pass in separately for the template to work
        'google_civic_election_id': google_civic_election_id,
        'politician_list':           politician_list,
        # Incoming variables, not saved yet
        'politician_name':                   politician_name,
        'google_civic_candidate_name':      google_civic_candidate_name,
        'google_civic_candidate_name2':      google_civic_candidate_name2,
        'google_civic_candidate_name3':      google_civic_candidate_name3,
        'state_code':                       state_code,
        'politician_twitter_handle':         politician_twitter_handle,
        'politician_url':                    politician_url,
        'political_party':                            political_party,
        'ballot_guide_official_statement':  ballot_guide_official_statement,
        'vote_smart_id':                    vote_smart_id,
        'maplight_id':                      maplight_id,
        'politician_we_vote_id':            politician_we_vote_id,
    }
    return render(request, 'politician/politician_edit.html', template_values)


@login_required
def politician_edit_by_we_vote_id_view(request, politician_we_vote_id):
    politician_manager = PoliticianManager()
    politician_id = politician_manager.fetch_politician_id_from_we_vote_id(politician_we_vote_id)
    return politician_we_vote_id(request, politician_id)


@login_required
def politician_edit_view(request, politician_id=0, politician_we_vote_id=''):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # These variables are here because there was an error on the edit_process_view and the voter needs to try again
    politician_name = request.GET.get('politician_name', False)
    state_code = request.GET.get('state_code', False)
    google_civic_candidate_name = request.GET.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.GET.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.GET.get('google_civic_candidate_name3', False)
    politician_twitter_handle = request.GET.get('politician_twitter_handle', False)
    politician_url = request.GET.get('politician_url', False)
    political_party = request.GET.get('political_party', False)
    vote_smart_id = request.GET.get('vote_smart_id', False)
    maplight_id = request.GET.get('maplight_id', False)

    messages_on_stage = get_messages(request)
    politician_id = convert_to_int(politician_id)
    politician_on_stage_found = False
    politician_on_stage = Politician()
    duplicate_politician_list = []

    try:
        if positive_value_exists(politician_id):
            politician_on_stage = Politician.objects.get(id=politician_id)
        else:
            politician_on_stage = Politician.objects.get(we_vote_id=politician_we_vote_id)
        politician_on_stage_found = True
    except Politician.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Politician.DoesNotExist:
        # This is fine, create new below
        pass

    if politician_on_stage_found:
        # Working with Vote Smart data
        try:
            vote_smart_politician_id = politician_on_stage.vote_smart_id
            rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
            rating_list = rating_list_query.filter(candidateId=vote_smart_politician_id)
        except VotesmartApiError as error_instance:
            # Catch the error message coming back from Vote Smart and pass it in the status
            error_message = error_instance.args
            status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
            print_to_log(logger=logger, exception_message_optional=status)
            rating_list = []

        # Working with We Vote Positions
        try:
            politician_position_query = PositionEntered.objects.order_by('stance')
            # As of Aug 2018 we are no longer using PERCENT_RATING
            politician_position_query = politician_position_query.exclude(stance__iexact='PERCENT_RATING')
            politician_position_list = politician_position_query.filter(
                politician_we_vote_id__iexact=politician_on_stage.we_vote_id)
        except Exception as e:
            politician_position_list = []

        # Working with Candidate "children" of this politician
        try:
            linked_candidate_list = CandidateCampaign.objects.all()
            linked_candidate_list = linked_candidate_list.filter(
                Q(politician_we_vote_id__iexact=politician_on_stage.we_vote_id) |
                Q(politician_id=politician_on_stage.id))
        except Exception as e:
            linked_candidate_list = []

        # Finding Candidates that *might* be "children" of this politician
        try:
            related_candidate_list = CandidateCampaign.objects.all()
            related_candidate_list = related_candidate_list.exclude(
                Q(politician_we_vote_id__iexact=politician_on_stage.we_vote_id) |
                Q(politician_id=politician_on_stage.id))

            filters = []
            new_filter = Q(candidate_name__icontains=politician_on_stage.first_name) & \
                Q(candidate_name__icontains=politician_on_stage.last_name)
            filters.append(new_filter)

            if positive_value_exists(politician_on_stage.politician_twitter_handle):
                new_filter = Q(candidate_twitter_handle__iexact=politician_on_stage.politician_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.vote_smart_id):
                new_filter = Q(vote_smart_id=politician_on_stage.vote_smart_id)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.vote_usa_politician_id):
                new_filter = Q(vote_usa_politician_id=politician_on_stage.vote_usa_politician_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                related_candidate_list = related_candidate_list.filter(final_filters)

            related_candidate_list = related_candidate_list.order_by('candidate_name')[:20]
        except Exception as e:
            related_candidate_list = []

        # Find possible duplicate politicians
        try:
            duplicate_politician_list = Politician.objects.all()
            duplicate_politician_list = duplicate_politician_list.exclude(
                we_vote_id__iexact=politician_on_stage.we_vote_id)

            filters = []
            new_filter = Q(politician_name__icontains=politician_on_stage.politician_name)
            filters.append(new_filter)

            if positive_value_exists(politician_on_stage.first_name) or \
                    positive_value_exists(politician_on_stage.last_name):
                new_filter = Q(first_name__icontains=politician_on_stage.first_name) & \
                    Q(last_name__icontains=politician_on_stage.last_name)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.politician_twitter_handle):
                new_filter = Q(politician_twitter_handle__icontains=politician_on_stage.politician_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(politician_on_stage.vote_smart_id):
                new_filter = Q(vote_smart_id=politician_on_stage.vote_smart_id)
                filters.append(new_filter)

            politician_on_stage.politician_name_normalized = ''
            if positive_value_exists(politician_on_stage.politician_name):
                raw = politician_on_stage.politician_name
                cnt = sum(1 for c in raw if c.isupper())
                if cnt > 5:
                    humanized = display_full_name_with_correct_capitalization(raw)
                    humanized_cleaned = humanized.replace('(', '').replace(')', '')
                    politician_on_stage.politician_name_normalized = string.capwords(humanized_cleaned)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                duplicate_politician_list = duplicate_politician_list.filter(final_filters)

            duplicate_politician_list = duplicate_politician_list.order_by('politician_name')[:20]
        except ObjectDoesNotExist:
            # This is fine, create new
            pass

        template_values = {
            'messages_on_stage':            messages_on_stage,
            'politician':                   politician_on_stage,
            'rating_list':                  rating_list,
            'politician_position_list':     politician_position_list,
            'linked_candidate_list':        linked_candidate_list,
            'related_candidate_list':       related_candidate_list,
            'duplicate_politician_list':    duplicate_politician_list,
            # Incoming variables, not saved yet
            'politician_name':              politician_name,
            'state_code':                   state_code,
            'google_civic_candidate_name':  google_civic_candidate_name,
            'google_civic_candidate_name2':  google_civic_candidate_name2,
            'google_civic_candidate_name3':  google_civic_candidate_name3,
            'politician_twitter_handle':    politician_twitter_handle,
            'politician_url':               politician_url,
            'political_party':              political_party,
            'vote_smart_id':                vote_smart_id,
            'maplight_id':                  maplight_id,
        }
    else:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            # Incoming variables
            'vote_smart_id':        vote_smart_id,
        }
    return render(request, 'politician/politician_edit.html', template_values)


def politician_change_names(changes):
    count = 0
    for change in changes:
        try:
            politician_query = Politician.objects.filter(we_vote_id=change['we_vote_id'])
            politician_query = politician_query
            politician_list = list(politician_query)
            politician = politician_list[0]
            setattr(politician, 'politician_name', change['name_after'])
            timezone = pytz.timezone("America/Los_Angeles")
            datetime_now = timezone.localize(datetime.now())
            setattr(politician, 'date_last_changed', datetime_now)
            politician.save()
            count += 1
        except Exception as err:
            logger.error('politician_change_names caught: ', err)
            count = -1

    return count


@login_required
def politician_edit_process_view(request):
    """
    Process the new or edit politician forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    first_name = request.POST.get('first_name', False)
    middle_name = request.POST.get('middle_name', False)
    last_name = request.POST.get('last_name', False)
    politician_id = convert_to_int(request.POST['politician_id'])
    politician_name = request.POST.get('politician_name', False)
    google_civic_candidate_name = request.POST.get('google_civic_candidate_name', False)
    google_civic_candidate_name2 = request.POST.get('google_civic_candidate_name2', False)
    google_civic_candidate_name3 = request.POST.get('google_civic_candidate_name3', False)
    politician_twitter_handle = request.POST.get('politician_twitter_handle', False)
    if positive_value_exists(politician_twitter_handle):
        politician_twitter_handle = extract_twitter_handle_from_text_string(politician_twitter_handle)
    politician_url = request.POST.get('politician_url', False)
    political_party = request.POST.get('political_party', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    maplight_id = request.POST.get('maplight_id', False)
    state_code = request.POST.get('state_code', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    vote_usa_politician_id = request.POST.get('vote_usa_politician_id', False)

    # Check to see if this politician is already being used anywhere
    politician_on_stage_found = False
    politician_on_stage = Politician()
    if positive_value_exists(politician_id):
        try:
            politician_query = Politician.objects.filter(id=politician_id)
            if len(politician_query):
                politician_on_stage = politician_query[0]
                politician_we_vote_id = politician_on_stage.we_vote_id
                politician_on_stage_found = True
        except Exception as e:
            pass

    # Check to see if there is a duplicate politician already saved
    existing_politician_found = False
    if not positive_value_exists(politician_id):
        try:
            filter_list = Q()

            at_least_one_filter = False
            if positive_value_exists(vote_smart_id):
                at_least_one_filter = True
                filter_list |= Q(vote_smart_id=vote_smart_id)
            if positive_value_exists(maplight_id):
                at_least_one_filter = True
                filter_list |= Q(maplight_id=maplight_id)
            if positive_value_exists(politician_twitter_handle):
                at_least_one_filter = True
                filter_list |= Q(politician_twitter_handle=politician_twitter_handle)

            if at_least_one_filter:
                politician_duplicates_query = Politician.objects.filter(filter_list)

                if len(politician_duplicates_query):
                    existing_politician_found = True
        except Exception as e:
            pass

    try:
        if existing_politician_found:
            messages.add_message(request, messages.ERROR, 'This politician is already saved for this election.')
            url_variables = "?politician_name=" + str(politician_name) + \
                            "&state_code=" + str(state_code) + \
                            "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                            "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                            "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                            "&politician_twitter_handle=" + str(politician_twitter_handle) + \
                            "&politician_url=" + str(politician_url) + \
                            "&political_party=" + str(political_party) + \
                            "&vote_smart_id=" + str(vote_smart_id) + \
                            "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                            "&maplight_id=" + str(maplight_id)
            return HttpResponseRedirect(reverse('politician:politician_new', args=()) + url_variables)
        elif politician_on_stage_found:
            # Update
            if politician_name is not False:
                politician_on_stage.politician_name = politician_name
            if first_name is not False:
                politician_on_stage.first_name = first_name
            if middle_name is not False:
                politician_on_stage.middle_name = middle_name
            if last_name is not False:
                politician_on_stage.last_name = last_name
            if state_code is not False:
                politician_on_stage.state_code = state_code
            if google_civic_candidate_name is not False:
                politician_on_stage.google_civic_candidate_name = google_civic_candidate_name
            if google_civic_candidate_name2 is not False:
                politician_on_stage.google_civic_candidate_name2 = google_civic_candidate_name2
            if google_civic_candidate_name3 is not False:
                politician_on_stage.google_civic_candidate_name3 = google_civic_candidate_name3
            if politician_twitter_handle is not False:
                politician_on_stage.politician_twitter_handle = politician_twitter_handle
            if politician_url is not False:
                politician_on_stage.politician_url = politician_url
            if political_party is not False:
                political_party = convert_to_political_party_constant(political_party)
                politician_on_stage.political_party = political_party
            if vote_smart_id is not False:
                politician_on_stage.vote_smart_id = vote_smart_id
            if maplight_id is not False:
                politician_on_stage.maplight_id = maplight_id
            if vote_usa_politician_id is not False:
                politician_on_stage.vote_usa_politician_id = vote_usa_politician_id

            politician_on_stage.save()
            messages.add_message(request, messages.INFO, 'Politician updated.')
        else:
            # Create new

            required_politician_variables = True \
                if positive_value_exists(politician_name) \
                else False
            if required_politician_variables:
                politician_on_stage = Politician(
                    politician_name=politician_name,
                    state_code=state_code,
                )
                politician_on_stage.first_name = extract_first_name_from_full_name(politician_name)
                politician_on_stage.middle_name = extract_middle_name_from_full_name(politician_name)
                politician_on_stage.last_name = extract_last_name_from_full_name(politician_name)
                if google_civic_candidate_name is not False:
                    politician_on_stage.google_civic_candidate_name = google_civic_candidate_name
                if google_civic_candidate_name2 is not False:
                    politician_on_stage.google_civic_candidate_name2 = google_civic_candidate_name2
                if google_civic_candidate_name3 is not False:
                    politician_on_stage.google_civic_candidate_name3 = google_civic_candidate_name3
                if politician_twitter_handle is not False:
                    politician_on_stage.politician_twitter_handle = politician_twitter_handle
                if politician_url is not False:
                    politician_on_stage.politician_url = politician_url
                if political_party is not False:
                    political_party = convert_to_political_party_constant(political_party)
                    politician_on_stage.political_party = political_party
                if vote_smart_id is not False:
                    politician_on_stage.vote_smart_id = vote_smart_id
                if maplight_id is not False:
                    politician_on_stage.maplight_id = maplight_id
                if politician_we_vote_id is not False:
                    politician_on_stage.we_vote_id = politician_we_vote_id
                if vote_usa_politician_id is not False:
                    politician_on_stage.vote_usa_politician_id = vote_usa_politician_id

                politician_on_stage.save()
                politician_we_vote_id = politician_on_stage.we_vote_id
                vote_usa_politician_id = politician_on_stage.vote_usa_politician_id
                politician_id = politician_on_stage.id
                messages.add_message(request, messages.INFO, 'New politician saved.')
            else:
                # messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                url_variables = "?politician_name=" + str(politician_name) + \
                                "&state_code=" + str(state_code) + \
                                "&google_civic_candidate_name=" + str(google_civic_candidate_name) + \
                                "&google_civic_candidate_name2=" + str(google_civic_candidate_name2) + \
                                "&google_civic_candidate_name3=" + str(google_civic_candidate_name3) + \
                                "&politician_twitter_handle=" + str(politician_twitter_handle) + \
                                "&politician_url=" + str(politician_url) + \
                                "&political_party=" + str(political_party) + \
                                "&vote_smart_id=" + str(vote_smart_id) + \
                                "&politician_we_vote_id=" + str(politician_we_vote_id) + \
                                "&maplight_id=" + str(maplight_id)
                if positive_value_exists(politician_id):
                    return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)) +
                                                url_variables)
                else:
                    return HttpResponseRedirect(reverse('politician:politician_new', args=()) +
                                                url_variables)

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save politician.')
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    position_list_manager = PositionListManager()
    # ##################################
    # Unlink Candidates from this Politician
    try:
        linked_candidate_query = CandidateCampaign.objects.all()
        linked_candidate_query = linked_candidate_query.filter(
            Q(politician_we_vote_id__iexact=politician_on_stage.we_vote_id) |
            Q(politician_id=politician_on_stage.id)
        )
        linked_candidate_list = list(linked_candidate_query)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'LINKED_CANDIDATE_PROBLEM: ' + str(e))
        linked_candidate_list = []
    for candidate in linked_candidate_list:
        if positive_value_exists(candidate.id):
            variable_name = "unlink_candidate_" + str(candidate.id) + "_from_politician"
            unlink_candidate = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(unlink_candidate) and positive_value_exists(politician_we_vote_id):
                candidate.politician_we_vote_id = None
                candidate.politician_id = None
                candidate.save()
                # Now update positions
                from candidate.models import CandidateListManager
                results = position_list_manager.update_politician_we_vote_id_in_all_positions(
                    candidate_we_vote_id=candidate.we_vote_id,
                    new_politician_id=None,
                    new_politician_we_vote_id=None)

                messages.add_message(request, messages.INFO,
                                     'Candidate unlinked, number of positions changed: {number_changed}'
                                     ''.format(number_changed=results['number_changed']))
            else:
                pass

    # ##################################
    # Link Candidates to this Politician
    # Finding Candidates that *might* be "children" of this politician
    try:
        related_candidate_list = CandidateCampaign.objects.all()
        related_candidate_list = related_candidate_list.exclude(
            politician_we_vote_id__iexact=politician_on_stage.we_vote_id)

        filters = []
        new_filter = \
            Q(candidate_name__icontains=politician_on_stage.first_name) & \
            Q(candidate_name__icontains=politician_on_stage.last_name)
        filters.append(new_filter)

        if positive_value_exists(politician_on_stage.politician_twitter_handle):
            new_filter = Q(candidate_twitter_handle__iexact=politician_on_stage.politician_twitter_handle)
            filters.append(new_filter)

        if positive_value_exists(politician_on_stage.vote_smart_id):
            new_filter = Q(vote_smart_id=politician_on_stage.vote_smart_id)
            filters.append(new_filter)

        if positive_value_exists(politician_on_stage.vote_usa_politician_id):
            new_filter = Q(vote_usa_politician_id=politician_on_stage.vote_usa_politician_id)
            filters.append(new_filter)

        # Add the first query
        if len(filters):
            final_filters = filters.pop()

            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item

            related_candidate_list = related_candidate_list.filter(final_filters)

        related_candidate_list = related_candidate_list.order_by('candidate_name')[:20]
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'RELATED_CANDIDATE_PROBLEM: ' + str(e))
        related_candidate_list = []
    for candidate in related_candidate_list:
        if positive_value_exists(candidate.id):
            variable_name = "link_candidate_" + str(candidate.id) + "_to_politician"
            link_candidate = positive_value_exists(request.POST.get(variable_name, False))
            if positive_value_exists(link_candidate) and positive_value_exists(politician_we_vote_id):
                candidate.politician_we_vote_id = politician_we_vote_id
                if not positive_value_exists(candidate.vote_usa_politician_id) and \
                        positive_value_exists(vote_usa_politician_id):
                    candidate.vote_usa_politician_id = vote_usa_politician_id
                candidate.save()
                # Now update positions
                from candidate.models import CandidateListManager
                results = position_list_manager.update_politician_we_vote_id_in_all_positions(
                    candidate_we_vote_id=candidate.we_vote_id,
                    new_politician_id=politician_id,
                    new_politician_we_vote_id=politician_we_vote_id)

                messages.add_message(request, messages.INFO,
                                     'Candidate linked, number of positions changed: {number_changed}'
                                     ''.format(number_changed=results['number_changed']))
            else:
                pass

    if politician_id:
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))
    else:
        return HttpResponseRedirect(reverse('politician:politician_new', args=()))


@login_required
def politician_retrieve_photos_view(request, candidate_id):  # TODO DALE Transition fully to politician
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(candidate_id)
    force_retrieve = request.GET.get('force_retrieve', 0)

    candidate_manager = CandidateManager()

    results = candidate_manager.retrieve_candidate_from_id(candidate_id)
    if not positive_value_exists(results['candidate_found']):
        messages.add_message(request, messages.ERROR,
                             "Candidate '{candidate_id}' not found.".format(candidate_id=candidate_id))
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    we_vote_candidate = results['candidate']

    display_messages = True
    retrieve_candidate_results = retrieve_candidate_photos(we_vote_candidate, force_retrieve)

    if retrieve_candidate_results['status'] and display_messages:
        messages.add_message(request, messages.INFO, retrieve_candidate_results['status'])
    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def politician_delete_process_view(request):
    """
    Delete this politician
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician_id = convert_to_int(request.GET.get('politician_id', 0))

    # Retrieve this politician
    politician_we_vote_id = ''
    politician_on_stage_found = False
    politician_on_stage = None
    if positive_value_exists(politician_id):
        try:
            politician_query = Politician.objects.filter(id=politician_id)
            if len(politician_query):
                politician_on_stage = politician_query[0]
                politician_we_vote_id = politician_on_stage.we_vote_id
                politician_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find politician -- exception: ', str(e))

    if not politician_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find politician.')
        return HttpResponseRedirect(reverse('politician:politician_list', args=()))

    # Are there any positions attached to this politician that should be moved to another instance of this politician?
    if positive_value_exists(politician_id) or positive_value_exists(politician_we_vote_id):
        position_list_manager = PositionListManager()
        from candidate.models import CandidateListManager
        candidate_list_manager = CandidateListManager()
        # By not passing in new values, we remove politician_id and politician_we_vote_id
        results = position_list_manager.update_politician_we_vote_id_in_all_positions(
            politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id)
        results = candidate_list_manager.update_politician_we_vote_id_in_all_candidates(
            politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id)

    try:
        # Delete the politician
        politician_on_stage.delete()
        messages.add_message(request, messages.INFO, 'Politician deleted.')
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete politician -- exception: ' + str(e))
        return HttpResponseRedirect(reverse('politician:politician_edit', args=(politician_id,)))

    return HttpResponseRedirect(reverse('politician:politician_list', args=()))


# This page does not need to be protected.
def politicians_sync_out_view(request):  # politiciansSyncOut
    state_code = request.GET.get('state_code', '')
    politician_search = request.GET.get('politician_search', '')

    try:
        politician_query = Politician.objects.using('readonly').all()
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        filters = []
        if positive_value_exists(politician_search):
            new_filter = Q(politician_name__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_twitter_handle__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(politician_url__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(party__icontains=politician_search)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=politician_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                politician_query = politician_query.filter(final_filters)

        politician_query = politician_query.values(
            'we_vote_id',
            'first_name',
            'middle_name',
            'last_name',
            'politician_name',
            'google_civic_candidate_name',
            'google_civic_candidate_name2',
            'google_civic_candidate_name3',
            'full_name_assembled',
            'gender',
            'birth_date',
            'bioguide_id',
            'thomas_id',
            'lis_id',
            'govtrack_id',
            'opensecrets_id',
            'vote_smart_id',
            'fec_id',
            'cspan_id',
            'wikipedia_id',
            'ballotpedia_id',
            'house_history_id',
            'maplight_id',
            'washington_post_id',
            'icpsr_id',
            'political_party',
            'state_code',
            'politician_url',
            'politician_twitter_handle',
            'we_vote_hosted_profile_image_url_large',
            'we_vote_hosted_profile_image_url_medium',
            'we_vote_hosted_profile_image_url_tiny',
            'ctcl_uuid',
            'politician_facebook_id',
            'politician_phone_number',
            'politician_googleplus_id',
            'politician_youtube_id',
            'politician_email_address',
            'vote_usa_politician_id')
        if politician_query:
            politician_list_json = list(politician_query)
            return HttpResponse(json.dumps(politician_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'POLITICIAN_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
