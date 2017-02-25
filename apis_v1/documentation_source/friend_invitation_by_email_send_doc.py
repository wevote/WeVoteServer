# apis_v1/documentation_source/friend_invitation_by_email_send_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_invitation_by_email_send_doc_template_values(url_root):
    """
    Show documentation about friendInvitationByEmailSend
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
            'name':         'email_address_array',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Array of Email address for friends to send the invitation to.',
        },
        {
            'name':         'first_name_array',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Array of First Name for friends to send the invitation to.',
        },
        {
            'name':         'last_name_array',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Array of Last Name for friends to send the invitation to.',
        },
        {
            'name':         'email_addresses_raw',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Email addresses to send the invitation to.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'invitation_message',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An optional message to send.',
        },
        {
            'name':         'sender_email_address',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The email address to use if an email is not attached to voter account.',
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
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "description_of_send_status": string,\n' \
                   '}'

    template_values = {
        'api_name': 'friendInvitationByEmailSend',
        'api_slug': 'friendInvitationByEmailSend',
        'api_introduction':
            "Invite your friends via email.",
        'try_now_link': 'apis_v1:friendInvitationByEmailSendView',
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
