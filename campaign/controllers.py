# campaign/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CampaignX, CampaignXListedByOrganization, CampaignXManager, CampaignXNewsItem, CampaignXOwner, \
    CampaignXPolitician, CampaignXSupporter, CAMPAIGNX_UNIQUE_ATTRIBUTES_TO_BE_CLEARED, CAMPAIGNX_UNIQUE_IDENTIFIERS, \
    FINAL_ELECTION_DATE_COOL_DOWN
import base64
import copy
from datetime import datetime, timedelta
from django.contrib import messages
from django.db.models import Q
from image.controllers import cache_image_object_to_aws, create_resized_images
import json
from io import BytesIO
from PIL import Image, ImageOps
import re
from activity.controllers import update_or_create_activity_notice_seed_for_campaignx_supporter_initial_response
from candidate.models import CandidateCampaign
from position.models import OPPOSE, SUPPORT
import pytz
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_date_to_date_as_integer, generate_date_as_integer, positive_value_exists

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

CAMPAIGNX_ERROR_DICT = {
    'status': 'ERROR ',
    'success': False,
    'campaign_description': '',
    'campaign_title': '',
    'campaignx_news_item_list': [],
    'campaignx_owner_list': [],
    'campaignx_politician_list': [],
    'campaignx_politician_list_exists': False,
    'campaignx_politician_starter_list': [],
    'campaignx_we_vote_id': '',
    'final_election_date_as_integer': None,
    'final_election_date_in_past': False,
    'in_draft_mode': True,
    'is_blocked_by_we_vote': False,
    'is_blocked_by_we_vote_reason': '',
    'is_supporters_count_minimum_exceeded': False,
    'latest_campaignx_supporter_endorsement_list': [],
    'latest_campaignx_supporter_list': [],
    'linked_politician_we_vote_id': '',
    'order_in_list': 0,
    'seo_friendly_path': '',
    'seo_friendly_path_list': [],
    'supporters_count': 0,
    'supporters_count_next_goal': 0,
    'supporters_count_victory_goal': 0,
    'visible_on_this_site': False,
    'voter_campaignx_supporter': {},
    'voter_can_send_updates_to_campaignx': False,
    'voter_can_vote_for_politician_we_vote_ids': [],
    'voter_is_campaignx_owner': False,
    'voter_signed_in_with_email': False,
    'we_vote_hosted_campaign_photo_large_url': '',
    'we_vote_hosted_campaign_photo_medium_url': '',
    'we_vote_hosted_campaign_photo_small_url': '',
}


def campaignx_list_retrieve_for_api(  # campaignListRetrieve
        hostname='',
        limit_to_this_state_code='',
        recommended_campaigns_for_campaignx_we_vote_id='',
        request=None,
        search_text='',
        voter_device_id=''):
    """

    :param hostname:
    :param limit_to_this_state_code:
    :param recommended_campaigns_for_campaignx_we_vote_id:
    :param request:
    :param search_text:
    :param voter_device_id:
    :return:
    """
    campaignx_dict_list = []
    status = ""
    promoted_campaignx_list_returned = True
    voter_can_vote_for_politicians_list_returned = True
    voter_owned_campaignx_list_returned = True
    voter_started_campaignx_list_returned = True
    voter_supported_campaignx_list_returned = True

    if positive_value_exists(recommended_campaigns_for_campaignx_we_vote_id) or positive_value_exists(search_text):
        # Do not retrieve certain data if returning recommended campaigns
        promoted_campaignx_list_returned = False
        voter_can_vote_for_politicians_list_returned = False
        voter_owned_campaignx_list_returned = False
        voter_started_campaignx_list_returned = False
        voter_supported_campaignx_list_returned = False

    promoted_campaignx_we_vote_ids = []
    voter_can_send_updates_campaignx_we_vote_ids = []
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
        return json_data
    voter = voter_results['voter']
    voter_signed_in_with_email = voter.signed_in_with_email()
    voter_we_vote_id = voter.we_vote_id

    from organization.controllers import site_configuration_retrieve_for_api
    results = site_configuration_retrieve_for_api(hostname)
    site_owner_organization_we_vote_id = results['organization_we_vote_id']

    voter_can_vote_for_politician_we_vote_ids = []
    # TODO: Creates excessive slow-down. We need a more optimized solution.
    # if voter_can_vote_for_politicians_list_returned:
    #     # We need to know all the politicians this voter can vote for so we can figure out
    #     #  if the voter can vote for any politicians in the election
    #     from ballot.controllers import what_voter_can_vote_for
    #     results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
    #     voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']

    visible_on_this_site_campaignx_we_vote_id_list = []
    campaignx_manager = CampaignXManager()
    if positive_value_exists(recommended_campaigns_for_campaignx_we_vote_id):
        results = retrieve_recommended_campaignx_list_for_campaignx_we_vote_id(
            request=request,
            voter_device_id=voter_device_id,
            voter_we_vote_id=voter_we_vote_id,
            campaignx_we_vote_id=recommended_campaigns_for_campaignx_we_vote_id,
            site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
    else:
        if positive_value_exists(site_owner_organization_we_vote_id):
            results = campaignx_manager.retrieve_campaignx_list_for_private_label(
                including_started_by_voter_we_vote_id=voter_we_vote_id,
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            visible_on_this_site_campaignx_we_vote_id_list = results['visible_on_this_site_campaignx_we_vote_id_list']
        else:
            results = campaignx_manager.retrieve_campaignx_list(
                including_started_by_voter_we_vote_id=voter_we_vote_id,
                limit_to_this_state_code=limit_to_this_state_code,
                search_text=search_text)
    success = results['success']
    status += results['status']
    campaignx_list = results['campaignx_list']
    campaignx_list_found = results['campaignx_list_found']

    if success:
        results = generate_campaignx_dict_list_from_campaignx_object_list(
            campaignx_object_list=campaignx_list,
            hostname=hostname,
            promoted_campaignx_we_vote_ids=promoted_campaignx_we_vote_ids,
            site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
            visible_on_this_site_campaignx_we_vote_id_list=visible_on_this_site_campaignx_we_vote_id_list,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )
        campaignx_dict_list = results['campaignx_dict_list']
        status += results['status']
        if not results['success']:
            success = False

    if success and voter_started_campaignx_list_returned:
        results = campaignx_manager.retrieve_campaignx_we_vote_id_list_started_by_voter(
            started_by_voter_we_vote_id=voter_we_vote_id)
        if not results['success']:
            voter_started_campaignx_list_returned = False
        else:
            voter_started_campaignx_we_vote_ids = results['campaignx_we_vote_id_list']

    if success and voter_supported_campaignx_list_returned:
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
        'campaignx_list':                           campaignx_dict_list,
        'campaignx_list_found':                     campaignx_list_found,
    }
    if promoted_campaignx_list_returned:
        json_data['promoted_campaignx_list_returned'] = True
        json_data['promoted_campaignx_we_vote_ids'] = promoted_campaignx_we_vote_ids
    if positive_value_exists(recommended_campaigns_for_campaignx_we_vote_id):
        json_data['recommended_campaigns_for_campaignx_we_vote_id'] = recommended_campaigns_for_campaignx_we_vote_id
    if voter_can_vote_for_politicians_list_returned:
        json_data['voter_can_vote_for_politicians_list_returned'] = True
        json_data['voter_can_vote_for_politician_we_vote_ids'] = voter_can_vote_for_politician_we_vote_ids
    if voter_owned_campaignx_list_returned:
        json_data['voter_owned_campaignx_list_returned'] = True
        json_data['voter_owned_campaignx_we_vote_ids'] = voter_owned_campaignx_we_vote_ids
        json_data['voter_can_send_updates_campaignx_we_vote_ids'] = voter_can_send_updates_campaignx_we_vote_ids
    if voter_started_campaignx_list_returned:
        json_data['voter_started_campaignx_list_returned'] = True
        json_data['voter_started_campaignx_we_vote_ids'] = voter_started_campaignx_we_vote_ids
    if voter_supported_campaignx_list_returned:
        json_data['voter_supported_campaignx_list_returned'] = True
        json_data['voter_supported_campaignx_we_vote_ids'] = voter_supported_campaignx_we_vote_ids
    return json_data


def campaignx_news_item_save_for_api(  # campaignNewsItemSave
        campaign_news_subject='',
        campaign_news_subject_changed=False,
        campaign_news_text='',
        campaign_news_text_changed=False,
        campaignx_news_item_we_vote_id='',
        campaignx_we_vote_id='',
        in_draft_mode=False,
        in_draft_mode_changed=False,
        send_now=False,
        visible_to_public=False,
        visible_to_public_changed=False,
        voter_device_id=''):
    status = ''
    success = True

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = {
            'status':                           status,
            'success':                          False,
            'campaign_news_subject':            '',
            'campaign_news_text':               '',
            'campaignx_news_item_we_vote_id':   '',
            'campaignx_we_vote_id':             '',
            'date_last_changed':                '',
            'date_posted':                      '',
            'date_sent_to_email':               '',
            'in_draft_mode':                    True,
            'organization_we_vote_id':          '',
            'speaker_name':                     '',
            'visible_to_public':                True,
            'voter_we_vote_id':                 '',
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    if not positive_value_exists(campaignx_we_vote_id):
        status += "CAMPAIGNX_WE_VOTE_ID_REQUIRED "
        results = {
            'status':                           status,
            'success':                          False,
            'campaign_news_subject':            '',
            'campaign_news_text':               '',
            'campaignx_news_item_we_vote_id':   '',
            'campaignx_we_vote_id':             '',
            'date_last_changed':                '',
            'date_posted':                      '',
            'date_sent_to_email':               '',
            'in_draft_mode':                    True,
            'organization_we_vote_id':          '',
            'speaker_name':                     '',
            'visible_to_public':                True,
            'voter_we_vote_id':                 '',
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    campaignx_manager = CampaignXManager()
    voter_is_campaignx_owner = campaignx_manager.is_voter_campaignx_owner(
        campaignx_we_vote_id=campaignx_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )
    if not positive_value_exists(voter_is_campaignx_owner):
        status += "VOTER_DOES_NOT_HAVE_RIGHT_TO_CREATE_NEWS_ITEM "
        results = {
            'status':                           status,
            'success':                          False,
            'campaign_news_subject':            '',
            'campaign_news_text':               '',
            'campaignx_news_item_we_vote_id':   '',
            'campaignx_we_vote_id':             '',
            'date_last_changed':                '',
            'date_posted':                      '',
            'date_sent_to_email':               '',
            'in_draft_mode':                    True,
            'organization_we_vote_id':          '',
            'speaker_name':                     '',
            'visible_to_public':                True,
            'voter_we_vote_id':                 '',
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results

    update_values = {
        'campaign_news_subject':            campaign_news_subject,
        'campaign_news_subject_changed':    campaign_news_subject_changed,
        'campaign_news_text':               campaign_news_text,
        'campaign_news_text_changed':       campaign_news_text_changed,
        'in_draft_mode':                    in_draft_mode,
        'in_draft_mode_changed':            in_draft_mode_changed,
        'visible_to_public':                visible_to_public,
        'visible_to_public_changed':        visible_to_public_changed,
    }
    create_results = campaignx_manager.update_or_create_campaignx_news_item(
        campaignx_news_item_we_vote_id=campaignx_news_item_we_vote_id,
        campaignx_we_vote_id=campaignx_we_vote_id,
        organization_we_vote_id=linked_organization_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        update_values=update_values,
    )

    status += create_results['status']
    campaignx_news_item = None
    campaignx_news_item_found = False
    date_sent_to_email_found = False
    if create_results['campaignx_news_item_found']:
        campaignx_news_item = create_results['campaignx_news_item']
        date_sent_to_email_found = positive_value_exists(campaignx_news_item.date_sent_to_email)
        campaignx_news_item_found = True

    send_campaignx_news_item = positive_value_exists(send_now)
    if campaignx_news_item_found:
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            read_only=True,
        )
        if results['campaignx_found']:
            campaignx = results['campaignx']

            from activity.controllers import update_or_create_activity_notice_seed_for_campaignx_news_item
            activity_results = update_or_create_activity_notice_seed_for_campaignx_news_item(
                campaignx_news_item_we_vote_id=campaignx_news_item.we_vote_id,
                campaignx_we_vote_id=campaignx.we_vote_id,
                send_campaignx_news_item=send_campaignx_news_item,
                speaker_name=campaignx_news_item.speaker_name,
                speaker_organization_we_vote_id=campaignx_news_item.organization_we_vote_id,
                speaker_voter_we_vote_id=campaignx_news_item.voter_we_vote_id,
                speaker_profile_image_url_medium=campaignx_news_item.we_vote_hosted_profile_image_url_medium,
                speaker_profile_image_url_tiny=campaignx_news_item.we_vote_hosted_profile_image_url_tiny,
                statement_subject=campaignx_news_item.campaign_news_subject,
                statement_text=campaignx_news_item.campaign_news_text)
            status += activity_results['status']
            if activity_results['success'] and send_campaignx_news_item and not date_sent_to_email_found:
                if activity_results['activity_notice_seed_found']:
                    activity_notice_seed = activity_results['activity_notice_seed']
                    campaignx_news_item.date_sent_to_email = activity_notice_seed.date_sent_to_email
                    campaignx_news_item.save()

    if campaignx_news_item_found:
        date_last_changed_string = ''
        date_posted_string = ''
        date_sent_to_email_string = ''
        try:
            date_last_changed_string = campaignx_news_item.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
            date_posted_string = campaignx_news_item.date_posted.strftime('%Y-%m-%d %H:%M:%S')
            date_sent_to_email_string = campaignx_news_item.date_posted.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            status += "DATE_CONVERSION_ERROR: " + str(e) + " "
        results = {
            'status':                       status,
            'success':                      success,
            'campaign_news_subject':        campaignx_news_item.campaign_news_subject,
            'campaign_news_text':           campaignx_news_item.campaign_news_text,
            'campaignx_news_item_we_vote_id': campaignx_news_item.we_vote_id,
            'campaignx_we_vote_id':         campaignx_news_item.campaignx_we_vote_id,
            'date_last_changed':            date_last_changed_string,
            'date_posted':                  date_posted_string,
            'date_sent_to_email':           date_sent_to_email_string,
            'in_draft_mode':                campaignx_news_item.in_draft_mode,
            'organization_we_vote_id':      campaignx_news_item.organization_we_vote_id,
            'speaker_name':                 campaignx_news_item.speaker_name,
            'voter_we_vote_id':             campaignx_news_item.voter_we_vote_id,
            'we_vote_hosted_profile_photo_image_url_medium':
                campaignx_news_item.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_photo_image_url_tiny': campaignx_news_item.we_vote_hosted_profile_image_url_tiny,
        }
        return results
    else:
        status += "CAMPAIGNX_NEWS_ITEM_NOT_FOUND_ERROR "
        results = {
            'status':                           status,
            'success':                          False,
            'campaign_news_subject':            '',
            'campaign_news_text':               '',
            'campaignx_news_item_we_vote_id':   '',
            'campaignx_we_vote_id':             '',
            'date_last_changed':                '',
            'date_posted':                      '',
            'date_sent_to_email':               '',
            'in_draft_mode':                    True,
            'organization_we_vote_id':          '',
            'speaker_name':                     '',
            'visible_to_public':                True,
            'voter_we_vote_id':                 '',
            'we_vote_hosted_profile_photo_image_url_tiny': '',
        }
        return results


def campaignx_retrieve_for_api(  # campaignRetrieve & campaignRetrieveAsOwner (No CDN)
        request=None,
        voter_device_id='',
        campaignx_we_vote_id='',
        seo_friendly_path='',
        as_owner=False,
        hostname=''):
    status = ''
    success = True
    campaignx_dict = {}
    campaignx_error_dict = copy.deepcopy(CAMPAIGNX_ERROR_DICT)
    campaignx_error_dict['seo_friendly_path'] = seo_friendly_path
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
            results = campaignx_error_dict
            results['status'] = status
            return results
        results = campaignx_manager.retrieve_campaignx_as_owner(
            campaignx_we_vote_id=campaignx_we_vote_id,
            seo_friendly_path=seo_friendly_path,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
        voter_is_campaignx_owner = results['viewer_is_owner']
    else:
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            seo_friendly_path=seo_friendly_path,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
        voter_is_campaignx_owner = results['viewer_is_owner']
    status += results['status']
    if not results['success']:
        status += "CAMPAIGNX_RETRIEVE_ERROR "
        results = campaignx_error_dict
        results['status'] = status
        return results
    elif not results['campaignx_found']:
        status += "CAMPAIGNX_NOT_FOUND: "
        status += results['status'] + " "
        results = campaignx_error_dict
        results['status'] = status
        results['success'] = True
        return results

    campaignx = results['campaignx']
    campaignx_owner_list = results['campaignx_owner_list']
    seo_friendly_path_list = results['seo_friendly_path_list']

    if hasattr(campaignx, 'we_vote_id'):
        # We need to know all the politicians this voter can vote for, so we can figure out
        #  if the voter can vote for any politicians in the election
        # May 6, 2023: TURNED OFF BECAUSE TOO TIME CONSUMING FOR NOW. Perhaps pre-calculate?
        # from ballot.controllers import what_voter_can_vote_for
        # results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        # voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']
        voter_can_vote_for_politician_we_vote_ids = []

        generate_results = generate_campaignx_dict_from_campaignx_object(
            campaignx=campaignx,
            campaignx_owner_list=campaignx_owner_list,
            hostname=hostname,
            seo_friendly_path_list=seo_friendly_path_list,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_is_campaignx_owner=voter_is_campaignx_owner,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )
        campaignx_dict = generate_results['campaignx_dict']
        status += generate_results['status']
        if not generate_results['success']:
            success = False
    else:
        pass
    if 'campaign_description' in campaignx_dict:
        results = campaignx_dict
    else:
        results = campaignx_error_dict

    results['status'] = status
    results['success'] = success
    return results


def campaignx_save_for_api(  # campaignSave & campaignStartSave
        campaign_description='',
        campaign_description_changed=False,
        in_draft_mode=False,
        in_draft_mode_changed=False,
        campaign_photo_from_file_reader='',
        campaign_photo_changed=False,
        campaign_photo_delete=False,
        campaign_photo_delete_changed=False,
        campaign_title='',
        campaign_title_changed=False,
        campaignx_we_vote_id='',
        hostname='',
        politician_delete_list_serialized='',
        politician_starter_list_serialized='',
        politician_starter_list_changed=False,
        request=None,
        voter_device_id=''):
    status = ''
    success = True
    campaignx_error_dict = copy.deepcopy(CAMPAIGNX_ERROR_DICT)

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = campaignx_error_dict
        results['status'] = status
        return results

    if positive_value_exists(in_draft_mode_changed) and not positive_value_exists(in_draft_mode):
        # Make sure organization object has necessary images needed for CampaignXOwner and CampaignXSupporter
        from organization.models import OrganizationManager
        organization_manager = OrganizationManager()
        organization_results = \
            organization_manager.retrieve_organization_from_we_vote_id(linked_organization_we_vote_id)
        organization_changed = False
        if organization_results['organization_found']:
            try:
                organization = organization_results['organization']
                if not positive_value_exists(organization.we_vote_hosted_profile_image_url_tiny) and \
                        positive_value_exists(voter.we_vote_hosted_profile_image_url_tiny):
                    organization.we_vote_hosted_profile_image_url_tiny = voter.we_vote_hosted_profile_image_url_tiny
                    organization_changed = True
                if not positive_value_exists(organization.we_vote_hosted_profile_image_url_medium) and \
                        positive_value_exists(voter.we_vote_hosted_profile_image_url_medium):
                    organization.we_vote_hosted_profile_image_url_medium = voter.we_vote_hosted_profile_image_url_medium
                    organization_changed = True
                if not positive_value_exists(organization.we_vote_hosted_profile_image_url_large) and \
                        positive_value_exists(voter.we_vote_hosted_profile_image_url_large):
                    organization.we_vote_hosted_profile_image_url_large = voter.we_vote_hosted_profile_image_url_large
                    organization_changed = True
                if organization_changed:
                    organization.save()
            except Exception as e:
                status += "COULD_NOT_UPDATE_ORGANIZATION_FROM_VOTER: " + str(e) + " "

        # To publish a campaign, voter must be signed in with an email address
        if not voter.signed_in_with_email():
            status += "MUST_BE_SIGNED_IN_WITH_EMAIL_TO_PUBLISH "
            results = campaignx_error_dict
            results['status'] = status
            return results

    campaignx_manager = CampaignXManager()
    viewer_is_owner = False
    if positive_value_exists(campaignx_we_vote_id):
        viewer_is_owner = campaignx_manager.is_voter_campaignx_owner(
            campaignx_we_vote_id=campaignx_we_vote_id, voter_we_vote_id=voter_we_vote_id)
        if not positive_value_exists(viewer_is_owner):
            status += "VOTER_IS_NOT_OWNER_OF_CAMPAIGNX "
            results = campaignx_error_dict
            results['status'] = status
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
            'campaign_description':                 campaign_description,
            'campaign_description_changed':         campaign_description_changed,
            'in_draft_mode':                        in_draft_mode,
            'in_draft_mode_changed':                in_draft_mode_changed,
            'campaign_photo_changed':               campaign_photo_changed,
            'campaign_photo_delete':                campaign_photo_delete,
            'campaign_photo_delete_changed':        campaign_photo_delete_changed,
            'campaign_title':                       campaign_title,
            'campaign_title_changed':               campaign_title_changed,
            'politician_delete_list_serialized':    politician_delete_list_serialized,
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
            'campaign_description':                 campaign_description,
            'campaign_description_changed':         campaign_description_changed,
            'in_draft_mode':                        in_draft_mode,
            'in_draft_mode_changed':                in_draft_mode_changed,
            'campaign_photo_delete':                campaign_photo_delete,
            'campaign_photo_delete_changed':        campaign_photo_delete_changed,
            'campaign_title':                       campaign_title,
            'campaign_title_changed':               campaign_title_changed,
            'politician_delete_list_serialized':    politician_delete_list_serialized,
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
        voter_is_campaignx_owner = results['viewer_is_owner']

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

        # We need to know all the politicians this voter can vote for so we can figure out
        #  if the voter can vote for any politicians in the election
        from ballot.controllers import what_voter_can_vote_for
        results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']

        generate_results = generate_campaignx_dict_from_campaignx_object(
            campaignx=campaignx,
            campaignx_owner_list=campaignx_owner_list,
            hostname=hostname,
            seo_friendly_path_list=seo_friendly_path_list,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_is_campaignx_owner=voter_is_campaignx_owner,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )

        campaignx_dict = generate_results['campaignx_dict']
        status += generate_results['status']
        if not generate_results['success']:
            success = False
        if 'campaignx_description' not in campaignx_dict:
            success = False
        if success:
            results = campaignx_dict
        else:
            results = campaignx_error_dict
        return results
    else:
        status += "CAMPAIGNX_SAVE_ERROR "
        results = campaignx_error_dict
        results['status'] = status
        return results


def campaignx_save_photo_from_file_reader(
        campaignx_we_vote_id='',
        campaignx_photo_binary_file=None,
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

    if not positive_value_exists(campaign_photo_from_file_reader) \
            and not positive_value_exists(campaignx_photo_binary_file):
        status += "MISSING_CAMPAIGNX_PHOTO_FROM_FILE_READER "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_campaign_photo_original_url': we_vote_hosted_campaign_photo_original_url,
        }
        return results

    if not campaignx_photo_binary_file:
        try:
            img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                                campaign_photo_from_file_reader).groupdict()
            if img_dict['encoding'] == 'base64':
                campaignx_photo_binary_file = img_dict['data']
            else:
                status += "INCOMING_CAMPAIGN_PHOTO_LARGE-BASE64_NOT_FOUND "
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_BINARY_DATA_FROM_INCOMING_CAMPAIGNX_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if campaignx_photo_binary_file:
        try:
            byte_data = base64.b64decode(campaignx_photo_binary_file)
            image_data = BytesIO(byte_data)
            original_image = Image.open(image_data)
            format_to_cache = original_image.format
            python_image_library_image = ImageOps.exif_transpose(original_image)
            python_image_library_image.thumbnail(
                (CAMPAIGN_PHOTO_ORIGINAL_MAX_WIDTH, CAMPAIGN_PHOTO_ORIGINAL_MAX_HEIGHT), Image.Resampling.LANCZOS)
            python_image_library_image.format = format_to_cache
            image_data_found = True
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_CAMPAIGN_PHOTO_FROM_BINARY_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if image_data_found:
        cache_results = cache_image_object_to_aws(
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
            'campaign_supported':           False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_medium': '',
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
            'campaign_supported':           False,
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
            'campaign_supported':           False,
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
        'campaign_supported':           campaignx_supporter.campaign_supported,
        'campaignx_we_vote_id':         campaignx_supporter.campaignx_we_vote_id,
        'date_last_changed':            date_last_changed_string,
        'date_supported':               date_supported_string,
        'organization_we_vote_id':      campaignx_supporter.organization_we_vote_id,
        'supporter_endorsement':        campaignx_supporter.supporter_endorsement,
        'supporter_name':               campaignx_supporter.supporter_name,
        'visible_to_public':            campaignx_supporter.visible_to_public,
        'voter_we_vote_id':             campaignx_supporter.voter_we_vote_id,
        'voter_signed_in_with_email':   voter_signed_in_with_email,
        'we_vote_hosted_profile_photo_image_url_medium': campaignx_supporter.we_vote_hosted_profile_image_url_medium,
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

    error_results = {
        'status': status,
        'success': False,
        'campaign_supported': False,
        'campaignx_we_vote_id': '',
        'date_last_changed': '',
        'date_supported': '',
        'id': '',
        'organization_we_vote_id': '',
        'supporter_endorsement': '',
        'supporter_name': '',
        'visible_to_public': True,
        'voter_we_vote_id': '',
        'voter_signed_in_with_email': voter_signed_in_with_email,
        'we_vote_hosted_profile_photo_image_url_tiny': '',
    }

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = error_results
        results['status'] = status
        return results

    if positive_value_exists(campaign_supported):
        # To support a campaign, voter should be signed in with an email address, but let pass anyway
        if not voter.signed_in_with_email():
            status += "SUPPORTER_NOT_SIGNED_IN_WITH_EMAIL "

    if not positive_value_exists(campaignx_we_vote_id):
        status += "CAMPAIGNX_WE_VOTE_ID_REQUIRED "
        results = error_results
        results['status'] = status
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

    if create_results['campaignx_supporter_found']:
        campaignx_supporter = create_results['campaignx_supporter']

        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            read_only=True,
        )
        notice_seed_statement_text = ''
        if results['campaignx_found']:
            campaignx = results['campaignx']
            notice_seed_statement_text = campaignx.campaign_title

            # If this campaignx is hard-linked to a politician, check to see if we have an existing Position entry
            if positive_value_exists(campaignx.linked_politician_we_vote_id) \
                    and positive_value_exists(voter_we_vote_id):
                from position.models import PositionManager
                position = None
                position_found = False
                position_manager = PositionManager()
                results = position_manager.retrieve_position_table_unknown(
                    politician_we_vote_id=campaignx.linked_politician_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
                if results['position_found']:
                    position = results['position']
                    try:
                        position.stance = SUPPORT
                        position.save()
                    except Exception as e:
                        status += "SAVE_STANCE_TO_SUPPORT_ERROR: " + str(e) + ""
                    position_found = True
                    if positive_value_exists(visible_to_public_changed):
                        is_friends_only_position = position.is_friends_only_position()
                        is_public_position = position.is_public_position()
                        if visible_to_public and is_friends_only_position:
                            visibility_needs_to_change = True
                        elif not visible_to_public and is_public_position:
                            visibility_needs_to_change = True
                        else:
                            visibility_needs_to_change = False
                        if visibility_needs_to_change:
                            results = position_manager.switch_position_visibility(
                                position, visible_to_public)
                            if results['success']:
                                position = results['position']
                elif results['success']:
                    # If not found, create new Position
                    results = position_manager.update_or_create_position(
                        organization_we_vote_id=linked_organization_we_vote_id,
                        politician_we_vote_id=campaignx.linked_politician_we_vote_id,
                        set_as_public_position=campaignx_supporter.visible_to_public,
                        stance=SUPPORT,
                        voter_we_vote_id=voter_we_vote_id,
                    )
                    position = results['position']
                    if results['success']:
                        position_found = True

                if position_found:
                    campaignx_supporter_supporter_endorsement_updated = False
                    try:
                        if positive_value_exists(position.we_vote_id):
                            campaignx_supporter.linked_position_we_vote_id = position.we_vote_id
                        if positive_value_exists(position.statement_text) \
                                and campaignx_supporter.supporter_endorsement is None:
                            campaignx_supporter.supporter_endorsement = position.statement_text
                            campaignx_supporter_supporter_endorsement_updated = True
                        campaignx_supporter.save()
                    except Exception as e:
                        status += "CAMPAIGNX_SUPPORTER_SAVE_ERROR: " + str(e) + " "
                    try:
                        position.campaignx_supporter_created = True
                        position.stance = SUPPORT
                        if positive_value_exists(campaignx_supporter.supporter_endorsement) \
                                and not campaignx_supporter_supporter_endorsement_updated:
                            position.statement_text = campaignx_supporter.supporter_endorsement
                        position.save()
                    except Exception as e:
                        status += "POSITION_SUPPORTER_ENDORSEMENT_SAVE_ERROR: " + str(e) + " "

        activity_results = update_or_create_activity_notice_seed_for_campaignx_supporter_initial_response(
            campaignx_we_vote_id=campaignx_supporter.campaignx_we_vote_id,
            visibility_is_public=campaignx_supporter.visible_to_public,
            speaker_name=campaignx_supporter.supporter_name,
            speaker_organization_we_vote_id=campaignx_supporter.organization_we_vote_id,
            speaker_voter_we_vote_id=campaignx_supporter.voter_we_vote_id,
            speaker_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
            speaker_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny,
            statement_text=notice_seed_statement_text)
        status += activity_results['status']

    status += create_results['status']
    if create_results['campaignx_supporter_found']:
        count_results = campaignx_manager.update_campaignx_supporters_count(campaignx_we_vote_id)
        campaignx_we_vote_id_list_to_refresh = [campaignx_we_vote_id]
        results = refresh_campaignx_supporters_count_in_all_children(
            campaignx_we_vote_id_list=campaignx_we_vote_id_list_to_refresh)
        status += results['status']
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
            'we_vote_hosted_profile_photo_image_url_medium':
                campaignx_supporter.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_photo_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
        }
        return results
    else:
        status += "CAMPAIGNX_SUPPORTER_SAVE_ERROR "
        results = error_results
        results['status'] = status
        return results


def create_campaignx_supporter_from_position(
        campaignx_we_vote_id='',
        create_object_in_database=False,
        position=None,
        position_we_vote_id='',
        show_to_public=True,
):
    status = ''
    campaignx_supporter = None
    campaignx_supporter_found = False

    if not positive_value_exists(campaignx_we_vote_id):
        status += "VALID_CAMPAIGNX_WE_VOTE_ID_NOT_FOUND "
        results = {
            'success':                      False,
            'status':                       status,
            'campaignx_supporter':          campaignx_supporter,
            'campaignx_supporter_found':    campaignx_supporter_found,
        }
        return results

    if hasattr(position, 'ballot_item_display_name'):
        pass
    else:
        from position.models import PositionManager
        position_manager = PositionManager()
        results = position_manager.retrieve_position(position_we_vote_id=position_we_vote_id)
        position = None
        position_found = False
        if results['position_found']:
            position = results['position']
            position_found = True
        if not position_found or not hasattr(position, 'ballot_item_display_name'):
            status += "VALID_POSITION_NOT_FOUND "
            results = {
                'campaignx_supporter':        campaignx_supporter,
                'campaignx_supporter_found':  campaignx_supporter_found,
                'status':                       status,
                'success': False,
            }
            return results

    # Make sure that the position.stance shows support
    if position.stance != SUPPORT:
        status += "VALID_POSITION_NOT_FOUND "
        results = {
            'success': False,
            'status': status,
            'campaignx_supporter': campaignx_supporter,
            'campaignx_supporter_found': campaignx_supporter_found,
        }
        return results

    campaignx_supporter_created = False
    try:
        campaignx_supporter = CampaignXSupporter(
            campaign_supported=True,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_supported=position.date_entered,
            linked_position_we_vote_id=position.we_vote_id,
            organization_we_vote_id=position.organization_we_vote_id,
            supporter_name=position.speaker_display_name,
            supporter_endorsement=position.statement_text,
            # visibility_blocked_by_we_vote=False,
            visible_to_public=show_to_public,
            voter_we_vote_id=position.voter_we_vote_id,
            we_vote_hosted_profile_image_url_medium=position.speaker_image_url_https_medium,
            we_vote_hosted_profile_image_url_tiny=position.speaker_image_url_https_tiny,
        )
        # Phone
        # if positive_value_exists(position.politician_phone_number):
        #     campaignx_supporter.campaignx_supporter_phone = position.politician_phone_number
        if positive_value_exists(create_object_in_database):
            campaignx_supporter.save()
            campaignx_supporter_created = True
        else:
            campaignx_supporter_found = True
        if campaignx_supporter_created:
            success = True
            status += "CAMPAIGNX_SUPPORTER_CREATED "
        elif campaignx_supporter_found:
            success = True
            status += "CAMPAIGNX_SUPPORTER_BUILT_BUT_NOT_SAVED "
        else:
            success = False
            status += "CAMPAIGNX_SUPPORTER_NOT_CREATED "
    except Exception as e:
        status += 'FAILED_TO_CREATE_CAMPAIGNX_SUPPORTER ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    results = {
        'campaignx_supporter_created':  campaignx_supporter_created,
        'campaignx_supporter_found':    campaignx_supporter_found,
        'campaignx_supporter':          campaignx_supporter,
        'status':                       status,
        'success':                      success,
    }
    return results


def create_campaignx_supporters_from_positions(
        request,
        friends_only_positions=False,
        politician_we_vote_id_list=[],
        state_code=''):
    # Create default variables needed below
    campaignx_supporter_bulk_create_list = []
    campaignx_supporter_entry_create_needed = False
    campaignx_supporter_entries_created = 0
    campaignx_supporter_entries_not_created = 0
    campaignx_we_vote_id_list_to_refresh = []
    # key: politician_we_vote_id, value: linked_campaignx_we_vote_id
    linked_campaignx_we_vote_id_by_politician_we_vote_id_dict = {}
    number_to_create = 1000
    from politician.models import Politician
    from position.models import PositionEntered, PositionForFriends
    position_objects_to_mark_as_having_campaignx_supporter_created = []
    position_updates_made = 0
    position_updates_needed = False
    position_we_vote_id_list_to_create = []
    status = ''
    success = True
    timezone = pytz.timezone("America/Los_Angeles")
    datetime_now = timezone.localize(datetime.now())
    date_today_as_integer = convert_date_to_date_as_integer(datetime_now)
    voter_we_vote_id_list = []  # Must be signed in to create a campaignx_supporter entry from friends_only_positions

    if positive_value_exists(friends_only_positions):
        position_query = PositionForFriends.objects.all()  # Cannot be readonly, since we bulk_update at the end
    else:
        position_query = PositionEntered.objects.all()  # Cannot be readonly, since we bulk_update at the end
    position_query = position_query.exclude(campaignx_supporter_created=True)
    position_query = position_query.filter(stance=SUPPORT)
    position_query = position_query.filter(
        Q(position_ultimate_election_not_linked=True) |
        Q(position_ultimate_election_date__gte=date_today_as_integer)
    )
    if positive_value_exists(len(politician_we_vote_id_list) > 0):
        position_query = position_query.filter(politician_we_vote_id__in=politician_we_vote_id_list)
    elif positive_value_exists(state_code):
        position_query = position_query.filter(state_code__iexact=state_code)
    total_to_convert = position_query.count()
    position_list_to_copy = list(position_query[:number_to_create])

    # Check CampaignXSupporter table to see if any of these positions already have a CampaignXSupporter entry
    #  if so, don't try to add a duplicate.
    for one_position in position_list_to_copy:
        voter_we_vote_id_list.append(one_position.voter_we_vote_id)

    # Retrieve all relevant voters associated with positions in a single query, so we can access voter.is_signed_in
    #  for friends_only_positions, we want to only create a campaignx_supporter entry if the voter is signed in
    voter_is_signed_in_by_voter_we_vote_id_dict = {}
    if positive_value_exists(friends_only_positions) and len(voter_we_vote_id_list) > 0:
        # from voter.models import Voter
        voter_query = Voter.objects.using('readonly').all()
        voter_query = voter_query.filter(we_vote_id__in=voter_we_vote_id_list)
        voter_list = list(voter_query)
        for one_voter in voter_list:
            voter_is_signed_in_by_voter_we_vote_id_dict[one_voter.we_vote_id] = one_voter.is_signed_in()
        position_list_modified = []
        for one_position in position_list_to_copy:
            if positive_value_exists(one_position.voter_we_vote_id) and \
                    one_position.voter_we_vote_id in voter_is_signed_in_by_voter_we_vote_id_dict:
                if voter_is_signed_in_by_voter_we_vote_id_dict[one_position.voter_we_vote_id]:
                    position_list_modified.append(one_position)
                else:
                    total_to_convert -= 1
            else:
                total_to_convert -= 1
        position_list_to_copy = position_list_modified

    for one_position in position_list_to_copy:
        if one_position.politician_we_vote_id not in politician_we_vote_id_list:
            politician_we_vote_id_list.append(one_position.politician_we_vote_id)  # Needed to get campaignx_we_vote_id
        position_we_vote_id_list_to_create.append(one_position.we_vote_id)

    # Retrieve all the related politicians in a single query, so we can access the linked_campaignx_we_vote_id
    #  when we are cycling through the positions
    politician_list = []
    if len(politician_we_vote_id_list) > 0:
        politician_query = Politician.objects.using('readonly').all()
        politician_query = politician_query.filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(politician_query)
    for one_politician in politician_list:
        if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
            linked_campaignx_we_vote_id_by_politician_we_vote_id_dict[one_politician.we_vote_id] = \
                one_politician.linked_campaignx_we_vote_id
            if one_politician.linked_campaignx_we_vote_id not in campaignx_we_vote_id_list_to_refresh:
                campaignx_we_vote_id_list_to_refresh.append(one_politician.linked_campaignx_we_vote_id)

    # Retrieve existing CampaignXSupporter entries that are related to the positions we are trying to copy from,
    #  so we can mark them as already processed in the PositionEntered table.
    if len(position_we_vote_id_list_to_create) > 0:
        queryset = CampaignXSupporter.objects.using('readonly').all()
        queryset = queryset.filter(linked_position_we_vote_id__in=position_we_vote_id_list_to_create)
        campaignx_supporters_already_exist_count = queryset.count()
        if positive_value_exists(campaignx_supporters_already_exist_count):
            queryset = queryset.values_list('linked_position_we_vote_id', flat=True).distinct()
            position_we_vote_ids_to_mark_as_having_campaignx_supporter_created = list(queryset)
            position_list_to_copy_modified = []
            for one_position in position_list_to_copy:
                if one_position.we_vote_id not in position_we_vote_ids_to_mark_as_having_campaignx_supporter_created:
                    position_list_to_copy_modified.append(one_position)
                else:
                    one_position.campaignx_supporter_created = True
                    position_objects_to_mark_as_having_campaignx_supporter_created.append(one_position)
                    position_updates_made += 1
                    position_updates_needed = True
            position_list_to_copy = position_list_to_copy_modified

    for one_position in position_list_to_copy:
        if one_position.stance == SUPPORT:
            if one_position.politician_we_vote_id in linked_campaignx_we_vote_id_by_politician_we_vote_id_dict:
                linked_campaignx_we_vote_id = \
                    linked_campaignx_we_vote_id_by_politician_we_vote_id_dict[one_position.politician_we_vote_id]
                if positive_value_exists(linked_campaignx_we_vote_id):
                    if linked_campaignx_we_vote_id not in campaignx_we_vote_id_list_to_refresh:
                        campaignx_we_vote_id_list_to_refresh.append(linked_campaignx_we_vote_id)
                else:
                    campaignx_supporter_entries_not_created += 1
                    continue
            else:
                campaignx_supporter_entries_not_created += 1
                continue
            show_to_public = not positive_value_exists(friends_only_positions)
            results = create_campaignx_supporter_from_position(
                campaignx_we_vote_id=linked_campaignx_we_vote_id,
                create_object_in_database=False,  # We create in bulk below
                position=one_position,
                show_to_public=show_to_public,
            )
            if results['campaignx_supporter_found']:
                campaignx_supporter = results['campaignx_supporter']
                campaignx_supporter_bulk_create_list.append(campaignx_supporter)
                campaignx_supporter_entry_create_needed = True
                campaignx_supporter_entries_created += 1  # campaignx_supporter_entries_created
                one_position.campaignx_supporter_created = True
                position_objects_to_mark_as_having_campaignx_supporter_created.append(one_position)
                position_updates_made += 1
                position_updates_needed = True
            else:
                campaignx_supporter_entries_not_created += 1
    campaignx_supporter_bulk_update_success = True
    update_message = ''
    if campaignx_supporter_entry_create_needed:
        try:
            CampaignXSupporter.objects.bulk_create(campaignx_supporter_bulk_create_list)
            update_message += "{campaignx_supporter_entries_created:,} CampaignXSupporter entries created, " \
                              "".format(campaignx_supporter_entries_created=campaignx_supporter_entries_created)
        except Exception as e:
            campaignx_supporter_bulk_update_success = False
            messages.add_message(request, messages.ERROR,
                                 "ERROR with CampaignXSupporter.objects.bulk_create: {e}, "
                                 "".format(e=e))
    if position_updates_needed and campaignx_supporter_bulk_update_success:
        try:
            if friends_only_positions:
                PositionForFriends.objects.bulk_update(
                    position_objects_to_mark_as_having_campaignx_supporter_created, ['campaignx_supporter_created'])
            else:
                PositionEntered.objects.bulk_update(
                    position_objects_to_mark_as_having_campaignx_supporter_created, ['campaignx_supporter_created'])
            update_message += \
                "{position_updates_made:,} positions updated with campaignx_supporter_created=True, " \
                "".format(position_updates_made=position_updates_made)
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with PositionEntered.objects.bulk_update: {e}, "
                                 "".format(e=e))

    total_to_convert_after = total_to_convert - number_to_create if total_to_convert > number_to_create else 0
    if positive_value_exists(total_to_convert_after):
        update_message += \
            "{total_to_convert_after:,} positions remaining in 'create CampaignXSupporter' process. " \
            "".format(total_to_convert_after=total_to_convert_after)

    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    results = {
        'campaignx_supporter_entries_created':  campaignx_supporter_entries_created,
        'campaignx_we_vote_id_list_to_refresh': campaignx_we_vote_id_list_to_refresh,
        'status':   status,
        'success':  success,
    }
    return results


def refresh_campaignx_supporters_count_for_campaignx_we_vote_id_list(request, campaignx_we_vote_id_list=[]):
    status = ''
    success = True
    update_message = ''
    campaignx_entries_need_to_be_updated = False
    campaignx_manager = CampaignXManager()
    campaignx_bulk_update_list = []
    campaignx_updates_made = 0
    if len(campaignx_we_vote_id_list) > 0:
        queryset = CampaignX.objects.all()  # Cannot be readonly because of bulk_update below
        queryset = queryset.filter(we_vote_id__in=campaignx_we_vote_id_list)
        campaignx_list = list(queryset)
        for one_campaignx in campaignx_list:
            supporters_count = campaignx_manager.fetch_campaignx_supporter_count(
                campaignx_we_vote_id=one_campaignx.we_vote_id)
            if supporters_count != one_campaignx.supporters_count:
                one_campaignx.supporters_count = supporters_count
                campaignx_bulk_update_list.append(one_campaignx)
                campaignx_entries_need_to_be_updated = True
                campaignx_updates_made += 1
    if campaignx_entries_need_to_be_updated:
        try:
            CampaignX.objects.bulk_update(campaignx_bulk_update_list, ['supporters_count'])
            update_message += \
                "{campaignx_updates_made:,} CampaignX entries updated with fresh supporters_count, " \
                "".format(campaignx_updates_made=campaignx_updates_made)
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with CampaignX.objects.bulk_update: {e}, "
                                 "".format(e=e))

    results = {
        'status':           status,
        'success':          success,
        'update_message':   update_message,
    }
    return results


def refresh_campaignx_supporters_count_in_all_children(request=None, campaignx_we_vote_id_list=[]):
    # Now push updates to campaignx entries out to candidates and politicians linked to the campaignx entries
    status = ''
    success = True
    update_message = ''
    if len(campaignx_we_vote_id_list) > 0:
        from candidate.controllers import update_candidate_details_from_campaignx
        from politician.controllers import update_politician_details_from_campaignx
        from politician.models import Politician
        from representative.controllers import update_representative_details_from_campaignx
        from representative.models import Representative
        timezone = pytz.timezone("America/Los_Angeles")
        datetime_now = timezone.localize(datetime.now())
        date_today_as_integer = convert_date_to_date_as_integer(datetime_now)

        queryset = CampaignX.objects.using('readonly').all()
        queryset = queryset.filter(we_vote_id__in=campaignx_we_vote_id_list)
        campaignx_list = list(queryset)
        # ##############################################################################
        # Update all upcoming candidates linked to CampaignX entries which were updated
        queryset = CandidateCampaign.objects.all()  # Cannot be readonly because of bulk_update below
        queryset = queryset.filter(linked_campaignx_we_vote_id__in=campaignx_we_vote_id_list)
        queryset = queryset.filter(candidate_ultimate_election_date__gte=date_today_as_integer)
        candidate_bulk_update_list = []
        candidate_bulk_updates_made = 0
        candidate_list = list(queryset)
        candidate_dict_by_campaignx_we_vote_id = {}
        for one_candidate in candidate_list:
            if one_candidate.linked_campaignx_we_vote_id not in candidate_dict_by_campaignx_we_vote_id:
                candidate_dict_by_campaignx_we_vote_id[one_candidate.linked_campaignx_we_vote_id] = one_candidate
        for one_campaignx in campaignx_list:
            if one_campaignx.we_vote_id in candidate_dict_by_campaignx_we_vote_id:
                candidate_update_results = update_candidate_details_from_campaignx(
                    candidate=candidate_dict_by_campaignx_we_vote_id[one_campaignx.we_vote_id],
                    campaignx=one_campaignx)
                if candidate_update_results['save_changes']:
                    candidate_bulk_update_list.append(candidate_update_results['candidate'])
                    candidate_bulk_updates_made += 1
        if len(candidate_bulk_update_list) > 0:
            try:
                CandidateCampaign.objects.bulk_update(candidate_bulk_update_list, ['supporters_count'])
                update_message += \
                    "{candidate_bulk_updates_made:,} Candidate entries updated with fresh supporters_count, " \
                    "".format(candidate_bulk_updates_made=candidate_bulk_updates_made)
            except Exception as e:
                status += "ERROR with CandidateCampaign.objects.bulk_update: {e}, ".format(e=e)
                if request:
                    messages.add_message(request, messages.ERROR,
                                         "ERROR with CandidateCampaign.objects.bulk_update: {e}, "
                                         "".format(e=e))
        # ##############################################################################
        # Update all politicians linked to CampaignX entries which were updated
        queryset = Politician.objects.all()  # Cannot be readonly because of bulk_update below
        queryset = queryset.filter(linked_campaignx_we_vote_id__in=campaignx_we_vote_id_list)
        politician_bulk_update_list = []
        politician_bulk_updates_made = 0
        politician_list = list(queryset)
        politician_dict_by_campaignx_we_vote_id = {}
        for one_politician in politician_list:
            if one_politician.linked_campaignx_we_vote_id not in politician_dict_by_campaignx_we_vote_id:
                politician_dict_by_campaignx_we_vote_id[one_politician.linked_campaignx_we_vote_id] = one_politician
        for one_campaignx in campaignx_list:
            if one_campaignx.we_vote_id in politician_dict_by_campaignx_we_vote_id:
                politician_update_results = update_politician_details_from_campaignx(
                    politician=politician_dict_by_campaignx_we_vote_id[one_campaignx.we_vote_id],
                    campaignx=one_campaignx)
                if politician_update_results['save_changes']:
                    politician_bulk_update_list.append(politician_update_results['politician'])
                    politician_bulk_updates_made += 1
        if len(politician_bulk_update_list) > 0:
            try:
                Politician.objects.bulk_update(politician_bulk_update_list, ['supporters_count'])
                update_message += \
                    "{politician_bulk_updates_made:,} Politician entries updated with fresh supporters_count, " \
                    "".format(politician_bulk_updates_made=politician_bulk_updates_made)
            except Exception as e:
                status += "ERROR with Politician.objects.bulk_update: {e}, ".format(e=e)
                if request:
                    messages.add_message(request, messages.ERROR,
                                         "ERROR with Politician.objects.bulk_update: {e}, "
                                         "".format(e=e))
        # ##############################################################################
        # Update all representatives linked to CampaignX entries which were updated
        queryset = Representative.objects.all()  # Cannot be readonly because of bulk_update below
        queryset = queryset.filter(linked_campaignx_we_vote_id__in=campaignx_we_vote_id_list)
        representative_bulk_update_list = []
        representative_bulk_updates_made = 0
        representative_list = list(queryset)
        representative_dict_by_campaignx_we_vote_id = {}
        for one_representative in representative_list:
            if one_representative.linked_campaignx_we_vote_id not in representative_dict_by_campaignx_we_vote_id:
                representative_dict_by_campaignx_we_vote_id[one_representative.linked_campaignx_we_vote_id] = \
                    one_representative
        for one_campaignx in campaignx_list:
            if one_campaignx.we_vote_id in representative_dict_by_campaignx_we_vote_id:
                representative_update_results = update_representative_details_from_campaignx(
                    representative=representative_dict_by_campaignx_we_vote_id[one_campaignx.we_vote_id],
                    campaignx=one_campaignx)
                if representative_update_results['save_changes']:
                    representative_bulk_update_list.append(representative_update_results['representative'])
                    representative_bulk_updates_made += 1
        if len(representative_bulk_update_list) > 0:
            try:
                Representative.objects.bulk_update(representative_bulk_update_list, ['supporters_count'])
                update_message += \
                    "{representative_bulk_updates_made:,} Representative entries updated " \
                    "with fresh supporters_count, " \
                    "".format(representative_bulk_updates_made=representative_bulk_updates_made)
            except Exception as e:
                status += "ERROR with Representative.objects.bulk_update: {e}, ".format(e=e)
                if request:
                    messages.add_message(request, messages.ERROR,
                                         "ERROR with Representative.objects.bulk_update: {e}, "
                                         "".format(e=e))

    results = {
        'status':           status,
        'success':          success,
        'update_message':   update_message,
    }
    return results


def fetch_sentence_string_from_politician_list(politician_list, max_number_of_list_items=200):
    """
    Parallel to politicianListToSentenceString in Campaigns site
    :param politician_list:
    :param max_number_of_list_items:
    :return:
    """
    sentence_string = ''
    if not politician_list or len(politician_list) == 0:
        return sentence_string
    if len(politician_list) == 1:
        sentence_string += ' ' + politician_list[0].politician_name
        return sentence_string
    number_of_politicians_in_list = len(politician_list)
    number_of_politicians_in_list_great_than_max_number_of_list_items = \
        number_of_politicians_in_list > max_number_of_list_items
    if number_of_politicians_in_list_great_than_max_number_of_list_items:
        number_of_politicians_to_show = max_number_of_list_items
    else:
        number_of_politicians_to_show = number_of_politicians_in_list
    politician_number = 0
    for politician in politician_list:
        politician_number += 1
        if politician_number >= number_of_politicians_to_show:
            if number_of_politicians_in_list_great_than_max_number_of_list_items:
                sentence_string += ' and more'
            else:
                sentence_string += ' and ' + politician.politician_name
        else:
            comma_or_not = '' if politician_number == (number_of_politicians_to_show - 1) else ','
            sentence_string += ' ' + politician.politician_name + comma_or_not

    return sentence_string


def figure_out_campaignx_conflict_values(campaignx1, campaignx2):
    campaignx_merge_conflict_values = {}

    for attribute in CAMPAIGNX_UNIQUE_IDENTIFIERS:
        try:
            campaignx1_attribute_value = getattr(campaignx1, attribute)
            campaignx2_attribute_value = getattr(campaignx2, attribute)
            if campaignx1_attribute_value is None and campaignx2_attribute_value is None:
                campaignx_merge_conflict_values[attribute] = 'MATCHING'
            elif campaignx1_attribute_value is None or campaignx1_attribute_value == "":
                campaignx_merge_conflict_values[attribute] = 'CAMPAIGNX2'
            elif campaignx2_attribute_value is None or campaignx2_attribute_value == "":
                campaignx_merge_conflict_values[attribute] = 'CAMPAIGNX1'
            else:
                if attribute == "campaign_title":
                    if campaignx1_attribute_value.lower() == campaignx2_attribute_value.lower():
                        campaignx_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        campaignx_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "ocd_id_state_mismatch_found":
                    if positive_value_exists(campaignx1_attribute_value):
                        campaignx_merge_conflict_values[attribute] = 'CAMPAIGNX1'
                    elif positive_value_exists(campaignx2_attribute_value):
                        campaignx_merge_conflict_values[attribute] = 'CAMPAIGNX2'
                    else:
                        campaignx_merge_conflict_values[attribute] = 'MATCHING'
                else:
                    if campaignx1_attribute_value == campaignx2_attribute_value:
                        campaignx_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        campaignx_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return campaignx_merge_conflict_values


def generate_campaignx_dict_list_from_campaignx_object_list(
        campaignx_object_list=[],
        hostname='',
        promoted_campaignx_we_vote_ids=[],
        site_owner_organization_we_vote_id='',
        visible_on_this_site_campaignx_we_vote_id_list=[],
        voter_can_vote_for_politician_we_vote_ids=[],
        voter_signed_in_with_email=False,
        voter_we_vote_id='',
):
    campaignx_manager = CampaignXManager()
    campaignx_dict_list = []
    campaignx_we_vote_id_list = []
    status = ""
    success = True
    for campaignx_object in campaignx_object_list:
        if hasattr(campaignx_object, 'we_vote_id'):
            campaignx_we_vote_id_list.append(campaignx_object.we_vote_id)

    if len(campaignx_we_vote_id_list) == 0:
        status += 'NO_CAMPAIGNS_PROVIDED_TO_GENERATE_CAMPAIGNX_DICT_LIST '
        success = False
        results = {
            'campaignx_dict_list': campaignx_dict_list,
            'status': status,
            'success': success,
        }
        return results

    voter_owned_campaignx_we_vote_ids = campaignx_manager.retrieve_voter_owned_campaignx_we_vote_ids(
        voter_we_vote_id=voter_we_vote_id,
    )
    voter_can_send_updates_campaignx_we_vote_ids = \
        campaignx_manager.retrieve_voter_can_send_updates_campaignx_we_vote_ids(
            voter_we_vote_id=voter_we_vote_id,
        )

    final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
    for campaignx in campaignx_object_list:
        voter_is_campaignx_owner = campaignx.we_vote_id in voter_owned_campaignx_we_vote_ids
        final_election_date_in_past = \
            final_election_date_plus_cool_down >= campaignx.final_election_date_as_integer \
            if positive_value_exists(campaignx.final_election_date_as_integer) else False

        # Should we promote this campaign on home page?
        if campaignx.is_still_active and campaignx.is_ok_to_promote_on_we_vote \
                and not final_election_date_in_past and not campaignx.is_in_team_review_mode:
            if positive_value_exists(site_owner_organization_we_vote_id):
                if campaignx.we_vote_id in visible_on_this_site_campaignx_we_vote_id_list:
                    promoted_campaignx_we_vote_ids.append(campaignx.we_vote_id)
            else:
                if campaignx.is_supporters_count_minimum_exceeded():
                    promoted_campaignx_we_vote_ids.append(campaignx.we_vote_id)

        campaignx_owner_list = []
        campaignx_owner_object_list = campaignx_manager.retrieve_campaignx_owner_list(
            campaignx_we_vote_id_list=[campaignx.we_vote_id], viewer_is_owner=voter_is_campaignx_owner)
        for campaignx_owner in campaignx_owner_object_list:
            campaign_owner_dict = {
                'feature_this_profile_image':               campaignx_owner.feature_this_profile_image,
                'organization_name':                        campaignx_owner.organization_name,
                'organization_we_vote_id':                  campaignx_owner.organization_we_vote_id,
                'visible_to_public':                        campaignx_owner.visible_to_public,
                'we_vote_hosted_profile_image_url_medium':  campaignx_owner.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny':    campaignx_owner.we_vote_hosted_profile_image_url_tiny,
            }
            campaignx_owner_list.append(campaign_owner_dict)

        order_in_list = 0
        try:
            order_in_list = campaignx.order_in_list
        except Exception as e:
            pass

        results = generate_campaignx_dict_from_campaignx_object(
            campaignx=campaignx,
            campaignx_owner_list=campaignx_owner_list,
            hostname=hostname,
            order_in_list=order_in_list,
            # seo_friendly_path_list=seo_friendly_path_list,
            voter_can_send_updates_campaignx_we_vote_ids=voter_can_send_updates_campaignx_we_vote_ids,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_is_campaignx_owner=voter_is_campaignx_owner,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )
        status += results['status']
        if results['success']:
            campaignx_dict_list.append(results['campaignx_dict'])

    results = {
        'campaignx_dict_list':      campaignx_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def generate_campaignx_dict_from_campaignx_object(
        campaignx=None,
        campaignx_owner_list=[],
        hostname='',
        order_in_list=0,
        seo_friendly_path_list=None,
        voter_can_send_updates_campaignx_we_vote_ids=None,
        voter_can_vote_for_politician_we_vote_ids=[],
        voter_is_campaignx_owner=False,
        voter_signed_in_with_email=False,
        voter_we_vote_id='',
):
    campaignx_manager = CampaignXManager()
    status = ""
    success = True

    # Get campaignx news items / updates
    campaignx_news_item_list = []
    news_item_list_results = campaignx_manager.retrieve_campaignx_news_item_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
        read_only=True,
        voter_is_campaignx_owner=voter_is_campaignx_owner)
    if news_item_list_results['campaignx_news_item_list_found']:
        news_item_list = news_item_list_results['campaignx_news_item_list']
        for news_item in news_item_list:
            date_last_changed_string = ''
            date_posted_string = ''
            date_sent_to_email_string = ''
            try:
                date_last_changed_string = news_item.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
                date_posted_string = news_item.date_posted.strftime('%Y-%m-%d %H:%M:%S')
                if positive_value_exists(news_item.date_sent_to_email):
                    date_sent_to_email_string = news_item.date_sent_to_email.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                status += "DATE_CONVERSION_ERROR: " + str(e) + " "
            one_news_item_dict = {
                'campaign_news_subject': news_item.campaign_news_subject,
                'campaign_news_text': news_item.campaign_news_text,
                'campaignx_news_item_we_vote_id': news_item.we_vote_id,
                'campaignx_we_vote_id': news_item.campaignx_we_vote_id,
                'date_last_changed': date_last_changed_string,
                'date_posted': date_posted_string,
                'date_sent_to_email': date_sent_to_email_string,
                'in_draft_mode': news_item.in_draft_mode,
                'organization_we_vote_id': news_item.organization_we_vote_id,
                'speaker_name': news_item.speaker_name,
                'visible_to_public': news_item.visible_to_public,
                'voter_we_vote_id': news_item.voter_we_vote_id,
                'we_vote_hosted_profile_image_url_medium': news_item.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': news_item.we_vote_hosted_profile_image_url_tiny,
            }
            campaignx_news_item_list.append(one_news_item_dict)

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
    if seo_friendly_path_list is None:
        seo_friendly_path_list = campaignx_manager.retrieve_seo_friendly_path_simple_list(
            campaignx_we_vote_id=campaignx.we_vote_id,
        )

    supporter_results = campaignx_manager.retrieve_campaignx_supporter(
        campaignx_we_vote_id=campaignx.we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        read_only=True)
    if supporter_results['success'] and supporter_results['campaignx_supporter_found']:
        campaignx_supporter = supporter_results['campaignx_supporter']
        chip_in_total = 'none'
        date_last_changed_string = ''
        date_supported_string = ''
        try:
            date_last_changed_string = campaignx_supporter.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
            date_supported_string = campaignx_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            status += "DATE_CONVERSION_ERROR: " + str(e) + " "
        try:
            from stripe_donations.models import StripeManager
            chip_in_total = StripeManager.retrieve_chip_in_total(voter_we_vote_id, campaignx.we_vote_id)
        except Exception as e:
            status += "RETRIEVE_CHIP_IN_TOTAL_ERROR: " + str(e) + " "

        voter_campaignx_supporter_dict = {
            'campaign_supported':           campaignx_supporter.campaign_supported,
            'campaignx_we_vote_id':         campaignx_supporter.campaignx_we_vote_id,
            'chip_in_total':                chip_in_total,
            'date_last_changed':            date_last_changed_string,
            'date_supported':               date_supported_string,
            'id':                           campaignx_supporter.id,
            'organization_we_vote_id':      campaignx_supporter.organization_we_vote_id,
            'supporter_endorsement':        campaignx_supporter.supporter_endorsement,
            'supporter_name':               campaignx_supporter.supporter_name,
            'visible_to_public':            campaignx_supporter.visible_to_public,
            'voter_we_vote_id':             campaignx_supporter.voter_we_vote_id,
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_image_url_medium': campaignx_supporter.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
        }
    else:
        voter_campaignx_supporter_dict = {}

    # Get most recent supporters, regardless of whether there is a written endorsement.
    latest_campaignx_supporter_list = []
    supporter_list_results = campaignx_manager.retrieve_campaignx_supporter_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
        limit=7,
        read_only=True,
        require_supporter_endorsement=False,
        require_visible_to_public=True)
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
                'campaign_supported': campaignx_supporter.campaign_supported,
                'campaignx_we_vote_id': campaignx_supporter.campaignx_we_vote_id,
                'date_supported': date_supported_string,
                'organization_we_vote_id': campaignx_supporter.organization_we_vote_id,
                'supporter_endorsement': campaignx_supporter.supporter_endorsement,
                'supporter_name': campaignx_supporter.supporter_name,
                'voter_we_vote_id': campaignx_supporter.voter_we_vote_id,
                'we_vote_hosted_profile_image_url_medium': campaignx_supporter.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
            }
            latest_campaignx_supporter_list.append(one_supporter_dict)

    # Get most recent supporter_endorsements which include written endorsement (require_supporter_endorsement == True)
    latest_campaignx_supporter_endorsement_list = []
    supporter_list_results = campaignx_manager.retrieve_campaignx_supporter_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
        limit=10,
        read_only=True,
        require_supporter_endorsement=True)
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
                'campaign_supported': campaignx_supporter.campaign_supported,
                'campaignx_we_vote_id': campaignx_supporter.campaignx_we_vote_id,
                'date_supported': date_supported_string,
                'organization_we_vote_id': campaignx_supporter.organization_we_vote_id,
                'supporter_endorsement': campaignx_supporter.supporter_endorsement,
                'supporter_name': campaignx_supporter.supporter_name,
                'voter_we_vote_id': campaignx_supporter.voter_we_vote_id,
                'we_vote_hosted_profile_image_url_medium': campaignx_supporter.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny': campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
            }
            latest_campaignx_supporter_endorsement_list.append(one_supporter_dict)

    if voter_can_send_updates_campaignx_we_vote_ids is not None:
        # Leave it as is, even if empty
        pass
    elif positive_value_exists(voter_we_vote_id):
        voter_can_send_updates_campaignx_we_vote_ids = \
            campaignx_manager.retrieve_voter_can_send_updates_campaignx_we_vote_ids(
                voter_we_vote_id=voter_we_vote_id,
            )
    else:
        voter_can_send_updates_campaignx_we_vote_ids = []

    # If smaller sizes weren't stored, use large image
    if campaignx.we_vote_hosted_campaign_photo_medium_url:
        we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_medium_url
    else:
        we_vote_hosted_campaign_photo_medium_url = campaignx.we_vote_hosted_campaign_photo_large_url
    if campaignx.we_vote_hosted_campaign_photo_small_url:
        we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_small_url
    else:
        we_vote_hosted_campaign_photo_small_url = campaignx.we_vote_hosted_campaign_photo_large_url
    supporters_count_next_goal = campaignx_manager.fetch_supporters_count_next_goal(
        supporters_count=campaignx.supporters_count,
        supporters_count_victory_goal=campaignx.supporters_count_victory_goal)
    final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
    final_election_date_in_past = \
        final_election_date_plus_cool_down >= campaignx.final_election_date_as_integer \
        if positive_value_exists(campaignx.final_election_date_as_integer) else False

    if hasattr(campaignx, 'visible_on_this_site'):
        visible_on_this_site = campaignx.visible_on_this_site
    else:
        visible_on_this_site = True

    campaignx_dict = {
        'campaign_description':             campaignx.campaign_description,
        'campaign_title':                   campaignx.campaign_title,
        'campaignx_news_item_list':         campaignx_news_item_list,
        'campaignx_owner_list':             campaignx_owner_list,
        'campaignx_politician_list':        campaignx_politician_list_modified,
        'campaignx_politician_list_exists': campaignx_politician_list_exists,
        'campaignx_politician_starter_list': campaignx_politician_starter_list,
        'campaignx_we_vote_id':             campaignx.we_vote_id,
        'final_election_date_as_integer':   campaignx.final_election_date_as_integer,
        'final_election_date_in_past':      final_election_date_in_past,
        'in_draft_mode':                    campaignx.in_draft_mode,
        'is_blocked_by_we_vote':            campaignx.is_blocked_by_we_vote,
        'is_blocked_by_we_vote_reason':     campaignx.is_blocked_by_we_vote_reason,
        'is_supporters_count_minimum_exceeded': campaignx.is_supporters_count_minimum_exceeded(),
        'latest_campaignx_supporter_endorsement_list':  latest_campaignx_supporter_endorsement_list,
        'latest_campaignx_supporter_list':  latest_campaignx_supporter_list,
        'linked_politician_we_vote_id':     campaignx.linked_politician_we_vote_id,
        'order_in_list':                    order_in_list,
        'seo_friendly_path':                campaignx.seo_friendly_path,
        'seo_friendly_path_list':           seo_friendly_path_list,
        'supporters_count':                 campaignx.supporters_count,
        'supporters_count_next_goal':       supporters_count_next_goal,
        'supporters_count_victory_goal':    campaignx.supporters_count_victory_goal,
        'visible_on_this_site':             visible_on_this_site,
        'voter_campaignx_supporter':        voter_campaignx_supporter_dict,
        'voter_can_send_updates_to_campaignx':
            campaignx.we_vote_id in voter_can_send_updates_campaignx_we_vote_ids,
        'voter_can_vote_for_politician_we_vote_ids': voter_can_vote_for_politician_we_vote_ids,
        'voter_is_campaignx_owner':         voter_is_campaignx_owner,
        'voter_signed_in_with_email':       voter_signed_in_with_email,
        'we_vote_hosted_campaign_photo_large_url':  campaignx.we_vote_hosted_campaign_photo_large_url,
        'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
        'we_vote_hosted_campaign_photo_small_url': we_vote_hosted_campaign_photo_small_url,
        'we_vote_hosted_profile_image_url_large': campaignx.we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium': campaignx.we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny': campaignx.we_vote_hosted_profile_image_url_tiny,
    }

    results = {
        'campaignx_dict':   campaignx_dict,
        'status':           status,
        'success':          success,
    }
    return results


def merge_these_two_campaignx_entries(
        campaignx1_we_vote_id,
        campaignx2_we_vote_id,
        admin_merge_choices={},
        regenerate_campaign_title=False):
    """
    Process the merging of two campaignx entries
    :param campaignx1_we_vote_id:
    :param campaignx2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :param regenerate_campaign_title:
    :return:
    """
    status = ""
    campaignx_manager = CampaignXManager()

    # CampaignX 1 is the one we keep, and CampaignX 2 is the one we will merge into CampaignX 1
    campaignx1_results = \
        campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx1_we_vote_id, read_only=False)
    if campaignx1_results['campaignx_found']:
        campaignx1_on_stage = campaignx1_results['campaignx']
        campaignx1_id = campaignx1_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_CAMPAIGNX_ENTRIES-COULD_NOT_RETRIEVE_CAMPAIGNX1 ",
            'campaignx_entries_merged': False,
            'campaignx': None,
        }
        return results

    campaignx2_results = \
        campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx2_we_vote_id, read_only=False)
    if campaignx2_results['campaignx_found']:
        campaignx2_on_stage = campaignx2_results['campaignx']
        campaignx2_id = campaignx2_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_CAMPAIGNX_ENTRIES-COULD_NOT_RETRIEVE_CAMPAIGNX2 ",
            'campaignx_entries_merged': False,
            'campaignx': None,
        }
        return results

    # TODO: Migrate images?

    # Merge attribute values chosen by the admin
    for attribute in CAMPAIGNX_UNIQUE_IDENTIFIERS:
        # try:
        if attribute in admin_merge_choices:
            setattr(campaignx1_on_stage, attribute, admin_merge_choices[attribute])
        # except Exception as e:
        #     # Don't completely fail if in attribute can't be saved.
        #     status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "

    if positive_value_exists(regenerate_campaign_title):
        if positive_value_exists(campaignx1_on_stage.linked_politician_we_vote_id):
            from politician.models import PoliticianManager
            politician_manager = PoliticianManager()
            results = politician_manager.retrieve_politician(
                politician_we_vote_id=campaignx1_on_stage.linked_politician_we_vote_id)
            if results['politician_found']:
                politician = results['politician']
                politician_name = politician.politician_name
                state_code = politician.state_code
                from politician.controllers_generate_seo_friendly_path import generate_campaign_title_from_politician
                campaignx1_on_stage.campaign_title = generate_campaign_title_from_politician(
                    politician_name=politician_name,
                    state_code=state_code)

    # #####################################
    # Merge CampaignXListedByOrganization
    campaignx1_organization_we_vote_id_list = []
    campaignx2_listed_by_organization_to_delete_list = []
    queryset = CampaignXListedByOrganization.objects.all()
    queryset = queryset.filter(campaignx_we_vote_id__iexact=campaignx1_we_vote_id)
    campaignx1_listed_by_organization_list = list(queryset)
    for campaignx1_listed_by_organization in campaignx1_listed_by_organization_list:
        if positive_value_exists(campaignx1_listed_by_organization.site_owner_organization_we_vote_id) and \
                campaignx1_listed_by_organization.site_owner_organization_we_vote_id \
                not in campaignx1_organization_we_vote_id_list:
            campaignx1_organization_we_vote_id_list\
                .append(campaignx1_listed_by_organization.site_owner_organization_we_vote_id)

    queryset = CampaignXListedByOrganization.objects.all()
    queryset = queryset.filter(campaignx_we_vote_id__iexact=campaignx2_we_vote_id)
    campaignx2_listed_by_organization_list = list(queryset)
    for campaignx2_listed_by_organization in campaignx2_listed_by_organization_list:
        # Is this listed_by_organization already in CampaignX 1?
        campaignx2_listed_by_organization_matches_campaignx1_listed_by_organization = False
        if positive_value_exists(campaignx2_listed_by_organization.site_owner_organization_we_vote_id) and \
                campaignx2_listed_by_organization.site_owner_organization_we_vote_id \
                in campaignx1_organization_we_vote_id_list:
            campaignx2_listed_by_organization_matches_campaignx1_listed_by_organization = True
        if campaignx2_listed_by_organization_matches_campaignx1_listed_by_organization:
            # If the listed_by_organization is already in CampaignX 1, move them to campaignx1
            campaignx2_listed_by_organization_to_delete_list.append(campaignx2_listed_by_organization)
        else:
            # If not, move them to campaignx1
            campaignx2_listed_by_organization.campaignx_we_vote_id = campaignx1_we_vote_id
            campaignx2_listed_by_organization.save()

    # #####################################
    # Merge CampaignXNewsItems
    campaignx_news_items_moved = CampaignXNewsItem.objects \
        .filter(campaignx_we_vote_id__iexact=campaignx2_we_vote_id) \
        .update(campaignx_we_vote_id=campaignx1_we_vote_id)

    # ##################################
    # Move the seo friendly paths from campaignx2 over to campaignx1. CampaignXSEOFriendlyPath entries are unique,
    #  so we don't need to check for duplicates.
    from campaign.models import CampaignXSEOFriendlyPath
    campaignx_seo_friendly_path_moved = CampaignXSEOFriendlyPath.objects \
        .filter(campaignx_we_vote_id__iexact=campaignx2_we_vote_id) \
        .update(campaignx_we_vote_id=campaignx1_we_vote_id)

    # ##################################
    # Update the linked_campaignx_we_vote_id in Politician entries
    try:
        from politician.models import Politician
        linked_campaignx_we_vote_id_updated = Politician.objects \
            .filter(linked_campaignx_we_vote_id__iexact=campaignx2_we_vote_id) \
            .update(linked_campaignx_we_vote_id=campaignx1_we_vote_id)
    except Exception as e:
        status += "POLITICIAN_LINKED_CAMPAIGNX_WE_VOTE_ID_NOT_UPDATED: " + str(e) + " "

    # ##################################
    # Migrate campaignx owners
    campaignx1_owner_organization_we_vote_id_list = []
    campaignx1_owner_voter_we_vote_id_list = []
    campaignx2_owners_to_delete_list = []
    campaignx1_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
        campaignx_we_vote_id_list=[campaignx1_we_vote_id],
        viewer_is_owner=True
    )
    for campaignx1_owner in campaignx1_owner_list:
        if positive_value_exists(campaignx1_owner.organization_we_vote_id) and \
                campaignx1_owner.organization_we_vote_id not in campaignx1_owner_organization_we_vote_id_list:
            campaignx1_owner_organization_we_vote_id_list.append(campaignx1_owner.organization_we_vote_id)
        if positive_value_exists(campaignx1_owner.voter_we_vote_id) and \
                campaignx1_owner.voter_we_vote_id not in campaignx1_owner_voter_we_vote_id_list:
            campaignx1_owner_voter_we_vote_id_list.append(campaignx1_owner.voter_we_vote_id)

    campaignx2_owner_list = campaignx_manager.retrieve_campaignx_owner_list(
        campaignx_we_vote_id_list=[campaignx2_we_vote_id],
        read_only=False,
        viewer_is_owner=True
    )
    for campaignx2_owner in campaignx2_owner_list:
        # Is this campaign owner already in CampaignX 1?
        campaignx2_owner_matches_campaignx1_owner = False
        if positive_value_exists(campaignx2_owner.organization_we_vote_id) and \
                campaignx2_owner.organization_we_vote_id in campaignx1_owner_organization_we_vote_id_list:
            campaignx2_owner_matches_campaignx1_owner = True
        if positive_value_exists(campaignx2_owner.voter_we_vote_id) and \
                campaignx2_owner.voter_we_vote_id in campaignx1_owner_voter_we_vote_id_list:
            campaignx2_owner_matches_campaignx1_owner = True
        if campaignx2_owner_matches_campaignx1_owner:
            # If there is a match, save to delete below
            campaignx2_owners_to_delete_list.append(campaignx2_owner)
        else:
            # If not, move them to campaignx1
            campaignx2_owner.campaignx_we_vote_id = campaignx1_we_vote_id
            campaignx2_owner.save()

    # #####################################
    # If a CampaignX politician isn't already in CampaignX 1, bring Politician over from CampaignX 2
    campaignx1_politician_we_vote_id_list = []
    campaignx2_politicians_to_delete_list = []
    campaignx1_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
        campaignx_we_vote_id=campaignx1_we_vote_id,
        read_only=False,
    )
    for campaignx1_politician in campaignx1_politician_list:
        if positive_value_exists(campaignx1_politician.politician_we_vote_id) and \
                campaignx1_politician.politician_we_vote_id not in campaignx1_politician_we_vote_id_list:
            campaignx1_politician_we_vote_id_list.append(campaignx1_politician.politician_we_vote_id)

    campaignx2_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
        campaignx_we_vote_id=campaignx2_we_vote_id,
        read_only=False,
    )
    for campaignx2_politician in campaignx2_politician_list:
        # Is this campaign politician already in CampaignX 1?
        if not positive_value_exists(campaignx2_politician.politician_we_vote_id):
            campaignx2_politicians_to_delete_list.append(campaignx2_politician)
        elif campaignx2_politician.politician_we_vote_id not in campaignx1_politician_we_vote_id_list:
            # If not, move them to campaignx1
            campaignx2_politician.campaignx_we_vote_id = campaignx1_we_vote_id
            campaignx2_politician.save()
        else:
            campaignx2_politicians_to_delete_list.append(campaignx2_politician)

    # #####################################
    # Merge CampaignX Supporters
    campaignx1_organization_we_vote_id_list = []
    campaignx1_voter_we_vote_id_list = []
    campaignx2_supporters_to_delete_list = []
    queryset = CampaignXSupporter.objects.all()
    queryset = queryset.filter(campaignx_we_vote_id__iexact=campaignx1_we_vote_id)
    campaignx1_supporters_list = list(queryset)
    for campaignx1_supporter in campaignx1_supporters_list:
        if positive_value_exists(campaignx1_supporter.organization_we_vote_id) and \
                campaignx1_supporter.organization_we_vote_id not in campaignx1_organization_we_vote_id_list:
            campaignx1_organization_we_vote_id_list.append(campaignx1_supporter.organization_we_vote_id)
        if positive_value_exists(campaignx1_supporter.voter_we_vote_id) and \
                campaignx1_supporter.voter_we_vote_id not in campaignx1_voter_we_vote_id_list:
            campaignx1_voter_we_vote_id_list.append(campaignx1_supporter.voter_we_vote_id)

    queryset = CampaignXSupporter.objects.all()
    queryset = queryset.filter(campaignx_we_vote_id__iexact=campaignx2_we_vote_id)
    campaignx2_supporters_list = list(queryset)
    for campaignx2_supporter in campaignx2_supporters_list:
        # Is this campaign politician already in CampaignX 1?
        campaignx2_supporter_matches_campaignx1_supporter = False
        if positive_value_exists(campaignx2_supporter.organization_we_vote_id) and \
                campaignx2_supporter.organization_we_vote_id in campaignx1_organization_we_vote_id_list:
            campaignx2_supporter_matches_campaignx1_supporter = True
        if positive_value_exists(campaignx2_supporter.voter_we_vote_id) and \
                campaignx2_supporter.voter_we_vote_id in campaignx1_voter_we_vote_id_list:
            campaignx2_supporter_matches_campaignx1_supporter = True
        if campaignx2_supporter_matches_campaignx1_supporter:
            # If the supporter is already in CampaignX 1, move them to campaignx1
            campaignx2_supporters_to_delete_list.append(campaignx2_supporter)
        else:
            # If not, move them to campaignx1
            campaignx2_supporter.campaignx_we_vote_id = campaignx1_we_vote_id
            campaignx2_supporter.save()

    # Clear 'unique=True' fields in campaignx2_on_stage, which need to be Null before campaignx1_on_stage can be saved
    #  with updated values
    campaignx2_updated = False
    for attribute in CAMPAIGNX_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
        setattr(campaignx2_on_stage, attribute, None)
        campaignx2_updated = True
    if campaignx2_updated:
        campaignx2_on_stage.save()

    campaignx1_on_stage.save()

    # Delete duplicate campaignx2 owner entries
    for campaignx2owner in campaignx2_owners_to_delete_list:
        campaignx2owner.delete()

    # Delete duplicate campaignx2 politician entries
    for campaignx2_politician in campaignx2_politicians_to_delete_list:
        campaignx2_politician.delete()

    # Delete duplicate campaignx2 supporter entries
    for campaignx2_supporter in campaignx2_supporters_to_delete_list:
        campaignx2_supporter.delete()

    # Finally, remove campaignx 2
    campaignx2_on_stage.delete()

    results = {
        'success': True,
        'status': status,
        'campaignx_entries_merged': True,
        'campaignx': campaignx1_on_stage,
    }
    return results


def move_campaignx_to_another_organization(
        from_organization_we_vote_id, to_organization_we_vote_id,
        to_organization_name=None):
    status = ''
    success = True
    campaignx_entries_moved = 0
    campaignx_listed_entries_moved = 0
    campaignx_news_item_entries_moved = 0
    campaignx_owner_entries_moved = 0
    campaignx_supporter_entries_moved = 0

    if not positive_value_exists(from_organization_we_vote_id) or not positive_value_exists(to_organization_we_vote_id):
        status += "MOVE_CAMPAIGNX_TO_ORG-MISSING_EITHER_FROM_OR_TO_ORG_WE_VOTE_ID "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_organization_we_vote_id':     from_organization_we_vote_id,
            'to_organization_we_vote_id':       to_organization_we_vote_id,
            'campaignx_entries_moved':          campaignx_entries_moved,
            'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
        }
        return results

    if from_organization_we_vote_id == to_organization_we_vote_id:
        status += "MOVE_CAMPAIGNX_TO_ORG-FROM_AND_TO_ORG_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'from_organization_we_vote_id':     from_organization_we_vote_id,
            'to_organization_we_vote_id':       to_organization_we_vote_id,
            'campaignx_entries_moved':          campaignx_entries_moved,
            'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
        }
        return results

    # #############################################
    # Move based on organization_we_vote_id
    if positive_value_exists(to_organization_name):
        try:
            campaignx_owner_entries_moved += CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_TO_ORG_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(supporter_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_TO_ORG_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
        try:
            campaignx_news_item_entries_moved += CampaignXNewsItem.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(speaker_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_NEWS_ITEM_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
    else:
        try:
            campaignx_owner_entries_moved += CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_TO_ORG_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_TO_ORG_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        try:
            campaignx_news_item_entries_moved += CampaignXNewsItem.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_NEWS_ITEM_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "

    try:
        campaignx_listed_entries_moved += CampaignXListedByOrganization.objects \
            .filter(site_owner_organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .update(site_owner_organization_we_vote_id=to_organization_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_LISTED_BY_ORG_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "

    results = {
        'status':                           status,
        'success':                          success,
        'from_organization_we_vote_id':     from_organization_we_vote_id,
        'to_organization_we_vote_id':       to_organization_we_vote_id,
        'campaignx_entries_moved':          campaignx_owner_entries_moved,
        'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
    }
    return results


def move_campaignx_to_another_politician(
        from_politician_we_vote_id='',
        to_politician_we_vote_id=''):
    """

    :param from_politician_we_vote_id:
    :param to_politician_we_vote_id:
    :return:
    """
    status = ''
    success = True
    campaignx_entries_moved = 0

    if positive_value_exists(from_politician_we_vote_id):
        try:
            campaignx_entries_moved += CampaignXPolitician.objects \
                .filter(politician_we_vote_id__iexact=from_politician_we_vote_id) \
                .update(politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_CAMPAIGNX_BY_POLITICIAN_WE_VOTE_ID: " + str(e) + " "
            success = False

    results = {
        'status':                   status,
        'success':                  success,
        'campaignx_entries_moved':  campaignx_entries_moved,
    }
    return results


def move_campaignx_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, from_organization_we_vote_id, to_organization_we_vote_id,
        to_organization_name=None):
    status = ''
    success = True
    campaignx_entries_moved = 0
    campaignx_listed_entries_moved = 0
    campaignx_news_item_entries_moved = 0
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
        success = False

    # ######################
    # Move News Item based on voter_we_vote_id
    try:
        campaignx_news_item_entries_moved += CampaignXNewsItem.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_NEWS_ITEM_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False

    # ######################
    # Move owners based on voter_we_vote_id
    try:
        campaignx_owner_entries_moved += CampaignXOwner.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False

    # ######################
    # Move supporters based on voter_we_vote_id
    try:
        campaignx_supporter_entries_moved += CampaignXSupporter.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False

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
            success = False
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(supporter_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
            success = False
        try:
            campaignx_news_item_entries_moved += CampaignXNewsItem.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(speaker_name=to_organization_name,
                        organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_NEWS_ITEM_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
            success = False
    else:
        try:
            campaignx_owner_entries_moved += CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
            success = False
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
            success = False
        try:
            campaignx_news_item_entries_moved += CampaignXNewsItem.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_NEWS_ITEM_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
            success = False

    try:
        campaignx_listed_entries_moved += CampaignXListedByOrganization.objects \
            .filter(site_owner_organization_we_vote_id__iexact=from_organization_we_vote_id) \
            .update(site_owner_organization_we_vote_id=to_organization_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_LISTED_BY_ORG_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        success = False

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'campaignx_entries_moved':          campaignx_owner_entries_moved,
        'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
    }
    return results


def delete_campaignx_supporters_after_positions_removed(
        request,
        friends_only_positions=False,
        state_code=''):
    # Create default variables needed below
    campaignx_supporter_entries_deleted_count = 0
    campaignx_we_vote_id_list_to_refresh = []
    number_to_delete = 20  # 1000
    from position.models import PositionEntered, PositionForFriends
    position_objects_to_set_campaignx_supporter_created_true = []  # Field is 'campaignx_supporter_created'
    position_updates_made = 0
    position_we_vote_id_list_to_remove_from_campaignx_supporters = []
    campaignx_supporter_id_list_to_delete = []
    status = ''
    success = True
    timezone = pytz.timezone("America/Los_Angeles")
    datetime_now = timezone.localize(datetime.now())
    date_today_as_integer = convert_date_to_date_as_integer(datetime_now)
    update_message = ''

    try:
        if positive_value_exists(friends_only_positions):
            position_query = PositionForFriends.objects.all()  # Cannot be readonly, since we bulk_update at the end
        else:
            position_query = PositionEntered.objects.all()  # Cannot be readonly, since we bulk_update at the end
        position_query = position_query.exclude(campaignx_supporter_created=True)
        position_query = position_query.exclude(stance=SUPPORT)
        position_query = position_query.filter(
            Q(position_ultimate_election_not_linked=True) |
            Q(position_ultimate_election_date__gte=date_today_as_integer)
        )
        if positive_value_exists(state_code):
            position_query = position_query.filter(state_code__iexact=state_code)
        total_to_convert = position_query.count()
        position_list_with_support_removed = list(position_query[:number_to_delete])
    except Exception as e:
        position_list_with_support_removed = []
        total_to_convert = 0
        update_message += "POSITION_LIST_WITH_SUPPORT_RETRIEVE_FAILED: " + str(e) + " "

    for one_position in position_list_with_support_removed:
        position_we_vote_id_list_to_remove_from_campaignx_supporters.append(one_position.we_vote_id)

    campaignx_supporter_search_success = True
    if len(position_we_vote_id_list_to_remove_from_campaignx_supporters) > 0:
        try:
            queryset = CampaignXSupporter.objects.using('readonly').all()
            queryset = queryset.filter(
                linked_position_we_vote_id__in=position_we_vote_id_list_to_remove_from_campaignx_supporters)
            campaignx_supporter_entries_to_delete = list(queryset)
            for one_campaignx_supporter in campaignx_supporter_entries_to_delete:
                campaignx_supporter_id_list_to_delete.append(one_campaignx_supporter.id)
        except Exception as e:
            campaignx_supporter_search_success = False
            update_message += "CAMPAIGNX_SUPPORTER_RETRIEVE_BY_POSITION_WE_VOTE_ID-FAILED: " + str(e) + " "

    position_updates_needed = False
    if campaignx_supporter_search_success:
        # As long as there haven't been any errors above, we can prepare to mark
        #  all positions 'campaignx_supporter_created' = True
        for one_position in position_list_with_support_removed:
            one_position.campaignx_supporter_created = True
            position_objects_to_set_campaignx_supporter_created_true.append(one_position)
            position_updates_made += 1
            position_updates_needed = True

    campaignx_supporter_bulk_delete_success = True
    if len(campaignx_supporter_id_list_to_delete) > 0:
        try:
            queryset = CampaignXSupporter.objects.all()
            queryset = queryset.filter(id__in=campaignx_supporter_id_list_to_delete)
            campaignx_supporter_entries_deleted_count, campaigns_dict = queryset.delete()
            campaignx_supporter_bulk_delete_success = True
            update_message += \
                "{campaignx_supporter_entries_deleted_count:,} CampaignXSupporter entries deleted, " \
                "".format(campaignx_supporter_entries_deleted_count=campaignx_supporter_entries_deleted_count)
        except Exception as e:
            campaignx_supporter_bulk_delete_success = False
            update_message += "CAMPAIGNX_SUPPORTER_BULK_DELETE-FAILED: " + str(e) + " "

    if position_updates_needed and campaignx_supporter_bulk_delete_success:
        try:
            if friends_only_positions:
                PositionForFriends.objects.bulk_update(
                    position_objects_to_set_campaignx_supporter_created_true, ['campaignx_supporter_created'])
            else:
                PositionEntered.objects.bulk_update(
                    position_objects_to_set_campaignx_supporter_created_true, ['campaignx_supporter_created'])
            update_message += \
                "{position_updates_made:,} positions updated with campaignx_supporter_created=True, " \
                "".format(position_updates_made=position_updates_made)
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with PositionEntered.objects.bulk_update: {e}, "
                                 "".format(e=e))

    total_to_convert_after = total_to_convert - number_to_delete if total_to_convert > number_to_delete else 0
    if positive_value_exists(total_to_convert_after):
        update_message += \
            "{total_to_convert_after:,} positions remaining in 'delete CampaignXSupporter' process. " \
            "".format(total_to_convert_after=total_to_convert_after)

    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    results = {
        'campaignx_supporter_entries_deleted':  campaignx_supporter_entries_deleted_count,
        'campaignx_we_vote_id_list_to_refresh': campaignx_we_vote_id_list_to_refresh,
        'status':   status,
        'success':  success,
    }
    return results


def retrieve_recommended_campaignx_list_for_campaignx_we_vote_id(
        request=None,
        voter_device_id='',
        campaignx_we_vote_id='',
        voter_we_vote_id='',
        site_owner_organization_we_vote_id='',
        minimum_number_of_campaignx_options=15,
        read_only=True):
    """
    Regarding minimum_number_of_campaignx_options:
    If we ask voters to sign 5 more campaigns, we want to make sure we send 3x options so we have enough
    available on the front end so we can filter out campaigns with duplicate politicians
    (after the voter makes choices) and let the voter skip campaigns they aren't interested in

    :param request:
    :param voter_device_id:
    :param campaignx_we_vote_id:
    :param voter_we_vote_id:
    :param site_owner_organization_we_vote_id:
    :param minimum_number_of_campaignx_options:
    :param read_only:
    :return:
    """
    campaignx_manager = CampaignXManager()
    campaignx_list = []
    original_campaignx_we_vote_id_list = [campaignx_we_vote_id]
    success = True
    status = ""

    # Remove campaigns already supported by this voter
    supported_by_voter_campaignx_we_vote_id_list = []
    if positive_value_exists(voter_we_vote_id):
        results = campaignx_manager.retrieve_campaignx_we_vote_id_list_supported_by_voter(
            voter_we_vote_id=voter_we_vote_id)
        if results['campaignx_we_vote_id_list_found']:
            supported_by_voter_campaignx_we_vote_id_list = results['campaignx_we_vote_id_list']

    campaignx_we_vote_id_list_voter_can_vote_for = []
    if positive_value_exists(voter_device_id):
        from ballot.controllers import what_voter_can_vote_for
        results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        if len(results['voter_can_vote_for_politician_we_vote_ids']) > 0:
            voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']
            politician_results = campaignx_manager.retrieve_campaignx_we_vote_id_list_by_politician_we_vote_id(
                politician_we_vote_id_list=voter_can_vote_for_politician_we_vote_ids)
            if politician_results['campaignx_we_vote_id_list_found']:
                campaignx_we_vote_id_list_voter_can_vote_for = politician_results['campaignx_we_vote_id_list']

    # Create pool of options
    # recommended_campaignx_we_vote_id_list = ['wv02camp4']
    continue_searching_for_options = True
    if positive_value_exists(site_owner_organization_we_vote_id):
        # Retrieve all campaigns visible on this site
        visible_on_this_site_campaignx_we_vote_id_list = \
            campaignx_manager.retrieve_visible_on_this_site_campaignx_simple_list(
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
        recommended_campaignx_we_vote_id_list = \
            list(set(visible_on_this_site_campaignx_we_vote_id_list) - set(original_campaignx_we_vote_id_list))
        if len(supported_by_voter_campaignx_we_vote_id_list) > 0:
            recommended_campaignx_we_vote_id_list = \
                list(set(recommended_campaignx_we_vote_id_list) - set(supported_by_voter_campaignx_we_vote_id_list))
        continue_searching_for_options = False
    else:
        recommended_campaignx_we_vote_id_list = campaignx_we_vote_id_list_voter_can_vote_for
        recommended_campaignx_we_vote_id_list = \
            list(set(recommended_campaignx_we_vote_id_list) - set(original_campaignx_we_vote_id_list))
        if len(supported_by_voter_campaignx_we_vote_id_list) > 0:
            recommended_campaignx_we_vote_id_list = \
                list(set(recommended_campaignx_we_vote_id_list) - set(supported_by_voter_campaignx_we_vote_id_list))
        if len(recommended_campaignx_we_vote_id_list) >= minimum_number_of_campaignx_options:
            # If we have the number we need, we can stop here
            continue_searching_for_options = False

    if continue_searching_for_options:
        number_of_options_already_found = len(recommended_campaignx_we_vote_id_list)
        number_to_find = minimum_number_of_campaignx_options - number_of_options_already_found
        if number_to_find > 0:
            campaignx_we_vote_id_list_to_exclude = \
                list(set(recommended_campaignx_we_vote_id_list +
                         supported_by_voter_campaignx_we_vote_id_list +
                         original_campaignx_we_vote_id_list))

            results = campaignx_manager.retrieve_campaignx_we_vote_id_list_filler_options(
                campaignx_we_vote_id_list_to_exclude=campaignx_we_vote_id_list_to_exclude,
                limit=number_to_find)
            if results['campaignx_we_vote_id_list_found']:
                campaignx_we_vote_id_list = results['campaignx_we_vote_id_list']
                recommended_campaignx_we_vote_id_list = \
                    list(set(recommended_campaignx_we_vote_id_list + campaignx_we_vote_id_list))

    results = campaignx_manager.retrieve_campaignx_list_by_campaignx_we_vote_id_list(
        campaignx_we_vote_id_list=recommended_campaignx_we_vote_id_list,
        read_only=read_only)
    campaignx_list_found = results['campaignx_list_found']
    campaignx_list = results['campaignx_list']
    status += results['status']

    if campaignx_list_found:
        if len(campaignx_list) > minimum_number_of_campaignx_options:
            # Consider sorting this list and filtering out ones with lowest "score"
            pass

    results = {
        'success': success,
        'status': status,
        'campaignx_list_found': campaignx_list_found,
        'campaignx_list': campaignx_list,
    }
    return results


def update_campaignx_from_politician(campaignx, politician):
    status = ''
    success = True
    save_changes = True
    # We want to match the campaignx profile images to whatever is in the politician (even None)
    campaignx.we_vote_hosted_profile_image_url_large = politician.we_vote_hosted_profile_image_url_large
    campaignx.we_vote_hosted_profile_image_url_medium = politician.we_vote_hosted_profile_image_url_medium
    campaignx.we_vote_hosted_profile_image_url_tiny = politician.we_vote_hosted_profile_image_url_tiny
    # TEMPORARY - Clear out we_vote_hosted_campaign_photo_large_url photos for campaigns hard-linked to politicians
    #  because all of these images were copied from the politician, and we now have a new location for them
    if positive_value_exists(campaignx.linked_politician_we_vote_id):
        campaignx.we_vote_hosted_campaign_photo_large_url = None
        campaignx.we_vote_hosted_campaign_photo_medium_url = None
        campaignx.we_vote_hosted_campaign_photo_small_url = None
    if positive_value_exists(politician.seo_friendly_path):
        campaignx.seo_friendly_path = politician.seo_friendly_path
    else:
        campaignx.seo_friendly_path = None

    # if not positive_value_exists(campaignx.wikipedia_url) and \
    #         positive_value_exists(politician.wikipedia_url):
    #     campaignx.wikipedia_url = politician.wikipedia_url
    #     save_changes = True

    results = {
        'success':      success,
        'status':       status,
        'campaignx':    campaignx,
        'save_changes': save_changes,
    }
    return results


def delete_campaign_supporter(voter_to_delete=None):
    
    status = ""
    success = True
    campaign_supporter_deleted = 0
    campaign_supporter_not_deleted = 0
    voter_to_delete_id = voter_to_delete.id

    if not positive_value_exists(voter_to_delete_id):
        status += "DELETE_CAMPAIGN_SUPPORTER-MISSING_VOTER_ID"
        success = False
        results = {
            'status':                           status,
            'success':                          success,
            'voter_to_delete_we_vote_id':       voter_to_delete_id,
            'campaign_supporter_deleted':       campaign_supporter_deleted,
            'campaign_supporter_not_deleted':   campaign_supporter_not_deleted,
        }
        return results
    
    try:
        number_deleted, details = CampaignXSupporter.objects\
            .filter(voter_we_vote_id__iexact=voter_to_delete_id, )\
            .delete()
        campaign_supporter_deleted += number_deleted
    except Exception as e:
        status += "CampaignXSupporter CAMPAIGN SUPPORTER NOT DELETED: " + str(e) + " "
        campaign_supporter_not_deleted += 1


    results = {
        'status':                           status,
        'success':                          success,
        'campaign_supporter_deleted':       campaign_supporter_deleted,
        'campaign_supporter_not_deleted':   campaign_supporter_not_deleted,
    }
    
    return results