# apis_v1/documentation_source/voter_facebook_sign_in_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_facebook_sign_in_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterFacebookSignInRetrieve
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
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_we_vote_id_attached_to_facebook": string,\n' \
                   '  "voter_we_vote_id_attached_to_facebook_email": string,\n' \
                   '  "facebook_retrieve_attempted": boolean,\n' \
                   '  "facebook_sign_in_found": boolean,\n' \
                   '  "facebook_sign_in_verified": boolean,\n' \
                   '  "facebook_access_token": string,\n' \
                   '  "facebook_signed_request": string,\n' \
                   '  "facebook_user_id": string,\n' \
                   '  "facebook_email": string,\n' \
                   '  "facebook_first_name": string,\n' \
                   '  "facebook_middle_name": string,\n' \
                   '  "facebook_last_name": string,\n' \
                   '  "facebook_profile_image_url_https": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterFacebookSignInRetrieve',
        'api_slug': 'voterFacebookSignInRetrieve',
        'api_introduction':
            "Retrieve the Facebook Sign In status based on voter_device_id.",
        'try_now_link': 'apis_v1:voterFacebookSignInRetrieveView',
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
