# apis_v1/documentation_source/voter_guides_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guides_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidesRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Retrieve all voter guides for this organization.',
        },
        {
            'name':         'voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Retrieve all voter guides for this voter.',
        },
        {
            'name':         'maximum_number_to_retrieve',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Defaults to 20 voter guides. Enter a value to set your own limit.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'organization_we_vote_id': 'wv02org1061',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_guides": list\n' \
                   '   [\n' \
                   '     "election_day_text": string (YYYY-MM-DD),\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "organization_we_vote_id": string (We Vote ID for the org that owns the voter guide),\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M:%S),\n' \
                   '     "pledge_goal": integer,\n' \
                   '     "pledge_count": integer,\n' \
                   '     "state_code": string,\n' \
                   '     "twitter_description": string,\n' \
                   '     "twitter_followers_count": integer,\n' \
                   '     "twitter_handle": integer,\n' \
                   '     "voter_guide_display_name": string (Name of this org or person),\n' \
                   '     "voter_guide_image_url_large": string, \n' \
                   '     "voter_guide_image_url_medium": string, \n' \
                   '     "voter_guide_image_url_tiny": string, \n' \
                   '     "voter_guide_owner_type": ORGANIZATION, PUBLIC_FIGURE, VOTER),\n' \
                   '     "we_vote_id": string (We Vote ID of the voter guide),\n' \
                   '   ],\n' \
                   '  "maximum_number_to_retrieve": integer,\n' \
                   '}\n'

    template_values = {
        'api_name': 'voterGuidesRetrieve',
        'api_slug': 'voterGuidesRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:voterGuidesRetrieveView',
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
