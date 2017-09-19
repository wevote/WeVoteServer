# image/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .functions import analyze_remote_url, analyze_image_file
from .models import WeVoteImageManager, WeVoteImage, FACEBOOK_PROFILE_IMAGE_NAME, FACEBOOK_BACKGROUND_IMAGE_NAME, \
    TWITTER_PROFILE_IMAGE_NAME, TWITTER_BACKGROUND_IMAGE_NAME, TWITTER_BANNER_IMAGE_NAME, MAPLIGHT_IMAGE_NAME, \
    VOTE_SMART_IMAGE_NAME, MASTER_IMAGE, ISSUE_IMAGE_NAME
from ballot.controllers import choose_election_from_existing_data
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from django.db.models import Q
from import_export_facebook.models import FacebookManager
from import_export_twitter.functions import retrieve_twitter_user_info
from issue.models import IssueManager
from organization.models import OrganizationManager
from politician.models import PoliticianManager
from position.controllers import reset_all_position_image_details_from_candidate, \
    reset_position_for_friends_image_details_from_voter, reset_position_entered_image_details_from_organization
from twitter.models import TwitterUserManager
from voter_guide.models import VoterGuideManager
from voter.models import VoterManager, VoterDeviceLinkManager, VoterAddressManager, VoterAddress, Voter
from wevote_functions.functions import positive_value_exists, convert_to_int
import requests
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)
HTTP_OK = 200
TWITTER = "twitter"
FACEBOOK = "facebook"
MAPLIGHT = "maplight"
VOTE_SMART = "vote_smart"
MAPLIGHT_URL_NOT_FOUND = "maplight url not found"
VOTE_SMART_URL_NOT_FOUND = "votesmart url not found"
FACEBOOK_USER_DOES_NOT_EXIST = "facebook user does not exist"
FACEBOOK_URL_NOT_FOUND = "facebook url not found"
TWITTER_USER_DOES_NOT_EXIST = "twitter user does not exist"
TWITTER_URL_NOT_FOUND = "twitter url not found"
IMAGE_ALREADY_CACHED = "image already cached"
ALL_KIND_OF_IMAGE = ['kind_of_image_twitter_profile', 'kind_of_image_twitter_background',
                     'kind_of_image_twitter_banner', 'kind_of_image_facebook_profile',
                     'kind_of_image_facebook_background', 'kind_of_image_maplight', 'kind_of_image_vote_smart']

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



def cache_all_kind_of_images_locally_for_all_organizations():
    """
    Cache all kind of images locally for all organizations
    :return:
    """
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

    return cache_images_locally_for_all_organizations_results


def cache_all_kind_of_images_locally_for_all_voters():
    """
    Cache all kind of images locally for all voters
    :return:
    """
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

    return cache_images_locally_for_all_voters_results


def cache_image_if_not_cached(google_civic_election_id, image_url_https, voter_we_vote_id=None,
                              candidate_we_vote_id=None, organization_we_vote_id=None, issue_we_vote_id=None,
                              twitter_id=None, twitter_screen_name=None,
                              facebook_user_id=None, maplight_id=None, vote_smart_id=None,
                              is_active_version=False, kind_of_image_twitter_profile=False,
                              kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                              kind_of_image_facebook_profile=False, kind_of_image_facebook_background=False,
                              kind_of_image_maplight=False, kind_of_image_vote_smart=False, kind_of_image_issue=False,
                              kind_of_image_original=False, facebook_background_image_offset_x=None,
                              facebook_background_image_offset_y=None):
    """
    Check if image is already cached or not. If not then cached it.
    :param google_civic_election_id:
    :param image_url_https:
    :param voter_we_vote_id:
    :param candidate_we_vote_id:
    :param organization_we_vote_id:
    :param issue_we_vote_id:
    :param twitter_id:
    :param twitter_screen_name:
    :param facebook_user_id:
    :param maplight_id:
    :param vote_smart_id:
    :param is_active_version:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_maplight:
    :param kind_of_image_vote_smart:
    :param kind_of_image_issue:
    :param kind_of_image_original:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :return:
    """
    we_vote_image_manager = WeVoteImageManager()
    cached_we_vote_image_results = we_vote_image_manager.retrieve_recent_cached_we_vote_image(
        voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
        organization_we_vote_id=organization_we_vote_id, issue_we_vote_id=issue_we_vote_id,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_maplight=kind_of_image_maplight, kind_of_image_vote_smart=kind_of_image_vote_smart,
        kind_of_image_issue=kind_of_image_issue, kind_of_image_original=kind_of_image_original,
        is_active_version=True)

    # If recent cached image matches with the current one the image is already cached
    cached_we_vote_image = cached_we_vote_image_results['we_vote_image']
    if cached_we_vote_image_results['we_vote_image_found'] and \
            image_url_https == cached_we_vote_image.twitter_profile_image_url_https or \
            image_url_https == cached_we_vote_image.twitter_profile_background_image_url_https or \
            image_url_https == cached_we_vote_image.twitter_profile_banner_url_https or \
            image_url_https == cached_we_vote_image.facebook_profile_image_url_https or \
            image_url_https == cached_we_vote_image.facebook_background_image_url_https or \
            image_url_https == cached_we_vote_image.maplight_image_url_https or \
            image_url_https == cached_we_vote_image.vote_smart_image_url_https or \
            image_url_https == cached_we_vote_image.issue_image_url_https:
        cache_image_results = IMAGE_ALREADY_CACHED
    else:
        # Image is not cached so caching it
        cache_image_locally_results = cache_image_locally(
            google_civic_election_id, image_url_https, voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id, organization_we_vote_id=organization_we_vote_id,
            issue_we_vote_id=issue_we_vote_id, twitter_id=twitter_id, facebook_user_id=facebook_user_id,
            maplight_id=maplight_id, vote_smart_id=vote_smart_id,
            twitter_screen_name=twitter_screen_name, is_active_version=is_active_version,
            kind_of_image_twitter_profile=kind_of_image_twitter_profile,
            kind_of_image_twitter_background=kind_of_image_twitter_background,
            kind_of_image_twitter_banner=kind_of_image_twitter_banner,
            kind_of_image_facebook_profile=kind_of_image_facebook_profile,
            kind_of_image_facebook_background=kind_of_image_facebook_background,
            kind_of_image_maplight=kind_of_image_maplight, kind_of_image_vote_smart=kind_of_image_vote_smart,
            kind_of_image_issue=kind_of_image_issue, kind_of_image_original=kind_of_image_original,
            facebook_background_image_offset_x=facebook_background_image_offset_x,
            facebook_background_image_offset_y=facebook_background_image_offset_y,
        )
        cache_image_results = cache_image_locally_results['success']

        set_active_version_false_results = we_vote_image_manager.set_active_version_false_for_other_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, issue_we_vote_id=issue_we_vote_id,
            image_url_https=image_url_https,
            kind_of_image_twitter_profile=kind_of_image_twitter_profile,
            kind_of_image_twitter_background=kind_of_image_twitter_background,
            kind_of_image_twitter_banner=kind_of_image_twitter_banner,
            kind_of_image_facebook_profile=kind_of_image_facebook_profile,
            kind_of_image_facebook_background=kind_of_image_facebook_background,
            kind_of_image_maplight=kind_of_image_maplight, kind_of_image_vote_smart=kind_of_image_vote_smart,
            kind_of_image_issue=kind_of_image_issue)
    return cache_image_results


def cache_organization_master_images(organization_we_vote_id):
    """
    Cache all kind of master images for an organization such as profile, background
    :param organization_we_vote_id:
    :return:
    """
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
            google_civic_election_id, twitter_profile_image_url_https, organization_we_vote_id=organization_we_vote_id,
            twitter_id=twitter_id, twitter_screen_name=twitter_screen_name, is_active_version=True,
            kind_of_image_twitter_profile=True, kind_of_image_original=True)

    if not twitter_profile_background_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_URL_NOT_FOUND
    else:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = cache_image_if_not_cached(
            google_civic_election_id, twitter_profile_background_image_url_https,
            organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name, is_active_version=True,
            kind_of_image_twitter_background=True, kind_of_image_original=True)

    if not twitter_profile_banner_url_https:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_URL_NOT_FOUND
    else:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_if_not_cached(
            google_civic_election_id, twitter_profile_banner_url_https,
            organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name, is_active_version=True,
            kind_of_image_twitter_banner=True, kind_of_image_original=True)

    return cache_all_kind_of_images_results


def cache_voter_master_images(voter_id):
    """
    Cache all kind of images locally for a voter such as profile, background
    :param voter_id:
    :return:
    """
    cache_all_kind_of_images_results = {
        'voter_id':                         voter_id,
        'voter_we_vote_id':                 "",
        'cached_twitter_profile_image':     False,
        'cached_twitter_background_image':  False,
        'cached_twitter_banner_image':      False,
        'cached_facebook_profile_image':    False,
        'cached_facebook_background_image': False
    }
    google_civic_election_id = 0
    twitter_id = None
    facebook_id = None
    voter_address_manager = VoterAddressManager()
    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()

    voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    if not voter_results['voter_found']:
        return cache_all_kind_of_images_results

    voter = voter_results['voter']
    if positive_value_exists(voter.we_vote_id):
        cache_all_kind_of_images_results['voter_we_vote_id'] = voter.we_vote_id
        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(0, voter_id)
        if voter_device_link_results['success']:
            voter_address_results = voter_address_manager.retrieve_address(0, voter_id)
            if voter_address_results['voter_address_found']:
                voter_address = voter_address_results['voter_address']
            else:
                voter_address = VoterAddress()

            results = choose_election_from_existing_data(voter_device_link_results['voter_device_link'],
                                                         0, voter_address)
            google_civic_election_id = results['google_civic_election_id']
    else:
        return cache_all_kind_of_images_results

    # DALE NOTE 2017-04-23 I don't think we want to use the twitter_id stored in the voter table
    # if positive_value_exists(voter.twitter_id):
    #     twitter_id = voter.twitter_id
    # else:
    twitter_user_manager = TwitterUserManager()
    twitter_screen_name = ''
    twitter_link_to_voter_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_voter_we_vote_id(
        voter.we_vote_id)
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
        voter.we_vote_id)
    if facebook_link_to_voter_results['facebook_link_to_voter_found']:
        facebook_id = facebook_link_to_voter_results['facebook_link_to_voter'].facebook_user_id

    if not positive_value_exists(twitter_id) and not positive_value_exists(facebook_id):
        cache_all_kind_of_images_results = {
            'voter_id':                         voter_id,
            'voter_we_vote_id':                 voter.we_vote_id,
            'voter_object':                     voter,
            'cached_twitter_profile_image':     TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_background_image':  TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_banner_image':      TWITTER_USER_DOES_NOT_EXIST,
            'cached_facebook_profile_image':    FACEBOOK_USER_DOES_NOT_EXIST,
            'cached_facebook_background_image': FACEBOOK_USER_DOES_NOT_EXIST
        }
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
                google_civic_election_id, twitter_profile_image_url_https,
                voter_we_vote_id=voter.we_vote_id,
                twitter_id=twitter_id, twitter_screen_name=twitter_screen_name, is_active_version=True,
                kind_of_image_twitter_profile=True, kind_of_image_original=True)

        if not twitter_profile_background_image_url_https:
            cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_twitter_background_image'] = cache_image_if_not_cached(
                google_civic_election_id, twitter_profile_background_image_url_https,
                voter_we_vote_id=voter.we_vote_id, twitter_id=twitter_id,
                twitter_screen_name=twitter_screen_name, is_active_version=True,
                kind_of_image_twitter_background=True, kind_of_image_original=True)

        if not twitter_profile_banner_url_https:
            cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_if_not_cached(
                google_civic_election_id, twitter_profile_banner_url_https,
                voter_we_vote_id=voter.we_vote_id, twitter_id=twitter_id,
                twitter_screen_name=twitter_screen_name, is_active_version=True,
                kind_of_image_twitter_banner=True, kind_of_image_original=True)

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
                google_civic_election_id, facebook_profile_image_url_https,
                voter_we_vote_id=voter.we_vote_id,
                facebook_user_id=facebook_id, is_active_version=True,
                kind_of_image_facebook_profile=True, kind_of_image_original=True)

        if not facebook_background_image_url_https:
            cache_all_kind_of_images_results['cached_facebook_background_image'] = FACEBOOK_URL_NOT_FOUND
        else:
            cache_all_kind_of_images_results['cached_facebook_background_image'] = cache_image_if_not_cached(
                google_civic_election_id, facebook_background_image_url_https,
                voter_we_vote_id=voter.we_vote_id, facebook_user_id=facebook_id,
                is_active_version=True, kind_of_image_facebook_background=True, kind_of_image_original=True)

    return cache_all_kind_of_images_results


def cache_image_locally(google_civic_election_id, image_url_https, voter_we_vote_id=None,
                        candidate_we_vote_id=None, organization_we_vote_id=None, issue_we_vote_id=None,
                        twitter_id=None, twitter_screen_name=None,
                        facebook_user_id=None, other_source=None, maplight_id=None, vote_smart_id=None,
                        other_source_profile_image_url=None,
                        is_active_version=False, kind_of_image_twitter_profile=False,
                        kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                        kind_of_image_facebook_profile=False, kind_of_image_facebook_background=False,
                        kind_of_image_maplight=False, kind_of_image_vote_smart=False, kind_of_image_issue=False,
                        kind_of_image_original=False, kind_of_image_large=False,
                        kind_of_image_medium=False, kind_of_image_tiny=False,
                        facebook_background_image_offset_x=False, facebook_background_image_offset_y=False):
    """
    Cache one type of image
    :param google_civic_election_id:
    :param image_url_https:
    :param voter_we_vote_id:
    :param candidate_we_vote_id:
    :param organization_we_vote_id:
    :param issue_we_vote_id:
    :param twitter_id:
    :param twitter_screen_name:
    :param facebook_user_id:
    :param other_source:                        # can be MapLight or VoteSmart
    :param maplight_id:
    :param vote_smart_id:
    :param other_source_profile_image_url:      # TODO need to find a way to get this
    :param is_active_version:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_maplight:
    :param kind_of_image_vote_smart:
    :param kind_of_image_issue:
    :param kind_of_image_original:
    :param kind_of_image_large:
    :param kind_of_image_medium:
    :param kind_of_image_tiny:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :return:
    """
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
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        google_civic_election_id, voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id, issue_we_vote_id,
        kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner,
        kind_of_image_facebook_profile, kind_of_image_facebook_background, kind_of_image_maplight,
        kind_of_image_vote_smart, kind_of_image_issue, kind_of_image_original, kind_of_image_large,
        kind_of_image_medium, kind_of_image_tiny,
        facebook_background_image_offset_x, facebook_background_image_offset_y)
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
        }
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']

    # saving other source information for that we_vote_image
    save_other_source_info = we_vote_image_manager.save_we_vote_image_other_source_info(
        we_vote_image, other_source, other_source_profile_image_url)
    if save_other_source_info['success']:
        pass

    # Image url validation and get source image properties
    analyze_source_images_results = analyze_source_images(twitter_id, twitter_screen_name,
                                                          facebook_user_id, maplight_id, vote_smart_id, image_url_https,
                                                          kind_of_image_twitter_profile,
                                                          kind_of_image_twitter_background,
                                                          kind_of_image_twitter_banner,
                                                          kind_of_image_facebook_profile,
                                                          kind_of_image_facebook_background, kind_of_image_maplight,
                                                          kind_of_image_vote_smart)

    if not analyze_source_images_results['analyze_image_url_results']['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_source':     image_stored_from_source,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID"

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id, issue_we_vote_id,
        kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner,
        kind_of_image_facebook_profile, kind_of_image_facebook_background, kind_of_image_maplight,
        kind_of_image_vote_smart, kind_of_image_issue, kind_of_image_original)
    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)
    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    if kind_of_image_facebook_profile or kind_of_image_facebook_background:
        # image url is valid so store source image of facebook to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_facebook_info(
            we_vote_image, facebook_user_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_facebook_profile,
            kind_of_image_facebook_background, image_url_valid)
    elif kind_of_image_twitter_profile or kind_of_image_twitter_background or kind_of_image_twitter_banner:
        # image url is valid so store source image of twitter to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(
            we_vote_image, twitter_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_twitter_profile,
            kind_of_image_twitter_background, kind_of_image_twitter_banner, image_url_valid)
    elif kind_of_image_maplight:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_maplight_info(
            we_vote_image, maplight_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_maplight, image_url_valid)
    elif kind_of_image_vote_smart:
        save_source_info_results = we_vote_image_manager.save_we_vote_image_vote_smart_info(
            we_vote_image, vote_smart_id, analyze_source_images_results['analyze_image_url_results']['image_width'],
            analyze_source_images_results['analyze_image_url_results']['image_height'],
            image_url_https, same_day_image_version, kind_of_image_vote_smart, image_url_valid)

    status += " " + save_source_info_results['status']
    if save_source_info_results['success']:
        image_stored_from_source = True
        date_image_saved = "{year}{:02d}{:02d}".format(we_vote_image.date_image_saved.month,
                                                       we_vote_image.date_image_saved.day,
                                                       year=we_vote_image.date_image_saved.year)
        # ex twitter_profile_image_master-2017210_1_48x48.png
        we_vote_image_file_name = "{image_type}_{master_image}-{date_image_saved}_{counter}_" \
                                  "{image_width}x{image_height}.{image_format}" \
                                  "".format(image_type=analyze_source_images_results['image_type'],
                                            master_image=MASTER_IMAGE, date_image_saved=date_image_saved,
                                            counter=str(same_day_image_version),
                                            image_width=str(analyze_source_images_results['analyze_image_url_results']
                                                            ['image_width']),
                                            image_height=str(analyze_source_images_results['analyze_image_url_results']
                                                             ['image_height']),
                                            image_format=str(analyze_source_images_results['analyze_image_url_results']
                                                             ['image_format']))

        if voter_we_vote_id:
            we_vote_image_file_location = voter_we_vote_id + "/" + we_vote_image_file_name
        elif candidate_we_vote_id:
            we_vote_image_file_location = candidate_we_vote_id + "/" + we_vote_image_file_name
        elif organization_we_vote_id:
            we_vote_image_file_location = organization_we_vote_id + "/" + we_vote_image_file_name
        else:
            we_vote_image_file_location = we_vote_image_file_name

        image_stored_locally = we_vote_image_manager.store_image_locally(
            analyze_source_images_results['image_url_https'], we_vote_image_file_name)

        if not image_stored_locally:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_LOCALLY",
                'we_vote_image_created':        we_vote_image_created,
                'image_url_valid':              image_url_valid,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         False,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        status += " IMAGE_STORED_LOCALLY"
        image_stored_to_aws = we_vote_image_manager.store_image_to_aws(
            we_vote_image_file_name, we_vote_image_file_location,
            analyze_source_images_results['analyze_image_url_results']['image_format'])
        if not image_stored_to_aws:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_TO_AWS",
                'we_vote_image_created':        we_vote_image_created,
                'image_url_valid':              image_url_valid,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         image_stored_locally,
                'image_stored_to_aws':          False,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results
        we_vote_image_url = "https://{bucket_name}.s3.amazonaws.com/{we_vote_image_file_location}" \
                            "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                      we_vote_image_file_location=we_vote_image_file_location)
        save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(we_vote_image, we_vote_image_url,
                                                                          we_vote_image_file_location,
                                                                          we_vote_parent_image_id, is_active_version)
        status += " IMAGE_STORED_TO_AWS " + save_aws_info['status']
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
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
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
        }
        delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
        return error_results

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_source':     image_stored_from_source,
        'image_stored_locally':         image_stored_locally,
        'image_stored_to_aws':          image_stored_to_aws,
    }
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

    get_url = "https://graph.facebook.com/v2.7/{facebook_user_id}/picture?width=200&height=200"\
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

    twitter_user_info_results = retrieve_twitter_user_info(twitter_id, twitter_handle='')
    if 'profile_image_url_https' in twitter_user_info_results['twitter_json'] \
            and twitter_user_info_results['twitter_json']['profile_image_url_https']:
        # new twitter image url found
        latest_twitter_profile_image_url = twitter_user_info_results['twitter_json'][
            'profile_image_url_https']

    if 'profile_background_image_url_https' in twitter_user_info_results['twitter_json'] \
            and twitter_user_info_results['twitter_json']['profile_background_image_url_https']:
        # new twitter image url found
        latest_twitter_background_image_url = twitter_user_info_results['twitter_json'][
            'profile_background_image_url_https']

    if 'profile_banner_url' in twitter_user_info_results['twitter_json'] \
            and twitter_user_info_results['twitter_json']['profile_banner_url']:
        # new twitter image url found
        latest_twitter_banner_image_url = twitter_user_info_results['twitter_json'][
            'profile_banner_url']

    results = {
        'latest_twitter_profile_image_url':     latest_twitter_profile_image_url,
        'latest_twitter_background_image_url':  latest_twitter_background_image_url,
        'latest_twitter_banner_image_url':      latest_twitter_banner_image_url,
    }
    return results


def analyze_source_images(twitter_id, twitter_screen_name, facebook_user_id, maplight_id, vote_smart_id,
                          image_url_https, kind_of_image_twitter_profile, kind_of_image_twitter_background,
                          kind_of_image_twitter_banner, kind_of_image_facebook_profile,
                          kind_of_image_facebook_background, kind_of_image_maplight, kind_of_image_vote_smart):
    """
    Checking twitter user images if url is valid and getting image properties
    :param twitter_id:
    :param twitter_screen_name:
    :param facebook_user_id:
    :param maplight_id:
    :param vote_smart_id:
    :param image_url_https:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_maplight:
    :param kind_of_image_vote_smart:
    :return:
    """
    image_type = None
    if kind_of_image_twitter_profile:
        image_type = TWITTER_PROFILE_IMAGE_NAME
    elif kind_of_image_twitter_background:
        image_type = TWITTER_BACKGROUND_IMAGE_NAME
    elif kind_of_image_twitter_banner:
        image_type = TWITTER_BANNER_IMAGE_NAME
    elif kind_of_image_facebook_profile:
        image_type = FACEBOOK_PROFILE_IMAGE_NAME
    elif kind_of_image_facebook_background:
        image_type = FACEBOOK_BACKGROUND_IMAGE_NAME
    elif kind_of_image_maplight:
        image_type = MAPLIGHT_IMAGE_NAME
    elif kind_of_image_vote_smart:
        image_type = VOTE_SMART_IMAGE_NAME

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
    create_all_resized_images_results = []
    we_vote_image_list = WeVoteImage.objects.all()
    # TODO Limit this to organizations only

    for we_vote_image in we_vote_image_list:
        # Iterate through all cached images
        create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
        create_all_resized_images_results.append(create_resized_images_results)
    return create_all_resized_images_results


def create_resized_images_for_all_voters():
    """
    Create resized images for all voters
    :return:
    """
    create_all_resized_images_results = []
    we_vote_image_list = WeVoteImage.objects.all()
    # TODO Limit this to voters only

    for we_vote_image in we_vote_image_list:
        # Iterate through all cached images
        create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
        create_all_resized_images_results.append(create_resized_images_results)
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
        candidate_campaign_manager = CandidateCampaignManager()
        reset_candidate_image_results = candidate_campaign_manager.reset_candidate_image_details(
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
            if we_vote_image.kind_of_image_facebook_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_profile_image_url_https = we_vote_image.facebook_profile_image_url_https
            if we_vote_image.kind_of_image_facebook_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_background_image_url_https = we_vote_image.facebook_background_image_url_https

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
            if we_vote_image.kind_of_image_facebook_profile and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_profile_image_url_https = we_vote_image.facebook_profile_image_url_https
            if we_vote_image.kind_of_image_facebook_background and we_vote_image.kind_of_image_original and \
                    we_vote_image.is_active_version:
                original_facebook_background_image_url_https = we_vote_image.facebook_background_image_url_https

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
    return results


def retrieve_all_images_for_one_candidate(candidate_we_vote_id):
    """
    Retrieve all cached images for one candidate
    :param candidate_we_vote_id:
    :return:
    """
    we_vote_image_list = []
    candidate_manager = CandidateCampaignManager()
    we_vote_image_manager = WeVoteImageManager()

    if positive_value_exists(candidate_we_vote_id):
        # if candidate_we_vote_id is defined then retrieve cached images for that candidate only
        candidate_results = candidate_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        if candidate_results['candidate_campaign_found']:
            we_vote_image_list_results = we_vote_image_manager.\
                retrieve_we_vote_image_list_from_we_vote_id(None, candidate_we_vote_id)
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
        # if candidate_we_vote_id is defined then retrieve cached images for that candidate only
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['organization_found']:
            we_vote_image_list_results = we_vote_image_manager.\
                retrieve_we_vote_image_list_from_we_vote_id(None, None, organization_we_vote_id)
            we_vote_image_list_query = we_vote_image_list_results['we_vote_image_list']
            we_vote_image_list = list(we_vote_image_list_query)

    return we_vote_image_list


def cache_and_create_resized_images_for_organization(organization_we_vote_id):
    """
    Create resized images for specific organization
    :param organization_we_vote_id:
    :return:
    """
    create_all_resized_images_results = []
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
            retrieve_we_vote_image_list_from_we_vote_id(None, None, organization_we_vote_id)
        for we_vote_image in we_vote_image_list_results['we_vote_image_list']:
            # Iterate through all cached images
            create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
            create_resized_images_results.update(cache_images_for_one_organization_results)
            create_all_resized_images_results.append(create_resized_images_results)
        return create_all_resized_images_results


def cache_and_create_resized_images_for_voter(voter_id):
    """
    Create resized images for specific voter_id
    :param voter_id:
    :return:
    """
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
            retrieve_we_vote_image_list_from_we_vote_id(voter_we_vote_id)
        for we_vote_image in we_vote_image_list_results['we_vote_image_list']:
            # Iterate through all cached images
            create_resized_images_results = create_resized_image_if_not_created(we_vote_image)
            create_resized_images_results.update(cache_images_for_a_voter_results)
            create_all_resized_images_results.append(create_resized_images_results)
        return create_all_resized_images_results


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
                retrieve_we_vote_image_list_from_we_vote_id(voter_we_vote_id)
            we_vote_image_list_query = we_vote_image_list_results['we_vote_image_list']
            we_vote_image_list = list(we_vote_image_list_query)

    return we_vote_image_list


def create_resized_image_if_not_created(we_vote_image):
    """
    Create resized images only if not created for we_vote_image object
    :param we_vote_image:
    :return:
    """
    voter_we_vote_id = we_vote_image.voter_we_vote_id
    candidate_we_vote_id = we_vote_image.candidate_we_vote_id
    organization_we_vote_id = we_vote_image.organization_we_vote_id
    google_civic_election_id = we_vote_image.google_civic_election_id
    we_vote_parent_image_id = we_vote_image.id
    twitter_id = we_vote_image.twitter_id
    facebook_user_id = we_vote_image.facebook_user_id
    maplight_id = we_vote_image.maplight_id
    vote_smart_id = we_vote_image.vote_smart_id
    kind_of_image_twitter_profile = we_vote_image.kind_of_image_twitter_profile
    kind_of_image_twitter_background = we_vote_image.kind_of_image_twitter_background
    kind_of_image_twitter_banner = we_vote_image.kind_of_image_twitter_banner
    kind_of_image_facebook_profile = we_vote_image.kind_of_image_facebook_profile
    kind_of_image_facebook_background = we_vote_image.kind_of_image_facebook_background
    kind_of_image_maplight = we_vote_image.kind_of_image_maplight
    kind_of_image_vote_smart = we_vote_image.kind_of_image_vote_smart
    image_offset_x = we_vote_image.facebook_background_image_offset_x
    image_offset_y = we_vote_image.facebook_background_image_offset_y

    if positive_value_exists(we_vote_image.we_vote_image_file_location):
        image_format = we_vote_image.we_vote_image_file_location.split(".")[-1]
    else:
        image_format = ""

    create_resized_image_results = {
        'voter_we_vote_id':                         voter_we_vote_id,
        'candidate_we_vote_id':                     candidate_we_vote_id,
        'organization_we_vote_id':                  organization_we_vote_id,
        'cached_large_image':                       False,
        'cached_medium_image':                      False,
        'cached_tiny_image':                        False,
    }

    if we_vote_image.kind_of_image_twitter_profile:
        image_url_https = we_vote_image.twitter_profile_image_url_https
    elif we_vote_image.kind_of_image_twitter_background:
        image_url_https = we_vote_image.twitter_profile_background_image_url_https
    elif we_vote_image.kind_of_image_twitter_banner:
        image_url_https = we_vote_image.twitter_profile_banner_url_https
    elif we_vote_image.kind_of_image_facebook_profile:
        image_url_https = we_vote_image.facebook_profile_image_url_https
    elif we_vote_image.kind_of_image_facebook_background:
        image_url_https = we_vote_image.facebook_background_image_url_https
    elif we_vote_image.kind_of_image_maplight:
        image_url_https = we_vote_image.maplight_image_url_https
    elif we_vote_image.kind_of_image_vote_smart:
        image_url_https = we_vote_image.vote_smart_image_url_https
    else:
        image_url_https = ''

    # Check if resized image versions exist or not
    resized_version_exists_results = check_resized_version_exists(
        voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
        organization_we_vote_id=organization_we_vote_id, image_url_https=image_url_https,
        kind_of_image_twitter_profile=kind_of_image_twitter_profile,
        kind_of_image_twitter_background=kind_of_image_twitter_background,
        kind_of_image_twitter_banner=kind_of_image_twitter_banner,
        kind_of_image_facebook_profile=kind_of_image_facebook_profile,
        kind_of_image_facebook_background=kind_of_image_facebook_background,
        kind_of_image_maplight=kind_of_image_maplight,
        kind_of_image_vote_smart=kind_of_image_vote_smart
    )
    if not resized_version_exists_results['large_image_version_exists']:
        # Large version does not exist so create resize image and cache it
        cache_resized_image_locally_results = cache_resized_image_locally(
            google_civic_election_id, image_url_https, we_vote_parent_image_id,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id, facebook_user_id=facebook_user_id,
            maplight_id=maplight_id, vote_smart_id=vote_smart_id, image_format=image_format,
            kind_of_image_twitter_profile=kind_of_image_twitter_profile,
            kind_of_image_twitter_background=kind_of_image_twitter_background,
            kind_of_image_twitter_banner=kind_of_image_twitter_banner,
            kind_of_image_facebook_profile=kind_of_image_facebook_profile,
            kind_of_image_facebook_background=kind_of_image_facebook_background,
            kind_of_image_maplight=kind_of_image_maplight, kind_of_image_vote_smart=kind_of_image_vote_smart,
            kind_of_image_large=True, image_offset_x=image_offset_x, image_offset_y=image_offset_y)
        create_resized_image_results['cached_large_image'] = \
            cache_resized_image_locally_results['success']
    else:
        create_resized_image_results['cached_large_image'] = IMAGE_ALREADY_CACHED

    if we_vote_image.kind_of_image_twitter_profile or we_vote_image.kind_of_image_facebook_profile or \
            we_vote_image.kind_of_image_maplight or we_vote_image.kind_of_image_vote_smart:
        if not resized_version_exists_results['medium_image_version_exists']:
            # Medium version does not exist so create resize image and cache it
            cache_resized_image_locally_results = cache_resized_image_locally(
                google_civic_election_id, image_url_https, we_vote_parent_image_id,
                voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id,
                facebook_user_id=facebook_user_id, maplight_id=maplight_id, vote_smart_id=vote_smart_id,
                image_format=image_format, kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background,
                kind_of_image_maplight=kind_of_image_maplight, kind_of_image_vote_smart=kind_of_image_vote_smart,
                kind_of_image_medium=True, image_offset_x=image_offset_x, image_offset_y=image_offset_y)
            create_resized_image_results['cached_medium_image'] = \
                cache_resized_image_locally_results['success']
        else:
            create_resized_image_results['cached_medium_image'] = IMAGE_ALREADY_CACHED

        if not resized_version_exists_results['tiny_image_version_exists']:
            # Tiny version does not exist so create resize image and cache it
            cache_resized_image_locally_results = cache_resized_image_locally(
                google_civic_election_id, image_url_https, we_vote_parent_image_id,
                voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id,
                facebook_user_id=facebook_user_id, maplight_id=maplight_id, vote_smart_id=vote_smart_id,
                image_format=image_format, kind_of_image_twitter_profile=kind_of_image_twitter_profile,
                kind_of_image_twitter_background=kind_of_image_twitter_background,
                kind_of_image_twitter_banner=kind_of_image_twitter_banner,
                kind_of_image_facebook_profile=kind_of_image_facebook_profile,
                kind_of_image_facebook_background=kind_of_image_facebook_background,
                kind_of_image_maplight=kind_of_image_maplight, kind_of_image_vote_smart=kind_of_image_vote_smart,
                kind_of_image_tiny=True, image_offset_x=image_offset_x, image_offset_y=image_offset_y)
            create_resized_image_results['cached_tiny_image'] = \
                cache_resized_image_locally_results['success']
        else:
            create_resized_image_results['cached_tiny_image'] = IMAGE_ALREADY_CACHED
    return create_resized_image_results


def check_resized_version_exists(voter_we_vote_id=None, candidate_we_vote_id=None, organization_we_vote_id=None,
                                 image_url_https=None, kind_of_image_twitter_profile=False,
                                 kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                                 kind_of_image_facebook_profile=False, kind_of_image_facebook_background=False,
                                 kind_of_image_maplight=False, kind_of_image_vote_smart=False):
    """
    Check if large, medium or tiny image versions already exist or not
    :param voter_we_vote_id:
    :param candidate_we_vote_id:
    :param organization_we_vote_id:
    :param image_url_https:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_maplight:
    :param kind_of_image_vote_smart:
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

    if kind_of_image_twitter_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            twitter_profile_image_url_https=image_url_https)
    elif kind_of_image_twitter_background:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            twitter_profile_background_image_url_https=image_url_https)
    elif kind_of_image_twitter_banner:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            twitter_profile_banner_url_https=image_url_https)
    elif kind_of_image_facebook_profile:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            facebook_profile_image_url_https=image_url_https)
    elif kind_of_image_facebook_background:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            facebook_background_image_url_https=image_url_https)
    elif kind_of_image_maplight:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            maplight_image_url_https=image_url_https)
    elif kind_of_image_vote_smart:
        we_vote_image_list_results = we_vote_image_manager.retrieve_we_vote_image_list_from_url(
            voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id,
            vote_smart_image_url_https=image_url_https)

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


def cache_resized_image_locally(google_civic_election_id, image_url_https, we_vote_parent_image_id,
                                voter_we_vote_id=None, candidate_we_vote_id=None, organization_we_vote_id=None,
                                issue_we_vote_id=None, twitter_id=None, image_format=None,
                                facebook_user_id=None, other_source=None, other_source_profile_image_url=None,
                                maplight_id=None, vote_smart_id=None,
                                is_active_version=False, kind_of_image_twitter_profile=False,
                                kind_of_image_twitter_background=False, kind_of_image_twitter_banner=False,
                                kind_of_image_facebook_profile=False, kind_of_image_facebook_background=False,
                                kind_of_image_maplight=False, kind_of_image_vote_smart=False,
                                kind_of_image_issue=False,
                                kind_of_image_original=False, kind_of_image_large=False, kind_of_image_medium=False,
                                kind_of_image_tiny=False, image_offset_x=0, image_offset_y=0):
    """
    Resize the image as per image version and cache the same
    :param google_civic_election_id:
    :param image_url_https:
    :param we_vote_parent_image_id:
    :param voter_we_vote_id:
    :param candidate_we_vote_id:
    :param organization_we_vote_id:
    :param issue_we_vote_id:
    :param twitter_id:
    :param image_format:
    :param facebook_user_id:
    :param other_source:                        # can be MapLight or VoteSmart
    :param other_source_profile_image_url:      # TODO need to find a way to get this
    :param maplight_id:
    :param vote_smart_id:
    :param is_active_version:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param kind_of_image_facebook_profile:
    :param kind_of_image_facebook_background:
    :param kind_of_image_maplight:
    :param kind_of_image_vote_smart:
    :param kind_of_image_issue:
    :param kind_of_image_original:
    :param kind_of_image_large:
    :param kind_of_image_medium:
    :param kind_of_image_tiny:
    :param image_offset_x:                      # For Facebook background
    :param image_offset_y:                      # For Facebook background
    :return:
    """

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

    # create we_vote_image entry with voter_we_vote_id and google_civic_election_id and kind_of_image
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        google_civic_election_id, voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id, issue_we_vote_id,
        kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner,
        kind_of_image_facebook_profile, kind_of_image_facebook_background, kind_of_image_maplight,
        kind_of_image_vote_smart, kind_of_image_issue, kind_of_image_original, kind_of_image_large,
        kind_of_image_medium, kind_of_image_tiny)
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

    # saving other source information for that we_vote_image
    save_other_source_info = we_vote_image_manager.save_we_vote_image_other_source_info(
        we_vote_image, other_source, other_source_profile_image_url)
    if save_other_source_info['success']:
        pass

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

    if kind_of_image_twitter_profile:
        image_type = TWITTER_PROFILE_IMAGE_NAME
    elif kind_of_image_twitter_background:
        image_type = TWITTER_BACKGROUND_IMAGE_NAME
    elif kind_of_image_twitter_banner:
        image_type = TWITTER_BANNER_IMAGE_NAME
    elif kind_of_image_facebook_profile:
        image_type = FACEBOOK_PROFILE_IMAGE_NAME
    elif kind_of_image_facebook_background:
        image_type = FACEBOOK_BACKGROUND_IMAGE_NAME
        image_height = SOCIAL_BACKGROUND_IMAGE_HEIGHT
        image_width = SOCIAL_BACKGROUND_IMAGE_WIDTH
    elif kind_of_image_maplight:
        image_type = MAPLIGHT_IMAGE_NAME
    elif kind_of_image_vote_smart:
        image_type = VOTE_SMART_IMAGE_NAME
    elif kind_of_image_issue:
        image_type = ISSUE_IMAGE_NAME
    else:
        image_type = ''

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        voter_we_vote_id, candidate_we_vote_id, organization_we_vote_id, issue_we_vote_id,
        kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner,
        kind_of_image_facebook_profile, kind_of_image_facebook_background,
        kind_of_image_maplight, kind_of_image_vote_smart, kind_of_image_issue,
        kind_of_image_original, kind_of_image_large, kind_of_image_medium, kind_of_image_tiny)
    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)
    if image_versions:
        same_day_image_version = max(image_versions) + 1
    else:
        same_day_image_version = 1

    if kind_of_image_facebook_profile or kind_of_image_facebook_background:
        # image url is valid so store source image of facebook to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_facebook_info(
            we_vote_image, facebook_user_id, image_width, image_height,
            image_url_https, same_day_image_version, kind_of_image_facebook_profile,
            kind_of_image_facebook_background)
    elif kind_of_image_twitter_profile or kind_of_image_twitter_background or kind_of_image_twitter_banner:
        # image url is valid so store source image of twitter to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(
            we_vote_image, twitter_id, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner)
    elif kind_of_image_maplight:
        # image url is valid so store source image of maplight to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_maplight_info(
            we_vote_image, maplight_id, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_maplight)
    elif kind_of_image_vote_smart:
        # image url is valid so store source image of maplight to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_vote_smart_info(
            we_vote_image, vote_smart_id, image_width, image_height, image_url_https, same_day_image_version,
            kind_of_image_vote_smart)
    elif kind_of_image_issue:
        # image url is valid so store source image of issue to WeVoteImage
        save_source_info_results = we_vote_image_manager.save_we_vote_image_issue_info(
            we_vote_image, image_width, image_height, image_url_https, same_day_image_version)
    else:
        save_source_info_results = {
            'status':           "KIND_OF_IMAGE_INVALID",
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
        we_vote_image_file_name = "{image_type}-{date_image_saved}_{counter}_" \
                                  "{image_width}x{image_height}.{image_format}" \
                                  "".format(image_type=image_type,
                                            date_image_saved=date_image_saved,
                                            counter=str(same_day_image_version),
                                            image_width=str(image_width),
                                            image_height=str(image_height),
                                            image_format=str(image_format))
        if voter_we_vote_id:
            we_vote_image_file_location = voter_we_vote_id + "/" + we_vote_image_file_name
        elif candidate_we_vote_id:
            we_vote_image_file_location = candidate_we_vote_id + "/" + we_vote_image_file_name
        elif organization_we_vote_id:
            we_vote_image_file_location = organization_we_vote_id + "/" + we_vote_image_file_name
        elif issue_we_vote_id:
            we_vote_image_file_location = issue_we_vote_id + "/" + we_vote_image_file_name

        image_stored_locally = we_vote_image_manager.store_image_locally(
                image_url_https, we_vote_image_file_name)
        if not image_stored_locally:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_LOCALLY",
                'we_vote_image_created':        we_vote_image_created,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         False,
                'resized_image_created':        resized_image_created,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        status += " IMAGE_STORED_LOCALLY"
        resized_image_created = we_vote_image_manager.resize_we_vote_master_image(
            we_vote_image_file_name, image_width, image_height, image_type, image_offset_x, image_offset_y)
        if not resized_image_created:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_LOCALLY",
                'we_vote_image_created':        we_vote_image_created,
                'image_stored_from_source':     image_stored_from_source,
                'image_stored_locally':         image_stored_locally,
                'resized_image_created':        False,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            delete_we_vote_image_results = we_vote_image_manager.delete_we_vote_image(we_vote_image)
            return error_results

        status += " RESIZED_IMAGE_CREATED"
        image_stored_to_aws = we_vote_image_manager.store_image_to_aws(we_vote_image_file_name,
                                                                       we_vote_image_file_location, image_format)
        if not image_stored_to_aws:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_TO_AWS",
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
            save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(we_vote_image, we_vote_image_url,
                                                                          we_vote_image_file_location,
                                                                          we_vote_parent_image_id, is_active_version)
        else:
            status += " WE_VOTE_IMAGE_URL_IS_EMPTY"
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
    return results


def create_resized_images(voter_we_vote_id=None, candidate_we_vote_id=None,
                          organization_we_vote_id=None, twitter_profile_image_url_https=None,
                          twitter_profile_background_image_url_https=None,
                          twitter_profile_banner_url_https=None,
                          facebook_profile_image_url_https=None,
                          facebook_background_image_url_https=None,
                          maplight_image_url_https=None, vote_smart_image_url_https=None):
    """
    Create resized images
    :param voter_we_vote_id:
    :param candidate_we_vote_id:
    :param organization_we_vote_id:
    :param twitter_profile_image_url_https:
    :param twitter_profile_background_image_url_https:
    :param twitter_profile_banner_url_https:
    :param facebook_profile_image_url_https:
    :param facebook_background_image_url_https:
    :param maplight_image_url_https:
    :param vote_smart_image_url_https:
    :return:
    """
    cached_master_image_url = None
    cached_resized_image_url_large = None
    cached_resized_image_url_medium = None
    cached_resized_image_url_tiny = None

    we_vote_image_manager = WeVoteImageManager()
    # Retrieve cached master image url from WeVoteImage table
    cached_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
        voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        twitter_profile_image_url_https=twitter_profile_image_url_https,
        twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
        twitter_profile_banner_url_https=twitter_profile_banner_url_https,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
        maplight_image_url_https=maplight_image_url_https, vote_smart_image_url_https=vote_smart_image_url_https,
        kind_of_image_original=True)
    if cached_we_vote_image_results['success']:
        cached_we_vote_image = cached_we_vote_image_results['we_vote_image']
        cached_master_image_url = cached_we_vote_image.we_vote_image_url

        # Create resized image if not created before
        create_resized_image_results = create_resized_image_if_not_created(cached_we_vote_image)
        # Retrieve resized large version image url
        if create_resized_image_results['cached_large_image']:
            cached_resized_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                facebook_background_image_url_https=facebook_background_image_url_https,
                maplight_image_url_https=maplight_image_url_https,
                vote_smart_image_url_https=vote_smart_image_url_https,
                kind_of_image_large=True)
            if cached_resized_we_vote_image_results['success']:
                cached_resized_we_vote_image = cached_resized_we_vote_image_results['we_vote_image']
                cached_resized_image_url_large = cached_resized_we_vote_image.we_vote_image_url

        if create_resized_image_results['cached_medium_image']:
            # Retrieve resized medium version image url
            cached_resized_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                facebook_background_image_url_https=facebook_background_image_url_https,
                maplight_image_url_https=maplight_image_url_https,
                vote_smart_image_url_https=vote_smart_image_url_https,
                kind_of_image_medium=True)
            if cached_resized_we_vote_image_results['success']:
                cached_resized_we_vote_image = cached_resized_we_vote_image_results['we_vote_image']
                cached_resized_image_url_medium = cached_resized_we_vote_image.we_vote_image_url

        if create_resized_image_results['cached_tiny_image']:
            # Retrieve resized tiny version image url
            cached_resized_we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_from_url(
                voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                facebook_background_image_url_https=facebook_background_image_url_https,
                maplight_image_url_https=maplight_image_url_https,
                vote_smart_image_url_https=vote_smart_image_url_https,
                kind_of_image_tiny=True)
            if cached_resized_we_vote_image_results['success']:
                cached_resized_we_vote_image = cached_resized_we_vote_image_results['we_vote_image']
                cached_resized_image_url_tiny = cached_resized_we_vote_image.we_vote_image_url
    results = {
        'cached_master_image_url':          cached_master_image_url,
        'cached_resized_image_url_large':   cached_resized_image_url_large,
        'cached_resized_image_url_medium':  cached_resized_image_url_medium,
        'cached_resized_image_url_tiny':    cached_resized_image_url_tiny
    }
    return results


def cache_master_and_resized_image(twitter_id=None, twitter_screen_name=None,
                                   twitter_profile_image_url_https=None,
                                   twitter_profile_background_image_url_https=None,
                                   twitter_profile_banner_url_https=None,
                                   voter_id=None, voter_we_vote_id=None,
                                   candidate_id=None, candidate_we_vote_id=None,
                                   organization_id=None, organization_we_vote_id=None,
                                   image_source=None, facebook_user_id=None,
                                   facebook_profile_image_url_https=None,
                                   facebook_background_image_url_https=None,
                                   facebook_background_image_offset_x=None,
                                   facebook_background_image_offset_y=None,
                                   maplight_id=None, vote_smart_id=None,
                                   maplight_image_url_https=None, vote_smart_image_url_https=None):
    """
    Cache original and re-sized images and return cached urls
    :param twitter_id:
    :param twitter_screen_name:
    :param twitter_profile_image_url_https:
    :param twitter_profile_background_image_url_https:
    :param twitter_profile_banner_url_https:
    :param voter_id:
    :param voter_we_vote_id:
    :param candidate_id:
    :param candidate_we_vote_id:
    :param organization_id:
    :param organization_we_vote_id:
    :param image_source:
    :param facebook_user_id:
    :param facebook_profile_image_url_https:
    :param facebook_background_image_url_https:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :param maplight_id:
    :param vote_smart_id:
    :param maplight_image_url_https:
    :param vote_smart_image_url_https:
    :return:
    """
    cached_twitter_profile_image_url_https = None
    cached_twitter_profile_background_image_url_https = None
    cached_twitter_profile_background_image_url_large = None
    cached_twitter_profile_banner_url_https = None
    cached_twitter_profile_banner_url_large = None
    cached_facebook_profile_image_url_https = None
    cached_facebook_background_image_url_https = None
    cached_facebook_background_image_url_large = None
    cached_maplight_image_url_https = None
    cached_vote_smart_image_url_https = None
    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None

    we_vote_image_manager = WeVoteImageManager()
    # caching refreshed new images to s3 aws
    cache_master_images_results = cache_master_images(
        voter_id=voter_id, voter_we_vote_id=voter_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        organization_id=organization_id, organization_we_vote_id=organization_we_vote_id,
        twitter_id=twitter_id, twitter_screen_name=twitter_screen_name,
        twitter_profile_image_url_https=twitter_profile_image_url_https,
        twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
        twitter_profile_banner_url_https=twitter_profile_banner_url_https,
        facebook_user_id=facebook_user_id, facebook_profile_image_url_https=facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
        facebook_background_image_offset_x=facebook_background_image_offset_x,
        facebook_background_image_offset_y=facebook_background_image_offset_y,
        image_source=image_source,
        maplight_id=maplight_id, maplight_image_url_https=maplight_image_url_https,
        vote_smart_id=vote_smart_id, vote_smart_image_url_https=vote_smart_image_url_https)

    # If cached master image or image is already cached then create all resized images for master image
    if cache_master_images_results['cached_twitter_profile_image'] is True or \
            cache_master_images_results['cached_twitter_profile_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            twitter_profile_image_url_https=twitter_profile_image_url_https)
        cached_twitter_profile_image_url_https = create_resized_image_results['cached_master_image_url']
        we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
        we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']

    if cache_master_images_results['cached_twitter_background_image'] is True or \
            cache_master_images_results['cached_twitter_background_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            twitter_profile_background_image_url_https=twitter_profile_background_image_url_https)
        cached_twitter_profile_background_image_url_https = create_resized_image_results['cached_master_image_url']
        cached_twitter_profile_background_image_url_large = \
            create_resized_image_results['cached_resized_image_url_large']

    if cache_master_images_results['cached_twitter_banner_image'] is True or \
            cache_master_images_results['cached_twitter_banner_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            twitter_profile_banner_url_https=twitter_profile_banner_url_https)
        cached_twitter_profile_banner_url_https = create_resized_image_results['cached_master_image_url']
        cached_twitter_profile_banner_url_large = create_resized_image_results['cached_resized_image_url_large']

    if cache_master_images_results['cached_facebook_profile_image'] is True or \
            cache_master_images_results['cached_facebook_profile_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            facebook_profile_image_url_https=facebook_profile_image_url_https)
        cached_facebook_profile_image_url_https = create_resized_image_results['cached_master_image_url']
        we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
        we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']

    if cache_master_images_results['cached_facebook_background_image'] is True or \
            cache_master_images_results['cached_facebook_background_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            facebook_background_image_url_https=facebook_background_image_url_https)
        cached_facebook_background_image_url_https = create_resized_image_results['cached_master_image_url']
        cached_facebook_background_image_url_large = create_resized_image_results['cached_resized_image_url_large']

    if cache_master_images_results['cached_maplight_image'] is True or \
            cache_master_images_results['cached_maplight_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            maplight_image_url_https=maplight_image_url_https)
        cached_maplight_image_url_https = create_resized_image_results['cached_master_image_url']
        we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
        we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']

    if cache_master_images_results['cached_vote_smart_image'] is True or \
            cache_master_images_results['cached_vote_smart_image'] == IMAGE_ALREADY_CACHED:
        create_resized_image_results = create_resized_images(
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id,
            vote_smart_image_url_https=vote_smart_image_url_https)
        cached_vote_smart_image_url_https = create_resized_image_results['cached_master_image_url']
        we_vote_hosted_profile_image_url_large = create_resized_image_results['cached_resized_image_url_large']
        we_vote_hosted_profile_image_url_medium = create_resized_image_results['cached_resized_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = create_resized_image_results['cached_resized_image_url_tiny']

    results = {
        'cached_twitter_profile_image_url_https':               cached_twitter_profile_image_url_https,
        'cached_twitter_profile_background_image_url_https':    cached_twitter_profile_background_image_url_https,
        'cached_twitter_profile_background_image_url_large':    cached_twitter_profile_background_image_url_large,
        'cached_twitter_profile_banner_url_https':              cached_twitter_profile_banner_url_https,
        'cached_twitter_profile_banner_url_large':              cached_twitter_profile_banner_url_large,
        'cached_facebook_profile_image_url_https':              cached_facebook_profile_image_url_https,
        'cached_facebook_background_image_url_https':           cached_facebook_background_image_url_https,
        'cached_facebook_background_image_url_large':           cached_facebook_background_image_url_large,
        'cached_maplight_image_url_https':                      cached_maplight_image_url_https,
        'cached_vote_smart_image_url_https':                    cached_vote_smart_image_url_https,
        'we_vote_hosted_profile_image_url_large':               we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':              we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':                we_vote_hosted_profile_image_url_tiny
    }
    return results


def cache_master_images(twitter_id=None, twitter_screen_name=None,
                        twitter_profile_image_url_https=None, twitter_profile_background_image_url_https=None,
                        twitter_profile_banner_url_https=None, voter_id=None, voter_we_vote_id=None,
                        candidate_id=None, candidate_we_vote_id=None, organization_id=None,
                        organization_we_vote_id=None, image_source=None, facebook_user_id=None,
                        facebook_profile_image_url_https=None, facebook_background_image_url_https=None,
                        facebook_background_image_offset_x=None, facebook_background_image_offset_y=None,
                        maplight_id=None, vote_smart_id=None, maplight_image_url_https=None,
                        vote_smart_image_url_https=None):
    """
    Cache all kind of images locally for a candidate or an organization such as profile, background
    :param twitter_id:
    :param twitter_screen_name:
    :param twitter_profile_image_url_https:
    :param twitter_profile_background_image_url_https:
    :param twitter_profile_banner_url_https:
    :param voter_id:
    :param voter_we_vote_id:
    :param candidate_id:
    :param candidate_we_vote_id:
    :param organization_id:
    :param organization_we_vote_id:
    :param image_source:
    :param facebook_user_id:
    :param facebook_profile_image_url_https:
    :param facebook_background_image_url_https:
    :param facebook_background_image_offset_x:
    :param facebook_background_image_offset_y:
    :param maplight_id:
    :param maplight_image_url_https:
    :param vote_smart_id:
    :param vote_smart_image_url_https:
    :return:
    """
    cache_all_kind_of_images_results = {
        'image_source':                     image_source,
        'voter_id':                         voter_id,
        'voter_we_vote_id':                 voter_we_vote_id,
        'candidate_id':                     candidate_id,
        'candidate_we_vote_id':             candidate_we_vote_id,
        'organization_id':                  organization_id,
        'organization_we_vote_id':          organization_we_vote_id,
        'cached_twitter_profile_image':     False,
        'cached_twitter_background_image':  False,
        'cached_twitter_banner_image':      False,
        'cached_facebook_profile_image':    False,
        'cached_facebook_background_image': False,
        'cached_maplight_image':            False,
        'cached_vote_smart_image':          False,
    }
    google_civic_election_id = 0
    we_vote_image_manager = WeVoteImageManager()

    if not twitter_profile_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = TWITTER_URL_NOT_FOUND
    else:
        twitter_profile_image_url_https = we_vote_image_manager.twitter_profile_image_url_https_original(
            twitter_profile_image_url_https)
    if not twitter_profile_background_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = TWITTER_URL_NOT_FOUND
    if not twitter_profile_banner_url_https:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = TWITTER_URL_NOT_FOUND
    if not facebook_profile_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_profile_image'] = FACEBOOK_URL_NOT_FOUND
    if not facebook_background_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_background_image'] = FACEBOOK_URL_NOT_FOUND
    if not maplight_image_url_https:
        cache_all_kind_of_images_results['cached_maplight_image'] = MAPLIGHT_URL_NOT_FOUND
    if not vote_smart_image_url_https:
        cache_all_kind_of_images_results['cached_vote_smart_image'] = VOTE_SMART_URL_NOT_FOUND

    if image_source is TWITTER and not positive_value_exists(twitter_id):
        cache_all_kind_of_images_results = {
            'image_source':                     image_source,
            'voter_id':                         voter_id,
            'voter_we_vote_id':                 voter_we_vote_id,
            'candidate_id':                     candidate_id,
            'candidate_we_vote_id':             candidate_we_vote_id,
            'organization_id':                  organization_id,
            'organization_we_vote_id':          organization_we_vote_id,
            'cached_twitter_profile_image':     TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_background_image':  TWITTER_USER_DOES_NOT_EXIST,
            'cached_twitter_banner_image':      TWITTER_USER_DOES_NOT_EXIST,
            'cached_facebook_profile_image':    False,
            'cached_facebook_background_image': False,
            'cached_maplight_image':            False,
            'cached_vote_smart_image':          False
        }
        return cache_all_kind_of_images_results

    if image_source is FACEBOOK and not positive_value_exists(facebook_user_id):
        cache_all_kind_of_images_results = {
            'image_source':                     image_source,
            'voter_id':                         voter_id,
            'voter_we_vote_id':                 voter_we_vote_id,
            'candidate_id':                     candidate_id,
            'candidate_we_vote_id':             candidate_we_vote_id,
            'organization_id':                  organization_id,
            'organization_we_vote_id':          organization_we_vote_id,
            'cached_twitter_profile_image':     False,
            'cached_twitter_background_image':  False,
            'cached_twitter_banner_image':      False,
            'cached_facebook_profile_image':    FACEBOOK_USER_DOES_NOT_EXIST,
            'cached_facebook_background_image': FACEBOOK_USER_DOES_NOT_EXIST,
            'cached_maplight_image':            False,
            'cached_vote_smart_image':          False
        }
        return cache_all_kind_of_images_results

    if twitter_profile_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id, twitter_profile_image_url_https, voter_we_vote_id=voter_we_vote_id,
            candidate_we_vote_id=candidate_we_vote_id, organization_we_vote_id=organization_we_vote_id,
            twitter_id=twitter_id, twitter_screen_name=twitter_screen_name, is_active_version=True,
            kind_of_image_twitter_profile=True, kind_of_image_original=True)

    if twitter_profile_background_image_url_https:
        cache_all_kind_of_images_results['cached_twitter_background_image'] = cache_image_if_not_cached(
            google_civic_election_id, twitter_profile_background_image_url_https,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name, is_active_version=True,
            kind_of_image_twitter_background=True, kind_of_image_original=True)

    if twitter_profile_banner_url_https:
        cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_if_not_cached(
            google_civic_election_id, twitter_profile_banner_url_https,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, twitter_id=twitter_id,
            twitter_screen_name=twitter_screen_name, is_active_version=True,
            kind_of_image_twitter_banner=True, kind_of_image_original=True)

    if facebook_profile_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_profile_image'] = cache_image_if_not_cached(
            google_civic_election_id, facebook_profile_image_url_https,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, facebook_user_id=facebook_user_id,
            is_active_version=True, kind_of_image_facebook_profile=True, kind_of_image_original=True)

    if facebook_background_image_url_https:
        cache_all_kind_of_images_results['cached_facebook_background_image'] = cache_image_if_not_cached(
            google_civic_election_id, facebook_background_image_url_https,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, facebook_user_id=facebook_user_id,
            is_active_version=True, kind_of_image_facebook_background=True,
            facebook_background_image_offset_x=facebook_background_image_offset_x,
            facebook_background_image_offset_y=facebook_background_image_offset_y,
            kind_of_image_original=True)

    if maplight_image_url_https:
        cache_all_kind_of_images_results['cached_maplight_image'] = cache_image_if_not_cached(
            google_civic_election_id, maplight_image_url_https,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, maplight_id=maplight_id,
            is_active_version=True, kind_of_image_maplight=True, kind_of_image_original=True)

    if vote_smart_image_url_https:
        cache_all_kind_of_images_results['cached_vote_smart_image'] = cache_image_if_not_cached(
            google_civic_election_id, maplight_image_url_https,
            voter_we_vote_id=voter_we_vote_id, candidate_we_vote_id=candidate_we_vote_id,
            organization_we_vote_id=organization_we_vote_id, vote_smart_id=vote_smart_id,
            is_active_version=True, kind_of_image_vote_smart=True, kind_of_image_original=True)

    return cache_all_kind_of_images_results


def cache_issue_image_master(google_civic_election_id, issue_image_file, issue_we_vote_id=None,
                             kind_of_image_issue=False, kind_of_image_original=False):
    """
    Cache master issue image to AWS
    :param google_civic_election_id:
    :param issue_image_file:
    :param issue_we_vote_id:
    :param kind_of_image_issue:
    :param kind_of_image_original:
    :return:
    """
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
        google_civic_election_id, issue_we_vote_id=issue_we_vote_id, kind_of_image_issue=kind_of_image_issue,
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
        issue_we_vote_id=issue_we_vote_id, kind_of_image_issue=kind_of_image_issue,
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
    save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(we_vote_image, we_vote_image_url,
                                                                      we_vote_image_file_location,
                                                                      we_vote_parent_image_id, is_active_version)
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
        issue_we_vote_id=issue_we_vote_id, image_url_https=we_vote_image.we_vote_image_url,
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
    return results
