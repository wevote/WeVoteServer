# apis_v1/documentation_source/sitewide_voter_metrics_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def sitewide_voter_metrics_sync_out_doc_template_values(url_root):
    """
    Show documentation about sitewideVoterMetricsSyncOut
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
                   '  "actions_count": integer,\n' \
                   '  "ballot_visited": integer,\n' \
                   '  "comments_entered_friends_only": integer,\n' \
                   '  "comments_entered_public": integer,\n' \
                   '  "days_visited": integer,\n' \
                   '  "elections_viewed": integer,\n' \
                   '  "entered_full_address": integer,\n' \
                   '  "issues_followed": integer,\n' \
                   '  "last_action_date": integer,\n' \
                   '  "last_calculated_date_as_integer": integer,\n' \
                   '  "organizations_followed": integer,\n' \
                   '  "positions_entered_friends_only": integer,\n' \
                   '  "positions_entered_public": integer,\n' \
                   '  "seconds_on_site": integer,\n' \
                   '  "signed_in_facebook": integer,\n' \
                   '  "signed_in_twitter": integer,\n' \
                   '  "signed_in_with_email": integer,\n' \
                   '  "signed_in_with_sms_phone_number": integer,\n' \
                   '  "time_until_sign_in": integer,\n' \
                   '  "voter_guides_viewed": integer,\n' \
                   '  "voter_we_vote_id": integer,\n' \
                   '  "welcome_visited": integer,\n' \
                   '}]'

    template_values = {
        'api_name': 'sitewideVoterMetricsSyncOut',
        'api_slug': 'sitewideVoterMetricsSyncOut',
        'api_introduction':
            "Allow people with Analytics Admin authority to retrieve voter metrics information "
            "for data analysis purposes.",
        'try_now_link': 'apis_v1:sitewideVoterMetricsSyncOutView',
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
