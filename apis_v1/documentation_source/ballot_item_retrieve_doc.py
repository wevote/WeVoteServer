# apis_v1/documentation_source/ballot_item_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def ballot_item_retrieve_doc_template_values(url_root):
    """
    Show documentation about ballotItemRetrieve
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
            'description':  'What is the type of ballot item that we are retrieving? '
                            '(kind_of_ballot_item is either "OFFICE", "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier for this ballot_item '
                            '(either ballot_item_id OR ballot_item_we_vote_id required -- not both. '
                            'If it exists, ballot_item_id is used instead of ballot_item_we_vote_id)',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this ballot_item across all networks '
                            '(either ballot_item_id OR ballot_item_we_vote_id required -- not both.) '
                            'NOTE: In the future we might support other identifiers used in the industry.',
        },
    ]
    optional_query_parameter_list = [
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
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_we_vote_id': 'wv01cand1755',
    }

    # See api_response_notes below. This is a wrapper for candidateRetrieve, measureRetrieve and officeRetrieve.
    api_response = ""

    template_values = {
        'api_name': 'ballotItemRetrieve',
        'api_slug': 'ballotItemRetrieve',
        'api_introduction':
            "Retrieve detailed information about one candidate.",
        'try_now_link': 'apis_v1:ballotItemRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "This API endpoint is a wrapper for <a href='/apis/v1/docs/officeRetrieve/'>officeRetrieve</a>, "
            "<a href='/apis/v1/docs/candidateRetrieve/'>candidateRetrieve</a> and "
            "<a href='/apis/v1/docs/measureRetrieve/'>measureRetrieve</a>, . "
            "See those endpoints for a description of variables returned.",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
