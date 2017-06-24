# import_export_google_civic/controllers.py
# Brought to you by We Vote. Be good.
# Complete description of all Google Civic fields:
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/index.html
# voterInfoQuery Details:
# https://developers.google.com/
#   resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html#voterInfoQuery

# -*- coding: UTF-8 -*-

from .models import GoogleCivicApiCounterManager
from ballot.models import BallotItemManager, BallotItemListManager, BallotReturned, BallotReturnedManager, \
    VoterBallotSavedManager
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from election.models import ElectionManager
import json
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from polling_location.models import PollingLocationManager
import requests
from voter.models import fetch_voter_id_from_voter_device_link, VoterAddressManager
from wevote_functions.functions import convert_state_text_to_state_code, convert_to_int, \
    extract_state_from_ocd_division_id, is_voter_device_id_valid, logger, positive_value_exists

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
        # For some reason Google Civic API violates the JSON standard and uses a / in front of '
        candidate_name = candidate_name.replace("/'", "'")
        # We want to save the name exactly as it comes from the Google Civic API
        google_civic_candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        party = one_candidate['party'] if 'party' in one_candidate else ''
        order_on_ballot = one_candidate['orderOnBallot'] if 'orderOnBallot' in one_candidate else 0
        candidate_url = one_candidate['candidateUrl'] if 'candidateUrl' in one_candidate else ''
        photo_url = one_candidate['photoUrl'] if 'photoUrl' in one_candidate else ''
        email = one_candidate['email'] if 'email' in one_candidate else ''
        phone = one_candidate['phone'] if 'phone' in one_candidate else ''

        # Make sure we start with empty channel values
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

        # DALE 2016-02-20 It would be helpful to call a service here that disambiguated the candidate
        # ...and linked to a politician
        # ...and looked to see if there were any other candidate_campaign entries for this election (in case the
        #   Google Civic contest_office name changed so we generated another contest)

        we_vote_id = ''
        # Make sure we have the minimum variables required to uniquely identify a candidate
        if google_civic_election_id and contest_office_id and candidate_name:
            # NOT using " and ocd_division_id"

            # Make sure there isn't an alternate entry for this election and contest_office (under a similar but
            # slightly different name TODO
            # Note: This doesn't deal with duplicate Presidential candidates. These duplicates are caused because
            # candidates are tied to a particular google_civic_election_id, so there is a different candidate entry
            # for each Presidential candidate for each state.

            updated_candidate_campaign_values = {
                # Values we search against
                'google_civic_election_id': google_civic_election_id,
            }
            if positive_value_exists(ocd_division_id):
                updated_candidate_campaign_values["ocd_division_id"] = ocd_division_id
            if positive_value_exists(candidate_name):
                # Note: When we decide to start updating candidate_name elsewhere within We Vote, we should stop
                #  updating candidate_name via subsequent Google Civic imports
                updated_candidate_campaign_values["candidate_name"] = candidate_name
                # We store the literal spelling here so we can match in the future, even if we customize candidate_name
                updated_candidate_campaign_values["google_civic_candidate_name"] = candidate_name
            if positive_value_exists(state_code):
                updated_candidate_campaign_values["state_code"] = state_code.lower()
            if positive_value_exists(party):
                updated_candidate_campaign_values["party"] = party
            if positive_value_exists(email):
                updated_candidate_campaign_values["candidate_email"] = email
            if positive_value_exists(phone):
                updated_candidate_campaign_values["candidate_phone"] = phone
            if positive_value_exists(order_on_ballot):
                updated_candidate_campaign_values["order_on_ballot"] = order_on_ballot
            if positive_value_exists(candidate_url):
                updated_candidate_campaign_values["candidate_url"] = candidate_url
            if positive_value_exists(photo_url):
                updated_candidate_campaign_values["photo_url"] = photo_url
            if positive_value_exists(facebook_url):
                updated_candidate_campaign_values["facebook_url"] = facebook_url
            if positive_value_exists(twitter_url):
                updated_candidate_campaign_values["twitter_url"] = twitter_url
            if positive_value_exists(google_plus_url):
                updated_candidate_campaign_values["google_plus_url"] = google_plus_url
            if positive_value_exists(youtube_url):
                updated_candidate_campaign_values["youtube_url"] = youtube_url
            # 2016-02-20 Google Civic sometimes changes the name of contests, which can create a new contest
            #  so we may need to update the candidate to a new contest_office_id
            if positive_value_exists(contest_office_id):
                updated_candidate_campaign_values["contest_office_id"] = contest_office_id
            if positive_value_exists(contest_office_we_vote_id):
                updated_candidate_campaign_values["contest_office_we_vote_id"] = contest_office_we_vote_id

            candidate_campaign_manager = CandidateCampaignManager()
            results = candidate_campaign_manager.update_or_create_candidate_campaign(
                we_vote_id, google_civic_election_id,
                ocd_division_id, contest_office_id, contest_office_we_vote_id,
                google_civic_candidate_name, updated_candidate_campaign_values)

    return results


def process_contest_office_from_structured_json(
        one_contest_office_structured_json, google_civic_election_id, state_code, ocd_division_id, local_ballot_order,
        voter_id, polling_location_we_vote_id):
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
    maplight_id = 0
    # Note that all of the information saved here is independent of a particular voter
    if google_civic_election_id and (district_id or district_name) and office_name:
        updated_contest_office_values = {
            'google_civic_election_id': google_civic_election_id,
        }
        if positive_value_exists(state_code):
            updated_contest_office_values["state_code"] = state_code.lower()
        if positive_value_exists(district_id):
            updated_contest_office_values["district_id"] = district_id
        if positive_value_exists(district_name):
            updated_contest_office_values["district_name"] = district_name
        if positive_value_exists(office_name):
            # Note: When we decide to start updating office_name elsewhere within We Vote, we should stop
            #  updating office_name via subsequent Google Civic imports
            updated_contest_office_values["office_name"] = office_name
            # We store the literal spelling here so we can match in the future, even if we customize measure_title
            updated_contest_office_values["google_civic_office_name"] = office_name
        if positive_value_exists(ocd_division_id):
            updated_contest_office_values["ocd_division_id"] = ocd_division_id
        if positive_value_exists(number_voting_for):
            updated_contest_office_values["number_voting_for"] = number_voting_for
        if positive_value_exists(number_elected):
            updated_contest_office_values["number_elected"] = number_elected
        if positive_value_exists(contest_level0):
            updated_contest_office_values["contest_level0"] = contest_level0
        if positive_value_exists(contest_level1):
            updated_contest_office_values["contest_level1"] = contest_level1
        if positive_value_exists(contest_level2):
            updated_contest_office_values["contest_level2"] = contest_level2
        if positive_value_exists(primary_party):
            updated_contest_office_values["primary_party"] = primary_party
        if positive_value_exists(district_scope):
            updated_contest_office_values["district_scope"] = district_scope
        if positive_value_exists(electorate_specifications):
            updated_contest_office_values["electorate_specifications"] = electorate_specifications
        if positive_value_exists(special):
            updated_contest_office_values["special"] = special
        contest_office_manager = ContestOfficeManager()
        # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
        # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
        # Presidential races don't have either district_id or district_name, so we can't require one.
        # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower" vs. "scope": "statewide"
        update_or_create_contest_office_results = contest_office_manager.update_or_create_contest_office(
            we_vote_id, maplight_id, google_civic_election_id, office_name, district_id,
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
        ballot_item_display_name = contest_office.office_name
    else:
        contest_office_id = 0
        contest_office_we_vote_id = ''
        ballot_item_display_name = ''

    # If a voter_id was passed in, save an entry for this office for the voter's ballot
    if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) \
            and positive_value_exists(contest_office_id):
        ballot_item_manager = BallotItemManager()
        measure_subtitle = ""
        ballot_item_manager.update_or_create_ballot_item_for_voter(
            voter_id, google_civic_election_id, google_ballot_placement, ballot_item_display_name,
            measure_subtitle, local_ballot_order, contest_office_id, contest_office_we_vote_id, state_code)
        # We leave off these and rely on default empty values: contest_measure_id, contest_measure_we_vote_id

    # If this is a polling location, we want to save the ballot information for it so we can use it as reference
    #  for nearby voters (when we don't have their full address)
    if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id) \
            and positive_value_exists(contest_office_id):
        ballot_item_manager = BallotItemManager()
        measure_subtitle = ""
        ballot_item_manager.update_or_create_ballot_item_for_polling_location(
            polling_location_we_vote_id, google_civic_election_id, google_ballot_placement, ballot_item_display_name,
            measure_subtitle, local_ballot_order, contest_office_id, contest_office_we_vote_id, state_code)
        # We leave off these and rely on default empty values: contest_measure_id, contest_measure_we_vote_id

    # Note: We do not need to connect the candidates with the voter here for a ballot item  # TODO DALE Actually we do
    # For VT, They don't have a district id, so all candidates were lumped together.
    # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
    # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
    # Presidential races don't have either district_id or district_name, so we can't require one.
    # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower" vs. "scope": "statewide"
    candidates_results = process_candidates_from_structured_json(
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

    # ballot_placement is a number specifying the position of this contest on the voter's ballot.
    # primary_party: If this is a partisan election, the name of the party it is for.
    results = {'ballot_placement': extract_value_from_array(one_contest_structured_json, 'ballotPlacement', 0),
               'primary_party': extract_value_from_array(one_contest_structured_json, 'primaryParty', '')}

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
        contests_structured_json, google_civic_election_id, ocd_division_id, state_code, voter_id,
        polling_location_we_vote_id):
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
        if contest_type.lower() == 'referendum':  # Referendum
            process_contest_results = process_contest_referendum_from_structured_json(
                one_contest, google_civic_election_id, ocd_division_id, local_ballot_order, state_code, voter_id,
                polling_location_we_vote_id)
            if process_contest_results['saved']:
                contests_saved += 1
            elif process_contest_results['updated']:
                contests_updated += 1
            elif process_contest_results['not_processed']:
                contests_not_processed += 1
        # All other contests are for an elected office
        else:
            process_contest_results = process_contest_office_from_structured_json(
                one_contest, google_civic_election_id, ocd_division_id, local_ballot_order, state_code, voter_id,
                polling_location_we_vote_id)
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


def retrieve_one_ballot_from_google_civic_api(text_for_map_search, incoming_google_civic_election_id=0,
                                              use_test_election=False):
    # Request json file from Google servers
    # logger.info("Loading ballot for one address from voterInfoQuery from Google servers")
    print("retrieving one ballot for " + str(incoming_google_civic_election_id))
    if positive_value_exists(use_test_election):
        response = requests.get(VOTER_INFO_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,
            "address": text_for_map_search,
            "electionId": 2000,  # The Google Civic API Test election
        })
    elif positive_value_exists(incoming_google_civic_election_id):
        response = requests.get(VOTER_INFO_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,
            "address": text_for_map_search,
            "electionId": incoming_google_civic_election_id,
        })
    else:
        response = requests.get(VOTER_INFO_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,
            "address": text_for_map_search,
        })

    structured_json = json.loads(response.text)
    if 'success' in structured_json and structured_json['success'] == False:
        import_results = {
            'success': False,
            'status': "Error: " + structured_json['status'],
        }
        return import_results

    # # For internal testing. Write the json retrieved above into a local file
    # with open('/Users/dalemcgrew/PythonProjects/WeVoteServer/'
    #           'import_export_google_civic/import_data/voterInfoQuery_VA_sample.json', 'w') as f:
    #     json.dump(structured_json, f)
    #     f.closed
    #
    # # TEMP - FROM FILE (so we aren't hitting Google Civic API during development)
    # with open("import_export_google_civic/import_data/voterInfoQuery_VA_sample.json") as json_data:
    #     structured_json = json.load(json_data)

    # Verify that we got a ballot. (If you use an address in California for an election in New York,
    #  you won't get a ballot for example.)
    success = False
    election_data_retrieved = False
    polling_location_retrieved = False
    contests_retrieved = False
    google_civic_election_id = 0
    error = structured_json.get('error', {})
    errors = error.get('errors', {})
    if len(errors):
        logger.error("retrieve_one_ballot_from_google_civic_api failed: " + json.dumps(errors), {}, {})

    if 'election' in structured_json:
        if 'id' in structured_json['election']:
            election_data_retrieved = True
            success = True
            google_civic_election_id = structured_json['election']['id']

    # TODO DALE We can get a google_civic_election_id back even though we don't have contest data.
    #  If we get a google_civic_election_id back but no contest data, reach out again with the google_civic_election_id
    #  so we can then get contest data

    # Use Google Civic API call counter to track the number of queries we are doing each day
    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_api_counter_manager.create_counter_entry('ballot', google_civic_election_id)

    if 'pollingLocations' in structured_json:
        polling_location_retrieved = True
        success = True

    if 'contests' in structured_json:
        if len(structured_json['contests']) > 0:
            contests_retrieved = True
            success = True

    results = {
        'success': success,
        'election_data_retrieved': election_data_retrieved,
        'polling_location_retrieved': polling_location_retrieved,
        'contests_retrieved': contests_retrieved,
        'structured_json': structured_json,
    }
    return results


# See import_data/voterInfoQuery_VA_sample.json
def store_one_ballot_from_google_civic_api(one_ballot_json, voter_id=0, polling_location_we_vote_id=''):
    """
    When we pass in a voter_id, we want to save this ballot related to the voter.
    When we pass in polling_location_we_vote_id, we want to save a ballot for that area, which is useful for
    getting new voters started by showing them a ballot roughly near them.
    """
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

    election_date_text = ''
    election_description_text = ''
    if 'electionDay' in one_ballot_json['election']:
        election_date_text = one_ballot_json['election']['electionDay']
    if 'name' in one_ballot_json['election']:
        election_description_text = one_ballot_json['election']['name']

    if 'id' not in one_ballot_json['election']:
        results = {
            'status': 'BALLOT_JSON_MISSING_ELECTION_ID',
            'success': False,
            'google_civic_election_id': 0,
        }
        return results

    voter_address_dict = one_ballot_json['normalizedInput'] if 'normalizedInput' in one_ballot_json else {}
    if positive_value_exists(voter_id):
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
    # We don't store the normalized address information when we capture a ballot for a polling location

    google_civic_election_id = one_ballot_json['election']['id']
    ocd_division_id = one_ballot_json['election']['ocdDivisionId']
    state_code = extract_state_from_ocd_division_id(ocd_division_id)
    if not positive_value_exists(state_code):
        # We have a backup method of looking up state from one_ballot_json['state']['name']
        # in case the ocd state fails
        state_name = ''
        if 'state' in one_ballot_json:
            if 'name' in one_ballot_json['state']:
                state_name = one_ballot_json['state']['name']
            elif len(one_ballot_json['state']) > 0:
                # In some cases, like test elections 2000 a list is returned in one_ballot_json['state']
                for one_state_entry in one_ballot_json['state']:
                    if 'name' in one_state_entry:
                        state_name = one_state_entry['name']
        state_code = convert_state_text_to_state_code(state_name)
    if not positive_value_exists(state_code):
        if 'normalizedInput' in one_ballot_json:
            state_code = one_ballot_json['normalizedInput']['state']

    # Loop through all contests and store in local db cache
    if 'contests' in one_ballot_json:
        results = process_contests_from_structured_json(one_ballot_json['contests'], google_civic_election_id,
                                                        ocd_division_id, state_code, voter_id,
                                                        polling_location_we_vote_id)

        status = results['status']
        success = results['success']
    else:
        status = "STORE_ONE_BALLOT_NO_CONTESTS_FOUND"
        success = False

    # When saving a ballot for individual voter, loop through all pollingLocations and store in local db
    # process_polling_locations_from_structured_json(one_ballot_json['pollingLocations'])

    # If we successfully save a ballot, create/update a BallotReturned entry
    ballot_returned_found = False
    ballot_returned = BallotReturned()
    is_test_election = True if positive_value_exists(google_civic_election_id) \
        and convert_to_int(google_civic_election_id) == 2000 else False

    # Make sure we have this polling_location
    polling_location_manager = PollingLocationManager()
    results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
    polling_location_latitude = None
    polling_location_longitude = None
    if results['polling_location_found']:
        polling_location = results['polling_location']
        polling_location_latitude = polling_location.latitude
        polling_location_longitude = polling_location.longitude

    if success and positive_value_exists(voter_address_dict) and not is_test_election:
        ballot_returned_manager = BallotReturnedManager()
        if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
            results = ballot_returned_manager.retrieve_ballot_returned_from_voter_id(voter_id, google_civic_election_id)
            if results['ballot_returned_found']:
                update_results = ballot_returned_manager.update_ballot_returned_with_normalized_values(
                    voter_address_dict, state_code, results['ballot_returned'],
                    polling_location_latitude, polling_location_longitude)
                ballot_returned_found = True  # If the update fails, we just return the original ballot_returned object
                ballot_returned = update_results['ballot_returned']
            else:
                create_results = ballot_returned_manager.create_ballot_returned_with_normalized_values(
                    voter_address_dict,
                    election_date_text, election_description_text,
                    google_civic_election_id, state_code, voter_id, '')
                ballot_returned_found = create_results['ballot_returned_found']
                ballot_returned = create_results['ballot_returned']
        if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
            results = ballot_returned_manager.retrieve_ballot_returned_from_polling_location_we_vote_id(
                polling_location_we_vote_id, google_civic_election_id)
            if results['ballot_returned_found']:
                update_results = ballot_returned_manager.update_ballot_returned_with_normalized_values(
                    voter_address_dict, state_code, results['ballot_returned'],
                    polling_location_latitude, polling_location_longitude)
                ballot_returned_found = True  # If the update fails, we just return the original ballot_returned object
                ballot_returned = update_results['ballot_returned']
            else:
                create_results = ballot_returned_manager.create_ballot_returned_with_normalized_values(
                    voter_address_dict,
                    election_date_text, election_description_text,
                    google_civic_election_id, state_code, 0, polling_location_we_vote_id,
                    polling_location_latitude, polling_location_longitude)
                ballot_returned_found = create_results['ballot_returned_found']
                ballot_returned = create_results['ballot_returned']
        # Currently we don't report the success or failure of storing ballot_returned

    results = {
        'status':                   status,
        'success':                  success,
        'ballot_returned_found':    ballot_returned_found,
        'ballot_returned':          ballot_returned,
        'google_civic_election_id': google_civic_election_id,
    }
    return results


# See import_data/election_query_sample.json
def retrieve_from_google_civic_api_election_query():
    # Request json file from Google servers
    logger.info("Loading json data from Google servers, API call electionQuery")
    print("Loading json data from Google servers, API call electionQuery")

    if not positive_value_exists(ELECTION_QUERY_URL):
        results = {
            'success':  False,
            'status':   'ELECTION_QUERY_URL missing from config/environment_variables.json',
        }
        return results

    response = requests.get(ELECTION_QUERY_URL, params={
        "key": GOOGLE_CIVIC_API_KEY,  # This comes from an environment variable
    })

    # Use Google Civic API call counter to track the number of queries we are doing each day
    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_api_counter_manager.create_counter_entry('election')

    structured_json = json.loads(response.text)
    if 'success' in structured_json and structured_json['success'] == False:
        results = {
            'success': False,
            'status': "Error: " + structured_json['status'],
        }
    else:
        results = {
            'structured_json':  structured_json,
            'success':          True,
            'status':           'structured_json retrieved',
        }
    return results


def store_results_from_google_civic_api_election_query(structured_json):
    if 'elections' in structured_json:
        elections_list_json = structured_json['elections']
    else:
        elections_list_json = {}
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


def voter_ballot_items_retrieve_from_google_civic_for_api(
        voter_device_id, text_for_map_search='', use_test_election=False):
    """
    We are telling the server to explicitly reach out to the Google Civic API and retrieve the ballot items
    for this voter.
    """
    # Confirm that we have a Google Civic API Key (GOOGLE_CIVIC_API_KEY)
    if not positive_value_exists(GOOGLE_CIVIC_API_KEY):
        results = {
            'status': 'NO_GOOGLE_CIVIC_API_KEY ',
            'success': False,
            'voter_device_id': voter_device_id,
            'google_civic_election_id': 0,
            'text_for_map_search': text_for_map_search,
        }
        return results

    # Confirm that we have the URL where we retrieve voter ballots (VOTER_INFO_URL)
    if not positive_value_exists(VOTER_INFO_URL):
        results = {
            'status': 'MISSING VOTER_INFO_URL in config/environment_variables.json ',
            'success': False,
            'voter_device_id': voter_device_id,
            'google_civic_election_id': 0,
            'text_for_map_search': text_for_map_search,
        }
        return results

    # Get voter_id from the voter_device_id so we can figure out which ballot_items to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING ',
            'success': False,
            'voter_device_id': voter_device_id,
            'google_civic_election_id': 0,
            'text_for_map_search': text_for_map_search,
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        results = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
            'voter_device_id': voter_device_id,
            'google_civic_election_id': 0,
            'text_for_map_search': text_for_map_search,
        }
        return results

    google_civic_election_id = 0  # = 5000  # TODO DALE TESTING A PROBLEM - when we remove this, update
    #  retrieve_one_ballot_from_google_civic_api to go back for a second look once we have google_civic_election_id
    status = ''
    success = False
    election_date_text = ''
    election_description_text = ''
    election_data_retrieved = False
    polling_location_retrieved = False
    contests_retrieved = False
    if not positive_value_exists(text_for_map_search):
        # Retrieve it from voter address
        voter_address_manager = VoterAddressManager()
        text_for_map_search = voter_address_manager.retrieve_ballot_map_text_from_voter_id(voter_id)

    # We want to remove all prior ballot items, so we make room for store_one_ballot_from_google_civic_api to save
    #  ballot items
    # 6/12/17: google_civic_election_id will always be 0 at this point, so next 8 lines are never executed
    if positive_value_exists(google_civic_election_id):
        voter_ballot_saved_manager = VoterBallotSavedManager()
        voter_ballot_saved_results = voter_ballot_saved_manager.delete_voter_ballot_saved(
            0, voter_id, google_civic_election_id)

        ballot_item_list_manager = BallotItemListManager()
        # We include a google_civic_election_id, so only the ballot info for this election is removed
        ballot_item_list_manager.delete_all_ballot_items_for_voter(voter_id, google_civic_election_id)

    if positive_value_exists(text_for_map_search):
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(
            text_for_map_search, google_civic_election_id, use_test_election)

        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']
            election_date_text = one_ballot_json['election']['electionDay']
            election_description_text = one_ballot_json['election']['name']

            # We may receive some election data, but not all of the data we need
            if one_ballot_results['election_data_retrieved']:
                election_data_retrieved = True
                success = True

            if one_ballot_results['polling_location_retrieved']:
                polling_location_retrieved = True
                success = True

            # Contests usually will be 'General', 'Primary', or 'Run-off' for contests with candidates.
            if one_ballot_results['contests_retrieved']:
                contests_retrieved = True

                # Now that we know we have new ballot data, we need to delete prior ballot data for this election
                # because when we change voterAddress, we usually get different ballot items
                ballot_item_list_manager = BallotItemListManager()
                # We include a google_civic_election_id, so only the ballot info for this election is removed
                google_civic_election_id_to_delete = one_ballot_json['election']['id']  # '0' would mean "delete all"
                if positive_value_exists(google_civic_election_id_to_delete) and positive_value_exists(voter_id):
                    ballot_item_list_manager.delete_all_ballot_items_for_voter(
                        voter_id, google_civic_election_id_to_delete)

                # store_on_ballot... adds an entry to the BallotReturned table
                # We update VoterAddress with normalized address data in store_one_ballot_from_google_civic_api
                store_one_ballot_results = store_one_ballot_from_google_civic_api(one_ballot_json, voter_id)
                if store_one_ballot_results['success']:
                    status += 'RETRIEVED_FROM_GOOGLE_CIVIC_AND_STORED_BALLOT_FOR_VOTER '
                    success = True
                    google_civic_election_id = store_one_ballot_results['google_civic_election_id']
                else:
                    status += 'UNABLE_TO-store_one_ballot_from_google_civic_api '
        elif 'error' in one_ballot_results['structured_json']:
            if one_ballot_results['structured_json']['error']['message'] == 'Election unknown':
                success = False  # It is only successful if new ballot data is retrieved.
            else:
                success = False
            status += "GOOGLE_CIVIC_API_ERROR: " + one_ballot_results['structured_json']['error']['message']

        else:
            status += 'UNABLE_TO-retrieve_one_ballot_from_google_civic_api'
            success = False
    else:
        status += 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH'
        success = False

    # If a google_civic_election_id was not returned, outside of this function we search again using a test election,
    # so that during our initial user testing, ballot data is returned in areas where elections don't currently exist

    results = {
        'success': success,
        'status': status,
        'voter_device_id': voter_device_id,
        'google_civic_election_id': google_civic_election_id,
        'text_for_map_search': text_for_map_search,
        'election_date_text': election_date_text,
        'election_description_text': election_description_text,
        'election_data_retrieved': election_data_retrieved,
        'polling_location_retrieved': polling_location_retrieved,
        'contests_retrieved': contests_retrieved,
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
        state_code, voter_id, polling_location_we_vote_id):
    """
    "referendumTitle": "Proposition 45",
    "referendumSubtitle": "Healthcare Insurance. Rate Changes. Initiative Statute.",
    "referendumUrl": "http://vig.cdn.sos.ca.gov/2014/general/en/pdf/proposition-45-title-summary-analysis.pdf",
    "district" <= this is an array
    """
    referendum_title = one_contest_referendum_structured_json['referendumTitle'] if \
        'referendumTitle' in one_contest_referendum_structured_json else ''
    referendum_subtitle = one_contest_referendum_structured_json['referendumSubtitle'] if \
        'referendumSubtitle' in one_contest_referendum_structured_json else ''
    if not positive_value_exists(referendum_subtitle):
        referendum_subtitle = one_contest_referendum_structured_json['referendumBrief'] if \
            'referendumBrief' in one_contest_referendum_structured_json else ''
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
        # We want to only add values, and never clear out existing values that may have been
        # entered independently
        updated_contest_measure_values = {
            'google_civic_election_id': google_civic_election_id,
        }
        if positive_value_exists(state_code):
            updated_contest_measure_values["state_code"] = state_code.lower()
        if positive_value_exists(district_id):
            updated_contest_measure_values["district_id"] = district_id
        if positive_value_exists(district_name):
            updated_contest_measure_values["district_name"] = district_name
        if positive_value_exists(referendum_title):
            updated_contest_measure_values["measure_title"] = referendum_title
            # We store the literal spelling here so we can match in the future, even if we customize measure_title
            updated_contest_measure_values["google_civic_measure_title"] = referendum_title
        if positive_value_exists(referendum_subtitle):
            updated_contest_measure_values["measure_subtitle"] = referendum_subtitle
        if positive_value_exists(referendum_url):
            updated_contest_measure_values["measure_url"] = referendum_url
        if positive_value_exists(referendum_text):
            updated_contest_measure_values["measure_text"] = referendum_text
        if positive_value_exists(ocd_division_id):
            updated_contest_measure_values["ocd_division_id"] = ocd_division_id
        if positive_value_exists(primary_party):
            updated_contest_measure_values["primary_party"] = primary_party
        if positive_value_exists(district_scope):
            updated_contest_measure_values["district_scope"] = district_scope

        contest_measure_manager = ContestMeasureManager()
        update_or_create_contest_measure_results = contest_measure_manager.update_or_create_contest_measure(
            we_vote_id, google_civic_election_id, referendum_title, district_id, district_name, state_code,
            updated_contest_measure_values)
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
        ballot_item_display_name = contest_measure.measure_title
        measure_subtitle = contest_measure.measure_subtitle
        ballot_item_manager = BallotItemManager()

        # If a voter_id was passed in, save an entry for this office for the voter's ballot
        if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(contest_measure_id):
            contest_office_id = 0
            contest_office_we_vote_id = ''
            ballot_item_manager.update_or_create_ballot_item_for_voter(
                voter_id, google_civic_election_id, google_ballot_placement, ballot_item_display_name,
                measure_subtitle, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id, state_code)

        if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(contest_measure_id):
            contest_office_id = 0
            contest_office_we_vote_id = ''
            ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle,
                local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id, state_code)

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
