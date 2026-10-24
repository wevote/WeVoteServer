# apis_v1/documentation_source/voter_reviewed_app_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def voter_reviewed_app_template_values(url_root):
    """
    Show documentation about voterReviewedApp
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server. ',
        },
        {
            'name':         'address_state_code',
            'value':        'string',  #    ('CA')
            'description':  'The two letter state for the voter&apos;s ballot location',
        },
        {
            'name':         'app_review_state',
            'value':        'string',  #    ('Positive', 'Negative', None)
            'description':  'The new state of the app review stored in voter_voter, one of {"POSITIVE", '
                            '"NEGATIVE", "NONE"}',
        },
        {
            'name':         'app_review_version',
            'value':        'string',  #    Version number string
            'description':  'The version of the app being reviewed... something like "2.7.4"',
        },
        {
            'name':         'app_review_platform',
            'value':        'string',  #
            'description':  'The platform of the app being reviewed, one of {"iOS", "Android"}',
        },
        {
            'name':         'app_review_pathname',
            'value':        'string',  #
            'description':  'The path (or page) being displayed, when the app review is initiated ... something like "/ballot"',
        },
        {
            'name':         'app_review_body_negative_bypass',
            'value':        'string',  #
            'description':  'Only when a Negative review is bypassed, this is the message body that is sent to Zendesk.'
                            ' This is not saved in the database.',
        },
        {
            'name':         'app_review_email',
            'value':        'string',  #
            'description':  'When a Negative review is bypassed and this email is supplied, use it for a "from" for '
                            'the email to Zendesk that creates a ticket. If no email is provided, the voter does '
                            'not want a reply from WeVote, and we supply donotreply@wevote.us as a "from". '
                            'This is not saved in the database.',
        },
        {
            'name':         'sendgrid_outgoing_email',
            'value':        'string',  #
            'description':  'Normally leave this field blank.  Only used in testing, when one needs to send the email to themselves instead of to Zendesk.',
        },
    ]


    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'format': 'json',
    }

    api_response = '[{\n' \
                   '  "success": string,\n' \
                   '  "status": string,\n' \
                   '  "we_vote_id": string,\n' \
                   '  "app_review_state": string,\n' \
                   '  "app_review_date": string,\n' \
                   '  "app_review_version": string,\n' \
                   '  "app_review_platform": string,\n' \
                   '  "email_api_status_code": string,\n' \
                   '  "app_review_email": string,\n' \
                   '  "first_name": string,\n' \
                   '  "last_name": string,\n' \
                   '}]'

    template_values = {
        'api_name': 'voterReviewedApp',
        'api_slug': 'voterReviewedApp',
        'get_or_post': 'POST',
        'url_root': url_root,
        'api_introduction':
            "This API is called from Cordova apps when they are prompted to review the app.<br><br>"
            
            "For negative reviews where the voter chooses to supply an email and which are screened out by the "
            "<b>\"Enjoying WeVote?\"</b> screening question (appRatePromptTitle), we send that email on to Zendesk "
            "which creates a ticket and generates an automatic email reply to the voter. If the voter does not "
            "supply an email, we use <b>\"donotreply@wevote.us\"</b> as the return address so the voter doesn't "
            "receive an email, and in that case we put the <span style='font-family: monospace; font-weight: 500;'>"
            "\"we_vote_id\"</span> in the ticket body which will allow us to to filter out repetitive complainers and "
            "spammers).<br><br>"
            
            "For the (hopefully) positive reviews that fall through to the App Store/Play Store process, we won't know "
            "if they loved us or hated us, but we log the date of their review so we don't ask them for reviews too "
            "often, and display a thank you modal (if the platform allows for that). <br><br>"
            
            "In either case we update the voter's record (voter_voter) with the four fields: "
            "<span style='font-family: monospace; font-weight: 500;'>app_review_state, app_review_version, app_review_platform, & app_review_date</span>."
            "<br><br>"
            
            "This will allow us to build automation in the future, so that could start asking for reviews again after a "
            "certain number of months, or after a major UI change. <br><br>",

        'try_now_link': 'apis_v1:voterReviewedApp',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'required_query_parameter_list': required_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
    }
    return template_values
