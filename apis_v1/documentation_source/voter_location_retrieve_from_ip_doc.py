# apis_v1/documentation_source/voter_location_retrieve_from_ip.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_location_retrieve_from_ip_doc_template_values(url_root):
    """
    Show documentation about voterLocationRetrieveFromIP
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'ip_address',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The IP Address of the browser',
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
        #     'code':         'VALID_VOTER_DEVICE_ID_MISSING',
        #     'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        # },
        # {
        #     'code':         'VALID_VOTER_ID_MISSING',
        #     'description':  'Cannot proceed. A valid voter_id was not found.',
        # },
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_location_found": boolean,\n' \
                   '  "voter_location": string (88 characters long),\n' \
                   '  "ip_address": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterLocationRetrieveFromIP',
        'api_slug': 'voterLocationRetrieveFromIP',
        'api_introduction':
            """
            Retrieve a printable string with the location of the voter, based on the browser's IP address.
            Ex: 'Oakland, CA 94602' <br>
            Requisite: set up <a href=https://github.com/wevote/WeVoteServer/blob/master/README_API_INSTALL.md#set-up-geoip> GeoIP </a>
            """,
        'try_now_link': 'apis_v1:voterLocationRetrieveFromIPView',
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
