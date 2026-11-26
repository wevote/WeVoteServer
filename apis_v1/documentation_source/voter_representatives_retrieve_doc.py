# apis_v1/documentation_source/voter_representatives_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_representatives_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterRepresentativesRetrieve
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
            'name':         'ballot_returned_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for the ballot at one address.',
        },
        {
            'name':         'ballot_location_shortcut',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for one ballot, identified by a string url.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'A valid voter_id was not found from voter_device_id. Cannot proceed.',
        },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "is_from_substituted_address": boolean,\n' \
                   '  "office_held_list_found": boolean,\n' \
                   '  "offices_held_for_location_found": boolean,\n' \
                   '  "offices_held_for_location_id": integer,\n' \
                   '  "state_code": string,\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "substituted_address_nearby": string,\n' \
                   '  "substituted_address_city": string,\n' \
                   '  "substituted_address_state": string,\n' \
                   '  "substituted_address_zip": string,\n' \
                   '  "text_for_map_search": string (if an error response),\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_device_id_not_valid": boolean,\n' \
                   '  "office_held_list": list\n' \
                   '   [\n' \
                   '     "district_id": integer,\n' \
                   '     "district_name": string,\n' \
                   '     "ocd_division_id": string,\n' \
                   '     "office_explanation_we_vote_id": string,\n' \
                   '     "office_held_description": string,\n' \
                   '     "office_held_facebook_url": string,\n' \
                   '     "office_held_id": integer,\n' \
                   '     "office_held_name": string,\n' \
                   '     "office_held_twitter_handle": string,\n' \
                   '     "office_held_url": string,\n' \
                   '     "office_held_we_vote_id": string,\n' \
                   '     "primary_party": string,\n' \
                   '     "race_office_level": string,\n' \
                   '     "state_code": string,\n' \
                   '     "vote_usa_office_id": string,\n' \
                   '     "representative_list": list\n' \
                   '      [\n' \
                   '        "ballot_item_display_name": string,\n' \
                   '        "facebook_url": string,\n' \
                   '        "id": integer,\n' \
                   '        "instagram_followers_count": string,\n' \
                   '        "instagram_handle": string,\n' \
                   '        "is_battleground_race_xxxx": boolean,\n' \
                   '        "is_claimed_profile": boolean,\n' \
                   '        "last_updated": string,\n' \
                   '        "linked_campaignx_we_vote_id": string,\n' \
                   '        "linkedin_url": string,\n' \
                   '        "ocd_division_id": string,\n' \
                   '        "office_held_district_name": string,\n' \
                   '        "office_held_id": integer,\n' \
                   '        "office_held_name": string,\n' \
                   '        "office_held_we_vote_id": string,\n' \
                   '        "political_party": string,\n' \
                   '        "politician_id": string,\n' \
                   '        "politician_we_vote_id": string,\n' \
                   '        "profile_image_background_color": string,\n' \
                   '        "representative_contact_form_url": string,\n' \
                   '        "representative_email": string,\n' \
                   '        "representative_email2": string,\n' \
                   '        "representative_email3": string,\n' \
                   '        "representative_name": string,\n' \
                   '        "representative_phone": string,\n' \
                   '        "representative_phone2": string,\n' \
                   '        "representative_phone3": string,\n' \
                   '        "representative_photo_url_large": string,\n' \
                   '        "representative_photo_url_medium": string,\n' \
                   '        "representative_photo_url_tiny": string,\n' \
                   '        "representative_url": string,\n' \
                   '        "seo_friendly_path": string,\n' \
                   '        "state_code": string,\n' \
                   '        "supporters_count": integer,\n' \
                   '        "twitter_description": string,\n' \
                   '        "twitter_handle": string,\n' \
                   '        "twitter_followers_count": integer,\n' \
                   '        "twitter_url": string,\n' \
                   '        "vote_usa_office_id": string,\n' \
                   '        "vote_usa_politician_id": string,\n' \
                   '        "we_vote_id": string,\n' \
                   '        "wikipedia_url": string,\n' \
                   '        "youtube_url": string,\n' \
                   '      ],\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterRepresentativesRetrieve',
        'api_slug': 'voterRepresentativesRetrieve',
        'api_introduction':
            "Request elected officials (OfficeHeld & Representative) for this voter location.",
        'try_now_link': 'apis_v1:voterRepresentativesRetrieveView',
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
