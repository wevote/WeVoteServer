# apis_v1/documentation_source/position_list_for_opinion_maker_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_list_for_opinion_maker_doc_template_values(url_root):
    """
    Show documentation about positionListForOpinionMaker
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
            'name':         'kind_of_opinion_maker',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The kind of ballot item we want positions for. '
                            ' (One of these: \'ORGANIZATION\', \'PUBLIC_FIGURE\')\n'
        },
        {
            'name':         'opinion_maker_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier of the ballot item we want positions for. '
                            '(either opinion_maker_id OR opinion_maker_we_vote_id required -- not both. '
                            'If it exists, opinion_maker_id is used instead of opinion_maker_we_vote_id)',
        },
        {
            'name':         'opinion_maker_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this opinion_maker across all networks '
                            '(either opinion_maker_id OR opinion_maker_we_vote_id required -- not both. '
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
        'kind_of_opinion_maker': 'ORGANIZATION',
        'opinion_maker_id': '145',
        'opinion_maker_we_vote_id': '',
        'stance': 'ANY_STANCE',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '  "kind_of_opinion_maker": string ' \
                   '   (One of these: \'ORGANIZATION\', \'PUBLIC_FIGURE\', \'UNKNOWN\'),\n' \
                   '  "opinion_maker_id": integer,\n' \
                   '  "opinion_maker_we_vote_id": string,\n' \
                   '  "opinion_maker_display_name": string,\n' \
                   '  "opinion_maker_image_url_https": string,\n' \
                   '  "is_following": boolean (Is this voter following this org/public_figure?),\n' \
                   '  "is_ignoring": boolean (Is this voter ignoring this org/public_figure?),\n' \
                   '  "position_list": list\n' \
                   '   [\n' \
                   '     "position_id": integer,\n' \
                   '     "position_we_vote_id": string,\n' \
                   '     "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '     "office_display_name": string (The name of the office if kind_of_ballot_item is CANDIDATE),\n' \
                   '     "ballot_item_image_url_https": string,\n' \
                   '     "kind_of_ballot_item": string, ' \
                   '      (One of these: \'CANDIDATE\', \'MEASURE\', \'OFFICE\', \'UNKNOWN\')\n' \
                   '     "ballot_item_id": integer,\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "is_support": boolean,\n' \
                   '     "is_oppose": boolean,\n' \
                   '     "statement_text": string,\n' \
                   '     "statement_html": string,\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "vote_smart_rating": string,\n' \
                   '     "vote_smart_time_span": string,\n' \
                   '     "last_updated": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'positionListForOpinionMaker',
        'api_slug': 'positionListForOpinionMaker',
        'api_introduction':
            "A list of all positions (support/oppose/info) held by this opinion maker  "
            "(an organization, friend, or public figure). ",
        'try_now_link': 'apis_v1:positionListForOpinionMakerView',
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
