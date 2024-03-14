# volunteer_task/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import date, timedelta
from volunteer_task.models import VOLUNTEER_ACTION_CANDIDATE_CREATED, VOLUNTEER_ACTION_POSITION_COMMENT_SAVED, \
    VOLUNTEER_ACTION_POSITION_SAVED, VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED, VolunteerTaskCompleted, \
    VolunteerWeeklyMetrics
from voter.models import Voter
from wevote_functions.functions import convert_date_as_integer_to_date, convert_date_to_date_as_integer, \
    positive_value_exists
from wevote_settings.models import fetch_volunteer_task_weekly_metrics_last_updated, WeVoteSetting, \
    WeVoteSettingsManager


def generate_start_and_end_of_week_date_integer(earliest_date_integer=None, latest_date_integer=None):
    status = ""
    success = True
    start_and_end_of_week_date_integer_list = []
    earliest_date = convert_date_as_integer_to_date(earliest_date_integer)
    # Roll back to the Monday, of the week containing the earliest_date
    weekday_of_earliest_date = earliest_date.weekday()
    if weekday_of_earliest_date == 0:
        earliest_monday_date = earliest_date
    else:
        earliest_monday_date = earliest_date - timedelta(days=weekday_of_earliest_date)
    earliest_monday_integer = convert_date_to_date_as_integer(earliest_monday_date)

    latest_date = convert_date_as_integer_to_date(latest_date_integer)
    # Figure out the Sunday of the week containing the latest_date
    weekday_of_latest_date = latest_date.weekday()
    if weekday_of_latest_date == 6:
        latest_sunday_date = latest_date
    else:
        days_to_add = 6 - weekday_of_latest_date
        latest_sunday_date = latest_date + timedelta(days=days_to_add)
    latest_sunday_integer = convert_date_to_date_as_integer(latest_sunday_date)

    more_weeks_to_process = earliest_monday_integer < latest_sunday_integer
    monday_date_on_stage = earliest_monday_date
    monday_integer_on_stage = earliest_monday_integer
    sunday_date_on_stage = monday_date_on_stage + timedelta(days=6)
    sunday_integer_on_stage = convert_date_to_date_as_integer(sunday_date_on_stage)
    while more_weeks_to_process:
        start_and_end_of_week_dict = {
            'start_of_week_date_integer': monday_integer_on_stage,
            'end_of_week_date_integer': sunday_integer_on_stage,
        }
        start_and_end_of_week_date_integer_list.append(start_and_end_of_week_dict)
        monday_date_on_stage = sunday_date_on_stage + timedelta(days=1)
        monday_integer_on_stage = convert_date_to_date_as_integer(monday_date_on_stage)
        sunday_date_on_stage = monday_date_on_stage + timedelta(days=6)
        sunday_integer_on_stage = convert_date_to_date_as_integer(sunday_date_on_stage)
        more_weeks_to_process = sunday_integer_on_stage <= latest_sunday_integer

    results = {
        'earliest_monday_integer':                  earliest_monday_integer,
        'latest_sunday_integer':                    latest_sunday_integer,
        'success':                                  success,
        'status':                                   status,
        'start_and_end_of_week_date_integer_list':  start_and_end_of_week_date_integer_list,
    }
    return results


def update_or_create_weekly_metrics_one_volunteer(
        end_of_week_date_integer=None,
        start_of_week_date_integer=None,
        volunteer_task_completed_list=None,
        voter=None,
        voter_display_name=None,
        voter_we_vote_id=None):
    candidates_created = 0
    positions_saved = 0
    position_comments_saved = 0
    volunteer_weekly_metrics = None
    volunteer_weekly_metrics_saved = False
    voter_guide_possibilities_created = 0
    status = ""
    success = False

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

    if missing_required_variable:
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
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POSITION_COMMENT_SAVED:
                    position_comments_saved += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_POSITION_SAVED:
                    positions_saved += 1
                elif volunteer_task_completed.action_constant == VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED:
                    voter_guide_possibilities_created += 1

    voter_date_unique_string = str(voter_we_vote_id) + "-" + str(end_of_week_date_integer)
    updates = {
        'candidates_created':                   candidates_created,
        'end_of_week_date_integer':             end_of_week_date_integer,
        'positions_saved':                      positions_saved,
        'position_comments_saved':              position_comments_saved,
        'voter_date_unique_string':             voter_date_unique_string,
        'voter_display_name':                   voter_display_name,
        'voter_guide_possibilities_created':    voter_guide_possibilities_created,
        'voter_we_vote_id':                     voter_we_vote_id,
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


def update_weekly_volunteer_metrics():
    end_date_integer = 0
    status = ""
    success = True
    task_list = []

    # Retrieve the last complete day we processed
    # If we run updates Wed March 13th, 2024, then the date stored is yesterday: 20240312
    weekly_metrics_last_updated_date_integer = fetch_volunteer_task_weekly_metrics_last_updated()

    try:
        queryset = VolunteerTaskCompleted.objects.using('readonly').all()  # 'analytics'
        # queryset = queryset.filter(we_vote_id__in=campaignx_we_vote_id_list)
        task_list = list(queryset)
        if len(task_list):
            task_list_found = True
    except Exception as e:
        status += "ERROR_RETRIEVING_VOLUNTEER_TASK_COMPLETED_LIST: " + str(e) + ' '
        success = False

    # Break up the results by voter_we_vote_id
    earliest_date_integer = 99991231  # Temp date far in the future, meant to be replaced immediately below
    latest_date_integer = 0
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

    results = generate_start_and_end_of_week_date_integer(earliest_date_integer, latest_date_integer)
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

    for voter_we_vote_id in voter_we_vote_id_list:
        voter = voter_dict_by_voter_we_vote_id.get(voter_we_vote_id)
        for start_and_end_of_week_dict in start_and_end_of_week_date_integer_list:
            results = update_or_create_weekly_metrics_one_volunteer(
                end_of_week_date_integer=start_and_end_of_week_dict['end_of_week_date_integer'],
                start_of_week_date_integer=start_and_end_of_week_dict['start_of_week_date_integer'],
                volunteer_task_completed_list=tasks_by_voter_we_vote_id[voter_we_vote_id],
                voter=voter,
            )

    if success and positive_value_exists(end_date_integer):
        we_vote_settings_manager = WeVoteSettingsManager()
        results = we_vote_settings_manager.save_setting(
            setting_name="volunteer_task_weekly_metrics_last_updated",
            setting_value=end_date_integer,
            value_type=WeVoteSetting.INTEGER)
        if not results['success']:
            status += results['status']
            success = False

    results = {
        'status':                           status,
        'success':                          success,
    }
    return results
