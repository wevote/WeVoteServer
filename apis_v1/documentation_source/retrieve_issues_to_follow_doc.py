# apis_v1/documentation_source/issues_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def retrieve_issues_to_follow_doc_template_values(url_root):
    """
    Show documentation about retrieveIssuesToFollowDocs
    """
    optional_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'sort_formula',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is MOST_LINKED_ORGANIZATIONS '
                            'A string constant that specifies the criteria which will be used to sort the issues. '
                            'Other options are: ALPHABETICAL_ASCENDING',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'sort_formula': 'MOST_LINKED_ORGANIZATIONS',
    }

    api_response = '[{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "issue_list": list\n' \
                   '   [\n' \
                   '     "issue_we_vote_id": string,\n' \
                   '     "issue_name": string,\n' \
                   '     "issue_description": string,\n' \
                   '     "issue_photo_url_large": string,\n' \
                   '     "issue_photo_url_medium": string,\n' \
                   '     "issue_photo_url_tiny": string,\n' \
                   '   ],\n' \
                   '}]'

    template_values = {
        'api_name': 'retrieveIssuesToFollow',
        'api_slug': 'retrieveIssuesToFollow',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:retrieveIssuesToFollowView',
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
