# apis_v1/documentation_source/candidates_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def candidates_retrieve_doc_template_values(url_root):
    """
    Show documentation about candidatesRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'office_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier for this office '
                            '(either office_id OR office_we_vote_id required -- not both. '
                            'If it exists, office_id is used instead of office_we_vote_id)',
        },
        {
            'name':         'office_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this office across all networks '
                            '(either office_id OR office_we_vote_id required -- not both.) NOTE: In the future we '
                            'might support other identifiers used in the industry.',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING',
            'description':  'A valid internal office_id parameter was not included, nor was a office_we_vote_id. '
                            'Cannot proceed.',
        },
        {
            'code':         'CANDIDATES_RETRIEVED',
            'description':  'Candidates were returned for this Office.',
        },
        {
            'code':         'NO_CANDIDATES_RETRIEVED',
            'description':  'There are no candidates stored for this Office.',
        },
    ]

    try_now_link_variables_dict = {
        'office_we_vote_id': 'wv01off922',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "office_id": integer,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "candidate_list": list\n' \
                   '   [\n' \
                   '     "id": integer,\n' \
                   '     "we_vote_id": string,\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "candidate_photo_url": string,\n' \
                   '     "party": string,\n' \
                   '     "order_on_ballot": integer,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'candidatesRetrieve',
        'api_slug': 'candidatesRetrieve',
        'api_introduction':
            "Retrieve all of the candidates competing for a particular office.",
        'try_now_link': 'apis_v1:candidatesRetrieveView',
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
