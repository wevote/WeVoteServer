# apis_v1/documentation_source/organization_link_to_issue_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_link_to_issue_sync_out_doc_template_values(url_root):
    """
    Show documentation about organizationLinkToIssueSyncOut
    """
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '[{\n' \
                   '  "issue_we_vote_id": string,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "link_active": boolean,\n' \
                   '  "reason_for_link": string,\n' \
                   '  "link_blocked": boolean,\n' \
                   '  "reason_link_is_blocked": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'organizationLinkToIssueSyncOut',
        'api_slug': 'organizationLinkToIssueSyncOut',
        'api_introduction':
            "This is the summary of the way that public organizations are categorized by issues. "
            "For example, if I want to find all organizations that are related to climate change, "
            "this is the data that tells me this.",
        'try_now_link': 'apis_v1:organizationLinkToIssueSyncOutView',
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
