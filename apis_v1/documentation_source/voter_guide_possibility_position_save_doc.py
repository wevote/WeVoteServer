# apis_v1/documentation_source/voter_guide_possibility_position_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guide_possibility_position_save_doc_template_values(url_root):
    """
    Show documentation about voterGuidePossibilityPositionSave
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
            'name':         'voter_guide_possibility_position_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The voter_guide_possibility_position to be updated, or if set to 0, create new.',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'ballot_item_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The candidate or measure name shown on the web page.',
        },
        {
            'name':         'ballot_item_state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The 2 digit state code of this candidate or measure. When state_code is provided, '
                            'create a candidate if an existing entry can\'t be found.',
        },
        {
            'name':         'position_stance',
            'value':        'string',  # boolean, integer, long, string
            'description':  'SUPPORT, OPPOSE or INFORMATION_ONLY',
        },
        {
            'name':         'statement_text',
            'value':        'string',  # boolean, integer, long, string
            'description':  'A written description of why the endorsement is what it is.',
        },
        {
            'name':         'more_info_url',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The URL a voter can go to for more information about the endorsement.',
        },
        {
            'name':         'possibility_should_be_deleted',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Permanent delete of the VoterGuidePossibilityPosition entry.',
        },
        {
            'name':         'possibility_should_be_ignored',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Soft delete. Stop analyzing this entry.',
        },
        {
            'name':         'candidate_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  '',
        },
        {
            'name':         'measure_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  '',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  '',
        },
        {
            'name':         'position_should_be_removed',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Delete saved position from PositionEntered table.',
        },
        {
            'name':         'google_civic_election_id_list[]',
            'value':        'integerlist',  # boolean, integer, long, string
            'description':  'The election ids we care about.',
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
                   '     "ballot_item_state_code": string,\n' \
                   '     "candidate_twitter_handle": string,\n' \
                   '     "candidate_we_vote_id": string,\n' \
                   '     "edit_position_url": string,\n' \
                   '     "google_civic_election_id": string,\n'\
                   '     "measure_we_vote_id": string,\n' \
                   '     "more_info_url": string,\n' \
                   '     "more_info_url_stored": string,\n' \
                   '     "office_we_vote_id": string,\n' \
                   '     "organization_name": string,\n' \
                   '     "organization_twitter_handle": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "office_name": string,\n' \
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
        'api_name': 'voterGuidePossibilityPositionSave',
        'api_slug': 'voterGuidePossibilityPositionSave',
        'api_introduction':
            "Save one possible endorsement from one particular web page.",
        'try_now_link': 'apis_v1:voterGuidePossibilityPositionSaveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'POST',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
