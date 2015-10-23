# election/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ElectionManager
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
