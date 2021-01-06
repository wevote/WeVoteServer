# apis_v1/documentation_source/organization_search_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_search_doc_template_values(url_root):
    """
    Show documentation about organizationSearch
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'organization_search_term',
            'value':        'string',  # boolean, integer, long, string
            'description':  'String of text used in AND search.',
        },
        {
            'name':         'organization_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Name of the organization that is displayed.',
        },
        {
            'name':         'organization_email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Contact email of the organization.',
        },
        {
            'name':         'organization_website',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Website of the organization.',
        },
        {
            'name':         'organization_twitter_handle',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Twitter handle of the organization.',
        },
        {
            'name':         'exact_match',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Require an exact match (case insensitive) of all fields submitted.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_id was not found.',
        },
        {
            'code':         'ORGANIZATION_SEARCH_ALL_TERMS_MISSING',
            'description':  'Cannot proceed. No search terms were provided.',
        },
        {
            'code':         'ORGANIZATIONS_RETRIEVED',
            'description':  'Successfully returned a list of Advocates that match search query.',
        },
        {
            'code':         'NO_ORGANIZATIONS_RETRIEVED',
            'description':  'Successfully searched, but no Advocates found that match search query.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "organization_search_term": string (the original search term passed in),\n' \
                   '  "organization_email": string (the original search term passed in),\n' \
                   '  "organization_name": string (the original search term passed in),\n' \
                   '  "organization_twitter_handle": string (the original search term passed in),\n' \
                   '  "organization_website": string (the original search term passed in),\n' \
                   '  "exact_match": boolean (did the search require exact match?),\n' \
                   '  "organizations_list": list\n' \
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
        'api_name': 'organizationSearch',
        'api_slug': 'organizationSearch',
        'api_introduction':
            "Find a list of all Advocates that match any of the search terms.",
        'try_now_link': 'apis_v1:organizationSearchView',
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
