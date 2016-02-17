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
        {
            'name':         'guess_if_no_address_saved',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Default = True. If True and the address is blank, make a guess at the voter\'s address '
                            'based on IP address, save it, then reach out to Google Civic to get the fresh ballot, and'
                            'finally, return the address.',
        },
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
        {
            'code':         'VOTER_ADDRESS_NOT_RETRIEVED',
            'description':  'retrieve_ballot_address_from_voter_id failed.',
        },
    ]

    try_now_link_variables_dict = {
        # 'voter_device_id': '',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "text_for_map_search": string (the value submitted and saved),\n' \
                   '  "address_type": string (one char: B = Ballot address),\n' \
                   '  "latitude": string (value from Google),\n' \
                   '  "longitude": string (value from Google),\n' \
                   '  "normalized_line1": string (value from Google),\n' \
                   '  "normalized_line2": string (value from Google),\n' \
                   '  "normalized_city": string (value from Google),\n' \
                   '  "normalized_state": string (value from Google),\n' \
                   '  "normalized_zip": string (value from Google),\n' \
                   '}'

    template_values = {
        'api_name': 'voterAddressRetrieve',
        'api_slug': 'voterAddressRetrieve',
        'api_introduction':
            "Retrieve the voter address for voter using voter_device_id.",
        'try_now_link': 'apis_v1:voterAddressRetrieveView',
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
