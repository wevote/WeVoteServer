# apis_v1/views/views_ballot.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json

from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.controllers import retrieve_sql_tables_as_csv, fast_load_status_retrieve, get_total_row_count
from wevote_functions.functions import get_voter_device_id

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def retrieve_sql_tables(request):  # retrieveSQLTables
    """
    Retrieve the SQL tables that would otherwise be synchronized via the "Sync Data with Master We Vote Servers" menu
    :param request:
    :return:
    """
    table = request.GET.get('table', 'bad_table_param')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    json_data = retrieve_sql_tables_as_csv(voter_device_id, table, start, end)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_sql_tables_row_count(request):  # retrieveSQLTablesRowCount
    json_data = {
        'rowCount': str(get_total_row_count())
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def fast_load_status_retrieve_view(request):   # fastLoadStatusRetrieve
    return fast_load_status_retrieve(request)