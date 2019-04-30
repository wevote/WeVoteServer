# apis_v1/documentation_source/organizations_found_on_url_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organizations_found_on_url_doc_template_values(url_root):
    """
    Show documentation about organizationsFoundOnUrl
    """
    required_query_parameter_list = [
        {
            'name':         'url_to_scan',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The URL we want to scan for organizations (typically for endorsements).',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'state_code',
            'value': 'string',  # boolean, integer, long, string
            'description': 'Limit the search to organizations in this state.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        # 'organization_id': '1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "organization_count": integer,\n' \
                   '  "organization_list": list\n' \
                   '   [\n' \
                   '     "organization_id": integer,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "organization_name": string,\n' \
                   '     "organization_twitter_handle": string,\n' \
                   '     "organization_facebook": string,\n' \
                   '     "organization_email": string,\n' \
                   '     "organization_website": string,\n' \
                   '     "organization_photo_url_medium": string,\n' \
                   '     "organization_photo_url_tiny": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'organizationsFoundOnUrl',
        'api_slug': 'organizationsFoundOnUrl',
        'api_introduction':
            "Call this to find all organizations that have a Twitter handle, Facebook page, or name on this page.",
        'try_now_link': 'apis_v1:organizationsFoundOnUrlView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
