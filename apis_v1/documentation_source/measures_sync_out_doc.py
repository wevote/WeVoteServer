# apis_v1/documentation_source/measures_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def measures_sync_out_doc_template_values(url_root):
    """
    Show documentation about measuresSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit the measures retrieved to those for this google_civic_election_id.',
        },
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the measures entries retrieved to those in a particular state.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "maplight_id": integer,\n' \
                   '  "vote_smart_id": integer,\n' \
                   '  "ballotpedia_page_title": string,\n' \
                   '  "ballotpedia_photo_url": string,\n' \
                   '  "district_id": string,\n' \
                   '  "district_name": string,\n' \
                   '  "district_scope": string,\n' \
                   '  "google_civic_election_id": string,\n' \
                   '  "measure_title": string,\n' \
                   '  "measure_subtitle": string,\n' \
                   '  "measure_text": string,\n' \
                   '  "measure_url": string,\n' \
                   '  "ocd_division_id": string,\n' \
                   '  "primary_party": string,\n' \
                   '  "state_code": string,\n' \
                   '  "wikipedia_page_id": string,\n' \
                   '  "wikipedia_page_title": string,\n' \
                   '  "wikipedia_photo_url": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'measuresSyncOut',
        'api_slug': 'measuresSyncOut/?format=json',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:measuresSyncOutView',
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
