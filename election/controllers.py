# election/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Election, ElectionManager
from config.base import get_environment_variable
from import_export_google_civic.controllers import retrieve_from_google_civic_api_election_query, \
    store_results_from_google_civic_api_election_query
import json
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def election_remote_retrieve():
    structured_json = retrieve_from_google_civic_api_election_query()
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

    election_manager = ElectionManager()
    elections_saved = 0
    elections_updated = 0
    elections_not_processed = 0
    for one_election in structured_json:
        logger.debug(
            u"google_civic_election_id: {google_civic_election_id}, election_name: {election_name}, "
            u"election_day_text: {election_day_text}".format(**one_election)
        )
        # Make sure we have the minimum required variables
        if not positive_value_exists(one_election["google_civic_election_id"]) or \
                not positive_value_exists(one_election["election_name"]):
            elections_not_processed += 1
            continue

        results = election_manager.update_or_create_election(
                one_election["google_civic_election_id"],
                one_election["election_name"],
                one_election["election_day_text"],
                one_election["ocd_division_id"])
        if results['success']:
            if results['new_election_created']:
                elections_saved += 1
            else:
                elections_updated += 1
        else:
            elections_not_processed += 1

    elections_results = {
        'saved': elections_saved,
        'updated': elections_updated,
        'not_processed': elections_not_processed,
    }
    return elections_results


def elections_retrieve_list_for_api(voter_device_id):
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

    election_list = Election.objects.all()

    if len(election_list):
        results = {
            'success': True,
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
        'success': False,
        'json_data': json_data,
    }
    return results
