# apis_v1/documentation_source/challenge_list_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def challenge_list_retrieve_doc_template_values(url_root):
    """
    Show documentation about challengeListRetrieve (No CDN)
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
        # 'challenge_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "challenge_list": list\n' \
                   '   [\n' \
                   '     "challenge_description": string,\n' \
                   '     "challenge_invite_text_default": string,\n' \
                   '     "challenge_title": string,\n' \
                   '     "challenge_we_vote_id": string,\n' \
                   '     "final_election_date_as_integer": integer,\n' \
                   '     "final_election_date_in_past": boolean,\n' \
                   '     "in_draft_mode": boolean,\n' \
                   '     "is_blocked_by_we_vote": boolean,\n' \
                   '     "is_blocked_by_we_vote_reason": string,\n' \
                   '     "is_supporters_count_minimum_exceeded": boolean,\n' \
                   '     "opposers_count": integer,\n' \
                   '     "seo_friendly_path": string,\n' \
                   '     "supporters_count": integer,\n' \
                   '     "supporters_count_next_goal": integer,\n' \
                   '     "supporters_count_victory_goal": integer,\n' \
                   '     "visible_on_this_site": boolean,\n' \
                   '     "voter_can_send_updates_to_challenge": boolean,\n' \
                   '     "voter_is_challenge_owner": boolean,\n' \
                   '     "voter_signed_in_with_email": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "we_vote_hosted_challenge_photo_large_url": string,\n' \
                   '     "we_vote_hosted_challenge_photo_medium_url": string,\n' \
                   '     "we_vote_hosted_challenge_photo_small_url": string,\n' \
                   '     "challenge_owner_list": list\n' \
                   '     [\n' \
                   '       "feature_this_profile_image": boolean,\n' \
                   '       "organization_name": string,\n' \
                   '       "organization_we_vote_id": string,\n' \
                   '       "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '       "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '       "visible_to_public": boolean,\n' \
                   '     ],\n' \
                   '     "challenge_politician_list": list\n' \
                   '     [\n' \
                   '       "challenge_politician_id": integer,\n' \
                   '       "politician_name": string,\n' \
                   '       "politician_we_vote_id": string,\n' \
                   '       "state_code": string,\n' \
                   '       "we_vote_hosted_profile_image_url_large": string,\n' \
                   '       "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '       "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '     ],\n' \
                   '     "challenge_politician_list_exists": boolean,\n' \
                   '     "challenge_politician_starter_list": list\n' \
                   '     [\n' \
                   '       "value": string,\n' \
                   '       "label": string,\n' \
                   '     ],\n' \
                   '     "seo_friendly_path_list": list\n' \
                   '     [],\n' \
                   '   ],\n' \
                   '  "challenge_list_found": boolean,\n' \
                   '  "promoted_challenge_list_returned": boolean,\n' \
                   '  "promoted_challenge_we_vote_ids": list [],\n' \
                   '  "voter_challenge_participant": {\n' \
                   '     "id": integer,\n' \
                   '     "challenge_we_vote_id": string,\n' \
                   '     "date_joined": string,\n' \
                   '     "date_last_changed": string,\n' \
                   '     "invitees_count": number,\n' \
                   '     "invitees_who_joined": number,\n' \
                   '     "invitees_who_viewed": number,\n' \
                   '     "invitees_who_viewed_plus": number,\n' \
                   '     "invite_text_for_friends": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "participant_name": string,\n' \
                   '     "points": number,\n' \
                   '     "rank": number,\n' \
                   '     "visible_to_public": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '  "voter_can_send_updates_challenge_we_vote_ids": list [],\n' \
                   '  "voter_can_vote_for_politicians_list_returned": boolean,\n' \
                   '  "voter_can_vote_for_politician_we_vote_ids": list [],\n' \
                   '  "voter_owned_challenge_list_returned": boolean,\n' \
                   '  "voter_owned_challenge_we_vote_ids": list [],\n' \
                   '  "voter_started_challenge_list_returned": boolean,\n' \
                   '  "voter_started_challenge_we_vote_ids": list [],\n' \
                   '  "challenge_we_vote_ids_where_voter_is_participant_returned": boolean,\n' \
                   '  "challenge_we_vote_ids_where_voter_is_participant": list [],\n' \
                   '}'

    template_values = {
        'api_name': 'challengeListRetrieve',
        'api_slug': 'challengeListRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:challengeListRetrieveView',
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
