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
            'description':  'The url where a voter guide can be found. '
                            'Either this url or the voter_guide_possibility_id is required.',
        },
        {
            'name':         'voter_guide_possibility_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'Either this id or a url_to_scan is required.',
        },
        {
            'name':         'limit_to_this_year',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Limit results to possibilities created this year, defaults to True',
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
        'url_to_scan':
            'https://projects.sfchronicle.com/2018/voter-guide/endorsements-list/',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "candidate": dict\n' \
                   '   {\n' \
                   '     "candidate_we_vote_id": string,\n' \
                   '     "candidate_name": string,\n' \
                   '     "candidate_website": string,\n' \
                   '     "candidate_twitter_handle": string,\n' \
                   '     "candidate_email": string,\n' \
                   '     "candidate_facebook": string,\n' \
                   '     "we_vote_hosted_profile_image_url_medium": string,\n'\
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '  "candidates_missing_from_we_vote": boolean,\n' \
                   '  "cannot_find_endorsements": boolean,\n' \
                   '  "capture_detailed_comments": boolean,\n' \
                   '  "contributor_comments": string,\n' \
                   '  "contributor_email": string,\n' \
                   '  "done_needs_verification": string,\n' \
                   '  "done_verified": string,\n' \
                   '  "from_prior_election": boolean,\n' \
                   '  "hide_from_active_review": boolean,\n' \
                   '  "ignore_this_source": boolean,\n' \
                   '  "internal_notes": string,\n' \
                   '  "organization": dict\n' \
                   '   {\n' \
                   '     "organization_we_vote_id": string,\n' \
                   '     "organization_name": string,\n' \
                   '     "organization_website": string,\n' \
                   '     "organization_twitter_handle": string,\n' \
                   '     "organization_email": string,\n' \
                   '     "organization_facebook": string,\n' \
                   '     "we_vote_hosted_profile_image_url_medium": string,\n'\
                   '     "we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '   },\n' \
                   '  "possible_candidate_name": string,\n' \
                   '  "possible_candidate_twitter_handle": string,\n' \
                   '  "possible_owner_of_website_candidates_list": list,\n' \
                   '   [\n' \
                   '     {\n' \
                   '       "candidate_we_vote_id": string,\n' \
                   '       "candidate_name": string,\n' \
                   '       "candidate_website": string,\n' \
                   '       "candidate_twitter_handle": string,\n' \
                   '       "candidate_email": string,\n' \
                   '       "candidate_facebook": string,\n' \
                   '       "candidate_photo_url_medium": string,\n'\
                   '       "candidate_photo_url_tiny": string,\n' \
                   '     },\n' \
                   '   ]\n' \
                   '  "possible_organization_name": string,\n' \
                   '  "possible_organization_twitter_handle": string,\n' \
                   '  "possible_owner_of_website_organizations_list": list,\n' \
                   '   [\n' \
                   '     {\n' \
                   '       "organization_id": integer,\n' \
                   '       "organization_we_vote_id": string,\n' \
                   '       "organization_name": string,\n' \
                   '       "organization_website": string,\n' \
                   '       "organization_twitter_handle": string,\n' \
                   '       "organization_email": string,\n' \
                   '       "organization_facebook": string,\n' \
                   '       "organization_photo_url_medium": string,\n'\
                   '       "organization_photo_url_tiny": string,\n' \
                   '     },\n' \
                   '   ]\n' \
                   '  "limit_to_this_state_code": string,\n' \
                   '  "url_to_scan": string,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_guide_possibility_edit": string,\n' \
                   '  "voter_guide_possibility_id": integer,\n' \
                   '  "voter_guide_possibility_type": string,\n' \
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
