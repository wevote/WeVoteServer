# apis_v1/documentation_source/voter_sms_phone_number_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_sms_phone_number_save_doc_template_values(url_root):
    """
    Show documentation about voterSMSPhoneNumberSave
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
            'name':         'sms_phone_number',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The phone number to be saved.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'delete_sms_phone_number',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'When this variable is passed in as true, mark this sms phone number as deleted.',
        },
        {
            'name':         'make_primary_sms_phone_number',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'When passed in as true, change this (verified) sms phone number to be the primary.',
        },
        {
            'name':         'resend_verification_code',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Send the a verification code to this sms phone number again.',
        },
        {
            'name':         'send_sign_in_code_sms',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Send the verification code to this sms phone number.',
        },
        {
            'name':         'sms_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this sms across all networks ',
        },
        {
            'name':         'verify_sms_phone_number',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'When this variable is passed in as true, change this sms phone number to verified.',
        },
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
                   '  "sms_phone_number": string,\n' \
                   '  "make_primary_sms_phone_number": boolean,\n' \
                   '  "delete_sms_phone_number": boolean,\n' \
                   '  "sms_phone_number_saved_we_vote_id": string,\n' \
                   '  "sms_phone_number_created": boolean,\n' \
                   '  "sms_phone_number_deleted": boolean,\n' \
                   '  "verification_code_sent": boolean,\n' \
                   '  "sms_phone_number_already_owned_by_other_voter": boolean,\n' \
                   '  "sms_phone_number_found": boolean,\n' \
                   '  "sms_phone_number_list_found": boolean,\n' \
                   '  "sms_phone_number_list": list\n' \
                   '   [\n' \
                   '     "normalized_sms_phone_number": string,\n' \
                   '     "primary_sms_phone_number": boolean,\n' \
                   '     "sms_phone_number_permanent_bounce": boolean,\n' \
                   '     "sms_phone_number_ownership_is_verified": boolean,\n' \
                   '     "voter_we_vote_id": string,\n' \
                   '     "sms_phone_number_we_vote_id": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'voterSMSPhoneNumberSave',
        'api_slug': 'voterSMSPhoneNumberSave',
        'api_introduction':
            "Save or create an SMS phone number for the current voter.",
        'try_now_link': 'apis_v1:voterSMSPhoneNumberSaveView',
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
