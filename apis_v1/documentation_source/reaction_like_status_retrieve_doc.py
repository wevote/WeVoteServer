# apis_v1/documentation_source/reaction_like_status_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def reaction_like_status_retrieve_doc_template_values(url_root):
    """
    Show documentation about reactionLikeStatusRetrieve
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
            'name':         'liked_item_we_vote_id_list[]',
            'value':        'stringlist',  # boolean, integer, long, string
            'description':  'Get all of the likes for all liked_item_we_vote_id\'s in this list.',
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
            'code':         'REACTION_LIKE_FOUND_WITH_VOTER_ID_AND_POSITION_ID',
            'description':  '',
        },
        {
            'code':         'UNABLE_TO_RETRIEVE-LIKED_ITEM_WE_VOTE_ID_MISSING',
            'description':  '',
        },
    ]

    try_now_link_variables_dict = {
        'liked_item_we_vote_id': '5655',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "reaction_like_list": list\n' \
                   '   [\n' \
                   '     "liked_item_we_vote_id": string,\n' \
                   '     "voter_display_name": string,\n' \
                   '     "voter_id": number,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'reactionLikeStatusRetrieve',
        'api_slug': 'reactionLikeStatusRetrieve',
        'api_introduction':
            "The likes from voters associated with various items requested.",
        'try_now_link': 'apis_v1:reactionLikeStatusRetrieveView',
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
