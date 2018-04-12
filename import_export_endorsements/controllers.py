# import_export_endorsements/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from import_export_batches.models import BatchManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_endorsements(organization):
    status = ""
    success = False
    page_found = False

    if not organization:
        status += 'ORGANIZATION_REQUIRED '
        results = {
            'success':              False,
            'status':               status
        }
        return results

    if not positive_value_exists(organization.organization_endorsements_api_url):
        status += 'ENDORSEMENT_URL_REQUIRED '
        results = {
            'success':              False,
            'status':               status
        }
        return results

    try:
        # create batch set for endorsements from this json
        batch_manager = BatchManager()
        results = batch_manager.create_batch_set_organization_endorsements(organization)
    except Exception as err:
        # There are a few possible pages this might refer to
        status += 'ENDORSEMENT_LOAD_ERROR '
        results = {
            'success':              False,
            'status':               status
        }
    return results


def import_candidate_position(candidate_position):
    print(candidate_position)


def import_measure_position(measure_position):
    print(measure_position)