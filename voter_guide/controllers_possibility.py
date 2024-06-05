# voter_guide/controllers_possibility.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import copy
from django.utils.timezone import localtime, now
from config.base import get_environment_variable
from candidate.controllers import find_candidate_endorsements_on_one_candidate_web_page, \
    find_organization_endorsements_of_candidates_on_one_web_page, \
    retrieve_candidate_list_for_all_upcoming_elections
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager
from election.controllers import retrieve_this_and_next_years_election_id_list
from import_export_twitter.controllers import refresh_twitter_organization_details, scrape_social_media_from_one_site
from organization.controllers import retrieve_organization_list_for_all_upcoming_elections
from organization.models import OrganizationListManager, OrganizationManager, GROUP
from measure.controllers import add_measure_name_alternatives_to_measure_list_light, \
    retrieve_measure_list_for_all_upcoming_elections
from measure.models import ContestMeasureListManager, ContestMeasureManager
from position.models import PositionEntered
from twitter.models import TwitterUserManager
from volunteer_task.models import VOLUNTEER_ACTION_CANDIDATE_CREATED, VolunteerTaskManager
from voter.models import fetch_voter_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_facebook_username_from_text_string, \
    extract_twitter_handle_from_text_string, extract_website_from_url, positive_value_exists, \
    STATE_CODE_MAP, get_voter_device_id, get_voter_api_device_id
from wevote_functions.functions_date import convert_date_to_we_vote_date_string
from .controllers_possibility_shared import fix_sequence_of_possible_endorsement_list

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut


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
            'ballot_item_state_code': "",
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


def augment_organization_possible_position_data(possible_endorsement, attach_objects=True):
    status = ""
    success = True

    organization_manager = OrganizationManager()
    organization_list_manager = OrganizationListManager()

    possible_endorsement_return_list = []
    possible_endorsement_count = 0
    if 'organization_we_vote_id' in possible_endorsement \
            and positive_value_exists(possible_endorsement['organization_we_vote_id']):
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
    elif 'organization_name' in possible_endorsement and \
            positive_value_exists(possible_endorsement['organization_name']):
        # If here search for possible organization matches
        results = organization_list_manager.retrieve_organizations_from_organization_name(
            organization_name=possible_endorsement['organization_name'])
        if results['organization_found']:
            organization = results['organization']
            if positive_value_exists(attach_objects):
                possible_endorsement['organization'] = organization
            possible_endorsement['organization_name'] = organization.organization_name
            possible_endorsement['organization_twitter_handle'] = organization.organization_twitter_handle
            possible_endorsement['organization_we_vote_id'] = organization.we_vote_id
            possible_endorsement['organization_website'] = organization.organization_website
            possible_endorsement['we_vote_hosted_profile_image_url_large'] = \
                organization.we_vote_hosted_profile_image_url_large
            possible_endorsement['we_vote_hosted_profile_image_url_medium'] = \
                organization.we_vote_hosted_profile_image_url_medium
            possible_endorsement['we_vote_hosted_profile_image_url_tiny'] = \
                organization.we_vote_hosted_profile_image_url_tiny

            possible_endorsement_return_list.append(possible_endorsement)
            possible_endorsement_count += 1
        elif results['organization_list_found']:
            organization_list = results['organization_list']
            first_in_list = True
            for organization in organization_list:
                if first_in_list:
                    first_in_list = False
                else:
                    possible_endorsement = copy.deepcopy(possible_endorsement)
                if positive_value_exists(attach_objects):
                    possible_endorsement['organization'] = organization
                possible_endorsement['organization_name'] = organization.organization_name
                possible_endorsement['organization_twitter_handle'] = organization.organization_twitter_handle
                possible_endorsement['organization_website'] = organization.organization_website
                possible_endorsement['organization_we_vote_id'] = organization.we_vote_id
                possible_endorsement['we_vote_hosted_profile_image_url_large'] = \
                    organization.we_vote_hosted_profile_image_url_large
                possible_endorsement['we_vote_hosted_profile_image_url_medium'] = \
                    organization.we_vote_hosted_profile_image_url_medium
                possible_endorsement['we_vote_hosted_profile_image_url_tiny'] = \
                    organization.we_vote_hosted_profile_image_url_tiny

                possible_endorsement_return_list.append(possible_endorsement)
                possible_endorsement_count += 1

    results = {
        'status':                           status,
        'success':                          success,
        'possible_endorsement_return_list': possible_endorsement_return_list,
        'possible_endorsement_count':       possible_endorsement_count,
    }
    return results


def break_up_text_into_possible_endorsement_list(ballot_items, starting_endorsement_number=1,
                                                 incoming_text_organization_names=False,
                                                 candidate_we_vote_id_to_include='',
                                                 organization_we_vote_id_to_include=''):
    names_list = []
    # Break up multiple lines
    ballot_items_list = ballot_items.splitlines()
    for one_line in ballot_items_list:
        one_line_stripped = one_line.strip()
        if positive_value_exists(one_line_stripped):
            names_list.append(one_line_stripped)

    possible_endorsement_list_results = \
        convert_list_of_names_to_possible_endorsement_list(
            names_list, starting_endorsement_number, incoming_text_organization_names,
            candidate_we_vote_id_to_include=candidate_we_vote_id_to_include,
            organization_we_vote_id_to_include=organization_we_vote_id_to_include,
        )

    results = {
        'status': possible_endorsement_list_results['status'],
        'success': possible_endorsement_list_results['success'],
        'possible_endorsement_list': possible_endorsement_list_results['possible_endorsement_list'],
        'possible_endorsement_list_found': possible_endorsement_list_results['possible_endorsement_list_found'],
    }
    return results


def candidates_found_on_url(url_to_scan, google_civic_election_id_list=[], state_code=''):
    status = ""
    success = True
    candidate_list_manager = CandidateListManager()

    facebook_page_list = []
    twitter_or_facebook_found = False
    twitter_handle_list = []
    twitter_handle_list_modified = []
    owner_of_website_candidate_list = []
    owner_of_website_candidate_list_count = 0

    retrieve_list = True
    scrape_results = scrape_social_media_from_one_site(url_to_scan, retrieve_list)

    # Only include a change if we have a new value (do not try to save blank value)
    if scrape_results['twitter_handle_found'] and positive_value_exists(scrape_results['twitter_handle']):
        twitter_handle_list = scrape_results['twitter_handle_list']
        twitter_or_facebook_found = True

    if scrape_results['facebook_page_found'] and positive_value_exists(scrape_results['facebook_page']):
        facebook_page_list = scrape_results['facebook_page_list']
        twitter_or_facebook_found = True

    if twitter_or_facebook_found:
        # Search for candidates that match (by Twitter Handle)
        for one_twitter_handle in twitter_handle_list:
            if positive_value_exists(one_twitter_handle):
                one_twitter_handle = one_twitter_handle.strip()
            if positive_value_exists(one_twitter_handle):
                twitter_handle_lower = one_twitter_handle.lower()
                twitter_handle_lower = extract_twitter_handle_from_text_string(twitter_handle_lower)
                if twitter_handle_lower not in twitter_handle_list_modified:
                    twitter_handle_list_modified.append(twitter_handle_lower)

        # Search for organizations that match (by Facebook page)
        facebook_page_list_modified = []
        for one_facebook_page in facebook_page_list:
            if positive_value_exists(one_facebook_page):
                one_facebook_page = one_facebook_page.strip()
            if positive_value_exists(one_facebook_page):
                one_facebook_page_lower = one_facebook_page.lower()
                one_facebook_page_lower = extract_facebook_username_from_text_string(one_facebook_page_lower)
                if one_facebook_page_lower not in facebook_page_list_modified:
                    facebook_page_list_modified.append(one_facebook_page_lower)

        voter_guide_website = extract_website_from_url(url_to_scan)
        results = candidate_list_manager.search_candidates_in_specific_elections(
            google_civic_election_id_list=google_civic_election_id_list,
            candidate_website=voter_guide_website,
            facebook_page_list=facebook_page_list_modified,
            state_code=state_code,
            twitter_handle_list=twitter_handle_list_modified
        )
        if results['candidate_list_found']:
            owner_of_website_candidate_list = results['candidate_list']
            owner_of_website_candidate_list_count = len(owner_of_website_candidate_list)

    results = {
        'status':           status,
        'success':          success,
        'candidate_list':   owner_of_website_candidate_list,
        'candidate_count':  owner_of_website_candidate_list_count,
    }
    return results


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
        google_civic_election_id = one_endorsement['google_civic_election_id'] \
            if 'google_civic_election_id' in one_endorsement else ''
        if 'ballot_item_state_code' in one_endorsement:
            ballot_item_state_code = one_endorsement['ballot_item_state_code']
        elif 'state_code' in one_endorsement:
            ballot_item_state_code = one_endorsement['state_code']
        else:
            ballot_item_state_code = ''
        possible_endorsement = {
            'ballot_item_name': one_endorsement['ballot_item_display_name'],
            'ballot_item_state_code': ballot_item_state_code,
            'candidate_we_vote_id': one_endorsement['candidate_we_vote_id'],
            'google_civic_election_id': google_civic_election_id,
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
        'possible_endorsement_list':        possible_endorsement_list,
        'possible_endorsement_list_found':  possible_endorsement_list_found,
    }
    return results


def convert_list_of_names_to_possible_endorsement_list(ballot_items_list, starting_endorsement_number=1,
                                                       incoming_text_organization_names=False,
                                                       candidate_we_vote_id_to_include='',
                                                       organization_we_vote_id_to_include=''):
    status = ""
    success = True
    possible_endorsement_list = []
    possible_endorsement_list_found = False

    number_index = starting_endorsement_number
    for one_name in ballot_items_list:
        if not positive_value_exists(one_name):
            continue
        possible_endorsement = {
            'ballot_item_name': '' if incoming_text_organization_names else one_name,
            'candidate_we_vote_id': candidate_we_vote_id_to_include,
            'statement_text': "",
            'google_civic_election_id': 0,
            'measure_we_vote_id': "",
            'more_info_url': "",
            'organization_name':  one_name if incoming_text_organization_names else '',
            'organization_we_vote_id': organization_we_vote_id_to_include,
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


def match_endorsement_list_with_candidates_in_database(
        possible_endorsement_list=[],
        google_civic_election_id_list=[],
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
        from voter_guide.controllers_possibility_shared import \
            augment_candidate_possible_position_data
        results = augment_candidate_possible_position_data(
            possible_endorsement,
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=state_code,
            all_possible_candidates=all_possible_candidates_list_light,
            attach_objects=attach_objects)
        if results['possible_endorsement_count'] > 0:
            possible_endorsement_list_modified += results['possible_endorsement_return_list']
        else:
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
    measure_list_manager = ContestMeasureListManager()

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
        elif 'candidate_we_vote_id' in possible_endorsement \
                and positive_value_exists(possible_endorsement['candidate_we_vote_id']):
            possible_endorsement_matched = True
            possible_endorsement_list_modified.append(possible_endorsement)
            # Go to the next entry in this possible_endorsement_list loop
            continue
        elif 'ballot_item_name' in possible_endorsement and \
                positive_value_exists(possible_endorsement['ballot_item_name']):
            # If here search for possible measure matches
            matching_results = measure_list_manager.retrieve_contest_measures_from_non_unique_identifiers(
                google_civic_election_id_list, state_code, possible_endorsement['ballot_item_name'])

            if matching_results['contest_measure_found']:
                measure = matching_results['contest_measure']

                # If one measure found, add we_vote_id here
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


def match_endorsement_list_with_organizations_in_database(possible_endorsement_list, attach_objects=True):
    """

    :param possible_endorsement_list:
    :param attach_objects:
    :return:
    """
    status = ""
    success = True
    possible_endorsement_list_found = False

    possible_endorsement_list_modified = []
    for possible_endorsement in possible_endorsement_list:
        results = augment_organization_possible_position_data(
            possible_endorsement, attach_objects=attach_objects)
        if results['possible_endorsement_count'] > 0:
            possible_endorsement_list_modified += results['possible_endorsement_return_list']
        else:
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


def organizations_found_on_url(url_to_scan, state_code=''):
    status = ""
    success = True
    organization_list_manager = OrganizationListManager()
    organization_manager = OrganizationManager()
    organization_list = []
    organization_count = 0
    twitter_user_manager = TwitterUserManager()

    facebook_page_list = []
    twitter_or_facebook_found = False
    twitter_handle_list = []

    retrieve_list = True
    scrape_results = scrape_social_media_from_one_site(url_to_scan, retrieve_list)

    # Only include a change if we have a new value (do not try to save blank value)
    if scrape_results['twitter_handle_found'] and positive_value_exists(scrape_results['twitter_handle']):
        twitter_handle_list = scrape_results['twitter_handle_list']
        twitter_or_facebook_found = True

    if scrape_results['facebook_page_found'] and positive_value_exists(scrape_results['facebook_page']):
        facebook_page_list = scrape_results['facebook_page_list']
        twitter_or_facebook_found = True

    if twitter_or_facebook_found:
        # Search for organizations that match (by Twitter Handle)
        twitter_handle_list_modified = []
        for one_twitter_handle in twitter_handle_list:
            if positive_value_exists(one_twitter_handle):
                one_twitter_handle = one_twitter_handle.strip()
            if positive_value_exists(one_twitter_handle):
                twitter_handle_lower = one_twitter_handle.lower()
                twitter_handle_lower = extract_twitter_handle_from_text_string(twitter_handle_lower)
                if twitter_handle_lower not in twitter_handle_list_modified:
                    twitter_handle_list_modified.append(twitter_handle_lower)

        # Search for organizations that match (by Facebook page)
        facebook_page_list_modified = []
        for one_facebook_page in facebook_page_list:
            if positive_value_exists(one_facebook_page):
                one_facebook_page = one_facebook_page.strip()
            if positive_value_exists(one_facebook_page):
                one_facebook_page_lower = one_facebook_page.lower()
                one_facebook_page_lower = extract_facebook_username_from_text_string(one_facebook_page_lower)
                if one_facebook_page_lower not in facebook_page_list_modified:
                    facebook_page_list_modified.append(one_facebook_page_lower)

        # We want to create an organization for each Twitter handle we find on the page so it can be chosen below
        for one_twitter_handle in twitter_handle_list_modified:
            one_organization_found = False
            results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                one_twitter_handle)
            if 'twitter_link_to_organization_found' in results and results['twitter_link_to_organization_found']:
                twitter_link_to_organization = results['twitter_link_to_organization']
                organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    twitter_link_to_organization.organization_we_vote_id)
                if organization_results['organization_found']:
                    one_organization_found = True
            twitter_user_id = 0
            twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                twitter_user_id, one_twitter_handle)
            if twitter_results['twitter_user_found']:
                twitter_user = twitter_results['twitter_user']
                twitter_user_id = twitter_user.twitter_id
            if not one_organization_found and positive_value_exists(twitter_user_id):
                organization_name = ""
                if not positive_value_exists(state_code):
                    state_code = None
                create_results = organization_manager.create_organization(
                    organization_name=organization_name,
                    organization_type=GROUP,
                    organization_twitter_handle=one_twitter_handle,
                    state_served_code=state_code)
                if create_results['organization_created']:
                    one_organization = create_results['organization']

                    # Create TwitterLinkToOrganization
                    link_results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_user_id, one_organization.we_vote_id)
                    # Refresh the organization with the Twitter details
                    refresh_twitter_organization_details(one_organization)

        voter_guide_website = extract_website_from_url(url_to_scan)
        results = organization_list_manager.organization_search_find_any_possibilities(
            organization_website=voter_guide_website,
            facebook_page_list=facebook_page_list_modified,
            twitter_handle_list=twitter_handle_list_modified
        )

        if results['organizations_found']:
            organization_list = results['organizations_list']
            organization_count = len(organization_list)

    results = {
        'status':               status,
        'success':              success,
        'organization_list':    organization_list,
        'organization_count':   organization_count,
    }
    return results


def process_organization_endorsing_candidates_input_form(
        request=None,
        organization_name=None,
        organization_twitter_handle=None,
        organization_we_vote_id=None,
        possible_endorsement_list=None,
        voter_guide_possibility_url=None,
):
    ballot_items_raw = request.POST.get('ballot_items_raw', "")
    ballot_items_additional = request.POST.get('ballot_items_additional', "")
    ignore_stored_positions = request.GET.get('ignore_stored_positions', False)
    organization_found = False
    organization_manager = OrganizationManager()
    organization_twitter_followers_count = 0
    possible_endorsement_list_found = False
    scan_url_again = request.POST.get('scan_url_again', False)
    state_code = request.POST.get('state_code', '')
    status = ""
    success = True
    twitter_user_manager = TwitterUserManager()
    volunteer_task_manager = VolunteerTaskManager()
    voter_device_id = get_voter_api_device_id(request)
    voter = fetch_voter_from_voter_device_link(voter_device_id)
    if hasattr(voter, 'we_vote_id'):
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    # First, identify the organization that is the subject of the page we are analyzing
    if positive_value_exists(organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if results['organization_found']:
            organization = results['organization']
            organization_found = True
            organization_name = organization.organization_name
            organization_twitter_handle = twitter_user_manager.fetch_twitter_handle_from_organization_we_vote_id(
                organization_we_vote_id)
            organization_twitter_followers_count = organization.twitter_followers_count

    if not positive_value_exists(organization_found):
        one_organization_found = False
        if positive_value_exists(organization_twitter_handle):
            results = organization_manager.retrieve_organization_from_twitter_handle(organization_twitter_handle)
            if results['organization_found']:
                organization = results['organization']
                organization_found = True
                organization_name = organization.organization_name
                organization_twitter_followers_count = organization.twitter_followers_count
                organization_we_vote_id = organization.we_vote_id
            if not positive_value_exists(organization_found):
                results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                    organization_twitter_handle)
                if results['twitter_link_to_organization_found']:
                    twitter_link_to_organization = results['twitter_link_to_organization']
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        twitter_link_to_organization.organization_we_vote_id)
                    if organization_results['organization_found']:
                        one_organization_found = True
                        organization = organization_results['organization']
                        organization_name = organization.organization_name
                        organization_twitter_followers_count = organization.twitter_followers_count
                        organization_we_vote_id = organization.we_vote_id
                twitter_user_id = 0
                twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                    twitter_user_id, organization_twitter_handle)
                if twitter_results['twitter_user_found']:
                    twitter_user = twitter_results['twitter_user']
                    if positive_value_exists(twitter_user.twitter_name):
                        organization_name = twitter_user.twitter_name
                    twitter_user_id = twitter_user.twitter_id
                if not one_organization_found and positive_value_exists(twitter_user_id):
                    # organization_name = ""
                    if not positive_value_exists(state_code):
                        state_code = None
                    create_results = organization_manager.create_organization(
                        organization_name=organization_name,
                        organization_type=GROUP,
                        organization_twitter_handle=organization_twitter_handle,
                        state_served_code=state_code)
                    if create_results['organization_created']:
                        one_organization_found = True
                        organization = create_results['organization']
                        organization_name = organization.organization_name
                        organization_we_vote_id = organization.we_vote_id

                        # Create TwitterLinkToOrganization
                        link_results = twitter_user_manager.create_twitter_link_to_organization(
                            twitter_user_id, organization.we_vote_id)
                        # Refresh the organization with the Twitter details
                        refresh_twitter_organization_details(organization)

    # #########################################
    # Figure out the Possible Candidates or Measures from one organization's perspective
    possible_endorsement_list_from_form = []
    possible_endorsement_list_results = take_in_possible_endorsement_list_from_form(request)
    if possible_endorsement_list_results['possible_endorsement_list_found']:
        possible_endorsement_list_from_form = possible_endorsement_list_results['possible_endorsement_list']
        possible_endorsement_list_found = True

    possible_endorsement_list = possible_endorsement_list + possible_endorsement_list_from_form
    results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
    if results['possible_endorsement_list_found']:
        possible_endorsement_list = results['possible_endorsement_list']

    # We will need all candidates for all upcoming elections, so we can search the HTML of
    #  the possible voter guide for these names
    all_possible_candidates_list_light_found = False
    all_possible_candidates_list_light = []
    # today = datetime.now().date()
    # candidate_year = today.year
    # results = retrieve_candidate_list_for_entire_year(
    #     candidate_year=candidate_year,
    #     limit_to_this_state_code=state_code,
    # )
    # if results['candidate_list_found']:
    #     all_possible_candidates_list_light_found = True
    #     all_possible_candidates_list_light = results['candidate_list_light']
    results = retrieve_candidate_list_for_all_upcoming_elections()
    if results['candidate_list_found']:
        all_possible_candidates_list_light_found = True
        all_possible_candidates_list_light = results['candidate_list_light']

    # We need all measures for all upcoming elections
    all_possible_measures_list_light_found = False
    all_possible_measures_list_light = []

    # Figure out the elections we care about
    google_civic_election_id_list_this_year = retrieve_this_and_next_years_election_id_list()
    if positive_value_exists(google_civic_election_id_list_this_year):
        # TODO: Add "shortened_identifier" to the model and this retrieve
        results = retrieve_measure_list_for_all_upcoming_elections(
            google_civic_election_id_list=google_civic_election_id_list_this_year,
            limit_to_this_state_code=state_code)
        if results['measure_list_found']:
            all_possible_measures_list_light_found = True
            all_possible_measures_list_light = results['measure_list_light']

            expand_results = add_measure_name_alternatives_to_measure_list_light(all_possible_measures_list_light)
            if expand_results['success']:
                all_possible_measures_list_light = expand_results['measure_list_light']

    ballot_item_list_light = all_possible_candidates_list_light + all_possible_measures_list_light

    possible_endorsement_list_from_url_scan = []
    first_scan_needed = positive_value_exists(voter_guide_possibility_url) and not possible_endorsement_list_found
    scan_url_now = first_scan_needed or positive_value_exists(scan_url_again)
    possibilities_found = all_possible_candidates_list_light_found or all_possible_measures_list_light_found
    if scan_url_now and possibilities_found:
        endorsement_scrape_results = find_organization_endorsements_of_candidates_on_one_web_page(
            voter_guide_possibility_url, ballot_item_list_light)
        if endorsement_scrape_results['at_least_one_endorsement_found']:
            endorsement_list_light = endorsement_scrape_results['endorsement_list_light']

            # Remove the candidates or measures from endorsement_list_light we have in possible_endorsement_list
            endorsement_list_light_updated = []
            for one_endorsement_light in endorsement_list_light:
                one_endorsement_light_is_unique = True
                for one_possible_endorsement in possible_endorsement_list:
                    if positive_value_exists(one_endorsement_light['candidate_we_vote_id']) \
                            and one_endorsement_light['candidate_we_vote_id'] == \
                            one_possible_endorsement['candidate_we_vote_id']:
                        one_endorsement_light_is_unique = False
                        break
                    elif positive_value_exists(one_endorsement_light['measure_we_vote_id']) \
                            and one_endorsement_light['measure_we_vote_id'] == \
                            one_possible_endorsement['measure_we_vote_id']:
                        one_endorsement_light_is_unique = False
                        break
                if one_endorsement_light_is_unique:
                    endorsement_list_light_updated.append(one_endorsement_light)

            possible_endorsement_list_results = \
                convert_candidate_endorsement_list_light_to_possible_endorsement_list(
                    endorsement_list_light_updated)
            if possible_endorsement_list_results['possible_endorsement_list_found']:
                possible_endorsement_list_from_url_scan = \
                    possible_endorsement_list_results['possible_endorsement_list']
                possible_endorsement_list_found = True

    possible_endorsement_list = possible_endorsement_list + possible_endorsement_list_from_url_scan
    results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
    if results['possible_endorsement_list_found']:
        possible_endorsement_list = results['possible_endorsement_list']

    # If we don't already have a list of possible endorsements, check the raw text entry field
    # For subsequent passes, we use ballot_items_additional
    possible_endorsement_list_from_ballot_items_raw = []
    if not possible_endorsement_list_found and positive_value_exists(ballot_items_raw):
        results = break_up_text_into_possible_endorsement_list(
            ballot_items_raw, organization_we_vote_id_to_include=organization_we_vote_id)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list_from_ballot_items_raw = results['possible_endorsement_list']
            # possible_endorsement_list_found = True
            changes_made = True
        possible_endorsement_list = possible_endorsement_list + possible_endorsement_list_from_ballot_items_raw
        results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

    remove_possibility_position_id = request.POST.get('remove_possibility_position_id', 0)

    if positive_value_exists(remove_possibility_position_id):
        results = modify_one_row_in_possible_endorsement_list(
            possible_endorsement_list, remove_possibility_position_id)
        if positive_value_exists(results['success']):
            possible_endorsement_list = results['possible_endorsement_list']

    for remove_possibility_position_id in request.POST.getlist('remove_possibility_position_ids'):
        results = modify_one_row_in_possible_endorsement_list(
            possible_endorsement_list, remove_possibility_position_id)
        if positive_value_exists(results['success']):
            possible_endorsement_list = results['possible_endorsement_list']

    # Check for additional items to add (For the first pass, we use ballot_items_raw)
    if positive_value_exists(ballot_items_additional):
        number_of_current_possible_endorsements = len(possible_endorsement_list)
        try:
            starting_possibility_number = number_of_current_possible_endorsements + 1
            results = break_up_text_into_possible_endorsement_list(
                ballot_items_additional, starting_possibility_number,
                organization_we_vote_id_to_include=organization_we_vote_id)
            if results['possible_endorsement_list_found']:
                additional_possible_endorsement_list = results['possible_endorsement_list']
                possible_endorsement_list = possible_endorsement_list + additional_possible_endorsement_list
                results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                changes_made = True
        except Exception as e:
            # If there is a problem, continue
            pass

    # Match incoming endorsements to candidates already in the database AND look for new matches
    if len(possible_endorsement_list):
        # Match possible_endorsement_list to candidates already in the database
        results = match_endorsement_list_with_candidates_in_database(
            possible_endorsement_list,
            google_civic_election_id_list=google_civic_election_id_list_this_year,
            all_possible_candidates_list_light=all_possible_candidates_list_light)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

        results = match_endorsement_list_with_measures_in_database(
            possible_endorsement_list, google_civic_election_id_list_this_year,
            all_possible_measures_list_light=all_possible_measures_list_light)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

        results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

    # Now look for candidate possibilities that have states attached so we can add them to the database
    if len(possible_endorsement_list):
        try:
            datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
            current_year = convert_to_int(datetime_now.year)
        except Exception as e:
            status += "FAILED_TO_GET_CURRENT_YEAR: " + str(e) + " "
            current_year = 2024
        adjusted_possible_endorsement_list = []
        for one_possible_endorsement in possible_endorsement_list:
            if 'candidate_we_vote_id' in one_possible_endorsement \
                    and positive_value_exists(one_possible_endorsement['candidate_we_vote_id']):
                adjusted_possible_endorsement_list.append(one_possible_endorsement)
                continue
            elif 'measure_we_vote_id' in one_possible_endorsement \
                    and positive_value_exists(one_possible_endorsement['measure_we_vote_id']):
                adjusted_possible_endorsement_list.append(one_possible_endorsement)
                continue
            ballot_item_name = one_possible_endorsement['ballot_item_name'] \
                if 'ballot_item_name' in one_possible_endorsement \
                and positive_value_exists(one_possible_endorsement['ballot_item_name']) else ''
            ballot_item_state_code = one_possible_endorsement['ballot_item_state_code'] \
                if 'ballot_item_state_code' in one_possible_endorsement \
                and positive_value_exists(one_possible_endorsement['ballot_item_state_code']) else ''
            # Note: We currently assume this is a candidate (as opposed to a measure)
            new_candidate_created = False
            if positive_value_exists(ballot_item_name) and positive_value_exists(ballot_item_state_code):
                try:
                    candidate_on_stage, new_candidate_created = CandidateCampaign.objects.update_or_create(
                        candidate_name=ballot_item_name,
                        candidate_year=current_year,
                        google_civic_candidate_name=ballot_item_name,
                        state_code=ballot_item_state_code,
                    )
                    if new_candidate_created:
                        status += "NEW_CANDIDATE_CAMPAIGN_CREATED "
                    else:
                        status += "CANDIDATE_CAMPAIGN_UPDATED "
                    if positive_value_exists(candidate_on_stage.we_vote_id):
                        one_possible_endorsement['candidate_we_vote_id'] = candidate_on_stage.we_vote_id
                except Exception as e:
                    status += 'FAILED_TO_CREATE_CANDIDATE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            adjusted_possible_endorsement_list.append(one_possible_endorsement)
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
        possible_endorsement_list = adjusted_possible_endorsement_list

    if positive_value_exists(ignore_stored_positions):
        # Identify which candidates already have positions stored, and remove them
        altered_position_list = []
        altered_position_list_used = False
        if positive_value_exists(organization_we_vote_id):
            for one_possible_endorsement in possible_endorsement_list:
                does_not_contain_position = True
                if 'candidate_we_vote_id' in one_possible_endorsement \
                        and positive_value_exists(one_possible_endorsement['candidate_we_vote_id']):
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=organization_we_vote_id,
                        candidate_campaign_we_vote_id=one_possible_endorsement['candidate_we_vote_id'])
                    position_count = position_exists_query.count()
                    if positive_value_exists(position_count):
                        # Since there is a position, remove this possible candidate
                        altered_position_list_used = True
                        does_not_contain_position = False
                        pass
                if 'measure_we_vote_id' in one_possible_endorsement \
                        and positive_value_exists(one_possible_endorsement['measure_we_vote_id']):
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=organization_we_vote_id,
                        contest_measure_we_vote_id=one_possible_endorsement['measure_we_vote_id'])
                    position_count = position_exists_query.count()
                    if positive_value_exists(position_count):
                        # Since there is a position, remove this possible measure
                        altered_position_list_used = True
                        does_not_contain_position = False
                        pass

                if does_not_contain_position:
                    altered_position_list.append(one_possible_endorsement)

        if altered_position_list_used:
            results = fix_sequence_of_possible_endorsement_list(altered_position_list)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']
    results = {
        'status':                               status,
        'success':                              success,
        'organization_name':                    organization_name,
        'organization_twitter_handle':          organization_twitter_handle,
        'organization_twitter_followers_count': organization_twitter_followers_count,
        'possible_endorsement_list':            possible_endorsement_list,
    }
    return results


def process_candidate_being_endorsed_input_form(
        request=None,
        candidate_name=None,
        candidate_twitter_handle=None,
        candidate_we_vote_id=None,
        possible_endorsement_list=None,
        voter_guide_possibility_url=None,
):
    ballot_items_raw = request.POST.get('ballot_items_raw', "")
    ballot_items_additional = request.POST.get('ballot_items_additional', "")
    ignore_stored_positions = request.GET.get('ignore_stored_positions', False)
    candidate_found = False
    candidate_manager = CandidateManager()
    candidate_list_manager = CandidateListManager()
    messages_info_to_display = ""
    possible_endorsement_list_found = False
    possible_endorsement_list = possible_endorsement_list if isinstance(possible_endorsement_list, list) else []
    scan_url_again = request.POST.get('scan_url_again', False)
    state_code = request.POST.get('state_code', '')
    status = ""
    success = True
    # First, identify the candidate that is the subject of the page we are analyzing
    if positive_value_exists(candidate_we_vote_id):
        results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        if results['candidate_found']:
            candidate = results['candidate']
            candidate_found = True
            candidate_name = candidate.display_candidate_name()
            candidate_twitter_handle = candidate.candidate_twitter_handle
    # Figure out the elections we care about
    google_civic_election_id_list_this_year = retrieve_this_and_next_years_election_id_list()
    if not positive_value_exists(candidate_found):
        if positive_value_exists(candidate_twitter_handle) or positive_value_exists(candidate_name):
            results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
                google_civic_election_id_list=google_civic_election_id_list_this_year,
                state_code=state_code,
                candidate_twitter_handle=candidate_twitter_handle,
                candidate_name=candidate_name,
                read_only=True)
            if results['candidate_found']:
                candidate = results['candidate']
                candidate_found = True
                candidate_name = candidate.display_candidate_name()
                candidate_we_vote_id = candidate.we_vote_id
            elif results['candidate_list_found']:
                pass
            else:
                messages_info_to_display = "Candidate (owner of this webpage) not found based on "
                if positive_value_exists(candidate_name):
                    messages_info_to_display += "candidate_name: " + candidate_name + " "
                if positive_value_exists(candidate_twitter_handle):
                    messages_info_to_display += "candidate_twitter_handle: " + candidate_twitter_handle + " "
                messages_info_to_display += \
                    ("Please make sure a Candidate entry for this person exists and then try again. "
                     "NOTE: It could be a first name mismatch--consider added a 'Candidate Alt Name' if Candidate "
                     "entry already exists. ")

    # #########################################
    # Figure out the Possible Endorsers from one candidate's perspective
    possible_endorsement_list_from_form = []
    possible_endorsement_list_results = take_in_possible_endorsement_list_from_form(request)
    if possible_endorsement_list_results['possible_endorsement_list_found']:
        possible_endorsement_list_from_form = possible_endorsement_list_results['possible_endorsement_list']
        possible_endorsement_list_found = True

    possible_endorsement_list = possible_endorsement_list + possible_endorsement_list_from_form
    results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
    if results['possible_endorsement_list_found']:
        possible_endorsement_list = results['possible_endorsement_list']

    # We will need all organizations so we can search the HTML of the possible voter guide for these names
    possible_endorsement_list_from_url_scan = []
    all_possible_organizations_list_light_found = False
    all_possible_organizations_list_light = []
    # We pass in the candidate_we_vote_id so that the possible_position data package includes that from the start
    # DALE 2024 June 5: explore this candidate_we_vote_id_to_include code -- we may need instead an "exclude"
    #  to prevent the candidate we are collecting endorsements for, from being shown on their own endorsements page
    results = retrieve_organization_list_for_all_upcoming_elections(
        limit_to_this_state_code=state_code, candidate_we_vote_id_to_include=candidate_we_vote_id)
    if results['organization_list_found']:
        all_possible_organizations_list_light_found = True
        all_possible_organizations_list_light = results['organization_list_light']

    first_scan_needed = positive_value_exists(voter_guide_possibility_url) and not possible_endorsement_list_found
    scan_url_now = first_scan_needed or positive_value_exists(scan_url_again)
    if scan_url_now and all_possible_organizations_list_light_found:
        endorsement_scrape_results = find_candidate_endorsements_on_one_candidate_web_page(
            voter_guide_possibility_url, all_possible_organizations_list_light)
        if endorsement_scrape_results['at_least_one_endorsement_found']:
            organization_list_light = endorsement_scrape_results['endorsement_list_light']

            # Remove the organizations from organization_list_light we have in possible_endorsement_list
            organization_list_light_updated = []
            for one_organization_light in organization_list_light:
                one_organization_light_is_unique = True
                for one_possible_endorsement in possible_endorsement_list:
                    if positive_value_exists(one_organization_light['organization_we_vote_id']) \
                            and one_organization_light['organization_we_vote_id'] == \
                            one_possible_endorsement['organization_we_vote_id']:
                        one_organization_light_is_unique = False
                        break
                if one_organization_light_is_unique:
                    organization_list_light_updated.append(one_organization_light)

            possible_endorsement_list_results = \
                convert_organization_endorsement_list_light_to_possible_endorsement_list(
                    organization_list_light_updated)
            if possible_endorsement_list_results['possible_endorsement_list_found']:
                possible_endorsement_list_from_url_scan = \
                    possible_endorsement_list_results['possible_endorsement_list']
                possible_endorsement_list_found = True

    possible_endorsement_list = possible_endorsement_list + possible_endorsement_list_from_url_scan
    results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
    if results['possible_endorsement_list_found']:
        possible_endorsement_list = results['possible_endorsement_list']

    # If we don't already have a list of possible endorsements, check the raw text entry field
    # For subsequent passes, we use ballot_items_additional
    possible_endorsement_list_from_ballot_items_raw = []
    if not possible_endorsement_list_found and positive_value_exists(ballot_items_raw):
        results = break_up_text_into_possible_endorsement_list(
            ballot_items_raw,
            incoming_text_organization_names=True,
            candidate_we_vote_id_to_include=candidate_we_vote_id)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list_from_ballot_items_raw = results['possible_endorsement_list']
            # possible_endorsement_list_found = True
            changes_made = True
        possible_endorsement_list = possible_endorsement_list + possible_endorsement_list_from_ballot_items_raw
        results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

    remove_possibility_position_id = request.POST.get('remove_possibility_position_id', 0)

    if positive_value_exists(remove_possibility_position_id):
        results = modify_one_row_in_possible_endorsement_list(
            possible_endorsement_list, remove_possibility_position_id)
        if positive_value_exists(results['success']):
            possible_endorsement_list = results['possible_endorsement_list']

    for remove_possibility_position_id in request.POST.getlist('remove_possibility_position_ids'):
        results = modify_one_row_in_possible_endorsement_list(
            possible_endorsement_list, remove_possibility_position_id)
        if positive_value_exists(results['success']):
            possible_endorsement_list = results['possible_endorsement_list']

    # Check for additional items to add (For the first pass, we use ballot_items_raw)
    if positive_value_exists(ballot_items_additional):
        number_of_current_possible_endorsements = len(possible_endorsement_list)
        try:
            starting_possibility_number = number_of_current_possible_endorsements + 1
            results = break_up_text_into_possible_endorsement_list(
                ballot_items_additional, starting_possibility_number,
                incoming_text_organization_names=True,
                candidate_we_vote_id_to_include=candidate_we_vote_id)
            if results['possible_endorsement_list_found']:
                additional_possible_endorsement_list = results['possible_endorsement_list']
                possible_endorsement_list = possible_endorsement_list + additional_possible_endorsement_list
                results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
                if results['possible_endorsement_list_found']:
                    possible_endorsement_list = results['possible_endorsement_list']
                changes_made = True
        except Exception as e:
            # If there is a problem, continue
            pass

    # Match incoming endorsements to candidates already in the database
    # Even though we are organization-focused in this branch, we still want to match
    # additional candidate information
    if len(possible_endorsement_list):
        # Match possible_endorsement_list to candidates already in the database
        results = match_endorsement_list_with_candidates_in_database(
            possible_endorsement_list,
            google_civic_election_id_list=google_civic_election_id_list_this_year)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

        results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

        # Match possible_endorsement_list with organizations in database
        results = match_endorsement_list_with_organizations_in_database(
            possible_endorsement_list, state_code)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

        results = fix_sequence_of_possible_endorsement_list(possible_endorsement_list)
        if results['possible_endorsement_list_found']:
            possible_endorsement_list = results['possible_endorsement_list']

    if positive_value_exists(ignore_stored_positions):
        # Identify which candidates already have positions stored, and remove them
        altered_position_list = []
        altered_position_list_used = False
        if positive_value_exists(candidate_we_vote_id):
            for one_possible_endorsement in possible_endorsement_list:
                does_not_contain_position = True
                if 'organization_we_vote_id' in one_possible_endorsement \
                        and positive_value_exists(one_possible_endorsement['organization_we_vote_id']):
                    position_exists_query = PositionEntered.objects.filter(
                        organization_we_vote_id=one_possible_endorsement['organization_we_vote_id'],
                        candidate_campaign_we_vote_id=candidate_we_vote_id)
                    position_count = position_exists_query.count()
                    if positive_value_exists(position_count):
                        # Since there is a position, remove this possible candidate
                        altered_position_list_used = True
                        does_not_contain_position = False
                        pass

                if does_not_contain_position:
                    altered_position_list.append(one_possible_endorsement)

        if altered_position_list_used:
            results = fix_sequence_of_possible_endorsement_list(altered_position_list)
            if results['possible_endorsement_list_found']:
                possible_endorsement_list = results['possible_endorsement_list']
    results = {
        'status':                               status,
        'success':                              success,
        'candidate_name':                       candidate_name,
        'candidate_twitter_handle':             candidate_twitter_handle,
        'candidate_we_vote_id':                 candidate_we_vote_id,
        'messages_info_to_display':             messages_info_to_display,
        # 'organization_twitter_followers_count': organization_twitter_followers_count,
        'possible_endorsement_list':            possible_endorsement_list,
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
                or (request.POST.get('ballot_item_state_code_' + str(number_index), None) is not None) \
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
                'ballot_item_state_code': request.POST.get('ballot_item_state_code_' + str(number_index), ""),
                'candidate_we_vote_id': request.POST.get('candidate_we_vote_id_' + str(number_index), ""),
                'google_civic_election_id': request.POST.get('google_civic_election_id_' + str(number_index), ""),
                'measure_we_vote_id': request.POST.get('measure_we_vote_id_' + str(number_index), ""),
                'organization_we_vote_id': request.POST.get('organization_we_vote_id_' + str(number_index), ""),
                'more_info_url': request.POST.get('more_info_url_' + str(number_index), ""),
                'statement_text': request.POST.get('statement_text_' + str(number_index), ""),
                'position_stance': request.POST.get('position_stance_' + str(number_index), "SUPPORT"),
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
