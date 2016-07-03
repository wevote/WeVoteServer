# apis_v1/documentation_source/search_all_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def search_all_doc_template_values(url_root):
    """
    Show documentation about searchAll
    """
    required_query_parameter_list = [
        {
            'name':         'text_from_search_field',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The string of text for which we want to search',
        },
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_id was not found.',
        },
    ]

    try_now_link_variables_dict = {
        'text_from_search_field': 'kamala',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "text_from_search_field": string,\n' \
                   '  "search_results_found": boolean,\n' \
                   '  "search_results": list\n' \
                   '   [{\n' \
                   '     "result_title": string,\n' \
                   '     "result_image": string,\n' \
                   '     "result_subtitle": string,\n' \
                   '     "result_summary": string,\n' \
                   '     "result_score": integer,\n' \
                   '     "link_internal": string,\n' \
                   '     "kind_of_owner": string,\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "state_code": string,\n' \
                   '     "twitter_handle": string,\n' \
                   '     "we_vote_id": string,\n' \
                   '     "local_id": integer,\n' \
                   '   },]\n' \
                   '}'

    template_values = {
        'api_name': 'searchAll',
        'api_slug': 'searchAll',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:searchAllView',
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
