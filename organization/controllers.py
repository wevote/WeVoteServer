# organization/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Organization, OrganizationListManager, OrganizationManager, \
    CORPORATION, GROUP, INDIVIDUAL, NEWS_ORGANIZATION, NONPROFIT, NONPROFIT_501C3, NONPROFIT_501C4, \
    POLITICAL_ACTION_COMMITTEE, ORGANIZATION, PUBLIC_FIGURE, UNKNOWN, VOTER, ORGANIZATION_TYPE_CHOICES
from analytics.models import ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_FOLLOW_IGNORE, \
    ACTION_ORGANIZATION_STOP_FOLLOWING, AnalyticsManager
from config.base import get_environment_variable
from django.http import HttpResponse
from exception.models import handle_record_not_found_exception
from follow.controllers import move_organization_followers_to_another_organization
from follow.models import FollowOrganizationManager, FollowOrganizationList, FOLLOW_IGNORE, FOLLOWING, STOP_FOLLOWING
from image.controllers import retrieve_all_images_for_one_organization
from import_export_facebook.models import FacebookManager
import json
from position.controllers import move_positions_to_another_organization, \
    update_position_for_friends_details_from_voter, \
    update_position_entered_details_from_organization
from position.models import PositionListManager
import robot_detection
from twitter.models import TwitterUserManager
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager, Voter
from voter_guide.models import VoterGuide, VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists, \
    process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
ORGANIZATIONS_SYNC_URL = get_environment_variable("ORGANIZATIONS_SYNC_URL")


def organization_retrieve_tweets(organization_we_vote_id, number_to_retrieve):
    # For one organization, retrieve X Tweets, and capture all #Hashtags used.
    # Sample code: Search for tweepy http://tweepy.readthedocs.io/en/v3.5.0/
    pass


def organization_analyze_tweets(organization_we_vote_id):
    # For one organization, retrieve X Tweets, and capture all #Hashtags used.
    # Loop through Tweets and create OrganizationLinkToHashtag and OrganizationLinkToWordOrPhrase
    pass


def move_organization_data_to_another_organization(from_organization_we_vote_id, to_organization_we_vote_id):
    status = ""
    success = False
    from_organization = Organization()
    to_organization = Organization()
    data_transfer_complete = False

    if not positive_value_exists(from_organization_we_vote_id) \
            or not positive_value_exists(to_organization_we_vote_id):
        results = {
            'status': 'MOVE_ORGANIZATION_DATA_INCOMING_VARIABLES_MISSING ',
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'data_transfer_complete': False,
        }
        return results

    organization_manager = OrganizationManager()
    from_organization_results = organization_manager.retrieve_organization_from_we_vote_id(from_organization_we_vote_id)
    if from_organization_results['organization_found']:
        from_organization = from_organization_results['organization']
    else:
        results = {
            'status': 'MOVE_ORGANIZATION_DATA_COULD_NOT_RETRIEVE_FROM_ORGANIZATION ',
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'data_transfer_complete': False,
        }
        return results

    to_organization_results = organization_manager.retrieve_organization_from_we_vote_id(to_organization_we_vote_id)
    if to_organization_results['organization_found']:
        to_organization = to_organization_results['organization']
    else:
        results = {
            'status': 'MOVE_ORGANIZATION_DATA_COULD_NOT_RETRIEVE_FROM_ORGANIZATION ',
            'success': False,
            'from_organization': from_organization,
            'to_organization': to_organization,
            'data_transfer_complete': False,
        }
        return results

    # If here we know that we have both from_organization and to_organization
    save_to_organization = False
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_website'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_email'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_contact_name'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_facebook'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_image'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'state_served_code'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'vote_smart_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_description'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_address'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_city'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_state'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_zip'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_phone1'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_phone2'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_fax'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'facebook_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'facebook_email'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'fb_username'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'facebook_profile_image_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_user_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_twitter_handle'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_name'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_location'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_followers_count'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_profile_image_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization,
                                           'twitter_profile_background_image_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_profile_banner_url_https'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'twitter_description'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_page_id'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_page_title'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_thumbnail_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_thumbnail_width'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_thumbnail_height'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'wikipedia_photo_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'ballotpedia_page_title'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'ballotpedia_photo_url'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_type'):
        save_to_organization = True
    if transfer_to_organization_if_missing(from_organization, to_organization, 'organization_endorsements_api_url'):
        save_to_organization = True

    if save_to_organization:
        try:
            to_organization.save()
            data_transfer_complete = True
        except Exception as e:
            # Fail silently
            pass
    else:
        data_transfer_complete = True

    results = {
        'status': status,
        'success': success,
        'from_organization': from_organization,
        'to_organization': to_organization,
        'data_transfer_complete': data_transfer_complete,
    }
    return results


def move_organization_to_another_complete(from_organization_id, from_organization_we_vote_id,
                                          to_organization_id, to_organization_we_vote_id,
                                          to_voter_id, to_voter_we_vote_id):
    status = ""
    success = True

    # Make sure we have both from_organization values
    organization_manager = OrganizationManager()
    if positive_value_exists(from_organization_id) and not positive_value_exists(from_organization_we_vote_id):
        from_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(from_organization_id)
    elif positive_value_exists(from_organization_we_vote_id) and not positive_value_exists(from_organization_id):
        from_organization_id = organization_manager.fetch_organization_id(from_organization_we_vote_id)

    # Make sure we have both to_organization values
    if positive_value_exists(to_organization_id) and not positive_value_exists(to_organization_we_vote_id):
        to_organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(to_organization_id)
    elif positive_value_exists(to_organization_we_vote_id) and not positive_value_exists(to_organization_id):
        to_organization_id = organization_manager.fetch_organization_id(to_organization_we_vote_id)

    # Make sure we have both to_voter values
    voter_manager = VoterManager()
    if positive_value_exists(to_voter_id) and not positive_value_exists(to_voter_we_vote_id):
        to_voter_we_vote_id = voter_manager.fetch_we_vote_id_from_local_id(to_voter_id)
    elif positive_value_exists(to_voter_we_vote_id) and not positive_value_exists(to_voter_id):
        to_voter_id = voter_manager.fetch_local_id_from_we_vote_id(to_voter_we_vote_id)

    # If anyone is following the old voter's organization, move those followers to the new voter's organization
    move_organization_followers_results = move_organization_followers_to_another_organization(
        from_organization_id, from_organization_we_vote_id,
        to_organization_id, to_organization_we_vote_id)
    status += " " + move_organization_followers_results['status']

    # Transfer positions from "from" organization to the "to" organization
    move_positions_to_another_org_results = move_positions_to_another_organization(
        from_organization_id, from_organization_we_vote_id,
        to_organization_id, to_organization_we_vote_id,
        to_voter_id, to_voter_we_vote_id)
    status += " " + move_positions_to_another_org_results['status']

    # There might be some useful information in the from_voter's organization that needs to be moved
    move_organization_results = move_organization_data_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += " " + move_organization_results['status']

    # Finally, delete the from_voter's organization
    if move_organization_results['data_transfer_complete']:
        from_organization = move_organization_results['from_organization']
        try:
            from_organization.delete()
        except Exception as e:
            status += "UNABLE_TO_DELETE_FROM_ORGANIZATION "

    # We need to make sure to update voter.linked_organization_we_vote_id outside of this routine

    results = {
        'status': status,
        'success': success,
    }
    return results


def transfer_to_organization_if_missing(from_organization, to_organization, field):
    save_to_organization = False
    if positive_value_exists(getattr(from_organization, field)):
        if not positive_value_exists(getattr(to_organization, field)):
            setattr(to_organization, field, getattr(from_organization, field))
            save_to_organization = True

    return save_to_organization


def organization_follow_or_unfollow_or_ignore(voter_device_id, organization_id, organization_we_vote_id,
                                              follow_kind=FOLLOWING,
                                              organization_follow_based_on_issue=None,
                                              user_agent_string='', user_agent_object=None):
    if organization_follow_based_on_issue is None:
        organization_follow_based_on_issue = False

    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': "",
        }
        return json_data

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': "",
        }
        return json_data

    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id)
    if not results['voter_found']:
        json_data = {
            'status': 'VOTER_NOT_FOUND',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': "",
        }
        return json_data

    voter = results['voter']
    voter_we_vote_id = voter.we_vote_id
    is_signed_in = voter.is_signed_in()
    voter_linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    organization_id = convert_to_int(organization_id)
    if not positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
        json_data = {
            'status': 'VALID_ORGANIZATION_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_follow_based_on_issue': organization_follow_based_on_issue,
            'voter_linked_organization_we_vote_id': voter_linked_organization_we_vote_id,
        }
        return json_data
    is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
    analytics_manager = AnalyticsManager()
    follow_organization_manager = FollowOrganizationManager()
    if follow_kind == FOLLOWING:
        results = follow_organization_manager.toggle_on_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status = 'FOLLOWING'
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id
            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_FOLLOW, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status = results['status']
            success = False

    elif follow_kind == FOLLOW_IGNORE:
        results = follow_organization_manager.toggle_ignore_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status = 'IGNORING'
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id
            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_FOLLOW_IGNORE, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status = results['status']
            success = False
    elif follow_kind == STOP_FOLLOWING:
        results = follow_organization_manager.toggle_off_voter_following_organization(
            voter_id, organization_id, organization_we_vote_id, voter_linked_organization_we_vote_id)
        if results['follow_organization_found']:
            status = 'STOPPED_FOLLOWING'
            success = True
            state_code = ''
            follow_organization = results['follow_organization']
            organization_id = follow_organization.organization_id
            organization_we_vote_id = follow_organization.organization_we_vote_id
            analytics_results = analytics_manager.save_action(
                ACTION_ORGANIZATION_STOP_FOLLOWING, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id, organization_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet)
        else:
            status = results['status']
            success = False
    else:
        status = 'INCORRECT_FOLLOW_KIND'
        success = False

    if positive_value_exists(voter_id):
        number_of_organizations_followed = \
            follow_organization_manager.fetch_number_of_organizations_followed(voter_id)

        voter_manager = VoterManager()
        voter_manager.update_organizations_interface_status(voter_we_vote_id, number_of_organizations_followed)

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'organization_id': organization_id,
        'organization_we_vote_id': organization_we_vote_id,
        'organization_follow_based_on_issue': organization_follow_based_on_issue,
        'voter_linked_organization_we_vote_id': voter_linked_organization_we_vote_id,
    }
    return json_data


def organizations_followed_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0,
                                            auto_followed_from_twitter_suggestion=False):
    """
    organizationsFollowedRetrieve Return a list of the organizations followed. See also voter_guides_followed_retrieve_for_api,
    which starts with organizations followed, but returns data as a list of voter guides.
    :param voter_device_id:
    :param maximum_number_to_retrieve:
    :param auto_followed_from_twitter_suggestion:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'organization_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = retrieve_organizations_followed(voter_id, auto_followed_from_twitter_suggestion)
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
                'twitter_followers_count':
                    organization.twitter_followers_count if positive_value_exists(
                        organization.twitter_followers_count) else 0,
                'twitter_description':
                    organization.organization_description
                    if positive_value_exists(organization.organization_description) else '',
                'organization_email':
                    organization.organization_email if positive_value_exists(organization.organization_email) else '',
                'organization_facebook': organization.organization_facebook
                    if positive_value_exists(organization.organization_facebook) else '',
                'organization_photo_url_large': organization.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(organization.we_vote_hosted_profile_image_url_large)
                    else organization.organization_photo_url(),
                'organization_photo_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                'organization_photo_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
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
        'auto_followed_from_twitter_suggestion': auto_followed_from_twitter_suggestion
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organizations_import_from_sample_file():  # TODO FINISH BUILDING/TESTING THIS
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    logger.info("Loading organizations from local file")

    with open('organization/import_data/organizations_sample.json') as json_data:
        structured_json = json.load(json_data)

    request = None
    return organizations_import_from_structured_json(structured_json)


def organizations_import_from_master_server(request, state_code=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    import_results, structured_json = process_request_from_master(
        request, "Loading Organizations from We Vote Master servers",
        ORGANIZATIONS_SYNC_URL, {
            "key":               WE_VOTE_API_KEY,  # This comes from an environment variable
            "format":            'json',
            "state_served_code": state_code,
        }
    )

    if import_results['success']:
        results = filter_organizations_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        import_results = organizations_import_from_structured_json(filtered_structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_organizations_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove candidates that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    organization_list_manager = OrganizationListManager()
    for one_organization in structured_json:
        organization_name = one_organization['organization_name'] if 'organization_name' in one_organization else ''
        we_vote_id = one_organization['we_vote_id'] if 'we_vote_id' in one_organization else ''
        organization_twitter_handle = one_organization['organization_twitter_handle'] \
            if 'organization_twitter_handle' in one_organization else ''
        vote_smart_id = one_organization['vote_smart_id'] if 'vote_smart_id' in one_organization else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = organization_list_manager.retrieve_possible_duplicate_organizations(
            organization_name, organization_twitter_handle, vote_smart_id, we_vote_id_from_master)

        if results['organization_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_organization)

    organizations_results = {
        'success':              True,
        'status':               "FILTER_ORGANIZATIONS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return organizations_results


def organizations_import_from_structured_json(structured_json):
    organizations_saved = 0
    organizations_updated = 0
    organizations_not_processed = 0
    for one_organization in structured_json:
        # We have already removed duplicate organizations

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
        except Organization.DoesNotExist:
            # No problem that we aren't finding existing organization
            pass
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            # We want to skip to the next org
            continue

        try:
            we_vote_id = one_organization["we_vote_id"]
            organization_name = one_organization["organization_name"] \
                if 'organization_name' in one_organization else False
            organization_website = one_organization["organization_website"] \
                if 'organization_website' in one_organization else False
            organization_email = one_organization["organization_email"] \
                if 'organization_email' in one_organization else False
            organization_contact_name = one_organization["organization_contact_name"] \
                if 'organization_contact_name' in one_organization else False
            organization_facebook = one_organization["organization_facebook"] \
                if 'organization_facebook' in one_organization else False
            organization_image = one_organization["organization_image"] \
                if 'organization_image' in one_organization else False
            state_served_code = one_organization["state_served_code"] \
                if 'state_served_code' in one_organization else False
            vote_smart_id = one_organization["vote_smart_id"] \
                if 'vote_smart_id' in one_organization else False
            organization_description = one_organization["organization_description"] \
                if 'organization_description' in one_organization else False
            organization_address = one_organization["organization_address"] \
                if 'organization_address' in one_organization else False
            organization_city = one_organization["organization_city"] \
                if 'organization_city' in one_organization else False
            organization_state = one_organization["organization_state"] \
                if 'organization_state' in one_organization else False
            organization_zip = one_organization["organization_zip"] \
                if 'organization_zip' in one_organization else False
            organization_phone1 = one_organization["organization_phone1"] \
                if 'organization_phone1' in one_organization else False
            organization_phone2 = one_organization["organization_phone2"] \
                if 'organization_phone2' in one_organization else False
            organization_fax = one_organization["organization_fax"] \
                if 'organization_fax' in one_organization else False
            twitter_user_id = one_organization["twitter_user_id"] \
                if 'twitter_user_id' in one_organization else False
            organization_twitter_handle = one_organization["organization_twitter_handle"] \
                if 'organization_twitter_handle' in one_organization else False
            twitter_name = one_organization["twitter_name"] \
                if 'twitter_name' in one_organization else False
            twitter_location = one_organization["twitter_location"] \
                if 'twitter_location' in one_organization else False
            twitter_followers_count = one_organization["twitter_followers_count"] \
                if 'twitter_followers_count' in one_organization else False
            twitter_profile_image_url_https = one_organization["twitter_profile_image_url_https"] \
                if 'twitter_profile_image_url_https' in one_organization else False
            twitter_profile_background_image_url_https = \
                one_organization["twitter_profile_background_image_url_https"] \
                if 'twitter_profile_background_image_url_https' in one_organization else False
            twitter_profile_banner_url_https = one_organization["twitter_profile_banner_url_https"] \
                if 'twitter_profile_banner_url_https' in one_organization else False
            twitter_description = one_organization["twitter_description"] \
                if 'twitter_description' in one_organization else False
            wikipedia_page_id = one_organization["wikipedia_page_id"] \
                if 'wikipedia_page_id' in one_organization else False
            wikipedia_page_title = one_organization["wikipedia_page_title"] \
                if 'wikipedia_page_title' in one_organization else False
            wikipedia_thumbnail_url = one_organization["wikipedia_thumbnail_url"] \
                if 'wikipedia_thumbnail_url' in one_organization else False
            wikipedia_thumbnail_width = one_organization["wikipedia_thumbnail_width"] \
                if 'wikipedia_thumbnail_width' in one_organization else False
            wikipedia_thumbnail_height = one_organization["wikipedia_thumbnail_height"] \
                if 'wikipedia_thumbnail_height' in one_organization else False
            wikipedia_photo_url = one_organization["wikipedia_photo_url"] \
                if 'wikipedia_photo_url' in one_organization else False
            ballotpedia_page_title = one_organization["ballotpedia_page_title"] \
                if 'ballotpedia_page_title' in one_organization else False
            ballotpedia_photo_url = one_organization["ballotpedia_photo_url"] \
                if 'ballotpedia_photo_url' in one_organization else False
            organization_type = one_organization["organization_type"] \
                if 'organization_type' in one_organization else False

            if organization_on_stage_found:
                # Update existing organization in the database
                if we_vote_id is not False:
                    organization_on_stage.we_vote_id = we_vote_id
                if organization_name is not False:
                    organization_on_stage.organization_name = organization_name
            else:
                # Create new
                organization_on_stage = Organization(
                    we_vote_id=one_organization["we_vote_id"],
                    organization_name=one_organization["organization_name"],
                )

            # Now save all of the fields in common to updating an existing entry vs. creating a new entry
            if organization_website is not False:
                organization_on_stage.organization_website = organization_website
            if organization_email is not False:
                organization_on_stage.organization_email = organization_email
            if organization_contact_name is not False:
                organization_on_stage.organization_contact_name = organization_contact_name
            if organization_facebook is not False:
                organization_on_stage.organization_facebook = organization_facebook
            if organization_image is not False:
                organization_on_stage.organization_image = organization_image
            if state_served_code is not False:
                organization_on_stage.state_served_code = state_served_code
            if vote_smart_id is not False:
                organization_on_stage.vote_smart_id = vote_smart_id
            if organization_description is not False:
                organization_on_stage.organization_description = organization_description
            if organization_address is not False:
                organization_on_stage.organization_address = organization_address
            if organization_city is not False:
                organization_on_stage.organization_city = organization_city
            if organization_state is not False:
                organization_on_stage.organization_state = organization_state
            if organization_zip is not False:
                organization_on_stage.organization_zip = organization_zip
            if organization_phone1 is not False:
                organization_on_stage.organization_phone1 = organization_phone1
            if organization_phone2 is not False:
                organization_on_stage.organization_phone2 = organization_phone2
            if organization_fax is not False:
                organization_on_stage.organization_fax = organization_fax
            if twitter_user_id is not False:
                organization_on_stage.twitter_user_id = twitter_user_id
            if organization_twitter_handle is not False:
                organization_on_stage.organization_twitter_handle = organization_twitter_handle
            if twitter_name is not False:
                organization_on_stage.twitter_name = twitter_name
            if twitter_location is not False:
                organization_on_stage.twitter_location = twitter_location
            if twitter_followers_count is not False:
                organization_on_stage.twitter_followers_count = twitter_followers_count
            if twitter_profile_image_url_https is not False:
                organization_on_stage.twitter_profile_image_url_https = twitter_profile_image_url_https
            if twitter_profile_background_image_url_https is not False:
                organization_on_stage.twitter_profile_background_image_url_https = \
                    twitter_profile_background_image_url_https
            if twitter_profile_banner_url_https is not False:
                organization_on_stage.twitter_profile_banner_url_https = twitter_profile_banner_url_https
            if twitter_description is not False:
                organization_on_stage.twitter_description = twitter_description
            if wikipedia_page_id is not False:
                organization_on_stage.wikipedia_page_id = wikipedia_page_id
            if wikipedia_page_title is not False:
                organization_on_stage.wikipedia_page_title = wikipedia_page_title
            if wikipedia_thumbnail_url is not False:
                organization_on_stage.wikipedia_thumbnail_url = wikipedia_thumbnail_url
            if wikipedia_thumbnail_width is not False:
                organization_on_stage.wikipedia_thumbnail_width = wikipedia_thumbnail_width
            if wikipedia_thumbnail_height is not False:
                organization_on_stage.wikipedia_thumbnail_height = wikipedia_thumbnail_height
            if wikipedia_photo_url is not False:
                organization_on_stage.wikipedia_photo_url = wikipedia_photo_url
            if ballotpedia_page_title is not False:
                organization_on_stage.ballotpedia_page_title = ballotpedia_page_title
            if ballotpedia_photo_url is not False:
                organization_on_stage.ballotpedia_photo_url = ballotpedia_photo_url
            if organization_type is not False:
                organization_on_stage.organization_type = organization_type

            organization_on_stage.save()
            if organization_on_stage_found:
                organizations_updated += 1
            else:
                organizations_saved += 1
        except Exception as e:
            organizations_not_processed += 1

    organizations_results = {
        'success': True,
        'status': "ORGANIZATION_IMPORT_PROCESS_COMPLETE",
        'saved': organizations_saved,
        'updated': organizations_updated,
        'not_processed': organizations_not_processed,
    }
    return organizations_results


def organization_retrieve_for_api(organization_id, organization_we_vote_id, voter_device_id):  #
    """
    Called from organizationRetrieve api
    :param organization_id:
    :param organization_we_vote_id:
    :param voter_device_id:
    :return:
    """
    organization_id = convert_to_int(organization_id)

    organization_we_vote_id = organization_we_vote_id.strip().lower()
    if not positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
        json_data = {
            'status':                           "ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING",
            'success':                          False,
            'organization_id':                  organization_id,
            'organization_we_vote_id':          organization_we_vote_id,
            'organization_name':                '',
            'organization_email':               '',
            'organization_website':             '',
            'organization_twitter_handle':      '',
            'twitter_description':              '',
            'twitter_followers_count':          '',
            'facebook_id':                      0,
            'organization_facebook':            '',
            'organization_photo_url_large':     '',
            'organization_photo_url_medium':    '',
            'organization_photo_url_tiny':      '',
            'organization_banner_url':          '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    if results['organization_found']:
        organization = results['organization']

        # Heal data: If the organization_name is a placeholder name, repair it with fresh data
        if organization_manager.organization_name_needs_repair(organization):
            organization = organization_manager.repair_organization(organization)
            position_list_manager = PositionListManager()
            position_list_manager.refresh_cached_position_info_for_organization(organization_we_vote_id)

        # Favor the Twitter banner and profile image if they exist
        # From Dale September 1, 2017:  Eventually we would like to let a person choose which they want to display,
        # but for now Twitter always wins out.
        we_vote_hosted_profile_image_url_large = organization.we_vote_hosted_profile_image_url_large if \
            positive_value_exists(organization.we_vote_hosted_profile_image_url_large) else \
            organization.organization_photo_url()

        if positive_value_exists(organization.twitter_profile_banner_url_https):
            organization_banner_url = organization.twitter_profile_banner_url_https
        else:
            organization_banner_url = organization.facebook_background_image_url_https

        if isinstance(organization_banner_url, list):
            # If a list, just return the first one
            organization_banner_url = organization_banner_url.pop()
        elif isinstance(organization_banner_url, tuple):
            # If a tuple, just return the first one
            organization_banner_url = organization_banner_url[0]

        json_data = {
            'success': True,
            'status': results['status'],
            'organization_id': organization.id,
            'organization_we_vote_id': organization.we_vote_id,  # this is the we_vote_id for this organization
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_website': organization.organization_website if positive_value_exists(
                organization.organization_website) else '',
            'organization_twitter_handle':
                organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'twitter_description':
                organization.twitter_description if positive_value_exists(
                    organization.twitter_description) else '',
            'twitter_followers_count':
                organization.twitter_followers_count if positive_value_exists(
                    organization.twitter_followers_count) else 0,
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
            'facebook_id':
                organization.facebook_id if positive_value_exists(organization.facebook_id) else 0,
            'organization_photo_url_large': we_vote_hosted_profile_image_url_large,
            'organization_photo_url_medium': organization.we_vote_hosted_profile_image_url_medium,
            'organization_photo_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
            'organization_banner_url': organization_banner_url,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                           results['status'],
            'success':                          False,
            'organization_id':                  organization_id,
            'organization_we_vote_id':          organization_we_vote_id,
            'organization_name':                '',
            'organization_email':               '',
            'organization_website':             '',
            'organization_twitter_handle':      '',
            'twitter_description':              '',
            'twitter_followers_count':          '',
            'organization_facebook':            '',
            'facebook_id':                      0,
            'organization_photo_url_large':     '',
            'organization_photo_url_medium':    '',
            'organization_photo_url_tiny':      '',
            'organization_banner_url':          '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_save_for_api(voter_device_id, organization_id, organization_we_vote_id,   # organizationSave
                              organization_name,
                              organization_email, organization_website,
                              organization_twitter_handle, organization_facebook, organization_image, organization_type,
                              refresh_from_twitter,
                              facebook_id, facebook_email, facebook_profile_image_url_https):
    """
    DALE NOTE: I believe we only use this to save an organization in order to link it to a voter
    NOTE September 2017:  I think the note above is outdated, we now use this to store displayable organization data
    :param voter_device_id:
    :param organization_id:
    :param organization_we_vote_id:
    :param organization_name:
    :param organization_email:
    :param organization_website:
    :param organization_twitter_handle:
    :param organization_facebook:
    :param organization_image:
    :param organization_type
    :param refresh_from_twitter:
    :param facebook_id:
    :param facebook_email:
    :param facebook_profile_image_url_https:
    :return:
    """
    organization_id = convert_to_int(organization_id)
    organization_we_vote_id = organization_we_vote_id.strip().lower()

    # Make sure we are only working with the twitter handle, and not the "https" or "@"
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle)

    facebook_id = convert_to_int(facebook_id)

    existing_unique_identifier_found = positive_value_exists(organization_id) \
        or positive_value_exists(organization_we_vote_id) or positive_value_exists(facebook_id)
    new_unique_identifier_found = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website) or positive_value_exists(facebook_id)
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have one of these: twitter_handle or website, AND organization_name
    required_variables_for_new_entry = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website) or positive_value_exists(facebook_id) \
        and positive_value_exists(organization_name)
    if not unique_identifier_found:
        results = {
            'status':                       "ORGANIZATION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                      False,
            'organization_id':              organization_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'new_organization_created':     False,
            'organization_name':            organization_name,
            'organization_email':           organization_email,
            'organization_website':         organization_website,
            'organization_facebook':        organization_facebook,
            'organization_photo_url':       organization_image,
            'organization_twitter_handle':  organization_twitter_handle,
            'twitter_followers_count':      0,
            'twitter_description':          "",
            'refresh_from_twitter':         refresh_from_twitter,
            'facebook_id':                  facebook_id,
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                       "NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING",
            'success':                      False,
            'organization_id':              organization_id,
            'organization_we_vote_id':      organization_we_vote_id,
            'new_organization_created':     False,
            'organization_name':            organization_name,
            'organization_email':           organization_email,
            'organization_website':         organization_website,
            'organization_facebook':        organization_facebook,
            'organization_photo_url':       organization_image,
            'organization_twitter_handle':  organization_twitter_handle,
            'twitter_followers_count':      0,
            'twitter_description':          "",
            'refresh_from_twitter':         refresh_from_twitter,
            'facebook_id':                  facebook_id,
        }
        return results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter_found = True
        voter = voter_results['voter']
    else:
        voter_found = False
        voter = Voter()

    facebook_background_image_url_https = False
    facebook_manager = FacebookManager()
    facebook_auth_response_results = facebook_manager.retrieve_facebook_auth_response(voter_device_id)
    facebook_auth_response = facebook_auth_response_results['facebook_auth_response']

    if organization_name is False:
        # If the variable comes in as a literal value "False" then don't create an organization_name
        pass
    else:
        if not positive_value_exists(organization_name) or organization_name == "null null":
            organization_name = ""
            if voter_found:
                # First see if there is a Twitter name
                organization_name = voter.twitter_name

                # Check to see if the voter has a name
                if not positive_value_exists(organization_name):
                    organization_name = voter.get_full_name()

            # If not, check the FacebookAuthResponse table
            if not positive_value_exists(organization_name):
                organization_name = facebook_auth_response.get_full_name()

    # Add in the facebook email if we have it
    if facebook_auth_response:
        if not positive_value_exists(facebook_email):
            facebook_email = facebook_auth_response.facebook_email

    organization_manager = OrganizationManager()
    save_results = organization_manager.update_or_create_organization(
        organization_id=organization_id, we_vote_id=organization_we_vote_id,
        organization_website_search=organization_website, organization_twitter_search=organization_twitter_handle,
        organization_name=organization_name, organization_website=organization_website,
        organization_twitter_handle=organization_twitter_handle, organization_email=organization_email,
        organization_facebook=organization_facebook, organization_image=organization_image,
        organization_type=organization_type, refresh_from_twitter=refresh_from_twitter,
        facebook_id=facebook_id, facebook_email=facebook_email,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
    )

    success = save_results['success']
    if save_results['success']:
        organization = save_results['organization']
        status = save_results['status']

        # Create TwitterLinkToOrganization
        twitter_user_manager = TwitterUserManager()
        retrieve_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
            organization.twitter_user_id, organization.organization_twitter_handle)
        if retrieve_results['twitter_user_found']:
            twitter_user = retrieve_results['twitter_user']
            if positive_value_exists(twitter_user.twitter_id):
                link_to_organization_results = \
                    twitter_user_manager.retrieve_twitter_link_to_organization(twitter_user.twitter_id)
                if link_to_organization_results['twitter_link_to_organization_found']:
                    # TwitterLinkToOrganization already exists
                    pass
                else:
                    # Create a TwitterLinkToOrganization entry
                    twitter_user_manager.create_twitter_link_to_organization(twitter_user.twitter_id,
                                                                             organization.we_vote_id)

        # Now update the voter record with the organization_we_vote_id
        if voter_found:
            # Does this voter have the same Twitter handle as this organization? If so, link this organization to
            #  this particular voter
            results = twitter_user_manager.retrieve_twitter_link_to_voter_from_twitter_handle(
                organization.organization_twitter_handle)
            if results['twitter_link_to_voter_found']:
                twitter_link_to_voter = results['twitter_link_to_voter']
                # Check to make sure another voter isn't hanging onto this organization_we_vote_id
                # TODO DALE UPDATE linked_organization_we_vote_id
                voter_manager.clear_out_collisions_for_linked_organization_we_vote_id(voter.we_vote_id,
                                                                                      organization.we_vote_id)
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()

                    # TODO DALE UPDATE positions to add voter_we_vote_id - Any position with
                    # the organization_we_vote_id should get the voter_we_vote_id added,
                    # and any position with the voter_we_vote_id should get the organization_we_vote_id added
                except Exception as e:
                    success = False
                    status += " UNABLE_TO_UPDATE_VOTER_WITH_ORGANIZATION_WE_VOTE_ID_FROM_TWITTER "
            elif positive_value_exists(facebook_id):
                # Check to make sure another voter isn't hanging onto this organization_we_vote_id
                voter_manager.clear_out_collisions_for_linked_organization_we_vote_id(voter.we_vote_id,
                                                                                      organization.we_vote_id)
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()

                    # TODO DALE UPDATE positions to add voter_we_vote_id - Any position with
                    # the organization_we_vote_id should get the voter_we_vote_id added,
                    # and any position with the voter_we_vote_id should get the organization_we_vote_id added
                except Exception as e:
                    success = False
                    status += " UNABLE_TO_UPDATE_VOTER_WITH_ORGANIZATION_WE_VOTE_ID_FROM_FACEBOOK "

        results = {
            'success':                      success,
            'status':                       status,
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
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
            'organization_photo_url':       organization.organization_photo_url()
                if positive_value_exists(organization.organization_photo_url()) else '',
            'organization_twitter_handle':  organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'twitter_followers_count':      organization.twitter_followers_count if positive_value_exists(
                    organization.twitter_followers_count) else 0,
            'twitter_description':          organization.twitter_description if positive_value_exists(
                    organization.twitter_description) else '',
            'refresh_from_twitter':         refresh_from_twitter,
            'facebook_id': organization.facebook_id if positive_value_exists(organization.facebook_id) else 0,
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
            'organization_facebook':    organization_facebook,
            'organization_photo_url':   organization_image,
            'organization_twitter_handle': organization_twitter_handle,
            'twitter_followers_count':  0,
            'twitter_description':      "",
            'refresh_from_twitter':     refresh_from_twitter,
            'facebook_id':              facebook_id,
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


def refresh_organization_data_from_master_tables(organization_we_vote_id):
    twitter_profile_image_url_https = None
    twitter_profile_background_image_url_https = None
    twitter_profile_banner_url_https = None
    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None
    twitter_json = {}
    success = False
    status = ""

    organization_manager = OrganizationManager()
    twitter_user_manager = TwitterUserManager()
    voter_manager = VoterManager()

    results = organization_manager.retrieve_organization(0, organization_we_vote_id)
    status += results['status']
    if not results['organization_found']:
        status += "REFRESH_ORGANIZATION_FROM_MASTER_TABLES-ORGANIZATION_NOT_FOUND "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    organization = results['organization']

    # Retrieve voter data from Voter table
    voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization_we_vote_id)

    twitter_id_belongs_to_this_organization = True
    twitter_user_id = organization.twitter_user_id
    twitter_link_to_org_results = twitter_user_manager.\
        retrieve_twitter_link_to_organization_from_organization_we_vote_id(organization_we_vote_id)
    if twitter_link_to_org_results['twitter_link_to_organization_found']:
        # If here, we have found a twitter_link_to_organization entry for this organization
        twitter_user_id = twitter_link_to_org_results['twitter_link_to_organization'].twitter_id
    else:
        # If here, a twitter_link_to_organization entry was not found for the organization
        # Is the twitter_user_id in use by any other group?
        results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(twitter_user_id)
        if results['twitter_link_to_organization_found']:
            # If here, then we know that the Twitter id is being used by another group, so we want to wipe out the
            # value from this organization.
            twitter_id_belongs_to_this_organization = False
            try:
                organization.organization_twitter_handle = None
                organization.twitter_user_id = None
                organization.twitter_followers_count = 0
                organization.save()
            except Exception as e:
                status += "COULD_NOT_SAVE_ORGANIZATION "
        else:
            twitter_user_manager.create_twitter_link_to_organization(twitter_user_id, organization_we_vote_id)

    # Retrieve twitter user data from TwitterUser Table
    if twitter_id_belongs_to_this_organization:
        twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_user_id)
        if twitter_user_results['twitter_user_found']:
            twitter_user = twitter_user_results['twitter_user']
            if twitter_user.twitter_handle != organization.organization_twitter_handle or \
                    twitter_user.twitter_name != organization.twitter_name or \
                    twitter_user.twitter_location != organization.twitter_location or \
                    twitter_user.twitter_followers_count != organization.twitter_followers_count or \
                    twitter_user.twitter_description != organization.twitter_description:
                twitter_json = {
                    'id':               twitter_user.twitter_id,
                    'screen_name':      twitter_user.twitter_handle,
                    'name':             twitter_user.twitter_name,
                    'followers_count':  twitter_user.twitter_followers_count,
                    'location':         twitter_user.twitter_location,
                    'description':      twitter_user.twitter_description,
                }

        # Retrieve organization images data from WeVoteImage table
        we_vote_image_list = retrieve_all_images_for_one_organization(organization.we_vote_id)
        if len(we_vote_image_list):
            # Retrieve all cached image for this organization
            for we_vote_image in we_vote_image_list:
                if we_vote_image.kind_of_image_twitter_profile:
                    if we_vote_image.kind_of_image_original:
                        twitter_profile_image_url_https = we_vote_image.we_vote_image_url
                    if we_vote_image.kind_of_image_large:
                        we_vote_hosted_profile_image_url_large = we_vote_image.we_vote_image_url
                    if we_vote_image.kind_of_image_medium:
                        we_vote_hosted_profile_image_url_medium = we_vote_image.we_vote_image_url
                    if we_vote_image.kind_of_image_tiny:
                        we_vote_hosted_profile_image_url_tiny = we_vote_image.we_vote_image_url
                elif we_vote_image.kind_of_image_twitter_background and we_vote_image.kind_of_image_original:
                    twitter_profile_background_image_url_https = we_vote_image.we_vote_image_url
                elif we_vote_image.kind_of_image_twitter_banner and we_vote_image.kind_of_image_original:
                    twitter_profile_banner_url_https = we_vote_image.we_vote_image_url

        update_organization_results = organization_manager.update_organization_twitter_details(
            organization, twitter_json, twitter_profile_image_url_https,
            twitter_profile_background_image_url_https, twitter_profile_banner_url_https,
            we_vote_hosted_profile_image_url_large, we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny)
        success = update_organization_results['success']
        status += update_organization_results['status']

    results = {
        'success': success,
        'status': status,
    }
    return results


def push_organization_data_to_other_table_caches(organization_we_vote_id):
    organization_manager = OrganizationManager()
    voter_guide_manager = VoterGuideManager()
    results = organization_manager.retrieve_organization(0, organization_we_vote_id)
    organization = results['organization']

    save_voter_guide_from_organization_results = \
        voter_guide_manager.update_organization_voter_guides_with_organization_data(organization)

    save_position_from_organization_results = update_position_entered_details_from_organization(organization)


def retrieve_organizations_followed(voter_id, auto_followed_from_twitter_suggestion=False):
    organization_list_found = False
    organization_list = []

    follow_organization_list_manager = FollowOrganizationList()
    organization_ids_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(
            voter_id, auto_followed_from_twitter_suggestion=auto_followed_from_twitter_suggestion)

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


def update_social_media_statistics_in_other_tables(organization):
    """
    Update other tables that use any of these social media statistics
    DALE 2017-11-06 This function is used several places, but I don't think it is doing what is implied by its name
    :param organization:
    :return:
    """

    voter_guide_manager = VoterGuideManager()
    voter_guide_results = voter_guide_manager.update_voter_guide_social_media_statistics(organization)

    if voter_guide_results['success'] and voter_guide_results['voter_guide']:
        voter_guide = voter_guide_results['voter_guide']
    else:
        voter_guide = VoterGuide()

    status = "FINISHED_UPDATE_SOCIAL_MEDIA_STATISTICS_IN_OTHER_TABLES"

    results = {
        'success':      True,
        'status':       status,
        'organization': organization,
        'voter_guide':  voter_guide,
    }
    return results
