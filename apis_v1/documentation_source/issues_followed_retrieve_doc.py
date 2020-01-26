# apis_v1/documentation_source/issues_followed_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def issues_followed_retrieve_doc_template_values(url_root):
    """
    Show documentation about issuesFollowedRetrieve
    """
    optional_query_parameter_list = [
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '[{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "issue_list": list\n' \
                   '   [\n' \
                   '     "issue_we_vote_id": string,\n' \
                   '     "issue_name": string,\n' \
                   '     "is_issue_followed": boolean,\n' \
                   '     "is_issue_ignored": boolean,\n' \
                   '   ],\n' \
                   '}]'

    template_values = {
        'api_name': 'issuesFollowedRetrieve',
        'api_slug': 'issuesFollowedRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:issuesFollowedRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
