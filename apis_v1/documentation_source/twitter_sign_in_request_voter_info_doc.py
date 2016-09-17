# apis_v1/documentation_source/twitter_sign_in_request_voter_info_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def twitter_sign_in_request_voter_info_doc_template_values(url_root):
    """
    Show documentation about twitterSignInRequestVoterInfo
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'return_url',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The URL where the browser should be redirected once authenticated. '
                            'Usually https://wevote.me/more/sign_in',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'switch_accounts_if_needed',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'If a We Vote account already exists for this Twitter handle, create new session tied to'
                           ' that account. If this variable not passed in, defaults to true.',
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
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "twitter_handle": string,\n' \
                   '  "twitter_handle_found": boolean,\n' \
                   '  "voter_info_retrieved": boolean,\n' \
                   '  "switch_accounts": boolean,\n' \
                   '  "return_url": string, (This is the final url to return to once authentication is complete. ' \
                   'If set, the twitterSignInRequestAccessToken api redirects to the twitterSignInRequestVoterInfo ' \
                   'api before redirecting to the value in return_url)\n' \
                   '}'

    template_values = {
        'api_name': 'twitterSignInRequestVoterInfo',
        'api_slug': 'twitterSignInRequestVoterInfo',
        'api_introduction':
            "Flow chart showing entire process here: "
            "https://docs.google.com/drawings/d/1WdVFsPZl3aLM9wxGuPTW3veqP-5EmZKv36KWjTz5pbU/edit",
        'try_now_link': 'apis_v1:twitterSignInRequestVoterInfoView',
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
