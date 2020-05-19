# apis_v1/documentation_source/voter_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterRetrieve
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
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server. '
                            'If not provided, a new voter_device_id (and voter entry) '
                            'will be generated, and the voter_device_id will be returned.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_RETRIEVE',
            'description':  'There is no voter_id attached to that voter_device_id',
        },
        {
            'code':         'VOTER_ID_COULD_NOT_BE_RETRIEVED',
            'description':  'Unable to retrieve voter_id, although voter_id was found linked to voter_device_id',
        },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (True as long as no db errors),\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_created": boolean,\n' \
                   '  "voter_found": boolean,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "facebook_id": integer,\n' \
                   '  "email": string,\n' \
                   '  "facebook_email": string,\n' \
                   '  "facebook_profile_image_url_https": string,\n' \
                   '  "full_name": string,\n' \
                   '  "first_name": string,\n' \
                   '  "last_name": string,\n' \
                   '  "twitter_screen_name": string,\n' \
                   '  "is_signed_in": boolean,\n' \
                   '  "is_admin": boolean,\n' \
                   '  "is_analytics_admin": boolean,\n' \
                   '  "is_partner_organization": boolean,\n' \
                   '  "is_political_data_manager": boolean,\n' \
                   '  "is_political_data_viewer": boolean,\n' \
                   '  "is_verified_volunteer": boolean,\n' \
                   '  "signed_in_facebook": boolean,\n' \
                   '  "signed_in_google": boolean,\n' \
                   '  "signed_in_twitter": boolean,\n' \
                   '  "signed_in_with_email": boolean,\n' \
                   '  "has_valid_email": boolean,\n' \
                   '  "has_data_to_preserve": boolean,\n' \
                   '  "has_email_with_verified_ownership": boolean,\n' \
                   '  "linked_organization_we_vote_id": string,\n' \
                   '  "voter_photo_url_large": string,\n' \
                   '  "voter_photo_url_medium": string,\n' \
                   '  "voter_photo_url_tiny": string,\n' \
                   '  "interface_status_flags": integer,\n' \
                   '  "notification_settings_flags": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterRetrieve',
        'api_slug': 'voterRetrieve',
        'api_introduction': "Export key voter data to JSON format",
        'try_now_link': 'apis_v1:voterRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes': "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
