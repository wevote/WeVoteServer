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
        {
            'name':         'url_to_scan',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url of the list of endorsements that the voter is viewing.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The Google civic election ID. Provide a value, only if you want data for a prior election.',
        },
        {
            'name':         'pdf_url',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The url of the list of endorsements, if the endorsement was originally on a pdf.',
        },
        {
            'name':         'visible_text_to_scan',
            'value':        'text',  # boolean, integer, long, string
            'description':  'Visible text from the page we are scanning. Only accepted in POST.',
        },
        {
            'name':         'use_vertex_to_scan_url_if_no_visible_text_provided',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'IF visible_text_to_scan is provided using POST, we always use Vertex AI to identify the '
                            'likely human names within the text provided. '
                            'If this variable is set to True (which is the default), '
                            'use Vertex to scan the url_to_scan (i.e., webpage) IFF a value '
                            'is NOT provided in visible_text_to_scan. Note that if visible_text_to_scan has a value, '
                            'we do NOT use Vertex AI to scan the url_to_scan. '
                            'In all cases, Vertex AI adds about 2-3 seconds to the response time.',
            'default':      'true',       # default 'checked' for a boolean radio input
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
                   '  "pdf_url": string,\n' \
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
            "WeVote's Political Data team reviews endorsement websites. We "
            "scan an organization's webpage that contains political endorsements. (Ex/ The National Bird Conservatory "
            "endorses Donald Duck for County Tax Collector) WeVote finds the owner of the web page, "
            "then finds all of the candidates listed on the page. We store in temporary tables, the SUPPORT and OPPOSE "
            "endorsements found on this page, and let a Political Data Manager review these endorsements as they are "
            "captured. Once the Political Data Manager has reviewed these endorsements, they can be saved to our "
            "publicly available list of endorsements. This tool helps our team provide quality assurance as we "
            "collect the data. This voterGuidePossibilityHighlightsRetrieve API connects WeVote's Chrome Extension to "
            "the 'Endorsement Websites' admin tools on WeVoteServer, and returns "
            "what candidates have been identified, and whether the endorsing organization SUPPORTs, OPPOSEs, "
            "or shares INFO_ONLY about the candidate. This API also returns names found on the page who might be "
            "politicians, so the Political Data Manager can more easily capture endorsements.",
        'try_now_link': 'apis_v1:voterGuidePossibilityHighlightsRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET or POST',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
