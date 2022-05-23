# apis_v1/documentation_source/friend_list_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_list_doc_template_values(url_root):
    """
    Show documentation about friendList
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
            'name':         'kind_of_list',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is CURRENT_FRIENDS. '
                            'Other options include FRIEND_INVITATIONS_PROCESSED, '
                            'FRIEND_INVITATIONS_SENT_TO_ME, FRIEND_INVITATIONS_SENT_BY_ME, '
                            'FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION, FRIENDS_IN_COMMON, '
                            'IGNORED_FRIEND_INVITATIONS, or SUGGESTED_FRIEND_LIST.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Only show friends who live in this state.'
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
        'kind_of_list':     'CURRENT_FRIENDS',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "state_code": string,\n' \
                   '  "kind_of_list": string, \n' \
                   '  "friend_list": list\n' \
                   '   [\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "voter_display_name": string,\n' \
                   '     "voter_photo_url_large": string,\n' \
                   '     "voter_photo_url_medium": string,\n' \
                   '     "voter_photo_url_tiny": string,\n' \
                   '     "voter_email_address": string,\n' \
                   '     "voter_twitter_handle": string,\n' \
                   '     "voter_twitter_description": string,\n' \
                   '     "voter_twitter_followers_count": number,\n' \
                   '     "linked_organization_we_vote_id": string,\n' \
                   '     "state_code_for_display": string,\n' \
                   '     "invitation_status": string,\n' \
                   '     "invitation_sent_to": string,\n' \
                   '     "positions_taken": number,\n' \
                   '     "mutual_friends": number,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'friendList',
        'api_slug': 'friendList',
        'api_introduction':
            "Request information about a voter's friends, including invitations to become a friend, "
            "a list of current friends, and friends you share in common with another voter.",
        'try_now_link': 'apis_v1:friendListView',
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
