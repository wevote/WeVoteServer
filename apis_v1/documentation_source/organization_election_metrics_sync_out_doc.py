# apis_v1/documentation_source/organization_election_metrics_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_election_metrics_sync_out_doc_template_values(url_root):
    """
    Show documentation about organizationElectionMetricsSyncOut
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
                   '  "authenticated_visitors_total": integer,\n' \
                   '  "election_day_text": string,\n' \
                   '  "entrants_friends_only_positions": integer,\n' \
                   '  "entrants_friends_only_positions_with_comments": integer,\n' \
                   '  "entrants_public_positions": integer,\n' \
                   '  "entrants_public_positions_with_comments": integer,\n' \
                   '  "entrants_took_position": integer,\n' \
                   '  "entrants_visited_ballot": integer,\n' \
                   '  "followers_at_time_of_election": integer,\n' \
                   '  "followers_friends_only_positions": integer,\n' \
                   '  "followers_friends_only_positions_with_comments": integer,\n' \
                   '  "followers_public_positions": integer,\n' \
                   '  "followers_public_positions_with_comments": integer,\n' \
                   '  "followers_took_position": integer,\n' \
                   '  "followers_visited_ballot": integer,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "new_auto_followers": integer,\n' \
                   '  "new_followers": integer,\n' \
                   '  "organization_we_vote_id": integer,\n' \
                   '  "visitors_total": integer,\n' \
                   '  "voter_guide_entrants": integer,\n' \
                   '}]'

    template_values = {
        'api_name': 'organizationElectionMetricsSyncOut',
        'api_slug': 'organizationElectionMetricsSyncOut',
        'api_introduction':
            "Allow people with Analytics Admin authority to retrieve election metrics for one organization information "
            "for data analysis purposes.",
        'try_now_link': 'apis_v1:organizationElectionMetricsSyncOutView',
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
