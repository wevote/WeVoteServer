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
            'name':         'ballot_returned_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the ballot at one address.',
        },
        {
            'name':         'ballot_location_shortcut',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for one ballot, identified by a string url.',
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
                   '  "google_civic_election_id": integer (if an error response),\n' \
                   '  "original_text_city": string,\n' \
                   '  "original_text_state": string,\n' \
                   '  "original_text_zip": string,\n' \
                   '  "text_for_map_search": string (if an error response),\n' \
                   '  "substituted_address_nearby": string,\n' \
                   '  "substituted_address_city": string,\n' \
                   '  "substituted_address_state": string,\n' \
                   '  "substituted_address_zip": string,\n' \
                   '  "ballot_found": boolean (if an error response),\n' \
                   '  "ballot_caveat": string (if an error response),\n' \
                   '  "is_from_substituted_address": boolean,\n' \
                   '  "is_from_test_ballot": boolean (if an error response),\n' \
                   '  "ballot_item_list": list\n' \
                   '   [\n' \
                   '     "id": integer,\n' \
                   '     "we_vote_id": string,\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "google_ballot_placement": integer,\n' \
                   '     "local_ballot_order": integer,\n' \
                   '     "kind_of_ballot_item": string (CANDIDATE, MEASURE),\n' \
                   '     "measure_subtitle": string (if kind_of_ballot_item is MEASURE)\n' \
                   '     "measure_text": string (if kind_of_ballot_item is MEASURE)\n' \
                   '     "measure_url": string (if kind_of_ballot_item is MEASURE)\n' \
                   '     "yes_vote_description": string (if kind_of_ballot_item is MEASURE)\n' \
                   '     "no_vote_description": string (if kind_of_ballot_item is MEASURE)\n' \
                   '     "candidate_list": list (if kind_of_ballot_item is CANDIDATE)\n' \
                   '      [\n' \
                   '        "id": integer,\n' \
                   '        "we_vote_id": string,\n' \
                   '        "ballot_item_display_name": string,\n' \
                   '        "ballotpedia_candidate_id": integer,\n' \
                   '        "ballotpedia_candidate_summary": string,\n' \
                   '        "ballotpedia_candidate_url": string,\n' \
                   '        "ballotpedia_person_id": integer,\n' \
                   '        "candidate_email": string,\n' \
                   '        "candidate_phone": string,\n' \
                   '        "candidate_photo_url_large": string,\n' \
                   '        "candidate_photo_url_medium": string,\n' \
                   '        "candidate_photo_url_tiny": string,\n' \
                   '        "candidate_url": string,\n' \
                   '        "candidate_contact_form_url": string,\n' \
                   '        "contest_office_id": integer,\n' \
                   '        "contest_office_name": string,\n' \
                   '        "contest_office_we_vote_id": string,\n' \
                   '        "facebook_url": string,\n' \
                   '        "google_civic_election_id": integer,\n' \
                   '        "instagram_handle": string,\n' \
                   '        "instagram_followers_count": string,\n' \
                   '        "kind_of_ballot_item": string,\n' \
                   '        "maplight_id": string,\n' \
                   '        "ocd_division_id": string,\n' \
                   '        "order_on_ballot": integer,\n' \
                   '        "party": string,\n' \
                   '        "politician_id": string,\n' \
                   '        "politician_we_vote_id": string,\n' \
                   '        "state_code": string,\n' \
                   '        "twitter_url": string,\n' \
                   '        "twitter_handle": string,\n' \
                   '        "twitter_description": string,\n' \
                   '        "twitter_followers_count": integer,\n' \
                   '        "youtube_url": string,\n' \
                   '        "is_battleground_race": boolean,\n' \
                   '        "withdrawn_from_election": boolean,\n' \
                   '        "withdrawal_date": date,\n' \
                   '      ],\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterBallotItemsRetrieve',
        'api_slug': 'voterBallotItemsRetrieve',
        'api_introduction':
            "Request a skeleton of ballot data for this voter location, so that the web_app has all the ids "
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
