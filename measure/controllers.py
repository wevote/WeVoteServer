# measure/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestMeasureManager
from ballot.models import MEASURE
from config.base import get_environment_variable
from django.http import HttpResponse
import json
import requests
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")


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
            'ballot_item_display_name': contest_measure.measure_title,
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


def measures_import_from_master_server():
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    logger.info("Loading Candidates from We Vote Master servers")
    request = requests.get(MEASURES_SYNC_URL, params={
        "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    })
    structured_json = json.loads(request.text)

    return measures_import_from_structured_json(request, structured_json)


def measures_import_from_structured_json(request, structured_json):
    candidate_campaign_manager = CandidateCampaignManager()
    candidates_saved = 0
    candidates_updated = 0
    candidates_not_processed = 0
    for candidate in structured_json:
        candidate_name = candidate['candidate_name'] if 'candidate_name' in candidate else ''
        we_vote_id = candidate['we_vote_id'] if 'we_vote_id' in candidate else ''
        google_civic_election_id = \
            candidate['google_civic_election_id'] if 'google_civic_election_id' in candidate else ''
        ocd_division_id = candidate['ocd_division_id'] if 'ocd_division_id' in candidate else ''
        contest_office_we_vote_id = \
            candidate['contest_office_we_vote_id'] if 'contest_office_we_vote_id' in candidate else ''

        # This routine imports from another We Vote server, so a contest_office_id doesn't come from import
        # Look it up for this local database. If we don't find it, then we know the contest_office hasn't been imported
        # from another server yet, so we fail out.
        contest_office_manager = ContestOfficeManager()
        contest_office_id = contest_office_manager.fetch_contest_office_id_from_we_vote_id(
            contest_office_we_vote_id)
        if positive_value_exists(candidate_name) and positive_value_exists(google_civic_election_id) \
                and positive_value_exists(we_vote_id) and positive_value_exists(contest_office_id):
            proceed_to_update_or_create = True
        # elif positive_value_exists(candidate_name) and positive_value_exists(google_civic_election_id) \
        #         and positive_value_exists(we_vote_id) and positive_value_exists(ocd_division_id) \
        #         and positive_value_exists(contest_office_we_vote_id):
        #     proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False
        if proceed_to_update_or_create:
            updated_candidate_campaign_values = {
                # Values we search against
                'google_civic_election_id': google_civic_election_id,
                'ocd_division_id': ocd_division_id,
                'contest_office_we_vote_id': contest_office_we_vote_id,
                'candidate_name': candidate_name,
                # The rest of the values
                'we_vote_id': we_vote_id,
                'maplight_id': candidate['maplight_id'] if 'maplight_id' in candidate else None,
                'contest_office_id': contest_office_id,
                'politician_we_vote_id':
                    candidate['politician_we_vote_id'] if 'politician_we_vote_id' in candidate else '',
                'state_code': candidate['state_code'] if 'state_code' in candidate else '',
                'party': candidate['party'] if 'party' in candidate else '',
                'order_on_ballot': candidate['order_on_ballot'] if 'order_on_ballot' in candidate else 0,
                'candidate_url': candidate['candidate_url'] if 'candidate_url' in candidate else '',
                'photo_url': candidate['photo_url'] if 'photo_url' in candidate else '',
                'photo_url_from_maplight':
                    candidate['photo_url_from_maplight'] if 'photo_url_from_maplight' in candidate else '',
                'facebook_url': candidate['facebook_url'] if 'facebook_url' in candidate else '',
                'twitter_url': candidate['twitter_url'] if 'twitter_url' in candidate else '',
                'google_plus_url': candidate['google_plus_url'] if 'google_plus_url' in candidate else '',
                'youtube_url': candidate['youtube_url'] if 'youtube_url' in candidate else '',
                'google_civic_candidate_name':
                    candidate['google_civic_candidate_name'] if 'google_civic_candidate_name' in candidate else '',
                'candidate_email': candidate['candidate_email'] if 'candidate_email' in candidate else '',
                'candidate_phone': candidate['candidate_phone'] if 'candidate_phone' in candidate else '',
            }
            results = candidate_campaign_manager.update_or_create_candidate_campaign(  # TO DO: UPDATE THIS TO MEASURE
                we_vote_id, google_civic_election_id, ocd_division_id,
                contest_office_id, contest_office_we_vote_id,
                candidate_name, updated_candidate_campaign_values)
        else:
            candidates_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create'
            }

        if results['success']:
            if results['new_candidate_created']:
                candidates_saved += 1
            else:
                candidates_updated += 1
        else:
            candidates_not_processed += 1
            if candidates_not_processed < 5 and request is not None:
                messages.add_message(request, messages.ERROR,
                                     results['status'] + "candidate_name: {candidate_name}"
                                                         ", google_civic_election_id: {google_civic_election_id}"
                                                         ", we_vote_id: {we_vote_id}"
                                                         ", contest_office_id: {contest_office_id}"
                                                         ", contest_office_we_vote_id: {contest_office_we_vote_id}"
                                                         "".format(
                                         candidate_name=candidate_name,
                                         google_civic_election_id=google_civic_election_id,
                                         we_vote_id=we_vote_id,
                                         contest_office_id=contest_office_id,
                                         contest_office_we_vote_id=contest_office_we_vote_id,
                                     ))
    candidates_results = {
        'saved': candidates_saved,
        'updated': candidates_updated,
        'not_processed': candidates_not_processed,
    }
    return candidates_results
