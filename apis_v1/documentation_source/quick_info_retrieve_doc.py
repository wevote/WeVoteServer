# apis_v1/documentation_source/quick_info_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def quick_info_retrieve_doc_template_values(url_root):
    """
    Show documentation about quickInfoRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'kind_of_ballot_item',
            'value':        'string',  # boolean, integer, long, string
            'description':  'What is the type of ballot item that we want quick information for (for use in a popup)? '
                            '(Either "OFFICE", "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we_vote_id for the ballot item we want quick information for. ',
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
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "quick_info_found": boolean,\n' \
                   '  "quick_info_id": integer,\n' \
                   '  "quick_info_we_vote_id": string,\n' \
                   '  "kind_of_ballot_item": string (CANDIDATE, MEASURE),\n' \
                   '  "incoming_ballot_item_we_vote_id": string,\n' \
                   '  "language": string,\n' \
                   '  "info_text": string,\n' \
                   '  "info_html": string,\n' \
                   '  "ballot_item_display_name": string,\n' \
                   '  "more_info_url": string,\n' \
                   '  "more_info_credit_text": string,\n' \
                   '  "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '  "last_editor_we_vote_id": string,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "politician_we_vote_id": string,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "quick_info_master_we_vote_id": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'quickInfoRetrieve',
        'api_slug': 'quickInfoRetrieve',
        'api_introduction':
            "Information necessary to populate a bubble next to a ballot item.",
        'try_now_link': 'apis_v1:quickInfoRetrieveView',
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
