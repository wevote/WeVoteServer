# voter_guide/controllers_possibility.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from import_export_twitter.controllers import refresh_twitter_organization_details, scrape_social_media_from_one_site
from organization.models import Organization, OrganizationListManager, OrganizationManager, \
    CORPORATION, GROUP, INDIVIDUAL, NEWS_ORGANIZATION, NONPROFIT, NONPROFIT_501C3, NONPROFIT_501C4, \
    POLITICAL_ACTION_COMMITTEE, ORGANIZATION, PUBLIC_FIGURE, UNKNOWN, VOTER, ORGANIZATION_TYPE_CHOICES

from twitter.models import TwitterUserManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, convert_date_to_we_vote_date_string, \
    extract_facebook_username_from_text_string, \
    extract_twitter_handle_from_text_string, extract_website_from_url, positive_value_exists, \
    STATE_CODE_MAP, get_voter_device_id, get_voter_api_device_id

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut


def organizations_found_on_url(url_to_scan, state_code=''):
    status = ""
    success = True
    organization_list_manager = OrganizationListManager()
    organization_manager = OrganizationManager()
    organization_list = []
    organization_count = 0
    twitter_user_manager = TwitterUserManager()

    facebook_page_list = []
    twitter_or_facebook_found = False
    twitter_handle_list = []

    retrieve_list = True
    scrape_results = scrape_social_media_from_one_site(url_to_scan, retrieve_list)

    # Only include a change if we have a new value (do not try to save blank value)
    if scrape_results['twitter_handle_found'] and positive_value_exists(scrape_results['twitter_handle']):
        twitter_handle_list = scrape_results['twitter_handle_list']
        twitter_or_facebook_found = True

    if scrape_results['facebook_page_found'] and positive_value_exists(scrape_results['facebook_page']):
        facebook_page_list = scrape_results['facebook_page_list']
        twitter_or_facebook_found = True

    if twitter_or_facebook_found:
        # Search for organizations that match (by Twitter Handle)
        twitter_handle_list_modified = []
        for one_twitter_handle in twitter_handle_list:
            if positive_value_exists(one_twitter_handle):
                one_twitter_handle = one_twitter_handle.strip()
            if positive_value_exists(one_twitter_handle):
                twitter_handle_lower = one_twitter_handle.lower()
                twitter_handle_lower = extract_twitter_handle_from_text_string(twitter_handle_lower)
                if twitter_handle_lower not in twitter_handle_list_modified:
                    twitter_handle_list_modified.append(twitter_handle_lower)

        # Search for organizations that match (by Facebook page)
        facebook_page_list_modified = []
        for one_facebook_page in facebook_page_list:
            if positive_value_exists(one_facebook_page):
                one_facebook_page = one_facebook_page.strip()
            if positive_value_exists(one_facebook_page):
                one_facebook_page_lower = one_facebook_page.lower()
                one_facebook_page_lower = extract_facebook_username_from_text_string(one_facebook_page_lower)
                if one_facebook_page_lower not in facebook_page_list_modified:
                    facebook_page_list_modified.append(one_facebook_page_lower)

        # We want to create an organization for each Twitter handle we find on the page so it can be chosen below
        for one_twitter_handle in twitter_handle_list_modified:
            one_organization_found = False
            results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                one_twitter_handle)
            if results['twitter_link_to_organization_found']:
                twitter_link_to_organization = results['twitter_link_to_organization']
                organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    twitter_link_to_organization.organization_we_vote_id)
                if organization_results['organization_found']:
                    one_organization_found = True
            twitter_user_id = 0
            twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                twitter_user_id, one_twitter_handle)
            if twitter_results['twitter_user_found']:
                twitter_user = twitter_results['twitter_user']
                twitter_user_id = twitter_user.twitter_id
            if not one_organization_found and positive_value_exists(twitter_user_id):
                organization_name = ""
                if not positive_value_exists(state_code):
                    state_code = None
                create_results = organization_manager.create_organization(
                    organization_name=organization_name,
                    organization_type=GROUP,
                    organization_twitter_handle=one_twitter_handle,
                    state_served_code=state_code)
                if create_results['organization_created']:
                    one_organization = create_results['organization']

                    # Create TwitterLinkToOrganization
                    link_results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_user_id, one_organization.we_vote_id)
                    # Refresh the organization with the Twitter details
                    refresh_twitter_organization_details(one_organization, twitter_user_id)

        voter_guide_website = extract_website_from_url(url_to_scan)
        results = organization_list_manager.organization_search_find_any_possibilities(
            organization_website=voter_guide_website,
            facebook_page_list=facebook_page_list_modified,
            twitter_handle_list=twitter_handle_list_modified
        )

        if results['organizations_found']:
            organization_list = results['organizations_list']
            organization_count = len(organization_list)

    results = {
        'status':               status,
        'success':              success,
        'organization_list':    organization_list,
        'organization_count':   organization_count,
    }
    return results
