import os
import psycopg2
import time
from zipfile import ZipFile
from config.base import get_environment_variable
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_sql_files_as_csv():
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

        # logger.debug("retrieve_tables psycopg2 Connected to DB")

        csv_files = {}
        cur = conn.cursor()
        for table_name in files:
            csv_name = table_name + '.csv'
            with open(csv_name, 'w') as file:
                cur.copy_to(file, table_name, sep =',')
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
        logger.debug('Extracting and zipping the 8 tables took ' + "{:.3f}".format(dt) + ' seconds')
        return results

    except Exception as e:
        status += "retrieve_tables export_sync_files_to_csv caught " + str(e)
        logger.error(status)
        results = {
            'status': status,
        }
        return results
