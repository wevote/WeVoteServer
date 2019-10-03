# apis_v1/documentation_source/voter_verify_secret_code_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_verify_secret_code_doc_template_values(url_root):
    """
    Show documentation about voterVerifySecretCode
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server. ',
        },
        {
            'name': 'secret_code',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The six digit code to verify.',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         'voter_device_id',
        #     'value':        'string',  # boolean, integer, long, string
        #     'description':  'An 88 character unique identifier linked to a voter record on the server. '
        #                     'If not provided, a new voter_device_id (and voter entry) '
        #                     'will be generated, and the voter_device_id will be returned.',
        # },
    ]

    potential_status_codes_list = [
        # {
        #     'code':         'VALID_VOTER_DEVICE_ID_MISSING',
        #     'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        # },
        # {
        #     'code':         'VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_RETRIEVE',
        #     'description':  'There is no voter_id attached to that voter_device_id',
        # },
        # {
        #     'code':         'VOTER_ID_COULD_NOT_BE_RETRIEVED',
        #     'description':  'Unable to retrieve voter_id, although voter_id was found linked to voter_device_id',
        # },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (True as long as no db errors),\n' \
                   '  "number_of_tries_remaining": integer,\n' \
                   '  "secret_code_verified": boolean,\n' \
                   '  "voter_must_request_new_code": boolean,\n' \
                   '  "voter_secret_code_requests_locked": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterVerifySecretCode',
        'api_slug': 'voterVerifySecretCode',
        'api_introduction': "Voter submits this six digit code to verify that they received an SMS message or email.",
        'try_now_link': 'apis_v1:voterVerifySecretCodeView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes': "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
