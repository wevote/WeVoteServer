import csv
import json
import os
import psycopg2
import requests
import time
from config.base import get_environment_variable
from django.http import HttpResponse
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

# This api will only return the data from the following tables
allowable_tables = {
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


def retrieve_sql_tables_as_csv(table_name, start, end):
    """
    Extract one of the 15 allowable database tables to CSV (pipe delimited) and send it to the
    developer's local WeVoteServer instance
    limit is used to specify a number of rows to return (this is the SQL LIMIT clause), non-zero or ignored
    offset is used to specify the first row to return (this is the SQL OFFSET clause), non-zero or ignored
    """
    t0 = time.time()

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
        if table_name in allowable_tables:
            cur = conn.cursor()
            csv_name = table_name + '.csv'
            print("exporting to: " + csv_name)
            with open(csv_name, 'w') as file:
                if positive_value_exists(end):
                    # SELECT * FROM public.ballot_ballotitem WHERE id BETWEEN 0 AND 1000 ORDER BY id;
                    sql = "COPY (SELECT * FROM public." + table_name + " WHERE id BETWEEN " + start + " AND " + end +\
                          " ORDER BY id) TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                else:
                    sql = "COPY " + table_name + " TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                cur.copy_expert(sql, file, size=8192)
                logger.error("retrieve_tables sql: " + sql)
            file.close()
            with open(csv_name, 'r') as file2:
                csv_files[table_name] = file2.read()
            file2.close()
            # logger.error("retrieve_tables removing: " + csv_name)
            os.remove(csv_name)
            if "exported" not in status:
                status += "exported "
            status += table_name + "(" + start + "," + end + "), "
            conn.commit()
            conn.close()
            dt = time.time() - t0
            logger.error('Extracting the "' + table_name + '" table took ' + "{:.3f}".format(dt) +
                         ' seconds.  start = ' + start + ', end = ' + end)
        else:
            status = "the table_name '" + table_name + "' is not in the table list, therefore no table was returned"
            logger.error(status)

        results = {
            'success': True,
            'status': status,
            'files': csv_files,
        }

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
    row[index] = ''.join(ch for ch in row[index] if ch != '\n' and ch != '\r' and ch != '\"')


def substitute_null(row, index, sub):
    if row[index] == '\\N' or row[index] == '':
        row[index] = sub


def dump_row_col_labels_and_errors(table_name, header, row, index):
    if row[0] == index:
        cnt = 0
        for element in header:
            print(table_name + "." + element + " [" + str(cnt) + "]: " + row[cnt])
            cnt += 1


def retrieve_sql_files_from_master_server(request):
    """
    Get the json data, and create new entries in the developers local database
    :return:
    """
    status = ''
    for table_name in allowable_tables:
        t1 = time.time()
        start = 0
        end = 0
        bytes_in = 0
        final_lines = []
        header = None
        while end < 10000000:
            end += 1000000
            response = requests.get("https://api.wevoteusa.org/apis/v1/retrieveSQLTables/",
                                    params={'table': table_name, 'start': start, 'end': end})
            bytes_in = len(response.text)
            start += 1000000
            structured_json = json.loads(response.text)
            if header is None and structured_json['success'] is False:
                print("FAILED:  Did not receive '" + table_name + " from server")
                break

            if structured_json['success'] is True:
                data = structured_json['files'][table_name]
                lines = data.splitlines()
                print('len lines = ' + str(len(lines)))
                if len(lines) == 1:
                    print('... end of lines found')
                    break
                if not positive_value_exists(header):
                    header = lines[0]
                else:
                    lines.remove(lines[0])
                final_lines = final_lines + lines
        print('final_lines len = ' + str(len(final_lines)))
        dt = time.time() - t1

        if len(final_lines) > 0:
            print('Retrieved the ' + table_name + ' table (as JSON) in ' + "{:.3f}".format(dt) +
                  ' seconds, and retrieved ' + "{:,}".format(bytes_in) + ' bytes')

            try:
                conn = psycopg2.connect(
                    database=get_environment_variable('DATABASE_NAME'),
                    user=get_environment_variable('DATABASE_USER'),
                    password=get_environment_variable('DATABASE_PASSWORD'),
                    host=get_environment_variable('DATABASE_HOST'),
                    port=get_environment_variable('DATABASE_PORT')
                )
    
                # print("retrieve_sql_files_from_master_server psycopg2 Connected to DB")
    
                cur = conn.cursor()
    
                print("... Started processing " + table_name + " data from master server.")
                cur.execute("DELETE FROM " + table_name)  # Delete all existing data in this one of 15 allowable_tables
                conn.commit()
                with open(table_name + '.csv', 'w') as csv_file:
                    csv_file.write(header)
                    csv_file.write(final_lines)
                    csv_file.close()

                csv_file_to_clean_csv_file2(table_name)

                try:
                    with open(table_name + '2.csv', 'r') as file:
                        cur.copy_from(file, table_name, sep='|', size=16384, columns=header)
                        file.close()
                    # print("... Table " + table_name + " was overwritten with data from the master server.")
                except Exception as e0:
                    print("FAILED " + table_name + " -- " + str(e0))
                conn.commit()
                conn.close()
                dt = time.time() - t1
                print('... Processing and overwriting the ' + table_name + ' table took ' + "{:.3f}".format(dt) +
                      ' seconds')
                status += ", " + " loaded " + table_name
                stat = 'Processing and loading the ' + str(len(allowable_tables)) + ' tables took ' +\
                       "{:.3f}".format(dt) + ' seconds'
                print(stat)
                status += stat

            except Exception as e:
                status += "retrieve_tables retrieve_sql_files_from_master_server caught " + str(e)
                logger.error(status)

    results = {
        'status': status,
        'status_code': status,
    }
    return HttpResponse(json.dumps(results), content_type='application/json')


def csv_file_to_clean_csv_file2( table_name ):
    csv_rows = []
    with open(table_name + '.csv', 'r') as csv_file2:
        line_reader = csv.reader(csv_file2, delimiter='|')
        header = None
        dummy_unique_id = 10000000
        skipped_rows = '... Skipped rows in ' + table_name + ': '
        for row in line_reader:
            if header is None:
                header = row
                continue
            # Messed up records with '|' in them
            if len(header) != len(row) or '|' in str(row):
                skipped_rows += row[0] + ", "
                continue
            if table_name == "ballot_ballotreturned":
                clean_row(row, 6)                       # text_for_map_search
                substitute_null(row, 7, '0.0')      # latitude
                substitute_null(row, 8, '0.0')      # longitude
                # dump_row_col_labels_and_errors(table_name, header, row, '50490')
            if table_name == "candidate_candidatetoofficelink":
                if row[1] == '':  # candidate_we_vote_id
                    continue
            elif table_name == "election_election":
                substitute_null(row, 2, '0')  # google_civic_election_id_new is an integer
                if row[8] == '' or row[8] == '\\N' or row[8] == '0':
                    dummy_unique_id += 1
                    row[8] = str(dummy_unique_id)  # ballotpedia_election_id
                substitute_null(row, 8, '0')  #
                clean_row(row, 10)  # internal_notes
                substitute_null(row, 2, 'f')  # election_preparation_finished
            elif table_name == "politician_politician":
                row[2] = row[2].replace("\\", "")  # middle_name
                substitute_null(row, 7, 'U')  # gender
                substitute_null(row, 8, '\\N')  # birth_date
                dummy_unique_id += 1
                row[9] = str(dummy_unique_id)  # bioguide_id, looks like we don't even use this anymore
                row[10] = str(dummy_unique_id)  # thomas_id, looks like we don't even use this anymore
                row[11] = str(dummy_unique_id)  # lis_id, looks like we don't even use this anymore
                row[12] = str(dummy_unique_id)  # govtrack_id, looks like we don't even use this anymore
                row[15] = str(dummy_unique_id)  # fec_id, looks like we don't even use this anymore
                row[19] = str(dummy_unique_id)  # maplight_id, looks like we don't even use this anymore
            elif table_name == "polling_location_pollinglocation":
                clean_row(row, 2)  # location_name
                row[2] = row[2].replace("\\", "")  # 'BIG BONE STATE PARK GARAGE BLDG\\'
                clean_row(row, 3)  # polling_hours_text
                clean_row(row, 4)  # directions_text
                clean_row(row, 5)  # line1
                clean_row(row, 6)  # line2
                substitute_null(row, 11, '0.00001')  # latitude
                substitute_null(row, 12, '0.00001')  # longitude
                substitute_null(row, 14, '\\N')  # google_response_address_not_found
            elif table_name == "office_contestoffice":
                # print(str(row))
                substitute_null(row, 4, '0')  # google_civic_election_id_new is an integer
                dummy_unique_id += 1
                row[6] = str(dummy_unique_id)  # maplight_id, looks like we don't even use this anymore
                substitute_null(row, 24, '0')  # ballotpedia_office_id is an integer
                substitute_null(row, 28, '0')  # ballotpedia_district_id is an integer
                substitute_null(row, 29, '0')  # ballotpedia_election_id is an integer
                substitute_null(row, 30, '0')  # ballotpedia_race_id is an integer
                substitute_null(row, 33, '0')  # google_ballot_placement is an integer
                substitute_null(row, 40, 'f')  # ballotpedia_is_marquee is a bool
                substitute_null(row, 41, 'f')  # is_battleground_race is a bool
            elif table_name == "candidate_candidatecampaign":
                dummy_unique_id += 1
                row[2] = str(dummy_unique_id)           # maplight_id, looks like we don't even use this anymore
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
                clean_row(row, 33)                      # wikipedia_thumbnail_width
                clean_row(row, 47)                      # issue_analysis_admin_notes
                # dump_row_col_labels_and_errors(table_name, header, row, '697')
            elif table_name == 'position_positionentered':
                clean_row(row, 4)                       # ballot_item_display_name
                substitute_null(row, 5, '1970-01-01 00:00:00+00')
                clean_row(row, 16)                      # vote_smart_rating_name
                clean_row(row, 28)                      # statement_text
                # dump_row_col_labels_and_errors(table_name, header, row, '33085')
            elif table_name == 'voter_guide_voterguide':
                clean_row(row, 28)                      # statement_text
                dump_row_col_labels_and_errors(table_name, header, row, '3482')
            csv_rows.append(row)
        csv_file2.close()
        if ',' in skipped_rows:
            print(skipped_rows + ' were skipped since they had pipe characters in the data')

    with open(table_name + '2.csv', 'w') as csv_file:
        csvwriter = csv.writer(csv_file, delimiter='|')
        for row in csv_rows:
            csvwriter.writerow(row)
    csv_file.close()
    return header
