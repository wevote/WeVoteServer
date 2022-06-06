# apis_v1/documentation_source/voter_contact_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def doc_template_values(url_root):
    """
    Show documentation about voterContactSave
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
            'description':  'An 88 character unique identifier linked to a voter record on the server. ',
        },
        {
            'name':         'email_address_text',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The email of the VoterContactEmail that we want to alter.',
        },
    ]

    optional_query_parameter_list = [
        {
            'name': 'ignore_voter_contact',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'Set to true if the voter wants to ignore this VoterContact entry.',
        },
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
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "ignore_voter_contact" boolean, \n' \
                   '  "email_address_text": string, \n' \
                   '}'

    template_values = {
        'api_name': 'voterContactSave',
        'api_slug': 'voterContactSave',
        'api_introduction':
            'Make changes to specific voterContactEmail entries.',
        'try_now_link': 'apis_v1:voterContactSaveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'get',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
