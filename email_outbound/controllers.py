# email_outbound/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .functions import merge_message_content_with_template
from .models import EmailAddress, EmailManager, EmailScheduled, GENERIC_EMAIL_TEMPLATE, LINK_TO_SIGN_IN_TEMPLATE, \
    SENT, SIGN_IN_CODE_EMAIL_TEMPLATE, TO_BE_PROCESSED, VERIFY_EMAIL_ADDRESS_TEMPLATE, WAITING_FOR_VERIFICATION
from config.base import get_environment_variable
import json
from organization.models import OrganizationManager, INDIVIDUAL
from validate_email import validate_email
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")


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

    voter_manager = VoterManager()
    if primary_email_address_found:
        # Make sure the voter's cached "email" and "primary_email_we_vote_id" are both correct and match same email
        voter_data_updated = False
        if voter.primary_email_we_vote_id and \
                voter.primary_email_we_vote_id.lower() != primary_email_address.we_vote_id.lower():
            voter.primary_email_we_vote_id = primary_email_address.we_vote_id
            voter_data_updated = True
        if voter.email and voter.email.lower() != primary_email_address.normalized_email_address.lower():
            voter.email = primary_email_address.normalized_email_address
            voter_data_updated = True

        if voter_data_updated:
            try:
                voter.save()
                status += "SAVED_UPDATED_EMAIL_VALUES "
            except Exception as e:
                # We could get this exception if the EmailAddress table has email X for voter 1
                # and the voter table stores the same email X for voter 2
                status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES"
                remove_cached_results = \
                    voter_manager.remove_voter_cached_email_entries_from_email_address_object(primary_email_address)
                status += remove_cached_results['status']
                try:
                    voter.primary_email_we_vote_id = primary_email_address.we_vote_id
                    voter.email_ownership_is_verified = True
                    voter.email = primary_email_address.normalized_email_address
                    voter.save()
                    status += "SAVED_UPDATED_EMAIL_VALUES2 "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES2 "
    else:
        # If here we need to heal data. If here we know that the voter record doesn't have any email info that matches
        #  an email address, so we want to make the first email address in the list the new master
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
                    remove_cached_results = \
                        voter_manager.remove_voter_cached_email_entries_from_email_address_object(
                            primary_email_address_candidate)
                    status += remove_cached_results['status']
                    try:
                        voter.primary_email_we_vote_id = primary_email_address_candidate.we_vote_id
                        voter.email_ownership_is_verified = True
                        voter.email = primary_email_address_candidate.normalized_email_address
                        voter.save()
                        status += "SAVED_PRIMARY_EMAIL_ADDRESS_CANDIDATE2 "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_PRIMARY_EMAIL_ADDRESS_CANDIDATE2 "
                break

    results = {
        'status':                           status,
        'success':                          success,
        'email_address_list':               email_address_list_augmented,
    }
    return results


def heal_primary_email_data_for_voter(email_address_list, voter):
    primary_email_address = None
    primary_email_address_found = False
    primary_email_address_we_vote_id = None

    status = ""
    success = True
    for email_address in email_address_list:
        if not primary_email_address_found:
            if email_address.we_vote_id == voter.primary_email_we_vote_id:
                primary_email_address_found = True
                primary_email_address = email_address
                primary_email_address_we_vote_id = primary_email_address.we_vote_id
            elif email_address.normalized_email_address == voter.email:
                primary_email_address_found = True
                primary_email_address = email_address
                primary_email_address_we_vote_id = primary_email_address.we_vote_id

    voter_manager = VoterManager()
    if primary_email_address_found:
        # Make sure the voter's cached "email" and "primary_email_we_vote_id" are both correct and match same email
        voter_data_updated = False
        if not voter.primary_email_we_vote_id:
            voter.primary_email_we_vote_id = primary_email_address_we_vote_id
            voter_data_updated = True
        elif voter.primary_email_we_vote_id and \
                voter.primary_email_we_vote_id.lower() != primary_email_address_we_vote_id.lower():
            voter.primary_email_we_vote_id = primary_email_address_we_vote_id
            voter_data_updated = True
        if not voter.email:
            voter.email = primary_email_address.normalized_email_address
            voter_data_updated = True
        elif voter.email and voter.email.lower() != primary_email_address.normalized_email_address.lower():
            voter.email = primary_email_address.normalized_email_address
            voter_data_updated = True

        if voter_data_updated:
            try:
                voter.save()
                status += "SAVED_UPDATED_EMAIL_VALUES "
            except Exception as e:
                # We could get this exception if the EmailAddress table has email X for voter 1
                # and the voter table stores the same email X for voter 2
                status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES"
                remove_cached_results = \
                    voter_manager.remove_voter_cached_email_entries_from_email_address_object(primary_email_address)
                status += remove_cached_results['status']
                try:
                    voter.primary_email_we_vote_id = primary_email_address_we_vote_id
                    voter.email_ownership_is_verified = True
                    voter.email = primary_email_address.normalized_email_address
                    voter.save()
                    status += "SAVED_UPDATED_EMAIL_VALUES2 "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES2 "
    else:
        # If here we need to heal data. If here we know that the voter record doesn't have any email info that matches
        #  an email address, so we want to make the first email address in the list the new master
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
                    remove_cached_results = \
                        voter_manager.remove_voter_cached_email_entries_from_email_address_object(
                            primary_email_address_candidate)
                    status += remove_cached_results['status']
                    try:
                        voter.primary_email_we_vote_id = primary_email_address_candidate.we_vote_id
                        voter.email_ownership_is_verified = True
                        voter.email = primary_email_address_candidate.normalized_email_address
                        voter.save()
                        status += "SAVED_PRIMARY_EMAIL_ADDRESS_CANDIDATE2 "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_PRIMARY_EMAIL_ADDRESS_CANDIDATE2 "
                break

    email_address_list_deduped = []
    for email_address in email_address_list:
        add_to_list = True
        is_primary_email_address = False
        if positive_value_exists(email_address.we_vote_id) and positive_value_exists(primary_email_address_we_vote_id):
            if email_address.we_vote_id == voter.primary_email_we_vote_id or \
                    email_address.we_vote_id == primary_email_address_we_vote_id:
                is_primary_email_address = True
        if not is_primary_email_address:
            if primary_email_address_found and hasattr(primary_email_address, "normalized_email_address"):
                # See if this email is the same as the primary email address
                if positive_value_exists(email_address.normalized_email_address) \
                        and positive_value_exists(primary_email_address.normalized_email_address):
                    if email_address.normalized_email_address.lower() == \
                            primary_email_address.normalized_email_address.lower():
                        # We want to get rid of this email
                        add_to_list = False
                        pass
        if add_to_list:
            email_address_list_deduped.append(email_address)

    results = {
        'status':                           status,
        'success':                          success,
        'email_address_list':               email_address_list_deduped,
    }
    return results


def move_email_address_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = " MOVE_EMAIL_ADDRESSES "
    success = False
    email_addresses_moved = 0
    email_addresses_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_EMAIL_ADDRESS_ENTRIES_MISSING_FROM_OR_TO_VOTER_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'email_addresses_moved': email_addresses_moved,
            'email_addresses_not_moved': email_addresses_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_EMAIL_ADDRESS_ENTRIES-IDENTICAL_FROM_AND_TO_VOTER_ID "
        results = {
            'status': status,
            'success': success,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'email_addresses_moved': email_addresses_moved,
            'email_addresses_not_moved': email_addresses_not_moved,
        }
        return results

    email_manager = EmailManager()
    email_address_list_results = email_manager.retrieve_voter_email_address_list(from_voter_we_vote_id)
    if email_address_list_results['email_address_list_found']:
        email_address_list = email_address_list_results['email_address_list']

        for email_address_object in email_address_list:
            # Change the voter_we_vote_id
            try:
                email_address_object.voter_we_vote_id = to_voter_we_vote_id
                email_address_object.save()
                email_addresses_moved += 1
            except Exception as e:
                email_addresses_not_moved += 1
                status += "UNABLE_TO_SAVE_EMAIL_ADDRESS "

        status += " MOVE_EMAIL_ADDRESSES, moved: " + str(email_addresses_moved) + \
                  ", not moved: " + str(email_addresses_not_moved)
    else:
        status += " " + email_address_list_results['status']

    results = {
        'status': status,
        'success': success,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'email_addresses_moved': email_addresses_moved,
        'email_addresses_not_moved': email_addresses_not_moved,
    }
    return results


def schedule_email_with_email_outbound_description(email_outbound_description, send_status=TO_BE_PROCESSED):
    email_manager = EmailManager()
    status = ""

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
        schedule_email_results = email_manager.schedule_email(email_outbound_description, subject,
                                                              message_text, message_html, send_status)
        success = schedule_email_results['success']
        status += schedule_email_results['status']
        email_scheduled_saved = schedule_email_results['email_scheduled_saved']
        email_scheduled = schedule_email_results['email_scheduled']
        email_scheduled_id = schedule_email_results['email_scheduled_id']
    else:
        success = False
        status += "SCHEDULE_EMAIL_TEMPLATE_NOT_PROCESSED "
        status += email_template_results['status'] + " "
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
                                recipient_email_address_secret_key):
    """
    When a voter adds a new email address for self, create and send an outbound email with a link
    that the voter can click to verify the email.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param recipient_email_address_secret_key:
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = VERIFY_EMAIL_ADDRESS_TEMPLATE

    # Generate secret key if needed
    if not positive_value_exists(recipient_email_address_secret_key):
        recipient_email_address_secret_key = email_manager.update_email_address_with_new_secret_key(
            recipient_email_we_vote_id)

    if not positive_value_exists(recipient_email_address_secret_key):
        results = {
            'status': "SCHEDULE_VERIFICATION-MISSING_EMAIL_SECRET_KEY ",
            'success': False,
            'email_scheduled_saved': email_scheduled_saved,
            'email_scheduled_sent': email_scheduled_sent,
            'email_scheduled_id': email_scheduled_id,
        }
        return results

    subject = "Please verify your email"

    template_variables_for_json = {
        "subject":                      subject,
        "recipient_voter_email":        recipient_voter_email,
        "we_vote_url":                  WEB_APP_ROOT_URL,
        "verify_email_link":            WEB_APP_ROOT_URL + "/verify_email/" + recipient_email_address_secret_key,
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


def schedule_link_to_sign_in_email(sender_voter_we_vote_id, recipient_voter_we_vote_id,
                                   recipient_email_we_vote_id, recipient_voter_email,
                                   recipient_email_address_secret_key):
    """
    When a voter wants to sign in with a pre-existing email, create and send an outbound email with a link
    that the voter can click to sign in.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param recipient_email_address_secret_key:
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = LINK_TO_SIGN_IN_TEMPLATE

    # Generate secret key if needed
    if not positive_value_exists(recipient_email_address_secret_key):
        recipient_email_address_secret_key = email_manager.update_email_address_with_new_secret_key(
            recipient_email_we_vote_id)

    if not positive_value_exists(recipient_email_address_secret_key):
        results = {
            'status': "SCHEDULE_LINK_TO_SIGN_IN-MISSING_EMAIL_SECRET_KEY ",
            'success': False,
            'email_scheduled_saved': email_scheduled_saved,
            'email_scheduled_sent': email_scheduled_sent,
            'email_scheduled_id': email_scheduled_id,
        }
        return results

    subject = "Sign in link you requested"
    link_to_sign_in = WEB_APP_ROOT_URL + "/sign_in_email/" + recipient_email_address_secret_key
    # 2019-09-30 Relying on web browser version for previous app versions
    # if is_cordova:
    #     link_to_sign_in = "wevotetwitterscheme://sign_in_email/" + recipient_email_address_secret_key

    template_variables_for_json = {
        "subject":                      subject,
        "recipient_voter_email":        recipient_voter_email,
        "we_vote_url":                  WEB_APP_ROOT_URL,
        "link_to_sign_in":              link_to_sign_in,
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


def schedule_sign_in_code_email(sender_voter_we_vote_id, recipient_voter_we_vote_id,
                                recipient_email_we_vote_id, recipient_voter_email,
                                secret_numerical_code):
    """
    When a voter wants to sign in with a pre-existing email, create and send an outbound email with a secret
    code that can be entered into the interface where the code was requested.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param secret_numerical_code:
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = SIGN_IN_CODE_EMAIL_TEMPLATE

    if not positive_value_exists(secret_numerical_code):
        results = {
            'status': "SCHEDULE_SIGN_IN_CODE_EMAIL-MISSING_EMAIL_SECRET_NUMERICAL_CODE ",
            'success': False,
            'email_scheduled_saved': email_scheduled_saved,
            'email_scheduled_sent': email_scheduled_sent,
            'email_scheduled_id': email_scheduled_id,
        }
        return results

    subject = "Your Sign in Code"

    template_variables_for_json = {
        "subject":                      subject,
        "recipient_voter_email":        recipient_voter_email,
        "we_vote_url":                  WEB_APP_ROOT_URL,
        "secret_numerical_code":        secret_numerical_code,
        "recipient_unsubscribe_url":    WEB_APP_ROOT_URL + "/unsubscribe?email_key=1234",
        "email_open_url":               WE_VOTE_SERVER_ROOT_URL + "/apis/v1/emailOpen?email_key=1234",
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    verification_from_email = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id, verification_from_email, recipient_voter_we_vote_id,
        recipient_email_we_vote_id, recipient_voter_email,
        template_variables_in_json, kind_of_email_template)
    status += outbound_results['status']
    if outbound_results['email_outbound_description_saved']:
        email_outbound_description = outbound_results['email_outbound_description']

        schedule_results = schedule_email_with_email_outbound_description(email_outbound_description)
        status += schedule_results['status']
        status += "SCHEDULE_EMAIL_WITH_OUTBOUND_DESCRIPTION_SENT "
        email_scheduled_saved = schedule_results['email_scheduled_saved']
        email_scheduled_id = schedule_results['email_scheduled_id']
        email_scheduled = schedule_results['email_scheduled']

        if email_scheduled_saved:
            status += "EMAIL_SCHEDULED_SAVED "
            send_results = email_manager.send_scheduled_email(email_scheduled)
            status += send_results['status']
            email_scheduled_sent = send_results['email_scheduled_sent']
        else:
            status += "EMAIL_SCHEDULED_NOT_SAVED "
    else:
        status += "EMAIL_OUTBOUND_DESCRIPTION_NOT_SAVED "

    results = {
        'status':                   status,
        'success':                  True,
        'email_scheduled_saved':    email_scheduled_saved,
        'email_scheduled_sent':     email_scheduled_sent,
        'email_scheduled_id':       email_scheduled_id,
    }
    return results


def voter_email_address_retrieve_for_api(voter_device_id):  # voterEmailAddressRetrieve
    """
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
    merge_results = email_manager.find_and_merge_all_duplicate_emails(voter_we_vote_id)
    status += merge_results['status']

    email_address_list_augmented = []
    email_results = email_manager.retrieve_voter_email_address_list(voter_we_vote_id)
    status += email_results['status']
    if email_results['email_address_list_found']:
        email_address_list_found = True
        email_address_list = email_results['email_address_list']

        # Make sure the voter's primary email address matches email table data
        merge_results = heal_primary_email_data_for_voter(email_address_list, voter)
        email_address_list = merge_results['email_address_list']
        status += merge_results['status']

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


def voter_email_address_sign_in_for_api(voter_device_id, email_secret_key):  # voterEmailAddressSignIn
    """
    :param voter_device_id:
    :param email_secret_key:
    :return:
    """
    email_secret_key_belongs_to_this_voter = False
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                                   device_id_results['status'],
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
            'voter_we_vote_id_from_secret_key':         "",
        }
        return json_data

    if not positive_value_exists(email_secret_key):
        error_results = {
            'status':                                   "VOTER_EMAIL_ADDRESS_VERIFY_MISSING_SECRET_KEY",
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
            'voter_we_vote_id_from_secret_key':         "",
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        error_results = {
            'status':                                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
            'voter_we_vote_id_from_secret_key':         "",
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    # Look to see if there is an EmailAddress entry for the incoming text_for_email_address or email_we_vote_id
    email_results = email_manager.retrieve_email_address_object_from_secret_key(email_secret_key)
    if not email_results['email_address_object_found']:
        status += email_results['status']
        error_results = {
            'status':                                   status,
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
            'voter_we_vote_id_from_secret_key':         "",
        }
        return error_results

    success = email_results['success']
    status += email_results['status']
    email_address_object = email_results['email_address_object']
    email_address_found = True

    email_ownership_is_verified = email_address_object.email_ownership_is_verified
    if voter_we_vote_id == email_address_object.voter_we_vote_id:
        email_secret_key_belongs_to_this_voter = True

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'voter_device_id':                          voter_device_id,
        'email_ownership_is_verified':              email_ownership_is_verified,
        'email_secret_key_belongs_to_this_voter':   email_secret_key_belongs_to_this_voter,
        'email_address_found':                      email_address_found,
        'voter_we_vote_id_from_secret_key':         email_address_object.voter_we_vote_id,
    }
    return json_data


def voter_email_address_verify_for_api(voter_device_id, email_secret_key):  # voterEmailAddressVerify
    """

    :param voter_device_id:
    :param email_secret_key:
    :return:
    """
    email_secret_key_belongs_to_this_voter = False
    voter_ownership_saved = False
    status = "ENTERING_VOTER_EMAIL_ADDRESS_VERIFY "
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        status += device_id_results['status']
        json_data = {
            'status':                                   device_id_results['status'],
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
        }
        return json_data

    if not positive_value_exists(email_secret_key):
        status += "VOTER_EMAIL_ADDRESS_VERIFY_MISSING_SECRET_KEY "
        error_results = {
            'status':                                   status,
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                                   status,
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'email_ownership_is_verified':              False,
            'email_secret_key_belongs_to_this_voter':   False,
            'email_address_found':                      False,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    # Look to see if there is an EmailAddress entry for the incoming text_for_email_address or email_we_vote_id
    email_results = email_manager.verify_email_address_object_from_secret_key(email_secret_key)
    if email_results['email_address_object_found']:
        email_address_object = email_results['email_address_object']
        email_address_found = True
        status += "EMAIL_ADDRESS_FOUND_FROM_VERIFY "

        email_ownership_is_verified = email_address_object.email_ownership_is_verified
        if voter_we_vote_id == email_address_object.voter_we_vote_id:
            email_secret_key_belongs_to_this_voter = True
            voter_ownership_results = voter_manager.update_voter_email_ownership_verified(voter, email_address_object)
            voter_ownership_saved = voter_ownership_results['voter_updated']
            if voter_ownership_saved:
                voter = voter_ownership_results['voter']
        else:
            email_owner_results = voter_manager.retrieve_voter_by_we_vote_id(email_address_object.voter_we_vote_id)
            if email_owner_results['voter_found']:
                email_owner_voter = email_owner_results['voter']
                voter_manager.update_voter_email_ownership_verified(email_owner_voter, email_address_object)
                # If we verify it but don't use it to sign in, don't set voter_ownership_saved
                # (which invalidates email_secret_key below)
    else:
        email_results = email_manager.retrieve_email_address_object_from_secret_key(email_secret_key)
        if email_results['email_address_object_found']:
            status += "EMAIL_ADDRESS_FOUND_FROM_RETRIEVE "
            email_address_object = email_results['email_address_object']
            email_address_found = True

            email_ownership_is_verified = email_address_object.email_ownership_is_verified
            if voter_we_vote_id == email_address_object.voter_we_vote_id:
                email_secret_key_belongs_to_this_voter = True
                voter_ownership_results = voter_manager.update_voter_email_ownership_verified(voter,
                                                                                              email_address_object)
                voter_ownership_saved = voter_ownership_results['voter_updated']
                if voter_ownership_saved:
                    voter = voter_ownership_results['voter']
        else:
            status += "EMAIL_NOT_FOUND_FROM_SECRET_KEY "
            error_results = {
                'status':                                   status,
                'success':                                  False,
                'voter_device_id':                          voter_device_id,
                'email_ownership_is_verified':              False,
                'email_secret_key_belongs_to_this_voter':   False,
                'email_address_found':                      False,
            }
            return error_results

    # send previous scheduled emails
    email_manager = EmailManager()
    send_status = WAITING_FOR_VERIFICATION
    scheduled_email_results = email_manager.retrieve_scheduled_email_list_from_send_status(
        email_address_object.voter_we_vote_id, send_status)
    if scheduled_email_results['scheduled_email_list_found']:
        scheduled_email_list = scheduled_email_results['scheduled_email_list']
        for scheduled_email in scheduled_email_list:
            send_results = email_manager.send_scheduled_email(scheduled_email)
            email_scheduled_sent = send_results['email_scheduled_sent']
            status += send_results['status']
            if email_scheduled_sent:
                # If scheduled email sent successfully then change their status from WAITING_FOR_VERIFICATION to SENT
                send_status = SENT
                update_scheduled_email_results = email_manager.update_scheduled_email_with_new_send_status(
                    scheduled_email, send_status)

    if voter_ownership_saved:
        if not positive_value_exists(voter.linked_organization_we_vote_id):
            # Create new organization
            organization_name = voter.get_full_name()
            organization_website = ""
            organization_twitter_handle = ""
            organization_twitter_id = ""
            organization_email = ""
            organization_facebook = ""
            organization_image = voter.voter_photo_url()
            organization_type = INDIVIDUAL
            organization_manager = OrganizationManager()
            create_results = organization_manager.create_organization(
                organization_name, organization_website, organization_twitter_handle,
                organization_email, organization_facebook, organization_image, organization_twitter_id,
                organization_type)
            if create_results['organization_created']:
                # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                organization = create_results['organization']
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()
                except Exception as e:
                    status += "UNABLE_TO_LINK_NEW_ORGANIZATION_TO_VOTER "

        # TODO DALE We want to invalidate the email_secret key used

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'voter_device_id':                          voter_device_id,
        'email_ownership_is_verified':              email_ownership_is_verified,
        'email_secret_key_belongs_to_this_voter':   email_secret_key_belongs_to_this_voter,
        'email_address_found':                      email_address_found,
    }
    return json_data


def voter_email_address_save_for_api(voter_device_id='',
                                     text_for_email_address='',
                                     incoming_email_we_vote_id='',
                                     send_link_to_sign_in=False,
                                     send_sign_in_code_email=False,
                                     resend_verification_email=False,
                                     resend_verification_code_email=False,
                                     make_primary_email=False,
                                     delete_email=False):
    """
    voterEmailAddressSave
    :param voter_device_id:
    :param text_for_email_address:
    :param incoming_email_we_vote_id:
    :param send_link_to_sign_in:
    :param send_sign_in_code_email:
    :param resend_verification_email:
    :param resend_verification_code_email:
    :param make_primary_email:
    :param delete_email:
    :return:
    """
    email_address_we_vote_id = ""
    email_address_saved_we_vote_id = ""
    email_address_created = False
    email_address_deleted = False
    verification_email_sent = False
    link_to_sign_in_email_sent = False
    sign_in_code_email_sent = False
    send_verification_email = False
    email_address_found = False
    email_address_list_found = False
    recipient_email_address_secret_key = ""
    messages_to_send = []
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        status += device_id_results['status'] + " VOTER_DEVICE_ID_NOT_VALID "
        json_data = {
            'status':                           status,
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           text_for_email_address,
            'email_address_we_vote_id':         incoming_email_we_vote_id,
            'email_address_saved_we_vote_id':   "",
            'email_address_created':            False,
            'email_address_deleted':            False,
            'verification_email_sent':          False,
            'link_to_sign_in_email_sent':       False,
            'sign_in_code_email_sent':          False,
            'email_address_already_owned_by_other_voter': False,
            'email_address_already_owned_by_this_voter': False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
            'secret_code_system_locked_for_this_voter_device_id': False,
        }
        return json_data

    # Is the text_for_email_address a valid email address?
    if positive_value_exists(incoming_email_we_vote_id):
        # We are happy
        pass
    elif positive_value_exists(text_for_email_address):
        if not validate_email(text_for_email_address):
            status += "VOTER_EMAIL_ADDRESS_SAVE_MISSING_VALID_EMAIL "
            error_results = {
                'status':                           status,
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'text_for_email_address':           text_for_email_address,
                'email_address_we_vote_id':         incoming_email_we_vote_id,
                'email_address_saved_we_vote_id':   "",
                'email_address_created':            False,
                'email_address_deleted':            False,
                'verification_email_sent':          False,
                'link_to_sign_in_email_sent':       False,
                'sign_in_code_email_sent':          False,
                'email_address_already_owned_by_other_voter': False,
                'email_address_already_owned_by_this_voter': False,
                'email_address_found':              False,
                'email_address_list_found':         False,
                'email_address_list':               [],
                'secret_code_system_locked_for_this_voter_device_id': False,
            }
            return error_results
    else:
        # We need EITHER incoming_email_we_vote_id or text_for_email_address
        status += "VOTER_EMAIL_ADDRESS_SAVE_MISSING_EMAIL "
        error_results = {
            'status':                           status,
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           text_for_email_address,
            'email_address_we_vote_id':         "",
            'email_address_saved_we_vote_id':   incoming_email_we_vote_id,
            'email_address_created':            False,
            'email_address_deleted':            False,
            'verification_email_sent':          False,
            'link_to_sign_in_email_sent':       False,
            'sign_in_code_email_sent':          False,
            'email_address_already_owned_by_other_voter': False,
            'email_address_already_owned_by_this_voter': False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
            'secret_code_system_locked_for_this_voter_device_id': False,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                           status,
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'text_for_email_address':           text_for_email_address,
            'email_address_we_vote_id':         "",
            'email_address_saved_we_vote_id':   "",
            'email_address_created':            False,
            'email_address_deleted':            False,
            'verification_email_sent':          False,
            'link_to_sign_in_email_sent':       False,
            'sign_in_code_email_sent':          False,
            'email_address_already_owned_by_other_voter': False,
            'email_address_already_owned_by_this_voter': False,
            'email_address_found':              False,
            'email_address_list_found':         False,
            'email_address_list':               [],
            'secret_code_system_locked_for_this_voter_device_id': False,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    email_address_already_owned_by_this_voter = False
    email_address_already_owned_by_other_voter = False
    verified_email_address_object = EmailAddress()
    verified_email_address_we_vote_id = ""
    email_address_list = []
    # Is this email already verified by another account?
    temp_voter_we_vote_id = ""
    find_verified_email_results = email_manager.retrieve_primary_email_with_ownership_verified(
        temp_voter_we_vote_id, text_for_email_address)
    if find_verified_email_results['email_address_object_found']:
        verified_email_address_object = find_verified_email_results['email_address_object']
        verified_email_address_we_vote_id = verified_email_address_object.we_vote_id
        if verified_email_address_object.voter_we_vote_id != voter_we_vote_id:
            email_address_already_owned_by_other_voter = True

    if email_address_already_owned_by_other_voter:
        status += "EMAIL_ALREADY_OWNED "
        if send_link_to_sign_in or send_sign_in_code_email:
            email_address_we_vote_id = verified_email_address_object.we_vote_id
            email_address_saved_we_vote_id = ""
            text_for_email_address = verified_email_address_object.normalized_email_address
            if positive_value_exists(verified_email_address_object.secret_key):
                recipient_email_address_secret_key = verified_email_address_object.secret_key
                status += "EXISTING_SECRET_KEY_FOUND "
            else:
                recipient_email_address_secret_key = \
                    email_manager.update_email_address_with_new_secret_key(email_address_we_vote_id)
                if positive_value_exists(recipient_email_address_secret_key):
                    status += "NEW_SECRET_KEY_GENERATED "
                else:
                    status += "NEW_SECRET_KEY_COULD_NOT_BE_GENERATED "
            email_address_created = False
            email_address_found = True
        else:
            status += "EMAIL_ALREADY_OWNED_BY_ANOTHER_VOTER-NO_SEND "
            error_results = {
                'status': status,
                'success': True,
                'voter_device_id': voter_device_id,
                'text_for_email_address': text_for_email_address,
                'email_address_we_vote_id': verified_email_address_we_vote_id,
                'email_address_saved_we_vote_id': "",
                'email_address_created':        False,
                'email_address_deleted':        False,
                'verification_email_sent':      False,
                'link_to_sign_in_email_sent':   False,
                'sign_in_code_email_sent':      False,
                'email_address_already_owned_by_other_voter': True,
                'email_address_already_owned_by_this_voter': False,
                'email_address_found':          True,
                'email_address_list_found':     False,
                'email_address_list':           [],
                'secret_code_system_locked_for_this_voter_device_id': False,
            }
            return error_results
    else:
        # Look to see if there is an EmailAddress entry for the incoming text_for_email_address or
        #  incoming_email_we_vote_id for this voter
        email_results = email_manager.retrieve_email_address_object(text_for_email_address, incoming_email_we_vote_id,
                                                                    voter_we_vote_id)
        if email_results['email_address_object_found']:
            email_address_object = email_results['email_address_object']
            email_address_list.append(email_address_object)
        elif email_results['email_address_list_found']:
            # This email was used by more than one person
            email_address_list = email_results['email_address_list']

        # Cycle through all EmailAddress entries with "text_for_email_address" or "incoming_email_we_vote_id"
        for email_address_object in email_address_list:
            email_address_already_owned_by_this_voter = True
            email_address_we_vote_id = email_address_object.we_vote_id
            email_address_saved_we_vote_id = ""
            text_for_email_address = email_address_object.normalized_email_address
            if positive_value_exists(email_address_object.secret_key):
                recipient_email_address_secret_key = email_address_object.secret_key
                status += "IN_LIST-SECRET_KEY_EXISTS "
            else:
                recipient_email_address_secret_key = \
                    email_manager.update_email_address_with_new_secret_key(email_address_we_vote_id)
                if positive_value_exists(recipient_email_address_secret_key):
                    status += "IN_LIST-NEW_SECRET_KEY_GENERATED "
                else:
                    status += "IN_LIST-NEW_SECRET_KEY_COULD_NOT_BE_GENERATED "
            email_address_created = False
            email_address_found = True
            if delete_email:
                status += "STARTING_DELETE_EMAIL "
                # If this email is cached in a voter record, remove it as long as primary_email_we_vote_id
                # matches email_address_object.we_vote_id
                primary_email_address_deleted = False
                if positive_value_exists(voter.primary_email_we_vote_id) \
                        and voter.primary_email_we_vote_id.lower() == email_address_object.we_vote_id.lower():
                    try:
                        voter.primary_email_we_vote_id = None
                        voter.email_ownership_is_verified = False
                        voter.email = None
                        voter.save()
                        primary_email_address_deleted = True
                        status += "VOTER_PRIMARY_EMAIL_ADDRESS_REMOVED "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_REMOVE_VOTER_PRIMARY_EMAIL_ADDRESS "
                try:
                    email_address_object.delete()
                    email_address_deleted = True
                    status += "DELETED_EMAIL_ADDRESS "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_DELETE_EMAIL_ADDRESS "
                    success = False

                if email_address_deleted:
                    # Delete all other emails associated with this account that are not be verified
                    if positive_value_exists(text_for_email_address):
                        duplicate_results = email_manager.retrieve_email_address_object(
                            text_for_email_address, voter_we_vote_id=voter_we_vote_id)
                        if duplicate_results['email_address_object_found']:
                            email_address_object_to_delete = duplicate_results['email_address_object']
                            if not positive_value_exists(email_address_object_to_delete.email_ownership_is_verified):
                                try:
                                    email_address_object_to_delete.delete()
                                    status += "DELETED_DUP_EMAIL_ADDRESS "
                                except Exception as e:
                                    status += "UNABLE_TO_DELETE_DUP_EMAIL_ADDRESS "
                        elif duplicate_results['email_address_list_found']:
                            email_address_list_for_delete = duplicate_results['email_address_list']
                            for email_address_object_to_delete in email_address_list_for_delete:
                                if not positive_value_exists(
                                        email_address_object_to_delete.email_ownership_is_verified):
                                    try:
                                        email_address_object_to_delete.delete()
                                        status += "DELETED_DUP_EMAIL_ADDRESS "
                                    except Exception as e:
                                        status += "UNABLE_TO_DELETE_DUP_EMAIL_ADDRESS "

                    # If there are any other verified emails, promote the first one to be the voter's verified email
                    if positive_value_exists(primary_email_address_deleted):
                        email_promotion_results = email_manager.retrieve_voter_email_address_list(voter_we_vote_id)
                        email_address_list_for_promotion = []
                        if email_promotion_results['email_address_list_found']:
                            # This email was used by more than one person
                            email_address_list_for_promotion = email_promotion_results['email_address_list']
                            email_address_list_found_for_promotion_to_primary = True
                        else:
                            email_address_list_found_for_promotion_to_primary = False

                        if email_address_list_found_for_promotion_to_primary:
                            for email_address_object_for_promotion in email_address_list_for_promotion:
                                if positive_value_exists(
                                        email_address_object_for_promotion.email_ownership_is_verified):
                                    # Assign this as voter's new primary email
                                    try:
                                        voter.primary_email_we_vote_id = email_address_object_for_promotion.we_vote_id
                                        voter.email_ownership_is_verified = True
                                        voter.email = email_address_object_for_promotion.normalized_email_address
                                        voter.save()
                                        status += "SAVED_EMAIL_ADDRESS_AS_NEW_PRIMARY "
                                        success = True
                                    except Exception as e:
                                        status += "UNABLE_TO_SAVE_EMAIL_ADDRESS_AS_NEW_PRIMARY "
                                        remove_cached_results = \
                                            voter_manager.remove_voter_cached_email_entries_from_email_address_object(
                                                email_address_object_for_promotion)
                                        status += remove_cached_results['status']
                                        try:
                                            voter.primary_email_we_vote_id = email_address_object_for_promotion.we_vote_id
                                            voter.email_ownership_is_verified = True
                                            voter.email = email_address_object_for_promotion.normalized_email_address
                                            voter.save()
                                            status += "SAVED_EMAIL_ADDRESS_AS_NEW_PRIMARY "
                                            success = True
                                        except Exception as e:
                                            status += "UNABLE_TO_REMOVE_VOTER_PRIMARY_EMAIL_ADDRESS2 "
                                    break  # Stop looking at email addresses to make the new primary

                break  # TODO DALE Is there ever a case where we want to delete more than one email at a time?
            elif make_primary_email and positive_value_exists(incoming_email_we_vote_id):
                # We know we want to make incoming_email_we_vote_id the primary email
                if not email_address_object.email_ownership_is_verified:
                    # Do not make an unverified email primary
                    status += "DO_NOT_MAKE_UNVERIFIED_EMAIL_PRIMARY "
                elif email_address_object.we_vote_id.lower() == incoming_email_we_vote_id.lower():
                    # Make sure this isn't already the primary
                    if positive_value_exists(voter.primary_email_we_vote_id) \
                            and voter.primary_email_we_vote_id.lower() == email_address_object.we_vote_id.lower():
                        # If already the primary email, leave it but make sure to heal the data
                        try:
                            voter.primary_email_we_vote_id = email_address_object.we_vote_id
                            voter.email_ownership_is_verified = True
                            voter.email = email_address_object.normalized_email_address
                            voter.save()
                            status += "SAVED_EMAIL_ADDRESS_AS_PRIMARY-HEALING_DATA "
                            success = True
                        except Exception as e:
                            status += "UNABLE_TO_SAVE_EMAIL_ADDRESS_AS_PRIMARY-HEALING_DATA "
                            remove_cached_results = \
                                voter_manager.remove_voter_cached_email_entries_from_email_address_object(
                                    email_address_object)
                            status += remove_cached_results['status']
                            try:
                                voter.primary_email_we_vote_id = email_address_object.we_vote_id
                                voter.email_ownership_is_verified = True
                                voter.email = email_address_object.normalized_email_address
                                voter.save()
                                status += "SAVED_EMAIL_ADDRESS_AS_NEW_PRIMARY "
                                success = True
                            except Exception as e:
                                status += "UNABLE_TO_REMOVE_VOTER_PRIMARY_EMAIL_ADDRESS2 "
                                success = False
                    else:
                        # Set this email address as the primary
                        status += "SET_THIS_EMAIL_ADDRESS_AS_PRIMARY "

                        # First, search for any other voter records that think they are using this
                        # normalized_email_address or primary_email_we_vote_id. If there are other records
                        # using these, they are bad data that don't reflect
                        remove_cached_results = \
                            voter_manager.remove_voter_cached_email_entries_from_email_address_object(
                                email_address_object)
                        status += remove_cached_results['status']

                        # And now, update current voter
                        try:
                            voter.primary_email_we_vote_id = email_address_object.we_vote_id
                            voter.email_ownership_is_verified = True
                            voter.email = email_address_object.normalized_email_address
                            voter.save()
                            status += "SAVED_EMAIL_ADDRESS_AS_PRIMARY "
                            success = True
                        except Exception as e:
                            status += "UNABLE_TO_SAVE_EMAIL_ADDRESS_AS_PRIMARY "
                            success = False
                    break  # Break out of the email_address_list loop
                elif positive_value_exists(voter.primary_email_we_vote_id) \
                        and voter.primary_email_we_vote_id.lower() == email_address_object.we_vote_id.lower():
                    # If here, we know that we are not looking at the email we want to make primary,
                    # but we only want to wipe out a voter's primary email when we replace it with another email
                    status += "LOOKING_AT_EMAIL_WITHOUT_WIPING_OUT_VOTER_PRIMARY "

        send_verification_email = False
        if email_address_deleted:
            # We cannot proceed with this email address, since it was just marked deleted
            pass
        elif email_address_already_owned_by_this_voter:
            status += "EMAIL_ADDRESS_ALREADY_OWNED_BY_THIS_VOTER "
            # We send back a message that the email already owned by setting email_address_found = True
            if resend_verification_email:
                send_verification_email = True
        elif not positive_value_exists(incoming_email_we_vote_id):
            # Save the new email address
            status += "CREATE_NEW_EMAIL_ADDRESS "
            email_ownership_is_verified = False
            email_save_results = email_manager.create_email_address(
                text_for_email_address, voter_we_vote_id, email_ownership_is_verified, make_primary_email)
            status += email_save_results['status']
            if email_save_results['email_address_object_saved']:
                # Send verification email
                send_verification_email = True
                new_email_address_object = email_save_results['email_address_object']
                email_address_we_vote_id = new_email_address_object.we_vote_id
                email_address_saved_we_vote_id = new_email_address_object.we_vote_id
                if positive_value_exists(new_email_address_object.secret_key):
                    recipient_email_address_secret_key = new_email_address_object.secret_key
                else:
                    recipient_email_address_secret_key = \
                        email_manager.update_email_address_with_new_secret_key(email_address_we_vote_id)
                email_address_created = True
                email_address_found = True
                success = True
                status += email_save_results['status']
            else:
                send_verification_email = False
                success = False
                status += "UNABLE_TO_SAVE_EMAIL_ADDRESS "

    secret_code_system_locked_for_this_voter_device_id = False
    voter_device_link_manager = VoterDeviceLinkManager()
    if send_link_to_sign_in and not email_address_already_owned_by_this_voter:
        # Run the code to send sign in email
        email_address_we_vote_id = email_address_we_vote_id if positive_value_exists(email_address_we_vote_id) \
            else incoming_email_we_vote_id
        link_send_results = schedule_link_to_sign_in_email(voter_we_vote_id, voter_we_vote_id,
                                                           email_address_we_vote_id, text_for_email_address,
                                                           recipient_email_address_secret_key)
        status += link_send_results['status']
        email_scheduled_saved = link_send_results['email_scheduled_saved']
        if email_scheduled_saved:
            link_to_sign_in_email_sent = True
            success = True
    elif send_sign_in_code_email:
        # Run the code to send email with sign in verification code (6 digit)
        email_address_we_vote_id = email_address_we_vote_id if positive_value_exists(email_address_we_vote_id) \
            else incoming_email_we_vote_id
        status += "ABOUT_TO_SEND_SIGN_IN_CODE_EMAIL: " + str(email_address_we_vote_id) + " "
        # We need to link a randomly generated 6 digit code to this voter_device_id
        results = voter_device_link_manager.retrieve_voter_secret_code_up_to_date(voter_device_id)
        secret_code = results['secret_code']
        secret_code_system_locked_for_this_voter_device_id = \
            results['secret_code_system_locked_for_this_voter_device_id']

        if positive_value_exists(secret_code_system_locked_for_this_voter_device_id):
            status += "SECRET_CODE_SYSTEM_LOCKED-EMAIL_SAVE "
            success = True
        elif positive_value_exists(secret_code):
            # And we need to store the secret_key (as opposed to the 6 digit secret code) in the voter_device_link
            #  so we can match this email to this session
            link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if link_results['voter_device_link_found']:
                voter_device_link = link_results['voter_device_link']
                update_results = voter_device_link_manager.update_voter_device_link_with_email_secret_key(
                    voter_device_link, recipient_email_address_secret_key)
                if positive_value_exists(update_results['success']):
                    status += "UPDATED_VOTER_DEVICE_LINK_WITH_SECRET_KEY "
                else:
                    status += update_results['status']
                    status += "COULD_NOT_UPDATE_VOTER_DEVICE_LINK_WITH_SECRET_KEY "
                    # Wipe out existing value and save again
                    voter_device_link_manager.clear_secret_key(email_secret_key=recipient_email_address_secret_key)
                    update_results = voter_device_link_manager.update_voter_device_link_with_email_secret_key(
                        voter_device_link, recipient_email_address_secret_key)
                    if not positive_value_exists(update_results['success']):
                        status += update_results['status']
            else:
                status += "VOTER_DEVICE_LINK_NOT_UPDATED_WITH_EMAIL_SECRET_KEY "

            status += 'ABOUT_TO_SEND_SIGN_IN_CODE '
            link_send_results = schedule_sign_in_code_email(
                voter_we_vote_id, voter_we_vote_id,
                email_address_we_vote_id, text_for_email_address,
                secret_code)
            status += link_send_results['status']
            email_scheduled_saved = link_send_results['email_scheduled_saved']
            if email_scheduled_saved:
                status += "EMAIL_CODE_SCHEDULED "
                sign_in_code_email_sent = True
                success = True
            else:
                status += 'SCHEDULE_SIGN_IN_CODE_EMAIL_FAILED '
                success = False
        else:
            status += results['status']
            status += 'RETRIEVE_VOTER_SECRET_CODE_UP_TO_DATE_FAILED '
            success = False
    elif send_verification_email:
        # Run the code to send verification email
        email_address_we_vote_id = email_address_we_vote_id if positive_value_exists(email_address_we_vote_id) \
            else incoming_email_we_vote_id
        verifications_send_results = schedule_verification_email(voter_we_vote_id, voter_we_vote_id,
                                                                 email_address_we_vote_id, text_for_email_address,
                                                                 recipient_email_address_secret_key)
        status += verifications_send_results['status']
        email_scheduled_saved = verifications_send_results['email_scheduled_saved']
        if email_scheduled_saved:
            status += "EMAIL_SCHEDULED "
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
        'email_address_we_vote_id':         email_address_we_vote_id,
        'email_address_already_owned_by_other_voter':   email_address_already_owned_by_other_voter,
        'email_address_already_owned_by_this_voter':    email_address_already_owned_by_this_voter,
        'email_address_found':              email_address_found,
        'email_address_list_found':         email_address_list_found,
        'email_address_list':               email_address_list_augmented,
        'email_address_saved_we_vote_id':   email_address_saved_we_vote_id,
        'email_address_created':            email_address_created,
        'email_address_deleted':            email_address_deleted,
        'verification_email_sent':          verification_email_sent,
        'link_to_sign_in_email_sent':       link_to_sign_in_email_sent,
        'sign_in_code_email_sent':          sign_in_code_email_sent,
        'secret_code_system_locked_for_this_voter_device_id': secret_code_system_locked_for_this_voter_device_id,
    }
    return json_data
