# measure/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from office.models import ContestOfficeManager
from config.base import get_environment_variable
from django.http import HttpResponse
from exception.models import handle_exception, handle_record_not_found_exception, handle_record_not_saved_exception
import json
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
# CANDIDATE_CAMPAIGNS_URL = get_environment_variable("CANDIDATE_CAMPAIGNS_URL")


def measure_retrieve_for_api(office_id, office_we_vote_id):  # TODO DALE This method is still a work in progress
    """
    Used by the api
    :param office_id:
    :param office_we_vote_id:
    :return:
    """
    # NOTE: Office retrieve is independent of *who* wants to see the data. Office retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItemsFromGoogleCivic does

    if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
        json_data = {
            'status': status,
            'success': False,
            'office_id': office_id,
            'office_we_vote_id': office_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_manager = ContestOfficeManager()
    if positive_value_exists(office_id):
        results = office_manager.retrieve_contest_office_from_id()
        success = results['success']
        status = results['status']
    elif positive_value_exists(office_we_vote_id):
        results = office_manager.retrieve_contest_office_from_id()
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status': status,
            'success': False,
            'office_id': office_id,
            'office_we_vote_id': office_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_office = results['contest_office']
        json_data = {
            'status':                   status,
            'success':                  True,
            'office_id':                contest_office.id,
            'office_we_vote_id':        contest_office.we_vote_id,
            'google_civic_election_id': contest_office.google_civic_election_id,
            'office_name':              contest_office.office_name,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
