# retrieve_tables/controllers_master.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
from io import StringIO

from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.models import RetrieveTableState
from retrieve_tables.retrieve_common import get_psycopg2_connection, allowable_tables
from wevote_functions.functions import positive_value_exists, convert_to_int, get_voter_api_device_id
from wevote_functions.functions_date import DATE_FORMAT_YMD_HMS

logger = wevote_functions.admin.get_logger(__name__)


dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'


def get_max_id(table_name):
    """
    Returns the maximum id of table to be fetched from the MASTER server
    Runs on the Master server
    :return: the number of rows
    """
    conn = get_psycopg2_connection()
    with conn.cursor() as cursor:
        sql = "SELECT MAX(id) FROM {table_name};".format(table_name=table_name)
        cursor.execute(sql)
        result = cursor.fetchone()
        max_id = result[0]
    conn.close()
    return max_id


def get_total_row_count():
    """
    Returns the total row count of all tables to be fetched from the MASTER server
    Runs on the Master server
    :return: the number of rows
    """
    conn = get_psycopg2_connection()

    rows = 0
    for table_name in allowable_tables:
        with conn.cursor() as cursor:
            sql = "SELECT COUNT(*) FROM {table_name};".format(table_name=table_name)
            cursor.execute(sql)
            row = cursor.fetchone()
            if positive_value_exists(row[0]):
                cnt = int(row[0])
            else:
                cnt = 0
            print('get_total_row_count of table ', table_name, ' is ', cnt)
            rows += cnt

    print('get_total_row_count is ', rows)

    conn.close()
    return rows


# noinspection PyUnusedLocal
def retrieve_sql_tables_as_csv(voter_api_device_id, table_name, start, end):
    """
    Extract one of the approximately 21 allowable database tables to CSV (pipe delimited) and send it to the
    developer's local WeVoteServer instance
    limit is used to specify a number of rows to return (this is the SQL LIMIT clause), non-zero or ignored
    offset is used to specify the first row to return (this is the SQL OFFSET clause), non-zero or ignored
    Note July 2022, re Joe:  This call to `https://api.wevoteusa.org/apis/v1/retrieveSQLTables/` has been moved from a
    "normal" API server (which was timing out) to a "process" API server with an 1800-second timeout.
    """
    t0 = time.time()

    status = ''

    csv_files = {}
    try:
        conn = get_psycopg2_connection()

        # logger.debug("retrieve_sql_tables_as_csv psycopg2 Connected to DB")

        print('retrieve_sql_tables_as_csv "', table_name + '"')
        print('retrieve_sql_tables_as_csv if table_name in allowable_tables ' + str(table_name in allowable_tables))
        if table_name in allowable_tables:
            try:
                cur = conn.cursor()
                file = StringIO()  # Empty file

                # logger.error("experiment: REAL FILE ALLOWED FOR file: " + table_name)
                if positive_value_exists(end):
                    sql = "COPY (SELECT * FROM public." + table_name + " WHERE id BETWEEN " + start + " AND " + \
                          end + " ORDER BY id) TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                else:
                    sql = "COPY " + table_name + " TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                # logger.error("experiment: retrieve_tables sql: " + sql)
                cur.copy_expert(sql, file, size=8192)
                # logger.error("experiment: after cur.copy_expert ")
                file.seek(0)
                # logger.error("experiment: retrieve_tables file contents: " + file.readline().strip())
                file.seek(0)
                csv_files[table_name] = file.read()
                # table_st = csv_files[table_name]
                # for i in range(0, 100000, 150):    # c type for loop for(i=0; i < 10000; i+= 150)
                #     print(table_str[i:i+150])

                file.close()
                # logger.error("experiment: after file close, status " + status)
                if "exported" not in status:
                    status += "exported "
                status += table_name + "(" + start + "," + end + "), "
                # logger.error("experiment: after status +=, " + status)
                # logger.error("experiment: before conn.commit")
                conn.commit()
                # logger.error("experiment: after conn.commit ")
                conn.close()
                # logger.error("experiment: after conn.close ")
                dt = time.time() - t0
                logger.error('Extracting the "' + table_name + '" table took ' + "{:.3f}".format(dt) +
                             ' seconds.  start = ' + start + ', end = ' + end)
            except Exception as e:
                logger.error("Real exception in retrieve_sql_tables_as_csv(): " + str(e) + " ")
        else:
            status = "the table_name '" + table_name + "' is not in the table list, therefore no table was returned"
            logger.error(status)

        # logger.error("experiment: before results")
        results = {
            'success': True,
            'status': status,
            'files': csv_files,
        }

        # logger.error("experiment: results returned")
        return results

    # run `pg_dump -f /dev/null wevotedev` on the server to evaluate for a corrupted file
    except Exception as e:
        status += "retrieve_tables export_sync_files_to_csv caught " + str(e)
        logger.error(status)
        logger.error("retrieve_tables export_sync_files_to_csv caught " + str(e))
        results = {
            'success': False,
            'status': status,
        }
        return results


def dump_row_col_labels_and_errors(table_name, header, row, index):
    if row[0] == index:
        cnt = 0
        for element in header:
            print(table_name + "." + element + " [" + str(cnt) + "]: " + row[cnt])
            cnt += 1


def check_for_non_ascii(table_name, row):
    field_no = 0
    for field in row:
        if (re.sub('[ -~]', '', field)) != "":
            print("check_for_non_ascii - table: " + table_name + ", row id:  " + str(row[0]) + ", field no: " +
                  str(field_no))
        field_no += 1


def fast_load_status_retrieve(request):   # fastLoadStatusRetrieve
    """
    Returns fast load status information for the progress update on the HTML page
    :param request:
    :return:
    """
    initialize = positive_value_exists(request.GET.get('initialize', False))
    voter_api_device_id = get_voter_api_device_id(request)
    if not voter_api_device_id:
        voter_api_device_id = request.GET.get('voter_api_device_id', '')
    is_running = positive_value_exists(request.GET.get('is_running', True))
    table_name = ''
    chunk = 0
    records = 0
    total = 0
    status = ""
    success = True
    started = None

    try:
        if initialize:
            total = get_total_row_count()
            started = datetime.now(tz=timezone.utc)
            row, success = RetrieveTableState.objects.update_or_create(
                voter_api_device_id=voter_api_device_id,
                defaults={
                    'is_running':       is_running,
                    'started_date':     started,
                    'table_name':       '',
                    'chunk':            0,
                    'current_record':   0,
                    'total_records':    total,
                })
            row_id = row.id
            status += "ROW_INITIALIZED "
        else:
            row = RetrieveTableState.objects.get(voter_api_device_id=voter_api_device_id)
            is_running = row.is_running
            table_name = row.table_name
            chunk = row.chunk
            records = row.current_record
            total = row.total_records
            started = row.started_date
            row_id = row.id
            status += "ROW_RETRIEVED "

    except Exception as e:
        status += "fast_load_status_retrieve caught exception: " + str(e)
        logger.error("fast_load_status_retrieve caught exception: " + str(e))
        success = False
        row_id = ''

    started_txt = started.strftime(DATE_FORMAT_YMD_HMS) if started else ""  # '%Y-%m-%d %H:%M:%S'
    results = {
        'status': status,
        'success': success,
        'initialize': initialize,
        'is_running': is_running,
        'voter_api_device_id': voter_api_device_id,
        'started_date': started_txt,
        'table_name': table_name,
        'chunk': chunk,
        'current_record': records,
        'total_records': total,
        'row_id': row_id,
    }

    res_str = ""
    try:
        res_str = json.dumps(results)
    except Exception as e:
        logger.error(f"ERROR - json.dump failed in fast_load_status_retrieve -- {str(e)}")

    return HttpResponse(res_str, content_type='application/json')


def fast_load_status_update(request):
    """
    Save updated fast load status
    """
    # use the voter_api_device_id from the url (Python), not the one from a cookie (JavaScript)
    voter_api_device_id = request.GET.get('voter_api_device_id', '')
    table_name = request.GET.get('table_name', '')
    additional_records = convert_to_int(request.GET.get('additional_records', 0))
    chunk = convert_to_int(request.GET.get('chunk', None))
    total_records = convert_to_int(request.GET.get('total_records', None))
    is_running = positive_value_exists(request.GET.get('is_running', True))
    print('fast_load_status_update ENTRY table_name', table_name, chunk, 'no row yet', additional_records)

    success = True
    response_string = "error"

    try:
        row = RetrieveTableState.objects.get(voter_api_device_id=voter_api_device_id)
        row.is_running = is_running
        if positive_value_exists(table_name):
            row.table_name = table_name
        if positive_value_exists(chunk):
            row.chunk = chunk
        if positive_value_exists(additional_records):
            row.current_record += additional_records
        if positive_value_exists(total_records):
            row.total_records = total_records
        row.save()
        status = 'ROW_SAVED'
        row_id = row.id
        response_string = (f"fast_load_status_update AFTER SAVE row_id {row_id}, started_date {row.started_date}, "
                           f"table_name {row.table_name}, chunk {row.chunk}, current_record {row.current_record}, "
                           f"total_records {row.total_records}, voter_api_device_id {row.voter_api_device_id}, "
                           f"additional_records {additional_records}")
        print(response_string)

    except Exception as e:
        logger.error("fast_load_status_update caught exception: " + str(e))
        success = False
        status = 'ROW_NOT_SAVED  ' + str(e)
        row_id = -1

    results = {
        'status': status,
        'success': success,
        'response_string': response_string,
        'row_id': row_id,
    }

    return HttpResponse(json.dumps(results), content_type='application/json')

# Similar to getPostgresTableStatistics in weconnect-server
def fast_load_table_statistics(request):
    logger.error("fast_load_table_statistics entrypoint: " + str(request))
    # breakpoint()
    conn = get_psycopg2_connection()
    with (conn.cursor() as cursor):
        sql = 'SELECT schemaname, relname AS table_name, n_live_tup AS estimated_row_count FROM pg_stat_user_tables ORDER BY n_live_tup DESC;'
        cursor.execute(sql)
        rows = cursor.fetchall()
        try:
            html = (
                '<!DOCTYPE html>'
                '<html>'
                '<head>'
                    '<title>Postgres DB Row Counts</title>'
                    '<style>'
                        'table { border-collapse: collapse; width: 50%; margin-left: 20px  }'
                        'th, td { border: 1px solid black; padding: 2px; text-align: left; }'
                        ':link, :visited { color: #039be5; outline: 0; text-decoration: none; padding-left: 20px; }'
                    '</style>'
                '</head>'
                '<body>'
                    '<a href="/apis/v1/docs/" >&lt; back to index</a>'
                    '<div style="height: 20px;"></div>'
                    '<table>'
                        '<tr>'
                            '<th>Table</th>'
                            '<th>Row Count</th>'
                        '</tr>')
            for row in rows:
                html += '<tr><td>%s</td><td>%s</td></tr>' %  (row[1], row[2])
            html += '</table></body></html>'
        except Exception as e:
            html = e
            logger.error(e)
    conn.close()
    return HttpResponse(html)



def make_filename_and_command(table_name):
    db_name = get_environment_variable('DATABASE_NAME')
    db_user = get_environment_variable('DATABASE_USER')
    db_password = get_environment_variable('DATABASE_PASSWORD')
    db_host = get_environment_variable('DATABASE_HOST')
    db_port = get_environment_variable('DATABASE_PORT')

    # command_str = (f"pg_dump 'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}' "
    #                f"--table='{table_name}' --format='c' --file='{tmp_file_name}' --disable-triggers")
    # how to check the args list
    # (3.11.8) WeVoteServer % python -c 'import sys; print(sys.argv[1:])' pg_dump postgresql://stevepodell:stevepg@localhost:5432/WeVoteServerDB --table=ballot_ballotitem --format=c --file=/tmp/backup-ballot_ballotitem-2024-12-10T10:20:40.backup --disable-triggers
    # ['pg_dump', 'postgresql://stevepodell:stevepg@localhost:5432/WeVoteServerDB', '--table=ballot_ballotitem', '--format=c', '--file=/tmp/backup-ballot_ballotitem-2024-12-10T10:20:40.backup', '--disable-triggers']

    tmp_file_name = f"/tmp/backup-{table_name}-{time.strftime('%Y-%m-%dT%H:%M:%S')}.backup"
    pgurl = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'


    command_args = ["pg_dump",
                    f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}',
                    f"--table={table_name}",
                    "--format=c",
                    f"--file={tmp_file_name}",
                    "--disable-triggers"]

    return tmp_file_name, command_args


def dump_full_postgres_table_to_tmp(table_name):
    results = {
        'success': False,
    }
    if table_name not in allowable_tables:
        results = {
            'status': f"Table {table_name} in not on the allowable tables list!",
        }
    else:
        temp_file_name, command_args = make_filename_and_command(table_name)

        try:
            # logger.error('experiment: subprocess.run pg_dump command_args: %s', str(command_args))
            result = subprocess.run(command_args, capture_output=True)  # , shell=False
            # logger.error('experiment: subprocess.run pg_dump returncode: %s', str(result.returncode))
            # logger.error('experiment: subprocess.run pg_dump stdout: %s', result.stdout)
            # logger.error('experiment: subprocess.run pg_dump stderr: %s', result.stderr)
            print('Dump completed')
            results['pg_dump_returncode'] = result.returncode
            results['success'] = True
            results['temp_file_name'] = temp_file_name
            results['status'] = f"tmp file {temp_file_name} created"
            logger.error('Ok: subprocess.run pg_dump temp_file_name : %s', temp_file_name)
        except Exception as e:
            logger.error('subprocess.run pg_dump error : %s', str(e))
            print("!!Problem occurred!!", e)
            results['success'] = False,
            results['error string'] = str(e)
    # logger.error('experiment: subprocess.run pg_dump results : %s', json.dumps(results))
    return results


# noinspection PyUnusedLocal
def backup_one_table_to_s3_controller(voter_api_device_id, table_name):
    t0 = time.time()
    results = {
        'success': True,
        'status': '',
        'aws_s3_file_url': '',
    }

    if table_name not in allowable_tables:
        results['success'] = False
        results['status'] = f"Table {table_name} in not on the allowable tables list!"
    else:
        # command_str, filename = make_filename_and_command(table_name)
        try:
            import boto3
            AWS_ACCESS_KEY_ID = get_environment_variable("AWS_ACCESS_KEY_ID")
            AWS_SECRET_ACCESS_KEY = get_environment_variable("AWS_SECRET_ACCESS_KEY")
            AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
            AWS_STORAGE_BUCKET_NAME = get_environment_variable("AWS_STORAGE_BUCKET_NAME")
            AWS_STORAGE_SERVICE = "s3"

            session = boto3.session.Session(region_name=AWS_REGION_NAME,
                                            aws_access_key_id=AWS_ACCESS_KEY_ID,
                                            aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3 = session.resource(AWS_STORAGE_SERVICE)

            ts = '{:.2f} seconds'.format(time.time() - t0)
            print(f"About to dump table at {ts} seconds")
            results = dump_full_postgres_table_to_tmp(table_name)
            ts: str = '{:.2f} seconds'.format(time.time() - t0)
            results['dump_table_to_tmp_completed'] = ts

            head, tail = os.path.split(results['temp_file_name'])

            date_tomorrow = datetime.now() + timedelta(days=2)
            date_tomorrow_seconds = timedelta(days=2).total_seconds()

            ts = '{:.2f} seconds'.format(time.time() - t0)
            print(f"About to upload to S3 at {ts} seconds")

            s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_file(
                results['temp_file_name'], tail, ExtraArgs={'Expires': date_tomorrow, 'ContentType': 'text/html'})

            aws_s3_file_url = s3.meta.client.generate_presigned_url(
                                ClientMethod='get_object',
                                Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': tail},
                                ExpiresIn=date_tomorrow_seconds,
                            )

            ts = '{:.2f} seconds'.format(time.time() - t0)
            results['tmp_file_to_s3_completed'] = str(ts)

            print(f"Done with upload to S3 at {ts} seconds")
            results['status'] += ', s3 upload completed'
            results['aws_s3_file_url'] = aws_s3_file_url

        except Exception as e:
            results['status'] = 'Error ' + str(e)

    return results
