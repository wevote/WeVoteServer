# apis_v1/documentation_source/friend_lists_all_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def friend_lists_all_doc_template_values(url_root):
    """
    Show documentation about friendListsAll
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

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "count": integer,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "state_code": string,\n' \
                   '  "current_friends": list\n' \
                   '  "invitations_processed": list\n' \
                   '  "invitations_sent_to_me": list\n' \
                   '  "invitations_sent_by_me": list\n' \
                   '  "invitations_waiting_for_verify": list\n' \
                   '  "suggested_friends": list\n' \
                   '}'

    template_values = {
        'api_name': 'friendListsAll',
        'api_slug': 'friendListsAll',
        'api_introduction':
            "Request information about a voter's friends, including invitations to become a friend, "
            "a list of current friends, and friends you share in common with another voter. "
            "This API differs from friendList in that it "
            "returns six different lists at once.",
        'try_now_link': 'apis_v1:friendListsAllView',
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
