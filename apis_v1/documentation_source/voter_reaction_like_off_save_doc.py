# apis_v1/documentation_source/voter_reaction_like_off_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_reaction_like_off_save_doc_template_values(url_root):
    """
    Show documentation about voterReactionLikeOffSave
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
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'reaction_like_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The id of the reaction entry.',
        },
        {
            'name':         'liked_item_we_vote_id',
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
            'description':  'Cannot proceed. Missing voter_id while trying to save.',
        },
        {
            'code':         'DELETED_BY_VOTER_ID_AND_LIKED_ITEM_WE_VOTE_ID',
            'description':  '',
        },
        {
            'code':         'DELETED_BY_REACTION_LIKE_ID',
            'description':  '',
        },
        {
            'code':         'UNABLE_TO_DELETE_REACTION_LIKE-INSUFFICIENT_VARIABLES',
            'description':  '',
        },
    ]

    try_now_link_variables_dict = {
        'liked_item_we_vote_id': '5655',
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (did the save happen?),\n' \
                   '}'

    template_values = {
        'api_name': 'voterReactionLikeOffSave',
        'api_slug': 'voterReactionLikeOffSave',
        'api_introduction':
            "Remove a Like that the voter set on a position.",
        'try_now_link': 'apis_v1:voterReactionLikeOffSaveView',
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
