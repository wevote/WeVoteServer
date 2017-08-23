# apis_v1/documentation_source/voter_follow_all_organizations_followed_by_organization_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_follow_all_organizations_followed_by_organization_doc_template_values(url_root):
    """
    Show documentation about voterFollowAllOrganizationsFollowedByOrganization
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we vote id for the Organization',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'maximum_number_to_follow',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'Defaults to 40 voter guides. Enter a value to set your own limit.',
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
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "organizations_follow_all_results": list\n' \
                   '   [\n' \
                   '     "status": string,\n' \
                   '     "success": boolean,\n' \
                   '     "voter_device_id": string (88 characters long),\n' \
                   '     "organization_id": integer,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "voter_linked_organization_we_vote_id": string,\n' \
                   '     "organization_follow_based_on_issue": boolean,\n' \
                   '   ],\n' \
                   '  "organization_we_vote_id": integer,\n' \
                   '  "maximum_number_to_follow": integer,\n' \
                   '}\n'

    template_values = {
        'api_name': 'voterFollowAllOrganizationsFollowedByOrganization',
        'api_slug': 'voterFollowAllOrganizationsFollowedByOrganization',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:voterFollowAllOrganizationsFollowedByOrganizationView',
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
