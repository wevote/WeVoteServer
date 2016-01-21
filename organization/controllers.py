# organization/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import OrganizationListManager, OrganizationManager
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_record_not_found_exception, \
    handle_record_not_saved_exception
from follow.models import FollowOrganizationManager, FollowOrganizationList, FOLLOW_IGNORE, FOLLOWING, STOP_FOLLOWING
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


def organizations_followed_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0):
    """
    Return a list of the organizations followed. See also voter_guides_followed_retrieve_for_api, which starts with
    organizations followed, but returns data as a list of voter guides.
    :param voter_device_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = retrieve_organizations_followed(voter_id)
    status = results['status']
    organizations_for_api = []
    if results['organization_list_found']:
        organization_list = results['organization_list']
        number_added_to_list = 0
        for organization in organization_list:
            one_organization = {
                'organization_id': organization.id,
                'organization_we_vote_id': organization.we_vote_id,
                'organization_name':
                    organization.organization_name if positive_value_exists(organization.organization_name) else '',
                'organization_website': organization.organization_website if positive_value_exists(
                    organization.organization_website) else '',
                'organization_twitter_handle':
                    organization.organization_twitter_handle if positive_value_exists(
                        organization.organization_twitter_handle) else '',
                'organization_email':
                    organization.organization_email if positive_value_exists(organization.organization_email) else '',
                'organization_facebook': organization.organization_facebook
                    if positive_value_exists(organization.organization_facebook) else '',
                'organization_photo_url': organization.organization_photo_url()
                    if positive_value_exists(organization.organization_photo_url()) else '',
          }
            organizations_for_api.append(one_organization.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(organizations_for_api):
            status = 'ORGANIZATIONS_FOLLOWED_RETRIEVED'
            success = True
        else:
            status = 'NO_ORGANIZATIONS_FOLLOWED_FOUND'
            success = True
    else:
        success = False

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'organization_list': organizations_for_api,
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
        except Organization.DoesNotExist:
            # No problem that we aren't finding existing organization
            pass
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        try:
            if organization_on_stage_found:
                # Update
                organization_on_stage.we_vote_id = one_organization["we_vote_id"]
                organization_on_stage.organization_name = one_organization["organization_name"]
                organization_on_stage.organization_website = one_organization["organization_website"]
                organization_on_stage.organization_twitter_handle = one_organization["organization_twitter_handle"]
                organization_on_stage.save()
                # messages.add_message(request, messages.INFO, u"Organization updated: {organization_name}".format(
                #     organization_name=one_organization["organization_name"]))
                organizations_updated += 1
            else:
                # Create new
                organization_on_stage = Organization(
                    we_vote_id=one_organization["we_vote_id"],
                    organization_name=one_organization["organization_name"],
                    organization_twitter_handle=one_organization["organization_twitter_handle"],
                    organization_website=one_organization["organization_website"],
                    organization_email=one_organization["organization_email"] if 'organization_email' in
                                                                                 one_organization else '',
                    organization_facebook=one_organization["organization_facebook"] if 'organization_facebook' in
                                                                                       one_organization else '',
                    organization_image=one_organization["organization_image"] if 'organization_image' in
                                                                                 one_organization else '',
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


# We retrieve from only one of the two possible variables
def organization_retrieve_for_api(organization_id, organization_we_vote_id):
    organization_id = convert_to_int(organization_id)

    we_vote_id = organization_we_vote_id.strip()
    if not positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
        json_data = {
            'status': "ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING",
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_name': '',
            'organization_email': '',
            'organization_website': '',
            'organization_twitter_handle': '',
            'organization_facebook': '',
            'organization_photo_url': '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    if results['organization_found']:
        organization = results['organization']
        json_data = {
            'success': True,
            'status': results['status'],
            'organization_id': organization.id,
            'organization_we_vote_id': organization.we_vote_id,
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_website': organization.organization_website if positive_value_exists(
                organization.organization_website) else '',
            'organization_twitter_handle':
                organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
            'organization_photo_url': organization.organization_photo_url()
                if positive_value_exists(organization.organization_photo_url()) else '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status': results['status'],
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': we_vote_id,
            'organization_name': '',
            'organization_email': '',
            'organization_website': '',
            'organization_twitter_handle': '',
            'organization_facebook': '',
            'organization_photo_url': '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_save_for_api(voter_device_id, organization_id, organization_we_vote_id, organization_name,
                              organization_email, organization_website,
                              organization_twitter_handle, organization_facebook, organization_image):
    organization_id = convert_to_int(organization_id)
    organization_we_vote_id = organization_we_vote_id.strip()

    existing_unique_identifier_found = positive_value_exists(organization_id) \
        or positive_value_exists(organization_we_vote_id)
    new_unique_identifier_found = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website)
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have one of these: twitter_handle or website, AND organization_name
    required_variables_for_new_entry = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website) and positive_value_exists(organization_name)
    if not unique_identifier_found:
        results = {
            'status': "ORGANIZATION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'new_organization_created': False,
            'organization_name': organization_name,
            'organization_email': organization_email,
            'organization_website': organization_website,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_facebook': organization_facebook,
            'organization_photo_url': organization_image,
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status': "NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING",
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'new_organization_created': False,
            'organization_name': organization_name,
            'organization_email': organization_email,
            'organization_website': organization_website,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_facebook': organization_facebook,
            'organization_photo_url': organization_image,
        }
        return results

    organization_manager = OrganizationManager()
    save_results = organization_manager.update_or_create_organization(
        organization_id=organization_id, we_vote_id=organization_we_vote_id,
        organization_website_search=organization_website, organization_twitter_search=organization_twitter_handle,
        organization_name=organization_name, organization_website=organization_website,
        organization_twitter_handle=organization_twitter_handle, organization_email=organization_email,
        organization_facebook=organization_facebook, organization_image=organization_image)

    if save_results['success']:
        organization = save_results['organization']
        results = {
            'success':                      save_results['success'],
            'status':                       save_results['status'],
            'voter_device_id':              voter_device_id,
            'organization_id':              organization.id,
            'organization_we_vote_id':      organization.we_vote_id,
            'new_organization_created':     save_results['new_organization_created'],
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_website':
                organization.organization_website if positive_value_exists(organization.organization_website) else '',
            'organization_twitter_handle':
                organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
            'organization_photo_url': organization.organization_photo_url()
                if positive_value_exists(organization.organization_photo_url()) else '',
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'organization_id':          organization_id,
            'organization_we_vote_id':  organization_we_vote_id,
            'new_organization_created': save_results['new_organization_created'],
            'organization_name':        organization_name,
            'organization_email':       organization_email,
            'organization_website':     organization_website,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_facebook':    organization_facebook,
            'organization_photo_url':   organization_image,
        }
        return results


def organization_search_for_api(organization_name, organization_twitter_handle, organization_website,
                                organization_email):
    organization_name = organization_name.strip()
    organization_twitter_handle = organization_twitter_handle.strip()
    organization_website = organization_website.strip()
    organization_email = organization_email.strip()

    # We need at least one term to search for
    if not positive_value_exists(organization_name) \
            and not positive_value_exists(organization_twitter_handle)\
            and not positive_value_exists(organization_website)\
            and not positive_value_exists(organization_email):
        json_data = {
            'status':               "ORGANIZATION_SEARCH_ALL_TERMS_MISSING",
            'success':              False,
            'organization_name':    organization_name,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_website': organization_website,
            'organization_email':   organization_email,
            'organizations_list':   [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_list_manager = OrganizationListManager()
    results = organization_list_manager.organization_search_find_any_possibilities(
        organization_name, organization_twitter_handle, organization_website, organization_email)

    if results['organizations_found']:
        organizations_list = results['organizations_list']
        json_data = {
            'status': results['status'],
            'success': True,
            'organization_name':    organization_name,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_website': organization_website,
            'organization_email':   organization_email,
            'organizations_list':   organizations_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':               results['status'],
            'success':              False,
            'organization_name':    organization_name,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_website': organization_website,
            'organization_email':   organization_email,
            'organizations_list':   [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_organizations_followed(voter_id):
    organization_list_found = False
    organization_list = []

    follow_organization_list_manager = FollowOrganizationList()
    organization_ids_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    organization_list_manager = OrganizationListManager()
    results = organization_list_manager.retrieve_organizations_by_id_list(organization_ids_followed_by_voter)
    if results['organization_list_found']:
        organization_list = results['organization_list']
        success = True
        if len(organization_list):
            organization_list_found = True
            status = 'SUCCESSFUL_RETRIEVE_OF_ORGANIZATIONS_FOLLOWED'
        else:
            status = 'ORGANIZATIONS_FOLLOWED_NOT_FOUND'
    else:
        status = results['status']
        success = results['success']

    results = {
        'success':                      success,
        'status':                       status,
        'organization_list_found':      organization_list_found,
        'organization_list':            organization_list,
    }
    return results
