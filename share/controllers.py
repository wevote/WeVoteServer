# share/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ShareManager
from analytics.models import ACTION_VIEW_SHARED_BALLOT, ACTION_VIEW_SHARED_BALLOT_ALL_OPINIONS, \
    ACTION_VIEW_SHARED_CANDIDATE, ACTION_VIEW_SHARED_CANDIDATE_ALL_OPINIONS, \
    ACTION_VIEW_SHARED_MEASURE, ACTION_VIEW_SHARED_MEASURE_ALL_OPINIONS, \
    ACTION_VIEW_SHARED_OFFICE, ACTION_VIEW_SHARED_OFFICE_ALL_OPINIONS, \
    ACTION_VIEW_SHARED_ORGANIZATION, ACTION_VIEW_SHARED_ORGANIZATION_ALL_OPINIONS, \
    ACTION_VIEW_SHARED_READY, ACTION_VIEW_SHARED_READY_ALL_OPINIONS, \
    AnalyticsManager
from follow.models import FOLLOWING, FollowOrganizationManager
import json
from organization.models import OrganizationManager
import robot_detection
from share.models import SharedItem, SharedLinkClicked, SharedPermissionsGranted
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

INDIVIDUAL = 'I'  # One person

logger = wevote_functions.admin.get_logger(__name__)


def move_shared_items_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id,
                                       from_organization_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = True
    shared_item_entries_moved = 0
    shared_item_entries_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_SHARED_ITEMS-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'shared_item_entries_moved': shared_item_entries_moved,
            'shared_item_entries_not_moved': shared_item_entries_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_SHARED_ITEMS-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'shared_item_entries_moved': shared_item_entries_moved,
            'shared_item_entries_not_moved': shared_item_entries_not_moved,
        }
        return results

    # ######################
    # Migrations
    if positive_value_exists(to_organization_we_vote_id):
        try:
            shared_item_entries_moved += SharedItem.objects\
                .filter(shared_by_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(shared_by_voter_we_vote_id=to_voter_we_vote_id,
                        shared_by_organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_ITEM-SHARED_BY_VOTER_WE_VOTE_ID-INCLUDING_ORG: " + str(e) + " "
        try:
            SharedLinkClicked.objects.filter(shared_by_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(shared_by_voter_we_vote_id=to_voter_we_vote_id,
                        shared_by_organization_we_vote_id=to_organization_we_vote_id)
            SharedLinkClicked.objects.filter(viewed_by_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(viewed_by_voter_we_vote_id=to_voter_we_vote_id,
                        viewed_by_organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_LINK_CLICKED-SHARED_BY_VOTER_WE_VOTE_ID-INCLUDING_ORG: " + str(e) + " "
        try:
            SharedPermissionsGranted.objects.filter(shared_by_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(shared_by_voter_we_vote_id=to_voter_we_vote_id,
                        shared_by_organization_we_vote_id=to_organization_we_vote_id)
            SharedPermissionsGranted.objects.filter(shared_to_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(shared_to_voter_we_vote_id=to_voter_we_vote_id,
                        shared_to_organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_PERMISSIONS_GRANTED-SHARED_BY_VOTER_WE_VOTE_ID-INCLUDING_ORG: " + str(e) + " "
    else:
        try:
            SharedItem.objects.filter(shared_by_voter_we_vote_id__iexact=from_voter_we_vote_id)\
                .update(shared_by_voter_we_vote_id=to_voter_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_ITEM-SHARED_BY_VOTER_WE_VOTE_ID: " + str(e) + " "
        try:
            SharedLinkClicked.objects.filter(shared_by_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(shared_by_voter_we_vote_id=to_voter_we_vote_id)
            SharedLinkClicked.objects.filter(viewed_by_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(viewed_by_voter_we_vote_id=to_voter_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_LINK_CLICKED-SHARED_BY_VOTER_WE_VOTE_ID: " + str(e) + " "
        try:
            SharedPermissionsGranted.objects.filter(shared_by_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(shared_by_voter_we_vote_id=to_voter_we_vote_id)
            SharedPermissionsGranted.objects.filter(shared_to_voter_we_vote_id__iexact=from_voter_we_vote_id) \
                .update(shared_to_voter_we_vote_id=to_voter_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_PERMISSIONS_GRANTED-SHARED_BY_VOTER_WE_VOTE_ID: " + str(e) + " "

    if positive_value_exists(from_organization_we_vote_id) and positive_value_exists(to_organization_we_vote_id):
        try:
            SharedItem.objects.filter(site_owner_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(site_owner_organization_we_vote_id=to_organization_we_vote_id)
            SharedItem.objects.filter(shared_by_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(shared_by_organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_ITEM-SITE_OWNER_ORGANIZATION_WE_VOTE_ID: " + str(e) + " "
        try:
            SharedLinkClicked.objects.filter(shared_by_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(shared_by_organization_we_vote_id=to_organization_we_vote_id)
            SharedLinkClicked.objects.filter(viewed_by_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(viewed_by_organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_LINK_CLICKED-SHARED_BY_ORGANIZATION_WE_VOTE_ID: " + str(e) + " "
        try:
            SharedPermissionsGranted.objects\
                .filter(shared_by_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(shared_by_organization_we_vote_id=to_organization_we_vote_id)
            SharedPermissionsGranted.objects\
                .filter(shared_to_organization_we_vote_id__iexact=from_organization_we_vote_id) \
                .update(shared_to_organization_we_vote_id=to_organization_we_vote_id)
        except Exception as e:
            status += "FAILED-SHARED_PERMISSIONS_GRANTED-SHARED_BY_ORGANIZATION_WE_VOTE_ID: " + str(e) + " "
    else:
        status += "MOVE_SHARED_ITEMS-MISSING_EITHER_FROM_OR_TO_ORGANIZATION_WE_VOTE_ID "

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'shared_item_entries_moved': shared_item_entries_moved,
        'shared_item_entries_not_moved': shared_item_entries_not_moved,
    }
    return results


def shared_item_retrieve_for_api(  # sharedItemRetrieve
        voter_device_id='',
        destination_full_url='',
        shared_item_code='',
        shared_item_clicked=False,
        user_agent_string='',
        user_agent_object=None):
    status = ''
    success = True
    candidate_we_vote_id = ''
    date_first_shared = None
    include_friends_only_positions = False
    is_ballot_share = False
    is_candidate_share = False
    is_measure_share = False
    is_office_share = False
    is_organization_share = False
    is_ready_share = False
    google_civic_election_id = ''
    measure_we_vote_id = ''
    office_we_vote_id = ''
    api_call_coming_from_voter_who_shared = False
    shared_by_voter_we_vote_id = ''
    shared_by_organization_type = ''
    shared_by_organization_we_vote_id = ''
    shared_item_code_no_opinions = ''
    shared_item_code_all_opinions = ''
    site_owner_organization_we_vote_id = ''
    url_with_shared_item_code_no_opinions = ''
    url_with_shared_item_code_all_opinions = ''
    viewed_by_voter_we_vote_id = ''
    viewed_by_organization_we_vote_id = ''
    voter_id = 0
    is_signed_in = False

    share_manager = ShareManager()
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        viewed_by_voter_we_vote_id = voter.we_vote_id
        viewed_by_organization_we_vote_id = voter.linked_organization_we_vote_id
        is_signed_in = voter.is_signed_in()

    results = share_manager.retrieve_shared_item(
        destination_full_url=destination_full_url,
        shared_by_voter_we_vote_id=viewed_by_voter_we_vote_id,
        shared_item_code=shared_item_code)
    status += results['status']
    if not results['shared_item_found']:
        status += "SHARED_ITEM_NOT_FOUND "
        results = {
            'status':                       status,
            'success':                      False,
            'destination_full_url':         destination_full_url,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_all_opinions':           shared_item_code_all_opinions,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_all_opinions':  url_with_shared_item_code_all_opinions,
            'is_ballot_share':              is_ballot_share,
            'is_candidate_share':           is_candidate_share,
            'is_measure_share':             is_measure_share,
            'is_office_share':              is_office_share,
            'is_organization_share':        is_organization_share,
            'is_ready_share':               is_ready_share,
            'include_friends_only_positions':   include_friends_only_positions,
            'google_civic_election_id':     google_civic_election_id,
            'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
            'shared_by_voter_we_vote_id':   shared_by_voter_we_vote_id,
            'shared_by_organization_type':  shared_by_organization_type,
            'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
            'candidate_we_vote_id':         candidate_we_vote_id,
            'measure_we_vote_id':           measure_we_vote_id,
            'office_we_vote_id':            office_we_vote_id,
            'date_first_shared':            date_first_shared,
        }
        return results

    shared_item = results['shared_item']
    shared_item_id = shared_item.id
    if positive_value_exists(shared_item.destination_full_url):
        try:
            hostname = shared_item.destination_full_url.strip().lower()
            hostname = hostname.replace('http://', '')
            hostname = hostname.replace('https://', '')
            if '/' in hostname:
                hostname_array = hostname.split('/')
                hostname = hostname_array[0]
            url_with_shared_item_code_no_opinions = \
                "https://" + hostname + "/-" + shared_item.shared_item_code_no_opinions
            url_with_shared_item_code_all_opinions = \
                "https://" + hostname + "/-" + shared_item.shared_item_code_all_opinions
        except Exception as e:
            status += "COULD_NOT_MODIFY_HOSTNAME: " + str(e) + " "

    if viewed_by_voter_we_vote_id == shared_item.shared_by_voter_we_vote_id:
        api_call_coming_from_voter_who_shared = True

    # Store that the link was clicked
    if positive_value_exists(shared_item_clicked):
        # At some point we may allow a distinction between sharing only your public opinions
        #  (as opposed to public AND friends only opinion). shared_item_code_public_opinions is not implemented yet.
        include_public_positions = shared_item.shared_item_code_all_opinions == shared_item_code
        include_friends_only_positions = shared_item.shared_item_code_all_opinions == shared_item_code
        clicked_results = share_manager.create_shared_link_clicked(
            destination_full_url=shared_item.destination_full_url,
            shared_item_code=shared_item_code,
            shared_item_id=shared_item_id,
            shared_by_voter_we_vote_id=shared_item.shared_by_voter_we_vote_id,
            shared_by_organization_type=shared_item.shared_by_organization_type,
            shared_by_organization_we_vote_id=shared_item.shared_by_organization_we_vote_id,
            site_owner_organization_we_vote_id=shared_item.site_owner_organization_we_vote_id,
            viewed_by_voter_we_vote_id=viewed_by_voter_we_vote_id,
            viewed_by_organization_we_vote_id=viewed_by_organization_we_vote_id,
            include_public_positions=include_public_positions,
            include_friends_only_positions=include_friends_only_positions,
        )
        status += clicked_results['status']

        # Store the new permissions granted if the public or friends-only positions were shared
        if positive_value_exists(include_public_positions) or positive_value_exists(include_friends_only_positions):
            permission_results = share_manager.update_or_create_shared_permissions_granted(
                shared_by_voter_we_vote_id=shared_item.shared_by_voter_we_vote_id,
                shared_by_organization_type=shared_item.shared_by_organization_type,
                shared_by_organization_we_vote_id=shared_item.shared_by_organization_we_vote_id,
                shared_to_voter_we_vote_id=viewed_by_voter_we_vote_id,
                shared_to_organization_we_vote_id=viewed_by_organization_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                year_as_integer=shared_item.year_as_integer,
                include_friends_only_positions=include_friends_only_positions,
            )
            status += permission_results['status']

            # Auto follow this person/organization
            if not api_call_coming_from_voter_who_shared:
                follow_organization_manager = FollowOrganizationManager()
                following_results = follow_organization_manager.toggle_voter_following_organization(
                    voter_id,
                    organization_id=0,
                    organization_we_vote_id=shared_item.shared_by_organization_we_vote_id,
                    voter_linked_organization_we_vote_id=viewed_by_organization_we_vote_id,
                    following_status=FOLLOWING)
                status += following_results['status']

        # Store analytics information when a Shared Item Code (sic) link was clicked
        # Do not store if you are clicking your own link
        if not api_call_coming_from_voter_who_shared:
            is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
            analytics_manager = AnalyticsManager()
            action_view_type = ''

            # We want to see if we can get the google_civic_election_id from the voter_device_link (no guarantees)
            voter_device_link_manager = VoterDeviceLinkManager()
            results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(
                voter_device_id, read_only=False)  # From the live database since it may be the first link clicked
            if results['voter_device_link_found']:
                voter_device_link = results['voter_device_link']
                clicked_google_civic_election_id = voter_device_link.google_civic_election_id
            else:
                clicked_google_civic_election_id = 0

            if shared_item.is_ballot_share:
                if positive_value_exists(include_friends_only_positions):
                    action_view_type = ACTION_VIEW_SHARED_BALLOT_ALL_OPINIONS
                # elif positive_value_exists(include_public_positions):  # Sharing only your public opinions
                else:
                    action_view_type = ACTION_VIEW_SHARED_BALLOT
            elif shared_item.is_candidate_share:
                if positive_value_exists(include_friends_only_positions):
                    action_view_type = ACTION_VIEW_SHARED_CANDIDATE_ALL_OPINIONS
                # elif positive_value_exists(include_public_positions):  # Sharing only your public opinions
                else:
                    action_view_type = ACTION_VIEW_SHARED_CANDIDATE
            elif shared_item.is_measure_share:
                if positive_value_exists(include_friends_only_positions):
                    action_view_type = ACTION_VIEW_SHARED_MEASURE_ALL_OPINIONS
                # elif positive_value_exists(include_public_positions):  # Sharing only your public opinions
                else:
                    action_view_type = ACTION_VIEW_SHARED_MEASURE
            elif shared_item.is_office_share:
                if positive_value_exists(include_friends_only_positions):
                    action_view_type = ACTION_VIEW_SHARED_OFFICE_ALL_OPINIONS
                # elif positive_value_exists(include_public_positions):  # Sharing only your public opinions
                else:
                    action_view_type = ACTION_VIEW_SHARED_OFFICE
            elif shared_item.is_organization_share:
                if positive_value_exists(include_friends_only_positions):
                    action_view_type = ACTION_VIEW_SHARED_ORGANIZATION_ALL_OPINIONS
                # elif positive_value_exists(include_public_positions):  # Sharing only your public opinions
                else:
                    action_view_type = ACTION_VIEW_SHARED_ORGANIZATION
            elif shared_item.is_ready_share:
                if positive_value_exists(include_friends_only_positions):
                    action_view_type = ACTION_VIEW_SHARED_READY_ALL_OPINIONS
                # elif positive_value_exists(include_public_positions):  # Sharing only your public opinions
                else:
                    action_view_type = ACTION_VIEW_SHARED_READY

            if positive_value_exists(action_view_type):
                analytics_results = analytics_manager.save_action(
                    action_constant=action_view_type,
                    voter_we_vote_id=viewed_by_voter_we_vote_id, voter_id=voter_id, is_signed_in=is_signed_in,
                    organization_we_vote_id=shared_item.shared_by_organization_we_vote_id,
                    google_civic_election_id=clicked_google_civic_election_id,
                    user_agent_string=user_agent_string, is_bot=is_bot,
                    is_mobile=user_agent_object.is_mobile,
                    is_desktop=user_agent_object.is_pc,
                    is_tablet=user_agent_object.is_tablet)
                status += analytics_results['status']
    else:
        # Shared item not clicked
        pass

    results = {
        'status':                       status,
        'success':                      success,
        'destination_full_url':         shared_item.destination_full_url,
        'is_ballot_share':              shared_item.is_ballot_share,
        'is_candidate_share':           shared_item.is_candidate_share,
        'is_measure_share':             shared_item.is_measure_share,
        'is_office_share':              shared_item.is_office_share,
        'is_organization_share':        shared_item.is_organization_share,
        'is_ready_share':               shared_item.is_ready_share,
        'include_friends_only_positions': include_friends_only_positions,
        'google_civic_election_id':     shared_item.google_civic_election_id,
        'shared_by_organization_type':  shared_item.shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_item.shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_item.shared_by_voter_we_vote_id,
        'site_owner_organization_we_vote_id':   shared_item.site_owner_organization_we_vote_id,
        'candidate_we_vote_id':         shared_item.candidate_we_vote_id,
        'measure_we_vote_id':           shared_item.measure_we_vote_id,
        'office_we_vote_id':            shared_item.office_we_vote_id,
        'date_first_shared':            str(shared_item.date_first_shared),
    }
    if api_call_coming_from_voter_who_shared:
        results['shared_item_code_no_opinions'] = shared_item.shared_item_code_no_opinions
        results['shared_item_code_all_opinions'] = shared_item.shared_item_code_all_opinions
        results['url_with_shared_item_code_no_opinions'] = url_with_shared_item_code_no_opinions
        results['url_with_shared_item_code_all_opinions'] = url_with_shared_item_code_all_opinions
    else:
        # If here we don't want to reveal the other shared_item code
        if shared_item.shared_item_code_no_opinions == shared_item_code:
            results['shared_item_code_no_opinions'] = shared_item.shared_item_code_no_opinions
            results['url_with_shared_item_code_no_opinions'] = url_with_shared_item_code_no_opinions
        else:
            results['shared_item_code_no_opinions'] = ''
            results['url_with_shared_item_code_no_opinions'] = ''
        if shared_item.shared_item_code_all_opinions == shared_item_code:
            results['shared_item_code_all_opinions'] = shared_item.shared_item_code_all_opinions
            results['url_with_shared_item_code_all_opinions'] = url_with_shared_item_code_all_opinions
        else:
            results['shared_item_code_all_opinions'] = ''
            results['url_with_shared_item_code_all_opinions'] = ''
    return results


def shared_item_save_for_api(  # sharedItemSave
        voter_device_id='',
        destination_full_url='',
        ballot_item_we_vote_id='',
        google_civic_election_id=0,
        is_ballot_share=False,
        is_candidate_share=False,
        is_measure_share=False,
        is_office_share=False,
        is_organization_share=False,
        is_ready_share=False,
        organization_we_vote_id=''):
    status = ''
    success = True
    candidate_we_vote_id = ''
    date_first_shared = None
    hostname = ''
    measure_we_vote_id = ''
    office_we_vote_id = ''
    shared_by_voter_we_vote_id = ''
    shared_by_organization_type = ''
    shared_by_organization_we_vote_id = ''
    shared_item_code_no_opinions = ''
    shared_item_code_all_opinions = ''
    site_owner_organization_we_vote_id = ''
    url_with_shared_item_code_no_opinions = destination_full_url  # Default to this
    url_with_shared_item_code_all_opinions = destination_full_url  # Default to this

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        shared_by_voter_we_vote_id = voter.we_vote_id
        shared_by_organization_we_vote_id = voter.linked_organization_we_vote_id
        shared_by_organization_type = INDIVIDUAL

    organization_manager = OrganizationManager()
    try:
        hostname = destination_full_url.strip().lower()
        hostname = hostname.replace('http://', '')
        hostname = hostname.replace('https://', '')
        if '/' in hostname:
            hostname_array = hostname.split('/')
            hostname = hostname_array[0]

        results = organization_manager.retrieve_organization_from_incoming_hostname(hostname, read_only=True)
        status += results['status']
        organization_found = results['organization_found']
        if organization_found:
            organization = results['organization']
            site_owner_organization_we_vote_id = organization.we_vote_id
    except Exception as e:
        status += "COULD_NOT_MODIFY_HOSTNAME: " + str(e) + " "
        success = False

    if positive_value_exists(ballot_item_we_vote_id):
        if "cand" in ballot_item_we_vote_id:
            candidate_we_vote_id = ballot_item_we_vote_id
        elif "meas" in ballot_item_we_vote_id:
            measure_we_vote_id = ballot_item_we_vote_id
        elif "off" in ballot_item_we_vote_id:
            office_we_vote_id = ballot_item_we_vote_id

    required_variables_for_new_entry = positive_value_exists(destination_full_url) \
        and positive_value_exists(shared_by_voter_we_vote_id)
    if not required_variables_for_new_entry or not success:
        status += "NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'destination_full_url':         destination_full_url,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_all_opinions':           shared_item_code_all_opinions,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_all_opinions':  url_with_shared_item_code_all_opinions,
            'is_ballot_share':              is_ballot_share,
            'is_candidate_share':           is_candidate_share,
            'is_measure_share':             is_measure_share,
            'is_office_share':              is_office_share,
            'is_organization_share':        is_organization_share,
            'is_ready_share':               is_ready_share,
            'google_civic_election_id':     google_civic_election_id,
            'shared_by_organization_type':  shared_by_organization_type,
            'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
            'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
            'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
            'candidate_we_vote_id':         candidate_we_vote_id,
            'measure_we_vote_id':           measure_we_vote_id,
            'office_we_vote_id':            office_we_vote_id,
            'date_first_shared':            date_first_shared,
        }
        return results

    share_manager = ShareManager()
    defaults = {
        'candidate_we_vote_id':                 candidate_we_vote_id,
        'google_civic_election_id':             google_civic_election_id,
        'is_ballot_share':                      is_ballot_share,
        'is_candidate_share':                   is_candidate_share,
        'is_measure_share':                     is_measure_share,
        'is_office_share':                      is_office_share,
        'is_organization_share':                is_organization_share,
        'is_ready_share':                       is_ready_share,
        'measure_we_vote_id':                   measure_we_vote_id,
        'office_we_vote_id':                    office_we_vote_id,
        'shared_by_organization_type':          shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
    }
    create_results = share_manager.update_or_create_shared_item(
        destination_full_url=destination_full_url,
        shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        defaults=defaults,
    )
    status += create_results['status']
    if create_results['shared_item_found']:
        shared_item = create_results['shared_item']
        shared_item_code_no_opinions = shared_item.shared_item_code_no_opinions
        shared_item_code_all_opinions = shared_item.shared_item_code_all_opinions
        url_with_shared_item_code_no_opinions = "https://" + hostname + "/-" + shared_item_code_no_opinions
        url_with_shared_item_code_all_opinions = "https://" + hostname + "/-" + shared_item_code_all_opinions

    results = {
        'status':                       status,
        'success':                      success,
        'destination_full_url':         destination_full_url,
        'shared_item_code_no_opinions':             shared_item_code_no_opinions,
        'shared_item_code_all_opinions':           shared_item_code_all_opinions,
        'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
        'url_with_shared_item_code_all_opinions':  url_with_shared_item_code_all_opinions,
        'is_ballot_share':              is_ballot_share,
        'is_candidate_share':           is_candidate_share,
        'is_measure_share':             is_measure_share,
        'is_office_share':              is_office_share,
        'is_organization_share':        is_organization_share,
        'is_ready_share':               is_ready_share,
        'google_civic_election_id':     google_civic_election_id,
        'shared_by_organization_type':  shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
        'candidate_we_vote_id':         candidate_we_vote_id,
        'measure_we_vote_id':           measure_we_vote_id,
        'office_we_vote_id':            office_we_vote_id,
        'date_first_shared':            date_first_shared,
    }
    return results


def super_share_item_save_for_api(  # superShareItemSave
        campaignx_we_vote_id='',
        campaignx_news_item_we_vote_id='',
        destination_full_url='',
        email_recipient_list_serialized='',
        email_recipient_list_changed=False,
        personalized_message='',
        personalized_message_changed=False,
        personalized_subject='',
        personalized_subject_changed=False,
        voter_device_id=''):
    status = ''
    success = True
    shared_by_voter_we_vote_id = ''
    shared_by_organization_type = ''
    shared_by_organization_we_vote_id = ''
    site_owner_organization_we_vote_id = ''
    super_share_item_id = 0

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        shared_by_voter_we_vote_id = voter.we_vote_id
        shared_by_organization_we_vote_id = voter.linked_organization_we_vote_id
        shared_by_organization_type = INDIVIDUAL

    organization_manager = OrganizationManager()
    try:
        hostname = destination_full_url.strip().lower()
        hostname = hostname.replace('http://', '')
        hostname = hostname.replace('https://', '')
        if '/' in hostname:
            hostname_array = hostname.split('/')
            hostname = hostname_array[0]

        results = organization_manager.retrieve_organization_from_incoming_hostname(hostname, read_only=True)
        status += results['status']
        organization_found = results['organization_found']
        if organization_found:
            organization = results['organization']
            site_owner_organization_we_vote_id = organization.we_vote_id
    except Exception as e:
        status += "COULD_NOT_MODIFY_HOSTNAME: " + str(e) + " "
        success = False

    required_variables_for_new_entry = positive_value_exists(campaignx_we_vote_id) \
        and positive_value_exists(shared_by_voter_we_vote_id)
    if not required_variables_for_new_entry or not success:
        status += "SUPER_SHARE_ITEM_REQUIRED_VARIABLES_MISSING "
        results = {
            'status':                               status,
            'success':                              False,
            'campaignx_we_vote_id':                 campaignx_we_vote_id,
            'destination_full_url':                 destination_full_url,
            'personalized_message':                 personalized_message,
            'personalized_subject':                 personalized_subject,
            'shared_by_organization_type':          shared_by_organization_type,
            'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
            'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
            'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
            'super_share_item_id':                  super_share_item_id,
            'super_share_email_recipient_list':     [],
        }
        return results

    share_manager = ShareManager()
    defaults = {
        'campaignx_news_item_we_vote_id':       campaignx_news_item_we_vote_id,
        'campaignx_we_vote_id':                 campaignx_we_vote_id,
        'personalized_message':                 personalized_message,
        'personalized_message_changed':         personalized_message_changed,
        'personalized_subject':                 personalized_subject,
        'personalized_subject_changed':         personalized_subject_changed,
        'shared_by_organization_type':          shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
    }
    create_results = share_manager.update_or_create_super_share_item(
        campaignx_we_vote_id=campaignx_we_vote_id,
        shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
        defaults=defaults,
    )
    status += create_results['status']
    personalized_message = ''
    personalized_subject = ''
    super_share_email_recipient_list = []
    if create_results['super_share_item_found']:
        super_share_item = create_results['super_share_item']
        personalized_message = super_share_item.personalized_message
        personalized_subject = super_share_item.personalized_subject
        super_share_item_id = super_share_item.id

        if email_recipient_list_changed:
            if email_recipient_list_serialized:
                email_recipient_list = json.loads(email_recipient_list_serialized)
            else:
                email_recipient_list = []

            if len(email_recipient_list) > 0:
                email_results = share_manager.add_and_remove_email_recipients(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    email_recipient_list=email_recipient_list,
                    shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                    super_share_item_id=super_share_item_id,
                )

        recipients_results = share_manager.retrieve_super_share_email_recipient_list(
            super_share_item_id=super_share_item_id,
            read_only=True,
        )
        if recipients_results['email_recipient_list_found']:
            email_recipient_list = recipients_results['email_recipient_list']
            for super_share_email_recipient in email_recipient_list:
                date_sent_to_email_string = ''
                try:
                    if super_share_email_recipient.date_sent_to_email:
                        date_sent_to_email_string = super_share_email_recipient.date_sent_to_email.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    pass
                email_recipient_dict = {
                    'date_sent_to_email': date_sent_to_email_string,
                    'email_address_text': super_share_email_recipient.email_address_text.lower(),
                    'recipient_display_name': super_share_email_recipient.recipient_display_name,
                    'recipient_first_name': super_share_email_recipient.recipient_first_name,
                    'recipient_last_name': super_share_email_recipient.recipient_last_name,
                    'recipient_state_code': super_share_email_recipient.recipient_state_code,
                }
                super_share_email_recipient_list.append(email_recipient_dict)
    results = {
        'status':                               status,
        'success':                              success,
        'campaignx_we_vote_id':                 campaignx_we_vote_id,
        'destination_full_url':                 destination_full_url,
        'personalized_message':                 personalized_message,
        'personalized_subject':                 personalized_subject,
        'shared_by_organization_type':          shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
        'super_share_item_id':                  super_share_item_id,
        'super_share_email_recipient_list':     super_share_email_recipient_list,
    }
    return results


def super_share_item_send_for_api(  # superShareItemSave (for sending)
        super_share_item_id='',
        voter_device_id=''):
    status = ''
    success = True
    date_sent_to_email_string = ''
    in_draft_mode = True

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not voter_results['voter_found']:
        status += "SUPER_SHARE_ITEM_SEND_FAILED-SENDING_VOTER_NOT_FOUND "
        success = False
        results = {
            'status':                   status,
            'success':                  success,
            'date_sent_to_email':       date_sent_to_email_string,
            'in_draft_mode':            in_draft_mode,
            'send_super_share_item':    True,
            'super_share_item_id':      super_share_item_id,
        }
        return results

    voter = voter_results['voter']
    # shared_by_voter_we_vote_id = voter.we_vote_id
    # shared_by_organization_we_vote_id = voter.linked_organization_we_vote_id
    # shared_by_organization_type = INDIVIDUAL
    speaker_name = voter.get_full_name(real_name_only=True)

    share_manager = ShareManager()
    results = share_manager.retrieve_super_share_item(
        super_share_item_id=super_share_item_id,
        read_only=False,
    )
    if results['super_share_item_found']:
        super_share_item = results['super_share_item']

        from activity.controllers import update_or_create_activity_notice_seed_for_super_share_item
        activity_results = update_or_create_activity_notice_seed_for_super_share_item(
            campaignx_news_item_we_vote_id=super_share_item.campaignx_news_item_we_vote_id,
            campaignx_we_vote_id=super_share_item.campaignx_we_vote_id,
            send_super_share_item=True,
            speaker_name=speaker_name,
            speaker_organization_we_vote_id=voter.linked_organization_we_vote_id,
            speaker_voter_we_vote_id=voter.we_vote_id,
            speaker_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
            speaker_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny,
            statement_subject=super_share_item.personalized_subject,
            statement_text=super_share_item.personalized_message,
            super_share_item_id=super_share_item_id)
        status += activity_results['status']
        if activity_results['success']:
            if activity_results['activity_notice_seed_found']:
                activity_notice_seed = activity_results['activity_notice_seed']
                in_draft_mode = False
                super_share_item.in_draft_mode = False
                super_share_item.date_sent_to_email = activity_notice_seed.date_sent_to_email
                super_share_item.save()
                try:
                    date_sent_to_email_string = activity_notice_seed.date_sent_to_email.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    pass
        else:
            success = activity_results['success']

    results = {
        'status':                   status,
        'success':                  success,
        'date_sent_to_email':       date_sent_to_email_string,
        'in_draft_mode':            in_draft_mode,
        'send_super_share_item':    True,
        'super_share_item_id':      super_share_item_id,
    }
    return results
