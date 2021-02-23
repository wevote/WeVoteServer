# campaign/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CampaignX, CampaignXManager, CampaignXOwner
import base64
from django.db.models import Q
from django.http import HttpResponse
from exception.models import handle_exception
from image.controllers import cache_campaignx_image, create_resized_images
import json
from io import BytesIO, StringIO
from PIL import Image, ImageOps
import re
from voter.models import fetch_voter_we_vote_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

# Search for in image/controllers.py as well
CAMPAIGN_PHOTO_LARGE_MAX_WIDTH = 640  # 1600
CAMPAIGN_PHOTO_LARGE_MAX_HEIGHT = 360  # 900


def campaignx_list_retrieve_for_api(voter_device_id):  # campaignListRetrieve
    """

    :param voter_device_id:
    :return:
    """
    campaignx_display_list = []
    status = ""
    voter_started_campaignx_we_vote_ids = []
    voter_supported_campaignx_we_vote_ids = []

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id=voter_device_id, read_only=True)
    if not positive_value_exists(voter_results['voter_found']):
        status += 'VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED '
        json_data = {
            'status': status,
            'success': False,
            'campaignx_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    # owned_by_voter_we_vote_id_list = [],
    # owned_by_organization_we_vote_id_list = []):

    # including_campaignx_we_vote_id_list = [],
    # excluding_campaignx_we_vote_id_list = [],
    # including_politicians_in_any_of_these_states = None,
    # including_politicians_with_support_in_any_of_these_issues = None):

    campaignx_manager = CampaignXManager()
    results = campaignx_manager.retrieve_campaignx_list(
        including_started_by_voter_we_vote_id=voter_we_vote_id)
    success = results['success']
    status += results['status']
    campaignx_list = results['campaignx_list']
    campaignx_list_found = results['campaignx_list_found']

    if success:
        for campaignx in campaignx_list:
            # Now calculate which campaigns belong to this voter
            if positive_value_exists(voter_we_vote_id):
                if campaignx.started_by_voter_we_vote_id == voter_we_vote_id:
                    voter_started_campaignx_we_vote_ids.append(campaignx.we_vote_id)
            one_campaignx = {
                'campaign_description':                     campaignx.campaign_description,
                'campaign_title':                           campaignx.campaign_title,
                'campaignx_we_vote_id':                     campaignx.we_vote_id,
                'in_draft_mode':                            campaignx.in_draft_mode,
                'supporters_count':                         campaignx.supporters_count,
                'we_vote_hosted_campaign_photo_large_url':  campaignx.we_vote_hosted_campaign_photo_large_url,
                'we_vote_hosted_campaign_photo_medium_url': campaignx.we_vote_hosted_campaign_photo_large_url,
            }
            campaignx_display_list.append(one_campaignx)

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'campaignx_list':                           campaignx_display_list,
        'campaignx_list_found':                     campaignx_list_found,
        'voter_started_campaignx_we_vote_ids':      voter_started_campaignx_we_vote_ids,
        'voter_supported_campaignx_we_vote_ids':    voter_supported_campaignx_we_vote_ids,
    }
    return json_data


def campaignx_retrieve_for_api(  # campaignRetrieve (CDN) & campaignRetrieveAsOwner (No CDN)
        voter_device_id='',
        campaignx_we_vote_id='',
        as_owner=False):
    status = ''
    campaignx_owner_list = []
    campaignx_politician_list = []

    campaignx_manager = CampaignXManager()
    if positive_value_exists(as_owner):
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_we_vote_id = voter.we_vote_id
        else:
            status += "VALID_VOTER_ID_MISSING "
            results = {
                'status':                           status,
                'success':                          False,
                'campaign_description':             '',
                'campaign_title':                   '',
                'in_draft_mode':                    True,
                'campaignx_owner_list':             campaignx_owner_list,
                'campaignx_politician_list':        campaignx_politician_list,
                'campaignx_we_vote_id':             '',
                'we_vote_hosted_campaign_photo_large_url':  '',
            }
            return results
        results = campaignx_manager.retrieve_campaignx_as_owner(
            campaignx_we_vote_id=campaignx_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
    else:
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            read_only=True,
        )
    status += results['status']
    if not results['success']:
        status += "CAMPAIGNX_RETRIEVE_ERROR "
        results = {
            'status':                           status,
            'success':                          False,
            'campaign_description':             '',
            'campaign_title':                   '',
            'in_draft_mode':                    True,
            'campaignx_owner_list':             campaignx_owner_list,
            'campaignx_politician_list':        campaignx_politician_list,
            'campaignx_we_vote_id':             '',
            'we_vote_hosted_campaign_photo_large_url': '',
        }
        return results
    elif not results['campaignx_found']:
        status += "CAMPAIGNX_NOT_FOUND: "
        status += results['status'] + " "
        results = {
            'status':                           status,
            'success':                          True,
            'campaign_description':             '',
            'campaign_title':                   '',
            'in_draft_mode':                    True,
            'campaignx_owner_list':             campaignx_owner_list,
            'campaignx_politician_list':        campaignx_politician_list,
            'campaignx_we_vote_id':             '',
            'we_vote_hosted_campaign_photo_large_url':  '',
        }
        return results

    campaignx = results['campaignx']
    campaignx_owner_list = results['campaignx_owner_list']
    if campaignx.politician_list_serialized:
        campaignx_politician_list = json.loads(campaignx.politician_list_serialized)
    else:
        campaignx_politician_list = []

    results = {
        'status':                           status,
        'success':                          True,
        'campaign_description':             campaignx.campaign_description,
        'campaign_title':                   campaignx.campaign_title,
        'in_draft_mode':                    campaignx.in_draft_mode,
        'campaignx_owner_list':             campaignx_owner_list,
        'campaignx_politician_list':        campaignx_politician_list,
        'campaignx_we_vote_id':             campaignx.we_vote_id,
        'we_vote_hosted_campaign_photo_large_url':  campaignx.we_vote_hosted_campaign_photo_large_url,
    }
    return results


def campaignx_save_for_api(  # campaignSave & campaignStartSave
        campaign_description='',
        campaign_description_changed=False,
        campaign_photo_from_file_reader='',
        campaign_photo_changed=False,
        campaign_title='',
        campaign_title_changed=False,
        campaignx_we_vote_id='',
        politician_list_serialized='',
        politician_list_changed=False,
        voter_device_id=''):
    status = ''
    success = True
    campaignx_owner_list = []
    campaignx_politician_list = []

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'campaign_description':         '',
            'campaign_title':               '',
            'in_draft_mode':                True,
            'campaignx_owner_list':         campaignx_owner_list,
            'campaignx_politician_list':    campaignx_politician_list,
            'campaignx_we_vote_id':         '',
            'we_vote_hosted_campaign_photo_large_url': '',
        }
        return results

    campaignx_manager = CampaignXManager()
    if positive_value_exists(campaignx_we_vote_id):
        viewer_is_owner = campaignx_manager.is_voter_campaignx_owner(
            campaignx_we_vote_id=campaignx_we_vote_id, voter_we_vote_id=voter_we_vote_id)
        if not positive_value_exists(viewer_is_owner):
            status += "VOTER_IS_NOT_OWNER_OF_CAMPAIGNX "
            results = {
                'status':                       status,
                'success':                      False,
                'campaign_description':         '',
                'campaign_title':               '',
                'in_draft_mode':                False,
                'campaignx_owner_list':         campaignx_owner_list,
                'campaignx_politician_list':    campaignx_politician_list,
                'campaignx_we_vote_id':         '',
                'we_vote_hosted_campaign_photo_large_url': '',
            }
            return results
        # Save campaign_photo_from_file_reader and get back we_vote_hosted_campaign_photo_original_url
        we_vote_hosted_campaign_photo_large_url = None
        we_vote_hosted_campaign_photo_original_url = None
        if campaign_photo_changed and campaign_photo_from_file_reader:
            photo_results = campaignx_save_photo_from_file_reader(
                campaignx_we_vote_id=campaignx_we_vote_id,
                campaign_photo_from_file_reader=campaign_photo_from_file_reader)
            if photo_results['we_vote_hosted_campaign_photo_original_url']:
                we_vote_hosted_campaign_photo_original_url = photo_results['we_vote_hosted_campaign_photo_original_url']
                # Now we want to resize to a large version
                create_resized_image_results = create_resized_images(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    we_vote_hosted_campaign_photo_original_url=we_vote_hosted_campaign_photo_original_url)
                we_vote_hosted_campaign_photo_large_url = \
                    create_resized_image_results['cached_resized_image_url_large']

        update_values = {
            'campaign_description':         campaign_description,
            'campaign_description_changed': campaign_description_changed,
            'campaign_photo_changed':       campaign_photo_changed,
            'campaign_title':               campaign_title,
            'campaign_title_changed':       campaign_title_changed,
            'politician_list_changed':      politician_list_changed,
            'politician_list_serialized':   politician_list_serialized,
            'we_vote_hosted_campaign_photo_large_url': we_vote_hosted_campaign_photo_large_url,
            'we_vote_hosted_campaign_photo_original_url': we_vote_hosted_campaign_photo_original_url,
        }
        create_results = campaignx_manager.update_or_create_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=linked_organization_we_vote_id,
            update_values=update_values,
        )
    else:
        # If here, we are working with a draft
        # Save campaign_photo_from_file_reader and get back we_vote_hosted_campaign_photo_large_url
        #  after initial update
        update_values = {
            'campaign_description':         campaign_description,
            'campaign_description_changed': campaign_description_changed,
            'campaign_title':               campaign_title,
            'campaign_title_changed':       campaign_title_changed,
            'politician_list_changed':      politician_list_changed,
            'politician_list_serialized':   politician_list_serialized,
        }
        create_results = campaignx_manager.update_or_create_campaignx(
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=linked_organization_we_vote_id,
            update_values=update_values,
        )
        if create_results['campaignx_created']:
            # Campaign was just created, so save the voter as an owner
            owner_results = campaignx_manager.update_or_create_campaignx_owner(
                campaignx_we_vote_id=create_results['campaignx_we_vote_id'],
                organization_we_vote_id=linked_organization_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            status += owner_results['status']
        if create_results['campaignx_found'] and campaign_photo_changed:
            campaignx = create_results['campaignx']
            if campaign_photo_from_file_reader:
                campaignx_we_vote_id = create_results['campaignx_we_vote_id']
                photo_results = campaignx_save_photo_from_file_reader(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    campaign_photo_from_file_reader=campaign_photo_from_file_reader)
                if photo_results['we_vote_hosted_campaign_photo_original_url']:
                    campaignx.we_vote_hosted_campaign_photo_original_url = \
                        photo_results['we_vote_hosted_campaign_photo_original_url']

                    # Now we want to resize to a large version
                    create_resized_image_results = create_resized_images(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        we_vote_hosted_campaign_photo_original_url=campaignx.we_vote_hosted_campaign_photo_original_url)
                    campaignx.we_vote_hosted_campaign_photo_large_url = \
                        create_resized_image_results['cached_resized_image_url_large']
                    campaignx.save()
            else:
                # Deleting image
                campaignx.we_vote_hosted_campaign_photo_large_url = None
                campaignx.save()

    status += create_results['status']
    if create_results['campaignx_found']:
        # Get owner_list
        results = campaignx_manager.retrieve_campaignx_as_owner(
            campaignx_we_vote_id=campaignx_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )

        campaignx = create_results['campaignx']
        campaignx_owner_list = results['campaignx_owner_list']
        # Get politician_list
        if campaignx.politician_list_serialized:
            campaignx_politician_list = json.loads(campaignx.politician_list_serialized)
        else:
            campaignx_politician_list = []

        results = {
            'status':                       status,
            'success':                      success,
            'campaign_description':         campaignx.campaign_description,
            'we_vote_hosted_campaign_photo_large_url': campaignx.we_vote_hosted_campaign_photo_large_url,
            'campaign_title':               campaignx.campaign_title,
            'in_draft_mode':                campaignx.in_draft_mode,
            'campaignx_politician_list':    campaignx_politician_list,
            'campaignx_owner_list':         campaignx_owner_list,
            'campaignx_we_vote_id':         campaignx.we_vote_id,
            'voter_we_vote_id':             voter_we_vote_id,
        }
        return results
    else:
        status += "CAMPAIGNX_SAVE_ERROR "
        results = {
            'status':                       status,
            'success':                      False,
            'campaign_description':         '',
            'we_vote_hosted_campaign_photo_large_url': '',
            'campaign_title':               '',
            'in_draft_mode':                True,
            'campaignx_owner_list':         [],
            'campaignx_politician_list':    [],
            'campaignx_we_vote_id':         '',
            'voter_we_vote_id':             voter_we_vote_id,
        }
        return results


def campaignx_save_photo_from_file_reader(
        campaignx_we_vote_id='',
        campaign_photo_from_file_reader=None):
    image_data_found = False
    python_image_library_image = None
    status = ""
    success = True
    we_vote_hosted_campaign_photo_original_url = ''

    if not positive_value_exists(campaignx_we_vote_id):
        status += "MISSING_CAMPAIGNX_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_campaign_photo_original_url': we_vote_hosted_campaign_photo_original_url,
        }
        return results

    if not positive_value_exists(campaign_photo_from_file_reader):
        status += "MISSING_CAMPAIGNX_PHOTO_FROM_FILE_READER "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_campaign_photo_original_url': we_vote_hosted_campaign_photo_original_url,
        }
        return results

    img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                        campaign_photo_from_file_reader).groupdict()
    if img_dict['encoding'] == 'base64':
        try:
            base64_data = img_dict['data']
            byte_data = base64.b64decode(base64_data)
            image_data = BytesIO(byte_data)
            python_image_library_image = Image.open(image_data)
            format_to_cache = python_image_library_image.format
            python_image_library_image.thumbnail(
                (CAMPAIGN_PHOTO_LARGE_MAX_WIDTH, CAMPAIGN_PHOTO_LARGE_MAX_HEIGHT), Image.ANTIALIAS)
            python_image_library_image.format = format_to_cache
            image_data_found = True
        except Exception as e:
            status += 'PROBLEM_DECODING_CAMPAIGN_PHOTO_LARGE: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))
    else:
        status += "INCOMING_CAMPAIGN_PHOTO_LARGE-BASE64_NOT_FOUND "

    if image_data_found:
        cache_results = cache_campaignx_image(
            python_image_library_image=python_image_library_image,
            campaignx_we_vote_id=campaignx_we_vote_id,
            kind_of_image_campaignx_photo=True,
            kind_of_image_original=True)
        status += cache_results['status']
        if cache_results['success']:
            cached_master_we_vote_image = cache_results['we_vote_image']
            we_vote_hosted_campaign_photo_original_url = cached_master_we_vote_image.we_vote_image_url

    results = {
        'status':                   status,
        'success':                  success,
        'we_vote_hosted_campaign_photo_original_url': we_vote_hosted_campaign_photo_original_url,
    }
    return results


def move_campaignx_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, from_organization_we_vote_id, to_organization_we_vote_id,
        to_organization_name=None):
    status = ''
    success = True
    campaignx_entries_moved = 0
    campaignx_owner_entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_CAMPAIGNX-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'to_voter_we_vote_id':              to_voter_we_vote_id,
            'campaignx_entries_moved':          campaignx_entries_moved,
            'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_CAMPAIGNX-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_voter_we_vote_id':            from_voter_we_vote_id,
            'to_voter_we_vote_id':              to_voter_we_vote_id,
            'campaignx_entries_moved':          campaignx_entries_moved,
            'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
        }
        return results

    # ######################
    # Move based on started_by_voter_we_vote_id
    try:
        campaignx_entries_moved += CampaignX.objects\
            .filter(started_by_voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(started_by_voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_UPDATE: " + str(e) + " "

    # ######################
    # Move based on voter_we_vote_id
    try:
        campaignx_owner_entries_moved += CampaignXOwner.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "

    # #############################################
    # Move based on organization_we_vote_id
    if positive_value_exists(to_organization_name):
        try:
            campaignx_owner_entries_moved += CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
    else:
        try:
            campaignx_owner_entries_moved += CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'campaignx_entries_moved':          campaignx_owner_entries_moved,
        'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
    }
    return results
