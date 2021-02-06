# bookmark/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BookmarkItemList, BookmarkItemManager
from ballot.models import CANDIDATE, MEASURE, OFFICE
from candidate.models import CandidateManager
from django.http import HttpResponse
import json
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_bookmark_off_save_for_api(voter_device_id,
                                office_id, office_we_vote_id,
                                candidate_id, candidate_we_vote_id,
                                measure_id, measure_we_vote_id):
    # Get voter_id from the voter_device_id so we can know who is doing the bookmarking
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    bookmark_item_manager = BookmarkItemManager()
    if positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        contest_office_manager = ContestOfficeManager()
        # Since we can take in either office_id or office_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(office_id):
            office_we_vote_id = contest_office_manager.fetch_contest_office_we_vote_id_from_id(office_id)
        elif positive_value_exists(office_we_vote_id):
            office_id = contest_office_manager.fetch_contest_office_id_from_we_vote_id(office_we_vote_id)

        results = bookmark_item_manager.toggle_off_voter_bookmarked_office(voter_id, office_id)
        status = "BOOKMARK_OFF_OFFICE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(office_id),
            'ballot_item_we_vote_id':   office_we_vote_id,
            'kind_of_ballot_item':      OFFICE,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        results = bookmark_item_manager.toggle_off_voter_bookmarked_candidate(voter_id, candidate_id)
        status = "BOOKMARK_OFF_CANDIDATE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        results = bookmark_item_manager.toggle_off_voter_bookmarked_measure(voter_id, measure_id)
        status = "BOOKMARK_OFF_MEASURE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_SAVE_OFF-OFFICE_ID_AND_CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_bookmark_on_save_for_api(voter_device_id,
                               office_id, office_we_vote_id,
                               candidate_id, candidate_we_vote_id,
                               measure_id, measure_we_vote_id):
    # Get voter_id from the voter_device_id so we can know who is doing the bookmarking
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VALID_VOTER_ID_MISSING",
            'success': False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    bookmark_item_manager = BookmarkItemManager()
    if positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        contest_office_manager = ContestOfficeManager()
        # Since we can take in either office_id or office_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(office_id):
            office_we_vote_id = contest_office_manager.fetch_contest_office_we_vote_id_from_id(office_id)
        elif positive_value_exists(office_we_vote_id):
            office_id = contest_office_manager.fetch_contest_office_id_from_we_vote_id(office_we_vote_id)

        results = bookmark_item_manager.toggle_on_voter_bookmarked_office(voter_id, office_id)
        status = "BOOKMARK_ON_OFFICE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(office_id),
            'ballot_item_we_vote_id':   office_we_vote_id,
            'kind_of_ballot_item':      OFFICE,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        results = bookmark_item_manager.toggle_on_voter_bookmarked_candidate(voter_id, candidate_id)
        status = "BOOKMARK_ON_CANDIDATE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        results = bookmark_item_manager.toggle_on_voter_bookmarked_measure(voter_id, measure_id)
        status = "BOOKMARK_ON_MEASURE " + results['status']
        success = results['success']

        json_data = {
            'status':                   status,
            'success':                  success,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_SAVE_ON-OFFICE_ID_AND_CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False

    json_data = {
        'status': status,
        'success': success,
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_bookmark_status_retrieve_for_api(voter_device_id,
                                       office_id, office_we_vote_id,
                                       candidate_id, candidate_we_vote_id,
                                       measure_id, measure_we_vote_id):
    # Get voter_id from the voter_device_id so we can know who is doing the bookmarking
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':                   'VALID_VOTER_DEVICE_ID_MISSING',
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'is_bookmarked':               False,
            'office_id':                convert_to_int(office_id),
            'candidate_id':             convert_to_int(candidate_id),
            'measure_id':               convert_to_int(measure_id),
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VALID_VOTER_ID_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'is_bookmarked':               False,
            'office_id':                convert_to_int(office_id),
            'candidate_id':             convert_to_int(candidate_id),
            'measure_id':               convert_to_int(measure_id),
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    bookmark_item_manager = BookmarkItemManager()
    if positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        contest_office_manager = ContestOfficeManager()
        # Since we can take in either office_id or office_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(office_id):
            office_we_vote_id = contest_office_manager.fetch_contest_office_we_vote_id_from_id(office_id)
        elif positive_value_exists(office_we_vote_id):
            office_id = contest_office_manager.fetch_contest_office_id_from_we_vote_id(office_we_vote_id)

        # Zero out the unused values
        bookmark_item_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        results = bookmark_item_manager.retrieve_bookmark_item(bookmark_item_id, voter_id, office_id,
                                                       candidate_campaign_id, contest_measure_id)
        status = results['status']
        success = results['success']
        is_bookmarked = results['is_bookmarked']

        json_data = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'is_bookmarked':               is_bookmarked,
            'ballot_item_id':           convert_to_int(office_id),
            'ballot_item_we_vote_id':   office_we_vote_id,
            'kind_of_ballot_item':      OFFICE,
            'office_id':                convert_to_int(office_id),
            'candidate_id':             convert_to_int(candidate_id),
            'measure_id':               convert_to_int(measure_id),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        # Since we can take in either candidate_id or candidate_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(candidate_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)
        elif positive_value_exists(candidate_we_vote_id):
            candidate_id = candidate_manager.fetch_candidate_id_from_we_vote_id(candidate_we_vote_id)

        # Zero out the unused values
        bookmark_item_id = 0
        contest_office_id = 0
        contest_measure_id = 0
        results = bookmark_item_manager.retrieve_bookmark_item(bookmark_item_id, voter_id, contest_office_id, candidate_id,
                                                       contest_measure_id)
        status = results['status']
        success = results['success']
        is_bookmarked = results['is_bookmarked']

        json_data = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'is_bookmarked':               is_bookmarked,
            'ballot_item_id':           convert_to_int(candidate_id),
            'ballot_item_we_vote_id':   candidate_we_vote_id,
            'kind_of_ballot_item':      CANDIDATE,
            'office_id':                convert_to_int(office_id),
            'candidate_id':             convert_to_int(candidate_id),
            'measure_id':               convert_to_int(measure_id),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        # Since we can take in either measure_id or measure_we_vote_id, we need to retrieve the value we don't have
        if positive_value_exists(measure_id):
            measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(measure_id)
        elif positive_value_exists(measure_we_vote_id):
            measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)

        # Zero out the unused values
        bookmark_item_id = 0
        contest_office_id = 0
        candidate_campaign_id = 0
        results = bookmark_item_manager.retrieve_bookmark_item(bookmark_item_id, voter_id, contest_office_id, candidate_campaign_id,
                                                       measure_id)
        status = results['status']
        success = results['success']
        is_bookmarked = results['is_bookmarked']

        json_data = {
            'status':                   status,
            'success':                  success,
            'voter_device_id':          voter_device_id,
            'is_bookmarked':               is_bookmarked,
            'ballot_item_id':           convert_to_int(measure_id),
            'ballot_item_we_vote_id':   measure_we_vote_id,
            'kind_of_ballot_item':      MEASURE,
            'office_id':                convert_to_int(office_id),
            'candidate_id':             convert_to_int(candidate_id),
            'measure_id':               convert_to_int(measure_id),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        status = 'UNABLE_TO_SAVE-OFFICE_ID_AND_CANDIDATE_ID_AND_MEASURE_ID_MISSING'
        success = False
        is_bookmarked = False

    json_data = {
        'status':                   status,
        'success':                  success,
        'voter_device_id':          voter_device_id,
        'is_bookmarked':               is_bookmarked,
        'office_id':                convert_to_int(office_id),
        'candidate_id':             convert_to_int(candidate_id),
        'measure_id':               convert_to_int(measure_id),
        'ballot_item_id':           0,
        'ballot_item_we_vote_id':   '',
        'kind_of_ballot_item':      '',
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_all_bookmarks_status_retrieve_for_api(voter_device_id):
    # Get voter_id from the voter_device_id so we can know whose bookmarks to retrieve
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':       "VALID_VOTER_DEVICE_ID_MISSING",
            'success':      False,
            'bookmark_list':    [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':       "VALID_VOTER_ID_MISSING",
            'success':      False,
            'bookmark_list':    [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    bookmark_item_list_manager = BookmarkItemList()
    results = bookmark_item_list_manager.retrieve_bookmark_item_list_for_voter(voter_id)
    status = results['status']
    success = results['success']

    bookmark_list = []
    if success:
        bookmark_item_list = results['bookmark_item_list']
        for bookmark_item in bookmark_item_list:
            # Create a list of bookmark information needed by API
            one_bookmark = {
                'ballot_item_we_vote_id':   bookmark_item.ballot_item_we_vote_id(),
                'bookmark_on':                  bookmark_item.is_bookmarked(),
            }
            bookmark_list.append(one_bookmark)

    json_data = {
        'status':       status,
        'success':      success,
        'bookmark_list':    bookmark_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')
