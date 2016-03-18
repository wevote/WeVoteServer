# apis_v1/documentation_source/voter_ballot_items_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_ballot_items_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterBallotItemsRetrieve
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
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular election. If not provided, use the most recent '
                            'ballot for the voter\'s address.',
        },
        {
            'name':         'use_test_election',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'If you need to request a test election, pass this with the value \'True\'. Note that '
                            'text_for_map_search (either passed into this API endpoint as a value, or previously saved '
                            'with voterAddressSave) is required with every election, including the test election.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'A valid voter_id was not found from voter_device_id. Cannot proceed.',
        },
        {
            'code':         'MISSING_GOOGLE_CIVIC_ELECTION_ID',
            'description':  'A valid google_civic_election_id not found. Cannot proceed.',
        },
        {
            'code':         'VOTER_BALLOT_ITEMS_RETRIEVED',
            'description':  'Ballot items were found.',
        },
    ]

    try_now_link_variables_dict = {
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
        'api_name': 'voterBallotItemsRetrieve',
        'api_slug': 'voterBallotItemsRetrieve',
        'api_introduction':
            "Request a skeleton of ballot data for this voter location, so that the web_app has all of the ids "
            "it needs to make more requests for data about each ballot item.",
        'try_now_link': 'apis_v1:voterBallotItemsRetrieveView',
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
