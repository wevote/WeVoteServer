# apis_v1/views/views_misc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
import json
import sys
from office.controllers import office_retrieve_for_api
from quick_info.controllers import quick_info_retrieve_for_api
from search.controllers import search_all_for_api
import wevote_functions.admin
from wevote_functions.functions import generate_voter_device_id, get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def device_id_generate_view(request):  # deviceIdGenerate
    """
    This API call is used by clients to generate a transient unique identifier (device_id - stored on client)
    which ties the device to a persistent voter_id (mapped together and stored on the server).
    Note: This call does not create a voter account -- that must be done in voterCreate.

    :param request:
    :return: Unique device id that can be stored in a cookie
    """
    voter_device_id = generate_voter_device_id()  # Stored in cookie elsewhere
    if 'test' not in sys.argv:
        logger.debug("apis_v1/views.py, device_id_generate-voter_device_id: {voter_device_id}".format(
            voter_device_id=voter_device_id
    ))

    if positive_value_exists(voter_device_id):
        success = True
        status = "DEVICE_ID_GENERATE_VALUE_DOES_NOT_EXIST"
    else:
        success = False
        status = "DEVICE_ID_GENERATE_VALUE_EXISTS"

    json_data = {
        'voter_device_id': voter_device_id,
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def office_retrieve_view(request):  # officeRetrieve
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', None)
    return office_retrieve_for_api(office_id, office_we_vote_id)


def quick_info_retrieve_view(request):
    """
    Retrieve the information necessary to populate a bubble next to a ballot item.
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', "")
    return quick_info_retrieve_for_api(kind_of_ballot_item=kind_of_ballot_item,
                                       ballot_item_we_vote_id=ballot_item_we_vote_id)


def search_all_view(request):  # searchAll
    """
    Find information anywhere in the We Vote universe.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    text_from_search_field = request.GET.get('text_from_search_field', '')

    if not positive_value_exists(text_from_search_field):
        status = 'MISSING_TEXT_FROM_SEARCH_FIELD'
        json_data = {
            'status':                   status,
            'success':                  False,
            'text_from_search_field':   text_from_search_field,
            'voter_device_id':          voter_device_id,
            'search_results':           [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = search_all_for_api(text_from_search_field, voter_device_id)
    status = "UNABLE_TO_FIND_ANY_SEARCH_RESULTS "
    search_results = []
    if results['search_results_found']:
        search_results = results['search_results']
        status = results['status']
    else:
        status += results['status']

    json_data = {
        'status':                   status,
        'success':                  True,
        'text_from_search_field':   text_from_search_field,
        'voter_device_id':          voter_device_id,
        'search_results':           search_results,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
