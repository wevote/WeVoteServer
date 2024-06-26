# voter_guide/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import copy
import json
from datetime import datetime, timedelta
from itertools import chain
from urllib.parse import urlparse

import pytz
from django.db.models import Q
from django.http import HttpResponse
from django.utils.timezone import localtime, now

import wevote_functions.admin
from ballot.models import OFFICE, CANDIDATE, MEASURE
from candidate.controllers import retrieve_candidate_list_for_all_prior_elections_this_year, \
    retrieve_candidate_list_for_all_upcoming_elections
from candidate.models import CandidateManager, CandidateListManager
from config.base import get_environment_variable
from election.controllers import retrieve_this_and_next_years_election_id_list, retrieve_upcoming_election_id_list
from election.models import ElectionManager
from exception.models import handle_record_not_found_exception
from follow.models import FollowOrganizationList, FollowIssueList, FOLLOWING
from friend.controllers import heal_current_friend
from friend.models import FriendManager
from issue.models import OrganizationLinkToIssueList
from measure.controllers import add_measure_name_alternatives_to_measure_list_light, \
    retrieve_measure_list_for_all_upcoming_elections
from organization.controllers import organization_follow_or_unfollow_or_ignore, \
    push_organization_data_to_other_table_caches, \
    refresh_organization_data_from_master_tables, retrieve_organization_list_for_all_upcoming_elections
from organization.models import OrganizationManager, OrganizationListManager, INDIVIDUAL
from pledge_to_vote.models import PledgeToVoteManager
from position.controllers import retrieve_ballot_item_we_vote_ids_for_organizations_to_follow, \
    retrieve_ballot_item_we_vote_ids_for_organization_static
from position.models import ANY_STANCE, FRIENDS_AND_PUBLIC, FRIENDS_ONLY, INFORMATION_ONLY, OPPOSE, \
    PositionEntered, PositionManager, PositionListManager, PUBLIC_ONLY, SUPPORT
from share.models import ShareManager
from twitter.models import TwitterUserManager
from volunteer_task.models import VOLUNTEER_ACTION_CANDIDATE_CREATED, \
    VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED, VolunteerTaskManager
from voter.models import fetch_voter_from_voter_device_link, fetch_voter_id_from_voter_device_link, \
    fetch_voter_we_vote_id_from_voter_device_link, \
    fetch_voter_we_vote_id_from_voter_id, VoterManager
from voter_guide.controllers_possibility import candidates_found_on_url, \
    match_endorsement_list_with_candidates_in_database, \
    match_endorsement_list_with_measures_in_database, match_endorsement_list_with_organizations_in_database, \
    organizations_found_on_url
from voter_guide.models import ENDORSEMENTS_FOR_CANDIDATE, ORGANIZATION_ENDORSING_CANDIDATES, \
    POSSIBILITY_LIST_LIMIT, UNKNOWN_TYPE, \
    VoterGuide, VoterGuideListManager, VoterGuideManager, \
    VoterGuidePossibility, VoterGuidePossibilityManager, VoterGuidePossibilityPosition, \
    WEBSITES_TO_NEVER_HIGHLIGHT_ENDORSEMENTS, WEBSITES_WE_DO_NOT_SCAN_FOR_ENDORSEMENTS
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists, \
    process_request_from_master, is_link_to_video
from wevote_functions.functions_date import generate_localized_datetime_from_obj

logger = wevote_functions.admin.get_logger(__name__)

VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def augment_with_voter_guide_possibility_position_data(voter_guide_possibility_list):
    # Identify how many endorsements already have positions stored
    voter_guide_possibility_list_modified = []
    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    google_civic_election_id_list_this_year = retrieve_this_and_next_years_election_id_list()
    for one_voter_guide_possibility in voter_guide_possibility_list:
        one_voter_guide_possibility.number_of_endorsements_with_position = 0
        possible_endorsement_list = []
        possible_endorsement_list_found = False
        # (ORGANIZATION_ENDORSING_CANDIDATES, 'Organization or News Website Endorsing Candidates'),
        # (ENDORSEMENTS_FOR_CANDIDATE, 'List of Endorsements for One Candidate'),
        # (UNKNOWN_TYPE, 'List of Endorsements for One Candidate'),
        is_organization_endorsing_candidates = \
            one_voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES or \
            one_voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE
        is_list_of_endorsements_for_candidate = \
            one_voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE
        if is_organization_endorsing_candidates:
            # POSSIBILITY_LIST_LIMIT set to 1000 possibilities to avoid very slow page loads
            results = extract_voter_guide_possibility_position_list_from_database(one_voter_guide_possibility)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

                # Match incoming endorsements to candidates already in the database
                results = match_endorsement_list_with_candidates_in_database(
                    possible_endorsement_list=possible_endorsement_list,
                    google_civic_election_id_list=google_civic_election_id_list_this_year,
                    is_organization_endorsing_candidates=is_organization_endorsing_candidates)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                    possible_endorsement_list_found = True
                # Match incoming endorsements to measures already in the database
                results = match_endorsement_list_with_measures_in_database(
                    possible_endorsement_list=possible_endorsement_list,
                    google_civic_election_id_list=google_civic_election_id_list_this_year)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                    possible_endorsement_list_found = True
        elif is_list_of_endorsements_for_candidate:
            # POSSIBILITY_LIST_LIMIT set to 1000 possibilities to avoid very slow page loads
            results = extract_voter_guide_possibility_position_list_from_database(one_voter_guide_possibility)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

                # Match incoming endorsements to candidates already in the database
                results = match_endorsement_list_with_candidates_in_database(
                    possible_endorsement_list=possible_endorsement_list,
                    google_civic_election_id_list=google_civic_election_id_list_this_year,
                    is_organization_endorsing_candidates=is_organization_endorsing_candidates)
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
            number_of_possible_endorsements_analyzed = 0
            for one_possible_endorsement in possible_endorsement_list:
                number_of_possible_endorsements_analyzed += 1
                if number_of_possible_endorsements_analyzed > POSSIBILITY_LIST_LIMIT:
                    break
                if 'candidate_we_vote_id' in one_possible_endorsement \
                        and positive_value_exists(one_possible_endorsement['candidate_we_vote_id']):
                    if is_organization_endorsing_candidates:
                        organization_we_vote_id = one_voter_guide_possibility.organization_we_vote_id
                    elif is_list_of_endorsements_for_candidate:
                        organization_we_vote_id = one_possible_endorsement['organization_we_vote_id']
                    else:
                        organization_we_vote_id = ''
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=organization_we_vote_id,
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
        try:
            one_voter_guide_possibility.number_of_endorsements_not_visible = \
                one_voter_guide_possibility.number_of_ballot_items - \
                one_voter_guide_possibility.number_of_endorsements_with_position
        except Exception as e:
            one_voter_guide_possibility.number_of_endorsements_not_visible = 0
        voter_guide_possibility_list_modified.append(one_voter_guide_possibility)
    return voter_guide_possibility_list_modified


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

    is_organization_endorsing_candidates = \
        voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES or \
        voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE
    is_list_of_endorsements_for_candidate = \
        voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE
    if is_organization_endorsing_candidates:
        # ######################
        # If we are starting from a single organization endorsing many candidates,
        # we store that organization information once
        organization_name = voter_guide_possibility.organization_name \
            if positive_value_exists(voter_guide_possibility.organization_name) else ""
        organization_we_vote_id = voter_guide_possibility.organization_we_vote_id \
            if positive_value_exists(voter_guide_possibility.organization_we_vote_id) else ""
        organization_twitter_handle = voter_guide_possibility.organization_twitter_handle \
            if positive_value_exists(voter_guide_possibility.organization_twitter_handle) else ""
        candidate_name = ""
        candidate_twitter_handle = ""
        candidate_we_vote_id = ""
        contest_office_name = ""
    elif is_list_of_endorsements_for_candidate:
        # ######################
        # If we are starting from a single candidate endorsed by many "organizations" (which may be people),
        # we store this candidate information once
        organization_name = ""
        organization_we_vote_id = ""
        organization_twitter_handle = ""
        candidate_name = voter_guide_possibility.candidate_name \
            if positive_value_exists(voter_guide_possibility.candidate_name) else ""
        candidate_twitter_handle = voter_guide_possibility.candidate_twitter_handle \
            if positive_value_exists(voter_guide_possibility.candidate_twitter_handle) else ""
        candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id \
            if positive_value_exists(voter_guide_possibility.candidate_we_vote_id) else ""

        contest_office_name = ""
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        if results['candidate_found']:
            candidate = results['candidate']
            contest_office_name = candidate.contest_office_name
        elif positive_value_exists(results['success']):
            # Consider adding candidate here?
            pass
    else:
        # Should not be possible to get here
        organization_name = ""
        organization_we_vote_id = ""
        organization_twitter_handle = ""
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
        if is_organization_endorsing_candidates:
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
        elif is_list_of_endorsements_for_candidate:
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
    Get voter_guide_possibility data from the database and put it into the Voter Guide Possibility system format we use
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

    is_organization_endorsing_candidates = \
        voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES or \
        voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE
    is_list_of_endorsements_for_candidate = \
        voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE
    if is_organization_endorsing_candidates:
        # ######################
        # If we are starting from a single organization endorsing many candidates,
        # we store that organization information once
        organization_name = voter_guide_possibility.organization_name \
            if positive_value_exists(voter_guide_possibility.organization_name) else ""
        organization_we_vote_id = voter_guide_possibility.organization_we_vote_id \
            if positive_value_exists(voter_guide_possibility.organization_we_vote_id) else ""
        organization_twitter_handle = voter_guide_possibility.organization_twitter_handle \
            if positive_value_exists(voter_guide_possibility.organization_twitter_handle) else ""
        # candidate_name = ""
        candidate_twitter_handle = ""
        candidate_we_vote_id = ""
        # contest_office_name = ""
    elif is_list_of_endorsements_for_candidate:
        # ######################
        # If we are starting from a single candidate endorsed by many "organizations" (which may be people),
        # we store this candidate information once
        organization_name = ""
        organization_we_vote_id = ""
        organization_twitter_handle = ""
        candidate_twitter_handle = voter_guide_possibility.candidate_twitter_handle \
            if positive_value_exists(voter_guide_possibility.candidate_twitter_handle) else ""
        candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id \
            if positive_value_exists(voter_guide_possibility.candidate_we_vote_id) else ""
        # candidate_manager = CandidateManager()
        # results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        # if results['candidate_found']:
        #     candidate = results['candidate']
        #     contest_office_name = candidate.contest_office_name
    else:
        # Should not be possible to get here
        organization_name = ""
        organization_we_vote_id = ""
        organization_twitter_handle = ""
        # candidate_name = ""
        candidate_twitter_handle = ""
        candidate_we_vote_id = ""
        # contest_office_name = ""
        pass

    possibility_position_query = VoterGuidePossibilityPosition.objects.filter(
        voter_guide_possibility_parent_id=voter_guide_possibility.id).order_by('possibility_position_number')
    if positive_value_exists(voter_guide_possibility_position_id):
        possibility_position_query = possibility_position_query.filter(id=voter_guide_possibility_position_id)
    possibility_position_query = possibility_position_query[:POSSIBILITY_LIST_LIMIT]
    possibility_position_list = list(possibility_position_query)
    candidate_manager = CandidateManager()
    for possibility_position in possibility_position_list:
        candidate_alternate_names = []
        if positive_value_exists(possibility_position.more_info_url):
            more_info_url = possibility_position.more_info_url
        else:
            more_info_url = voter_guide_possibility.voter_guide_possibility_url
        if is_organization_endorsing_candidates:
            # The organization variables have been set above
            # Note that UNKNOWN_TYPE might be set if we are looking at organization
            # ######################
            # If we are starting from a single organization endorsing many candidates,
            # we refresh the candidate information from the VoterGuidePossibilityPosition table with each loop
            candidate_we_vote_id = possibility_position.candidate_we_vote_id \
                if positive_value_exists(possibility_position.candidate_we_vote_id) else ""
            candidate_twitter_handle = possibility_position.candidate_twitter_handle \
                if positive_value_exists(possibility_position.candidate_twitter_handle) else ""
            # If this is a list of candidates being endorsed by one organization, add on the alternate_names
            if positive_value_exists(candidate_we_vote_id):
                candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id,
                                                                                         read_only=True)
                if candidate_results['candidate_found']:
                    candidate_alternate_names = candidate_results['candidate'].display_alternate_names_list()
        elif is_list_of_endorsements_for_candidate:
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

        position_json = {
            'possibility_position_id': possibility_position.id,
            'possibility_position_number': possibility_position.possibility_position_number,
            'ballot_item_name': possibility_position.ballot_item_name,
            'ballot_item_state_code': possibility_position.ballot_item_state_code,
            'candidate_alternate_names': candidate_alternate_names,
            'candidate_twitter_handle': candidate_twitter_handle,
            'candidate_we_vote_id': candidate_we_vote_id,
            # 'contest_office_name': contest_office_name,
            'google_civic_election_id': possibility_position.google_civic_election_id,
            'measure_we_vote_id': possibility_position.measure_we_vote_id,
            'more_info_url': more_info_url,
            'organization_name': organization_name,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_we_vote_id': organization_we_vote_id,
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


def delete_voter_guides_for_voter(from_voter_we_vote_id, from_organization_we_vote_id):
    status = ''
    success = True
    voter_guide_entries_deleted = 0
    voter_guide_entries_not_deleted = 0

    if not positive_value_exists(from_voter_we_vote_id):
        status += "DELETE_VOTER_GUIDES-MISSING_VOTER_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'voter_guide_entries_deleted': voter_guide_entries_deleted,
            'voter_guide_entries_not_deleted': voter_guide_entries_not_deleted,
        }
        return results

    if not positive_value_exists(from_organization_we_vote_id):
        status += "DELETE_VOTER_GUIDES-MISSING_FROM_ORGANIZATION_WE_VOTE_ID "

    voter_guide_list_manager = VoterGuideListManager()
    from_voter_guide_results = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_we_vote_id(
        from_voter_we_vote_id, read_only=False)
    if not from_voter_guide_results['success']:
        success = False
    if from_voter_guide_results['voter_guide_list_found']:
        from_voter_guide_list = from_voter_guide_results['voter_guide_list']
    else:
        from_voter_guide_list = []

    for from_voter_guide in from_voter_guide_list:
        try:
            from_voter_guide.delete()
            voter_guide_entries_deleted += 1
        except Exception as e:
            status += "COULD_NOT_DELETE_VOTER_GUIDE: " + str(e) + " "
            success = False
            voter_guide_entries_not_deleted += 1

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'voter_guide_entries_deleted':      voter_guide_entries_deleted,
        'voter_guide_entries_not_deleted':  voter_guide_entries_not_deleted,
    }
    return results


def duplicate_voter_guides(from_voter_id, from_voter_we_vote_id, from_organization_we_vote_id,
                           to_voter_id, to_voter_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = True
    voter_guides_duplicated = 0
    voter_guides_not_duplicated = 0
    organization_manager = OrganizationManager()
    voter_guide_list_manager = VoterGuideListManager()
    voter_guide_manager = VoterGuideManager()
    voter_guide_list = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_id(from_voter_id, read_only=False)

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
                status += "FAILED_TO_DELETE_VOTER_GUIDE: " + str(e) + " "
                success = False
                voter_guides_not_duplicated += 1

    # Now retrieve by organization_we_vote_id in case there is damaged data
    voter_guide_list = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
        from_organization_we_vote_id, read_only=False)

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
                status += "FAILED_TO_UPDATE_VOTER_GUIDE: " + str(e) + " "
                success = False
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
                                       to_organization_we_vote_id):
    status = ''
    success = True
    to_voter_id = 0
    voter_guide_entries_moved = 0
    voter_guide_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_VOTER_GUIDES-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
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
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'voter_guide_entries_moved': voter_guide_entries_moved,
            'voter_guide_entries_not_moved': voter_guide_entries_not_moved,
        }
        return results

    if not positive_value_exists(to_organization_we_vote_id):
        status += "MOVE_VOTER_GUIDES-MISSING_TO_ORGANIZATION_WE_VOTE_ID "
        success = False

    voter_guide_list_manager = VoterGuideListManager()
    from_voter_guide_results = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_we_vote_id(
        from_voter_we_vote_id, read_only=False)
    if not from_voter_guide_results['success']:
        status += from_voter_guide_results['status']
        success = False
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
        to_voter_we_vote_id, read_only=False)
    if not to_voter_guide_results['success']:
        status += to_voter_guide_results['status']
        success = False
    if to_voter_guide_results['voter_guide_list_found']:
        to_voter_guide_list = to_voter_guide_results['voter_guide_list']
    else:
        to_voter_guide_list = []

    voter_manager = VoterManager()
    for from_voter_guide in from_voter_guide_list:
        # See if the "to_voter" already has a matching entry
        to_voter_guide_found = False
        from_voter_guide_google_civic_election_id = from_voter_guide.google_civic_election_id
        # Cycle through all the "to_voter" current_friend entries and if there isn't one, create it
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
                if positive_value_exists(to_organization_we_vote_id):
                    from_voter_guide.organization_we_vote_id = to_organization_we_vote_id
                from_voter_guide.save()
                voter_guide_entries_moved += 1
            except Exception as e:
                status += "COULD_NOT_UPDATE_FROM_VOTER_GUIDE: " + str(e) + " "
                success = False
                voter_guide_entries_not_moved += 1

    # Now remove the voter_guides where there were duplicates
    from_voter_guide_remaining_results = voter_guide_list_manager.retrieve_all_voter_guides_by_voter_we_vote_id(
        from_voter_we_vote_id, read_only=False)
    if not from_voter_guide_remaining_results['success']:
        status += from_voter_guide_remaining_results['status']
        success = False
    if from_voter_guide_remaining_results['voter_guide_list_found']:
        from_voter_guide_list_remaining = to_voter_guide_results['voter_guide_list']
        for from_voter_guide in from_voter_guide_list_remaining:
            # Delete the remaining voter_guides
            try:
                # Leave this turned off until testing is finished
                # from_voter_guide.delete()
                pass
            except Exception as e:
                status += "COULD_NOT_DELETE_FROM_VOTER_GUIDE: " + str(e) + " "
                success = False

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
    elections_dict = {}
    organizations_dict = {}
    voter_we_vote_id_dict = {}
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
                    we_vote_hosted_profile_image_url_tiny,
                    elections_dict=elections_dict,
                    organizations_dict=organizations_dict,
                    voter_we_vote_id_dict=voter_we_vote_id_dict,
                )
                if results['success']:
                    elections_dict = results['elections_dict']
                    organizations_dict = results['organizations_dict']
                    voter_we_vote_id_dict = results['voter_we_vote_id_dict']
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(vote_smart_time_span):
                results = voter_guide_manager.update_or_create_organization_voter_guide_by_time_span(
                    voter_guide_we_vote_id, organization_we_vote_id, vote_smart_time_span, pledge_goal,
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


def voter_guide_possibility_retrieve_for_api(  # voterGuidePossibilityRetrieve
        voter_device_id='',
        voter_guide_possibility_id=0,
        url_to_scan='',
        pdf_url='',
        limit_to_this_year=True):
    """
    voterGuidePossibilityRetrieve
    :param voter_device_id:
    :param voter_guide_possibility_id:
    :param url_to_scan:
    :param pdf_url: The url of the PDF that was used to generate the url_to_scan in S3
    :param limit_to_this_year
    :return:
    """
    status = ""
    voter_id = 0

    if not positive_value_exists(voter_device_id):
        status += "VOTER_DEVICE_ID_NOT_PROVIDED "
    # results = is_voter_device_id_valid(voter_device_id)
    # if not results['success']:
    #     return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = 0
    voter_who_submitted_we_vote_id = ''
    voter_who_submitted_name = ''
    assigned_to_voter_we_vote_id = ''
    assigned_to_name = ''
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        voter_who_submitted_we_vote_id = voter.we_vote_id
        voter_who_submitted_name = voter.get_full_name(real_name_only=True)
        if voter.is_admin or voter.is_political_data_manager or voter.is_verified_volunteer:
            assigned_to_voter_we_vote_id = voter.we_vote_id
            assigned_to_name = voter.get_full_name(real_name_only=True)

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        # json_data = {
        #     'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID ",
        #     'success': False,
        #     'voter_device_id': voter_device_id,
        # }
        # return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    voter_guide_possibility = VoterGuidePossibility()
    if positive_value_exists(voter_guide_possibility_id):
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id, limit_to_this_year=limit_to_this_year)
    else:
        if not positive_value_exists(url_to_scan):
            status += "VOTER_GUIDE_POSSIBILITY_RETRIEVE-URL_TO_SCAN_MISSING "
            json_data = {
                'status': status,
                'success': False,
                'voter_device_id': voter_device_id,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')

        if not url_to_scan.startswith('http://') and not url_to_scan.startswith('https://'):
            url_to_scan = 'https://' + url_to_scan

        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_from_url(
            voter_guide_possibility_url=url_to_scan,
            pdf_url=pdf_url,
            voter_who_submitted_we_vote_id=voter_who_submitted_we_vote_id,
            limit_to_this_year=limit_to_this_year)

    if not positive_value_exists(results['success']):
        status += results['status']
        status += "VOTER_GUIDE_POSSIBILITY_RETRIEVE_SUCCESS_FALSE "
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    status += results['status']
    voter_guide_possibility_found = False
    candidate_we_vote_id = ""
    organization_we_vote_id = ""
    is_list_of_endorsements_for_candidate = False
    if results['voter_guide_possibility_found']:
        status += "VOTER_GUIDE_POSSIBILITY_FOUND "
        voter_guide_possibility_found = True
        voter_guide_possibility = results['voter_guide_possibility']
        voter_guide_possibility_id = results['voter_guide_possibility_id']
        organization_we_vote_id = results['organization_we_vote_id']
        if positive_value_exists(voter_guide_possibility.candidate_name) \
                or positive_value_exists(voter_guide_possibility.candidate_twitter_handle) \
                or positive_value_exists(voter_guide_possibility.candidate_we_vote_id):
            is_list_of_endorsements_for_candidate = True
        else:
            is_list_of_endorsements_for_candidate = False
    else:
        # Current entry not found. Create new entry.
        status += "EXISTING_VOTER_GUIDE_POSSIBILITY_NOT_FOUND "
        if any(value.lower() in url_to_scan.lower() for value in WEBSITES_WE_DO_NOT_SCAN_FOR_ENDORSEMENTS):
            voter_guide_possibility_found = False
            status += "URL_TO_SCAN_IS_IN-WEBSITES_WE_DO_NOT_SCAN_FOR_ENDORSEMENTS "
        else:
            is_list_of_endorsements_for_candidate = False  # To be extended to also save candidate focused endorsement pages
            if positive_value_exists(is_list_of_endorsements_for_candidate):
                voter_guide_possibility_type = ENDORSEMENTS_FOR_CANDIDATE
            else:
                voter_guide_possibility_type = ORGANIZATION_ENDORSING_CANDIDATES
            updated_values = {
                'voter_guide_possibility_type':     voter_guide_possibility_type,
                'voter_guide_possibility_url':      url_to_scan,
                'voter_who_submitted_name':         voter_who_submitted_name,
                'voter_who_submitted_we_vote_id':   voter_who_submitted_we_vote_id,
                'assigned_to_voter_we_vote_id':     assigned_to_voter_we_vote_id,
                'assigned_to_name':                 assigned_to_name,
            }
            create_results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility(
                voter_guide_possibility_url=url_to_scan,
                # pdf_url,
                # voter_who_submitted_we_vote_id=voter_who_submitted_we_vote_id,
                updated_values=updated_values)
            if create_results['voter_guide_possibility_saved']:
                status += create_results['status']
                voter_guide_possibility_found = True
                voter_guide_possibility = create_results['voter_guide_possibility']
                voter_guide_possibility_id = create_results['voter_guide_possibility_id']
                organization_we_vote_id = voter_guide_possibility.organization_we_vote_id
                candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id
                if create_results['voter_guide_possibility_created'] and \
                        positive_value_exists(voter_who_submitted_we_vote_id):
                    try:
                        # Give the volunteer who entered this credit
                        volunteer_task_manager = VolunteerTaskManager()
                        task_results = volunteer_task_manager.create_volunteer_task_completed(
                            action_constant=VOLUNTEER_ACTION_VOTER_GUIDE_POSSIBILITY_CREATED,
                            voter_id=voter_id,
                            voter_we_vote_id=voter_who_submitted_we_vote_id,
                        )
                    except Exception as e:
                        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    candidates_missing_from_we_vote = False  # filter_selected_candidates_missing
    cannot_find_endorsements = False  # filter_selected_not_available_yet
    capture_detailed_comments = False  # filter_selected_capture_detailed_comments
    contributor_email = ""
    contributor_comments = ""
    done_needs_verification = False  # filter_selected_done_needs_verification
    done_verified = False  # filter_selected_done_verified
    from_prior_election = False  # filter_selected_from_prior_election
    hide_from_active_review = False  # filter_selected_archive
    ignore_this_source = False  # filter_selected_ignore
    internal_notes = ""
    possible_candidate_name = ""
    possible_candidate_twitter_handle = ""
    possible_organization_name = ""
    possible_organization_twitter_handle = ""
    limit_to_this_state_code = ""
    voter_guide_possibility_edit = ""
    voter_guide_possibility_type = ""
    if voter_guide_possibility_found:
        candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id
        candidates_missing_from_we_vote = voter_guide_possibility.candidates_missing_from_we_vote
        cannot_find_endorsements = voter_guide_possibility.cannot_find_endorsements
        capture_detailed_comments = voter_guide_possibility.capture_detailed_comments
        contributor_email = voter_guide_possibility.contributor_email
        contributor_comments = voter_guide_possibility.contributor_comments
        done_needs_verification = voter_guide_possibility.done_needs_verification
        done_verified = voter_guide_possibility.done_verified
        from_prior_election = voter_guide_possibility.from_prior_election
        hide_from_active_review = voter_guide_possibility.hide_from_active_review
        ignore_this_source = voter_guide_possibility.ignore_this_source
        internal_notes = voter_guide_possibility.internal_notes
        possible_candidate_name = voter_guide_possibility.candidate_name
        possible_candidate_twitter_handle = voter_guide_possibility.candidate_twitter_handle
        possible_organization_name = voter_guide_possibility.organization_name
        possible_organization_twitter_handle = voter_guide_possibility.organization_twitter_handle
        limit_to_this_state_code = voter_guide_possibility.state_code
        url_to_scan = voter_guide_possibility.voter_guide_possibility_url
        voter_guide_possibility_type = voter_guide_possibility.voter_guide_possibility_type
        voter_guide_possibility_edit = WE_VOTE_SERVER_ROOT_URL + "/vg/create/?voter_guide_possibility_id=" + \
            str(voter_guide_possibility_id)

    organization_dict = {}
    possible_owner_of_website_organizations_list = []
    twitter_user_manager = TwitterUserManager()
    if positive_value_exists(organization_we_vote_id):
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        status += organization_results['status']
        if organization_results['organization_found']:
            organization = organization_results['organization']
            organization_twitter_handle = twitter_user_manager.fetch_twitter_handle_from_organization_we_vote_id(
                organization_we_vote_id)
            organization_dict = {
                'organization_we_vote_id': organization_we_vote_id,
                'organization_name': organization.organization_name,
                'organization_website': organization.organization_website,
                'organization_twitter_handle': organization_twitter_handle,
                'organization_email': organization.organization_email,
                'organization_facebook': organization.organization_facebook,
                'we_vote_hosted_profile_image_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
            }
    elif not positive_value_exists(is_list_of_endorsements_for_candidate):
        # As long as we know there isn't a candidate_we_vote_id, try to find organization owner
        if positive_value_exists(possible_organization_name) \
                or positive_value_exists(possible_organization_twitter_handle):
            # Search for organizations that match
            organization_list_manager = OrganizationListManager()
            results = organization_list_manager.organization_search_find_any_possibilities(
                organization_name=possible_organization_name,
                organization_twitter_handle=possible_organization_twitter_handle
            )
            if results['organizations_found']:
                possible_owner_of_website_organizations_list = results['organizations_list']
        elif positive_value_exists(url_to_scan):
            scrape_results = organizations_found_on_url(url_to_scan, limit_to_this_state_code)
            possible_owner_of_website_organizations_list = scrape_results['organization_list']

    candidate_dict = {}
    possible_owner_of_website_candidates_list = []
    if positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        status += candidate_results['status']
        if candidate_results['candidate_found']:
            candidate = candidate_results['candidate']
            candidate_dict = {
                'candidate_we_vote_id':         candidate.we_vote_id,
                'candidate_name':               candidate.candidate_name,
                'candidate_website':            candidate.candidate_url,
                'candidate_twitter_handle':     candidate.candidate_twitter_handle,
                'candidate_email':              candidate.candidate_email,
                'candidate_facebook':           candidate.facebook_url,
                'candidate_photo_url_medium':   candidate.we_vote_hosted_profile_image_url_medium,
                'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
            }
    elif positive_value_exists(is_list_of_endorsements_for_candidate):
        if positive_value_exists(possible_candidate_name) or positive_value_exists(possible_candidate_twitter_handle):
            google_civic_election_id_list = retrieve_upcoming_election_id_list(
                limit_to_this_state_code=limit_to_this_state_code)
            candidate_list_manager = CandidateListManager()
            results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
                google_civic_election_id_list=google_civic_election_id_list,
                state_code=limit_to_this_state_code,
                candidate_twitter_handle=possible_candidate_twitter_handle,
                candidate_name=possible_candidate_name,
                read_only=True)
            possible_candidate_list = []
            if results['candidate_list_found']:
                possible_candidate_list = results['candidate_list']
            elif results['candidate_found']:
                possible_candidate_list.append(results['candidate'])
            for candidate in possible_candidate_list:
                possible_candidate_dict = {
                    'candidate_we_vote_id':         candidate.we_vote_id,
                    'candidate_name':               candidate.candidate_name,
                    'candidate_website':            candidate.candidate_url,
                    'candidate_twitter_handle':     candidate.candidate_twitter_handle,
                    'candidate_email':              candidate.candidate_email,
                    'candidate_facebook':           candidate.facebook_url,
                    'candidate_photo_url_medium':   candidate.we_vote_hosted_profile_image_url_medium,
                    'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
                }
                possible_owner_of_website_candidates_list.append(possible_candidate_dict)
        elif positive_value_exists(url_to_scan):
            google_civic_election_id_list = retrieve_upcoming_election_id_list(
                limit_to_this_state_code=limit_to_this_state_code)
            scrape_results = candidates_found_on_url(url_to_scan, google_civic_election_id_list,
                                                     limit_to_this_state_code)
            possible_owner_of_website_candidates_list = scrape_results['candidate_list']

    json_data = {
        'status':                               status,
        'success':                              results['success'],
        'candidate':                            candidate_dict,
        'candidates_missing_from_we_vote':      candidates_missing_from_we_vote,
        'cannot_find_endorsements':             cannot_find_endorsements,
        'capture_detailed_comments':            capture_detailed_comments,
        'contributor_comments':                 contributor_comments,
        'contributor_email':                    contributor_email,
        'done_needs_verification':              done_needs_verification,
        'done_verified':                        done_verified,
        'from_prior_election':                  from_prior_election,
        'hide_from_active_review':              hide_from_active_review,
        'ignore_this_source':                   ignore_this_source,
        'internal_notes':                       internal_notes,
        'organization':                         organization_dict,
        'possible_candidate_name':              possible_candidate_name,
        'possible_candidate_twitter_handle':    possible_candidate_twitter_handle,
        'possible_owner_of_website_candidates_list': possible_owner_of_website_candidates_list,
        'possible_organization_name':           possible_organization_name,
        'possible_organization_twitter_handle': possible_organization_twitter_handle,
        'possible_owner_of_website_organizations_list': possible_owner_of_website_organizations_list,
        'limit_to_this_state_code':             limit_to_this_state_code,
        'url_to_scan':                          url_to_scan,
        'voter_device_id':                      voter_device_id,
        'voter_guide_possibility_edit':         voter_guide_possibility_edit,
        'voter_guide_possibility_id':           voter_guide_possibility_id,
        'voter_guide_possibility_type':         voter_guide_possibility_type,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_highlights_retrieve_for_api(  # voterGuidePossibilityHighlightsRetrieve
        google_civic_election_id=0,
        names_list=[],
        pdf_url="",
        status="",
        url_to_scan="",
        voter_device_id=""):
    status += "VOTER_GUIDE_POSSIBILITY_HIGHLIGHTS_RETRIEVE "
    success = True
    highlight_list = []
    voter_we_vote_id = ''
    names_already_included_list = []
    candidate_manager = CandidateManager()

    # Once we know we have a voter_device_id to work with, get this working
    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_from_url(
        voter_guide_possibility_url=url_to_scan,
        pdf_url=pdf_url,
        # voter_who_submitted_we_vote_id=voter_we_vote_id,
        # google_civic_election_id=google_civic_election_id
    )

    status += results['status']
    if results['voter_guide_possibility_found']:
        voter_guide_possibility_id = results['voter_guide_possibility_id']
        results = voter_guide_possibility_positions_retrieve_for_api(
            voter_device_id, voter_guide_possibility_id)
        if results['possible_position_list']:
            possible_position_list = results['possible_position_list']
            for one_possible_position in possible_position_list:
                if one_possible_position['position_we_vote_id']:
                    display = 'STORED'
                elif one_possible_position['position_should_be_removed']:
                    display = 'DELETED'
                else:
                    display = 'POSSIBILITY'
                if one_possible_position['ballot_item_name'] not in names_already_included_list:
                    names_already_included_list.append(one_possible_position['ballot_item_name'])
                    one_highlight = {
                        'name':         one_possible_position['ballot_item_name'],
                        'we_vote_id':   one_possible_position['candidate_we_vote_id'],
                        'display':      display,
                        'stance':       one_possible_position['position_stance'],
                    }
                    highlight_list.append(one_highlight)
                if positive_value_exists(one_possible_position['candidate_we_vote_id']):
                    candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(
                        one_possible_position['candidate_we_vote_id'], read_only=True)
                    if candidate_results['candidate_found']:
                        one_candidate = candidate_results['candidate']
                        if positive_value_exists(one_candidate.display_candidate_name()) \
                                and one_candidate.display_candidate_name() not in names_already_included_list:
                            names_already_included_list.append(one_candidate.display_candidate_name())
                            one_highlight = {
                                'name':         one_candidate.display_candidate_name(),
                                'we_vote_id':   one_possible_position['candidate_we_vote_id'],
                                'display':      display,
                                'stance':       one_possible_position['position_stance'],
                            }
                            highlight_list.append(one_highlight)
                        alternate_names = one_candidate.display_alternate_names_list()
                        for alternate_name in alternate_names:
                            if positive_value_exists(alternate_name) \
                                    and alternate_name not in names_already_included_list:
                                names_already_included_list.append(alternate_name)
                                one_highlight = {
                                    'name':         alternate_name,
                                    'we_vote_id':   one_possible_position['candidate_we_vote_id'],
                                    'display':      display,
                                    'stance':       one_possible_position['position_stance'],
                                }
                                highlight_list.append(one_highlight)

    # We want to take all the human names found by scanning the HTML page (using VertexAI), and check to see if
    #  we can find existing candidates in our database.
    limit_to_these_last_names = []
    names_list_found = len(names_list) > 0
    if names_list_found:
        from wevote_functions.functions import extract_last_name_from_full_name
        for one_name in names_list:
            try:
                last_name = extract_last_name_from_full_name(one_name)
                if last_name and positive_value_exists(last_name):
                    last_name_lower = last_name.lower()
                    if last_name_lower not in limit_to_these_last_names:
                        limit_to_these_last_names.append(last_name_lower)
            except Exception as e:
                pass
    if len(limit_to_these_last_names) > 0:
        results = retrieve_candidate_list_for_all_upcoming_elections(
            limit_to_these_last_names=limit_to_these_last_names,
            super_light_candidate_list=True)
        if results['candidate_list_found']:
            all_possible_candidates_list_light = results['candidate_list_light']
            for one_possible_candidate in all_possible_candidates_list_light:
                if one_possible_candidate['name'] not in names_already_included_list:
                    names_already_included_list.append(one_possible_candidate['name'])
                    one_highlight = {
                        'name':         one_possible_candidate['name'],
                        'we_vote_id':   one_possible_candidate['we_vote_id'],
                        'display':      'DEFAULT',
                        'stance':       '',
                    }
                    highlight_list.append(one_highlight)
                if 'alternate_names' in one_possible_candidate:
                    for one_alternate_name in one_possible_candidate['alternate_names']:
                        if one_alternate_name not in names_already_included_list:
                            names_already_included_list.append(one_alternate_name)
                            one_highlight = {
                                'name':         one_alternate_name,
                                'we_vote_id':   one_possible_candidate['we_vote_id'],
                                'display':      'DEFAULT',
                                'stance':       '',
                            }
                            highlight_list.append(one_highlight)

        # We include prior elections this year for primary candidates not linked to future election yet
        results = retrieve_candidate_list_for_all_prior_elections_this_year(
            limit_to_these_last_names=limit_to_these_last_names,
            super_light_candidate_list=True)
        if results['candidate_list_found']:
            all_possible_candidates_list_light = results['candidate_list_light']
            for one_possible_candidate in all_possible_candidates_list_light:
                if one_possible_candidate['name'] not in names_already_included_list:
                    names_already_included_list.append(one_possible_candidate['name'])
                    one_highlight = {
                        'name':         one_possible_candidate['name'],
                        'we_vote_id':   one_possible_candidate['we_vote_id'],
                        'display':      'DEFAULT',
                        'stance':       '',
                        'prior':        1,
                    }
                    highlight_list.append(one_highlight)
                if 'alternate_names' in one_possible_candidate:
                    for one_alternate_name in one_possible_candidate['alternate_names']:
                        if one_alternate_name not in names_already_included_list:
                            names_already_included_list.append(one_alternate_name)
                            one_highlight = {
                                'name':         one_alternate_name,
                                'we_vote_id':   one_possible_candidate['we_vote_id'],
                                'display':      'DEFAULT',
                                'stance':       '',
                                'prior':        1,
                            }
                            highlight_list.append(one_highlight)
    if names_list_found:
        # Finally, include the raw names from names_list (from Vertex AI) which weren't found in our database
        for one_name in names_list:
            if one_name and one_name not in names_already_included_list:
                names_already_included_list.append(one_name)
                one_highlight = {
                    'name':         one_name,
                    'we_vote_id':   '',
                    'display':      'DEFAULT',
                    'stance':       '',
                }
                highlight_list.append(one_highlight)

    json_data = {
        'status':               status,
        'success':              success,
        'url_to_scan':          url_to_scan,
        'highlight_list':       highlight_list,
        'never_highlight_on':   WEBSITES_TO_NEVER_HIGHLIGHT_ENDORSEMENTS,
    }
    return json_data


def clean_up_possible_endorsement_list(possible_endorsement_list):
    #  remove null value ballot_item_name entries
    endorse_no_nulls = filter(lambda item: positive_value_exists(item['ballot_item_name']), possible_endorsement_list)
    # Sort the list by id in place
    endorse_no_nulls_sorted = sorted(endorse_no_nulls, key=lambda item: item['possibility_position_id'], reverse=True)
    # Dedupe, excluding older dupe endorsements
    prior_names = []
    results = []
    for endorse in endorse_no_nulls_sorted:
        name = endorse['ballot_item_name']
        if name not in prior_names:
            results.append(endorse)
            prior_names.append(name)
    return results


def voter_guide_possibility_positions_retrieve_for_api(  # voterGuidePossibilityPositionsRetrieve
        voter_device_id, voter_guide_possibility_id, voter_guide_possibility_position_id=0, limit_to_this_year=True):
    status = "VOTER_GUIDE_POSSIBILITY_POSITIONS_RETRIEVE "
    success = True
    voter_guide_possibility = None
    voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
    voter_guide_possibility_found = False

    try:
        voter_guide_possibility_manager = VoterGuidePossibilityManager()
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id, limit_to_this_year=limit_to_this_year)
        status += results['status']
        if results['voter_guide_possibility_found']:
            voter_guide_possibility = results['voter_guide_possibility']
            voter_guide_possibility_found = True
    except Exception as e:
        status += "VOTER_GUIDE_POSSIBILITY_POSITIONS_RETRIEVE_FAILED1: " + str(e) + " "
        success = False

    # We do not want to bring endorsements found on other web pages over to this voter_guide_possibility
    #  because it creates clutter, and in practice isn't helpful.
    # if positive_value_exists(results['success']):
    #     move_voter_guide_possibility_positions_to_requested_voter_guide_possibility(results['voter_guide_possibility'])

    possible_endorsement_list = []
    try:
        if voter_guide_possibility_found:
            limit_to_this_state_code = voter_guide_possibility.state_code

            results = extract_voter_guide_possibility_position_list_from_database(
                voter_guide_possibility, voter_guide_possibility_position_id)
            status += results['status']
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']

                google_civic_election_id_list_this_year = retrieve_this_and_next_years_election_id_list()
                is_organization_endorsing_candidates = \
                    voter_guide_possibility.voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES or \
                    voter_guide_possibility.voter_guide_possibility_type == UNKNOWN_TYPE
                is_list_of_endorsements_for_candidate = \
                    voter_guide_possibility.voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE

                if is_organization_endorsing_candidates:
                    organization_we_vote_id = voter_guide_possibility.organization_we_vote_id
                    # Match incoming endorsements to candidates already in the database
                    results = match_endorsement_list_with_candidates_in_database(
                        possible_endorsement_list=possible_endorsement_list,
                        google_civic_election_id_list=google_civic_election_id_list_this_year,
                        state_code=limit_to_this_state_code,
                        attach_objects=False,
                        is_organization_endorsing_candidates=is_organization_endorsing_candidates)
                    if results['possible_endorsement_list_found']:
                        possible_endorsement_list = results['possible_endorsement_list']

                    # Match incoming endorsements to measures already in the database
                    results = match_endorsement_list_with_measures_in_database(
                        possible_endorsement_list=possible_endorsement_list,
                        google_civic_election_id_list=google_civic_election_id_list_this_year,
                        state_code=limit_to_this_state_code,
                        attach_objects=False)
                    if results['possible_endorsement_list_found']:
                        possible_endorsement_list = results['possible_endorsement_list']

                    # Add on existing position information
                    for one_possible_endorsement in possible_endorsement_list:
                        if 'candidate_we_vote_id' in one_possible_endorsement \
                                and positive_value_exists(one_possible_endorsement['candidate_we_vote_id']):
                            position_exists_query = PositionEntered.objects.using('readonly').filter(
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
                elif is_list_of_endorsements_for_candidate:
                    candidate_we_vote_id = voter_guide_possibility.candidate_we_vote_id

                    # Match incoming endorsements to candidates already in the database
                    results = match_endorsement_list_with_organizations_in_database(
                        possible_endorsement_list=possible_endorsement_list,
                        attach_objects=False,
                        is_organization_endorsing_candidates=False)
                    if results['possible_endorsement_list_found']:
                        possible_endorsement_list = results['possible_endorsement_list']

                    # Add on existing position information
                    for one_possible_endorsement in possible_endorsement_list:
                        if 'organization_we_vote_id' in one_possible_endorsement \
                                and positive_value_exists(one_possible_endorsement['organization_we_vote_id']):
                            position_exists_query = PositionEntered.objects.using('readonly').filter(
                                organization_we_vote_id=one_possible_endorsement['organization_we_vote_id'],
                                candidate_campaign_we_vote_id=candidate_we_vote_id)
                            position_list = list(position_exists_query)
                            if positive_value_exists(len(position_list)):
                                one_possible_endorsement['position_we_vote_id'] = position_list[0].we_vote_id
                                one_possible_endorsement['position_stance_stored'] = position_list[0].stance
                                one_possible_endorsement['statement_text_stored'] = position_list[0].statement_text
                                one_possible_endorsement['more_info_url_stored'] = position_list[0].more_info_url
                else:
                    status += "MISSING_VOTER_GUIDE_POSSIBILITY_TYPE "
                    pass

        # June 2023, remove older dupe entries and entries with null names -- shouldn't need to do this, but ...
        possible_endorsement_list = clean_up_possible_endorsement_list(possible_endorsement_list)
    except Exception as e:
        status += "VOTER_GUIDE_POSSIBILITY_POSITIONS_RETRIEVE_FAILED2: " + str(e) + " "
        success = False
    json_data = {
        'status':                       status,
        'success':                      success,
        'voter_guide_possibility_id':   voter_guide_possibility_id,
        'possible_position_list':       possible_endorsement_list,
    }
    return json_data


def move_voter_guide_possibility_positions_to_requested_voter_guide_possibility(voter_guide_possibility):
    """
    This finds endorsements on other VoterGuidePossibility entries and moves them over to this entry.
    2024-06 After using this for some months, we decided:
    We do not want to bring endorsements found on other web pages over to this voter_guide_possibility
    because it creates clutter, and in practice isn't helpful.
    """
    voter_guide_possibility_id = voter_guide_possibility.id
    organization_we_vote_id = voter_guide_possibility.organization_we_vote_id
    voter_guide_possibility_url = voter_guide_possibility.voter_guide_possibility_url
    parts = urlparse(voter_guide_possibility_url)
    net_location = parts.netloc
    # print(net_location)

    enddate = datetime.now(pytz.UTC)
    startdate = enddate - timedelta(days=186)    # 6 months

    voter_guide_possibility_query = VoterGuidePossibility.objects.filter(
        Q(voter_guide_possibility_url__contains=net_location) &
        Q(organization_we_vote_id__iexact=organization_we_vote_id) &
        Q(date_last_changed__range=[startdate, enddate])).order_by('-date_last_changed')
    # leave destination in set     .exclude(id=voter_guide_possibility_id)
    voter_guide_possibility_list = list(voter_guide_possibility_query)
    ids_list = []
    for voter_guide_possibility in voter_guide_possibility_list:
        ids_list.append(voter_guide_possibility.id)

    possibility_position_query = VoterGuidePossibilityPosition.objects.filter(
        Q(voter_guide_possibility_parent_id__in=ids_list)).order_by(
            'ballot_item_name', '-voter_guide_possibility_parent_id')
    possibility_position_query_list = list(possibility_position_query)
    # for blip in possibility_position_query_list:
    #     print(str(blip.ballot_item_name) + "    " + str(blip.voter_guide_possibility_parent_id))

    # Remove duplicates, for now if the voter_guide_possibility_parent_id numer is higher, that is the one we keep
    seen_candidates = set()
    new_list = []
    for position in possibility_position_query_list:
        if position.ballot_item_name not in seen_candidates:
            new_list.append(position)
            seen_candidates.add(position.ballot_item_name)
            # TODO: If we have to change all the exising  position.voter_guide_possibility_parent_id entries to match
            #  the voter_guide_possibility_id passed in the query from the extension, our design could use improvement.
            #  It seems that VoterGuidePossibilityPosition items should not be tied to a specific VoterGuidePossibility,
            #  this would mean that we would lose the connection between a political data volunter an their changes, but
            #  we could solve this by versioning the VoterGuidePossibilityPosition and have a admin console that allowed
            #  us to review the changes
            if position.voter_guide_possibility_parent_id != voter_guide_possibility_id:
                position.voter_guide_possibility_parent_id = voter_guide_possibility_id
                try:
                    logger.debug("Updating '" + position.ballot_item_name + "' from parent id " +
                                 str(position.voter_guide_possibility_parent_id) + " to " +
                                 str(voter_guide_possibility_id))
                except Exception as e:
                    logger.error(
                        "move_voter_guide_possibility_positions_to_requested_voter_guide_possibility logger error: ", e)

                position.save()

    # print('-------')
    # for possible_postion in new_list:
    #     print(str(possible_postion.ballot_item_name) + "    " + str(possible_postion.voter_guide_possibility_parent_id))
    # print('-------')
    return


def voter_guide_possibility_save_for_api(  # voterGuidePossibilitySave
        voter_device_id,
        voter_guide_possibility_id,
        candidates_missing_from_we_vote=None,  # filter_selected_candidates_missing
        cannot_find_endorsements=None,  # filter_selected_not_available_yet
        capture_detailed_comments=None,  # filter_selected_capture_detailed_comments
        clear_organization_options=None,
        contributor_comments=None,
        contributor_email=None,
        done_needs_verification=None,  # filter_selected_done_needs_verification
        done_verified=None,  # filter_selected_done_verified
        from_prior_election=None,  # filter_selected_from_prior_election
        hide_from_active_review=None,  # filter_selected_archive
        ignore_this_source=None,  # filter_selected_ignore
        internal_notes=None,
        voter_guide_possibility_type=None,
        organization_we_vote_id=None,
        possible_organization_name=None,
        possible_organization_twitter_handle=None,
        candidate_we_vote_id=None,
        possible_candidate_name=None,
        possible_candidate_twitter_handle=None,
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
        status += "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_GUIDE_POSSIBILITY "
        # json_data = {
        #     'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_GUIDE_POSSIBILITY ",
        #     'success': False,
        #     'voter_device_id': voter_device_id,
        # }
        # return HttpResponse(json.dumps(json_data), content_type='application/json')

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
        if candidate_we_vote_id is not None:
            voter_guide_possibility.candidate_we_vote_id = candidate_we_vote_id
            at_least_one_change = True
        if candidates_missing_from_we_vote is not None:
            voter_guide_possibility.candidates_missing_from_we_vote = \
                positive_value_exists(candidates_missing_from_we_vote)
            at_least_one_change = True
        if cannot_find_endorsements is not None:
            voter_guide_possibility.cannot_find_endorsements = positive_value_exists(cannot_find_endorsements)
            at_least_one_change = True
        if capture_detailed_comments is not None:
            voter_guide_possibility.capture_detailed_comments = positive_value_exists(capture_detailed_comments)
            at_least_one_change = True
        if contributor_comments is not None:
            voter_guide_possibility.contributor_comments = contributor_comments
            at_least_one_change = True
        if contributor_email is not None:
            voter_guide_possibility.contributor_email = contributor_email
            at_least_one_change = True
        if done_needs_verification is not None:
            voter_guide_possibility.done_needs_verification = positive_value_exists(done_needs_verification)
            at_least_one_change = True
        if done_verified is not None:
            voter_guide_possibility.done_verified = positive_value_exists(done_verified)
            at_least_one_change = True
        if from_prior_election is not None:
            voter_guide_possibility.from_prior_election = positive_value_exists(from_prior_election)
            at_least_one_change = True
        if hide_from_active_review is not None:
            voter_guide_possibility.hide_from_active_review = positive_value_exists(hide_from_active_review)
            at_least_one_change = True
        if ignore_this_source is not None:
            voter_guide_possibility.ignore_this_source = positive_value_exists(ignore_this_source)
            at_least_one_change = True
        if internal_notes is not None:
            voter_guide_possibility.internal_notes = internal_notes
            at_least_one_change = True
        if limit_to_this_state_code is not None:
            voter_guide_possibility.state_code = limit_to_this_state_code
            at_least_one_change = True
        if organization_we_vote_id is not None:
            voter_guide_possibility.organization_we_vote_id = organization_we_vote_id
            at_least_one_change = True
        if possible_candidate_name is not None:
            voter_guide_possibility.candidate_name = possible_candidate_name
            at_least_one_change = True
        if possible_candidate_twitter_handle is not None:
            voter_guide_possibility.candidate_twitter_handle = possible_candidate_twitter_handle
            at_least_one_change = True
        if possible_organization_name is not None:
            voter_guide_possibility.organization_name = possible_organization_name
            at_least_one_change = True
        if possible_organization_twitter_handle is not None:
            voter_guide_possibility.organization_twitter_handle = possible_organization_twitter_handle
            at_least_one_change = True
        if voter_guide_possibility_type is not None:
            voter_guide_possibility.voter_guide_possibility_type = voter_guide_possibility_type
            at_least_one_change = True
        if clear_organization_options is not None:
            voter_guide_possibility.organization_we_vote_id = ''
            voter_guide_possibility.organization_name = ''
            voter_guide_possibility.organization_twitter_handle = ''
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
        voter_device_id=None,
        voter_guide_possibility_id=None,
        voter_guide_possibility_position_id=None,
        ballot_item_name=None,
        ballot_item_state_code=None,
        position_stance=None,
        statement_text=None,
        more_info_url=None,
        possibility_should_be_deleted=None,
        possibility_should_be_ignored=None,
        candidate_twitter_handle=None,
        candidate_we_vote_id=None,
        measure_we_vote_id=None,
        organization_name=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        position_should_be_removed=None,
        google_civic_election_id_list=None):
    status = "VOTER_GUIDE_POSSIBILITY_POSITION_SAVE "
    success = True
    # results = is_voter_device_id_valid(voter_device_id)
    # if not results['success']:
    #     return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if not positive_value_exists(voter_guide_possibility_id) \
            and not positive_value_exists(voter_guide_possibility_position_id):
        json_data = {
                'status': "MISSING_BOTH_REQUIRED_VARIABLES ",
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return json_data

    voter = fetch_voter_from_voter_device_link(voter_device_id)
    if voter and hasattr(voter, 'we_vote_id'):
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_GUIDE_POSSIBILITY "
        # json_data = {
        #     'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_GUIDE_POSSIBILITY ",
        #     'success': False,
        #     'voter_device_id': voter_device_id,
        # }
        # return json_data

    # At this point, we may or may not have a valid voter

    volunteer_task_manager = VolunteerTaskManager()
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
            return json_data
        else:
            status += "FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION_FOR_DELETE "
            status += results['status']
            json_data = {
                'status': status,
                'success': False,
            }
            return json_data

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
            return json_data
        voter_guide_possibility_position = results['voter_guide_possibility_position']
        voter_guide_possibility_id = voter_guide_possibility_position.voter_guide_possibility_parent_id
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
            return json_data

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
            return json_data
        voter_guide_possibility_position = create_results['voter_guide_possibility_position']
        voter_guide_possibility_position_id = voter_guide_possibility_position.id

    voter_guide_possibility_type = ""
    if not voter_guide_possibility_found:
        results = voter_guide_possibility_manager.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id)
        if results['voter_guide_possibility_found']:
            voter_guide_possibility = results['voter_guide_possibility']
            voter_guide_possibility_found = True
            voter_guide_possibility_type = voter_guide_possibility.voter_guide_possibility_type

    at_least_one_change = False
    # 2019-09-15 Switched from "None" to "positive_value_exists": For now we don't need to be able to wipe out
    # many of these variables via API call
    try:
        # if ballot_item_name is not None:
        if positive_value_exists(ballot_item_name):
            voter_guide_possibility_position.ballot_item_name = ballot_item_name
            at_least_one_change = True
        # if candidate_twitter_handle is not None:
        if positive_value_exists(candidate_twitter_handle):
            voter_guide_possibility_position.candidate_twitter_handle = candidate_twitter_handle
            at_least_one_change = True
        # if candidate_we_vote_id is not None:
        if positive_value_exists(candidate_we_vote_id):
            voter_guide_possibility_position.candidate_we_vote_id = candidate_we_vote_id
            at_least_one_change = True
        # if measure_we_vote_id is not None:
        if positive_value_exists(measure_we_vote_id):
            voter_guide_possibility_position.measure_we_vote_id = measure_we_vote_id
            at_least_one_change = True
        if more_info_url is not None:
            voter_guide_possibility_position.more_info_url = more_info_url
            at_least_one_change = True
        # if organization_name is not None:
        if positive_value_exists(organization_name):
            voter_guide_possibility_position.organization_name = organization_name
            at_least_one_change = True
        # if organization_twitter_handle is not None:
        if positive_value_exists(organization_twitter_handle):
            voter_guide_possibility_position.organization_twitter_handle = organization_twitter_handle
            at_least_one_change = True
        # if organization_we_vote_id is not None:
        if positive_value_exists(organization_we_vote_id):
            voter_guide_possibility_position.organization_we_vote_id = organization_we_vote_id
            at_least_one_change = True
        if position_should_be_removed is not None:
            voter_guide_possibility_position.position_should_be_removed = \
                positive_value_exists(position_should_be_removed)
            at_least_one_change = True
        # if position_stance is not None:
        if positive_value_exists(position_stance):
            voter_guide_possibility_position.position_stance = position_stance
            at_least_one_change = True
        if possibility_should_be_ignored is not None:
            voter_guide_possibility_position.possibility_should_be_ignored = \
                positive_value_exists(possibility_should_be_ignored)
            at_least_one_change = True
        if positive_value_exists(ballot_item_state_code):
            voter_guide_possibility_position.ballot_item_state_code = ballot_item_state_code
            at_least_one_change = True
        if statement_text is not None:
            voter_guide_possibility_position.statement_text = statement_text
            at_least_one_change = True

        if at_least_one_change:
            timezone = pytz.timezone("America/Los_Angeles")
            voter_guide_possibility_position.date_updated = timezone.localize(datetime.now())
            voter_guide_possibility_position.save()
    except Exception as e:
        status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY1 ' \
                  '{error} [type: {error_type}]'.format(error=str(e), error_type=type(e))
        success = False

    limit_to_this_state_code = ""
    if voter_guide_possibility_found:
        limit_to_this_state_code = voter_guide_possibility.state_code

    possible_endorsement_dict = {
        'possibility_position_id': voter_guide_possibility_position.id,
        'ballot_item_name': voter_guide_possibility_position.ballot_item_name,
        'ballot_item_state_code': voter_guide_possibility_position.ballot_item_state_code,
        'candidate_twitter_handle': voter_guide_possibility_position.candidate_twitter_handle,
        'candidate_we_vote_id': voter_guide_possibility_position.candidate_we_vote_id,
        # 'contest_office_name': 'contest_office_name',
        'google_civic_election_id': voter_guide_possibility_position.google_civic_election_id,
        'measure_we_vote_id': voter_guide_possibility_position.measure_we_vote_id,
        'more_info_url': voter_guide_possibility_position.more_info_url,
        'organization_name': voter_guide_possibility_position.organization_name,
        'organization_we_vote_id': voter_guide_possibility_position.organization_we_vote_id,
        'organization_twitter_handle': voter_guide_possibility_position.organization_twitter_handle,
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

    if voter_guide_possibility_type == ORGANIZATION_ENDORSING_CANDIDATES \
            or voter_guide_possibility_type == UNKNOWN_TYPE:
        is_organization_endorsing_candidates = True
        is_list_of_endorsements_for_candidate = False
        organization_we_vote_id = voter_guide_possibility_position.organization_we_vote_id
    elif voter_guide_possibility_type == ENDORSEMENTS_FOR_CANDIDATE:
        is_organization_endorsing_candidates = False
        is_list_of_endorsements_for_candidate = True
        candidate_we_vote_id = voter_guide_possibility_position.candidate_we_vote_id
    else:
        # Default to this
        is_organization_endorsing_candidates = True
        is_list_of_endorsements_for_candidate = False

    candidate_possible_endorsement_count = 0
    possible_endorsement_list = []
    if is_organization_endorsing_candidates:
        # We will need all candidates for all upcoming elections so we can search the HTML of
        #  the possible voter guide for these names
        all_possible_candidates_list_light = []
        if positive_value_exists(google_civic_election_id_list):
            results = retrieve_candidate_list_for_all_upcoming_elections(
                google_civic_election_id_list, limit_to_this_state_code=limit_to_this_state_code)
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

        # ballot_item_list_light = all_possible_candidates_list_light + all_possible_measures_list_light

        attach_objects = False
        from voter_guide.controllers_possibility_shared import augment_candidate_possible_position_data
        augment_results = augment_candidate_possible_position_data(
            possible_endorsement=possible_endorsement_dict,
            all_possible_candidates=all_possible_candidates_list_light,
            attach_objects=attach_objects,
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=limit_to_this_state_code)
        candidate_possible_endorsement_count = augment_results['possible_endorsement_count']
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

            # If here, we may want to create a new candidate
            if not positive_value_exists(candidate_we_vote_id) and not positive_value_exists(measure_we_vote_id):
                ballot_item_name = modified_possible_endorsement_dict['ballot_item_name'] \
                    if 'ballot_item_name' in modified_possible_endorsement_dict \
                       and positive_value_exists(modified_possible_endorsement_dict['ballot_item_name']) else ''
                ballot_item_state_code = modified_possible_endorsement_dict['ballot_item_state_code'] \
                    if 'ballot_item_state_code' in modified_possible_endorsement_dict \
                       and positive_value_exists(modified_possible_endorsement_dict['ballot_item_state_code']) else ''
                # Note: We currently assume this is a candidate (as opposed to a measure)
                new_candidate_created = False
                if positive_value_exists(ballot_item_name) and positive_value_exists(ballot_item_state_code):
                    from candidate.models import CandidateCampaign
                    try:
                        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
                        current_year = convert_to_int(datetime_now.year)
                        update_values = {
                            'candidate_name': ballot_item_name,
                            'candidate_year': current_year,
                            'google_civic_candidate_name': ballot_item_name,
                            'state_code': ballot_item_state_code,
                        }
                        candidate_on_stage, new_candidate_created = CandidateCampaign.objects.update_or_create(
                            candidate_name=ballot_item_name,
                            candidate_year=current_year,
                            # google_civic_candidate_name=ballot_item_name,
                            state_code=ballot_item_state_code,
                            defaults=update_values,
                        )
                        if new_candidate_created:
                            status += "NEW_CANDIDATE_CAMPAIGN_CREATED "
                        else:
                            status += "NEW_CANDIDATE_CAMPAIGN_UPDATED "
                        if positive_value_exists(candidate_on_stage.we_vote_id):
                            candidate_we_vote_id = candidate_on_stage.we_vote_id
                            modified_possible_endorsement_dict['candidate_we_vote_id'] = candidate_on_stage.we_vote_id
                    except Exception as e:
                        status += 'FAILED_TO_CREATE_CANDIDATE ' \
                                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                if new_candidate_created and positive_value_exists(voter_we_vote_id):
                    try:
                        # Give the volunteer who entered this credit
                        task_results = volunteer_task_manager.create_volunteer_task_completed(
                            action_constant=VOLUNTEER_ACTION_CANDIDATE_CREATED,
                            voter_id=voter_id,
                            voter_we_vote_id=voter_we_vote_id,
                        )
                    except Exception as e:
                        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
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
                    timezone = pytz.timezone("America/Los_Angeles")
                    voter_guide_possibility_position.date_updated = timezone.localize(datetime.now())
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
            return json_data
    else:
        # If here we are looking at page of endorsements for one candidate
        # We will need all organizations so we can search the HTML of the possible voter guide for these names
        possible_endorsement_list_from_url_scan = []
        all_possible_organizations_list_light_found = False
        all_possible_organizations_list_light = []
        # We pass in the candidate_we_vote_id so that the possible_position data package includes that from the start
        results = retrieve_organization_list_for_all_upcoming_elections(
            limit_to_this_state_code=limit_to_this_state_code, candidate_we_vote_id_to_include=candidate_we_vote_id)
        if results['organization_list_found']:
            all_possible_organizations_list_light_found = True
            all_possible_organizations_list_light = results['organization_list_light']

    # Now save additional entries found
    if candidate_possible_endorsement_count > 1 and len(possible_endorsement_list):
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
                return json_data

    # If here, the voter_guide_possibility was successfully saved, so we want to return the refreshed data
    json_data = voter_guide_possibility_positions_retrieve_for_api(
        voter_device_id,
        voter_guide_possibility_id=voter_guide_possibility_id,
        voter_guide_possibility_position_id=voter_guide_possibility_position_id)
    return json_data


def voter_guides_to_follow_retrieve_for_api(  # voterGuidesToFollowRetrieve
        voter_device_id,
        kind_of_ballot_item='',
        ballot_item_we_vote_id='',
        google_civic_election_id=0,
        search_string='',
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
            'status': 'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID ',
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
            'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID ",
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
                'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID VOTER_WE_VOTE_ID_NOT_FOUND ",
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
                 '{error} [type: {error_type}] '.format(error=str(e), error_type=type(e))
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
                'twitter_description':          voter_guide.twitter_description
                if positive_value_exists(voter_guide.twitter_description) and
                len(voter_guide.twitter_description) > 1 else '',
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
                    results = position_manager.retrieve_organization_candidate_position_with_we_vote_id(
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
                'status': status + ' VOTER_GUIDES_TO_FOLLOW_FOR_API_RETRIEVED-POSITIVE_NUMBER_RETRIEVED ',
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
    status = ''
    success = True
    if filter_voter_guides_by_issue is None:
        filter_voter_guides_by_issue = False
    voter_guide_list_found = False
    retrieve_public_positions = True  # The alternate is positions for friends-only. Since this method returns positions
    # to follow, we never need to return friend's positions here

    position_list_manager = PositionListManager()
    if (kind_of_ballot_item == CANDIDATE) and positive_value_exists(ballot_item_we_vote_id):
        candidate_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_candidate(
            retrieve_public_positions, candidate_id, ballot_item_we_vote_id, ANY_STANCE, read_only=True)
    elif (kind_of_ballot_item == MEASURE) and positive_value_exists(ballot_item_we_vote_id):
        measure_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
            retrieve_public_positions, measure_id, ballot_item_we_vote_id, ANY_STANCE, read_only=True)
    elif (kind_of_ballot_item == OFFICE) and positive_value_exists(ballot_item_we_vote_id):
        office_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
            retrieve_public_positions=True,
            contest_office_id=office_id,
            contest_office_we_vote_id=ballot_item_we_vote_id,
            stance_we_are_looking_for=ANY_STANCE,
            most_recent_only=False,
            read_only=True)
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
    try:
        organizations_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)
    except Exception as e:
        organizations_followed_by_voter = []
        status += "RETRIEVE_FOLLOW_ORGANIZATION_FAILED: " + str(e) + " "
        success = False

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

    status += 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_BY_BALLOT_ITEM '

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
    success = True

    # Start with orgs followed and ignored by this voter
    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    try:
        organization_we_vote_ids_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
                voter_id, return_we_vote_id)
        organization_we_vote_ids_ignored_by_voter = \
            follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(
                voter_id, return_we_vote_id)
    except Exception as e:
        organization_we_vote_ids_followed_by_voter = []
        organization_we_vote_ids_ignored_by_voter = []
        status += "ERROR_RETRIEVING_FOLLOWED_OR_IGNORED: " + str(e) + " "
        success = False

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
            'success':                      success,
            'status':                       "NO_VOTER_GUIDES_TO_FOLLOW_FOUND_FOR_THIS_ELECTION-FOR_VOTER",
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    status += 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_BY_ELECTION '

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


def voter_guides_upcoming_retrieve_for_api(  # voterGuidesUpcomingRetrieve && voterGuidesFromFriendsUpcomingRetrieve
        google_civic_election_id_list=[], friends_vs_public=PUBLIC_ONLY, voter_we_vote_id=''):
    status = ""

    voter_guides = []
    status += "RETRIEVING_VOTER_GUIDES_UPCOMING " + friends_vs_public + " "

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
    if positive_value_exists(voter_we_vote_id):
        voter_guide_organization_we_vote_id_already_from_friend = []
        # ####################
        # From friends
        voter_guide_list = []
        voter_guide_results = retrieve_voter_guides_from_friends(
            voter_we_vote_id=voter_we_vote_id,
            maximum_number_to_retrieve=100,
            sort_by='twitter_followers_count',
            sort_order='desc',
            google_civic_election_id_list=google_civic_election_id_list,
            read_only=True)
        status += voter_guide_results['status']
        if voter_guide_results['voter_guide_list_found']:
            voter_guide_list = voter_guide_results['voter_guide_list']
            for voter_guide in voter_guide_list:
                voter_guide_organization_we_vote_id_already_from_friend.append(voter_guide.organization_we_vote_id)
        # ####################
        # From SharedItems
        voter_guide_shared_results = retrieve_voter_guides_from_shared_items(
            voter_we_vote_id=voter_we_vote_id,
            maximum_number_to_retrieve=100,
            google_civic_election_id_list=google_civic_election_id_list,
            read_only=True)
        status += voter_guide_shared_results['status']
        if voter_guide_shared_results['voter_guide_list_found']:
            voter_guide_shared_list = voter_guide_shared_results['voter_guide_list']
            for voter_guide in voter_guide_shared_list:
                if voter_guide.organization_we_vote_id not in voter_guide_organization_we_vote_id_already_from_friend:
                    # Includes added variable to signal that this isn't from friend:
                    voter_guide.from_shared_item = True
                    voter_guide_list.append(voter_guide)
    else:
        # Dale 2020-06-01 maximum_number_to_retrieve=200 took too long for CDN timeout
        # Set to 125 so we have a better ability to search code for this routine
        voter_guide_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_generic(
            maximum_number_to_retrieve=125, sort_by='twitter_followers_count', sort_order='desc',
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

        if hasattr(voter_guide, 'from_shared_item') and positive_value_exists(voter_guide.from_shared_item):
            if hasattr(voter_guide, 'friends_vs_public') \
                    and voter_guide.friends_vs_public in (FRIENDS_AND_PUBLIC, FRIENDS_ONLY):
                friends_vs_public_for_this_voter_guide = voter_guide.friends_vs_public
            else:
                friends_vs_public_for_this_voter_guide = PUBLIC_ONLY
        else:
            friends_vs_public_for_this_voter_guide = friends_vs_public

        # Augment the voter guide with a list of ballot_item we_vote_id's that this org supports
        stance_we_are_looking_for = SUPPORT
        ballot_item_support_results = retrieve_ballot_item_we_vote_ids_for_organization_static(
            organization,
            google_civic_election_id,
            stance_we_are_looking_for,
            friends_vs_public=friends_vs_public_for_this_voter_guide,
            voter_we_vote_id=voter_we_vote_id)
        if ballot_item_support_results['count']:
            ballot_item_we_vote_ids_this_org_supports = ballot_item_support_results[
                'ballot_item_we_vote_ids_list']
        else:
            ballot_item_we_vote_ids_this_org_supports = []
        voter_guide.ballot_item_we_vote_ids_this_org_supports = ballot_item_we_vote_ids_this_org_supports

        # Augment the voter guide with a list of ballot_item we_vote_id's that this org has info about
        stance_we_are_looking_for = INFORMATION_ONLY
        ballot_item_info_only_results = retrieve_ballot_item_we_vote_ids_for_organization_static(
            organization,
            google_civic_election_id,
            stance_we_are_looking_for,
            friends_vs_public=friends_vs_public_for_this_voter_guide,
            voter_we_vote_id=voter_we_vote_id)
        if ballot_item_info_only_results['count']:
            ballot_item_we_vote_ids_this_org_info_only = ballot_item_info_only_results['ballot_item_we_vote_ids_list']
        else:
            ballot_item_we_vote_ids_this_org_info_only = []
        voter_guide.ballot_item_we_vote_ids_this_org_info_only = ballot_item_we_vote_ids_this_org_info_only

        # Augment the voter guide with a list of ballot_item we_vote_id's that this org opposes
        stance_we_are_looking_for = OPPOSE
        ballot_item_oppose_results = retrieve_ballot_item_we_vote_ids_for_organization_static(
            organization,
            google_civic_election_id,
            stance_we_are_looking_for,
            friends_vs_public=friends_vs_public_for_this_voter_guide,
            voter_we_vote_id=voter_we_vote_id)
        if ballot_item_oppose_results['count']:
            ballot_item_we_vote_ids_this_org_opposes = ballot_item_oppose_results['ballot_item_we_vote_ids_list']
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
            'from_shared_item':             hasattr(voter_guide, 'from_shared_item'),
            'google_civic_election_id':     voter_guide.google_civic_election_id,
            'issue_we_vote_ids_linked':     issue_we_vote_ids_linked,
            'last_updated':                 last_updated,
            'organization_we_vote_id':      voter_guide.organization_we_vote_id,
            'linked_voter_we_vote_id':      voter_guide.voter_we_vote_id,
            'owner_voter_id':               voter_guide.owner_voter_id,
            'pledge_goal':                  voter_guide.pledge_goal,
            'pledge_count':                 voter_guide.pledge_count,
            'public_figure_we_vote_id':     voter_guide.public_figure_we_vote_id,
            'time_span':                    voter_guide.vote_smart_time_span,
            'twitter_description':          voter_guide.twitter_description
            if positive_value_exists(voter_guide.twitter_description) and
            len(voter_guide.twitter_description) > 1 else '',
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

    number_retrieved = len(voter_guides)
    json_data = {
        'status': 'VOTER_GUIDES_TO_FOLLOW_FOR_API_RETRIEVED-JSON_DATA: ' + status,
        'success': True,
        'voter_guides': voter_guides,
        'number_retrieved': number_retrieved,
    }

    results = {
        'success': success,
        'status': status + 'VOTER_GUIDES_TO_FOLLOW_FOR_API_RETRIEVED-FINISHED ',
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
    status = ""
    success = True
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
        try:
            organization_we_vote_ids_followed_by_voter = \
                follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
                    voter_id, return_we_vote_id)
            organization_we_vote_ids_ignored_by_voter = \
                follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(
                    voter_id, return_we_vote_id)
        except Exception as e:
            organization_we_vote_ids_followed_by_voter = []
            organization_we_vote_ids_ignored_by_voter = []
            status += "ERROR_RETRIEVING_FOLLOWED_OR_IGNORED: " + str(e) + " "
            success = False

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
    voter_we_vote_id = ''
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
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
                organization_name=voter_full_name,
                organization_website="",
                organization_twitter_handle="",
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
        if refresh_results['values_changed'] or not positive_value_exists(voter_guide.voter_we_vote_id):
            status += "VOTER_GUIDE_VALUES_CHANGED "
            voter_guide = refresh_results['voter_guide']
            if not positive_value_exists(voter_guide.voter_we_vote_id) and positive_value_exists(voter_we_vote_id):
                voter_guide.voter_we_vote_id = voter_we_vote_id
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
        'twitter_description': voter_guide.twitter_description
        if positive_value_exists(voter_guide.twitter_description) and
        len(voter_guide.twitter_description) > 1 else '',
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
                'twitter_description':          voter_guide.twitter_description
                if positive_value_exists(voter_guide.twitter_description) and
                len(voter_guide.twitter_description) > 1 else '',
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


def voter_guides_retrieve_for_api(organization_we_vote_id="", voter_we_vote_id="",  # voterGuidesRetrieve
                                  maximum_number_to_retrieve=0):
    """
    This function allows us to search for voter guides using a variety of criteria.
    :param organization_we_vote_id:
    :param voter_we_vote_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    voter_guide_list_manager = VoterGuideListManager()
    election_manager = ElectionManager()
    results = voter_guide_list_manager.retrieve_all_voter_guides(
        organization_we_vote_id, 0, voter_we_vote_id, maximum_number_to_retrieve=maximum_number_to_retrieve)
    status = results['status']
    voter_guide_list = results['voter_guide_list']
    voter_guides = []
    elections_dict = {}
    elections_to_retrieve_by_we_vote_id = []
    if results['voter_guide_list_found']:
        for voter_guide in voter_guide_list:
            if positive_value_exists(voter_guide.google_civic_election_id) \
                    and voter_guide.google_civic_election_id not in elections_to_retrieve_by_we_vote_id:
                elections_to_retrieve_by_we_vote_id.append(voter_guide.google_civic_election_id)
        # Now retrieve all of these elections and put them in elections_dict
        election_results = election_manager.retrieve_elections_by_google_civic_election_id_list(
            google_civic_election_id_list=elections_to_retrieve_by_we_vote_id, read_only=True)
        if election_results['success']:
            election_list = election_results['election_list']
            for one_election in election_list:
                elections_dict[convert_to_int(one_election.google_civic_election_id)] = one_election
        for voter_guide in voter_guide_list:
            if voter_guide.last_updated:
                last_updated = voter_guide.last_updated.strftime('%Y-%m-%d %H:%M')
            else:
                last_updated = ''
            election_description_text = ''
            if positive_value_exists(voter_guide.google_civic_election_id):
                one_election = elections_dict.get(convert_to_int(voter_guide.google_civic_election_id))
                if one_election and positive_value_exists(one_election.google_civic_election_id):
                    election_description_text = one_election.election_name
            one_voter_guide = {
                'we_vote_id':                   voter_guide.we_vote_id,
                'google_civic_election_id':     voter_guide.google_civic_election_id,
                'election_day_text':            voter_guide.election_day_text,
                'election_description_text':    election_description_text,
                'voter_guide_display_name':     voter_guide.voter_guide_display_name(),
                'voter_guide_image_url_large':  voter_guide.we_vote_hosted_profile_image_url_large
                if positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large)
                else voter_guide.voter_guide_image_url(),
                'voter_guide_image_url_medium': voter_guide.we_vote_hosted_profile_image_url_medium,
                'voter_guide_image_url_tiny':   voter_guide.we_vote_hosted_profile_image_url_tiny,
                'voter_guide_owner_type':       voter_guide.voter_guide_owner_type,
                'organization_we_vote_id':      voter_guide.organization_we_vote_id,
                'twitter_description':          voter_guide.twitter_description
                if positive_value_exists(voter_guide.twitter_description) and
                len(voter_guide.twitter_description) > 1 else '',
                'twitter_followers_count':      voter_guide.twitter_followers_count,
                'twitter_handle':               voter_guide.twitter_handle,
                'pledge_goal':                  voter_guide.pledge_goal,
                'pledge_count':                 voter_guide.pledge_count,
                'state_code':                   voter_guide.state_code,
                'last_updated':                 last_updated,
            }
            voter_guides.append(one_voter_guide.copy())

        if not len(voter_guides):
            status += 'NO_VOTER_GUIDES_FOUND-STRANGE_BEHAVIOR '
        success = True
    else:
        status += 'NO_VOTER_GUIDE_LIST_FOUND '
        success = results['success']

    json_data = {
        'status': status,
        'success': success,
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
            'status':                       'VALID_VOTER_DEVICE_ID_MISSING ',
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
            'status':                       'VALID_VOTER_ID_MISSING ',
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
    if not results['voter_found']:
        status += results['status'] + 'VOTER_NOT_FOUND '
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
                'twitter_description':          voter_guide.twitter_description
                if positive_value_exists(voter_guide.twitter_description) and
                len(voter_guide.twitter_description) > 1 else '',
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
        success = results['success']

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
                'twitter_description':          one_organization.twitter_description
                if positive_value_exists(one_organization.twitter_description) and
                len(one_organization.twitter_description) > 1 else '',
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
        google_civic_election_id_list = [google_civic_election_id]
        results = voter_guide_list_manager.retrieve_voter_guides_for_election(google_civic_election_id_list)
        if results['voter_guide_list_found']:
            voter_guide_list_found = True
            voter_guide_list = results['voter_guide_list']
    else:
        results = voter_guide_list_manager.retrieve_all_voter_guides_order_by()
        if results['voter_guide_list_found']:
            voter_guide_list_found = True
            voter_guide_list = results['voter_guide_list']

    elections_dict = {}
    organizations_dict = {}
    voter_we_vote_id_dict = {}
    organization_we_vote_ids_refreshed = []
    if voter_guide_list_found:
        for voter_guide in voter_guide_list:
            if positive_value_exists(voter_guide.organization_we_vote_id):
                if voter_guide.organization_we_vote_id not in organization_we_vote_ids_refreshed:
                    results = refresh_organization_data_from_master_tables(voter_guide.organization_we_vote_id)
                    status += results['status']
                    if results['success']:
                        push_organization_data_to_other_table_caches(voter_guide.organization_we_vote_id)
                        organization_we_vote_ids_refreshed.append(voter_guide.organization_we_vote_id)
                if positive_value_exists(voter_guide.google_civic_election_id):
                    voter_guide_we_vote_id = ''
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                        voter_guide_we_vote_id,
                        voter_guide.organization_we_vote_id,
                        voter_guide.google_civic_election_id,
                        elections_dict=elections_dict,
                        organizations_dict=organizations_dict,
                        voter_we_vote_id_dict=voter_we_vote_id_dict,
                    )
                    if results['success']:
                        voter_guide_updated_count += 1
                        elections_dict = results['elections_dict']
                        organizations_dict = results['organizations_dict']
                        voter_we_vote_id_dict = results['voter_we_vote_id_dict']
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
    status = ''
    success = True
    voter_guide_list = []
    voter_guide_list_found = False

    follow_organization_list_manager = FollowOrganizationList()
    return_we_vote_id = True
    try:
        organization_we_vote_ids_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
                voter_id, return_we_vote_id)
    except Exception as e:
        organization_we_vote_ids_followed_by_voter = []
        status += "ERROR_RETRIEVING_FOLLOWED_OR_IGNORED: " + str(e) + " "
        success = False

    if success:
        voter_guide_list_object = VoterGuideListManager()
        results = voter_guide_list_object.retrieve_voter_guides_by_organization_list(
            organization_we_vote_ids_followed_by_voter)

        voter_guide_list = []
        if results['voter_guide_list_found']:
            voter_guide_list = results['voter_guide_list']
            status = 'SUCCESSFUL_RETRIEVE_VOTER_GUIDES_FOLLOWED '
            if len(voter_guide_list):
                voter_guide_list_found = True
        else:
            status = results['status']
            if not results['success']:
                success = False

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


def retrieve_voter_guides_from_friends(
        voter_we_vote_id='',
        maximum_number_to_retrieve=0,
        sort_by='',
        sort_order='',
        google_civic_election_id_list=[],
        read_only=False):
    """
    Get the voter guides for friends of the voter
    """
    status = ""
    voter_guide_list = []
    voter_guide_list_found = False
    if not positive_value_exists(maximum_number_to_retrieve):
        maximum_number_to_retrieve = 50

    friend_manager = FriendManager()
    friend_results = friend_manager.retrieve_current_friend_list(voter_we_vote_id)
    organization_we_vote_ids_from_friends = []
    if friend_results['current_friend_list_found']:
        current_friend_list = friend_results['current_friend_list']
        status += "CURRENT_FRIEND_LIST: "
        for one_friend in current_friend_list:
            if one_friend.viewer_voter_we_vote_id == voter_we_vote_id:
                # If viewer is the voter, the friend is the viewee
                if not positive_value_exists(one_friend.viewee_organization_we_vote_id):
                    one_friend = heal_current_friend(one_friend)
                try:
                    organization_we_vote_ids_from_friends.append(one_friend.viewee_organization_we_vote_id)
                    status += "(viewee: " + one_friend.viewee_voter_we_vote_id + \
                              "/" + one_friend.viewee_organization_we_vote_id + ")"
                except Exception as e:
                    status += "APPEND_PROBLEM1: " + str(e) + ' '
            else:
                # If viewer is NOT the voter, the friend is the viewer
                if not positive_value_exists(one_friend.viewer_organization_we_vote_id):
                    one_friend = heal_current_friend(one_friend)
                try:
                    organization_we_vote_ids_from_friends.append(one_friend.viewer_organization_we_vote_id)
                    status += "(viewer: " + one_friend.viewer_voter_we_vote_id + \
                              "/" + one_friend.viewer_organization_we_vote_id + ")"
                except Exception as e:
                    status += "APPEND_PROBLEM2: " + str(e) + ' '

    if len(organization_we_vote_ids_from_friends) == 0:
        success = True
        status += "NO_FRIENDS_FOUND_SO_NO_VOTER_GUIDES "
        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results
    try:
        if read_only:
            voter_guide_query = VoterGuide.objects.using('readonly').all()
        else:
            voter_guide_query = VoterGuide.objects.all()
        # As of August 2018, we no longer want to support Vote Smart ratings voter guides
        voter_guide_query = voter_guide_query.exclude(vote_smart_time_span__isnull=False)
        voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)

        voter_guide_query = voter_guide_query.filter(
            organization_we_vote_id__in=organization_we_vote_ids_from_friends)

        if positive_value_exists(len(google_civic_election_id_list)):
            status += "CONVERTING_GOOGLE_CIVIC_ELECTION_ID_LIST_TO_INTEGER "
            google_civic_election_id_integer_list = []
            for google_civic_election_id in google_civic_election_id_list:
                google_civic_election_id_integer_list.append(convert_to_int(google_civic_election_id))
            voter_guide_query = voter_guide_query.filter(
                google_civic_election_id__in=google_civic_election_id_integer_list)

        # We retrieve anyone you are friends with, even if they are public figures

        if not positive_value_exists(len(google_civic_election_id_list)):
            # We also want to exclude voter guides with election_day_text smaller than today's date
            status += "EXCLUDE_PAST_ELECTION_DAYS "
            # timezone = pytz.timezone("America/Los_Angeles")
            # datetime_now = timezone.localize(datetime.now())
            datetime_now = generate_localized_datetime_from_obj()[1]
            two_days = timedelta(days=2)
            datetime_two_days_ago = datetime_now - two_days
            earliest_date_to_show = datetime_two_days_ago.strftime("%Y-%m-%d")
            voter_guide_query = voter_guide_query.exclude(election_day_text__lt=earliest_date_to_show)
            voter_guide_query = voter_guide_query.exclude(election_day_text__isnull=True)

        if sort_order == 'desc':
            voter_guide_query = voter_guide_query.order_by('-' + sort_by)[:maximum_number_to_retrieve]
        elif positive_value_exists(sort_by):
            voter_guide_query = voter_guide_query.order_by(sort_by)[:maximum_number_to_retrieve]
        else:
            voter_guide_query = voter_guide_query[:maximum_number_to_retrieve]

        voter_guide_list = list(voter_guide_query)
        if len(voter_guide_list):
            voter_guide_list_found = True
            status += 'VOTER_GUIDE_FOUND_VOTER_GUIDES_TO_FOLLOW_FROM_FRIENDS '
        else:
            status += 'NO_VOTER_GUIDES_FOUND_VOTER_GUIDES_TO_FOLLOW_FROM_FRIENDS '
        success = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        status += 'retrieve_voter_guides_to_follow_generic: Unable to retrieve voter guides from db. ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    # Since we are in the function that retrieves voter guides for voterGuidesFromFriendsUpcomingRetrieve
    # heal the data if we haven't moved the voter_we_vote_id into the voter_guide
    if voter_guide_list_found:
        voter_manager = VoterManager()
        for one_voter_guide in voter_guide_list:
            if not positive_value_exists(one_voter_guide.voter_we_vote_id):
                if read_only:
                    # Retrieve fresh object that will allow us to save
                    voter_guide_manager = VoterGuideManager()
                    voter_guide_results = voter_guide_manager.retrieve_voter_guide(voter_guide_id=one_voter_guide.id)
                    if voter_guide_results['voter_guide_found']:
                        one_voter_guide = voter_guide_results['voter_guide']
                results = voter_manager.retrieve_voter_by_organization_we_vote_id(
                    one_voter_guide.organization_we_vote_id)
                if results['voter_found']:
                    try:
                        one_voter_guide.voter_we_vote_id = results['voter'].we_vote_id
                        one_voter_guide.save()
                    except Exception as e:
                        status += 'COULD_NOT_UPDATE_VOTER_WE_VOTE_ID ' + str(e) + ' '

    # If we have multiple voter guides for one org, we only want to show the most recent
    if voter_guide_list_found:
        if not positive_value_exists(len(google_civic_election_id_list)):
            # If we haven't specified multiple elections, then remove old voter guides
            voter_guide_list_manager = VoterGuideListManager()
            voter_guide_list_filtered = \
                voter_guide_list_manager.remove_older_voter_guides_for_each_org(voter_guide_list)
        else:
            voter_guide_list_filtered = voter_guide_list
    else:
        voter_guide_list_filtered = []

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list_filtered,
    }
    return results


def retrieve_voter_guides_from_shared_items(
        voter_we_vote_id='',
        maximum_number_to_retrieve=0,
        sort_by='',
        sort_order='',
        google_civic_election_id_list=[],
        read_only=False):
    """
    Get the voter guides for the people who have shared with you
    """
    status = ""
    voter_guide_list = []
    voter_guide_list_found = False
    if not positive_value_exists(maximum_number_to_retrieve):
        maximum_number_to_retrieve = 30

    share_manager = ShareManager()
    permission_results = share_manager.retrieve_shared_permissions_granted_list(
        shared_to_voter_we_vote_id=voter_we_vote_id,
        current_year_only=True,
        read_only=True)
    shared_permissions_granted_list = []
    shared_by_organization_we_vote_id_list = []
    if permission_results['shared_permissions_granted_list_found']:
        shared_permissions_granted_list = permission_results['shared_permissions_granted_list']
        for shared_permissions_granted in shared_permissions_granted_list:
            if positive_value_exists(shared_permissions_granted.shared_by_organization_we_vote_id) \
                    and shared_permissions_granted.shared_by_organization_we_vote_id \
                    not in shared_by_organization_we_vote_id_list:
                shared_by_organization_we_vote_id_list.append(
                    shared_permissions_granted.shared_by_organization_we_vote_id)

    if len(shared_by_organization_we_vote_id_list) == 0:
        success = True
        status += "NO_SHARED_BY_ORGANIZATIONS_SO_NO_VOTER_GUIDES "
        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results
    try:
        if read_only:
            voter_guide_query = VoterGuide.objects.using('readonly').all()
        else:
            voter_guide_query = VoterGuide.objects.all()
        # As of August 2018, we no longer want to support Vote Smart ratings voter guides
        voter_guide_query = voter_guide_query.exclude(vote_smart_time_span__isnull=False)
        voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)

        voter_guide_query = voter_guide_query.filter(
            organization_we_vote_id__in=shared_by_organization_we_vote_id_list)

        if positive_value_exists(len(google_civic_election_id_list)):
            status += "CONVERTING_GOOGLE_CIVIC_ELECTION_ID_LIST_TO_INTEGER "
            google_civic_election_id_integer_list = []
            for google_civic_election_id in google_civic_election_id_list:
                google_civic_election_id_integer_list.append(convert_to_int(google_civic_election_id))
            voter_guide_query = voter_guide_query.filter(
                google_civic_election_id__in=google_civic_election_id_integer_list)

        # We retrieve anyone you are friends with, even if they are public figures

        if not positive_value_exists(len(google_civic_election_id_list)):
            # We also want to exclude voter guides with election_day_text smaller than today's date
            status += "EXCLUDE_PAST_ELECTION_DAYS "
            # timezone = pytz.timezone("America/Los_Angeles")
            # datetime_now = timezone.localize(datetime.now())
            datetime_now = generate_localized_datetime_from_obj()[1]
            two_days = timedelta(days=2)
            datetime_two_days_ago = datetime_now - two_days
            earliest_date_to_show = datetime_two_days_ago.strftime("%Y-%m-%d")
            voter_guide_query = voter_guide_query.exclude(election_day_text__lt=earliest_date_to_show)
            voter_guide_query = voter_guide_query.exclude(election_day_text__isnull=True)

        if sort_order == 'desc':
            voter_guide_query = voter_guide_query.order_by('-' + sort_by)[:maximum_number_to_retrieve]
        elif positive_value_exists(sort_by):
            voter_guide_query = voter_guide_query.order_by(sort_by)[:maximum_number_to_retrieve]
        else:
            voter_guide_query = voter_guide_query[:maximum_number_to_retrieve]

        voter_guide_list = list(voter_guide_query)
        if len(voter_guide_list):
            voter_guide_list_found = True
            status += 'VOTER_GUIDE_FOUND_VOTER_GUIDES_FROM_SHARED_ITEMS '
        else:
            status += 'NO_VOTER_GUIDES_FOUND_VOTER_GUIDES_FROM_SHARED_ITEMS '
        success = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        status += 'RETRIEVE_VOTER_GUIDES_FROM_SHARED_ITEMS-FAILED ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    # Since we are in the function that retrieves voter guides for voterGuidesFromFriendsUpcomingRetrieve
    # heal the data if we haven't moved the voter_we_vote_id into the voter_guide
    if voter_guide_list_found:
        voter_manager = VoterManager()
        for one_voter_guide in voter_guide_list:
            if not positive_value_exists(one_voter_guide.voter_we_vote_id):
                if read_only:
                    # Retrieve fresh object that will allow us to save
                    voter_guide_manager = VoterGuideManager()
                    voter_guide_results = voter_guide_manager.retrieve_voter_guide(voter_guide_id=one_voter_guide.id)
                    if voter_guide_results['voter_guide_found']:
                        one_voter_guide = voter_guide_results['voter_guide']
                results = voter_manager.retrieve_voter_by_organization_we_vote_id(
                    one_voter_guide.organization_we_vote_id)
                if results['voter_found']:
                    try:
                        one_voter_guide.voter_we_vote_id = results['voter'].we_vote_id
                        one_voter_guide.save()
                    except Exception as e:
                        status += 'SHARED_ITEMS-COULD_NOT_UPDATE_VOTER_WE_VOTE_ID ' + str(e) + ' '
    else:
        voter_guide_list = []

    # # If we have multiple voter guides for one org, we only want to show the most recent
    # if voter_guide_list_found:
    #     if not positive_value_exists(len(google_civic_election_id_list)):
    #         # If we haven't specified multiple elections, then remove old voter guides
    #         voter_guide_list_manager = VoterGuideListManager()
    #         voter_guide_list_filtered = \
    #             voter_guide_list_manager.remove_older_voter_guides_for_each_org(voter_guide_list)
    #     else:
    #         voter_guide_list_filtered = voter_guide_list
    # else:
    #     voter_guide_list_filtered = []

    voter_guide_list_augmented = []
    for voter_guide in voter_guide_list:
        include_friends_only_positions = False
        voter_guide.from_shared_item = True
        for shared_permissions_granted in shared_permissions_granted_list:
            if voter_guide.organization_we_vote_id == shared_permissions_granted.shared_by_organization_we_vote_id:
                include_friends_only_positions = shared_permissions_granted.include_friends_only_positions
                break
        if include_friends_only_positions:
            voter_guide.friends_vs_public = FRIENDS_AND_PUBLIC
        else:
            voter_guide.friends_vs_public = PUBLIC_ONLY
        voter_guide_list_augmented.append(voter_guide)
    voter_guide_list_found = len(voter_guide_list_augmented)

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list_augmented,
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
                'twitter_description':          voter_guide.twitter_description
                if positive_value_exists(voter_guide.twitter_description) and
                len(voter_guide.twitter_description) > 1 else '',
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
        follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(
            voter_id, return_we_vote_id)

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
