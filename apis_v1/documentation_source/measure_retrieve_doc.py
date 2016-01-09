# apis_v1/documentation_source/measure_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def measure_retrieve_doc_template_values(url_root):
    """
    Show documentation about measureRetrieve
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
            'name':         'measure_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier for this measure '
                            '(either measure_id OR measure_we_vote_id required -- not both. '
                            'If it exists, measure_id is used instead of measure_we_vote_id)',
        },
        {
            'name':         'measure_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this measure across all networks '
                            '(either measure_id OR measure_we_vote_id required -- not both. '
                            'If it exists, measure_id is used instead of measure_we_vote_id)',
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
        'measure_we_vote_id': 'wv01meas1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "kind_of_ballot_item": string,\n' \
                   '  "id": integer,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "ballot_item_display_name": string,\n' \
                   '  "measure_subtitle": string,\n' \
                   '  "maplight_id": integer,\n' \
                   '  "measure_text": string,\n' \
                   '  "measure_url": string,\n' \
                   '  "ocd_division_id": string,\n' \
                   '  "district_name": string,\n' \
                   '  "state_code": string,\n' \
                   '}'

    template_values = {
        'api_name': 'measureRetrieve',
        'api_slug': 'measureRetrieve',
        'api_introduction':
            "Retrieve detailed information about one measure.",
        'try_now_link': 'apis_v1:measureRetrieveView',
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
