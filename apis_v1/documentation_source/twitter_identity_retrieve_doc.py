# apis_v1/documentation_source/twitter_identity_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def twitter_identity_retrieve_doc_template_values(url_root):
    """
    Show documentation about twitterIdentityRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'twitter_handle',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Find the kind of owner and unique id of this twitter handle.',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'twitter_handle': 'RepBarbaraLee',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "twitter_handle": string,\n' \
                   '  "owner_found": boolean,\n' \
                   '  "kind_of_owner": string, (POLITICIAN, CANDIDATE, ORGANIZATION)\n' \
                   '  "owner_we_vote_id": string,\n' \
                   '  "owner_id": integer,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'twitterIdentityRetrieve',
        'api_slug': 'twitterIdentityRetrieve',
        'api_introduction':
            "Find the kind of owner and unique id of this twitter handle, whether it be a candidate, organization, or "
            "individual voter. We use this to take an incoming URI like "
            "https://wevote.guide/RepBarbaraLee and return the owner of \'RepBarbaraLee\'.",
        'try_now_link': 'apis_v1:twitterIdentityRetrieveView',
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
