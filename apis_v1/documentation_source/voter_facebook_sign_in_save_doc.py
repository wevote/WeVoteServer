# apis_v1/documentation_source/voter_facebook_sign_in_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_facebook_sign_in_save_doc_template_values(url_root):
    """
    Show documentation about voterFacebookSignInSave
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'save_auth_data',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Listen for facebook authentication data.',
        },
        {
            'name':         'facebook_access_token',  # Comes with save_auth_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'The Facebook accessToken',
        },
        {
            'name':         'facebook_user_id',  # Comes with save_auth_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'The Facebook big integer id',
        },
        {
            'name':         'facebook_expires_in',  # Comes with save_auth_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'The Facebook expiresIn',
        },
        {
            'name':         'facebook_signed_request',  # Comes with save_auth_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'The Facebook signedRequest',
        },
        # ##########################
        {
            'name':         'save_profile_data',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Listen for facebook profile data.',
        },
        {
            'name':         'facebook_email',  # Comes with save_profile_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'Email address from Facebook',
        },
        {
            'name':         'facebook_first_name',  # Comes with save_profile_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'First name from Facebook',
        },
        {
            'name':         'facebook_middle_name',  # Comes with save_profile_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'Middle name from Facebook',
        },
        {
            'name':         'facebook_last_name',  # Comes with save_profile_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'Last name from Facebook',
        },
        {
            'name':         'facebook_profile_image_url_https',  # Comes with save_profile_data
            'value':        'string',  # boolean, integer, long, string
            'description':  'Email address from Facebook',
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
            'code':         'MISSING_VOTER_ID_OR_ADDRESS_TYPE',
            'description':  'Cannot proceed. Missing variables voter_id or address_type while trying to save.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "facebook_save_attempted": boolean,\n' \
                   '  "facebook_sign_in_saved": boolean,\n' \
                   '}'

    template_values = {
        'api_name': 'voterFacebookSignInSave',
        'api_slug': 'voterFacebookSignInSave',
        'api_introduction':
            "Save the results of Facebook sign in authentication.",
        'try_now_link': 'apis_v1:voterFacebookSignInSaveView',
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
