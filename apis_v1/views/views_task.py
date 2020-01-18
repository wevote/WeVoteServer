# apis_v1/views/views_task.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
import dateutil.parser
import json
import pytz
import requests as python_requests
import subprocess
from django.http import HttpResponse
from background_task import background

from config.base import get_environment_variable, get_environment_variable_default
from scheduled_tasks.models import BackgroundTaskOutputManager
from scheduled_tasks.task_models import WeTask
# from scheduled_tasks.task_models_completed import WeTaskCompleted  # DALE 2020-01-17 To prevent ModuleNotFoundError
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def delete_task(request):           # taskUpdateOne
    tid = request.GET.get('id', '')

    WeTask().delete_task(tid)

    json_data = {
        'status':                   'status',
        'success':                  'success',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def limit_task_history():           # taskUpdateOne
    task_retention_days = get_environment_variable_default("SCHEDULED_TASKS_RETAIN_HISTORY", 90)  #
    success = False
    try:
        task_retention_days_int = int(task_retention_days)
        nowdt = datetime.now(pytz.timezone("America/Los_Angeles"))
        limit_dt = nowdt - timedelta(days=task_retention_days_int)
        # print("task_retention_days: " + str(task_retention_days))

        BackgroundTaskOutputManager().delete_older_tasks(limit_dt=limit_dt)
        # WeTaskCompleted().delete_older_tasks(limit_dt=limit_dt)  # DALE 2020-01-17 To prevent ModuleNotFoundError

        success = True
    except Exception as e:
        logger.error("limit_task_history threw: " + str(e))

    return success


def save_new_task(request):         # taskSaveNew
    task_parameters = request.GET.get('task_parameters', '')
    verbose_name = request.GET.get('verbose_task_name', '')
    priority = request.GET.get('priority', '')
    run_at = request.GET.get('run_at', '')
    repeat = calculate_repeat(request.GET.get('repeat', ''))
    repeat_until = request.GET.get('repeat_until', '')
    run_at_dt = dateutil.parser.parse(run_at)
    repeat_until_dt = dateutil.parser.parse(repeat_until)

    if task_parameters.startswith('https://') or task_parameters.startswith('htts://'):
        we_task_http(task_parameters=task_parameters, verbose_name=verbose_name, schedule=run_at_dt,
                     priority=priority, repeat=repeat, repeat_until=repeat_until_dt)
    else:
        we_task(task_parameters=task_parameters, verbose_name=verbose_name, schedule=run_at_dt,
                priority=priority, repeat=repeat, repeat_until=repeat_until_dt)

    json_data = {
        'status':                   'status',
        'success':                  'success',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def calculate_repeat(repeat):
    if repeat in {'HOURLY', 'DAILY', 'WEEKLY', 'EVERY_2_WEEKS', 'EVERY_4_WEEKS', 'NEVER'}:
        if repeat == 'HOURLY':
            return 3600
        elif repeat == 'DAILY':
            return 3600*24
        elif repeat == 'WEEKLY':
            return 3600*24*7
        elif repeat == 'EVERY_2_WEEKS':
            return 3600*24*7*2
        elif repeat == 'EVERY_4_WEEKS':
            return 3600*24*7*4
    return 0


def get_repeat_string(repeat):
    if repeat == 3600:
        return 'HOURLY'
    elif repeat == 3600*24:
        return 'DAILY'
    elif repeat == 3600*24*7:
        return 'WEEKLY'
    elif repeat == 3600*24*7*2:
        return 'EVERY_2_WEEKS'
    elif repeat == 3600*24*7*4:
        return 'EVERY_4_WEEKS'
    else:
        return 'NONE'


def insert_output_record(task_parameters, nowdt, output_text):
    # DALE 2020-01-17 To prevent ModuleNotFoundError
    # tlist = WeTaskCompleted().raw_list(limit=1)
    # # print("WeTaskCompleted.raw_list: " + str(tlist[0].id))
    #
    # BackgroundTaskOutputManager.create_output_entry(tlist[0].id, date_output_completed=nowdt, output_text=output_text)

    success = False
    return success


def read_output_record(request):
    tid = request.GET.get('id', '')

    tlist = BackgroundTaskOutputManager.retrieve_background_task_output_with_completed_id(tid)

    text = ""
    try:
        text = tlist[0].output_text
    except Exception as e:
        logger.error("read_output_record threw: " + str(e))

    json_data = {
        'data':                   text,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


@background()
def we_task(task_parameters, verbose_name="", schedule='', name=''):  # pep8 parsing is wrong, these are required
    # print("We_task parms: " + task_parameters)
    bits = task_parameters.split(" ")
    p1 = subprocess.Popen(bits, stdout=subprocess.PIPE)
    output = p1.communicate()[0]

    nowdt = datetime.now(pytz.timezone("America/Los_Angeles"))
    output_string = nowdt.isoformat() + "--" + task_parameters + "--" + output.decode("utf-8")
    output_string = output_string.replace('\n', '<br/>')
    # print(output_string)

    insert_output_record(task_parameters, nowdt, output_string)
    limit_task_history()

@background()
def we_task_http(task_parameters, verbose_name="", schedule='', name=''):  # pep8 parsing is wrong, these are required
    # print("We_task HTTP parms: " + task_parameters)
    r = python_requests.get(task_parameters)
    output = r.text
    # print("r.text  ", r.text)
    nowdt = datetime.now(pytz.timezone("America/Los_Angeles"))
    output_string = nowdt.isoformat() + "--" + task_parameters + "--<br/>" + output
    output_string = output_string.replace('\n', '<br/>')
    # print(output_string)

    insert_output_record(task_parameters, nowdt, output_string)
    limit_task_history()


def run_task_immediately(request):  # taskRunImmediately
    json_data = {
        'status':                   'status',
        'success':                  'success',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')

