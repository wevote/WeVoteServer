# email_outbound/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .functions import merge_message_content_with_template
from .models import EmailManager, EmailScheduled, GENERIC_EMAIL_TEMPLATE, VERIFY_EMAIL_ADDRESS_TEMPLATE
from config.base import get_environment_variable
import json
from validate_email import validate_email
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")


def schedule_email_with_email_outbound_description(email_outbound_description):
    email_manager = EmailManager()

    template_variables_in_json = email_outbound_description.template_variables_in_json
    if positive_value_exists(email_outbound_description.kind_of_email_template):
        kind_of_email_template = email_outbound_description.kind_of_email_template
    else:
        kind_of_email_template = GENERIC_EMAIL_TEMPLATE

    email_template_results = merge_message_content_with_template(kind_of_email_template, template_variables_in_json)
    if email_template_results['success']:
        subject = email_template_results['subject']
        message_text = email_template_results['message_text']
        message_html = email_template_results['message_html']
        schedule_email_results = email_manager.schedule_email(email_outbound_description, subject, message_text, message_html)
        success = schedule_email_results['success']
        status = schedule_email_results['status']
        email_scheduled_saved = schedule_email_results['email_scheduled_saved']
        email_scheduled = schedule_email_results['email_scheduled']
        email_scheduled_id = schedule_email_results['email_scheduled_id']
    else:
        success = False
        status = "SCHEDULE_EMAIL_TEMPLATE_NOT_PROCESSED"
        email_scheduled_saved = False
        email_scheduled = EmailScheduled()
        email_scheduled_id = 0

    results = {
        'success': success,
        'status': status,
        'email_scheduled_saved': email_scheduled_saved,
        'email_scheduled_id': email_scheduled_id,
        'email_scheduled': email_scheduled,
    }
    return results


def schedule_verification_email(sender_voter_we_vote_id, recipient_voter_we_vote_id,
                                recipient_email_we_vote_id, recipient_voter_email,
                                recipient_email_address_secret_key, verification_context=None):
    """
    When a voter adds a new email address for self, create and send an outbound email with a link
    that the voter can click to verify the email.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param recipient_email_address_secret_key:
    :param verification_context: We tell the voter the context in which the verification was triggered
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = VERIFY_EMAIL_ADDRESS_TEMPLATE

    subject = "Please verify your email"

    template_variables_for_json = {
        "subject":                      subject,
        "recipient_voter_email":        recipient_voter_email,
        "we_vote_url":                  WEB_APP_ROOT_URL,
        "verify_email_url":
            WEB_APP_ROOT_URL + "/more/sign_in?verify_key=" + recipient_email_address_secret_key,
        "recipient_unsubscribe_url":    WEB_APP_ROOT_URL + "/unsubscribe?email_key=1234",
        "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    verification_from_email = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id, verification_from_email, recipient_voter_we_vote_id,
        recipient_email_we_vote_id, recipient_voter_email,
        template_variables_in_json, kind_of_email_template)
    status += outbound_results['status'] + " "
    if outbound_results['email_outbound_description_saved']:
        email_outbound_description = outbound_results['email_outbound_description']

        schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
        status += schedule_results['status'] + " "
        email_scheduled_saved = schedule_results['email_scheduled_saved']
        email_scheduled_id = schedule_results['email_scheduled_id']
        email_scheduled = schedule_results['email_scheduled']

        if email_scheduled_saved:
            send_results = email_manager.send_scheduled_email(email_scheduled)
            email_scheduled_sent = send_results['email_scheduled_sent']

    results = {
        'status':                   status,
        'success':                  True,
        'email_scheduled_saved':    email_scheduled_saved,
        'email_scheduled_sent':     email_scheduled_sent,
        'email_scheduled_id':       email_scheduled_id,
    }
    return results


def voter_email_address_retrieve_for_api(voter_device_id):
    """
    voterEmailAddressRetrieve
    :param voter_device_id:
    :return:
    """
    email_address_list_found = False
    status = ""
    success = True

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                           device_id_results['status'],
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                           "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    email_address_list_augmented = []
    email_results = email_manager.retrieve_voter_email_address_list(voter_we_vote_id)
    status += email_results['status']
    if email_results['email_address_list_found']:
        email_address_list_found = True
        email_address_list = email_results['email_address_list']

        augment_results = augment_email_address_list(email_address_list, voter)
        email_address_list_augmented = augment_results['email_address_list']
        status += augment_results['status']

    json_data = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'email_address_list_found':         email_address_list_found,
        'email_address_list':               email_address_list_augmented,
    }
    return json_data


def voter_email_address_save_for_api(voter_device_id, text_for_email_address, email_we_vote_id,
                                     resend_verification_email, make_primary_email, delete_email):
    """
    voterEmailAddressSave
    :param voter_device_id:
    :param text_for_email_address:
    :param email_we_vote_id:
    :param resend_verification_email:
    :param make_primary_email:
    :param delete_email:
    :return:
    """
    email_address_saved_we_vote_id = ""
    email_address_created = False
    email_address_deleted = False
    verification_email_sent = False
    email_address_found = False
    email_address_list_found = False
    messages_to_send = []
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                           device_id_results['status'],
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           text_for_email_address,
            'email_address_saved_we_vote_id':   email_we_vote_id,
            'email_address_created':            False,
            'email_address_deleted':            False,
            'verification_email_sent':          False,
            'email_address_already_owned_by_other_voter': False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return json_data

    # Is the text_for_email_address a valid email address?
    if positive_value_exists(email_we_vote_id):
        # We are happy
        pass
    elif positive_value_exists(text_for_email_address):
        if not validate_email(text_for_email_address):
            error_results = {
                'status':                           "VOTER_EMAIL_ADDRESS_SAVE_MISSING_VALID_EMAIL",
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'text_for_email_address':           text_for_email_address,
                'email_address_saved_we_vote_id':   email_we_vote_id,
                'email_address_created':            False,
                'email_address_deleted':            False,
                'verification_email_sent':          False,
                'email_address_already_owned_by_other_voter': False,
                'email_address_found':              False,
                'email_address_list_found':         False,
                'email_address_list':               [],
            }
            return error_results
    else:
        # We need EITHER email_we_vote_id or text_for_email_address
        error_results = {
            'status': "VOTER_EMAIL_ADDRESS_SAVE_MISSING_EMAIL",
            'success': False,
            'voter_device_id': voter_device_id,
            'text_for_email_address': text_for_email_address,
            'email_address_saved_we_vote_id': email_we_vote_id,
            'email_address_created': False,
            'email_address_deleted': False,
            'verification_email_sent': False,
            'email_address_already_owned_by_other_voter': False,
            'email_address_found': False,
            'email_address_list_found': False,
            'email_address_list': [],
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                           "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           text_for_email_address,
            'email_address_saved_we_vote_id':   "",
            'email_address_created':            False,
            'email_address_deleted':            False,
            'verification_email_sent':          False,
            'email_address_already_owned_by_other_voter': False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    email_address_already_owned_by_this_voter = False
    email_address_already_owned_by_other_voter = False
    email_address_list = []
    # Look to see if there is an EmailAddress entry for the incoming text_for_email_address or email_we_vote_id
    email_results = email_manager.retrieve_email_address_object(text_for_email_address, email_we_vote_id)
    if email_results['email_address_object_found']:
        email_address_object = email_results['email_address_object']
        email_address_list.append(email_address_object)
    elif email_results['email_address_list_found']:
        # This email was used by more than one person
        email_address_list = email_results['email_address_list']

    # Cycle through all EmailAddress entries with the email set as "text_for_email_address"
    for email_address_object in email_address_list:
        # Does the current voter own an existing entry for this text_for_email_address
        if email_address_object.voter_we_vote_id == voter_we_vote_id:
            # This can be over-ridden/ignored if email_address_already_owned_by_other_voter is true for other entry
            email_address_already_owned_by_this_voter = True
            email_address_saved_we_vote_id = email_address_object.we_vote_id
            text_for_email_address = email_address_object.normalized_email_address
            email_address_created = False
            email_address_found = True
            if delete_email:
                try:
                    email_address_object.delete()
                    email_address_deleted = True
                    status += "DELETED_EMAIL_ADDRESS"
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_DELETE_EMAIL_ADDRESS"
                    success = False
            elif make_primary_email:
                try:
                    voter.primary_email_we_vote_id = email_address_object.we_vote_id
                    voter.email = text_for_email_address
                    voter.save()
                    status += "SAVED_EMAIL_ADDRESS_AS_PRIMARY"
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_SAVE_EMAIL_ADDRESS_AS_PRIMARY"
                    success = False

        # If current voter is not owner, has ownership been verified? (Claiming an email is first-come-first-served)
        elif email_address_object.email_ownership_is_verified:
            # If here, then another voter already has verified this text_for_email_address
            email_address_already_owned_by_other_voter = True

    send_verification_email = False
    if email_address_deleted:
        # We cannot proceed with this email address
        pass
    elif email_address_already_owned_by_other_voter:
        # We cannot proceed with this email address
        pass
    elif email_address_already_owned_by_this_voter:
        # We send back a message that the email already owned by setting email_address_found = True
        if resend_verification_email:
            send_verification_email = True
    else:
        # Save the email
        email_ownership_is_verified = False
        email_save_results = email_manager.create_email_address(text_for_email_address, voter_we_vote_id,
                                                                email_ownership_is_verified, make_primary_email)

        if email_save_results['email_address_object_saved']:
            # Send verification email
            send_verification_email = True
            new_email_address_object = email_save_results['email_address_object']
            email_we_vote_id = new_email_address_object.we_vote_id
            email_address_saved_we_vote_id = email_we_vote_id
            email_address_created = True
            email_address_found = True
            success = True
        else:
            send_verification_email = False
            success = False
            status += " UNABLE_TO_SAVE_EMAIL_ADDRESS"

    if send_verification_email:
        # Generate secret key
        recipient_email_address_secret_key = "1234"

        # Run the code to send verification email for new_email_we_vote_id
        verifications_send_results = schedule_verification_email(voter_we_vote_id, voter_we_vote_id,
                                                                 email_we_vote_id, text_for_email_address,
                                                                 recipient_email_address_secret_key)
        status += verifications_send_results['status']
        email_scheduled_saved = verifications_send_results['email_scheduled_saved']
        email_scheduled_id = verifications_send_results['email_scheduled_id']
        if email_scheduled_saved:
            messages_to_send.append(email_scheduled_id)
            verification_email_sent = True
            success = True

    # Now that the save is complete, retrieve the updated list
    email_address_list_augmented = []
    email_results = email_manager.retrieve_voter_email_address_list(voter_we_vote_id)
    if email_results['email_address_list_found']:
        email_address_list_found = True
        email_address_list = email_results['email_address_list']
        augment_results = augment_email_address_list(email_address_list, voter)
        email_address_list_augmented = augment_results['email_address_list']
        status += augment_results['status']

    json_data = {
        'status':                           status,
        'success':                          success,
        'voter_device_id':                  voter_device_id,
        'text_for_email_address':           text_for_email_address,
        'email_address_saved_we_vote_id':   email_address_saved_we_vote_id,
        'email_address_created':            email_address_created,
        'email_address_deleted':            email_address_deleted,
        'verification_email_sent':          verification_email_sent,
        'email_address_already_owned_by_other_voter': email_address_already_owned_by_other_voter,
        'email_address_found':              email_address_found,
        'email_address_list_found':         email_address_list_found,
        'email_address_list':               email_address_list_augmented,
    }
    return json_data


def augment_email_address_list(email_address_list, voter):
    email_address_list_augmented = []
    primary_email_address_found = False

    status = ""
    success = True
    for email_address in email_address_list:
        is_primary_email_address = False
        if email_address.we_vote_id == voter.primary_email_we_vote_id:
            is_primary_email_address = True
            primary_email_address_found = True
            primary_email_address = email_address
        elif email_address.normalized_email_address == voter.email:
            is_primary_email_address = True
            primary_email_address_found = True
            primary_email_address = email_address
        email_address_for_json = {
            'normalized_email_address': email_address.normalized_email_address,
            'primary_email_address': is_primary_email_address,
            'email_permanent_bounce': email_address.email_permanent_bounce,
            'email_ownership_is_verified': email_address.email_ownership_is_verified,
            'voter_we_vote_id': email_address.voter_we_vote_id,
            'email_we_vote_id': email_address.we_vote_id,
        }
        email_address_list_augmented.append(email_address_for_json)

    if primary_email_address_found:
        # Make sure the voter's cached "email" and "primary_email_we_vote_id" are both correct and match same email
        voter_data_updated = False
        if voter.primary_email_we_vote_id.lower != primary_email_address.we_vote_id.lower:
            voter.primary_email_we_vote_id = primary_email_address.we_vote_id
            voter_data_updated = True
        if voter.email.lower != primary_email_address.normalized_email_address.lower:
            voter.email = primary_email_address.normalized_email_address
            voter_data_updated = True

        if voter_data_updated:
            try:
                voter.save()
                status += "SAVED_UPDATED_EMAIL_VALUES"
            except Exception as e:
                # TODO DALE We could get this exception if the EmailAddress table has email X for voter 1
                # and the voter table stores the same email X for voter 2
                status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES"
    else:
        # If here we need to heal data. If here we know that the voter record doesn't have any email info
        for primary_email_address_candidate in email_address_list:
            if primary_email_address_candidate.email_ownership_is_verified:
                # Now that we have found a verified email, save it to the voter account, and break out of loop
                voter.primary_email_we_vote_id = primary_email_address_candidate.we_vote_id
                voter.email = primary_email_address_candidate.normalized_email_address
                voter.email_ownership_is_verified = True
                try:
                    voter.save()
                    status += "SAVED_PRIMARY_EMAIL_ADDRESS_CANDIDATE"
                except Exception as e:
                    status += "UNABLE_TO_SAVE_PRIMARY_EMAIL_ADDRESS_CANDIDATE"
                break

    results = {
        'status':                           status,
        'success':                          success,
        'email_address_list':               email_address_list_augmented,
    }
    return results

