# apis_v1/documentation_source/voter_supporting_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_supporting_save_doc_template_values(url_root):
    """
    Show documentation about voterSupportingSave
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
            'name':         'candidate_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The candidate that the voter is supporting. '
                            '(Either measure_id or candidate_id must exist)',
        },
        {
            'name':         'measure_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The measure that the voter is supporting. (Either measure_id or candidate_id must exist)',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (did the save happen?),\n' \
                   '}'

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
            'code':         'UNABLE_TO_SAVE-CANDIDATE_ID_AND_MEASURE_ID_MISSING',
            'description':  'Cannot proceed. Neither candidate_id nor measure_id were included.',
        },
        {
            'code':         'SUPPORTING_CANDIDATE STANCE_UPDATED',
            'description':  'Success. Existing entry updated.',
        },
        {
            'code':         'SUPPORTING_CANDIDATE NEW_STANCE_SAVED',
            'description':  'Success. New entry created.',
        },
        {
            'code':         'SUPPORTING_CANDIDATE STANCE_COULD_NOT_BE_UPDATED',
            'description':  'Cannot proceed. Existing entry could not be updated.',
        },
        {
            'code':         'SUPPORTING_CANDIDATE NEW_STANCE_COULD_NOT_BE_SAVED',
            'description':  'Cannot proceed. New entry could not be created.',
        },
        {
            'code':         'SUPPORTING_MEASURE STANCE_UPDATED',
            'description':  'Success. Existing entry updated.',
        },
        {
            'code':         'SUPPORTING_MEASURE NEW_STANCE_SAVED',
            'description':  'Success. New entry created.',
        },
        {
            'code':         'SUPPORTING_MEASURE STANCE_COULD_NOT_BE_UPDATED',
            'description':  'Cannot proceed. Existing entry could not be updated.',
        },
        {
            'code':         'SUPPORTING_MEASURE NEW_STANCE_COULD_NOT_BE_SAVED',
            'description':  'Cannot proceed. New entry could not be created.',
        },
    ]

    template_values = {
        'api_name': 'voterSupportingSave',
        'api_slug': 'voterSupportingSave',
        'api_introduction':
            "Save or create support stance for the current voter for either a measure or candidate.",
        'try_now_link': 'apis_v1:voterSupportingSaveView',
        'try_now_link_variables': '?candidate_id=5655&measure_id=0',
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
