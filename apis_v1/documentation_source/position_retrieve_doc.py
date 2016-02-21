# apis_v1/documentation_source/position_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def position_retrieve_doc_template_values(url_root):
    """
    Show documentation about positionRetrieve
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
    ]
    optional_query_parameter_list = [
        {
            'name':         'position_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Internal database unique identifier.',
        },
        {
            'name':         'position_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'We Vote unique identifier so we can move positions from server-to-server.',
        },
        # We also want to retrieve a position with the following sets of variables:
        # organization_we_vote_id, google_civic_election_id, office_we_vote_id
        # organization_we_vote_id, google_civic_election_id, candidate_we_vote_id
        # organization_we_vote_id, google_civic_election_id, measure_we_vote_id
        # public_figure_we_vote_id, google_civic_election_id, office_we_vote_id
        # public_figure_we_vote_id, google_civic_election_id, candidate_we_vote_id
        # public_figure_we_vote_id, google_civic_election_id, measure_we_vote_id
        # NOTE: With voter we need ability to store private version and public version - maybe distinction between
        #   private and public is voter_we_vote_id vs. public_figure_we_vote_id?
        # voter_we_vote_id, google_civic_election_id, office_we_vote_id
        # voter_we_vote_id, google_civic_election_id, candidate_we_vote_id
        # voter_we_vote_id, google_civic_election_id, measure_we_vote_id
        #
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    potential_status_codes_list = [
        {
            'code':         'RETRIEVE_POSITION_FOUND_WITH_POSITION_ID',
            'description':  'The position was found using the internal id',
        },
        {
            'code':         'RETRIEVE_POSITION_FOUND_WITH_WE_VOTE_ID',
            'description':  'The position was found using the we_vote_id',
        },
        {
            'code':         'POSITION_RETRIEVE_BOTH_IDS_MISSING',
            'description':  'One identifier required. Neither provided.',
        },
        {
            'code':         'POSITION_NOT_FOUND_WITH_ID',
            'description':  'The position was not found with internal id.',
        },
        {
            'code':         'ERROR_<specifics here>',
            'description':  'An internal description of what error prevented the retrieve of the position.',
        },
    ]

    try_now_link_variables_dict = {
        'position_we_vote_id': 'wv01pos7',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "ballot_item_display_name": string (either measure name or candidate name),\n' \
                   '  "position_id": integer (the internal id of the position found),\n' \
                   '  "position_we_vote_id": string (the position identifier that moves server-to-server),\n' \
                   '  "speaker_display_name": string,\n' \
                   '  "speaker_display_name": string,\n' \
                   '  "speaker_image_url_https": string,\n' \
                   '  "is_support": boolean,\n' \
                   '  "is_oppose": boolean,\n' \
                   '  "is_information_only": boolean,\n' \
                   '  "organization_we_vote_id": string (the organization identifier that moves server-to-server),\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "stance": string (support/oppose/info only),\n' \
                   '  "statement_text": string,\n' \
                   '  "statement_html": string,\n' \
                   '  "more_info_url": string,\n' \
                   '  "last_updated": string,\n' \
                   '}'

    template_values = {
        'api_name': 'positionRetrieve',
        'api_slug': 'positionRetrieve',
        'api_introduction':
            "Retrieve the position using position_id (first choice) or we_vote_id. (In the future we will add the"
            "ability to retrieve via a set of variables like "
            "(organization_we_vote_id, google_civic_election_id, candidate_we_vote_id)",
        'try_now_link': 'apis_v1:positionRetrieveView',
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
