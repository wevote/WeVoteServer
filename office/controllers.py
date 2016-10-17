# office/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestOfficeListManager, ContestOfficeManager
from ballot.models import OFFICE
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
import json
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")


def offices_import_from_sample_file():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    with open("office/import_data/contest_office_sample.json") as json_data:
        structured_json = json.load(json_data)

    return offices_import_from_structured_json(structured_json)


def offices_import_from_master_server(request, google_civic_election_id=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    messages.add_message(request, messages.INFO, "Loading Contest Offices from We Vote Master servers")
    request = requests.get(OFFICES_SYNC_URL, params={
        "key": WE_VOTE_API_KEY,
        "format":   'json',
        "google_civic_election_id": google_civic_election_id,
    })
    structured_json = json.loads(request.text)

    results = filter_offices_structured_json_for_local_duplicates(structured_json)
    filtered_structured_json = results['structured_json']
    duplicates_removed = results['duplicates_removed']

    import_results = offices_import_from_structured_json(filtered_structured_json)
    import_results['duplicates_removed'] = duplicates_removed

    return import_results


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
        we_vote_id = one_office['we_vote_id'] if 'we_vote_id' in one_office else ''
        office_name = one_office['office_name'] if 'office_name' in one_office else ''
        state_code = one_office['state_code'] if 'state_code' in one_office else ''

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

        results = office_manager_list.retrieve_possible_duplicate_offices(google_civic_election_id, office_name,
                                                                          state_code, we_vote_id_from_master)

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
            district_id = one_office['district_id'] if 'district_id' in one_office else ''
            office_name = one_office['office_name'] if 'office_name' in one_office else ''
            state_code = one_office['state_code'] if 'state_code' in one_office else ''
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
            wikipedia_id = one_office['wikipedia_id'] if 'wikipedia_id' in one_office else ''
            updated_contest_office_values = {
                'we_vote_id': we_vote_id,
                'google_civic_election_id': google_civic_election_id,
                'district_id': district_id,
                'district_name': district_name,
                'office_name': office_name,
                'state_code': state_code,
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
                'wikipedia_id': wikipedia_id,
            }
            results = office_manager.update_or_create_contest_office(
                we_vote_id, maplight_id, google_civic_election_id, office_name, state_code,
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
            'ballot_item_display_name': contest_office.office_name,
            'ocd_division_id':          contest_office.ocd_division_id,
            'maplight_id':              contest_office.maplight_id,
            'ballotpedia_id':           contest_office.ballotpedia_id,
            'wikipedia_id':             contest_office.wikipedia_id,
            'number_voting_for':        contest_office.number_voting_for,
            'number_elected':           contest_office.number_elected,
            'state_code':               contest_office.state_code,
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
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
