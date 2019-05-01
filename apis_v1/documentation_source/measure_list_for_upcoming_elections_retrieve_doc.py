# apis_v1/documentation_source/measure_list_for_upcoming_elections_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def doc_template_values(url_root):
    """
    Show documentation about measureListForUpcomingElectionsRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'google_civic_election_id_list',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'List of election ids we care about.',
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
            'description':  'Candidates were returned for these elections.',
        },
        {
            'code':         'NO_CANDIDATES_RETRIEVED',
            'description':  'There are no candidates stored for these elections.',
        },
    ]

    try_now_link_variables_dict = {
        'google_civic_election_id_list': '6000',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "google_civic_election_id_list": list\n' \
                   '  [\n' \
                   '  integer,\n' \
                   '  ],\n' \
                   '  "measure_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "ballot_item_website": string,\n' \
                   '     "candidate_contact_form_url": string,\n' \
                   '     "candidate_we_vote_id": string,\n' \
                   '     "alternate_names": list,\n' \
                   '     [\n' \
                   '     "String here",\n' \
                   '     ],\n' \
                   '     "google_civic_election_id": string,\n' \
                   '     "office_we_vote_id": string,\n' \
                   '     "measure_we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'measureListForUpcomingElectionsRetrieve',
        'api_slug': 'measureListForUpcomingElectionsRetrieve',
        'api_introduction':
            "Retrieve all of the measures in upcoming elections. This shares the same response package format with "
            "candidateListForUpcomingElectionsRetrieve.",
        'try_now_link': 'apis_v1:measureListForUpcomingElectionsRetrieveView',
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
