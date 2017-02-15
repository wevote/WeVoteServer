# image/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.controllers import choose_election_from_existing_data
from .functions import analyze_remote_url
from import_export_twitter.functions import retrieve_twitter_user_info
from .models import WeVoteImageManager
from twitter.models import TwitterUserManager
from voter.models import VoterManager, VoterDeviceLinkManager
from wevote_functions.functions import positive_value_exists
import requests
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)
HTTP_OK = 200
TWITTER_URL_NOT_FOUND = "twitter url not found"
IMAGE_ALREADY_CACHED = "image already cached"
ALL_KIND_OF_IMAGE = ['kind_of_image_twitter_profile', 'kind_of_image_twitter_background',
                     'kind_of_image_twitter_banner']

# naming convention stored at aws
TWITTER_PROFILE_IMAGE_NAME = "twitter_profile_image"
TWITTER_BACKGROUND_IMAGE_NAME = "twitter_background_image"
TWITTER_BANNER_IMAGE_NAME = "twitter_banner_image"
MASTER_IMAGE = "master"


def cache_all_kind_of_images_locally_for_voter(voter_id):
    """
    Cache All kind of images locally for a voter such as profile, background
    :param voter_id:
    :return:
    """
    pass


def migrate_remote_voter_image_urls_to_local_cache(voter_id):
    """
    Migrating vote image urls to local cache
    :param voter_id:
    :return:
    """
    cache_all_kind_of_images_results = {
        'voter_we_vote_id':                 False,
        'cached_twitter_profile_image':     False,
        'cached_twitter_background_image':  False,
        'cached_twitter_banner_image':      False
    }
    google_civic_election_id = 0
    twitter_image_url_changed = False
    is_active_version = False
    we_vote_image_manager = WeVoteImageManager()
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
            results = choose_election_from_existing_data(voter_device_link_results['voter_device_link'], 0, '')
            google_civic_election_id = results['google_civic_election_id']
    else:
        return cache_all_kind_of_images_results

    for kind_of_image in ALL_KIND_OF_IMAGE:
        if kind_of_image == "kind_of_image_twitter_profile":
            twitter_user, twitter_profile_image_url_https = retrieve_twitter_image_url(
                voter.twitter_id, kind_of_image_twitter_profile=True)
            # If twitter image url not found in TwitterUser table then reaching out to twitter and getting new image
            if not twitter_profile_image_url_https:
                twitter_profile_image_url_https = retrieve_latest_twitter_image_url(
                    voter.twitter_id, voter.twitter_screen_name, kind_of_image_twitter_profile=True)
                if not twitter_profile_image_url_https:
                    # new twitter profile image not found
                    cache_all_kind_of_images_results['cached_twitter_background_image'] = \
                        TWITTER_URL_NOT_FOUND
                    continue
                twitter_image_url_changed = True
                is_active_version = True

            # Get cached profile images and check if this image is already cached or not
            cached_we_vote_image_list_results = we_vote_image_manager.retrieve_cached_we_vote_image_list(
                voter.we_vote_id, kind_of_image_twitter_profile=True)
            for cached_we_vote_image in cached_we_vote_image_list_results['we_vote_image_list']:
                # If image is already cached then no need to cache it again
                if twitter_profile_image_url_https == cached_we_vote_image.twitter_profile_image_url_https:
                    cache_all_kind_of_images_results['cached_twitter_profile_image'] = \
                        IMAGE_ALREADY_CACHED
                    break
            else:
                # Image is not cached so caching it
                cache_image_locally_results = cache_image_locally(voter, google_civic_election_id,
                                                                  twitter_profile_image_url_https, is_active_version,
                                                                  kind_of_image_twitter_profile=True)
                cache_all_kind_of_images_results['cached_twitter_profile_image'] = \
                    cache_image_locally_results['success']
                # Update TwitterUser Table with latest image url
                if twitter_image_url_changed:
                    # TODO Update all other tables ex. TwitterUser, Voter with updated cache urls
                    pass

        elif kind_of_image == "kind_of_image_twitter_background":
            twitter_user, twitter_profile_background_image_url_https = retrieve_twitter_image_url(
                voter.twitter_id, kind_of_image_twitter_background=True)
            # If twitter image url not found in TwitterUser table then reaching out to twitter and getting new image
            if not twitter_profile_background_image_url_https:
                twitter_profile_background_image_url_https = retrieve_latest_twitter_image_url(
                    voter.twitter_id, voter.twitter_screen_name, kind_of_image_twitter_background=True)
                if not twitter_profile_background_image_url_https:
                    # new twitter profile image not found
                    cache_all_kind_of_images_results['cached_twitter_background_image'] = \
                        TWITTER_URL_NOT_FOUND
                    continue
                twitter_image_url_changed = True
                is_active_version = True

            # Get cached profile images and check if this image is already cached or not
            cached_we_vote_image_list_results = we_vote_image_manager.retrieve_cached_we_vote_image_list(
                voter.we_vote_id, kind_of_image_twitter_background=True)
            for cached_we_vote_image in cached_we_vote_image_list_results['we_vote_image_list']:
                # If image is already cached then no need to cache it again
                if twitter_profile_background_image_url_https == \
                        cached_we_vote_image.twitter_profile_background_image_url_https:
                    cache_all_kind_of_images_results['cached_twitter_background_image'] = \
                        IMAGE_ALREADY_CACHED
                    break
            else:
                # Image is not cached so caching it
                cache_image_locally_results = cache_image_locally(voter, google_civic_election_id,
                                                                  twitter_profile_background_image_url_https,
                                                                  is_active_version,
                                                                  kind_of_image_twitter_background=True)
                cache_all_kind_of_images_results['cached_twitter_background_image'] = \
                    cache_image_locally_results['success']
                # Update TwitterUser Table with latest image url
                if twitter_image_url_changed:
                    # TODO Update all other tables ex. TwitterUser, Voter with updated cache urls
                    pass

        elif kind_of_image == "kind_of_image_twitter_banner":
            twitter_user, twitter_profile_banner_url_https = retrieve_twitter_image_url(
                voter.twitter_id, kind_of_image_twitter_banner=True)
            # If twitter image url not found in TwitterUser table then reaching out to twitter and getting new image
            if not twitter_profile_banner_url_https:
                twitter_profile_banner_url_https = retrieve_latest_twitter_image_url(
                    voter.twitter_id, voter.twitter_screen_name, kind_of_image_twitter_banner=True)
                if not twitter_profile_banner_url_https:
                    # new twitter profile image not found
                    cache_all_kind_of_images_results['cached_twitter_background_image'] = \
                        TWITTER_URL_NOT_FOUND
                    continue
                twitter_image_url_changed = True
                is_active_version = True

            # Get cached profile images and check if this image is already cached or not
            cached_we_vote_image_list_results = we_vote_image_manager.retrieve_cached_we_vote_image_list(
                voter.we_vote_id, kind_of_image_twitter_banner=True)
            for cached_we_vote_image in cached_we_vote_image_list_results['we_vote_image_list']:
                # If image is already cached then no need to cache it again
                if twitter_profile_banner_url_https == cached_we_vote_image.twitter_profile_banner_url_https:
                    cache_all_kind_of_images_results['cached_twitter_banner_image'] = \
                        IMAGE_ALREADY_CACHED
                    break
            else:
                # Image is not cached so caching it
                cache_image_locally_results = cache_image_locally(voter, google_civic_election_id,
                                                                  twitter_profile_banner_url_https, is_active_version,
                                                                  kind_of_image_twitter_banner=True)
                cache_all_kind_of_images_results['cached_twitter_banner_image'] = \
                    cache_image_locally_results['success']
                # Update TwitterUser Table with latest image url
                if twitter_image_url_changed:
                    # TODO Update all other tables ex. TwitterUser, Voter with updated cache urls
                    pass

    return cache_all_kind_of_images_results


def cache_image_locally(voter, google_civic_election_id, twitter_image_url_https, is_active_version,
                        kind_of_image_twitter_profile=False,
                        kind_of_image_twitter_background=False,
                        kind_of_image_twitter_banner=False):
    """
    Cache one type of image
    :param voter:
    :param google_civic_election_id:
    :param twitter_image_url_https:
    :param is_active_version:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    other_source_profile_image_url = None   # TODO need to find a way to get this
    other_source = None     # can be MapLight or VoteSmart
    we_vote_image_url = None
    we_vote_parent_image_id = None

    success = False
    status = ''
    we_vote_image_created = False
    twitter_url_not_found = False
    image_url_valid = False
    image_stored_from_twitter = False
    image_stored_locally = False
    image_stored_to_aws = False
    image_versions = []

    we_vote_image_manager = WeVoteImageManager()

    # create we_vote_image entry with voter_we_vote_id and google_civic_election_id and kind_of_image
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        voter.we_vote_id, google_civic_election_id, kind_of_image_twitter_profile,
        kind_of_image_twitter_background, kind_of_image_twitter_banner)
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'twitter_url_not_found':        twitter_url_not_found,
            'image_url_valid':              image_url_valid,
            'image_stored_from_twitter':    image_stored_from_twitter,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    we_vote_image_created = True
    we_vote_image = create_we_vote_image_results['we_vote_image']
    # saving facebook information for that we_vote_image entry
    save_facebook_info_results = we_vote_image_manager.save_we_vote_image_facebook_info(we_vote_image, voter)
    if save_facebook_info_results['success']:
        pass

    # saving other source information for that we_vote_image
    save_other_source_info = we_vote_image_manager.save_we_vote_image_other_source_info(
        we_vote_image, other_source, other_source_profile_image_url)
    if save_other_source_info['success']:
        pass

    # Image url validation and get source image properties
    twitter_user_images_results = analyze_twitter_user_images(voter.twitter_id, voter.twitter_screen_name,
                                                              twitter_image_url_https,
                                                              kind_of_image_twitter_profile,
                                                              kind_of_image_twitter_background,
                                                              kind_of_image_twitter_banner)

    if not twitter_user_images_results['analyze_image_url_results']['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID",
            'we_vote_image_created':        True,
            'image_url_valid':              False,
            'image_stored_from_twitter':    image_stored_from_twitter,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID"

    # Get today's cached images and their versions so that image version can be calculated
    cached_todays_we_vote_image_list_results = we_vote_image_manager.retrieve_todays_cached_we_vote_image_list(
        voter.we_vote_id, kind_of_image_twitter_profile, kind_of_image_twitter_background, kind_of_image_twitter_banner)
    for cached_we_vote_image in cached_todays_we_vote_image_list_results['we_vote_image_list']:
        if cached_we_vote_image.same_day_image_version:
            image_versions.append(cached_we_vote_image.same_day_image_version)
    if image_versions:
        twitter_user_images_results['same_day_image_version'] = max(image_versions) + 1
    else:
        twitter_user_images_results['same_day_image_version'] = 1

    # if image url is valid then store source image of twitter to weVoteImage
    save_twitter_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(
        we_vote_image, twitter_user_images_results)

    status += " " + save_twitter_info_results['status']
    if save_twitter_info_results['success']:
        image_stored_from_twitter = True
        date_image_saved = "{year}{month}{day}".format(year=we_vote_image.date_image_saved.year,
                                                       month=we_vote_image.date_image_saved.month,
                                                       day=we_vote_image.date_image_saved.day)
        # ex twitter_profile_image_master-2017210_1_48x48.png
        we_vote_image_file_name = "{twitter_image_type}_{master_image}-{date_image_saved}_{counter}_" \
                                  "{image_width}x{image_height}.{image_format}" \
                                  "".format(twitter_image_type=twitter_user_images_results['twitter_image_type'],
                                            master_image=MASTER_IMAGE, date_image_saved=date_image_saved,
                                            counter=str(twitter_user_images_results['same_day_image_version']),
                                            image_width=str(twitter_user_images_results['analyze_image_url_results']
                                                            ['image_width']),
                                            image_height=str(twitter_user_images_results['analyze_image_url_results']
                                                             ['image_height']),
                                            image_format=str(twitter_user_images_results['analyze_image_url_results']
                                                             ['image_format']))
        we_vote_image_file_location = voter.we_vote_id + "/" + we_vote_image_file_name

        if not is_active_version:
            is_active_version = check_source_image_active(twitter_user_images_results, kind_of_image_twitter_profile,
                                                          kind_of_image_twitter_background,
                                                          kind_of_image_twitter_banner)

        image_stored_locally = store_source_image_locally(we_vote_image_file_name, twitter_user_images_results,
                                                          kind_of_image_twitter_profile,
                                                          kind_of_image_twitter_background,
                                                          kind_of_image_twitter_banner)
        if not image_stored_locally:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_LOCALLY",
                'we_vote_image_created':        we_vote_image_created,
                'image_url_valid':              image_url_valid,
                'image_stored_from_twitter':    image_stored_from_twitter,
                'image_stored_locally':         False,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            return error_results

        status += " IMAGE_STORED_LOCALLY"
        image_stored_to_aws = we_vote_image_manager.store_image_to_aws(we_vote_image_file_name,
                                                                       we_vote_image_file_location)
        if not image_stored_to_aws:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_TO_AWS",
                'we_vote_image_created':        we_vote_image_created,
                'image_url_valid':              image_url_valid,
                'image_stored_from_twitter':    image_stored_from_twitter,
                'image_stored_locally':         image_stored_locally,
                'image_stored_to_aws':          False,
            }
            return error_results

        save_aws_info = we_vote_image_manager.save_we_vote_image_aws_info(we_vote_image, we_vote_image_url,
                                                                          we_vote_image_file_location,
                                                                          we_vote_parent_image_id, is_active_version)
        status += " IMAGE_STORED_TO_AWS " + save_aws_info['status']
        success = save_aws_info['success']

    else:
        error_results = {
            'success':                      success,
            'status':                       status,
            'we_vote_image_created':        we_vote_image_created,
            'image_url_valid':              image_url_valid,
            'image_stored_from_twitter':    False,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    results = {
        'success':                      success,
        'status':                       status,
        'we_vote_image_created':        we_vote_image_created,
        'image_url_valid':              image_url_valid,
        'image_stored_from_twitter':    image_stored_from_twitter,
        'image_stored_locally':         image_stored_locally,
        'image_stored_to_aws':          image_stored_to_aws,
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


def retrieve_latest_twitter_image_url(twitter_id, twitter_screen_name, kind_of_image_twitter_profile=False,
                                      kind_of_image_twitter_background=False,
                                      kind_of_image_twitter_banner=False, size="original"):
    """
    Retrieve latest twitter background and banner image url from twitter API call and twitter profile image from a url
    :param twitter_id:
    :param twitter_screen_name:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :param size:
    :return:
    """
    latest_twitter_image_url = None
    if kind_of_image_twitter_profile:
        get_url = "https://twitter.com/{twitter_screen_name}/profile_image?size={size}" \
            .format(twitter_screen_name=twitter_screen_name, size=size)
        response = requests.get(get_url)
        if response.status_code == HTTP_OK:
            # new twitter profile image url found
            latest_twitter_image_url = response.url
        return latest_twitter_image_url

    twitter_user_info_results = retrieve_twitter_user_info(twitter_id, twitter_handle='')
    if kind_of_image_twitter_background:
        if 'profile_background_image_url_https' in twitter_user_info_results['twitter_json'] \
                and twitter_user_info_results['twitter_json']['profile_background_image_url_https']:
            # new twitter image url found
            latest_twitter_image_url = twitter_user_info_results['twitter_json'][
                'profile_background_image_url_https']
    elif kind_of_image_twitter_banner:
        if 'profile_banner_url' in twitter_user_info_results['twitter_json'] \
                and twitter_user_info_results['twitter_json']['profile_banner_url']:
            # new twitter image url found
            latest_twitter_image_url = twitter_user_info_results['twitter_json'][
                'profile_banner_url']

    return latest_twitter_image_url


def analyze_twitter_user_images(twitter_id, twitter_screen_name, twitter_image_url_https, kind_of_image_twitter_profile,
                                kind_of_image_twitter_background, kind_of_image_twitter_banner):
    """
    Checking twitter user images if url is valid and getting image properties
    :param twitter_id:
    :param twitter_screen_name:
    :param twitter_image_url_https:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    twitter_image_type = None
    twitter_profile_image_url_https = None
    twitter_profile_background_image_url_https = None
    twitter_profile_banner_url_https = None
    analyze_image_url_results = {
        'image_url_valid': False,
        'image_width': None,
        'image_height': None,
        'image_format': None
    }

    if kind_of_image_twitter_profile:
        twitter_profile_image_url_https = twitter_image_url_https
        twitter_image_type = TWITTER_PROFILE_IMAGE_NAME
        analyze_image_url_results = analyze_remote_url(twitter_profile_image_url_https)
        if not analyze_image_url_results['image_url_valid']:
            # image url is broken so reaching out to Twitter and getting new image
            twitter_profile_image_url_https = retrieve_latest_twitter_image_url(
                twitter_id, twitter_screen_name, kind_of_image_twitter_profile=True)
            if not twitter_profile_image_url_https:
                # new twitter image url not found
                error_results = {
                    'twitter_id':                                   twitter_id,
                    'twitter_screen_name':                          twitter_screen_name,
                    'twitter_profile_image_url_https':              twitter_profile_image_url_https,
                    'twitter_profile_background_image_url_https':   twitter_profile_background_image_url_https,
                    'twitter_profile_banner_url_https':             twitter_profile_banner_url_https,
                    'twitter_image_type':                           twitter_image_type,
                    'analyze_image_url_results':                    analyze_image_url_results
                }
                return error_results

            # new twitter image url found
            analyze_image_url_results = analyze_remote_url(twitter_profile_image_url_https)

    elif kind_of_image_twitter_background:
        twitter_profile_background_image_url_https = twitter_image_url_https
        twitter_image_type = TWITTER_BACKGROUND_IMAGE_NAME
        analyze_image_url_results = analyze_remote_url(twitter_profile_background_image_url_https)
        if not analyze_image_url_results['image_url_valid']:
            # image url is broken so reaching out to Twitter and getting new image
            twitter_profile_background_image_url_https = retrieve_latest_twitter_image_url(
                twitter_id, twitter_screen_name, kind_of_image_twitter_background=True)
            if not twitter_profile_background_image_url_https:
                # new twitter image url not found
                error_results = {
                    'twitter_id':                                   twitter_id,
                    'twitter_screen_name':                          twitter_screen_name,
                    'twitter_profile_image_url_https':              twitter_profile_image_url_https,
                    'twitter_profile_background_image_url_https':   twitter_profile_background_image_url_https,
                    'twitter_profile_banner_url_https':             twitter_profile_banner_url_https,
                    'twitter_image_type':                           twitter_image_type,
                    'analyze_image_url_results':                    analyze_image_url_results
                }
                return error_results

            # new twitter image url found
            analyze_image_url_results = analyze_remote_url(twitter_profile_background_image_url_https)

    elif kind_of_image_twitter_banner:
        twitter_profile_banner_url_https = twitter_image_url_https
        twitter_image_type = TWITTER_BANNER_IMAGE_NAME
        analyze_image_url_results = analyze_remote_url(twitter_profile_banner_url_https)
        if not analyze_image_url_results['image_url_valid']:
            # image url is broken so reaching out to Twitter and getting new image
            twitter_profile_banner_url_https = retrieve_latest_twitter_image_url(
                twitter_id, twitter_screen_name, kind_of_image_twitter_background=True)
            if not twitter_profile_banner_url_https:
                # new twitter image url not found
                error_results = {
                    'twitter_id':                                   twitter_id,
                    'twitter_screen_name':                          twitter_screen_name,
                    'twitter_profile_image_url_https':              twitter_profile_image_url_https,
                    'twitter_profile_background_image_url_https':   twitter_profile_background_image_url_https,
                    'twitter_profile_banner_url_https':             twitter_profile_banner_url_https,
                    'twitter_image_type':                           twitter_image_type,
                    'analyze_image_url_results':                    analyze_image_url_results
                }
                return error_results

            # new twitter image url found
            analyze_image_url_results = analyze_remote_url(twitter_profile_banner_url_https)

    results = {
        'twitter_id':                                   twitter_id,
        'twitter_screen_name':                          twitter_screen_name,
        'twitter_profile_image_url_https':              twitter_profile_image_url_https,
        'twitter_profile_background_image_url_https':   twitter_profile_background_image_url_https,
        'twitter_profile_banner_url_https':             twitter_profile_banner_url_https,
        'twitter_image_type':                           twitter_image_type,
        'analyze_image_url_results':                    analyze_image_url_results
    }
    return results


def check_source_image_active(twitter_user_images_dict, kind_of_image_twitter_profile,
                              kind_of_image_twitter_background, kind_of_image_twitter_banner):
    """
    Check if this source image is latest image or old one
    :param twitter_user_images_dict:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    is_active_version = False
    if kind_of_image_twitter_profile:
        latest_twitter_profile_image_url_https = retrieve_latest_twitter_image_url(
            twitter_user_images_dict['twitter_id'], twitter_user_images_dict['twitter_screen_name'],
            kind_of_image_twitter_profile=True)
        if latest_twitter_profile_image_url_https == \
                twitter_user_images_dict['twitter_profile_image_url_https']:
            is_active_version = True

    elif kind_of_image_twitter_background:
        latest_twitter_profile_background_image_url_https = retrieve_latest_twitter_image_url(
            twitter_user_images_dict['twitter_id'], twitter_user_images_dict['twitter_screen_name'],
            kind_of_image_twitter_background=True)
        if latest_twitter_profile_background_image_url_https == \
                twitter_user_images_dict['twitter_profile_background_image_url_https']:
            is_active_version = True

    elif kind_of_image_twitter_banner:
        latest_twitter_profile_banner_url_https = retrieve_latest_twitter_image_url(
            twitter_user_images_dict['twitter_id'], twitter_user_images_dict['twitter_screen_name'],
            kind_of_image_twitter_banner=True)
        if latest_twitter_profile_banner_url_https == \
                twitter_user_images_dict['twitter_profile_banner_url_https']:
            is_active_version = True

    return is_active_version


def store_source_image_locally(we_vote_image_file_location, twitter_user_images_results, kind_of_image_twitter_profile,
                               kind_of_image_twitter_background, kind_of_image_twitter_banner):
    """
    Store source image locally according to the kind_of_image so that it could be uploaded to aws later
    :param we_vote_image_file_location:
    :param twitter_user_images_results:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    image_stored_locally = False
    we_vote_image_manager = WeVoteImageManager()

    if kind_of_image_twitter_profile:
        image_stored_locally = we_vote_image_manager.save_image_locally(
            twitter_user_images_results['twitter_profile_image_url_https'], we_vote_image_file_location)
    elif kind_of_image_twitter_background:
        image_stored_locally = we_vote_image_manager.save_image_locally(
            twitter_user_images_results['twitter_profile_background_image_url_https'], we_vote_image_file_location)
    elif kind_of_image_twitter_banner:
        image_stored_locally = we_vote_image_manager.save_image_locally(
            twitter_user_images_results['twitter_profile_banner_url_https'], we_vote_image_file_location)

    return image_stored_locally
