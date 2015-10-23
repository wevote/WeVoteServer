# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocationManager
import xml.etree.ElementTree as MyElementTree


def return_polling_locations_data(state=''):
    # In most states we can visit this URL (example is 'va' or virginia):
    # https://data.votinginfoproject.org/feeds/va/?order=D
    # and download the first zip file.
    # https://data.votinginfoproject.org/feeds/STATE/?order=D
    if state == 'va':
        xml_file_location = 'polling_location/import_data/va/vipFeed-51-2015-11-03-short.xml'
    else:
        # Default entry
        xml_file_location = 'polling_location/import_data/va/vipFeed-51-2015-11-03-short.xml'
    polling_locations_list = retrieve_polling_locations_data_from_xml(xml_file_location)
    return polling_locations_list


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
        one_entry = {
            "polling_location_id": polling_location.get('id'),
            "location_name": address.find('location_name').text,
            "polling_hours_text": polling_location.find('polling_hours').text,
            "line1": address.find('line1').text,
            "line2": '',
            "city": address.find('city').text,
            "state": address.find('state').text,
            "zip_long": address.find('zip').text,
        }
        polling_locations_list.append(one_entry)
    return polling_locations_list


def import_and_save_all_polling_locations_data():
    state = "va"
    results = import_and_save_polling_locations_data_for_state(state)
    return results


def import_and_save_polling_locations_data_for_state(state):
    polling_locations_list = return_polling_locations_data(state)
    results = save_polling_locations_from_list(polling_locations_list)
    return results


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
