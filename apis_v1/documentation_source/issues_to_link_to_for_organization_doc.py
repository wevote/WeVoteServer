# apis_v1/documentation_source/issues_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def issues_to_link_to_for_organization_doc_template_values(url_root):
    """
    Show documentation about issuesToLinkToForOrganization
    """
    optional_query_parameter_list = [
        {
            'name': 'organization_we_vote_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The Endorser\'s we vote id',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '[{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "organization_we_vote_id": string,\n' \
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
        'api_name': 'issuesToLinkToForOrganization',
        'api_slug': 'issuesToLinkToForOrganization',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:issuesToLinkToForOrganizationView',
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
