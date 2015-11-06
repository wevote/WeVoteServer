# apis_v1/documentation_source/organization_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# This is a template (starting point) for creating documentation for individual APIs


def organization_save_doc_template_values(url_root):
    """
    Show documentation about organizationSave
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
            'name':         'organization_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The internal database id for this organization. (One of these is required: '
                            'organization_id, organization_we_vote_id, '
                            'organization_website or organization_twitter_handle)',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this organization across all networks.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'organization_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Name of the organization that is displayed.',
        },
        {
            'name':         'organization_email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Contact email of the organization.',
        },
        {
            'name':         'organization_website',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Website of the organization.',
        },
        {
            'name':         'organization_twitter_handle',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Twitter handle of the organization.',
        },
        {
            'name':         'organization_facebook',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Facebook page of the organization.',
        },
        {
            'name':         'organization_image',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Logo of the organization that is displayed.',
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
            'code':         'ORGANIZATION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING',
            'description':  'Cannot proceed. Missing sufficient unique identifiers for either save new or update.',
        },
        {
            'code':         'NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING',
            'description':  'Cannot proceed. This is a new entry and there are not sufficient variables.',
        },
        {
            'code':         'FOUND_WITH_WEBSITE SAVED',
            'description':  'An organization with matching website was found. Record updated.',
        },
    ]

    try_now_link_variables_dict = {
        # 'organization_we_vote_id': 'wv85org1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "organization_id": integer,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "new_organization_created": boolean,\n' \
                   '  "organization_name": string,\n' \
                   '  "organization_email": string,\n' \
                   '  "organization_website": string,\n' \
                   '  "organization_twitter_handle": string,\n' \
                   '}'

    template_values = {
        'api_name': 'organizationSave',
        'api_slug': 'organizationSave',
        'api_introduction':
            "Save a new organization or update an existing organization. Note that passing in a blank value does not "
            "delete an existing value. We may want to come up with a variable we pass if we want to clear a value.",
        'try_now_link': 'apis_v1:organizationSaveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'POST',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
