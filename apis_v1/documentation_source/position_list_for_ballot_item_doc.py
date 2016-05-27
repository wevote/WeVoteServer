# apis_v1/documentation_source/position_list_for_ballot_item_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_list_for_ballot_item_doc_template_values(url_root):
    """
    Show documentation about positionListForBallotItem
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
        {
            'name':         'kind_of_ballot_item',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The kind of ballot item we want positions for. '
                            '(kind_of_ballot_item is either "OFFICE", "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier of the ballot item we want positions for. '
                            '(either ballot_item_id OR ballot_item_we_vote_id required -- not both. '
                            'If it exists, ballot_item_id is used instead of ballot_item_we_vote_id)',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this ballot_item across all networks '
                            '(either ballot_item_id OR ballot_item_we_vote_id required -- not both. '
                            'NOTE: In the future we might support other identifiers used in the industry.',
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
            'name':         'show_positions_this_voter_follows',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'True default shows the positions of organizations, public figures and '
                            'friends this voter is following. '
                            'If False, show positions that the voter is NOT following.',
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
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_id': '5655',
        'show_positions_this_voter_follows': 'False',
        'stance': 'ANY_STANCE',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '  "kind_of_ballot_item": string (CANDIDATE, MEASURE), ' \
                   '   (One of these: \'CANDIDATE\', \'MEASURE\', \'OFFICE\', \'UNKNOWN\',)\n' \
                   '  "ballot_item_id": integer,\n' \
                   '  "ballot_item_we_vote_id": string,\n' \
                   '  "position_list": list\n' \
                   '   [\n' \
                   '     "position_id": integer,\n' \
                   '     "position_we_vote_id": string,\n' \
                   '     "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '     "speaker_display_name": string,\n' \
                   '     "speaker_image_url_https": string,\n' \
                   '     "speaker_twitter_handle": string,\n' \
                   '     "speaker_type": string, ' \
                   '      (One of these: \'ORGANIZATION\', \'VOTER\', \'PUBLIC_FIGURE\', \'UNKNOWN\',)\n' \
                   '     "speaker_id": integer,\n' \
                   '     "speaker_we_vote_id": string,\n' \
                   '     "is_support": boolean,\n' \
                   '     "is_positive_rating": boolean,\n' \
                   '     "is_support_or_positive_rating": boolean,\n' \
                   '     "is_oppose": boolean,\n' \
                   '     "is_negative_rating": boolean,\n' \
                   '     "is_oppose_or_negative_rating": boolean,\n' \
                   '     "more_info_url": string,\n' \
                   '     "statement_text": string,\n' \
                   '     "last_updated": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'positionListForBallotItem',
        'api_slug': 'positionListForBallotItem',
        'api_introduction':
            "A list of all positions (support/oppose/info) for this Ballot Item (Office, Candidate or Measure) "
            "from organizations, friends, and public figures this voter follows. "
            "(Or show the positions the voter is NOT following if show_positions_this_voter_follows is False.)",
        'try_now_link': 'apis_v1:positionListForBallotItemView',
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
