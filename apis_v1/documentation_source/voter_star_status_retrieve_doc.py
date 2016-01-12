# apis_v1/documentation_source/voter_star_status_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_star_status_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterStarStatusRetrieve
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
            'description':  'What is the type of ballot item for which we are retrieving the status? '
                            '(kind_of_ballot_item is either "OFFICE", "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier for this ballot_item '
                            '(either ballot_item_id OR ballot_item_we_vote_id required -- not both. '
                            'If it exists, ballot_item_id is used instead of ballot_item_we_vote_id)',
        },
        # {
        #     'name':         'office_id',
        #     'value':        'integer',  # boolean, integer, long, string
        #     'description':  'The office that the voter is starring. '
        #                     '(Either office_id, candidate_id or measure_id must exist)',
        # },
        # {
        #     'name':         'candidate_id',
        #     'value':        'integer',  # boolean, integer, long, string
        #     'description':  'The candidate that the voter is supporting. '
        #                     '(Either office_id, candidate_id or measure_id must exist)',
        # },
        # {
        #     'name':         'measure_id',
        #     'value':        'integer',  # boolean, integer, long, string
        #     'description':  'The measure that the voter is supporting. '
        #                     '(Either office_id, candidate_id or measure_id must exist)',
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
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_id': '5655',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "is_starred": boolean,\n' \
                   '  "office_id": integer,\n' \
                   '  "candidate_id": integer,\n' \
                   '  "measure_id": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterStarStatusRetrieve',
        'api_slug': 'voterStarStatusRetrieve',
        'api_introduction':
            "Is the star next to this office, candidate, or measure starred for this voter?",
        'try_now_link': 'apis_v1:voterStarStatusRetrieveView',
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
