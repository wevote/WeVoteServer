# apis_v1/documentation_source/retrieve_fast_load_table_statistics.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def retrieve_fast_load_table_statistics_doc_template_values(url_root):
    """
    Show documentation about retrieveFastLoadTableStatisticsDocs
    """
    optional_query_parameter_list = [
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
                   '     "table stuff tbd: string,\n' \
                   '   ],\n' \
                   '}]'

    template_values = {
        'api_name': 'retrieveIssuesToFollow',
        'api_slug': 'retrieveIssuesToFollow',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:retrieveFastLoadTableStatistics',
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
