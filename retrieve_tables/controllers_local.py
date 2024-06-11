# retrieve_tables/controllers_local.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import csv
import json
import os
import time

import psycopg2
import requests
from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.controllers_master import allowable_tables, dump_row_col_labels_and_errors
from wevote_functions.functions import get_voter_api_device_id

logger = wevote_functions.admin.get_logger(__name__)

# This api will only return the data from the following tables

dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'


def save_off_database():
    file = "WeVoteServerDB-{:.0f}.pgsql".format(time.time())
    os.system('pg_dump WeVoteServerDB > ' + file)
    time.sleep(20)


def update_fast_load_db(host, voter_api_device_id, table_name, additional_records):
    try:
        response = requests.get(host + '/apis/v1/fastLoadStatusUpdate/',
                                verify=True,
                                params={'table_name': table_name,
                                        'additional_records': additional_records,
                                        'is_running': True,
                                        'voter_api_device_id': voter_api_device_id,
                                        })
        # print('update_fast_load_db ', response.status_code, response.url, voter_api_device_id)
    except Exception as e:
        logger.error('update_fast_load_db caught: ', str(e))


def retrieve_sql_files_from_master_server(request):
    """
    Get the json data, and create new entries in the developers local database
    Runs on the Local server (developer's Mac)
    :return:
    """
    status = ''
    t0 = time.time()
    print(
        'Saving off a copy of your local db (an an emergency fallback, that will almost never be needed) in \'WeVoteServerDB-*.pgsql\' files, feel free to delete them at anytime')
    save_off_database()
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
        t1 = time.time()
        dt = 0
        tables_with_too_many_columns = {'candidate_candidatecampaign'}
        gulp_size = 500000 if table_name not in tables_with_too_many_columns else 100000
        start = 0
        end = gulp_size - 1

        final_lines_count = 0
        while end < 20000000:
            t2 = time.time()
            request_count = 0
            wait_for_a_http_200 = True
            response = {}

            while wait_for_a_http_200:
                load_successful = False
                retry = 1
                while not load_successful:
                    base_url = (host + 'apis/v1/retrieveSQLTables/?table_name=' + table_name + '&start=' + str(start) +
                                '&end=' + str(end))
                    try:
                        response = requests.get(host + '/apis/v1/retrieveSQLTables/',
                                                verify=True,
                                                params={'table_name': table_name, 'start': start, 'end': end,
                                                        'voter_api_device_id': voter_api_device_id})
                        print('retrieveSQLTables url: ' + response.url)
                        request_count += 1
                        load_successful = True
                        if response.status_code == 200:
                            wait_for_a_http_200 = False
                        else:
                            print(host + '/apis/v1/retrieveSQLTables/   (failing get response) response.status_code ' +
                                  str(response.status_code) + '  RETRY ---- ' + base_url)
                            continue
                    except Exception as getErr:
                        print(host +
                              '/apis/v1/retrieveSQLTables/   (failing SSL connection err on get) error ' +
                              str(getErr) + '  RETRY #' + str(retry) + '  ---- ' + base_url)
                        retry += 1
                        if retry < 10:
                            continue

            bytes_transferred = len(response.text)
            structured_json = json.loads(response.text)
            if structured_json['success'] is False:
                print("FAILED:  Did not receive '" + table_name + " from server")
                break

            data = structured_json['files'][table_name]
            lines = data.splitlines()
            if len(lines) == 1:
                dt = time.time() - t1
                print('... Retrieved ' + "{:,}".format(final_lines_count) + ' lines from the ' + table_name +
                      ' table (as JSON) in ' + str(int(dt)) + ' seconds)')
                break
            final_lines_count += len(lines)
            print(f'... Intermediate line count from this request of {gulp_size:,} rows, returned {len(lines):,} '
                  f'rows ({bytes_transferred:,} bytes), cumulative lines is {final_lines_count:,}')
            update_fast_load_db(host, voter_api_device_id, table_name, len(lines))

            if len(lines) > 0:
                try:
                    conn = psycopg2.connect(
                        database=get_environment_variable('DATABASE_NAME'),
                        user=get_environment_variable('DATABASE_USER'),
                        password=get_environment_variable('DATABASE_PASSWORD'),
                        host=get_environment_variable('DATABASE_HOST'),
                        port=get_environment_variable('DATABASE_PORT')
                    )

                    cur = conn.cursor()

                    print("... Processing rows " + "{:,}".format(start) + " through " + "{:,}".format(end) +
                          " of table " + table_name + " data received from master server.")
                    if start == 0:
                        cur.execute("DELETE FROM " + table_name)  # Delete all existing data in this table
                        conn.commit()
                        print("... SQL executed: DELETE (all) FROM " + table_name)

                    with open(os.path.join(LOCAL_TMP_PATH, table_name + '.csvTemp'), 'w') as csv_file:
                        for s in lines:
                            csv_file.write("%s\n" % s)
                        csv_file.close()

                    header = csv_file_to_clean_csv_file2(table_name)

                    try:
                        with open(os.path.join(LOCAL_TMP_PATH, table_name + '2.csvTemp'), 'r') as file:
                            cur.copy_from(file, table_name, sep='|', size=16384, columns=header)
                            file.close()
                    except Exception as e0:
                        print("FAILED_TABLE_INSERT: " + table_name + " -- " + str(e0))
                    conn.commit()
                    conn.close()
                    dt = time.time() - t1
                    dt2 = time.time() - t2
                    dtc = time.time() - t0
                    print('... Processing and inserting the chunk of 500k from ' + table_name + ' table took ' +
                          str(int(dt2)) + ' seconds, cumulative ' + str(int(dtc)) + ' seconds')
                    stats |= {table_name: str(int(dtc))}

                except Exception as e:
                    status += "retrieve_tables retrieve_sql_files_from_master_server caught " + str(e)
                    logger.error(status)

                finally:
                    if table_name not in tables_with_too_many_columns:
                        start += 500000
                        end += 500000
                    else:
                        start += 100000
                        end += 100000

        # Update the last_value for this table so creating new entries doesn't
        #  throw "django Key (id)= already exists" error
        try:
            conn = psycopg2.connect(
                database=get_environment_variable('DATABASE_NAME'),
                user=get_environment_variable('DATABASE_USER'),
                password=get_environment_variable('DATABASE_PASSWORD'),
                host=get_environment_variable('DATABASE_HOST'),
                port=get_environment_variable('DATABASE_PORT')
            )

            cur = conn.cursor()
            command = "SELECT setval('" + table_name + "_id_seq', (SELECT MAX(id) FROM \"" + table_name + "\"))"
            cur.execute(command)
            data_tuple = cur.fetchone()
            print("... SQL executed: " + command + " and returned " + str(data_tuple[0]))
            conn.commit()
            if str(data_tuple[0]) != 'None':
                command = "ALTER SEQUENCE " + table_name + "_id_seq START WITH " + str(data_tuple[0])
                cur.execute(command)
                conn.commit()
            conn.close()
            print("... SQL executed: " + command)
            # To confirm:  SELECT * FROM information_schema.sequences where sequence_name like 'org%'

        except Exception as e:
            status += "... SQL FAILED: SELECT setval('" + \
                      table_name + "_id_seq', (SELECT MAX(id) FROM \"" + table_name + "\")): " + str(e)
            logger.error(status)

        status += ", " + " loaded " + table_name
        stat = 'Processing and loading table: ' + table_name + '  took ' + str(int(dt)) + ' seconds'
        print("... " + stat)
        status += stat

    minutes = (time.time() - t0)/60

    for table in stats:
        secs = int(stats[table])
        min1 = int(secs / 60)
        secs1 = int(secs % 60)
        print("Processing and loading table " + table + " ended at " + str(min1) + ":" + str(secs1) + "  cumulative")
    print("Processing and loading grand total " + str(len(allowable_tables)) + " tables took {:.1f}".format(minutes) + ' minutes')

    os.system('rm ' + os.path.join(LOCAL_TMP_PATH, '*.csvTemp'))    # Clean up all the temp files

    results = {
        'status': status,
        'status_code': status,
    }
    return HttpResponse(json.dumps(results), content_type='application/json')


# We don't check every field for garbage, although maybe we should...
# Since the error reporting in the python console is pretty good, you should be able to figure out what field has
# garbage in it.
# Because we export to csv (comma separated values) files, that end up the WeVoterServer root dir, you can stop
# processing with the debugger, open the csv files in Excel, and get a decent view of what is happening.  The diagnostic
# function dump_row_col_labels_and_errors(table_name, header, row, '2000060') also is really good at figuring out what
# field has problems, and it dumps the field numbers and names which helps determine what row processing functions need
# to be added, like 'clean_row(row, 10)                      # ballot_item_display_name'
# The data provided to the developers local is pretty good, but some of the cleanups removes commas, and other niceities
# from text fields.  It should be good enough, and if not, this function is where it can be improved.
# hint: temporarily comment out some lines in allowable_tables, so you can get to the problem table quicker
# hint: Access https://pg.admin.wevote.us/  (view access to the production server Postgres) can really help, ask Dale
def csv_file_to_clean_csv_file2(table_name):
    """
    Runs on the Master server
    """
    csv_rows = []
    with open(os.path.join(LOCAL_TMP_PATH, table_name + '.csvTemp'), 'r') as csv_file2:
        line_reader = csv.reader(csv_file2, delimiter='|')
        header = None

        skipped_rows = '... Skipped rows in ' + table_name + ': '
        for row in line_reader:
            # check_for_non_ascii(table_name, row)
            try:
                if header is None:
                    header = row
                    continue
                if len(header) != len(row) or '|' in str(row):  # Messed up records with '|' in them
                    skipped_rows += row[0] + ", "
                    continue

                if table_name == "ballot_ballotitem":
                    clean_row(row, 10)                      # ballot_item_display_name
                    clean_row(row, 12)                      # measure_subtitle
                    clean_row(row, 14)                      # measure_text
                    clean_row(row, 16)                      # no_vote_description
                    clean_row(row, 17)                      # yes_vote_description
                    # dump_row_col_labels_and_errors(table_name, header, row, '3000150')
                elif table_name == "ballot_ballotreturned":
                    clean_row(row, 6)                       # text_for_map_search
                    substitute_null(row, 7, '0.0')          # latitude
                    substitute_null(row, 8, '0.0')          # longitude
                    # dump_row_col_labels_and_errors(table_name, header, row, '50490')
                elif table_name == "candidate_candidatetoofficelink":
                    if row[1] == '':                        # candidate_we_vote_id
                        continue
                elif table_name == "campaign_campaignx":
                    clean_row(row, 6)                 # campaign_description
                # elif table_name == "campaign_campaignxowner":
                #     dump_row_col_labels_and_errors("campaign_campaignxowner", header, row, '5')
                elif table_name == "campaign_campaignxsupporter":
                    clean_row(row, 6)                 # supporter_endorsement
                    # dump_row_col_labels_and_errors("campaign_campaignxsupporter", header, row, '45')
                elif table_name == "election_election":
                    substitute_null(row, 2, '0')  # google_civic_election_id_new is an integer
                    if row[8] == '' or row[8] == '\\N' or row[8] == '0':
                        row[8] = get_dummy_unique_id()       # ballotpedia_election_id
                    substitute_null(row, 8, '0')            #
                    clean_row(row, 10)                      # internal_notes
                    substitute_null(row, 2, 'f')            # election_preparation_finished
                elif table_name == "politician_politician":
                    row[2] = row[2].replace("\\", "")       # middle_name
                    substitute_null(row, 7, 'U')            # gender
                    substitute_null(row, 8, '\\N')          # birth_date
                    row[9] = get_dummy_unique_id()          # bioguide_id, looks like we don't even use this anymore
                    row[10] = get_dummy_unique_id()         # thomas_id, looks like we don't even use this anymore
                    row[11] = get_dummy_unique_id()         # lis_id, looks like we don't even use this anymore
                    row[12] = get_dummy_unique_id()         # govtrack_id, looks like we don't even use this anymore
                    row[15] = get_dummy_unique_id()         # fec_id, looks like we don't even use this anymore
                    row[19] = get_dummy_unique_id()         # maplight_id, looks like we don't even use this anymore
                    clean_row(row, 52)                      # twitter description
                    clean_row(row, 54)                      # twitter_location
                    clean_row(row, 55)                      # twitter_name
                    clean_row(row, 111)                     # ballot_guide_official_statement
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
                    substitute_null(row, 4, '0')            # google_civic_election_id_new is an integer
                    row[6] = get_dummy_unique_id()          # maplight_id, looks like we don't even use this anymore
                    substitute_null(row, 24, '0')           # ballotpedia_office_id is an integer
                    substitute_null(row, 28, '0')           # ballotpedia_district_id is an integer
                    substitute_null(row, 29, '0')           # ballotpedia_election_id is an integer
                    substitute_null(row, 30, '0')           # ballotpedia_race_id is an integer
                    substitute_null(row, 33, '0')           # google_ballot_placement is an integer
                    substitute_null(row, 40, 'f')           # ballotpedia_is_marquee is a bool
                    substitute_null(row, 41, 'f')           # is_battleground_race is a bool
                elif table_name == "candidate_candidatecampaign":
                    row[2] = get_dummy_unique_id()          # maplight_id, looks like we don't even use this anymore
                    substitute_null(row, 6, '0')            # politician_id
                    clean_row(row, 8)                       # candidate_name |"Elizabeth Nelson ""Liz"" Johnson"|
                    clean_row(row, 9)                       # google_civic_candidate_name
                    clean_row(row, 24)                      # candidate_email
                    substitute_null(row, 28, '0')           # wikipedia_page_id
                    clean_row(row, 32)                      # twitter_description
                    substitute_null(row, 33, '0')           # twitter_followers_count
                    clean_row(row, 34)                      # twitter_location
                    clean_row(row, 35)                      # twitter_name
                    clean_row(row, 36)                      # twitter_profile_background_image_url_https
                    substitute_null(row, 39, '0')           # twitter_user_id
                    clean_row(row, 40)                      # ballot_guide_official_statement
                    clean_row(row, 41)                      # contest_office_name
                    substitute_null(row, 53, '0')           # ballotpedia_candidate_id
                    clean_row(row, 57)                      # ballotpedia_candidate_summary
                    substitute_null(row, 58, '0')           # ballotpedia_election_id
                    substitute_null(row, 59, '0')           # ballotpedia_image_id
                    substitute_null(row, 60, '0')           # ballotpedia_office_id
                    substitute_null(row, 61, '0')           # ballotpedia_person_id
                    substitute_null(row, 62, '0')           # ballotpedia_race_id
                    substitute_null(row, 65, '0')           # crowdpac_candidate_id
                    substitute_null(row, 71, '\\N')         # withdrawal_date
                    substitute_null(row, 75, '0')           # candidate_year
                    substitute_null(row, 76, '0')           # candidate_ultimate_election_date
                    # dump_row_col_labels_and_errors(table_name, header, row, '4441')
                elif table_name == "measure_contestmeasure":
                    row[3] = row[3].replace('\n', '  ')     # measure_title
                    clean_row(row, 4)                       #
                    clean_row(row, 5)                       #
                    clean_row(row, 6)                       # measure_url
                    substitute_null(row, 17, '0')           # wikipedia_page_id is a bigint
                    clean_row(row, 26)                      # ballotpedia_measure_name
                    clean_row(row, 28)                      # ballotpedia_measure_summ
                    clean_row(row, 29)                      # ballotpedia_measure_text
                    clean_row(row, 32)                      # ballotpedia_no_vote_desc
                    clean_row(row, 33)                      # ballotpedia_yes_vote_des
                    substitute_null(row, 34, '0')           # google_ballot_placement is a bigint
                    substitute_null(row, 39, '0')           # measure_year is an integer
                    substitute_null(row, 40, '0')           # measure_ultimate_election_date is an integer
                # elif table_name == 'office_contestofficevisitingotherelection':
                #     pass   # no fixes needed
                elif table_name == 'organization_organization':
                    clean_row(row, 11)                      # organization_description
                    clean_row(row, 12)                      # organization_address
                    substitute_null(row, 23, '0')           # twitter_followers_count
                    clean_row(row, 22)                      # twitter_description
                    substitute_null(row, 31, '0')           # wikipedia_thumbnail_height
                    substitute_null(row, 33, '0')           # wikipedia_thumbnail_width
                    clean_row(row, 47)                      # issue_analysis_admin_notes
                    # dump_row_col_labels_and_errors(table_name, header, row, '1')
                elif table_name == 'position_positionentered':
                    clean_row(row, 4)                       # ballot_item_display_name
                    substitute_null(row, 5, '1970-01-01 00:00:00+00')
                    clean_row(row, 15)                      #
                    clean_row(row, 16)                      # vote_smart_rating_name
                    clean_bigint_row(row, 18)               # contest_office_id
                    clean_row(row, 22)                      # google_civic_candidate_name
                    clean_row(row, 28)                      # statement_text
                    clean_url(row, 30)                      # more_info_url
                    clean_row(row, 37)                      # speaker_display_name
                    clean_row(row, 43)                      # google_civic_measure_title
                    clean_row(row, 44)                      # contest_office_name
                    clean_row(row, 45)                      # political_party
                    # dump_row_col_labels_and_errors(table_name, header, row, '33083')
                elif table_name == 'voter_guide_voterguidepossibility':
                    clean_url(row, 1)                       # voter_guide_possibility_url
                    clean_row(row, 5)                       # ballot_items_raw
                    clean_row(row, 6)                       # organization_name
                    clean_row(row, 7)                       # organization_twitter_handle
                    clean_row(row, 11)                      # internal_notes
                    clean_row(row, 20)                      # contributor_comments
                    clean_row(row, 22)                      # candidate_name
                    # dump_row_col_labels_and_errors(table_name, header, row, '4')
                elif table_name == 'voter_guide_voterguidepossibilityposition':
                    substitute_null(row, 1, '0')            # voter_guide_possibility_parent_id
                    substitute_null(row, 2, '0')            # possibility_position_number
                    clean_row(row, 3)                       # ballot_item_name
                    clean_row(row, 4)                       # candidate_we_vote_id
                    clean_row(row, 5)                       # position_we_vote_id
                    clean_row(row, 6)                       # measure_we_vote_id
                    clean_row(row, 7)                       # statement_text
                    substitute_null(row, 8, '0')            # google_civic_election_id
                    clean_url(row, 10)                      # more_info_url
                    clean_row(row, 13)                      # candidate_twitter_handle
                    clean_row(row, 14)                      # organization_name
                    clean_row(row, 15)                      # organization_twitter_handle
                    clean_row(row, 16)                      # organization_we_vote_id
                    # dump_row_col_labels_and_errors(table_name, header, row, '4')
                elif table_name == 'voter_guide_voterguide':
                    clean_row(row, 14)                      # twitter_description
                    # dump_row_col_labels_and_errors(table_name, header, row, '3482')
                elif table_name == 'representative_representative':
                    clean_row(row, 18)                  # 'twitter_location'
                    clean_row(row, 23)                  # 'twitter_description'
                csv_rows.append(row)
            except Exception as e:
                logger.error("csv_file_to_clean_csv_file2 (" + table_name + ") caught " + str(e))

        csv_file2.close()
        if ',' in skipped_rows:
            print(skipped_rows + ' were skipped since they had pipe characters in the data')

    with open(os.path.join(LOCAL_TMP_PATH, table_name + '2.csvTemp'), 'w') as csv_file:
        csvwriter = csv.writer(csv_file, delimiter='|')
        for row in csv_rows:
            csvwriter.writerow(row)
    csv_file.close()
    return header


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


def clean_row(row, index):
    newstring = row[index].replace('\n', ' ').replace(',', ' ')
    newstring = ''.join(ch for ch in newstring if ch.isdigit() or ch.isalnum() or ch == ' ' or ch == '.' or ch == '_')
    row[index] = newstring.strip()


def clean_bigint_row(row, index):
    if not row[index].isnumeric() and row[index] != '\\N':
        row[index] = 0


def clean_url(row, index):
    if "," in row[index]:
        # ','' is technically valid in a URL, but is a reserved char, can mess up some ".xml" urls, but "ok" for
        # developer data
        row[index] = row[index].replace(",", "")


def substitute_null(row, index, sub):
    if row[index] == '\\N' or row[index] == '':
        row[index] = sub


def get_dummy_unique_id():
    global dummy_unique_id
    dummy_unique_id += 1
    return str(dummy_unique_id)
