# apis_v1/documentation_source/office_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def office_retrieve_doc_template_values(url_root):
    """
    Show documentation about officeRetrieve
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
        {
            'name':         'office_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique internal identifier for this office '
                            '(either office_id OR office_we_vote_id required -- not both. '
                            'If it exists, office_id is used instead of office_we_vote_id)',
        },
        {
            'name':         'office_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this office across all networks '
                            '(either office_id OR office_we_vote_id required -- not both.) NOTE: In the future we '
                            'might support other identifiers used in the industry.',
        },
    ]
    optional_query_parameter_list = [
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
    ]

    try_now_link_variables_dict = {
        'office_we_vote_id': 'wv01off922',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "ballot_item_display_name": string,\n' \
                   '  "ballotpedia_id": string,\n' \
                   '  "ballotpedia_office_id": integer,\n' \
                   '  "ballotpedia_office_name": string,\n' \
                   '  "ballotpedia_office_url": string,\n' \
                   '  "ballotpedia_race_id": integer,\n' \
                   '  "ballotpedia_race_office_level": string,\n' \
                   '  "district_name": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "id": integer,\n' \
                   '  "kind_of_ballot_item": string (CANDIDATE, MEASURE),\n' \
                   '  "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '  "maplight_id": string,\n' \
                   '  "number_voting_for": integer,\n' \
                   '  "number_elected": integer,\n' \
                   '  "ocd_division_id": string,\n' \
                   '  "primary_party": string,\n' \
                   '  "state_code": string,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "wikipedia_id": string,\n' \
                   '}'

    template_values = {
        'api_name': 'officeRetrieve',
        'api_slug': 'officeRetrieve',
        'api_introduction':
            "Retrieve detailed information about one office.",
        'try_now_link': 'apis_v1:officeRetrieveView',
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
