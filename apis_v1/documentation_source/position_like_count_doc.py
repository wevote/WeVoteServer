# apis_v1/documentation_source/position_like_count.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_like_count_doc_template_values(url_root):
    """
    Show documentation about positionLikeCount
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
            'name':         'position_entered_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The position that the voter is liking.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'limit_to_voters_network',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'If you want the number of Likes returned to *only* be from people in the voter\'s '
                            'network, pass the value True.',
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
            'code':         'POSITION_LIKE_ALL_COUNT_RETRIEVED',
            'description':  '',
        },
        {
            'code':         'POSITION_LIKE_VOTER_NETWORK_COUNT_RETRIEVED',
            'description':  '',
        },
    ]

    try_now_link_variables_dict = {
        'position_entered_id': '5655',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "position_entered_id": integer,\n' \
                   '  "type_of_count": string, (is this a count based on ALL or VOTER_NETWORK)\n' \
                   '  "number_of_likes": integer, (will be same count as all_likes and voter_network_likes values-' \
                   ' is provided if the front end would rather work with a type_of_count switch)\n' \
                   '  "all_likes": integer,\n' \
                   '  "voter_network_likes": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'positionLikeCount',
        'api_slug': 'positionLikeCount',
        'api_introduction':
            "The total number of Likes that a position has received, either from the perspective of "
            "your network of friends, or the entire network.",
        'try_now_link': 'apis_v1:positionLikeCountView',
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
