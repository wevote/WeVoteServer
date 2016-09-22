# apis_v1/documentation_source/friend_invite_response_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_invite_response_doc_template_values(url_root):
    """
    Show documentation about friendInviteResponse
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
            'name':         'kind_of_invite_response',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is ACCEPT_INVITATION. '
                            'Other options include IGNORE_INVITATION.',
        },
        {
            'name':         'voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the voter who sent the invitation.',
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
        'kind_of_invite_response':     'ACCEPT_INVITATION',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "kind_of_invite_response": string, \n' \
                   '  "friend_voter": dict\n' \
                   '   {\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "voter_display_name": string,\n' \
                   '     "voter_photo_url": string,\n' \
                   '     "voter_twitter_handle": string,\n' \
                   '     "voter_twitter_description": string,\n' \
                   '     "voter_twitter_followers_count": number,\n' \
                   '     "voter_state_code": string,\n' \
                   '   },\n' \
                   '}'

    template_values = {
        'api_name': 'friendInviteResponse',
        'api_slug': 'friendInviteResponse',
        'api_introduction':
            "Respond to friend request. ",
        'try_now_link': 'apis_v1:friendInviteResponseView',
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
