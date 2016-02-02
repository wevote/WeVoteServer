# apis_v1/documentation_source/voter_photo_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_photo_save_doc_template_values(url_root):
    """
    Show documentation about voterPhotoSave
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
            'description':  'An 88 character unique identifier (from cookie - not URL variable) linked to '
                            'a voter record on the server',
        },
        {
            'name':         'facebook_profile_image_url_https',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url on the facebook servers of this person\'s profile photo.',
        },
        {
            'name':         'twitter_profile_image_url_https',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url on the twitter servers of this person\'s profile photo.',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'MISSING_VOTER_ID',
            'description':  'Cannot proceed. Missing variables voter_id while trying to save.',
        },
        {
            'code':         'VOTER_PHOTO_SAVED',
            'description':  'Successfully saved',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (True as long as no db errors),\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_photo_saved": boolean (did the voter address save happen?),\n' \
                   '  "facebook_profile_image_url_https": string,\n' \
                   '  "twitter_profile_image_url_https": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterPhotoSave',
        'api_slug': 'voterPhotoSave',
        'api_introduction':
            "Save one or more photos for the current voter.",
        'try_now_link': 'apis_v1:voterPhotoSaveView',
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
