# apis_v1/documentation_source/positions_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def positions_sync_out_doc_template_values(url_root):
    """
    Show documentation about positionsSyncOut
    """
    required_query_parameter_list = [
        {
            'name':         'format',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Currently must be \'json\' to work.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The election for which we want positions.',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
        'google_civic_election_id': '1000000',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "ballot_item_display_name": string,\n' \
                   '  "ballot_item_image_url_https": string,\n' \
                   '  "candidate_campaign_we_vote_id": string,\n' \
                   '  "contest_measure_we_vote_id": string,\n' \
                   '  "contest_office_we_vote_id": string,\n' \
                   '  "date_entered": string,\n' \
                   '  "date_last_changed": string,\n' \
                   '  "from_scraper": string,\n' \
                   '  "google_civic_candidate_name": string,\n' \
                   '  "google_civic_election_id": string,\n' \
                   '  "more_info_url": string,\n' \
                   '  "organization_certified": string,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "politician_we_vote_id": string,\n' \
                   '  "public_figure_we_vote_id": string,\n' \
                   '  "speaker_display_name": string,\n' \
                   '  "speaker_image_url_https": string,\n' \
                   '  "speaker_twitter_handle": string,\n' \
                   '  "stance": string,\n' \
                   '  "state_code": string,\n' \
                   '  "statement_text": string,\n' \
                   '  "statement_html": string,\n' \
                   '  "tweet_source_id": string,\n' \
                   '  "twitter_user_entered_position": string,\n' \
                   '  "volunteer_certified": string,\n' \
                   '  "vote_smart_rating": string,\n' \
                   '  "vote_smart_rating_id": string,\n' \
                   '  "vote_smart_rating_name": string,\n' \
                   '  "vote_smart_time_span": string,\n' \
                   '  "voter_entering_position": string,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'positionsSyncOut',
        'api_slug': 'positionsSyncOut/?format=json',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:positionsSyncOutView',
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
