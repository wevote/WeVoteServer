# measure/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


from .controllers import add_contest_measure_title_to_next_spot, figure_out_measure_conflict_values, \
    find_duplicate_contest_measure, \
    measures_import_from_master_server, merge_if_duplicate_measures
from .models import ContestMeasure, ContestMeasureListManager, ContestMeasureManager, \
    CONTEST_MEASURE_UNIQUE_IDENTIFIERS, ContestMeasuresArePossibleDuplicates
from admin_tools.views import redirect_to_sign_in_page
from ballot.controllers import move_ballot_items_to_another_measure
from bookmark.models import BookmarkItemList
from config.environment_variable_functions import get_environment_variable
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception
from position.controllers import move_positions_to_another_measure, update_all_position_details_from_contest_measure
from position.models import OPPOSE, PositionEntered, PositionListManager, SUPPORT
from volunteer_task.models import VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION, VolunteerTaskManager
from voter.models import voter_has_authority, fetch_voter_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP, get_voter_api_device_id
from wevote_functions.functions_date import DATE_FORMAT_DAY_TWO_DIGIT, get_current_year_as_integer
from django.http import HttpResponse
import json

MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")  # measuresSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)

@login_required
def measure_delete_process_view(request):
    """
    Delete a measure
    :param request:
    :return:
    """

    measure_id = convert_to_int(request.POST.get('measure_id', 0))
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    state_code = request.POST.get('state_code', '')

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this Measure. '
                             'Please check the checkbox to confirm you want to delete this measure.')
        return HttpResponseRedirect(reverse('measure:measure_edit', args=(measure_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id)+
                                    "&state_code=" + str(state_code))

    contest_measure_manager = ContestMeasureManager()
    results = contest_measure_manager.retrieve_contest_measure_from_id(contest_measure_id=measure_id)
    if results['contest_measure_found']:
        contest_measure = results['contest_measure']
        # if positions are still attached, then don't proceed with deleting the measure
        position_list_manager = PositionListManager()
        retrieve_public_positions = True  # The alternate is positions for friends-only
        position_list = position_list_manager.retrieve_all_positions_for_contest_measure(
            retrieve_public_positions, contest_measure_id=measure_id, contest_measure_we_vote_id=contest_measure.we_vote_id, stance_we_are_looking_for='ANY_STANCE')
        if positive_value_exists(len(position_list)):
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'positions still attached to this measure.')
            return HttpResponseRedirect(reverse('measure:measure_edit', args=(measure_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
        else:
            contest_measure.delete()
            messages.add_message(request, messages.INFO, 'Measure deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'Measure not found.')

    return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))

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

    state_code = request.GET.get('state_code', "")
    status = ""

    results = find_and_merge_duplicate_measures(state_code=state_code)
    if results['measures_merged_found']:
        measures_merged_list = results['measures_merged_list']
        for measure in measures_merged_list:
            messages.add_message(request, messages.INFO,
                                 "Measure {measure_name} automatically merged."
                                 "".format(measure_name=measure.measure_name))
    else:
        status += "No measures found to merge."

    return HttpResponseRedirect(reverse('measure:duplicates_list', args=()) +
                                "?state_code={state_code}"
                                "".format(state_code=state_code))


def find_and_merge_duplicate_measures(state_code=''):
    duplicate_check_complete_measure_we_vote_id_list = []
    contestmeasure_manager = ContestMeasureManager()
    measures_merged_found = False
    measures_merged_list = []
    reset_duplicate_check_last_completed_we_vote_id_list = []
    status = ""
    success = True
    error_results = {
        "duplicate_check_complete_measure_we_vote_id_list": [],
        "measures_merged_found": measures_merged_found,
        "measures_merged_list": measures_merged_list,
        "reset_duplicate_check_last_completed_measure_we_vote_id_list": reset_duplicate_check_last_completed_we_vote_id_list,
        "status": status,
        "success": False,
    }
    # ################################
    # Assemble a list of measures that we already think might be duplicates
    try:
        queryset = ContestMeasuresArePossibleDuplicates.objects.using('readonly').all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        queryset = queryset.exclude(contest_measure1_we_vote_id=None)
        queryset = queryset.exclude(contest_measure2_we_vote_id=None)
        queryset_measure1 = queryset.values_list('contest_measure1_we_vote_id', flat=True).distinct()
        exclude_measure1_we_vote_id_list = list(queryset_measure1)
        queryset_measure2 = queryset.values_list('contest_measure2_we_vote_id', flat=True).distinct()
        exclude_measure2_we_vote_id_list = list(queryset_measure2)
        exclude_measure_we_vote_id_list = \
            list(set(exclude_measure1_we_vote_id_list + exclude_measure2_we_vote_id_list))
    except Exception as e:
        status += f"COULD_NOT_RETRIEVE_POSSIBLE_DUPLICATES: {str(e)} "
        error_results['status'] = status
        return error_results

    # ################################
    # Retrieve list of measures to compare
    try:
        measure_query = ContestMeasure.objects.using('readonly').all()
        if exclude_measure_we_vote_id_list and len(exclude_measure_we_vote_id_list) > 0:
            measure_query = measure_query.exclude(we_vote_id__in=exclude_measure_we_vote_id_list)
        if positive_value_exists(state_code):
            measure_query = measure_query.filter(state_code__iexact=state_code)
        measure_list = list(measure_query)
    except Exception as e:
        status += f"COULD_NOT_RETRIEVE_MEASURES: {str(e)} "
        error_results['status'] = status
        return error_results

    # ################################
    # Loop through all the measures in this state
    try:
        for we_vote_measure in measure_list:
            if we_vote_measure.we_vote_id in exclude_measure_we_vote_id_list:
                continue
            # Start ignore list with entries already reviewed
            ignore_measure_id_list = exclude_measure_we_vote_id_list.copy()
            # Add current entry to ignore list
            ignore_measure_id_list.append(we_vote_measure.we_vote_id)
            # Now check for others we have already labeled as "not a duplicate" of this particular measure
            duplicates_results = \
                contestmeasure_manager.retrieve_measures_are_not_duplicates_list(we_vote_measure.we_vote_id)
            if duplicates_results['success']:
                not_a_duplicate_list = duplicates_results['contest_measures_are_not_duplicates_list_we_vote_ids']
                # Add current entry to ignore list
                ignore_measure_id_list += not_a_duplicate_list
            else:
                status += f"COULD_NOT_RETRIEVE_MEASURES_ARE_NOT_DUPLICATES: {duplicates_results['status']} "

            results = find_duplicate_contest_measure(we_vote_measure, ignore_measure_id_list)

            # If we find measures to merge, store them for review
            if results['contest_measure_merge_possibility_found']:
                measure_option1_for_template = we_vote_measure
                measure_option2_for_template = results['contest_measure_merge_possibility']

                # Can we automatically merge these measures?
                merge_results = merge_if_duplicate_measures(
                    measure_option1_for_template,
                    measure_option2_for_template,
                    results['contest_measure_merge_conflict_values'])
                
                if not state_code:
                    state_code = we_vote_measure.state_code

                if merge_results['measures_merged']:
                    measure = merge_results['measure']
                    if measure.we_vote_id not in exclude_measure_we_vote_id_list:
                        exclude_measure_we_vote_id_list.append(measure.we_vote_id)
                    if we_vote_measure.we_vote_id not in exclude_measure_we_vote_id_list:
                        exclude_measure_we_vote_id_list.append(we_vote_measure.we_vote_id)
                    ContestMeasuresArePossibleDuplicates.objects.create(
                        contest_measure1_we_vote_id=we_vote_measure.we_vote_id,
                        contest_measure2_we_vote_id=None,
                        state_code=state_code,
                    )
                    ContestMeasuresArePossibleDuplicates.objects.create(
                        contest_measure1_we_vote_id=we_vote_measure.we_vote_id,
                        contest_measure2_we_vote_id=measure.we_vote_id,
                        state_code=state_code,
                    )
                    measures_merged_list.append(measure)
                    measures_merged_found = True
                    if measure.we_vote_id not in reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(measure.we_vote_id)
                else:
                    # Add an entry showing that this is a possible match
                    status += (
                        f"[Measure {we_vote_measure.measure_title} "
                        f"({we_vote_measure.we_vote_id}) has possible match.] "
                    )
                    ContestMeasuresArePossibleDuplicates.objects.create(
                        contest_measure1_we_vote_id=we_vote_measure.we_vote_id,
                        contest_measure2_we_vote_id=measure_option2_for_template.we_vote_id,
                        state_code=state_code,
                    )
                    if measure_option2_for_template.we_vote_id not in exclude_measure_we_vote_id_list:
                        exclude_measure_we_vote_id_list.append(measure_option2_for_template.we_vote_id)
                    if we_vote_measure.we_vote_id not in reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(we_vote_measure.we_vote_id)
                    if measure_option2_for_template.we_vote_id not in \
                            reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(
                            measure_option2_for_template.we_vote_id)
            else:
                # No matches found
                ContestMeasuresArePossibleDuplicates.objects.create(
                    contest_measure1_we_vote_id=we_vote_measure.we_vote_id,
                    contest_measure2_we_vote_id=None,
                    state_code=state_code,
                )
                if we_vote_measure.we_vote_id not in duplicate_check_complete_measure_we_vote_id_list:
                    duplicate_check_complete_measure_we_vote_id_list.append(we_vote_measure.we_vote_id)
    except Exception as e:
        status += f"CRASHED_IN_MEASURE_LIST_LOOP: {str(e)} "
        # Fall through to exit function

    return {
        "duplicate_check_complete_measure_we_vote_id_list": duplicate_check_complete_measure_we_vote_id_list,
        "measures_merged_found": measures_merged_found,
        "measures_merged_list": measures_merged_list,
        "reset_duplicate_check_last_completed_we_vote_id_list": reset_duplicate_check_last_completed_we_vote_id_list,
        "status": status,
        "success": success,
    }

# This page does not need to be protected.
# class MeasuresSyncOutView(APIView):
#     def get(self, request, format=None):
def measures_sync_out_view(request):  # measuresSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    status = ''

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
            'measure_subtitle', 'measure_text', 'measure_title', 'measure_url', 'measure_year',
            'ocd_division_id',
            'primary_party', 'state_code',
            'vote_smart_id',
            'vote_usa_measure_id',
            'we_vote_id',
            'referendum_con',
            'referendum_pro',
            'wikipedia_page_id', 'wikipedia_page_title', 'wikipedia_photo_url')
        if contest_measure_list_dict:
            contest_measure_list_json = list(contest_measure_list_dict)
            return HttpResponse(json.dumps(contest_measure_list_json), content_type='application/json')
    except Exception as e:
        status += 'EXCEPTION processing measures_sync_out_view: ' + str(e) + ' '

    status += 'CONTEST_MEASURE_LIST_MISSING '
    json_data = {
        'success': False,
        'status': status,
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

                new_filter = Q(we_vote_id=one_word)
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
                # Find the count of Voters that support this candidate (Endorsers are not included in this)
                one_measure.support_count = position_list_manager.fetch_voter_positions_count_for_contest_measure(
                    one_measure.id, "", SUPPORT)
                one_measure.oppose_count = position_list_manager.fetch_voter_positions_count_for_contest_measure(
                    one_measure.id, "", OPPOSE)
                support_and_oppose_total += one_measure.support_count
                support_and_oppose_total += one_measure.oppose_count

                if positive_value_exists(support_and_oppose_total):
                    percentage_of_oppose_number = one_measure.oppose_count / support_and_oppose_total * 100
                    one_measure.percentage_of_oppose = DATE_FORMAT_DAY_TWO_DIGIT % percentage_of_oppose_number # "%d"
                    percentage_of_support_number = one_measure.support_count / support_and_oppose_total * 100
                    one_measure.percentage_of_support = DATE_FORMAT_DAY_TWO_DIGIT % percentage_of_support_number # "%d"

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
        # figure out which election filter(s) to use for the counts
        if positive_value_exists(google_civic_election_id):
            # specific election selected, ignore the list
            count_result = contest_measure_list_manager.retrieve_measure_count_for_election_and_state(
                google_civic_election_id, one_state_code)
        elif not positive_value_exists(show_all_elections):
            # limit to upcoming elections only (google_civic_election_id_list was built above)
            count_result = contest_measure_list_manager.retrieve_measure_count_for_election_and_state(
                0, one_state_code, google_civic_election_id_list)
        else:
            # show_all_elections: count across every election
            count_result = contest_measure_list_manager.retrieve_measure_count_for_election_and_state(
                0, one_state_code)

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

    measure_list_count_str = f'{measure_list_count:,}'

    status_print_list = ""
    status_print_list += "measure_list_count: " + measure_list_count_str + " "

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
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))

    # try:
    #     measure_list = ContestMeasure.objects.order_by('measure_title')
    #     if positive_value_exists(google_civic_election_id):
    #         measure_list = measure_list.filter(google_civic_election_id=google_civic_election_id)
    # except ContestMeasure.DoesNotExist:
    #     # This is fine
    #     measure_list = ContestMeasure()
    #     pass

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
    messages_on_stage = get_messages(request)
    template_values = {
        'election_list':            election_list,
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
    }
    return render(request, 'measure/measure_edit.html', template_values)

@login_required
def measure_duplicates_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    measure_search = request.GET.get('measure_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = positive_value_exists(request.GET.get('show_all', False))

    duplicates_list = []
    duplicates_list_count = 0
    possible_duplicates_count = 0
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        queryset = ContestMeasuresArePossibleDuplicates.objects.using('readonly').all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        duplicates_list_count = queryset.count()
        queryset = queryset.exclude(
            Q(contest_measure2_we_vote_id__isnull=True) | Q(contest_measure2_we_vote_id=''))
        possible_duplicates_count = queryset.count()
        if positive_value_exists(show_all):
            duplicates_list = list(queryset)
        else:
            duplicates_list = list(queryset[:1000])
    except ObjectDoesNotExist:
        # This is fine
        pass

    measures_dict = {}
    measures_to_display_we_vote_id_list = []
    for one_duplicate in duplicates_list:
        if positive_value_exists(one_duplicate.contest_measure1_we_vote_id):
            measures_to_display_we_vote_id_list.append(one_duplicate.contest_measure1_we_vote_id)
        if positive_value_exists(one_duplicate.contest_measure2_we_vote_id):
            measures_to_display_we_vote_id_list.append(one_duplicate.contest_measure2_we_vote_id)
    try:
        queryset = ContestMeasure.objects.using('readonly').all()
        queryset = queryset.filter(we_vote_id__in=measures_to_display_we_vote_id_list)
        measure_data_list = list(queryset)
        for one_measure in measure_data_list:
            measures_dict[one_measure.we_vote_id] = one_measure
    except Exception as e:
        pass

    duplicates_list_modified = []
    for one_duplicate in duplicates_list:
        if positive_value_exists(one_duplicate.contest_measure1_we_vote_id) \
                and one_duplicate.contest_measure1_we_vote_id in measures_dict \
                and positive_value_exists(one_duplicate.contest_measure2_we_vote_id) \
                and one_duplicate.contest_measure2_we_vote_id in measures_dict:
            one_duplicate.measure1 = measures_dict[one_duplicate.contest_measure1_we_vote_id]
            one_duplicate.measure2 = measures_dict[one_duplicate.contest_measure2_we_vote_id]
            duplicates_list_modified.append(one_duplicate)
        else:
            possible_duplicates_count -= 1

    if measure_search:
        search_words = measure_search.split()
        filtered_duplicates = []

        for duplicate in duplicates_list_modified:
            match_found = False
            for word in search_words:
                word_lower = word.lower()
                # Check measure1
                if duplicate.measure1 and duplicate.measure1.measure_title and word_lower in duplicate.measure1.measure_title.lower():
                    match_found = True
                # Check measure2
                if duplicate.measure2 and duplicate.measure2.measure_title and word_lower in duplicate.measure2.measure_title.lower():
                    match_found = True
            if match_found:
                filtered_duplicates.append(duplicate)

        duplicates_list_modified = filtered_duplicates

    messages.add_message(request, messages.INFO,
                         "Measures analyzed: {duplicates_list_count:,}. "
                         "Possible duplicate measures found: {possible_duplicates_count:,}. "
                         "State: {state_code}"
                         "".format(
                             duplicates_list_count=duplicates_list_count,
                             possible_duplicates_count=possible_duplicates_count,
                             state_code=state_code))

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'google_civic_election_id':     google_civic_election_id,
        'duplicates_list':              duplicates_list_modified,
        'measure_search':               measure_search,
        'show_all':                     show_all,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
    }
    return render(request, 'measure/measure_duplicates_list.html', template_values)

@login_required
def measure_delete_all_duplicates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    if positive_value_exists(state_code):
        queryset = ContestMeasuresArePossibleDuplicates.objects.filter(
            state_code__iexact=state_code,
        )
        queryset.delete()
        messages.add_message(request, messages.INFO, 'Duplicate measure data deleted.')
    else:
        messages.add_message(request, messages.INFO, 'Duplicate measure data NOT deleted. State code missing.')
    return HttpResponseRedirect(reverse('measure:duplicates_list', args=()) +
                                "?state_code=" + str(state_code))

@login_required
def measures_not_duplicates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    measure1_we_vote_id = request.GET.get('contest_measure1_we_vote_id', '')
    measure2_we_vote_id = request.GET.get('contest_measure2_we_vote_id', '')
    state_code = request.GET.get('state_code', '')
    status = ""
    volunteer_task_manager = VolunteerTaskManager()
    voter_id = 0
    voter_we_vote_id = ""
    voter_device_id = get_voter_api_device_id(request)
    if positive_value_exists(voter_device_id):
        voter = fetch_voter_from_voter_device_link(voter_device_id)
        if hasattr(voter, 'we_vote_id'):
            voter_id = voter.id
            voter_we_vote_id = voter.we_vote_id

    contestmeasure_manager = ContestMeasureManager()
    results = contestmeasure_manager.update_or_create_measures_are_not_duplicates(
        measure1_we_vote_id, measure2_we_vote_id)
    if results['success']:
        queryset = ContestMeasuresArePossibleDuplicates.objects.filter(
            contest_measure1_we_vote_id=measure1_we_vote_id,
            contest_measure2_we_vote_id=measure2_we_vote_id,
        )
        queryset.delete()
        messages.add_message(request, messages.INFO, 'Two measures marked as not duplicates.')
        if positive_value_exists(voter_we_vote_id):
            try:
                # Give the volunteer who entered this credit
                task_results = volunteer_task_manager.create_volunteer_task_completed(
                    action_constant=VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION,
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-DEDUPLICATION: ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    else:
        messages.add_message(request, messages.ERROR,
                             'Could not save measures_are_not_duplicates entry: ' +
                             results['status'])
    return HttpResponseRedirect(reverse('measure:duplicates_list', args=()) +
                                "?state_code=" + str(state_code))

@login_required
def measure_edit_view(request, measure_id=0, measure_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))

    messages_on_stage = get_messages(request)
    measure_id = convert_to_int(measure_id)
    measure_on_stage_found = False
    try:
        if positive_value_exists(measure_id):
            measure_on_stage = ContestMeasure.objects.get(id=measure_id)
            measure_on_stage_found = True
            google_civic_election_id = measure_on_stage.google_civic_election_id
        elif positive_value_exists(measure_we_vote_id):
            measure_on_stage = ContestMeasure.objects.get(we_vote_id=measure_we_vote_id)
            google_civic_election_id = measure_on_stage.google_civic_election_id
            measure_on_stage_found = True
        else:
            measure_on_stage = None
    except ContestMeasure.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        measure_on_stage = None
    except ContestMeasure.DoesNotExist:
        # This is fine, create new
        measure_on_stage = None
        pass

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

    template_values = {
        'election_list':            election_list,
        'google_civic_election_id': google_civic_election_id,
        'measure':                  measure_on_stage,
        'messages_on_stage':        messages_on_stage,
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
    google_civic_election_id = request.POST.get('google_civic_election_id', False)
    google_civic_measure_title = request.POST.get('google_civic_measure_title', False)
    google_civic_measure_title2 = request.POST.get('google_civic_measure_title2', False)
    google_civic_measure_title3 = request.POST.get('google_civic_measure_title3', False)
    google_civic_measure_title4 = request.POST.get('google_civic_measure_title4', False)
    google_civic_measure_title5 = request.POST.get('google_civic_measure_title5', False)
    measure_id = convert_to_int(request.POST['measure_id'])
    measure_title = request.POST.get('measure_title', False)
    measure_subtitle = request.POST.get('measure_subtitle', False)
    measure_text = request.POST.get('measure_text', False)
    measure_url = request.POST.get('measure_url', False)
    measure_year = request.POST.get('measure_year', False)
    maplight_id = request.POST.get('maplight_id', False)
    referendum_con = request.POST.get('referendum_con', False)
    referendum_pro = request.POST.get('referendum_pro', False)
    vote_smart_id = request.POST.get('vote_smart_id', False)
    vote_usa_measure_id = request.POST.get('vote_usa_measure_id', False)
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
                    if ballotpedia_district_id == '':
                        measure_on_stage.ballotpedia_district_id = 0
                    else:
                        measure_on_stage.ballotpedia_district_id = ballotpedia_district_id
                if ballotpedia_election_id is not False:
                    if ballotpedia_election_id == '':
                        measure_on_stage.ballotpedia_election_id = 0
                    else:
                        measure_on_stage.ballotpedia_election_id = ballotpedia_election_id
                if ballotpedia_measure_status is not False:
                    measure_on_stage.ballotpedia_measure_status = ballotpedia_measure_status
                if ballotpedia_measure_url is not False:
                    measure_on_stage.ballotpedia_measure_url = ballotpedia_measure_url
                if ballotpedia_no_vote_description is not False:
                    measure_on_stage.ballotpedia_no_vote_description = ballotpedia_no_vote_description
                if ballotpedia_yes_vote_description is not False:
                    measure_on_stage.ballotpedia_yes_vote_description = ballotpedia_yes_vote_description
                if google_civic_election_id is not False:
                    measure_on_stage.google_civic_election_id = google_civic_election_id
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
                if measure_year is not False:
                    measure_on_stage.measure_year = measure_year
                if maplight_id is not False:
                    measure_on_stage.maplight_id = maplight_id
                if referendum_con is not False:
                    measure_on_stage.referendum_con = referendum_con
                if referendum_pro is not False:
                    measure_on_stage.referendum_pro = referendum_pro
                if vote_smart_id is not False:
                    measure_on_stage.vote_smart_id = vote_smart_id
                if vote_usa_measure_id is not False:
                    measure_on_stage.vote_usa_measure_id = vote_usa_measure_id
                if state_code is not False:
                    measure_on_stage.state_code = state_code

                if positive_value_exists(measure_on_stage.we_vote_id):
                    measure_on_stage.save()
                    messages.add_message(request, messages.INFO, 'ContestMeasure updated.')
                    update_position_results = update_all_position_details_from_contest_measure(measure_on_stage)
                else:
                    messages.add_message(request, messages.ERROR, 'ContestMeasure NOT updated -- missing we_vote_id.')
            else:
                # Create new
                if not positive_value_exists(measure_year):
                    measure_year = get_current_year_as_integer()
                measure_on_stage = ContestMeasure(
                    ballotpedia_measure_status=ballotpedia_measure_status,
                    ballotpedia_measure_url=ballotpedia_measure_url,
                    google_civic_election_id=google_civic_election_id,
                    google_civic_measure_title=google_civic_measure_title,
                    google_civic_measure_title2=google_civic_measure_title2,
                    google_civic_measure_title3=google_civic_measure_title3,
                    google_civic_measure_title4=google_civic_measure_title4,
                    google_civic_measure_title5=google_civic_measure_title5,
                    measure_subtitle=measure_subtitle,
                    measure_text=measure_text,
                    measure_title=measure_title,
                    measure_url=measure_url,
                    measure_year=measure_year,
                    state_code=state_code,
                    maplight_id=maplight_id,
                    vote_smart_id=vote_smart_id,
                    vote_usa_measure_id=vote_usa_measure_id,
                )
                if ballotpedia_district_id is not False:
                    if ballotpedia_district_id == '':
                        measure_on_stage.ballotpedia_district_id = 0
                    else:
                        measure_on_stage.ballotpedia_district_id = ballotpedia_district_id
                if ballotpedia_election_id is not False:
                    if ballotpedia_election_id == '':
                        measure_on_stage.ballotpedia_election_id = 0
                    else:
                        measure_on_stage.ballotpedia_election_id = ballotpedia_election_id
                if ballotpedia_no_vote_description is not False:
                    measure_on_stage.ballotpedia_no_vote_description = ballotpedia_no_vote_description
                if ballotpedia_yes_vote_description is not False:
                    measure_on_stage.ballotpedia_yes_vote_description = ballotpedia_yes_vote_description
                if referendum_con is not False:
                    measure_on_stage.referendum_con = referendum_con
                if referendum_pro is not False:
                    measure_on_stage.referendum_pro = referendum_pro
                measure_on_stage.save()
                messages.add_message(request, messages.INFO, 'New measure saved.')
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not save measure: ' + str(e))

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
        measure_queryset = measure_queryset.exclude(we_vote_id=measure_we_vote_id)

        if positive_value_exists(state_code):
            measure_queryset = measure_queryset.filter(state_code__iexact=state_code)

        search_words = measure_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(measure_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id=one_word)
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
                contest_measure_we_vote_id=measure_on_stage.we_vote_id)
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
