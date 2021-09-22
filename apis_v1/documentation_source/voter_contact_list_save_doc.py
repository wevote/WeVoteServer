# apis_v1/documentation_source/voter_contact_list_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_contact_list_save_doc_template_values(url_root):
    """
    Show documentation about voterContactListSave
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
            'name':         'contacts',
            'value':        'string',  # boolean, integer, long, string
            'description':  'A json structure of Google contacts, arrives as a string',
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
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "we_vote_id_for_google_contacts" string, \n' \
                   '  "contacts_stored": integer, \n' \
                   '}'

    template_values = {
        'api_name': 'voterContactListSave',
        'api_slug': 'voterContactListSave',
        'api_introduction':
            'Receive a voter&apos;s Google contacts for saving.<br>'
            '<b>Example JSON string to add one contact:</b><br>'
            '&nbsp;&nbsp;[{"display_name": "George Washington","family_name": "Washington",'
            '"given_name": "George","email": "george@whitehouse.com","update_time": "2014-03-20T16:36:33.176Z",'
            '"type": "OTHER_CONTACT"}]<br>',
        'try_now_link': 'apis_v1:voterContactListSaveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'post',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
