# apis_v1/documentation_source/issues_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def issues_retrieve_doc_template_values(url_root):
    """
    Show documentation about issuesRetrieve
    """
    optional_query_parameter_list = [
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'sort_formula',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Default is MOST_LINKED_ORGANIZATIONS '
                            'A string constant that specifies the criteria which will be used to sort the issues. '
                            'Other options are: ALPHABETICAL_ASCENDING',
        },
        {
            'name':         'voter_issues_only',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'DEPRECATED When this is true, then the resulting issue list contains only issues followed '
                            'by this voter\'s we vote id',
        },
        {
            'name':         'include_voter_follow_status',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'When this is true, then the fields: is_issue_followed and is_issue_ignored reflect the '
                            'real values, else these fields are false by default',
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
                   '  "voter_issues_only": boolean DEPRECATED, \n' \
                   '  "include_voter_follow_status": boolean, \n' \
                   '  "issue_list": list\n' \
                   '   [\n' \
                   '     "issue_we_vote_id": string,\n' \
                   '     "issue_name": string,\n' \
                   '     "issue_description": string,\n' \
                   '     "issue_icon_local_path": string,\n' \
                   '     "issue_image_url": string,\n' \
                   '     "issue_photo_url_large": string,\n' \
                   '     "issue_photo_url_medium": string,\n' \
                   '     "issue_photo_url_tiny": string,\n' \
                   '     "is_issue_followed": boolean,\n' \
                   '     "is_issue_ignored": boolean,\n' \
                   '   ],\n' \
                   '  "issue_score_list": list DEPRECATED\n' \
                   '   [\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "issue_support_score": integer,\n' \
                   '     "issue_oppose_score": integer,\n' \
                   '     "organization_we_vote_id_support_list": list\n' \
                   '      [\n' \
                   '         "organization_we_vote_id": string,\n' \
                   '      ],\n' \
                   '     "organization_name_support_list": list\n' \
                   '      [\n' \
                   '         "Speaker Display Name": string,\n' \
                   '      ],\n' \
                   '     "organization_we_vote_id_oppose_list": list\n' \
                   '      [\n' \
                   '         "organization_we_vote_id": string,\n' \
                   '      ],\n' \
                   '     "organization_name_oppose_list": list\n' \
                   '      [\n' \
                   '         "Speaker Display Name": string,\n' \
                   '      ],\n' \
                   '   ],\n' \
                   '  "issues_under_ballot_items_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "issue_we_vote_id_list": list\n' \
                   '      [\n' \
                   '         "issue_we_vote_id": string,\n' \
                   '      ],\n' \
                   '   ],\n' \
                   '}]'

    template_values = {
        'api_name': 'issuesRetrieve',
        'api_slug': 'issuesRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:issuesRetrieveView',
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
