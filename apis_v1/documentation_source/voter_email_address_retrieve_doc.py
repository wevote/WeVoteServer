# apis_v1/documentation_source/voter_email_address_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_email_address_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterEmailAddressRetrieve
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
    ]

    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            'description':  'No voter could be found from the voter_device_id',
        },
    ]

    try_now_link_variables_dict = {
        # 'voter_device_id': '',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "email_address_list_found": boolean,\n' \
                   '  "email_address_list": list\n' \
                   '   [\n' \
                   '     "normalized_email_address": string,\n' \
                   '     "primary_email_address": boolean,\n' \
                   '     "email_permanent_bounce": boolean,\n' \
                   '     "email_ownership_is_verified": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "email_we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterEmailAddressRetrieve',
        'api_slug': 'voterEmailAddressRetrieve',
        'api_introduction':
            "Retrieve a list of all of the email addresses for voter using voter_device_id.",
        'try_now_link': 'apis_v1:voterEmailAddressRetrieveView',
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
