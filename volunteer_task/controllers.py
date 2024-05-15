# volunteer_task/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import date, timedelta
from volunteer_task.models import VOLUNTEER_ACTION_CANDIDATE_CREATED, \
    VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS, VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED, \
    VOLUNTEER_ACTION_MATCH_CANDIDATES_TO_POLITICIANS, \
    VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION, VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION, \
    VOLUNTEER_ACTION_POLITICIAN_PHOTO, VOLUNTEER_ACTION_POLITICIAN_REQUEST, \
    VOLUNTEER_ACTION_POSITION_COMMENT_SAVED, VOLUNTEER_ACTION_POSITION_SAVED, \
    VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE, \
    VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED, VolunteerTaskCompleted, \
    VolunteerWeeklyMetrics
from voter.models import Voter
from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import convert_date_as_integer_to_date, convert_date_to_date_as_integer
from wevote_settings.models import fetch_volunteer_task_weekly_metrics_last_updated, WeVoteSetting, \
    WeVoteSettingsManager

START_AND_END_OF_WEEK_BY_WEEKDAY = {
    0: 6,
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
}
WEEKDAY_WRAPAROUND_DICT = {
    -7: 0,
    -6: 1,
    -5: 2,
    -4: 3,
    -3: 4,
    -2: 5,
    -1: 6,
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 0,
    8: 1,
    9: 2,
    10: 3,
    11: 4,
    12: 5,
    13: 6,
}


def augmentation_change_found(changes_found_dict={}):  # politician_requested_change_found
    status = ""
    # Which kinds of changes are considered VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION
    changes_which_count = \
        [
            'is_ballotpedia_added', 'is_ballotpedia_removed',
            'is_candidate_analysis_done',
            'is_candidate_url_added', 'is_candidate_url_removed',
            'is_facebook_added', 'is_facebook_removed',
            'is_link_to_office_added', 'is_link_to_office_removed',
            'is_linkedin_added', 'is_linkedin_removed',
            'is_politician_analysis_done',
            'is_politician_url_added', 'is_politician_url_removed',
            'is_twitter_handle_added', 'is_twitter_handle_removed',
            'is_wikipedia_added', 'is_wikipedia_removed',
            'is_withdrawal_date_added', 'is_withdrawal_date_removed',
            'is_website_added', 'is_website_removed',
        ]
    # We intentionally do not include 'is_official_statement_added'
    return changes_which_count_found(changes_found_dict=changes_found_dict, changes_which_count=changes_which_count)


def change_tracking(
        existing_value='',
        new_value='',
        changes_found_dict={},
        changes_found_key_base='',
        changes_found_key_name='',
):
    change_description = ''
    change_description_changed = False
    incoming_value_lower_case = new_value.strip().lower() \
        if positive_value_exists(new_value) else ''
    existing_value_lower_case = existing_value.strip().lower() \
        if positive_value_exists(existing_value) else ''
    if positive_value_exists(new_value) and \
            incoming_value_lower_case != existing_value_lower_case:
        change_description += "ADDED: " + changes_found_key_name + " " \
                              + str(new_value) + " "
        change_description_changed = True
        changes_found_dict[changes_found_key_base + '_added'] = True
    elif incoming_value_lower_case != existing_value_lower_case:
        change_description += "REMOVED: " + changes_found_key_name + " " \
                              + str(existing_value) + " "
        change_description_changed = True
        changes_found_dict[changes_found_key_base + '_removed'] = True
    results = {
        'change_description':           change_description,
        'change_description_changed':   change_description_changed,
        'changes_found_dict':           changes_found_dict,
    }
    return results


def change_tracking_boolean(
        existing_value='',
        new_value='',
        changes_found_dict={},
        changes_found_key_base='',
        changes_found_key_name='',
):
    change_description = ''
    change_description_changed = False
    if new_value != existing_value:
        change_description += "BOOL-CHANGED: " + changes_found_key_name + " " + str(new_value) + " "
        change_description_changed = True
        changes_found_dict[changes_found_key_base + '_added'] = True
    results = {
        'change_description':           change_description,
        'change_description_changed':   change_description_changed,
        'changes_found_dict':           changes_found_dict,
    }
    return results


def is_key_in_dict_and_true(dict_to_search={}, key_to_search=''):
    status = ""
    try:
        if key_to_search in dict_to_search:
            return positive_value_exists(dict_to_search[key_to_search])
    except Exception as e:
        status += "FAILED_TO_CHECK_KEY_IN_DICT_AND_TRUE: " + str(e) + " "
    return False


def generate_start_and_end_of_week_date_integer(
        earliest_date_integer=None,
        latest_date_integer=None,
        which_day_is_start_of_week=0):
    status = ""
    success = True
    start_and_end_of_week_date_integer_list = []
    try:
        earliest_date = convert_date_as_integer_to_date(earliest_date_integer)
    except Exception as e:
        earliest_date_integer = 99990101
        earliest_date = convert_date_as_integer_to_date(earliest_date_integer)
        status += "FAILED_TO_CREATE_EARLIEST_DATE-FALLING_BACK_ON_99991231: " + str(e) + " "
    # Roll back to the start of the team's week, of the week containing the earliest_date
    weekday_of_earliest_date = earliest_date.weekday()
    which_day_is_end_of_week = get_end_of_week_weekday_from_start_of_week_weekday(which_day_is_start_of_week)

    offset_to_go_back_to_start_of_week = calculate_distance_back_to_start_of_week_from_weekday(
        weekday_of_earliest_date, end_of_week_weekday=which_day_is_end_of_week)
    if offset_to_go_back_to_start_of_week is False:
        earliest_start_of_week_date = earliest_date
        earliest_start_of_week_integer = 0
        status += "GENERATE_ERROR_RETRIEVING_EARLIEST_START_OF_WEEK_DATE1 "
    else:
        # Roll back to the start of the week, of the week containing the earliest_date
        if offset_to_go_back_to_start_of_week == 0:
            earliest_start_of_week_date = earliest_date
        else:
            earliest_start_of_week_date = \
                earliest_date - timedelta(days=offset_to_go_back_to_start_of_week)
        earliest_start_of_week_integer = convert_date_to_date_as_integer(earliest_start_of_week_date)

    try:
        latest_date = convert_date_as_integer_to_date(latest_date_integer)
    except Exception as e:
        latest_date_integer = 19700201
        latest_date = convert_date_as_integer_to_date(latest_date_integer)
        status += "FAILED_TO_CREATE_LATEST_DATE-FALLING_BACK_ON_19700101: " + str(e) + " "
    # Figure out the last day of the week containing the latest_date
    weekday_of_latest_date = latest_date.weekday()
    which_day_is_end_of_week = get_end_of_week_weekday_from_start_of_week_weekday(which_day_is_start_of_week)
    offset_to_go_forward_to_end_of_week = calculate_distance_forward_to_end_of_week_from_weekday(
        weekday_of_latest_date, end_of_week_weekday=which_day_is_end_of_week)
    if offset_to_go_forward_to_end_of_week is False:
        latest_end_of_week_integer = 0
        status += "GENERATE_ERROR_RETRIEVING_LATEST_END_OF_WEEK_DATE1 "
    else:
        if offset_to_go_forward_to_end_of_week == 0:
            latest_end_of_week_date = latest_date
        else:
            latest_end_of_week_date = latest_date + timedelta(days=offset_to_go_forward_to_end_of_week)
        latest_end_of_week_integer = convert_date_to_date_as_integer(latest_end_of_week_date)

    more_weeks_to_process = earliest_start_of_week_integer < latest_end_of_week_integer
    start_of_week_date_on_stage = earliest_start_of_week_date
    start_of_week_integer_on_stage = earliest_start_of_week_integer
    end_of_week_date_on_stage = start_of_week_date_on_stage + timedelta(days=6)
    end_of_week_integer_on_stage = convert_date_to_date_as_integer(end_of_week_date_on_stage)
    while more_weeks_to_process:
        start_and_end_of_week_dict = {
            'start_of_week_date_integer': start_of_week_integer_on_stage,
            'end_of_week_date_integer': end_of_week_integer_on_stage,
        }
        start_and_end_of_week_date_integer_list.append(start_and_end_of_week_dict)
        start_of_week_date_on_stage = end_of_week_date_on_stage + timedelta(days=1)
        start_of_week_integer_on_stage = convert_date_to_date_as_integer(start_of_week_date_on_stage)
        end_of_week_date_on_stage = start_of_week_date_on_stage + timedelta(days=6)
        end_of_week_integer_on_stage = convert_date_to_date_as_integer(end_of_week_date_on_stage)
        more_weeks_to_process = end_of_week_integer_on_stage <= latest_end_of_week_integer

    results = {
        'earliest_start_of_week_integer':           earliest_start_of_week_integer,
        'latest_end_of_week_integer':               latest_end_of_week_integer,
        'success':                                  success,
        'status':                                   status,
        'start_and_end_of_week_date_integer_list':  start_and_end_of_week_date_integer_list,
    }
    return results


def is_candidate_or_politician_analysis_done(changes_found_dict={}):
    # Which kinds of changes are considered VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION
    changes_which_count = ['is_candidate_analysis_done', 'is_politician_analysis_done']
    return changes_which_count_found(changes_found_dict=changes_found_dict, changes_which_count=changes_which_count)


def photo_change_found(changes_found_dict={}):
    # Which kinds of changes are considered VOLUNTEER_ACTION_POLITICIAN_PHOTO
    changes_which_count = ['is_photo_added', 'is_photo_removed']
    return changes_which_count_found(changes_found_dict=changes_found_dict, changes_which_count=changes_which_count)


def politician_requested_change_found(changes_found_dict={}):
    # Which kinds of changes are considered VOLUNTEER_ACTION_POLITICIAN_REQUEST
    changes_which_count = ['is_official_statement_added', 'is_official_statement_removed']
    return changes_which_count_found(changes_found_dict=changes_found_dict, changes_which_count=changes_which_count)


def changes_which_count_found(changes_found_dict={}, changes_which_count=[]):
    status = ""
    for one_change in changes_which_count:
        try:
            if is_key_in_dict_and_true(dict_to_search=changes_found_dict, key_to_search=one_change):
                return True
        except Exception as e:
            status += "FAILED_TO_CALCULATE_WHICH_COUNT_MATCH: " + str(e) + " "
    return False


def update_or_create_weekly_metrics_one_volunteer(
        end_of_week_date_integer=None,
        start_of_week_date_integer=None,
        volunteer_task_completed_list=None,
        voter=None,
        voter_display_name=None,
        voter_we_vote_id=None,
        which_day_is_end_of_week=6):

    candidates_created = 0                  # VOLUNTEER_ACTION_CANDIDATE_CREATED = 3
    duplicate_politician_analysis = 0       # VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS = 10
    election_retrieve_started = 0           # VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED = 9
    match_candidates_to_politicians = 0     # VOLUNTEER_ACTION_MATCH_CANDIDATES_TO_POLITICIANS = 11
    politicians_augmented = 0               # VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION = 6
    politicians_deduplicated = 0            # VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION = 5
    politicians_photo_added = 0             # VOLUNTEER_ACTION_POLITICIAN_PHOTO = 7
    politicians_requested_changes = 0       # VOLUNTEER_ACTION_POLITICIAN_REQUEST = 8
    position_comments_saved = 0             # VOLUNTEER_ACTION_POSITION_COMMENT_SAVED = 2
    positions_saved = 0                     # VOLUNTEER_ACTION_POSITION_SAVED = 1
    twitter_bulk_retrieve = 0               # VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE = 12
    voter_guide_possibilities_created = 0   # VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED = 4

    volunteer_weekly_metrics = None
    volunteer_weekly_metrics_saved = False
    status = ""
    success = True

    if hasattr(voter, 'we_vote_id'):
        voter_display_name = voter.get_full_name()
        voter_we_vote_id = voter.we_vote_id

    missing_required_variable = False
    if not positive_value_exists(end_of_week_date_integer):
        status += 'MISSING_END_OF_WEEK_DATE_INTEGER '
        missing_required_variable = True
    if not positive_value_exists(start_of_week_date_integer):
        status += 'MISSING_START_OF_WEEK_DATE_INTEGER '
        missing_required_variable = True
    if not positive_value_exists(voter_display_name):
        status += 'MISSING_VOTER_DISPLAY_NAME '
        missing_required_variable = True
    if not positive_value_exists(voter_we_vote_id):
        status += 'MISSING_VOTER_WE_VOTE_ID '
        missing_required_variable = True
    if not which_day_is_end_of_week:
        status += 'MISSING_WEEKDAY '
        missing_required_variable = True

    if missing_required_variable:
        success = False
        results = {
            'success':                          success,
            'status':                           status,
            'volunteer_weekly_metrics_saved':   volunteer_weekly_metrics_saved,
            'volunteer_weekly_metrics':         volunteer_weekly_metrics,
        }
        return results

    # Find all dates (as integer) for Sundays in the volunteer_task_completed_list passed in
    for volunteer_task_completed in volunteer_task_completed_list:
        # Only count entries related to voter_we_vote_id
        if volunteer_task_completed.voter_we_vote_id == voter_we_vote_id:
            # Only process entries between the start_of_week_date_integer and end_of_week_date_integer
            if start_of_week_date_integer <= volunteer_task_completed.date_as_integer <= end_of_week_date_integer:
                if volunteer_task_completed.action_constant == VOLUNTEER_ACTION_CANDIDATE_CREATED:
                    candidates_created += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS:
                    duplicate_politician_analysis += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_ELECTION_RETRIEVE_STARTED:
                    election_retrieve_started += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_MATCH_CANDIDATES_TO_POLITICIANS:
                    match_candidates_to_politicians += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POLITICIAN_AUGMENTATION:
                    politicians_augmented += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION:
                    politicians_deduplicated += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POLITICIAN_PHOTO:
                    politicians_photo_added += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POLITICIAN_REQUEST:
                    politicians_requested_changes += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POSITION_COMMENT_SAVED:
                    position_comments_saved += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POSITION_SAVED:
                    positions_saved += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE:
                    twitter_bulk_retrieve += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED:
                    voter_guide_possibilities_created += 1

    voter_date_unique_string = \
        str(voter_we_vote_id) + "-" + str(end_of_week_date_integer) + "-" + str(which_day_is_end_of_week)
    updates = {
        'candidates_created':                   candidates_created,
        'duplicate_politician_analysis':        duplicate_politician_analysis,
        'election_retrieve_started':            election_retrieve_started,
        'match_candidates_to_politicians':      match_candidates_to_politicians,
        'end_of_week_date_integer':             end_of_week_date_integer,
        'politicians_augmented':                politicians_augmented,
        'politicians_deduplicated':             politicians_deduplicated,
        'politicians_photo_added':              politicians_photo_added,
        'politicians_requested_changes':        politicians_requested_changes,
        'positions_saved':                      positions_saved,
        'position_comments_saved':              position_comments_saved,
        'twitter_bulk_retrieve':                twitter_bulk_retrieve,
        'voter_date_unique_string':             voter_date_unique_string,
        'voter_display_name':                   voter_display_name,
        'voter_guide_possibilities_created':    voter_guide_possibilities_created,
        'voter_we_vote_id':                     voter_we_vote_id,
        'which_day_is_end_of_week':             which_day_is_end_of_week,
    }
    try:
        volunteer_weekly_metrics = VolunteerWeeklyMetrics.objects.using('analytics').update_or_create(
            voter_date_unique_string=voter_date_unique_string,
            defaults=updates,
        )
        volunteer_weekly_metrics_saved = True
        status += 'WEEKLY_METRICS_SAVED '
    except Exception as e:
        success = False
        status += 'COULD_NOT_SAVE_WEEKLY_METRICS: ' + str(e) + ' '

    results = {
        'success':                          success,
        'status':                           status,
        'volunteer_weekly_metrics_saved':   volunteer_weekly_metrics_saved,
        'volunteer_weekly_metrics':         volunteer_weekly_metrics,
    }
    return results


def get_key_from_value(val, my_dict):
    for key, value in my_dict.items():
        if val == value:
            return key
    return 0


def get_start_of_week_weekday_from_end_of_week_weekday(end_of_week_weekday=6):
    return get_key_from_value(end_of_week_weekday, START_AND_END_OF_WEEK_BY_WEEKDAY)


def get_end_of_week_weekday_from_start_of_week_weekday(start_of_week_weekday=0):
    return START_AND_END_OF_WEEK_BY_WEEKDAY[start_of_week_weekday]


def calculate_distance_back_to_start_of_week_from_weekday(weekday_value, end_of_week_weekday=6):
    days_offset = 0
    which_day_is_start_of_week = get_start_of_week_weekday_from_end_of_week_weekday(end_of_week_weekday)
    while days_offset <= 7:
        weekday_to_compare_raw = weekday_value - days_offset
        weekday_to_compare = WEEKDAY_WRAPAROUND_DICT[weekday_to_compare_raw]
        if weekday_to_compare == which_day_is_start_of_week:
            return days_offset
        days_offset += 1
    return False


def calculate_distance_forward_to_end_of_week_from_weekday(weekday_value, end_of_week_weekday=0):
    days_offset = 0
    while days_offset <= 7:
        weekday_to_compare_raw = weekday_value + days_offset
        weekday_to_compare = WEEKDAY_WRAPAROUND_DICT[weekday_to_compare_raw]
        if weekday_to_compare == end_of_week_weekday:
            return days_offset
        days_offset += 1
    return False


def update_weekly_volunteer_metrics(which_day_is_end_of_week=6, recalculate_all=False):
    which_day_is_start_of_week = get_start_of_week_weekday_from_end_of_week_weekday(which_day_is_end_of_week)
    status = ""
    success = True
    task_list = []

    if positive_value_exists(recalculate_all):
        day_before_last_update_date_integer = 20240312  # Hard coded for resetting all statistics for this team
    else:
        # Retrieve the last complete day we processed
        # If we run updates Wed March 13th, 2024, then the date stored is the day before: 20240312 (vs. 20240313)
        day_before_last_update_date_integer = fetch_volunteer_task_weekly_metrics_last_updated()

    try:
        day_before_last_update_date = convert_date_as_integer_to_date(day_before_last_update_date_integer)
        weekday_of_last_update_date = day_before_last_update_date.weekday()
        offset_to_go_back_to_start_of_week = calculate_distance_back_to_start_of_week_from_weekday(
            weekday_of_last_update_date, end_of_week_weekday=which_day_is_end_of_week)
        if offset_to_go_back_to_start_of_week is False:
            earliest_start_of_week_integer = 0
            status += "ERROR_RETRIEVING_EARLIEST_START_OF_WEEK_DATE1 "
        else:
            # Roll back to the start of the week, of the week containing the earliest_date
            if offset_to_go_back_to_start_of_week == which_day_is_end_of_week:
                earliest_start_of_week_date = day_before_last_update_date
            else:
                earliest_start_of_week_date = \
                    day_before_last_update_date - timedelta(days=offset_to_go_back_to_start_of_week)
            earliest_start_of_week_integer = convert_date_to_date_as_integer(earliest_start_of_week_date)
    except Exception as e:
        earliest_start_of_week_integer = 0
        status += "ERROR_RETRIEVING_EARLIEST_START_OF_WEEK_DATE2: " + str(e) + ' '

    try:
        queryset = VolunteerTaskCompleted.objects.using('readonly').all()  # 'analytics'
        # We have to process an entire week of task metrics if we last processed within the week.
        #  Once past the Sunday of a week, we can stop fresh calculations and move onto weeks we haven't processed
        #  completely yet.
        queryset = queryset.filter(date_as_integer__gte=earliest_start_of_week_integer)
        task_list = list(queryset)
    except Exception as e:
        status += "ERROR_RETRIEVING_VOLUNTEER_TASK_COMPLETED_LIST: " + str(e) + ' '
        success = False

    # Break up the results by voter_we_vote_id
    earliest_date_integer = 99991201  # Temp date far in the future, meant to be replaced immediately below
    latest_date_integer = 19700201  # Temp date in the past
    tasks_by_voter_we_vote_id = {}
    voter_we_vote_id_list = []
    for volunteer_task_completed in task_list:
        if volunteer_task_completed.date_as_integer < earliest_date_integer:
            earliest_date_integer = volunteer_task_completed.date_as_integer
        if volunteer_task_completed.date_as_integer > latest_date_integer:
            latest_date_integer = volunteer_task_completed.date_as_integer
        if positive_value_exists(volunteer_task_completed.voter_we_vote_id) and \
                volunteer_task_completed.voter_we_vote_id not in tasks_by_voter_we_vote_id:
            tasks_by_voter_we_vote_id[volunteer_task_completed.voter_we_vote_id] = []
            voter_we_vote_id_list.append(volunteer_task_completed.voter_we_vote_id)
        tasks_by_voter_we_vote_id[volunteer_task_completed.voter_we_vote_id].append(volunteer_task_completed)

    results = generate_start_and_end_of_week_date_integer(
        earliest_date_integer,
        latest_date_integer,
        which_day_is_start_of_week=which_day_is_start_of_week)
    start_and_end_of_week_date_integer_list = results['start_and_end_of_week_date_integer_list']

    voter_list = []
    try:
        queryset = Voter.objects.using('readonly').all()
        queryset = queryset.filter(we_vote_id__in=voter_we_vote_id_list)
        voter_list = list(queryset)
    except Exception as e:
        status += "ERROR_RETRIEVING_VOTER_LIST: " + str(e) + ' '
        success = False

    voter_dict_by_voter_we_vote_id = {}
    for voter in voter_list:
        voter_dict_by_voter_we_vote_id[voter.we_vote_id] = voter

    all_voters_updated_successfully = True
    for voter_we_vote_id in voter_we_vote_id_list:
        voter = voter_dict_by_voter_we_vote_id.get(voter_we_vote_id)
        for start_and_end_of_week_dict in start_and_end_of_week_date_integer_list:
            results = update_or_create_weekly_metrics_one_volunteer(
                end_of_week_date_integer=start_and_end_of_week_dict['end_of_week_date_integer'],
                start_of_week_date_integer=start_and_end_of_week_dict['start_of_week_date_integer'],
                volunteer_task_completed_list=tasks_by_voter_we_vote_id[voter_we_vote_id],
                voter=voter,
                which_day_is_end_of_week=which_day_is_end_of_week,
            )
            if not results['success']:
                all_voters_updated_successfully = False

    # We keep calculating the last week to deal with teams with different end_of_week days
    week_ago_integer = 0
    if all_voters_updated_successfully:
        today = date.today()
        week_ago = today - timedelta(days=7)
        week_ago_integer = convert_date_to_date_as_integer(week_ago)
    if all_voters_updated_successfully and positive_value_exists(week_ago_integer):
        we_vote_settings_manager = WeVoteSettingsManager()
        results = we_vote_settings_manager.save_setting(
            setting_name="volunteer_task_weekly_metrics_last_updated",
            setting_value=week_ago_integer,
            value_type=WeVoteSetting.INTEGER)
        if not results['success']:
            status += results['status']
            success = False

    results = {
        'status':                           status,
        'success':                          success,
    }
    return results
