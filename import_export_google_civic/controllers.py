# import_export_google_civic/controllers.py
# Brought to you by We Vote. Be good.
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html
# -*- coding: UTF-8 -*-

import json
import requests
from election.models import Election, ElectionManager
from exception.models import handle_record_not_found_exception
from import_export_google_civic.models import GoogleCivicContestOffice, GoogleCivicBallotItemManager, \
    GoogleCivicCandidateCampaign, GoogleCivicContestReferendum, GoogleCivicElection
from config.base import get_environment_variable
from wevote_functions.models import logger, value_exists

# TODO DALE is it ok to import logger like above? the following line was saying it couldn't find admin.get_logger
# logger = wevote_functions.admin.get_logger(__name__)

GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
ELECTION_QUERY_URL = get_environment_variable("ELECTION_QUERY_URL")
VOTER_INFO_URL = get_environment_variable("VOTER_INFO_URL")
VOTER_INFO_JSON_FILE = get_environment_variable("VOTER_INFO_JSON_FILE")


# See import_data/election_query_sample.json
def retrieve_from_google_civic_api_election_query():
    # Request json file from Google servers
    logger.info("Loading json data from Google servers, API call electionQuery")
    request = requests.get(ELECTION_QUERY_URL, params={
        "key": GOOGLE_CIVIC_API_KEY,  # This comes from an environment variable
    })
    return json.loads(request.text)


def store_results_from_google_civic_api_election_query(structured_json):
    elections_list_json = structured_json['elections']
    for one_election in elections_list_json:
        raw_ocd_division_id = one_election['ocdDivisionId']
        election_date_text = one_election['electionDay']
        google_civic_election_id = one_election['id']
        election_name = one_election['name']

        election_manager = ElectionManager()
        results = election_manager.update_or_create_election(
            google_civic_election_id, election_name, election_date_text, raw_ocd_division_id)

    return results


# Complete description of all Google Civic fields:
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/index.html
# voterInfoQuery Details:
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html#voterInfoQuery
def import_voterinfo_from_json(save_to_db):
    """
    Get the json data, and call the sub functions that
    :return:
    """
    load_from_google_servers = False
    if load_from_google_servers:
        # Request json file from Google servers
        logger.info("Loading from Google servers")
        request = requests.get(VOTER_INFO_URL, params={
            "key": GOOGLE_CIVIC_API_KEY,  # This comes from an environment variable
            "address": "254 Hartford Street San Francisco CA",
            "electionId": "2000",
        })
        structured_json = json.loads(request.text)
    else:
        # Load saved json from local file
        logger.info("Loading from local file")

        with open(VOTER_INFO_JSON_FILE) as json_data:
            structured_json = json.load(json_data)

    # Process election and store in local db cache
    # google_civic_election_id = The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = process_election_from_structured_json(structured_json['election'], save_to_db)

    # Loop through all pollingLocations and store in local db cache
    process_polling_locations_from_structured_json(structured_json['pollingLocations'], save_to_db)

    # Loop through all contests and store in local db cache
    process_contests_from_structured_json(structured_json['contests'], google_civic_election_id, save_to_db)

    # We ignore "kind", "state", and "normalizedInput"
    # "kind": "civicinfo#voterInfoResponse",

    # "state" has information (including URLs) about the election adminstrators

    # "normalizedInput": {
    #   "line1": "254 hartford st",
    #   "city": "san francisco",
    #   "state": "CA",
    #   "zip": "94114"
    #  },
    return


def process_election_from_structured_json(election_structured_data, save_to_db):
    """
    "id": "4111",
    "name": "MI Special Election",
    "electionDay": "2015-05-05"
    """
    google_civic_election_id = election_structured_data['id']
    name = election_structured_data['name']
    election_day = election_structured_data['electionDay']
    # DALE 2015-05-01 The election type is currently in the contests, and not in the election
    # is_general_election = False  # Reset to false
    # is_primary_election = False  # Reset to false
    # is_runoff_election = False  # Reset to false
    # for case in switch(election_structured_data['type']):
    #     if case('Primary'):
    #         is_primary_election = True
    #         break
    #     if case('Run-off'):
    #         is_runoff_election = True
    #         break
    #     if case('General'): pass
    #     if case():  # default
    #         is_general_election = True

    if save_to_db:
        if google_civic_election_id and name and election_day:
            try:
                # Try to find earlier version based on Google's unique identifier google_civic_election_id
                query1 = GoogleCivicContestOffice.objects.all()
                query1 = query1.filter(google_civic_election_id__exact=google_civic_election_id)

                # Was at least one existing entry found based on the above criteria?
                if len(query1):
                    google_civic_election_entry = query1[0]
                # If no entries found previously, create a new entry
                else:
                    google_civic_election_entry \
                        = GoogleCivicElection.objects.create(google_civic_election_id=google_civic_election_id,
                                                             name=name,
                                                             election_day=election_day,
                                                             # is_general_election=is_general_election,
                                                             # is_primary_election=is_primary_election,
                                                             # is_runoff_election=is_runoff_election,
                                                             )
                # Return the google_civic_election_id so we can tie all of the Offices and Measures to this election
            except Exception as e:
                handle_record_not_found_exception(e, logger=logger)

    return google_civic_election_id


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


def process_contests_from_structured_json(contests_structured_json, google_civic_election_id, save_to_db):
    """
    "type": 'General', 'Primary', 'Run-off'
    or
    "type": "Referendum",
    """
    local_ballot_order = 0
    for one_contest in contests_structured_json:
        local_ballot_order += 1
        contest_type = one_contest['type']
        # If the contest is for an elected office, we use the function:
        #   process_contest_office_from_structured_json
        if contest_type in ('General', 'Primary', 'Run-off'):
            process_contest_office_from_structured_json(
                one_contest, google_civic_election_id, local_ballot_order, save_to_db)

        # If the contest is a referendum/initiative/measure, we use the function:
        #   process_contest_referendum_from_structured_json
        elif contest_type == 'Referendum':
            process_contest_referendum_from_structured_json(
                one_contest, google_civic_election_id, local_ballot_order, save_to_db)


def process_contest_office_from_structured_json(
        one_contest_office_structured_json, google_civic_election_id, local_ballot_order, save_to_db):
    voter_id = 1  # TODO Temp

    logger.debug("General contest_type")
    office = one_contest_office_structured_json['office']

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

    results = process_contest_common_fields_from_structured_json(one_contest_office_structured_json)
    ballot_placement = results['ballot_placement']  # A number specifying the position of this contest
    # on the voter's ballot.
    primary_party = results['primary_party']  # If this is a partisan election, the name of the party it is for.
    district_name = results['district_name']  # The name of the district.
    district_scope = results['district_scope']   # The geographic scope of this district. If unspecified the
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    district_ocd_id = results['district_ocd_id']
    electorate_specifications = results['electorate_specifications']  # A description of any additional
    # eligibility requirements for voting in this contest.
    special = results['special']  # "Yes" or "No" depending on whether this a contest being held
    # outside the normal election cycle.

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
    level_structured_json = one_contest_office_structured_json['level']
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
    roles_structured_json = one_contest_office_structured_json['roles']
    # for one_role in roles_structured_json:
    # Figure out how we are going to use level info

    candidates = one_contest_office_structured_json['candidates']

    internal_contest_office_id = 0  # Set to 0 in case a new one is not created
    # Note that all of the information saved here is independent of a particular voter
    if save_to_db:
        if office and district_name and district_scope and district_ocd_id and google_civic_election_id:
            try:
                # Try to find earlier version based on name of the office google_civic_election_id
                query1 = GoogleCivicContestOffice.objects.all()
                query1 = query1.filter(google_civic_election_id__exact=google_civic_election_id)
                query1 = query1.filter(district_scope__exact=district_scope)
                query1 = query1.filter(office__exact=office)

                # Was at least one existing entry found based on the above criteria?
                if len(query1):
                    google_civic_contest_office = query1[0]
                # If no entries found previously, create a new entry
                else:
                    google_civic_contest_office = \
                        GoogleCivicContestOffice.objects.create(office=office,
                                                                google_civic_election_id=google_civic_election_id,
                                                                number_voting_for=number_voting_for,
                                                                number_elected=number_elected,
                                                                contest_level0=contest_level0,
                                                                contest_level1=contest_level1,
                                                                contest_level2=contest_level2,
                                                                ballot_placement=ballot_placement,
                                                                primary_party=primary_party,
                                                                district_name=district_name,
                                                                district_scope=district_scope,
                                                                district_ocd_id=district_ocd_id,
                                                                electorate_specifications=electorate_specifications,
                                                                special=special,
                                                                )
                # The internal id is needed since there isn't a ContestOffice google identifier
                internal_contest_office_id = google_civic_contest_office.id
            except Exception as e:
                handle_record_not_found_exception(e, logger=logger)

        if value_exists(voter_id) and value_exists(google_civic_election_id) and value_exists(district_ocd_id):
            google_civic_ballot_item_manager = GoogleCivicBallotItemManager()
            google_civic_ballot_item_manager.save_ballot_item_for_voter(
                voter_id, google_civic_election_id, district_ocd_id, ballot_placement, local_ballot_order)

    process_candidates_from_structured_json(
        candidates, google_civic_election_id, internal_contest_office_id, save_to_db)

    return


# GoogleRepresentatives
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.representatives.html
def process_candidates_from_structured_json(
        candidates_structured_json, google_civic_election_id, google_civic_contest_office_id, save_to_db):
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
    for one_candidate in candidates_structured_json:
        name = one_candidate['name']
        party = one_candidate['party']
        if 'order_on_ballot' in one_candidate:
            order_on_ballot = one_candidate['orderOnBallot']
        else:
            order_on_ballot = 0
        if 'candidateUrl' in one_candidate:
            candidate_url = one_candidate['candidateUrl']
        else:
            candidate_url = ''

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
                        facebook_url = one_channel['id']
                    if one_channel['type'] == 'Twitter':
                        twitter_url = one_channel['id']
                    if one_channel['type'] == 'GooglePlus':
                        google_plus_url = one_channel['id']
                    if one_channel['type'] == 'YouTube':
                        youtube_url = one_channel['id']

        if save_to_db:
            if name and google_civic_election_id and google_civic_contest_office_id:
                try:
                    # Try to find existing candidate (based on name, google_civic_election_id
                    # and google_civic_contest_office_id
                    query1 = GoogleCivicCandidateCampaign.objects.all()
                    query1 = query1.filter(name__exact=name)
                    query1 = query1.filter(google_civic_election_id__exact=google_civic_election_id)
                    query1 = query1.filter(google_civic_contest_office_id__exact=google_civic_contest_office_id)

                    # Was at least one existing entry found based on the above criteria?
                    if len(query1):
                        google_civic_candidate_campaign = query1[0]
                    # If no entries found previously, create a new entry
                    else:
                        google_civic_candidate_campaign = \
                            GoogleCivicCandidateCampaign.objects.create(
                                name=name,
                                party=party,
                                google_civic_contest_office_id=google_civic_contest_office_id,
                                google_civic_election_id=google_civic_election_id,
                                order_on_ballot=order_on_ballot,
                                candidate_url=candidate_url,
                                facebook_url=facebook_url,
                                twitter_url=twitter_url,
                                google_plus_url=google_plus_url,
                                youtube_url=youtube_url,
                                )
                except Exception as e:
                    handle_record_not_found_exception(e, logger=logger)

    return


def process_contest_referendum_from_structured_json(
        one_contest_referendum_structured_json, google_civic_election_id, local_ballot_order, save_to_db):
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
    district_ocd_id = results['district_ocd_id']
    electorate_specifications = results['electorate_specifications']  # A description of any additional
    #  eligibility requirements for voting in this contest.
    special = results['special']  # "Yes" or "No" depending on whether this a contest being held
    # outside the normal election cycle.

    if save_to_db:
        if referendum_title and referendum_subtitle and district_name and district_scope and district_ocd_id \
                and google_civic_election_id:
            try:
                query1 = GoogleCivicContestReferendum.objects.all()
                query1 = query1.filter(referendum_title__exact=referendum_title)
                query1 = query1.filter(google_civic_election_id__exact=google_civic_election_id)
                query1 = query1.filter(district_scope__exact=district_scope)

                # Was at least one existing entry found based on the above criteria?
                if len(query1):
                    google_civic_contest_referendum = query1[0]
                # If no entries found previously, create a new entry
                else:
                    google_civic_contest_referendum = \
                        GoogleCivicContestReferendum.objects.create(referendum_title=referendum_title,
                                                                    referendum_subtitle=referendum_subtitle,
                                                                    google_civic_election_id=google_civic_election_id,
                                                                    referendum_url=referendum_url,
                                                                    ballot_placement=ballot_placement,
                                                                    primary_party=primary_party,
                                                                    district_name=district_name,
                                                                    district_scope=district_scope,
                                                                    district_ocd_id=district_ocd_id,
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

def process_contest_common_fields_from_structured_json(one_contest_structured_json):
    # These following fields exist for both candidates and referendum

    results = {}
    # A number specifying the position of this contest on the voter's ballot.
    if 'ballotPlacement' in one_contest_structured_json:
        results['ballot_placement'] = one_contest_structured_json['ballotPlacement']
    else:
        results['ballot_placement'] = 0

    # If this is a partisan election, the name of the party it is for.
    if 'primaryParty' in one_contest_structured_json:
        results['primary_party'] = one_contest_structured_json['primaryParty']
    else:
        results['primary_party'] = ''

    # The name of the district.
    results['district_name'] = one_contest_structured_json['district']['name']

    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    results['district_scope'] = one_contest_structured_json['district']['scope']

    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    results['district_ocd_id'] = one_contest_structured_json['district']['id']

    # A description of any additional eligibility requirements for voting in this contest.
    if 'electorateSpecifications' in one_contest_structured_json:
        results['electorate_specifications'] = one_contest_structured_json['electorateSpecifications']
    else:
        results['electorate_specifications'] = ''

    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    if 'special' in one_contest_structured_json:
        results['special'] = one_contest_structured_json['special']
    else:
        results['special'] = ''

    return results
