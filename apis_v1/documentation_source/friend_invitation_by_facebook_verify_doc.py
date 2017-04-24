# apis_v1/documentation_source/friend_invitation_by_facebook_verify_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_invitation_by_facebook_verify_doc_template_values(url_root):
    """
    Show documentation about friendInvitationByFacebookVerify
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
            'name': 'facebook_request_id',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'facebook request id for the invitation.',
        },
        {
            'name': 'recipient_facebook_id',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'Recipient facebook id to verify the invitation.',
        },
        {
            'name': 'sender_facebook_id',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'Sender facebook id to verify the invitation.',
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
                   '  "invitation_found": boolean,\n' \
                   '}'

    template_values = {
        'api_name': 'friendInvitationByFacebookVerify',
        'api_slug': 'friendInvitationByFacebookVerify',
        'api_introduction':
            "Accept an invitation from facebook to be someone's friend",
        'try_now_link': 'apis_v1:friendInvitationByFacebookVerifyView',
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
