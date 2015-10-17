# apis_v1/documentation_source/voter_count_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_count_doc_template_values(url_root):
    """
    Show documentation about voterCount
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

    api_response = '{\n' \
                   '  "voter_count": integer,\n' \
                   '  "success": boolean,\n' \
                   '}'

    potential_status_codes_list = [
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    template_values = {
        'api_name': 'voterCount',
        'api_slug': 'voterCount',
        'api_introduction':
            "Return the number of voters in the database.",
        'try_now_link': 'apis_v1:voterCountView',
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
