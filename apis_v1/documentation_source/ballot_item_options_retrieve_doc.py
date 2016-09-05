# apis_v1/documentation_source/ballot_item_options_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def ballot_item_options_retrieve_doc_template_values(url_root):
    """
    Show documentation about ballotItemOptionsRetrieve
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
    ]
    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular election. If NOT provided, we instead use the '
                            'google_civic_election_id for the person who is signed in.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'CANDIDATES_RETRIEVED OFFICES_RETRIEVED MEASURES_RETRIEVED',
            'description':  'Ballot items were found.',
        },
        {
            'code':         'NO_CANDIDATES_RETRIEVED NO_OFFICES_RETRIEVED NO_MEASURES_RETRIEVED',
            'description':  'Candidates, offices or measures were not able to be retrieved.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "ballot_item_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_display_name": string,\n' \
                   '     "measure_we_vote_id": integer,\n' \
                   '     "office_we_vote_id": string,\n' \
                   '     "candidate_we_vote_id": string,\n' \
                   '   ],\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'ballotItemOptionsRetrieve',
        'api_slug': 'ballotItemOptionsRetrieve',
        'api_introduction':
            "Returns ALL of the offices, measures and candidates for a) the currently signed in voter, or "
            "b) the election specified by the google_civic_election_id, so we can help "
            "volunteers or staff find offices, candidates or measures when they are building out organizational "
            "voter guides. This information is not organized in a "
            "hierarchy, but is instead provided in a simple list to help with auto-complete and browser-side "
            "quick search features.",
        'try_now_link': 'apis_v1:ballotItemOptionsRetrieveView',
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
