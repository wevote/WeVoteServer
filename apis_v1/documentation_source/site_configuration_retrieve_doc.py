# apis_v1/documentation_source/site_configuration_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def site_configuration_retrieve_doc_template_values(url_root):
    """
    Show documentation about siteConfigurationRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'hostname',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The URL that the voter is visiting.',
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
        {
            'code':         'ORGANIZATION_FOUND_WITH_ID',
            'description':  'The organization was found using the internal id',
        },
    ]
    try_now_link_variables_dict = {
        'hostname': 'localhost',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "chosen_hide_we_vote_logo": boolean,\n' \
                   '  "chosen_prevent_sharing_opinions": boolean,\n' \
                   '  "chosen_logo_url_https": string,\n' \
                   '  "features_provided_bitmap": integer,\n' \
                   '  "hostname": string,\n' \
                   '  "organization_we_vote_id": string (the organization identifier that moves server-to-server),\n' \
                   '}'

    template_values = {
        'api_name': 'siteConfigurationRetrieve',
        'api_slug': 'siteConfigurationRetrieve',
        'api_introduction':
            "Retrieve the private label settings as configured by this organization.",
        'try_now_link': 'apis_v1:siteConfigurationRetrieveView',
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
