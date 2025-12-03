# retrieve_tables/controllers_local.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import os
import subprocess
import time

import psycopg2
import requests
import sqlalchemy as sa
from django.http import HttpResponse, HttpResponseServerError

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.retrieve_common import allowable_tables
from wevote_functions.functions import get_voter_api_device_id, positive_value_exists, server_is_source_of_truth

logger = wevote_functions.admin.get_logger(__name__)

global_stats = {}
dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'


def update_fast_load_db(host, voter_api_device_id, table_name, additional_records):
    """
    Updates progress bar and data on fast load HTML page
    :param host:
    :param voter_api_device_id:
    :param table_name:
    :param additional_records:
    :return:
    """
    try:
        response = requests.get(host + '/apis/v1/fastLoadStatusUpdate/',
                                verify=True,
                                params={'table_name': table_name,
                                        'additional_records': additional_records,
                                        'is_running': True,
                                        'voter_api_device_id': voter_api_device_id,
                                        })

        # print('update_fast_load_db ', response.status_code, response.url, voter_api_device_id)
        # print(response.request.url)
        print('update_fast_load_db ', response.status_code, response.url, voter_api_device_id)
    except Exception as e:
        logger.error('update_fast_load_db caught: ', str(e))


def retrieve_sql_files_from_master_server(request):
    results = {}

    # ONLY CHANGE host to 'wevotedeveloper.com' while debugging the fast load code, where Master and Client are the same
    # host = 'https://wevotedeveloper.com:8000'
    host = 'https://api.wevoteusa.org'
    voter_api_device_id = get_voter_api_device_id(request)

    try:
        # hack, call master from local...
        # results = backup_one_table_to_s3_controller('id', 'ballot_ballotitem')
        # ballot_ballotitem has 40,999,358 records in December 2024 and takes about 69 seconds to dump and 10 more to
        # upload on the master servers (simulated on my fast Mac with fast Internet).  These s3 files are set to expire
        # in a day
        # Example: https://wevote-images.s3.amazonaws.com/backup-ballot_ballotitem-2024-12-06T13:25:13.backup
        # This same backup file takes 21 seconds to download to a local tempfile, and then 3 seconds to pg_restore

        if server_is_source_of_truth():
            raise Exception('Server may be a source of truth. Not allowed to Fast Load to maintain data integrity.')

        num_tables = len(allowable_tables)
        print(f"Fast loading {num_tables} tables")
        global_stats['num_tables'] = num_tables
        global_stats['count'] = 0
        global_stats['step'] = 0
        global_stats['elapsed'] = 0
        global_stats['global_t0'] = time.time()

        for table_name in allowable_tables:
            global_stats['table_size'] = ''
            global_stats['table_name_text'] = ('<b>Saving</b>&nbsp;&nbsp;<i>' + table_name +
                                          '</i>&nbsp;&nbsp;to s3 from the <b>master</b> server')
            global_stats['table_name'] = table_name
            global_stats['count'] += 1
            global_stats['step'] += 1
            global_stats['elapsed'] = int(time.time()- global_stats['global_t0'])
            print(f"{global_stats['count']} -- Retrieving table {table_name}")
            url = f'{host}/apis/v1/backupOneTableToS3/'
            params = {'table_name': table_name, 'voter_api_device_id': voter_api_device_id}
            structured_json = fetch_data_from_api(url, params, 100, 180)  # 3 min timeout for ballot_i
            aws_s3_file_url = structured_json['aws_s3_file_url']
            print(f"{global_stats['count']} -- URL to aws file {aws_s3_file_url} "
                  f"received at {int(time.time()-global_stats['global_t0'])} seconds")

            global_stats['table_name_text'] = ('<b>Loading</b>&nbsp;&nbsp;<i>' + table_name +
                                          '</i>&nbsp;&nbsp;from s3 on the <b>local</b> server')
            # restore_one_file_to_local_server(aws_s3_file_url, 'ballot_ballotitem')
            restore_one_file_to_local_server(aws_s3_file_url, table_name)
            global_stats['step'] += 1
            print(f"{global_stats['count']} "
                  f"-- Restored table {table_name} at {int(time.time()- global_stats['global_t0'])} seconds")

        print(f"All {num_tables} tables fast loaded in {int(time.time() - global_stats['global_t0'])} seconds")

    except Exception as e:
        results['status'] = 'Error ' + str(e)
        logger.error(f"Error retrieving {str(e)}")
        return HttpResponseServerError(json.dumps(results), content_type='application/json')

    return HttpResponse(json.dumps(results), content_type='application/json')


def restore_one_file_to_local_server(aws_s3_file_url, table_name):
    import tempfile
    results = {
        'success': False
    }

    tf = tempfile.NamedTemporaryFile(mode='r+b')
    try:
        diff_t0 = int((time.time() - global_stats['global_t0']))
        print(f"About to download {table_name} from S3 at {diff_t0} seconds")
        with requests.get(aws_s3_file_url, stream=True) as response:
            global_stats['table_size'] = int(response.headers.get('Content-Length'))
            response.raise_for_status()
            # Process in 1MB chunks
            for chunk in response.iter_content(chunk_size=(1024*1024)):
                if chunk:
                    tf.write(chunk)
        # Force the python buffer to be written to the file            
        tf.flush()
        if tf.tell() != global_stats['table_size']:
            raise Exception(f"Downloaded {int(tf.tell()/1024)} Kb, expected {int(global_stats['table_size']/1024)} Kb")

        print("Downloaded", tf.name)
        diff_t0 = int(time.time() - global_stats['global_t0'])
        print(f"Done with download from S3 at {diff_t0} seconds")
    except Exception as e:
        print("!!Problem occurred Downloading file:", e)
        results['success'] = False,
        results['error string'] = str(e)
        tf.close()
        return results

    try:
        db_name = get_environment_variable("DATABASE_NAME")
        db_user = get_environment_variable('DATABASE_USER')
        db_host = get_environment_variable('DATABASE_HOST')
        db_port = get_environment_variable('DATABASE_PORT')
        db_pass = get_environment_variable('DATABASE_PASSWORD')

        diff_t0 = int(time.time() - global_stats['global_t0'])
        print(f"About to TRUNCATE {table_name} at {diff_t0} seconds")
        # # engine = connect_to_db()
    except Exception as e:
        print("!!Problem occurred getting variables for db:", e)
        results['success'] = False,
        results['error string'] = str(e)
        tf.close()
        return results

    try:
        table_truncated = truncate_table_psycopg2(table_name)
        if isinstance(table_truncated, Exception):
            raise Exception(f"Truncate table {table_name} failed: {table_truncated}")

        diff_t0 = int((time.time() - global_stats['global_t0']))
        print(f"About to sync data from tempfile at {diff_t0} seconds")

        command_list = ['pg_restore',
                        '-v', 
                        '--data-only', 
                        '--disable-triggers',
                        '--no-password',
                        '-U', db_user]
        command_list.extend(['-h', db_host] if positive_value_exists(db_host) else [])
        command_list.extend(['-p', db_port] if positive_value_exists(db_port) else [])
        command_list.extend(['-d', db_name,
                            '-t', table_name,
                            tf.name])

        # Get password and set environment. If no password, don't set the environment variable.
        # Pssing 'None' to the environment variable will cause the command to fail.
        env = os.environ.copy()
        if db_pass:
            env['PGPASSWORD'] = db_pass

        table_restore_result = subprocess.run(command_list, env=env, capture_output=True, text=True)
        # Any return code other than 0 is an error
        if table_restore_result.returncode != 0:
            raise RuntimeError(f"pg_restore failed: {table_restore_result.stderr}")

        diff_t0 = int((time.time() - global_stats['global_t0']))
        print(f"Restore completed at {diff_t0} seconds")
        results['success'] = True
    except Exception as e:
        print("!!Problem occurred 2!!", e)
        logger.error("Problem occurred in pg_restore step: ", e)
        results['success'] = False,
        results['error string'] = str(e)
    tf.close()

    return results


# noinspection PyUnusedLocal
def get_local_fast_load_status(request):
    # print("Getting local fast load status", global_stats)
    return HttpResponse(json.dumps(global_stats), content_type='application/json')


def connect_to_db():
    """
    Create a connection with the local postgres database with sqlalchemy and psycopg2
    :return:
    """
    try:
        connection_string = f"postgresql+psycopg2://{get_environment_variable('DATABASE_USER')}"
        if positive_value_exists(get_environment_variable('DATABASE_PASSWORD')):
            connection_string += f":{get_environment_variable('DATABASE_PASSWORD')}"
        connection_string += f"@{get_environment_variable('DATABASE_HOST')}"
        if positive_value_exists(get_environment_variable('DATABASE_PORT')):
            connection_string += f":{get_environment_variable('DATABASE_PORT')}"
        connection_string += f"/{get_environment_variable('DATABASE_NAME')}"
        engine = sa.create_engine(connection_string)
        return engine
    except Exception as e:
        logger.error('Unable to connect to database: ', str(e))


def truncate_table_psycopg2(table_name):
    try:
        conn = psycopg2.connect(
            database=get_environment_variable('DATABASE_NAME'),
            user=get_environment_variable('DATABASE_USER'),
            password=get_environment_variable('DATABASE_PASSWORD'),
            host=get_environment_variable('DATABASE_HOST'),
            port=get_environment_variable('DATABASE_PORT')
        )
        conn.autocommit = True
        cur = conn.cursor()
        statement = f"TRUNCATE TABLE {table_name}"
        ret = cur.execute(statement)
        # print(f"TRUNCATE TABLE {table_name} re {str(ret)}")
    except Exception as e:
        logger.error(f'FAILED_TABLE_TRUNCATE: {table_name} -- {str(e)}')
        return e


def drop_table(engine, table_name):
    """
    Truncates (completely clears contents of) local table
    :param engine: connection to local Postgres
    :param table_name: table to truncate
    :return:
    """
    with engine.connect() as conn:
        try:
            # Drop the table
            conn.execute(sa.text(f"DROP TABLE {table_name}"))
            print(f"RUNNING: DROP TABLE {table_name} ")
        except Exception as e:
            logger.error(f'FAILED_TABLE_DROP: {table_name} -- {str(e)}')


def fetch_data_from_api(url, params, max_retries=1000, timeout=8):
    """
    Fetches data from remote Postgres database
    :param url:
    :param params:
    :param max_retries:
    :return:
    """
    for attempt in range(max_retries):
        # print(f'Attempt {attempt} of {max_retries} attempts to fetch data from api')
        try:
            response = requests.get(url, params=params, verify=True, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"\nAPI request failed with status code {response.status_code}, retrying...")
        except requests.Timeout:
            logger.error(f"Request timed out, retrying...\n{url} params: {params}")
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}, retrying...")
        time.sleep(2 ** attempt)  # Exponential backoff

    raise Exception("API request failed after maximum retries")
