# apis_v1/documentation_source/voter_guides_to_follow_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guides_to_follow_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidesToFollowRetrieve
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
                   '  "voter_guides": list\n' \
                   '   [\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "voter_guide_owner_type": one character (O = Organization, P = Public Figure, V = Voter),\n' \
                   '     "organization_we_vote_id": string (a unique We Vote ID if owner type is "O"),\n' \
                   '     "public_figure_we_vote_id": string (a unique We Vote ID if owner type is "P"),\n' \
                   '     "owner_voter_id": integer (a unique integer id if owner type is "V"),\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M),\n' \
                   '   ],\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '}\n'

    potential_status_codes_list = [
        {
            'code':         'VOTER_GUIDES_TO_FOLLOW_RETRIEVED',
            'description':  'At least one voter guide was returned.',
        },
        {
            'code':         'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'NO_VOTER_GUIDES_FOUND',
            'description':  'No voter guides exist in the database matching the search terms.',
        },
    ]

    template_values = {
        'api_name': 'voterGuidesToFollowRetrieve',
        'api_slug': 'voterGuidesToFollowRetrieve',
        'api_introduction':
            "Look up the election and ballot items that this person is focused on. Return the organizations, "
            "public figures, and voters that have shared voter guides available to follow. Take into consideration "
            "which voter guides the voter has previously ignored. "
            "Do not show voter guides the voter is already following.",
        'try_now_link': 'apis_v1:voterGuidesToFollowRetrieveView',
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
