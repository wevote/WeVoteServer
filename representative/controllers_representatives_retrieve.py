# representative/controllers_representatives_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime
from django.db.models import Q
from django.http import HttpResponse
from exception.models import handle_exception
import json

from candidate.models import PROFILE_IMAGE_TYPE_UNKNOWN, PROFILE_IMAGE_TYPE_UPLOADED
from config.environment_variable_functions import get_environment_variable
from office_held.controllers import generate_office_held_dict_from_office_held_object, \
    generate_office_held_dict_list_from_office_held_we_vote_id_list
from office_held.models import OfficeHeld, OfficeHeldManager
from import_export_google_civic.controllers_representatives import REPRESENTATIVES_BY_ADDRESS_URL, \
    retrieve_remote_representatives_from_location_api
from voter.constants import MINIMUM_ADDRESS_LENGTH_TO_HAVE_STREET_ADDRESS
from voter.models import BALLOT_ADDRESS, VoterAddressManager, VoterDeviceLinkManager, VoterManager, \
    fetch_voter_we_vote_id_from_voter_id
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE
import wevote_functions.admin
from wevote_functions.functions import add_period_to_middle_name_initial, add_period_to_name_prefix_and_suffix, \
    convert_to_int, convert_to_political_party_constant, positive_value_exists, process_request_from_master, \
    remove_period_from_middle_name_initial, remove_period_from_name_prefix_and_suffix
from wevote_functions.functions_date import DATE_FORMAT_YMD_HMS, get_current_date_as_integer, \
    get_current_year_as_integer
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
        representative_dict = generate_representative_dict_from_representative_object(representative=representative_object)
        representative_dict_list.append(representative_dict)

    results = {
        'representative_dict_list': representative_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def generate_representative_dict_from_representative_object(representative):
    date_last_updated = ''
    if positive_value_exists(representative.date_last_updated):
        date_last_updated = representative.date_last_updated.strftime(DATE_FORMAT_YMD_HMS)  # '%Y-%m-%d %H:%M:%S'
    representative_dict = {
        'ballot_item_display_name':     representative.display_representative_name(),
        'facebook_url':                 representative.facebook_url
        if not representative.facebook_url_is_broken else '',
        'id':                           representative.id,
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
        'office_held_district_name':    representative.office_held_district_name,
        'office_held_id':               representative.office_held_id,
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
        'twitter_description':          representative.twitter_description
        if positive_value_exists(representative.twitter_description) and
        len(representative.twitter_description) > 1 else '',
        'twitter_followers_count':      representative.twitter_followers_count,
        'twitter_handle':               representative.fetch_twitter_handle(),
        'twitter_url':                  representative.twitter_url,
        'vote_usa_office_id':           representative.vote_usa_office_id,
        'vote_usa_politician_id':       representative.vote_usa_politician_id,
        'we_vote_id':                   representative.we_vote_id,
        'wikipedia_url':                representative.wikipedia_url,
        # I'm not sure we need this in WebApp
        # 'year_in_office_2023':          representative.year_in_office_2023,
        # 'year_in_office_2024':          representative.year_in_office_2024,
        # 'year_in_office_2025':          representative.year_in_office_2025,
        # 'year_in_office_2026':          representative.year_in_office_2026,
        # 'year_in_office_2027':          representative.year_in_office_2027,
        # 'year_in_office_2028':          representative.year_in_office_2028,
        # 'year_in_office_2029':          representative.year_in_office_2029,
        # 'year_in_office_2030':          representative.year_in_office_2030,
        'youtube_url':                  representative.youtube_url,
    }
    return representative_dict


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
            representative_dict = generate_representative_dict_from_representative_object(representative=representative)
            representative_dict_list.append(representative_dict)

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


def voter_representatives_retrieve_for_api(  # voterRepresentativesRetrieve
        voter_device_id,
        incoming_status = '',
        ):
    """
    Request the ballot data requested by the voter
    :param incoming_status:
    :param voter_device_id:
    :return:
    """
    offices_held_for_location_id = 0
    state_code = ''
    status = incoming_status
    text_for_map_search = ''

    default_dict_results = {
        'offices_held_for_location_found':      False,
        'offices_held_for_location_id':         offices_held_for_location_id,
        'office_held_list_found':               False,
        'office_held_list':                     [],
        'is_from_substituted_address':          False,
        'state_code':                           state_code,
        'status':                               status,
        'success':                              False,
        'text_for_map_search':                  text_for_map_search,
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
        dict_results = default_dict_results
        dict_results['status'] = status
        dict_results['voter_device_id_not_valid'] = voter_device_id_not_valid
        return dict_results

    voter_device_link = voter_device_link_results['voter_device_link']
    voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        status += " " + "VALID_VOTER_ID_MISSING"
        dict_results = default_dict_results
        dict_results['voter_device_id'] = voter_device_id
        return dict_results

    voter_we_vote_id = fetch_voter_we_vote_id_from_voter_id(voter_id)

    results = retrieve_or_generate_offices_held_for_location_for_voter(
        voter_device_link,
        voter_id,
        voter_we_vote_id,
    )
    json_data = default_dict_results
    json_data['status'] = results['status']
    json_data['success'] = results['success']
    json_data['offices_held_for_location_id'] = results['offices_held_for_location_id']
    json_data['offices_held_for_location_found'] = results['offices_held_for_location_found']
    existing_offices_held_by_vote_usa_office_id_dict = results['existing_offices_held_by_vote_usa_office_id_dict']
    existing_representatives_by_office_and_name_dict = results['existing_representatives_by_office_and_name_dict']
    offices_held_for_location = results['offices_held_for_location']

    # Create the response package for voterRepresentativesRetrieve based on offices_held_for_location
    results = generate_office_held_list_from_object_list(
        offices_held_for_location=offices_held_for_location,
        existing_offices_held_by_vote_usa_office_id_dict=existing_offices_held_by_vote_usa_office_id_dict,
        existing_representatives_by_office_and_name_dict=existing_representatives_by_office_and_name_dict,
    )
    if results['office_held_list_found']:
        json_data['office_held_list'] = results['office_held_list']
        json_data['office_held_list_found'] = True

    return json_data

def generate_office_held_list_from_object_list(
        offices_held_for_location=None,
        existing_offices_held_by_vote_usa_office_id_dict=None,
        existing_representatives_by_office_and_name_dict=None,
    ):
    default_dict_results = {
        'office_held_list': [],
        'office_held_list_found': False,
        'status': '',
        'success': False,
    }
    office_held_list_found = False
    status = ""
    success = True

    # Loop through entries in existing_offices_held_by_vote_usa_office_id_dict with
    #  key being vote_usa_office_id and value being the OfficeHeld object
    dict_results = default_dict_results
    for vote_usa_office_id, office_held_object in existing_offices_held_by_vote_usa_office_id_dict.items():
        office_held_list_found = True
        one_office_dict = generate_office_held_dict_from_office_held_object(office_held_object)

        try:
            office_held_we_vote_id = office_held_object.office_held_we_vote_id
        except Exception:
            try:
                office_held_we_vote_id = office_held_object['office_held_we_vote_id']
            except Exception:
                try:
                    office_held_we_vote_id = office_held_object.we_vote_id
                except Exception:
                    try:
                        office_held_we_vote_id = office_held_object['we_vote_id']
                    except Exception:
                        office_held_we_vote_id = ''
        representatives_dict = existing_representatives_by_office_and_name_dict.get(office_held_we_vote_id, {})
        representative_list = []
        for representative_object in representatives_dict.values():
            one_representatives_dict = generate_representative_dict_from_representative_object(representative_object)
            representative_list.append(one_representatives_dict)

        one_office_dict['representative_list'] = representative_list
        dict_results['office_held_list'].append(one_office_dict)

    dict_results['office_held_list_found'] = office_held_list_found
    dict_results['status'] = status
    dict_results['success'] = success
    return dict_results


def retrieve_or_generate_offices_held_for_location_for_voter(
        voter_device_link,
        voter_id,
        voter_we_vote_id,
    ):
    date_as_integer = get_current_date_as_integer()
    year_as_integer = get_current_year_as_integer()
    offices_held_for_location = None
    offices_held_for_location_id = ''
    offices_held_for_location_found = False
    state_code = ''
    status = ""
    text_for_map_search = ''

    default_dict_results = {
        'existing_offices_held_by_vote_usa_office_id_dict': {},
        'existing_representatives_by_office_and_name_dict': {},
        'offices_held_for_location':        None,
        'offices_held_for_location_id':     offices_held_for_location_id,
        'offices_held_for_location_found':  False,
        'state_code':                       state_code,
        'status':                           status,
        'success':                          False,
        'text_for_map_search':              text_for_map_search,
    }

    if not positive_value_exists(voter_we_vote_id):
        status += "VOTER_NOT_PASSED_IN "
        dict_results = default_dict_results
        dict_results['status'] = status
        return dict_results

    dict_results = default_dict_results
    voter_address_manager = VoterAddressManager()
    voter_address_id = 0
    address_type = BALLOT_ADDRESS
    voter_address_results = voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)
    status += " " + voter_address_results['status']
    # Note that this might be an empty VoterAddress object
    voter_address = voter_address_results['voter_address']
    if voter_address and hasattr(voter_address, 'text_for_map_search'):
        state_code = voter_address.get_state_code()
        dict_results['state_code'] = state_code
        text_for_map_search = voter_address.text_for_map_search
        dict_results['text_for_map_search'] = text_for_map_search
    if positive_value_exists(voter_address_results['voter_address_has_value']):
        offices_held_based_on_voter_address = True
    else:
        offices_held_based_on_voter_address = False

    # This code finds representatives saved for this voter for today
    required_variables_to_find_representatives = \
        positive_value_exists(date_as_integer) and \
        positive_value_exists(text_for_map_search) and \
        positive_value_exists(voter_we_vote_id)
    if not required_variables_to_find_representatives:
        status += "MISSING_REQUIRED_VARIABLES:: "
        status += f"date_as_integer: {date_as_integer}, "
        status += f"text_for_map_search: {text_for_map_search} "
        status += f"voter_we_vote_id: {voter_we_vote_id} "
        status += ":: "
        dict_results['status'] = status
        return dict_results

    # See if we have already stored the representatives for this voter for today, and if so,
    #  return those.
    if positive_value_exists(date_as_integer) and positive_value_exists(state_code) \
            and positive_value_exists(voter_we_vote_id):
        office_held_manager = OfficeHeldManager()
        results = office_held_manager.retrieve_offices_held_for_location(
            date_as_integer=date_as_integer,
            state_code=state_code,
            voter_we_vote_id=voter_we_vote_id,
        )
        status += results['status']
        if results['offices_held_for_location_found']:
            # We need to generate the following two dictionaries
            offices_held_for_location = results['offices_held_for_location']
            office_held_we_vote_id_list = []
            for index in range(1, 31):
                office_held_we_vote_id = getattr(offices_held_for_location, f'office_held_we_vote_id_{index:02d}')
                if positive_value_exists(office_held_we_vote_id):
                    office_held_we_vote_id_list.append(office_held_we_vote_id)
            if positive_value_exists(len(office_held_we_vote_id_list)):
                # Get OfficeHeld objects so we can use them to generate the voterRepresentativesRetrieve API
                try:
                    queryset = OfficeHeld.objects.using('readonly').all()
                    queryset = queryset.filter(we_vote_id__in=office_held_we_vote_id_list)
                    office_held_list = list(queryset)
                    # Loop through office_held_list and create a dictionary
                    #  that uses office_held.vote_usa_office_id as the key and office_held as the value
                    existing_offices_held_by_vote_usa_office_id_dict = {}
                    for office_held in office_held_list:
                        existing_offices_held_by_vote_usa_office_id_dict[office_held.vote_usa_office_id] = office_held
                    dict_results['existing_offices_held_by_vote_usa_office_id_dict'] = \
                        existing_offices_held_by_vote_usa_office_id_dict
                except Exception as e:
                    status += "EXCEPTION_RETRIEVING_OFFICES_HELD: " + str(e) + " "

                # Get Representatives objects so we can use them to generate the voterRepresentativesRetrieve API
                try:
                    years_list = [year_as_integer]
                    representative_manager = RepresentativeManager()
                    rep_results = representative_manager.retrieve_representative_list(
                        office_held_we_vote_id_list=office_held_we_vote_id_list,
                        read_only=True,
                        years_list=years_list,
                    )
                    representative_list = []
                    if rep_results['representative_list_found']:
                        representative_list = rep_results['representative_list']

                    # Loop through representative_list and create a dictionary
                    #  that uses representative.office_held_we_vote_id as the first key and
                    #  representative.representative_name as the second key, with representative as the value
                    existing_representatives_by_office_and_name_dict = {}
                    for representative in representative_list:
                        if representative.office_held_we_vote_id not in \
                                existing_representatives_by_office_and_name_dict:
                            existing_representatives_by_office_and_name_dict[representative.office_held_we_vote_id] = {}
                        if representative.representative_name not in \
                                existing_representatives_by_office_and_name_dict[representative.office_held_we_vote_id]:
                            existing_representatives_by_office_and_name_dict\
                                [representative.office_held_we_vote_id][representative.representative_name] = \
                                representative

                    dict_results['existing_representatives_by_office_and_name_dict'] = \
                        existing_representatives_by_office_and_name_dict
                except Exception as e:
                    status += "EXCEPTION_RETRIEVING_REPRESENTATIVES: " + str(e) + " "

            dict_results['offices_held_for_location'] = offices_held_for_location
            dict_results['offices_held_for_location_found'] = results['offices_held_for_location_found']
            dict_results['status'] = status
            dict_results['success'] = True
            return dict_results

    # If here, then we need to either:
    # 1) Retrieve representatives from Vote-USA, Ballotpedia or Google Civic for VoterAddress
    #    if we have full address
    # 2) Find representatives from a nearby map point address, previously retrieved and cached within We Vote
    # ...and generate local OfficesHeldForLocation entry for today for later retrieves.
    results = generate_offices_held_for_location_for_voter(
        state_code=state_code,
        text_for_map_search=text_for_map_search,
        voter_we_vote_id=voter_we_vote_id,
    )
    status += results['status']
    if results['offices_held_for_location_found']:
        dict_results['existing_offices_held_by_vote_usa_office_id_dict'] = \
            results['existing_offices_held_by_vote_usa_office_id_dict']
        dict_results['existing_representatives_by_office_and_name_dict'] = \
            results['existing_representatives_by_office_and_name_dict']
        dict_results['offices_held_for_location'] = results['offices_held_for_location']
        dict_results['offices_held_for_location_found'] = results['offices_held_for_location_found']
        dict_results['status'] = status
        dict_results['success'] = True
        return dict_results

    status += "REPRESENTATIVES_NOT_FOUND_OR_GENERATED "
    dict_results['status'] = status
    dict_results['success'] = True
    return dict_results


def generate_offices_held_for_location_for_voter(
        state_code=None,
        text_for_map_search=None,
        voter_we_vote_id=None,
    ):
    existing_offices_held_by_vote_usa_office_id_dict = {}
    existing_representatives_by_office_and_name_dict = {}
    offices_held_for_location = None
    offices_held_for_location_id = ''
    offices_held_for_location_found = False
    status = ''

    # #########################################################################
    # 1) Retrieve representatives from Vote-USA if we have full address
    length_of_text_for_map_search = 0
    if isinstance(text_for_map_search, str):
        length_of_text_for_map_search = len(text_for_map_search)
    if length_of_text_for_map_search > MINIMUM_ADDRESS_LENGTH_TO_HAVE_STREET_ADDRESS:
        status += "TEXT_FOR_MAP_SEARCH_LONG_ENOUGH "

        update_or_create_rules = {
            'create_office_helds':      True,
            'create_representatives':   True,
            'update_office_helds':      False,
            'update_representatives':   False,
        }

        failed_representatives_api_call = 0
        reps_not_returned_from_this_voter_we_vote_id = []
        reps_returned_from_this_voter_we_vote_id = []
        successful_representatives_api_call = 0
        one_location_results = retrieve_remote_representatives_from_location_api(
            state_code=state_code,
            text_for_map_search=text_for_map_search,
            update_or_create_rules=update_or_create_rules,
            voter_we_vote_id=voter_we_vote_id,
        )

        if one_location_results and 'success' in one_location_results and one_location_results['success']:
            offices_held_for_location = one_location_results['offices_held_for_location']
            offices_held_for_location_found = one_location_results['offices_held_for_location_found']
            offices_held_for_location_id = one_location_results['offices_held_for_location_id']
            success = True

        existing_offices_held_by_ocd_and_name_dict = \
            one_location_results['existing_offices_held_by_ocd_and_name_dict']
        existing_offices_held_by_vote_usa_office_id_dict = \
            one_location_results['existing_offices_held_by_vote_usa_office_id_dict']
        existing_representatives_by_office_and_name_dict = one_location_results['existing_representatives_by_office_and_name_dict']
        new_office_held_we_vote_ids_list = one_location_results['new_office_held_we_vote_ids_list']
        new_representative_we_vote_ids_list = one_location_results['new_representative_we_vote_ids_list']

        if one_location_results['successful_representatives_api_call']:
            successful_representatives_api_call += 1
            reps_returned_from_this_voter_we_vote_id.append(voter_we_vote_id)
            if successful_representatives_api_call < 5 and positive_value_exists(one_location_results['status']):
                # Only show this error message status for the first 4 times, so we don't overwhelm the log
                status += "REPRESENTATIVES_RETRIEVED: [[[" + one_location_results['status'] + "]]] "
        else:
            failed_representatives_api_call += 1
            reps_not_returned_from_this_voter_we_vote_id.append(voter_we_vote_id)
            if failed_representatives_api_call < 5 and positive_value_exists(one_location_results['status']):
                # Only show this error message status for the first 4 times, so we don't overwhelm the log
                status += "REPRESENTATIVES_NOT_RETRIEVED: [[[" + one_location_results['status'] + "]]] "
        if positive_value_exists(len(reps_returned_from_this_voter_we_vote_id)):
            status += "reps_returned_from_this_voter_we_vote_id: " + \
                      str(reps_returned_from_this_voter_we_vote_id) + " "
        if positive_value_exists(len(reps_not_returned_from_this_voter_we_vote_id)):
            status += "reps_not_returned_from_this_voter_we_vote_id: " + \
                      str(reps_not_returned_from_this_voter_we_vote_id) + " "

    # #########################################################################
    # 2) Find representatives from a nearby map point address, previously retrieved and cached within We Vote
    # ...and generate local OfficesHeldForLocation entry for today for later retrieves.

    results = {
        'existing_offices_held_by_vote_usa_office_id_dict': existing_offices_held_by_vote_usa_office_id_dict,
        'existing_representatives_by_office_and_name_dict': existing_representatives_by_office_and_name_dict,
        'status':                           status,
        'success':                          True,
        'offices_held_for_location':        offices_held_for_location,
        'offices_held_for_location_id':     offices_held_for_location_id,
        'offices_held_for_location_found':  offices_held_for_location_found,
    }
    return results
