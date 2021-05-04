# campaign/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CampaignX, CampaignXManager, CampaignXOwner, CampaignXSupporter
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
CAMPAIGN_PHOTO_ORIGINAL_MAX_WIDTH = 1200
CAMPAIGN_PHOTO_ORIGINAL_MAX_HEIGHT = 628
CAMPAIGN_PHOTO_LARGE_MAX_WIDTH = 575
CAMPAIGN_PHOTO_LARGE_MAX_HEIGHT = 301
CAMPAIGN_PHOTO_MEDIUM_MAX_WIDTH = 224
CAMPAIGN_PHOTO_MEDIUM_MAX_HEIGHT = 117
CAMPAIGN_PHOTO_SMALL_MAX_WIDTH = 140
CAMPAIGN_PHOTO_SMALL_MAX_HEIGHT = 73


def campaignx_list_retrieve_for_api(request, voter_device_id, hostname=''):  # campaignListRetrieve
    """

    :param request:
    :param voter_device_id:
    :param hostname:
    :return:
    """
    campaignx_display_list = []
    status = ""
    promoted_campaignx_we_vote_ids = []
    voter_owned_campaignx_we_vote_ids = []
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
        # return HttpResponse(json.dumps(json_data), content_type='application/json')
        return json_data
    voter = voter_results['voter']
    voter_signed_in_with_email = voter.signed_in_with_email()
    voter_we_vote_id = voter.we_vote_id

    from organization.controllers import site_configuration_retrieve_for_api
    results = site_configuration_retrieve_for_api(hostname)
    site_owner_organization_we_vote_id = results['organization_we_vote_id']

    # owned_by_voter_we_vote_id_list = [],
    # owned_by_organization_we_vote_id_list = []):

    # including_campaignx_we_vote_id_list = [],
    # excluding_campaignx_we_vote_id_list = [],
    # including_politicians_in_any_of_these_states = None,
    # including_politicians_with_support_in_any_of_these_issues = None):

    # We need to know all of the politicians this voter can vote for so we can figure out
    #  if the voter can vote for any politicians in the election
    from ballot.controllers import what_voter_can_vote_for
    results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
    voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']

    visible_on_this_site_campaignx_we_vote_id_list = []
    campaignx_manager = CampaignXManager()
    if positive_value_exists(site_owner_organization_we_vote_id):
        results = campaignx_manager.retrieve_campaignx_list_for_private_label(
            including_started_by_voter_we_vote_id=voter_we_vote_id,
            site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
        visible_on_this_site_campaignx_we_vote_id_list = results['visible_on_this_site_campaignx_we_vote_id_list']
    else:
        results = campaignx_manager.retrieve_campaignx_list(
            including_started_by_voter_we_vote_id=voter_we_vote_id)
    success = results['success']
    status += results['status']
    campaignx_list = results['campaignx_list']
    campaignx_list_found = results['campaignx_list_found']

    if success:
        for campaignx in campaignx_list:
            # Now calculate which campaigns belong to this voter
            viewer_is_owner = False
            if positive_value_exists(voter_we_vote_id):
                if campaignx.started_by_voter_we_vote_id == voter_we_vote_id:
                    voter_started_campaignx_we_vote_ids.append(campaignx.we_vote_id)
                    viewer_is_owner = True
            if campaignx.is_still_active and campaignx.is_ok_to_promote_on_we_vote:
                if positive_value_exists(site_owner_organization_we_vote_id):
                    if campaignx.we_vote_id in visible_on_this_site_campaignx_we_vote_id_list:
                        promoted_campaignx_we_vote_ids.append(campaignx.we_vote_id)
                else:
                    promoted_campaignx_we_vote_ids.append(campaignx.we_vote_id)

            campaignx_owner_object_list = campaignx_manager.retrieve_campaignx_owner_list(
                campaignx_we_vote_id=campaignx.we_vote_id, viewer_is_owner=viewer_is_owner)
            campaignx_owner_list = []
            for campaignx_owner in campaignx_owner_object_list:
                campaign_owner_dict = {
                    'organization_name':                        campaignx_owner.organization_name,
                    'organization_we_vote_id':                  campaignx_owner.organization_we_vote_id,
                    'feature_this_profile_image':               campaignx_owner.feature_this_profile_image,
                    'visible_to_public':                        campaignx_owner.visible_to_public,
                    'we_vote_hosted_profile_image_url_tiny':    campaignx_owner.we_vote_hosted_profile_image_url_tiny,
                }
                campaignx_owner_list.append(campaign_owner_dict)

            if campaignx.politician_starter_list_serialized:
                campaignx_politician_starter_list = json.loads(campaignx.politician_starter_list_serialized)
            else:
                campaignx_politician_starter_list = []

            campaignx_politician_list_modified = []
            campaignx_politician_list_exists = False
            campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
                campaignx_we_vote_id=campaignx.we_vote_id,
            )

            for campaignx_politician in campaignx_politician_list:
                campaignx_politician_list_exists = True
                campaignx_politician_dict = {
                    'campaignx_politician_id':  campaignx_politician.id,
                    'politician_name': campaignx_politician.politician_name,
                    'politician_we_vote_id': campaignx_politician.politician_we_vote_id,
                    'state_code': campaignx_politician.state_code,
                    'we_vote_hosted_profile_image_url_large':
                        campaignx_politician.we_vote_hosted_profile_image_url_large,
                    'we_vote_hosted_profile_image_url_medium':
                        campaignx_politician.we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_image_url_tiny': campaignx_politician.we_vote_hosted_profile_image_url_tiny,
                }
                campaignx_politician_list_modified.append(campaignx_politician_dict)

            # Get list of SEO Friendly Paths related to this campaignX. For most campaigns, there will only be one.
            seo_friendly_path_list = campaignx_manager.retrieve_seo_friendly_path_simple_list(
                campaignx_we_vote_id=campaignx.we_vote_id,
            )

            supporter_results = campaignx_manager.retrieve_campaignx_supporter(
                campaignx_we_vote_id=campaignx.we_vote_id,
                voter_we_vote_id=voter_we_vote_id,
                read_only=True)
            if supporter_results['success'] and supporter_results['campaignx_supporter_found']:
                campaignx_supporter = supporter_results['campaignx_supporter']
                date_last_changed_string = ''
                date_supported_string = ''
                try:
                    date_last_changed_string = campaignx_supporter.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
                    date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    status += "DATE_CONVERSION_ERROR: " + str(e) + " "
                voter_campaignx_supporter_dict = {
                    'campaign_supported':           campaignx_supporter.campaign_supported,
                    'campaignx_we_vote_id':         campaignx_supporter.campaignx_we_vote_id,
                    'date_last_changed':            date_last_changed_string,
                    'date_supported':               date_supported_string,
                    'id':                           campaignx_supporter.id,
                    'organization_we_vote_id':      campaignx_supporter.organization_we_vote_id,
                    'supporter_endorsement':        campaignx_supporter.supporter_endorsement,
                    'supporter_name':               campaignx_supporter.supporter_name,
                    'visible_to_public':            campaignx_supporter.visible_to_public,
                    'voter_we_vote_id':             campaignx_supporter.voter_we_vote_id,
                    'voter_signed_in_with_email':   voter_signed_in_with_email,
                    'we_vote_hosted_profile_photo_image_url_tiny':
                    campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
                }
            else:
                voter_campaignx_supporter_dict = {}

            if hasattr(campaignx, 'visible_on_this_site'):
                visible_on_this_site = campaignx.visible_on_this_site
            else:
                visible_on_this_site = True

            # If smaller sizes weren't stored, use large image
            if campaignx.we_vote_hosted_campaign_photo_medium_url:
                we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_medium_url
            else:
                we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_large_url
            if campaignx.we_vote_hosted_campaign_photo_small_url:
                we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_small_url
            else:
                we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_large_url
            one_campaignx = {
                'campaign_description':                     campaignx.campaign_description,
                'campaignx_owner_list':                     campaignx_owner_list,
                'campaignx_politician_list':                campaignx_politician_list_modified,
                'campaignx_politician_list_exists':         campaignx_politician_list_exists,
                'campaignx_politician_starter_list':        campaignx_politician_starter_list,
                'campaign_title':                           campaignx.campaign_title,
                'campaignx_we_vote_id':                     campaignx.we_vote_id,
                'in_draft_mode':                            campaignx.in_draft_mode,
                'seo_friendly_path':                        campaignx.seo_friendly_path,
                'seo_friendly_path_list':                   seo_friendly_path_list,
                'supporters_count':                         campaignx.supporters_count,
                'visible_on_this_site':                     visible_on_this_site,
                'voter_campaignx_supporter':                voter_campaignx_supporter_dict,
                'voter_signed_in_with_email':               voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url':  campaignx.we_vote_hosted_campaign_photo_large_url,
                'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
                'we_vote_hosted_campaign_photo_small_url':  we_vote_hosted_campaign_photo_small_url,
            }
            campaignx_display_list.append(one_campaignx)

        voter_owned_list = campaignx_manager.retrieve_campaignx_owner_list(
            voter_we_vote_id=voter_we_vote_id,
            viewer_is_owner=True,
            read_only=True)
        for one_owner in voter_owned_list:
            voter_owned_campaignx_we_vote_ids.append(one_owner.campaignx_we_vote_id)

        supporter_list_results = campaignx_manager.retrieve_campaignx_supporter_list(
            voter_we_vote_id=voter_we_vote_id,
            limit=0,
            require_visible_to_public=False,
            read_only=True)
        if supporter_list_results['supporter_list_found']:
            supporter_list = supporter_list_results['supporter_list']
            for one_supporter in supporter_list:
                voter_supported_campaignx_we_vote_ids.append(one_supporter.campaignx_we_vote_id)

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'campaignx_list':                           campaignx_display_list,
        'campaignx_list_found':                     campaignx_list_found,
        'promoted_campaignx_we_vote_ids':           promoted_campaignx_we_vote_ids,
        'voter_can_vote_for_politician_we_vote_ids': voter_can_vote_for_politician_we_vote_ids,
        'voter_owned_campaignx_we_vote_ids':        voter_owned_campaignx_we_vote_ids,
        'voter_started_campaignx_we_vote_ids':      voter_started_campaignx_we_vote_ids,
        'voter_supported_campaignx_we_vote_ids':    voter_supported_campaignx_we_vote_ids,
    }
    return json_data


def campaignx_retrieve_for_api(  # campaignRetrieve & campaignRetrieveAsOwner (No CDN)
        request=None,
        voter_device_id='',
        campaignx_we_vote_id='',
        seo_friendly_path='',
        as_owner=False,
        hostname=''):
    status = ''
    campaignx_owner_list = []
    campaignx_politician_starter_list = []
    seo_friendly_path_list = []
    voter_signed_in_with_email = False
    voter_we_vote_id = ''

    campaignx_manager = CampaignXManager()
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
    if positive_value_exists(as_owner):
        if not positive_value_exists(voter_we_vote_id):
            status += "VALID_VOTER_ID_MISSING "
            results = {
                'status':                           status,
                'success':                          False,
                'campaign_description':             '',
                'campaign_title':                   '',
                'campaignx_owner_list':             campaignx_owner_list,
                'campaignx_politician_list':        [],
                'campaignx_politician_list_exists': False,
                'campaignx_politician_starter_list': campaignx_politician_starter_list,
                'campaignx_we_vote_id':             '',
                'in_draft_mode':                    True,
                'seo_friendly_path':                '',
                'seo_friendly_path_list':           seo_friendly_path_list,
                'supporters_count':                 0,
                'visible_on_this_site':             False,
                'voter_campaignx_supporter':        {},
                'voter_signed_in_with_email':       voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url':  '',
                'we_vote_hosted_campaign_photo_medium_url': '',
                'we_vote_hosted_campaign_photo_small_url': '',
            }
            return results
        results = campaignx_manager.retrieve_campaignx_as_owner(
            campaignx_we_vote_id=campaignx_we_vote_id,
            seo_friendly_path=seo_friendly_path,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
    else:
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            seo_friendly_path=seo_friendly_path,
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
            'campaignx_owner_list':             campaignx_owner_list,
            'campaignx_politician_list':        [],
            'campaignx_politician_list_exists': False,
            'campaignx_politician_starter_list': campaignx_politician_starter_list,
            'campaignx_we_vote_id':             '',
            'in_draft_mode':                    True,
            'seo_friendly_path':                '',
            'seo_friendly_path_list':           seo_friendly_path_list,
            'supporters_count':                 0,
            'visible_on_this_site':             False,
            'voter_campaignx_supporter':        {},
            'voter_signed_in_with_email':       voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url': '',
            'we_vote_hosted_campaign_photo_medium_url': '',
            'we_vote_hosted_campaign_photo_small_url': '',
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
            'campaignx_owner_list':             campaignx_owner_list,
            'campaignx_politician_list':        [],
            'campaignx_politician_list_exists': False,
            'campaignx_politician_starter_list': campaignx_politician_starter_list,
            'campaignx_we_vote_id':             '',
            'in_draft_mode':                    True,
            'seo_friendly_path':                '',
            'seo_friendly_path_list':           seo_friendly_path_list,
            'supporters_count':                 0,
            'visible_on_this_site':             False,
            'voter_campaignx_supporter':        {},
            'voter_signed_in_with_email':       voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url':  '',
            'we_vote_hosted_campaign_photo_medium_url': '',
            'we_vote_hosted_campaign_photo_small_url': '',
        }
        return results

    campaignx = results['campaignx']
    campaignx_owner_list = results['campaignx_owner_list']
    seo_friendly_path_list = results['seo_friendly_path_list']

    from organization.controllers import site_configuration_retrieve_for_api
    site_results = site_configuration_retrieve_for_api(hostname)
    site_owner_organization_we_vote_id = site_results['organization_we_vote_id']

    if positive_value_exists(site_owner_organization_we_vote_id):
        try:
            visible_on_this_site_campaignx_we_vote_id_list = \
                campaignx_manager.retrieve_visible_on_this_site_campaignx_simple_list(
                    site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            if campaignx.we_vote_id in visible_on_this_site_campaignx_we_vote_id_list:
                campaignx.visible_on_this_site = True
            else:
                campaignx.visible_on_this_site = False
        except Exception as e:
            success = False
            status += "RETRIEVE_CAMPAIGNX_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "
    else:
        campaignx.visible_on_this_site = True

    if campaignx.politician_starter_list_serialized:
        campaignx_politician_starter_list = json.loads(campaignx.politician_starter_list_serialized)
    else:
        campaignx_politician_starter_list = []

    campaignx_politician_list_modified = []
    campaignx_politician_list_exists = False
    campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
    )

    # We need to know all of the politicians this voter can vote for so we can figure out
    #  if the voter can vote for any politicians in the election
    from ballot.controllers import what_voter_can_vote_for
    results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
    voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']

    for campaignx_politician in campaignx_politician_list:
        campaignx_politician_list_exists = True
        campaignx_politician_dict = {
            'campaignx_politician_id': campaignx_politician.id,
            'politician_name':  campaignx_politician.politician_name,
            'politician_we_vote_id':  campaignx_politician.politician_we_vote_id,
            'state_code':  campaignx_politician.state_code,
            'we_vote_hosted_profile_image_url_large': campaignx_politician.we_vote_hosted_profile_image_url_large,
            'we_vote_hosted_profile_image_url_medium': campaignx_politician.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_image_url_tiny': campaignx_politician.we_vote_hosted_profile_image_url_tiny,
        }
        campaignx_politician_list_modified.append(campaignx_politician_dict)

    supporter_results = campaignx_manager.retrieve_campaignx_supporter(
        campaignx_we_vote_id=campaignx.we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        read_only=True)
    if supporter_results['success'] and supporter_results['campaignx_supporter_found']:
        campaignx_supporter = supporter_results['campaignx_supporter']
        date_last_changed_string = ''
        date_supported_string = ''
        try:
            date_last_changed_string = campaignx_supporter.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
            date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            status += "DATE_CONVERSION_ERROR: " + str(e) + " "
        voter_campaignx_supporter_dict = {
            'campaign_supported':           campaignx_supporter.campaign_supported,
            'campaignx_we_vote_id':         campaignx_supporter.campaignx_we_vote_id,
            'date_last_changed':            date_last_changed_string,
            'date_supported':               date_supported_string,
            'id':                           campaignx_supporter.id,
            'organization_we_vote_id':      campaignx_supporter.organization_we_vote_id,
            'supporter_endorsement':        campaignx_supporter.supporter_endorsement,
            'supporter_name':               campaignx_supporter.supporter_name,
            'visible_to_public':            campaignx_supporter.visible_to_public,
            'voter_we_vote_id':             campaignx_supporter.voter_we_vote_id,
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
        }
    else:
        voter_campaignx_supporter_dict = {}

    # Get most recent supporters
    latest_campaignx_supporter_list = []
    supporter_list_results = campaignx_manager.retrieve_campaignx_supporter_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
        limit=7,
        read_only=True)
    if supporter_list_results['supporter_list_found']:
        supporter_list = supporter_list_results['supporter_list']
        for campaignx_supporter in supporter_list:
            date_supported_string = ''
            try:
                date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                status += "DATE_CONVERSION_ERROR: " + str(e) + " "
            one_supporter_dict = {
                'id': campaignx_supporter.id,
                'date_supported': date_supported_string,
                'organization_we_vote_id': campaignx_supporter.organization_we_vote_id,
                'supporter_endorsement': campaignx_supporter.supporter_endorsement,
                'supporter_name': campaignx_supporter.supporter_name,
                'voter_we_vote_id': campaignx_supporter.voter_we_vote_id,
                'we_vote_hosted_profile_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
            }
            latest_campaignx_supporter_list.append(one_supporter_dict)

    # Get most recent supporter_endorsements
    latest_campaignx_supporter_endorsement_list = []
    supporter_list_results = campaignx_manager.retrieve_campaignx_supporter_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
        limit=10,
        require_supporter_endorsement=True,
        read_only=True)
    if supporter_list_results['supporter_list_found']:
        supporter_list = supporter_list_results['supporter_list']
        for campaignx_supporter in supporter_list:
            date_supported_string = ''
            try:
                date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                status += "DATE_CONVERSION_ERROR: " + str(e) + " "
            one_supporter_dict = {
                'id': campaignx_supporter.id,
                'date_supported': date_supported_string,
                'organization_we_vote_id': campaignx_supporter.organization_we_vote_id,
                'supporter_endorsement': campaignx_supporter.supporter_endorsement,
                'supporter_name': campaignx_supporter.supporter_name,
                'voter_we_vote_id': campaignx_supporter.voter_we_vote_id,
                'we_vote_hosted_profile_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
            }
            latest_campaignx_supporter_endorsement_list.append(one_supporter_dict)

    # If smaller sizes weren't stored, use large image
    if campaignx.we_vote_hosted_campaign_photo_medium_url:
        we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_medium_url
    else:
        we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_large_url
    if campaignx.we_vote_hosted_campaign_photo_small_url:
        we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_small_url
    else:
        we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_large_url
    results = {
        'status':                           status,
        'success':                          True,
        'campaign_description':             campaignx.campaign_description,
        'campaign_title':                   campaignx.campaign_title,
        'in_draft_mode':                    campaignx.in_draft_mode,
        'campaignx_owner_list':             campaignx_owner_list,
        'campaignx_politician_list':        campaignx_politician_list_modified,
        'campaignx_politician_list_exists': campaignx_politician_list_exists,
        'campaignx_politician_starter_list': campaignx_politician_starter_list,
        'campaignx_we_vote_id':             campaignx.we_vote_id,
        'latest_campaignx_supporter_endorsement_list':  latest_campaignx_supporter_endorsement_list,
        'latest_campaignx_supporter_list':  latest_campaignx_supporter_list,
        'seo_friendly_path':                campaignx.seo_friendly_path,
        'seo_friendly_path_list':           seo_friendly_path_list,
        'supporters_count':                 campaignx.supporters_count,
        'visible_on_this_site':             campaignx.visible_on_this_site,
        'voter_campaignx_supporter':        voter_campaignx_supporter_dict,
        'voter_can_vote_for_politician_we_vote_ids': voter_can_vote_for_politician_we_vote_ids,
        'voter_signed_in_with_email':       voter_signed_in_with_email,
        'we_vote_hosted_campaign_photo_large_url':  campaignx.we_vote_hosted_campaign_photo_large_url,
        'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
        'we_vote_hosted_campaign_photo_small_url': we_vote_hosted_campaign_photo_small_url,
    }
    return results


def campaignx_save_for_api(  # campaignSave & campaignStartSave
        campaign_description='',
        campaign_description_changed=False,
        in_draft_mode=False,
        in_draft_mode_changed=False,
        campaign_photo_from_file_reader='',
        campaign_photo_changed=False,
        campaign_title='',
        campaign_title_changed=False,
        campaignx_we_vote_id='',
        politician_delete_list_serialized='',
        politician_starter_list_serialized='',
        politician_starter_list_changed=False,
        voter_device_id=''):
    status = ''
    success = True
    campaignx_owner_list = []
    campaignx_politician_starter_list = []
    seo_friendly_path_list = []
    voter_signed_in_with_email = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
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
            'campaignx_politician_list':    [],
            'campaignx_politician_list_exists': False,
            'campaignx_politician_starter_list':    campaignx_politician_starter_list,
            'campaignx_we_vote_id':         '',
            'seo_friendly_path':            '',
            'seo_friendly_path_list':       seo_friendly_path_list,
            'supporters_count':             0,
            'visible_on_this_site':         False,
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url': '',
            'we_vote_hosted_campaign_photo_medium_url': '',
            'we_vote_hosted_campaign_photo_small_url': '',
        }
        return results

    if positive_value_exists(in_draft_mode_changed) and not positive_value_exists(in_draft_mode):
        # To publish a campaign, voter must be signed in with an email address
        if not voter.signed_in_with_email():
            status += "MUST_BE_SIGNED_IN_WITH_EMAIL "
            results = {
                'status':                       status,
                'success':                      False,
                'campaign_description':         '',
                'campaign_title':               '',
                'campaignx_owner_list':         campaignx_owner_list,
                'campaignx_politician_list':    [],
                'campaignx_politician_list_exists': False,
                'campaignx_politician_starter_list': campaignx_politician_starter_list,
                'campaignx_we_vote_id':         '',
                'in_draft_mode':                True,
                'seo_friendly_path':            '',
                'seo_friendly_path_list':       seo_friendly_path_list,
                'supporters_count':             0,
                'visible_on_this_site':         False,
                'voter_signed_in_with_email':   voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url': '',
                'we_vote_hosted_campaign_photo_medium_url': '',
                'we_vote_hosted_campaign_photo_small_url': '',
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
                'campaignx_owner_list':         campaignx_owner_list,
                'campaignx_politician_list':    [],
                'campaignx_politician_list_exists': False,
                'campaignx_politician_starter_list': campaignx_politician_starter_list,
                'campaignx_we_vote_id':         '',
                'in_draft_mode':                False,
                'seo_friendly_path':            '',
                'seo_friendly_path_list':       seo_friendly_path_list,
                'supporters_count':             0,
                'visible_on_this_site':         False,
                'voter_signed_in_with_email':   voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url': '',
                'we_vote_hosted_campaign_photo_medium_url': '',
                'we_vote_hosted_campaign_photo_small_url': '',
            }
            return results
        # Save campaign_photo_from_file_reader and get back we_vote_hosted_campaign_photo_original_url
        we_vote_hosted_campaign_photo_large_url = None
        we_vote_hosted_campaign_photo_medium_url = None
        we_vote_hosted_campaign_photo_original_url = None
        we_vote_hosted_campaign_photo_small_url = None
        if campaign_photo_changed and campaign_photo_from_file_reader:
            photo_results = campaignx_save_photo_from_file_reader(
                campaignx_we_vote_id=campaignx_we_vote_id,
                campaign_photo_from_file_reader=campaign_photo_from_file_reader)
            if photo_results['we_vote_hosted_campaign_photo_original_url']:
                we_vote_hosted_campaign_photo_original_url = photo_results['we_vote_hosted_campaign_photo_original_url']
                # Now we want to resize to a large version
                create_resized_image_results = create_resized_images(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    campaignx_photo_url_https=we_vote_hosted_campaign_photo_original_url)
                we_vote_hosted_campaign_photo_large_url = \
                    create_resized_image_results['cached_resized_image_url_large']
                we_vote_hosted_campaign_photo_medium_url = \
                    create_resized_image_results['cached_resized_image_url_medium']
                we_vote_hosted_campaign_photo_small_url = \
                    create_resized_image_results['cached_resized_image_url_tiny']

        update_values = {
            'campaign_description':         campaign_description,
            'campaign_description_changed': campaign_description_changed,
            'in_draft_mode':                in_draft_mode,
            'in_draft_mode_changed':        in_draft_mode_changed,
            'campaign_photo_changed':       campaign_photo_changed,
            'campaign_title':               campaign_title,
            'campaign_title_changed':       campaign_title_changed,
            'politician_delete_list_serialized':   politician_delete_list_serialized,
            'politician_starter_list_changed':      politician_starter_list_changed,
            'politician_starter_list_serialized':   politician_starter_list_serialized,
            'we_vote_hosted_campaign_photo_large_url': we_vote_hosted_campaign_photo_large_url,
            'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
            'we_vote_hosted_campaign_photo_small_url': we_vote_hosted_campaign_photo_small_url,
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
            'in_draft_mode':                in_draft_mode,
            'in_draft_mode_changed':        in_draft_mode_changed,
            'campaign_title':               campaign_title,
            'campaign_title_changed':       campaign_title_changed,
            'politician_delete_list_serialized':   politician_delete_list_serialized,
            'politician_starter_list_changed':      politician_starter_list_changed,
            'politician_starter_list_serialized':   politician_starter_list_serialized,
        }
        create_results = campaignx_manager.update_or_create_campaignx(
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=linked_organization_we_vote_id,
            update_values=update_values,
        )
        if create_results['campaignx_created']:
            # Campaign was just created, so save the voter as an owner
            campaignx_we_vote_id = create_results['campaignx_we_vote_id']
            owner_results = campaignx_manager.update_or_create_campaignx_owner(
                campaignx_we_vote_id=campaignx_we_vote_id,
                organization_we_vote_id=linked_organization_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            status += owner_results['status']
        if create_results['campaignx_found'] and campaign_photo_changed:
            campaignx = create_results['campaignx']
            campaignx_we_vote_id = create_results['campaignx_we_vote_id']
            if campaign_photo_from_file_reader:
                photo_results = campaignx_save_photo_from_file_reader(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    campaign_photo_from_file_reader=campaign_photo_from_file_reader)
                if photo_results['we_vote_hosted_campaign_photo_original_url']:
                    campaignx.we_vote_hosted_campaign_photo_original_url = \
                        photo_results['we_vote_hosted_campaign_photo_original_url']

                    # Now we want to resize to a large version
                    create_resized_image_results = create_resized_images(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        campaignx_photo_url_https=campaignx.we_vote_hosted_campaign_photo_original_url)
                    campaignx.we_vote_hosted_campaign_photo_large_url = \
                        create_resized_image_results['cached_resized_image_url_large']
                    campaignx.we_vote_hosted_campaign_photo_medium_url = \
                        create_resized_image_results['cached_resized_image_url_medium']
                    campaignx.we_vote_hosted_campaign_photo_small_url = \
                        create_resized_image_results['cached_resized_image_url_tiny']
                    campaignx.save()
            else:
                # Deleting image
                campaignx.we_vote_hosted_campaign_photo_large_url = None
                campaignx.we_vote_hosted_campaign_photo_medium_url = None
                campaignx.we_vote_hosted_campaign_photo_small_url = None
                campaignx.save()

    status += create_results['status']
    if create_results['campaignx_found']:
        campaignx = create_results['campaignx']
        campaignx_we_vote_id = campaignx.we_vote_id

        # Get owner_list
        results = campaignx_manager.retrieve_campaignx_as_owner(
            campaignx_we_vote_id=campaignx_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
        campaignx_owner_list = results['campaignx_owner_list']

        # Get politician_starter_list
        if campaignx.politician_starter_list_serialized:
            campaignx_politician_starter_list = json.loads(campaignx.politician_starter_list_serialized)
        else:
            campaignx_politician_starter_list = []

        campaignx_politician_list_modified = []
        campaignx_politician_list_exists = False
        # if positive_value_exists(politician_starter_list_changed):
        #     results = campaignx_manager.update_or_create_campaignx_politicians_from_starter(
        #         campaignx_we_vote_id=campaignx.we_vote_id,
        #         politician_starter_list=campaignx_politician_starter_list,
        #     )
        #     campaignx_politician_list_exists = results['campaignx_politician_list_found']
        #     campaignx_politician_list = results['campaignx_politician_list']
        # else:
        campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
            campaignx_we_vote_id=campaignx_we_vote_id,
        )
        # Convert to json-friendly
        for campaignx_politician in campaignx_politician_list:
            campaignx_politician_list_exists = True
            campaignx_politician_dict = {
                'campaignx_politician_id': campaignx_politician.id,
                'politician_name':  campaignx_politician.politician_name,
                'politician_we_vote_id':  campaignx_politician.politician_we_vote_id,
                'state_code':  campaignx_politician.state_code,
                'we_vote_hosted_profile_image_url_large': campaignx_politician.we_vote_hosted_profile_image_url_large,
                'we_vote_hosted_profile_image_url_medium': campaignx_politician.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': campaignx_politician.we_vote_hosted_profile_image_url_tiny,
            }
            campaignx_politician_list_modified.append(campaignx_politician_dict)

        # Get list of SEO Friendly Paths related to this campaignX. For most campaigns, there will only be one.
        seo_friendly_path_list = campaignx_manager.retrieve_seo_friendly_path_simple_list(
            campaignx_we_vote_id=campaignx_we_vote_id,
        )

        if in_draft_mode_changed and not positive_value_exists(in_draft_mode):
            if voter.signed_in_with_email():
                # Make sure the person creating the campaign has a campaignx_supporter entry IFF they are signed in
                update_values = {
                    'campaign_supported': True,
                    'campaign_supported_changed': True,
                    'supporter_endorsement': '',
                    'supporter_endorsement_changed': False,
                    'visible_to_public': True,
                    'visible_to_public_changed': True,
                }
                create_results = campaignx_manager.update_or_create_campaignx_supporter(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                    organization_we_vote_id=linked_organization_we_vote_id,
                    update_values=update_values,
                )
                status += create_results['status']
                # Make sure an owner entry exists
                owner_results = campaignx_manager.update_or_create_campaignx_owner(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    organization_we_vote_id=linked_organization_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id)
                status += owner_results['status']

        if hasattr(campaignx, 'visible_on_this_site'):
            visible_on_this_site = campaignx.visible_on_this_site
        else:
            visible_on_this_site = True

        # If smaller sizes weren't stored, use large image
        if campaignx.we_vote_hosted_campaign_photo_medium_url:
            we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_medium_url
        else:
            we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_large_url
        if campaignx.we_vote_hosted_campaign_photo_small_url:
            we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_small_url
        else:
            we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_large_url
        results = {
            'status':                       status,
            'success':                      success,
            'campaign_description':         campaignx.campaign_description,
            'campaign_title':               campaignx.campaign_title,
            'campaignx_owner_list':         campaignx_owner_list,
            'campaignx_politician_list':            campaignx_politician_list_modified,
            'campaignx_politician_list_exists':     campaignx_politician_list_exists,
            'campaignx_politician_starter_list':    campaignx_politician_starter_list,
            'campaignx_we_vote_id':         campaignx.we_vote_id,
            'in_draft_mode':                campaignx.in_draft_mode,
            'seo_friendly_path':            campaignx.seo_friendly_path,
            'seo_friendly_path_list':       seo_friendly_path_list,
            'supporters_count':             campaignx.supporters_count,
            'visible_on_this_site':         visible_on_this_site,
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url': campaignx.we_vote_hosted_campaign_photo_large_url,
            'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
            'we_vote_hosted_campaign_photo_small_url': we_vote_hosted_campaign_photo_small_url,
        }
        return results
    else:
        status += "CAMPAIGNX_SAVE_ERROR "
        results = {
            'status':                       status,
            'success':                      False,
            'campaign_description':         '',
            'campaign_title':               '',
            'campaignx_owner_list':         [],
            'campaignx_politician_list':    [],
            'campaignx_politician_list_exists': False,
            'campaignx_politician_starter_list':    [],
            'campaignx_we_vote_id':         '',
            'in_draft_mode':                True,
            'seo_friendly_path':            '',
            'seo_friendly_path_list':       [],
            'supporters_count':             0,
            'visible_on_this_site':         False,
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url': '',
            'we_vote_hosted_campaign_photo_medium_url': '',
            'we_vote_hosted_campaign_photo_small_url': '',
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
                (CAMPAIGN_PHOTO_ORIGINAL_MAX_WIDTH, CAMPAIGN_PHOTO_ORIGINAL_MAX_HEIGHT), Image.ANTIALIAS)
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
            try:
                we_vote_hosted_campaign_photo_original_url = cached_master_we_vote_image.we_vote_image_url
            except Exception as e:
                status += "FAILED_TO_CACHE_CAMPAIGNX_IMAGE: " + str(e) + ' '
                success = False
        else:
            success = False
    results = {
        'status':                   status,
        'success':                  success,
        'we_vote_hosted_campaign_photo_original_url': we_vote_hosted_campaign_photo_original_url,
    }
    return results


def campaignx_supporter_retrieve_for_api(  # campaignSupporterRetrieve
        voter_device_id='',
        campaignx_we_vote_id=''):
    status = ''
    voter_signed_in_with_email = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    campaignx_manager = CampaignXManager()
    results = campaignx_manager.retrieve_campaignx_supporter(
        campaignx_we_vote_id=campaignx_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        read_only=True,
    )
    status += results['status']
    if not results['success']:
        status += "CAMPAIGNX_SUPPORTER_RETRIEVE_ERROR "
        results = {
            'status':                       status,
            'success':                      False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results
    elif not results['campaignx_supporter_found']:
        status += "CAMPAIGNX_SUPPORTER_NOT_FOUND: "
        status += results['status'] + " "
        results = {
            'status':                       status,
            'success':                      False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    campaignx_supporter = results['campaignx_supporter']
    date_last_changed_string = ''
    date_supported_string = ''
    try:
        date_last_changed_string = campaignx_supporter.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
        date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        status += "DATE_CONVERSION_ERROR: " + str(e) + " "
    results = {
        'status':                       status,
        'success':                      True,
        'campaignx_we_vote_id':         campaignx_supporter.campaignx_we_vote_id,
        'date_last_changed':            date_last_changed_string,
        'date_supported':               date_supported_string,
        'organization_we_vote_id':      campaignx_supporter.organization_we_vote_id,
        'supporter_endorsement':        campaignx_supporter.supporter_endorsement,
        'supporter_name':               campaignx_supporter.supporter_name,
        'visible_to_public':            campaignx_supporter.visible_to_public,
        'voter_we_vote_id':             campaignx_supporter.voter_we_vote_id,
        'voter_signed_in_with_email':   voter_signed_in_with_email,
        'we_vote_hosted_profile_photo_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
    }
    return results


def campaignx_supporter_save_for_api(  # campaignSupporterSave
        campaignx_we_vote_id='',
        campaign_supported=False,
        campaign_supported_changed=False,
        supporter_endorsement='',
        supporter_endorsement_changed=False,
        visible_to_public=False,
        visible_to_public_changed=False,
        voter_device_id=''):
    status = ''
    success = True
    voter_signed_in_with_email = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    if positive_value_exists(campaign_supported):
        # To support a campaign, voter must be signed in with an email address
        if not voter.signed_in_with_email():
            status += "MUST_BE_SIGNED_IN_WITH_EMAIL "
            results = {
                'status':                       status,
                'success':                      False,
                'campaignx_we_vote_id':         '',
                'date_last_changed':            '',
                'date_supported':               '',
                'organization_we_vote_id':      '',
                'supporter_endorsement':        '',
                'supporter_name':               '',
                'visible_to_public':            True,
                'voter_we_vote_id':             '',
                'voter_signed_in_with_email':   voter_signed_in_with_email,
                'we_vote_hosted_profile_photo_image_url_tiny': '',
            }
            return results

    if not positive_value_exists(campaignx_we_vote_id):
        status += "CAMPAIGNX_WE_VOTE_ID_REQUIRED "
        results = {
            'status':                       status,
            'success':                      False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    campaignx_manager = CampaignXManager()
    update_values = {
        'campaign_supported':               campaign_supported,
        'campaign_supported_changed':       campaign_supported_changed,
        'supporter_endorsement':            supporter_endorsement,
        'supporter_endorsement_changed':    supporter_endorsement_changed,
        'visible_to_public':                visible_to_public,
        'visible_to_public_changed':        visible_to_public_changed,
    }
    create_results = campaignx_manager.update_or_create_campaignx_supporter(
        campaignx_we_vote_id=campaignx_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        organization_we_vote_id=linked_organization_we_vote_id,
        update_values=update_values,
    )

    status += create_results['status']
    if create_results['campaignx_supporter_found']:
        if positive_value_exists(campaign_supported_changed):
            count_results = campaignx_manager.update_campaignx_supporters_count(campaignx_we_vote_id)
            if not count_results['success']:
                status += count_results['status']

        campaignx_supporter = create_results['campaignx_supporter']
        date_last_changed_string = ''
        date_supported_string = ''
        try:
            date_last_changed_string = campaignx_supporter.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
            date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            status += "DATE_CONVERSION_ERROR: " + str(e) + " "
        results = {
            'status':                       status,
            'success':                      success,
            'campaignx_we_vote_id':         campaignx_supporter.campaignx_we_vote_id,
            'date_last_changed':            date_last_changed_string,
            'date_supported':               date_supported_string,
            'organization_we_vote_id':      campaignx_supporter.organization_we_vote_id,
            'supporter_endorsement':        campaignx_supporter.supporter_endorsement,
            'supporter_name':               campaignx_supporter.supporter_name,
            'visible_to_public':            campaignx_supporter.visible_to_public,
            'voter_we_vote_id':             campaignx_supporter.voter_we_vote_id,
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
        }
        return results
    else:
        status += "CAMPAIGNX_SUPPORTER_SAVE_ERROR "
        results = {
            'status':                       status,
            'success':                      False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results


def move_campaignx_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, from_organization_we_vote_id, to_organization_we_vote_id,
        to_organization_name=None):
    status = ''
    success = True
    campaignx_entries_moved = 0
    campaignx_owner_entries_moved = 0
    campaignx_supporter_entries_moved = 0

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
    # Move owners based on voter_we_vote_id
    try:
        campaignx_owner_entries_moved += CampaignXOwner.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "

    # ######################
    # Move supporters based on voter_we_vote_id
    try:
        campaignx_supporter_entries_moved += CampaignXSupporter.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "

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
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(supporter_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
    else:
        try:
            campaignx_owner_entries_moved += CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'campaignx_entries_moved':          campaignx_owner_entries_moved,
        'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
    }
    return results
