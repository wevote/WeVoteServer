import csv
import json
import os
import re
import time
from io import StringIO

import psycopg2
import requests
from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

# This api will only return the data from the following tables
# Creating CampaignX's locally seems to be best testing strategy
# 'campaign_campaignx',
# 'campaign_campaignxlistedbyorganization',
# 'campaign_campaignxnewsitem',
# 'campaign_campaignx_politician',
# 'campaign_campaignxseofriendlypath',
allowable_tables = [
    'candidate_candidatecampaign',
    'candidate_candidatesarenotduplicates',
    'candidate_candidatetoofficelink',
    'elected_office_electedoffice',
    'elected_official_electedofficial',
    'elected_official_electedofficialsarenotduplicates',
    'election_ballotpediaelection',
    'election_election',
    'electoral_district_electoraldistrict',
    # 'electoral_district_electoraldistrictlinktopollinglocation',
    'issue_issue',
    'issue_organizationlinktoissue',
    'measure_contestmeasure',
    'measure_contestmeasuresarenotduplicates',
    'office_contestoffice',
    'office_contestofficesarenotduplicates',
    'office_contestofficevisitingotherelection',
    'organization_organization',
    'organization_organizationreserveddomain',
    'party_party',
    'politician_politician',
    'politician_politiciansarenotduplicates',
    'polling_location_pollinglocation',
    'position_positionentered',
    'twitter_twitterlinktoorganization',
    'voter_guide_voterguidepossibility',
    'voter_guide_voterguidepossibilityposition',
    'voter_guide_voterguide',
    'wevote_settings_wevotesetting',
    'ballot_ballotitem',
    'ballot_ballotreturned',
]

dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'


def retrieve_sql_tables_as_csv(table_name, start, end):
    """
    Extract one of the 15 allowable database tables to CSV (pipe delimited) and send it to the
    developer's local WeVoteServer instance
    limit is used to specify a number of rows to return (this is the SQL LIMIT clause), non-zero or ignored
    offset is used to specify the first row to return (this is the SQL OFFSET clause), non-zero or ignored
    """
    t0 = time.time()

    status = ''

    f = open("requirements.txt", "r")
    for line in f:
        if "psycopg2" in line:
            logger.error("experiment 20: psycopg2: " + line.strip())

    try:
        conn = psycopg2.connect(
            database=get_environment_variable('DATABASE_NAME'),
            user=get_environment_variable('DATABASE_USER'),
            password=get_environment_variable('DATABASE_PASSWORD'),
            host=get_environment_variable('DATABASE_HOST'),
            port=get_environment_variable('DATABASE_PORT')
        )

        # logger.debug("retrieve_sql_tables_as_csv psycopg2 Connected to DB")

        try:
            # Simple copy experiment
            sql = 'COPY "election_election" TO STDOUT;'
            logger.error("experiment 20: SIMPLIFIED11 sql: " + sql)
            file = StringIO()  # Empty file
            cur = conn.cursor()
            cur.copy_expert(sql, file, size=8192)
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED11 select some stuff: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED11 select some stuff retrieve_sql_tables_as_csv(): " + str(e) + " ")

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = 'COPY "party_party" TO STDOUT'
            logger.error("experiment 20: SIMPLIFIED10 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED10 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED10 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED10: " + str(e))

        # Works to here

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = 'COPY "public"."party_party" TO STDOUT'
            logger.error("experiment 20: SIMPLIFIED9 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED9 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED9 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED9: " + str(e))


        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = "COPY (SELECT * FROM \"public\".\"party_party\" WHERE id BETWEEN " + start + " AND " + \
                  end + " ORDER BY id) TO STDOUT"

            sql = "COPY \"candidate_candidatecampaign\" TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED8 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED8 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED8 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED8: " + str(e))

        # Fails in next block

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = "COPY \"candidate_candidatecampaign\" TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED7 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED7 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED7 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED7: " + str(e))

        try:
            # Simple copy experiment
            sql = 'COPY "public"."election_election" TO STDOUT;'
            logger.error("experiment 20: SIMPLIFIED6 retrieve_tables sql: " + sql)
            file = StringIO()  # Empty file
            cur = conn.cursor()
            cur.copy_expert(sql, file, size=8192)
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED6: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED6: " + str(e) + " ")

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = "COPY \"public\".\"candidate_candidatecampaign\" TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED5 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED5 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED5 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED5: " + str(e))

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = "COPY \"public\".\"candidate_candidatecampaign\" TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED4 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED4 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED4 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED4: " + str(e))

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = "COPY public.candidate_candidatecampaign TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED3 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED3 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED3 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED3: " + str(e))

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            sql = "COPY (SELECT * FROM public.candidate_candidatecampaign) TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED2 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED2 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED2 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED2: " + str(e))

        try:
            cur = conn.cursor()
            file = StringIO()  # Empty file
            if positive_value_exists(end):
                sql = "COPY (SELECT * FROM \"public\".\"" + table_name + "\" WHERE id BETWEEN " + start + " AND " + \
                      end + " ORDER BY id) TO STDOUT"
                # sql = "COPY (SELECT * FROM public." + table_name + " WHERE id BETWEEN " + start + " AND " + \
                #       end + " ORDER BY id) TO STDOUT"
            else:
                sql = "COPY " + table_name + " TO STDOUT"
            logger.error("experiment 20: SIMPLIFIED1 retrieve_tables sql: " + sql)
            cur.copy_expert(sql, file, size=8192)
            logger.error("experiment 20: SIMPLIFIED1 after cur.copy_expert ")
            file.seek(0)
            logger.error("experiment 20: SIMPLIFIED1 retrieve_tables file contents: " + file.readline().strip())
        except Exception as e:
            logger.error("Real exception in SIMPLIFIED: " + str(e))

        csv_files = {}
        if table_name in allowable_tables:
            try:
                cur = conn.cursor()
                file = StringIO()  # Empty file

                logger.error("experiment 20: file: " + str(file))
                if positive_value_exists(end):
                    sql = "COPY (SELECT * FROM public." + table_name + " WHERE id BETWEEN " + start + " AND " + \
                          end + " ORDER BY id) TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                else:
                    sql = "COPY " + table_name + " TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                logger.error("experiment 20: retrieve_tables sql: " + sql)
                cur.copy_expert(sql, file, size=8192)
                logger.error("experiment 20: after cur.copy_expert ")
                file.seek(0)
                logger.error("experiment 20: retrieve_tables file contents: " + file.readline().strip())
                file.seek(0)
                csv_files[table_name] = file.read()
                file.close()
                logger.error("experiment 20: after file close, status " + status)
                if "exported" not in status:
                    status += "exported "
                status += table_name + "(" + start + "," + end + "), "
                logger.error("experiment 20: after status +=, " + status)
                logger.error("experiment 20: before conn.commit")
                conn.commit()
                logger.error("experiment 20: after conn.commit ")
                conn.close()
                logger.error("experiment 20: after conn.close ")
                dt = time.time() - t0
                logger.error('Extracting the "' + table_name + '" table took ' + "{:.3f}".format(dt) +
                             ' seconds.  start = ' + start + ', end = ' + end)
            except Exception as e:
                logger.error("Real exception in retrieve_sql_tables_as_csv(): " + str(e) + " ")
        else:
            status = "the table_name '" + table_name + "' is not in the table list, therefore no table was returned"
            logger.error(status)

        logger.error("experiment 20: before results")
        results = {
            'success': True,
            'status': status,
            'files': csv_files,
        }

        logger.error("experiment 20: results: " + str(results))
        return results

    except Exception as e:
        status += "retrieve_tables export_sync_files_to_csv caught " + str(e)
        logger.error(status)
        logger.error("retrieve_tables export_sync_files_to_csv caught " + str(e))
        results = {
            'success': False,
            'status': status,
        }
        return results


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


def get_dummy_unique_id():
    global dummy_unique_id
    dummy_unique_id += 1
    return str(dummy_unique_id)


def save_off_database():
    file = "WeVoteServerDB-{:.0f}.pgsql".format(time.time())
    os.system('pg_dump WeVoteServerDB > ' + file)
    time.sleep(20)


def retrieve_sql_files_from_master_server(request):
    """
    Get the json data, and create new entries in the developers local database
    :return:
    """
    status = ''
    t0 = time.time()

    save_off_database()

    for table_name in allowable_tables:
        print('Starting on the ' + table_name + ' table, requesting up to 1,000,000 rows')
        # if table_name != 'ballot_ballotitem':
        #     continue
        t1 = time.time()
        dt = 0
        start = 0
        end = 999999
        final_lines_count = 0
        while end < 20000000:
            t2 = time.time()
            # To test locally call https://wevotedeveloper.com:8000/apis/v1/retrieveSQLTables/?table=election_election
            response = requests.get("https://api.wevoteusa.org/apis/v1/retrieveSQLTables/",
                                    params={'table': table_name, 'start': start, 'end': end})
            structured_json = json.loads(response.text)
            if structured_json['success'] is False:
                print("FAILED:  Did not receive '" + table_name + " from server")
                break

            data = structured_json['files'][table_name]
            lines = data.splitlines()
            if len(lines) == 1:
                dt = time.time() - t1
                print('... Retrieved ' + str(final_lines_count) + ' lines from the ' + table_name +
                      ' table (as JSON) in ' + str(int(dt)) + ' seconds)')
                break
            final_lines_count += len(lines)
            print('... Intermediate line count from this request of 1M, returned ' + str(len(lines)) +
                  " rows, cumulative is " + str(final_lines_count))

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

                    print("... Processing rows " + str(start) + " through " + str(end) + " of table " + table_name +
                          " data received from master server.")
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
                    print('... Processing and inserting the chunk of 1M from ' + table_name + ' table took ' +
                          str(int(dt2)) + ' seconds, cumulative ' + str(int(dtc)) + ' seconds')

                except Exception as e:
                    status += "retrieve_tables retrieve_sql_files_from_master_server caught " + str(e)
                    logger.error(status)

                finally:
                    start += 1000000
                    end += 1000000

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
    print("Processing and loading " + str(len(allowable_tables)) + " tables took {:.1f}".format(minutes) + ' minutes')

    os.system('rm ' + os.path.join(LOCAL_TMP_PATH, '*.csvTemp'))    # Clean up all the temp files

    results = {
        'status': status,
        'status_code': status,
    }
    return HttpResponse(json.dumps(results), content_type='application/json')


# We don't check every field for garbage, although maybe we should...
# Since the error reporting in the python console is pretty good, you should be able to figure out what field has
# garbage in it.
# Because we export to csv (comma separated values) files, that end up the the WeVoterServer root dir, you can stop
# processing with the debugger, open the csv files in Excel, and get a decent view of what is happening.  The diagnostic
# function dump_row_col_labels_and_errors(table_name, header, row, '2000060') also is really good at figuring out what
# field has problems, and it dumps the field numbers and names which helps determine what row processing functions need
# to be added, like 'clean_row(row, 10)                      # ballot_item_display_name'
# The data provided to the developers local is pretty good, but some of the cleanups removes commas, and other niceities
# from text fields.  It should be good enough, and if not, this function is where it can be improved.
# hint: temporarily comment out some lines in allowable_tables, so you can get to the problem table quicker
# hint: Access https://pg.admin.wevote.us/  (view access to the production server Postgres) can really help, ask Dale
def csv_file_to_clean_csv_file2(table_name):
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
