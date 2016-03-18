# apis_v1/documentation_source/voter_address_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_address_save_doc_template_values(url_root):
    """
    Show documentation about voterAddressSave
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
        {
            'name':         'text_for_map_search',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The address text a voter enters to identify the location tied to their ballot. '
                            '(Not mailing address.)',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
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
        {
            'code':         'VOTER_ADDRESS_SAVED',
            'description':  'Successfully saved',
        },
        {
            'code':         'MULTIPLE_MATCHING_ADDRESSES_FOUND',
            'description':  'Could not save. Multiple entries already saved.',
        },
        {
            'code':         'MISSING_POST_VARIABLE-ADDRESS',
            'description':  'Could not save. POST variable \'address\' is required.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "text_for_map_search": string,\n' \
                   '  "substituted_address_nearby": string,\n' \
                   '  "ballot_found": boolean,\n' \
                   '  "ballot_caveat": string,\n' \
                   '  "is_from_substituted_address": boolean,\n' \
                   '  "is_from_test_ballot": boolean,\n' \
                   '  "ballot_item_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "voter_id": integer,\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "google_ballot_placement": integer,\n' \
                   '     "local_ballot_order": integer,\n' \
                   '     "kind_of_ballot_item": string (CANDIDATE, MEASURE),\n' \
                   '     "id": integer,\n' \
                   '     "we_vote_id": string,\n' \
                   '     "candidate_list": list\n' \
                   '      [\n' \
                   '        "id": integer,\n' \
                   '        "we_vote_id": string,\n' \
                   '        "ballot_item_display_name": string,\n' \
                   '        "candidate_photo_url": string,\n' \
                   '        "order_on_ballot": integer,\n' \
                   '      ],\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterAddressSave',
        'api_slug': 'voterAddressSave',
        'api_introduction':
            "Save or create an address for the current voter. Then return the same results as we return with "
            "voterBallotItemsRetrieve.",
        'try_now_link': 'apis_v1:voterAddressSaveView',
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
