# apis_v1/documentation_source/candidate_to_office_link_sync_out_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def candidate_to_office_link_sync_out_doc_template_values(url_root):
    """
    Show documentation about candidateToOfficeLinkSyncOut
    """
    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Limit the candidate_to_office_link entries retrieved '
                            'to those for this google_civic_election_id.',
        },
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Limit the candidate_to_office_link entries retrieved to those in a particular state.',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "contest_office_we_vote_id": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "state_code": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'candidateToOfficeLinkSyncOut',
        'api_slug': 'candidateToOfficeLinkSyncOut',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:candidateToOfficeLinkSyncOutView',
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
