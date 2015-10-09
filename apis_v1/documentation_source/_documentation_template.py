# apis_v1/documentation_source/_documentation_template.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# This is a template (starting point) for creating documentation for individual APIs


def PUT_NAME_HERE_doc_template_values(url_root):
    """
    Show documentation about voterRetrieve
    """
    required_query_parameter_list = [
        # {
        #     'name':         'voter_device_id',
        #     'value':        'string (from cookie)',  # boolean, integer, long, string
        #     'description':  'An 88 character unique identifier linked to a voter record on the server',
        # },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    template_values = {
        'api_name': 'voterRetrieve - TODO This documentation still in progress',
        'api_slug': 'voterRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:voterRetrieveView',
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
