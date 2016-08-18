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
            'name':         'kind_of_ballot_item',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The kind of ballot item the voter wants to comment on. '
                            '(kind_of_ballot_item is either "CANDIDATE", "POLITICIAN" or "MEASURE")',
        },
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this ballot_item across all networks.',
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
        {
            'name':         'set_as_public_position',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Should this position be saved so it can be seen by anyone in the public, '
                            'or only for friends',
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
    ]

    try_now_link_variables_dict = {
        'kind_of_ballot_item': 'CANDIDATE',
        'ballot_item_we_vote_id': 'wv01cand1755',
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
                   '  "is_public_position": boolean,\n' \
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
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
