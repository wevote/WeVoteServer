# position_like/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionLikeListManager, PositionLikeManager
from django.http import HttpResponse
import json
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def position_like_count_for_api(voter_device_id, position_entered_id, limit_to_voters_network=False):
    # Get voter_id from the voter_device_id so we can know who is doing the liking
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':               'VALID_VOTER_DEVICE_ID_MISSING',
            'success':              False,
            'voter_device_id':      voter_device_id,
            'position_entered_id':  position_entered_id,
            'voter_network_likes':  False,
            'all_likes':            False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':               "VALID_VOTER_ID_MISSING",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'position_entered_id':  position_entered_id,
            'voter_network_likes':  False,
            'all_likes':            False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_like_list_manager = PositionLikeListManager()
    type_of_count = False
    number_of_likes = False
    if positive_value_exists(position_entered_id):
        if limit_to_voters_network:
            if positive_value_exists(voter_id):
                results = position_like_list_manager.count_voter_network_position_likes(position_entered_id, voter_id)
                status = results['status']
                success = results['success']
                all_likes = False
                voter_network_likes = results['number_of_likes']
                type_of_count = 'VOTER_NETWORK'
                number_of_likes = results['number_of_likes']
            else:
                status = 'UNABLE_TO_RETRIEVE_VOTER_NETWORK_COUNT-VOTER_ID_MISSING'
                success = False
                all_likes = False
                voter_network_likes = False
        else:
            results = position_like_list_manager.count_all_position_likes(position_entered_id)
            status = results['status']
            success = results['success']
            all_likes = results['number_of_likes']
            voter_network_likes = False
            type_of_count = 'ALL'
            number_of_likes = results['number_of_likes']
    else:
        status = 'UNABLE_TO_RETRIEVE_COUNT-POSITION_ENTERED_ID_MISSING'
        success = False
        all_likes = False
        voter_network_likes = False

    json_data = {
        'status':               status,
        'success':              success,
        'voter_device_id':      voter_device_id,
        'position_entered_id':  position_entered_id,
        'type_of_count':        type_of_count,
        'number_of_likes':      number_of_likes,
        'all_likes':            all_likes,
        'voter_network_likes':  voter_network_likes,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_like_off_save_for_api(voter_device_id, position_like_id, position_entered_id):
    # Get voter_id from the voter_device_id so we can know who is doing the liking
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

    position_like_manager = PositionLikeManager()
    if positive_value_exists(position_like_id) or \
            (positive_value_exists(voter_id) and positive_value_exists(position_entered_id)):
        results = position_like_manager.toggle_off_voter_position_like(
            position_like_id, voter_id, position_entered_id)
        status = results['status']
        success = results['success']
    else:
        status = 'UNABLE_TO_DELETE_POSITION_LIKE-INSUFFICIENT_VARIABLES'
        success = False

    json_data = {
        'status': status,
        'success': success,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_like_on_save_for_api(voter_device_id, position_entered_id):
    # Get voter_id from the voter_device_id so we can know who is doing the liking
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

    position_like_manager = PositionLikeManager()
    position_like_id = 0
    if positive_value_exists(voter_id) and positive_value_exists(position_entered_id):
        results = position_like_manager.toggle_on_voter_position_like(voter_id, position_entered_id)
        status = results['status']
        success = results['success']
        position_like_id = results['position_like_id']
    else:
        status = 'UNABLE_TO_SAVE_POSITION_LIKE-INSUFFICIENT_VARIABLES'
        success = False

    json_data = {
        'status': status,
        'success': success,
        'position_like_id': position_like_id,
        'position_entered_id': position_entered_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_like_status_retrieve_for_api(voter_device_id, position_entered_id):
    # Get voter_id from the voter_device_id so we can know who is doing the liking
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':               'VALID_VOTER_DEVICE_ID_MISSING',
            'success':              False,
            'voter_device_id':      voter_device_id,
            'is_liked':             False,
            'position_entered_id':  position_entered_id,
            'position_like_id':     0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':               "VALID_VOTER_ID_MISSING",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'is_liked':             False,
            'position_entered_id':  position_entered_id,
            'position_like_id':     0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_like_manager = PositionLikeManager()
    if positive_value_exists(position_entered_id):
        position_like_id = 0
        results = position_like_manager.retrieve_position_like(position_like_id, voter_id, position_entered_id)
        status = results['status']
        success = results['success']
        is_liked = results['is_liked']
        position_like_id = results['position_like_id']
    else:
        status = 'UNABLE_TO_RETRIEVE-POSITION_ENTERED_ID_MISSING'
        success = False
        is_liked = False
        position_like_id = 0

    json_data = {
        'status':               status,
        'success':              success,
        'voter_device_id':      voter_device_id,
        'is_liked':             is_liked,
        'position_entered_id':  position_entered_id,
        'position_like_id':     position_like_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
