# apis_v1/views/views_position.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
import json
from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching
from ballot.models import OFFICE, CANDIDATE, MEASURE
from position.controllers import position_list_for_ballot_item_for_api, position_list_for_opinion_maker_for_api, \
    position_list_for_voter_for_api, \
    position_retrieve_for_api, position_save_for_api
from position.models import ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING, \
    FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC
from position_like.controllers import position_like_count_for_api
from support_oppose_deciding.controllers import position_oppose_count_for_ballot_item_for_api, \
    position_support_count_for_ballot_item_for_api, \
    position_public_oppose_count_for_ballot_item_for_api, \
    position_public_support_count_for_ballot_item_for_api, positions_count_for_all_ballot_items_for_api, \
    positions_count_for_one_ballot_item_for_api
import wevote_functions.admin
from wevote_functions.functions import convert_to_bool, get_voter_device_id,  \
    is_speaker_type_organization, is_speaker_type_public_figure, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def position_list_for_ballot_item_view(request):  # positionListForBallotItem
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in (ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE

    friends_vs_public_incoming = request.GET.get('friends_vs_public', FRIENDS_AND_PUBLIC)
    if friends_vs_public_incoming in (FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC):
        friends_vs_public = friends_vs_public_incoming
    else:
        friends_vs_public = FRIENDS_AND_PUBLIC

    show_positions_this_voter_follows = request.GET.get('show_positions_this_voter_follows', True)
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', "")
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return position_list_for_ballot_item_for_api(voter_device_id=voter_device_id,
                                                 friends_vs_public=friends_vs_public,
                                                 office_id=office_id,
                                                 office_we_vote_id=office_we_vote_id,
                                                 candidate_id=candidate_id,
                                                 candidate_we_vote_id=candidate_we_vote_id,
                                                 measure_id=measure_id,
                                                 measure_we_vote_id=measure_we_vote_id,
                                                 stance_we_are_looking_for=stance_we_are_looking_for,
                                                 show_positions_this_voter_follows=show_positions_this_voter_follows)


def position_list_for_opinion_maker_view(request):  # positionListForOpinionMaker
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE
    friends_vs_public_incoming = request.GET.get('friends_vs_public', ANY_STANCE)
    if friends_vs_public_incoming in (FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC):
        friends_vs_public = friends_vs_public_incoming
    else:
        friends_vs_public = FRIENDS_AND_PUBLIC
    kind_of_opinion_maker = request.GET.get('kind_of_opinion_maker', "")
    opinion_maker_id = request.GET.get('opinion_maker_id', 0)
    opinion_maker_we_vote_id = request.GET.get('opinion_maker_we_vote_id', "")
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")
    filter_for_voter = positive_value_exists(request.GET.get('filter_for_voter', True))
    filter_out_voter = positive_value_exists(request.GET.get('filter_out_voter', False))
    # Make sure filter_for_voter is reset to False if filter_out_voter is true
    filter_for_voter = False if filter_out_voter else filter_for_voter
    if is_speaker_type_organization(kind_of_opinion_maker):
        organization_id = opinion_maker_id
        organization_we_vote_id = opinion_maker_we_vote_id
        public_figure_id = 0
        public_figure_we_vote_id = ''
    elif is_speaker_type_public_figure(kind_of_opinion_maker):
        organization_id = 0
        organization_we_vote_id = ''
        public_figure_id = opinion_maker_id
        public_figure_we_vote_id = opinion_maker_we_vote_id
    else:
        organization_id = 0
        organization_we_vote_id = ''
        public_figure_id = 0
        public_figure_we_vote_id = ''
    return position_list_for_opinion_maker_for_api(voter_device_id=voter_device_id,
                                                   organization_id=organization_id,
                                                   organization_we_vote_id=organization_we_vote_id,
                                                   public_figure_id=public_figure_id,
                                                   public_figure_we_vote_id=public_figure_we_vote_id,
                                                   friends_vs_public=friends_vs_public,
                                                   stance_we_are_looking_for=stance_we_are_looking_for,
                                                   filter_for_voter=filter_for_voter,
                                                   filter_out_voter=filter_out_voter,
                                                   google_civic_election_id=google_civic_election_id,
                                                   state_code=state_code)


def position_list_for_voter_view(request):  # positionListForVoter
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE
    friends_vs_public_incoming = request.GET.get('friends_vs_public', ANY_STANCE)
    if friends_vs_public_incoming in (FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC):
        friends_vs_public = friends_vs_public_incoming
    else:
        friends_vs_public = FRIENDS_AND_PUBLIC
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")
    show_only_this_election = request.GET.get('show_only_this_election', True)
    show_only_this_election = positive_value_exists(show_only_this_election)
    show_all_other_elections = request.GET.get('show_all_other_elections', False)
    show_all_other_elections = positive_value_exists(show_all_other_elections)
    # Make sure show_only_this_election is reset to False if filter_out_voter is true
    show_only_this_election = False if show_all_other_elections else show_only_this_election
    if show_only_this_election or show_all_other_elections and not positive_value_exists(google_civic_election_id):
        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
        google_civic_election_id = results['google_civic_election_id']
    return position_list_for_voter_for_api(voter_device_id=voter_device_id,
                                           friends_vs_public=friends_vs_public,
                                           stance_we_are_looking_for=stance_we_are_looking_for,
                                           show_only_this_election=show_only_this_election,
                                           show_all_other_elections=show_all_other_elections,
                                           google_civic_election_id=google_civic_election_id,
                                           state_code=state_code)


def position_retrieve_view(request):
    """
    Retrieve all of the details about a single position based on unique identifier (positionRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_we_vote_id = request.GET.get('position_we_vote_id', '')
    return position_retrieve_for_api(
        position_we_vote_id=position_we_vote_id,
        voter_device_id=voter_device_id
    )


def position_save_view(request):  # positionSave
    """
    Save a single position
    :param request:
    :return:
    """
    # We set values that aren't passed in, to False so we know to treat them as null or unchanged. This allows us to
    #  only change the values we want to
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_we_vote_id = request.GET.get('position_we_vote_id', False)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', False)
    public_figure_we_vote_id = request.GET.get('public_figure_we_vote_id', False)
    voter_we_vote_id = request.GET.get('voter_we_vote_id', False)
    google_civic_election_id = request.GET.get('google_civic_election_id', False)
    ballot_item_display_name = request.GET.get('ballot_item_display_name', False)
    office_we_vote_id = request.GET.get('office_we_vote_id', False)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', False)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', False)
    stance = request.GET.get('stance', False)
    set_as_public_position = request.GET.get('set_as_public_position', True)
    statement_text = request.GET.get('statement_text', False)
    statement_html = request.GET.get('statement_html', False)
    more_info_url = request.GET.get('more_info_url', False)

    results = position_save_for_api(
        voter_device_id=voter_device_id,
        position_we_vote_id=position_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        public_figure_we_vote_id=public_figure_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        ballot_item_display_name=ballot_item_display_name,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        stance=stance,
        set_as_public_position=set_as_public_position,
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def position_oppose_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that oppose this (positionOpposeCountForBallotItem)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_oppose_count_for_ballot_item_for_api(
        voter_device_id=voter_device_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def position_support_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that support this (positionSupportCountForBallotItem)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_support_count_for_ballot_item_for_api(
        voter_device_id=voter_device_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def position_public_oppose_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and public figures that publicly oppose this (positionPublicOpposeCountForBallotItem)
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_public_oppose_count_for_ballot_item_for_api(
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def position_public_support_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and public figures that publicly support this (positionPublicSupportCountForBallotItem)
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_public_support_count_for_ballot_item_for_api(
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def positions_count_for_all_ballot_items_view(request):  # positionsCountForAllBallotItems
    """
    Retrieve the number of support/oppose positions from the voter's network
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    results = positions_count_for_all_ballot_items_for_api(
        voter_device_id=voter_device_id,
        google_civic_election_id=google_civic_election_id)
    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'position_counts_list': results['position_counts_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_count_for_one_ballot_item_view(request):  # positionsCountForOneBallotItem
    """
    Retrieve the number of support/oppose positions from the voter's network for one ballot item
    We return results in the same format as positions_count_for_all_ballot_items_view
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', "")

    results = positions_count_for_one_ballot_item_for_api(
        voter_device_id=voter_device_id,
        ballot_item_we_vote_id=ballot_item_we_vote_id)
    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'position_counts_list': results['position_counts_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_like_count_view(request):
    """
    Retrieve the total number of Likes that a position has received, either from the perspective of the voter's
    network of friends, or the entire network. (positionLikeCount)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    limit_to_voters_network = request.GET.get('limit_to_voters_network', False)
    limit_to_voters_network = positive_value_exists(limit_to_voters_network)
    return position_like_count_for_api(voter_device_id=voter_device_id, position_entered_id=position_entered_id,
                                       limit_to_voters_network=limit_to_voters_network)
