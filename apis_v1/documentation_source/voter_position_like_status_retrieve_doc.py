# apis_v1/documentation_source/voter_position_like_status_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_position_like_status_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterPositionLikeStatusRetrieve
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
            'code':         'POSITION_LIKE_FOUND_WITH_VOTER_ID_AND_POSITION_ID',
            'description':  '',
        },
        {
            'code':         'UNABLE_TO_RETRIEVE-POSITION_ENTERED_ID_MISSING',
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
                   '  "is_liked": boolean,\n' \
                   '  "position_like_id": integer,\n' \
                   '  "position_entered_id": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterPositionLikeStatusRetrieve',
        'api_slug': 'voterPositionLikeStatusRetrieve',
        'api_introduction':
            "Has this voter 'Liked' this position?",
        'try_now_link': 'apis_v1:voterPositionLikeStatusRetrieveView',
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
