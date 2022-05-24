# apis_v1/documentation_source/friend_invitation_information_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_invitation_information_doc_template_values(url_root):
    """
    Show documentation about friendInvitationInformation
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
            'name':         'invitation_secret_key',
            'value':        'string',  # boolean, integer, long, string
            'description':  'We pass in the secret key as an identifier.',
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
            'code':         'MISSING_VOTER_ID_OR_ADDRESS_TYPE',
            'description':  'Cannot proceed. Missing variables voter_id or address_type while trying to save.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "friend_first_name": string,\n' \
                   '  "friend_last_name": string,\n' \
                   '  "friend_image_url_https_large": string,\n' \
                   '  "friend_image_url_https_tiny": string,\n' \
                   '  "friend_issue_we_vote_id_list": list,\n' \
                   '  "friend_we_vote_id": string,\n' \
                   '  "friend_organization_we_vote_id": string,\n' \
                   '  "invitation_found": boolean,\n' \
                   '  "invitation_message": string,\n' \
                   '  "invitation_secret_key": string,\n' \
                   '}'

    template_values = {
        'api_name': 'friendInvitationInformation',
        'api_slug': 'friendInvitationInformation',
        'api_introduction':
            "Accept an invitation to be someone's friend based on a secret key.",
        'try_now_link': 'apis_v1:friendInvitationInformationView',
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
