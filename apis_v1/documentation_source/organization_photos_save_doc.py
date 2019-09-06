# apis_v1/documentation_source/organization_photos_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_photos_save_doc_template_values(url_root):
    """
    Show documentation about organizationPhotosSave
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
            'name':         'organization_id',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'The internal database id for this organization. '
                            '(One of these is required to update data: '
                            'organization_id, organization_we_vote_id or organization_twitter_handle)',
        },
        {
            'name':         'organization_twitter_handle',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this organization across all networks. '
                            '(One of these is required to update data: '
                            'organization_id, organization_we_vote_id, organization_twitter_handle)',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this organization across all networks. '
                            '(One of these is required to update data: '
                            'organization_id, organization_we_vote_id, organization_twitter_handle)',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'chosen_favicon_from_file_reader',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the output from JavaScript\'s FileReader for an uploaded favicon image.',
        },
        {
            'name':         'chosen_logo_from_file_reader',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the output from JavaScript\'s FileReader for an uploaded logo.',
        },
        {
            'name':         'chosen_social_share_master_image_from_file_reader',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the output from JavaScript\'s FileReader for an uploaded social share image.',
        },
        {
            'name':         'delete_chosen_favicon',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Tell the API server to delete the current favicon for this organization.',
        },
        {
            'name':         'delete_chosen_logo',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Tell the API server to delete the current logo for this organization.',
        },
        {
            'name':         'delete_chosen_social_share_master_image',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Tell the API server to delete the current social share master image '
                            'for this organization.',
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
                   '  "organization_id": integer,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '}'

    template_values = {
        'api_name': 'organizationPhotosSave',
        'api_slug': 'organizationPhotosSave',
        'api_introduction':
            "Save uploaded photos for an existing organization.",
        'try_now_link': 'apis_v1:organizationPhotosSaveView',
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
