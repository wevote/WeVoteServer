# apis_v1/documentation_source/voter_notification_settings_update_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_notification_settings_update_doc_template_values(url_root):
    """
    Show documentation about voterNotificationSettingsUpdate
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
            'name':         'email_subscription_secret_key',
            'value':        'string',  # boolean, integer, long, string
            'description':  'A long string which tells us which email we want the notification options updated for. ',
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
            'code':         'UPDATED_VOTER',
            'description':  'Successfully saved',
        },
    ]

    try_now_link_variables_dict = {
        'email_subscription_secret_key': '',
        'interface_status_flags': 'False',
        'flag_integer_to_set': 'False',
        'flag_integer_to_unset': 'False',
        'notification_settings_flags': 'False',
        'notification_flag_integer_to_set': 'False',
        'notification_flag_integer_to_unset': 'False',
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (True as long as no db errors),\n' \
                   '  "voter_found": boolean (True if voter found from secret key),\n' \
                   '  "voter_updated": boolean (True if save executed successfully),\n' \
                   '  "email_subscription_secret_key": string (88 characters long),\n' \
                   '  "sms_subscription_secret_key": string (88 characters long),\n' \
                   '  "interface_status_flags": integer,\n' \
                   '  "flag_integer_to_set": integer,\n' \
                   '  "flag_integer_to_unset": integer,\n' \
                   '  "notification_settings_flags": integer,\n' \
                   '  "notification_flag_integer_to_set": integer,\n' \
                   '  "notification_flag_integer_to_unset": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterNotificationSettingsUpdate',
        'api_slug': 'voterNotificationSettingsUpdate',
        'api_introduction':
            "Update profile-related information for a voter based on secret key. If the string 'False' is passed "
            "(or the boolean value), do not update the field.",
        'try_now_link': 'apis_v1:voterNotificationSettingsUpdateView',
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
