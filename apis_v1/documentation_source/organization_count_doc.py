# apis_v1/documentation_source/organization_count_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_count_doc_template_values(url_root):
    """
    Show documentation about organizationCount
    """
    required_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # string, long, boolean
        #     'description':  '',
        # },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # string, long, boolean
        #     'description':  '',
        # },
    ]

    api_response = '{\n' \
                   '  "organization_count": integer,\n' \
                   '  "success": boolean,\n' \
                   '}'

    potential_status_codes_list = [
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    template_values = {
        'api_name': 'organizationCount',
        'api_slug': 'organizationCount',
        'api_introduction':
            "Return the number of organizations in the database.",
        'try_now_link': 'apis_v1:organizationCountView',
        'try_now_link_variables': '',
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
