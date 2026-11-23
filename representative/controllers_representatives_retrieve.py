# representative/controllers_representatives_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import PROFILE_IMAGE_TYPE_UNKNOWN, PROFILE_IMAGE_TYPE_UPLOADED
from config.environment_variable_functions import get_environment_variable
from datetime import datetime
from django.db.models import Q
from django.http import HttpResponse
from exception.models import handle_exception
import json
from office_held.controllers import generate_office_held_dict_list_from_office_held_we_vote_id_list
from politician.models import PoliticianManager
from voter.models import BALLOT_ADDRESS, VoterAddressManager, VoterDeviceLinkManager, VoterManager
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE
import wevote_functions.admin
from wevote_functions.functions import add_period_to_middle_name_initial, add_period_to_name_prefix_and_suffix, \
    convert_to_int, convert_to_political_party_constant, positive_value_exists, process_request_from_master, \
    remove_period_from_middle_name_initial, remove_period_from_name_prefix_and_suffix
from wevote_functions.functions_date import DATE_FORMAT_YMD_HMS
from .models import Representative, RepresentativeManager, REPRESENTATIVE_UNIQUE_IDENTIFIERS

logger = wevote_functions.admin.get_logger(__name__)

REPRESENTATIVE_SYNC_URL = "https://api.wevoteusa.org/apis/v1/representativesSyncOut/"
# REPRESENTATIVE_SYNC_URL = "http://localhost:8001/apis/v1/representativesSyncOut/"
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")



def generate_representative_dict_list_from_representative_object_list(
        representative_object_list=[]):
    representative_dict_list = []
    status = ""
    success = True

    for representative_object in representative_object_list:
        results = generate_representative_dict_from_representative_object(representative=representative_object)
        status += results['status']
        if results['success']:
            representative_dict_list.append(results['representative_dict'])

    results = {
        'representative_dict_list': representative_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def generate_representative_dict_from_representative_object(
        representative=None):
    status = ""
    success = True

    date_last_updated = ''
    if positive_value_exists(representative.date_last_updated):
        date_last_updated = representative.date_last_updated.strftime(DATE_FORMAT_YMD_HMS)  # '%Y-%m-%d %H:%M:%S'
    representative_dict = {
        'id':                           representative.id,
        'we_vote_id':                   representative.we_vote_id,
        'ballot_item_display_name':     representative.display_representative_name(),
        'facebook_url':                 representative.facebook_url
        if not representative.facebook_url_is_broken else '',
        'instagram_followers_count':    representative.instagram_followers_count,
        'instagram_handle':             representative.instagram_handle,
        'is_battleground_race_2019':    positive_value_exists(representative.is_battleground_race_2019),
        'is_battleground_race_2020':    positive_value_exists(representative.is_battleground_race_2020),
        'is_battleground_race_2021':    positive_value_exists(representative.is_battleground_race_2021),
        'is_battleground_race_2022':    positive_value_exists(representative.is_battleground_race_2022),
        'is_battleground_race_2023':    positive_value_exists(representative.is_battleground_race_2023),
        'is_battleground_race_2024':    positive_value_exists(representative.is_battleground_race_2024),
        'is_battleground_race_2025':    positive_value_exists(representative.is_battleground_race_2025),
        'is_battleground_race_2026':    positive_value_exists(representative.is_battleground_race_2026),
        'is_battleground_race_2027':    positive_value_exists(representative.is_battleground_race_2027),
        'is_battleground_race_2028':    positive_value_exists(representative.is_battleground_race_2028),
        'is_battleground_race_2029':    positive_value_exists(representative.is_battleground_race_2029),
        'is_battleground_race_2030':    positive_value_exists(representative.is_battleground_race_2030),
        'is_claimed_profile':           representative.is_claimed_profile
        if positive_value_exists(representative.is_claimed_profile) else False,  # TO BE IMPLEMENTED FROM POLITICIAN
        'last_updated':                 date_last_updated,
        'linked_campaignx_we_vote_id':  representative.linked_campaignx_we_vote_id,
        'linkedin_url':                 representative.linkedin_url,
        'ocd_division_id':              representative.ocd_division_id,
        'office_held_id':               representative.office_held_id,
        'office_held_district_name':    representative.office_held_district_name,
        'office_held_name':             representative.office_held_name,
        'office_held_we_vote_id':       representative.office_held_we_vote_id,
        'political_party':              representative.political_party_display(),
        'politician_id':                representative.politician_id,
        'politician_we_vote_id':        representative.politician_we_vote_id,
        'profile_image_background_color': representative.profile_image_background_color,
        'representative_contact_form_url': representative.representative_contact_form_url,
        'representative_email':         representative.representative_email,
        'representative_email2':        representative.representative_email2,
        'representative_email3':        representative.representative_email3,
        'representative_name':          representative.representative_name,
        'representative_phone':         representative.representative_phone,
        'representative_phone2':        representative.representative_phone2,
        'representative_phone3':        representative.representative_phone3,
        'representative_photo_url_large': representative.we_vote_hosted_profile_image_url_large,
        'representative_photo_url_medium': representative.we_vote_hosted_profile_image_url_medium,
        'representative_photo_url_tiny': representative.we_vote_hosted_profile_image_url_tiny,
        'representative_url':           representative.representative_url,
        'seo_friendly_path':            representative.seo_friendly_path,
        'state_code':                   representative.state_code,
        'supporters_count':             representative.supporters_count,
        'twitter_url':                  representative.twitter_url,
        'twitter_handle':               representative.fetch_twitter_handle(),
        'twitter_description':          representative.twitter_description
        if positive_value_exists(representative.twitter_description) and
        len(representative.twitter_description) > 1 else '',
        'twitter_followers_count':      representative.twitter_followers_count,
        'vote_usa_office_id':           representative.vote_usa_office_id,
        'vote_usa_politician_id':       representative.vote_usa_politician_id,
        'wikipedia_url':                representative.wikipedia_url,
        'year_in_office_2023':          representative.year_in_office_2023,
        'year_in_office_2024':          representative.year_in_office_2024,
        'year_in_office_2025':          representative.year_in_office_2025,
        'year_in_office_2026':          representative.year_in_office_2026,
        'year_in_office_2027':          representative.year_in_office_2027,
        'year_in_office_2028':          representative.year_in_office_2028,
        'year_in_office_2029':          representative.year_in_office_2029,
        'year_in_office_2030':          representative.year_in_office_2030,
        'youtube_url':                  representative.youtube_url,
    }

    results = {
        'representative_dict':  representative_dict,
        'status':               status,
        'success':              success,
    }
    return results


def representatives_query_for_api(  # representativesQuery
        index_start=0,  # We limit each return to 300, so this is how we page forward
        year=0,
        limit_to_this_state_code='',
        number_requested=300,
        race_office_level_list=[],
        search_text=''):

    representative_list = []
    representative_dict_list = []
    required_variables_missing = False
    retrieve_mode = ''
    returned_count = 0
    status = ''
    success = True
    total_count = 0

    year = convert_to_int(year)
    if year <= 9999:
        # We want all representatives for one year
        retrieve_mode = 'YEAR'
    elif year <= 999999:
        # We want all representatives for one month
        retrieve_mode = 'MONTH'
    elif len(search_text) > 0:
        pass
    else:
        retrieve_mode = 'YEAR'
        today = datetime.now().date()
        year = today.year

    if required_variables_missing:
        json_data = {
            'index_start': 0,
            'kind': 'wevote#representativesQuery',
            'office_held_list': [],
            'representatives': [],
            'returned_count': 0,
            'state': limit_to_this_state_code,
            'status': status,
            'success': False,
            'total_count': 0,
            'year': year,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    representative_manager = RepresentativeManager()
    if retrieve_mode == 'YEAR':
        try:
            results = representative_manager.retrieve_representative_list(
                index_start=index_start,
                limit_to_this_state_code=limit_to_this_state_code,
                read_only=True,
                representatives_limit=number_requested,
                years_list=[year],
            )
            success = results['success']
            status = results['status']
            representative_list = results['representative_list']
            returned_count = results['returned_count']
            total_count = results['total_count']
        except Exception as e:
            status = 'FAILED representatives_query. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)
            success = False
    elif len(search_text) > 0:
        try:
            results = representative_manager.retrieve_representative_list(
                index_start=index_start,
                limit_to_this_state_code=limit_to_this_state_code,
                read_only=True,
                representatives_limit=number_requested,
                search_string=search_text,
                years_list=[year],
            )
            success = results['success']
            status = results['status']
            representative_list = results['representative_list']
            returned_count = results['returned_count']
            total_count = results['total_count']
        except Exception as e:
            status = 'FAILED representatives_query. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)
            success = False

    # Get all the office_held entries for representatives retrieved
    office_held_dict_list = []
    if success:
        office_held_we_vote_id_list = []
        for one_representative in representative_list:
            if positive_value_exists(one_representative.office_held_we_vote_id) \
                    and one_representative.office_held_we_vote_id not in office_held_we_vote_id_list:
                office_held_we_vote_id_list.append(one_representative.office_held_we_vote_id)
        if len(office_held_we_vote_id_list) > 0:
            results = generate_office_held_dict_list_from_office_held_we_vote_id_list(
                office_held_we_vote_id_list=office_held_we_vote_id_list)
            status += results['status']
            if results['success']:
                office_held_dict_list.append(results['office_held_dict_list'])

    if success:
        for representative in representative_list:
            results = generate_representative_dict_from_representative_object(representative=representative)
            status += results['status']
            if results['success']:
                representative_dict_list.append(results['representative_dict'])

        if len(representative_dict_list):
            status += 'REPRESENTATIVES_RETRIEVED '
        else:
            status += 'NO_REPRESENTATIVES_RETRIEVED '

    json_data = {
        'index_start':      index_start,
        'kind':             'wevote#representativesQuery',
        'office_held_list': office_held_dict_list,
        'representatives':  representative_dict_list,
        'returned_count':   returned_count,
        'state':            limit_to_this_state_code,
        'status':           status,
        'success':          success,
        'total_count':      total_count,
        'year':             year,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_representatives_retrieve_for_api(
        voter_device_id,
        incoming_status = '',
        ):
    """
    Request the ballot data requested by the voter
    :param incoming_status:
    :param voter_device_id:
    :return:
    """
    status = incoming_status

    error_json_data = {
        'status':                               status,
        'success':                              False,
        'office_held_list_found':                         False,
        'office_held_list':                     [],
        'ballot_location_display_name':         '',
        'is_from_substituted_address':          False,
        'next_national_election_day_text':      '',
        'original_text_city':                   '',
        'original_text_state':                  '',
        'original_text_zip':                    '',
        'polling_location_we_vote_id_source':   '',
        'substituted_address_nearby':           '',
        'substituted_address_city':             '',
        'substituted_address_state':            '',
        'substituted_address_zip':              '',
        'text_for_map_search':                  '',
        'voter_device_id':                      voter_device_id,
        'voter_device_id_not_valid':            False,
    }

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if not voter_device_link_results['voter_device_link_found']:
        status += "VALID_VOTER_DEVICE_ID_MISSING "
        # If the retrieve had no errors, a voter_device_id was passed in, but voter_device_link_found is False,
        # tell the WebApp the voter_device_id might need to be replaced.
        voter_device_id_not_valid = \
            positive_value_exists(voter_device_id) and positive_value_exists(voter_device_link_results['success'])
        error_json_data['status'] = status
        error_json_data['voter_device_id_not_valid'] = voter_device_id_not_valid
        return error_json_data

    voter_device_link = voter_device_link_results['voter_device_link']
    voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        status += " " + "VALID_VOTER_ID_MISSING"
        error_json_data['voter_device_id'] = voter_device_id
        return error_json_data

    voter_address_manager = VoterAddressManager()
    voter_address_id = 0
    address_type = BALLOT_ADDRESS
    voter_address_results = voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)
    status += " " + voter_address_results['status']
    # Note that this might be an empty VoterAddress object
    voter_address = voter_address_results['voter_address']
    text_for_map_search = ''
    if voter_address and hasattr(voter_address, 'text_for_map_search'):
        text_for_map_search = voter_address.text_for_map_search
    if positive_value_exists(voter_address_results['voter_address_has_value']):
        ballot_retrieval_based_on_voter_address = True
    else:
        ballot_retrieval_based_on_voter_address = False

    # json_data = voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id,
    #                                                 ballot_returned_we_vote_id, ballot_location_shortcut)
    json_data = error_json_data  # TEMP

    return json_data
