# position/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered, PositionEnteredManager, PositionListManager, ANY_STANCE, NO_STANCE
from ballot.models import OFFICE, CANDIDATE, POLITICIAN, MEASURE
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_record_not_found_exception, handle_record_not_saved_exception
from follow.models import FollowOrganizationList
from organization.models import OrganizationManager
import json
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
from voter_guide.models import ORGANIZATION, PUBLIC_FIGURE, VOTER, UNKNOWN_VOTER_GUIDE
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POSITIONS_URL = get_environment_variable("POSITIONS_URL")


# We retrieve from only one of the two possible variables
def position_retrieve_for_api(position_id, position_we_vote_id, voter_device_id):
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    # TODO for certain positions (voter positions), we need to restrict the retrieve based on voter_device_id / voter_id
    if voter_device_id:
        pass

    we_vote_id = position_we_vote_id.strip()
    if not positive_value_exists(position_id) and not positive_value_exists(position_we_vote_id):
        json_data = {
            'status':                   "POSITION_RETRIEVE_BOTH_IDS_MISSING",
            'success':                  False,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionEnteredManager()
    organization_id = 0
    contest_office_id = 0
    candidate_campaign_id = 0
    contest_measure_id = 0
    position_voter_id = 0
    results = position_manager.retrieve_position(position_id, position_we_vote_id, organization_id, position_voter_id,
                                                 contest_office_id, candidate_campaign_id, contest_measure_id)
    # results = {
    #     'error_result':             error_result,
    #     'DoesNotExist':             exception_does_not_exist,
    #     'MultipleObjectsReturned':  exception_multiple_object_returned,
    #     'position_found':           True if position_id > 0 else False,
    #     'position_id':              position_id,
    #     'position':                 position_on_stage,
    #     'is_support':               position_on_stage.is_support(),
    #     'is_oppose':                position_on_stage.is_oppose(),
    #     'is_no_stance':             position_on_stage.is_no_stance(),
    #     'is_information_only':      position_on_stage.is_information_only(),
    #     'is_still_deciding':        position_on_stage.is_still_deciding(),
    # }

    if results['position_found']:
        position = results['position']
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'is_support':               results['is_support'],
            'is_oppose':                results['is_oppose'],
            'is_information_only':      results['is_information_only'],
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   results['status'],
            'success':                  results['success'],
            'position_id':              position_id,
            'position_we_vote_id':      we_vote_id,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   NO_STANCE,
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_save_for_api(
        voter_device_id, position_id, position_we_vote_id,
        organization_we_vote_id,
        public_figure_we_vote_id,
        voter_we_vote_id,
        google_civic_election_id,
        ballot_item_display_name,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        stance,
        statement_text,
        statement_html,
        more_info_url
        ):
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    existing_unique_identifier_found = positive_value_exists(position_id) \
        or positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        results = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results

    position_manager = PositionEnteredManager()
    save_results = position_manager.update_or_create_position(
        position_id=position_id,
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
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    if save_results['success']:
        position = save_results['position']
        results = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'new_position_created':     save_results['new_position_created'],
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'is_support':               position.is_support(),
            'is_oppose':                position.is_oppose(),
            'is_information_only':      position.is_information_only(),
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results


def position_list_for_ballot_item_for_api(voter_device_id,  # positionListForBallotItem
                                          office_id, candidate_id, measure_id,
                                          stance_we_are_looking_for=ANY_STANCE,
                                          show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the position identifiers from orgs, friends and public figures the voter follows
    This list of information is used to retrieve the detailed information
    """
    position_manager = PositionEnteredManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'count':            0,
            'kind_of_ballot_item': "UNKNOWN",
            'ballot_item_id':   0,
            'position_list':    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status': "VALID_VOTER_ID_MISSING ",
            'success': False,
            'count':            0,
            'kind_of_ballot_item': "UNKNOWN",
            'ballot_item_id':   0,
            'position_list':    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    if positive_value_exists(candidate_id):
        candidate_we_vote_id = ''
        all_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                candidate_id, candidate_we_vote_id, stance_we_are_looking_for)
        kind_of_ballot_item = CANDIDATE
        ballot_item_id = candidate_id
    elif positive_value_exists(measure_id):
        measure_we_vote_id = ''
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                measure_id, measure_we_vote_id, stance_we_are_looking_for)
        kind_of_ballot_item = MEASURE
        ballot_item_id = measure_id
    elif positive_value_exists(office_id):
        office_we_vote_id = ''
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                office_id, office_we_vote_id, stance_we_are_looking_for)
        kind_of_ballot_item = OFFICE
        ballot_item_id = measure_id
    else:
        position_list = []
        json_data = {
            'status':           'POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID',
            'success':          False,
            'count':            0,
            'kind_of_ballot_item': "UNKNOWN",
            'ballot_item_id':   0,
            'position_list':    position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    if show_positions_this_voter_follows:
        position_objects = position_list_manager.calculate_positions_followed_by_voter(
            voter_id, all_positions_list, organizations_followed_by_voter)
        positions_count = len(position_objects)
        status = 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_FOLLOWED'
        success = True
    else:
        position_objects = position_list_manager.calculate_positions_not_followed_by_voter(
            all_positions_list, organizations_followed_by_voter)
        positions_count = len(position_objects)
        status = 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED'
        success = True

    position_list = []
    for one_position in position_objects:
        # Whose position is it?
        if positive_value_exists(one_position.organization_we_vote_id):
            speaker_type = ORGANIZATION
            speaker_id = one_position.organization_id
            speaker_we_vote_id = one_position.organization_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https):
                one_position = position_manager.refresh_cached_position_info(one_position)
        elif positive_value_exists(one_position.voter_id):
            speaker_type = VOTER
            speaker_id = one_position.voter_id
            speaker_we_vote_id = one_position.voter_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name):
                one_position = position_manager.refresh_cached_position_info(one_position)
        elif positive_value_exists(one_position.public_figure_we_vote_id):
            speaker_type = PUBLIC_FIGURE
            speaker_id = one_position.public_figure_id
            speaker_we_vote_id = one_position.public_figure_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https):
                one_position = position_manager.refresh_cached_position_info(one_position)
        else:
            speaker_type = UNKNOWN_VOTER_GUIDE
            speaker_id = None
            speaker_we_vote_id = None
            one_position_success = False

        if one_position_success:
            one_position_dict_for_api = {
                'position_id':          one_position.id,
                'position_we_vote_id':  one_position.we_vote_id,
                'ballot_item_display_name': one_position.ballot_item_display_name,
                'speaker_display_name': one_position.speaker_display_name,
                'speaker_image_url_https': one_position.speaker_image_url_https,
                'speaker_type':         speaker_type,
                'speaker_id':           speaker_id,
                'speaker_we_vote_id':   speaker_we_vote_id,
                'is_support':           one_position.is_support(),
                'is_oppose':            one_position.is_oppose(),
                'last_updated':         one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    json_data = {
        'status':           status,
        'success':          success,
        'count':            positions_count,
        'kind_of_ballot_item': kind_of_ballot_item,
        'ballot_item_id':   ballot_item_id,
        'position_list':    position_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_import_from_sample_file(request=None):  # , load_from_uri=False
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # if load_from_uri:
    #     # Request json file from We Vote servers
    #     messages.add_message(request, messages.INFO, "Loading positions from We Vote Master servers")
    #     request = requests.get(POSITIONS_URL, params={
    #         "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    #     })
    #     structured_json = json.loads(request.text)
    # else:
    # Load saved json from local file
    with open("position/import_data/positions_sample.json") as json_data:
        structured_json = json.load(json_data)

    positions_saved = 0
    positions_updated = 0
    positions_not_processed = 0
    for one_position in structured_json:
        # Make sure we have the minimum required variables
        if not positive_value_exists(one_position["we_vote_id"]) \
                or not positive_value_exists(one_position["organization_we_vote_id"])\
                or not positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            positions_not_processed += 1
            continue

        # Check to see if this position is already being used anywhere
        position_on_stage_found = False
        try:
            if len(one_position["we_vote_id"]) > 0:
                position_query = PositionEntered.objects.filter(we_vote_id=one_position["we_vote_id"])
                if len(position_query):
                    position_on_stage = position_query[0]
                    position_on_stage_found = True
        except PositionEntered.DoesNotExist as e:
            handle_record_not_found_exception(e, logger=logger)
            pass
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        # We need to look up the local organization_id based on the newly saved we_vote_id
        organization_manager = OrganizationManager()
        organization_id = organization_manager.fetch_organization_id(one_position["organization_we_vote_id"])

        # We need to look up the local candidate_campaign_id
        candidate_campaign_manager = CandidateCampaignManager()
        candidate_campaign_id = candidate_campaign_manager.fetch_candidate_campaign_id_from_we_vote_id(
            one_position["candidate_campaign_we_vote_id"])

        # Find the google_civic_candidate_name so we have a backup way to link position if the we_vote_id is lost
        google_civic_candidate_name = one_position["google_civic_candidate_name"] if \
            "google_civic_candidate_name" in one_position else ''
        if not positive_value_exists(google_civic_candidate_name):
            google_civic_candidate_name = candidate_campaign_manager.fetch_google_civic_candidate_name_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])

        # TODO We need to look up contest_measure_id
        contest_measure_id = 0

        try:
            if position_on_stage_found:
                # Update
                position_on_stage.we_vote_id = one_position["we_vote_id"]
                position_on_stage.organization_id = organization_id
                position_on_stage.organization_we_vote_id = one_position["organization_we_vote_id"]
                position_on_stage.candidate_campaign_id = candidate_campaign_id
                position_on_stage.candidate_campaign_we_vote_id = one_position["candidate_campaign_we_vote_id"]
                position_on_stage.google_civic_candidate_name = google_civic_candidate_name
                position_on_stage.contest_measure_id = contest_measure_id
                position_on_stage.date_entered = one_position["date_entered"]
                position_on_stage.google_civic_election_id = one_position["google_civic_election_id"]
                position_on_stage.stance = one_position["stance"]
                position_on_stage.more_info_url = one_position["more_info_url"]
                position_on_stage.statement_text = one_position["statement_text"]
                position_on_stage.statement_html = one_position["statement_html"]
                position_on_stage.save()
                positions_updated += 1
                # messages.add_message(request, messages.INFO, u"Position updated: {we_vote_id}".format(
                #     we_vote_id=one_position["we_vote_id"]))
            else:
                # Create new
                position_on_stage = PositionEntered(
                    we_vote_id=one_position["we_vote_id"],
                    organization_id=organization_id,
                    organization_we_vote_id=one_position["organization_we_vote_id"],
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=one_position["candidate_campaign_we_vote_id"],
                    google_civic_candidate_name=google_civic_candidate_name,
                    contest_measure_id=contest_measure_id,
                    date_entered=one_position["date_entered"],
                    google_civic_election_id=one_position["google_civic_election_id"],
                    stance=one_position["stance"],
                    more_info_url=one_position["more_info_url"],
                    statement_text=one_position["statement_text"],
                    statement_html=one_position["statement_html"],
                )
                position_on_stage.save()
                positions_saved += 1
                # messages.add_message(request, messages.INFO, u"New position imported: {we_vote_id}".format(
                #     we_vote_id=one_position["we_vote_id"]))
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            if request is not None:
                messages.add_message(request, messages.ERROR,
                                     u"Could not save/update position, "
                                     u"position_on_stage_found: {position_on_stage_found}, "
                                     u"we_vote_id: {we_vote_id}, "
                                     u"organization_we_vote_id: {organization_we_vote_id}, "
                                     u"candidate_campaign_we_vote_id: {candidate_campaign_we_vote_id}".format(
                                         position_on_stage_found=position_on_stage_found,
                                         we_vote_id=one_position["we_vote_id"],
                                         organization_we_vote_id=one_position["organization_we_vote_id"],
                                         candidate_campaign_we_vote_id=one_position["candidate_campaign_we_vote_id"],
                                     ))
            positions_not_processed += 1

    positions_results = {
        'saved': positions_saved,
        'updated': positions_updated,
        'not_processed': positions_not_processed,
    }
    return positions_results


# We retrieve the position for this voter for one ballot item. Could just be the stance, but for now we are
# retrieving the entire position
def voter_position_retrieve_for_api(voter_device_id, office_we_vote_id, candidate_we_vote_id, measure_we_vote_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_we_vote_id = office_we_vote_id.strip()
    candidate_we_vote_id = candidate_we_vote_id.strip()
    measure_we_vote_id = measure_we_vote_id.strip()

    if not positive_value_exists(office_we_vote_id) and \
            not positive_value_exists(candidate_we_vote_id) and \
            not positive_value_exists(measure_we_vote_id):
        json_data = {
            'status':                   "POSITION_RETRIEVE_MISSING_AT_LEAST_ONE_BALLOT_ITEM_ID",
            'success':                  False,
            'position_id':              0,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionEnteredManager()

    if positive_value_exists(office_we_vote_id):
        results = position_manager.retrieve_voter_contest_office_position_with_we_vote_id(
            voter_id, office_we_vote_id)

    elif positive_value_exists(candidate_we_vote_id):
        results = position_manager.retrieve_voter_candidate_campaign_position_with_we_vote_id(
            voter_id, candidate_we_vote_id)

    elif positive_value_exists(measure_we_vote_id):
        results = position_manager.retrieve_voter_contest_measure_position_with_we_vote_id(
            voter_id, measure_we_vote_id)

    # retrieve_position results
    # results = {
    #     'error_result':             error_result,
    #     'DoesNotExist':             exception_does_not_exist,
    #     'MultipleObjectsReturned':  exception_multiple_object_returned,
    #     'position_found':           True if position_id > 0 else False,
    #     'position_id':              position_id,
    #     'position':                 position_on_stage,
    #     'is_support':               position_on_stage.is_support(),
    #     'is_oppose':                position_on_stage.is_oppose(),
    #     'is_no_stance':             position_on_stage.is_no_stance(),
    #     'is_information_only':      position_on_stage.is_information_only(),
    #     'is_still_deciding':        position_on_stage.is_still_deciding(),
    # }

    if results['position_found']:
        position = results['position']
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'is_support':               results['is_support'],
            'is_oppose':                results['is_oppose'],
            'is_information_only':      results['is_information_only'],
            'google_civic_election_id': position.google_civic_election_id,
            'office_we_vote_id':        position.contest_office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   results['status'],
            'success':                  False,
            'position_id':              0,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_comment_save_for_api(
        voter_device_id, position_id, position_we_vote_id,
        google_civic_election_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        statement_text,
        statement_html
        ):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data

    voter = voter_results['voter']
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    existing_unique_identifier_found = positive_value_exists(position_id) \
        or positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(voter_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(voter_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        json_data = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        json_data = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data

    position_manager = PositionEnteredManager()
    save_results = position_manager.update_or_create_position(
        position_id=position_id,
        position_we_vote_id=position_we_vote_id,
        voter_we_vote_id=voter.we_vote_id,
        google_civic_election_id=google_civic_election_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html,
    )

    if save_results['success']:
        position = save_results['position']
        json_data = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position.id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'new_position_created':     save_results['new_position_created'],
            'is_support':               position.is_support(),
            'is_oppose':                position.is_oppose(),
            'is_information_only':      position.is_information_only(),
            'google_civic_election_id': position.google_civic_election_id,
            'office_we_vote_id':        position.contest_office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'last_updated':             position.last_updated(),
        }
        return json_data
    else:
        json_data = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return json_data
