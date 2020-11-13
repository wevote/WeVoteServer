import csv
import json
import os
import psycopg2
import requests
import time
from config.base import get_environment_variable
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_sql_tables_as_csv():
    t0 = time.time()
    files = {
        'candidate_candidatecampaign',
        'candidate_candidatetoofficelink',
        'election_election',
        'measure_contestmeasure',
        'office_contestofficevisitingotherelection',
        'office_contestoffice',
        'politician_politician',
        'polling_location_pollinglocation'
    }

    status = ''

    try:
        conn = psycopg2.connect(
            database=get_environment_variable('DATABASE_NAME'),
            user=get_environment_variable('DATABASE_USER'),
            password=get_environment_variable('DATABASE_PASSWORD'),
            host=get_environment_variable('DATABASE_HOST'),
            port=get_environment_variable('DATABASE_PORT')
        )

        # logger.debug("retrieve_sql_tables_as_csv psycopg2 Connected to DB")

        csv_files = {}
        cur = conn.cursor()
        for table_name in files:
            csv_name = table_name + '.csv'
            with open(csv_name, 'w') as file:
                cur.copy_to(file, table_name, sep='|')
            with open(csv_name, 'r') as file:
                csv_files[table_name] = file.read()
            os.remove(csv_name)
            status += "exported " + table_name + ", "
        conn.commit()
        conn.close()

        results = {
            'status': status,
            'files': csv_files,
        }

        dt = time.time() - t0
        # This takes 0.532 seconds on my mac
        logger.error('Extracting and zipping the 8 tables took ' + "{:.3f}".format(dt) + ' seconds')
        return results

    except Exception as e:
        status += "retrieve_tables export_sync_files_to_csv caught " + str(e)
        logger.error(status)
        results = {
            'status': status,
        }
        return results

def retrieve_sql_files_from_master_server(request, state_code=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    t0 = time.time()
    response = requests.get("https://api.wevoteusa.org/apis/v1/retrieveSQLTables/", params={})
    dt = time.time() - t0
    structured_json = json.loads(response.text)
    logger.debug('Retrieving the 8 tables took ' + "{:.3f}".format(dt) + ' seconds, and retrieved ' +
                 "{:,}".format(len(response.text)) + ' bytes')

    status = ''
    try:
        conn = psycopg2.connect(
            database=get_environment_variable('DATABASE_NAME'),
            user=get_environment_variable('DATABASE_USER'),
            password=get_environment_variable('DATABASE_PASSWORD'),
            host=get_environment_variable('DATABASE_HOST'),
            port=get_environment_variable('DATABASE_PORT')
        )

        logger.debug("retrieve_sql_files_from_master_server psycopg2 Connected to DB")

        csv_files = {}
        cur = conn.cursor()
        for table_name in structured_json['files']:
            print("started " + table_name)
            cur.execute("DELETE FROM " + table_name)
            conn.commit()
            with open(table_name + '.csv', 'w') as csv_file:
                csv_file.write(structured_json['files'][table_name])
            csv_rows = []
            with open(table_name + '.csv', 'r') as csv_file2:
                line_reader = csv.reader(csv_file2, delimiter='|')
                for row in line_reader:
                    if table_name == "candidate_candidatetoofficelink":
                        if row[2] == '':
                            row[2] = '0'    # String
                    if table_name == "election_election":
                        if row[2] == '\\N':
                            print(row)
                            row[2] = '0'      # Integer
                        if row[8] == '\\N':
                            print(row)
                            row[8] = ''
                    if table_name == "politician_politician":
                        if row[7] == '\\N':  # gender
                            print(row)
                            row[7] = 'U'
                    csv_rows.append(row)
            with open(table_name + '2.csv', 'w') as csv_file:
                csvwriter = csv.writer(csv_file)
                for row in csv_rows:
                    csvwriter.writerow(row)
            with open(table_name + '2.csv', 'r') as file:
                sqlstr = "COPY " + table_name + " FROM STDIN DELIMITER ',' CSV"
                cur.copy_expert(sqlstr, file)
            # status += "exported " + table_name + ", "
            print("completed " + table_name)

        conn.commit()
        conn.close()

    except Exception as e:
        status += "retrieve_tables retrieve_sql_files_from_master_server caught " + str(e)
        logger.error(status)
    results = {
        'status': status,
    }
    return results

