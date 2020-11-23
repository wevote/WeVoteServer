import csv
import json
import os
import psycopg2
import requests
import time
from config.base import get_environment_variable
from django.http import HttpResponse
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_sql_tables_as_csv():
    """
    Extract the 15 database tables to CSV (pipe delimited) and send it to the developer's local WeVoteServer instance
    :return:
    """
    t0 = time.time()
    tables = {
        'ballot_ballotitem',
        'ballot_ballotreturned',
        'candidate_candidatecampaign',
        'candidate_candidatetoofficelink',
        'election_election',
        'issue_issue',
        'issue_organizationlinktoissue',
        'measure_contestmeasure',
        'office_contestoffice',
        'office_contestofficevisitingotherelection',
        'organization_organization',
        'politician_politician',
        'polling_location_pollinglocation',
        'position_positionentered',
        'voter_guide_voterguide'
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
                sql = "COPY " + table_name + " TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N' "  # Option+z = Ω
                cur.copy_expert(sql, file, size=8192)
                logger.error("retrieve_tables sql: " + sql)
            file.close()
            with open(csv_name, 'r') as file2:
                csv_files[table_name] = file2.read()
            file2.close()
            logger.error("retrieve_tables removing: " + csv_name)
            os.remove(csv_name)
            status += "exported " + table_name + ", "
        conn.commit()
        conn.close()

        # with open("steve.json", 'w') as filej:
        #     filej.write(json.dumps(csv_files))
        #     filej.close()

        results = {
            'status': status,
            'files': csv_files,
        }

        dt = time.time() - t0
        # This takes 0.532 seconds on my mac
        logger.error('Extracting and zipping the ' + str(len(tables)) + ' tables took ' + "{:.3f}".format(dt) +
                     ' seconds')
        return results

    except Exception as e:
        status += "retrieve_tables export_sync_files_to_csv caught " + str(e)
        logger.error(status)
        logger.error("retrieve_tables export_sync_files_to_csv caught " + str(e))
        results = {
            'status': status,
        }
        return results


def clean_row(row, index):
    row[index] = ''.join(ch for ch in row[index] if ch != '\n' and ch != '\r' and ch != '\"')


def substitute_null(row, index, sub):
    if row[index] == '\\N' or row[index] == '':
        row[index] = sub


def retrieve_sql_files_from_master_server(request, state_code=''):
    """
    Get the json data, and create new entries in the developers local database
    :return:
    """
    t0 = time.time()
    response = requests.get("https://api.wevoteusa.org/apis/v1/retrieveSQLTables/", params={})
    dt = time.time() - t0
    structured_json = json.loads(response.text)
    count = 'ZERO'
    if 'files' in structured_json:
        count = str(len(structured_json['files']))
    print('Retrieving the ' + count + ' tables (as JSON) took ' + "{:.3f}".format(dt) +
          ' seconds, and retrieved ' + "{:,}".format(len(response.text)) + ' bytes')

    status = ''
    if 'files' in structured_json:
        try:
            conn = psycopg2.connect(
                database=get_environment_variable('DATABASE_NAME'),
                user=get_environment_variable('DATABASE_USER'),
                password=get_environment_variable('DATABASE_PASSWORD'),
                host=get_environment_variable('DATABASE_HOST'),
                port=get_environment_variable('DATABASE_PORT')
            )

            print("retrieve_sql_files_from_master_server psycopg2 Connected to DB")

            cur = conn.cursor()

            for table_name in structured_json['files']:
                print("Started processing " + table_name + " data from master server.")
                cur.execute("DELETE FROM " + table_name)  # Delete all existing data in this one of eight tables
                conn.commit()
                with open(table_name + '.csv', 'w') as csv_file:
                    csv_file.write(structured_json['files'][table_name])
                    csv_file.close()
                csv_rows = []
                with open(table_name + '.csv', 'r') as csv_file2:
                    line_reader = csv.reader(csv_file2, delimiter='|')
                    header = None
                    dummy_unique_id = 0
                    skipped_rows = 'Skipped rows in ' + table_name + ': '
                    for row in line_reader:
                        if header is None:
                            header = row
                            continue
                        # Messed up records with '|' in them
                        if len(header) != len(row) or '|' in str(row):
                            skipped_rows += row[0] + ", "
                            continue
                        if table_name == "candidate_candidatetoofficelink":
                            if row[1] == '':                # candidate_we_vote_id
                                continue
                        elif table_name == "election_election":
                            substitute_null(row, 2, '0')    # google_civic_election_id_new is an integer
                            if row[8] == '':
                                dummy_unique_id += 1
                                row[8] = str(dummy_unique_id)  # ballotpedia_election_id
                            substitute_null(row, 8, '0')    #
                            clean_row(row, 10)              # internal_notes
                            substitute_null(row, 2, 'f')    # election_preparation_finished
                        elif table_name == "politician_politician":
                            row[2] = row[2].replace("\\", "")  # middle_name
                            substitute_null(row, 7, 'U')    # gender
                            substitute_null(row, 8, '\\N')  # birth_date
                            dummy_unique_id += 1
                            row[9] = str(dummy_unique_id)   # bioguide_id, looks like we don't even use this anymore
                            row[10] = str(dummy_unique_id)  # thomas_id, looks like we don't even use this anymore
                            row[11] = str(dummy_unique_id)  # lis_id, looks like we don't even use this anymore
                            row[12] = str(dummy_unique_id)  # govtrack_id, looks like we don't even use this anymore
                            row[15] = str(dummy_unique_id)  # fec_id, looks like we don't even use this anymore
                            row[19] = str(dummy_unique_id)  # maplight_id, looks like we don't even use this anymore
                        elif table_name == "polling_location_pollinglocation":
                            clean_row(row, 2)                       # location_name
                            row[2] = row[2].replace("\\", "")       # 'BIG BONE STATE PARK GARAGE BLDG\\'
                            clean_row(row, 3)                       # polling_hours_text
                            clean_row(row, 4)                       # directions_text
                            clean_row(row, 5)                       # line1
                            clean_row(row, 6)                       # line2
                            substitute_null(row, 11, '0.00001')     # latitude
                            substitute_null(row, 12, '0.00001')     # longitude
                            substitute_null(row, 14, '\\N')         # google_response_address_not_found
                        elif table_name == "office_contestoffice":
                            # print(str(row))
                            substitute_null(row, 4, '0')    # google_civic_election_id_new is an integer
                            dummy_unique_id += 1
                            row[6] = str(dummy_unique_id)   # maplight_id, looks like we don't even use this anymore
                            substitute_null(row, 24, '0')   # ballotpedia_office_id is an integer
                            substitute_null(row, 28, '0')   # ballotpedia_district_id is an integer
                            substitute_null(row, 29, '0')   # ballotpedia_election_id is an integer
                            substitute_null(row, 30, '0')   # ballotpedia_race_id is an integer
                            substitute_null(row, 33, '0')   # google_ballot_placement is an integer
                            substitute_null(row, 40, 'f')   # ballotpedia_is_marquee is a bool
                            substitute_null(row, 41, 'f')   # is_battleground_race is a bool
                        elif table_name == "candidate_candidatecampaign":
                            dummy_unique_id += 1
                            row[2] = str(dummy_unique_id)   # maplight_id, looks like we don't even use this anymore
                            substitute_null(row, 6, '0')    # politician_id
                            clean_row(row, 8)               # candidate_name |"Elizabeth Nelson ""Liz"" Johnson"|
                            clean_row(row, 9)               # google_civic_candidate_name
                            clean_row(row, 24)              # candidate_email
                            substitute_null(row, 28, '0')   # wikipedia_page_id
                            clean_row(row, 32)              # twitter_description
                            substitute_null(row, 33, '0')   # twitter_followers_count
                            clean_row(row, 34)              # twitter_location
                            clean_row(row, 35)              # twitter_name
                            clean_row(row, 36)              # twitter_profile_background_image_url_https
                            substitute_null(row, 39, '0')   # twitter_user_id
                            clean_row(row, 40)              # ballot_guide_official_statement
                            clean_row(row, 41)              # contest_office_name
                            substitute_null(row, 53, '0')   # ballotpedia_candidate_id
                            clean_row(row, 57)              # ballotpedia_candidate_summary
                            substitute_null(row, 58, '0')   # ballotpedia_election_id
                            substitute_null(row, 59, '0')   # ballotpedia_image_id
                            substitute_null(row, 60, '0')   # ballotpedia_office_id
                            substitute_null(row, 61, '0')   # ballotpedia_person_id
                            substitute_null(row, 62, '0')   # ballotpedia_race_id
                            substitute_null(row, 65, '0')   # crowdpac_candidate_id
                            substitute_null(row, 71, '\\N')  # withdrawal_date
                            substitute_null(row, 75, '0')   # candidate_year
                            substitute_null(row, 76, '0')   # candidate_ultimate_election_date
                            # if row[0] == '4261':
                            #     elcnt = 0
                            #     for element in header:
                            #         print(table_name + "." + element + " [" + str(elcnt) + "]: " + row[elcnt])
                            #         elcnt += 1
                        elif table_name == "measure_contestmeasure":
                            row[3] = row[3].replace('\n', '  ')  # measure_title
                            clean_row(row, 4)  #
                            clean_row(row, 5)  #
                            clean_row(row, 6)  # measure_url
                            substitute_null(row, 17, '0')  # wikipedia_page_id is a bigint
                            clean_row(row, 26)  # ballotpedia_measure_name
                            clean_row(row, 28)  # ballotpedia_measure_summ
                            clean_row(row, 29)  # ballotpedia_measure_text
                            clean_row(row, 32)  # ballotpedia_no_vote_desc
                            clean_row(row, 33)  # ballotpedia_yes_vote_des
                            substitute_null(row, 34, '0')  # google_ballot_placement is a bigint
                            substitute_null(row, 39, '0')  # measure_year is an integer
                            substitute_null(row, 40, '0')  # measure_ultimate_election_date is an integer
                        # elif table_name == 'office_contestofficevisitingotherelection':
                        #     pass   # no fixes needed
                        # if table_name == "measure_contestmeasure":
                        #     pass # no fixes needed
                        csv_rows.append(row)
                    csv_file2.close()
                    if ',' in skipped_rows:
                        print(skipped_rows + ' were skipped since they had pipe characters in the data')
                with open(table_name + '2.csv', 'w') as csv_file:
                    csvwriter = csv.writer(csv_file, delimiter='|')
                    for row in csv_rows:
                        csvwriter.writerow(row)
                csv_file.close()
                try:
                    with open(table_name + '2.csv', 'r') as file:
                        cur.copy_from(file, table_name, sep='|', size=16384, columns=header)
                        file.close()
                    print("... Table " + table_name + " was overwritten with data from the master server.")
                except Exception as e0:
                    print("FAILED " + table_name + " -- " + str(e0))
                conn.commit()
                conn.close()
                dt = time.time() - t0
                print('Processing and loading the 8 tables took ' + "{:.3f}".format(dt) + ' seconds')
                status += 'Processing and loading the 8 tables took ' + "{:.3f}".format(dt) + ' seconds'

        except Exception as e:
            status += "retrieve_tables retrieve_sql_files_from_master_server caught " + str(e)
            logger.error(status)
    else:
        status = "Received zero files from server"

    results = {
        'status': status,
        'status_code': status,
    }
    return HttpResponse(json.dumps(results), content_type='application/json')
