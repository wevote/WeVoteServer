# position/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from django.contrib import messages
from exception.models import handle_record_not_found_exception, handle_record_not_saved_exception
from organization.models import OrganizationManager
import json
import wevote_functions.admin
from wevote_functions.models import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POSITIONS_URL = get_environment_variable("POSITIONS_URL")


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

