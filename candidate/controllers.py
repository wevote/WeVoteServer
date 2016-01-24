# candidate/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CandidateCampaignList, CandidateCampaignManager
from ballot.models import CANDIDATE
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_exception
from import_export_vote_smart.controllers import retrieve_and_match_candidate_from_vote_smart, \
    retrieve_candidate_photo_from_vote_smart
from import_export_vote_smart.models import VoteSmartCandidateManager
import json
from office.models import ContestOfficeManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
CANDIDATE_CAMPAIGNS_URL = get_environment_variable("CANDIDATE_CAMPAIGNS_URL")


def candidates_import_from_sample_file(request=None, load_from_uri=False):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # if load_from_uri:
    #     # Request json file from We Vote servers
    #     messages.add_message(request, messages.INFO, "Loading CandidateCampaign IDs from We Vote Master servers")
    #     request = requests.get(CANDIDATE_CAMPAIGNS_URL, params={
    #         "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    #     })
    #     structured_json = json.loads(request.text)
    # else:
    # Load saved json from local file

    # messages.add_message(request, messages.INFO, "Loading CandidateCampaigns from local file")

    with open("candidate/import_data/candidate_campaigns_sample.json") as json_data:
        structured_json = json.load(json_data)

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
        contest_office_id = contest_office_manager.fetch_contest_office_id_from_contest_office_we_vote_id(
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
            results = candidate_campaign_manager.update_or_create_candidate_campaign(
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


def candidate_retrieve_for_api(candidate_id, candidate_we_vote_id):
    """
    Used by the api
    :param candidate_id:
    :param candidate_we_vote_id:
    :return:
    """
    # NOTE: Candidates retrieve is independent of *who* wants to see the data. Candidates retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItems does

    if not positive_value_exists(candidate_id) and not positive_value_exists(candidate_we_vote_id):
        status = 'VALID_CANDIDATE_ID_AND_CANDIDATE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      CANDIDATE,
            'id':                       candidate_id,
            'we_vote_id':               candidate_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    candidate_manager = CandidateCampaignManager()
    if positive_value_exists(candidate_id):
        results = candidate_manager.retrieve_candidate_campaign_from_id(candidate_id)
        success = results['success']
        status = results['status']
    elif positive_value_exists(candidate_we_vote_id):
        results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        success = results['success']
        status = results['status']
    else:
        status = 'VALID_CANDIDATE_ID_AND_CANDIDATE_WE_VOTE_ID_MISSING_2'  # It should be impossible to reach this
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      CANDIDATE,
            'id':                       candidate_id,
            'we_vote_id':               candidate_we_vote_id,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if success:
        candidate_campaign = results['candidate_campaign']
        json_data = {
            'status':                       status,
            'success':                      True,
            'kind_of_ballot_item':          CANDIDATE,
            'id':                           candidate_campaign.id,
            'we_vote_id':                   candidate_campaign.we_vote_id,
            'ballot_item_display_name':     candidate_campaign.candidate_name,
            'candidate_photo_url':          candidate_campaign.fetch_photo_url(),
            'order_on_ballot':              candidate_campaign.order_on_ballot,
            'google_civic_election_id':     candidate_campaign.google_civic_election_id,
            'maplight_id':                  candidate_campaign.maplight_id,
            'contest_office_id':            candidate_campaign.contest_office_id,
            'contest_office_we_vote_id':    candidate_campaign.contest_office_we_vote_id,
            'politician_id':                candidate_campaign.politician_id,
            'politician_we_vote_id':        candidate_campaign.politician_we_vote_id,
            # 'google_civic_candidate_name': candidate_campaign.google_civic_candidate_name,
            'party':                        candidate_campaign.maplight_id,
            'ocd_division_id':              candidate_campaign.ocd_division_id,
            'state_code':                   candidate_campaign.state_code,
            'candidate_url':                candidate_campaign.candidate_url,
            'facebook_url':                 candidate_campaign.facebook_url,
            'twitter_url':                  candidate_campaign.twitter_url,
            'twitter_handle':               candidate_campaign.fetch_twitter_handle(),
            'google_plus_url':              candidate_campaign.google_plus_url,
            'youtube_url':                  candidate_campaign.youtube_url,
            'candidate_email':              candidate_campaign.candidate_email,
            'candidate_phone':              candidate_campaign.candidate_phone,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      CANDIDATE,
            'id':                       candidate_id,
            'we_vote_id':               candidate_we_vote_id,
            'google_civic_election_id': 0,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def candidates_retrieve_for_api(office_id, office_we_vote_id):
    """
    Used by the api
    :param office_id:
    :param office_we_vote_id:
    :return:
    """
    # NOTE: Candidates retrieve is independent of *who* wants to see the data. Candidates retrieve never triggers
    #  a ballot data lookup from Google Civic, like voterBallotItems does

    if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
        status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': 0,
            'candidate_list':           [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    candidate_list = []
    candidates_to_display = []
    google_civic_election_id = 0
    try:
        candidate_list_object = CandidateCampaignList()
        results = candidate_list_object.retrieve_all_candidates_for_office(office_id, office_we_vote_id)
        success = results['success']
        status = results['status']
        candidate_list = results['candidate_list']
    except Exception as e:
        status = 'FAILED candidates_retrieve. ' \
                 '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        # Reset office_we_vote_id and office_id so we are sure that it matches what we pull from the database
        office_id = 0
        office_we_vote_id = ''
        for candidate in candidate_list:
            one_candidate = {
                'id':                           candidate.id,
                'we_vote_id':                   candidate.we_vote_id,
                'ballot_item_display_name':     candidate.candidate_name,
                'candidate_photo_url':          candidate.fetch_photo_url(),
                'order_on_ballot':              candidate.order_on_ballot,
            }
            candidates_to_display.append(one_candidate.copy())
            # Capture the office_we_vote_id and google_civic_election_id so we can return
            if not positive_value_exists(office_id) and candidate.contest_office_id:
                office_id = candidate.contest_office_id
            if not positive_value_exists(office_we_vote_id) and candidate.contest_office_we_vote_id:
                office_we_vote_id = candidate.contest_office_we_vote_id
            if not positive_value_exists(google_civic_election_id) and candidate.google_civic_election_id:
                google_civic_election_id = candidate.google_civic_election_id

        if len(candidates_to_display):
            status = 'CANDIDATES_RETRIEVED'
        else:
            status = 'NO_CANDIDATES_RETRIEVED'

        json_data = {
            'status':                   status,
            'success':                  True,
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'candidate_list':           candidates_to_display,
        }
    else:
        json_data = {
            'status':                   status,
            'success':                  False,
            'office_id':                office_id,
            'office_we_vote_id':        office_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'candidate_list':           [],
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_candidate_photos(we_vote_candidate, force_retrieve=False):
    # Has this candidate already been linked to a Vote Smart candidate?
    candidate_retrieve_results = retrieve_and_match_candidate_from_vote_smart(we_vote_candidate, force_retrieve)

    if positive_value_exists(candidate_retrieve_results['vote_smart_candidate_id']):
        # Bring out the object that now has vote_smart_id attached
        we_vote_candidate = candidate_retrieve_results['we_vote_candidate']
        # Reach out to Vote Smart and retrieve photo URL
        photo_retrieve_results = retrieve_candidate_photo_from_vote_smart(we_vote_candidate)
        status = photo_retrieve_results['status']
        success = photo_retrieve_results['success']
    else:
        status = candidate_retrieve_results['status'] + ' '
        status += 'RETRIEVE_CANDIDATE_PHOTOS_NO_CANDIDATE_MATCH'
        success = False

    results = {
        'success':  success,
        'status':   status
    }

    return results
