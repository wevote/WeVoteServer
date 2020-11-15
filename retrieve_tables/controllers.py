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
    tables = {
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
        for table_name in tables:
            csv_name = table_name + '.csv'
            print("exporting to: " + csv_name)
            with open(csv_name, 'w') as file:
                # cur.copy_to(file, table_name, sep="|")
                sql = "COPY " + table_name + " TO STDOUT WITH CSV DELIMITER '|' HEADER "
                cur.copy_expert(sql, file, size=8192)
            file.close()
            with open(csv_name, 'r') as file2:
                csv_files[table_name] = file2.read()
            file2.close()
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
            print("All rows deleted from local table: " + table_name)
            with open(table_name + '.csv', 'w') as csv_file:
                csv_file.write(structured_json['files'][table_name])
                csv_file.close()
            csv_rows = []
            with open(table_name + '.csv', 'r') as csv_file2:
                line_reader = csv.reader(csv_file2, delimiter='|')
                for row in line_reader:
                    if table_name == "candidate_candidatetoofficelink":
                        if row[2] == '':    # contest_office_we_vote_id is an integer
                            row[2] = '0'
                    if table_name == "election_election":
                        continue
                        if row[2] == '\\N':  # google_civic_election_id_new is an integer
                            row[2] = '0'
                        if row[8] == '\\N':
                            row[8] = ''

                        row[3] = "stevenospaces3"
                        row[5] = "steveocd5"

                    if table_name == "politician_politician":
                        if row[7] == '\\N':  # gender
                            row[7] = 'U'
                    if table_name == "polling_location_pollinglocation":
                        continue
                        if row[14] == '\\N':  # google_response_address_not_found is a (yuck) integer
                            # print(row)
                            row[14] = '0'
                            # print(row)
                    if table_name == "office_contestoffice":
                        # if "va" in row:
                        #     continue
                        if row[5] == '\\N':  # google_civic_election_id_new is an integer
                            row[5] = '0'
                        if row[24] == '\\N':  # ballotpedia_office_id is an integer
                            row[24] = '0'
                        if row[28] == '\\N':  # ballotpedia_district_id is an integer
                            row[28] = '0'
                        if row[29] == '\\N':  # ballotpedia_election_id is an integer
                            row[29] = '0'
                        if row[30] == '\\N':  # ballotpedia_race_id is an integer
                            row[30] = '0'
                        if row[33] == '\\N':  # google_ballot_placement is an integer
                            row[33] = '0'
                        if row[40] == '\\N':  # google_ballot_placement is a bool
                            row[40] = 'f'
                        if row[41] == '\\N':  # is_battleground_race is a bool
                            row[41] = 'f'
                    if table_name == "candidate_candidatecampaign":
                        #  has 4 urls
                        continue
                    if table_name == "office_contestoffice":
                        continue
                        row[6] = 'urlsteve6'
                        row[9] = 'ocdsteve9'
                        row[12] = 'ocdsteve12'
                    if table_name == "measure_contestmeasure":
                        # continue
                        row[6] = 'urlsteve6'
                        row[30] = 'urlsteve30'
                        row[9] = 'ocdsteve9'
                    csv_rows.append(row)
                csv_file2.close()
            with open(table_name + '2.csv', 'w') as csv_file:
                csvwriter = csv.writer(csv_file, delimiter='|')
                for row in csv_rows:
                    csvwriter.writerow(row)
            csv_file.close()
            try:
                with open(table_name + '2.csv', 'r') as file:
                    cur.copy_from(file, table_name, sep='|', size=16384)
                    file.close()
                print("completed " + table_name)
            except Exception as e0:
                logger.error("FAILED " + table_name + " -- " + str(e0))
                print("FAILED " + table_name + " -- " + str(e0))
        conn.commit()
        conn.close()

    except Exception as e:
        status += "retrieve_tables retrieve_sql_files_from_master_server caught " + str(e)
        logger.error(status)
    results = {
        'status': status,
    }
    return results

