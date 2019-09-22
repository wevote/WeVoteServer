# apis_v1/documentation_source/organization_index_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_index_doc_template_values(url_root):
    """
    Show documentation about organizationIndex
    """
    required_query_parameter_list = [
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = 'The raw HTML for index.html is returned, using the organizations custom settings'

    template_values = {
        'api_name': 'organizationIndex',
        'api_slug': 'organizationIndex',
        'api_introduction':
            "Return a customized index.html (as text). Add /ORGANIZATION_URL after organizationIndex in the URL.",
        'try_now_link': 'apis_v1:organizationIndexView',
        'try_now_link_additional_path': 'www.domain.org',
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
