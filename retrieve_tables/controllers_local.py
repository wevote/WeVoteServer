# retrieve_tables/controllers_local.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import csv
import json
import os
import time
from datetime import datetime, timezone
import sys
import logging

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from io import StringIO
import requests
import pandas as pd
from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.controllers_master import allowable_tables
from wevote_functions.functions import get_voter_api_device_id

logger = wevote_functions.admin.get_logger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, BrokenPipeError):
        logging.error("Unhandled broken pipe error", exc_info=(exc_type, exc_value, exc_traceback))
    else:
        # For other exceptions, you might want to log or handle them differently
        logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


# Set global exception handler
sys.excepthook = handle_exception

# This api will only return the data from the following tables

dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'


def save_off_database():
    file = "WeVoteServerDB-{:.0f}.pgsql".format(time.time())
    os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ['PATH']
    os.system('pg_dump WeVoteServerDB > ' + file)
    time.sleep(20)


# def update_fast_load_db(host, voter_api_device_id, table_name, additional_records):
#     try:
#         response = requests.get(host + '/apis/v1/fastLoadStatusUpdate/',
#                                 verify=True,
#                                 params={'table_name': table_name,
#                                         'additional_records': additional_records,
#                                         'is_running': True,
#                                         'voter_api_device_id': voter_api_device_id,
#                                         })
#         # print('update_fast_load_db ', response.status_code, response.url, voter_api_device_id)
#     except Exception as e:
#         logger.error('update_fast_load_db caught: ', str(e))


def connect_to_db():
    """
    Create a connection with the local postgres database
    :return:
    """
    # CONNECT TO POSTGRES LOCAL WITH SQLALCHEMY AND PSYCOPG
    try:
        engine = sa.create_engine(
            f"postgresql+psycopg2://{get_environment_variable('DATABASE_USER')}:{get_environment_variable('DATABASE_PASSWORD')}@{get_environment_variable('DATABASE_HOST')}:{5432}/{get_environment_variable('DATABASE_NAME')}"
        )
        return engine
    except Exception as e:
        logger.error('Unable to connect to database: ', str(e))


def fetch_data_from_api(url, params, max_retries=10):
    """
    Fetches data from remote Postgres database
    :param url:
    :param params:
    :param max_retries:
    :return:
    """
    for attempt in range(max_retries):
        print(f'Attempt {attempt} of {max_retries} attempts to fetch data from api')
        try:
            print("Waiting for response...")
            response = requests.get(url, params=params, verify=True, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"API request failed with status code {response.status_code}, retrying...")
        except requests.Timeout:
            logger.error(f"Request timed out, retrying...")
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}, retrying...")
        time.sleep(2 ** attempt)  # Exponential backoff

    raise Exception("API request failed after maximum retries")


def convert_df_col_types(df_col_types):
    sqlalchemy_types = {
        'BIGINT': sa.types.BigInteger,
        'INTEGER': sa.types.Integer,
        'VARCHAR': sa.types.String,
        'TEXT': sa.types.Text,
        'DATE': sa.types.Date,
        'TIMESTAMP': sa.types.TIMESTAMP,
        'BOOLEAN': sa.types.Boolean,
        'FLOAT': sa.types.Float,
        'NUMERIC': sa.types.Numeric,
        'CHAR': sa.types.CHAR,
        'DOUBLE PRECISION': sa.types.DOUBLE_PRECISION
    }

    new_dict = {}

    for col_name, col_type in df_col_types.items():
        if col_type.startswith('VARCHAR'):
            length = int(col_type.split('(')[1].strip(')'))
            new_dict[col_name] = sa.types.String(length=length)
        elif col_type in sqlalchemy_types:
            new_dict[col_name] = sqlalchemy_types[col_type]()
        else:
            # Handle unknown types or types not directly mapped
            print(f"Warning: Column type '{col_type}' for column '{col_name}' is not mapped.")
            new_dict[col_name] = sa.types.NullType()  # Default to NullType if unknown

    return new_dict


def psql_insert_copy(table, conn, keys, data_iter):
    """
    Execute SQL statement inserting data

    Parameters
    ----------
    table : pandas.io.sql.SQLTable
    conn : sqlalchemy.engine.Engine or sqlalchemy.engine.Connection
    keys : list of str
        Column names
    data_iter : Iterable that iterates the values to be inserted
    """
    # gets a DBAPI connection that can provide a cursor
    dbapi_conn = conn.connection
    data_list = [list(row) for row in data_iter]
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_list)
        s_buf.seek(0)

        columns = ', '.join('"{}"'.format(k) for k in keys)
        if table.schema:
            table_name = '{}.{}'.format(table.schema, table.name)
        else:
            table_name = table.name

        sql = f"COPY {table_name} ({columns}) FROM STDIN WITH NULL AS '' CSV"
        cur.copy_expert(sql=sql, file=s_buf)


def process_table_data(table_name, data, start_line):
    print("Processing data from API...")
    split_data = data.splitlines(keepends=True)
    first_len = len(split_data[0].split("|"))
    lines = [line.split("|") for line in split_data if len(line.split("|")) == first_len]
    df = pd.DataFrame(lines[1:], columns=lines[0])
    df.columns = df.columns.str.strip()
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    engine = connect_to_db()
    meta = sa.MetaData()
    table = sa.Table(table_name, meta, autoload_with=engine)

    inspector = Inspector.from_engine(engine)
    unique_constraints = inspector.get_unique_constraints(table_name)
    # Retrieve the column information
    columns = inspector.get_columns(table_name)
    # Filter out columns that have a NOT NULL constraint
    not_null_columns = [col['name'] for col in columns if not col['nullable']]

    columns = table.c
    col_dict = {column.name: str(column.type) for column in columns}
    converted_col_types = convert_df_col_types(col_dict)
    print("Cleaning data from API...")
    df_cleaned = clean_df(df, table_name, col_dict, unique_constraints, not_null_columns)
    try:
        with engine.connect() as conn:
            # Truncate the table
            conn.execute(sa.text(f"TRUNCATE {table_name} RESTART IDENTITY CASCADE"))
            conn.commit()
            # checking that table is actually empty before inserting new data
            result = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = result.fetchone()[0]
            if row_count > 0:
                print(f"Error: {table_name} is not empty after truncation")
                return

    except Exception as e:
        print(f'FAILED_TABLE_TRUNCATE: {table_name} -- {str(e)}')

    try:
        with engine.connect() as conn:
            # Write cleaned DataFrame to the PostgresSQL table
            print('Writing cleaned data to table...')
            if table_name == "position_positionentered":
                conn.execute(sa.text(f"""
                ALTER TABLE {table_name} 
                ALTER CONSTRAINT position_positionent_twitter_user_entered_6c22de6d_fk_twitter_t 
                DEFERRABLE INITIALLY DEFERRED"""
                                     ))
            # conn.execute(sa.text(f"SET session_replication_role = replica;"))
            df_cleaned.to_sql(table_name, engine, if_exists='append', index=False, dtype=converted_col_types)
            # conn.execute(sa.text(f"SET session_replication_role = origin;"))
            print(f"Successfully inserted data into {table_name}")
    except Exception as e:
        print(f"FAILED_TABLE_INSERT: {table_name} -- {str(e)}")
    return len(df_cleaned)


def retrieve_sql_files_from_master_server(request):
    """
    Get the json data, and create new entries in the developers local database
    Runs on the Local server (developer's Mac)
    :return:
    """
    status = ''
    t0 = time.time()
    engine = connect_to_db()
    print(
        'Saving off a copy of your local db (an an emergency fallback, that will almost never be needed) in '
        '\'WeVoteServerDB-*.pgsql\' files, feel free to delete them at anytime')
    # save_off_database()
    dt = time.time() - t0
    stats = {}
    print('Saved off local database in ' + str(int(dt)) + ' seconds')
    stats |= {'save_off': str(int(dt))}

    # ONLY CHANGE host to 'wevotedeveloper.com' while debugging the fast load code, where Master and Client are the same
    # host = 'https://wevotedeveloper.com:8000'
    host = 'https://api.wevoteusa.org'

    voter_api_device_id = get_voter_api_device_id(request)
    requests.get(host + '/apis/v1/fastLoadStatusRetrieve',
                 params={"initialize": True, "voter_api_device_id": voter_api_device_id}, verify=True)

    for table_name in allowable_tables:
        chunk_size = 500000 if table_name != 'candidate_candidatecampaign' else 100000
        print(f'\nStarting on the {table_name} table, requesting {chunk_size} rows')
        start = 0
        end = chunk_size - 1
        structured_json = {}

        # filling table with 500,000 line chunks
        while end < 20000000:
            print(f"Processing chunk from {start} to {end} for table {table_name}")
            try:
                url = f'{host}/apis/v1/retrieveSQLTables/'
                params = {'table_name': table_name, 'start': start, 'end': end,
                          'voter_api_device_id': voter_api_device_id}
                structured_json = fetch_data_from_api(url, params)
            except Exception as e:
                print(f"FETCH_ERROR: {table_name} -- {str(e)}")

            if not structured_json['success']:
                print(f"FAILED: Did not receive '{table_name}' from server")
                break

            try:
                data = structured_json['files'].get(table_name, "")
                lines_count = process_table_data(table_name, data, start)
                print(f'{lines_count} lines in table {table_name}')
                if lines_count == 0 or end - lines_count > 0:
                    break
            except Exception as e:
                print(f"TABLE_PROCESSING_ERROR: {table_name} -- {str(e)}")

            start += chunk_size
            end += chunk_size

        with engine.connect() as conn:
            try:
                query = sa.text(f"""SELECT setval('{table_name}_id_seq', (SELECT MAX(id) FROM "{table_name}"))""")
                result = conn.execute(query)
                sequence_val = result.fetchone()[0]
                # print(f"... SQL executed: {query} and returned {sequence_val}")
                if sequence_val is not None:
                    query = sa.text(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH {int(sequence_val) + 1}")
                    conn.execute(query)
                    # print(f"... SQL executed: {query}")
                # To confirm:  SELECT * FROM information_schema.sequences where sequence_name like 'org%'
            except Exception as e:
                print(f'...FAILED_SEQUENCE_RESET: {table_name} -- {str(e)}')

    minutes = (time.time() - t0) / 60
    print(f"Total time for all tables: {minutes:.1f} minutes")
    results = {'status': 'Completed', 'status_code': 200}
    return HttpResponse(json.dumps(results), content_type='application/json')


def is_table_empty(table_name, engine):
    with engine.connect() as conn:
        query = sa.text(f"SELECT COUNT(*) FROM {table_name};")
        result = conn.execute(query)
        count = result.scalar()  # Get the count of rows
    return count == 0


def clean_df(df, table_name, col_dict, unique_constraints, not_null_columns):
    """
    Runs on the Master server
    """
    df.replace('\\N', pd.NA, inplace=True)
    df.replace(['\n', ','], ' ', inplace=True)
    df.replace(to_replace=r'[^0-9a-zA-Z\. _]', value="", regex=True)

    # Remove leading and trailing whitespaces in each cell of df
    df = strip_whitespace(df)

    # cleaning bool columns
    boolean_columns = [col for col, dtype in col_dict.items() if 'BOOLEAN' == dtype]
    df = clean_bool_cols(df, boolean_columns)

    # cleaning timestamp columns
    timestamp_columns = [col for col, dtype in col_dict.items() if 'TIMESTAMP' == dtype]
    df = clean_timestamp_cols(df, timestamp_columns, not_null_columns)

    # cleaning int columns
    int_columns = [col for col, dtype in col_dict.items() if 'INTEGER' == dtype or 'BIGINT' == dtype]
    for col in int_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # add any column to this list if you know it doesn't have ids
    dummy_cols = {'ballotpedia_election_id', 'bioguide_id', 'thomas_id', 'lis_id', 'govtrack_id', 'fec_id',
                  'maplight_id'}
    df = get_dummy_ids(df, dummy_cols, unique_constraints)

    if table_name == "politician_politician":
        df['middle_name'].replace("\\", "", inplace=True)  # middle_name
        df['gender'].replace(["\\N", ""], "U", inplace=True)  # gender
    return df


def strip_whitespace(df):
    """
    Strips whitespace from every cell in the DataFrame.
    """
    return df.map(lambda x: x.strip() if isinstance(x, str) else x)


def clean_bool_cols(df, boolean_columns):
    boolean_map = {
        'True': 1, 'False': 0,
        't': 1, 'f': 0,
        '1': 1, '0': 0,
        'yes': 1, 'no': 0
    }
    for col in boolean_columns:
        if col in df.columns:
            df[col].replace(r'^\s*$', pd.NA, regex=True, inplace=True)
            df[col].replace(boolean_map, inplace=True)
            df[col] = df[col].fillna(False).astype(bool)  # Convert remaining NaNs to False
        else:
            print(f"Column {col} is not present in the dataframe")
    return df


def clean_timestamp_cols(df, timestamp_columns, not_null_columns):
    for col in timestamp_columns:
        # Ensure timestamp cols with not-null constraints do not contain problematic values before conversion
        if col in not_null_columns:
            df[col].replace(['', pd.NA, 'null'], datetime.now(timezone.utc), inplace=True)
        df[col] = pd.to_datetime(df[col], errors='coerce')  # convert cols to datetime
        df[col].fillna(datetime.now(timezone.utc), inplace=True)  # Fill any NaT values that were created by conversion
        if df[col].dt.tz is None:  # Convert to UTC timezone if not timezone specified
            df[col] = df[col].dt.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
        else:
            df[col] = df[col].dt.tz_convert('UTC')
    return df


def get_row_count_from_master_server():
    try:
        host = 'https://api.wevoteusa.org'
        response = requests.get(host + '/apis/v1/retrieveSQLTablesRowCount')
        if response.status_code == 200:
            count = int(response.json()['rowCount'])
            return count
        logger.error("retrieveSQLTablesRowCount received HTTP response " + str(response.status_code))
        return -1
    except Exception as e:
        logger.error("retrieveSQLTablesRowCount row count error ", str(e))
        return -1


def clean_bigint_row(row, index):
    if not row[index].isnumeric() and row[index] != '\\N':
        row[index] = 0


def clean_url(row, index):
    if "," in row[index]:
        row[index] = row[index].replace(",", "")


def substitute_null(row, index, sub):
    if row[index] == '\\N' or row[index] == '':
        row[index] = sub


def get_dummy_ids(df, dummy_cols, unique_constraints):
    """
    Generates unique id's for each row in dummy_cols and unique_constraints
    :param df:
    :param dummy_cols: a list of col names that require unique id's for each row
    :param unique_constraints: a list of col names that have unique constraints
    :return:
    """
    # adding columns with unique constraints to dummy_cols
    unique_cols = set([con['column_names'][0] for con in unique_constraints])
    dummy_cols.update(unique_cols - dummy_cols)
    dummy_cols = list(dummy_cols)
    for col in dummy_cols:
        if col in df.columns:
            # Filter for rows where the column has empty strings, '\N', or '0'
            mask = df[col].replace(['', '\\N', '0', 0], pd.NA).isna()

            # Check if there are rows that need new IDs
            if mask.any():
                existing_ids = df.loc[~mask, col].dropna().unique()  # Get existing IDs in the column
                max_existing_id = pd.Series(existing_ids).apply(pd.to_numeric,
                                                                errors='coerce').max()  # Get the max existing ID
                next_id = int(max_existing_id) + 1 if pd.notna(max_existing_id) else 1  # Set the next ID
                # Generate new IDs starting from the next available ID
                df.loc[mask, col] = [next_id + i for i in range(mask.sum())]

    return df
