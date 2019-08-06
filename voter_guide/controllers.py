# voter_guide/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import OFFICE, CANDIDATE, MEASURE
from candidate.controllers import retrieve_candidate_list_for_all_upcoming_elections
from candidate.models import CandidateCampaignManager, CandidateCampaignListManager
from config.base import get_environment_variable
import copy
from django.http import HttpResponse
from election.controllers import retrieve_upcoming_election_id_list
from election.models import ElectionManager
from follow.models import FollowOrganizationList, FollowIssueList, FOLLOWING
from itertools import chain
from issue.models import OrganizationLinkToIssueList
import json
from measure.controllers import add_measure_name_alternatives_to_measure_list_light, \
    retrieve_measure_list_for_all_upcoming_elections
from measure.models import ContestMeasureList, ContestMeasureManager
from office.models import ContestOfficeManager
from organization.controllers import organization_follow_or_unfollow_or_ignore, \
    push_organization_data_to_other_table_caches, \
    refresh_organization_data_from_master_tables
from organization.models import OrganizationManager, OrganizationListManager, INDIVIDUAL
from pledge_to_vote.models import PledgeToVoteManager
from position.controllers import retrieve_ballot_item_we_vote_ids_for_organizations_to_follow, \
    retrieve_ballot_item_we_vote_ids_for_organization_static
from position.models import ANY_STANCE, INFORMATION_ONLY, OPPOSE, \
    PositionEntered, PositionManager, PositionListManager, SUPPORT
from voter.models import fetch_voter_id_from_voter_device_link, fetch_voter_we_vote_id_from_voter_device_link, \
    fetch_voter_we_vote_id_from_voter_id, VoterManager
from voter_guide.models import ENDORSEMENTS_FOR_CANDIDATE, ORGANIZATION_ENDORSING_CANDIDATES, UNKNOWN_TYPE, \
    VoterGuide, VoterGuideListManager, VoterGuideManager, \
    VoterGuidePossibility, VoterGuidePossibilityManager, VoterGuidePossibilityPosition
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists, \
    process_request_from_master, is_link_to_video

logger = wevote_functions.admin.get_logger(__name__)

VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def convert_candidate_endorsement_list_light_to_possible_endorsement_list(endorsement_list_light):
    status = ""
    success = True
    possible_endorsement_list = []
    possible_endorsement_list_found = False
    # one_endorsement = {
    #     'ballot_item_display_name': candidate.display_candidate_name(),
    #     'candidate_we_vote_id': candidate.we_vote_id,
    #     'google_civic_election_id': candidate.google_civic_election_id,
    #     'office_we_vote_id': candidate.contest_office_we_vote_id,
    #     'measure_we_vote_id': '',
    # }

    number_index = 1
    for one_endorsement in endorsement_list_light:
        if not positive_value_exists(one_endorsement['ballot_item_display_name']):
            continue
        possible_endorsement = {
            'ballot_item_name': one_endorsement['ballot_item_display_name'],
            'candidate_we_vote_id': one_endorsement['candidate_we_vote_id'],
            'google_civic_election_id': one_endorsement['google_civic_election_id'],
            'measure_we_vote_id': one_endorsement['measure_we_vote_id'],
            'more_info_url': "",
            'organization_we_vote_id': "",
            'possibility_position_number': str(number_index),
            'possibility_should_be_deleted': False,
            'possibility_should_be_ignored': False,
            'position_should_be_removed': False,
            'position_stance': "SUPPORT",
            'statement_text': "",
        }
        possible_endorsement_list.append(possible_endorsement)
        number_index += 1

    if len(possible_endorsement_list):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':          possible_endorsement_list,
        'possible_endorsement_list_found':    possible_endorsement_list_found,
    }
    return results


def convert_organization_endorsement_list_light_to_possible_endorsement_list(endorsement_list_light):
    status = ""
    success = True
    possible_endorsement_list = []
    possible_endorsement_list_found = False
    # one_endorsement = {
    #     'ballot_item_display_name': candidate.display_candidate_name(),
    #     'candidate_we_vote_id': candidate.we_vote_id,
    #     'google_civic_election_id': candidate.google_civic_election_id,
    #     'office_we_vote_id': candidate.contest_office_we_vote_id,
    #     'measure_we_vote_id': '',
    # }

    number_index = 1
    for one_endorsement in endorsement_list_light:
        if 'organization_we_vote_id' not in one_endorsement \
                or not positive_value_exists(one_endorsement['organization_we_vote_id']):
            continue
        possible_endorsement = {
            'ballot_item_name': "",
            'candidate_we_vote_id': one_endorsement['candidate_we_vote_id'],
            'google_civic_election_id': "",
            'measure_we_vote_id': "",
            'more_info_url': "",
            'organization_name': one_endorsement['organization_name'],
            'organization_website': one_endorsement['organization_website'],
            'organization_we_vote_id': one_endorsement['organization_we_vote_id'],
            'possibility_position_number': str(number_index),
            'possibility_should_be_deleted': False,
            'possibility_should_be_ignored': False,
            'position_should_be_removed': False,
            'position_stance': "SUPPORT",
            'statement_text': "",
        }
        possible_endorsement_list.append(possible_endorsement)
        number_index += 1

    if len(possible_endorsement_list):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':          possible_endorsement_list,
        'possible_endorsement_list_found':    possible_endorsement_list_found,
    }
    return results


def augment_with_voter_guide_possibility_position_data(voter_guide_possibility_list):
    # Identify how many endorsements already have positions stored
    voter_guide_possibility_list_modified = []
    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    for one_voter_guide_possibility in voter_guide_possibility_list:
        one_voter_guide_possibility.number_of_endorsements_with_position = 0
        possible_endorsement_list = []
        possible_endorsement_list_found = False
        google_civic_election_id_list = []
        # (ORGANIZATION_ENDORSING_CANDIDATES, 'Organization or News Website Endorsing Candidates'),
        # (ENDORSEMENTS_FOR_CANDIDATE, 'List of Endorsements for One Candidate'),
        # (UNKNOWN_TYPE, 'List of Endorsements for One Candidate'),
        if one_voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES or one_voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE:
            results = extract_voter_guide_possibility_position_list_from_database(one_voter_guide_possibility)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

                # Match incoming endorsements to candidates already in the database
                results = match_endorsement_list_with_candidates_in_database(
                    possible_endorsement_list, google_civic_election_id_list)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                    possible_endorsement_list_found = True
                # Match incoming endorsements to measures already in the database
                results = match_endorsement_list_with_measures_in_database(
                    possible_endorsement_list, google_civic_election_id_list)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                    possible_endorsement_list_found = True
        elif one_voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE:
            results = extract_voter_guide_possibility_position_list_from_database(one_voter_guide_possibility)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

                # Match incoming endorsements to candidates already in the database
                results = match_endorsement_list_with_candidates_in_database(
                    possible_endorsement_list, google_civic_election_id_list)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                    possible_endorsement_list_found = True

        if possible_endorsement_list_found:
            one_voter_guide_possibility.number_of_ballot_items = \
                voter_guide_possibility_manager.number_of_ballot_items(one_voter_guide_possibility.id)
            one_voter_guide_possibility.number_of_ballot_items_not_matched = \
                voter_guide_possibility_manager.number_of_ballot_items_not_matched(one_voter_guide_possibility.id)
            one_voter_guide_possibility.number_of_candidates_in_database = \
                voter_guide_possibility_manager.number_of_candidates_in_database(one_voter_guide_possibility.id)
            one_voter_guide_possibility.number_of_measures_in_database = \
                voter_guide_possibility_manager.number_of_measures_in_database(one_voter_guide_possibility.id)
            one_voter_guide_possibility.positions_ready_to_save_as_batch = \
                voter_guide_possibility_manager.positions_ready_to_save_as_batch(one_voter_guide_possibility)
            for one_possible_endorsement in possible_endorsement_list:
                if 'candidate_we_vote_id' in one_possible_endorsement \
                        and positive_value_exists(one_possible_endorsement['candidate_we_vote_id']):
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=one_voter_guide_possibility.organization_we_vote_id,
                        candidate_campaign_we_vote_id=one_possible_endorsement['candidate_we_vote_id'])
                    position_count = position_exists_query.count()
                    if positive_value_exists(position_count):
                        one_voter_guide_possibility.number_of_endorsements_with_position += 1
                elif 'measure_we_vote_id' in one_possible_endorsement \
                        and positive_value_exists(one_possible_endorsement['measure_we_vote_id']):
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=one_voter_guide_possibility.organization_we_vote_id,
                        contest_measure_we_vote_id=one_possible_endorsement['measure_we_vote_id'])
                    position_count = position_exists_query.count()
                    if positive_value_exists(position_count):
                        one_voter_guide_possibility.number_of_endorsements_with_position += 1
        voter_guide_possibility_list_modified.append(one_voter_guide_possibility)
    return voter_guide_possibility_list_modified


def convert_list_of_names_to_possible_endorsement_list(ballot_items_list, starting_endorsement_number=1):
    status = ""
    success = True
    possible_endorsement_list = []
    possible_endorsement_list_found = False

    number_index = starting_endorsement_number
    for one_name in ballot_items_list:
        if not positive_value_exists(one_name):
            continue
        possible_endorsement = {
            'ballot_item_name': one_name,
            'candidate_we_vote_id': "",
            'statement_text': "",
            'google_civic_election_id': 0,
            'measure_we_vote_id': "",
            'more_info_url': "",
            'organization_name': "",
            'organization_we_vote_id': "",
            'possibility_position_number': str(number_index),
            'possibility_should_be_deleted': False,
            'possibility_should_be_ignored': False,
            'position_should_be_removed': False,
            'position_stance': "SUPPORT",
        }
        possible_endorsement_list.append(possible_endorsement)
        number_index += 1

    if len(possible_endorsement_list):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':          possible_endorsement_list,
        'possible_endorsement_list_found':    possible_endorsement_list_found,
    }
    return results


def extract_import_position_list_from_voter_guide_possibility(voter_guide_possibility):
    """
    Take the data from the VoterGuidePossibility database and convert it to the format we use for the Import Export
    Batch System.
    :param voter_guide_possibility:
    :return:
    """
    status = ""
    success = True
    position_json_list = []
    position_json_list_found = False

    more_info_url = voter_guide_possibility.voter_guide_possibility_url
    # DEBUG=1 Phase out state_code for entire voter_guide_possibility?
    state_code = voter_guide_possibility.state_code \
        if positive_value_exists(voter_guide_possibility.state_code) else ""

    # ######################
    # If we are starting from a single organization endorsing many candidates,
    # we store that organization information once
    if voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES \
            or voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE:
        organization_name = voter_guide_possibility.organization_name \
            if positive_value_exists(voter_guide_possibility.organization_name) else ""
        organization_we_vote_id = voter_guide_possibility.organization_we_vote_id \
            if positive_value_exists(voter_guide_possibility.organization_we_vote_id) else ""
        organization_twitter_handle = voter_guide_possibility.organization_twitter_handle \
            if positive_value_exists(voter_guide_possibility.organization_twitter_handle) else ""
    else:
        organization_name = ""
        organization_we_vote_id = ""
        organization_twitter_handle = ""

    # ######################
    # If we are starting from a single candidate endorsed by many "organizations" (which may be people),
    # we store this candidate information once
    if voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE:
        candidate_name = voter_guide_possibility.candidate_name \
            if positive_value_exists(voter_guide_possibility.candidate_name) else ""
        candidate_twitter_handle = voter_guide_possibility.candidate_twitter_handle \
            if positive_value_exists(voter_guide_possibility.candidate_twitter_handle) else ""
        candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id \
            if positive_value_exists(voter_guide_possibility.candidate_we_vote_id) else ""

        contest_office_name = ""
        candidate_manager = CandidateCampaignManager()
        results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        if results['candidate_campaign_found']:
            candidate = results['candidate_campaign']
            contest_office_name = candidate.contest_office_name
    else:
        candidate_name = ""
        candidate_twitter_handle = ""
        candidate_we_vote_id = ""
        contest_office_name = ""

    possibility_position_query = VoterGuidePossibilityPosition.objects.filter(
        voter_guide_possibility_parent_id=voter_guide_possibility.id).order_by('possibility_position_number')
    possibility_position_list = list(possibility_position_query)
    for possibility_position in possibility_position_list:
        if positive_value_exists(possibility_position.more_info_url):
            more_info_url = possibility_position.more_info_url
        else:
            more_info_url = voter_guide_possibility.voter_guide_possibility_url
        if voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES \
                or voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE:
            # The organization variables have been set above
            # Note that UNKNOWN_TYPE might be set if we are looking at organization
            # ######################
            # If we are starting from a single organization endorsing many candidates,
            # we store that candidate information once
            if positive_value_exists(possibility_position.candidate_we_vote_id):
                candidate_name = possibility_position.ballot_item_name
                position_json = {
                    'candidate_name': candidate_name,
                    'candidate_we_vote_id': possibility_position.candidate_we_vote_id,
                    'candidate_twitter_handle': possibility_position.candidate_twitter_handle,
                    'google_civic_election_id': possibility_position.google_civic_election_id,
                    'more_info_url': more_info_url,
                    'organization_name': organization_name,
                    'organization_we_vote_id': organization_we_vote_id,
                    'organization_twitter_handle': organization_twitter_handle,
                    'stance': possibility_position.position_stance,
                    'statement_text': possibility_position.statement_text,
                    'state_code': state_code,
                }
                position_json_list.append(position_json)
            elif positive_value_exists(possibility_position.measure_we_vote_id):
                measure_title = possibility_position.ballot_item_name
                position_json = {
                    'google_civic_election_id': possibility_position.google_civic_election_id,
                    'measure_title': measure_title,
                    'measure_we_vote_id': possibility_position.measure_we_vote_id,
                    'more_info_url': more_info_url,
                    'organization_name': organization_name,
                    'organization_we_vote_id': organization_we_vote_id,
                    'organization_twitter_handle': organization_twitter_handle,
                    'stance': possibility_position.position_stance,
                    'statement_text': possibility_position.statement_text,
                    'state_code': state_code,
                }
                position_json_list.append(position_json)
            else:
                status += "MISSING_BOTH_CANDIDATE_AND_MEASURE_WE_VOTE_ID "
        elif voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE:
            # ######################
            # If we are starting from a single candidate endorsed by many "organizations" (which may be people),
            # we store the unique organization information in the VoterGuidePossibilityPosition table
            organization_name = possibility_position.organization_name \
                if positive_value_exists(possibility_position.organization_name) else ""
            organization_we_vote_id = possibility_position.organization_we_vote_id \
                if positive_value_exists(possibility_position.organization_we_vote_id) else ""
            organization_twitter_handle = possibility_position.organization_twitter_handle \
                if positive_value_exists(possibility_position.organization_twitter_handle) else ""
            position_json = {
                'candidate_name': candidate_name,
                'candidate_we_vote_id': candidate_we_vote_id,
                'candidate_twitter_handle': candidate_twitter_handle,
                'contest_office_name': contest_office_name,
                'google_civic_election_id': possibility_position.google_civic_election_id,
                'measure_we_vote_id': possibility_position.measure_we_vote_id,
                'more_info_url': more_info_url,
                'organization_name': organization_name,
                'organization_we_vote_id': organization_we_vote_id,
                'organization_twitter_handle': organization_twitter_handle,
                'stance': possibility_position.position_stance,
                'statement_text': possibility_position.statement_text,
                'state_code': state_code,
            }
            position_json_list.append(position_json)
        else:
            # This is an error condition which should not be reached
            status += "UNRECOGNIZED_VOTER_POSSIBILITY_TYPE "

    if len(position_json_list):
        position_json_list_found = True

    results = {
        'status':                   status,
        'success':                  success,
        'position_json_list':       position_json_list,
        'position_json_list_found': position_json_list_found,
    }
    return results


def extract_voter_guide_possibility_position_list_from_database(
        voter_guide_possibility, voter_guide_possibility_position_id=0):
    """
    Get voter_guide_possibility data from the database and put it into the Suggested Voter Guide system format we use
    :param voter_guide_possibility:
    :param voter_guide_possibility_position_id: This is included if we only want to retrieve one possible position
    :return:
    """
    status = ""
    success = True
    possible_endorsement_list = []
    possible_endorsement_list_found = False

    # DEBUG=1 Phase out state_code for entire voter_guide_possibility?
    state_code = voter_guide_possibility.state_code \
        if positive_value_exists(voter_guide_possibility.state_code) else ""
    # ######################
    # If we are starting from a single organization endorsing many candidates,
    # we store that organization information once
    if voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES \
            or voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE:
        organization_name = voter_guide_possibility.organization_name \
            if positive_value_exists(voter_guide_possibility.organization_name) else ""
        organization_we_vote_id = voter_guide_possibility.organization_we_vote_id \
            if positive_value_exists(voter_guide_possibility.organization_we_vote_id) else ""
        organization_twitter_handle = voter_guide_possibility.organization_twitter_handle \
            if positive_value_exists(voter_guide_possibility.organization_twitter_handle) else ""
    else:
        organization_name = ""
        organization_we_vote_id = ""
        organization_twitter_handle = ""

    # ######################
    # If we are starting from a single candidate endorsed by many "organizations" (which may be people),
    # we store this candidate information once
    if voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE:
        candidate_twitter_handle = voter_guide_possibility.candidate_twitter_handle \
            if positive_value_exists(voter_guide_possibility.candidate_twitter_handle) else ""
        candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id \
            if positive_value_exists(voter_guide_possibility.candidate_we_vote_id) else ""
        # candidate_manager = CandidateCampaignManager()
        # results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        # if results['candidate_campaign_found']:
        #     candidate = results['candidate_campaign']
        #     contest_office_name = candidate.contest_office_name
    else:
        # candidate_name = ""
        candidate_twitter_handle = ""
        candidate_we_vote_id = ""
        # contest_office_name = ""

    possibility_position_query = VoterGuidePossibilityPosition.objects.filter(
        voter_guide_possibility_parent_id=voter_guide_possibility.id).order_by('possibility_position_number')
    if positive_value_exists(voter_guide_possibility_position_id):
        possibility_position_query = possibility_position_query.filter(id=voter_guide_possibility_position_id)
    possibility_position_list = list(possibility_position_query)
    for possibility_position in possibility_position_list:
        if positive_value_exists(possibility_position.more_info_url):
            more_info_url = possibility_position.more_info_url
        else:
            more_info_url = voter_guide_possibility.voter_guide_possibility_url
        if voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES \
                or voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE:
            # The organization variables have been set above
            # Note that UNKNOWN_TYPE might be set if we are looking at organization
            # ######################
            # If we are starting from a single organization endorsing many candidates,
            # we refresh the candidate information from the VoterGuidePossibilityPosition table with each loop
            candidate_we_vote_id = possibility_position.candidate_we_vote_id \
                if positive_value_exists(possibility_position.candidate_we_vote_id) else ""
            candidate_twitter_handle = possibility_position.candidate_twitter_handle \
                if positive_value_exists(possibility_position.candidate_twitter_handle) else ""
        elif voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE:
            # ######################
            # If we are starting from a single candidate endorsed by many "organizations" (which may be people),
            # we refresh the organization information from the VoterGuidePossibilityPosition table with each loop
            organization_name = possibility_position.organization_name \
                if positive_value_exists(possibility_position.organization_name) else ""
            organization_we_vote_id = possibility_position.organization_we_vote_id \
                if positive_value_exists(possibility_position.organization_we_vote_id) else ""
            organization_twitter_handle = possibility_position.organization_twitter_handle \
                if positive_value_exists(possibility_position.organization_twitter_handle) else ""
        else:
            status += "PROBLEM-SHOULD_NOT_BE_HERE "
            candidate_we_vote_id = ""
            organization_name = ""
            organization_we_vote_id = ""
            organization_twitter_handle = ""

        position_json = {
            'possibility_position_id': possibility_position.id,
            'ballot_item_name': possibility_position.ballot_item_name,
            'candidate_we_vote_id': candidate_we_vote_id,
            'candidate_twitter_handle': candidate_twitter_handle,
            # 'contest_office_name': contest_office_name,
            'google_civic_election_id': possibility_position.google_civic_election_id,
            'measure_we_vote_id': possibility_position.measure_we_vote_id,
            'more_info_url': more_info_url,
            'organization_name': organization_name,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_twitter_handle': organization_twitter_handle,
            'possibility_position_number': possibility_position.possibility_position_number,
            'possibility_should_be_deleted': False,
            'possibility_should_be_ignored': possibility_position.possibility_should_be_ignored,
            'position_should_be_removed': possibility_position.position_should_be_removed,
            'position_we_vote_id': possibility_position.position_we_vote_id,
            'position_stance': possibility_position.position_stance,
            'statement_text': possibility_position.statement_text,
            'state_code': state_code,
        }
        possible_endorsement_list.append(position_json)

    if len(possible_endorsement_list):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        possible_endorsement_list,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def augment_candidate_possible_position_data(
        possible_endorsement, google_civic_election_id_list, limit_to_this_state_code="",
        all_possible_candidates=[], attach_objects=True):
    status = ""
    success = True
    candidate_campaign_manager = CandidateCampaignManager()
    candidate_campaign_list_manager = CandidateCampaignListManager()
    contest_office_manager = ContestOfficeManager()

    possible_endorsement_matched = False
    possible_endorsement_return_list = []
    possible_endorsement_count = 0
    if 'candidate_we_vote_id' in possible_endorsement \
            and positive_value_exists(possible_endorsement['candidate_we_vote_id']):
        possible_endorsement_matched = True
        results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
            possible_endorsement['candidate_we_vote_id'])
        if results['candidate_campaign_found']:
            candidate = results['candidate_campaign']
            if positive_value_exists(attach_objects):
                possible_endorsement['candidate'] = candidate
            possible_endorsement['ballot_item_name'] = candidate.display_candidate_name()
            possible_endorsement['google_civic_election_id'] = candidate.google_civic_election_id
            possible_endorsement['office_name'] = candidate.contest_office_name
            possible_endorsement['office_we_vote_id'] = candidate.contest_office_we_vote_id
            possible_endorsement['political_party'] = candidate.party
            possible_endorsement['ballot_item_image_url_https_large'] = \
                candidate.we_vote_hosted_profile_image_url_large
            possible_endorsement['ballot_item_image_url_https_medium'] = \
                candidate.we_vote_hosted_profile_image_url_medium
            if not positive_value_exists(possible_endorsement['google_civic_election_id']) \
                    and positive_value_exists(candidate.contest_office_we_vote_id):
                possible_endorsement['google_civic_election_id'] = \
                    contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
                        candidate.contest_office_we_vote_id)
        possible_endorsement_count += 1
        possible_endorsement_return_list.append(possible_endorsement)
    elif 'ballot_item_name' in possible_endorsement and \
            positive_value_exists(possible_endorsement['ballot_item_name']):
        possible_endorsement_matched = True
        # If here search for possible candidate matches
        matching_results = candidate_campaign_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list, limit_to_this_state_code, '', possible_endorsement['ballot_item_name'])

        if matching_results['candidate_found']:
            candidate = matching_results['candidate']

            # If one candidate found, add we_vote_id here
            possible_endorsement['candidate_we_vote_id'] = candidate.we_vote_id
            if positive_value_exists(attach_objects):
                possible_endorsement['candidate'] = candidate
            possible_endorsement['ballot_item_name'] = candidate.display_candidate_name()
            possible_endorsement['google_civic_election_id'] = candidate.google_civic_election_id
            possible_endorsement['office_name'] = candidate.contest_office_name
            possible_endorsement['office_we_vote_id'] = candidate.contest_office_we_vote_id
            possible_endorsement['political_party'] = candidate.party
            possible_endorsement['ballot_item_image_url_https_large'] = \
                candidate.we_vote_hosted_profile_image_url_large
            possible_endorsement['ballot_item_image_url_https_medium'] = \
                candidate.we_vote_hosted_profile_image_url_medium
            if not positive_value_exists(possible_endorsement['google_civic_election_id']) \
                    and positive_value_exists(candidate.contest_office_we_vote_id):
                possible_endorsement['google_civic_election_id'] = \
                    contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
                        candidate.contest_office_we_vote_id)
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)
        elif matching_results['candidate_list_found']:
            # Keep the current option
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)
            possible_endorsement_matched = True
            # ...and add entries for other possible matches
            status += "MULTIPLE_CANDIDATES_FOUND "
            candidate_list = matching_results['candidate_list']
            for candidate in candidate_list:
                possible_endorsement_copy = copy.deepcopy(possible_endorsement)
                # Reset the possibility position id
                possible_endorsement_copy['possibility_position_id'] = 0
                # If one candidate found, add we_vote_id here
                possible_endorsement_copy['candidate_we_vote_id'] = candidate.we_vote_id
                if positive_value_exists(attach_objects):
                    possible_endorsement_copy['candidate'] = candidate
                possible_endorsement_copy['ballot_item_name'] = candidate.display_candidate_name()
                possible_endorsement_copy['google_civic_election_id'] = candidate.google_civic_election_id
                possible_endorsement_copy['office_name'] = candidate.contest_office_name
                possible_endorsement_copy['office_we_vote_id'] = candidate.contest_office_we_vote_id
                possible_endorsement_copy['political_party'] = candidate.party
                possible_endorsement_copy['ballot_item_image_url_https_large'] = \
                    candidate.we_vote_hosted_profile_image_url_large
                possible_endorsement_copy['ballot_item_image_url_https_medium'] = \
                    candidate.we_vote_hosted_profile_image_url_medium
                if not positive_value_exists(possible_endorsement_copy['google_civic_election_id']) \
                        and positive_value_exists(candidate.contest_office_we_vote_id):
                    possible_endorsement_copy['google_civic_election_id'] = \
                        contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
                            candidate.contest_office_we_vote_id)
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement_copy)
        elif not positive_value_exists(matching_results['success']):
            possible_endorsement_matched = True
            status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-NO_SUCCESS "
            status += matching_results['status']
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)
        else:
            status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-CANDIDATE_NOT_FOUND "

            # Now we want to do a reverse search, where we cycle through all upcoming candidates and search
            # within the incoming text for a known candidate name
            for one_endorsement_light in all_possible_candidates:
                if one_endorsement_light['ballot_item_display_name'] in possible_endorsement['ballot_item_name']:
                    possible_endorsement['candidate_we_vote_id'] = one_endorsement_light['candidate_we_vote_id']
                    possible_endorsement['ballot_item_name'] = one_endorsement_light['ballot_item_display_name']
                    possible_endorsement['google_civic_election_id'] = \
                        one_endorsement_light['google_civic_election_id']
                    matching_results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                        possible_endorsement['candidate_we_vote_id'])

                    if matching_results['candidate_campaign_found']:
                        candidate = matching_results['candidate_campaign']

                        # If one candidate found, add we_vote_id here
                        possible_endorsement['candidate_we_vote_id'] = candidate.we_vote_id
                        if positive_value_exists(attach_objects):
                            possible_endorsement['candidate'] = candidate
                        possible_endorsement['ballot_item_name'] = candidate.display_candidate_name()
                        possible_endorsement['google_civic_election_id'] = candidate.google_civic_election_id
                        possible_endorsement['office_name'] = candidate.contest_office_name
                        possible_endorsement['office_we_vote_id'] = candidate.contest_office_we_vote_id
                        possible_endorsement['political_party'] = candidate.party
                        possible_endorsement['ballot_item_image_url_https_large'] = \
                            candidate.we_vote_hosted_profile_image_url_large
                        possible_endorsement['ballot_item_image_url_https_medium'] = \
                            candidate.we_vote_hosted_profile_image_url_medium
                        if not positive_value_exists(possible_endorsement['google_civic_election_id']) \
                                and positive_value_exists(candidate.contest_office_we_vote_id):
                            possible_endorsement['google_civic_election_id'] = \
                                contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
                                    candidate.contest_office_we_vote_id)
                    possible_endorsement_matched = True
                    possible_endorsement_count += 1
                    possible_endorsement_return_list.append(possible_endorsement)
                    break

    if not possible_endorsement_matched:
        # We want to check 'alternate_names' candidate names in upcoming elections
        # (ex/ Candidate name with middle initial in alternate_names)
        #  against the possible endorsement ()
        # NOTE: one_endorsement_light is a candidate or measure for an upcoming election
        # NOTE: possible endorsement is one of the incoming new endorsements we are trying to match
        synonym_found = False
        for one_endorsement_light in all_possible_candidates:
            # Hanging off each ballot_item_dict is a alternate_names that includes
            #  shortened alternative names that we should check against decide_line_lower_case
            if 'alternate_names' in one_endorsement_light and \
                    positive_value_exists(one_endorsement_light['alternate_names']):
                alternate_names = one_endorsement_light['alternate_names']
                for ballot_item_display_name_alternate in alternate_names:
                    if ballot_item_display_name_alternate.lower() in \
                            possible_endorsement['ballot_item_name'].lower():
                        # Make a copy so we don't change the incoming object -- if we find multiple upcoming
                        # candidates that match, we should use them all
                        possible_endorsement_copy = copy.deepcopy(possible_endorsement)
                        possible_endorsement_copy['candidate_we_vote_id'] = \
                            one_endorsement_light['candidate_we_vote_id']
                        possible_endorsement_copy['ballot_item_name'] = \
                            one_endorsement_light['ballot_item_display_name']
                        possible_endorsement_copy['google_civic_election_id'] = \
                            one_endorsement_light['google_civic_election_id']
                        matching_results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                            possible_endorsement_copy['candidate_we_vote_id'])

                        if matching_results['candidate_campaign_found']:
                            candidate = matching_results['candidate_campaign']

                            # If one candidate found, augment the data if we can
                            if positive_value_exists(attach_objects):
                                possible_endorsement_copy['candidate'] = candidate
                            possible_endorsement_copy['ballot_item_name'] = candidate.candidate_name
                            possible_endorsement_copy['google_civic_election_id'] = candidate.google_civic_election_id
                            possible_endorsement_copy['office_name'] = candidate.contest_office_name
                            possible_endorsement_copy['office_we_vote_id'] = candidate.contest_office_we_vote_id
                            possible_endorsement_copy['political_party'] = candidate.party
                            possible_endorsement_copy['ballot_item_image_url_https_large'] = \
                                candidate.we_vote_hosted_profile_image_url_large
                            possible_endorsement_copy['ballot_item_image_url_https_medium'] = \
                                candidate.we_vote_hosted_profile_image_url_medium
                        synonym_found = True
                        possible_endorsement_count += 1
                        possible_endorsement_return_list.append(possible_endorsement_copy)
                        break
        if not synonym_found:
            # If an entry based on a synonym wasn't found, then store the original possibility
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_return_list': possible_endorsement_return_list,
        'possible_endorsement_count':       possible_endorsement_count,
    }
    return results


def augment_organization_possible_position_data(
        possible_endorsement, limit_to_this_state_code="",
        all_possible_candidates=[], attach_objects=True):
    status = ""
    success = True

    organization_manager = OrganizationManager()
    organization_list_manager = OrganizationListManager()

    possible_endorsement_matched = False
    possible_endorsement_return_list = []
    possible_endorsement_count = 0
    if 'organization_we_vote_id' in possible_endorsement \
            and positive_value_exists(possible_endorsement['organization_we_vote_id']):
        possible_endorsement_matched = True
        results = organization_manager.retrieve_organization_from_we_vote_id(
            possible_endorsement['organization_we_vote_id'])
        if results['organization_found']:
            organization = results['organization']
            if positive_value_exists(attach_objects):
                possible_endorsement['organization'] = organization
            possible_endorsement['organization_name'] = organization.organization_name
            possible_endorsement['organization_twitter_handle'] = organization.organization_twitter_handle
            possible_endorsement['organization_website'] = organization.organization_website
            possible_endorsement['we_vote_hosted_profile_image_url_large'] = \
                organization.we_vote_hosted_profile_image_url_large
            possible_endorsement['we_vote_hosted_profile_image_url_medium'] = \
                organization.we_vote_hosted_profile_image_url_medium
            possible_endorsement['we_vote_hosted_profile_image_url_tiny'] = \
                organization.we_vote_hosted_profile_image_url_tiny
        possible_endorsement_count += 1
        possible_endorsement_return_list.append(possible_endorsement)
    # DALE 2019-08-02 Not sure we want to search by name
    elif 'ballot_item_name' in possible_endorsement and \
            positive_value_exists(possible_endorsement['ballot_item_name']):
        pass
        # possible_endorsement_matched = True
        # # If here search for possible candidate matches
        # matching_results = organization_list_manager.retrieve_candidates_from_non_unique_identifiers(
        #     google_civic_election_id_list, limit_to_this_state_code, '', possible_endorsement['ballot_item_name'])
        #
        # if matching_results['candidate_found']:
        #     candidate = matching_results['candidate']
        #
        #     # If one candidate found, add we_vote_id here
        #     possible_endorsement['candidate_we_vote_id'] = candidate.we_vote_id
        #     if positive_value_exists(attach_objects):
        #         possible_endorsement['candidate'] = candidate
        #     possible_endorsement['ballot_item_name'] = candidate.display_candidate_name()
        #     possible_endorsement['google_civic_election_id'] = candidate.google_civic_election_id
        #     possible_endorsement['office_name'] = candidate.contest_office_name
        #     possible_endorsement['office_we_vote_id'] = candidate.contest_office_we_vote_id
        #     possible_endorsement['political_party'] = candidate.party
        #     possible_endorsement['ballot_item_image_url_https_large'] = \
        #         candidate.we_vote_hosted_profile_image_url_large
        #     possible_endorsement['ballot_item_image_url_https_medium'] = \
        #         candidate.we_vote_hosted_profile_image_url_medium
        #     if not positive_value_exists(possible_endorsement['google_civic_election_id']) \
        #             and positive_value_exists(candidate.contest_office_we_vote_id):
        #         possible_endorsement['google_civic_election_id'] = \
        #             contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
        #                 candidate.contest_office_we_vote_id)
        #     possible_endorsement_count += 1
        #     possible_endorsement_return_list.append(possible_endorsement)
        # elif matching_results['candidate_list_found']:
        #     # Keep the current option
        #     possible_endorsement_count += 1
        #     possible_endorsement_return_list.append(possible_endorsement)
        #     possible_endorsement_matched = True
        #     # ...and add entries for other possible matches
        #     status += "MULTIPLE_CANDIDATES_FOUND "
        #     candidate_list = matching_results['candidate_list']
        #     for candidate in candidate_list:
        #         possible_endorsement_copy = copy.deepcopy(possible_endorsement)
        #         # Reset the possibility position id
        #         possible_endorsement_copy['possibility_position_id'] = 0
        #         # If one candidate found, add we_vote_id here
        #         possible_endorsement_copy['candidate_we_vote_id'] = candidate.we_vote_id
        #         if positive_value_exists(attach_objects):
        #             possible_endorsement_copy['candidate'] = candidate
        #         possible_endorsement_copy['ballot_item_name'] = candidate.display_candidate_name()
        #         possible_endorsement_copy['google_civic_election_id'] = candidate.google_civic_election_id
        #         possible_endorsement_copy['office_name'] = candidate.contest_office_name
        #         possible_endorsement_copy['office_we_vote_id'] = candidate.contest_office_we_vote_id
        #         possible_endorsement_copy['political_party'] = candidate.party
        #         possible_endorsement_copy['ballot_item_image_url_https_large'] = \
        #             candidate.we_vote_hosted_profile_image_url_large
        #         possible_endorsement_copy['ballot_item_image_url_https_medium'] = \
        #             candidate.we_vote_hosted_profile_image_url_medium
        #         if not positive_value_exists(possible_endorsement_copy['google_civic_election_id']) \
        #                 and positive_value_exists(candidate.contest_office_we_vote_id):
        #             possible_endorsement_copy['google_civic_election_id'] = \
        #                 contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
        #                     candidate.contest_office_we_vote_id)
        #         possible_endorsement_count += 1
        #         possible_endorsement_return_list.append(possible_endorsement_copy)
        # elif not positive_value_exists(matching_results['success']):
        #     possible_endorsement_matched = True
        #     status += "AUGMENT_ORGANIZATION_FROM_NON_UNIQUE-NO_SUCCESS "
        #     status += matching_results['status']
        #     possible_endorsement_count += 1
        #     possible_endorsement_return_list.append(possible_endorsement)
        # else:
        #     status += "AUGMENT_ORGANIZATION_FROM_NON_UNIQUE-ORGANIZATION_NOT_FOUND "
        #
        #     Now we want to do a reverse search, where we cycle through all upcoming candidates and search
        #     within the incoming text for a known candidate name
        #     for one_endorsement_light in all_possible_candidates:
        #         if one_endorsement_light['ballot_item_display_name'] in possible_endorsement['ballot_item_name']:
        #             possible_endorsement['candidate_we_vote_id'] = one_endorsement_light['candidate_we_vote_id']
        #             possible_endorsement['ballot_item_name'] = one_endorsement_light['ballot_item_display_name']
        #             possible_endorsement['google_civic_election_id'] = \
        #                 one_endorsement_light['google_civic_election_id']
        #             matching_results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
        #                 possible_endorsement['candidate_we_vote_id'])
        #
        #             if matching_results['candidate_campaign_found']:
        #                 candidate = matching_results['candidate_campaign']
        #
        #                 # If one candidate found, add we_vote_id here
        #                 possible_endorsement['candidate_we_vote_id'] = candidate.we_vote_id
        #                 if positive_value_exists(attach_objects):
        #                     possible_endorsement['candidate'] = candidate
        #                 possible_endorsement['ballot_item_name'] = candidate.display_candidate_name()
        #                 possible_endorsement['google_civic_election_id'] = candidate.google_civic_election_id
        #                 possible_endorsement['office_name'] = candidate.contest_office_name
        #                 possible_endorsement['office_we_vote_id'] = candidate.contest_office_we_vote_id
        #                 possible_endorsement['political_party'] = candidate.party
        #                 possible_endorsement['ballot_item_image_url_https_large'] = \
        #                     candidate.we_vote_hosted_profile_image_url_large
        #                 possible_endorsement['ballot_item_image_url_https_medium'] = \
        #                     candidate.we_vote_hosted_profile_image_url_medium
        #                 if not positive_value_exists(possible_endorsement['google_civic_election_id']) \
        #                         and positive_value_exists(candidate.contest_office_we_vote_id):
        #                     possible_endorsement['google_civic_election_id'] = \
        #                         contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
        #                             candidate.contest_office_we_vote_id)
        #             possible_endorsement_matched = True
        #             possible_endorsement_count += 1
        #             possible_endorsement_return_list.append(possible_endorsement)
        #             break

    # if not possible_endorsement_matched:
    #     # We want to check 'alternate_names' candidate names in upcoming elections
    #     # (ex/ Candidate name with middle initial in alternate_names)
    #     #  against the possible endorsement ()
    #     # NOTE: one_endorsement_light is a candidate or measure for an upcoming election
    #     # NOTE: possible endorsement is one of the incoming new endorsements we are trying to match
    #     synonym_found = False
    #     for one_endorsement_light in all_possible_candidates:
    #         # Hanging off each ballot_item_dict is a alternate_names that includes
    #         #  shortened alternative names that we should check against decide_line_lower_case
    #         if 'alternate_names' in one_endorsement_light and \
    #                 positive_value_exists(one_endorsement_light['alternate_names']):
    #             alternate_names = one_endorsement_light['alternate_names']
    #             for ballot_item_display_name_alternate in alternate_names:
    #                 if ballot_item_display_name_alternate.lower() in \
    #                         possible_endorsement['ballot_item_name'].lower():
    #                     # Make a copy so we don't change the incoming object -- if we find multiple upcoming
    #                     # candidates that match, we should use them all
    #                     possible_endorsement_copy = copy.deepcopy(possible_endorsement)
    #                     possible_endorsement_copy['candidate_we_vote_id'] = \
    #                         one_endorsement_light['candidate_we_vote_id']
    #                     possible_endorsement_copy['ballot_item_name'] = \
    #                         one_endorsement_light['ballot_item_display_name']
    #                     possible_endorsement_copy['google_civic_election_id'] = \
    #                         one_endorsement_light['google_civic_election_id']
    #                     matching_results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
    #                         possible_endorsement_copy['candidate_we_vote_id'])
    #
    #                     if matching_results['candidate_campaign_found']:
    #                         candidate = matching_results['candidate_campaign']
    #
    #                         # If one candidate found, augment the data if we can
    #                         if positive_value_exists(attach_objects):
    #                             possible_endorsement_copy['candidate'] = candidate
    #                         possible_endorsement_copy['ballot_item_name'] = candidate.candidate_name
    #                         possible_endorsement_copy['google_civic_election_id'] = candidate.google_civic_election_id
    #                         possible_endorsement_copy['office_name'] = candidate.contest_office_name
    #                         possible_endorsement_copy['office_we_vote_id'] = candidate.contest_office_we_vote_id
    #                         possible_endorsement_copy['political_party'] = candidate.party
    #                         possible_endorsement_copy['ballot_item_image_url_https_large'] = \
    #                             candidate.we_vote_hosted_profile_image_url_large
    #                         possible_endorsement_copy['ballot_item_image_url_https_medium'] = \
    #                             candidate.we_vote_hosted_profile_image_url_medium
    #                     synonym_found = True
    #                     possible_endorsement_count += 1
    #                     possible_endorsement_return_list.append(possible_endorsement_copy)
    #                     break
    #     if not synonym_found:
    #         # If an entry based on a synonym wasn't found, then store the original possibility
    #         possible_endorsement_count += 1
    #         possible_endorsement_return_list.append(possible_endorsement)

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_return_list': possible_endorsement_return_list,
        'possible_endorsement_count':       possible_endorsement_count,
    }
    return results


def match_endorsement_list_with_candidates_in_database(
        possible_endorsement_list,
        google_civic_election_id_list,
        state_code='',
        all_possible_candidates_list_light=[],
        attach_objects=True):
    """

    :param possible_endorsement_list:
    :param google_civic_election_id_list:
    :param state_code:
    :param all_possible_candidates_list_light: Only use when trying to match to new candidates
    :param attach_objects:
    :return:
    """
    status = ""
    success = True
    possible_endorsement_list_found = False

    possible_endorsement_list_modified = []
    for possible_endorsement in possible_endorsement_list:
        results = augment_candidate_possible_position_data(
            possible_endorsement, google_civic_election_id_list, limit_to_this_state_code=state_code,
            all_possible_candidates=all_possible_candidates_list_light, attach_objects=attach_objects)
        if results['possible_endorsement_count'] > 0:
            possible_endorsement_list_modified += results['possible_endorsement_return_list']

    if len(possible_endorsement_list_modified):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        possible_endorsement_list_modified,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def match_endorsement_list_with_measures_in_database(
        possible_endorsement_list, google_civic_election_id_list, state_code='', all_possible_measures_list_light=[],
        attach_objects=True):
    """

    :param possible_endorsement_list: This is the list of measures and candidates that were either found on the
      page or entered manually (ex/ "Prop 1")
    :param google_civic_election_id_list:
    :param state_code:
    :param all_possible_measures_list_light: This is the list of actual candidates or measures in the database
    :param attach_objects: Should we attach objects that won't convert to json?
    :return:
    """
    status = ""
    success = True
    possible_endorsement_list_found = False

    possible_endorsement_list_modified = []
    measure_manager = ContestMeasureManager()
    measure_list_manager = ContestMeasureList()
    for possible_endorsement in possible_endorsement_list:
        possible_endorsement_matched = False
        if 'measure_we_vote_id' in possible_endorsement \
                and positive_value_exists(possible_endorsement['measure_we_vote_id']):
            results = measure_manager.retrieve_contest_measure_from_we_vote_id(
                possible_endorsement['measure_we_vote_id'])
            if results['contest_measure_found']:
                measure = results['contest_measure']
                if positive_value_exists(attach_objects):
                    possible_endorsement['measure'] = measure
                possible_endorsement['ballot_item_name'] = measure.measure_title
                possible_endorsement['google_civic_election_id'] = measure.google_civic_election_id
            possible_endorsement_matched = True
            possible_endorsement_list_modified.append(possible_endorsement)
        elif 'ballot_item_name' in possible_endorsement and \
                positive_value_exists(possible_endorsement['ballot_item_name']):
            # If here search for possible measure matches
            matching_results = measure_list_manager.retrieve_contest_measures_from_non_unique_identifiers(
                google_civic_election_id_list, state_code, possible_endorsement['ballot_item_name'])

            if matching_results['contest_measure_found']:
                measure = matching_results['contest_measure']

                # If one candidate found, add we_vote_id here
                possible_endorsement['measure_we_vote_id'] = measure.we_vote_id
                if positive_value_exists(attach_objects):
                    possible_endorsement['measure'] = measure
                possible_endorsement['ballot_item_name'] = measure.measure_title
                possible_endorsement['google_civic_election_id'] = measure.google_civic_election_id
                possible_endorsement_matched = True
                possible_endorsement_list_modified.append(possible_endorsement)
            elif matching_results['multiple_entries_found']:
                status += "MULTIPLE_MEASURES_FOUND-CANNOT_MATCH "
                # possible_endorsement_list_modified.append(possible_endorsement)
            elif not positive_value_exists(matching_results['success']):
                status += "RETRIEVE_MEASURES_FROM_NON_UNIQUE-NO_SUCCESS "
                status += matching_results['status']
                # possible_endorsement_list_modified.append(possible_endorsement)
            else:
                # status += "RETRIEVE_MEASURES_FROM_NON_UNIQUE-MEASURE_NOT_FOUND "

                # Now we want to do a reverse search, where we cycle through all upcoming measures and search
                # within the incoming text for a known measure title
                for one_possible_measure in all_possible_measures_list_light:
                    if one_possible_measure['ballot_item_display_name'] in possible_endorsement['ballot_item_name']:
                        possible_endorsement['measure_we_vote_id'] = one_possible_measure['measure_we_vote_id']
                        possible_endorsement['ballot_item_name'] = one_possible_measure['ballot_item_display_name']
                        possible_endorsement['google_civic_election_id'] = \
                            one_possible_measure['google_civic_election_id']
                        matching_results = measure_manager.retrieve_contest_measure_from_we_vote_id(
                            possible_endorsement['measure_we_vote_id'])

                        if matching_results['contest_measure_found']:
                            measure = matching_results['contest_measure']

                            # If one measure found, augment the data if we can
                            possible_endorsement['measure_we_vote_id'] = measure.we_vote_id
                            if positive_value_exists(attach_objects):
                                possible_endorsement['measure'] = measure
                            possible_endorsement['ballot_item_name'] = measure.measure_title
                            possible_endorsement['google_civic_election_id'] = measure.google_civic_election_id

                        possible_endorsement_matched = True
                        possible_endorsement_list_modified.append(possible_endorsement)
                        break

        if not possible_endorsement_matched:
            # We want to check the synonyms for each measure in upcoming elections
            # (ex/ "Prop 1" in alternate_names) against the possible endorsement ()
            # NOTE: one_possible_measure is a candidate or measure for an upcoming election
            # NOTE: possible endorsement is one of the incoming new endorsements we are trying to match
            synonym_found = False
            for one_possible_measure in all_possible_measures_list_light:
                # Hanging off each ballot_item_dict is a alternate_names that includes
                #  shortened alternative names that we should check against decide_line_lower_case
                if 'alternate_names' in one_possible_measure and \
                        positive_value_exists(one_possible_measure['alternate_names']):
                    alternate_names = one_possible_measure['alternate_names']
                    for ballot_item_display_name_alternate in alternate_names:
                        if ballot_item_display_name_alternate.lower() in \
                                possible_endorsement['ballot_item_name'].lower():
                            # Make a copy so we don't change the incoming object -- if we find multiple upcoming
                            # measures that match, we should use them all
                            possible_endorsement_copy = copy.deepcopy(possible_endorsement)
                            possible_endorsement_copy['measure_we_vote_id'] = \
                                one_possible_measure['measure_we_vote_id']
                            possible_endorsement_copy['ballot_item_name'] = \
                                one_possible_measure['ballot_item_display_name']
                            possible_endorsement_copy['google_civic_election_id'] = \
                                one_possible_measure['google_civic_election_id']
                            matching_results = measure_manager.retrieve_contest_measure_from_we_vote_id(
                                possible_endorsement_copy['measure_we_vote_id'])

                            if matching_results['contest_measure_found']:
                                measure = matching_results['contest_measure']

                                # If one measure found, augment the data if we can
                                if positive_value_exists(attach_objects):
                                    possible_endorsement_copy['measure'] = measure
                                possible_endorsement_copy['ballot_item_name'] = measure.measure_title
                                possible_endorsement_copy['google_civic_election_id'] = measure.google_civic_election_id
                            synonym_found = True
                            possible_endorsement_list_modified.append(possible_endorsement_copy)
                            break
            if not synonym_found:
                # If an entry based on a synonym wasn't found, then store the orginal possibility
                possible_endorsement_list_modified.append(possible_endorsement)

    if len(possible_endorsement_list_modified):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        possible_endorsement_list_modified,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def match_endorsement_list_with_organizations_in_database(
        possible_endorsement_list,
        state_code='',
        all_possible_candidates_list_light=[],
        attach_objects=True):
    """

    :param possible_endorsement_list:
    :param state_code:
    :param all_possible_candidates_list_light: Only use when trying to match to new candidates
    :param attach_objects:
    :return:
    """
    status = ""
    success = True
    possible_endorsement_list_found = False

    possible_endorsement_list_modified = []
    for possible_endorsement in possible_endorsement_list:
        results = augment_organization_possible_position_data(
            possible_endorsement, limit_to_this_state_code=state_code,
            all_possible_candidates=all_possible_candidates_list_light, attach_objects=attach_objects)
        if results['possible_endorsement_count'] > 0:
            possible_endorsement_list_modified += results['possible_endorsement_return_list']

    if len(possible_endorsement_list_modified):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        possible_endorsement_list_modified,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def modify_one_row_in_possible_endorsement_list(possible_endorsement_list, possibility_position_id_to_remove=None,
                                                name_to_add_to_new_row=None):
    status = ""
    success = True
    # possibility_number_list = POSSIBLE_ENDORSEMENT_NUMBER_LIST_FULL
    possible_endorsement_list_found = False
    updated_possible_endorsement_list = []
    shift_remaining_items = False

    possibility_position_id_to_remove = convert_to_int(possibility_position_id_to_remove)
    if positive_value_exists(possibility_position_id_to_remove):
        if len(possible_endorsement_list) == 1:
            possible_endorsement = possible_endorsement_list[0]
            if convert_to_int(possible_endorsement['possibility_position_id']) == possibility_position_id_to_remove:
                possible_endorsement['possibility_should_be_deleted'] = True
            updated_possible_endorsement_list = [possible_endorsement]
            possible_endorsement_list_found = True
        else:
            for possible_endorsement in possible_endorsement_list:
                if convert_to_int(possible_endorsement['possibility_position_id']) == possibility_position_id_to_remove:
                    possible_endorsement['possibility_should_be_deleted'] = True
                    shift_remaining_items = True
                updated_possible_endorsement_list.append(possible_endorsement)
            if len(updated_possible_endorsement_list):
                possible_endorsement_list_found = True

    number_index = 0
    if shift_remaining_items and len(updated_possible_endorsement_list):
        # Reset the sequence of values in possible_candidate_number
        for possible_endorsement in updated_possible_endorsement_list:
            next_possibility_position_number = str(number_index + 1)
            possible_endorsement['possibility_position_number'] = next_possibility_position_number
            number_index += 1
            updated_possible_endorsement_list.append(possible_endorsement)

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        updated_possible_endorsement_list,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def fix_sequence_of_possible_endorsement_list(possible_endorsement_list):
    status = ""
    success = True
    possible_endorsement_list_found = True
    updated_possible_endorsement_list = []

    number_index = 1
    for possible_endorsement in possible_endorsement_list:
        possible_endorsement['possibility_position_number'] = number_index
        updated_possible_endorsement_list.append(possible_endorsement)
        number_index += 1

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        updated_possible_endorsement_list,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def take_in_possible_endorsement_list_from_form(request):
    status = ""
    success = True
    possible_endorsement_list = []
    possible_endorsement_list_found = False

    number_index = 1
    continue_looking_for_possible_endorsements = True
    while continue_looking_for_possible_endorsements:
        if (request.POST.get('ballot_item_name_' + str(number_index), None) is not None) \
                or (request.POST.get('candidate_we_vote_id_' + str(number_index), None) is not None) \
                or (request.POST.get('google_civic_election_id_' + str(number_index), None) is not None) \
                or (request.POST.get('measure_we_vote_id_' + str(number_index), None) is not None) \
                or (request.POST.get('more_info_url_' + str(number_index), None) is not None) \
                or (request.POST.get('organization_we_vote_' + str(number_index), None) is not None) \
                or (request.POST.get('position_stance_' + str(number_index), None) is not None) \
                or (request.POST.get('possibility_should_be_ignored_' + str(number_index), None) is not None) \
                or (request.POST.get('position_should_be_removed_' + str(number_index), None) is not None) \
                or (request.POST.get('possibility_position_id_' + str(number_index), None) is not None) \
                or (request.POST.get('statement_text_' + str(number_index), None) is not None):
            possible_endorsement = {
                'ballot_item_name': request.POST.get('ballot_item_name_' + str(number_index), ""),
                'candidate_we_vote_id': request.POST.get('candidate_we_vote_id_' + str(number_index), ""),
                'google_civic_election_id': request.POST.get('google_civic_election_id_' + str(number_index), ""),
                'measure_we_vote_id': request.POST.get('measure_we_vote_id_' + str(number_index), ""),
                'organization_we_vote_id': request.POST.get('organization_we_vote_id_' + str(number_index), ""),
                'more_info_url': request.POST.get('more_info_url_' + str(number_index), ""),
                'statement_text': request.POST.get('statement_text_' + str(number_index), ""),
                'position_stance': request.POST.get('position_stance_' + str(number_index), ""),
                'possibility_should_be_deleted':
                    positive_value_exists(request.POST.get('possibility_should_be_deleted_' + str(number_index),
                                                           False)),
                'possibility_should_be_ignored':
                    positive_value_exists(request.POST.get('possibility_should_be_ignored_' + str(number_index),
                                                           False)),
                'position_should_be_removed':
                    positive_value_exists(request.POST.get('position_should_be_removed_' + str(number_index), False)),
                'possibility_position_id':
                    convert_to_int(request.POST.get('possibility_position_id_' + str(number_index), 0)),
                'possibility_position_number': str(number_index),
            }
            possible_endorsement_list.append(possible_endorsement)
        else:
            continue_looking_for_possible_endorsements = False
        number_index += 1

    if len(possible_endorsement_list):
        possible_endorsement_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_list':        possible_endorsement_list,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def duplicate_voter_guides(from_voter_id, from_voter_we_vote_id, from_organization_we_vote_id,
                           to_voter_id, to_voter_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = False
    voter_guides_duplicated = 0
    voter_guides_not_duplicated = 0
    organization_manager = OrganizationManager()
    voter_guide_list_manager = VoterGuideListManager()
    voter_guide_manager = VoterGuideManager()
    voter_guide_list = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_id(from_voter_id)

    for from_voter_guide in voter_guide_list:
        # TODO When we want to heal the data
        # try:
        #     from_voter_guide.save()
        # except Exception as e:
        #     pass

        # See if the "to_voter_organization" already has an entry for this organization
        voter_guide_id = 0
        voter_guide_we_vote_id = ""
        google_civic_election_id = 0
        vote_smart_time_span = None
        public_figure_we_vote_id = None
        existing_entry_results = voter_guide_manager.retrieve_voter_guide(
            voter_guide_id, voter_guide_we_vote_id, google_civic_election_id, vote_smart_time_span,
            to_organization_we_vote_id, public_figure_we_vote_id, to_voter_we_vote_id)
        if not existing_entry_results['voter_guide_found']:
            try:
                from_voter_guide.id = None  # Reset the id so a new entry is created
                from_voter_guide.pk = None
                from_voter_guide.we_vote_id = None  # Clear out existing we_vote_id
                from_voter_guide.generate_new_we_vote_id()
                # Now replace with to_voter info
                from_voter_guide.owner_voter_id = to_voter_id
                from_voter_guide.owner_voter_we_vote_id = to_voter_we_vote_id
                from_voter_guide.organization_we_vote_id = to_organization_we_vote_id
                from_voter_guide.save()
                voter_guides_duplicated += 1
            except Exception as e:
                voter_guides_not_duplicated += 1

    # Now retrieve by organization_we_vote_id in case there is damaged data
    voter_guide_list = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
        from_organization_we_vote_id)

    for from_voter_guide in voter_guide_list:
        # TODO When we want to heal the data
        # try:
        #     from_voter_guide.save()
        # except Exception as e:
        #     pass

        # See if the "to_voter_organization" already has an entry for this organization
        voter_guide_id = 0
        voter_guide_we_vote_id = ""
        google_civic_election_id = 0
        vote_smart_time_span = None
        public_figure_we_vote_id = None
        existing_entry_results = voter_guide_manager.retrieve_voter_guide(
            voter_guide_id, voter_guide_we_vote_id, google_civic_election_id, vote_smart_time_span,
            to_organization_we_vote_id, public_figure_we_vote_id, to_voter_we_vote_id)
        if not existing_entry_results['voter_guide_found']:
            try:
                from_voter_guide.id = None  # Reset the id so a new entry is created
                from_voter_guide.pk = None
                from_voter_guide.we_vote_id = None  # Clear out existing we_vote_id
                from_voter_guide.generate_new_we_vote_id()
                # Now replace with to_voter info
                from_voter_guide.owner_voter_id = to_voter_id
                from_voter_guide.owner_voter_we_vote_id = to_voter_we_vote_id
                from_voter_guide.organization_we_vote_id = to_organization_we_vote_id
                from_voter_guide.save()
                voter_guides_duplicated += 1
            except Exception as e:
                voter_guides_not_duplicated += 1

    results = {
        'status':                       status,
        'success':                      success,
        'from_voter_id':                from_voter_id,
        'from_voter_we_vote_id':        from_voter_we_vote_id,
        'to_voter_id':                  to_voter_id,
        'to_voter_we_vote_id':          to_voter_we_vote_id,
        'voter_guides_duplicated':      voter_guides_duplicated,
        'voter_guides_not_duplicated':  voter_guides_not_duplicated,
    }
    return results


def move_voter_guides_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id,
                                       from_organization_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = False
    to_voter_id = 0
    voter_guide_entries_moved = 0
    voter_guide_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_VOTER_GUIDES-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'voter_guide_entries_moved': voter_guide_entries_moved,
            'voter_guide_entries_not_moved': voter_guide_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_VOTER_GUIDES-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'voter_guide_entries_moved': voter_guide_entries_moved,
            'voter_guide_entries_not_moved': voter_guide_entries_not_moved,
        }
        return results

    if not positive_value_exists(from_organization_we_vote_id) or not positive_value_exists(to_organization_we_vote_id):
        status += "MOVE_VOTER_GUIDES-MISSING_EITHER_FROM_OR_TO_ORGANIZATION_WE_VOTE_ID "

    voter_guide_list_manager = VoterGuideListManager()
    for_editing = True

    from_voter_guide_results = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_we_vote_id(
        from_voter_we_vote_id, for_editing)
    if from_voter_guide_results['voter_guide_list_found']:
        from_voter_guide_list = from_voter_guide_results['voter_guide_list']
    else:
        from_voter_guide_list = []

    from_voter_guide_list_count = len(from_voter_guide_list)

    if not positive_value_exists(from_voter_guide_list_count):
        status += "MOVE_VOTER_GUIDES-NO_FROM_VOTER_GUIDES_FOUND "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'voter_guide_entries_moved': voter_guide_entries_moved,
            'voter_guide_entries_not_moved': voter_guide_entries_not_moved,
        }
        return results

    to_voter_guide_results = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_we_vote_id(
        to_voter_we_vote_id, for_editing)
    if to_voter_guide_results['voter_guide_list_found']:
        to_voter_guide_list = to_voter_guide_results['voter_guide_list']
    else:
        to_voter_guide_list = []

    voter_manager = VoterManager()
    for from_voter_guide in from_voter_guide_list:
        # See if the "to_voter" already has a matching entry
        to_voter_guide_found = False
        from_voter_guide_google_civic_election_id = from_voter_guide.google_civic_election_id
        # Cycle through all of the "to_voter" current_friend entries and if there isn't one, create it
        for to_voter_guide in to_voter_guide_list:
            to_voter_guide_google_civic_election_id = to_voter_guide.google_civic_election_id
            if to_voter_guide_google_civic_election_id == from_voter_guide_google_civic_election_id:
                to_voter_guide_found = True
                break

        if to_voter_guide_found:
            # We don't do anything with the from_voter_guide, and end up deleting it below
            pass
        else:
            # Change the voter and organization values to the new values
            if not positive_value_exists(to_voter_id):
                to_voter_id = voter_manager.fetch_local_id_from_we_vote_id(to_voter_we_vote_id)
            try:
                from_voter_guide.owner_voter_id = to_voter_id
                from_voter_guide.owner_voter_we_vote_id = to_voter_we_vote_id
                from_voter_guide.organization_we_vote_id = to_organization_we_vote_id
                from_voter_guide.save()
                voter_guide_entries_moved += 1
            except Exception as e:
                voter_guide_entries_not_moved += 1

    # Now remove the voter_guides where there were duplicates
    from_voter_guide_remaining_results = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_we_vote_id(
        from_voter_we_vote_id, for_editing)
    if from_voter_guide_remaining_results['voter_guide_list_found']:
        from_voter_guide_list_remaining = to_voter_guide_results['voter_guide_list']
        for from_voter_guide in from_voter_guide_list_remaining:
            # Delete the remaining voter_guides
            try:
                # Leave this turned off until testing is finished
                # from_voter_guide.delete()
                pass
            except Exception as e:
                pass

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'voter_guide_entries_moved': voter_guide_entries_moved,
        'voter_guide_entries_not_moved': voter_guide_entries_not_moved,
    }
    return results


def voter_guides_import_from_master_server(request, google_civic_election_id):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Voter Guides from We Vote Master servers",
        VOTER_GUIDES_SYNC_URL, {
            "key":                      WE_VOTE_API_KEY,  # This comes from an environment variable
            "format":                   'json',
            "google_civic_election_id": str(google_civic_election_id),
        }
    )

    if import_results['success']:
        # results = filter_voter_guides_structured_json_for_local_duplicates(structured_json)
        # filtered_structured_json = results['structured_json']
        # duplicates_removed = results['duplicates_removed']
        filtered_structured_json = structured_json
        duplicates_removed = 0

        import_results = voter_guides_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_voter_guides_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove voter_guides that seem to be duplicates, but have different we_vote_id's.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    voter_guide_list_manager = VoterGuideListManager()
    for one_voter_guide in structured_json:
        we_vote_id = one_voter_guide['we_vote_id'] if 'we_vote_id' in one_voter_guide else ''
        google_civic_election_id = one_voter_guide['google_civic_election_id'] \
            if 'google_civic_election_id' in one_voter_guide else ''
        vote_smart_time_span = one_voter_guide['vote_smart_time_span'] \
            if 'vote_smart_time_span' in one_voter_guide else ''
        organization_we_vote_id = one_voter_guide['organization_we_vote_id'] \
            if 'organization_we_vote_id' in one_voter_guide else ''
        public_figure_we_vote_id = one_voter_guide['public_figure_we_vote_id'] \
            if 'public_figure_we_vote_id' in one_voter_guide else ''
        twitter_handle = one_voter_guide['twitter_handle'] if 'twitter_handle' in one_voter_guide else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = voter_guide_list_manager.retrieve_possible_duplicate_voter_guides(
            google_civic_election_id, vote_smart_time_span,
            organization_we_vote_id, public_figure_we_vote_id,
            twitter_handle,
            we_vote_id_from_master)

        if results['voter_guide_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_voter_guide)

    voter_guides_results = {
        'success':              True,
        'status':               "FILTER_VOTER_GUIDES_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return voter_guides_results


def voter_guides_import_from_structured_json(structured_json):
    """
    This pathway in requires a voter_guide_we_vote_id, and is not used when we import from Google Civic
    :param structured_json:
    :return:
    """
    voter_guide_manager = VoterGuideManager()
    organization_manager = OrganizationManager()
    organization_id = 0
    voter_guides_saved = 0
    voter_guides_updated = 0
    voter_guides_not_processed = 0
    for one_voter_guide in structured_json:
        voter_guide_we_vote_id = one_voter_guide['we_vote_id'] if 'we_vote_id' in one_voter_guide else ''
        google_civic_election_id = one_voter_guide['google_civic_election_id'] \
            if 'google_civic_election_id' in one_voter_guide else ''
        # This is recalculated, so technically not needed here
        election_day_text = one_voter_guide['election_day_text'] \
            if 'election_day_text' in one_voter_guide else ''
        vote_smart_time_span = one_voter_guide['vote_smart_time_span'] \
            if 'vote_smart_time_span' in one_voter_guide else ''
        organization_we_vote_id = one_voter_guide['organization_we_vote_id'] \
            if 'organization_we_vote_id' in one_voter_guide else ''
        public_figure_we_vote_id = one_voter_guide['public_figure_we_vote_id'] \
            if 'public_figure_we_vote_id' in one_voter_guide else ''
        state_code = one_voter_guide['state_code'] if 'state_code' in one_voter_guide else ''
        pledge_count = one_voter_guide['pledge_count'] if 'pledge_count' in one_voter_guide else ''
        pledge_goal = one_voter_guide['pledge_goal'] if 'pledge_goal' in one_voter_guide else ''
        we_vote_hosted_profile_image_url_large = one_voter_guide['we_vote_hosted_profile_image_url_large'] \
            if 'we_vote_hosted_profile_image_url_large' in one_voter_guide else ''
        we_vote_hosted_profile_image_url_medium = one_voter_guide['we_vote_hosted_profile_image_url_medium'] \
            if 'we_vote_hosted_profile_image_url_medium' in one_voter_guide else ''
        we_vote_hosted_profile_image_url_tiny = one_voter_guide['we_vote_hosted_profile_image_url_tiny'] \
            if 'we_vote_hosted_profile_image_url_tiny' in one_voter_guide else ''

        if positive_value_exists(voter_guide_we_vote_id) and \
                (positive_value_exists(organization_we_vote_id) or
                 positive_value_exists(public_figure_we_vote_id)) and \
                (positive_value_exists(google_civic_election_id) or
                 positive_value_exists(vote_smart_time_span)):
            # Make sure we have the organization (or public figure) in this database before we import the voter guide
            if positive_value_exists(organization_we_vote_id):
                results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
                if results['organization_found']:
                    organization_id = results['organization_id']
                if positive_value_exists(organization_id):
                    proceed_to_update_or_create = True
                else:
                    proceed_to_update_or_create = False
            elif positive_value_exists(public_figure_we_vote_id):
                # TODO DALE Update this to work with public_figure
                public_figure_id = organization_manager.retrieve_organization_from_we_vote_id(public_figure_we_vote_id)
                if positive_value_exists(public_figure_id):
                    proceed_to_update_or_create = True
                else:
                    proceed_to_update_or_create = False
            else:
                proceed_to_update_or_create = False
        else:
            proceed_to_update_or_create = False

        if proceed_to_update_or_create:
            if positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                    voter_guide_we_vote_id, organization_we_vote_id, google_civic_election_id, state_code, pledge_goal,
                    we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny
                )
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(vote_smart_time_span):
                results = voter_guide_manager.update_or_create_organization_voter_guide_by_time_span(
                    voter_guide_we_vote_id, organization_we_vote_id, vote_smart_time_span, pledge_goal,
                    we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny)
            elif positive_value_exists(public_figure_we_vote_id) and positive_value_exists(google_civic_election_id):
                results = voter_guide_manager.update_or_create_public_figure_voter_guide(
                    voter_guide_we_vote_id, google_civic_election_id, public_figure_we_vote_id, pledge_goal,
                    we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny)
            else:
                results = {
                    'success': False,
                    'status': 'Required value missing, cannot update or create (1)'
                }
        else:
            voter_guides_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create (2)'
            }

        if results['success']:
            if results['new_voter_guide_created']:
                voter_guides_saved += 1
            else:
                voter_guides_updated += 1
        else:
            voter_guides_not_processed += 1
    voter_guides_results = {
        'success':          True,
        'status':           "VOTER_GUIDES_IMPORT_PROCESS_COMPLETE",
        'saved':            voter_guides_saved,
        'updated':          voter_guides_updated,
        'not_processed':    voter_guides_not_processed,
    }
    return voter_guides_results


def voter_guide_possibility_retrieve_for_api(voter_device_id, voter_guide_possibility_id=0, url_to_scan=''):
    status = ""
    results = is_voter_device_id_valid(voter_device_id)
    # url_to_scan = url_to_scan  # TODO Use scrapy here
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_who_submitted_we_vote_id = fetch_voter_we_vote_id_from_voter_id(voter_id)
    # TODO We will need the voter_id here so we can control volunteer actions

    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    voter_guide_possibility = VoterGuidePossibility()
    if positive_value_exists(voter_guide_possibility_id):
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id)
    else:
        if not positive_value_exists(url_to_scan):
            status += "VOTER_GUIDE_POSSIBILITY_RETRIEVE-URL_TO_SCAN_MISSING "
            json_data = {
                'status': status,
                'success': False,
                'voter_device_id': voter_device_id,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')

        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_from_url(
                url_to_scan, voter_who_submitted_we_vote_id)

    status += results['status']
    voter_guide_possibility_found = False
    organization_we_vote_id = ""
    if results['voter_guide_possibility_found']:
        voter_guide_possibility_found = True
        voter_guide_possibility = results['voter_guide_possibility']
        voter_guide_possibility_id = results['voter_guide_possibility_id']
        organization_we_vote_id = results['organization_we_vote_id']
    elif positive_value_exists(results['success']):
        # Create new entry
        create_results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility(
            url_to_scan, voter_who_submitted_we_vote_id)
        if create_results['voter_guide_possibility_saved']:
            voter_guide_possibility_found = True
            voter_guide_possibility = create_results['voter_guide_possibility']
            voter_guide_possibility_id = create_results['voter_guide_possibility_id']
            organization_we_vote_id = voter_guide_possibility.organization_we_vote_id

    candidates_missing_from_we_vote = False
    cannot_find_endorsements = False
    capture_detailed_comments = False
    contributor_email = ""
    contributor_comments = ""
    hide_from_active_review = False
    ignore_this_source = False
    internal_notes = ""
    possible_organization_name = ""
    possible_organization_twitter_handle = ""
    limit_to_this_state_code = ""
    voter_guide_possibility_edit = ""
    if voter_guide_possibility_found:
        candidates_missing_from_we_vote = voter_guide_possibility.candidates_missing_from_we_vote
        cannot_find_endorsements = voter_guide_possibility.cannot_find_endorsements
        capture_detailed_comments = voter_guide_possibility.capture_detailed_comments
        contributor_email = voter_guide_possibility.contributor_email
        contributor_comments = voter_guide_possibility.contributor_comments
        hide_from_active_review = voter_guide_possibility.hide_from_active_review
        ignore_this_source = voter_guide_possibility.ignore_this_source
        internal_notes = voter_guide_possibility.internal_notes
        possible_organization_name = voter_guide_possibility.organization_name
        possible_organization_twitter_handle = voter_guide_possibility.organization_twitter_handle
        limit_to_this_state_code = voter_guide_possibility.state_code
        url_to_scan = voter_guide_possibility.voter_guide_possibility_url
        voter_guide_possibility_edit = WE_VOTE_SERVER_ROOT_URL + "/vg/create/?voter_guide_possibility_id=" + \
            str(voter_guide_possibility_id)

    organization_dict = {}
    if positive_value_exists(organization_we_vote_id):
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        status += organization_results['status']
        if organization_results['organization_found']:
            organization = organization_results['organization']
            organization_dict = {
                'organization_we_vote_id': organization_we_vote_id,
                'organization_name': organization.organization_name,
                'organization_website': organization.organization_website,
                'organization_twitter_handle': organization.organization_twitter_handle,
                'organization_email': organization.organization_email,
                'organization_facebook': organization.organization_facebook,
                'we_vote_hosted_profile_image_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
            }

    json_data = {
        'status':                               status,
        'success':                              results['success'],
        'candidates_missing_from_we_vote':      candidates_missing_from_we_vote,
        'cannot_find_endorsements':             cannot_find_endorsements,
        'capture_detailed_comments':            capture_detailed_comments,
        'contributor_email':                    contributor_email,
        'contributor_comments':                 contributor_comments,
        'hide_from_active_review':              hide_from_active_review,
        'ignore_this_source':                   ignore_this_source,
        'internal_notes':                       internal_notes,
        'organization':                         organization_dict,
        'possible_organization_name':           possible_organization_name,
        'possible_organization_twitter_handle': possible_organization_twitter_handle,
        'limit_to_this_state_code':             limit_to_this_state_code,
        'url_to_scan':                          url_to_scan,
        'voter_device_id':                      voter_device_id,
        'voter_guide_possibility_edit':         voter_guide_possibility_edit,
        'voter_guide_possibility_id':           voter_guide_possibility_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_positions_retrieve_for_api(  # voterGuidePossibilityPositionsRetrieve
        voter_device_id, voter_guide_possibility_id, voter_guide_possibility_position_id=0):
    status = "VOTER_GUIDE_POSSIBILITY_POSITIONS_RETRIEVE "
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # TODO We will need the voter_id here so we can control volunteer actions

    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
        voter_guide_possibility_id=voter_guide_possibility_id)

    possible_endorsement_list = []
    if results['voter_guide_possibility_found']:
        voter_guide_possibility = results['voter_guide_possibility']
        limit_to_this_state_code = voter_guide_possibility.state_code
        organization_we_vote_id = voter_guide_possibility.organization_we_vote_id

        results = extract_voter_guide_possibility_position_list_from_database(
            voter_guide_possibility, voter_guide_possibility_position_id)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

            # Do we want to analyze the stored possible_endorsement_list here?
            #  I don't think so -- I think we want to analyze on save.
            # if google_civic_election_id_list and len(google_civic_election_id_list):
            #     google_civic_election_id_list = []
            # else:
            #     google_civic_election_id_list = retrieve_upcoming_election_id_list(
            #         limit_to_this_state_code=state_code)

            google_civic_election_id_list = []

            # Match incoming endorsements to candidates already in the database
            results = match_endorsement_list_with_candidates_in_database(
                possible_endorsement_list,
                google_civic_election_id_list,
                limit_to_this_state_code,
                attach_objects=False)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

            # Match incoming endorsements to measures already in the database
            results = match_endorsement_list_with_measures_in_database(
                possible_endorsement_list, google_civic_election_id_list, limit_to_this_state_code,
                attach_objects=False)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

            # Add on existing position information
            if positive_value_exists(organization_we_vote_id):
                for one_possible_endorsement in possible_endorsement_list:
                    if 'candidate_we_vote_id' in one_possible_endorsement \
                            and positive_value_exists(one_possible_endorsement['candidate_we_vote_id']):
                        position_exists_query = PositionEntered.objects.filter(
                            organization_we_vote_id=organization_we_vote_id,
                            candidate_campaign_we_vote_id=one_possible_endorsement['candidate_we_vote_id'])
                        position_list = list(position_exists_query)
                        if positive_value_exists(len(position_list)):
                            one_possible_endorsement['position_we_vote_id'] = position_list[0].we_vote_id
                            one_possible_endorsement['position_stance_stored'] = position_list[0].stance
                            one_possible_endorsement['statement_text_stored'] = position_list[0].statement_text
                            one_possible_endorsement['more_info_url_stored'] = position_list[0].more_info_url
                    elif 'measure_we_vote_id' in one_possible_endorsement \
                            and positive_value_exists(one_possible_endorsement['measure_we_vote_id']):
                        position_exists_query = PositionEntered.objects.filter(
                            organization_we_vote_id=organization_we_vote_id,
                            contest_measure_we_vote_id=one_possible_endorsement['measure_we_vote_id'])
                        position_list = list(position_exists_query)
                        if positive_value_exists(len(position_list)):
                            one_possible_endorsement['position_we_vote_id'] = position_list[0].we_vote_id
                            one_possible_endorsement['position_stance_stored'] = position_list[0].stance
                            one_possible_endorsement['statement_text_stored'] = position_list[0].statement_text
                            one_possible_endorsement['more_info_url_stored'] = position_list[0].more_info_url

    status += results['status']
    json_data = {
        'status':                       status,
        'success':                      results['success'],
        'voter_guide_possibility_id':   voter_guide_possibility_id,
        'possible_position_list':       possible_endorsement_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_save_for_api(  # voterGuidePossibilitySave
        voter_device_id,
        voter_guide_possibility_id,
        candidates_missing_from_we_vote=None,
        capture_detailed_comments=None,
        clear_organization_options=None,
        contributor_comments=None,
        contributor_email=None,
        hide_from_active_review=None,
        ignore_this_source=None,
        internal_notes=None,
        organization_we_vote_id=None,
        possible_organization_name=None,
        possible_organization_twitter_handle=None,
        limit_to_this_state_code=None):
    status = ""
    success = True
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if not positive_value_exists(voter_guide_possibility_id):
        json_data = {
                'status': "MISSING_REQUIRED_VARIABLE-VOTER_GUIDE_POSSIBILITY_ID ",
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_GUIDE_POSSIBILITY ",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # At this point, we have a valid voter

    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
        voter_guide_possibility_id=voter_guide_possibility_id)
    if not results['voter_guide_possibility_found']:
        json_data = {
            'status': results['status'],
            'success': results['success'],
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    at_least_one_change = False
    voter_guide_possibility = results['voter_guide_possibility']
    voter_guide_possibility_id = voter_guide_possibility.id

    try:
        if candidates_missing_from_we_vote is not None:
            voter_guide_possibility.candidates_missing_from_we_vote = \
                positive_value_exists(candidates_missing_from_we_vote)
            at_least_one_change = True
        if capture_detailed_comments is not None:
            voter_guide_possibility.capture_detailed_comments = \
                positive_value_exists(capture_detailed_comments)
            at_least_one_change = True
        if clear_organization_options is not None:
            voter_guide_possibility.clear_organization_options = \
                positive_value_exists(clear_organization_options)
            at_least_one_change = True
        if contributor_comments is not None:
            voter_guide_possibility.contributor_comments = contributor_comments
            at_least_one_change = True
        if contributor_email is not None:
            voter_guide_possibility.contributor_email = contributor_email
            at_least_one_change = True
        if hide_from_active_review is not None:
            voter_guide_possibility.hide_from_active_review = \
                positive_value_exists(hide_from_active_review)
            at_least_one_change = True
        if ignore_this_source is not None:
            voter_guide_possibility.ignore_this_source = \
                positive_value_exists(ignore_this_source)
            at_least_one_change = True
        if internal_notes is not None:
            voter_guide_possibility.internal_notes = internal_notes
            at_least_one_change = True
        if organization_we_vote_id is not None:
            voter_guide_possibility.organization_we_vote_id = organization_we_vote_id
            at_least_one_change = True
        if possible_organization_name is not None:
            voter_guide_possibility.organization_name = possible_organization_name
            at_least_one_change = True
        if possible_organization_twitter_handle is not None:
            voter_guide_possibility.organization_twitter_handle = possible_organization_twitter_handle
            at_least_one_change = True
        if limit_to_this_state_code is not None:
            voter_guide_possibility.state_code = limit_to_this_state_code
            at_least_one_change = True

        if at_least_one_change:
            voter_guide_possibility.save()
    except Exception as e:
        status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY ' \
                  '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
        success = False

    if not success:
        json_data = {
            'status': status,
            'success': success,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # If here, the voter_guide_possibility was successfully saved, so we want to return the refreshed data
    return voter_guide_possibility_retrieve_for_api(voter_device_id,
                                                    voter_guide_possibility_id=voter_guide_possibility_id)


def voter_guide_possibility_position_save_for_api(  # voterGuidePossibilityPositionSave
        voter_device_id,
        voter_guide_possibility_id,
        voter_guide_possibility_position_id,
        ballot_item_name=None,
        position_stance=None,
        statement_text=None,
        more_info_url=None,
        possibility_should_be_deleted=None,
        possibility_should_be_ignored=None,
        candidate_we_vote_id=None,
        measure_we_vote_id=None,
        position_should_be_removed=None,
        google_civic_election_id_list=None):
    status = "VOTER_GUIDE_POSSIBILITY_POSITION_SAVE "
    success = True
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if not positive_value_exists(voter_guide_possibility_id) \
            and not positive_value_exists(voter_guide_possibility_position_id):
        json_data = {
                'status': "MISSING_BOTH_REQUIRED_VARIABLES ",
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_GUIDE_POSSIBILITY ",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # At this point, we have a valid voter

    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    voter_guide_possibility_position = VoterGuidePossibilityPosition()
    voter_guide_possibility = None
    voter_guide_possibility_found = False
    if positive_value_exists(possibility_should_be_deleted) \
            and positive_value_exists(voter_guide_possibility_position_id):
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_position(
            voter_guide_possibility_position_id=voter_guide_possibility_position_id)
        if results['voter_guide_possibility_position_found']:
            voter_guide_possibility_position = results['voter_guide_possibility_position']
            try:
                voter_guide_possibility_position.delete()
                status += "DELETED_VOTER_GUIDE_POSSIBILITY_POSITION "
                success = True
            except Exception as e:
                status += 'FAILED_TO_DELETE_VOTER_GUIDE_POSSIBILITY_POSITION ' \
                          '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
                success = False
            json_data = {
                'status': status,
                'success': success,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        else:
            status += "FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION_FOR_DELETE "
            status += results['status']
            json_data = {
                'status': status,
                'success': False,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')

    if positive_value_exists(voter_guide_possibility_position_id):
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_position(
            voter_guide_possibility_position_id=voter_guide_possibility_position_id)
        if not results['voter_guide_possibility_position_found']:
            status += "FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION "
            status += results['status']
            json_data = {
                'status': status,
                'success': False,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        voter_guide_possibility_position = results['voter_guide_possibility_position']
        voter_guide_possibility_id = voter_guide_possibility_position['voter_guide_possibility_parent_id']
    elif positive_value_exists(voter_guide_possibility_id):
        # If we are here, it is because we are creating a new possibility_position
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id)
        if not results['voter_guide_possibility_found']:
            status += results['status']
            status += "FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY "
            json_data = {
                'status': status,
                'success': False,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')

        voter_guide_possibility = results['voter_guide_possibility']
        voter_guide_possibility_found = True

        # Now that we verified voter_guide_possibility exists, create new voter_guide_possibility_position
        updated_values = {
            'possibility_position_number':  1,
            'voter_guide_possibility_parent_id': voter_guide_possibility_id,
        }
        create_results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility_position(
            voter_guide_possibility_position_id, voter_guide_possibility_id,
            updated_values)
        if not create_results['new_voter_guide_possibility_position_created']:
            status += create_results['status']
            status += "FAILED_TO_CREATE_NEW_VOTER_GUIDE_POSSIBILITY_POSITION "
            json_data = {
                'status': status,
                'success': False,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        voter_guide_possibility_position = create_results['voter_guide_possibility_position']
        voter_guide_possibility_position_id = voter_guide_possibility_position.id

    if not voter_guide_possibility_found:
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id)
        if results['voter_guide_possibility_found']:
            voter_guide_possibility = results['voter_guide_possibility']
            voter_guide_possibility_found = True

    at_least_one_change = False
    try:
        if ballot_item_name is not None:
            voter_guide_possibility_position.ballot_item_name = ballot_item_name
            at_least_one_change = True
        if position_stance is not None:
            voter_guide_possibility_position.position_stance = position_stance
            at_least_one_change = True
        if statement_text is not None:
            voter_guide_possibility_position.statement_text = statement_text
            at_least_one_change = True
        if more_info_url is not None:
            voter_guide_possibility_position.more_info_url = more_info_url
            at_least_one_change = True
        if possibility_should_be_ignored is not None:
            voter_guide_possibility_position.possibility_should_be_ignored = \
                positive_value_exists(possibility_should_be_ignored)
            at_least_one_change = True
        if candidate_we_vote_id is not None:
            voter_guide_possibility_position.candidate_we_vote_id = candidate_we_vote_id
            at_least_one_change = True
        if measure_we_vote_id is not None:
            voter_guide_possibility_position.measure_we_vote_id = measure_we_vote_id
            at_least_one_change = True
        if position_should_be_removed is not None:
            voter_guide_possibility_position.position_should_be_removed = \
                positive_value_exists(position_should_be_removed)
            at_least_one_change = True

        if at_least_one_change:
            voter_guide_possibility_position.save()
    except Exception as e:
        status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY1 ' \
                  '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
        success = False

    limit_to_this_state_code = ""
    organization_name = ""
    organization_we_vote_id = ""
    organization_twitter_handle = ""
    if voter_guide_possibility_found:
        organization_we_vote_id = voter_guide_possibility.organization_we_vote_id
        limit_to_this_state_code = voter_guide_possibility.state_code

    possible_endorsement_dict = {
        'possibility_position_id': voter_guide_possibility_position.id,
        'ballot_item_name': voter_guide_possibility_position.ballot_item_name,
        'candidate_we_vote_id': voter_guide_possibility_position.candidate_we_vote_id,
        # 'candidate_twitter_handle': 'candidate_twitter_handle',
        # 'contest_office_name': 'contest_office_name',
        'google_civic_election_id': voter_guide_possibility_position.google_civic_election_id,
        'measure_we_vote_id': voter_guide_possibility_position.measure_we_vote_id,
        'more_info_url': more_info_url,
        'organization_name': organization_name,
        'organization_we_vote_id': organization_we_vote_id,
        'organization_twitter_handle': organization_twitter_handle,
        'possibility_position_number': voter_guide_possibility_position.possibility_position_number,
        'possibility_should_be_ignored': voter_guide_possibility_position.possibility_should_be_ignored,
        'position_should_be_removed': voter_guide_possibility_position.position_should_be_removed,
        'position_we_vote_id': voter_guide_possibility_position.position_we_vote_id,
        'position_stance': voter_guide_possibility_position.position_stance,
        'statement_text': voter_guide_possibility_position.statement_text,
        'state_code': limit_to_this_state_code,
    }

    if google_civic_election_id_list and len(google_civic_election_id_list):
        pass
    else:
        google_civic_election_id_list = retrieve_upcoming_election_id_list(
            limit_to_this_state_code=limit_to_this_state_code)

    # We will need all candidates for all upcoming elections so we can search the HTML of
    #  the possible voter guide for these names
    all_possible_candidates_list_light = []
    if positive_value_exists(google_civic_election_id_list):
        results = retrieve_candidate_list_for_all_upcoming_elections(google_civic_election_id_list,
                                                                     limit_to_this_state_code=limit_to_this_state_code)
        if results['candidate_list_found']:
            all_possible_candidates_list_light = results['candidate_list_light']

    # We need all measures for all upcoming elections
    all_possible_measures_list_light = []
    if positive_value_exists(google_civic_election_id_list):
        # TODO: Add "shortened_identifier" to the model and this retrieve
        results = retrieve_measure_list_for_all_upcoming_elections(google_civic_election_id_list,
                                                                   limit_to_this_state_code=limit_to_this_state_code)
        if results['measure_list_found']:
            all_possible_measures_list_light = results['measure_list_light']

            expand_results = add_measure_name_alternatives_to_measure_list_light(all_possible_measures_list_light)
            if expand_results['success']:
                all_possible_measures_list_light = expand_results['measure_list_light']

    attach_objects = False
    possible_endorsement_list = []
    augment_results = augment_candidate_possible_position_data(
        possible_endorsement_dict, google_civic_election_id_list, limit_to_this_state_code=limit_to_this_state_code,
        all_possible_candidates=all_possible_candidates_list_light, attach_objects=attach_objects)
    if augment_results['possible_endorsement_count'] > 0:
        possible_endorsement_list = augment_results['possible_endorsement_return_list']
        modified_possible_endorsement_dict = possible_endorsement_list.pop(0)
        candidate_we_vote_id = modified_possible_endorsement_dict['candidate_we_vote_id']
        if not positive_value_exists(candidate_we_vote_id):
            candidate_we_vote_id = None  # Only save if we have a new value
        measure_we_vote_id = modified_possible_endorsement_dict['measure_we_vote_id']
        if not positive_value_exists(measure_we_vote_id):
            measure_we_vote_id = None  # Only save if we have a new value
        position_we_vote_id = modified_possible_endorsement_dict['position_we_vote_id']
        if not positive_value_exists(position_we_vote_id):
            position_we_vote_id = None  # Only save if we have a new value

        at_least_one_change = False
        try:
            if candidate_we_vote_id is not None:
                voter_guide_possibility_position.candidate_we_vote_id = candidate_we_vote_id
                at_least_one_change = True
            if measure_we_vote_id is not None:
                voter_guide_possibility_position.measure_we_vote_id = measure_we_vote_id
                at_least_one_change = True
            if position_we_vote_id is not None:
                voter_guide_possibility_position.position_we_vote_id = position_we_vote_id
                at_least_one_change = True

            if at_least_one_change:
                voter_guide_possibility_position.save()
        except Exception as e:
            status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY2 ' \
                      '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
            success = False

    if not success:
        json_data = {
            'status': status,
            'success': success,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Now save additional entries found
    if augment_results['possible_endorsement_count'] > 1 and len(possible_endorsement_list):
        # Since we aren't dealing with only one voter_guide_possibility_position any more, clear id
        #  so the full list is returned
        voter_guide_possibility_position_id = 0
        for modified_possible_endorsement_dict in possible_endorsement_list:
            # We are adding more possible endorsements to the list

            # TODO DALE
            # We should make sure there isn't already an entry under voter_guide_possibility
            #  with a position with the same candidate_we_vote_id or measure_we_vote_id or position_we_vote_id
            voter_guide_possibility_position_copy = copy.deepcopy(voter_guide_possibility_position)
            voter_guide_possibility_position_copy.id = None
            voter_guide_possibility_position_copy.pk = None
            candidate_we_vote_id = modified_possible_endorsement_dict['candidate_we_vote_id']
            if not positive_value_exists(candidate_we_vote_id):
                candidate_we_vote_id = None  # Only save if we have a new value
            measure_we_vote_id = modified_possible_endorsement_dict['measure_we_vote_id']
            if not positive_value_exists(measure_we_vote_id):
                measure_we_vote_id = None  # Only save if we have a new value
            position_we_vote_id = modified_possible_endorsement_dict['position_we_vote_id']
            if not positive_value_exists(position_we_vote_id):
                position_we_vote_id = None  # Only save if we have a new value

            at_least_one_change = False
            try:
                if candidate_we_vote_id is not None:
                    voter_guide_possibility_position_copy.candidate_we_vote_id = candidate_we_vote_id
                    at_least_one_change = True
                if measure_we_vote_id is not None:
                    voter_guide_possibility_position_copy.measure_we_vote_id = measure_we_vote_id
                    at_least_one_change = True
                if position_we_vote_id is not None:
                    voter_guide_possibility_position_copy.position_we_vote_id = position_we_vote_id
                    at_least_one_change = True

                if at_least_one_change:
                    voter_guide_possibility_position_copy.save()
            except Exception as e:
                status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY3 ' \
                          '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
                success = False

            if not success:
                json_data = {
                    'status': status,
                    'success': success,
                    'voter_device_id': voter_device_id,
                }
                return HttpResponse(json.dumps(json_data), content_type='application/json')

    # If here, the voter_guide_possibility was successfully saved, so we want to return the refreshed data
    return voter_guide_possibility_positions_retrieve_for_api(
        voter_device_id,
        voter_guide_possibility_id=voter_guide_possibility_id,
        voter_guide_possibility_position_id=voter_guide_possibility_position_id)


def voter_guides_to_follow_retrieve_for_api(voter_device_id,  # voterGuidesToFollowRetrieve
                                            kind_of_ballot_item='', ballot_item_we_vote_id='',
                                            google_civic_election_id=0, search_string='',
                                            start_retrieve_at_this_number=0,
                                            maximum_number_to_retrieve=0,
                                            filter_voter_guides_by_issue=False,
                                            add_voter_guides_not_from_election=False):
    voter_we_vote_id = ""
    start_retrieve_at_this_number = convert_to_int(start_retrieve_at_this_number)
    number_retrieved = 0
    filter_voter_guides_by_issue = positive_value_exists(filter_voter_guides_by_issue)
    add_voter_guides_not_from_election = positive_value_exists(add_voter_guides_not_from_election)
    status = ""
    # Get voter_id from the voter_device_id so we can figure out which voter_guides to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID',
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'start_retrieve_at_this_number': start_retrieve_at_this_number,
            'number_retrieved': number_retrieved,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'google_civic_election_id': google_civic_election_id,
            'search_string': search_string,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
        }
        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'start_retrieve_at_this_number': start_retrieve_at_this_number,
            'number_retrieved': number_retrieved,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'google_civic_election_id': google_civic_election_id,
            'search_string': search_string,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
        }
        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results

    # If filter_voter_guides_by_issue is set then fetch organization_we_vote_ids related to the
    # issues that the voter follows
    organization_we_vote_id_list_for_voter_issues = []
    if filter_voter_guides_by_issue:
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        if not positive_value_exists(voter_we_vote_id):
            json_data = {
                'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID VOTER_WE_VOTE_ID_NOT_FOUND",
                'success': False,
                'voter_device_id': voter_device_id,
                'voter_guides': [],
                'start_retrieve_at_this_number': start_retrieve_at_this_number,
                'number_retrieved': number_retrieved,
                'maximum_number_to_retrieve': maximum_number_to_retrieve,
                'google_civic_election_id': google_civic_election_id,
                'search_string': search_string,
            }
            results = {
                'success': False,
                'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
                'json_data': json_data,
            }
            return results
        else:
            follow_issue_list_manager = FollowIssueList()
            following_status = FOLLOWING
            issue_list_for_voter = follow_issue_list_manager. \
                retrieve_follow_issue_list_by_voter_we_vote_id(voter_we_vote_id, following_status)  # Read only
            issue_list_for_voter = list(issue_list_for_voter)
            issue_we_vote_id_list_for_voter = []
            for issue in issue_list_for_voter:
                issue_we_vote_id_list_for_voter.append(issue.issue_we_vote_id)

            link_issue_list = OrganizationLinkToIssueList()
            organization_we_vote_id_list_result = link_issue_list. \
                retrieve_organization_we_vote_id_list_from_issue_we_vote_id_list(issue_we_vote_id_list_for_voter)
            organization_we_vote_id_list_for_voter_issues = \
                organization_we_vote_id_list_result['organization_we_vote_id_list']

    voter_guide_list = []
    voter_guides = []
    try:
        if positive_value_exists(kind_of_ballot_item) and positive_value_exists(ballot_item_we_vote_id):
            results = retrieve_voter_guides_to_follow_by_ballot_item(voter_id,
                                                                     kind_of_ballot_item, ballot_item_we_vote_id,
                                                                     search_string, filter_voter_guides_by_issue,
                                                                     organization_we_vote_id_list_for_voter_issues)
            success = results['success']
            status += results['status']
            voter_guide_list = results['voter_guide_list']
        elif positive_value_exists(google_civic_election_id):
            # This retrieve also does the reordering
            results = retrieve_voter_guides_to_follow_by_election_for_api(voter_id, google_civic_election_id,
                                                                          search_string,
                                                                          filter_voter_guides_by_issue,
                                                                          organization_we_vote_id_list_for_voter_issues,
                                                                          start_retrieve_at_this_number,
                                                                          maximum_number_to_retrieve,
                                                                          'twitter_followers_count', 'desc')
            success = results['success']
            voter_guide_list = results['voter_guide_list']
            status = results['status'] + ", len(voter_guide_list): " + str(len(voter_guide_list)) + " "
            if add_voter_guides_not_from_election:
                status += "ADDING_VOTER_GUIDES_NOT_FROM_ELECTION "
                non_election_results = retrieve_voter_guides_to_follow_generic_for_api(
                    voter_id, search_string,
                    filter_voter_guides_by_issue,
                    organization_we_vote_id_list_for_voter_issues,
                    maximum_number_to_retrieve,
                    'twitter_followers_count', 'desc')
                if non_election_results['success']:
                    status += non_election_results['status']
                    non_election_voter_guide_list = non_election_results['voter_guide_list']
                    voter_guide_list = voter_guide_list + non_election_voter_guide_list
        else:
            status += "RETRIEVING_VOTER_GUIDES_WITHOUT_ELECTION_ID_OR_BALLOT_ITEM "
            results = retrieve_voter_guides_to_follow_generic_for_api(voter_id, search_string,
                                                                      filter_voter_guides_by_issue,
                                                                      organization_we_vote_id_list_for_voter_issues,
                                                                      maximum_number_to_retrieve,
                                                                      'twitter_followers_count', 'desc')
            success = results['success']
            status += results['status']
            voter_guide_list = results['voter_guide_list']

    except Exception as e:
        status += 'FAILED voter_guides_to_follow_retrieve_for_api, retrieve_voter_guides_for_election ' \
                 '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
        success = False

    if success:
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id, read_only=True)
        linked_organization_we_vote_id = ""
        if results['voter_found']:
            voter = results['voter']
            voter_we_vote_id = voter.we_vote_id
            linked_organization_we_vote_id = voter.linked_organization_we_vote_id

        number_added_to_list = 0
        position_manager = PositionManager()
        position = PositionEntered()
        pledge_to_vote_manager = PledgeToVoteManager()
        for voter_guide in voter_guide_list:
            if positive_value_exists(voter_guide.organization_we_vote_id) \
                    and positive_value_exists(linked_organization_we_vote_id) \
                    and linked_organization_we_vote_id == voter_guide.organization_we_vote_id:
                # Do not return your own voter guide to follow
                continue

            if hasattr(voter_guide, 'ballot_item_we_vote_ids_this_org_supports'):
                ballot_item_we_vote_ids_this_org_supports = voter_guide.ballot_item_we_vote_ids_this_org_supports
            else:
                ballot_item_we_vote_ids_this_org_supports = []

            if hasattr(voter_guide, 'ballot_item_we_vote_ids_this_org_info_only'):
                ballot_item_we_vote_ids_this_org_info_only = voter_guide.ballot_item_we_vote_ids_this_org_info_only
            else:
                ballot_item_we_vote_ids_this_org_info_only = []

            if hasattr(voter_guide, 'ballot_item_we_vote_ids_this_org_opposes'):
                ballot_item_we_vote_ids_this_org_opposes = voter_guide.ballot_item_we_vote_ids_this_org_opposes
            else:
                ballot_item_we_vote_ids_this_org_opposes = []

            organization_link_to_issue_list = OrganizationLinkToIssueList()
            issue_we_vote_ids_linked = \
                organization_link_to_issue_list.fetch_issue_we_vote_id_list_by_organization_we_vote_id(
                    voter_guide.organization_we_vote_id)

            pledge_to_vote_we_vote_id = ""
            pledge_results = pledge_to_vote_manager.retrieve_pledge_to_vote(
                pledge_to_vote_we_vote_id, voter_we_vote_id, voter_guide.we_vote_id)  # Already read_only
            if pledge_results['pledge_found']:
                voter_has_pledged = pledge_results['voter_has_pledged']
            else:
                voter_has_pledged = False
            position_found = False
            if voter_guide.last_updated:
                last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ''
            one_voter_guide = {
                'ballot_item_we_vote_ids_this_org_supports':    ballot_item_we_vote_ids_this_org_supports,
                'ballot_item_we_vote_ids_this_org_info_only':   ballot_item_we_vote_ids_this_org_info_only,
                'ballot_item_we_vote_ids_this_org_opposes':     ballot_item_we_vote_ids_this_org_opposes,
                'election_day_text':            voter_guide.election_day_text,
                'google_civic_election_id':     voter_guide.google_civic_election_id,
                'issue_we_vote_ids_linked':     issue_we_vote_ids_linked,
                'last_updated':                 last_updated,
                'organization_we_vote_id':      voter_guide.organization_we_vote_id,
                'owner_voter_id':               voter_guide.owner_voter_id,
                'pledge_goal':                  voter_guide.pledge_goal,
                'pledge_count':                 voter_guide.pledge_count,
                'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
                'time_span':                    voter_guide.vote_smart_time_span,
                'twitter_description':          voter_guide.twitter_description,
                'twitter_followers_count':      voter_guide.twitter_followers_count,
                'twitter_handle':               voter_guide.twitter_handle,
                'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
                'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
                if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
                else voter_guide.voter_guide_image_url(),
                'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
                'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
                'voter_has_pledged':            voter_has_pledged,
                'we_vote_id':                   voter_guide.we_vote_id,
            }
            if positive_value_exists(ballot_item_we_vote_id):
                if kind_of_ballot_item == CANDIDATE:
                    organization_manager = OrganizationManager()
                    organization_id = organization_manager.fetch_organization_id(
                        voter_guide.organization_we_vote_id)
                    results = position_manager.retrieve_organization_candidate_campaign_position_with_we_vote_id(
                        organization_id, ballot_item_we_vote_id)
                    if results['position_found']:
                        position = results['position']
                        position_found = True
                elif kind_of_ballot_item == MEASURE:
                    organization_manager = OrganizationManager()
                    organization_id = organization_manager.fetch_organization_id(
                        voter_guide.organization_we_vote_id)
                    results = position_manager.retrieve_organization_contest_measure_position_with_we_vote_id(
                        organization_id, ballot_item_we_vote_id)
                    if results['position_found']:
                        position = results['position']
                        position_found = True

                # Since a ballot_item_we_vote_id came in, we only want to return a voter guide if there is a
                #  support, oppose, or a comment
                if position_found:
                    if position.is_support_or_positive_rating() or position.is_oppose_or_negative_rating() or \
                            position.statement_text or is_link_to_video(position.more_info_url):
                        # We can proceed
                        pass
                    else:
                        # We shouldn't return a voter_guide in this case without support/oppose/or a comment
                        continue

                if position_found:
                    one_voter_guide['is_support'] = position.is_support()
                    one_voter_guide['is_positive_rating'] = position.is_positive_rating()
                    one_voter_guide['is_support_or_positive_rating'] = position.is_support_or_positive_rating()
                    one_voter_guide['is_oppose'] = position.is_oppose()
                    one_voter_guide['is_negative_rating'] = position.is_negative_rating()
                    one_voter_guide['is_oppose_or_negative_rating'] = position.is_oppose_or_negative_rating()
                    one_voter_guide['is_information_only'] = position.is_information_only()
                    one_voter_guide['ballot_item_display_name'] = position.ballot_item_display_name
                    one_voter_guide['speaker_display_name'] = position.speaker_display_name
                    one_voter_guide['statement_text'] = position.statement_text
                    one_voter_guide['more_info_url'] = position.more_info_url
                    one_voter_guide['has_video'] = is_link_to_video(position.more_info_url)
                    one_voter_guide['vote_smart_rating'] = position.vote_smart_rating
                    one_voter_guide['vote_smart_time_span'] = position.vote_smart_time_span

            voter_guides.append(one_voter_guide.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        number_retrieved = len(voter_guides)
        if positive_value_exists(number_retrieved):
            json_data = {
                'status': status + ' VOTER_GUIDES_TO_FOLLOW_FOR_API_RETRIEVED',
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guides': voter_guides,
                'google_civic_election_id': google_civic_election_id,
                'search_string': search_string,
                'ballot_item_we_vote_id': ballot_item_we_vote_id,
                'start_retrieve_at_this_number': start_retrieve_at_this_number,
                'number_retrieved': number_retrieved,
                'maximum_number_to_retrieve': maximum_number_to_retrieve,
                'filter_voter_guides_by_issue': filter_voter_guides_by_issue
            }
        else:
            json_data = {
                'status': status + ' NO_VOTER_GUIDES_FOUND',
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guides': voter_guides,
                'google_civic_election_id': google_civic_election_id,
                'search_string': search_string,
                'ballot_item_we_vote_id': ballot_item_we_vote_id,
                'start_retrieve_at_this_number': start_retrieve_at_this_number,
                'number_retrieved': number_retrieved,
                'maximum_number_to_retrieve': maximum_number_to_retrieve,
                'filter_voter_guides_by_issue': filter_voter_guides_by_issue
            }

        results = {
            'success': success,
            'google_civic_election_id': google_civic_election_id,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results
    else:
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'start_retrieve_at_this_number': start_retrieve_at_this_number,
            'number_retrieved': number_retrieved,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'google_civic_election_id': google_civic_election_id,
            'search_string': search_string,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
        }

        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results


def retrieve_voter_guides_to_follow_by_ballot_item(voter_id, kind_of_ballot_item, ballot_item_we_vote_id,
                                                   search_string, filter_voter_guides_by_issue=None,
                                                   organization_we_vote_id_list_for_voter_issues=None):
    if filter_voter_guides_by_issue is None:
        filter_voter_guides_by_issue = False
    voter_guide_list_found = False
    retrieve_public_positions = True  # The alternate is positions for friends-only. Since this method returns positions
    # to follow, we never need to return friend's positions here

    position_list_manager = PositionListManager()
    if (kind_of_ballot_item == CANDIDATE) and positive_value_exists(ballot_item_we_vote_id):
        candidate_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
            retrieve_public_positions, candidate_id, ballot_item_we_vote_id, ANY_STANCE, read_only=True)
    elif (kind_of_ballot_item == MEASURE) and positive_value_exists(ballot_item_we_vote_id):
        measure_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
            retrieve_public_positions, measure_id, ballot_item_we_vote_id, ANY_STANCE, read_only=True)
    elif (kind_of_ballot_item == OFFICE) and positive_value_exists(ballot_item_we_vote_id):
        office_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                office_id, ballot_item_we_vote_id, ANY_STANCE, read_only=True)
    else:
        voter_guide_list = []
        results = {
            'success':                      False,
            'status':                       "VOTER_GUIDES_BALLOT_RELATED_VARIABLES_MISSING",
            'search_string':                search_string,
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    if filter_voter_guides_by_issue and organization_we_vote_id_list_for_voter_issues is not None:
        all_positions_list = position_list_manager.remove_positions_unrelated_to_issues(
            all_positions_list, organization_we_vote_id_list_for_voter_issues)

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id,
                                                                                                  read_only=True)

    positions_list = position_list_manager.calculate_positions_not_followed_by_voter(
        all_positions_list, organizations_followed_by_voter)

    voter_guide_list = []
    # Cycle through the positions held by groups that you don't currently follow
    voter_guide_manager = VoterGuideManager()
    for one_position in positions_list:
        if positive_value_exists(one_position.organization_we_vote_id):
            if one_position.google_civic_election_id:
                results = voter_guide_manager.retrieve_voter_guide(
                    voter_guide_id=0,
                    google_civic_election_id=one_position.google_civic_election_id,
                    vote_smart_time_span=None,
                    organization_we_vote_id=one_position.organization_we_vote_id,
                    read_only=True)
            else:
                results['voter_guide_found'] = False
                # As of Aug 2018, we no longer use vote_smart_time_span
                # results = voter_guide_manager.retrieve_voter_guide(
                #     voter_guide_id=0,
                #     google_civic_election_id=0,
                #     vote_smart_time_span=one_position.vote_smart_time_span,
                #     organization_we_vote_id=one_position.organization_we_vote_id)

        elif positive_value_exists(one_position.public_figure_we_vote_id):
            results['voter_guide_found'] = False
        elif positive_value_exists(one_position.voter_we_vote_id):
            results['voter_guide_found'] = False
        else:
            results['voter_guide_found'] = False

        if results['voter_guide_found']:
            one_voter_guide = results['voter_guide']

            # Augment the voter guide with a list of ballot_item we_vote_id's that this org supports
            stance_we_are_looking_for = SUPPORT
            organization_id = 0
            ballot_item_support_results = retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(
                voter_id, organization_id, one_voter_guide.organization_we_vote_id, stance_we_are_looking_for,
                one_position.google_civic_election_id)

            if ballot_item_support_results['count']:
                ballot_item_we_vote_ids_this_org_supports = ballot_item_support_results['ballot_item_we_vote_ids_list']
            else:
                ballot_item_we_vote_ids_this_org_supports = []

            one_voter_guide.ballot_item_we_vote_ids_this_org_supports = \
                ballot_item_we_vote_ids_this_org_supports

            # Augment the voter guide with a list of ballot_item we_vote_id's that this org has info about
            stance_we_are_looking_for = INFORMATION_ONLY
            organization_id = 0
            ballot_item_info_only_results = retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(
                voter_id, organization_id, one_voter_guide.organization_we_vote_id, stance_we_are_looking_for,
                one_position.google_civic_election_id)

            if ballot_item_info_only_results['count']:
                ballot_item_we_vote_ids_this_org_info_only = \
                    ballot_item_info_only_results['ballot_item_we_vote_ids_list']
            else:
                ballot_item_we_vote_ids_this_org_info_only = []

            one_voter_guide.ballot_item_we_vote_ids_this_org_info_only = \
                ballot_item_we_vote_ids_this_org_info_only

            # Augment the voter guide with a list of ballot_item we_vote_id's that this org opposes
            stance_we_are_looking_for = OPPOSE
            organization_id = 0
            ballot_item_oppose_results = retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(
                voter_id, organization_id, one_voter_guide.organization_we_vote_id, stance_we_are_looking_for,
                one_position.google_civic_election_id)

            if ballot_item_oppose_results['count']:
                ballot_item_we_vote_ids_this_org_opposes = ballot_item_oppose_results['ballot_item_we_vote_ids_list']
            else:
                ballot_item_we_vote_ids_this_org_opposes = []

            one_voter_guide.ballot_item_we_vote_ids_this_org_opposes = \
                ballot_item_we_vote_ids_this_org_opposes

            # If we passed in search_string, make sure they are in this entry.
            # If they aren't, don't return voter guide
            if positive_value_exists(search_string):
                search_string = str(search_string)  # Make sure search_string is a string
                twitter_handle = str(one_voter_guide.twitter_handle)
                display_name = str(one_voter_guide.display_name)

                if search_string.lower() in twitter_handle.lower() or search_string.lower() in display_name.lower():
                    voter_guide_list.append(one_voter_guide)
            else:
                voter_guide_list.append(one_voter_guide)

    status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_BY_BALLOT_ITEM'
    success = True

    if len(voter_guide_list):
        voter_guide_list_found = True

    results = {
        'success':                      success,
        'status':                       status,
        'search_string':                search_string,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def retrieve_voter_guides_to_follow_by_election_for_api(voter_id, google_civic_election_id, search_string,
                                                        filter_voter_guides_by_issue=False,
                                                        organization_we_vote_id_list_for_voter_issues=None,
                                                        start_retrieve_at_this_number=0,
                                                        maximum_number_to_retrieve=0, sort_by='', sort_order=''):
    filter_voter_guides_by_issue = positive_value_exists(filter_voter_guides_by_issue)

    voter_guide_list_found = False
    status = ""
    status += "voter_id: " + str(voter_id) + " "

    # Start with orgs followed and ignored by this voter
    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organization_we_vote_ids_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
            voter_id, return_we_vote_id, read_only=True)
    organization_we_vote_ids_ignored_by_voter = \
        follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(
            voter_id, return_we_vote_id, read_only=True)

    # position_list_manager = PositionListManager()
    if not positive_value_exists(google_civic_election_id):
        voter_guide_list = []
        results = {
            'success':                      False,
            'status':                       "VOTER_GUIDES_BALLOT_RELATED_VARIABLES_MISSING",
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    # Retrieve all voter guides for this election
    voter_guide_list_manager = VoterGuideListManager()
    org_list_found_by_google_civic_election_id = []
    voter_guide_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_by_election(
        google_civic_election_id, org_list_found_by_google_civic_election_id, search_string,
        start_retrieve_at_this_number,
        maximum_number_to_retrieve, sort_by, sort_order, read_only=True)

    status += " " + voter_guide_results['status'] + " "

    if voter_guide_results['voter_guide_list_found']:
        voter_guide_list = voter_guide_results['voter_guide_list']
    else:
        voter_guide_list = []

    if filter_voter_guides_by_issue and organization_we_vote_id_list_for_voter_issues is not None:
        # Only include voter guides from organizations in organization_we_vote_id_list_for_voter_issues
        voter_guide_list = only_include_these_voter_guides_for_voter(
            voter_guide_list, organization_we_vote_id_list_for_voter_issues)

    # Now remove voter guides from organizations that voter is ignoring
    voter_guide_list = remove_voter_guides_for_voter(voter_guide_list, organization_we_vote_ids_ignored_by_voter)

    # Now remove voter guides from organizations that the voter is already following
    voter_guide_list = remove_voter_guides_for_voter(voter_guide_list, organization_we_vote_ids_followed_by_voter)

    if not len(voter_guide_list):
        # If no positions are found, exit
        voter_guide_list = []
        results = {
            'success':                      True,
            'status':                       "NO_VOTER_GUIDES_TO_FOLLOW_FOUND_FOR_THIS_ELECTION-FOR_VOTER",
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    status += 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_BY_ELECTION '
    success = True

    if len(voter_guide_list):
        voter_guide_list_found = True
        updated_voter_guide_list = []
        for one_voter_guide in voter_guide_list:
            # Augment the voter guide with a list of ballot_item we_vote_id's that this org supports
            stance_we_are_looking_for = SUPPORT
            organization_id = 0
            ballot_item_support_results = retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(
                voter_id, organization_id, one_voter_guide.organization_we_vote_id, stance_we_are_looking_for,
                google_civic_election_id)  # Already read_only

            if ballot_item_support_results['count']:
                ballot_item_we_vote_ids_this_org_supports = ballot_item_support_results['ballot_item_we_vote_ids_list']
            else:
                ballot_item_we_vote_ids_this_org_supports = []

            one_voter_guide.ballot_item_we_vote_ids_this_org_supports = ballot_item_we_vote_ids_this_org_supports

            # Augment the voter guide with a list of ballot_item we_vote_id's that this org has info about
            stance_we_are_looking_for = INFORMATION_ONLY
            organization_id = 0
            ballot_item_info_only_results = retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(
                voter_id, organization_id, one_voter_guide.organization_we_vote_id, stance_we_are_looking_for,
                google_civic_election_id)

            if ballot_item_info_only_results['count']:
                ballot_item_we_vote_ids_this_org_info_only = \
                    ballot_item_info_only_results['ballot_item_we_vote_ids_list']
            else:
                ballot_item_we_vote_ids_this_org_info_only = []

            one_voter_guide.ballot_item_we_vote_ids_this_org_info_only = ballot_item_we_vote_ids_this_org_info_only

            # Augment the voter guide with a list of ballot_item we_vote_id's that this org opposes
            stance_we_are_looking_for = OPPOSE
            organization_id = 0
            ballot_item_oppose_results = retrieve_ballot_item_we_vote_ids_for_organizations_to_follow(
                voter_id, organization_id, one_voter_guide.organization_we_vote_id, stance_we_are_looking_for,
                google_civic_election_id)

            if ballot_item_oppose_results['count']:
                ballot_item_we_vote_ids_this_org_opposes = ballot_item_oppose_results['ballot_item_we_vote_ids_list']
            else:
                ballot_item_we_vote_ids_this_org_opposes = []

            one_voter_guide.ballot_item_we_vote_ids_this_org_opposes = ballot_item_we_vote_ids_this_org_opposes

            updated_voter_guide_list.append(one_voter_guide)
        voter_guide_list = updated_voter_guide_list

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def voter_guides_upcoming_retrieve_for_api(google_civic_election_id_list=[]):  # voterGuidesUpcomingRetrieve
    status = ""

    voter_guides = []
    status += "RETRIEVING_VOTER_GUIDES_UPCOMING "

    if not positive_value_exists(google_civic_election_id_list) or \
            not positive_value_exists(len(google_civic_election_id_list)):
        # Figure out the next elections upcoming
        election_manager = ElectionManager()
        results = election_manager.retrieve_upcoming_elections()
        if results['election_list_found']:
            election_list = results['election_list']
            google_civic_election_id_list = []
            for one_election in election_list:
                google_civic_election_id_list.append(one_election.google_civic_election_id)

    voter_guide_list_manager = VoterGuideListManager()
    voter_guide_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_generic(
        maximum_number_to_retrieve=500, sort_by='twitter_followers_count', sort_order='desc',
        google_civic_election_id_list=google_civic_election_id_list, read_only=True)

    if voter_guide_results['voter_guide_list_found']:
        voter_guide_list = voter_guide_results['voter_guide_list']
    else:
        voter_guide_list = []

    success = voter_guide_results['success']
    status += voter_guide_results['status']

    organization_manager = OrganizationManager()
    for voter_guide in voter_guide_list:
        organization_we_vote_id = voter_guide.organization_we_vote_id
        google_civic_election_id = voter_guide.google_civic_election_id

        if not positive_value_exists(organization_we_vote_id) or not positive_value_exists(google_civic_election_id):
            # We can't use a voter_guide that doesn't have both of these values
            continue

        results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id, read_only=True)

        if not results['organization_found']:
            # We can't use a voter_guide that does not have a valid organization attached
            continue

        organization = results['organization']

        # Augment the voter guide with a list of ballot_item we_vote_id's that this org supports
        stance_we_are_looking_for = SUPPORT
        ballot_item_support_results = retrieve_ballot_item_we_vote_ids_for_organization_static(
            organization, google_civic_election_id, stance_we_are_looking_for)  # Already read_only
        if ballot_item_support_results['count']:
            ballot_item_we_vote_ids_this_org_supports = ballot_item_support_results[
                'ballot_item_we_vote_ids_list']
        else:
            ballot_item_we_vote_ids_this_org_supports = []
        voter_guide.ballot_item_we_vote_ids_this_org_supports = ballot_item_we_vote_ids_this_org_supports

        # Augment the voter guide with a list of ballot_item we_vote_id's that this org has info about
        stance_we_are_looking_for = INFORMATION_ONLY
        ballot_item_info_only_results = retrieve_ballot_item_we_vote_ids_for_organization_static(
            organization, google_civic_election_id, stance_we_are_looking_for)  # Already read_only
        if ballot_item_info_only_results['count']:
            ballot_item_we_vote_ids_this_org_info_only = \
                ballot_item_info_only_results['ballot_item_we_vote_ids_list']
        else:
            ballot_item_we_vote_ids_this_org_info_only = []
        voter_guide.ballot_item_we_vote_ids_this_org_info_only = ballot_item_we_vote_ids_this_org_info_only

        # Augment the voter guide with a list of ballot_item we_vote_id's that this org opposes
        stance_we_are_looking_for = OPPOSE
        ballot_item_oppose_results = retrieve_ballot_item_we_vote_ids_for_organization_static(
            organization, google_civic_election_id, stance_we_are_looking_for)  # Already read_only
        if ballot_item_oppose_results['count']:
            ballot_item_we_vote_ids_this_org_opposes = ballot_item_oppose_results[
                'ballot_item_we_vote_ids_list']
        else:
            ballot_item_we_vote_ids_this_org_opposes = []
        voter_guide.ballot_item_we_vote_ids_this_org_opposes = ballot_item_we_vote_ids_this_org_opposes

        # If there aren't any opinions in the voter guide, skip it and don't return it
        if not len(ballot_item_we_vote_ids_this_org_supports) and \
                not len(ballot_item_we_vote_ids_this_org_info_only) and \
                not len(ballot_item_we_vote_ids_this_org_opposes):
            continue

        organization_link_to_issue_list = OrganizationLinkToIssueList()
        issue_we_vote_ids_linked = \
            organization_link_to_issue_list.fetch_issue_we_vote_id_list_by_organization_we_vote_id(
                voter_guide.organization_we_vote_id)
        if voter_guide.last_updated:
            last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
        else:
            last_updated = ''
        one_voter_guide = {
            'ballot_item_we_vote_ids_this_org_supports':    ballot_item_we_vote_ids_this_org_supports,
            'ballot_item_we_vote_ids_this_org_info_only':   ballot_item_we_vote_ids_this_org_info_only,
            'ballot_item_we_vote_ids_this_org_opposes':     ballot_item_we_vote_ids_this_org_opposes,
            'election_day_text':            voter_guide.election_day_text,
            'google_civic_election_id':     voter_guide.google_civic_election_id,
            'issue_we_vote_ids_linked':     issue_we_vote_ids_linked,
            'last_updated':                 last_updated,
            'organization_we_vote_id':      voter_guide.organization_we_vote_id,
            'owner_voter_id':               voter_guide.owner_voter_id,
            'pledge_goal':                  voter_guide.pledge_goal,
            'pledge_count':                 voter_guide.pledge_count,
            'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
            'time_span':                    voter_guide.vote_smart_time_span,
            'twitter_description':          voter_guide.twitter_description,
            'twitter_followers_count':      voter_guide.twitter_followers_count,
            'twitter_handle':               voter_guide.twitter_handle,
            'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
            'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
            if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
            else voter_guide.voter_guide_image_url(),
            'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
            'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
            'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
            'we_vote_id':                   voter_guide.we_vote_id,
        }

        voter_guides.append(one_voter_guide.copy())
        # if positive_value_exists(maximum_number_to_retrieve):
        #     number_added_to_list += 1
        #     if number_added_to_list >= maximum_number_to_retrieve:
        #         break

    number_retrieved = len(voter_guides)
    json_data = {
        'status': 'VOTER_GUIDES_TO_FOLLOW_FOR_API_RETRIEVED: ' + status,
        'success': True,
        'voter_guides': voter_guides,
        'number_retrieved': number_retrieved,
    }

    results = {
        'success': success,
        'status': 'VOTER_GUIDES_TO_FOLLOW_FOR_API_RETRIEVED: ' + status,
        'json_data': json_data,
    }
    return results


def remove_voter_guides_for_voter(voter_guide_list, organizations_we_vote_ids_to_remove):
    if not positive_value_exists(len(organizations_we_vote_ids_to_remove)):
        # There aren't any organization_we_vote_ids to remove, so just return original list
        return voter_guide_list

    voter_guide_list_modified = []
    for one_voter_guide in voter_guide_list:
        if one_voter_guide.organization_we_vote_id not in organizations_we_vote_ids_to_remove:
            voter_guide_list_modified.append(one_voter_guide)

    return voter_guide_list_modified


def only_include_these_voter_guides_for_voter(voter_guide_list, organizations_we_vote_ids_to_keep):
    if not positive_value_exists(len(organizations_we_vote_ids_to_keep)):
        # There aren't any organization_we_vote_ids to remove, so just return original list
        return []

    voter_guide_list_modified = []
    for one_voter_guide in voter_guide_list:
        if one_voter_guide.organization_we_vote_id in organizations_we_vote_ids_to_keep:
            voter_guide_list_modified.append(one_voter_guide)

    return voter_guide_list_modified


def retrieve_voter_guides_to_follow_generic_for_api(voter_id, search_string, filter_voter_guides_by_issue=False,
                                                    organization_we_vote_id_list_for_voter_issues=None,
                                                    maximum_number_to_retrieve=0, sort_by='', sort_order=''):
    """
    Separate from an election or a ballot item, return a list of voter_guides the voter has not already followed
    :param voter_id:
    :param search_string:
    :param filter_voter_guides_by_issue:
    :param organization_we_vote_id_list_for_voter_issues:
    :param maximum_number_to_retrieve:
    :param sort_by:
    :param sort_order:
    :return:
    """
    filter_voter_guides_by_issue = positive_value_exists(filter_voter_guides_by_issue)
    voter_guide_list_found = False

    # Start with organizations followed and ignored by this voter
    return_we_vote_id = True
    follow_organization_list_manager = FollowOrganizationList()
    if positive_value_exists(search_string):
        # If we are searching for organizations, we don't want to limit the search
        organization_we_vote_ids_followed_by_voter = []
        organization_we_vote_ids_ignored_by_voter = []
    else:
        read_only = True
        organization_we_vote_ids_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
                voter_id, return_we_vote_id, read_only=read_only)
        organization_we_vote_ids_ignored_by_voter = \
            follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(
                voter_id, return_we_vote_id, read_only=read_only)

    # This is a list of orgs that the voter is already following or ignoring
    organization_we_vote_ids_followed_or_ignored_by_voter = list(chain(organization_we_vote_ids_followed_by_voter,
                                                                       organization_we_vote_ids_ignored_by_voter))

    voter_guide_list_manager = VoterGuideListManager()

    # First, retrieve the voter_guides stored by org and google_civic_election_id
    voter_guide_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_generic(
        organization_we_vote_ids_followed_or_ignored_by_voter, search_string,
        maximum_number_to_retrieve, sort_by, sort_order, read_only=True)

    if voter_guide_results['voter_guide_list_found']:
        voter_guide_list = voter_guide_results['voter_guide_list']
    else:
        voter_guide_list = []

    position_list_manager = PositionListManager()
    if filter_voter_guides_by_issue and organization_we_vote_id_list_for_voter_issues is not None:
        voter_guide_list = position_list_manager.remove_positions_unrelated_to_issues(
            voter_guide_list, organization_we_vote_id_list_for_voter_issues)

    status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_GENERIC '
    success = True

    if len(voter_guide_list):
        voter_guide_list_found = True

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def voter_guide_save_for_api(voter_device_id, voter_guide_we_vote_id, google_civic_election_id):  # voterGuideSave
    """
    This function lets us create a new voter guide or update an existing one.
    :param voter_device_id:
    :param voter_guide_we_vote_id:
    :param google_civic_election_id:
    :return:
    """
    success = False
    status = ""
    voter_guide = VoterGuide()
    # organization = Organization()
    if not positive_value_exists(voter_device_id):
        status += 'VALID_VOTER_DEVICE_ID_MISSING'
        json_data = {
            'status':                       status,
            'success':                      False,
            'we_vote_id':                   voter_guide_we_vote_id,
            'google_civic_election_id':     google_civic_election_id,
            'time_span':                    "",
            'voter_guide_display_name':     "",
            'voter_guide_image_url_large':  "",
            'voter_guide_image_url_medium': "",
            'voter_guide_image_url_tiny':   "",
            'voter_guide_owner_type':       "",
            'organization_we_vote_id':      "",
            'public_figure_we_vote_id':     "",
            'twitter_description':          "",
            'twitter_followers_count':      0,
            'twitter_handle':               "",
            'owner_voter_id':               0,
            'pledge_goal':                  0,
            'pledge_count':                 0,
            'last_updated':                 "",
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter = None
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = 0
    voter_full_name = ""
    linked_organization_we_vote_id = ""
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_full_name = voter.get_full_name()
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    if not positive_value_exists(voter_id):
        status += 'VALID_VOTER_ID_MISSING'
        json_data = {
            'status':                       status,
            'success':                      False,
            'we_vote_id':                   voter_guide_we_vote_id,
            'google_civic_election_id':     google_civic_election_id,
            'time_span':                    "",
            'voter_guide_display_name':     "",
            'voter_guide_image_url_large':  "",
            'voter_guide_image_url_medium': "",
            'voter_guide_image_url_tiny':   "",
            'voter_guide_owner_type':       "",
            'organization_we_vote_id':      linked_organization_we_vote_id,
            'public_figure_we_vote_id':     "",
            'twitter_description':          "",
            'twitter_followers_count':      0,
            'twitter_handle':               "",
            'owner_voter_id':               0,
            'pledge_goal':                  0,
            'pledge_count':                 0,
            'last_updated':                 "",
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_guide_manager = VoterGuideManager()
    if positive_value_exists(voter_guide_we_vote_id):
        results = voter_guide_manager.retrieve_voter_guide(voter_guide_we_vote_id=voter_guide_we_vote_id)
        voter_guide_found = False
        status += results['status']
        if results['voter_guide_found']:
            voter_guide = results['voter_guide']
            if voter_guide.id:
                voter_guide_found = True
                success = True
        # If a voter_guide_we_vote_id is passed in and not found, we want to exit and NOT create a new one
        if not positive_value_exists(voter_guide_found):
            status += "VOTER_GUIDE_SAVE-VOTER_GUIDE_NOT_FOUND "
            json_data = {
                'status':                       status,
                'success':                      False,
                'we_vote_id':                   voter_guide_we_vote_id,
                'google_civic_election_id':     google_civic_election_id,
                'time_span':                    "",
                'voter_guide_display_name':     "",
                'voter_guide_image_url_large':  "",
                'voter_guide_image_url_medium': "",
                'voter_guide_image_url_tiny':   "",
                'voter_guide_owner_type':       "",
                'organization_we_vote_id':      linked_organization_we_vote_id,
                'public_figure_we_vote_id':     "",
                'twitter_description':          "",
                'twitter_followers_count':      0,
                'twitter_handle':               "",
                'owner_voter_id':               0,
                'pledge_goal':                  0,
                'pledge_count':                 0,
                'last_updated':                 "",
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        organization_manager = OrganizationManager()
        if positive_value_exists(linked_organization_we_vote_id):
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(linked_organization_we_vote_id)
            if organization_results['organization_found']:
                status += "ORGANIZATION_FOUND "
                organization = organization_results['organization']
                # linked_organization_we_vote_id = organization.we_vote_id
            else:
                status += "ORGANIZATION_NOT_FOUND_EVEN_THOUGH_WE_VOTE_ID_TIED_TO_VOTER: "
                status += organization_results['status']
                linked_organization_we_vote_id = ""
                voter_manager = VoterManager()
                if positive_value_exists(voter_id):
                    # We want to remove the previously linked organization_we_vote_id
                    voter_manager.alter_linked_organization_we_vote_id(voter, None)

        if not positive_value_exists(linked_organization_we_vote_id):
            organization_create_results = organization_manager.create_organization(
                voter_full_name, organization_website="", organization_twitter_handle="",
                organization_type=INDIVIDUAL)
            if organization_create_results['organization_created']:
                organization = organization_create_results['organization']
                linked_organization_we_vote_id = organization.we_vote_id
                # Save the new linked_organization_we_vote_id
                results = voter_manager.alter_linked_organization_we_vote_id(voter, linked_organization_we_vote_id)
                if not results['success']:
                    status += "COULD_NOT_LINK_VOTER_TO_NEW_ORGANIZATION: " + results['status'] + " "
                    linked_organization_we_vote_id = ""
            else:
                status += organization_create_results['status']

        if not positive_value_exists(linked_organization_we_vote_id):
            status += 'LINKED_ORGANIZATION_NOT_FOUND '
            json_data = {
                'status':                       status,
                'success':                      False,
                'we_vote_id':                   voter_guide_we_vote_id,
                'google_civic_election_id':     google_civic_election_id,
                'time_span':                    "",
                'voter_guide_display_name':     "",
                'voter_guide_image_url_large':  "",
                'voter_guide_image_url_medium': "",
                'voter_guide_image_url_tiny':   "",
                'voter_guide_owner_type':       "",
                'organization_we_vote_id':      linked_organization_we_vote_id,
                'public_figure_we_vote_id':     "",
                'twitter_description':          "",
                'twitter_followers_count':      0,
                'twitter_handle':               "",
                'owner_voter_id':               0,
                'pledge_goal':                  0,
                'pledge_count':                 0,
                'last_updated':                 "",
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')

        results = voter_guide_manager.retrieve_voter_guide(google_civic_election_id=google_civic_election_id,
                                                           organization_we_vote_id=linked_organization_we_vote_id)
        voter_guide_found = False
        voter_guide_does_not_exist = False
        status += results['status']
        if results['voter_guide_found']:
            status += "VOTER_GUIDE_FOUND "
            voter_guide = results['voter_guide']
            if voter_guide.we_vote_id:
                voter_guide_found = True
                success = True
        elif results['MultipleObjectsReturned']:
            # Duplicates found. We need to deduplicate.
            success = False
            duplicate_results = voter_guide_manager.merge_duplicate_voter_guides_for_organization_and_election(
                linked_organization_we_vote_id, google_civic_election_id)
            status += duplicate_results['status']
            if duplicate_results['voter_guide_found']:
                success = True
                voter_guide_found = True
                voter_guide = duplicate_results['voter_guide']
                update_results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                    voter_guide.we_vote_id,
                    linked_organization_we_vote_id,
                    google_civic_election_id)
                status += update_results['status']
                if update_results['voter_guide_saved']:
                    voter_guide = update_results['voter_guide']
        else:
            voter_guide_does_not_exist = True

        if not voter_guide_found:
            status += "VOTER_GUIDE_NOT_FOUND google_civic_election_id: " + str(google_civic_election_id) \
                      + " linked_organization_we_vote_id: " + str(linked_organization_we_vote_id) + " "

        if voter_guide_does_not_exist:
            status += "VOTER_GUIDE_DOES_NOT_EXIST-CREATE_NEW "
            create_results = voter_guide_manager.update_or_create_voter_voter_guide(
                google_civic_election_id=google_civic_election_id,
                voter=voter)
            if create_results['voter_guide_created'] or create_results['voter_guide_saved']:
                status += "VOTER_GUIDE_CREATED "
                voter_guide_found = True
                success = True
                voter_guide = create_results['voter_guide']
            else:
                status += "VOTER_GUIDE_COULD_NOT_BE_UPDATED_OR_CREATED: " + create_results['status'] + " "

    try:
        organization
    except NameError:
        organization_exists = False
    else:
        organization_exists = True

    if voter_guide_found and positive_value_exists(linked_organization_we_vote_id) and organization_exists:
        refresh_results = voter_guide_manager.refresh_one_voter_guide_from_organization(voter_guide, organization)
        if refresh_results['values_changed']:
            status += "VOTER_GUIDE_VALUES_CHANGED "
            voter_guide = refresh_results['voter_guide']
            try:
                voter_guide.save()
                success = True
                status += "VOTER_GUIDE_REFRESHED "
            except Exception as e:
                success = False
                status += "COULD_NOT_REFRESH_VOTER_GUIDE " + str(e)
        else:
            status += "VOTER_GUIDE_VALUES_DID_NOT_CHANGE "
    else:
        status += "COULD_NOT_REFRESH_VOTER_GUIDE "

    if voter_guide.last_updated:
        last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
    else:
        last_updated = ''
    json_data = {
        'status': status,
        'success': success,
        'we_vote_id': voter_guide.we_vote_id,
        'google_civic_election_id': voter_guide.google_civic_election_id,
        'time_span': voter_guide.vote_smart_time_span,
        'voter_guide_display_name': voter_guide.voter_guide_display_name(),
        'voter_guide_image_url_large': voter_guide.we_vote_hosted_profile_image_url_large
        if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
        else voter_guide.voter_guide_image_url(),
        'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
        'voter_guide_image_url_tiny': voter_guide.we_vote_hosted_profile_image_url_tiny,
        'voter_guide_owner_type': voter_guide.voter_guide_owner_type,
        'organization_we_vote_id': linked_organization_we_vote_id,
        'public_figure_we_vote_id': voter_guide.public_figure_we_vote_id,
        'twitter_description': voter_guide.twitter_description,
        'twitter_followers_count': voter_guide.twitter_followers_count,
        'twitter_handle': voter_guide.twitter_handle,
        'owner_voter_id': voter_guide.owner_voter_id,
        'pledge_goal': voter_guide.pledge_goal,
        'pledge_count': voter_guide.pledge_count,
        'last_updated': last_updated,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guides_followed_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0):
    """
    voter_guides_followed_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0)  # voterGuidesFollowedRetrieve
    Start with the organizations followed and return a list of voter_guides.
    See also organizations_followed_for_api, which returns a list of organizations.

    :param voter_device_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = retrieve_voter_guides_followed(voter_id)
    status = results['status']
    voter_guide_list = results['voter_guide_list']
    voter_guides = []
    if results['voter_guide_list_found']:
        pledge_to_vote_manager = PledgeToVoteManager()
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_id(voter_id)
        number_added_to_list = 0
        for voter_guide in voter_guide_list:
            pledge_to_vote_we_vote_id = ""
            pledge_results = pledge_to_vote_manager.retrieve_pledge_to_vote(
                pledge_to_vote_we_vote_id, voter_we_vote_id, voter_guide.we_vote_id)
            if pledge_results['pledge_found']:
                voter_has_pledged = pledge_results['voter_has_pledged']
            else:
                voter_has_pledged = False
            if voter_guide.last_updated:
                last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ''
            one_voter_guide = {
                'we_vote_id':                   voter_guide.we_vote_id,
                'google_civic_election_id':     voter_guide.google_civic_election_id,
                'time_span':                    voter_guide.vote_smart_time_span,
                'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
                'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
                    else voter_guide.voter_guide_image_url(),
                'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
                'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
                'organization_we_vote_id':      voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
                'twitter_description':          voter_guide.twitter_description,
                'twitter_followers_count':      voter_guide.twitter_followers_count,
                'twitter_handle':               voter_guide.twitter_handle,
                'owner_voter_id':               voter_guide.owner_voter_id,
                'pledge_goal':                  voter_guide.pledge_goal,
                'pledge_count':                 voter_guide.pledge_count,
                'voter_has_pledged':            voter_has_pledged,
                'last_updated':                 last_updated,
            }
            voter_guides.append(one_voter_guide.copy())
            # If we have passed in a limit (that is not zero), honor it
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            status += 'VOTER_GUIDES_FOLLOWED_RETRIEVED '
            success = True
        else:
            status += 'NO_VOTER_GUIDES_FOLLOWED_FOUND '
            success = True
    else:
        success = False

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'maximum_number_to_retrieve': maximum_number_to_retrieve,
        'voter_guides': voter_guides,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guides_retrieve_for_api(voter_device_id, organization_we_vote_id="", voter_we_vote_id="",
                                  maximum_number_to_retrieve=0):
    """
    voter_guides_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0)  # voterGuidesRetrieve
    This function allows us to search for voter guides using a variety of criteria.
    :param voter_device_id:
    :param organization_we_vote_id:
    :param voter_we_vote_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_guide_list_manager = VoterGuideListManager()
    results = voter_guide_list_manager.retrieve_all_voter_guides(organization_we_vote_id, 0, voter_we_vote_id)
    status = results['status']
    voter_guide_list = results['voter_guide_list']
    voter_guides = []
    if results['voter_guide_list_found']:
        number_added_to_list = 0
        for voter_guide in voter_guide_list:
            if voter_guide.last_updated:
                last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ''
            one_voter_guide = {
                'we_vote_id':                   voter_guide.we_vote_id,
                'google_civic_election_id':     voter_guide.google_civic_election_id,
                'election_day_text':            voter_guide.election_day_text,
                'time_span':                    voter_guide.vote_smart_time_span,
                'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
                'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
                if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
                else voter_guide.voter_guide_image_url(),
                'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
                'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
                'organization_we_vote_id':      voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
                'twitter_description':          voter_guide.twitter_description,
                'twitter_followers_count':      voter_guide.twitter_followers_count,
                'twitter_handle':               voter_guide.twitter_handle,
                'owner_voter_id':               voter_guide.owner_voter_id,
                'pledge_goal':                  voter_guide.pledge_goal,
                'pledge_count':                 voter_guide.pledge_count,
                'last_updated':                 last_updated,
            }
            voter_guides.append(one_voter_guide.copy())
            # If we have passed in a limit (that is not zero), honor it
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            status += 'NO_VOTER_GUIDES_RETRIEVED '
            success = True
        else:
            status += 'NO_VOTER_GUIDE_LIST_FOUND1 '
            success = True
    else:
        status += 'NO_VOTER_GUIDE_LIST_FOUND2 '
        success = False

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'maximum_number_to_retrieve': maximum_number_to_retrieve,
        'voter_guides': voter_guides,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_follow_all_organizations_followed_by_organization_for_api(voter_device_id,
                                                                    organization_we_vote_id,
                                                                    maximum_number_to_follow=0,
                                                                    user_agent_string='', user_agent_object=None):
    # voterGuidesFollowedByOrganizationRetrieve
    """
    Retrieve organizations followed by organization_we_vote_id and follow all.

    :param voter_device_id:
    :param organization_we_vote_id:
    :param maximum_number_to_follow:
    :param user_agent_string:
    :param user_agent_object:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status':                       'VALID_VOTER_DEVICE_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_follow':     maximum_number_to_follow,
            'voter_guides':                 [],
            'organization_we_vote_id':      organization_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                       'VALID_VOTER_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_follow':     maximum_number_to_follow,
            'voter_guides':                 [],
            'organization_we_vote_id':      organization_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    if not voter_results['voter_found']:
        json_data = {
            'status':                       'VOTER_NOT_FOUND',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_follow':     maximum_number_to_follow,
            'voter_guides':                 [],
            'organization_we_vote_id':      organization_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not positive_value_exists(organization_we_vote_id):
        json_data = {
            'status':                       'ORGANIZATION_WE_VOTE_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_follow':     maximum_number_to_follow,
            'voter_guides':                 [],
            'organization_we_vote_id':      organization_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Retrieve all organizations already followed by voter
    organizations_followed_by_voter_results = retrieve_organizations_followed_by_organization_we_vote_id(
        voter_results['voter'].linked_organization_we_vote_id)
    organizations_we_vote_ids_list_followed_by_voter = \
        organizations_followed_by_voter_results['organization_we_vote_ids_followed_list']

    # Retrieve all organizations followed by this organization
    organizations_followed_by_we_vote_id_results = retrieve_organizations_followed_by_organization_we_vote_id(
        organization_we_vote_id)
    organizations_we_vote_ids_list_followed_by_organization_we_vote_id = \
        organizations_followed_by_we_vote_id_results['organization_we_vote_ids_followed_list']

    # If some organizations are already followed by voter then do not follow again.
    organization_we_vote_ids_list_need_to_be_followed = []
    for organization_followed_by_we_vote_id in organizations_we_vote_ids_list_followed_by_organization_we_vote_id:
        if organization_followed_by_we_vote_id not in organizations_we_vote_ids_list_followed_by_voter:
            organization_we_vote_ids_list_need_to_be_followed.append(organization_followed_by_we_vote_id)

    success = True
    status = organizations_followed_by_we_vote_id_results['status']
    organizations_follow_all_results = []
    if len(organization_we_vote_ids_list_need_to_be_followed):
        number_added_to_list = 0
        for organization_we_vote_id_followed in organization_we_vote_ids_list_need_to_be_followed:
            organization_follow_result = organization_follow_or_unfollow_or_ignore(
                voter_device_id, organization_id=0, organization_we_vote_id=organization_we_vote_id_followed,
                follow_kind=FOLLOWING, user_agent_string=user_agent_string, user_agent_object=user_agent_object)
            if not organization_follow_result['success']:
                success = False

            organizations_follow_all_results.append(organization_follow_result)
            if positive_value_exists(maximum_number_to_follow):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_follow:
                    break

    json_data = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'maximum_number_to_follow':         maximum_number_to_follow,
        'organizations_follow_all_results': organizations_follow_all_results,
        'organization_we_vote_id':          organization_we_vote_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guides_followed_by_organization_retrieve_for_api(voter_device_id,  # voterGuidesFollowedByOrganizationRetrieve
                                                           voter_linked_organization_we_vote_id,
                                                           filter_by_this_google_civic_election_id=False,
                                                           maximum_number_to_retrieve=0):
    """
    Start with the organizations followed and return a list of voter_guides. voterGuidesFollowedByOrganizationRetrieve
    See also organizations_followed_for_api, which returns a list of organizations.

    :param voter_device_id:
    :param voter_linked_organization_we_vote_id:
    :param filter_by_this_google_civic_election_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    status = ""
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status':                       'VALID_VOTER_DEVICE_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_retrieve':   maximum_number_to_retrieve,
            'voter_guides':                 [],
            'organization_we_vote_id':      voter_linked_organization_we_vote_id,
            'filter_by_this_google_civic_election_id':  filter_by_this_google_civic_election_id
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                       'VALID_VOTER_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_retrieve':   maximum_number_to_retrieve,
            'voter_guides':                 [],
            'organization_we_vote_id':      voter_linked_organization_we_vote_id,
            'filter_by_this_google_civic_election_id':  filter_by_this_google_civic_election_id
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id)
    status += results['status'] + 'VOTER_NOT_FOUND'
    if not results['voter_found']:
        json_data = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'maximum_number_to_retrieve':   maximum_number_to_retrieve,
            'voter_guides':                 [],
            'organization_we_vote_id':      voter_linked_organization_we_vote_id,
            'filter_by_this_google_civic_election_id':  filter_by_this_google_civic_election_id
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter = results['voter']
    voter_we_vote_id = voter.we_vote_id
    results = retrieve_voter_guides_followed_by_organization_we_vote_id(voter_linked_organization_we_vote_id,
                                                                        filter_by_this_google_civic_election_id)
    status += results['status']
    voter_guide_list = results['voter_guide_list']
    voter_guides = []
    if results['voter_guide_list_found']:
        pledge_to_vote_manager = PledgeToVoteManager()
        number_added_to_list = 0
        for voter_guide in voter_guide_list:
            pledge_to_vote_we_vote_id = ""
            pledge_results = pledge_to_vote_manager.retrieve_pledge_to_vote(
                pledge_to_vote_we_vote_id, voter_we_vote_id, voter_guide.we_vote_id)
            if pledge_results['pledge_found']:
                voter_has_pledged = pledge_results['voter_has_pledged']
            else:
                voter_has_pledged = False
            if voter_guide.last_updated:
                last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ''
            one_voter_guide = {
                'we_vote_id':                   voter_guide.we_vote_id,
                'google_civic_election_id':     voter_guide.google_civic_election_id,
                'time_span':                    voter_guide.vote_smart_time_span,
                'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
                'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
                    else voter_guide.voter_guide_image_url(),
                'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
                'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
                'organization_we_vote_id':      voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
                'twitter_description':          voter_guide.twitter_description,
                'twitter_followers_count':      voter_guide.twitter_followers_count,
                'twitter_handle':               voter_guide.twitter_handle,
                'owner_voter_id':               voter_guide.owner_voter_id,
                'pledge_goal':                  voter_guide.pledge_goal,
                'pledge_count':                 voter_guide.pledge_count,
                'voter_has_pledged':            voter_has_pledged,
                'last_updated':                 last_updated,
            }
            voter_guides.append(one_voter_guide.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            status += 'VOTER_GUIDES_FOLLOWED_BY_ORGANIZATION_RETRIEVED '
            success = True
        else:
            status += 'NO_VOTER_GUIDES_FOLLOWED_BY_ORGANIZATION_FOUND '
            success = True
    else:
        success = False

    json_data = {
        'status':                       status,
        'success':                      success,
        'voter_device_id':              voter_device_id,
        'maximum_number_to_retrieve':   maximum_number_to_retrieve,
        'voter_guides':                 voter_guides,
        'organization_we_vote_id':      voter_linked_organization_we_vote_id,
        'filter_by_this_google_civic_election_id':  filter_by_this_google_civic_election_id
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_followers_retrieve_for_api(voter_device_id, organization_we_vote_id,  # voterGuideFollowersRetrieve
                                           maximum_number_to_retrieve=0):
    """
    Start with the organizations followed and return a list of voter_guides. voterGuidesFollowedByOrganizationRetrieve
    See also organizations_followed_for_api, which returns a list of organizations.

    :param voter_device_id:
    :param organization_we_vote_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status':                       'VALID_VOTER_DEVICE_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'maximum_number_to_retrieve':   maximum_number_to_retrieve,
            'voter_guides':                 [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                       'VALID_VOTER_ID_MISSING',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'maximum_number_to_retrieve':   maximum_number_to_retrieve,
            'voter_guides':                 [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if not results['voter_found']:
        json_data = {
            'status':                       'VOTER_NOT_FOUND',
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'maximum_number_to_retrieve':   maximum_number_to_retrieve,
            'voter_guides':                 [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = retrieve_voter_guide_followers_by_organization_we_vote_id(organization_we_vote_id)
    status = results['status']
    voter_guides = []
    if results['organization_list_found']:
        organization_list = results['organization_list']
        number_added_to_list = 0
        for one_organization in organization_list:
            if not positive_value_exists(one_organization.organization_name):
                continue
            elif one_organization.organization_name.startswith("Voter-"):
                continue

            date_last_changed = one_organization.date_last_changed
            if positive_value_exists(date_last_changed):
                last_updated = date_last_changed.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ""
            # pledge_to_vote_manager = PledgeToVoteManager()
            # pledge_results = pledge_to_vote_manager.retrieve_pledge_statistics()
            # TODO We don't have a voter_guide_we_vote_id here so it is hard to get the right pledge_statistics
            one_voter_guide = {
                'voter_guide_display_name':     one_organization.organization_name,
                'voter_guide_image_url_large':  one_organization.we_vote_hosted_profile_image_url_large
                if positive_value_exists(one_organization.we_vote_hosted_profile_image_url_large)
                else one_organization.organization_photo_url(),
                'voter_guide_image_url_medium': one_organization.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   one_organization.we_vote_hosted_profile_image_url_tiny,
                'organization_we_vote_id':      one_organization.we_vote_id,
                'twitter_description':          one_organization.twitter_description,
                'twitter_followers_count':      one_organization.twitter_followers_count,
                'twitter_handle':               one_organization.organization_twitter_handle,
                # 'pledge_goal':                  pledge_goal,
                # 'pledge_count':                 pledge_count,
                'last_updated':                 last_updated,
            }
            voter_guides.append(one_voter_guide.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            status += 'VOTER_GUIDE_FOLLOWERS_RETRIEVED '
            success = True
        else:
            status += 'NO_VOTER_GUIDE_FOLLOWERS_FOUND '
            success = True
    else:
        success = False

    json_data = {
        'status':                       status,
        'success':                      success,
        'voter_device_id':              voter_device_id,
        'organization_we_vote_id':      organization_we_vote_id,
        'maximum_number_to_retrieve':   maximum_number_to_retrieve,
        'voter_guides':                 voter_guides,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def refresh_existing_voter_guides(google_civic_election_id, organization_we_vote_id=""):
    voter_guide_updated_count = 0
    voter_guide_list_found = False
    voter_guide_list = []
    status = ""
    success = True

    # Cycle through existing voter_guides
    voter_guide_list_manager = VoterGuideListManager()
    voter_guide_manager = VoterGuideManager()

    if positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
        voter_guide_we_vote_id = ''
        results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
            voter_guide_we_vote_id, organization_we_vote_id, google_civic_election_id)
        if results['voter_guide_saved']:
            voter_guide_list_found = True
            voter_guide_list.append(results['voter_guide'])
    elif positive_value_exists(organization_we_vote_id):
        results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(organization_we_vote_id)
        if results['voter_guide_list_found']:
            voter_guide_list_found = True
            voter_guide_list = results['voter_guide_list']
    elif positive_value_exists(google_civic_election_id):
        results = voter_guide_list_manager.retrieve_voter_guides_for_election(google_civic_election_id)
        if results['voter_guide_list_found']:
            voter_guide_list_found = True
            voter_guide_list = results['voter_guide_list']
    else:
        results = voter_guide_list_manager.retrieve_all_voter_guides_order_by()
        if results['voter_guide_list_found']:
            voter_guide_list_found = True
            voter_guide_list = results['voter_guide_list']

    if voter_guide_list_found:
        for voter_guide in voter_guide_list:
            if positive_value_exists(voter_guide.organization_we_vote_id):
                results = refresh_organization_data_from_master_tables(voter_guide.organization_we_vote_id)
                status += results['status']
                # DALE 2017-11-06 This seems to be wasteful, doing the same data pushing multiple times. Refactor.
                if results['success']:
                    push_organization_data_to_other_table_caches(voter_guide.organization_we_vote_id)
                # DALE 2017-11-06 The update voter guides functions below I think are also done
                #  in "push_organization_data_to_other_table_caches". Refactor.
                if positive_value_exists(voter_guide.google_civic_election_id):
                    voter_guide_we_vote_id = ''
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                        voter_guide_we_vote_id,
                        voter_guide.organization_we_vote_id, voter_guide.google_civic_election_id)
                    if results['success']:
                        voter_guide_updated_count += 1
                elif positive_value_exists(voter_guide.vote_smart_time_span):
                    voter_guide_we_vote_id = ''
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_time_span(
                        voter_guide_we_vote_id, voter_guide.organization_we_vote_id, voter_guide.vote_smart_time_span)
                    if results['success']:
                        voter_guide_updated_count += 1
    results = {
        'status':                       status,
        'success':                      success,
        'voter_guide_updated_count':    voter_guide_updated_count,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def retrieve_organizations_followed_by_organization_we_vote_id(organization_we_vote_id):
    # voterFollowAllOrganizationsFollowedByOrganization
    """
    Retrieve organizations_we_vote_ids_list followed_by_organization_we_vote_id.
    :param organization_we_vote_id:
    :return:
    """

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organization_we_vote_ids_followed_list = \
        follow_organization_list_manager.retrieve_followed_organization_by_organization_we_vote_id_simple_id_array(
            organization_we_vote_id, return_we_vote_id)

    if len(organization_we_vote_ids_followed_list):
        status = 'SUCCESSFUL_RETRIEVE_OF_ORGANIZATIONS_FOLLOWED'
        organization_we_vote_ids_followed_list_found = True
    else:
        status = 'ORGANIZATIONS_FOLLOWED_NOT_FOUND'
        organization_we_vote_ids_followed_list_found = False

    results = {
        'status':                                       status,
        'organization_we_vote_ids_followed_list_found': organization_we_vote_ids_followed_list_found,
        'organization_we_vote_ids_followed_list':       organization_we_vote_ids_followed_list,
    }
    return results


def retrieve_voter_guides_followed(voter_id):
    voter_guide_list_found = False

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organization_we_vote_ids_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id,
                                                                                                  return_we_vote_id)

    voter_guide_list_object = VoterGuideListManager()
    results = voter_guide_list_object.retrieve_voter_guides_by_organization_list(
        organization_we_vote_ids_followed_by_voter)

    voter_guide_list = []
    if results['voter_guide_list_found']:
        voter_guide_list = results['voter_guide_list']
        status = 'SUCCESSFUL_RETRIEVE_VOTER_GUIDES_FOLLOWED '
        success = True
        if len(voter_guide_list):
            voter_guide_list_found = True
    else:
        status = results['status']
        success = results['success']

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def retrieve_voter_guides_followed_by_organization_we_vote_id(organization_we_vote_id,
                                                              filter_by_this_google_civic_election_id=False):
    # retrieve_voter_guides_followed_by_organization_we_vote_id() voterGuidesFollowedByOrganizationRetrieve
    """
    Retrieve voter guide followed by an organization with organization_we_vote_id
    :param organization_we_vote_id:
    :param filter_by_this_google_civic_election_id:
    :return:
    """
    voter_guide_list_found = False

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organization_we_vote_ids_followed = \
        follow_organization_list_manager.retrieve_followed_organization_by_organization_we_vote_id_simple_id_array(
            organization_we_vote_id, return_we_vote_id)

    voter_guide_list_object = VoterGuideListManager()
    results = voter_guide_list_object.retrieve_voter_guides_by_organization_list(
        organization_we_vote_ids_followed, filter_by_this_google_civic_election_id)

    voter_guide_list = []
    if results['voter_guide_list_found']:
        voter_guide_list = results['voter_guide_list']
        status = 'SUCCESSFUL_RETRIEVE_VOTER_GUIDES_FOLLOWED_BY_ORGANIZATION_WE_VOTE_ID '
        success = True
        if len(voter_guide_list):
            voter_guide_list_found = True
    else:
        status = results['status']
        success = results['success']

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def retrieve_voter_guide_followers_by_organization_we_vote_id(organization_we_vote_id):  # voterGuidesFollowersRetrieve
    organization_list_found = False

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organization_we_vote_ids_followers = \
        follow_organization_list_manager.retrieve_followers_organization_by_organization_we_vote_id_simple_id_array(
            organization_we_vote_id, return_we_vote_id)

    organization_list_object = OrganizationListManager()
    results = organization_list_object.retrieve_organizations_by_organization_we_vote_id_list(
        organization_we_vote_ids_followers)

    organization_list = []
    if results['organization_list_found']:
        organization_list = results['organization_list']
        status = 'SUCCESSFUL_RETRIEVE_OF_ORGANIZATIONS_FOLLOWERS'
        success = True
        if len(organization_list):
            organization_list_found = True
    else:
        status = results['status']
        success = results['success']

    results = {
        'success':                      success,
        'status':                       status,
        'organization_list_found':      organization_list_found,
        'organization_list':            organization_list,
    }
    return results


def voter_guides_ignored_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0):
    """
    Start with the organizations followed and return a list of voter_guides. voterGuidesIgnoredRetrieve
    See also organizations_followed_for_api, which returns a list of organizations.

    :param voter_device_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if results['voter_found']:
        voter = results['voter']
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_we_vote_id = ""

    results = retrieve_voter_guides_ignored(voter_id)
    status = results['status']
    voter_guide_list = results['voter_guide_list']
    voter_guides = []
    if results['voter_guide_list_found']:
        number_added_to_list = 0
        pledge_to_vote_manager = PledgeToVoteManager()
        for voter_guide in voter_guide_list:
            pledge_to_vote_we_vote_id = ""
            pledge_results = pledge_to_vote_manager.retrieve_pledge_to_vote(
                pledge_to_vote_we_vote_id, voter_we_vote_id, voter_guide.we_vote_id)
            if pledge_results['pledge_found']:
                voter_has_pledged = pledge_results['voter_has_pledged']
            else:
                voter_has_pledged = False
            if voter_guide.last_updated:
                last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ''
            one_voter_guide = {
                'we_vote_id':                   voter_guide.we_vote_id,
                'google_civic_election_id':     voter_guide.google_civic_election_id,
                'time_span':                    voter_guide.vote_smart_time_span,
                'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
                'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
                    else voter_guide.voter_guide_image_url(),
                'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
                'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
                'organization_we_vote_id':      voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
                'twitter_description':          voter_guide.twitter_description,
                'twitter_followers_count':      voter_guide.twitter_followers_count,
                'twitter_handle':               voter_guide.twitter_handle,
                'owner_voter_id':               voter_guide.owner_voter_id,
                'pledge_goal':                  voter_guide.pledge_goal,
                'pledge_count':                 voter_guide.pledge_count,
                'voter_has_pledged':            voter_has_pledged,
                'last_updated':                 last_updated,
            }
            voter_guides.append(one_voter_guide.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            status = 'VOTER_GUIDES_IGNORED_RETRIEVED'
            success = True
        else:
            status = 'NO_VOTER_GUIDES_IGNORED_FOUND'
            success = True
    else:
        success = results['success']

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'maximum_number_to_retrieve': maximum_number_to_retrieve,
        'voter_guides': voter_guides,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_voter_guides_ignored(voter_id):  # voterGuidesIgnoredRetrieve
    voter_guide_list_found = False

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    organization_we_vote_ids_ignored_by_voter = \
        follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(voter_id,
                                                                                                  return_we_vote_id)

    voter_guide_list_object = VoterGuideListManager()
    results = voter_guide_list_object.retrieve_voter_guides_by_organization_list(
        organization_we_vote_ids_ignored_by_voter)

    voter_guide_list = []
    if results['voter_guide_list_found']:
        voter_guide_list = results['voter_guide_list']
        status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_IGNORED'
        success = True
        if len(voter_guide_list):
            voter_guide_list_found = True
    else:
        status = results['status']
        success = results['success']

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results
