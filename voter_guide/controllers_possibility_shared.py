# voter_guide/controllers_possibility_shared.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import copy
from config.base import get_environment_variable
from candidate.models import CandidateListManager, CandidateManager
from office.models import ContestOfficeManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import convert_date_to_we_vote_date_string

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut


def augment_candidate_possible_position_data(
        possible_endorsement,
        google_civic_election_id_list=[],
        limit_to_this_state_code="",
        all_possible_candidates=[],
        attach_objects=True):
    status = ""
    success = True
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    contest_office_manager = ContestOfficeManager()

    possible_endorsement_matched = False
    possible_endorsement_return_list = []
    possible_endorsement_count = 0
    possible_endorsement['withdrawn_from_election'] = False
    possible_endorsement['withdrawal_date'] = ''
    withdrawal_date_as_string = ''

    if 'candidate_we_vote_id' in possible_endorsement \
            and positive_value_exists(possible_endorsement['candidate_we_vote_id']):
        possible_endorsement_matched = True
        results = candidate_manager.retrieve_candidate_from_we_vote_id(
            possible_endorsement['candidate_we_vote_id'], read_only=True)
        if results['candidate_found']:
            candidate = results['candidate']
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
            possible_endorsement['withdrawn_from_election'] = candidate.withdrawn_from_election
            try:
                withdrawal_date_as_string = convert_date_to_we_vote_date_string(candidate.withdrawal_date)
            except Exception as e:
                status += "COULD_NOT_CONVERT candidate.withdrawal_date TO_STRING: " + str(e) + " "
            possible_endorsement['withdrawal_date'] = withdrawal_date_as_string

        possible_endorsement_count += 1
        possible_endorsement_return_list.append(possible_endorsement)
    elif 'ballot_item_name' in possible_endorsement and \
            positive_value_exists(possible_endorsement['ballot_item_name']):
        possible_endorsement_matched = True
        if not positive_value_exists(limit_to_this_state_code):
            if 'ballot_item_state_code' in possible_endorsement and \
                    positive_value_exists(possible_endorsement['ballot_item_state_code']):
                limit_to_this_state_code = possible_endorsement['ballot_item_state_code']
        # If here search for possible candidate matches
        matching_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=limit_to_this_state_code,
            candidate_name=possible_endorsement['ballot_item_name'],
            read_only=True)

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
            possible_endorsement['withdrawn_from_election'] = candidate.withdrawn_from_election
            try:
                withdrawal_date_as_string = convert_date_to_we_vote_date_string(candidate.withdrawal_date)
            except Exception as e:
                status += "COULD_NOT_CONVERT candidate.withdrawal_date TO_STRING: " + str(e) + " "
            possible_endorsement['withdrawal_date'] = withdrawal_date_as_string
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
                possible_endorsement_copy['withdrawn_from_election'] = candidate.withdrawn_from_election
                try:
                    withdrawal_date_as_string = convert_date_to_we_vote_date_string(candidate.withdrawal_date)
                except Exception as e:
                    status += "COULD_NOT_CONVERT candidate.withdrawal_date TO_STRING: " + str(e) + " "
                possible_endorsement['withdrawal_date'] = withdrawal_date_as_string
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
                    if 'google_civic_election_id' in one_endorsement_light:
                        possible_endorsement['google_civic_election_id'] = \
                            one_endorsement_light['google_civic_election_id']
                    else:
                        possible_endorsement['google_civic_election_id'] = 0
                    matching_results = candidate_manager.retrieve_candidate_from_we_vote_id(
                        possible_endorsement['candidate_we_vote_id'], read_only=True)

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
                        possible_endorsement['withdrawn_from_election'] = candidate.withdrawn_from_election
                        try:
                            withdrawal_date_as_string = convert_date_to_we_vote_date_string(candidate.withdrawal_date)
                        except Exception as e:
                            status += "COULD_NOT_CONVERT candidate.withdrawal_date TO_STRING: " + str(e) + " "
                        possible_endorsement['withdrawal_date'] = withdrawal_date_as_string
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
            # Hanging off each ballot_item_dict is an alternate_names that includes
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
                        if 'google_civic_election_id' in one_endorsement_light:
                            possible_endorsement_copy['google_civic_election_id'] = \
                                one_endorsement_light['google_civic_election_id']
                        else:
                            possible_endorsement_copy['google_civic_election_id'] = 0
                        matching_results = candidate_manager.retrieve_candidate_from_we_vote_id(
                            possible_endorsement_copy['candidate_we_vote_id'], read_only=True)

                        if matching_results['candidate_found']:
                            candidate = matching_results['candidate']

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
                            possible_endorsement_copy['withdrawn_from_election'] = candidate.withdrawn_from_election
                            try:
                                withdrawal_date_as_string = convert_date_to_we_vote_date_string(
                                    candidate.withdrawal_date)
                            except Exception as e:
                                status += "COULD_NOT_CONVERT candidate.withdrawal_date TO_STRING: " + str(e) + " "
                            possible_endorsement['withdrawal_date'] = withdrawal_date_as_string

                        synonym_found = True
                        possible_endorsement_count += 1
                        possible_endorsement_return_list.append(possible_endorsement_copy)
                        break

        if not synonym_found:
            # If an entry based on a synonym wasn't found, then store the original possibility
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)

    # Finally, if the possible_endorsement wasn't matched to any existing records, we still want to use it
    if possible_endorsement_matched and not positive_value_exists(possible_endorsement_count):
        possible_endorsement_count += 1
        possible_endorsement_return_list.append(possible_endorsement)

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_return_list': possible_endorsement_return_list,
        'possible_endorsement_count':       possible_endorsement_count,
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

