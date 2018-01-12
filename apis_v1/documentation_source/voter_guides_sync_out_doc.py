# apis_v1/documentation_source/voter_guides_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guides_sync_out_doc_template_values(url_root):
    """
    Show documentation about voterGuidesSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit the voter_guides retrieved to those for this google_civic_election_id.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "display_name": string,\n' \
                   '  "google_civic_election_id": string,\n' \
                   '  "image_url": string,\n' \
                   '  "last_updated": string,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "owner_we_vote_id": string,\n' \
                   '  "public_figure_we_vote_id": string,\n' \
                   '  "twitter_description": string,\n' \
                   '  "twitter_followers_count": integer,\n' \
                   '  "twitter_handle": string,\n' \
                   '  "vote_smart_time_span": string,\n' \
                   '  "voter_guide_owner_type": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'voterGuidesSyncOut',
        'api_slug': 'voterGuidesSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:voterGuidesSyncOutView',
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
