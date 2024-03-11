# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
from datetime import datetime, timedelta

import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from admin_tools.views import redirect_to_sign_in_page
from voter.models import voter_has_authority, VoterManager


@login_required
def performance_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    assigned_to_voter_we_vote_id = request.GET.get('assigned_to_voter_we_vote_id', False)

    performance_list = []
    one_person_one_week_dict = {
        'end_of_week_date_integer': 20240302,
        'voter_display_name': 'Michael G',
        'voter_we_vote_id': '',
        'positions_saved': 12,
        'positions_written_saved': 3,
    }
    performance_list.append(one_person_one_week_dict)
    one_person_one_week_dict = {
        'end_of_week_date_integer': 20240309,
        'voter_display_name': 'Michael G',
        'voter_we_vote_id': '',
        'positions_saved': 8,
        'positions_written_saved': 5,
    }
    performance_list.append(one_person_one_week_dict)
    one_person_one_week_dict = {
        'end_of_week_date_integer': 20240309,
        'voter_display_name': 'Dale McGrew',
        'voter_we_vote_id': '',
        'positions_saved': 10,
        'positions_written_saved': 0,
    }
    performance_list.append(one_person_one_week_dict)

    actions_completed_dict = {}
    end_of_week_date_integer_list = []
    performance_display_dict = {}
    voter_display_name_list = []
    for one_person_one_week_dict in performance_list:
        if one_person_one_week_dict['end_of_week_date_integer'] not in end_of_week_date_integer_list:
            end_of_week_date_integer_list.append(one_person_one_week_dict['end_of_week_date_integer'])
        end_of_week_date_integer = one_person_one_week_dict['end_of_week_date_integer']
        voter_display_name = one_person_one_week_dict['voter_display_name']
        if voter_display_name not in actions_completed_dict:
            actions_completed_dict[voter_display_name] = {}
        if voter_display_name not in performance_display_dict:
            performance_display_dict[voter_display_name] = {}
        if voter_display_name not in voter_display_name_list:
            voter_display_name_list.append(voter_display_name)
        if end_of_week_date_integer not in actions_completed_dict[voter_display_name]:
            actions_completed_dict[voter_display_name][end_of_week_date_integer] = {
                'positions_saved': one_person_one_week_dict['positions_saved'],
                'positions_written_saved': one_person_one_week_dict['positions_written_saved'],
            }

    for voter_display_name in voter_display_name_list:
        for end_of_week_date_integer in end_of_week_date_integer_list:
            if end_of_week_date_integer in actions_completed_dict[voter_display_name]:
                positions_saved = actions_completed_dict[voter_display_name][end_of_week_date_integer]['positions_saved']
                positions_written_saved = \
                    actions_completed_dict[voter_display_name][end_of_week_date_integer]['positions_written_saved']
            else:
                positions_saved = 0
                positions_written_saved = 0
            performance_display_dict[voter_display_name][end_of_week_date_integer] = {
                'positions_saved': positions_saved,
                'positions_written_saved': positions_written_saved,
            }

    messages_on_stage = get_messages(request)
    template_values = {
        'end_of_week_date_integer_list':    end_of_week_date_integer_list,
        'messages_on_stage':        messages_on_stage,
        'performance_display_dict': performance_display_dict,
        'performance_list':         performance_list,
        'voter_display_name_list':  voter_display_name_list,
    }
    return render(request, 'volunteer_task/performance_list.html', template_values)
