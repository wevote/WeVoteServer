# apis_v1/documentation_source/voter_sms_phone_number_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_sms_phone_number_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterSMSPhoneNumberRetrieve
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
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            'description':  'No voter could be found from the voter_device_id',
        },
    ]

    try_now_link_variables_dict = {
        # 'voter_device_id': '',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "sms_phone_number_list_found": boolean,\n' \
                   '  "sms_phone_number_list": list\n' \
                   '   [\n' \
                   '     "normalized_sms_phone_number": string,\n' \
                   '     "primary_sms_phone_number": boolean,\n' \
                   '     "sms_permanent_bounce": boolean,\n' \
                   '     "sms_ownership_is_verified": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "sms_we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterSMSPhoneNumberRetrieve',
        'api_slug': 'voterSMSPhoneNumberRetrieve',
        'api_introduction':
            "Retrieve a list of all of the sms phone numbers for voter using voter_device_id.",
        'try_now_link': 'apis_v1:voterSMSPhoneNumberRetrieveView',
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
