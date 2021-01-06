# apis_v1/documentation_source/organization_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_retrieve_doc_template_values(url_root):
    """
    Show documentation about organizationRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'organization_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Internal database unique identifier (one identifier required, '
                            'either organization_id or organization_we_vote_id)',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'We Vote unique identifier so we can move Advocates from server-to-server '
                            '(one identifier required, either id or we_vote_id)',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    potential_status_codes_list = [
        {
            'code':         'ORGANIZATION_FOUND_WITH_ID',
            'description':  'The organization was found using the internal id',
        },
        {
            'code':         'ORGANIZATION_FOUND_WITH_WE_VOTE_ID',
            'description':  'The organization was found using the we_vote_id',
        },
        {
            'code':         'ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING',
            'description':  'One identifier required. Neither provided.',
        },
        {
            'code':         'ORGANIZATION_NOT_FOUND_WITH_ID',
            'description':  'The organization was not found with internal id.',
        },
        {
            'code':         'ERROR_<specifics here>',
            'description':  'An internal description of what error prevented the retrieve of the organization.',
        },
    ]
    try_now_link_variables_dict = {
        'organization_we_vote_id': 'wv85org1',
    }

    # Changes made here should also be made in organizations_followed_retrieved
    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "facebook_id": integer,\n' \
                   '  "organization_banner_url": string,\n' \
                   '  "organization_description": string,\n' \
                   '  "organization_email": string,\n' \
                   '  "organization_facebook": string,\n' \
                   '  "organization_id": integer (the id of the organization found),\n' \
                   '  "organization_instagram_handle": string,\n' \
                   '  "organization_name": string (value from Google),\n' \
                   '  "organization_photo_url_large": string,\n' \
                   '  "organization_photo_url_medium": string,\n' \
                   '  "organization_photo_url_tiny": string,\n' \
                   '  "organization_type": string,\n' \
                   '  "organization_twitter_handle": string (twitter address),\n' \
                   '  "organization_we_vote_id": string (the organization identifier that moves server-to-server),\n' \
                   '  "organization_website": string (website address),\n' \
                   '  "twitter_description": string,\n' \
                   '  "twitter_followers_count": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'organizationRetrieve',
        'api_slug': 'organizationRetrieve',
        'api_introduction':
            "Retrieve the organization using organization_id (first choice) or we_vote_id.",
        'try_now_link': 'apis_v1:organizationRetrieveView',
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
