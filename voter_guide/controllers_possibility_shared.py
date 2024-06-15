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


def already_in_list_test(
        possible_endorsement,
        already_found_we_vote_id_list,
        is_organization_endorsing_candidates=True):
    if is_organization_endorsing_candidates:
        already_in_list = 'candidate_we_vote_id' in possible_endorsement \
                          and positive_value_exists(possible_endorsement['candidate_we_vote_id']) \
                          and possible_endorsement['candidate_we_vote_id'] in already_found_we_vote_id_list
    else:
        already_in_list = 'organization_we_vote_id' in possible_endorsement \
                          and positive_value_exists(possible_endorsement['organization_we_vote_id']) \
                          and possible_endorsement['organization_we_vote_id'] in already_found_we_vote_id_list
    return already_in_list


def unique_add_to_already_found_list(
        possible_endorsement,
        already_found_we_vote_id_list,
        is_organization_endorsing_candidates=True):
    already_in_list = \
        already_in_list_test(possible_endorsement, already_found_we_vote_id_list, is_organization_endorsing_candidates)
    if not already_in_list:
        if is_organization_endorsing_candidates:
            if positive_value_exists(possible_endorsement['candidate_we_vote_id']):
                already_found_we_vote_id_list.append(possible_endorsement['candidate_we_vote_id'])
        else:
            if positive_value_exists(possible_endorsement['organization_we_vote_id']):
                already_found_we_vote_id_list.append(possible_endorsement['organization_we_vote_id'])
    return already_found_we_vote_id_list


def augment_candidate_possible_position_data(
        possible_endorsement={},
        all_possible_candidates=[],
        already_found_we_vote_id_list=[],
        attach_objects=True,
        candidates_dict={},
        google_civic_election_id_list=[],
        is_organization_endorsing_candidates=True,
        limit_to_this_state_code=""):
    already_found_we_vote_id_list_local = copy.deepcopy(already_found_we_vote_id_list)
    status = ""
    success = True
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()

    possible_endorsement_matched = False
    possible_endorsement_return_list = []
    possible_endorsement_count = 0
    possible_endorsement['withdrawn_from_election'] = False
    possible_endorsement['withdrawal_date'] = ''

    if 'candidate_we_vote_id' in possible_endorsement \
            and positive_value_exists(possible_endorsement['candidate_we_vote_id']):
        if possible_endorsement['candidate_we_vote_id'] in candidates_dict:
            candidate = candidates_dict[possible_endorsement['candidate_we_vote_id']]
        else:
            candidate = None
        if not candidate:
            results = candidate_manager.retrieve_candidate_from_we_vote_id(
                possible_endorsement['candidate_we_vote_id'], read_only=True)
            if results['candidate_found']:
                candidate = results['candidate']
                candidates_dict[candidate.we_vote_id] = candidate
        if candidate and hasattr(candidate, 'we_vote_id') and positive_value_exists(candidate.we_vote_id):
            possible_endorsement, status2 = \
                attach_candidate_fields_to_possible_endorsement(candidate, possible_endorsement, attach_objects)
            # status += status2
        else:
            status += "MISSING_WE_VOTE_ID_FOR_CANDIDATE100 "

        possible_endorsement_count += 1
        possible_endorsement_return_list.append(possible_endorsement)
        possible_endorsement_matched = True
        if is_organization_endorsing_candidates:
            already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                possible_endorsement,
                already_found_we_vote_id_list_local,
                is_organization_endorsing_candidates)
    elif is_organization_endorsing_candidates:
        is_organization_endorsing_results = \
            augment_or_expand_candidate_possible_position_data_when_is_organization_endorsing(
                possible_endorsement=possible_endorsement,
                all_possible_candidates=all_possible_candidates,
                already_found_we_vote_id_list=already_found_we_vote_id_list_local,
                attach_objects=attach_objects,
                candidates_dict=candidates_dict,
                google_civic_election_id_list=google_civic_election_id_list,
                limit_to_this_state_code=limit_to_this_state_code
            )
        already_found_we_vote_id_list_local = is_organization_endorsing_results['already_found_we_vote_id_list']
        candidates_dict = is_organization_endorsing_results['candidates_dict']
        possible_endorsement_count = is_organization_endorsing_results['possible_endorsement_count']
        possible_endorsement_return_list = is_organization_endorsing_results['possible_endorsement_return_list']
        status = is_organization_endorsing_results['status']
        success = is_organization_endorsing_results['success']
    else:
        # If here, is_list_of_endorsements_for_candidate, and we want to see if we can find the
        #  candidate_we_vote_id from the incoming candidate_name. But only one -- we don't want
        #  to expand out the options.
        if 'ballot_item_name' in possible_endorsement and \
                positive_value_exists(possible_endorsement['ballot_item_name']):
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
                if hasattr(candidate, 'we_vote_id') and positive_value_exists(candidate.we_vote_id):
                    candidates_dict[candidate.we_vote_id] = candidate
                    possible_endorsement, status2 = attach_candidate_fields_to_possible_endorsement(
                        candidate, possible_endorsement, attach_objects)
                    # status += status2
                else:
                    status += "MISSING_WE_VOTE_ID_FOR_CANDIDATE09 "
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement)
                possible_endorsement_matched = True
                if is_organization_endorsing_candidates:
                    already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                        possible_endorsement,
                        already_found_we_vote_id_list_local,
                        is_organization_endorsing_candidates)
            elif matching_results['candidate_list_found']:
                # Keep the current option as is -- we don't know enough to pick which one to use
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement)
                possible_endorsement_matched = True
                if is_organization_endorsing_candidates:
                    already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                        possible_endorsement,
                        already_found_we_vote_id_list_local,
                        is_organization_endorsing_candidates)
            elif not positive_value_exists(matching_results['success']):
                status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-NO_SUCCESS "
                status += matching_results['status']
                already_in_list = already_in_list_test(
                    possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
                if is_organization_endorsing_candidates and already_in_list:
                    status += "ALREADY_IN_LIST4 "
                else:
                    possible_endorsement_count += 1
                    possible_endorsement_return_list.append(possible_endorsement)
                    possible_endorsement_matched = True
                    if is_organization_endorsing_candidates:
                        already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                            possible_endorsement,
                            already_found_we_vote_id_list_local,
                            is_organization_endorsing_candidates)
            else:
                status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-CANDIDATE_NOT_FOUND "
        else:
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)
            if is_organization_endorsing_candidates:
                already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                    possible_endorsement,
                    already_found_we_vote_id_list_local,
                    is_organization_endorsing_candidates)

    # Finally, if the possible_endorsement wasn't matched to any existing records, we still want to use it
    if possible_endorsement_matched and not positive_value_exists(possible_endorsement_count):
        already_in_list = already_in_list_test(
            possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
        if is_organization_endorsing_candidates and already_in_list:
            status += "ALREADY_IN_LIST8 "
        else:
            # If an entry based on a synonym wasn't found, then store the original possibility
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)
            # possible_endorsement_matched = True
            if is_organization_endorsing_candidates:
                already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                    possible_endorsement,
                    already_found_we_vote_id_list_local,
                    is_organization_endorsing_candidates)

    results = {
        'already_found_we_vote_id_list':        already_found_we_vote_id_list_local,
        'candidates_dict':                      candidates_dict,
        'status':                               status,
        'success':                              success,
        'possible_endorsement_return_list':     possible_endorsement_return_list,
        'possible_endorsement_count':           possible_endorsement_count,
    }

    return results


def attach_candidate_fields_to_possible_endorsement(candidate, possible_endorsement, attach_objects=False):
    status = ""
    # If one candidate found, add we_vote_id here
    possible_endorsement['candidate_we_vote_id'] = candidate.we_vote_id
    if positive_value_exists(attach_objects):
        possible_endorsement['candidate'] = candidate
    # Don't change ballot_item_name, so it matches what is coming in from the page. Only add if missing.
    if not positive_value_exists(possible_endorsement['ballot_item_name']):
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
        contest_office_manager = ContestOfficeManager()
        possible_endorsement['google_civic_election_id'] = \
            contest_office_manager.fetch_google_civic_election_id_from_office_we_vote_id(
                candidate.contest_office_we_vote_id)
    possible_endorsement['withdrawn_from_election'] = candidate.withdrawn_from_election
    try:
        withdrawal_date_as_string = convert_date_to_we_vote_date_string(candidate.withdrawal_date)
    except Exception as e:
        status += "COULD_NOT_CONVERT candidate.withdrawal_date TO_STRING: " + str(e) + " "
        withdrawal_date_as_string = ""
    possible_endorsement['withdrawal_date'] = withdrawal_date_as_string
    return possible_endorsement, status


def augment_or_expand_candidate_possible_position_data_when_is_organization_endorsing(
        possible_endorsement={},
        all_possible_candidates=[],
        already_found_we_vote_id_list=[],
        attach_objects=True,
        candidates_dict={},
        google_civic_election_id_list=[],
        limit_to_this_state_code=""):
    already_found_we_vote_id_list_local = copy.deepcopy(already_found_we_vote_id_list)
    status = ""
    success = True
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    contest_office_manager = ContestOfficeManager()

    is_organization_endorsing_candidates = True
    possible_endorsement_matched = False
    possible_endorsement_return_list = []
    possible_endorsement_count = 0
    withdrawal_date_as_string = ''

    if 'candidate_we_vote_id' in possible_endorsement \
            and positive_value_exists(possible_endorsement['candidate_we_vote_id']):
        # We don't need to process this condition because it is taken care of in
        # augment_or_expand_candidate_possible_position_data()
        pass
    elif 'ballot_item_name' in possible_endorsement and \
            positive_value_exists(possible_endorsement['ballot_item_name']):
        # If here, is_list_of_endorsements_for_candidate, and we want to see if we can find the
        #  candidate_we_vote_id from the incoming candidate_name (in ballot_item_name field).
        #  If we find multiple options, we add them to the list, so they can be filtered out manually.
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
            already_in_list = already_in_list_test(
                possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
            if is_organization_endorsing_candidates and already_in_list:
                status += "ALREADY_IN_LIST10 "
            else:
                candidate = matching_results['candidate']
                if hasattr(candidate, 'we_vote_id') and positive_value_exists(candidate.we_vote_id):
                    candidates_dict[candidate.we_vote_id] = candidate
                    possible_endorsement, status2 = attach_candidate_fields_to_possible_endorsement(
                        candidate, possible_endorsement, attach_objects)
                    # status += status2
                else:
                    status += "MISSING_WE_VOTE_ID_FOR_CANDIDATE10 "
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement)
                if is_organization_endorsing_candidates:
                    already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                        possible_endorsement,
                        already_found_we_vote_id_list_local,
                        is_organization_endorsing_candidates)
        elif matching_results['candidate_list_found']:
            already_in_list = already_in_list_test(
                possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
            if is_organization_endorsing_candidates and already_in_list:
                status += "ALREADY_IN_LIST12 "
            else:
                # Keep the current option
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement)
                possible_endorsement_matched = True
                if is_organization_endorsing_candidates:
                    already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                        possible_endorsement,
                        already_found_we_vote_id_list_local,
                        is_organization_endorsing_candidates)
            # ...and add entries for other possible matches
            status += "MULTIPLE_CANDIDATES_FOUND "
            candidate_list = matching_results['candidate_list']
            for candidate in candidate_list:
                if hasattr(candidate, 'we_vote_id') and positive_value_exists(candidate.we_vote_id):
                    candidates_dict[candidate.we_vote_id] = candidate
                    if is_organization_endorsing_candidates and \
                            positive_value_exists(candidate.we_vote_id) and \
                            candidate.we_vote_id in already_found_we_vote_id_list_local:
                        status += "ALREADY_IN_LIST13 "
                    else:
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
                        if is_organization_endorsing_candidates:
                            already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                                possible_endorsement,
                                already_found_we_vote_id_list_local,
                                is_organization_endorsing_candidates)
        elif not positive_value_exists(matching_results['success']):
            status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-NO_SUCCESS "
            status += matching_results['status']
            already_in_list = already_in_list_test(
                possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
            if is_organization_endorsing_candidates and already_in_list:
                status += "ALREADY_IN_LIST14 "
            else:
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement)
                possible_endorsement_matched = True
                if is_organization_endorsing_candidates:
                    already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                        possible_endorsement,
                        already_found_we_vote_id_list_local,
                        is_organization_endorsing_candidates)
        else:
            status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-CANDIDATE_NOT_FOUND "

            # Now we want to do a reverse search, where we cycle through all upcoming candidates and search
            # within the incoming text for a known candidate name
            for one_endorsement_light in all_possible_candidates:
                if positive_value_exists(one_endorsement_light['ballot_item_display_name']) and \
                        one_endorsement_light['ballot_item_display_name'] in possible_endorsement['ballot_item_name']:
                    possible_endorsement['candidate_we_vote_id'] = one_endorsement_light['candidate_we_vote_id']
                    already_in_list = already_in_list_test(
                        possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
                    if is_organization_endorsing_candidates and already_in_list:
                        status += "ALREADY_IN_LIST15 "
                        continue
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
                        if hasattr(candidate, 'we_vote_id') and positive_value_exists(candidate.we_vote_id):
                            candidates_dict[candidate.we_vote_id] = candidate
                            possible_endorsement, status2 = attach_candidate_fields_to_possible_endorsement(
                                candidate, possible_endorsement, attach_objects)
                            # status += status2
                        else:
                            status += "MISSING_WE_VOTE_ID_FOR_CANDIDATE15 "
                    possible_endorsement_count += 1
                    possible_endorsement_return_list.append(possible_endorsement)
                    possible_endorsement_matched = True
                    if is_organization_endorsing_candidates:
                        already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                            possible_endorsement,
                            already_found_we_vote_id_list_local,
                            is_organization_endorsing_candidates)
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

                        already_in_list = already_in_list_test(
                            possible_endorsement, already_found_we_vote_id_list_local,
                            is_organization_endorsing_candidates)
                        if is_organization_endorsing_candidates and already_in_list:
                            status += "ALREADY_IN_LIST16 "
                        else:
                            # Make a copy, so we don't change the incoming object -- if we find multiple upcoming
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
                                if hasattr(candidate, 'we_vote_id') and positive_value_exists(candidate.we_vote_id):
                                    candidates_dict[candidate.we_vote_id] = candidate
                                    possible_endorsement, status2 = attach_candidate_fields_to_possible_endorsement(
                                        candidate, possible_endorsement, attach_objects)
                                    # status += status2
                                else:
                                    status += "MISSING_WE_VOTE_ID_FOR_CANDIDATE16 "

                            synonym_found = True
                            possible_endorsement_count += 1
                            possible_endorsement_return_list.append(possible_endorsement_copy)
                            if is_organization_endorsing_candidates:
                                already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                                    possible_endorsement,
                                    already_found_we_vote_id_list_local,
                                    is_organization_endorsing_candidates)
                            break

        if not synonym_found:
            already_in_list = already_in_list_test(
                possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
            if is_organization_endorsing_candidates and already_in_list:
                status += "ALREADY_IN_LIST17 "
            else:
                # If an entry based on a synonym wasn't found, then store the original possibility
                possible_endorsement_count += 1
                possible_endorsement_return_list.append(possible_endorsement)
                if is_organization_endorsing_candidates:
                    already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                        possible_endorsement,
                        already_found_we_vote_id_list_local,
                        is_organization_endorsing_candidates)

    # Finally, if the possible_endorsement wasn't matched to any existing records, we still want to use it
    if possible_endorsement_matched and not positive_value_exists(possible_endorsement_count):
        already_in_list = already_in_list_test(
            possible_endorsement, already_found_we_vote_id_list_local, is_organization_endorsing_candidates)
        if is_organization_endorsing_candidates and already_in_list:
            status += "ALREADY_IN_LIST18 "
        else:
            # If an entry based on a synonym wasn't found, then store the original possibility
            possible_endorsement_count += 1
            possible_endorsement_return_list.append(possible_endorsement)
            if is_organization_endorsing_candidates:
                already_found_we_vote_id_list_local = unique_add_to_already_found_list(
                    possible_endorsement,
                    already_found_we_vote_id_list_local,
                    is_organization_endorsing_candidates)

    results = {
        'already_found_we_vote_id_list':        already_found_we_vote_id_list_local,
        'candidates_dict':                      candidates_dict,
        'possible_endorsement_count':           possible_endorsement_count,
        'possible_endorsement_return_list':     possible_endorsement_return_list,
        'status':                               status,
        'success':                              success,
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
