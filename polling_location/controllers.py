# polling_location/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import glob

from .models import PollingLocationManager
from config.base import get_environment_variable
from django.contrib import messages
import json
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
import xml.etree.ElementTree as MyElementTree

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POLLING_LOCATIONS_SYNC_URL = get_environment_variable("POLLING_LOCATIONS_SYNC_URL")


def polling_locations_import_from_master_server(request, state_code):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    messages.add_message(request, messages.INFO, "Loading Measures from We Vote Master servers")
    logger.info("Loading Measures from We Vote Master servers")
    request = requests.get(POLLING_LOCATIONS_SYNC_URL, params={
        "key": WE_VOTE_API_KEY,  # This comes from an environment variable
        "format":   'json',
        "state": state_code,
    })
    structured_json = json.loads(request.text)
    results = filter_polling_locations_structured_json_for_local_duplicates(structured_json)
    filtered_structured_json = results['structured_json']
    duplicates_removed = results['duplicates_removed']

    import_results = polling_locations_import_from_structured_json(filtered_structured_json)
    import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_polling_locations_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove candidates that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    measure_list_manager = ContestMeasureList()
    for one_measure in structured_json:
        measure_title = one_measure['measure_title'] if 'measure_title' in one_measure else ''
        we_vote_id = one_measure['we_vote_id'] if 'we_vote_id' in one_measure else ''
        google_civic_election_id = \
            one_measure['google_civic_election_id'] if 'google_civic_election_id' in one_measure else ''
        measure_url = one_measure['measure_url'] if 'measure_url' in one_measure else ''
        maplight_id = one_measure['maplight_id'] if 'maplight_id' in one_measure else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = measure_list_manager.retrieve_possible_duplicate_measures(
            measure_title, google_civic_election_id, measure_url, maplight_id,
            we_vote_id_from_master)

        if results['measure_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_measure)

    candidates_results = {
        'success':              True,
        'status':               "FILTER_MEASURES_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return candidates_results


def polling_locations_import_from_structured_json(structured_json):
    """
    This pathway in requires a we_vote_id, and is not used when we import from Google Civic
    :param structured_json:
    :return:
    """
    contest_measure_manager = ContestMeasureManager()
    measures_saved = 0
    measures_updated = 0
    measures_not_processed = 0
    for one_measure in structured_json:
        we_vote_id = one_measure['we_vote_id'] if 'we_vote_id' in one_measure else ''
        google_civic_election_id = \
            one_measure['google_civic_election_id'] if 'google_civic_election_id' in one_measure else ''

        if positive_value_exists(we_vote_id) and positive_value_exists(google_civic_election_id):
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False

        if proceed_to_update_or_create:
            measure_title = one_measure['measure_title'] if 'measure_title' in one_measure else ''
            district_id = one_measure['district_id'] if 'district_id' in one_measure else 0
            district_name = one_measure['district_name'] if 'district_name' in one_measure else 0
            state_code = one_measure['state_code'] if 'state_code' in one_measure else ''

            updated_contest_measure_values = {
                # Values we search against
                'we_vote_id': we_vote_id,
                'google_civic_election_id': google_civic_election_id,
                # The rest of the values
                'ballotpedia_page_title': one_measure['ballotpedia_page_title'] if 'ballotpedia_page_title' in
                                                                                   one_measure else '',
                'ballotpedia_photo_url': one_measure['ballotpedia_photo_url'] if 'ballotpedia_photo_url' in
                                                                                 one_measure else '',
                'district_id': district_id,
                'district_name': district_name,
                'district_scope': one_measure['district_scope'] if 'district_scope' in one_measure else '',
                'maplight_id': one_measure['maplight_id'] if 'maplight_id' in one_measure else None,
                'measure_subtitle': one_measure['measure_subtitle'] if 'measure_subtitle' in one_measure else '',
                'measure_text': one_measure['measure_text'] if 'measure_text' in one_measure else '',
                'measure_url': one_measure['measure_url'] if 'measure_url' in one_measure else '',
                'measure_title': measure_title,
                'ocd_division_id': one_measure['ocd_division_id'] if 'ocd_division_id' in one_measure else '',
                'primary_party': one_measure['primary_party'] if 'primary_party' in one_measure else '',
                'state_code': state_code,
                'wikipedia_page_id': one_measure['wikipedia_page_id'] if 'wikipedia_page_id' in one_measure else '',
                'wikipedia_page_title': one_measure['wikipedia_page_title'] if 'wikipedia_page_title' in
                                                                               one_measure else '',
                'wikipedia_photo_url': one_measure['wikipedia_photo_url'] if 'wikipedia_photo_url' in
                                                                             one_measure else '',
            }

            results = contest_measure_manager.update_or_create_contest_measure(
                we_vote_id, google_civic_election_id, measure_title,
                district_id, district_name, state_code, updated_contest_measure_values)
        else:
            measures_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_measure_created']:
                measures_saved += 1
            else:
                measures_updated += 1
        else:
            measures_not_processed += 1
    measures_results = {
        'success': True,
        'status': "MEASURES_IMPORT_PROCESS_COMPLETE",
        'saved': measures_saved,
        'updated': measures_updated,
        'not_processed': measures_not_processed,
    }
    return measures_results


def import_and_save_all_polling_locations_data(state_code=''):
    # In most states we can visit this URL (example is 'va' or virginia):
    # https://data.votinginfoproject.org/feeds/va/?order=D
    # and download the first zip file.
    # https://data.votinginfoproject.org/feeds/STATE/?order=D

    print('import_and_save_all_polling_locations_data...')
    all_results = []
    for xml_path in glob.glob('polling_location/import_data/*/vipFeed-*.xml'):
        if 'ignore' in xml_path:
            continue
        if positive_value_exists(state_code):
            state_code_folder_path = "/" + state_code + "/"
            if state_code_folder_path in xml_path:
                print('  loading:', xml_path)
                all_results.append(import_and_save_polling_location_data(xml_path))
        else:
            print('  loading:', xml_path)
            all_results.append(import_and_save_polling_location_data(xml_path))

    return merge_polling_location_results(*all_results)


def merge_polling_location_results(*dict_args):
    results = {
        'updated':          0,
        'saved':            0,
        'not_processed':    0,
    }
    for incoming_results in dict_args:
        new_results = {
            'updated':          results['updated'] + incoming_results['updated'],
            'saved':            results['saved'] + incoming_results['saved'],
            'not_processed':    results['not_processed'] + incoming_results['not_processed'],
        }
        results = new_results
    return results


def import_and_save_polling_location_data(xml_file_location):
    polling_locations_list = retrieve_polling_locations_data_from_xml(xml_file_location)
    results = save_polling_locations_from_list(polling_locations_list)
    return results


def retrieve_polling_locations_data_from_xml(xml_file_location):
    # We parse the XML file, which can be quite large
    # <polling_location id="80037">
    #   <polling_hours>6:00 AM - 7:00 PM</polling_hours>
    #   <address>
    #     <city>HARRISONBURG</city>
    #     <line1>400 MOUNTAIN VIEW DRIVE</line1>
    #     <state>VA</state>
    #     <location_name>SPOTSWOOD ELEMENTARY SCHOOL</location_name>
    #     <zip>22801</zip>
    #   </address>
    # </polling_location>
    tree = MyElementTree.parse(xml_file_location)
    root = tree.getroot()
    polling_locations_list = []
    for polling_location in root.findall('polling_location'):
        address = polling_location.find('address')
        if address is not None:
            location_name = address.find('location_name')
            location_name_text = location_name.text if location_name is not None else ''
            line1 = address.find('line1')
            line1_text = line1.text if line1 is not None else ''
            city = address.find('city')
            city_text = city.text if city is not None else ''
            if city_text == 'A BALLOT FOR EACH ELECTION':
                # We don't want to save this polling location
                continue
            if city_text == '0':
                # We don't want to save this polling location
                continue
            state = address.find('state')
            state_text = state.text if state is not None else ''
            zip_long = address.find('zip')
            zip_long_text = zip_long.text if zip_long is not None else ''
        else:
            location_name_text = ''
            line1_text = ''
            city_text = ''
            state_text = ''
            zip_long_text = ''
        polling_hours = polling_location.find('polling_hours')
        polling_hours_text = polling_hours.text if polling_hours is not None else ''
        directions = polling_location.find('directions')
        directions_text = directions.text if directions is not None else ''
        one_entry = {
            "polling_location_id": polling_location.get('id'),
            "location_name": location_name_text,
            "polling_hours_text": polling_hours_text,
            "directions": directions_text,
            "line1": line1_text,
            "line2": '',
            "city": city_text,
            "state": state_text,
            "zip_long": zip_long_text,
        }
        polling_locations_list.append(one_entry)
    return polling_locations_list


def save_polling_locations_from_list(polling_locations_list):
    polling_location_manager = PollingLocationManager()
    polling_locations_updated = 0
    polling_locations_saved = 0
    polling_locations_not_processed = 0
    polling_location_we_vote_id = ''
    for polling_location in polling_locations_list:
        results = polling_location_manager.update_or_create_polling_location(
            polling_location_we_vote_id,
            polling_location['polling_location_id'],
            polling_location['location_name'],
            polling_location['polling_hours_text'],
            polling_location['directions'],
            polling_location['line1'],
            polling_location['line2'],
            polling_location['city'],
            polling_location['state'],
            polling_location['zip_long'])
        if results['success']:
            if results['new_polling_location_created']:
                polling_locations_saved += 1
            else:
                polling_locations_updated += 1
        else:
            polling_locations_not_processed += 1
    save_results = {
        'updated': polling_locations_updated,
        'saved': polling_locations_saved,
        'not_processed': polling_locations_not_processed,
    }
    return save_results
