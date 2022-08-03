# candidate/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import datetime as the_other_datetime
import json
import urllib.request
from socket import timeout
from django.http import HttpResponse
from django.utils.timezone import now
import wevote_functions.admin
from apis_v1.views.views_extension import process_pdf_to_html
from ballot.models import CANDIDATE
from bookmark.models import BookmarkItemList
from config.base import get_environment_variable
from election.models import ElectionManager
from exception.models import handle_exception
from image.controllers import retrieve_all_images_for_one_candidate, cache_master_and_resized_image, \
    IMAGE_SOURCE_BALLOTPEDIA, \
    LINKEDIN, TWITTER, WIKIPEDIA, FACEBOOK
from import_export_vote_smart.controllers import retrieve_and_match_candidate_from_vote_smart, \
    retrieve_candidate_photo_from_vote_smart
from office.models import ContestOfficeManager
from politician.models import PoliticianManager
from position.controllers import move_positions_to_another_candidate, update_all_position_details_from_candidate
from twitter.models import TwitterUserManager
from wevote_functions.functions import add_period_to_middle_name_initial, add_period_to_name_prefix_and_suffix, \
    convert_date_to_we_vote_date_string, convert_to_int, \
    convert_to_political_party_constant, positive_value_exists, process_request_from_master, \
    extract_twitter_handle_from_text_string, extract_website_from_url, \
    remove_period_from_middle_name_initial, remove_period_from_name_prefix_and_suffix
from .models import CandidateListManager, CandidateCampaign, CandidateManager, \
    CANDIDATE_UNIQUE_IDENTIFIERS, PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_UNKNOWN

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
CANDIDATES_SYNC_URL = get_environment_variable("CANDIDATES_SYNC_URL")  # candidatesSyncOut


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


def add_name_to_next_spot(candidate_or_politician, google_civic_candidate_name_to_add):

    if not positive_value_exists(google_civic_candidate_name_to_add):
        return candidate_or_politician

    # If an initial exists in the name (ex/ " A "), then search for the name
    # with a period added (ex/ " A. ") We check for an exact match AND a match with/without initial + period
    # google_civic_candidate_name
    name_changed = False
    google_civic_candidate_name_modified = "IGNORE_NO_NAME"
    google_civic_candidate_name_new_start = google_civic_candidate_name_to_add  # For prefix/suffixes
    add_results = add_period_to_middle_name_initial(google_civic_candidate_name_to_add)
    if add_results['name_changed']:
        name_changed = True
        google_civic_candidate_name_modified = add_results['modified_name']
        google_civic_candidate_name_new_start = google_civic_candidate_name_modified
    else:
        add_results = remove_period_from_middle_name_initial(google_civic_candidate_name_to_add)
        if add_results['name_changed']:
            name_changed = True
            google_civic_candidate_name_modified = add_results['modified_name']
            google_civic_candidate_name_new_start = google_civic_candidate_name_modified

    # Deal with prefix and suffix
    # If an prefix or suffix exists in the name (ex/ " JR"), then search for the name
    # with a period added (ex/ " JR.")
    add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name_new_start)
    if add_results['name_changed']:
        name_changed = True
        google_civic_candidate_name_modified = add_results['modified_name']
    else:
        add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name_new_start)
        if add_results['name_changed']:
            name_changed = True
            google_civic_candidate_name_modified = add_results['modified_name']

    if not positive_value_exists(candidate_or_politician.google_civic_candidate_name):
        candidate_or_politician.google_civic_candidate_name = google_civic_candidate_name_to_add
    elif google_civic_candidate_name_to_add == candidate_or_politician.google_civic_candidate_name:
        # The value is already stored in candidate_or_politician.google_civic_candidate_name so doesn't need
        # to be added anywhere below
        pass
    elif name_changed and candidate_or_politician.google_civic_candidate_name == google_civic_candidate_name_modified:
        # If candidate_or_politician.google_civic_candidate_name has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif not positive_value_exists(candidate_or_politician.google_civic_candidate_name2):
        candidate_or_politician.google_civic_candidate_name2 = google_civic_candidate_name_to_add
    elif google_civic_candidate_name_to_add == candidate_or_politician.google_civic_candidate_name2:
        # The value is already stored in candidate_or_politician.google_civic_candidate_name2 so doesn't need
        # to be added to candidate_or_politician.google_civic_candidate_name3
        pass
    elif name_changed and candidate_or_politician.google_civic_candidate_name2 == google_civic_candidate_name_modified:
        # If candidate_or_politician.google_civic_candidate_name2 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif not positive_value_exists(candidate_or_politician.google_civic_candidate_name3):
        candidate_or_politician.google_civic_candidate_name3 = google_civic_candidate_name_to_add
    elif google_civic_candidate_name_to_add == candidate_or_politician.google_civic_candidate_name3:
        # The value is already stored in candidate_or_politician.google_civic_candidate_name2 so doesn't need
        # to be added to candidate_or_politician.google_civic_candidate_name3
        pass
    elif name_changed and candidate_or_politician.google_civic_candidate_name3 == google_civic_candidate_name_modified:
        # If candidate_or_politician.google_civic_candidate_name3 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    # We only support 3 alternate candidate names so far
    # elif not positive_value_exists(candidate_or_politician.google_civic_candidate_name4):
    #     candidate_or_politician.google_civic_candidate_name4 = google_civic_candidate_name_to_add
    # elif google_civic_candidate_name_to_add == candidate_or_politician.google_civic_candidate_name4:
    #     # The value is already stored in candidate_or_politician.google_civic_candidate_name2 so doesn't need
    #     # to be added to candidate_or_politician.google_civic_candidate_name3
    #     pass
    # elif name_changed and candidate_or_politician.google_civic_candidate_name4 == google_civic_candidate_name_modified:
    #     # If candidate_or_politician.google_civic_candidate_name4 has a middle initial with/without a period
    #     # don't store it if the alternate without/with the period already is stored
    #     pass
    # elif not positive_value_exists(candidate_or_politician.google_civic_candidate_name5):
    #     candidate_or_politician.google_civic_candidate_name5 = google_civic_candidate_name_to_add
    # # We currently only support 5 alternate names
    return candidate_or_politician


def candidates_import_from_sample_file():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Load saved json from local file
    logger.info("Loading CandidateCampaigns from local file")

    with open("candidate/import_data/candidates_sample.json") as json_data:
        structured_json = json.load(json_data)

    return candidates_import_from_structured_json(structured_json)


def candidates_import_from_master_server(
        request, google_civic_election_id='', state_code=''):  # Consumes candidatesSyncOut
    """
    Get the json data, and either create new entries or update existing
    :param request:
    :param google_civic_election_id:
    :param state_code:
    :return:
    """

    import_results, structured_json = process_request_from_master(
        request, "Loading Candidates from We Vote Master servers",
        CANDIDATES_SYNC_URL,
        {
            "key": WE_VOTE_API_KEY,  # This comes from an environment variable
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": state_code,
        }
    )

    if import_results['success']:
        # results = filter_candidates_structured_json_for_local_duplicates(structured_json)
        # filtered_structured_json = results['structured_json']
        # duplicates_removed = results['duplicates_removed']
        # import_results = candidates_import_from_structured_json(filtered_structured_json)
        import_results = candidates_import_from_structured_json(structured_json)
        # import_results['duplicates_removed'] = duplicates_removed
        import_results['duplicates_removed'] = 0

    import2_results, structured_json = process_request_from_master(
        request, "Loading Candidate to Office Links from We Vote Master servers",
        "https://api.wevoteusa.org/apis/v1/candidateToOfficeLinkSyncOut/",
        {
            "key": WE_VOTE_API_KEY,  # This comes from an environment variable
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": state_code,
        }
    )

    if import2_results['success']:
        import2_results = candidate_to_office_link_import_from_structured_json(structured_json)

    return import_results


def fetch_duplicate_candidate_count(we_vote_candidate, ignore_candidate_id_list):
    if not hasattr(we_vote_candidate, 'google_civic_election_id'):
        return 0

    if not positive_value_exists(we_vote_candidate.google_civic_election_id):
        return 0

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_google_civic_election_id_list_from_candidate_we_vote_id_list(
        candidate_we_vote_id_list=[we_vote_candidate.we_vote_id])
    google_civic_election_id_list = results['google_civic_election_id_list']

    # Search for other candidates in any of the elections this candidate is in that match name and election
    return candidate_list_manager.fetch_candidates_from_non_unique_identifiers_count(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=we_vote_candidate.state_code,
        candidate_twitter_handle=we_vote_candidate.candidate_twitter_handle,
        candidate_name=we_vote_candidate.candidate_name,
        ignore_candidate_id_list=ignore_candidate_id_list)


def find_duplicate_candidate(we_vote_candidate, ignore_candidate_id_list, read_only=True):
    if not hasattr(we_vote_candidate, 'candidate_name'):
        error_results = {
            'success':                              False,
            'status':                               "FIND_DUPLICATE_CANDIDATE_MISSING_CANDIDATE_OBJECT ",
            'candidate_merge_possibility_found':    False,
            'candidate_list':                       [],
        }
        return error_results

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_google_civic_election_id_list_from_candidate_we_vote_id_list(
        candidate_we_vote_id_list=[we_vote_candidate.we_vote_id])
    google_civic_election_id_list = results['google_civic_election_id_list']

    # Search for other candidates that share the same elections that match name and election
    try:
        results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            candidate_twitter_handle=we_vote_candidate.candidate_twitter_handle,
            candidate_name=we_vote_candidate.candidate_name,
            google_civic_election_id_list=google_civic_election_id_list,
            ignore_candidate_id_list=ignore_candidate_id_list,
            state_code=we_vote_candidate.state_code,
            vote_usa_politician_id=we_vote_candidate.vote_usa_politician_id,
            read_only=read_only,
        )

        if results['candidate_found']:
            candidate_merge_conflict_values = \
                figure_out_candidate_conflict_values(we_vote_candidate, results['candidate'])

            results = {
                'success':                              True,
                'status':                               "FIND_DUPLICATE_CANDIDATE_DUPLICATES_FOUND",
                'candidate_merge_possibility_found':    True,
                'candidate_merge_possibility':          results['candidate'],
                'candidate_merge_conflict_values':      candidate_merge_conflict_values,
                'candidate_list':                       results['candidate_list'],
            }
            return results
        elif results['candidate_list_found']:
            # Only deal with merging the incoming candidate and the first on found
            candidate_merge_conflict_values = \
                figure_out_candidate_conflict_values(we_vote_candidate, results['candidate_list'][0])

            results = {
                'success':                              True,
                'status':                               "FIND_DUPLICATE_CANDIDATE_DUPLICATES_FOUND",
                'candidate_merge_possibility_found':    True,
                'candidate_merge_possibility':          results['candidate_list'][0],
                'candidate_merge_conflict_values':      candidate_merge_conflict_values,
                'candidate_list':                       results['candidate_list'],
            }
            return results
        else:
            results = {
                'success':                              True,
                'status':                               "FIND_DUPLICATE_CANDIDATE_NO_DUPLICATES_FOUND",
                'candidate_merge_possibility_found':    False,
                'candidate_list':                       results['candidate_list'],
            }
            return results

    except CandidateCampaign.DoesNotExist:
        pass
    except Exception as e:
        pass

    results = {
        'success':                              True,
        'status':                               "FIND_DUPLICATE_CANDIDATE_NO_DUPLICATES_FOUND",
        'candidate_merge_possibility_found':    False,
        'candidate_list':                       [],
    }
    return results


def figure_out_candidate_conflict_values(candidate1, candidate2):
    candidate_merge_conflict_values = {}

    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        try:
            candidate1_attribute_value = getattr(candidate1, attribute)
            candidate2_attribute_value = getattr(candidate2, attribute)
            if candidate1_attribute_value is None and candidate2_attribute_value is None:
                candidate_merge_conflict_values[attribute] = 'MATCHING'
            elif candidate1_attribute_value is None or candidate1_attribute_value == "":
                candidate_merge_conflict_values[attribute] = 'CANDIDATE2'
            elif candidate2_attribute_value is None or candidate2_attribute_value == "":
                candidate_merge_conflict_values[attribute] = 'CANDIDATE1'
            else:
                if attribute == "ballotpedia_candidate_url" \
                        or attribute == "candidate_contact_form_url" \
                        or attribute == "candidate_instagram_form_url" \
                        or attribute == "facebook_url" \
                        or attribute == "linkedin_url" \
                        or attribute == "youtube_url":
                    # If there is a link with 'http' in candidate 2, and candidate 1 doesn't have 'http',
                    #  use the one with 'http'
                    if 'http' in candidate2_attribute_value and 'http' not in candidate1_attribute_value:
                        candidate_merge_conflict_values[attribute] = 'CANDIDATE2'
                    elif candidate1_attribute_value.lower() == candidate2_attribute_value.lower():
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "candidate_twitter_handle":
                    if candidate1_attribute_value.lower() == candidate2_attribute_value.lower():
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "candidate_url":
                    candidate1_attribute_value_trimmed = candidate1_attribute_value.rstrip('/')
                    candidate2_attribute_value_trimmed = candidate2_attribute_value.rstrip('/')
                    if candidate1_attribute_value_trimmed.lower() == candidate2_attribute_value_trimmed.lower():
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    elif 'http' in candidate2_attribute_value and 'http' not in candidate1_attribute_value:
                        candidate_merge_conflict_values[attribute] = 'CANDIDATE2'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "candidate_name" or attribute == "state_code":
                    if candidate1_attribute_value.lower() == candidate2_attribute_value.lower():
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "party":
                    if convert_to_political_party_constant(candidate1_attribute_value) == \
                            convert_to_political_party_constant(candidate2_attribute_value):
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "profile_image_type_currently_active":
                    if candidate1_attribute_value == 'UNKNOWN' and candidate2_attribute_value != 'UNKNOWN':
                        candidate_merge_conflict_values[attribute] = 'CANDIDATE2'
                    elif candidate1_attribute_value == candidate2_attribute_value:
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    if candidate1_attribute_value == candidate2_attribute_value:
                        candidate_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        candidate_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return candidate_merge_conflict_values


def merge_if_duplicate_candidates(candidate1_on_stage, candidate2_on_stage, conflict_values):
    success = False
    status = "MERGE_IF_DUPLICATE_CANDIDATES "
    candidates_merged = False
    decisions_required = False
    candidate1_we_vote_id = candidate1_on_stage.we_vote_id
    candidate2_we_vote_id = candidate2_on_stage.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        if attribute == "candidate_url":
            # Don't worry about CONFLICT with any of these fields, but honor CANDIDATE2
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CANDIDATE2":
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
            elif positive_value_exists(getattr(candidate1_on_stage, attribute)):
                # We can proceed because candidate1 has a valid image, so we can default to choosing that one
                pass
            elif positive_value_exists(getattr(candidate2_on_stage, attribute)):
                # If we are here candidate1 does NOT have image, but candidate2 does
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
        elif attribute == "facebook_profile_image_url_https" \
                or attribute == "twitter_profile_background_image_url_https" \
                or attribute == "twitter_profile_banner_url_https" \
                or attribute == "twitter_profile_image_url_https" \
                or attribute == "twitter_user_id" \
                or attribute == "vote_usa_profile_image_url_https" \
                or attribute == "we_vote_hosted_profile_facebook_image_url_large" \
                or attribute == "we_vote_hosted_profile_facebook_image_url_medium" \
                or attribute == "we_vote_hosted_profile_facebook_image_url_tiny" \
                or attribute == "we_vote_hosted_profile_image_url_large" \
                or attribute == "we_vote_hosted_profile_image_url_medium" \
                or attribute == "we_vote_hosted_profile_image_url_tiny" \
                or attribute == "we_vote_hosted_profile_twitter_image_url_large" \
                or attribute == "we_vote_hosted_profile_twitter_image_url_medium" \
                or attribute == "we_vote_hosted_profile_twitter_image_url_tiny" \
                or attribute == "we_vote_hosted_profile_uploaded_image_url_large" \
                or attribute == "we_vote_hosted_profile_uploaded_image_url_medium" \
                or attribute == "we_vote_hosted_profile_uploaded_image_url_tiny" \
                or attribute == "we_vote_hosted_profile_vote_usa_image_url_large" \
                or attribute == "we_vote_hosted_profile_vote_usa_image_url_medium" \
                or attribute == "we_vote_hosted_profile_vote_usa_image_url_tiny":
            # Don't let conflict stop us with any of these fields
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CANDIDATE2":
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
            elif positive_value_exists(getattr(candidate1_on_stage, attribute)):
                # We can proceed because candidate1 has a valid field, so we can default to choosing that one
                pass
            elif positive_value_exists(getattr(candidate2_on_stage, attribute)):
                # If we are here candidate1 does NOT have image, but candidate2 does
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
        elif attribute == "facebook_url" \
                or attribute == "maplight_id" \
                or attribute == "profile_image_type_currently_active" \
                or attribute == "twitter_url":
            # Don't worry about CONFLICT with any of these fields, but honor CANDIDATE2
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CANDIDATE2":
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
            elif positive_value_exists(getattr(candidate1_on_stage, attribute)):
                # We can proceed because candidate1 has a valid image, so we can default to choosing that one
                pass
            elif positive_value_exists(getattr(candidate2_on_stage, attribute)):
                # If we are here candidate1 does NOT have image, but candidate2 does
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
        elif attribute == "contest_office_id" \
                or attribute == "contest_office_we_vote_id" \
                or attribute == "google_civic_election_id":
            # We are phasing these fields out
            if positive_value_exists(getattr(candidate1_on_stage, attribute)):
                pass
            elif positive_value_exists(getattr(candidate2_on_stage, attribute)):
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                decisions_required = True
                status += 'CONFLICT: ' + str(attribute) + ' '
            elif conflict_value == "CANDIDATE2":
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)

    if not decisions_required:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = merge_these_two_candidates(candidate1_we_vote_id, candidate2_we_vote_id, merge_choices)

        if merge_results['candidates_merged']:
            success = True
            candidates_merged = True

    results = {
        'success':              success,
        'status':               status,
        'candidates_merged':    candidates_merged,
        'decisions_required':   decisions_required,
        'candidate':            candidate1_on_stage,
    }
    return results


def merge_these_two_candidates(candidate1_we_vote_id, candidate2_we_vote_id, admin_merge_choices={}):
    """
    Process the merging of two candidates
    :param candidate1_we_vote_id:
    :param candidate2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :return:
    """
    status = ""
    candidate_manager = CandidateManager()

    # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
    candidate1_results = \
        candidate_manager.retrieve_candidate_from_we_vote_id(candidate1_we_vote_id, read_only=False)
    if candidate1_results['candidate_found']:
        candidate1_on_stage = candidate1_results['candidate']
        candidate1_id = candidate1_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_CANDIDATES-COULD_NOT_RETRIEVE_CANDIDATE1 ",
            'candidates_merged': False,
            'candidate': None,
        }
        return results

    candidate2_results = \
        candidate_manager.retrieve_candidate_from_we_vote_id(candidate2_we_vote_id, read_only=False)
    if candidate2_results['candidate_found']:
        candidate2_on_stage = candidate2_results['candidate']
        candidate2_id = candidate2_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_CANDIDATES-COULD_NOT_RETRIEVE_CANDIDATE2 ",
            'candidates_merged': False,
            'candidate': None,
        }
        return results

    # TODO: Migrate images?

    # Merge politician data
    politician1_we_vote_id = candidate1_on_stage.politician_we_vote_id
    politician2_we_vote_id = candidate2_on_stage.politician_we_vote_id
    if positive_value_exists(politician1_we_vote_id) and positive_value_exists(politician2_we_vote_id):
        if politician1_we_vote_id != politician2_we_vote_id:
            # Conflicting parent politicians
            # TODO: Call separate politician merge process
            results = {
                'success': False,
                'status': "MERGE_THESE_TWO_CANDIDATES-UNABLE_TO_MERGE_PARENT_POLITICIANS ",
                'candidates_merged': False,
                'candidate': None,
            }
            return results
            # else do nothing (same parent politician)
    elif positive_value_exists(politician2_we_vote_id):
        # Migrate politician from candidate 2 to candidate 1
        politician2_id = 0
        try:
            # get the politician_id directly to avoid bad data
            politician_manager = PoliticianManager()
            results = politician_manager.retrieve_politician(0, politician2_we_vote_id)
            if results['politician_found']:
                politician = results['politician']
                politician2_id = politician.id
        except Exception as e:
            status += "COULD_NOT_UPDATE_POLITICIAN_FOR_CANDIDATE2 " + str(e) + " "
        candidate1_on_stage.politician_we_vote_id = politician2_we_vote_id
        candidate1_on_stage.politician_id = politician2_id
    # else do nothing (no parent politician for candidate 2)

    # # TODO: Migrate bookmarks
    # bookmark_item_list_manager = BookmarkItemList()
    # bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_candidate(candidate2_we_vote_id)
    # if bookmark_results['bookmark_item_list_found']:
    #     status += "Bookmarks found for Candidate 2 - automatic merge not working yet. "
    #     results = {
    #         'success': True,
    #         'status': status,
    #         'candidates_merged': False,
    #         'candidate': None,
    #     }
    #     return results

    # Merge attribute values chosen by the admin
    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        # try:
        if attribute in admin_merge_choices:
            setattr(candidate1_on_stage, attribute, admin_merge_choices[attribute])
        # except Exception as e:
        #     # Don't completely fail if in attribute can't be saved.
        #     status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "

    # Preserve unique google_civic_candidate_name, _name2, _name3, _name4, and _name5
    if positive_value_exists(candidate2_on_stage.google_civic_candidate_name):
        candidate1_on_stage = add_name_to_next_spot(
            candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name)
    if positive_value_exists(candidate2_on_stage.google_civic_candidate_name2):
        candidate1_on_stage = add_name_to_next_spot(
            candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name2)
    if positive_value_exists(candidate2_on_stage.google_civic_candidate_name3):
        candidate1_on_stage = add_name_to_next_spot(
            candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name3)

    # Merge public positions
    public_positions_results = move_positions_to_another_candidate(candidate2_id, candidate2_we_vote_id,
                                                                   candidate1_id, candidate1_we_vote_id,
                                                                   True)
    if not public_positions_results['success']:
        status += public_positions_results['status']
        status += "MERGE_THESE_TWO_CANDIDATES-COULD_NOT_MOVE_PUBLIC_POSITIONS_TO_CANDIDATE1 "
        results = {
            'success': False,
            'status': status,
            'candidates_merged': False,
            'candidate': None,
        }
        return results

    # Merge friends-only positions
    friends_positions_results = move_positions_to_another_candidate(candidate2_id, candidate2_we_vote_id,
                                                                    candidate1_id, candidate1_we_vote_id,
                                                                    False)
    if not friends_positions_results['success']:
        status += friends_positions_results['status']
        status += "MERGE_THESE_TWO_CANDIDATES-COULD_NOT_MOVE_FRIENDS_POSITIONS_TO_CANDIDATE1 "
        results = {
            'success': False,
            'status': status,
            'candidates_merged': False,
            'candidate': None,
        }
        return results

    # #####################################
    # Deal with candidate_to_office_link
    # We are going to keep candidate1 linkages
    candidate1_office_we_vote_id_list = []
    candidate1_link_results = candidate_manager.retrieve_candidate_to_office_link(
            candidate_we_vote_id=candidate1_we_vote_id, read_only=False)
    if positive_value_exists(candidate1_link_results['success']):
        candidate1_to_office_link_list = candidate1_link_results['candidate_to_office_link_list']
        # Cycle through the candidate1 links and put the contest_office_we_vote_id's into a simple list
        for link in candidate1_to_office_link_list:
            candidate1_office_we_vote_id_list.append(link.contest_office_we_vote_id)
    else:
        status += candidate1_link_results['status']

    # We need to migrate candidate2 linkages
    candidate2_to_office_link_list = []
    candidate2_link_results = candidate_manager.retrieve_candidate_to_office_link(
            candidate_we_vote_id=candidate2_we_vote_id, read_only=False)
    if positive_value_exists(candidate2_link_results['success']):
        candidate2_to_office_link_list = candidate2_link_results['candidate_to_office_link_list']
    else:
        status += candidate1_link_results['status']

    # Cycle through the candidate2 links. Either move them (if "to" link doesn't exist), or delete if a "to" link exists
    for candidate2_link in candidate2_to_office_link_list:
        if candidate2_link.contest_office_we_vote_id in candidate1_office_we_vote_id_list:
            candidate2_link.delete()
        else:
            candidate2_link.candidate_we_vote_id = candidate1_we_vote_id
            candidate2_link.save()

    # Note: wait to wrap in try/except block
    candidate1_on_stage.save()
    # 2021-10-16 Uses image data from master table which we aren't updating with the merge yet
    # refresh_candidate_data_from_master_tables(candidate1_on_stage.we_vote_id)

    # Remove candidate 2
    candidate2_on_stage.delete()

    results = {
        'success': True,
        'status': status,
        'candidates_merged': True,
        'candidate': candidate1_on_stage,
    }
    return results


def move_candidates_to_another_office(from_contest_office_id, from_contest_office_we_vote_id,
                                      to_contest_office_id, to_contest_office_we_vote_id):
    status = ''
    success = True
    candidate_entries_moved = 0
    candidate_entries_not_moved = 0
    candidate_manager = CandidateManager()
    contest_manager = ContestOfficeManager()

    # #####################################
    # The from office
    if positive_value_exists(from_contest_office_id) and not positive_value_exists(from_contest_office_we_vote_id):
        from_contest_office_we_vote_id = contest_manager.fetch_contest_office_we_vote_id_from_id(from_contest_office_id)
    from_link_results = candidate_manager.retrieve_candidate_to_office_link(
            contest_office_we_vote_id=from_contest_office_we_vote_id, read_only=False)
    if not positive_value_exists(from_link_results['success']):
        status += from_link_results['status']
        success = False
        results = {
            'success': success,
            'status': status,
            'from_contest_office_id': from_contest_office_id,
            'from_contest_office_we_vote_id': from_contest_office_we_vote_id,
            'to_contest_office_id': to_contest_office_id,
            'to_contest_office_we_vote_id': to_contest_office_we_vote_id,
            'candidate_entries_moved': candidate_entries_moved,
            'candidate_entries_not_moved': candidate_entries_not_moved,
        }
        return results
    from_candidate_to_office_link_list = from_link_results['candidate_to_office_link_list']

    # #####################################
    # The to office
    if positive_value_exists(to_contest_office_id) and not positive_value_exists(to_contest_office_we_vote_id):
        to_contest_office_we_vote_id = contest_manager.fetch_contest_office_we_vote_id_from_id(to_contest_office_id)
    to_link_results = candidate_manager.retrieve_candidate_to_office_link(
            contest_office_we_vote_id=to_contest_office_we_vote_id, read_only=False)
    if not positive_value_exists(to_link_results['success']):
        status += to_link_results['status']
        success = False
        results = {
            'success': success,
            'status': status,
            'from_contest_office_id': from_contest_office_id,
            'from_contest_office_we_vote_id': from_contest_office_we_vote_id,
            'to_contest_office_id': to_contest_office_id,
            'to_contest_office_we_vote_id': to_contest_office_we_vote_id,
            'candidate_entries_moved': candidate_entries_moved,
            'candidate_entries_not_moved': candidate_entries_not_moved,
        }
        return results
    to_candidate_to_office_link_list = to_link_results['candidate_to_office_link_list']

    # #####################################
    # Cycle through the to links and put the candidate_we_vote_id's into a simple list
    to_candidate_we_vote_id_list = []
    for to_link in to_candidate_to_office_link_list:
        to_candidate_we_vote_id_list.append(to_link.candidate_we_vote_id)

    # #####################################
    # Cycle through the from links and either move them (if a "to" link doesn't exist), or delete if a "to" link exists
    for from_link in from_candidate_to_office_link_list:
        if from_link.candidate_we_vote_id in to_candidate_we_vote_id_list:
            from_link.delete()
            candidate_entries_not_moved += 1
        else:
            from_link.contest_office_we_vote_id = to_contest_office_we_vote_id
            from_link.google_civic_election_id = \
                contest_manager.fetch_google_civic_election_id_from_office_we_vote_id(to_contest_office_we_vote_id)
            from_link.save()
            candidate_entries_moved += 1

    results = {
        'status':                           status,
        'success':                          success,
        'from_contest_office_id':           from_contest_office_id,
        'from_contest_office_we_vote_id':   from_contest_office_we_vote_id,
        'to_contest_office_id':             to_contest_office_id,
        'to_contest_office_we_vote_id':     to_contest_office_we_vote_id,
        'candidate_entries_moved':          candidate_entries_moved,
        'candidate_entries_not_moved':      candidate_entries_not_moved,
    }
    return results


def move_candidates_to_another_politician(
        from_politician_id=0,
        from_politician_we_vote_id='',
        to_politician_id=0,
        to_politician_we_vote_id=''):
    """

    :param from_politician_id:
    :param from_politician_we_vote_id:
    :param to_politician_id:
    :param to_politician_we_vote_id:
    :return:
    """
    status = ''
    success = True
    candidate_entries_moved = 0

    if positive_value_exists(from_politician_we_vote_id):
        try:
            candidate_entries_moved += CandidateCampaign.objects \
                .filter(politician_we_vote_id__iexact=from_politician_we_vote_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_CANDIDATES_BY_POLITICIAN_WE_VOTE_ID: " + str(e) + " "
            success = False

    if positive_value_exists(from_politician_id):
        try:
            candidate_entries_moved += CandidateCampaign.objects \
                .filter(politician_id=from_politician_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_CANDIDATES_BY_POLITICIAN_ID: " + str(e) + " "
            success = False

    results = {
        'status':                   status,
        'success':                  success,
        'candidate_entries_moved':  candidate_entries_moved,
    }
    return results


def filter_candidates_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove candidates that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    processed = 0
    duplicates_removed = 0
    filtered_structured_json = []
    candidate_list_manager = CandidateListManager()
    for one_candidate in structured_json:
        candidate_name = one_candidate['candidate_name'] if 'candidate_name' in one_candidate else ''
        google_civic_candidate_name = one_candidate['google_civic_candidate_name'] \
            if 'google_civic_candidate_name' in one_candidate else ''
        google_civic_candidate_name2 = one_candidate['google_civic_candidate_name2'] \
            if 'google_civic_candidate_name2' in one_candidate else ''
        google_civic_candidate_name3 = one_candidate['google_civic_candidate_name3'] \
            if 'google_civic_candidate_name3' in one_candidate else ''
        we_vote_id = one_candidate['we_vote_id'] if 'we_vote_id' in one_candidate else ''
        google_civic_election_id = \
            one_candidate['google_civic_election_id'] if 'google_civic_election_id' in one_candidate else ''
        contest_office_we_vote_id = \
            one_candidate['contest_office_we_vote_id'] if 'contest_office_we_vote_id' in one_candidate else ''
        politician_we_vote_id = one_candidate['politician_we_vote_id'] \
            if 'politician_we_vote_id' in one_candidate else ''
        candidate_twitter_handle = one_candidate['candidate_twitter_handle'] \
            if 'candidate_twitter_handle' in one_candidate else ''
        ballotpedia_candidate_id = one_candidate['ballotpedia_candidate_id'] \
            if 'ballotpedia_candidate_id' in one_candidate else ''
        # Not needed here: ballotpedia_person_id
        vote_smart_id = one_candidate['vote_smart_id'] if 'vote_smart_id' in one_candidate else ''
        maplight_id = one_candidate['maplight_id'] if 'maplight_id' in one_candidate else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = candidate_list_manager.retrieve_possible_duplicate_candidates(
            candidate_name, google_civic_candidate_name, google_civic_candidate_name2, google_civic_candidate_name3,
            google_civic_election_id, contest_office_we_vote_id,
            politician_we_vote_id, candidate_twitter_handle, ballotpedia_candidate_id, vote_smart_id, maplight_id,
            we_vote_id_from_master, read_only=True)

        if results['candidate_list_found']:
            # print("Skipping candidate " + str(candidate_name) + ",  " + str(google_civic_candidate_name) + ",  " +
            #       str(google_civic_election_id) + ",  " + str(contest_office_we_vote_id) + ",  " +
            #       str(politician_we_vote_id) + ",  " + str(candidate_twitter_handle) + ",  " +
            #       str(vote_smart_id) + ",  " + str(maplight_id) + ",  " + str(we_vote_id_from_master))
            # Obsolete note?: There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_candidate)

        processed += 1
        if not processed % 10000:
            print("... candidates checked for duplicates: " + str(processed) + " of " + str(len(structured_json)))

    candidates_results = {
        'success':              True,
        'status':               "FILTER_CANDIDATES_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return candidates_results


def candidates_import_from_structured_json(structured_json):  # Consumes candidatesSyncOut
    candidate_manager = CandidateManager()
    candidates_saved = 0
    candidates_updated = 0
    candidates_not_processed = 0
    for one_candidate in structured_json:
        candidate_name = one_candidate['candidate_name'] if 'candidate_name' in one_candidate else ''
        we_vote_id = one_candidate['we_vote_id'] if 'we_vote_id' in one_candidate else ''
        google_civic_election_id = \
            one_candidate['google_civic_election_id'] if 'google_civic_election_id' in one_candidate else ''
        ocd_division_id = one_candidate['ocd_division_id'] if 'ocd_division_id' in one_candidate else ''
        contest_office_we_vote_id = \
            one_candidate['contest_office_we_vote_id'] if 'contest_office_we_vote_id' in one_candidate else ''

        # This routine imports from another We Vote server, so a contest_office_id doesn't come from import
        # Look up contest_office in this local database.
        # If we don't find a contest_office by we_vote_id, then we know the contest_office hasn't been imported
        # from another server yet, so we fail out.
        contest_office_manager = ContestOfficeManager()
        contest_office_id = contest_office_manager.fetch_contest_office_id_from_we_vote_id(
            contest_office_we_vote_id)

        if positive_value_exists(candidate_name) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(we_vote_id):  # Removed:  and positive_value_exists(contest_office_id)
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False
        if proceed_to_update_or_create:
            updated_candidate_values = {
                'candidate_name': candidate_name,
                'contest_office_id': contest_office_id,
                'contest_office_we_vote_id': contest_office_we_vote_id,
                'google_civic_election_id': google_civic_election_id,
                'ocd_division_id': ocd_division_id,
                'we_vote_id': we_vote_id,
            }
            if 'ballot_guide_official_statement' in one_candidate:
                updated_candidate_values['ballot_guide_official_statement'] = \
                    one_candidate['ballot_guide_official_statement']
            if 'ballotpedia_candidate_id' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_id'] = one_candidate['ballotpedia_candidate_id']
            if 'ballotpedia_candidate_name' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_name'] = one_candidate['ballotpedia_candidate_name']
            if 'ballotpedia_candidate_url' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_url'] = one_candidate['ballotpedia_candidate_url']
            if 'ballotpedia_candidate_summary' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_summary'] = \
                    one_candidate['ballotpedia_candidate_summary']
            if 'ballotpedia_election_id' in one_candidate:
                updated_candidate_values['ballotpedia_election_id'] = one_candidate['ballotpedia_election_id']
            if 'ballotpedia_image_id' in one_candidate:
                updated_candidate_values['ballotpedia_image_id'] = one_candidate['ballotpedia_image_id']
            if 'ballotpedia_office_id' in one_candidate:
                updated_candidate_values['ballotpedia_office_id'] = one_candidate['ballotpedia_office_id']
            if 'ballotpedia_page_title' in one_candidate:
                updated_candidate_values['ballotpedia_page_title'] = one_candidate['ballotpedia_page_title']
            if 'ballotpedia_person_id' in one_candidate:
                updated_candidate_values['ballotpedia_person_id'] = one_candidate['ballotpedia_person_id']
            if 'ballotpedia_photo_url' in one_candidate:
                updated_candidate_values['ballotpedia_photo_url'] = one_candidate['ballotpedia_photo_url']
            if 'ballotpedia_profile_image_url_https' in one_candidate:
                updated_candidate_values['ballotpedia_profile_image_url_https'] = \
                    one_candidate['ballotpedia_profile_image_url_https']
            if 'ballotpedia_race_id' in one_candidate:
                updated_candidate_values['ballotpedia_race_id'] = one_candidate['ballotpedia_race_id']
            if 'birth_day_text' in one_candidate:
                updated_candidate_values['birth_day_text'] = one_candidate['birth_day_text']
            if 'candidate_contact_form_url' in one_candidate:
                updated_candidate_values['candidate_contact_form_url'] = one_candidate['candidate_contact_form_url']
            if 'candidate_email' in one_candidate:
                updated_candidate_values['candidate_email'] = one_candidate['candidate_email']
            if 'candidate_gender' in one_candidate:
                updated_candidate_values['candidate_gender'] = one_candidate['candidate_gender']
            if 'instagram_handle' in one_candidate:
                updated_candidate_values['instagram_handle'] = one_candidate['instagram_handle']
            if 'instagram_followers_count' in one_candidate:
                updated_candidate_values['instagram_followers_count'] = one_candidate['instagram_followers_count']
            if 'candidate_is_incumbent' in one_candidate:
                updated_candidate_values['candidate_is_incumbent'] = one_candidate['candidate_is_incumbent']
            if 'candidate_is_top_ticket' in one_candidate:
                updated_candidate_values['candidate_is_top_ticket'] = one_candidate['candidate_is_top_ticket']
            if 'candidate_participation_status' in one_candidate:
                updated_candidate_values['candidate_participation_status'] = \
                    one_candidate['candidate_participation_status']
            if 'candidate_phone' in one_candidate:
                updated_candidate_values['candidate_phone'] = one_candidate['candidate_phone']
            if 'candidate_twitter_handle' in one_candidate:
                updated_candidate_values['candidate_twitter_handle'] = \
                    one_candidate['candidate_twitter_handle']
            if 'candidate_ultimate_election_date' in one_candidate:
                updated_candidate_values['candidate_ultimate_election_date'] = \
                    one_candidate['candidate_ultimate_election_date']
            if 'candidate_url' in one_candidate:
                updated_candidate_values['candidate_url'] = one_candidate['candidate_url']
            if 'candidate_year' in one_candidate:
                updated_candidate_values['candidate_year'] = convert_to_int(one_candidate['candidate_year'])
            if 'contest_office_name' in one_candidate:
                updated_candidate_values['contest_office_name'] = one_candidate['contest_office_name']
            if 'crowdpac_candidate_id' in one_candidate:
                updated_candidate_values['crowdpac_candidate_id'] = one_candidate['crowdpac_candidate_id']
            if 'ctcl_uuid' in one_candidate:
                updated_candidate_values['ctcl_uuid'] = one_candidate['ctcl_uuid']
            if 'do_not_display_on_ballot' in one_candidate:
                updated_candidate_values['do_not_display_on_ballot'] = one_candidate['do_not_display_on_ballot']
            if 'facebook_profile_image_url_https' in one_candidate:
                updated_candidate_values['facebook_profile_image_url_https'] = \
                    one_candidate['facebook_profile_image_url_https']
            if 'facebook_url' in one_candidate:
                updated_candidate_values['facebook_url'] = one_candidate['facebook_url']
            if 'facebook_url_is_broken' in one_candidate:
                updated_candidate_values['facebook_url_is_broken'] = one_candidate['facebook_url_is_broken']
            if 'google_civic_candidate_name' in one_candidate:
                updated_candidate_values['google_civic_candidate_name'] = \
                    one_candidate['google_civic_candidate_name']
            if 'google_civic_candidate_name2' in one_candidate:
                updated_candidate_values['google_civic_candidate_name2'] = \
                    one_candidate['google_civic_candidate_name2']
            if 'google_civic_candidate_name3' in one_candidate:
                updated_candidate_values['google_civic_candidate_name3'] = \
                    one_candidate['google_civic_candidate_name3']
            if 'google_plus_url' in one_candidate:
                updated_candidate_values['google_plus_url'] = one_candidate['google_plus_url']
            if 'linkedin_url' in one_candidate:
                updated_candidate_values['linkedin_url'] = one_candidate['linkedin_url']
            if 'linkedin_photo_url' in one_candidate:
                updated_candidate_values['linkedin_photo_url'] = one_candidate['linkedin_photo_url']
            if 'maplight_id' in one_candidate:
                updated_candidate_values['maplight_id'] = one_candidate['maplight_id']
            if 'other_source_url' in one_candidate:
                updated_candidate_values['other_source_url'] = one_candidate['other_source_url']
            if 'other_source_photo_url' in one_candidate:
                updated_candidate_values['other_source_photo_url'] = one_candidate['other_source_photo_url']
            if 'order_on_ballot' in one_candidate:
                updated_candidate_values['order_on_ballot'] = one_candidate['order_on_ballot']
            if 'party' in one_candidate:
                updated_candidate_values['party'] = one_candidate['party']
            if 'photo_url' in one_candidate:
                updated_candidate_values['photo_url'] = one_candidate['photo_url']
            if 'photo_url_from_maplight' in one_candidate:
                updated_candidate_values['photo_url_from_maplight'] = one_candidate['photo_url_from_maplight']
            if 'photo_url_from_vote_smart' in one_candidate:
                updated_candidate_values['photo_url_from_vote_smart'] = one_candidate['photo_url_from_vote_smart']
            if 'photo_url_from_vote_usa' in one_candidate:
                updated_candidate_values['photo_url_from_vote_usa'] = one_candidate['photo_url_from_vote_usa']
            if 'politician_we_vote_id' in one_candidate:
                updated_candidate_values['politician_we_vote_id'] = one_candidate['politician_we_vote_id']
            if 'profile_image_type_currently_active' in one_candidate:
                updated_candidate_values['profile_image_type_currently_active'] = \
                    one_candidate['profile_image_type_currently_active']
            if 'state_code' in one_candidate:
                updated_candidate_values['state_code'] = one_candidate['state_code']
            if 'twitter_description' in one_candidate:
                updated_candidate_values['twitter_description'] = one_candidate['twitter_description']
            if 'twitter_followers_count' in one_candidate:
                updated_candidate_values['twitter_followers_count'] = one_candidate['twitter_followers_count']
            if 'twitter_location' in one_candidate:
                updated_candidate_values['twitter_location'] = one_candidate['twitter_location']
            if 'twitter_name' in one_candidate:
                updated_candidate_values['twitter_name'] = one_candidate['twitter_name']
            if 'twitter_profile_background_image_url_https' in one_candidate:
                updated_candidate_values['twitter_profile_background_image_url_https'] = \
                    one_candidate['twitter_profile_background_image_url_https']
            if 'twitter_profile_banner_url_https' in one_candidate:
                updated_candidate_values['twitter_profile_banner_url_https'] = \
                    one_candidate['twitter_profile_banner_url_https']
            if 'twitter_profile_image_url_https' in one_candidate:
                updated_candidate_values['twitter_profile_image_url_https'] = \
                    one_candidate['twitter_profile_image_url_https']
            if 'twitter_url' in one_candidate:
                updated_candidate_values['twitter_url'] = one_candidate['twitter_url']
            if 'twitter_user_id' in one_candidate:
                updated_candidate_values['twitter_user_id'] = one_candidate['twitter_user_id']
            if 'vote_smart_id' in one_candidate:
                updated_candidate_values['vote_smart_id'] = one_candidate['vote_smart_id']
            if 'vote_usa_office_id' in one_candidate:
                updated_candidate_values['vote_usa_office_id'] = one_candidate['vote_usa_office_id']
            if 'vote_usa_politician_id' in one_candidate:
                updated_candidate_values['vote_usa_politician_id'] = one_candidate['vote_usa_politician_id']
            if 'vote_usa_profile_image_url_https' in one_candidate:
                updated_candidate_values['vote_usa_profile_image_url_https'] = \
                    one_candidate['vote_usa_profile_image_url_https']
            if 'we_vote_hosted_profile_facebook_image_url_large' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_facebook_image_url_large'] = \
                    one_candidate['we_vote_hosted_profile_facebook_image_url_large']
            if 'we_vote_hosted_profile_facebook_image_url_medium' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_facebook_image_url_medium'] = \
                    one_candidate['we_vote_hosted_profile_facebook_image_url_medium']
            if 'we_vote_hosted_profile_facebook_image_url_tiny' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_facebook_image_url_tiny'] = \
                    one_candidate['we_vote_hosted_profile_facebook_image_url_tiny']
            if 'we_vote_hosted_profile_image_url_large' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_image_url_large'] = \
                    one_candidate['we_vote_hosted_profile_image_url_large']
            if 'we_vote_hosted_profile_image_url_medium' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_image_url_medium'] = \
                    one_candidate['we_vote_hosted_profile_image_url_medium']
            if 'we_vote_hosted_profile_image_url_tiny' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_image_url_tiny'] = \
                    one_candidate['we_vote_hosted_profile_image_url_tiny']
            if 'we_vote_hosted_profile_twitter_image_url_large' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_twitter_image_url_large'] = \
                    one_candidate['we_vote_hosted_profile_twitter_image_url_large']
            if 'we_vote_hosted_profile_twitter_image_url_medium' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_twitter_image_url_medium'] = \
                    one_candidate['we_vote_hosted_profile_twitter_image_url_medium']
            if 'we_vote_hosted_profile_twitter_image_url_tiny' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_twitter_image_url_tiny'] = \
                    one_candidate['we_vote_hosted_profile_twitter_image_url_tiny']
            if 'we_vote_hosted_profile_uploaded_image_url_large' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_uploaded_image_url_large'] = \
                    one_candidate['we_vote_hosted_profile_uploaded_image_url_large']
            if 'we_vote_hosted_profile_uploaded_image_url_medium' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_uploaded_image_url_medium'] = \
                    one_candidate['we_vote_hosted_profile_uploaded_image_url_medium']
            if 'we_vote_hosted_profile_uploaded_image_url_tiny' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_uploaded_image_url_tiny'] = \
                    one_candidate['we_vote_hosted_profile_uploaded_image_url_tiny']
            if 'we_vote_hosted_profile_vote_usa_image_url_large' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_vote_usa_image_url_large'] = \
                    one_candidate['we_vote_hosted_profile_vote_usa_image_url_large']
            if 'we_vote_hosted_profile_vote_usa_image_url_medium' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_vote_usa_image_url_medium'] = \
                    one_candidate['we_vote_hosted_profile_vote_usa_image_url_medium']
            if 'we_vote_hosted_profile_vote_usa_image_url_tiny' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_vote_usa_image_url_tiny'] = \
                    one_candidate['we_vote_hosted_profile_vote_usa_image_url_tiny']
            if 'wikipedia_page_id' in one_candidate:
                updated_candidate_values['wikipedia_page_id'] = one_candidate['wikipedia_page_id']
            if 'wikipedia_page_title' in one_candidate:
                updated_candidate_values['wikipedia_page_title'] = one_candidate['wikipedia_page_title']
            if 'wikipedia_photo_url' in one_candidate:
                updated_candidate_values['wikipedia_photo_url'] = one_candidate['wikipedia_photo_url']
            if 'withdrawal_date' in one_candidate:
                updated_candidate_values['withdrawal_date'] = one_candidate['withdrawal_date']
            if 'withdrawn_from_election' in one_candidate:
                updated_candidate_values['withdrawn_from_election'] = one_candidate['withdrawn_from_election']
            if 'youtube_url' in one_candidate:
                updated_candidate_values['youtube_url'] = one_candidate['youtube_url']

            results = candidate_manager.update_or_create_candidate(
                we_vote_id, google_civic_election_id, ocd_division_id,
                contest_office_id, contest_office_we_vote_id,
                candidate_name, updated_candidate_values)
        else:
            candidates_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_candidate_created']:
                candidates_saved += 1
            else:
                candidates_updated += 1

        processed = candidates_not_processed + candidates_saved + candidates_updated
        if not processed % 10000:
            print("... candidates processed for update/create: " + str(processed) + " of " + str(len(structured_json)))

    candidates_results = {
        'success':          True,
        'status':           "CANDIDATES_IMPORT_PROCESS_COMPLETE",
        'saved':            candidates_saved,
        'updated':          candidates_updated,
        'not_processed':    candidates_not_processed,
    }
    return candidates_results


def candidate_to_office_link_import_from_structured_json(structured_json):
    candidate_manager = CandidateManager()
    entries_saved = 0
    entries_updated = 0
    entries_not_processed = 0
    for one_candidate in structured_json:
        candidate_we_vote_id = one_candidate['candidate_we_vote_id'] if 'candidate_we_vote_id' in one_candidate else ''
        contest_office_we_vote_id = \
            one_candidate['contest_office_we_vote_id'] if 'contest_office_we_vote_id' in one_candidate else ''
        google_civic_election_id = \
            one_candidate['google_civic_election_id'] if 'google_civic_election_id' in one_candidate else ''
        state_code = one_candidate['state_code'] if 'state_code' in one_candidate else ''
        if positive_value_exists(candidate_we_vote_id) \
                and positive_value_exists(contest_office_we_vote_id) \
                and positive_value_exists(google_civic_election_id):
            results = candidate_manager.get_or_create_candidate_to_office_link(
                candidate_we_vote_id,
                contest_office_we_vote_id,
                google_civic_election_id,
                state_code)
        else:
            entries_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_candidate_to_office_link_created']:
                entries_saved += 1
            else:
                entries_updated += 1

        processed = entries_not_processed + entries_saved + entries_updated
        if not processed % 10000:
            print("... candidate to office link processed for update/create: " + str(processed) +
                  " of " + str(len(structured_json)))

    entries_results = {
        'success':          True,
        'status':           "CANDIDATE_TO_OFFICE_IMPORT_PROCESS_COMPLETE",
        'saved':            entries_saved,
        'updated':          entries_updated,
        'not_processed':    entries_not_processed,
    }
    return entries_results


def candidate_retrieve_for_api(candidate_id, candidate_we_vote_id):  # candidateRetrieve
    """
    Used by the api
    :param candidate_id:
    :param candidate_we_vote_id:
    :return:
    """
    # NOTE: Candidates retrieve is independent of *who* wants to see the data. Candidates retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItems does

    if not positive_value_exists(candidate_id) and not positive_value_exists(candidate_we_vote_id):
        status = 'VALID_CANDIDATE_ID_AND_CANDIDATE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      CANDIDATE,
            'id':                       candidate_id,
            'we_vote_id':               candidate_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    candidate_manager = CandidateManager()
    if positive_value_exists(candidate_id):
        results = candidate_manager.retrieve_candidate_from_id(candidate_id, read_only=True)
        success = results['success']
        status = results['status']
    elif positive_value_exists(candidate_we_vote_id):
        results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_CANDIDATE_ID_AND_CANDIDATE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      CANDIDATE,
            'id':                       candidate_id,
            'we_vote_id':               candidate_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        candidate = results['candidate']
        wdate = ''
        if isinstance(candidate.withdrawal_date, the_other_datetime.date):
            wdate = candidate.withdrawal_date.strftime("%Y-%m-%d")
        if not positive_value_exists(candidate.contest_office_name):
            candidate = candidate_manager.refresh_cached_candidate_office_info(candidate)

        office_list_for_candidate = []
        office_link_results = candidate_manager.retrieve_candidate_to_office_link(
            candidate_we_vote_id=candidate.we_vote_id,
            read_only=True)
        if office_link_results['list_found']:
            office_manager = ContestOfficeManager()
            election_manager = ElectionManager()
            candidate_to_office_link_list = office_link_results['candidate_to_office_link_list']
            for candidate_to_office_link in candidate_to_office_link_list:
                contest_office_name = ''
                results = office_manager.retrieve_contest_office_from_we_vote_id(
                    candidate_to_office_link.contest_office_we_vote_id)
                if results['contest_office_found']:
                    contest_office = results['contest_office']
                    if contest_office:
                        contest_office_name = contest_office.office_name
                election_day_text = ''
                if positive_value_exists(candidate_to_office_link.google_civic_election_id):
                    results = election_manager.retrieve_election(
                        google_civic_election_id=candidate_to_office_link.google_civic_election_id,
                        read_only=True)
                    if results['election_found']:
                        election = results['election']
                        election_day_text = election.election_day_text
                one_office_dict = {
                    'contest_office_name': contest_office_name,
                    'contest_office_we_vote_id': candidate_to_office_link.contest_office_we_vote_id,
                    'election_day_text': election_day_text,
                    'google_civic_election_id': candidate_to_office_link.google_civic_election_id,
                    'state_code': candidate_to_office_link.state_code,
                }
                office_list_for_candidate.append(one_office_dict)
        date_last_updated = ''
        if positive_value_exists(candidate.date_last_updated):
            date_last_updated = candidate.date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
        json_data = {
            'status':                       status,
            'success':                      True,
            'ballot_item_display_name':     candidate.display_candidate_name(),
            'ballotpedia_candidate_id':     candidate.ballotpedia_candidate_id,
            'ballotpedia_candidate_summary': candidate.ballotpedia_candidate_summary,
            'ballotpedia_candidate_url':    candidate.ballotpedia_candidate_url,
            'ballotpedia_person_id':        candidate.ballotpedia_person_id,
            'candidate_photo_url_large':    candidate.we_vote_hosted_profile_image_url_large
            if positive_value_exists(candidate.we_vote_hosted_profile_image_url_large)
            else candidate.candidate_photo_url(),
            'candidate_photo_url_medium':   candidate.we_vote_hosted_profile_image_url_medium,
            'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
            'candidate_email':              candidate.candidate_email,
            'candidate_phone':              candidate.candidate_phone,
            'candidate_url':                candidate.candidate_url,
            'candidate_contact_form_url':   candidate.candidate_contact_form_url,
            'contest_office_id':            candidate.contest_office_id,
            'contest_office_we_vote_id':    candidate.contest_office_we_vote_id,
            'contest_office_name':          candidate.contest_office_name,
            'contest_office_list':          office_list_for_candidate,
            'facebook_url':                 candidate.facebook_url,
            # 'google_civic_candidate_name': candidate.google_civic_candidate_name,
            'google_civic_election_id':     candidate.google_civic_election_id,
            'instagram_handle':             candidate.instagram_handle,
            'instagram_followers_count':    candidate.instagram_followers_count,
            'id':                           candidate.id,
            'kind_of_ballot_item':          CANDIDATE,
            'last_updated':                 date_last_updated,
            'maplight_id':                  candidate.maplight_id,
            'ocd_division_id':              candidate.ocd_division_id,
            'order_on_ballot':              candidate.order_on_ballot,
            'party':                        candidate.political_party_display(),
            'politician_id':                candidate.politician_id,
            'politician_we_vote_id':        candidate.politician_we_vote_id,
            'state_code':                   candidate.state_code,
            'twitter_url':                  candidate.twitter_url,
            'twitter_handle':               candidate.fetch_twitter_handle(),
            'twitter_description':          candidate.twitter_description
            if positive_value_exists(candidate.twitter_description) and
            len(candidate.twitter_description) > 1 else '',
            'twitter_followers_count':      candidate.twitter_followers_count,
            'we_vote_id':                   candidate.we_vote_id,
            'withdrawn_from_election':      candidate.withdrawn_from_election,
            'withdrawal_date':              wdate,
            'youtube_url': candidate.youtube_url,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      CANDIDATE,
            'id':                       candidate_id,
            'we_vote_id':               candidate_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def candidates_retrieve_for_api(office_id=0, office_we_vote_id=''):  # candidatesRetrieve
    """
    Used by the api
    :param office_id:
    :param office_we_vote_id:
    :return:
    """
    # NOTE: Candidates retrieve is independent of *who* wants to see the data. Candidates retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItems does

    if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': 0,
            'candidate_list':           [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    candidate_list = []
    candidates_to_display = []
    google_civic_election_id = 0
    try:
        candidate_list_object = CandidateListManager()
        results = candidate_list_object.retrieve_all_candidates_for_office(
            office_id=office_id,
            office_we_vote_id=office_we_vote_id)
        success = results['success']
        status = results['status']
        candidate_list = results['candidate_list']
    except Exception as e:
        status = 'FAILED candidates_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        candidate_manager = CandidateManager()
        for candidate in candidate_list:
            if not positive_value_exists(candidate.contest_office_name):
                candidate = candidate_manager.refresh_cached_candidate_office_info(candidate)
            wdate = ''
            if isinstance(candidate.withdrawal_date, the_other_datetime.date):
                wdate = candidate.withdrawal_date.strftime("%Y-%m-%d")

            office_list_for_candidate = []
            office_link_results = candidate_manager.retrieve_candidate_to_office_link(
                    candidate_we_vote_id=candidate.we_vote_id,
                    read_only=True)
            if office_link_results['list_found']:
                office_manager = ContestOfficeManager()
                election_manager = ElectionManager()
                candidate_to_office_link_list = office_link_results['candidate_to_office_link_list']
                for candidate_to_office_link in candidate_to_office_link_list:
                    contest_office_name = ''
                    results = office_manager.retrieve_contest_office_from_we_vote_id(
                        candidate_to_office_link.contest_office_we_vote_id)
                    if results['contest_office_found']:
                        contest_office = results['contest_office']
                        if contest_office:
                            contest_office_name = contest_office.office_name
                    election_day_text = ''
                    if positive_value_exists(candidate_to_office_link.google_civic_election_id):
                        results = election_manager.retrieve_election(
                            google_civic_election_id=candidate_to_office_link.google_civic_election_id,
                            read_only=True)
                        if results['election_found']:
                            election = results['election']
                            election_day_text = election.election_day_text
                    one_office_dict = {
                        'contest_office_name':          contest_office_name,
                        'contest_office_we_vote_id':    candidate_to_office_link.contest_office_we_vote_id,
                        'election_day_text':            election_day_text,
                        'google_civic_election_id':     candidate_to_office_link.google_civic_election_id,
                        'state_code':                   candidate_to_office_link.state_code,
                    }
                    office_list_for_candidate.append(one_office_dict)

            # This should match voter_ballot_items_retrieve_for_one_election_for_api (voterBallotItemsRetrieve)
            date_last_updated = ''
            if positive_value_exists(candidate.date_last_updated):
                date_last_updated = candidate.date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
            one_candidate = {
                'status':                       status,
                'success':                      True,
                'id':                           candidate.id,
                'we_vote_id':                   candidate.we_vote_id,
                'ballot_item_display_name':     candidate.display_candidate_name(),
                'ballotpedia_candidate_id':     candidate.ballotpedia_candidate_id,
                'ballotpedia_candidate_summary': candidate.ballotpedia_candidate_summary,
                'ballotpedia_candidate_url':    candidate.ballotpedia_candidate_url,
                'ballotpedia_person_id':        candidate.ballotpedia_person_id,
                'candidate_email':              candidate.candidate_email,
                'candidate_phone':              candidate.candidate_phone,
                'candidate_photo_url_large':    candidate.we_vote_hosted_profile_image_url_large
                if positive_value_exists(candidate.we_vote_hosted_profile_image_url_large)
                else candidate.candidate_photo_url(),
                'candidate_photo_url_medium':   candidate.we_vote_hosted_profile_image_url_medium,
                'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
                'candidate_url':                candidate.candidate_url,
                'candidate_contact_form_url':   candidate.candidate_contact_form_url,
                'contest_office_list':          office_list_for_candidate,
                'contest_office_id':            candidate.contest_office_id,  # Deprecate
                'contest_office_name':          candidate.contest_office_name,  # Deprecate
                'contest_office_we_vote_id':    office_we_vote_id,
                'facebook_url':                 candidate.facebook_url,
                'instagram_followers_count':    candidate.instagram_followers_count,
                'instagram_handle':             candidate.instagram_handle,
                'google_civic_election_id':     candidate.google_civic_election_id,  # Deprecate
                'kind_of_ballot_item':          CANDIDATE,
                'last_updated':                 date_last_updated,
                'maplight_id':                  candidate.maplight_id,
                'ocd_division_id':              candidate.ocd_division_id,
                'order_on_ballot':              candidate.order_on_ballot,
                'party':                        candidate.political_party_display(),
                'politician_id':                candidate.politician_id,
                'politician_we_vote_id':        candidate.politician_we_vote_id,
                'state_code':                   candidate.state_code,
                'twitter_url':                  candidate.twitter_url,
                'twitter_handle':               candidate.fetch_twitter_handle(),
                'twitter_description':          candidate.twitter_description
                if positive_value_exists(candidate.twitter_description) and
                len(candidate.twitter_description) > 1 else '',
                'twitter_followers_count':      candidate.twitter_followers_count,
                'youtube_url':                  candidate.youtube_url,
                'withdrawn_from_election':      candidate.withdrawn_from_election,
                'withdrawal_date':              wdate,
            }
            candidates_to_display.append(one_candidate.copy())
            # Deprecate all of these
            # Capture the office_we_vote_id and google_civic_election_id so we can return
            if not positive_value_exists(office_id) and candidate.contest_office_id:
                office_id = candidate.contest_office_id
            if not positive_value_exists(google_civic_election_id) and candidate.google_civic_election_id:
                google_civic_election_id = candidate.google_civic_election_id

        if len(candidates_to_display):
            status += 'CANDIDATES_RETRIEVED '
        else:
            status += 'NO_CANDIDATES_RETRIEVED '

    json_data = {
        'status':                   status,
        'success':                  success,
        'contest_office_id':        office_id,  # Deprecate
        'contest_office_we_vote_id': office_we_vote_id,
        'google_civic_election_id': google_civic_election_id,  # Deprecate
        'candidate_list':           candidates_to_display,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def refresh_candidate_data_from_master_tables(candidate_we_vote_id):
    # Pull from ContestOffice and TwitterUser tables and update CandidateCampaign table
    twitter_profile_image_url_https = None
    twitter_profile_background_image_url_https = None
    twitter_profile_banner_url_https = None
    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None
    twitter_json = {}
    status = ""

    candidate_manager = CandidateManager()
    candidate = CandidateCampaign()
    twitter_user_manager = TwitterUserManager()

    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=False)
    if not results['candidate_found']:
        status = "REFRESH_CANDIDATE_FROM_MASTER_TABLES-CANDIDATE_NOT_FOUND "
        results = {
            'success':      False,
            'status':       status,
            'candidate':    candidate,
        }
        return results

    candidate = results['candidate']

    # Retrieve twitter user data from TwitterUser Table
    twitter_user_id = candidate.twitter_user_id
    twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_user_id)
    if twitter_user_results['twitter_user_found']:
        twitter_user = twitter_user_results['twitter_user']
        if twitter_user.twitter_handle != candidate.candidate_twitter_handle or \
                twitter_user.twitter_name != candidate.twitter_name or \
                twitter_user.twitter_location != candidate.twitter_location or \
                twitter_user.twitter_followers_count != candidate.twitter_followers_count or \
                twitter_user.twitter_description != candidate.twitter_description:
            twitter_json = {
                'id': twitter_user.twitter_id,
                'screen_name': twitter_user.twitter_handle,
                'name': twitter_user.twitter_name,
                'followers_count': twitter_user.twitter_followers_count,
                'location': twitter_user.twitter_location,
                'description': twitter_user.twitter_description,
            }

    # Retrieve images data from WeVoteImage table
    we_vote_image_list = retrieve_all_images_for_one_candidate(candidate_we_vote_id)
    if len(we_vote_image_list):
        # Retrieve all cached image for this organization
        # TODO 2018-07-03 Right now this is focused on Twitter, but it should also take into consideration Ballotpedia
        for we_vote_image in we_vote_image_list:
            if we_vote_image.kind_of_image_twitter_profile:
                if we_vote_image.kind_of_image_original:
                    twitter_profile_image_url_https = we_vote_image.we_vote_image_url
                if we_vote_image.kind_of_image_large:
                    we_vote_hosted_profile_image_url_large = we_vote_image.we_vote_image_url
                if we_vote_image.kind_of_image_medium:
                    we_vote_hosted_profile_image_url_medium = we_vote_image.we_vote_image_url
                if we_vote_image.kind_of_image_tiny:
                    we_vote_hosted_profile_image_url_tiny = we_vote_image.we_vote_image_url
            elif we_vote_image.kind_of_image_twitter_background and we_vote_image.kind_of_image_original:
                twitter_profile_background_image_url_https = we_vote_image.we_vote_image_url
            elif we_vote_image.kind_of_image_twitter_banner and we_vote_image.kind_of_image_original:
                twitter_profile_banner_url_https = we_vote_image.we_vote_image_url

    # Refresh twitter details in CandidateCampaign
    update_candidate_results = candidate_manager.update_candidate_twitter_details(
        candidate, twitter_json, twitter_profile_image_url_https,
        twitter_profile_background_image_url_https, twitter_profile_banner_url_https,
        we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
        we_vote_hosted_profile_image_url_tiny)
    status += update_candidate_results['status']
    success = update_candidate_results['success']

    # Refresh contest office details in CandidateCampaign
    candidate = candidate_manager.refresh_cached_candidate_office_info(candidate)
    status += "REFRESHED_CANDIDATE_CAMPAIGN_FROM_CONTEST_OFFICE"

    if not positive_value_exists(candidate.politician_id) and \
            positive_value_exists(candidate.politician_we_vote_id):
        politician_manager = PoliticianManager()
        politician_id = politician_manager.fetch_politician_id_from_we_vote_id(candidate.politician_we_vote_id)
        update_values = {
            'politician_id': politician_id,
        }
        results = candidate_manager.update_candidate_row_entry(candidate.we_vote_id, update_values)
        candidate = results['updated_candidate']

    results = {
        'success':      success,
        'status':       status,
        'candidate':    candidate,
    }
    return results


def push_candidate_data_to_other_table_caches(candidate_we_vote_id):
    candidate_manager = CandidateManager()
    results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=False)
    candidate = results['candidate']

    save_position_from_candidate_results = update_all_position_details_from_candidate(candidate)


def retrieve_candidate_photos(we_vote_candidate, force_retrieve=False):
    vote_smart_candidate_exists = False
    vote_smart_candidate_just_retrieved = False
    vote_smart_candidate_photo_exists = False
    vote_smart_candidate_photo_just_retrieved = False

    # Has this candidate already been linked to a Vote Smart candidate?
    candidate_retrieve_results = retrieve_and_match_candidate_from_vote_smart(we_vote_candidate, force_retrieve)

    if positive_value_exists(candidate_retrieve_results['vote_smart_candidate_id']):
        # Bring out the object that now has vote_smart_id attached
        we_vote_candidate = candidate_retrieve_results['we_vote_candidate']
        # Reach out to Vote Smart and retrieve photo URL
        photo_retrieve_results = retrieve_candidate_photo_from_vote_smart(we_vote_candidate)
        status = photo_retrieve_results['status']
        success = photo_retrieve_results['success']
        vote_smart_candidate_exists = True
        vote_smart_candidate_just_retrieved = candidate_retrieve_results['vote_smart_candidate_just_retrieved']

        if success:
            vote_smart_candidate_photo_exists = photo_retrieve_results['vote_smart_candidate_photo_exists']
            vote_smart_candidate_photo_just_retrieved = \
                photo_retrieve_results['vote_smart_candidate_photo_just_retrieved']
    else:
        status = candidate_retrieve_results['status'] + ' '
        status += 'RETRIEVE_CANDIDATE_PHOTOS_NO_CANDIDATE_MATCH'
        success = False

    results = {
        'success':                                      success,
        'status':                                       status,
        'vote_smart_candidate_exists':                  vote_smart_candidate_exists,
        'vote_smart_candidate_just_retrieved':          vote_smart_candidate_just_retrieved,
        'vote_smart_candidate_photo_just_retrieved':    vote_smart_candidate_photo_just_retrieved,
        'vote_smart_candidate_photo_exists':            vote_smart_candidate_photo_exists,
    }

    return results


def candidate_politician_match(we_vote_candidate):
    politician_manager = PoliticianManager()
    status = ''
    success = True

    # Does this candidate already have a we_vote_id for a politician?
    if positive_value_exists(we_vote_candidate.politician_we_vote_id):
        # Find existing politician. No update here for now.
        results = politician_manager.retrieve_politician(we_vote_id=we_vote_candidate.politician_we_vote_id)
        status += results['status']
        if not results['success']:
            results = {
                'success':                  False,
                'status':                   status,
                'politician_list_found':    False,
                'politician_list':          [],
                'politician_found':         False,
                'politician_created':       False,
                'politician':               None,
            }
            return results
        elif results['politician_found']:
            politician = results['politician']
            # Save politician_we_vote_id in we_vote_candidate
            we_vote_candidate.politician_we_vote_id = politician.we_vote_id
            we_vote_candidate.politician_id = politician.id
            we_vote_candidate.save()

            results = {
                'success':                  results['success'],
                'status':                   status,
                'politician_list_found':    False,
                'politician_list':          [],
                'politician_found':         results['politician_found'],
                'politician_created':       False,
                'politician':               results['politician'],
            }
            return results
        else:
            # Politician wasn't found, so clear out politician_we_vote_id and politician_id
            we_vote_candidate.politician_we_vote_id = None
            we_vote_candidate.politician_id = None
            we_vote_candidate.save()

    # Search the politician table for a match
    results = politician_manager.retrieve_all_politicians_that_might_match_candidate(
        candidate_name=we_vote_candidate.candidate_name,
        candidate_twitter_handle=we_vote_candidate.candidate_twitter_handle,
        google_civic_candidate_name=we_vote_candidate.google_civic_candidate_name,
        google_civic_candidate_name2=we_vote_candidate.google_civic_candidate_name2,
        google_civic_candidate_name3=we_vote_candidate.google_civic_candidate_name3,
        maplight_id=we_vote_candidate.maplight_id,
        state_code=we_vote_candidate.state_code,
        vote_smart_id=we_vote_candidate.vote_smart_id,
        vote_usa_politician_id=we_vote_candidate.vote_usa_politician_id,
    )
    status += results['status']
    if not results['success']:
        results = {
            'success':                  False,
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_list_found']:
        # If here, return the list but don't link the candidate
        politician_list = results['politician_list']

        results = {
            'success':                  True,
            'status':                   status,
            'politician_list_found':    True,
            'politician_list':          politician_list,
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_found']:
        # Save this politician_we_vote_id with the candidate
        politician = results['politician']
        # Save politician_we_vote_id in we_vote_candidate
        we_vote_candidate.politician_we_vote_id = politician.we_vote_id
        we_vote_candidate.politician_id = politician.id
        we_vote_candidate.save()

        results = {
            'success':                  True,
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         True,
            'politician_created':       False,
            'politician':               politician,
        }
        return results
    else:
        # Create new politician for this candidate
        create_results = politician_manager.update_or_create_politician_from_candidate(we_vote_candidate)
        status += create_results['status']
        if create_results['politician_found']:
            politician = create_results['politician']
            # Save politician_we_vote_id in we_vote_candidate
            we_vote_candidate.politician_we_vote_id = politician.we_vote_id
            we_vote_candidate.politician_id = politician.id
            we_vote_candidate.save()

        results = {
            'success':                      create_results['success'],
            'status':                       status,
            'politician_list_found':        False,
            'politician_list':              [],
            'politician_found':             create_results['politician_found'],
            'politician_created':           create_results['politician_created'],
            'politician':                   create_results['politician'],
        }
        return results


def retrieve_candidate_politician_match_options(
        vote_smart_id,
        vote_usa_politician_id='',
        maplight_id='',
        candidate_twitter_handle='',
        candidate_name='',
        state_code=''):
    politician_manager = PoliticianManager()
    politician_created = False
    politician_found = False
    politician_list_found = False
    politician_list = []
    status = ""

    # Search the politician table for a match
    results = politician_manager.retrieve_all_politicians_that_might_match_candidate(
        candidate_name=candidate_name,
        candidate_twitter_handle=candidate_twitter_handle,
        maplight_id=maplight_id,
        state_code=state_code,
        vote_smart_id=vote_smart_id,
        vote_usa_politician_id=vote_usa_politician_id,
    )
    if results['politician_list_found']:
        # If here, return
        politician_list = results['politician_list']
        status += results['status']
        results = {
            'success':                  results['success'],
            'status':                   status,
            'politician_list_found':    True,
            'politician_list':          politician_list,
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_found']:
        # Return this politician entry
        politician = results['politician']
        status += results['status']

        results = {
            'success':                  results['success'],
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         True,
            'politician_created':       False,
            'politician':               politician,
        }
        return results

    success = False
    status += "TO_BE_IMPLEMENTED "
    results = {
        'success':                  success,
        'status':                   status,
        'politician_list_found':    politician_list_found,
        'politician_list':          politician_list,
        'politician_found':         politician_found,
        'politician_created':       politician_created,
        'politician':               None,
    }

    return results


def retrieve_candidate_list_for_entire_year(
        candidate_year=0,
        limit_to_this_state_code=''):
    candidate_list_found = False
    candidate_list_light = []
    status = ''
    success = True

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_all_candidates_for_one_year(
            candidate_year=candidate_year,
            limit_to_this_state_code=limit_to_this_state_code,
            search_string=False,
            return_list_of_objects=False,
            read_only=True)
    if results['candidate_list_found']:
        candidate_list_found = True
        candidate_list_light = results['candidate_list_light']
    else:
        status += results['status']
        success = results['success']

    results = {
        'candidate_list_found': candidate_list_found,
        'candidate_list_light': candidate_list_light,
        'status':               status,
        'success':              success,
    }
    return results


def retrieve_candidate_list_for_all_upcoming_elections(upcoming_google_civic_election_id_list=[],
                                                       limit_to_this_state_code="",
                                                       return_list_of_objects=False,
                                                       super_light_candidate_list=False):

    status = ""
    success = True
    candidate_list_objects = []
    candidate_list_light = []
    candidate_list_found = False

    if not upcoming_google_civic_election_id_list \
            or not positive_value_exists(len(upcoming_google_civic_election_id_list)):
        election_manager = ElectionManager()
        election_list_results = \
            election_manager.retrieve_upcoming_google_civic_election_id_list(limit_to_this_state_code)

        upcoming_google_civic_election_id_list = election_list_results['upcoming_google_civic_election_id_list']
        status += election_list_results['status']

    if len(upcoming_google_civic_election_id_list):
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidates_for_specific_elections(
            upcoming_google_civic_election_id_list,
            limit_to_this_state_code=limit_to_this_state_code,
            return_list_of_objects=return_list_of_objects,
            super_light_candidate_list=super_light_candidate_list)
        if results['candidate_list_found']:
            candidate_list_found = True
            candidate_list_light = results['candidate_list_light']
        else:
            status += results['status']
            success = results['success']

    results = {
        'success': success,
        'status': status,
        'candidate_list_found':             candidate_list_found,
        'candidate_list_objects':           candidate_list_objects if return_list_of_objects else [],
        'candidate_list_light':             candidate_list_light,
        'google_civic_election_id_list':    upcoming_google_civic_election_id_list,
        'return_list_of_objects':           return_list_of_objects,
        'super_light_candidate_list':       super_light_candidate_list,
    }
    return results


def retrieve_candidate_list_for_all_prior_elections_this_year(
        prior_google_civic_election_id_list=[],
        limit_to_this_state_code="",
        return_list_of_objects=False,
        super_light_candidate_list=False):

    status = ""
    success = True
    candidate_list_objects = []
    candidate_list_light = []
    candidate_list_found = False

    if not prior_google_civic_election_id_list \
            or not positive_value_exists(len(prior_google_civic_election_id_list)):
        election_manager = ElectionManager()
        election_list_results = \
            election_manager.retrieve_prior_google_civic_election_id_list_this_year(limit_to_this_state_code)

        prior_google_civic_election_id_list = election_list_results['prior_google_civic_election_id_list']
        status += election_list_results['status']

    if len(prior_google_civic_election_id_list):
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidates_for_specific_elections(
            prior_google_civic_election_id_list,
            limit_to_this_state_code=limit_to_this_state_code,
            return_list_of_objects=return_list_of_objects,
            super_light_candidate_list=super_light_candidate_list)
        if results['candidate_list_found']:
            candidate_list_found = True
            candidate_list_light = results['candidate_list_light']
        else:
            status += results['status']
            success = results['success']

    results = {
        'success': success,
        'status': status,
        'candidate_list_found':             candidate_list_found,
        'candidate_list_objects':           candidate_list_objects if return_list_of_objects else [],
        'candidate_list_light':             candidate_list_light,
        'google_civic_election_id_list':    prior_google_civic_election_id_list,
        'return_list_of_objects':           return_list_of_objects,
        'super_light_candidate_list':       super_light_candidate_list,
    }
    return results


def retrieve_next_or_most_recent_office_for_candidate(candidate_we_vote_id=''):
    status = ''
    success = True
    contest_office = None
    contest_office_found = False
    google_civic_election_id = 0

    candidate_list_manager = CandidateListManager()
    candidate_we_vote_id_list = [candidate_we_vote_id]
    link_results = candidate_list_manager.retrieve_candidate_to_office_link_list(
        candidate_we_vote_id_list=candidate_we_vote_id_list)
    candidate_to_office_link_list = link_results['candidate_to_office_link_list']
    link_dict = {}
    for one_link in candidate_to_office_link_list:
        election = one_link.election()
        if election and election.election_day_text:
            link_dict[election.election_day_text] = one_link

    now_as_we_vote_date_string = convert_date_to_we_vote_date_string(now())
    sorted_keys = sorted(link_dict.keys())
    # Start with oldest
    is_first = True
    first_after_now_found = False
    candidate_to_office_link_found = False
    office_we_vote_id = ''
    for election_day_text in sorted_keys:
        if is_first:
            # Default to oldest entry
            candidate_to_office_link = link_dict[election_day_text]
            office_we_vote_id = candidate_to_office_link.contest_office_we_vote_id
            google_civic_election_id = candidate_to_office_link.google_civic_election_id
            candidate_to_office_link_found = True
            is_first = False
        elif election_day_text < now_as_we_vote_date_string:
            # Keep updating as we approach "now"
            candidate_to_office_link = link_dict[election_day_text]
            office_we_vote_id = candidate_to_office_link.contest_office_we_vote_id
            google_civic_election_id = candidate_to_office_link.google_civic_election_id
            candidate_to_office_link_found = True
        else:
            # Once we have passed "now", take the first election (i.e., the next election)
            if not first_after_now_found:
                candidate_to_office_link = link_dict[election_day_text]
                office_we_vote_id = candidate_to_office_link.contest_office_we_vote_id
                google_civic_election_id = candidate_to_office_link.google_civic_election_id
                candidate_to_office_link_found = True
                first_after_now_found = True

    if candidate_to_office_link_found and positive_value_exists(office_we_vote_id):
        contest_office_manager = ContestOfficeManager()
        office_results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)
        contest_office_found = office_results['contest_office_found']
        contest_office = office_results['contest_office']

    results = {
        'success':              success,
        'status':               status,
        'contest_office_found': contest_office_found,
        'contest_office':       contest_office,
        'google_civic_election_id': google_civic_election_id,
    }
    return results


def save_image_to_candidate_table(candidate, image_url, source_link, url_is_broken, kind_of_source_website=None):
    status = ''
    success = True
    cache_results = {
        'we_vote_hosted_profile_image_url_large':   None,
        'we_vote_hosted_profile_image_url_medium':  None,
        'we_vote_hosted_profile_image_url_tiny':    None
    }

    if not positive_value_exists(kind_of_source_website):
        kind_of_source_website = extract_website_from_url(source_link)
    if IMAGE_SOURCE_BALLOTPEDIA in kind_of_source_website:
        # NOT FULLY UPDATED TO WORK
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            ballotpedia_profile_image_url=image_url,
            image_source=IMAGE_SOURCE_BALLOTPEDIA)
        cached_ballotpedia_profile_image_url_https = cache_results['cached_ballotpedia_image_url_https']
        candidate.ballotpedia_photo_url = cached_ballotpedia_profile_image_url_https
        candidate.ballotpedia_page_title = source_link

    elif LINKEDIN in kind_of_source_website:
        # NOT FULLY UPDATED TO WORK
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            linkedin_profile_image_url=image_url,
            image_source=LINKEDIN)
        cached_linkedin_profile_image_url_https = cache_results['cached_linkedin_image_url_https']
        candidate.linkedin_url = source_link
        candidate.linkedin_photo_url = cached_linkedin_profile_image_url_https

    elif WIKIPEDIA in kind_of_source_website:
        # NOT FULLY UPDATED TO WORK
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            wikipedia_profile_image_url=image_url,
            image_source=WIKIPEDIA)
        cached_wikipedia_profile_image_url_https = cache_results['cached_wikipedia_image_url_https']
        candidate.wikipedia_photo_url = cached_wikipedia_profile_image_url_https
        candidate.wikipedia_page_title = source_link

    elif TWITTER in kind_of_source_website:
        # NOT FULLY UPDATED TO WORK
        twitter_screen_name = extract_twitter_handle_from_text_string(source_link)
        candidate.candidate_twitter_handle = twitter_screen_name
        candidate.twitter_url = source_link

    elif FACEBOOK in kind_of_source_website:
        candidate.facebook_url_is_broken = url_is_broken
        if not url_is_broken:
            cache_results = cache_master_and_resized_image(
                candidate_id=candidate.id,
                candidate_we_vote_id=candidate.we_vote_id,
                facebook_profile_image_url_https=image_url,
                image_source=FACEBOOK)
            cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
            candidate.facebook_url = source_link
            candidate.facebook_profile_image_url_https = cached_facebook_profile_image_url_https
            # Store the We Vote cached URL
            candidate.we_vote_hosted_profile_facebook_image_url_large = \
                cache_results['we_vote_hosted_profile_image_url_large']
            candidate.we_vote_hosted_profile_facebook_image_url_medium = \
                cache_results['we_vote_hosted_profile_image_url_medium']
            candidate.we_vote_hosted_profile_facebook_image_url_tiny = \
                cache_results['we_vote_hosted_profile_image_url_tiny']
            # Update the active image
            if candidate.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                candidate.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_FACEBOOK
            if candidate.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                candidate.we_vote_hosted_profile_image_url_large = \
                    cache_results['we_vote_hosted_profile_image_url_large']
                candidate.we_vote_hosted_profile_image_url_medium = \
                    cache_results['we_vote_hosted_profile_image_url_medium']
                candidate.we_vote_hosted_profile_image_url_tiny = \
                    cache_results['we_vote_hosted_profile_image_url_tiny']
        else:
            candidate.facebook_profile_image_url_https = None

    else:
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            other_source_image_url=image_url,
            other_source=kind_of_source_website)
        cached_other_source_image_url_https = cache_results['cached_other_source_image_url_https']
        candidate.other_source_url = source_link
        candidate.other_source_photo_url = cached_other_source_image_url_https

    try:
        candidate.save()
    except Exception as e:
        status += "CANDIDATE_NOT_SAVED: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
    }
    return results


def save_google_search_link_to_candidate_table(candidate, google_search_link):
    google_search_website_name = google_search_link.split("//")[1].split("/")[0]
    if IMAGE_SOURCE_BALLOTPEDIA in google_search_website_name:
        candidate.ballotpedia_page_title = google_search_link
    elif LINKEDIN in google_search_website_name:
        candidate.linkedin_url = google_search_link
    elif WIKIPEDIA in google_search_website_name:
        candidate.wikipedia_page_title = google_search_link
    elif TWITTER in google_search_website_name:
        candidate.twitter_url = google_search_link
    elif FACEBOOK in google_search_website_name:
        candidate.facebook_url = google_search_link
    else:
        candidate.candidate_url = google_search_link
    try:
        candidate.save()
    except Exception as e:
        pass


def find_candidate_endorsements_on_one_candidate_web_page(site_url, endorsement_list_light):
    organization_we_vote_ids_list = []
    endorsement_list_light_modified = []
    measure_we_vote_ids_list = []
    status = ""
    success = False
    if len(site_url) < 10:
        status += 'FIND_ENDORSEMENTS_ON_CANDIDATE_PAGE-PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':                           status,
            'success':                          success,
            'at_least_one_endorsement_found':   False,
            'page_redirected':                  False,
            'endorsement_list_light':           endorsement_list_light_modified,
        }
        return results

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Encoding': 'none',
    # 'Accept-Language': 'en-US,en;q=0.8',
    # 'Connection': 'keep-alive'
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        all_html_raw = page.read()
        all_html = all_html_raw.decode("utf8")
        page.close()
        try:
            all_html_lower_case = all_html.lower()
            for one_ballot_item_dict in endorsement_list_light:
                # Add empty candidate_we_vote_id
                one_ballot_item_dict['candidate_we_vote_id'] = ""
                if positive_value_exists(one_ballot_item_dict['organization_we_vote_id']) \
                        and one_ballot_item_dict['organization_we_vote_id'] \
                        not in organization_we_vote_ids_list:
                    if positive_value_exists(one_ballot_item_dict['organization_name']):
                        if one_ballot_item_dict['organization_name'].lower() in all_html_lower_case:
                            organization_we_vote_ids_list.append(one_ballot_item_dict['organization_we_vote_id'])
                            endorsement_list_light_modified.append(one_ballot_item_dict)
                            continue
                        elif 'alternate_names' in one_ballot_item_dict:
                            alternate_name_found = False
                            alternate_names = one_ballot_item_dict['alternate_names']
                            for organization_name_alternate in alternate_names:
                                if organization_name_alternate.lower() in all_html_lower_case:
                                    organization_we_vote_ids_list.append(
                                        one_ballot_item_dict['organization_we_vote_id'])
                                    endorsement_list_light_modified.append(one_ballot_item_dict)
                                    alternate_name_found = True
                                    break
                            if alternate_name_found:
                                continue
                    if 'organization_website' in one_ballot_item_dict and \
                            positive_value_exists(one_ballot_item_dict['organization_website']):
                        organization_website = one_ballot_item_dict['organization_website'].lower()
                        # Remove the http... from the candidate website
                        organization_website_stripped = extract_website_from_url(organization_website)
                        # Also search for extract_website_from_url
                        if organization_website_stripped not in \
                                ('ballotpedia.org',
                                 'bit.ly',
                                 'en.wikipedia.org',
                                 'facebook.com',
                                 'instagram.com',
                                 'linkedin.com',
                                 'nationbuilder.com',
                                 'secure.actblue.com',
                                 'secure.winred.com',
                                 't.co',
                                 'tinyurl.com',
                                 'twitter.com',
                                 'wix.com',
                                 'wixsite.com',
                                 'wordpress.com',
                                 'youtube.com'):
                            # We strip out straight 'wixsite.com', but not 'candidate.wixsite.com'
                            if organization_website_stripped in all_html_lower_case:
                                organization_we_vote_ids_list.append(
                                    one_ballot_item_dict['organization_we_vote_id'])
                                endorsement_list_light_modified.append(one_ballot_item_dict)
                                continue

        except Exception as error_message:
            status += "SCRAPE_ONE_LINE_ERROR: {error_message}".format(error_message=error_message)

        success = True
        status += "FINISHED_SCRAPING_PAGE "
    except timeout:
        status += "ENDORSEMENTS-WEB_PAGE_SCRAPE_TIMEOUT_ERROR "
        success = False
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "SCRAPE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "SCRAPE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    at_least_one_endorsement_found = positive_value_exists(len(organization_we_vote_ids_list)) \
        or positive_value_exists(len(measure_we_vote_ids_list))
    results = {
        'status':                           status,
        'success':                          success,
        'at_least_one_endorsement_found':   at_least_one_endorsement_found,
        'page_redirected':                  False,
        'endorsement_list_light':           endorsement_list_light_modified,
    }
    return results


def find_candidate_endorsements_on_one_candidate_web_page(site_url, endorsement_list_light):
    organization_we_vote_ids_list = []
    endorsement_list_light_modified = []
    measure_we_vote_ids_list = []
    status = ""
    success = False
    if len(site_url) < 10:
        status += 'FIND_ENDORSEMENTS_ON_CANDIDATE_PAGE-PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':                           status,
            'success':                          success,
            'at_least_one_endorsement_found':   False,
            'page_redirected':                  False,
            'endorsement_list_light':           endorsement_list_light_modified,
        }
        return results

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Encoding': 'none',
    # 'Accept-Language': 'en-US,en;q=0.8',
    # 'Connection': 'keep-alive'
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        all_html_raw = page.read()
        all_html = all_html_raw.decode("utf8")
        page.close()
        try:
            all_html_lower_case = all_html.lower()
            for one_ballot_item_dict in endorsement_list_light:
                # Add empty candidate_we_vote_id
                one_ballot_item_dict['candidate_we_vote_id'] = ""
                if positive_value_exists(one_ballot_item_dict['organization_we_vote_id']) \
                        and one_ballot_item_dict['organization_we_vote_id'] \
                        not in organization_we_vote_ids_list:
                    if positive_value_exists(one_ballot_item_dict['organization_name']):
                        if one_ballot_item_dict['organization_name'].lower() in all_html_lower_case:
                            organization_we_vote_ids_list.append(one_ballot_item_dict['organization_we_vote_id'])
                            endorsement_list_light_modified.append(one_ballot_item_dict)
                            continue
                        elif 'alternate_names' in one_ballot_item_dict:
                            alternate_name_found = False
                            alternate_names = one_ballot_item_dict['alternate_names']
                            for organization_name_alternate in alternate_names:
                                if organization_name_alternate.lower() in all_html_lower_case:
                                    organization_we_vote_ids_list.append(
                                        one_ballot_item_dict['organization_we_vote_id'])
                                    endorsement_list_light_modified.append(one_ballot_item_dict)
                                    alternate_name_found = True
                                    break
                            if alternate_name_found:
                                continue
                    if 'organization_website' in one_ballot_item_dict and \
                            positive_value_exists(one_ballot_item_dict['organization_website']):
                        organization_website = one_ballot_item_dict['organization_website'].lower()
                        # Remove the http... from the candidate website
                        organization_website_stripped = extract_website_from_url(organization_website)
                        if organization_website_stripped not in \
                                ('ballotpedia.org',
                                 'bit.ly',
                                 'en.wikipedia.org',
                                 'facebook.com',
                                 'instagram.com',
                                 'linkedin.com',
                                 'nationbuilder.com',
                                 'secure.actblue.com',
                                 'secure.winred.com',
                                 't.co',
                                 'tinyurl.com',
                                 'twitter.com',
                                 'wix.com',
                                 'wixsite.com',
                                 'wordpress.com',
                                 'youtube.com'):
                            # We strip out straight 'wixsite.com', but not 'candidate.wixsite.com'
                            if organization_website_stripped in all_html_lower_case:
                                organization_we_vote_ids_list.append(
                                    one_ballot_item_dict['organization_we_vote_id'])
                                endorsement_list_light_modified.append(one_ballot_item_dict)
                                continue

        except Exception as error_message:
            status += "SCRAPE_ONE_LINE_ERROR: {error_message}".format(error_message=error_message)

        success = True
        status += "FINISHED_SCRAPING_PAGE "
    except timeout:
        status += "ENDORSEMENTS-WEB_PAGE_SCRAPE_TIMEOUT_ERROR "
        success = False
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "SCRAPE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "SCRAPE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    at_least_one_endorsement_found = positive_value_exists(len(organization_we_vote_ids_list)) \
        or positive_value_exists(len(measure_we_vote_ids_list))
    results = {
        'status':                           status,
        'success':                          success,
        'at_least_one_endorsement_found':   at_least_one_endorsement_found,
        'page_redirected':                  False,
        'endorsement_list_light':           endorsement_list_light_modified,
    }
    return results


def find_organization_endorsements_of_candidates_on_one_web_page(site_url, endorsement_list_light):
    status = ""
    success = False
    at_least_one_endorsement_found = False
    endorsement_list_light_modified = []
    if len(site_url) < 10:
        status = 'FIND_ENDORSEMENTS-PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':                           status,
            'success':                          success,
            'at_least_one_endorsement_found':   False,
            'page_redirected':                  False,
            'endorsement_list_light':           endorsement_list_light_modified,
        }
        return results

    if site_url.lower().endswith(".pdf"):
        print("PDF Detected ", site_url)
        response = process_pdf_to_html(site_url)
        if positive_value_exists(response['s3_url_for_html']):
            # Overwrite the the site_url parameter, with a url to an html representation of the PDF file
            site_url = response['s3_url_for_html']

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Encoding': 'none',
    # 'Accept-Language': 'en-US,en;q=0.8',
    # 'Connection': 'keep-alive'
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        all_html_raw = page.read()
        all_html = all_html_raw.decode("utf8")
        page.close()
        all_html_lower_case = all_html.lower()
        scan_results = organization_endorsements_scanner(endorsement_list_light, all_html_lower_case)
        status += scan_results['status']
        success = scan_results['success']
        endorsement_list_light_modified = scan_results['endorsement_list_light']
        # at_least_one_endorsement_found = scan_results['at_least_one_endorsement_found']

        status += "FINISHED_SCRAPING_PAGE "
    except timeout:
        status += "ENDORSEMENTS-WEB_PAGE_SCRAPE_TIMEOUT_ERROR "
        success = False
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "SCRAPE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "SCRAPE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    reorder_results = reorder_endorsement_list_to_match_candidates_on_one_web_page(
        site_url, endorsement_list_light_modified)
    if reorder_results['success']:
        endorsement_list_light_modified = reorder_results['endorsement_list_light']
        at_least_one_endorsement_found = reorder_results['at_least_one_endorsement_found']

    results = {
        'status':                           status,
        'success':                          success,
        'at_least_one_endorsement_found':   at_least_one_endorsement_found,
        'page_redirected':                  False,
        'endorsement_list_light':           endorsement_list_light_modified,
    }
    return results


def organization_endorsements_scanner(endorsement_list_light, text_to_search_lower_case,
                                      candidate_we_vote_ids_list=[], measure_we_vote_ids_list=[]):
    """
    Take the list of candidates and measures (in endorsement_list_light) and search the text_to_search_lower_case
    provided. Return the ones found.
    :param endorsement_list_light:
    :param text_to_search_lower_case:
    :param candidate_we_vote_ids_list:
    :param measure_we_vote_ids_list:
    :return:
    """
    endorsement_list_light_modified = []
    status = ""
    success = True
    try:
        for one_ballot_item_dict in endorsement_list_light:
            # Add empty organization_we_vote_id
            one_ballot_item_dict['organization_we_vote_id'] = ""
            # Hanging off each ballot_item_dict is a alternate_names that includes
            #  shortened alternative names that we should check against all_html_lower_case
            if positive_value_exists(one_ballot_item_dict['measure_we_vote_id']) \
                    and one_ballot_item_dict['measure_we_vote_id'] not in measure_we_vote_ids_list:
                if positive_value_exists(one_ballot_item_dict['ballot_item_display_name']):
                    ballot_item_display_name_lower = one_ballot_item_dict['ballot_item_display_name'].lower()
                    if ballot_item_display_name_lower in text_to_search_lower_case:
                        measure_we_vote_ids_list.append(one_ballot_item_dict['measure_we_vote_id'])
                        endorsement_list_light_modified.append(one_ballot_item_dict)
                        continue
                if 'alternate_names' in one_ballot_item_dict:
                    alternate_names = one_ballot_item_dict['alternate_names']
                    for ballot_item_display_name_alternate in alternate_names:
                        if ballot_item_display_name_alternate in text_to_search_lower_case:
                            measure_we_vote_ids_list.append(one_ballot_item_dict['measure_we_vote_id'])
                            endorsement_list_light_modified.append(one_ballot_item_dict)
                            continue
            elif positive_value_exists(one_ballot_item_dict['candidate_we_vote_id']) \
                    and one_ballot_item_dict['candidate_we_vote_id'] not in candidate_we_vote_ids_list:
                if positive_value_exists(one_ballot_item_dict['ballot_item_display_name']):
                    ballot_item_display_name_lower = one_ballot_item_dict['ballot_item_display_name'].lower()
                    if ballot_item_display_name_lower in text_to_search_lower_case:
                        candidate_we_vote_ids_list.append(one_ballot_item_dict['candidate_we_vote_id'])
                        endorsement_list_light_modified.append(one_ballot_item_dict)
                        continue
                if 'ballot_item_website' in one_ballot_item_dict and \
                        positive_value_exists(one_ballot_item_dict['ballot_item_website']):
                    ballot_item_website = one_ballot_item_dict['ballot_item_website'].lower()
                    # Remove the http... from the candidate website
                    ballot_item_website_stripped = extract_website_from_url(ballot_item_website)
                    if ballot_item_website_stripped not in \
                            ('ballotpedia.org',
                             'bit.ly',
                             'en.wikipedia.org',
                             'facebook.com',
                             'instagram.com',
                             'linkedin.com',
                             'nationbuilder.com',
                             'secure.actblue.com',
                             'secure.winred.com',
                             't.co',
                             'tinyurl.com',
                             'twitter.com',
                             'wix.com',
                             'wixsite.com',
                             'wordpress.com',
                             'youtube.com'):
                        # We strip out straight 'wixsite.com', but not 'candidate.wixsite.com'
                        if ballot_item_website_stripped in text_to_search_lower_case:
                            candidate_we_vote_ids_list.append(one_ballot_item_dict['candidate_we_vote_id'])
                            endorsement_list_light_modified.append(one_ballot_item_dict)
                            continue
                if 'alternate_names' in one_ballot_item_dict:
                    alternate_name_found = False
                    for ballot_item_display_name_alternate in one_ballot_item_dict['alternate_names']:
                        if ballot_item_display_name_alternate.lower() in text_to_search_lower_case:
                            candidate_we_vote_ids_list.append(one_ballot_item_dict['candidate_we_vote_id'])
                            endorsement_list_light_modified.append(one_ballot_item_dict)
                            alternate_name_found = True
                            break
                    if alternate_name_found:
                        continue
            else:
                testing = 1
    except Exception as error_message:
        status += "SCRAPE_ONE_LINE_ERROR: {error_message}".format(error_message=error_message)

    at_least_one_endorsement_found = positive_value_exists(len(candidate_we_vote_ids_list)) \
        or positive_value_exists(len(measure_we_vote_ids_list))

    results = {
        'status':                           status,
        'success':                          success,
        'at_least_one_endorsement_found':   at_least_one_endorsement_found,
        'page_redirected':                  False,
        'endorsement_list_light':           endorsement_list_light_modified,
        'candidate_we_vote_ids_list':       candidate_we_vote_ids_list,
        'measure_we_vote_ids_list':         measure_we_vote_ids_list,
    }
    return results


def reorder_endorsement_list_to_match_candidates_on_one_web_page(site_url, endorsement_list_light):
    candidate_we_vote_ids_list = []
    endorsement_list_light_modified = []
    measure_we_vote_ids_list = []
    status = ""
    success = False

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        all_lines = page.readlines()
        page.close()
        for one_line in all_lines:
            one_line_decoded = one_line.decode()
            try:
                one_line_decoded_lower_case = one_line_decoded.lower()
                scan_results = organization_endorsements_scanner(
                    endorsement_list_light, one_line_decoded_lower_case,
                    candidate_we_vote_ids_list=candidate_we_vote_ids_list,
                    measure_we_vote_ids_list=measure_we_vote_ids_list)
                status += scan_results['status']
                endorsement_list_light_new_segment = scan_results['endorsement_list_light']
                endorsement_list_light_modified += endorsement_list_light_new_segment
                candidate_we_vote_ids_list = scan_results['candidate_we_vote_ids_list']
                measure_we_vote_ids_list = scan_results['measure_we_vote_ids_list']

            except Exception as error_message:
                status += "SCRAPE_ONE_LINE_ERROR: {error_message}".format(error_message=error_message)

        success = True
        status += "FINISHED_SCRAPING_PAGE "
    except timeout:
        status += "ENDORSEMENTS-WEB_PAGE_SCRAPE_TIMEOUT_ERROR "
        success = False
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "SCRAPE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "SCRAPE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    at_least_one_endorsement_found = positive_value_exists(len(candidate_we_vote_ids_list)) \
        or positive_value_exists(len(measure_we_vote_ids_list))
    results = {
        'status':                           status,
        'success':                          success,
        'at_least_one_endorsement_found':   at_least_one_endorsement_found,
        'page_redirected':                  False,
        'endorsement_list_light':           endorsement_list_light_modified,
    }
    return results
