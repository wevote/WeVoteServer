# ballot/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItemListManager, BallotItemManager, BallotReturnedListManager, BallotReturnedManager, \
    CANDIDATE, find_best_previously_stored_ballot_returned, OFFICE, MEASURE, \
    VoterBallotSaved, VoterBallotSavedManager
from candidate.models import CandidateListManager
from config.base import get_environment_variable
from datetime import datetime, timedelta
import datetime as the_other_datetime
from election.controllers import retrieve_upcoming_election_id_list
from election.models import ElectionManager
from exception.models import handle_exception
from import_export_google_civic.controllers import \
    refresh_voter_ballot_items_from_google_civic_from_voter_ballot_saved, \
    voter_ballot_items_retrieve_from_google_civic_for_api
from measure.models import ContestMeasureListManager, ContestMeasureManager
from office.models import ContestOfficeManager, ContestOfficeListManager
from polling_location.models import PollingLocationManager
import pytz
from voter.models import BALLOT_ADDRESS, VoterAddress, VoterAddressManager, VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_code_from_address_string, positive_value_exists, \
    process_request_from_master, strip_html_tags
from wevote_functions.functions_date import generate_localized_datetime_from_obj
from geopy.geocoders import get_geocoder_for_service

logger = wevote_functions.admin.get_logger(__name__)

GEOCODE_TIMEOUT = 10
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
            # results = filter_ballot_items_structured_json_for_local_duplicates(structured_json)
            # filtered_structured_json = results['structured_json']
            # duplicates_removed = results['duplicates_removed']
            # import_results = ballot_items_import_from_structured_json(filtered_structured_json)

            import_results = ballot_items_import_from_structured_json(structured_json)
            import_results['duplicates_removed'] = 0
    except Exception as e:
        import_results = {
            'success': False,
            'status': "FAILED_TO_GET_JSON_FROM_MASTER_SERVER " + str(e) + ' ',
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
        request, "Requesting Ballot Returned entries (saved ballots, specific to one location) "
                 "from WeVote Master servers",
        BALLOT_RETURNED_SYNC_URL,
        {
            "key": WE_VOTE_API_KEY,  # This comes from an environment variable
            "google_civic_election_id": str(google_civic_election_id),
            "state_code": str(state_code),
        }
    )

    print("... the master server returned " + str(len(structured_json)) + " BallotReturned entries for election " +
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
        'status': "BALLOT_ITEMS_IMPORT_PROCESS_COMPLETE",
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

            # Here we check for a local polling_location. We used to require the map point be found,
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
        location = google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
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
                status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_DELETE_FROM_BALLOT_ITEM_ENTRY " + str(e) + " "
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
                status += "MOVE_TO_ANOTHER_CONTEST_OFFICE-UNABLE_TO_SAVE_NEW_ballot_item " + str(e) + ' '
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


def figure_out_google_civic_election_id_voter_is_watching_by_voter_we_vote_id(voter_we_vote_id):
    voter_id = 0
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id)
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
    return figure_out_google_civic_election_id_voter_is_watching_by_voter_id(voter_id)


def figure_out_google_civic_election_id_voter_is_watching_by_voter_id(voter_id):
    status = 'FIGURE_OUT_BY_VOTER_ID '

    # We zero out this value  since we will never have this coming in for this function
    google_civic_election_id = 0
    voter_device_id = ""

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id, voter_id=voter_id)
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
    ballots_refreshed = 0

    # ballot_saved_manager = VoterBallotSavedManager()
    # # When voters provide partial addresses, we copy their ballots from nearby map points
    # # We want to find all voter_ballot_saved entries that came from polling_location_we_vote_id_source
    # polling_location_we_vote_id_source = ballot_returned_from_polling_location.polling_location_we_vote_id
    #
    # if not positive_value_exists(polling_location_we_vote_id_source) \
    #         or not positive_value_exists(google_civic_election_id):
    #     status += "REFRESH_VOTER_BALLOTS_FROM_POLLING_LOCATION-MISSING_REQUIRED_VARIABLE(S) "
    #     success = False
    #     results = {
    #         'status': status,
    #         'success': success,
    #     }
    #     return results
    #
    # retrieve_results = ballot_saved_manager.retrieve_voter_ballot_saved_list_for_election(
    #     google_civic_election_id, polling_location_we_vote_id_source)
    # if retrieve_results['voter_ballot_saved_list_found']:
    #     voter_ballot_saved_list = retrieve_results['voter_ballot_saved_list']
    #     for voter_ballot_saved in voter_ballot_saved_list:
    #         # Neither BallotReturned nor VoterBallotSaved change when we get refreshed data from Google Civic
    #         if positive_value_exists(voter_ballot_saved.voter_id) \
    #                 and positive_value_exists(voter_ballot_saved.ballot_returned_we_vote_id):
    #             refresh_results = refresh_ballot_items_for_voter_copied_from_one_polling_location(
    #                 voter_ballot_saved.voter_id, ballot_returned_from_polling_location)
    #
    #             if refresh_results['ballot_returned_copied']:
    #                 ballots_refreshed += 1
    #             else:
    #                 status += refresh_results['status']

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
    ballot_returned_manager = BallotReturnedManager()
    ballot_saved_manager = VoterBallotSavedManager()

    # When we set up voter_ballot_saved entries by copying data from a map point, if something
    # happens to the ballot_returned entry, we need to repair it
    retrieve_results = ballot_saved_manager.retrieve_voter_ballot_saved_list_for_election(
        google_civic_election_id, find_all_entries_for_election=True)
    voter_ballot_saved_entries_deleted_count = 0
    if retrieve_results['voter_ballot_saved_list_found']:
        voter_ballot_saved_list = retrieve_results['voter_ballot_saved_list']
        for voter_ballot_saved in voter_ballot_saved_list:
            # Make sure a BallotReturned entry exists for entries with voter_ballot_saved.ballot_returned_we_vote_id
            if positive_value_exists(voter_ballot_saved.ballot_returned_we_vote_id):
                ballot_returned_results = \
                    ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(
                        voter_ballot_saved.ballot_returned_we_vote_id)
                if not positive_value_exists(ballot_returned_results['ballot_returned_found']):
                    # Delete the voter_ballot_saved entry
                    voter_ballot_saved.delete()
                    voter_ballot_saved_entries_deleted_count += 1

    if positive_value_exists(voter_ballot_saved_entries_deleted_count):
        status += "VOTER_BALLOT_SAVED_ENTRIES_DELETED:" + str(voter_ballot_saved_entries_deleted_count) + " "
    else:
        status += "ALL_VOTER_BALLOT_SAVED_ENTRIES_HAVE_ACCURATE_BALLOT_RETURNED_WE_VOTE_ID "

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
    success = True
    number_of_ballot_items_updated = 0
    status = ""

    if not positive_value_exists(google_civic_election_id):
        status += "REPAIR_BALLOT_ITEMS_FOR_ELECTION-MISSING_ELECTION_ID "
        success = False
        results = {
            'status': status,
            'success': success,
        }
        return results

    ballot_item_manager = BallotItemManager()
    ballot_item_list_manager = BallotItemListManager()
    candidate_list = CandidateListManager()
    office_list_manager = ContestOfficeListManager()
    measure_list_manager = ContestMeasureListManager()
    results = office_list_manager.retrieve_offices(google_civic_election_id=google_civic_election_id)
    offices_in_this_election_list = results['office_list_light']
    ballot_items_deleted_count = 0
    # Start by removing ballot_items for offices that don't have any candidates
    for one_office in offices_in_this_election_list:
        results = candidate_list.retrieve_candidate_count_for_office(0, one_office['office_we_vote_id'])
        if not positive_value_exists(results['candidate_count']):
            # If no candidates found for this office, delete the ballot item.
            ballot_item_results = ballot_item_list_manager.delete_all_ballot_items_for_contest_office(
                0, one_office['office_we_vote_id'])
            ballot_items_deleted_count += ballot_item_results['ballot_items_deleted_count']

    if positive_value_exists(ballot_items_deleted_count):
        status += "BALLOT_ITEMS_DELETED:" + str(ballot_items_deleted_count) + " "

    results = office_list_manager.retrieve_offices(
        google_civic_election_id=google_civic_election_id,
        return_list_of_objects=True,
        read_only=True,
    )
    offices_in_this_election_list = results['office_list_objects']
    for contest_office in offices_in_this_election_list:
        results = ballot_item_manager.refresh_all_ballot_item_office_entries(contest_office=contest_office)
        number_of_ballot_items_updated += results['number_of_ballot_items_updated']

    results = measure_list_manager.retrieve_measures(
        google_civic_election_id=google_civic_election_id,
        read_only=True,
    )
    measures_in_this_election_list = results['measure_list_objects']
    for contest_measure in measures_in_this_election_list:
        results = ballot_item_manager.refresh_all_ballot_item_measure_entries(contest_measure=contest_measure)
        number_of_ballot_items_updated += results['number_of_ballot_items_updated']

    # Separately from this function, we need to go through the ballot_returned entries that we already retrieved
    # data for, and make sure we have all the needed ballot item data
    # results = refresh_voter_ballots_copied_from_any_polling_location(google_civic_election_id)
    # voter_ballots_copied_count = results['voter_ballots_copied']
    # voter_ballots_copied_count = 0

    # Now check for VoterBallotSaved entries for voter ballots that were not copied from map points
    #  so we can refresh the data
    # This tries to reach out to Google Civic
    retrieve_from_google_civic = False
    ballots_refreshed = 0
    refresh_ballot_status = ''
    if retrieve_from_google_civic:
        refresh_ballot_results = refresh_voter_ballots_not_copied_from_polling_location(
            google_civic_election_id, refresh_from_google)
        ballots_refreshed = refresh_ballot_results['ballots_refreshed']
        refresh_ballot_status = refresh_ballot_results['status']

    status = "REPAIR_BALLOT_ITEMS, total count updated: {number_of_ballot_items_updated}, " \
             "ballot_items_deleted_count: {ballot_items_deleted_count}, " \
             ", REFRESH: " \
             "unique_ballots_refreshed: {ballots_refreshed} refresh_ballot_status: {refresh_ballot_status}" \
             "".format(number_of_ballot_items_updated=number_of_ballot_items_updated,
                       ballot_items_deleted_count=ballot_items_deleted_count,
                       ballots_refreshed=ballots_refreshed,
                       refresh_ballot_status=refresh_ballot_status)
    results = {
        'status': status,
        'success': success,
    }
    return results


def all_ballot_items_retrieve_for_api(google_civic_election_id, state_code=''):  # allBallotItemsRetrieve
    """

    :param google_civic_election_id:
    :param state_code:
    :return:
    """
    status = ''
    success = True
    ballot_found = False

    if not positive_value_exists(google_civic_election_id):
        status += "ALL_BALLOT_ITEMS_RETRIEVE-GOOGLE_CIVIC_ELECTION_ID_MISSING "
        error_json_data = {
            'status':                   status,
            'success':                  False,
            'ballot_found':             False,
            'ballot_item_list':         [],
            'google_civic_election_id': google_civic_election_id,
            'is_from_test_ballot':      False,
            'election_name':            '',
            'election_day_text':        '',
        }
        return error_json_data

    # Get and return the ballot_item_list
    ballot_item_list = []
    results = all_ballot_items_retrieve_for_one_election_for_api(google_civic_election_id, state_code)
    if not positive_value_exists(results['success']):
        status += "ALL_BALLOT_ITEMS_RETRIEVE-NO_SUCCESS "
        success = False
    status += results['status']

    election_day_text = ""
    election_description_text = ""
    if positive_value_exists(results['success']):
        ballot_item_list = results['ballot_item_list']
        ballot_found = len(ballot_item_list)

        # Now retrieve information about election
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_election(google_civic_election_id)
        if election_results['election_found']:
            election = election_results['election']
            election_description_text = election.election_name
            if positive_value_exists(election.election_day_text):
                election_day_text = election.election_day_text

    json_data = {
        'status':                       status,
        'success':                      success,
        'ballot_found':                 ballot_found,
        'ballot_item_list':             ballot_item_list,
        'election_name':                election_description_text,
        'election_day_text':            election_day_text,
        'google_civic_election_id':     google_civic_election_id,
        'state_code':                   state_code,
    }
    return json_data


def voter_ballot_items_retrieve_for_api(  # voterBallotItemsRetrieve
        voter_device_id='',
        google_civic_election_id=0,
        ballot_returned_we_vote_id='',
        ballot_location_shortcut='',
        incoming_status=''):
    status = incoming_status

    next_national_election_day_text = '2024/11/05'

    specific_ballot_requested = positive_value_exists(ballot_returned_we_vote_id) or \
        positive_value_exists(ballot_location_shortcut)

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        status += "VALID_VOTER_DEVICE_ID_MISSING "
        # If the retrieve had no errors, a voter_device_id was passed in, but voter_device_link_found is False,
        # tell the WebApp the voter_device_id might need to be replaced.
        voter_device_id_not_valid = \
            positive_value_exists(voter_device_id) and positive_value_exists(voter_device_link_results['success'])
        error_json_data = {
            'status':                               status,
            'success':                              False,
            'ballot_caveat':                        '',
            'ballot_found':                         False,
            'ballot_item_list':                     [],
            'ballot_location_display_name':         '',
            'ballot_location_shortcut':             ballot_location_shortcut,
            'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
            'google_civic_election_id':             google_civic_election_id,
            'is_from_substituted_address':          False,
            'is_from_test_ballot':                  False,
            'next_national_election_day_text':      '',
            'original_text_city':                   '',
            'original_text_state':                  '',
            'original_text_zip':                    '',
            'polling_location_we_vote_id_source':   '',
            'substituted_address_nearby':           '',
            'substituted_address_city':             '',
            'substituted_address_state':            '',
            'substituted_address_zip':              '',
            'text_for_map_search':                  '',
            'voter_device_id':                      voter_device_id,
            'voter_device_id_not_valid':            voter_device_id_not_valid,
        }
        return error_json_data

    voter_device_link = voter_device_link_results['voter_device_link']
    voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        status += " " + "VALID_VOTER_ID_MISSING"
        error_json_data = {
            'status':                               status,
            'success':                              False,
            'ballot_caveat':                        '',
            'ballot_found':                         False,
            'ballot_item_list':                     [],
            'ballot_location_display_name':         '',
            'ballot_location_shortcut':             ballot_location_shortcut,
            'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
            'google_civic_election_id':             google_civic_election_id,
            'is_from_substituted_address':          False,
            'is_from_test_ballot':                  False,
            'next_national_election_day_text':      '',
            'original_text_city':                   '',
            'original_text_state':                  '',
            'original_text_zip':                    '',
            'polling_location_we_vote_id_source':   '',
            'substituted_address_nearby':           '',
            'substituted_address_city':             '',
            'substituted_address_state':            '',
            'substituted_address_zip':              '',
            'text_for_map_search':                  '',
            'voter_device_id':                      voter_device_id,
        }
        return error_json_data

    voter_address_manager = VoterAddressManager()
    voter_address_id = 0
    address_type = BALLOT_ADDRESS
    voter_address_results = voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)
    status += " " + voter_address_results['status']
    # Note that this might be an empty VoterAddress object
    voter_address = voter_address_results['voter_address']
    text_for_map_search = ''
    if voter_address and hasattr(voter_address, 'text_for_map_search'):
        text_for_map_search = voter_address.text_for_map_search
    if positive_value_exists(voter_address_results['voter_address_has_value']):
        ballot_retrieval_based_on_voter_address = True
    else:
        ballot_retrieval_based_on_voter_address = False

    offices_held_for_location_id = ''
    offices_held_text_for_map_search = ''
    polling_location_we_vote_id_source = ''
    substituted_address_nearby = ''
    substituted_address_city = ''
    substituted_address_state = ''
    substituted_address_zip = ''
    use_office_held_ballot = False
    use_voter_ballot_saved = False
    results = choose_election_and_prepare_ballot_data(
        voter_device_link,
        google_civic_election_id,
        voter_address,
        ballot_returned_we_vote_id,
        ballot_location_shortcut)
    status += " " + results['status']
    voter_ballot_saved_found = results['voter_ballot_saved_found']
    if results['use_office_held_ballot']:
        offices_held_for_location_id = results['offices_held_for_location_id']
        if voter_address and hasattr(voter_address, 'text_for_map_search'):
            offices_held_text_for_map_search = voter_address.text_for_map_search
        if 'substituted_address_nearby' in results:
            substituted_address_nearby = results['substituted_address_nearby']
        if 'substituted_address_city' in results:
            substituted_address_city = results['substituted_address_city']
        if 'substituted_address_state' in results:
            substituted_address_state = results['substituted_address_state']
        if 'substituted_address_zip' in results:
            substituted_address_zip = results['substituted_address_zip']
        use_office_held_ballot = True
    elif voter_ballot_saved_found:
        use_voter_ballot_saved = True
        voter_ballot_saved = results['voter_ballot_saved']
        ballot_returned_we_vote_id = voter_ballot_saved.ballot_returned_we_vote_id
    elif not voter_ballot_saved_found:
        if positive_value_exists(ballot_returned_we_vote_id):
            ballot_caveat = "We could not find the ballot with the id '{ballot_returned_we_vote_id}'.".format(
                ballot_returned_we_vote_id=ballot_returned_we_vote_id)
        elif positive_value_exists(ballot_location_shortcut):
            ballot_caveat = "We could not find the ballot '{ballot_location_shortcut}'.".format(
                ballot_location_shortcut=ballot_location_shortcut)
        elif positive_value_exists(text_for_map_search):
            ballot_caveat = "We could not find a ballot near '{text_for_map_search}'.".format(
                text_for_map_search=text_for_map_search)
        else:
            ballot_caveat = "Please save your address so we can find your ballot."

        error_json_data = {
            'status':                               status,
            'success':                              True,
            'ballot_caveat':                        ballot_caveat,
            'ballot_found':                         False,
            'ballot_item_list':                     [],
            'ballot_location_display_name':         '',
            'ballot_location_shortcut':             ballot_location_shortcut,
            'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
            'google_civic_election_id':             google_civic_election_id,
            'is_from_substituted_address':          False,
            'is_from_test_ballot':                  False,
            'next_national_election_day_text':      next_national_election_day_text,
            'original_text_city':                   '',
            'original_text_state':                  '',
            'original_text_zip':                    '',
            'polling_location_we_vote_id_source':   polling_location_we_vote_id_source,
            'substituted_address_nearby':           substituted_address_nearby,
            'substituted_address_city':             substituted_address_city,
            'substituted_address_state':            substituted_address_state,
            'substituted_address_zip':              substituted_address_zip,
            'text_for_map_search':                  text_for_map_search,
            'voter_device_id':                      voter_device_id,
        }
        return error_json_data

    google_civic_election_id = results['google_civic_election_id']

    # Update voter_device_link
    if voter_device_link.google_civic_election_id != google_civic_election_id:
        voter_device_link_manager.update_voter_device_link_with_election_id(voter_device_link, google_civic_election_id)

    # Update voter_address to include matching google_civic_election_id and voter_ballot_saved entry
    if positive_value_exists(google_civic_election_id):
        # 2017-10-25 DALE It turns out we don't want to update the address with just the election_id unless
        #  the election was calculated from an address. We want to keep google_civic_election_id tied
        #  to the voter's address
        if ballot_retrieval_based_on_voter_address:
            if google_civic_election_id != voter_address.google_civic_election_id:
                voter_address.google_civic_election_id = google_civic_election_id
                voter_address_manager.update_existing_voter_address_object(voter_address)

    election_manager = ElectionManager()
    if use_voter_ballot_saved and positive_value_exists(google_civic_election_id):
        # Get and return the ballot_item_list
        results = voter_ballot_items_retrieve_for_one_election_for_api(
            voter_device_id,
            voter_id=voter_id,
            google_civic_election_id=google_civic_election_id,
            ballot_returned_we_vote_id=ballot_returned_we_vote_id)

        election_day_text = voter_ballot_saved.election_day_text()
        if not results['success']:
            status += "FAILED_VOTER_BALLOT_ITEMS_RETRIEVE: "
            status += results['status']
        elif len(results['ballot_item_list']) == 0:
            status += results['status']
            try:
                # Heal the data
                voter_ballot_saved.delete()
                voter_ballot_saved_found = False
                status += "DELETED_VOTER_BALLOT_SAVED_WITH_EMPTY_BALLOT_ITEM_LIST "
            except Exception as e:
                status += "UNABLE_TO_DELETE_VOTER_BALLOT_SAVED " + str(e) + " "
        elif not positive_value_exists(voter_ballot_saved.election_description_text) \
                or not positive_value_exists(election_day_text):
            try:
                voter_ballot_saved_changed = False
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    if not positive_value_exists(voter_ballot_saved.election_description_text):
                        voter_ballot_saved.election_description_text = election.election_name
                        voter_ballot_saved_changed = True
                    if not positive_value_exists(election_day_text):
                        if positive_value_exists(election.election_day_text):
                            voter_ballot_saved.election_date = \
                                datetime.strptime(election.election_day_text, "%Y-%m-%d").date()
                            voter_ballot_saved_changed = True
                if voter_address.text_for_map_search != voter_ballot_saved.original_text_for_map_search and \
                        not specific_ballot_requested:
                    # We don't want to change the voter_ballot_saved.original_text_for_map_search to be
                    #  the voter's address if we copied this ballot based on ballot_returned_we_vote_id
                    #  or ballot_location_shortcut
                    voter_ballot_saved.original_text_for_map_search = voter_address.text_for_map_search
                    voter_ballot_saved_changed = True
                if voter_ballot_saved_changed:
                    voter_ballot_saved.save()
            except Exception as e:
                status += "Failed to update election_name or original_text_for_map_search " + str(e) + " "
        elif voter_ballot_saved.original_text_for_map_search != voter_address.text_for_map_search and \
                not specific_ballot_requested:
            # We don't want to change the voter_ballot_saved.original_text_for_map_search to be the voter's address
            #  if we copied this ballot based on ballot_returned_we_vote_id or ballot_location_shortcut
            try:
                voter_ballot_saved.original_text_for_map_search = voter_address.text_for_map_search
                voter_ballot_saved.save()
            except Exception as e:
                status += "Failed to update original_text_for_map_search " + str(e) + " "

        status += " " + results['status']
        if positive_value_exists(voter_ballot_saved_found):
            json_data = {
                'status':                               status,
                'success':                              True,
                'ballot_caveat':                        voter_ballot_saved.ballot_caveat(),
                'ballot_found':                         True,
                'ballot_item_list':                     results['ballot_item_list'],
                'ballot_location_display_name':         voter_ballot_saved.ballot_location_display_name,
                'ballot_location_shortcut':             voter_ballot_saved.ballot_location_shortcut,
                'ballot_returned_we_vote_id':           voter_ballot_saved.ballot_returned_we_vote_id,
                'election_name':                        voter_ballot_saved.election_description_text,
                'election_day_text':                    voter_ballot_saved.election_day_text(),
                'google_civic_election_id':             google_civic_election_id,
                'is_from_substituted_address':          voter_ballot_saved.is_from_substituted_address,
                'is_from_test_ballot':                  voter_ballot_saved.is_from_test_ballot,
                'next_national_election_day_text':      next_national_election_day_text,
                'original_text_city':                   voter_ballot_saved.original_text_city,
                'original_text_state':                  voter_ballot_saved.original_text_state,
                'original_text_zip':                    voter_ballot_saved.original_text_zip,
                'polling_location_we_vote_id_source':   voter_ballot_saved.polling_location_we_vote_id_source,
                'substituted_address_nearby':           voter_ballot_saved.substituted_address_nearby,
                'substituted_address_city':             voter_ballot_saved.substituted_address_city,
                'substituted_address_state':            voter_ballot_saved.substituted_address_state,
                'substituted_address_zip':              voter_ballot_saved.substituted_address_zip,
                'text_for_map_search':                  voter_ballot_saved.original_text_for_map_search,
                'voter_device_id':                      voter_device_id,
            }
            return json_data
    elif use_office_held_ballot:
        from ballot.controllers_ballot_from_offices_held import \
            voter_ballot_items_retrieve_for_one_election_by_offices_held_for_api
        results = voter_ballot_items_retrieve_for_one_election_by_offices_held_for_api(
            # voter_device_id,
            # voter_id=voter_id,
            google_civic_election_id=google_civic_election_id,
            offices_held_for_location_id=offices_held_for_location_id)
        if 'polling_location_we_vote_id' in results and \
                positive_value_exists(results['polling_location_we_vote_id']):
            polling_location_we_vote_id_source = results['polling_location_we_vote_id']
        ballot_item_list_found = results['ballot_item_list_found']
        if positive_value_exists(ballot_item_list_found):
            election_day_text = ''
            election_description_text = ''
            if positive_value_exists(results['google_civic_election_id']):
                google_civic_election_id = results['google_civic_election_id']
            if positive_value_exists(google_civic_election_id):
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    election_description_text = election.election_name
                    election_day_text = election.election_day_text

            json_data = {
                'status':                               status,
                'success':                              True,
                'ballot_caveat':                        '',  # results['ballot_caveat'],
                'ballot_found':                         True,
                'ballot_item_list':                     results['ballot_item_list'],
                'ballot_location_display_name':         '',  # voter_ballot_saved.ballot_location_display_name,
                'ballot_location_shortcut':             '',  # voter_ballot_saved.ballot_location_shortcut,
                'ballot_returned_we_vote_id':           '',  #
                'election_name':                        election_description_text,
                'election_day_text':                    election_day_text,
                'google_civic_election_id':             google_civic_election_id,
                'is_from_substituted_address':          True,
                'is_from_test_ballot':                  '',  # voter_ballot_saved.is_from_test_ballot,
                'next_national_election_day_text':      next_national_election_day_text,
                'original_text_city':                   '',  # voter_ballot_saved.original_text_city,
                'original_text_state':                  '',  # voter_ballot_saved.original_text_state,
                'original_text_zip':                    '',  # voter_ballot_saved.original_text_zip,
                'polling_location_we_vote_id_source':   polling_location_we_vote_id_source,
                'substituted_address_nearby':           substituted_address_nearby,
                'substituted_address_city':             substituted_address_city,
                'substituted_address_state':            substituted_address_state,
                'substituted_address_zip':              substituted_address_zip,
                'text_for_map_search':                  offices_held_text_for_map_search,
                'voter_device_id':                      voter_device_id,
            }
            return json_data

    status += " " + "NO_VOTER_BALLOT_SAVED_FOUND "
    json_data = {
        'status':                               status,
        'success':                              True,
        'ballot_caveat':                        '',
        'ballot_found':                         False,
        'ballot_item_list':                     [],
        'ballot_location_display_name':         '',
        'ballot_location_shortcut':             ballot_location_shortcut,
        'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
        'google_civic_election_id':             0,
        'is_from_substituted_address':          False,
        'is_from_test_ballot':                  False,
        'next_national_election_day_text':      next_national_election_day_text,
        'original_text_city':                   '',
        'original_text_state':                  '',
        'original_text_zip':                    '',
        'polling_location_we_vote_id_source':   polling_location_we_vote_id_source,
        'substituted_address_nearby':           substituted_address_nearby,
        'substituted_address_city':             substituted_address_city,
        'substituted_address_state':            substituted_address_state,
        'substituted_address_zip':              substituted_address_zip,
        'text_for_map_search':                  '',
        'voter_device_id':                      voter_device_id,
    }
    return json_data


def choose_election_and_prepare_ballot_data(
        voter_device_link,
        google_civic_election_id,
        voter_address,
        ballot_returned_we_vote_id='',
        ballot_location_shortcut=''):
    offices_held_for_location_id = ''
    voter_id = voter_device_link.voter_id
    status = ""

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        results = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'offices_held_for_location_id': offices_held_for_location_id,
            'use_office_held_ballot':   False,
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
    # 1) Find ballot data from a specific location (using either ballot_returned_we_vote_id or ballot_location_shortcut)
    # 2) Get ballot data from the current default ballot source: Vote USA, Ballotpedia or Google Civic for VoterAddress
    # 3) Find ballot data from a nearby address, previously retrieved and cached within We Vote, or
    #    generated within We Vote (google_civic_election_id >= 1000000
    # 4) Get test ballot data from Google Civic
    results = generate_ballot_data(
        voter_device_link=voter_device_link,
        google_civic_election_id=google_civic_election_id,
        voter_address=voter_address,
        ballot_returned_we_vote_id=ballot_returned_we_vote_id,
        ballot_location_shortcut=ballot_location_shortcut)
    status += results['status']
    if results['voter_ballot_saved_found']:
        # Return voter_ballot_saved
        return results

    from ballot.controllers_ballot_from_offices_held import generate_ballot_data_from_offices_held
    results = generate_ballot_data_from_offices_held(
        voter_device_link=voter_device_link,
        google_civic_election_id=google_civic_election_id,
        voter_address=voter_address)
    status += results['status']
    if results['use_office_held_ballot'] and positive_value_exists(results['offices_held_for_location_id']):
        results['status'] += 'USING_OFFICES_HELD_BALLOT '
        return results

    status += "BALLOT_NOT_FOUND_OR_GENERATED "
    results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': google_civic_election_id,
        'offices_held_for_location_id': offices_held_for_location_id,
        'use_office_held_ballot':   False,
        'voter_ballot_saved':       None,
        'voter_ballot_saved_found': False,
    }
    return results


def generate_ballot_data(
        voter_device_link=None,
        google_civic_election_id=0,
        voter_address=None,
        ballot_returned_we_vote_id='',
        ballot_location_shortcut=''):
    status = ''
    try:
        voter_device_id = voter_device_link.voter_device_id
        voter_id = voter_device_link.voter_id
    except Exception as e:
        status += "PROBLEM_WITH_VOTER_DEVICE_LINK_OBJECT: " + str(e) + " "
        voter_device_id = ''
        voter_id = 0

    voter_address_exists = \
        voter_address and hasattr(voter_address, 'voter_id') and positive_value_exists(voter_address.voter_id)
    voter_ballot_saved_manager = VoterBallotSavedManager()
    status = ""
    specific_ballot_requested = positive_value_exists(ballot_returned_we_vote_id) or \
        positive_value_exists(ballot_location_shortcut)

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        results = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': 0,
            'state_code':               '',
            'use_office_held_ballot':   False,
            'voter_ballot_saved_found': False,
            'voter_ballot_saved':       VoterBallotSaved()
        }
        return results

    election_manager = ElectionManager()
    if specific_ballot_requested:
        text_for_map_search = ''
        google_civic_election_id = 0
        ballot_returned_results = find_best_previously_stored_ballot_returned(
            voter_id, text_for_map_search, google_civic_election_id,
            ballot_returned_we_vote_id, ballot_location_shortcut)
        status += ballot_returned_results['status']
        if ballot_returned_results['ballot_returned_found']:
            is_from_substituted_address = True
            is_from_test_address = False
            election_day_text = ballot_returned_results['election_day_text']
            election_description_text = ballot_returned_results['election_description_text']
            if not positive_value_exists(election_day_text) or not positive_value_exists(election_description_text):
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    election_day_text = election.election_day_text
                    election_description_text = election.election_name
            save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                voter_id,
                ballot_returned_results['google_civic_election_id'],
                ballot_returned_results['state_code'],
                election_day_text,
                election_description_text,
                text_for_map_search,
                ballot_returned_results['substituted_address_nearby'],
                is_from_substituted_address,
                is_from_test_address,
                ballot_returned_results['polling_location_we_vote_id_source'],
                ballot_returned_results['ballot_location_display_name'],
                ballot_returned_results['ballot_returned_we_vote_id'],
                ballot_returned_results['ballot_location_shortcut'],
                substituted_address_city=ballot_returned_results['substituted_address_city'],
                substituted_address_state=ballot_returned_results['substituted_address_state'],
                substituted_address_zip=ballot_returned_results['substituted_address_zip'],
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
        text_for_map_search = voter_address.text_for_map_search if voter_address_exists else ''

        if positive_value_exists(google_civic_election_id):
            # If a specific google_civic_election_id came in, we need to return a ballot in that particular election,
            # even if it isn't an election the voter has seen before.
            text_for_map_search_for_google_civic_retrieve = ""
            # Is the voter's address in a particular state?
            if voter_address_exists:
                state_code_from_text_for_map_search = voter_address.get_state_code_from_text_for_map_search()
            else:
                state_code_from_text_for_map_search = ''
            if positive_value_exists(state_code_from_text_for_map_search):
                # If the voter address is for another state, then remove
                election_results = election_manager.retrieve_election(google_civic_election_id)
                if election_results['election_found']:
                    election = election_results['election']
                    # If the voter's address is in a state supported by this election, pass in the text_for_map_search
                    try:
                        election_state_code_lower = election.state_code.lower()
                    except Exception as e:
                        election_state_code_lower = ''
                    try:
                        state_code_from_text_for_map_search_lower = state_code_from_text_for_map_search.lower()
                    except Exception as e:
                        state_code_from_text_for_map_search_lower = ''
                    if election_state_code_lower == "na" or election_state_code_lower == "":
                        # If a National election, then we want the address passed in
                        text_for_map_search_for_google_civic_retrieve = text_for_map_search
                    elif election_state_code_lower == state_code_from_text_for_map_search_lower:
                        text_for_map_search_for_google_civic_retrieve = text_for_map_search
                    else:
                        text_for_map_search_for_google_civic_retrieve = ""
            else:
                # Voter address state_code not found, so we don't use the text_for_map_search value
                text_for_map_search_for_google_civic_retrieve = ""

            # 0) Find ballot data for an election that is in a different state than the voter
            ballot_returned_results = find_best_previously_stored_ballot_returned(
                voter_id, text_for_map_search_for_google_civic_retrieve, google_civic_election_id)
            status += ballot_returned_results['status']
            if ballot_returned_results['ballot_returned_found']:
                # If this ballot_returned entry is the result of searching based on an address, as opposed to
                # a specific_ballot_requested, we want to update the VoterAddress
                if voter_address_exists and not specific_ballot_requested and positive_value_exists(text_for_map_search):
                    try:
                        voter_address.ballot_location_display_name = \
                            ballot_returned_results['ballot_location_display_name']
                        voter_address.ballot_returned_we_vote_id = ballot_returned_results['ballot_returned_we_vote_id']
                        voter_address.save()
                    except Exception as e:
                        pass

                # And now store the details of this ballot for this voter
                is_from_substituted_address = True
                is_from_test_address = False
                save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                    voter_id,
                    ballot_returned_results['google_civic_election_id'],
                    ballot_returned_results['state_code'],
                    ballot_returned_results['election_day_text'],
                    ballot_returned_results['election_description_text'],
                    text_for_map_search,
                    ballot_returned_results['substituted_address_nearby'],
                    is_from_substituted_address,
                    is_from_test_address,
                    ballot_returned_results['polling_location_we_vote_id_source'],
                    ballot_returned_results['ballot_location_display_name'],
                    ballot_returned_results['ballot_returned_we_vote_id'],
                    ballot_returned_results['ballot_location_shortcut'],
                    substituted_address_city=ballot_returned_results['substituted_address_city'],
                    substituted_address_state=ballot_returned_results['substituted_address_state'],
                    substituted_address_zip=ballot_returned_results['substituted_address_zip'],
                )
                status += save_results['status']
                results = {
                    'status':                   status,
                    'success':                  save_results['success'],
                    'google_civic_election_id': save_results['google_civic_election_id'],
                    'use_office_held_ballot':   False,
                    'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                    'voter_ballot_saved':       save_results['voter_ballot_saved'],
                }
                return results
            else:
                # If here, then we couldn't find or generate a voter_ballot_saved entry
                results = {
                    'status':                   status,
                    'success':                  False,
                    'google_civic_election_id': google_civic_election_id,
                    'use_office_held_ballot':   False,
                    'voter_ballot_saved_found': False,
                    'voter_ballot_saved':       VoterBallotSaved(),
                }
                return results

        # If a partial address doesn't exist, exit because we can't generate a ballot without an address
        if voter_address_exists and not positive_value_exists(voter_address.text_for_map_search):
            status += "VOTER_ADDRESS_BLANK "
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': 0,
                'state_code':               '',
                'use_office_held_ballot':   False,
                'voter_ballot_saved_found': False,
                'voter_ballot_saved':       None,
            }
            return results

        # 1) Find ballot specific to the voter's address
        # This code is for voterBallotItemsRetrieve. Similar code in voterAddressSave.
        # Search for these variables elsewhere when updating code
        turn_off_direct_voter_ballot_retrieve = False
        default_election_data_source_is_ballotpedia = False
        default_election_data_source_is_ctcl = True
        default_election_data_source_is_google_civic = False
        default_election_data_source_is_vote_usa = False
        if turn_off_direct_voter_ballot_retrieve:
            # We set this option when we want to force the retrieval of a nearby ballot
            pass
        elif default_election_data_source_is_ballotpedia:
            status += "SHOULD_WE_USE_BALLOTPEDIA_API? "
            length_at_which_we_suspect_address_has_street = 25
            length_of_text_for_map_search = 0
            if isinstance(text_for_map_search, str):
                length_of_text_for_map_search = len(text_for_map_search)

            if positive_value_exists(google_civic_election_id) and positive_value_exists(voter_id):
                # Delete voter-specific ballot_returned for this election
                ballot_returned_manager = BallotReturnedManager()
                results = ballot_returned_manager.delete_ballot_returned_by_identifier(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id)

                # Delete voter_ballot_saved for this election
                voter_ballot_saved_manager.delete_voter_ballot_saved(
                    voter_id=voter_id, google_civic_election_id=google_civic_election_id)

                # Delete all existing voter-specific ballot items for this election
                ballot_item_list_manager = BallotItemListManager()
                ballot_item_list_manager.delete_all_ballot_items_for_voter(voter_id, google_civic_election_id)

            # We don't want to call Ballotpedia when we just have "City, State ZIP". Since we don't always know
            #  whether we have a street address or not, then we use a simple string length cut-off.
            if length_of_text_for_map_search > length_at_which_we_suspect_address_has_street:
                status += "GENERATE_BALLOT_DATA_BP_TEXT_FOR_MAP_SEARCH_LONG_ENOUGH "
                # 1a) Get ballot data from Ballotpedia for the actual VoterAddress
                from import_export_ballotpedia.controllers import \
                    voter_ballot_items_retrieve_from_ballotpedia_for_api_v4
                ballotpedia_retrieve_results = voter_ballot_items_retrieve_from_ballotpedia_for_api_v4(
                    voter_device_id,
                    text_for_map_search=text_for_map_search)
                status += ballotpedia_retrieve_results['status']
                if ballotpedia_retrieve_results['google_civic_election_id'] \
                        and ballotpedia_retrieve_results['ballot_returned_found']:
                    is_from_substituted_address = False
                    substituted_address_nearby = ''
                    is_from_test_address = False
                    polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter

                    # We update the voter_address with this google_civic_election_id outside this function

                    # Save the meta information for this ballot data
                    save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                        voter_id=voter_id,
                        google_civic_election_id=ballotpedia_retrieve_results['google_civic_election_id'],
                        state_code=ballotpedia_retrieve_results['state_code'],
                        election_day_text=ballotpedia_retrieve_results['election_day_text'],
                        election_description_text=ballotpedia_retrieve_results['election_description_text'],
                        original_text_for_map_search=ballotpedia_retrieve_results['text_for_map_search'],
                        substituted_address_nearby=substituted_address_nearby,
                        is_from_substituted_address=is_from_substituted_address,
                        is_from_test_ballot=is_from_test_address,
                        polling_location_we_vote_id_source=polling_location_we_vote_id_source,
                        ballot_location_display_name=ballotpedia_retrieve_results['ballot_location_display_name'],
                        ballot_returned_we_vote_id=ballotpedia_retrieve_results['ballot_returned_we_vote_id'],
                        ballot_location_shortcut=ballotpedia_retrieve_results['ballot_location_shortcut'],
                        original_text_city=ballotpedia_retrieve_results['original_text_city'],
                        original_text_state=ballotpedia_retrieve_results['original_text_state'],
                        original_text_zip=ballotpedia_retrieve_results['original_text_zip'],
                    )
                    status += save_results['status']
                    results = {
                        'status':                   status,
                        'success':                  save_results['success'],
                        'google_civic_election_id': save_results['google_civic_election_id'],
                        'use_office_held_ballot':   False,
                        'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                        'voter_ballot_saved':       save_results['voter_ballot_saved'],
                    }
                    return results
            else:
                status += "NOT_REACHING_OUT_TO_BALLOTPEDIA "
        elif default_election_data_source_is_ctcl:
            status += "SHOULD_WE_USE_CTCL_API? "
            length_at_which_we_suspect_address_has_street = 25
            length_of_text_for_map_search = 0
            if isinstance(text_for_map_search, str):
                length_of_text_for_map_search = len(text_for_map_search)

            # We don't want to call CTCL when we just have "City, State ZIP". Since we don't always know
            #  whether we have a street address or not, then we use a simple string length cut-off.
            if length_of_text_for_map_search > length_at_which_we_suspect_address_has_street:
                status += "GENERATE_BALLOT_DATA_CTCL_TEXT_FOR_MAP_SEARCH_LONG_ENOUGH "
                # 1a) Get ballot data for the actual VoterAddress
                from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_2021
                ctcl_retrieve_results = voter_ballot_items_retrieve_from_google_civic_2021(
                    voter_device_id,
                    text_for_map_search=text_for_map_search,
                    use_ctcl=True)
                status += ctcl_retrieve_results['status']
                if ctcl_retrieve_results['google_civic_election_id'] \
                        and ctcl_retrieve_results['ballot_returned_found']:
                    is_from_substituted_address = False
                    substituted_address_nearby = ''
                    is_from_test_address = False
                    polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter

                    # We update the voter_address with this google_civic_election_id outside of this function

                    # Save the meta information for this ballot data
                    save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                        voter_id=voter_id,
                        google_civic_election_id=ctcl_retrieve_results['google_civic_election_id'],
                        state_code=ctcl_retrieve_results['state_code'],
                        election_day_text=ctcl_retrieve_results['election_day_text'],
                        election_description_text=ctcl_retrieve_results['election_description_text'],
                        original_text_for_map_search=ctcl_retrieve_results['text_for_map_search'],
                        substituted_address_nearby=substituted_address_nearby,
                        is_from_substituted_address=is_from_substituted_address,
                        is_from_test_ballot=is_from_test_address,
                        polling_location_we_vote_id_source=polling_location_we_vote_id_source,
                        ballot_location_display_name=ctcl_retrieve_results['ballot_location_display_name'],
                        ballot_returned_we_vote_id=ctcl_retrieve_results['ballot_returned_we_vote_id'],
                        ballot_location_shortcut=ctcl_retrieve_results['ballot_location_shortcut'],
                        original_text_city=ctcl_retrieve_results['original_text_city'],
                        original_text_state=ctcl_retrieve_results['original_text_state'],
                        original_text_zip=ctcl_retrieve_results['original_text_zip'],
                    )
                    status += save_results['status']
                    results = {
                        'status':                   status,
                        'success':                  save_results['success'],
                        'google_civic_election_id': save_results['google_civic_election_id'],
                        'use_office_held_ballot':   False,
                        'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                        'voter_ballot_saved':       save_results['voter_ballot_saved'],
                    }
                    return results
            else:
                status += "NOT_REACHING_OUT_TO_CTCL "
        elif default_election_data_source_is_google_civic:
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
                    google_retrieve_results['ballot_location_shortcut'],
                    original_text_city=google_retrieve_results['original_text_city'],
                    original_text_state=google_retrieve_results['original_text_state'],
                    original_text_zip=google_retrieve_results['original_text_zip'],
                )
                status += save_results['status']
                results = {
                    'status':                   status,
                    'success':                  save_results['success'],
                    'google_civic_election_id': save_results['google_civic_election_id'],
                    'use_office_held_ballot':   False,
                    'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                    'voter_ballot_saved':       save_results['voter_ballot_saved'],
                }
                return results
        elif default_election_data_source_is_vote_usa:
            status += "DEFAULT_ELECTION_SOURCE_IS_VOTE_USA "
            length_at_which_we_suspect_address_has_street = 25
            length_of_text_for_map_search = 0
            if isinstance(text_for_map_search, str):
                length_of_text_for_map_search = len(text_for_map_search)

            # We don't want to call Vote USA when we just have "City, State ZIP".
            # Since we don't always know whether we have a street address or not, then we use a
            # simple string length cut-off.
            if length_of_text_for_map_search > length_at_which_we_suspect_address_has_street:
                status += "GENERATE_BALLOT_DATA_VOTE_USA_TEXT_FOR_MAP_SEARCH_LONG_ENOUGH "
                # 1a) Get ballot data for the actual VoterAddress
                from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_2021
                vote_usa_results = voter_ballot_items_retrieve_from_google_civic_2021(
                    voter_device_id,
                    text_for_map_search=text_for_map_search,
                    use_vote_usa=True)
                status += vote_usa_results['status']
                if vote_usa_results['google_civic_election_id'] \
                        and vote_usa_results['ballot_returned_found']:
                    is_from_substituted_address = False
                    substituted_address_nearby = ''
                    is_from_test_address = False
                    polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter

                    # We update the voter_address with this google_civic_election_id outside this function

                    # Save the meta information for this ballot data
                    save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                        voter_id=voter_id,
                        google_civic_election_id=vote_usa_results['google_civic_election_id'],
                        state_code=vote_usa_results['state_code'],
                        election_day_text=vote_usa_results['election_day_text'],
                        election_description_text=vote_usa_results['election_description_text'],
                        original_text_for_map_search=vote_usa_results['text_for_map_search'],
                        substituted_address_nearby=substituted_address_nearby,
                        is_from_substituted_address=is_from_substituted_address,
                        is_from_test_ballot=is_from_test_address,
                        polling_location_we_vote_id_source=polling_location_we_vote_id_source,
                        ballot_location_display_name=vote_usa_results['ballot_location_display_name'],
                        ballot_returned_we_vote_id=vote_usa_results['ballot_returned_we_vote_id'],
                        ballot_location_shortcut=vote_usa_results['ballot_location_shortcut'],
                        original_text_city=vote_usa_results['original_text_city'],
                        original_text_state=vote_usa_results['original_text_state'],
                        original_text_zip=vote_usa_results['original_text_zip'],
                    )
                    status += save_results['status']
                    results = {
                        'status':                   status,
                        'success':                  save_results['success'],
                        'google_civic_election_id': save_results['google_civic_election_id'],
                        'use_office_held_ballot':   False,
                        'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
                        'voter_ballot_saved':       save_results['voter_ballot_saved'],
                    }
                    return results
            else:
                status += "NOT_REACHING_OUT_TO_VOTE_USA "

        # 2) Find ballot data from a nearby address, previously retrieved from primary source and cached within We Vote
        ballot_returned_results = find_best_previously_stored_ballot_returned(voter_id, text_for_map_search)
        status += ballot_returned_results['status']
        if ballot_returned_results['ballot_returned_found']:
            # If this ballot_returned entry is the result of searching based on an address, as opposed to
            # a specific_ballot_requested, we want to update the VoterAddress
            if not specific_ballot_requested and positive_value_exists(voter_address.text_for_map_search):
                try:
                    voter_address.ballot_location_display_name = ballot_returned_results['ballot_location_display_name']
                    voter_address.ballot_returned_we_vote_id = ballot_returned_results['ballot_returned_we_vote_id']
                    voter_address.save()
                except Exception as e:
                    pass

            # And now store the details of this ballot for this voter
            is_from_substituted_address = True
            is_from_test_address = False
            save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                voter_id,
                ballot_returned_results['google_civic_election_id'],
                ballot_returned_results['state_code'],
                ballot_returned_results['election_day_text'],
                ballot_returned_results['election_description_text'],
                text_for_map_search,
                ballot_returned_results['substituted_address_nearby'],
                is_from_substituted_address,
                is_from_test_address,
                ballot_returned_results['polling_location_we_vote_id_source'],
                ballot_returned_results['ballot_location_display_name'],
                ballot_returned_results['ballot_returned_we_vote_id'],
                ballot_returned_results['ballot_location_shortcut'],
                substituted_address_city=ballot_returned_results['original_text_city'],
                substituted_address_state=ballot_returned_results['original_text_state'],
                substituted_address_zip=ballot_returned_results['original_text_zip'],
            )
            status += save_results['status']
            results = {
                'status':                   status,
                'success':                  save_results['success'],
                'google_civic_election_id': save_results['google_civic_election_id'],
                'use_office_held_ballot':   False,
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
        #         'use_office_held_ballot':   False,
        #         'voter_ballot_saved_found': save_results['voter_ballot_saved_found'],
        #         'voter_ballot_saved':       save_results['voter_ballot_saved'],
        #     }
        #     return results

    status += " UNABLE_TO_GENERATE_BALLOT_DATA "
    results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'use_office_held_ballot':   False,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None,
    }
    return results


def voter_ballot_list_retrieve_for_api(voter_id):  # voterBallotListRetrieve
    voter_ballot_list_for_json = []
    election_ids_in_voter_ballot_saved_list = []
    final_ballot_list = []

    # Retrieve all the upcoming elections
    election_manager = ElectionManager()
    results = election_manager.retrieve_listed_elections()
    election_list = results['election_list']
    election_list_by_election_id = {}
    for one_election in election_list:
        election_list_by_election_id[one_election.google_civic_election_id] = one_election
    elections_retrieved_count = 0

    # If a voter_id was passed in, return a list of elections the voter has looked at
    if positive_value_exists(voter_id):
        voter_ballot_saved_manager = VoterBallotSavedManager()
        voter_ballot_list_results = voter_ballot_saved_manager.retrieve_ballots_per_voter_id(voter_id)
        if voter_ballot_list_results['voter_ballot_list_found']:
            voter_ballot_list = voter_ballot_list_results['voter_ballot_list']
            for one_ballot_entry in voter_ballot_list:
                google_civic_election_id = convert_to_int(one_ballot_entry.google_civic_election_id)
                if google_civic_election_id not in election_list_by_election_id:
                    results = election_manager.retrieve_election(google_civic_election_id)
                    if results['election_found']:
                        election_list_by_election_id[google_civic_election_id] = results['election']
                try:
                    election = election_list_by_election_id[google_civic_election_id]
                    state_code_list = election.state_code_list()
                except Exception as e:
                    state_code_list = []
                # # Return the states that have ballot items in this election
                # results = ballot_returned_list_manager.retrieve_state_codes_in_election(google_civic_election_id)
                # if results['success']:
                #     state_code_list = results['state_code_list']

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
                    "state_code":                   one_ballot_entry.state_code,
                    "state_code_list":              state_code_list,
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

            # State code list
            state_code_list = election.state_code_list()
            # # Return the states that have ballot items in this election
            # results = ballot_returned_list_manager.retrieve_state_codes_in_election(google_civic_election_id)
            # if results['success']:
            #     state_code_list = results['state_code_list']

            one_election = {
                "google_civic_election_id":         convert_to_int(election.google_civic_election_id),
                "election_description_text":        election.election_name,
                "election_day_text":                election.election_day_text,
                "original_text_for_map_search":     "",
                "ballot_returned_we_vote_id":       "",
                "ballot_location_shortcut":         "",
                "state_code":                       election.state_code,
                "state_code_list":                  state_code_list,
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
            'use_office_held_ballot':   False,
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
        'use_office_held_ballot': False,
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
            'use_office_held_ballot':   False,
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
        'use_office_held_ballot': False,
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
            voter_id, google_civic_election_id)  # Not read only
        status += voter_ballot_saved_results['status']
        if voter_ballot_saved_results['voter_ballot_saved_found']:
            voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
            status += "VOTER_BALLOT_SAVED_FOUND_1 "
            results = {
                'status':                   status,
                'success':                  True,
                'google_civic_election_id': voter_ballot_saved.google_civic_election_id,
                'use_office_held_ballot':   False,
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
                'use_office_held_ballot':   False,
                'voter_ballot_saved_found': False,
                'voter_ballot_saved':       VoterBallotSaved()
            }
            return results

    if positive_value_exists(voter_device_link.google_civic_election_id):
        # If the voter_device_link was updated within the last day, use that election_id.
        # We do this check because we don't want a voter to return to an election they are just investigating which
        # may not be related to their address.
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        datetime_now = generate_localized_datetime_from_obj()[1]
        election_choice_is_stale_boolean = False
        election_choice_is_stale_duration = timedelta(days=1)
        election_choice_is_stale_date = datetime_now
        if voter_device_link.date_election_last_changed:
            election_choice_is_stale_date = \
                voter_device_link.date_election_last_changed + election_choice_is_stale_duration
        state_code = ""
        voter_device_link_election_is_current = True

        # Run through this process based on voter_device_link data
        if not voter_device_link.date_election_last_changed or not election_choice_is_stale_date:
            election_choice_is_stale_boolean = True
        elif datetime_now and election_choice_is_stale_date:
            if datetime_now > election_choice_is_stale_date:
                election_choice_is_stale_boolean = True

        if election_choice_is_stale_boolean:
            voter_device_link_election_is_current = False
            status += "VOTER_DEVICE_LINK_ELECTION_EXISTS_AND_SHOULD_BE_ERASED "
            try:
                voter_device_link.google_civic_election_id = 0
                voter_device_link.save()
            except Exception as e:
                status += "VOTER_DEVICE_LINK_ELECTION_COULD_NOT_BE_ERASED: " + str(e) + " "

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
                    'use_office_held_ballot':   False,
                    'voter_ballot_saved_found': True,
                    'voter_ballot_saved':       voter_ballot_saved
                }
                return results
            else:
                # If here, then we expected a VoterBallotSaved entry, but didn't find it.
                # Remove google_civic_election_id from voter_device_link.
                status += "VOTER_BALLOT_SAVED_MISSING_REMOVE_ELECTION_FROM_DEVICE_LINK "
                try:
                    voter_device_link.google_civic_election_id = 0
                    voter_device_link.save()
                except Exception as e:
                    status += "VOTER_DEVICE_LINK_ELECTION_COULD_NOT_BE_ERASED2: " + str(e) + " "

    # Run through this process again based on voter_address data
    voter_address_exists = \
        voter_address and hasattr(voter_address, 'voter_id') and positive_value_exists(voter_address.voter_id)
    if not voter_address_exists:
        voter_address_google_civic_election_id = 0
    elif not positive_value_exists(voter_address.google_civic_election_id):
        voter_address_google_civic_election_id = 0
    else:
        voter_address_google_civic_election_id = voter_address.google_civic_election_id
    voter_address_google_civic_election_id = convert_to_int(voter_address_google_civic_election_id)
    if positive_value_exists(voter_address_google_civic_election_id):
        # If the voter_address was updated more than 7 days ago, check for a more current ballot.
        # We do this check because we don't want a voter to return 1 year later and be returned to the old election,
        # nor do we want to assume the ballot from a week ago is the most current for their location/address.
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        datetime_now = generate_localized_datetime_from_obj()[1]
        election_choice_is_stale_boolean = False
        election_choice_is_stale_duration = timedelta(days=7)
        election_choice_is_stale_date = datetime_now
        if voter_address.date_last_changed:
            election_choice_is_stale_date = voter_address.date_last_changed + election_choice_is_stale_duration
        state_code = ""
        voter_address_election_is_current = True
        if not voter_address.date_last_changed or not election_choice_is_stale_date:
            election_choice_is_stale_boolean = True
        elif datetime_now and election_choice_is_stale_date:
            if datetime_now > election_choice_is_stale_date:
                election_choice_is_stale_boolean = True

        if election_choice_is_stale_boolean:
            voter_address_election_is_current = False
            status += "VOTER_ADDRESS_ELECTION_EXPIRED "
            try:
                voter_address.google_civic_election_id = 0
                voter_address.save()
            except Exception as e:
                status += "VOTER_ADDRESS_ELECTION_ID_COULD_NOT_BE_REMOVED: " + str(e) + " "

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
                    'use_office_held_ballot':   False,
                    'voter_ballot_saved_found': True,
                    'voter_ballot_saved':       voter_ballot_saved
                }
                return results
            else:
                # If here, then we expected a VoterBallotSaved entry, but didn't find it.
                # Remove google_civic_election_id from voter address.
                status += "VOTER_BALLOT_SAVED_MISSING_REMOVE_ADDRESS_ELECTION "
                try:
                    voter_address.ballot_returned_we_vote_id = ""
                    voter_address.google_civic_election_id = 0
                    voter_address.save()
                except Exception as e:
                    status += "VOTER_ADDRESS_ELECTION_COULD_NOT_BE_REMOVED2: " + str(e) + " "
        else:
            status += "VOTER_ADDRESS_ELECTION_NOT_CURRENT "

    status += "VOTER_BALLOT_SAVED_NOT_FOUND_FROM_EXISTING_DATA "
    error_results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'use_office_held_ballot':   False,
        'voter_ballot_saved_found': False,
        'voter_ballot_saved':       None
    }
    return error_results


def all_ballot_items_retrieve_for_one_election_for_api(google_civic_election_id, state_code_to_find):
    """
    allBallotItemsRetrieve
    :param google_civic_election_id: This variable was passed in explicitly so we can
    get the ballot items related to that election.
    :param state_code_to_find:
    :return:
    """
    status = ""
    success = True
    contest_office_list_manager = ContestOfficeListManager()
    candidate_list_object = CandidateListManager()
    contest_measure_list_manager = ContestMeasureListManager()

    ballot_item_list = []
    ballot_items_to_display = []
    office_list = []
    results = {}

    # Retrieve all offices in this election
    read_only = True
    return_list_of_objects = True
    office_results = contest_office_list_manager.retrieve_all_offices_for_upcoming_election(
        google_civic_election_id, state_code_to_find, return_list_of_objects, read_only)
    office_success = office_results['success']
    status += office_results['status']
    if office_results['office_list_found']:
        office_list = office_results['office_list_objects']

    if not office_success:
        success = False

    first_no_candidates_warning = True
    if office_success:
        status += "OFFICE_LIST_FOUND "
        kind_of_ballot_item = OFFICE
        for contest_office in office_list:
            if positive_value_exists(contest_office.we_vote_id):
                ballot_item_display_name = contest_office.office_name
                office_id = contest_office.id
                office_we_vote_id = contest_office.we_vote_id
                race_office_level = contest_office.ballotpedia_race_office_level
                state_code = contest_office.state_code
                if positive_value_exists(state_code):
                    state_code_lower_case = state_code.lower()
                else:
                    state_code_lower_case = ""
                try:
                    read_only = True
                    results = candidate_list_object.retrieve_all_candidates_for_office(
                        office_we_vote_id=office_we_vote_id, read_only=read_only)
                    candidates_to_display = []
                    if results['candidate_list_found']:
                        candidate_list = results['candidate_list']
                        for candidate in candidate_list:
                            # This should match values returned in candidates_retrieve_for_api (candidatesRetrieve)
                            candidate_state_code = candidate.state_code
                            if positive_value_exists(candidate_state_code):
                                candidate_state_code_lower_case = candidate_state_code.lower()
                            else:
                                candidate_state_code_lower_case = ""
                            withdrawal_date = ''
                            if isinstance(candidate.withdrawal_date, the_other_datetime.date):
                                withdrawal_date = candidate.withdrawal_date.strftime("%Y-%m-%d")
                            one_candidate = {
                                # 'id':                           candidate.id,
                                'we_vote_id':                   candidate.we_vote_id,
                                'ballot_item_display_name':     candidate.display_candidate_name(),
                                # 'ballotpedia_candidate_id':     candidate.ballotpedia_candidate_id,
                                'ballotpedia_candidate_summary': candidate.ballotpedia_candidate_summary,
                                'ballotpedia_candidate_url':    candidate.ballotpedia_candidate_url,
                                # 'ballotpedia_person_id':        candidate.ballotpedia_person_id,
                                # 'candidate_email':              candidate.candidate_email,
                                # 'candidate_phone':              candidate.candidate_phone,
                                # 'candidate_photo_url_large':
                                #     candidate.we_vote_hosted_profile_image_url_large
                                #     if positive_value_exists(
                                #     candidate.we_vote_hosted_profile_image_url_large)
                                #     else candidate.candidate_photo_url(),
                                'candidate_photo_url_medium':
                                    candidate.we_vote_hosted_profile_image_url_medium,
                                'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
                                # 'candidate_url':                candidate.candidate_url,
                                # 'candidate_contact_form_url':   candidate.candidate_contact_form_url,
                                # 'contest_office_id':            candidate.contest_office_id,
                                # 'contest_office_name':          candidate.contest_office_name,
                                # 'contest_office_we_vote_id':    candidate.contest_office_we_vote_id,
                                'facebook_url':                 candidate.facebook_url,
                                'instagram_handle':             candidate.instagram_handle,
                                'instagram_followers_count':    candidate.instagram_followers_count,
                                # 'google_civic_election_id':     candidate.google_civic_election_id,
                                'kind_of_ballot_item':          CANDIDATE,
                                # 'maplight_id':                  candidate.maplight_id,
                                # 'ocd_division_id':              candidate.ocd_division_id,
                                # 'order_on_ballot':              candidate.order_on_ballot,
                                'party':                        candidate.political_party_display(),
                                # 'politician_id':                candidate.politician_id,
                                # 'politician_we_vote_id':        candidate.politician_we_vote_id,
                                'state_code':                   candidate_state_code_lower_case,
                                'supporters_count':             candidate.supporters_count,
                                # 'twitter_url':                  candidate.twitter_url,
                                'twitter_handle':               candidate.fetch_twitter_handle(),
                                'twitter_description':          candidate.twitter_description
                                if positive_value_exists(candidate.twitter_description) and
                                len(candidate.twitter_description) > 1 else '',
                                'twitter_followers_count':      candidate.twitter_followers_count,
                                # 'youtube_url':                  candidate.youtube_url,
                                'is_battleground_race':         candidate.is_battleground_race
                                if positive_value_exists(candidate.is_battleground_race) else False,
                                'withdrawn_from_election':      candidate.withdrawn_from_election,
                                'withdrawal_date':              withdrawal_date,
                                'wikipedia_url': candidate.wikipedia_url,

                            }
                            candidates_to_display.append(one_candidate.copy())
                except Exception as e:
                    status = "FAILED retrieve_all_candidates_for_office: " + str(e) + " "
                    candidates_to_display = []
                    if hasattr(results, 'status'):
                        status += results['status'] + " "

                if len(candidates_to_display):
                    one_ballot_item = {
                        'ballot_item_display_name':     ballot_item_display_name,
                        'candidate_list':               candidates_to_display,
                        'google_civic_election_id':     google_civic_election_id,
                        # 'id':                           office_id,
                        'kind_of_ballot_item':          kind_of_ballot_item,
                        'race_office_level':            race_office_level,
                        'state_code':                   state_code_lower_case,
                        'we_vote_id':                   office_we_vote_id,
                    }
                    ballot_items_to_display.append(one_ballot_item.copy())
                else:
                    if first_no_candidates_warning:
                        status += "NO_CANDIDATES_FOR_OFFICE(S): "
                        first_no_candidates_warning = False
                    status += str(office_we_vote_id) + " "

    # Retrieve all measures in this election
    read_only = True
    return_list_of_objects = True
    measure_limit = 0
    measure_list = []
    google_civic_election_id_list = [google_civic_election_id]
    measure_results = contest_measure_list_manager.retrieve_all_measures_for_upcoming_election(
        google_civic_election_id_list=google_civic_election_id_list,
        state_code=state_code_to_find,
        return_list_of_objects=return_list_of_objects,
        limit=measure_limit,
        read_only=read_only)
    measure_success = measure_results['success']
    status += measure_results['status']
    if measure_results['measure_list_found']:
        measure_list = measure_results['measure_list_objects']

    if not measure_success:
        success = False

    if measure_success:
        status += "MEASURE_LIST_FOUND "
        kind_of_ballot_item = MEASURE
        election_name = ""
        # Now retrieve information about election
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_election(google_civic_election_id)
        if election_results['election_found']:
            election = election_results['election']
            election_name = election.election_name
        for contest_measure in measure_list:
            measure_we_vote_id = contest_measure.we_vote_id
            if positive_value_exists(measure_we_vote_id):
                state_code = contest_measure.state_code
                if positive_value_exists(state_code):
                    state_code_lower_case = state_code.lower()
                else:
                    state_code_lower_case = ""

                one_ballot_item = {
                    'ballot_item_display_name':     contest_measure.measure_title,
                    'google_civic_election_id':     google_civic_election_id,
                    'google_ballot_placement':      contest_measure.google_ballot_placement,
                    'id':                           contest_measure.id,
                    'kind_of_ballot_item':          kind_of_ballot_item,
                    'measure_subtitle':             contest_measure.measure_subtitle,
                    'measure_text':                 contest_measure.measure_text,
                    'measure_url':                  contest_measure.measure_url,
                    'no_vote_description':          strip_html_tags(contest_measure.ballotpedia_no_vote_description),
                    # 'district_name':                "",  # TODO Add this
                    'election_display_name':        election_name,
                    # 'regional_display_name':        "",  # TODO Add this
                    # 'state_display_name':           "",  # TODO Add this
                    'we_vote_id':                   measure_we_vote_id,
                    'state_code':                   state_code_lower_case,
                    'yes_vote_description':         strip_html_tags(contest_measure.ballotpedia_yes_vote_description),
                }
                ballot_items_to_display.append(one_ballot_item.copy())

    results = {
        'status': status,
        'success': success,
        'ballot_item_list': ballot_items_to_display,
        'google_civic_election_id': google_civic_election_id,
    }
    return results


def ballot_items_search_retrieve_for_api(search_string):  # ballotItemsSearchRetrieve
    """
    IMPLEMENTATION NOT COMPLETE
    2020-07-12 I decided to use ballotItemOptionsRetrieve instead.
    If we choose to finish building ballotItemsSearchRetrieve, it would be so we can
    return the entire Office (with other candidates) when we find one candidate.
    :param search_string:
    :return:
    """
    status = ""
    success = True
    contest_office_list_manager = ContestOfficeListManager()
    candidate_list_object = CandidateListManager()
    contest_measure_list_manager = ContestMeasureListManager()

    ballot_found = False
    ballot_item_list = []
    ballot_items_to_display = []
    office_list = []
    results = {}

    # # Retrieve all offices in this election
    # read_only = True
    # return_list_of_objects = True
    # office_results = contest_office_list_manager.retrieve_all_offices_for_upcoming_election(
    #     google_civic_election_id, state_code_to_find, return_list_of_objects, read_only)
    # office_success = office_results['success']
    # status += office_results['status']
    # if office_results['office_list_found']:
    #     office_list = office_results['office_list_objects']
    #
    # if not office_success:
    #     success = False
    #
    # first_no_candidates_warning = True
    # if office_success:
    #     status += "OFFICE_LIST_FOUND "
    #     kind_of_ballot_item = OFFICE
    #     for contest_office in office_list:
    #         if positive_value_exists(contest_office.we_vote_id):
    #             ballot_item_display_name = contest_office.office_name
    #             office_id = contest_office.id
    #             office_we_vote_id = contest_office.we_vote_id
    #             race_office_level = contest_office.ballotpedia_race_office_level
    #             state_code = contest_office.state_code
    #             if positive_value_exists(state_code):
    #                 state_code_lower_case = state_code.lower()
    #             else:
    #                 state_code_lower_case = ""
    #             try:
    #                 read_only = True
    #                 results = candidate_list_object.retrieve_all_candidates_for_office(
    #                     office_we_vote_id=office_we_vote_id, read_only=read_only)
    #                 candidates_to_display = []
    #                 if results['candidate_list_found']:
    #                     candidate_list = results['candidate_list']
    #                     for candidate in candidate_list:
    #                         # This should match values returned in candidates_retrieve_for_api (candidatesRetrieve)
    #                         candidate_state_code = candidate.state_code
    #                         if positive_value_exists(candidate_state_code):
    #                             candidate_state_code_lower_case = candidate_state_code.lower()
    #                         else:
    #                             candidate_state_code_lower_case = ""
    #                         withdrawal_date = ''
    #                         if isinstance(candidate.withdrawal_date, the_other_datetime.date):
    #                             withdrawal_date = candidate.withdrawal_date.strftime("%Y-%m-%d")
    #                         one_candidate = {
    #                             # 'id':                           candidate.id,
    #                             'we_vote_id':                   candidate.we_vote_id,
    #                             'ballot_item_display_name':     candidate.display_candidate_name(),
    #                             # 'ballotpedia_candidate_id':     candidate.ballotpedia_candidate_id,
    #                             'ballotpedia_candidate_summary': candidate.ballotpedia_candidate_summary,
    #                             'ballotpedia_candidate_url':    candidate.ballotpedia_candidate_url,
    #                             # 'ballotpedia_person_id':        candidate.ballotpedia_person_id,
    #                             # 'candidate_email':              candidate.candidate_email,
    #                             # 'candidate_phone':              candidate.candidate_phone,
    #                             # 'candidate_photo_url_large':
    #                             #     candidate.we_vote_hosted_profile_image_url_large
    #                             #     if positive_value_exists(
    #                             #     candidate.we_vote_hosted_profile_image_url_large)
    #                             #     else candidate.candidate_photo_url(),
    #                             'candidate_photo_url_medium':
    #                                 candidate.we_vote_hosted_profile_image_url_medium,
    #                             'candidate_photo_url_tiny': candidate.we_vote_hosted_profile_image_url_tiny,
    #                             # 'candidate_url':                candidate.candidate_url,
    #                             # 'candidate_contact_form_url':   candidate.candidate_contact_form_url,
    #                             # 'contest_office_id':            candidate.contest_office_id,
    #                             # 'contest_office_name':          candidate.contest_office_name,
    #                             # 'contest_office_we_vote_id':    candidate.contest_office_we_vote_id,
    #                             # 'facebook_url':                 candidate.facebook_url,
    #                             # 'google_civic_election_id':     candidate.google_civic_election_id,
    #                             'kind_of_ballot_item':          CANDIDATE,
    #                             # 'maplight_id':                  candidate.maplight_id,
    #                             # 'ocd_division_id':              candidate.ocd_division_id,
    #                             # 'order_on_ballot':              candidate.order_on_ballot,
    #                             'party':                        candidate.political_party_display(),
    #                             # 'politician_id':                candidate.politician_id,
    #                             # 'politician_we_vote_id':        candidate.politician_we_vote_id,
    #                             'state_code':                   candidate_state_code_lower_case,
    #                             'supporters_count':             candidate.supporters_count,
    #                             # 'twitter_url':                  candidate.twitter_url,
    #                             'twitter_handle':               candidate.fetch_twitter_handle(),
    #                             'twitter_description':          candidate.twitter_description,
    #                             'twitter_followers_count':      candidate.twitter_followers_count,
    #                             # 'youtube_url':                  candidate.youtube_url,
    #                             'is_battleground_race': candidate.is_battleground_race
    #                             if positive_value_exists(candidate.is_battleground_race) else False,
    #                             'withdrawn_from_election':      candidate.withdrawn_from_election,
    #                             'withdrawal_date':              withdrawal_date,
    #                         }
    #                         candidates_to_display.append(one_candidate.copy())
    #             except Exception as e:
    #                 status = "FAILED retrieve_all_candidates_for_office: " + str(e) + " "
    #                 candidates_to_display = []
    #                 if hasattr(results, 'status'):
    #                     status += results['status'] + " "
    #
    #             if len(candidates_to_display):
    #                 one_ballot_item = {
    #                     'ballot_item_display_name':     ballot_item_display_name,
    #                     'candidate_list':               candidates_to_display,
    #                     'google_civic_election_id':     google_civic_election_id,
    #                     # 'id':                           office_id,
    #                     'kind_of_ballot_item':          kind_of_ballot_item,
    #                     'race_office_level':            race_office_level,
    #                     'state_code':                   state_code_lower_case,
    #                     'we_vote_id':                   office_we_vote_id,
    #                 }
    #                 ballot_items_to_display.append(one_ballot_item.copy())
    #             else:
    #                 if first_no_candidates_warning:
    #                     status += "NO_CANDIDATES_FOR_OFFICE(S): "
    #                     first_no_candidates_warning = False
    #                 status += str(office_we_vote_id) + " "
    #
    # # Retrieve all measures in this election
    # read_only = True
    # return_list_of_objects = True
    # measure_limit = 0
    # measure_list = []
    # google_civic_election_id_list = [google_civic_election_id]
    # measure_results = contest_measure_list_manager.retrieve_all_measures_for_upcoming_election(
    #     google_civic_election_id_list=google_civic_election_id_list,
    #     state_code=state_code_to_find,
    #     return_list_of_objects=return_list_of_objects,
    #     limit=measure_limit,
    #     read_only=read_only)
    # measure_success = measure_results['success']
    # status += measure_results['status']
    # if measure_results['measure_list_found']:
    #     measure_list = measure_results['measure_list_objects']
    #
    # if not measure_success:
    #     success = False
    #
    # if measure_success:
    #     status += "MEASURE_LIST_FOUND "
    #     kind_of_ballot_item = MEASURE
    #     election_name = ""
    #     # Now retrieve information about election
    #     election_manager = ElectionManager()
    #     election_results = election_manager.retrieve_election(google_civic_election_id)
    #     if election_results['election_found']:
    #         election = election_results['election']
    #         election_name = election.election_name
    #     for contest_measure in measure_list:
    #         measure_we_vote_id = contest_measure.we_vote_id
    #         if positive_value_exists(measure_we_vote_id):
    #             state_code = contest_measure.state_code
    #             if positive_value_exists(state_code):
    #                 state_code_lower_case = state_code.lower()
    #             else:
    #                 state_code_lower_case = ""
    #
    #             one_ballot_item = {
    #                 'ballot_item_display_name':     contest_measure.measure_title,
    #                 'google_civic_election_id':     google_civic_election_id,
    #                 'google_ballot_placement':      contest_measure.google_ballot_placement,
    #                 'id':                           contest_measure.id,
    #                 'kind_of_ballot_item':          kind_of_ballot_item,
    #                 'measure_subtitle':             contest_measure.measure_subtitle,
    #                 'measure_text':                 contest_measure.measure_text,
    #                 'measure_url':                  contest_measure.measure_url,
    #                 'no_vote_description':          strip_html_tags(contest_measure.ballotpedia_no_vote_description),
    #                 # 'district_name':                "",  # TODO Add this
    #                 'election_display_name':        election_name,
    #                 # 'regional_display_name':        "",  # TODO Add this
    #                 # 'state_display_name':           "",  # TODO Add this
    #                 'we_vote_id':                   measure_we_vote_id,
    #                 'state_code':                   state_code_lower_case,
    #                 'yes_vote_description':         strip_html_tags(contest_measure.ballotpedia_yes_vote_description),
    #             }
    #             ballot_items_to_display.append(one_ballot_item.copy())

    results = {
        'status':                   status,
        'success':                  success,
        'ballot_found':             ballot_found,
        'ballot_item_list':         ballot_items_to_display,
    }
    return results


def retrieve_politician_we_vote_ids_voter_can_vote_for(
        voter_device_id,
        voter_id=0,
        polling_location_we_vote_id=''):
    """

    :param voter_device_id:
    :param voter_id:
    :param polling_location_we_vote_id:
    :return:
    """

    status = ""
    success = True
    ballot_item_list_manager = BallotItemListManager()
    candidate_list_object = CandidateListManager()
    election_manager = ElectionManager()

    ballot_item_list = []
    politician_we_vote_id_list_found = False
    politician_we_vote_id_list = []
    results = {}

    upcoming_google_civic_election_id_list = []
    upcoming_results = election_manager.retrieve_upcoming_google_civic_election_id_list(
        require_include_in_list_for_voters=True
    )
    if upcoming_results['upcoming_google_civic_election_id_list_found']:
        upcoming_google_civic_election_id_list = upcoming_results['upcoming_google_civic_election_id_list']
    try:
        if positive_value_exists(polling_location_we_vote_id):
            results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                polling_location_we_vote_id=polling_location_we_vote_id,
                google_civic_election_id_list=upcoming_google_civic_election_id_list,
                ignore_ballot_item_order=True,
                read_only=True)
            success = results['success']
            status += results['status']
            ballot_item_list = results['ballot_item_list']
        elif positive_value_exists(voter_id):
            results = ballot_item_list_manager.retrieve_all_ballot_items_for_voter(
                voter_id=voter_id,
                google_civic_election_id_list=upcoming_google_civic_election_id_list,
                ignore_ballot_item_order=True,
                read_only=True)
            success = results['success']
            status += results['status']
            ballot_item_list = results['ballot_item_list']
        else:
            success = False
            status += "MISSING_POLLING_LOCATION_AND_VOTER_ID "
    except Exception as e:
        status += 'FAILED voter_ballot_items_retrieve. ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        status += "LOOKING_FOR_POLITICIANS-BALLOT_ITEM_LIST_FOUND "
        office_we_vote_id_list = []
        measure_we_vote_id_list = []
        for ballot_item in ballot_item_list:
            if positive_value_exists(ballot_item.contest_office_we_vote_id):
                if ballot_item.contest_office_we_vote_id not in office_we_vote_id_list:
                    office_we_vote_id_list.append(ballot_item.contest_office_we_vote_id)
            elif positive_value_exists(ballot_item.contest_measure_we_vote_id):
                if ballot_item.contest_measure_we_vote_id not in measure_we_vote_id_list:
                    measure_we_vote_id_list.append(ballot_item.contest_measure_we_vote_id)

        if len(office_we_vote_id_list) > 0:
            results = candidate_list_object.retrieve_candidate_we_vote_id_list_from_office_list(
                contest_office_we_vote_id_list=office_we_vote_id_list
            )
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']
            if len(candidate_we_vote_id_list) > 0:
                results = candidate_list_object.retrieve_politician_we_vote_id_list_from_candidate_we_vote_id_list(
                    candidate_we_vote_id_list=candidate_we_vote_id_list)
                politician_we_vote_id_list = results['politician_we_vote_id_list']
                if len(politician_we_vote_id_list) > 0:
                    politician_we_vote_id_list_found = True

    results = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'politician_we_vote_id_list_found': politician_we_vote_id_list_found,
        'politician_we_vote_id_list':       politician_we_vote_id_list,
    }
    return results


def voter_ballot_items_retrieve_for_one_election_for_api(
        voter_device_id, voter_id=0, google_civic_election_id='', ballot_returned_we_vote_id=''):
    """
    voterBallotItemsRetrieve
    :param voter_device_id:
    :param voter_id:
    :param google_civic_election_id: This variable was passed in explicitly so we can
    get the ballot items related to that election.
    :param ballot_returned_we_vote_id:
    :return:
    """
    status = ""
    ballot_item_list_manager = BallotItemListManager()
    ballot_returned_manager = BallotReturnedManager()
    polling_location_we_vote_id = ''

    if positive_value_exists(ballot_returned_we_vote_id):
        ballot_returned_results = \
            ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(ballot_returned_we_vote_id)
        if ballot_returned_results['ballot_returned_found']:
            ballot_returned = ballot_returned_results['ballot_returned']
            polling_location_we_vote_id = ballot_returned.polling_location_we_vote_id

    ballot_item_object_list = []
    ballot_item_list_found = False
    google_civic_election_id_list = [google_civic_election_id]
    try:
        if positive_value_exists(polling_location_we_vote_id):
            results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                polling_location_we_vote_id=polling_location_we_vote_id,
                google_civic_election_id_list=google_civic_election_id_list,
                read_only=True)
            success = results['success']
            status += results['status']
            ballot_item_object_list = results['ballot_item_list']
            ballot_item_list_found = results['ballot_item_list_found']
        else:
            results = ballot_item_list_manager.retrieve_all_ballot_items_for_voter(
                voter_id=voter_id,
                google_civic_election_id_list=google_civic_election_id_list,
                read_only=True)
            success = results['success']
            status += results['status']
            ballot_item_object_list = results['ballot_item_list']
            ballot_item_list_found = results['ballot_item_list_found']
    except Exception as e:
        status += 'FAILED voter_ballot_items_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        results = generate_ballot_item_list_from_object_list(
            ballot_item_object_list=ballot_item_object_list,
            google_civic_election_id=google_civic_election_id,
            voter_device_id=voter_device_id,
        )
    else:
        results = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'ballot_item_list': [],
            'ballot_item_list_found': ballot_item_list_found,
            'google_civic_election_id': google_civic_election_id,
        }

    return results


def generate_ballot_item_list_from_object_list(
        ballot_item_object_list=[],
        google_civic_election_id='',
        voter_device_id=''):
    ballot_items_to_display = []
    results = {}
    status = ''
    success = True

    contest_office_manager = ContestOfficeManager()
    candidate_list_object = CandidateListManager()

    # Loop through measures to make sure we have full measure data needed
    contest_measure_we_vote_id_list = []
    for ballot_item in ballot_item_object_list:
        if ballot_item.contest_measure_we_vote_id and \
                ballot_item.contest_measure_we_vote_id not in contest_measure_we_vote_id_list:
            contest_measure_we_vote_id_list.append(ballot_item.contest_measure_we_vote_id)

    measure_results_dict = {}
    if len(contest_measure_we_vote_id_list) > 0:
        # Retrieve all of these measures with a single call
        measure_list_manager = ContestMeasureListManager()
        results = measure_list_manager.retrieve_measures(
            measure_we_vote_id_list=contest_measure_we_vote_id_list, read_only=True)
        if results['measure_list_found']:
            measure_list_objects = results['measure_list_objects']
            for one_measure in measure_list_objects:
                measure_results_dict[one_measure.we_vote_id] = one_measure

    # Now prepare the full list for json result
    status += "BALLOT_ITEM_LIST_FOUND "
    ballot_item_list_found = len(ballot_item_object_list) > 0
    from candidate.controllers import generate_candidate_dict_from_candidate_object
    for ballot_item in ballot_item_object_list:
        if ballot_item.contest_office_we_vote_id:
            office_name = ""
            kind_of_ballot_item = OFFICE
            office_id = ballot_item.contest_office_id
            office_we_vote_id = ballot_item.contest_office_we_vote_id
            primary_party = ""
            race_office_level = ""
            if positive_value_exists(office_we_vote_id):
                office_results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                    office_we_vote_id, read_only=True)
                if office_results['contest_office_found']:
                    contest_office = office_results['contest_office']
                    office_id = contest_office.id
                    office_name = contest_office.office_name
                    primary_party = contest_office.primary_party
                    race_office_level = contest_office.ballotpedia_race_office_level
            try:
                results = candidate_list_object.retrieve_all_candidates_for_office(
                    office_we_vote_id=office_we_vote_id, read_only=True)

                candidates_to_display = []
                if results['candidate_list_found']:
                    candidate_list = results['candidate_list']
                    for candidate in candidate_list:
                        candidate_dict_results = generate_candidate_dict_from_candidate_object(
                            candidate=candidate,
                            google_civic_election_id=google_civic_election_id,
                            office_id=office_id,
                            office_name=office_name,
                            office_we_vote_id=office_we_vote_id,
                        )
                        if candidate_dict_results['success']:
                            candidate_dict = candidate_dict_results['candidate_dict']
                            candidates_to_display.append(candidate_dict)
            except Exception as e:
                status += 'FAILED retrieve_all_candidates_for_office. ' + str(e) + " "
                candidates_to_display = []
                if hasattr(results, 'status'):
                    status += results['status'] + " "

            if len(candidates_to_display):
                one_ballot_item = {
                    'ballot_item_display_name':     ballot_item.ballot_item_display_name,
                    'google_civic_election_id':     google_civic_election_id,
                    'google_ballot_placement':      ballot_item.google_ballot_placement,
                    'id':                           office_id,
                    'local_ballot_order':           ballot_item.local_ballot_order,
                    'kind_of_ballot_item':          kind_of_ballot_item,
                    'primary_party':                primary_party,
                    'race_office_level':            race_office_level,
                    'we_vote_id':                   office_we_vote_id,
                    'candidate_list':               candidates_to_display,
                }
                ballot_items_to_display.append(one_ballot_item.copy())
            else:
                status += "NO_CANDIDATES_FOR_OFFICE:" + str(office_we_vote_id) + " "
        elif ballot_item.contest_measure_we_vote_id:
            kind_of_ballot_item = MEASURE
            measure_id = ballot_item.contest_measure_id
            measure_we_vote_id = ballot_item.contest_measure_we_vote_id
            measure_display_name_number = 100
            try:
                if measure_we_vote_id in measure_results_dict:
                    ballot_item_display_name = measure_results_dict[measure_we_vote_id].measure_title
                    measure_subtitle = measure_results_dict[measure_we_vote_id].measure_subtitle
                    measure_text = measure_results_dict[measure_we_vote_id].measure_text
                    measure_url = measure_results_dict[measure_we_vote_id].measure_url
                    no_vote_description = measure_results_dict[measure_we_vote_id].ballotpedia_no_vote_description
                    yes_vote_description = measure_results_dict[measure_we_vote_id].ballotpedia_yes_vote_description
                else:
                    ballot_item_display_name = ballot_item.ballot_item_display_name
                    measure_subtitle = ballot_item.measure_subtitle
                    measure_text = ballot_item.measure_text
                    measure_url = ballot_item.measure_url
                    no_vote_description = ballot_item.no_vote_description
                    yes_vote_description = ballot_item.yes_vote_description
            except Exception as e:
                status += "PROBLEM_WITH_MEASURE: " + str(e) + " "
                ballot_item_display_name = ballot_item.ballot_item_display_name
                measure_subtitle = ballot_item.measure_subtitle
                measure_text = ballot_item.measure_text
                measure_url = ballot_item.measure_url
                no_vote_description = ballot_item.no_vote_description
                yes_vote_description = ballot_item.yes_vote_description
            one_ballot_item = {
                'ballot_item_display_name':     ballot_item_display_name,
                'google_civic_election_id':     google_civic_election_id,
                'google_ballot_placement':      ballot_item.google_ballot_placement,
                'id':                           measure_id,
                'kind_of_ballot_item':          kind_of_ballot_item,
                'local_ballot_order':           ballot_item.local_ballot_order + 100,  # Shift to bottom
                'measure_subtitle':             measure_subtitle,
                'measure_text':                 measure_text,
                'measure_url':                  measure_url,
                'no_vote_description':          strip_html_tags(no_vote_description),
                'district_name':                "",  # TODO Add this
                'election_display_name':        "",  # TODO Add this
                'regional_display_name':        "",  # TODO Add this
                'state_display_name':           "",  # TODO Add this
                'we_vote_id':                   measure_we_vote_id,
                'yes_vote_description':         strip_html_tags(yes_vote_description),
            }
            ballot_items_to_display.append(one_ballot_item.copy())

    from operator import itemgetter
    try:
        ballot_item_list_ordered = sorted(ballot_items_to_display, key=itemgetter('local_ballot_order'), reverse=False)
    except Exception as e:
        ballot_item_list_ordered = ballot_items_to_display
        status += "BALLOT_ITEM_LIST_ORDERING_FAILED: " + str(e) + " "

    results = {
        'status':                   status,
        'success':                  True,
        'voter_device_id':          voter_device_id,
        'ballot_item_list':         ballot_item_list_ordered,
        'ballot_item_list_found':   ballot_item_list_found,
        'google_civic_election_id': google_civic_election_id,
    }
    return results


def ballot_item_highlights_retrieve_for_api(starting_year):  # ballotItemHighlightsRetrieve
    from candidate.controllers import retrieve_candidate_list_for_all_prior_elections_this_year, \
        retrieve_candidate_list_for_all_upcoming_elections
    from voter_guide.models import WEBSITES_TO_NEVER_HIGHLIGHT_ENDORSEMENTS
    status = "BALLOT_ITEM_HIGHLIGHTS_RETRIEVE "
    success = True
    highlight_list = []
    names_already_included_list = []

    super_light_candidate_list = True
    results = retrieve_candidate_list_for_all_upcoming_elections(
        super_light_candidate_list=super_light_candidate_list)
    if results['candidate_list_found']:
        all_possible_candidates_list_light = results['candidate_list_light']
        for one_possible_candidate in all_possible_candidates_list_light:
            if one_possible_candidate['name'] not in names_already_included_list:
                names_already_included_list.append(one_possible_candidate['name'])
                one_highlight = {
                    'name':         one_possible_candidate['name'],
                    'we_vote_id':   one_possible_candidate['we_vote_id'],
                }
                highlight_list.append(one_highlight)
            if 'alternate_names' in one_possible_candidate:
                for one_alternate_name in one_possible_candidate['alternate_names']:
                    if one_alternate_name not in names_already_included_list:
                        names_already_included_list.append(one_alternate_name)
                        one_highlight = {
                            'name':         one_alternate_name,
                            'we_vote_id':   one_possible_candidate['we_vote_id'],
                        }
                        highlight_list.append(one_highlight)

    results = retrieve_candidate_list_for_all_prior_elections_this_year(
        super_light_candidate_list=super_light_candidate_list, starting_year=starting_year)
    if results['candidate_list_found']:
        all_possible_candidates_list_light = results['candidate_list_light']
        for one_possible_candidate in all_possible_candidates_list_light:
            if one_possible_candidate['name'] not in names_already_included_list:
                names_already_included_list.append(one_possible_candidate['name'])
                one_highlight = {
                    'name':         one_possible_candidate['name'],
                    'we_vote_id':   one_possible_candidate['we_vote_id'],
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
                            'prior':        1,
                        }
                        highlight_list.append(one_highlight)

    json_data = {
        'status':               status,
        'success':              success,
        'highlight_list':       highlight_list,
        'never_highlight_on':   WEBSITES_TO_NEVER_HIGHLIGHT_ENDORSEMENTS,
    }
    return json_data


def ballot_item_options_retrieve_for_api(google_civic_election_id='', search_string='', state_code=''):
    """
    ballotItemOptionsRetrieve
    This function returns a normalized list of candidates and measures so we can pre-populate form fields.
    Not specific to one voter.
    :param google_civic_election_id:
    :param search_string:
    :param state_code:
    :return:
    """
    status = ""
    candidate_list = []
    candidate_success = True
    measure_list = []
    measure_success = True

    if not positive_value_exists(search_string):
        status += "SEARCH_STRING_REQUIRED "
        json_data = {
            'status': status,
            'success': True,
            'search_string': search_string,
            'ballot_item_list': [],
            'google_civic_election_id': google_civic_election_id,
        }
        results = {
            'status': status,
            'success': True,
            'search_string': search_string,
            'google_civic_election_id': google_civic_election_id,
            'json_data': json_data,
        }
        return results

    if positive_value_exists(google_civic_election_id):
        google_civic_election_id_list = [google_civic_election_id]
    else:
        google_civic_election_id_list = retrieve_upcoming_election_id_list(
            state_code, require_include_in_list_for_voters=False)

    try:
        candidate_list_object = CandidateListManager()
        results = candidate_list_object.search_candidates_in_specific_elections(
            google_civic_election_id_list=google_civic_election_id_list,
            search_string=search_string,
            state_code=state_code)
        candidate_success = results['success']
        status += results['status']
        candidate_list = results['candidate_list_json']
    except Exception as e:
        status += 'FAILED_BALLOT_ITEM_OPTIONS_RETRIEVE-CANDIDATE_LIST. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        candidate_list = []
        candidate_success = False

    try:
        measure_list_object = ContestMeasureListManager()
        results = measure_list_object.search_measures_in_specific_elections(
            google_civic_election_id_list=google_civic_election_id_list,
            search_string=search_string,
            state_code=state_code)
        measure_success = results['success']
        status += ' ' + results['status']
        measure_list = results['measure_list_json']
    except Exception as e:
        status += 'FAILED_BALLOT_ITEM_OPTIONS_RETRIEVE-MEASURE_LIST ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        measure_list = []
        measure_success = False

    ballot_items_to_display = []
    if candidate_success and len(candidate_list):
        for candidate in candidate_list:
            ballot_items_to_display.append(candidate.copy())

    if measure_success and len(measure_list):
        for measure in measure_list:
            ballot_items_to_display.append(measure.copy())

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
        'state_code':               state_code,
        'google_civic_election_id': google_civic_election_id,
        'json_data':                json_data,
    }
    return results


def what_voter_can_vote_for(request, voter_device_id):
    status = ''
    ballot_returned_we_vote_id = ''
    google_civic_election_id = 0

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        status += "VALID_VOTER_DEVICE_ID_MISSING "
        error_json_data = {
            'status':                               status,
            'success':                              False,
            'voter_can_vote_for_politician_we_vote_ids': [],
        }
        return error_json_data

    voter_device_link = voter_device_link_results['voter_device_link']
    voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        status += " " + "VALID_VOTER_ID_MISSING"
        error_json_data = {
            'status':                       status,
            'success':                      False,
            'voter_can_vote_for_politician_we_vote_ids': [],
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

        from geoip.controllers import voter_location_retrieve_from_ip_for_api
        voter_location_results = voter_location_retrieve_from_ip_for_api(request)
        if voter_location_results['voter_location_found']:
            status += 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_FOUND_FROM_IP '
            text_for_map_search = voter_location_results['voter_location']
            status += '*** ' + text_for_map_search + ' ***, '

            google_civic_election_id = 0

            voter_address_results = voter_address_manager.update_or_create_voter_address(
                voter_id=voter_id,
                address_type=BALLOT_ADDRESS,
                raw_address_text=text_for_map_search,
                voter_entered_address=False)
            status += voter_address_results['status'] + ", "

            if voter_address_results['voter_address_found']:
                voter_address = voter_address_results['voter_address']
                if positive_value_exists(voter_address_results['voter_address_has_value']):
                    ballot_retrieval_based_on_voter_address = True
                else:
                    ballot_retrieval_based_on_voter_address = False

    results = choose_election_and_prepare_ballot_data(
        voter_device_link,
        google_civic_election_id,
        voter_address)
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
            'voter_can_vote_for_politician_we_vote_ids': [],
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
            if google_civic_election_id != voter_address.google_civic_election_id:
                voter_address.google_civic_election_id = google_civic_election_id
                voter_address_manager.update_existing_voter_address_object(voter_address)

    polling_location_we_vote_id_source = voter_ballot_saved.polling_location_we_vote_id_source
    results = retrieve_politician_we_vote_ids_voter_can_vote_for(
        voter_device_id,
        voter_id=voter_id,
        polling_location_we_vote_id=polling_location_we_vote_id_source)

    if results['politician_we_vote_id_list_found']:
        politician_we_vote_id_list = results['politician_we_vote_id_list']
    else:
        politician_we_vote_id_list = []
        status += " " + results['status']

    json_data = {
        'status':                       status,
        'success':                      True,
        'voter_can_vote_for_politician_we_vote_ids': politician_we_vote_id_list,
    }
    return json_data
