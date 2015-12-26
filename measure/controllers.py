# measure/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestMeasureManager
from ballot.models import MEASURE
from config.base import get_environment_variable
from django.http import HttpResponse
import json
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
# CANDIDATE_CAMPAIGNS_URL = get_environment_variable("CANDIDATE_CAMPAIGNS_URL")


def measure_retrieve_for_api(measure_id, measure_we_vote_id):
    """
    Used by the api
    :param measure_id:
    :param measure_we_vote_id:
    :return:
    """
    # NOTE: Office retrieve is independent of *who* wants to see the data. Office retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItemsFromGoogleCivic does

    if not positive_value_exists(measure_id) and not positive_value_exists(measure_we_vote_id):
        status = 'VALID_MEASURE_ID_AND_MEASURE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      MEASURE,
            'id':                       measure_id,
            'we_vote_id':               measure_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    measure_manager = ContestMeasureManager()
    if positive_value_exists(measure_id):
        results = measure_manager.retrieve_contest_measure_from_id(measure_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(measure_we_vote_id):
        results = measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_MEASURE_ID_AND_MEASURE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      MEASURE,
            'id':                       measure_id,
            'we_vote_id':               measure_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_measure = results['contest_measure']
        json_data = {
            'status':                   status,
            'success':                  True,
            'kind_of_ballot_item':      MEASURE,
            'id':                       contest_measure.id,
            'we_vote_id':               contest_measure.we_vote_id,
            'google_civic_election_id': contest_measure.google_civic_election_id,
            'ballot_item_label':        contest_measure.measure_title,
            'measure_subtitle':         contest_measure.measure_subtitle,
            'maplight_id':              contest_measure.maplight_id,
            'measure_text':             contest_measure.measure_text,
            'measure_url':              contest_measure.measure_url,
            'ocd_division_id':          contest_measure.ocd_division_id,
            'district_name':            contest_measure.district_name,
            'state_code':               contest_measure.state_code,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      MEASURE,
            'id':                       measure_id,
            'we_vote_id':               measure_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
