# office/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestOfficeListManager, ContestOfficeManager, CONTEST_OFFICE_UNIQUE_IDENTIFIERS, ContestOffice
from ballot.controllers import move_ballot_items_to_another_office
from ballot.models import OFFICE
from bookmark.models import BookmarkItemList
from candidate.controllers import move_candidates_to_another_office
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
import json
from position.controllers import move_positions_to_another_office, update_all_position_details_from_contest_office
import requests
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut


def add_contest_office_name_to_next_spot(contest_office_to_update, google_civic_office_name_to_add):

    if not positive_value_exists(google_civic_office_name_to_add):
        return contest_office_to_update

    if not positive_value_exists(contest_office_to_update.google_civic_office_name):
        contest_office_to_update.google_civic_office_name = google_civic_office_name_to_add
    elif google_civic_office_name_to_add == contest_office_to_update.google_civic_office_name:
        # The value is already stored in contest_office_to_update.google_civic_office_name so doesn't need
        # to be added to contest_office_to_update.google_civic_office_name2
        pass
    elif not positive_value_exists(contest_office_to_update.google_civic_office_name2):
        contest_office_to_update.google_civic_office_name2 = google_civic_office_name_to_add
    elif google_civic_office_name_to_add == contest_office_to_update.google_civic_office_name2:
        # The value is already stored in contest_office_to_update.google_civic_office_name2 so doesn't need
        # to be added to contest_office_to_update.google_civic_office_name3
        pass
    elif not positive_value_exists(contest_office_to_update.google_civic_office_name3):
        contest_office_to_update.google_civic_office_name3 = google_civic_office_name_to_add
    elif google_civic_office_name_to_add == contest_office_to_update.google_civic_office_name3:
        # The value is already stored in contest_office_to_update.google_civic_office_name2 so doesn't need
        # to be added to contest_office_to_update.google_civic_office_name3
        pass
    elif not positive_value_exists(contest_office_to_update.google_civic_office_name4):
        contest_office_to_update.google_civic_office_name4 = google_civic_office_name_to_add
    elif google_civic_office_name_to_add == contest_office_to_update.google_civic_office_name4:
        # The value is already stored in contest_office_to_update.google_civic_office_name2 so doesn't need
        # to be added to contest_office_to_update.google_civic_office_name3
        pass
    elif not positive_value_exists(contest_office_to_update.google_civic_office_name5):
        contest_office_to_update.google_civic_office_name5 = google_civic_office_name_to_add
    # We currently only support 5 alternate names
    return contest_office_to_update


def offices_import_from_sample_file():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    with open("office/import_data/contest_office_sample.json") as json_data:
        structured_json = json.load(json_data)

    return offices_import_from_structured_json(structured_json)


def offices_import_from_master_server(request, google_civic_election_id='', state_code=''):  # officesSyncOut
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    import_results, structured_json = process_request_from_master(
        request, "Loading Contest Offices from We Vote Master servers",
        OFFICES_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": state_code,
        }
    )

    if import_results['success']:
        # We shouldn't need to check for duplicates any more
        # results = filter_offices_structured_json_for_local_duplicates(structured_json)
        # filtered_structured_json = results['structured_json']
        # duplicates_removed = results['duplicates_removed']
        duplicates_removed = 0

        import_results = offices_import_from_structured_json(structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def fetch_duplicate_office_count(contest_office, ignore_office_we_vote_id_list):
    if not hasattr(contest_office, 'google_civic_election_id'):
        return 0

    if not positive_value_exists(contest_office.google_civic_election_id):
        return 0

    # Search for other offices within this election that match name and election
    contest_office_list_manager = ContestOfficeListManager()
    return contest_office_list_manager.fetch_offices_from_non_unique_identifiers_count(
        contest_office.google_civic_election_id, contest_office.state_code,
        contest_office.office_name, ignore_office_we_vote_id_list)


def find_duplicate_contest_office(contest_office, ignore_office_we_vote_id_list):
    if not hasattr(contest_office, 'google_civic_election_id'):
        error_results = {
            'success':                                  False,
            'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_MISSING_OFFICE_OBJECT ",
            'contest_office_merge_possibility_found':   False,
            'contest_office_merge_conflict_values':     {},
            'contest_office_list':                      [],
        }
        return error_results

    if not positive_value_exists(contest_office.google_civic_election_id):
        error_results = {
            'success':                          False,
            'status':                           "FIND_DUPLICATE_CONTEST_OFFICE_MISSING_GOOGLE_CIVIC_ELECTION_ID ",
            'contest_office_merge_possibility_found':   False,
            'contest_office_merge_conflict_values':     {},
            'contest_office_list':                      [],
        }
        return error_results

    # Search for other contest offices within this election that match name and election
    contest_office_list_manager = ContestOfficeListManager()
    try:
        results = contest_office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
            ballotpedia_race_id=contest_office.ballotpedia_race_id,
            ctcl_uuid=contest_office.ctcl_uuid,
            contest_office_name=contest_office.office_name,
            district_id=contest_office.district_id,
            district_name=contest_office.district_name,
            google_civic_election_id=contest_office.google_civic_election_id,
            ignore_office_we_vote_id_list=ignore_office_we_vote_id_list,
            incoming_state_code=contest_office.state_code,
            vote_usa_office_id=contest_office.vote_usa_office_id)

        if results['contest_office_found']:
            contest_office_merge_conflict_values = \
                figure_out_office_conflict_values(contest_office, results['contest_office'])

            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_DUPLICATES_FOUND",
                'contest_office_merge_possibility_found':   True,
                'contest_office_merge_possibility':         results['contest_office'],
                'contest_office_merge_conflict_values':     contest_office_merge_conflict_values,
                'contest_office_list':                      results['contest_office_list'],
            }
            return results
        elif results['contest_office_list_found']:
            # Only deal with merging the incoming contest office and the first on found
            contest_office_merge_conflict_values = \
                figure_out_office_conflict_values(contest_office, results['contest_office_list'][0])

            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_DUPLICATES_FOUND",
                'contest_office_merge_possibility_found':   True,
                'contest_office_merge_possibility':         results['contest_office_list'][0],
                'contest_office_merge_conflict_values':     contest_office_merge_conflict_values,
                'contest_office_list':                      results['contest_office_list'],
            }
            return results
        else:
            results = {
                'success':                                  True,
                'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_NO_DUPLICATES_FOUND",
                'contest_office_merge_possibility_found':   False,
                'contest_office_merge_conflict_values':     {},
                'contest_office_list':                      results['contest_office_list'],
            }
            return results

    except ContestOffice.DoesNotExist:
        pass
    except Exception as e:
        pass

    results = {
        'success':                                  True,
        'status':                                   "FIND_DUPLICATE_CONTEST_OFFICE_NO_DUPLICATES_FOUND",
        'contest_office_merge_possibility_found':   False,
    }
    return results


def figure_out_office_conflict_values(contest_office1, contest_office2):
    contest_office_merge_conflict_values = {}

    for attribute in CONTEST_OFFICE_UNIQUE_IDENTIFIERS:
        try:
            contest_office1_attribute = getattr(contest_office1, attribute)
            contest_office2_attribute = getattr(contest_office2, attribute)
            if contest_office1_attribute is None and contest_office2_attribute is None:
                contest_office_merge_conflict_values[attribute] = 'MATCHING'
            elif contest_office1_attribute is None or contest_office1_attribute == "":
                if attribute == "maplight_id":
                    if contest_office2_attribute is None or contest_office2_attribute == "" \
                            or contest_office2_attribute == 0 or contest_office2_attribute == '0':
                        # In certain cases (like maplight_id) we don't want to copy over empty maplight_id
                        contest_office_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE2'
                else:
                    contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE2'
            elif contest_office2_attribute is None or contest_office2_attribute == "":
                contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE1'
            else:
                if attribute == "is_battleground_race":
                    # We always want to default to preserving a true value
                    if contest_office1_attribute == contest_office2_attribute:
                        contest_office_merge_conflict_values[attribute] = 'MATCHING'
                    elif positive_value_exists(contest_office1_attribute):
                        contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE1'
                    elif positive_value_exists(contest_office2_attribute):
                        contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE2'
                    else:
                        contest_office_merge_conflict_values[attribute] = 'CONTEST_OFFICE1'
                elif attribute == "maplight_id":
                    contest_office1_attribute_empty = False
                    contest_office2_attribute_empty = False
                    if not contest_office1_attribute or contest_office1_attribute == 0 \
                            or contest_office1_attribute is None:
                        contest_office1_attribute_empty = True
                    if not contest_office2_attribute or contest_office2_attribute == 0 \
                            or contest_office2_attribute is None:
                        contest_office1_attribute_empty = True
                    if contest_office1_attribute == contest_office2_attribute:
                        contest_office_merge_conflict_values[attribute] = 'MATCHING'
                    elif contest_office1_attribute_empty and contest_office2_attribute_empty:
                        contest_office_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        contest_office_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "office_name" or attribute == "state_code":
                    if contest_office1_attribute.lower() == contest_office2_attribute.lower():
                        contest_office_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        contest_office_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    if contest_office1_attribute == contest_office2_attribute:
                        contest_office_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        contest_office_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return contest_office_merge_conflict_values


def merge_if_duplicate_offices(office1_on_stage, office2_on_stage, conflict_values):
    status = "MERGE_IF_DUPLICATE_OFFICES "
    offices_merged = False
    decisions_required = False
    office1_we_vote_id = office1_on_stage.we_vote_id
    office2_we_vote_id = office2_on_stage.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    for attribute in CONTEST_OFFICE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            decisions_required = True
            break
        elif conflict_value == "OFFICE2":
            merge_choices[attribute] = getattr(office2_on_stage, attribute)

    if decisions_required:
        success = True
        status += "DECISION_REQUIRED "
    else:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = merge_these_two_offices(office1_we_vote_id, office2_we_vote_id, merge_choices,
                                                office1_on_stage, office2_on_stage)

        if merge_results['offices_merged']:
            success = True
            offices_merged = True
        else:
            success = False
            status += merge_results['status']

    results = {
        'success':              success,
        'status':               status,
        'offices_merged':       offices_merged,
        'decisions_required':   decisions_required,
        'office':               office1_on_stage,
    }
    return results


def merge_these_two_offices(contest_office1_we_vote_id, contest_office2_we_vote_id, admin_merge_choices={},
                            contest_office1_on_stage=None, contest_office2_on_stage=None):
    """
    Process the merging of two offices. Note that this is similar to office/views_admin.py "office_merge_process_view"
    :param contest_office1_we_vote_id:
    :param contest_office2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :param contest_office1_on_stage: The first office object if we have it
    :param contest_office2_on_stage: The second office object if we have it
    :return:
    """
    status = ""
    office_manager = ContestOfficeManager()

    if contest_office1_on_stage and contest_office1_on_stage.we_vote_id:
        contest_office1_id = contest_office1_on_stage.id
        contest_office1_we_vote_id = contest_office1_on_stage.we_vote_id
    else:
        # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
        contest_office1_results = \
            office_manager.retrieve_contest_office_from_we_vote_id(contest_office1_we_vote_id)
        if contest_office1_results['contest_office_found']:
            contest_office1_on_stage = contest_office1_results['contest_office']
            contest_office1_id = contest_office1_on_stage.id
        else:
            results = {
                'success': False,
                'status': "MERGE_THESE_TWO_OFFICES-COULD_NOT_RETRIEVE_OFFICE1 ",
                'offices_merged': False,
                'office': None,
            }
            return results

    if contest_office2_on_stage and contest_office2_on_stage.we_vote_id:
        contest_office2_id = contest_office2_on_stage.id
        contest_office2_we_vote_id = contest_office2_on_stage.we_vote_id
    else:
        contest_office2_results = \
            office_manager.retrieve_contest_office_from_we_vote_id(contest_office2_we_vote_id)
        if contest_office2_results['contest_office_found']:
            contest_office2_on_stage = contest_office2_results['contest_office']
            contest_office2_id = contest_office2_on_stage.id
        else:
            results = {
                'success': False,
                'status': "MERGE_THESE_TWO_OFFICES-COULD_NOT_RETRIEVE_OFFICE2 ",
                'offices_merged': False,
                'office': None,
            }
            return results

    # TODO: Migrate bookmarks - for now stop the merge process if there are bookmarks
    bookmark_item_list_manager = BookmarkItemList()
    bookmark_results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_contest_office(
        contest_office2_we_vote_id)
    if bookmark_results['bookmark_item_list_found']:
        status += "Bookmarks found for Contest Office 2 - automatic merge not working yet. "
        results = {
            'success': False,
            'status': status,
            'offices_merged': False,
            'office': None,
        }
        return results

    # Merge attribute values chosen by the admin
    for attribute in CONTEST_OFFICE_UNIQUE_IDENTIFIERS:
        if attribute in admin_merge_choices:
            setattr(contest_office1_on_stage, attribute, admin_merge_choices[attribute])

    # Preserve unique google_civic_office_name, _name2, _name3, _name4, and _name5
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name2):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name2)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name3):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name3)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name4):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name4)
    if positive_value_exists(contest_office2_on_stage.google_civic_office_name5):
        contest_office1_on_stage = add_contest_office_name_to_next_spot(
            contest_office1_on_stage, contest_office2_on_stage.google_civic_office_name5)

    # TODO: Merge quick_info's office details in future

    # Merge ballot item's office details
    ballot_items_results = move_ballot_items_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                               contest_office1_id, contest_office1_we_vote_id,
                                                               contest_office1_on_stage)
    if not ballot_items_results['success']:
        status += ballot_items_results['status']
        results = {
            'success': False,
            'status': status,
            'offices_merged': False,
            'office': contest_office1_on_stage,
        }
        return results

    # Merge public positions
    public_positions_results = move_positions_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                                contest_office1_id, contest_office1_we_vote_id,
                                                                True)
    if not public_positions_results['success']:
        status += public_positions_results['status']
        results = {
            'success': False,
            'status': status,
            'offices_merged': False,
            'office': contest_office1_on_stage,
        }
        return results

    # Merge friends-only positions
    friends_positions_results = move_positions_to_another_office(contest_office2_id, contest_office2_we_vote_id,
                                                                 contest_office1_id, contest_office1_we_vote_id,
                                                                 False)
    if not friends_positions_results['success']:
        status += friends_positions_results['status']
        results = {
            'success': False,
            'status': status,
            'offices_merged': False,
            'office': contest_office1_on_stage,
        }
        return results

    # TODO: Migrate images?

    # Finally, move candidates attached to this office
    from_contest_office_id = contest_office2_on_stage.id
    from_contest_office_we_vote_id = contest_office2_on_stage.we_vote_id
    to_contest_office_id = contest_office1_on_stage.id
    to_contest_office_we_vote_id = contest_office1_on_stage.we_vote_id
    results = move_candidates_to_another_office(from_contest_office_id, from_contest_office_we_vote_id,
                                                to_contest_office_id, to_contest_office_we_vote_id)

    if not positive_value_exists(results['success']):
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_OFFICES-COULD_NOT_MOVE_CANDIDATES_TO_OFFICE1 ",
            'offices_merged': False,
            'office': None,
        }
        return results

    # Note: wait to wrap in try/except block
    contest_office1_on_stage.save()
    # There isn't any office data to refresh from other master tables

    # Remove office 2
    contest_office2_on_stage.delete()

    results = {
        'success': True,
        'status': status,
        'offices_merged': True,
        'office': contest_office1_on_stage,
    }
    return results


def filter_offices_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove offices that seem to be duplicates, but have different we_vote_id's
    :param structured_json:
    :return:
    """
    office_manager_list = ContestOfficeListManager()
    duplicates_removed = 0
    filtered_structured_json = []
    for one_office in structured_json:
        google_civic_election_id = one_office['google_civic_election_id'] \
            if 'google_civic_election_id' in one_office else 0
        state_code = one_office['state_code'] if 'state_code' in one_office else ''
        we_vote_id = one_office['we_vote_id'] if 'we_vote_id' in one_office else ''
        office_name = one_office['office_name'] if 'office_name' in one_office else ''

        # district_id = one_office['district_id'] if 'district_id' in one_office else ''
        # ocd_division_id = one_office['ocd_division_id'] if 'ocd_division_id' in one_office else ''
        # number_voting_for = one_office['number_voting_for'] if 'number_voting_for' in one_office else ''
        # number_elected = one_office['number_elected'] if 'number_elected' in one_office else ''
        # contest_level0 = one_office['contest_level0'] if 'contest_level0' in one_office else ''
        # contest_level1 = one_office['contest_level1'] if 'contest_level1' in one_office else ''
        # contest_level2 = one_office['contest_level2'] if 'contest_level2' in one_office else ''
        # primary_party = one_office['primary_party'] if 'primary_party' in one_office else ''
        # district_name = one_office['district_name'] if 'district_name' in one_office else ''
        # district_scope = one_office['district_scope'] if 'district_scope' in one_office else ''
        # electorate_specifications = one_office['electorate_specifications'] \
        #     if 'electorate_specifications' in one_office else ''
        # special = one_office['special'] if 'special' in one_office else ''
        # maplight_id = one_office['maplight_id'] if 'maplight_id' in one_office else 0
        # ballotpedia_id = one_office['ballotpedia_id'] if 'ballotpedia_id' in one_office else ''
        # wikipedia_id = one_office['wikipedia_id'] if 'wikipedia_id' in one_office else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = office_manager_list.retrieve_possible_duplicate_offices(
            google_civic_election_id,
            state_code,
            office_name,
            we_vote_id_from_master)

        if results['office_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_office)

    offices_results = {
        'success':              True,
        'status':               "FILTER_OFFICES_PROCESS_COMPLETE ",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return offices_results


def offices_import_from_structured_json(structured_json):
    office_manager = ContestOfficeManager()
    offices_saved = 0
    offices_updated = 0
    offices_not_processed = 0
    for one_office in structured_json:
        updated_contest_office_values = {}
        district_id = one_office['district_id'] if 'district_id' in one_office else ''
        google_civic_election_id = one_office['google_civic_election_id'] \
            if 'google_civic_election_id' in one_office else 0
        ctcl_uuid = one_office['ctcl_uuid'] if 'ctcl_uuid' in one_office else None
        maplight_id = one_office['maplight_id'] if 'maplight_id' in one_office else 0
        office_name = one_office['office_name'] if 'office_name' in one_office else ''
        vote_usa_office_id = one_office['vote_usa_office_id'] if 'vote_usa_office_id' in one_office else None
        we_vote_id = one_office['we_vote_id'] if 'we_vote_id' in one_office else ''
        if positive_value_exists(google_civic_election_id) and positive_value_exists(we_vote_id):
            updated_contest_office_values['ballotpedia_district_id'] = one_office['ballotpedia_district_id'] \
                if 'ballotpedia_district_id' in one_office else ''
            updated_contest_office_values['ballotpedia_id'] = one_office['ballotpedia_id'] \
                if 'ballotpedia_id' in one_office else ''
            updated_contest_office_values['ballotpedia_is_marquee'] = one_office['ballotpedia_is_marquee'] \
                if 'ballotpedia_is_marquee' in one_office else ''
            # Equivalent to office_held
            updated_contest_office_values['ballotpedia_office_id'] = one_office['ballotpedia_office_id'] \
                if 'ballotpedia_office_id' in one_office else ''
            updated_contest_office_values['ballotpedia_office_name'] = one_office['ballotpedia_office_name'] \
                if 'ballotpedia_office_name' in one_office else ''
            updated_contest_office_values['ballotpedia_office_url'] = one_office['ballotpedia_office_url'] \
                if 'ballotpedia_office_url' in one_office else ''
            # Equivalent to contest_office
            updated_contest_office_values['ballotpedia_race_id'] = one_office['ballotpedia_race_id'] \
                if 'ballotpedia_race_id' in one_office else ''
            updated_contest_office_values['ballotpedia_race_office_level'] = \
                one_office['ballotpedia_race_office_level'] if 'ballotpedia_race_office_level' in one_office else ''
            updated_contest_office_values['ballotpedia_race_url'] = \
                one_office['ballotpedia_race_url'] if 'ballotpedia_race_url' in one_office else ''
            updated_contest_office_values['contest_level0'] = one_office['contest_level0'] \
                if 'contest_level0' in one_office else ''
            updated_contest_office_values['contest_level1'] = one_office['contest_level1'] \
                if 'contest_level1' in one_office else ''
            updated_contest_office_values['contest_level2'] = one_office['contest_level2'] \
                if 'contest_level2' in one_office else ''
            updated_contest_office_values['ctcl_uuid'] = one_office['ctcl_uuid'] \
                if 'ctcl_uuid' in one_office else ''
            updated_contest_office_values['district_id'] = one_office['district_id'] \
                if 'district_id' in one_office else ''
            updated_contest_office_values['district_name'] = one_office['district_name'] \
                if 'district_name' in one_office else ''
            updated_contest_office_values['district_scope'] = one_office['district_scope'] \
                if 'district_scope' in one_office else ''
            updated_contest_office_values['electorate_specifications'] = one_office['electorate_specifications'] \
                if 'electorate_specifications' in one_office else ''
            updated_contest_office_values['google_ballot_placement'] = one_office['google_ballot_placement'] \
                if 'google_ballot_placement' in one_office else ''
            updated_contest_office_values['google_civic_election_id'] = one_office['google_civic_election_id'] \
                if 'google_civic_election_id' in one_office else ''
            updated_contest_office_values['google_civic_office_name'] = one_office['google_civic_office_name'] \
                if 'google_civic_office_name' in one_office else ''
            updated_contest_office_values['google_civic_office_name2'] = one_office['google_civic_office_name2'] \
                if 'google_civic_office_name2' in one_office else ''
            updated_contest_office_values['google_civic_office_name3'] = one_office['google_civic_office_name3'] \
                if 'google_civic_office_name3' in one_office else ''
            updated_contest_office_values['google_civic_office_name4'] = one_office['google_civic_office_name4'] \
                if 'google_civic_office_name4' in one_office else ''
            updated_contest_office_values['google_civic_office_name5'] = one_office['google_civic_office_name5'] \
                if 'google_civic_office_name5' in one_office else ''
            updated_contest_office_values['is_ballotpedia_general_election'] = \
                one_office['is_ballotpedia_general_election'] if 'is_ballotpedia_general_election' in one_office else ''
            updated_contest_office_values['is_ballotpedia_general_runoff_election'] = \
                one_office['is_ballotpedia_general_runoff_election'] \
                    if 'is_ballotpedia_general_runoff_election' in one_office else ''
            updated_contest_office_values['is_ballotpedia_primary_election'] = \
                one_office['is_ballotpedia_primary_election'] if 'is_ballotpedia_primary_election' in one_office else ''
            updated_contest_office_values['is_ballotpedia_primary_runoff_election'] = \
                one_office['is_ballotpedia_primary_runoff_election'] \
                    if 'is_ballotpedia_primary_runoff_election' in one_office else ''
            updated_contest_office_values['is_battleground_race'] = one_office['is_battleground_race'] \
                if 'is_battleground_race' in one_office else ''
            updated_contest_office_values['maplight_id'] = one_office['maplight_id'] \
                if 'maplight_id' in one_office else 0
            updated_contest_office_values['number_elected'] = one_office['number_elected'] \
                if 'number_elected' in one_office else ''
            updated_contest_office_values['number_voting_for'] = one_office['number_voting_for'] \
                if 'number_voting_for' in one_office else ''
            updated_contest_office_values['ocd_division_id'] = one_office['ocd_division_id'] \
                if 'ocd_division_id' in one_office else ''
            updated_contest_office_values['office_name'] = one_office['office_name'] \
                if 'office_name' in one_office else ''
            updated_contest_office_values['primary_party'] = one_office['primary_party'] \
                if 'primary_party' in one_office else ''
            updated_contest_office_values['special'] = one_office['special'] if 'special' in one_office else ''
            updated_contest_office_values['state_code'] = one_office['state_code'] if 'state_code' in one_office else ''
            updated_contest_office_values['vote_usa_office_id'] = one_office['vote_usa_office_id'] \
                if 'vote_usa_office_id' in one_office else None
            updated_contest_office_values['we_vote_id'] = one_office['we_vote_id'] \
                if 'we_vote_id' in one_office else ''
            updated_contest_office_values['wikipedia_id'] = one_office['wikipedia_id'] \
                if 'wikipedia_id' in one_office else ''
            results = office_manager.update_or_create_contest_office(
                ctcl_uuid=ctcl_uuid,
                district_id=district_id,
                google_civic_election_id=google_civic_election_id,
                maplight_id=maplight_id,
                office_name=office_name,
                office_we_vote_id=we_vote_id,
                vote_usa_office_id=vote_usa_office_id,
                updated_contest_office_values=updated_contest_office_values)
        else:
            offices_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create '
            }

        if results['success']:
            if results['new_office_created']:
                offices_saved += 1
            else:
                offices_updated += 1

    offices_results = {
        'success':          True,
        'status':           "OFFICE_IMPORT_PROCESS_COMPLETE ",
        'saved':            offices_saved,
        'updated':          offices_updated,
        'not_processed':    offices_not_processed,
    }
    return offices_results


def office_create_from_office_held(office_held_we_vote_id='', google_civic_election_id=''):
    status = ''
    success = True
    contest_office = None
    contest_office_found = False
    election_day_text = ''
    election_year = 0
    office_we_vote_id = ''

    from office_held.models import OfficeHeldManager
    office_held_manager = OfficeHeldManager()
    results = office_held_manager.retrieve_office_held(office_held_we_vote_id=office_held_we_vote_id)
    office_held = None
    office_held_found = False
    if not results['success']:
        status += results['status']
    elif results['office_held_found']:
        office_held = results['office_held']
        office_held_found = True

    if not office_held_found or not hasattr(office_held, 'office_held_name'):
        status += "VALID_OFFICE_HELD_NOT_FOUND "
        results = {
            'election_day_text':    election_day_text,
            'election_year':        election_year,
            'office':               contest_office,
            'office_found':         contest_office_found,
            'office_we_vote_id':    '',
            'status':               status,
            'success':              False,
        }
        return results

    try:
        new_contest_office_created = False
        contest_office = ContestOffice.objects.create(
            ballotpedia_race_office_level=office_held.race_office_level,
            district_id=office_held.district_id,
            district_name=office_held.district_name,
            district_scope=office_held.district_scope,
            google_civic_election_id=google_civic_election_id,
            google_civic_office_name=office_held.google_civic_office_held_name,
            google_civic_office_name2=office_held.google_civic_office_held_name2,
            google_civic_office_name3=office_held.google_civic_office_held_name3,
            number_elected=office_held.number_elected,
            ocd_division_id=office_held.ocd_division_id,
            office_held_description=office_held.office_held_description,
            office_held_description_es=office_held.office_held_description_es,
            office_held_name=office_held.office_held_name,
            office_held_name_es=office_held.office_held_name_es,
            office_held_we_vote_id=office_held.we_vote_id,
            office_name=office_held.office_held_name,
            office_twitter_handle=office_held.office_held_twitter_handle,
            office_url=office_held.office_held_url,
            primary_party=office_held.primary_party,
            state_code=office_held.state_code,
        )
        contest_office_found = True
        election_day_text = ''

        if positive_value_exists(contest_office.id):
            office_we_vote_id = contest_office.we_vote_id
            if positive_value_exists(google_civic_election_id):
                from election.models import ElectionManager
                election_manager = ElectionManager()
                results = election_manager.retrieve_election(
                    google_civic_election_id=google_civic_election_id)
                if results['election_found']:
                    election = results['election']
                    if positive_value_exists(election.election_day_text):
                        election_day_text = election.election_day_text
                        year = election.election_day_text[:4]
                        if year:
                            election_year = convert_to_int(year)
                # Set is_battleground_race
                if positive_value_exists(election_year):
                    is_battleground_race_key = 'is_battleground_race_' + str(election_year)
                    if hasattr(office_held, is_battleground_race_key):
                        is_battleground_race = getattr(office_held, is_battleground_race_key)
                        if positive_value_exists(is_battleground_race):
                            contest_office.is_battleground_race = is_battleground_race
            if positive_value_exists(office_held.office_held_facebook_url) and not office_held.facebook_url_is_broken:
                contest_office.office_facebook_url = office_held.office_held_facebook_url
            contest_office.save()
            new_contest_office_created = True
        if new_contest_office_created:
            success = True
            status += "OFFICE_CREATED "
        else:
            success = False
            status += "OFFICE_NOT_CREATED "

    except Exception as e:
        status += 'FAILED_TO_CREATE_OFFICE ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    results = {
        'election_day_text':    election_day_text,
        'election_year':        election_year,
        'office':               contest_office,
        'office_found':         contest_office_found,
        'office_we_vote_id':    office_we_vote_id,
        'status':               status,
        'success':              success,
    }
    return results


def office_retrieve_for_api(office_id, office_we_vote_id):
    """
    Used by the api
    :param office_id:
    :param office_we_vote_id:
    :return:
    """
    # NOTE: Office retrieve is independent of *who* wants to see the data. Office retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItemsFromGoogleCivic does

    if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING '
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
            'state_code':               '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_manager = ContestOfficeManager()
    if positive_value_exists(office_id):
        results = office_manager.retrieve_contest_office_from_id(office_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(office_we_vote_id):
        results = office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING_2 '  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
            'state_code':               '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_office = results['contest_office']
        date_last_updated = ''
        if positive_value_exists(contest_office.date_last_updated):
            date_last_updated = contest_office.date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
        json_data = {
            'status':                   status,
            'success':                  True,
            'ballot_item_display_name': contest_office.office_name,
            'ballotpedia_id':           contest_office.ballotpedia_id,
            'ballotpedia_district_id':  contest_office.ballotpedia_district_id,
            'ballotpedia_office_id':    contest_office.ballotpedia_office_id,
            'ballotpedia_office_url':   contest_office.ballotpedia_office_url,
            'ballotpedia_race_id':      contest_office.ballotpedia_race_id,
            'ballotpedia_race_office_level':      contest_office.ballotpedia_race_office_level,
            'district_name':            contest_office.district_name,
            'google_civic_election_id': contest_office.google_civic_election_id,
            'id':                       contest_office.id,
            'kind_of_ballot_item':      OFFICE,
            'last_updated':             date_last_updated,
            'maplight_id':              contest_office.maplight_id,
            'number_voting_for':        contest_office.number_voting_for,
            'number_elected':           contest_office.number_elected,
            'ocd_division_id':          contest_office.ocd_division_id,
            'primary_party':            contest_office.primary_party,
            'race_office_level':        contest_office.ballotpedia_race_office_level,
            'state_code':               contest_office.state_code,
            'we_vote_id':               contest_office.we_vote_id,
            'wikipedia_id':             contest_office.wikipedia_id,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
            'state_code':               '',
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def push_contest_office_data_to_other_table_caches(contest_office_id=0, contest_office_we_vote_id=''):
    contest_office_manager = ContestOfficeManager()
    if positive_value_exists(contest_office_we_vote_id):
        results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id)
    elif positive_value_exists(contest_office_id):
        results = contest_office_manager.retrieve_contest_office_from_id(contest_office_id)

    if results['contest_office_found']:
        contest_office = results['contest_office']
        save_position_from_office_results = update_all_position_details_from_contest_office(contest_office)
        return save_position_from_office_results
    else:
        results = {
            'success':                      False,
            'positions_updated_count':      0,
            'positions_not_updated_count':  0,
            'update_all_position_results':  []
        }
        return results
