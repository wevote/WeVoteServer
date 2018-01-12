# apis_v1/documentation_source/organizations_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organizations_sync_out_doc_template_values(url_root):
    """
    Show documentation about organizationsSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'state_served_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the results to just the state requested.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "vote_smart_id": integer,\n' \
                   '  "ballotpedia_page_title": string,\n' \
                   '  "ballotpedia_photo_url": string,\n' \
                   '  "organization_address": string,\n' \
                   '  "organization_city": string,\n' \
                   '  "organization_contact_name": string,\n' \
                   '  "organization_description": string,\n' \
                   '  "organization_email": string,\n' \
                   '  "organization_facebook": string,\n' \
                   '  "organization_name": string,\n' \
                   '  "organization_image": string,\n' \
                   '  "organization_phone1": string,\n' \
                   '  "organization_phone2": string,\n' \
                   '  "organization_fax": string,\n' \
                   '  "organization_state": string,\n' \
                   '  "organization_type": string,\n' \
                   '  "organization_twitter_handle": string,\n' \
                   '  "organization_website": string,\n' \
                   '  "organization_zip": string,\n' \
                   '  "state_served_code": string,\n' \
                   '  "twitter_description": string,\n' \
                   '  "twitter_followers_count": integer,\n' \
                   '  "twitter_location": string,\n' \
                   '  "twitter_name": string,\n' \
                   '  "twitter_profile_background_image_url_https": string,\n' \
                   '  "twitter_profile_banner_url_https": string,\n' \
                   '  "twitter_profile_image_url_https": string,\n' \
                   '  "twitter_user_id": integer,\n' \
                   '  "wikipedia_page_id": string,\n' \
                   '  "wikipedia_page_title": string,\n' \
                   '  "wikipedia_photo_url": string,\n' \
                   '  "wikipedia_thumbnail_height": string,\n' \
                   '  "wikipedia_thumbnail_url": string,\n' \
                   '  "wikipedia_thumbnail_width": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'organizationsSyncOut',
        'api_slug': 'organizationsSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:organizationsSyncOutView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
