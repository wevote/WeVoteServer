# apis_v1/documentation_source/voter_ballot_items_retrieve_from_google_civic_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_ballot_items_retrieve_from_google_civic_doc_template_values(url_root):
    """
    Show documentation about voterBallotItemsRetrieveFromGoogleCivic
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string (from cookie)',  # boolean, integer, long, string
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
            'name':         'text_for_map_search',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The voter\'s address we want to look up in the Google Civic API. If blank, we look this '
                            'value up from the database.',
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
            'code':         'RETRIEVED_AND_STORED_BALLOT_FOR_VOTER',
            'description':  'Ballot items were found and saved.',
        },
        {
            'code':         'MISSING_ADDRESS_TEXT_FOR_BALLOT_SEARCH',
            'description':  'A voter address was not passed in.',
        },
        {
            'code':         'GOOGLE_CIVIC_API_ERROR: Election unknown',
            'description':  'There is no upcoming election for this address. Or, the election has passed and the '
                            'election data is no longer available.',
        },
        {
            'code':         'GOOGLE_CIVIC_API_ERROR: Election is over',
            'description':  'The ballot data for this election is not being hosted by Google Civic any more.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "election_data_retrieved": boolean,\n' \
                   '  "polling_location_retrieved": boolean,\n' \
                   '  "contests_retrieved": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "text_for_map_search": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterBallotItemsRetrieveFromGoogleCivic',
        'api_slug': 'voterBallotItemsRetrieveFromGoogleCivic',
        'api_introduction':
            "Tell the We Vote server to reach out to the Google Civic API and retrieve a list of "
            "ballot items for the current voter (based on the address saved with voterAddressSave), "
            "and store them in the We Vote database so we can display them with voterBallotItemsRetrieve, "
            "and other API calls.",
        'try_now_link': 'apis_v1:voterBallotItemsRetrieveFromGoogleCivicView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "If the google_civic_election_id is 2000 then we are looking at test election data.",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
