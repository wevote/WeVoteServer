# apis_v1/documentation_source/voter_list_analytics_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_list_analytics_doc_template_values(url_root):
    """
    Show documentation about voterListAnalytics
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]

    optional_query_parameter_list = [
        {
            'name':         'show_signed_in_voters',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Only show voters who have signed in. (Default is False)',
        },
        {
            'name':         'show_we_vote_id_only',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Return only a list of We Vote Ids (Default is False)',
        },
        {
            'name':         'voter_count_requested',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The number to return. (Default is 10,000 voters)',
        },
        {
            'name':         'voter_index_start',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Return the list starting with this voter number.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        # 'voter_device_id': '',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "documentation_url": "https://api.wevoteusa.org/apis/v1/docs/voterListAnalytics/",\n' \
                   '  "show_signed_in_voters": boolean (Was there request for only signed in voters?),\n' \
                   '  "voter_count_total": integer (the total number of voters to be returned by search parameters),\n' \
                   '  "voter_count_requested": integer (ex/ Send me 10,000),\n' \
                   '  "voter_count_returned": integer (ex/ 5234),\n' \
                   '  "voter_index_start": integer (ex/ returning voter 100),\n' \
                   '  "voter_index_end": integer (ex/ ...through voter 200),\n' \
                   '  "voter_list": list\n' \
                   '   [{\n' \
                   '     "we_vote_id": string,\n' \
                   '   }],\n' \
                   '}'

    template_values = {
        'api_name': 'voterListAnalytics',
        'api_slug': 'voterListAnalytics',
        'api_introduction':
            "For accounts that have the right permissions, return a list of voters who have used We Vote.",
        'try_now_link': 'apis_v1:voterListAnalyticsView',
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
