# apis_v1/documentation_source/challenge_invitee_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def challenge_invitee_save_doc_template_values(url_root):
    """
    Show documentation about challengeInviteeSave
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
        {
            'name':         'voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The voter_we_vote_id for the supporter.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The organization_we_vote_id for the supporter.',
        },
        {
            'name':         'invitee_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The title of the challenge.',
        },
        {
            'name':         'invitee_name_changed',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Are we trying to change the challenge\'s title?',
        },
        {
            'name': 'supporter_endorsement',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The title of the challenge.',
        },
        {
            'name': 'supporter_endorsement_changed',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'Are we trying to change the challenge\'s title?',
        },
        {
            'name': 'visible_to_public',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The title of the challenge.',
        },
        {
            'name': 'visible_to_public_changed',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'Are we trying to change the challenge\'s title?',
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
        # 'challenge_we_vote_id': 'wv85camp1',
    }

    api_response = '{\n' \
                   '  "challenge_we_vote_id": string,\n' \
                   '  "challenge_joined": boolean,\n' \
                   '  "date_invite_sent": string,\n' \
                   '  "date_invite_viewed": string,\n' \
                   '  "date_challenge_joined": string,\n' \
                   '  "invitee_id": string,\n' \
                   '  "invitee_name": string,\n' \
                   '  "invitee_url_code": string,\n' \
                   '  "inviter_name": string,\n' \
                   '  "inviter_voter_we_vote_id": string,\n' \
                   '  "invite_sent": boolean,\n' \
                   '  "invite_text_from_inviter": string,\n' \
                   '  "invite_viewed": boolean,\n' \
                   '  "invite_viewed_count": number,\n' \
                   '  "next_invitee_url_code": string,\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '  "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '}'

    template_values = {
        'api_name': 'challengeInviteeSave',
        'api_slug': 'challengeInviteeSave',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:challengeInviteeSaveView',
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
