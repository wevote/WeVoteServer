# apis_v1/documentation_source/shared_item_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def shared_item_save_doc_template_values(url_root):
    """
    Show documentation about sharedItemSave
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
            'name':         'destination_full_url',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The full URL with the final destination.',
        },
        {
            'name':         'other_voter_email_address_text',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The email address of the person you are sharing with. '
                            'Required if is_remind_contact_share.',
        },
        {
            'name':         'shared_by_voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The voter_we_vote_id of the person who is sharing.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'ballot_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we_vote_id for the ballot item being shared.',
        },
        {
            'name':         'google_civic_election_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The unique identifier for a particular election.',
        },
        {
            'name':         'is_ballot_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The kind of destination shared: Ballot page',
        },
        {
            'name':         'is_candidate_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The kind of destination shared: Candidate page',
        },
        {
            'name':         'is_measure_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The kind of destination shared: Measure page',
        },
        {
            'name':         'is_office_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The kind of destination shared: Office page',
        },
        {
            'name':         'is_organization_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The kind of destination shared: Voter Guide page',
        },
        {
            'name':         'is_ready_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The kind of destination shared: Ready page',
        },
        {
            'name':         'is_remind_contact_share',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Send remind a contact to vote email',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The organization the voter wants to share.',
        },
        {
            'name':         'other_voter_email_address_text',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The text of the email address of the friend the current voter is sharing with.',
        },
        {
            'name':         'other_voter_display_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The full display name of the friend the current voter is sharing with.',
        },
        {
            'name':         'other_voter_first_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The first name (given name) of the friend the current voter is sharing with.',
        },
        {
            'name':         'other_voter_last_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The last name (family name) of the friend the current voter is sharing with.',
        },
        {
            'name':         'other_voter_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The voter_we_vote_id of the friend the current voter is sharing with (if we have it).',
        },
        {
            'name':         'shared_message',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The message to send to the friend the current voter is sharing with.',
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
                   '  "candidate_we_vote_id": string,\n' \
                   '  "date_first_shared": datetime,\n' \
                   '  "destination_full_url": string,\n' \
                   '  "google_civic_election_id": integer,\n' \
                   '  "is_ballot_share": boolean,\n' \
                   '  "is_candidate_share": boolean,\n' \
                   '  "is_measure_share": boolean,\n' \
                   '  "is_office_share": boolean,\n' \
                   '  "is_organization_share": boolean,\n' \
                   '  "is_ready_share": boolean,\n' \
                   '  "is_remind_contact_share": boolean,\n' \
                   '  "measure_we_vote_id": string,\n' \
                   '  "office_we_vote_id": string,\n' \
                   '  "other_voter_display_name": string,\n' \
                   '  "other_voter_email_address_text": string,\n' \
                   '  "other_voter_first_name": string,\n' \
                   '  "other_voter_last_name": string,\n' \
                   '  "other_voter_we_vote_id": string,\n' \
                   '  "shared_by_display_name": string,\n' \
                   '  "shared_by_first_name": string,\n' \
                   '  "shared_by_last_name": string,\n' \
                   '  "shared_by_email_address_text": string,\n' \
                   '  "shared_by_organization_type": string,\n' \
                   '  "shared_by_organization_we_vote_id": string,\n' \
                   '  "shared_by_voter_we_vote_id": string,\n' \
                   '  "shared_by_we_vote_hosted_profile_image_url_large": string,\n' \
                   '  "shared_by_we_vote_hosted_profile_image_url_medium": string,\n' \
                   '  "shared_by_we_vote_hosted_profile_image_url_tiny": string,\n' \
                   '  "shared_item_code_no_opinions": string,\n' \
                   '  "shared_item_code_all_opinions": string,\n' \
                   '  "site_owner_organization_we_vote_id": string,\n' \
                   '  "url_with_shared_item_code_no_opinions": string,\n' \
                   '  "url_with_shared_item_code_all_opinions": string,\n' \
                   '}'

    template_values = {
        'api_name': 'sharedItemSave',
        'api_slug': 'sharedItemSave',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:sharedItemSaveView',
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
