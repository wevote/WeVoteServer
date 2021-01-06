# apis_v1/documentation_source/organizations_followed_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organizations_followed_retrieve_doc_template_values(url_root):
    """
    Show documentation about organizationsFollowedRetrieve
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
            'name':         'auto_followed_from_twitter_suggestion',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'True default retrieve auto followed Advocates.'
                            'If False, retrieve all Advocates followed by voter'
                            '(includes twitter auto followed Advocates)',
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
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'auto_followed_from_twitter_suggestion': 'False',
    }

    # Changes made here should also be made in organizations_retrieve
    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "organization_list": list\n' \
                   '   [\n' \
                   '     "organization_id": integer (the id of the organization found),\n' \
                   '     "organization_we_vote_id": string (the organization ' \
                   'identifier that moves server-to-server),\n' \
                   '     "organization_name": string (value from Google),\n' \
                   '     "organization_website": string (website address),\n' \
                   '     "organization_twitter_handle": string (twitter address),\n' \
                   '     "twitter_followers_count": integer,\n' \
                   '     "twitter_description": string,\n' \
                   '     "organization_email": string,\n' \
                   '     "organization_facebook": string,\n' \
                   '     "organization_photo_url_large": string,\n' \
                   '     "organization_photo_url_medium": string,\n' \
                   '     "organization_photo_url_tiny": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'organizationsFollowedRetrieve',
        'api_slug': 'organizationsFollowedRetrieve',
        'api_introduction':
            "A list of all Advocates followed by this voter includes automatically followed from twitter. "
            "(Or show the Advocates this voter is following automatically from twitter only "
            "if auto_followed_from_twitter_suggestion is True.)",
        'try_now_link': 'apis_v1:organizationsFollowedRetrieveView',
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
