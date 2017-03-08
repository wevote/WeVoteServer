# apis_v1/documentation_source/polling_locations_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def polling_locations_sync_out_doc_template_values(url_root):
    """
    Show documentation about pollingLocationsSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'state',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the polling_locations retrieved to those from one state. Entered as a state code.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "city": string,\n' \
                   '  "directions_text": string,\n' \
                   '  "line1": string,\n' \
                   '  "line2": string,\n' \
                   '  "location_name": string,\n' \
                   '  "polling_hours_text": string,\n' \
                   '  "state": string,\n' \
                   '  "zip_long": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'pollingLocationsSyncOut',
        'api_slug': 'pollingLocationsSyncOut/?format=json',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:pollingLocationsSyncOutView',
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
