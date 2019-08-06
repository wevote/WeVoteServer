# apis_v1/documentation_source/voter_guide_possibility_positions_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guide_possibility_positions_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidePossibilityPositionsRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'voter_guide_possibility_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'This id of the VoterGuidePossibility is required.',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'voter_guide_possibility_position_id',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'If you enter voter_guide_possibility_position_id the query will be limited '
                           'to just this entry.',
        },
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
        {
            'code':         'VOTER_GUIDE_POSSIBILITY_NOT_FOUND',
            'description':  'A voter guide possibility was not found at that URL.',
        },
        {
            'code':         'VOTER_GUIDE_POSSIBILITY_FOUND_WITH_URL',
            'description':  'A voter guide possibility entry was found.',
        },
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'voter_guide_possibility_id':
            '8',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_guide_possibility_id": integer,\n' \
                   '  "possible_position_list": list [\n' \
                   '   {\n' \
                   '     "possibility_position_id": integer,\n' \
                   '     "possibility_position_number": integer,\n' \
                   '     "ballot_item_name": string,\n' \
                   '     "ballot_item_image_url_https_medium": string,\n' \
                   '     "candidate_twitter_handle": string,\n' \
                   '     "candidate_we_vote_id": string,\n' \
                   '     "edit_position_url": string,\n' \
                   '     "google_civic_election_id": string,\n'\
                   '     "measure_we_vote_id": string,\n' \
                   '     "more_info_url_stored": string,\n' \
                   '     "more_info_url": string,\n' \
                   '     "office_we_vote_id": string,\n' \
                   '     "organization_name": string,\n' \
                   '     "organization_twitter_handle": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "political_party": string,\n' \
                   '     "position_should_be_removed": boolean,\n' \
                   '     "position_stance": string,\n' \
                   '     "position_stance_stored": string,\n' \
                   '     "position_we_vote_id": string,\n' \
                   '     "possibility_should_be_deleted": boolean,\n' \
                   '     "possibility_should_be_ignored": boolean,\n' \
                   '     "statement_text": string,\n' \
                   '     "statement_text_stored": string,\n' \
                   '     "state_code": string,\n' \
                   '   }' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterGuidePossibilityPositionsRetrieve',
        'api_slug': 'voterGuidePossibilityPositionsRetrieve',
        'api_introduction':
            "Retrieve all of the possible endorsements scraped from this particular page.",
        'try_now_link': 'apis_v1:voterGuidePossibilityPositionsRetrieveView',
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
