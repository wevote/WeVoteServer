# apis_v1/documentation_source/position_list_for_ballot_item_from_friends_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_list_for_ballot_item_from_friends_doc_template_values(url_root):
    """
    Show documentation about positionListForBallotItemFromFriends
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
            'name':         'friends_vs_public',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is FRIENDS_AND_PUBLIC. '
                            'Other options include FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC',
        },
        {
            'name':         'private_citizens_only',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Defaults to False. '
                            'If False, only retrieve positions from groups and public figures. '
                            'If True, only return positions from private citizens.',
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
            'description':  'The number of Advocates that oppose this ballot item that voter is NOT following.',
        },
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_id': '5655',
        'stance': 'ANY_STANCE',
        'friends_vs_public': 'FRIENDS_AND_PUBLIC',
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
                   '     "position_we_vote_id": string,\n' \
                   '     "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '     "ballot_item_image_url_https_large": string,\n' \
                   '     "ballot_item_image_url_https_medium": string,\n' \
                   '     "ballot_item_image_url_https_tiny": string,\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "speaker_display_name": string,\n' \
                   '     "speaker_image_url_https_large": string,\n' \
                   '     "speaker_image_url_https_medium": string,\n' \
                   '     "speaker_image_url_https_tiny": string,\n' \
                   '     "speaker_twitter_handle": string,\n' \
                   '     "twitter_followers_count": integer,\n' \
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
                   '     "is_information_only": boolean,\n' \
                   '     "is_public_position": boolean,\n' \
                   '     "more_info_url": string,\n' \
                   '     "statement_text": string,\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'positionListForBallotItemFromFriends',
        'api_slug': 'positionListForBallotItemFromFriends',
        'api_introduction':
            "A list of all positions (support/oppose/info) for this Ballot Item (Office, Candidate or Measure) "
            "from friends of this voter (including both public and friends only). ",
        'try_now_link': 'apis_v1:positionListForBallotItemFromFriendsView',
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
