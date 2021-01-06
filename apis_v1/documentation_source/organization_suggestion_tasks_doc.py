# apis_v1/documentation_source/organization_suggestion_tasks_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_suggestion_tasks_doc_template_values(url_root):
    """
    Show documentation about organizationSuggestionTask
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
            'name':         'kind_of_suggestion_task',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW. '
                            'Other options include UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW, '
                            'UPDATE_SUGGESTIONS_FROM_WHAT_FRIENDS_FOLLOW_ON_TWITTER, '
                            'UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS, '
                            'UPDATE_SUGGESTIONS_FROM_WHAT_FRIEND_FOLLOWS_ON_TWITTER or UPDATE_SUGGESTIONS_ALL',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'kind_of_follow_task',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is FOLLOW_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW. '
                            'Other options include FOLLOW_SUGGESTIONS_FROM_FRIENDS, '
                            'or FOLLOW_SUGGESTIONS_FROM_FRIENDS_ON_TWITTER, ',
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
                   '}'

    template_values = {
        'api_name': 'organizationSuggestionTasks',
        'api_slug': 'organizationSuggestionTasks',
        'api_introduction':
            "This will provide list of suggested Advocates to follow. "
            "These suggestions are generated from twitter ids i follow, or organization of my friends follow",
        'try_now_link': 'apis_v1:organizationSuggestionTasksView',
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
