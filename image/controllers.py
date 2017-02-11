# image/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .functions import analyze_remote_url
from import_export_twitter.functions import retrieve_twitter_user_info
from .models import WeVoteImageManager
from twitter.models import TwitterUserManager
from voter.models import VoterManager, VoterDeviceLinkManager
from wevote_functions.functions import positive_value_exists
import time
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)
IMAGE_NOT_FOUND = "Image not found"
ALL_KIND_OF_IMAGE = ['kind_of_image_twitter_profile', 'kind_of_image_twitter_background',
                     'kind_of_image_twitter_banner']

# For naming convention stored at aws
TWITTER_PROFILE_IMAGE_NAME = "twitter_profile_image"
TWITTER_BACKGROUND_IMAGE_NAME = "twitter_profile_image"
TWITTER_BANNER_IMAGE_NAME = "twitter_profile_image"
MASTER_IMAGE = "master"


def cache_all_kind_of_images_locally_for_voter(voter_id):
    """
    Cache All kind of images locally for a voter such as profile, background
    :param voter_id:
    :return:
    """
    cache_all_kind_of_images_results = {
        'voter_we_vote_id':                 False,
        'cached_twitter_prfile_image':      False,
        'cached_twitter_background_image':  False,
        'cached_twitter_banner_image':      False
    }

    for kind_of_image in ALL_KIND_OF_IMAGE:
        if kind_of_image == "kind_of_image_twitter_profile":
            cache_image_locally_results = cache_image_locally(voter_id, kind_of_image_twitter_profile=True)
            if cache_image_locally_results['image_not_found']:
                cache_all_kind_of_images_results['cached_twitter_prfile_image'] = IMAGE_NOT_FOUND
            else:
                cache_all_kind_of_images_results['cached_twitter_prfile_image'] = cache_image_locally_results['success']
        elif kind_of_image == "kind_of_image_twitter_background":
            cache_image_locally_results = cache_image_locally(voter_id, kind_of_image_twitter_background=True)
            if cache_image_locally_results['image_not_found']:
                cache_all_kind_of_images_results['cached_twitter_background_image'] = IMAGE_NOT_FOUND
            else:
                cache_all_kind_of_images_results['cached_twitter_background_image'] = \
                    cache_image_locally_results['success']
        elif kind_of_image == "kind_of_image_twitter_banner":
            cache_image_locally_results = cache_image_locally(voter_id, kind_of_image_twitter_banner=True)
            if cache_image_locally_results['image_not_found']:
                cache_all_kind_of_images_results['cached_twitter_banner_image'] = IMAGE_NOT_FOUND
            else:
                cache_all_kind_of_images_results['cached_twitter_banner_image'] = cache_image_locally_results['success']

        cache_all_kind_of_images_results['voter_we_vote_id'] = cache_image_locally_results['voter_we_vote_id']

    return cache_all_kind_of_images_results


def cache_image_locally(voter_id, kind_of_image_twitter_profile=False,
                        kind_of_image_twitter_background=False,
                        kind_of_image_twitter_banner=False):
    """
    Cache one type of image
    :param voter_id:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    voter_we_vote_id = None
    google_civic_election_id = 0
    other_source_profile_image_url = None   # TODO need to find a way to get this
    other_source = None     # can be MapLight or VoteSmart
    we_vote_image_url = None
    we_vote_parent_image_id = None

    success = False
    status = ''
    we_vote_image_created = False
    image_not_found = False
    image_url_valid = False
    image_stored_from_twitter = False
    image_stored_locally = False
    image_stored_to_aws = False

    counter = 1     # TODO need to find when to increment

    we_vote_image_manager = WeVoteImageManager()
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_manager = VoterManager()

    voter_results = voter_manager.retrieve_voter_by_id(voter_id)
    if not voter_results['voter_found']:
        error_results = {
            'success':                      success,
            'status':                       'VOTER_NOT_FOUND_FROM_VOTE_ID',
            'voter_we_vote_id':             voter_we_vote_id,
            'we_vote_image_created':        we_vote_image_created,
            'image_not_found':              image_not_found,
            'image_url_valid':              image_url_valid,
            'image_stored_from_twitter':    image_stored_from_twitter,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    if positive_value_exists(voter_we_vote_id):
        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(0, voter_id)
        if voter_device_link_results['success']:
            google_civic_election_id = voter_device_link_results['voter_device_link'].google_civic_election_id
    else:
        error_results = {
            'success':                      success,
            'status':                       'VOTER_WE_VOTE_ID_INVALID',
            'voter_we_vote_id':             voter_we_vote_id,
            'we_vote_image_created':        we_vote_image_created,
            'image_not_found':              image_not_found,
            'image_url_valid':              image_url_valid,
            'image_stored_from_twitter':    image_stored_from_twitter,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    # create we_vote_image entry with voter_we_vote_id and google_civic_election_id and kind_of_image
    create_we_vote_image_results = we_vote_image_manager.create_we_vote_image(
        voter_we_vote_id, google_civic_election_id, kind_of_image_twitter_profile,
        kind_of_image_twitter_background, kind_of_image_twitter_banner)
    status += create_we_vote_image_results['status']
    if not create_we_vote_image_results['we_vote_image_saved']:
        error_results = {
            'success':                      success,
            'status':                       status,
            'voter_we_vote_id':             voter_we_vote_id,
            'we_vote_image_created':        we_vote_image_created,
            'image_not_found':              image_not_found,
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
    twitter_user_images_results = analyze_twitter_user_images(voter, kind_of_image_twitter_profile,
                                                              kind_of_image_twitter_background,
                                                              kind_of_image_twitter_banner)
    if twitter_user_images_results['image_not_found']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_NOT_FOUND",
            'voter_we_vote_id':             voter_we_vote_id,
            'we_vote_image_created':        True,
            'image_not_found':              True,
            'image_url_valid':              image_url_valid,
            'image_stored_from_twitter':    image_stored_from_twitter,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results
    elif not twitter_user_images_results['analyze_image_url_results']['image_url_valid']:
        error_results = {
            'success':                      success,
            'status':                       status + " IMAGE_URL_NOT_VALID",
            'voter_we_vote_id':             voter_we_vote_id,
            'we_vote_image_created':        True,
            'image_not_found':              image_not_found,
            'image_url_valid':              False,
            'image_stored_from_twitter':    image_stored_from_twitter,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    image_url_valid = True
    status += " IMAGE_URL_VALID"
    # if image url is valid then store source image of twitter to weVoteImage
    store_source_image_from_twitter_results = store_source_image_from_twitter(
        we_vote_image, twitter_user_images_results, kind_of_image_twitter_profile,
        kind_of_image_twitter_background, kind_of_image_twitter_banner)

    status += " " + store_source_image_from_twitter_results['status']
    if store_source_image_from_twitter_results['success'] or store_source_image_from_twitter_results['already_saved']:
        image_stored_from_twitter = True
        # ex twitter_profile_image_master-20170210_1_48x48.png
        we_vote_image_file_name = "{twitter_image_type}{master_image}-{date_image_saved}_{counter}_" \
                                  "{image_width}x{image_height}.{image_format}" \
                                  "".format(twitter_image_type=twitter_user_images_results['twitter_image_type'],
                                            master_image=MASTER_IMAGE, date_image_saved=time.strftime("%Y%m%d"),
                                            counter=str(counter),
                                            image_width=str(twitter_user_images_results['analyze_image_url_results']
                                                            ['image_width']),
                                            image_height=str(twitter_user_images_results['analyze_image_url_results']
                                                             ['image_height']),
                                            image_format=str(twitter_user_images_results['analyze_image_url_results']
                                                             ['image_format']))
        we_vote_image_file_location = voter_we_vote_id + "/" + we_vote_image_file_name
        is_active_version = check_source_image_active(twitter_user_images_results, kind_of_image_twitter_profile,
                                                      kind_of_image_twitter_background, kind_of_image_twitter_banner)

        image_stored_locally = store_source_image_locally(we_vote_image_file_name, twitter_user_images_results,
                                                          kind_of_image_twitter_profile,
                                                          kind_of_image_twitter_background,
                                                          kind_of_image_twitter_banner)
        if not image_stored_locally:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_LOCALLY",
                'voter_we_vote_id':             voter_we_vote_id,
                'we_vote_image_created':        we_vote_image_created,
                'image_not_found':              image_not_found,
                'image_url_valid':              image_url_valid,
                'image_stored_from_twitter':    image_stored_from_twitter,
                'image_stored_locally':         False,
                'image_stored_to_aws':          image_stored_to_aws,
            }
            return error_results

        status += " IMAGE_STORED_LOCALLY"
        image_stored_to_aws = we_vote_image_manager.store_image_to_aws(we_vote_image_file_name, we_vote_image_file_location)
        if not image_stored_to_aws:
            error_results = {
                'success':                      success,
                'status':                       status + " IMAGE_NOT_STORED_TO_AWS",
                'voter_we_vote_id':             voter_we_vote_id,
                'we_vote_image_created':        we_vote_image_created,
                'image_not_found':              image_not_found,
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
            'voter_we_vote_id':             voter_we_vote_id,
            'we_vote_image_created':        we_vote_image_created,
            'image_not_found':              image_not_found,
            'image_url_valid':              image_url_valid,
            'image_stored_from_twitter':    False,
            'image_stored_locally':         image_stored_locally,
            'image_stored_to_aws':          image_stored_to_aws,
        }
        return error_results

    results = {
        'success':                      success,
        'status':                       status,
        'voter_we_vote_id':             voter_we_vote_id,
        'we_vote_image_created':        we_vote_image_created,
        'image_not_found':              image_not_found,
        'image_url_valid':              image_url_valid,
        'image_stored_from_twitter':    image_stored_from_twitter,
        'image_stored_locally':         image_stored_locally,
        'image_stored_to_aws':          image_stored_to_aws,
    }
    return results


def analyze_twitter_user_images(voter, kind_of_image_twitter_profile, kind_of_image_twitter_background,
                                kind_of_image_twitter_banner):
    """
    Checking twitter user images if url is valid and getting image properties
    :param voter:
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
    image_not_found = False
    twitter_user_manager = TwitterUserManager()

    twitter_id = voter.twitter_id
    twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_id)
    if twitter_user_results['twitter_user_found']:
        if kind_of_image_twitter_profile:
            twitter_profile_image_url_https = twitter_user_results['twitter_user'].twitter_profile_image_url_https
            if twitter_profile_image_url_https:
                twitter_image_type = TWITTER_PROFILE_IMAGE_NAME
                analyze_image_url_results = analyze_remote_url(twitter_profile_image_url_https)
                if not analyze_image_url_results['image_url_valid']:
                    # image url is broken so reaching out to Twitter and getting new image
                    twitter_user_info_results = retrieve_twitter_user_info(twitter_id, twitter_handle='')
                    if 'profile_image_url_https' in twitter_user_info_results['twitter_json']:
                        # new twitter profile image found
                        twitter_profile_image_url_https = twitter_user_info_results['twitter_json'][
                            'profile_image_url_https']
                        analyze_image_url_results = analyze_remote_url(twitter_profile_image_url_https)
            else:
                image_not_found = True
        elif kind_of_image_twitter_background:
            twitter_profile_background_image_url_https = twitter_user_results['twitter_user'] \
                .twitter_profile_background_image_url_https
            if twitter_profile_background_image_url_https:
                twitter_image_type = TWITTER_BACKGROUND_IMAGE_NAME
                analyze_image_url_results = analyze_remote_url(twitter_profile_background_image_url_https)
                if not analyze_image_url_results['image_url_valid']:
                    # image url is broken so reaching out to Twitter and getting new image
                    twitter_user_info_results = retrieve_twitter_user_info(twitter_id, twitter_handle='')
                    if 'profile_background_image_url_https' in twitter_user_info_results['twitter_json']:
                        # new twitter profile image found
                        twitter_profile_background_image_url_https = twitter_user_info_results['twitter_json'][
                            'profile_background_image_url_https']
                        analyze_image_url_results = analyze_remote_url(twitter_profile_background_image_url_https)
            else:
                image_not_found = True
        elif kind_of_image_twitter_banner:
            twitter_profile_banner_url_https = twitter_user_results['twitter_user'].twitter_profile_banner_url_https
            if twitter_profile_banner_url_https:
                twitter_image_type = TWITTER_BANNER_IMAGE_NAME
                analyze_image_url_results = analyze_remote_url(twitter_profile_banner_url_https)
                if not analyze_image_url_results['image_url_valid']:
                    # image url is broken so reaching out to Twitter and getting new image
                    twitter_user_info_results = retrieve_twitter_user_info(twitter_id, twitter_handle='')
                    if 'profile_banner_url_https' in twitter_user_info_results['twitter_json']:
                        # new twitter profile image found
                        twitter_profile_banner_url_https = twitter_user_info_results['twitter_json'][
                            'profile_banner_url_https']
                        analyze_image_url_results = analyze_remote_url(twitter_profile_banner_url_https)
            else:
                image_not_found = True
    results = {
        'twitter_id':                                   twitter_id,
        'twitter_profile_image_url_https':              twitter_profile_image_url_https,
        'twitter_profile_background_image_url_https':   twitter_profile_background_image_url_https,
        'twitter_profile_banner_url_https':             twitter_profile_banner_url_https,
        'twitter_image_type':                           twitter_image_type,
        'analyze_image_url_results':                    analyze_image_url_results,
        'image_not_found':                              image_not_found
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

    twitter_user_info_results = retrieve_twitter_user_info(twitter_user_images_dict['twitter_id'], twitter_handle='')
    if twitter_user_info_results['success']:
        if kind_of_image_twitter_profile and 'profile_image_url_https' in twitter_user_info_results['twitter_json']:
            # new twitter profile image found
            if twitter_user_images_dict['twitter_profile_image_url_https'] == \
                    twitter_user_info_results['twitter_json']['profile_image_url_https']:
                is_active_version = True
        elif kind_of_image_twitter_background \
                and 'profile_background_image_url_https' in twitter_user_info_results['twitter_json']:
            # new twitter profile image found
            if twitter_user_images_dict['twitter_profile_background_image_url_https'] == \
                    twitter_user_info_results['twitter_json']['profile_background_image_url_https']:
                is_active_version = True
        elif kind_of_image_twitter_banner and 'profile_banner_url_https' in twitter_user_info_results['twitter_json']:
            # new twitter profile image found
            if twitter_user_images_dict['twitter_profile_banner_url_https'] == \
                    twitter_user_info_results['twitter_json']['profile_banner_url_https']:
                is_active_version = True

    return is_active_version


def store_source_image_from_twitter(we_vote_image, twitter_user_images_dict, kind_of_image_twitter_profile,
                                    kind_of_image_twitter_background, kind_of_image_twitter_banner):
    """
    Store source image from twitter to we_vote_image only if image is not already stored
    :param we_vote_image:
    :param twitter_user_images_dict:
    :param kind_of_image_twitter_profile:
    :param kind_of_image_twitter_background:
    :param kind_of_image_twitter_banner:
    :return:
    """
    '''
    # need to check: create will create new entrres always for same values? if yes then need to use get_or_create
    we_vote_image_manager.retrieve_we_vote_image(we_vote_image.voter_we_vote_id, kind_of_image_twitter_profile,
                                    kind_of_image_twitter_background, kind_of_image_twitter_banner,
                                    kind_of_image_profile_medium, kind_of_image_profile_tiny)
    '''
    we_vote_image_manager = WeVoteImageManager()

    if kind_of_image_twitter_profile and we_vote_image.twitter_profile_image_url_https != \
            twitter_user_images_dict['twitter_profile_image_url_https']:
        save_twitter_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(we_vote_image,
                                                                                          twitter_user_images_dict)
    elif kind_of_image_twitter_background and we_vote_image.twitter_profile_background_image_url_https != \
            twitter_user_images_dict['twitter_profile_background_image_url_https']:
        save_twitter_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(we_vote_image,
                                                                                          twitter_user_images_dict)
    elif kind_of_image_twitter_banner and we_vote_image.twitter_profile_banner_url_https != \
            twitter_user_images_dict['twitter_profile_banner_url_https']:
        save_twitter_info_results = we_vote_image_manager.save_we_vote_image_twitter_info(we_vote_image,
                                                                                          twitter_user_images_dict)
    else:
        save_twitter_info_results = {
            'status':           "IMAGE_ALREADY_SAVED_FROM_TWITTER",
            'success':          False,
            'we_vote_image':    we_vote_image,
            'already_saved':    True,
        }

    return save_twitter_info_results


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
