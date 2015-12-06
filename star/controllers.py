# star/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
import json
from star.models import StarItemManager
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.models import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_star_off_save_for_api(voter_device_id, office_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is doing the starring
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    star_item_manager = StarItemManager()
    if positive_value_exists(office_id):
        results = star_item_manager.toggle_off_voter_starred_office(voter_id, office_id)
        status = "STAR_OFF_OFFICE " + results['status']
        success = results['success']
    elif positive_value_exists(candidate_id):
        results = star_item_manager.toggle_off_voter_starred_candidate(voter_id, candidate_id)
        status = "STAR_OFF_CANDIDATE " + results['status']
        success = results['success']
    elif positive_value_exists(measure_id):
        results = star_item_manager.toggle_off_voter_starred_measure(voter_id, measure_id)
        status = "STAR_OFF_MEASURE " + results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_SAVE-OFFICE_ID_AND_CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_star_on_save_for_api(voter_device_id, office_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is doing the starring
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    star_item_manager = StarItemManager()
    if positive_value_exists(office_id):
        results = star_item_manager.toggle_on_voter_starred_office(voter_id, office_id)
        status = "STAR_ON_OFFICE " + results['status']
        success = results['success']
    elif positive_value_exists(candidate_id):
        results = star_item_manager.toggle_on_voter_starred_candidate(voter_id, candidate_id)
        status = "STAR_ON_CANDIDATE " + results['status']
        success = results['success']
    elif positive_value_exists(measure_id):
        results = star_item_manager.toggle_on_voter_starred_measure(voter_id, measure_id)
        status = "STAR_ON_MEASURE " + results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_SAVE-OFFICE_ID_AND_CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_star_status_retrieve_for_api(voter_device_id, office_id, candidate_id, measure_id):
    # Get voter_id from the voter_device_id so we can know who is doing the starring
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':           'VALID_VOTER_DEVICE_ID_MISSING',
            'success':          False,
            'voter_device_id':  voter_device_id,
            'is_starred':       False,
            'office_id':        office_id,
            'candidate_id':     candidate_id,
            'measure_id':       measure_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':           "VALID_VOTER_ID_MISSING",
            'success':          False,
            'voter_device_id':  voter_device_id,
            'is_starred':       False,
            'office_id':        office_id,
            'candidate_id':     candidate_id,
            'measure_id':       measure_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    star_item_manager = StarItemManager()
    if positive_value_exists(office_id):
        # Zero out the unused values
        star_item_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        results = star_item_manager.retrieve_star_item(star_item_id, voter_id, office_id,
                                                       candidate_campaign_id, contest_measure_id)
        status = results['status']
        success = results['success']
        is_starred = results['is_starred']
    elif positive_value_exists(candidate_id):
        # Zero out the unused values
        star_item_id = 0
        contest_office_id = 0
        contest_measure_id = 0
        results = star_item_manager.retrieve_star_item(star_item_id, voter_id, contest_office_id, candidate_id,
                                                       contest_measure_id)
        status = results['status']
        success = results['success']
        is_starred = results['is_starred']
    elif positive_value_exists(measure_id):
        # Zero out the unused values
        star_item_id = 0
        contest_office_id = 0
        candidate_campaign_id = 0
        results = star_item_manager.retrieve_star_item(star_item_id, voter_id, contest_office_id, candidate_campaign_id,
                                                       measure_id)
        status = results['status']
        success = results['success']
        is_starred = results['is_starred']
    else:
        status = 'UNABLE_TO_SAVE-OFFICE_ID_AND_CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False
        is_starred = False

    # From retrieve_star_item
    # results = {
    #     'status':                       status,
    #     'success':                      success,
    #     'star_item_found':              star_item_on_stage_found,
    #     'star_item_id':                 star_item_on_stage_id,
    #     'star_item':                    star_item_on_stage,
    #     'is_starred':                   star_item_on_stage.is_starred(),
    #     'is_not_starred':               star_item_on_stage.is_not_starred(),
    #     'error_result':                 error_result,
    #     'DoesNotExist':                 exception_does_not_exist,
    #     'MultipleObjectsReturned':      exception_multiple_object_returned,
    # }

    json_data = {
        'status':           status,
        'success':          success,
        'voter_device_id':  voter_device_id,
        'is_starred':       is_starred,
        'office_id':        office_id,
        'candidate_id':     candidate_id,
        'measure_id':       measure_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
