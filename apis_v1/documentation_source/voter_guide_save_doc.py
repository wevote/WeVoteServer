# apis_v1/documentation_source/voter_guide_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guide_save_doc_template_values(url_root):
    """
    Show documentation about voterGuideSave
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
            'name':         'voter_guide_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this voter guide. If not passed in, create a new '
                            'voter guide for this voter\'s linked_organization_we_vote_id for this election.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  '',
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
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_guide_display_name": string (Name of this org or person),\n' \
                   '  "voter_guide_owner_type": ORGANIZATION, PUBLIC_FIGURE, VOTER),\n' \
                   '  "we_vote_id": string (We Vote ID of the voter guide),\n' \
                   '  "organization_we_vote_id": string (We Vote ID for the org that owns the voter guide),\n' \
                   '  "public_figure_we_vote_id": string (We Vote ID for the person that owns the voter guide),\n' \
                   '  "voter_guide_image_url_large": string ' \
                   '(We Vote ID for the person that owns the voter guide),\n' \
                   '  "voter_guide_image_url_medium": string ' \
                   '(We Vote ID for the person that owns the voter guide),\n' \
                   '  "voter_guide_image_url_tiny": string ' \
                   '(We Vote ID for the person that owns the voter guide),\n' \
                   '  "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "twitter_description": string,\n' \
                   '  "twitter_followers_count": integer,\n' \
                   '  "twitter_handle": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterGuideSave',
        'api_slug': 'voterGuideSave',
        'api_introduction':
            "Save a new voter guide.",
        'try_now_link': 'apis_v1:voterGuideSaveView',
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
