# apis_v1/views/views_voter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from reaction.controllers import reaction_like_count_for_api, voter_reaction_like_off_save_for_api, \
    voter_reaction_like_on_save_for_api, reaction_like_status_retrieve_for_api
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def reaction_like_count_view(request):  # reactionLikeCount
    """
    Retrieve the total number of Likes that an item has received, either from the perspective of the voter's
    network of friends, or the entire network. (reactionLikeCount)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    liked_item_we_vote_id = request.GET.get('liked_item_we_vote_id', '')
    limit_to_voters_network = request.GET.get('limit_to_voters_network', False)
    limit_to_voters_network = positive_value_exists(limit_to_voters_network)
    return reaction_like_count_for_api(voter_device_id=voter_device_id, liked_item_we_vote_id=liked_item_we_vote_id,
                                       limit_to_voters_network=limit_to_voters_network)


def voter_reaction_like_off_save_view(request):  # voterReactionLikeOffSave
    """
    Un-mark the reaction for a single position for one voter (voterReactionLikeOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    liked_item_we_vote_id = request.GET.get('liked_item_we_vote_id', '')
    return voter_reaction_like_off_save_for_api(
        voter_device_id=voter_device_id,
        liked_item_we_vote_id=liked_item_we_vote_id)


def voter_reaction_like_on_save_view(request):  # voterReactionLikeOnSave
    """
    Mark the reaction for a single position for one voter (voterReactionLikeOnSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    # We track activity_tidbit_we_vote_id so we can get all of the likes under on major item
    activity_tidbit_we_vote_id = request.GET.get('activity_tidbit_we_vote_id', '')
    liked_item_we_vote_id = request.GET.get('liked_item_we_vote_id', '')
    return voter_reaction_like_on_save_for_api(
        voter_device_id=voter_device_id,
        liked_item_we_vote_id=liked_item_we_vote_id,
        activity_tidbit_we_vote_id=activity_tidbit_we_vote_id)


def reaction_like_status_retrieve_view(request):  # reactionLikeStatusRetrieve
    """
    Retrieve whether or not a reaction is marked for position (reactionLikeStatusRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    liked_item_we_vote_id_list = request.GET.getlist('liked_item_we_vote_id_list[]')
    return reaction_like_status_retrieve_for_api(
        voter_device_id=voter_device_id, liked_item_we_vote_id_list=liked_item_we_vote_id_list)
