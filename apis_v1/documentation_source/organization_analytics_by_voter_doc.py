# apis_v1/documentation_source/organization_analytics_by_voter_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_analytics_by_voter_doc_template_values(url_root):
    """
    Show documentation about organizationAnalyticsByVoter
    """
    required_query_parameter_list = [
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An organization\'s unique We Vote id.',
        },
        {
            'name':         'organization_api_pass_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An organization\'s unique pass code for retrieving this data. '
                            'Not needed if organization is signed in.',
        },
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Not needed if organization_api_pass_code is used.',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit the results to just this election',
        },
        {
            'name':         'external_voter_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the results to just this voter',
        },
        {
            'name':         'voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the results to just this voter',
        },
    ]

    potential_status_codes_list = [
        # {
        #     'code':         'VALID_VOTER_DEVICE_ID_MISSING',
        #     'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        # },
        # {
        #     'code':         'VALID_VOTER_ID_MISSING',
        #     'description':  'Cannot proceed. A valid voter_id was not found.',
        # },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "election_list": list\n' \
                   '   [\n' \
                   '     "election_id": string,\n' \
                   '     "election_name": string,\n' \
                   '     "election_date": string,\n' \
                   '     "election_state": string,\n' \
                   '   ],\n' \
                   '  "voter_list": list\n' \
                   '   [\n' \
                   '     "external_voter_id": string (Unique ID from organization),\n' \
                   '     "voter_we_vote_id": string (the voter\'s we vote id),\n' \
                   '     "elections_visited: list,\n' \
                   '     [\n' \
                   '       "election_id": string (the election if within we vote),\n' \
                   '       "support_count": integer (COMING SOON),\n' \
                   '       "oppose_count: integer (COMING SOON),\n' \
                   '       "friends_only_support_count": integer (COMING SOON),\n' \
                   '       "friends_only_oppose_count: integer (COMING SOON),\n' \
                   '       "friends_only_comments_count": integer (COMING SOON),\n' \
                   '       "public_support_count": integer (COMING SOON),\n' \
                   '       "public_oppose_count: integer (COMING SOON),\n' \
                   '       "public_comments_count": integer (COMING SOON),\n' \
                   '     ],\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'organizationAnalyticsByVoter',
        'api_slug': 'organizationAnalyticsByVoter',
        'api_introduction':
            "A list of voter-specific analytics about either a) one of your member's, or b) all of your members "
            "based on the variables you send with the request. These analytics come from visits to organization's "
            "custom URL, and not the main WeVote.US site.",
        'try_now_link': 'apis_v1:organizationAnalyticsByVoterView',
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
