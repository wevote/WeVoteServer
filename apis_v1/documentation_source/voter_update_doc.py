# apis_v1/documentation_source/voter_update_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_update_doc_template_values(url_root):
    """
    Show documentation about voterUpdate
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
        {
            'name':         'facebook_email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The voter\'s email from facebook.',
        },
        {
            'name':         'facebook_profile_image_url_https',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url on the facebook servers of this person\'s profile photo.',
        },
        {
            'name':         'first_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The first name to update to.',
        },
        {
            'name':         'middle_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The middle name to update to.',
        },
        {
            'name':         'last_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The last name (family name) to update to.',
        },
        {
            'name':         'twitter_profile_image_url_https',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url on the twitter servers of this person\'s profile photo.',
        },
        {
            'name':         'interface_status_flags',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'An integer whose bits represent several flags for the user, such as the ',
        },
        {
            'name':         'flag_integer_to_set',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Sets the corresponding bit represented by this integer\'s bit, '
                            'in interface_status_flags bit',
        },
        {
            'name':         'flag_integer_to_unset',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Unsets the corresponding bit represented by this integer\'s bit, '
                            'in interface_status_flags bit',
        },
        {
            'name': 'notification_settings_flags',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'An integer whose bits represent several flags for the user, such as the ',
        },
        {
            'name': 'notification_flag_integer_to_set',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'Sets the corresponding bit represented by this integer\'s bit, '
                           'in notification_settings_flags bit',
        },
        {
            'name': 'notification_flag_integer_to_unset',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'Unsets the corresponding bit represented by this integer\'s bit, '
                           'in notification_settings_flags bit',
        },
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
            'code':         'UPDATED_VOTER',
            'description':  'Successfully saved',
        },
    ]

    try_now_link_variables_dict = {
        'facebook_email': 'False',
        'facebook_profile_image_url_https': 'False',
        'first_name': 'False',
        'middle_name': 'False',
        'last_name': 'False',
        'twitter_profile_image_url_https': 'False',
        'interface_status_flags': 'False',
        'flag_integer_to_set': 'False',
        'flag_integer_to_unset': 'False',
        'notification_settings_flags': 'False',
        'notification_flag_integer_to_set': 'False',
        'notification_flag_integer_to_unset': 'False',
    }

    # TODO: update api_response with all the variables, such as first_name and last_name
    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (True as long as no db errors),\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_updated": boolean (did the voter address save happen?),\n' \
                   '  "facebook_profile_image_url_https": string,\n' \
                   '  "twitter_profile_image_url_https": string,\n' \
                   '  "we_vote_hosted_profile_image_url_large": string,\n' \
                   '  "we_vote_hosted_profile_image_url_medium": string,\n' \
                   '  "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '  "interface_status_flags": integer,\n' \
                   '  "flag_integer_to_set": integer,\n' \
                   '  "flag_integer_to_unset": integer,\n' \
                   '  "notification_settings_flags": integer,\n' \
                   '  "notification_flag_integer_to_set": integer,\n' \
                   '  "notification_flag_integer_to_unset": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterUpdate',
        'api_slug': 'voterUpdate',
        'api_introduction':
            "Update profile-related information for the current voter. If the string 'False' is passed "
            "(or the boolean value), do not update the field.",
        'try_now_link': 'apis_v1:voterUpdateView',
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
