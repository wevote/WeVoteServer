# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import glob

from .models import PollingLocationManager
import xml.etree.ElementTree as MyElementTree


def import_and_save_all_polling_locations_data():
    # In most states we can visit this URL (example is 'va' or virginia):
    # https://data.votinginfoproject.org/feeds/va/?order=D
    # and download the first zip file.
    # https://data.votinginfoproject.org/feeds/STATE/?order=D

    print('import_and_save_all_polling_locations_data...')
    all_results = []
    for xml_path in glob.glob('polling_location/import_data/*/vipFeed-*.xml'):
        if 'ignore' in xml_path:
            continue
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
    for polling_location in polling_locations_list:
        results = polling_location_manager.update_or_create_polling_location(
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
