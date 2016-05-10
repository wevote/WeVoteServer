# apis_v1/documentation_source/organizations_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organizations_sync_out_doc_template_values(url_root):
    """
    Show documentation about organizationsSyncOut
    """
    required_query_parameter_list = [
        {
            'name':         'format',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Currently must be \'json\' to work.',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    potential_status_codes_list = [
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'organizationsSyncOut',
        'api_slug': 'organizationsSyncOut/?format=json',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:organizationsSyncOutView',
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
