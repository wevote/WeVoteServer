# apis_v1/documentation_source/voter_ballot_list_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_ballot_list_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterBallotListRetrieve
    """
    required_query_parameter_list = [
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name': 'api_key',
            'value': 'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description': 'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
        {
            'code': 'VALID_VOTER_DEVICE_ID_MISSING',
            'description': 'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code': 'VALID_VOTER_ID_MISSING',
            'description': 'A valid voter_id was not found from voter_device_id. Cannot proceed.',
        },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_ballot_list": list\n' \
                   '   [\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "election_description_text": string,\n' \
                   '     "election_date": string,\n' \
                   '     "original_text_for_map_search": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterBallotListRetrieve',
        'api_slug': 'voterBallotListRetrieve',
        'api_introduction':
            "Retrieve a list of ballots per voter_id",
        'try_now_link': 'apis_v1:voterBallotListRetrieveView',
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
