# apis_v1/documentation_source/voter_address_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_address_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterAddressRetrieve
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
            'description':  'An 88 character unique identifier (from cookie - not URL variable) linked to '
                            'a voter record on the server',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "address": string (the value submitted and saved),\n' \
                   '  "address_type": string (one char: B = Ballot address),\n' \
                   '  "latitude": string (value from Google),\n' \
                   '  "longitude": string (value from Google),\n' \
                   '  "normalized_line1": string (value from Google),\n' \
                   '  "normalized_line2": string (value from Google),\n' \
                   '  "normalized_city": string (value from Google),\n' \
                   '  "normalized_state": string (value from Google),\n' \
                   '  "normalized_zip": string (value from Google),\n' \
                   '}'
    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            'description':  'No voter could be found from the voter_device_id',
        },
        {
            'code':         'VOTER_ADDRESS_NOT_RETRIEVED',
            'description':  'retrieve_ballot_address_from_voter_id failed.',
        },
    ]

    template_values = {
        'api_name': 'voterAddressRetrieve',
        'api_slug': 'voterAddressRetrieve',
        'api_introduction':
            "Retrieve the voter address for voter using voter_device_id.",
        'try_now_link': 'apis_v1:voterAddressRetrieveView',
        'try_now_link_variables': '',
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
