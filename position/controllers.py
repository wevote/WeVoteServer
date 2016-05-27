# position/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered, PositionEnteredManager, PositionListManager, ANY_STANCE, NO_STANCE
from ballot.models import OFFICE, CANDIDATE, MEASURE
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from election.models import fetch_election_state
from exception.models import handle_record_not_found_exception, handle_record_not_saved_exception
from follow.models import FollowOrganizationManager, FollowOrganizationList
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from organization.models import OrganizationManager
import json
import requests
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
from voter_guide.models import ORGANIZATION, PUBLIC_FIGURE, VOTER, UNKNOWN_VOTER_GUIDE
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POSITIONS_SYNC_URL = get_environment_variable("POSITIONS_SYNC_URL")


# We retrieve from only one of the two possible variables
def position_retrieve_for_api(position_id, position_we_vote_id, voter_device_id):  # positionRetrieve
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    # TODO for certain positions (voter positions), we need to restrict the retrieve based on voter_device_id / voter_id
    if voter_device_id:
        pass

    we_vote_id = position_we_vote_id.strip()
    if not positive_value_exists(position_id) and not positive_value_exists(position_we_vote_id):
        json_data = {
            'status':                   "POSITION_RETRIEVE_BOTH_IDS_MISSING",
            'success':                  False,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':              False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'vote_smart_rating':        '',
            'vote_smart_time_span':     '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionEnteredManager()
    organization_id = 0
    contest_office_id = 0
    candidate_campaign_id = 0
    contest_measure_id = 0
    position_voter_id = 0
    results = position_manager.retrieve_position(position_id, position_we_vote_id, organization_id, position_voter_id,
                                                 contest_office_id, candidate_campaign_id, contest_measure_id)

    if results['position_found']:
        position = results['position']
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'is_support':                       results['is_support'],
            'is_positive_rating':               results['is_positive_rating'],
            'is_support_or_positive_rating':    results['is_support_or_positive_rating'],
            'is_oppose':                        results['is_oppose'],
            'is_negative_rating':               results['is_negative_rating'],
            'is_oppose_or_negative_rating':     results['is_oppose_or_negative_rating'],
            'is_information_only':      results['is_information_only'],
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'vote_smart_rating':        position.vote_smart_rating,
            'vote_smart_time_span':     position.vote_smart_time_span,
            'last_updated':             position.last_updated(),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   results['status'],
            'success':                  results['success'],
            'position_id':              position_id,
            'position_we_vote_id':      we_vote_id,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   NO_STANCE,
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'vote_smart_rating':        '',
            'vote_smart_time_span':     '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_save_for_api(
        voter_device_id, position_id, position_we_vote_id,
        organization_we_vote_id,
        public_figure_we_vote_id,
        voter_we_vote_id,
        google_civic_election_id,
        ballot_item_display_name,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        stance,
        statement_text,
        statement_html,
        more_info_url
        ):
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    existing_unique_identifier_found = positive_value_exists(position_id) \
        or positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        results = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               '',
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               '',
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results

    # Look up the state_code from the election
    state_code = fetch_election_state(google_civic_election_id)

    position_manager = PositionEnteredManager()
    save_results = position_manager.update_or_create_position(
        position_id=position_id,
        position_we_vote_id=position_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        public_figure_we_vote_id=public_figure_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        state_code=state_code,
        ballot_item_display_name=ballot_item_display_name,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        stance=stance,
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    if save_results['success']:
        position = save_results['position']
        results = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'new_position_created':     save_results['new_position_created'],
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'is_support':                       position.is_support(),
            'is_positive_rating':               position.is_positive_rating(),
            'is_support_or_positive_rating':    position.is_support_or_positive_rating(),
            'is_oppose':                        position.is_oppose(),
            'is_negative_rating':               position.is_negative_rating(),
            'is_oppose_or_negative_rating':     position.is_oppose_or_negative_rating(),
            'is_information_only':      position.is_information_only(),
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'state_code':               position.state_code,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results


def position_list_for_ballot_item_for_api(voter_device_id,  # positionListForBallotItem
                                          office_id, office_we_vote_id,
                                          candidate_id, candidate_we_vote_id,
                                          measure_id, measure_we_vote_id,
                                          stance_we_are_looking_for=ANY_STANCE,
                                          show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the position identifiers from orgs, friends and public figures the voter follows
    This list of information is used to retrieve the detailed information
    """
    position_manager = PositionEnteredManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':               'VALID_VOTER_DEVICE_ID_MISSING',
            'success':              False,
            'count':                0,
            'kind_of_ballot_item':  "UNKNOWN",
            'ballot_item_id':       0,
            'position_list':        position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':               "VALID_VOTER_ID_MISSING ",
            'success':              False,
            'count':                0,
            'kind_of_ballot_item':  "UNKNOWN",
            'ballot_item_id':       0,
            'position_list':        position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    ballot_item_found = False
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        return_only_latest_position_per_speaker = True
        all_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                candidate_id, candidate_we_vote_id, stance_we_are_looking_for, return_only_latest_position_per_speaker)
        kind_of_ballot_item = CANDIDATE

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        candidate_campaign_manager = CandidateCampaignManager()
        if positive_value_exists(candidate_id):
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        else:
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)

        if results['candidate_campaign_found']:
            candidate_campaign = results['candidate_campaign']
            ballot_item_id = candidate_campaign.id
            ballot_item_we_vote_id = candidate_campaign.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = candidate_id
            ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                measure_id, measure_we_vote_id, stance_we_are_looking_for)
        kind_of_ballot_item = MEASURE

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        contest_measure_manager = ContestMeasureManager()
        if positive_value_exists(measure_id):
            results = contest_measure_manager.retrieve_contest_measure_from_id(measure_id)
        else:
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)

        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            ballot_item_id = contest_measure.id
            ballot_item_we_vote_id = contest_measure.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = measure_id
            ballot_item_we_vote_id = measure_we_vote_id
    elif positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                office_id, office_we_vote_id, stance_we_are_looking_for)
        kind_of_ballot_item = OFFICE

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        contest_office_manager = ContestOfficeManager()
        if positive_value_exists(office_id):
            results = contest_office_manager.retrieve_contest_office_from_id(office_id)
        else:
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)

        if results['contest_office_found']:
            contest_office = results['contest_office']
            ballot_item_id = contest_office.id
            ballot_item_we_vote_id = contest_office.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = office_id
            ballot_item_we_vote_id = office_we_vote_id
    else:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not ballot_item_found:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_BALLOT_ITEM_NOT_FOUND',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    if show_positions_this_voter_follows:
        position_objects = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, all_positions_list, organizations_followed_by_voter)
        positions_count = len(position_objects)
        status = 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_FOLLOWED'
        success = True
    else:
        position_objects = position_list_manager.calculate_positions_not_followed_by_voter(
            all_positions_list, organizations_followed_by_voter)
        positions_count = len(position_objects)
        status = 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED'
        success = True

    position_list = []
    for one_position in position_objects:
        # Whose position is it?
        if positive_value_exists(one_position.organization_we_vote_id):
            speaker_type = ORGANIZATION
            speaker_id = one_position.organization_id
            speaker_we_vote_id = one_position.organization_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or not positive_value_exists(one_position.speaker_twitter_handle):
                one_position = position_manager.refresh_cached_position_info(one_position)
            speaker_display_name = one_position.speaker_display_name
        elif positive_value_exists(one_position.voter_id):
            speaker_type = VOTER
            speaker_id = one_position.voter_id
            speaker_we_vote_id = one_position.voter_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.voter_we_vote_id) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or not positive_value_exists(one_position.speaker_twitter_handle):
                one_position = position_manager.refresh_cached_position_info(one_position)

            speaker_display_name = "You"
        elif positive_value_exists(one_position.public_figure_we_vote_id):
            speaker_type = PUBLIC_FIGURE
            speaker_id = one_position.public_figure_id
            speaker_we_vote_id = one_position.public_figure_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or not positive_value_exists(one_position.speaker_twitter_handle):
                one_position = position_manager.refresh_cached_position_info(one_position)
            speaker_display_name = one_position.speaker_display_name
        else:
            speaker_type = UNKNOWN_VOTER_GUIDE
            speaker_display_name = "Unknown"
            speaker_id = None
            speaker_we_vote_id = None
            one_position_success = False

        if one_position_success:
            one_position_dict_for_api = {
                'position_id':                      one_position.id,
                'position_we_vote_id':              one_position.we_vote_id,
                'ballot_item_display_name':         one_position.ballot_item_display_name,
                'speaker_display_name':             speaker_display_name,
                'speaker_image_url_https':          one_position.speaker_image_url_https,
                'speaker_twitter_handle':           one_position.speaker_twitter_handle,
                'speaker_type':                     speaker_type,
                'speaker_id':                       speaker_id,
                'speaker_we_vote_id':               speaker_we_vote_id,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'vote_smart_rating':                one_position.vote_smart_rating,
                'vote_smart_time_span':             one_position.vote_smart_time_span,
                'statement_text':                   one_position.statement_text,
                'more_info_url':                    one_position.more_info_url,
                'last_updated':                     one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    json_data = {
        'status':                   status,
        'success':                  success,
        'count':                    positions_count,
        'kind_of_ballot_item':      kind_of_ballot_item,
        'ballot_item_id':           ballot_item_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'position_list':            position_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_list_for_opinion_maker_for_api(voter_device_id,  # positionListForOpinionMaker
                                            organization_id, organization_we_vote_id,
                                            public_figure_id, public_figure_we_vote_id,
                                            stance_we_are_looking_for=ANY_STANCE,
                                            filter_for_voter=True,
                                            google_civic_election_id=0,
                                            state_code=''):
    """
    We want to return a JSON file with a list of positions held by orgs and public figures
    We retrieve the positions of friends separately (since we have to deal with stricter security with friends).
    """
    is_following = False
    is_ignoring = False
    opinion_maker_display_name = ''
    opinion_maker_image_url_https = ''
    status = ''
    all_positions_list = []

    # Convert incoming variables to "opinion_maker"
    if positive_value_exists(organization_id) or positive_value_exists(organization_we_vote_id):
        kind_of_opinion_maker = ORGANIZATION
        kind_of_opinion_maker_text = "ORGANIZATION"  # For returning a value via the API
        opinion_maker_id = organization_id
        opinion_maker_we_vote_id = organization_we_vote_id
    elif positive_value_exists(public_figure_id) or positive_value_exists(public_figure_we_vote_id):
        kind_of_opinion_maker = PUBLIC_FIGURE
        kind_of_opinion_maker_text = "PUBLIC_FIGURE"
        opinion_maker_id = public_figure_id
        opinion_maker_we_vote_id = public_figure_we_vote_id
    else:
        kind_of_opinion_maker = UNKNOWN_VOTER_GUIDE
        kind_of_opinion_maker_text = "UNKNOWN_VOTER_GUIDE"
        opinion_maker_id = 0
        opinion_maker_we_vote_id = ''

    position_manager = PositionEnteredManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':                           'VALID_VOTER_DEVICE_ID_MISSING_OPINION_MAKER_POSITION_LIST',
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':                           "VALID_VOTER_ID_MISSING_OPINION_MAKER_POSITION_LIST ",
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    opinion_maker_found = False
    if kind_of_opinion_maker == ORGANIZATION:
        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this opinion_maker, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        organization_manager = OrganizationManager()
        if positive_value_exists(organization_id):
            results = organization_manager.retrieve_organization_from_id(organization_id)
        else:
            results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)

        if results['organization_found']:
            organization = results['organization']
            opinion_maker_id = organization.id
            opinion_maker_we_vote_id = organization.we_vote_id
            opinion_maker_display_name = organization.organization_name
            opinion_maker_image_url_https = organization.organization_photo_url()
            opinion_maker_found = True

            follow_organization_manager = FollowOrganizationManager()
            voter_we_vote_id = ''
            following_results = follow_organization_manager.retrieve_voter_following_org_status(
                voter_id, voter_we_vote_id, opinion_maker_id, opinion_maker_we_vote_id)
            if following_results['is_following']:
                is_following = True
            elif following_results['is_ignoring']:
                is_ignoring = True

            all_positions_list = position_list_manager.retrieve_all_positions_for_organization(
                    organization_id, organization_we_vote_id, stance_we_are_looking_for,
                    filter_for_voter, voter_device_id, google_civic_election_id, state_code)
        else:
            opinion_maker_id = organization_id
            opinion_maker_we_vote_id = organization_we_vote_id
    elif kind_of_opinion_maker == PUBLIC_FIGURE:
        all_positions_list = position_list_manager.retrieve_all_positions_for_public_figure(
                public_figure_id, public_figure_we_vote_id, stance_we_are_looking_for,
                filter_for_voter, voter_device_id, google_civic_election_id, state_code)

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this opinion_maker, we retrieve the following so we can have the id and we_vote_id (per the request of
        # the WebApp team)
        # TODO Do we want to give public figures an entry separate from their voter account? Needs to be implemented.
        # candidate_campaign_manager = CandidateCampaignManager()
        # if positive_value_exists(candidate_id):
        #     results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        # else:
        #     results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        #
        # if results['candidate_campaign_found']:
        #     candidate_campaign = results['candidate_campaign']
        #     ballot_item_id = candidate_campaign.id
        #     ballot_item_we_vote_id = candidate_campaign.we_vote_id
        #     opinion_maker_found = True
        # else:
        #     ballot_item_id = candidate_id
        #     ballot_item_we_vote_id = candidate_we_vote_id
    else:
        position_list = []
        json_data = {
            'status':                           'POSITION_LIST_RETRIEVE_MISSING_OPINION_MAKER_ID',
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not opinion_maker_found:
        position_list = []
        json_data = {
            'status':                           'POSITION_LIST_RETRIEVE_OPINION_MAKER_NOT_FOUND',
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list = []
    for one_position in all_positions_list:
        # Whose position is it?
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.public_figure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = one_position.public_figure_id
            ballot_item_we_vote_id = one_position.public_figure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.public_figure_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = one_position.public_figure_id
            ballot_item_we_vote_id = one_position.public_figure_we_vote_id
            one_position_success = True
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            # Make sure we have this data to display. If we don't, refresh PositionEntered table from other tables.
            if not positive_value_exists(one_position.ballot_item_display_name) \
                    or not positive_value_exists(one_position.ballot_item_image_url_https) \
                    or not positive_value_exists(one_position.ballot_item_twitter_handle) \
                    or not positive_value_exists(one_position.state_code):
                one_position = position_manager.refresh_cached_position_info(one_position)
            one_position_dict_for_api = {
                'position_id':                  one_position.id,
                'position_we_vote_id':          one_position.we_vote_id,
                'ballot_item_display_name':     one_position.ballot_item_display_name,
                'ballot_item_image_url_https':  one_position.ballot_item_image_url_https,
                'ballot_item_twitter_handle':   one_position.ballot_item_twitter_handle,
                'kind_of_ballot_item':          kind_of_ballot_item,
                'ballot_item_id':               ballot_item_id,
                'ballot_item_we_vote_id':       ballot_item_we_vote_id,
                'ballot_item_state_code':       one_position.state_code,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'vote_smart_rating':            one_position.vote_smart_rating,
                'vote_smart_time_span':         one_position.vote_smart_time_span,
                'google_civic_election_id':     one_position.google_civic_election_id,
                'last_updated':                 one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    status += ' POSITION_LIST_FOR_OPINION_MAKER_SUCCEEDED'
    success = True
    json_data = {
        'status':                           status,
        'success':                          success,
        'count':                            len(position_list),
        'kind_of_opinion_maker':            kind_of_opinion_maker_text,
        'opinion_maker_id':                 opinion_maker_id,
        'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
        'opinion_maker_display_name':       opinion_maker_display_name,
        'opinion_maker_image_url_https':    opinion_maker_image_url_https,
        'is_following':                     is_following,
        'is_ignoring':                      is_ignoring,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
        'position_list':                    position_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_import_from_sample_file(request=None):  # , load_from_uri=False
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Load saved json from local file
    with open("position/import_data/positions_sample.json") as json_data:
        structured_json = json.load(json_data)

    request = None
    return positions_import_from_structured_json(request, structured_json)


def positions_import_from_master_server(request, google_civic_election_id=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    messages.add_message(request, messages.INFO, "Loading Positions from We Vote Master servers")
    logger.info("Loading Positions from We Vote Master servers")
    # Request json file from We Vote servers
    request = requests.get(POSITIONS_SYNC_URL, params={
        "key":                      WE_VOTE_API_KEY,  # This comes from an environment variable
        "format":                   'json',
        "google_civic_election_id": google_civic_election_id,
    })
    structured_json = json.loads(request.text)

    results = filter_positions_structured_json_for_local_duplicates(structured_json)
    filtered_structured_json = results['structured_json']
    duplicates_removed = results['duplicates_removed']

    import_results = positions_import_from_structured_json(filtered_structured_json)
    import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_positions_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove positions that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    position_list_manager = PositionListManager()
    for one_position in structured_json:
        we_vote_id = one_position['we_vote_id'] if 'we_vote_id' in one_position else ''
        google_civic_election_id = \
            one_position['google_civic_election_id'] if 'google_civic_election_id' in one_position else ''
        organization_we_vote_id = \
            one_position['organization_we_vote_id'] if 'organization_we_vote_id' in one_position else ''
        candidate_campaign_we_vote_id = one_position['candidate_campaign_we_vote_id'] \
            if 'candidate_campaign_we_vote_id' in one_position else ''
        contest_measure_we_vote_id = one_position['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_position else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = position_list_manager.retrieve_possible_duplicate_positions(
            google_civic_election_id, organization_we_vote_id,
            candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            we_vote_id_from_master)

        if results['position_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_position)

    positions_results = {
        'success':              True,
        'status':               "FILTER_POSITIONS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return positions_results


def positions_import_from_structured_json(structured_json):
    positions_saved = 0
    positions_updated = 0
    positions_not_processed = 0
    for one_position in structured_json:
        # Make sure we have the minimum required variables
        if positive_value_exists(one_position["we_vote_id"]) \
                and (positive_value_exists(one_position["organization_we_vote_id"]) or positive_value_exists(
                        one_position["public_figure_we_vote_id"])) \
                and positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            # organization position on candidate
            pass
        elif positive_value_exists(one_position["we_vote_id"]) \
                and (positive_value_exists(one_position["organization_we_vote_id"]) or positive_value_exists(
                    one_position["public_figure_we_vote_id"])) \
                and positive_value_exists(one_position["contest_measure_we_vote_id"]):
            # organization position on measure
            pass
        else:
            # Note that we do not import voter_we_vote_id positions at this point because they are considered private
            positions_not_processed += 1
            continue

        # Check to see if this position had been imported previously
        position_on_stage_found = False
        try:
            if len(one_position["we_vote_id"]) > 0:
                position_query = PositionEntered.objects.filter(we_vote_id=one_position["we_vote_id"])
                if len(position_query):
                    position_on_stage = position_query[0]
                    position_on_stage_found = True
        except PositionEntered.DoesNotExist as e:
            pass
        except Exception as e:
            pass

        # We need to look up the local organization_id and store for internal use
        organization_id = 0
        if positive_value_exists(one_position["organization_we_vote_id"]):
            organization_manager = OrganizationManager()
            organization_id = organization_manager.fetch_organization_id(one_position["organization_we_vote_id"])
            if not positive_value_exists(organization_id):
                # If an id does not exist, then we don't have this organization locally
                positions_not_processed += 1
                continue
        elif positive_value_exists(one_position["public_figure_we_vote_id"]):
            # TODO Build this for public_figure - skip for now
            continue

        candidate_campaign_manager = CandidateCampaignManager()
        candidate_campaign_id = 0
        contest_measure_id = 0
        if positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            # We need to look up the local candidate_campaign_id and store for internal use
            candidate_campaign_id = candidate_campaign_manager.fetch_candidate_campaign_id_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])
            if not positive_value_exists(candidate_campaign_id):
                # If an id does not exist, then we don't have this candidate locally
                positions_not_processed += 1
                continue
        elif positive_value_exists(one_position["contest_measure_we_vote_id"]):
            contest_measure_manager = ContestMeasureManager()
            contest_measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(
                one_position["contest_measure_we_vote_id"])
            if not positive_value_exists(contest_measure_id):
                # If an id does not exist, then we don't have this measure locally
                positions_not_processed += 1
                continue

        contest_office_id = 0
        if positive_value_exists(one_position['contest_office_we_vote_id']):
            # TODO
            pass

        politician_id = 0
        if positive_value_exists(one_position['politician_we_vote_id']):
            # TODO
            pass

        voter_id = 0
        if positive_value_exists(one_position['voter_we_vote_id']):
            # TODO
            pass

        # Find the google_civic_candidate_name so we have a backup way to link position if the we_vote_id is lost
        google_civic_candidate_name = one_position["google_civic_candidate_name"] if \
            "google_civic_candidate_name" in one_position else ''
        if not positive_value_exists(google_civic_candidate_name):
            google_civic_candidate_name = candidate_campaign_manager.fetch_google_civic_candidate_name_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])

        try:
            if position_on_stage_found:
                # Update
                position_on_stage.we_vote_id = one_position["we_vote_id"]
                position_on_stage.candidate_campaign_id = candidate_campaign_id
                position_on_stage.candidate_campaign_we_vote_id = one_position["candidate_campaign_we_vote_id"]
                position_on_stage.contest_measure_id = contest_measure_id
                position_on_stage.contest_measure_we_vote_id = one_position["contest_measure_we_vote_id"]
                position_on_stage.contest_office_id = contest_office_id
                position_on_stage.contest_office_we_vote_id = one_position["contest_office_we_vote_id"]
                position_on_stage.date_entered = one_position["date_entered"]
                position_on_stage.google_civic_candidate_name = google_civic_candidate_name
                position_on_stage.google_civic_election_id = one_position["google_civic_election_id"]
                position_on_stage.more_info_url = one_position["more_info_url"]
                position_on_stage.organization_id = organization_id
                position_on_stage.organization_we_vote_id = one_position["organization_we_vote_id"]
                position_on_stage.stance = one_position["stance"]
                position_on_stage.statement_text = one_position["statement_text"]
                position_on_stage.statement_html = one_position["statement_html"]
            else:
                # Create new
                position_on_stage = PositionEntered(
                    we_vote_id=one_position["we_vote_id"],
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=one_position["candidate_campaign_we_vote_id"],
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=one_position["contest_measure_we_vote_id"],
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=one_position["contest_office_we_vote_id"],
                    date_entered=one_position["date_entered"],
                    google_civic_candidate_name=google_civic_candidate_name,
                    google_civic_election_id=one_position["google_civic_election_id"],
                    more_info_url=one_position["more_info_url"],
                    organization_id=organization_id,
                    organization_we_vote_id=one_position["organization_we_vote_id"],
                    stance=one_position["stance"],
                    statement_html=one_position["statement_html"],
                    statement_text=one_position["statement_text"],
                )

            position_on_stage.ballot_item_display_name = one_position["ballot_item_display_name"]
            position_on_stage.ballot_item_image_url_https = one_position["ballot_item_image_url_https"]
            position_on_stage.ballot_item_twitter_handle = one_position["ballot_item_twitter_handle"]
            position_on_stage.from_scraper = one_position["from_scraper"]
            position_on_stage.date_last_changed = one_position["date_last_changed"]
            position_on_stage.organization_certified = one_position["organization_certified"]
            position_on_stage.politician_id = politician_id
            position_on_stage.politician_we_vote_id = one_position["politician_we_vote_id"]
            position_on_stage.public_figure_we_vote_id = one_position["public_figure_we_vote_id"]
            position_on_stage.speaker_display_name = one_position["speaker_display_name"]
            position_on_stage.speaker_image_url_https = one_position["speaker_image_url_https"]
            position_on_stage.speaker_twitter_handle = one_position["speaker_twitter_handle"]
            position_on_stage.tweet_source_id = one_position["tweet_source_id"]
            position_on_stage.twitter_user_entered_position = one_position["twitter_user_entered_position"]
            position_on_stage.volunteer_certified = one_position["volunteer_certified"]
            position_on_stage.vote_smart_rating = one_position["vote_smart_rating"]
            position_on_stage.vote_smart_rating_id = one_position["vote_smart_rating_id"]
            position_on_stage.vote_smart_rating_name = one_position["vote_smart_rating_name"]
            position_on_stage.vote_smart_time_span = one_position["vote_smart_time_span"]
            position_on_stage.voter_entering_position = one_position["voter_entering_position"]
            position_on_stage.voter_id = voter_id
            position_on_stage.voter_we_vote_id = one_position["voter_we_vote_id"]

            position_on_stage.save()
            if position_on_stage_found:
                # Update
                positions_updated += 1
            else:
                # New
                positions_saved += 1
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            positions_not_processed += 1

    positions_results = {
        'success': True,
        'status': "POSITIONS_IMPORT_PROCESS_COMPLETE",
        'saved': positions_saved,
        'updated': positions_updated,
        'not_processed': positions_not_processed,
    }
    return positions_results


# We retrieve the position for this voter for one ballot item. Could just be the stance, but for now we are
# retrieving the entire position
def voter_position_retrieve_for_api(voter_device_id, office_we_vote_id, candidate_we_vote_id, measure_we_vote_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if positive_value_exists(office_we_vote_id):
        kind_of_ballot_item = OFFICE
        ballot_item_we_vote_id = office_we_vote_id
    elif positive_value_exists(candidate_we_vote_id):
        kind_of_ballot_item = CANDIDATE
        ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_we_vote_id):
        kind_of_ballot_item = MEASURE
        ballot_item_we_vote_id = candidate_we_vote_id
    else:
        kind_of_ballot_item = ''
        ballot_item_we_vote_id = ''

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                  False,
            'position_id':              0,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_we_vote_id = office_we_vote_id.strip()
    candidate_we_vote_id = candidate_we_vote_id.strip()
    measure_we_vote_id = measure_we_vote_id.strip()

    if not positive_value_exists(office_we_vote_id) and \
            not positive_value_exists(candidate_we_vote_id) and \
            not positive_value_exists(measure_we_vote_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "POSITION_RETRIEVE_MISSING_AT_LEAST_ONE_BALLOT_ITEM_ID",
            'success':                  False,
            'position_id':              0,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionEnteredManager()

    if positive_value_exists(office_we_vote_id):
        results = position_manager.retrieve_voter_contest_office_position_with_we_vote_id(
            voter_id, office_we_vote_id)

    elif positive_value_exists(candidate_we_vote_id):
        results = position_manager.retrieve_voter_candidate_campaign_position_with_we_vote_id(
            voter_id, candidate_we_vote_id)

    elif positive_value_exists(measure_we_vote_id):
        results = position_manager.retrieve_voter_contest_measure_position_with_we_vote_id(
            voter_id, measure_we_vote_id)

    if results['position_found']:
        position = results['position']
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'is_support':               results['is_support'],
            'is_oppose':                results['is_oppose'],
            'is_information_only':      results['is_information_only'],
            'google_civic_election_id': position.google_civic_election_id,
            'office_we_vote_id':        position.contest_office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   results['status'],
            'success':                  True,
            'position_id':              0,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


# We retrieve the position for this voter for one ballot item. Could just be the stance, but for now we are
# retrieving the entire position
def voter_all_positions_retrieve_for_api(voter_device_id, google_civic_election_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':                   "VOTER_DEVICE_ID_NOT_VALID-VOTER_ALL_POSITIONS",
            'success':                  False,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_ALL_POSITIONS",
            'success':                  False,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    voter_we_vote_id = ''

    results = position_list_manager.retrieve_all_positions_for_voter_simple(voter_id, voter_we_vote_id,
                                                                            google_civic_election_id)

    if results['position_list_found']:
        position_list = results['position_list']
        json_data = {
            'status':                   results['status'],
            'success':                  True,
            'position_list_found':      True,
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   "VOTER_POSITIONS_NOT_FOUND-NONE_EXIST",
            'success':                  True,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_comment_save_for_api(
        voter_device_id, position_id, position_we_vote_id,
        google_civic_election_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        statement_text,
        statement_html
        ):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_POSITION_COMMENT",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data

    voter = voter_results['voter']
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    existing_unique_identifier_found = positive_value_exists(position_id) \
        or positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(voter_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(voter_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data

    position_manager = PositionEnteredManager()
    save_results = position_manager.update_or_create_position(
        position_id=position_id,
        position_we_vote_id=position_we_vote_id,
        voter_we_vote_id=voter.we_vote_id,
        google_civic_election_id=google_civic_election_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html,
    )

    if save_results['success']:
        position = save_results['position']
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'new_position_created':     save_results['new_position_created'],
            'is_support':               position.is_support(),
            'is_oppose':                position.is_oppose(),
            'is_information_only':      position.is_information_only(),
            'google_civic_election_id': position.google_civic_election_id,
            'office_we_vote_id':        position.contest_office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'last_updated':             position.last_updated(),
        }
        return json_data
    else:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data
