# apis_v1/documentation_source/organization_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_save_doc_template_values(url_root):
    """
    Show documentation about organizationSave
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
                            'organization_id, organization_we_vote_id, facebook_id, '
                            'organization_website or organization_twitter_handle)',
        },
        {
            'name':         'organization_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The unique identifier for this organization across all networks. '
                            '(One of these is required to update data: '
                            'organization_id, organization_we_vote_id, facebook_id, '
                            'organization_website or organization_twitter_handle)',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'chosen_domain_string',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the value of client\'s customized web address. Ex/ vote.organization.org'
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'chosen_google_analytics_tracking_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the value of client\'s Google Analytics code. '
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'chosen_html_verification_string',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the value of client\'s verification string, needed by Google. '
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'chosen_hide_we_vote_logo',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'The client wants to hide the default logo. '
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'chosen_prevent_sharing_opinions',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'If you are a 501c3, this lets you maintain compliance by turning off the ability '
                            'for voters to share their opinions out to social media, from your site.',
        },
        {
            'name':         'chosen_social_share_description',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the value of client\'s customized description. '
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'chosen_subdomain_string',
            'value':        'string',  # boolean, integer, long, string
            'description':  'This is the value of client\'s customized subdomain. Ex/ cats.WeVote.US '
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'chosen_subscription_plan',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'This is an integer value specifying the subscription plan the client has chosen. '
                            'It is changed by a client in Settings section.',
        },
        {
            'name':         'facebook_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Facebook identifier of the voter who wants to share a voter guide. '
                            '(NOTE: In order to create a new organization, you may pass in '
                            'either organization_twitter_handle OR facebook_id)',
        },
        {
            'name':         'facebook_email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Personal email returned upon Facebook sign in.',
        },
        {
            'name':         'facebook_profile_image_url_https',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Personal photo returned upon Facebook sign in.',
        },
        {
            'name':         'organization_description',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The description of the organization that is displayed.',
        },
        {
            'name':         'organization_email',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Contact email of the organization.',
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
        {
            'name':         'organization_name',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Name of the organization that is displayed.',
        },
        {
            'name':         'organization_twitter_handle',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Twitter handle of the organization. '
                            '(NOTE: In order to create a new organization, you may pass in '
                            'either organization_twitter_handle OR facebook_id)',
        },
        {
            'name':         'organization_type',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The type of the organization: '
                            'C = Corporation, G = Group of people (not an individual), but org status unknown, '
                            'I = One person, C3 = 501(c)(3) Nonprofit, C4 = 501(c)(3) Nonprofit, '
                            'NP = Nonprofit other than C3 or C4, NW = News organization, '
                            'P = Political Action Committee, C = Company,  PF = Politician, U = Other',
        },
        {
            'name':         'organization_website',
            'value':        'string',  # boolean, integer, long, string
            'description':  'Website of the organization.',
        },
        {
            'name':         'refresh_from_twitter',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Augment the data passed in with information from Twitter. Do not replace data passed in '
                            'as a variable with the data from Twitter, but if a variable is not passed in via the API, '
                            'then fill in that variable with data from Twitter. One use-case is to save an '
                            'organization with only a Twitter handle, and fill in the rest of the data with a call '
                            'to Twitter.',
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
                   '  "facebook_id": integer,\n' \
                   '  "new_organization_created": boolean,\n' \
                   '  "organization_email": string,\n' \
                   '  "organization_facebook": string,\n' \
                   '  "organization_instagram_handle": string,\n' \
                   '  "organization_id": integer,\n' \
                   '  "organization_description": string,\n' \
                   '  "organization_name": string,\n' \
                   '  "organization_photo_url": string,\n' \
                   '  "organization_twitter_handle": string,\n' \
                   '  "organization_type": string,\n' \
                   '  "organization_website": string,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "refresh_from_twitter": boolean,\n' \
                   '  "twitter_followers_count": integer,\n' \
                   '  "twitter_description": string,\n' \
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
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
