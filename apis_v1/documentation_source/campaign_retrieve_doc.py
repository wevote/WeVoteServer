# apis_v1/documentation_source/campaign_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def campaign_retrieve_doc_template_values(url_root):
    """
    Show documentation about campaignRetrieve (CDN) & campaignRetrieveAsOwner (No CDN)
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
            'name':         'campaignx_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique id of the campaign. If this value is "", then the API will attempt to do the '
                            'lookup by seo_friendly_path if one is supplied.',
        },
        {
            'name':         'seo_friendly_path',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The SEO friendly path component.',
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
        # 'campaignx_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "campaign_description": string,\n' \
                   '  "campaign_title": string,\n' \
                   '  "campaignx_politician_list_exists": boolean,\n' \
                   '  "campaignx_we_vote_id": string,\n' \
                   '  "final_election_date_as_integer": integer,\n' \
                   '  "final_election_date_in_past": boolean,\n' \
                   '  "in_draft_mode": boolean,\n' \
                   '  "is_blocked_by_we_vote": boolean,\n' \
                   '  "is_blocked_by_we_vote_reason": string,\n' \
                   '  "is_supporters_count_minimum_exceeded": boolean,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "seo_friendly_path": string,\n' \
                   '  "supporters_count": integer,\n' \
                   '  "supporters_count_next_goal": integer,\n' \
                   '  "supporters_count_victory_goal": integer,\n' \
                   '  "visible_on_this_site": boolean,\n' \
                   '  "voter_is_campaignx_owner": boolean,\n' \
                   '  "voter_signed_in_with_email": boolean,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "we_vote_hosted_campaign_photo_large_url": string,\n' \
                   '  "we_vote_hosted_campaign_photo_medium_url": string,\n' \
                   '  "we_vote_hosted_campaign_photo_small_url": string,\n' \
                   '  "campaignx_news_item_list": list\n' \
                   '   [\n' \
                   '   {\n' \
                   '     "campaign_news_subject": string,\n' \
                   '     "campaign_news_text": string,\n' \
                   '     "campaignx_news_item_we_vote_id": string,\n' \
                   '     "campaignx_we_vote_id": string,\n' \
                   '     "date_last_changed": string,\n' \
                   '     "date_posted": string,\n' \
                   '     "in_draft_mode": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "speaker_name": string,\n' \
                   '     "visible_to_public": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '   ],\n' \
                   '  "campaignx_owner_list": list\n' \
                   '   [\n' \
                   '   {\n' \
                   '     "organization_name": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '     "visible_to_public": boolean,\n' \
                   '   },\n' \
                   '   ],\n' \
                   '  "campaignx_politician_list": list\n' \
                   '   [\n' \
                   '   {\n' \
                   '     "campaignx_politician_id": integer,\n' \
                   '     "politician_name": string,\n' \
                   '     "politician_we_vote_id": string,\n' \
                   '     "state_code": string,\n' \
                   '     "we_vote_hosted_profile_image_url_large": string,\n' \
                   '     "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '   ],\n' \
                   '  "campaignx_politician_starter_list": list\n' \
                   '   [\n' \
                   '   {\n' \
                   '     "value": string,\n' \
                   '     "label": string,\n' \
                   '   },\n' \
                   '   ],\n' \
                   '  "latest_campaignx_supporter_endorsement_list": list\n' \
                   '   [\n' \
                   '   {\n' \
                   '     "id": integer,\n' \
                   '     "campaign_supported": boolean,\n' \
                   '     "campaignx_we_vote_id": string,\n' \
                   '     "date_supported": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "supporter_endorsement": string,\n' \
                   '     "supporter_name": string,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '   ],\n' \
                   '  "latest_campaignx_supporter_list": list\n' \
                   '   [\n' \
                   '   {\n' \
                   '     "id": integer,\n' \
                   '     "campaign_supported": boolean,\n' \
                   '     "campaignx_we_vote_id": string,\n' \
                   '     "date_supported": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "supporter_endorsement": string,\n' \
                   '     "supporter_name": string,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '   ],\n' \
                   '  "seo_friendly_path_list": list\n' \
                   '   [],\n' \
                   '  "voter_campaignx_supporter": {\n' \
                   '     "id": integer,\n' \
                   '     "campaign_supported": boolean,\n' \
                   '     "campaignx_we_vote_id": string,\n' \
                   '     "chip_in_total": string,\n' \
                   '     "date_last_changed": string,\n' \
                   '     "date_supported": string,\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "supporter_endorsement": string,\n' \
                   '     "supporter_name": string,\n' \
                   '     "visible_to_public": boolean,\n' \
                   '     "voter_signed_in_with_email": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '}'

    template_values = {
        'api_name': 'campaignRetrieve',
        'api_slug': 'campaignRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:campaignRetrieveView',
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
