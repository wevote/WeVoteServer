# apis_v1/documentation_source/position_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def apple_sign_in_save_doc_view_template_values(url_root):
    """
    Show documentation about appleSignInSave
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
            'name':         'email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The email address used to establish an Apple ID, can be an alias (aliases complicate '
                            'matching)',
        },
        {
            'name': 'first_name',  # 'givenName' in the Apple API response
            'value': 'string',     # boolean, integer, long, string
            'description': 'The first name (given name) of the Apple ID user.',
        },
        {
            'name': 'middle_name',  # 'middleName' in the Apple API response
            'value': 'string',      # boolean, integer, long, string
            'description': 'The middle name of the Apple ID user.  This field can be an empty string',
        },
        {
            'name': 'last_name',    # 'familyName' in the Apple API response
            'value': 'string',      # boolean, integer, long, string
            'description': 'The last name (family name) of the Apple ID user.',
        },
        {
            'name': 'user_code',    # 'user' in the Apple API response
            'value': 'string',      # boolean, integer, long, string
            'description': 'The hash that Sign in with Apple returns for a successful sign in for a given '
                           'Apple ID',
        },

    ]
    optional_query_parameter_list = [
        {
            'name': 'apple_platform',       # apple calls it platform
            'value': 'string',              # boolean, integer, long, string
            'description': 'iOS, or iPadOS',
        },
        {
            'name': 'apple_os_version',     # apple calls it version
            'value': 'string',              # boolean, integer, long, string
            'description': '13.5 for example',
        },
        {
            'name': 'apple_model',          # apple calls it model
            'value': 'string',              # boolean, integer, long, string
            'description': '"iPhone12,3" is an "iPhone 11 Pro" for example',
        },
        {
            'name': 'voter_we_vote_id',
            'value': 'string',              # boolean, integer, long, string
            'description': 'The unique identifier for the voter. It would be unusual to know this in advance.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'APPLE_USER_ID_RECORD_CREATED_OR_UPDATED',
            'description':  'Success.  Mormal operation.',
        },
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'Cannot proceed. A valid voter_device_id parameter was not included.',
        },
        {
            'code':         'ERROR_APPLE_USER_NOT_CREATED_OR_NOT_UPDATED',
            'description':  'Cannot proceed. The record was not created or updated, due to a bug or a system issue.',
        },
    ]

    try_now_link_variables_dict = {
        'organization_we_vote_id': 'wv85org1',
        'ballot_item_display_name': 'Test Ballot Item Label',
        'candidate_we_vote_id': 'wv01cand1755',
        'stance': 'SUPPORT',
        'statement_text': 'This is what I believe...',
        'google_civic_election_id': '4162',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '}'

    template_values = {
        'api_name': 'appleSignInSave',
        'api_slug': 'appleSignInSave',
        'api_introduction':
            "Save the Apple 'user' code, returned by the <em>Sign In With Apple</em> api response for a given Apple ID "
            " -- the Apple ID is phone owner's email address and password used to sign into iCloud.<br>"
            "WeVote code never 'sees' the Apple ID password, only the 'user' code returned by the API and the user's "
            "email address (which unfortunately can be an Apple aliased email address).",
        'try_now_link': 'apis_v1:appleSignInSaveView',
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
