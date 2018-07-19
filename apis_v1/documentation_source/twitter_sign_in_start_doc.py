# apis_v1/documentation_source/twitter_sign_in_start_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def twitter_sign_in_start_doc_template_values(url_root):
    """
    Show documentation about twitterSignInStart
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
                            'Usually https://wevote.me/settings/account',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
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
                   '  "twitter_redirect_url": string, ' \
                   '(Where twitter wants We Vote to redirect the browser, with variables)\n' \
                   '  "voter_info_retrieved": boolean, ' \
                   '(if handled without redirect, was voter info retrieved from Twitter?)\n' \
                   '  "switch_accounts": boolean, (Was there an existing account for this Twitter account? ' \
                   'If true, a new voter_device_id is returned that links to this other We Vote account.)\n' \
                   '}'

    template_values = {
        'api_name': 'twitterSignInStart',
        'api_slug': 'twitterSignInStart',
        'api_introduction':
            "Flow chart showing entire process here: "
            "https://docs.google.com/drawings/d/1WdVFsPZl3aLM9wxGuPTW3veqP-5EmZKv36KWjTz5pbU/edit",
        'try_now_link': 'apis_v1:twitterSignInStartView',
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
