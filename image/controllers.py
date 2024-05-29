# image/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import time

import requests
from django.db.models import Q

import wevote_functions.admin
from candidate.models import CandidateManager, PROFILE_IMAGE_TYPE_BALLOTPEDIA, PROFILE_IMAGE_TYPE_FACEBOOK, \
    PROFILE_IMAGE_TYPE_LINKEDIN, \
    PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA, PROFILE_IMAGE_TYPE_WIKIPEDIA
from config.base import get_environment_variable
from import_export_facebook.models import FacebookManager
from issue.models import IssueManager
from organization.models import OrganizationManager
from politician.models import PoliticianManager
from position.controllers import reset_all_position_image_details_from_candidate, \
    reset_position_for_friends_image_details_from_voter, reset_position_entered_image_details_from_organization, \
    update_all_position_details_from_candidate
from twitter.functions import retrieve_twitter_user_info
from twitter.models import TwitterUserManager
from voter.models import VoterManager, VoterDeviceLink, VoterDeviceLinkManager, VoterAddressManager, Voter
from voter_guide.models import VoterGuideManager
from wevote_functions.functions import positive_value_exists, convert_to_int
from .functions import analyze_remote_url, analyze_image_file, analyze_image_in_memory, \
    change_default_profile_image_if_needed
from .models import WeVoteImageManager, WeVoteImage, \
    CHOSEN_FAVICON_NAME, CHOSEN_LOGO_NAME, CHOSEN_SOCIAL_SHARE_IMAGE_NAME, \
    FACEBOOK_PROFILE_IMAGE_NAME, FACEBOOK_BACKGROUND_IMAGE_NAME, \
    TWITTER_PROFILE_IMAGE_NAME, TWITTER_BACKGROUND_IMAGE_NAME, TWITTER_BANNER_IMAGE_NAME, MAPLIGHT_IMAGE_NAME, \
    MASTER_IMAGE, ISSUE_IMAGE_NAME, BALLOTPEDIA_IMAGE_NAME, CAMPAIGNX_PHOTO_IMAGE_NAME, CTCL_PROFILE_IMAGE_NAME, \
    LINKEDIN_IMAGE_NAME, ORGANIZATION_UPLOADED_PROFILE_IMAGE_NAME, POLITICIAN_UPLOADED_PROFILE_IMAGE_NAME, \
    VOTE_SMART_IMAGE_NAME, VOTE_USA_PROFILE_IMAGE_NAME, VOTER_UPLOADED_IMAGE_NAME, \
    WIKIPEDIA_IMAGE_NAME

logger = wevote_functions.admin.get_logger(__name__)
HTTP_OK = 200
# These constants are used for "image_source" which is not a WeVoteImage table value, but gets used in the controller
# to set the table values like: kind_of_image_twitter_profile and kind_of_image_facebook_profile
# code. "other_source" is a database table value that is not given its own "kind_of_image..." table boolean
TWITTER = "twitter"
FACEBOOK = "facebook"
MAPLIGHT = "maplight"
VOTE_SMART = "vote_smart"
IMAGE_SOURCE_GOOGLE_CIVIC = "google_civic"
IMAGE_SOURCE_VOTE_USA = "vote_usa"
IMAGE_SOURCE_BALLOTPEDIA = "ballotpedia"
IMAGE_SOURCE_WIKIPEDIA = "wikipedia"
LINKEDIN = "linkedin"
WIKIPEDIA = "wikipedia"
OTHER_SOURCE = "other_source"  # Set "kind_of_image_other_source" to true

BALLOTPEDIA_URL_NOT_FOUND = "ballotpedia url not found"
CAMPAIGNX_PHOTO_URL_NOT_FOUND = "campaignx photo url not found"
CTCL_PROFILE_URL_NOT_FOUND = "ctcl profile url not found"
FACEBOOK_USER_DOES_NOT_EXIST = "facebook user does not exist"
FACEBOOK_URL_NOT_FOUND = "facebook url not found"
IMAGE_ALREADY_CACHED = "image already cached"
LINKEDIN_URL_NOT_FOUND = "linkedin url not found"
MAPLIGHT_URL_NOT_FOUND = "maplight url not found"
OTHER_SOURCE_URL_NOT_FOUND = "other source url not found"
TWITTER_USER_DOES_NOT_EXIST = "twitter user does not exist"
TWITTER_URL_NOT_FOUND = "twitter url not found"
VOTE_SMART_URL_NOT_FOUND = "votesmart url not found"
VOTE_USA_PROFILE_URL_NOT_FOUND = "vote usa profile url not found"
VOTER_UPLOADED_PROFILE_IMAGE_DOES_NOT_EXIST = "voter uploaded profile image does not exist"
WIKIPEDIA_URL_NOT_FOUND = "wikipedia url not found"

# Search for in campaign/controllers.py as well
# Facebook shared image: 1200 x 630
# Facebook shared link: 1200 x 628
# Tweet with image in shared link: 1200 x 628
# Tweet with single image: 1200 x 675 (Twitter recommended aspect ratio is 16:9)
CAMPAIGN_PHOTO_ORIGINAL_MAX_WIDTH = 1200
CAMPAIGN_PHOTO_ORIGINAL_MAX_HEIGHT = 628
CAMPAIGN_PHOTO_LARGE_MAX_WIDTH = 575
CAMPAIGN_PHOTO_LARGE_MAX_HEIGHT = 301
CAMPAIGN_PHOTO_MEDIUM_MAX_WIDTH = 224
CAMPAIGN_PHOTO_MEDIUM_MAX_HEIGHT = 117
CAMPAIGN_PHOTO_SMALL_MAX_WIDTH = 140
CAMPAIGN_PHOTO_SMALL_MAX_HEIGHT = 73
PROFILE_IMAGE_ORIGINAL_MAX_WIDTH = 2048
PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT = 2048
PROFILE_IMAGE_LARGE_WIDTH = convert_to_int(get_environment_variable("PROFILE_IMAGE_LARGE_WIDTH"))
PROFILE_IMAGE_LARGE_HEIGHT = convert_to_int(get_environment_variable("PROFILE_IMAGE_LARGE_HEIGHT"))
PROFILE_IMAGE_MEDIUM_WIDTH = convert_to_int(get_environment_variable("PROFILE_IMAGE_MEDIUM_WIDTH"))
PROFILE_IMAGE_MEDIUM_HEIGHT = convert_to_int(get_environment_variable("PROFILE_IMAGE_MEDIUM_HEIGHT"))
PROFILE_IMAGE_TINY_WIDTH = convert_to_int(get_environment_variable("PROFILE_IMAGE_TINY_WIDTH"))
PROFILE_IMAGE_TINY_HEIGHT = convert_to_int(get_environment_variable("PROFILE_IMAGE_TINY_HEIGHT"))
ISSUES_IMAGE_LARGE_WIDTH = convert_to_int(get_environment_variable("ISSUES_IMAGE_LARGE_WIDTH"))
ISSUES_IMAGE_LARGE_HEIGHT = convert_to_int(get_environment_variable("ISSUES_IMAGE_LARGE_HEIGHT"))
ISSUES_IMAGE_MEDIUM_WIDTH = convert_to_int(get_environment_variable("ISSUES_IMAGE_MEDIUM_WIDTH"))
ISSUES_IMAGE_MEDIUM_HEIGHT = convert_to_int(get_environment_variable("ISSUES_IMAGE_MEDIUM_HEIGHT"))
ISSUES_IMAGE_TINY_WIDTH = convert_to_int(get_environment_variable("ISSUES_IMAGE_TINY_WIDTH"))
ISSUES_IMAGE_TINY_HEIGHT = convert_to_int(get_environment_variable("ISSUES_IMAGE_TINY_HEIGHT"))
AWS_STORAGE_BUCKET_NAME = get_environment_variable("AWS_STORAGE_BUCKET_NAME")

try:
    SOCIAL_BACKGROUND_IMAGE_WIDTH = convert_to_int(get_environment_variable("SOCIAL_BACKGROUND_IMAGE_WIDTH"))
    SOCIAL_BACKGROUND_IMAGE_HEIGHT = convert_to_int(get_environment_variable("SOCIAL_BACKGROUND_IMAGE_HEIGHT"))
except Exception:
    # In case not defined in a dev environment, use the default values which come from the Sept 2017 size of the react
    #   image class="organization-banner-image-img"
    logger.error(
        "SOCIAL_BACKGROUND_IMAGE_WIDTH and/or SOCIAL_BACKGROUND_IMAGE_HEIGHT not defined in environment_variables.")
    SOCIAL_BACKGROUND_IMAGE_HEIGHT = 200    # HTML x
    SOCIAL_BACKGROUND_IMAGE_WIDTH = 900     # HTML y

log_time = False


def log_and_time_cache_action(start, time0, name):
    if log_time:
        if start:
            print('image/controllers process timing start for', name)
            return time.time()
        else:
            dt = time.time() - time0
            print('image/controllers process timing start for', name, '-- took {:.3f}'.format(dt),
                  'seconds to complete.')
            return 0


def cache_all_kind_of_images_locally_for_all_organizations():
    """
    Cache all kind of images locally for all organizations
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_all_kind_of_images_locally_for_all_organizations')
    cache_images_locally_for_all_organizations_results = []

    # TODO Update this for organizations
    # voter_list = Voter.objects.all()
    #
    # # If there is a value in twitter_id OR facebook_id, return the voter
    # image_filters = []
    # new_filter = Q(twitter_id__isnull=False)
    # image_filters.append(new_filter)
    # new_filter = Q(facebook_id__isnull=False)
    # image_filters.append(new_filter)
    #
    # # Add the first query
    # final_filters = image_filters.pop()
    #
    # # ...and "OR" the remaining items in the list
    # for item in image_filters:
    #     final_filters |= item
    #
    # # voter_list = voter_list.filter(final_filters)
    # voter_list = voter_list.order_by('-is_admin', '-is_verified_volunteer', 'facebook_email', 'twitter_screen_name',
    #                                  'last_name', 'first_name')
    # voter_list = voter_list[:200]  # Limit to 200 for now
    #
    # for voter in voter_list:
    #     cache_images_for_one_organization_results = migrate_remote_voter_image_urls_to_local_cache(voter.id)
    #     cache_images_locally_for_all_organizations_results.append(cache_images_for_one_organization_results)

    log_and_time_cache_action(False, time0, 'cache_all_kind_of_images_locally_for_all_organizations')
    return cache_images_locally_for_all_organizations_results


def cache_all_kind_of_images_locally_for_all_voters():
    """
    Cache all kind of images locally for all voters
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_all_kind_of_images_locally_for_all_voters')
    cache_images_locally_for_all_voters_results = []

    voter_list = Voter.objects.all()

    # If there is a value in twitter_id OR facebook_id, return the voter
    image_filters = []
    new_filter = Q(twitter_id__isnull=False)
    image_filters.append(new_filter)
    new_filter = Q(facebook_id__isnull=False)
    image_filters.append(new_filter)

    # Add the first query
    final_filters = image_filters.pop()

    # ...and "OR" the remaining items in the list
    for item in image_filters:
        final_filters |= item

    # voter_list = voter_list.filter(final_filters)
    voter_list = voter_list.order_by('-is_admin', '-is_verified_volunteer', 'facebook_email', 'twitter_screen_name',
                                     'last_name', 'first_name')
    voter_list = voter_list[:200]  # Limit to 200 for now

    for voter in voter_list:
        cache_images_for_a_voter_results = cache_voter_master_images(voter.id)
        cache_images_locally_for_all_voters_results.append(cache_images_for_a_voter_results)

    log_and_time_cache_action(False, time0, 'cache_all_kind_of_images_locally_for_all_voters')
    return cache_images_locally_for_all_voters_results


def cache_image_if_not_cached(
        campaignx_we_vote_id=None,
        candidate_we_vote_id=None,
        facebook_background_image_offset_x=None,
        facebook_background_image_offset_y=None,
        facebook_user_id=None,
        google_civic_election_id=0,
        image_url_https='',
        issue_we_vote_id=None,
        is_active_version=False,
        kind_of_image_ballotpedia_profile=False,
        kind_of_image_campaignx_photo=False,
        kind_of_image_ctcl_profile=False,
        kind_of_image_facebook_background=False,
        kind_of_image_facebook_profile=False,
        kind_of_image_issue=False,
        kind_of_image_linkedin_profile=False,
        kind_of_image_maplight=False,
        kind_of_image_organization_uploaded_profile=False,
        kind_of_image_original=False,
        kind_of_image_other_source=False,
        kind_of_image_politician_uploaded_profile=False,
        kind_of_image_twitter_background=False,
        kind_of_image_twitter_banner=False,
        kind_of_image_twitter_profile=False,
        kind_of_image_vote_smart=False,
        kind_of_image_vote_usa_profile=False,
        kind_of_image_voter_uploaded_profile=False,
        kind_of_image_wikipedia_profile=False,
        maplight_id=None,
        organization_we_vote_id=None,
        other_source=None,
        politician_we_vote_id=None,
        representative_we_vote_id=None,
        twitter_id=None,
        twitter_screen_name=None,
        voter_we_vote_id=None,
        vote_smart_id=None):
    """
    Check if image is already cached or not. If not then cached it.
    :param campaignx_we_vote_id:
    :param candidate_we_vote_id:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :param facebook_user_id:
    :param google_civic_election_id:
    :param image_url_https:
    :param issue_we_vote_id:
    :param is_active_version:
    :param kind_of_image_ballotpedia_profile:
    :param kind_of_image_campaignx_photo:
    :param kind_of_image_ctcl_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_issue:
    :param kind_of_image_linkedin_profile:
    :param kind_of_image_maplight:
    :param kind_of_image_organization_uploaded_profile:
    :param kind_of_image_original:
    :param kind_of_image_other_source:
    :param kind_of_image_politician_uploaded_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_vote_smart:
    :param kind_of_image_vote_usa_profile:
    :param kind_of_image_voter_uploaded_profile:
    :param kind_of_image_wikipedia_profile:
    :param maplight_id:
    :param organization_we_vote_id:
    :param other_source:
    :param politician_we_vote_id:
    :param representative_we_vote_id:
    :param twitter_id:
    :param twitter_screen_name:
    :param voter_we_vote_id:
    :param vote_smart_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_image_if_not_cached')
    we_vote_image_manager = WeVoteImageManager()
    cached_we_vote_image_results = we_vote_image_manager.retrieve_recent_cached_we_vote_image(
        campaignx_we_vote_id=campaignx_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        is_active_version=True,
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_original=kind_of_image_original,
        kind_of_image_other_source=kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        representative_we_vote_id=representative_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )

    # If recent cached image matches with the current one the image is already cached
    # Jan 2022: Facebook reuses the same hash for the download link facebook_profile_image_url_https if you change
    # profile picture quickly enough (timing uncertain), so we can use that as a criteria.  Since we are processing
    # these asynchronously in a SQS job, run the job each time the voter signs in with Facebook.
    # Feb 2023 Dale: This function is used for both SQS and at least one other Facebook retrieve path
    #  (voter_cache_facebook_images_process), and the SQS approach (of not using the original Facebook image url) isn't
    #  compatible with how we use the original Facebook image url downstream for later processing.
    #  REMOVED: and not kind_of_image_facebook_profile
    cached_we_vote_image = cached_we_vote_image_results['we_vote_image']
    if cached_we_vote_image_results['we_vote_image_found'] and (\
            image_url_https == cached_we_vote_image.ballotpedia_profile_image_url or \
            image_url_https == cached_we_vote_image.campaignx_photo_url_https or \
            image_url_https == cached_we_vote_image.facebook_background_image_url_https or \
            image_url_https == cached_we_vote_image.facebook_profile_image_url_https or \
            image_url_https == cached_we_vote_image.issue_image_url_https or \
            image_url_https == cached_we_vote_image.linkedin_profile_image_url or \
            image_url_https == cached_we_vote_image.maplight_image_url_https or \
            image_url_https == cached_we_vote_image.organization_uploaded_profile_image_url_https or \
            image_url_https == cached_we_vote_image.other_source_image_url or \
            image_url_https == cached_we_vote_image.politician_uploaded_profile_image_url_https or \
            image_url_https == cached_we_vote_image.twitter_profile_background_image_url_https or \
            image_url_https == cached_we_vote_image.twitter_profile_banner_url_https or \
            image_url_https == cached_we_vote_image.twitter_profile_image_url_https or \
            image_url_https == cached_we_vote_image.vote_smart_image_url_https or \
            image_url_https == cached_we_vote_image.photo_url_from_ctcl or \
            image_url_https == cached_we_vote_image.photo_url_from_vote_usa or \
            image_url_https == cached_we_vote_image.voter_uploaded_profile_image_url_https or \
            image_url_https == cached_we_vote_image.wikipedia_profile_image_url):
        # DALE 2023-08-05 I know this pattern of sometimes returning a string with the status, and sometimes returning
        #  a dictionary,  is strange, but that is the way it was built.
        cache_image_results = IMAGE_ALREADY_CACHED
    else:
        # Image is not cached so caching it
        cache_image_locally_results = cache_image_locally(
            campaignx_we_vote_id=campaignx_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            facebook_background_image_offset_x=facebook_background_image_offset_x,
            facebook_background_image_offset_y=facebook_background_image_offset_y,
            facebook_user_id=facebook_user_id,
            google_civic_election_id=google_civic_election_id,
            image_url_https=image_url_https,
            is_active_version=is_active_version,
            issue_we_vote_id=issue_we_vote_id,
            kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
            kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
            kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
            kind_of_image_facebook_background=kind_of_image_facebook_background,
            kind_of_image_facebook_profile=kind_of_image_facebook_profile,
            kind_of_image_issue=kind_of_image_issue,
            kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
            kind_of_image_maplight=kind_of_image_maplight,
            kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
            kind_of_image_original=kind_of_image_original,
            kind_of_image_other_source=kind_of_image_other_source,
            kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
            kind_of_image_twitter_background=kind_of_image_twitter_background,
            kind_of_image_twitter_banner=kind_of_image_twitter_banner,
            kind_of_image_twitter_profile=kind_of_image_twitter_profile,
            kind_of_image_vote_smart=kind_of_image_vote_smart,
            kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
            kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
            kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
            maplight_id=maplight_id,
            organization_we_vote_id=organization_we_vote_id,
            other_source=other_source,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            vote_smart_id=vote_smart_id,
            voter_we_vote_id=voter_we_vote_id,
        )
        cache_image_results = cache_image_locally_results['success']

        if cache_image_results:
            set_active_version_false_results = we_vote_image_manager.set_active_version_false_for_other_images(
                campaignx_we_vote_id=campaignx_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                issue_we_vote_id=issue_we_vote_id,
                image_url_https=image_url_https,
                kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
                kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
                kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_issue=kind_of_image_issue,
                kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
                kind_of_image_maplight=kind_of_image_maplight,
                kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
                kind_of_image_other_source=kind_of_image_other_source,
                kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
                kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_vote_smart=kind_of_image_vote_smart,
                kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
                kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
                kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                voter_we_vote_id=voter_we_vote_id,
            )
    log_and_time_cache_action(False, time0, 'cache_image_if_not_cached')
    return cache_image_results


def cache_organization_master_images(organization_we_vote_id):
    """
    Cache all kind of master images for an organization such as profile, background
    :param organization_we_vote_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_organization_master_images')
    cache_all_kind_of_images_results = {
        'organization_we_vote_id':          "",
        'cached_twitter_profile_image':     False,
        'cached_twitter_background_image':  False,
        'cached_twitter_banner_image':      False,
        'cached_facebook_profile_image':    False,
        'cached_facebook_background_image': False
    }
    google_civic_election_id = 0
    twitter_id = None
    organization_manager = OrganizationManager()

    organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
    if not organization_results['organization_found']:
        return cache_all_kind_of_images_results

    organization = organization_results['organization']
    organization_we_vote_id = organization.we_vote_id
    if positive_value_exists(organization_we_vote_id):
        cache_all_kind_of_images_results['organization_we_vote_id'] = organization_we_vote_id
    else:
        return cache_all_kind_of_images_results

    twitter_user_manager = TwitterUserManager()
    twitter_screen_name = ''
    twitter_link_to_organization_results = \
        twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(organization_we_vote_id)
    if twitter_link_to_organization_results['twitter_link_to_organization_found']:
        twitter_link_to_organization = twitter_link_to_organization_results['twitter_link_to_organization']
        twitter_id = twitter_link_to_organization.twitter_id
        twitter_screen_name = twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()

    if not positive_value_exists(twitter_id):
        cache_all_kind_of_images_results = {
            'organization_we_vote_id':          organization_we_vote_id,
            'organization':                     organization,
            'cached_twitter_profile_image':     TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_background_image':  TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_banner_image':      TWITTER_USER_DOES_NOT_EXIST,
        }
        return cache_all_kind_of_images_results

    # Retrieve latest twitter image urls from Twitter
    latest_image_urls_results = retrieve_image_urls_from_twitter(twitter_id)
    twitter_profile_image_url_https = latest_image_urls_results['latest_twitter_profile_image_url']
    twitter_profile_background_image_url_https = latest_image_urls_results['latest_twitter_background_image_url']
    twitter_profile_banner_url_https = latest_image_urls_results['latest_twitter_banner_image_url']

    # Cache all images if not already cached
    if not twitter_profile_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = TWITTER_URL_NOT_FOUND
    else:
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id,
            twitter_profile_image_url_https,
            organization_we_vote_id=organization_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            is_active_version=True,
            kind_of_image_twitter_profile=True,
            kind_of_image_original=True)

    if not twitter_profile_background_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_URL_NOT_FOUND
    else:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = cache_image_if_not_cached(
            google_civic_election_id,
            twitter_profile_background_image_url_https,
            organization_we_vote_id=organization_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            is_active_version=True,
            kind_of_image_twitter_background=True,
            kind_of_image_original=True)

    if not twitter_profile_banner_url_https:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_URL_NOT_FOUND
    else:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_if_not_cached(
            google_civic_election_id,
            twitter_profile_banner_url_https,
            organization_we_vote_id=organization_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            is_active_version=True,
            kind_of_image_twitter_banner=True,
            kind_of_image_original=True)

    log_and_time_cache_action(False, time0, 'cache_organization_master_images')
    return cache_all_kind_of_images_results


def cache_voter_master_images(voter_id):
    """
    Cache all kind of images locally for a voter such as profile, background
    :param voter_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_voter_master_images')
    cache_all_kind_of_images_results = {
        'cached_facebook_background_image':     False,
        'cached_facebook_profile_image':        False,
        'cached_twitter_background_image':      False,
        'cached_twitter_banner_image':          False,
        'cached_twitter_profile_image':         False,
        'cached_voter_uploaded_profile_image':  False,
        'voter_id':                             voter_id,
        'voter_we_vote_id':                     "",
    }
    google_civic_election_id = 0
    twitter_id = None
    facebook_id = None
    voter_address_manager = VoterAddressManager()
    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()

    cached_voter_uploaded_profile_image = VOTER_UPLOADED_PROFILE_IMAGE_DOES_NOT_EXIST

    voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    if not voter_results['voter_found']:
        log_and_time_cache_action(False, time0, 'cache_voter_master_images - voter does not exist')
        return cache_all_kind_of_images_results

    voter = voter_results['voter']
    if positive_value_exists(voter.we_vote_id):
        cache_all_kind_of_images_results['voter_we_vote_id'] = voter.we_vote_id
        # DALE 2018-06-19 I don't see why we need a google_civic_election_id for storing a voter's photos
        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(0, voter_id=voter_id)
        if voter_device_link_results['success']:
            voter_device_link = voter_device_link_results['voter_device_link']
        else:
            voter_device_link = VoterDeviceLink()
        voter_address_results = voter_address_manager.retrieve_address(0, voter_id)
        if voter_address_results['voter_address_found']:
            voter_address = voter_address_results['voter_address']
        else:
            voter_address = None

        if voter.we_vote_hosted_profile_uploaded_image_url_large:
            cached_voter_uploaded_profile_image = True
            cache_all_kind_of_images_results['cached_voter_uploaded_profile_image'] = True,

        from ballot.controllers import choose_election_from_existing_data
        results = choose_election_from_existing_data(voter_device_link, 0, voter_address)
        google_civic_election_id = results['google_civic_election_id']
    else:
        log_and_time_cache_action(False, time0, 'cache_voter_master_images - voter.we_vote_id does not exist')
        return cache_all_kind_of_images_results

    # DALE NOTE 2017-04-23 I don't think we want to use the twitter_id stored in the voter table
    # if positive_value_exists(voter.twitter_id):
    #     twitter_id = voter.twitter_id
    # else:
    twitter_user_manager = TwitterUserManager()
    twitter_screen_name = ''
    twitter_link_to_voter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        voter.we_vote_id, read_only=True)
    if twitter_link_to_voter_results['twitter_link_to_voter_found']:
        twitter_link_to_voter = twitter_link_to_voter_results['twitter_link_to_voter']
        twitter_id = twitter_link_to_voter.twitter_id
        twitter_screen_name = twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()

    # DALE NOTE 2017-04-23 I don't think we want to use the facebook_id stored in the voter table
    # if positive_value_exists(voter.facebook_id):
    #     facebook_id = voter.facebook_id
    # else:
    facebook_manager = FacebookManager()
    facebook_link_to_voter_results = facebook_manager.retrieve_facebook_link_to_voter_from_voter_we_vote_id(
        voter.we_vote_id, read_only=True)
    if facebook_link_to_voter_results['facebook_link_to_voter_found']:
        facebook_id = facebook_link_to_voter_results['facebook_link_to_voter'].facebook_user_id

    if not positive_value_exists(twitter_id) and not positive_value_exists(facebook_id):
        # If we don't have a Twitter or Facebook photo to update, then no need to update this voter further
        cache_all_kind_of_images_results = {
            'cached_facebook_background_image':     FACEBOOK_USER_DOES_NOT_EXIST,
            'cached_facebook_profile_image':        FACEBOOK_USER_DOES_NOT_EXIST,
            'cached_twitter_profile_image':         TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_background_image':      TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_banner_image':          TWITTER_USER_DOES_NOT_EXIST,
            'cached_voter_uploaded_profile_image':  cached_voter_uploaded_profile_image,
            'voter_id':                             voter_id,
            'voter_object':                         voter,
            'voter_we_vote_id':                     voter.we_vote_id,
        }
        log_and_time_cache_action(False, time0, 'cache_voter_master_images - If we dont have a Twitter or '
                                                'Facebook photo to update, then no need to update this voter further')
        return cache_all_kind_of_images_results

    if not positive_value_exists(twitter_id):
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = TWITTER_USER_DOES_NOT_EXIST,
        cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_USER_DOES_NOT_EXIST,
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_USER_DOES_NOT_EXIST,
    else:
        # Retrieve latest twitter image urls from Twitter
        latest_image_urls_results = retrieve_image_urls_from_twitter(twitter_id)
        twitter_profile_image_url_https = latest_image_urls_results['latest_twitter_profile_image_url']
        twitter_profile_background_image_url_https = latest_image_urls_results['latest_twitter_background_image_url']
        twitter_profile_banner_url_https = latest_image_urls_results['latest_twitter_banner_image_url']

        # Cache all images if not already cached
        if not twitter_profile_image_url_https:
            cache_all_kind_of_images_results['cached_twitter_profile_image'] = TWITTER_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_twitter_profile_image'] = cache_image_if_not_cached(
                google_civic_election_id,
                twitter_profile_image_url_https,
                voter_we_vote_id=voter.we_vote_id,
                twitter_id=twitter_id,
                twitter_screen_name=twitter_screen_name,
                is_active_version=True,
                kind_of_image_twitter_profile=True,
                kind_of_image_original=True)

        if not twitter_profile_background_image_url_https:
            cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_twitter_background_image'] = cache_image_if_not_cached(
                google_civic_election_id,
                twitter_profile_background_image_url_https,
                voter_we_vote_id=voter.we_vote_id,
                twitter_id=twitter_id,
                twitter_screen_name=twitter_screen_name,
                is_active_version=True,
                kind_of_image_twitter_background=True,
                kind_of_image_original=True)

        if not twitter_profile_banner_url_https:
            cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_if_not_cached(
                google_civic_election_id,
                twitter_profile_banner_url_https,
                voter_we_vote_id=voter.we_vote_id,
                twitter_id=twitter_id,
                twitter_screen_name=twitter_screen_name,
                is_active_version=True,
                kind_of_image_twitter_banner=True,
                kind_of_image_original=True)

    if not positive_value_exists(facebook_id):
        cache_all_kind_of_images_results['cached_facebook_profile_image'] = FACEBOOK_USER_DOES_NOT_EXIST,
        cache_all_kind_of_images_results['cached_facebook_background_image'] = FACEBOOK_USER_DOES_NOT_EXIST,
    else:
        # Retrieve latest facebook image urls from Facebook
        latest_image_urls_results = retrieve_facebook_image_url(facebook_id)
        facebook_profile_image_url_https = latest_image_urls_results['facebook_profile_image_url']
        facebook_background_image_url_https = latest_image_urls_results['facebook_background_image_url']

        # Cache all images if not already cached
        if not facebook_profile_image_url_https:
            cache_all_kind_of_images_results['cached_facebook_profile_image'] = FACEBOOK_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_facebook_profile_image'] = cache_image_if_not_cached(
                google_civic_election_id,
                facebook_profile_image_url_https,
                voter_we_vote_id=voter.we_vote_id,
                facebook_user_id=facebook_id,
                is_active_version=True,
                kind_of_image_facebook_profile=True,
                kind_of_image_original=True)

        if not facebook_background_image_url_https:
            cache_all_kind_of_images_results['cached_facebook_background_image'] = FACEBOOK_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_facebook_background_image'] = cache_image_if_not_cached(
                google_civic_election_id,
                facebook_background_image_url_https,
                voter_we_vote_id=voter.we_vote_id,
                facebook_user_id=facebook_id,
                is_active_version=True,
                kind_of_image_facebook_background=True,
                kind_of_image_original=True)

    log_and_time_cache_action(False, time0, 'cache_voter_master_images - final exit')
    return cache_all_kind_of_images_results


def cache_image_locally(
        campaignx_we_vote_id=None,
        candidate_we_vote_id=None,
        facebook_background_image_offset_x=False,
        facebook_background_image_offset_y=False,
        facebook_user_id=None,
        google_civic_election_id=0,
        image_url_https='',
        is_active_version=False,
        issue_we_vote_id=None,
        kind_of_image_ballotpedia_profile=False,
        kind_of_image_campaignx_photo=False,
        kind_of_image_ctcl_profile=False,
        kind_of_image_facebook_background=False,
        kind_of_image_facebook_profile=False,
        kind_of_image_issue=False,
        kind_of_image_large=False,
        kind_of_image_linkedin_profile=False,
        kind_of_image_maplight=False,
        kind_of_image_medium=False,
        kind_of_image_organization_uploaded_profile=False,
        kind_of_image_original=False,
        kind_of_image_other_source=False,
        kind_of_image_politician_uploaded_profile=False,
        kind_of_image_tiny=False,
        kind_of_image_twitter_profile=False,
        kind_of_image_twitter_background=False,
        kind_of_image_twitter_banner=False,
        kind_of_image_vote_smart=False,
        kind_of_image_vote_usa_profile=False,
        kind_of_image_voter_uploaded_profile=False,
        kind_of_image_wikipedia_profile=False,
        maplight_id=None,
        organization_we_vote_id=None,
        other_source=None,
        politician_we_vote_id=None,
        representative_we_vote_id=None,
        twitter_id=None,
        twitter_screen_name=None,
        vote_smart_id=None,
        voter_we_vote_id=None):
    """
    Cache one type of image
    :param campaignx_we_vote_id:
    :param candidate_we_vote_id:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :param facebook_user_id:
    :param google_civic_election_id:
    :param image_url_https:
    :param is_active_version:
    :param issue_we_vote_id:
    :param kind_of_image_ballotpedia_profile:
    :param kind_of_image_campaignx_photo:
    :param kind_of_image_ctcl_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_issue:
    :param kind_of_image_large:
    :param kind_of_image_linkedin_profile:
    :param kind_of_image_maplight:
    :param kind_of_image_medium:
    :param kind_of_image_organization_uploaded_profile:
    :param kind_of_image_original:
    :param kind_of_image_other_source:
    :param kind_of_image_politician_uploaded_profile:
    :param kind_of_image_tiny:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_vote_smart:
    :param kind_of_image_vote_usa_profile:
    :param kind_of_image_voter_uploaded_profile:
    :param kind_of_image_wikipedia_profile:
    :param maplight_id:
    :param organization_we_vote_id:
    :param other_source:
    :param politician_we_vote_id:
    :param representative_we_vote_id:
    :param twitter_id:
    :param twitter_screen_name:
    :param vote_smart_id:
    :param voter_we_vote_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_image_locally')
    we_vote_parent_image_id = None

    success = False
    status = ''
    we_vote_image_created = False
    image_url_valid = False
    image_stored_from_source = False
    image_stored_locally = False
    image_stored_to_aws = False
    image_versions = []

    we_vote_image_manager = WeVoteImageManager()

    # create we_vote_image entry with voter_we_vote_id and google_civic_election_id and kind_of_image
    # Blank wevoteimage created at the point, with no urls
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        campaignx_we_vote_id=campaignx_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        facebook_background_image_offset_x=facebook_background_image_offset_x,
        facebook_background_image_offset_y=facebook_background_image_offset_y,
        google_civic_election_id=google_civic_election_id,
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_large=kind_of_image_large,
        kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_medium=kind_of_image_medium,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_original=kind_of_image_original,
        kind_of_image_other_source=kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        kind_of_image_tiny=kind_of_image_tiny,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        representative_we_vote_id=representative_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
            'image_url_https':              '',
        }
        log_and_time_cache_action(False, time0, 'cache_image_locally -- create_we_vote_image_results, was not saved')
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']

    # Image url validation and get source image properties
    analyze_source_images_results = analyze_source_images(
        twitter_id=twitter_id,
        twitter_screen_name=twitter_screen_name,
        facebook_user_id=facebook_user_id,
        maplight_id=maplight_id,
        vote_smart_id=vote_smart_id,
        image_url_https=image_url_https,
        kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_other_source=kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
        other_source=other_source)

    if 'analyze_image_url_results' not in analyze_source_images_results or \
            'image_url_valid' not in analyze_source_images_results['analyze_image_url_results'] or not \
            analyze_source_images_results['analyze_image_url_results']['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
            'image_url_https':              '',
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(False, time0, 'cache_image_locally -- analyze_image_url_results problem')
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID "

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        campaignx_we_vote_id=campaignx_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_original=kind_of_image_original,
        kind_of_image_other_source=kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        representative_we_vote_id=representative_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )
    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)
    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    if kind_of_image_ballotpedia_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_ballotpedia_info(
            we_vote_image, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_ballotpedia_profile, image_url_valid)
    elif kind_of_image_campaignx_photo:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_campaignx_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['analyze_image_url_results']['image_width'],
            image_height=analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
    elif kind_of_image_ctcl_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_ctcl_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['analyze_image_url_results']['image_width'],
            image_height=analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
    elif kind_of_image_facebook_profile or kind_of_image_facebook_background:
        # image url is valid so store source image of facebook to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_facebook_info(
            we_vote_image, facebook_user_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_facebook_profile,
            kind_of_image_facebook_background, image_url_valid)
    elif kind_of_image_linkedin_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_linkedin_info(
            we_vote_image, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_linkedin_profile, image_url_valid)
    elif kind_of_image_maplight:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_maplight_info(
            we_vote_image, maplight_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_maplight, image_url_valid)
    elif kind_of_image_other_source:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_other_source_info(
            we_vote_image, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'], other_source,
            image_url_https, same_day_image_version, kind_of_image_other_source, image_url_valid)
    elif kind_of_image_organization_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_organization_uploaded_profile_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['analyze_image_url_results']['image_width'],
            image_height=analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https=image_url_https,
            image_url_valid=image_url_valid,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_politician_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_politician_uploaded_profile_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['analyze_image_url_results']['image_width'],
            image_height=analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https=image_url_https,
            image_url_valid=image_url_valid,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_twitter_profile or kind_of_image_twitter_background or kind_of_image_twitter_banner:
        # image url is valid so store source image of twitter to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(
            we_vote_image, twitter_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_twitter_profile,
            kind_of_image_twitter_background, kind_of_image_twitter_banner, image_url_valid)
    elif kind_of_image_vote_smart:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_vote_smart_info(
            we_vote_image, vote_smart_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_vote_smart, image_url_valid)
    elif kind_of_image_vote_usa_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_vote_usa_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['analyze_image_url_results']['image_width'],
            image_height=analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
    elif kind_of_image_voter_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_voter_uploaded_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['analyze_image_url_results']['image_width'],
            image_height=analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
    elif kind_of_image_wikipedia_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_wikipedia_info(
            we_vote_image, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_wikipedia_profile, image_url_valid)

    status += " " + save_source_info_results['status']
    if save_source_info_results['success']:
        image_stored_from_source = True
        date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                       we_vote_image.date_image_saved.day,
                                                       year=we_vote_image.date_image_saved.year)
        # ex twitter_profile_image_master-2017210_1_48x48.png
        analyze_image_url_results = analyze_source_images_results['analyze_image_url_results']
        image_width = analyze_image_url_results['image_width'] if 'image_width' in analyze_image_url_results else 0
        image_height = analyze_image_url_results['image_height'] if 'image_height' in analyze_image_url_results else 0
        image_format = analyze_image_url_results['image_format'] if 'image_format' in analyze_image_url_results else ''
        we_vote_image_file_name = \
            "{image_type}_{master_image}-{date_image_saved}_{counter}_" \
            "{image_width}x{image_height}.{image_format}" \
            "".format(
                image_type=analyze_source_images_results['image_type'],
                master_image=MASTER_IMAGE,
                date_image_saved=date_image_saved,
                counter=str(same_day_image_version),
                image_width=str(image_width),
                image_height=str(image_height),
                image_format=str(image_format))

        if voter_we_vote_id:
            we_vote_image_file_location = voter_we_vote_id + "/" + we_vote_image_file_name
        elif campaignx_we_vote_id:
            we_vote_image_file_location = campaignx_we_vote_id + "/" + we_vote_image_file_name
        elif candidate_we_vote_id:
            we_vote_image_file_location = candidate_we_vote_id + "/" + we_vote_image_file_name
        elif organization_we_vote_id:
            we_vote_image_file_location = organization_we_vote_id + "/" + we_vote_image_file_name
        elif politician_we_vote_id:
            we_vote_image_file_location = politician_we_vote_id + "/" + we_vote_image_file_name
        elif representative_we_vote_id:
            we_vote_image_file_location = representative_we_vote_id + "/" + we_vote_image_file_name
        else:
            we_vote_image_file_location = we_vote_image_file_name

        image_stored_locally = we_vote_image_manager.store_image_locally(
            analyze_source_images_results['image_url_https'], we_vote_image_file_name)

        if not image_stored_locally:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_LOCALLY ",
                'we_vote_image_created':        we_vote_image_created,
                'image_url_valid':              image_url_valid,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         False,
                'image_stored_to_aws':          image_stored_to_aws,
                'image_url_https':              '',
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            log_and_time_cache_action(False, time0, 'cache_image_locally -- IMAGE_NOT_STORED_LOCALLY problem')
            return error_results

        status += " IMAGE_STORED_LOCALLY "
        image_stored_to_aws = we_vote_image_manager.store_image_to_aws(
            we_vote_image_file_name=we_vote_image_file_name,
            we_vote_image_file_location=we_vote_image_file_location,
            image_format=analyze_source_images_results['analyze_image_url_results']['image_format'])
        if not image_stored_to_aws:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_TO_AWS ",
                'we_vote_image_created':        we_vote_image_created,
                'image_url_valid':              image_url_valid,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         image_stored_locally,
                'image_stored_to_aws':          False,
                'image_url_https':              '',
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            log_and_time_cache_action(False, time0, 'cache_image_locally -- IMAGE_NOT_STORED_TO_AWS problem')
            return error_results
        we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                            "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                      we_vote_image_file_location=we_vote_image_file_location)
        # logger.error('(Ok) New image created in cache_image_locally we_vote_image_url: %s' % we_vote_image_url)
        save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(
            we_vote_image,
            we_vote_image_url=we_vote_image_url,
            we_vote_image_file_location=we_vote_image_file_location,
            we_vote_parent_image_id=we_vote_parent_image_id,
            is_active_version=is_active_version)
        status += " IMAGE_STORED_TO_AWS " + save_aws_info['status'] + " "
        success = save_aws_info['success']
        if not success:
            error_results = {
                'success':                  success,
                'status':                   status,
                'we_vote_image_created':    we_vote_image_created,
                'image_url_valid':          image_url_valid,
                'image_stored_from_source': image_stored_from_source,
                'image_stored_locally':     image_stored_locally,
                'image_stored_to_aws':      image_stored_to_aws,
                'image_url_https':          we_vote_image_url,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            log_and_time_cache_action(False, time0, 'cache_image_locally -- IMAGE_STORED_TO_AWS with error')
            return error_results

    else:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     False,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
            'image_url_https':              '',
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(False, time0, 'cache_image_locally -- save_source_info_results problem')
        save_source_info_results
        return error_results

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_locally':         image_stored_locally,
        'image_stored_to_aws':          image_stored_to_aws,
        'image_url_https':              we_vote_image_url,
    }
    log_and_time_cache_action(False, time0, 'cache_image_locally -- final')
    return results


def retrieve_facebook_image_url(facebook_user_id):
    """
    Retrieve facebook profile url from Facebook and background url from FacebookUser table.
    :param facebook_user_id:
    :return:
    """
    results = {
        'facebook_profile_image_url':       None,
        'facebook_background_image_url':    None
    }
    facebook_manager = FacebookManager()

    get_url = "https://graph.facebook.com/v3.1/{facebook_user_id}/picture?width=200&height=200"\
        .format(facebook_user_id=facebook_user_id)
    response = requests.get(get_url)
    if response.status_code == HTTP_OK:
        # new facebook profile image url found
        results['facebook_profile_image_url'] = response.url

    facebook_user_results = facebook_manager.retrieve_facebook_user_by_facebook_user_id(facebook_user_id)
    if facebook_user_results['facebook_user_found']:
        results['facebook_background_image_url'] = \
            facebook_user_results['facebook_user'].facebook_background_image_url_https

    return results


def retrieve_and_save_ballotpedia_candidate_images(candidate):
    from import_export_ballotpedia.controllers import retrieve_ballotpedia_candidate_image_from_api
    status = ""
    candidate_manager = CandidateManager()
    politician_manager = PoliticianManager()

    if not candidate:
        status += "BALLOTPEDIA_CANDIDATE_IMAGE_NOT_RETRIEVED-CANDIDATE_MISSING "
        results = {
            'success':      False,
            'status':       status,
            'candidate':    None,
        }
        return results

    if positive_value_exists(candidate.ballotpedia_image_id):
        status += "BALLOTPEDIA_CANDIDATE_IMAGE-REACHING_OUT_TO_BALLOTPEDIA "
        results = retrieve_ballotpedia_candidate_image_from_api(
            candidate.ballotpedia_image_id, candidate.google_civic_election_id)

        if results['success']:
            status += "BALLOTPEDIA_CANDIDATE_IMAGE_RETRIEVED "

            # Get original image url for cache original size image
            ballotpedia_profile_image_url_https = results['profile_image_url_https']

            cache_results = cache_master_and_resized_image(
                candidate_id=candidate.id,
                candidate_we_vote_id=candidate.we_vote_id,
                ballotpedia_profile_image_url=ballotpedia_profile_image_url_https,
                image_source=IMAGE_SOURCE_BALLOTPEDIA)
            cached_ballotpedia_image_url_https = cache_results['cached_ballotpedia_image_url_https']
            we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
            we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

            save_candidate_results = candidate_manager.update_candidate_ballotpedia_image_details(
                candidate,
                cached_ballotpedia_image_url_https,
                we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny)
            candidate = save_candidate_results['candidate']
            # Need to update voter ballotpedia details for the candidate in future
            # TODO: Replace with update_politician_details_from_candidate in politician/controllers.py
            save_politician_details_results = politician_manager.update_politician_details_from_candidate(
                candidate)
            save_position_from_candidate_results = update_all_position_details_from_candidate(candidate)
    else:
        status += "BALLOTPEDIA_CANDIDATE_IMAGE-CLEARING_DETAILS "
        # save_candidate_results = candidate_manager.clear_candidate_twitter_details(
        # candidate)

    results = {
        'success':      True,
        'status':       status,
        'candidate':    candidate,
    }
    return results


def retrieve_twitter_image_url(twitter_id, kind_of_image_twitter_profile=False,
                               kind_of_image_twitter_background=False,
                               kind_of_image_twitter_banner=False):
    """
    Retrieve twitter image urls from TwitterUser table.
    :param twitter_id:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    twitter_image_url = None
    twitter_user_manager = TwitterUserManager()

    twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_id)
    if twitter_user_results['twitter_user_found']:
        if kind_of_image_twitter_profile:
            twitter_image_url = twitter_user_results['twitter_user'].twitter_profile_image_url_https
        elif kind_of_image_twitter_background:
            twitter_image_url = twitter_user_results['twitter_user'].twitter_profile_background_image_url_https
        elif kind_of_image_twitter_banner:
            twitter_image_url = twitter_user_results['twitter_user'].twitter_profile_banner_url_https
    return twitter_user_results['twitter_user'], twitter_image_url


def retrieve_image_urls_from_twitter(twitter_id):
    """
    Retrieve latest twitter profile, background and banner image url from twitter API call
    :param twitter_id:
    :return:
    """
    latest_twitter_profile_image_url = None
    latest_twitter_background_image_url = None
    latest_twitter_banner_image_url = None

    from twitter.models import TwitterApiCounterManager
    twitter_api_counter_manager = TwitterApiCounterManager()
    twitter_user_info_results = retrieve_twitter_user_info(
        twitter_id,
        twitter_handle='',
        twitter_api_counter_manager=twitter_api_counter_manager,
        parent='parent = retrieve_image_urls_from_twitter'
    )
    if 'profile_image_url' in twitter_user_info_results['twitter_dict'] \
            and twitter_user_info_results['twitter_dict']['profile_image_url']:
        # new twitter image url found
        latest_twitter_profile_image_url = twitter_user_info_results['twitter_dict'][
            'profile_image_url']

    # 2024-01-27 Twitter API v2 doesn't return profile_background_image_url_https any more
    # if 'profile_background_image_url_https' in twitter_user_info_results['twitter_dict'] \
    #         and twitter_user_info_results['twitter_dict']['profile_background_image_url_https']:
    #     # new twitter image url found
    #     latest_twitter_background_image_url = twitter_user_info_results['twitter_dict'][
    #         'profile_background_image_url_https']

    # 2024-01-27 Twitter API v2 doesn't return profile_banner_url any more
    # if 'profile_banner_url' in twitter_user_info_results['twitter_dict'] \
    #         and twitter_user_info_results['twitter_dict']['profile_banner_url']:
    #     # new twitter image url found
    #     latest_twitter_banner_image_url = twitter_user_info_results['twitter_dict'][
    #         'profile_banner_url']

    results = {
        'latest_twitter_profile_image_url':     latest_twitter_profile_image_url,
        'latest_twitter_background_image_url':  latest_twitter_background_image_url,
        'latest_twitter_banner_image_url':      latest_twitter_banner_image_url,
    }
    return results


def analyze_source_images(
        twitter_id=0,
        twitter_screen_name='',
        facebook_user_id=0,
        maplight_id=0,
        vote_smart_id=0,
        image_url_https="",
        kind_of_image_ballotpedia_profile=False,
        kind_of_image_campaignx_photo=False,
        kind_of_image_ctcl_profile=False,
        kind_of_image_facebook_background=False,
        kind_of_image_facebook_profile=False,
        kind_of_image_linkedin_profile=False,
        kind_of_image_maplight=False,
        kind_of_image_organization_uploaded_profile=False,
        kind_of_image_other_source=False,
        kind_of_image_politician_uploaded_profile=False,
        kind_of_image_twitter_background=False,
        kind_of_image_twitter_banner=False,
        kind_of_image_twitter_profile=False,
        kind_of_image_vote_smart=False,
        kind_of_image_vote_usa_profile=False,
        kind_of_image_voter_uploaded_profile=False,
        kind_of_image_wikipedia_profile=False,
        other_source=False):
    """

    :param twitter_id:
    :param twitter_screen_name:
    :param facebook_user_id:
    :param maplight_id:
    :param vote_smart_id:
    :param image_url_https:
    :param kind_of_image_ballotpedia_profile:
    :param kind_of_image_campaignx_photo:
    :param kind_of_image_ctcl_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_linkedin_profile:
    :param kind_of_image_maplight:
    :param kind_of_image_organization_uploaded_profile:
    :param kind_of_image_other_source:
    :param kind_of_image_politician_uploaded_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_vote_smart:
    :param kind_of_image_vote_usa_profile:
    :param kind_of_image_voter_uploaded_profile:
    :param kind_of_image_wikipedia_profile:
    :param other_source:
    :return:
    """
    image_type = None
    if kind_of_image_ballotpedia_profile:
        image_type = BALLOTPEDIA_IMAGE_NAME
    elif kind_of_image_campaignx_photo:
        image_type = CAMPAIGNX_PHOTO_IMAGE_NAME
    elif kind_of_image_ctcl_profile:
        image_type = CTCL_PROFILE_IMAGE_NAME
    elif kind_of_image_facebook_background:
        image_type = FACEBOOK_BACKGROUND_IMAGE_NAME
    elif kind_of_image_facebook_profile:
        image_type = FACEBOOK_PROFILE_IMAGE_NAME
    elif kind_of_image_linkedin_profile:
        image_type = LINKEDIN_IMAGE_NAME
    elif kind_of_image_maplight:
        image_type = MAPLIGHT_IMAGE_NAME
    elif kind_of_image_organization_uploaded_profile:
        image_type = ORGANIZATION_UPLOADED_PROFILE_IMAGE_NAME
    elif kind_of_image_other_source:
        image_type = other_source
    elif kind_of_image_politician_uploaded_profile:
        image_type = POLITICIAN_UPLOADED_PROFILE_IMAGE_NAME
    elif kind_of_image_twitter_background:
        image_type = TWITTER_BACKGROUND_IMAGE_NAME
    elif kind_of_image_twitter_banner:
        image_type = TWITTER_BANNER_IMAGE_NAME
    elif kind_of_image_twitter_profile:
        image_type = TWITTER_PROFILE_IMAGE_NAME
    elif kind_of_image_vote_smart:
        image_type = VOTE_SMART_IMAGE_NAME
    elif kind_of_image_vote_usa_profile:
        image_type = VOTE_USA_PROFILE_IMAGE_NAME
    elif kind_of_image_voter_uploaded_profile:
        image_type = VOTER_UPLOADED_IMAGE_NAME
    elif kind_of_image_wikipedia_profile:
        image_type = WIKIPEDIA_IMAGE_NAME

    analyze_image_url_results = analyze_remote_url(image_url_https)
    results = {
        'twitter_id':                   twitter_id,
        'twitter_screen_name':          twitter_screen_name,
        'facebook_user_id':             facebook_user_id,
        'maplight_id':                  maplight_id,
        'vote_smart_id':                vote_smart_id,
        'image_url_https':              image_url_https,
        'image_type':                   image_type,
        'analyze_image_url_results':    analyze_image_url_results
    }
    return results


def create_resized_images_for_all_organizations():
    """
    Create resized images for all organizations
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'create_resized_images_for_all_organizations')
    create_all_resized_images_results = []
    we_vote_image_list = WeVoteImage.objects.all()
    # TODO Limit this to organizations only

    for we_vote_image in we_vote_image_list:
        # Iterate through all cached images
        create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
        create_all_resized_images_results.append(create_resized_images_results)
    log_and_time_cache_action(True, time0, 'create_resized_images_for_all_organizations')
    return create_all_resized_images_results


def create_resized_images_for_all_voters():
    """
    Create resized images for all voters
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'create_resized_images_for_all_voters')
    create_all_resized_images_results = []
    we_vote_image_list = WeVoteImage.objects.all()
    # TODO Limit this to voters only

    for we_vote_image in we_vote_image_list:
        # Iterate through all cached images
        create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
        create_all_resized_images_results.append(create_resized_images_results)
    log_and_time_cache_action(False, time0, 'create_resized_images_for_all_voters')
    return create_all_resized_images_results


def delete_cached_images_for_candidate(candidate):
    original_twitter_profile_image_url_https = None
    original_twitter_profile_background_image_url_https = None
    original_twitter_profile_banner_url_https = None
    delete_image_count = 0
    not_deleted_image_count = 0

    we_vote_image_list = retrieve_all_images_for_one_candidate(candidate.we_vote_id)
    if len(we_vote_image_list) > 0:
        we_vote_image_manager = WeVoteImageManager()
        for we_vote_image in we_vote_image_list:
            if we_vote_image.kind_of_image_twitter_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_image_url_https = we_vote_image.twitter_profile_image_url_https
            if we_vote_image.kind_of_image_twitter_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_background_image_url_https = \
                    we_vote_image.twitter_profile_background_image_url_https
            if we_vote_image.kind_of_image_twitter_banner and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_banner_url_https = we_vote_image.twitter_profile_banner_url_https

        # Reset CandidateCampaign with original image details
        candidate_manager = CandidateManager()
        reset_candidate_image_results = candidate_manager.reset_candidate_image_details(
            candidate, original_twitter_profile_image_url_https, original_twitter_profile_background_image_url_https,
            original_twitter_profile_banner_url_https)

        # Reset Twitter User Table with original image details
        twitter_user_manager = TwitterUserManager()
        reset_twitter_user_image_results = twitter_user_manager.reset_twitter_user_image_details(
            candidate.twitter_user_id, original_twitter_profile_image_url_https,
            original_twitter_profile_background_image_url_https, original_twitter_profile_banner_url_https)

        # Reset Position Table with original image details
        reset_position_image_results = reset_all_position_image_details_from_candidate(
            candidate, original_twitter_profile_image_url_https)

        # Reset Politician Table with original image details
        politician_manager = PoliticianManager()
        reset_politician_image_results = politician_manager.reset_politician_image_details_from_candidate(
            candidate, original_twitter_profile_image_url_https, original_twitter_profile_background_image_url_https,
            original_twitter_profile_banner_url_https)

        if reset_candidate_image_results['success']:
            for we_vote_image in we_vote_image_list:
                # Delete image from AWS
                image_deleted_from_aws = we_vote_image_manager.delete_image_from_aws(
                    we_vote_image.we_vote_image_file_location)

                delete_result = we_vote_image_manager.delete_we_vote_image(we_vote_image)
                if delete_result['success']:
                    delete_image_count += 1
                else:
                    not_deleted_image_count += 1

        success = True
        status = "DELETED_CACHED_IMAGES_FOR_CANDIDATE"
    else:
        success = False
        status = "NO_IMAGE_FOUND_FOR_CANDIDATE"

    results = {
        'success':              success,
        'status':               status,
        'delete_image_count':   delete_image_count,
        'not_deleted_image_count':  not_deleted_image_count,
    }
    return results


def delete_cached_images_for_issue(issue):
    delete_image_count = 0
    not_deleted_image_count = 0

    we_vote_image_list = retrieve_all_images_for_one_issue(issue.we_vote_id)
    if len(we_vote_image_list) > 0:
        we_vote_image_manager = WeVoteImageManager()

        # Reset Issue with original image details
        issue_manager = IssueManager()
        reset_candidate_image_results = issue_manager.reset_issue_image_details(
            issue, issue_image_url='')

        if reset_candidate_image_results['success']:
            for we_vote_image in we_vote_image_list:
                # Delete image from AWS
                image_deleted_from_aws = we_vote_image_manager.delete_image_from_aws(
                    we_vote_image.we_vote_image_file_location)

                delete_result = we_vote_image_manager.delete_we_vote_image(we_vote_image)
                if delete_result['success']:
                    delete_image_count += 1
                else:
                    not_deleted_image_count += 1

        success = True
        status = "DELETED_CACHED_IMAGES_FOR_ISSUE"
    else:
        success = False
        status = "NO_IMAGE_FOUND_FOR_ISSUE"

    results = {
        'success':                  success,
        'status':                   status,
        'delete_image_count':       delete_image_count,
        'not_deleted_image_count':  not_deleted_image_count,
    }
    return results


def delete_cached_images_for_organization(organization):
    original_twitter_profile_image_url_https = None
    original_twitter_profile_background_image_url_https = None
    original_twitter_profile_banner_url_https = None
    original_facebook_profile_image_url_https = None
    original_facebook_background_image_url_https = None
    delete_image_count = 0
    not_deleted_image_count = 0

    we_vote_image_list = retrieve_all_images_for_one_organization(organization.we_vote_id)
    if len(we_vote_image_list) > 0:
        we_vote_image_manager = WeVoteImageManager()
        for we_vote_image in we_vote_image_list:
            if we_vote_image.kind_of_image_facebook_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_background_image_url_https = we_vote_image.facebook_background_image_url_https
            if we_vote_image.kind_of_image_facebook_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_profile_image_url_https = we_vote_image.facebook_profile_image_url_https
            if we_vote_image.kind_of_image_twitter_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_background_image_url_https = \
                    we_vote_image.twitter_profile_background_image_url_https
            if we_vote_image.kind_of_image_twitter_banner and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_banner_url_https = we_vote_image.twitter_profile_banner_url_https
            if we_vote_image.kind_of_image_twitter_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_image_url_https = we_vote_image.twitter_profile_image_url_https

        # Reset Organization with original image details
        organization_manager = OrganizationManager()
        reset_organization_image_results = organization_manager.reset_organization_image_details(
            organization, original_twitter_profile_image_url_https, original_twitter_profile_background_image_url_https,
            original_twitter_profile_banner_url_https, original_facebook_profile_image_url_https)

        # Reset Twitter User Table with original image details
        twitter_user_manager = TwitterUserManager()
        reset_twitter_user_image_results = twitter_user_manager.reset_twitter_user_image_details(
            organization.twitter_user_id, original_twitter_profile_image_url_https,
            original_twitter_profile_background_image_url_https, original_twitter_profile_banner_url_https)

        # Reset Position Table with original image details
        reset_position_image_results = reset_position_entered_image_details_from_organization(
            organization, original_twitter_profile_image_url_https, original_facebook_profile_image_url_https)

        # Reset Voter Guide table with original image details
        voter_guide_manager = VoterGuideManager()
        reset_voter_guide_image_results = voter_guide_manager.reset_voter_guide_image_details(
            organization, original_twitter_profile_image_url_https, original_facebook_profile_image_url_https)

        # Reset Voter with original image details
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization.we_vote_id)
        voter = voter_results['voter']
        if voter_results['voter_found']:
            reset_voter_image_results = voter_manager.reset_voter_image_details(
                voter, original_twitter_profile_image_url_https, original_facebook_profile_image_url_https)

        # Reset Facebook User Table with original image details
        facebook_manager = FacebookManager()
        reset_facebook_user_image_results = facebook_manager.reset_facebook_user_image_details(
            organization.facebook_id, original_facebook_profile_image_url_https,
            original_facebook_background_image_url_https)

        if reset_organization_image_results['success']:
            for we_vote_image in we_vote_image_list:
                # Delete image from AWS
                image_deleted_from_aws = we_vote_image_manager.delete_image_from_aws(
                    we_vote_image.we_vote_image_file_location)

                delete_result = we_vote_image_manager.delete_we_vote_image(we_vote_image)
                if delete_result['success']:
                    delete_image_count += 1
                else:
                    not_deleted_image_count += 1

        success = True
        status = "DELETED_CACHED_IMAGES_FOR_CANDIDATE"
    else:
        success = False
        status = "NO_IMAGE_FOUND_FOR_CANDIDATE"

    results = {
        'success':                  success,
        'status':                   status,
        'delete_image_count':       delete_image_count,
        'not_deleted_image_count':  not_deleted_image_count,
    }
    return results


def delete_cached_images_for_voter(voter):
    time0 = log_and_time_cache_action(True, 0, 'delete_cached_images_for_voter')
    original_twitter_profile_image_url_https = None
    original_twitter_profile_background_image_url_https = None
    original_twitter_profile_banner_url_https = None
    original_facebook_profile_image_url_https = None
    original_facebook_background_image_url_https = None

    delete_image_count = 0
    not_deleted_image_count = 0

    we_vote_image_list = retrieve_all_images_for_one_voter(voter.id)
    if len(we_vote_image_list) > 0:
        we_vote_image_manager = WeVoteImageManager()
        for we_vote_image in we_vote_image_list:
            if we_vote_image.kind_of_image_facebook_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_profile_image_url_https = we_vote_image.facebook_profile_image_url_https
            if we_vote_image.kind_of_image_facebook_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_background_image_url_https = we_vote_image.facebook_background_image_url_https
            if we_vote_image.kind_of_image_twitter_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_background_image_url_https = \
                    we_vote_image.twitter_profile_background_image_url_https
            if we_vote_image.kind_of_image_twitter_banner and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_banner_url_https = we_vote_image.twitter_profile_banner_url_https
            if we_vote_image.kind_of_image_twitter_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_twitter_profile_image_url_https = we_vote_image.twitter_profile_image_url_https

        # Reset Voter with original image details
        voter_manager = VoterManager()
        reset_voter_image_results = voter_manager.reset_voter_image_details(
            voter, original_twitter_profile_image_url_https, original_facebook_profile_image_url_https)

        # Reset Twitter User Table with original image details
        twitter_user_manager = TwitterUserManager()
        reset_twitter_user_image_results = twitter_user_manager.reset_twitter_user_image_details(
            voter.twitter_id, original_twitter_profile_image_url_https,
            original_twitter_profile_background_image_url_https, original_twitter_profile_banner_url_https)

        # Reset Organization with original image details
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization(0, '', '', voter.twitter_id)
        organization = organization_results['organization']
        if organization_results['organization_found']:
            reset_organization_image_results = organization_manager.reset_organization_image_details(
                organization, original_twitter_profile_image_url_https,
                original_twitter_profile_background_image_url_https, original_twitter_profile_banner_url_https,
                original_facebook_profile_image_url_https)

        # Reset Position Table with original image details
        reset_position_image_results = reset_position_for_friends_image_details_from_voter(
            voter, original_twitter_profile_image_url_https, original_facebook_profile_image_url_https)

        # Reset Facebook User Table with original image details
        facebook_manager = FacebookManager()
        reset_facebook_user_image_results = facebook_manager.reset_facebook_user_image_details(
            voter.facebook_id, original_facebook_profile_image_url_https, original_facebook_background_image_url_https)

        if reset_voter_image_results['success']:
            for we_vote_image in we_vote_image_list:
                # Delete image from AWS
                image_deleted_from_aws = we_vote_image_manager.delete_image_from_aws(
                    we_vote_image.we_vote_image_file_location)

                delete_result = we_vote_image_manager.delete_we_vote_image(we_vote_image)
                if delete_result['success']:
                    delete_image_count += 1
                else:
                    not_deleted_image_count += 1

        success = True
        status = "DELETED_CACHED_IMAGES_FOR_VOTER"
    else:
        success = False
        status = "NO_IMAGE_FOUND_FOR_VOTER"

    results = {
        'success':                  success,
        'status':                   status,
        'delete_image_count':       delete_image_count,
        'not_deleted_image_count':  not_deleted_image_count,
    }
    log_and_time_cache_action(True, time0, 'delete_cached_images_for_voter')
    return results


def delete_stored_images_for_voter(voter):
    """
    This method actually removes all image data from the Voter, Facebook, and Twitter tables for this voter
    Call delete_cached_images_for_voter() before calling this one, to remove all the cached images from AWS, otherwise
    the cached images will stay in AWS as unreferenced wasted storage
    """
    time0 = log_and_time_cache_action(True, 0, 'delete_stored_images_for_voter')
    success = False

    # Delete Voter images
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_we_vote_id(voter.we_vote_id)
    voter = voter_results['voter']
    if voter_results['voter_found']:
        voter.facebook_profile_image_url_https = ''
        voter.twitter_profile_image_url_https = ''
        voter.we_vote_hosted_profile_image_url_large = ''
        voter.we_vote_hosted_profile_image_url_medium = ''
        voter.we_vote_hosted_profile_image_url_tiny = ''
        voter.we_vote_hosted_profile_uploaded_image_url_large = ''
        voter.we_vote_hosted_profile_uploaded_image_url_medium = ''
        voter.we_vote_hosted_profile_uploaded_image_url_tiny = ''
        voter.save()
        success = True

    # Delete Twitter User Table images
    if positive_value_exists(voter.twitter_id):
        twitter_user_manager = TwitterUserManager()
        twitter_results = twitter_user_manager.retrieve_twitter_user(voter.twitter_id)
        twitter_user_found = twitter_results['twitter_user_found']
        twitter_user = twitter_results['twitter_user']
        if twitter_user_found:
            twitter_user.twitter_profile_image_url_https = ''
            twitter_user.twitter_profile_background_image_url_https = ''
            twitter_user.twitter_profile_banner_url_https = ''
            twitter_user.we_vote_hosted_profile_image_url_large = ''
            twitter_user.we_vote_hosted_profile_image_url_medium = ''
            twitter_user.we_vote_hosted_profile_image_url_tiny = ''
            twitter_user.save()
            success = True

    # Delete Organization images, Dec 2019, not for now, don't want to cause exceptions

    # Delete Position Table images, Dec 2019, not for now, don't want to cause exceptions

    # Delete Facebook User Table images
    if positive_value_exists(voter.facebook_id):
        facebook_manager = FacebookManager()
        facebook_user_results = facebook_manager.retrieve_facebook_user_by_facebook_user_id(voter.facebook_id)
        facebook_user = facebook_user_results['facebook_user']
        if facebook_user_results['facebook_user_found']:
            facebook_user.facebook_profile_image_url_https = ''
            facebook_user.facebook_background_image_url_https = ''
            facebook_user.we_vote_hosted_profile_image_url_large = ''
            facebook_user.we_vote_hosted_profile_image_url_medium = ''
            facebook_user.we_vote_hosted_profile_image_url_tiny = ''
            facebook_user.save()
            success = True

    # Delete FacebookAuthResponse Table images, Dec 2019, not for now, as a result image will display when voter signsin

    # Delete TwitterAuthResponse Table images, Dec 2019, not for now, as a result image will display when voter signs in

    if success:
        status = "DELETED_STORED_IMAGES_FOR_VOTER"
    else:
        status = "NO_IMAGE_FOUND_FOR_VOTER"

    results = {
        'success':                  success,
        'status':                   status,
    }
    log_and_time_cache_action(True, time0, 'delete_stored_images_for_voter')
    return results


def retrieve_all_images_for_one_candidate(candidate_we_vote_id):
    """
    Retrieve all cached images for one candidate
    :param candidate_we_vote_id:
    :return:
    """
    we_vote_image_list = []
    candidate_manager = CandidateManager()
    we_vote_image_manager = WeVoteImageManager()

    if positive_value_exists(candidate_we_vote_id):
        # if candidate_we_vote_id is defined then retrieve cached images for that candidate only
        candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id)
        if candidate_results['candidate_found']:
            we_vote_image_list_results = we_vote_image_manager.\
                retrieve_we_vote_image_list_from_we_vote_id(candidate_we_vote_id=candidate_we_vote_id)
            we_vote_image_list_query = we_vote_image_list_results['we_vote_image_list']
            we_vote_image_list = list(we_vote_image_list_query)

    return we_vote_image_list


def retrieve_all_images_for_one_organization(organization_we_vote_id):
    """
    Retrieve all cached images for one organization
    :param organization_we_vote_id:
    :return:
    """
    we_vote_image_list = []
    organization_manager = OrganizationManager()
    we_vote_image_manager = WeVoteImageManager()

    if positive_value_exists(organization_we_vote_id):
        # if organization_we_vote_id is defined then retrieve cached images for that organization only
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['organization_found']:
            we_vote_image_list_results = we_vote_image_manager.\
                retrieve_we_vote_image_list_from_we_vote_id(organization_we_vote_id=organization_we_vote_id)
            we_vote_image_list_query = we_vote_image_list_results['we_vote_image_list']
            we_vote_image_list = list(we_vote_image_list_query)

    return we_vote_image_list


def cache_and_create_resized_images_for_organization(organization_we_vote_id):
    """
    Create resized images for specific organization
    :param organization_we_vote_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_and_create_resized_images_for_organization')
    organization_manager = OrganizationManager()
    we_vote_image_manager = WeVoteImageManager()

    # cache original image
    cache_images_for_one_organization_results = cache_organization_master_images(
        organization_we_vote_id)

    # create resized images for that organization only
    organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
    if organization_results['success']:
        organization_we_vote_id = organization_results['organization'].we_vote_id
        we_vote_image_list_results = we_vote_image_manager.\
            retrieve_we_vote_image_list_from_we_vote_id(organization_we_vote_id=organization_we_vote_id)
        for we_vote_image in we_vote_image_list_results['we_vote_image_list']:
            # Iterate through all cached images
            create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
            create_resized_images_results.update(cache_images_for_one_organization_results)
            # TODO: Steve 12/15/21, this is a shot in the dark fix for changes that don't look like they could ever run
            create_resized_images_results.append(create_resized_images_results)
    log_and_time_cache_action(False, time0, 'cache_and_create_resized_images_for_organization')
    return create_resized_images_results


def cache_and_create_resized_images_for_voter(voter_id):
    """
    Create resized images for specific voter_id
    :param voter_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_and_create_resized_images_for_voter')
    create_all_resized_images_results = []
    voter_manager = VoterManager()
    we_vote_image_manager = WeVoteImageManager()

    # cache original image
    cache_images_for_a_voter_results = cache_voter_master_images(voter_id)

    # create resized images for that voter only
    voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    if voter_results['success']:
        voter_we_vote_id = voter_results['voter'].we_vote_id
        we_vote_image_list_results = we_vote_image_manager.\
            retrieve_we_vote_image_list_from_we_vote_id(voter_we_vote_id=voter_we_vote_id)
        for we_vote_image in we_vote_image_list_results['we_vote_image_list']:
            # Iterate through all cached images
            create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
            create_resized_images_results.update(cache_images_for_a_voter_results)
            create_all_resized_images_results.append(create_resized_images_results)
        log_and_time_cache_action(False, time0, 'create_resized_images_for_all_organizations')
        return create_all_resized_images_results
    log_and_time_cache_action(False, time0, 'cache_and_create_resized_images_for_voter FAILURE')


def cache_image_object_to_aws(
        python_image_library_image=None,
        campaignx_we_vote_id=None,
        kind_of_image_original=False,
        kind_of_image_campaignx_photo=False,
        kind_of_image_organization_uploaded_profile=False,
        kind_of_image_politician_uploaded_profile=False,
        organization_we_vote_id=None,
        politician_we_vote_id=None):
    """
    Cache master images to AWS.
    :param python_image_library_image:
    :param campaignx_we_vote_id:
    :param kind_of_image_original:
    :param kind_of_image_campaignx_photo:
    :param kind_of_image_organization_uploaded_profile:
    :param kind_of_image_politician_uploaded_profile:
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_image_object_to_aws')
    we_vote_parent_image_id = None
    success = False
    status = ''
    is_active_version = True
    we_vote_image_created = False
    image_url_valid = False
    image_stored_from_source = False
    image_stored_to_aws = False
    image_versions = []

    we_vote_image_manager = WeVoteImageManager()

    if positive_value_exists(kind_of_image_campaignx_photo):
        create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
            campaignx_we_vote_id=campaignx_we_vote_id,
            kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
            kind_of_image_original=kind_of_image_original)
        we_vote_image = create_we_vote_image_results['we_vote_image']
        we_vote_image_created = True
        we_vote_image_saved = create_we_vote_image_results['we_vote_image_saved']
    elif positive_value_exists(kind_of_image_organization_uploaded_profile):
        create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
            organization_we_vote_id=organization_we_vote_id,
            kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
            kind_of_image_original=kind_of_image_original)
        we_vote_image = create_we_vote_image_results['we_vote_image']
        we_vote_image_created = True
        we_vote_image_saved = create_we_vote_image_results['we_vote_image_saved']
    elif positive_value_exists(kind_of_image_politician_uploaded_profile):
        create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
            politician_we_vote_id=politician_we_vote_id,
            kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
            kind_of_image_original=kind_of_image_original)
        we_vote_image = create_we_vote_image_results['we_vote_image']
        we_vote_image_created = True
        we_vote_image_saved = create_we_vote_image_results['we_vote_image_saved']
    else:
        status += "MISSING_KIND_OF_IMAGE "
        we_vote_image_saved = False
    status += create_we_vote_image_results['status']
    if not we_vote_image_saved:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        log_and_time_cache_action(True, time0, 'cache_image_object_to_aws -- did not create image')
        return error_results

    # image file validation and get source image properties
    analyze_source_images_results = analyze_image_in_memory(python_image_library_image)

    if not analyze_source_images_results['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID ",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_image_object_to_aws -- analyze failed')
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID "
    image_width = analyze_source_images_results['image_width']
    image_height = analyze_source_images_results['image_height']
    image_format = analyze_source_images_results['image_format']

    # Get today's cached images and their versions so that image version can be calculated
    if positive_value_exists(kind_of_image_campaignx_photo):
        cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
            campaignx_we_vote_id=campaignx_we_vote_id,
            kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
            kind_of_image_original=kind_of_image_original)
    elif positive_value_exists(kind_of_image_organization_uploaded_profile):
        cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
            organization_we_vote_id=organization_we_vote_id,
            kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
            kind_of_image_original=kind_of_image_original)
    elif positive_value_exists(kind_of_image_politician_uploaded_profile):
        cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
            politician_we_vote_id=politician_we_vote_id,
            kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
            kind_of_image_original=kind_of_image_original)
    else:
        status += "MISSING_KIND_OF_IMAGE_TODAY_CACHED_IMAGES "
        we_vote_image_saved = False

    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)

    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    image_stored_from_source = True
    date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                   we_vote_image.date_image_saved.day,
                                                   year=we_vote_image.date_image_saved.year)
    if kind_of_image_campaignx_photo:
        image_type = CAMPAIGNX_PHOTO_IMAGE_NAME
    elif kind_of_image_organization_uploaded_profile:
        image_type = ORGANIZATION_UPLOADED_PROFILE_IMAGE_NAME
    elif kind_of_image_politician_uploaded_profile:
        image_type = POLITICIAN_UPLOADED_PROFILE_IMAGE_NAME
    else:
        image_type = 'unknown_image_type'

    if kind_of_image_original:
        master_image = MASTER_IMAGE
        image_format_filtered = image_format
    else:
        master_image = 'calculated'
        image_format_filtered = 'jpg'

    # ex issue_image_master-2017210_1_48x48.png
    we_vote_image_file_name = "{image_type}_{master_image}-{date_image_saved}_{counter}_" \
                              "{image_width}x{image_height}.{image_format}" \
                              "".format(image_type=image_type,
                                        master_image=master_image,
                                        date_image_saved=date_image_saved,
                                        counter=str(same_day_image_version),
                                        image_width=str(image_width),
                                        image_height=str(image_height),
                                        image_format=str(image_format_filtered))

    if kind_of_image_campaignx_photo:
        we_vote_image_file_location = campaignx_we_vote_id + "/" + we_vote_image_file_name
    elif kind_of_image_organization_uploaded_profile:
        we_vote_image_file_location = organization_we_vote_id + "/" + we_vote_image_file_name
    elif kind_of_image_politician_uploaded_profile:
        we_vote_image_file_location = politician_we_vote_id + "/" + we_vote_image_file_name
    else:
        we_vote_image_file_location = "unknown_kind_of_image" + "/" + we_vote_image_file_name

    image_stored_locally = we_vote_image_manager.store_python_image_locally(
        python_image_library_image, we_vote_image_file_name)

    if not image_stored_locally:
        status += " IMAGE_NOT_STORED_LOCALLY "
        error_results = {
            'success': success,
            'status': status,
            'we_vote_image_created': we_vote_image_created,
            'image_url_valid': image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_locally': False,
            'image_stored_to_aws': image_stored_to_aws,
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_image_object_to_aws -- not image_stored_locally')
        return error_results

    image_stored_to_aws = we_vote_image_manager.store_image_to_aws(
        we_vote_image_file_name=we_vote_image_file_name,
        we_vote_image_file_location=we_vote_image_file_location,
        image_format=image_format)
    if not image_stored_to_aws:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_NOT_STORED_TO_AWS ",
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          False,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_image_object_to_aws -- not image_stored_to_aws')
        return error_results

    we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                        "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                  we_vote_image_file_location=we_vote_image_file_location)
    save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(
        we_vote_image,
        we_vote_image_url=we_vote_image_url,
        we_vote_image_file_location=we_vote_image_file_location,
        we_vote_parent_image_id=we_vote_parent_image_id,
        is_active_version=is_active_version)
    status += " IMAGE_STORED_TO_AWS " + save_aws_info['status'] + " "
    success = save_aws_info['success']
    if not success:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_image_object_to_aws -- not save_aws_info')
        return error_results

    kind_of_image_large = not kind_of_image_original
    if kind_of_image_campaignx_photo:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_campaignx_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['image_width'],
            image_height=analyze_source_images_results['image_height'],
            image_url_https=we_vote_image.we_vote_image_url,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
        status += " " + save_source_info_results['status']
        successful_save = save_source_info_results['success']
    elif kind_of_image_organization_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_organization_uploaded_profile_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['image_width'],
            image_height=analyze_source_images_results['image_height'],
            image_url_https=we_vote_image.we_vote_image_url,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
        status += " " + save_source_info_results['status']
        successful_save = save_source_info_results['success']
    elif kind_of_image_politician_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_politician_uploaded_profile_info(
            we_vote_image=we_vote_image,
            image_width=analyze_source_images_results['image_width'],
            image_height=analyze_source_images_results['image_height'],
            image_url_https=we_vote_image.we_vote_image_url,
            same_day_image_version=same_day_image_version,
            image_url_valid=image_url_valid)
        status += " " + save_source_info_results['status']
        successful_save = save_source_info_results['success']
    else:
        successful_save = False
    if not successful_save:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': False,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_image_object_to_aws -- not save_source_info_results')
        return error_results

    # set active version False for other master images for same campaignx
    set_active_version_false_results = we_vote_image_manager.set_active_version_false_for_other_images(
        campaignx_we_vote_id=campaignx_we_vote_id,
        image_url_https=we_vote_image.we_vote_image_url,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
    )
    status += set_active_version_false_results['status']

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_to_aws':          image_stored_to_aws,
        'we_vote_image':                we_vote_image
    }
    log_and_time_cache_action(False, time0, 'cache_image_object_to_aws')
    return results


def cache_voter_master_uploaded_image(
        python_image_library_image=None,
        voter_we_vote_id=None):
    """
    Cache master voter uploaded image to AWS.
    :param python_image_library_image:
    :param voter_we_vote_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_voter_master_uploaded_image')
    we_vote_parent_image_id = None
    success = False
    status = ''
    is_active_version = True
    we_vote_image_created = False
    image_url_valid = False
    image_stored_from_source = False
    image_stored_to_aws = False
    image_versions = []

    we_vote_image_manager = WeVoteImageManager()

    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        voter_we_vote_id=voter_we_vote_id,
        kind_of_image_voter_uploaded_profile=True,
        kind_of_image_original=True)
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        log_and_time_cache_action(True, time0, 'cache_voter_master_uploaded_image -- not we_vote_image_saved')
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']

    # image file validation and get source image properties
    analyze_source_images_results = analyze_image_in_memory(python_image_library_image)

    if not analyze_source_images_results['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID ",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_voter_master_uploaded_image -- not image_url_valid')
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID "
    image_width = analyze_source_images_results['image_width']
    image_height = analyze_source_images_results['image_height']
    image_format = analyze_source_images_results['image_format']

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        kind_of_image_original=True,
        kind_of_image_voter_uploaded_profile=True,
        voter_we_vote_id=voter_we_vote_id,
    )

    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)

    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    image_stored_from_source = True
    date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                   we_vote_image.date_image_saved.day,
                                                   year=we_vote_image.date_image_saved.year)
    image_type = 'voter_uploaded_profile_image'

    master_image = MASTER_IMAGE  # "master"
    image_format_filtered = image_format

    # ex voter_uploaded_profile_image_master-2017210_1_48x48.png
    we_vote_image_file_name = "{image_type}_{master_image}-{date_image_saved}_{counter}_" \
                              "{image_width}x{image_height}.{image_format}" \
                              "".format(image_type=image_type,
                                        master_image=master_image,
                                        date_image_saved=date_image_saved,
                                        counter=str(same_day_image_version),
                                        image_width=str(image_width),
                                        image_height=str(image_height),
                                        image_format=str(image_format_filtered))

    we_vote_image_file_location = voter_we_vote_id + "/" + we_vote_image_file_name

    image_stored_locally = we_vote_image_manager.store_python_image_locally(
        python_image_library_image, we_vote_image_file_name)

    if not image_stored_locally:
        error_results = {
            'success': success,
            'status': status + " IMAGE_NOT_STORED_LOCALLY ",
            'we_vote_image_created': we_vote_image_created,
            'image_url_valid': image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_locally': False,
            'image_stored_to_aws': image_stored_to_aws,
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_voter_master_uploaded_image -- not image_stored_locally')
        return error_results

    image_stored_to_aws = we_vote_image_manager.store_image_to_aws(
        we_vote_image_file_name=we_vote_image_file_name,
        we_vote_image_file_location=we_vote_image_file_location,
        image_format=image_format)
    if not image_stored_to_aws:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_NOT_STORED_TO_AWS ",
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          False,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_voter_master_uploaded_image -- not image_stored_to_aws')
        return error_results

    we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                        "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                  we_vote_image_file_location=we_vote_image_file_location)
    save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(
        we_vote_image,
        we_vote_image_url=we_vote_image_url,
        we_vote_image_file_location=we_vote_image_file_location,
        we_vote_parent_image_id=we_vote_parent_image_id,
        is_active_version=is_active_version)
    status += " IMAGE_STORED_TO_AWS " + save_aws_info['status'] + " "
    success = save_aws_info['success']
    if not success:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        log_and_time_cache_action(True, time0, 'cache_voter_master_uploaded_image -- not save_aws_info')
        return error_results

    save_source_info_results = we_vote_image_manager.save_we_vote_image_voter_uploaded_info(
        we_vote_image=we_vote_image,
        image_width=analyze_source_images_results['image_width'],
        image_height=analyze_source_images_results['image_height'],
        image_url_https=we_vote_image.we_vote_image_url,
        same_day_image_version=same_day_image_version,
        image_url_valid=image_url_valid)
    status += " " + save_source_info_results['status']
    if not save_source_info_results['success']:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': False,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    # set active version False for other master images for same campaignx
    set_active_version_false_results = we_vote_image_manager.set_active_version_false_for_other_images(
        voter_we_vote_id=voter_we_vote_id,
        image_url_https=we_vote_image.we_vote_image_url,
        kind_of_image_voter_uploaded_profile=True)
    status += set_active_version_false_results['status']

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_to_aws':          image_stored_to_aws,
        'we_vote_image':                we_vote_image
    }
    log_and_time_cache_action(False, time0, 'cache_voter_master_uploaded_image')
    return results


def retrieve_all_images_for_one_issue(issue_we_vote_id):
    """
    Retrieve all cached images for one issue
    :param issue_we_vote_id:
    :return:
    """
    we_vote_image_list = []
    we_vote_image_manager = WeVoteImageManager()

    if issue_we_vote_id:
        # if issue_we_vote_id is defined then retrieve cached images for that issue only
        we_vote_image_list_results = we_vote_image_manager.\
            retrieve_we_vote_image_list_from_we_vote_id(issue_we_vote_id=issue_we_vote_id)
        we_vote_image_list_query = we_vote_image_list_results['we_vote_image_list']
        we_vote_image_list = list(we_vote_image_list_query)

    return we_vote_image_list


def retrieve_all_images_for_one_voter(voter_id):
    """
    Retrieve all cached images for one voter
    :param voter_id:
    :return:
    """
    we_vote_image_list = []
    voter_manager = VoterManager()
    we_vote_image_manager = WeVoteImageManager()

    if voter_id:
        # if voter_id is defined then retrieve cached images for that voter only
        voter_results = voter_manager.retrieve_voter_by_id(voter_id)
        if voter_results['success']:
            voter_we_vote_id = voter_results['voter'].we_vote_id
            we_vote_image_list_results = we_vote_image_manager.\
                retrieve_we_vote_image_list_from_we_vote_id(voter_we_vote_id=voter_we_vote_id)
            we_vote_image_list_query = we_vote_image_list_results['we_vote_image_list']
            we_vote_image_list = list(we_vote_image_list_query)

    return we_vote_image_list


def create_resized_image_if_not_created(we_vote_image):
    """
    Create resized images only if not created for we_vote_image object
    :param we_vote_image:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'create_resized_image_if_not_created')

    if positive_value_exists(we_vote_image.we_vote_image_file_location):
        image_format = we_vote_image.we_vote_image_file_location.split(".")[-1]
    else:
        image_format = ""

    create_resized_image_results = {
        'voter_we_vote_id':                         we_vote_image.voter_we_vote_id,
        'campaignx_we_vote_id':                     we_vote_image.campaignx_we_vote_id,
        'candidate_we_vote_id':                     we_vote_image.candidate_we_vote_id,
        'organization_we_vote_id':                  we_vote_image.organization_we_vote_id,
        'politician_we_vote_id':                    we_vote_image.politician_we_vote_id,
        'representative_we_vote_id':                we_vote_image.representative_we_vote_id,
        'cached_large_image':                       False,
        'cached_medium_image':                      False,
        'cached_tiny_image':                        False,
    }

    if we_vote_image.kind_of_image_ballotpedia_profile:
        image_url_https = we_vote_image.ballotpedia_profile_image_url
    elif we_vote_image.kind_of_image_campaignx_photo:
        image_url_https = we_vote_image.campaignx_photo_url_https
    elif we_vote_image.kind_of_image_ctcl_profile:
        image_url_https = we_vote_image.photo_url_from_ctcl
    elif we_vote_image.kind_of_image_facebook_background:
        image_url_https = we_vote_image.facebook_background_image_url_https
    elif we_vote_image.kind_of_image_facebook_profile:
        image_url_https = we_vote_image.facebook_profile_image_url_https
        # 2024-02-04 Dale: This use of 'we_vote_image_url' instead of 'facebook_profile_image_url_https', was added for
        # Facebook profile images brought in through SQS, but is non-standard and creates problems downstream
        # image_url_https = we_vote_image.we_vote_image_url
    elif we_vote_image.kind_of_image_linkedin_profile:
        image_url_https = we_vote_image.linkedin_profile_image_url
    elif we_vote_image.kind_of_image_maplight:
        image_url_https = we_vote_image.maplight_image_url_https
    elif we_vote_image.kind_of_image_organization_uploaded_profile:
        image_url_https = we_vote_image.organization_uploaded_profile_image_url_https
    elif we_vote_image.kind_of_image_other_source:
        image_url_https = we_vote_image.other_source_image_url
    elif we_vote_image.kind_of_image_politician_uploaded_profile:
        image_url_https = we_vote_image.politician_uploaded_profile_image_url_https
    elif we_vote_image.kind_of_image_twitter_background:
        image_url_https = we_vote_image.twitter_profile_background_image_url_https
    elif we_vote_image.kind_of_image_twitter_banner:
        image_url_https = we_vote_image.twitter_profile_banner_url_https
    elif we_vote_image.kind_of_image_twitter_profile:
        image_url_https = we_vote_image.twitter_profile_image_url_https
    elif we_vote_image.kind_of_image_vote_smart:
        image_url_https = we_vote_image.vote_smart_image_url_https
    elif we_vote_image.kind_of_image_vote_usa_profile:
        image_url_https = we_vote_image.photo_url_from_vote_usa
    elif we_vote_image.kind_of_image_voter_uploaded_profile:
        image_url_https = we_vote_image.voter_uploaded_profile_image_url_https
    elif we_vote_image.kind_of_image_wikipedia_profile:
        image_url_https = we_vote_image.wikipedia_profile_image_url
    else:
        image_url_https = ''

    # Check if resized image versions exist or not
    resized_version_exists_results = check_resized_version_exists(
        campaignx_we_vote_id=we_vote_image.campaignx_we_vote_id,
        candidate_we_vote_id=we_vote_image.candidate_we_vote_id,
        image_url_https=image_url_https,
        kind_of_image_ballotpedia_profile=we_vote_image.kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=we_vote_image.kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=we_vote_image.kind_of_image_ctcl_profile,
        kind_of_image_facebook_background=we_vote_image.kind_of_image_facebook_background,
        kind_of_image_facebook_profile=we_vote_image.kind_of_image_facebook_profile,
        kind_of_image_linkedin_profile=we_vote_image.kind_of_image_linkedin_profile,
        kind_of_image_maplight=we_vote_image.kind_of_image_maplight,
        kind_of_image_organization_uploaded_profile=we_vote_image.kind_of_image_organization_uploaded_profile,
        kind_of_image_other_source=we_vote_image.kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=we_vote_image.kind_of_image_politician_uploaded_profile,
        kind_of_image_twitter_profile=we_vote_image.kind_of_image_twitter_profile,
        kind_of_image_twitter_background=we_vote_image.kind_of_image_twitter_background,
        kind_of_image_twitter_banner=we_vote_image.kind_of_image_twitter_banner,
        kind_of_image_vote_smart=we_vote_image.kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=we_vote_image.kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=we_vote_image.kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=we_vote_image.kind_of_image_wikipedia_profile,
        organization_we_vote_id=we_vote_image.organization_we_vote_id,
        politician_we_vote_id=we_vote_image.politician_we_vote_id,
        representative_we_vote_id=we_vote_image.representative_we_vote_id,
        voter_we_vote_id=we_vote_image.voter_we_vote_id,
    )
    if not resized_version_exists_results['large_image_version_exists']:
        # Large version does not exist so create resize image and cache it
        cache_resized_image_locally_results = cache_resized_image_locally(
            campaignx_we_vote_id=we_vote_image.campaignx_we_vote_id,
            candidate_we_vote_id=we_vote_image.candidate_we_vote_id,
            facebook_user_id=we_vote_image.facebook_user_id,
            google_civic_election_id=we_vote_image.google_civic_election_id,
            image_format=image_format,
            image_offset_x=we_vote_image.facebook_background_image_offset_x,
            image_offset_y=we_vote_image.facebook_background_image_offset_y,
            image_url_https=image_url_https,
            kind_of_image_ballotpedia_profile=we_vote_image.kind_of_image_ballotpedia_profile,
            kind_of_image_campaignx_photo=we_vote_image.kind_of_image_campaignx_photo,
            kind_of_image_ctcl_profile=we_vote_image.kind_of_image_ctcl_profile,
            kind_of_image_facebook_background=we_vote_image.kind_of_image_facebook_background,
            kind_of_image_facebook_profile=we_vote_image.kind_of_image_facebook_profile,
            kind_of_image_large=True,
            kind_of_image_linkedin_profile=we_vote_image.kind_of_image_linkedin_profile,
            kind_of_image_maplight=we_vote_image.kind_of_image_maplight,
            kind_of_image_organization_uploaded_profile=we_vote_image.kind_of_image_organization_uploaded_profile,
            kind_of_image_other_source=we_vote_image.kind_of_image_other_source,
            kind_of_image_politician_uploaded_profile=we_vote_image.kind_of_image_politician_uploaded_profile,
            kind_of_image_twitter_background=we_vote_image.kind_of_image_twitter_background,
            kind_of_image_twitter_banner=we_vote_image.kind_of_image_twitter_banner,
            kind_of_image_twitter_profile=we_vote_image.kind_of_image_twitter_profile,
            kind_of_image_vote_smart=we_vote_image.kind_of_image_vote_smart,
            kind_of_image_vote_usa_profile=we_vote_image.kind_of_image_vote_usa_profile,
            kind_of_image_voter_uploaded_profile=we_vote_image.kind_of_image_voter_uploaded_profile,
            kind_of_image_wikipedia_profile=we_vote_image.kind_of_image_wikipedia_profile,
            maplight_id=we_vote_image.maplight_id,
            organization_we_vote_id=we_vote_image.organization_we_vote_id,
            other_source=we_vote_image.other_source,
            politician_we_vote_id=we_vote_image.politician_we_vote_id,
            representative_we_vote_id=we_vote_image.representative_we_vote_id,
            twitter_id=we_vote_image.twitter_id,
            vote_smart_id=we_vote_image.vote_smart_id,
            voter_we_vote_id=we_vote_image.voter_we_vote_id,
            we_vote_parent_image_id=we_vote_image.id,
        )
        create_resized_image_results['cached_large_image'] = cache_resized_image_locally_results['success']
    else:
        create_resized_image_results['cached_large_image'] = IMAGE_ALREADY_CACHED

    # Only some of our kinds of images have medium or tiny sizes
    if we_vote_image.kind_of_image_ballotpedia_profile or \
            we_vote_image.kind_of_image_campaignx_photo or \
            we_vote_image.kind_of_image_ctcl_profile or \
            we_vote_image.kind_of_image_facebook_profile or \
            we_vote_image.kind_of_image_linkedin_profile or \
            we_vote_image.kind_of_image_organization_uploaded_profile or \
            we_vote_image.kind_of_image_politician_uploaded_profile or \
            we_vote_image.kind_of_image_maplight or \
            we_vote_image.kind_of_image_twitter_profile or \
            we_vote_image.kind_of_image_vote_smart or \
            we_vote_image.kind_of_image_vote_usa_profile or \
            we_vote_image.kind_of_image_voter_uploaded_profile or \
            we_vote_image.kind_of_image_wikipedia_profile or \
            we_vote_image.kind_of_image_other_source:
        if not resized_version_exists_results['medium_image_version_exists']:
            # Medium version does not exist so create resize image and cache it
            cache_resized_image_locally_results = cache_resized_image_locally(
                campaignx_we_vote_id=we_vote_image.campaignx_we_vote_id,
                candidate_we_vote_id=we_vote_image.candidate_we_vote_id,
                facebook_user_id=we_vote_image.facebook_user_id,
                google_civic_election_id=we_vote_image.google_civic_election_id,
                image_format=image_format,
                image_offset_x=we_vote_image.facebook_background_image_offset_x,
                image_offset_y=we_vote_image.facebook_background_image_offset_y,
                image_url_https=image_url_https,
                kind_of_image_ballotpedia_profile=we_vote_image.kind_of_image_ballotpedia_profile,
                kind_of_image_campaignx_photo=we_vote_image.kind_of_image_campaignx_photo,
                kind_of_image_ctcl_profile=we_vote_image.kind_of_image_ctcl_profile,
                kind_of_image_facebook_profile=we_vote_image.kind_of_image_facebook_profile,
                kind_of_image_facebook_background=we_vote_image.kind_of_image_facebook_background,
                kind_of_image_linkedin_profile=we_vote_image.kind_of_image_linkedin_profile,
                kind_of_image_maplight=we_vote_image.kind_of_image_maplight,
                kind_of_image_medium=True,
                kind_of_image_organization_uploaded_profile=we_vote_image.kind_of_image_organization_uploaded_profile,
                kind_of_image_other_source=we_vote_image.kind_of_image_other_source,
                kind_of_image_politician_uploaded_profile=we_vote_image.kind_of_image_politician_uploaded_profile,
                kind_of_image_twitter_background=we_vote_image.kind_of_image_twitter_background,
                kind_of_image_twitter_banner=we_vote_image.kind_of_image_twitter_banner,
                kind_of_image_twitter_profile=we_vote_image.kind_of_image_twitter_profile,
                kind_of_image_vote_smart=we_vote_image.kind_of_image_vote_smart,
                kind_of_image_vote_usa_profile=we_vote_image.kind_of_image_vote_usa_profile,
                kind_of_image_voter_uploaded_profile=we_vote_image.kind_of_image_voter_uploaded_profile,
                kind_of_image_wikipedia_profile=we_vote_image.kind_of_image_wikipedia_profile,
                maplight_id=we_vote_image.maplight_id,
                organization_we_vote_id=we_vote_image.organization_we_vote_id,
                other_source=we_vote_image.other_source,
                politician_we_vote_id=we_vote_image.politician_we_vote_id,
                representative_we_vote_id=we_vote_image.representative_we_vote_id,
                twitter_id=we_vote_image.twitter_id,
                vote_smart_id=we_vote_image.vote_smart_id,
                voter_we_vote_id=we_vote_image.voter_we_vote_id,
                we_vote_parent_image_id=we_vote_image.id,
            )
            create_resized_image_results['cached_medium_image'] = cache_resized_image_locally_results['success']
        else:
            create_resized_image_results['cached_medium_image'] = IMAGE_ALREADY_CACHED

        if not resized_version_exists_results['tiny_image_version_exists']:
            # Tiny version does not exist so create resize image and cache it
            cache_resized_image_locally_results = cache_resized_image_locally(
                campaignx_we_vote_id=we_vote_image.campaignx_we_vote_id,
                candidate_we_vote_id=we_vote_image.candidate_we_vote_id,
                facebook_user_id=we_vote_image.facebook_user_id,
                google_civic_election_id=we_vote_image.google_civic_election_id,
                image_format=image_format,
                image_offset_x=we_vote_image.facebook_background_image_offset_x,
                image_offset_y=we_vote_image.facebook_background_image_offset_y,
                image_url_https=image_url_https,
                kind_of_image_ballotpedia_profile=we_vote_image.kind_of_image_ballotpedia_profile,
                kind_of_image_campaignx_photo=we_vote_image.kind_of_image_campaignx_photo,
                kind_of_image_ctcl_profile=we_vote_image.kind_of_image_ctcl_profile,
                kind_of_image_facebook_background=we_vote_image.kind_of_image_facebook_background,
                kind_of_image_facebook_profile=we_vote_image.kind_of_image_facebook_profile,
                kind_of_image_linkedin_profile=we_vote_image.kind_of_image_linkedin_profile,
                kind_of_image_maplight=we_vote_image.kind_of_image_maplight,
                kind_of_image_organization_uploaded_profile=we_vote_image.kind_of_image_organization_uploaded_profile,
                kind_of_image_other_source=we_vote_image.kind_of_image_other_source,
                kind_of_image_politician_uploaded_profile=we_vote_image.kind_of_image_politician_uploaded_profile,
                kind_of_image_tiny=True,
                kind_of_image_twitter_background=we_vote_image.kind_of_image_twitter_background,
                kind_of_image_twitter_banner=we_vote_image.kind_of_image_twitter_banner,
                kind_of_image_twitter_profile=we_vote_image.kind_of_image_twitter_profile,
                kind_of_image_vote_smart=we_vote_image.kind_of_image_vote_smart,
                kind_of_image_vote_usa_profile=we_vote_image.kind_of_image_vote_usa_profile,
                kind_of_image_voter_uploaded_profile=we_vote_image.kind_of_image_voter_uploaded_profile,
                kind_of_image_wikipedia_profile=we_vote_image.kind_of_image_wikipedia_profile,
                maplight_id=we_vote_image.maplight_id,
                organization_we_vote_id=we_vote_image.organization_we_vote_id,
                other_source=we_vote_image.other_source,
                politician_we_vote_id=we_vote_image.politician_we_vote_id,
                representative_we_vote_id=we_vote_image.representative_we_vote_id,
                twitter_id=we_vote_image.twitter_id,
                vote_smart_id=we_vote_image.vote_smart_id,
                voter_we_vote_id=we_vote_image.voter_we_vote_id,
                we_vote_parent_image_id=we_vote_image.id,
            )
            create_resized_image_results['cached_tiny_image'] = cache_resized_image_locally_results['success']
        else:
            create_resized_image_results['cached_tiny_image'] = IMAGE_ALREADY_CACHED
    log_and_time_cache_action(False, time0, 'create_resized_image_if_not_created')
    return create_resized_image_results


def check_resized_version_exists(
        voter_we_vote_id=None,
        campaignx_we_vote_id=None,
        candidate_we_vote_id=None,
        organization_we_vote_id=None,
        politician_we_vote_id=None,
        representative_we_vote_id=None,
        image_url_https=None,
        kind_of_image_ballotpedia_profile=False,
        kind_of_image_campaignx_photo=False,
        kind_of_image_ctcl_profile=False,
        kind_of_image_facebook_background=False,
        kind_of_image_facebook_profile=False,
        kind_of_image_linkedin_profile=False,
        kind_of_image_maplight=False,
        kind_of_image_organization_uploaded_profile=False,
        kind_of_image_politician_uploaded_profile=False,
        kind_of_image_twitter_background=False,
        kind_of_image_twitter_banner=False,
        kind_of_image_twitter_profile=False,
        kind_of_image_vote_smart=False,
        kind_of_image_vote_usa_profile=False,
        kind_of_image_voter_uploaded_profile=False,
        kind_of_image_wikipedia_profile=False,
        kind_of_image_other_source=False):
    """
    Check if large, medium or tiny image versions already exist or not
    :param voter_we_vote_id:
    :param campaignx_we_vote_id:
    :param candidate_we_vote_id:
    :param organization_we_vote_id:
    :param politician_we_vote_id:
    :param representative_we_vote_id:
    :param image_url_https:
    :param kind_of_image_ballotpedia_profile:
    :param kind_of_image_campaignx_photo:
    :param kind_of_image_ctcl_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_linkedin_profile:
    :param kind_of_image_maplight:
    :param kind_of_image_organization_uploaded_profile:
    :param kind_of_image_politician_uploaded_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_vote_smart:
    :param kind_of_image_vote_usa_profile:
    :param kind_of_image_voter_uploaded_profile:
    :param kind_of_image_wikipedia_profile:
    :param kind_of_image_other_source:
    :return:
    """
    results = {
        'medium_image_version_exists':  False,
        'tiny_image_version_exists':    False,
        'large_image_version_exists':   False
    }
    we_vote_image_list_results = {
        'we_vote_image_list':   [],
    }
    we_vote_image_manager = WeVoteImageManager()

    if kind_of_image_ballotpedia_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            ballotpedia_profile_image_url=image_url_https,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_campaignx_photo:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            campaignx_photo_url_https=image_url_https,
            campaignx_we_vote_id=campaignx_we_vote_id,
        )
    elif kind_of_image_ctcl_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            photo_url_from_ctcl=image_url_https,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
        )
    elif kind_of_image_facebook_background:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            facebook_background_image_url_https=image_url_https,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_facebook_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            facebook_profile_image_url_https=image_url_https,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_linkedin_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            linkedin_profile_image_url=image_url_https,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_maplight:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            maplight_image_url_https=image_url_https,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_organization_uploaded_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            organization_uploaded_profile_image_url_https=image_url_https,
            organization_we_vote_id=organization_we_vote_id,
        )
    elif kind_of_image_politician_uploaded_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            politician_uploaded_profile_image_url_https=image_url_https,
            politician_we_vote_id=politician_we_vote_id,
        )
    elif kind_of_image_twitter_banner:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_profile_banner_url_https=image_url_https,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_twitter_background:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_profile_background_image_url_https=image_url_https,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_twitter_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_profile_image_url_https=image_url_https,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_vote_smart:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            vote_smart_image_url_https=image_url_https,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_vote_usa_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            photo_url_from_vote_usa=image_url_https,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
        )
    elif kind_of_image_voter_uploaded_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_uploaded_profile_image_url_https=image_url_https,
            voter_we_vote_id=voter_we_vote_id,
        )
    elif kind_of_image_wikipedia_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            wikipedia_profile_image_url=image_url_https,
        )
    elif kind_of_image_other_source:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            other_source_image_url=image_url_https,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
        )

    we_vote_image_list = we_vote_image_list_results['we_vote_image_list']
    for we_vote_image in we_vote_image_list:
        if we_vote_image.we_vote_image_url is None or we_vote_image.we_vote_image_url == "":
            # if we_vote_image_url is empty then delete that entry
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        elif we_vote_image.kind_of_image_medium:
            results['medium_image_version_exists'] = True
        elif we_vote_image.kind_of_image_tiny:
            results['tiny_image_version_exists'] = True
        elif we_vote_image.kind_of_image_large:
            results['large_image_version_exists'] = True

    return results


def cache_resized_image_locally(
        campaignx_we_vote_id=None,
        candidate_we_vote_id=None,
        facebook_user_id=None,
        google_civic_election_id=0,
        image_format=None,
        image_offset_x=0,
        image_offset_y=0,
        image_url_https='',
        is_active_version=True,
        issue_we_vote_id=None,
        kind_of_image_ballotpedia_profile=False,
        kind_of_image_campaignx_photo=False,
        kind_of_image_ctcl_profile=False,
        kind_of_image_facebook_background=False,
        kind_of_image_facebook_profile=False,
        kind_of_image_issue=False,
        kind_of_image_large=False,
        kind_of_image_linkedin_profile=False,
        kind_of_image_maplight=False,
        kind_of_image_medium=False,
        kind_of_image_organization_uploaded_profile=False,
        kind_of_image_original=False,
        kind_of_image_other_source=False,
        kind_of_image_politician_uploaded_profile=False,
        kind_of_image_tiny=False,
        kind_of_image_twitter_background=False,
        kind_of_image_twitter_banner=False,
        kind_of_image_twitter_profile=False,
        kind_of_image_vote_smart=False,
        kind_of_image_vote_usa_profile=False,
        kind_of_image_voter_uploaded_profile=False,
        kind_of_image_wikipedia_profile=False,
        maplight_id=None,
        organization_we_vote_id=None,
        other_source=None,
        politician_we_vote_id=None,
        representative_we_vote_id=None,
        twitter_id=None,
        vote_smart_id=None,
        voter_we_vote_id=None,
        we_vote_parent_image_id=0,
    ):
    """
    Resize the image as per image version and cache the same
    :param campaignx_we_vote_id:
    :param candidate_we_vote_id:
    :param facebook_user_id:
    :param google_civic_election_id:
    :param image_format:
    :param image_offset_x:
    :param image_offset_y:
    :param image_url_https:
    :param is_active_version:
    :param issue_we_vote_id:
    :param kind_of_image_ballotpedia_profile:
    :param kind_of_image_campaignx_photo:
    :param kind_of_image_ctcl_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_issue:
    :param kind_of_image_large:
    :param kind_of_image_linkedin_profile:
    :param kind_of_image_maplight:
    :param kind_of_image_medium:
    :param kind_of_image_organization_uploaded_profile:
    :param kind_of_image_original:
    :param kind_of_image_other_source:
    :param kind_of_image_politician_uploaded_profile:
    :param kind_of_image_tiny:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_vote_smart:
    :param kind_of_image_vote_usa_profile:
    :param kind_of_image_voter_uploaded_profile:
    :param kind_of_image_wikipedia_profile:
    :param maplight_id:
    :param organization_we_vote_id:
    :param other_source:
    :param politician_we_vote_id:
    :param representative_we_vote_id:
    :param twitter_id:
    :param vote_smart_id:
    :param voter_we_vote_id:
    :param we_vote_parent_image_id:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_resized_image_locally')
    success = False
    status = ''
    we_vote_image_created = False
    resized_image_created = False
    image_stored_from_source = False
    image_stored_locally = False
    image_stored_to_aws = False
    image_versions = []
    we_vote_image_file_location = None

    we_vote_image_manager = WeVoteImageManager()

    # Set up image we will use for large, medium or tiny
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        campaignx_we_vote_id=campaignx_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_large=kind_of_image_large,
        kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_medium=kind_of_image_medium,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_original=kind_of_image_original,
        kind_of_image_other_source=kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        kind_of_image_tiny=kind_of_image_tiny,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        representative_we_vote_id=representative_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_locally':         image_stored_locally,
            'resized_image_created':        resized_image_created,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']

    image_width = ''
    image_height = ''
    if kind_of_image_issue:
        if kind_of_image_large:
            image_width = ISSUES_IMAGE_LARGE_WIDTH
            image_height = ISSUES_IMAGE_LARGE_HEIGHT
        elif kind_of_image_medium:
            image_width = ISSUES_IMAGE_MEDIUM_WIDTH
            image_height = ISSUES_IMAGE_MEDIUM_HEIGHT
        elif kind_of_image_tiny:
            image_width = ISSUES_IMAGE_TINY_WIDTH
            image_height = ISSUES_IMAGE_TINY_HEIGHT
    elif kind_of_image_campaignx_photo:
        if kind_of_image_large:
            image_width = CAMPAIGN_PHOTO_LARGE_MAX_WIDTH
            image_height = CAMPAIGN_PHOTO_LARGE_MAX_HEIGHT
        elif kind_of_image_medium:
            image_width = CAMPAIGN_PHOTO_MEDIUM_MAX_WIDTH
            image_height = CAMPAIGN_PHOTO_MEDIUM_MAX_HEIGHT
        elif kind_of_image_tiny:
            image_width = CAMPAIGN_PHOTO_SMALL_MAX_WIDTH
            image_height = CAMPAIGN_PHOTO_SMALL_MAX_HEIGHT
    else:
        if kind_of_image_large:
            image_width = PROFILE_IMAGE_LARGE_WIDTH
            image_height = PROFILE_IMAGE_LARGE_HEIGHT
        elif kind_of_image_medium:
            image_width = PROFILE_IMAGE_MEDIUM_WIDTH
            image_height = PROFILE_IMAGE_MEDIUM_HEIGHT
        elif kind_of_image_tiny:
            image_width = PROFILE_IMAGE_TINY_WIDTH
            image_height = PROFILE_IMAGE_TINY_HEIGHT

    if kind_of_image_ballotpedia_profile:
        image_type = BALLOTPEDIA_IMAGE_NAME
    elif kind_of_image_campaignx_photo:
        image_type = CAMPAIGNX_PHOTO_IMAGE_NAME
    elif kind_of_image_ctcl_profile:
        image_type = CTCL_PROFILE_IMAGE_NAME
    elif kind_of_image_facebook_background:
        image_type = FACEBOOK_BACKGROUND_IMAGE_NAME
        image_height = SOCIAL_BACKGROUND_IMAGE_HEIGHT
        image_width = SOCIAL_BACKGROUND_IMAGE_WIDTH
    elif kind_of_image_facebook_profile:
        image_type = FACEBOOK_PROFILE_IMAGE_NAME
    elif kind_of_image_issue:
        image_type = ISSUE_IMAGE_NAME
    elif kind_of_image_linkedin_profile:
        image_type = LINKEDIN_IMAGE_NAME
    elif kind_of_image_maplight:
        image_type = MAPLIGHT_IMAGE_NAME
    elif kind_of_image_organization_uploaded_profile:
        image_type = ORGANIZATION_UPLOADED_PROFILE_IMAGE_NAME
    elif kind_of_image_other_source:
        image_type = other_source
    elif kind_of_image_politician_uploaded_profile:
        image_type = POLITICIAN_UPLOADED_PROFILE_IMAGE_NAME
    elif kind_of_image_twitter_background:
        image_type = TWITTER_BACKGROUND_IMAGE_NAME
    elif kind_of_image_twitter_banner:
        image_type = TWITTER_BANNER_IMAGE_NAME
    elif kind_of_image_twitter_profile:
        image_type = TWITTER_PROFILE_IMAGE_NAME
    elif kind_of_image_vote_smart:
        image_type = VOTE_SMART_IMAGE_NAME
    elif kind_of_image_vote_usa_profile:
        image_type = VOTE_USA_PROFILE_IMAGE_NAME
    elif kind_of_image_voter_uploaded_profile:
        image_type = VOTER_UPLOADED_IMAGE_NAME
    elif kind_of_image_wikipedia_profile:
        image_type = WIKIPEDIA_IMAGE_NAME
    else:
        image_type = ''

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        campaignx_we_vote_id=campaignx_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_ballotpedia_profile=kind_of_image_ballotpedia_profile,
        kind_of_image_campaignx_photo=kind_of_image_campaignx_photo,
        kind_of_image_ctcl_profile=kind_of_image_ctcl_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_large=kind_of_image_large,
        kind_of_image_linkedin_profile=kind_of_image_linkedin_profile,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_medium=kind_of_image_medium,
        kind_of_image_organization_uploaded_profile=kind_of_image_organization_uploaded_profile,
        kind_of_image_original=kind_of_image_original,
        kind_of_image_other_source=kind_of_image_other_source,
        kind_of_image_politician_uploaded_profile=kind_of_image_politician_uploaded_profile,
        kind_of_image_tiny=kind_of_image_tiny,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_vote_usa_profile=kind_of_image_vote_usa_profile,
        kind_of_image_voter_uploaded_profile=kind_of_image_voter_uploaded_profile,
        kind_of_image_wikipedia_profile=kind_of_image_wikipedia_profile,
        organization_we_vote_id=organization_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        representative_we_vote_id=representative_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )
    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)
    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    # 2021-05-09 We default to storing all resized images as jpg
    convert_image_to_jpg = True
    if kind_of_image_ballotpedia_profile:
        # image url is valid so store source image of ballotpedia to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_ballotpedia_info(
            we_vote_image, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_ballotpedia_profile)
    elif kind_of_image_campaignx_photo:
        # Update this new image with width, height, original url and version number
        save_source_info_results = we_vote_image_manager.save_we_vote_image_campaignx_info(
            we_vote_image=we_vote_image,
            image_width=image_width,
            image_height=image_height,
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_ctcl_profile:
        # Update this new image with width, height, original url and version number
        save_source_info_results = we_vote_image_manager.save_we_vote_image_ctcl_info(
            we_vote_image=we_vote_image,
            image_width=image_width,
            image_height=image_height,
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_facebook_profile or kind_of_image_facebook_background:
        # image url is valid so store source image of facebook to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_facebook_info(
            we_vote_image, facebook_user_id, image_width, image_height,
            image_url_https, same_day_image_version, kind_of_image_facebook_profile,
            kind_of_image_facebook_background)
    elif kind_of_image_issue:
        # image url is valid so store source image of issue to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_issue_info(
            we_vote_image, image_width, image_height, image_url_https, same_day_image_version)
        convert_image_to_jpg = False
    elif kind_of_image_linkedin_profile:
        # image url is valid so store source image of linkedin to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_linkedin_info(
            we_vote_image, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_linkedin_profile)
    elif kind_of_image_maplight:
        # image url is valid so store source image of maplight to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_maplight_info(
            we_vote_image, maplight_id, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_maplight)
    elif kind_of_image_organization_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_organization_uploaded_profile_info(
            we_vote_image=we_vote_image,
            image_width=image_width,
            image_height=image_height,
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_other_source:
        # image url is valid so store source image from other source to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_other_source_info(
            we_vote_image, image_width, image_height, other_source, image_url_https, same_day_image_version,
            kind_of_image_other_source)
    elif kind_of_image_politician_uploaded_profile:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_politician_uploaded_profile_info(
            we_vote_image=we_vote_image,
            image_width=image_width,
            image_height=image_height,
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_twitter_profile or kind_of_image_twitter_background or kind_of_image_twitter_banner:
        # image url is valid so store source image of twitter to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(
            we_vote_image, twitter_id, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner)
        convert_image_to_jpg = False
    elif kind_of_image_vote_smart:
        # image url is valid so store source image of maplight to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_vote_smart_info(
            we_vote_image, vote_smart_id, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_vote_smart)
    elif kind_of_image_vote_usa_profile:
        # Update this new image with width, height, original url and version number
        save_source_info_results = we_vote_image_manager.save_we_vote_image_vote_usa_info(
            we_vote_image=we_vote_image,
            image_width=image_width,
            image_height=image_height,
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_voter_uploaded_profile:
        # Update this new image with width, height, original url and version number
        save_source_info_results = we_vote_image_manager.save_we_vote_image_voter_uploaded_info(
            we_vote_image=we_vote_image,
            image_width=image_width,
            image_height=image_height,
            image_url_https=image_url_https,
            same_day_image_version=same_day_image_version,
        )
    elif kind_of_image_wikipedia_profile:
        # image url is valid so store source image of wikipedia to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_wikipedia_info(
            we_vote_image, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_wikipedia_profile)
    else:
        save_source_info_results = {
            'status':           "KIND_OF_IMAGE_INVALID ",
            'success':          False,
            'we_vote_image':    None,
        }

    status += " " + save_source_info_results['status']
    if save_source_info_results['success']:
        image_stored_from_source = True
        date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                       we_vote_image.date_image_saved.day,
                                                       year=we_vote_image.date_image_saved.year)
        # ex twitter_profile_image_master-2017210_1_48x48.png
        if convert_image_to_jpg:
            image_format_filtered = 'jpg'
        else:
            image_format_filtered = image_format
        we_vote_image_file_name = "{image_type}-{date_image_saved}_{counter}_" \
                                  "{image_width}x{image_height}.{image_format}" \
                                  "".format(image_type=image_type,
                                            date_image_saved=date_image_saved,
                                            counter=str(same_day_image_version),
                                            image_width=str(image_width),
                                            image_height=str(image_height),
                                            image_format=str(image_format_filtered))
        if campaignx_we_vote_id:
            we_vote_image_file_location = campaignx_we_vote_id + "/" + we_vote_image_file_name
        elif candidate_we_vote_id:
            we_vote_image_file_location = candidate_we_vote_id + "/" + we_vote_image_file_name
        elif issue_we_vote_id:
            we_vote_image_file_location = issue_we_vote_id + "/" + we_vote_image_file_name
        elif organization_we_vote_id:
            we_vote_image_file_location = organization_we_vote_id + "/" + we_vote_image_file_name
        elif politician_we_vote_id:
            we_vote_image_file_location = politician_we_vote_id + "/" + we_vote_image_file_name
        elif representative_we_vote_id:
            we_vote_image_file_location = representative_we_vote_id + "/" + we_vote_image_file_name
        elif voter_we_vote_id:
            we_vote_image_file_location = voter_we_vote_id + "/" + we_vote_image_file_name
        else:
            we_vote_image_file_location = "missing_id/" + we_vote_image_file_name


        image_stored_locally = we_vote_image_manager.store_image_locally(
                image_url_https, we_vote_image_file_name)
        if not image_stored_locally:
            status += " IMAGE_NOT_STORED_LOCALLY1 "
            error_results = {
                'success':                      success,
                'status':                       status,
                'we_vote_image_created':        we_vote_image_created,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         False,
                'resized_image_created':        resized_image_created,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        status += " IMAGE_STORED_LOCALLY "
        resized_image_created = we_vote_image_manager.resize_we_vote_master_image(
            image_local_path=we_vote_image_file_name,
            image_width=image_width,
            image_height=image_height,
            image_type=image_type,
            image_offset_x=image_offset_x,
            image_offset_y=image_offset_y,
            convert_image_to_jpg=convert_image_to_jpg)
        if not resized_image_created:
            status += " IMAGE_NOT_STORED_LOCALLY2 "
            error_results = {
                'success':                      success,
                'status':                       status,
                'we_vote_image_created':        we_vote_image_created,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         image_stored_locally,
                'resized_image_created':        False,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        status += " RESIZED_IMAGE_CREATED "
        image_stored_to_aws = we_vote_image_manager.store_image_to_aws(
            we_vote_image_file_name=we_vote_image_file_name,
            we_vote_image_file_location=we_vote_image_file_location,
            image_format=image_format_filtered)
        if not image_stored_to_aws:
            status += " IMAGE_NOT_STORED_TO_AWS "
            error_results = {
                'success':                      success,
                'status':                       status,
                'we_vote_image_created':        we_vote_image_created,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         image_stored_locally,
                'resized_image_created':        resized_image_created,
                'image_stored_to_aws':          False,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                            "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                      we_vote_image_file_location=we_vote_image_file_location)
        # if we_vote_image_url is not empty then save we_vote_image_wes_info else delete we_vote_image entry
        if we_vote_image_url is not None and we_vote_image_url != "":
            # logger.error('(Ok) New image created in cache_resized_image_locally we_vote_image_url: %s' %
            #              we_vote_image_url)
            save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(
                we_vote_image,
                we_vote_image_url=we_vote_image_url,
                we_vote_image_file_location=we_vote_image_file_location,
                we_vote_parent_image_id=we_vote_parent_image_id,
                is_active_version=is_active_version)
        else:
            status += " WE_VOTE_IMAGE_URL_IS_EMPTY "
            error_results = {
                'success':                  success,
                'status':                   status,
                'we_vote_image_created':    we_vote_image_created,
                'image_stored_from_source': image_stored_from_source,
                'image_stored_locally':     image_stored_locally,
                'resized_image_created':    resized_image_created,
                'image_stored_to_aws':      image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        status += " IMAGE_STORED_TO_AWS " + save_aws_info['status']
        success = save_aws_info['success']
        if not success:
            error_results = {
                'success':                  success,
                'status':                   status,
                'we_vote_image_created':    we_vote_image_created,
                'image_stored_from_source': image_stored_from_source,
                'image_stored_locally':     image_stored_locally,
                'resized_image_created':    resized_image_created,
                'image_stored_to_aws':      image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

    else:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_stored_from_source':     False,
            'image_stored_locally':         image_stored_locally,
            'resized_image_created':        resized_image_created,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_locally':         image_stored_locally,
        'resized_image_created':        resized_image_created,
        'image_stored_to_aws':          image_stored_to_aws,
    }
    log_and_time_cache_action(False, time0, 'cache_resized_image_locally')
    return results


def create_resized_images(
        ballotpedia_profile_image_url=None,
        campaignx_photo_url_https=None,
        campaignx_we_vote_id=None,
        candidate_we_vote_id=None,
        facebook_background_image_url_https=None,
        facebook_profile_image_url_https=None,
        linkedin_profile_image_url=None,
        maplight_image_url_https=None,
        organization_we_vote_id=None,
        organization_uploaded_profile_image_url_https=None,
        other_source_image_url=None,
        photo_url_from_ctcl=None,
        photo_url_from_vote_usa=None,
        politician_uploaded_profile_image_url_https=None,
        politician_we_vote_id=None,
        representative_we_vote_id=None,
        twitter_profile_image_url_https=None,
        twitter_profile_background_image_url_https=None,
        twitter_profile_banner_url_https=None,
        vote_smart_image_url_https=None,
        voter_uploaded_profile_image_url_https=None,
        voter_we_vote_id=None,
        wikipedia_profile_image_url=None,
        we_vote_image_url=None,
):
    """
    Create resized images
    :param ballotpedia_profile_image_url:
    :param campaignx_photo_url_https:
    :param campaignx_we_vote_id:
    :param candidate_we_vote_id:
    :param facebook_background_image_url_https:
    :param facebook_profile_image_url_https:
    :param linkedin_profile_image_url:
    :param maplight_image_url_https:
    :param organization_uploaded_profile_image_url_https:
    :param organization_we_vote_id:
    :param other_source_image_url:
    :param photo_url_from_ctcl:
    :param photo_url_from_vote_usa:
    :param politician_uploaded_profile_image_url_https:
    :param politician_we_vote_id:
    :param representative_we_vote_id:
    :param twitter_profile_image_url_https:
    :param twitter_profile_background_image_url_https:
    :param twitter_profile_banner_url_https:
    :param vote_smart_image_url_https:
    :param voter_uploaded_profile_image_url_https:
    :param voter_we_vote_id:
    :param wikipedia_profile_image_url:
    :param we_vote_image_url:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_resized_images')
    cached_master_image_url = None
    cached_resized_image_url_large = None
    cached_resized_image_url_medium = None
    cached_resized_image_url_tiny = None

    we_vote_image_manager = WeVoteImageManager()
    # Retrieve cached master image url from WeVoteImage table
    cached_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
        ballotpedia_profile_image_url=ballotpedia_profile_image_url,
        campaignx_we_vote_id=campaignx_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        campaignx_photo_url_https=campaignx_photo_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        kind_of_image_original=True,
        linkedin_profile_image_url=linkedin_profile_image_url,
        maplight_image_url_https=maplight_image_url_https,
        organization_uploaded_profile_image_url_https=organization_uploaded_profile_image_url_https,
        organization_we_vote_id=organization_we_vote_id,
        other_source_image_url=other_source_image_url,
        photo_url_from_ctcl=photo_url_from_ctcl,
        photo_url_from_vote_usa=photo_url_from_vote_usa,
        politician_uploaded_profile_image_url_https=politician_uploaded_profile_image_url_https,
        politician_we_vote_id=politician_we_vote_id,
        representative_we_vote_id=representative_we_vote_id,
        twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
        twitter_profile_banner_url_https=twitter_profile_banner_url_https,
        twitter_profile_image_url_https=twitter_profile_image_url_https,
        vote_smart_image_url_https=vote_smart_image_url_https,
        voter_uploaded_profile_image_url_https=voter_uploaded_profile_image_url_https,
        voter_we_vote_id=voter_we_vote_id,
        wikipedia_profile_image_url=wikipedia_profile_image_url,
        we_vote_image_url=we_vote_image_url,
    )
    if cached_we_vote_image_results['we_vote_image_found']:
        cached_we_vote_image = cached_we_vote_image_results['we_vote_image']
        cached_master_image_url = cached_we_vote_image.we_vote_image_url

        # Create resized large image if not created before
        create_resized_image_results = create_resized_image_if_not_created(cached_we_vote_image)
        # Retrieve resized large version image url
        if create_resized_image_results['cached_large_image']:
            cached_resized_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                ballotpedia_profile_image_url=ballotpedia_profile_image_url,
                campaignx_photo_url_https=campaignx_photo_url_https,
                campaignx_we_vote_id=campaignx_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                facebook_background_image_url_https=facebook_background_image_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                kind_of_image_large=True,
                linkedin_profile_image_url=linkedin_profile_image_url,
                maplight_image_url_https=maplight_image_url_https,
                organization_uploaded_profile_image_url_https=organization_uploaded_profile_image_url_https,
                organization_we_vote_id=organization_we_vote_id,
                other_source_image_url=other_source_image_url,
                photo_url_from_ctcl=photo_url_from_ctcl,
                photo_url_from_vote_usa=photo_url_from_vote_usa,
                politician_uploaded_profile_image_url_https=politician_uploaded_profile_image_url_https,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                vote_smart_image_url_https=vote_smart_image_url_https,
                voter_uploaded_profile_image_url_https=voter_uploaded_profile_image_url_https,
                voter_we_vote_id=voter_we_vote_id,
                wikipedia_profile_image_url=wikipedia_profile_image_url,
            )
            if cached_resized_we_vote_image_results['success']:
                cached_resized_we_vote_image = cached_resized_we_vote_image_results['we_vote_image']
                cached_resized_image_url_large = cached_resized_we_vote_image.we_vote_image_url

        if create_resized_image_results['cached_medium_image']:
            # Retrieve resized medium version image url
            cached_resized_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                ballotpedia_profile_image_url=ballotpedia_profile_image_url,
                campaignx_photo_url_https=campaignx_photo_url_https,
                campaignx_we_vote_id=campaignx_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                facebook_background_image_url_https=facebook_background_image_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                kind_of_image_medium=True,
                linkedin_profile_image_url=linkedin_profile_image_url,
                maplight_image_url_https=maplight_image_url_https,
                organization_uploaded_profile_image_url_https=organization_uploaded_profile_image_url_https,
                organization_we_vote_id=organization_we_vote_id,
                other_source_image_url=other_source_image_url,
                photo_url_from_ctcl=photo_url_from_ctcl,
                photo_url_from_vote_usa=photo_url_from_vote_usa,
                politician_uploaded_profile_image_url_https=politician_uploaded_profile_image_url_https,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                vote_smart_image_url_https=vote_smart_image_url_https,
                voter_uploaded_profile_image_url_https=voter_uploaded_profile_image_url_https,
                voter_we_vote_id=voter_we_vote_id,
                wikipedia_profile_image_url=wikipedia_profile_image_url,
            )
            if cached_resized_we_vote_image_results['success']:
                cached_resized_we_vote_image = cached_resized_we_vote_image_results['we_vote_image']
                cached_resized_image_url_medium = cached_resized_we_vote_image.we_vote_image_url

        if create_resized_image_results['cached_tiny_image']:
            # Retrieve resized tiny version image url
            cached_resized_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                ballotpedia_profile_image_url=ballotpedia_profile_image_url,
                campaignx_photo_url_https=campaignx_photo_url_https,
                campaignx_we_vote_id=campaignx_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                facebook_background_image_url_https=facebook_background_image_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                kind_of_image_tiny=True,
                linkedin_profile_image_url=linkedin_profile_image_url,
                maplight_image_url_https=maplight_image_url_https,
                organization_uploaded_profile_image_url_https=organization_uploaded_profile_image_url_https,
                organization_we_vote_id=organization_we_vote_id,
                other_source_image_url=other_source_image_url,
                photo_url_from_ctcl=photo_url_from_ctcl,
                photo_url_from_vote_usa=photo_url_from_vote_usa,
                politician_uploaded_profile_image_url_https=politician_uploaded_profile_image_url_https,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                vote_smart_image_url_https=vote_smart_image_url_https,
                voter_uploaded_profile_image_url_https=voter_uploaded_profile_image_url_https,
                voter_we_vote_id=voter_we_vote_id,
                wikipedia_profile_image_url=wikipedia_profile_image_url,
            )
            if cached_resized_we_vote_image_results['success']:
                cached_resized_we_vote_image = cached_resized_we_vote_image_results['we_vote_image']
                cached_resized_image_url_tiny = cached_resized_we_vote_image.we_vote_image_url
    results = {
        'cached_master_image_url':          cached_master_image_url,
        'cached_resized_image_url_large':   cached_resized_image_url_large,
        'cached_resized_image_url_medium':  cached_resized_image_url_medium,
        'cached_resized_image_url_tiny':    cached_resized_image_url_tiny
    }
    log_and_time_cache_action(False, time0, 'cache_resized_images')
    return results


def cache_master_and_resized_image(
        ballotpedia_profile_image_url=None,
        candidate_id=None,
        candidate_we_vote_id=None,
        facebook_background_image_url_https=None,
        facebook_background_image_offset_x=None,
        facebook_background_image_offset_y=None,
        facebook_profile_image_url_https=None,
        facebook_user_id=None,
        image_source=None,
        linkedin_profile_image_url=None,
        maplight_id=None,
        maplight_image_url_https=None,
        organization_id=None,
        organization_we_vote_id=None,
        other_source_image_url=None,
        other_source=None,
        photo_url_from_ctcl=None,
        photo_url_from_vote_usa=None,
        politician_id=None,
        politician_we_vote_id=None,
        representative_id=None,
        representative_we_vote_id=None,
        twitter_id=None,
        twitter_profile_image_url_https=None,
        twitter_profile_background_image_url_https=None,
        twitter_profile_banner_url_https=None,
        twitter_screen_name=None,
        voter_id=None,
        voter_we_vote_id=None,
        vote_smart_id=None,
        vote_smart_image_url_https=None,
        wikipedia_profile_image_url=None):
    """
    Start with URL of image hosted on another server, cache it on the We Vote network,
    as well as re-sized images. Return cached urls
    :param ballotpedia_profile_image_url:
    :param candidate_id:
    :param candidate_we_vote_id:
    :param facebook_background_image_url_https:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :param facebook_profile_image_url_https:
    :param facebook_user_id:
    :param image_source:
    :param linkedin_profile_image_url:
    :param maplight_id:
    :param maplight_image_url_https:
    :param organization_id:
    :param organization_we_vote_id:
    :param other_source_image_url:
    :param other_source:
    :param photo_url_from_ctcl:
    :param photo_url_from_vote_usa:
    :param politician_id:
    :param politician_we_vote_id:
    :param representative_id:
    :param representative_we_vote_id:
    :param twitter_id:
    :param twitter_profile_image_url_https:
    :param twitter_profile_background_image_url_https:
    :param twitter_profile_banner_url_https:
    :param twitter_screen_name:
    :param voter_id:
    :param voter_we_vote_id:
    :param vote_smart_id:
    :param vote_smart_image_url_https:
    :param wikipedia_profile_image_url:
    :return:
    """
    # print('---------------- cache_master_and_resized_image ------------------')
    time0 = log_and_time_cache_action(True, 0, 'cache_master_and_resized_image')
    status = ''
    success = True
    cached_ballotpedia_image_url_https = None
    cached_ctcl_profile_image_url_https = None
    cached_facebook_profile_image_url_https = None
    cached_facebook_background_image_url_https = None
    cached_facebook_background_image_url_large = None
    cached_linkedin_image_url_https = None
    cached_maplight_image_url_https = None
    cached_other_source_image_url_https = None
    cached_twitter_profile_background_image_url_https = None
    cached_twitter_profile_background_image_url_large = None
    cached_twitter_profile_banner_url_https = None
    cached_twitter_profile_banner_url_large = None
    cached_twitter_profile_image_url_https = None
    cached_vote_smart_image_url_https = None
    cached_vote_usa_profile_image_url_https = None
    cached_wikipedia_image_url_https = None
    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None

    try:
        # caching refreshed new images to s3 aws
        cache_master_images_results = cache_master_images(
            ballotpedia_profile_image_url=ballotpedia_profile_image_url,
            candidate_id=candidate_id,
            candidate_we_vote_id=candidate_we_vote_id,
            facebook_background_image_url_https=facebook_background_image_url_https,
            facebook_background_image_offset_x=facebook_background_image_offset_x,
            facebook_background_image_offset_y=facebook_background_image_offset_y,
            facebook_user_id=facebook_user_id,
            facebook_profile_image_url_https=facebook_profile_image_url_https,
            image_source=image_source,
            linkedin_profile_image_url=linkedin_profile_image_url,
            maplight_id=maplight_id,
            maplight_image_url_https=maplight_image_url_https,
            organization_id=organization_id,
            organization_we_vote_id=organization_we_vote_id,
            other_source_image_url=other_source_image_url,
            other_source=other_source,
            photo_url_from_ctcl=photo_url_from_ctcl,
            photo_url_from_vote_usa=photo_url_from_vote_usa,
            politician_id=politician_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_id=representative_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            twitter_profile_image_url_https=twitter_profile_image_url_https,
            twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
            twitter_profile_banner_url_https=twitter_profile_banner_url_https,
            vote_smart_id=vote_smart_id,
            vote_smart_image_url_https=vote_smart_image_url_https,
            voter_id=voter_id,
            voter_we_vote_id=voter_we_vote_id,
            wikipedia_profile_image_url=wikipedia_profile_image_url)
    except Exception as e:
        status += "ERROR_IN-cache_master_images: " + str(e) + " "
        print(" ------- --------- ERROR_IN-cache_master_images: " + str(e))
        cache_master_images_results['cached_ballotpedia_image'] = False
        success = False

    if cache_master_images_results['cached_ballotpedia_image'] is True or \
            cache_master_images_results['cached_ballotpedia_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                ballotpedia_profile_image_url=ballotpedia_profile_image_url)
            cached_ballotpedia_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_BALLOTPEDIA-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_ctcl_profile_image'] is True or \
            cache_master_images_results['cached_ctcl_profile_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                photo_url_from_ctcl=photo_url_from_ctcl)
            cached_ctcl_profile_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_CTCL-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_facebook_profile_image'] is True or \
            cache_master_images_results['cached_facebook_profile_image'] == IMAGE_ALREADY_CACHED:
        try:
            # NOTE 2021-07-17 I think we want to start calling facebook_profile_image_url_https ->
            # photo_download_url_from_facebook since facebook_profile_image_url_https isn't stored on We Vote servers
            # yet at this point and (2023-01-14) that link and hash is reused throughout the day as the voters facebook
            # profile picture is changed by the voter
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                facebook_profile_image_url_https=facebook_profile_image_url_https)
            cached_facebook_profile_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_FACEBOOK_PROFILE-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_facebook_background_image'] is True or \
            cache_master_images_results['cached_facebook_background_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                facebook_background_image_url_https=facebook_background_image_url_https)
            cached_facebook_background_image_url_https = create_resized_image_results['cached_master_image_url']
            cached_facebook_background_image_url_large = create_resized_image_results['cached_resized_image_url_large']
        except Exception as e:
            status += "ERROR_IN_FACEBOOK_BACKGROUND-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_linkedin_image'] is True or \
            cache_master_images_results['cached_linkedin_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                linkedin_profile_image_url=linkedin_profile_image_url)
            cached_linkedin_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_LINKEDIN-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_maplight_image'] is True or \
            cache_master_images_results['cached_maplight_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                maplight_image_url_https=maplight_image_url_https)
            cached_maplight_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_MAPLIGHT-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_other_source_image'] is True or \
            cache_master_images_results['cached_other_source_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                other_source_image_url=other_source_image_url)
            cached_other_source_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_OTHER-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_twitter_background_image'] is True or \
            cache_master_images_results['cached_twitter_background_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https)
            cached_twitter_profile_background_image_url_https = create_resized_image_results['cached_master_image_url']
            cached_twitter_profile_background_image_url_large = \
                create_resized_image_results['cached_resized_image_url_large']
        except Exception as e:
            status += "ERROR_IN_TWITTER_BACKGROUND-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_twitter_banner_image'] is True or \
            cache_master_images_results['cached_twitter_banner_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https)
            cached_twitter_profile_banner_url_https = create_resized_image_results['cached_master_image_url']
            cached_twitter_profile_banner_url_large = create_resized_image_results['cached_resized_image_url_large']
        except Exception as e:
            status += "ERROR_IN_TWITTER_BANNER-create_resized_images: " + str(e) + " "
            success = False

    # If cached master image or image is already cached then create all resized images for master image
    if cache_master_images_results['cached_twitter_profile_image'] is True or \
            cache_master_images_results['cached_twitter_profile_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                twitter_profile_image_url_https=twitter_profile_image_url_https)
            cached_twitter_profile_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_TWITTER_PROFILE-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_vote_smart_image'] is True or \
            cache_master_images_results['cached_vote_smart_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                vote_smart_image_url_https=vote_smart_image_url_https)
            cached_vote_smart_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_VOTE_SMART-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_vote_usa_profile_image'] is True or \
            cache_master_images_results['cached_vote_usa_profile_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                photo_url_from_vote_usa=photo_url_from_vote_usa)
            cached_vote_usa_profile_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_VOTE_USA-create_resized_images: " + str(e) + " "
            success = False

    if cache_master_images_results['cached_wikipedia_image'] is True or \
            cache_master_images_results['cached_wikipedia_image'] == IMAGE_ALREADY_CACHED:
        try:
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                representative_we_vote_id=representative_we_vote_id,
                wikipedia_profile_image_url=wikipedia_profile_image_url)
            cached_wikipedia_image_url_https = create_resized_image_results['cached_master_image_url']
            we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']
        except Exception as e:
            status += "ERROR_IN_WIKIPEDIA-create_resized_images: " + str(e) + " "
            success = False

    results = {
        'cached_ballotpedia_image_url_https':                   cached_ballotpedia_image_url_https,
        'cached_ctcl_profile_image_url_https':                  cached_ctcl_profile_image_url_https,
        'cached_facebook_profile_image_url_https':              cached_facebook_profile_image_url_https,
        'cached_facebook_background_image_url_https':           cached_facebook_background_image_url_https,
        'cached_facebook_background_image_url_large':           cached_facebook_background_image_url_large,
        'cached_linkedin_image_url_https':                      cached_linkedin_image_url_https,
        'cached_maplight_image_url_https':                      cached_maplight_image_url_https,
        'cached_other_source_image_url_https':                  cached_other_source_image_url_https,
        'cached_twitter_profile_image_url_https':               cached_twitter_profile_image_url_https,
        'cached_twitter_profile_background_image_url_https':    cached_twitter_profile_background_image_url_https,
        'cached_twitter_profile_background_image_url_large':    cached_twitter_profile_background_image_url_large,
        'cached_twitter_profile_banner_url_https':              cached_twitter_profile_banner_url_https,
        'cached_twitter_profile_banner_url_large':              cached_twitter_profile_banner_url_large,
        'cached_vote_smart_image_url_https':                    cached_vote_smart_image_url_https,
        'cached_vote_usa_profile_image_url_https':              cached_vote_usa_profile_image_url_https,
        'cached_wikipedia_image_url_https':                     cached_wikipedia_image_url_https,
        'status':                                               status,
        'success':                                              success,
        'we_vote_hosted_profile_image_url_large':               we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':              we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':                we_vote_hosted_profile_image_url_tiny
    }
    log_and_time_cache_action(False, time0, 'cache_master_and_resized_image')
    return results


def cache_master_images(
        ballotpedia_profile_image_url=None,
        candidate_id=None,
        candidate_we_vote_id=None,
        facebook_user_id=None,
        facebook_profile_image_url_https=None,
        facebook_background_image_url_https=None,
        facebook_background_image_offset_x=None,
        facebook_background_image_offset_y=None,
        image_source=None,
        linkedin_profile_image_url=None,
        maplight_id=None,
        maplight_image_url_https=None,
        organization_id=None,
        organization_we_vote_id=None,
        other_source_image_url=None,
        other_source=None,
        photo_url_from_ctcl=None,
        photo_url_from_vote_usa=None,
        politician_id=None,
        politician_we_vote_id=None,
        representative_id=None,
        representative_we_vote_id=None,
        twitter_id=None,
        twitter_screen_name=None,
        twitter_profile_image_url_https=None,
        twitter_profile_background_image_url_https=None,
        twitter_profile_banner_url_https=None,
        voter_id=None,
        voter_we_vote_id=None,
        vote_smart_id=None,
        vote_smart_image_url_https=None,
        wikipedia_profile_image_url=None):
    """
    Collect all kind of images from URLs hosted outside of the We Vote network, and cache them locally
    for a candidate or an organization such as profile, background
    :param ballotpedia_profile_image_url:
    :param candidate_id:
    :param candidate_we_vote_id:
    :param facebook_user_id:
    :param facebook_profile_image_url_https:
    :param facebook_background_image_url_https:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :param image_source:
    :param linkedin_profile_image_url:
    :param maplight_id:
    :param maplight_image_url_https:
    :param organization_id:
    :param organization_we_vote_id:
    :param other_source_image_url:
    :param other_source:
    :param photo_url_from_ctcl:
    :param photo_url_from_vote_usa:
    :param politician_id:
    :param politician_we_vote_id:
    :param representative_id:
    :param representative_we_vote_id:
    :param twitter_id:
    :param twitter_screen_name:
    :param twitter_profile_image_url_https:
    :param twitter_profile_background_image_url_https:
    :param twitter_profile_banner_url_https:
    :param voter_id:
    :param voter_we_vote_id:
    :param vote_smart_id:
    :param vote_smart_image_url_https:
    :param wikipedia_profile_image_url:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_master_images')
    cache_all_kind_of_images_results = {
        'candidate_id':                     candidate_id,
        'candidate_we_vote_id':             candidate_we_vote_id,
        'cached_ballotpedia_image':         False,
        'cached_ctcl_profile_image':        False,
        'cached_facebook_profile_image':    False,
        'cached_facebook_background_image': False,
        'cached_linkedin_image':            False,
        'cached_maplight_image':            False,
        'cached_other_source_image':        False,
        'cached_twitter_background_image':  False,
        'cached_twitter_banner_image':      False,
        'cached_twitter_profile_image':     False,
        'cached_vote_smart_image':          False,
        'cached_vote_usa_profile_image':    False,
        'cached_wikipedia_image':           False,
        'image_source':                     image_source,
        'organization_id':                  organization_id,
        'organization_we_vote_id':          organization_we_vote_id,
        'politician_id':                    politician_id,
        'politician_we_vote_id':            politician_we_vote_id,
        'representative_id':                representative_id,
        'representative_we_vote_id':        representative_we_vote_id,
        'voter_id':                         voter_id,
        'voter_we_vote_id':                 voter_we_vote_id,
    }
    google_civic_election_id = 0
    we_vote_image_manager = WeVoteImageManager()

    if not ballotpedia_profile_image_url:
        cache_all_kind_of_images_results['cached_ballotpedia_image'] = BALLOTPEDIA_URL_NOT_FOUND
    if not facebook_profile_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_profile_image'] = FACEBOOK_URL_NOT_FOUND
    if not facebook_background_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_background_image'] = FACEBOOK_URL_NOT_FOUND
    if not linkedin_profile_image_url:
        cache_all_kind_of_images_results['cached_linkedin_image'] = LINKEDIN_URL_NOT_FOUND
    if not maplight_image_url_https:
        cache_all_kind_of_images_results['cached_maplight_image'] = MAPLIGHT_URL_NOT_FOUND
    if not other_source_image_url:
        cache_all_kind_of_images_results['cached_other_source_image'] = OTHER_SOURCE_URL_NOT_FOUND
    if not photo_url_from_ctcl:
        cache_all_kind_of_images_results['cached_ctcl_profile_image'] = CTCL_PROFILE_URL_NOT_FOUND
    if not photo_url_from_vote_usa:
        cache_all_kind_of_images_results['cached_vote_usa_profile_image'] = VOTE_USA_PROFILE_URL_NOT_FOUND
    if not twitter_profile_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = TWITTER_URL_NOT_FOUND
    else:
        twitter_profile_image_url_https = we_vote_image_manager.twitter_profile_image_url_https_original(
            twitter_profile_image_url_https)
    if not twitter_profile_background_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_URL_NOT_FOUND
    if not twitter_profile_banner_url_https:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_URL_NOT_FOUND
    if not vote_smart_image_url_https:
        cache_all_kind_of_images_results['cached_vote_smart_image'] = VOTE_SMART_URL_NOT_FOUND
    if not wikipedia_profile_image_url:
        cache_all_kind_of_images_results['cached_wikipedia_image'] = WIKIPEDIA_URL_NOT_FOUND

    if ballotpedia_profile_image_url:
        cache_all_kind_of_images_results['cached_ballotpedia_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=ballotpedia_profile_image_url,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            is_active_version=True,
            kind_of_image_ballotpedia_profile=True,
            kind_of_image_original=True)

    if facebook_profile_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=facebook_profile_image_url_https,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            facebook_user_id=facebook_user_id,
            is_active_version=True,
            kind_of_image_facebook_profile=True,
            kind_of_image_original=True)

        cache_all_kind_of_images_results['cached_facebook_background_image'] = cache_image_if_not_cached(
            candidate_we_vote_id=candidate_we_vote_id,
            google_civic_election_id=google_civic_election_id,
            image_url_https=facebook_background_image_url_https,
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            facebook_user_id=facebook_user_id,
            is_active_version=True,
            kind_of_image_facebook_background=True,
            facebook_background_image_offset_x=facebook_background_image_offset_x,
            facebook_background_image_offset_y=facebook_background_image_offset_y,
            kind_of_image_original=True)

    if linkedin_profile_image_url:
        cache_all_kind_of_images_results['cached_linkedin_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=linkedin_profile_image_url,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            is_active_version=True,
            kind_of_image_linkedin_profile=True,
            kind_of_image_original=True)

    if maplight_image_url_https:
        cache_all_kind_of_images_results['cached_maplight_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=maplight_image_url_https,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            maplight_id=maplight_id,
            is_active_version=True,
            kind_of_image_maplight=True,
            kind_of_image_original=True)

    if other_source_image_url:
        cache_all_kind_of_images_results['cached_other_source_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=other_source_image_url,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            is_active_version=True,
            kind_of_image_other_source=True,
            kind_of_image_original=True,
            other_source=other_source)

    if photo_url_from_ctcl:
        cache_all_kind_of_images_results['cached_ctcl_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=photo_url_from_ctcl,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            is_active_version=True,
            kind_of_image_ctcl_profile=True,
            kind_of_image_original=True)

    if photo_url_from_vote_usa:
        cache_all_kind_of_images_results['cached_vote_usa_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=photo_url_from_vote_usa,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            is_active_version=True,
            kind_of_image_vote_usa_profile=True,
            kind_of_image_original=True)

    if twitter_profile_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=twitter_profile_image_url_https,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            is_active_version=True,
            kind_of_image_twitter_profile=True,
            kind_of_image_original=True)

    if twitter_profile_background_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=twitter_profile_background_image_url_https,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            is_active_version=True,
            kind_of_image_twitter_background=True,
            kind_of_image_original=True)

    if twitter_profile_banner_url_https:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=twitter_profile_banner_url_https,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name,
            is_active_version=True,
            kind_of_image_twitter_banner=True,
            kind_of_image_original=True)

    if vote_smart_image_url_https:
        cache_all_kind_of_images_results['cached_vote_smart_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=vote_smart_image_url_https,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            vote_smart_id=vote_smart_id,
            is_active_version=True,
            kind_of_image_vote_smart=True,
            kind_of_image_original=True)

    if wikipedia_profile_image_url:
        cache_all_kind_of_images_results['cached_wikipedia_image'] = cache_image_if_not_cached(
            google_civic_election_id=google_civic_election_id,
            image_url_https=wikipedia_profile_image_url,
            voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            representative_we_vote_id=representative_we_vote_id,
            is_active_version=True,
            kind_of_image_wikipedia_profile=True,
            kind_of_image_original=True)

    log_and_time_cache_action(False, time0, 'cache_master_images')
    return cache_all_kind_of_images_results


def cache_issue_image_master(google_civic_election_id, issue_image_file, issue_we_vote_id=None,
                             kind_of_image_issue=False, kind_of_image_original=False):
    """
    Cache master issue image to AWS. This function is a more focused version of cache_image_locally (which deals with
    all the standard photos like Facebook, or Twitter).
    :param google_civic_election_id:
    :param issue_image_file:
    :param issue_we_vote_id:
    :param kind_of_image_issue:
    :param kind_of_image_original:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_issue_image_master')
    we_vote_parent_image_id = None
    success = False
    status = ''
    is_active_version = True
    we_vote_image_created = False
    image_url_valid = False
    image_stored_from_source = False
    image_stored_to_aws = False
    image_versions = []

    we_vote_image_manager = WeVoteImageManager()

    # create we_vote_image entry with issue_we_vote_id and google_civic_election_id and kind_of_image
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        google_civic_election_id=google_civic_election_id,
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_original=kind_of_image_original)
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']

    # image file validation and get source image properties
    analyze_source_images_results = analyze_image_file(issue_image_file)

    if not analyze_source_images_results['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID"
    image_width = analyze_source_images_results['image_width']
    image_height = analyze_source_images_results['image_height']
    image_format = analyze_source_images_results['image_format']

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        issue_we_vote_id=issue_we_vote_id,
        kind_of_image_issue=kind_of_image_issue,
        kind_of_image_original=kind_of_image_original)
    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)
    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    image_stored_from_source = True
    date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                   we_vote_image.date_image_saved.day,
                                                   year=we_vote_image.date_image_saved.year)
    # ex issue_image_master-2017210_1_48x48.png
    we_vote_image_file_name = "{image_type}_{master_image}-{date_image_saved}_{counter}_" \
                              "{image_width}x{image_height}.{image_format}" \
                              "".format(image_type=ISSUE_IMAGE_NAME,
                                        master_image=MASTER_IMAGE, date_image_saved=date_image_saved,
                                        counter=str(same_day_image_version),
                                        image_width=str(image_width),
                                        image_height=str(image_height),
                                        image_format=str(image_format))

    we_vote_image_file_location = issue_we_vote_id + "/" + we_vote_image_file_name

    image_stored_to_aws = we_vote_image_manager.store_image_file_to_aws(
        issue_image_file, we_vote_image_file_location)
    if not image_stored_to_aws:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_NOT_STORED_TO_AWS",
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          False,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                        "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                  we_vote_image_file_location=we_vote_image_file_location)
    save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(
        we_vote_image,
        we_vote_image_url=we_vote_image_url,
        we_vote_image_file_location=we_vote_image_file_location,
        we_vote_parent_image_id=we_vote_parent_image_id,
        is_active_version=is_active_version)
    status += " IMAGE_STORED_TO_AWS " + save_aws_info['status']
    success = save_aws_info['success']
    if not success:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    save_source_info_results = we_vote_image_manager.save_we_vote_image_issue_info(
        we_vote_image, analyze_source_images_results['image_width'],
        analyze_source_images_results['image_height'], we_vote_image.we_vote_image_url,
        same_day_image_version, image_url_valid)
    status += " " + save_source_info_results['status']
    if not save_source_info_results['success']:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': False,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    # set active version False for other master images for same candidate/organization
    set_active_version_false_results = we_vote_image_manager.set_active_version_false_for_other_images(
        issue_we_vote_id=issue_we_vote_id,
        image_url_https=we_vote_image.we_vote_image_url,
        kind_of_image_issue=True)

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_to_aws':          image_stored_to_aws,
        'we_vote_image':                we_vote_image
    }
    log_and_time_cache_action(False, time0, 'cache_issue_image_master')
    return results


def cache_organization_sharing_image(
        python_image_library_image=None,
        organization_we_vote_id=None,
        kind_of_image_original=False,
        kind_of_image_chosen_favicon=False,
        kind_of_image_chosen_logo=False,
        kind_of_image_chosen_social_share_master=False):
    """
    Cache master "chosen" images to AWS. This function is a more focused version of cache_image_locally
    (which deals with all the standard profile photos like Facebook, or Twitter).
    :param python_image_library_image:
    :param organization_we_vote_id:
    :param kind_of_image_original:
    :param kind_of_image_chosen_favicon:
    :param kind_of_image_chosen_logo:
    :param kind_of_image_chosen_social_share_master:
    :return:
    """
    time0 = log_and_time_cache_action(True, 0, 'cache_organization_sharing_image')
    we_vote_parent_image_id = None
    success = False
    status = ''
    is_active_version = True
    we_vote_image_created = False
    image_url_valid = False
    image_stored_from_source = False
    image_stored_to_aws = False
    image_versions = []

    we_vote_image_manager = WeVoteImageManager()

    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        organization_we_vote_id=organization_we_vote_id,
        kind_of_image_chosen_favicon=kind_of_image_chosen_favicon,
        kind_of_image_chosen_logo=kind_of_image_chosen_logo,
        kind_of_image_chosen_social_share_master=kind_of_image_chosen_social_share_master,
        kind_of_image_original=kind_of_image_original)
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']

    # image file validation and get source image properties
    analyze_source_images_results = analyze_image_in_memory(python_image_library_image)

    if not analyze_source_images_results['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID ",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          image_stored_to_aws,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID "
    image_width = analyze_source_images_results['image_width']
    image_height = analyze_source_images_results['image_height']
    image_format = analyze_source_images_results['image_format']

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        kind_of_image_chosen_favicon=kind_of_image_chosen_favicon,
        kind_of_image_chosen_logo=kind_of_image_chosen_logo,
        kind_of_image_chosen_social_share_master=kind_of_image_chosen_social_share_master,
        kind_of_image_original=kind_of_image_original,
        organization_we_vote_id=organization_we_vote_id,
    )

    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)

    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    image_stored_from_source = True
    date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                   we_vote_image.date_image_saved.day,
                                                   year=we_vote_image.date_image_saved.year)
    if kind_of_image_chosen_favicon:
        image_type = CHOSEN_FAVICON_NAME
    elif kind_of_image_chosen_logo:
        image_type = CHOSEN_LOGO_NAME
    elif kind_of_image_chosen_social_share_master:
        image_type = CHOSEN_SOCIAL_SHARE_IMAGE_NAME
    else:
        image_type = 'organization_sharing'

    if kind_of_image_original:
        master_image = MASTER_IMAGE
    else:
        master_image = 'calculated'

    # ex issue_image_master-2017210_1_48x48.png
    we_vote_image_file_name = "{image_type}_{master_image}-{date_image_saved}_{counter}_" \
                              "{image_width}x{image_height}.{image_format}" \
                              "".format(image_type=image_type,
                                        master_image=master_image,
                                        date_image_saved=date_image_saved,
                                        counter=str(same_day_image_version),
                                        image_width=str(image_width),
                                        image_height=str(image_height),
                                        image_format=str(image_format))

    we_vote_image_file_location = organization_we_vote_id + "/" + we_vote_image_file_name

    image_stored_locally = we_vote_image_manager.store_python_image_locally(
        python_image_library_image, we_vote_image_file_name)

    if not image_stored_locally:
        error_results = {
            'success': success,
            'status': status + " IMAGE_NOT_STORED_LOCALLY ",
            'we_vote_image_created': we_vote_image_created,
            'image_url_valid': image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_locally': False,
            'image_stored_to_aws': image_stored_to_aws,
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    image_stored_to_aws = we_vote_image_manager.store_image_to_aws(
        we_vote_image_file_name=we_vote_image_file_name,
        we_vote_image_file_location=we_vote_image_file_location,
        image_format=image_format)
    if not image_stored_to_aws:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_NOT_STORED_TO_AWS ",
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_to_aws':          False,
            'we_vote_image':                None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                        "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                  we_vote_image_file_location=we_vote_image_file_location)
    save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(
        we_vote_image,
        we_vote_image_url=we_vote_image_url,
        we_vote_image_file_location=we_vote_image_file_location,
        we_vote_parent_image_id=we_vote_parent_image_id,
        is_active_version=is_active_version)
    status += " IMAGE_STORED_TO_AWS " + save_aws_info['status']
    success = save_aws_info['success']
    if not success:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': image_stored_from_source,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    save_source_info_results = we_vote_image_manager.save_we_vote_image_organization_share_info(
        we_vote_image, analyze_source_images_results['image_width'],
        analyze_source_images_results['image_height'], we_vote_image.we_vote_image_url,
        same_day_image_version, image_url_valid,
        kind_of_image_chosen_favicon=kind_of_image_chosen_favicon, kind_of_image_chosen_logo=kind_of_image_chosen_logo,
        kind_of_image_chosen_social_share_master=kind_of_image_chosen_social_share_master)
    status += " " + save_source_info_results['status']
    if not save_source_info_results['success']:
        error_results = {
            'success':                  success,
            'status':                   status,
            'we_vote_image_created':    we_vote_image_created,
            'image_url_valid':          image_url_valid,
            'image_stored_from_source': False,
            'image_stored_to_aws':      image_stored_to_aws,
            'we_vote_image':            None
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    # set active version False for other master images for same candidate/organization
    set_active_version_false_results = we_vote_image_manager.set_active_version_false_for_other_images(
        organization_we_vote_id=organization_we_vote_id,
        image_url_https=we_vote_image.we_vote_image_url,
        kind_of_image_chosen_favicon=kind_of_image_chosen_favicon,
        kind_of_image_chosen_logo=kind_of_image_chosen_logo,
        kind_of_image_chosen_social_share_master=kind_of_image_chosen_social_share_master)
    status += set_active_version_false_results['status']

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_to_aws':          image_stored_to_aws,
        'we_vote_image':                we_vote_image
    }
    log_and_time_cache_action(False, time0, 'cache_organization_sharing_image')
    return results


def organize_object_photo_fields_based_on_image_type_currently_active(
        object_with_photo_fields=None,
        profile_image_type_currently_active=PROFILE_IMAGE_TYPE_UNKNOWN):
    profile_image_default_updated = False
    save_changes = False
    status = ""
    success = True
    if not hasattr(object_with_photo_fields, 'profile_image_type_currently_active') \
            or not positive_value_exists(profile_image_type_currently_active):
        status += "PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_MISSING "
        results = {
            'success':                          False,
            'status':                           status,
            'object_with_photo_fields':         object_with_photo_fields,
            'profile_image_default_updated':    profile_image_default_updated,
            'save_changes':                     save_changes,
        }
        return results

    object_with_photo_fields.profile_image_type_currently_active = profile_image_type_currently_active
    ballotpedia_image_exists = True \
        if hasattr(object_with_photo_fields, 'we_vote_hosted_profile_ballotpedia_image_url_large') \
           and (
                   positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_ballotpedia_image_url_large) \
                   or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_ballotpedia_image_url_medium) \
                   or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_ballotpedia_image_url_tiny) \
               ) else False
    facebook_image_exists = True \
        if positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_facebook_image_url_large) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_facebook_image_url_medium) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_facebook_image_url_tiny) \
        else False
    linkedin_image_exists = True \
        if hasattr(object_with_photo_fields, 'we_vote_hosted_profile_linkedin_image_url_large') \
           and (
                   positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_linkedin_image_url_large) \
                   or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_linkedin_image_url_medium) \
                   or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_linkedin_image_url_tiny) \
               ) else False
    twitter_image_exists = True \
        if positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_twitter_image_url_large) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_twitter_image_url_medium) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_twitter_image_url_tiny) \
        else False
    uploaded_image_exists = True \
        if positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_uploaded_image_url_large) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_uploaded_image_url_medium) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_uploaded_image_url_tiny) \
        else False
    vote_usa_image_exists = True \
        if positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_vote_usa_image_url_large) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_vote_usa_image_url_medium) \
           or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_vote_usa_image_url_tiny) \
        else False
    wikipedia_image_exists = True \
        if hasattr(object_with_photo_fields, 'we_vote_hosted_profile_wikipedia_image_url_large') \
           and (
                   positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_wikipedia_image_url_large) \
                   or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_wikipedia_image_url_medium) \
                   or positive_value_exists(object_with_photo_fields.we_vote_hosted_profile_wikipedia_image_url_tiny) \
               ) else False
    if object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
        if uploaded_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UPLOADED
            save_changes = True
        elif twitter_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
            save_changes = True
        elif ballotpedia_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_BALLOTPEDIA
            save_changes = True
        elif facebook_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_FACEBOOK
            save_changes = True
        elif linkedin_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_LINKEDIN
            save_changes = True
        elif wikipedia_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_WIKIPEDIA
            save_changes = True
        elif vote_usa_image_exists:
            object_with_photo_fields.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_VOTE_USA
            save_changes = True
    # Now move selected field into master politician image
    if uploaded_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_uploaded_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True
    elif ballotpedia_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_BALLOTPEDIA:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_ballotpedia_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True
    elif twitter_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_twitter_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True
    elif facebook_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_facebook_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True
    elif linkedin_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_LINKEDIN:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_linkedin_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True
    elif wikipedia_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_WIKIPEDIA:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_wikipedia_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True
    elif vote_usa_image_exists and \
            object_with_photo_fields.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_VOTE_USA:
        results = change_default_profile_image_if_needed(
            object_with_photo_fields=object_with_photo_fields,
            new_profile_image_key='we_vote_hosted_profile_vote_usa_image_url')
        if results['save_changes']:
            object_with_photo_fields = results['object_with_photo_fields']
            profile_image_default_updated = True
            save_changes = True

    results = {
        'success':                          success,
        'status':                           status,
        'object_with_photo_fields':         object_with_photo_fields,
        'profile_image_default_updated':    profile_image_default_updated,
        'save_changes':                     save_changes,
    }
    return results
