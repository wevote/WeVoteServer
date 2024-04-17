# retrieve_tables/controllers_master.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import re
import time
from datetime import datetime, timezone
from io import StringIO

import psycopg2
from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from retrieve_tables.models import RetrieveTableState
from wevote_functions.functions import positive_value_exists, get_voter_device_id, convert_to_int

logger = wevote_functions.admin.get_logger(__name__)

# This api will only return the data from the following tables
# Creating CampaignX's locally seems to be best testing strategy
# 'campaign_campaignx',
# 'campaign_campaignxlistedbyorganization',
# 'campaign_campaignxnewsitem',
# 'campaign_campaignx_politician',
# 'campaign_campaignxseofriendlypath',
allowable_tables = [
    'ballot_ballotitem',
    'position_positionentered',
    'candidate_candidatesarenotduplicates',
    'candidate_candidatetoofficelink',
    'election_ballotpediaelection',
    'election_election',
    'electoral_district_electoraldistrict',
    'issue_issue',
    'issue_organizationlinktoissue',
    'measure_contestmeasure',
    'measure_contestmeasuresarenotduplicates',
    'office_contestoffice',
    'office_contestofficesarenotduplicates',
    'office_contestofficevisitingotherelection',
    'office_held_officeheld',
    'organization_organizationreserveddomain',
    'party_party',
    'politician_politician',
    'politician_politiciansarenotduplicates',
    'representative_representative',
    'representative_representativesarenotduplicates',
    'twitter_twitterlinktoorganization',
    'voter_guide_voterguidepossibility',
    'voter_guide_voterguidepossibilityposition',
    'voter_guide_voterguide',
    'wevote_settings_wevotesetting',
    'ballot_ballotreturned',
    'polling_location_pollinglocation',
    'organization_organization',
    'candidate_candidatecampaign',
]

dummy_unique_id = 10000000
LOCAL_TMP_PATH = '/tmp/'


def get_total_row_count():
    """
    Returns the total row count of tables to be fetched from the MASTER server
    Runs on the Master server
    :return: the number of rows
    """
    conn = psycopg2.connect(
        database=get_environment_variable('DATABASE_NAME'),
        user=get_environment_variable('DATABASE_USER'),
        password=get_environment_variable('DATABASE_PASSWORD'),
        host=get_environment_variable('DATABASE_HOST'),
        port=get_environment_variable('DATABASE_PORT')
    )

    rows = 0
    for table_name in allowable_tables:
        with conn.cursor() as cursor:
            sql = "SELECT MAX(id) FROM \"public\".\"{table_name}\";".format(table_name=table_name)
            cursor.execute(sql)
            row = cursor.fetchone()
            if row[0] is not None:
                sql = "SELECT COUNT(*) FROM \"public\".\"{table_name}\";".format(table_name=table_name)
                cursor.execute(sql)
                row = cursor.fetchone()
                if row[0] is not None:
                    cnt = int(row[0])
            print('get_total_row_count of table ', table_name, ' is ', cnt)
            rows += cnt

    print('get_total_row_count is ', rows)

    conn.close()
    return rows


def retrieve_sql_tables_as_csv(voter_device_id, table_name, start, end):
    """
    Extract one of the approximately 21 allowable database tables to CSV (pipe delimited) and send it to the
    developer's local WeVoteServer instance
    limit is used to specify a number of rows to return (this is the SQL LIMIT clause), non-zero or ignored
    offset is used to specify the first row to return (this is the SQL OFFSET clause), non-zero or ignored
    Note July 2022, re Joe:  This call to `https://api.wevoteusa.org/apis/v1/retrieveSQLTables/` has been moved from a
    "normal" API server (which was timing out) to a "process" API server with an 1800-second timeout.
    """
    t0 = time.time()

    status = ''

    csv_files = {}
    try:
        conn = psycopg2.connect(
            database=get_environment_variable('DATABASE_NAME'),
            user=get_environment_variable('DATABASE_USER'),
            password=get_environment_variable('DATABASE_PASSWORD'),
            host=get_environment_variable('DATABASE_HOST'),
            port=get_environment_variable('DATABASE_PORT')
        )

        # logger.debug("retrieve_sql_tables_as_csv psycopg2 Connected to DB")

        print('retrieve_sql_tables_as_csv "', table_name + '"')
        print('retrieve_sql_tables_as_csv if table_name in allowable_tables ' + str(table_name in allowable_tables))
        if table_name in allowable_tables:
            try:
                cur = conn.cursor()
                file = StringIO()  # Empty file

                # logger.error("experiment: REAL FILE ALLOWED FOR file: " + table_name)
                if positive_value_exists(end):
                    sql = "COPY (SELECT * FROM public." + table_name + " WHERE id BETWEEN " + start + " AND " + \
                          end + " ORDER BY id) TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                else:
                    sql = "COPY " + table_name + " TO STDOUT WITH DELIMITER '|' CSV HEADER NULL '\\N'"
                # logger.error("experiment: retrieve_tables sql: " + sql)
                cur.copy_expert(sql, file, size=8192)
                # logger.error("experiment: after cur.copy_expert ")
                file.seek(0)
                # logger.error("experiment: retrieve_tables file contents: " + file.readline().strip())
                file.seek(0)
                csv_files[table_name] = file.read()
                file.close()
                # logger.error("experiment: after file close, status " + status)
                if "exported" not in status:
                    status += "exported "
                status += table_name + "(" + start + "," + end + "), "
                # logger.error("experiment: after status +=, " + status)
                # logger.error("experiment: before conn.commit")
                conn.commit()
                # logger.error("experiment: after conn.commit ")
                conn.close()
                # logger.error("experiment: after conn.close ")
                dt = time.time() - t0
                logger.error('Extracting the "' + table_name + '" table took ' + "{:.3f}".format(dt) +
                             ' seconds.  start = ' + start + ', end = ' + end)
            except Exception as e:
                logger.error("Real exception in retrieve_sql_tables_as_csv(): " + str(e) + " ")
        else:
            status = "the table_name '" + table_name + "' is not in the table list, therefore no table was returned"
            logger.error(status)

        # logger.error("experiment: before results")
        results = {
            'success': True,
            'status': status,
            'files': csv_files,
        }

        # logger.error("experiment: results returned")
        return results

    # run `pg_dump -f /dev/null wevotedev` on the server to evaluate for a corrupted file
    except Exception as e:
        status += "retrieve_tables export_sync_files_to_csv caught " + str(e)
        logger.error(status)
        logger.error("retrieve_tables export_sync_files_to_csv caught " + str(e))
        results = {
            'success': False,
            'status': status,
        }
        return results


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


def fast_load_status_retrieve(request):   # fastLoadStatusRetrieve
    initialize = positive_value_exists(request.GET.get('initialize', False))
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    is_running = positive_value_exists(request.GET.get('is_running', True))
    table_name = ''
    chunk = 0
    records = 0
    total = 0
    status = ""
    success = True
    started = None

    try:
        if initialize:
            total = get_total_row_count()
            started = datetime.now(tz=timezone.utc)
            RetrieveTableState.objects.update_or_create(
                voter_device_id=voter_device_id,
                defaults={
                    'is_running':       is_running,
                    'started_date':     started,
                    'table_name':       '',
                    'chunk':            0,
                    'current_record':   0,
                    'total_records':    total,
                })
            status += "ROW_INITIALIZED "
        else:
            row = RetrieveTableState.objects.get(voter_device_id=voter_device_id)
            is_running = row.is_running
            table_name = row.table_name
            chunk = row.chunk
            records = row.current_record
            total = row.total_records
            started = row.started_date
            status += "ROW_RETRIEVED "

    except Exception as e:
        status += "fast_load_status_retrieve caught exception: " + str(e)
        logger.error("fast_load_status_retrieve caught exception: " + str(e))
        success = False

    started_txt = started.strftime('%Y-%m-%d %H:%M:%S') if started else ""
    results = {
        'status': status,
        'success': success,
        'initialize': initialize,
        'is_running': is_running,
        'voter_device_id': voter_device_id,
        'started_date': started_txt,
        'table_name': table_name,
        'chunk': chunk,
        'current_record': records,
        'total_records': total,
    }

    return HttpResponse(json.dumps(results), content_type='application/json')


def fast_load_status_update(request):
    """
    Save updated fast load status
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    table_name = request.GET.get('table_name', '')
    additional_records = convert_to_int(request.GET.get('additional_records', 0))
    chunk = convert_to_int(request.GET.get('chunk', None))
    total_records = convert_to_int(request.GET.get('total_records', None))
    is_running = positive_value_exists(request.GET.get('is_running', True))
    print('fast_load_status_update ENTRY table_name', table_name, chunk, 'no row yet', additional_records)

    success = True

    try:
        row = RetrieveTableState.objects.get(voter_device_id=voter_device_id)
        row.is_running = is_running
        if positive_value_exists(table_name):
            row.table_name = table_name
        if positive_value_exists(chunk):
            row.chunk = chunk
        if positive_value_exists(additional_records):
            row.current_record += additional_records
        if positive_value_exists(total_records):
            row.total_records = total_records
        row.save()
        status = 'ROW_SAVED'
        id = row.id
        print('fast_load_status_update AFTER SAVE table_name', table_name, chunk, row.current_record, additional_records)

    except Exception as e:
        logger.error("fast_load_status_update caught exception: " + str(e))
        success = False
        status = 'ROW_NOT_SAVED  ' + str(e)
        id = -1

    results = {
        'status': status,
        'success': success,
        'row_id': id,
    }

    return HttpResponse(json.dumps(results), content_type='application/json')