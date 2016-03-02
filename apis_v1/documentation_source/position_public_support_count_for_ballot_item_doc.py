# apis_v1/documentation_source/position_public_support_count_for_ballot_item_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_public_support_count_for_ballot_item_doc_template_values(url_root):
    """
    Show documentation about positionPublicSupportCountForBallotItem
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'kind_of_ballot_item',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The kind of ballot item we want the support count for. '
                            '(kind_of_ballot_item is either "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier of the ballot item we want the support count for. '
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
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    potential_status_codes_list = [
        {
            'code':         'UNABLE_TO_RETRIEVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING',
            'description':  'Cannot proceed. Neither candidate_id nor measure_id were included.',
        },
        {
            'code':         'SUCCESSFUL_RETRIEVE_OF_POSITIONS',
            'description':  'The number of supports for this ballot item was retrieved.',
        },
        {
            'code':         'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED',
            'description':  'The number of organizations that support this ballot item that voter is NOT following.',
        },
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_id': '5655',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'positionPublicSupportCountForBallotItem',
        'api_slug': 'positionPublicSupportCountForBallotItem',
        'api_introduction':
            "A single number showing the total supporters for this Ballot Item (Candidate or Measure) from "
            "any organizations and public figures. (Not just the ones a voter follows.)",
        'try_now_link': 'apis_v1:positionPublicSupportCountForBallotItemView',
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
