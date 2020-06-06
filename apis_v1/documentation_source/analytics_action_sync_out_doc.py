# apis_v1/documentation_source/analytics_action_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def analytics_action_sync_out_doc_template_values(url_root):
    """
    Show documentation about analyticsActionSyncOut
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name': 'voter_device_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'An 88 character unique identifier linked to a voter record on the server. '
                           'If not provided, a new voter_device_id (and voter entry) '
                           'will be generated, and the voter_device_id will be returned.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'starting_date_as_integer',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The earliest date for the batch we are retrieving. Format: YYYYMMDD (ex/ 20200131) '
                            '(Default is 3 months ago)',
        },
        {
            'name':         'ending_date_as_integer',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Retrieve data through this date. Format: YYYYMMDD (ex/ 20200228) (Default is right now.)'
        },
        {
            'name':         'return_csv_format',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'If set to true, return results in CSV format instead of JSON.'
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
    }

    api_response = '[{\n' \
                   '  "id": integer,\n' \
                   '  "action_constant": string,\n' \
                   '  "action_constant_text": string,\n' \
                   '  "authentication_failed_twice": string,\n' \
                   '  "ballot_item_we_vote_id": string,\n' \
                   '  "date_as_integer": integer,\n' \
                   '  "exact_time": string,\n' \
                   '  "first_visit_today": boolean,\n' \
                   '  "google_civic_election_id": string,\n' \
                   '  "is_bot": boolean,\n' \
                   '  "is_desktop": boolean,\n' \
                   '  "is_mobile": boolean,\n' \
                   '  "is_signed_in": boolean,\n' \
                   '  "is_tablet": boolean,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "state_code": string,\n' \
                   '  "user_agent": string,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'analyticsActionSyncOut',
        'api_slug': 'analyticsActionSyncOut',
        'api_introduction':
            "Allow people with Analytics Admin authority to retrieve raw Analytics Action information "
            "for data analysis purposes. The definitions of the ACTION constants ('action_constant') are here: "
            "https://github.com/wevote/WeVoteServer/blob/develop/analytics/models.py",
        'try_now_link': 'apis_v1:analyticsActionSyncOutView',
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
