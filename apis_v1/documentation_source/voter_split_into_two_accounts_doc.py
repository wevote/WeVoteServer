# apis_v1/documentation_source/voter_split_into_two_accounts_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_split_into_two_accounts_doc_template_values(url_root):
    """
    Show documentation about voterSplitIntoTwoAccounts
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'split_off_twitter',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Confirm that we want to split off the Twitter authorization from this account.',
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
            'code':         'MISSING_VOTER_ID_OR_ADDRESS_TYPE',
            'description':  'Cannot proceed. Missing variables voter_id or address_type while trying to save.',
        },
    ]

    try_now_link_variables_dict = {
        'split_off_twitter': True,
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "email_ownership_is_verified": boolean,\n' \
                   '  "email_secret_key_belongs_to_this_voter": boolean,\n' \
                   '  "email_address_found": boolean,\n' \
                   '}'

    template_values = {
        'api_name': 'voterSplitIntoTwoAccounts',
        'api_slug': 'voterSplitIntoTwoAccounts',
        'api_introduction':
            "Split one account into two accounts. Used for un-linking a Twitter account "
            "from the current voter account.",
        'try_now_link': 'apis_v1:voterSplitIntoTwoAccountsView',
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
