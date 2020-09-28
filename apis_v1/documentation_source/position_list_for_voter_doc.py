# apis_v1/documentation_source/position_list_for_voter_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_list_for_voter_doc_template_values(url_root):
    """
    Show documentation about positionListForVoter
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
            'name':         'stance',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is ANY_STANCE. '
                            'Other options include SUPPORT, STILL_DECIDING, INFO_ONLY, NO_STANCE, OPPOSE, '
                            'PERCENT_RATING',
        },
        {
            'name':         'friends_vs_public',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is FRIENDS_AND_PUBLIC. '
                            'Other options include FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular election. If not provided, return all positions'
                            ' for this organization. If this variable is included, state_code will be ignored.',
        },
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The us state we want ballot item positions for. '
        },
        {
            'name':         'show_only_this_election',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The default is \'True\'. Only show positions about things on the current ballot. ',
        },
        {
            'name':         'show_all_other_elections',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The default is \'False\'. Show the positions for this ballot item that are NOT on this '
                            'voter\'s ballot.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_id was not found.',
        },
        {
            'code':         'UNABLE_TO_RETRIEVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING',
            'description':  'Cannot proceed. Neither candidate_id nor measure_id were included.',
        },
        {
            'code':         'SUCCESSFUL_RETRIEVE_OF_POSITIONS',
            'description':  'The number of opposes for this ballot item was retrieved.',
        },
        {
            'code':         'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED',
            'description':  'The number of organizations that oppose this ballot item that voter is NOT following.',
        },
    ]

    try_now_link_variables_dict = {
        'stance': 'ANY_STANCE',
        'friends_vs_public': 'FRIENDS_AND_PUBLIC',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '  "friends_vs_public": string ' \
                   '   (One of these: \'FRIENDS_ONLY\', \'PUBLIC_ONLY\', \'FRIENDS_AND_PUBLIC\'),\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "voter_display_name": string,\n' \
                   '  "voter_image_url_https_large": string,\n' \
                   '  "voter_image_url_https_medium": string,\n' \
                   '  "voter_image_url_https_tiny": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "state_code": string,\n' \
                   '  "position_list": list\n' \
                   '  "show_only_this_election": boolean (True if only returning positions for voter\'s ballot),\n' \
                   '  "show_all_other_elections": boolean (True if returning positions NOT on voter\'s ballot,\n' \
                   '   [\n' \
                   '     "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '     "ballot_item_id": integer,\n' \
                   '     "ballot_item_image_url_https_large": string,\n' \
                   '     "ballot_item_image_url_https_medium": string,\n' \
                   '     "ballot_item_image_url_https_tiny": string,\n' \
                   '     "ballot_item_twitter_handle": string,\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "ballot_item_political_party": string,\n' \
                   '     "ballot_item_state_code": string,\n' \
                   '     "contest_office_id": integer,\n' \
                   '     "contest_office_we_vote_id": string,\n' \
                   '     "contest_office_name": string (The name of the office if kind_of_ballot_item is CANDIDATE),\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "is_support": boolean,\n' \
                   '     "is_positive_rating": boolean,\n' \
                   '     "is_support_or_positive_rating": boolean,\n' \
                   '     "is_oppose": boolean,\n' \
                   '     "is_negative_rating": boolean,\n' \
                   '     "is_oppose_or_negative_rating": boolean,\n' \
                   '     "is_information_only": boolean,\n' \
                   '     "kind_of_ballot_item": string, ' \
                   '      (One of these: \'CANDIDATE\', \'MEASURE\', \'OFFICE\', \'UNKNOWN\')\n' \
                   '     "last_updated": string,\n' \
                   '     "more_info_url": string,\n' \
                   '     "position_we_vote_id": string,\n' \
                   '     "position_ultimate_election_date": integer,\n' \
                   '     "position_year": integer,\n' \
                   '     "race_office_level": string, ' \
                   '     "statement_text": string,\n' \
                   '     "statement_html": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'positionListForVoter',
        'api_slug': 'positionListForVoter',
        'api_introduction':
            "A list of all positions (support/oppose/info) held by this voter. ",
        'try_now_link': 'apis_v1:positionListForVoterView',
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
