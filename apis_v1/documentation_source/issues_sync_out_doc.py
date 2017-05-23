# apis_v1/documentation_source/issues_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def issues_sync_out_doc_template_values(url_root):
    """
    Show documentation about issuesSyncOut
    """
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "issues_name": string,\n' \
                   '  "issues_description": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'issuesSyncOut',
        'api_slug': 'issuesSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:issuesSyncOutView',
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
