# apis_v1/documentation_source/representatives_query.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def representatives_query_doc_template_values(url_root):
    """
    Show documentation about representativesQuery
    """
    required_query_parameter_list = [
        {
            'name':         'year',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Year in this format: YYYY',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'race_office_level',
            'value': 'list of strings',  # boolean, integer, long, string
            'description': 'Limit the representatives returned to: Federal, State, Local',
        },
        {
            'name': 'search_text',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The word or words we want to search for in all representatives.',
        },
        {
            'name': 'state',
            'value': 'string',  # boolean, integer, long, string
            'description': 'Limit the representatives returned to this state.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'CANDIDATES_RETRIEVED',
            'description':  'Candidates were returned.',
        },
        {
            'code':         'NO_CANDIDATES_RETRIEVED',
            'description':  'There are no representatives stored for this Office.',
        },
    ]

    try_now_link_variables_dict = {
        'year': '2023',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "index_start": integer,\n' \
                   '  "returned_count": integer,\n' \
                   '  "total_count": integer,\n' \
                   '  "kind": string,\n' \
                   '  "state": string,\n' \
                   '  "office_held_list": {\n' \
                   '     "id": integer,\n' \
                   '     "name": string,\n' \
                   '     "we_vote_id": string,\n' \
                   '   },\n' \
                   '  "representatives": list\n' \
                   '   [\n' \
                   '     "id": integer,\n' \
                   '     "status": string,\n' \
                   '     "success": boolean,\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "kind_of_ballot_item": string,\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '     "office_held_we_vote_id": string,\n' \
                   '     "party": string,\n' \
                   '     "politician_we_vote_id": string,\n' \
                   '     "representative_photo_url_large": string,\n' \
                   '     "representative_photo_url_medium": string,\n'\
                   '     "representative_photo_url_tiny": string,\n' \
                   '     "we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'representativesQuery',
        'api_slug': 'representativesQuery',
        'api_introduction':
            "Retrieve all the representatives in a particular election or state.",
        'try_now_link': 'apis_v1:representativesQueryView',
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
