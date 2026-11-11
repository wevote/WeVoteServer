# apis_v1/documentation_source/representatives_query.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from wevote_functions.functions_date import DATE_FORMAT_YMD_HMS


def representatives_query_doc_template_values(url_root):
    """
    Show documentation about representativesQuery
    """
    required_query_parameter_list = [
        {
            'name':         'year',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Year in this format: YYYY',
        },
    ]
    optional_query_parameter_list = [
        {
            'name': 'race_office_level',
            'value': 'list of strings',  # boolean, integer, long, string
            'description': 'Limit the representatives returned to: Federal, State, Local',
        },
        {
            'name': 'search_text',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The word or words we want to search for in all representatives.',
        },
        {
            'name': 'state',
            'value': 'string',  # boolean, integer, long, string
            'description': 'Limit the representatives returned to this state.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'REPRESENTATIVES_RETRIEVED',
            'description':  'Representatives were returned.',
        },
        {
            'code':         'NO_REPRESENTATIVES_RETRIEVED',
            'description':  'There are no representatives stored for this Office.',
        },
    ]

    try_now_link_variables_dict = {
        'year': '2023',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "index_start": integer,\n' \
                   '  "kind": string,\n' \
                   '  "office_held_list": {\n' \
                   '     "district_id": string,\n' \
                   '     "district_name": string,\n' \
                   '     "name": string,\n' \
                   '     "ocd_division_id": string,\n' \
                   '     "office_held_description": string,\n' \
                   '     "office_held_facebook_url": string,\n' \
                   '     "office_held_id": integer,\n' \
                   '     "office_held_name": string,\n' \
                   '     "office_held_twitter_handle": string,\n' \
                   '     "office_held_url": string,\n' \
                   '     "office_held_we_vote_id": string,\n' \
                   '     "state_code": string,\n' \
                   '     "vote_usa_office_id": string,\n' \
                   '   },\n' \
                   '  "representatives": list\n' \
                   '   [\n' \
                   '     {\n' \
                   '       "id": integer,\n' \
                   '       "we_vote_id": string,\n' \
                   '       "ballot_item_display_name": string,\n' \
                   '       "facebook_url": string,\n' \
                   '       "instagram_followers_count": integer,\n' \
                   '       "instagram_handle": string,\n' \
                   '       "is_battleground_race_2019": boolean,\n' \
                   '       "is_battleground_race_2020": boolean,\n' \
                   '       "is_battleground_race_2021": boolean,\n' \
                   '       "is_battleground_race_2022": boolean,\n' \
                   '       "is_battleground_race_2023": boolean,\n' \
                   '       "is_battleground_race_2024": boolean,\n' \
                   '       "is_battleground_race_2025": boolean,\n' \
                   '       "is_battleground_race_2026": boolean,\n' \
                   '       "is_battleground_race_2027": boolean,\n' \
                   '       "is_battleground_race_2028": boolean,\n' \
                   '       "is_battleground_race_2029": boolean,\n' \
                   '       "is_battleground_race_2030": boolean,\n' \
                   '       "is_claimed_profile": boolean,\n' \
                   '       "last_updated": string (time in this format ' + DATE_FORMAT_YMD_HMS + '),\n' \
                   '       "linked_campaignx_we_vote_id": string,\n' \
                   '       "linkedin_url": string,\n' \
                   '       "ocd_division_id": string,\n' \
                   '       "office_held_id": string,\n' \
                   '       "office_held_district_name": string,\n' \
                   '       "office_held_name": string,\n' \
                   '       "office_held_we_vote_id": string,\n' \
                   '       "political_party": string,\n' \
                   '       "politician_id": integer,\n' \
                   '       "politician_we_vote_id": string,\n' \
                   '       "profile_image_background_color": string,\n' \
                   '       "representative_contact_form_url": string,\n' \
                   '       "representative_email": string,\n' \
                   '       "representative_email2": string,\n' \
                   '       "representative_email3": string,\n' \
                   '       "representative_name": string,\n' \
                   '       "representative_phone": string,\n' \
                   '       "representative_phone2": string,\n' \
                   '       "representative_phone3": string,\n' \
                   '       "representative_photo_url_large": string,\n' \
                   '       "representative_photo_url_medium": string,\n' \
                   '       "representative_photo_url_tiny": string,\n' \
                   '       "representative_url": string,\n' \
                   '       "seo_friendly_path": string,\n' \
                   '       "state_code": string,\n' \
                   '       "supporters_count": integer,\n' \
                   '       "twitter_url": string,\n' \
                   '       "twitter_handle": string,\n' \
                   '       "twitter_description": string,\n' \
                   '       "twitter_followers_count": integer,\n' \
                   '       "wikipedia_url": string,\n' \
                   '       "year_in_office_2023": boolean,\n' \
                   '       "year_in_office_2024": boolean,\n' \
                   '       "year_in_office_2025": boolean,\n' \
                   '       "year_in_office_2026": boolean,\n' \
                   '       "year_in_office_2027": boolean,\n' \
                   '       "year_in_office_2028": boolean,\n' \
                   '       "year_in_office_2029": boolean,\n' \
                   '       "year_in_office_2030": boolean,\n' \
                   '       "youtube_url": string,\n' \
                   '     },\n' \
                   '   ],\n' \
                   '  "returned_count": integer,\n' \
                   '  "total_count": integer,\n' \
                   '  "state": string,\n' \
                   '}'

    template_values = {
        'api_name': 'representativesQuery',
        'api_slug': 'representativesQuery',
        'api_introduction':
            "Retrieve all the representatives in a particular election or state.",
        'try_now_link': 'apis_v1:representativesQueryView',
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
