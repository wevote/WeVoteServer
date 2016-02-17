# apis_v1/documentation_source/voter_position_comment_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_position_comment_save_doc_template_values(url_root):
    """
    Show documentation about voterPositionCommentSave
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
            'name':         'office_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the office the position about. '
                            '(One and only one of these is required: '
                            'office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)',
        },
        {
            'name':         'candidate_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the candidate the position about. '
                            '(One and only one of these is required: '
                            'office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)',
        },
        {
            'name':         'measure_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the measure the position about. '
                            '(One and only one of these is required: '
                            'office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)',
        },
        {
            'name':         'statement_text',
            'value':        'string',  # boolean, integer, long, string
            'description':  'A text description of this stance.',
        },
        {
            'name':         'statement_html',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An HTML description of this stance.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'ID of the election this position is related to.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'position_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Internal database unique identifier for a position.',
        },
        {
            'name':         'position_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'We Vote unique identifier for this position.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            'description':  'Cannot proceed. A valid voter_id was not found.',
        },
        # {
        #     'code':         'POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING',
        #     'description':  'Cannot proceed. Missing sufficient unique identifiers for either save new or update.',
        # },
        # {
        #     'code':         'NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING',
        #     'description':  'Cannot proceed. This is a new entry and there are not sufficient variables.',
        # },
        # {
        #     'code':         'CREATE_POSITION_SUCCESSFUL',
        #     'description':  'Position created.',
        # },
        # {
        #     'code':         'POSITION_SAVED_WITH_POSITION_ID',
        #     'description':  '',
        # },
        # {
        #     'code':         'POSITION_SAVED_WITH_POSITION_WE_VOTE_ID',
        #     'description':  '',
        # },
        # {
        #     'code':         'POSITION_CHANGES_SAVED',
        #     'description':  '',
        # },
        # {
        #     'code':         'NO_POSITION_CHANGES_SAVED_WITH_POSITION_ID',
        #     'description':  '',
        # },
        # {
        #     'code':         'NO_POSITION_CHANGES_SAVED_WITH_POSITION_WE_VOTE_ID',
        #     'description':  '',
        # },
        # {
        #     'code':         'NO_POSITION_CHANGES_SAVED',
        #     'description':  '',
        # },
        # {
        #     'code':         'POSITION_COULD_NOT_BE_FOUND_WITH_POSITION_ID_OR_WE_VOTE_ID',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'candidate_we_vote_id': 'wv01cand1755',
        'statement_text': 'This is what I believe...',
        'google_civic_election_id': '4162',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "position_id": integer (the internal id of the position found),\n' \
                   '  "position_we_vote_id": string (the position identifier that moves server-to-server),\n' \
                   '  "new_position_created": boolean,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "statement_text": string,\n' \
                   '  "statement_html": string,\n' \
                   '  "last_updated": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterPositionCommentSave',
        'api_slug': 'voterPositionCommentSave',
        'api_introduction':
            "Save a voter's comment about an office, candidate or measure, to be shared with friends. ",
        'try_now_link': 'apis_v1:voterPositionCommentSaveView',
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
