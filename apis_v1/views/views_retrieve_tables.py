# apis_v1/views/views_ballot.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json

from django.http import HttpResponse

import wevote_functions.admin
from config.environment_variable_functions import get_environment_variable
from retrieve_tables.controllers_master import fast_load_status_retrieve, get_max_id, \
    backup_one_table_to_s3_controller, fast_load_table_statistics
from retrieve_tables.controllers_master import fast_load_status_update
from wevote_functions.functions import get_voter_api_device_id
from wevote_tokens.enums import TokenTypes
from wevote_tokens.models.single_use_tokens import Scope
from wevote_tokens.utils import TokensManager

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

@TokensManager(
    token_types=[TokenTypes.SINGLE_USE.value],
    scope=Scope.BACKUP_ONE_TABLE_TO_S3.value,
    expiration_seconds=2700
)
def backup_one_table_to_s3_view(request):  # backupOneTableToS3
    """
    pg_dump one SQL tables on the master server to AWS s3, for use with December 2025 version of fast load
    :param request:
    :return:
    """
    table_name = request.GET.get('table_name', 'bad_table_param_error')
    voter_api_device_id = get_voter_api_device_id(request)
    extended_fastload_logging = request.GET.get('EXTENDED_FASTLOAD_LOGGING', False)

    logger.error(f"Ok: backup_one_table_to_s3 {table_name} -- voter_api_device_id: {voter_api_device_id}")
    json_data = backup_one_table_to_s3_controller(voter_api_device_id, table_name, extended_fastload_logging)
    # logger.error(f"Ok: backup_one_table_to_s3 json_data: {json_data}")

    return HttpResponse(json.dumps(json_data), content_type='application/json')


# def retrieve_sql_tables(request):  # retrieveSQLTables
#     """
#     Retrieve the SQL tables that would otherwise be synchronized via the "Sync Data with Master We Vote Servers" menu
#     :param request:
#     :return:
#     """
#     table_name = request.GET.get('table_name', 'bad_table_param_error')
#     start = request.GET.get('start', '')
#     end = request.GET.get('end', '')
#     voter_api_device_id = get_voter_api_device_id(request)
#
#     print("retrieveSQLTables voter_api_device_id: ", voter_api_device_id)
#     json_data = retrieve_sql_tables_as_csv(voter_api_device_id, table_name, start, end)
#
#     return HttpResponse(json.dumps(json_data), content_type='application/json')


# def retrieve_sql_tables_row_count(request):  # retrieveSQLTablesRowCount
#     json_data = {
#         'rowCount': str(get_total_row_count())
#     }
#     return HttpResponse(json.dumps(json_data), content_type='application/json')
#

def fast_load_status_retrieve_view(request):   # fastLoadStatusRetrieve
    return fast_load_status_retrieve(request)


def fast_load_status_update_view(request):   # fastLoadStatusUpdate
    return fast_load_status_update(request)

def fast_load_table_statistics_view(request):   #
    return fast_load_table_statistics(request)  # similar to getPostgresTableStatistics in weconnect_server


def retrieve_max_id(request):                   # retrieveMaxID
    table_name = request.GET.get('table_name', 'bad_table_param_error')
    json_data = {
        'maxID': get_max_id(table_name)
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
