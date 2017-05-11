# ballot/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItemListManager, BallotItemManager, BallotReturnedListManager, BallotReturnedManager, \
    CANDIDATE, copy_existing_ballot_items_from_stored_ballot, OFFICE, MEASURE, \
    VoterBallotSaved, VoterBallotSavedManager
from candidate.models import CandidateCampaignListManager
from config.base import get_environment_variable
from datetime import datetime
from django.contrib import messages
from election.models import ElectionManager
from exception.models import handle_exception
from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_for_api
import json
from measure.models import ContestMeasureList
from office.models import ContestOfficeListManager
from polling_location.models import PollingLocationManager
import requests
from voter.models import BALLOT_ADDRESS, VoterAddressManager, \
    VoterDeviceLinkManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
BALLOT_ITEMS_SYNC_URL = get_environment_variable("BALLOT_ITEMS_SYNC_URL")
BALLOT_RETURNED_SYNC_URL = get_environment_variable("BALLOT_RETURNED_SYNC_URL")


def ballot_items_import_from_master_server(request, google_civic_election_id, state_code):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    messages.add_message(request, messages.INFO, "Loading Ballot Items from We Vote Master servers")
    logger.info("Loading Ballot Items from We Vote Master servers")

    if positive_value_exists(google_civic_election_id) and positive_value_exists(state_code):
        request = requests.get(BALLOT_ITEMS_SYNC_URL, params={
            "key":                      WE_VOTE_API_KEY,  # This comes from an environment variable
            "google_civic_election_id": google_civic_election_id,
            "state_code":               state_code,
        })
    elif positive_value_exists(google_civic_election_id):
        request = requests.get(BALLOT_ITEMS_SYNC_URL, params={
            "key":                      WE_VOTE_API_KEY,
            "google_civic_election_id": google_civic_election_id,
        })
    elif not positive_value_exists(state_code):
        request = requests.get(BALLOT_ITEMS_SYNC_URL, params={
            "key":                      WE_VOTE_API_KEY,
            "state_code":               state_code,
        })

    try:
        structured_json = json.loads(request.text)
        results = filter_ballot_items_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        import_results = ballot_items_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed
    except Exception as e:
        import_results = {
            'success': False,
            'status': "FAILED_TO_GET_JSON_FROM_MASTER_SERVER",
            'saved': 0,
            'updated': 0,
            'not_processed': 0,
            'duplicates_removed': 0
        }

    return import_results


def ballot_returned_import_from_master_server(request, google_civic_election_id):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    messages.add_message(request, messages.INFO, "Loading Ballot Returned entries (saved ballots, specific to one "
                                                 "location) from We Vote Master servers")
    logger.info("Loading Ballot Returned entries (saved ballots, specific to one location) from We Vote Master servers")
    request = requests.get(BALLOT_RETURNED_SYNC_URL, params={
        "key":                      WE_VOTE_API_KEY,  # This comes from an environment variable
        "format":                   'json',
        "google_civic_election_id": google_civic_election_id,
    })
    structured_json = json.loads(request.text)
    results = filter_ballot_returned_structured_json_for_local_duplicates(structured_json)
    filtered_structured_json = results['structured_json']
    duplicates_removed = results['duplicates_removed']

    import_results = ballot_returned_import_from_structured_json(filtered_structured_json)
    import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_ballot_items_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove ballot_items that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office or measure in the database this routine --
    that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    ballot_item_list_manager = BallotItemListManager()
    for one_ballot_item in structured_json:
        ballot_item_display_name = one_ballot_item['ballot_item_display_name'] \
            if 'ballot_item_display_name' in one_ballot_item else ''
        google_civic_election_id = one_ballot_item['google_civic_election_id'] \
            if 'google_civic_election_id' in one_ballot_item else ''
        polling_location_we_vote_id = one_ballot_item['polling_location_we_vote_id'] \
            if 'polling_location_we_vote_id' in one_ballot_item else ''
        contest_office_we_vote_id = one_ballot_item['contest_office_we_vote_id'] \
            if 'contest_office_we_vote_id' in one_ballot_item else ''
        contest_measure_we_vote_id = one_ballot_item['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_ballot_item else ''

        # Check to see if there is an entry that matches in all critical ways, minus the
        # contest_office_we_vote_id or contest_measure_we_vote_id. That is, an entry for a
        # google_civic_election_id + polling_location_we_vote_id that has the same ballot_item_display_name,
        # but different contest_office_we_vote_id or contest_measure_we_vote_id
        results = ballot_item_list_manager.retrieve_possible_duplicate_ballot_items(
            ballot_item_display_name, google_civic_election_id, polling_location_we_vote_id, contest_office_we_vote_id,
            contest_measure_we_vote_id)

        if results['ballot_item_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_ballot_item)

    ballot_items_results = {
        'success':              True,
        'status':               "FILTER_BALLOT_ITEMS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return ballot_items_results


def filter_ballot_returned_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove ballot_returned entries that seem to be duplicates,
    but have different polling_location_we_vote_id's.
    We do not check to see if we have a local entry for polling_location_we_vote_id -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    ballot_returned_list_manager = BallotReturnedListManager()
    for one_ballot_returned in structured_json:
        polling_location_we_vote_id = one_ballot_returned['polling_location_we_vote_id'] \
            if 'polling_location_we_vote_id' in one_ballot_returned else ''
        google_civic_election_id = \
            one_ballot_returned['google_civic_election_id'] if 'google_civic_election_id' in one_ballot_returned else ''
        normalized_line1 = one_ballot_returned['normalized_line1'] if 'normalized_line1' in one_ballot_returned else ''
        normalized_zip = one_ballot_returned['normalized_zip'] if 'normalized_zip' in one_ballot_returned else ''

        # Check to see if there is an entry that matches in all critical ways, minus the polling_location_we_vote_id
        results = ballot_returned_list_manager.retrieve_possible_duplicate_ballot_returned(
            google_civic_election_id, normalized_line1, normalized_zip, polling_location_we_vote_id)

        if results['ballot_returned_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_ballot_returned)

    ballot_returned_results = {
        'success':              True,
        'status':               "FILTER_BALLOT_RETURNED_ITEMS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return ballot_returned_results


def ballot_items_import_from_structured_json(structured_json):
    """
    This pathway in requires a we_vote_id, and is not used when we import from Google Civic
    :param structured_json:
    :return:
    """
    ballot_item_manager = BallotItemManager()
    ballot_items_saved = 0
    ballot_items_updated = 0
    ballot_items_not_processed = 0
    for one_ballot_item in structured_json:
        polling_location_we_vote_id = one_ballot_item['polling_location_we_vote_id'] \
            if 'polling_location_we_vote_id' in one_ballot_item else ''
        google_civic_election_id = \
            one_ballot_item['google_civic_election_id'] if 'google_civic_election_id' in one_ballot_item else ''
        contest_office_we_vote_id = one_ballot_item['contest_office_we_vote_id'] \
            if 'contest_office_we_vote_id' in one_ballot_item else ''
        contest_measure_we_vote_id = one_ballot_item['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_ballot_item else ''

        if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id) \
                and (positive_value_exists(contest_office_we_vote_id) or
                     positive_value_exists(contest_measure_we_vote_id)):
            # We check to make sure we have a local copy of this polling_location, contest_office or contest_measure
            #  in ballot_item_manager.update_or_create_ballot_item_for_polling_location
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False

        if proceed_to_update_or_create:
            ballot_item_display_name = one_ballot_item['ballot_item_display_name'] \
                if 'ballot_item_display_name' in one_ballot_item else ''
            measure_subtitle = one_ballot_item['measure_subtitle'] if 'measure_subtitle' in one_ballot_item else 0
            google_ballot_placement = one_ballot_item['google_ballot_placement'] \
                if 'google_ballot_placement' in one_ballot_item else 0
            local_ballot_order = one_ballot_item['local_ballot_order'] \
                if 'local_ballot_order' in one_ballot_item else ''

            contest_office_id = 0
            contest_measure_id = 0

            results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id)

        else:
            ballot_items_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_ballot_item_created']:
                ballot_items_saved += 1
            else:
                ballot_items_updated += 1
        else:
            ballot_items_not_processed += 1
    ballot_items_results = {
        'success': True,
        'status': "ballot_items_IMPORT_PROCESS_COMPLETE",
        'saved': ballot_items_saved,
        'updated': ballot_items_updated,
        'not_processed': ballot_items_not_processed,
    }
    return ballot_items_results


def ballot_returned_import_from_structured_json(structured_json):
    """
    This pathway in requires a we_vote_id, and is not used when we import from Google Civic
    :param structured_json:
    :return:
    """
    ballot_returned_manager = BallotReturnedManager()
    polling_location_manager = PollingLocationManager()
    ballot_returned_saved = 0
    ballot_returned_updated = 0
    ballot_returned_not_processed = 0
    for one_ballot_returned in structured_json:
        google_civic_election_id = \
            one_ballot_returned['google_civic_election_id'] if 'google_civic_election_id' in one_ballot_returned else 0
        polling_location_we_vote_id = one_ballot_returned['polling_location_we_vote_id'] \
            if 'polling_location_we_vote_id' in one_ballot_returned else ''
        # I don't think we expect voter_id to be other than 0 since we only import ballot_returned entries from
        # polling_locations
        voter_id = one_ballot_returned['voter_id'] if 'voter_id' in one_ballot_returned else 0

        if positive_value_exists(google_civic_election_id) and (positive_value_exists(polling_location_we_vote_id) or
                                                                positive_value_exists(voter_id)):
            # Make sure we have a local polling_location
            results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
            if results['polling_location_found']:
                proceed_to_update_or_create = True
            else:
                # We don't want to save a ballot_returned entry if the polling location wasn't stored locally
                proceed_to_update_or_create = False
        else:
            proceed_to_update_or_create = False

        if proceed_to_update_or_create:
            election_date = one_ballot_returned['election_date'] if 'election_date' in one_ballot_returned else False
            election_description_text = one_ballot_returned['election_description_text'] \
                if 'election_description_text' in one_ballot_returned else False
            latitude = one_ballot_returned['latitude'] if 'latitude' in one_ballot_returned else False
            longitude = one_ballot_returned['longitude'] if 'longitude' in one_ballot_returned else False
            normalized_city = one_ballot_returned['normalized_city'] \
                if 'normalized_city' in one_ballot_returned else False
            normalized_line1 = one_ballot_returned['normalized_line1'] \
                if 'normalized_line1' in one_ballot_returned else False
            normalized_line2 = one_ballot_returned['normalized_line2'] \
                if 'normalized_line2' in one_ballot_returned else False
            normalized_state = one_ballot_returned['normalized_state'] \
                if 'normalized_state' in one_ballot_returned else False
            normalized_zip = one_ballot_returned['normalized_zip'] \
                if 'normalized_zip' in one_ballot_returned else False
            text_for_map_search = one_ballot_returned['text_for_map_search'] \
                if 'text_for_map_search' in one_ballot_returned else False

            results = ballot_returned_manager.update_or_create_ballot_returned(
                polling_location_we_vote_id, voter_id, google_civic_election_id, election_date,
                election_description_text, latitude, longitude,
                normalized_city, normalized_line1, normalized_line2, normalized_state,
                normalized_zip, text_for_map_search)
        else:
            ballot_returned_not_processed += 1
            results = {
                'success': False,
            }

        if results['success']:
            if results['new_ballot_returned_created']:
                ballot_returned_saved += 1
            else:
                ballot_returned_updated += 1
        else:
            ballot_returned_not_processed += 1

    status = "BALLOT_RETURNED_IMPORT_PROCESS_COMPLETED"

    ballot_returned_results = {
        'success':          True,
        'status':           status,
        'saved':            ballot_returned_saved,
        'updated':          ballot_returned_updated,
        'not_processed':    ballot_returned_not_processed,
    }
    return ballot_returned_results


def figure_out_google_civic_election_id_voter_is_watching(voter_device_id):
    status = ''

    # We zero out this value  since we will never have this coming in for this function
    google_civic_election_id = 0

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        status += "VALID_VOTER_DEVICE_ID_MISSING: " + voter_device_link_results['status']
        results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'voter_device_link_found':      False,
            'voter_address_object_found':   False,
            'voter_ballot_saved_found':     False,
            'google_civic_election_id':     0,
        }
        return results

    voter_device_link = voter_device_link_results['voter_device_link']
    voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        status += " " + "VALID_VOTER_ID_MISSING"
        results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'voter_device_link_found':      False,
            'voter_address_object_found':   False,
            'voter_ballot_saved_found':     False,
            'google_civic_election_id':     0,
        }
        return results

    voter_address_manager = VoterAddressManager()
    voter_address_id = 0
    address_type = BALLOT_ADDRESS
    voter_address_results = voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)
    status += " " + voter_address_results['status']
    if not positive_value_exists(voter_address_results['voter_address_has_value']):
        # If there isn't an address with a value, then there won't be a voter_ballot_saved_found
        results = {
            'status':                       status,
            'success':                      True,
            'voter_device_id':              voter_device_id,
            'voter_device_link_found':      False,
            'voter_address_object_found':   voter_address_results['voter_address_found'],
            'voter_ballot_saved_found':     False,
            'google_civic_election_id':     0,
        }
        return results

    voter_address = voter_address_results['voter_address']

    # This routine finds a ballot saved for this voter
    choose_election_results = choose_election_from_existing_data(voter_device_link, google_civic_election_id,
                                                                 voter_address)
    status += " " + choose_election_results['status']
    results = {
        'status': status,
        'success': choose_election_results['success'],
        'voter_device_id': voter_device_id,
        'voter_device_link_found': True,
        'voter_address_object_found': voter_address_results['voter_address_found'],
        'voter_ballot_saved_found': choose_election_results['voter_ballot_saved_found'],
        'google_civic_election_id': choose_election_results['google_civic_election_id'],
    }
    return results


def voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id):
    status = ''

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        status += "VALID_VOTER_DEVICE_ID_MISSING "
        error_json_data = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'ballot_found':                 False,
            'ballot_item_list':             [],
            'google_civic_election_id':     google_civic_election_id,
            'text_for_map_search':          '',
            'substituted_address_nearby':   '',
            'ballot_caveat':                '',
            'is_from_substituted_address':  False,
            'is_from_test_ballot':          False,
        }
        return error_json_data

    voter_device_link = voter_device_link_results['voter_device_link']
    voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        status += " " + "VALID_VOTER_ID_MISSING"
        error_json_data = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'ballot_found':                 False,
            'ballot_item_list':             [],
            'google_civic_election_id':     google_civic_election_id,
            'text_for_map_search':          '',
            'substituted_address_nearby':   '',
            'ballot_caveat':                '',
            'is_from_substituted_address':  False,
            'is_from_test_ballot':          False,
        }
        return error_json_data

    voter_address_manager = VoterAddressManager()
    voter_address_id = 0
    address_type = BALLOT_ADDRESS
    voter_address_results = voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)
    status += " " + voter_address_results['status']
    if not positive_value_exists(voter_address_results['voter_address_has_value']):
        error_json_data = {
            'status':                       status,
            'success':                      voter_address_results['success'],
            'voter_device_id':              voter_device_id,
            'ballot_found':                 False,
            'ballot_item_list':             [],
            'google_civic_election_id':     0,
            'text_for_map_search':          '',
            'substituted_address_nearby':   '',
            'ballot_caveat':                '',
            'is_from_substituted_address':  False,
            'is_from_test_ballot':          False,
        }
        return error_json_data

    voter_address = voter_address_results['voter_address']

    results = choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id, voter_address)
    status += " " + results['status']
    if not results['voter_ballot_saved_found']:
        if positive_value_exists(voter_address.text_for_map_search):
            ballot_caveat = "We could not find a ballot near '{text_for_map_search}'.".format(
                text_for_map_search=voter_address.text_for_map_search)
        else:
            ballot_caveat = "Please save your address so we can find your ballot."

        error_json_data = {
            'status':                       status,
            'success':                      True,
            'voter_device_id':              voter_device_id,
            'ballot_found':                 False,
            'ballot_item_list':             [],
            'google_civic_election_id':     0,
            'text_for_map_search':          voter_address.text_for_map_search,
            'substituted_address_nearby':   '',
            'ballot_caveat':                ballot_caveat,
            'is_from_substituted_address':  False,
            'is_from_test_ballot':          False,
        }
        return error_json_data

    google_civic_election_id = results['google_civic_election_id']
    voter_ballot_saved = results['voter_ballot_saved']

    # Update voter_device_link
    if voter_device_link.google_civic_election_id != google_civic_election_id:
        voter_device_link_manager.update_voter_device_link_with_election_id(voter_device_link, google_civic_election_id)

    # Update voter_address to include matching google_civic_election_id and voter_ballot_saved entry
    if positive_value_exists(google_civic_election_id):
        voter_address.google_civic_election_id = google_civic_election_id
        voter_address_manager.update_existing_voter_address_object(voter_address)

        # Get and return the ballot_item_list
        results = voter_ballot_items_retrieve_for_one_election_for_api(voter_device_id, voter_id,
                                                                       google_civic_election_id)

        if len(results['ballot_item_list']) == 0:
            try:
                # Heal the data
                voter_ballot_saved.delete()
                # TODO DALE DELETE ANY EXISTING BALLOT ITEMS??
                status += "DELETED_VOTER_BALLOT_SAVED_WITH_EMPTY_BALLOT_ITEM_LIST "
            except Exception as e:
                status += "UNABLE_TO_DELETE_VOTER_BALLOT_SAVED "
        elif not positive_value_exists(voter_ballot_saved.election_description_text) \
                or not positive_value_exists(voter_ballot_saved.election_date_text()):
            try:
                election_manager = ElectionManager()
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    if not positive_value_exists(voter_ballot_saved.election_description_text):
                        voter_ballot_saved.election_description_text = election.election_name
                    if not positive_value_exists(voter_ballot_saved.election_date_text()):
                        voter_ballot_saved.election_date = \
                            datetime.strptime(election.election_day_text, "%Y-%m-%d").date()
                if voter_address.text_for_map_search != voter_ballot_saved.original_text_for_map_search:
                    voter_ballot_saved.original_text_for_map_search = voter_address.text_for_map_search
                voter_ballot_saved.save()
            except Exception as e:
                status += "Failed to update election_name or original_text_for_map_search "
        elif voter_ballot_saved.original_text_for_map_search != voter_address.text_for_map_search:
            try:
                voter_ballot_saved.original_text_for_map_search = voter_address.text_for_map_search
                voter_ballot_saved.save()
            except Exception as e:
                status += "Failed to update original_text_for_map_search"

        status += " " + results['status']
        json_data = {
            'status':                       status,
            'success':                      True,
            'voter_device_id':              voter_device_id,
            'ballot_found':                 True,
            'ballot_item_list':             results['ballot_item_list'],
            'google_civic_election_id':     google_civic_election_id,
            'election_name':                voter_ballot_saved.election_description_text,
            'election_date':                voter_ballot_saved.election_date_text(),
            'text_for_map_search':          voter_ballot_saved.original_text_for_map_search,
            'substituted_address_nearby':   voter_ballot_saved.substituted_address_nearby,
            'ballot_caveat':                voter_ballot_saved.ballot_caveat(),
            'is_from_substituted_address':  voter_ballot_saved.is_from_substituted_address,
            'is_from_test_ballot':          voter_ballot_saved.is_from_test_ballot,
        }
        return json_data

    status += " " + "NO_VOTER_BALLOT_SAVED_FOUND"
    error_json_data = {
        'status':                       status,
        'success':                      True,
        'voter_device_id':              voter_device_id,
        'ballot_found':                 False,
        'ballot_item_list':             [],
        'google_civic_election_id':     0,
        'text_for_map_search':          '',
        'substituted_address_nearby':   '',
        'ballot_caveat':                '',
        'is_from_substituted_address':  False,
        'is_from_test_ballot':          False,
    }
    return error_json_data


def choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id, voter_address):
    voter_id = voter_device_link.voter_id
    status = ""

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        results = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'voter_ballot_saved_found': False,
            'voter_ballot_saved':       None,
        }
        return results

    # This routine finds a ballot saved for this voter
    results = choose_election_from_existing_data(voter_device_link, google_civic_election_id, voter_address)
    status += results['status']
    if results['voter_ballot_saved_found']:
        # Return voter_ballot_saved
        return results

    # If here, then we need to either:
    # 1) Get ballot data from Google Civic for the actual VoterAddress
    # 2) Copy ballot data from a nearby address, previously retrieved from Google Civic and cached within We Vote, or
    #    generated within We Vote (google_civic_election_id >= 1000000
    # 3) Get test ballot data from Google Civic
    results = generate_ballot_data(voter_device_link, voter_address)
    status += results['status']
    if results['voter_ballot_saved_found']:
        # Return voter_ballot_saved
        return results

    status += "BALLOT_NOT_FOUND_OR_GENERATED-SUFFICIENT_ADDRESS_PROBABLY_MISSING"
    results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': google_civic_election_id,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None,
    }
    return results


def generate_ballot_data(voter_device_link, voter_address):
    voter_device_id = voter_device_link.voter_device_id
    voter_id = voter_device_link.voter_id
    voter_ballot_saved_manager = VoterBallotSavedManager()
    status = ""

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID"
        results = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': 0,
            'voter_ballot_saved_found': False,
            'voter_ballot_saved':       VoterBallotSaved()
        }
        return results

    # If a partial address doesn't exist, exit because we can't generate a ballot without an address
    if not positive_value_exists(voter_address.text_for_map_search):
        status += "VOTER_ADDRESS_BLANK"
        results = {
            'status':                   status,
            'success':                  True,
            'google_civic_election_id': 0,
            'voter_ballot_saved_found': False,
            'voter_ballot_saved':       None,
        }
        return results

    # 1) Get ballot data from Google Civic for the actual VoterAddress
    text_for_map_search = voter_address.text_for_map_search
    use_test_election = False
    results = voter_ballot_items_retrieve_from_google_civic_for_api(voter_device_id, text_for_map_search,
                                                                    use_test_election)
    status += results['status']
    if results['google_civic_election_id'] and results['contests_retrieved']:
        is_from_substituted_address = False
        substituted_address_nearby = ''
        is_from_test_address = False

        # We update the voter_address with this google_civic_election_id outside of this function

        # Save the meta information for this ballot data
        save_results = voter_ballot_saved_manager.create_voter_ballot_saved(
            voter_id,
            results['google_civic_election_id'],
            results['election_date_text'],
            results['election_description_text'],
            results['text_for_map_search'],
            substituted_address_nearby,
            is_from_substituted_address,
            is_from_test_address
        )
        status += save_results['status']
        results = {
            'status':                   status,
            'success':                  save_results['success'],
            'google_civic_election_id': save_results['google_civic_election_id'],
            'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
            'voter_ballot_saved':       save_results['voter_ballot_saved'],
        }
        return results

    # 2) Copy ballot data from a nearby address, previously retrieved from Google Civic and cached within We Vote
    copy_results = copy_existing_ballot_items_from_stored_ballot(voter_id, text_for_map_search)
    status += copy_results['status']
    if copy_results['ballot_returned_copied']:
        is_from_substituted_address = True
        is_from_test_address = False
        save_results = voter_ballot_saved_manager.create_voter_ballot_saved(
            voter_id,
            copy_results['google_civic_election_id'],
            copy_results['election_date_text'],
            copy_results['election_description_text'],
            text_for_map_search,
            copy_results['substituted_address_nearby'],
            is_from_substituted_address,
            is_from_test_address
        )
        status += save_results['status']
        results = {
            'status':                   status,
            'success':                  save_results['success'],
            'google_civic_election_id': save_results['google_civic_election_id'],
            'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
            'voter_ballot_saved':       save_results['voter_ballot_saved'],
        }
        return results

    # 3) Get test ballot data from Google Civic
    # use_test_election = True
    # results = voter_ballot_items_retrieve_from_google_civic_for_api(voter_device_id, text_for_map_search,
    #                                                                 use_test_election)
    # if results['google_civic_election_id']:
    #     is_from_substituted_address = False
    #     substituted_address_nearby = ''
    #     is_from_test_address = True
        # Since this is a test address, we don't want to save the google_civic_election_id (of 2000)
        # with the voter_address
    #     save_results = voter_ballot_saved_manager.create_voter_ballot_saved(
    #         voter_id,
    #         results['google_civic_election_id'],
    #         results['election_date_text'],
    #         results['election_description_text'],
    #         results['text_for_map_search'],
    #         substituted_address_nearby,
    #         is_from_substituted_address,
    #         is_from_test_address
    #     )
    #     results = {
    #         'status':                   save_results['status'],
    #         'success':                  save_results['success'],
    #         'google_civic_election_id': save_results['google_civic_election_id'],
    #         'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
    #         'voter_ballot_saved':       save_results['voter_ballot_saved'],
    #     }
    #     return results

    status += " UNABLE_TO_GENERATE_BALLOT_DATA "
    results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None,
    }
    return results


def voter_ballot_list_retrieve_for_api(voter_id):
    voter_ballot_saved_manager = VoterBallotSavedManager()
    voter_ballot_list_for_json = []

    # If a voter_device_id was passed in, return a list of entries for that voter_id
    if positive_value_exists(voter_id):
        voter_ballot_list_results = voter_ballot_saved_manager.retrieve_ballots_per_voter_id(voter_id)
        if voter_ballot_list_results['voter_ballot_list_found']:
            voter_ballot_list = voter_ballot_list_results['voter_ballot_list']
            for one_ballot_entry in voter_ballot_list:
                one_voter_ballot_list = {
                    "google_civic_election_id":       one_ballot_entry.google_civic_election_id,
                    "election_description_text":      one_ballot_entry.election_description_text,
                    "election_date":                  one_ballot_entry.election_date_text(),
                    "original_text_for_map_search":   one_ballot_entry.original_text_for_map_search
                }
                voter_ballot_list_for_json.append(one_voter_ballot_list)
            results = {
                'status': "VOTER_BALLOT_LIST_RETRIEVED",
                'success': True,
                'voter_ballot_list_found': True,
                'voter_ballot_list': voter_ballot_list_for_json
            }
            return results
        else:
            results = {
                'status': "VOTER_BALLOT_LIST_NOT_RETRIEVED",
                'success': True,
                'voter_ballot_list_found': False,
                'voter_ballot_list': voter_ballot_list_for_json
            }
        return results


def choose_election_from_existing_data(voter_device_link, google_civic_election_id, voter_address):
    voter_id = voter_device_link.voter_id
    voter_ballot_saved_manager = VoterBallotSavedManager()
    status = ""

    # If a google_civic_election_id was passed in, then we simply return the ballot that was saved
    if positive_value_exists(google_civic_election_id):
        voter_ballot_saved_results = voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_voter_id(
            voter_id, google_civic_election_id)
        status += voter_ballot_saved_results['status']
        if voter_ballot_saved_results['voter_ballot_saved_found']:
            voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
            status += "VOTER_BALLOT_SAVED_FOUND_1 "
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': voter_ballot_saved.google_civic_election_id,
                'voter_ballot_saved_found': True,
                'voter_ballot_saved':       voter_ballot_saved
            }
            return results
        else:
            # If here, then we expected a VoterBallotSaved entry for this voter, but didn't find it
            pass

    if positive_value_exists(voter_device_link.google_civic_election_id):
        voter_ballot_saved_results = voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_voter_id(
            voter_id, voter_device_link.google_civic_election_id)
        status += voter_ballot_saved_results['status']
        if voter_ballot_saved_results['voter_ballot_saved_found']:
            voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
            status += "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_DEVICE_LINK "
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': voter_ballot_saved.google_civic_election_id,
                'voter_ballot_saved_found': True,
                'voter_ballot_saved':       voter_ballot_saved
            }
            return results
        else:
            # If here, then we expected a VoterBallotSaved entry, but didn't find it. Unable to repair the data
            pass

    if voter_address.google_civic_election_id is None:
        voter_address_google_civic_election_id = 0
    else:
        voter_address_google_civic_election_id = voter_address.google_civic_election_id
    voter_address_google_civic_election_id = convert_to_int(voter_address_google_civic_election_id)
    if positive_value_exists(voter_address_google_civic_election_id) \
            and voter_address_google_civic_election_id != 2000:
        # If we have already linked an address to a VoterBallotSaved entry, use this
        voter_ballot_saved_results = voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_voter_id(
            voter_id, voter_address_google_civic_election_id)
        status += voter_ballot_saved_results['status']
        if voter_ballot_saved_results['voter_ballot_saved_found']:
            status += "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ADDRESS "
            voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': voter_ballot_saved.google_civic_election_id,
                'voter_ballot_saved_found': True,
                'voter_ballot_saved':       voter_ballot_saved
            }
            return results
        else:
            # If here, then we expected a VoterBallotSaved entry, but didn't find it. Unable to repair the data
            pass

    status += "VOTER_BALLOT_SAVED_NOT_FOUND_FROM_EXISTING_DATA "
    error_results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None
    }
    return error_results


def voter_ballot_items_retrieve_for_one_election_for_api(voter_device_id, voter_id, google_civic_election_id):
    """

    :param voter_device_id:
    :param voter_id:
    :param google_civic_election_id: This variable was passed in explicitly so we can
    get the ballot items related to that election.
    :return:
    """
    status = ""
    ballot_item_list_manager = BallotItemListManager()

    ballot_item_list = []
    ballot_items_to_display = []
    results = {}
    try:
        results = ballot_item_list_manager.retrieve_all_ballot_items_for_voter(voter_id, google_civic_election_id)
        success = results['success']
        status += results['status']
        ballot_item_list = results['ballot_item_list']
    except Exception as e:
        status += 'FAILED voter_ballot_items_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        for ballot_item in ballot_item_list:
            if ballot_item.contest_office_we_vote_id:
                kind_of_ballot_item = OFFICE
                ballot_item_id = ballot_item.contest_office_id
                we_vote_id = ballot_item.contest_office_we_vote_id
                try:
                    candidate_list_object = CandidateCampaignListManager()
                    results = candidate_list_object.retrieve_all_candidates_for_office(ballot_item_id, we_vote_id)
                    candidates_to_display = []
                    if results['candidate_list_found']:
                        candidate_list = results['candidate_list']
                        for candidate in candidate_list:
                            # This should match values returned in candidates_retrieve_for_api
                            one_candidate = {
                                'id':                           candidate.id,
                                'we_vote_id':                   candidate.we_vote_id,
                                'ballot_item_display_name':     candidate.display_candidate_name(),
                                'candidate_photo_url_large':    candidate.we_vote_hosted_profile_image_url_large
                                    if positive_value_exists(candidate.we_vote_hosted_profile_image_url_large)
                                    else candidate.candidate_photo_url(),
                                'candidate_photo_url_medium':   candidate.we_vote_hosted_profile_image_url_medium,
                                'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
                                'party':                        candidate.political_party_display(),
                                'order_on_ballot':              candidate.order_on_ballot,
                                'kind_of_ballot_item':          CANDIDATE,
                                'twitter_handle':               candidate.candidate_twitter_handle,
                                'twitter_description':          candidate.twitter_description,
                                'twitter_followers_count':      candidate.twitter_followers_count,
                            }
                            candidates_to_display.append(one_candidate.copy())
                except Exception as e:
                    # status = 'FAILED candidates_retrieve. ' \
                    #          '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
                    candidates_to_display = []
                    if hasattr(results, 'status'):
                        status += results['status'] + " "
                one_ballot_item = {
                    'ballot_item_display_name':     ballot_item.ballot_item_display_name,
                    'google_civic_election_id':     ballot_item.google_civic_election_id,
                    'google_ballot_placement':      ballot_item.google_ballot_placement,
                    'local_ballot_order':           ballot_item.local_ballot_order,
                    'kind_of_ballot_item':          kind_of_ballot_item,
                    'id':                           ballot_item_id,
                    'we_vote_id':                   we_vote_id,
                    'candidate_list':               candidates_to_display,
                }
                ballot_items_to_display.append(one_ballot_item.copy())
            elif ballot_item.contest_measure_we_vote_id:
                kind_of_ballot_item = MEASURE
                ballot_item_id = ballot_item.contest_measure_id
                we_vote_id = ballot_item.contest_measure_we_vote_id
                one_ballot_item = {
                    'ballot_item_display_name':     ballot_item.ballot_item_display_name,
                    'google_civic_election_id':     ballot_item.google_civic_election_id,
                    'google_ballot_placement':      ballot_item.google_ballot_placement,
                    'local_ballot_order':           ballot_item.local_ballot_order,
                    'measure_subtitle':             ballot_item.measure_subtitle,
                    'kind_of_ballot_item':          kind_of_ballot_item,
                    'id':                           ballot_item_id,
                    'we_vote_id':                   we_vote_id,
                }
                ballot_items_to_display.append(one_ballot_item.copy())

        results = {
            'status': 'VOTER_BALLOT_ITEMS_RETRIEVED',
            'success': True,
            'voter_device_id': voter_device_id,
            'ballot_item_list': ballot_items_to_display,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        results = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'ballot_item_list': [],
            'google_civic_election_id': google_civic_election_id,
        }
    return results


def ballot_item_options_retrieve_for_api(google_civic_election_id=0, state_code=''):
    """
    This function returns a normalized list of candidates and measures so we can pre-populate form fields.
    Not specific to one voter.
    :param google_civic_election_id:
    :param state_code:
    :return:
    """

    status = ""
    try:
        candidate_list_object = CandidateCampaignListManager()
        results = candidate_list_object.retrieve_all_candidates_for_upcoming_election(google_civic_election_id,
                                                                                      state_code)
        candidate_success = results['success']
        status += results['status']
        candidate_list = results['candidate_list_light']
    except Exception as e:
        status += 'FAILED ballot_item_options_retrieve_for_api, candidate_list. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        candidate_list = []
        candidate_success = False

    try:
        office_list_object = ContestOfficeListManager()
        results = office_list_object.retrieve_all_offices_for_upcoming_election(google_civic_election_id, state_code)
        office_success = results['success']
        status += ' ' + results['status']
        office_list = results['office_list_light']
    except Exception as e:
        status += 'FAILED ballot_item_options_retrieve_for_api, office_list. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        office_list = []
        office_success = False

    try:
        measure_list_object = ContestMeasureList()
        results = measure_list_object.retrieve_all_measures_for_upcoming_election(google_civic_election_id, state_code)
        measure_success = results['success']
        status += ' ' + results['status']
        measure_list = results['measure_list_light']
    except Exception as e:
        status += 'FAILED ballot_item_options_retrieve_for_api, measure_list. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        measure_list = []
        measure_success = False

    ballot_items_to_display = []
    if candidate_success and len(candidate_list):
        for candidate in candidate_list:
            ballot_items_to_display.append(candidate.copy())

    if office_success and len(office_list):
        for office in office_list:
            ballot_items_to_display.append(office.copy())

    if measure_success and len(measure_list):
        for measure in measure_list:
            ballot_items_to_display.append(measure.copy())

    json_data = {
        'status': status,
        'success': candidate_success or measure_success,
        'ballot_item_list': ballot_items_to_display,
        'google_civic_election_id': google_civic_election_id,
    }
    results = {
        'status': status,
        'success': candidate_success or measure_success,
        'google_civic_election_id': google_civic_election_id,  # We want to save google_civic_election_id in cookie
        'json_data': json_data,
    }
    return results
