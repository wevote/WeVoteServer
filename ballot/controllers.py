# ballot/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItemListManager, BallotItemManager, BallotReturnedListManager, BallotReturnedManager, \
    CANDIDATE, copy_existing_ballot_items_from_stored_ballot, OFFICE, MEASURE, \
    refresh_ballot_items_for_voter_copied_from_one_polling_location, VoterBallotSaved, VoterBallotSavedManager
from candidate.models import CandidateCampaignListManager
from config.base import get_environment_variable
from datetime import datetime, timedelta
from election.models import ElectionManager, fetch_next_election_for_state
from exception.models import handle_exception
from import_export_ballotpedia.controllers import voter_ballot_items_retrieve_from_ballotpedia_for_api
from import_export_google_civic.controllers import \
    refresh_voter_ballot_items_from_google_civic_from_voter_ballot_saved, \
    voter_ballot_items_retrieve_from_google_civic_for_api
from measure.models import ContestMeasureList, ContestMeasureManager
from office.models import ContestOfficeManager, ContestOfficeListManager
from polling_location.models import PollingLocationManager
import pytz
from voter.models import BALLOT_ADDRESS, VoterAddress, VoterAddressManager, VoterDeviceLinkManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_code_from_address_string, positive_value_exists, \
    process_request_from_master
from geopy.geocoders import get_geocoder_for_service

logger = wevote_functions.admin.get_logger(__name__)

GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
BALLOT_ITEMS_SYNC_URL = get_environment_variable("BALLOT_ITEMS_SYNC_URL")  # ballotItemsSyncOut
BALLOT_RETURNED_SYNC_URL = get_environment_variable("BALLOT_RETURNED_SYNC_URL")  # ballotReturnedSyncOut


def ballot_items_import_from_master_server(request, google_civic_election_id, state_code):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers

    if positive_value_exists(google_civic_election_id) and positive_value_exists(state_code):
        params = {
            "key":                      WE_VOTE_API_KEY,
            "google_civic_election_id": str(google_civic_election_id),
            "state_code":               state_code,
        }
    elif positive_value_exists(google_civic_election_id):
        params = {
            "key":                      WE_VOTE_API_KEY,
            "google_civic_election_id": str(google_civic_election_id)
        }
    elif positive_value_exists(state_code):
        params = {
            "key":                      WE_VOTE_API_KEY,
            "state_code":               state_code,
        }
    else:
        import_results = {
            'success': False,
            'status': "BALLOT_ITEMS_IMPORT_COULD_NOT_RUN-INSUFFICIENT_VARIABLES",
        }
        return import_results

    import_results, structured_json = \
        process_request_from_master(request, "Loading Ballot Items from We Vote Master servers",
                                    BALLOT_ITEMS_SYNC_URL, params)

    if not import_results['success']:
        return import_results

    try:
        if 'success' in structured_json:  # On error, you get: {'success': False, 'status': 'BALLOT_ITEM_LIST_MISSING'}
            import_results = {
                'success': False,
                'status': structured_json['status'] + ": Did you set the correct state for syncing this election?",
            }
        else:
            results = filter_ballot_items_structured_json_for_local_duplicates(structured_json)
            filtered_structured_json = results['structured_json']
            duplicates_removed = results['duplicates_removed']

            import_results = ballot_items_import_from_structured_json(filtered_structured_json)
            import_results['duplicates_removed'] = duplicates_removed
    except Exception as e:
        import_results = {
            'success': False,
            'status': "FAILED_TO_GET_JSON_FROM_MASTER_SERVER",
        }

    return import_results


def ballot_returned_import_from_master_server(request, google_civic_election_id, state_code):
    """
    Get the json data, and either create new entries or update existing
    Request json file from We Vote servers

    :param request:
    :param google_civic_election_id:
    :param state_code:
    :return:
    """

    import_results, structured_json = process_request_from_master(
        request, "Loading Ballot Returned entries (saved ballots, specific to one location) from WeVote Master servers",
        BALLOT_RETURNED_SYNC_URL,
        {
            "key": WE_VOTE_API_KEY,  # This comes from an environment variable
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": str(state_code),
        }
    )

    print("... the master server returned " + str(len(structured_json)) + " polling locations for election " +
          str(google_civic_election_id) + " in state " + str(state_code))

    if import_results['success']:
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
        state_code = one_ballot_item['state_code'] \
            if 'state_code' in one_ballot_item else ''
        polling_location_we_vote_id = one_ballot_item['polling_location_we_vote_id'] \
            if 'polling_location_we_vote_id' in one_ballot_item else ''
        contest_office_we_vote_id = None
        contest_measure_we_vote_id = None
        # Check to see if there is an entry that matches in all critical ways, minus the
        # contest_office_we_vote_id or contest_measure_we_vote_id. That is, an entry for a
        # google_civic_election_id + polling_location_we_vote_id that has the same ballot_item_display_name,
        # but different contest_office_we_vote_id or contest_measure_we_vote_id
        # contest_office_we_vote_id = one_ballot_item['contest_office_we_vote_id'] \
        #     if 'contest_office_we_vote_id' in one_ballot_item else ''
        # contest_measure_we_vote_id = one_ballot_item['contest_measure_we_vote_id'] \
        #     if 'contest_measure_we_vote_id' in one_ballot_item else ''
        voter_id = 0
        results = ballot_item_list_manager.retrieve_possible_duplicate_ballot_items(
            ballot_item_display_name, google_civic_election_id,
            polling_location_we_vote_id, voter_id,
            contest_office_we_vote_id, contest_measure_we_vote_id, state_code)

        if results['ballot_item_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_ballot_item)

        count = duplicates_removed + len(filtered_structured_json)
        if not count % 10000:
            print("... ballot items checked for duplicates: " + str(count) + " of " + str(len(structured_json)))

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
        processed = duplicates_removed + len(filtered_structured_json)
        if processed % 5000 == 0:
            print("... pre-processed " + str(processed) + " ballot returned imports")

        processed = duplicates_removed + len(filtered_structured_json)
        if not processed % 10000:
            print("... ballots returned, checked for duplicates: " + str(processed) + " of " +
                  str(len(structured_json)))

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
        state_code = one_ballot_item['state_code'] if 'state_code' in one_ballot_item else ''
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

        defaults = {}
        if proceed_to_update_or_create:
            ballot_item_display_name = one_ballot_item['ballot_item_display_name'] \
                if 'ballot_item_display_name' in one_ballot_item else ''
            measure_subtitle = one_ballot_item['measure_subtitle'] if 'measure_subtitle' in one_ballot_item else ''
            measure_text = one_ballot_item['measure_text'] if 'measure_text' in one_ballot_item else ''
            google_ballot_placement = one_ballot_item['google_ballot_placement'] \
                if 'google_ballot_placement' in one_ballot_item else 0
            local_ballot_order = one_ballot_item['local_ballot_order'] \
                if 'local_ballot_order' in one_ballot_item else ''

            defaults['measure_url'] = one_ballot_item['measure_url'] if 'measure_url' in one_ballot_item else ''
            defaults['yes_vote_description'] = one_ballot_item['yes_vote_description'] \
                if 'yes_vote_description' in one_ballot_item else ''
            defaults['no_vote_description'] = one_ballot_item['no_vote_description'] \
                if 'no_vote_description' in one_ballot_item else ''

            contest_office_id = 0
            contest_measure_id = 0

            results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure_id, contest_measure_we_vote_id, state_code, defaults)

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

        count = ballot_items_saved + ballot_items_updated
        if not count % 10000:
            print("... processed for update/create: " + str(count) + " of " + str(len(structured_json)))

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
            proceed_to_update_or_create = True

            # Here we check for a local polling_location. We used to require the polling location be found,
            #  but no longer.
            results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
            if results['polling_location_found']:
                polling_location_found = True
            else:
                polling_location_found = False
        else:
            proceed_to_update_or_create = False

        if proceed_to_update_or_create:
            election_day_text = one_ballot_returned['election_day_text'] if 'election_day_text' in one_ballot_returned else False
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
            if latitude is False or latitude is None or longitude is False or longitude is None:
                if text_for_map_search is False:
                    logger.warning("Bad data received in ballot_returned_import_from_structured_json:" +
                                   str(one_ballot_returned))
                else:
                    latitude, longitude = heal_geo_coordinates(text_for_map_search)

            results = ballot_returned_manager.update_or_create_ballot_returned(
                polling_location_we_vote_id, voter_id, google_civic_election_id, election_day_text,
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
        processed = ballot_returned_saved + ballot_returned_updated + ballot_returned_not_processed
        if processed % 5000 == 0:
            print("... processed " + str(processed) + " ballot returned imports")

        processed = ballot_returned_saved + ballot_returned_updated + ballot_returned_not_processed
        if not processed % 10000:
            print("... ballots returned, processed for update/create: " + str(processed) + " of " + str(len(structured_json)))

    status = "BALLOT_RETURNED_IMPORT_PROCESS_COMPLETED"

    ballot_returned_results = {
        'success':          True,
        'status':           status,
        'saved':            ballot_returned_saved,
        'updated':          ballot_returned_updated,
        'not_processed':    ballot_returned_not_processed,
    }
    return ballot_returned_results


def heal_geo_coordinates(text_for_map_search):
    longitude = None
    latitude = None
    try:
        google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        location = google_client.geocode(text_for_map_search, sensor=False)
        if location is None:
            status = 'Could not find location matching "{}" '.format(text_for_map_search)
            logger.debug(status)
        else:
            latitude = location.latitude
            longitude = location.longitude
    except Exception as e:
        pass
    return latitude, longitude


def move_ballot_items_to_another_measure(from_contest_measure_id, from_contest_measure_we_vote_id,
                                         to_contest_measure_id, to_contest_measure_we_vote_id,
                                         updated_contest_measure):
    status = ''
    success = True
    ballot_item_entries_moved = 0
    ballot_item_entries_not_moved = 0
    ballot_item_manager = BallotItemManager()
    ballot_item_list_manager = BallotItemListManager()

    # We search on both from_office_id and from_office_we_vote_id in case there is some data that needs
    # to be healed
    all_ballot_items_results = ballot_item_list_manager.retrieve_all_ballot_items_for_contest_measure(
        from_contest_measure_id, from_contest_measure_we_vote_id)
    from_ballot_item_list = all_ballot_items_results['ballot_item_list']

    for from_ballot_item_entry in from_ballot_item_list:
        # First see if a ballot_item entry exists for the to_contest_measure and polling_location or voter
        empty_ballot_item_display_name = ""
        empty_contest_office_we_vote_id = ""
        state_code = ""
        results = ballot_item_list_manager.retrieve_possible_duplicate_ballot_items(
            empty_ballot_item_display_name, from_ballot_item_entry.google_civic_election_id,
            from_ballot_item_entry.polling_location_we_vote_id, from_ballot_item_entry.voter_id,
            empty_contest_office_we_vote_id, to_contest_measure_we_vote_id, state_code)
        if results['ballot_item_list_count'] > 0:
            # At least one found so we don't want to create another one
            to_ballot_item_list = results['ballot_item_list']
            to_ballot_item_entry = to_ballot_item_list[0]
            ballot_item_entries_not_moved += 1
            ballot_item_manager.refresh_cached_ballot_item_measure_info(
                to_ballot_item_entry, updated_contest_measure)

            # Delete from_ballot_item_entry
            try:
                from_ballot_item_entry.delete()
            except Exception as e:
                success = False
                status += "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_DELETE_FROM_BALLOT_ITEM_ENTRY "
        else:
            # If duplicates weren't found, then update the existing ballot item to use the new contest_measure
            try:
                from_ballot_item_entry.contest_measure_id = to_contest_measure_id
                from_ballot_item_entry.contest_measure_we_vote_id = to_contest_measure_we_vote_id
                from_ballot_item_entry.save()
                ballot_item_entries_moved += 1
                ballot_item_manager.refresh_cached_ballot_item_measure_info(
                    from_ballot_item_entry, updated_contest_measure)
            except Exception as e:
                success = False
                status += "MOVE_TO_ANOTHER_CONTEST_MEASURE-UNABLE_TO_SAVE_NEW_ballot_item "
                ballot_item_entries_not_moved += 1

    results = {
        'status': status,
        'success': success,
        'from_contest_measure_id': from_contest_measure_id,
        'from_contest_measure_we_vote_id': from_contest_measure_we_vote_id,
        'to_contest_measure_id': to_contest_measure_id,
        'to_contest_measure_we_vote_id': to_contest_measure_we_vote_id,
        'ballot_item_entries_moved': ballot_item_entries_moved,
        'ballot_item_entries_not_moved': ballot_item_entries_not_moved,
    }
    return results


def move_ballot_items_to_another_office(from_contest_office_id, from_contest_office_we_vote_id,
                                        to_contest_office_id, to_contest_office_we_vote_id,
                                        updated_contest_office):
    status = ''
    success = True
    ballot_item_entries_moved = 0
    ballot_item_entries_not_moved = 0
    ballot_item_manager = BallotItemManager()
    ballot_item_list_manager = BallotItemListManager()

    # We search on both from_office_id and from_office_we_vote_id in case there is some data that needs
    # to be healed
    all_ballot_items_results = ballot_item_list_manager.retrieve_all_ballot_items_for_contest_office(
        from_contest_office_id, from_contest_office_we_vote_id)
    from_ballot_item_list = all_ballot_items_results['ballot_item_list']

    for from_ballot_item_entry in from_ballot_item_list:
        # First see if a ballot_item entry exists for the to_contest_office and polling_location or voter
        empty_ballot_item_display_name = ""
        empty_contest_measure_we_vote_id = ""
        state_code = ""
        results = ballot_item_list_manager.retrieve_possible_duplicate_ballot_items(
            empty_ballot_item_display_name, from_ballot_item_entry.google_civic_election_id,
            from_ballot_item_entry.polling_location_we_vote_id, from_ballot_item_entry.voter_id,
            to_contest_office_we_vote_id, empty_contest_measure_we_vote_id, state_code)
        if results['ballot_item_list_count'] > 0:
            # At least one found so we don't want to create another one
            to_ballot_item_list = results['ballot_item_list']
            to_ballot_item_entry = to_ballot_item_list[0]
            ballot_item_entries_not_moved += 1
            ballot_item_manager.refresh_cached_ballot_item_office_info(
                to_ballot_item_entry, updated_contest_office)

            # Delete from_ballot_item_entry
            try:
                from_ballot_item_entry.delete()
            except Exception as e:
                success = False
                status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_DELETE_FROM_BALLOT_ITEM_ENTRY "
        else:
            # If duplicates weren't found, then update the existing ballot item to use the new contest_office
            try:
                from_ballot_item_entry.contest_office_id = to_contest_office_id
                from_ballot_item_entry.contest_office_we_vote_id = to_contest_office_we_vote_id
                from_ballot_item_entry.save()
                ballot_item_entries_moved += 1
                ballot_item_manager.refresh_cached_ballot_item_office_info(
                    from_ballot_item_entry, updated_contest_office)
            except Exception as e:
                success = False
                status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_SAVE_NEW_ballot_item "
                ballot_item_entries_not_moved += 1

    results = {
        'status':                           status,
        'success':                          success,
        'from_contest_office_id':           from_contest_office_id,
        'from_contest_office_we_vote_id':   from_contest_office_we_vote_id,
        'to_contest_office_id':             to_contest_office_id,
        'to_contest_office_we_vote_id':     to_contest_office_we_vote_id,
        'ballot_item_entries_moved':        ballot_item_entries_moved,
        'ballot_item_entries_not_moved':    ballot_item_entries_not_moved,
    }
    return results


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
    # Note that this might be an empty VoterAddress object
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


def figure_out_google_civic_election_id_voter_is_watching_by_voter_id(voter_id):
    status = 'FIGURE_OUT_BY_VOTER_ID '

    # We zero out this value  since we will never have this coming in for this function
    google_civic_election_id = 0
    voter_device_id = ""

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id, voter_id)
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
    voter_device_id = voter_device_link.voter_device_id

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
    # Note that this might be an empty VoterAddress object
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


def refresh_voter_ballots_from_polling_location(ballot_returned_from_polling_location, google_civic_election_id):
    status = ""
    success = True

    ballot_saved_manager = VoterBallotSavedManager()
    # When voters provide partial addresses, we copy their ballots from nearby polling locations
    # We want to find all voter_ballot_saved entries that came from polling_location_we_vote_id_source
    polling_location_we_vote_id_source = ballot_returned_from_polling_location.polling_location_we_vote_id

    if not positive_value_exists(polling_location_we_vote_id_source) \
            or not positive_value_exists(google_civic_election_id):
        status += "REFRESH_VOTER_BALLOTS_FROM_POLLING_LOCATION-MISSING_REQUIRED_VARIABLE(S) "
        success = False
        results = {
            'status': status,
            'success': success,
        }
        return results

    retrieve_results = ballot_saved_manager.retrieve_voter_ballot_saved_list_for_election(
        google_civic_election_id, polling_location_we_vote_id_source)
    ballots_refreshed = 0
    if retrieve_results['voter_ballot_saved_list_found']:
        voter_ballot_saved_list = retrieve_results['voter_ballot_saved_list']
        for voter_ballot_saved in voter_ballot_saved_list:
            # Neither BallotReturned nor VoterBallotSaved change when we get refreshed data from Google Civic
            if positive_value_exists(voter_ballot_saved.voter_id) \
                    and positive_value_exists(voter_ballot_saved.ballot_returned_we_vote_id):
                refresh_results = refresh_ballot_items_for_voter_copied_from_one_polling_location(
                    voter_ballot_saved.voter_id, ballot_returned_from_polling_location)

                if refresh_results['ballot_returned_copied']:
                    ballots_refreshed += 1
                else:
                    status += refresh_results['status']

    results = {
        'status':               status,
        'success':              success,
        'ballots_refreshed':    ballots_refreshed,
    }
    return results


def refresh_voter_ballots_not_copied_from_polling_location(google_civic_election_id, refresh_from_google=False):
    status = ""
    success = True
    ballots_refreshed = 0

    ballot_item_list_manager = BallotItemListManager()
    ballot_saved_manager = VoterBallotSavedManager()
    # When voters provide complete addresses, we get their ballot straight from Google Civic
    # We want to find all voter_ballot_saved entries for these voters with full addresses
    # This function does NOT reach back out to Google Civic
    retrieve_results = ballot_saved_manager.retrieve_voter_ballot_saved_list_for_election(
        google_civic_election_id, find_only_entries_not_copied_from_polling_location=True)
    if retrieve_results['voter_ballot_saved_list_found']:
        voter_ballot_saved_list = retrieve_results['voter_ballot_saved_list']
        offices_dict = {}
        measures_dict = {}
        for voter_ballot_saved in voter_ballot_saved_list:
            # Neither BallotReturned nor VoterBallotSaved change when we get refreshed data from Google Civic
            if positive_value_exists(voter_ballot_saved.voter_id):
                if positive_value_exists(refresh_from_google):
                    # 2018-May Note that when we have 10K+ voters with custom addresses, this process probably won't
                    # finish and will want to be changed to update in batches
                    refresh_results = refresh_voter_ballot_items_from_google_civic_from_voter_ballot_saved(
                        voter_ballot_saved)
                    if refresh_results['success']:
                        ballots_refreshed += 1
                    else:
                        status += refresh_results['status']
                else:
                    refresh_results = ballot_item_list_manager.refresh_ballot_items_from_master_tables(
                        voter_ballot_saved.voter_id, google_civic_election_id,
                        offices_dict, measures_dict)
                    offices_dict = refresh_results['offices_dict']
                    measures_dict = refresh_results['measures_dict']
                    if refresh_results['success']:
                        ballots_refreshed += 1
                    else:
                        status += refresh_results['status']

    results = {
        'status':               status,
        'success':              success,
        'ballots_refreshed':    ballots_refreshed,
    }
    return results


def repair_ballot_items_for_election(google_civic_election_id, refresh_from_google=False):
    saved_count = 0
    state_code_not_found_count = 0
    error_count = 0
    success = True
    office_manager = ContestOfficeManager()
    measure_manager = ContestMeasureManager()
    state_code_from_election = ""

    ballot_item_list_manager = BallotItemListManager()
    results = ballot_item_list_manager.retrieve_ballot_items_for_election_lacking_state(google_civic_election_id)

    if results['ballot_item_list_found']:
        ballot_item_list = results['ballot_item_list']

        election_manager = ElectionManager()
        election_results = election_manager.retrieve_election(google_civic_election_id)
        if election_results['election_found']:
            election = election_results['election']
            state_code_from_election = election.get_election_state()

        for one_ballot_item in ballot_item_list:
            state_code_from_office_or_measure = ""
            save_ballot_item = False
            if not positive_value_exists(state_code_from_election):
                # If here, look up the state code by from the office or measure
                if positive_value_exists(one_ballot_item.contest_office_we_vote_id):
                    state_code_from_office_or_measure = office_manager.fetch_state_code_from_we_vote_id(
                        one_ballot_item.contest_office_we_vote_id)
                elif positive_value_exists(one_ballot_item.contest_measure_we_vote_id):
                    state_code_from_office_or_measure = measure_manager.fetch_state_code_from_we_vote_id(
                        one_ballot_item.contest_measure_we_vote_id)
            try:
                # Heal the data
                if positive_value_exists(state_code_from_office_or_measure):
                    one_ballot_item.state_code = state_code_from_office_or_measure
                    save_ballot_item = True
                elif positive_value_exists(state_code_from_election):
                    one_ballot_item.state_code = state_code_from_election
                    save_ballot_item = True

                if save_ballot_item:
                    one_ballot_item.save()
                    saved_count += 1
                else:
                    state_code_not_found_count += 1
            except Exception as e:
                error_count += 1

    if positive_value_exists(saved_count):
        success = True

    count_results = ballot_item_list_manager.count_ballot_items_for_election_lacking_state(google_civic_election_id)
    ballot_item_list_count = count_results['ballot_item_list_count']

    # Now check for VoterBallotSaved entries for voter ballots that were not copied from polling locations
    #  so we can refresh the data
    refresh_ballot_results = refresh_voter_ballots_not_copied_from_polling_location(google_civic_election_id,
                                                                                    refresh_from_google)
    ballots_refreshed = refresh_ballot_results['refresh_ballot_results']

    status = "REPAIR_BALLOT_ITEMS, total count that need repair: {ballot_item_list_count}, " \
             "saved_count: {saved_count}, " \
             "state_code_not_found_count: {state_code_not_found_count}, " \
             "error_count: {error_count}\n" \
             "REFRESH: ballots_refreshed: {ballots_refreshed} " \
             "".format(ballot_item_list_count=ballot_item_list_count,
                       ballots_refreshed=ballots_refreshed,
                       saved_count=saved_count,
                       state_code_not_found_count=state_code_not_found_count,
                       error_count=error_count)
    results = {
        'status': status,
        'success': success,
    }
    return results


def voter_ballot_items_retrieve_for_api(
        voter_device_id, google_civic_election_id,
        ballot_returned_we_vote_id='', ballot_location_shortcut=''):  # voterBallotItemsRetrieve
    status = ''

    specific_ballot_requested = positive_value_exists(ballot_returned_we_vote_id) or \
        positive_value_exists(ballot_location_shortcut)

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        status += "VALID_VOTER_DEVICE_ID_MISSING "
        error_json_data = {
            'status':                               status,
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'ballot_found':                         False,
            'ballot_item_list':                     [],
            'google_civic_election_id':             google_civic_election_id,
            'text_for_map_search':                  '',
            'substituted_address_nearby':           '',
            'ballot_caveat':                        '',
            'is_from_substituted_address':          False,
            'is_from_test_ballot':                  False,
            'ballot_location_display_name':         '',
            'ballot_location_shortcut':             ballot_location_shortcut,
            'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
            'polling_location_we_vote_id_source':   '',
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
            'ballot_location_display_name':         '',
            'ballot_location_shortcut':             ballot_location_shortcut,
            'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
            'polling_location_we_vote_id_source':   '',
        }
        return error_json_data

    voter_address_manager = VoterAddressManager()
    voter_address_id = 0
    address_type = BALLOT_ADDRESS
    voter_address_results = voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)
    status += " " + voter_address_results['status']
    # Note that this might be an empty VoterAddress object
    voter_address = voter_address_results['voter_address']
    if positive_value_exists(voter_address_results['voter_address_has_value']):
        ballot_retrieval_based_on_voter_address = True
    else:
        ballot_retrieval_based_on_voter_address = False

    results = choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id, voter_address,
                                                      ballot_returned_we_vote_id, ballot_location_shortcut)
    status += " " + results['status']
    if not results['voter_ballot_saved_found']:
        if positive_value_exists(ballot_returned_we_vote_id):
            ballot_caveat = "We could not find the ballot with the id '{ballot_returned_we_vote_id}'.".format(
                ballot_returned_we_vote_id=ballot_returned_we_vote_id)
        elif positive_value_exists(ballot_location_shortcut):
            ballot_caveat = "We could not find the ballot '{ballot_location_shortcut}'.".format(
                ballot_location_shortcut=ballot_location_shortcut)
        elif positive_value_exists(voter_address.text_for_map_search):
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
            'ballot_location_display_name':         '',
            'ballot_location_shortcut':             ballot_location_shortcut,
            'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
            'polling_location_we_vote_id_source': '',
        }
        return error_json_data

    google_civic_election_id = results['google_civic_election_id']
    voter_ballot_saved = results['voter_ballot_saved']

    # Update voter_device_link
    if voter_device_link.google_civic_election_id != google_civic_election_id:
        voter_device_link_manager.update_voter_device_link_with_election_id(voter_device_link, google_civic_election_id)

    # Update voter_address to include matching google_civic_election_id and voter_ballot_saved entry
    if positive_value_exists(google_civic_election_id):
        # 2017-10-25 DALE It turns out we don't want to update the address with just the election_id unless
        #  the election was calculated from an address. We want to keep google_civic_election_id tied
        #  to the voter's address
        if ballot_retrieval_based_on_voter_address:
            voter_address.google_civic_election_id = google_civic_election_id
            voter_address_manager.update_existing_voter_address_object(voter_address)

        # Get and return the ballot_item_list
        results = voter_ballot_items_retrieve_for_one_election_for_api(voter_device_id, voter_id,
                                                                       google_civic_election_id)

        if len(results['ballot_item_list']) == 0:
            try:
                # Heal the data
                voter_ballot_saved.delete()
                status += "DELETED_VOTER_BALLOT_SAVED_WITH_EMPTY_BALLOT_ITEM_LIST "
            except Exception as e:
                status += "UNABLE_TO_DELETE_VOTER_BALLOT_SAVED "
        elif not positive_value_exists(voter_ballot_saved.election_description_text) \
                or not positive_value_exists(voter_ballot_saved.election_day_text()):
            try:
                election_manager = ElectionManager()
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    if not positive_value_exists(voter_ballot_saved.election_description_text):
                        voter_ballot_saved.election_description_text = election.election_name
                    if not positive_value_exists(voter_ballot_saved.election_day_text()):
                        voter_ballot_saved.election_date = \
                            datetime.strptime(election.election_day_text, "%Y-%m-%d").date()
                if voter_address.text_for_map_search != voter_ballot_saved.original_text_for_map_search and \
                        not specific_ballot_requested:
                    # We don't want to change the voter_ballot_saved.original_text_for_map_search to be
                    #  the voter's address if we copied this ballot based on ballot_returned_we_vote_id
                    #  or ballot_location_shortcut
                    voter_ballot_saved.original_text_for_map_search = voter_address.text_for_map_search
                voter_ballot_saved.save()
            except Exception as e:
                status += "Failed to update election_name or original_text_for_map_search "
        elif voter_ballot_saved.original_text_for_map_search != voter_address.text_for_map_search and \
                not specific_ballot_requested:
            # We don't want to change the voter_ballot_saved.original_text_for_map_search to be the voter's address
            #  if we copied this ballot based on ballot_returned_we_vote_id or ballot_location_shortcut
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
            'election_day_text':            voter_ballot_saved.election_day_text(),
            'text_for_map_search':          voter_ballot_saved.original_text_for_map_search,
            'substituted_address_nearby':   voter_ballot_saved.substituted_address_nearby,
            'ballot_caveat':                voter_ballot_saved.ballot_caveat(),
            'is_from_substituted_address':  voter_ballot_saved.is_from_substituted_address,
            'is_from_test_ballot':          voter_ballot_saved.is_from_test_ballot,
            'ballot_location_display_name': voter_ballot_saved.ballot_location_display_name,
            'ballot_location_shortcut':     voter_ballot_saved.ballot_location_shortcut,
            'ballot_returned_we_vote_id':   voter_ballot_saved.ballot_returned_we_vote_id,
            'polling_location_we_vote_id_source': voter_ballot_saved.polling_location_we_vote_id_source,
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
        'ballot_location_display_name':         '',
        'ballot_location_shortcut':             ballot_location_shortcut,
        'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
        'polling_location_we_vote_id_source':   '',
    }
    return error_json_data


def choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id, voter_address,
                                            ballot_returned_we_vote_id='', ballot_location_shortcut=''):
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

    # This code finds a ballot saved for this voter
    if positive_value_exists(ballot_returned_we_vote_id):
        results = choose_voter_ballot_saved_from_existing_ballot_returned_we_vote_id(
            voter_device_link, ballot_returned_we_vote_id)
        status += results['status']
        if results['voter_ballot_saved_found']:
            # Return voter_ballot_saved
            return results
    elif positive_value_exists(ballot_location_shortcut):
        results = choose_voter_ballot_saved_from_existing_ballot_location_shortcut(
            voter_device_link, ballot_location_shortcut)
        status += results['status']
        if results['voter_ballot_saved_found']:
            # Return voter_ballot_saved
            return results
    else:
        results = choose_election_from_existing_data(voter_device_link, google_civic_election_id, voter_address)
        status += results['status']
        if results['voter_ballot_saved_found']:
            # Return voter_ballot_saved
            return results

    # If here, then we need to either:
    # 1) Copy ballot data from a specific location (using either ballot_returned_we_vote_id or ballot_location_shortcut)
    # 2) Get ballot data from Ballotpedia or Google Civic for the actual VoterAddress
    # 3) Copy ballot data from a nearby address, previously retrieved from Google Civic and cached within We Vote, or
    #    generated within We Vote (google_civic_election_id >= 1000000
    # 4) Get test ballot data from Google Civic
    results = generate_ballot_data(voter_device_link, google_civic_election_id, voter_address,
                                   ballot_returned_we_vote_id, ballot_location_shortcut)
    status += results['status']
    if results['voter_ballot_saved_found']:
        # Return voter_ballot_saved
        return results

    status += "BALLOT_NOT_FOUND_OR_GENERATED "
    results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': google_civic_election_id,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None,
    }
    return results


def generate_ballot_data(voter_device_link, google_civic_election_id, voter_address,
                         ballot_returned_we_vote_id='', ballot_location_shortcut=''):
    voter_device_id = voter_device_link.voter_device_id
    voter_id = voter_device_link.voter_id
    voter_ballot_saved_manager = VoterBallotSavedManager()
    status = ""
    specific_ballot_requested = positive_value_exists(ballot_returned_we_vote_id) or \
        positive_value_exists(ballot_location_shortcut)

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID"
        results = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': 0,
            'state_code':               '',
            'voter_ballot_saved_found': False,
            'voter_ballot_saved':       VoterBallotSaved()
        }
        return results

    if specific_ballot_requested:
        text_for_map_search = ''
        google_civic_election_id = 0
        copy_results = copy_existing_ballot_items_from_stored_ballot(
            voter_id, text_for_map_search, google_civic_election_id,
            ballot_returned_we_vote_id, ballot_location_shortcut)
        status += copy_results['status']
        if copy_results['ballot_returned_copied']:
            is_from_substituted_address = True
            is_from_test_address = False
            save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                voter_id,
                copy_results['google_civic_election_id'],
                copy_results['state_code'],
                copy_results['election_day_text'],
                copy_results['election_description_text'],
                text_for_map_search,
                copy_results['substituted_address_nearby'],
                is_from_substituted_address,
                is_from_test_address,
                copy_results['polling_location_we_vote_id_source'],
                copy_results['ballot_location_display_name'],
                copy_results['ballot_returned_we_vote_id'],
                copy_results['ballot_location_shortcut']
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
    else:
        text_for_map_search = voter_address.text_for_map_search

        if positive_value_exists(google_civic_election_id):
            # If a specific google_civic_election_id came in, we need to return a ballot in that particular election,
            # even if it isn't an election the voter has seen before.
            text_for_map_search_for_google_civic_retrieve = ""
            # Is the voter's address in a particular state?
            state_code_from_text_for_map_search = voter_address.get_state_code_from_text_for_map_search()
            if positive_value_exists(state_code_from_text_for_map_search):
                # If the voter address is for another state, then remove
                election_manager = ElectionManager()
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    # If the voter's address is in a state supported by this election, pass in the text_for_map_search
                    if election.state_code.lower() == "na" or election.state_code.lower() == "":
                        # If a National election, then we want the address passed in
                        text_for_map_search_for_google_civic_retrieve = voter_address.text_for_map_search
                    elif election.state_code.lower() == state_code_from_text_for_map_search.lower():
                        text_for_map_search_for_google_civic_retrieve = voter_address.text_for_map_search
                    else:
                        text_for_map_search_for_google_civic_retrieve = ""
            else:
                # Voter address state_code not found, so we don't use the text_for_map_search value
                text_for_map_search_for_google_civic_retrieve = ""

            # 0) Copy ballot data for an election that is in a different state than the voter
            copy_results = copy_existing_ballot_items_from_stored_ballot(
                voter_id, text_for_map_search_for_google_civic_retrieve, google_civic_election_id)
            status += copy_results['status']
            if copy_results['ballot_returned_copied']:
                # If this ballot_returned entry is the result of searching based on an address, as opposed to
                # a specific_ballot_requested, we want to update the VoterAddress
                if not specific_ballot_requested and positive_value_exists(voter_address.text_for_map_search):
                    try:
                        voter_address.ballot_location_display_name = copy_results['ballot_location_display_name']
                        voter_address.ballot_returned_we_vote_id = copy_results['ballot_returned_we_vote_id']
                        voter_address.save()
                    except Exception as e:
                        pass

                # And now store the details of this ballot for this voter
                is_from_substituted_address = True
                is_from_test_address = False
                save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                    voter_id,
                    copy_results['google_civic_election_id'],
                    copy_results['state_code'],
                    copy_results['election_day_text'],
                    copy_results['election_description_text'],
                    text_for_map_search,
                    copy_results['substituted_address_nearby'],
                    is_from_substituted_address,
                    is_from_test_address,
                    copy_results['polling_location_we_vote_id_source'],
                    copy_results['ballot_location_display_name'],
                    copy_results['ballot_returned_we_vote_id'],
                    copy_results['ballot_location_shortcut']
                )
                status += save_results['status']
                results = {
                    'status': status,
                    'success': save_results['success'],
                    'google_civic_election_id': save_results['google_civic_election_id'],
                    'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                    'voter_ballot_saved': save_results['voter_ballot_saved'],
                }
                return results
            else:
                # If here, then we couldn't find or generate a voter_ballot_saved entry
                results = {
                    'status': status,
                    'success': False,
                    'google_civic_election_id': google_civic_election_id,
                    'voter_ballot_saved_found': False,
                    'voter_ballot_saved': VoterBallotSaved(),
                }
                return results

        # If a partial address doesn't exist, exit because we can't generate a ballot without an address
        if not positive_value_exists(voter_address.text_for_map_search):
            status += "VOTER_ADDRESS_BLANK"
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': 0,
                'state_code':               '',
                'voter_ballot_saved_found': False,
                'voter_ballot_saved':       None,
            }
            return results

        default_election_data_source_is_ballotpedia = False
        if default_election_data_source_is_ballotpedia:
            # 1a) Get ballot data from Ballotpedia for the actual VoterAddress
            ballotpedia_retrieve_results = voter_ballot_items_retrieve_from_ballotpedia_for_api(
                voter_device_id, text_for_map_search)
            status += ballotpedia_retrieve_results['status']
            if ballotpedia_retrieve_results['google_civic_election_id'] \
                    and ballotpedia_retrieve_results['contests_retrieved']:
                is_from_substituted_address = False
                substituted_address_nearby = ''
                is_from_test_address = False
                polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter

                # We update the voter_address with this google_civic_election_id outside of this function

                # Save the meta information for this ballot data
                save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                    voter_id,
                    ballotpedia_retrieve_results['google_civic_election_id'],
                    ballotpedia_retrieve_results['state_code'],
                    ballotpedia_retrieve_results['election_day_text'],
                    ballotpedia_retrieve_results['election_description_text'],
                    ballotpedia_retrieve_results['text_for_map_search'],
                    substituted_address_nearby,
                    is_from_substituted_address,
                    is_from_test_address,
                    polling_location_we_vote_id_source,
                    ballotpedia_retrieve_results['ballot_location_display_name'],
                    ballotpedia_retrieve_results['ballot_returned_we_vote_id'],
                    ballotpedia_retrieve_results['ballot_location_shortcut']
                )
                status += save_results['status']
                results = {
                    'status': status,
                    'success': save_results['success'],
                    'google_civic_election_id': save_results['google_civic_election_id'],
                    'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                    'voter_ballot_saved': save_results['voter_ballot_saved'],
                }
                return results
            pass
        else:
            # 1b) Get ballot data from Google Civic for the actual VoterAddress
            use_test_election = False
            google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
                voter_device_id, text_for_map_search, use_test_election)
            status += google_retrieve_results['status']
            if google_retrieve_results['google_civic_election_id'] and google_retrieve_results['contests_retrieved']:
                is_from_substituted_address = False
                substituted_address_nearby = ''
                is_from_test_address = False
                polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter

                # We update the voter_address with this google_civic_election_id outside of this function

                # Save the meta information for this ballot data
                save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                    voter_id,
                    google_retrieve_results['google_civic_election_id'],
                    google_retrieve_results['state_code'],
                    google_retrieve_results['election_day_text'],
                    google_retrieve_results['election_description_text'],
                    google_retrieve_results['text_for_map_search'],
                    substituted_address_nearby,
                    is_from_substituted_address,
                    is_from_test_address,
                    polling_location_we_vote_id_source,
                    google_retrieve_results['ballot_location_display_name'],
                    google_retrieve_results['ballot_returned_we_vote_id'],
                    google_retrieve_results['ballot_location_shortcut']
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
            # If this ballot_returned entry is the result of searching based on an address, as opposed to
            # a specific_ballot_requested, we want to update the VoterAddress
            if not specific_ballot_requested and positive_value_exists(voter_address.text_for_map_search):
                try:
                    voter_address.ballot_location_display_name = copy_results['ballot_location_display_name']
                    voter_address.ballot_returned_we_vote_id = copy_results['ballot_returned_we_vote_id']
                    voter_address.save()
                except Exception as e:
                    pass

            # And now store the details of this ballot for this voter
            is_from_substituted_address = True
            is_from_test_address = False
            save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                voter_id,
                copy_results['google_civic_election_id'],
                copy_results['state_code'],
                copy_results['election_day_text'],
                copy_results['election_description_text'],
                text_for_map_search,
                copy_results['substituted_address_nearby'],
                is_from_substituted_address,
                is_from_test_address,
                copy_results['polling_location_we_vote_id_source'],
                copy_results['ballot_location_display_name'],
                copy_results['ballot_returned_we_vote_id'],
                copy_results['ballot_location_shortcut']
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
        # google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
        #          voter_device_id, text_for_map_search, use_test_election)
        # if google_retrieve_results['google_civic_election_id']:
        #     is_from_substituted_address = False
        #     substituted_address_nearby = ''
        #     is_from_test_address = True
        #     polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter
            # Since this is a test address, we don't want to save the google_civic_election_id (of 2000)
            # with the voter_address
        #     save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
        #         voter_id,
        #         google_retrieve_results['google_civic_election_id'],
        #         google_retrieve_results['state_code'],
        #         google_retrieve_results['election_day_text'],
        #         google_retrieve_results['election_description_text'],
        #         google_retrieve_results['text_for_map_search'],
        #         substituted_address_nearby,
        #         is_from_substituted_address,
        #         is_from_test_address,
        #         polling_location_we_vote_id_source,
        #         google_retrieve_results['ballot_location_display_name'],
        #         google_retrieve_results['ballot_returned_we_vote_id'],
        #         google_retrieve_results['ballot_location_shortcut'],
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


def voter_ballot_list_retrieve_for_api(voter_id):  # voterBallotListRetrieve
    voter_ballot_list_for_json = []
    election_ids_in_voter_ballot_saved_list = []
    final_ballot_list = []

    # Retrieve all of the upcoming elections
    ballot_returned_list_manager = BallotReturnedListManager()
    election_manager = ElectionManager()
    # results = election_manager.retrieve_upcoming_elections()
    # upcoming_election_list = results['election_list']
    results = election_manager.retrieve_listed_elections()
    election_list = results['election_list']
    elections_retrieved_count = 0
    maximum_number_of_elections_to_retrieve = 10

    # If a voter_id was passed in, return a list of elections the voter has looked at
    if positive_value_exists(voter_id):
        voter_ballot_saved_manager = VoterBallotSavedManager()
        voter_ballot_list_results = voter_ballot_saved_manager.retrieve_ballots_per_voter_id(voter_id)
        if voter_ballot_list_results['voter_ballot_list_found']:
            voter_ballot_list = voter_ballot_list_results['voter_ballot_list']
            for one_ballot_entry in voter_ballot_list:
                election_ids_in_voter_ballot_saved_list.append(one_ballot_entry.google_civic_election_id)
                ballot_returned_we_vote_id = one_ballot_entry.ballot_returned_we_vote_id \
                    if one_ballot_entry.ballot_returned_we_vote_id else ""
                one_voter_ballot_list = {
                    "google_civic_election_id":     one_ballot_entry.google_civic_election_id,
                    "election_description_text":    one_ballot_entry.election_description_text,
                    "election_day_text":            one_ballot_entry.election_day_text(),
                    "original_text_for_map_search": one_ballot_entry.original_text_for_map_search,
                    "ballot_returned_we_vote_id":   ballot_returned_we_vote_id,
                    "ballot_location_shortcut":     one_ballot_entry.ballot_location_shortcut,
                }
                voter_ballot_list_for_json.append(one_voter_ballot_list)
                elections_retrieved_count += 1

    # Now see if there are any elections that the voter has not looked at that we can add
    for election in election_list:
        if convert_to_int(election.google_civic_election_id) not in election_ids_in_voter_ballot_saved_list:
            # We used to filter out elections without ballot items. Now we want to return all of them that are marked
            #   as "listed"
            # ballot_returned_count = ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
            #     election.google_civic_election_id)
            # if positive_value_exists(ballot_returned_count):
            one_election = {
                "google_civic_election_id":         convert_to_int(election.google_civic_election_id),
                "election_description_text":        election.election_name,
                "election_day_text":                election.election_day_text,
                "original_text_for_map_search":     "",
                "ballot_returned_we_vote_id":       "",
                "ballot_location_shortcut":         "",
            }
            final_ballot_list.append(one_election)
            elections_retrieved_count += 1

    final_ballot_list = voter_ballot_list_for_json + final_ballot_list

    results = {
        'status': "VOTER_BALLOT_LIST_RETRIEVED",
        'success': True,
        'voter_ballot_list_found': True,
        'voter_ballot_list': final_ballot_list
    }
    return results


def choose_voter_ballot_saved_from_existing_ballot_returned_we_vote_id(voter_device_link, ballot_returned_we_vote_id):
    voter_id = voter_device_link.voter_id
    voter_ballot_saved_manager = VoterBallotSavedManager()
    status = ""

    voter_ballot_saved_results = voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_ballot_returned_we_vote_id(
        voter_id, ballot_returned_we_vote_id)
    status += voter_ballot_saved_results['status']
    if voter_ballot_saved_results['voter_ballot_saved_found']:
        voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
        status += "VOTER_BALLOT_SAVED_FOUND_FROM_BALLOT_RETURNED_WE_VOTE_ID "
        results = {
            'status':                   status,
            'success':                  True,
            'google_civic_election_id': voter_ballot_saved.google_civic_election_id,
            'voter_ballot_saved_found': True,
            'voter_ballot_saved':       voter_ballot_saved
        }
        return results
    else:
        # If here, we expected a VoterBallotSaved entry for this voter, but didn't find it
        pass

    status += "VOTER_BALLOT_SAVED_NOT_FOUND_FROM_BALLOT_RETURNED_WE_VOTE_ID "
    error_results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None
    }
    return error_results


def choose_voter_ballot_saved_from_existing_ballot_location_shortcut(voter_device_link, ballot_location_shortcut):
    voter_id = voter_device_link.voter_id
    voter_ballot_saved_manager = VoterBallotSavedManager()
    status = ""

    voter_ballot_saved_results = \
        voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_ballot_location_shortcut(
            voter_id, ballot_location_shortcut)
    status += voter_ballot_saved_results['status']
    if voter_ballot_saved_results['voter_ballot_saved_found']:
        voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
        status += "VOTER_BALLOT_SAVED_FOUND_FROM_BALLOT_RETURNED_LOCATION_SHORTCUT "
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

    status += "VOTER_BALLOT_SAVED_NOT_FOUND_FROM_BALLOT_RETURNED_LOCATION_SHORTCUT "
    error_results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None
    }
    return error_results


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
            # If here, we did not find a VoterBallotSaved entry for this voter, but we don't want to keep looking.
            # Instead, we want to return "voter_ballot_saved_found = False" so that we force a
            # nearby ballot get copied into voter_ballot_saved
            # Is the voter_address a match in this state? If NOT, then return
            # A) The first ballot_location
            # B) If no ballot_locations, return the first polling_location with a ballot
            status += "VOTER_BALLOT_SAVED_FOR_GOOGLE_CIVIC_ELECTION_ID_NOT_FOUND "
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': google_civic_election_id,
                'voter_ballot_saved_found': False,
                'voter_ballot_saved':       VoterBallotSaved()
            }
            return results

    if positive_value_exists(voter_device_link.google_civic_election_id):
        # If the voter_device_link was updated previous to 7 days ago, check to see if this election is in the past.
        # We do this check because we don't want a voter to return 1 year later and be returned to the old election.
        timezone = pytz.timezone("America/Los_Angeles")
        datetime_now = timezone.localize(datetime.now())
        election_choice_is_stale_duration = timedelta(days=7)
        election_choice_is_stale_date = datetime_now - election_choice_is_stale_duration
        state_code = ""
        voter_device_link_election_is_current = True
        if voter_device_link.date_last_changed and election_choice_is_stale_date:
            if voter_device_link.date_last_changed < election_choice_is_stale_date:
                # It it in the past, check to see if there is an upcoming election in this state or in the country.
                if positive_value_exists(voter_device_link.state_code):
                    state_code = voter_device_link.state_code
                elif voter_address and positive_value_exists(voter_address.normalized_state):
                    state_code = voter_address.normalized_state
                elif voter_address and positive_value_exists(voter_address.get_state_code_from_text_for_map_search()):
                    state_code = voter_address.get_state_code_from_text_for_map_search()

                election_manager = ElectionManager()
                if positive_value_exists(state_code):
                    results = election_manager.retrieve_next_election_for_state(state_code)
                else:
                    results = election_manager.retrieve_next_election_with_state_optional()

                if results['election_found']:
                    election = results['election']
                    if positive_value_exists(election.google_civic_election_id):
                        # If there IS an upcoming election, remove google_civic_election_id voter_device_link
                        # then exit this branch, but stay in this function.
                        status += "VOTER_DEVICE_LINK_ELECTION_EXPIRED "
                        try:
                            voter_device_link.google_civic_election_id = 0
                            voter_device_link.save()
                        except Exception as e:
                            status += "VOTER_DEVICE_LINK_ELECTION_COULD_NOT_BE_REMOVED "
                        # We only stop the return of data if a newer one exists
                        voter_device_link_election_is_current = False

        if voter_device_link_election_is_current:
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
        # If the voter_address was updated more than 7 days ago, check to see if this election is in the past.
        # We do this check because we don't want a voter to return 1 year later and be returned to the old election.
        timezone = pytz.timezone("America/Los_Angeles")
        datetime_now = timezone.localize(datetime.now())
        election_choice_is_stale_duration = timedelta(days=7)
        election_choice_is_stale_date = datetime_now - election_choice_is_stale_duration
        state_code = ""
        voter_address_election_is_current = True
        if voter_address.date_last_changed and election_choice_is_stale_date:
            if voter_address.date_last_changed < election_choice_is_stale_date:
                # It it in the past, check to see if there is an upcoming election in this state or in the country.
                if voter_address and positive_value_exists(voter_address.normalized_state):
                    state_code = voter_address.normalized_state
                elif voter_address and positive_value_exists(voter_address.get_state_code_from_text_for_map_search()):
                    state_code = voter_address.get_state_code_from_text_for_map_search()
                elif positive_value_exists(voter_device_link.state_code):
                    state_code = voter_device_link.state_code

                election_manager = ElectionManager()
                if positive_value_exists(state_code):
                    results = election_manager.retrieve_next_election_for_state(state_code)
                else:
                    results = election_manager.retrieve_next_election_with_state_optional()
                if results['election_found']:
                    election = results['election']
                    if positive_value_exists(election.google_civic_election_id):
                        # If there IS, save voter_address without google_civic_election_id,
                        # then exit this branch without finding google_civic_election_id, but stay in this function.
                        status += "VOTER_ADDRESS_ELECTION_EXPIRED "
                        try:
                            voter_address.google_civic_election_id = 0
                            voter_address.save()
                        except Exception as e:
                            status += "VOTER_ADDRESS_ELECTION_COULD_NOT_BE_REMOVED "
                        # We only stop the return of data if a newer one exists
                        voter_address_election_is_current = False

        if voter_address_election_is_current:
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
        status += "BALLOT_ITEM_LIST_FOUND "
        for ballot_item in ballot_item_list:
            if ballot_item.contest_office_we_vote_id:
                kind_of_ballot_item = OFFICE
                ballot_item_id = ballot_item.contest_office_id
                office_we_vote_id = ballot_item.contest_office_we_vote_id
                try:
                    candidate_list_object = CandidateCampaignListManager()
                    results = candidate_list_object.retrieve_all_candidates_for_office(
                        ballot_item_id, office_we_vote_id)
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

                if len(candidates_to_display):
                    one_ballot_item = {
                        'ballot_item_display_name':     ballot_item.ballot_item_display_name,
                        'google_civic_election_id':     ballot_item.google_civic_election_id,
                        'google_ballot_placement':      ballot_item.google_ballot_placement,
                        'local_ballot_order':           ballot_item.local_ballot_order,
                        'kind_of_ballot_item':          kind_of_ballot_item,
                        'id':                           ballot_item_id,
                        'we_vote_id':                   office_we_vote_id,
                        'candidate_list':               candidates_to_display,
                    }
                    ballot_items_to_display.append(one_ballot_item.copy())
                else:
                    status += "NO_CANDIDATES_FOR_OFFICE:" + str(office_we_vote_id) + " "
            elif ballot_item.contest_measure_we_vote_id:
                kind_of_ballot_item = MEASURE
                ballot_item_id = ballot_item.contest_measure_id
                measure_we_vote_id = ballot_item.contest_measure_we_vote_id
                one_ballot_item = {
                    'ballot_item_display_name':     ballot_item.ballot_item_display_name,
                    'google_civic_election_id':     ballot_item.google_civic_election_id,
                    'google_ballot_placement':      ballot_item.google_ballot_placement,
                    'id':                           ballot_item_id,
                    'kind_of_ballot_item':          kind_of_ballot_item,
                    'local_ballot_order':           ballot_item.local_ballot_order,
                    'measure_subtitle':             ballot_item.measure_subtitle,
                    'measure_text':                 ballot_item.measure_text,
                    'measure_url':                  ballot_item.measure_url,
                    'no_vote_description':          ballot_item.no_vote_description,
                    'we_vote_id':                   measure_we_vote_id,
                    'yes_vote_description':         ballot_item.yes_vote_description,
                }
                ballot_items_to_display.append(one_ballot_item.copy())

        results = {
            'status': status,
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


def ballot_item_options_retrieve_for_api(google_civic_election_id, search_string, state_code=''):
    """
    This function returns a normalized list of candidates and measures so we can pre-populate form fields.
    Not specific to one voter.
    :param google_civic_election_id:
    :param search_string:
    :param state_code:
    :return:
    """

    status = ""
    try:
        candidate_list_object = CandidateCampaignListManager()
        results = candidate_list_object.search_candidates_for_upcoming_election(
            google_civic_election_id, search_string, state_code)
        candidate_success = results['success']
        status += results['status']
        candidate_list = results['candidate_list_json']
    except Exception as e:
        status += 'FAILED ballot_item_options_retrieve_for_api, candidate_list. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        candidate_list = []
        candidate_success = False

    measure_success = False
    # try:
    #     measure_list_object = ContestMeasureList()
    #     results = measure_list_object.retrieve_all_measures_for_upcoming_election(
    # google_civic_election_id, state_code)
    #     measure_success = results['success']
    #     status += ' ' + results['status']
    #     measure_list = results['measure_list_light']
    # except Exception as e:
    #     status += 'FAILED ballot_item_options_retrieve_for_api, measure_list. ' \
    #              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
    #     handle_exception(e, logger=logger, exception_message=status)
    #     measure_list = []
    #     measure_success = False

    ballot_items_to_display = []
    if candidate_success and len(candidate_list):
        for candidate in candidate_list:
            ballot_items_to_display.append(candidate.copy())

    # if measure_success and len(measure_list):
    #     for measure in measure_list:
    #         ballot_items_to_display.append(measure.copy())

    json_data = {
        'status':                   status,
        'success':                  candidate_success or measure_success,
        'search_string':            search_string,
        'ballot_item_list':         ballot_items_to_display,
        'google_civic_election_id': google_civic_election_id,
    }
    results = {
        'status':                   status,
        'success':                  candidate_success or measure_success,
        'search_string':            search_string,
        'google_civic_election_id': google_civic_election_id,
        'json_data':                json_data,
    }
    return results
