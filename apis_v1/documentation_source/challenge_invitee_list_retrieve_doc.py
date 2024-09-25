# apis_v1/documentation_source/challenge_invitee_list_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def challenge_invitee_list_retrieve_doc_template_values(url_root):
    """
    Show documentation about challengeInviteeListRetrieve
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
            'name':         'challenge_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we_vote_id for the challenge.',
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
        # 'challenge_we_vote_id': 'wv85camp1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "challenge_we_vote_id": string,\n' \
                   '  "date_last_changed": string,\n' \
                   '  "invitee_list: list \n' \
                   '  [{\n' \
                   '    "challenge_we_vote_id": string,\n' \
                   '    "date_joined": string,\n' \
                   '    "date_last_changed": string,\n' \
                   '    "friends_invited": number,\n' \
                   '    "friends_who_joined": number,\n' \
                   '    "friends_who_viewed": number,\n' \
                   '    "friends_who_viewed_plus": number,\n' \
                   '    "organization_we_vote_id": string,\n' \
                   '    "invitee_name": string,\n' \
                   '    "points": number,\n' \
                   '    "rank": number,\n' \
                   '    "visible_to_public": boolean,\n' \
                   '    "voter_we_vote_id": string,\n' \
                   '    "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '    "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '  },]\n' \
                   '}'

    template_values = {
        'api_name': 'challengeInviteeListRetrieve',
        'api_slug': 'challengeInviteeListRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:challengeInviteeListRetrieveView',
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
