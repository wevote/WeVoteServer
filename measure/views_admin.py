# measure/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


from .controllers import fetch_duplicate_measure_count, figure_out_measure_conflict_values, \
    find_duplicate_contest_measure, \
    measures_import_from_master_server
from .models import ContestMeasure, ContestMeasureListManager, ContestMeasureManager, \
    CONTEST_MEASURE_UNIQUE_IDENTIFIERS
from admin_tools.views import redirect_to_sign_in_page
from ballot.controllers import move_ballot_items_to_another_measure
from bookmark.models import BookmarkItemList
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from position.controllers import move_positions_to_another_measure
from position.models import OPPOSE, PositionEntered, PositionListManager, SUPPORT
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from django.http import HttpResponse
import json

MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")  # measuresSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def compare_two_measures_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_measure1_we_vote_id = request.GET.get('contest_measure1_we_vote_id', 0)
    contest_measure2_we_vote_id = request.GET.get('contest_measure2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    contest_measure_manager = ContestMeasureManager()
    contest_measure_results = \
        contest_measure_manager.retrieve_contest_measure_from_we_vote_id(contest_measure1_we_vote_id)
    if not contest_measure_results['contest_measure_found']:
        messages.add_message(request, messages.ERROR, "Contest Office1 not found.")
        return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    contest_measure_option1_for_template = contest_measure_results['contest_measure']

    contest_measure_results = \
        contest_measure_manager.retrieve_contest_measure_from_we_vote_id(contest_measure2_we_vote_id)
    if not contest_measure_results['contest_measure_found']:
        messages.add_message(request, messages.ERROR, "Contest Office2 not found.")
        return HttpResponseRedirect(reverse('measure:measure_summary',
                                            args=(contest_measure_option1_for_template.id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    contest_measure_option2_for_template = contest_measure_results['contest_measure']

    contest_measure_merge_conflict_values = figure_out_measure_conflict_values(
        contest_measure_option1_for_template, contest_measure_option2_for_template)

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another measure to merge after finishing
    return render_contest_measure_merge_form(request, contest_measure_option1_for_template,
                                             contest_measure_option2_for_template,
                                             contest_measure_merge_conflict_values,
                                             remove_duplicate_process)


@login_required
def find_and_merge_duplicate_measures_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_measure_list = []
    ignore_measure_we_vote_id_list = []
    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    contest_measure_manager = ContestMeasureManager()

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('measure:measure_list', args=()))

    try:
        # We sort by ID so that the entry which was saved first becomes the "master"
        contest_measure_query = ContestMeasure.objects.order_by('id')
        contest_measure_query = contest_measure_query.filter(google_civic_election_id=google_civic_election_id)
        contest_measure_list = list(contest_measure_query)
    except ContestMeasure.DoesNotExist:
        pass

    # Loop through all of the measures in this election to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
        duplicate_measure_count = 0
        for contest_measure in contest_measure_list:
            # Note that we don't reset the ignore_measure_we_vote_id_list, so we don't search for a duplicate
            # both directions
            ignore_measure_we_vote_id_list.append(contest_measure.we_vote_id)
            duplicate_measure_count_temp = fetch_duplicate_measure_count(contest_measure,
                                                                         ignore_measure_we_vote_id_list)
            duplicate_measure_count += duplicate_measure_count_temp

        if positive_value_exists(duplicate_measure_count):
            messages.add_message(request, messages.INFO, "There are approximately {duplicate_measure_count} "
                                                         "possible duplicates."
                                                         "".format(duplicate_measure_count=duplicate_measure_count))

    # Loop through all of the contest measures in this election
    ignore_measure_we_vote_id_list = []
    for contest_measure in contest_measure_list:
        # Add current contest measure entry to the ignore list
        ignore_measure_we_vote_id_list.append(contest_measure.we_vote_id)
        # Now check to for other contest measures we have labeled as "not a duplicate"
        not_a_duplicate_list = contest_measure_manager.fetch_measures_are_not_duplicates_list_we_vote_ids(
            contest_measure.we_vote_id)

        ignore_measure_we_vote_id_list += not_a_duplicate_list

        results = find_duplicate_contest_measure(contest_measure, ignore_measure_we_vote_id_list)
        ignore_measure_we_vote_id_list = []

        # If we find contest measures to merge, stop and ask for confirmation
        if results['contest_measure_merge_possibility_found']:
            contest_measure_option1_for_template = contest_measure
            contest_measure_option2_for_template = results['contest_measure_merge_possibility']

            # This view function takes us to displaying a template
            remove_duplicate_process = True  # Try to find another measure to merge after finishing
            return render_contest_measure_merge_form(request, contest_measure_option1_for_template,
                                                     contest_measure_option2_for_template,
                                                     results['contest_measure_merge_conflict_values'],
                                                     remove_duplicate_process)

    message = "Google Civic Election ID: {election_id}, " \
              "No duplicate contest measures found for this election." \
              "".format(election_id=google_civic_election_id)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('measure:measure_list', args=()) + "?google_civic_election_id={var}"
                                                                           "".format(var=google_civic_election_id))


# This page does not need to be protected.
# class MeasuresSyncOutView(APIView):
#     def get(self, request, format=None):
def measures_sync_out_view(request):  # measuresSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    try:
        contest_measure_query = ContestMeasure.objects.using('readonly').all()
        if positive_value_exists(google_civic_election_id):
            contest_measure_query = contest_measure_query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            contest_measure_query = contest_measure_query.filter(state_code__iexact=state_code)
        contest_measure_list_dict = contest_measure_query.values(
            'ballotpedia_district_id', 'ballotpedia_election_id',
            'ballotpedia_measure_id', 'ballotpedia_measure_name',
            'ballotpedia_measure_status', 'ballotpedia_measure_summary', 'ballotpedia_measure_text',
            'ballotpedia_measure_url',
            'ballotpedia_no_vote_description',
            'ballotpedia_page_title', 'ballotpedia_photo_url',
            'ballotpedia_yes_vote_description',
            'ctcl_uuid',
            'district_id', 'district_name', 'district_scope',
            'election_day_text',
            'google_ballot_placement', 'google_civic_election_id',
            'google_civic_measure_title', 'google_civic_measure_title2', 'google_civic_measure_title3',
            'google_civic_measure_title4', 'google_civic_measure_title5',
            'maplight_id',
            'measure_subtitle', 'measure_text', 'measure_title', 'measure_url',
            'ocd_division_id',
            'primary_party', 'state_code',
            'vote_smart_id',
            'we_vote_id',
            'wikipedia_page_id', 'wikipedia_page_title', 'wikipedia_photo_url')
        if contest_measure_list_dict:
            contest_measure_list_json = list(contest_measure_list_dict)
            return HttpResponse(json.dumps(contest_measure_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'CONTEST_MEASURE_LIST_MISSING'
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def measures_import_from_master_server_view(request):  # GET '/m/import/?google_civic_election_id=nnn&state_code=xx'
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in MEASURES_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id):
        logger.error("measures_import_from_master_server_view did not receive a google_civic_election_id")

    results = measures_import_from_master_server(request, google_civic_election_id, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Measures import completed. '
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
def measure_merge_process_view(request):
    """
    Process the merging of two measures
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    contest_measure_manager = ContestMeasureManager()

    merge = request.POST.get('merge', False)
    skip = request.POST.get('skip', False)

    # Contest measure 1 is the one we keep, and Contest measure 2 is the one we will merge into Contest measure 1
    contest_measure1_we_vote_id = request.POST.get('contest_measure1_we_vote_id', 0)
    contest_measure2_we_vote_id = request.POST.get('contest_measure2_we_vote_id', 0)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    redirect_to_contest_measure_list = \
        positive_value_exists(request.POST.get('redirect_to_contest_measure_list', False))
    remove_duplicate_process = positive_value_exists(request.POST.get('remove_duplicate_process', False))
    state_code = request.POST.get('state_code', '')

    if positive_value_exists(skip):
        results = contest_measure_manager.update_or_create_contest_measures_are_not_duplicates(
            contest_measure1_we_vote_id, contest_measure2_we_vote_id)
        if not results['new_contest_measures_are_not_duplicates_created']:
            messages.add_message(request, messages.ERROR, 'Could not save contest_measures_are_not_duplicates entry: ' +
                                 results['status'])
        messages.add_message(request, messages.INFO, 'Prior contest measures skipped, and not merged.')
        return HttpResponseRedirect(reverse('measure:find_and_merge_duplicate_measures', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    contest_measure1_results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
        contest_measure1_we_vote_id)
    if contest_measure1_results['contest_measure_found']:
        contest_measure1_on_stage = contest_measure1_results['contest_measure']
        contest_measure1_id = contest_measure1_on_stage.id
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve measure 1.')
        return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    contest_measure2_results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
        contest_measure2_we_vote_id)
    if contest_measure2_results['contest_measure_found']:
        contest_measure2_on_stage = contest_measure2_results['contest_measure']
        contest_measure2_id = contest_measure2_on_stage.id
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve contest measure 2.')
        return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    # TODO: Merge quick_info's measure details in future
    # TODO: Migrate bookmarks
    bookmark_item_list_manager = BookmarkItemList()
    bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_measure(
        contest_measure2_we_vote_id)
    if bookmark_results['bookmark_item_list_found']:
        messages.add_message(request, messages.ERROR, "Bookmarks found for Contest Office 2 - "
                                                      "automatic merge not working yet.")
        return HttpResponseRedirect(reverse('measure:find_and_merge_duplicate_measures', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Merge attribute values
    conflict_values = figure_out_measure_conflict_values(contest_measure1_on_stage, contest_measure2_on_stage)
    for attribute in CONTEST_MEASURE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            choice = request.POST.get(attribute + '_choice', '')
            if contest_measure2_we_vote_id == choice:
                setattr(contest_measure1_on_stage, attribute, getattr(contest_measure2_on_stage, attribute))
        elif conflict_value == "CONTEST_MEASURE2":
            setattr(contest_measure1_on_stage, attribute, getattr(contest_measure2_on_stage, attribute))

    # Preserve unique google_civic_measure_title, _title2, _title3, _title4 and _title5
    if positive_value_exists(contest_measure2_on_stage.google_civic_measure_title):
        contest_measure1_on_stage = add_contest_measure_title_to_next_spot(
            contest_measure1_on_stage, contest_measure2_on_stage.google_civic_measure_title)
    if positive_value_exists(contest_measure2_on_stage.google_civic_measure_title2):
        contest_measure1_on_stage = add_contest_measure_title_to_next_spot(
            contest_measure1_on_stage, contest_measure2_on_stage.google_civic_measure_title2)
    if positive_value_exists(contest_measure2_on_stage.google_civic_measure_title3):
        contest_measure1_on_stage = add_contest_measure_title_to_next_spot(
            contest_measure1_on_stage, contest_measure2_on_stage.google_civic_measure_title3)
    if positive_value_exists(contest_measure2_on_stage.google_civic_measure_title4):
        contest_measure1_on_stage = add_contest_measure_title_to_next_spot(
            contest_measure1_on_stage, contest_measure2_on_stage.google_civic_measure_title4)
    if positive_value_exists(contest_measure2_on_stage.google_civic_measure_title5):
        contest_measure1_on_stage = add_contest_measure_title_to_next_spot(
            contest_measure1_on_stage, contest_measure2_on_stage.google_civic_measure_title5)

    # Merge ballot item's measure details
    ballot_items_results = move_ballot_items_to_another_measure(contest_measure2_id, contest_measure2_we_vote_id,
                                                                contest_measure1_id, contest_measure1_we_vote_id,
                                                                contest_measure1_on_stage)
    if not ballot_items_results['success']:
        messages.add_message(request, messages.ERROR, ballot_items_results['status'])
        return HttpResponseRedirect(reverse('measure:find_and_merge_duplicate_measures', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Merge public positions
    public_positions_results = move_positions_to_another_measure(contest_measure2_id, contest_measure2_we_vote_id,
                                                                 contest_measure1_id, contest_measure1_we_vote_id,
                                                                 True)
    if not public_positions_results['success']:
        messages.add_message(request, messages.ERROR, public_positions_results['status'])
        return HttpResponseRedirect(reverse('measure:find_and_merge_duplicate_measures', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Merge friends-only positions
    friends_positions_results = move_positions_to_another_measure(contest_measure2_id, contest_measure2_we_vote_id,
                                                                  contest_measure1_id, contest_measure1_we_vote_id,
                                                                  False)
    if not friends_positions_results['success']:
        messages.add_message(request, messages.ERROR, friends_positions_results['status'])
        return HttpResponseRedirect(reverse('measure:find_and_merge_duplicate_measures', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # Remove contest measure 2
    contest_measure2_on_stage.delete()

    # Note: wait to wrap in try/except block
    contest_measure1_on_stage.save()
    # There isn't any measure data to refresh from other master tables

    if redirect_to_contest_measure_list:
        return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('measure:find_and_merge_duplicate_measures', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('measure:measure_edit', args=(contest_measure1_on_stage.id,)))


def add_contest_measure_title_to_next_spot(contest_measure_to_update, google_civic_measure_title_to_add):
    if not positive_value_exists(google_civic_measure_title_to_add):
        return contest_measure_to_update

    if not positive_value_exists(contest_measure_to_update.google_civic_measure_title):
        contest_measure_to_update.google_civic_measure_title = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title2):
        contest_measure_to_update.google_civic_measure_title2 = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title2:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title3):
        contest_measure_to_update.google_civic_measure_title3 = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title3:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title4):
        contest_measure_to_update.google_civic_measure_title4 = google_civic_measure_title_to_add
    elif google_civic_measure_title_to_add == contest_measure_to_update.google_civic_measure_title4:
        pass
    elif not positive_value_exists(contest_measure_to_update.google_civic_measure_title5):
        contest_measure_to_update.google_civic_measure_title5 = google_civic_measure_title_to_add
    return contest_measure_to_update

@login_required
def measure_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
    state_code = request.GET.get('state_code', '')
    measure_search = request.GET.get('measure_search', '')

    google_civic_election_id_list = []
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

    measure_list_count = 0
    position_list_manager = PositionListManager()
    measure_list_modified = []
    try:
        measure_list = ContestMeasure.objects.order_by('measure_title')
        if positive_value_exists(google_civic_election_id):
            measure_list = measure_list.filter(google_civic_election_id=google_civic_election_id)
        elif positive_value_exists(show_all_elections):
            pass
        else:
            # Limit this search to upcoming_elections only
            for one_election in election_list:
                google_civic_election_id_list.append(one_election.google_civic_election_id)
            measure_list = measure_list.filter(google_civic_election_id__in=google_civic_election_id_list)
        if positive_value_exists(state_code):
            measure_list = measure_list.filter(state_code__iexact=state_code)

        if positive_value_exists(measure_search):
            search_words = measure_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(state_code__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(measure_title__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    measure_list = measure_list.filter(final_filters)

        measure_list_count = measure_list.count()

        if positive_value_exists(google_civic_election_id):
            for one_measure in measure_list:
                support_and_oppose_total = 0
                # Find the count of Voters that support this candidate (Organizations are not included in this)
                one_measure.support_count = position_list_manager.fetch_voter_positions_count_for_contest_measure(
                    one_measure.id, "", SUPPORT)
                one_measure.oppose_count = position_list_manager.fetch_voter_positions_count_for_contest_measure(
                    one_measure.id, "", OPPOSE)
                support_and_oppose_total += one_measure.support_count
                support_and_oppose_total += one_measure.oppose_count

                if positive_value_exists(support_and_oppose_total):
                    percentage_of_oppose_number = one_measure.oppose_count / support_and_oppose_total * 100
                    one_measure.percentage_of_oppose = "%d" % percentage_of_oppose_number
                    percentage_of_support_number = one_measure.support_count / support_and_oppose_total * 100
                    one_measure.percentage_of_support = "%d" % percentage_of_support_number

                measure_list_modified.append(one_measure)
        else:
            measure_list_modified = measure_list

    except ContestMeasure.DoesNotExist:
        # This is fine
        measure_list_modified = []
        pass

    state_list = STATE_CODE_MAP
    state_list_modified = {}
    contest_measure_list_manager = ContestMeasureListManager()
    for one_state_code, one_state_name in state_list.items():
        count_result = contest_measure_list_manager.retrieve_measure_count_for_election_and_state(
            google_civic_election_id, one_state_code)
        state_name_modified = one_state_name
        if positive_value_exists(count_result['measure_count']):
            state_name_modified += " - " + str(count_result['measure_count'])
            state_list_modified[one_state_code] = state_name_modified
        elif str(one_state_code.lower()) == str(state_code.lower()):
            state_name_modified += " - 0"
            state_list_modified[one_state_code] = state_name_modified
        else:
            # Do not include state in drop-down if there aren't any candidates in that state
            pass
    sorted_state_list = sorted(state_list_modified.items())

    status_print_list = ""
    status_print_list += "measure_list_count: " + \
                         str(measure_list_count) + " "

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'measure_list':             measure_list_modified,
        'election_list':            election_list,
        'show_all_elections':       show_all_elections,
        'state_list':               sorted_state_list,
        'measure_search':           measure_search,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
    }
    return render(request, 'measure/measure_list.html', template_values)


@login_required
def measure_new_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    try:
        measure_list = ContestMeasure.objects.order_by('measure_title')
        if positive_value_exists(google_civic_election_id):
            measure_list = measure_list.filter(google_civic_election_id=google_civic_election_id)
    except ContestMeasure.DoesNotExist:
        # This is fine
        measure_list = ContestMeasure()
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'measure_list':             measure_list,
    }
    return render(request, 'measure/measure_edit.html', template_values)


@login_required
def measure_edit_view(request, measure_id=0, measure_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    measure_id = convert_to_int(measure_id)
    measure_on_stage_found = False
    try:
        if positive_value_exists(measure_id):
            measure_on_stage = ContestMeasure.objects.get(id=measure_id)
            measure_on_stage_found = True
        elif positive_value_exists(measure_we_vote_id):
            measure_on_stage = ContestMeasure.objects.get(we_vote_id=measure_we_vote_id)
            measure_on_stage_found = True
        else:
            measure_on_stage = ContestMeasure()
    except ContestMeasure.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        measure_on_stage = ContestMeasure()
    except ContestMeasure.DoesNotExist:
        # This is fine, create new
        measure_on_stage = ContestMeasure()
        pass

    if measure_on_stage_found:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
            'measure':                  measure_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage':        messages_on_stage,
            'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'measure/measure_edit.html', template_values)


@login_required
def measure_edit_process_view(request):
    """
    Process the new or edit measure forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ballotpedia_district_id = request.POST.get('ballotpedia_district_id', False)
    ballotpedia_election_id = request.POST.get('ballotpedia_election_id', False)
    ballotpedia_measure_status = request.POST.get('ballotpedia_measure_status', False)
    ballotpedia_measure_url = request.POST.get('ballotpedia_measure_url', False)
    ballotpedia_no_vote_description = request.POST.get('ballotpedia_no_vote_description', False)
    ballotpedia_yes_vote_description = request.POST.get('ballotpedia_yes_vote_description', False)
    measure_id = convert_to_int(request.POST['measure_id'])
    measure_title = request.POST.get('measure_title', False)
    google_civic_measure_title = request.POST.get('google_civic_measure_title', False)
    google_civic_measure_title2 = request.POST.get('google_civic_measure_title2', False)
    google_civic_measure_title3 = request.POST.get('google_civic_measure_title3', False)
    google_civic_measure_title4 = request.POST.get('google_civic_measure_title4', False)
    google_civic_measure_title5 = request.POST.get('google_civic_measure_title5', False)
    measure_subtitle = request.POST.get('measure_subtitle', False)
    measure_text = request.POST.get('measure_text', False)
    measure_url = request.POST.get('measure_url', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    maplight_id = request.POST.get('maplight_id', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    state_code = request.POST.get('state_code', False)

    # Check to see if this measure exists
    measure_on_stage_found = False
    measure_on_stage = ContestMeasure()
    error = False
    try:
        if positive_value_exists(measure_id):
            measure_query = ContestMeasure.objects.filter(id=measure_id)
            if len(measure_query):
                measure_on_stage = measure_query[0]
                measure_on_stage_found = True
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'There was an error trying to find this measure.')
        error = True

    if not error:
        try:
            if measure_on_stage_found:
                # Update
                if ballotpedia_district_id is not False:
                    measure_on_stage.ballotpedia_district_id = ballotpedia_district_id
                if ballotpedia_election_id is not False:
                    measure_on_stage.ballotpedia_election_id = ballotpedia_election_id
                if ballotpedia_measure_status is not False:
                    measure_on_stage.ballotpedia_measure_status = ballotpedia_measure_status
                if ballotpedia_measure_url is not False:
                    measure_on_stage.ballotpedia_measure_url = ballotpedia_measure_url
                if ballotpedia_no_vote_description is not False:
                    measure_on_stage.ballotpedia_no_vote_description = ballotpedia_no_vote_description
                if ballotpedia_yes_vote_description is not False:
                    measure_on_stage.ballotpedia_yes_vote_description = ballotpedia_yes_vote_description
                if google_civic_measure_title is not False:
                    measure_on_stage.google_civic_measure_title = google_civic_measure_title
                if google_civic_measure_title2 is not False:
                    measure_on_stage.google_civic_measure_title2 = google_civic_measure_title2
                if google_civic_measure_title3 is not False:
                    measure_on_stage.google_civic_measure_title3 = google_civic_measure_title3
                if google_civic_measure_title4 is not False:
                    measure_on_stage.google_civic_measure_title4 = google_civic_measure_title4
                if google_civic_measure_title5 is not False:
                    measure_on_stage.google_civic_measure_title5 = google_civic_measure_title5
                if measure_title is not False:
                    measure_on_stage.measure_title = measure_title
                if measure_subtitle is not False:
                    measure_on_stage.measure_subtitle = measure_subtitle
                if measure_text is not False:
                    measure_on_stage.measure_text = measure_text
                if measure_url is not False:
                    measure_on_stage.measure_url = measure_url
                if google_civic_election_id is not False:
                    measure_on_stage.google_civic_election_id = google_civic_election_id
                if maplight_id is not False:
                    measure_on_stage.maplight_id = maplight_id
                if vote_smart_id is not False:
                    measure_on_stage.vote_smart_id = vote_smart_id
                if state_code is not False:
                    measure_on_stage.state_code = state_code

                if positive_value_exists(measure_on_stage.we_vote_id):
                    measure_on_stage.save()
                    messages.add_message(request, messages.INFO, 'ContestMeasure updated.')
                else:
                    messages.add_message(request, messages.ERROR, 'ContestMeasure NOT updated -- missing we_vote_id.')
            else:
                # Create new
                measure_on_stage = ContestMeasure(
                    ballotpedia_district_id=ballotpedia_district_id,
                    ballotpedia_election_id=ballotpedia_election_id,
                    ballotpedia_measure_status=ballotpedia_measure_status,
                    ballotpedia_measure_url=ballotpedia_measure_url,
                    ballotpedia_no_vote_description=ballotpedia_no_vote_description,
                    ballotpedia_yes_vote_description=ballotpedia_yes_vote_description,
                    google_civic_measure_title=google_civic_measure_title,
                    google_civic_measure_title2=google_civic_measure_title2,
                    google_civic_measure_title3=google_civic_measure_title3,
                    google_civic_measure_title4=google_civic_measure_title4,
                    google_civic_measure_title5=google_civic_measure_title5,
                    measure_subtitle=measure_subtitle,
                    measure_text=measure_text,
                    measure_title=measure_title,
                    measure_url=measure_url,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    maplight_id=maplight_id,
                    vote_smart_id=vote_smart_id,
                )
                measure_on_stage.save()
                messages.add_message(request, messages.INFO, 'New measure saved.')
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not save measure.')

    return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def measure_summary_view(request, measure_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    measure_id = convert_to_int(measure_id)
    measure_we_vote_id = ''
    measure_on_stage_found = False
    measure_on_stage = ContestMeasure()
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', "")

    measure_search = request.GET.get('measure_search', "")

    try:
        measure_on_stage = ContestMeasure.objects.get(id=measure_id)
        measure_we_vote_id = measure_on_stage.we_vote_id
        measure_on_stage_found = True
    except ContestMeasure.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ContestMeasure.DoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')

    measure_search_results_list = []
    if positive_value_exists(measure_search) and positive_value_exists(measure_we_vote_id):
        measure_queryset = ContestMeasure.objects.all()
        measure_queryset = measure_queryset.filter(google_civic_election_id=google_civic_election_id)
        measure_queryset = measure_queryset.exclude(we_vote_id__iexact=measure_we_vote_id)

        if positive_value_exists(state_code):
            measure_queryset = measure_queryset.filter(state_code__iexact=state_code)

        search_words = measure_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(measure_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(ballotpedia_measure_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title2__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title3__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title4__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(google_civic_measure_title5__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                measure_queryset = measure_queryset.filter(final_filters)

        measure_search_results_list = list(measure_queryset)
    elif measure_on_stage_found:
        ignore_measure_we_vote_id_list = []
        ignore_measure_we_vote_id_list.append(measure_on_stage.we_vote_id)
        results = find_duplicate_contest_measure(measure_on_stage, ignore_measure_we_vote_id_list)
        if results['contest_measure_merge_possibility_found']:
            measure_search_results_list = results['contest_measure_list']

    if measure_on_stage_found:
        # Working with We Vote Positions
        try:
            measure_position_query = PositionEntered.objects.order_by('stance')
            measure_position_query = measure_position_query.filter(
                contest_measure_we_vote_id__iexact=measure_on_stage.we_vote_id)
            # if positive_value_exists(google_civic_election_id):
            #     measure_position_query = measure_position_query.filter(
            #         google_civic_election_id=google_civic_election_id)
            measure_position_list = list(measure_position_query)
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            measure_position_list = []

    if measure_on_stage_found:
        template_values = {
            'election_list': election_list,
            'google_civic_election_id': google_civic_election_id,
            'measure': measure_on_stage,
            'measure_position_list': measure_position_list,
            'measure_search_results_list': measure_search_results_list,
            'messages_on_stage': messages_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'measure/measure_summary.html', template_values)


def render_contest_measure_merge_form(
        request, contest_measure_option1_for_template, contest_measure_option2_for_template,
        contest_measure_merge_conflict_values, remove_duplicate_process=True):
    position_list_manager = PositionListManager()

    bookmark_item_list_manager = BookmarkItemList()

    # Get positions counts for both measures
    contest_measure_option1_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_contest_measure(
            contest_measure_option1_for_template.id, contest_measure_option1_for_template.we_vote_id)
    contest_measure_option1_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_contest_measure(
            contest_measure_option1_for_template.id, contest_measure_option1_for_template.we_vote_id)
    # Bookmarks for option 1
    bookmark_results1 = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_measure(
        contest_measure_option1_for_template.we_vote_id)
    if bookmark_results1['bookmark_item_list_found']:
        bookmark_item_list = bookmark_results1['bookmark_item_list']
        contest_measure_option1_bookmark_count = len(bookmark_item_list)
    else:
        contest_measure_option1_bookmark_count = 0
    contest_measure_option1_for_template.bookmarks_count = contest_measure_option1_bookmark_count

    contest_measure_option2_for_template.public_positions_count = \
        position_list_manager.fetch_public_positions_count_for_contest_measure(
            contest_measure_option2_for_template.id, contest_measure_option2_for_template.we_vote_id)
    contest_measure_option2_for_template.friends_positions_count = \
        position_list_manager.fetch_friends_only_positions_count_for_contest_measure(
            contest_measure_option2_for_template.id, contest_measure_option2_for_template.we_vote_id)
    # Bookmarks for option 2
    bookmark_results2 = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_measure(
        contest_measure_option2_for_template.we_vote_id)
    if bookmark_results2['bookmark_item_list_found']:
        bookmark_item_list = bookmark_results2['bookmark_item_list']
        contest_measure_option2_bookmark_count = len(bookmark_item_list)
    else:
        contest_measure_option2_bookmark_count = 0
    contest_measure_option2_for_template.bookmarks_count = contest_measure_option2_bookmark_count

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'contest_measure_option1':  contest_measure_option1_for_template,
        'contest_measure_option2':  contest_measure_option2_for_template,
        'conflict_values':          contest_measure_merge_conflict_values,
        'google_civic_election_id': contest_measure_option1_for_template.google_civic_election_id,
        'remove_duplicate_process': remove_duplicate_process,
    }
    return render(request, 'measure/measure_merge.html', template_values)
