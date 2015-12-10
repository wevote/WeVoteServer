# office/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestOfficeManager
from config.base import get_environment_variable
from django.http import HttpResponse
from exception.models import handle_exception, handle_record_not_found_exception, handle_record_not_saved_exception
import json
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
# CANDIDATE_CAMPAIGNS_URL = get_environment_variable("CANDIDATE_CAMPAIGNS_URL")


def offices_import_from_sample_file(request=None, load_from_uri=False):  # TODO FINISH BUILDING/TESTING THIS
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # if load_from_uri:
    #     # Request json file from We Vote servers
    #     messages.add_message(request, messages.INFO, "Loading ContestOffice IDs from We Vote Master servers")
    #     request = requests.get(CANDIDATE_CAMPAIGNS_URL, params={
    #         "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    #     })
    #     structured_json = json.loads(request.text)
    # else:

    # Load saved json from local file
    # messages.add_message(request, messages.INFO, "Loading ContestOffices from local file")

    with open("office/import_data/contest_office_sample.json") as json_data:
        structured_json = json.load(json_data)

    office_manager = ContestOfficeManager()
    offices_saved = 0
    offices_updated = 0
    offices_not_processed = 0
    for one_office in structured_json:
        google_civic_election_id = one_office['google_civic_election_id'] if 'google_civic_election_id' in one_office else ''
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
            electorate_specifications = one_office['electorate_specifications'] if 'electorate_specifications' in one_office else ''
            special = one_office['special'] if 'special' in one_office else ''
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
            }
            results = office_manager.update_or_create_contest_office(
                we_vote_id, google_civic_election_id, district_id, district_name, office_name,
                state_code, updated_contest_office_values)
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
        'saved': offices_saved,
        'updated': offices_updated,
        'not_processed': offices_not_processed,
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
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
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
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_office = results['contest_office']
        json_data = {
            'status':                   status,
            'success':                  True,
            'office_id':                contest_office.id,
            'office_we_vote_id':        contest_office.we_vote_id,
            'google_civic_election_id': contest_office.google_civic_election_id,
            'office_name':              contest_office.office_name,
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
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
