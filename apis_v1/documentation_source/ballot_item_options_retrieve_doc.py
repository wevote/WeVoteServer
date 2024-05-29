# apis_v1/documentation_source/ballot_item_options_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def ballot_item_options_retrieve_doc_template_values(url_root):
    """
    Show documentation about ballotItemOptionsRetrieve
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
            'name': 'google_civic_election_id',
            'value': 'integer',  # boolean, integer, long, string
            'description': 'The unique identifier for a particular election. If NOT provided, we instead use the '
                           'google_civic_election_id for the person who is signed in.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'search_string',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Search words to use to find the candidate or measure for voter guide.'
        },
        {
            'name':         'state_code',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The us state we want ballot item options for. '
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'CANDIDATES_RETRIEVED OFFICES_RETRIEVED MEASURES_RETRIEVED',
            'description':  'Ballot items were found.',
        },
        {
            'code':         'NO_CANDIDATES_RETRIEVED NO_OFFICES_RETRIEVED NO_MEASURES_RETRIEVED',
            'description':  'Candidates, offices or measures were not able to be retrieved.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "search_string": string,\n' \
                   '  "ballot_item_list": candidate dict\n' \
                   '   [\n' \
                   '      "ballot_item_display_name": string,\n' \
                   '      "ballotpedia_candidate_id": integer,\n' \
                   '      "ballotpedia_candidate_url": string,\n' \
                   '      "ballotpedia_person_id": integer,\n' \
                   '      "candidate_contact_form_url": string, \n' \
                   '      "candidate_email": string,\n' \
                   '      "candidate_name": string,\n' \
                   '      "candidate_phone": string,\n' \
                   '      "candidate_photo_url_large": string,\n' \
                   '      "candidate_photo_url_medium": string,\n' \
                   '      "candidate_photo_url_tiny": string,\n' \
                   '      "candidate_url": string,\n' \
                   '      "candidate_we_vote_id": string,\n' \
                   '      "candidate_website": string,\n' \
                   '      "contest_office_id": integer,\n' \
                   '      "contest_office_we_vote_id": string,\n' \
                   '      "contest_office_name": string,\n' \
                   '      "google_civic_election_id": integer,\n' \
                   '      "id": integer,\n' \
                   '      "kind_of_ballot_item": string (CANDIDATE),\n' \
                   '      "maplight_id": integer,\n' \
                   '      "ocd_division_id": string,\n' \
                   '      "order_on_ballot": integer,\n' \
                   '      "party": string,\n' \
                   '      "politician_id": integer,\n' \
                   '      "politician_we_vote_id": string,\n' \
                   '      "state_code": string,\n' \
                   '      "facebook_url": string,\n' \
                   '      "twitter_url": string,\n' \
                   '      "twitter_handle": string,\n' \
                   '      "google_plus_url": string,\n' \
                   '      "youtube_url": string,\n' \
                   '      "we_vote_id": string,\n' \
                   '      "wikipedia_url": string,\n' \
 \
                   '   ],\n' \
                   '  "ballot_item_list": measure dict\n' \
                   '   [\n' \
                   '      "ballot_item_display_name": string,\n' \
                   '      "google_civic_election_id": integer,\n' \
                   '      "id": integer,\n' \
                   '      "kind_of_ballot_item": string (MEASURE),\n' \
                   '      "measure_subtitle": string,\n' \
                   '      "measure_text": string,\n' \
                   '      "measure_url": string,\n' \
                   '      "measure_we_vote_id": string,\n' \
                   '      "no_vote_description": string,\n' \
                   '      "state_code": string,\n' \
                   '      "yes_vote_description": string,\n' \
                   '   ],\n' \
                   '}'

    template_values = {
        'api_name': 'ballotItemOptionsRetrieve',
        'api_slug': 'ballotItemOptionsRetrieve',
        'api_introduction':
            "Returns measures and candidates based on search terms, so we can help "
            "volunteers or staff find offices, candidates or measures when they are building out organizational "
            "voter guides. This information is not organized in a "
            "hierarchy, but is instead provided in a simple list for browser-side "
            "quick search features.",
        'try_now_link': 'apis_v1:ballotItemOptionsRetrieveView',
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
