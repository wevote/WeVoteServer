# apis_v1/documentation_source/candidates_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def candidates_sync_out_doc_template_values(url_root):
    """
    Show documentation about candidatesSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit the candidates retrieved to those for this google_civic_election_id.',
        },
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the candidates entries retrieved to those in a particular state.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "ballot_guide_official_statement": string,\n' \
                   '  "ballotpedia_candidate_id": integer,\n' \
                   '  "ballotpedia_candidate_name": string,\n' \
                   '  "ballotpedia_candidate_summary": string,\n' \
                   '  "ballotpedia_candidate_url": string,\n' \
                   '  "ballotpedia_election_id": integer,\n' \
                   '  "ballotpedia_image_id": integer,\n' \
                   '  "ballotpedia_office_id": integer,\n' \
                   '  "ballotpedia_page_title": string,\n' \
                   '  "ballotpedia_person_id": integer,\n' \
                   '  "ballotpedia_photo_url": string,\n' \
                   '  "ballotpedia_race_id": integer,\n' \
                   '  "birth_day_text": string,\n' \
                   '  "candidate_email": string,\n' \
                   '  "candidate_gender": string,\n' \
                   '  "candidate_is_incumbent": boolean,\n' \
                   '  "candidate_is_top_ticket": boolean,\n' \
                   '  "candidate_name": string,\n' \
                   '  "candidate_participation_status": string,\n' \
                   '  "candidate_phone": string,\n' \
                   '  "candidate_twitter_handle": string,\n' \
                   '  "candidate_url": string,\n' \
                   '  "contest_office_we_vote_id": string,\n' \
                   '  "contest_office_name": string,\n' \
                   '  "crowdpac_candidate_id": integer,\n' \
                   '  "facebook_url": string,\n' \
                   '  "google_civic_candidate_name": string,\n' \
                   '  "google_civic_candidate_name2": string,\n' \
                   '  "google_civic_candidate_name3": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "google_plus_url": string,\n' \
                   '  "maplight_id": integer,\n' \
                   '  "ocd_division_id": string,\n' \
                   '  "order_on_ballot": string,\n' \
                   '  "party": string,\n' \
                   '  "photo_url": string,\n' \
                   '  "photo_url_from_maplight": string,\n' \
                   '  "photo_url_from_vote_smart": string,\n' \
                   '  "politician_we_vote_id": string,\n' \
                   '  "state_code": string,\n' \
                   '  "twitter_url": string,\n' \
                   '  "twitter_user_id": string,\n' \
                   '  "twitter_name": string,\n' \
                   '  "twitter_location": string,\n' \
                   '  "twitter_followers_count": integer,\n' \
                   '  "twitter_profile_image_url_https": string,\n' \
                   '  "twitter_description": string,\n' \
                   '  "vote_smart_id": integer,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "wikipedia_page_id": string,\n' \
                   '  "wikipedia_page_title": string,\n' \
                   '  "wikipedia_photo_url": string,\n' \
                   '  "youtube_url": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'candidatesSyncOut',
        'api_slug': 'candidatesSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:candidatesSyncOutView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
