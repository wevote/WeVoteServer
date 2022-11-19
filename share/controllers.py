# share/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.utils.timezone import now
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
from position.models import PositionListManager
import robot_detection
from share.models import SharedItem, SharedLinkClicked, SharedPermissionsGranted
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_settings.models import WeVoteSetting, WeVoteSettingsManager

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


def shared_item_list_save_for_api(  # sharedItemListSave
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
        is_remind_contact_share=False,
        other_voter_email_address_array=None,
        shared_message=None):
    status = ''
    success = True
    candidate_we_vote_id = ''
    date_first_shared = None
    hostname = ''
    measure_we_vote_id = ''
    office_we_vote_id = ''
    shared_by_display_name = None
    shared_by_organization_type = ''
    shared_by_organization_we_vote_id = ''
    shared_by_voter_we_vote_id = ''
    shared_by_we_vote_hosted_profile_image_url_large = None
    shared_by_we_vote_hosted_profile_image_url_medium = None
    shared_by_we_vote_hosted_profile_image_url_tiny = None
    shared_item_code_no_opinions = ''
    shared_item_code_all_opinions = ''
    site_owner_organization_we_vote_id = ''
    url_with_shared_item_code_no_opinions = destination_full_url  # Default to this
    url_with_shared_item_code_all_opinions = destination_full_url  # Default to this
    voter = None

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
        and positive_value_exists(shared_by_voter_we_vote_id) \
        and other_voter_email_address_array and len(other_voter_email_address_array) > 0
    if not required_variables_for_new_entry or not success:
        if positive_value_exists(is_remind_contact_share):
            status += "REMIND_CONTACT_SHARED_ITEM_LIST_REQUIRED_VARIABLES_MISSING "
        else:
            status += "SHARED_ITEM_LIST_SAVE_REQUIRED_VARIABLES_MISSING "
        results = {
            'status':                                   status,
            'success':                                  False,
            'candidate_we_vote_id':                     candidate_we_vote_id,
            'date_first_shared':                        date_first_shared,
            'destination_full_url':                     destination_full_url,
            'google_civic_election_id':                 google_civic_election_id,
            'is_ballot_share':                          is_ballot_share,
            'is_candidate_share':                       is_candidate_share,
            'is_measure_share':                         is_measure_share,
            'is_office_share':                          is_office_share,
            'is_organization_share':                    is_organization_share,
            'is_ready_share':                           is_ready_share,
            'is_remind_contact_share':                  is_remind_contact_share,
            'measure_we_vote_id':                       measure_we_vote_id,
            'office_we_vote_id':                        office_we_vote_id,
            'other_voter_email_address_array':           other_voter_email_address_array,
            'shared_by_display_name':                   shared_by_display_name,
            'shared_by_organization_type':              shared_by_organization_type,
            'shared_by_organization_we_vote_id':        shared_by_organization_we_vote_id,
            'shared_by_voter_we_vote_id':               shared_by_voter_we_vote_id,
            'shared_by_we_vote_hosted_profile_image_url_large': shared_by_we_vote_hosted_profile_image_url_large,
            'shared_by_we_vote_hosted_profile_image_url_medium': shared_by_we_vote_hosted_profile_image_url_medium,
            'shared_by_we_vote_hosted_profile_image_url_tiny': shared_by_we_vote_hosted_profile_image_url_tiny,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_all_opinions':            shared_item_code_all_opinions,
            'shared_message':                           shared_message,
            'site_owner_organization_we_vote_id':       site_owner_organization_we_vote_id,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_all_opinions':   url_with_shared_item_code_all_opinions,
        }
        return results

    share_manager = ShareManager()
    if positive_value_exists(shared_by_organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(
            organization_we_vote_id=shared_by_organization_we_vote_id,
            read_only=True)
        if results['success'] and results['organization_found']:
            shared_by_display_name = None
            if positive_value_exists(results['organization'].organization_name) \
                    and 'Voter-' not in results['organization'].organization_name:
                shared_by_display_name = results['organization'].organization_name
            shared_by_we_vote_hosted_profile_image_url_large = \
                results['organization'].we_vote_hosted_profile_image_url_large
            shared_by_we_vote_hosted_profile_image_url_medium = \
                results['organization'].we_vote_hosted_profile_image_url_medium
            shared_by_we_vote_hosted_profile_image_url_tiny = \
                results['organization'].we_vote_hosted_profile_image_url_tiny

    error_message_to_show_voter = ''
    number_of_messages_sent = 0
    success_message_to_show_voter = ''
    for other_voter_email_address_text in other_voter_email_address_array:
        one_result = shared_item_save_for_api(
            voter,
            destination_full_url=destination_full_url,
            ballot_item_we_vote_id=ballot_item_we_vote_id,
            google_civic_election_id=google_civic_election_id,
            is_ballot_share=is_ballot_share,
            is_candidate_share=is_candidate_share,
            is_measure_share=is_measure_share,
            is_office_share=is_office_share,
            is_organization_share=is_organization_share,
            is_ready_share=is_ready_share,
            is_remind_contact_share=is_remind_contact_share,
            # organization_we_vote_id=organization_we_vote_id,
            # other_voter_display_name=other_voter_display_name,
            # other_voter_first_name=other_voter_first_name,
            # other_voter_last_name=other_voter_last_name,
            # other_voter_we_vote_id=other_voter_we_vote_id,
            other_voter_email_address_text=other_voter_email_address_text,
            shared_message=shared_message,
        )
        number_of_messages_sent += one_result['number_of_messages_sent']
        if hasattr(one_result, 'success_message_to_show_voter') \
                and positive_value_exists(one_result['success_message_to_show_voter']):
            success_message_to_show_voter += one_result['success_message_to_show_voter']
        if hasattr(one_result, 'error_message_to_show_voter') \
                and positive_value_exists(one_result['error_message_to_show_voter']):
            error_message_to_show_voter += one_result['error_message_to_show_voter']

    results = {
        'status':                               status,
        'success':                              success,
        'candidate_we_vote_id':                 candidate_we_vote_id,
        'date_first_shared':                    date_first_shared,
        'destination_full_url':                 destination_full_url,
        'error_message_to_show_voter':          error_message_to_show_voter,
        'google_civic_election_id':             google_civic_election_id,
        'is_ballot_share':                      is_ballot_share,
        'is_candidate_share':                   is_candidate_share,
        'is_measure_share':                     is_measure_share,
        'is_office_share':                      is_office_share,
        'is_organization_share':                is_organization_share,
        'is_ready_share':                       is_ready_share,
        'is_remind_contact_share':              is_remind_contact_share,
        'measure_we_vote_id':                   measure_we_vote_id,
        'number_of_messages_sent':              number_of_messages_sent,
        'office_we_vote_id':                    office_we_vote_id,
        'other_voter_email_address_array':      other_voter_email_address_array,
        'shared_by_display_name':               shared_by_display_name,
        'shared_by_organization_type':          shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'shared_by_we_vote_hosted_profile_image_url_large':     shared_by_we_vote_hosted_profile_image_url_large,
        'shared_by_we_vote_hosted_profile_image_url_medium':    shared_by_we_vote_hosted_profile_image_url_medium,
        'shared_by_we_vote_hosted_profile_image_url_tiny':      shared_by_we_vote_hosted_profile_image_url_tiny,
        'shared_item_code_no_opinions':                         shared_item_code_no_opinions,
        'shared_item_code_all_opinions':                        shared_item_code_all_opinions,
        'site_owner_organization_we_vote_id':                   site_owner_organization_we_vote_id,
        'success_message_to_show_voter':                        success_message_to_show_voter,
        'url_with_shared_item_code_no_opinions':                url_with_shared_item_code_no_opinions,
        'url_with_shared_item_code_all_opinions':               url_with_shared_item_code_all_opinions,
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
    hostname = ''
    include_friends_only_positions = False
    is_ballot_share = False
    is_candidate_share = False
    is_measure_share = False
    is_office_share = False
    is_organization_share = False
    is_ready_share = False
    is_remind_contact_share = False
    google_civic_election_id = ''
    measure_we_vote_id = ''
    office_we_vote_id = ''
    other_voter_display_name = ''
    other_voter_email_address_text = ''
    other_voter_first_name = ''
    other_voter_last_name = ''
    other_voter_we_vote_id = ''
    api_call_coming_from_voter_who_shared = False
    email_secret_key = ''
    sms_secret_key = ''
    shared_by_display_name = ''
    shared_by_voter_we_vote_id = ''
    shared_by_organization_type = ''
    shared_by_organization_we_vote_id = ''
    shared_by_we_vote_hosted_profile_image_url_large = ''
    shared_by_we_vote_hosted_profile_image_url_medium = ''
    shared_by_we_vote_hosted_profile_image_url_tiny = ''
    shared_item_code_no_opinions = ''
    shared_item_code_all_opinions = ''
    shared_message = ''
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
        shared_item_code=shared_item_code,
        read_only=True)
    status += results['status']
    if not results['shared_item_found']:
        status += "SHARED_ITEM_NOT_FOUND "
        results = {
            'status':                           status,
            'success':                          False,
            'candidate_we_vote_id':             candidate_we_vote_id,
            'date_first_shared':                date_first_shared,
            'destination_full_url':             destination_full_url,
            'destination_full_url_override':    '',
            'email_secret_key':                 email_secret_key,
            'google_civic_election_id':         google_civic_election_id,
            'include_friends_only_positions':   include_friends_only_positions,
            'is_ballot_share':                  is_ballot_share,
            'is_candidate_share':               is_candidate_share,
            'is_measure_share':                 is_measure_share,
            'is_office_share':                  is_office_share,
            'is_organization_share':            is_organization_share,
            'is_ready_share':                   is_ready_share,
            'is_remind_contact_share':          is_remind_contact_share,
            'measure_we_vote_id':               measure_we_vote_id,
            'office_we_vote_id':                        office_we_vote_id,
            'other_voter_email_address_text':           other_voter_email_address_text,
            'other_voter_display_name':                 other_voter_display_name,
            'other_voter_first_name':                   other_voter_first_name,
            'other_voter_last_name':                    other_voter_last_name,
            'other_voter_we_vote_id':                   other_voter_we_vote_id,
            'shared_by_display_name':                   shared_by_display_name,
            'shared_by_voter_we_vote_id':               shared_by_voter_we_vote_id,
            'shared_by_organization_type':              shared_by_organization_type,
            'shared_by_organization_we_vote_id':        shared_by_organization_we_vote_id,
            'shared_by_we_vote_hosted_profile_image_url_large': shared_by_we_vote_hosted_profile_image_url_large,
            'shared_by_we_vote_hosted_profile_image_url_medium': shared_by_we_vote_hosted_profile_image_url_medium,
            'shared_by_we_vote_hosted_profile_image_url_tiny': shared_by_we_vote_hosted_profile_image_url_tiny,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_all_opinions':            shared_item_code_all_opinions,
            'shared_message':                           shared_message,
            'site_owner_organization_we_vote_id':       site_owner_organization_we_vote_id,
            'sms_secret_key':                           sms_secret_key,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_all_opinions':   url_with_shared_item_code_all_opinions,
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

    destination_full_url_override = ''
    if positive_value_exists(shared_item_code) and positive_value_exists(hostname):
        if positive_value_exists(shared_item.shared_item_code_ready):
            if shared_item_code == shared_item.shared_item_code_ready:
                destination_full_url_override = "https://" + hostname + "/ready"
        if positive_value_exists(shared_item.shared_item_code_remind_contacts):
            if shared_item_code == shared_item.shared_item_code_remind_contacts:
                destination_full_url_override = "https://" + hostname + "/friends/remind"

    if viewed_by_voter_we_vote_id == shared_item.shared_by_voter_we_vote_id:
        api_call_coming_from_voter_who_shared = True

    # Store that the link was clicked
    # TODO We need to adjust this since each shared item can contain the primary destination_full_url
    #  and secondary links
    if positive_value_exists(shared_item_clicked) and not positive_value_exists(api_call_coming_from_voter_who_shared):
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

        delete_secret_keys = False
        # If an email or sms secret_key was stored in the SharedItem, we can use it to sign in the person clicking the
        #  link on the first click. After the first click, we delete both secret keys so subsequent clicks don't sign
        #  the person in.
        if positive_value_exists(shared_item.email_secret_key):
            email_secret_key = shared_item.email_secret_key
            delete_secret_keys = True
        if positive_value_exists(shared_item.sms_secret_key):
            sms_secret_key = shared_item.sms_secret_key
            delete_secret_keys = True
        if delete_secret_keys:
            # Retrieve again from main db so we can delete
            retrieve_results_for_delete = share_manager.retrieve_shared_item(
                shared_item_code=shared_item_code,
                read_only=False)
            status += results['status']
            if retrieve_results_for_delete['shared_item_found']:
                shared_item = retrieve_results_for_delete['shared_item']
                try:
                    shared_item.email_secret_key = None
                    shared_item.sms_secret_key = None
                    shared_item.save()
                except Exception as e:
                    status += "COULD_NOT_CLEAR_SECRET_KEYS: " + str(e) + " "

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

    position_list = []
    if positive_value_exists(shared_item.shared_by_voter_we_vote_id) \
            and shared_item.shared_item_code_all_opinions == shared_item_code:
        position_list_manager = PositionListManager()
        results = position_list_manager.retrieve_all_positions_for_voter_simple(
            voter_we_vote_id=shared_item.shared_by_voter_we_vote_id)
        if results['position_list_found']:
            position_list = results['position_list']

    other_voter_email_address_text = shared_item.other_voter_email_address_text \
        if positive_value_exists(shared_item.other_voter_email_address_text) else ''
    other_voter_display_name = shared_item.other_voter_display_name \
        if positive_value_exists(shared_item.other_voter_display_name) else ''
    other_voter_first_name = shared_item.other_voter_first_name \
        if positive_value_exists(shared_item.other_voter_first_name) else ''
    other_voter_last_name = shared_item.other_voter_last_name \
        if positive_value_exists(shared_item.other_voter_last_name) else ''
    other_voter_we_vote_id = shared_item.other_voter_we_vote_id \
        if positive_value_exists(shared_item.other_voter_we_vote_id) else ''
    shared_by_display_name = shared_item.shared_by_display_name \
        if positive_value_exists(shared_item.shared_by_display_name) else ''
    shared_by_we_vote_hosted_profile_image_url_large = shared_item.shared_by_we_vote_hosted_profile_image_url_large \
        if positive_value_exists(shared_item.shared_by_we_vote_hosted_profile_image_url_large) else ''
    shared_by_we_vote_hosted_profile_image_url_medium = shared_item.shared_by_we_vote_hosted_profile_image_url_medium \
        if positive_value_exists(shared_item.shared_by_we_vote_hosted_profile_image_url_medium) else ''
    shared_by_we_vote_hosted_profile_image_url_tiny = shared_item.shared_by_we_vote_hosted_profile_image_url_tiny \
        if positive_value_exists(shared_item.shared_by_we_vote_hosted_profile_image_url_tiny) else ''

    if positive_value_exists(shared_item.date_first_shared):
        date_first_shared = shared_item.date_first_shared.strftime('%Y-%m-%d %H:%M:%S')

    results = {
        'status':                               status,
        'success':                              success,
        'destination_full_url':                 shared_item.destination_full_url,
        'destination_full_url_override':        destination_full_url_override,
        'email_secret_key':                     email_secret_key,  # Only returned on first click
        'is_ballot_share':                      shared_item.is_ballot_share,
        'is_candidate_share':                   shared_item.is_candidate_share,
        'is_measure_share':                     shared_item.is_measure_share,
        'is_office_share':                      shared_item.is_office_share,
        'is_organization_share':                shared_item.is_organization_share,
        'is_ready_share':                       shared_item.is_ready_share,
        'is_remind_contact_share':              shared_item.is_remind_contact_share,
        'include_friends_only_positions':       include_friends_only_positions,
        'google_civic_election_id':             shared_item.google_civic_election_id,
        'other_voter_email_address_text':       other_voter_email_address_text,
        'other_voter_display_name':             other_voter_display_name,
        'other_voter_first_name':               other_voter_first_name,
        'other_voter_last_name':                other_voter_last_name,
        'other_voter_we_vote_id':               other_voter_we_vote_id,
        'position_list':                        position_list,
        'shared_by_display_name':               shared_by_display_name,
        'shared_by_organization_type':          shared_item.shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_item.shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_item.shared_by_voter_we_vote_id,
        'shared_by_we_vote_hosted_profile_image_url_large': shared_by_we_vote_hosted_profile_image_url_large,
        'shared_by_we_vote_hosted_profile_image_url_medium': shared_by_we_vote_hosted_profile_image_url_medium,
        'shared_by_we_vote_hosted_profile_image_url_tiny': shared_by_we_vote_hosted_profile_image_url_tiny,
        'shared_message':                       shared_item.shared_message,
        'site_owner_organization_we_vote_id':   shared_item.site_owner_organization_we_vote_id,
        'sms_secret_key':                       sms_secret_key,  # Only returned on first click
        'candidate_we_vote_id':                 shared_item.candidate_we_vote_id,
        'measure_we_vote_id':                   shared_item.measure_we_vote_id,
        'office_we_vote_id':                    shared_item.office_we_vote_id,
        'date_first_shared':                    str(date_first_shared),
    }
    if api_call_coming_from_voter_who_shared:
        results['shared_item_code_no_opinions'] = shared_item.shared_item_code_no_opinions
        results['shared_item_code_all_opinions'] = shared_item.shared_item_code_all_opinions
        results['shared_item_code_ready'] = shared_item.shared_item_code_ready
        results['shared_item_code_remind_contacts'] = shared_item.shared_item_code_remind_contacts
        results['url_with_shared_item_code_no_opinions'] = url_with_shared_item_code_no_opinions
        results['url_with_shared_item_code_all_opinions'] = url_with_shared_item_code_all_opinions
    else:
        # If here we don't want to reveal the other shared_item codes
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
        if shared_item.shared_item_code_ready == shared_item_code:
            results['shared_item_code_ready'] = shared_item.shared_item_code_ready
        else:
            results['shared_item_code_ready'] = ''
        if shared_item.shared_item_code_remind_contacts == shared_item_code:
            results['shared_item_code_remind_contacts'] = shared_item.shared_item_code_remind_contacts
        else:
            results['shared_item_code_remind_contacts'] = ''
    return results


def shared_item_save_for_api(  # sharedItemSave
        voter=None,
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
        is_remind_contact_share=False,
        organization_we_vote_id='',
        other_voter_display_name='',
        other_voter_first_name='',
        other_voter_last_name='',
        other_voter_we_vote_id='',
        other_voter_email_address_text=None,
        shared_message=None):
    status = ''
    success = True
    candidate_we_vote_id = ''
    date_first_shared = None
    hostname = ''
    measure_we_vote_id = ''
    number_of_messages_sent = 0
    office_we_vote_id = ''
    ready_page_url_using_shared_item_code = ''
    remind_contacts_url_using_shared_item_code = ''
    shared_by_display_name = None
    shared_by_organization_type = ''
    shared_by_organization_we_vote_id = ''
    shared_by_voter_we_vote_id = ''
    shared_by_we_vote_hosted_profile_image_url_large = None
    shared_by_we_vote_hosted_profile_image_url_medium = None
    shared_by_we_vote_hosted_profile_image_url_tiny = None
    shared_item_code_no_opinions = ''
    shared_item_code_all_opinions = ''
    site_owner_organization_we_vote_id = ''
    url_with_shared_item_code_no_opinions = destination_full_url  # Default to this
    url_with_shared_item_code_all_opinions = destination_full_url  # Default to this

    if voter and hasattr(voter, 'linked_organization_we_vote_id'):
        shared_by_voter_we_vote_id = voter.we_vote_id
        shared_by_organization_we_vote_id = voter.linked_organization_we_vote_id
        shared_by_organization_type = INDIVIDUAL
    else:
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

    if positive_value_exists(is_remind_contact_share):
        # destination_full_url is optional because by default we only use the
        #  built-in /ready and /friends/remind links
        required_variables_for_new_entry = positive_value_exists(destination_full_url) \
            and positive_value_exists(shared_by_voter_we_vote_id) \
            and positive_value_exists(other_voter_email_address_text)
    else:
        required_variables_for_new_entry = positive_value_exists(destination_full_url) \
            and positive_value_exists(shared_by_voter_we_vote_id)
    if not required_variables_for_new_entry or not success:
        if positive_value_exists(is_remind_contact_share):
            status += "REMIND_CONTACT_SHARED_ITEM_REQUIRED_VARIABLES_MISSING "
        else:
            status += "SHARED_ITEM_SAVE_REQUIRED_VARIABLES_MISSING "
        results = {
            'status':                                   status,
            'success':                                  False,
            'candidate_we_vote_id':                     candidate_we_vote_id,
            'date_first_shared':                        date_first_shared,
            'destination_full_url':                     destination_full_url,
            'google_civic_election_id':                 google_civic_election_id,
            'is_ballot_share':                          is_ballot_share,
            'is_candidate_share':                       is_candidate_share,
            'is_measure_share':                         is_measure_share,
            'is_office_share':                          is_office_share,
            'is_organization_share':                    is_organization_share,
            'is_ready_share':                           is_ready_share,
            'is_remind_contact_share':                  is_remind_contact_share,
            'measure_we_vote_id':                       measure_we_vote_id,
            'number_of_messages_sent':                  number_of_messages_sent,
            'office_we_vote_id':                        office_we_vote_id,
            'other_voter_email_address_text':           other_voter_email_address_text,
            'other_voter_display_name':                 other_voter_display_name,
            'other_voter_first_name':                   other_voter_first_name,
            'other_voter_last_name':                    other_voter_last_name,
            'other_voter_we_vote_id':                   other_voter_we_vote_id,
            'shared_by_display_name':                   shared_by_display_name,
            'shared_by_organization_type':              shared_by_organization_type,
            'shared_by_organization_we_vote_id':        shared_by_organization_we_vote_id,
            'shared_by_voter_we_vote_id':               shared_by_voter_we_vote_id,
            'shared_by_we_vote_hosted_profile_image_url_large': shared_by_we_vote_hosted_profile_image_url_large,
            'shared_by_we_vote_hosted_profile_image_url_medium': shared_by_we_vote_hosted_profile_image_url_medium,
            'shared_by_we_vote_hosted_profile_image_url_tiny': shared_by_we_vote_hosted_profile_image_url_tiny,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_all_opinions':            shared_item_code_all_opinions,
            'shared_message':                           shared_message,
            'site_owner_organization_we_vote_id':       site_owner_organization_we_vote_id,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_all_opinions':   url_with_shared_item_code_all_opinions,
        }
        return results

    share_manager = ShareManager()
    if positive_value_exists(shared_by_organization_we_vote_id):
        results = organization_manager.retrieve_organization_from_we_vote_id(
            organization_we_vote_id=shared_by_organization_we_vote_id,
            read_only=True)
        if results['success'] and results['organization_found']:
            shared_by_display_name = None
            if positive_value_exists(results['organization'].organization_name) \
                    and 'Voter-' not in results['organization'].organization_name:
                shared_by_display_name = results['organization'].organization_name
            shared_by_we_vote_hosted_profile_image_url_large = \
                results['organization'].we_vote_hosted_profile_image_url_large
            shared_by_we_vote_hosted_profile_image_url_medium = \
                results['organization'].we_vote_hosted_profile_image_url_medium
            shared_by_we_vote_hosted_profile_image_url_tiny = \
                results['organization'].we_vote_hosted_profile_image_url_tiny
    defaults = {
        'candidate_we_vote_id':                 candidate_we_vote_id,
        'google_civic_election_id':             google_civic_election_id,
        'is_ballot_share':                      is_ballot_share,
        'is_candidate_share':                   is_candidate_share,
        'is_measure_share':                     is_measure_share,
        'is_office_share':                      is_office_share,
        'is_organization_share':                is_organization_share,
        'is_ready_share':                       is_ready_share,
        'is_remind_contact_share':              is_remind_contact_share,
        'measure_we_vote_id':                   measure_we_vote_id,
        'office_we_vote_id':                    office_we_vote_id,
        'shared_by_display_name':               shared_by_display_name,
        'shared_by_organization_type':          shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'shared_by_we_vote_hosted_profile_image_url_large':     shared_by_we_vote_hosted_profile_image_url_large,
        'shared_by_we_vote_hosted_profile_image_url_medium':    shared_by_we_vote_hosted_profile_image_url_medium,
        'shared_by_we_vote_hosted_profile_image_url_tiny':      shared_by_we_vote_hosted_profile_image_url_tiny,
        'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
    }
    recipient_email_secret_key = None
    if positive_value_exists(other_voter_email_address_text):
        defaults['other_voter_email_address_text'] = other_voter_email_address_text
        # We want to get the email_secret_key (i.e. support auto-sign) in if:
        #  1) Only one Email object exists, and it has not been verified by a voter yet
        #  2) We don't recognize this email (generate it)
        from email_outbound.models import EmailManager
        email_manager = EmailManager()
        retrieve_results = email_manager.retrieve_email_address_object(
            normalized_email_address=other_voter_email_address_text)
        if retrieve_results['email_address_object_found']:
            # Only one found. Check to make sure it hasn't been verified yet.
            recipient_email_address_object = retrieve_results['email_address_object']
            if not recipient_email_address_object.email_ownership_is_verified:
                if positive_value_exists(recipient_email_address_object.secret_key):
                    recipient_email_secret_key = recipient_email_address_object.secret_key
                elif positive_value_exists(recipient_email_address_object.we_vote_id):
                    recipient_email_secret_key = \
                        email_manager.update_email_address_with_new_secret_key(
                            email_we_vote_id=recipient_email_address_object.we_vote_id)
                if positive_value_exists(recipient_email_secret_key):
                    status += "SECRET_KEY_INCLUDED_ONE_FOUND_ONE_EMAIL_OBJECT "
        elif retrieve_results['success'] and not retrieve_results['email_address_list_found']:
            # Generate new EmailAddress because none found
            create_results = email_manager.create_email_address(
                normalized_email_address=other_voter_email_address_text)
            if create_results['email_address_object_saved']:
                recipient_email_address_object = create_results['email_address_object']
                if positive_value_exists(recipient_email_address_object.secret_key):
                    recipient_email_secret_key = recipient_email_address_object.secret_key
                    if positive_value_exists(recipient_email_secret_key):
                        status += "SECRET_KEY_INCLUDED_ONE_FOUND_LIST "
                else:
                    # If a secret key wasn't generated upon email creation, don't try again
                    status += "CREATE_EMAIL_DID_NOT_GENERATE_SECRET_KEY "
        else:
            status += "CANNOT_INCLUDE_SECRET_KEY "
    if positive_value_exists(recipient_email_secret_key):
        defaults['email_secret_key'] = recipient_email_secret_key
    if positive_value_exists(other_voter_we_vote_id):
        defaults['other_voter_we_vote_id'] = other_voter_we_vote_id
    if positive_value_exists(other_voter_display_name):
        defaults['other_voter_display_name'] = other_voter_display_name
    if positive_value_exists(other_voter_first_name):
        defaults['other_voter_first_name'] = other_voter_first_name
    if positive_value_exists(other_voter_last_name):
        defaults['other_voter_last_name'] = other_voter_last_name
    if positive_value_exists(shared_message):
        defaults['shared_message'] = shared_message
    # TODO Limit number of reminders to X per week?
    # Since reminder email is only sent upon creation, and we don't need to edit these, always
    #  create a new SharedItem when is_remind_contact_share
    force_create_new = is_remind_contact_share
    create_results = share_manager.update_or_create_shared_item(
        destination_full_url=destination_full_url,
        force_create_new=force_create_new,
        shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        defaults=defaults,
    )
    status += create_results['status']
    if create_results['shared_item_found']:
        shared_item = create_results['shared_item']
        if positive_value_exists(shared_item.date_first_shared):
            date_first_shared = shared_item.date_first_shared.strftime('%Y-%m-%d %H:%M:%S')

        shared_item_code_no_opinions = shared_item.shared_item_code_no_opinions
        url_with_shared_item_code_no_opinions = "https://" + hostname + "/-" + shared_item_code_no_opinions

        shared_item_code_all_opinions = shared_item.shared_item_code_all_opinions
        url_with_shared_item_code_all_opinions = "https://" + hostname + "/-" + shared_item_code_all_opinions

        # It is better to have a trackable code, but we can still link to the right page if we don't have code
        if positive_value_exists(shared_item.shared_item_code_ready):
            ready_page_url_using_shared_item_code = "https://" + hostname + "/-" + shared_item.shared_item_code_ready
        else:
            ready_page_url_using_shared_item_code = "https://" + hostname + "/"

        # It is better to have a trackable code, but we can still link to the right page if we don't have code
        if positive_value_exists(shared_item.shared_item_code_remind_contacts):
            remind_contacts_url_using_shared_item_code = \
                "https://" + hostname + "/-" + shared_item.shared_item_code_remind_contacts
        else:
            remind_contacts_url_using_shared_item_code = "https://" + hostname + "/friends/remind"
    else:
        remind_contacts_url_using_shared_item_code = "https://" + hostname + "/friends/remind"

    if create_results['shared_item_created'] and positive_value_exists(is_remind_contact_share):
        # Trigger send of the reminder
        from friend.controllers import remind_contact_by_email_send_for_api
        results = remind_contact_by_email_send_for_api(
            voter=voter,
            voter_device_id=voter_device_id,
            email_addresses_raw=other_voter_email_address_text,
            invitation_message=shared_message,
            other_voter_first_name=other_voter_first_name,
            sender_display_name=shared_by_display_name,
            ready_page_url_using_shared_item_code=ready_page_url_using_shared_item_code,
            remind_contacts_url_using_shared_item_code=remind_contacts_url_using_shared_item_code,
            web_app_root_url=hostname)
        status += results['status']
        number_of_messages_sent += results['number_of_messages_sent']

    results = {
        'status':                               status,
        'success':                              success,
        'candidate_we_vote_id':                 candidate_we_vote_id,
        'date_first_shared':                    date_first_shared,
        'destination_full_url':                 destination_full_url,
        'google_civic_election_id':             google_civic_election_id,
        'is_ballot_share':                      is_ballot_share,
        'is_candidate_share':                   is_candidate_share,
        'is_measure_share':                     is_measure_share,
        'is_office_share':                      is_office_share,
        'is_organization_share':                is_organization_share,
        'is_ready_share':                       is_ready_share,
        'is_remind_contact_share':              is_remind_contact_share,
        'measure_we_vote_id':                   measure_we_vote_id,
        'number_of_messages_sent':              number_of_messages_sent,
        'office_we_vote_id':                    office_we_vote_id,
        'other_voter_display_name':             other_voter_display_name,
        'other_voter_email_address_text':       other_voter_email_address_text,
        'other_voter_first_name':               other_voter_first_name,
        'other_voter_last_name':                other_voter_last_name,
        'other_voter_we_vote_id':               other_voter_we_vote_id,
        'shared_by_display_name':               shared_by_display_name,
        'shared_by_organization_type':          shared_by_organization_type,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'shared_by_we_vote_hosted_profile_image_url_large':     shared_by_we_vote_hosted_profile_image_url_large,
        'shared_by_we_vote_hosted_profile_image_url_medium':    shared_by_we_vote_hosted_profile_image_url_medium,
        'shared_by_we_vote_hosted_profile_image_url_tiny':      shared_by_we_vote_hosted_profile_image_url_tiny,
        'shared_item_code_no_opinions':                         shared_item_code_no_opinions,
        'shared_item_code_all_opinions':                        shared_item_code_all_opinions,
        'site_owner_organization_we_vote_id':                   site_owner_organization_we_vote_id,
        'url_with_shared_item_code_no_opinions':                url_with_shared_item_code_no_opinions,
        'url_with_shared_item_code_all_opinions':               url_with_shared_item_code_all_opinions,
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


def update_shared_item_statistics(number_to_update=10000):
    shared_items_changed = 0
    shared_items_not_changed = 0
    status = ''
    success = True

    # Get last ShareLinkClicked id: "share_link_clicked_count_statistics_updated_through_id"
    we_vote_settings_manager = WeVoteSettingsManager()
    results = we_vote_settings_manager.fetch_setting_results('share_link_clicked_count_statistics_updated_through_id')
    share_link_clicked_count_statistics_updated_through_id = 0
    if not results['success']:
        status += results['status']
        success = False
        count_updates_remaining = 0
        results = {
            'status':                   status,
            'success':                  success,
            'count_updates_remaining':  count_updates_remaining,
            'shared_items_changed':     shared_items_changed,
            'shared_items_not_changed': shared_items_not_changed,
        }
        return results
    elif results['we_vote_setting_found']:
        share_link_clicked_count_statistics_updated_through_id = results['setting_value']

    highest_shared_link_clicked_id = 0
    if positive_value_exists(share_link_clicked_count_statistics_updated_through_id):
        status += "share_link_clicked_count_statistics_updated_through_id-FOUND: {share_link_clicked_id} ".format(
            share_link_clicked_id=share_link_clicked_count_statistics_updated_through_id
        )
        highest_shared_link_clicked_id = share_link_clicked_count_statistics_updated_through_id
    else:
        status += "Starting update at share_link_clicked.id = 0 "

    # Get a list of shared_item_id's which have had activity in X period of time or since...
    clicked_queryset = SharedLinkClicked.objects.using('readonly').all()
    clicked_queryset = clicked_queryset.order_by('id')
    clicked_queryset = clicked_queryset.filter(id__gt=share_link_clicked_count_statistics_updated_through_id)

    if not positive_value_exists(number_to_update):
        number_to_update = 10000
    clicked_queryset = clicked_queryset[:number_to_update]
    shared_link_clicked_list = list(clicked_queryset)
    shared_item_id_list = []
    for one_shared_link_clicked in shared_link_clicked_list:
        if one_shared_link_clicked.id > highest_shared_link_clicked_id:
            highest_shared_link_clicked_id = one_shared_link_clicked.id
        if one_shared_link_clicked.shared_item_id not in shared_item_id_list:
            shared_item_id_list.append(one_shared_link_clicked.shared_item_id)

    # Now get all the SharedItems to update
    queryset = SharedItem.objects.all()
    queryset = queryset.filter(id__in=shared_item_id_list)
    shared_item_list = list(queryset)

    for shared_item in shared_item_list:
        prior_shared_link_clicked_count = shared_item.shared_link_clicked_count
        prior_shared_link_clicked_unique_viewer_count = shared_item.shared_link_clicked_unique_viewer_count
        clicked_queryset = SharedLinkClicked.objects.using('readonly').all()
        clicked_queryset = clicked_queryset.filter(shared_item_id=shared_item.id)
        shared_item.shared_link_clicked_count = clicked_queryset.count()
        unique_queryset = clicked_queryset.order_by('shared_item_id', 'viewed_by_voter_we_vote_id')\
            .distinct('shared_item_id', 'viewed_by_voter_we_vote_id')
        shared_item.shared_link_clicked_unique_viewer_count = unique_queryset.count()
        if prior_shared_link_clicked_count != shared_item.shared_link_clicked_count or \
                prior_shared_link_clicked_unique_viewer_count != shared_item.shared_link_clicked_unique_viewer_count:
            shared_items_changed += 1
            try:
                shared_item.shared_link_clicked_count_last_updated = now()
                shared_item.save()
                shared_items_changed += 1
            except Exception as e:
                status += "FAILED_SAVE: " + str(e) + " "
                success = False
                break
        else:
            shared_items_not_changed += 1

    if success and positive_value_exists(highest_shared_link_clicked_id):
        # Update the "share_link_clicked_count_statistics_updated_through_id"
        results = we_vote_settings_manager.save_setting(
            setting_name="share_link_clicked_count_statistics_updated_through_id",
            setting_value=highest_shared_link_clicked_id,
            value_type=WeVoteSetting.INTEGER)
        if not results['success']:
            status += results['status']
            success = False

    # How many remain to be updated in the future?
    queryset = SharedLinkClicked.objects.using('readonly').all()
    queryset = queryset.filter(id__gt=highest_shared_link_clicked_id)
    count_updates_remaining = queryset.count()

    results = {
        'status':                   status,
        'success':                  success,
        'count_updates_remaining':  count_updates_remaining,
        'shared_items_changed':     shared_items_changed,
        'shared_items_not_changed': shared_items_not_changed,
    }
    return results
