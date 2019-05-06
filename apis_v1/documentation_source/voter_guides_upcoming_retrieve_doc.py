# apis_v1/documentation_source/voter_guides_upcoming_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guides_upcoming_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidesUpcomingRetrieve
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
            'name':         'google_civic_election_id_list[]',
            'value':        'integerlist',  # boolean, integer, long, string
            'description':  'The unique identifier for one or more elections. If not provided, '
                            'use all of the upcoming elections.',
        },
        {
            'name':         'start_retrieve_at_this_number',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'In most elections we have well over the maximum_number_to_retrieve voter guides that '
                            'we want to retrieve with each call. Setting this number lets us retrieve voter guides '
                            'in "pages".',
        },
        {
            'name':         'maximum_number_to_retrieve',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Defaults to 75 voter guides. Enter a value to set your own limit.',
        },
    ]

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

    try_now_link_variables_dict = {
        # 'kind_of_ballot_item': 'CANDIDATE',
        # 'ballot_item_we_vote_id': 'wv01cand2897',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "search_string": string,\n' \
                   '  "start_retrieve_at_this_number": integer\n' \
                   '  "number_retrieved": integer\n' \
                   '  "maximum_number_to_retrieve": integer,\n' \
                   '  "voter_guides": list\n' \
                   '   [{\n' \
                   '     "voter_guide_display_name": string (Name of this org or person),\n' \
                   '     "voter_guide_owner_type": ORGANIZATION, PUBLIC_FIGURE, VOTER),\n' \
                   '     "we_vote_id": string (We Vote ID of the voter guide),\n' \
                   '     "organization_we_vote_id": string (We Vote ID for the org that owns the voter guide),\n' \
                   '     "public_figure_we_vote_id": string (We Vote ID for the person that owns the voter guide),\n' \
                   '     "voter_guide_image_url_large": string ' \
                   '(We Vote ID for the person that owns the voter guide),\n' \
                   '     "voter_guide_image_url_medium": string ' \
                   '(We Vote ID for the person that owns the voter guide),\n' \
                   '     "voter_guide_image_url_tiny": string ' \
                   '(We Vote ID for the person that owns the voter guide),\n' \
                   '     "last_updated": string (time in this format %Y-%m-%d %H:%M),\n' \
                   '     "google_civic_election_id": integer,\n' \
                   '     "twitter_description": string,\n' \
                   '     "twitter_followers_count": integer,\n' \
                   '     "twitter_handle": integer,\n' \
                   '     "owner_voter_id": integer TO BE DEPRECATED,\n' \
                   '     "ballot_item_we_vote_ids_this_org_supports": ' \
                   'The list of ballot_item_we_vote_ids supported by this organization,\n' \
                   '     "ballot_item_we_vote_ids_this_org_info_only": ' \
                   'The list of ballot_item_we_vote_ids this organization has information about,\n' \
                   '     "ballot_item_we_vote_ids_this_org_opposes": ' \
                   'The list of ballot_item_we_vote_ids opposed by this organization,\n' \
                   '     "issue_we_vote_ids_linked": The list of issue_we_vote_ids linked to this organization,\n' \
                   '     "is_support": boolean (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "is_positive_rating": boolean (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "is_support_or_positive_rating": boolean (Exists if looking at one ballot_item),\n' \
                   '     "is_oppose": boolean (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "is_negative_rating": boolean (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "is_oppose_or_negative_rating": boolean (Exists if looking at one ballot_item),\n' \
                   '     "is_information_only": boolean (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "vote_smart_rating": integer (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "vote_smart_time_span": string (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "candidate_name": string (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "speaker_display_name": string (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "statement_text": string (Exists if looking at voter guides for one ballot_item),\n' \
                   '     "more_info_url": string (Exists if looking at voter guides for one ballot_item),\n' \
                   '   },],\n' \
                   '}\n'

    template_values = {
        'api_name': 'voterGuidesUpcomingRetrieve',
        'api_slug': 'voterGuidesUpcomingRetrieve',
        'api_introduction':
            "Retrieve all voter guides for all upcoming elections.",
        'try_now_link': 'apis_v1:voterGuidesUpcomingRetrieveView',
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
