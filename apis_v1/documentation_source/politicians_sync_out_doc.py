# apis_v1/documentation_source/politicians_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def politicians_sync_out_doc_template_values(url_root):
    """
    Show documentation about politiciansSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'politician_search',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the politicians retrieved to those found by this search string.',
        },
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the politicians entries retrieved to those in a particular state.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'state_code': 'ca',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "first_name": string,\n' \
                   '  "middle_name": string,\n' \
                   '  "last_name": string,\n' \
                   '  "politician_name": string,\n' \
                   '  "google_civic_candidate_name": string,\n' \
                   '  "full_name_assembled": string,\n' \
                   '  "gender": string,\n' \
                   '  "birth_date": string,\n' \
                   '  "bioguide_id": string,\n' \
                   '  "thomas_id": string,\n' \
                   '  "lis_id": string,\n' \
                   '  "govtrack_id": string,\n' \
                   '  "opensecrets_id": string,\n' \
                   '  "vote_smart_id": string,\n' \
                   '  "fec_id": string,\n' \
                   '  "cspan_id": string,\n' \
                   '  "wikipedia_id": string,\n' \
                   '  "ballotpedia_id": string,\n' \
                   '  "house_history_id": string,\n' \
                   '  "maplight_id": string,\n' \
                   '  "washington_post_id": string,\n' \
                   '  "icpsr_id": string,\n' \
                   '  "political_party": string,\n' \
                   '  "state_code": string,\n' \
                   '  "politician_url": string,\n' \
                   '  "politician_twitter_handle": string,\n' \
                   '  "politician_twitter_handle2": string,\n' \
                   '  "politician_twitter_handle3": string,\n' \
                   '  "politician_twitter_handle4": string,\n' \
                   '  "politician_twitter_handle5": string,\n' \
                   '  "we_vote_hosted_profile_image_url_large": string,\n' \
                   '  "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '  "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '  "ctcl_uuid": string,\n' \
                   '  "politician_facebook_id": string,\n' \
                   '  "politician_phone_number": string,\n' \
                   '  "politician_googleplus_id": string,\n' \
                   '  "politician_youtube_id": string,\n' \
                   '  "politician_email_address": string DEPRECATING,\n' \
                   '  "politician_email": string,\n' \
                   '  "politician_email2": string,\n' \
                   '  "politician_email3": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'politiciansSyncOut',
        'api_slug': 'politiciansSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:politiciansSyncOutView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
