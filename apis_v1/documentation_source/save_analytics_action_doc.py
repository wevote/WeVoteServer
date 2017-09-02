# apis_v1/documentation_source/save_analytics_action_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def save_analytics_action_doc_template_values(url_root):
    """
    Show documentation about saveAnalyticsAction
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
            'name':         'action_constant',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'There is a constant for each kind of action:\n'
                            'ACTION_VOTER_GUIDE_VISIT = 1\n'
                            'ACTION_VOTER_GUIDE_ENTRY = 2\n'
                            'ACTION_ORGANIZATION_FOLLOW = 3\n'
                            'ACTION_ORGANIZATION_AUTO_FOLLOW = 4\n'
                            'ACTION_ISSUE_FOLLOW = 5\n'
                            'ACTION_BALLOT_VISIT = 6\n'
                            'ACTION_POSITION_TAKEN = 7\n'
                            'ACTION_VOTER_TWITTER_AUTH = 8\n'
                            'ACTION_VOTER_FACEBOOK_AUTH = 9\n'
                            'ACTION_WELCOME_ENTRY = 10\n'
                            'ACTION_FRIEND_ENTRY = 11',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this organization across all networks ',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular election.',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we_vote_id for the ballot item we are storing analytics for. ',
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
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "action_constant": integer,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "organization_id": integer,\n' \
                   '  "ballot_item_we_vote_id": string,\n' \
                   '  "date_as_integer": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'saveAnalyticsAction',
        'api_slug': 'saveAnalyticsAction',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:saveAnalyticsActionView',
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
