# apis_v1/documentation_source/offices_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def offices_sync_out_doc_template_values(url_root):
    """
    Show documentation about officesSyncOut
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
            'description':  'Limit the offices entries retrieved to those in a particular state.',
        },
    ]

    potential_status_codes_list = [
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "we_vote_id": string,\n' \
                   '  "office_name": string,\n' \
                   '  "ballotpedia_id": string,\n' \
                   '  "contest_level0": string,\n' \
                   '  "contest_level1": string,\n' \
                   '  "contest_level2": string,\n' \
                   '  "district_id": string,\n' \
                   '  "district_name": string,\n' \
                   '  "district_scope": string,\n' \
                   '  "electorate_specifications": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "maplight_id": integer,\n' \
                   '  "number_elected": integer,\n' \
                   '  "number_voting_for": integer,\n' \
                   '  "ocd_division_id": integer,\n' \
                   '  "primary_party": string,\n' \
                   '  "special": string,\n' \
                   '  "state_code": string,\n' \
                   '  "wikipedia_id": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'officesSyncOut',
        'api_slug': 'officesSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:officesSyncOutView',
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
