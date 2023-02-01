# import_export_google_civic/controllers_representatives.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from .models import GoogleCivicApiCounterManager
from config.base import get_environment_variable
from datetime import datetime
from django.utils.timezone import localtime, now
from exception.models import handle_exception
import json
from office_held.models import OfficeHeldManager
from polling_location.models import KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR, KIND_OF_LOG_ENTRY_API_END_POINT_CRASH, \
    KIND_OF_LOG_ENTRY_NO_OFFICES_HELD, KIND_OF_LOG_ENTRY_RATE_LIMIT_ERROR, \
    KIND_OF_LOG_ENTRY_REPRESENTATIVES_RECEIVED, PollingLocationManager
from representative.models import RepresentativeManager
import requests
from wevote_functions.functions import convert_district_scope_to_ballotpedia_race_office_level, \
    convert_level_to_race_office_level, convert_state_text_to_state_code, convert_to_int, \
    extract_district_id_label_when_district_id_exists_from_ocd_id, extract_district_id_from_ocd_division_id, \
    extract_facebook_username_from_text_string, extract_instagram_handle_from_text_string, \
    extract_state_code_from_address_string, extract_state_from_ocd_division_id, \
    extract_twitter_handle_from_text_string, extract_vote_usa_measure_id, extract_vote_usa_office_id, \
    is_voter_device_id_valid, logger, positive_value_exists, STATE_CODE_MAP

GEOCODE_TIMEOUT = 10
GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
ELECTION_QUERY_URL = get_environment_variable("ELECTION_QUERY_URL")
VOTER_INFO_URL = get_environment_variable("VOTER_INFO_URL")
VOTER_INFO_JSON_FILE = get_environment_variable("VOTER_INFO_JSON_FILE")
REPRESENTATIVES_BY_ADDRESS_URL = get_environment_variable("REPRESENTATIVES_BY_ADDRESS_URL")


def augment_officials_list_with_office_data(incoming_officials_list=[]):
    status = ''
    success = True
    # continue_searching_for_office = True
    # create_office_entry = False
    # office_manager = ContestOfficeManager()
    # ctcl_office_uuid = False
    # if continue_searching_for_office and positive_value_exists(ctcl_office_uuid):
    #     if ctcl_office_uuid in existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string]:
    #         contest_office = \
    #             existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string][ctcl_office_uuid]
    #         office_held_name = contest_office.office_name
    #         contest_office_we_vote_id = contest_office.we_vote_id
    #         contest_office_id = contest_office.id
    #         office_name = contest_office.office_name
    #         continue_searching_for_office = False
    #     else:
    #         office_results = office_manager.retrieve_contest_office(
    #             ctcl_uuid=ctcl_office_uuid,
    #             google_civic_election_id=google_civic_election_id,
    #             read_only=(not allowed_to_update_offices))
    #         if office_results['contest_office_found']:
    #             continue_searching_for_office = False
    #             contest_office = office_results['contest_office']
    #             office_held_name = contest_office.office_name
    #             contest_office_we_vote_id = contest_office.we_vote_id
    #             contest_office_id = contest_office.id
    #             office_name = contest_office.office_name
    #             existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string][ctcl_office_uuid] = contest_office
    #             # In the future, we will want to look for updated data to save
    #         elif office_results['MultipleObjectsReturned']:
    #             status += "MORE_THAN_ONE_OFFICE_WITH_SAME_CTCL_UUID_ID: " + str(ctcl_office_uuid) + " "
    #             continue_searching_for_office = False
    #         elif not office_results['success']:
    #             status += "RETRIEVE_BY_CTCL_UUID_FAILED: "
    #             status += office_results['status']
    #             results = {
    #                 'success': False,
    #                 'status': status,
    #                 'saved': 0,
    #                 'updated': 0,
    #                 'not_processed': 1,
    #                 'office_held_dict_list_for_location': office_held_dict_list_for_location,
    #                 'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
    #                 'existing_representative_objects_dict': existing_representative_objects_dict,
    #                 'new_representative_we_vote_ids_list': new_representative_we_vote_ids_list,
    #                 'new_office_held_we_vote_ids_list': new_office_held_we_vote_ids_list,
    #             }
    #             return results
    #         else:
    #             continue_searching_for_office = True
    # elif continue_searching_for_office and positive_value_exists(vote_usa_office_id):
    #     if vote_usa_office_id in existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string]:
    #         contest_office = \
    #             existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string][vote_usa_office_id]
    #         office_held_name = contest_office.office_name
    #         contest_office_we_vote_id = contest_office.we_vote_id
    #         contest_office_id = contest_office.id
    #         office_name = contest_office.office_name
    #         continue_searching_for_office = False
    #     else:
    #         # Uncomment this if testing against specific offices
    #         # if positive_value_exists(vote_usa_office_id):
    #         #     strings_to_find = [
    #         #         'BoardOfSupervisors', 'CommissionerOfRevenue', 'CommonwealthSAttorney',
    #         #         'SchoolBoard',
    #         #     ]
    #         #     if vote_usa_office_id.endswith(tuple(strings_to_find)):
    #         #         # For debugging
    #         #         record_found = True
    #         office_results = office_manager.retrieve_contest_office(
    #             vote_usa_office_id=vote_usa_office_id,
    #             google_civic_election_id=google_civic_election_id,
    #             read_only=(not allowed_to_update_offices))
    #         if office_results['contest_office_found']:
    #             continue_searching_for_office = False
    #             contest_office = office_results['contest_office']
    #             office_held_name = contest_office.office_name
    #             contest_office_we_vote_id = contest_office.we_vote_id
    #             contest_office_id = contest_office.id
    #             office_name = contest_office.office_name
    #             existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string][vote_usa_office_id] = contest_office
    #             # In the future, we will want to look for updated data to save
    #         elif office_results['MultipleObjectsReturned']:
    #             status += "MORE_THAN_ONE_OFFICE_WITH_SAME_VOTE_USA_ID: " + str(vote_usa_office_id) + " "
    #             continue_searching_for_office = False
    #         elif not office_results['success']:
    #             status += "RETRIEVE_BY_VOTE_USA_FAILED: "
    #             status += office_results['status']
    #             results = {
    #                 'success': False,
    #                 'status': status,
    #                 'saved': 0,
    #                 'updated': 0,
    #                 'not_processed': 1,
    #                 'office_held_dict_list_for_location': office_held_dict_list_for_location,
    #                 'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
    #                 'existing_representative_objects_dict': existing_representative_objects_dict,
    #                 'new_representative_we_vote_ids_list': new_representative_we_vote_ids_list,
    #                 'new_office_held_we_vote_ids_list': new_office_held_we_vote_ids_list,
    #             }
    #             return results
    #         else:
    #             # If here, we have a Vote USA Office Id, but no office found.
    #             create_office_entry = True
    #             continue_searching_for_office = False
    #
    # if continue_searching_for_office:
    #     # Check to see if there is an office which doesn't match by data provider id
    #     office_list_manager = ContestOfficeListManager()
    #     read_only = not (allowed_to_create_offices or allowed_to_update_offices)  # In case we need to update source id
    #     results = office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
    #         contest_office_name=office_name,
    #         ctcl_uuid=ctcl_office_uuid,
    #         google_civic_election_id=google_civic_election_id,
    #         incoming_state_code=state_code,
    #         district_id=district_id,
    #         read_only=read_only,
    #         vote_usa_office_id=vote_usa_office_id)
    #     if not results['success']:
    #         continue_searching_for_office = False
    #         status += "FAILED_RETRIEVING_CONTEST_FROM_UNIQUE_IDS: " + results['status'] + " "
    #     elif results['multiple_entries_found']:
    #         continue_searching_for_office = False
    #         status += "RETRIEVING_CONTEST_FROM_UNIQUE_IDS-MULTIPLE_FOUND: " + results['status'] + " "
    #         create_office_entry = True
    #     elif results['contest_office_found']:
    #         continue_searching_for_office = False
    #         contest_office = results['contest_office']
    #         office_held_name = contest_office.office_name
    #         contest_office_we_vote_id = contest_office.we_vote_id
    #         contest_office_id = contest_office.id
    #         office_name = contest_office.office_name
    #         if use_ctcl:
    #             if allowed_to_create_office_helds and not positive_value_exists(contest_office.ctcl_uuid):
    #                 contest_office.ctcl_uuid = ctcl_office_uuid
    #                 try:
    #                     contest_office.save()
    #                     if positive_value_exists(ctcl_office_uuid):
    #                         existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string][ctcl_office_uuid] = \
    #                             contest_office
    #                 except Exception as e:
    #                     status += "SAVING_CTCL_UUID_FAILED: " + str(e) + ' '
    #         elif use_vote_usa:
    #             if allowed_to_create_office_helds and not positive_value_exists(contest_office.vote_usa_office_id):
    #                 contest_office.vote_usa_office_id = vote_usa_office_id
    #                 try:
    #                     contest_office.save()
    #                     if positive_value_exists(vote_usa_office_id):
    #                         existing_offices_held_by_ocd_and_name_dict[google_civic_election_id_string][vote_usa_office_id] = \
    #                             contest_office
    #                 except Exception as e:
    #                     status += "SAVING_VOTE_USA_OFFICE_ID_FAILED: " + str(e) + ' '
    #     else:
    #         create_office_entry = True
    officials_list = incoming_officials_list
    results = {
        'success': success,
        'status': status,
        'officials_list': officials_list,
    }
    return results


def augment_officials_list_with_politician_data(incoming_officials_list=[]):
    status = ''
    success = True
    officials_list = incoming_officials_list
    results = {
        'success': success,
        'status': status,
        'officials_list': officials_list,
    }
    return results


def augment_officials_list_with_representative_data(incoming_officials_list=[]):
    status = ''
    success = True
    officials_list = incoming_officials_list
    results = {
        'success': success,
        'status': status,
        'officials_list': officials_list,
    }
    return results


def create_default_values_for_offices_held_for_location(
        office_held_dict_list_for_location=[]):
    defaults = {}
    success = True
    status = ""
    index_number = 1
    for office_held_dict in office_held_dict_list_for_location:
        if index_number > 30:
            status += "MORE_THAN_30_OFFICES "
        office_held_name_field_name = "office_held_name_{:02d}".format(index_number)
        defaults[office_held_name_field_name] = office_held_dict['office_held_name']
        office_held_we_vote_id_field_name = "office_held_we_vote_id_{:02d}".format(index_number)
        defaults[office_held_we_vote_id_field_name] = office_held_dict['office_held_we_vote_id']
        index_number += 1
    results = {
        'status':  status,
        'success':  success,
        'defaults': defaults,
    }
    return results


def groom_and_store_office_held_with_representatives_google_civic_json(
        divisions_dict={},
        office_held_dict={},
        office_held_array_index=0,
        officials_list=[],
        state_code='',
        offices_held_display_order=0,
        voter_id=0,
        polling_location_we_vote_id='',
        office_held_dict_list_for_location=[],
        existing_offices_held_by_ocd_and_name_dict={},
        existing_representative_objects_dict={},
        existing_representative_to_office_held_links_dict={},
        new_office_held_we_vote_ids_list=[],
        new_representative_we_vote_ids_list=[],
        use_ctcl=False,
        use_google_civic=False,
        use_vote_usa=False,
        update_or_create_rules={}):
    status = ''
    success = True
    office_held_manager = OfficeHeldManager()
    office_held_object = None

    office_held_id = 0
    office_held_we_vote_id = ""
    office_held_name = ""

    office_data_exists = 'name' in office_held_dict and positive_value_exists(office_held_dict['name'])
    if not office_data_exists:
        # We need office to proceed, so without it, go to the next race
        results = {
            'success': False,
            'status': status,
            'saved': 0,
            'updated': 0,
            'not_processed': 1,
            'office_held_dict_list_for_location': office_held_dict_list_for_location,
            'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
            'existing_representative_to_office_held_links_dict': existing_representative_to_office_held_links_dict,
            'existing_representative_objects_dict': existing_representative_objects_dict,
            'new_representative_we_vote_ids_list': new_representative_we_vote_ids_list,
            'new_office_held_we_vote_ids_list': new_office_held_we_vote_ids_list,
        }
        return results

    ctcl_office_uuid = None
    vote_usa_office_id = None
    if positive_value_exists(use_ctcl):
        ctcl_office_uuid = office_held_dict['id']
    elif positive_value_exists(use_vote_usa):
        raw_vote_usa_office_id = office_held_dict['id']
        vote_usa_office_id = extract_vote_usa_office_id(raw_vote_usa_office_id)

    office_held_name = office_held_dict['name']

    if "/n" in office_held_name:
        # Sometimes a line break is passed in with the office_held_name
        office_held_name = office_held_name.replace("/n", " ")
        office_held_name = office_held_name.strip()
        office_held_dict['name'] = office_held_name

    district = ''
    district_id = None
    ocd_division_id = office_held_dict['divisionId'] if 'divisionId' in office_held_dict else ''
    if ocd_division_id:
        district_id = extract_district_id_from_ocd_division_id(ocd_division_id)
        # I think results['district'] is not correct and should be replaced
        #  with name like 'contest_ocd_district_id_label'
        district = extract_district_id_label_when_district_id_exists_from_ocd_id(ocd_division_id)

    # TODO: Do we have access to district_scope data?
    # district_scope: The geographic scope of this district. If unspecified the
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    # district_scope = results['district_scope']
    # race_office_level = convert_district_scope_to_ballotpedia_race_office_level(district_scope)
    # office_ocd_division_id = results['contest_ocd_division_id']
    # district_id = results['district_id']
    # district_name = results['district_name']  # The name of the district.
    divisions_as_list = []
    for temp_ocd_id in divisions_dict:
        one_division = divisions_dict[temp_ocd_id]
        one_division['ocd_id'] = temp_ocd_id
        divisions_as_list.append(one_division)
    division_for_this_office_held_list = []
    for one_division in divisions_as_list:
        try:
            if 'officeIndices' in one_division:
                if office_held_array_index in one_division['officeIndices']:
                    division_for_this_office_held_list.append(one_division)
        except IndexError as e:
            pass
        except KeyError as e:
            pass
        except Exception as e:
            status += "DIVISION_MATCH_ERROR: " + str(e) + " "
    district_name = None
    try:
        if len(division_for_this_office_held_list) == 1:
            district_name = division_for_this_office_held_list[0]['name']
    except Exception as e:
        status += "FAILED_GETTING_DIVISION_NAME: " + str(e) + " "

    # We want to convert incoming levels list from an array to three fields for the same table
    # levels: string, A list of office levels to filter by. Only offices that serve at least one of these levels
    # will be returned. Divisions that don't contain a matching office will not be returned. (repeated)
    # Allowed values
    #   administrativeArea1 -
    #   administrativeArea2 -
    #   country -
    #   international -
    #   locality -
    #   regional -
    #   special -
    #   subLocality1 -
    #   subLocality2 -
    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both "administrative-area-2"
    # and "administrative-area-1".
    office_held_levels = office_held_dict['levels'] if 'levels' in office_held_dict else []
    try:
        office_held_level0 = office_held_levels[0]
    except IndexError:
        office_held_level0 = None
    try:
        office_held_level1 = office_held_levels[1]
    except IndexError:
        office_held_level1 = None
    try:
        office_held_level2 = office_held_levels[2]
    except IndexError:
        office_held_level2 = None

    race_office_level = None
    race_office_level_found = False
    for one_level in office_held_levels:
        # Only use the first one found
        if not race_office_level_found:
            race_office_level = convert_level_to_race_office_level(one_level)
            if positive_value_exists(race_office_level):
                race_office_level_found = True

    # roles: string, A list of office roles to filter by. Only offices fulfilling one of these roles will be returned.
    # Divisions that don't contain a matching office will not be returned. (repeated)
    # Allowed values
    #   deputyHeadOfGovernment -
    #   executiveCouncil -
    #   governmentOfficer -
    #   headOfGovernment -
    #   headOfState -
    #   highestCourtJudge -
    #   judge -
    #   legislatorLowerBody -
    #   legislatorUpperBody -
    #   schoolBoard -
    #   specialPurposeOfficer -
    office_held_roles = office_held_dict['roles'] if 'roles' in office_held_dict else []
    try:
        office_held_role0 = office_held_roles[0]
    except IndexError:
        office_held_role0 = None
    try:
        office_held_role1 = office_held_roles[1]
    except IndexError:
        office_held_role1 = None
    try:
        office_held_role2 = office_held_roles[2]
    except IndexError:
        office_held_role2 = None

    # Is this office_held_object already cached in this process?
    office_held_object_found = False
    if ocd_division_id in existing_offices_held_by_ocd_and_name_dict:
        if office_held_name in existing_offices_held_by_ocd_and_name_dict[ocd_division_id]:
            office_held_object = existing_offices_held_by_ocd_and_name_dict[ocd_division_id][office_held_name]
            office_held_object_found = True
            office_held_id = office_held_object.id
            office_held_we_vote_id = office_held_object.we_vote_id

    allowed_to_create_office_helds = \
        'create_office_helds' in update_or_create_rules and \
        positive_value_exists(update_or_create_rules['create_office_helds'])
    allowed_to_update_office_helds = \
        'update_office_helds' in update_or_create_rules and \
        positive_value_exists(update_or_create_rules['update_office_helds'])

    if not office_held_object_found:
        # Now see if this office_held_object is already in the database
        if positive_value_exists(ocd_division_id) and positive_value_exists(office_held_name):
            try:
                results = office_held_manager.retrieve_office_held(
                    ocd_division_id=ocd_division_id,
                    google_civic_office_held_name=office_held_name,
                    read_only=(not allowed_to_update_office_helds))
            except Exception as e:
                status += "RETRIEVE_OFFICE_HELD_ERROR: " + str(e) + " "
            try:
                if results['success']:
                    if results['office_held_list_found']:
                        # Use the first one found
                        office_held_list = results['office_held_list']
                        office_held_object = office_held_list[0]
                        office_held_object_found = True
                    elif results['office_held_found']:
                        office_held_object = results['office_held']
                        office_held_object_found = True
                    if office_held_object_found:
                        office_held_id = office_held_object.id
                        office_held_we_vote_id = office_held_object.we_vote_id
                        if type(existing_offices_held_by_ocd_and_name_dict) is not dict:
                            existing_offices_held_by_ocd_and_name_dict = {}
                        if office_held_object.ocd_division_id not in existing_offices_held_by_ocd_and_name_dict:
                            existing_offices_held_by_ocd_and_name_dict[office_held_object.ocd_division_id] = {}
                        if type(existing_offices_held_by_ocd_and_name_dict[office_held_object.ocd_division_id]) is not dict:
                            existing_offices_held_by_ocd_and_name_dict[office_held_object.ocd_division_id] = {}
                        existing_offices_held_by_ocd_and_name_dict[
                            office_held_object.ocd_division_id][office_held_object.office_held_name] = office_held_object
                else:
                    success = False
            except Exception as e:
                status += "PROBLEM_GETTING_OFFICE_HELD_OBJECT: " + str(e) + " "

    officials_list_results = augment_officials_list_with_representative_data(officials_list)
    if officials_list_results['success']:
        officials_list = officials_list_results['officials_list']

    officials_list_results = augment_officials_list_with_politician_data(officials_list)
    if officials_list_results['success']:
        officials_list = officials_list_results['officials_list']

    officials_list_results = augment_officials_list_with_office_data(officials_list)
    if officials_list_results['success']:
        officials_list = officials_list_results['officials_list']

    # Which officials (representatives) are attached to this office_held?
    official_indices_list = office_held_dict['officialIndices'] if 'officialIndices' in office_held_dict else []
    officials_for_this_office_held_list = []
    index = 0
    for one_official in officials_list:
        if index in official_indices_list:
            officials_for_this_office_held_list.append(one_official)
        index += 1

    today = datetime.now().date()
    this_year = 0
    if today and today.year:
        this_year = convert_to_int(today.year)

    create_office_held_entry = not office_held_object_found
    proceed_to_create_office_held = positive_value_exists(create_office_held_entry) and allowed_to_create_office_helds
    proceed_to_update_office_held = office_held_object_found and allowed_to_update_office_helds

    if positive_value_exists(state_code):
        use_state_code = True
        if ocd_division_id == 'ocd-division/country:us':
            use_state_code = False
            state_code = None
        elif 'country' in office_held_levels:
            if 'deputyHeadOfGovernment' in office_held_roles or 'headOfGovernment' in office_held_roles:
                use_state_code = False
                state_code = None

    if proceed_to_create_office_held or proceed_to_update_office_held:
        # Note that all the information saved here is independent of a particular voter
        if positive_value_exists(office_held_name):
            updated_office_held_values = {
                'office_held_name': office_held_name,
            }
            if positive_value_exists(state_code):
                use_state_code = True
                if ocd_division_id == 'ocd-division/country:us':
                    use_state_code = False
                elif 'country' in office_held_levels:
                    if 'deputyHeadOfGovernment' in office_held_roles or 'headOfGovernment' in office_held_roles:
                        use_state_code = False

                if use_state_code:
                    state_code_for_error_checking = state_code.lower()
                    # Limit to 2 digits so we don't exceed the database limit
                    state_code_for_error_checking = state_code_for_error_checking[-2:]
                    # Make sure we recognize the state
                    list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                               state_code_for_error_checking in key.lower()]
                    state_code_for_error_checking = list_of_states_matching.pop()
                    updated_office_held_values['state_code'] = state_code_for_error_checking
            if positive_value_exists(race_office_level):
                updated_office_held_values['race_office_level'] = race_office_level
            if positive_value_exists(district_id):
                updated_office_held_values['district_id'] = district_id
            if positive_value_exists(ocd_division_id):
                updated_office_held_values['ocd_division_id'] = ocd_division_id
            if positive_value_exists(district_name):
                updated_office_held_values['district_name'] = district_name
            if positive_value_exists(office_held_name):
                # Note: When we decide to start updating office_held_name elsewhere within We Vote, we should stop
                #  updating office_held_name via subsequent Google Civic imports
                updated_office_held_values['office_held_name'] = office_held_name
                # We store the literal spelling here, so we can match in the future, even if we customize measure_title
                updated_office_held_values['google_civic_office_held_name'] = office_held_name
            # if positive_value_exists(number_elected):
            #     updated_office_held_values['number_elected'] = number_elected
            if positive_value_exists(office_held_level0):
                updated_office_held_values['office_held_level0'] = office_held_level0
            if positive_value_exists(office_held_level1):
                updated_office_held_values['office_held_level1'] = office_held_level1
            if positive_value_exists(office_held_level2):
                updated_office_held_values['office_held_level2'] = office_held_level2
            if positive_value_exists(office_held_role0):
                updated_office_held_values['office_held_role0'] = office_held_role0
            if positive_value_exists(office_held_role1):
                updated_office_held_values['office_held_role1'] = office_held_role1
            if positive_value_exists(office_held_role2):
                updated_office_held_values['office_held_role2'] = office_held_role2
            # if positive_value_exists(primary_party):
            #     updated_office_held_values['primary_party'] = primary_party
            # if positive_value_exists(district_scope):
            #     updated_office_held_values['district_scope'] = district_scope
            # if positive_value_exists(google_ballot_placement):
            #     updated_office_held_values['google_ballot_placement'] = google_ballot_placement
            if positive_value_exists(ctcl_office_uuid):
                updated_office_held_values['ctcl_uuid'] = ctcl_office_uuid
            # if positive_value_exists(vote_usa_office_id):
            #     updated_office_held_values['vote_usa_office_id'] = vote_usa_office_id
            if positive_value_exists(this_year):
                year_with_data_key = 'year_with_data_' + str(this_year)
                updated_office_held_values[year_with_data_key] = True

            try:
                if positive_value_exists(proceed_to_create_office_held):
                    update_or_create_office_held_results = office_held_manager.create_office_held_row_entry(
                        office_held_name=office_held_name,
                        defaults=updated_office_held_values)
                else:
                    update_or_create_office_held_results = office_held_manager.update_office_held_row_entry(
                        office_held_we_vote_id=office_held_we_vote_id,
                        defaults=updated_office_held_values)

                if update_or_create_office_held_results['success']:
                    try:
                        if positive_value_exists(update_or_create_office_held_results['office_held_found']):
                            office_held_object = update_or_create_office_held_results['office_held']
                            office_held_name = office_held_object.office_held_name
                            office_held_id = office_held_object.id
                            office_held_we_vote_id = office_held_object.we_vote_id
                            if office_held_we_vote_id not in new_office_held_we_vote_ids_list:
                                new_office_held_we_vote_ids_list.append(office_held_we_vote_id)
                            if type(existing_offices_held_by_ocd_and_name_dict) is not dict:
                                existing_offices_held_by_ocd_and_name_dict = {}
                            if ocd_division_id not in existing_offices_held_by_ocd_and_name_dict:
                                existing_offices_held_by_ocd_and_name_dict[ocd_division_id] = {}
                            if type(existing_offices_held_by_ocd_and_name_dict[ocd_division_id]) is not dict:
                                existing_offices_held_by_ocd_and_name_dict[ocd_division_id] = {}
                            existing_offices_held_by_ocd_and_name_dict[ocd_division_id][
                                office_held_name] = office_held_object
                    except Exception as e:
                        status += "PROBLEM_CACHING_OFFICE_HELD: " + str(e) + " "
                else:
                    office_held_name = ''
                    office_held_id = 0
                    office_held_we_vote_id = ''
                    success = False
                    status += update_or_create_office_held_results['status']
            except Exception as e:
                status += "CREATE_OR_UPDATE_OFFICE_HELD_ERROR: " + str(e) + " "
        else:
            results = {
                'success': False,
                'status': status,
                'saved': 0,
                'updated': 0,
                'not_processed': 1,
                'office_held_dict_list_for_location': office_held_dict_list_for_location,
                'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
                'existing_representative_objects_dict': existing_representative_objects_dict,
                'new_representative_we_vote_ids_list': new_representative_we_vote_ids_list,
                'new_office_held_we_vote_ids_list': new_office_held_we_vote_ids_list,
            }
            return results
    else:
        if hasattr(office_held_object, 'office_held_name'):
            office_held_name = office_held_object.office_held_name
        if hasattr(office_held_object, 'id'):
            office_held_id = office_held_object.id
        if hasattr(office_held_object, 'we_vote_id'):
            office_held_we_vote_id = office_held_object.we_vote_id

    if positive_value_exists(office_held_we_vote_id):
        # These will get stored to associate the office held with this polling location, so we can show
        #  voters near this polling location who their elected officials are
        office_held_json = {
            'office_held_name':             office_held_name,
            'office_held_we_vote_id':       office_held_we_vote_id,
            'offices_held_display_order':   offices_held_display_order,
        }
        office_held_dict_list_for_location.append(office_held_json)

    if positive_value_exists(office_held_we_vote_id):
        try:
            # Modeled after groom_and_store_google_civic_candidates_json_2021
            results = groom_and_store_officials_list_from_json(
                ocd_division_id=ocd_division_id,
                officials_list=officials_for_this_office_held_list,
                state_code=state_code,
                office_held_id=office_held_id,
                office_held_we_vote_id=office_held_we_vote_id,
                office_held_name=office_held_name,
                existing_representative_objects_dict=existing_representative_objects_dict,
                existing_representative_to_office_held_links_dict=existing_representative_to_office_held_links_dict,
                new_representative_we_vote_ids_list=new_representative_we_vote_ids_list,
                update_or_create_rules=update_or_create_rules,
                use_ctcl=use_ctcl,
                use_google_civic=use_google_civic)
            existing_representative_objects_dict = results['existing_representative_objects_dict']
            existing_representative_to_office_held_links_dict = \
                results['existing_representative_to_office_held_links_dict']
            new_representative_we_vote_ids_list = results['new_representative_we_vote_ids_list']
        except Exception as e:
            status += "COULD_NOT_STORE_REPRESENTATIVES: " + str(e) + " "
    results = {
        'success':                                      success,
        'status':                                       status,
        'office_held_dict_list_for_location':           office_held_dict_list_for_location,
        'existing_offices_held_by_ocd_and_name_dict':   existing_offices_held_by_ocd_and_name_dict,
        'existing_representative_objects_dict':         existing_representative_objects_dict,
        'existing_representative_to_office_held_links_dict': existing_representative_to_office_held_links_dict,
        'new_representative_we_vote_ids_list':          new_representative_we_vote_ids_list,
        'new_office_held_we_vote_ids_list':             new_office_held_we_vote_ids_list,
    }
    return results


def groom_and_store_officials_list_from_json(
        ocd_division_id='',
        officials_list=[],
        office_held_id=0,
        office_held_we_vote_id='',
        office_held_name='',
        election_year_integer=0,
        existing_representative_objects_dict={},
        existing_representative_to_office_held_links_dict={},
        new_representative_we_vote_ids_list=[],
        state_code='',
        update_or_create_rules={},
        use_ctcl=False,
        use_google_civic=False,
        use_vote_usa=False):
    status = ''
    success = True
    results = {}
    representative_manager = RepresentativeManager()
    today = datetime.now().date()
    this_year = 0
    if today and today.year:
        this_year = convert_to_int(today.year)

    for one_official in officials_list:
        create_representative = False
        representative_object = None
        representative_object_found = False

        representative_name = one_official['name'] if 'name' in one_official else ''
        # For some reason Google Civic API violates the JSON standard and uses a / in front of '
        representative_name = representative_name.replace("/'", "'")
        representative_name = representative_name.strip()
        # We want to save the name exactly as it comes from the Google Civic API
        google_civic_representative_name = one_official['name'] if 'name' in one_official else ''
        google_civic_representative_name = google_civic_representative_name.strip()
        political_party = one_official['party'] if 'party' in one_official else ''
        political_party = political_party.strip()
        representative_url = None
        representative_url2 = None
        representative_url3 = None
        wikipedia_url = None
        if 'urls' in one_official:
            representative_urls = one_official['urls']
            for one_url in representative_urls:
                if 'wikipedia.org' in one_url and not positive_value_exists(wikipedia_url):
                    # Store the first incoming URL which has a wikipedia url in it
                    wikipedia_url = one_url
                elif not positive_value_exists(representative_url):
                    representative_url = one_url
                elif not positive_value_exists(representative_url2):
                    representative_url2 = one_url
                elif not positive_value_exists(representative_url3):
                    representative_url3 = one_url
        if positive_value_exists(representative_url):
            if 'http' not in representative_url:
                representative_url = 'https://' + representative_url
        if positive_value_exists(representative_url2):
            if 'http' not in representative_url2:
                representative_url2 = 'https://' + representative_url2
        if positive_value_exists(representative_url3):
            if 'http' not in representative_url3:
                representative_url3 = 'https://' + representative_url3
        # representative_contact_form_url = one_official['representative_contact_form_url'] \
        #     if 'representative_contact_form_url' in one_official else ''
        # if positive_value_exists(representative_contact_form_url):
        #     if 'http' not in representative_contact_form_url:
        #         representative_contact_form_url = 'https://' + representative_contact_form_url
        representative_email = None
        representative_email2 = None
        representative_email3 = None
        if 'emails' in one_official:
            representative_emails = one_official['emails']
            for one_email in representative_emails:
                if not positive_value_exists(representative_email):
                    representative_email = one_email
                elif not positive_value_exists(representative_email2):
                    representative_email2 = one_email
                elif not positive_value_exists(representative_email3):
                    representative_email3 = one_email
        representative_phone = None
        representative_phone2 = None
        representative_phone3 = None
        if 'phones' in one_official:
            representative_phones = one_official['phones']
            for one_phone in representative_phones:
                if not positive_value_exists(representative_phone):
                    representative_phone = one_phone
                elif not positive_value_exists(representative_phone2):
                    representative_phone2 = one_phone
                elif not positive_value_exists(representative_phone3):
                    representative_phone3 = one_phone
        photo_url = ''
        photo_url_from_ctcl = ''
        photo_url_from_google_civic = ''
        photo_url_from_vote_usa = ''
        if positive_value_exists(use_ctcl):
            photo_url_from_ctcl = one_official['photoUrl'] if 'photoUrl' in one_official else ''
        elif positive_value_exists(use_google_civic):
            photo_url_from_google_civic = one_official['photoUrl'] if 'photoUrl' in one_official else ''
        elif positive_value_exists(use_vote_usa):
            photo_url_from_vote_usa = one_official['photoUrl'] if 'photoUrl' in one_official else ''
        else:
            photo_url = one_official['photoUrl'] if 'photoUrl' in one_official else ''

        # Make sure we start with empty channel values
        ballotpedia_representative_url = ''
        blogger_url = ''
        representative_twitter_handle = ''
        facebook_url = ''
        flickr_url = ''
        go_fund_me_url = ''
        google_plus_url = ''
        instagram_handle = ''
        instagram_url = ''
        linkedin_url = ''
        twitter_url = ''
        vimeo_url = ''
        youtube_url = ''
        if 'channels' in one_official:
            channels = one_official['channels']
            for one_channel in channels:
                if 'type' in one_channel:
                    if one_channel['type'] == 'BallotPedia':
                        ballotpedia_representative_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(ballotpedia_representative_url):
                            if 'http' not in ballotpedia_representative_url:
                                ballotpedia_representative_url = 'https://' + ballotpedia_representative_url
                    if one_channel['type'] == 'Blogger':
                        blogger_url = one_channel['id'] if 'id' in one_channel else ''
                    if one_channel['type'] == 'Facebook':
                        facebook_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(facebook_url):
                            facebook_handle = extract_facebook_username_from_text_string(facebook_url)
                            if positive_value_exists(facebook_handle):
                                facebook_url = "https://facebook.com/" + str(facebook_handle)
                            else:
                                facebook_url = ''
                        else:
                            facebook_url = ''
                    if one_channel['type'] == 'Flickr':
                        flickr_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(flickr_url):
                            if 'http' not in flickr_url:
                                flickr_url = 'https://' + flickr_url
                    if one_channel['type'] == 'GooglePlus':
                        google_plus_url = one_channel['id'] if 'id' in one_channel else ''
                    if one_channel['type'] == 'GoFundMe':
                        go_fund_me_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(go_fund_me_url):
                            if 'http' not in go_fund_me_url:
                                go_fund_me_url = 'https://' + go_fund_me_url
                    if one_channel['type'] == 'Instagram':
                        instagram_handle = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(instagram_handle):
                            instagram_handle = extract_instagram_handle_from_text_string(instagram_handle)
                    if one_channel['type'] == 'LinkedIn':
                        linkedin_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(linkedin_url):
                            if 'http' not in linkedin_url:
                                linkedin_url = 'https://' + linkedin_url
                    if one_channel['type'] == 'Twitter':
                        twitter_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(twitter_url):
                            representative_twitter_handle = extract_twitter_handle_from_text_string(twitter_url)
                    if one_channel['type'] == 'Vimeo':
                        vimeo_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(vimeo_url):
                            if 'http' not in vimeo_url:
                                vimeo_url = 'https://' + vimeo_url
                    if one_channel['type'] == 'Wikipedia':
                        wikipedia_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(wikipedia_url):
                            if 'http' not in wikipedia_url:
                                wikipedia_url = 'https://' + wikipedia_url
                        if not positive_value_exists(ballotpedia_representative_url):
                            if "ballotpedia.org" in wikipedia_url:
                                ballotpedia_representative_url = wikipedia_url
                    if one_channel['type'] == 'YouTube':
                        youtube_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(youtube_url):
                            if 'http' not in youtube_url:
                                youtube_url = 'https://' + youtube_url

        continue_searching_for_representative = True
        allowed_to_create_representatives = 'create_representatives' in update_or_create_rules \
                                            and positive_value_exists(update_or_create_rules['create_representatives'])
        allowed_to_update_representatives = 'update_representatives' in update_or_create_rules \
                                            and positive_value_exists(update_or_create_rules['update_representatives'])
        if positive_value_exists(use_google_civic) and positive_value_exists(office_held_we_vote_id) and \
                positive_value_exists(representative_name):
            if office_held_we_vote_id in existing_representative_objects_dict:
                if representative_name in existing_representative_objects_dict[office_held_we_vote_id]:
                    representative_object = \
                        existing_representative_objects_dict[office_held_we_vote_id][representative_name]
                    representative_we_vote_id = representative_object.we_vote_id
                    if positive_value_exists(representative_we_vote_id):
                        representative_object_found = True
                        continue_searching_for_representative = False
            if continue_searching_for_representative:
                # Does representative already exist?
                results = representative_manager.retrieve_representative(
                    office_held_we_vote_id=office_held_we_vote_id,
                    google_civic_representative_name=google_civic_representative_name,
                    read_only=(not allowed_to_update_representatives))
                if results['success']:
                    if results['representative_list_found']:
                        # Use the first one found
                        representative_list = results['representative_list']
                        representative_object = representative_list[0]
                        representative_object_found = True
                    elif results['representative_found']:
                        representative_object = results['representative']
                        representative_object_found = True
                    else:
                        representative_object_found = False
                    if representative_object_found:
                        try:
                            if type(existing_representative_objects_dict) is not dict:
                                existing_representative_objects_dict = {}
                            if office_held_we_vote_id not in existing_representative_objects_dict:
                                existing_representative_objects_dict[office_held_we_vote_id] = {}
                            if type(existing_representative_objects_dict[office_held_we_vote_id]) is not dict:
                                existing_representative_objects_dict[office_held_we_vote_id] = {}
                            existing_representative_objects_dict[office_held_we_vote_id][
                                representative_object.representative_name] = representative_object
                        except Exception as e:
                            status += "COULD_NOT_CACHE_REPRESENTATIVE: " + str(e) + " "
                    else:
                        continue_searching_for_representative = True
                else:
                    success = False

        if success and not representative_object_found:
            create_representative = True

        # Make sure we have the minimum variables required to uniquely identify a representative
        proceed_to_create_representative = positive_value_exists(create_representative) \
            and allowed_to_create_representatives
        proceed_to_update_representatives = allowed_to_update_representatives
        if success and (proceed_to_create_representative or proceed_to_update_representatives) \
                and (positive_value_exists(office_held_we_vote_id) and positive_value_exists(representative_name)):
            updated_representative_values = {
            }
            if positive_value_exists(facebook_url):
                updated_representative_values['facebook_url'] = facebook_url
            if positive_value_exists(google_civic_representative_name):
                # We store literal spelling here, so we can match in the future, even if we change representative_name
                updated_representative_values['google_civic_representative_name'] = google_civic_representative_name
            if positive_value_exists(instagram_handle):
                updated_representative_values['instagram_handle'] = instagram_handle
            if positive_value_exists(linkedin_url):
                updated_representative_values['linkedin_url'] = linkedin_url
            if positive_value_exists(ocd_division_id):
                updated_representative_values['ocd_division_id'] = ocd_division_id
            if positive_value_exists(office_held_id):
                updated_representative_values['office_held_id'] = office_held_id
            if positive_value_exists(office_held_we_vote_id):
                updated_representative_values['office_held_we_vote_id'] = office_held_we_vote_id
            if positive_value_exists(office_held_name):
                updated_representative_values['office_held_name'] = office_held_name
            # if positive_value_exists(photo_url):
            #     updated_representative_values['photo_url'] = photo_url
            if positive_value_exists(photo_url_from_ctcl):
                updated_representative_values['photo_url_from_ctcl'] = photo_url_from_ctcl
            if positive_value_exists(photo_url_from_google_civic):
                updated_representative_values['photo_url_from_google_civic'] = photo_url_from_google_civic
            if positive_value_exists(photo_url_from_vote_usa):
                updated_representative_values['photo_url_from_vote_usa'] = photo_url_from_vote_usa
            if positive_value_exists(political_party):
                updated_representative_values['political_party'] = political_party
            # if positive_value_exists(politician_id):
            #     updated_representative_values['politician_id'] = politician_id
            # if positive_value_exists(politician_we_vote_id):
            #     updated_representative_values['politician_we_vote_id'] = politician_we_vote_id
            if positive_value_exists(representative_email):
                updated_representative_values['representative_email'] = representative_email
            if positive_value_exists(representative_email2):
                updated_representative_values['representative_email2'] = representative_email2
            if positive_value_exists(representative_email3):
                updated_representative_values['representative_email3'] = representative_email3
            if positive_value_exists(representative_name):
                # Note: When we decide to start updating representative_name elsewhere within We Vote, we should stop
                #  updating representative_name via subsequent Google Civic imports
                updated_representative_values['representative_name'] = representative_name
            if positive_value_exists(representative_phone):
                updated_representative_values['representative_phone'] = representative_phone
            if positive_value_exists(representative_phone2):
                updated_representative_values['representative_phone2'] = representative_phone2
            if positive_value_exists(representative_phone3):
                updated_representative_values['representative_phone3'] = representative_phone3
            if positive_value_exists(representative_twitter_handle):
                updated_representative_values['representative_twitter_handle'] = representative_twitter_handle
            if positive_value_exists(representative_url):
                updated_representative_values['representative_url'] = representative_url
            if positive_value_exists(representative_url2):
                updated_representative_values['representative_url2'] = representative_url2
            if positive_value_exists(representative_url3):
                updated_representative_values['representative_url3'] = representative_url3
            if positive_value_exists(state_code):
                updated_representative_values['state_code'] = state_code.lower()
            if positive_value_exists(wikipedia_url):
                updated_representative_values['wikipedia_url'] = wikipedia_url
            if positive_value_exists(this_year):
                year_in_office_key = 'year_in_office_' + str(this_year)
                updated_representative_values[year_in_office_key] = True
            if positive_value_exists(youtube_url):
                updated_representative_values['youtube_url'] = youtube_url

            if positive_value_exists(proceed_to_create_representative):
                # If here we only want to create new representatives -- not update existing representatives
                representative_results = \
                    representative_manager.create_representative_row_entry(update_values=updated_representative_values)
                representative_created = representative_results['representative_created']
                if positive_value_exists(representative_created):
                    try:
                        representative_object = representative_results['representative']
                        representative_we_vote_id = representative_object.we_vote_id
                        if representative_we_vote_id not in new_representative_we_vote_ids_list:
                            new_representative_we_vote_ids_list.append(representative_we_vote_id)
                        if positive_value_exists(use_google_civic):
                            results = retrieve_and_store_google_civic_representative_photo(representative_object)
                            if results['success']:
                                representative_object = results['representative']
                        # elif positive_value_exists(use_vote_usa):
                        #     if positive_value_exists(representative_object.photo_url_from_vote_usa):
                        #         from import_export_vote_usa.controllers import \
                        #             retrieve_and_store_vote_usa_representative_photo
                        #         results = retrieve_and_store_vote_usa_representative_photo(representative_object)
                        #         if results['success']:
                        #             representative_object = results['representative']
                        # else:
                        #     if positive_value_exists(representative_object.photo_url):
                        #         representative_results = \
                        #             representative_manager.modify_representative_with_organization_endorsements_image(
                        #                 representative_object, photo_url, True)
                        #         if representative_results['success']:
                        #             representative_object = representative_results['representative']
                        # Now put it into a local variable for later use
                        if type(existing_representative_objects_dict) is not dict:
                            existing_representative_objects_dict = {}
                        if office_held_we_vote_id not in existing_representative_objects_dict:
                            existing_representative_objects_dict[office_held_we_vote_id] = {}
                        if type(existing_representative_objects_dict[office_held_we_vote_id]) is not dict:
                            existing_representative_objects_dict[office_held_we_vote_id] = {}
                        existing_representative_objects_dict[office_held_we_vote_id][
                            representative_object.representative_name] = representative_object
                    except Exception as e:
                        status += "PROBLEM_AFTER_REPRESENTATIVE_CREATED: " + str(e) + " "
            # else:
            #     representative_results = representative_manager.update_representative_row_entry(
            #         google_civic_election_id=google_civic_election_id,
            #         ocd_division_id=ocd_division_id,
            #         office_held_id=office_held_id,
            #         office_held_we_vote_id=office_held_we_vote_id,
            #         google_civic_representative_name=google_civic_representative_name,
            #         updated_representative_values=updated_representative_values)
            #     representative_found = representative_results['representative_found']
            #     if positive_value_exists(representative_found):
            #         representative_object = representative_results['representative']
            #         representative_we_vote_id = representative_object.we_vote_id
            #     if positive_value_exists(use_ctcl):
            #         existing_representative_objects_dict[representative_ctcl_uuid] = representative_object
            #     elif positive_value_exists(use_vote_usa):
            #         existing_representative_objects_dict[vote_usa_politician_id] = representative_object

        # DALE 2023-01-14 Not sure we are going to use a separate link object for Representatives and OfficeHeld
        # if positive_value_exists(representative_we_vote_id):
        #     # Now make sure we have a CandidateToOfficeLink
        #     results = is_there_existing_representative_to_office_link(
        #         existing_representative_to_office_held_links_dict=existing_representative_to_office_held_links_dict,
        #         office_held_we_vote_id=office_held_we_vote_id,
        #         representative_we_vote_id=representative_we_vote_id,
        #     )
        #     existing_representative_to_office_held_links_dict = results['existing_representative_to_office_held_links_dict']
        #     if not results['representative_to_office_link_found']:
        #         link_results = representative_manager.get_or_create_representative_to_office_link(
        #             representative_we_vote_id=representative_we_vote_id,
        #             office_held_we_vote_id=office_held_we_vote_id,
        #             google_civic_election_id=google_civic_election_id,
        #             state_code=state_code)
        #         if positive_value_exists(link_results['success']):
        #             results = update_existing_representative_to_office_held_links_dict(
        #                 existing_representative_to_office_held_links_dict=existing_representative_to_office_held_links_dict,
        #                 office_held_we_vote_id=office_held_we_vote_id,
        #                 representative_we_vote_id=representative_we_vote_id,
        #             )
        #             existing_representative_to_office_held_links_dict = \
        #             results['existing_representative_to_office_held_links_dict']

    results = {
        'status':                                       status,
        'success':                                      success,
        'existing_representative_objects_dict':         existing_representative_objects_dict,
        'existing_representative_to_office_held_links_dict': existing_representative_to_office_held_links_dict,
        'new_representative_we_vote_ids_list':          new_representative_we_vote_ids_list,
    }
    return results


def retrieve_and_store_google_civic_representative_photo(representative):
    success = True
    status = ''
    status += "RETRIEVE_AND_STORE_GOOGLE_CIVIC_REPRESENTATIVE_PHOTO_NOT_IMPLEMENTED_YET "
    # TODO Update this with photo_url_from_google_civic
    # cache_results = cache_master_and_resized_image(
    #     representative_id=representative.id,
    #     representative_we_vote_id=representative.we_vote_id,
    #     photo_url_from_google_civic=representative.photo_url_from_google_civic,
    #     image_source=IMAGE_SOURCE_GOOGLE_CIVIC)
    # vote_usa_profile_image_url_https = cache_results['cached_other_source_image_url_https']
    # we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
    # we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
    # we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
    #
    # representative.vote_usa_profile_image_url_https = vote_usa_profile_image_url_https
    # representative.we_vote_hosted_profile_vote_usa_image_url_large = we_vote_hosted_profile_image_url_large
    # representative.we_vote_hosted_profile_vote_usa_image_url_medium = we_vote_hosted_profile_image_url_medium
    # representative.we_vote_hosted_profile_vote_usa_image_url_tiny = we_vote_hosted_profile_image_url_tiny
    #
    # if representative.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
    #     representative.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_VOTE_USA
    # if representative.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_VOTE_USA:
    #     representative.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
    #     representative.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
    #     representative.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
    #
    # try:
    #     representative.save()
    #     status += "CANDIDATE_SAVED "
    # except Exception as e:
    #     success = False
    #     status += "CANDIDATE_NOT_SAVED: " + str(e) + " "

    results = {
        'success':          success,
        'status':           status,
        'representative':   representative,
    }
    return results


def retrieve_google_civic_representatives_from_polling_location_api(
        polling_location_we_vote_id="",
        polling_location=None,
        state_code="",
        batch_process_id=0,
        batch_set_id=0,
        existing_offices_held_by_ocd_and_name_dict={},
        existing_representative_objects_dict={},
        existing_representative_to_office_held_links_dict={},
        new_office_held_we_vote_ids_list=[],
        new_representative_we_vote_ids_list=[],
        update_or_create_rules={}):
    """

    :param polling_location_we_vote_id:
    :param polling_location:
    :param state_code:
    :param batch_process_id:
    :param batch_set_id:
    :param existing_offices_held_by_ocd_and_name_dict:
    :param existing_representative_objects_dict:
    :param existing_representative_to_office_held_links_dict:
    :param new_office_held_we_vote_ids_list:
    :param new_representative_we_vote_ids_list:
    :param update_or_create_rules:
    :return:
    """
    success = True
    status = ""
    ballot_items_count = 0
    polling_location_found = False
    batch_header_id = 0
    successful_representatives_api_call = False

    if not positive_value_exists(polling_location_we_vote_id) and not polling_location:
        status += "MISSING_POLLING_LOCATION_INFO_FOR_REPRESENTATIVES "
        results = {
            'success':                                  False,
            'status':                                   status,
            'ballot_items_count':                       ballot_items_count,
            'successful_representatives_api_call':      successful_representatives_api_call,
            'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
            'existing_representative_objects_dict':     existing_representative_objects_dict,
            'existing_representative_to_office_held_links_dict': existing_representative_to_office_held_links_dict,
            'new_office_held_we_vote_ids_list':         new_office_held_we_vote_ids_list,
            'new_representative_we_vote_ids_list':      new_representative_we_vote_ids_list,
        }
        return results

    # Create rules
    if 'create_office_helds' not in update_or_create_rules:
        update_or_create_rules['create_office_helds'] = True
    if 'create_representatives' not in update_or_create_rules:
        update_or_create_rules['create_representatives'] = True
    # Update rules
    if 'update_office_helds' not in update_or_create_rules:
        update_or_create_rules['update_office_helds'] = False
    if 'update_representatives' not in update_or_create_rules:
        update_or_create_rules['update_representatives'] = False

    latitude = 0.0
    longitude = 0.0
    text_for_map_search = ''
    polling_location_manager = PollingLocationManager()
    if polling_location:
        polling_location_found = True
        polling_location_we_vote_id = polling_location.we_vote_id
        latitude = polling_location.latitude
        longitude = polling_location.longitude
        text_for_map_search = polling_location.get_text_for_map_search()
    elif positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(
            0, polling_location_we_vote_id, read_only=True)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            latitude = polling_location.latitude
            longitude = polling_location.longitude
            text_for_map_search = polling_location.get_text_for_map_search()
            polling_location_found = True

    if polling_location_found:
        if not positive_value_exists(text_for_map_search):
            success = False
            status += "MISSING_TEXT_FOR_MAP_SEARCH-GOOGLE_CIVIC "
            results = {
                'success':                                  success,
                'status':                                   status,
                'ballot_items_count':                       ballot_items_count,
                'successful_representatives_api_call':      successful_representatives_api_call,
                'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
                'existing_representative_objects_dict':     existing_representative_objects_dict,
                'existing_representative_to_office_held_links_dict': existing_representative_to_office_held_links_dict,
                'new_office_held_we_vote_ids_list':         new_office_held_we_vote_ids_list,
                'new_representative_we_vote_ids_list':      new_representative_we_vote_ids_list,
            }
            return results

        if not positive_value_exists(state_code):
            if positive_value_exists(polling_location.state):
                state_code = polling_location.state
            else:
                state_code = "na"

        try:
            # Get representatives info for this address
            response = requests.get(
                REPRESENTATIVES_BY_ADDRESS_URL,
                params={
                    "address": text_for_map_search,
                    "key": GOOGLE_CIVIC_API_KEY,
                })
            representative_info_by_address_json = json.loads(response.text)
        except Exception as e:
            success = False
            status += 'GOOGLE_CIVIC_API_END_POINT_CRASH: ' + str(e) + ' '
            log_entry_message = status
            results = polling_location_manager.create_polling_location_log_entry(
                batch_process_id=batch_process_id,
                is_from_google_civic=True,
                kind_of_log_entry=KIND_OF_LOG_ENTRY_API_END_POINT_CRASH,
                log_entry_message=log_entry_message,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                text_for_map_search=text_for_map_search,
            )
            status += results['status']
            results = polling_location_manager.update_polling_location_with_log_counts(
                is_from_google_civic=True,
                polling_location_we_vote_id=polling_location_we_vote_id,
                update_error_counts=True,
            )
            status += results['status']
            handle_exception(e, logger=logger, exception_message=status)
            results = {
                'success':                                  success,
                'status':                                   status,
                'ballot_items_count':                       ballot_items_count,
                'successful_representatives_api_call':      successful_representatives_api_call,
                'existing_offices_held_by_ocd_and_name_dict': existing_offices_held_by_ocd_and_name_dict,
                'existing_representative_objects_dict':     existing_representative_objects_dict,
                'existing_representative_to_office_held_links_dict': existing_representative_to_office_held_links_dict,
                'new_office_held_we_vote_ids_list':         new_office_held_we_vote_ids_list,
                'new_representative_we_vote_ids_list':      new_representative_we_vote_ids_list,
            }
            return results

        try:
            # Use API call counter to track the number of queries we are doing each day
            api_counter_manager = GoogleCivicApiCounterManager()
            api_counter_manager.create_counter_entry('representatives')

            if 'offices' in representative_info_by_address_json:
                office_held_dict_list_for_location = []
                office_held_array_index = 0
                offices_held_display_order = 1
                for office_held_dict in representative_info_by_address_json['offices']:
                    groom_results = groom_and_store_office_held_with_representatives_google_civic_json(
                        divisions_dict=representative_info_by_address_json.get('divisions', {}),
                        office_held_dict_list_for_location=office_held_dict_list_for_location,
                        office_held_dict=office_held_dict,
                        offices_held_display_order=offices_held_display_order,
                        office_held_array_index=office_held_array_index,
                        officials_list=representative_info_by_address_json.get('officials', []),
                        state_code=state_code,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        existing_offices_held_by_ocd_and_name_dict=existing_offices_held_by_ocd_and_name_dict,
                        existing_representative_objects_dict=existing_representative_objects_dict,
                        existing_representative_to_office_held_links_dict=
                        existing_representative_to_office_held_links_dict,
                        new_office_held_we_vote_ids_list=new_office_held_we_vote_ids_list,
                        new_representative_we_vote_ids_list=new_representative_we_vote_ids_list,
                        update_or_create_rules=update_or_create_rules,
                        use_google_civic=True,
                        )
                    status += groom_results['status']
                    office_held_dict_list_for_location = groom_results['office_held_dict_list_for_location']
                    existing_offices_held_by_ocd_and_name_dict = groom_results['existing_offices_held_by_ocd_and_name_dict']
                    existing_representative_objects_dict = groom_results['existing_representative_objects_dict']
                    existing_representative_to_office_held_links_dict = groom_results['existing_representative_to_office_held_links_dict']
                    new_office_held_we_vote_ids_list = groom_results['new_office_held_we_vote_ids_list']
                    new_representative_we_vote_ids_list = groom_results['new_representative_we_vote_ids_list']
                    office_held_array_index += 1
                    offices_held_display_order += 1
                    successful_representatives_api_call = groom_results['success'] or successful_representatives_api_call

                # If we successfully save all of a location's elected representatives,
                # create/update an OfficesHeldForLocation entry
                if office_held_dict_list_for_location and len(office_held_dict_list_for_location) > 0:
                    office_held_manager = OfficeHeldManager()
                    results = office_held_manager.retrieve_latest_offices_held_for_location(
                        polling_location_we_vote_id=polling_location_we_vote_id,
                    )
                    if results['success']:
                        if results['offices_held_for_location_found']:
                            # TODO: Complete the update process
                            # Figure out if:
                            # 1) any entries have been added or removed,
                            # 2) the office_held_names have changed, or
                            # 3) the order of existing entries has changed
                            pass
                        else:
                            prepare_default_results = create_default_values_for_offices_held_for_location(
                                office_held_dict_list_for_location=office_held_dict_list_for_location
                            )
                            if prepare_default_results['success']:
                                defaults = prepare_default_results['defaults']
                                defaults['date_last_retrieved'] = now()

                                today = datetime.now().date()
                                this_year = 0
                                if today and today.year:
                                    this_year = convert_to_int(today.year)
                                if positive_value_exists(this_year):
                                    year_with_data_key = 'year_with_data_' + str(this_year)
                                    defaults[year_with_data_key] = True

                                results = office_held_manager.create_offices_held_for_location_row_entry(
                                    polling_location_we_vote_id=polling_location_we_vote_id,
                                    state_code=state_code,
                                    defaults=defaults)
                                if not results['success']:
                                    status += results['status']
                            else:
                                status += "COULD_NOT_CREATE_DEFAULT_VALUES_FOR_OFFICES_HELD_FOR_LOCATION "
                    else:
                        status += results['status']
                        status += "FAILED-retrieve_latest_offices_held_for_location "
                    # Store that we have reviewed this polling_location, so we don't retrieve it again in the next chunk
                    results = polling_location_manager.create_polling_location_log_entry(
                        batch_process_id=batch_process_id,
                        is_from_google_civic=True,
                        kind_of_log_entry=KIND_OF_LOG_ENTRY_REPRESENTATIVES_RECEIVED,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        state_code=state_code,
                        text_for_map_search=text_for_map_search,
                    )
                    if not results['success']:
                        status += results['status']
                    results = polling_location_manager.update_polling_location_with_log_counts(
                        is_from_google_civic=True,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        update_data_counts=True,
                        is_successful_retrieve=True,
                    )
                    status += results['status']
                else:
                    # We need to at least to mark the BallotReturned entry with a new date_last_updated date,
                    #  so we can move on to other ballot returned entries.
                    status += "OFFICES_HELD_BUT_NO_INCOMING_REPRESENTATIVES_FOUND_GOOGLE_CIVIC "
            else:
                # Create BallotReturnedEmpty entry, so we don't keep retrieving this map point
                kind_of_log_entry = KIND_OF_LOG_ENTRY_NO_OFFICES_HELD
                log_entry_message = ''
                try:
                    error = representative_info_by_address_json.get('error', {})
                    errors = error.get('errors', {})
                    if len(errors):
                        log_entry_message = errors
                        for one_error in errors:
                            try:
                                if 'reason' in one_error:
                                    if one_error['reason'] == "notFound":
                                        # Representatives not found at this location
                                        address_not_found = True
                                        status += "ERROR_REPRESENTATIVES_notFound "
                                    elif one_error['reason'] == "parseError":
                                        kind_of_log_entry = KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR
                                        status += "ERROR_REPRESENTATIVES_parseError "
                                    elif one_error['reason'] == "rateLimitExceeded":
                                        kind_of_log_entry = KIND_OF_LOG_ENTRY_RATE_LIMIT_ERROR
                                        status += "ERROR_rateLimitExceeded "
                                    else:
                                        reason_not_found = True
                                        status += "ERROR_REPRESENTATIVES_REASON_NOT_RECOGNIZED: " \
                                                  "" + str(one_error['reason']) + ' '
                            except Exception as e:
                                status += "PROBLEM_PARSING_REPRESENTATIVES_ERROR_GOOGLE_CIVIC: " + str(e) + ' '
                except Exception as e:
                    status += "PROBLEM_GETTING_REPRESENTATIVES_ERRORS_GOOGLE_CIVIC: " + str(e) + " "
                    log_entry_message += status
                results = polling_location_manager.create_polling_location_log_entry(
                    batch_process_id=batch_process_id,
                    is_from_google_civic=True,
                    kind_of_log_entry=kind_of_log_entry,
                    log_entry_message=log_entry_message,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    state_code=state_code,
                    text_for_map_search=text_for_map_search,
                )
                status += results['status']
                results = polling_location_manager.update_polling_location_with_log_counts(
                    is_from_google_civic=True,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    update_error_counts=True,
                )
                status += results['status']
        except Exception as e:
            success = False
            status += 'RETRIEVE_REPRESENTATIVES_FROM_POLLING_LOCATIONS_GOOGLE_CIVIC-ERROR: ' + str(e) + ' '
            handle_exception(e, logger=logger, exception_message=status)
    else:
        status += "POLLING_LOCATION_NOT_FOUND-GOOGLE_CIVIC-(" + str(polling_location_we_vote_id) + ") "
    results = {
        'success':                                  success,
        'status':                                   status,
        'ballot_items_count':                       ballot_items_count,
        'successful_representatives_api_call':      successful_representatives_api_call,
        'existing_offices_held_by_ocd_and_name_dict':   existing_offices_held_by_ocd_and_name_dict,
        'existing_representative_objects_dict':     existing_representative_objects_dict,
        'existing_representative_to_office_held_links_dict':  existing_representative_to_office_held_links_dict,
        'new_office_held_we_vote_ids_list':         new_office_held_we_vote_ids_list,
        'new_representative_we_vote_ids_list':      new_representative_we_vote_ids_list,
    }
    return results


def retrieve_representatives_from_google_civic_api(text_for_map_search):
    # Request json file from Google servers
    # logger.info("Loading ballot for one address from voterInfoQuery from Google servers")
    success = True
    status = ""

    # results = {
    #     'status':               'FUNCTION_TO_BE_BUILT ',
    #     'success':              False,
    #     'text_for_map_search':  text_for_map_search,
    #     'locations_retrieved':  False,
    # }
    # return results

    # print("retrieving one ballot for " + str(text_for_map_search))
    response = requests.get(REPRESENTATIVES_BY_ADDRESS_URL, params={
        "key": GOOGLE_CIVIC_API_KEY,
        "address": text_for_map_search,
    })

    structured_json = json.loads(response.text)
    if 'success' in structured_json and not positive_value_exists(structured_json['success']):
        import_results = {
            'success':              False,
            'status':               "Error: " + structured_json['status'],
            'locations_retrieved':  False,
            'structured_json':      {},
        }
        return import_results

    # # # For internal testing. Write the json retrieved above into a local file
    # # with open('/Users/dalemcgrew/PythonProjects/WeVoteServer/'
    # #           'import_export_google_civic/import_data/voterInfoQuery_VA_sample.json', 'w') as f:
    # #     json.dump(structured_json, f)
    # #     f.closed
    # #
    # # # TEMP - FROM FILE (so we aren't hitting Google Civic API during development)
    # # with open("import_export_google_civic/import_data/voterInfoQuery_VA_sample.json") as json_data:
    # #     structured_json = json.load(json_data)
    #
    # # Verify that we got a ballot. (If you use an address in California for an election in New York,
    # #  you won't get a ballot for example.)
    # success = False
    # election_data_retrieved = False
    # polling_location_retrieved = False
    # contests_retrieved = False
    # election_administration_data_retrieved = False
    # google_civic_election_id = 0
    # google_response_address_not_found = False
    # error = structured_json.get('error', {})
    # errors = error.get('errors', {})
    # if len(errors):
    #     logger.debug("retrieve_one_ballot_from_google_civic_api failed: " + str(errors))
    #     for one_error_from_google in errors:
    #         if 'reason' in one_error_from_google:
    #             if one_error_from_google['reason'] == "notFound":
    #                 # Ballot data not found at this location
    #                 google_response_address_not_found = True
    #             if one_error_from_google['reason'] == "parseError":
    #                 # Not an address format Google can parse
    #                 google_response_address_not_found = True
    #
    # if 'election' in structured_json:
    #     if 'id' in structured_json['election']:
    #         election_data_retrieved = True
    #         success = True
    #         google_civic_election_id = structured_json['election']['id']
    #
    # #  We can get a google_civic_election_id back even though we don't have contest data.
    # #  If we get a google_civic_election_id back but no contest data,
    # reach out again with the google_civic_election_id
    # #  so we can then get contest data

    # Use Google Civic API call counter to track the number of queries we are doing each day
    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_api_counter_manager.create_counter_entry('representatives')

    # if 'pollingLocations' in structured_json:
    #     polling_location_retrieved = True
    #     success = True
    #
    # if 'contests' in structured_json:
    #     if len(structured_json['contests']) > 0:
    #         contests_retrieved = True
    #         success = True
    #
    # if 'state' in structured_json:
    #     if len(structured_json['state']) > 0:
    #         if 'electionAdministrationBody' in structured_json['state'][0]:
    #             election_administration_data_retrieved = True
    #             success = True

    results = {
        'success':              success,
        'status':               status,
        'locations_retrieved':  True,
        'structured_json':      structured_json,
    }
    return results


def store_representatives_from_google_civic_api(one_representative_json, voter_id=0, polling_location_we_vote_id=''):
    """
    When we pass in a voter_id, we want to save this ballot related to the voter.
    When we pass in polling_location_we_vote_id, we want to save a ballot for that area, which is useful for
    getting new voters started by showing them a ballot roughly near them.
    """
    results = {
        'status':                       'FUNCTION_TO_BE_BUILT ',
        'success':                      False,
        'polling_location_we_vote_id':  polling_location_we_vote_id,
        'voter_id':                     voter_id,
    }
    return results

    # #     "election": {
    # #     "electionDay": "2015-11-03",
    # #     "id": "4162",
    # #     "name": "Virginia General Election",
    # #     "ocdDivisionId": "ocd-division/country:us/state:va"
    # # },
    # if 'election' not in one_representative_json:
    #     results = {
    #         'status': 'BALLOT_JSON_MISSING_ELECTION',
    #         'success': False,
    #         'google_civic_election_id': 0,
    #     }
    #     return results
    #
    # election_day_text = ''
    # election_description_text = ''
    # if 'electionDay' in one_representative_json['election']:
    #     election_day_text = one_representative_json['election']['electionDay']
    # if 'name' in one_representative_json['election']:
    #     election_description_text = one_representative_json['election']['name']
    #
    # if 'id' not in one_representative_json['election']:
    #     results = {
    #         'status': 'BALLOT_JSON_MISSING_ELECTION_ID',
    #         'success': False,
    #         'google_civic_election_id': 0,
    #     }
    #     return results
    #
    # voter_address_dict = one_representative_json['normalizedInput'] if 'normalizedInput' in one_representative_json else {}
    # if positive_value_exists(voter_id):
    #     if positive_value_exists(voter_address_dict):
    #         # When saving a ballot for an individual voter, use this data to update voter address with the
    #         #  normalized address information returned from Google Civic
    #         # "normalizedInput": {
    #         #   "line1": "254 hartford st",
    #         #   "city": "san francisco",
    #         #   "state": "CA",
    #         #   "zip": "94114"
    #         #  },
    #         voter_address_manager = VoterAddressManager()
    #         voter_address_manager.update_voter_address_with_normalized_values(
    #             voter_id, voter_address_dict)
    #         # Note that neither 'success' nor 'status' are set here because updating the voter_address with normalized
    #         # values isn't critical to the success of storing the ballot for a voter
    # # We don't store the normalized address information when we capture a ballot for a map point
    #
    # google_civic_election_id = one_representative_json['election']['id']
    # ocd_division_id = one_representative_json['election']['ocdDivisionId']
    # state_code = extract_state_from_ocd_division_id(ocd_division_id)
    # if not positive_value_exists(state_code):
    #     # We have a backup method of looking up state from one_representative_json['state']['name']
    #     # in case the ocd state fails
    #     state_name = ''
    #     if 'state' in one_representative_json:
    #         if 'name' in one_representative_json['state']:
    #             state_name = one_representative_json['state']['name']
    #         elif len(one_representative_json['state']) > 0:
    #             # In some cases, like test elections 2000 a list is returned in one_representative_json['state']
    #             for one_state_entry in one_representative_json['state']:
    #                 if 'name' in one_state_entry:
    #                     state_name = one_state_entry['name']
    #     state_code = convert_state_text_to_state_code(state_name)
    # if not positive_value_exists(state_code):
    #     if 'normalizedInput' in one_representative_json:
    #         state_code = one_representative_json['normalizedInput']['state']
    #
    # # Loop through all contests and store in local db cache
    # if 'contests' in one_representative_json:
    #     results = process_contests_from_structured_json(one_representative_json['contests'], google_civic_election_id,
    #                                                     ocd_division_id, state_code, voter_id,
    #                                                     polling_location_we_vote_id)
    #
    #     status = results['status']
    #     success = results['success']
    # else:
    #     status = "STORE_ONE_BALLOT_NO_CONTESTS_FOUND"
    #     success = False
    #     results = {
    #         'status':                   status,
    #         'success':                  success,
    #         'ballot_returned_found':    False,
    #         'ballot_returned':          ballot_returned,
    #         'google_civic_election_id': google_civic_election_id,
    #     }
    #     return results
    #
    # # When saving a ballot for individual voter, loop through all pollingLocations and store in local db
    # # process_polling_locations_from_structured_json(one_representative_json['pollingLocations'])
    #
    # # If we successfully save a ballot, create/update a BallotReturned entry
    # ballot_returned_found = False
    # if hasattr(ballot_returned, 'voter_id') and positive_value_exists(ballot_returned.voter_id):
    #     ballot_returned_found = True
    # elif hasattr(ballot_returned, 'polling_location_we_vote_id') \
    #         and positive_value_exists(ballot_returned.polling_location_we_vote_id):
    #     ballot_returned_found = True
    # else:
    #     ballot_returned = BallotReturned()
    #
    # is_test_election = True if positive_value_exists(google_civic_election_id) \
    #     and convert_to_int(google_civic_election_id) == 2000 else False
    #
    # # If this is connected to a polling_location, retrieve the polling_location_information
    # ballot_returned_manager = BallotReturnedManager()
    # polling_location_manager = PollingLocationManager()
    #
    # if not is_test_election:
    #     if not ballot_returned_found:
    #         # If ballot_returned wasn't passed into this function, retrieve it
    #         if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
    #             results = ballot_returned_manager.retrieve_ballot_returned_from_voter_id(
    #                 voter_id, google_civic_election_id)
    #             if results['ballot_returned_found']:
    #                 ballot_returned_found = True
    #                 ballot_returned = results['ballot_returned']
    #         elif positive_value_exists(polling_location_we_vote_id) and \
    #                 positive_value_exists(google_civic_election_id):
    #             results = ballot_returned_manager.retrieve_ballot_returned_from_polling_location_we_vote_id(
    #                 polling_location_we_vote_id, google_civic_election_id)
    #             if results['ballot_returned_found']:
    #                 ballot_returned_found = True  # If the update fails, return the original ballot_returned object
    #                 ballot_returned = results['ballot_returned']
    #
    #     # Now update ballot_returned with latest values
    #     if positive_value_exists(ballot_returned_found):
    #         if positive_value_exists(voter_address_dict):
    #             update_results = ballot_returned_manager.update_ballot_returned_with_normalized_values(
    #                     voter_address_dict, ballot_returned)
    #             ballot_returned = update_results['ballot_returned']
    #     else:
    #         create_results = ballot_returned_manager.create_ballot_returned_with_normalized_values(
    #             voter_address_dict,
    #             election_day_text, election_description_text,
    #             google_civic_election_id, voter_id, polling_location_we_vote_id
    #         )
    #         ballot_returned_found = create_results['ballot_returned_found']
    #         ballot_returned = create_results['ballot_returned']
    #
    #     # Currently we don't report the success or failure of storing ballot_returned
    #
    # if positive_value_exists(ballot_returned_found):
    #     if positive_value_exists(polling_location_we_vote_id):
    #         results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
    #         if results['polling_location_found']:
    #             polling_location = results['polling_location']
    #             ballot_returned.latitude = polling_location.latitude
    #             ballot_returned.longitude = polling_location.longitude
    #             ballot_returned.save()
    #
    # results = {
    #     'status':                   status,
    #     'success':                  success,
    #     'ballot_returned_found':    ballot_returned_found,
    #     'ballot_returned':          ballot_returned,
    #     'google_civic_election_id': google_civic_election_id,
    # }
    # return results
