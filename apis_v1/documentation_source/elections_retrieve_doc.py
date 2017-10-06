# apis_v1/documentation_source/elections_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def elections_retrieve_doc_template_values(url_root):
    """
    Show documentation about electionsRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "election_list": list,\n' \
                   '  [{\n' \
                   '    "google_civic_election_id": integer,\n' \
                   '    "election_name": string,\n' \
                   '    "election_day_text": string,\n' \
                   '    "election_is_upcoming": boolean,\n' \
                   '    "get_election_state": string,\n' \
                   '    "state_code": string,\n' \
                   '    "ocd_division_id": string,\n' \
                   '    "ballot_returned_count": integer,\n' \
                   '    "ballot_location_list": list\n' \
                   '    [\n' \
                   '      "ballot_location_display_name": string,\n' \
                   '      "ballot_location_shortcut": string,\n' \
                   '      "ballot_returned_we_vote_id": string,\n' \
                   '      "ballot_location_order": integer,\n' \
                   '    ],\n' \
                   '  }]\n'\
                   '}'

    template_values = {
        'api_name': 'electionsRetrieve',
        'api_slug': 'electionsRetrieve',
        'api_introduction':
            "Return a list of all elections, and include ballot location options so a voter can jump to "
            "sample ballots.",
        'try_now_link': 'apis_v1:electionsRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
