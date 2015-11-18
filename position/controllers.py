# position/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_record_not_found_exception, handle_record_not_saved_exception
from organization.models import OrganizationManager
from position.models import PositionEnteredManager
import json
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POSITIONS_URL = get_environment_variable("POSITIONS_URL")


# We retrieve from only one of the two possible variables
def position_retrieve_for_api(position_id, position_we_vote_id, voter_device_id):
    position_id = convert_to_int(position_id)
    position_we_vote_id = position_we_vote_id.strip()

    # TODO for certain positions (voter positions), we need to restrict the retrieve based on voter_device_id / voter_id

    we_vote_id = position_we_vote_id.strip()
    if not positive_value_exists(position_id) and not positive_value_exists(position_we_vote_id):
        json_data = {
            'status':                   "POSITION_RETRIEVE_BOTH_IDS_MISSING",
            'success':                  False,
            'position_id':              position_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_label':        '',
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
    candidate_campaign_id = 0
    contest_measure_id = 0
    position_voter_id = 0
    results = position_manager.retrieve_position(position_id, position_we_vote_id, organization_id, position_voter_id,
                                                 candidate_campaign_id, contest_measure_id)
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
            'ballot_item_label':        position.ballot_item_label,
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
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   results['status'],
            'success':                  False,
            'position_id':              position_id,
            'position_we_vote_id':      we_vote_id,
            'ballot_item_label':        '',
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


def position_save_for_api(
        voter_device_id, position_id, position_we_vote_id,
        organization_we_vote_id,
        public_figure_we_vote_id,
        voter_we_vote_id,
        google_civic_election_id,
        ballot_item_label,
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
            'ballot_item_label':        ballot_item_label,
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
            'ballot_item_label':        ballot_item_label,
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
        ballot_item_label=ballot_item_label,
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
            'ballot_item_label':        position.ballot_item_label,
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
            'last_updated':             '',
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
            'ballot_item_label':        '',
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


def positions_import_from_sample_file(request=None, load_from_uri=False):
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

