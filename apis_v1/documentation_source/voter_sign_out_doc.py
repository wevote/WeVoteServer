# apis_v1/documentation_source/voter_sign_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_sign_out_doc_template_values(url_root):
    """
    Show documentation about voterSignOut
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
            'name':         'sign_out_all_devices',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'This is \'False\' by default. If set to \'True\', sign out all other devices signed into '
                            'this account by deleting all voter_device_id\'s linked to this voter account.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'DELETE_VOTER_DEVICE_LINK_SUCCESSFUL',
            'description':  'The voter device link was successfully removed.',
        },
        {
            'code':         'DELETE_ALL_VOTER_DEVICE_LINKS_SUCCESSFUL',
            'description':  'All voter device links for this voter were successfully removed.',
        },
        {
            'code':         'DELETE_VOTER_DEVICE_LINK-MISSING_VARIABLES',
            'description':  'voter_id could not be found from the voter_device_id passed in.',
        },
        {
            'code':         'DELETE_ALL_VOTER_DEVICE_LINKS-MISSING_VARIABLES',
            'description':  'voter_id could not be found from the voter_device_id passed in.',
        },
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'voterSignOut',
        'api_slug': 'voterSignOut',
        'api_introduction':
            "Sign out from this account. (Delete this voter_device_id from the database.)",
        'try_now_link': 'apis_v1:voterSignOutView',
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
