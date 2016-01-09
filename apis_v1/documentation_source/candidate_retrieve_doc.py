# apis_v1/documentation_source/candidate_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def candidate_retrieve_doc_template_values(url_root):
    """
    Show documentation about candidateRetrieve
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
        {
            'name':         'candidate_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier for this candidate '
                            '(either candidate_id OR candidate_we_vote_id required -- not both. '
                            'If it exists, candidate_id is used instead of candidate_we_vote_id)',
        },
        {
            'name':         'candidate_we_vote_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for this candidate across all networks '
                            '(either candidate_id OR candidate_we_vote_id required -- not both.) '
                            'NOTE: In the future we might support other identifiers used in the industry.',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_id was not found.',
        },
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'candidate_we_vote_id': 'wv01cand1755',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "kind_of_ballot_item": string,\n' \
                   '  "id": integer,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "ballot_item_display_name": string,\n' \
                   '  "candidate_photo_url": string,\n' \
                   '  "order_on_ballot": integer,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "maplight_id": integer,\n' \
                   '  "contest_office_id": integer,\n' \
                   '  "contest_office_we_vote_id": string,\n' \
                   '  "politician_id": integer,\n' \
                   '  "politician_we_vote_id": string,\n' \
                   '  "party": string,\n' \
                   '  "ocd_division_id": string,\n' \
                   '  "state_code": string,\n' \
                   '  "candidate_url": string,\n' \
                   '  "facebook_url": string,\n' \
                   '  "twitter_url": string,\n' \
                   '  "twitter_handle": string,\n' \
                   '  "google_plus_url": string,\n' \
                   '  "youtube_url": string,\n' \
                   '  "candidate_email": string,\n' \
                   '  "candidate_phone": string,\n' \
                   '}'

    template_values = {
        'api_name': 'candidateRetrieve',
        'api_slug': 'candidateRetrieve',
        'api_introduction':
            "Retrieve detailed information about one candidate.",
        'try_now_link': 'apis_v1:candidateRetrieveView',
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
