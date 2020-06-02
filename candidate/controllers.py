# candidate/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CandidateCampaignListManager, CandidateCampaign, CandidateCampaignManager, \
    CANDIDATE_UNIQUE_IDENTIFIERS
from ballot.models import CANDIDATE
from bookmark.models import BookmarkItemList
from config.base import get_environment_variable
import datetime as the_other_datetime
from django.http import HttpResponse
from election.models import ElectionManager
from exception.models import handle_exception
from image.controllers import retrieve_all_images_for_one_candidate, cache_master_and_resized_image, \
    BALLOTPEDIA_IMAGE_SOURCE, \
    LINKEDIN, TWITTER, WIKIPEDIA, FACEBOOK
from import_export_vote_smart.controllers import retrieve_and_match_candidate_from_vote_smart, \
    retrieve_candidate_photo_from_vote_smart
import json
from office.models import ContestOfficeManager
from politician.models import PoliticianManager
from position.controllers import move_positions_to_another_candidate, update_all_position_details_from_candidate
import re
from socket import timeout
from twitter.models import TwitterUserManager
import urllib.request
import wevote_functions.admin
from wevote_functions.functions import add_period_to_middle_name_initial, add_period_to_name_prefix_and_suffix, \
    convert_to_political_party_constant, positive_value_exists, process_request_from_master, convert_to_int, \
    extract_twitter_handle_from_text_string, extract_website_from_url, \
    remove_period_from_middle_name_initial, remove_period_from_name_prefix_and_suffix

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
CANDIDATES_SYNC_URL = get_environment_variable("CANDIDATES_SYNC_URL")  # candidatesSyncOut


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


def add_candidate_name_to_next_spot(candidate_to_update, google_civic_candidate_name_to_add):

    if not positive_value_exists(google_civic_candidate_name_to_add):
        return candidate_to_update

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

    if not positive_value_exists(candidate_to_update.google_civic_candidate_name):
        candidate_to_update.google_civic_candidate_name = google_civic_candidate_name_to_add
    elif google_civic_candidate_name_to_add == candidate_to_update.google_civic_candidate_name:
        # The value is already stored in candidate_to_update.google_civic_candidate_name so doesn't need
        # to be added anywhere below
        pass
    elif name_changed and candidate_to_update.google_civic_candidate_name == google_civic_candidate_name_modified:
        # If candidate_to_update.google_civic_candidate_name has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif not positive_value_exists(candidate_to_update.google_civic_candidate_name2):
        candidate_to_update.google_civic_candidate_name2 = google_civic_candidate_name_to_add
    elif google_civic_candidate_name_to_add == candidate_to_update.google_civic_candidate_name2:
        # The value is already stored in candidate_to_update.google_civic_candidate_name2 so doesn't need
        # to be added to candidate_to_update.google_civic_candidate_name3
        pass
    elif name_changed and candidate_to_update.google_civic_candidate_name2 == google_civic_candidate_name_modified:
        # If candidate_to_update.google_civic_candidate_name2 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif not positive_value_exists(candidate_to_update.google_civic_candidate_name3):
        candidate_to_update.google_civic_candidate_name3 = google_civic_candidate_name_to_add
    elif google_civic_candidate_name_to_add == candidate_to_update.google_civic_candidate_name3:
        # The value is already stored in candidate_to_update.google_civic_candidate_name2 so doesn't need
        # to be added to candidate_to_update.google_civic_candidate_name3
        pass
    elif name_changed and candidate_to_update.google_civic_candidate_name3 == google_civic_candidate_name_modified:
        # If candidate_to_update.google_civic_candidate_name3 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    # We only support 3 alternate candidate names so far
    # elif not positive_value_exists(candidate_to_update.google_civic_candidate_name4):
    #     candidate_to_update.google_civic_candidate_name4 = google_civic_candidate_name_to_add
    # elif google_civic_candidate_name_to_add == candidate_to_update.google_civic_candidate_name4:
    #     # The value is already stored in candidate_to_update.google_civic_candidate_name2 so doesn't need
    #     # to be added to candidate_to_update.google_civic_candidate_name3
    #     pass
    # elif name_changed and candidate_to_update.google_civic_candidate_name4 == google_civic_candidate_name_modified:
    #     # If candidate_to_update.google_civic_candidate_name4 has a middle initial with/without a period
    #     # don't store it if the alternate without/with the period already is stored
    #     pass
    # elif not positive_value_exists(candidate_to_update.google_civic_candidate_name5):
    #     candidate_to_update.google_civic_candidate_name5 = google_civic_candidate_name_to_add
    # # We currently only support 5 alternate names
    return candidate_to_update


def candidates_import_from_sample_file():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Load saved json from local file
    logger.info("Loading CandidateCampaigns from local file")

    with open("candidate/import_data/candidate_campaigns_sample.json") as json_data:
        structured_json = json.load(json_data)

    return candidates_import_from_structured_json(structured_json)


def candidates_import_from_master_server(request, google_civic_election_id='', state_code=''):
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
        results = filter_candidates_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        import_results = candidates_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed

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

    # Search for other candidates within this election that match name and election
    candidate_campaign_list_manager = CandidateCampaignListManager()
    return candidate_campaign_list_manager.fetch_candidates_from_non_unique_identifiers_count(
        we_vote_candidate.google_civic_election_id, we_vote_candidate.state_code,
        we_vote_candidate.candidate_twitter_handle, we_vote_candidate.candidate_name, ignore_candidate_id_list)


def find_duplicate_candidate(we_vote_candidate, ignore_candidate_id_list):
    if not hasattr(we_vote_candidate, 'google_civic_election_id'):
        error_results = {
            'success':                              False,
            'status':                               "FIND_DUPLICATE_CANDIDATE_MISSING_CANDIDATE_OBJECT",
            'candidate_merge_possibility_found':    False,
            'candidate_list':                       [],
        }
        return error_results

    if not positive_value_exists(we_vote_candidate.google_civic_election_id):
        error_results = {
            'success':                              False,
            'status':                               "FIND_DUPLICATE_CANDIDATE_MISSING_GOOGLE_CIVIC_ELECTION_ID",
            'candidate_merge_possibility_found':    False,
            'candidate_list':                       [],
        }
        return error_results

    # Search for other candidates within this election that match name and election
    candidate_campaign_list_manager = CandidateCampaignListManager()
    try:
        google_civic_election_id_list = [we_vote_candidate.google_civic_election_id]
        results = candidate_campaign_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list, we_vote_candidate.state_code,
            we_vote_candidate.candidate_twitter_handle, we_vote_candidate.candidate_name, ignore_candidate_id_list)

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
            elif candidate1_attribute_value is None or candidate1_attribute_value is "":
                candidate_merge_conflict_values[attribute] = 'CANDIDATE2'
            elif candidate2_attribute_value is None or candidate2_attribute_value is "":
                candidate_merge_conflict_values[attribute] = 'CANDIDATE1'
            else:
                if attribute == "candidate_name" or attribute == "state_code":
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
    status = "MERGE_IF_DUPLICATE "
    candidates_merged = False
    decisions_required = False
    candidate1_we_vote_id = candidate1_on_stage.we_vote_id
    candidate2_we_vote_id = candidate2_on_stage.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        if attribute is "we_vote_hosted_profile_image_url_large" \
                or attribute is "we_vote_hosted_profile_image_url_medium" \
                or attribute is "we_vote_hosted_profile_image_url_tiny":
            if positive_value_exists(getattr(candidate1_on_stage, attribute)):
                # We can proceed because candidate1 has a valid image, so we can default to choosing that one
                pass
            elif positive_value_exists(getattr(candidate2_on_stage, attribute)):
                # If we are here candidate1 does NOT have image, but candidate2 does
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                decisions_required = True
                break
            elif conflict_value == "CANDIDATE2":
                merge_choices[attribute] = getattr(candidate2_on_stage, attribute)

    if not decisions_required:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = merge_these_two_candidates(candidate1_we_vote_id, candidate2_we_vote_id, merge_choices,
                                                   candidate1_on_stage, candidate2_on_stage)

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


def merge_these_two_candidates(candidate1_we_vote_id, candidate2_we_vote_id, admin_merge_choices={},
                               candidate1_on_stage=None, candidate2_on_stage=None):
    """
    Process the merging of two candidates
    :param candidate1_we_vote_id:
    :param candidate2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :param candidate1_on_stage: The first candidate object if we have it
    :param candidate2_on_stage: The second candidate object if we have it
    :return:
    """
    status = ""
    candidate_campaign_manager = CandidateCampaignManager()

    if candidate1_on_stage and candidate1_on_stage.we_vote_id:
        candidate1_id = candidate1_on_stage.id
        candidate1_we_vote_id = candidate1_on_stage.we_vote_id
    else:
        # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
        candidate1_results = \
            candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate1_we_vote_id)
        if candidate1_results['candidate_campaign_found']:
            candidate1_on_stage = candidate1_results['candidate_campaign']
            candidate1_id = candidate1_on_stage.id
        else:
            results = {
                'success': False,
                'status': "MERGE_THESE_TWO_CANDIDATES-COULD_NOT_RETRIEVE_CANDIDATE1 ",
                'candidates_merged': False,
                'candidate': None,
            }
            return results

    if candidate2_on_stage and candidate2_on_stage.we_vote_id:
        candidate2_id = candidate2_on_stage.id
        candidate2_we_vote_id = candidate2_on_stage.we_vote_id
    else:
        candidate2_results = \
            candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate2_we_vote_id)
        if candidate2_results['candidate_campaign_found']:
            candidate2_on_stage = candidate2_results['candidate_campaign']
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
            status += "COULD_NOT_UPDATE_POLITICIAN_FOR_CANDIDATE2 "
        candidate1_on_stage.politician_we_vote_id = politician2_we_vote_id
        candidate1_on_stage.politician_id = politician2_id
    # else do nothing (no parent politician for candidate 2)

    # TODO: Migrate bookmarks
    bookmark_item_list_manager = BookmarkItemList()
    bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_candidate(candidate2_we_vote_id)
    if bookmark_results['bookmark_item_list_found']:
        status += "Bookmarks found for Candidate 2 - automatic merge not working yet. "
        results = {
            'success': True,
            'status': status,
            'candidates_merged': False,
            'candidate': None,
        }
        return results

    # Merge attribute values chosen by the admin
    for attribute in CANDIDATE_UNIQUE_IDENTIFIERS:
        if attribute in admin_merge_choices:
            setattr(candidate1_on_stage, attribute, admin_merge_choices[attribute])

    # Preserve unique google_civic_candidate_name, _name2, _name3, _name4, and _name5
    if positive_value_exists(candidate2_on_stage.google_civic_candidate_name):
        candidate1_on_stage = add_candidate_name_to_next_spot(
            candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name)
    if positive_value_exists(candidate2_on_stage.google_civic_candidate_name2):
        candidate1_on_stage = add_candidate_name_to_next_spot(
            candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name2)
    if positive_value_exists(candidate2_on_stage.google_civic_candidate_name3):
        candidate1_on_stage = add_candidate_name_to_next_spot(
            candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name3)
    # DALE 2018-07-09 We don't offer
    # if positive_value_exists(candidate2_on_stage.google_civic_candidate_name4):
    #     candidate1_on_stage = add_candidate_name_to_next_spot(
    #         candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name4)
    # if positive_value_exists(candidate2_on_stage.google_civic_candidate_name5):
    #     candidate1_on_stage = add_candidate_name_to_next_spot(
    #         candidate1_on_stage, candidate2_on_stage.google_civic_candidate_name5)

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

    # Note: wait to wrap in try/except block
    candidate1_on_stage.save()
    refresh_candidate_data_from_master_tables(candidate1_on_stage.we_vote_id)

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
                                      to_contest_office_id, to_contest_office_we_vote_id,
                                      updated_contest_office):
    status = ''
    success = True
    candidate_entries_moved = 0
    candidate_entries_not_moved = 0
    candidate_campaign_manager = CandidateCampaignManager()
    candidate_campaign_list_manager = CandidateCampaignListManager()

    # We search on both from_office_id and from_office_we_vote_id in case there is some data that needs
    # to be healed
    all_candidates_results = candidate_campaign_list_manager.retrieve_all_candidates_for_office(
        office_we_vote_id=from_contest_office_we_vote_id)
    from_candidate_list = all_candidates_results['candidate_list']
    for from_candidate_entry in from_candidate_list:
        try:
            from_candidate_entry.contest_office_id = to_contest_office_id
            from_candidate_entry.contest_office_we_vote_id = to_contest_office_we_vote_id
            from_candidate_entry.save()
            candidate_entries_moved += 1
            candidate_campaign_manager.refresh_cached_candidate_office_info(from_candidate_entry,
                                                                            updated_contest_office)
        except Exception as e:
            success = False
            status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_SAVE_NEW_CANDIDATE "
            candidate_entries_not_moved += 1

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
    candidate_list_manager = CandidateCampaignListManager()
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
            we_vote_id_from_master)

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


def candidates_import_from_structured_json(structured_json):
    candidate_campaign_manager = CandidateCampaignManager()
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
                and positive_value_exists(we_vote_id) and positive_value_exists(contest_office_id):
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False
        if proceed_to_update_or_create:
            updated_candidate_values = {
                'google_civic_election_id': google_civic_election_id,
                'ocd_division_id': ocd_division_id,
                'contest_office_id': contest_office_id,
                'contest_office_we_vote_id': contest_office_we_vote_id,
                'candidate_name': candidate_name,
                'we_vote_id': we_vote_id,
            }
            if 'ballotpedia_candidate_id' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_id'] = one_candidate['ballotpedia_candidate_id']
            if 'ballotpedia_candidate_name' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_name'] = one_candidate['ballotpedia_candidate_name']
            if 'ballotpedia_candidate_summary' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_summary'] = \
                    one_candidate['ballotpedia_candidate_summary']
            if 'ballotpedia_candidate_url' in one_candidate:
                updated_candidate_values['ballotpedia_candidate_url'] = one_candidate['ballotpedia_candidate_url']
            if 'ballotpedia_election_id' in one_candidate:
                updated_candidate_values['ballotpedia_election_id'] = one_candidate['ballotpedia_election_id']
            if 'ballotpedia_image_id' in one_candidate:
                updated_candidate_values['ballotpedia_image_id'] = one_candidate['ballotpedia_image_id']
            if 'ballotpedia_office_id' in one_candidate:
                updated_candidate_values['ballotpedia_office_id'] = one_candidate['ballotpedia_office_id']
            if 'ballotpedia_page_title' in one_candidate:
                updated_candidate_values['ballotpedia_page_title'] = one_candidate['ballotpedia_page_title']
            if 'ballotpedia_photo_url' in one_candidate:
                updated_candidate_values['ballotpedia_photo_url'] = one_candidate['ballotpedia_photo_url']
            if 'ballotpedia_person_id' in one_candidate:
                updated_candidate_values['ballotpedia_person_id'] = one_candidate['ballotpedia_person_id']
            if 'ballotpedia_race_id' in one_candidate:
                updated_candidate_values['ballotpedia_race_id'] = one_candidate['ballotpedia_race_id']
            if 'ballot_guide_official_statement' in one_candidate:
                updated_candidate_values['ballot_guide_official_statement'] = \
                    one_candidate['ballot_guide_official_statement']
            if 'candidate_email' in one_candidate:
                updated_candidate_values['candidate_email'] = one_candidate['candidate_email']
            if 'candidate_gender' in one_candidate:
                updated_candidate_values['candidate_gender'] = one_candidate['candidate_gender']
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
            if 'candidate_url' in one_candidate:
                updated_candidate_values['candidate_url'] = one_candidate['candidate_url']
            if 'candidate_contact_form_url' in one_candidate:
                updated_candidate_values['candidate_contact_form_url'] = one_candidate['candidate_contact_form_url']
            if 'contest_office_name' in one_candidate:
                updated_candidate_values['contest_office_name'] = one_candidate['contest_office_name']
            if 'crowdpac_candidate_id' in one_candidate:
                updated_candidate_values['crowdpac_candidate_id'] = one_candidate['crowdpac_candidate_id']
            if 'facebook_url' in one_candidate:
                updated_candidate_values['facebook_url'] = one_candidate['facebook_url']
            if 'google_civic_candidate_name' in one_candidate:
                updated_candidate_values['google_civic_candidate_name'] = \
                    one_candidate['google_civic_candidate_name']
            if 'google_civic_candidate_name2' in one_candidate:
                updated_candidate_values['google_civic_candidate_name2'] = \
                    one_candidate['google_civic_candidate_name2']
            if 'google_civic_candidate_name3' in one_candidate:
                updated_candidate_values['google_civic_candidate_name3'] = \
                    one_candidate['google_civic_candidate_name3']
            if 'maplight_id' in one_candidate:
                updated_candidate_values['maplight_id'] = one_candidate['maplight_id']
            if 'order_on_ballot' in one_candidate:
                updated_candidate_values['order_on_ballot'] = one_candidate['order_on_ballot']
            if 'party' in one_candidate:
                updated_candidate_values['party'] = one_candidate['party']
            if 'politician_we_vote_id' in one_candidate:
                updated_candidate_values['politician_we_vote_id'] = one_candidate['politician_we_vote_id']
            if 'state_code' in one_candidate:
                updated_candidate_values['state_code'] = one_candidate['state_code']
            if 'photo_url' in one_candidate:
                updated_candidate_values['photo_url'] = one_candidate['photo_url']
            if 'photo_url_from_maplight' in one_candidate:
                updated_candidate_values['photo_url_from_maplight'] = one_candidate['photo_url_from_maplight']
            if 'photo_url_from_vote_smart' in one_candidate:
                updated_candidate_values['photo_url_from_vote_smart'] = \
                    one_candidate['photo_url_from_vote_smart']
            if 'twitter_url' in one_candidate:
                updated_candidate_values['twitter_url'] = one_candidate['twitter_url']
            if 'youtube_url' in one_candidate:
                updated_candidate_values['youtube_url'] = one_candidate['youtube_url']
            if 'twitter_user_id' in one_candidate:
                updated_candidate_values['twitter_user_id'] = one_candidate['twitter_user_id']
            if 'twitter_name' in one_candidate:
                updated_candidate_values['twitter_name'] = one_candidate['twitter_name']
            if 'twitter_location' in one_candidate:
                updated_candidate_values['twitter_location'] = one_candidate['twitter_location']
            if 'twitter_followers_count' in one_candidate:
                updated_candidate_values['twitter_followers_count'] = one_candidate['twitter_followers_count']
            if 'twitter_profile_image_url_https' in one_candidate:
                updated_candidate_values['twitter_profile_image_url_https'] = \
                    one_candidate['twitter_profile_image_url_https']
            if 'twitter_description' in one_candidate:
                updated_candidate_values['twitter_description'] = one_candidate['twitter_description']
            if 'vote_smart_id' in one_candidate:
                updated_candidate_values['vote_smart_id'] = one_candidate['vote_smart_id']
            if 'we_vote_hosted_profile_image_url_large' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_image_url_large'] = \
                    one_candidate['we_vote_hosted_profile_image_url_large']
            if 'we_vote_hosted_profile_image_url_medium' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_image_url_medium'] = \
                    one_candidate['we_vote_hosted_profile_image_url_medium']
            if 'we_vote_hosted_profile_image_url_tiny' in one_candidate:
                updated_candidate_values['we_vote_hosted_profile_image_url_tiny'] = \
                    one_candidate['we_vote_hosted_profile_image_url_tiny']
            if 'wikipedia_page_id' in one_candidate:
                updated_candidate_values['wikipedia_page_id'] = one_candidate['wikipedia_page_id']
            if 'wikipedia_page_title' in one_candidate:
                updated_candidate_values['wikipedia_page_title'] = one_candidate['wikipedia_page_title']
            if 'wikipedia_photo_url' in one_candidate:
                updated_candidate_values['wikipedia_photo_url'] = one_candidate['wikipedia_photo_url']

            results = candidate_campaign_manager.update_or_create_candidate_campaign(
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
    candidate_campaign_manager = CandidateCampaignManager()
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
            results = candidate_campaign_manager.get_or_create_candidate_to_office_link(
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

    candidate_manager = CandidateCampaignManager()
    if positive_value_exists(candidate_id):
        results = candidate_manager.retrieve_candidate_campaign_from_id(candidate_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(candidate_we_vote_id):
        results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
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
        candidate_campaign = results['candidate_campaign']
        wdate = ''
        if isinstance(candidate_campaign.withdrawal_date, the_other_datetime.date):
            wdate = candidate_campaign.withdrawal_date.strftime("%Y-%m-%d")
        if not positive_value_exists(candidate_campaign.contest_office_name):
            candidate_campaign = candidate_manager.refresh_cached_candidate_office_info(candidate_campaign)
        json_data = {
            'status':                       status,
            'success':                      True,
            'kind_of_ballot_item':          CANDIDATE,
            'id':                           candidate_campaign.id,
            'we_vote_id':                   candidate_campaign.we_vote_id,
            'ballot_item_display_name':     candidate_campaign.display_candidate_name(),
            'candidate_photo_url_large':    candidate_campaign.we_vote_hosted_profile_image_url_large
            if positive_value_exists(candidate_campaign.we_vote_hosted_profile_image_url_large)
            else candidate_campaign.candidate_photo_url(),
            'candidate_photo_url_medium':   candidate_campaign.we_vote_hosted_profile_image_url_medium,
            'candidate_photo_url_tiny':     candidate_campaign.we_vote_hosted_profile_image_url_tiny,
            'order_on_ballot':              candidate_campaign.order_on_ballot,
            'google_civic_election_id':     candidate_campaign.google_civic_election_id,
            'ballotpedia_candidate_id':     candidate_campaign.ballotpedia_candidate_id,
            'ballotpedia_candidate_summary': candidate_campaign.ballotpedia_candidate_summary,
            'ballotpedia_candidate_url':    candidate_campaign.ballotpedia_candidate_url,
            'ballotpedia_person_id':        candidate_campaign.ballotpedia_person_id,
            'maplight_id':                  candidate_campaign.maplight_id,
            'contest_office_id':            candidate_campaign.contest_office_id,
            'contest_office_we_vote_id':    candidate_campaign.contest_office_we_vote_id,
            'contest_office_name':          candidate_campaign.contest_office_name,
            'politician_id':                candidate_campaign.politician_id,
            'politician_we_vote_id':        candidate_campaign.politician_we_vote_id,
            # 'google_civic_candidate_name': candidate_campaign.google_civic_candidate_name,
            'party':                        candidate_campaign.political_party_display(),
            'ocd_division_id':              candidate_campaign.ocd_division_id,
            'state_code':                   candidate_campaign.state_code,
            'candidate_url':                candidate_campaign.candidate_url,
            'candidate_contact_form_url':   candidate_campaign.candidate_contact_form_url,
            'facebook_url':                 candidate_campaign.facebook_url,
            'twitter_url':                  candidate_campaign.twitter_url,
            'twitter_handle':               candidate_campaign.fetch_twitter_handle(),
            'twitter_description':          candidate_campaign.twitter_description,
            'twitter_followers_count':      candidate_campaign.twitter_followers_count,
            'youtube_url':                  candidate_campaign.youtube_url,
            'candidate_email':              candidate_campaign.candidate_email,
            'candidate_phone':              candidate_campaign.candidate_phone,
            'withdrawn_from_election':      candidate_campaign.withdrawn_from_election,
            'withdrawal_date':              wdate,
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
        candidate_list_object = CandidateCampaignListManager()
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
        # Reset office_we_vote_id and office_id so we are sure that it matches what we pull from the database
        office_id = 0
        office_we_vote_id = ''
        for candidate_campaign in candidate_list:
            if not positive_value_exists(candidate_campaign.contest_office_name):
                candidate_manager = CandidateCampaignManager()
                candidate_campaign = candidate_manager.refresh_cached_candidate_office_info(candidate_campaign)
            wdate = ''
            if isinstance(candidate_campaign.withdrawal_date, the_other_datetime.date):
                wdate = candidate_campaign.withdrawal_date.strftime("%Y-%m-%d")

            # This should match voter_ballot_items_retrieve_for_one_election_for_api (voterBallotItemsRetrieve)
            one_candidate = {
                'status':                       status,
                'success':                      True,
                'id':                           candidate_campaign.id,
                'we_vote_id':                   candidate_campaign.we_vote_id,
                'ballot_item_display_name':     candidate_campaign.display_candidate_name(),
                'ballotpedia_candidate_id':     candidate_campaign.ballotpedia_candidate_id,
                'ballotpedia_candidate_summary': candidate_campaign.ballotpedia_candidate_summary,
                'ballotpedia_candidate_url':    candidate_campaign.ballotpedia_candidate_url,
                'ballotpedia_person_id':        candidate_campaign.ballotpedia_person_id,
                'candidate_email':              candidate_campaign.candidate_email,
                'candidate_phone':              candidate_campaign.candidate_phone,
                'candidate_photo_url_large':    candidate_campaign.we_vote_hosted_profile_image_url_large
                if positive_value_exists(candidate_campaign.we_vote_hosted_profile_image_url_large)
                else candidate_campaign.candidate_photo_url(),
                'candidate_photo_url_medium':   candidate_campaign.we_vote_hosted_profile_image_url_medium,
                'candidate_photo_url_tiny':     candidate_campaign.we_vote_hosted_profile_image_url_tiny,
                'candidate_url':                candidate_campaign.candidate_url,
                'candidate_contact_form_url':   candidate_campaign.candidate_contact_form_url,
                'contest_office_id':            candidate_campaign.contest_office_id,  # Deprecate
                'contest_office_name':          candidate_campaign.contest_office_name,  # Deprecate
                'contest_office_we_vote_id':    candidate_campaign.contest_office_we_vote_id,  # Deprecate
                'facebook_url':                 candidate_campaign.facebook_url,
                'google_civic_election_id':     candidate_campaign.google_civic_election_id,  # Deprecate
                'kind_of_ballot_item':          CANDIDATE,
                'maplight_id':                  candidate_campaign.maplight_id,
                'ocd_division_id':              candidate_campaign.ocd_division_id,
                'order_on_ballot':              candidate_campaign.order_on_ballot,
                'party':                        candidate_campaign.political_party_display(),
                'politician_id':                candidate_campaign.politician_id,
                'politician_we_vote_id':        candidate_campaign.politician_we_vote_id,
                'state_code':                   candidate_campaign.state_code,
                'twitter_url':                  candidate_campaign.twitter_url,
                'twitter_handle':               candidate_campaign.fetch_twitter_handle(),
                'twitter_description':          candidate_campaign.twitter_description,
                'twitter_followers_count':      candidate_campaign.twitter_followers_count,
                'youtube_url':                  candidate_campaign.youtube_url,
                'withdrawn_from_election':      candidate_campaign.withdrawn_from_election,
                'withdrawal_date':              wdate,
            }
            candidates_to_display.append(one_candidate.copy())
            # Deprecate all of these
            # Capture the office_we_vote_id and google_civic_election_id so we can return
            if not positive_value_exists(office_id) and candidate_campaign.contest_office_id:
                office_id = candidate_campaign.contest_office_id
            if not positive_value_exists(office_we_vote_id) and candidate_campaign.contest_office_we_vote_id:
                office_we_vote_id = candidate_campaign.contest_office_we_vote_id
            if not positive_value_exists(google_civic_election_id) and candidate_campaign.google_civic_election_id:
                google_civic_election_id = candidate_campaign.google_civic_election_id

        if len(candidates_to_display):
            status += 'CANDIDATES_RETRIEVED '
        else:
            status += 'NO_CANDIDATES_RETRIEVED '

    json_data = {
        'status':                   status,
        'success':                  success,
        'contest_office_id':        office_id,  # Deprecate
        'contest_office_we_vote_id': office_we_vote_id,  # Deprecate
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

    candidate_campaign_manager = CandidateCampaignManager()
    candidate_campaign = CandidateCampaign()
    twitter_user_manager = TwitterUserManager()

    results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
    if not results['candidate_campaign_found']:
        status = "REFRESH_CANDIDATE_FROM_MASTER_TABLES-CANDIDATE_NOT_FOUND "
        results = {
            'success':              False,
            'status':               status,
            'candidate_campaign':   candidate_campaign,
        }
        return results

    candidate_campaign = results['candidate_campaign']

    # Retrieve twitter user data from TwitterUser Table
    twitter_user_id = candidate_campaign.twitter_user_id
    twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_user_id)
    if twitter_user_results['twitter_user_found']:
        twitter_user = twitter_user_results['twitter_user']
        if twitter_user.twitter_handle != candidate_campaign.candidate_twitter_handle or \
                twitter_user.twitter_name != candidate_campaign.twitter_name or \
                twitter_user.twitter_location != candidate_campaign.twitter_location or \
                twitter_user.twitter_followers_count != candidate_campaign.twitter_followers_count or \
                twitter_user.twitter_description != candidate_campaign.twitter_description:
            twitter_json = {
                'id': twitter_user.twitter_id,
                'screen_name': twitter_user.twitter_handle,
                'name': twitter_user.twitter_name,
                'followers_count': twitter_user.twitter_followers_count,
                'location': twitter_user.twitter_location,
                'description': twitter_user.twitter_description,
            }

    # Retrieve organization images data from WeVoteImage table
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

    # Refresh twitter details in candidate campaign
    update_candidate_results = candidate_campaign_manager.update_candidate_twitter_details(
        candidate_campaign, twitter_json, twitter_profile_image_url_https,
        twitter_profile_background_image_url_https, twitter_profile_banner_url_https,
        we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
        we_vote_hosted_profile_image_url_tiny)
    status += update_candidate_results['status']
    success = update_candidate_results['success']

    # Refresh contest office details in candidate campaign
    candidate_campaign = candidate_campaign_manager.refresh_cached_candidate_office_info(candidate_campaign)
    status += "REFRESHED_CANDIDATE_CAMPAIGN_FROM_CONTEST_OFFICE"

    if not positive_value_exists(candidate_campaign.politician_id) and \
            positive_value_exists(candidate_campaign.politician_we_vote_id):
        politician_manager = PoliticianManager()
        politician_id = politician_manager.fetch_politician_id_from_we_vote_id(candidate_campaign.politician_we_vote_id)
        update_values = {
            'politician_id': politician_id,
        }
        results = candidate_campaign_manager.update_candidate_row_entry(candidate_campaign.we_vote_id, update_values)
        candidate_campaign = results['updated_candidate']

    results = {
        'success':              success,
        'status':               status,
        'candidate_campaign':   candidate_campaign,
    }
    return results


def push_candidate_data_to_other_table_caches(candidate_we_vote_id):
    candidate_campaign_manager = CandidateCampaignManager()
    results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
    candidate_campaign = results['candidate_campaign']

    save_position_from_candidate_results = update_all_position_details_from_candidate(candidate_campaign)


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
    politician_created = False
    politician_found = False
    politician_list_found = False
    politician_list = []

    # Does this candidate already have a we_vote_id for a politician?
    if positive_value_exists(we_vote_candidate.politician_we_vote_id):
        # Synchronize data and exit
        update_results = politician_manager.update_or_create_politician_from_candidate(we_vote_candidate)

        if update_results['politician_found']:
            politician = update_results['politician']
            # Save politician_we_vote_id in we_vote_candidate
            we_vote_candidate.politician_we_vote_id = politician.we_vote_id
            we_vote_candidate.politician_id = politician.id
            we_vote_candidate.save()

        results = {
            'success': update_results['success'],
            'status': update_results['status'],
            'politician_list_found': False,
            'politician_list': [],
            'politician_found': update_results['politician_found'],
            'politician_created': update_results['politician_created'],
            'politician': update_results['politician'],
        }
        return results
    else:
        # Search the politician table for a match
        results = politician_manager.retrieve_all_politicians_that_might_match_candidate(
            we_vote_candidate.vote_smart_id, we_vote_candidate.maplight_id, we_vote_candidate.candidate_twitter_handle,
            we_vote_candidate.candidate_name, we_vote_candidate.state_code)
        if results['politician_list_found']:
            # If here, return
            politician_list = results['politician_list']

            results = {
                'success':                  results['success'],
                'status':                   results['status'],
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
                'success':                  results['success'],
                'status':                   results['status'],
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

            if create_results['politician_found']:
                politician = create_results['politician']
                # Save politician_we_vote_id in we_vote_candidate
                we_vote_candidate.politician_we_vote_id = politician.we_vote_id
                we_vote_candidate.politician_id = politician.id
                we_vote_candidate.save()

            results = {
                'success':                      create_results['success'],
                'status':                       create_results['status'],
                'politician_list_found':        False,
                'politician_list':              [],
                'politician_found':             create_results['politician_found'],
                'politician_created':           create_results['politician_created'],
                'politician':                   create_results['politician'],
            }
            return results

    success = False
    status = "TO_BE_IMPLEMENTED"
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


def retrieve_candidate_politician_match_options(vote_smart_id, maplight_id, candidate_twitter_handle,
                                                candidate_name, state_code):
    politician_manager = PoliticianManager()
    politician_created = False
    politician_found = False
    politician_list_found = False
    politician_list = []

    # Search the politician table for a match
    results = politician_manager.retrieve_all_politicians_that_might_match_candidate(
        vote_smart_id, maplight_id, candidate_twitter_handle,
        candidate_name, state_code)
    if results['politician_list_found']:
        # If here, return
        politician_list = results['politician_list']

        results = {
            'success':                  results['success'],
            'status':                   results['status'],
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

        results = {
            'success':                  results['success'],
            'status':                   results['status'],
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         True,
            'politician_created':       False,
            'politician':               politician,
        }
        return results

    success = False
    status = "TO_BE_IMPLEMENTED"
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
        candidate_list_manager = CandidateCampaignListManager()
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
        candidate_list_manager = CandidateCampaignListManager()
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
    if BALLOTPEDIA_IMAGE_SOURCE in kind_of_source_website:
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            ballotpedia_profile_image_url=image_url,
            image_source=BALLOTPEDIA_IMAGE_SOURCE)
        cached_ballotpedia_profile_image_url_https = cache_results['cached_ballotpedia_image_url_https']
        candidate.ballotpedia_photo_url = cached_ballotpedia_profile_image_url_https
        candidate.ballotpedia_page_title = source_link

    elif LINKEDIN in kind_of_source_website:
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            linkedin_profile_image_url=image_url,
            image_source=LINKEDIN)
        cached_linkedin_profile_image_url_https = cache_results['cached_linkedin_image_url_https']
        candidate.linkedin_url = source_link
        candidate.linkedin_photo_url = cached_linkedin_profile_image_url_https

    elif WIKIPEDIA in kind_of_source_website:
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
            wikipedia_profile_image_url=image_url,
            image_source=WIKIPEDIA)
        cached_wikipedia_profile_image_url_https = cache_results['cached_wikipedia_image_url_https']
        candidate.wikipedia_photo_url = cached_wikipedia_profile_image_url_https
        candidate.wikipedia_page_title = source_link

    elif TWITTER in kind_of_source_website:
        twitter_screen_name = extract_twitter_handle_from_text_string(source_link)
        candidate.candidate_twitter_handle = twitter_screen_name
        candidate.twitter_url = source_link

    elif FACEBOOK in kind_of_source_website:
        candidate.facebook_url_is_broken = url_is_broken
        if not url_is_broken:
            cache_results = cache_master_and_resized_image(
                candidate_id=candidate.id, candidate_we_vote_id=candidate.we_vote_id,
                facebook_profile_image_url_https=image_url,
                image_source=FACEBOOK)
            cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
            candidate.facebook_url = source_link
            candidate.facebook_profile_image_url_https = cached_facebook_profile_image_url_https
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

    if not url_is_broken:
        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

    try:
        if not url_is_broken:
            candidate.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
            candidate.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
            candidate.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
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
    if BALLOTPEDIA_IMAGE_SOURCE in google_search_website_name:
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
                        if organization_website_stripped not in \
                                ('bit.ly',
                                 'en.wikipedia.org',
                                 'facebook.com',
                                 'instagram.com',
                                 'linkedin.com',
                                 'nationbuilder.com',
                                 'secure.actblue.com',
                                 'tinyurl.com',
                                 'twitter.com',
                                 'youtube.com'):
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
                                ('bit.ly',
                                 'en.wikipedia.org',
                                 'facebook.com',
                                 'instagram.com',
                                 'linkedin.com',
                                 'nationbuilder.com',
                                 'secure.actblue.com',
                                 'tinyurl.com',
                                 'twitter.com',
                                 'youtube.com'):
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
                alternate_names = one_ballot_item_dict['alternate_names']
                for ballot_item_display_name_alternate in alternate_names:
                    if ballot_item_display_name_alternate in text_to_search_lower_case:
                        measure_we_vote_ids_list.append(one_ballot_item_dict['measure_we_vote_id'])
                        endorsement_list_light_modified.append(one_ballot_item_dict)
                        continue
            elif positive_value_exists(one_ballot_item_dict['candidate_we_vote_id']) \
                    and one_ballot_item_dict['candidate_we_vote_id'] not in candidate_we_vote_ids_list:
                if positive_value_exists(one_ballot_item_dict['ballot_item_display_name']) and \
                        one_ballot_item_dict['ballot_item_display_name'].lower() in text_to_search_lower_case:
                    candidate_we_vote_ids_list.append(one_ballot_item_dict['candidate_we_vote_id'])
                    endorsement_list_light_modified.append(one_ballot_item_dict)
                    continue
                if 'ballot_item_website' in one_ballot_item_dict and \
                        positive_value_exists(one_ballot_item_dict['ballot_item_website']):
                    ballot_item_website = one_ballot_item_dict['ballot_item_website'].lower()
                    # Remove the http... from the candidate website
                    ballot_item_website_stripped = extract_website_from_url(ballot_item_website)
                    if ballot_item_website_stripped not in \
                            ('bit.ly',
                             'en.wikipedia.org',
                             'facebook.com',
                             'instagram.com',
                             'linkedin.com',
                             'nationbuilder.com',
                             'secure.actblue.com',
                             'tinyurl.com',
                             'twitter.com',
                             'youtube.com'):
                        if ballot_item_website_stripped in text_to_search_lower_case:
                            candidate_we_vote_ids_list.append(one_ballot_item_dict['candidate_we_vote_id'])
                            endorsement_list_light_modified.append(one_ballot_item_dict)
                            continue
                if one_ballot_item_dict['alternate_names']:
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
