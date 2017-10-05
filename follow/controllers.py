# follow/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FollowOrganizationList, FollowOrganizationManager, UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, \
    FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW, FollowIssueList, FollowIssueManager, FOLLOWING, FollowMetricsManager
from analytics.models import ACTION_ISSUE_FOLLOW, ACTION_ISSUE_FOLLOW_IGNORE, \
    ACTION_ISSUE_STOP_FOLLOWING, AnalyticsManager
from django.http import HttpResponse
from friend.models import FriendManager
import json
from organization.models import OrganizationManager
import robot_detection
from twitter.models import TwitterUserManager
from voter.models import VoterManager, fetch_voter_we_vote_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def duplicate_follow_entries_to_another_voter(from_voter_id, from_voter_we_vote_id, to_voter_id, to_voter_we_vote_id):
    status = ''
    success = False
    follow_entries_duplicated = 0
    follow_entries_not_duplicated = 0
    organization_manager = OrganizationManager()
    voter_manager = VoterManager()
    follow_organization_list = FollowOrganizationList()
    follow_organization_manager = FollowOrganizationManager()
    from_follow_list = follow_organization_list.retrieve_follow_organization_by_voter_id(from_voter_id)

    to_voter_linked_organization_we_vote_id = \
        voter_manager.fetch_linked_organization_we_vote_id_from_local_id(to_voter_id)

    for from_follow_entry in from_follow_list:
        heal_data = False
        # See if we need to heal the data
        if not positive_value_exists(from_follow_entry.organization_we_vote_id):
            from_follow_entry.organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(
                from_follow_entry.organization_id)
            heal_data = True
        if not positive_value_exists(from_follow_entry.voter_linked_organization_we_vote_id):
            from_follow_entry.voter_linked_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_from_local_id(from_voter_id)
            heal_data = True

        if heal_data:
            try:
                from_follow_entry.save()
            except Exception as e:
                pass

        # See if the "to_voter" already has an entry for this organization
        existing_entry_results = follow_organization_manager.retrieve_follow_organization(
            0, to_voter_id, from_follow_entry.organization_id, from_follow_entry.organization_we_vote_id)
        if not existing_entry_results['follow_organization_found']:
            # Change the voter_id and voter_linked_organization_we_vote_id, and then save a new entry.
            #  This will not overwrite existing from_follow_entry.
            try:
                from_follow_entry.id = None  # Reset the id so a new entry is created
                from_follow_entry.pk = None
                from_follow_entry.voter_id = to_voter_id
                # We don't currently store follow entries by we_vote_id
                from_follow_entry.voter_linked_organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_follow_entry.save()
                follow_entries_duplicated += 1
            except Exception as e:
                follow_entries_not_duplicated += 1

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
    success = False
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
    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'follow_issue_entries_duplicated':  follow_issue_entries_duplicated,
        'follow_issue_entries_not_duplicated':  follow_issue_entries_not_duplicated,
    }
    return results


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
    success = False
    follow_issue_entries_moved = 0
    follow_issue_entries_not_moved = 0
    follow_issue_list = FollowIssueList()
    from_follow_issue_list = follow_issue_list.retrieve_follow_issue_list_by_voter_we_vote_id(from_voter_we_vote_id)
    to_follow_issue_list = follow_issue_list.retrieve_follow_issue_list_by_voter_we_vote_id(to_voter_we_vote_id)
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
    success = False
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
                pass

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

    from_follow_list = follow_organization_list.retrieve_follow_organization_by_organization_we_vote_id(
        from_organization_we_vote_id)
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
                pass

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


def voter_issue_follow_for_api(voter_device_id, issue_we_vote_id, follow_value, ignore_value,
                               user_agent_string, user_agent_object):  # issueFollow
    voter_we_vote_id = False
    voter_id = 0
    is_signed_in = False
    issue_id = ''
    if positive_value_exists(voter_device_id):
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
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
                                                              is_desktop=user_agent_object.is_desktop,
                                                              is_tablet=user_agent_object.is_tablet)
        elif not follow_value:
            result = follow_issue_manager.toggle_off_voter_following_issue(voter_we_vote_id, issue_id,
                                                                           issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_STOP_FOLLOWING,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_desktop,
                                                              is_tablet=user_agent_object.is_tablet)
        elif ignore_value:
            result = follow_issue_manager.toggle_ignore_voter_following_issue(voter_we_vote_id, issue_id,
                                                                              issue_we_vote_id)
            analytics_results = analytics_manager.save_action(ACTION_ISSUE_FOLLOW_IGNORE,
                                                              voter_we_vote_id, voter_id, is_signed_in,
                                                              user_agent_string=user_agent_string, is_bot=is_bot,
                                                              is_mobile=user_agent_object.is_mobile,
                                                              is_desktop=user_agent_object.is_desktop,
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

    return HttpResponse(json.dumps(new_result), content_type='application/json')


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
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
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
        # A) get all of the twitter_ids of all twitter accounts I follow (on Twitter)
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
                        create_or_update_suggested_organization_to_follow(voter_we_vote_id,
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
                        create_or_update_suggested_organization_to_follow(voter_we_vote_id,
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
                                create_or_update_suggested_organization_to_follow(voter_we_vote_id,
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
        # If here, we want to retrieve from the local database all of the organizations that we are following on Twitter
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
