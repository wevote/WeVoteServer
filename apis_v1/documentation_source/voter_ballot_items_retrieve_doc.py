# apis_v1/documentation_source/voter_ballot_items_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_ballot_items_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterBallotItemsRetrieveView
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string (from cookie)',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_ballot_items": list\n' \
                   '   [\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "voter_guide_owner_type": one character (O = Organization, P = Public Figure, V = Voter),\n' \
                   '     "organization_we_vote_id": string (a unique We Vote ID if owner type is "O"),\n' \
                   '     "public_figure_we_vote_id": string (a unique We Vote ID if owner type is "P"),\n' \
                   '     "owner_voter_id": integer (a unique integer id if owner type is "V"),\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M),\n' \
                   '   ],\n' \
                   '}'

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    template_values = {
        'api_name': 'voterBallotItemsRetrieveView',
        'api_slug': 'voterBallotItemsRetrieveView',
        'api_introduction':
            "Request a skeleton of ballot data for this voter location, so that the web_app has all of the ids "
            "it needs to make more requests for data about each ballot item.",
        'try_now_link': 'apis_v1:voterBallotItemsRetrieveView',
        'try_now_link_variables': '',
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
