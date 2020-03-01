# election/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Election, ElectionManager
from ballot.models import BallotReturned
from config.base import get_environment_variable
from import_export_google_civic.controllers import retrieve_from_google_civic_api_election_query, \
    store_results_from_google_civic_api_election_query
import json
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ELECTIONS_SYNC_URL = get_environment_variable("ELECTIONS_SYNC_URL")  # electionsSyncOut


def election_remote_retrieve():
    retrieve_results = retrieve_from_google_civic_api_election_query()
    structured_json = retrieve_results.get('structured_json', {})
    error = structured_json.get('error', {})
    errors = error.get('errors', {})
    if not retrieve_results['success'] or len(errors):  # Success refers to http success, not an error free response
        logger.error("Loading Election from Google Civic failed: " + json.dumps(errors))
        results = {
            'success':  False,
            'status':   retrieve_results['status']
        }
        return results
    else:
        results = store_results_from_google_civic_api_election_query(structured_json)
        return results


def elections_import_from_sample_file():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Load saved json from local file
    logger.info("Loading elections from local file")

    with open('election/import_data/elections_sample.json') as json_data:
        structured_json = json.load(json_data)

    return elections_import_from_structured_json(structured_json)


def elections_import_from_master_server(request=None):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Election from We Vote Master servers",
        ELECTIONS_SYNC_URL, {
            "key":    WE_VOTE_API_KEY,  # This comes from an environment variable
        }
    )

    if not import_results['success']:
        return import_results

    return elections_import_from_structured_json(structured_json)


def elections_import_from_structured_json(structured_json):

    election_manager = ElectionManager()
    elections_saved = 0
    elections_updated = 0
    elections_not_processed = 0
    for one_election in structured_json:
        logger.debug(
            u"google_civic_election_id: {google_civic_election_id}, election_name: {election_name}, "
            u"election_day_text: {election_day_text}".format(**one_election)
        )

        ballotpedia_election_id = one_election["ballotpedia_election_id"] \
            if "ballotpedia_election_id" in one_election else ''
        ballotpedia_kind_of_election = one_election["ballotpedia_kind_of_election"] \
            if "ballotpedia_kind_of_election" in one_election else ''
        candidate_photos_finished = one_election["candidate_photos_finished"] \
            if "candidate_photos_finished" in one_election else ''
        election_name = one_election["election_name"] if "election_name" in one_election else ''
        election_day_text = one_election["election_day_text"] if "election_day_text" in one_election else ''
        election_preparation_finished = one_election["election_preparation_finished"] \
            if "election_preparation_finished" in one_election else ''
        google_civic_election_id = one_election["google_civic_election_id"] \
            if "google_civic_election_id" in one_election else ''
        ignore_this_election = one_election["ignore_this_election"] \
            if "ignore_this_election" in one_election else ''
        include_in_list_for_voters = one_election["include_in_list_for_voters"] \
            if "include_in_list_for_voters" in one_election else ''
        internal_notes = one_election["internal_notes"] if "internal_notes" in one_election else ''
        is_national_election_raw = one_election["is_national_election"] \
            if "is_national_election" in one_election else ''
        is_national_election = positive_value_exists(is_national_election_raw)
        ocd_division_id = one_election["ocd_division_id"] if "ocd_division_id" in one_election else ''
        state_code = one_election["state_code"] if "state_code" in one_election else ''

        # Make sure we have the minimum required variables
        if not positive_value_exists(google_civic_election_id) or not positive_value_exists(election_name):
            elections_not_processed += 1
            continue

        results = election_manager.update_or_create_election(
                google_civic_election_id, election_name, election_day_text, ocd_division_id,
                ballotpedia_election_id, ballotpedia_kind_of_election, candidate_photos_finished,
                election_preparation_finished, ignore_this_election, include_in_list_for_voters,
                internal_notes, is_national_election, state_code)

        if results['success']:
            if results['new_election_created']:
                elections_saved += 1
            else:
                elections_updated += 1
        else:
            elections_not_processed += 1

    elections_results = {
        'success':          True,
        'status':           "ELECTION_IMPORT_PROCESS_COMPLETE",
        'saved':            elections_saved,
        'updated':          elections_updated,
        'not_processed':    elections_not_processed,
    }
    return elections_results


def elections_retrieve_for_api():  # electionsRetrieve
    status = ""
    election_list = []

    try:
        # Get the election list using the readonly DB server
        election_list_query = Election.objects.using('readonly').all()
        election_list_query = election_list_query.order_by('-election_day_text')
        election_list_query = election_list_query.filter(include_in_list_for_voters=True)
        success = True
    except Exception as e:
        success = False
        status += "ERROR: " + str(e) + " "
        results = {
            'success': success,
            'status': status,
            'election_list': election_list,
        }
        return results

    election_list_raw = list(election_list_query)
    for election in election_list_raw:
        try:
            ballot_location_list = []
            ballot_returned_query = BallotReturned.objects.using('readonly')
            ballot_returned_query = ballot_returned_query.filter(
                google_civic_election_id=election.google_civic_election_id)
            ballot_returned_query = ballot_returned_query.filter(ballot_location_display_option_on=True)
            ballot_returned_query = ballot_returned_query.order_by('ballot_location_display_name')
            ballot_returned_list = list(ballot_returned_query)

            # ballot_returned_count_query = BallotReturned.objects.using('readonly')
            # ballot_returned_count_query = ballot_returned_count_query.filter(
            #     google_civic_election_id=election.google_civic_election_id)
            # ballot_returned_count = ballot_returned_count_query.count()

            for ballot_returned in ballot_returned_list:
                ballot_location_display_option = {
                    'ballot_location_display_name': ballot_returned.ballot_location_display_name,
                    'ballot_location_shortcut':     ballot_returned.ballot_location_shortcut if
                    ballot_returned.ballot_location_shortcut else '',
                    'text_for_map_search':          ballot_returned.text_for_map_search,
                    'ballot_returned_we_vote_id':   ballot_returned.we_vote_id,
                    'polling_location_we_vote_id':  ballot_returned.polling_location_we_vote_id,
                    'ballot_location_order':        ballot_returned.ballot_location_order,
                    'google_civic_election_id':     ballot_returned.google_civic_election_id,
                }
                ballot_location_list.append(ballot_location_display_option)
            election_json = {
                'google_civic_election_id':     convert_to_int(election.google_civic_election_id),
                'election_name':                election.election_name,
                'election_day_text':            election.election_day_text,
                'election_is_upcoming':         election.election_is_upcoming(),
                'get_election_state':           election.get_election_state(),
                'state_code':                   election.state_code,
                'ocd_division_id':              election.ocd_division_id,
                'ballot_location_list':         ballot_location_list,
                # 'ballot_returned_count':        ballot_returned_count,
            }
            election_list.append(election_json)

        except Exception as e:
            status += "FAILURE: " + str(e) + " "

    results = {
        'success':          success,
        'status':           status,
        'election_list':    election_list,
    }
    return results


def elections_sync_out_list_for_api(voter_device_id):
    # # We care about who the voter is, because we *might* want to limit which elections we show?
    # results = is_voter_device_id_valid(voter_device_id)
    # if not results['success']:
    #     results2 = {
    #         'success': False,
    #         'json_data': results['json_data'],
    #     }
    #     return results2
    #
    # voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    # if voter_id > 0:
    #     voter_manager = VoterManager()
    #     results = voter_manager.retrieve_voter_by_id(voter_id)
    #     if results['voter_found']:
    #         voter_id = results['voter_id']
    # else:
    #     # If we are here, the voter_id could not be found from the voter_device_id
    #     json_data = {
    #         'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
    #         'success': False,
    #         'voter_device_id': voter_device_id,
    #     }
    #     results = {
    #         'success': False,
    #         'json_data': json_data,
    #     }
    #     return results
    #

    try:
        # Get the election list using the readonly DB server
        election_list = Election.objects.using('readonly').all()
        success = True
    except Exception as e:
        success = False

    if success:
        results = {
            'success': success,
            'election_list': election_list,
        }
        return results

    # Trying to mimic the Google Civic error codes scheme
    errors_list = [
        {
            'domain':  "TODO global",
            'reason':  "TODO reason",
            'message':  "TODO Error message here",
            'locationType':  "TODO Error message here",
            'location':  "TODO location",
        }
    ]
    error_package = {
        'errors':   errors_list,
        'code':     400,
        'message':  "Error message here",
    }
    json_data = {
        'error': error_package,
        'status': "ELECTIONS_COULD_NOT_BE_RETRIEVED",
        'success': False,
        'voter_device_id': voter_device_id,
    }
    results = {
        'success': success,
        'json_data': json_data,
    }
    return results


def retrieve_upcoming_election_id_list(limit_to_this_state_code=''):
    # There is a parallel function in election_manager.retrieve_upcoming_google_civic_election_id_list(
    # Figure out the elections we care about
    google_civic_election_id_list = []
    election_manager = ElectionManager()
    # If a state_code is included, national elections will NOT be returned
    # If a state_code is NOT included, the national election WILL be returned with this query
    results = election_manager.retrieve_upcoming_elections(state_code=limit_to_this_state_code)
    if results['election_list_found']:
        upcoming_election_list = results['election_list']
        for one_election in upcoming_election_list:
            if positive_value_exists(one_election.google_civic_election_id):
                google_civic_election_id_list.append(one_election.google_civic_election_id)

    # If a state code IS included, then the above retrieve_upcoming_elections will have missed the national election
    # so we want to return it here
    if positive_value_exists(limit_to_this_state_code):
        results = election_manager.retrieve_next_national_election()
        if results['election_found']:
            one_election = results['election']
            if positive_value_exists(one_election.google_civic_election_id) \
                    and one_election.google_civic_election_id not in google_civic_election_id_list:
                google_civic_election_id_list.append(one_election.google_civic_election_id)

    return google_civic_election_id_list
