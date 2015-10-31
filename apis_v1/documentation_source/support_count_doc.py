# apis_v1/documentation_source/support_count_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def support_count_doc_template_values(url_root):
    """
    Show documentation about supportCount
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
            'name':         'candidate_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The candidate we want the support count for. '
                            '(Either measure_id or candidate_id must exist)',
        },
        {
            'name':         'measure_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The measure we want the support count for. (Either measure_id or candidate_id must exist. '
                            'We ignore measure_id if candidate_id exists.)',
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
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '}'

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

    template_values = {
        'api_name': 'supportCount',
        'api_slug': 'supportCount',
        'api_introduction':
            "How many of the organizations that the voter follows, plus the friends of the voter, "
            "support this candidate or measure?",
        'try_now_link': 'apis_v1:supportCountView',
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
