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
                   '  "voter_id": integer,\n' \
                   '  "ballot_item_list": list\n' \
                   '   [\n' \
                   '     "ballot_item_label": string,\n' \
                   '     "voter_id": integer,\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "google_ballot_placement": integer,\n' \
                   '     "local_ballot_order": integer,\n' \
                   '     "contest_office_id": integer,\n' \
                   '     "contest_office_we_vote_id": string,\n' \
                   '     "contest_measure_id": integer,\n' \
                   '     "contest_measure_we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'A valid voter_id was not found from voter_device_id. Cannot proceed.',
        },
        {
            'code':         'MISSING_GOOGLE_CIVIC_ELECTION_ID',
            'description':  'A valid google_civic_election_id not found. Cannot proceed.',
        },
        {
            'code':         'VOTER_BALLOT_ITEMS_RETRIEVED',
            'description':  'Ballot items were found.',
        },
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
