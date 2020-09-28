# apis_v1/documentation_source/position_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_save_doc_template_values(url_root):
    """
    Show documentation about positionSave
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
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'ID of the election this position is related to.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'position_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this position across all networks. ',
        },
        {
            'name':         'ballot_item_display_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Text we display for the name of this office, candidate or measure. '
                            'If missing, we look it up internally and fill it in.',
        },
        {
            'name':         'office_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the office that the position is commenting on. '
                            '(One and only one of these is required: '
                            'office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)',
        },
        {
            'name':         'candidate_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the candidate that the position is commenting on. '
                            '(One and only one of these is required: '
                            'office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)',
        },
        {
            'name':         'measure_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the measure that the position is commenting on. '
                            '(One and only one of these is required: '
                            'office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The organization that is taking the position.'
                            ' (One and only one of these is required: '
                            'organization_we_vote_id, public_figure_we_vote_id, voter_we_vote_id)',
        },
        {
            'name':         'public_figure_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The public figure (or voter) that is publicly taking the position.'
                            ' (One and only one of these is required: '
                            'organization_we_vote_id, public_figure_we_vote_id, voter_we_vote_id)',
        },
        {
            'name':         'voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The voter that is privately taking the position.'
                            ' (One and only one of these is required: '
                            'organization_we_vote_id, public_figure_we_vote_id, voter_we_vote_id)',
        },
        {
            'name':         'stance',
            'value':        'string',  # boolean, integer, long, string
            'description':  'SUPPORT, OPPOSE, INFORMATION_ONLY (future: STILL_DECIDING, NO_STANCE)',
        },
        {
            'name':         'set_as_public_position',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Should this position be saved so it can be seen by anyone in the public, '
                            'or only for friends',
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
            'name':         'more_info_url',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The URL of the website where this stance can either be verified, '
                            'or pursued in more depth.',
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
            'code':         'POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING',
            'description':  'Cannot proceed. Missing sufficient unique identifiers for either save new or update.',
        },
        {
            'code':         'NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING',
            'description':  'Cannot proceed. This is a new entry and there are not sufficient variables.',
        },
        {
            'code':         'CREATE_POSITION_SUCCESSFUL',
            'description':  'Position created.',
        },
        {
            'code':         'POSITION_SAVED_WITH_POSITION_ID',
            'description':  '',
        },
        {
            'code':         'POSITION_SAVED_WITH_POSITION_WE_VOTE_ID',
            'description':  '',
        },
        {
            'code':         'POSITION_CHANGES_SAVED',
            'description':  '',
        },
        {
            'code':         'NO_POSITION_CHANGES_SAVED_WITH_POSITION_ID',
            'description':  '',
        },
        {
            'code':         'NO_POSITION_CHANGES_SAVED_WITH_POSITION_WE_VOTE_ID',
            'description':  '',
        },
        {
            'code':         'NO_POSITION_CHANGES_SAVED',
            'description':  '',
        },
        {
            'code':         'POSITION_COULD_NOT_BE_FOUND_WITH_POSITION_ID_OR_WE_VOTE_ID',
            'description':  '',
        },
    ]

    try_now_link_variables_dict = {
        'organization_we_vote_id': 'wv85org1',
        'ballot_item_display_name': 'Test Ballot Item Label',
        'candidate_we_vote_id': 'wv01cand1755',
        'stance': 'SUPPORT',
        'set_as_public_position': 'true',
        'statement_text': 'This is what I believe...',
        'google_civic_election_id': '4162',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "new_position_created": boolean,\n' \
                   '  "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '  "speaker_display_name": string,\n' \
                   '  "speaker_image_url_https": string,\n' \
                   '  "speaker_twitter_handle": string,\n' \
                   '  "is_support": boolean,\n' \
                   '  "is_positive_rating": boolean,\n' \
                   '  "is_support_or_positive_rating": boolean,\n' \
                   '  "is_oppose": boolean,\n' \
                   '  "is_negative_rating": boolean,\n' \
                   '  "is_oppose_or_negative_rating": boolean,\n' \
                   '  "is_information_only": boolean,\n' \
                   '  "is_public_position": boolean,\n' \
                   '  "organization_we_vote_id": string (the organization identifier that moves server-to-server),\n' \
                   '  "position_we_vote_id": string (the position identifier that moves server-to-server),\n' \
                   '  "position_ultimate_election_date": integer,\n' \
                   '  "position_year": integer,\n' \
                   '  "public_figure_we_vote_id": string,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "voter_id": integer,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "stance": string (support/oppose/info only),\n' \
                   '  "statement_text": string,\n' \
                   '  "statement_html": string,\n' \
                   '  "more_info_url": string,\n' \
                   '  "last_updated": string,\n' \
                   '}'

    template_values = {
        'api_name': 'positionSave',
        'api_slug': 'positionSave',
        'api_introduction':
            "Save a new position or update an existing position. Note that passing in a blank value does not "
            "delete an existing value. We may want to come up with a variable we pass if we want to clear a value.",
        'try_now_link': 'apis_v1:positionSaveView',
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
