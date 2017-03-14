# apis_v1/documentation_source/voter_address_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def donation_with_stripe_doc_template_values(url_root):
    """
    Show documentation about donationWithStripe
    """
    required_query_parameter_list = [
        {
            'name':         'api_key',
            'value':        'string (from post, cookie, or get (in that order))',  # boolean, integer, long, string
            'description':  'The unique key provided to any organization using the WeVoteServer APIs',
        },
        {
            'name':         'token',
            'value':        'string',  # boolean, integer, long, string
            'description':  'A unique identifier linked to a stripe payment made on the client side',
        },
        {
            'name': 'email',
            'value': 'string',  # boolean, integer, long, string
            'description': 'A unique email linked to a stripe payment made on the client side',
        },

    ]
    optional_query_parameter_list = [
        {
            'name':         'amount',
            'value':        'integer',  # boolean, integer, long, string
            'description':  'amount to be charged',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'TOKEN_MISSING',
            'description':  'Cannot proceed. A valid stripe token was not included.',
        }
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "token": string,\n' \
                   '}'
    template_values = {
        'api_name': 'donationWithStripe',
        'api_slug': 'donationWithStripe',
        'api_introduction':
            "Process stripe payment with stripe client generated token",
        'try_now_link': 'apis_v1:donationWithStripeView',
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
