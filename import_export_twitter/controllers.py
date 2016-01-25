# import_export_twitter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/controllers.py for routines that manage internal twitter data

from config.base import get_environment_variable
from organization.controllers import update_social_media_statistics_in_other_tables
from organization.models import Organization, OrganizationManager
import re
from socket import timeout
import tweepy
import urllib.request
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

RE_FACEBOOK = r'//www\.facebook\.com/(?:#!/)?(\w+)'
# RE_FACEBOOK = r'/(?:https?:\/\/)?(?:www\.)?facebook\.com\/(?:(?:\w)*#!\/)?(?:pages\/)?(?:[\w\-]*\/)*?(\/)?([^/?]*)/'
FACEBOOK_BLACKLIST = ['group', 'group.php', 'None']
# NOTE: Scraping a website for the Facebook handle is more complicated than Twitter. There must be an existing
#  solution available? My attempt turned off for now.

# Only pays attention to https://twitter.com or http://twitter.com and ignores www.twitter.com
RE_TWITTER = r'//twitter\.com/(?:#!/)?(\w+)'
TWITTER_BLACKLIST = ['home', 'https', 'intent', 'none', 'search', 'share', 'twitterapi']
TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


class GetOutOfLoop(Exception):
    pass


class GetOutOfLoopLocal(Exception):
    pass


def refresh_twitter_details(organization):
    organization_manager = OrganizationManager()
    status = "ENTERING_REFRESH_TWITTER_DETAILS"

    if not organization:
        status = "ORGANIZATION_TWITTER_DETAILS_NOT_RETRIEVED-ORG_MISSING"
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if organization.organization_twitter_handle:
        status = "ORGANIZATION_TWITTER_DETAILS-REACHING_OUT_TO_TWITTER"
        results = retrieve_twitter_user_info(organization.organization_twitter_handle)

        if results['success']:
            status = "ORGANIZATION_TWITTER_DETAILS_RETRIEVED_FROM_TWITTER"
            save_results = organization_manager.update_organization_twitter_details(
                organization, results['twitter_json'])

            if save_results['success']:
                results = update_social_media_statistics_in_other_tables(organization)
                status = "ORGANIZATION_TWITTER_DETAILS_RETRIEVED_FROM_TWITTER_AND_SAVED"
    else:
            status = "ORGANIZATION_TWITTER_DETAILS-CLEARING_DETAILS"
            save_results = organization_manager.clear_organization_twitter_details(organization)

            if save_results['success']:
                results = update_social_media_statistics_in_other_tables(organization)
                status = "ORGANIZATION_TWITTER_DETAILS_CLEARED_FROM_DB"


    results = {
        'success':                  True,
        'status':                   status,
    }
    return results


def retrieve_twitter_user_info(twitter_handle):
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth)

    twitter_handle_found = False
    twitter_json = []
    try:
        twitter_user = api.get_user(twitter_handle)
        twitter_json = twitter_user._json
        success = True
        status = 'TWITTER_RETRIEVE_SUCCESSFUL'
    except tweepy.RateLimitError:
        success = False
        status = 'TWITTER_RATE_LIMIT_ERROR'
    except tweepy.error.TweepError as error_instance:
        success = False
        status = ''
        error_tuple = error_instance.args
        for error_dict in error_tuple:
            for one_error in error_dict:
                status += '[' + one_error['message'] + '] '

    results = {
        'status':               status,
        'success':              success,
        'twitter_handle':       twitter_handle,
        'twitter_handle_found': twitter_handle_found,
        'twitter_json':         twitter_json,
    }
    return results


def scrape_social_media_from_one_site(site_url):
    twitter_handle = ''
    twitter_handle_found = False
    facebook_page = ''
    facebook_page_found = False
    success = False
    if len(site_url) < 10:
        status = 'PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':               status,
            'success':              success,
            'twitter_handle':       twitter_handle,
            'twitter_handle_found': twitter_handle_found,
            'facebook_page':        facebook_page,
            'facebook_page_found':  facebook_page_found,
        }
        return results

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Encoding': 'none',
    # 'Accept-Language': 'en-US,en;q=0.8',
    # 'Connection': 'keep-alive'
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        for line in page.readlines():
            try:
                if not twitter_handle_found:
                    for m in re.finditer(RE_TWITTER, line.decode()):
                        if m:
                            name = m.group(1)
                            if name not in TWITTER_BLACKLIST:
                                twitter_handle = name
                                twitter_handle_found = True
                                raise GetOutOfLoopLocal
            except GetOutOfLoopLocal:
                pass
            # SEE NOTE ABOUT FACEBOOK SCRAPING ABOVE
            # try:
            #     if not facebook_page_found:
            #         for m2 in re.finditer(RE_FACEBOOK, line.decode()):
            #             if m2:
            #                 possible_page1 = m2.group(1)
            #                 if possible_page1 not in FACEBOOK_BLACKLIST:
            #                     facebook_page = possible_page1
            #                     facebook_page_found = True
            #                     raise GetOutOfLoopLocal
            #                 try:
            #                     possible_page2 = m2.group(2)
            #                     if possible_page2 not in FACEBOOK_BLACKLIST:
            #                         facebook_page = possible_page2
            #                         facebook_page_found = True
            #                         raise GetOutOfLoopLocal
            #                     # ATTEMPT 1
            #                     # start_of_close_tag_index = possible_page2.find('"')
            #                     # possible_page2 = possible_page2[:start_of_close_tag_index]
            #                     # ATTEMPT 2
            #                     # fb_re = re.compile(r'facebook.com([^"]+)')
            #                     # results = fb_re.findall(possible_page2)
            #                 except Exception as error_instance:
            #                     pass
            #                 # possible_page3 = m2.group(3)
            #                 # possible_page4 = m2.group(4)
            # except GetOutOfLoopLocal:
            #     pass
            if twitter_handle_found:  # and facebook_page_found:
                raise GetOutOfLoop
        success = True
        status = 'FINISHED_SCRAPING_PAGE'
    except timeout:
        status = "SCRAPE_TIMEOUT_ERROR"
        success = False
    except GetOutOfLoop:
        success = True
        status = 'TWITTER_HANDLE_FOUND-BREAK_OUT'
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status = "SCRAPE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status = "SCRAPE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status':               status,
        'success':              success,
        'page_redirected':      twitter_handle,
        'twitter_handle':       twitter_handle,
        'twitter_handle_found': twitter_handle_found,
        'facebook_page':        facebook_page,
        'facebook_page_found':  facebook_page_found,
    }
    return results


def scrape_and_save_social_media_from_all_organizations(state_code=''):
    facebook_pages_found = 0
    twitter_handles_found = 0
    force_retrieve = False
    temp_count = 0

    organization_manager = OrganizationManager()
    organization_list_query = Organization.objects.order_by('organization_name')
    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code=state_code)

    organization_list = organization_list_query
    for organization in organization_list:
        twitter_handle = ''
        facebook_page = ''
        if not organization.organization_website:
            continue
        if (not positive_value_exists(organization.organization_twitter_handle)) or force_retrieve:
            scrape_results = scrape_social_media_from_one_site(organization.organization_website)

            if scrape_results['twitter_handle_found']:
                twitter_handle = scrape_results['twitter_handle']
                twitter_handles_found += 1

            if scrape_results['facebook_page_found']:
                facebook_page = scrape_results['facebook_page']
                facebook_pages_found += 1

        save_results = organization_manager.update_organization_social_media(organization, twitter_handle,
                                                                             facebook_page)

        if save_results['success']:
            organization = save_results['organization']

        # ######################################
        if organization.organization_twitter_handle:
            results = retrieve_twitter_user_info(organization.organization_twitter_handle)

            if results['success']:
                save_results = organization_manager.update_organization_twitter_details(
                    organization, results['twitter_json'])

                if save_results['success']:
                    results = update_social_media_statistics_in_other_tables(organization)
        # ######################################

        # temp_count += 1
        # if temp_count > 10:
        #     break

    status = "ORGANIZATION_SOCIAL_MEDIA_RETRIEVED"
    results = {
        'success':                  True,
        'status':                   status,
        'twitter_handles_found':    twitter_handles_found,
        'facebook_pages_found':     facebook_pages_found,
    }
    return results
