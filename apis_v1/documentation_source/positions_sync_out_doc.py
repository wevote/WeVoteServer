# apis_v1/documentation_source/positions_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def positions_sync_out_doc_template_values(url_root):
    """
    Show documentation about positionsSyncOut
    """
    required_query_parameter_list = [
        {
            'name':         'format',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Currently must be \'json\' to work.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The election for which we want positions.',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
        'google_civic_election_id': '1000000',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'positionsSyncOut',
        'api_slug': 'positionsSyncOut/?format=json',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:positionsSyncOutView',
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
