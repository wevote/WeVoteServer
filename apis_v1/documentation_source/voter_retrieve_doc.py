# apis_v1/documentation_source/voter_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterRetrieve
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
    ]
    optional_query_parameter_list = [
        {
            'name':         'format',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Although optional, We Vote is built using the json value',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_DEVICE_ID',
            'description':  'There is no voter_id attached to that voter_device_id',
        },
        {
            'code':         'VOTER_ID_COULD_NOT_BE_RETRIEVED',
            'description':  'Unable to retrieve voter_id, although voter_id was found linked to voter_device_id',
        },
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = 'SUCCESS:\n'\
                   '[{\n' \
                   '  "id": integer,\n' \
                   '  "first_name": string,\n' \
                   '  "last_name": string,\n' \
                   '  "email": string,\n' \
                   '}]\n'\
                   'FAILURE:\n'\
                   '{\n' \
                   '  "status": string,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'voterRetrieve',
        'api_slug': 'voterRetrieve/?format=json',
        'api_introduction':
            "Export the raw voter data to JSON format",
        'try_now_link': 'apis_v1:voterRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "NOTE: Success returns a single entry in a json list, "
            "so you need to loop through that list to get to the single voter entry.",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
