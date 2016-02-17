# support_oppose_deciding/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import JsonResponse
from position.models import PositionEnteredManager
from voter.models import fetch_voter_id_from_voter_device_link, voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import get_voter_api_device_id


logger = wevote_functions.admin.get_logger(__name__)


def voter_supporting_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_supporting_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    position_entered_manager = PositionEnteredManager()
    results = position_entered_manager.toggle_on_voter_support_for_candidate_campaign(voter_id, candidate_campaign_id)
    if results['success']:
        return JsonResponse({0: "success"})
    else:
        return JsonResponse({0: "failure"})


def voter_stop_supporting_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_stop_supporting_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    position_entered_manager = PositionEnteredManager()
    results = position_entered_manager.toggle_off_voter_support_for_candidate_campaign(voter_id, candidate_campaign_id)
    if results['success']:
        return JsonResponse({0: "success"})
    else:
        return JsonResponse({0: "failure"})


def voter_opposing_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_opposing_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    position_entered_manager = PositionEnteredManager()
    results = position_entered_manager.toggle_on_voter_oppose_for_candidate_campaign(voter_id, candidate_campaign_id)
    if results['success']:
        return JsonResponse({0: "success"})
    else:
        return JsonResponse({0: "failure"})


def voter_stop_opposing_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_stop_opposing_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    position_entered_manager = PositionEnteredManager()
    results = position_entered_manager.toggle_off_voter_oppose_for_candidate_campaign(voter_id, candidate_campaign_id)
    if results['success']:
        return JsonResponse({0: "success"})
    else:
        return JsonResponse({0: "failure"})


def voter_asking_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_asking_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    logger.debug("voter_asking_candidate_campaign_view NOT BUILT YET, voter_id: {voter_id}".format(
        voter_id=voter_id
    ))

    return JsonResponse({0: "not working yet - needs to be built"})


def voter_stop_asking_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_stop_asking_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    logger.debug("voter_stop_asking_candidate_campaign_view NOT BUILT YET, voter_id: {voter_id}".format(
        voter_id=voter_id
    ))

    return JsonResponse({0: "not working yet - needs to be built"})


def voter_stance_for_candidate_campaign_view(request, candidate_campaign_id):
    logger.debug("voter_stance_for_candidate_campaign_view {candidate_campaign_id}".format(
        candidate_campaign_id=candidate_campaign_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    position_entered_manager = PositionEnteredManager()
    results = position_entered_manager.retrieve_voter_candidate_campaign_position(voter_id, candidate_campaign_id)
    if results['position_found']:
        if results['is_support']:
            return JsonResponse({0: "support"})
        elif results['is_oppose']:
            return JsonResponse({0: "oppose"})
        elif results['is_no_stance']:
            return JsonResponse({0: "no_stance"})
        elif results['is_information_only']:
            return JsonResponse({0: "information_only"})
        elif results['is_still_deciding']:
            return JsonResponse({0: "still_deciding"})
    return JsonResponse({0: "failure"})


def voter_stance_for_contest_measure_view(request, contest_measure_id):
    logger.debug("voter_stance_for_candidate_campaign_view {candidate_campaign_id}".format(
        contest_measure_id=contest_measure_id
    ))
    voter_api_device_id = get_voter_api_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    logger.debug("voter_stance_for_contest_measure_view NOT BUILT YET, voter_id: {voter_id}".format(
        voter_id=voter_id
    ))

    return JsonResponse({0: "not working yet - needs to be built"})
