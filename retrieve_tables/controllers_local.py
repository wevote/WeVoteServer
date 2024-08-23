# retrieve_tables/controllers_local.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import csv
import json
import os
import time

import psycopg2
from psycopg2 import sql
import pandas.io.sql as sqlio
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
import uuid
import requests
import pandas as pd
from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.controllers_master import allowable_tables
from wevote_functions.functions import get_voter_api_device_id

logger = wevote_functions.admin.get_logger(__name__)

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
    Create a connection with the local postges database
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
            print(f'Response received with status code {response.status_code}')
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
        'CHAR': sa.types.CHAR
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

    pk_col = set()
    unique_cols = set()
    unique_cols.add("id")
    for constraint in table.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            for column in constraint.columns:
                unique_cols.add(column.name)
        if isinstance(constraint, sa.PrimaryKeyConstraint):
            for column in constraint.columns:
                pk_col.add(column.name)
    print("UNIQUE COLS: ", unique_cols)
    with engine.connect() as conn:
        try:
            conn.execute(table.delete())
            print(f'Deleted old data in table {table_name}...')
        except Exception as e:
            print(f'FAILED_TABLE_DELETE: {table_name} -- {str(e)}')

    columns = table.c
    col_names = ", ".join([f'"{col.name}"' for col in columns])
    col_dict = {column.name: str(column.type) for column in columns}
    converted_col_types = convert_df_col_types(col_dict)
    print("Cleaning data...")
    df_cleaned = clean_df(df, table_name, col_dict)
    print("Cleaning done.")
    # print(f"Cleaned df for {table_name}: {df_cleaned.head()}")

    try:
        # Write cleaned DataFrame to the PostgreSQL table
        gulpsize = 500000 if table_name != 'candidate_candidatecampaign' else 100000
        print("Writing new data to Postgres...")
        upsert_df(df_cleaned, table_name, col_names, unique_cols, pk_col, engine)
        # df_cleaned.to_sql(
        #     table_name, engine,
        #     if_exists='append',
        #     chunksize=gulpsize,
        #     index=False,
        #     dtype=converted_col_types,
        #     # method="multi"
        # )
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
        'Saving off a copy of your local db (an an emergency fallback, that will almost never be needed) in \'WeVoteServerDB-*.pgsql\' files, feel free to delete them at anytime')
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
        print('Starting on the ' + table_name + ' table, requesting up to 500,000 rows')
        start = 0
        end = 500000 - 1

        # filling table with 500,000 line chunks
        while end < 20000000:
            url = f'{host}/apis/v1/retrieveSQLTables/'
            params = {'table_name': table_name, 'start': start, 'end': end, 'voter_api_device_id': voter_api_device_id}
            structured_json = fetch_data_from_api(url, params)

            if not structured_json['success']:
                print(f"FAILED: Did not receive '{table_name}' from server")
                break
            print(f'Received {table_name} table from server')

            data = structured_json['files'].get(table_name, "")
            lines_count = process_table_data(table_name, data, start)
            print(f'{lines_count} lines in table {table_name}')
            if end - lines_count > 0:
                break
            if lines_count == 0:
                break

            start += 500000
            end += 500000

        with engine.connect() as conn:
            try:
                query = sa.text(f"""SELECT setval('{table_name}_id_seq', (SELECT MAX(id) FROM "{table_name}"))""")
                result = conn.execute(query)
                sequence_val = result.fetchone()[0]
                print(f"... SQL executed: {query} and returned {sequence_val}")
                if sequence_val is not None:
                    query = sa.text(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH {int(sequence_val)+1}")
                    conn.execute(query)
                    print(f"... SQL executed: {query}")
                # To confirm:  SELECT * FROM information_schema.sequences where sequence_name like 'org%'
            except Exception as e:
                print(f'...FAILED_SEQUENCE_RESET: {table_name} -- {str(e)}')

    minutes = (time.time() - t0) / 60
    for table, time_taken in stats.items():
        secs = int(time_taken)
        min1, secs1 = divmod(secs, 60)
        print(f"Processing and loading table {table} took {min1}:{secs1} cumulative")

    print(f"Total time for all tables: {minutes:.1f} minutes")
    results = {'status': 'Completed', 'status_code': 200}
    return HttpResponse(json.dumps(results), content_type='application/json')


def is_table_empty(table_name, engine):
    with engine.connect() as conn:
        query = sa.text(f"SELECT COUNT(*) FROM {table_name};")
        result = conn.execute(query)
        count = result.scalar()  # Get the count of rows
    return count == 0


def clean_df(df, table_name, col_dict):
    """
    Runs on the Master server
    """
    df.replace('\\N', pd.NA, inplace=True)
    df.replace(['\n', ','], ' ', inplace=True)
    df.replace(to_replace=r'[^0-9a-zA-Z\. _]', value="", regex=True)

    def strip_whitespace(x):
        if isinstance(x, str):
            return x.strip()
        return x

    # Apply the function to each element of the DataFrame
    df = df.map(strip_whitespace)

    # cleaning bool columns
    boolean_columns = [col for col, dtype in col_dict.items() if 'BOOLEAN' == dtype]
    df = clean_bool_cols(df, boolean_columns)
    timestamp_columns = [col for col, dtype in col_dict.items() if 'TIMESTAMP' == dtype]
    for col in timestamp_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_convert('UTC')
    # cleaning int columns
    int_columns = [col for col, dtype in col_dict.items() if 'INTEGER' == dtype or 'BIGINT' == dtype]
    for col in int_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # add any column to this function call if you know it doesn't have ids
    df = get_dummy_ids(
        df,
        ['ballotpedia_election_id', 'bioguide_id', 'thomas_id',
         'lis_id', 'govtrack_id', 'fec_id', 'maplight_id']
    )
    if table_name == "politician_politician":
        df['middle_name'].replace("\\", "", inplace=True)  # middle_name
        df['gender'].replace(["\\N", ""], "U", inplace=True)  # gender
        df['birth_date'] = pd.to_datetime(df['birth_date'], errors='coerce')
        # clean_row(df, ['twitter_description', 'twitter_location', 'twitter_name', 'ballot_guide_official_statement'])                              # twitter description, twitter_location, twitter_name
    return df


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


# def clean_row(df, cols):
#     for col in cols:
#         df[col] = df[col].replace(['\n',','], ' ', inplace=True)
#         df[col] = df[col].replace(to_replace=r'[^0-9a-zA-Z\. _]', value="", regex=True)
#         df[col] = df[col].str.strip()
#     return df

def clean_bigint_row(row, index):
    if not row[index].isnumeric() and row[index] != '\\N':
        row[index] = 0


def clean_url(row, index):
    if "," in row[index]:
        row[index] = row[index].replace(",", "")


def substitute_null(row, index, sub):
    if row[index] == '\\N' or row[index] == '':
        row[index] = sub


def get_dummy_ids(df, cols):
    for col in cols:
        if col in df.columns:
            # Filter for rows where the column has empty strings, '\N', or '0'
            mask = df[col].replace(['', '\\N', '0'], pd.NA).isna()
            # Check if there are rows that need new IDs
            if mask.any():
                existing_ids = df.loc[~mask, col].dropna().unique()  # Get existing IDs in the column
                max_existing_id = pd.Series(existing_ids).apply(pd.to_numeric,
                                                                errors='coerce').max()  # Get the max existing ID
                next_id = int(max_existing_id) + 1 if pd.notna(max_existing_id) else 1  # Set the next ID
                # Generate new IDs starting from the next available ID
                df.loc[mask, col] = [next_id + i for i in range(mask.sum())]

    return df


def upsert_df(
        df: pd.DataFrame,
        table_name: str,
        col_names: str,
        unique_cols: set,
        pk_col: set,
        engine: sa.engine.Engine):
    """Implements the equivalent of pd.DataFrame.to_sql(..., if_exists='update')
    (which does not exist). Creates or updates the db records based on the
    dataframe records.
    Conflicts to determine update are based on the dataframes index.
    This will set primary keys on the table equal to the index names
    1. Create a temp table from the dataframe
    2. Insert/update from temp table into table_name
    Returns: True if successful
    """
    with engine.connect() as conn:
        # # Repeat the following steps for the all tables with primary key
        # table = "politician_politician"
        # pkey = "id"
        # # Get the serial sequence reference using pg_get_serial_sequence
        # output = pd.read_sql(f"SELECT pg_get_serial_sequence('{table}', '{pkey}');", con=engine)
        # # Set the serial sequence value to the max value of the primary key
        # output = pd.read_sql(f"SELECT setval('{output.iloc[0][0]}', (SELECT MAX({pkey}) FROM {table})+1);",
        #                      con=engine)

        # If the table does not exist, we should just use to_sql to create it
        query_create = sa.text(f"""SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_schema = 'public'
                AND    table_name   = '{table_name}');
                """)
        try:
            if not conn.execute(query_create).first()[0]:
                df.to_sql(table_name, engine)
                return True
        except Exception as e:
            print(f'FAILED_CREATE_TABLE: {table_name} -- {str(e)}')

        # If it already exists...
        try:
            temp_table_name = f"temp_{uuid.uuid4().hex[:6]}"
            df.to_sql(temp_table_name, engine, index=False)
        except Exception as e:
            print(f'FAILED_CREATE_TEMP_TABLE: {table_name} -- {str(e)}')

        columns = list(df.columns)
        # Can add more columns that identify a record. ex = "id, politician_name" or "id, twitter_handle, pol_name"
        unique_cons_cols = ", ".join(f'"{col}"' for col in unique_cols if col in columns)

        # columns to update on conflict
        update_column_stmt = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in pk_col])

        # For the ON CONFLICT clause, postgres requires that the columns have unique constraint
        constraint_exists_query = sa.text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints
                    WHERE table_name = '{table_name}'
                    AND constraint_type = 'UNIQUE'
                );
                """)
        unique_constraints_exist = conn.execute(constraint_exists_query).scalar()

        if unique_constraints_exist and unique_cons_cols:
            query_pk = sa.text(f"""
            ALTER TABLE "{table_name}" ADD CONSTRAINT {table_name}_unique_constraint_for_upsert UNIQUE ({unique_cons_cols});
            """)
            try:
                conn.execute(query_pk)
            except Exception as e:
                # relation "unique_constraint_for_upsert" already exists
                print(f'ADD_UNIQUE_CONSTRAINT_FAIL: {table_name} -- {str(e)}')
                if not 'unique_constraint_for_upsert" already exists' in e.args[0]:
                    raise e

            # Compose upsert query
            query_upsert = sa.text(f"""
            INSERT INTO "{table_name}" ({col_names}) 
            SELECT {col_names} FROM "{temp_table_name}"
            ON CONFLICT ({unique_cons_cols}) DO UPDATE 
            SET {update_column_stmt};
            """)
        else:
            # If no unique constraints, perform a custom upsert
            # Here you might need a custom upsert logic depending on your needs
            query_upsert = sa.text(f"""
                        INSERT INTO "{table_name}" ({col_names})
                        SELECT {col_names} FROM "{temp_table_name}"
                        ON CONFLICT DO NOTHING;  -- No unique constraint to handle conflicts
                        """)
        try:
            conn.execute(query_upsert)
            query_drop = sa.text(f'DROP TABLE "{temp_table_name}"')
            conn.execute(query_drop)
        except Exception as e:
            print(f'UPSERT_FAIL: {table_name} -- {str(e)}')

    return True
