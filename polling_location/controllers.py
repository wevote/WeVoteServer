# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocationManager
import xml.etree.ElementTree as MyElementTree


def import_and_save_all_polling_locations_data():
    # In most states we can visit this URL (example is 'va' or virginia):
    # https://data.votinginfoproject.org/feeds/va/?order=D
    # and download the first zip file.
    # https://data.votinginfoproject.org/feeds/STATE/?order=D

    # Alaska
    xml_file_location = 'polling_location/import_data/ak/vipFeed-02-2014-11-04-AK.xml'
    ak1_results = import_and_save_polling_location_data(xml_file_location)

    # Arizona
    xml_file_location = 'polling_location/import_data/az/vipFeed-04-2015-11-03-AZ.xml'
    az1_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/az/vipFeed-04-2015-08-25.xml'
    az2_results = import_and_save_polling_location_data(xml_file_location)

    # ##################
    # California
    xml_file_location = 'polling_location/import_data/ca/vipFeed-06-2015-11-03-short.xml'
    ca1_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-06037-2015-11-03-Calabasas-short.xml'
    ca2_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-06037-2015-11-03-short.xml'
    ca3_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-6067-2014-11-04-short.xml'
    ca4_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-6075-2015-11-03-short.xml'
    ca5_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-6087-2014-11-04-short.xml'
    ca6_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-6103-2014-11-04-short.xml'
    ca7_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ca/vipFeed-6115-2014-11-04-short.xml'
    ca8_results = import_and_save_polling_location_data(xml_file_location)

    # North Carolina
    xml_file_location = 'polling_location/import_data/nc/vipFeed-37-2015-04-07.xml'
    nc1_results = import_and_save_polling_location_data(xml_file_location)

    #
    xml_file_location = 'polling_location/import_data/nd/vipFeed-38-2014-11-04.xml'
    nd1_results = import_and_save_polling_location_data(xml_file_location)

    #
    xml_file_location = 'polling_location/import_data/ne/vipFeed-31-2014-11-04.xml'
    ne1_results = import_and_save_polling_location_data(xml_file_location)

    # New Hampshire
    xml_file_location = 'polling_location/import_data/nh/vipFeed-33-2012-11-06.xml'
    nh1_results = import_and_save_polling_location_data(xml_file_location)

    # New Jersey
    xml_file_location = 'polling_location/import_data/nj/vipFeed-34-2015-11-03.xml'
    nj1_results = import_and_save_polling_location_data(xml_file_location)

    # Nevada
    xml_file_location = 'polling_location/import_data/nv/vipFeed-32-2014-11-04.xml'
    nv1_results = import_and_save_polling_location_data(xml_file_location)

    # New York
    xml_file_location = 'polling_location/import_data/ny/vipFeed-36-2015-11-03.xml'
    ny1_results = import_and_save_polling_location_data(xml_file_location)

    # ##################
    # Rhode Island
    xml_file_location = 'polling_location/import_data/ri/vipFeed-44-2015-12-15-short.xml'
    ri1_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ri/vipFeed-44-2016-01-05-egreenwich-short.xml'
    ri2_results = import_and_save_polling_location_data(xml_file_location)

    xml_file_location = 'polling_location/import_data/ri/vipFeed-44-2016-01-05-senate-short.xml'
    ri3_results = import_and_save_polling_location_data(xml_file_location)

    # ##################
    # Virginia
    xml_file_location = 'polling_location/import_data/va/vipFeed-51-2015-11-03-short.xml'
    va1_results = import_and_save_polling_location_data(xml_file_location)

    # Washington
    xml_file_location = 'polling_location/import_data/wa/vipFeed-53-2015-08-04.xml'
    wa1_results = import_and_save_polling_location_data(xml_file_location)

    # Wisconsin
    xml_file_location = 'polling_location/import_data/wi/vipFeed-55-2015-04-07.xml'
    wi1_results = import_and_save_polling_location_data(xml_file_location)

    # West Virginia
    xml_file_location = 'polling_location/import_data/wv/vipFeed-54-2015-05-16.xml'
    wv1_results = import_and_save_polling_location_data(xml_file_location)

    # Wyoming
    xml_file_location = 'polling_location/import_data/wy/vipFeed-56-2016-11-08.xml'
    wy1_results = import_and_save_polling_location_data(xml_file_location)

    return merge_polling_location_results(ak1_results, az1_results, az2_results,
                                          ca1_results, ca2_results, ca3_results, ca4_results, ca5_results, ca6_results,
                                          ca7_results, ca8_results,
                                          nc1_results, nd1_results,
                                          ne1_results, nh1_results, nj1_results, nv1_results, ny1_results,
                                          ri1_results, ri2_results, ri3_results,
                                          va1_results, wa1_results, wi1_results, wv1_results, wy1_results
                                          )


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
