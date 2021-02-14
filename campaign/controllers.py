# campaign/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CampaignX, CampaignXManager
from django.db.models import Q
from django.http import HttpResponse
import json
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


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
                'campaign_title':                   '',
                'in_draft_mode':                    True,
                'campaignx_owner_list':             campaignx_owner_list,
                'campaignx_politician_list':        campaignx_politician_list,
                'campaignx_we_vote_id':             '',
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
            'campaign_title':                   '',
            'in_draft_mode':                    True,
            'campaignx_owner_list':             campaignx_owner_list,
            'campaignx_politician_list':        campaignx_politician_list,
            'campaignx_we_vote_id':             '',
        }
        return results
    elif not results['campaignx_found']:
        status += "CAMPAIGNX_NOT_FOUND: "
        status += results['status'] + " "
        results = {
            'status':                           status,
            'success':                          True,
            'campaign_title':                   '',
            'in_draft_mode':                    True,
            'campaignx_owner_list':             campaignx_owner_list,
            'campaignx_politician_list':        campaignx_politician_list,
            'campaignx_we_vote_id':             '',
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
        'campaign_title':                   campaignx.campaign_title,
        'in_draft_mode':                    campaignx.in_draft_mode,
        'campaignx_owner_list':             campaignx_owner_list,
        'campaignx_politician_list':        campaignx_politician_list,
        'campaignx_we_vote_id':             campaignx.we_vote_id,
    }
    return results


def campaignx_save_for_api(  # campaignSave & campaignStartSave
        voter_device_id='',
        campaignx_we_vote_id='',
        politician_list_serialized='',
        politician_list_changed=False,
        campaign_title='',
        campaign_title_changed=False):
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
            'campaign_title':               '',
            'in_draft_mode':                True,
            'campaignx_owner_list':         campaignx_owner_list,
            'campaignx_politician_list':    campaignx_politician_list,
            'campaignx_we_vote_id':         '',
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
                'campaign_title':               '',
                'in_draft_mode':                False,
                'campaignx_owner_list':         campaignx_owner_list,
                'campaignx_politician_list':    campaignx_politician_list,
                'campaignx_we_vote_id':         '',
            }
            return results
        update_values = {
            'campaign_title':               campaign_title,
            'campaign_title_changed':       campaign_title_changed,
            'politician_list_changed':      politician_list_changed,
            'politician_list_serialized':   politician_list_serialized,
        }
        create_results = campaignx_manager.update_or_create_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=linked_organization_we_vote_id,
            update_values=update_values,
        )
    else:
        # If here, we are working with a draft
        update_values = {
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
            'campaign_title':               '',
            'in_draft_mode':                True,
            'campaignx_owner_list':         [],
            'campaignx_politician_list':    [],
            'campaignx_we_vote_id':         '',
            'voter_we_vote_id':             voter_we_vote_id,
        }
        return results
