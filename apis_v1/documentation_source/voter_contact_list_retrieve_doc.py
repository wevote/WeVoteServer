# apis_v1/documentation_source/voter_contact_list_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_contact_list_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterContactListRetrieve
    """
    required_query_parameter_list = [
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]

    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit results to this election',
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
                   '  "voter_contact_email_list": list\n' \
                   '   [{\n' \
                   '     "date_last_changed": string,\n' \
                   '     "email_address_text": string,\n' \
                   '     "google_contact_id": string,\n' \
                   '     "google_date_last_updated": string,\n' \
                   '     "google_display_name": string,\n' \
                   '     "google_first_name": string,\n' \
                   '     "google_last_name": string,\n' \
                   '     "has_data_from_google_people_api": boolean,\n' \
                   '     "ignore_contact": boolean,\n' \
                   '     "imported_by_voter_we_vote_id": string,\n' \
                   '     "is_friend": boolean,\n' \
                   '     "state_code": string,\n' \
                   '   },],\n' \
                   '}'

    template_values = {
        'api_name': 'voterContactListRetrieve',
        'api_slug': 'voterContactListRetrieve',
        'api_introduction':
            "Retrieve a voter_contact_list that we can display publicly.",
        'try_now_link': 'apis_v1:voterContactListRetrieveView',
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
