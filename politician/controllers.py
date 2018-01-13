# politician/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from politician.models import Politician, PoliticianManager
from config.base import get_environment_variable
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, process_request_from_master, convert_to_int

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut


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
    for one_politician in structured_json:
        politician_name = one_politician['politician_name'] if 'politician_name' in one_politician else ''
        politician_we_vote_id = one_politician['we_vote_id'] if 'we_vote_id' in one_politician else ''

        if positive_value_exists(politician_name) and positive_value_exists(politician_we_vote_id):
            proceed_to_update_or_create = True
        else:
            proceed_to_update_or_create = False
        if proceed_to_update_or_create:
            updated_politician_values = {
                'politician_name': politician_name,
                'we_vote_id': politician_we_vote_id,
            }
            if 'first_name' in one_politician:
                updated_politician_values['first_name'] = one_politician['first_name']
            if 'middle_name' in one_politician:
                updated_politician_values['middle_name'] = one_politician['middle_name']
            if 'last_name' in one_politician:
                updated_politician_values['last_name'] = one_politician['last_name']
            if 'politician_name' in one_politician:
                updated_politician_values['politician_name'] = one_politician['politician_name']
            if 'google_civic_candidate_name' in one_politician:
                updated_politician_values['google_civic_candidate_name'] = one_politician['google_civic_candidate_name']
            if 'full_name_assembled' in one_politician:
                updated_politician_values['full_name_assembled'] = one_politician['full_name_assembled']
            if 'gender' in one_politician:
                updated_politician_values['gender'] = one_politician['gender']
            if 'birth_date' in one_politician:
                updated_politician_values['birth_date'] = one_politician['birth_date']
            if 'bioguide_id' in one_politician:
                updated_politician_values['bioguide_id'] = one_politician['bioguide_id']
            if 'thomas_id' in one_politician:
                updated_politician_values['thomas_id'] = one_politician['thomas_id']
            if 'lis_id' in one_politician:
                updated_politician_values['lis_id'] = one_politician['lis_id']
            if 'govtrack_id' in one_politician:
                updated_politician_values['govtrack_id'] = one_politician['govtrack_id']
            if 'opensecrets_id' in one_politician:
                updated_politician_values['opensecrets_id'] = one_politician['opensecrets_id']
            if 'vote_smart_id' in one_politician:
                updated_politician_values['vote_smart_id'] = one_politician['vote_smart_id']
            if 'fec_id' in one_politician:
                updated_politician_values['fec_id'] = one_politician['fec_id']
            if 'cspan_id' in one_politician:
                updated_politician_values['cspan_id'] = one_politician['cspan_id']
            if 'wikipedia_id' in one_politician:
                updated_politician_values['wikipedia_id'] = one_politician['wikipedia_id']
            if 'ballotpedia_id' in one_politician:
                updated_politician_values['ballotpedia_id'] = one_politician['ballotpedia_id']
            if 'house_history_id' in one_politician:
                updated_politician_values['house_history_id'] = one_politician['house_history_id']
            if 'maplight_id' in one_politician:
                updated_politician_values['maplight_id'] = one_politician['maplight_id']
            if 'washington_post_id' in one_politician:
                updated_politician_values['washington_post_id'] = one_politician['washington_post_id']
            if 'icpsr_id' in one_politician:
                updated_politician_values['icpsr_id'] = one_politician['icpsr_id']
            if 'political_party' in one_politician:
                updated_politician_values['political_party'] = one_politician['political_party']
            if 'state_code' in one_politician:
                updated_politician_values['state_code'] = one_politician['state_code']
            if 'politician_url' in one_politician:
                updated_politician_values['politician_url'] = one_politician['politician_url']
            if 'politician_twitter_handle' in one_politician:
                updated_politician_values['politician_twitter_handle'] = one_politician['politician_twitter_handle']
            if 'we_vote_hosted_profile_image_url_large' in one_politician:
                updated_politician_values['we_vote_hosted_profile_image_url_large'] = \
                    one_politician['we_vote_hosted_profile_image_url_large']
            if 'we_vote_hosted_profile_image_url_medium' in one_politician:
                updated_politician_values['we_vote_hosted_profile_image_url_medium'] = \
                    one_politician['we_vote_hosted_profile_image_url_medium']
            if 'we_vote_hosted_profile_image_url_tiny' in one_politician:
                updated_politician_values['we_vote_hosted_profile_image_url_tiny'] = \
                    one_politician['we_vote_hosted_profile_image_url_tiny']
            if 'ctcl_uuid' in one_politician:
                updated_politician_values['ctcl_uuid'] = one_politician['ctcl_uuid']
            if 'politician_facebook_id' in one_politician:
                updated_politician_values['politician_facebook_id'] = one_politician['politician_facebook_id']
            if 'politician_phone_number' in one_politician:
                updated_politician_values['politician_phone_number'] = one_politician['politician_phone_number']
            if 'politician_googleplus_id' in one_politician:
                updated_politician_values['politician_googleplus_id'] = one_politician['politician_googleplus_id']
            if 'politician_youtube_id' in one_politician:
                updated_politician_values['politician_youtube_id'] = one_politician['politician_youtube_id']
            if 'politician_email_address' in one_politician:
                updated_politician_values['politician_email_address'] = one_politician['politician_email_address']

            results = politician_manager.update_or_create_politician(updated_politician_values, politician_we_vote_id)
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

    politicians_results = {
        'success':          True,
        'status':           "POLITICIANS_IMPORT_PROCESS_COMPLETE",
        'saved':            politicians_saved,
        'updated':          politicians_updated,
        'not_processed':    politicians_not_processed,
    }
    return politicians_results
