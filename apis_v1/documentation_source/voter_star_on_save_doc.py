# apis_v1/documentation_source/voter_star_on_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_star_on_save_doc_template_values(url_root):
    """
    Show documentation about voterStarOnSave
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier (from cookie - not URL variable) linked to '
                            'a voter record on the server',
        },
        {
            'name':         'office_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The office that the voter is starring. '
                            '(Either office_id, candidate_id or measure_id must exist)',
        },
        {
            'name':         'candidate_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The candidate that the voter is supporting. '
                            '(Either office_id, candidate_id or measure_id must exist)',
        },
        {
            'name':         'measure_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The measure that the voter is supporting. '
                            '(Either office_id, candidate_id or measure_id must exist)',
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
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'Cannot proceed. Missing voter_id while trying to save.',
        },
        {
            'code':         'STAR_ON_OFFICE CREATE/UPDATE ITEM_STARRED',
            'description':  '',
        },
        {
            'code':         'STAR_ON_CANDIDATE CREATE/UPDATE ITEM_STARRED',
            'description':  '',
        },
        {
            'code':         'STAR_ON_MEASURE CREATE/UPDATE ITEM_STARRED',
            'description':  '',
        },
    ]

    try_now_link_variables_dict = {
        'candidate_id': '5655',
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (did the save happen?),\n' \
                   '}'

    template_values = {
        'api_name': 'voterStarOnSave',
        'api_slug': 'voterStarOnSave',
        'api_introduction':
            "Save or create private 'star on' state for the current voter for a measure, an office or candidate.",
        'try_now_link': 'apis_v1:voterStarOnSaveView',
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
