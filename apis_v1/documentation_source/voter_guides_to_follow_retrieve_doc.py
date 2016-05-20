# apis_v1/documentation_source/voter_guides_to_follow_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guides_to_follow_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidesToFollowRetrieve
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
            'name':         'kind_of_ballot_item',
            'value':        'string',  # boolean, integer, long, string
            'description':  'What is the type of ballot item that we are retrieving? '
                            '(kind_of_ballot_item is either "OFFICE", "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular ballot item. If this variable is provided, '
                            'we want to retrieve all of the voter guides that have something to say about this '
                            'particular ballot item.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular election. If not provided, use the most recent '
                            'ballot for the voter\'s address.',
        },
        {
            'name':         'search_string',
            'value':        'string',  # boolean, integer, long, string
            'description':  'A string of keyword(s) to search for (to find twitter handle or org name).',
        },
        {
            'name':         'use_test_election',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'If you need to request a test election, pass this with the value \'True\'. Note that '
                            'text_for_map_search (either passed into this API endpoint as a value, or previously saved '
                            'with voterAddressSave) is required with every election, including the test election.',
        },
        {
            'name':         'maximum_number_to_retrieve',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Defaults to 20 voter guides. Enter a value to set your own limit.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VOTER_GUIDES_TO_FOLLOW_RETRIEVED',
            'description':  'At least one voter guide was returned.',
        },
        {
            'code':         'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'NO_VOTER_GUIDES_FOUND',
            'description':  'No voter guides exist in the database matching the search terms.',
        },
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_we_vote_id': 'wv01cand2897',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "search_string": string,\n' \
                   '  "maximum_number_to_retrieve": integer,\n' \
                   '  "voter_guides": list\n' \
                   '   [\n' \
                   '     "voter_guide_display_name": string (Name of this org or person),\n' \
                   '     "voter_guide_owner_type": ORGANIZATION, PUBLIC_FIGURE, VOTER),\n' \
                   '     "we_vote_id": string (We Vote ID of the voter guide),\n' \
                   '     "organization_we_vote_id": string (We Vote ID for the org that owns the voter guide),\n' \
                   '     "public_figure_we_vote_id": string (We Vote ID for the person that owns the voter guide),\n' \
                   '     "voter_guide_image_url": string (We Vote ID for the person that owns the voter guide),\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M),\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "twitter_description": string,\n' \
                   '     "twitter_followers_count": integer,\n' \
                   '     "twitter_handle": integer,\n' \
                   '     "owner_voter_id": integer TO BE DEPRECATED,\n' \
                   '   ],\n' \
                   '}\n'

    template_values = {
        'api_name': 'voterGuidesToFollowRetrieve',
        'api_slug': 'voterGuidesToFollowRetrieve',
        'api_introduction':
            "Look up the election and ballot items that this person is focused on. Return the organizations, "
            "public figures, and voters that have shared voter guides available to follow. Take into consideration "
            "which voter guides the voter has previously ignored. "
            "Do not show voter guides the voter is already following."
            "If neither ballot_item_we_vote_id (paired with kind_of_ballot_item) nor google_civic_election_id are"
            "passed in, and google_civic_election_id is set to '0', then simply return a list of voter guides "
            "that haven't been followed yet. If google_civic_election_id is NOT set to 0, the routine tries to"
            "figure out which election is being looked at in the voter_device_link or the voter_address.",
        'try_now_link': 'apis_v1:voterGuidesToFollowRetrieveView',
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
