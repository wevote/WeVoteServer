# retrieve_tables/controllers_local.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json
import os
import re
import subprocess
import time

import psycopg2
import requests
import sqlalchemy as sa
from django.http import HttpResponse, HttpResponseServerError
try:
    from opentelemetry import context as otel_context
    from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY
    OTEL_AVAILABLE = True
except ImportError:
    otel_context = None
    _SUPPRESS_INSTRUMENTATION_KEY = None
    OTEL_AVAILABLE = False

import wevote_functions.admin
from config.environment_variable_functions import get_environment_variable, get_environment_variable_default
from retrieve_tables.retrieve_common import allowable_tables
from wevote_functions.functions import get_voter_api_device_id, positive_value_exists, server_is_source_of_truth
from wevote_tokens.enums import TokenCookies, TokenHeaders, TokenTypes
from wevote_tokens.models.single_use_tokens import SingleUseTokenManager
from wevote_tokens.utils import TokensManager

logger = wevote_functions.admin.get_logger(__name__)

global_stats = {}
dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'

# EXTENDED_FASTLOAD_LOGGING is only used by developers for debugging, set it on the local, and then it is sent in
# the API requests to the master, and the resulting logging can be monitored in CloudWatch
EXTENDED_FASTLOAD_LOGGING = get_environment_variable_default("EXTENDED_FASTLOAD_LOGGING", False)
# DEBUG_FASTLOAD_SINGLE_SERVER is only used by developers for debugging, where you have downloaded a copy of the
# production database, and are using the local server as both local and master.  See docs/DebuggingFastLoadPython.md
DEBUG_FASTLOAD_SINGLE_SERVER = get_environment_variable_default("DEBUG_FASTLOAD_SINGLE_SERVER", False)


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

        # print('update_fast_load_db ', response.status_code, response.url, voter_api_device_id, flush=True)
        # print(response.request.url, flush=True)
        print('update_fast_load_db ', response.status_code, response.url, voter_api_device_id, flush=True)
    except Exception as e:
        logger.error('update_fast_load_db caught: ', str(e))


def retrieve_sql_files_from_master_server(request):
    results = {}

    # ONLY CHANGE host to 'wevotedeveloper.com' while debugging the fast load code, where Master and Client are the same
    host = 'https://wevotedeveloper.com:8000' if DEBUG_FASTLOAD_SINGLE_SERVER else 'https://api.wevoteusa.org'
    voter_api_device_id = get_voter_api_device_id(request)

    try:
        if server_is_source_of_truth() and not DEBUG_FASTLOAD_SINGLE_SERVER:
            raise Exception('Server may be a source of truth. Not allowed to Fast Load to maintain data integrity.')

        token_headers = {
            TokenHeaders.USER_ID.value: request.COOKIES.get(TokenCookies.SYNC_DATA_WITH_MASTER_SERVERS_START_USER_ID.value, None),
            TokenHeaders.AUTHORIZATION.value: f'Bearer {request.COOKIES.get(TokenCookies.SYNC_DATA_WITH_MASTER_SERVERS_START_TOKEN_ID.value, None)}',
            TokenHeaders.TOKEN_KEY.value: request.COOKIES.get(TokenCookies.SYNC_DATA_WITH_MASTER_SERVERS_START_TOKEN_KEY.value, None),
            TokenHeaders.TOKEN_NEW_KEY.value: SingleUseTokenManager.generate_encryption_key(),
            TokenHeaders.TOKEN_TYPE.value: TokenTypes.SINGLE_USE.value,
            TokenHeaders.CREATE_TOKEN.value: 'True',
        }

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
            params = {'table_name': table_name, 'voter_api_device_id': voter_api_device_id,
                      'extended_fastload_logging': EXTENDED_FASTLOAD_LOGGING}
            fetch_data_response = fetch_data_from_api(url, params, token_headers, 100, 180)  # 3 min timeout for ballot_i

            response_headers = TokensManager.convert_headers_to_dict(fetch_data_response.headers)
            if 'token_authentication' in response_headers:
                token_authentication = response_headers['token_authentication']
                # print(f"Token authentication: {token_authentication}")
                if token_authentication['success']:
                    token_creation = response_headers['token_creation']
                    # print(f"Token creation: {token_creation}")
                    if token_creation['success']:
                        token_headers[TokenHeaders.AUTHORIZATION.value] = f"Bearer {token_creation['token_info']['token_pk']}"
                        token_headers[TokenHeaders.TOKEN_KEY.value] = token_headers[TokenHeaders.TOKEN_NEW_KEY.value]
                        token_headers[TokenHeaders.TOKEN_NEW_KEY.value] = SingleUseTokenManager.generate_encryption_key()
                else:
                    if not DEBUG_FASTLOAD_SINGLE_SERVER:
                        print(f"Token authentication failed: {token_authentication['error_message']}")
            else:
                print("Token authentication not found in response headers.")

            structured_json = fetch_data_response.json()
            aws_s3_file_url = structured_json['aws_s3_file_url']
            print(f"{global_stats['count']} -- URL to aws file {aws_s3_file_url} "
                  f"received at {int(time.time()-global_stats['global_t0'])} seconds")

            global_stats['table_name_text'] = ('<b>Loading</b>&nbsp;&nbsp;<i>' + table_name +
                                          '</i>&nbsp;&nbsp;from local disk to the <b>local</b> server')
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

    if EXTENDED_FASTLOAD_LOGGING:
        tf = tempfile.NamedTemporaryFile(delete=False, mode='r+b')
        full_path = tf.name
        print(f"Full Path of tempfile: {full_path}")
    else:
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
                    # print(f"Chunk: {chunk}")
                    tf.write(chunk)
        # Force the python buffer to be written to the file
        tf.flush()
        if tf.tell() != global_stats['table_size']:
            raise Exception(f"Downloaded {int(tf.tell()/1024)} Kb, expected {int(global_stats['table_size']/1024)} Kb")

        print("Downloaded", tf.name)

        # if EXTENDED_FASTLOAD_LOGGING:
        #     with os.scandir('/tmp') as entries:
        #         text = 'Ok: fastload Local after: '
        #         for entry in entries:
        #             if entry.is_file():
        #                 # Get statistics for each file
        #                 info = entry.stat()
        #                 text += f"{entry.name} ({info.st_size}) {datetime.fromtimestamp(info.st_mtime)}, "
        #         logger.error(text)

        diff_t0 = int(time.time() - global_stats['global_t0'])
        print(f"Done with download from S3 at {diff_t0} seconds")
    except Exception as e:
        print("!!Problem occurred Downloading file: ", str(e))
        results['success'] = False,
        results['error string'] = str(e)
        tf.close()
        return results

    try:
        in_docker = get_environment_variable_default('RUNNING_IN_DOCKER', False)
        db_name = get_environment_variable("DATABASE_NAME")
        db_user = get_environment_variable('DATABASE_USER')
        db_password = get_environment_variable('DATABASE_PASSWORD')
        db_host = 'db' if in_docker else get_environment_variable_default('DATABASE_HOST', 'db')
        db_port = get_environment_variable_default('DATABASE_PORT', '5432')
        db_pass = get_environment_variable('DATABASE_PASSWORD')

        diff_t0 = int(time.time() - global_stats['global_t0'])
        print(f"About to TRUNCATE {table_name} at {diff_t0} seconds", flush=True)
    except Exception as e:
        print("!!Problem occurred getting variables for db:", str(e), flush=True)
        results['success'] = False,
        results['error string'] = str(e)
        tf.close()
        return results

    try:
        table_truncated = truncate_table_psycopg2(table_name)
        if isinstance(table_truncated, Exception):
            raise Exception(f"Truncate table {table_name} failed: {table_truncated}")

        diff_t0 = int((time.time() - global_stats['global_t0']))
        print(f"About to sync data from tempfile at {diff_t0} seconds", flush=True)

        # Sanity check to prove that that pg_dump can be run in controllers_local -- never need this
        # command_args = ["pg_dump",
        #                 # f'postgresql://{db_user}:{db_password}@db:{db_port}/wevoteserverdb',
        #                 # "-d",
        #                 "\'postgresql://postgres:admin@db:5432/wevoteserverdb\'",
        #                 "--format=c",
        #                 "--table=voter_voteraddress",
        #                 "--file=/tmp/steve25",
        #                 "--disable-triggers"]
        #
        # # print('pg_dump command:', ' '.join(command_args))
        # print('pg_dump command WARMUP1:')
        # try:
        #     result2 = subprocess.run(command_args, capture_output=True, text=True)
        #     print('pg_dump command WARMUP2 result2:' + str(result2))
        # except Exception as e:
        #     print("pg_dump ERROR: " + str(e))
        # print('pg_dump command WARMUP3: done')
        #

        print(f"Ok. Running in_docker: {in_docker}", flush=True)
        if in_docker:
            pgurl = f'\'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}\''
            command_list = f"pg_restore -c -v --disable-triggers --no-password --no-owner --no-acl -U postgres -d {pgurl} -t {table_name} < {tf.name}"
            print('Ok. command in Docker:   ' + command_list, flush=True)
        else:
            command_list = ['pg_restore',
                            '-v',
                            '--data-only',
                            '--disable-triggers',
                            '--no-password',
                            '--no-owner',
                            '--no-acl',
                            '-U', db_user]
            command_list.extend(['-h', db_host] if positive_value_exists(db_host) else [])
            command_list.extend(['-p', db_port] if positive_value_exists(db_port) else [])
            command_list.extend(['-d', db_name,
                                 '-t', table_name,
                                 tf.name])
            print(f"Ok. Not running in Docker, command: {command_list}", flush=True)

        # Get password and set environment. If no password, don't set the environment variable.
        # Passing 'None' to the environment variable will cause the command to fail.
        env = os.environ.copy()
        if db_pass:
            env['PGPASSWORD'] = db_pass

        # env_in_container = subprocess.run(["env"], env=env, capture_output=True, text=True)
        # print(f"pg_restore env: {env_in4_container.stdout}")
        # script_path = os.path.join("/tmp", tf.name)
        # print(f"script_path: {script_path}")
        # env_in_container = subprocess.run(['ls', '-la', script_path], env=env, capture_output=True, text=True)
        # print(f"ls -la {script_path}:  {env_in_container.stdout}")

        # The Docker branch builds a shell string (uses "< file" redirection) so it needs shell=True.
        # The non-Docker branch builds an argument list, which must run with shell=False, otherwise
        # only "pg_restore" is executed and its arguments are dropped.
        table_restore_result = subprocess.run(command_list, shell=in_docker, env=env,
                                              capture_output=True, text=True)

        # Any return code other than 0 is an error
        if table_restore_result.returncode != 0:
            logger.error(f"pg_restore failed: {table_restore_result.stderr}")

        diff_t0 = int((time.time() - global_stats['global_t0']))
        print(f"Restore completed at {diff_t0} seconds", flush=True)
        results['success'] = True

        if EXTENDED_FASTLOAD_LOGGING:     # Double check
            try:
                query = f"SELECT count(*) FROM public.\"{table_name}\""
                command_list = ['psql', '-h', db_host, '-U', 'postgres', '-d',  db_name, '-c', query]
                count_result = subprocess.run(command_list, env=env, capture_output=True, text=True)
                numbers = re.findall(r"\d+", count_result.stdout)
                print(f"pg_restore successfully restored {table_name} with row count: {numbers[0]}", flush=True)
            except Exception as e:
                logger.error("pg_restore count(*) failed" + str(e))

    except Exception as e:
        logger.error("Problem occurred in pg_restore step 2: ", str(e))
        results['success'] = False,
        results['error string'] = str(e)
    tf.close()

    return results


# noinspection PyUnusedLocal
def get_local_fast_load_status(request):
    # print("Getting local fast load status", global_stats, flush=True)
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
        # print(f"TRUNCATE TABLE {table_name} re {str(ret)}", flush=True)
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
            print(f"RUNNING: DROP TABLE {table_name} ", flush=True)
        except Exception as e:
            logger.error(f'FAILED_TABLE_DROP: {table_name} -- {str(e)}')

def fetch_data_from_api(url, params, token_headers, max_retries=1000, timeout=8):
    """
    Fetches data from remote Postgres database
    :param url:
    :param params:
    :param max_retries:
    :return:
    """
    for attempt in range(max_retries):
        # print(f'Attempt {attempt} of {max_retries} attempts to fetch data from api', flush=True)
        try:
            verify = not DEBUG_FASTLOAD_SINGLE_SERVER  # verify is True for normal operation
            #Strip otel tokens so a new trace is tracked in production
            token = None
            if OTEL_AVAILABLE:
                token = otel_context.attach(otel_context.set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
            try:
                response = requests.get(url, params=params, headers=token_headers, verify=verify, timeout=timeout)
            finally:
                if token is not None:
                    otel_context.detach(token)
            if response.status_code == 200:
                return response
            elif 400 <= response.status_code < 500:
                logger.warning(f"\nAPI request failed with status code {response.status_code}. \
                Authentication error entountered. Try passing login info to the master server and retrying.")
                break
            else:
                logger.warning(f"\nAPI request failed with status code {response.status_code}, retrying...")
        except requests.Timeout:
            logger.error(f"Request timed out, retrying...\n{url} params: {params}")
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}, retrying...")
        time.sleep(2 ** attempt)  # Exponential backoff

    raise Exception("API request failed after maximum retries")
