# representative/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import PROFILE_IMAGE_TYPE_UNKNOWN, PROFILE_IMAGE_TYPE_UPLOADED
from config.base import get_environment_variable
from datetime import datetime
from django.db.models import Q
from django.http import HttpResponse
from exception.models import handle_exception
import json
from office_held.controllers import generate_office_held_dict_list_from_office_held_we_vote_id_list
from politician.models import PoliticianManager
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE
import wevote_functions.admin
from wevote_functions.functions import add_period_to_middle_name_initial, add_period_to_name_prefix_and_suffix, \
    convert_to_int, convert_to_political_party_constant, positive_value_exists, process_request_from_master, \
    remove_period_from_middle_name_initial, remove_period_from_name_prefix_and_suffix
from .models import Representative, RepresentativeManager, REPRESENTATIVE_UNIQUE_IDENTIFIERS

logger = wevote_functions.admin.get_logger(__name__)

REPRESENTATIVE_SYNC_URL = "https://api.wevoteusa.org/apis/v1/representativesSyncOut/"
# REPRESENTATIVE_SYNC_URL = "http://localhost:8001/apis/v1/representativesSyncOut/"
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")


def add_value_to_next_representative_spot(
        field_name_base='',
        look_at_alternate_names=False,
        representative=None,
        new_value_to_add=''):
    """
    This function can be used with Representative, CandidateCampaign and Politician
    :param field_name_base:
    :param look_at_alternate_names:
    :param representative:
    :param new_value_to_add:
    :return:
    """
    field_updated = ''
    status = ''
    success = True
    values_changed = False
    if not positive_value_exists(new_value_to_add):
        status += 'NEW_VALUE_OR_FIELD_NAME_MISSING-(' + str(new_value_to_add) + "/" + str(field_name_base) + ')'
        return {
            'field_updated':    field_updated,
            'representative':   representative,
            'status':           status,
            'success':          False,
            'values_changed':   values_changed,
        }

    name_changed = False
    new_value_modified = "IGNORE_NO_NAME"
    if positive_value_exists(look_at_alternate_names):
        # If an initial exists in the name (ex/ " A "), then search for the name
        # with a period added (ex/ " A. ") We check for an exact match AND a match with/without initial + period
        # new_value
        new_value_new_start = new_value_to_add  # For prefix/suffixes
        add_results = add_period_to_middle_name_initial(new_value_to_add)
        if add_results['name_changed']:
            name_changed = True
            new_value_modified = add_results['modified_name']
            new_value_new_start = new_value_modified
        else:
            add_results = remove_period_from_middle_name_initial(new_value_to_add)
            if add_results['name_changed']:
                name_changed = True
                new_value_modified = add_results['modified_name']
                new_value_new_start = new_value_modified

        # Deal with prefix and suffix
        # If a prefix or suffix exists in the name (ex/ " JR"), then search for the name
        # with a period added (ex/ " JR.")
        add_results = add_period_to_name_prefix_and_suffix(new_value_new_start)
        if add_results['name_changed']:
            name_changed = True
            new_value_modified = add_results['modified_name']
        else:
            add_results = remove_period_from_name_prefix_and_suffix(new_value_new_start)
            if add_results['name_changed']:
                name_changed = True
                new_value_modified = add_results['modified_name']

    current_value1 = getattr(representative, field_name_base, '')
    current_value2 = getattr(representative, field_name_base + '2', '')
    current_value3 = getattr(representative, field_name_base + '3', '')
    current_value4 = getattr(representative, field_name_base + '4', '')
    current_value5 = getattr(representative, field_name_base + '5', '')
    if not positive_value_exists(current_value1):
        setattr(representative, field_name_base, new_value_to_add)
        field_updated = field_name_base
        if field_name_base in \
                ['candidate_twitter_handle', 'politician_twitter_handle', 'representative_twitter_handle']:
            representative.twitter_handle_updates_failing = False
        values_changed = True
    elif new_value_to_add.lower() == current_value1.lower():
        # The value is already stored in current_value1 so doesn't need
        # to be added anywhere below
        pass
    elif name_changed and current_value1.lower() == new_value_modified.lower():
        # If current_value1 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif not positive_value_exists(current_value2):
        setattr(representative, field_name_base + '2', new_value_to_add)
        field_updated = field_name_base + '2'
        if field_name_base in \
                ['candidate_twitter_handle2', 'politician_twitter_handle2', 'representative_twitter_handle2']:
            representative.twitter_handle2_updates_failing = False
        values_changed = True
    elif new_value_to_add.lower() == current_value2.lower():
        # The value is already stored in current_value2 so doesn't need
        # to be added to current_value3
        pass
    elif name_changed and current_value2.lower() == new_value_modified.lower():
        # If representative.google_civic_candidate_name2 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif not positive_value_exists(current_value3):
        setattr(representative, field_name_base + '3', new_value_to_add)
        field_updated = field_name_base + '3'
        values_changed = True
    elif new_value_to_add.lower() == current_value3.lower():
        # The value is already stored in representative.google_civic_candidate_name3 so doesn't need
        # to be added to representative.google_civic_candidate_name3
        pass
    elif name_changed and current_value3.lower() == new_value_modified.lower():
        # If representative.google_civic_candidate_name3 has a middle initial with/without a period
        # don't store it if the alternate without/with the period already is stored
        pass
    elif field_name_base in ['politician_twitter_handle']:
        # 2024-01-19 We support:
        # politician_twitter_handle4, politician_twitter_handle5
        # We do not currently support for a 4th or 5th name:
        # google_civic_candidate_name4, google_civic_candidate_name5
        # representative_twitter_handle4, representative_twitter_handle5
        if not positive_value_exists(current_value4):
            setattr(representative, field_name_base + '4', new_value_to_add)
            field_updated = field_name_base + '4'
            values_changed = True
        elif new_value_to_add.lower() == current_value4.lower():
            # The value is already stored in representative.google_civic_candidate_name4 so doesn't need
            # to be added to representative.google_civic_candidate_name4
            pass
        elif name_changed and current_value4.lower() == new_value_modified.lower():
            # If representative.google_civic_candidate_name4 has a middle initial with/without a period
            # don't store it if the alternate without/with the period already is stored
            pass
        elif not positive_value_exists(current_value5):
            setattr(representative, field_name_base + '5', new_value_to_add)
            field_updated = field_name_base + '5'
            values_changed = True
        else:
            status += "{field_name_base}5 FULL-COULD_NOT_STORE_VALUE ".format(field_name_base=field_name_base)
    else:
        status += "{field_name_base}4 NOT_SUPPORTED_FOR_THIS_OBJECT ".format(field_name_base=field_name_base)
    return {
        'field_updated':    field_updated,
        'representative':   representative,
        'success':          success,
        'status':           status,
        'values_changed':   values_changed,
    }


def add_value_to_next_representative_spot_wrapper(
        field_name_base='',
        look_at_alternate_names=False,
        representative=None,
        new_value_to_add1='',
        new_value_to_add2='',
        new_value_to_add3=''):
    success = True
    status = ""
    values_changed = False
    if positive_value_exists(new_value_to_add1):
        results = add_value_to_next_representative_spot(
            field_name_base=field_name_base,
            look_at_alternate_names=look_at_alternate_names,
            new_value_to_add=new_value_to_add1,
            representative=representative,
        )
        if results['success'] and results['values_changed']:
            representative = results['representative']
            values_changed = True
        if not results['success']:
            status += results['status']
    if positive_value_exists(new_value_to_add2):
        results = add_value_to_next_representative_spot(
            field_name_base=field_name_base,
            look_at_alternate_names=look_at_alternate_names,
            new_value_to_add=new_value_to_add2,
            representative=representative,
        )
        if results['success'] and results['values_changed']:
            representative = results['representative']
            values_changed = True
        if not results['success']:
            status += results['status']
    if positive_value_exists(new_value_to_add3):
        results = add_value_to_next_representative_spot(
            field_name_base=field_name_base,
            look_at_alternate_names=look_at_alternate_names,
            new_value_to_add=new_value_to_add3,
            representative=representative,
        )
        if results['success'] and results['values_changed']:
            representative = results['representative']
            values_changed = True
        if not results['success']:
            status += results['status']

    return {
        'success':          success,
        'status':           status,
        'representative':   representative,
        'values_changed':   values_changed,
    }


def fetch_duplicate_representative_count(
        we_vote_representative=None,
        ignore_representative_we_vote_id_list=[]):
    if not hasattr(we_vote_representative, 'representative_name'):
        return 0

    if not positive_value_exists(we_vote_representative.representative_name):
        return 0

    representative_manager = RepresentativeManager()
    return representative_manager.fetch_representatives_from_non_unique_identifiers_count(
        ocd_division_id=we_vote_representative.ocd_division_id,
        representative_twitter_handle=we_vote_representative.representative_twitter_handle,
        representative_twitter_handle2=we_vote_representative.representative_twitter_handle2,
        representative_twitter_handle3=we_vote_representative.representative_twitter_handle3,
        representative_name=we_vote_representative.representative_name,
        state_code=we_vote_representative.state_code,
        ignore_representative_we_vote_id_list=ignore_representative_we_vote_id_list)


def figure_out_representative_conflict_values(representative1, representative2):
    representative_merge_conflict_values = {}

    for attribute in REPRESENTATIVE_UNIQUE_IDENTIFIERS:
        try:
            representative1_attribute_value = getattr(representative1, attribute)
            try:
                representative1_attribute_value_lower_case = representative1_attribute_value.lower()
            except Exception:
                representative1_attribute_value_lower_case = None
            representative2_attribute_value = getattr(representative2, attribute)
            try:
                representative2_attribute_value_lower_case = representative2_attribute_value.lower()
            except Exception:
                representative2_attribute_value_lower_case = None
            if representative1_attribute_value is None and representative2_attribute_value is None:
                representative_merge_conflict_values[attribute] = 'MATCHING'
            elif representative1_attribute_value is None or representative1_attribute_value == "":
                representative_merge_conflict_values[attribute] = 'REPRESENTATIVE2'
            elif representative2_attribute_value is None or representative2_attribute_value == "":
                representative_merge_conflict_values[attribute] = 'REPRESENTATIVE1'
            else:
                if attribute == "ballotpedia_representative_url" \
                        or attribute == "representative_contact_form_url" \
                        or attribute == "facebook_url" \
                        or attribute == "linkedin_url" \
                        or attribute == "wikipedia_url" \
                        or attribute == "youtube_url":
                    # If there is a link with 'http' in representative 2, and representative 1 doesn't have 'http',
                    #  use the one with 'http'
                    if 'http' in representative2_attribute_value and 'http' not in representative1_attribute_value:
                        representative_merge_conflict_values[attribute] = 'REPRESENTATIVE2'
                    elif representative1_attribute_value_lower_case == representative2_attribute_value_lower_case:
                        representative_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        representative_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "representative_name" \
                        or attribute == "state_code":
                    if representative1_attribute_value_lower_case == representative2_attribute_value_lower_case:
                        representative_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        representative_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "political_party":
                    if convert_to_political_party_constant(representative1_attribute_value) == \
                            convert_to_political_party_constant(representative2_attribute_value):
                        representative_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        representative_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    if representative1_attribute_value == representative2_attribute_value:
                        representative_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        representative_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            pass

    return representative_merge_conflict_values


def find_duplicate_representative(we_vote_representative, ignore_representative_we_vote_id_list, read_only=True):
    status = ''
    if not hasattr(we_vote_representative, 'representative_name'):
        status += "FIND_DUPLICATE_REPRESENTATIVE_MISSING_REPRESENTATIVE_OBJECT "
        error_results = {
            'success':                                  False,
            'status':                                   status,
            'representative_merge_possibility_found':   False,
            'representative_list':                      [],
        }
        return error_results

    representative_list_manager = RepresentativeManager()
    try:
        representative_twitter_handle_list = []
        if positive_value_exists(we_vote_representative.representative_twitter_handle):
            representative_twitter_handle_list.append(we_vote_representative.representative_twitter_handle)
        if positive_value_exists(we_vote_representative.representative_twitter_handle2):
            representative_twitter_handle_list.append(we_vote_representative.representative_twitter_handle2)
        if positive_value_exists(we_vote_representative.representative_twitter_handle3):
            representative_twitter_handle_list.append(we_vote_representative.representative_twitter_handle3)
        results = representative_list_manager.retrieve_representatives_from_non_unique_identifiers(
            ignore_representative_we_vote_id_list=ignore_representative_we_vote_id_list,
            ocd_division_id=we_vote_representative.ocd_division_id,
            representative_name=we_vote_representative.representative_name,
            twitter_handle_list=representative_twitter_handle_list,
            state_code=we_vote_representative.state_code,
            read_only=read_only,
        )

        if results['representative_found']:
            status += "FIND_DUPLICATE_REPRESENTATIVE_DUPLICATE_FOUND "
            representative_merge_conflict_values = \
                figure_out_representative_conflict_values(we_vote_representative, results['representative'])

            results = {
                'success':                                  True,
                'status':                                   status,
                'representative_merge_possibility_found':   True,
                'representative_merge_possibility':         results['representative'],
                'representative_merge_conflict_values':     representative_merge_conflict_values,
                'representative_list':                      results['representative_list'],
            }
            return results
        elif results['representative_list_found']:
            # Only deal with merging the incoming representative and the first on found
            status += "FIND_DUPLICATE_REPRESENTATIVE_DUPLICATE_LIST_FOUND "
            representative_merge_conflict_values = \
                figure_out_representative_conflict_values(we_vote_representative, results['representative_list'][0])

            results = {
                'success':                              True,
                'status':                                   status,
                'representative_merge_possibility_found':    True,
                'representative_merge_possibility':          results['representative_list'][0],
                'representative_merge_conflict_values':      representative_merge_conflict_values,
                'representative_list':                       results['representative_list'],
            }
            return results
        else:
            status += results['status']
            status += "FIND_DUPLICATE_REPRESENTATIVE_NO_DUPLICATES_FOUND "
            results = {
                'success':                                  True,
                'status':                                   status,
                'representative_merge_possibility_found':   False,
                'representative_list':                      results['representative_list'],
            }
            return results

    except Exception as e:
        status += "ERROR_IN_FIND_DUPLICATES: " + str(e) + " "
        success = False

    status += "FIND_DUPLICATE_REPRESENTATIVE_NO_DUPLICATES_FOUND "
    results = {
        'success':                                  success,
        'status':                                   status,
        'representative_merge_possibility_found':   False,
        'representative_list':                      [],
    }
    return results


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
        date_last_updated = representative.date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
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
        'wikipedia_url':                representative.wikipedia_url,
        'year_in_office_2023':          representative.year_in_office_2023,
        'year_in_office_2024':          representative.year_in_office_2024,
        'year_in_office_2025':          representative.year_in_office_2025,
        'year_in_office_2026':          representative.year_in_office_2026,
        'youtube_url':                  representative.youtube_url,
    }

    results = {
        'representative_dict':  representative_dict,
        'status':               status,
        'success':              success,
    }
    return results


def match_representatives_to_politicians_first_attempt(state_code=''):
    """
    Find any 50 representatives with politician_match_attempted == False, and attempt to match them to:
    a) existing politician
    b) or create new politician (we can deduplicate later)
    :param state_code:
    :return:
    """
    queryset = Representative.objects.all()
    queryset = queryset.filter(politician_match_attempted=False)
    queryset = queryset.filter(Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=""))
    if positive_value_exists(state_code):
        queryset = queryset.filter(state_code__iexact=state_code)
    representative_list = list(queryset[:50])
    num_representatives_reviewed = 0
    new_politicians_created = 0
    existing_politician_found = 0
    multiple_politicians_found = 0
    other_results = 0
    status = ""
    success = True

    status += "About to loop through up to 50 representatives to match to a politician record. "

    # Loop through all the representatives from this year
    for we_vote_representative in representative_list:
        num_representatives_reviewed += 1
        match_results = representative_politician_match(we_vote_representative)
        if match_results['politician_created']:
            new_politicians_created += 1
        elif match_results['politician_found']:
            existing_politician_found += 1
        elif match_results['politician_list_found']:
            multiple_politicians_found += 1
        else:
            other_results += 1
        if not match_results['success']:
            status += match_results['status']
        try:
            we_vote_representative.politician_match_attempted = True
            we_vote_representative.save()
        except Exception as e:
            status += "FAILED-POLITICIAN_MATCH_ATTEMPTED: " + str(e) + " "

    results = {
        'multiple_possible_politicians_found':  multiple_politicians_found,
        'matched_to_existing_politician':       existing_politician_found,
        'new_politicians_created':              new_politicians_created,
        'number_of_representatives_reviewed':   num_representatives_reviewed,
        'success':                              success,
        'status':                               status,
    }
    return results


def merge_if_duplicate_representatives(representative1_on_stage, representative2_on_stage, conflict_values):
    success = False
    status = "MERGE_IF_DUPLICATE_REPRESENTATIVES "
    representatives_merged = False
    decisions_required = False
    representative1_we_vote_id = representative1_on_stage.we_vote_id
    representative2_we_vote_id = representative2_on_stage.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    for attribute in REPRESENTATIVE_UNIQUE_IDENTIFIERS:
        # With the following fields from REPRESENTATIVE_UNIQUE_IDENTIFIERS, we
        # don't let a difference between any of these representative1 values vs representative2 values
        # stop us from auto-merging because they are all copied from other "master" tables.
        if attribute == "office_held_name" \
                or attribute == "twitter_description" \
                or attribute == "twitter_followers_count" \
                or attribute == "twitter_location" \
                or attribute == "twitter_name" \
                or attribute == "twitter_profile_background_image_url_https" \
                or attribute == "twitter_profile_banner_url_https" \
                or attribute == "twitter_profile_image_url_https" \
                or attribute == "twitter_url" \
                or attribute == "twitter_user_id" \
                or attribute == "we_vote_hosted_profile_image_url_large" \
                or attribute == "we_vote_hosted_profile_image_url_medium" \
                or attribute == "we_vote_hosted_profile_image_url_tiny":
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "REPRESENTATIVE2":
                # Use value from REPRESENTATIVE2
                merge_choices[attribute] = getattr(representative2_on_stage, attribute)
            elif positive_value_exists(getattr(representative1_on_stage, attribute)):
                # We can default to value in representative1, because it has a valid field
                pass
            elif positive_value_exists(getattr(representative2_on_stage, attribute)):
                # If we are here, representative1 does NOT have valid value, so we default to value representative2 has
                merge_choices[attribute] = getattr(representative2_on_stage, attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                decisions_required = True
                status += 'CONFLICT: ' + str(attribute) + ' '
            elif conflict_value == "REPRESENTATIVE2":
                merge_choices[attribute] = getattr(representative2_on_stage, attribute)

    if not decisions_required:
        status += "NO_DECISIONS_REQUIRED "
        merge_results = \
            merge_these_two_representatives(representative1_we_vote_id, representative2_we_vote_id, merge_choices)

        if merge_results['representatives_merged']:
            success = True
            representatives_merged = True

    results = {
        'success':                  success,
        'status':                   status,
        'representatives_merged':   representatives_merged,
        'decisions_required':       decisions_required,
        'representative':           representative1_on_stage,
    }
    return results


def merge_these_two_representatives(representative1_we_vote_id, representative2_we_vote_id, admin_merge_choices={}):
    """
    Process the merging of two representatives
    :param representative1_we_vote_id:
    :param representative2_we_vote_id:
    :param admin_merge_choices: Dictionary with the attribute name as the key, and the chosen value as the value
    :return:
    """
    status = ""
    representative_manager = RepresentativeManager()

    # Candidate 1 is the one we keep, and Candidate 2 is the one we will merge into Candidate 1
    representative1_results = representative_manager.retrieve_representative(
        representative_we_vote_id=representative1_we_vote_id,
        read_only=False)
    if representative1_results['representative_found']:
        representative1_on_stage = representative1_results['representative']
        representative1_id = representative1_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_REPRESENTATIVES-COULD_NOT_RETRIEVE_REPRESENTATIVE1 ",
            'representatives_merged': False,
            'representative': None,
        }
        return results

    representative2_results = \
        representative_manager.retrieve_representative(
            representative_we_vote_id=representative2_we_vote_id,
            read_only=False)
    if representative2_results['representative_found']:
        representative2_on_stage = representative2_results['representative']
        representative2_id = representative2_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_REPRESENTATIVES-COULD_NOT_RETRIEVE_REPRESENTATIVE2 ",
            'representatives_merged': False,
            'representative': None,
        }
        return results

    # Merge politician data
    politician1_we_vote_id = representative1_on_stage.politician_we_vote_id
    politician2_we_vote_id = representative2_on_stage.politician_we_vote_id
    if positive_value_exists(politician1_we_vote_id) and positive_value_exists(politician2_we_vote_id):
        if politician1_we_vote_id != politician2_we_vote_id:
            # Conflicting parent politicians
            # TODO: Call separate politician merge process
            results = {
                'success': False,
                'status': "MERGE_THESE_TWO_REPRESENTATIVES-UNABLE_TO_MERGE_PARENT_POLITICIANS ",
                'representatives_merged': False,
                'representative': None,
            }
            return results
            # else do nothing (same parent politician)
    elif positive_value_exists(politician2_we_vote_id):
        # Migrate politician from representative 2 to representative 1
        politician2_id = 0
        try:
            # get the politician_id directly to avoid bad data
            politician_manager = PoliticianManager()
            results = politician_manager.retrieve_politician(
                politician_we_vote_id=politician2_we_vote_id,
                read_only=True)
            if results['politician_found']:
                politician = results['politician']
                politician2_id = politician.id
        except Exception as e:
            status += "COULD_NOT_UPDATE_POLITICIAN_FOR_REPRESENTATIVE2 " + str(e) + " "
        representative1_on_stage.politician_we_vote_id = politician2_we_vote_id
        representative1_on_stage.politician_id = politician2_id
    # else do nothing (no parent politician for representative 2)

    # Merge attribute values chosen by the admin
    for attribute in REPRESENTATIVE_UNIQUE_IDENTIFIERS:
        # try:
        if attribute in admin_merge_choices:
            setattr(representative1_on_stage, attribute, admin_merge_choices[attribute])
        # except Exception as e:
        #     # Don't completely fail if in attribute can't be saved.
        #     status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "

    # Preserve unique google_civic_representative_name, _name2, and _name3
    results = add_value_to_next_representative_spot_wrapper(
        field_name_base='google_civic_representative_name',
        look_at_alternate_names=True,
        new_value_to_add1=representative2_on_stage.google_civic_representative_name,
        new_value_to_add2=representative2_on_stage.google_civic_representative_name2,
        new_value_to_add3=representative2_on_stage.google_civic_representative_name3,
        representative=representative1_on_stage,
    )
    if results['success'] and results['values_changed']:
        representative1_on_stage = results['representative']

    # Preserve unique representative_email, _email2, and _email3
    results = add_value_to_next_representative_spot_wrapper(
        field_name_base='representative_email',
        new_value_to_add1=representative2_on_stage.representative_email,
        new_value_to_add2=representative2_on_stage.representative_email2,
        new_value_to_add3=representative2_on_stage.representative_email3,
        representative=representative1_on_stage,
    )
    if results['success'] and results['values_changed']:
        representative1_on_stage = results['representative']

    # Preserve unique representative_phone, _phone2, and _phone3
    results = add_value_to_next_representative_spot_wrapper(
        field_name_base='representative_phone',
        new_value_to_add1=representative2_on_stage.representative_phone,
        new_value_to_add2=representative2_on_stage.representative_phone2,
        new_value_to_add3=representative2_on_stage.representative_phone3,
        representative=representative1_on_stage,
    )
    if results['success'] and results['values_changed']:
        representative1_on_stage = results['representative']

    # Preserve unique representative_twitter_handle, representative_twitter_handle2, and representative_twitter_handle3
    results = add_value_to_next_representative_spot_wrapper(
        field_name_base='representative_twitter_handle',
        new_value_to_add1=representative2_on_stage.representative_twitter_handle,
        new_value_to_add2=representative2_on_stage.representative_twitter_handle2,
        new_value_to_add3=representative2_on_stage.representative_twitter_handle3,
        representative=representative1_on_stage,
    )
    if results['success'] and results['values_changed']:
        representative1_on_stage = results['representative']

    # Preserve unique representative_url, _url2, and _url3
    results = add_value_to_next_representative_spot_wrapper(
        field_name_base='representative_url',
        new_value_to_add1=representative2_on_stage.representative_url,
        new_value_to_add2=representative2_on_stage.representative_url2,
        new_value_to_add3=representative2_on_stage.representative_url3,
        representative=representative1_on_stage,
    )
    if results['success'] and results['values_changed']:
        representative1_on_stage = results['representative']

    # #####################################
    # Deal with representative_to_office_link
    # We are going to keep representative1 linkages
    # representative1_office_we_vote_id_list = []
    # representative1_link_results = representative_manager.retrieve_representative_to_office_link(
    #         representative_we_vote_id=representative1_we_vote_id, read_only=False)
    # if positive_value_exists(representative1_link_results['success']):
    #     representative1_to_office_link_list = representative1_link_results['representative_to_office_link_list']
    #     # Cycle through the representative1 links and put the contest_office_we_vote_id's into a simple list
    #     for link in representative1_to_office_link_list:
    #         representative1_office_we_vote_id_list.append(link.contest_office_we_vote_id)
    # else:
    #     status += representative1_link_results['status']

    # We need to migrate representative2 linkages
    # representative2_to_office_link_list = []
    # representative2_link_results = representative_manager.retrieve_representative_to_office_link(
    #         representative_we_vote_id=representative2_we_vote_id, read_only=False)
    # if positive_value_exists(representative2_link_results['success']):
    #     representative2_to_office_link_list = representative2_link_results['representative_to_office_link_list']
    # else:
    #     status += representative1_link_results['status']

    # Cycle through the representative2 links. Either move them (if "to" link doesn't exist),
    # or delete if a "to" link exists
    # for representative2_link in representative2_to_office_link_list:
    #     if representative2_link.contest_office_we_vote_id in representative1_office_we_vote_id_list:
    #         representative2_link.delete()
    #     else:
    #         representative2_link.representative_we_vote_id = representative1_we_vote_id
    #         representative2_link.save()

    # Note: wait to wrap in try/except block
    representative1_on_stage.save()
    # 2021-10-16 Uses image data from master table which we aren't updating with the merge yet
    # refresh_representative_data_from_master_tables(representative1_on_stage.we_vote_id)

    # Remove representative 2
    representative2_on_stage.delete()

    results = {
        'success':                  True,
        'status':                   status,
        'representatives_merged':   True,
        'representative':           representative1_on_stage,
    }
    return results


def move_representatives_to_another_politician(
        from_politician_id=0,
        from_politician_we_vote_id='',
        to_politician_id=0,
        to_politician_we_vote_id=''):
    """

    :param from_politician_id:
    :param from_politician_we_vote_id:
    :param to_politician_id:
    :param to_politician_we_vote_id:
    :return:
    """
    status = ''
    success = True
    representatives_entries_moved = 0

    if positive_value_exists(from_politician_we_vote_id):
        try:
            representatives_entries_moved += Representative.objects \
                .filter(politician_we_vote_id__iexact=from_politician_we_vote_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_REPRESENTATIVES_BY_POLITICIAN_WE_VOTE_ID: " + str(e) + " "
            success = False

    if positive_value_exists(from_politician_id):
        try:
            representatives_entries_moved += Representative.objects \
                .filter(politician_id=from_politician_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_REPRESENTATIVES_BY_POLITICIAN_ID: " + str(e) + " "
            success = False

    results = {
        'status':                           status,
        'success':                          success,
        'representatives_entries_moved':  representatives_entries_moved,
    }
    return results


def deduplicate_politicians_first_attempt(state_code=''):
    merge_errors = 0
    multiple_possible_politicians_found = 0
    no_merge_options_found = 0
    number_of_politicians_reviewed = 0
    decisions_required = 0
    politicians_merged = 0
    politicians_not_merged = 0
    status = ""
    success = True
    try:
        representative_query = Representative.objects.all()
        representative_query = representative_query.filter(politician_deduplication_attempted=False)
        representative_query = representative_query.exclude(
            Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=""))
        if positive_value_exists(state_code):
            representative_query = representative_query.filter(state_code__iexact=state_code)
        representative_list = list(representative_query[:50])
    except Exception as e:
        status += "REPRESENTATIVE_QUERY_FAILED: " + str(e) + " "
        success = False
        results = {
            'decisions_required':                   decisions_required,
            'merge_errors':                         merge_errors,
            'multiple_possible_politicians_found':  multiple_possible_politicians_found,
            'no_merge_options_found':               no_merge_options_found,
            'number_of_politicians_reviewed':       number_of_politicians_reviewed,
            'politicians_merged':                   politicians_merged,
            'politicians_not_merged':               politicians_not_merged,
            'success':                              success,
            'status':                               status,
        }
        return results

    # Get all the politician_we_vote_ids, so we can get all politicians in a single query
    politician_we_vote_id_list = []
    for we_vote_representative in representative_list:
        politician_we_vote_id_list.append(we_vote_representative.politician_we_vote_id)

    politician_dict = {}
    if len(politician_we_vote_id_list) > 0:
        from politician.models import Politician
        try:
            queryset = Politician.objects.using('readonly').all()
            queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
            politician_list = list(queryset)
            for politician in politician_list:
                politician_dict[politician.we_vote_id] = politician
        except Exception as e:
            status += "COULD_NOT_RETRIEVE_POLITICIANS: " + str(e) + " "
            success = False
            results = {
                'decisions_required':                   decisions_required,
                'merge_errors':                         merge_errors,
                'multiple_possible_politicians_found':  multiple_possible_politicians_found,
                'no_merge_options_found':               no_merge_options_found,
                'number_of_politicians_reviewed':       number_of_politicians_reviewed,
                'politicians_merged':                   politicians_merged,
                'politicians_not_merged':               politicians_not_merged,
                'success':                              success,
                'status':                               status,
            }
            return results

    from politician.controllers import find_duplicate_politician, merge_if_duplicate_politicians
    politician_manager = PoliticianManager()
    for we_vote_representative in representative_list:
        if not positive_value_exists(we_vote_representative.politician_we_vote_id):
            continue
        if we_vote_representative.politician_we_vote_id not in politician_dict:
            continue
        we_vote_politician = politician_dict[we_vote_representative.politician_we_vote_id]
        number_of_politicians_reviewed += 1
        # Add current politician entry to ignore list
        ignore_politician_we_vote_id_list = [we_vote_politician.we_vote_id]
        # Now check to for other politicians we have labeled as "not a duplicate"
        not_a_duplicate_list = politician_manager.fetch_politicians_are_not_duplicates_list_we_vote_ids(
            we_vote_politician.we_vote_id)
        ignore_politician_we_vote_id_list += not_a_duplicate_list

        results = find_duplicate_politician(we_vote_politician, ignore_politician_we_vote_id_list, read_only=True)
        if results['politician_merge_possibility_found']:
            politician_option1_for_template = we_vote_politician
            politician_option2_for_template = results['politician_merge_possibility']

            # Can we automatically merge these politicians?
            merge_results = merge_if_duplicate_politicians(
                politician_option1_for_template,
                politician_option2_for_template,
                results['politician_merge_conflict_values'])

            if not merge_results['success']:
                merge_errors += 1
                politicians_not_merged += 1
                status += merge_results['status']
            elif merge_results['decisions_required']:
                decisions_required += 1
                politicians_not_merged += 1
                status += "DECISIONS_REQUIRED "
            elif merge_results['politicians_merged']:
                politicians_merged += 1
                status += "MERGED_WITH_OTHER_POLITICIAN "
            else:
                multiple_possible_politicians_found += 1
                status += "COULD_NOT_MERGE "
        else:
            no_merge_options_found += 1
            politicians_not_merged += 1
        try:
            we_vote_representative.politician_deduplication_attempted = True
            we_vote_representative.save()
        except Exception as e:
            status += "FAILED_UPDATING_politician_deduplication_attempted: " + str(e) + " "

    results = {
        'decisions_required':                   decisions_required,
        'merge_errors':                         merge_errors,
        'multiple_possible_politicians_found':  multiple_possible_politicians_found,
        'no_merge_options_found':               no_merge_options_found,
        'number_of_politicians_reviewed':       number_of_politicians_reviewed,
        'politicians_merged':                   politicians_merged,
        'politicians_not_merged':               politicians_not_merged,
        'success':                              success,
        'status':                               status,
    }
    return results


def representatives_import_from_master_server(request, state_code=''):  # representativesSyncOut
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Request json file from We Vote servers
    import_results, structured_json = process_request_from_master(
        request, "Loading Representative entries from We Vote Master servers",
        REPRESENTATIVE_SYNC_URL, {
            "key": WE_VOTE_API_KEY,
            "state_code": state_code,
        }
    )

    if import_results['success']:
        # We shouldn't need to check for duplicates any more
        # results = filter_offices_structured_json_for_local_duplicates(structured_json)
        # filtered_structured_json = results['structured_json']
        # duplicates_removed = results['duplicates_removed']
        duplicates_removed = 0

        import_results = representatives_import_from_structured_json(structured_json)
        import_results['duplicates_removed'] = duplicates_removed

    return import_results


def representatives_import_from_structured_json(structured_json):  # representativesSyncOut
    representative_manager = RepresentativeManager()
    representatives_saved = 0
    representatives_updated = 0
    representatives_not_processed = 0
    status = ""
    status_passed_through_count = 0

    boolean_fields = [
        'facebook_url_is_broken',
        'is_battleground_race_2019',
        'is_battleground_race_2020',
        'is_battleground_race_2021',
        'is_battleground_race_2022',
        'is_battleground_race_2023',
        'is_battleground_race_2024',
        'is_battleground_race_2025',
        'is_battleground_race_2026',
        'politician_deduplication_attempted',
        'politician_match_attempted',
        'twitter_handle_updates_failing',
        'twitter_handle2_updates_failing',
        'year_in_office_2023',
        'year_in_office_2024',
        'year_in_office_2025',
        'year_in_office_2026',
    ]
    character_fields = [
        'ballotpedia_representative_url',
        'ctcl_uuid',
        'facebook_url',
        'google_civic_profile_image_url_https',
        'google_civic_representative_name',
        'google_civic_representative_name2',
        'google_civic_representative_name3',
        'instagram_handle',
        'linkedin_url',
        'ocd_division_id',
        'office_held_district_name',
        'office_held_name',
        'office_held_we_vote_id',
        'photo_url_from_google_civic',
        'political_party',
        'politician_we_vote_id',
        'profile_image_type_currently_active',
        'representative_contact_form_url',
        'representative_email',
        'representative_email2',
        'representative_email3',
        'representative_phone',
        'representative_phone2',
        'representative_phone3',
        'representative_twitter_handle',
        'representative_twitter_handle2',
        'representative_twitter_handle3',
        'representative_url',
        'representative_url2',
        'representative_url3',
        'seo_friendly_path',
        'state_code',
        'twitter_description',
        'twitter_name',
        'twitter_location',
        'twitter_followers_count',
        'twitter_profile_image_url_https',
        'twitter_profile_background_image_url_https',
        'twitter_profile_banner_url_https',
        'twitter_url',
        'vote_usa_politician_id',
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
        'wikipedia_url',
        'youtube_url',
    ]
    character_null_false_fields = [
        'representative_name',
    ]
    character_to_datetime_fields = [
        'date_last_updated',
        'date_last_updated_from_politician',
        'seo_friendly_path_date_last_updated',
    ]
    integer_fields = [
        'instagram_followers_count',
        'office_held_id',
        'politician_id',
        'twitter_user_id',
        'twitter_followers_count',
    ]
    for one_representative in structured_json:
        updated_representative_values = {}
        representatives_we_vote_id = one_representative.get('we_vote_id', '')
        for one_field in boolean_fields:
            if one_field in one_representative:
                updated_representative_values[one_field] = positive_value_exists(one_representative[one_field])
            else:
                updated_representative_values[one_field] = None
        for one_field in character_fields:
            updated_representative_values[one_field] = one_representative[one_field] \
                if one_field in one_representative \
                else None
        for one_field in character_null_false_fields:
            updated_representative_values[one_field] = one_representative[one_field] \
                if one_field in one_representative \
                else ''
        for one_field in character_to_datetime_fields:
            if one_field in one_representative and positive_value_exists(one_representative[one_field]):
                updated_representative_values[one_field] = \
                    datetime.strptime(one_representative[one_field], '%Y-%m-%d %H:%M:%S')
            else:
                updated_representative_values[one_field] = None
        for one_field in integer_fields:
            if one_field in one_representative:
                updated_representative_values[one_field] = convert_to_int(one_representative[one_field])
            else:
                updated_representative_values[one_field] = 0
        results = representative_manager.update_or_create_representative(
            representative_we_vote_id=representatives_we_vote_id,
            updated_values=updated_representative_values)

        if results['success']:
            if results['new_representative_created']:
                representatives_saved += 1
            else:
                representatives_updated += 1
        else:
            representatives_not_processed += 1
            if status_passed_through_count < 10:
                status += results['status']
                status_passed_through_count += 1

    results = {
        'success':          True,
        'status':           "REPRESENTATIVE_IMPORT_PROCESS_COMPLETE ",
        'saved':            representatives_saved,
        'updated':          representatives_updated,
        'not_processed':    representatives_not_processed,
    }
    return results


def representative_politician_match(representative):
    politician_manager = PoliticianManager()
    status = ''
    success = True

    # Does this candidate already have a we_vote_id for a politician?
    if positive_value_exists(representative.politician_we_vote_id):
        # Find existing politician. No update here for now.
        results = politician_manager.retrieve_politician(
            politician_we_vote_id=representative.politician_we_vote_id,
            read_only=True)
        status += results['status']
        if not results['success']:
            results = {
                'success':                  False,
                'status':                   status,
                'politician_list_found':    False,
                'politician_list':          [],
                'politician_found':         False,
                'politician_created':       False,
                'politician':               None,
            }
            return results
        elif results['politician_found']:
            politician = results['politician']
            politician_found = True
            # Save politician_we_vote_id in representative
            representative.politician_we_vote_id = politician.we_vote_id
            representative.politician_id = politician.id
            representative.seo_friendly_path = politician.seo_friendly_path
            representative.save()

            if positive_value_exists(representative.we_vote_id):
                years_false_list = []
                years_true_list = []
                is_battleground_years_list = IS_BATTLEGROUND_YEARS_AVAILABLE
                for year in is_battleground_years_list:
                    is_battleground_race_key = 'is_battleground_race_' + str(year)
                    if hasattr(representative, is_battleground_race_key):
                        if positive_value_exists(getattr(representative, is_battleground_race_key)):
                            years_true_list.append(year)
                        else:
                            # When merging into a politician from a representative, don't send in "False" years
                            pass
                from politician.controllers import update_parallel_fields_with_years_in_related_objects
                results = update_parallel_fields_with_years_in_related_objects(
                    field_key_root='is_battleground_race_',
                    master_we_vote_id_updated=representative.we_vote_id,
                    years_false_list=years_false_list,
                    years_true_list=years_true_list,
                )
                status += results['status']

            results = {
                'success':                  success,
                'status':                   status,
                'politician_list_found':    False,
                'politician_list':          [],
                'politician_found':         politician_found,
                'politician_created':       False,
                'politician':               politician,
            }
            return results
        else:
            # Politician wasn't found, so clear out politician_we_vote_id and politician_id
            representative.politician_we_vote_id = None
            representative.politician_id = None
            representative.seo_friendly_path = None
            representative.save()

    # Search the politician table for a stricter match (don't match on "dan" if "dan smith" passed in)
    #  so we set return_close_matches to False
    from wevote_functions.functions import add_to_list_if_positive_value_exists
    facebook_url_list = []
    facebook_url_list = add_to_list_if_positive_value_exists(representative.facebook_url, facebook_url_list)
    full_name_list = []
    full_name_list = add_to_list_if_positive_value_exists(representative.representative_name, full_name_list)
    full_name_list = \
        add_to_list_if_positive_value_exists(representative.google_civic_representative_name, full_name_list)
    full_name_list = \
        add_to_list_if_positive_value_exists(representative.google_civic_representative_name2, full_name_list)
    full_name_list = \
        add_to_list_if_positive_value_exists(representative.google_civic_representative_name3, full_name_list)
    twitter_handle_list = []
    twitter_handle_list = \
        add_to_list_if_positive_value_exists(representative.representative_twitter_handle, twitter_handle_list)
    twitter_handle_list = \
        add_to_list_if_positive_value_exists(representative.representative_twitter_handle2, twitter_handle_list)
    twitter_handle_list = \
        add_to_list_if_positive_value_exists(representative.representative_twitter_handle3, twitter_handle_list)
    results = politician_manager.retrieve_all_politicians_that_might_match_similar_object(
        facebook_url_list=facebook_url_list,
        full_name_list=full_name_list,
        twitter_handle_list=twitter_handle_list,
        return_close_matches=False,
        state_code=representative.state_code,
    )
    status += results['status']
    if not results['success']:
        results = {
            'success':                  False,
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_list_found']:
        # If here, return the list but don't link the representative
        politician_list = results['politician_list']

        results = {
            'success':                  True,
            'status':                   status,
            'politician_list_found':    True,
            'politician_list':          politician_list,
            'politician_found':         False,
            'politician_created':       False,
            'politician':               None,
        }
        return results
    elif results['politician_found']:
        # Save this politician_we_vote_id with the representative
        politician = results['politician']
        # Save politician_we_vote_id in representative
        representative.politician_we_vote_id = politician.we_vote_id
        representative.politician_id = politician.id
        representative.seo_friendly_path = politician.seo_friendly_path
        representative.save()

        if positive_value_exists(representative.we_vote_id):
            years_false_list = []
            years_true_list = []
            is_battleground_years_list = IS_BATTLEGROUND_YEARS_AVAILABLE
            for year in is_battleground_years_list:
                is_battleground_race_key = 'is_battleground_race_' + str(year)
                if hasattr(representative, is_battleground_race_key):
                    if positive_value_exists(getattr(representative, is_battleground_race_key)):
                        years_true_list.append(year)
                    else:
                        # When merging into a politician from a representative, don't send in "False" years
                        pass
            from politician.controllers import update_parallel_fields_with_years_in_related_objects
            results = update_parallel_fields_with_years_in_related_objects(
                field_key_root='is_battleground_race_',
                master_we_vote_id_updated=representative.we_vote_id,
                years_false_list=years_false_list,
                years_true_list=years_true_list,
            )
            status += results['status']

        results = {
            'success':                  True,
            'status':                   status,
            'politician_list_found':    False,
            'politician_list':          [],
            'politician_found':         True,
            'politician_created':       False,
            'politician':               politician,
        }
        return results
    else:
        # Create new politician for this representative
        create_results = politician_manager.create_politician_from_similar_object(representative)
        politician = create_results['politician']
        politician_created = create_results['politician_created']
        politician_found = create_results['politician_found']
        status += create_results['status']
        success = create_results['success']
        if create_results['politician_found']:
            # Save politician_we_vote_id in representative
            representative.politician_we_vote_id = politician.we_vote_id
            representative.politician_id = politician.id
            representative.seo_friendly_path = politician.seo_friendly_path
            representative.save()

            if positive_value_exists(representative.we_vote_id):
                # Since this is a new politician, we can send in "False" years
                years_false_list = []
                years_true_list = []
                is_battleground_years_list = IS_BATTLEGROUND_YEARS_AVAILABLE
                for year in is_battleground_years_list:
                    is_battleground_race_key = 'is_battleground_race_' + str(year)
                    if hasattr(representative, is_battleground_race_key):
                        if positive_value_exists(getattr(representative, is_battleground_race_key)):
                            years_true_list.append(year)
                        else:
                            years_false_list.append(year)
                from politician.controllers import update_parallel_fields_with_years_in_related_objects
                results = update_parallel_fields_with_years_in_related_objects(
                    field_key_root='is_battleground_race_',
                    master_we_vote_id_updated=representative.we_vote_id,
                    years_false_list=years_false_list,
                    years_true_list=years_true_list,
                )
                status += results['status']

        results = {
            'success':                      success,
            'status':                       status,
            'politician_list_found':        False,
            'politician_list':              [],
            'politician_found':             politician_found,
            'politician_created':           politician_created,
            'politician':                   politician,
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


def update_representative_details_from_campaignx(representative=None, campaignx=None):
    status = ''
    success = True
    save_changes = False

    if not hasattr(representative, 'supporters_count') or not hasattr(campaignx, 'supporters_count'):
        success = False
        status += 'UPDATE_REPRESENTATIVE_FROM_CAMPAIGNX_MISSING_REQUIRED_ATTRIBUTES '
        results = {
            'success':          success,
            'status':           status,
            'representative':   representative,
            'save_changes':     save_changes,
        }
        return results

    if representative.supporters_count != campaignx.supporters_count:
        representative.supporters_count = campaignx.supporters_count
        save_changes = True

    results = {
        'success':          success,
        'status':           status,
        'representative':   representative,
        'save_changes':     save_changes,
    }
    return results


def update_representative_details_from_politician(representative=None, politician=None):
    status = ''
    success = True
    save_changes = False
    if not positive_value_exists(representative.ballotpedia_representative_url) and \
            positive_value_exists(politician.ballotpedia_politician_url):
        representative.ballotpedia_representative_url = politician.ballotpedia_politician_url
        save_changes = True
    representative_facebook_url_missing = \
        not positive_value_exists(representative.facebook_url) or representative.facebook_url_is_broken
    politician_facebook_url_exists = \
        positive_value_exists(politician.facebook_url) and not politician.facebook_url_is_broken
    if representative_facebook_url_missing and politician_facebook_url_exists:
        representative.facebook_url = politician.facebook_url
        representative.facebook_url_is_broken = False
        save_changes = True
    if positive_value_exists(politician.politician_name) and positive_value_exists(representative.representative_name) \
            and politician.politician_name != representative.representative_name:
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_representative_name',
            look_at_alternate_names=True,
            representative=representative,
            new_value_to_add=politician.politician_name)
        if name_results['success']:
            representative = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
    if positive_value_exists(politician.google_civic_candidate_name):
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_representative_name',
            look_at_alternate_names=True,
            representative=representative,
            new_value_to_add=politician.google_civic_candidate_name)
        if name_results['success']:
            representative = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
    if positive_value_exists(politician.google_civic_candidate_name2):
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_representative_name',
            look_at_alternate_names=True,
            representative=representative,
            new_value_to_add=politician.google_civic_candidate_name2)
        if name_results['success']:
            representative = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
    if positive_value_exists(politician.google_civic_candidate_name3):
        name_results = add_value_to_next_representative_spot(
            field_name_base='google_civic_representative_name',
            look_at_alternate_names=True,
            representative=representative,
            new_value_to_add=politician.google_civic_candidate_name3)
        if name_results['success']:
            representative = name_results['representative']
            save_changes = save_changes or name_results['values_changed']
    if not positive_value_exists(representative.instagram_followers_count) and \
            positive_value_exists(politician.instagram_followers_count):
        representative.instagram_followers_count = politician.instagram_followers_count
        save_changes = True
    if not positive_value_exists(representative.instagram_handle) and \
            positive_value_exists(politician.instagram_handle):
        representative.instagram_handle = politician.instagram_handle
        save_changes = True
    if not positive_value_exists(representative.linkedin_url) and \
            positive_value_exists(politician.linkedin_url):
        representative.linkedin_url = politician.linkedin_url
        save_changes = True
    if not positive_value_exists(representative.representative_contact_form_url) and \
            positive_value_exists(politician.politician_contact_form_url):
        representative.representative_contact_form_url = politician.politician_contact_form_url
        save_changes = True
    if positive_value_exists(politician.politician_email):
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_email',
            representative=representative,
            new_value_to_add=politician.politician_email)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_email2):
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_email',
            representative=representative,
            new_value_to_add=politician.politician_email2)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_email3):
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_email',
            representative=representative,
            new_value_to_add=politician.politician_email3)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_phone_number):
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_phone',
            representative=representative,
            new_value_to_add=politician.politician_phone_number)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_phone_number2):
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_phone',
            representative=representative,
            new_value_to_add=politician.politician_phone_number2)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_phone_number3):
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_phone',
            representative=representative,
            new_value_to_add=politician.politician_phone_number3)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_twitter_handle) and not politician.twitter_handle_updates_failing:
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_twitter_handle',
            representative=representative,
            new_value_to_add=politician.politician_twitter_handle)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if positive_value_exists(politician.politician_twitter_handle2) and not politician.twitter_handle2_updates_failing:
        twitter_results = add_value_to_next_representative_spot(
            field_name_base='representative_twitter_handle',
            representative=representative,
            new_value_to_add=politician.politician_twitter_handle2)
        if twitter_results['success']:
            representative = twitter_results['representative']
    if not positive_value_exists(representative.twitter_description) and \
            positive_value_exists(politician.twitter_description):
        representative.twitter_description = politician.twitter_description
        save_changes = True
    if not positive_value_exists(representative.twitter_followers_count) and \
            positive_value_exists(politician.twitter_followers_count):
        representative.twitter_followers_count = politician.twitter_followers_count
        save_changes = True
    if not positive_value_exists(representative.twitter_location) and \
            positive_value_exists(politician.twitter_location):
        representative.twitter_location = politician.twitter_location
        save_changes = True
    if not positive_value_exists(representative.twitter_name) and \
            positive_value_exists(politician.twitter_name):
        representative.twitter_name = politician.twitter_name
        save_changes = True
    if positive_value_exists(politician.politician_url):
        results = add_value_to_next_representative_spot(
            field_name_base='representative_url',
            representative=representative,
            new_value_to_add=politician.politician_url)
        if results['success']:
            representative = results['representative']
            save_changes = True
    if positive_value_exists(politician.politician_url2):
        results = add_value_to_next_representative_spot(
            field_name_base='representative_url',
            representative=representative,
            new_value_to_add=politician.politician_url2)
        if results['success']:
            representative = results['representative']
            save_changes = True
    if positive_value_exists(politician.politician_url3):
        results = add_value_to_next_representative_spot(
            field_name_base='representative_url',
            representative=representative,
            new_value_to_add=politician.politician_url3)
        if results['success']:
            representative = results['representative']
            save_changes = True
    if positive_value_exists(politician.politician_url4):
        results = add_value_to_next_representative_spot(
            field_name_base='representative_url',
            representative=representative,
            new_value_to_add=politician.politician_url4)
        if results['success']:
            representative = results['representative']
            save_changes = True
    if positive_value_exists(politician.politician_url5):
        results = add_value_to_next_representative_spot(
            field_name_base='representative_url',
            representative=representative,
            new_value_to_add=politician.politician_url5)
        if results['success']:
            representative = results['representative']
            save_changes = True
    if not positive_value_exists(representative.vote_usa_politician_id) and \
            positive_value_exists(politician.vote_usa_politician_id):
        representative.vote_usa_politician_id = politician.vote_usa_politician_id
        save_changes = True
    if not positive_value_exists(representative.we_vote_hosted_profile_image_url_large):
        if positive_value_exists(politician.we_vote_hosted_profile_image_url_large):
            representative.we_vote_hosted_profile_image_url_large = \
                politician.we_vote_hosted_profile_image_url_large
            save_changes = True
    if not positive_value_exists(representative.we_vote_hosted_profile_image_url_medium):
        if positive_value_exists(politician.we_vote_hosted_profile_image_url_medium):
            representative.we_vote_hosted_profile_image_url_medium = \
                politician.we_vote_hosted_profile_image_url_medium
            save_changes = True
    if not positive_value_exists(representative.we_vote_hosted_profile_image_url_tiny):
        if positive_value_exists(politician.we_vote_hosted_profile_image_url_tiny):
            representative.we_vote_hosted_profile_image_url_tiny = \
                politician.we_vote_hosted_profile_image_url_tiny
            save_changes = True
    # Uploaded photo
    representative.we_vote_hosted_profile_uploaded_image_url_large = \
        politician.we_vote_hosted_profile_uploaded_image_url_large
    representative.we_vote_hosted_profile_uploaded_image_url_medium = \
        politician.we_vote_hosted_profile_uploaded_image_url_medium
    representative.we_vote_hosted_profile_uploaded_image_url_tiny = \
        politician.we_vote_hosted_profile_uploaded_image_url_tiny
    if representative.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
        if positive_value_exists(politician.we_vote_hosted_profile_uploaded_image_url_large) \
                or positive_value_exists(politician.we_vote_hosted_profile_uploaded_image_url_medium) \
                or positive_value_exists(politician.we_vote_hosted_profile_uploaded_image_url_tiny):
            representative.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UPLOADED
            representative.we_vote_hosted_profile_image_url_large = \
                politician.we_vote_hosted_profile_uploaded_image_url_large
            representative.we_vote_hosted_profile_image_url_medium = \
                politician.we_vote_hosted_profile_uploaded_image_url_medium
            representative.we_vote_hosted_profile_image_url_tiny = \
                politician.we_vote_hosted_profile_uploaded_image_url_tiny
    if politician.profile_image_background_color != representative.profile_image_background_color:
        representative.profile_image_background_color = politician.profile_image_background_color
        save_changes = True
    if not positive_value_exists(representative.wikipedia_url) and \
            positive_value_exists(politician.wikipedia_url):
        representative.wikipedia_url = politician.wikipedia_url
        save_changes = True
    if not positive_value_exists(representative.youtube_url) and \
            positive_value_exists(politician.youtube_url):
        representative.youtube_url = politician.youtube_url
        save_changes = True

    results = {
        'success':          success,
        'status':           status,
        'representative':   representative,
        'save_changes':     save_changes,
    }
    return results
