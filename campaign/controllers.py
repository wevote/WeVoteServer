# campaign/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CampaignX, CampaignXListedByOrganization, CampaignXManager, CampaignXNewsItem, CampaignXOwner, \
    CampaignXSupporter, FINAL_ELECTION_DATE_COOL_DOWN
import base64
from image.controllers import cache_campaignx_image, create_resized_images
import json
from io import BytesIO
from PIL import Image
import re
from activity.controllers import update_or_create_activity_notice_seed_for_campaignx_supporter_initial_response
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import generate_date_as_integer, positive_value_exists

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


def campaignx_list_retrieve_for_api(  # campaignListRetrieve
        request=None,
        voter_device_id='',
        hostname='',
        recommended_campaigns_for_campaignx_we_vote_id=''):
    """

    :param request:
    :param voter_device_id:
    :param hostname:
    :param recommended_campaigns_for_campaignx_we_vote_id:
    :return:
    """
    campaignx_display_list = []
    status = ""
    promoted_campaignx_list_returned = True
    voter_can_vote_for_politicians_list_returned = True
    voter_owned_campaignx_list_returned = True
    voter_started_campaignx_list_returned = True
    voter_supported_campaignx_list_returned = True

    if positive_value_exists(recommended_campaigns_for_campaignx_we_vote_id):
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
    #     # We need to know all of the politicians this voter can vote for so we can figure out
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
                including_started_by_voter_we_vote_id=voter_we_vote_id)
    success = results['success']
    status += results['status']
    campaignx_list = results['campaignx_list']
    campaignx_list_found = results['campaignx_list_found']

    if success:
        voter_owned_campaignx_we_vote_ids = campaignx_manager.retrieve_voter_owned_campaignx_we_vote_ids(
            voter_we_vote_id=voter_we_vote_id,
        )
        voter_can_send_updates_campaignx_we_vote_ids = \
            campaignx_manager.retrieve_voter_can_send_updates_campaignx_we_vote_ids(
                voter_we_vote_id=voter_we_vote_id,
            )

        final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
        for campaignx in campaignx_list:
            viewer_is_owner = campaignx.we_vote_id in voter_owned_campaignx_we_vote_ids
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
                campaignx_we_vote_id=campaignx.we_vote_id, viewer_is_owner=viewer_is_owner)
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
                    'we_vote_hosted_profile_image_url_tiny':
                        campaignx_politician.we_vote_hosted_profile_image_url_tiny,
                }
                campaignx_politician_list_modified.append(campaignx_politician_dict)

            # Get list of SEO Friendly Paths related to this campaignX. For most campaigns, there will only be one.
            seo_friendly_path_list = campaignx_manager.retrieve_seo_friendly_path_simple_list(
                campaignx_we_vote_id=campaignx.we_vote_id,
            )

            voter_campaignx_supporter_dict = {}
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
                    status += "LIST_RETRIEVE_CHIP_IN_TOTAL_ERROR: " + str(e) + " "
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
                    'we_vote_hosted_profile_photo_image_url_medium':
                        campaignx_supporter.we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_photo_image_url_tiny':
                        campaignx_supporter.we_vote_hosted_profile_image_url_tiny,
                }

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
            supporters_count_next_goal = campaignx_manager.fetch_supporters_count_next_goal(
                supporters_count=campaignx.supporters_count,
                supporters_count_victory_goal=campaignx.supporters_count_victory_goal)
            one_campaignx = {
                'campaign_description':                     campaignx.campaign_description,
                'campaignx_owner_list':                     campaignx_owner_list,
                'campaignx_politician_list':                campaignx_politician_list_modified,
                'campaignx_politician_list_exists':         campaignx_politician_list_exists,
                'campaignx_politician_starter_list':        campaignx_politician_starter_list,
                'campaign_title':                           campaignx.campaign_title,
                'campaignx_we_vote_id':                     campaignx.we_vote_id,
                'final_election_date_as_integer':           campaignx.final_election_date_as_integer,
                'final_election_date_in_past':              final_election_date_in_past,
                'in_draft_mode':                            campaignx.in_draft_mode,
                'is_blocked_by_we_vote':                    campaignx.is_blocked_by_we_vote,
                'is_blocked_by_we_vote_reason':             campaignx.is_blocked_by_we_vote_reason,
                'is_in_team_review_mode':                   campaignx.is_in_team_review_mode,
                'is_supporters_count_minimum_exceeded':     campaignx.is_supporters_count_minimum_exceeded(),
                'seo_friendly_path':                        campaignx.seo_friendly_path,
                'seo_friendly_path_list':                   seo_friendly_path_list,
                'supporters_count':                         campaignx.supporters_count,
                'supporters_count_next_goal':               supporters_count_next_goal,
                'supporters_count_victory_goal':            campaignx.supporters_count_victory_goal,
                'visible_on_this_site':                     visible_on_this_site,
                'voter_campaignx_supporter':                voter_campaignx_supporter_dict,
                'voter_can_send_updates_to_campaignx':
                    campaignx.we_vote_id in voter_can_send_updates_campaignx_we_vote_ids,
                'voter_is_campaignx_owner':                 viewer_is_owner,
                'voter_signed_in_with_email':               voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url':  campaignx.we_vote_hosted_campaign_photo_large_url,
                'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
                'we_vote_hosted_campaign_photo_small_url':  we_vote_hosted_campaign_photo_small_url,
            }
            campaignx_display_list.append(one_campaignx)

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
        'campaignx_list':                           campaignx_display_list,
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
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
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
                'status':                                   status,
                'success':                                  False,
                'campaign_description':                     '',
                'campaign_title':                           '',
                'campaignx_owner_list':                     campaignx_owner_list,
                'campaignx_politician_list':                [],
                'campaignx_politician_list_exists':         False,
                'campaignx_politician_starter_list':        campaignx_politician_starter_list,
                'campaignx_we_vote_id':                     '',
                'final_election_date_as_integer':           None,
                'final_election_date_in_past':              False,
                'in_draft_mode':                            True,
                'is_blocked_by_we_vote':                    False,
                'is_blocked_by_we_vote_reason':             '',
                'is_supporters_count_minimum_exceeded':     False,
                'seo_friendly_path':                        '',
                'seo_friendly_path_list':                   seo_friendly_path_list,
                'supporters_count':                         0,
                'supporters_count_next_goal':               0,
                'supporters_count_victory_goal':            0,
                'visible_on_this_site':                     False,
                'voter_campaignx_supporter':                {},
                'voter_can_send_updates_to_campaignx':      False,
                'voter_is_campaignx_owner':                 False,
                'voter_signed_in_with_email':               voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url':  '',
                'we_vote_hosted_campaign_photo_medium_url': '',
                'we_vote_hosted_campaign_photo_small_url':  '',
            }
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
            'is_supporters_count_minimum_exceeded': False,
            'seo_friendly_path':                '',
            'seo_friendly_path_list':           seo_friendly_path_list,
            'supporters_count':                 0,
            'supporters_count_next_goal':       0,
            'supporters_count_victory_goal':    0,
            'visible_on_this_site':             False,
            'voter_campaignx_supporter':        {},
            'voter_can_send_updates_to_campaignx': False,
            'voter_is_campaignx_owner':         False,
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
            'final_election_date_as_integer':   None,
            'final_election_date_in_past':      False,
            'in_draft_mode':                    True,
            'is_blocked_by_we_vote':            False,
            'is_blocked_by_we_vote_reason':     '',
            'is_supporters_count_minimum_exceeded': False,
            'seo_friendly_path':                '',
            'seo_friendly_path_list':           seo_friendly_path_list,
            'supporters_count':                 0,
            'supporters_count_next_goal':       0,
            'supporters_count_victory_goal':    0,
            'visible_on_this_site':             False,
            'voter_campaignx_supporter':        {},
            'voter_can_send_updates_to_campaignx': False,
            'voter_is_campaignx_owner':         False,
            'voter_signed_in_with_email':       voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url':  '',
            'we_vote_hosted_campaign_photo_medium_url': '',
            'we_vote_hosted_campaign_photo_small_url': '',
        }
        return results

    campaignx = results['campaignx']
    campaignx_owner_list = results['campaignx_owner_list']
    seo_friendly_path_list = results['seo_friendly_path_list']

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

    voter_can_send_updates_campaignx_we_vote_ids = \
        campaignx_manager.retrieve_voter_can_send_updates_campaignx_we_vote_ids(
            voter_we_vote_id=voter_we_vote_id,
        )

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

    # Get most recent supporters
    latest_campaignx_supporter_list = []
    supporter_list_results = campaignx_manager.retrieve_campaignx_supporter_list(
        campaignx_we_vote_id=campaignx.we_vote_id,
        limit=7,
        read_only=True,
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
    results = {
        'status':                           status,
        'success':                          True,
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
        'seo_friendly_path':                campaignx.seo_friendly_path,
        'seo_friendly_path_list':           seo_friendly_path_list,
        'supporters_count':                 campaignx.supporters_count,
        'supporters_count_next_goal':       supporters_count_next_goal,
        'supporters_count_victory_goal':    campaignx.supporters_count_victory_goal,
        'visible_on_this_site':             campaignx.visible_on_this_site,
        'voter_campaignx_supporter':        voter_campaignx_supporter_dict,
        'voter_can_send_updates_to_campaignx':
            campaignx.we_vote_id in voter_can_send_updates_campaignx_we_vote_ids,
        'voter_can_vote_for_politician_we_vote_ids': voter_can_vote_for_politician_we_vote_ids,
        'voter_is_campaignx_owner':         voter_is_campaignx_owner,
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
        campaign_photo_delete=False,
        campaign_photo_delete_changed=False,
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
            'status':                               status,
            'success':                              False,
            'campaign_description':                 '',
            'campaign_title':                       '',
            'final_election_date_as_integer':       None,
            'final_election_date_in_past':          False,
            'in_draft_mode':                        True,
            'is_blocked_by_we_vote':                False,
            'is_blocked_by_we_vote_reason':         '',
            'is_supporters_count_minimum_exceeded': False,
            'campaignx_owner_list':                 campaignx_owner_list,
            'campaignx_politician_list':            [],
            'campaignx_politician_list_exists':     False,
            'campaignx_politician_starter_list':    campaignx_politician_starter_list,
            'campaignx_we_vote_id':                 '',
            'seo_friendly_path':                    '',
            'seo_friendly_path_list':               seo_friendly_path_list,
            'supporters_count':                     0,
            'supporters_count_next_goal':           0,
            'supporters_count_victory_goal':        0,
            'visible_on_this_site':                 False,
            'voter_can_send_updates_to_campaignx':  False,
            'voter_is_campaignx_owner':             False,
            'voter_signed_in_with_email':           voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url': '',
            'we_vote_hosted_campaign_photo_medium_url': '',
            'we_vote_hosted_campaign_photo_small_url': '',
        }
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
            status += "MUST_BE_SIGNED_IN_WITH_EMAIL "
            results = {
                'status':                               status,
                'success':                              False,
                'campaign_description':                 '',
                'campaign_title':                       '',
                'campaignx_owner_list':                 campaignx_owner_list,
                'campaignx_politician_list':            [],
                'campaignx_politician_list_exists':     False,
                'campaignx_politician_starter_list':    campaignx_politician_starter_list,
                'campaignx_we_vote_id':                 '',
                'final_election_date_as_integer':       None,
                'final_election_date_in_past':          False,
                'in_draft_mode':                        True,
                'is_blocked_by_we_vote':                False,
                'is_blocked_by_we_vote_reason':         '',
                'is_supporters_count_minimum_exceeded': False,
                'seo_friendly_path':                    '',
                'seo_friendly_path_list':               seo_friendly_path_list,
                'supporters_count':                     0,
                'supporters_count_next_goal':           0,
                'supporters_count_victory_goal':        0,
                'visible_on_this_site':                 False,
                'voter_can_send_updates_to_campaignx':  False,
                'voter_is_campaignx_owner':             False,
                'voter_signed_in_with_email':           voter_signed_in_with_email,
                'we_vote_hosted_campaign_photo_large_url': '',
                'we_vote_hosted_campaign_photo_medium_url': '',
                'we_vote_hosted_campaign_photo_small_url': '',
            }
            return results

    campaignx_manager = CampaignXManager()
    viewer_is_owner = False
    if positive_value_exists(campaignx_we_vote_id):
        viewer_is_owner = campaignx_manager.is_voter_campaignx_owner(
            campaignx_we_vote_id=campaignx_we_vote_id, voter_we_vote_id=voter_we_vote_id)
        if not positive_value_exists(viewer_is_owner):
            status += "VOTER_IS_NOT_OWNER_OF_CAMPAIGNX "
            results = {
                'status':                               status,
                'success':                              False,
                'campaign_description':                 '',
                'campaign_title':                       '',
                'campaignx_owner_list':                 campaignx_owner_list,
                'campaignx_politician_list':            [],
                'campaignx_politician_list_exists':     False,
                'campaignx_politician_starter_list':    campaignx_politician_starter_list,
                'campaignx_we_vote_id':                 '',
                'final_election_date_as_integer':       None,
                'final_election_date_in_past':          False,
                'in_draft_mode':                        False,
                'is_blocked_by_we_vote':                False,
                'is_blocked_by_we_vote_reason':         '',
                'is_supporters_count_minimum_exceeded': False,
                'seo_friendly_path':                    '',
                'seo_friendly_path_list':               seo_friendly_path_list,
                'supporters_count':                     0,
                'supporters_count_next_goal':           0,
                'supporters_count_victory_goal':        0,
                'visible_on_this_site':                 False,
                'voter_can_send_updates_to_campaignx':  False,
                'voter_is_campaignx_owner':             False,
                'voter_signed_in_with_email':           voter_signed_in_with_email,
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

        voter_can_send_updates_campaignx_we_vote_ids = \
            campaignx_manager.retrieve_voter_can_send_updates_campaignx_we_vote_ids(
                voter_we_vote_id=voter_we_vote_id,
            )

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
        supporters_count_next_goal = campaignx_manager.fetch_supporters_count_next_goal(
            supporters_count=campaignx.supporters_count,
            supporters_count_victory_goal=campaignx.supporters_count_victory_goal)
        final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
        final_election_date_in_past = \
            final_election_date_plus_cool_down >= campaignx.final_election_date_as_integer \
            if positive_value_exists(campaignx.final_election_date_as_integer) else False
        results = {
            'status':                               status,
            'success':                              success,
            'campaign_description':                 campaignx.campaign_description,
            'campaign_title':                       campaignx.campaign_title,
            'campaignx_owner_list':                 campaignx_owner_list,
            'campaignx_politician_list':            campaignx_politician_list_modified,
            'campaignx_politician_list_exists':     campaignx_politician_list_exists,
            'campaignx_politician_starter_list':    campaignx_politician_starter_list,
            'campaignx_we_vote_id':                 campaignx.we_vote_id,
            'final_election_date_as_integer':       campaignx.final_election_date_as_integer,
            'final_election_date_in_past':          final_election_date_in_past,
            'in_draft_mode':                        campaignx.in_draft_mode,
            'is_blocked_by_we_vote':                campaignx.is_blocked_by_we_vote,
            'is_blocked_by_we_vote_reason':         campaignx.is_blocked_by_we_vote_reason,
            'is_supporters_count_minimum_exceeded': campaignx.is_supporters_count_minimum_exceeded(),
            'seo_friendly_path':                    campaignx.seo_friendly_path,
            'seo_friendly_path_list':               seo_friendly_path_list,
            'supporters_count':                     campaignx.supporters_count,
            'supporters_count_next_goal':           supporters_count_next_goal,
            'supporters_count_victory_goal':        campaignx.supporters_count_victory_goal,
            'visible_on_this_site':                 visible_on_this_site,
            'voter_can_send_updates_to_campaignx':
                campaignx.we_vote_id in voter_can_send_updates_campaignx_we_vote_ids,
            'voter_is_campaignx_owner':             viewer_is_owner,
            'voter_signed_in_with_email':           voter_signed_in_with_email,
            'we_vote_hosted_campaign_photo_large_url': campaignx.we_vote_hosted_campaign_photo_large_url,
            'we_vote_hosted_campaign_photo_medium_url': we_vote_hosted_campaign_photo_medium_url,
            'we_vote_hosted_campaign_photo_small_url': we_vote_hosted_campaign_photo_small_url,
        }
        return results
    else:
        status += "CAMPAIGNX_SAVE_ERROR "
        results = {
            'status':                               status,
            'success':                              False,
            'campaign_description':                 '',
            'campaign_title':                       '',
            'campaignx_owner_list':                 [],
            'campaignx_politician_list':            [],
            'campaignx_politician_list_exists':     False,
            'campaignx_politician_starter_list':    [],
            'campaignx_we_vote_id':                 '',
            'in_draft_mode':                        True,
            'seo_friendly_path':                    '',
            'seo_friendly_path_list':               [],
            'supporters_count':                     0,
            'supporters_count_next_goal':           0,
            'supporters_count_victory_goal':        0,
            'visible_on_this_site':                 False,
            'voter_can_send_updates_to_campaignx':  False,
            'voter_is_campaignx_owner':             False,
            'voter_signed_in_with_email':           voter_signed_in_with_email,
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
            'campaign_supported':           False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'id':                           '',
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
                'campaign_supported':           False,
                'campaignx_we_vote_id':         '',
                'date_last_changed':            '',
                'date_supported':               '',
                'id':                           '',
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
            'campaign_supported':           False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'id':                           '',
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

    if create_results['campaignx_supporter_found']:
        campaignx_supporter = create_results['campaignx_supporter']
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            read_only=True,
        )
        statement_text = ''
        if results['campaignx_found']:
            campaignx = results['campaignx']
            statement_text = campaignx.campaign_title

        activity_results = update_or_create_activity_notice_seed_for_campaignx_supporter_initial_response(
            campaignx_we_vote_id=campaignx_supporter.campaignx_we_vote_id,
            visibility_is_public=campaignx_supporter.visible_to_public,
            speaker_name=campaignx_supporter.supporter_name,
            speaker_organization_we_vote_id=campaignx_supporter.organization_we_vote_id,
            speaker_voter_we_vote_id=campaignx_supporter.voter_we_vote_id,
            speaker_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
            speaker_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny,
            statement_text=statement_text)
        status += activity_results['status']

    status += create_results['status']
    if create_results['campaignx_supporter_found']:
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
        results = {
            'status':                       status,
            'success':                      False,
            'campaign_supported':           False,
            'campaignx_we_vote_id':         '',
            'date_last_changed':            '',
            'date_supported':               '',
            'id':                           '',
            'organization_we_vote_id':      '',
            'supporter_endorsement':        '',
            'supporter_name':               '',
            'visible_to_public':            True,
            'voter_we_vote_id':             '',
            'voter_signed_in_with_email':   voter_signed_in_with_email,
            'we_vote_hosted_profile_photo_image_url_tiny': '',
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

    # ######################
    # Move News Item based on voter_we_vote_id
    try:
        campaignx_news_item_entries_moved += CampaignXNewsItem.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CAMPAIGNX_NEWS_ITEM_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "

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
            status += "FAILED-CAMPAIGNX_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
        try:
            campaignx_supporter_entries_moved += CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
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
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'campaignx_entries_moved':          campaignx_owner_entries_moved,
        'campaignx_owner_entries_moved':    campaignx_owner_entries_moved,
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
