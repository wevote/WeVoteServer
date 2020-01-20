# scheduled_tasks/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pytz
import re

from admin_tools.views import redirect_to_sign_in_page
from apis_v1.views.views_task import get_repeat_string
from exception.models import print_to_log
from scheduled_tasks.task_models import WeTask
from scheduled_tasks.task_models_completed import WeTaskCompleted
from voter.models import voter_has_authority
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


@login_required
def scheduled_tasks_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    limit = int(request.GET.get('limit', '25'))
    tasks_list_found = False
    tasks = list()
    task_list_completed = list()
    task_list_future = list()

    for task_list_type in ['task_list_future', 'task_list_completed']:
        if task_list_type is 'task_list_future':
            task_list = WeTask().raw_list()
        else:
            task_list = WeTaskCompleted().raw_list(limit=limit)
            task_list = []

        for task in task_list:
            try:
                run_at_dt = task.run_at.astimezone(pytz.timezone("US/Pacific"))  # Display PST/PDST
                nice_run_at = run_at_dt.strftime("%m/%d/%Y %H:%M")
                if type(task.repeat_until) is datetime:
                    repeat_until_dt = task.repeat_until.astimezone(pytz.timezone("US/Pacific"))  # Display PST/PDST
                    nice_repeat_until = repeat_until_dt.strftime("%m/%d/%Y %H:%M")
                else:
                    nice_repeat_until = task.repeat_until
                if type(task.failed_at) is datetime:
                    failed_at_dt = task.failed_at.astimezone(pytz.timezone("US/Pacific"))  # Display PST/PDST
                    nice_failed_at = failed_at_dt.strftime("%m/%d/%Y %H:%M")
                else:
                    nice_failed_at = task.failed_at
            except Exception as e:
                nice_run_at = "format error"
                nice_repeat_until = "format error"
                nice_failed_at = "format error"
            if task.task_params is None:
                task_params = ''
            else:
                m = re.search('(?:.*?task_parameters\": \")(.*?)\"', task.task_params)
                task_params = m.group(1) if m and m.group(1) else ''

            task_dict = {
                'id': task.id,
                'task_name': task.task_name,
                'task_parameters': task_params,
                'verbose_name': task.verbose_name if task.verbose_name else '',
                'priority': task.priority if task.priority else 1,
                'run_at': nice_run_at,
                'repeat': get_repeat_string(task.repeat),
                'repeat_until': nice_repeat_until if nice_repeat_until else '',
                'queue': task.queue if task.queue else '',
                'attempts': task.attempts,
                'failed_at': nice_failed_at if nice_failed_at else '',
                'last_error': task.last_error,
            }
            tasks.append(task_dict)

        if task_list_type is 'task_list_future':
            task_list_future = tasks
            tasks = []
        else:
            task_list_completed = tasks
            tasks = []

    try:
        if len(task_list_future):
            tasks_list_found = True
    except Exception as error_instance:
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        print_to_log(logger=logger, exception_message_optional=status)

    if tasks_list_found:
        template_values = {
            'task_list_future': task_list_future,
            'task_list_completed': task_list_completed,
        }
    else:
        template_values = {}

    return render(request, 'scheduled_tasks/task_list.html', template_values)

