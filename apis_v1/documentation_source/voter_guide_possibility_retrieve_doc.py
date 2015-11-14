# apis_v1/documentation_source/voter_guide_possibility_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guide_possibility_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidePossibilityRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string (from cookie)',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'voter_guide_possibility_url',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url where a voter guide can be found.',
        },
    ]
    optional_query_parameter_list = [
        # {
        #     'name':         '',
        #     'value':        '',  # boolean, integer, long, string
        #     'description':  '',
        # },
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
        {
            'code':         'VOTER_GUIDE_POSSIBILITY_NOT_FOUND',
            'description':  'A voter guide possibility was not found at that URL.',
        },
        {
            'code':         'VOTER_GUIDE_POSSIBILITY_FOUND_WITH_URL',
            'description':  'A voter guide possibility entry was found.',
        },
        # {
        #     'code':         '',
        #     'description':  '',
        # },
    ]

    try_now_link_variables_dict = {
        'voter_guide_possibility_url':
            'http://ww2.kqed.org/news/2015/10/25/guide-to-san-francisco-2015-ballot-propositions-a-to-k',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_guide_possibility_url": string,\n' \
                   '  "voter_guide_possibility_id": integer,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "public_figure_we_vote_id": string,\n' \
                   '  "owner_we_vote_id": string,\n' \
                   '}'

    template_values = {
        'api_name': 'voterGuidePossibilityRetrieve',
        'api_slug': 'voterGuidePossibilityRetrieve',
        'api_introduction':
            "Has a particular web page URL been captured as a possible voter guide?",
        'try_now_link': 'apis_v1:voterGuidePossibilityRetrieveView',
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
