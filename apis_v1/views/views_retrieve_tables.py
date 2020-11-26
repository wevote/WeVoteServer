# apis_v1/views/views_ballot.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from retrieve_tables.controllers import retrieve_sql_tables_as_csv
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def retrieve_sql_tables(request):  # retrieveSQLTables
    """
    Retrieve the SQL tables that would otherwise be synchronized via the "Sync Data with Master We Vote Servers" menu
    :param request:
    :return:
    """
    table = request.GET.get('table', '')
    start = request.GET.get('begin', '')
    end = request.GET.get('end', '')
    json_data = retrieve_sql_tables_as_csv(table, start, end)
    return HttpResponse(json.dumps(json_data), content_type='application/json')

