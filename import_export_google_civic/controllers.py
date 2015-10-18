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
from ballot.models import BallotItemManager
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from election.models import ElectionManager
from exception.models import handle_record_not_found_exception
from measure.models import ContestMeasure
from office.models import ContestOfficeManager
from wevote_functions.models import logger, positive_value_exists

GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
ELECTION_QUERY_URL = get_environment_variable("ELECTION_QUERY_URL")
VOTER_INFO_URL = get_environment_variable("VOTER_INFO_URL")
VOTER_INFO_JSON_FILE = get_environment_variable("VOTER_INFO_JSON_FILE")


# GoogleRepresentatives
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.representatives.html
def process_candidates_from_structured_json(
        candidates_structured_json, google_civic_election_id, ocd_division_id, contest_office_id):
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
        party = one_candidate['party'] if 'party' in one_candidate else ''
        order_on_ballot = one_candidate['orderOnBallot'] if 'orderOnBallot' in one_candidate else 0
        candidate_url = one_candidate['candidateUrl'] if 'candidateUrl' in one_candidate else ''
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

        if google_civic_election_id and ocd_division_id and contest_office_id and candidate_name:
            updated_candidate_campaign_values = {
                # Values we search against
                'google_civic_election_id': google_civic_election_id,
                'ocd_division_id': ocd_division_id,
                'contest_office_id': contest_office_id,
                'candidate_name': candidate_name,
                # The rest of the values
                'party': party,
                'email': email,
                'phone': phone,
                'order_on_ballot': order_on_ballot,
                'candidate_url': candidate_url,
                'facebook_url': facebook_url,
                'twitter_url': twitter_url,
                'google_plus_url': google_plus_url,
                'youtube_url': youtube_url,
                'google_civic_candidate_name': candidate_name,
            }
            candidate_campaign_manager = CandidateCampaignManager()
            results = candidate_campaign_manager.update_or_create_candidate_campaign(
                google_civic_election_id, ocd_division_id, contest_office_id, candidate_name,
                updated_candidate_campaign_values)

    return results


def process_contest_office_from_structured_json(
        one_contest_office_structured_json, google_civic_election_id, ocd_division_id, local_ballot_order, voter_id):
    logger.debug("General contest_type")
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
    roles_structured_json = \
        one_contest_office_structured_json['roles'] if 'roles' in one_contest_office_structured_json else ''
    # for one_role in roles_structured_json:
    # Figure out how we are going to use level info

    candidates_structured_json = \
        one_contest_office_structured_json['candidates'] if 'candidates' in one_contest_office_structured_json else ''

    # Note that all of the information saved here is independent of a particular voter
    if google_civic_election_id and district_id and office_name:
        updated_contest_office_values = {
            # Values we search against
            'google_civic_election_id': google_civic_election_id,
            'district_id': district_id,
            'office_name': office_name,
            # The rest of the values
            'number_voting_for': number_voting_for,
            'number_elected': number_elected,
            'contest_level0': contest_level0,
            'contest_level1': contest_level1,
            'contest_level2': contest_level2,
            'primary_party': primary_party,
            'district_name': district_name,
            'district_scope': district_scope,
            'electorate_specifications': electorate_specifications,
            'special': special,
        }
        contest_office_manager = ContestOfficeManager()
        update_or_create_contest_office_results = contest_office_manager.update_or_create_contest_office(
            google_civic_election_id, district_id, office_name, updated_contest_office_values)
    else:
        update_or_create_contest_office_results = {
            'success': False
        }

    if update_or_create_contest_office_results['success']:
        contest_office = update_or_create_contest_office_results['contest_office']
        contest_office_id = contest_office.id
        ballot_item_label = contest_office.office_name
    else:
        contest_office_id = 0
        ballot_item_label = ''
    contest_measure_id = 0

    # If a voter_id was passed in, save an entry for this office for the voter's ballot
    if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) and positive_value_exists(contest_office_id):
        ballot_item_manager = BallotItemManager()
        ballot_item_manager.update_or_create_ballot_item_for_voter(
            voter_id, google_civic_election_id, google_ballot_placement, ballot_item_label,
            local_ballot_order, contest_measure_id, contest_office_id)

    process_candidates_from_structured_json(
        candidates_structured_json, google_civic_election_id, ocd_division_id, contest_office_id)

    return


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


def process_contests_from_structured_json(contests_structured_json, google_civic_election_id, ocd_division_id, voter_id):
    """
    Take in the portion of the json related to contests, and save to the database
    "type": 'General', "House of Delegates", 'locality', 'Primary', 'Run-off', "State Senate"
    or
    "type": "Referendum",
    """
    local_ballot_order = 0
    for one_contest in contests_structured_json:
        local_ballot_order += 1  # Needed if ballotPlacement isn't provided by Google Civic
        contest_type = one_contest['type']

        # Is the contest is a referendum/initiative/measure?
        if contest_type == 'Referendum':
            process_contest_referendum_from_structured_json(
                one_contest, google_civic_election_id, ocd_division_id, local_ballot_order, voter_id)

        # All other contests are for an elected office
        else:
            process_contest_office_from_structured_json(
                one_contest, google_civic_election_id, ocd_division_id, local_ballot_order, voter_id)


def retrieve_one_ballot_from_google_civic_api(text_for_map_search, google_civic_election_id):
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

    # TODO Add Google Civic API call counter so we can track the number of queries we are doing each day

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
    google_civic_election_id = one_ballot_json['election']['id']
    ocd_division_id = one_ballot_json['election']['ocdDivisionId']

    # Loop through all contests and store in local db cache
    process_contests_from_structured_json(one_ballot_json['contests'], google_civic_election_id,
                                          ocd_division_id, voter_id)

    if voter_id > 0:
        print "TODO Update voter address"
        voter_address = one_ballot_json['normalizedInput'] if 'normalizedInput' in one_ballot_json else {}
        # When saving a ballot for an individual voter, use this data to update voter address
        # "normalizedInput": {
        #   "line1": "254 hartford st",
        #   "city": "san francisco",
        #   "state": "CA",
        #   "zip": "94114"
        #  },

    # When saving a ballot for individual voter, loop through all pollingLocations and store in local db
    # process_polling_locations_from_structured_json(one_ballot_json['pollingLocations'])

    # TODO DALE
    results = {
        'success': True,
    }
    return results


# See import_data/election_query_sample.json
def retrieve_from_google_civic_api_election_query():
    # Request json file from Google servers
    logger.info("Loading json data from Google servers, API call electionQuery")
    request = requests.get(ELECTION_QUERY_URL, params={
        "key": GOOGLE_CIVIC_API_KEY,  # This comes from an environment variable
    })
    # TODO Add Google Civic API call counter so we can track the number of queries we are doing each day
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


###################################################
# OLD BELOW
###################################################


def process_polling_locations_from_structured_json(polling_location_structured_data, save_to_db):
    """
    "pollingLocations": [
      {
       "address": {
        "locationName": "School-Harvey Milk",
        "line1": "4235 19th Street",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94114-2415"
       },
       "notes": "Between Collingwood & Diamond",
       "pollingHours": "07:00-20:00",
    """
    return


def process_contest_referendum_from_structured_json(
        one_contest_referendum_structured_json, google_civic_election_id, ocd_division_id, local_ballot_order, save_to_db):
    """
    "referendumTitle": "Proposition 45",
    "referendumSubtitle": "Healthcare Insurance. Rate Changes. Initiative Statute.",
    "referendumUrl": "http://vig.cdn.sos.ca.gov/2014/general/en/pdf/proposition-45-title-summary-analysis.pdf",
    "district" <= this is an array
    """
    logger.debug("Referendum contest_type")
    referendum_title = one_contest_referendum_structured_json['referendumTitle']
    referendum_subtitle = one_contest_referendum_structured_json['referendumSubtitle']
    referendum_url = one_contest_referendum_structured_json['referendumUrl']

    # These following fields exist for both candidates and referendum
    results = process_contest_common_fields_from_structured_json(one_contest_referendum_structured_json)
    ballot_placement = results['ballot_placement']  # A number specifying the position of this contest
    # on the voter's ballot.
    primary_party = results['primary_party']  # If this is a partisan election, the name of the party it is for.
    district_name = results['district_name']  # The name of the district.
    district_scope = results['district_scope']   # The geographic scope of this district. If unspecified the
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    district_id = results['district_id']
    electorate_specifications = results['electorate_specifications']  # A description of any additional
    #  eligibility requirements for voting in this contest.
    special = results['special']  # "Yes" or "No" depending on whether this a contest being held
    # outside the normal election cycle.

    if save_to_db:
        if referendum_title and referendum_subtitle and district_name and district_scope and district_id \
                and google_civic_election_id:
            try:
                query1 = ContestMeasure.objects.all()
                query1 = query1.filter(referendum_title__exact=referendum_title)
                query1 = query1.filter(google_civic_election_id__exact=google_civic_election_id)
                query1 = query1.filter(district_scope__exact=district_scope)

                # Was at least one existing entry found based on the above criteria?
                if len(query1):
                    google_civic_contest_referendum = query1[0]
                # If no entries found previously, create a new entry
                else:
                    google_civic_contest_referendum = \
                        ContestMeasure.objects.create(referendum_title=referendum_title,
                                                                    referendum_subtitle=referendum_subtitle,
                                                                    google_civic_election_id=google_civic_election_id,
                                                                    referendum_url=referendum_url,
                                                                    ballot_placement=ballot_placement,
                                                                    primary_party=primary_party,
                                                                    district_name=district_name,
                                                                    district_scope=district_scope,
                                                                    district_id=district_id,
                                                                    electorate_specifications=electorate_specifications,
                                                                    special=special,
                                                                    )

                # Save information about this contest item on the voter's ballot from: ballot_placement
            except Exception as e:
                handle_record_not_found_exception(e, logger=logger)

    return


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
