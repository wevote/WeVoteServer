# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
from datetime import datetime, timedelta

import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render

from admin_tools.views import redirect_to_sign_in_page
from volunteer_task.models import VolunteerWeeklyMetrics
from voter.models import voter_has_authority, VoterManager
from wevote_functions.functions import positive_value_exists
from .controllers import update_weekly_volunteer_metrics


@login_required
def performance_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    assigned_to_voter_we_vote_id = request.GET.get('assigned_to_voter_we_vote_id', False)
    status = ""
    success = True

    results = update_weekly_volunteer_metrics()

    performance_list = []
    # one_person_one_week_dict = {
    #     'end_of_week_date_integer': 20240302,
    #     'voter_display_name': 'Michael G',
    #     'voter_we_vote_id': '',
    #     'positions_saved': 12,
    #     'position_comments_saved': 3,
    # }
    # performance_list.append(one_person_one_week_dict)
    # one_person_one_week_dict = {
    #     'end_of_week_date_integer': 20240309,
    #     'voter_display_name': 'Michael G',
    #     'voter_we_vote_id': '',
    #     'positions_saved': 8,
    #     'position_comments_saved': 5,
    # }
    # performance_list.append(one_person_one_week_dict)
    # one_person_one_week_dict = {
    #     'end_of_week_date_integer': 20240309,
    #     'voter_display_name': 'Dale McGrew',
    #     'voter_we_vote_id': '',
    #     'positions_saved': 10,
    #     'position_comments_saved': 0,
    # }
    # performance_list.append(one_person_one_week_dict)
    try:
        queryset = VolunteerWeeklyMetrics.objects.using('readonly').all()  # 'analytics'
        # queryset = queryset.filter(we_vote_id__in=campaignx_we_vote_id_list)
        performance_list = list(queryset)
    except Exception as e:
        status += "ERROR_RETRIEVING_VOLUNTEER_TASK_COMPLETED_LIST: " + str(e) + ' '
        success = False

    actions_completed_dict = {}
    end_of_week_date_integer_list = []
    performance_display_dict = {}
    voter_display_name_list = []
    for one_person_one_week in performance_list:
        if one_person_one_week.end_of_week_date_integer not in end_of_week_date_integer_list:
            end_of_week_date_integer_list.append(one_person_one_week.end_of_week_date_integer)
        end_of_week_date_integer = one_person_one_week.end_of_week_date_integer
        voter_display_name = one_person_one_week.voter_display_name
        if voter_display_name not in actions_completed_dict:
            actions_completed_dict[voter_display_name] = {}
        if voter_display_name not in performance_display_dict:
            performance_display_dict[voter_display_name] = {}
        if voter_display_name not in voter_display_name_list:
            voter_display_name_list.append(voter_display_name)
        if end_of_week_date_integer not in actions_completed_dict[voter_display_name]:
            actions_completed_dict[voter_display_name][end_of_week_date_integer] = {
                'candidates_created': one_person_one_week.candidates_created,
                'positions_saved': one_person_one_week.positions_saved,
                'position_comments_saved': one_person_one_week.position_comments_saved,
                'voter_guide_possibilities_created': one_person_one_week.voter_guide_possibilities_created,
            }

    for voter_display_name in voter_display_name_list:
        # Set these values to true if we have any tasks completed in any of the weeks we are displaying
        performance_display_dict[voter_display_name]['candidates_created'] = 0
        performance_display_dict[voter_display_name]['positions_saved'] = 0
        performance_display_dict[voter_display_name]['position_comments_saved'] = 0
        performance_display_dict[voter_display_name]['voter_guide_possibilities_created'] = 0
        performance_display_dict[voter_display_name]['volunteer_task_total'] = 0
        for end_of_week_date_integer in end_of_week_date_integer_list:
            if end_of_week_date_integer in actions_completed_dict[voter_display_name]:
                candidates_created = \
                    actions_completed_dict[voter_display_name][end_of_week_date_integer]['candidates_created']
                positions_saved = \
                    actions_completed_dict[voter_display_name][end_of_week_date_integer]['positions_saved']
                position_comments_saved = \
                    actions_completed_dict[voter_display_name][end_of_week_date_integer]['position_comments_saved']
                voter_guide_possibilities_created = \
                    actions_completed_dict[voter_display_name][end_of_week_date_integer]['voter_guide_possibilities_created']
            else:
                candidates_created
                positions_saved = 0
                position_comments_saved = 0
                voter_guide_possibilities_created = 0
            performance_display_dict[voter_display_name][end_of_week_date_integer] = {
                'candidates_created': candidates_created,
                'positions_saved': positions_saved,
                'position_comments_saved': position_comments_saved,
                'voter_guide_possibilities_created': voter_guide_possibilities_created,
            }

            if candidates_created > 0:
                performance_display_dict[voter_display_name]['candidates_created'] += candidates_created
                performance_display_dict[voter_display_name]['volunteer_task_total'] += candidates_created
            if positions_saved > 0:
                performance_display_dict[voter_display_name]['positions_saved'] += positions_saved
                performance_display_dict[voter_display_name]['volunteer_task_total'] += positions_saved
            if position_comments_saved > 0:
                performance_display_dict[voter_display_name]['position_comments_saved'] += position_comments_saved
                performance_display_dict[voter_display_name]['volunteer_task_total'] += position_comments_saved
            if voter_guide_possibilities_created > 0:
                performance_display_dict[voter_display_name]['voter_guide_possibilities_created'] += \
                    voter_guide_possibilities_created
                performance_display_dict[voter_display_name]['volunteer_task_total'] += \
                    voter_guide_possibilities_created

    messages_on_stage = get_messages(request)
    template_values = {
        'end_of_week_date_integer_list':    end_of_week_date_integer_list,
        'messages_on_stage':        messages_on_stage,
        'performance_display_dict': performance_display_dict,
        'performance_list':         performance_list,
        'voter_display_name_list':  voter_display_name_list,
    }
    return render(request, 'volunteer_task/performance_list.html', template_values)
