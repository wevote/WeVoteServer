# import_export_endorsements/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from urllib.request import Request, urlopen
import json
from organization.models import Organization
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_endorsments(organization):
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
        status += 'ENDORSMENT_URL_REQUIRED '
        results = {
            'success':              False,
            'status':               status
        }
        return results

    try:
        organization_endorsements_api_url = organization.organization_endorsements_api_url
        req = Request(organization_endorsements_api_url, headers={'User-Agent': 'Mozilla/5.0'})
        url = urlopen(req)
        data = url.read()
        status += 'PAGE_FOUND '
        str= data.decode('utf-8')
        response = json.loads(str)
        results = {
            'success':              True,
            'status':               status,
            'endorsments':          response
        }
        return results
    except Exception as err:
        # There are a few possible pages this might refer to
        status += 'ENDORSMENT_LOAD_ERROR '
        results = {
            'success':              False,
            'status':               status
        }
        return results


def import_candidate_position(candidate_position):
    print(candidate_position)

def import_measure_position(measure_position):
    print(measure_position)