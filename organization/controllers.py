# organization/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import BallotItem
from candidate.models import CandidateCampaign, CandidateCampaignManager
from django.contrib import messages
from election.models import Election
from exception.models import handle_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
import json
from office.models import ContestOffice
from organization.models import Organization, OrganizationManager
from politician.models import Politician
from position.models import PositionEntered
import requests
from config.base import get_environment_variable
import wevote_functions.admin
from wevote_functions.models import value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ORGANIZATIONS_URL = get_environment_variable("ORGANIZATIONS_URL")
ORGANIZATIONS_JSON_FILE = get_environment_variable("ORGANIZATIONS_JSON_FILE")
CANDIDATE_CAMPAIGNS_URL = get_environment_variable("CANDIDATE_CAMPAIGNS_URL")
CANDIDATE_CAMPAIGNS_JSON_FILE = get_environment_variable("CANDIDATE_CAMPAIGNS_JSON_FILE")
POSITIONS_URL = get_environment_variable("POSITIONS_URL")
POSITIONS_JSON_FILE = get_environment_variable("POSITIONS_JSON_FILE")


def import_we_vote_organizations_from_json(request, load_from_uri=False):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    if load_from_uri:
        # Request json file from We Vote servers
        logger.info("Loading Organizations from We Vote Master servers")
        request = requests.get(ORGANIZATIONS_URL, params={
            "key": WE_VOTE_API_KEY,  # This comes from an environment variable
        })
        structured_json = json.loads(request.text)
    else:
        # Load saved json from local file
        logger.info("Loading organizations from local file")

        with open(ORGANIZATIONS_JSON_FILE) as json_data:
            structured_json = json.load(json_data)

    for one_organization in structured_json:
        logger.debug(
            u"we_vote_id: {we_vote_id}, organization_name: {organization_name}, "
            u"organization_website: {organization_website}".format(**one_organization)
        )
        # Make sure we have the minimum required variables
        if len(one_organization["we_vote_id"]) == 0 or len(one_organization["organization_name"]) == 0:
            continue

        # Check to see if this organization is already being used anywhere
        organization_on_stage_found = False
        try:
            if len(one_organization["we_vote_id"]) > 0:
                organization_query = Organization.objects.filter(we_vote_id=one_organization["we_vote_id"])
                if len(organization_query):
                    organization_on_stage = organization_query[0]
                    organization_on_stage_found = True
            elif len(one_organization["organization_name"]) > 0:
                organization_query = Organization.objects.filter(
                    organization_name=one_organization["organization_name"])
                if len(organization_query):
                    organization_on_stage = organization_query[0]
                    organization_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        try:
            if organization_on_stage_found:
                # Update
                organization_on_stage.we_vote_id = one_organization["we_vote_id"]
                organization_on_stage.organization_name = one_organization["organization_name"]
                organization_on_stage.organization_website = one_organization["organization_website"]
                organization_on_stage.twitter_handle = one_organization["twitter_handle"]
                organization_on_stage.save()
                messages.add_message(request, messages.INFO, u"Organization updated: {organization_name}".format(
                    organization_name=one_organization["organization_name"]))
            else:
                # Create new
                organization_on_stage = Organization(
                    we_vote_id=one_organization["we_vote_id"],
                    organization_name=one_organization["organization_name"],
                    twitter_handle=one_organization["twitter_handle"],
                    organization_website=one_organization["organization_website"],
                )
                organization_on_stage.save()
                messages.add_message(request, messages.INFO, u"New organization imported: {organization_name}".format(
                    organization_name=one_organization["organization_name"]))
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR,
                                 "Could not save Organization, we_vote_id: {we_vote_id}, "
                                 "organization_name: {organization_name}, "
                                 "organization_website: {organization_website}".format(
                                     we_vote_id=one_organization["we_vote_id"],
                                     organization_name=one_organization["organization_name"],
                                     organization_website=one_organization["organization_website"],
                                 ))

    return
