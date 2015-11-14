# ballot/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItemListManager
from candidate.models import CandidateCampaignList
from exception.models import handle_exception
from import_export_google_civic.controllers import retrieve_and_store_ballot_for_voter
from measure.models import ContestMeasureList
from office.models import ContestOfficeList
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.models import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_ballot_items_retrieve(voter_device_id, google_civic_election_id):
    # Get voter_id from the voter_device_id so we can figure out which ballot_items to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_id': 0,
            'voter_device_id': voter_device_id,
            'ballot_item_list': [],
            'google_civic_election_id': google_civic_election_id,
        }
        results = {
            'success': False,
            'json_data': json_data,
            'google_civic_election_id': 0,  # Force the clearing of google_civic_election_id
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
            'voter_id': voter_id,
            'voter_device_id': voter_device_id,
            'ballot_item_list': [],
            'google_civic_election_id': google_civic_election_id,
        }
        results = {
            'success': False,
            'json_data': json_data,
            'google_civic_election_id': 0,  # Force the clearing of google_civic_election_id
        }
        return results

    # If the google_civic_election_id was found cached in a cookie and passed in, use that
    if positive_value_exists(google_civic_election_id):
        # If we have a google_civic_election_id, we can assume we have ballot information already stored for this voter
        pass
    else:
        # We need to reach out to Google Civic to get this voter's ballot
        # NOTE: We remove prior ballot_items within retrieve_and_store_ballot_for_voter
        results = retrieve_and_store_ballot_for_voter(voter_id)
        # We come back from retrieving the ballot with a google_civic_election_id and the data stored in the BallotItem
        # table
        google_civic_election_id = results['google_civic_election_id']

    if not positive_value_exists(google_civic_election_id):
        # At this point if we don't have a google_civic_election_id, then we don't have an upcoming election
        #  for that address
        json_data = {
            'status': 'NO_UPCOMING_ELECTION_FOR_ADDRESS',
            'success': True,
            'voter_id': voter_id,
            'voter_device_id': voter_device_id,
            'ballot_item_list': [],
            'google_civic_election_id': 0,
        }
        results = {
            'success': True,
            'json_data': json_data,
            'google_civic_election_id': 0,  # Force the clearing of google_civic_election_id
        }
        return results

    ballot_item_list = []
    ballot_items_to_display = []
    try:
        ballot_item_list_object = BallotItemListManager()
        results = ballot_item_list_object.retrieve_all_ballot_items_for_voter(voter_id, google_civic_election_id)
        success = results['success']
        status = results['status']
        ballot_item_list = results['ballot_item_list']
    except Exception as e:
        status = 'FAILED voter_ballot_items_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        for ballot_item in ballot_item_list:
            one_ballot_item = {
                'ballot_item_label':            ballot_item.ballot_item_label,
                'voter_id':                     ballot_item.voter_id,
                'google_civic_election_id':     ballot_item.google_civic_election_id,
                'google_ballot_placement':      ballot_item.google_ballot_placement,
                'local_ballot_order':           ballot_item.local_ballot_order,
                'contest_office_id':            ballot_item.contest_office_id,
                'contest_office_we_vote_id':    ballot_item.contest_office_we_vote_id,
                'contest_measure_id':           ballot_item.contest_measure_id,
                'contest_measure_we_vote_id':   ballot_item.contest_measure_we_vote_id,
            }
            ballot_items_to_display.append(one_ballot_item.copy())

        json_data = {
            'status': 'VOTER_BALLOT_ITEMS_RETRIEVED',
            'success': True,
            'voter_device_id': voter_device_id,
            'voter_id': voter_id,
            'ballot_item_list': ballot_items_to_display,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_id': voter_id,
            'ballot_item_list': [],
            'google_civic_election_id': google_civic_election_id,
        }
    results = {
        'success': success,
        'google_civic_election_id': google_civic_election_id,  # We want to save google_civic_election_id in cookie
        'json_data': json_data,
    }
    return results


def ballot_item_options_retrieve_for_api(google_civic_election_id=0):
    """
    This function returns a normalized list of candidates and measures so we can pre-populate form fields
    :param google_civic_election_id:
    :return:
    """

    status = ""
    try:
        candidate_list_object = CandidateCampaignList()
        results = candidate_list_object.retrieve_all_candidates_for_upcoming_election(google_civic_election_id)
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
        office_list_object = ContestOfficeList()
        results = office_list_object.retrieve_all_offices_for_upcoming_election(google_civic_election_id)
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
        results = measure_list_object.retrieve_all_measures_for_upcoming_election(google_civic_election_id)
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
