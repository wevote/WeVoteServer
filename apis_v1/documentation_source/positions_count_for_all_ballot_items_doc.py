# apis_v1/documentation_source/positions_count_for_all_ballot_items_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def positions_count_for_all_ballot_items_doc_template_values(url_root):
    """
    Show documentation about positionsCountForAllBallotItems
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
            'description':  'The unique identifier for a particular election. If not provided, return all positions'
                            ' for this voter.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "google_civic_election_id: integer,\n' \
                   '  "ballot_item_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "support_count": integer,\n' \
                   '     "oppose_count": integer,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'positionsCountForAllBallotItems',
        'api_slug': 'positionsCountForAllBallotItems',
        'api_introduction':
            "Retrieve all positions held by this voter in one list.",
        'try_now_link': 'apis_v1:positionsCountForAllBallotItemsView',
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
