# apis_v1/documentation_source/device_id_generate_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def device_id_generate_doc_template_values(url_root):
    """
    Show documentation about deviceIdGenerate
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
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

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'deviceIdGenerate',
        'api_slug': 'deviceIdGenerate',
        'api_introduction':
            "Generate a transient unique identifier (device_id - stored on client) "
            "which ties the device to a persistent voter_id (mapped together and stored on the server)."
            "Note: This call does not create a voter account -- that must be done in voterCreate.",
        'try_now_link': 'apis_v1:deviceIdGenerateView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
    }
    return template_values
