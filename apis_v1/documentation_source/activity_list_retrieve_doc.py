# apis_v1/documentation_source/activity_list_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def activity_list_retrieve_doc_template_values(url_root):
    """
    Show documentation about activityListRetrieve
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
            'description':  'Voters device id',
        },
    ]

    potential_status_codes_list = [
        {
            'code':         'VALID_VOTER_DEVICE_ID_MISSING',
            'description':  'A valid voter_device_id parameter was not included. Cannot proceed.',
        },
        {
            'code':         'VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            'description':  'No voter could be found from the voter_device_id',
        },
    ]

    try_now_link_variables_dict = {
        # 'voter_device_id': '',
    }

    api_response = '{\n' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "activity_list": list\n' \
                   '   [{\n' \
                   '     "date_last_changed": string,\n' \
                   '     "date_of_notice": string,\n' \
                   '     "id": integer,\n' \
                   '     "kind_of_seed": string,\n' \
                   '     "new_positions_entered_count": integer,\n' \
                   '     "position_we_vote_id_list": list,\n' \
                   '     "speaker_name": string,\n' \
                   '     "speaker_organization_we_vote_id": string,\n' \
                   '     "speaker_voter_we_vote_id": string,\n' \
                   '     "speaker_profile_image_url_medium": string,\n' \
                   '     "speaker_profile_image_url_tiny": string,\n' \
                   '   },],\n' \
                   '}'

    template_values = {
        'api_name': 'activityListRetrieve',
        'api_slug': 'activityListRetrieve',
        'api_introduction':
            "Retrieve an activity_list that we can display to this voter.",
        'try_now_link': 'apis_v1:activityListRetrieveView',
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
