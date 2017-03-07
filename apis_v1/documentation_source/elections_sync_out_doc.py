# apis_v1/documentation_source/elections_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def elections_sync_out_doc_template_values(url_root):
    """
    Show documentation about electionsSyncOut
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

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = 'SUCCESS:\n'\
                   '[{\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "election_name": string,\n' \
                   '  "election_day_text": string,\n' \
                   '  "get_election_state": string,\n' \
                   '  "ocd_division_id": string,\n' \
                   '}]\n'\
                   'FAILURE:\n'\
                   '{\n' \
                   '  "status": string,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'electionsSyncOut',
        'api_slug': 'electionsSyncOut/?format=json',
        'api_introduction':
            "Export the raw elections data stored in the database to JSON format. "
            "This API call does not reach out to the Google Civic API, but simply returns data that was retrieved "
            "earlier.",
        'try_now_link': 'apis_v1:electionsSyncOutView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "NOTE: Success returns a single entry in a json list, "
            "so you need to loop through that list to get to the single election entry.",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
