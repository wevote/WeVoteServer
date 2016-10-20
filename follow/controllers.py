# follow/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FollowOrganizationList, FollowOrganizationManager
from django.http import HttpResponse
from email_outbound.models import EmailManager
import json
import wevote_functions.admin
from wevote_functions.functions import generate_voter_device_id, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def move_follow_entries_to_another_voter(from_voter_id, to_voter_id, to_voter_we_vote_id):
    status = ''
    success = False
    follow_entries_moved = 0
    follow_entries_not_moved = 0
    follow_organization_list = FollowOrganizationList()
    follow_organization_manager = FollowOrganizationManager()
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_voter_id(from_voter_id)

    for from_follow_entry in from_follow_list:
        # See if the "to_voter" already has an entry for this organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, to_voter_id, from_follow_entry.organization_id, from_follow_entry.organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            # Change the voter_id and voter_we_vote_id
            try:
                from_follow_entry.voter_id = to_voter_id
                # We don't currently store follow entries by we_vote_id
                # from_follow_entry.voter_we_vote_id = to_voter_we_vote_id
                from_follow_entry.save()
                follow_entries_moved += 1
            except Exception as e:
                follow_entries_not_moved += 1

    results = {
        'status': status,
        'success': success,
        'from_voter_id': from_voter_id,
        'to_voter_id': to_voter_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'follow_entries_moved': follow_entries_moved,
        'follow_entries_not_moved': follow_entries_not_moved,
    }
    return results


def move_organization_followers_to_another_organization(from_organization_id, from_organization_we_vote_id,
                                                        to_organization_id, to_organization_we_vote_id):
    status = ''
    success = False
    follow_entries_moved = 0
    follow_entries_not_moved = 0
    follow_organization_list = FollowOrganizationList()
    follow_organization_manager = FollowOrganizationManager()

    # We search on both from_organization_id and from_organization_we_vote_id in case there is some data that needs
    # to be healed
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_id(from_organization_id)
    for from_follow_entry in from_follow_list:
        # See if the "to_voter" already has an entry for the to_organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, from_follow_entry.voter_id, to_organization_id, to_organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            # Change the voter_id and voter_we_vote_id
            try:
                from_follow_entry.organization_id = to_organization_id
                from_follow_entry.organization_we_vote_id = to_organization_we_vote_id
                from_follow_entry.save()
                follow_entries_moved += 1
            except Exception as e:
                follow_entries_not_moved += 1

    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_we_vote_id(
        from_organization_we_vote_id)
    for from_follow_entry in from_follow_list:
        # See if the "to_voter" already has an entry for the to_organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, from_follow_entry.voter_id, to_organization_id, to_organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            # Change the voter_id and voter_we_vote_id
            try:
                from_follow_entry.organization_id = to_organization_id
                from_follow_entry.organization_we_vote_id = to_organization_we_vote_id
                from_follow_entry.save()
                follow_entries_moved += 1
            except Exception as e:
                follow_entries_not_moved += 1

    results = {
        'status': status,
        'success': success,
        'from_organization_id': from_organization_id,
        'from_organization_we_vote_id': from_organization_we_vote_id,
        'to_organization_id': to_organization_id,
        'to_organization_we_vote_id': to_organization_we_vote_id,
        'follow_entries_moved': follow_entries_moved,
        'follow_entries_not_moved': follow_entries_not_moved,
    }
    return results
