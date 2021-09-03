# apis_v1/documentation_source/campaign_news_item_save_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def campaign_news_item_save_doc_template_values(url_root):
    """
    Show documentation about campaignNewsItemSave
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
            'name':         'campaignx_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we_vote_id for the campaign.',
        },
    ]
    optional_query_parameter_list = [
        {
            'name':         'campaignx_news_item_we_vote_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The we_vote_id for the news item.',
        },
        {
            'name':         'campaign_news_subject',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The subject of the news item.',
        },
        {
            'name':         'campaign_news_subject_changed',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Are we trying to change the campaign news item\'s subject?',
        },
        {
            'name':         'campaign_news_text',
            'value':        'string',  # boolean, integer, long, string
            'description':  'The text of the news item.',
        },
        {
            'name':         'campaign_news_text_changed',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Are we trying to change the campaign news item\'s text?',
        },
        {
            'name':         'in_draft_mode',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Is this item still in draft mode?',
        },
        {
            'name':         'in_draft_mode_changed',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Has the draft mode changed?',
        },
        {
            'name':         'visible_to_public',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Is this item visible to supporters or the public?',
        },
        {
            'name':         'visible_to_public_changed',
            'value':        'boolean',  # boolean, integer, long, string
            'description':  'Has the visible to public setting changed?',
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
        # 'campaignx_we_vote_id': 'wv85camp1',
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "campaign_news_subject": string,\n' \
                   '  "campaign_news_text": string,\n' \
                   '  "campaignx_news_item_we_vote_id": string,\n' \
                   '  "campaignx_we_vote_id": string,\n' \
                   '  "date_last_changed": string,\n' \
                   '  "date_posted": string,\n' \
                   '  "date_sent_to_email": string,\n' \
                   '  "in_draft_mode": boolean,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "speaker_name": string,\n' \
                   '  "visible_to_public": boolean,\n' \
                   '  "voter_we_vote_id": string,\n' \
                   '  "we_vote_hosted_profile_photo_image_url_tiny": string,\n' \
                   '}'

    template_values = {
        'api_name': 'campaignNewsItemSave',
        'api_slug': 'campaignNewsItemSave',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:campaignNewsItemSaveView',
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
