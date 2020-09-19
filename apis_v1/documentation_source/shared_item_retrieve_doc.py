# apis_v1/documentation_source/shared_item_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def shared_item_retrieve_doc_template_values(url_root):
    """
    Show documentation about sharedItemRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'shared_item_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The code coming from the URL that we need to look up the final destination.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'shared_item_clicked',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Is this retrieve because of this voter clicking?',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'VALID_VOTER_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_id was not found.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "destination_full_url": string,\n' \
                   '  "shared_item_code_no_opinions": string,\n' \
                   '  "shared_item_code_all_opinions": string,\n' \
                   '  "url_with_shared_item_code_no_opinions": string,\n' \
                   '  "url_with_shared_item_code_all_opinions": string,\n' \
                   '  "is_ballot_share": boolean,\n' \
                   '  "is_candidate_share": boolean,\n' \
                   '  "is_measure_share": boolean,\n' \
                   '  "is_office_share": boolean,\n' \
                   '  "is_organization_share": boolean,\n' \
                   '  "is_ready_share": boolean,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "site_owner_organization_we_vote_id": string,\n' \
                   '  "shared_by_voter_we_vote_id": string,\n' \
                   '  "shared_by_organization_type": string,\n' \
                   '  "shared_by_organization_we_vote_id": string,\n' \
                   '  "candidate_we_vote_id": string,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "date_first_shared": datetime,\n' \
                   '}'

    template_values = {
        'api_name': 'sharedItemRetrieve',
        'api_slug': 'sharedItemRetrieve',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:sharedItemRetrieveView',
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
