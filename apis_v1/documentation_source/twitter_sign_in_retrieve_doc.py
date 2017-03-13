# apis_v1/documentation_source/twitter_sign_in_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def twitter_sign_in_retrieve_doc_template_values(url_root):
    """
    Show documentation about twitterSignInRetrieve
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
                   '  "voter_we_vote_id_attached_to_twitter": string,\n' \
                   '  "voter_we_vote_id_attached_to_twitter_email": string,\n' \
                   '  "twitter_retrieve_attempted": boolean,\n' \
                   '  "twitter_sign_in_found": boolean,\n' \
                   '  "twitter_sign_in_verified": boolean,\n' \
                   '  "twitter_access_token": string,\n' \
                   '  "twitter_signed_request": string,\n' \
                   '  "twitter_user_id": string,\n' \
                   '  "twitter_email": string,\n' \
                   '  "twitter_first_name": string,\n' \
                   '  "twitter_middle_name": string,\n' \
                   '  "twitter_last_name": string,\n' \
                   '  "twitter_profile_image_url_https": string,\n' \
                   '  "we_vote_hosted_profile_image_url_large": string,\n' \
                   '  "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '  "we_vote_hosted_profile_image_url_tny": string,\n' \
                   '}'

    template_values = {
        'api_name': 'twitterSignInRetrieve',
        'api_slug': 'twitterSignInRetrieve',
        'api_introduction':
            "Retrieve the Twitter Sign In status based on voter_device_id.",
        'try_now_link': 'apis_v1:twitterSignInRetrieveView',
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
