# apis_v1/documentation_source/sitewide_daily_metrics_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def sitewide_daily_metrics_sync_out_doc_template_values(url_root):
    """
    Show documentation about sitewideDailyMetricsSyncOut
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
                   '  "authenticated_visitors_today": integer,\n' \
                   '  "authenticated_visitors_total": integer,\n' \
                   '  "ballot_views_today": integer,\n' \
                   '  "date_as_integer": integer,\n' \
                   '  "entered_full_address": integer,\n' \
                   '  "friend_entrants_today": integer,\n' \
                   '  "friends_only_positions": integer,\n' \
                   '  "individuals_with_friends_only_positions": integer,\n' \
                   '  "individuals_with_positions": integer,\n' \
                   '  "individuals_with_public_positions": integer,\n' \
                   '  "issue_follows_today": integer,\n' \
                   '  "issue_follows_total": integer,\n' \
                   '  "issues_followed_today": integer,\n' \
                   '  "issues_followed_total": integer,\n' \
                   '  "issues_linked_today": integer,\n' \
                   '  "issues_linked_total": integer,\n' \
                   '  "new_visitors_today": integer,\n' \
                   '  "organization_public_positions": integer,\n' \
                   '  "organizations_auto_followed_today": integer,\n' \
                   '  "organizations_auto_followed_total": integer,\n' \
                   '  "organizations_followed_today": integer,\n' \
                   '  "organizations_followed_total": integer,\n' \
                   '  "organizations_signed_in_total": integer,\n' \
                   '  "organizations_with_linked_issues": integer,\n' \
                   '  "organizations_with_new_positions_today": integer,\n' \
                   '  "organizations_with_positions": integer,\n' \
                   '  "visitors_today": integer,\n' \
                   '  "visitors_total": integer,\n' \
                   '  "voter_guide_entrants_today": integer,\n' \
                   '  "voter_guides_viewed_today": integer,\n' \
                   '  "voter_guides_viewed_total": integer,\n' \
                   '  "welcome_page_entrants_today": integer,\n' \
                   '}]'

    template_values = {
        'api_name': 'sitewideDailyMetricsSyncOut',
        'api_slug': 'sitewideDailyMetricsSyncOut',
        'api_introduction':
            "Allow people with Analytics Admin authority to retrieve daily metrics information "
            "for data analysis purposes.",
        'try_now_link': 'apis_v1:sitewideDailyMetricsSyncOutView',
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
