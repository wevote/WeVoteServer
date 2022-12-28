# apis_v1/documentation_source/candidates_query.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def candidates_query_doc_template_values(url_root):
    """
    Show documentation about candidatesQuery
    """
    required_query_parameter_list = [
        {
            'name':         'electionDay',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Date of the election in this format: YYYY-MM-DD\n'
                            'For all elections in a year, pass in: YYYY\n'
                            'For all elections in a month, pass in: YYYY-MM',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'raceOfficeLevelList',
            'value': 'list of strings',  # boolean, integer, long, string
            'description': 'Limit the candidates returned to: Federal, State, Local',
        },
        {
            'name': 'searchText',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The word or words we want to search for in all candidates.',
        },
        {
            'name': 'state',
            'value': 'string',  # boolean, integer, long, string
            'description': 'Limit the candidates returned to this state.',
        },
        {
            'name': 'useWeVoteFormat',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'Return the candidate variables in snake case variable name format to match '
                           'other We Vote APIs.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'CANDIDATES_RETRIEVED',
            'description':  'Candidates were returned.',
        },
        {
            'code':         'NO_CANDIDATES_RETRIEVED',
            'description':  'There are no candidates stored for this Office.',
        },
    ]

    try_now_link_variables_dict = {
        'electionDay': '2022-11-08',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "candidatesIndexStart": integer,\n' \
                   '  "candidatesReturnedCount": integer,\n' \
                   '  "candidatesTotalCount": integer,\n' \
                   '  "electionDay": string,\n' \
                   '  "kind": string,\n' \
                   '  "state": string,\n' \
                   '  "candidates": list\n' \
                   '   [\n' \
                   '     "id": integer,\n' \
                   '     "status": string,\n' \
                   '     "success": boolean,\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "ballotpedia_candidate_id": integer,\n' \
                   '     "ballotpedia_candidate_summary": string,\n' \
                   '     "ballotpedia_candidate_url": string,\n' \
                   '     "candidate_photo_url_large": string,\n' \
                   '     "candidate_photo_url_medium": string,\n'\
                   '     "candidate_photo_url_tiny": string,\n' \
                   '     "kind_of_ballot_item": string,\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '     "order_on_ballot": integer,\n' \
                   '     "party": string,\n' \
                   '     "we_vote_id": string,\n' \
                   '   ],\n' \
                   '  "election": {\n' \
                   '     "electionDay": string,\n' \
                   '     "id": integer,\n' \
                   '     "name": string,\n' \
                   '     "ballotpediaId": string,\n' \
                   '     "googleCivicId": string,\n' \
                   '     "voteUSAId": string,\n' \
                   '     "weVoteId": string,\n' \
                   '   },\n' \
                   '  "elections": list\n' \
                   '   [\n' \
                   '     "electionDay": string,\n' \
                   '     "id": integer,\n' \
                   '     "name": string,\n' \
                   '     "ballotpediaId": string,\n' \
                   '     "googleCivicId": string,\n' \
                   '     "voteUSAId": string,\n' \
                   '     "weVoteId": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'candidatesQuery',
        'api_slug': 'candidatesQuery',
        'api_introduction':
            "Retrieve all the candidates in a particular election or state. This API maintains compatibility with "
            "the Vote USA API of the same name. For We Vote usage, we offer an option to return variables with "
            "'snake case' formatting as opposed to 'camel case'.",
        'try_now_link': 'apis_v1:candidatesQueryView',
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
