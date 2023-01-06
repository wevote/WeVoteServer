# politician/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.controllers import add_name_to_next_spot, move_candidates_to_another_politician
from elected_official.controllers import move_elected_officials_to_another_politician
from politician.models import Politician, PoliticianManager, POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED, \
    POLITICIAN_UNIQUE_IDENTIFIERS
from position.controllers import move_positions_to_another_politician
from config.base import get_environment_variable
import wevote_functions.admin
from wevote_functions.functions import convert_to_political_party_constant, positive_value_exists, \
    process_request_from_master

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut


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
        values_changed = True
    elif twitter_handle == politician.politician_twitter_handle:
        # The value is already stored in politician.politician_twitter_handle so doesn't need
        # to be added anywhere below
        pass
    elif not positive_value_exists(politician.politician_twitter_handle2):
        politician.politician_twitter_handle2 = twitter_handle
        values_changed = True
    elif twitter_handle == politician.politician_twitter_handle2:
        # The value is already stored in politician.politician_twitter_handle2 so doesn't need
        # to be added to politician.politician_twitter_handle3
        pass
    elif not positive_value_exists(politician.politician_twitter_handle3):
        politician.politician_twitter_handle3 = twitter_handle
        values_changed = True
    elif twitter_handle == politician.politician_twitter_handle3:
        # The value is already stored in politician.politician_twitter_handle3 so doesn't need
        # to be added to politician.politician_twitter_handle4
        pass
    elif not positive_value_exists(politician.politician_twitter_handle4):
        politician.politician_twitter_handle4 = twitter_handle
        values_changed = True
    elif twitter_handle == politician.politician_twitter_handle4:
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
        politician_twitter_handle_list=politician_twitter_handle_list,
        politician_name=we_vote_politician.politician_name,
        ignore_politician_id_list=ignore_politician_id_list)


def find_duplicate_politician(we_vote_politician, ignore_politician_id_list):
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
            politician_twitter_handle_list=politician_twitter_handle_list,
            politician_name=we_vote_politician.politician_name,
            ignore_politician_id_list=ignore_politician_id_list)

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


def figure_out_politician_conflict_values(politician1, politician2):
    status = ''
    success = True
    politician_merge_conflict_values = {}

    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        try:
            politician1_attribute_value = getattr(politician1, attribute)
            politician2_attribute_value = getattr(politician2, attribute)
            if politician1_attribute_value is None and politician2_attribute_value is None:
                politician_merge_conflict_values[attribute] = 'MATCHING'
            elif politician1_attribute_value is None or politician1_attribute_value == "":
                politician_merge_conflict_values[attribute] = 'POLITICIAN2'
            elif politician2_attribute_value is None or politician2_attribute_value == "":
                politician_merge_conflict_values[attribute] = 'POLITICIAN1'
            else:
                if attribute == "politician_url":
                    # If there is a link with 'http' in politician 2, and politician 1 doesn't have 'http',
                    #  use the one with 'http'
                    if 'http' in politician2_attribute_value and 'http' not in politician1_attribute_value:
                        politician_merge_conflict_values[attribute] = 'POLITICIAN2'
                    elif politician1_attribute_value.lower() == politician2_attribute_value.lower():
                        politician_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        politician_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "politician_name" or attribute == "state_code":
                    if politician1_attribute_value.lower() == politician2_attribute_value.lower():
                        politician_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        politician_merge_conflict_values[attribute] = 'CONFLICT'
                elif attribute == "political_party":
                    if convert_to_political_party_constant(politician1_attribute_value) == \
                            convert_to_political_party_constant(politician2_attribute_value):
                        politician_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        politician_merge_conflict_values[attribute] = 'CONFLICT'
                else:
                    if politician1_attribute_value == politician2_attribute_value:
                        politician_merge_conflict_values[attribute] = 'MATCHING'
                    else:
                        politician_merge_conflict_values[attribute] = 'CONFLICT'
        except AttributeError:
            status += "COULD_NOT_PROCESS_ATTRIBUTE: " + str(attribute) + " "
            success = False

    return {
        'status': status,
        'success': success,
        'politician_merge_conflict_values': politician_merge_conflict_values,
    }


def merge_if_duplicate_politicians(politician1_on_stage, politician2_on_stage, conflict_values):
    success = False
    status = "MERGE_IF_DUPLICATE_POLITICIANS "
    politicians_merged = False
    decisions_required = False
    politician1_we_vote_id = politician1_on_stage.we_vote_id
    politician2_we_vote_id = politician2_on_stage.we_vote_id

    # Are there any comparisons that require admin intervention?
    merge_choices = {}
    clear_these_attributes_from_politician2 = []
    for attribute in POLITICIAN_UNIQUE_IDENTIFIERS:
        if attribute == "ballotpedia_id" \
                or attribute == "other_source_photo_url" \
                or attribute == "we_vote_hosted_profile_image_url_large" \
                or attribute == "we_vote_hosted_profile_image_url_medium" \
                or attribute == "we_vote_hosted_profile_image_url_tiny":
            if positive_value_exists(getattr(politician1_on_stage, attribute)):
                # We can proceed because politician1 has a valid image, so we can default to choosing that one
                pass
            elif positive_value_exists(getattr(politician2_on_stage, attribute)):
                # If we are here, politician1 does NOT have an image, but politician2 does
                merge_choices[attribute] = getattr(politician2_on_stage, attribute)
        else:
            conflict_value = conflict_values.get(attribute, None)
            if conflict_value == "CONFLICT":
                decisions_required = True
                break
            elif conflict_value == "POLITICIAN2":
                merge_choices[attribute] = getattr(politician2_on_stage, attribute)
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

        if merge_results['politicians_merged']:
            success = True
            politicians_merged = True

    results = {
        'success':              success,
        'status':               status,
        'politicians_merged':   politicians_merged,
        'decisions_required':   decisions_required,
        'politician':           politician1_on_stage,
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
    politician1_results = politician_manager.retrieve_politician(we_vote_id=politician1_we_vote_id)
    if politician1_results['politician_found']:
        politician1_on_stage = politician1_results['politician']
        politician1_id = politician1_on_stage.id
    else:
        results = {
            'success': False,
            'status': "MERGE_THESE_TWO_POLITICIANS-COULD_NOT_RETRIEVE_POLITICIAN1 ",
            'politicians_merged': False,
            'politician': None,
        }
        return results

    politician2_results = politician_manager.retrieve_politician(we_vote_id=politician2_we_vote_id)
    if politician2_results['politician_found']:
        politician2_on_stage = politician2_results['politician']
        politician2_id = politician2_on_stage.id
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
                setattr(politician1_on_stage, attribute, admin_merge_choices[attribute])
        except Exception as e:
            # Don't completely fail if in attribute can't be saved.
            status += "ATTRIBUTE_SAVE_FAILED (" + str(attribute) + ") " + str(e) + " "

    # Preserve unique google_civic_candidate_name, _name2, _name3
    if positive_value_exists(politician2_on_stage.google_civic_candidate_name):
        politician1_on_stage = add_name_to_next_spot(
            politician1_on_stage, politician2_on_stage.google_civic_candidate_name)
    if positive_value_exists(politician2_on_stage.google_civic_candidate_name2):
        politician1_on_stage = add_name_to_next_spot(
            politician1_on_stage, politician2_on_stage.google_civic_candidate_name2)
    if positive_value_exists(politician2_on_stage.google_civic_candidate_name3):
        politician1_on_stage = add_name_to_next_spot(
            politician1_on_stage, politician2_on_stage.google_civic_candidate_name3)

    # Preserve unique politician_twitter_handle -> politician_twitter_handle5
    if positive_value_exists(politician2_on_stage.politician_twitter_handle):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1_on_stage, politician2_on_stage.politician_twitter_handle)
        if twitter_results['success']:
            politician1_on_stage = twitter_results['politician']
    if positive_value_exists(politician2_on_stage.politician_twitter_handle2):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1_on_stage, politician2_on_stage.politician_twitter_handle2)
        if twitter_results['success']:
            politician1_on_stage = twitter_results['politician']
    if positive_value_exists(politician2_on_stage.politician_twitter_handle3):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1_on_stage, politician2_on_stage.politician_twitter_handle3)
        if twitter_results['success']:
            politician1_on_stage = twitter_results['politician']
    if positive_value_exists(politician2_on_stage.politician_twitter_handle4):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1_on_stage, politician2_on_stage.politician_twitter_handle4)
        if twitter_results['success']:
            politician1_on_stage = twitter_results['politician']
    if positive_value_exists(politician2_on_stage.politician_twitter_handle5):
        twitter_results = add_twitter_handle_to_next_politician_spot(
            politician1_on_stage, politician2_on_stage.politician_twitter_handle5)
        if twitter_results['success']:
            politician1_on_stage = twitter_results['politician']

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

    # Update Elected Officials to new politician ids
    elected_official_results = move_elected_officials_to_another_politician(
        from_politician_id=politician2_id,
        from_politician_we_vote_id=politician2_we_vote_id,
        to_politician_id=politician1_id,
        to_politician_we_vote_id=politician1_we_vote_id)
    if not elected_official_results['success']:
        status += elected_official_results['status']
        status += "COULD_NOT_MOVE_ELECTED_OFFICIALS_TO_POLITICIAN1 "
        results = {
            'success': False,
            'status': status,
            'politicians_merged': False,
            'politician': None,
        }
        return results

    # Clear 'unique=True' fields in politician2_on_stage, which need to be Null before politician1_on_stage can be saved
    #  with updated values
    politician2_updated = False
    for attribute in clear_these_attributes_from_politician2:
        setattr(politician2_on_stage, attribute, None)
        politician2_updated = True
    if politician2_updated:
        politician2_on_stage.save()

    # Note: wait to wrap in try/except block
    politician1_on_stage.save()
    # 2021-10-16 Uses image data from master table which we aren't updating with the merge yet
    # refresh_politician_data_from_master_tables(politician1_on_stage.we_vote_id)

    # Remove politician 2
    politician2_on_stage.delete()

    results = {
        'success': True,
        'status': status,
        'politicians_merged': True,
        'politician': politician1_on_stage,
    }
    return results


def politicians_import_from_master_server(request, state_code=''):
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


def politicians_import_from_structured_json(structured_json):
    politician_manager = PoliticianManager()
    politicians_saved = 0
    politicians_updated = 0
    politicians_not_processed = 0
    status = ''

    importing_turned_off = True
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

    for one_politician in structured_json:
        politician_name = one_politician['politician_name'] if 'politician_name' in one_politician else ''
        politician_we_vote_id = one_politician['we_vote_id'] if 'we_vote_id' in one_politician else ''

        if positive_value_exists(politician_name):
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False
        if proceed_to_update_or_create:
            updated_politician_values = {
                'politician_name': politician_name,
                # 'we_vote_id': politician_we_vote_id,  # Trying to keep politician
            }
            if 'ballotpedia_id' in one_politician:
                updated_politician_values['ballotpedia_id'] = one_politician['ballotpedia_id']
            if 'ballotpedia_politician_name' in one_politician:
                updated_politician_values['ballotpedia_politician_name'] = one_politician['ballotpedia_politician_name']
            if 'ballotpedia_politician_url' in one_politician:
                updated_politician_values['ballotpedia_politician_url'] = one_politician['ballotpedia_politician_url']
            if 'bioguide_id' in one_politician:
                updated_politician_values['bioguide_id'] = one_politician['bioguide_id']
            if 'birth_date' in one_politician:
                updated_politician_values['birth_date'] = one_politician['birth_date']
            if 'cspan_id' in one_politician:
                updated_politician_values['cspan_id'] = one_politician['cspan_id']
            if 'ctcl_uuid' in one_politician:
                updated_politician_values['ctcl_uuid'] = one_politician['ctcl_uuid']
            if 'facebook_url' in one_politician:
                updated_politician_values['facebook_url'] = one_politician['facebook_url']
            if 'facebook_url_is_broken' in one_politician:
                updated_politician_values['facebook_url_is_broken'] = one_politician['facebook_url_is_broken']
            if 'fec_id' in one_politician:
                updated_politician_values['fec_id'] = one_politician['fec_id']
            if 'first_name' in one_politician:
                updated_politician_values['first_name'] = one_politician['first_name']
            if 'full_name_assembled' in one_politician:
                updated_politician_values['full_name_assembled'] = one_politician['full_name_assembled']
            if 'gender' in one_politician:
                updated_politician_values['gender'] = one_politician['gender']
            if 'google_civic_candidate_name' in one_politician:
                updated_politician_values['google_civic_candidate_name'] = \
                    one_politician['google_civic_candidate_name']
            if 'google_civic_candidate_name2' in one_politician:
                updated_politician_values['google_civic_candidate_name2'] = \
                    one_politician['google_civic_candidate_name2']
            if 'google_civic_candidate_name3' in one_politician:
                updated_politician_values['google_civic_candidate_name3'] = \
                    one_politician['google_civic_candidate_name3']
            if 'govtrack_id' in one_politician:
                updated_politician_values['govtrack_id'] = one_politician['govtrack_id']
            if 'house_history_id' in one_politician:
                updated_politician_values['house_history_id'] = one_politician['house_history_id']
            if 'icpsr_id' in one_politician:
                updated_politician_values['icpsr_id'] = one_politician['icpsr_id']
            if 'instagram_followers_count' in one_politician:
                updated_politician_values['instagram_followers_count'] = one_politician['instagram_followers_count']
            if 'instagram_handle' in one_politician:
                updated_politician_values['instagram_handle'] = one_politician['instagram_handle']
            if 'last_name' in one_politician:
                updated_politician_values['last_name'] = one_politician['last_name']
            if 'lis_id' in one_politician:
                updated_politician_values['lis_id'] = one_politician['lis_id']
            if 'maplight_id' in one_politician:
                updated_politician_values['maplight_id'] = one_politician['maplight_id']
            if 'middle_name' in one_politician:
                updated_politician_values['middle_name'] = one_politician['middle_name']
            if 'opensecrets_id' in one_politician:
                updated_politician_values['opensecrets_id'] = one_politician['opensecrets_id']
            if 'political_party' in one_politician:
                updated_politician_values['political_party'] = one_politician['political_party']
            if 'politician_contact_form_url' in one_politician:
                updated_politician_values['politician_contact_form_url'] = one_politician['politician_contact_form_url']
            if 'politician_email_address' in one_politician:
                updated_politician_values['politician_email_address'] = one_politician['politician_email_address']
            if 'politician_facebook_id' in one_politician:
                updated_politician_values['politician_facebook_id'] = one_politician['politician_facebook_id']
            if 'politician_googleplus_id' in one_politician:
                updated_politician_values['politician_googleplus_id'] = one_politician['politician_googleplus_id']
            if 'politician_name' in one_politician:
                updated_politician_values['politician_name'] = one_politician['politician_name']
            if 'politician_phone_number' in one_politician:
                updated_politician_values['politician_phone_number'] = one_politician['politician_phone_number']
            if 'politician_twitter_handle' in one_politician:
                updated_politician_values['politician_twitter_handle'] = one_politician['politician_twitter_handle']
            if 'politician_twitter_handle2' in one_politician:
                updated_politician_values['politician_twitter_handle2'] = one_politician['politician_twitter_handle2']
            if 'politician_twitter_handle3' in one_politician:
                updated_politician_values['politician_twitter_handle3'] = one_politician['politician_twitter_handle3']
            if 'politician_twitter_handle4' in one_politician:
                updated_politician_values['politician_twitter_handle4'] = one_politician['politician_twitter_handle4']
            if 'politician_twitter_handle5' in one_politician:
                updated_politician_values['politician_twitter_handle5'] = one_politician['politician_twitter_handle5']
            if 'politician_url' in one_politician:
                updated_politician_values['politician_url'] = one_politician['politician_url']
            if 'politician_youtube_id' in one_politician:
                updated_politician_values['politician_youtube_id'] = one_politician['politician_youtube_id']
            if 'state_code' in one_politician:
                updated_politician_values['state_code'] = one_politician['state_code']
            if 'thomas_id' in one_politician:
                updated_politician_values['thomas_id'] = one_politician['thomas_id']
            if 'vote_smart_id' in one_politician:
                updated_politician_values['vote_smart_id'] = one_politician['vote_smart_id']
            if 'vote_usa_politician_id' in one_politician:
                updated_politician_values['vote_usa_politician_id'] = one_politician['vote_usa_politician_id']
            if 'washington_post_id' in one_politician:
                updated_politician_values['washington_post_id'] = one_politician['washington_post_id']
            if 'we_vote_hosted_profile_image_url_large' in one_politician:
                updated_politician_values['we_vote_hosted_profile_image_url_large'] = \
                    one_politician['we_vote_hosted_profile_image_url_large']
            if 'we_vote_hosted_profile_image_url_medium' in one_politician:
                updated_politician_values['we_vote_hosted_profile_image_url_medium'] = \
                    one_politician['we_vote_hosted_profile_image_url_medium']
            if 'we_vote_hosted_profile_image_url_tiny' in one_politician:
                updated_politician_values['we_vote_hosted_profile_image_url_tiny'] = \
                    one_politician['we_vote_hosted_profile_image_url_tiny']
            if 'wikipedia_id' in one_politician:
                updated_politician_values['wikipedia_id'] = one_politician['wikipedia_id']

            results = politician_manager.update_or_create_politician(
                updated_politician_values=updated_politician_values,
                politician_we_vote_id=politician_we_vote_id)
            if results['success']:
                values_changed = False
                politician = results['politician']
                if 'politician_twitter_handle' in one_politician:
                    twitter_results = add_twitter_handle_to_next_politician_spot(
                        politician, one_politician['politician_twitter_handle'])
                    if twitter_results['success']:
                        politician = twitter_results['politician']
                        if twitter_results['values_changed']:
                            values_changed = True
                    else:
                        results['status'] += twitter_results['status']
                if 'politician_twitter_handle2' in one_politician:
                    twitter_results = add_twitter_handle_to_next_politician_spot(
                        politician, one_politician['politician_twitter_handle2'])
                    if twitter_results['success']:
                        politician = twitter_results['politician']
                        if twitter_results['values_changed']:
                            values_changed = True
                    else:
                        results['status'] += twitter_results['status']
                if 'politician_twitter_handle3' in one_politician:
                    twitter_results = add_twitter_handle_to_next_politician_spot(
                        politician, one_politician['politician_twitter_handle3'])
                    if twitter_results['success']:
                        politician = twitter_results['politician']
                        if twitter_results['values_changed']:
                            values_changed = True
                    else:
                        results['status'] += twitter_results['status']
                if 'politician_twitter_handle4' in one_politician:
                    twitter_results = add_twitter_handle_to_next_politician_spot(
                        politician, one_politician['politician_twitter_handle4'])
                    if twitter_results['success']:
                        politician = twitter_results['politician']
                        if twitter_results['values_changed']:
                            values_changed = True
                    else:
                        results['status'] += twitter_results['status']
                if 'politician_twitter_handle5' in one_politician:
                    twitter_results = add_twitter_handle_to_next_politician_spot(
                        politician, one_politician['politician_twitter_handle5'])
                    if twitter_results['success']:
                        politician = twitter_results['politician']
                        if twitter_results['values_changed']:
                            values_changed = True
                    else:
                        results['status'] += twitter_results['status']
                if values_changed:
                    politician.save()
        else:
            politicians_not_processed += 1
            results = {
                'success': False,
                'status': 'Required value missing, cannot update or create',
                'politician_created':   False,
                'politician_found':     False,
                'politician':           Politician(),
            }

        if results['success']:
            if results['politician_created']:
                politicians_saved += 1
            else:
                politicians_updated += 1

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
