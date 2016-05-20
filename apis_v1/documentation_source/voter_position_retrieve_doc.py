# apis_v1/documentation_source/voter_position_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_position_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterPositionRetrieve
    """
    required_query_parameter_list = [
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
        {
            'name':         'kind_of_ballot_item',
            'value':        'string',  # boolean, integer, long, string
            'description':  'What is the type of ballot item for which we need to know the voter\'s stance? '
                            '(kind_of_ballot_item is either "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique we_vote identifier for this ballot_item '
                            '(either ballot_item_id OR ballot_item_we_vote_id required -- not both. '
                            'If it exists, ballot_item_id is used instead of ballot_item_we_vote_id)',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_we_vote_id': 'wv01cand1755',
    }

    # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating or is_oppose_or_negative_rating
    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '  "position_id": integer (the internal id of the position found),\n' \
                   '  "position_we_vote_id": string (the position identifier that moves server-to-server),\n' \
                   '  "is_support": boolean,\n' \
                   '  "is_oppose": boolean,\n' \
                   '  "is_information_only": boolean,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "kind_of_ballot_item": string (OFFICE, CANDIDATE, MEASURE),\n' \
                   '  "ballot_item_we_vote_id": string,\n' \
                   '  "stance": string (SUPPORT, OPPOSE, INFO_ONLY, or NO_STANCE),\n' \
                   '  "statement_text": string,\n' \
                   '  "statement_html": string,\n' \
                   '  "more_info_url": string,\n' \
                   '  "last_updated": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterPositionRetrieve',
        'api_slug': 'voterPositionRetrieve',
        'api_introduction':
            "Retrieve the position (support/oppose) on this office, candidate or measure for the voter.",
        'try_now_link': 'apis_v1:voterPositionRetrieveView',
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
