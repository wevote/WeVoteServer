# apis_v1/documentation_source/friend_invitation_by_facebook_send_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_invitation_by_facebook_send_doc_template_values(url_root):
    """
    Show documentation about friendInvitationByFacebookSend
    """
    required_query_parameter_list = [
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name': 'api_key',
            'value': 'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description': 'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name': 'recipients_facebook_id_array',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'Array of recipients facebook id to send the invitation to.',
        },
        {
            'name': 'recipients_facebook_name_array',
            'value': 'string',  # boolean, integer, long, string
            'description': 'Array of facebook name for friends to send the invitation to.',
        },
        {
            'name': 'facebook_request_id',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'facebook request id for the invitation.',
        },
    ]

    optional_query_parameter_list = []

    potential_status_codes_list = [
        {
            'code': 'VALID_VOTER_DEVICE_ID_MISSING',
            'description': 'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code': 'VALID_VOTER_ID_MISSING',
            'description': 'Cannot proceed. A valid voter_id was not found.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "all_friends_facebook_link_created_results": string,\n' \
                   '}'

    template_values = {
        'api_name': 'friendInvitationByFacebookSend',
        'api_slug': 'friendInvitationByFacebookSend',
        'api_introduction':
            "Invite your friends via facebook.",
        'try_now_link': 'apis_v1:friendInvitationByFacebookSendView',
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
