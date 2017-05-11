# apis_v1/documentation_source/voter_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_retrieve_doc_template_values(url_root):
    """
    Show documentation about voterRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server. '
                            'If not provided, a new voter_device_id (and voter entry) '
                            'will be generated, and the voter_device_id will be returned.',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_DEVICE_ID',
            'description':  'There is no voter_id attached to that voter_device_id',
        },
        {
            'code':         'VOTER_ID_COULD_NOT_BE_RETRIEVED',
            'description':  'Unable to retrieve voter_id, although voter_id was found linked to voter_device_id',
        },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string (description of what happened),\n' \
                   '  "success": boolean (True as long as no db errors),\n' \
                   '  "voter_device_id": string (88 characters long),\n' \
                   '  "voter_created": boolean,\n' \
                   '  "voter_found": boolean,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "facebook_id": integer,\n' \
                   '  "email": string,\n' \
                   '  "facebook_email": string,\n' \
                   '  "facebook_profile_image_url_https": string,\n' \
                   '  "full_name": string,\n' \
                   '  "first_name": string,\n' \
                   '  "last_name": string,\n' \
                   '  "twitter_screen_name": string,\n' \
                   '  "is_signed_in": boolean,\n' \
                   '  "is_admin": boolean,\n' \
                   '  "is_verified_volunteer": boolean,\n' \
                   '  "signed_in_facebook": boolean,\n' \
                   '  "signed_in_google": boolean,\n' \
                   '  "signed_in_twitter": boolean,\n' \
                   '  "signed_in_with_email": boolean,\n' \
                   '  "has_valid_email": boolean,\n' \
                   '  "has_data_to_preserve": boolean,\n' \
                   '  "has_email_with_verified_ownership": boolean,\n' \
                   '  "linked_organization_we_vote_id": string,\n' \
                   '  "voter_photo_url_large": string,\n' \
                   '  "voter_photo_url_medium": string,\n' \
                   '  "voter_photo_url_tiny": string,\n' \
                   '  "voter_donation_journal_list": list [ (List of donation journal entries for charges and subscriptions),\n' \
                   '    "created": datetime, (Timestamp of the charge creation)\n' \
                   '    "amount" : integer, (Amount donatated, or subscribed to, in cents)\n' \
                   '    "currency" : integer, (International 3 letter currency code, like \'usd\'\n' \
                   '    "record_enum" : string, (One of {PAYMENT_FROM_UI, PAYMENT_AUTO_SUBS, SUBS_SETUP_AND_INITIAL})\n' \
                   '    "brand" : string, (Credit card brand, like Visa or MasterCard)\n' \
                   '    "exp_month" : string, (Credit card expiration month {1...12})\n' \
                   '    "exp_year" : string, (Credit card expiration year, like 2017)\n' \
                   '    "last4" : string, (Last 4 digits of the credit card)\n' \
                   '    "stripe_status" : string, (The status stripe returned for the transaction)\n' \
                   '    "charge_id" : string, (Stripe\'s charge id)\n' \
                   '    "subs_id" : string, (Stripe\'s subscription id)\n' \
                   '    "subs_canceled_at" : datetime, (Date the subscription was canceled)\n' \
                   '    "subs_ended_at" : datetime, (Date the subscription was ended)\n' \
                   '   ]\n' \
                   '  "interface_status_flags": integer,\n' \
                   '}'

    template_values = {
        'api_name': 'voterRetrieve',
        'api_slug': 'voterRetrieve',
        'api_introduction': "Export key voter data to JSON format",
        'try_now_link': 'apis_v1:voterRetrieveView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes': "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
