# apis_v1/documentation_source/voter_aggregate_analytics_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_aggregate_analytics_doc_template_values(url_root):
    """
    Show documentation about voterAggregateAnalytics
    """
    required_query_parameter_list = [
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
        {
            'name':         'show_county_topics',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Include statistics about topics followed by voters county-by-county.',
        },
        {
            'name':         'show_state_topics',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Include statistics about topics followed by voters in each state.',
        },
        {
            'name':         'show_this_year_of_analytics',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit results to the analytics of this one year.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        # 'voter_device_id': '',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "voters": integer (the number of voters who used We Vote, limited by search parameters),\n' \
                   '  "voters_with_topics": integer (the number of voters following at least one topic),\n' \
                   '  "percent_of_voters_with_topics": integer (voters_with_topics / voters),\n' \
                   '  "year": integer (the year shown, default is "all years"),\n' \
                   '  "states": dict\n' \
                   '   {\n' \
                   '     "<STATE_CODE>": 2-digit string all-caps, key for dict,\n' \
                   '       {\n' \
                   '         "state_name": string,\n' \
                   '         "voters": integer (the number of voters who used We Vote in this state),\n' \
                   '         "voters_with_any_topic": integer (# of voters in this state who chose 1+ topics),\n' \
                   '         "counties": list of dicts (all counties that included activity)\n' \
                   '         [{\n' \
                   '           "county_name": string, (display name)\n' \
                   '           "county_short_name": string,\n' \
                   '           "county_fips_code": string,\n' \
                   '           "voters": integer (the number of voters who used We Vote in this county),\n' \
                   '           "voters_with_any_topic": integer (# of voters in this county who chose 1+ topics),\n' \
                   '           "percent_of_voters_with_any_topic": integer (voters_with_any_topic / voters),\n' \
                   '           "topics_by_county": list (all topics in this county that included activity)\n' \
                   '           [{\n' \
                   '             "topic_name": string,\n' \
                   '             "issue_we_vote_id": string,\n' \
                   '             "voters_with_topic": integer (# of voters in this county who followed this topic),\n' \
                   '             "percent_of_voters": (voters_with_topic / voters in county),\n' \
                   '             "percent_of_voters_with_any_topic": ' \
                   '(voters_with_topic / voters_with_any_topic in county),\n' \
                   '           }],\n' \
                   '         }],\n' \
                   '       },\n' \
                   '   },\n' \
                   '}'

    template_values = {
        'api_name': 'voterAggregateAnalytics',
        'api_slug': 'voterAggregateAnalytics',
        'api_introduction':
            "Retrieve the number of voters who have used We Vote. Many fields are not returned under some search "
            "configurations.",
        'try_now_link': 'apis_v1:voterAggregateAnalyticsView',
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
