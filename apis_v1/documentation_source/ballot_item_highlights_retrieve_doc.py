# apis_v1/documentation_source/ballot_item_highlights_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def ballot_item_highlights_retrieve_doc_template_values(url_root):
    """
    Show documentation about ballotItemHighlightsRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "highlight_list": list [\n' \
                   '    {\n' \
                   '      "name": string,\n' \
                   '      "we_vote_id": string,\n' \
                   '      "prior": integer, (\'1\' if from a prior election)\n'\
                   '    }\n' \
                   '  ],\n' \
                   '  "never_highlight_on": list [\n' \
                   '     "*.wevote.us",\n' \
                   '     "api.wevoteusa.org",\n' \
                   '     "localhost"\n' \
                   '  ]\n' \
                   '}'

    template_values = {
        'api_name': 'ballotItemHighlightsRetrieve',
        'api_slug': 'ballotItemHighlightsRetrieve',
        'api_introduction':
            "Retrieve all the candidates that might be highlighted on an endorsement guide. ",
        'try_now_link': 'apis_v1:ballotItemHighlightsRetrieveView',
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
