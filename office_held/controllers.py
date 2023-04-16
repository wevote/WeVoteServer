# office_held/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime
from config.base import get_environment_variable
from office_held.models import OfficeHeldManager
from wevote_functions.functions import positive_value_exists, process_request_from_master

OFFICE_HELD_SYNC_URL = "https://api.wevoteusa.org/apis/v1/officeHeldSyncOut/"
# OFFICE_HELD_SYNC_URL = "http://localhost:8001/apis/v1/officeHeldSyncOut/"
OFFICES_HELD_FOR_LOCATION_SYNC_URL = "https://api.wevoteusa.org/apis/v1/officesHeldForLocationSyncOut/"
# OFFICES_HELD_FOR_LOCATION_SYNC_URL = "http://localhost:8001/apis/v1/officesHeldForLocationSyncOut/"
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")


def generate_office_held_dict_list_from_office_held_object_list(office_held_list=[]):
    office_held_dict_list = []
    status = ""
    success = True
    for office_held in office_held_list:
        one_office_dict = {
            'district_id':                  office_held.district_id,
            'district_name':                office_held.district_name,
            'ocd_division_id':              office_held.ocd_division_id,
            'office_held_id':               office_held.id,
            'office_held_description':      office_held.office_held_description,
            'office_held_facebook_url':     office_held.office_held_facebook_url,
            'office_held_name':             office_held.office_held_name,
            'office_held_twitter_handle':   office_held.office_held_twitter_handle,
            'office_held_url':              office_held.office_held_url,
            'office_held_we_vote_id':       office_held.we_vote_id,
            'race_office_level':            office_held.race_office_level,
            'state_code':                   office_held.state_code,
        }
        office_held_dict_list.append(one_office_dict)

    results = {
        'office_held_dict_list':    office_held_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def generate_office_held_dict_list_from_office_held_we_vote_id_list(
        office_held_we_vote_id_list=[]):
    office_held_dict_list = []
    office_held_manager = OfficeHeldManager()
    status = ""
    success = True
    if len(office_held_we_vote_id_list) > 0:
        results = office_held_manager.retrieve_office_held_list(
            office_held_we_vote_id_list=office_held_we_vote_id_list,
            read_only=True)
        if results['office_held_list_found']:
            office_held_list = results['office_held_list']
            results = generate_office_held_dict_list_from_office_held_object_list(office_held_list=office_held_list)
            status += results['status']
            if results['success']:
                office_held_dict_list = results['office_held_dict_list']

    results = {
        'office_held_dict_list':    office_held_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def office_held_import_from_structured_json(structured_json):
    office_held_manager = OfficeHeldManager()
    offices_saved = 0
    offices_updated = 0
    offices_not_processed = 0
    status = ""
    status_passed_through_count = 0
    boolean_fields = [
        'facebook_url_is_broken',
        'is_battleground_race_2019',
        'is_battleground_race_2020',
        'is_battleground_race_2021',
        'is_battleground_race_2022',
        'is_battleground_race_2023',
        'is_battleground_race_2024',
        'is_battleground_race_2025',
        'is_battleground_race_2026',
        'office_held_is_partisan',
        'year_with_data_2023',
        'year_with_data_2024',
        'year_with_data_2025',
        'year_with_data_2026',
    ]
    character_fields = [
        'district_id',
        'district_name',
        'district_scope',
        'google_civic_office_held_name',
        'google_civic_office_held_name2',
        'google_civic_office_held_name3',
        'number_elected',
        'ocd_division_id',
        'office_held_description',
        'office_held_description_es',
        'office_held_facebook_url',
        'office_held_level0',
        'office_held_level1',
        'office_held_level2',
        'office_held_name_es',
        'office_held_role0',
        'office_held_role1',
        'office_held_role2',
        'office_held_twitter_handle',
        'office_held_url',
        'primary_party',
        'race_office_level',
        'state_code',
        'we_vote_id',
    ]
    character_null_false_fields = [
        'office_held_name',
    ]
    for one_office in structured_json:
        updated_office_held_values = {}
        office_held_we_vote_id = one_office.get('we_vote_id', '')
        for one_field in boolean_fields:
            if one_field in one_office:
                updated_office_held_values[one_field] = positive_value_exists(one_office[one_field])
            else:
                updated_office_held_values[one_field] = None
        for one_field in character_fields:
            updated_office_held_values[one_field] = one_office[one_field] if one_field in one_office else None
        for one_field in character_null_false_fields:
            updated_office_held_values[one_field] = one_office[one_field] if one_field in one_office else ''
        results = office_held_manager.update_or_create_office_held(
            office_held_we_vote_id=office_held_we_vote_id,
            updated_values=updated_office_held_values)

        if results['success']:
            if results['created']:
                offices_saved += 1
            else:
                offices_updated += 1
        else:
            offices_not_processed += 1
            if status_passed_through_count < 10:
                status += results['status']
                status_passed_through_count += 1

    status += "OFFICE_HELD_IMPORT_PROCESS_COMPLETE "
    results = {
        'success':          True,
        'status':           status,
        'saved':            offices_saved,
        'updated':          offices_updated,
        'not_processed':    offices_not_processed,
    }
    return results


def office_held_import_from_master_server(request, state_code=''):  # officeHeldSyncOut
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    import_results, structured_json = process_request_from_master(
        request, "Loading Office Held entries from We Vote Master servers",
        OFFICE_HELD_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
            "state_code": state_code,
        }
    )

    if import_results['success']:
        # We shouldn't need to check for duplicates any more
        # results = filter_offices_structured_json_for_local_duplicates(structured_json)
        # filtered_structured_json = results['structured_json']
        # duplicates_removed = results['duplicates_removed']
        duplicates_removed = 0

        import_results = office_held_import_from_structured_json(structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def offices_held_for_location_import_from_structured_json(structured_json):  # officesHeldForLocationSyncOut
    office_held_manager = OfficeHeldManager()
    offices_saved = 0
    offices_updated = 0
    offices_not_processed = 0
    status = ""
    status_passed_through_count = 0
    boolean_fields = [
        'year_with_data_2023',
        'year_with_data_2024',
        'year_with_data_2025',
        'year_with_data_2026',
    ]
    character_fields = [
        'office_held_name_01',
        'office_held_name_02',
        'office_held_name_03',
        'office_held_name_04',
        'office_held_name_05',
        'office_held_name_06',
        'office_held_name_07',
        'office_held_name_08',
        'office_held_name_09',
        'office_held_name_10',
        'office_held_name_11',
        'office_held_name_12',
        'office_held_name_13',
        'office_held_name_14',
        'office_held_name_15',
        'office_held_name_16',
        'office_held_name_17',
        'office_held_name_18',
        'office_held_name_19',
        'office_held_name_20',
        'office_held_name_21',
        'office_held_name_22',
        'office_held_name_23',
        'office_held_name_24',
        'office_held_name_25',
        'office_held_name_26',
        'office_held_name_27',
        'office_held_name_28',
        'office_held_name_29',
        'office_held_name_30',
        'office_held_we_vote_id_01',
        'office_held_we_vote_id_02',
        'office_held_we_vote_id_03',
        'office_held_we_vote_id_04',
        'office_held_we_vote_id_05',
        'office_held_we_vote_id_06',
        'office_held_we_vote_id_07',
        'office_held_we_vote_id_08',
        'office_held_we_vote_id_09',
        'office_held_we_vote_id_10',
        'office_held_we_vote_id_11',
        'office_held_we_vote_id_12',
        'office_held_we_vote_id_13',
        'office_held_we_vote_id_14',
        'office_held_we_vote_id_15',
        'office_held_we_vote_id_16',
        'office_held_we_vote_id_17',
        'office_held_we_vote_id_18',
        'office_held_we_vote_id_19',
        'office_held_we_vote_id_20',
        'office_held_we_vote_id_21',
        'office_held_we_vote_id_22',
        'office_held_we_vote_id_23',
        'office_held_we_vote_id_24',
        'office_held_we_vote_id_25',
        'office_held_we_vote_id_26',
        'office_held_we_vote_id_27',
        'office_held_we_vote_id_28',
        'office_held_we_vote_id_29',
        'office_held_we_vote_id_30',
        'polling_location_we_vote_id',
        'state_code',
        'voter_we_vote_id',
    ]
    character_to_date_fields = [
        'date_last_retrieved',
        'date_last_updated',
    ]
    for offices_held_for_location in structured_json:
        offices_held_for_location_values = {}
        polling_location_we_vote_id = offices_held_for_location.get('polling_location_we_vote_id', '')
        for one_field in boolean_fields:
            if one_field in offices_held_for_location:
                offices_held_for_location_values[one_field] = \
                    positive_value_exists(offices_held_for_location[one_field])
            else:
                offices_held_for_location_values[one_field] = None
        for one_field in character_fields:
            offices_held_for_location_values[one_field] = offices_held_for_location[one_field] \
                if one_field in offices_held_for_location else None
        for one_field in character_to_date_fields:
            if one_field in offices_held_for_location and positive_value_exists(offices_held_for_location[one_field]):
                date_field_trimmed = offices_held_for_location[one_field].replace(" 00:00:00", "")
                offices_held_for_location_values[one_field] = datetime.strptime(date_field_trimmed, '%Y-%m-%d').date()
            else:
                offices_held_for_location_values[one_field] = None
        results = office_held_manager.update_or_create_offices_held_for_location(
            polling_location_we_vote_id=polling_location_we_vote_id,
            updated_values=offices_held_for_location_values)

        if results['success']:
            if results['created']:
                offices_saved += 1
            else:
                offices_updated += 1
        else:
            offices_not_processed += 1
            if status_passed_through_count < 10:
                status += results['status']
                status_passed_through_count += 1

    status += "OFFICE_HELD_FOR_LOCATION_IMPORT_PROCESS_COMPLETE "
    results = {
        'success':          True,
        'status':           status,
        'saved':            offices_saved,
        'updated':          offices_updated,
        'not_processed':    offices_not_processed,
    }
    return results


def offices_held_for_location_import_from_master_server(request, state_code=''):  # officesHeldForLocationSyncOut
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    import_results, structured_json = process_request_from_master(
        request, "Loading Offices Held for Location entries from We Vote Master servers",
        OFFICES_HELD_FOR_LOCATION_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
            "state_code": state_code,
        }
    )

    if import_results['success']:
        # We shouldn't need to check for duplicates any more
        # results = filter_offices_structured_json_for_local_duplicates(structured_json)
        # filtered_structured_json = results['structured_json']
        # duplicates_removed = results['duplicates_removed']
        duplicates_removed = 0

        import_results = offices_held_for_location_import_from_structured_json(structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results
