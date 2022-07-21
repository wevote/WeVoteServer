# campaign/controllers_email_outbound.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
import json

from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def campaignx_friend_has_supported_send(  # CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE
        campaignx_we_vote_id='',
        recipient_voter_we_vote_id='',
        speaker_voter_we_vote_id=''):
    from email_outbound.controllers import schedule_email_with_email_outbound_description
    from email_outbound.models import EmailManager, CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE
    status = ""

    voter_manager = VoterManager()
    from organization.controllers import transform_campaigns_url
    campaigns_root_url_verified = transform_campaigns_url('')  # Change to client URL if needed

    recipient_voter_results = voter_manager.retrieve_voter_by_we_vote_id(recipient_voter_we_vote_id)
    if not recipient_voter_results['voter_found']:
        error_results = {
            'status':                               "RECIPIENT_VOTER_NOT_FOUND ",
            'success':                              False,
        }
        return error_results

    recipient_voter = recipient_voter_results['voter']

    email_manager = EmailManager()

    # Retrieve the email address of the original_sender (which is the person we are sending this notification to)
    recipient_email_we_vote_id = ""
    recipient_email = ""
    recipient_email_subscription_secret_key = ""
    if recipient_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(recipient_voter_we_vote_id)
        success = results['success']
        if results['email_address_object_found']:
            recipient_email_object = results['email_address_object']
            recipient_email_we_vote_id = recipient_email_object.we_vote_id
            recipient_email = recipient_email_object.normalized_email_address
            if positive_value_exists(recipient_email_object.subscription_secret_key):
                recipient_email_subscription_secret_key = recipient_email_object.subscription_secret_key
            else:
                recipient_email_subscription_secret_key = \
                    email_manager.update_email_address_with_new_subscription_secret_key(
                        email_we_vote_id=recipient_email_we_vote_id)
    else:
        # The recipient must have a valid email
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VALID_EMAIL "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    if positive_value_exists(recipient_email_we_vote_id):
        recipient_voter_we_vote_id = recipient_voter.we_vote_id

    if not positive_value_exists(recipient_voter_we_vote_id):
        # The recipient must have a valid voter_we_vote_id
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VOTER_WE_VOTE_ID "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    real_name_only = True
    recipient_name = recipient_voter.get_full_name(real_name_only)

    speaker_voter_name = ''
    if positive_value_exists(speaker_voter_we_vote_id):
        speaker_voter_results = voter_manager.retrieve_voter_by_we_vote_id(speaker_voter_we_vote_id)
        if speaker_voter_results['voter_found']:
            speaker_voter = speaker_voter_results['voter']
            speaker_voter_name = speaker_voter.get_full_name(real_name_only)
            # speaker_voter_photo = speaker_voter.voter_photo_url()

    from campaign.controllers import fetch_sentence_string_from_politician_list
    from campaign.models import CampaignXManager
    campaignx_manager = CampaignXManager()
    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)
    campaignx_title = ''
    campaignx_url = campaigns_root_url_verified + '/id/' + campaignx_we_vote_id  # Default link
    we_vote_hosted_campaign_photo_large_url = ''
    if results['campaignx_found']:
        campaignx = results['campaignx']
        campaignx_title = campaignx.campaign_title
        if positive_value_exists(campaignx.seo_friendly_path):
            campaignx_url = campaigns_root_url_verified + '/c/' + campaignx.seo_friendly_path
        we_vote_hosted_campaign_photo_large_url = campaignx.we_vote_hosted_campaign_photo_large_url

    politician_list = campaignx_manager.retrieve_campaignx_politician_list(campaignx_we_vote_id=campaignx_we_vote_id)
    politician_count = len(politician_list)
    your_friends_name = speaker_voter_name if positive_value_exists(speaker_voter_name) else 'Your friend'
    if politician_count > 0:
        subject = your_friends_name + " supports" + fetch_sentence_string_from_politician_list(
            politician_list=politician_list,
            max_number_of_list_items=4,
        )
        politician_full_sentence_string = fetch_sentence_string_from_politician_list(
            politician_list=politician_list,
        )
    else:
        subject = your_friends_name + " supports " + campaignx_title
        politician_full_sentence_string = ''

    # Unsubscribe link in email
    recipient_unsubscribe_url = \
        campaigns_root_url_verified + "/settings/notifications/esk/" + recipient_email_subscription_secret_key
    # recipient_unsubscribe_url = \
    #     "{root_url}/unsubscribe/{email_secret_key}/friendcampaignsupport" \
    #     "".format(
    #         email_secret_key=recipient_email_subscription_secret_key,
    #         root_url=campaigns_root_url_verified,
    #     )
    # Instant unsubscribe link in email header
    # list_unsubscribe_url = str(str(recipient_unsubscribe_url) + '/instant')
    # # Instant unsubscribe email address in email header
    # # from voter.models import NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL  # To be updated
    # list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
    #                           "".format(setting='NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL')

    template_variables_for_json = {
        "subject":                          subject,
        "campaignx_title":                  campaignx_title,
        "campaignx_url":                    campaignx_url,
        "politician_count":                 politician_count,
        "politician_full_sentence_string":  politician_full_sentence_string,
        "recipient_name":                   recipient_name,
        "recipient_unsubscribe_url":        recipient_unsubscribe_url,
        "recipient_voter_email":            recipient_email,
        "speaker_voter_name":               speaker_voter_name,
        "view_main_discussion_page_url":    campaigns_root_url_verified + "/news",
        "view_your_ballot_url":             campaigns_root_url_verified + "/ballot",
        "we_vote_hosted_campaign_photo_large_url":  we_vote_hosted_campaign_photo_large_url,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    from_email_for_daily_summary = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    # Create the outbound email description, then schedule it
    kind_of_email_template = CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE
    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=speaker_voter_we_vote_id,
        sender_voter_email=from_email_for_daily_summary,
        sender_voter_name=speaker_voter_name,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        # list_unsubscribe_mailto=list_unsubscribe_mailto,
        # list_unsubscribe_url=list_unsubscribe_url,
    )
    status += outbound_results['status'] + " "
    success = outbound_results['success']
    if outbound_results['email_outbound_description_saved']:
        email_outbound_description = outbound_results['email_outbound_description']
        schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
        status += schedule_results['status'] + " "
        success = schedule_results['success']
        if schedule_results['email_scheduled_saved']:
            # messages_to_send.append(schedule_results['email_scheduled_id'])
            email_scheduled = schedule_results['email_scheduled']
            send_results = email_manager.send_scheduled_email(email_scheduled)
            email_scheduled_sent = send_results['email_scheduled_sent']
            status += send_results['status']
            success = send_results['success']

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results


def campaignx_news_item_send(  # CAMPAIGNX_NEWS_ITEM_TEMPLATE
        campaignx_news_item_we_vote_id='',
        campaigns_root_url_verified='',
        campaignx_title='',
        campaignx_url='',
        campaignx_we_vote_id='',
        politician_count=0,
        politician_full_sentence_string='',
        recipient_voter_we_vote_id='',
        speaker_voter_name='',
        speaker_voter_we_vote_id='',
        statement_subject='',
        statement_text_preview='',
        we_vote_hosted_campaign_photo_large_url=''):
    from campaign.models import CampaignXManager
    from email_outbound.controllers import schedule_email_with_email_outbound_description
    from email_outbound.models import EmailManager, CAMPAIGNX_NEWS_ITEM_TEMPLATE, CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE
    status = ""

    campaignx_manager = CampaignXManager()
    email_manager = EmailManager()
    voter_manager = VoterManager()

    recipient_voter_results = voter_manager.retrieve_voter_by_we_vote_id(recipient_voter_we_vote_id)
    if not recipient_voter_results['voter_found']:
        error_results = {
            'status':                               "RECIPIENT_VOTER_NOT_FOUND ",
            'success':                              False,
        }
        return error_results

    recipient_voter = recipient_voter_results['voter']

    # Retrieve the email address of the original_sender (which is the person we are sending this notification to)
    recipient_email_we_vote_id = ""
    recipient_email = ""
    recipient_email_subscription_secret_key = ""
    if recipient_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(recipient_voter_we_vote_id)
        success = results['success']
        if results['email_address_object_found']:
            recipient_email_object = results['email_address_object']
            recipient_email_we_vote_id = recipient_email_object.we_vote_id
            recipient_email = recipient_email_object.normalized_email_address
            if positive_value_exists(recipient_email_object.subscription_secret_key):
                recipient_email_subscription_secret_key = recipient_email_object.subscription_secret_key
            else:
                recipient_email_subscription_secret_key = \
                    email_manager.update_email_address_with_new_subscription_secret_key(
                        email_we_vote_id=recipient_email_we_vote_id)
    else:
        # The recipient must have a valid email
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VALID_EMAIL "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    if not positive_value_exists(recipient_email_we_vote_id):
        recipient_voter_we_vote_id = recipient_voter.we_vote_id

    if not positive_value_exists(recipient_voter_we_vote_id):
        # The recipient must have a valid voter_we_vote_id
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VOTER_WE_VOTE_ID "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    recipient_name = recipient_voter.get_full_name(real_name_only=True)

    # When did this voter support this campaign?
    date_supported = ''
    supporter_results = campaignx_manager.retrieve_campaignx_supporter(
        campaignx_we_vote_id=campaignx_we_vote_id,
        voter_we_vote_id=recipient_voter_we_vote_id,
        read_only=True,
    )
    if supporter_results['campaignx_supporter_found']:
        campaign_supporter = supporter_results['campaignx_supporter']
        if campaign_supporter.date_supported:
            try:
                date_supported = campaign_supporter.date_supported.strftime('%B %d, %Y at %H:%M')
            except Exception as e:
                status += "DATE_CONVERSION_ERROR: " + str(e) + " "

    campaignx_news_item_url = campaignx_url + '/u/' + campaignx_news_item_we_vote_id

    # Unsubscribe link in email
    recipient_unsubscribe_url = \
        campaigns_root_url_verified + "/settings/notifications/esk/" + recipient_email_subscription_secret_key
    # recipient_unsubscribe_url = \
    #     "{root_url}/unsubscribe/{email_secret_key}/friendopinionsall" \
    #     "".format(
    #         email_secret_key=recipient_email_subscription_secret_key,
    #         root_url=campaigns_root_url_verified,
    #     )
    # # Instant unsubscribe link in email header
    # list_unsubscribe_url = str(str(recipient_unsubscribe_url) + '/instant')
    # # Instant unsubscribe email address in email header
    # # from voter.models import NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL  # To be updated
    # list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
    #                           "".format(setting='NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL')

    template_variables_for_json = {
        "subject":                          statement_subject,
        "campaignx_title":                  campaignx_title,
        "campaignx_news_item_url":          campaignx_news_item_url,
        "campaignx_news_text":              statement_text_preview,
        "campaignx_url":                    campaignx_url,
        "date_supported":                   date_supported,
        "politician_count":                 politician_count,
        "politician_full_sentence_string":  politician_full_sentence_string,
        "recipient_name":                   recipient_name,
        "recipient_unsubscribe_url":        recipient_unsubscribe_url,
        "recipient_voter_email":            recipient_email,
        "speaker_voter_name":               speaker_voter_name,
        "view_main_discussion_page_url":    campaigns_root_url_verified + "/news",
        "view_your_ballot_url":             campaigns_root_url_verified + "/ballot",
        "we_vote_hosted_campaign_photo_large_url":  we_vote_hosted_campaign_photo_large_url,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    from_email_for_campaignx_news_item = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    # Create the outbound email description, then schedule it
    kind_of_email_template = CAMPAIGNX_NEWS_ITEM_TEMPLATE
    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=speaker_voter_we_vote_id,
        sender_voter_email=from_email_for_campaignx_news_item,
        sender_voter_name=speaker_voter_name,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        # list_unsubscribe_mailto=list_unsubscribe_mailto,
        # list_unsubscribe_url=list_unsubscribe_url,
    )
    status += outbound_results['status'] + " "
    success = outbound_results['success']
    if outbound_results['email_outbound_description_saved']:
        email_outbound_description = outbound_results['email_outbound_description']
        schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
        status += schedule_results['status'] + " "
        success = schedule_results['success']
        if schedule_results['email_scheduled_saved']:
            # messages_to_send.append(schedule_results['email_scheduled_id'])
            email_scheduled = schedule_results['email_scheduled']
            send_results = email_manager.send_scheduled_email(email_scheduled)
            email_scheduled_sent = send_results['email_scheduled_sent']
            status += send_results['status']
            success = send_results['success']

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results


def campaignx_super_share_item_send(  # CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE
        campaignx_news_item_we_vote_id='',
        campaigns_root_url_verified='',
        campaignx_title='',
        recipient_email_address='',
        recipient_first_name='',
        recipient_voter_we_vote_id='',
        speaker_email_address='',
        speaker_photo='',
        speaker_voter_name='',
        speaker_voter_we_vote_id='',
        statement_subject='',
        statement_text_preview='',
        view_shared_campaignx_url='',
        we_vote_hosted_campaign_photo_large_url='',
):
    # from campaign.models import CampaignXManager
    from email_outbound.controllers import schedule_email_with_email_outbound_description
    from email_outbound.models import EmailManager, CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE
    import html
    status = ""

    email_manager = EmailManager()

    # Invitation Message HTML
    invitation_message = statement_text_preview.replace("\r\n", "<br />")
    invitation_message = invitation_message.replace("\n\r", "<br />")
    invitation_message = invitation_message.replace("\n", "<br />")
    invitation_message = invitation_message.replace("\r", "<br />")

    # Invitation Message Plain Text
    invitation_message_plain_text = html.unescape(statement_text_preview)

    if positive_value_exists(campaignx_news_item_we_vote_id):
        campaignx_news_item_url = view_shared_campaignx_url + '/u/' + campaignx_news_item_we_vote_id
    else:
        campaignx_news_item_url = ''

    recipient_email_subscription_secret_key = ''  # To be added
    # Unsubscribe link in email
    recipient_unsubscribe_url = \
        "{root_url}/unsubscribe/{email_secret_key}/campaignshare" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=campaigns_root_url_verified,
        )
    # Instant unsubscribe link in email header
    list_unsubscribe_url = str(str(recipient_unsubscribe_url) + '/instant')
    # Instant unsubscribe email address in email header
    # from voter.models import NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL  # To be updated
    list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                              "".format(setting='NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL')

    template_variables_for_json = {
        "campaignx_title":                  campaignx_title,
        "campaignx_news_item_url":          campaignx_news_item_url,
        "campaignx_news_text":              statement_text_preview,
        "campaignx_url":                    view_shared_campaignx_url,
        "invitation_message":               invitation_message,
        "invitation_message_plain_text":    invitation_message_plain_text,
        "recipient_email_address":          recipient_email_address,
        "recipient_first_name":             recipient_first_name,
        "recipient_unsubscribe_url":        recipient_unsubscribe_url,
        "sender_email_address":             speaker_email_address,
        "sender_photo":                     speaker_photo,
        "sender_name":                      speaker_voter_name,
        "subject":                          statement_subject,
        "view_home_page_url":               campaigns_root_url_verified,
        "we_vote_hosted_campaign_photo_large_url":  we_vote_hosted_campaign_photo_large_url,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    from_email_for_campaignx_news_item = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    # Create the outbound email description, then schedule it
    kind_of_email_template = CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE
    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=speaker_voter_we_vote_id,
        sender_voter_email=from_email_for_campaignx_news_item,
        sender_voter_name=speaker_voter_name,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id='',
        recipient_voter_email=recipient_email_address,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        list_unsubscribe_mailto=list_unsubscribe_mailto,
        list_unsubscribe_url=list_unsubscribe_url,
    )
    status += outbound_results['status'] + " "
    success = outbound_results['success']
    if outbound_results['email_outbound_description_saved']:
        email_outbound_description = outbound_results['email_outbound_description']
        schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
        status += schedule_results['status'] + " "
        success = schedule_results['success']
        if schedule_results['email_scheduled_saved']:
            email_scheduled = schedule_results['email_scheduled']
            send_results = email_manager.send_scheduled_email(email_scheduled)
            email_scheduled_sent = send_results['email_scheduled_sent']
            status += send_results['status']
            success = send_results['success']

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results


def campaignx_supporter_initial_response_send(  # CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE
        campaignx_we_vote_id='',
        recipient_voter_we_vote_id=''):
    from email_outbound.controllers import schedule_email_with_email_outbound_description
    from email_outbound.models import EmailManager, CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE
    status = ""

    voter_manager = VoterManager()
    from organization.controllers import transform_campaigns_url
    campaigns_root_url_verified = transform_campaigns_url('')  # Change to client URL if needed

    recipient_voter_results = voter_manager.retrieve_voter_by_we_vote_id(recipient_voter_we_vote_id)
    if not recipient_voter_results['voter_found']:
        error_results = {
            'status':                               "RECIPIENT_VOTER_NOT_FOUND ",
            'success':                              False,
        }
        return error_results

    recipient_voter = recipient_voter_results['voter']

    email_manager = EmailManager()

    # Retrieve the email address of the original_sender (which is the person we are sending this notification to)
    recipient_email_we_vote_id = ""
    recipient_email = ""
    recipient_email_subscription_secret_key = ""
    if recipient_voter.has_email_with_verified_ownership():
        results = email_manager.retrieve_primary_email_with_ownership_verified(recipient_voter_we_vote_id)
        success = results['success']
        if results['email_address_object_found']:
            recipient_email_object = results['email_address_object']
            recipient_email_we_vote_id = recipient_email_object.we_vote_id
            recipient_email = recipient_email_object.normalized_email_address
            if positive_value_exists(recipient_email_object.subscription_secret_key):
                recipient_email_subscription_secret_key = recipient_email_object.subscription_secret_key
            else:
                recipient_email_subscription_secret_key = \
                    email_manager.update_email_address_with_new_subscription_secret_key(
                        email_we_vote_id=recipient_email_we_vote_id)
    else:
        # The recipient must have a valid email
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VALID_EMAIL "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    if not positive_value_exists(recipient_email_we_vote_id):
        recipient_voter_we_vote_id = recipient_voter.we_vote_id

    if not positive_value_exists(recipient_voter_we_vote_id):
        # The recipient must have a valid voter_we_vote_id
        status += "RECIPIENT_VOTER_DOES_NOT_HAVE_VOTER_WE_VOTE_ID "
        success = True
        results = {
            'success': success,
            'status': status,
        }
        return results

    # Template variables
    from campaign.controllers import fetch_sentence_string_from_politician_list
    from campaign.models import CampaignXManager
    campaignx_manager = CampaignXManager()
    results = campaignx_manager.retrieve_campaignx(campaignx_we_vote_id=campaignx_we_vote_id)
    campaignx_title = ''
    campaignx_url = campaigns_root_url_verified + '/id/' + campaignx_we_vote_id  # Default link
    we_vote_hosted_campaign_photo_large_url = ''
    if results['campaignx_found']:
        campaignx = results['campaignx']
        campaignx_title = campaignx.campaign_title
        if positive_value_exists(campaignx.seo_friendly_path):
            campaignx_url = campaigns_root_url_verified + '/c/' + campaignx.seo_friendly_path
        we_vote_hosted_campaign_photo_large_url = campaignx.we_vote_hosted_campaign_photo_large_url
    campaignx_share_campaign_url = campaignx_url + '/share-campaign'

    real_name_only = True
    recipient_name = recipient_voter.get_full_name(real_name_only)
    # speaker_voter_name = speaker_voter.get_full_name(real_name_only)
    # speaker_voter_photo = speaker_voter.voter_photo_url()
    # speaker_voter_description = ""
    # speaker_voter_network_details = ""

    politician_list = campaignx_manager.retrieve_campaignx_politician_list(campaignx_we_vote_id=campaignx_we_vote_id)
    politician_count = len(politician_list)
    if politician_count > 0:
        subject = "You support" + fetch_sentence_string_from_politician_list(
            politician_list=politician_list,
            max_number_of_list_items=4,
        )
        politician_full_sentence_string = fetch_sentence_string_from_politician_list(
            politician_list=politician_list,
        )
    else:
        subject = "You support " + campaignx_title
        politician_full_sentence_string = ''

    recipient_email_subscription_secret_key = ''  # To be added
    # Unsubscribe link in email
    recipient_unsubscribe_url = \
        campaigns_root_url_verified + "/settings/notifications/esk/" + recipient_email_subscription_secret_key
    # recipient_unsubscribe_url = \
    #     "{root_url}/unsubscribe/{email_secret_key}/friendopinionsall" \
    #     "".format(
    #         email_secret_key=recipient_email_subscription_secret_key,
    #         root_url=campaigns_root_url_verified,
    #     )
    # # Instant unsubscribe link in email header
    # list_unsubscribe_url = str(str(recipient_unsubscribe_url) + '/instant')
    # # Instant unsubscribe email address in email header
    # # from voter.models import NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL  # To be updated
    # list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
    #                           "".format(setting='NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL')

    template_variables_for_json = {
        "subject":                          subject,
        "campaignx_share_campaign_url":     campaignx_share_campaign_url,
        "campaignx_title":                  campaignx_title,
        "campaignx_url":                    campaignx_url,
        "politician_count":                 politician_count,
        "politician_full_sentence_string":  politician_full_sentence_string,
        # "sender_email_address":         speaker_voter_email,  # Does not affect the "From" email header
        # "sender_description":           speaker_voter_description,
        # "sender_network_details":       speaker_voter_network_details,
        "recipient_name":                   recipient_name,
        "recipient_unsubscribe_url":        recipient_unsubscribe_url,
        "recipient_voter_email":            recipient_email,
        "view_main_discussion_page_url":    campaigns_root_url_verified + "/news",
        "view_your_ballot_url":             campaigns_root_url_verified + "/ballot",
        "we_vote_hosted_campaign_photo_large_url":  we_vote_hosted_campaign_photo_large_url,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    from_email_for_daily_summary = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    # Create the outbound email description, then schedule it
    kind_of_email_template = CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE
    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=recipient_voter_we_vote_id,
        sender_voter_email=from_email_for_daily_summary,
        sender_voter_name='',
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        # list_unsubscribe_mailto=list_unsubscribe_mailto,
        # list_unsubscribe_url=list_unsubscribe_url,
    )
    status += outbound_results['status'] + " "
    success = outbound_results['success']
    if outbound_results['email_outbound_description_saved']:
        email_outbound_description = outbound_results['email_outbound_description']
        schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
        status += schedule_results['status'] + " "
        success = schedule_results['success']
        if schedule_results['email_scheduled_saved']:
            # messages_to_send.append(schedule_results['email_scheduled_id'])
            email_scheduled = schedule_results['email_scheduled']
            send_results = email_manager.send_scheduled_email(email_scheduled)
            email_scheduled_sent = send_results['email_scheduled_sent']
            status += send_results['status']
            success = send_results['success']

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results
