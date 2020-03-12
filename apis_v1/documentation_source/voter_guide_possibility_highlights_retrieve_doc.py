# apis_v1/documentation_source/voter_guide_possibility_highlights_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_guide_possibility_highlights_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterGuidePossibilityHighlightsRetrieve
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
    ]
    optional_query_parameter_list = [
        {
            'name':         'url_to_scan',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url of the list of endorsements that the voter is viewing.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The Google civic election ID. Provide a value, only if you want data for a prior election.',
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
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "url_to_scan": string,\n' \
                   '  "highlight_list": list [\n' \
                   '    {\n' \
                   '      "name": string,\n' \
                   '      "we_vote_id": string,\n' \
                   '      "display": string, (\'STORED\', \'DELETED\', \'POSSIBILITY\', or \'DEFAULT\')\n' \
                   '      "stance": string, (\'SUPPORT\', \'OPPOSED\', or \'INFO_ONLY\')\n'\
                   '      "prior": integer, (\'1\' if from a prior election)\n'\
                   '    }\n' \
                   '  ],\n' \
                   '  "never_highlight_on": list [\n' \
                   '     "*.wevote.us",\n' \
                   '     "api.wevoteusa.org",\n' \
                   '     "localhost"\n' \
                   '  ]\n' \
                   '}'

    template_values = {
        'api_name': 'voterGuidePossibilityHighlightsRetrieve',
        'api_slug': 'voterGuidePossibilityHighlightsRetrieve',
        'api_introduction':
            "Retrieve all of the candidates that might be highlighted on an endorsement guide. "
            "DEFAULT = there is no entry in this organization's Voter Guide Possibility yet.",
        'try_now_link': 'apis_v1:voterGuidePossibilityHighlightsRetrieveView',
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
