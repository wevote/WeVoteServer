# apis_v1/documentation_source/facebook_sign_in_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def facebook_sign_in_doc_template_values(url_root):
    """
    Show documentation about facebookSignIn
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
            'name':         'facebook_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The Facebook big integer id',
        },
        {
            'name':         'facebook_email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Email address from Facebook',
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
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "facebook_id": integer,\n' \
                   '  "facebook_email": string,\n' \
                   '}'

    template_values = {
        'api_name': 'facebookSignIn',
        'api_slug': 'facebookSignIn',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:facebookSignInView',
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
