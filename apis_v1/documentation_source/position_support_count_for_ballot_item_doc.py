# apis_v1/documentation_source/position_support_count_for_ballot_item_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_support_count_for_ballot_item_doc_template_values(url_root):
    """
    Show documentation about positionSupportCountForBallotItem
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
        # {
        #     'name':         'candidate_id',
        #     'value':        'integer',  # boolean, integer, long, string
        #     'description':  'The candidate we want the support count for. '
        #                     '(Either measure_id or candidate_id must exist)',
        # },
        # {
        #     'name':         'measure_id',
        #     'value':        'integer',  # boolean, integer, long, string
        #     'description':  'The measure we want the support count for. '
        #                     ' (Either measure_id or candidate_id must exist. '
        #                     'We ignore measure_id if candidate_id exists.)',
        # },
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
        'api_name': 'positionSupportCountForBallotItem',
        'api_slug': 'positionSupportCountForBallotItem',
        'api_introduction':
            "A single number showing the total supporters for this Ballot Item (Candidate or Measure) from "
            "organizations, friends, and public figures this voter follows.",
        'try_now_link': 'apis_v1:positionSupportCountForBallotItemView',
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
