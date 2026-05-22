# email_outbound/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import base64
import json
import re
import uuid
from datetime import datetime
import time

from django.utils import timezone
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from admin_tools.views import redirect_to_sign_in_page
from email_outbound.models import EmailAttachments
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_functions.validate_email import validate_email
from .functions import build_s3_key, upload_fileobj_to_s3, delete_from_s3, download_bytes_from_s3, \
    move_s3_object, cleanup_unused_inline_attachments

from .controllers_email_campaign import augment_email_campaign_recipient, refresh_email_campaign_data, \
    render_audience_builder_html
from .controllers_audience_builder import audience_builder_data_retrieve, render_audience_builder_preview_html
from .models import EmailCampaign, EmailTemplate, EmailTemplateFolder, EmailCampaignRecipient, \
    AudienceBuilderFolder, AudienceBuilder, AudienceFilter, AudienceFilterChain, EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS, \
    OPERATOR_AND, OPERATOR_EXCLUDE, OPERATOR_INCLUDE, OPERATOR_OR

logger = wevote_functions.admin.get_logger(__name__)

# can change these restrictions accordingly
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10MB; adjust to your needs
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

def add_to_recipient_dict_if_accepted_we_vote_id_type(incoming_we_vote_id, recipient_dict, accepted_we_vote_id_types):
    save_recipient = False
    for we_vote_id_type in accepted_we_vote_id_types:
        if we_vote_id_type in incoming_we_vote_id:
            # It's a we_vote_id type we expect
            if we_vote_id_type == 'pol':
                recipient_dict.update({
                    'politician_we_vote_id': incoming_we_vote_id,
                })
                save_recipient = True
            elif we_vote_id_type == 'voter':
                recipient_dict.update({
                    'voter_we_vote_id': incoming_we_vote_id,
                })
                save_recipient = True
            break
    return recipient_dict, save_recipient


def email_associated_with_we_vote_id(email_address, incoming_we_vote_id):
    # TODO Check to make sure the email address is actually associated with the incoming_we_vote_id
    return True


@login_required
def email_campaign_edit_process_view(request):
    """
    Process the new or edit campaign form
    :param request:
    :return:
    """
    # The performance_dict variable contains list(s) of performance_snapshots.
    performance_dict = {}
    # Set up performance_list for this view. A pointer to the performance_list variable is established here.
    #  Throughout the rest of this view, we add snapshots to the performance_list. Since the performance_list
    #  is "attached" to the performance_dict with a pointer, when we pass performance_dict to the template,
    #  the performance_list data is included.
    performance_list = []
    performance_dict.update({
        'email_campaign_edit_process_view': performance_list,
    })

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    # Get form data
    audience_builder_id = request.POST.get('audience_builder_id', 0)
    audience_builder_id = convert_to_int(audience_builder_id)
    campaign_title = request.POST.get('campaign_title', '').strip()
    email_template_id = request.POST.get('email_template_id', 0)
    email_subject = request.POST.get('email_subject', '').strip()
    email_body = request.POST.get('email_body', '')
    email_campaign_id = request.POST.get('email_campaign_id', '')
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    include_footer = request.POST.get('include_footer', False)
    include_footer = positive_value_exists(include_footer)
    recipient_ids = request.POST.get('recipient_ids', '')
    state_code = request.POST.get('state_code', '')
    send_button_clicked = request.POST.get('send_button_clicked', '')
    send_time_option = request.POST.get('send_time_option', 'now')
    scheduled_send_time_str = request.POST.get('scheduled_send_time', '')
    draft_uuid = request.POST.get('draft_uuid', None)

    # Parse scheduled send time
    scheduled_send_time = None
    if send_time_option == 'scheduled' and scheduled_send_time_str:
        try:
            naive_dt = datetime.fromisoformat(scheduled_send_time_str)
            scheduled_send_time = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError:
            pass

    # Create or update email_campaign
    email_campaign = {}
    if email_campaign_id:
        try:
            email_campaign = EmailCampaign.objects.get(id=email_campaign_id)
            email_campaign.audience_builder_id = audience_builder_id
            email_campaign.email_campaign_name = campaign_title
            email_campaign.email_template_id = email_template_id
            email_campaign.email_subject_template_raw = email_subject
            email_campaign.email_body_template_raw = email_body
            email_campaign.include_footer = include_footer
            email_campaign.scheduled_send_time = scheduled_send_time
            email_campaign.save()
            
            # # Clear existing recipients for this email_campaign
            # # TODO: We want to update this to only delete entries below that have been removed from the form
            # deleted_count, result_dict = EmailCampaignRecipient.objects.filter(
            # email_campaign_id=email_campaign.id).delete()
            status += 'EMAIL_CAMPAIGN_UPDATED '
        except EmailCampaign.DoesNotExist:
            email_campaign = EmailCampaign.objects.create(
                audience_builder_id=audience_builder_id,
                email_campaign_name=campaign_title,
                email_template_id=email_template_id,
                email_subject_template_raw=email_subject,
                email_body_template_raw=email_body,
                scheduled_send_time=scheduled_send_time,
            )
            email_campaign_id = email_campaign.id
            messages.add_message(request, messages.SUCCESS, 'Email campaign created.')
        except Exception as e:
            messages.add_message(request, messages.ERROR, f'Could not update email campaign. {e}')
    else:
        try:
            email_campaign = EmailCampaign.objects.create(
                audience_builder_id=audience_builder_id,
                email_campaign_name=campaign_title,
                email_template_id=email_template_id,
                email_subject_template_raw=email_subject,
                email_body_template_raw=email_body,
                scheduled_send_time=scheduled_send_time,
            )
            email_campaign_id = email_campaign.id
            messages.add_message(request, messages.SUCCESS, 'Email campaign created.')
        except Exception as e:
            messages.add_message(request, messages.ERROR, f'Could not create email campaign. {e}')

    if not positive_value_exists(email_campaign_id):
        messages.add_message(request, messages.ERROR, 'Email campaign not created or saved.')

    # if creating an email campaign move attachments from draft to campaign folder
    if draft_uuid and email_campaign and email_campaign_id:
        try:
            with transaction.atomic():
                qs = EmailAttachments.objects.select_for_update().filter(
                    draft_uuid=draft_uuid,
                    email_campaign__isnull=True,
                    email_template__isnull=True,
                )
                for att in qs:
                    new_key = build_s3_key(
                        campaign_id=int(email_campaign_id),
                        template_id=None,
                        draft_uuid=None,
                        original_filename=att.original_name,
                    )
                    if EmailAttachments.objects.filter(s3_key=att.s3_key).count() == 1:

                        move_s3_object(old_key=att.s3_key, new_key=new_key)
                        att.s3_key = new_key

                    att.email_campaign = email_campaign
                    att.draft_uuid = None
                    att.save(update_fields=["s3_key", "email_campaign", "draft_uuid"])
        except Exception as e:
            status += f'ERROR_MOVING_DRAFT_ATTACHMENTS: {e} '

    # clean up previously saved inline images removed before hitting save
    try:
        cleanup_unused_inline_attachments(html=email_body, email_campaign=email_campaign)
    except Exception as e:
        status += f'ERROR_CLEANING_UP_INLINE_IMAGES: {e} '

    # Find all existing manually entered recipients for this email_campaign so we can remove them if they don't come in
    manually_added_recipients = []
    manually_added_recipients_found = False
    if positive_value_exists(email_campaign_id):
        try:
            queryset = EmailCampaignRecipient.objects.filter(email_campaign_id=email_campaign_id)
            queryset = queryset.filter(manually_added=True)
            manually_added_recipients = list(queryset)
            manually_added_recipients_found = True
        except Exception as e:
            status += f'ERROR_RETRIEVING_MANUALLY_ADDED_RECIPIENTS: {e} '

    # Retrieve the sender's voter_object if we are sending the email
    sender_object = {}
    if positive_value_exists(send_button_clicked):
        from voter.models import VoterManager
        from wevote_functions.functions import get_voter_api_device_id

        voter_api_device_id = get_voter_api_device_id(request)
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id, read_only=False)

        if voter_results['voter_found']:
            sender_object = voter_results['voter']
            status += "SENDER_VOTER_FOUND "
        else:
            status += "SENDER_VOTER_NOT_FOUND "
            messages.add_message(request, messages.ERROR, 'Could not identify sender voter.')

    campaignx_list_dict = {}
    politicians_dict = {}
    voters_dict = {}

    # Save recipients
    if positive_value_exists(recipient_ids) and positive_value_exists(email_campaign_id):
        accepted_we_vote_id_types = ['pol', 'voter']
        recipient_list = recipient_ids.split(',')
        for recipient_id in recipient_list:
            # Reset possible values
            email_address = ''
            incoming_we_vote_id = ''
            politician_we_vote_id = ''  # TODO if incoming_we_vote_id is pol, then assign to this
            recipient_dict = {}
            recipient_object = None
            save_recipient = False
            voter_we_vote_id = ''  # TODO if incoming_we_vote_id is voter, then assign to this
            recipient_id = recipient_id.strip()
            # recipient_id is structured like "WE_VOTE_ID-EMAIL_ADDRESS"
            # recipient_id = "wv01voter111-dalemcgrew@gmail.com"  # Test recipient_id
            # recipient_id = "dalemcgrew@gmail.com"  # Test recipient_id
            # recipient_id = "-dalemcgrew@gmail.com"  # Test recipient_id
            # recipient_id = "wv01pol111"  # Test recipient_id
            # recipient_id = "wv01voter111-"  # Test recipient_id
            if recipient_id:
                try:
                    part1, part2 = recipient_id.split('-')
                except Exception as e:
                    status += f'MINUS_SIGN_MISSING_FROM_RECIPIENT_ID: {e} '
                    part1 = recipient_id
                    part2 = ''

                save_recipient = False  # Reset to be safe
                recipient_dict.update({
                    'email_campaign_id':    email_campaign_id,
                    'manually_added':       True,
                })

                if positive_value_exists(part2):
                    # Check to see if part1 contains any strings from accepted_we_vote_id_types
                    recipient_dict, recipient_dict_changed = \
                        add_to_recipient_dict_if_accepted_we_vote_id_type(
                            part1, recipient_dict, accepted_we_vote_id_types)
                    if positive_value_exists(recipient_dict_changed):
                        incoming_we_vote_id = part1
                        save_recipient = True
                    if validate_email(part2):
                        # It's an email address
                        email_address = part2
                        save_recipient = True
                else:
                    # If only one part is found, test it to see if it's an email address or a we_vote_id
                    if validate_email(part1):
                        # It's an email address
                        email_address = part1
                        save_recipient = True
                    else:
                        # Check to see if part1 contains any strings from accepted_we_vote_id_types
                        recipient_dict, recipient_dict_changed = \
                            add_to_recipient_dict_if_accepted_we_vote_id_type(
                                part1, recipient_dict, accepted_we_vote_id_types)
                        if positive_value_exists(recipient_dict_changed):
                            incoming_we_vote_id = part1
                            save_recipient = True
                        # if validate_email(part2):  # part2 would never exist give if/else block above
                        #     # It's an email address
                        #     email_address = part2

                save_email = False
                if positive_value_exists(email_address):
                    # Check to make sure the email address is associated with the we_vote_id
                    if not positive_value_exists(incoming_we_vote_id):
                        save_email = True
                    elif email_associated_with_we_vote_id(email_address, incoming_we_vote_id):
                        # Currently this is always true. Do we want to do this check here, or during augmentation below?
                        save_email = True

                if save_email:
                    recipient_dict.update({
                        'email_address': email_address,
                    })
                    save_recipient = True

            save_recipient_object = False
            if save_recipient:
                try:
                    # Check to see if an EmailCampaignRecipient value exists that matches the email_campaign_id and
                    #  any of these other values with a "Q" query parameter:
                    #  email_address, voter_we_vote_id, or politician_we_vote_id
                    queryset = EmailCampaignRecipient.objects.filter(email_campaign_id=email_campaign_id)
                    queryset = queryset.filter(
                        Q(email_address=email_address) |
                        Q(voter_we_vote_id=incoming_we_vote_id) |
                        Q(politician_we_vote_id=incoming_we_vote_id)
                    )
                    # queryset = queryset.distinct()  # Is this necessary?
                    if queryset.count() > 0:
                        # This recipient already exists for this campaign
                        recipient_list = list(queryset)
                        recipient_object = recipient_list[0]
                        # Update existing recipient with new values from recipient_dict
                        for field_key, field_value in recipient_dict.items():
                            if field_key != 'email_campaign_id':  # Don't update the primary lookup field
                                if hasattr(recipient_object, field_key):
                                    setattr(recipient_object, field_key, field_value)
                        save_recipient_object = True
                        status += f"EmailCampaignRecipient updated. "
                    else:
                        # Create a new EmailCampaignRecipient object
                        recipient_object = EmailCampaignRecipient(**recipient_dict)
                        manually_added_recipients_found = True
                        save_recipient_object = True
                        status += f"New EmailCampaignRecipient added. "
                except Exception as e:
                    status += f"Error saving recipient: {str(e)}. "

            if save_recipient_object:
                # ##################################
                # Augment the recipient
                # If there is an email_address, but no voter_we_vote_id or politician_we_vote_id,
                #  try to find the voter or politician, in that order (voter first)
                #  NOTE: giving voter record matching preference seems like the right direction, but we might find that
                #  trying to match to politician before voter *might* make more sense.
                # If there is a voter_we_vote_id or politician_we_vote_id, but no email_address, find the email_address
                results = augment_email_campaign_recipient(
                    recipient_object,
                    campaignx_list_dict=campaignx_list_dict,
                    politicians_dict=politicians_dict,
                    sender_object=sender_object,
                    voters_dict=voters_dict)
                if results['success'] and results['save_changes']:
                    recipient_object = results['email_campaign_recipient']
                    status += results['status'] + "AUGMENTED_RECIPIENT_SUCCESS "
                    campaignx_list_dict = results['campaignx_list_dict']
                    politicians_dict = results['politicians_dict']
                    voters_dict = results['voters_dict']

                    recipient_object.save()
                    status += "SAVED_RECIPIENT_OBJECT_SUCCESS "
                else:
                    status += results['status'] + "AUGMENTED_RECIPIENT_FAILED "

                # And now remove this object from manually_added_recipients. Any manually_added_recipients entries
                #  that remain after this loop can be deleted from the database.
                if manually_added_recipients_found:
                    # Loop through the manually_added_recipients list and remove any EmailCampaignRecipient objects
                    #  from the list that match the current recipient_object, whether it be by email address,
                    #  voter_we_vote_id, or politician_we_vote_id.
                    for recipient in manually_added_recipients[:]:
                        if recipient.email_address == recipient_object.email_address or \
                                recipient.voter_we_vote_id == recipient_object.voter_we_vote_id or \
                                recipient.politician_we_vote_id == recipient_object.politician_we_vote_id:
                            manually_added_recipients.remove(recipient)
                            status += "REMOVED_RECIPIENT_FROM_LIST "

        if manually_added_recipients_found:
            # Any recipients still in the manually_added_recipients list should be deleted from the database
            for recipient in manually_added_recipients:
                recipient.delete()
                status += "REMOVED_RECIPIENT_FROM_DB "

    if positive_value_exists(send_button_clicked):
        # Prepare the EmailCampaignRecipients from the AudienceBuilder
        if positive_value_exists(audience_builder_id):
            from email_outbound.controllers_audience_builder import \
                generate_email_campaign_recipients_from_audience_builder
            # Here when we generate the campaign recipients from audience_builders, and we populate them with rich data
            generate_results = generate_email_campaign_recipients_from_audience_builder(
                audience_builder_id=audience_builder_id,
                email_campaign_id=email_campaign_id)
            status += generate_results['status']

        # Send the email
        from email_outbound.controllers_email_campaign import email_campaign_send
        send_results = email_campaign_send(email_campaign=email_campaign, email_campaign_id=email_campaign_id)
        emails_scheduled = send_results['emails_scheduled']
        status += send_results['status']

        if positive_value_exists(emails_scheduled):
            status += "EMAILS_SCHEDULED: " + str(emails_scheduled) + " "
            status += " Email sent! "
            messages.add_message(request, messages.SUCCESS, status)
            # email_campaign = send_results['email_campaign']
        else:
            messages.add_message(request, messages.ERROR, 'Error sending email: ' + status)
        redirect_url = reverse('email_outbound:email_campaign_edit') + \
            "?id=" + str(email_campaign_id) + \
            "&google_civic_election_id=" + str(google_civic_election_id) + \
            "&state_code=" + str(state_code)
    else:
        # Redirect back to edit page with the campaign ID
        redirect_url = reverse('email_outbound:email_campaign_edit') + \
            "?id=" + str(email_campaign_id) + \
            "&google_civic_election_id=" + str(google_civic_election_id) + \
            "&state_code=" + str(state_code)
    return HttpResponseRedirect(redirect_url)


@login_required
def email_campaign_edit_view(request):
    # Restrict access
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')
    campaign_id = request.GET.get('id', '')

    # generate uuid unique identifier to pre-save the attachments
    draft_uuid = uuid.uuid4()
    
    # Load existing campaign if editing
    campaign_recipients = []
    email_campaign = None
    emails_sent = False
    if campaign_id:
        try:
            email_campaign = EmailCampaign.objects.get(id=campaign_id)
            emails_sent = positive_value_exists(email_campaign.emails_sent)
            
            # Load recipients for this campaign who were manually added
            recipients = EmailCampaignRecipient.objects.filter(
                email_campaign_id=campaign_id,
                manually_added=True,
            )
            campaign_recipients = []
            for recipient in recipients:
                recipient_dict = {
                    'candidate_we_vote_id': recipient.candidate_we_vote_id
                    if positive_value_exists(recipient.candidate_we_vote_id) else '',
                    'email_address': recipient.email_address
                    if positive_value_exists(recipient.email_address) else '',
                    'email_campaign_id': recipient.email_campaign_id,
                    'organization_we_vote_id': recipient.organization_we_vote_id
                    if positive_value_exists(recipient.organization_we_vote_id) else '',
                    'politician_we_vote_id': recipient.politician_we_vote_id
                    if positive_value_exists(recipient.politician_we_vote_id) else '',
                    'recipient_full_name': recipient.recipient_full_name
                    if positive_value_exists(recipient.recipient_full_name) else '',
                    'voter_we_vote_id': recipient.voter_we_vote_id
                    if positive_value_exists(recipient.voter_we_vote_id) else '',
                }
                campaign_recipients.append(recipient_dict)

        except EmailCampaign.DoesNotExist:
            pass
    
    # Get list of saved campaigns
    saved_campaigns = EmailCampaign.objects.filter(deleted=False).order_by('-id')[:10]

    # Step 1: Get folders that are not deleted
    folder_queryset = EmailTemplateFolder.objects.filter(deleted=False, archived=False).order_by('email_template_name')

    # Get all valid folder IDs
    valid_folder_ids = list(folder_queryset.values_list('id', flat=True))

    # Step 2: Build a list of folders, each with its templates
    folder_tree = []
    for folder in folder_queryset:
        templates_in_folder = EmailTemplate.objects.filter(
            email_template_folder_id=folder.id,
            deleted=False,
            archived=False
        ).order_by('email_template_name')

        folder_tree.append({
            'node_value': folder.id,
            'node_name': folder.email_template_name,  # For template display
            'children': [
                {
                    'node_value': template.id,
                    'node_name': template.email_template_name,
                }
                for template in templates_in_folder
            ],
        })

    # Step 2b: Get templates without a folder (unfiled)
    # This includes templates with folder_id=0, NULL, or referencing non-existent folders
    unfiled_templates = EmailTemplate.objects.filter(
        deleted=False,
        archived=False
    ).filter(
        Q(email_template_folder_id__isnull=True) |
        Q(email_template_folder_id=0) |
        ~Q(email_template_folder_id__in=valid_folder_ids)
    ).order_by('email_template_name')

    # Always add unfiled section at the end (even if empty, so users know it exists)
    folder_tree.append(
        {
            'id': None,
            'folder_name': 'Unfiled',
            'children': [
                {
                    'node_value': template.id,
                    'node_name': template.email_template_name,
                }
                for template in unfiled_templates
            ],
        }
    )

    # Step 3: Pass data to template
    import json
    template_values = {
        'emails_sent':  emails_sent,
        'folder_tree': folder_tree,
        'google_civic_election_id': google_civic_election_id,
        'state_code': state_code,
        'email_campaign': email_campaign,
        'saved_campaigns': saved_campaigns,
        'campaign_recipients': json.dumps(campaign_recipients),
        'token_list': EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS,
        'draft_uuid': draft_uuid
    }

    return render(request, 'email_outbound/email_campaign_edit.html', template_values)


@login_required
def email_campaign_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    fields_changed = []
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')
    status = ''
    update_list = []
    draft_uuid = request.GET.get('draft_uuid', request.POST.get('draft_uuid', ''))

    # on cancel, delete unsaved attachments temporarily stored in s3
    # delete behavior: only delete from s3 if no other copies/references of attachment remain
    if draft_uuid:
        attachments = list(EmailAttachments.objects.filter(draft_uuid=draft_uuid))
        for att in attachments:
            att_s3_key = att.s3_key
            att_count = EmailAttachments.objects.filter(s3_key=att_s3_key).count()
            if att_count > 1:
                att.delete()
            elif att_count == 1:
                att.delete()
                delete_from_s3(key=att.s3_key)
            messages.success(request, "Attachment deleted")

    campaigns_queryset = EmailCampaign.objects.filter(deleted=False).order_by('-id')

    # Active tab: sent campaigns
    campaigns_sent = campaigns_queryset.filter(emails_sent=True)
    for campaign in campaigns_sent:
        # Refresh the recipient_count, bounce_count, and open_count for all sent campaigns
        refresh_results = refresh_email_campaign_data(campaign)
        if refresh_results['changes_made']:
            update_list.append(refresh_results['email_campaign'])
            fields_changed_temp = refresh_results['fields_changed']
            # Update the fields_changed list with any additional fields in fields_changed_temp
            fields_changed.extend(fields_changed_temp)

        if campaign.recipient_count and campaign.recipient_count > 0 and campaign.open_count:
            campaign.open_rate = round((campaign.open_count / campaign.recipient_count) * 100, 2)
        else:
            campaign.open_rate = None

    # Drafts tab: not yet sent
    campaigns_drafts = campaigns_queryset.filter(emails_sent=False)

    # Archived tab filter would go here:

    if len(update_list) > 0:
        # Do a bulk update of the changes made in the update_list of EmailCampaign objects
        try:
            EmailCampaign.objects.bulk_update(update_list, fields_changed)
            status += \
                "{campaign_updates_made:,} campaigns updated " \
                "".format(campaign_updates_made=len(update_list))
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 "ERROR with PositionEntered.objects.bulk_update: {e}, "
                                 "".format(e=e))

    template_values = {
        # 'election':                                 election,
        # 'election_list':                            election_list,
        'google_civic_election_id':                 google_civic_election_id,
        'state_code':                               state_code,
        # 'state_list':                               sorted_state_list,
        'campaigns_sent':                           campaigns_sent,
        'campaigns_drafts':                         campaigns_drafts,
        # 'campaigns_archived':                     campaigns_archived,
    }
    return render(request, 'email_outbound/email_campaign_list.html', template_values)


@login_required
def email_recipient_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    campaign_id = request.GET.get('id', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')
    status = ''

    email_campaign = EmailCampaign.objects.get(id=campaign_id)

    queryset = EmailCampaignRecipient.objects.filter(email_campaign_id=campaign_id)
    # Sort the recipients by "open_tracking_last_open". If that field doesn't have a date,
    #  then sort by "recipient_last_name"
    queryset = queryset.order_by(
        '-open_tracking_last_open',
        'recipient_last_name',
    )

    # Opened the email
    recipient_open_list = queryset.filter(open_tracking_count__gt=0)

    # Not opened yet
    recipient_not_opened_list = queryset.filter(open_tracking_count=0)

    # Bounced tab filter would go here:

    template_values = {
        'email_campaign':             email_campaign,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
        'recipient_open_list':      recipient_open_list,
        'recipient_not_opened_list': recipient_not_opened_list,
    }
    return render(request, 'email_outbound/email_recipient_list.html', template_values)


@login_required
def email_template_edit_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')
    email_template_id = request.GET.get('email_template_id', 0)
    default_folder_id = request.GET.get('default_email_template_folder_id', None)

    # generate unique identifier to temporarily attach attachments to before save
    draft_uuid = uuid.uuid4()

    # Load existing template if editing
    email_template = None
    if positive_value_exists(email_template_id):
        try:
            email_template = EmailTemplate.objects.get(id=email_template_id)
        except EmailTemplate.DoesNotExist:
            email_template = None

    selected_folder_id = None
    if email_template:
        selected_folder_id = email_template.email_template_folder_id
    elif default_folder_id:
        selected_folder_id = int(default_folder_id)

    # customization tokens

    messages_on_stage = get_messages(request)

    template_values = {
        # 'election':               election,
        # 'election_list':          election_list,
        'email_template':           email_template,
        'folder_list':              EmailTemplateFolder.objects.filter(deleted=False).order_by('email_template_name'),
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'selected_folder_id':       selected_folder_id,
        'state_code':               state_code,
        'token_list':               EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS,
        'draft_uuid':               draft_uuid,
        # 'state_list':             sorted_state_list,
    }
    return render(request, 'email_outbound/email_template_edit.html', template_values)
# Upload attachments to S3 temporarily to the draft uuid
# expects query params: draft UUID
@login_required
def attachment_upload_view(request) -> HttpResponse:
    draft_uuid = request.GET.get("draft_uuid") or request.POST.get("draft_uuid") or None

    if not draft_uuid:
        return HttpResponseBadRequest("draft_uuid is required")

    # POST
    print("no issues till here")
    files = request.FILES.getlist("attachments")
    if not files:
        return HttpResponseBadRequest("No files provided")

    created = []
    for f in files:
        if f.size and f.size > MAX_ATTACHMENT_BYTES:
            return HttpResponseBadRequest(f"File too large. Max is {MAX_ATTACHMENT_BYTES} bytes.")

        content_type = (getattr(f, "content_type", "") or "").strip()
        # print(f"no issues up to here as well {content_type}")
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            return HttpResponseBadRequest(f"Unsupported content type: {content_type}")

        # build s3 key
        key = build_s3_key(
            campaign_id=None,
            template_id=None,
            draft_uuid=draft_uuid,
            original_filename=f.name,
        )

        size_bytes = upload_fileobj_to_s3(
            fileobj=f,
            key=key,
            content_type=content_type,
        )

        # create attachment object with s3 key and other details
        att = EmailAttachments.objects.create(
            email_campaign=None,
            email_template=None,
            draft_uuid=draft_uuid,
            s3_key=key,
            original_name=f.name,
            content_type=content_type,
            file_size=size_bytes or int(f.size or 0),
        )

        created.append({
            "id": att.id,
            "name": att.original_name or f.name,
        })

    messages.success(request, "Attachment uploaded.")
    return JsonResponse({"ok": True, "attachments": created})

# delete attachments using attachment id
# delete from s3 only if 1 copy or referrence remains
@login_required
def attachment_delete_view(request, attachment_id: int) -> HttpResponse:
    att = get_object_or_404(EmailAttachments, id=attachment_id)
    att_s3_key = att.s3_key
    att_count = EmailAttachments.objects.filter(s3_key=att_s3_key).count()
    if att_count > 1:
        att.delete()
    elif att_count == 1:
        att.delete()
        delete_from_s3(key=att.s3_key)
    messages.success(request, "Attachment deleted.")
    # redirect back
    return JsonResponse({"ok": True, "deleted_id": attachment_id})

# download attachments using attachment id (using max preset file size vals)
@login_required
def attachment_download_view(request, attachment_id: int) -> StreamingHttpResponse:
    att = get_object_or_404(EmailAttachments, id=attachment_id)

    body = download_bytes_from_s3(key=att.s3_key)
    #
    resp = StreamingHttpResponse(body.iter_chunks(chunk_size=1024 * 512),
                                 content_type=att.content_type or "application/octet-stream")
    resp["Content-Disposition"] = f'attachment; filename="{att.original_name}"'
    return resp

# copy attachments from template to campaign
@login_required
def copy_attachments_to_campaign(request, template_id, campaign_id, draft_uuid):
    template_id = int(template_id) if template_id and template_id != 'null' else None
    campaign_id = int(campaign_id) if campaign_id and campaign_id != 'null' else None

    campaign = get_object_or_404(EmailCampaign, pk=campaign_id) if campaign_id else None
    template = get_object_or_404(EmailTemplate, pk=template_id) if template_id else None
    draft_uuid = None if draft_uuid == 'D_UUID' or draft_uuid == 'null' else draft_uuid

    attachments = []
    try:
        template_attachments = list(EmailAttachments.objects.filter(email_template=template))
        # delete old inline attachments on campaign when copying in new template
        if campaign_id:
            campaign_inline_attachments = list(EmailAttachments.objects.filter(email_campaign=campaign, is_inline=True))
            for c_att in campaign_inline_attachments:
                att_s3_key = c_att.s3_key
                att_count = EmailAttachments.objects.filter(s3_key=att_s3_key).count()
                if att_count > 1:
                    c_att.delete()
                elif att_count == 1:
                    c_att.delete()
                    delete_from_s3(key=c_att.s3_key)
                messages.success(request, "Attachment deleted.")

        # copy in new attachments from template to campaign
        if draft_uuid:
            for att in template_attachments:
                if not EmailAttachments.objects.filter(draft_uuid=draft_uuid, s3_key=att.s3_key).exists():
                    new_att = EmailAttachments.objects.create(
                        draft_uuid=draft_uuid,
                        email_template=None,
                        s3_key=att.s3_key,
                        original_name=att.original_name,
                        content_type=att.content_type,
                        file_size=att.file_size,
                        is_inline=att.is_inline,
                    )

                    attachments.append({
                        "id": new_att.id,
                        "name": new_att.original_name,
                        "is_inline": new_att.is_inline,
                    })
    except EmailAttachments.DoesNotExist:
        return JsonResponse({"ok": False, "attachments": attachments})

    return JsonResponse({"ok": True, "attachments": attachments})

# handle inline image upload
@login_required
def attachment_image_upload_view(request):
    draft_uuid = request.GET.get("draft_uuid") or request.POST.get("draft_uuid") or None

    if not draft_uuid:
        return HttpResponseBadRequest("campaign_id or template_id or draft_uuid is required")

    # POST
    print("no issues till here")
    f = request.FILES.get("file")
    print("are there files: ", f)
    if not f:
        return HttpResponseBadRequest("No files provided")

    if f.size and f.size > MAX_ATTACHMENT_BYTES:
        return HttpResponseBadRequest(f"File too large. Max is {MAX_ATTACHMENT_BYTES} bytes.")

    content_type = (getattr(f, "content_type", "") or "").strip()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        return HttpResponseBadRequest(f"Unsupported content type: {content_type}")

    print("at good files")
    key = build_s3_key(
        campaign_id=None,
        template_id=None,
        draft_uuid=draft_uuid,
        original_filename=f.name,
    )
    size_bytes = upload_fileobj_to_s3(
        fileobj=f,
        key=key,
        content_type=content_type,
    )
    att = EmailAttachments.objects.create(
        email_campaign=None,
        email_template=None,
        draft_uuid=draft_uuid,
        s3_key=key,
        original_name=f.name,
        content_type=content_type,
        file_size=size_bytes or int(f.size or 0),
        is_inline=True
    )

    messages.success(request, "Attachment uploaded.")

    render_url = reverse("email_outbound:email_attachment_render", kwargs={"attachment_id": att.id})

    return JsonResponse({
        "location": render_url,   # TinyMCE expects this
        "attachment_id": att.id
    })

# generate render view for inline attachment
@login_required
def attachment_render_view(request, attachment_id: int):
    att = get_object_or_404(EmailAttachments, id=attachment_id)

    raw = download_bytes_from_s3(key=att.s3_key)
    resp = HttpResponse(raw, content_type=att.content_type or "application/octet-stream")
    resp["Content-Disposition"] = f'inline; filename="{att.original_name}"'
    print('render url: ', resp)
    return resp

@login_required
def email_template_edit_process_view(request):
    """
    Process the new or edit template form
    :param request:
    :return:
    """
    # The performance_dict variable contains list(s) of performance_snapshots.
    performance_dict = {}
    # Set up performance_list for this view. A pointer to the performance_list variable is established here.
    #  Throughout the rest of this view, we add snapshots to the performance_list. Since the performance_list
    #  is "attached" to the performance_dict with a pointer, when we pass performance_dict to the template,
    #  the performance_list data is included.
    performance_list = []
    performance_dict.update({
        'email_template_edit_process_view': performance_list,
    })

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    email_template_name = request.POST.get('email_template_name', '').strip()
    subject = request.POST.get('subject', '').strip()
    message = request.POST.get('message', '').strip()
    folder_id = request.POST.get('folder', 0)
    email_template_id = request.POST.get('email_template_id', None)
    draft_uuid = request.POST.get('draft_uuid', None)
    email_template = None
    # if positive_value_exists(email_template_name):
    #     email_template_name = email_template_name.strip()
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    if folder_id == "null":
        folder_id = None

    try:
        if email_template_id and EmailTemplate.objects.filter(
            id=email_template_id,
            deleted=False,
        ).exists():
            email_template = EmailTemplate.objects.filter(
                id=email_template_id,
                deleted=False,
            ).first()
            email_template.email_template_name = email_template_name
            email_template.subject = subject
            email_template.message = message
            email_template.email_template_folder_id = folder_id
            email_template.save()
            status += "Existing template updated. "
        else:
            email_template = EmailTemplate.objects.create(
                email_template_name=email_template_name,
                subject=subject,
                message=message,
                email_template_folder_id=folder_id,
                deleted=False,
                archived=False,
            )
            email_template_id = email_template.id
            if email_template is not None:
                status += "New template created. "

        # on save, process attachments, move s3 key location, and mark them to respective template id
        if draft_uuid and email_template and email_template_id:
            with transaction.atomic():
                qs = EmailAttachments.objects.select_for_update().filter(
                    draft_uuid=draft_uuid,
                    email_campaign__isnull=True,
                    email_template__isnull=True,
                )
                for att in qs:
                    new_key = build_s3_key(
                        campaign_id=None,
                        template_id=int(email_template_id),
                        draft_uuid=None,
                        original_filename=att.original_name,
                    )
                    if EmailAttachments.objects.filter(s3_key=att.s3_key).count() == 1:
                        move_s3_object(old_key=att.s3_key, new_key=new_key)
                        att.s3_key = new_key
                    att.email_template = email_template
                    att.draft_uuid = None
                    att.save(update_fields=["s3_key", "email_template", "draft_uuid"])

        # clean up unused inline attachments that have been removed
        cleanup_unused_inline_attachments(html=message, email_template=email_template)

    except Exception as e:
        status += f"Error saving template: {e}"

    messages.add_message(request, messages.INFO, status)

    # Since a pointer to performance_list was attached to performance_dict above, the performance_list
    # data gets passed along within performance_dict. We pass this performance_dict
    # with the name 'performance_process_dict' so it is clear this is from a "process" view.
    performance_process_dict_encoded = urlencode({
        'performance_process_dict': json.dumps(performance_dict)
    })

    redirect_url = reverse(
        'email_outbound:email_template_list',
        args=()) + "?google_civic_election_id=" + str(google_civic_election_id) + \
        "&state_code=" + str(state_code) + "&" + performance_process_dict_encoded
    return HttpResponseRedirect(redirect_url)


@login_required
def email_template_list_process_view(request):
    """
    Process the email template list form (archive/delete operations)
    :param request:
    :return:
    """

    if request.method != "POST":
        return HttpResponseRedirect(reverse('email_outbound:email_template_list'))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    def back():
        return HttpResponseRedirect(
            f"{reverse('email_outbound:email_template_list')}"
            f"?google_civic_election_id={google_civic_election_id}&state_code={state_code}")

    action = request.POST.get("action", "").strip()

    try:
        if action == "create_folder":
            name = (request.POST.get("email_template_name") or "").strip()
            if not name:
                messages.error(request, "Folder name is required.")
                return back()
            exists = EmailTemplateFolder.objects.filter(
                deleted=False,
                email_template_name__iexact=name
            ).exists()
            if exists:
                err = f'A folder named "{name}" already exists.'
                messages.error(request, err)
                return back()
            EmailTemplateFolder.objects.create(email_template_name=name)
            messages.success(request, f"Folder “{name}” created.")
            return back()

        if action == "rename_folder":
            folder_id = request.POST.get("folder_id")
            new_name = (request.POST.get("edit_email_template_name") or "").strip()
            folder = EmailTemplateFolder.objects.get(id=folder_id, deleted=False)
            old = folder.email_template_name
            folder.email_template_name = new_name
            folder.save(update_fields=["email_template_name"])
            messages.success(request, f"Folder renamed from “{old}” to “{new_name}”.")
            return back()

        if action == "delete_folder":
            folder_id = request.POST.get("folder_id")
            folder = EmailTemplateFolder.objects.get(id=folder_id, deleted=False)
            # Move templates to Unfiled (NULL)
            EmailTemplate.objects.filter(email_template_folder_id=folder.id).update(email_template_folder_id=None)
            folder.deleted = True
            folder.archived = False
            folder.save(update_fields=["deleted", "archived"])
            messages.success(request, "Folder deleted. Templates moved to Unfiled.")
            return back()

        if action == "archive_folder":
            folder_id = request.POST.get("folder_id")
            folder = EmailTemplateFolder.objects.get(id=folder_id, deleted=False)
            folder.archived = True
            folder.save(update_fields=["archived"])
            messages.success(request, f"Folder “{folder.email_template_name}” archived.")
            return back()

        if action == "unarchive_folder":
            folder_id = request.POST.get("folder_id")
            folder = EmailTemplateFolder.objects.get(id=folder_id, deleted=False)
            folder.archived = False
            folder.save(update_fields=["archived"])
            messages.success(request, f"Folder “{folder.email_template_name}” unarchived.")
            return back()

        if action == "create_template":
            # Optionally pick a default folder for the new template (can be blank/unfiled)
            folder_id = request.POST.get("folder_id")
            # Redirect to template edit page (creation flow)
            edit_url = reverse("email_outbound:email_template_edit")
            qs = f"?google_civic_election_id={google_civic_election_id}&state_code={state_code}"
            if folder_id and folder_id != "null":
                qs += f"&default_email_template_folder_id={folder_id}"
            return HttpResponseRedirect(edit_url + qs)

        if action == "change_template_folder":
            template_id = request.POST.get("template_id")
            new_folder_id = request.POST.get("new_folder_id")  # can be "null"
            tmpl = EmailTemplate.objects.get(id=template_id, deleted=False)
            if new_folder_id == "null" or new_folder_id == "":
                tmpl.email_template_folder_id = None
            else:
                folder = EmailTemplateFolder.objects.get(id=new_folder_id, deleted=False)
                tmpl.email_template_folder_id = folder.id
            tmpl.save(update_fields=["email_template_folder_id"])
            messages.success(request, "Template moved.")
            return back()

        if action == "archive_template":
            template_id = request.POST.get("template_id")
            tmpl = EmailTemplate.objects.get(id=template_id, deleted=False)
            tmpl.archived = True
            tmpl.save(update_fields=["archived"])
            messages.success(request, f"Template “{tmpl.email_template_name}” archived.")
            return back()

        if action == "unarchive_template":
            template_id = request.POST.get("template_id")
            tmpl = EmailTemplate.objects.get(id=template_id, deleted=False)
            tmpl.archived = False
            tmpl.save(update_fields=["archived"])
            messages.success(request, f"Template “{tmpl.email_template_name}” unarchived.")
            return back()

        if action == "delete_template":
            # delete templates attached to template as well
            template_id = request.POST.get("template_id")

            with transaction.atomic():
                tmpl = get_object_or_404(EmailTemplate, id=template_id, deleted=False)
                tmpl.deleted = True
                tmpl.email_template_folder_id = None
                tmpl.save(update_fields=["deleted", "email_template_folder_id"])

                # select and lock attachment rows for this template
                attachments = list(
                    EmailAttachments.objects.select_for_update()
                    .filter(email_template=tmpl)
                )

                # get S3 keys
                keys_to_maybe_delete = []
                for att in attachments:
                    key = att.s3_key  # if you store it
                    keys_to_maybe_delete.append(key)
                    att.delete()

            # Outside transaction: delete from S3 only if no refs remain
            for key in keys_to_maybe_delete:
                still_used = EmailAttachments.objects.filter(s3_key=key).exists()
                if not still_used:
                    delete_from_s3(key=key)

            messages.success(request, "Template deleted.")
            return back()

        messages.error(request, "Unknown action.")
        return back()

    except EmailTemplateFolder.DoesNotExist:
        messages.error(request, "Folder not found.")
        return back()
    except EmailTemplate.DoesNotExist:
        messages.error(request, "Template not found.")
        return back()
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return back()


@login_required
def email_template_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id',
                                               request.POST.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', request.POST.get('state_code', ''))
    draft_uuid = request.GET.get('draft_uuid', request.POST.get('draft_uuid', ''))

    # Folders
    folder_qs = EmailTemplateFolder.objects.filter(deleted=False)
    folders_active = folder_qs.filter(archived=False).order_by('email_template_name')
    folders_archived = folder_qs.filter(archived=True).order_by('email_template_name')

    # Templates
    template_qs = EmailTemplate.objects.filter(deleted=False)
    templates_active = template_qs.filter(archived=False).order_by('email_template_name')
    templates_archived = template_qs.filter(archived=True).order_by('email_template_name')

    # delete unsaved attachments temporarily stored on cancel
    if draft_uuid:
        attachments = list(EmailAttachments.objects.filter(draft_uuid=draft_uuid))
        for att in attachments:
            att_s3_key = att.s3_key
            att_count = EmailAttachments.objects.filter(s3_key=att_s3_key).count()
            if att_count > 1:
                att.delete()
            elif att_count == 1:
                att.delete()
                delete_from_s3(key=att.s3_key)
            messages.success(request, "Attachment deleted")

    # Map active templates by folder id
    templates_by_folder = {}
    for t in templates_active:
        fid = t.email_template_folder_id  # None means "Unfiled"
        templates_by_folder.setdefault(fid, []).append(t)

    unfiled_templates = templates_by_folder.get(None, [])

    # Map folder id to folder name
    all_folders_by_id = {}
    for folder in folder_qs:
        all_folders_by_id[folder.id] = folder.email_template_name

    context = {
        "google_civic_election_id": google_civic_election_id,
        "state_code": state_code,

        # Groupings for UI
        "all_folders_by_id": all_folders_by_id,
        "folders_active": folders_active,
        "folders_archived": folders_archived,
        "templates_by_folder": templates_by_folder,  # keyed by folder id (None for Unfiled)
        "unfiled_templates": unfiled_templates,
        "archived_templates": templates_archived,

        # URLs
        "process_url": reverse('email_outbound:email_template_list_process'),
        "template_edit_url": reverse('email_outbound:email_template_edit'),
    }
    # messages.add_message(request, messages.INFO, '')
    return render(request, "email_outbound/email_template_list.html", context)


def audience_builder_drawer_html_view(request):
    """
    Returns HTML fragment for the audience builder drawer
    """
    status = ""
    success = True

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return JsonResponse({'success': False, 'status': 'PERMISSION_DENIED'}, status=403)

    audience_builder_id = request.POST.get('audience_builder_id', request.GET.get('audience_builder_id', None))
    audience_builder_name = ''

    results = audience_builder_data_retrieve(audience_builder_id)
    status += results['status']

    if results['success']:
        audience_builder = results['audience_builder']
        if hasattr(audience_builder, 'audience_builder_name'):
            audience_builder_name = audience_builder.audience_builder_name
        audience_filter_chain_dict = results['audience_filter_chain_dict']
        audience_filter_dict = results['audience_filter_dict']

        html_results = render_audience_builder_html(
            audience_builder=audience_builder,
            audience_filter_chain_dict=audience_filter_chain_dict,
            audience_filter_dict=audience_filter_dict,
            request=request,
        )

        if html_results['success']:
            return JsonResponse({
                'audience_builder_id': audience_builder_id,
                'audience_builder_name': audience_builder_name,
                'html': html_results['audience_builder_html'],
                'status': html_results['status'],
                'success': True,
            })
        else:
            return JsonResponse({
                'audience_builder_id': audience_builder_id,
                'audience_builder_name': audience_builder_name,
                'html': '',
                'status': html_results['status'],
                'success': False,
            }, status=500)
    else:
        return JsonResponse({
            'audience_builder_id': audience_builder_id,
            'audience_builder_name': audience_builder_name,
            'html': '',
            'status': status,
            'success': False,
        }, status=500)


def audience_builder_drawer_preview_html_view(request):
    """
    Returns HTML fragment for the preview shown in the audience builder drawer
    """
    status = ""
    success = True

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return JsonResponse({'success': False, 'status': 'PERMISSION_DENIED'}, status=403)

    audience_builder_id = request.POST.get('audience_builder_id', request.GET.get('audience_builder_id', None))
    audience_builder_name = ''

    results = audience_builder_data_retrieve(audience_builder_id)
    status += results['status']

    if results['success']:
        audience_builder = results['audience_builder']
        if hasattr(audience_builder, 'audience_builder_name'):
            audience_builder_name = audience_builder.audience_builder_name
        audience_filter_chain_dict = results['audience_filter_chain_dict']
        audience_filter_dict = results['audience_filter_dict']

        html_results = render_audience_builder_preview_html(
            audience_builder=audience_builder,
            audience_filter_chain_dict=audience_filter_chain_dict,
            audience_filter_dict=audience_filter_dict,
            request=request,
        )

        if html_results['success']:
            return JsonResponse({
                'audience_builder_id': audience_builder_id,
                'audience_builder_name': audience_builder_name,
                'html': html_results['audience_builder_preview_html'],
                'status': html_results['status'],
                'success': True,
            })
        else:
            return JsonResponse({
                'audience_builder_id': audience_builder_id,
                'audience_builder_name': audience_builder_name,
                'html': '',
                'status': html_results['status'],
                'success': False,
            }, status=500)
    else:
        return JsonResponse({
            'audience_builder_id': audience_builder_id,
            'audience_builder_name': audience_builder_name,
            'html': '',
            'status': status,
            'success': False,
        }, status=500)


@login_required
def audience_builder_edit_view(request):
    """

    """
    audience_builder = {}
    audience_builder_html = ''
    audience_filter_chain_dict = {}
    audience_filter_dict = {}
    status = ""
    success = True
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    audience_builder_id = request.GET.get('audience_builder_id', request.POST.get('audience_builder_id', None))
    google_civic_election_id = request.GET.get('google_civic_election_id',
                                               request.POST.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', request.POST.get('state_code', ''))

    results = audience_builder_data_retrieve(audience_builder_id)
    status += results['status']
    if results['success']:
        audience_builder = results['audience_builder']
        audience_filter_chain_dict = results['audience_filter_chain_dict']
        audience_filter_dict = results['audience_filter_dict']
    else:
        audience_builder_id = None
        messages.add_message(request, messages.ERROR, status)
        success = False

    if success:
        results = render_audience_builder_html(
            audience_builder=audience_builder,
            audience_filter_chain_dict=audience_filter_chain_dict,
            audience_filter_dict=audience_filter_dict,
            request=request,
        )
        status += results['status']
        if results['success']:
            audience_builder_html = results['audience_builder_html']
        else:
            messages.add_message(request, messages.ERROR, status)

    messages_on_stage = get_messages(request)
    context = {
        'audience_builder':         audience_builder,
        'audience_builder_id':      audience_builder_id,
        'audience_builder_html':    audience_builder_html,
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'process_url':              reverse('email_outbound:audience_builder_edit_process'),
        'state_code':               state_code,
        'status':                   status,
        'audience_builder_edit_url':        reverse('email_outbound:audience_builder_list'),
    }
    return render(request, "email_outbound/audience_builder_edit.html", context)


@login_required
def audience_builder_edit_process_view(request):
    """
    Process the audience builder form
    :param request:
    :return:
    """
    status = ''
    success = True
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    audience_builder = None
    audience_builder_id = request.POST.get('audience_builder_id', request.GET.get('audience_builder_id', None))
    audience_builder_name = request.POST.get('audience_builder_name', request.GET.get('audience_builder_name', False))
    audience_filter_chain = None
    google_civic_election_id = \
        request.POST.get('google_civic_election_id', request.GET.get('google_civic_election_id', 0))
    state_code = request.POST.get('state_code', request.GET.get('state_code', ''))

    action = request.POST.get("action", request.GET.get("action", "")).strip()

    try:
        if action == "delete":
            audience_builder = AudienceBuilder.objects.get(id=audience_builder_id, deleted=False)
            audience_builder.deleted = True
            audience_builder.save()
            status += "Audience Builder deleted."
            success = True
        else:
            try:
                if positive_value_exists(audience_builder_id):
                    audience_builder = AudienceBuilder.objects.get(id=audience_builder_id)
                    if audience_builder_name is not False:
                        audience_builder.audience_builder_name = audience_builder_name
                    audience_builder.save()
                    status += "Audience Builder updated successfully."
                else:
                    audience_builder = AudienceBuilder.objects.create(
                        audience_builder_name=audience_builder_name)
                    audience_builder_id = audience_builder.id
                    status += f"New audience builder created: '{audience_builder_name}'"
                success = True
            except Exception as e:
                messages.error(request, f"Error creating new template: {str(e)}")
                success = False

    except AudienceBuilder.DoesNotExist:
        status += "Audience Builder not found."
        success = False
    except Exception as e:
        status += f"Error: {e}"
        success = False

    audience_filter_chain_dict = {}
    audience_filter_dict = {}
    # Get all existing AudienceBuilder data including children (AudienceFilterChain and their AudienceFilter children)
    if success and positive_value_exists(audience_builder_id):
        results = audience_builder_data_retrieve(audience_builder_id)
        status += results['status']
        if results['success']:
            audience_builder = results['audience_builder']
            audience_filter_chain_dict = results['audience_filter_chain_dict']
            audience_filter_dict = results['audience_filter_dict']
        else:
            success = False
            status += "ERROR_RETRIEVING_DATA "

    # Make sure we have at least one AudienceFilterChain and AudienceFilter for this AudienceBuilder
    if success and hasattr(audience_builder, 'audience_filter_chain1_id'):
        # If audience_filter_chain_dict is empty, create a default AudienceFilterChain
        if not audience_filter_chain_dict:
            audience_filter_chain, created = AudienceFilterChain.objects.update_or_create(
                audience_builder_id=audience_builder_id)
            if created:
                audience_filter_chain_dict = {audience_filter_chain.id: audience_filter_chain}
                audience_builder.audience_filter_chain1_id = audience_filter_chain.id
                audience_builder.save()

        # If audience_filter_dict is empty, create a default AudienceFilter
        if not audience_filter_dict and hasattr(audience_filter_chain, 'filter1_id'):
            audience_filter, created = AudienceFilter.objects.update_or_create(
                audience_builder_id=audience_builder_id)
            if created:
                audience_filter_dict = {audience_filter.id: audience_filter}
                audience_filter_chain.filter1_id = audience_filter.id
                audience_filter_chain.save()

    # If an "Add new" button was pressed under AudienceFilterChain, create new AudienceFilterChain
    #  and initial AudienceFilter
    for builder_relative_chain_id in range(1, 10):
        next_filter_chain_found = False
        if builder_relative_chain_id < 9:
            ok_to_create_next_chain = True
        else:
            ok_to_create_next_chain = False
        next_builder_relative_chain_id = builder_relative_chain_id + 1
        next_chain_position_id_attribute = f'audience_filter_chain{next_builder_relative_chain_id}_id'
        next_chain_id = getattr(audience_builder, next_chain_position_id_attribute, None)

        if positive_value_exists(next_chain_id):
            if next_chain_id in audience_filter_chain_dict:
                next_filter_chain_found = True
        if ok_to_create_next_chain and not next_filter_chain_found:
            # Here we don't have to specify the chain_id because we are just dealing with the list of 9 chains
            add_audience_filter_chain_key = f'add_audience_filter_chain_after_filter{builder_relative_chain_id}'
            add_audience_filter_chain = \
                request.POST.get(add_audience_filter_chain_key,
                                 request.GET.get(add_audience_filter_chain_key, False))
            if positive_value_exists(add_audience_filter_chain):
                audience_filter_chain = AudienceFilterChain.objects.create(
                    audience_builder_id=audience_builder_id)
                audience_filter_chain_dict[audience_filter_chain.id] = audience_filter_chain
                next_builder_relative_chain_id = builder_relative_chain_id + 1
                # Keep track of the chain id in the audience_builder
                chain_id_attribute = f'audience_filter_chain{next_builder_relative_chain_id}_id'
                setattr(audience_builder, chain_id_attribute, audience_filter_chain.id)
                # Add the chain_to_chain operator to the audience_builder
                operator_attribute = \
                    f'chain{builder_relative_chain_id}_to_chain{next_builder_relative_chain_id}_operator'
                setattr(audience_builder, operator_attribute, OPERATOR_OR)
                audience_builder.save()

                # Now create new AudienceFilter and link it to the chain
                audience_filter = AudienceFilter.objects.create(
                    audience_builder_id=audience_builder_id)
                audience_filter_dict[audience_filter.id] = audience_filter
                # Now link the new filter to the first spot in the chain
                audience_filter_id_attribute = f'filter1_id'
                setattr(audience_filter_chain, audience_filter_id_attribute, audience_filter.id)
                audience_filter_chain.save()

    # If an "Add new" button was pressed under an AudienceFilter, create new AudienceFilter
    # builder_relative_chain_id is the order of the chain in the audience_builder object
    for builder_relative_chain_id in range(1, 10):
        # For example, "audience_builder.audience_filter_chain1_id" contains the unique ID of the AudienceFilterChain
        #  this is positioned in the first "AudienceFilterChain" linked to the audience_builder object
        builder_relative_chain_id_attribute = f'audience_filter_chain{builder_relative_chain_id}_id'
        chain_id = getattr(audience_builder, builder_relative_chain_id_attribute, None)
        if positive_value_exists(chain_id):
            audience_filter_chain = audience_filter_chain_dict.get(chain_id, None)
            if hasattr(audience_filter_chain, 'filter1_id'):
                for filter_position_in_chain in range(1, 10):
                    add_audience_filter_key = \
                        f'add_audience_filter_after_filter{filter_position_in_chain}_for_chain_{chain_id}'
                    add_audience_filter = \
                        request.POST.get(add_audience_filter_key,
                                         request.GET.get(add_audience_filter_key, False))
                    if positive_value_exists(add_audience_filter):
                        try:
                            audience_filter = AudienceFilter.objects.create(
                                audience_builder_id=audience_builder_id)
                            audience_filter_dict[audience_filter.id] = audience_filter
                            # Now link the new filter to the chain
                            audience_filter_id_attribute = f'filter{filter_position_in_chain + 1}_id'
                            setattr(audience_filter_chain, audience_filter_id_attribute, audience_filter.id)
                            # Add the chain_to_chain operator to the audience_builder
                            if filter_position_in_chain < 9:
                                filter_to_filter_operator_attribute = \
                                    f'filter{filter_position_in_chain}_to_filter{filter_position_in_chain + 1}_operator'
                                setattr(audience_filter_chain, filter_to_filter_operator_attribute, OPERATOR_AND)
                            audience_filter_chain.save()
                            audience_filter_chain_dict[chain_id] = audience_filter_chain
                        except Exception as e:
                            status += f"ERROR_CREATING_FILTER: {str(e)} "

    # If "Delete" button was pressed for AudienceFilter
    audience_filter_id_to_delete = \
        request.POST.get('audience_filter_id_to_delete',
                         request.GET.get('audience_filter_id_to_delete', False))
    if positive_value_exists(audience_filter_id_to_delete):
        from email_outbound.controllers_email_campaign import delete_audience_filter
        delete_results = delete_audience_filter(audience_filter_id_to_delete=audience_filter_id_to_delete)
        if delete_results['success']:
            status += delete_results['status']
        else:
            status += delete_results['status']

    # If "Delete" button was pressed for AudienceFilterChain
    audience_filter_chain_id_to_delete = \
        request.POST.get('audience_filter_chain_id_to_delete',
                         request.GET.get('audience_filter_chain_id_to_delete', False))
    if positive_value_exists(audience_filter_chain_id_to_delete):
        from email_outbound.controllers_email_campaign import delete_audience_filter_chain_and_children
        delete_results = delete_audience_filter_chain_and_children(audience_builder, audience_filter_chain_id_to_delete)
        if delete_results['success']:
            status += delete_results['status']

            # Reorganize the remaining chains to remove gaps
            from email_outbound.controllers_email_campaign import reorganize_audience_filter_chains
            reorganize_results = reorganize_audience_filter_chains(audience_builder)
            if reorganize_results['success'] and reorganize_results['changes_made']:
                status += "Filter chains reorganized successfully."
            elif not reorganize_results['success']:
                status += f"Chain deleted but reorganization had issues: {reorganize_results['status']}"
        else:
            status += delete_results['status']

    # Now save any AudienceFilter changes
    from email_outbound.controllers_email_campaign import save_all_audience_filter_changes
    save_results = save_all_audience_filter_changes(audience_filter_dict=audience_filter_dict, request=request)
    if not save_results['success']:
        status += "Audience filters NOT saved."

    # If this is an AJAX request, return JSON with updated HTML
    audience_builder_name = 'Loading...'
    if is_ajax:
        results = audience_builder_data_retrieve(audience_builder_id)
        status += results['status']
        if results['success']:
            audience_builder = results['audience_builder']
            audience_builder_name = audience_builder.audience_builder_name
            audience_filter_chain_dict = results['audience_filter_chain_dict']
            audience_filter_dict = results['audience_filter_dict']
        else:
            audience_builder_id = None
            success = False

        if success:
            # Render the updated HTML
            html_results = render_audience_builder_html(
                audience_builder=audience_builder,
                audience_filter_chain_dict=audience_filter_chain_dict,
                audience_filter_dict=audience_filter_dict,
                request=request,
            )

            if html_results['success']:
                return JsonResponse({
                    'audience_builder_id':      audience_builder_id,
                    'audience_builder_name':    audience_builder_name,
                    'html':                     html_results['audience_builder_html'],
                    'status':                   status,
                    'success':                  True,
                })
            else:
                return JsonResponse({
                    'audience_builder_id':      audience_builder_id,
                    'audience_builder_name':    audience_builder_name,
                    'html': '',
                    'status': status + html_results['status'],
                    'success': False,
                }, status=500)
        else:
            return JsonResponse({
                'audience_builder_id': audience_builder_id,
                'audience_builder_name': audience_builder_name,
                'html': '',
                'status': status,
                'success': False,
            }, status=400)

    # For non-AJAX requests, redirect as before
    messages.add_message(request, messages.SUCCESS if success else messages.ERROR, status)
    return HttpResponseRedirect(reverse('email_outbound:audience_builder_edit') +
                                "?audience_builder_id=" + str(audience_builder_id) +
                                "&google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def audience_builder_list_process_view(request):
    """
    Process the audience builder list form (archive/delete operations)
    :param request:
    :return:
    """

    if request.method != "POST":
        return HttpResponseRedirect(reverse('email_outbound:audience_builder_list'))

    audience_builder_id = None
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    def back():
        return HttpResponseRedirect(
            f"{reverse('email_outbound:audience_builder_list')}?google_civic_election_id={google_civic_election_id}&state_code={state_code}")

    action = request.POST.get("action", "").strip()

    try:
        if action == "create_folder":
            name = (request.POST.get("audience_builder_name") or "").strip()
            if not name:
                messages.error(request, "Folder name is required.")
                return back()
            exists = AudienceBuilderFolder.objects.filter(
                deleted=False,
                audience_builder_name__iexact=name
            ).exists()
            if exists:
                err = f'A folder named "{name}" already exists.'
                messages.error(request, err)
                return back()
            AudienceBuilderFolder.objects.create(audience_builder_name=name)
            messages.success(request, f"Folder “{name}” created.")
            return back()

        if action == "rename_folder":
            folder_id = request.POST.get("folder_id")
            new_name = (request.POST.get("edit_audience_builder_name") or "").strip()
            folder = AudienceBuilderFolder.objects.get(id=folder_id, deleted=False)
            old = folder.audience_builder_name
            folder.audience_builder_name = new_name
            folder.save(update_fields=["audience_builder_name"])
            messages.success(request, f"Folder renamed from “{old}” to “{new_name}”.")
            return back()

        if action == "delete_folder":
            folder_id = request.POST.get("folder_id")
            folder = AudienceBuilderFolder.objects.get(id=folder_id, deleted=False)
            # Move templates to Unfiled (NULL)
            AudienceBuilder.objects.filter(audience_builder_folder_id=folder.id).update(audience_builder_folder_id=None)
            folder.deleted = True
            folder.archived = False
            folder.save(update_fields=["deleted", "archived"])
            messages.success(request, "Folder deleted. Audience Builders moved to Unfiled.")
            return back()

        if action == "archive_folder":
            folder_id = request.POST.get("folder_id")
            folder = AudienceBuilderFolder.objects.get(id=folder_id, deleted=False)
            folder.archived = True
            folder.save(update_fields=["archived"])
            messages.success(request, f"Folder “{folder.audience_builder_name}” archived.")
            return back()

        if action == "unarchive_folder":
            folder_id = request.POST.get("folder_id")
            folder = AudienceBuilderFolder.objects.get(id=folder_id, deleted=False)
            folder.archived = False
            folder.save(update_fields=["archived"])
            messages.success(request, f"Folder “{folder.audience_builder_name}” unarchived.")
            return back()

        if action == "create_audience_builder":
            # Optionally pick a default folder for the new template (can be blank/unfiled)
            folder_id = request.POST.get("folder_id")
            # Redirect to template edit page (creation flow)
            edit_url = reverse("email_outbound:audience_builder_edit_process")
            # if modal is used for audience builder edit then ignore this link
            # else link to appropriate view
            qs = f"?google_civic_election_id={google_civic_election_id}&state_code={state_code}"
            if folder_id and folder_id != "null":
                qs += f"&default_audience_builder_folder_id={folder_id}"

            audience_builder_name = f"Audience Builder {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                new_audience_builder, created = AudienceBuilder.objects.update_or_create(
                    audience_builder_name=audience_builder_name)
                audience_builder_id = new_audience_builder.id
            except Exception as e:
                messages.error(request, f"Error creating new template: {str(e)}")
                return back()

            if created:
                messages.success(request, f"New template created: “{audience_builder_name}”")
                if positive_value_exists(audience_builder_id):
                    qs += f"&audience_builder_id={audience_builder_id}"

            return HttpResponseRedirect(edit_url + qs)

        if action == "change_audience_builder_folder":
            audience_builder_id = request.POST.get("audience_builder_id")
            new_folder_id = request.POST.get("new_folder_id")  # can be "null"
            tmpl = AudienceBuilder.objects.get(id=audience_builder_id, deleted=False)
            if new_folder_id == "null" or new_folder_id == "":
                tmpl.audience_builder_folder_id = None
            else:
                folder = AudienceBuilderFolder.objects.get(id=new_folder_id, deleted=False)
                tmpl.audience_builder_folder_id = folder.id
            tmpl.save(update_fields=["audience_builder_folder_id"])
            messages.success(request, "Audience Builder moved.")
            return back()

        if action == "archive_audience_builder":
            audience_builder_id = request.POST.get("audience_builder_id")
            tmpl = AudienceBuilder.objects.get(id=audience_builder_id, deleted=False)
            tmpl.archived = True
            tmpl.save(update_fields=["archived"])
            messages.success(request, f"Audience Builder “{tmpl.audience_builder_name}” archived.")
            return back()

        if action == "unarchive_audience_builder":
            audience_builder_id = request.POST.get("audience_builder_id")
            tmpl = AudienceBuilder.objects.get(id=audience_builder_id, deleted=False)
            tmpl.archived = False
            tmpl.save(update_fields=["archived"])
            messages.success(request, f"Audience Builder “{tmpl.audience_builder_name}” unarchived.")
            return back()

        if action == "delete_audience_builder":
            audience_builder_id = request.POST.get("audience_builder_id")
            tmpl = AudienceBuilder.objects.get(id=audience_builder_id, deleted=False)
            tmpl.deleted = True
            tmpl.audience_builder_folder_id = None
            tmpl.save(update_fields=["deleted", "audience_builder_folder_id"])
            messages.success(request, "Audience Builder deleted.")
            return back()

        messages.error(request, "Unknown action.")
        return back()

    except AudienceBuilderFolder.DoesNotExist:
        messages.error(request, "Folder not found.")
        return back()
    except AudienceBuilder.DoesNotExist:
        messages.error(request, "Audience Builder not found.")
        return back()
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return back()


@login_required
def audience_builder_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id',
                                               request.POST.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', request.POST.get('state_code', ''))

    # Folders
    folder_qs = AudienceBuilderFolder.objects.filter(deleted=False)
    folders_active = folder_qs.filter(archived=False).order_by('audience_builder_name')
    folders_archived = folder_qs.filter(archived=True).order_by('audience_builder_name')

    # Audience Builders
    audience_builder_qs = AudienceBuilder.objects.filter(deleted=False)
    audience_builders_active = audience_builder_qs.filter(archived=False).order_by('audience_builder_name')
    audience_builders_archived = audience_builder_qs.filter(archived=True).order_by('audience_builder_name')

    # Map active templates by folder id
    audience_builders_by_folder = {}
    for t in audience_builders_active:
        fid = t.audience_builder_folder_id  # None means "Unfiled"
        audience_builders_by_folder.setdefault(fid, []).append(t)

    unfiled_audience_builders = audience_builders_by_folder.get(None, [])

    # Map folder id to folder name
    all_folders_by_id = {}
    for folder in folder_qs:
        all_folders_by_id[folder.id] = folder.audience_builder_name

    context = {
        "google_civic_election_id": google_civic_election_id,
        "state_code": state_code,

        # Groupings for UI
        "all_folders_by_id": all_folders_by_id,
        "folders_active": folders_active,
        "folders_archived": folders_archived,
        "audience_builders_by_folder": audience_builders_by_folder,  # keyed by folder id (None for Unfiled)
        "unfiled_audience_builders": unfiled_audience_builders,
        "archived_audience_builders": audience_builders_archived,

        # URLs
        "process_url": reverse('email_outbound:audience_builder_list_process'),
        "audience_builder_edit_url": reverse('email_outbound:audience_builder_edit'),
    }
    # messages.add_message(request, messages.INFO, '')
    return render(request, "email_outbound/audience_builder_list.html", context)


@login_required
def email_template_content_view(request):
    """
    API endpoint to fetch template content
    """
    template_id = request.GET.get('template_id', '')
    
    try:
        template = EmailTemplate.objects.get(id=template_id)
        return JsonResponse({
            'success': True,
            'subject': template.subject or '',
            'message': template.message or '',
        })
    except EmailTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)


@login_required
def email_recipient_view(request, email_recipient_id=0):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')
    status = ''

    email_recipient = EmailCampaignRecipient.objects.get(id=email_recipient_id)
    email_body_assembled = email_recipient.email_body_assembled
    if email_body_assembled:
        try:
            # We want to search for this pattern "/apis/v1/opened/hcRlYMGJCK4yZuz/" in email_body_assembled,
            #  where hcRlYMGJCK4yZuz could be any random string, and then remove that final random string.
            # This serves the purpose of NOT marking the email as opened when we view it in our admin tools.
            email_body_assembled = re.sub(r'/apis/v1/opened/[a-zA-Z0-9]+/', '/apis/v1/opened/DONOTTRACK/',
                                          email_body_assembled)
        except Exception as e:
            email_body_assembled = email_recipient.email_body_assembled
            status += "ERROR_SUBSTITUTING_EMAIL_BODY_ASSEMBLED: " + str(e) + " "

    template_values = {
        'email_body_assembled':     email_body_assembled,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
    }
    return render(request, 'email_outbound/view_recipient_email.html', template_values)
