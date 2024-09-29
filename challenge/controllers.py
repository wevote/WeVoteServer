# challenge/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers_participant import generate_challenge_participant_dict_from_challenge_participant_object
from .models import Challenge, ChallengeListedByOrganization, ChallengeManager, ChallengeNewsItem, ChallengeOwner, \
    ChallengePolitician, ChallengeParticipant, CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED, CHALLENGE_UNIQUE_IDENTIFIERS, \
    FINAL_ELECTION_DATE_COOL_DOWN
import base64
import copy
from django.contrib import messages
from django.db.models import Q
from image.controllers import cache_image_object_to_aws, create_resized_images
import json
from io import BytesIO
from PIL import Image, ImageOps
import re
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import generate_date_as_integer, get_current_date_as_integer, DATE_FORMAT_YMD_HMS

logger = wevote_functions.admin.get_logger(__name__)

# Search for in image/controllers.py as well
CHALLENGE_PHOTO_ORIGINAL_MAX_WIDTH = 1200
CHALLENGE_PHOTO_ORIGINAL_MAX_HEIGHT = 628
CHALLENGE_PHOTO_LARGE_MAX_WIDTH = 575
CHALLENGE_PHOTO_LARGE_MAX_HEIGHT = 301
CHALLENGE_PHOTO_MEDIUM_MAX_WIDTH = 224
CHALLENGE_PHOTO_MEDIUM_MAX_HEIGHT = 117
CHALLENGE_PHOTO_SMALL_MAX_WIDTH = 140
CHALLENGE_PHOTO_SMALL_MAX_HEIGHT = 73

CHALLENGE_ERROR_DICT = {
    'status': 'ERROR ',
    'success': False,
    'challenge_description': '',
    'challenge_invite_text_default': '',
    'challenge_title': '',
    'challenge_news_item_list': [],
    'challenge_owner_list': [],
    'challenge_politician_list': [],
    'challenge_politician_list_exists': False,
    'challenge_politician_starter_list': [],
    'challenge_we_vote_id': '',
    'final_election_date_as_integer': None,
    'final_election_date_in_past': False,
    'in_draft_mode': True,
    'is_blocked_by_we_vote': False,
    'is_blocked_by_we_vote_reason': '',
    'is_participants_count_minimum_exceeded': False,
    'latest_challenge_participant_list': [],
    'politician_we_vote_id': '',
    'opposers_count': 0,
    'order_in_list': 0,
    'seo_friendly_path': '',
    'seo_friendly_path_list': [],
    'participants_count': 0,
    'participants_count_next_goal': 0,
    'participants_count_victory_goal': 0,
    'visible_on_this_site': False,
    'voter_challenge_participant': {},
    'voter_can_send_updates_to_challenge': False,
    'voter_can_vote_for_politician_we_vote_ids': [],
    'voter_is_challenge_owner': False,
    'voter_signed_in_with_email': False,
    'we_vote_hosted_challenge_photo_large_url': '',
    'we_vote_hosted_challenge_photo_medium_url': '',
    'we_vote_hosted_challenge_photo_small_url': '',
}


def challenge_list_retrieve_for_api(  # challengeListRetrieve
        hostname='',
        limit_to_this_state_code='',
        recommended_challenges_for_challenge_we_vote_id='',
        request=None,
        search_text='',
        voter_device_id=''):
    """

    :param hostname:
    :param limit_to_this_state_code:
    :param recommended_challenges_for_challenge_we_vote_id:
    :param request:
    :param search_text:
    :param voter_device_id:
    :return:
    """
    challenge_dict_list = []
    status = ""
    promoted_challenge_list_returned = True
    voter_can_vote_for_politicians_list_returned = True
    voter_owned_challenge_list_returned = True
    voter_started_challenge_list_returned = True
    challenge_we_vote_ids_where_voter_is_participant_returned = True

    if positive_value_exists(recommended_challenges_for_challenge_we_vote_id) or positive_value_exists(search_text):
        # Do not retrieve certain data if returning recommended challenges
        promoted_challenge_list_returned = False
        voter_can_vote_for_politicians_list_returned = False
        voter_owned_challenge_list_returned = False
        voter_started_challenge_list_returned = False
        challenge_we_vote_ids_where_voter_is_participant_returned = False

    promoted_challenge_we_vote_ids = []
    voter_can_send_updates_challenge_we_vote_ids = []
    voter_owned_challenge_we_vote_ids = []
    voter_started_challenge_we_vote_ids = []
    challenge_we_vote_ids_where_voter_is_participant = []

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id=voter_device_id, read_only=True)
    if not positive_value_exists(voter_results['voter_found']):
        status += 'VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED '
        json_data = {
            'status': status,
            'success': False,
            'challenge_list': [],
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

    visible_on_this_site_challenge_we_vote_id_list = []
    challenge_manager = ChallengeManager()
    if positive_value_exists(recommended_challenges_for_challenge_we_vote_id):
        results = retrieve_recommended_challenge_list_for_challenge_we_vote_id(
            request=request,
            voter_device_id=voter_device_id,
            voter_we_vote_id=voter_we_vote_id,
            challenge_we_vote_id=recommended_challenges_for_challenge_we_vote_id,
            site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
    else:
        if positive_value_exists(site_owner_organization_we_vote_id):
            results = challenge_manager.retrieve_challenge_list_for_private_label(
                including_started_by_voter_we_vote_id=voter_we_vote_id,
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            visible_on_this_site_challenge_we_vote_id_list = results['visible_on_this_site_challenge_we_vote_id_list']
        else:
            results = challenge_manager.retrieve_challenge_list(
                including_started_by_voter_we_vote_id=voter_we_vote_id,
                limit_to_this_state_code=limit_to_this_state_code,
                search_text=search_text)
    success = results['success']
    status += results['status']
    challenge_list = results['challenge_list']
    challenge_list_found = results['challenge_list_found']

    if success:
        results = generate_challenge_dict_list_from_challenge_object_list(
            challenge_object_list=challenge_list,
            hostname=hostname,
            promoted_challenge_we_vote_ids=promoted_challenge_we_vote_ids,
            site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
            visible_on_this_site_challenge_we_vote_id_list=visible_on_this_site_challenge_we_vote_id_list,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )
        challenge_dict_list = results['challenge_dict_list']
        status += results['status']
        if not results['success']:
            success = False

    if success and voter_started_challenge_list_returned:
        results = challenge_manager.retrieve_challenge_we_vote_id_list_started_by_voter(
            started_by_voter_we_vote_id=voter_we_vote_id)
        if not results['success']:
            voter_started_challenge_list_returned = False
        else:
            voter_started_challenge_we_vote_ids = results['challenge_we_vote_id_list']

    if success and challenge_we_vote_ids_where_voter_is_participant_returned:
        participant_list_results = challenge_manager.retrieve_challenge_participant_list(
            voter_we_vote_id=voter_we_vote_id,
            limit=0,
            require_visible_to_public=False,
            read_only=True)
        if participant_list_results['participant_list_found']:
            participant_list = participant_list_results['participant_list']
            for one_participant in participant_list:
                challenge_we_vote_ids_where_voter_is_participant.append(one_participant.challenge_we_vote_id)

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'challenge_list':                           challenge_dict_list,
        'challenge_list_found':                     challenge_list_found,
    }
    if promoted_challenge_list_returned:
        json_data['promoted_challenge_list_returned'] = True
        json_data['promoted_challenge_we_vote_ids'] = promoted_challenge_we_vote_ids
    if positive_value_exists(recommended_challenges_for_challenge_we_vote_id):
        json_data['recommended_challenges_for_challenge_we_vote_id'] = recommended_challenges_for_challenge_we_vote_id
    if voter_can_vote_for_politicians_list_returned:
        json_data['voter_can_vote_for_politicians_list_returned'] = True
        json_data['voter_can_vote_for_politician_we_vote_ids'] = voter_can_vote_for_politician_we_vote_ids
    if voter_owned_challenge_list_returned:
        json_data['voter_owned_challenge_list_returned'] = True
        json_data['voter_owned_challenge_we_vote_ids'] = voter_owned_challenge_we_vote_ids
        json_data['voter_can_send_updates_challenge_we_vote_ids'] = voter_can_send_updates_challenge_we_vote_ids
    if voter_started_challenge_list_returned:
        json_data['voter_started_challenge_list_returned'] = True
        json_data['voter_started_challenge_we_vote_ids'] = voter_started_challenge_we_vote_ids
    if challenge_we_vote_ids_where_voter_is_participant_returned:
        json_data['challenge_we_vote_ids_where_voter_is_participant_returned'] = True
        json_data['challenge_we_vote_ids_where_voter_is_participant'] = challenge_we_vote_ids_where_voter_is_participant
    return json_data


def challenge_news_item_save_for_api(  # challengeNewsItemSave
        challenge_news_subject='',
        challenge_news_subject_changed=False,
        challenge_news_text='',
        challenge_news_text_changed=False,
        challenge_news_item_we_vote_id='',
        challenge_we_vote_id='',
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
            'challenge_news_subject':            '',
            'challenge_news_text':               '',
            'challenge_news_item_we_vote_id':   '',
            'challenge_we_vote_id':             '',
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

    if not positive_value_exists(challenge_we_vote_id):
        status += "CHALLENGE_WE_VOTE_ID_REQUIRED "
        results = {
            'status':                           status,
            'success':                          False,
            'challenge_news_subject':            '',
            'challenge_news_text':               '',
            'challenge_news_item_we_vote_id':   '',
            'challenge_we_vote_id':             '',
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

    challenge_manager = ChallengeManager()
    voter_is_challenge_owner = challenge_manager.is_voter_challenge_owner(
        challenge_we_vote_id=challenge_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
    )
    if not positive_value_exists(voter_is_challenge_owner):
        status += "VOTER_DOES_NOT_HAVE_RIGHT_TO_CREATE_NEWS_ITEM "
        results = {
            'status':                           status,
            'success':                          False,
            'challenge_news_subject':            '',
            'challenge_news_text':               '',
            'challenge_news_item_we_vote_id':   '',
            'challenge_we_vote_id':             '',
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
        'challenge_news_subject':           challenge_news_subject,
        'challenge_news_subject_changed':   challenge_news_subject_changed,
        'challenge_news_text':              challenge_news_text,
        'challenge_news_text_changed':      challenge_news_text_changed,
        'in_draft_mode':                    in_draft_mode,
        'in_draft_mode_changed':            in_draft_mode_changed,
        'visible_to_public':                visible_to_public,
        'visible_to_public_changed':        visible_to_public_changed,
    }
    create_results = challenge_manager.update_or_create_challenge_news_item(
        challenge_news_item_we_vote_id=challenge_news_item_we_vote_id,
        challenge_we_vote_id=challenge_we_vote_id,
        organization_we_vote_id=linked_organization_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        update_values=update_values,
    )

    status += create_results['status']
    challenge_news_item = None
    challenge_news_item_found = False
    date_sent_to_email_found = False
    if create_results['challenge_news_item_found']:
        challenge_news_item = create_results['challenge_news_item']
        date_sent_to_email_found = positive_value_exists(challenge_news_item.date_sent_to_email)
        challenge_news_item_found = True

    send_challenge_news_item = positive_value_exists(send_now)
    if challenge_news_item_found:
        results = challenge_manager.retrieve_challenge(
            challenge_we_vote_id=challenge_we_vote_id,
            read_only=True,
        )
        if results['challenge_found']:
            challenge = results['challenge']

            from activity.controllers import update_or_create_activity_notice_seed_for_challenge_news_item
            activity_results = update_or_create_activity_notice_seed_for_challenge_news_item(
                challenge_news_item_we_vote_id=challenge_news_item.we_vote_id,
                challenge_we_vote_id=challenge.we_vote_id,
                send_challenge_news_item=send_challenge_news_item,
                speaker_name=challenge_news_item.speaker_name,
                speaker_organization_we_vote_id=challenge_news_item.organization_we_vote_id,
                speaker_voter_we_vote_id=challenge_news_item.voter_we_vote_id,
                speaker_profile_image_url_medium=challenge_news_item.we_vote_hosted_profile_image_url_medium,
                speaker_profile_image_url_tiny=challenge_news_item.we_vote_hosted_profile_image_url_tiny,
                statement_subject=challenge_news_item.challenge_news_subject,
                statement_text=challenge_news_item.challenge_news_text)
            status += activity_results['status']
            if activity_results['success'] and send_challenge_news_item and not date_sent_to_email_found:
                if activity_results['activity_notice_seed_found']:
                    activity_notice_seed = activity_results['activity_notice_seed']
                    challenge_news_item.date_sent_to_email = activity_notice_seed.date_sent_to_email
                    challenge_news_item.save()

    if challenge_news_item_found:
        date_last_changed_string = ''
        date_posted_string = ''
        date_sent_to_email_string = ''
        try:
            date_last_changed_string = challenge_news_item.date_last_changed.strftime(DATE_FORMAT_YMD_HMS) # '%Y-%m-%d %H:%M:%S'
            date_posted_string = challenge_news_item.date_posted.strftime(DATE_FORMAT_YMD_HMS) # '%Y-%m-%d %H:%M:%S'
            date_sent_to_email_string = challenge_news_item.date_posted.strftime(DATE_FORMAT_YMD_HMS) # '%Y-%m-%d %H:%M:%S'
        except Exception as e:
            status += "DATE_CONVERSION_ERROR: " + str(e) + " "
        results = {
            'status':                       status,
            'success':                      success,
            'challenge_news_subject':       challenge_news_item.challenge_news_subject,
            'challenge_news_text':          challenge_news_item.challenge_news_text,
            'challenge_news_item_we_vote_id': challenge_news_item.we_vote_id,
            'challenge_we_vote_id':         challenge_news_item.challenge_we_vote_id,
            'date_last_changed':            date_last_changed_string,
            'date_posted':                  date_posted_string,
            'date_sent_to_email':           date_sent_to_email_string,
            'in_draft_mode':                challenge_news_item.in_draft_mode,
            'organization_we_vote_id':      challenge_news_item.organization_we_vote_id,
            'speaker_name':                 challenge_news_item.speaker_name,
            'voter_we_vote_id':             challenge_news_item.voter_we_vote_id,
            'we_vote_hosted_profile_photo_image_url_medium':
                challenge_news_item.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_photo_image_url_tiny': challenge_news_item.we_vote_hosted_profile_image_url_tiny,
        }
        return results
    else:
        status += "CHALLENGE_NEWS_ITEM_NOT_FOUND_ERROR "
        results = {
            'status':                           status,
            'success':                          False,
            'challenge_news_subject':            '',
            'challenge_news_text':               '',
            'challenge_news_item_we_vote_id':   '',
            'challenge_we_vote_id':             '',
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


def challenge_retrieve_for_api(  # challengeRetrieve & challengeRetrieveAsOwner (No CDN)
        voter_device_id='',
        challenge_we_vote_id='',
        seo_friendly_path='',
        as_owner=False,
        hostname=''):
    status = ''
    success = True
    challenge_dict = {}
    challenge_error_dict = copy.deepcopy(CHALLENGE_ERROR_DICT)
    challenge_error_dict['seo_friendly_path'] = seo_friendly_path
    voter_signed_in_with_email = False
    voter_we_vote_id = ''

    challenge_manager = ChallengeManager()
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
    if positive_value_exists(as_owner):
        if not positive_value_exists(voter_we_vote_id):
            status += "VALID_VOTER_ID_MISSING "
            results = challenge_error_dict
            results['status'] = status
            return results
        results = challenge_manager.retrieve_challenge_as_owner(
            challenge_we_vote_id=challenge_we_vote_id,
            seo_friendly_path=seo_friendly_path,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
        voter_is_challenge_owner = results['viewer_is_owner']
    else:
        results = challenge_manager.retrieve_challenge(
            challenge_we_vote_id=challenge_we_vote_id,
            seo_friendly_path=seo_friendly_path,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
        voter_is_challenge_owner = results['viewer_is_owner']
    status += results['status']
    if not results['success']:
        status += "CHALLENGE_RETRIEVE_ERROR "
        results = challenge_error_dict
        results['status'] = status
        return results
    elif not results['challenge_found']:
        status += "CHALLENGE_NOT_FOUND: "
        status += results['status'] + " "
        results = challenge_error_dict
        results['status'] = status
        results['success'] = True
        return results

    challenge = results['challenge']
    challenge_owner_list = results['challenge_owner_list']
    seo_friendly_path_list = results['seo_friendly_path_list']

    if hasattr(challenge, 'we_vote_id'):
        # We need to know all the politicians this voter can vote for, so we can figure out
        #  if the voter can vote for any politicians in the election
        # May 6, 2023: TURNED OFF BECAUSE TOO TIME CONSUMING FOR NOW. Perhaps pre-calculate?
        # from ballot.controllers import what_voter_can_vote_for
        # results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        # voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']
        voter_can_vote_for_politician_we_vote_ids = []

        generate_results = generate_challenge_dict_from_challenge_object(
            challenge=challenge,
            challenge_owner_list=challenge_owner_list,
            hostname=hostname,
            seo_friendly_path_list=seo_friendly_path_list,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_is_challenge_owner=voter_is_challenge_owner,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )
        challenge_dict = generate_results['challenge_dict']
        status += generate_results['status']
        if not generate_results['success']:
            success = False
    else:
        pass
    if 'challenge_description' in challenge_dict:
        results = challenge_dict
    else:
        results = challenge_error_dict

    results['status'] = status
    results['success'] = success
    return results


def challenge_save_for_api(  # challengeSave & challengeStartSave
        challenge_description='',
        challenge_description_changed=False,
        challenge_invite_text_default='',
        challenge_invite_text_default_changed=False,
        in_draft_mode=False,
        in_draft_mode_changed=False,
        is_start_save=False,
        challenge_photo_from_file_reader='',
        challenge_photo_changed=False,
        challenge_photo_delete=False,
        challenge_photo_delete_changed=False,
        challenge_title='',
        challenge_title_changed=False,
        challenge_we_vote_id='',
        hostname='',
        politician_delete_list_serialized='',
        politician_starter_list_serialized='',
        politician_starter_list_changed=False,
        request=None,
        voter_device_id=''):
    status = ''
    success = True
    challenge_error_dict = copy.deepcopy(CHALLENGE_ERROR_DICT)

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = challenge_error_dict
        results['status'] = status
        return results

    if positive_value_exists(in_draft_mode_changed) and not positive_value_exists(in_draft_mode):
        # Make sure organization object has necessary images needed for ChallengeOwner and ChallengeParticipant
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

        # To publish a challenge, voter must be signed in
        if not voter.is_signed_in():
            status += "MUST_BE_SIGNED_IN_TO_PUBLISH "
            results = challenge_error_dict
            results['status'] = status
            return results

    challenge_manager = ChallengeManager()
    viewer_is_owner = False
    if positive_value_exists(challenge_we_vote_id):
        viewer_is_owner = challenge_manager.is_voter_challenge_owner(
            challenge_we_vote_id=challenge_we_vote_id, voter_we_vote_id=voter_we_vote_id)
        if not positive_value_exists(viewer_is_owner):
            if is_start_save:
                # Get owner_list
                results = challenge_manager.retrieve_challenge_as_owner(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                    read_only=True,
                )
                challenge_owner_list = results['challenge_owner_list']
                # If there isn't another owner, make this voter the owner
                temporarily_true = True
                if temporarily_true or len(challenge_owner_list) == 0:
                    owner_results = challenge_manager.update_or_create_challenge_owner(
                        challenge_we_vote_id=challenge_we_vote_id,
                        organization_we_vote_id=linked_organization_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                    status += owner_results['status']
                    viewer_is_owner = owner_results['challenge_owner_created'] or owner_results['challenge_owner_found']

        if not positive_value_exists(viewer_is_owner):
            status += "VOTER_IS_NOT_OWNER_OF_CHALLENGE "
            results = challenge_error_dict
            results['status'] = status
            return results
        # Save challenge_photo_from_file_reader and get back we_vote_hosted_challenge_photo_original_url
        we_vote_hosted_challenge_photo_large_url = None
        we_vote_hosted_challenge_photo_medium_url = None
        we_vote_hosted_challenge_photo_original_url = None
        we_vote_hosted_challenge_photo_small_url = None
        if challenge_photo_changed and challenge_photo_from_file_reader:
            photo_results = challenge_save_photo_from_file_reader(
                challenge_we_vote_id=challenge_we_vote_id,
                challenge_photo_from_file_reader=challenge_photo_from_file_reader)
            if photo_results['we_vote_hosted_challenge_photo_original_url']:
                we_vote_hosted_challenge_photo_original_url = \
                    photo_results['we_vote_hosted_challenge_photo_original_url']
                # Now we want to resize to a large version
                create_resized_image_results = create_resized_images(
                    challenge_we_vote_id=challenge_we_vote_id,
                    challenge_photo_url_https=we_vote_hosted_challenge_photo_original_url)
                we_vote_hosted_challenge_photo_large_url = \
                    create_resized_image_results['cached_resized_image_url_large']
                we_vote_hosted_challenge_photo_medium_url = \
                    create_resized_image_results['cached_resized_image_url_medium']
                we_vote_hosted_challenge_photo_small_url = \
                    create_resized_image_results['cached_resized_image_url_tiny']

        update_values = {
            'challenge_description':                challenge_description,
            'challenge_description_changed':        challenge_description_changed,
            'challenge_invite_text_default':    challenge_invite_text_default,
            'challenge_invite_text_default_changed': challenge_invite_text_default_changed,
            'in_draft_mode':                        in_draft_mode,
            'in_draft_mode_changed':                in_draft_mode_changed,
            'challenge_photo_changed':              challenge_photo_changed,
            'challenge_photo_delete':               challenge_photo_delete,
            'challenge_photo_delete_changed':       challenge_photo_delete_changed,
            'challenge_title':                      challenge_title,
            'challenge_title_changed':              challenge_title_changed,
            'politician_delete_list_serialized':    politician_delete_list_serialized,
            'politician_starter_list_changed':      politician_starter_list_changed,
            'politician_starter_list_serialized':   politician_starter_list_serialized,
            'we_vote_hosted_challenge_photo_large_url': we_vote_hosted_challenge_photo_large_url,
            'we_vote_hosted_challenge_photo_medium_url': we_vote_hosted_challenge_photo_medium_url,
            'we_vote_hosted_challenge_photo_small_url': we_vote_hosted_challenge_photo_small_url,
            'we_vote_hosted_challenge_photo_original_url': we_vote_hosted_challenge_photo_original_url,
        }
        create_results = challenge_manager.update_or_create_challenge(
            challenge_we_vote_id=challenge_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=linked_organization_we_vote_id,
            update_values=update_values,
        )
    else:
        # If here, we are working with a draft
        # Save challenge_photo_from_file_reader and get back we_vote_hosted_challenge_photo_large_url
        #  after initial update
        update_values = {
            'challenge_description':                challenge_description,
            'challenge_description_changed':        challenge_description_changed,
            'challenge_invite_text_default':    challenge_invite_text_default,
            'challenge_invite_text_default_changed': challenge_invite_text_default_changed,
            'in_draft_mode':                        in_draft_mode,
            'in_draft_mode_changed':                in_draft_mode_changed,
            'challenge_photo_delete':               challenge_photo_delete,
            'challenge_photo_delete_changed':       challenge_photo_delete_changed,
            'challenge_title':                      challenge_title,
            'challenge_title_changed':              challenge_title_changed,
            'politician_delete_list_serialized':    politician_delete_list_serialized,
            'politician_starter_list_changed':      politician_starter_list_changed,
            'politician_starter_list_serialized':   politician_starter_list_serialized,
        }
        create_results = challenge_manager.update_or_create_challenge(
            voter_we_vote_id=voter_we_vote_id,
            organization_we_vote_id=linked_organization_we_vote_id,
            update_values=update_values,
        )
        if create_results['challenge_created']:
            # Challenge was just created, so save the voter as an owner
            challenge_we_vote_id = create_results['challenge_we_vote_id']
            owner_results = challenge_manager.update_or_create_challenge_owner(
                challenge_we_vote_id=challenge_we_vote_id,
                organization_we_vote_id=linked_organization_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            status += owner_results['status']
        if create_results['challenge_found'] and challenge_photo_changed:
            challenge = create_results['challenge']
            challenge_we_vote_id = create_results['challenge_we_vote_id']
            if challenge_photo_from_file_reader:
                photo_results = challenge_save_photo_from_file_reader(
                    challenge_we_vote_id=challenge_we_vote_id,
                    challenge_photo_from_file_reader=challenge_photo_from_file_reader)
                if photo_results['we_vote_hosted_challenge_photo_original_url']:
                    challenge.we_vote_hosted_challenge_photo_original_url = \
                        photo_results['we_vote_hosted_challenge_photo_original_url']

                    # Now we want to resize to a large version
                    # Temp: Store as a campaignx photo
                    create_resized_image_results = create_resized_images(
                        campaignx_we_vote_id=challenge_we_vote_id,
                        campaignx_photo_url_https=challenge.we_vote_hosted_challenge_photo_original_url)
                    challenge.we_vote_hosted_challenge_photo_large_url = \
                        create_resized_image_results['cached_resized_image_url_large']
                    challenge.we_vote_hosted_challenge_photo_medium_url = \
                        create_resized_image_results['cached_resized_image_url_medium']
                    challenge.we_vote_hosted_challenge_photo_small_url = \
                        create_resized_image_results['cached_resized_image_url_tiny']
                    challenge.save()
            else:
                # Deleting image
                challenge.we_vote_hosted_challenge_photo_large_url = None
                challenge.we_vote_hosted_challenge_photo_medium_url = None
                challenge.we_vote_hosted_challenge_photo_small_url = None
                challenge.save()

    status += create_results['status']
    if create_results['challenge_found']:
        challenge = create_results['challenge']
        challenge_we_vote_id = challenge.we_vote_id

        # Get owner_list
        results = challenge_manager.retrieve_challenge_as_owner(
            challenge_we_vote_id=challenge_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=True,
        )
        challenge_owner_list = results['challenge_owner_list']
        voter_is_challenge_owner = results['viewer_is_owner']

        # Get list of SEO Friendly Paths related to this Challenge. For most challenges, there will only be one.
        seo_friendly_path_list = challenge_manager.retrieve_seo_friendly_path_simple_list(
            challenge_we_vote_id=challenge_we_vote_id,
        )

        if in_draft_mode_changed and not positive_value_exists(in_draft_mode):
            if voter.is_signed_in():
                # Make sure the person creating the challenge has a challenge_participant entry IFF they are signed in
                update_values = {
                    'visible_to_public': True,
                    'visible_to_public_changed': True,
                }
                create_results = challenge_manager.update_or_create_challenge_participant(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                    organization_we_vote_id=linked_organization_we_vote_id,
                    update_values=update_values,
                )
                status += create_results['status']
                # Make sure an owner entry exists
                owner_results = challenge_manager.update_or_create_challenge_owner(
                    challenge_we_vote_id=challenge_we_vote_id,
                    organization_we_vote_id=linked_organization_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id)
                status += owner_results['status']

        # We need to know all the politicians this voter can vote for so we can figure out
        #  if the voter can vote for any politicians in the election
        # from ballot.controllers import what_voter_can_vote_for
        # results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        # voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']
        voter_can_vote_for_politician_we_vote_ids = []

        generate_results = generate_challenge_dict_from_challenge_object(
            challenge=challenge,
            challenge_owner_list=challenge_owner_list,
            hostname=hostname,
            seo_friendly_path_list=seo_friendly_path_list,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_is_challenge_owner=voter_is_challenge_owner,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )

        challenge_dict = generate_results['challenge_dict']
        status += generate_results['status']
        if not generate_results['success']:
            success = False
        if 'challenge_description' not in challenge_dict:
            success = False
        if success:
            results = challenge_dict
        else:
            results = challenge_error_dict
        return results
    else:
        status += "CHALLENGE_SAVE_ERROR "
        results = challenge_error_dict
        results['status'] = status
        return results


def challenge_save_photo_from_file_reader(
        challenge_we_vote_id='',
        challenge_photo_binary_file=None,
        challenge_photo_from_file_reader=None):
    image_data_found = False
    python_image_library_image = None
    status = ""
    success = True
    we_vote_hosted_challenge_photo_original_url = ''

    if not positive_value_exists(challenge_we_vote_id):
        status += "MISSING_CHALLENGE_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_challenge_photo_original_url': we_vote_hosted_challenge_photo_original_url,
        }
        return results

    if not positive_value_exists(challenge_photo_from_file_reader) \
            and not positive_value_exists(challenge_photo_binary_file):
        status += "MISSING_CHALLENGE_PHOTO_FROM_FILE_READER "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_challenge_photo_original_url': we_vote_hosted_challenge_photo_original_url,
        }
        return results

    if not challenge_photo_binary_file:
        try:
            img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                                challenge_photo_from_file_reader).groupdict()
            if img_dict['encoding'] == 'base64':
                challenge_photo_binary_file = img_dict['data']
            else:
                status += "INCOMING_CHALLENGE_PHOTO_LARGE-BASE64_NOT_FOUND "
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_BINARY_DATA_FROM_INCOMING_CHALLENGE_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if challenge_photo_binary_file:
        try:
            byte_data = base64.b64decode(challenge_photo_binary_file)
            image_data = BytesIO(byte_data)
            original_image = Image.open(image_data)
            format_to_cache = original_image.format
            python_image_library_image = ImageOps.exif_transpose(original_image)
            python_image_library_image.thumbnail(
                (CHALLENGE_PHOTO_ORIGINAL_MAX_WIDTH, CHALLENGE_PHOTO_ORIGINAL_MAX_HEIGHT), Image.Resampling.LANCZOS)
            python_image_library_image.format = format_to_cache
            image_data_found = True
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_CHALLENGE_PHOTO_FROM_BINARY_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if image_data_found:
        cache_results = cache_image_object_to_aws(
            python_image_library_image=python_image_library_image,
            challenge_we_vote_id=challenge_we_vote_id,
            kind_of_image_challenge_photo=True,
            kind_of_image_original=True)
        status += cache_results['status']
        if cache_results['success']:
            cached_master_we_vote_image = cache_results['we_vote_image']
            try:
                we_vote_hosted_challenge_photo_original_url = cached_master_we_vote_image.we_vote_image_url
            except Exception as e:
                status += "FAILED_TO_CACHE_CHALLENGE_IMAGE: " + str(e) + ' '
                success = False
        else:
            success = False
    results = {
        'status':                   status,
        'success':                  success,
        'we_vote_hosted_challenge_photo_original_url': we_vote_hosted_challenge_photo_original_url,
    }
    return results


def fetch_duplicate_challenge_count(
        challenge=None,
        ignore_challenge_we_vote_id_list=[],
        politician_name='',
        state_code=''):
    if not hasattr(challenge, 'challenge_title'):
        return 0

    challenge_manager = ChallengeManager()
    return challenge_manager.fetch_challenges_from_non_unique_identifiers_count(
        challenge_title=challenge.challenge_title,
        ignore_challenge_we_vote_id_list=ignore_challenge_we_vote_id_list,
        politician_name=politician_name,
        state_code=state_code,
    )


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


def figure_out_challenge_conflict_values(challenge1, challenge2):
    status = ''
    success = True
    challenge_merge_conflict_values = {}

    for attribute in CHALLENGE_UNIQUE_IDENTIFIERS:
        try:
            challenge1_attribute_value = getattr(challenge1, attribute)
            challenge2_attribute_value = getattr(challenge2, attribute)
            if challenge1_attribute_value is None and challenge2_attribute_value is None:
                challenge_merge_conflict_values[attribute] = 'MATCHING'
            elif challenge1_attribute_value is True and challenge2_attribute_value is True:
                challenge_merge_conflict_values[attribute] = 'MATCHING'
            elif challenge1_attribute_value is False and challenge2_attribute_value is False:
                challenge_merge_conflict_values[attribute] = 'MATCHING'
            elif challenge1_attribute_value == "" and challenge2_attribute_value == "":
                challenge_merge_conflict_values[attribute] = 'MATCHING'
            elif challenge1_attribute_value is None or challenge1_attribute_value == "":
                challenge_merge_conflict_values[attribute] = 'CHALLENGE2'
            elif challenge2_attribute_value is None or challenge2_attribute_value == "":
                challenge_merge_conflict_values[attribute] = 'CHALLENGE1'
            else:
                if attribute == "challenge_title":
                    if challenge1_attribute_value.lower() == challenge2_attribute_value.lower():
                        challenge_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        challenge_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "challenge_ends_date_as_integer":
                    # Choose the earlier date
                    if challenge2_attribute_value < challenge1_attribute_value:
                        challenge_merge_conflict_values[attribute] = 'CHALLENGE2'
                    else:
                        challenge_merge_conflict_values[attribute] = 'CHALLENGE1'
                else:
                    if challenge1_attribute_value == challenge2_attribute_value:
                        challenge_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        challenge_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    results = {
        'status':           status,
        'success':          success,
        'conflict_values':  challenge_merge_conflict_values,
    }
    return results


def find_duplicate_challenge(
        challenge=None,
        ignore_challenge_we_vote_id_list=[],
        politician_name='',
        state_code=''):
    status = ''
    success = True
    error_results = {
        'success': success,
        'status': status,
        'challenge_merge_possibility_found': False,
        'challenge_merge_possibility': None,
        'challenge_merge_conflict_values': {},
        'challenge_list': [],
    }
    if not hasattr(challenge, 'challenge_title'):
        status += "FIND_DUPLICATE_CHALLENGE_MISSING_CHALLENGE_OBJECT "
        error_results['success'] = False
        error_results['status'] = status
        return error_results

    challenge_manager = ChallengeManager()

    # Search for other challenges that share the same elections that match name and election
    try:
        results = challenge_manager.retrieve_challenges_from_non_unique_identifiers(
            challenge_title=challenge.challenge_title,
            state_code=state_code,
            politician_name=politician_name,
            ignore_challenge_we_vote_id_list=ignore_challenge_we_vote_id_list)

        if results['challenge_found']:
            conflict_results = figure_out_challenge_conflict_values(challenge, results['challenge'])
            challenge_merge_conflict_values = conflict_results['conflict_values']
            if not conflict_results['success']:
                status += conflict_results['status']
                success = conflict_results['success']
            else:
                status += "FIND_DUPLICATE_CHALLENGE_DUPLICATE_FOUND "
            results = {
                'success':                              success,
                'status':                               status,
                'challenge_merge_possibility_found':    True,
                'challenge_merge_possibility':          results['challenge'],
                'challenge_merge_conflict_values':      challenge_merge_conflict_values,
                'challenge_list':                       results['challenge_list'],
            }
            return results
        elif results['challenge_list_found']:
            # Only deal with merging the incoming challenge and the first on found
            conflict_results = figure_out_challenge_conflict_values(challenge, results['challenge_list'][0])
            challenge_merge_conflict_values = conflict_results['conflict_values']
            if not conflict_results['success']:
                status += conflict_results['status']
                success = conflict_results['success']
            else:
                status += "FIND_DUPLICATE_CHALLENGE_DUPLICATES_FOUND_FROM_LIST "
            results = {
                'success':                              success,
                'status':                               status,
                'challenge_merge_possibility_found':    True,
                'challenge_merge_possibility':          results['challenge_list'][0],
                'challenge_merge_conflict_values':      challenge_merge_conflict_values,
                'challenge_list':                       results['challenge_list'],
            }
            return results
        else:
            status += "FIND_DUPLICATE_CHALLENGE_NO_DUPLICATES_FOUND "
            error_results['success'] = success
            error_results['status'] = status
            error_results['challenge_list'] = results['challenge_list']
            return error_results

    except Exception as e:
        status += "FIND_DUPLICATE_CHALLENGE_ERROR: " + str(e) + ' '
        success = False

    error_results['success'] = success
    error_results['status'] = status
    return error_results


def generate_challenge_dict_list_from_challenge_object_list(
        challenge_object_list=[],
        hostname='',
        promoted_challenge_we_vote_ids=[],
        site_owner_organization_we_vote_id='',
        visible_on_this_site_challenge_we_vote_id_list=[],
        voter_can_vote_for_politician_we_vote_ids=[],
        voter_signed_in_with_email=False,
        voter_we_vote_id='',
):
    challenge_manager = ChallengeManager()
    challenge_dict_list = []
    challenge_we_vote_id_list = []
    status = ""
    success = True
    for challenge_object in challenge_object_list:
        if hasattr(challenge_object, 'we_vote_id'):
            challenge_we_vote_id_list.append(challenge_object.we_vote_id)

    if len(challenge_we_vote_id_list) == 0:
        status += 'NO_CHALLENGES_PROVIDED_TO_GENERATE_CHALLENGE_DICT_LIST '
        success = False
        results = {
            'challenge_dict_list': challenge_dict_list,
            'status': status,
            'success': success,
        }
        return results

    voter_owned_challenge_we_vote_ids = challenge_manager.retrieve_voter_owned_challenge_we_vote_ids(
        voter_we_vote_id=voter_we_vote_id,
    )
    voter_can_send_updates_challenge_we_vote_ids = \
        challenge_manager.retrieve_voter_can_send_updates_challenge_we_vote_ids(
            voter_we_vote_id=voter_we_vote_id,
        )

    final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
    for challenge in challenge_object_list:
        voter_is_challenge_owner = challenge.we_vote_id in voter_owned_challenge_we_vote_ids
        final_election_date_in_past = \
            final_election_date_plus_cool_down >= challenge.final_election_date_as_integer \
            if positive_value_exists(challenge.final_election_date_as_integer) else False

        # Should we promote this challenge on home page?
        if challenge.is_still_active and challenge.is_ok_to_promote_on_we_vote \
                and not final_election_date_in_past and not challenge.is_in_team_review_mode:
            if positive_value_exists(site_owner_organization_we_vote_id):
                if challenge.we_vote_id in visible_on_this_site_challenge_we_vote_id_list:
                    promoted_challenge_we_vote_ids.append(challenge.we_vote_id)
            else:
                if challenge.is_participants_count_minimum_exceeded():
                    promoted_challenge_we_vote_ids.append(challenge.we_vote_id)

        challenge_owner_list = []
        challenge_owner_object_list = challenge_manager.retrieve_challenge_owner_list(
            challenge_we_vote_id_list=[challenge.we_vote_id], viewer_is_owner=voter_is_challenge_owner)
        for challenge_owner in challenge_owner_object_list:
            challenge_owner_dict = {
                'feature_this_profile_image':               challenge_owner.feature_this_profile_image,
                'organization_name':                        challenge_owner.organization_name,
                'organization_we_vote_id':                  challenge_owner.organization_we_vote_id,
                'visible_to_public':                        challenge_owner.visible_to_public,
                'we_vote_hosted_profile_image_url_medium':  challenge_owner.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny':    challenge_owner.we_vote_hosted_profile_image_url_tiny,
            }
            challenge_owner_list.append(challenge_owner_dict)

        order_in_list = 0
        try:
            order_in_list = challenge.order_in_list
        except Exception as e:
            pass

        results = generate_challenge_dict_from_challenge_object(
            challenge=challenge,
            challenge_owner_list=challenge_owner_list,
            hostname=hostname,
            order_in_list=order_in_list,
            # seo_friendly_path_list=seo_friendly_path_list,
            voter_can_send_updates_challenge_we_vote_ids=voter_can_send_updates_challenge_we_vote_ids,
            voter_can_vote_for_politician_we_vote_ids=voter_can_vote_for_politician_we_vote_ids,
            voter_is_challenge_owner=voter_is_challenge_owner,
            voter_signed_in_with_email=voter_signed_in_with_email,
            voter_we_vote_id=voter_we_vote_id,
        )
        status += results['status']
        if results['success']:
            challenge_dict_list.append(results['challenge_dict'])

    results = {
        'challenge_dict_list':      challenge_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def generate_challenge_dict_from_challenge_object(
        challenge=None,
        challenge_owner_list=[],
        hostname='',
        order_in_list=0,
        seo_friendly_path_list=None,
        voter_can_send_updates_challenge_we_vote_ids=None,
        voter_can_vote_for_politician_we_vote_ids=[],
        voter_is_challenge_owner=False,
        voter_signed_in_with_email=False,
        voter_we_vote_id='',
):
    challenge_manager = ChallengeManager()
    status = ""
    success = True

    # Get challenge news items / updates
    challenge_news_item_list = []
    # Only retrieve news items if NOT linked to a politician
    if challenge and not positive_value_exists(challenge.politician_we_vote_id):
        news_item_list_results = challenge_manager.retrieve_challenge_news_item_list(
            challenge_we_vote_id=challenge.we_vote_id,
            read_only=True,
            voter_is_challenge_owner=voter_is_challenge_owner)
        if news_item_list_results['challenge_news_item_list_found']:
            news_item_list = news_item_list_results['challenge_news_item_list']
            for news_item in news_item_list:
                date_last_changed_string = ''
                date_posted_string = ''
                date_sent_to_email_string = ''
                try:
                    date_last_changed_string = news_item.date_last_changed.strftime(DATE_FORMAT_YMD_HMS) # '%Y-%m-%d %H:%M:%S'
                    date_posted_string = news_item.date_posted.strftime(DATE_FORMAT_YMD_HMS) # '%Y-%m-%d %H:%M:%S'
                    if positive_value_exists(news_item.date_sent_to_email):
                        date_sent_to_email_string = news_item.date_sent_to_email.strftime(DATE_FORMAT_YMD_HMS) # '%Y-%m-%d %H:%M:%S'
                except Exception as e:
                    status += "DATE_CONVERSION_ERROR: " + str(e) + " "
                one_news_item_dict = {
                    'challenge_news_subject': news_item.challenge_news_subject,
                    'challenge_news_text': news_item.challenge_news_text,
                    'challenge_news_item_we_vote_id': news_item.we_vote_id,
                    'challenge_we_vote_id': news_item.challenge_we_vote_id,
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
                challenge_news_item_list.append(one_news_item_dict)

    from organization.controllers import site_configuration_retrieve_for_api
    site_results = site_configuration_retrieve_for_api(hostname)
    site_owner_organization_we_vote_id = site_results['organization_we_vote_id']

    if positive_value_exists(site_owner_organization_we_vote_id):
        try:
            visible_on_this_site_challenge_we_vote_id_list = \
                challenge_manager.retrieve_visible_on_this_site_challenge_simple_list(
                    site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            if challenge.we_vote_id in visible_on_this_site_challenge_we_vote_id_list:
                challenge.visible_on_this_site = True
            else:
                challenge.visible_on_this_site = False
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "
    else:
        challenge.visible_on_this_site = True

    if challenge.politician_starter_list_serialized:
        challenge_politician_starter_list = json.loads(challenge.politician_starter_list_serialized)
    else:
        challenge_politician_starter_list = []

    challenge_politician_list_modified = []
    challenge_politician_list_exists = False
    challenge_politician_list = challenge_manager.retrieve_challenge_politician_list(
        challenge_we_vote_id=challenge.we_vote_id,
    )

    for challenge_politician in challenge_politician_list:
        challenge_politician_list_exists = True
        challenge_politician_dict = {
            'challenge_politician_id': challenge_politician.id,
            'politician_name':  challenge_politician.politician_name,
            'politician_we_vote_id':  challenge_politician.politician_we_vote_id,
            'state_code':  challenge_politician.state_code,
            'we_vote_hosted_profile_image_url_large': challenge_politician.we_vote_hosted_profile_image_url_large,
            'we_vote_hosted_profile_image_url_medium': challenge_politician.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_image_url_tiny': challenge_politician.we_vote_hosted_profile_image_url_tiny,
        }
        challenge_politician_list_modified.append(challenge_politician_dict)

    # Get list of SEO Friendly Paths related to this Challenge. For most challenges, there will only be one.
    if seo_friendly_path_list is None:
        seo_friendly_path_list = challenge_manager.retrieve_seo_friendly_path_simple_list(
            challenge_we_vote_id=challenge.we_vote_id,
        )

    latest_challenge_participant_list = []  # Latest participants with or without comments
    latest_position_dict_list = []  # DALE 2024-07-06 I don't know if we want to bring this in here
    participants_count_next_goal = 0
    voter_challenge_participant_dict = {}
    participant_results = challenge_manager.retrieve_challenge_participant(
        challenge_we_vote_id=challenge.we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        read_only=True)
    if participant_results['success'] and participant_results['challenge_participant_found']:
        challenge_participant = participant_results['challenge_participant']
        generate_results = generate_challenge_participant_dict_from_challenge_participant_object(
            challenge_participant=challenge_participant)
        if generate_results['success']:
            voter_challenge_participant_dict = generate_results['challenge_participant_dict']

    # Get most recent participants
    participant_list_results = challenge_manager.retrieve_challenge_participant_list(
        challenge_we_vote_id=challenge.we_vote_id,
        limit=7,
        read_only=True,
        require_invite_text_for_friends=False,
        require_visible_to_public=True)
    if participant_list_results['participant_list_found']:
        participant_list = participant_list_results['participant_list']
        for challenge_participant in participant_list:
            generate_results = generate_challenge_participant_dict_from_challenge_participant_object(
                challenge_participant=challenge_participant)
            if generate_results['success']:
                one_participant_dict = generate_results['challenge_participant_dict']
                latest_challenge_participant_list.append(one_participant_dict)

    participants_count_next_goal = challenge_manager.fetch_participants_count_next_goal(
        participants_count=challenge.participants_count,
        participants_count_victory_goal=challenge.participants_count_victory_goal)

    if voter_can_send_updates_challenge_we_vote_ids is not None:
        # Leave it as is, even if empty
        pass
    elif positive_value_exists(voter_we_vote_id):
        voter_can_send_updates_challenge_we_vote_ids = \
            challenge_manager.retrieve_voter_can_send_updates_challenge_we_vote_ids(
                voter_we_vote_id=voter_we_vote_id,
            )
    else:
        voter_can_send_updates_challenge_we_vote_ids = []

    # If smaller sizes weren't stored, use large image
    if challenge.we_vote_hosted_challenge_photo_medium_url:
        we_vote_hosted_challenge_photo_medium_url = challenge.we_vote_hosted_challenge_photo_medium_url
    else:
        we_vote_hosted_challenge_photo_medium_url = challenge.we_vote_hosted_challenge_photo_large_url
    if challenge.we_vote_hosted_challenge_photo_small_url:
        we_vote_hosted_challenge_photo_small_url = challenge.we_vote_hosted_challenge_photo_small_url
    else:
        we_vote_hosted_challenge_photo_small_url = challenge.we_vote_hosted_challenge_photo_large_url
    final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
    final_election_date_in_past = \
        final_election_date_plus_cool_down >= challenge.final_election_date_as_integer \
        if positive_value_exists(challenge.final_election_date_as_integer) else False

    if positive_value_exists(challenge.challenge_title):
        challenge_title = challenge.challenge_title.strip()
    else:
        challenge_title = ""

    if hasattr(challenge, 'visible_on_this_site'):
        visible_on_this_site = challenge.visible_on_this_site
    else:
        visible_on_this_site = True

    if positive_value_exists(challenge.challenge_invite_text_default):
        challenge_invite_text_default = challenge.challenge_invite_text_default
    else:
        from challenge.models import CHALLENGE_INVITE_TEXT_DEFAULT
        challenge_invite_text_default = CHALLENGE_INVITE_TEXT_DEFAULT
        challenge_invite_text_default = \
            challenge_invite_text_default.replace('[challenge_title]', challenge_title)

    challenge_dict = {
        'challenge_description':            challenge.challenge_description,
        'challenge_invite_text_default':    challenge_invite_text_default,
        'challenge_ends_date_as_integer':   challenge.challenge_ends_date_as_integer,
        'challenge_starts_date_as_integer': challenge.challenge_starts_date_as_integer,
        'challenge_title':                  challenge.challenge_title,
        'challenge_news_item_list':         challenge_news_item_list,
        'challenge_owner_list':             challenge_owner_list,
        'challenge_politician_list':        challenge_politician_list_modified,
        'challenge_politician_list_exists': challenge_politician_list_exists,
        'challenge_politician_starter_list': challenge_politician_starter_list,
        'challenge_we_vote_id':             challenge.we_vote_id,
        'final_election_date_as_integer':   challenge.final_election_date_as_integer,
        'final_election_date_in_past':      final_election_date_in_past,
        'in_draft_mode':                    challenge.in_draft_mode,
        'is_blocked_by_we_vote':            challenge.is_blocked_by_we_vote,
        'is_blocked_by_we_vote_reason':     challenge.is_blocked_by_we_vote_reason,
        'is_participants_count_minimum_exceeded': challenge.is_participants_count_minimum_exceeded(),
        'latest_challenge_participant_list':  latest_challenge_participant_list,
        'politician_we_vote_id':            challenge.politician_we_vote_id,
        'opposers_count':                   challenge.opposers_count,
        'order_in_list':                    order_in_list,
        'profile_image_background_color':   challenge.profile_image_background_color,
        'seo_friendly_path':                challenge.seo_friendly_path,
        'seo_friendly_path_list':           seo_friendly_path_list,
        'participants_count':                 challenge.participants_count,
        'participants_count_next_goal':       participants_count_next_goal,
        'participants_count_victory_goal':    challenge.participants_count_victory_goal,
        'visible_on_this_site':             visible_on_this_site,
        'voter_challenge_participant':        voter_challenge_participant_dict,
        'voter_can_send_updates_to_challenge':
            challenge.we_vote_id in voter_can_send_updates_challenge_we_vote_ids,
        'voter_can_vote_for_politician_we_vote_ids': voter_can_vote_for_politician_we_vote_ids,
        'voter_is_challenge_owner':         voter_is_challenge_owner,
        'voter_signed_in_with_email':       voter_signed_in_with_email,
        'we_vote_hosted_challenge_photo_large_url':  challenge.we_vote_hosted_challenge_photo_large_url,
        'we_vote_hosted_challenge_photo_medium_url': we_vote_hosted_challenge_photo_medium_url,
        'we_vote_hosted_challenge_photo_small_url': we_vote_hosted_challenge_photo_small_url,
        'we_vote_hosted_profile_image_url_large': challenge.we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium': challenge.we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny': challenge.we_vote_hosted_profile_image_url_tiny,
    }

    results = {
        'challenge_dict':   challenge_dict,
        'status':           status,
        'success':          success,
    }
    return results


def merge_if_duplicate_challenges(challenge1, challenge2, conflict_values):
    """
    See also figure_out_challenge_conflict_values
    :param challenge1:
    :param challenge2:
    :param conflict_values:
    :return:
    """
    success = True
    status = "MERGE_IF_DUPLICATE_CHALLENGES "
    challenges_merged = False
    decisions_required = False
    challenge1_we_vote_id = challenge1.we_vote_id
    challenge2_we_vote_id = challenge2.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    clear_these_attributes_from_challenge2 = []
    for attribute in CHALLENGE_UNIQUE_IDENTIFIERS:
        if \
                attribute == "seo_friendly_path" \
                or attribute == "we_vote_hosted_challenge_photo_original_url" \
                or attribute == "we_vote_hosted_challenge_photo_large_url" \
                or attribute == "we_vote_hosted_challenge_photo_medium_url" \
                or attribute == "we_vote_hosted_challenge_photo_small_url" \
                or attribute == "we_vote_hosted_profile_image_url_large" \
                or attribute == "we_vote_hosted_profile_image_url_medium" \
                or attribute == "we_vote_hosted_profile_image_url_tiny":
            if positive_value_exists(getattr(challenge1, attribute)):
                # We can proceed because challenge1 has a valid attribute, so we can default to choosing that one
                if attribute in CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_challenge2.append(attribute)
            elif positive_value_exists(getattr(challenge2, attribute)):
                # If we are here, challenge1 does NOT have a valid attribute, but challenge2 does
                merge_choices[attribute] = getattr(challenge2, attribute)
                if attribute in CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_challenge2.append(attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                if attribute == "challenge_title":
                    # If the lower case versions of the name attribute are identical, choose the name
                    #  that has upper and lower case letters, and do not require a decision
                    challenge1_attribute_value = getattr(challenge1, attribute)
                    try:
                        challenge1_attribute_value_lower_case = challenge1_attribute_value.lower()
                    except Exception:
                        challenge1_attribute_value_lower_case = None
                    challenge2_attribute_value = getattr(challenge2, attribute)
                    try:
                        challenge2_attribute_value_lower_case = challenge2_attribute_value.lower()
                    except Exception:
                        challenge2_attribute_value_lower_case = None
                    if positive_value_exists(challenge1_attribute_value_lower_case) \
                            and challenge1_attribute_value_lower_case == challenge2_attribute_value_lower_case:
                        # Give preference to value with both upper and lower case letters (as opposed to all uppercase)
                        if any(char.isupper() for char in challenge1_attribute_value) \
                                and any(char.islower() for char in challenge1_attribute_value):
                            merge_choices[attribute] = getattr(challenge1, attribute)
                        else:
                            merge_choices[attribute] = getattr(challenge2, attribute)
                    else:
                        decisions_required = True
                        break
                else:
                    decisions_required = True
                    break
            elif conflict_value == "CHALLENGE2":
                merge_choices[attribute] = getattr(challenge2, attribute)
                if attribute in CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_challenge2.append(attribute)

    if not decisions_required:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = merge_these_two_challenges(
            challenge1_we_vote_id,
            challenge2_we_vote_id,
            admin_merge_choices=merge_choices,
            clear_these_attributes_from_challenge2=clear_these_attributes_from_challenge2,
        )

        if not merge_results['success']:
            success = False
            status += merge_results['status']
        elif merge_results['challenges_merged']:
            challenges_merged = True
        else:
            status += "NOT_MERGED "

    results = {
        'success':                  success,
        'status':                   status,
        'challenges_merged':        challenges_merged,
        'decisions_required':       decisions_required,
        'challenge':                challenge1,
    }
    return results


def merge_these_two_challenges(
        challenge1_we_vote_id,
        challenge2_we_vote_id,
        admin_merge_choices={},
        clear_these_attributes_from_challenge2=[],
        regenerate_challenge_title=False):
    """
    Process the merging of two challenge entries
    :param challenge1_we_vote_id:
    :param challenge2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :param clear_these_attributes_from_challenge2:
    :param regenerate_challenge_title:
    :return:
    """
    status = ""
    challenge_manager = ChallengeManager()

    # Challenge 1 is the one we keep, and Challenge 2 is the one we will merge into Challenge 1
    challenge1_results = \
        challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge1_we_vote_id, read_only=False)
    if challenge1_results['challenge_found']:
        challenge1_on_stage = challenge1_results['challenge']
        challenge1_id = challenge1_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_CHALLENGES-COULD_NOT_RETRIEVE_CHALLENGE1 ",
            'challenges_merged': False,
            'challenge': None,
        }
        return results

    challenge2_results = \
        challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge2_we_vote_id, read_only=False)
    if challenge2_results['challenge_found']:
        challenge2_on_stage = challenge2_results['challenge']
        challenge2_id = challenge2_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_CHALLENGES-COULD_NOT_RETRIEVE_CHALLENGE2 ",
            'challenges_merged': False,
            'challenge': None,
        }
        return results

    # TODO: Migrate images?

    # Merge attribute values chosen by the admin
    for attribute in CHALLENGE_UNIQUE_IDENTIFIERS:
        # try:
        if attribute in admin_merge_choices:
            setattr(challenge1_on_stage, attribute, admin_merge_choices[attribute])
        # except Exception as e:
        #     # Don't completely fail if in attribute can't be saved.
        #     status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "

    if positive_value_exists(regenerate_challenge_title):
        if positive_value_exists(challenge1_on_stage.politician_we_vote_id):
            from politician.models import PoliticianManager
            politician_manager = PoliticianManager()
            results = politician_manager.retrieve_politician(
                politician_we_vote_id=challenge1_on_stage.politician_we_vote_id)
            if results['politician_found']:
                politician = results['politician']
                politician_name = politician.politician_name
                state_code = politician.state_code
                from politician.controllers_generate_seo_friendly_path import generate_challenge_title_from_politician
                challenge1_on_stage.challenge_title = generate_challenge_title_from_politician(
                    politician_name=politician_name,
                    state_code=state_code)

    # #####################################
    # Merge ChallengeListedByOrganization
    challenge1_organization_we_vote_id_list = []
    challenge2_listed_by_organization_to_delete_list = []
    queryset = ChallengeListedByOrganization.objects.all()
    queryset = queryset.filter(challenge_we_vote_id=challenge1_we_vote_id)
    challenge1_listed_by_organization_list = list(queryset)
    for challenge1_listed_by_organization in challenge1_listed_by_organization_list:
        if positive_value_exists(challenge1_listed_by_organization.site_owner_organization_we_vote_id) and \
                challenge1_listed_by_organization.site_owner_organization_we_vote_id \
                not in challenge1_organization_we_vote_id_list:
            challenge1_organization_we_vote_id_list\
                .append(challenge1_listed_by_organization.site_owner_organization_we_vote_id)

    queryset = ChallengeListedByOrganization.objects.all()
    queryset = queryset.filter(challenge_we_vote_id=challenge2_we_vote_id)
    challenge2_listed_by_organization_list = list(queryset)
    for challenge2_listed_by_organization in challenge2_listed_by_organization_list:
        # Is this listed_by_organization already in Challenge 1?
        challenge2_listed_by_organization_matches_challenge1_listed_by_organization = False
        if positive_value_exists(challenge2_listed_by_organization.site_owner_organization_we_vote_id) and \
                challenge2_listed_by_organization.site_owner_organization_we_vote_id \
                in challenge1_organization_we_vote_id_list:
            challenge2_listed_by_organization_matches_challenge1_listed_by_organization = True
        if challenge2_listed_by_organization_matches_challenge1_listed_by_organization:
            # If the listed_by_organization is already in Challenge 1, move them to challenge1
            challenge2_listed_by_organization_to_delete_list.append(challenge2_listed_by_organization)
        else:
            # If not, move them to challenge1
            challenge2_listed_by_organization.challenge_we_vote_id = challenge1_we_vote_id
            challenge2_listed_by_organization.save()

    # #####################################
    # Merge ChallengeNewsItems
    challenge_news_items_moved = ChallengeNewsItem.objects \
        .filter(challenge_we_vote_id=challenge2_we_vote_id) \
        .update(challenge_we_vote_id=challenge1_we_vote_id)

    # ##################################
    # Move the seo friendly paths from challenge2 over to challenge1. ChallengeSEOFriendlyPath entries are unique,
    #  so we don't need to check for duplicates.
    from challenge.models import ChallengeSEOFriendlyPath
    challenge_seo_friendly_path_moved = ChallengeSEOFriendlyPath.objects \
        .filter(challenge_we_vote_id=challenge2_we_vote_id) \
        .update(challenge_we_vote_id=challenge1_we_vote_id)

    # ##################################
    # Update the linked_challenge_we_vote_id in Politician entries
    try:
        from politician.models import Politician
        linked_challenge_we_vote_id_updated = Politician.objects \
            .filter(linked_challenge_we_vote_id=challenge2_we_vote_id) \
            .update(linked_challenge_we_vote_id=challenge1_we_vote_id)
    except Exception as e:
        status += "POLITICIAN_LINKED_CHALLENGE_WE_VOTE_ID_NOT_UPDATED: " + str(e) + " "

    # ##################################
    # Migrate challenge owners
    challenge1_owner_organization_we_vote_id_list = []
    challenge1_owner_voter_we_vote_id_list = []
    challenge2_owners_to_delete_list = []
    challenge1_owner_list = challenge_manager.retrieve_challenge_owner_list(
        challenge_we_vote_id_list=[challenge1_we_vote_id],
        viewer_is_owner=True
    )
    for challenge1_owner in challenge1_owner_list:
        if positive_value_exists(challenge1_owner.organization_we_vote_id) and \
                challenge1_owner.organization_we_vote_id not in challenge1_owner_organization_we_vote_id_list:
            challenge1_owner_organization_we_vote_id_list.append(challenge1_owner.organization_we_vote_id)
        if positive_value_exists(challenge1_owner.voter_we_vote_id) and \
                challenge1_owner.voter_we_vote_id not in challenge1_owner_voter_we_vote_id_list:
            challenge1_owner_voter_we_vote_id_list.append(challenge1_owner.voter_we_vote_id)

    challenge2_owner_list = challenge_manager.retrieve_challenge_owner_list(
        challenge_we_vote_id_list=[challenge2_we_vote_id],
        read_only=False,
        viewer_is_owner=True
    )
    for challenge2_owner in challenge2_owner_list:
        # Is this challenge owner already in Challenge 1?
        challenge2_owner_matches_challenge1_owner = False
        if positive_value_exists(challenge2_owner.organization_we_vote_id) and \
                challenge2_owner.organization_we_vote_id in challenge1_owner_organization_we_vote_id_list:
            challenge2_owner_matches_challenge1_owner = True
        if positive_value_exists(challenge2_owner.voter_we_vote_id) and \
                challenge2_owner.voter_we_vote_id in challenge1_owner_voter_we_vote_id_list:
            challenge2_owner_matches_challenge1_owner = True
        if challenge2_owner_matches_challenge1_owner:
            # If there is a match, save to delete below
            challenge2_owners_to_delete_list.append(challenge2_owner)
        else:
            # If not, move them to challenge1
            challenge2_owner.challenge_we_vote_id = challenge1_we_vote_id
            challenge2_owner.save()

    # #####################################
    # If a Challenge politician isn't already in Challenge 1, bring Politician over from Challenge 2
    challenge1_politician_we_vote_id_list = []
    challenge2_politicians_to_delete_list = []
    challenge1_politician_list = challenge_manager.retrieve_challenge_politician_list(
        challenge_we_vote_id=challenge1_we_vote_id,
        read_only=False,
    )
    for challenge1_politician in challenge1_politician_list:
        if positive_value_exists(challenge1_politician.politician_we_vote_id) and \
                challenge1_politician.politician_we_vote_id not in challenge1_politician_we_vote_id_list:
            challenge1_politician_we_vote_id_list.append(challenge1_politician.politician_we_vote_id)

    challenge2_politician_list = challenge_manager.retrieve_challenge_politician_list(
        challenge_we_vote_id=challenge2_we_vote_id,
        read_only=False,
    )
    for challenge2_politician in challenge2_politician_list:
        # Is this challenge politician already in Challenge 1?
        if not positive_value_exists(challenge2_politician.politician_we_vote_id):
            challenge2_politicians_to_delete_list.append(challenge2_politician)
        elif challenge2_politician.politician_we_vote_id not in challenge1_politician_we_vote_id_list:
            # If not, move them to challenge1
            challenge2_politician.challenge_we_vote_id = challenge1_we_vote_id
            challenge2_politician.save()
        else:
            challenge2_politicians_to_delete_list.append(challenge2_politician)

    # #####################################
    # Merge Challenge Participants
    challenge1_organization_we_vote_id_list = []
    challenge1_voter_we_vote_id_list = []
    challenge2_participants_to_delete_list = []
    queryset = ChallengeParticipant.objects.all()
    queryset = queryset.filter(challenge_we_vote_id=challenge1_we_vote_id)
    challenge1_participant_list = list(queryset)
    for challenge1_participant in challenge1_participant_list:
        if positive_value_exists(challenge1_participant.organization_we_vote_id) and \
                challenge1_participant.organization_we_vote_id not in challenge1_organization_we_vote_id_list:
            challenge1_organization_we_vote_id_list.append(challenge1_participant.organization_we_vote_id)
        if positive_value_exists(challenge1_participant.voter_we_vote_id) and \
                challenge1_participant.voter_we_vote_id not in challenge1_voter_we_vote_id_list:
            challenge1_voter_we_vote_id_list.append(challenge1_participant.voter_we_vote_id)

    queryset = ChallengeParticipant.objects.all()
    queryset = queryset.filter(challenge_we_vote_id=challenge2_we_vote_id)
    challenge2_participant_list = list(queryset)
    for challenge2_participant in challenge2_participant_list:
        # Is this challenge politician already in Challenge 1?
        challenge2_participant_matches_challenge1_participant = False
        if positive_value_exists(challenge2_participant.organization_we_vote_id) and \
                challenge2_participant.organization_we_vote_id in challenge1_organization_we_vote_id_list:
            challenge2_participant_matches_challenge1_participant = True
        if positive_value_exists(challenge2_participant.voter_we_vote_id) and \
                challenge2_participant.voter_we_vote_id in challenge1_voter_we_vote_id_list:
            challenge2_participant_matches_challenge1_participant = True
        if challenge2_participant_matches_challenge1_participant:
            # If the participant is already in Challenge 1, move them to challenge1
            challenge2_participants_to_delete_list.append(challenge2_participant)
        else:
            # If not, move them to challenge1
            challenge2_participant.challenge_we_vote_id = challenge1_we_vote_id
            challenge2_participant.save()

    # Clear 'unique=True' fields in challenge2_on_stage, which need to be Null before challenge1_on_stage can be saved
    #  with updated values
    challenge2_updated = False
    for attribute in clear_these_attributes_from_challenge2:  # CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
        setattr(challenge2_on_stage, attribute, None)
        challenge2_updated = True
    if challenge2_updated:
        challenge2_on_stage.save()

    challenge1_on_stage.save()

    # Delete duplicate challenge2 owner entries
    for challenge2owner in challenge2_owners_to_delete_list:
        challenge2owner.delete()

    # Delete duplicate challenge2 politician entries
    for challenge2_politician in challenge2_politicians_to_delete_list:
        challenge2_politician.delete()

    # Delete duplicate challenge2 participant entries
    for challenge2_participant in challenge2_participants_to_delete_list:
        challenge2_participant.delete()

    # Finally, remove challenge 2
    challenge2_on_stage.delete()

    results = {
        'success': True,
        'status': status,
        'challenges_merged': True,
        'challenge': challenge1_on_stage,
    }
    return results


# def move_challenge_to_another_organization(
#         from_organization_we_vote_id, to_organization_we_vote_id,
#         to_organization_name=None):
#     status = ''
#     success = True
#     challenges_moved = 0
#     challenge_listed_entries_moved = 0
#     challenge_news_item_entries_moved = 0
#     challenge_owner_entries_moved = 0
#     challenge_participant_entries_moved = 0
#
#     if not positive_value_exists(from_organization_we_vote_id) or not positive_value_exists(to_organization_we_vote_id):
#         status += "MOVE_CHALLENGE_TO_ORG-MISSING_EITHER_FROM_OR_TO_ORG_WE_VOTE_ID "
#         success = False
#         results = {
#             'status':                           status,
#             'success':                          success,
#             'from_organization_we_vote_id':     from_organization_we_vote_id,
#             'to_organization_we_vote_id':       to_organization_we_vote_id,
#             'challenges_moved':                 challenges_moved,
#             'challenge_owner_entries_moved':    challenge_owner_entries_moved,
#         }
#         return results
#
#     if from_organization_we_vote_id == to_organization_we_vote_id:
#         status += "MOVE_CHALLENGE_TO_ORG-FROM_AND_TO_ORG_WE_VOTE_IDS_IDENTICAL "
#         success = False
#         results = {
#             'status':                           status,
#             'success':                          success,
#             'from_organization_we_vote_id':     from_organization_we_vote_id,
#             'to_organization_we_vote_id':       to_organization_we_vote_id,
#             'challenges_moved':                 challenges_moved,
#             'challenge_owner_entries_moved':    challenge_owner_entries_moved,
#         }
#         return results
#
#     # #############################################
#     # Move based on organization_we_vote_id
#     if positive_value_exists(to_organization_name):
#         try:
#             challenge_owner_entries_moved += ChallengeOwner.objects \
#                 .filter(organization_we_vote_id=from_organization_we_vote_id) \
#                 .update(organization_name=to_organization_name,
#                         organization_we_vote_id=to_organization_we_vote_id)
#         except Exception as e:
#             status += "FAILED-CHALLENGE_TO_ORG_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
#         try:
#             challenge_participant_entries_moved += ChallengeParticipant.objects \
#                 .filter(organization_we_vote_id=from_organization_we_vote_id) \
#                 .update(participant_name=to_organization_name,
#                         organization_we_vote_id=to_organization_we_vote_id)
#         except Exception as e:
#             status += "FAILED-CHALLENGE_TO_ORG_PARTICIPANT_UPDATE-FROM_ORG_WE_VOTE_ID-WITH_NAME: " + str(e) + " "
#         try:
#             challenge_news_item_entries_moved += ChallengeNewsItem.objects \
#                 .filter(organization_we_vote_id=from_organization_we_vote_id) \
#                 .update(speaker_name=to_organization_name,
#                         organization_we_vote_id=to_organization_we_vote_id)
#         except Exception as e:
#             status += "FAILED-CHALLENGE_NEWS_ITEM_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
#     else:
#         try:
#             challenge_owner_entries_moved += ChallengeOwner.objects \
#                 .filter(organization_we_vote_id=from_organization_we_vote_id) \
#                 .update(organization_we_vote_id=to_organization_we_vote_id)
#         except Exception as e:
#             status += "FAILED-CHALLENGE_TO_ORG_OWNER_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
#         try:
#             challenge_participant_entries_moved += ChallengeParticipant.objects \
#                 .filter(organization_we_vote_id=from_organization_we_vote_id) \
#                 .update(organization_we_vote_id=to_organization_we_vote_id)
#         except Exception as e:
#             status += "FAILED-CHALLENGE_TO_ORG_PARTICIPANT_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
#         try:
#             challenge_news_item_entries_moved += ChallengeNewsItem.objects \
#                 .filter(organization_we_vote_id=from_organization_we_vote_id) \
#                 .update(organization_we_vote_id=to_organization_we_vote_id)
#         except Exception as e:
#             status += "FAILED-CHALLENGE_NEWS_ITEM_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
#
#     results = {
#         'status':                           status,
#         'success':                          success,
#         'from_organization_we_vote_id':     from_organization_we_vote_id,
#         'to_organization_we_vote_id':       to_organization_we_vote_id,
#         'challenges_moved':                 challenge_owner_entries_moved,
#         'challenge_owner_entries_moved':    challenge_owner_entries_moved,
#     }
#     return results


# def move_challenge_to_another_politician(
#         from_politician_we_vote_id='',
#         to_politician_we_vote_id=''):
#     """
#
#     :param from_politician_we_vote_id:
#     :param to_politician_we_vote_id:
#     :return:
#     """
#     status = ''
#     success = True
#     challenges_moved = 0
#
#     if positive_value_exists(from_politician_we_vote_id):
#         try:
#             challenges_moved += ChallengePolitician.objects \
#                 .filter(politician_we_vote_id=from_politician_we_vote_id) \
#                 .update(politician_we_vote_id=to_politician_we_vote_id)
#         except Exception as e:
#             status += "FAILED_MOVE_CHALLENGE_BY_POLITICIAN_WE_VOTE_ID: " + str(e) + " "
#             success = False
#
#     results = {
#         'status':                   status,
#         'success':                  success,
#         'challenges_moved':  challenges_moved,
#     }
#     return results


def move_challenges_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id, to_organization_we_vote_id):
    status = ''
    success = True
    challenges_moved = 0
    challenge_invitee_entries_moved = 0
    # challenge_listed_entries_moved = 0
    challenge_news_item_entries_moved = 0
    challenge_owner_entries_moved = 0
    challenge_participant_entries_moved = 0

    error_results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'challenges_moved':                 challenges_moved,
        'challenge_invitee_entries_moved':  challenge_invitee_entries_moved,
        'challenge_news_item_entries_moved': challenge_news_item_entries_moved,
        'challenge_owner_entries_moved':    challenge_owner_entries_moved,
        'challenge_participant_entries_moved': challenge_participant_entries_moved,
    }

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_CHALLENGE-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        error_results['success'] = False
        error_results['status'] = status
        return error_results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_CHALLENGE-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        error_results['success'] = False
        error_results['status'] = status
        return error_results

    # ######################
    # Move based on started_by_voter_we_vote_id
    try:
        challenges_moved += Challenge.objects\
            .filter(started_by_voter_we_vote_id=from_voter_we_vote_id)\
            .update(started_by_voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CHALLENGE_UPDATE: " + str(e) + " "
        success = False

    # ######################
    # Move News Item based on voter_we_vote_id
    try:
        challenge_news_item_entries_moved += ChallengeNewsItem.objects\
            .filter(voter_we_vote_id=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CHALLENGE_NEWS_ITEM_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False

    # ######################
    # Move owners based on voter_we_vote_id
    try:
        challenge_owner_entries_moved += ChallengeOwner.objects\
            .filter(voter_we_vote_id=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-CHALLENGE_OWNER_UPDATE-FROM_VOTER_WE_VOTE_ID: " + str(e) + " "
        success = False

    # ######################
    # Move participants based on voter_we_vote_id
    from challenge.controllers_participant import move_participant_entries_to_another_voter
    participant_results = move_participant_entries_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id, to_organization_we_vote_id)
    if participant_results['success']:
        challenge_participant_entries_moved = participant_results['participant_entries_moved']
    else:
        status += participant_results['status'] + " "
        success = False

    # ######################
    # Move invitees based on voter_we_vote_id
    from challenge.controllers_invitee import move_invitee_entries_to_another_voter
    invitee_results = move_invitee_entries_to_another_voter(
        from_voter_we_vote_id, to_voter_we_vote_id)
    if invitee_results['success']:
        challenge_invitee_entries_moved = invitee_results['invitee_entries_moved']
    else:
        status += invitee_results['status'] + " "
        success = False

    # try:
    #     challenge_listed_entries_moved += ChallengeListedByOrganization.objects \
    #         .filter(site_owner_organization_we_vote_id=from_organization_we_vote_id) \
    #         .update(site_owner_organization_we_vote_id=to_organization_we_vote_id)
    # except Exception as e:
    #     status += "FAILED-CHALLENGE_LISTED_BY_ORG_UPDATE-FROM_ORG_WE_VOTE_ID: " + str(e) + " "
    #     success = False

    results = {
        'status':                           status,
        'success':                          success,
        'from_voter_we_vote_id':            from_voter_we_vote_id,
        'to_voter_we_vote_id':              to_voter_we_vote_id,
        'challenges_moved':                 challenges_moved,
        'challenge_invitee_entries_moved':  challenge_invitee_entries_moved,
        'challenge_news_item_entries_moved': challenge_news_item_entries_moved,
        'challenge_owner_entries_moved':    challenge_owner_entries_moved,
        'challenge_participant_entries_moved': challenge_participant_entries_moved,
    }
    return results


def retrieve_recommended_challenge_list_for_challenge_we_vote_id(
        request=None,
        voter_device_id='',
        challenge_we_vote_id='',
        voter_we_vote_id='',
        site_owner_organization_we_vote_id='',
        minimum_number_of_challenge_options=15,
        read_only=True):
    """
    Regarding minimum_number_of_challenge_options:
    If we ask voters to sign 5 more challenges, we want to make sure we send 3x options so we have enough
    available on the front end so we can filter out challenges with duplicate politicians
    (after the voter makes choices) and let the voter skip challenges they aren't interested in

    :param request:
    :param voter_device_id:
    :param challenge_we_vote_id:
    :param voter_we_vote_id:
    :param site_owner_organization_we_vote_id:
    :param minimum_number_of_challenge_options:
    :param read_only:
    :return:
    """
    challenge_manager = ChallengeManager()
    challenge_list = []
    original_challenge_we_vote_id_list = [challenge_we_vote_id]
    success = True
    status = ""

    # Remove challenges already supported by this voter
    supported_by_voter_challenge_we_vote_id_list = []
    if positive_value_exists(voter_we_vote_id):
        results = challenge_manager.retrieve_challenge_we_vote_id_list_supported_by_voter(
            voter_we_vote_id=voter_we_vote_id)
        if results['challenge_we_vote_id_list_found']:
            supported_by_voter_challenge_we_vote_id_list = results['challenge_we_vote_id_list']

    challenge_we_vote_id_list_voter_can_vote_for = []
    if positive_value_exists(voter_device_id):
        from ballot.controllers import what_voter_can_vote_for
        results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        if len(results['voter_can_vote_for_politician_we_vote_ids']) > 0:
            voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']
            politician_results = challenge_manager.retrieve_challenge_we_vote_id_list_by_politician_we_vote_id(
                politician_we_vote_id_list=voter_can_vote_for_politician_we_vote_ids)
            if politician_results['challenge_we_vote_id_list_found']:
                challenge_we_vote_id_list_voter_can_vote_for = politician_results['challenge_we_vote_id_list']

    # Create pool of options
    # recommended_challenge_we_vote_id_list = ['wv02chal4']
    continue_searching_for_options = True
    if positive_value_exists(site_owner_organization_we_vote_id):
        # Retrieve all challenges visible on this site
        visible_on_this_site_challenge_we_vote_id_list = \
            challenge_manager.retrieve_visible_on_this_site_challenge_simple_list(
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
        recommended_challenge_we_vote_id_list = \
            list(set(visible_on_this_site_challenge_we_vote_id_list) - set(original_challenge_we_vote_id_list))
        if len(supported_by_voter_challenge_we_vote_id_list) > 0:
            recommended_challenge_we_vote_id_list = \
                list(set(recommended_challenge_we_vote_id_list) - set(supported_by_voter_challenge_we_vote_id_list))
        continue_searching_for_options = False
    else:
        recommended_challenge_we_vote_id_list = challenge_we_vote_id_list_voter_can_vote_for
        recommended_challenge_we_vote_id_list = \
            list(set(recommended_challenge_we_vote_id_list) - set(original_challenge_we_vote_id_list))
        if len(supported_by_voter_challenge_we_vote_id_list) > 0:
            recommended_challenge_we_vote_id_list = \
                list(set(recommended_challenge_we_vote_id_list) - set(supported_by_voter_challenge_we_vote_id_list))
        if len(recommended_challenge_we_vote_id_list) >= minimum_number_of_challenge_options:
            # If we have the number we need, we can stop here
            continue_searching_for_options = False

    if continue_searching_for_options:
        number_of_options_already_found = len(recommended_challenge_we_vote_id_list)
        number_to_find = minimum_number_of_challenge_options - number_of_options_already_found
        if number_to_find > 0:
            challenge_we_vote_id_list_to_exclude = \
                list(set(recommended_challenge_we_vote_id_list +
                         supported_by_voter_challenge_we_vote_id_list +
                         original_challenge_we_vote_id_list))

            results = challenge_manager.retrieve_challenge_we_vote_id_list_filler_options(
                challenge_we_vote_id_list_to_exclude=challenge_we_vote_id_list_to_exclude,
                limit=number_to_find)
            if results['challenge_we_vote_id_list_found']:
                challenge_we_vote_id_list = results['challenge_we_vote_id_list']
                recommended_challenge_we_vote_id_list = \
                    list(set(recommended_challenge_we_vote_id_list + challenge_we_vote_id_list))

    results = challenge_manager.retrieve_challenge_list_by_challenge_we_vote_id_list(
        challenge_we_vote_id_list=recommended_challenge_we_vote_id_list,
        read_only=read_only)
    challenge_list_found = results['challenge_list_found']
    challenge_list = results['challenge_list']
    status += results['status']

    if challenge_list_found:
        if len(challenge_list) > minimum_number_of_challenge_options:
            # Consider sorting this list and filtering out ones with lowest "score"
            pass

    results = {
        'success': success,
        'status': status,
        'challenge_list_found': challenge_list_found,
        'challenge_list': challenge_list,
    }
    return results


def update_challenge_from_politician(challenge, politician):
    status = ''
    success = True
    save_changes = True
    fields_updated = [
        'organization_we_vote_id',
        'profile_image_background_color',
        'seo_friendly_path',
        'we_vote_hosted_challenge_photo_large_url', 'we_vote_hosted_challenge_photo_medium_url',
        'we_vote_hosted_challenge_photo_small_url',
        'we_vote_hosted_profile_image_url_large', 'we_vote_hosted_profile_image_url_medium',
        'we_vote_hosted_profile_image_url_tiny',
    ]
    challenge.organization_we_vote_id = politician.organization_we_vote_id
    # We want to match the challenge profile images to whatever is in the politician (even None)
    challenge.we_vote_hosted_profile_image_url_large = politician.we_vote_hosted_profile_image_url_large
    challenge.we_vote_hosted_profile_image_url_medium = politician.we_vote_hosted_profile_image_url_medium
    challenge.we_vote_hosted_profile_image_url_tiny = politician.we_vote_hosted_profile_image_url_tiny
    challenge.profile_image_background_color = politician.profile_image_background_color
    # TEMPORARY - Clear out we_vote_hosted_challenge_photo_large_url photos for challenges hard-linked to politicians
    #  because all of these images were copied from the politician, and we now have a new location for them
    if positive_value_exists(challenge.politician_we_vote_id):
        challenge.we_vote_hosted_challenge_photo_large_url = None
        challenge.we_vote_hosted_challenge_photo_medium_url = None
        challenge.we_vote_hosted_challenge_photo_small_url = None
    if positive_value_exists(politician.seo_friendly_path):
        challenge.seo_friendly_path = politician.seo_friendly_path
    else:
        challenge.seo_friendly_path = None

    # if not positive_value_exists(challenge.wikipedia_url) and \
    #         positive_value_exists(politician.wikipedia_url):
    #     challenge.wikipedia_url = politician.wikipedia_url
    #     save_changes = True

    results = {
        'challenge':        challenge,
        'fields_updated':   fields_updated,
        'save_changes':     save_changes,
        'success':          success,
        'status':           status,
    }
    return results


def update_challenges_from_politician_list(politician_list):
    error_message_to_print = ''
    info_message_to_print = ''
    status = ""
    success = True

    challenge_we_vote_id_list = []
    for politician in politician_list:
        if positive_value_exists(politician.linked_challenge_we_vote_id) and \
                politician.linked_challenge_we_vote_id not in challenge_we_vote_id_list:
            challenge_we_vote_id_list.append(politician.linked_challenge_we_vote_id)
    if len(challenge_we_vote_id_list) > 0:
        challenge_list = []
        try:
            queryset = Challenge.objects.filter(we_vote_id__in=challenge_we_vote_id_list)  # Cannot be 'readonly'
            challenge_list = list(queryset)
        except Exception as e:
            status += "ERROR with Challenge.objects.filter: {e}, ".format(e=e)
            success = False

        # Create dict
        challenge_dict = {challenge.we_vote_id: challenge for challenge in challenge_list}

        # Update all entries in the database
        challenge_bulk_update_list = []
        fields_updated = []
        for politician in politician_list:
            challenge = challenge_dict.get(politician.linked_challenge_we_vote_id, None)
            if challenge:
                results = update_challenge_from_politician(challenge, politician)
                if not results['success']:
                    status += results['status'] + " "
                else:
                    save_changes = results['save_changes']
                    if save_changes:
                        challenge_bulk_update_list.append(results['challenge'])
                        fields_updated = results['fields_updated']  # Doesn't need to be set again-and-again

        if len(challenge_bulk_update_list) > 0:
            try:
                Challenge.objects.bulk_update(challenge_bulk_update_list, fields_updated)
                info_message_to_print = \
                    "{challenge_updates_made:,} Challenge entries updated with data from politician. " \
                    "".format(challenge_updates_made=len(challenge_bulk_update_list))
            except Exception as e:
                status += "ERROR_WITH_Challenge.objects.bulk_update: {e}, ".format(e=e)
                success = False
        else:
            status += "NO_CHALLENGES_TO_UPDATE "

    results = {
        'error_message_to_print':   error_message_to_print,
        'info_message_to_print':    info_message_to_print,
        'success':                  success,
        'status':                   status,
    }
    return results
