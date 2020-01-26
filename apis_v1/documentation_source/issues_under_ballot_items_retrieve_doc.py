# apis_v1/documentation_source/issues_under_ballot_items_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def issues_under_ballot_items_retrieve_doc_template_values(url_root):
    """
    Show documentation about issuesUnderBallotItemsRetrieve
    """
    optional_query_parameter_list = [
        {
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '[{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "issues_under_ballot_items_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_we_vote_id": string,\n' \
                   '     "issue_we_vote_id_list": list\n' \
                   '      [\n' \
                   '         "issue_we_vote_id": string,\n' \
                   '      ],\n' \
                   '   ],\n' \
                   '}]'

    template_values = {
        'api_name': 'issuesUnderBallotItemsRetrieve',
        'api_slug': 'issuesUnderBallotItemsRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:issuesUnderBallotItemsRetrieveView',
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
