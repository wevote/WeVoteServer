# reaction/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ReactionLike, ReactionLikeManager
from django.http import HttpResponse
import json
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def reaction_like_count_for_api(voter_device_id, liked_item_we_vote_id, limit_to_voters_network=False):
    # Get voter_id from the voter_device_id so we can know who is doing the liking
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':               'VALID_VOTER_DEVICE_ID_MISSING',
            'success':              False,
            'voter_device_id':      voter_device_id,
            'liked_item_we_vote_id':  liked_item_we_vote_id,
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
            'liked_item_we_vote_id':  liked_item_we_vote_id,
            'voter_network_likes':  False,
            'all_likes':            False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    reaction_like_manager = ReactionLikeManager()
    type_of_count = False
    number_of_likes = False
    if positive_value_exists(liked_item_we_vote_id):
        if limit_to_voters_network:
            if positive_value_exists(voter_id):
                results = reaction_like_manager.count_voter_network_reaction_likes(liked_item_we_vote_id, voter_id)
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
            results = reaction_like_manager.count_all_reaction_likes(liked_item_we_vote_id)
            status = results['status']
            success = results['success']
            all_likes = results['number_of_likes']
            voter_network_likes = False
            type_of_count = 'ALL'
            number_of_likes = results['number_of_likes']
    else:
        status = 'UNABLE_TO_RETRIEVE_COUNT-LIKED_ITEM_WE_VOTE_ID_MISSING'
        success = False
        all_likes = False
        voter_network_likes = False

    json_data = {
        'status':               status,
        'success':              success,
        'voter_device_id':      voter_device_id,
        'liked_item_we_vote_id':  liked_item_we_vote_id,
        'type_of_count':        type_of_count,
        'number_of_likes':      number_of_likes,
        'all_likes':            all_likes,
        'voter_network_likes':  voter_network_likes,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_reaction_like_off_save_for_api(voter_device_id, reaction_like_id, liked_item_we_vote_id):
    status = ''
    # Get voter_id from the voter_device_id so we can know who is doing the liking
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        status += "VALID_VOTER_ID_MISSING "
        json_data = {
            'status':                   status,
            'success':                  False,
            'reaction_like_id':         reaction_like_id,
            'liked_item_we_vote_id':    liked_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    reaction_like_manager = ReactionLikeManager()
    if positive_value_exists(reaction_like_id) or \
            (positive_value_exists(voter_id) and positive_value_exists(liked_item_we_vote_id)):
        results = reaction_like_manager.toggle_off_voter_reaction_like(
            reaction_like_id=reaction_like_id,
            voter_id=voter_id,
            liked_item_we_vote_id=liked_item_we_vote_id)
        status += results['status']
        success = results['success']
    else:
        status += 'UNABLE_TO_DELETE_REACTION_LIKE-INSUFFICIENT_VARIABLES '
        success = False

    json_data = {
        'status':                   status,
        'success':                  success,
        'reaction_like_id':         reaction_like_id,
        'liked_item_we_vote_id':    liked_item_we_vote_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_reaction_like_on_save_for_api(voter_device_id, liked_item_we_vote_id):
    status = ''
    # Get voter_id from the voter_device_id so we can know who is doing the liking
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        status += "VALID_VOTER_ID_MISSING "
        json_data = {
            'status':                   status,
            'success':                  False,
            'reaction_like_id':         0,
            'liked_item_we_vote_id':    liked_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id=voter_id, read_only=True)
    if not results['voter_found']:
        status += "VALID_VOTER_MISSING "
        json_data = {
            'status':                   status,
            'success':                  False,
            'reaction_like_id':         0,
            'liked_item_we_vote_id':    liked_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter = results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_display_name = voter.get_full_name(real_name_only=True)

    reaction_like_manager = ReactionLikeManager()
    reaction_like_id = 0
    if positive_value_exists(voter_id) and positive_value_exists(liked_item_we_vote_id):
        results = reaction_like_manager.toggle_on_voter_reaction_like(
            voter_id=voter_id,
            voter_we_vote_id=voter_we_vote_id,
            voter_display_name=voter_display_name,
            liked_item_we_vote_id=liked_item_we_vote_id)
        status += results['status']
        success = results['success']
        reaction_like_id = results['reaction_like_id']
    else:
        status += 'UNABLE_TO_SAVE_REACTION_LIKE-INSUFFICIENT_VARIABLES '
        success = False

    json_data = {
        'status':                   status,
        'success':                  success,
        'reaction_like_id':         reaction_like_id,
        'liked_item_we_vote_id':    liked_item_we_vote_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def reaction_like_status_retrieve_for_api(voter_device_id, liked_item_we_vote_id_list):  # reactionLikeStatusRetrieve
    status = ''
    success = True
    reaction_like_list = []
    # Get voter_id from the voter_device_id so we can know who is doing the liking
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        status += "VALID_VOTER_ID_MISSING "
        json_data = {
            'status':                       status,
            'success':                      False,
            'liked_item_we_vote_id_list':   liked_item_we_vote_id_list,
            'reaction_like_list':           reaction_like_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if liked_item_we_vote_id_list and len(liked_item_we_vote_id_list) > 0:
        try:
            reaction_query = ReactionLike.objects.filter(
                liked_item_we_vote_id__in=liked_item_we_vote_id_list)
            reaction_like_object_list = list(reaction_query)
            status += "REACTION_LIKE_LIST_RETRIEVE "
            for reaction_like in reaction_like_object_list:
                reaction_like_dict = {
                    'voter_id':                 reaction_like.voter_id,
                    'voter_we_vote_id':         reaction_like.voter_we_vote_id,
                    'voter_display_name':       reaction_like.voter_display_name,
                    'liked_item_we_vote_id':    reaction_like.liked_item_we_vote_id,
                    'date_last_changed':        reaction_like.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
                }
                reaction_like_list.append(reaction_like_dict)
        except Exception as e:
            status += "FAILED_RETRIEVING_REACTION_LIKE_LIST " + str(e) + " "
            success = False
    else:
        status += 'UNABLE_TO_RETRIEVE-LIKED_ITEM_WE_VOTE_ID_MISSING '
        success = False

    json_data = {
        'status':                       status,
        'success':                      success,
        'liked_item_we_vote_id_list':   liked_item_we_vote_id_list,
        'reaction_like_list':           reaction_like_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
