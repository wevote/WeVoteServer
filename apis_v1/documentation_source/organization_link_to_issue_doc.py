# apis_v1/documentation_source/issues_retrieve_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def organization_link_to_issue_doc_template_values(url_root):
    """
    Show documentation about organizationLinkToIssue
    """
    optional_query_parameter_list = [
        {
            'name': 'organization_we_vote_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The we vote id for the Advocate',
        },
        {
            'name': 'issue_we_vote_id',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The we vote id for the Issue',
        },
        {
            'name': 'organization_linked_to_issue',
            'value': 'boolean',  # boolean, integer, long, string
            'description': 'Specifies if the organization to issue link should be active or blocked',
        },
        {
            'name': 'reason_for_link',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The reason why the link is being made active'
                           'Possible reasons for making link active:  NO_REASON, LINKED_BY_ORGANIZATION, '
                           '   LINKED_BY_WE_VOTE, AUTO_LINKED_BY_HASHTAG, AUTO_LINKED_BY_HASHTAG',
        },
        {
            'name': 'reason_for_unlink',
            'value': 'string',  # boolean, integer, long, string
            'description':  'The reason why the link is being blocked or unlinked'
                            'Possible reasons for making link inactive(blocking the link):  BLOCKED_BY_ORGANIZATION, '
                            'BLOCKED_BY_WE_VOTE, FLAGGED_BY_VOTERS',
        },
    ]

    potential_status_codes_list = [
    ]

    try_now_link_variables_dict = {
        'organization_linked_to_issue': 'True',
        'reason_for_link': 'LINKED_BY_ORGANIZATION',
        'reason_for_unlink': 'BLOCKED_BY_ORGANIZATION',
    }

    api_response = '[{' \
                   '  "success": boolean,\n' \
                   '  "status": string,\n' \
                   '  "organization_we_vote_id": string,\n' \
                   '  "issue_we_vote_id": string,\n' \
                   '  "organization_linked_to_issue": boolean,\n' \
                   '  "reason_for_link": string,\n' \
                   '  "reason_for_unlink": string,\n' \
                   '  "link_issue_found": boolean,\n' \
                   '  "link_issue": {\n' \
                   '        "organization_we_vote_id": string,\n' \
                   '        "issue_id": integer,\n' \
                   '        "issue_we_vote_id": string,\n' \
                   '        "link_active": boolean,\n' \
                   '        "reason_for_link": string,\n' \
                   '        "link_blocked": boolean,\n' \
                   '        "reason_link_is_blocked": boolean,\n' \
                   '    "}" \n' \
                   '}]'

    template_values = {
        'api_name': 'organizationLinkToIssue',
        'api_slug': 'organizationLinkToIssue',
        'api_introduction':
            "",
        'try_now_link': 'apis_v1:organizationLinkToIssueView',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
