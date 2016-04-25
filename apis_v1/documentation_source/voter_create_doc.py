# apis_v1/documentation_source/voter_create_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_create_doc_template_values(url_root):
    """
    Show documentation about voterCreate
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server. '
                            'If you do not pass in a voter_device_id, generate one, link '
                            'it to the newly created voter, and return it.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_ALREADY_EXISTS',
            'description':  'A voter account is already linked with that voter_device_id',
        },
        {
            'code':         'VOTER_CREATED',
            'description':  'A voter account was successfully created',
        },
        {
            'code':         'VOTER_NOT_CREATED',
            'description':  'A voter account could not be created',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": status string,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_id": integer,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterCreate',
        'api_slug': 'voterCreate',
        'api_introduction':
            "Generate a voter account for this voter_device_id",
        'try_now_link': 'apis_v1:voterCreateView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
