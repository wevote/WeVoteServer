# follow/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import copy
import robot_detection
from django.db.models import Q

from .models import FollowOrganization, FollowOrganizationList, FollowOrganizationManager, \
    UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, FOLLOW_DISLIKE, FOLLOWING, \
    FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, FollowIssueList, FollowIssueManager, FollowMetricsManager
from analytics.models import ACTION_ISSUE_FOLLOW, ACTION_ISSUE_FOLLOW_IGNORE, \
    ACTION_ISSUE_STOP_FOLLOWING, AnalyticsManager
from campaign.controllers import refresh_campaignx_supporters_count_in_all_children
from campaign.models import CampaignXManager
from friend.models import FriendManager
from organization.models import Organization, OrganizationManager
from politician.models import Politician
from position.models import OPPOSE, PositionEntered, PositionForFriends, SUPPORT
from twitter.models import TwitterUserManager
from voter.models import VoterManager, fetch_voter_we_vote_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def delete_follow_entries_for_voter(voter_to_delete_id):
    status = ''
    success = True
    follow_entries_deleted = 0
    follow_entries_not_deleted = 0

    if not positive_value_exists(voter_to_delete_id):
        status += "DELETE_FOLLOW_ENTRIES-Missing voter_to_delete_id "
        results = {
            'status':                   status,
            'success':                  success,
            'voter_to_delete_id':            voter_to_delete_id,
            'follow_entries_deleted':     follow_entries_deleted,
            'follow_entries_not_deleted': follow_entries_not_deleted,
        }
        return results

    follow_organization_list = FollowOrganizationList()
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_voter_id(voter_to_delete_id)

    for from_follow_entry in from_follow_list:
        try:
            from_follow_entry.delete()
            follow_entries_deleted += 1
        except Exception as e:
            follow_entries_not_deleted += 1
            status += "FAILED_DELETING_FROM_FOLLOW_ENTRY: " + str(e) + ' '
            success = False

    results = {
        'status':                       status,
        'success':                      success,
        'voter_to_delete_id':           voter_to_delete_id,
        'follow_entries_deleted':       follow_entries_deleted,
        'follow_entries_not_deleted':   follow_entries_not_deleted,
    }
    return results


def delete_follow_issue_entries_for_voter(voter_to_delete_we_vote_id):
    status = ''
    success = True
    follow_issue_entries_deleted = 0
    follow_issue_entries_not_deleted = 0
    follow_issue_list = FollowIssueList()

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_FOLLOW_ISSUE_ENTRIES_FOR_VOTER-Missing voter_to_delete_we_vote_id "
        results = {
            'status': status,
            'success': success,
            'voter_to_delete_we_vote_id': voter_to_delete_we_vote_id,
            'follow_issue_entries_deleted': follow_issue_entries_deleted,
            'follow_issue_entries_not_deleted': follow_issue_entries_not_deleted,
        }
        return results

    from_follow_issue_list = follow_issue_list.retrieve_follow_issue_list_by_voter_we_vote_id(
        voter_to_delete_we_vote_id, read_only=False)

    for from_follow_issue_entry in from_follow_issue_list:
        try:
            from_follow_issue_entry.delete()
            follow_issue_entries_deleted += 1
        except Exception as e:
            follow_issue_entries_not_deleted += 1
            status += "FAILED_FROM_FOLLOW_ISSUE_DELETE: " + str(e) + " "
            success = False

    results = {
        'status':                           status,
        'success':                          success,
        'voter_to_delete_we_vote_id':       voter_to_delete_we_vote_id,
        'follow_issue_entries_deleted':     follow_issue_entries_deleted,
        'follow_issue_entries_not_deleted': follow_issue_entries_not_deleted,
    }
    return results


def delete_organization_followers_for_organization(from_organization_id, from_organization_we_vote_id):
    status = ''
    success = True
    follow_entries_deleted = 0
    follow_entries_not_deleted = 0
    follow_organization_list = FollowOrganizationList()

    # We search on both from_organization_id and from_organization_we_vote_id in case there is some data that needs
    # to be healed
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_id(from_organization_id)
    for from_follow_entry in from_follow_list:
        try:
            from_follow_entry.delete()
            follow_entries_deleted += 1
        except Exception as e:
            follow_entries_not_deleted += 1
            status += "FAILED_DELETING_FROM_FOLLOW_ENTRY_BY_ID: " + str(e) + ' '
            success = False

    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_we_vote_id(
        from_organization_we_vote_id, read_only=False)
    for from_follow_entry in from_follow_list:
        try:
            from_follow_entry.delete()
            follow_entries_deleted += 1
        except Exception as e:
            follow_entries_not_deleted += 1
            status += "FAILED_DELETING_FROM_FOLLOW_ENTRY_BY_WE_VOTE_ID: " + str(e) + ' '
            success = False

    results = {
        'status':                       status,
        'success':                      success,
        'from_organization_id':         from_organization_id,
        'from_organization_we_vote_id': from_organization_we_vote_id,
        'follow_entries_deleted':       follow_entries_deleted,
        'follow_entries_not_deleted':   follow_entries_not_deleted,
    }
    return results


def duplicate_follow_entries_to_another_voter(from_voter_id, from_voter_we_vote_id, to_voter_id, to_voter_we_vote_id):
    status = ''
    success = True
    follow_entries_duplicated = 0
    follow_entries_not_duplicated = 0
    organization_manager = OrganizationManager()
    voter_manager = VoterManager()
    follow_organization_list = FollowOrganizationList()
    follow_organization_manager = FollowOrganizationManager()
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_voter_id(from_voter_id)

    voter_linked_organization_we_vote_id = \
        voter_manager.fetch_linked_organization_we_vote_id_from_local_id(to_voter_id)

    for from_follow_entry in from_follow_list:
        heal_data = False
        # See if we need to heal the data
        if not positive_value_exists(from_follow_entry.organization_we_vote_id):
            from_follow_entry.organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(
                from_follow_entry.organization_id)
            heal_data = True
        if not positive_value_exists(from_follow_entry.organization_we_vote_id_that_is_following):
            from_follow_entry.organization_we_vote_id_that_is_following = \
                voter_manager.fetch_linked_organization_we_vote_id_from_local_id(from_voter_id)
            heal_data = True

        if heal_data:
            try:
                from_follow_entry.save()
            except Exception as e:
                status += "FAILED_SAVING_FROM_FOLLOW_HEALED_DATA: " + str(e) + ' '
                success = False

        # See if the "to_voter" already has an entry for this organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, to_voter_id, from_follow_entry.organization_id, from_follow_entry.organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            # Change the voter_id and organization_we_vote_id_that_is_following, and then save a new entry.
            #  This will not overwrite existing from_follow_entry.
            try:
                from_follow_entry.id = None  # Reset the id so a new entry is created
                from_follow_entry.pk = None
                from_follow_entry.voter_id = to_voter_id
                # We don't currently store follow entries by we_vote_id
                from_follow_entry.organization_we_vote_id_that_is_following = voter_linked_organization_we_vote_id
                from_follow_entry.save()
                follow_entries_duplicated += 1
            except Exception as e:
                follow_entries_not_duplicated += 1
                status += "FAILED_SAVING_FROM_FOLLOW_UPDATED_DATA: " + str(e) + ' '
                success = False

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_id':                    from_voter_id,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_id':                      to_voter_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'follow_entries_duplicated':        follow_entries_duplicated,
        'follow_entries_not_duplicated':    follow_entries_not_duplicated,
    }
    return results


def duplicate_follow_issue_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    follow_issue_entries_duplicated = 0
    follow_issue_entries_not_duplicated = 0
    follow_issue_list = FollowIssueList()
    from_follow_issue_list = follow_issue_list.retrieve_follow_issue_list_by_voter_we_vote_id(from_voter_we_vote_id)
    to_follow_issue_we_vote_id_list = \
        follow_issue_list.retrieve_follow_issue_we_vote_id_list_by_voter_we_vote_id(to_voter_we_vote_id)

    for from_follow_issue_entry in from_follow_issue_list:
        # See if the "to_voter" already has an entry for this issue
        if from_follow_issue_entry.issue_we_vote_id not in to_follow_issue_we_vote_id_list:
            # Change the from_voter_we_vote_id to to_voter_we_vote_id
            try:
                from_follow_issue_entry.id = None  # Reset the id so a new entry is created
                from_follow_issue_entry.pk = None
                from_follow_issue_entry.voter_we_vote_id = to_voter_we_vote_id
                from_follow_issue_entry.save()
                follow_issue_entries_duplicated += 1
            except Exception as e:
                follow_issue_entries_not_duplicated += 1
                status += "FAILED_SAVING_FROM_FOLLOW_ISSUE: " + str(e) + ' '
                success = False
    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'follow_issue_entries_duplicated':  follow_issue_entries_duplicated,
        'follow_issue_entries_not_duplicated':  follow_issue_entries_not_duplicated,
    }
    return results


def move_follow_entries_to_another_voter(from_voter_id=0, to_voter_id=0, to_voter_we_vote_id=''):
    status = ''
    success = True
    follow_entries_moved = 0
    follow_entries_not_moved = 0

    if not positive_value_exists(from_voter_id) or not positive_value_exists(to_voter_id):
        status += "MOVE_FOLLOW_ENTRIES_TO_ANOTHER_VOTER-Missing either from_voter_id or to_voter_id "
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_id':            from_voter_id,
            'to_voter_id':              to_voter_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'follow_entries_moved':     follow_entries_moved,
            'follow_entries_not_moved': follow_entries_not_moved,
        }
        return results

    if from_voter_id == to_voter_id:
        status += "MOVE_FOLLOW_ENTRIES_TO_ANOTHER_VOTER-from_voter_id and to_voter_id identical "
        results = {
            'status':                   status,
            'success':                  success,
            'from_voter_id':            from_voter_id,
            'to_voter_id':              to_voter_id,
            'to_voter_we_vote_id':      to_voter_we_vote_id,
            'follow_entries_moved':     follow_entries_moved,
            'follow_entries_not_moved': follow_entries_not_moved,
        }
        return results

    follow_organization_list = FollowOrganizationList()
    try:
        organization_we_vote_ids_followed = \
            follow_organization_list.retrieve_follow_organization_by_voter_id_simple_id_array(
                voter_id=to_voter_id,
                return_we_vote_id=True,
            )
    except Exception as e:
        organization_we_vote_ids_followed = []
        status += "FOLLOW_ORGANIZATION_RETRIEVE_FAILED: " + str(e) + " "
        success = False

    if success:
        move_results = follow_organization_list.move_follow_organization_from_voter_id_to_new_voter_id(
            from_voter_id=from_voter_id,
            to_voter_id=to_voter_id,
            exclude_organization_we_vote_id_list=organization_we_vote_ids_followed,
        )
        follow_entries_moved = move_results['number_moved']

        if move_results['success']:
            # Finally, delete remaining FollowOrganization entries for from_voter_id
            delete_results = \
                follow_organization_list.delete_follow_organization_list_for_voter_id(voter_id=from_voter_id)
            if not delete_results['success']:
                status += delete_results['status']
                success = False
            follow_entries_not_moved = delete_results['number_deleted']
        else:
            success = False

    results = {
        'status':                   status,
        'success':                  success,
        'from_voter_id':            from_voter_id,
        'to_voter_id':              to_voter_id,
        'to_voter_we_vote_id':      to_voter_we_vote_id,
        'follow_entries_moved':     follow_entries_moved,
        'follow_entries_not_moved': follow_entries_not_moved,
    }
    return results


def move_follow_issue_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    follow_issue_entries_moved = 0
    follow_issue_entries_not_moved = 0
    follow_issue_list = FollowIssueList()

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_FOLLOW_ISSUE_ENTRIES_TO_ANOTHER_VOTER-" \
                  "Missing either from_voter_we_vote_id or to_voter_we_vote_id "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'follow_issue_entries_moved': follow_issue_entries_moved,
            'follow_issue_entries_not_moved': follow_issue_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_FOLLOW_ISSUE_ENTRIES_TO_ANOTHER_VOTER-from_voter_we_vote_id and to_voter_we_vote_id identical "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'follow_issue_entries_moved': follow_issue_entries_moved,
            'follow_issue_entries_not_moved': follow_issue_entries_not_moved,
        }
        return results

    from_follow_issue_list = follow_issue_list.retrieve_follow_issue_list_by_voter_we_vote_id(
        from_voter_we_vote_id, read_only=False)
    to_follow_issue_list = follow_issue_list.retrieve_follow_issue_list_by_voter_we_vote_id(
        to_voter_we_vote_id, read_only=False)
    to_follow_issue_we_vote_id_list = \
        follow_issue_list.retrieve_follow_issue_we_vote_id_list_by_voter_we_vote_id(to_voter_we_vote_id)

    for from_follow_issue_entry in from_follow_issue_list:
        # See if the "to_voter" already has an entry for this issue
        if from_follow_issue_entry.issue_we_vote_id in to_follow_issue_we_vote_id_list:
            # Find the entry in the to_follow_issue_list
            for to_follow_issue_entry in to_follow_issue_list:
                if to_follow_issue_entry.issue_we_vote_id == from_follow_issue_entry.issue_we_vote_id:
                    # Change the following status if it is not already FOLLOWING
                    if to_follow_issue_entry.following_status == FOLLOWING:
                        # If the to_voter entry is already FOLLOWING, leave it
                        continue
                    else:
                        # Update the to_follow_issue_entry with the following_status
                        try:
                            to_follow_issue_entry.following_status = from_follow_issue_entry.following_status
                            to_follow_issue_entry.save()
                            follow_issue_entries_moved += 1
                        except Exception as e:
                            follow_issue_entries_not_moved += 1
                            status += "FAILED_TO_FOLLOW_ISSUE_SAVE: " + str(e) + " "
                            success = False
                        continue

        else:
            # Change the from_voter_we_vote_id to to_voter_we_vote_id
            try:
                from_follow_issue_entry.voter_we_vote_id = to_voter_we_vote_id
                # We don't currently store follow entries by we_vote_id
                # from_follow_issue_entry.voter_we_vote_id = to_voter_we_vote_id
                from_follow_issue_entry.save()
                follow_issue_entries_moved += 1
            except Exception as e:
                follow_issue_entries_not_moved += 1
                status += "FAILED_FROM_FOLLOW_ISSUE_SAVE: " + str(e) + " "
                success = False

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'follow_issue_entries_moved':       follow_issue_entries_moved,
        'follow_issue_entries_not_moved':   follow_issue_entries_not_moved,
    }
    return results


def duplicate_organization_followers_to_another_organization(from_organization_id, from_organization_we_vote_id,
                                                             to_organization_id, to_organization_we_vote_id):
    status = ''
    success = True
    follow_entries_duplicated = 0
    follow_entries_not_duplicated = 0
    voter_manager = VoterManager()
    organization_manager = OrganizationManager()
    follow_organization_list = FollowOrganizationList()
    follow_organization_manager = FollowOrganizationManager()

    # We search on both from_organization_id and from_organization_we_vote_id in case there is some data that needs
    # to be healed
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_id(from_organization_id)
    for from_follow_entry in from_follow_list:
        heal_data = False
        # See if we need to heal the data
        if not positive_value_exists(from_follow_entry.organization_we_vote_id):
            from_follow_entry.organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(
                from_follow_entry.organization_id)
            heal_data = True

        if heal_data:
            try:
                from_follow_entry.save()
            except Exception as e:
                status += "FAILED_DELETING_FOLLOW_ENTRY: " + str(e) + " "
                success = False

        # See if the "to_voter" already has an entry for the to_organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, from_follow_entry.voter_id, to_organization_id, to_organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            try:
                from_follow_entry.id = None  # Reset the id so a new entry is created
                from_follow_entry.pk = None
                from_follow_entry.organization_id = to_organization_id
                from_follow_entry.organization_we_vote_id = to_organization_we_vote_id
                from_follow_entry.save()
                follow_entries_duplicated += 1
            except Exception as e:
                follow_entries_not_duplicated += 1
                status += "FAILED_ADJUSTING_FOLLOW_ENTRY: " + str(e) + " "
                success = False

    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_we_vote_id(
        from_organization_we_vote_id, read_only=False)
    for from_follow_entry in from_follow_list:
        heal_data = False
        # See if we need to heal the data
        if not positive_value_exists(from_follow_entry.organization_we_vote_id):
            from_follow_entry.organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(
                from_follow_entry.organization_id)
            heal_data = True

        if heal_data:
            try:
                from_follow_entry.save()
            except Exception as e:
                status += "FAILED_SAVING_FROM_FOLLOW_ENTRY: " + str(e) + " "
                success = False

        # See if the "to_voter" already has an entry for the to_organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, from_follow_entry.voter_id, to_organization_id, to_organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            try:
                from_follow_entry.id = None  # Reset the id so a new entry is created
                from_follow_entry.pk = None
                from_follow_entry.organization_id = to_organization_id
                from_follow_entry.organization_we_vote_id = to_organization_we_vote_id
                from_follow_entry.save()
                follow_entries_duplicated += 1
            except Exception as e:
                follow_entries_not_duplicated += 1
                status += "FAILED_ADJUSTING_FROM_FOLLOW_ENTRY: " + str(e) + " "
                success = False

    results = {
        'status':                           status,
        'success':                          success,
        'from_organization_id':             from_organization_id,
        'from_organization_we_vote_id':     from_organization_we_vote_id,
        'to_organization_id':               to_organization_id,
        'to_organization_we_vote_id':       to_organization_we_vote_id,
        'follow_entries_duplicated':        follow_entries_duplicated,
        'follow_entries_not_duplicated':    follow_entries_not_duplicated,
    }
    return results


def voter_campaignx_follow_for_api(voter_device_id, issue_we_vote_id, follow_value, ignore_value,
                                   user_agent_string, user_agent_object):  # campaignFollow
    voter_we_vote_id = False
    voter_id = 0
    is_signed_in = False
    issue_id = ''
    if positive_value_exists(voter_device_id):
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_we_vote_id = voter.we_vote_id
            voter_id = voter.id
            if voter.is_signed_in():
                is_signed_in = True
    follow_issue_manager = FollowIssueManager()
    follow_metrics_manager = FollowMetricsManager()
    result = False
    is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
    analytics_manager = AnalyticsManager()
    if positive_value_exists(voter_we_vote_id) and positive_value_exists(issue_we_vote_id):
        if follow_value:
            result = follow_issue_manager.toggle_on_voter_following_issue(voter_we_vote_id, issue_id,
                                                                          issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_FOLLOW,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_pc,
                                                              is_tablet=user_agent_object.is_tablet)
        elif not follow_value:
            result = follow_issue_manager.toggle_off_voter_following_issue(voter_we_vote_id, issue_id,
                                                                           issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_STOP_FOLLOWING,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_pc,
                                                              is_tablet=user_agent_object.is_tablet)
        elif ignore_value:
            result = follow_issue_manager.toggle_ignore_voter_following_issue(voter_we_vote_id, issue_id,
                                                                              issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_FOLLOW_IGNORE,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_pc,
                                                              is_tablet=user_agent_object.is_tablet)

    if not result:
        new_result = {
            'success': False,
            'follow_issue_found': False,
        }
    else:
        if positive_value_exists(voter_we_vote_id):
            number_of_issues_followed = follow_metrics_manager.fetch_issues_followed(voter_we_vote_id)

            voter_manager = VoterManager()
            voter_manager.update_issues_interface_status(voter_we_vote_id, number_of_issues_followed)

        new_result = {
            'success': result['success'],
            'status': result['status'],
            'voter_device_id': voter_device_id,
            'issue_we_vote_id': issue_we_vote_id,
            'follow_value': follow_value,
            'ignore_value': ignore_value,
            'follow_issue_found': result['follow_issue_found'],
            'follow_issue_id': result['follow_issue_id'],
        }

    return new_result


def voter_issue_follow_for_api(voter_device_id, issue_we_vote_id, follow_value, ignore_value,
                               user_agent_string, user_agent_object):  # issueFollow
    voter_we_vote_id = False
    voter_id = 0
    is_signed_in = False
    issue_id = ''
    if positive_value_exists(voter_device_id):
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
        if voter_results['voter_found']:
            voter = voter_results['voter']
            voter_we_vote_id = voter.we_vote_id
            voter_id = voter.id
            if voter.is_signed_in():
                is_signed_in = True
    follow_issue_manager = FollowIssueManager()
    follow_metrics_manager = FollowMetricsManager()
    result = False
    is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
    analytics_manager = AnalyticsManager()
    if positive_value_exists(voter_we_vote_id) and positive_value_exists(issue_we_vote_id):
        if follow_value:
            result = follow_issue_manager.toggle_on_voter_following_issue(voter_we_vote_id, issue_id,
                                                                          issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_FOLLOW,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_pc,
                                                              is_tablet=user_agent_object.is_tablet)
        elif not follow_value:
            result = follow_issue_manager.toggle_off_voter_following_issue(voter_we_vote_id, issue_id,
                                                                           issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_STOP_FOLLOWING,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_pc,
                                                              is_tablet=user_agent_object.is_tablet)
        elif ignore_value:
            result = follow_issue_manager.toggle_ignore_voter_following_issue(voter_we_vote_id, issue_id,
                                                                              issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_FOLLOW_IGNORE,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_pc,
                                                              is_tablet=user_agent_object.is_tablet)

    if not result:
        new_result = {
            'success': False,
            'follow_issue_found': False,
        }
    else:
        if positive_value_exists(voter_we_vote_id):
            number_of_issues_followed = follow_metrics_manager.fetch_issues_followed(voter_we_vote_id)

            voter_manager = VoterManager()
            voter_manager.update_issues_interface_status(voter_we_vote_id, number_of_issues_followed)

        new_result = {
            'success': result['success'],
            'status': result['status'],
            'voter_device_id': voter_device_id,
            'issue_we_vote_id': issue_we_vote_id,
            'follow_value': follow_value,
            'ignore_value': ignore_value,
            'follow_issue_found': result['follow_issue_found'],
            'follow_issue_id': result['follow_issue_id'],
        }

    return new_result


def move_organization_followers_to_another_organization(from_organization_id, from_organization_we_vote_id,
                                                        to_organization_id, to_organization_we_vote_id):
    status = ''
    success = True
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
                status += "FAILED_SAVING_FROM_FOLLOW_ENTRY1: " + str(e) + ' '
                success = False

    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_we_vote_id(
        from_organization_we_vote_id, read_only=False)
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
                status += "FAILED_SAVING_FROM_FOLLOW_ENTRY2: " + str(e) + ' '
                success = False

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


def organization_suggestion_tasks_for_api(voter_device_id,
                                          kind_of_suggestion_task=UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW,
                                          kind_of_follow_task=''):  # organizationSuggestionTasks
    """
    organizationSuggestionTasks API Endpoint
    :param kind_of_suggestion_task:
    :type kind_of_follow_task:
    :param voter_device_id:
    :return:
    """
    success = False
    status = ''
    organization_suggestion_task_saved = False
    organization_suggestion_list = []
    organization_suggestion_followed_list = []

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        error_results = {
            'status':                                   results['status'],
            'success':                                  success,
            'voter_device_id':                          voter_device_id,
            'kind_of_suggestion_task':                  kind_of_suggestion_task,
            'kind_of_follow_task':                      kind_of_follow_task,
            'organization_suggestion_task_saved':       organization_suggestion_task_saved,
            'organization_suggestion_list':             organization_suggestion_list,
            'organization_suggestion_followed_list':    organization_suggestion_followed_list

        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                                  success,
            'voter_device_id':                          voter_device_id,
            'kind_of_suggestion_task':                  kind_of_suggestion_task,
            'kind_of_follow_task':                      kind_of_follow_task,
            'organization_suggestion_task_saved':       organization_suggestion_task_saved,
            'organization_suggestion_list':             organization_suggestion_list,
            'organization_suggestion_followed_list':    organization_suggestion_followed_list

        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    twitter_id_of_me = voter.twitter_id

    follow_organization_list = FollowOrganizationList()
    follow_organization_manager = FollowOrganizationManager()
    twitter_user_manager = TwitterUserManager()
    friend_manager = FriendManager()

    # Not getting twitter_id during first Calling from webapp due to which not geting suggestions from twitter who
    # i follow however successfully retrieved in second call
    if kind_of_suggestion_task == UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW:
        # If here, we want to
        # A) get all the twitter_ids of all twitter accounts I follow (on Twitter)
        # B) then check to see if any of those twitter accounts have voter guides on We Vote
        twitter_who_i_follow_list_results = twitter_user_manager.retrieve_twitter_who_i_follow_list(twitter_id_of_me)
        status += twitter_who_i_follow_list_results['status']
        success = twitter_who_i_follow_list_results['success']
        if twitter_who_i_follow_list_results['twitter_who_i_follow_list_found']:
            twitter_who_i_follow_list = twitter_who_i_follow_list_results['twitter_who_i_follow_list']
            for twitter_who_i_follow_entry in twitter_who_i_follow_list:
                # searching each twitter_id_i_follow in TwitterLinkToOrganization table
                twitter_id_i_follow = twitter_who_i_follow_entry.twitter_id_i_follow
                twitter_organization_retrieve_results = twitter_user_manager. \
                    retrieve_twitter_link_to_organization_from_twitter_user_id(twitter_id_i_follow)
                status += ' ' + twitter_organization_retrieve_results['status']
                success = twitter_organization_retrieve_results['success']
                if twitter_organization_retrieve_results['twitter_link_to_organization_found']:
                    twitter_link_to_organization = twitter_organization_retrieve_results['twitter_link_to_organization']
                    organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id
                    twitter_suggested_organization_updated_results = follow_organization_manager.\
                        update_or_create_suggested_organization_to_follow(voter_we_vote_id,
                                                                          organization_we_vote_id, from_twitter=True)
                    status += ' ' + twitter_suggested_organization_updated_results['status']
                    success = twitter_suggested_organization_updated_results['success']
                    if twitter_suggested_organization_updated_results['suggested_organization_to_follow_saved']:
                        twitter_suggested_organization_to_follow = twitter_suggested_organization_updated_results[
                            'suggested_organization_to_follow']
                        one_suggested_organization = {
                            "organization_we_vote_id": twitter_suggested_organization_to_follow.organization_we_vote_id,
                        }
                        organization_suggestion_list.append(one_suggested_organization)
    '''
    # Need to discuss and store friends in different table
    elif kind_of_suggestion_task == UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW:
        retrieve_current_friends_as_voters_results = friend_manager.retrieve_current_friends_as_voters(
            voter_we_vote_id)
        status += retrieve_current_friends_as_voters_results['status']
        success = retrieve_current_friends_as_voters_results['success']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friends_list = retrieve_current_friends_as_voters_results['friend_list']
            for current_friend_entry in current_friends_list:
                current_friend_voter_id = current_friend_entry.id
                follow_organization_list_results = follow_organization_list.\
                    retrieve_follow_organization_by_voter_id(current_friend_voter_id)
                for follow_organization_entry in follow_organization_list_results:
                    organization_we_vote_id = follow_organization_entry.organization_we_vote_id
                    suggested_organization_what_friend_follow_list = follow_organization_manager. \
                        update_or_create_suggested_organization_to_follow(voter_we_vote_id,
                                                                          organization_we_vote_id, from_twitter=False)
                    status += ' ' + suggested_organization_what_friend_follow_list['status']
                    success = suggested_organization_what_friend_follow_list['success']
                    if suggested_organization_what_friend_follow_list['suggested_organization_to_follow_saved']:
                        suggested_organization_what_friend_follow = suggested_organization_what_friend_follow_list[
                            'suggested_organization_to_follow']
                        one_suggested_organization = {
                            "organization_we_vote_id": suggested_organization_what_friend_follow.organization_we_vote_id
                        }
                        organization_suggestion_list.append(one_suggested_organization)
    # not tested yet
    elif kind_of_suggestion_task == UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER:
        retrieve_current_friends_as_voters_results = friend_manager.retrieve_current_friends_as_voters(
            voter_we_vote_id)
        status += retrieve_current_friends_as_voters_results['status']
        success = retrieve_current_friends_as_voters_results['success']
        if retrieve_current_friends_as_voters_results['friend_list_found']:
            current_friends_list = retrieve_current_friends_as_voters_results['friend_list']
            for current_friend_entry in current_friends_list:
                current_friend_twitter_id = current_friend_entry.twitter_id
                twitter_who_friend_follow_list_results = twitter_user_manager.retrieve_twitter_who_i_follow_list(
                    current_friend_twitter_id)
                status += twitter_who_friend_follow_list_results['status']
                success = twitter_who_friend_follow_list_results['success']
                if twitter_who_friend_follow_list_results['twitter_who_i_follow_list_found']:
                    twitter_who_friend_follow_list = twitter_who_friend_follow_list_results['twitter_who_i_follow_list']
                    for twitter_who_friend_follow_entry in twitter_who_friend_follow_list:
                        # searching each twitter_id_i_follow in TwitterLinkToOrganization table
                        twitter_id_friend_follow = twitter_who_friend_follow_entry.twitter_id_i_follow
                        twitter_organization_retrieve_results = twitter_user_manager. \
                            retrieve_twitter_link_to_organization_from_twitter_user_id(twitter_id_friend_follow)
                        status += ' ' + twitter_organization_retrieve_results['status']
                        success = twitter_organization_retrieve_results['success']
                        if twitter_organization_retrieve_results['twitter_link_to_organization_found']:
                            # organization_found = True
                            # twitter_who_i_follow_update_results = \
                            #    twitter_user_manager.create_twitter_who_i_follow_entries(
                            #    twitter_id_of_me, twitter_who_i_follow_entry.twitter_id_i_follow, organization_found)
                            # status = ' ' + twitter_who_i_follow_update_results['status']
                            twitter_link_to_organization = twitter_organization_retrieve_results[
                                'twitter_link_to_organization']
                            organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id
                            twitter_suggested_organization_updated_results = follow_organization_manager. \
                                update_or_create_suggested_organization_to_follow(voter_we_vote_id,
                                                                                  organization_we_vote_id, from_twitter=True)
                            status += ' ' + twitter_suggested_organization_updated_results['status']
                            success = twitter_suggested_organization_updated_results['success']
                            if twitter_suggested_organization_updated_results['suggested_organization_to_follow_saved']:
                                twitter_suggested_organization_to_follow = \
                                    twitter_suggested_organization_updated_results['suggested_organization_to_follow']
                                one_suggested_organization = {
                                    "organization_we_vote_id": twitter_suggested_organization_to_follow.
                                        organization_we_vote_id,
                                }
                                organization_suggestion_list.append(one_suggested_organization)
    '''
    # Not getting twitter_id during first Calling from webapp due to which not geting suggestions from twitter who
    # i follow however successfully retrieved in second call
    if kind_of_follow_task == FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW:
        # If here, we want to retrieve from the local database all the organizations that we are following on Twitter
        auto_followed_from_twitter_suggestion = True
        suggested_organization_to_follow_list_results = follow_organization_manager. \
            retrieve_suggested_organization_to_follow_list(voter_we_vote_id, auto_followed_from_twitter_suggestion)
        status += suggested_organization_to_follow_list_results['status']
        success = suggested_organization_to_follow_list_results['success']
        if suggested_organization_to_follow_list_results['suggested_organization_to_follow_list_found']:
            suggested_organization_to_follow_list = \
                suggested_organization_to_follow_list_results['suggested_organization_to_follow_list']
            for suggested_organization_to_follow_entry in suggested_organization_to_follow_list:
                organization_we_vote_id = suggested_organization_to_follow_entry.organization_we_vote_id
                toggle_on_results = follow_organization_manager.\
                    toggle_on_voter_following_organization(voter_id, 0, organization_we_vote_id,
                                                           voter_linked_organization_we_vote_id,
                                                           auto_followed_from_twitter_suggestion)
                status += ' ' + toggle_on_results['status']
                success = toggle_on_results['success']
                if toggle_on_results['follow_organization_found']:
                    follow_suggested_organization = toggle_on_results['follow_organization']
                    one_suggested_organization = {
                        "organization_we_vote_id": follow_suggested_organization.organization_we_vote_id,
                    }
                    organization_suggestion_followed_list.append(one_suggested_organization)
    '''
    elif kind_of_follow_task == FOLLOW_SUGGESTIONS_FROM_FRIENDS:
        suggested_organization_to_follow_list_results = follow_organization_manager. \
            retrieve_suggested_organization_to_follow_list(voter_we_vote_id, from_twitter=False)
        status += suggested_organization_to_follow_list_results['status']
        success = suggested_organization_to_follow_list_results['success']
        if suggested_organization_to_follow_list_results['suggested_organization_to_follow_list_found']:
            suggested_organization_to_follow_list = \
                suggested_organization_to_follow_list_results['suggested_organization_to_follow_list']
            for suggested_organization_to_follow_entry in suggested_organization_to_follow_list:
                organization_we_vote_id = suggested_organization_to_follow_entry.organization_we_vote_id
                toogle_twitter_following_organization_results = follow_organization_manager.\
                    toogle_twitter_following_organization(voter_id, organization_we_vote_id,
                                                          auto_followed_from_twitter_suggestion=False)
                status += ' ' + toogle_twitter_following_organization_results['status']
                success = toogle_twitter_following_organization_results['success']
                if toogle_twitter_following_organization_results['follow_suggested_organization_on_stage_found']:
                    follow_suggested_organization_on_stage = toogle_twitter_following_organization_results[
                        'follow_suggested_organization_on_stage']
                    one_suggested_organization = {
                        "organization_we_vote_id": follow_suggested_organization_on_stage.organization_we_vote_id,
                    }
                    organization_suggestion_followed_list.append(one_suggested_organization)
    '''
    organization_suggestion_task_saved = True if len(organization_suggestion_list) or len(
        organization_suggestion_followed_list) else False
    results = {
        'success':                                  success,
        'status':                                   status,
        'voter_device_id':                          voter_device_id,
        'kind_of_suggestion_task':                  kind_of_suggestion_task,
        'kind_of_follow_task':                      kind_of_follow_task,
        'organization_suggestion_task_saved':       organization_suggestion_task_saved,
        'organization_suggestion_list':             organization_suggestion_list,
        'organization_suggestion_followed_list':    organization_suggestion_followed_list
    }
    return results


def create_followers_from_politicians(
        number_to_create=100,
        request={},
        state_code=''):
    campaignx_manager = CampaignXManager()
    campaignx_we_vote_id_list_to_refresh = []
    error_message_to_print = ''
    info_message_to_print = ''
    politician_we_vote_id_list = []
    positions_analyzed_count = 0
    status = ""
    success = True

    # Find some Politicians we know have positions
    queryset = PositionEntered.objects.using('readonly').all()
    queryset = queryset.exclude(follow_organization_analysis_complete=True)
    queryset = queryset.exclude(
        Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=''))
    queryset = queryset.values_list('politician_we_vote_id', flat=True).distinct()
    highly_likely_politician_list = list(queryset)

    queryset = Politician.objects.all()  # Cannot be 'readonly' because we update these values below
    queryset = queryset.filter(follow_organization_analysis_complete=False)
    queryset = queryset.exclude(follow_organization_intervention_needed=True)
    queryset = queryset.exclude(
        Q(linked_campaignx_we_vote_id__isnull=True) | Q(linked_campaignx_we_vote_id=''))
    queryset = queryset.exclude(
        Q(organization_we_vote_id__isnull=True) | Q(organization_we_vote_id=''))
    if positive_value_exists(highly_likely_politician_list):
        queryset = queryset.filter(we_vote_id__in=highly_likely_politician_list)
    elif positive_value_exists(state_code):
        queryset = queryset.filter(state_code__iexact=state_code)
    politician_list = list(queryset[:number_to_create])

    for politician_on_stage in politician_list:
        if politician_on_stage.we_vote_id not in politician_we_vote_id_list:
            # If an organization hasn't been created for the Politician yet, don't try to update Politician yet
            if positive_value_exists(politician_on_stage.organization_we_vote_id):
                politician_we_vote_id_list.append(politician_on_stage.we_vote_id)
        if positive_value_exists(politician_on_stage.linked_campaignx_we_vote_id):
            if politician_on_stage.linked_campaignx_we_vote_id not in campaignx_we_vote_id_list_to_refresh:
                campaignx_we_vote_id_list_to_refresh.append(politician_on_stage.linked_campaignx_we_vote_id)

    # #############################
    # Create FollowOrganization entries
    # From PUBLIC positions
    results = create_followers_from_positions(
        friends_only_positions=False,
        number_to_create=1000,
        politicians_to_follow_we_vote_id_list=politician_we_vote_id_list)
    positions_analyzed_count += results['positions_analyzed_count']
    if positive_value_exists(results['error_message_to_print']):
        error_message_to_print += results['error_message_to_print']
    if positive_value_exists(results['positions_analyzed_count']):
        if positive_value_exists(results['info_message_to_print']):
            info_message_to_print += results['info_message_to_print']
    campaignx_we_vote_id_list_changed = results['campaignx_we_vote_id_list_to_refresh']
    if len(campaignx_we_vote_id_list_changed) > 0:
        campaignx_we_vote_id_list_to_refresh = \
            list(set(campaignx_we_vote_id_list_changed + campaignx_we_vote_id_list_to_refresh))
    # From FRIENDS_ONLY positions
    results = create_followers_from_positions(
        friends_only_positions=True,
        number_to_create=1000,
        politicians_to_follow_we_vote_id_list=politician_we_vote_id_list)
    positions_analyzed_count += results['positions_analyzed_count']
    if positive_value_exists(results['error_message_to_print']):
        error_message_to_print += results['error_message_to_print']
    if positive_value_exists(results['positions_analyzed_count']):
        if positive_value_exists(results['info_message_to_print']):
            info_message_to_print += results['info_message_to_print']
    campaignx_we_vote_id_list_changed = results['campaignx_we_vote_id_list_to_refresh']
    if len(campaignx_we_vote_id_list_changed) > 0:
        campaignx_we_vote_id_list_to_refresh = \
            list(set(campaignx_we_vote_id_list_changed + campaignx_we_vote_id_list_to_refresh))

    info_message_to_print += \
        "{positions_analyzed_count:,} positions analyzed, " \
        "".format(
            positions_analyzed_count=positions_analyzed_count)

    follow_organization_manager = FollowOrganizationManager()
    for politician_on_stage in politician_list:
        supporters_count = follow_organization_manager.fetch_follow_organization_count(
            following_status=FOLLOWING,
            organization_we_vote_id_being_followed=politician_on_stage.organization_we_vote_id)
        opposers_count = follow_organization_manager.fetch_follow_organization_count(
            following_status=FOLLOW_DISLIKE,
            organization_we_vote_id_being_followed=politician_on_stage.organization_we_vote_id)
        results = campaignx_manager.retrieve_campaignx(
            campaignx_we_vote_id=politician_on_stage.linked_campaignx_we_vote_id,
            read_only=False)
        count_refresh_needed = False
        if results['campaignx_found']:
            campaignx = results['campaignx']
            if campaignx.opposers_count != opposers_count:
                count_refresh_needed = True
            if campaignx.supporters_count != supporters_count:
                count_refresh_needed = True
            if count_refresh_needed:
                campaignx.opposers_count = opposers_count
                campaignx.supporters_count = supporters_count
                campaignx.save()

    results = refresh_campaignx_supporters_count_in_all_children(
        request,
        campaignx_we_vote_id_list=campaignx_we_vote_id_list_to_refresh)
    # if positive_value_exists(results['update_message']):
    #     update_message += results['update_message']

    update_list = []
    for politician_on_stage in politician_list:
        politician_on_stage.follow_organization_analysis_complete = True
        update_list.append(politician_on_stage)

    try:
        update_count = Politician.objects.bulk_update(
            update_list,
            ['follow_organization_analysis_complete', 'follow_organization_intervention_needed'])
        info_message_to_print += \
            "{update_count:,} politicians updated, " \
            "".format(
                update_count=update_count)
    except Exception as e:
        error_message_to_print += "ERROR with Politician.objects.bulk_create: {e}, ".format(e=e)

    results = {
        # 'campaignx_we_vote_id_list_to_refresh': campaignx_we_vote_id_list_to_refresh,
        'error_message_to_print':   error_message_to_print,
        # 'follow_organization_entries_created':  follow_organization_entries_created,
        'info_message_to_print':    info_message_to_print,
        'positions_analyzed_count': positions_analyzed_count,
        'status':                   status,
        'success':                  success,
    }
    return results


def create_followers_from_positions(
        friends_only_positions=False,
        number_to_create=100,
        politicians_to_follow_we_vote_id_list=[],
        state_code=''):
    # Create default variables needed below
    follow_organization_bulk_create_list = []
    follow_organization_entry_create_needed = False
    follow_organization_entries_created = 0
    follow_organization_entries_not_created = 0
    campaignx_we_vote_id_list_to_refresh = []
    error_message_to_print = ''
    info_message_to_print = ''
    # key: politician_we_vote_id, value: linked_campaignx_we_vote_id
    linked_campaignx_we_vote_id_by_politician_we_vote_id_dict = {}
    # key: politician_we_vote_id, value: organization_we_vote_id
    organization_we_vote_id_by_politician_we_vote_id_dict = {}
    organization_we_vote_id_following_politician_list = []
    # politician_we_vote_id_list_being_followed = []  # List of politician_we_vote_ids being followed
    position_objects_to_mark_as_having_follow_organization_created = []
    position_updates_made = 0
    position_updates_needed = False
    position_we_vote_id_list_to_create_follower = []
    status = ''
    success = True
    voter_we_vote_id_list_following = []  # Must be signed in to create FollowOrganization from friends_only_positions

    # #####################################
    # Retrieve Positions that haven't been reviewed yet (limited by number_to_create)
    if positive_value_exists(friends_only_positions):
        position_query = PositionForFriends.objects.all()  # Cannot be readonly, since we bulk_update at the end
    else:
        position_query = PositionEntered.objects.all()  # Cannot be readonly, since we bulk_update at the end
    # position_query = position_query.filter(position_year=2024)
    position_query = position_query.exclude(follow_organization_analysis_complete=True)
    position_query = position_query.exclude(
        Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=''))
    # We need to handle both SUPPORT and OPPOSE, so no need to restrict to only SUPPORT here
    # position_query = position_query.filter(stance=SUPPORT)
    # DALE 2024-07-14 We can include positions from prior years
    # date_today_as_integer = get_current_date_as_integer()
    # position_query = position_query.filter(
    #     Q(position_ultimate_election_not_linked=True) |
    #     Q(position_ultimate_election_date__gte=date_today_as_integer)
    # )
    if positive_value_exists(len(politicians_to_follow_we_vote_id_list) > 0):
        # Note that this will miss any positions where the politician_we_vote_id didn't get stored with them
        #  2024-07-14 Check to see if we have a script that populates the politician_we_vote_id when there is only
        #   the candidate_campaign_we_vote_id
        position_query = position_query.filter(politician_we_vote_id__in=politicians_to_follow_we_vote_id_list)
    elif positive_value_exists(state_code):
        position_query = position_query.filter(state_code__iexact=state_code)
    total_to_convert = position_query.count()
    positions_analyzed_count = total_to_convert
    if positive_value_exists(total_to_convert):
        position_list_to_create_follower = list(position_query[:number_to_create])
        # Now zero in on just these politicians (OR fill up politicians_to_follow_we_vote_id_list if it was empty)
        for one_position in position_list_to_create_follower:
            if positive_value_exists(one_position.politician_we_vote_id):
                politicians_to_follow_we_vote_id_list.append(one_position.politician_we_vote_id)
    else:
        position_list_to_create_follower = []
    position_objects_to_mark_as_analysis_complete = []  # Move positions over to this for bulk_update

    # Assemble we_vote_id lists, so we can retrieve the objects to work with them
    for one_position in position_list_to_create_follower:
        if positive_value_exists(one_position.voter_we_vote_id):
            voter_we_vote_id_list_following.append(one_position.voter_we_vote_id)
        # politician_we_vote_id_list_being_followed.append(one_position.politician_we_vote_id)
        # position_we_vote_id_list_to_create_follower.append(one_position.we_vote_id)
        # We are taking the organization endorsing a politician, and creating a FollowOrganization entry
        organization_we_vote_id_following_politician_list.append(one_position.organization_we_vote_id)

    # Retrieve all relevant voters associated with positions, in a single query, so we can access voter.is_signed_in
    #  For friends_only_positions, we want to only create a follow_organization entry if the voter is signed in
    voter_is_signed_in_by_voter_we_vote_id_dict = {}
    if positive_value_exists(friends_only_positions) and len(voter_we_vote_id_list_following) > 0:
        from voter.models import Voter
        voter_query = Voter.objects.using('readonly').all()
        voter_query = voter_query.filter(we_vote_id__in=voter_we_vote_id_list_following)
        voter_list = list(voter_query)
        for one_voter in voter_list:
            voter_is_signed_in_by_voter_we_vote_id_dict[one_voter.we_vote_id] = one_voter.is_signed_in()
        position_list_to_create_follower_modified = []
        for one_position in position_list_to_create_follower:
            if positive_value_exists(one_position.voter_we_vote_id):
                if one_position.voter_we_vote_id in voter_is_signed_in_by_voter_we_vote_id_dict:
                    if voter_is_signed_in_by_voter_we_vote_id_dict[one_position.voter_we_vote_id]:
                        position_list_to_create_follower_modified.append(one_position)
                    else:
                        one_position.follow_organization_analysis_complete = True
                        one_position.follow_organization_created = False
                        position_objects_to_mark_as_analysis_complete.append(one_position)
                        total_to_convert -= 1
                        # By not adding to position_list_to_create_follower_modified, we are "dropping" it
                else:
                    one_position.follow_organization_analysis_complete = True
                    one_position.follow_organization_created = False
                    position_objects_to_mark_as_analysis_complete.append(one_position)
                    total_to_convert -= 1
                    # By not adding to position_list_to_create_follower_modified, we are "dropping" it
            else:
                # Is from organization not linked to voter
                position_list_to_create_follower_modified.append(one_position)
        position_list_to_create_follower = position_list_to_create_follower_modified

    # Retrieve all the related politicians in a single query, so we can access the linked_campaignx_we_vote_id
    #  when we are cycling through the positions
    politician_list = []
    if len(politicians_to_follow_we_vote_id_list) > 0:
        politician_query = Politician.objects.using('readonly').all()
        politician_query = politician_query.filter(we_vote_id__in=politicians_to_follow_we_vote_id_list)
        politician_list = list(politician_query)
    for one_politician in politician_list:
        if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
            linked_campaignx_we_vote_id_by_politician_we_vote_id_dict[one_politician.we_vote_id] = \
                one_politician.linked_campaignx_we_vote_id
            if one_politician.linked_campaignx_we_vote_id not in campaignx_we_vote_id_list_to_refresh:
                campaignx_we_vote_id_list_to_refresh.append(one_politician.linked_campaignx_we_vote_id)
        if positive_value_exists(one_politician.organization_we_vote_id):
            organization_we_vote_id_by_politician_we_vote_id_dict[one_politician.we_vote_id] = \
                one_politician.organization_we_vote_id

    # Retrieve all the related Organizations in a single query, so we can access get the organization_we_vote_id
    #  from politician_we_vote_id. Eventually org_we_vote_id will be in the Politician record, but this makes sure.
    expected_organization_count = len(politicians_to_follow_we_vote_id_list)
    organization_count = 0
    organization_list = []
    politician_we_vote_ids_not_found = copy.deepcopy(politicians_to_follow_we_vote_id_list)
    if len(politicians_to_follow_we_vote_id_list) > 0:
        queryset = Organization.objects.using('readonly').all()
        queryset = queryset.filter(politician_we_vote_id__in=politicians_to_follow_we_vote_id_list)
        organization_list = list(queryset)
    for one_organization in organization_list:
        organization_count += 1
        if positive_value_exists(one_organization.politician_we_vote_id):
            if one_organization.politician_we_vote_id in politician_we_vote_ids_not_found:
                try:
                    politician_we_vote_ids_not_found.remove(one_organization.politician_we_vote_id)
                except Exception as e:
                    pass
            try:
                organization_we_vote_id_by_politician_we_vote_id_dict[one_organization.politician_we_vote_id] = \
                    one_organization.we_vote_id
            except Exception as e:
                pass
    if organization_count != expected_organization_count:
        # If here, then 1+ of the politicians doesn't have an organization linked to it.
        error_message_to_print += "ORGANIZATIONS_MISSING_FOR: " + str(politician_we_vote_ids_not_found) + " "

    # Check FollowOrganization table to see if any of these positions already have a FollowOrganization entry
    #  if so, don't try to add a duplicate.
    # Retrieve existing FollowOrganization entries that are related to the organization which is endorsing
    #  this politician, so we can mark them as already processed in the PositionEntered table.
    position_objects_to_update_later = []
    if len(organization_we_vote_id_following_politician_list) > 0:
        queryset = FollowOrganization.objects.using('readonly').all()
        queryset = queryset.filter(
            organization_we_vote_id_that_is_following__in=organization_we_vote_id_following_politician_list)
        existing_follow_organization_entries = list(queryset)
        position_list_to_create_follower_modified = []
        # key = organization_we_vote_id endorsing, value = org we_vote_id being endorsed (i.e., Politician)
        follow_organization_dict_by_endorser = {}
        for one_follow_organization in existing_follow_organization_entries:
            follow_organization_dict_by_endorser[
                one_follow_organization.organization_we_vote_id_that_is_following] = \
                one_follow_organization.organization_we_vote_id
        for one_position in position_list_to_create_follower:
            # If we have FollowOrganization entry in existing_follow_organization_entries, then save one_position,
            #  so we can mark as reviewed
            follow_organization_entry_for_this_position_already_exists = False
            organization_we_vote_id_with_opinion = one_position.organization_we_vote_id
            politician_we_vote_id_being_endorsed = one_position.politician_we_vote_id
            organization_we_vote_id_being_endorsed = ''
            if positive_value_exists(politician_we_vote_id_being_endorsed):
                if politician_we_vote_id_being_endorsed in organization_we_vote_id_by_politician_we_vote_id_dict:
                    organization_we_vote_id_being_endorsed = \
                        organization_we_vote_id_by_politician_we_vote_id_dict[politician_we_vote_id_being_endorsed]
            if positive_value_exists(organization_we_vote_id_with_opinion) and \
                    positive_value_exists(organization_we_vote_id_being_endorsed):
                existing_org_we_vote_id_being_endorsed = \
                    follow_organization_dict_by_endorser.get(organization_we_vote_id_with_opinion)
                if existing_org_we_vote_id_being_endorsed == organization_we_vote_id_being_endorsed:
                    follow_organization_entry_for_this_position_already_exists = True
            else:
                # Politician probably doesn't have organization linked to it yet
                position_objects_to_update_later.append(one_position)
                continue
            if follow_organization_entry_for_this_position_already_exists:
                one_position.follow_organization_analysis_complete = True
                one_position.follow_organization_created = True
                position_objects_to_mark_as_having_follow_organization_created.append(one_position)
                position_updates_made += 1
                position_updates_needed = True
            else:
                position_list_to_create_follower_modified.append(one_position)
        position_list_to_create_follower = position_list_to_create_follower_modified

    for one_position in position_list_to_create_follower:
        if one_position.stance == SUPPORT:
            following_status = FOLLOWING
        elif one_position.stance == OPPOSE:
            following_status = FOLLOW_DISLIKE
        else:
            # Do not try to create a FollowOrganization entry without SUPPORT or OPPOSE stance
            one_position.follow_organization_analysis_complete = True
            one_position.follow_organization_created = False
            position_objects_to_mark_as_analysis_complete.append(one_position)
            continue
        is_follow_visible_publicly = not positive_value_exists(friends_only_positions)

        # ######################
        organization_we_vote_id_with_opinion = one_position.organization_we_vote_id
        politician_we_vote_id_being_endorsed = one_position.politician_we_vote_id
        organization_we_vote_id_being_endorsed = ''
        if positive_value_exists(politician_we_vote_id_being_endorsed):
            if politician_we_vote_id_being_endorsed in organization_we_vote_id_by_politician_we_vote_id_dict:
                organization_we_vote_id_being_endorsed = \
                    organization_we_vote_id_by_politician_we_vote_id_dict[politician_we_vote_id_being_endorsed]
        if positive_value_exists(organization_we_vote_id_with_opinion) and \
                positive_value_exists(organization_we_vote_id_being_endorsed):
            created = False
            try:
                follow_organization, created = FollowOrganization.objects.update_or_create(
                    organization_we_vote_id_that_is_following=organization_we_vote_id_with_opinion,
                    organization_we_vote_id=organization_we_vote_id_being_endorsed,
                    defaults={
                        'organization_we_vote_id_that_is_following': organization_we_vote_id_with_opinion,
                        'organization_we_vote_id': organization_we_vote_id_being_endorsed,
                        'following_status': following_status,
                        'is_follow_visible_publicly': is_follow_visible_publicly,
                    }
                )
                # follow_organization_bulk_create_list.append(follow_organization)
                # follow_organization_entry_create_needed = True
                if positive_value_exists(created):
                    follow_organization_entries_created += 1
                    status += "FOLLOW_ORGANIZATION_CREATED "
                else:
                    status += "FOLLOW_ORGANIZATION_UPDATED "
                one_position.follow_organization_analysis_complete = True
                one_position.follow_organization_created = True
                position_objects_to_mark_as_having_follow_organization_created.append(one_position)
                position_updates_made += 1
                position_updates_needed = True
            except Exception as e:
                follow_organization_entries_not_created += 1
                success = False
                status += "FOLLOW_ORGANIZATION_NOT_UPDATED: " + str(e) + ' '
            if created:
                # If an entry was created, we should refresh the CampaignX supporters_count
                if one_position.politician_we_vote_id in linked_campaignx_we_vote_id_by_politician_we_vote_id_dict:
                    linked_campaignx_we_vote_id = \
                        linked_campaignx_we_vote_id_by_politician_we_vote_id_dict[one_position.politician_we_vote_id]
                    if positive_value_exists(linked_campaignx_we_vote_id):
                        if linked_campaignx_we_vote_id not in campaignx_we_vote_id_list_to_refresh:
                            campaignx_we_vote_id_list_to_refresh.append(linked_campaignx_we_vote_id)
        else:
            # The position doesn't contain both organization_we_vote_id and politician_we_vote_id
            #  TODO: Flag for later?
            pass

    combined_list = list(set(position_objects_to_mark_as_analysis_complete +
                             position_objects_to_mark_as_having_follow_organization_created))
    if position_updates_needed and len(combined_list) > 0:
        try:
            if friends_only_positions:
                PositionForFriends.objects.bulk_update(
                    combined_list,
                    ['follow_organization_analysis_complete', 'follow_organization_created'])
            else:
                PositionEntered.objects.bulk_update(
                    combined_list,
                    ['follow_organization_analysis_complete', 'follow_organization_created'])
            info_message_to_print += \
                "{position_updates_made:,} positions updated, " \
                "".format(
                    position_updates_made=position_updates_made)
        except Exception as e:
            error_message_to_print += "ERROR with PositionEntered.objects.bulk_create: {e}, ".format(e=e)

    info_message_to_print += \
        "{follow_organization_entries_created:,} FollowOrganization entries created, " \
        "".format(follow_organization_entries_created=follow_organization_entries_created)

    counter = 0
    follow_organization_created_list = []
    for one_position in position_objects_to_mark_as_having_follow_organization_created:
        counter += 1
        if counter < 5:
            follow_organization_created_list.append(one_position.we_vote_id)
    info_message_to_print += \
        "(sample list: {follow_organization_created_list}) " \
        "".format(follow_organization_created_list=follow_organization_created_list)

    total_to_convert_after = total_to_convert - number_to_create if total_to_convert > number_to_create else 0
    if positive_value_exists(total_to_convert_after):
        info_message_to_print += \
            "{total_to_convert_after:,} positions remaining in 'create FollowOrganization' process. " \
            "".format(total_to_convert_after=total_to_convert_after)

    results = {
        'campaignx_we_vote_id_list_to_refresh': campaignx_we_vote_id_list_to_refresh,
        'error_message_to_print':   error_message_to_print,
        'follow_organization_entries_created':  follow_organization_entries_created,
        'info_message_to_print':    info_message_to_print,
        'positions_analyzed_count': positions_analyzed_count,
        'status':                   status,
        'success':                  success,
    }
    return results


def create_follow_organization_from_position(
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
                'campaignx_supporter':          campaignx_supporter,
                'campaignx_supporter_found':    campaignx_supporter_found,
                'status':                       status,
                'success':                      False,
            }
            return results

    # Change the following_status based on position.stance
    if position.stance in [OPPOSE]:
        following_status = FOLLOW_DISLIKE
    elif position.stance in [SUPPORT]:
        following_status = FOLLOWING
    else:
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
        campaignx_supporter = FollowOrganization(
            campaign_supported=True,
            campaignx_we_vote_id=campaignx_we_vote_id,
            date_supported=position.date_entered,
            following_status=following_status,
            linked_position_we_vote_id=position.we_vote_id,
            organization_we_vote_id=position.organization_we_vote_id,
            supporter_name=position.speaker_display_name,
            supporter_endorsement=position.statement_text,
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
