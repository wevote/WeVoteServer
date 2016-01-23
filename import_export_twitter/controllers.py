# import_export_twitter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/controllers.py for routines that manage internal twitter data

from config.base import get_environment_variable
from organization.models import Organization, OrganizationManager
import re
from socket import timeout
import tweepy
import urllib.request
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

RE_TWITTER = r'//twitter\.com/(?:#!/)?(\w+)'
# RE_TWITTER_INTENT = r'https://twitter.com/intent/follow?user_id=168541923'
TWITTER_BLACKLIST = ['intent', 'search', 'share', 'twitterapi']
TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = get_environment_variable("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = get_environment_variable("TWITTER_ACCESS_TOKEN_SECRET")


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


class GetOutOfLoop(Exception):
    pass


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
    success = False
    if len(site_url) < 10:
        status = 'PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':               status,
            'success':              success,
            'twitter_handle':       twitter_handle,
            'twitter_handle_found': twitter_handle_found,
        }
        return results

    urllib._urlopener = FakeFirefoxURLopener()
    try:
        page = urllib.request.urlopen(site_url, timeout=5)
        for line in page.readlines():
            for m in re.finditer(RE_TWITTER, line.decode()):
                if m:
                    name = m.group(1)
                    if name not in TWITTER_BLACKLIST:
                        twitter_handle = name
                        twitter_handle_found = True
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
        # Catch the error message coming back from Vote Smart and pass it in the status
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
    }
    return results


def scrape_and_save_social_media_from_all_organizations():
    twitter_handles_found = 0
    force_retrieve = False
    temp_count = 0

    organization_manager = OrganizationManager()
    organization_list = Organization.objects.order_by('organization_name')
    for organization in organization_list:
        twitter_handle = ''
        organization_facebook = ''
        if not organization.organization_website:
            continue
        if (not positive_value_exists(organization.organization_twitter_handle)) or force_retrieve:
            scrape_results = scrape_social_media_from_one_site(organization.organization_website)

            if scrape_results['twitter_handle_found']:
                twitter_handle = scrape_results['twitter_handle']
                twitter_handles_found += 1

        save_results = organization_manager.update_organization_social_media(organization, twitter_handle,
                                                                             organization_facebook)

        if save_results['success']:
            organization = save_results['organization']

        # ######################################
        if organization.organization_twitter_handle:
            results = retrieve_twitter_user_info(organization.organization_twitter_handle)

            if results['success']:
                save_results = organization_manager.update_organization_twitter_details(
                    organization, results['twitter_json'])

                if save_results['success']:
                    results = organization_manager.update_social_media_statistics_in_other_tables(organization)
        # ######################################

        # temp_count += 1
        # if temp_count > 10:
        #     break

    status = "ORGANIZATION_SOCIAL_MEDIA_RETRIEVED"
    results = {
        'success':                  True,
        'status':                   status,
        'twitter_handles_found':    twitter_handles_found,
    }
    return results
