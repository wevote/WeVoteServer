# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from admin_tools.views import redirect_to_sign_in_page
from datetime import date, timedelta
from volunteer_task.models import VolunteerWeeklyMetrics
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_functions.functions_date import convert_date_to_date_as_integer
from .controllers import update_weekly_volunteer_metrics
from .models import VolunteerTeam, VolunteerTeamMember

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


@csrf_exempt
@login_required
def performance_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'analytics_admin', 'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    success = True
    team_we_vote_id = request.GET.get('team_we_vote_id', False)
    recalculate_all = request.GET.get('recalculate_all', False)

    volunteer_team_member_list = []
    voter_we_vote_id_list = []
    volunteer_team_name = ''
    which_day_is_end_of_week = 6  # Monday is 0 and Sunday is 6
    which_day_is_end_of_week_display = WEEKDAYS[which_day_is_end_of_week]
    if positive_value_exists(team_we_vote_id):
        try:
            volunteer_team = VolunteerTeam.objects.get(we_vote_id=team_we_vote_id)
            volunteer_team_name = volunteer_team.team_name
            which_day_is_end_of_week = volunteer_team.which_day_is_end_of_week
            which_day_is_end_of_week_display = WEEKDAYS[which_day_is_end_of_week]
        except Exception as e:
            status += "ERROR_FIND_VOLUNTEER_TEAM: " + str(e) + " "

        try:
            queryset = VolunteerTeamMember.objects.using('readonly').all()
            queryset = queryset.filter(team_we_vote_id=team_we_vote_id)
            # Get the voter objects
            volunteer_team_member_list = list(queryset)
            # Just get the voter_we_vote_id's
            queryset_flat = queryset.values_list('voter_we_vote_id', flat=True).distinct()
            voter_we_vote_id_list = list(queryset_flat)
        except Exception as e:
            status += "ERROR_FIND_VOLUNTEER_TEAM_MEMBERS: " + str(e) + " "

    results = update_weekly_volunteer_metrics(
        which_day_is_end_of_week=which_day_is_end_of_week,
        recalculate_all=recalculate_all)

    # earliest_for_display_date_integer = 20240410
    today = date.today()
    earliest_for_display_date = today - timedelta(days=35)
    earliest_for_display_date_integer = convert_date_to_date_as_integer(earliest_for_display_date)

    performance_list = []
    try:
        queryset = VolunteerWeeklyMetrics.objects.using('readonly').all()  # 'analytics'
        # We store summaries for the last 7 days, so we can have the deadline be different team-by-team
        queryset = queryset.filter(which_day_is_end_of_week=which_day_is_end_of_week)
        if positive_value_exists(earliest_for_display_date_integer):
            queryset = queryset.filter(end_of_week_date_integer__gte=earliest_for_display_date_integer)
        if positive_value_exists(team_we_vote_id):
            queryset = queryset.filter(voter_we_vote_id__in=voter_we_vote_id_list)
        performance_list = list(queryset)
    except Exception as e:
        status += "ERROR_RETRIEVING_VOLUNTEER_TASK_COMPLETED_LIST: " + str(e) + ' '
        success = False

    actions_completed_dict = {}
    end_of_week_date_integer_list = []
    individual_performance_dict = {}
    team_actions_completed_dict = {}
    team_performance_dict = {}
    voter_display_name_by_voter_we_vote_id_dict = {}
    voter_we_vote_id_list = []

    for one_person_one_week in performance_list:
        if one_person_one_week.end_of_week_date_integer not in end_of_week_date_integer_list:
            end_of_week_date_integer_list.append(one_person_one_week.end_of_week_date_integer)
        end_of_week_date_integer = one_person_one_week.end_of_week_date_integer
        voter_we_vote_id = one_person_one_week.voter_we_vote_id
        voter_display_name = one_person_one_week.voter_display_name
        voter_display_name_by_voter_we_vote_id_dict[voter_we_vote_id] = voter_display_name
        if voter_we_vote_id not in actions_completed_dict:
            actions_completed_dict[voter_we_vote_id] = {}
        if voter_we_vote_id not in individual_performance_dict:
            individual_performance_dict[voter_we_vote_id] = {}
        if voter_we_vote_id not in voter_we_vote_id_list:
            voter_we_vote_id_list.append(voter_we_vote_id)
        if end_of_week_date_integer not in actions_completed_dict[voter_we_vote_id]:
            actions_completed_dict[voter_we_vote_id][end_of_week_date_integer] = {
                'candidates_created': one_person_one_week.candidates_created,
                'duplicate_politician_analysis': one_person_one_week.duplicate_politician_analysis,
                'election_retrieve_started': one_person_one_week.election_retrieve_started,
                'match_candidates_to_politicians': one_person_one_week.match_candidates_to_politicians,
                'politicians_augmented': one_person_one_week.politicians_augmented,
                'politicians_deduplicated': one_person_one_week.politicians_deduplicated,
                'politicians_photo_added': one_person_one_week.politicians_photo_added,
                'politicians_requested_changes': one_person_one_week.politicians_requested_changes,
                'positions_saved': one_person_one_week.positions_saved,
                'position_comments_saved': one_person_one_week.position_comments_saved,
                'twitter_bulk_retrieve': one_person_one_week.twitter_bulk_retrieve,
                'voter_guide_possibilities_created': one_person_one_week.voter_guide_possibilities_created,
            }
        if end_of_week_date_integer not in team_actions_completed_dict:
            team_actions_completed_dict[end_of_week_date_integer] = {
                'candidates_created': 0,
                'duplicate_politician_analysis': 0,
                'election_retrieve_started': 0,
                'match_candidates_to_politicians': 0,
                'politicians_augmented': 0,
                'politicians_deduplicated': 0,
                'politicians_photo_added': 0,
                'politicians_requested_changes': 0,
                'positions_saved': 0,
                'position_comments_saved': 0,
                'twitter_bulk_retrieve': 0,
                'voter_guide_possibilities_created': 0,
            }
        team_actions_completed_dict[end_of_week_date_integer] = {
            'candidates_created':
                team_actions_completed_dict[end_of_week_date_integer]['candidates_created'] +
                one_person_one_week.candidates_created,
            'duplicate_politician_analysis':
                team_actions_completed_dict[end_of_week_date_integer]['duplicate_politician_analysis'] +
                one_person_one_week.duplicate_politician_analysis,
            'election_retrieve_started':
                team_actions_completed_dict[end_of_week_date_integer]['election_retrieve_started'] +
                one_person_one_week.election_retrieve_started,
            'match_candidates_to_politicians':
                team_actions_completed_dict[end_of_week_date_integer]['match_candidates_to_politicians'] +
                one_person_one_week.match_candidates_to_politicians,
            'politicians_augmented':
                team_actions_completed_dict[end_of_week_date_integer]['politicians_augmented'] +
                one_person_one_week.politicians_augmented,
            'politicians_deduplicated':
                team_actions_completed_dict[end_of_week_date_integer]['politicians_deduplicated'] +
                one_person_one_week.politicians_deduplicated,
            'politicians_photo_added':
                team_actions_completed_dict[end_of_week_date_integer]['politicians_photo_added'] +
                one_person_one_week.politicians_photo_added,
            'politicians_requested_changes':
                team_actions_completed_dict[end_of_week_date_integer]['politicians_requested_changes'] +
                one_person_one_week.politicians_requested_changes,
            'positions_saved':
                team_actions_completed_dict[end_of_week_date_integer]['positions_saved'] +
                one_person_one_week.positions_saved,
            'position_comments_saved':
                team_actions_completed_dict[end_of_week_date_integer]['position_comments_saved'] +
                one_person_one_week.position_comments_saved,
            'twitter_bulk_retrieve':
                team_actions_completed_dict[end_of_week_date_integer]['twitter_bulk_retrieve'] +
                one_person_one_week.twitter_bulk_retrieve,
            'voter_guide_possibilities_created':
                team_actions_completed_dict[end_of_week_date_integer]['voter_guide_possibilities_created'] +
                one_person_one_week.voter_guide_possibilities_created,
        }

    end_of_week_date_integer_list = sorted(end_of_week_date_integer_list)

    # ########################################
    # Work on individual Volunteer statistics
    weekly_metrics_fields = [
        'candidates_created', 'duplicate_politician_analysis', 'election_retrieve_started',
        'match_candidates_to_politicians', 'politicians_augmented', 'politicians_deduplicated',
        'politicians_photo_added', 'politicians_requested_changes', 'positions_saved',
        'position_comments_saved', 'twitter_bulk_retrieve', 'voter_guide_possibilities_created',
    ]
    for voter_we_vote_id in voter_we_vote_id_list:
        # Set these values to true if we have any tasks completed in any of the weeks we are displaying
        individual_performance_dict[voter_we_vote_id]['voter_display_name'] = \
            voter_display_name_by_voter_we_vote_id_dict[voter_we_vote_id]
        for weekly_metric_key in weekly_metrics_fields:
            individual_performance_dict[voter_we_vote_id][weekly_metric_key] = 0
        individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] = 0
        for end_of_week_date_integer in end_of_week_date_integer_list:
            if end_of_week_date_integer in actions_completed_dict[voter_we_vote_id]:
                candidates_created = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['candidates_created']
                duplicate_politician_analysis = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['duplicate_politician_analysis']
                election_retrieve_started = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['election_retrieve_started']
                match_candidates_to_politicians = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer][
                        'match_candidates_to_politicians']
                politicians_augmented = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['politicians_augmented']
                politicians_deduplicated = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['politicians_deduplicated']
                politicians_photo_added = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['politicians_photo_added']
                politicians_requested_changes = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['politicians_requested_changes']
                positions_saved = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['positions_saved']
                position_comments_saved = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['position_comments_saved']
                twitter_bulk_retrieve = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer]['twitter_bulk_retrieve']
                voter_guide_possibilities_created = \
                    actions_completed_dict[voter_we_vote_id][end_of_week_date_integer][
                        'voter_guide_possibilities_created']
                volunteer_task_total = \
                    candidates_created + duplicate_politician_analysis + election_retrieve_started + \
                    match_candidates_to_politicians + \
                    politicians_augmented + politicians_deduplicated + politicians_photo_added + \
                    politicians_requested_changes + positions_saved + position_comments_saved + \
                    twitter_bulk_retrieve + voter_guide_possibilities_created
            else:
                candidates_created = 0
                duplicate_politician_analysis = 0
                election_retrieve_started = 0
                match_candidates_to_politicians = 0
                politicians_augmented = 0
                politicians_deduplicated = 0
                politicians_photo_added = 0
                politicians_requested_changes = 0
                positions_saved = 0
                position_comments_saved = 0
                twitter_bulk_retrieve = 0
                voter_guide_possibilities_created = 0
                volunteer_task_total = 0
            individual_performance_dict[voter_we_vote_id][end_of_week_date_integer] = {
                'candidates_created': candidates_created,
                'duplicate_politician_analysis': duplicate_politician_analysis,
                'election_retrieve_started': election_retrieve_started,
                'match_candidates_to_politicians': match_candidates_to_politicians,
                'politicians_augmented': politicians_augmented,
                'politicians_deduplicated': politicians_deduplicated,
                'politicians_photo_added': politicians_photo_added,
                'politicians_requested_changes': politicians_requested_changes,
                'positions_saved': positions_saved,
                'position_comments_saved': position_comments_saved,
                'twitter_bulk_retrieve': twitter_bulk_retrieve,
                'volunteer_task_total': volunteer_task_total,
                'voter_guide_possibilities_created': voter_guide_possibilities_created,
            }

            if candidates_created > 0:
                individual_performance_dict[voter_we_vote_id]['candidates_created'] += candidates_created
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += candidates_created
            if duplicate_politician_analysis > 0:
                individual_performance_dict[voter_we_vote_id]['duplicate_politician_analysis'] += \
                    duplicate_politician_analysis
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += duplicate_politician_analysis
            if election_retrieve_started > 0:
                individual_performance_dict[voter_we_vote_id]['election_retrieve_started'] += election_retrieve_started
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += election_retrieve_started
            if match_candidates_to_politicians > 0:
                individual_performance_dict[voter_we_vote_id]['match_candidates_to_politicians'] += \
                    match_candidates_to_politicians
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += match_candidates_to_politicians
            if politicians_augmented > 0:
                individual_performance_dict[voter_we_vote_id]['politicians_augmented'] += politicians_augmented
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += politicians_augmented
            if politicians_deduplicated > 0:
                individual_performance_dict[voter_we_vote_id]['politicians_deduplicated'] += politicians_deduplicated
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += politicians_deduplicated
            if politicians_photo_added > 0:
                individual_performance_dict[voter_we_vote_id]['politicians_photo_added'] += politicians_photo_added
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += politicians_photo_added
            if politicians_requested_changes > 0:
                individual_performance_dict[voter_we_vote_id]['politicians_requested_changes'] += \
                    politicians_requested_changes
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += politicians_requested_changes
            if positions_saved > 0:
                individual_performance_dict[voter_we_vote_id]['positions_saved'] += positions_saved
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += positions_saved
            if position_comments_saved > 0:
                individual_performance_dict[voter_we_vote_id]['position_comments_saved'] += position_comments_saved
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += position_comments_saved
            if twitter_bulk_retrieve > 0:
                individual_performance_dict[voter_we_vote_id]['twitter_bulk_retrieve'] += twitter_bulk_retrieve
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += twitter_bulk_retrieve
            if voter_guide_possibilities_created > 0:
                individual_performance_dict[voter_we_vote_id]['voter_guide_possibilities_created'] += \
                    voter_guide_possibilities_created
                individual_performance_dict[voter_we_vote_id]['volunteer_task_total'] += \
                    voter_guide_possibilities_created

    try:
        voter_we_vote_id_list_modified = \
            sorted(voter_we_vote_id_list,
                   key=lambda x: (-convert_to_int(individual_performance_dict[x]['volunteer_task_total'])))
    except Exception as e:
        voter_we_vote_id_list_modified = voter_we_vote_id_list

    # ############################
    # Now work on Team statistics
    team_performance_dict['team_name'] = volunteer_team_name
    team_performance_dict['which_day_is_end_of_week_display'] = which_day_is_end_of_week_display

    # Below, set these values to true if we have any tasks completed in any of the weeks we are displaying
    for weekly_metric_key in weekly_metrics_fields:
        team_performance_dict[weekly_metric_key] = 0
    team_performance_dict['volunteer_task_total'] = 0
    for end_of_week_date_integer in end_of_week_date_integer_list:
        if end_of_week_date_integer in team_actions_completed_dict:
            candidates_created = \
                team_actions_completed_dict[end_of_week_date_integer]['candidates_created']
            duplicate_politician_analysis = \
                team_actions_completed_dict[end_of_week_date_integer]['duplicate_politician_analysis']
            election_retrieve_started = \
                team_actions_completed_dict[end_of_week_date_integer]['election_retrieve_started']
            match_candidates_to_politicians = \
                team_actions_completed_dict[end_of_week_date_integer]['match_candidates_to_politicians']
            politicians_augmented = \
                team_actions_completed_dict[end_of_week_date_integer]['politicians_augmented']
            politicians_deduplicated = \
                team_actions_completed_dict[end_of_week_date_integer]['politicians_deduplicated']
            politicians_photo_added = \
                team_actions_completed_dict[end_of_week_date_integer]['politicians_photo_added']
            politicians_requested_changes = \
                team_actions_completed_dict[end_of_week_date_integer]['politicians_requested_changes']
            positions_saved = \
                team_actions_completed_dict[end_of_week_date_integer]['positions_saved']
            position_comments_saved = \
                team_actions_completed_dict[end_of_week_date_integer]['position_comments_saved']
            twitter_bulk_retrieve = \
                team_actions_completed_dict[end_of_week_date_integer]['twitter_bulk_retrieve']
            voter_guide_possibilities_created = \
                team_actions_completed_dict[end_of_week_date_integer]['voter_guide_possibilities_created']
            volunteer_task_total = \
                candidates_created + duplicate_politician_analysis + election_retrieve_started + \
                match_candidates_to_politicians + \
                politicians_augmented + politicians_deduplicated + politicians_photo_added + \
                politicians_requested_changes + positions_saved + position_comments_saved + \
                twitter_bulk_retrieve + voter_guide_possibilities_created
        else:
            candidates_created = 0
            duplicate_politician_analysis = 0
            election_retrieve_started = 0
            match_candidates_to_politicians = 0
            politicians_augmented = 0
            politicians_deduplicated = 0
            politicians_photo_added = 0
            politicians_requested_changes = 0
            positions_saved = 0
            position_comments_saved = 0
            twitter_bulk_retrieve = 0
            voter_guide_possibilities_created = 0
            volunteer_task_total = 0
        team_performance_dict[end_of_week_date_integer] = {
            'candidates_created': candidates_created,
            'duplicate_politician_analysis': duplicate_politician_analysis,
            'election_retrieve_started': election_retrieve_started,
            'match_candidates_to_politicians': match_candidates_to_politicians,
            'politicians_augmented': politicians_augmented,
            'politicians_deduplicated': politicians_deduplicated,
            'politicians_photo_added': politicians_photo_added,
            'politicians_requested_changes': politicians_requested_changes,
            'positions_saved': positions_saved,
            'position_comments_saved': position_comments_saved,
            'twitter_bulk_retrieve': twitter_bulk_retrieve,
            'volunteer_task_total': volunteer_task_total,
            'voter_guide_possibilities_created': voter_guide_possibilities_created,
        }

        if candidates_created > 0:
            team_performance_dict['candidates_created'] += candidates_created
            team_performance_dict['volunteer_task_total'] += candidates_created
        if duplicate_politician_analysis > 0:
            team_performance_dict['duplicate_politician_analysis'] += duplicate_politician_analysis
            team_performance_dict['volunteer_task_total'] += duplicate_politician_analysis
        if election_retrieve_started > 0:
            team_performance_dict['election_retrieve_started'] += election_retrieve_started
            team_performance_dict['volunteer_task_total'] += election_retrieve_started
        if match_candidates_to_politicians > 0:
            team_performance_dict['match_candidates_to_politicians'] += match_candidates_to_politicians
            team_performance_dict['volunteer_task_total'] += match_candidates_to_politicians
        if politicians_augmented > 0:
            team_performance_dict['politicians_augmented'] += politicians_augmented
            team_performance_dict['volunteer_task_total'] += politicians_augmented
        if politicians_deduplicated > 0:
            team_performance_dict['politicians_deduplicated'] += politicians_deduplicated
            team_performance_dict['volunteer_task_total'] += politicians_deduplicated
        if politicians_photo_added > 0:
            team_performance_dict['politicians_photo_added'] += politicians_photo_added
            team_performance_dict['volunteer_task_total'] += politicians_photo_added
        if politicians_requested_changes > 0:
            team_performance_dict['politicians_requested_changes'] += politicians_requested_changes
            team_performance_dict['volunteer_task_total'] += politicians_requested_changes
        if positions_saved > 0:
            team_performance_dict['positions_saved'] += positions_saved
            team_performance_dict['volunteer_task_total'] += positions_saved
        if position_comments_saved > 0:
            team_performance_dict['position_comments_saved'] += position_comments_saved
            team_performance_dict['volunteer_task_total'] += position_comments_saved
        if twitter_bulk_retrieve > 0:
            team_performance_dict['twitter_bulk_retrieve'] += twitter_bulk_retrieve
            team_performance_dict['volunteer_task_total'] += twitter_bulk_retrieve
        if voter_guide_possibilities_created > 0:
            team_performance_dict['voter_guide_possibilities_created'] += \
                voter_guide_possibilities_created
            team_performance_dict['volunteer_task_total'] += \
                voter_guide_possibilities_created

    volunteer_team_list = []
    try:
        queryset = VolunteerTeam.objects.using('readonly').all().order_by('team_name')
        volunteer_team_list = list(queryset)
    except Exception as e:
        message = "COULD_NOT_GET_VOLUNTEER_TEAM_LIST: " + str(e) + " "
        messages.add_message(request, messages.ERROR, message)

    messages_on_stage = get_messages(request)
    template_values = {
        'end_of_week_date_integer_list':    end_of_week_date_integer_list,
        'messages_on_stage':                messages_on_stage,
        'individual_performance_dict':      individual_performance_dict,
        'performance_list':                 performance_list,
        'team_performance_dict':            team_performance_dict,
        'team_we_vote_id':                  team_we_vote_id,
        'volunteer_team_list':              volunteer_team_list,
        'volunteer_team_member_list':       volunteer_team_member_list,
        'voter_we_vote_id_list':            voter_we_vote_id_list_modified,
    }
    return render(request, 'volunteer_task/performance_list.html', template_values)
