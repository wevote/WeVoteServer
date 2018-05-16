# office/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestOfficeListManager, ContestOfficeManager, CONTEST_OFFICE_UNIQUE_IDENTIFIERS, ContestOffice
from ballot.models import OFFICE
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
import json
from position.controllers import update_all_position_details_from_contest_office
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut


def offices_import_from_sample_file():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    with open("office/import_data/contest_office_sample.json") as json_data:
        structured_json = json.load(json_data)

    return offices_import_from_structured_json(structured_json)


def offices_import_from_master_server(request, google_civic_election_id='', state_code=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    import_results, structured_json = process_request_from_master(
        request, "Loading Contest Offices from We Vote Master servers",
        OFFICES_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": state_code,
        }
    )

    if import_results['success']:
        results = filter_offices_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        import_results = offices_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def fetch_duplicate_office_count(contest_office, ignore_office_id_list):
    if not hasattr(contest_office, 'google_civic_election_id'):
        return 0

    if not positive_value_exists(contest_office.google_civic_election_id):
        return 0

    # Search for other offices within this election that match name and election
    contest_office_list_manager = ContestOfficeListManager()
    return contest_office_list_manager.fetch_offices_from_non_unique_identifiers_count(
        contest_office.google_civic_election_id, contest_office.state_code,
        contest_office.office_name, ignore_office_id_list)


def find_duplicate_contest_office(contest_office, ignore_office_id_list):
    if not hasattr(contest_office, 'google_civic_election_id'):
        error_results = {
            'success':                                  False,
            'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_MISSING_OFFICE_OBJECT ",
            'contest_office_merge_possibility_found':   False,
        }
        return error_results

    if not positive_value_exists(contest_office.google_civic_election_id):
        error_results = {
            'success':                                False,
            'status':                                 "FIND_DUPLICATE_CONTEST_OFFICE_MISSING_GOOGLE_CIVIC_ELECTION_ID ",
            'contest_office_merge_possibility_found': False,
        }
        return error_results

    # Search for other contest offices within this election that match name and election
    contest_office_list_manager = ContestOfficeListManager()
    try:
        results = contest_office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
            contest_office.office_name, contest_office.google_civic_election_id, contest_office.state_code,
            contest_office.district_id, contest_office.district_name, ignore_office_id_list)

        if results['contest_office_found']:
            contest_office_merge_conflict_values = figure_out_conflict_values(contest_office, results['contest_office'])

            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_DUPLICATES_FOUND",
                'contest_office_merge_possibility_found':   True,
                'contest_office_merge_possibility':         results['contest_office'],
                'contest_office_merge_conflict_values':     contest_office_merge_conflict_values,
            }
            return results
        elif results['contest_office_list_found']:
            # Only deal with merging the incoming contest office and the first on found
            contest_office_merge_conflict_values = \
                figure_out_conflict_values(contest_office, results['contest_office_list'][0])

            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_DUPLICATES_FOUND",
                'contest_office_merge_possibility_found':   True,
                'contest_office_merge_possibility':         results['contest_office_list'][0],
                'contest_office_merge_conflict_values':     contest_office_merge_conflict_values,
            }
            return results
        else:
            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_NO_DUPLICATES_FOUND",
                'contest_office_merge_possibility_found':   False,
            }
            return results

    except ContestOffice.DoesNotExist:
        pass
    except Exception as e:
        pass

    results = {
        'success':                                  True,
        'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_NO_DUPLICATES_FOUND",
        'contest_office_merge_possibility_found':   False,
    }
    return results


def figure_out_conflict_values(contest_office1, contest_office2):
    contest_office_merge_conflict_values = {}

    for attribute in CONTEST_OFFICE_UNIQUE_IDENTIFIERS:
        try:
            contest_office1_attribute = getattr(contest_office1, attribute)
            contest_office2_attribute = getattr(contest_office2, attribute)
            if contest_office1_attribute is None and contest_office2_attribute is None:
                contest_office_merge_conflict_values[attribute] = 'MATCHING'
            elif contest_office1_attribute is None or contest_office1_attribute is "":
                contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE2'
            elif contest_office2_attribute is None or contest_office2_attribute is "":
                contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE1'
            elif contest_office1_attribute == contest_office2_attribute:
                contest_office_merge_conflict_values[attribute] = 'MATCHING'
            else:
                contest_office_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return contest_office_merge_conflict_values


def filter_offices_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove offices that seem to be duplicates, but have different we_vote_id's
    :param structured_json:
    :return:
    """
    office_manager_list = ContestOfficeListManager()
    duplicates_removed = 0
    filtered_structured_json = []
    for one_office in structured_json:
        google_civic_election_id = one_office['google_civic_election_id'] \
            if 'google_civic_election_id' in one_office else 0
        state_code = one_office['state_code'] if 'state_code' in one_office else ''
        we_vote_id = one_office['we_vote_id'] if 'we_vote_id' in one_office else ''
        office_name = one_office['office_name'] if 'office_name' in one_office else ''

        # district_id = one_office['district_id'] if 'district_id' in one_office else ''
        # ocd_division_id = one_office['ocd_division_id'] if 'ocd_division_id' in one_office else ''
        # number_voting_for = one_office['number_voting_for'] if 'number_voting_for' in one_office else ''
        # number_elected = one_office['number_elected'] if 'number_elected' in one_office else ''
        # contest_level0 = one_office['contest_level0'] if 'contest_level0' in one_office else ''
        # contest_level1 = one_office['contest_level1'] if 'contest_level1' in one_office else ''
        # contest_level2 = one_office['contest_level2'] if 'contest_level2' in one_office else ''
        # primary_party = one_office['primary_party'] if 'primary_party' in one_office else ''
        # district_name = one_office['district_name'] if 'district_name' in one_office else ''
        # district_scope = one_office['district_scope'] if 'district_scope' in one_office else ''
        # electorate_specifications = one_office['electorate_specifications'] \
        #     if 'electorate_specifications' in one_office else ''
        # special = one_office['special'] if 'special' in one_office else ''
        # maplight_id = one_office['maplight_id'] if 'maplight_id' in one_office else 0
        # ballotpedia_id = one_office['ballotpedia_id'] if 'ballotpedia_id' in one_office else ''
        # wikipedia_id = one_office['wikipedia_id'] if 'wikipedia_id' in one_office else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = office_manager_list.retrieve_possible_duplicate_offices(google_civic_election_id, state_code,
                                                                          office_name, we_vote_id_from_master)

        if results['office_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_office)

    offices_results = {
        'success':              True,
        'status':               "FILTER_OFFICES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return offices_results


def offices_import_from_structured_json(structured_json):
    office_manager = ContestOfficeManager()
    offices_saved = 0
    offices_updated = 0
    offices_not_processed = 0
    for one_office in structured_json:
        google_civic_election_id = one_office['google_civic_election_id'] \
            if 'google_civic_election_id' in one_office else 0
        we_vote_id = one_office['we_vote_id'] if 'we_vote_id' in one_office else ''
        if positive_value_exists(google_civic_election_id) and positive_value_exists(we_vote_id):
            state_code = one_office['state_code'] if 'state_code' in one_office else ''
            district_id = one_office['district_id'] if 'district_id' in one_office else ''
            office_name = one_office['office_name'] if 'office_name' in one_office else ''
            ocd_division_id = one_office['ocd_division_id'] if 'ocd_division_id' in one_office else ''
            number_voting_for = one_office['number_voting_for'] if 'number_voting_for' in one_office else ''
            number_elected = one_office['number_elected'] if 'number_elected' in one_office else ''
            contest_level0 = one_office['contest_level0'] if 'contest_level0' in one_office else ''
            contest_level1 = one_office['contest_level1'] if 'contest_level1' in one_office else ''
            contest_level2 = one_office['contest_level2'] if 'contest_level2' in one_office else ''
            primary_party = one_office['primary_party'] if 'primary_party' in one_office else ''
            district_name = one_office['district_name'] if 'district_name' in one_office else ''
            district_scope = one_office['district_scope'] if 'district_scope' in one_office else ''
            electorate_specifications = one_office['electorate_specifications'] \
                if 'electorate_specifications' in one_office else ''
            special = one_office['special'] if 'special' in one_office else ''
            maplight_id = one_office['maplight_id'] if 'maplight_id' in one_office else 0
            ballotpedia_id = one_office['ballotpedia_id'] if 'ballotpedia_id' in one_office else ''
            # Equivalent to elected_office
            ballotpedia_office_id = one_office['ballotpedia_office_id'] if 'ballotpedia_office_id' in one_office else ''
            ballotpedia_office_name = one_office['ballotpedia_office_name'] \
                if 'ballotpedia_office_name' in one_office else ''
            ballotpedia_office_url = one_office['ballotpedia_office_url'] \
                if 'ballotpedia_office_url' in one_office else ''
            # Equivalent to contest_office
            ballotpedia_race_id = one_office['ballotpedia_race_id'] if 'ballotpedia_race_id' in one_office else ''
            ballotpedia_race_office_level = one_office['ballotpedia_race_office_level'] \
                if 'ballotpedia_race_office_level' in one_office else ''
            wikipedia_id = one_office['wikipedia_id'] if 'wikipedia_id' in one_office else ''
            updated_contest_office_values = {
                'we_vote_id': we_vote_id,
                'google_civic_election_id': google_civic_election_id,
                'state_code': state_code,
                'district_id': district_id,
                'district_name': district_name,
                'office_name': office_name,
                # The rest of the values
                'ocd_division_id': ocd_division_id,
                'number_voting_for': number_voting_for,
                'number_elected': number_elected,
                'contest_level0': contest_level0,
                'contest_level1': contest_level1,
                'contest_level2': contest_level2,
                'primary_party': primary_party,
                'district_scope': district_scope,
                'electorate_specifications': electorate_specifications,
                'special': special,
                'maplight_id': maplight_id,
                'ballotpedia_id': ballotpedia_id,
                'ballotpedia_office_id': ballotpedia_office_id,
                'ballotpedia_office_name': ballotpedia_office_name,
                'ballotpedia_office_url': ballotpedia_office_url,
                'ballotpedia_race_id': ballotpedia_race_id,
                'ballotpedia_race_office_level': ballotpedia_race_office_level,
                'wikipedia_id': wikipedia_id,
            }
            results = office_manager.update_or_create_contest_office(
                we_vote_id, maplight_id, google_civic_election_id, office_name, district_id,
                updated_contest_office_values)
        else:
            offices_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_office_created']:
                offices_saved += 1
            else:
                offices_updated += 1

    offices_results = {
        'success':          True,
        'status':           "OFFICE_IMPORT_PROCESS_COMPLETE",
        'saved':            offices_saved,
        'updated':          offices_updated,
        'not_processed':    offices_not_processed,
    }
    return offices_results


def office_retrieve_for_api(office_id, office_we_vote_id):
    """
    Used by the api
    :param office_id:
    :param office_we_vote_id:
    :return:
    """
    # NOTE: Office retrieve is independent of *who* wants to see the data. Office retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItemsFromGoogleCivic does

    if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
            'state_code':               '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_manager = ContestOfficeManager()
    if positive_value_exists(office_id):
        results = office_manager.retrieve_contest_office_from_id(office_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(office_we_vote_id):
        results = office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
            'state_code':               '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_office = results['contest_office']
        json_data = {
            'status':                   status,
            'success':                  True,
            'kind_of_ballot_item':      OFFICE,
            'id':                       contest_office.id,
            'we_vote_id':               contest_office.we_vote_id,
            'google_civic_election_id': contest_office.google_civic_election_id,
            'state_code':               contest_office.state_code,
            'ballot_item_display_name': contest_office.office_name,
            'ocd_division_id':          contest_office.ocd_division_id,
            'maplight_id':              contest_office.maplight_id,
            'ballotpedia_id':           contest_office.ballotpedia_id,
            'ballotpedia_office_id':    contest_office.ballotpedia_office_id,
            'ballotpedia_office_url':   contest_office.ballotpedia_office_url,
            'ballotpedia_race_id':      contest_office.ballotpedia_race_id,
            'wikipedia_id':             contest_office.wikipedia_id,
            'number_voting_for':        contest_office.number_voting_for,
            'number_elected':           contest_office.number_elected,
            'primary_party':            contest_office.primary_party,
            'district_name':            contest_office.district_name,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
            'state_code':               '',
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def push_contest_office_data_to_other_table_caches(contest_office_id=0, contest_office_we_vote_id=''):
    contest_office_manager = ContestOfficeManager()
    if positive_value_exists(contest_office_we_vote_id):
        results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id)
    elif positive_value_exists(contest_office_id):
        results = contest_office_manager.retrieve_contest_office_from_id(contest_office_id)

    if results['contest_office_found']:
        contest_office = results['contest_office']
        save_position_from_office_results = update_all_position_details_from_contest_office(contest_office)
        return save_position_from_office_results
    else:
        results = {
            'success':                      False,
            'positions_updated_count':      0,
            'positions_not_updated_count':  0,
            'update_all_position_results':  []
        }
        return results
