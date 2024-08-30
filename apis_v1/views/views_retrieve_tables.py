# apis_v1/views/views_ballot.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json

from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.controllers_master import fast_load_status_retrieve, retrieve_sql_tables_as_csv, \
    get_total_row_count
from retrieve_tables.controllers_master import fast_load_status_update
from wevote_functions.functions import get_voter_api_device_id

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def retrieve_sql_tables(request):  # retrieveSQLTables
    """
    Retrieve the SQL tables that would otherwise be synchronized via the "Sync Data with Master We Vote Servers" menu
    :param request:
    :return:
    """
    table_name = request.GET.get('table_name', 'bad_table_param_error')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    voter_api_device_id = get_voter_api_device_id(request)

    # print("retrieveSQLTables voter_api_device_id: ", voter_api_device_id)
    # DALE 2024-08-30 TURNING OFF DUE TO SERVER OVERLOAD
    # json_data = retrieve_sql_tables_as_csv(voter_api_device_id, table_name, start, end)
    status = ''
    status += "Retrieving SQL tables: " + table_name + " " + start + " " + end + "TURNED OFF DUE TO SERVER OVERLOAD "
    json_data = {
        'success': False,
        'status': status,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_sql_tables_row_count(request):  # retrieveSQLTablesRowCount
    json_data = {
        'rowCount': str(get_total_row_count())
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def fast_load_status_retrieve_view(request):   # fastLoadStatusRetrieve
    return fast_load_status_retrieve(request)


def fast_load_status_update_view(request):   # fastLoadStatusUpdate
    return fast_load_status_update(request)
