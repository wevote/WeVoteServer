# politician/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import base64
import copy
from io import BytesIO
from PIL import Image, ImageOps
import re
from datetime import datetime
from django.db.models import Q
from django.contrib.postgres.search import TrigramSimilarity
from django.http import HttpResponse
from exception.models import handle_exception
import json

from campaign.models import CampaignXManager, FINAL_ELECTION_DATE_COOL_DOWN, CampaignXOwner
from candidate.controllers import add_name_to_next_spot, copy_field_value_from_object1_to_object2, \
    generate_candidate_dict_list_from_candidate_object_list, move_candidates_to_another_politician
from candidate.models import CandidateListManager, CandidateManager, PROFILE_IMAGE_TYPE_FACEBOOK, \
    PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_VOTE_USA, CandidateCampaign
from email_outbound.models import EmailAddress
from image.controllers import cache_image_object_to_aws, create_resized_images
from office.models import ContestOfficeManager, ContestOfficeListManager, ContestOffice
from office_held.controllers import generate_office_held_dict_list_from_office_held_we_vote_id_list
from organization.models import Organization, OrganizationManager
from politician.controllers_generate_seo_friendly_path import generate_campaign_title_from_politician
from politician.models import Politician, PoliticianManager, PoliticianSEOFriendlyPath, \
    POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED, POLITICIAN_UNIQUE_IDENTIFIERS, UNKNOWN
from position.controllers import move_positions_to_another_politician
import pytz
from representative.controllers import generate_representative_dict_list_from_representative_object_list, \
    move_representatives_to_another_politician
from representative.models import RepresentativeManager
from voter.models import Voter, VoterManager
from config.base import get_environment_variable
import wevote_functions.admin
from wevote_functions.functions import candidate_party_display, convert_to_int, \
    convert_to_political_party_constant, extract_instagram_handle_from_text_string, \
    generate_random_string, positive_value_exists, \
    process_request_from_master, remove_middle_initial_from_name
from wevote_functions.functions_date import convert_date_to_we_vote_date_string, \
    convert_we_vote_date_string_to_date_as_integer, generate_date_as_integer, \
    generate_localized_datetime_from_obj, DATE_FORMAT_YMD_HMS

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut
# Also search image/controllers.py for these constants
PROFILE_IMAGE_ORIGINAL_MAX_WIDTH = 2048
PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT = 2048
POLITICIAN_RETRIEVE_ERROR_DICT = {
    'ballotpedia_politician_url': '',
    'candidate_list': '',
    'candidate_list_exists': '',
    'final_election_date_in_past': True,
    'in_draft_mode': True,
    'instagram_handle': '',
    'is_supporters_count_minimum_exceeded': False,
    'linked_campaignx_we_vote_id': '',
    'office_held_list': '',
    'office_held_list_exists': '',
    'opponent_candidate_list': '',
    'opponent_candidate_list_exists': '',
    'opposers_count': 0,
    'organization_we_vote_id': '',
    'political_party': '',
    'politician_candidate_list': [],
    'politician_candidate_list_exists': False,
    'politician_description': '',
    'politician_email': '',
    'politician_email2': '',
    'politician_email3': '',
    'politician_name': '',
    'politician_news_item_list': '',
    'politician_owner_list': [],
    'politician_twitter_handle': '',
    'politician_twitter_handle2': '',
    'politician_ultimate_election_date': 0,
    'politician_url': '',
    'politician_we_vote_id': '',
    # 'is_blocked_by_we_vote':            politician.is_blocked_by_we_vote,
    # 'is_blocked_by_we_vote_reason':     politician.is_blocked_by_we_vote_reason,
    # 'latest_politician_supporter_endorsement_list':  latest_politician_supporter_endorsement_list,
    # 'latest_politician_supporter_list':  latest_politician_supporter_list,
    'profile_image_background_color': '',
    'representative_list': '',
    'representative_list_exists': '',
    'seo_friendly_path': '',
    'seo_friendly_path_list': '',
    'state_code': '',
    'status': '',
    'success': False,
    'supporters_count': 0,
    'supporters_count_next_goal':       0,
    'supporters_count_victory_goal':    0,
    'twitter_followers_count': '',
    'visible_on_this_site':             False,
    'voter_politician_supporter':        {},
    'voter_can_send_updates_to_politician': False,
    'voter_can_vote_for_politician_we_vote_ids': '',
    'voter_is_politician_owner': False,
    'voter_signed_in_with_email': False,
    'we_vote_hosted_profile_image_url_large': '',
    'we_vote_hosted_profile_image_url_medium': '',
    'we_vote_hosted_profile_image_url_tiny': '',
    'wikipedia_url': '',
    'youtube_url': '',
}


def add_alternate_names_to_next_spot(politician):
    status = ''
    success = True
    values_changed = False
    if not hasattr(politician, 'politician_name') or not positive_value_exists(politician.politician_name):
        status += 'POLITICIAN_MISSING '
        return {
            'success':          False,
            'status':           status,
            'politician':       politician,
            'values_changed':   values_changed,
        }

    from wevote_functions.functions import MIDDLE_INITIAL_SUBSTRINGS
    # Does the politician.politician_name contain a single middle initial?

    middle_initial_found = False
    name_without_middle_initial = ''
    politician_name_has_middle_initial = False
    for middle_initial_substring in MIDDLE_INITIAL_SUBSTRINGS:
        if not middle_initial_found and middle_initial_substring in politician.politician_name:
            middle_initial_found = True
            politician_name_has_middle_initial = True
            name_without_middle_initial = politician.politician_name.replace(middle_initial_substring, ' ')
            status += "MIDDLE_INITIAL_FOUND "
    if politician_name_has_middle_initial and positive_value_exists(name_without_middle_initial):
        if name_without_middle_initial != politician.google_civic_candidate_name and \
                name_without_middle_initial != politician.google_civic_candidate_name2 and \
                name_without_middle_initial != politician.google_civic_candidate_name3:
            # We do not have an alternate name WITHOUT the middle initial. Save it.
            results = add_name_to_next_spot(politician, name_without_middle_initial)
            if results['success'] and results['values_changed']:
                status += "POLITICIAN_CHANGED "
                politician = results['candidate_or_politician']
                values_changed = True
            elif not results['success']:
                status += results['status']
                success = False
    # We currently only support 3 alternate names
    return {
        'success':          success,
        'status':           status,
        'politician':       politician,
        'values_changed':   values_changed,
    }


def add_twitter_handle_to_next_politician_spot(politician, twitter_handle):
    status = ''
    success = True
    values_changed = False
    if not positive_value_exists(twitter_handle):
        status += 'TWITTER_HANDLE_MISSING '
        return {
            'success':          False,
            'status':           status,
            'politician':       politician,
            'values_changed':   values_changed,
        }

    if not positive_value_exists(politician.politician_twitter_handle):
        politician.politician_twitter_handle = twitter_handle
        politician.twitter_handle_updates_failing = False
        values_changed = True
    elif twitter_handle.lower() == politician.politician_twitter_handle.lower():
        # The value is already stored in politician.politician_twitter_handle so doesn't need
        # to be added anywhere below
        pass
    elif not positive_value_exists(politician.politician_twitter_handle2):
        politician.politician_twitter_handle2 = twitter_handle
        politician.twitter_handle2_updates_failing = False
        values_changed = True
    elif twitter_handle.lower() == politician.politician_twitter_handle2.lower():
        # The value is already stored in politician.politician_twitter_handle2 so doesn't need
        # to be added to politician.politician_twitter_handle3
        pass
    elif not positive_value_exists(politician.politician_twitter_handle3):
        politician.politician_twitter_handle3 = twitter_handle
        values_changed = True
    elif twitter_handle.lower() == politician.politician_twitter_handle3.lower():
        # The value is already stored in politician.politician_twitter_handle3 so doesn't need
        # to be added to politician.politician_twitter_handle4
        pass
    elif not positive_value_exists(politician.politician_twitter_handle4):
        politician.politician_twitter_handle4 = twitter_handle
        values_changed = True
    elif twitter_handle.lower() == politician.politician_twitter_handle4.lower():
        # The value is already stored in politician.politician_twitter_handle4 so doesn't need
        # to be added to politician.politician_twitter_handle5
        pass
    elif not positive_value_exists(politician.politician_twitter_handle5):
        politician.politician_twitter_handle5 = twitter_handle
        values_changed = True
    # We currently only support 5 alternate names
    return {
        'success': success,
        'status': status,
        'politician': politician,
        'values_changed': values_changed,
    }


def add_url_to_politician_url_spot(politician, incoming_politician_url, position=-1):
    """
    :param politician:
    :param incoming_politician_url:
    :param position: -1 means add at the end of the list, 1 means add at the beginning of the list
    :return:
    """
    position = convert_to_int(position)
    status = ''
    success = True
    values_changed = True  # With this implementation, we always assume a change

    previous_url1 = politician.politician_url
    previous_url2 = politician.politician_url2
    previous_url3 = politician.politician_url3
    previous_url4 = politician.politician_url4
    previous_url5 = politician.politician_url5
    reordered_urls = []
    if positive_value_exists(previous_url1):
        reordered_urls.append(previous_url1)
    if positive_value_exists(previous_url2):
        reordered_urls.append(previous_url2)
    if positive_value_exists(previous_url3):
        reordered_urls.append(previous_url3)
    if positive_value_exists(previous_url4):
        reordered_urls.append(previous_url4)
    if positive_value_exists(previous_url5):
        reordered_urls.append(previous_url5)

    # Remove incoming_politician_url from the reordered_urls array (if it exists)
    reordered_urls = [url for url in reordered_urls if url.lower() != incoming_politician_url.lower()]

    number_of_urls = len(reordered_urls)
    if position == 0:
        position_as_index = 0
    elif position < 0:
        if number_of_urls == 0:
            position_as_index = 0
        else:
            position_as_index = number_of_urls - 1
    elif 0 < position <= 5:
        if position >= number_of_urls:
            position_as_index = number_of_urls - 1
        else:
            position_as_index = position - 1
    else:
        status += 'POSITION_OUT_OF_RANGE_PLACED_AT_END '
        position_as_index = number_of_urls

    # We place the url, even if incoming_politician_url is an empty string
    reordered_urls.insert(position_as_index, incoming_politician_url)

    # Place the reordered URLs back into the politician object
    politician.politician_url = reordered_urls[0] if reordered_urls else None
    politician.politician_url2 = reordered_urls[1] if len(reordered_urls) > 1 else None
    politician.politician_url3 = reordered_urls[2] if len(reordered_urls) > 2 else None
    politician.politician_url4 = reordered_urls[3] if len(reordered_urls) > 3 else None
    politician.politician_url5 = reordered_urls[4] if len(reordered_urls) > 4 else None
    # We currently only support 5 politician URLs
    return {
        'success': success,
        'status': status,
        'politician': politician,
        'values_changed': values_changed,
    }


def fetch_duplicate_politician_count(we_vote_politician, ignore_politician_id_list):
    if not hasattr(we_vote_politician, 'politician_name'):
        return 0

    politician_manager = PoliticianManager()
    politician_twitter_handle_list = []
    if positive_value_exists(we_vote_politician.politician_twitter_handle):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle)
    if positive_value_exists(we_vote_politician.politician_twitter_handle2):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle2)
    if positive_value_exists(we_vote_politician.politician_twitter_handle3):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle3)
    if positive_value_exists(we_vote_politician.politician_twitter_handle4):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle4)
    if positive_value_exists(we_vote_politician.politician_twitter_handle5):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle5)
    return politician_manager.fetch_politicians_from_non_unique_identifiers_count(
        state_code=we_vote_politician.state_code,
        twitter_handle_list=politician_twitter_handle_list,
        politician_name=we_vote_politician.politician_name,
        ignore_politician_id_list=ignore_politician_id_list)


def fetch_number_of_politicians_to_match_to_organizations():
    try:
        # Count the number of Politicians who need an organization to be generated
        queryset = Politician.objects.using('readonly').all()
        queryset = queryset.filter(organization_analysis_needed=True)
        queryset = queryset.exclude(organization_manual_intervention_needed=True)
        organization_might_be_needed_count = queryset.count()
        return organization_might_be_needed_count
    except Exception as e:
        status = f"ERROR: fetch_number_of_politicians_to_match_to_organizations: {e}"
        return 0


def find_duplicate_politician(we_vote_politician, ignore_politician_id_list, read_only=True):
    status = ''
    success = True
    if not hasattr(we_vote_politician, 'politician_name'):
        status += "FIND_DUPLICATE_POLITICIAN_MISSING_POLITICIAN_OBJECT "
        error_results = {
            'success':                              False,
            'status':                               status,
            'politician_merge_possibility_found':   False,
            'politician_list':                      [],
        }
        return error_results

    politician_manager = PoliticianManager()
    politician_twitter_handle_list = []
    if positive_value_exists(we_vote_politician.politician_twitter_handle):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle)
    if positive_value_exists(we_vote_politician.politician_twitter_handle2):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle2)
    if positive_value_exists(we_vote_politician.politician_twitter_handle3):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle3)
    if positive_value_exists(we_vote_politician.politician_twitter_handle4):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle4)
    if positive_value_exists(we_vote_politician.politician_twitter_handle5):
        politician_twitter_handle_list.append(we_vote_politician.politician_twitter_handle5)

    # Search for other politicians that share the same elections that match name and election
    try:
        results = politician_manager.retrieve_politicians_from_non_unique_identifiers(
            state_code=we_vote_politician.state_code,
            twitter_handle_list=politician_twitter_handle_list,
            politician_name=we_vote_politician.politician_name,
            ignore_politician_id_list=ignore_politician_id_list,
            read_only=read_only)

        if results['politician_found']:
            conflict_results = figure_out_politician_conflict_values(we_vote_politician, results['politician'])
            politician_merge_conflict_values = conflict_results['politician_merge_conflict_values']
            if not conflict_results['success']:
                status += conflict_results['status']
                success = conflict_results['success']
            status += "FIND_DUPLICATE_POLITICIAN_DUPLICATE_FOUND "
            results = {
                'success':                              success,
                'status':                               status,
                'politician_merge_possibility_found':   True,
                'politician_merge_possibility':         results['politician'],
                'politician_merge_conflict_values':     politician_merge_conflict_values,
                'politician_list':                      results['politician_list'],
            }
            return results
        elif results['politician_list_found']:
            # Only deal with merging the incoming politician and the first on found
            conflict_results = figure_out_politician_conflict_values(we_vote_politician, results['politician_list'][0])
            politician_merge_conflict_values = conflict_results['politician_merge_conflict_values']
            if not conflict_results['success']:
                status += conflict_results['status']
                success = conflict_results['success']
            status += "FIND_DUPLICATE_POLITICIAN_DUPLICATES_FOUND_FROM_LIST "
            results = {
                'success':                              success,
                'status':                               status,
                'politician_merge_possibility_found':   True,
                'politician_merge_possibility':         results['politician_list'][0],
                'politician_merge_conflict_values':     politician_merge_conflict_values,
                'politician_list':                      results['politician_list'],
            }
            return results
        else:
            status += "FIND_DUPLICATE_POLITICIAN_NO_DUPLICATES_FOUND "
            results = {
                'success':                              success,
                'status':                               status,
                'politician_merge_possibility_found':   False,
                'politician_list':                      results['politician_list'],
            }
            return results

    except Exception as e:
        status += "FIND_DUPLICATE_POLITICIAN_ERROR: " + str(e) + ' '
        success = False

    results = {
        'success':                              success,
        'status':                               status,
        'politician_merge_possibility_found':   False,
        'politician_list':                      [],
    }
    return results


def find_campaignx_list_to_link_to_this_politician(politician=None):
    """
    Find Campaigns to Link to this Politician
    Finding Campaigns that *might* be "children" of this politician

    :param politician:
    :return:
    """
    if not hasattr(politician, 'we_vote_id'):
        return []
    from campaign.models import CampaignX
    try:
        related_list = CampaignX.objects.using('readonly').all()
        related_list = related_list.exclude(
            linked_politician_we_vote_id=politician.we_vote_id)
        related_list = related_list.filter(campaign_title__icontains=politician.first_name)
        related_list = related_list.filter(campaign_title__icontains=politician.last_name)

        # filters = []
        # new_filter = \
        #     Q(campaign_title__icontains=politician.first_name) & \
        #     Q(campaign_title__icontains=politician.last_name)
        # filters.append(new_filter)
        #
        # # Add the first query
        # if len(filters):
        #     final_filters = filters.pop()
        #
        #     # ...and "OR" the remaining items in the list
        #     for item in filters:
        #         final_filters |= item
        #
        #     related_list = related_list.filter(final_filters)

        related_list = related_list.order_by('campaign_title')[:20]
    except Exception as e:
        related_list = []
    return related_list


def find_candidates_to_link_to_this_politician(politician=None,use_trigram_match=False):
    """
    Find Candidates to Link to this Politician
    Finding Candidates that *might* be "children" of this politician
    Uses PostgreSQL trigram (pg_trgm) for fast, fuzzy name matching.

    :param politician:
    :return:
    """
    if not hasattr(politician, 'we_vote_id'):
        return []
    related_candidate_list = []
    from candidate.models import CandidateCampaign
    try:
        queryset = CandidateCampaign.objects.using('readonly').all()
        queryset = queryset.exclude(
            politician_we_vote_id=politician.we_vote_id)

        filters = []
               
        # Use icontains for FILTERING (fast B-tree index), trigram only for ORDERING if requested
        if positive_value_exists(politician.first_name) and positive_value_exists(politician.last_name):
            new_filter = \
            Q(candidate_name__icontains=politician.first_name) & \
            Q(candidate_name__icontains=politician.last_name)
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle):
            new_filter = (
                Q(candidate_twitter_handle__iexact=politician.politician_twitter_handle) |
                Q(candidate_twitter_handle2__iexact=politician.politician_twitter_handle) |
                Q(candidate_twitter_handle3__iexact=politician.politician_twitter_handle)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle2):
            new_filter = (
                Q(candidate_twitter_handle__iexact=politician.politician_twitter_handle2) |
                Q(candidate_twitter_handle2__iexact=politician.politician_twitter_handle2) |
                Q(candidate_twitter_handle3__iexact=politician.politician_twitter_handle2)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle3):
            new_filter = (
                Q(candidate_twitter_handle__iexact=politician.politician_twitter_handle3) |
                Q(candidate_twitter_handle2__iexact=politician.politician_twitter_handle3) |
                Q(candidate_twitter_handle3__iexact=politician.politician_twitter_handle3)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle4):
            new_filter = (
                Q(candidate_twitter_handle__iexact=politician.politician_twitter_handle4) |
                Q(candidate_twitter_handle2__iexact=politician.politician_twitter_handle4) |
                Q(candidate_twitter_handle3__iexact=politician.politician_twitter_handle4)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle5):
            new_filter = (
                Q(candidate_twitter_handle__iexact=politician.politician_twitter_handle5) |
                Q(candidate_twitter_handle2__iexact=politician.politician_twitter_handle5) |
                Q(candidate_twitter_handle3__iexact=politician.politician_twitter_handle5)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.vote_smart_id):
            new_filter = Q(vote_smart_id=politician.vote_smart_id)
            filters.append(new_filter)

        if positive_value_exists(politician.vote_usa_politician_id):
            new_filter = Q(vote_usa_politician_id=politician.vote_usa_politician_id)
            filters.append(new_filter)

        # Add the first query
        if len(filters):
            final_filters = filters.pop()

            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item

            queryset = queryset.filter(final_filters)

        # Apply trigram ordering ONLY for ranking (not filtering) on already filtered results
        if use_trigram_match:
            queryset = queryset.annotate(
                trigram_match=TrigramSimilarity('candidate_name', politician.politician_name)
            )
            queryset = queryset.order_by('-trigram_match', 'candidate_name')
        else:
            queryset = queryset.order_by('candidate_name')
        queryset = queryset[:20]
        related_candidate_list = list(queryset)
    except Exception as e:
        related_candidate_list = []
    return related_candidate_list


def find_representatives_to_link_to_this_politician(politician=None):
    """
    Find Representatives to Link to this Politician
    Finding Representatives that *might* be "children" of this politician

    :param politician:
    :return:
    """
    if not hasattr(politician, 'we_vote_id'):
        return []
    from representative.models import Representative
    try:
        related_representative_list = Representative.objects.using('readonly').all()
        related_representative_list = related_representative_list.exclude(
            politician_we_vote_id=politician.we_vote_id)

        filters = []
        new_filter = \
            Q(representative_name__icontains=politician.first_name) & \
            Q(representative_name__icontains=politician.last_name)
        filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle):
            new_filter = (
                Q(representative_twitter_handle__iexact=politician.politician_twitter_handle) |
                Q(representative_twitter_handle2__iexact=politician.politician_twitter_handle) |
                Q(representative_twitter_handle3__iexact=politician.politician_twitter_handle)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle2):
            new_filter = (
                Q(representative_twitter_handle__iexact=politician.politician_twitter_handle2) |
                Q(representative_twitter_handle2__iexact=politician.politician_twitter_handle2) |
                Q(representative_twitter_handle3__iexact=politician.politician_twitter_handle2)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle3):
            new_filter = (
                Q(representative_twitter_handle__iexact=politician.politician_twitter_handle3) |
                Q(representative_twitter_handle2__iexact=politician.politician_twitter_handle3) |
                Q(representative_twitter_handle3__iexact=politician.politician_twitter_handle3)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle4):
            new_filter = (
                Q(representative_twitter_handle__iexact=politician.politician_twitter_handle4) |
                Q(representative_twitter_handle2__iexact=politician.politician_twitter_handle4) |
                Q(representative_twitter_handle3__iexact=politician.politician_twitter_handle4)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.politician_twitter_handle5):
            new_filter = (
                Q(representative_twitter_handle__iexact=politician.politician_twitter_handle5) |
                Q(representative_twitter_handle2__iexact=politician.politician_twitter_handle5) |
                Q(representative_twitter_handle3__iexact=politician.politician_twitter_handle5)
            )
            filters.append(new_filter)

        if positive_value_exists(politician.vote_usa_politician_id):
            new_filter = Q(vote_usa_politician_id=politician.vote_usa_politician_id)
            filters.append(new_filter)

        # Add the first query
        if len(filters):
            final_filters = filters.pop()

            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item

            related_representative_list = related_representative_list.filter(final_filters)

        related_representative_list = related_representative_list.order_by('representative_name')[:20]
    except Exception as e:
        related_representative_list = []
    return related_representative_list


def figure_out_politician_conflict_values(politician1, politician2):
    """
    See also merge_if_duplicate_politicians
    :param politician1:
    :param politician2:
    :return:
    """
    status = ''
    success = True
    politician_merge_conflict_values = {}

    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        try:
            politician1_attribute_value = getattr(politician1, attribute)
            try:
                politician1_attribute_value_lower_case = politician1_attribute_value.lower()
            except Exception:
                politician1_attribute_value_lower_case = None
            politician2_attribute_value = getattr(politician2, attribute)
            try:
                politician2_attribute_value_lower_case = politician2_attribute_value.lower()
            except Exception:
                politician2_attribute_value_lower_case = None
            if politician1_attribute_value is None and politician2_attribute_value is None:
                politician_merge_conflict_values[attribute] = 'MATCHING'
            elif politician1_attribute_value is None or politician1_attribute_value == "":
                politician_merge_conflict_values[attribute] = 'POLITICIAN2'
            elif politician2_attribute_value is None or politician2_attribute_value == "":
                politician_merge_conflict_values[attribute] = 'POLITICIAN1'
            elif attribute == "gender":
                if politician1_attribute_value == politician2_attribute_value:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                elif politician1_attribute_value is UNKNOWN and positive_value_exists(politician2_attribute_value):
                    politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                elif politician2_attribute_value is UNKNOWN and positive_value_exists(politician1_attribute_value):
                    politician_merge_conflict_values[attribute] = 'POLITICIAN1'
                else:
                    politician_merge_conflict_values[attribute] = 'CONFLICT'
            elif attribute.startswith("is_battleground_race_"):
                # We always want to default to preserving a true value
                if politician1_attribute_value == politician2_attribute_value:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                elif positive_value_exists(politician1_attribute_value):
                    politician_merge_conflict_values[attribute] = 'POLITICIAN1'
                elif positive_value_exists(politician2_attribute_value):
                    politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                else:
                    politician_merge_conflict_values[attribute] = 'POLITICIAN1'
            elif attribute.startswith("linked_campaignx_we_vote_id"):
                # 2024-May We are defaulting to choosing the lowest campaignx_we_vote_id
                if politician1_attribute_value == politician2_attribute_value:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                else:
                    politician1_campaignx_integer_part = convert_to_int(politician1_attribute_value[8:])
                    politician2_campaignx_integer_part = convert_to_int(politician2_attribute_value[8:])
                    if politician1_campaignx_integer_part > politician2_campaignx_integer_part:
                        politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                    else:
                        politician_merge_conflict_values[attribute] = 'POLITICIAN1'
            elif attribute == "ocd_id_state_mismatch_found":
                if positive_value_exists(politician1_attribute_value):
                    politician_merge_conflict_values[attribute] = 'POLITICIAN1'
                elif positive_value_exists(politician2_attribute_value):
                    politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                else:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
            elif attribute == "political_party":
                if convert_to_political_party_constant(politician1_attribute_value) == \
                        convert_to_political_party_constant(politician2_attribute_value):
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                else:
                    politician_merge_conflict_values[attribute] = 'CONFLICT'
            elif attribute == "politician_name":
                if politician1_attribute_value_lower_case == politician2_attribute_value_lower_case:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                else:
                    try:
                        middle_results = remove_middle_initial_from_name(politician1_attribute_value)
                        politician1_name_without_middle_initials = middle_results['modified_name']
                        politician1_name_without_middle_initials_lower_case = \
                            politician1_name_without_middle_initials.lower()
                    except Exception:
                        politician1_name_without_middle_initials_lower_case = None
                    try:
                        middle_results = remove_middle_initial_from_name(politician2_attribute_value)
                        politician2_name_without_middle_initials = middle_results['modified_name']
                        politician2_name_without_middle_initials_lower_case = \
                            politician2_name_without_middle_initials.lower()
                    except Exception:
                        politician2_name_without_middle_initials_lower_case = None
                    if politician1_name_without_middle_initials_lower_case == \
                            politician2_name_without_middle_initials_lower_case:
                        # If they are the same without middle initial, favor the original name without middle initial
                        if len(politician1_attribute_value_lower_case) < len(politician2_attribute_value_lower_case):
                            politician_merge_conflict_values[attribute] = 'POLITICIAN1'
                        elif len(politician2_attribute_value_lower_case) < len(politician1_attribute_value_lower_case):
                            politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                        else:
                            politician_merge_conflict_values[attribute] = 'CONFLICT'
                    else:
                        politician_merge_conflict_values[attribute] = 'CONFLICT'
            elif attribute == "seo_friendly_path":
                if politician1_attribute_value_lower_case == politician2_attribute_value_lower_case:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                elif len(politician1_attribute_value_lower_case) > 0 and len(
                        politician2_attribute_value_lower_case) == 0:
                    politician_merge_conflict_values[attribute] = 'POLITICIAN1'
                elif len(politician1_attribute_value_lower_case) == 0 and len(
                        politician2_attribute_value_lower_case) > 0:
                    politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                elif len(politician1_attribute_value_lower_case) > 5 and len(
                        politician2_attribute_value_lower_case) > 5:
                    # If we remove the last four digits from the path, are the strings identical?
                    politician1_attribute_value_lower_case_minus_four_digits = \
                        politician1_attribute_value_lower_case[:-4]
                    politician2_attribute_value_lower_case_minus_four_digits = \
                        politician2_attribute_value_lower_case[:-4]
                    if politician1_attribute_value_lower_case == \
                            politician2_attribute_value_lower_case_minus_four_digits:
                        politician_merge_conflict_values[attribute] = 'POLITICIAN1'
                    elif politician2_attribute_value_lower_case == \
                            politician1_attribute_value_lower_case_minus_four_digits:
                        politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                    else:
                        politician_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    politician_merge_conflict_values[attribute] = 'CONFLICT'
            elif attribute == "state_code":
                if politician1_attribute_value_lower_case == politician2_attribute_value_lower_case:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                else:
                    politician_merge_conflict_values[attribute] = 'CONFLICT'
            else:
                if politician1_attribute_value == politician2_attribute_value:
                    politician_merge_conflict_values[attribute] = 'MATCHING'
                else:
                    politician_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError as e:
            status += "COULD_NOT_PROCESS_ATTRIBUTE: " + str(attribute) + ": " + str(e)
            success = False

    return {
        'status': status,
        'success': success,
        'politician_merge_conflict_values': politician_merge_conflict_values,
    }


def generate_campaignx_for_politician(
        datetime_now=None,
        politician=None,
        save_individual_politician=False):
    status = ""
    success = True
    update_values = {}
    update_values['linked_politician_we_vote_id'] = politician.we_vote_id
    campaign_title = generate_campaign_title_from_politician(
        politician_name=politician.politician_name,
        state_code=politician.state_code)
    if positive_value_exists(campaign_title):
        update_values['campaign_title'] = campaign_title
        update_values['campaign_title_changed'] = True
    if positive_value_exists(politician.twitter_description):
        update_values['campaign_description'] = politician.twitter_description
        update_values['campaign_description_changed'] = True
        update_values['campaign_description_linked_to_twitter'] = True
    if positive_value_exists(politician.we_vote_hosted_profile_image_url_large):
        update_values['we_vote_hosted_profile_image_url_large'] = politician.we_vote_hosted_profile_image_url_large
        update_values['politician_photo_changed'] = True
    if positive_value_exists(politician.we_vote_hosted_profile_image_url_medium):
        update_values['we_vote_hosted_profile_image_url_medium'] = politician.we_vote_hosted_profile_image_url_medium
        update_values['politician_photo_changed'] = True
    if positive_value_exists(politician.we_vote_hosted_profile_image_url_tiny):
        update_values['we_vote_hosted_profile_image_url_tiny'] = politician.we_vote_hosted_profile_image_url_tiny
        update_values['politician_photo_changed'] = True
    update_values['in_draft_mode'] = False
    update_values['in_draft_mode_changed'] = True

    campaignx_manager = CampaignXManager()
    results = campaignx_manager.update_or_create_campaignx(
        politician_we_vote_id=politician.we_vote_id,
        update_values=update_values,
    )
    campaignx_created = False
    if results['campaignx_found']:
        campaignx_created = True
        if datetime_now is None:
            # timezone = pytz.timezone("America/Los_Angeles")
            # datetime_now = timezone.localize(datetime.now())
            datetime_now = generate_localized_datetime_from_obj()[1]
        politician.linked_campaignx_we_vote_id = results['campaignx'].we_vote_id
        politician.linked_campaignx_we_vote_id_date_last_updated = datetime_now
        if positive_value_exists(save_individual_politician):
            try:
                politician.save()
            except Exception as e:
                status += "COULD_NOT_SAVE_INDIVIDUAL_POLITICIAN: " + str(e) + " "
                success = False

    results = {
        'campaignx_created':    campaignx_created,
        'status':               status,
        'success':              success,
        'politician':           politician,
    }
    return results


def generate_politician_dict_from_politician_object(politician=None):
    success = True
    status = ""
    # If smaller sizes weren't stored, use large image
    if politician.we_vote_hosted_profile_image_url_medium:
        we_vote_hosted_profile_image_url_medium = politician.we_vote_hosted_profile_image_url_medium
    else:
        we_vote_hosted_profile_image_url_medium = politician.we_vote_hosted_profile_image_url_large
    if politician.we_vote_hosted_profile_image_url_tiny:
        we_vote_hosted_profile_image_url_tiny = politician.we_vote_hosted_profile_image_url_tiny
    else:
        we_vote_hosted_profile_image_url_tiny = politician.we_vote_hosted_profile_image_url_large
    # supporters_count_next_goal = politician_manager.fetch_supporters_count_next_goal(
    #     supporters_count=politician.supporters_count,
    #     supporters_count_victory_goal=politician.supporters_count_victory_goal)
    today_as_integer = generate_date_as_integer()
    final_election_date_in_past = \
        today_as_integer > politician.politician_ultimate_election_date \
        if positive_value_exists(politician.politician_ultimate_election_date) else True
    if positive_value_exists(politician.ballot_guide_official_statement):
        politician_description = politician.ballot_guide_official_statement
    elif positive_value_exists(politician.twitter_description):
        politician_description = politician.twitter_description
    else:
        politician_description = ''
    instagram_handle = extract_instagram_handle_from_text_string(politician.instagram_handle)
    is_claimed_profile_date_time = ''
    if positive_value_exists(politician.is_claimed_profile_date_time):
        is_claimed_profile_date_time = politician.is_claimed_profile_date_time.strftime(DATE_FORMAT_YMD_HMS)
    politician_dict = {
        'ballot_guide_official_statement':  politician.ballot_guide_official_statement,
        'ballotpedia_politician_url':       politician.ballotpedia_politician_url,
        'bluesky_handle':                   politician.bluesky_handle,
        'final_election_date_in_past':      final_election_date_in_past,
        'instagram_handle':                 instagram_handle,
        'is_claimed_profile':               positive_value_exists(politician.is_claimed_profile),
        'is_claimed_profile_date_time':     is_claimed_profile_date_time,
        'linked_campaignx_we_vote_id':      politician.linked_campaignx_we_vote_id,
        'opposers_count':                   politician.opposers_count,
        'political_party':                  candidate_party_display(politician.political_party),
        'politician_description':           politician_description,
        'politician_email':                 politician.politician_email,
        'politician_email2':                politician.politician_email2,
        'politician_email3':                politician.politician_email3,
        'politician_name':                  politician.politician_name,
        'politician_twitter_handle':        politician.politician_twitter_handle,
        'politician_twitter_handle2':       politician.politician_twitter_handle2,
        'politician_url':                   politician.politician_url,
        'politician_we_vote_id':            politician.we_vote_id,
        # 'in_draft_mode':                    politician.in_draft_mode,
        # 'is_blocked_by_we_vote':            politician.is_blocked_by_we_vote,
        # 'is_blocked_by_we_vote_reason':     politician.is_blocked_by_we_vote_reason,
        # 'is_supporters_count_minimum_exceeded': politician.is_supporters_count_minimum_exceeded(),
        'profile_image_background_color':   politician.profile_image_background_color,
        'profile_image_type_currently_active': politician.profile_image_type_currently_active,
        'seo_friendly_path':                politician.seo_friendly_path,
        'state_code':                       politician.state_code,
        'supporters_count':                 politician.supporters_count,
        # 'supporters_count_victory_goal':    politician.supporters_count_victory_goal,
        'threads_handle':                   politician.threads_handle,
        'twitter_followers_count':          politician.twitter_followers_count,
        # 'visible_on_this_site':             politician.visible_on_this_site,
        'we_vote_hosted_profile_ballotpedia_image_url_large':   politician.we_vote_hosted_profile_ballotpedia_image_url_large,
        'we_vote_hosted_profile_facebook_image_url_large':   politician.we_vote_hosted_profile_facebook_image_url_large,
        'we_vote_hosted_profile_image_url_large':   politician.we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny,
        'we_vote_hosted_profile_linkedin_image_url_large':   politician.we_vote_hosted_profile_linkedin_image_url_large,
        'we_vote_hosted_profile_twitter_image_url_large':   politician.we_vote_hosted_profile_twitter_image_url_large,
        'we_vote_hosted_profile_uploaded_image_url_large':   politician.we_vote_hosted_profile_uploaded_image_url_large,
        'we_vote_hosted_profile_vote_usa_image_url_large':   politician.we_vote_hosted_profile_vote_usa_image_url_large,
        'we_vote_hosted_profile_wikipedia_image_url_large':   politician.we_vote_hosted_profile_wikipedia_image_url_large,
        'wikipedia_url':                    politician.wikipedia_url,
        'youtube_url':                      politician.youtube_url,
    }
    results = {
        'politician_dict': politician_dict,
        'status': status,
        'success': success,
    }
    return results


def is_voter_politician_owner(
        politician=None,
        politician_we_vote_id=None,
        voter=None,
        voter_we_vote_id=None,
):
    politician_found = False
    status = ''
    success = True
    voter_emails_found = False
    voter_found = False
    has_permission_to_edit_politician = False

    if voter and positive_value_exists(voter.we_vote_id):
        voter_found = True
        voter_we_vote_id = voter.we_vote_id
    elif positive_value_exists(voter_we_vote_id):
        try:
            voter = Voter.objects.using('readonly').get(we_vote_id=voter_we_vote_id)
            voter_found = True
        except Exception as e:
            status += "VOTER_NOT_FOUND: " + str(e) + " "

    if not voter_found:
        status += "VOTER_REQUIRED_FOR_VOTER_POLITICIAN_OWNERSHIP "
        success = False
        results = {
            'politician_found': politician_found,
            'politician_we_vote_id': politician_we_vote_id,
            'has_permission_to_edit_politician': has_permission_to_edit_politician,
            'status': status,
            'success': success,
        }
        return results

    voter_email_address_list = []
    try:
        queryset = EmailAddress.objects.using('readonly').all()
        queryset = queryset.filter(voter_we_vote_id=voter_we_vote_id)
        queryset = queryset.filter(email_ownership_is_verified=True)
        queryset = queryset.values_list('normalized_email_address', flat=True).distinct()
        voter_email_address_list = list(queryset)
        voter_emails_found = True
    except Exception as e:
        status += "VOTER_EMAILS_NOT_FOUND: " + str(e) + " "
    voter_email_address_set = set(email.lower() for email in voter_email_address_list)

    if not voter_emails_found or len(voter_email_address_list) == 0:
        status += "VOTER_DOES_NOT_HAVE_EMAILS "
        results = {
            'politician_found': politician_found,
            'politician_we_vote_id': politician_we_vote_id,
            'has_permission_to_edit_politician': has_permission_to_edit_politician,
            'status': status,
            'success': success,
        }
        return results

    if politician and positive_value_exists(politician.we_vote_id):
        politician_found = True
        politician_we_vote_id = politician.we_vote_id
    elif positive_value_exists(politician_we_vote_id):
        try:
            politician = Politician.objects.using('readonly').get(we_vote_id=politician_we_vote_id)
            politician_found = True
        except Exception as e:
            status += "POLITICIAN_NOT_FOUND: " + str(e) + " "

    if not politician_found:
        status += "POLITICIAN_REQUIRED_FOR_VOTER_POLITICIAN_OWNERSHIP "
        success = False
        results = {
            'politician_found': politician_found,
            'politician_we_vote_id': politician_we_vote_id,
            'has_permission_to_edit_politician': has_permission_to_edit_politician,
            'status': status,
            'success': success,
        }
        return results

    # Does the voter have a verified email address that matches a politician email address?
    politician_email_address_list = []
    if positive_value_exists(politician.politician_email):
        politician_email_address_list.append(politician.politician_email)
    if positive_value_exists(politician.politician_email2):
        politician_email_address_list.append(politician.politician_email2)
    if positive_value_exists(politician.politician_email3):
        politician_email_address_list.append(politician.politician_email3)
    politician_email_address_set = set(email.lower() for email in politician_email_address_list if email)
    # Check if there's any intersection between the two sets
    matching_emails = voter_email_address_set.intersection(politician_email_address_set)

    if matching_emails:
        has_permission_to_edit_politician = True
        status += f"VOTER_OWNS_POLITICIAN: Matching emails: {', '.join(matching_emails)} "

    if not has_permission_to_edit_politician:
        # Now check to see if the voter is on the Politician's staff (CampaignX Owner)
        campaignx_we_vote_id = politician.linked_campaignx_we_vote_id
        try:
            campaignx_owner_query = CampaignXOwner.objects.using('readonly').filter(
                campaignx_we_vote_id=campaignx_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            has_permission_to_edit_politician = positive_value_exists(campaignx_owner_query.count())
            status += 'VOTER_IS_CAMPAIGNX_OWNER '
        except CampaignXOwner as e:
            status += 'CAMPAIGNX_OWNER_QUERY_FAILED: ' + str(e) + ' '

    results = {
        'politician_found': politician_found,
        'politician_we_vote_id': politician_we_vote_id,
        'has_permission_to_edit_politician': has_permission_to_edit_politician,
        'status': status,
        'success': success,
    }
    return results


def match_politician_to_organization(
        changed_by_name=None,
        changed_by_voter_we_vote_id=None,
        politician=None):
    status = ''
    success = True
    results = {
        'organization_created': False,
        'organization_creation_error': False,
        'politician': politician,
        'politician_error': False,
        'politician_has_two_linked_organizations': False,
        'politician_has_two_possible_organizations': False,
        'politician_updated': False,
        'status': status,
        'success': success,
    }
    from organization.controllers import create_organization_from_politician

    # Search the Organization table to see if there is already an organization linked to this politician
    try:
        queryset = Organization.objects.using('readonly').all()
        queryset = queryset.filter(politician_we_vote_id=politician.we_vote_id)
        linked_organization_list = list(queryset)
        if len(linked_organization_list) > 1:
            politician.organization_analysis_needed = False
            politician.organization_manual_intervention_needed = True
            politician.organization_we_vote_id = linked_organization_list[0].we_vote_id  # Link first one
            politician.politician_has_two_linked_organizations = True
            status += "MULTIPLE_LINKED_ORGS_FOUND "
            for one_linked_org in linked_organization_list:
                status += " [" + str(one_linked_org.we_vote_id) + "] "
            results['politician'] = politician
            results['politician_updated'] = True
            results['politician_has_two_linked_organizations'] = True
            results['status'] = status
            return results
        elif len(linked_organization_list) > 0:
            politician.organization_analysis_needed = False
            politician.organization_manual_intervention_needed = False
            politician.organization_we_vote_id = linked_organization_list[0].we_vote_id  # Link first one
            politician.politician_has_two_linked_organizations = False
            status += "ONE_LINKED_ORG_FOUND "
            for one_linked_org in linked_organization_list:
                status += " [" + str(one_linked_org.we_vote_id) + "] "
            results['politician'] = politician
            results['politician_updated'] = True
            results['status'] = status
            return results
    except Exception as e:
        status += "ERROR_SEARCHING_FOR_ORGANIZATION: " + str(e) + " "
        results['politician_error'] = True
        results['status'] = status
        results['success'] = False
        return results
    # If still here, find an organization that matches the primary Twitter handle for this politician
    try:
        # Organization needed
        # See if we can find an organization that matches the primary Twitter handle for this politician
        #  that isn't already connected to another politician
        at_least_one_politician_twitter_handle_found = False
        queryset = Organization.objects.all()  # Cannot be 'readonly' because we save link to Politician below
        queryset = queryset.filter(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id=''))
        filters = []

        if positive_value_exists(politician.politician_twitter_handle):
            new_filter = Q(organization_twitter_handle__iexact=politician.politician_twitter_handle)
            filters.append(new_filter)
            at_least_one_politician_twitter_handle_found = True

        if positive_value_exists(politician.politician_twitter_handle2):
            new_filter = Q(organization_twitter_handle__iexact=politician.politician_twitter_handle2)
            filters.append(new_filter)
            at_least_one_politician_twitter_handle_found = True

        if positive_value_exists(politician.politician_twitter_handle3):
            new_filter = Q(organization_twitter_handle__iexact=politician.politician_twitter_handle3)
            filters.append(new_filter)
            at_least_one_politician_twitter_handle_found = True

        if positive_value_exists(politician.politician_twitter_handle4):
            new_filter = Q(organization_twitter_handle__iexact=politician.politician_twitter_handle4)
            filters.append(new_filter)
            at_least_one_politician_twitter_handle_found = True

        if positive_value_exists(politician.politician_twitter_handle5):
            new_filter = Q(organization_twitter_handle__iexact=politician.politician_twitter_handle5)
            filters.append(new_filter)
            at_least_one_politician_twitter_handle_found = True

        # Add the first query
        if len(filters):
            final_filters = filters.pop()
            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item
            queryset = queryset.filter(final_filters)

        if at_least_one_politician_twitter_handle_found:
            # Return the organization with the most Twitter followers if there are multiple choices
            queryset = queryset.order_by('-twitter_followers_count')
            existing_organization_list = list(queryset)
            if len(existing_organization_list) > 0:
                organization = existing_organization_list[0]
                status += "ORGANIZATION_FOUND_BY_TWITTER "
                organization.politician_we_vote_id = politician.we_vote_id
                if not positive_value_exists(organization.state_served_code) and \
                        positive_value_exists(politician.state_code):
                    organization.state_served_code = politician.state_code
                organization.save()

                if len(existing_organization_list) == 1:
                    politician.organization_manual_intervention_needed = False
                politician.organization_analysis_needed = False
                politician.organization_we_vote_id = organization.we_vote_id
                results['politician'] = politician
                results['politician_updated'] = True
                results['status'] = status
                return results
    except Exception as e:
        status += "FAILED_MATCHING_BY_TWITTER: " + str(e) + " "
        results['politician_error'] = True
        results['status'] = status
        results['success'] = False
        return results

    # If still here, find an organization with a name that matches this politician
    use_name_match = False
    if use_name_match:
        organization_possible_match_by_name_found = False
        try:
            queryset = Organization.objects.all()  # Cannot be 'readonly'
            queryset = queryset.filter(
                Q(politician_we_vote_id__isnull=True) |
                Q(politician_we_vote_id=''))
            queryset = queryset.filter(organization_name__iexact=politician.politician_name)
            if positive_value_exists(politician.state_code):
                # If the politician has a state code, only match to an existing organization by name if
                #  1) the organization doesn't have a state code, or
                #  2) the organization's state code matches the politician's state code, or
                politician_state_code_lower = politician.state_code.lower()
                queryset = queryset.filter(
                    Q(state_served_code__iexact=politician_state_code_lower) |
                    Q(state_served_code__iexact='') |
                    Q(state_served_code__isnull=True))
            queryset = queryset.order_by('-twitter_followers_count')
            organization_list = list(queryset)
            if len(organization_list) > 1:
                organization = organization_list[0]
                politician.politician_has_two_linked_organizations = True
                results['politician_has_two_linked_organizations'] = True
                organization_possible_match_by_name_found = True
            elif len(organization_list) > 0:
                organization = organization_list[0]
                organization_possible_match_by_name_found = True
            else:
                organization = None
            # Double-check that this organization doesn't have another politician that might be better fit
            if organization_possible_match_by_name_found:
                manual_intervention_needed = False
                other_politician_found_with_same_twitter_as_organization = False
                if positive_value_exists(organization.organization_twitter_handle):
                    try:
                        politician_queryset = Politician.objects.using('readonly').all()
                        politician_queryset = politician_queryset.exclude(we_vote_id=politician.we_vote_id)
                        politician_queryset = politician_queryset.filter(
                            Q(politician_twitter_handle__iexact=organization.organization_twitter_handle) |
                            Q(politician_twitter_handle2__iexact=organization.organization_twitter_handle) |
                            Q(politician_twitter_handle3__iexact=organization.organization_twitter_handle) |
                            Q(politician_twitter_handle4__iexact=organization.organization_twitter_handle) |
                            Q(politician_twitter_handle5__iexact=organization.organization_twitter_handle)
                        )
                        other_politician_found_with_same_twitter_as_organization = \
                            positive_value_exists(politician_queryset.count())
                    except Exception as e:
                        manual_intervention_needed = True
                        status += "FAILED_TO_CHECK_OTHER_POLITICIANS: " + str(e) + " "
                    if other_politician_found_with_same_twitter_as_organization or manual_intervention_needed:
                        status += "CANNOT_LINK_MATCHING_ORGANIZATION_OTHER_POLITICIAN_USING_SAME_TWITTER_HANDLE "
                        # We create a new organization, and then will merge the duplicate organizations in the future.
                        politician.organization_manual_intervention_needed = True
                        create_results = create_organization_from_politician(
                            changed_by_name=changed_by_name,
                            changed_by_voter_we_vote_id=changed_by_voter_we_vote_id,
                            politician=politician)
                        results['status'] = status
                        results['status'] += create_results['status']
                        if create_results['organization_found']:
                            politician.organization_analysis_needed = False
                            politician.organization_we_vote_id = create_results['organization'].we_vote_id
                            results['politician'] = politician
                            results['politician_updated'] = True
                        else:
                            results['organization_creation_error'] = True
                            results['politician'] = politician
                            results['politician_updated'] = False
                        return results
                # Double-check that this organization doesn't belong to a voter
                manual_intervention_needed = False
                organization_owned_by_voter = False
                try:
                    voter_queryset = Voter.objects.using('readonly').all()
                    voter_queryset = voter_queryset.filter(
                        linked_organization_we_vote_id=organization.we_vote_id)
                    organization_owned_by_voter = positive_value_exists(voter_queryset.count())
                except Exception as e:
                    manual_intervention_needed = True
                    status += "FAILED_TO_CHECK_VOTER: " + str(e) + " "
                if organization_owned_by_voter or manual_intervention_needed:
                    status += "CANNOT_LINK_MATCHING_ORGANIZATION_OTHER_POLITICIAN_IN_USE_BY_OTHER_VOTER "
                    politician.organization_manual_intervention_needed = True
                    results['politician'] = politician
                    results['politician_updated'] = True
                    results['status'] = status
                    return results
                # Now we are confident enough that this organization should be linked to this politician
                status += "ORGANIZATION_FOUND_BY_NAME "
                organization.politician_we_vote_id = politician.we_vote_id
                if not positive_value_exists(organization.state_served_code) and \
                        positive_value_exists(politician.state_code):
                    organization.state_served_code = politician.state_code
                organization.save()

                politician.organization_analysis_needed = False
                politician.organization_manual_intervention_needed = False
                politician.organization_we_vote_id = organization.we_vote_id
                results['politician'] = politician
                results['politician_updated'] = True
                results['status'] = status
                return results
        except Exception as e:
            status += "FAILED_MATCHING_BY_NAME: " + str(e) + " "
            results['politician_error'] = True
            results['status'] = status
            results['success'] = False
            return results

    # If we haven't exited yet, create an organization for this politician
    create_results = create_organization_from_politician(
        changed_by_name=changed_by_name,
        changed_by_voter_we_vote_id=changed_by_voter_we_vote_id,
        politician=politician)
    results['status'] = status
    results['status'] += create_results['status']
    if create_results['organization_found']:
        politician.organization_analysis_needed = False
        politician.organization_manual_intervention_needed = False
        politician.organization_we_vote_id = create_results['organization'].we_vote_id
        results['politician'] = politician
        results['politician_updated'] = True
    else:
        results['organization_creation_error'] = True
        results['politician'] = politician
        results['politician_updated'] = False
    return results


def match_politicians_to_organizations(
        changed_by_name='',
        changed_by_voter_we_vote_id='',
        number_of_politicians_to_match=100,
        state_code='',
):
    organization_might_be_needed_count = 0
    organizations_created_count = 0
    organization_creation_errors_count = 0
    politician_data_list = []
    politician_error_count = 0
    politician_has_two_linked_organizations = 0
    politician_has_two_possible_organizations = 0
    politician_list_count = 0
    politician_update_count = 0
    politician_we_vote_id_update_list = []
    politician_we_vote_id_update_failed_list = []
    politicians_analyzed_count = 0
    status = ''
    success = True
    update_list = []

    try:
        queryset = Politician.objects.all()
        queryset = queryset.filter(organization_analysis_needed=True)
        queryset = queryset.exclude(organization_manual_intervention_needed=True)
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        organization_might_be_needed_count = queryset.count()
        queryset = queryset.order_by('-politician_ultimate_election_date')
        politician_data_list = list(queryset[:number_of_politicians_to_match])
        politician_list_count = len(politician_data_list)
        for politician in politician_data_list:
            add_to_update_list = False
            results = match_politician_to_organization(
                changed_by_name=changed_by_name,
                changed_by_voter_we_vote_id=changed_by_voter_we_vote_id,
                politician=politician)
            if results['politician_updated']:
                politician = results['politician']
                add_to_update_list = True
                politician_we_vote_id_update_list.append(politician.we_vote_id)
            elif results['success']:
                status += "POLITICIAN_NOT_UPDATED1: " + politician.we_vote_id + " [" + results['status'] + "] "
                politician = results['politician']
                add_to_update_list = True
                politician_we_vote_id_update_failed_list.append(politician.we_vote_id)
            else:
                status += "POLITICIAN_NOT_UPDATED2: " + politician.we_vote_id + " [" + results['status'] + "] "
                politician_we_vote_id_update_failed_list.append(politician.we_vote_id)
            organizations_created_count += 1 if results['organization_created'] else 0
            organization_creation_errors_count += 1 if results['organization_creation_error'] else 0
            politician_error_count += 1 if results['politician_error'] else 0
            politician_has_two_linked_organizations += 1 if results['politician_has_two_linked_organizations'] else 0
            politician_has_two_possible_organizations += \
                1 if results['politician_has_two_possible_organizations'] else 0
            politician_update_count += 1 if results['politician_updated'] else 0
            politicians_analyzed_count += 1

            # If we need to do any politician or organization verification, we could do it here

            if add_to_update_list:
                update_list.append(politician)

        if politician_update_count > 0:
            try:
                Politician.objects.bulk_update(update_list, [
                    'organization_analysis_needed', 'organization_manual_intervention_needed',
                    'organization_we_vote_id', 'politician_has_two_linked_organizations'])
            except Exception as e:
                status += "FAILED_TO_BULK_UPDATE_POLITICIANS: " + str(e) + " "
                politician_update_count = 0

    except Exception as e:
        status += "GENERAL_ERROR: " + str(e) + " "
        success = False

    results = {
        'organizations_created_count': organizations_created_count,
        'organization_creation_errors_count': organization_creation_errors_count,
        'organization_might_be_needed_count': organization_might_be_needed_count,
        'politician_error_count': politician_error_count,
        'politician_has_two_linked_organizations': politician_has_two_linked_organizations,
        'politician_has_two_possible_organizations': politician_has_two_possible_organizations,
        'politician_list': politician_data_list,
        'politician_list_count': politician_list_count,
        'politician_update_count': politician_update_count,
        'politician_we_vote_id_update_list': politician_we_vote_id_update_list,
        'politician_we_vote_id_update_failed_list': politician_we_vote_id_update_failed_list,
        'politicians_analyzed': politicians_analyzed_count,
        'status': status,
        'success': success,
    }
    return results


def merge_if_duplicate_politicians(politician1, politician2, conflict_values):
    """
    See also figure_out_politician_conflict_values
    :param politician1:
    :param politician2:
    :param conflict_values:
    :return:
    """
    success = True
    status = "MERGE_IF_DUPLICATE_POLITICIANS "
    politicians_merged = False
    decisions_required = False
    politician1_we_vote_id = politician1.we_vote_id
    politician2_we_vote_id = politician2.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    clear_these_attributes_from_politician2 = []
    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        if attribute == "ballotpedia_id" \
                or attribute == "other_source_photo_url" \
                or attribute == "seo_friendly_path" \
                or attribute == "we_vote_hosted_profile_image_url_large" \
                or attribute == "we_vote_hosted_profile_image_url_medium" \
                or attribute == "we_vote_hosted_profile_image_url_tiny":
            if positive_value_exists(getattr(politician1, attribute)):
                # We can proceed because politician1 has a valid attribute, so we can default to choosing that one
                if attribute in POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_politician2.append(attribute)
            elif positive_value_exists(getattr(politician2, attribute)):
                # If we are here, politician1 does NOT have a valid attribute, but politician2 does
                merge_choices[attribute] = getattr(politician2, attribute)
                if attribute in POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_politician2.append(attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                if attribute == "politician_name" \
                        or attribute == "first_name" \
                        or attribute == "middle_name" \
                        or attribute == "last_name":
                    # If the lower case versions of the name attribute are identical, choose the name
                    #  that has upper and lower case letters, and do not require a decision
                    politician1_attribute_value = getattr(politician1, attribute)
                    try:
                        politician1_attribute_value_lower_case = politician1_attribute_value.lower()
                    except Exception:
                        politician1_attribute_value_lower_case = None
                    politician2_attribute_value = getattr(politician2, attribute)
                    try:
                        politician2_attribute_value_lower_case = politician2_attribute_value.lower()
                    except Exception:
                        politician2_attribute_value_lower_case = None
                    if positive_value_exists(politician1_attribute_value_lower_case) \
                            and politician1_attribute_value_lower_case == politician2_attribute_value_lower_case:
                        # Give preference to value with both upper and lower case letters (as opposed to all uppercase)
                        if any(char.isupper() for char in politician1_attribute_value) \
                                and any(char.islower() for char in politician1_attribute_value):
                            merge_choices[attribute] = getattr(politician1, attribute)
                        else:
                            merge_choices[attribute] = getattr(politician2, attribute)
                    else:
                        decisions_required = True
                        break
                else:
                    decisions_required = True
                    break
            elif conflict_value == "POLITICIAN2":
                merge_choices[attribute] = getattr(politician2, attribute)
                if attribute in POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_politician2.append(attribute)

    if not decisions_required:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = merge_these_two_politicians(
            politician1_we_vote_id,
            politician2_we_vote_id,
            merge_choices,
            clear_these_attributes_from_politician2
        )

        if not merge_results['success']:
            success = False
            status += merge_results['status']
        elif merge_results['politicians_merged']:
            politicians_merged = True
        else:
            status += "NOT_MERGED "

    results = {
        'success':              success,
        'status':               status,
        'politicians_merged':   politicians_merged,
        'decisions_required':   decisions_required,
        'politician':           politician1,
    }
    return results


def merge_these_two_politicians(
        politician1_we_vote_id,
        politician2_we_vote_id,
        admin_merge_choices={},
        clear_these_attributes_from_politician2=[]):
    """
    Process the merging of two politicians
    :param politician1_we_vote_id:
    :param politician2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :param clear_these_attributes_from_politician2:
    :return:
    """
    status = ""
    politician_manager = PoliticianManager()

    # Politician 1 is the one we keep, and Politician 2 is the one we will merge into Politician 1
    politician1_results = politician_manager.retrieve_politician(politician_we_vote_id=politician1_we_vote_id)
    if politician1_results['politician_found']:
        politician1 = politician1_results['politician']
        politician1_id = politician1.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_POLITICIANS-COULD_NOT_RETRIEVE_POLITICIAN1 ",
            'politicians_merged': False,
            'politician': None,
        }
        return results

    politician2_results = politician_manager.retrieve_politician(politician_we_vote_id=politician2_we_vote_id)
    if politician2_results['politician_found']:
        politician2 = politician2_results['politician']
        politician2_id = politician2.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_POLITICIANS-COULD_NOT_RETRIEVE_POLITICIAN2 ",
            'politicians_merged': False,
            'politician': None,
        }
        return results

    # Merge attribute values chosen by the admin
    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        try:
            if attribute in admin_merge_choices:
                setattr(politician1, attribute, admin_merge_choices[attribute])
        except Exception as e:
            # Don't completely fail if in attribute can't be saved.
            status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "

    # Preserve unique facebook_url -> facebook_url3
    from representative.controllers import add_value_to_next_representative_spot
    if positive_value_exists(politician2.facebook_url):
        results = add_value_to_next_representative_spot(
            field_name_base='facebook_url',
            new_value_to_add=politician2.facebook_url,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.facebook_url2):
        results = add_value_to_next_representative_spot(
            field_name_base='facebook_url',
            new_value_to_add=politician2.facebook_url2,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.facebook_url3):
        results = add_value_to_next_representative_spot(
            field_name_base='facebook_url',
            new_value_to_add=politician2.facebook_url3,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']

    # Preserve unique politician_name & google_civic_candidate_name, _name2, _name3
    if politician2.politician_name != politician1.politician_name:
        results = add_name_to_next_spot(politician1, politician2.politician_name)
        if results['success'] and results['values_changed']:
            politician1 = results['candidate_or_politician']
    if positive_value_exists(politician2.google_civic_candidate_name):
        results = add_name_to_next_spot(politician1, politician2.google_civic_candidate_name)
        if results['success'] and results['values_changed']:
            politician1 = results['candidate_or_politician']
    if positive_value_exists(politician2.google_civic_candidate_name2):
        results = add_name_to_next_spot(politician1, politician2.google_civic_candidate_name2)
        if results['success'] and results['values_changed']:
            politician1 = results['candidate_or_politician']
    if positive_value_exists(politician2.google_civic_candidate_name3):
        results = add_name_to_next_spot(politician1, politician2.google_civic_candidate_name3)
        if results['success'] and results['values_changed']:
            politician1 = results['candidate_or_politician']

    # Preserve unique politician_email -> politician_email3
    # TEMP UNTIL WE DEPRECATE politician_email_address
    if positive_value_exists(politician2.politician_email_address):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_email',
            new_value_to_add=politician2.politician_email_address,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_email):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_email',
            new_value_to_add=politician2.politician_email,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_email2):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_email',
            new_value_to_add=politician2.politician_email2,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_email3):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_email',
            new_value_to_add=politician2.politician_email3,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']

    # Preserve unique politician_phone_number -> politician_phone_number3
    if positive_value_exists(politician2.politician_phone_number):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_phone_number',
            new_value_to_add=politician2.politician_phone_number,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_phone_number2):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_phone_number',
            new_value_to_add=politician2.politician_phone_number2,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_phone_number3):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_phone_number',
            new_value_to_add=politician2.politician_phone_number3,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']

    # Preserve unique politician_twitter_handle -> politician_twitter_handle5
    if positive_value_exists(politician2.politician_twitter_handle):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1, politician2.politician_twitter_handle)
        if twitter_results['success']:
            politician1 = twitter_results['politician']
    if positive_value_exists(politician2.politician_twitter_handle2):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1, politician2.politician_twitter_handle2)
        if twitter_results['success']:
            politician1 = twitter_results['politician']
    if positive_value_exists(politician2.politician_twitter_handle3):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1, politician2.politician_twitter_handle3)
        if twitter_results['success']:
            politician1 = twitter_results['politician']
    if positive_value_exists(politician2.politician_twitter_handle4):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1, politician2.politician_twitter_handle4)
        if twitter_results['success']:
            politician1 = twitter_results['politician']
    if positive_value_exists(politician2.politician_twitter_handle5):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1, politician2.politician_twitter_handle5)
        if twitter_results['success']:
            politician1 = twitter_results['politician']

    # Preserve unique politician_url -> politician_url5
    if positive_value_exists(politician2.politician_url):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_url',
            new_value_to_add=politician2.politician_url,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_url2):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_url',
            new_value_to_add=politician2.politician_url2,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_url3):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_url',
            new_value_to_add=politician2.politician_url3,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_url4):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_url',
            new_value_to_add=politician2.politician_url4,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']
    if positive_value_exists(politician2.politician_url5):
        results = add_value_to_next_representative_spot(
            field_name_base='politician_url',
            new_value_to_add=politician2.politician_url5,
            representative=politician1,
        )
        if results['success'] and results['values_changed']:
            politician1 = results['representative']
        if not results['success']:
            status += results['status']

    # Preserve the shortcuts used by politician2
    try:
        shortcuts_moved = PoliticianSEOFriendlyPath.objects \
            .filter(politician_we_vote_id=politician2_we_vote_id) \
            .update(politician_we_vote_id=politician1_we_vote_id)
        status += "SHORTCUTS_MOVED: " + str(shortcuts_moved) + " "
    except Exception as e:
        status += "MERGE_TWO_POLITICIANS-COULD_NOT_MOVE_SHORTCUTS: " + str(e) + " "

    # Update candidates to new politician ids
    candidate_results = move_candidates_to_another_politician(
        from_politician_id=politician2_id,
        from_politician_we_vote_id=politician2_we_vote_id,
        to_politician_id=politician1_id,
        to_politician_we_vote_id=politician1_we_vote_id)
    if not candidate_results['success']:
        status += candidate_results['status']
        status += "COULD_NOT_MOVE_CANDIDATES_TO_POLITICIAN1 "
        results = {
            'success': False,
            'status': status,
            'politicians_merged': False,
            'politician': None,
        }
        return results

    # Update positions to new politician ids
    positions_results = move_positions_to_another_politician(
        from_politician_id=politician2_id,
        from_politician_we_vote_id=politician2_we_vote_id,
        to_politician_id=politician1_id,
        to_politician_we_vote_id=politician1_we_vote_id)
    if not positions_results['success']:
        status += positions_results['status']
        status += "MERGE_THESE_TWO_POLITICIANS-COULD_NOT_MOVE_POSITIONS_TO_POLITICIAN1 "
        results = {
            'success': False,
            'status': status,
            'politicians_merged': False,
            'politician': None,
        }
        return results

    # Update CampaignX entries to new politician_we_vote_id
    from campaign.controllers import move_campaignx_to_another_politician
    results = move_campaignx_to_another_politician(
        from_politician_we_vote_id=politician2_we_vote_id,
        to_politician_we_vote_id=politician1_we_vote_id)
    if not results['success']:
        status += results['status']
        status += "COULD_NOT_MOVE_CAMPAIGNX_TO_POLITICIAN1 "
        results = {
            'success': False,
            'status': status,
            'politicians_merged': False,
            'politician': None,
        }
        return results

    # Update any CampaignXPolitician entries to new politician_we_vote_id
    from campaign.models import CampaignXPolitician
    campaign_politicians_moved = CampaignXPolitician.objects \
        .filter(politician_we_vote_id=politician2_we_vote_id) \
        .update(politician_we_vote_id=politician1_we_vote_id)
    status += "CAMPAIGNX_POLITICIANS_MOVED: " + str(campaign_politicians_moved) + " "

    # Update Representatives to new politician ids
    representative_results = move_representatives_to_another_politician(
        from_politician_id=politician2_id,
        from_politician_we_vote_id=politician2_we_vote_id,
        to_politician_id=politician1_id,
        to_politician_we_vote_id=politician1_we_vote_id)
    if not representative_results['success']:
        status += representative_results['status']
        status += "COULD_NOT_MOVE_REPRESENTATIVES_TO_POLITICIAN1 "
        results = {
            'success': False,
            'status': status,
            'politicians_merged': False,
            'politician': None,
        }
        return results

    # Update any WeVoteImage entries to new politician_we_vote_id
    from image.models import WeVoteImage
    images_moved = WeVoteImage.objects \
        .filter(politician_we_vote_id=politician2_we_vote_id) \
        .update(politician_we_vote_id=politician1_we_vote_id)
    status += "WE_VOTE_IMAGE_ENTRIES_MOVED: " + str(images_moved) + " "

    # Clear 'unique=True' fields in politician2, which need to be Null before politician1 can be saved
    #  with updated values
    politician2_updated = False
    for attribute in clear_these_attributes_from_politician2:
        setattr(politician2, attribute, None)
        politician2_updated = True
    if politician2_updated:
        politician2.save()

    # Note: wait to wrap in try/except block
    politician1.save()
    # 2021-10-16 Uses image data from master table which we aren't updating with the merge yet
    # refresh_politician_data_from_master_tables(politician1.we_vote_id)

    # Remove politician 2
    politician2.delete()

    results = {
        'success': True,
        'status': status,
        'politicians_merged': True,
        'politician': politician1,
    }
    return results


def politician_save_photo_from_file_reader(
        politician_we_vote_id='',
        politician_photo_binary_file=None,
        politician_photo_from_file_reader=None):
    image_data_found = False
    python_image_library_image = None
    status = ""
    success = True
    we_vote_hosted_politician_photo_original_url = ''

    if not positive_value_exists(politician_we_vote_id):
        status += "MISSING_POLITICIAN_WE_VOTE_ID "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_politician_photo_original_url': we_vote_hosted_politician_photo_original_url,
        }
        return results

    if not positive_value_exists(politician_photo_from_file_reader) \
            and not positive_value_exists(politician_photo_binary_file):
        status += "MISSING_POLITICIAN_PHOTO_FROM_FILE_READER "
        results = {
            'status': status,
            'success': success,
            'we_vote_hosted_politician_photo_original_url': we_vote_hosted_politician_photo_original_url,
        }
        return results

    if not politician_photo_binary_file:
        try:
            img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)",
                                politician_photo_from_file_reader).groupdict()
            if img_dict['encoding'] == 'base64':
                politician_photo_binary_file = img_dict['data']
            else:
                status += "INCOMING_POLITICIAN_UPLOADED_PHOTO-BASE64_NOT_FOUND "
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_BINARY_DATA_FROM_INCOMING_POLITICIAN_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if politician_photo_binary_file:
        try:
            byte_data = base64.b64decode(politician_photo_binary_file)
            image_data = BytesIO(byte_data)
            original_image = Image.open(image_data)
            format_to_cache = original_image.format
            python_image_library_image = ImageOps.exif_transpose(original_image)
            python_image_library_image.thumbnail(
                (PROFILE_IMAGE_ORIGINAL_MAX_WIDTH, PROFILE_IMAGE_ORIGINAL_MAX_HEIGHT), Image.Resampling.LANCZOS)
            python_image_library_image.format = format_to_cache
            image_data_found = True
        except Exception as e:
            status += 'PROBLEM_EXTRACTING_POLITICIAN_PHOTO_FROM_BINARY_DATA: {error} [type: {error_type}] ' \
                      ''.format(error=e, error_type=type(e))

    if image_data_found:
        cache_results = cache_image_object_to_aws(
            python_image_library_image=python_image_library_image,
            politician_we_vote_id=politician_we_vote_id,
            kind_of_image_politician_uploaded_profile=True,
            kind_of_image_original=True)
        status += cache_results['status']
        if cache_results['success']:
            cached_master_we_vote_image = cache_results['we_vote_image']
            try:
                we_vote_hosted_politician_photo_original_url = cached_master_we_vote_image.we_vote_image_url
            except Exception as e:
                status += "FAILED_TO_CACHE_POLITICIAN_IMAGE: " + str(e) + ' '
                success = False
        else:
            success = False
    results = {
        'status':                   status,
        'success':                  success,
        'we_vote_hosted_politician_photo_original_url': we_vote_hosted_politician_photo_original_url,
    }
    return results


def politician_retrieve_for_api(  # politicianRetrieve & politicianRetrieveAsOwner (No CDN)
        request=None,
        voter_device_id='',
        politician_we_vote_id='',
        seo_friendly_path='',
        as_owner=False,
        hostname=''):
    status = ''
    success = True

    politician_found = False
    politician_owner_list = []
    save_politician = False
    seo_friendly_path_list = []
    voter_is_politician_owner = False
    voter_signed_in_with_email = False
    voter_we_vote_id = ''

    politician_manager = PoliticianManager()
    politician = None
    politician_retrieve_error_dict = copy.deepcopy(POLITICIAN_RETRIEVE_ERROR_DICT)
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
    if positive_value_exists(as_owner):
        if not positive_value_exists(voter_we_vote_id):
            status += "VALID_VOTER_ID_MISSING "
            success = False
        if success:
            results = politician_manager.retrieve_politician(
                politician_we_vote_id=politician_we_vote_id,
                seo_friendly_path=seo_friendly_path,
                voter_we_vote_id=voter_we_vote_id,
                read_only=False,
            )
            if not results['success']:
                status += "POLITICIAN_RETRIEVE_ERROR1: "
                success = False
            politician_found = results['politician_found']
            status += results['status']
            voter_is_politician_owner = True
            politician = results['politician']
            # politician_owner_list = results['politician_owner_list']
            if voter_is_politician_owner and not politician.is_claimed_profile:
                politician.is_claimed_profile = True
                politician.is_claimed_profile_date = datetime.now()
                save_politician = True
    else:
        results = politician_manager.retrieve_politician(
            politician_we_vote_id=politician_we_vote_id,
            seo_friendly_path=seo_friendly_path,
            read_only=True,
        )
        if not results['success']:
            status += "POLITICIAN_RETRIEVE_ERROR2: "
            success = False
        politician_found = results['politician_found']
        politician = results['politician']
        # politician_owner_list = results['politician_owner_list']
        voter_is_politician_owner = False
        status += results['status']
    if not success or not politician_found:
        results = politician_retrieve_error_dict
        results['status'] = status
        results['voter_signed_in_with_email'] = voter_signed_in_with_email
        return results

    if not positive_value_exists(politician.linked_campaignx_we_vote_id):
        results = generate_campaignx_for_politician(politician=politician, save_individual_politician=True)
        if results['success'] and results['campaignx_created']:
            politician = results['politician']

    # ########################################################################
    # Get organization -- the Endorser object associated with this politician
    organization_we_vote_id = ''
    organization_manager = OrganizationManager()
    organization_results = organization_manager.retrieve_organization(
        politician_we_vote_id=politician.we_vote_id,
        read_only=True)
    if organization_results['organization_found']:
        organization = organization_results['organization']
        organization_we_vote_id = organization.we_vote_id
    else:
        status += "ORGANIZATION_NOT_FOUND_FOR_POLITICIAN "

    # Get voter_politician_supporter
    voter_politician_supporter = {}

    # Get politician news items / updates
    politician_news_item_list = []
    # news_item_list_results = politician_manager.retrieve_politician_news_item_list(
    #     politician_we_vote_id=politician.we_vote_id,
    #     read_only=True,
    #     voter_is_politician_owner=voter_is_politician_owner)
    # if news_item_list_results['politician_news_item_list_found']:
    #     news_item_list = news_item_list_results['politician_news_item_list']
    #     for news_item in news_item_list:
    #         date_last_changed_string = ''
    #         date_posted_string = ''
    #         date_sent_to_email_string = ''
    #         try:
    #             date_last_changed_string = news_item.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
    #             date_posted_string = news_item.date_posted.strftime('%Y-%m-%d %H:%M:%S')
    #             if positive_value_exists(news_item.date_sent_to_email):
    #                 date_sent_to_email_string = news_item.date_sent_to_email.strftime('%Y-%m-%d %H:%M:%S')
    #         except Exception as e:
    #             status += "DATE_CONVERSION_ERROR: " + str(e) + " "
    #         one_news_item_dict = {
    #             'politician_news_subject': news_item.politician_news_subject,
    #             'politician_news_text': news_item.politician_news_text,
    #             'politician_news_item_we_vote_id': news_item.we_vote_id,
    #             'politician_we_vote_id': news_item.politician_we_vote_id,
    #             'date_last_changed': date_last_changed_string,
    #             'date_posted': date_posted_string,
    #             'date_sent_to_email': date_sent_to_email_string,
    #             'in_draft_mode': news_item.in_draft_mode,
    #             'organization_we_vote_id': news_item.organization_we_vote_id,
    #             'speaker_name': news_item.speaker_name,
    #             'visible_to_public': news_item.visible_to_public,
    #             'voter_we_vote_id': news_item.voter_we_vote_id,
    #             'we_vote_hosted_profile_image_url_medium': news_item.we_vote_hosted_profile_image_url_medium,
    #             'we_vote_hosted_profile_image_url_tiny': news_item.we_vote_hosted_profile_image_url_tiny,
    #         }
    #         politician_news_item_list.append(one_news_item_dict)

    # from organization.controllers import site_configuration_retrieve_for_api
    # site_results = site_configuration_retrieve_for_api(hostname)
    # site_owner_organization_we_vote_id = site_results['organization_we_vote_id']
    #
    # if positive_value_exists(site_owner_organization_we_vote_id):
    #     try:
    #         visible_on_this_site_politician_we_vote_id_list = \
    #             politician_manager.retrieve_visible_on_this_site_politician_simple_list(
    #                 site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
    #         if politician.we_vote_id in visible_on_this_site_politician_we_vote_id_list:
    #             politician.visible_on_this_site = True
    #         else:
    #             politician.visible_on_this_site = False
    #     except Exception as e:
    #         success = False
    #         status += "RETRIEVE_POLITICIAN_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "
    # else:
    #     politician.visible_on_this_site = True

    voter_can_send_updates_politician_we_vote_ids = []
    # voter_can_send_updates_politician_we_vote_ids = \
    #     politician_manager.retrieve_voter_can_send_updates_politician_we_vote_ids(
    #         voter_we_vote_id=voter_we_vote_id,
    #     )

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_candidate_list(
        politician_we_vote_id_list=[politician.we_vote_id],
        read_only=True,
    )
    status += results['status']
    politician_candidate_list = results['candidate_list']
    politician_candidate_list_exists = results['candidate_list_found']

    # Retrieve most recent opponents of this candidate (showing this on politician page helps with SEO)
    politician_ultimate_election_date = 0
    most_recent_candidate_we_vote_id = None
    opponent_candidate_list = []
    for one_candidate in politician_candidate_list:
        if one_candidate and one_candidate.candidate_ultimate_election_date \
                and one_candidate.candidate_ultimate_election_date > politician_ultimate_election_date:
            politician_ultimate_election_date = one_candidate.candidate_ultimate_election_date
            most_recent_candidate_we_vote_id = one_candidate.we_vote_id
    if positive_value_exists(most_recent_candidate_we_vote_id):
        opponent_candidate_we_vote_id_list = []
        from candidate.models import CandidateToOfficeLink
        try:
            link_queryset = CandidateToOfficeLink.objects.all()
            link_queryset = link_queryset.filter(candidate_we_vote_id=most_recent_candidate_we_vote_id)
            link_queryset = link_queryset.values_list('contest_office_we_vote_id', flat=True).distinct()
            contest_office_we_vote_id_list = list(link_queryset)
        except Exception as e:
            contest_office_we_vote_id_list = []
            status += "PROBLEM_RETRIEVING_OPPONENT_OFFICE_LIST: " + str(e) + " "
        if len(contest_office_we_vote_id_list) > 0:
            try:
                link_queryset = CandidateToOfficeLink.objects.all()
                link_queryset = link_queryset.filter(contest_office_we_vote_id__in=contest_office_we_vote_id_list)
                link_queryset = link_queryset.values_list('candidate_we_vote_id', flat=True).distinct()
                opponent_candidate_we_vote_id_list = list(link_queryset)
            except Exception as e:
                status += "PROBLEM_RETRIEVING_OPPONENT_CANDIDATE_LIST: " + str(e) + " "
        if len(opponent_candidate_we_vote_id_list) > 0:
            candidate_list_manager = CandidateListManager()
            results = candidate_list_manager.retrieve_candidate_list(
                candidate_we_vote_id_list=opponent_candidate_we_vote_id_list,
                read_only=True)
            if results['candidate_list_found']:
                opponent_candidate_list_unfiltered = results['candidate_list']
                latest_year = 0
                candidates_by_year_dict = {}
                for one_candidate in opponent_candidate_list_unfiltered:
                    if not positive_value_exists(one_candidate.candidate_year):
                        # Skip candidate if it doesn't have a year'
                        continue
                    if politician.we_vote_id == one_candidate.politician_we_vote_id:
                        # Do not include this politician's candidate entries
                        continue
                    if one_candidate.candidate_year > latest_year:
                        latest_year = one_candidate.candidate_year
                    if one_candidate.candidate_year not in candidates_by_year_dict:
                        candidates_by_year_dict[one_candidate.candidate_year] = []
                    candidates_by_year_dict[one_candidate.candidate_year].append(one_candidate)
                if positive_value_exists(latest_year) and latest_year in candidates_by_year_dict:
                    opponent_candidate_list = candidates_by_year_dict[latest_year]
    opponent_candidate_list_exists = False
    if len(opponent_candidate_list) > 0:
        # We match the output from candidatesRetrieve & candidateRetrieve API
        results = generate_candidate_dict_list_from_candidate_object_list(
            candidate_object_list=opponent_candidate_list)
        opponent_candidate_dict_list = results['candidate_dict_list']
        opponent_candidate_list_exists = len(opponent_candidate_dict_list) > 0
    else:
        opponent_candidate_dict_list = []

    # We match the output from candidatesRetrieve & candidateRetrieve API
    if len(politician_candidate_list) > 0:
        results = generate_candidate_dict_list_from_candidate_object_list(
            candidate_object_list=politician_candidate_list)
        politician_candidate_dict_list = results['candidate_dict_list']
    else:
        politician_candidate_dict_list = []

    representative_manager = RepresentativeManager()
    results = representative_manager.retrieve_representative_list(
        politician_we_vote_id_list=[politician.we_vote_id],
        read_only=True,
    )
    status += results['status']
    politician_representative_list = results['representative_list']
    politician_representative_list_exists = results['representative_list_found']
    if len(politician_representative_list) > 0:
        # We match the output from representativesRetrieve & representativeRetrieve API
        results = generate_representative_dict_list_from_representative_object_list(
            representative_object_list=politician_representative_list)
        politician_representative_dict_list = results['representative_dict_list']
    else:
        politician_representative_dict_list = []
    office_held_dict_list = []
    office_held_dict_list_found = False
    office_held_we_vote_id_list = []
    for one_representative in politician_representative_list:
        if positive_value_exists(one_representative.office_held_we_vote_id) \
                and one_representative.office_held_we_vote_id not in office_held_we_vote_id_list:
            office_held_we_vote_id_list.append(one_representative.office_held_we_vote_id)
    if len(office_held_we_vote_id_list) > 0:
        results = generate_office_held_dict_list_from_office_held_we_vote_id_list(
            office_held_we_vote_id_list=office_held_we_vote_id_list)
        status += results['status']
        office_held_dict_list = results['office_held_dict_list']
        if results['success'] and len(office_held_dict_list) > 0:
            office_held_dict_list_found = True

    # We need to know all the politicians this voter can vote for, so we can figure out
    #  if the voter can vote for any politicians in the election
    if positive_value_exists(as_owner):
        from ballot.controllers import what_voter_can_vote_for
        results = what_voter_can_vote_for(request=request, voter_device_id=voter_device_id)
        voter_can_vote_for_politician_we_vote_ids = results['voter_can_vote_for_politician_we_vote_ids']
    else:
        voter_can_vote_for_politician_we_vote_ids = []

    # supporter_results = politician_manager.retrieve_politician_supporter(
    #     politician_we_vote_id=politician.we_vote_id,
    #     voter_we_vote_id=voter_we_vote_id,
    #     read_only=True)
    # if supporter_results['success'] and supporter_results['politician_supporter_found']:
    #     politician_supporter = supporter_results['politician_supporter']
    #     chip_in_total = 'none'
    #     date_last_changed_string = ''
    #     date_supported_string = ''
    #     try:
    #         date_last_changed_string = politician_supporter.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
    #         date_supported_string = politician_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
    #     except Exception as e:
    #         status += "DATE_CONVERSION_ERROR: " + str(e) + " "
    #     try:
    #         from stripe_donations.models import StripeManager
    #         chip_in_total = StripeManager.retrieve_chip_in_total(voter_we_vote_id, politician.we_vote_id)
    #     except Exception as e:
    #         status += "RETRIEVE_CHIP_IN_TOTAL_ERROR: " + str(e) + " "
    #
    #     voter_politician_supporter_dict = {
    #         'politician_supported':           politician_supporter.politician_supported,
    #         'politician_we_vote_id':         politician_supporter.politician_we_vote_id,
    #         'chip_in_total':                chip_in_total,
    #         'date_last_changed':            date_last_changed_string,
    #         'date_supported':               date_supported_string,
    #         'id':                           politician_supporter.id,
    #         'organization_we_vote_id':      politician_supporter.organization_we_vote_id,
    #         'supporter_endorsement':        politician_supporter.supporter_endorsement,
    #         'supporter_name':               politician_supporter.supporter_name,
    #         'visible_to_public':            politician_supporter.visible_to_public,
    #         'voter_we_vote_id':             politician_supporter.voter_we_vote_id,
    #         'voter_signed_in_with_email':   voter_signed_in_with_email,
    #         'we_vote_hosted_profile_image_url_medium': politician_supporter.we_vote_hosted_profile_image_url_medium,
    #         'we_vote_hosted_profile_image_url_tiny': politician_supporter.we_vote_hosted_profile_image_url_tiny,
    #     }
    # else:
    #     voter_politician_supporter_dict = {}

    # Get most recent supporters
    latest_politician_supporter_list = []
    # supporter_list_results = politician_manager.retrieve_politician_supporter_list(
    #     politician_we_vote_id=politician.we_vote_id,
    #     limit=7,
    #     read_only=True,
    #     require_visible_to_public=True)
    # if supporter_list_results['supporter_list_found']:
    #     supporter_list = supporter_list_results['supporter_list']
    #     for politician_supporter in supporter_list:
    #         date_supported_string = ''
    #         try:
    #             date_supported_string = politician_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
    #         except Exception as e:
    #             status += "DATE_CONVERSION_ERROR: " + str(e) + " "
    #         one_supporter_dict = {
    #             'id': politician_supporter.id,
    #             'politician_supported': politician_supporter.politician_supported,
    #             'politician_we_vote_id': politician_supporter.politician_we_vote_id,
    #             'date_supported': date_supported_string,
    #             'organization_we_vote_id': politician_supporter.organization_we_vote_id,
    #             'supporter_endorsement': politician_supporter.supporter_endorsement,
    #             'supporter_name': politician_supporter.supporter_name,
    #             'voter_we_vote_id': politician_supporter.voter_we_vote_id,
    #           'we_vote_hosted_profile_image_url_medium': politician_supporter.we_vote_hosted_profile_image_url_medium,
    #             'we_vote_hosted_profile_image_url_tiny': politician_supporter.we_vote_hosted_profile_image_url_tiny,
    #         }
    #         latest_politician_supporter_list.append(one_supporter_dict)

    # Get most recent supporter_endorsements
    latest_politician_supporter_endorsement_list = []
    # supporter_list_results = politician_manager.retrieve_politician_supporter_list(
    #     politician_we_vote_id=politician.we_vote_id,
    #     limit=10,
    #     require_supporter_endorsement=True,
    #     read_only=True)
    # if supporter_list_results['supporter_list_found']:
    #     supporter_list = supporter_list_results['supporter_list']
    #     for politician_supporter in supporter_list:
    #         date_supported_string = ''
    #         try:
    #             date_supported_string = politician_supporter.date_supported.strftime('%Y-%m-%d %H:%M:%S')
    #         except Exception as e:
    #             status += "DATE_CONVERSION_ERROR: " + str(e) + " "
    #         one_supporter_dict = {
    #             'id': politician_supporter.id,
    #             'politician_supported': politician_supporter.politician_supported,
    #             'politician_we_vote_id': politician_supporter.politician_we_vote_id,
    #             'date_supported': date_supported_string,
    #             'organization_we_vote_id': politician_supporter.organization_we_vote_id,
    #             'supporter_endorsement': politician_supporter.supporter_endorsement,
    #             'supporter_name': politician_supporter.supporter_name,
    #             'voter_we_vote_id': politician_supporter.voter_we_vote_id,
    #           'we_vote_hosted_profile_image_url_medium': politician_supporter.we_vote_hosted_profile_image_url_medium,
    #             'we_vote_hosted_profile_image_url_tiny': politician_supporter.we_vote_hosted_profile_image_url_tiny,
    #         }
    #         latest_politician_supporter_endorsement_list.append(one_supporter_dict)

    # Find alternate URLs from PoliticianSEOFriendlyPath
    queryset = PoliticianSEOFriendlyPath.objects.using('readonly').all()
    queryset = queryset.filter(politician_we_vote_id=politician.we_vote_id)
    seo_friendly_path_object_list = list(queryset)
    for one_seo_friendly_path_object in seo_friendly_path_object_list:
        if one_seo_friendly_path_object.final_pathname_string and \
                one_seo_friendly_path_object.final_pathname_string not in seo_friendly_path_list:
            seo_friendly_path_list.append(one_seo_friendly_path_object.final_pathname_string)

    if save_politician:
        politician.save()

    generate_results = generate_politician_dict_from_politician_object(politician=politician)
    results = generate_results['politician_dict']
    results.update({
        'candidate_list':                   politician_candidate_dict_list,
        'candidate_list_exists':            politician_candidate_list_exists,
        'office_held_list':                 office_held_dict_list,
        'office_held_list_exists':          office_held_dict_list_found,
        'opponent_candidate_list':          opponent_candidate_dict_list,
        'opponent_candidate_list_exists':   opponent_candidate_list_exists,
        'organization_we_vote_id':          organization_we_vote_id,
        'politician_news_item_list':        politician_news_item_list,
        'politician_owner_list':            politician_owner_list,
        # 'latest_politician_supporter_endorsement_list':  latest_politician_supporter_endorsement_list,
        # 'latest_politician_supporter_list':  latest_politician_supporter_list,
        'politician_ultimate_election_date': politician_ultimate_election_date,
        'representative_list':              politician_representative_dict_list,
        'representative_list_exists':       politician_representative_list_exists,
        'seo_friendly_path_list':           seo_friendly_path_list,
        'status':                           status,
        'success':                          success,
        # 'supporters_count_next_goal':       supporters_count_next_goal,
        # 'voter_politician_supporter':        voter_politician_supporter_dict,
        'voter_can_send_updates_to_politician':
            politician.we_vote_id in voter_can_send_updates_politician_we_vote_ids,
        'voter_can_vote_for_politician_we_vote_ids': voter_can_vote_for_politician_we_vote_ids,
        'voter_is_politician_owner':        voter_is_politician_owner,
        'voter_signed_in_with_email':       voter_signed_in_with_email,
    })
    return results


def politician_save_for_api(  # politicianSave
        ballot_guide_official_statement='',
        ballot_guide_official_statement_changed='',
        campaign_website='',
        campaign_website_changed=False,
        political_party='',
        political_party_changed=False,
        politician_name='',
        politician_name_changed=False,
        politician_photo_from_file_reader='',
        politician_photo_changed=False,
        politician_photo_delete=False,
        politician_photo_delete_changed=False,
        politician_we_vote_id='',
        profile_image_type_currently_active=False,
        profile_image_type_currently_active_changed=False,
        request=None,
        state_code='',
        state_code_changed=False,
        voter_device_id=''):
    status = ''
    success = True
    politician_retrieve_error_dict = copy.deepcopy(POLITICIAN_RETRIEVE_ERROR_DICT)

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_signed_in_with_email = voter.signed_in_with_email()
        voter_we_vote_id = voter.we_vote_id
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id
    else:
        status += "VALID_VOTER_ID_MISSING "
        results = politician_retrieve_error_dict
        results['status'] = status
        return results

    politician_manager = PoliticianManager()
    if positive_value_exists(politician_we_vote_id):
        # Check permissions to make sure this voter can make saves to the Politician
        results = is_voter_politician_owner(
            politician_we_vote_id=politician_we_vote_id, voter_we_vote_id=voter_we_vote_id)
        has_permission_to_edit_politician = results['has_permission_to_edit_politician']
        if not positive_value_exists(has_permission_to_edit_politician):
            status += "DOES_NOT_HAVE_PERMISSION_TO_EDIT_POLITICIAN "
            results = politician_retrieve_error_dict
            results['status'] = status
            return results

        update_values = {}

        # Save politician_photo_from_file_reader and get back we_vote_hosted_politician_photo_original_url
        if politician_photo_changed and politician_photo_from_file_reader:
            photo_results = politician_save_photo_from_file_reader(
                politician_we_vote_id=politician_we_vote_id,
                politician_photo_from_file_reader=politician_photo_from_file_reader)
            if positive_value_exists(photo_results['we_vote_hosted_politician_photo_original_url']):
                update_values['we_vote_hosted_politician_photo_original_url'] = \
                    photo_results['we_vote_hosted_politician_photo_original_url']
                # Now we want to resize to a large version
                create_resized_image_results = create_resized_images(
                    politician_we_vote_id=politician_we_vote_id,
                    politician_uploaded_profile_image_url_https=photo_results\
                    ['we_vote_hosted_politician_photo_original_url'])
                update_values['we_vote_hosted_profile_uploaded_image_url_large'] = \
                    create_resized_image_results['cached_resized_image_url_large']
                update_values['we_vote_hosted_profile_uploaded_image_url_medium'] = \
                    create_resized_image_results['cached_resized_image_url_medium']
                update_values['we_vote_hosted_profile_uploaded_image_url_small'] = \
                    create_resized_image_results['cached_resized_image_url_tiny']
        elif positive_value_exists(politician_photo_delete) and positive_value_exists(politician_photo_delete_changed):
            # Only delete if another photo was not provided
            update_values['we_vote_hosted_politician_photo_original_url'] = None
            update_values['we_vote_hosted_profile_uploaded_image_url_large'] = None
            update_values['we_vote_hosted_profile_uploaded_image_url_medium'] = None
            update_values['we_vote_hosted_profile_uploaded_image_url_small'] = None

        if ballot_guide_official_statement_changed:
            update_values['ballot_guide_official_statement'] = ballot_guide_official_statement
        if campaign_website_changed:
            # Note we are adding campaign_website to the the first politician_url spot below
            pass
        if political_party_changed:
            update_values['political_party'] = political_party
        if politician_name_changed:
            update_values['politician_name'] = politician_name
        if profile_image_type_currently_active_changed:
            update_values['profile_image_type_currently_active'] = profile_image_type_currently_active
        if state_code_changed:
            update_values['state_code'] = state_code

        create_results = politician_manager.update_or_create_politician(
            politician_we_vote_id=politician_we_vote_id,
            update_values=update_values,
        )
    else:
        # If here, we are creating a new Politician
        # Make sure we have minimum required data
        update_values = {
            'ballot_guide_official_statement':      ballot_guide_official_statement,
            'political_party':                      political_party,
            'politician_name':                      politician_name,
            'profile_image_type_currently_active':  profile_image_type_currently_active,
            'state_code':                           state_code,
        }
        create_results = politician_manager.update_or_create_politician(
            politician_name=politician_name,
            state_code=state_code,
            update_values=update_values,
        )
        if create_results['politician_created']:
            # Campaign was just created, so save the voter as an owner
            politician_we_vote_id = create_results['politician_we_vote_id']
            owner_results = politician_manager.update_or_create_politician_owner(
                politician_we_vote_id=politician_we_vote_id,
                organization_we_vote_id=linked_organization_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            status += owner_results['status']
        if create_results['politician_found'] and politician_photo_changed:
            politician = create_results['politician']
            politician_we_vote_id = create_results['politician_we_vote_id']
            if politician_photo_from_file_reader:
                photo_results = politician_save_photo_from_file_reader(
                    politician_we_vote_id=politician_we_vote_id,
                    politician_photo_from_file_reader=politician_photo_from_file_reader)
                if photo_results['we_vote_hosted_politician_photo_original_url']:
                    politician.we_vote_hosted_politician_photo_original_url = \
                        photo_results['we_vote_hosted_politician_photo_original_url']

                    # Now we want to resize to a large version
                    create_resized_image_results = create_resized_images(
                        politician_we_vote_id=politician_we_vote_id,
                        politician_uploaded_profile_image_url_https=politician.we_vote_hosted_politician_photo_original_url)
                    politician.we_vote_hosted_profile_uploaded_image_url_large = \
                        create_resized_image_results['cached_resized_image_url_large']
                    politician.we_vote_hosted_profile_uploaded_image_url_medium = \
                        create_resized_image_results['cached_resized_image_url_medium']
                    politician.we_vote_hosted_profile_uploaded_image_url_small = \
                        create_resized_image_results['cached_resized_image_url_tiny']

                    politician.save()
            else:
                # Deleting image
                politician.we_vote_hosted_profile_uploaded_image_url_large = None
                politician.we_vote_hosted_profile_uploaded_image_url_medium = None
                politician.we_vote_hosted_profile_uploaded_image_url_small = None
                politician.save()

    status += create_results['status']
    if create_results['politician_found']:
        politician_changed = False
        politician = create_results['politician']
        politician_we_vote_id = politician.we_vote_id

        # Update the first politician_url field with campaign_website.
        if campaign_website_changed:
            # Place campaign_website in first spot, and move all other politician_urls to the next spot over.
            campaign_results = add_url_to_politician_url_spot(politician, campaign_website, 1)
            status += campaign_results['status']
            if campaign_results['success'] and campaign_results['values_changed']:
                politician = campaign_results['politician']
                politician_changed = True

        if profile_image_type_currently_active_changed or politician_photo_changed or politician_photo_delete:
            from image.controllers import organize_object_photo_fields_based_on_image_type_currently_active
            results = organize_object_photo_fields_based_on_image_type_currently_active(
                object_with_photo_fields=politician,
                profile_image_type_currently_active=politician.profile_image_type_currently_active,
            )
            status += results['status']
            if results['success'] and results['save_changes']:
                politician = results['object_with_photo_fields']
                from politician.controllers_generate_color import generate_background
                politician.profile_image_background_color = generate_background(politician)
                politician_changed = True

        # If we are saving the politician from an API call, then it means the voter has claimed the profile.
        if not positive_value_exists(politician.is_claimed_profile):
            # Updates data like calculate_if_is_claimed_profile
            politician.is_claimed_profile = True
            politician.is_claimed_profile_date_time = datetime.now()
            politician_changed = True

        if politician_changed:
            try:
                politician.save()
            except Exception as e:
                status += "ERROR_SAVING_POLITICIAN_ONE_LAST_TIME: " + str(e) + " "

        results = politician_retrieve_for_api(
            as_owner=True,
            politician_we_vote_id=politician_we_vote_id,
            voter_device_id=voter_device_id,
        )
        results['status'] = status + results['status']
        return results
    else:
        status += "POLITICIAN_SAVE_ERROR "
        results = politician_retrieve_error_dict
        results['status'] = status
        return results


def politicians_import_from_master_server(request, state_code=''):  # politiciansSyncOut
    """
    Get the json data, and either create new entries or update existing
    :param request:
    :param state_code:
    :return:
    """

    import_results, structured_json = process_request_from_master(
        request, "Loading Politicians from We Vote Master servers",
        POLITICIANS_SYNC_URL,
        {
            "key": WE_VOTE_API_KEY,  # This comes from an environment variable
            "state_code": state_code,
        }
    )

    if import_results['success']:
        import_results = politicians_import_from_structured_json(structured_json)
        import_results['duplicates_removed'] = 0

    return import_results


def politicians_import_from_structured_json(structured_json):  # politiciansSyncOut
    politician_manager = PoliticianManager()
    politicians_saved = 0
    politicians_updated = 0
    politicians_not_processed = 0
    status = ''
    status_passed_through_count = 0

    importing_turned_off = False
    # We need to deal with merging incoming politicians with records created on the developer's machine
    if importing_turned_off:
        status += "POLITICIANS_IMPORT_PROCESS_TURNED_OFF "
        politicians_results = {
            'success': True,
            'status': status,
            'saved': politicians_saved,
            'updated': politicians_updated,
            'not_processed': politicians_not_processed,
        }
        return politicians_results

    boolean_fields = [
        'facebook_url_is_broken',
        'facebook_url2_is_broken',
        'facebook_url3_is_broken',
        'is_battleground_race_2019',
        'is_battleground_race_2020',
        'is_battleground_race_2021',
        'is_battleground_race_2022',
        'is_battleground_race_2023',
        'is_battleground_race_2024',
        'is_battleground_race_2025',
        'is_battleground_race_2026',
        'twitter_handle_updates_failing',
        'twitter_handle2_updates_failing',
    ]
    character_fields = [
        'ballotpedia_id',
        'ballotpedia_politician_name',
        'ballotpedia_politician_url',
        'bioguide_id',
        'cspan_id',
        'ctcl_uuid',
        'facebook_url',
        'facebook_url2',
        'facebook_url3',
        'fec_id',
        'first_name',
        'full_name_assembled',
        'gender',
        'google_civic_candidate_name',
        'google_civic_candidate_name2',
        'google_civic_candidate_name3',
        'govtrack_id',
        'house_history_id',
        'icpsr_id',
        'instagram_handle',
        'last_name',
        'linked_campaignx_we_vote_id',
        'linkedin_url',
        'lis_id',
        'maplight_id',
        'middle_name',
        'opensecrets_id',
        'political_party',
        'politician_contact_form_url',
        'politician_email_address',
        'politician_email',
        'politician_email2',
        'politician_email3',
        'politician_facebook_id',
        'politician_googleplus_id',
        'politician_name',
        'politician_phone_number',
        'politician_phone_number2',
        'politician_phone_number3',
        'politician_twitter_handle',
        'politician_twitter_handle2',
        'politician_twitter_handle3',
        'politician_twitter_handle4',
        'politician_twitter_handle5',
        'politician_url',
        'politician_url2',
        'politician_url3',
        'politician_url4',
        'politician_url5',
        'politician_youtube_id',
        'profile_image_background_color',
        'profile_image_type_currently_active',
        'seo_friendly_path',
        'state_code',
        'thomas_id',
        'twitter_description',
        'twitter_location',
        'twitter_name',
        'twitter_profile_image_url_https',
        'twitter_profile_background_image_url_https',
        'twitter_profile_banner_url_https',
        'vote_smart_id',
        'vote_usa_politician_id',
        'vote_usa_profile_image_url_https',
        'washington_post_id',
        'we_vote_hosted_profile_facebook_image_url_large',
        'we_vote_hosted_profile_facebook_image_url_medium',
        'we_vote_hosted_profile_facebook_image_url_tiny',
        'we_vote_hosted_profile_image_url_large',
        'we_vote_hosted_profile_image_url_medium',
        'we_vote_hosted_profile_image_url_tiny',
        'we_vote_hosted_profile_twitter_image_url_large',
        'we_vote_hosted_profile_twitter_image_url_medium',
        'we_vote_hosted_profile_twitter_image_url_tiny',
        'we_vote_hosted_profile_uploaded_image_url_large',
        'we_vote_hosted_profile_uploaded_image_url_medium',
        'we_vote_hosted_profile_uploaded_image_url_tiny',
        'we_vote_hosted_profile_vote_usa_image_url_large',
        'we_vote_hosted_profile_vote_usa_image_url_medium',
        'we_vote_hosted_profile_vote_usa_image_url_tiny',
        'we_vote_id',
        'wikipedia_id',
        'wikipedia_url',
        'youtube_url',
    ]
    character_null_false_fields = [
    ]
    character_to_date_fields = [
        'birth_date',
    ]
    character_to_datetime_fields = [
        'date_last_updated',
        'date_last_updated_from_candidate',
        'seo_friendly_path_date_last_updated',
    ]
    integer_fields = [
        'instagram_followers_count',
        'twitter_followers_count',
        'twitter_user_id',
    ]
    for one_politician in structured_json:
        politician_name = one_politician['politician_name'] if 'politician_name' in one_politician else ''
        politician_we_vote_id = one_politician['we_vote_id'] if 'we_vote_id' in one_politician else ''

        if positive_value_exists(politician_name):
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False
        if not proceed_to_update_or_create:
            continue

        updated_politician_values = {}
        for one_field in boolean_fields:
            if one_field in one_politician:
                updated_politician_values[one_field] = positive_value_exists(one_politician[one_field])
            else:
                updated_politician_values[one_field] = None
        for one_field in character_fields:
            updated_politician_values[one_field] = one_politician[one_field] \
                if one_field in one_politician \
                else None
        for one_field in character_null_false_fields:
            updated_politician_values[one_field] = one_politician[one_field] \
                if one_field in one_politician \
                else ''
        for one_field in character_to_date_fields:
            if one_field in one_politician and positive_value_exists(one_politician[one_field]):
                date_field_trimmed = one_politician[one_field].replace(" 00:00:00", "")
                updated_politician_values[one_field] = datetime.strptime(date_field_trimmed, '%Y-%m-%d').date()
            else:
                updated_politician_values[one_field] = None
        for one_field in character_to_datetime_fields:
            if one_field in one_politician and positive_value_exists(one_politician[one_field]):
                updated_politician_values[one_field] = \
                    datetime.strptime(one_politician[one_field], DATE_FORMAT_YMD_HMS)  # '%Y-%m-%d %H:%M:%S'
            else:
                updated_politician_values[one_field] = None
        for one_field in integer_fields:
            if one_field in one_politician:
                updated_politician_values[one_field] = convert_to_int(one_politician[one_field])
            else:
                updated_politician_values[one_field] = 0

        results = politician_manager.update_or_create_politician(
            update_values=updated_politician_values,
            politician_we_vote_id=politician_we_vote_id)
        if results['success']:
            if results['politician_created']:
                politicians_saved += 1
            else:
                politicians_updated += 1
            # values_changed = False
            # politician = results['politician']
            # if 'politician_twitter_handle' in one_politician:
            #     twitter_results = add_twitter_handle_to_next_politician_spot(
            #         politician, one_politician['politician_twitter_handle'])
            #     if twitter_results['success']:
            #         politician = twitter_results['politician']
            #         if twitter_results['values_changed']:
            #             values_changed = True
            #     else:
            #         results['status'] += twitter_results['status']
            # if 'politician_twitter_handle2' in one_politician:
            #     twitter_results = add_twitter_handle_to_next_politician_spot(
            #         politician, one_politician['politician_twitter_handle2'])
            #     if twitter_results['success']:
            #         politician = twitter_results['politician']
            #         if twitter_results['values_changed']:
            #             values_changed = True
            #     else:
            #         results['status'] += twitter_results['status']
            # if 'politician_twitter_handle3' in one_politician:
            #     twitter_results = add_twitter_handle_to_next_politician_spot(
            #         politician, one_politician['politician_twitter_handle3'])
            #     if twitter_results['success']:
            #         politician = twitter_results['politician']
            #         if twitter_results['values_changed']:
            #             values_changed = True
            #     else:
            #         results['status'] += twitter_results['status']
            # if 'politician_twitter_handle4' in one_politician:
            #     twitter_results = add_twitter_handle_to_next_politician_spot(
            #         politician, one_politician['politician_twitter_handle4'])
            #     if twitter_results['success']:
            #         politician = twitter_results['politician']
            #         if twitter_results['values_changed']:
            #             values_changed = True
            #     else:
            #         results['status'] += twitter_results['status']
            # if 'politician_twitter_handle5' in one_politician:
            #     twitter_results = add_twitter_handle_to_next_politician_spot(
            #         politician, one_politician['politician_twitter_handle5'])
            #     if twitter_results['success']:
            #         politician = twitter_results['politician']
            #         if twitter_results['values_changed']:
            #             values_changed = True
            #     else:
            #         results['status'] += twitter_results['status']
            # if values_changed:
            #     politician.save()
        else:
            politicians_not_processed += 1
            if status_passed_through_count < 10:
                status += results['status']
                status_passed_through_count += 1

        # if results['success']:
        #     if results['politician_created']:
        #         politicians_saved += 1
        #     else:
        #         politicians_updated += 1

        processed = politicians_not_processed + politicians_saved + politicians_updated
        if not processed % 10000:
            print("... politicians processed for update/create: " + str(processed) + " of " + str(len(structured_json)))

    status += "POLITICIANS_IMPORT_PROCESS_COMPLETE "
    politicians_results = {
        'success':          True,
        'status':           status,
        'saved':            politicians_saved,
        'updated':          politicians_updated,
        'not_processed':    politicians_not_processed,
    }
    return politicians_results


def politicians_query_for_api(  # politiciansQuery
        index_start=0,  # We limit each return to 100, so this is how we page forward
        limit_to_this_state_code='',
        number_requested=100,
        race_office_level_list=[],
        search_text=''):

    politician_list = []
    politician_dict_list = []
    required_variables_missing = False
    returned_count = 0
    status = ''
    success = True
    total_count = 0

    if required_variables_missing:
        json_data = {
            'index_start': 0,
            'kind': 'wevote#politiciansQuery',
            'office_held_list': [],
            'politicians': [],
            'returned_count': 0,
            'state': limit_to_this_state_code,
            'status': status,
            'success': False,
            'total_count': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    politician_manager = PoliticianManager()
    if len(search_text) > 0:
        try:
            results = politician_manager.retrieve_politician_list(
                index_start=index_start,
                limit_to_this_state_code=limit_to_this_state_code,
                read_only=True,
                politicians_limit=number_requested,
                search_string=search_text,
            )
            success = results['success']
            status = results['status']
            politician_list = results['politician_list']
            returned_count = results['returned_count']
            total_count = results['total_count']
        except Exception as e:
            status = 'FAILED politicians_query. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)
            success = False
    else:
        try:
            results = politician_manager.retrieve_politician_list(
                index_start=index_start,
                limit_to_this_state_code=limit_to_this_state_code,
                read_only=True,
                politicians_limit=number_requested,
            )
            success = results['success']
            status = results['status']
            politician_list = results['politician_list']
            returned_count = results['returned_count']
            total_count = results['total_count']
        except Exception as e:
            status = 'FAILED politicians_query. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)
            success = False

    if success:
        for politician in politician_list:
            results = generate_politician_dict_from_politician_object(politician=politician)
            status += results['status']
            if results['success']:
                politician_dict_list.append(results['politician_dict'])

        if len(politician_dict_list):
            status += 'POLITICIANS_RETRIEVED '
        else:
            status += 'NO_POLITICIANS_RETRIEVED '

    json_data = {
        'index_start':      index_start,
        'kind':             'wevote#politiciansQuery',
        'politicians':      politician_dict_list,
        'returned_count':   returned_count,
        'state':            limit_to_this_state_code,
        'status':           status,
        'success':          success,
        'total_count':      total_count,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def update_politician_details_from_campaignx(politician, campaignx):
    status = ''
    success = True
    save_changes = False

    if not hasattr(politician, 'supporters_count') or not hasattr(campaignx, 'supporters_count'):
        success = False
        status += 'UPDATE_POLITICIAN_FROM_CAMPAIGNX_MISSING_REQUIRED_ATTRIBUTES '
        results = {
            'success': success,
            'status': status,
            'politician': politician,
            'save_changes': save_changes,
        }
        return results

    if politician.opposers_count != campaignx.opposers_count:
        politician.opposers_count = campaignx.opposers_count
        save_changes = True

    if politician.supporters_count != campaignx.supporters_count:
        politician.supporters_count = campaignx.supporters_count
        save_changes = True

    results = {
        'success':      success,
        'status':       status,
        'politician':   politician,
        'save_changes': save_changes,
    }
    return results


def update_politician_details_from_candidate(politician=None, candidate=None):
    """
    Meant to add on new information to a politician. Not meant to destroy existing information in the politician
    with data from the candidate.
    :param politician:
    :param candidate:
    :return:
    """
    fields_updated = []
    status = ''
    success = True
    save_changes = False

    if not hasattr(politician, 'politician_name') or not hasattr(candidate, 'candidate_name'):
        status += "MISSING_VALID_POLITICIAN_OR_CANDIDATE "
        success = False
        results = {
            'fields_updated':   fields_updated,
            'politician':       politician,
            'save_changes':     save_changes,
            'success':          success,
            'status':           status,
        }
        return results

    from representative.controllers import add_value_to_next_representative_spot
    if not positive_value_exists(politician.ballotpedia_politician_name) and \
            positive_value_exists(candidate.ballotpedia_candidate_name):
        politician.ballotpedia_politician_name = candidate.ballotpedia_candidate_name
        fields_updated.append('ballotpedia_politician_name')
        save_changes = True
    if not positive_value_exists(politician.ballotpedia_politician_url) and \
            positive_value_exists(candidate.ballotpedia_candidate_url):
        politician.ballotpedia_politician_url = candidate.ballotpedia_candidate_url
        fields_updated.append('ballotpedia_politician_url')
        save_changes = True
    # For identically named fields - no existing value
    results = copy_field_value_from_object1_to_object2(
        object1=candidate,
        object2=politician,
        object1_field_name_list=[
            'ballotpedia_photo_url',
            'ballotpedia_profile_image_url_https',
            'bluesky_handle',
            'instagram_followers_count',
            'instagram_handle',
            'linkedin_photo_url',
            'linkedin_profile_image_url_https',
            'linkedin_url',
            'photo_url_from_vote_usa',
            'tiktok_url',
            'vote_usa_profile_image_url_https',
            'wikipedia_photo_url',
            'wikipedia_url',
            'wikipedia_profile_image_url_https',
            'youtube_url',
        ],
        only_change_object2_field_if_incoming_value=True,
        only_change_object2_field_if_no_existing_value=True)
    politician = results['object2'] if results['success'] and results['values_changed'] else politician
    save_changes = save_changes or results['values_changed']
    fields_updated_append = results['fields_updated']
    for new_field in fields_updated_append:
        if new_field not in fields_updated:
            fields_updated.append(new_field)
    # For identically named fields - lock existing values
    results = copy_field_value_from_object1_to_object2(
        object1=candidate,
        object2=politician,
        object1_field_name_list=[
            'ballot_guide_official_statement',
        ],
        only_change_object2_field_if_incoming_value=False,
        only_change_object2_field_if_no_existing_value=False)
    politician = results['object2'] if results['success'] and results['values_changed'] else politician
    save_changes = save_changes or results['values_changed']
    fields_updated_append = results['fields_updated']
    for new_field in fields_updated_append:
        if new_field not in fields_updated:
            fields_updated.append(new_field)
    candidate_facebook_url_exists = \
        positive_value_exists(candidate.facebook_url) and not candidate.facebook_url_is_broken
    if candidate_facebook_url_exists:
        name_results = add_value_to_next_representative_spot(
            field_name_base='facebook_url',
            representative=politician,
            new_value_to_add=candidate.facebook_url)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if positive_value_exists(candidate.candidate_name) and positive_value_exists(politician.politician_name) \
            and candidate.candidate_name != politician.politician_name:
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_candidate_name',
            look_at_alternate_names=True,
            representative=politician,
            new_value_to_add=candidate.candidate_name)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if positive_value_exists(candidate.google_civic_candidate_name):
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_candidate_name',
            look_at_alternate_names=True,
            representative=politician,
            new_value_to_add=candidate.google_civic_candidate_name)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if positive_value_exists(candidate.google_civic_candidate_name2):
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_candidate_name',
            look_at_alternate_names=True,
            representative=politician,
            new_value_to_add=candidate.google_civic_candidate_name2)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if positive_value_exists(candidate.google_civic_candidate_name3):
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_candidate_name',
            look_at_alternate_names=True,
            representative=politician,
            new_value_to_add=candidate.google_civic_candidate_name3)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if not positive_value_exists(politician.instagram_followers_count) and \
            positive_value_exists(candidate.instagram_followers_count):
        politician.instagram_followers_count = candidate.instagram_followers_count
        fields_updated.append('instagram_followers_count')
        save_changes = True
    if not positive_value_exists(politician.instagram_handle) and \
            positive_value_exists(candidate.instagram_handle):
        politician.instagram_handle = candidate.instagram_handle
        fields_updated.append('instagram_handle')
        save_changes = True
    if not positive_value_exists(politician.linkedin_url) and \
            positive_value_exists(candidate.linkedin_url):
        politician.linkedin_url = candidate.linkedin_url
        fields_updated.append('linkedin_url')
        save_changes = True
    if positive_value_exists(candidate.candidate_email):
        name_results = add_value_to_next_representative_spot(
            field_name_base='politician_email',
            look_at_alternate_names=False,
            representative=politician,
            new_value_to_add=candidate.candidate_email)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if not positive_value_exists(politician.political_party) and positive_value_exists(candidate.party):
        politician.political_party = candidate.party
        fields_updated.append('political_party')
        save_changes = True
    if not positive_value_exists(politician.politician_phone_number) and \
            positive_value_exists(candidate.candidate_phone):
        politician.politician_phone_number = candidate.candidate_phone
        fields_updated.append('politician_phone_number')
        save_changes = True
    if not positive_value_exists(politician.twitter_description) and \
            positive_value_exists(candidate.twitter_description):
        politician.twitter_description = candidate.twitter_description
        fields_updated.append('twitter_description')
        save_changes = True
    if not positive_value_exists(politician.twitter_followers_count) and \
            positive_value_exists(candidate.twitter_followers_count):
        politician.twitter_followers_count = candidate.twitter_followers_count
        fields_updated.append('twitter_followers_count')
        save_changes = True
    if positive_value_exists(candidate.candidate_twitter_handle) and not candidate.twitter_handle_updates_failing:
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician, candidate.candidate_twitter_handle)
        if twitter_results['success']:
            politician = twitter_results['politician']
    if positive_value_exists(candidate.candidate_twitter_handle2) and not candidate.twitter_handle2_updates_failing:
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician, candidate.candidate_twitter_handle2)
        if twitter_results['success']:
            politician = twitter_results['politician']
    if positive_value_exists(candidate.candidate_twitter_handle3):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician, candidate.candidate_twitter_handle3)
        if twitter_results['success']:
            politician = twitter_results['politician']
    if not positive_value_exists(politician.twitter_location) and \
            positive_value_exists(candidate.twitter_location):
        politician.twitter_location = candidate.twitter_location
        fields_updated.append('twitter_location')
        save_changes = True
    if not positive_value_exists(politician.twitter_name) and \
            positive_value_exists(candidate.twitter_name):
        politician.twitter_name = candidate.twitter_name
        fields_updated.append('twitter_name')
        save_changes = True
    # Contact Form URL
    if not positive_value_exists(politician.politician_contact_form_url) and \
            positive_value_exists(candidate.candidate_contact_form_url):
        politician.politician_contact_form_url = candidate.candidate_contact_form_url
        fields_updated.append('politician_contact_form_url')
        save_changes = True
    # URL
    if positive_value_exists(candidate.candidate_url):
        name_results = add_value_to_next_representative_spot(
            field_name_base='politician_url',
            look_at_alternate_names=True,
            representative=politician,
            new_value_to_add=candidate.candidate_url)
        if name_results['success']:
            politician = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
            if name_results['values_changed']:
                if name_results['field_updated'] not in fields_updated:
                    fields_updated.append(name_results['field_updated'])
    if not positive_value_exists(politician.vote_usa_politician_id) and \
            positive_value_exists(candidate.vote_usa_politician_id):
        politician.vote_usa_politician_id = candidate.vote_usa_politician_id
        fields_updated.append('vote_usa_politician_id')
        save_changes = True
    # Photos
    if politician.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
        if positive_value_exists(candidate.profile_image_type_currently_active) \
                and candidate.profile_image_type_currently_active != PROFILE_IMAGE_TYPE_UNKNOWN:
            politician.profile_image_type_currently_active = candidate.profile_image_type_currently_active
            save_changes = True
            if 'profile_image_type_currently_active' not in fields_updated:
                fields_updated.append('profile_image_type_currently_active')
    results = copy_field_value_from_object1_to_object2(
        object1=candidate,
        object2=politician,
        object1_field_name_list=[
            'we_vote_hosted_profile_ballotpedia_image_url_large',
            'we_vote_hosted_profile_ballotpedia_image_url_medium',
            'we_vote_hosted_profile_ballotpedia_image_url_tiny',
            'we_vote_hosted_profile_facebook_image_url_large',
            'we_vote_hosted_profile_facebook_image_url_medium',
            'we_vote_hosted_profile_facebook_image_url_tiny',
            'we_vote_hosted_profile_linkedin_image_url_large',
            'we_vote_hosted_profile_linkedin_image_url_medium',
            'we_vote_hosted_profile_linkedin_image_url_tiny',
            'we_vote_hosted_profile_twitter_image_url_large',
            'we_vote_hosted_profile_twitter_image_url_medium',
            'we_vote_hosted_profile_twitter_image_url_tiny',
            'we_vote_hosted_profile_uploaded_image_url_large',
            'we_vote_hosted_profile_uploaded_image_url_medium',
            'we_vote_hosted_profile_uploaded_image_url_tiny',
            'we_vote_hosted_profile_vote_usa_image_url_large',
            'we_vote_hosted_profile_vote_usa_image_url_medium',
            'we_vote_hosted_profile_vote_usa_image_url_tiny',
            'we_vote_hosted_profile_wikipedia_image_url_large',
            'we_vote_hosted_profile_wikipedia_image_url_medium',
            'we_vote_hosted_profile_wikipedia_image_url_tiny',
        ],
        only_change_object2_field_if_incoming_value=True,
        only_change_object2_field_if_no_existing_value=True)
    politician = results['object2'] if results['success'] and results['values_changed'] else politician
    save_changes = save_changes or results['values_changed']
    fields_updated_append = results['fields_updated']
    for new_field in fields_updated_append:
        if new_field not in fields_updated:
            fields_updated.append(new_field)
    profile_image_default_updated = False
    from image.controllers import organize_object_photo_fields_based_on_image_type_currently_active
    results = organize_object_photo_fields_based_on_image_type_currently_active(
        object_with_photo_fields=politician,
        profile_image_type_currently_active=politician.profile_image_type_currently_active,
    )
    if results['success']:
        politician = results['object_with_photo_fields']
        profile_image_default_updated = results['profile_image_default_updated']
        save_changes = save_changes or results['values_changed']

    if profile_image_default_updated:
        if 'profile_image_type_currently_active' not in fields_updated:
            fields_updated.append('profile_image_type_currently_active')
        if 'we_vote_hosted_profile_image_url_large' not in fields_updated:
            fields_updated.append('we_vote_hosted_profile_image_url_large')
        if 'we_vote_hosted_profile_image_url_medium' not in fields_updated:
            fields_updated.append('we_vote_hosted_profile_image_url_medium')
        if 'we_vote_hosted_profile_image_url_tiny' not in fields_updated:
            fields_updated.append('we_vote_hosted_profile_image_url_tiny')

    # Other
    # if not positive_value_exists(politician.wikipedia_url) and \
    #         positive_value_exists(candidate.wikipedia_url):
    #     politician.wikipedia_url = candidate.wikipedia_url
    #     fields_updated.append('wikipedia_url')
    #     save_changes = True

    results = {
        'fields_updated':   fields_updated,
        'politician':       politician,
        'save_changes':     save_changes,
        'status':           status,
        'success':          success,
    }
    return results


def update_parallel_fields_with_years_in_related_objects(
        field_key_root='',
        master_we_vote_id_updated='',
        years_false_list=[],
        years_true_list=[]):
    status = ''
    success = True
    update_candidate = True
    update_office = True
    update_office_held = True
    years_list = list(set(years_false_list + years_true_list))

    if field_key_root not in ['is_battleground_race_']:
        status += "FIELD_KEY_ROOT_NOT_RECOGNIZED "
        success = False
    if not positive_value_exists(master_we_vote_id_updated):
        status += "MISSING_MASTER_WE_VOTE_ID "
        success = False
    if not len(years_list) > 0:
        if 'cand' in master_we_vote_id_updated:
            # Calculate below
            status += "CALCULATE_YEARS_LISTS_FOR_CANDIDATE "
        else:
            status += "MISSING_YEARS_LIST "
            success = False
    if not success:
        results = {
            'success': success,
            'status': status,
        }
        return results

    candidate_list_manager = CandidateListManager()
    candidate_manager = CandidateManager()
    candidate_we_vote_id_list = []
    office_list_manager = ContestOfficeListManager()
    office_manager = ContestOfficeManager()
    office_we_vote_id_list = []
    update_candidates_under_these_office_we_vote_ids = []
    from office_held.models import OfficeHeldManager
    office_held_manager = OfficeHeldManager()
    office_held_we_vote_id_list = []
    politician_manager = PoliticianManager()
    politician_we_vote_id_list = []
    representative_manager = RepresentativeManager()
    if 'cand' in master_we_vote_id_updated:
        # We never treat candidate battleground data as master data, so we need to look at the ContestOffice
        #  for is_battleground_race
        update_office = False
        year = 0
        years_false_list = []
        years_true_list = []
        link_results = candidate_manager.retrieve_candidate_to_office_link(
            candidate_we_vote_id=master_we_vote_id_updated)
        if link_results['only_one_found']:
            candidate_to_office_link = link_results['candidate_to_office_link']
            office_we_vote_id_list.append(candidate_to_office_link.contest_office_we_vote_id)
        elif link_results['list_found']:
            candidate_to_office_link_list = link_results['candidate_to_office_link_list']
            for candidate_to_office_link in candidate_to_office_link_list:
                office_we_vote_id_list.append(candidate_to_office_link.contest_office_we_vote_id)
        if len(office_we_vote_id_list) > 0:
            office_results = office_list_manager.retrieve_offices(
                retrieve_from_this_office_we_vote_id_list=office_we_vote_id_list,
                return_list_of_objects=True)
            if office_results['success']:
                office_list = office_results['office_list_objects']
                latest_election_day_text_as_integer = 0
                if len(office_list) > 0:
                    # Just pick one to start with in case "get_election_day_text()" returns nothing
                    latest_office_we_vote_id = office_list[0].we_vote_id
                else:
                    latest_office_we_vote_id = ''
                # Filter out primary office races
                for office in office_list:
                    election_day_text = office.get_election_day_text()
                    if positive_value_exists(election_day_text):
                        date_as_integer = \
                            convert_we_vote_date_string_to_date_as_integer(election_day_text)
                        if date_as_integer > latest_election_day_text_as_integer:
                            latest_election_day_text_as_integer = date_as_integer
                            latest_office_we_vote_id = office.we_vote_id
                for office in office_list:
                    if office.we_vote_id is latest_office_we_vote_id:
                        election_day_text = office.get_election_day_text()
                        if positive_value_exists(election_day_text):
                            date_as_integer = convert_we_vote_date_string_to_date_as_integer(election_day_text)
                            year = date_as_integer // 10000
                        if positive_value_exists(year):
                            if positive_value_exists(office.is_battleground_race):
                                years_true_list = [year]
                            else:
                                # When coming from a candidate, don't update politician+ with false years
                                # years_false_list = [year]
                                pass
        years_list = list(set(years_false_list + years_true_list))
        if len(years_list) > 0:
            results = candidate_manager.retrieve_candidate(
                candidate_we_vote_id=master_we_vote_id_updated,
                read_only=True)
            if results['candidate_found']:
                candidate = results['candidate']
                if positive_value_exists(candidate.politician_we_vote_id):
                    if candidate.politician_we_vote_id not in politician_we_vote_id_list:
                        politician_we_vote_id_list.append(candidate.politician_we_vote_id)
                        results = politician_manager.retrieve_politician(
                            politician_we_vote_id=candidate.politician_we_vote_id,
                            read_only=False)
                        if not results['success']:
                            success = False
                        elif results['politician_found']:
                            politician = results['politician']
                            results = update_parallel_fields_on_related_object(
                                field_key_root=field_key_root,
                                object_to_update=politician,
                                years_false_list=years_false_list,
                                years_true_list=years_true_list)
                            if not results['success']:
                                status += results['status']
                    if success and positive_value_exists(politician_we_vote_id_list):
                        results = representative_manager.retrieve_representative_list(
                            politician_we_vote_id_list=politician_we_vote_id_list,
                            read_only=False,
                            years_list=years_list,
                        )
                        if not results['success']:
                            success = False
                        if success:
                            representative_list = results['representative_list']
                            for representative in representative_list:
                                results = update_parallel_fields_on_related_object(
                                    field_key_root=field_key_root,
                                    object_to_update=representative,
                                    years_false_list=years_false_list,
                                    years_true_list=years_true_list)
                                if not results['success']:
                                    status += results['status']
                                if positive_value_exists(representative.office_held_we_vote_id) and \
                                        representative.office_held_we_vote_id not in office_held_we_vote_id_list:
                                    office_held_we_vote_id_list.append(representative.office_held_we_vote_id)
    elif 'officeheld' in master_we_vote_id_updated:
        update_office_held = False
        results = update_representatives_under_this_office_held(
            field_key_root=field_key_root,
            office_held_we_vote_id=master_we_vote_id_updated,
            years_false_list=years_false_list,
            years_true_list=years_true_list)
        status += results['status']
        if results['success']:
            politician_we_vote_id_list = \
                list(set(politician_we_vote_id_list +
                         results['politician_we_vote_id_list']))
    elif 'off' in master_we_vote_id_updated:
        update_candidate = False
        update_office = False
        results = update_candidates_under_this_office(
            field_key_root=field_key_root,
            office_we_vote_id=master_we_vote_id_updated,
            years_false_list=years_false_list,
            years_true_list=years_true_list)
        status += results['status']
        if results['success']:
            office_held_we_vote_id_list = \
                list(set(office_held_we_vote_id_list +
                         results['office_held_we_vote_id_list']))
        politician_we_vote_id_list = []  # Reset this so we don't trigger the actions below
    elif 'pol' in master_we_vote_id_updated:
        politician_we_vote_id_list = [master_we_vote_id_updated]
        # Direct update: Representatives (Retrieve representative_list)
        results = representative_manager.retrieve_representative_list(
            politician_we_vote_id_list=[master_we_vote_id_updated],
            read_only=False,
            years_list=years_list,
        )
        if not results['success']:
            success = False
        if success:
            representative_list = results['representative_list']
            for representative in representative_list:
                results = update_parallel_fields_on_related_object(
                    field_key_root=field_key_root,
                    object_to_update=representative,
                    years_false_list=years_false_list,
                    years_true_list=years_true_list)
                if not results['success']:
                    status += results['status']
                if positive_value_exists(representative.office_held_we_vote_id) and \
                        representative.office_held_we_vote_id not in office_held_we_vote_id_list:
                    office_held_we_vote_id_list.append(representative.office_held_we_vote_id)
        # For each Representative we update, update OfficeHeld below
        # Update Candidate (for that year) and Office (last for that year) below
    elif 'rep' in master_we_vote_id_updated:
        results = representative_manager.retrieve_representative(representative_we_vote_id=master_we_vote_id_updated)
        if not results['success']:
            success = False
        if success:
            representative = results['representative']
            if positive_value_exists(representative.office_held_we_vote_id):
                office_held_we_vote_id_list = [representative.office_held_we_vote_id]
            if positive_value_exists(representative.politician_we_vote_id):
                politician_we_vote_id_list = [representative.politician_we_vote_id]
                # Direct update: Politician
                results = politician_manager.retrieve_politician(
                    politician_we_vote_id=representative.politician_we_vote_id,
                    read_only=False)
                if not results['success']:
                    success = False
                if results['politician_found']:
                    politician = results['politician']
                    results = update_parallel_fields_on_related_object(
                        field_key_root=field_key_root,
                        object_to_update=politician,
                        years_false_list=years_false_list,
                        years_true_list=years_true_list)
                    if not results['success']:
                        status += results['status']
        # Update OfficeHeld below
        # Update Candidate (for that year) and Office (last for that year) below

    # For each Politician we worked with, update the candidate(s) for that year:
    #  I believe from 2020 forward we only had one candidate entry per object.
    if success and len(politician_we_vote_id_list) > 0:
        for year in years_list:
            candidate_results = candidate_list_manager.retrieve_all_candidates_for_one_year(
                candidate_year=year,
                politician_we_vote_id_list=politician_we_vote_id_list,
                return_list_of_objects=True)
            if not candidate_results['success']:
                success = False
            if success:
                candidate_list = candidate_results['candidate_list_objects']
                if year in years_false_list:
                    is_battleground_race = False
                elif year in years_true_list:
                    is_battleground_race = True
                else:
                    is_battleground_race = None
                if is_battleground_race is not None:
                    office_we_vote_id_list = []
                    candidates_to_update = []  # List for bulk update
                    for candidate in candidate_list:
                        if positive_value_exists(update_candidate):
                            # Modify object in memory
                            candidate.is_battleground_race = is_battleground_race
                            candidates_to_update.append(candidate)

                        # For each Candidate we update, update the last ContestOffice for that year
                        link_results = candidate_manager.retrieve_candidate_to_office_link(
                            candidate_we_vote_id=candidate.we_vote_id)
                        if link_results['only_one_found']:
                            candidate_to_office_link = link_results['candidate_to_office_link']
                            office_we_vote_id_list.append(candidate_to_office_link.contest_office_we_vote_id)
                        elif link_results['list_found']:
                            candidate_to_office_link_list = link_results['candidate_to_office_link_list']
                            for candidate_to_office_link in candidate_to_office_link_list:
                                office_we_vote_id_list.append(candidate_to_office_link.contest_office_we_vote_id)

                    # Perform Candidate Bulk Save
                    if len(candidates_to_update) > 0:
                        try:
                            CandidateCampaign.objects.bulk_update(candidates_to_update, ['is_battleground_race'])
                        except Exception as e:
                            status += "BULK_COULD_NOT_SAVE_CANDIDATES: " + str(e) + " "

                    # Now update all related offices for this candidate in this year
                    if len(office_we_vote_id_list) > 0 and update_office:
                        office_results = office_list_manager.retrieve_offices(
                            retrieve_from_this_office_we_vote_id_list=office_we_vote_id_list,
                            return_list_of_objects=True)
                        if office_results['success']:
                            office_list = office_results['office_list_objects']
                            offices_to_update = []  # List for bulk update
                            latest_election_day_text_as_integer = 0
                            if len(office_list) > 0:
                                latest_office_we_vote_id = office_list[0].we_vote_id
                            else:
                                latest_office_we_vote_id = ''

                            # Filter out primary office races to find the latest office
                            for office in office_list:
                                election_day_text = office.get_election_day_text()
                                if positive_value_exists(election_day_text):
                                    date_as_integer = convert_we_vote_date_string_to_date_as_integer(election_day_text)
                                    if date_as_integer > latest_election_day_text_as_integer:
                                        latest_election_day_text_as_integer = date_as_integer
                                        latest_office_we_vote_id = office.we_vote_id

                            # Prepare offices for bulk update
                            for office in office_list:
                                if office.we_vote_id == latest_office_we_vote_id:
                                    if update_office:
                                        office.is_battleground_race = is_battleground_race
                                        offices_to_update.append(office)

                                    if positive_value_exists(office.office_held_we_vote_id) and \
                                        office.office_held_we_vote_id not in office_held_we_vote_id_list:
                                        office_held_we_vote_id_list.append(office.office_held_we_vote_id)
                                    under_results = update_candidates_under_this_office(
                                        field_key_root=field_key_root,
                                        office_we_vote_id=office.we_vote_id,
                                        years_false_list=years_false_list,
                                        years_true_list=years_true_list)
                                    if under_results['success']:
                                        office_held_we_vote_id_list = list(set(office_held_we_vote_id_list +
                                                                               under_results[
                                                                                   'office_held_we_vote_id_list']))

                            # Perform Office Bulk Save
                            if len(offices_to_update) > 0:
                                try:
                                    ContestOffice.objects.bulk_update(offices_to_update, ['is_battleground_race'])
                                except Exception as e:
                                    status += "BULK_COULD_NOT_SAVE_OFFICE: " + str(e) + " "

    # For each Representative we dealt with, update OfficeHeld
    if success and positive_value_exists(office_held_we_vote_id_list) and update_office_held:
        results = office_held_manager.retrieve_office_held_list(
            office_held_we_vote_id_list=office_held_we_vote_id_list
        )
        if not results['success']:
            success = False
        if success:
            office_held_list = results['office_held_list']
            for office_held in office_held_list:
                results = update_parallel_fields_on_related_object(
                    field_key_root=field_key_root,
                    object_to_update=office_held,
                    years_false_list=years_false_list,
                    years_true_list=years_true_list)
                if not results['success']:
                    status += results['status']
                under_results = update_representatives_under_this_office_held(
                    field_key_root=field_key_root,
                    office_held_we_vote_id=office_held.we_vote_id,
                    years_false_list=years_false_list,
                    years_true_list=years_true_list)
                status += under_results['status']
                if not under_results['success']:
                    success = False

    results = {
        'success':      success,
        'status':       status,
    }
    return results


def update_candidates_under_this_office(
        field_key_root='',
        office_we_vote_id='',
        years_false_list=[],
        years_true_list=[]):
    candidate_list_manager = CandidateListManager()
    candidate_manager = CandidateManager()
    candidate_we_vote_id_list = []
    office_held_we_vote_id_list = []
    office_manager = ContestOfficeManager()
    politician_manager = PoliticianManager()
    politician_we_vote_id_list = []
    representative_manager = RepresentativeManager()
    status = ""
    success = True
    years_list = list(set(years_false_list + years_true_list))
    # Update the candidates underneath this office
    link_results = candidate_manager.retrieve_candidate_to_office_link(
        contest_office_we_vote_id=office_we_vote_id)
    if not link_results['success']:
        success = False
    elif link_results['only_one_found']:
        candidate_to_office_link = link_results['candidate_to_office_link']
        candidate_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)
    elif link_results['list_found']:
        candidate_to_office_link_list = link_results['candidate_to_office_link_list']
        for candidate_to_office_link in candidate_to_office_link_list:
            candidate_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)
    if success and len(candidate_we_vote_id_list) > 0:
        results = candidate_list_manager.retrieve_candidate_list(
            candidate_we_vote_id_list=candidate_we_vote_id_list,
            read_only=False)
        if not results['success']:
            success = False
        if success and results['candidate_list_found']:
            candidate_list = results['candidate_list']
            # We need to retrieve office, so we can get year of the election
            office_results = office_manager.retrieve_contest_office(
                contest_office_we_vote_id=office_we_vote_id)
            year = 0
            if not office_results['success']:
                success = False
            if success and office_results['contest_office_found']:
                office = office_results['contest_office']
                election_day_text = office.get_election_day_text()
                if positive_value_exists(election_day_text):
                    date_as_integer = convert_we_vote_date_string_to_date_as_integer(election_day_text)
                    year = date_as_integer // 10000
            if year in years_false_list:
                is_battleground_race = False
            elif year in years_true_list:
                is_battleground_race = True
            else:
                is_battleground_race = None
            if is_battleground_race is not None:
                for candidate in candidate_list:
                    try:
                        candidate.is_battleground_race = is_battleground_race
                        candidate.save()
                    except Exception as e:
                        status += "COULD_NOT_SAVE_CANDIDATE1: " + str(e) + " "
                    # For each Candidate, update the Politician here
                    # Direct update: Politician
                    if positive_value_exists(candidate.politician_we_vote_id):
                        if candidate.politician_we_vote_id not in politician_we_vote_id_list:
                            politician_we_vote_id_list.append(candidate.politician_we_vote_id)
                            results = politician_manager.retrieve_politician(
                                politician_we_vote_id=candidate.politician_we_vote_id,
                                read_only=False)
                            if not results['success']:
                                success = False
                            if results['politician_found']:
                                politician = results['politician']
                                results = update_parallel_fields_on_related_object(
                                    field_key_root=field_key_root,
                                    object_to_update=politician,
                                    years_false_list=years_false_list,
                                    years_true_list=years_true_list)
                                if not results['success']:
                                    status += results['status']
                if positive_value_exists(politician_we_vote_id_list):
                    results = representative_manager.retrieve_representative_list(
                        politician_we_vote_id_list=politician_we_vote_id_list,
                        read_only=False,
                        years_list=years_list,
                    )
                    if not results['success']:
                        success = False
                    if success:
                        representative_list = results['representative_list']
                        for representative in representative_list:
                            results = update_parallel_fields_on_related_object(
                                field_key_root=field_key_root,
                                object_to_update=representative,
                                years_false_list=years_false_list,
                                years_true_list=years_true_list)
                            if not results['success']:
                                status += results['status']
                            if positive_value_exists(representative.office_held_we_vote_id) and \
                                    representative.office_held_we_vote_id not in office_held_we_vote_id_list:
                                office_held_we_vote_id_list.append(representative.office_held_we_vote_id)

    results = {
        'office_held_we_vote_id_list':  office_held_we_vote_id_list,
        'success':      success,
        'status':       status,
    }
    return results


def update_representatives_under_this_office_held(
        field_key_root='',
        office_held_we_vote_id='',
        years_false_list=[],
        years_true_list=[]):
    politician_manager = PoliticianManager()
    politician_we_vote_id_list = []
    representative_manager = RepresentativeManager()
    status = ""
    success = True
    years_list = list(set(years_false_list + years_true_list))

    # Direct update: Representatives (Retrieve representative_list)
    results = representative_manager.retrieve_representative_list(
        office_held_we_vote_id_list=[office_held_we_vote_id],
        read_only=False,
        years_list=years_list,
    )
    if not results['success']:
        success = False
    if success:
        representative_list = results['representative_list']
        for representative in representative_list:
            attach_results = update_parallel_fields_on_related_object(
                field_key_root=field_key_root,
                object_to_update=representative,
                years_false_list=years_false_list,
                years_true_list=years_true_list)
            if not attach_results['success']:
                status += attach_results['status']
            if positive_value_exists(representative.politician_we_vote_id) and \
                    representative.politician_we_vote_id not in politician_we_vote_id_list:
                politician_we_vote_id_list.append(representative.politician_we_vote_id)
    # For each Representative we updated, update attached Politician
    if success and len(politician_we_vote_id_list) > 0:
        politician_results = politician_manager.retrieve_politician_list(
            politician_we_vote_id_list=politician_we_vote_id_list)
        if not politician_results['success']:
            success = False
        if success:
            politician_list = politician_results['politician_list']
            for politician in politician_list:
                attach_results = update_parallel_fields_on_related_object(
                    field_key_root=field_key_root,
                    object_to_update=politician,
                    years_false_list=years_false_list,
                    years_true_list=years_true_list)
                if not attach_results['success']:
                    status += attach_results['status']

    results = {
        'politician_we_vote_id_list':  politician_we_vote_id_list,
        'success':      success,
        'status':       status,
    }
    return results


def update_parallel_fields_on_related_object(
    field_key_root='',
    object_to_update=None,
    years_false_list=[],
    years_true_list=[]
):
    status = ''
    success = True
    save_changes = False
    try:
        for year_integer in years_false_list:
            field_key = field_key_root + str(year_integer)
            setattr(object_to_update, field_key, False)
            save_changes = True
        for year_integer in years_true_list:
            field_key = field_key_root + str(year_integer)
            setattr(object_to_update, field_key, True)
            save_changes = True
        if save_changes:
            object_to_update.save()
    except Exception as e:
        status += "FAILURE_TO_UPDATE_RELATED_OBJECT: " + str(e) + " "
        success = False

    results = {
        'success':      success,
        'status':       status,
    }
    return results
