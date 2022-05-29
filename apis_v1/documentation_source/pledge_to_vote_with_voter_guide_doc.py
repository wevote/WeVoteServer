# apis_v1/documentation_source/pledge_to_vote_with_voter_guide_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def pledge_to_vote_with_voter_guide_doc_template_values(url_root):
    """
    Show documentation about pledgeToVoteWithVoterGuide
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'voter_guide_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Pledge to support or oppose all the things listed on this voter guide',
        },
        {
            'name':         'delete_pledge',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Remove this pledge',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'A valid voter_id was not found from voter_device_id. Cannot proceed.',
        },
    ]

    try_now_link_variables_dict = {
        # 'voter_guide_we_vote_id': '1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "voter_guide_we_vote_id": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "pledge_statistics_found": boolean,\n' \
                   '  "pledge_goal": integer,\n' \
                   '  "pledge_count": integer,\n' \
                   '  "voter_has_pledged": boolean,\n' \
                   '  "delete_pledge": boolean,\n' \
                   '}'

    template_values = {
        'api_name': 'pledgeToVoteWithVoterGuide',
        'api_slug': 'pledgeToVoteWithVoterGuide',
        'api_introduction':
            "Call this to save that the voter is pledging to vote as the voter guide recommends.",
        'try_now_link': 'apis_v1:pledgeToVoteWithVoterGuideView',
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
