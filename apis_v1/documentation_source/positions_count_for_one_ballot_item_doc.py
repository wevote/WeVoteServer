# apis_v1/documentation_source/positions_count_for_one_ballot_item_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def positions_count_for_one_ballot_item_doc_template_values(url_root):
    """
    Show documentation about positionsCountForOneBallotItem
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
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for one ballot item.',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "ballot_item_we_vote_id: string,\n' \
                   '  "ballot_item_list": list ' \
                   '(we return a list so this API can be consumed like positionsCountForAllBallotItems)\n' \
                   '   [\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "support_count": integer,\n' \
                   '     "oppose_count": integer,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'positionsCountForOneBallotItem',
        'api_slug': 'positionsCountForOneBallotItem',
        'api_introduction':
            "Retrieve all positions held by this voter in one list.",
        'try_now_link': 'apis_v1:positionsCountForOneBallotItemView',
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
