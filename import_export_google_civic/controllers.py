# import_export_google_civic/controllers.py
# Brought to you by We Vote. Be good.
# Complete description of all Google Civic fields:
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/index.html
# voterInfoQuery Details:
# https://developers.google.com/
#   resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html#voterInfoQuery

# -*- coding: UTF-8 -*-

import json
import requests
from .models import GoogleCivicApiCounterManager
from ballot.models import BallotItemManager, BallotItemListManager
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from election.models import ElectionManager
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from voter.models import VoterAddressManager
from wevote_functions.models import extract_state_from_ocd_division_id, logger, positive_value_exists

GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
ELECTION_QUERY_URL = get_environment_variable("ELECTION_QUERY_URL")
VOTER_INFO_URL = get_environment_variable("VOTER_INFO_URL")
VOTER_INFO_JSON_FILE = get_environment_variable("VOTER_INFO_JSON_FILE")


# GoogleRepresentatives
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.representatives.html
def process_candidates_from_structured_json(
        candidates_structured_json, google_civic_election_id, ocd_division_id, state_code, contest_office_id,
        contest_office_we_vote_id):
    """
    "candidates": [
        {
         "name": "Nancy Pelosi",
         "party": "Democratic"
        },
        {
         "name": "John Dennis",
         "party": "Republican",
         "candidateUrl": "http://www.johndennisforcongress.com/",
         "channels": [
          {
           "type": "Facebook",
           "id": "https://www.facebook.com/johndennis2010"
          },
          {
           "type": "Twitter",
           "id": "https://twitter.com/johndennis2012"
    """
    results = {}
    for one_candidate in candidates_structured_json:
        candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        # For some reason Google Civic API violates the JSON standard and uses a
        candidate_name = candidate_name.replace('/', "'")
        # We want to save the name exactly as it comes from the Google Civic API
        google_civic_candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        party = one_candidate['party'] if 'party' in one_candidate else ''
        order_on_ballot = one_candidate['orderOnBallot'] if 'orderOnBallot' in one_candidate else 0
        candidate_url = one_candidate['candidateUrl'] if 'candidateUrl' in one_candidate else ''
        photo_url = one_candidate['photoUrl'] if 'photoUrl' in one_candidate else ''
        email = one_candidate['email'] if 'email' in one_candidate else ''
        phone = one_candidate['phone'] if 'phone' in one_candidate else ''

        # set them to channel values to empty
        facebook_url = ''
        twitter_url = ''
        google_plus_url = ''
        youtube_url = ''
        if 'channels' in one_candidate:
            channels = one_candidate['channels']
            for one_channel in channels:
                if 'type' in one_channel:
                    if one_channel['type'] == 'Facebook':
                        facebook_url = one_channel['id'] if 'id' in one_channel else ''
                    if one_channel['type'] == 'Twitter':
                        twitter_url = one_channel['id'] if 'id' in one_channel else ''
                    if one_channel['type'] == 'GooglePlus':
                        google_plus_url = one_channel['id'] if 'id' in one_channel else ''
                    if one_channel['type'] == 'YouTube':
                        youtube_url = one_channel['id'] if 'id' in one_channel else ''

        we_vote_id = ''
        if google_civic_election_id and ocd_division_id and contest_office_id and candidate_name:
            updated_candidate_campaign_values = {
                # Values we search against
                'google_civic_election_id': google_civic_election_id,
                'ocd_division_id': ocd_division_id,
                'contest_office_id': contest_office_id,
                'contest_office_we_vote_id': contest_office_we_vote_id,
                # Note: When we decide to start updating candidate_name elsewhere within We Vote, we should stop
                #  updating candidate_name via subsequent Google Civic imports
                'candidate_name': candidate_name,
                # The rest of the values
                'state_code': state_code,  # Not required due to federal candidates
                'party': party,
                'candidate_email': email,
                'candidate_phone': phone,
                'order_on_ballot': order_on_ballot,
                'candidate_url': candidate_url,
                'photo_url': photo_url,
                'facebook_url': facebook_url,
                'twitter_url': twitter_url,
                'google_plus_url': google_plus_url,
                'youtube_url': youtube_url,
                'google_civic_candidate_name': google_civic_candidate_name,
            }
            candidate_campaign_manager = CandidateCampaignManager()
            results = candidate_campaign_manager.update_or_create_candidate_campaign(
                we_vote_id, google_civic_election_id, ocd_division_id, contest_office_id, contest_office_we_vote_id,
                google_civic_candidate_name, updated_candidate_campaign_values)

    return results


def process_contest_office_from_structured_json(
        one_contest_office_structured_json, google_civic_election_id, ocd_division_id, local_ballot_order, state_code,
        voter_id):
    logger.debug("General contest_type")

    # Protect against the case where this is NOT an office
    if 'candidates' not in one_contest_office_structured_json:
        is_not_office = True
    else:
        is_not_office = False
    if is_not_office:
        update_or_create_contest_office_results = {
            'success': False,
            'saved': 0,
            'updated': 0,
            'not_processed': 1,
        }
        return update_or_create_contest_office_results

    office_name = one_contest_office_structured_json['office']

    # The number of candidates that a voter may vote for in this contest.
    if 'numberVotingFor' in one_contest_office_structured_json:
        number_voting_for = one_contest_office_structured_json['numberVotingFor']
    else:
        number_voting_for = 1

    # The number of candidates that will be elected to office in this contest.
    if 'numberElected' in one_contest_office_structured_json:
        number_elected = one_contest_office_structured_json['numberElected']
    else:
        number_elected = 1

    # These are several fields that are shared in common between offices and measures
    results = process_contest_common_fields_from_structured_json(one_contest_office_structured_json)

    # ballot_placement: A number specifying the position of this contest on the voter's ballot.
    google_ballot_placement = results['ballot_placement']
    primary_party = results['primary_party']  # If this is a partisan election, the name of the party it is for.

    # district_scope: The geographic scope of this district. If unspecified the
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = results['district_scope']
    district_id = results['district_id']
    district_name = results['district_name']  # The name of the district.

    # electorate_specifications: A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = results['electorate_specifications']

    # special: "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = results['special']

    # We want to convert this from an array to three fields for the same table
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
    level_structured_json = \
        one_contest_office_structured_json['level'] if 'level' in one_contest_office_structured_json else ''
    contest_level = []
    for one_level in level_structured_json:
        contest_level.append(one_level)
    if 0 in contest_level:
        contest_level0 = contest_level[0]
    else:
        contest_level0 = ''
    if 1 in contest_level:
        contest_level1 = contest_level[1]
    else:
        contest_level1 = ''
    if 2 in contest_level:
        contest_level2 = contest_level[2]
    else:
        contest_level2 = ''

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
    # roles_structured_json = \
    #     one_contest_office_structured_json['roles'] if 'roles' in one_contest_office_structured_json else ''
    # for one_role in roles_structured_json:
    # Figure out how we are going to use level info

    candidates_structured_json = \
        one_contest_office_structured_json['candidates'] if 'candidates' in one_contest_office_structured_json else ''

    we_vote_id = ''
    # Note that all of the information saved here is independent of a particular voter
    if google_civic_election_id and (district_id or district_name) and office_name:
        updated_contest_office_values = {
            # Values we search against
            'google_civic_election_id': google_civic_election_id,
            'state_code': state_code.lower(),  # Not required for cases of federal offices
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
        }
        contest_office_manager = ContestOfficeManager()
        update_or_create_contest_office_results = contest_office_manager.update_or_create_contest_office(
            we_vote_id, google_civic_election_id, district_id, district_name, office_name, state_code,
            updated_contest_office_values)
    else:
        update_or_create_contest_office_results = {
            'success': False,
            'saved': 0,
            'updated': 0,
            'not_processed': 1,
        }

    if update_or_create_contest_office_results['success']:
        contest_office = update_or_create_contest_office_results['contest_office']
        contest_office_id = contest_office.id
        contest_office_we_vote_id = contest_office.we_vote_id
        ballot_item_label = contest_office.office_name
    else:
        contest_office_id = 0
        contest_office_we_vote_id = ''
        ballot_item_label = ''

    # If a voter_id was passed in, save an entry for this office for the voter's ballot
    if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) \
            and positive_value_exists(contest_office_id):
        ballot_item_manager = BallotItemManager()
        ballot_item_manager.update_or_create_ballot_item_for_voter(
            voter_id, google_civic_election_id, google_ballot_placement, ballot_item_label,
            local_ballot_order, contest_office_id, contest_office_we_vote_id)
        # We leave off these and rely on default empty values: contest_measure_id, contest_measure_we_vote_id

    # Note: We do not need to connect the candidates with the voter here for a ballot item
    process_candidates_from_structured_json(
        candidates_structured_json, google_civic_election_id, ocd_division_id, state_code, contest_office_id,
        contest_office_we_vote_id)

    return update_or_create_contest_office_results


def extract_value_from_array(structured_json, index_key, default_value):
    if index_key in structured_json:
        return structured_json[index_key]
    else:
        return default_value


def process_contest_common_fields_from_structured_json(one_contest_structured_json):
    # These following fields exist for both candidates and referendum

    results = {}
    # A number specifying the position of this contest on the voter's ballot.
    results['ballot_placement'] = extract_value_from_array(one_contest_structured_json, 'ballotPlacement', 0)

    # If this is a partisan election, the name of the party it is for.
    results['primary_party'] = extract_value_from_array(one_contest_structured_json, 'primaryParty', '')

    if 'district' in one_contest_structured_json:
        # The name of the district.
        results['district_name'] = \
            one_contest_structured_json['district']['name'] if 'name' in one_contest_structured_json['district'] else ''

        # The geographic scope of this district. If unspecified the district's geography is not known.
        # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
        # cityWide, township, countyCouncil, cityCouncil, ward, special
        results['district_scope'] = \
            one_contest_structured_json['district']['scope'] \
            if 'scope' in one_contest_structured_json['district'] else ''

        # An identifier for this district, relative to its scope. For example, the 34th State Senate district
        # would have id "34" and a scope of stateUpper.
        results['district_id'] = \
            one_contest_structured_json['district']['id'] if 'id' in one_contest_structured_json['district'] else ''

    # A description of any additional eligibility requirements for voting in this contest.
    results['electorate_specifications'] = \
        one_contest_structured_json['electorateSpecifications'] \
        if 'electorateSpecifications' in one_contest_structured_json else ''

    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    results['special'] = one_contest_structured_json['special'] if 'special' in one_contest_structured_json else ''

    return results


def process_contests_from_structured_json(
        contests_structured_json, google_civic_election_id, ocd_division_id, state_code, voter_id):
    """
    Take in the portion of the json related to contests, and save to the database
    "type": 'General', "House of Delegates", 'locality', 'Primary', 'Run-off', "State Senate", "Municipal"
    or
    "type": "Referendum",
    """
    local_ballot_order = 0
    contests_saved = 0
    contests_updated = 0
    contests_not_processed = 0
    for one_contest in contests_structured_json:
        local_ballot_order += 1  # Needed if ballotPlacement isn't provided by Google Civic
        contest_type = one_contest['type']

        # Is the contest is a referendum/initiative/measure?
        if contest_type.lower() == 'referendum':
            process_contest_results = process_contest_referendum_from_structured_json(
                one_contest, google_civic_election_id, ocd_division_id, local_ballot_order, state_code, voter_id)
            if process_contest_results['saved']:
                contests_saved += 1
            elif process_contest_results['updated']:
                contests_updated += 1
            elif process_contest_results['not_processed']:
                contests_not_processed += 1
        # All other contests are for an elected office
        else:
            process_contest_results = process_contest_office_from_structured_json(
                one_contest, google_civic_election_id, ocd_division_id, local_ballot_order, state_code, voter_id)
            if process_contest_results['saved']:
                contests_saved += 1
            elif process_contest_results['updated']:
                contests_updated += 1
            elif process_contest_results['not_processed']:
                contests_not_processed += 1

    results = {
        'success': True,
        'status': 'Contests saved: {saved}, '
                  'contests updated: {updated}, '
                  'contests not_processed: {not_processed}'.format(saved=contests_saved, updated=contests_updated,
                                                                   not_processed=contests_not_processed),
    }
    return results


def retrieve_one_ballot_from_google_civic_api(text_for_map_search, google_civic_election_id=0):
    # Request json file from Google servers
    logger.info("Loading ballot for one address from voterInfoQuery from Google servers")
    request = requests.get(VOTER_INFO_URL, params={
        "key": GOOGLE_CIVIC_API_KEY,
        "address": text_for_map_search,
        "electionId": google_civic_election_id,
    })
    structured_json = json.loads(request.text)

    # # For internal testing. Write the json retrieved above into a local file
    # with open('/Users/dalemcgrew/PythonProjects/WeVoteServer/'
    #           'import_export_google_civic/import_data/voterInfoQuery_VA_sample.json', 'w') as f:
    #     json.dump(structured_json, f)
    #     f.closed
    #
    # # TEMP - FROM FILE (so we aren't hitting Google Civic API during development)
    # with open("import_export_google_civic/import_data/voterInfoQuery_VA_sample.json") as json_data:
    #     structured_json = json.load(json_data)

    # Use Google Civic API call counter to track the number of queries we are doing each day
    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_api_counter_manager.create_counter_entry('ballot', google_civic_election_id)

    # Verify that we got a ballot. (If you use an address in California for an election in New York,
    #  you won't get a ballot for example.)
    success = False
    if 'contests' in structured_json:
        if len(structured_json['contests']) > 0:
            success = True

    results = {
        'success': success,
        'structured_json': structured_json,
    }
    return results


# See import_data/voterInfoQuery_VA_sample.json
def store_one_ballot_from_google_civic_api(one_ballot_json, voter_id=0):

    #     "election": {
    #     "electionDay": "2015-11-03",
    #     "id": "4162",
    #     "name": "Virginia General Election",
    #     "ocdDivisionId": "ocd-division/country:us/state:va"
    # },
    if 'election' not in one_ballot_json:
        results = {
            'status': 'BALLOT_JSON_MISSING_ELECTION',
            'success': False,
            'google_civic_election_id': 0,
        }
        return results

    if 'id' not in one_ballot_json['election']:
        results = {
            'status': 'BALLOT_JSON_MISSING_ELECTION_ID',
            'success': False,
            'google_civic_election_id': 0,
        }
        return results

    if positive_value_exists(voter_id):
        voter_address_dict = one_ballot_json['normalizedInput'] if 'normalizedInput' in one_ballot_json else {}
        if positive_value_exists(voter_address_dict):
            # When saving a ballot for an individual voter, use this data to update voter address with the
            #  normalized address information returned from Google Civic
            # "normalizedInput": {
            #   "line1": "254 hartford st",
            #   "city": "san francisco",
            #   "state": "CA",
            #   "zip": "94114"
            #  },
            voter_address_manager = VoterAddressManager()
            voter_address_manager.update_voter_address_with_normalized_values(
                voter_id, voter_address_dict)
            # Note that neither 'success' nor 'status' are set here because updating the voter_address with normalized
            # values isn't critical to the success of storing the ballot for a voter

    google_civic_election_id = one_ballot_json['election']['id']
    ocd_division_id = one_ballot_json['election']['ocdDivisionId']
    state_code = extract_state_from_ocd_division_id(ocd_division_id)
    if not positive_value_exists(state_code):
        # We have a backup method of looking up state from one_ballot_json['state']['name']
        # in case the ocd state fails
        if 'state' in one_ballot_json:
            if 'name' in one_ballot_json['state']:
                state_code = one_ballot_json['state']['name']

    # Loop through all contests and store in local db cache
    results = process_contests_from_structured_json(one_ballot_json['contests'], google_civic_election_id,
                                                    ocd_division_id, state_code, voter_id)

    status = results['status']

    # When saving a ballot for individual voter, loop through all pollingLocations and store in local db
    # process_polling_locations_from_structured_json(one_ballot_json['pollingLocations'])

    results = {
        'status': status,
        'success': results['success'],
        'google_civic_election_id': google_civic_election_id,
    }
    return results


# See import_data/election_query_sample.json
def retrieve_from_google_civic_api_election_query():
    # Request json file from Google servers
    logger.info("Loading json data from Google servers, API call electionQuery")
    request = requests.get(ELECTION_QUERY_URL, params={
        "key": GOOGLE_CIVIC_API_KEY,  # This comes from an environment variable
    })
    # Use Google Civic API call counter to track the number of queries we are doing each day
    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_api_counter_manager.create_counter_entry('election')
    return json.loads(request.text)


def store_results_from_google_civic_api_election_query(structured_json):
    elections_list_json = structured_json['elections']
    results = {}
    for one_election in elections_list_json:
        raw_ocd_division_id = one_election['ocdDivisionId']
        election_date_text = one_election['electionDay']
        google_civic_election_id = one_election['id']
        election_name = one_election['name']

        election_manager = ElectionManager()
        results = election_manager.update_or_create_election(
            google_civic_election_id, election_name, election_date_text, raw_ocd_division_id)

    return results


def retrieve_and_store_ballot_for_voter(voter_id, text_for_map_search=''):
    google_civic_election_id = 0
    if not positive_value_exists(text_for_map_search):
        # Retrieve it from voter address
        voter_address_manager = VoterAddressManager()
        text_for_map_search = voter_address_manager.retrieve_ballot_map_text_from_voter_id(voter_id)

    if positive_value_exists(text_for_map_search):
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(text_for_map_search)
        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']

            # Wipe out ballot_items stored previously
            ballot_item_list_manager = BallotItemListManager()
            # We do not include a google_civic_election_id, so all prior ballots are removed
            google_civic_election_id_to_delete = 0  # This means "delete all"
            ballot_item_list_manager.delete_all_ballot_items_for_voter(voter_id, google_civic_election_id_to_delete)

            # We update VoterAddress with normalized address data in store_one_ballot_from_google_civic_api

            store_one_ballot_results = store_one_ballot_from_google_civic_api(one_ballot_json, voter_id)
            if store_one_ballot_results['success']:
                status = 'RETRIEVED_AND_STORED_BALLOT_FOR_VOTER'
                success = True
                google_civic_election_id = store_one_ballot_results['google_civic_election_id']
            else:
                status = 'UNABLE_TO-store_one_ballot_from_google_civic_api'
                success = False
        elif 'error' in one_ballot_results['structured_json']:
            if one_ballot_results['structured_json']['error']['message'] == 'Election unknown':
                success = True
            else:
                success = False
            status = one_ballot_results['structured_json']['error']['message']

        else:
            status = 'UNABLE_TO-retrieve_one_ballot_from_google_civic_api'
            success = False
    else:
        status = 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH'
        success = False

    results = {
        'google_civic_election_id': google_civic_election_id,
        'success': success,
        'status': status,
    }
    return results


# We will want to do this in the future
# def process_polling_locations_from_structured_json(polling_location_structured_data):
#     """
#     "pollingLocations": [
#       {
#        "address": {
#         "locationName": "School-Harvey Milk",
#         "line1": "4235 19th Street",
#         "city": "San Francisco",
#         "state": "CA",
#         "zip": "94114-2415"
#        },
#        "notes": "Between Collingwood & Diamond",
#        "pollingHours": "07:00-20:00",
#     """
#     return


def process_contest_referendum_from_structured_json(
        one_contest_referendum_structured_json, google_civic_election_id, ocd_division_id, local_ballot_order,
        state_code, voter_id):
    """
    "referendumTitle": "Proposition 45",
    "referendumSubtitle": "Healthcare Insurance. Rate Changes. Initiative Statute.",
    "referendumUrl": "http://vig.cdn.sos.ca.gov/2014/general/en/pdf/proposition-45-title-summary-analysis.pdf",
    "district" <= this is an array
    """
    referendum_title = one_contest_referendum_structured_json['referendumTitle']
    referendum_subtitle = one_contest_referendum_structured_json['referendumSubtitle'] if \
        'referendumSubtitle' in one_contest_referendum_structured_json else ''
    referendum_url = one_contest_referendum_structured_json['referendumUrl'] if \
        'referendumUrl' in one_contest_referendum_structured_json else ''
    referendum_text = one_contest_referendum_structured_json['referendumText'] if \
        'referendumText' in one_contest_referendum_structured_json else ''

    # These following fields exist for both candidates and referendum
    results = process_contest_common_fields_from_structured_json(one_contest_referendum_structured_json)
    google_ballot_placement = results['ballot_placement']  # A number specifying the position of this contest
    # on the voter's ballot.
    primary_party = results['primary_party']  # If this is a partisan election, the name of the party it is for.
    district_name = results['district_name']  # The name of the district.
    district_scope = results['district_scope']   # The geographic scope of this district. If unspecified the
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    district_id = results['district_id']

    # Note that all of the information saved here is independent of a particular voter
    we_vote_id = ''
    if google_civic_election_id and (district_id or district_name) and referendum_title:
        update_contest_measure_values = {
            # Values we search against
            'google_civic_election_id': google_civic_election_id,
            'state_code': state_code.lower(),  # Not required for cases of federal offices
            'district_id': district_id,
            'district_name': district_name,
            'measure_title': referendum_title,
            # The rest of the values
            'measure_subtitle': referendum_subtitle,
            'measure_url': referendum_url,
            'measure_text': referendum_text,
            'ocd_division_id': ocd_division_id,
            'primary_party': primary_party,
            'district_scope': district_scope,
        }
        # create_contest_measure_values = {
        #     # Values we search against
        #     'google_civic_election_id': google_civic_election_id,
        #     'state_code': state_code.lower(),  # Not required for cases of federal offices
        #     'district_id': district_id,
        #     'district_name': district_name,
        #     'measure_title': referendum_title,
        #     # The rest of the values
        #     'measure_subtitle': referendum_subtitle,
        #     'measure_url': referendum_url,
        #     'measure_text': referendum_text,
        #     'ocd_division_id': ocd_division_id,
        #     'primary_party': primary_party,
        #     'district_scope': district_scope,
        #     # 'electorate_specifications': electorate_specifications,
        #     # 'special': special,
        # }
        contest_measure_manager = ContestMeasureManager()
        update_or_create_contest_measure_results = contest_measure_manager.update_or_create_contest_measure(
            we_vote_id, google_civic_election_id, district_id, district_name, referendum_title, state_code,
            update_contest_measure_values)  # , create_contest_measure_values
    else:
        update_or_create_contest_measure_results = {
            'success': False,
            'saved': 0,
            'updated': 0,
            'not_processed': 1,
        }

    if update_or_create_contest_measure_results['success']:
        contest_measure = update_or_create_contest_measure_results['contest_measure']
        contest_measure_id = contest_measure.id
        contest_measure_we_vote_id = contest_measure.we_vote_id
        ballot_item_label = contest_measure.measure_title

        # If a voter_id was passed in, save an entry for this office for the voter's ballot
        if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(contest_measure_id):
            ballot_item_manager = BallotItemManager()
            contest_office_id = 0
            contest_office_we_vote_id = ''
            ballot_item_manager.update_or_create_ballot_item_for_voter(
                voter_id, google_civic_election_id, google_ballot_placement, ballot_item_label, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id)

    return update_or_create_contest_measure_results


# GoogleDivisions  # Represents a political geographic division that matches the requested query.
# Dale commentary, 2015-04-30 This information becomes useful when we are tying
# voter address -> precincts -> jurisdictions
# With Cicero or Google Civic we can go from voter address -> jurisdictions
# https://developers.google.com/civic-information/docs/v2/divisions
# "ocdId": string,  # The unique Open Civic Data identifier for this division.
#   "name": string,  # The name of the division.
#   "aliases": [
#     string
#   ]

# Looks up representative information for a single geographic division.
# https://developers.google.com/civic-information/docs/v2/representatives/representativeInfoByDivision
