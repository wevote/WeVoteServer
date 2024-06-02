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
from candidate.models import CandidateManager, CandidateListManager
from config.base import get_environment_variable
from django.utils.timezone import localtime, now
from election.models import ElectionManager
from geopy.geocoders import get_geocoder_for_service
import json
from measure.models import ContestMeasureManager, ContestMeasureListManager
from office.models import ContestOfficeManager, ContestOfficeListManager
from polling_location.models import PollingLocationManager
import requests
from voter.models import fetch_voter_id_from_voter_device_link, VoterAddressManager
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

OFFICE_NAMES_WITH_NO_STATE = ['President of the United States']
PRESIDENTIAL_CANDIDATES_JSON_LIST = [
    {
        'id': 54804,
        'race': 31729,
        'is_incumbent': True,
        'party_affiliation': [{
            'id': 1,
            'name': 'Republican Party',
            'url': 'https://ballotpedia.org/Republican_Party',
        }],
        'person': {
            'id': 15180,
            'image': {
            },
            'name': 'Donald Trump',
            'first_name': 'Donald',
            'last_name': 'Trump',
        },
    },
    {
        'id': 59216,
        'race': 31729,
        'is_incumbent': False,
        'party_affiliation': [{
            'id': 2,
            'name': 'Democratic Party',
            'url': 'https://ballotpedia.org/Democratic_Party',
        }],
        'person': {
            'id': 26709,
            'image': {
            },
            'name': 'Joe Biden',
            'first_name': 'Joe',
            'last_name': 'Biden',
        },
    },
]


# GoogleRepresentatives
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.representatives.html
def process_candidates_from_structured_json(
        candidates_structured_json=None,
        google_civic_election_id=None,
        ocd_division_id=None,
        state_code=None,
        contest_office_id=None,
        contest_office_we_vote_id=None):
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
    contest_office_name = ""
    if positive_value_exists(contest_office_we_vote_id):
        office_manager = ContestOfficeManager()
        results = office_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_name = contest_office.office_name

    results = {}
    for one_candidate in candidates_structured_json:
        candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        # For some reason Google Civic API violates the JSON standard and uses a / in front of '
        candidate_name = candidate_name.replace("/'", "'")
        candidate_name = candidate_name.strip()
        # We want to save the name exactly as it comes from the Google Civic API
        google_civic_candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        google_civic_candidate_name = google_civic_candidate_name.strip()
        party = one_candidate['party'] if 'party' in one_candidate else ''
        party = party.strip()
        order_on_ballot = one_candidate['orderOnBallot'] if 'orderOnBallot' in one_candidate else 0
        candidate_url = one_candidate['candidateUrl'] if 'candidateUrl' in one_candidate else ''
        candidate_contact_form_url = one_candidate['candidate_contact_form_url'] \
            if 'candidate_contact_form_url' in one_candidate else ''
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
        # ...and looked to see if there were any other candidate entries for this election (in case the
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

            updated_candidate_values = {
                # Values we search against
                'google_civic_election_id': google_civic_election_id,
            }
            if positive_value_exists(ocd_division_id):
                updated_candidate_values['ocd_division_id'] = ocd_division_id
            if positive_value_exists(candidate_name):
                # Note: When we decide to start updating candidate_name elsewhere within We Vote, we should stop
                #  updating candidate_name via subsequent Google Civic imports
                updated_candidate_values['candidate_name'] = candidate_name
                # We store the literal spelling here, so we can match in the future, even if we customize candidate_name
                updated_candidate_values['google_civic_candidate_name'] = candidate_name
            if positive_value_exists(contest_office_name) and contest_office_name in OFFICE_NAMES_WITH_NO_STATE:
                updated_candidate_values['state_code'] = 'NA'
            elif positive_value_exists(state_code):
                state_code_for_error_checking = state_code.lower()
                # Limit to 2 digits, so we don't exceed the database limit
                state_code_for_error_checking = state_code_for_error_checking[-2:]
                # Make sure we recognize the state
                list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                           state_code_for_error_checking in key.lower()]
                state_code_for_error_checking = list_of_states_matching.pop()
                updated_candidate_values['state_code'] = state_code_for_error_checking
            if positive_value_exists(party):
                updated_candidate_values['party'] = party
            if positive_value_exists(email):
                updated_candidate_values['candidate_email'] = email
            if positive_value_exists(phone):
                updated_candidate_values['candidate_phone'] = phone
            if positive_value_exists(order_on_ballot):
                updated_candidate_values['order_on_ballot'] = order_on_ballot
            if positive_value_exists(candidate_url):
                updated_candidate_values['candidate_url'] = candidate_url
            if positive_value_exists(candidate_contact_form_url):
                updated_candidate_values['candidate_contact_form_url'] = candidate_contact_form_url
            if positive_value_exists(photo_url):
                updated_candidate_values['photo_url'] = photo_url
            if positive_value_exists(facebook_url):
                updated_candidate_values['facebook_url'] = facebook_url
            if positive_value_exists(twitter_url):
                updated_candidate_values['twitter_url'] = twitter_url
            if positive_value_exists(google_plus_url):
                updated_candidate_values['google_plus_url'] = google_plus_url
            if positive_value_exists(youtube_url):
                updated_candidate_values['youtube_url'] = youtube_url
            # 2016-02-20 Google Civic sometimes changes the name of contests, which can create a new contest
            #  so we may need to update the candidate to a new contest_office_id
            if positive_value_exists(contest_office_id):
                updated_candidate_values['contest_office_id'] = contest_office_id
            if positive_value_exists(contest_office_we_vote_id):
                updated_candidate_values['contest_office_we_vote_id'] = contest_office_we_vote_id
            if positive_value_exists(contest_office_name):
                updated_candidate_values['contest_office_name'] = contest_office_name

            candidate_manager = CandidateManager()
            results = candidate_manager.update_or_create_candidate(
                we_vote_id, google_civic_election_id,
                ocd_division_id, contest_office_id, contest_office_we_vote_id,
                google_civic_candidate_name, updated_candidate_values)

    return results


def groom_and_store_google_civic_ballot_json_2021(
        one_ballot_json,
        google_civic_election_id='',
        state_code='',
        polling_location_we_vote_id='',
        election_day_text='',
        voter_id=0,
        existing_offices_by_election_dict={},
        existing_candidate_objects_dict={},
        existing_candidate_to_office_links_dict={},
        existing_measure_objects_dict={},
        new_office_we_vote_ids_list=[],
        new_candidate_we_vote_ids_list=[],
        new_measure_we_vote_ids_list=[],
        update_or_create_rules={},
        use_ctcl=False,
        use_vote_usa=False,
        ):
    status = ""
    success = False
    ballot_item_dict_list = []
    incoming_state_code = state_code

    error = one_ballot_json.get('error', {})
    errors = error.get('errors', {})
    if len(errors):
        # logger.debug("groom_and_store_google_civic_ballot_json_2021 failed: " + str(errors))
        for one_error in errors:
            try:
                if 'reason' in one_error:
                    if one_error['reason'] == "notFound":
                        # Ballot data not found at this location
                        address_not_found = True
                    if one_error['reason'] == "parseError":
                        # Not an address format Google can parse
                        address_not_found = True
                if 'message' in one_error:
                    status += "VOTER_INFO_QUERY_ERROR_MESSAGE: " + one_error['message'] + " "
            except Exception as e:
                status += "VOTER_INFO_QUERY_PROBLEM_PARSING_ERROR: " + str(e) + ' '

    if 'election' not in one_ballot_json or 'id' not in one_ballot_json['election']:
        status += "VOTER_INFO_QUERY_ONE_BALLOT_JSON_MISSING_ELECTION "
        success = False
        results = {
            'success':                                  success,
            'status':                                   status,
            'google_civic_election_id':                 google_civic_election_id,
            'ballot_item_dict_list':                    ballot_item_dict_list,
            'existing_offices_by_election_dict':        existing_offices_by_election_dict,
            'existing_candidate_objects_dict':          existing_candidate_objects_dict,
            'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
            'existing_measure_objects_dict':            existing_measure_objects_dict,
            'new_office_we_vote_ids_list':              new_office_we_vote_ids_list,
            'new_candidate_we_vote_ids_list':           new_candidate_we_vote_ids_list,
            'new_measure_we_vote_ids_list':             new_measure_we_vote_ids_list,
        }
        return results

    if 'id' in one_ballot_json['election']:
        election_data_retrieved = True
        success = True
        if positive_value_exists(use_ctcl):
            # We may not need this
            ctcl_election_uuid = one_ballot_json['election']['id']
        elif positive_value_exists(use_vote_usa):
            # We may not need this
            vote_usa_election_id = one_ballot_json['election']['id']
        else:
            google_civic_election_id_from_json = one_ballot_json['election']['id']

    if 'electionDay' in one_ballot_json['election']:
        election_day_text = one_ballot_json['election']['electionDay']
    # We may not need this
    election_description_text = ''
    if 'name' in one_ballot_json['election']:
        election_description_text = one_ballot_json['election']['name']

    voter_address_dict = one_ballot_json['normalizedInput'] if 'normalizedInput' in one_ballot_json else {}
    if positive_value_exists(voter_id):
        if positive_value_exists(voter_address_dict):
            voter_address_manager = VoterAddressManager()
            voter_address_manager.update_voter_address_with_normalized_values(
                voter_id, voter_address_dict)
            # Note that neither 'success' nor 'status' are set here because updating the voter_address with normalized
            # values isn't critical to the success of storing the ballot for a voter
    # We don't store the normalized address information when we capture a ballot for a map point

    ocd_division_id = ''
    if 'ocdDivisionId' in one_ballot_json['election']:
        try:
            ocd_division_id = one_ballot_json['election']['ocdDivisionId']
            state_code = extract_state_from_ocd_division_id(ocd_division_id)
        except Exception as e:
            ocd_division_id = ''
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
    if not positive_value_exists(state_code):
        state_code = incoming_state_code

    election_year_integer = 0
    if positive_value_exists(election_day_text):
        election_year_string = election_day_text[:4]
        if election_year_string and len(election_year_string) == 4:
            election_year_integer_test = convert_to_int(election_year_string)
            if election_year_integer_test > 2000:
                election_year_integer = election_year_integer_test
    if not positive_value_exists(election_year_integer):
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        current_year = datetime_now.year
        election_year_integer = convert_to_int(current_year)

    local_ballot_order = 0
    if 'contests' in one_ballot_json:
        for one_contest_json in one_ballot_json['contests']:
            local_ballot_order += 1  # Needed if ballotPlacement not provided by API. Related to ballot_placement.
            contest_type_calculated = 'office'
            if 'type' in one_contest_json:
                # Google Civic format uses 'type', but not all of our partners do
                contest_type = one_contest_json['type']
                if contest_type.lower() == 'referendum' or 'referendumTitle' in one_contest_json:
                    contest_type_calculated = 'referendum'
            elif 'referendumTitle' in one_contest_json:
                # Vote USA not supporting 'type', so we determine with this
                contest_type_calculated = 'referendum'
            elif 'office' in one_contest_json:
                # Vote USA not supporting 'type', so we determine with this
                contest_type_calculated = 'office'
            elif 'ballot_measures' in one_contest_json:
                # This might be a holdover from Ballotpedia, and may need to be removed
                contest_type_calculated = 'referendum'
            else:
                # Assume we are working with office
                pass
            if contest_type_calculated == 'referendum':  # Referendum
                try:
                    process_contest_results = groom_and_store_google_civic_measure_json_2021(
                        ballot_item_dict_list=ballot_item_dict_list,
                        election_day_text=election_day_text,
                        existing_measure_objects_dict=existing_measure_objects_dict,
                        google_civic_election_id=google_civic_election_id,
                        local_ballot_order=local_ballot_order,
                        new_measure_we_vote_ids_list=new_measure_we_vote_ids_list,
                        one_contest_json=one_contest_json,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        state_code=state_code,
                        update_or_create_rules=update_or_create_rules,
                        use_ctcl=use_ctcl,
                        use_vote_usa=use_vote_usa,
                        voter_id=voter_id,
                    )
                    existing_measure_objects_dict = process_contest_results['existing_measure_objects_dict']
                    new_measure_we_vote_ids_list = process_contest_results['new_measure_we_vote_ids_list']
                    ballot_item_dict_list = process_contest_results['ballot_item_dict_list']
                except Exception as e:
                    status += "REFERENDUM_FAIL: " + str(e) + ' '
            else:
                try:
                    process_contest_results = groom_and_store_google_civic_office_json_2021(
                        one_contest_json=one_contest_json,
                        google_civic_election_id=google_civic_election_id,
                        election_day_text=election_day_text,
                        state_code=state_code,
                        election_year_integer=election_year_integer,
                        election_ocd_division_id=ocd_division_id,
                        local_ballot_order=local_ballot_order,
                        voter_id=voter_id,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        ballot_item_dict_list=ballot_item_dict_list,
                        existing_candidate_objects_dict=existing_candidate_objects_dict,
                        existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                        existing_offices_by_election_dict=existing_offices_by_election_dict,
                        new_office_we_vote_ids_list=new_office_we_vote_ids_list,
                        new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                        use_ctcl=use_ctcl,
                        use_vote_usa=use_vote_usa,
                        update_or_create_rules=update_or_create_rules,
                    )
                    existing_candidate_objects_dict = process_contest_results['existing_candidate_objects_dict']
                    existing_candidate_to_office_links_dict = \
                        process_contest_results['existing_candidate_to_office_links_dict']
                    existing_offices_by_election_dict = process_contest_results['existing_offices_by_election_dict']
                    new_office_we_vote_ids_list = process_contest_results['new_office_we_vote_ids_list']
                    new_candidate_we_vote_ids_list = process_contest_results['new_candidate_we_vote_ids_list']
                    ballot_item_dict_list = process_contest_results['ballot_item_dict_list']
                except Exception as e:
                    status += "OFFICE_FAIL: " + str(e) + ' '
    else:
        status += "NO_CONTESTS_IN_JSON "
    results = {
        'success':                              success,
        'status':                               status,
        'google_civic_election_id':             google_civic_election_id,
        'ballot_item_dict_list':                ballot_item_dict_list,
        'existing_offices_by_election_dict':    existing_offices_by_election_dict,
        'existing_candidate_objects_dict':      existing_candidate_objects_dict,
        'existing_candidate_to_office_links_dict': existing_candidate_to_office_links_dict,
        'existing_measure_objects_dict':        existing_measure_objects_dict,
        'new_office_we_vote_ids_list':          new_office_we_vote_ids_list,
        'new_candidate_we_vote_ids_list':       new_candidate_we_vote_ids_list,
        'new_measure_we_vote_ids_list':         new_measure_we_vote_ids_list,
    }
    return results


def groom_and_store_google_civic_candidates_json_2021(
        candidates_structured_json={},
        google_civic_election_id='',
        office_ocd_division_id='',
        state_code='',
        contest_office_id=0,
        contest_office_we_vote_id='',
        contest_office_name='',
        election_year_integer=0,
        existing_candidate_objects_dict={},
        existing_candidate_to_office_links_dict={},
        new_candidate_we_vote_ids_list=[],
        update_or_create_rules={},
        use_ctcl=False,
        use_vote_usa=False,
        vote_usa_office_id=''):
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
    status = ''
    success = True
    results = {}
    candidate_manager = CandidateManager()
    for one_candidate in candidates_structured_json:
        # Reset
        candidate_we_vote_id = ''

        candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        # For some reason Google Civic API violates the JSON standard and uses a / in front of '
        candidate_name = candidate_name.replace("/'", "'")
        candidate_name = candidate_name.strip()
        # We want to save the name exactly as it comes from the Google Civic API
        google_civic_candidate_name = one_candidate['name'] if 'name' in one_candidate else ''
        google_civic_candidate_name = google_civic_candidate_name.strip()
        party = one_candidate['party'] if 'party' in one_candidate else ''
        party = party.strip()
        order_on_ballot = one_candidate['orderOnBallot'] if 'orderOnBallot' in one_candidate else 0
        candidate_url = one_candidate['candidateUrl'] if 'candidateUrl' in one_candidate else ''
        if positive_value_exists(candidate_url):
            if 'http' not in candidate_url:
                candidate_url = 'https://' + candidate_url
        candidate_contact_form_url = one_candidate['candidate_contact_form_url'] \
            if 'candidate_contact_form_url' in one_candidate else ''
        if positive_value_exists(candidate_contact_form_url):
            if 'http' not in candidate_contact_form_url:
                candidate_contact_form_url = 'https://' + candidate_contact_form_url
        candidate_email = one_candidate['email'] if 'email' in one_candidate else ''
        candidate_phone = one_candidate['phone'] if 'phone' in one_candidate else ''
        photo_url = ''
        photo_url_from_ctcl = ''
        photo_url_from_vote_usa = ''
        if positive_value_exists(use_ctcl):
            photo_url_from_ctcl = one_candidate['photoUrl'] if 'photoUrl' in one_candidate else ''
        elif positive_value_exists(use_vote_usa):
            photo_url_from_vote_usa = one_candidate['photoUrl'] if 'photoUrl' in one_candidate else ''
        else:
            photo_url = one_candidate['photoUrl'] if 'photoUrl' in one_candidate else ''

        # Make sure we start with empty channel values
        ballotpedia_candidate_url = ''
        blogger_url = ''
        candidate_twitter_handle = ''
        facebook_url = ''
        flickr_url = ''
        go_fund_me_url = ''
        google_plus_url = ''
        instagram_handle = ''
        linkedin_url = ''
        twitter_url = ''
        vimeo_url = ''
        wikipedia_url = ''
        youtube_url = ''
        if 'channels' in one_candidate:
            channels = one_candidate['channels']
            for one_channel in channels:
                if 'type' in one_channel:
                    if one_channel['type'] == 'BallotPedia':
                        ballotpedia_candidate_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(ballotpedia_candidate_url):
                            if 'http' not in ballotpedia_candidate_url:
                                ballotpedia_candidate_url = 'https://' + ballotpedia_candidate_url
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
                            candidate_twitter_handle = extract_twitter_handle_from_text_string(twitter_url)
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
                        if not positive_value_exists(ballotpedia_candidate_url):
                            if "ballotpedia.org" in wikipedia_url:
                                ballotpedia_candidate_url = wikipedia_url
                    if one_channel['type'] == 'YouTube':
                        youtube_url = one_channel['id'] if 'id' in one_channel else ''
                        if positive_value_exists(youtube_url):
                            if 'http' not in youtube_url:
                                youtube_url = 'https://' + youtube_url

        # DALE 2016-02-20 It would be helpful to call a service here that disambiguated the candidate
        # ...and linked to a politician
        # ...and looked to see if there were any other candidate entries for this election (in case the
        #   Google Civic contest_office name changed so we generated another contest)

        # candidate_dict
        candidate_ctcl_uuid = ''
        vote_usa_politician_id = ''
        if positive_value_exists(use_ctcl):
            if 'uuid' in one_candidate and positive_value_exists(one_candidate['uuid']):
                candidate_ctcl_uuid = one_candidate['uuid']
            elif 'id' in one_candidate and positive_value_exists(one_candidate['id']):
                candidate_ctcl_uuid = one_candidate['id']
        elif positive_value_exists(use_vote_usa):
            if 'id' in one_candidate and positive_value_exists(one_candidate['id']):
                vote_usa_politician_id = one_candidate['id']

        continue_searching_for_candidate = True
        create_candidate = False
        if positive_value_exists(use_ctcl) and positive_value_exists(candidate_ctcl_uuid):
            if candidate_ctcl_uuid in existing_candidate_objects_dict:
                candidate = existing_candidate_objects_dict[candidate_ctcl_uuid]
                candidate_we_vote_id = candidate.we_vote_id
                continue_searching_for_candidate = False
            else:
                # Does candidate already exist?
                candidate_results = candidate_manager.retrieve_candidate(
                    candidate_ctcl_uuid=candidate_ctcl_uuid,
                    candidate_year=election_year_integer,
                    read_only=True
                )
                if candidate_results['candidate_found']:
                    continue_searching_for_candidate = False
                    candidate = candidate_results['candidate']
                    candidate_we_vote_id = candidate.we_vote_id
                    if candidate_ctcl_uuid not in existing_candidate_objects_dict:
                        existing_candidate_objects_dict[candidate_ctcl_uuid] = candidate
                    # In the future, we will want to look for updated data to save
                elif candidate_results['MultipleObjectsReturned']:
                    continue_searching_for_candidate = False
                    status += "MORE_THAN_ONE_CANDIDATE_WITH_SAME_CTCL_UUID1 (" + str(candidate_ctcl_uuid) + "/" + \
                              str(candidate_name) + ")"
                    continue
                elif not candidate_results['success']:
                    continue_searching_for_candidate = False
                    status += "RETRIEVE_BY_CANDIDATE_CTCL_UUID_FAILED "
                    status += candidate_results['status']
                    continue
                else:
                    continue_searching_for_candidate = True
        elif positive_value_exists(use_vote_usa) and positive_value_exists(vote_usa_politician_id):
            if vote_usa_politician_id in existing_candidate_objects_dict:
                candidate = existing_candidate_objects_dict[vote_usa_politician_id]
                candidate_we_vote_id = candidate.we_vote_id
                continue_searching_for_candidate = False
            else:
                # Does candidate already exist?
                # Vote USA uses permanent office and politician ids, so finding an existing candidate from a prior
                #  election in our database is not uncommon. If it isn't linked to the relevant
                #  google_civic_election_id, then we still consider the candidate "not found" and we create a new
                #
                candidate_results = candidate_manager.retrieve_candidate_from_vote_usa_variables(
                    candidate_year=election_year_integer,
                    vote_usa_office_id=vote_usa_office_id,
                    vote_usa_politician_id=vote_usa_politician_id,
                    google_civic_election_id=google_civic_election_id,
                    read_only=False)
                candidate_to_office_link_missing = False
                candidate_we_vote_id_to_link = ''
                try:
                    candidate_to_office_link_missing = candidate_results['candidate_to_office_link_missing']
                    candidate_we_vote_id_to_link = candidate_results['candidate_we_vote_id_to_link']
                except Exception as e:
                    status += "candidate_to_office_link_missing KEY_ERROR: " + str(e) + " "
                if candidate_to_office_link_missing:
                    status += candidate_results['status']
                    if positive_value_exists(candidate_we_vote_id_to_link):
                        status += "CANDIDATE_TO_OFFICE_LINK_MISSING-ADDING "
                        continue_searching_for_candidate = False
                        link_results = candidate_manager.get_or_create_candidate_to_office_link(
                            candidate_we_vote_id=candidate_results['candidate_we_vote_id_to_link'],
                            contest_office_we_vote_id=contest_office_we_vote_id,
                            google_civic_election_id=google_civic_election_id,
                            state_code=state_code)
                        if not link_results['success']:
                            status += link_results['status']
                    else:
                        status += "CANDIDATE_TO_OFFICE_LINK_MISSING-NO_CANDIDATE_WE_VOTE_ID "
                elif candidate_results['candidate_found']:
                    continue_searching_for_candidate = False
                    candidate = candidate_results['candidate']
                    candidate_we_vote_id = candidate.we_vote_id
                    if positive_value_exists(candidate.photo_url_from_vote_usa) \
                            and not positive_value_exists(candidate.vote_usa_profile_image_url_https):
                        from import_export_vote_usa.controllers import \
                            retrieve_and_store_vote_usa_candidate_photo
                        results = retrieve_and_store_vote_usa_candidate_photo(candidate)
                        if results['success']:
                            candidate = results['candidate']
                    existing_candidate_objects_dict[vote_usa_politician_id] = candidate
                    # In the future, we will want to look for updated data to save
                elif candidate_results['MultipleObjectsReturned']:
                    continue_searching_for_candidate = False
                    status += candidate_results['status']
                    status += "MORE_THAN_ONE_CANDIDATE_WITH_SAME_VOTE_USA_POLITICIAN_ID " \
                              "(" + str(vote_usa_politician_id) + ") "
                    continue
                elif not candidate_results['success']:
                    continue_searching_for_candidate = False
                    status += "RETRIEVE_BY_CANDIDATE_VOTE_USA_FAILED: "
                    status += candidate_results['status']
                    continue
                else:
                    continue_searching_for_candidate = True

        if continue_searching_for_candidate:
            candidate_list_manager = CandidateListManager()
            state_code_for_search = state_code
            if positive_value_exists(contest_office_name) and contest_office_name in OFFICE_NAMES_WITH_NO_STATE:
                state_code_for_search = 'NA'
            results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
                google_civic_election_id_list=[google_civic_election_id],
                state_code=state_code_for_search,
                candidate_twitter_handle=None,
                candidate_name=candidate_name,
                instagram_handle=None,
                read_only=False)
            if not results['success']:
                continue_searching_for_candidate = False
                status += "FAILED_RETRIEVING_CANDIDATE_FROM_UNIQUE_IDS: " + results['status'] + " "
            elif results['multiple_entries_found']:
                continue_searching_for_candidate = False
                status += "RETRIEVING_CONTEST_FROM_UNIQUE_IDS-MULTIPLE_FOUND: " + results['status'] + " "
            elif results['candidate_found']:
                continue_searching_for_candidate = False
                candidate = results['candidate']
                candidate_we_vote_id = candidate.we_vote_id
                if use_ctcl:
                    if positive_value_exists(candidate_ctcl_uuid) and not positive_value_exists(candidate.ctcl_uuid):
                        candidate.ctcl_uuid = candidate_ctcl_uuid
                        try:
                            candidate.save()
                            if candidate_ctcl_uuid not in existing_candidate_objects_dict:
                                existing_candidate_objects_dict[candidate_ctcl_uuid] = candidate
                        except Exception as e:
                            status += "SAVING_CTCL_UUID_FAILED: " + str(e) + ' '
                    elif candidate_ctcl_uuid not in existing_candidate_objects_dict:
                        existing_candidate_objects_dict[candidate_ctcl_uuid] = candidate
                elif use_vote_usa:
                    if positive_value_exists(vote_usa_politician_id) \
                            and not positive_value_exists(candidate.vote_usa_politician_id):
                        candidate.vote_usa_politician_id = vote_usa_politician_id
                        try:
                            candidate.save()
                            if vote_usa_politician_id not in existing_candidate_objects_dict:
                                existing_candidate_objects_dict[vote_usa_politician_id] = candidate
                        except Exception as e:
                            status += "SAVING_VOTE_USA_POLITICIAN_ID_FAILED: " + str(e) + ' '
                    elif vote_usa_politician_id not in existing_candidate_objects_dict:
                        existing_candidate_objects_dict[vote_usa_politician_id] = candidate
            else:
                create_candidate = True

        # Make sure we have the minimum variables required to uniquely identify a candidate
        allowed_to_create_candidates = 'create_candidates' in update_or_create_rules and positive_value_exists(
            update_or_create_rules['create_candidates'])
        proceed_to_create_candidate = positive_value_exists(create_candidate) and allowed_to_create_candidates
        allowed_to_update_candidates = 'update_candidates' in update_or_create_rules and positive_value_exists(
            update_or_create_rules['update_candidates'])
        proceed_to_update_candidates = allowed_to_update_candidates
        if proceed_to_create_candidate or proceed_to_update_candidates:
            if google_civic_election_id and contest_office_id and candidate_name:
                # NOT using " and office_ocd_division_id"

                # Make sure there isn't an alternate entry for this election and contest_office (under a similar but
                # slightly different name TODO
                # Note: This doesn't deal with duplicate Presidential candidates. These duplicates are caused because
                # candidates are tied to a particular google_civic_election_id, so there is a different candidate entry
                # for each Presidential candidate for each state.

                updated_candidate_values = {
                    # Values we search against
                    'google_civic_election_id': google_civic_election_id,
                }
                if positive_value_exists(office_ocd_division_id):
                    updated_candidate_values['ocd_division_id'] = office_ocd_division_id
                if positive_value_exists(ballotpedia_candidate_url):
                    updated_candidate_values['ballotpedia_candidate_url'] = ballotpedia_candidate_url
                if positive_value_exists(candidate_name):
                    # Note: When we decide to start updating candidate_name elsewhere within We Vote, we should stop
                    #  updating candidate_name via subsequent Google Civic imports
                    updated_candidate_values['candidate_name'] = candidate_name
                    # We store the literal spelling here so we can match in the future, even if we change candidate_name
                    updated_candidate_values['google_civic_candidate_name'] = candidate_name
                if positive_value_exists(election_year_integer):
                    updated_candidate_values['candidate_year'] = election_year_integer
                if positive_value_exists(candidate_contact_form_url):
                    updated_candidate_values['candidate_contact_form_url'] = candidate_contact_form_url
                if positive_value_exists(instagram_handle):
                    updated_candidate_values['instagram_handle'] = instagram_handle
                if positive_value_exists(candidate_email):
                    updated_candidate_values['candidate_email'] = candidate_email
                if positive_value_exists(candidate_phone):
                    updated_candidate_values['candidate_phone'] = candidate_phone
                if positive_value_exists(candidate_twitter_handle):
                    updated_candidate_values['candidate_twitter_handle'] = candidate_twitter_handle
                if positive_value_exists(candidate_url):
                    updated_candidate_values['candidate_url'] = candidate_url
                # 2016-02-20 Google Civic sometimes changes the name of contests, which can create a new contest
                #  so we may need to update the candidate to a new contest_office_id
                if positive_value_exists(contest_office_id):
                    updated_candidate_values['contest_office_id'] = contest_office_id
                if positive_value_exists(contest_office_we_vote_id):
                    updated_candidate_values['contest_office_we_vote_id'] = contest_office_we_vote_id
                if positive_value_exists(contest_office_name):
                    updated_candidate_values['contest_office_name'] = contest_office_name
                if positive_value_exists(facebook_url):
                    updated_candidate_values['facebook_url'] = facebook_url
                if positive_value_exists(flickr_url):
                    updated_candidate_values['flickr_url'] = flickr_url
                if positive_value_exists(go_fund_me_url):
                    updated_candidate_values['go_fund_me_url'] = go_fund_me_url
                if positive_value_exists(google_plus_url):
                    updated_candidate_values['google_plus_url'] = google_plus_url
                if positive_value_exists(linkedin_url):
                    updated_candidate_values['linkedin_url'] = linkedin_url
                if positive_value_exists(order_on_ballot):
                    updated_candidate_values['order_on_ballot'] = order_on_ballot
                if positive_value_exists(party):
                    updated_candidate_values['party'] = party
                if positive_value_exists(photo_url):
                    updated_candidate_values['photo_url'] = photo_url
                if positive_value_exists(photo_url_from_ctcl):
                    updated_candidate_values['photo_url_from_ctcl'] = photo_url_from_ctcl
                if positive_value_exists(photo_url_from_vote_usa):
                    updated_candidate_values['photo_url_from_vote_usa'] = photo_url_from_vote_usa
                if positive_value_exists(contest_office_name) and contest_office_name in OFFICE_NAMES_WITH_NO_STATE:
                    updated_candidate_values['state_code'] = 'NA'
                elif positive_value_exists(state_code):
                    state_code_for_error_checking = state_code.lower()
                    # Limit to 2 digits, so we don't exceed the database limit
                    state_code_for_error_checking = state_code_for_error_checking[-2:]
                    # Make sure we recognize the state
                    list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                               state_code_for_error_checking in key.lower()]
                    state_code_for_error_checking = list_of_states_matching.pop()
                    updated_candidate_values['state_code'] = state_code_for_error_checking
                if positive_value_exists(vimeo_url):
                    updated_candidate_values['vimeo_url'] = vimeo_url
                if positive_value_exists(vote_usa_office_id):
                    updated_candidate_values['vote_usa_office_id'] = vote_usa_office_id
                if positive_value_exists(vote_usa_politician_id):
                    updated_candidate_values['vote_usa_politician_id'] = vote_usa_politician_id
                if positive_value_exists(youtube_url):
                    updated_candidate_values['youtube_url'] = youtube_url

                candidate = None
                candidate_we_vote_id = ''

                if positive_value_exists(proceed_to_create_candidate):
                    # If here we only want to create new candidates -- not update existing candidates
                    # These parameters are required to create a CandidateCampaign
                    if positive_value_exists(google_civic_election_id) and positive_value_exists(candidate_name):
                        candidate_results = candidate_manager.create_candidate_row_entry(updated_candidate_values)
                        new_candidate_created = candidate_results['new_candidate_created']
                        if positive_value_exists(new_candidate_created):
                            candidate = candidate_results['new_candidate']
                            candidate_we_vote_id = candidate.we_vote_id
                            if candidate_we_vote_id not in new_candidate_we_vote_ids_list:
                                new_candidate_we_vote_ids_list.append(candidate_we_vote_id)
                            if positive_value_exists(use_ctcl):
                                if positive_value_exists(candidate_ctcl_uuid):
                                    existing_candidate_objects_dict[candidate_ctcl_uuid] = candidate
                            elif positive_value_exists(use_vote_usa):
                                if positive_value_exists(candidate.photo_url_from_vote_usa):
                                    from import_export_vote_usa.controllers import \
                                        retrieve_and_store_vote_usa_candidate_photo
                                    results = retrieve_and_store_vote_usa_candidate_photo(candidate)
                                    if results['success']:
                                        candidate = results['candidate']
                                existing_candidate_objects_dict[vote_usa_politician_id] = candidate
                            else:
                                if positive_value_exists(candidate.photo_url):
                                    candidate_results = \
                                        candidate_manager.modify_candidate_with_organization_endorsements_image(
                                            candidate, photo_url, True)
                                    if candidate_results['success']:
                                        candidate = candidate_results['candidate']
                                existing_candidate_objects_dict[candidate_we_vote_id] = candidate
                else:
                    candidate_results = candidate_manager.update_or_create_candidate(
                        google_civic_election_id=google_civic_election_id,
                        ocd_division_id=office_ocd_division_id,
                        contest_office_id=contest_office_id,
                        contest_office_we_vote_id=contest_office_we_vote_id,
                        google_civic_candidate_name=google_civic_candidate_name,
                        updated_candidate_values=updated_candidate_values)
                    candidate_found = candidate_results['candidate_found']
                    if positive_value_exists(candidate_found):
                        candidate = candidate_results['candidate']
                        candidate_we_vote_id = candidate.we_vote_id
                    if positive_value_exists(use_ctcl):
                        existing_candidate_objects_dict[candidate_ctcl_uuid] = candidate
                    elif positive_value_exists(use_vote_usa):
                        existing_candidate_objects_dict[vote_usa_politician_id] = candidate

        if positive_value_exists(candidate_we_vote_id):
            # Now make sure we have a CandidateToOfficeLink
            results = is_there_existing_candidate_to_office_link(
                existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                contest_office_we_vote_id=contest_office_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
            )
            existing_candidate_to_office_links_dict = results['existing_candidate_to_office_links_dict']
            if not results['candidate_to_office_link_found']:
                link_results = candidate_manager.get_or_create_candidate_to_office_link(
                    candidate_we_vote_id=candidate_we_vote_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code)
                if positive_value_exists(link_results['success']):
                    results = update_existing_candidate_to_office_links_dict(
                        existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                        contest_office_we_vote_id=contest_office_we_vote_id,
                        candidate_we_vote_id=candidate_we_vote_id,
                    )
                    existing_candidate_to_office_links_dict = results['existing_candidate_to_office_links_dict']

    results = {
        'status':                           status,
        'success':                          success,
        'existing_candidate_objects_dict':  existing_candidate_objects_dict,
        'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
        'new_candidate_we_vote_ids_list':   new_candidate_we_vote_ids_list,
    }
    return results


def is_there_existing_candidate_to_office_link(
        existing_candidate_to_office_links_dict={},
        contest_office_we_vote_id='',
        candidate_we_vote_id=''):
    candidate_to_office_link_found = False
    if positive_value_exists(contest_office_we_vote_id) and positive_value_exists(candidate_we_vote_id):
        if contest_office_we_vote_id in existing_candidate_to_office_links_dict:
            if candidate_we_vote_id in existing_candidate_to_office_links_dict[contest_office_we_vote_id]:
                candidate_to_office_link_found = True
    results = {
        'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
        'candidate_to_office_link_found':   candidate_to_office_link_found,
    }
    return results


def update_existing_candidate_to_office_links_dict(
        existing_candidate_to_office_links_dict={},
        contest_office_we_vote_id='',
        candidate_we_vote_id=''):
    if positive_value_exists(contest_office_we_vote_id) and positive_value_exists(candidate_we_vote_id):
        if contest_office_we_vote_id not in existing_candidate_to_office_links_dict:
            existing_candidate_to_office_links_dict[contest_office_we_vote_id] = {}
        if candidate_we_vote_id not in existing_candidate_to_office_links_dict[contest_office_we_vote_id]:
            existing_candidate_to_office_links_dict[contest_office_we_vote_id][candidate_we_vote_id] = True
    results = {
        'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
    }
    return results


def process_contest_office_from_structured_json(
        one_contest_office_structured_json,
        google_civic_election_id,
        state_code,
        ocd_division_id,
        local_ballot_order,
        voter_id,
        polling_location_we_vote_id):

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

    if "/n" in office_name:
        # Sometimes a line break is passed in with the office_name
        office_name = office_name.replace("/n", " ")
        office_name = office_name.strip()
        one_contest_office_structured_json['office'] = office_name

    # The number of candidates that a voter may vote for in this contest.
    if 'numberVotingFor' in one_contest_office_structured_json:
        number_voting_for = one_contest_office_structured_json['numberVotingFor']
    else:
        number_voting_for = str(1)

    # The number of candidates that will be elected to office in this contest.
    if 'numberElected' in one_contest_office_structured_json:
        number_elected = one_contest_office_structured_json['numberElected']
    else:
        number_elected = str(1)

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
    # Note that all the information saved here is independent of a particular voter
    if google_civic_election_id and (district_id or district_name) and office_name:
        updated_contest_office_values = {
            'google_civic_election_id': google_civic_election_id,
        }
        if positive_value_exists(office_name) and office_name in OFFICE_NAMES_WITH_NO_STATE:
            updated_contest_office_values['state_code'] = 'NA'
        elif positive_value_exists(state_code):
            state_code_for_error_checking = state_code.lower()
            # Limit to 2 digits, so we don't exceed the database limit
            state_code_for_error_checking = state_code_for_error_checking[-2:]
            # Make sure we recognize the state
            list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                       state_code_for_error_checking in key.lower()]
            state_code_for_error_checking = list_of_states_matching.pop()
            updated_contest_office_values['state_code'] = state_code_for_error_checking
        if positive_value_exists(district_id):
            updated_contest_office_values['district_id'] = district_id
        if positive_value_exists(district_name):
            updated_contest_office_values['district_name'] = district_name
        if positive_value_exists(office_name):
            # Note: When we decide to start updating office_name elsewhere within We Vote, we should stop
            #  updating office_name via subsequent Google Civic imports
            updated_contest_office_values['office_name'] = office_name
            # We store the literal spelling here so we can match in the future, even if we customize measure_title
            updated_contest_office_values['google_civic_office_name'] = office_name
        if positive_value_exists(ocd_division_id):
            updated_contest_office_values['ocd_division_id'] = ocd_division_id
        if positive_value_exists(number_voting_for):
            updated_contest_office_values['number_voting_for'] = number_voting_for
        if positive_value_exists(number_elected):
            updated_contest_office_values['number_elected'] = number_elected
        if positive_value_exists(contest_level0):
            updated_contest_office_values['contest_level0'] = contest_level0
        if positive_value_exists(contest_level1):
            updated_contest_office_values['contest_level1'] = contest_level1
        if positive_value_exists(contest_level2):
            updated_contest_office_values['contest_level2'] = contest_level2
        if positive_value_exists(primary_party):
            updated_contest_office_values['primary_party'] = primary_party
        if positive_value_exists(district_scope):
            updated_contest_office_values['district_scope'] = district_scope
        if positive_value_exists(electorate_specifications):
            updated_contest_office_values['electorate_specifications'] = electorate_specifications
        if positive_value_exists(special):
            updated_contest_office_values['special'] = special
        if positive_value_exists(google_ballot_placement):
            updated_contest_office_values['google_ballot_placement'] = google_ballot_placement
        office_manager = ContestOfficeManager()
        # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
        # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
        # Presidential races don't have either district_id or district_name, so we can't require one.
        # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower" vs. "scope": "statewide"
        update_or_create_contest_office_results = office_manager.update_or_create_contest_office(
            office_we_vote_id=we_vote_id,
            maplight_id=maplight_id,
            google_civic_election_id=google_civic_election_id,
            office_name=office_name,
            district_id=district_id,
            updated_contest_office_values=updated_contest_office_values)
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
        measure_text = ""
        contest_measure_id = 0
        contest_measure_we_vote_id = ""
        ballot_item_manager.update_or_create_ballot_item_for_voter(
            voter_id, google_civic_election_id, google_ballot_placement,
            ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
            contest_office_id, contest_office_we_vote_id,
            contest_measure_id, contest_measure_we_vote_id, state_code)

    # If this is a map point, we want to save the ballot information for it so we can use it as reference
    #  for nearby voters (when we don't have their full address)
    if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id) \
            and positive_value_exists(contest_office_id):
        ballot_item_manager = BallotItemManager()
        measure_subtitle = ""
        measure_text = ""
        contest_measure_id = 0
        contest_measure_we_vote_id = ""
        ballot_item_manager.update_or_create_ballot_item_for_polling_location(
            polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
            ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
            contest_office_id, contest_office_we_vote_id,
            contest_measure_id, contest_measure_we_vote_id, state_code)

    # Note: We do not need to connect the candidates with the voter here for a ballot item  # TODO DALE Actually we do
    # For VT, They don't have a district id, so all candidates were lumped together.
    # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
    # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
    # Presidential races don't have either district_id or district_name, so we can't require one.
    # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower" vs. "scope": "statewide"
    candidates_results = process_candidates_from_structured_json(
        candidates_structured_json,
        google_civic_election_id,
        ocd_division_id,
        state_code,
        contest_office_id,
        contest_office_we_vote_id)

    return update_or_create_contest_office_results


def groom_and_store_google_civic_office_json_2021(
        one_contest_json={},
        google_civic_election_id='',
        election_day_text='',
        state_code='',
        election_year_integer=0,
        election_ocd_division_id='',
        local_ballot_order=0,
        voter_id=0,
        polling_location_we_vote_id='',
        ballot_item_dict_list=[],
        existing_offices_by_election_dict={},
        existing_candidate_objects_dict={},
        existing_candidate_to_office_links_dict={},
        new_office_we_vote_ids_list=[],
        new_candidate_we_vote_ids_list=[],
        use_ctcl=False,
        use_vote_usa=False,
        update_or_create_rules={}):
    status = ''
    success = True

    ballot_item_display_name = ''
    contest_office = None
    contest_office_id = 0
    contest_office_we_vote_id = ""
    office_name = ""
    google_civic_election_id_string = str(google_civic_election_id)

    office_data_exists = 'office' in one_contest_json and positive_value_exists(one_contest_json['office'])
    if not office_data_exists:
        # We need office to proceed, so without it, go to the next race
        results = {
            'success': False,
            'status': status,
            'saved': 0,
            'updated': 0,
            'not_processed': 1,
            'ballot_item_dict_list': ballot_item_dict_list,
            'existing_offices_by_election_dict': existing_offices_by_election_dict,
            'existing_candidate_objects_dict': existing_candidate_objects_dict,
            'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
            'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
        }
        return results

    ctcl_office_uuid = None
    vote_usa_office_id = None
    if positive_value_exists(use_ctcl):
        ctcl_office_uuid = one_contest_json['id']
    elif positive_value_exists(use_vote_usa):
        raw_vote_usa_office_id = one_contest_json['id']
        vote_usa_office_id = extract_vote_usa_office_id(raw_vote_usa_office_id)

    office_name = one_contest_json['office']

    if "/n" in office_name:
        # Sometimes a line break is passed in with the office_name
        office_name = office_name.replace("/n", " ")
        office_name = office_name.strip()
        one_contest_json['office'] = office_name

    # The number of candidates that a voter may vote for in this contest.
    if 'numberVotingFor' in one_contest_json:
        number_voting_for = one_contest_json['numberVotingFor']
    else:
        number_voting_for = str(1)

    # The number of candidates that will be elected to office in this contest.
    if 'numberElected' in one_contest_json:
        number_elected = one_contest_json['numberElected']
    else:
        number_elected = str(1)

    # These are several fields that are shared in common between offices and measures
    results = process_contest_common_fields_from_structured_json(one_contest_json, is_ctcl=use_ctcl)

    # ballot_placement: A number specifying the position of this contest on the voter's ballot.
    google_ballot_placement = results['ballot_placement']
    primary_party = results['primary_party']  # If this is a partisan election, the name of the party it is for.

    # district_scope: The geographic scope of this district. If unspecified the
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = results['district_scope']
    if office_name in OFFICE_NAMES_WITH_NO_STATE:
        ballotpedia_race_office_level = 'Federal'
    else:
        ballotpedia_race_office_level = convert_district_scope_to_ballotpedia_race_office_level(district_scope)
    office_ocd_division_id = results['contest_ocd_division_id']
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
    level_list = one_contest_json['level'] if 'level' in one_contest_json else []
    contest_level = []
    for one_level in level_list:
        contest_level.append(one_level)
    try:
        contest_level0 = contest_level[0]
    except IndexError:
        contest_level0 = None
    try:
        contest_level1 = contest_level[1]
    except IndexError:
        contest_level1 = None
    try:
        contest_level2 = contest_level[2]
    except IndexError:
        contest_level2 = None

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
    #     one_contest_json['roles'] if 'roles' in one_contest_json else ''
    # for one_role in roles_structured_json:
    # Figure out how we are going to use level info

    allowed_to_create_offices = \
        'create_offices' in update_or_create_rules and positive_value_exists(update_or_create_rules['create_offices'])
    allowed_to_update_offices = \
        'update_offices' in update_or_create_rules and positive_value_exists(update_or_create_rules['update_offices'])

    candidates_structured_json = one_contest_json['candidates'] if 'candidates' in one_contest_json else ''

    # Check to see if this is a new office or if we have any new data
    if google_civic_election_id_string not in existing_offices_by_election_dict:
        existing_offices_by_election_dict[google_civic_election_id_string] = {}

    continue_searching_for_office = True
    create_office_entry = False
    office_manager = ContestOfficeManager()
    if continue_searching_for_office and positive_value_exists(ctcl_office_uuid):
        if ctcl_office_uuid in existing_offices_by_election_dict[google_civic_election_id_string]:
            contest_office = \
                existing_offices_by_election_dict[google_civic_election_id_string][ctcl_office_uuid]
            ballot_item_display_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
            office_name = contest_office.office_name
            continue_searching_for_office = False
        else:
            office_results = office_manager.retrieve_contest_office(
                ctcl_uuid=ctcl_office_uuid,
                google_civic_election_id=google_civic_election_id,
                read_only=(not allowed_to_update_offices))
            if office_results['contest_office_found']:
                continue_searching_for_office = False
                contest_office = office_results['contest_office']
                ballot_item_display_name = contest_office.office_name
                contest_office_we_vote_id = contest_office.we_vote_id
                contest_office_id = contest_office.id
                office_name = contest_office.office_name
                existing_offices_by_election_dict[google_civic_election_id_string][ctcl_office_uuid] = contest_office
                # In the future, we will want to look for updated data to save
            elif office_results['MultipleObjectsReturned']:
                status += "MORE_THAN_ONE_OFFICE_WITH_SAME_CTCL_UUID_ID: " + str(ctcl_office_uuid) + " "
                continue_searching_for_office = False
            elif not office_results['success']:
                status += "RETRIEVE_BY_CTCL_UUID_FAILED: "
                status += office_results['status']
                results = {
                    'success': False,
                    'status': status,
                    'saved': 0,
                    'updated': 0,
                    'not_processed': 1,
                    'ballot_item_dict_list': ballot_item_dict_list,
                    'existing_offices_by_election_dict': existing_offices_by_election_dict,
                    'existing_candidate_objects_dict': existing_candidate_objects_dict,
                    'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                    'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                }
                return results
            else:
                continue_searching_for_office = True
    elif continue_searching_for_office and positive_value_exists(vote_usa_office_id):
        if vote_usa_office_id in existing_offices_by_election_dict[google_civic_election_id_string]:
            contest_office = \
                existing_offices_by_election_dict[google_civic_election_id_string][vote_usa_office_id]
            ballot_item_display_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
            office_name = contest_office.office_name
            continue_searching_for_office = False
        else:
            # Uncomment this if testing against specific offices
            # if positive_value_exists(vote_usa_office_id):
            #     strings_to_find = [
            #         'BoardOfSupervisors', 'CommissionerOfRevenue', 'CommonwealthSAttorney',
            #         'SchoolBoard',
            #     ]
            #     if vote_usa_office_id.endswith(tuple(strings_to_find)):
            #         # For debugging
            #         record_found = True
            office_results = office_manager.retrieve_contest_office(
                vote_usa_office_id=vote_usa_office_id,
                google_civic_election_id=google_civic_election_id,
                read_only=(not allowed_to_update_offices))
            if office_results['contest_office_found']:
                continue_searching_for_office = False
                contest_office = office_results['contest_office']
                ballot_item_display_name = contest_office.office_name
                contest_office_we_vote_id = contest_office.we_vote_id
                contest_office_id = contest_office.id
                office_name = contest_office.office_name
                existing_offices_by_election_dict[google_civic_election_id_string][vote_usa_office_id] = contest_office
                # In the future, we will want to look for updated data to save
            elif office_results['MultipleObjectsReturned']:
                status += "MORE_THAN_ONE_OFFICE_WITH_SAME_VOTE_USA_ID: " + str(vote_usa_office_id) + " "
                continue_searching_for_office = False
            elif not office_results['success']:
                status += "RETRIEVE_BY_VOTE_USA_FAILED: "
                status += office_results['status']
                results = {
                    'success': False,
                    'status': status,
                    'saved': 0,
                    'updated': 0,
                    'not_processed': 1,
                    'ballot_item_dict_list': ballot_item_dict_list,
                    'existing_offices_by_election_dict': existing_offices_by_election_dict,
                    'existing_candidate_objects_dict': existing_candidate_objects_dict,
                    'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                    'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
                }
                return results
            else:
                # If here, we have a Vote USA Office Id, but no office found.
                create_office_entry = True
                continue_searching_for_office = False

    if continue_searching_for_office:
        # Check to see if there is an office which doesn't match by data provider id
        office_list_manager = ContestOfficeListManager()
        read_only = not (allowed_to_create_offices or allowed_to_update_offices)  # In case we need to update source id
        results = office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
            contest_office_name=office_name,
            ctcl_uuid=ctcl_office_uuid,
            google_civic_election_id=google_civic_election_id,
            incoming_state_code=state_code,
            district_id=district_id,
            read_only=read_only,
            vote_usa_office_id=vote_usa_office_id)
        if not results['success']:
            continue_searching_for_office = False
            status += "FAILED_RETRIEVING_CONTEST_FROM_UNIQUE_IDS: " + results['status'] + " "
        elif results['multiple_entries_found']:
            continue_searching_for_office = False
            status += "RETRIEVING_CONTEST_FROM_UNIQUE_IDS-MULTIPLE_FOUND: " + results['status'] + " "
            create_office_entry = True
        elif results['contest_office_found']:
            continue_searching_for_office = False
            contest_office = results['contest_office']
            ballot_item_display_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
            office_name = contest_office.office_name
            if use_ctcl:
                if allowed_to_create_offices and not positive_value_exists(contest_office.ctcl_uuid):
                    contest_office.ctcl_uuid = ctcl_office_uuid
                    try:
                        contest_office.save()
                        if positive_value_exists(ctcl_office_uuid):
                            existing_offices_by_election_dict[google_civic_election_id_string][ctcl_office_uuid] = \
                                contest_office
                    except Exception as e:
                        status += "SAVING_CTCL_UUID_FAILED: " + str(e) + ' '
            elif use_vote_usa:
                if allowed_to_create_offices and not positive_value_exists(contest_office.vote_usa_office_id):
                    contest_office.vote_usa_office_id = vote_usa_office_id
                    try:
                        contest_office.save()
                        if positive_value_exists(vote_usa_office_id):
                            existing_offices_by_election_dict[google_civic_election_id_string][vote_usa_office_id] = \
                                contest_office
                    except Exception as e:
                        status += "SAVING_VOTE_USA_OFFICE_ID_FAILED: " + str(e) + ' '
        else:
            create_office_entry = True

    proceed_to_create_office = positive_value_exists(create_office_entry) and allowed_to_create_offices
    proceed_to_update_office = allowed_to_update_offices

    if proceed_to_create_office or proceed_to_update_office:
        # Note that all the information saved here is independent of a particular voter
        if google_civic_election_id and \
                (district_id or district_name or ctcl_office_uuid or vote_usa_office_id) and \
                office_name:
            updated_contest_office_values = {
                'google_civic_election_id': google_civic_election_id,
            }
            if positive_value_exists(state_code):
                state_code_for_error_checking = state_code.lower()
                # Limit to 2 digits so we don't exceed the database limit
                state_code_for_error_checking = state_code_for_error_checking[-2:]
                # Make sure we recognize the state
                list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                           state_code_for_error_checking in key.lower()]
                state_code_for_error_checking = list_of_states_matching.pop()
                updated_contest_office_values['state_code'] = state_code_for_error_checking

            if positive_value_exists(ballotpedia_race_office_level):
                updated_contest_office_values['ballotpedia_race_office_level'] = ballotpedia_race_office_level
            if positive_value_exists(district_id):
                updated_contest_office_values['district_id'] = district_id
            if positive_value_exists(office_ocd_division_id):
                updated_contest_office_values['ocd_division_id'] = office_ocd_division_id
            if positive_value_exists(district_name):
                updated_contest_office_values['district_name'] = district_name
            if positive_value_exists(office_name):
                # Note: When we decide to start updating office_name elsewhere within We Vote, we should stop
                #  updating office_name via subsequent Google Civic imports
                updated_contest_office_values['office_name'] = office_name
                # We store the literal spelling here so we can match in the future, even if we customize measure_title
                updated_contest_office_values['google_civic_office_name'] = office_name
            if positive_value_exists(number_voting_for):
                updated_contest_office_values['number_voting_for'] = number_voting_for
            if positive_value_exists(number_elected):
                updated_contest_office_values['number_elected'] = number_elected
            if positive_value_exists(contest_level0):
                updated_contest_office_values['contest_level0'] = contest_level0
            if positive_value_exists(contest_level1):
                updated_contest_office_values['contest_level1'] = contest_level1
            if positive_value_exists(contest_level2):
                updated_contest_office_values['contest_level2'] = contest_level2
            if positive_value_exists(primary_party):
                updated_contest_office_values['primary_party'] = primary_party
            if positive_value_exists(district_scope):
                updated_contest_office_values['district_scope'] = district_scope
            if positive_value_exists(electorate_specifications):
                updated_contest_office_values['electorate_specifications'] = electorate_specifications
            if positive_value_exists(special):
                updated_contest_office_values['special'] = special
            if positive_value_exists(google_ballot_placement):
                updated_contest_office_values['google_ballot_placement'] = google_ballot_placement
            if positive_value_exists(ctcl_office_uuid):
                updated_contest_office_values['ctcl_uuid'] = ctcl_office_uuid
            if positive_value_exists(vote_usa_office_id):
                updated_contest_office_values['vote_usa_office_id'] = vote_usa_office_id

            if positive_value_exists(proceed_to_create_office):
                update_or_create_contest_office_results = office_manager.create_contest_office_row_entry(
                    contest_office_name=office_name,
                    contest_office_votes_allowed=number_voting_for,
                    contest_office_number_elected=number_elected,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    defaults=updated_contest_office_values)
            else:
                update_or_create_contest_office_results = office_manager.update_or_create_contest_office(
                    office_we_vote_id=contest_office_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    office_name=office_name,
                    district_id=district_id,
                    updated_contest_office_values=updated_contest_office_values)

            if update_or_create_contest_office_results['success']:
                if positive_value_exists(update_or_create_contest_office_results['contest_office_found']):
                    contest_office = update_or_create_contest_office_results['contest_office']
                    ballot_item_display_name = contest_office.office_name
                    contest_office_id = contest_office.id
                    contest_office_we_vote_id = contest_office.we_vote_id
                    new_office_created = True
                    if contest_office_we_vote_id not in new_office_we_vote_ids_list:
                        new_office_we_vote_ids_list.append(contest_office_we_vote_id)

                    if positive_value_exists(ctcl_office_uuid):
                        existing_offices_by_election_dict[google_civic_election_id_string][ctcl_office_uuid] = \
                            contest_office
                    elif positive_value_exists(vote_usa_office_id):
                        existing_offices_by_election_dict[google_civic_election_id_string][vote_usa_office_id] = \
                            contest_office
            else:
                ballot_item_display_name = ''
                contest_office_id = 0
                contest_office_we_vote_id = ''
                success = False
                status += update_or_create_contest_office_results['status']
        else:
            results = {
                'success': False,
                'status': status,
                'saved': 0,
                'updated': 0,
                'not_processed': 1,
                'ballot_item_dict_list': ballot_item_dict_list,
                'existing_offices_by_election_dict': existing_offices_by_election_dict,
                'existing_candidate_objects_dict': existing_candidate_objects_dict,
                'new_candidate_we_vote_ids_list': new_candidate_we_vote_ids_list,
                'new_office_we_vote_ids_list': new_office_we_vote_ids_list,
            }
            return results
    else:
        if hasattr(contest_office, 'office_name'):
            ballot_item_display_name = contest_office.office_name
        if hasattr(contest_office, 'id'):
            contest_office_id = contest_office.id
        if hasattr(contest_office, 'we_vote_id'):
            contest_office_we_vote_id = contest_office.we_vote_id

    if positive_value_exists(contest_office_we_vote_id):
        office_json = {
            'ballot_item_display_name':     ballot_item_display_name,
            'contest_office_id':            contest_office_id,
            'contest_office_name':          ballot_item_display_name,
            'contest_office_we_vote_id':    contest_office_we_vote_id,
            'election_day_text':            election_day_text,
            'local_ballot_order':           local_ballot_order,
            'polling_location_we_vote_id':  polling_location_we_vote_id,
            'state_code':                   state_code,
            'voter_id':                     voter_id,
        }
        ballot_item_dict_list.append(office_json)

    if positive_value_exists(contest_office_we_vote_id):
        try:
            candidates_results = groom_and_store_google_civic_candidates_json_2021(
                candidates_structured_json=candidates_structured_json,
                google_civic_election_id=google_civic_election_id,
                office_ocd_division_id=office_ocd_division_id,
                state_code=state_code,
                contest_office_id=contest_office_id,
                contest_office_we_vote_id=contest_office_we_vote_id,
                contest_office_name=office_name,
                election_year_integer=election_year_integer,
                existing_candidate_objects_dict=existing_candidate_objects_dict,
                existing_candidate_to_office_links_dict=existing_candidate_to_office_links_dict,
                new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
                update_or_create_rules=update_or_create_rules,
                use_ctcl=use_ctcl,
                use_vote_usa=use_vote_usa,
                vote_usa_office_id=vote_usa_office_id)
            existing_candidate_objects_dict = candidates_results['existing_candidate_objects_dict']
            existing_candidate_to_office_links_dict = candidates_results['existing_candidate_to_office_links_dict']
            new_candidate_we_vote_ids_list = candidates_results['new_candidate_we_vote_ids_list']
        except Exception as e:
            status += "COULD_NOT_STORE_CANDIDATES: " + str(e) + " "
            pass
    results = {
        'success':                          success,
        'status':                           status,
        'ballot_item_dict_list':            ballot_item_dict_list,
        'existing_offices_by_election_dict': existing_offices_by_election_dict,
        'existing_candidate_objects_dict':  existing_candidate_objects_dict,
        'existing_candidate_to_office_links_dict':  existing_candidate_to_office_links_dict,
        'new_candidate_we_vote_ids_list':   new_candidate_we_vote_ids_list,
        'new_office_we_vote_ids_list':      new_office_we_vote_ids_list,
    }
    return results


def extract_value_from_array(structured_json, index_key, default_value):
    if index_key in structured_json:
        return structured_json[index_key]
    else:
        return default_value


def process_contest_common_fields_from_structured_json(one_contest_structured_json, is_ctcl=False):
    # These following fields exist for both candidates and referendum

    # ballot_placement is a number specifying the position of this contest on the voter's ballot.
    # primary_party: If this is a partisan election, the name of the party it is for.
    results = {
        'ballot_placement': extract_value_from_array(one_contest_structured_json, 'ballotPlacement', 0),
        'primary_party': extract_value_from_array(one_contest_structured_json, 'primaryParty', '')
    }

    # https://developers.google.com/civic-information/docs/v2/elections/voterInfoQuery
    district_dict = one_contest_structured_json['district'] if 'district' in one_contest_structured_json else {}

    # contests[].district.name
    # The name of the district.
    results['district_name'] = district_dict['name'] if 'name' in district_dict else ''
    # contests[].district.scope
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    results['district_scope'] = district_dict['scope'] if 'scope' in district_dict else ''
    # contests[].district.id
    # A string identifier for this district, relative to its scope. For example, the 34th State Senate district
    #  would have id "34" and a scope of stateUpper.
    results['district_id'] = district_dict['id'] if 'id' in district_dict else ''
    # Added on by CTCL (not part of spec)
    results['contest_ocd_division_id'] = district_dict['ocdid'] if 'ocdid' in district_dict else ''
    if is_ctcl:
        # 2021-10-22 CTCL has a bug where they are passing in 'ocd-division/country:us/state:va/sldl:59'
        #  as the district.id instead of just the number
        # For an OCD ID, the district integer is added to the end. For example,
        # Virginia's 8th congressional district 8 looks like this:
        # ocd-division/country:us/state:va/cd:8
        if 'contest_ocd_division_id' in results:
            results['district_id'] = extract_district_id_from_ocd_division_id(results['contest_ocd_division_id'])
            # I think results['district'] is not correct and should be replaced
            #  with name like 'contest_ocd_district_id_label'
            results['district'] = \
                extract_district_id_label_when_district_id_exists_from_ocd_id(results['contest_ocd_division_id']) \
                if 'contest_ocd_division_id' in results else ''

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
        local_ballot_order += 1  # Needed if ballotPlacement isn't provided by Google Civic. Related to ballot_placement
        contest_type = one_contest['type']

        # Is the contest is a referendum/initiative/measure?
        if contest_type.lower() == 'referendum' or 'referendumTitle' in one_contest:  # Referendum
            process_contest_results = process_contest_referendum_from_structured_json(
                one_contest, google_civic_election_id, state_code, ocd_division_id, local_ballot_order, voter_id,
                polling_location_we_vote_id)
            if process_contest_results['saved']:
                contests_saved += 1
            elif process_contest_results['updated']:
                contests_updated += 1
            elif process_contest_results['not_processed']:
                contests_not_processed += 1
        # All other contests are for a contest office
        else:
            process_contest_results = process_contest_office_from_structured_json(
                one_contest, google_civic_election_id, state_code, ocd_division_id, local_ballot_order, voter_id,
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
    print("retrieving one ballot for " + str(incoming_google_civic_election_id) + ": " + str(text_for_map_search))
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
    if 'success' in structured_json and structured_json['success'] is False:
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
    election_administration_data_retrieved = False
    google_civic_election_id = 0
    google_response_address_not_found = False
    error = structured_json.get('error', {})
    errors = error.get('errors', {})
    if len(errors):
        logger.debug("retrieve_one_ballot_from_google_civic_api failed: " + str(errors))
        for one_error_from_google in errors:
            if 'reason' in one_error_from_google:
                if one_error_from_google['reason'] == "notFound":
                    # Ballot data not found at this location
                    google_response_address_not_found = True
                if one_error_from_google['reason'] == "parseError":
                    # Not an address format Google can parse
                    google_response_address_not_found = True

    if 'election' in structured_json:
        if 'id' in structured_json['election']:
            election_data_retrieved = True
            success = True
            google_civic_election_id = structured_json['election']['id']

    #  We can get a google_civic_election_id back even though we don't have contest data.
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

    if 'state' in structured_json:
        if len(structured_json['state']) > 0:
            if 'electionAdministrationBody' in structured_json['state'][0]:
                election_administration_data_retrieved = True
                success = True

    results = {
        'success': success,
        'election_data_retrieved': election_data_retrieved,
        'polling_location_retrieved': polling_location_retrieved,
        'google_response_address_not_found': google_response_address_not_found,
        'contests_retrieved': contests_retrieved,
        'election_administration_data_retrieved': election_administration_data_retrieved,
        'structured_json': structured_json,
    }
    return results


# See import_data/voterInfoQuery_VA_sample.json
def store_one_ballot_from_google_civic_api(one_ballot_json, voter_id=0, polling_location_we_vote_id='',
                                           ballot_returned=None):
    """
    When we pass in a voter_id, we want to save this ballot related to the voter.
    When we pass in polling_location_we_vote_id, we want to save a ballot for that area, which is useful for
    getting new voters started by showing them a ballot roughly near them.
    See updated version using the import_export_batch system in:
    import_export_google_civic/controllers.py groom_and_store_google_civic_ballot_json_2021
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

    election_day_text = ''
    election_description_text = ''
    if 'electionDay' in one_ballot_json['election']:
        election_day_text = one_ballot_json['election']['electionDay']
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
    # We don't store the normalized address information when we capture a ballot for a map point

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
        results = {
            'status':                   status,
            'success':                  success,
            'ballot_returned_found':    False,
            'ballot_returned':          ballot_returned,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    # When saving a ballot for individual voter, loop through all pollingLocations and store in local db
    # process_polling_locations_from_structured_json(one_ballot_json['pollingLocations'])

    # If we successfully save a ballot, create/update a BallotReturned entry
    ballot_returned_found = False
    if hasattr(ballot_returned, 'voter_id') and positive_value_exists(ballot_returned.voter_id):
        ballot_returned_found = True
    elif hasattr(ballot_returned, 'polling_location_we_vote_id') \
            and positive_value_exists(ballot_returned.polling_location_we_vote_id):
        ballot_returned_found = True
    else:
        ballot_returned = BallotReturned()

    is_test_election = True if positive_value_exists(google_civic_election_id) \
        and convert_to_int(google_civic_election_id) == 2000 else False

    # If this is connected to a polling_location, retrieve the polling_location_information
    ballot_returned_manager = BallotReturnedManager()
    polling_location_manager = PollingLocationManager()

    if not is_test_election:
        if not ballot_returned_found:
            # If ballot_returned wasn't passed into this function, retrieve it
            if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                results = ballot_returned_manager.retrieve_ballot_returned_from_voter_id(
                    voter_id, google_civic_election_id)
                if results['ballot_returned_found']:
                    ballot_returned_found = True
                    ballot_returned = results['ballot_returned']
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                results = ballot_returned_manager.retrieve_ballot_returned_from_polling_location_we_vote_id(
                    polling_location_we_vote_id, google_civic_election_id)
                if results['ballot_returned_found']:
                    ballot_returned_found = True  # If the update fails, return the original ballot_returned object
                    ballot_returned = results['ballot_returned']

        # Now update ballot_returned with latest values
        if positive_value_exists(ballot_returned_found):
            if positive_value_exists(voter_address_dict):
                update_results = ballot_returned_manager.update_ballot_returned_with_normalized_values(
                        voter_address_dict, ballot_returned)
                ballot_returned = update_results['ballot_returned']
        else:
            create_results = ballot_returned_manager.create_ballot_returned_with_normalized_values(
                voter_address_dict,
                election_day_text, election_description_text,
                google_civic_election_id, voter_id, polling_location_we_vote_id
            )
            ballot_returned_found = create_results['ballot_returned_found']
            ballot_returned = create_results['ballot_returned']

        # Currently we don't report the success or failure of storing ballot_returned

    if positive_value_exists(ballot_returned_found):
        if positive_value_exists(polling_location_we_vote_id):
            results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
            if results['polling_location_found']:
                polling_location = results['polling_location']
                ballot_returned.latitude = polling_location.latitude
                ballot_returned.longitude = polling_location.longitude
                ballot_returned.save()

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
    if 'success' in structured_json and structured_json['success'] is False:
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
        election_day_text = one_election['electionDay']
        google_civic_election_id = one_election['id']
        election_name = one_election['name']

        election_manager = ElectionManager()
        results = election_manager.update_or_create_election(
            google_civic_election_id, election_name, election_day_text, raw_ocd_division_id,
            election_name_do_not_override=True)

    return results


def refresh_voter_ballot_items_from_google_civic_from_voter_ballot_saved(voter_ballot_saved):
    """
    We are telling the server to explicitly reach out to the Google Civic API and retrieve the ballot items
    for this VoterBallotSaved entry.
    """
    # Confirm that we have a Google Civic API Key (GOOGLE_CIVIC_API_KEY)
    if not positive_value_exists(GOOGLE_CIVIC_API_KEY):
        results = {
            'status':                       'NO_GOOGLE_CIVIC_API_KEY ',
            'success':                      False,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    # Confirm that we have the URL where we retrieve voter ballots (VOTER_INFO_URL)
    if not positive_value_exists(VOTER_INFO_URL):
        results = {
            'status':                       'MISSING VOTER_INFO_URL in config/environment_variables.json ',
            'success':                      False,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    if not positive_value_exists(voter_ballot_saved.voter_id):
        results = {
            'status':                       "VALID_VOTER_ID_MISSING ",
            'success':                      False,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    ballot_returned_manager = BallotReturnedManager()
    results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(
        voter_ballot_saved.ballot_returned_we_vote_id)
    if not results['ballot_returned_found']:
        results = {
            'status':                       "BALLOT_RETURNED_NOT_FOUND ",
            'success':                      False,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    ballot_returned = results['ballot_returned']

    status = ''
    success = True
    election_day_text = ''
    election_description_text = ''
    election_data_retrieved = False
    polling_location_retrieved = False
    ballot_location_display_name = ''
    ballot_location_shortcut = ''
    ballot_returned_we_vote_id = ''
    contests_retrieved = False
    state_code = ''
    if not positive_value_exists(ballot_returned.text_for_map_search) \
            or not positive_value_exists(ballot_returned.google_civic_election_id):
        results = {
            'status':                       "BALLOT_RETURNED_TEXT_FOR_MAP_SEARCH_OR_ELECTION_ID_NOT_FOUND ",
            'success':                      False,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              ballot_returned,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    google_civic_election_id = 0
    if positive_value_exists(ballot_returned.text_for_map_search):
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(
            ballot_returned.text_for_map_search, ballot_returned.google_civic_election_id)

        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']

            google_civic_election_id_received = one_ballot_json['election']['id']
            google_civic_election_id_received = convert_to_int(google_civic_election_id_received)
            if google_civic_election_id_received != ballot_returned.google_civic_election_id:
                results = {
                    'status': "BALLOT_RETURNED_ELECTION_IDS_DO_NOT_MATCH ",
                    'success': False,
                    'google_civic_election_id': 0,
                    'state_code': "",
                    'election_day_text': "",
                    'election_description_text': "",
                    'election_data_retrieved': False,
                    'polling_location_retrieved': False,
                    'contests_retrieved': False,
                    'ballot_location_display_name': "",
                    'ballot_location_shortcut': "",
                    'ballot_returned': ballot_returned,
                    'ballot_returned_we_vote_id': "",
                }
                return results

            election_day_text = one_ballot_json['election']['electionDay']
            election_description_text = one_ballot_json['election']['name']

            # We may receive some election data, but not all the data we need
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
                # We include a google_civic_election_id, so only the ballot info for this election is removed
                google_civic_election_id_to_delete = ballot_returned.google_civic_election_id
                if positive_value_exists(google_civic_election_id_to_delete) \
                        and positive_value_exists(voter_ballot_saved.voter_id):
                    # Remove all prior ballot items, so we make room for store_one_ballot_from_google_civic_api to save
                    #  ballot items
                    voter_ballot_saved_manager = VoterBallotSavedManager()
                    ballot_item_list_manager = BallotItemListManager()

                    # I don't think we want to delete voter_ballot_saved
                    # voter_ballot_saved_id = 0
                    # voter_ballot_saved_results = voter_ballot_saved_manager.delete_voter_ballot_saved(
                    #     voter_ballot_saved_id, voter_ballot_saved.voter_id, google_civic_election_id_to_delete)

                    ballot_item_list_manager.delete_all_ballot_items_for_voter(
                        voter_ballot_saved.voter_id, google_civic_election_id_to_delete)

                # store_on_ballot... adds an entry to the BallotReturned table
                # We update VoterAddress with normalized address data in store_one_ballot_from_google_civic_api
                store_one_ballot_results = store_one_ballot_from_google_civic_api(
                    one_ballot_json, voter_ballot_saved.voter_id, ballot_returned=ballot_returned)
                if store_one_ballot_results['success']:
                    status += 'RETRIEVED_FROM_GOOGLE_CIVIC_AND_STORED_BALLOT_FOR_VOTER2 '
                    success = True
                    google_civic_election_id = store_one_ballot_results['google_civic_election_id']
                    if store_one_ballot_results['ballot_returned_found']:
                        ballot_returned = store_one_ballot_results['ballot_returned']
                        ballot_location_display_name = ballot_returned.ballot_location_display_name
                        ballot_location_shortcut = ballot_returned.ballot_location_shortcut
                        ballot_returned_we_vote_id = ballot_returned.we_vote_id
                else:
                    status += 'UNABLE_TO-store_one_ballot_from_google_civic_api '
        elif 'error' in one_ballot_results['structured_json']:
            if one_ballot_results['structured_json']['error']['message'] == 'Election unknown':
                success = False  # It is only successful if new ballot data is retrieved.
            else:
                success = False
            status += "GOOGLE_CIVIC_API_ERROR: " + one_ballot_results['structured_json']['error']['message'] + " "

        else:
            status += 'UNABLE_TO-retrieve_one_ballot_from_google_civic_api'
            success = False
    else:
        status += 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH'
        success = False

    # If a google_civic_election_id was not returned, outside of this function we search again using a test election,
    # so that during our initial user testing, ballot data is returned in areas where elections don't currently exist

    results = {
        'success':                      success,
        'status':                       status,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'election_day_text':            election_day_text,
        'election_description_text':    election_description_text,
        'election_data_retrieved':      election_data_retrieved,
        'polling_location_retrieved':   polling_location_retrieved,
        'contests_retrieved':           contests_retrieved,
        'ballot_location_display_name': ballot_location_display_name,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned':              ballot_returned,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
    }
    return results


def store_ballot_item_dict_list(
        ballot_item_dict_list=[],
        google_civic_election_id=0,
        voter_id=0,
        polling_location_we_vote_id='',
        state_code=''):
    """
    When we pass in a voter_id, we want to save these ballot_items related to the voter.
    When we pass in polling_location_we_vote_id, we want to save the ballot_items for that area, which is useful for
    getting new voters started by showing them a ballot roughly near them.
    """
    status = ""
    success = True

    if not positive_value_exists(google_civic_election_id):
        results = {
            'status': 'BALLOT_ITEM_DICT_LIST_MISSING_ELECTION_ID ',
            'success': False,
            'google_civic_election_id': 0,
        }
        return results

    # Check to see if there is a state served for the election
    if not positive_value_exists(state_code):
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            state_code = election.state_code

    # Similar to import_export_batches.controllers, import_ballot_item_data_from_batch_row_actions
    ballot_item_manager = BallotItemManager()
    office_manager = ContestOfficeManager()
    measure_manager = ContestMeasureManager()
    google_ballot_placement = None
    number_of_ballot_items_updated = 0
    measure_subtitle = ""
    measure_text = ""
    for one_ballot_item_dict in ballot_item_dict_list:
        contest_office_we_vote_id = one_ballot_item_dict['contest_office_we_vote_id'] \
            if 'contest_office_we_vote_id' in one_ballot_item_dict else None
        contest_office_id = one_ballot_item_dict['contest_office_id'] \
            if 'contest_office_id' in one_ballot_item_dict else None
        contest_measure_we_vote_id = one_ballot_item_dict['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_ballot_item_dict else None
        contest_measure_id = one_ballot_item_dict['contest_measure_id'] \
            if 'contest_measure_id' in one_ballot_item_dict else None

        if 'contest_office_name' in one_ballot_item_dict:
            ballot_item_display_name = one_ballot_item_dict['contest_office_name']
        elif 'contest_measure_name' in one_ballot_item_dict:
            ballot_item_display_name = one_ballot_item_dict['contest_measure_name']
        else:
            ballot_item_display_name = None

        local_ballot_order = one_ballot_item_dict['local_ballot_order'] \
            if 'local_ballot_order' in one_ballot_item_dict else ""

        # Make sure we have both ids for office
        if positive_value_exists(contest_office_we_vote_id) \
                and not positive_value_exists(contest_office_id):
            contest_office_id = office_manager.fetch_contest_office_id_from_we_vote_id(contest_office_we_vote_id)
        elif positive_value_exists(contest_office_id) \
                and not positive_value_exists(contest_office_we_vote_id):
            contest_office_we_vote_id = office_manager.fetch_contest_office_we_vote_id_from_id(contest_office_id)
        # Make sure we have both ids for measure
        if positive_value_exists(contest_measure_we_vote_id) \
                and not positive_value_exists(contest_measure_id):
            contest_measure_id = measure_manager.fetch_contest_measure_id_from_we_vote_id(contest_measure_we_vote_id)
        elif positive_value_exists(contest_measure_id) \
                and not positive_value_exists(contest_measure_we_vote_id):
            contest_measure_we_vote_id = measure_manager.fetch_contest_measure_we_vote_id_from_id(contest_measure_id)

        # Update or create
        if positive_value_exists(ballot_item_display_name) and positive_value_exists(state_code) \
                and positive_value_exists(google_civic_election_id):
            defaults = {}
            defaults['measure_url'] = one_ballot_item_dict['ballotpedia_measure_url'] \
                if 'ballotpedia_measure_url' in one_ballot_item_dict else ''
            defaults['yes_vote_description'] = one_ballot_item_dict['yes_vote_description'] \
                if 'yes_vote_description' in one_ballot_item_dict else ''
            defaults['no_vote_description'] = one_ballot_item_dict['no_vote_description'] \
                if 'no_vote_description' in one_ballot_item_dict else ''

            if positive_value_exists(voter_id):
                results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    google_ballot_placement=google_ballot_placement,
                    ballot_item_display_name=ballot_item_display_name,
                    measure_subtitle=measure_subtitle,
                    measure_text=measure_text,
                    local_ballot_order=local_ballot_order,
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    state_code=state_code,
                    defaults=defaults)
                if results['ballot_item_found']:
                    number_of_ballot_items_updated += 1
                else:
                    status += results['status'] + " "
                    status += "UPDATE_OR_CREATE_BALLOT_ITEM_UNSUCCESSFUL "
            elif positive_value_exists(polling_location_we_vote_id):
                results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                    polling_location_we_vote_id,
                    google_civic_election_id,
                    google_ballot_placement,
                    ballot_item_display_name,
                    measure_subtitle,
                    measure_text,
                    local_ballot_order,
                    contest_office_id,
                    contest_office_we_vote_id,
                    contest_measure_id,
                    contest_measure_we_vote_id,
                    state_code,
                    defaults)
                if results['ballot_item_found']:
                    number_of_ballot_items_updated += 1
        else:
            status += "MISSING-BALLOT_ITEM_DISPLAY_NAME-OR-NORMALIZED_STATE-OR-ELECTION_ID "
            status += "DISPLAY_NAME:" + str(ballot_item_display_name) + " "
            status += "STATE:" + str(state_code) + " "

    results = {
        'status':                   status,
        'success':                  success,
    }
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
            'status':                       'NO_GOOGLE_CIVIC_API_KEY ',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    # Confirm that we have the URL where we retrieve voter ballots (VOTER_INFO_URL)
    if not positive_value_exists(VOTER_INFO_URL):
        results = {
            'status':                       'MISSING VOTER_INFO_URL in config/environment_variables.json ',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    # Get voter_id from the voter_device_id so we can figure out which ballot_items to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'status':                       'VALID_VOTER_DEVICE_ID_MISSING ',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        results = {
            'status':                       "VALID_VOTER_ID_MISSING ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     0,
            'state_code':                   "",
            'election_day_text':           "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'polling_location_retrieved':   False,
            'contests_retrieved':           False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    status = ''
    success = True
    election_day_text = ''
    election_description_text = ''
    election_data_retrieved = False
    polling_location_retrieved = False
    ballot_location_display_name = ''
    ballot_location_shortcut = ''
    ballot_returned = None
    ballot_returned_we_vote_id = ''
    original_text_city = ''
    original_text_state = ''
    original_text_zip = ''
    contests_retrieved = False
    state_code = ''
    if not positive_value_exists(text_for_map_search):
        # Retrieve it from voter address
        voter_address_manager = VoterAddressManager()
        text_for_map_search = voter_address_manager.retrieve_ballot_map_text_from_voter_id(voter_id)
        results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
        if results['voter_address_found']:
            voter_address = results['voter_address']
            original_text_city = voter_address.normalized_city
            original_text_state = voter_address.normalized_state
            original_text_zip = voter_address.normalized_zip

    google_civic_election_id = 0
    if positive_value_exists(text_for_map_search):
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(
            text_for_map_search, google_civic_election_id, use_test_election)

        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']
            election_day_text = one_ballot_json['election']['electionDay']
            election_description_text = one_ballot_json['election']['name']

            # We may receive some election data, but not all the data we need
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
                # We include a google_civic_election_id, so only the ballot info for this election is removed
                google_civic_election_id_to_delete = one_ballot_json['election']['id']  # '0' would mean "delete all"
                if positive_value_exists(google_civic_election_id_to_delete) and positive_value_exists(voter_id):
                    # Remove all prior ballot items, so we make room for store_one_ballot_from_google_civic_api to save
                    #  ballot items
                    voter_ballot_saved_manager = VoterBallotSavedManager()
                    ballot_item_list_manager = BallotItemListManager()

                    voter_ballot_saved_id = 0
                    voter_ballot_saved_results = voter_ballot_saved_manager.delete_voter_ballot_saved(
                        voter_ballot_saved_id, voter_id, google_civic_election_id_to_delete)

                    ballot_item_list_manager.delete_all_ballot_items_for_voter(
                        voter_id, google_civic_election_id_to_delete)

                # store_on_ballot... adds an entry to the BallotReturned table
                # We update VoterAddress with normalized address data in store_one_ballot_from_google_civic_api
                store_one_ballot_results = store_one_ballot_from_google_civic_api(one_ballot_json, voter_id)
                if store_one_ballot_results['success']:
                    status += 'RETRIEVED_FROM_GOOGLE_CIVIC_AND_STORED_BALLOT_FOR_VOTER '
                    success = True
                    google_civic_election_id = store_one_ballot_results['google_civic_election_id']
                    if store_one_ballot_results['ballot_returned_found']:
                        ballot_returned = store_one_ballot_results['ballot_returned']
                        ballot_location_display_name = ballot_returned.ballot_location_display_name
                        ballot_location_shortcut = ballot_returned.ballot_location_shortcut
                        ballot_returned_we_vote_id = ballot_returned.we_vote_id
                else:
                    status += 'UNABLE_TO-store_one_ballot_from_google_civic_api '
        elif 'error' in one_ballot_results['structured_json']:
            if one_ballot_results['structured_json']['error']['message'] == 'Election unknown':
                success = False  # It is only successful if new ballot data is retrieved.
            else:
                success = False
            status += "GOOGLE_CIVIC_API_ERROR: " + one_ballot_results['structured_json']['error']['message'] + " "

        else:
            status += 'UNABLE_TO-retrieve_one_ballot_from_google_civic_api'
            success = False
    else:
        status += 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH'
        success = False

    # If a google_civic_election_id was not returned, outside of this function we search again using a test election,
    # so that during our initial user testing, ballot data is returned in areas where elections don't currently exist

    results = {
        'success':                      success,
        'status':                       status,
        'voter_device_id':              voter_device_id,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,  # Note, this isn't an actual state_code yet - TODO: populate
        'election_day_text':            election_day_text,
        'election_description_text':    election_description_text,
        'election_data_retrieved':      election_data_retrieved,
        'text_for_map_search':          text_for_map_search,
        'original_text_city':           original_text_city,
        'original_text_state':          original_text_state,
        'original_text_zip':            original_text_zip,
        'polling_location_retrieved':   polling_location_retrieved,
        'contests_retrieved':           contests_retrieved,
        'ballot_location_display_name': ballot_location_display_name,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned':              ballot_returned,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
    }
    return results


def voter_ballot_items_retrieve_from_google_civic_2021(
        voter_device_id,
        text_for_map_search='',
        google_civic_election_id='',
        use_ctcl=False,
        use_vote_usa=False):
    """
    We are telling the server to explicitly reach out and retrieve the ballot items for this voter.
    """

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        results = {
            'status':                       "VOTER_BALLOT_ITEMS_FROM_GOOGLE_CIVIC-VALID_VOTER_ID_MISSING ",
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   "",
            'election_day_text':            "",
            'election_description_text':    "",
            'election_data_retrieved':      False,
            'text_for_map_search':          text_for_map_search,
            'original_text_city':           '',
            'original_text_state':          '',
            'original_text_zip':            '',
            'polling_location_retrieved':   False,
            'ballot_location_display_name': "",
            'ballot_location_shortcut':     "",
            'ballot_returned':              None,
            'ballot_returned_found':        False,
            'ballot_returned_we_vote_id':   "",
        }
        return results

    status = ''
    success = True
    election_day_text = ''
    election_description_text = ''
    election_data_retrieved = False
    polling_location_retrieved = False
    ballot_location_display_name = ''
    ballot_location_shortcut = ''
    ballot_returned = None
    ballot_returned_we_vote_id = ''
    ballot_returned_found = False
    latitude = 0.0
    longitude = 0.0
    original_text_city = ''
    original_text_state = ''
    original_text_zip = ''
    lat_long_found = False
    status += "ENTERING-voter_ballot_items_retrieve_from_google_civic_2021, text_for_map_search: " \
              "" + str(text_for_map_search) + " "
    if not positive_value_exists(text_for_map_search):
        # Retrieve it from voter address
        voter_address_manager = VoterAddressManager()
        text_for_map_search = voter_address_manager.retrieve_ballot_map_text_from_voter_id(voter_id)
        results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
        if results['voter_address_found']:
            voter_address = results['voter_address']
            original_text_city = voter_address.normalized_city
            original_text_state = voter_address.normalized_state
            original_text_zip = voter_address.normalized_zip

    election_manager = ElectionManager()
    ctcl_election_uuid = ''
    state_code = extract_state_code_from_address_string(text_for_map_search)
    status += "[STATE_CODE: " + str(state_code) + "] "
    if positive_value_exists(state_code):
        original_text_state = state_code
        status += "[ORIGINAL_TEXT_STATE: " + str(original_text_state) + "] "
    if positive_value_exists(google_civic_election_id):
        election_results = election_manager.retrieve_election(google_civic_election_id)
        if election_results['election_found']:
            election_data_retrieved = True
            election = election_results['election']
            ctcl_election_uuid = election.ctcl_uuid
            google_civic_election_id = election.google_civic_election_id
            election_day_text = election.election_day_text
            election_description_text = election.election_name

        status += "ELECTION_BY_GOOGLE_CIVIC_ELECTION_ID: " + str(google_civic_election_id) + " "
    else:
        # We need to figure out next upcoming election for this person based on the state_code in text_for_map_search
        if positive_value_exists(state_code):
            election_results = election_manager.retrieve_next_election_for_state(
                state_code, require_include_in_list_for_voters=True)
            if election_results['election_found']:
                election_data_retrieved = True
                election = election_results['election']
                ctcl_election_uuid = election.ctcl_uuid
                google_civic_election_id = election.google_civic_election_id
                election_day_text = election.election_day_text
                election_description_text = election.election_name
                status += "NEXT_ELECTION_FOUND_FOR_STATE: " + str(google_civic_election_id) + " "
            else:
                status += "NEXT_ELECTION_NOT_FOUND "

    # Load up ballot_returned so we can use below functions
    ballot_returned_manager = BallotReturnedManager()
    if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
        results = ballot_returned_manager.retrieve_ballot_returned_from_voter_id(
            voter_id, google_civic_election_id)
        if results['ballot_returned_found']:
            ballot_returned_found = True
            ballot_returned = results['ballot_returned']

    # Create ballot_returned as "stub" we can use in retrieve_ctcl_ballot_items_for_one_voter_api
    if not positive_value_exists(ballot_returned_found):
        updates = {
            # 'line1': 'Line 1 example'
        }
        create_results = ballot_returned_manager.create_ballot_returned(
            voter_id=voter_id,
            google_civic_election_id=google_civic_election_id,
            election_day_text=election_day_text,
            election_description_text=election_description_text,
            updates=updates,
        )
        ballot_returned_found = create_results['ballot_returned_found']
        ballot_returned = create_results['ballot_returned']

    if not positive_value_exists(text_for_map_search) or not positive_value_exists(google_civic_election_id):
        status += 'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH_FOR_ELECTION_ID '
        success = False
        results = {
            'success':                      success,
            'status':                       status,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   state_code,
            'election_day_text':            election_day_text,
            'election_description_text':    election_description_text,
            'election_data_retrieved':      election_data_retrieved,
            'text_for_map_search':          text_for_map_search,
            'original_text_city':           original_text_city,
            'original_text_state':          original_text_state,
            'original_text_zip':            original_text_zip,
            'polling_location_retrieved':   polling_location_retrieved,
            'ballot_location_display_name': ballot_location_display_name,
            'ballot_location_shortcut':     ballot_location_shortcut,
            'ballot_returned':              ballot_returned,
            'ballot_returned_found':        ballot_returned_found,
            'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
        }
        return results

    normalized_city = None
    normalized_line1 = None
    normalized_state = None
    normalized_zip = None
    route = None
    street_number = None
    try:
        # Make sure we have a latitude and longitude
        google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        location = google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
        if location is None:
            status += 'RETRIEVE_FROM_VOTE_USA-Could not find location matching "{}"'.format(text_for_map_search)
            success = False
        else:
            latitude = location.latitude
            longitude = location.longitude
            lat_long_found = True
            if hasattr(location, 'raw'):
                if 'address_components' in location.raw:
                    for one_address_component in location.raw['address_components']:
                        if 'street_number' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['long_name']):
                            street_number = one_address_component['long_name']
                        if 'route' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['long_name']):
                            route = one_address_component['long_name']
                        if 'locality' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['long_name']):
                            normalized_city = one_address_component['long_name']
                        if 'postal_code' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['long_name']):
                            original_text_zip = one_address_component['long_name']
                            normalized_zip = one_address_component['long_name']
                        if 'administrative_area_level_1' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['short_name']):
                            normalized_state = one_address_component['short_name']
                            if not positive_value_exists(original_text_state):
                                original_text_state = one_address_component['short_name']
                    # Now create "normalized_line1" value to store in ballot_returned
                    if positive_value_exists(street_number) or positive_value_exists(route):
                        normalized_line1 = ''
                        if positive_value_exists(street_number):
                            normalized_line1 += str(street_number)
                        if positive_value_exists(route):
                            normalized_line1 += " " + route
    except Exception as e:
        status += "RETRIEVE_FROM_CTCL_OR_VOTE_USA-EXCEPTION with get_geocoder_for_service ERROR: " + str(e) + " "
        success = False

    if not success:
        results = {
            'success':                      success,
            'status':                       status,
            'voter_device_id':              voter_device_id,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   state_code,
            'election_day_text':            election_day_text,
            'election_description_text':    election_description_text,
            'election_data_retrieved':      election_data_retrieved,
            'text_for_map_search':          text_for_map_search,
            'original_text_city':           original_text_city,
            'original_text_state':          original_text_state,
            'original_text_zip':            original_text_zip,
            'polling_location_retrieved':   polling_location_retrieved,
            'ballot_location_display_name': ballot_location_display_name,
            'ballot_location_shortcut':     ballot_location_shortcut,
            'ballot_returned':              ballot_returned,
            'ballot_returned_found':        ballot_returned_found,
            'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
        }
        return results

    try:
        ballot_returned.latitude = latitude
        ballot_returned.longitude = longitude
        ballot_returned.normalized_line1 = normalized_line1
        ballot_returned.normalized_city = normalized_city
        ballot_returned.normalized_state = normalized_state
        ballot_returned.normalized_zip = normalized_zip
        ballot_returned.state_code = original_text_state
        ballot_returned.text_for_map_search = text_for_map_search
        ballot_returned.save()
    except Exception as e:
        status += "COULD_NOT_SAVE_LATITUDE_OR_LONGITUDE: " + str(e) + " "
        success = False

    one_ballot_results = {}
    use_ballotpedia = False
    if not success:
        pass
    elif positive_value_exists(use_ballotpedia):
        pass
        # one_ballot_results = retrieve_one_ballot_from_ballotpedia_api_v4(
        #     latitude, longitude, google_civic_election_id, state_code=state_code,
        #     text_for_map_search=text_for_map_search, voter_id=voter_id)
    elif positive_value_exists(use_ctcl):
        from import_export_ctcl.controllers import retrieve_ctcl_ballot_items_for_one_voter_api
        one_ballot_results = retrieve_ctcl_ballot_items_for_one_voter_api(
            google_civic_election_id,
            ctcl_election_uuid=ctcl_election_uuid,
            election_day_text=election_day_text,
            ballot_returned=ballot_returned,
            state_code=state_code)
        original_text_city = ballot_returned.normalized_city
        original_text_state = ballot_returned.normalized_state
        original_text_zip = ballot_returned.normalized_zip
    elif positive_value_exists(use_vote_usa):
        from import_export_vote_usa.controllers import retrieve_vote_usa_ballot_items_for_one_voter_api
        one_ballot_results = retrieve_vote_usa_ballot_items_for_one_voter_api(
            google_civic_election_id,
            election_day_text=election_day_text,
            ballot_returned=ballot_returned,
            state_code=state_code)
        original_text_city = ballot_returned.normalized_city
        original_text_state = ballot_returned.normalized_state
        original_text_zip = ballot_returned.normalized_zip
    else:
        # Should not be possible to get here
        pass

    if not one_ballot_results['success']:
        status += 'UNABLE_TO-retrieve_one_ballot_from_google_civic_api'
        status += one_ballot_results['status']
        success = False
    else:
        status += "RETRIEVE_ONE_BALLOT-SUCCESS "
        success = True
        ballot_returned_found = one_ballot_results['ballot_returned_found'] \
            if 'ballot_returned_found' in one_ballot_results else False
        if positive_value_exists(ballot_returned_found):
            ballot_returned = one_ballot_results['ballot_returned']
            ballot_returned_we_vote_id = ballot_returned.we_vote_id
            # Now that we know we have new ballot data, we need to delete prior ballot data for this election
            # because when we change voterAddress, we usually get different ballot items
            # We include a google_civic_election_id, so only the ballot info for this election is removed
            google_civic_election_id_to_delete = google_civic_election_id
            if positive_value_exists(google_civic_election_id_to_delete) and positive_value_exists(voter_id):
                # Remove all prior ballot items, so we make room for saving new ones
                #  ballot items
                voter_ballot_saved_manager = VoterBallotSavedManager()
                voter_ballot_saved_id = 0
                delete_results = voter_ballot_saved_manager.delete_voter_ballot_saved(
                    voter_ballot_saved_id, voter_id, google_civic_election_id_to_delete)
        else:
            status += "BALLOT_RETURNED_MISSING: "
            status += one_ballot_results['status']

    # VoterBallotSaved gets created outside this function

    results = {
        'success':                      success,
        'status':                       status,
        'voter_device_id':              voter_device_id,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
        'election_day_text':            election_day_text,
        'election_description_text':    election_description_text,
        'election_data_retrieved':      election_data_retrieved,
        'text_for_map_search':          text_for_map_search,
        'original_text_city':           original_text_city,
        'original_text_state':          original_text_state,
        'original_text_zip':            original_text_zip,
        'polling_location_retrieved':   polling_location_retrieved,
        'ballot_returned_found':        ballot_returned_found,
        'ballot_location_display_name': ballot_location_display_name,
        'ballot_location_shortcut':     ballot_location_shortcut,
        'ballot_returned':              ballot_returned,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
    }
    return results


def process_contest_referendum_from_structured_json(
        one_contest_referendum_structured_json, google_civic_election_id, state_code,
        ocd_division_id, local_ballot_order, voter_id, polling_location_we_vote_id):
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

    # Note that all the information saved here is independent of a particular voter
    we_vote_id = ''
    if google_civic_election_id and (district_id or district_name) and referendum_title:
        # We want to only add values, and never clear out existing values that may have been
        # entered independently
        updated_contest_measure_values = {
            'google_civic_election_id': google_civic_election_id,
        }
        if positive_value_exists(state_code):
            state_code_for_error_checking = state_code.lower()
            # Limit to 2 digits so we don't exceed the database limit
            state_code_for_error_checking = state_code_for_error_checking[-2:]
            # Make sure we recognize the state
            list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                       state_code_for_error_checking in key.lower()]
            state_code_for_error_checking = list_of_states_matching.pop()
            updated_contest_measure_values['state_code'] = state_code_for_error_checking
        if positive_value_exists(district_id):
            updated_contest_measure_values['district_id'] = district_id
        if positive_value_exists(district_name):
            updated_contest_measure_values['district_name'] = district_name
        if positive_value_exists(referendum_title):
            updated_contest_measure_values['measure_title'] = referendum_title
            # We store the literal spelling here so we can match in the future, even if we customize measure_title
            updated_contest_measure_values['google_civic_measure_title'] = referendum_title
        if positive_value_exists(referendum_subtitle):
            updated_contest_measure_values['measure_subtitle'] = referendum_subtitle
        if positive_value_exists(referendum_url):
            updated_contest_measure_values['measure_url'] = referendum_url
        if positive_value_exists(referendum_text):
            updated_contest_measure_values['measure_text'] = referendum_text
        if positive_value_exists(ocd_division_id):
            updated_contest_measure_values['ocd_division_id'] = ocd_division_id
        if positive_value_exists(primary_party):
            updated_contest_measure_values['primary_party'] = primary_party
        if positive_value_exists(district_scope):
            updated_contest_measure_values['district_scope'] = district_scope

        measure_manager = ContestMeasureManager()
        update_or_create_contest_measure_results = measure_manager.update_or_create_contest_measure(
            we_vote_id=we_vote_id,
            google_civic_election_id=google_civic_election_id,
            measure_title=referendum_title,
            district_id=district_id,
            district_name=district_name,
            state_code=state_code,
            updated_contest_measure_values=updated_contest_measure_values)
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
        measure_text = contest_measure.measure_text
        ballot_item_manager = BallotItemManager()

        # If a voter_id was passed in, save an entry for this office for the voter's ballot
        if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(contest_measure_id):
            contest_office_id = 0
            contest_office_we_vote_id = ''
            ballot_item_manager.update_or_create_ballot_item_for_voter(
                voter_id, google_civic_election_id, google_ballot_placement, ballot_item_display_name,
                measure_subtitle, measure_text, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id, state_code)

        if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(contest_measure_id):
            contest_office_id = 0
            contest_office_we_vote_id = ''
            ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id, state_code)

    return update_or_create_contest_measure_results


def groom_and_store_google_civic_measure_json_2021(
        ballot_item_dict_list=[],
        election_day_text='',
        existing_measure_objects_dict={},
        google_civic_election_id='',
        local_ballot_order=0,
        new_measure_we_vote_ids_list=[],
        one_contest_json={},
        polling_location_we_vote_id='',
        use_ctcl=False,
        use_vote_usa=False,
        update_or_create_rules={},
        state_code='',
        voter_id=0):
    status = ''
    success = True
    contest_measure = None
    contest_measure_id = 0
    contest_measure_we_vote_id = ""
    google_civic_election_id_string = str(google_civic_election_id)

    referendum_title = one_contest_json['referendumTitle'] if \
        'referendumTitle' in one_contest_json else ''

    measure_data_exists = positive_value_exists(referendum_title)
    if not measure_data_exists:
        # We need measure to proceed, so without it, go to the next race
        status += "MISSING_REFERENDUM_TITLE "
        results = {
            'success':                              False,
            'status':                               status,
            'ballot_item_dict_list':                ballot_item_dict_list,
            'existing_measure_objects_dict':        existing_measure_objects_dict,
            'new_measure_we_vote_ids_list':         new_measure_we_vote_ids_list,
        }
        return results

    ctcl_measure_uuid = None
    vote_usa_measure_id = None
    if positive_value_exists(use_ctcl):
        ctcl_measure_uuid = one_contest_json['id']
    elif positive_value_exists(use_vote_usa):
        raw_vote_usa_measure_id = one_contest_json['id']
        vote_usa_measure_id = extract_vote_usa_measure_id(raw_vote_usa_measure_id)

    referendum_subtitle = one_contest_json['referendumSubtitle'] if \
        'referendumSubtitle' in one_contest_json else ''
    if not positive_value_exists(referendum_subtitle):
        referendum_subtitle = one_contest_json['referendumBrief'] if \
            'referendumBrief' in one_contest_json else ''
    referendum_url = one_contest_json['referendumUrl'] if \
        'referendumUrl' in one_contest_json else ''
    referendum_text = one_contest_json['referendumText'] if \
        'referendumText' in one_contest_json else ''

    # These following fields exist for both candidates and referendum
    results = process_contest_common_fields_from_structured_json(one_contest_json, is_ctcl=use_ctcl)
    google_ballot_placement = results['ballot_placement']  # A number specifying the position of this contest
    # on the voter's ballot.
    primary_party = results['primary_party']  # If this is a partisan election, the name of the party it is for.
    district_name = results['district_name']  # The name of the district.
    district_scope = results['district_scope']   # The geographic scope of this district. If unspecified the
    measure_ocd_division_id = results['contest_ocd_division_id']
    # district's geography is not known. One of: national, statewide, congressional, stateUpper, stateLower,
    # countywide, judicial, schoolBoard, cityWide, township, countyCouncil, cityCouncil, ward, special
    district_id = results['district_id']

    allowed_to_create_measures = \
        'create_measures' in update_or_create_rules and positive_value_exists(
            update_or_create_rules['create_measures'])
    allowed_to_update_measures = \
        'update_measures' in update_or_create_rules and positive_value_exists(
            update_or_create_rules['update_measures'])

    continue_searching_for_measure = True
    create_measure_entry = False
    measure_manager = ContestMeasureManager()
    if continue_searching_for_measure and positive_value_exists(ctcl_measure_uuid):
        if ctcl_measure_uuid in existing_measure_objects_dict:
            contest_measure = existing_measure_objects_dict[ctcl_measure_uuid]
            contest_measure_we_vote_id = contest_measure.we_vote_id
            contest_measure_id = contest_measure.id
            measure_title = contest_measure.measure_title
            continue_searching_for_measure = False
        else:
            measure_results = measure_manager.retrieve_contest_measure(
                ctcl_uuid=ctcl_measure_uuid,
                read_only=(not allowed_to_update_measures))
            if measure_results['contest_measure_found']:
                continue_searching_for_measure = False
                contest_measure = measure_results['contest_measure']
                contest_measure_we_vote_id = contest_measure.we_vote_id
                contest_measure_id = contest_measure.id
                measure_title = contest_measure.measure_title
                existing_measure_objects_dict[ctcl_measure_uuid] = contest_measure
                # In the future, we will want to look for updated data to save
            elif measure_results['MultipleObjectsReturned']:
                status += "MORE_THAN_ONE_MEASURE_WITH_SAME_CTCL_UUID_ID: " + str(ctcl_measure_uuid) + " "
                continue_searching_for_measure = False
            elif not measure_results['success']:
                status += "MEASURE_RETRIEVE_BY_CTCL_UUID_FAILED: "
                status += measure_results['status']
                results = {
                    'success':                              False,
                    'status':                               status,
                    'ballot_item_dict_list':                ballot_item_dict_list,
                    'existing_measure_objects_dict':        existing_measure_objects_dict,
                    'new_measure_we_vote_ids_list':         new_measure_we_vote_ids_list,
                }
                return results
            else:
                continue_searching_for_measure = True
    elif continue_searching_for_measure and positive_value_exists(vote_usa_measure_id):
        if vote_usa_measure_id in existing_measure_objects_dict:
            contest_measure = existing_measure_objects_dict[vote_usa_measure_id]
            contest_measure_we_vote_id = contest_measure.we_vote_id
            contest_measure_id = contest_measure.id
            measure_title = contest_measure.measure_title
            continue_searching_for_measure = False
        else:
            measure_results = measure_manager.retrieve_contest_measure(
                vote_usa_measure_id=vote_usa_measure_id,
                read_only=(not allowed_to_update_measures))
            if measure_results['contest_measure_found']:
                continue_searching_for_measure = False
                contest_measure = measure_results['contest_measure']
                contest_measure_we_vote_id = contest_measure.we_vote_id
                contest_measure_id = contest_measure.id
                measure_title = contest_measure.measure_title
                existing_measure_objects_dict[vote_usa_measure_id] = contest_measure
                # In the future, we will want to look for updated data to save
            elif measure_results['MultipleObjectsReturned']:
                status += "MORE_THAN_ONE_MEASURE_WITH_SAME_VOTE_USA_ID: " + str(vote_usa_measure_id) + " "
                continue_searching_for_measure = False
            elif not measure_results['success']:
                status += "MEASURE_RETRIEVE_BY_VOTE_USA_FAILED: "
                status += measure_results['status']
                results = {
                    'success':                          False,
                    'status':                           status,
                    'ballot_item_dict_list':            ballot_item_dict_list,
                    'existing_measure_objects_dict':    existing_measure_objects_dict,
                    'new_measure_we_vote_ids_list':     new_measure_we_vote_ids_list,
                }
                return results
            else:
                # If here, we have a Vote USA Measure Id, but no measure found.
                create_measure_entry = True
                continue_searching_for_measure = False

    if continue_searching_for_measure:
        # Check to see if there is an measure which doesn't match by data provider id
        measure_list_manager = ContestMeasureListManager()
        read_only = not allowed_to_create_measures  # Retrieve an editable object in case we need to update source id
        results = measure_list_manager.retrieve_contest_measures_from_non_unique_identifiers(
            contest_measure_title=referendum_title,
            google_civic_election_id_list=[google_civic_election_id],
            incoming_state_code=state_code,
            district_id=district_id,
            read_only=read_only)
        if not results['success']:
            continue_searching_for_measure = False
            status += "FAILED_RETRIEVING_CONTEST_FROM_UNIQUE_IDS: " + results['status'] + " "
            success = False
        elif results['multiple_entries_found']:
            continue_searching_for_measure = False
            status += "RETRIEVING_CONTEST_FROM_UNIQUE_IDS-MULTIPLE_FOUND: " + results['status'] + " "
            success = False
        elif results['contest_measure_found']:
            continue_searching_for_measure = False
            contest_measure = results['contest_measure']
            contest_measure_we_vote_id = contest_measure.we_vote_id
            contest_measure_id = contest_measure.id
            measure_title = contest_measure.measure_title
            if use_ctcl:
                if allowed_to_create_measures and not positive_value_exists(contest_measure.ctcl_uuid):
                    contest_measure.ctcl_uuid = ctcl_measure_uuid
                    try:
                        contest_measure.save()
                        if positive_value_exists(ctcl_measure_uuid):
                            existing_measure_objects_dict[ctcl_measure_uuid] = contest_measure
                    except Exception as e:
                        status += "SAVING_CTCL_UUID_FAILED: " + str(e) + ' '
                        success = False
            elif use_vote_usa:
                if allowed_to_create_measures and not positive_value_exists(contest_measure.vote_usa_measure_id):
                    contest_measure.vote_usa_measure_id = vote_usa_measure_id
                    try:
                        contest_measure.save()
                        if positive_value_exists(vote_usa_measure_id):
                            existing_measure_objects_dict[vote_usa_measure_id] = contest_measure
                    except Exception as e:
                        status += "SAVING_VOTE_USA_MEASURE_ID_FAILED: " + str(e) + ' '
                        success = False
        else:
            create_measure_entry = True

    if not success:
        results = {
            'success':                          False,
            'status':                           status,
            'ballot_item_dict_list':            ballot_item_dict_list,
            'existing_measure_objects_dict':    existing_measure_objects_dict,
            'new_measure_we_vote_ids_list':     new_measure_we_vote_ids_list,
        }
        return results

    proceed_to_create_measure = positive_value_exists(create_measure_entry) and allowed_to_create_measures
    proceed_to_update_measure = allowed_to_update_measures

    ballot_item_display_name = ''
    if proceed_to_create_measure or proceed_to_update_measure:
        # Note that all the information saved here is independent of a particular voter
        if google_civic_election_id and \
                (district_id or district_name or ctcl_measure_uuid or vote_usa_measure_id) and \
                referendum_title:
            updated_contest_measure_values = {
                'google_civic_election_id': google_civic_election_id,
            }

            if positive_value_exists(state_code):
                state_code_for_error_checking = state_code.lower()
                # Limit to 2 digits so we don't exceed the database limit
                state_code_for_error_checking = state_code_for_error_checking[-2:]
                # Make sure we recognize the state
                list_of_states_matching = [key.lower() for key, value in STATE_CODE_MAP.items() if
                                           state_code_for_error_checking in key.lower()]
                state_code_for_error_checking = list_of_states_matching.pop()
                updated_contest_measure_values['state_code'] = state_code_for_error_checking
            if positive_value_exists(district_id):
                updated_contest_measure_values['district_id'] = district_id
            if positive_value_exists(district_name):
                updated_contest_measure_values['district_name'] = district_name
            if positive_value_exists(referendum_title):
                updated_contest_measure_values['measure_title'] = referendum_title
                # We store the literal spelling here so we can match in the future, even if we customize measure_title
                updated_contest_measure_values['google_civic_measure_title'] = referendum_title
            if positive_value_exists(referendum_subtitle):
                updated_contest_measure_values['measure_subtitle'] = referendum_subtitle
            if positive_value_exists(referendum_url):
                updated_contest_measure_values['measure_url'] = referendum_url
            if positive_value_exists(referendum_text):
                updated_contest_measure_values['measure_text'] = referendum_text
            if positive_value_exists(measure_ocd_division_id):
                updated_contest_measure_values['ocd_division_id'] = measure_ocd_division_id
            if positive_value_exists(primary_party):
                updated_contest_measure_values['primary_party'] = primary_party
            if positive_value_exists(district_scope):
                updated_contest_measure_values['district_scope'] = district_scope
            if 'yes_vote_description' in one_contest_json and \
                    positive_value_exists(one_contest_json['yes_vote_description']):
                updated_contest_measure_values['ballotpedia_yes_vote_description'] = \
                    one_contest_json['yes_vote_description']
            if 'no_vote_description' in one_contest_json and \
                    positive_value_exists(one_contest_json['no_vote_description']):
                updated_contest_measure_values['ballotpedia_no_vote_description'] = \
                    one_contest_json['no_vote_description']

            if positive_value_exists(proceed_to_create_measure):
                update_or_create_contest_measure_results = measure_manager.create_measure_row_entry(
                    ctcl_uuid=ctcl_measure_uuid,
                    google_civic_election_id=google_civic_election_id,
                    measure_subtitle=referendum_subtitle,
                    measure_text=referendum_text,
                    measure_title=referendum_title,
                    state_code=state_code,
                    vote_usa_measure_id=vote_usa_measure_id,
                    defaults=updated_contest_measure_values)
            else:
                update_or_create_contest_measure_results = measure_manager.update_or_create_contest_measure(
                    ctcl_uuid=ctcl_measure_uuid,
                    district_id=district_id,
                    district_name=district_name,
                    google_civic_election_id=google_civic_election_id,
                    measure_title=referendum_title,
                    state_code=state_code,
                    vote_usa_measure_id=vote_usa_measure_id,
                    we_vote_id=contest_measure_we_vote_id,
                    updated_contest_measure_values=updated_contest_measure_values)

            if update_or_create_contest_measure_results['success']:
                if positive_value_exists(update_or_create_contest_measure_results['contest_measure_found']):
                    contest_measure = update_or_create_contest_measure_results['contest_measure']
                    contest_measure_id = contest_measure.id
                    contest_measure_we_vote_id = contest_measure.we_vote_id
                    ballot_item_display_name = contest_measure.measure_title
                    measure_subtitle = contest_measure.measure_subtitle
                    measure_text = contest_measure.measure_text
                    new_measure_created = True
                    if contest_measure_we_vote_id not in new_measure_we_vote_ids_list:
                        new_measure_we_vote_ids_list.append(contest_measure_we_vote_id)

                    if positive_value_exists(ctcl_measure_uuid):
                        existing_measure_objects_dict[ctcl_measure_uuid] = contest_measure
                    elif positive_value_exists(vote_usa_measure_id):
                        existing_measure_objects_dict[vote_usa_measure_id] = contest_measure
            else:
                contest_measure_id = 0
                contest_measure_we_vote_id = ''
                ballot_item_display_name = ''
                success = False
                status += update_or_create_contest_measure_results['status']
        else:
            results = {
                'success':                          False,
                'status':                           status,
                'ballot_item_dict_list':            ballot_item_dict_list,
                'existing_measure_objects_dict':    existing_measure_objects_dict,
                'new_measure_we_vote_ids_list':     new_measure_we_vote_ids_list,
            }
            return results

    if positive_value_exists(contest_measure_we_vote_id):
        measure_json = {
            'ballot_item_display_name':     ballot_item_display_name,
            'contest_measure_text':         contest_measure.measure_text,
            'contest_measure_name':         contest_measure.measure_title,  # We use "name" in import system
            'contest_measure_url':          contest_measure.measure_url,
            'contest_measure_we_vote_id':   contest_measure.we_vote_id,
            'contest_measure_id':           contest_measure.id,
            'election_day_text':            election_day_text,
            'local_ballot_order':           local_ballot_order,
            'no_vote_description':          contest_measure.ballotpedia_no_vote_description,
            'polling_location_we_vote_id':  polling_location_we_vote_id,
            'state_code':                   state_code,
            'voter_id':                     voter_id,
            'yes_vote_description':         contest_measure.ballotpedia_yes_vote_description,
        }
        ballot_item_dict_list.append(measure_json)

    results = {
        'success':                          success,
        'status':                           status,
        'ballot_item_dict_list':            ballot_item_dict_list,
        'existing_measure_objects_dict':    existing_measure_objects_dict,
        'new_measure_we_vote_ids_list':     new_measure_we_vote_ids_list,
    }
    return results

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
