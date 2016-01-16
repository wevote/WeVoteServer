# geoip/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import OFFICE
from django.http import HttpResponse
import json
from office.models import ContestOfficeManager
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_location_retrieve_from_ip_for_api(ip_address):
    """
    Used by the api
    :param ip_address:
    :return:
    """
    # NOTE: Office retrieve is independent of *who* wants to see the data. Office retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItemsFromGoogleCivic does

    if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_manager = ContestOfficeManager()
    if positive_value_exists(office_id):
        results = office_manager.retrieve_contest_office_from_id(office_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(office_we_vote_id):
        results = office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        contest_office = results['contest_office']
        json_data = {
            'status':                   status,
            'success':                  True,
            'kind_of_ballot_item':      OFFICE,
            'id':                       contest_office.id,
            'we_vote_id':               contest_office.we_vote_id,
            'google_civic_election_id': contest_office.google_civic_election_id,
            'ballot_item_display_name': contest_office.office_name,
            'ocd_division_id':          contest_office.ocd_division_id,
            'maplight_id':              contest_office.maplight_id,
            'ballotpedia_id':           contest_office.ballotpedia_id,
            'wikipedia_id':             contest_office.wikipedia_id,
            'number_voting_for':        contest_office.number_voting_for,
            'number_elected':           contest_office.number_elected,
            'state_code':               contest_office.state_code,
            'primary_party':            contest_office.primary_party,
            'district_name':            contest_office.district_name,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      OFFICE,
            'id':                       office_id,
            'we_vote_id':               office_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
