# apis_v1/documentation_source/device_id_generate_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def device_store_firebase_fcm_token_doc_template_values(url_root):
    """
    Show documentation about deviceStoreFirebaseCloudMessagingToken
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
            'name':         'platform_type',
            'value':        'string',  # boolean, integer, long, string
            'description':  'One of {"IOS", "ANDROID", WEBAPP"} ',
        },
        {
            'name':         'firebase_fcm_token',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique Firebase Cloud Messaging Token assigned to the calling device by Firebase',
        },
    ]
    optional_query_parameter_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n'
    '}'

    template_values = {
        'api_name': 'deviceStoreFirebaseCloudMessagingToken',
        'api_slug': 'deviceStoreFirebaseCloudMessagingToken',
        'api_introduction':
            "Store the Firebase Cloud Messaging Token, which has been generated for this device by Google's Firebase"
            "cloud service.  This token allows WeVote to send a notification to the device via an API call to the"
            "Firebase Service.  These notifications (in iOS) will appear on screen even if the WeVoteCordova app is not"
            "currently running.  (Android has different conditions).",
        'try_now_link': 'apis_v1:deviceStoreFirebaseCloudMessagingToken',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
    }
    return template_values
