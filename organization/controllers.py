# organization/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_record_not_found_exception, \
    handle_record_not_saved_exception
from follow.models import FollowOrganizationManager, FOLLOW_IGNORE, FOLLOWING, STOP_FOLLOWING
import json
from organization.models import Organization
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ORGANIZATIONS_URL = get_environment_variable("ORGANIZATIONS_URL")


def organization_follow_all(voter_device_id, organization_id, follow_kind=FOLLOWING):
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_id = convert_to_int(organization_id)
    if not positive_value_exists(organization_id):
        json_data = {
            'status': 'VALID_ORGANIZATION_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if follow_kind == FOLLOWING:
        follow_organization_manager = FollowOrganizationManager()
        results = follow_organization_manager.toggle_on_voter_following_organization(voter_id, organization_id)
        if results['success']:
            status = 'FOLLOWING'
            success = True
        else:
            status = results['status']
            success = False

    elif follow_kind == FOLLOW_IGNORE:
        follow_organization_manager = FollowOrganizationManager()
        results = follow_organization_manager.toggle_ignore_voter_following_organization(voter_id, organization_id)
        if results['success']:
            status = 'IGNORING'
            success = True
        else:
            status = results['status']
            success = False
    elif follow_kind == STOP_FOLLOWING:
        follow_organization_manager = FollowOrganizationManager()
        results = follow_organization_manager.toggle_off_voter_following_organization(voter_id, organization_id)
        if results['success']:
            status = 'STOPPED_FOLLOWING'
            success = True
        else:
            status = results['status']
            success = False
    else:
        status = 'INCORRECT_FOLLOW_KIND'
        success = False

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'organization_id': organization_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organizations_import_from_sample_file(request=None, load_from_uri=False):  # TODO FINISH BUILDING/TESTING THIS
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # if load_from_uri:
    #     # Request json file from We Vote servers
    #     logger.info("Loading Organizations from We Vote Master servers")
    #     request = requests.get(ORGANIZATIONS_URL, params={
    #         "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    #     })
    #     structured_json = json.loads(request.text)
    # else:
    # Load saved json from local file
    logger.info("Loading organizations from local file")

    with open('organization/import_data/organizations_sample.json') as json_data:
        structured_json = json.load(json_data)

    organizations_saved = 0
    organizations_updated = 0
    organizations_not_processed = 0
    for one_organization in structured_json:
        logger.debug(
            u"we_vote_id: {we_vote_id}, organization_name: {organization_name}, "
            u"organization_website: {organization_website}".format(**one_organization)
        )
        # Make sure we have the minimum required variables
        if not positive_value_exists(one_organization["we_vote_id"]) or \
                not positive_value_exists(one_organization["organization_name"]):
            organizations_not_processed += 1
            continue

        # Check to see if this organization is already being used anywhere
        organization_on_stage_found = False
        try:
            if positive_value_exists(one_organization["we_vote_id"]):
                organization_query = Organization.objects.filter(we_vote_id=one_organization["we_vote_id"])
                if len(organization_query):
                    organization_on_stage = organization_query[0]
                    organization_on_stage_found = True
            elif positive_value_exists(one_organization["organization_name"]):
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
                # messages.add_message(request, messages.INFO, u"Organization updated: {organization_name}".format(
                #     organization_name=one_organization["organization_name"]))
                organizations_updated += 1
            else:
                # Create new
                organization_on_stage = Organization(
                    we_vote_id=one_organization["we_vote_id"],
                    organization_name=one_organization["organization_name"],
                    twitter_handle=one_organization["twitter_handle"],
                    organization_website=one_organization["organization_website"],
                )
                organization_on_stage.save()
                organizations_saved += 1
                # messages.add_message(request, messages.INFO, u"New organization imported: {organization_name}".format(
                #     organization_name=one_organization["organization_name"]))
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            if request is not None:
                messages.add_message(request, messages.ERROR,
                                     "Could not save Organization, we_vote_id: {we_vote_id}, "
                                     "organization_name: {organization_name}, "
                                     "organization_website: {organization_website}".format(
                                         we_vote_id=one_organization["we_vote_id"],
                                         organization_name=one_organization["organization_name"],
                                         organization_website=one_organization["organization_website"],
                                     ))
            organizations_not_processed += 1

    organizations_results = {
        'saved': organizations_saved,
        'updated': organizations_updated,
        'not_processed': organizations_not_processed,
    }
    return organizations_results
