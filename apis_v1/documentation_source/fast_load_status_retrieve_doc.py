# apis_v1/documentation_source/fast_load_status_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def fast_load_status_retrieve_doc_template_values(url_root):
    """
    Show documentation about fastLoadStatusRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'initialize',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Set true to initialize the record.  When set to false, we are reading the values, '
                            'in which case the optional parameters are moot.  The master server side of the fast_load '
                            'process updates the record in real time, so that the developer\'s server can display '
                            'status',
            'default':      'false',    # default 'checked' for a boolean radio input
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'is_running',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'True if we are running',
            'default': 'true',  # default 'checked' for a boolean radio input
        },
     ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "initialize": boolean,\n' \
                   '  "is_running": boolean,\n' \
                   '  "voter_device_id": voter_device_id,\n' \
                   '  "started_date": started_date,\n' \
                   '  "table_name": table_name,\n' \
                   '  "chunk": chunk,\n' \
                   '  "current_record": current_record,\n' \
                   '  "total_records": total_records,\n' \
                   '}'

    template_values = {
        'api_name': 'fastLoadStatusRetrieve',
        'api_slug': 'fastLoadStatusRetrieve',
        'api_introduction':
            "Developers need copies of certain sql tables on their PCs to run a local API server during development. "
            "This API allows them to monitor the progress of a action that can take a half hour to complete.",
        'try_now_link': 'apis_v1:fastLoadStatusRetrieve',
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
