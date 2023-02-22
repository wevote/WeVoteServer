# sms/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .functions import merge_message_content_with_template
from .models import GENERIC_SMS_TEMPLATE, SMSPhoneNumber, SMSManager, SMSScheduled, \
    SENT, SIGN_IN_CODE_SMS_TEMPLATE, TO_BE_PROCESSED, WAITING_FOR_VERIFICATION
from config.base import get_environment_variable
import json
from organization.controllers import transform_web_app_url
import phonenumbers
from voter.models import VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def validate_sms_phone_number(sms_phone_number, region="US"):
    parse_results = phonenumbers.parse(sms_phone_number, region)
    return phonenumbers.is_valid_number(parse_results)


def delete_sms_phone_number_entries_for_voter(voter_to_delete_we_vote_id, voter_to_delete):
    status = "DELETE_SMS_PHONE_NUMBERS "
    success = False
    sms_phone_numbers_deleted = 0
    sms_phone_numbers_not_deleted = 0

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_SMS_PHONE_NUMBER_ENTRIES_MISSING_FROM_VOTER_WE_VOTE_ID "
        results = {
            'status':                           status,
            'success':                          success,
            'voter_to_delete':                  voter_to_delete,
            'voter_to_delete_we_vote_id':       voter_to_delete_we_vote_id,
            'sms_phone_numbers_deleted':        sms_phone_numbers_deleted,
            'sms_phone_numbers_not_deleted':    sms_phone_numbers_not_deleted,
        }
        return results

    sms_manager = SMSManager()
    sms_phone_number_list_results = sms_manager.retrieve_voter_sms_phone_number_list(voter_to_delete_we_vote_id)
    if sms_phone_number_list_results['sms_phone_number_list_found']:
        sms_phone_number_list = sms_phone_number_list_results['sms_phone_number_list']

        for sms_phone_number in sms_phone_number_list:
            try:
                sms_phone_number.delete()
                sms_phone_numbers_deleted += 1
            except Exception as e:
                sms_phone_numbers_not_deleted += 1
                status += "UNABLE_TO_DELETE_SMS_PHONE_NUMBER " + str(e) + ' '

        status += " MOVE_SMS_PHONE_NUMBERS, moved: " + str(sms_phone_numbers_deleted) + \
                  ", not moved: " + str(sms_phone_numbers_not_deleted) + " "
    else:
        status += " " + sms_phone_number_list_results['status']

    if positive_value_exists(voter_to_delete.primary_sms_we_vote_id):
        # Remove the sms information so we don't have a future conflict
        try:
            voter_to_delete.normalized_sms_phone_number = None
            voter_to_delete.primary_sms_we_vote_id = None
            voter_to_delete.sms_ownership_is_verified = False
            voter_to_delete.save()
        except Exception as e:
            status += "CANNOT_CLEAR_OUT_VOTER_SMS_INFO: " + str(e) + " "

    results = {
        'status':                           status,
        'success':                          success,
        'voter_to_delete':                  voter_to_delete,
        'voter_to_delete_we_vote_id':       voter_to_delete_we_vote_id,
        'sms_phone_numbers_deleted':        sms_phone_numbers_deleted,
        'sms_phone_numbers_not_deleted':    sms_phone_numbers_not_deleted,
    }
    return results


def augment_sms_phone_number_list(sms_phone_number_list, voter):
    status = ""
    success = True
    sms_phone_number_list_augmented = []
    primary_sms_phone_number_found = False

    if not voter or not voter.we_vote_id:
        status += 'AUGMENT_SMS_MISSING_VOTER_OBJECT '
        success = False
        results = {
            'status':                   status,
            'success':                  success,
            'sms_phone_number_list':    sms_phone_number_list_augmented,
        }
        return results

    primary_sms_phone_number = None
    for sms_phone_number in sms_phone_number_list:
        is_primary_sms_phone_number = False
        if sms_phone_number.we_vote_id == voter.primary_sms_we_vote_id:
            is_primary_sms_phone_number = True
            primary_sms_phone_number_found = True
            primary_sms_phone_number = sms_phone_number
        elif sms_phone_number.normalized_sms_phone_number == voter.normalized_sms_phone_number:
            is_primary_sms_phone_number = True
            primary_sms_phone_number_found = True
            primary_sms_phone_number = sms_phone_number
        sms_phone_number_for_json = {
            'normalized_sms_phone_number': sms_phone_number.normalized_sms_phone_number,
            'primary_sms_phone_number': is_primary_sms_phone_number,
            'sms_permanent_bounce': sms_phone_number.sms_permanent_bounce,
            'sms_ownership_is_verified': sms_phone_number.sms_ownership_is_verified,
            'voter_we_vote_id': sms_phone_number.voter_we_vote_id,
            'sms_we_vote_id': sms_phone_number.we_vote_id,
        }
        sms_phone_number_list_augmented.append(sms_phone_number_for_json)

    voter_manager = VoterManager()
    if primary_sms_phone_number_found:
        # Make sure the voter's cached "sms" and "primary_sms_we_vote_id" are both correct and match same sms
        voter_data_updated = False
        if voter.primary_sms_we_vote_id and \
                voter.primary_sms_we_vote_id.lower() != primary_sms_phone_number.we_vote_id.lower():
            voter.primary_sms_we_vote_id = primary_sms_phone_number.we_vote_id
            voter_data_updated = True
        if voter.normalized_sms_phone_number and voter.normalized_sms_phone_number != primary_sms_phone_number.normalized_sms_phone_number:
            voter.normalized_sms_phone_number = primary_sms_phone_number.normalized_sms_phone_number
            voter_data_updated = True

        if voter_data_updated:
            try:
                voter.save()
                status += "SAVED_UPDATED_SMS_VALUES "
            except Exception as e:
                # We could get this exception if the SMSPhoneNumber table has sms X for voter 1
                # and the voter table stores the same sms X for voter 2
                status += "UNABLE_TO_SAVE_UPDATED_SMS_VALUES"
                remove_cached_results = \
                    voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(primary_sms_phone_number)
                status += remove_cached_results['status']
                try:
                    voter.primary_sms_we_vote_id = primary_sms_phone_number.we_vote_id
                    voter.sms_ownership_is_verified = True
                    voter.normalized_sms_phone_number = primary_sms_phone_number.normalized_sms_phone_number
                    voter.save()
                    status += "SAVED_UPDATED_SMS_VALUES2 "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_SAVE_UPDATED_SMS_VALUES2 "
    else:
        # If here we need to heal data. If here we know that the voter record doesn't have any sms info that matches
        #  an sms address, so we want to make the first sms address in the list the new master
        for primary_sms_phone_number_candidate in sms_phone_number_list:
            if primary_sms_phone_number_candidate.sms_ownership_is_verified:
                # Now that we have found a verified sms, save it to the voter account, and break out of loop
                voter.primary_sms_we_vote_id = primary_sms_phone_number_candidate.we_vote_id
                voter.normalized_sms_phone_number = primary_sms_phone_number_candidate.normalized_sms_phone_number
                voter.sms_ownership_is_verified = True
                try:
                    voter.save()
                    status += "SAVED_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE"
                except Exception as e:
                    status += "UNABLE_TO_SAVE_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE"
                    remove_cached_results = \
                        voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(
                            primary_sms_phone_number_candidate)
                    status += remove_cached_results['status']
                    try:
                        voter.primary_sms_we_vote_id = primary_sms_phone_number_candidate.we_vote_id
                        voter.sms_ownership_is_verified = True
                        voter.normalized_sms_phone_number = \
                            primary_sms_phone_number_candidate.normalized_sms_phone_number
                        voter.save()
                        status += "SAVED_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE2 "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE2 "
                break

    results = {
        'status':                   status,
        'success':                  success,
        'sms_phone_number_list':    sms_phone_number_list_augmented,
    }
    return results


def heal_primary_sms_data_for_voter(sms_phone_number_list, voter):
    primary_sms_phone_number = None
    primary_sms_phone_number_found = False
    primary_sms_phone_number_we_vote_id = None

    status = ""
    success = True
    for sms_phone_number in sms_phone_number_list:
        if not primary_sms_phone_number_found:
            if sms_phone_number.we_vote_id == voter.primary_sms_we_vote_id:
                primary_sms_phone_number_found = True
                primary_sms_phone_number = sms_phone_number
                primary_sms_phone_number_we_vote_id = primary_sms_phone_number.we_vote_id
            elif sms_phone_number.normalized_sms_phone_number == voter.normalized_sms_phone_number:
                primary_sms_phone_number_found = True
                primary_sms_phone_number = sms_phone_number
                primary_sms_phone_number_we_vote_id = primary_sms_phone_number.we_vote_id

    voter_manager = VoterManager()
    if primary_sms_phone_number_found:
        # Make sure the voter's cached "sms" and "primary_sms_we_vote_id" are both correct and match same sms
        voter_data_updated = False
        if not voter.primary_sms_we_vote_id:
            voter.primary_sms_we_vote_id = primary_sms_phone_number_we_vote_id
            voter_data_updated = True
        elif voter.primary_sms_we_vote_id and \
                voter.primary_sms_we_vote_id.lower() != primary_sms_phone_number_we_vote_id.lower():
            voter.primary_sms_we_vote_id = primary_sms_phone_number_we_vote_id
            voter_data_updated = True
        if not voter.normalized_sms_phone_number:
            voter.normalized_sms_phone_number = primary_sms_phone_number.normalized_sms_phone_number
            voter_data_updated = True
        elif voter.normalized_sms_phone_number \
                and voter.normalized_sms_phone_number.lower() != \
                primary_sms_phone_number.normalized_sms_phone_number.lower():
            voter.normalized_sms_phone_number = primary_sms_phone_number.normalized_sms_phone_number
            voter_data_updated = True

        if voter_data_updated:
            try:
                voter.save()
                status += "SAVED_UPDATED_SMS_VALUES "
            except Exception as e:
                # We could get this exception if the SMSPhoneNumber table has sms X for voter 1
                # and the voter table stores the same sms X for voter 2
                status += "UNABLE_TO_SAVE_UPDATED_SMS_VALUES " + str(e) + " "
                remove_cached_results = \
                    voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(primary_sms_phone_number)
                status += remove_cached_results['status']
                try:
                    voter.primary_sms_we_vote_id = primary_sms_phone_number_we_vote_id
                    voter.sms_ownership_is_verified = True
                    voter.normalized_sms_phone_number = primary_sms_phone_number.normalized_sms_phone_number
                    voter.save()
                    status += "SAVED_UPDATED_SMS_VALUES2 "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_SAVE_UPDATED_SMS_VALUES2 " + str(e) + " "
    else:
        # If here we need to heal data. If here we know that the voter record doesn't have any sms info that matches
        #  an sms address, so we want to make the first sms address in the list the new master
        for primary_sms_phone_number_candidate in sms_phone_number_list:
            if primary_sms_phone_number_candidate.sms_ownership_is_verified:
                # Now that we have found a verified sms, save it to the voter account, and break out of loop
                voter.primary_sms_we_vote_id = primary_sms_phone_number_candidate.we_vote_id
                voter.normalized_sms_phone_number = primary_sms_phone_number_candidate.normalized_sms_phone_number
                voter.sms_ownership_is_verified = True
                try:
                    voter.save()
                    status += "SAVED_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE "
                except Exception as e:
                    status += "UNABLE_TO_SAVE_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE " + str(e) + " "
                    remove_cached_results = \
                        voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(
                            primary_sms_phone_number_candidate)
                    status += remove_cached_results['status']
                    try:
                        voter.primary_sms_we_vote_id = primary_sms_phone_number_candidate.we_vote_id
                        voter.sms_ownership_is_verified = True
                        voter.normalized_sms_phone_number = primary_sms_phone_number_candidate.normalized_sms_phone_number
                        voter.save()
                        status += "SAVED_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE2 "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_PRIMARY_SMS_PHONE_NUMBER_CANDIDATE2 " + str(e) + " "
                break

    sms_phone_number_list_deduped = []
    for sms_phone_number in sms_phone_number_list:
        add_to_list = True
        is_primary_sms_phone_number = False
        if positive_value_exists(sms_phone_number.we_vote_id) \
                and positive_value_exists(primary_sms_phone_number_we_vote_id):
            if sms_phone_number.we_vote_id == voter.primary_sms_we_vote_id or \
                    sms_phone_number.we_vote_id == primary_sms_phone_number_we_vote_id:
                is_primary_sms_phone_number = True
        if not is_primary_sms_phone_number:
            if primary_sms_phone_number_found and hasattr(primary_sms_phone_number, "normalized_sms_phone_number"):
                # See if this sms is the same as the primary sms address
                if positive_value_exists(sms_phone_number.normalized_sms_phone_number) \
                        and positive_value_exists(primary_sms_phone_number.normalized_sms_phone_number):
                    if sms_phone_number.normalized_sms_phone_number.lower() == \
                            primary_sms_phone_number.normalized_sms_phone_number.lower():
                        # We want to get rid of this sms
                        add_to_list = False
                        pass
        if add_to_list:
            sms_phone_number_list_deduped.append(sms_phone_number)

    results = {
        'status':                   status,
        'success':                  success,
        'sms_phone_number_list':    sms_phone_number_list_deduped,
    }
    return results


def move_sms_phone_number_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id, from_voter, to_voter):
    status = "MOVE_SMS_PHONE_NUMBERS "
    success = True
    sms_phone_numbers_moved = 0
    sms_phone_numbers_not_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_SMS_PHONE_NUMBER_ENTRIES_MISSING_FROM_OR_TO_VOTER_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter': to_voter,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'sms_phone_numbers_moved': sms_phone_numbers_moved,
            'sms_phone_numbers_not_moved': sms_phone_numbers_not_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_SMS_PHONE_NUMBER_ENTRIES-IDENTICAL_FROM_AND_TO_VOTER_ID "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'from_voter_we_vote_id': from_voter_we_vote_id,
            'to_voter': to_voter,
            'to_voter_we_vote_id': to_voter_we_vote_id,
            'sms_phone_numbers_moved': sms_phone_numbers_moved,
            'sms_phone_numbers_not_moved': sms_phone_numbers_not_moved,
        }
        return results

    sms_manager = SMSManager()
    sms_phone_number_list_results = sms_manager.retrieve_voter_sms_phone_number_list(from_voter_we_vote_id)
    if not sms_phone_number_list_results['success']:
        status += sms_phone_number_list_results['status']
        success = False
    if sms_phone_number_list_results['sms_phone_number_list_found']:
        sms_phone_number_list = sms_phone_number_list_results['sms_phone_number_list']

        for sms_phone_number in sms_phone_number_list:
            # Change the voter_we_vote_id
            try:
                sms_phone_number.voter_we_vote_id = to_voter_we_vote_id
                sms_phone_number.save()
                sms_phone_numbers_moved += 1
            except Exception as e:
                sms_phone_numbers_not_moved += 1
                status += "UNABLE_TO_SAVE_SMS_PHONE_NUMBER: " + str(e) + ' '
                success = False

        status += " MOVE_SMS_PHONE_NUMBERS, moved: " + str(sms_phone_numbers_moved) + \
                  ", not moved: " + str(sms_phone_numbers_not_moved) + " "
    else:
        status += " " + sms_phone_number_list_results['status']

    # Now clean up the list of emails
    merge_results = sms_manager.find_and_merge_all_duplicate_sms(to_voter_we_vote_id)
    status += merge_results['status']
    if not merge_results['success']:
        success = False

    sms_results = sms_manager.retrieve_voter_sms_phone_number_list(to_voter_we_vote_id)
    status += sms_results['status']
    if not sms_results['success']:
        success = False
    if sms_results['sms_phone_number_list_found']:
        sms_phone_number_list = sms_results['sms_phone_number_list']

        # Make sure the voter's primary sms matches sms table data
        merge_results = heal_primary_sms_data_for_voter(sms_phone_number_list, to_voter)
        status += merge_results['status']

    if positive_value_exists(from_voter.primary_sms_we_vote_id):
        # Remove the sms information so we don't have a future conflict
        try:
            from_voter.normalized_sms_phone_number = None
            from_voter.primary_sms_we_vote_id = None
            from_voter.sms_ownership_is_verified = False
            from_voter.save()
        except Exception as e:
            status += "CANNOT_CLEAR_OUT_VOTER_SMS_INFO: " + str(e) + " "
            success = False

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter': to_voter,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'sms_phone_numbers_moved': sms_phone_numbers_moved,
        'sms_phone_numbers_not_moved': sms_phone_numbers_not_moved,
    }
    return results


def schedule_sms_with_sms_description(sms_description, send_status=TO_BE_PROCESSED):
    sms_manager = SMSManager()
    status = ""

    template_variables_in_json = sms_description.template_variables_in_json
    if positive_value_exists(sms_description.kind_of_sms_template):
        kind_of_sms_template = sms_description.kind_of_sms_template
    else:
        kind_of_sms_template = GENERIC_SMS_TEMPLATE

    sms_template_results = merge_message_content_with_template(kind_of_sms_template, template_variables_in_json)
    if sms_template_results['success']:
        message_text = sms_template_results['message_text']
        schedule_sms_results = sms_manager.schedule_sms(sms_description, message_text, send_status)
        success = schedule_sms_results['success']
        status += schedule_sms_results['status']
        sms_scheduled_saved = schedule_sms_results['sms_scheduled_saved']
        sms_scheduled = schedule_sms_results['sms_scheduled']
        sms_scheduled_id = schedule_sms_results['sms_scheduled_id']
    else:
        success = False
        status += "SCHEDULE_SMS_TEMPLATE_NOT_PROCESSED "
        status += sms_template_results['status'] + " "
        sms_scheduled_saved = False
        sms_scheduled = SMSScheduled()
        sms_scheduled_id = 0

    results = {
        'success':              success,
        'status':               status,
        'sms_scheduled_saved':  sms_scheduled_saved,
        'sms_scheduled_id':     sms_scheduled_id,
        'sms_scheduled':        sms_scheduled,
    }
    return results


def schedule_verification_sms(sender_voter_we_vote_id, recipient_voter_we_vote_id,
                              recipient_sms_we_vote_id, recipient_voter_sms,
                              recipient_sms_phone_number_secret_key, web_app_root_url=''):
    """
    TODO: This needs to be reworked
    When a voter adds a new sms address for self, create and send an outbound sms with a link
    that the voter can click to verify the sms.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_sms_we_vote_id:
    :param recipient_voter_sms:
    :param recipient_sms_phone_number_secret_key:
    :param web_app_root_url:
    :return:
    """
    sms_scheduled_saved = False
    sms_scheduled_sent = False
    sms_scheduled_id = 0

    sms_manager = SMSManager()
    status = ""
    kind_of_sms_template = 'VERIFY_SMS_PHONE_NUMBER_TEMPLATE'
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

    # Generate secret key if needed
    if not positive_value_exists(recipient_sms_phone_number_secret_key):
        recipient_sms_phone_number_secret_key = sms_manager.update_sms_phone_number_with_new_secret_key(
            recipient_sms_we_vote_id)

    if not positive_value_exists(recipient_sms_phone_number_secret_key):
        results = {
            'status': "SCHEDULE_VERIFICATION-MISSING_SMS_SECRET_KEY ",
            'success': False,
            'sms_scheduled_saved': sms_scheduled_saved,
            'sms_scheduled_sent': sms_scheduled_sent,
            'sms_scheduled_id': sms_scheduled_id,
        }
        return results

    subject = "Please verify your sms"
    original_sender_sms_subscription_secret_key = ''

    template_variables_for_json = {
        "subject":                      subject,
        "recipient_voter_sms":          recipient_voter_sms,
        "we_vote_url":                  web_app_root_url_verified,
        "verify_sms_link":              web_app_root_url_verified + "/verify_sms/" +
        recipient_sms_phone_number_secret_key,
        # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
        # original_sender_sms_subscription_secret_key,
        "recipient_unsubscribe_url":
            web_app_root_url_verified + "/unsubscribe/{sms_secret_key}/login".format(
                sms_secret_key=original_sender_sms_subscription_secret_key,
            ),
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    verification_from_sms = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    outbound_results = sms_manager.create_sms_description(
        sender_voter_we_vote_id, verification_from_sms, recipient_voter_we_vote_id,
        recipient_sms_we_vote_id, recipient_voter_sms,
        template_variables_in_json, kind_of_sms_template)
    status += outbound_results['status'] + " "
    if outbound_results['sms_description_saved']:
        sms_description = outbound_results['sms_description']

        schedule_results = schedule_sms_with_sms_description(sms_description)
        status += schedule_results['status'] + " "
        sms_scheduled_saved = schedule_results['sms_scheduled_saved']
        sms_scheduled_id = schedule_results['sms_scheduled_id']
        sms_scheduled = schedule_results['sms_scheduled']

        if sms_scheduled_saved:
            send_results = sms_manager.send_scheduled_sms(sms_scheduled)
            sms_scheduled_sent = send_results['sms_scheduled_sent']

    results = {
        'status':                   status,
        'success':                  True,
        'sms_scheduled_saved':    sms_scheduled_saved,
        'sms_scheduled_sent':     sms_scheduled_sent,
        'sms_scheduled_id':       sms_scheduled_id,
    }
    return results


def schedule_sign_in_code_sms(sender_voter_we_vote_id, recipient_voter_we_vote_id,
                              recipient_sms_we_vote_id, recipient_voter_sms,
                              secret_numerical_code, web_app_root_url=''):
    """
    When a voter wants to sign in with a pre-existing sms, create and send an outbound sms with a secret
    code that can be entered into the interface where the code was requested.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_sms_we_vote_id:
    :param recipient_voter_sms:
    :param secret_numerical_code:
    :param web_app_root_url:
    :return:
    """
    sms_scheduled_saved = False
    sms_scheduled_sent = False
    sms_scheduled_id = 0

    sms_manager = SMSManager()
    status = ""
    kind_of_sms_template = SIGN_IN_CODE_SMS_TEMPLATE
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

    if not positive_value_exists(secret_numerical_code):
        status += "SCHEDULE_SIGN_IN_CODE_SMS-MISSING_SMS_SECRET_NUMERICAL_CODE "
        results = {
            'status':               status,
            'success':              False,
            'sms_scheduled_saved':  sms_scheduled_saved,
            'sms_scheduled_sent':   sms_scheduled_sent,
            'sms_scheduled_id':     sms_scheduled_id,
        }
        return results

    template_variables_for_json = {
        "recipient_voter_sms":      recipient_voter_sms,
        "we_vote_url":              web_app_root_url_verified,
        "secret_numerical_code":    secret_numerical_code,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    try:
        verification_from_sms = get_environment_variable("SYSTEM_SENDER_SMS_PHONE_NUMBER")
    except Exception as e:
        verification_from_sms = ''

    outbound_results = sms_manager.create_sms_description(
        sender_voter_we_vote_id, verification_from_sms, recipient_voter_we_vote_id,
        recipient_sms_we_vote_id, recipient_voter_sms,
        template_variables_in_json, kind_of_sms_template)
    status += outbound_results['status']
    if outbound_results['sms_description_saved']:
        sms_description = outbound_results['sms_description']

        schedule_results = schedule_sms_with_sms_description(sms_description)
        status += schedule_results['status'] + " "
        sms_scheduled_saved = schedule_results['sms_scheduled_saved']
        sms_scheduled_id = schedule_results['sms_scheduled_id']
        sms_scheduled = schedule_results['sms_scheduled']

        if sms_scheduled_saved:
            send_results = sms_manager.send_scheduled_sms(sms_scheduled)
            sms_scheduled_sent = send_results['sms_scheduled_sent']
            status += send_results['status']

    results = {
        'status':               status,
        'success':              True,
        'sms_scheduled_saved':  sms_scheduled_saved,
        'sms_scheduled_sent':   sms_scheduled_sent,
        'sms_scheduled_id':     sms_scheduled_id,
    }
    return results


def voter_sms_phone_number_retrieve_for_api(voter_device_id):  # voterSMSPhoneNumberRetrieve
    """

    :param voter_device_id:
    :return:
    """
    sms_phone_number_list_found = False
    status = ""
    success = True

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                       device_id_results['status'],
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'sms_phone_number_list_found':  False,
            'sms_phone_number_list':        [],
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not voter_results['voter_found']:
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                       status,
            'success':                      False,
            'voter_device_id':              voter_device_id,
            'sms_phone_number_list_found':  False,
            'sms_phone_number_list':        [],
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    sms_manager = SMSManager()
    merge_results = sms_manager.find_and_merge_all_duplicate_sms(voter_we_vote_id)
    status += merge_results['status']

    sms_phone_number_list_augmented = []
    sms_results = sms_manager.retrieve_voter_sms_phone_number_list(voter_we_vote_id)
    status += sms_results['status']
    if sms_results['sms_phone_number_list_found']:
        sms_phone_number_list_found = True
        sms_phone_number_list = sms_results['sms_phone_number_list']

        # Remove duplicates: sms_we_vote_id
        merge_results = heal_primary_sms_data_for_voter(sms_phone_number_list, voter)
        sms_phone_number_list = merge_results['sms_phone_number_list']
        status += merge_results['status']

        augment_results = augment_sms_phone_number_list(sms_phone_number_list, voter)
        sms_phone_number_list_augmented = augment_results['sms_phone_number_list']
        status += augment_results['status']

    json_data = {
        'status':                       status,
        'success':                      success,
        'voter_device_id':              voter_device_id,
        'sms_phone_number_list_found':  sms_phone_number_list_found,
        'sms_phone_number_list':        sms_phone_number_list_augmented,
    }
    return json_data


def voter_sms_phone_number_sign_in_for_api(voter_device_id, sms_secret_key):  # voterSMSPhoneNumberSignIn
    """
    :param voter_device_id:
    :param sms_secret_key:
    :return:
    """
    sms_secret_key_belongs_to_this_voter = False
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                                   device_id_results['status'],
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'sms_ownership_is_verified':              False,
            'sms_secret_key_belongs_to_this_voter':   False,
            'sms_phone_number_found':                      False,
            'voter_we_vote_id_from_secret_key':         "",
        }
        return json_data

    if not positive_value_exists(sms_secret_key):
        error_results = {
            'status':                                   "VOTER_SMS_PHONE_NUMBER_VERIFY_MISSING_SECRET_KEY",
            'success':                                  False,
            'voter_device_id':                          voter_device_id,
            'sms_ownership_is_verified':              False,
            'sms_secret_key_belongs_to_this_voter':   False,
            'sms_phone_number_found':                      False,
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
            'sms_ownership_is_verified':              False,
            'sms_secret_key_belongs_to_this_voter':   False,
            'sms_phone_number_found':                      False,
            'voter_we_vote_id_from_secret_key':         "",
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    sms_manager = SMSManager()
    # Look to see if there is an SMSPhoneNumber entry for the incoming sms_phone_number or sms_we_vote_id
    sms_results = sms_manager.retrieve_sms_phone_number_from_secret_key(sms_secret_key)
    if not sms_results['sms_phone_number_found']:
        error_results = {
            'status':                               "SMS_NOT_FOUND_FROM_SECRET_KEY",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sms_ownership_is_verified':            False,
            'sms_secret_key_belongs_to_this_voter': False,
            'sms_phone_number_found':               False,
            'voter_we_vote_id_from_secret_key':     "",
        }
        return error_results

    success = sms_results['success']
    status += sms_results['status']
    sms_phone_number = sms_results['sms_phone_number']
    sms_phone_number_found = True

    sms_ownership_is_verified = sms_phone_number.sms_ownership_is_verified
    if voter_we_vote_id == sms_phone_number.voter_we_vote_id:
        sms_secret_key_belongs_to_this_voter = True

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'voter_device_id':                          voter_device_id,
        'sms_ownership_is_verified':              sms_ownership_is_verified,
        'sms_secret_key_belongs_to_this_voter':   sms_secret_key_belongs_to_this_voter,
        'sms_phone_number_found':                      sms_phone_number_found,
        'voter_we_vote_id_from_secret_key':         sms_phone_number.voter_we_vote_id,
    }
    return json_data


def voter_sms_phone_number_save_for_api(  # voterSMSPhoneNumberSave
        voter_device_id='',
        sms_phone_number='',
        incoming_sms_we_vote_id='',
        send_sign_in_code_sms=False,
        resend_verification_sms=False,
        make_primary_sms_phone_number=False,
        delete_sms=False,
        web_app_root_url=''):
    """
    voterSMSPhoneNumberSave
    :param voter_device_id:
    :param sms_phone_number:
    :param incoming_sms_we_vote_id:
    :param send_sign_in_code_sms:
    :param resend_verification_sms:
    :param make_primary_sms_phone_number:
    :param delete_sms:
    :param web_app_root_url:
    :return:
    """
    sms_phone_number_we_vote_id = ""
    sms_phone_number_saved_we_vote_id = ""
    sms_phone_number_created = False
    sms_phone_number_deleted = False
    verification_sms_sent = False
    link_to_sign_in_sms_sent = False
    sign_in_code_sms_sent = False
    send_verification_sms = False
    sms_phone_number_found = False
    sms_phone_number_list_found = False
    status = ""
    success = False

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':                               device_id_results['status'],
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sms_phone_number':                     sms_phone_number,
            'sms_phone_number_we_vote_id':          incoming_sms_we_vote_id,
            'sms_phone_number_saved_we_vote_id':    "",
            'sms_phone_number_created':             False,
            'sms_phone_number_deleted':             False,
            'verification_sms_sent':                False,
            'link_to_sign_in_sms_sent':             False,
            'sign_in_code_sms_sent':                False,
            'sms_phone_number_already_owned_by_other_voter': False,
            'sms_phone_number_already_owned_by_this_voter': False,
            'sms_phone_number_found':               False,
            'sms_phone_number_list_found':          False,
            'sms_phone_number_list':                [],
            'secret_code_system_locked_for_this_voter_device_id': False,
        }
        return json_data

    # Is the sms_phone_number a valid sms address?
    if positive_value_exists(incoming_sms_we_vote_id):
        # We are happy
        pass
    elif positive_value_exists(sms_phone_number):
        if not validate_sms_phone_number(sms_phone_number):
            error_results = {
                'status':                               "VOTER_SMS_PHONE_NUMBER_SAVE_MISSING_VALID_SMS ",
                'success':                              False,
                'voter_device_id':                      voter_device_id,
                'sms_phone_number':                     sms_phone_number,
                'sms_phone_number_we_vote_id':          incoming_sms_we_vote_id,
                'sms_phone_number_saved_we_vote_id':    "",
                'sms_phone_number_created':             False,
                'sms_phone_number_deleted':             False,
                'verification_sms_sent':                False,
                'link_to_sign_in_sms_sent':             False,
                'sign_in_code_sms_sent':                False,
                'sms_phone_number_already_owned_by_other_voter': False,
                'sms_phone_number_already_owned_by_this_voter': False,
                'sms_phone_number_found':               False,
                'sms_phone_number_list_found':          False,
                'sms_phone_number_list':                [],
                'secret_code_system_locked_for_this_voter_device_id': False,
            }
            return error_results
    else:
        # We need EITHER incoming_sms_we_vote_id or sms_phone_number
        error_results = {
            'status':                               "VOTER_SMS_PHONE_NUMBER_SAVE_MISSING_SMS ",
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sms_phone_number':                     sms_phone_number,
            'sms_phone_number_we_vote_id':          "",
            'sms_phone_number_saved_we_vote_id':    incoming_sms_we_vote_id,
            'sms_phone_number_created':             False,
            'sms_phone_number_deleted':             False,
            'verification_sms_sent':                False,
            'link_to_sign_in_sms_sent':             False,
            'sign_in_code_sms_sent':                False,
            'sms_phone_number_already_owned_by_other_voter': False,
            'sms_phone_number_already_owned_by_this_voter': False,
            'sms_phone_number_found':               False,
            'sms_phone_number_list_found':          False,
            'sms_phone_number_list':                [],
            'secret_code_system_locked_for_this_voter_device_id': False,
        }
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if not voter_results['voter_found']:
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results = {
            'status':                               status,
            'success':                              False,
            'voter_device_id':                      voter_device_id,
            'sms_phone_number':                     sms_phone_number,
            'sms_phone_number_we_vote_id':          "",
            'sms_phone_number_saved_we_vote_id':    "",
            'sms_phone_number_created':             False,
            'sms_phone_number_deleted':             False,
            'verification_sms_sent':                False,
            'link_to_sign_in_sms_sent':             False,
            'sign_in_code_sms_sent':                False,
            'sms_phone_number_already_owned_by_other_voter': False,
            'sms_phone_number_already_owned_by_this_voter': False,
            'sms_phone_number_found':               False,
            'sms_phone_number_list_found':          False,
            'sms_phone_number_list':                [],
            'secret_code_system_locked_for_this_voter_device_id': False,
        }
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    sms_manager = SMSManager()
    sms_phone_number_already_owned_by_this_voter = False
    sms_phone_number_already_owned_by_other_voter = False
    recipient_sms_secret_key = ''
    verified_sms_phone_number = SMSPhoneNumber()
    verified_sms_phone_number_we_vote_id = ""
    if positive_value_exists(sms_phone_number):
        parsed_sms_phone_number = phonenumbers.parse(sms_phone_number, "US")
        normalized_sms_phone_number = \
            phonenumbers.format_number(parsed_sms_phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    else:
        normalized_sms_phone_number = ''
    sms_phone_number_list = []
    # Is this sms already verified by another account?
    find_verified_sms_results = sms_manager.retrieve_primary_sms_with_ownership_verified(
        normalized_sms_phone_number=normalized_sms_phone_number, sms_we_vote_id=incoming_sms_we_vote_id)
    if find_verified_sms_results['sms_phone_number_found']:
        verified_sms_phone_number = find_verified_sms_results['sms_phone_number']
        verified_sms_phone_number_we_vote_id = verified_sms_phone_number.we_vote_id
        if verified_sms_phone_number.voter_we_vote_id != voter_we_vote_id:
            sms_phone_number_already_owned_by_other_voter = True

    if sms_phone_number_already_owned_by_other_voter:
        if send_sign_in_code_sms:
            # Make sure the verified sms number has a secret_key
            sms_phone_number_we_vote_id = verified_sms_phone_number.we_vote_id
            sms_phone_number_saved_we_vote_id = ""
            if positive_value_exists(verified_sms_phone_number.secret_key):
                recipient_sms_secret_key = verified_sms_phone_number.secret_key
            else:
                recipient_sms_secret_key = \
                    sms_manager.update_sms_phone_number_with_new_secret_key(sms_phone_number_we_vote_id)
            sms_phone_number_created = False
            sms_phone_number_found = True
        else:
            status += "SMS_ALREADY_OWNED_BY_ANOTHER_VOTER "
            error_results = {
                'status':                               status,
                'success':                              True,
                'voter_device_id':                      voter_device_id,
                'sms_phone_number':                     sms_phone_number,
                'sms_phone_number_we_vote_id':          verified_sms_phone_number_we_vote_id,
                'sms_phone_number_saved_we_vote_id':    "",
                'sms_phone_number_created':             False,
                'sms_phone_number_deleted':             False,
                'verification_sms_sent':                False,
                'link_to_sign_in_sms_sent':             False,
                'sign_in_code_sms_sent':                False,
                'sms_phone_number_already_owned_by_other_voter': True,
                'sms_phone_number_already_owned_by_this_voter': sms_phone_number_already_owned_by_this_voter,
                'sms_phone_number_found':               True,
                'sms_phone_number_list_found':          False,
                'sms_phone_number_list':                [],
                'secret_code_system_locked_for_this_voter_device_id': False,
            }
            return error_results

    # Look to see if there is an SMSPhoneNumber entry for the incoming sms_phone_number or
    #  incoming_sms_we_vote_id for this voter
    sms_results = sms_manager.retrieve_sms_phone_number(normalized_sms_phone_number, incoming_sms_we_vote_id,
                                                        voter_we_vote_id)
    if sms_results['sms_phone_number_found']:
        sms_phone_number = sms_results['sms_phone_number']
        sms_phone_number_list.append(sms_phone_number)
    elif sms_results['sms_phone_number_list_found']:
        # This sms was used by more than one person
        sms_phone_number_list = sms_results['sms_phone_number_list']

    # Cycle through all SMSPhoneNumber entries with "sms_phone_number" or "incoming_sms_we_vote_id"
    for sms_phone_number in sms_phone_number_list:
        sms_phone_number_we_vote_id = sms_phone_number.we_vote_id
        sms_phone_number_saved_we_vote_id = ""
        normalized_sms_phone_number = sms_phone_number.normalized_sms_phone_number
        if positive_value_exists(sms_phone_number.secret_key):
            recipient_sms_secret_key = sms_phone_number.secret_key
        else:
            recipient_sms_secret_key = \
                sms_manager.update_sms_phone_number_with_new_secret_key(sms_phone_number_we_vote_id)
        sms_phone_number_created = False
        sms_phone_number_found = True
        if delete_sms:
            # If this sms is cached in a voter record, remove it as long as primary_sms_we_vote_id
            # matches sms_phone_number.we_vote_id
            primary_sms_phone_number_deleted = False
            if positive_value_exists(voter.primary_sms_we_vote_id) \
                    and voter.primary_sms_we_vote_id.lower() == sms_phone_number.we_vote_id.lower():
                try:
                    voter.primary_sms_we_vote_id = None
                    voter.sms_ownership_is_verified = False
                    voter.normalized_sms_phone_number = None
                    voter.save()
                    primary_sms_phone_number_deleted = True
                    status += "VOTER_PRIMARY_SMS_PHONE_NUMBER_REMOVED "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_REMOVE_VOTER_PRIMARY_SMS_PHONE_NUMBER "
            try:
                sms_phone_number.delete()
                sms_phone_number_deleted = True
                status += "DELETED_SMS_PHONE_NUMBER "
                success = True
            except Exception as e:
                status += "UNABLE_TO_DELETE_SMS_PHONE_NUMBER " + str(e) + " "
                success = False

            if sms_phone_number_deleted:
                # Delete all other identical phone numbers associated with this account that are not be verified
                if positive_value_exists(normalized_sms_phone_number):
                    duplicate_results = sms_manager.retrieve_sms_phone_number(
                        normalized_sms_phone_number, voter_we_vote_id=voter_we_vote_id)
                    if duplicate_results['sms_phone_number_found']:
                        sms_phone_number_to_delete = duplicate_results['sms_phone_number']
                        if not positive_value_exists(sms_phone_number_to_delete.sms_ownership_is_verified):
                            try:
                                sms_phone_number_to_delete.delete()
                                status += "DELETED_DUP_SMS1 "
                            except Exception as e:
                                status += "UNABLE_TO_DELETE_DUP_SMS1 "
                    elif duplicate_results['sms_phone_number_list_found']:
                        sms_phone_number_list_for_delete = duplicate_results['sms_phone_number_list']
                        for sms_phone_number_to_delete in sms_phone_number_list_for_delete:
                            if not positive_value_exists(
                                    sms_phone_number_to_delete.sms_ownership_is_verified):
                                try:
                                    sms_phone_number_to_delete.delete()
                                    status += "DELETED_DUP_SMS2 "
                                except Exception as e:
                                    status += "UNABLE_TO_DELETE_DUP_SMS2 "

                # If there are any other verified sms, promote the first one to be the voter's verified sms
                if positive_value_exists(primary_sms_phone_number_deleted):
                    temp_sms_phone_number = ""
                    temp_incoming_sms_we_vote_id = ""
                    sms_promotion_results = sms_manager.retrieve_sms_phone_number(
                        temp_sms_phone_number, temp_incoming_sms_we_vote_id, voter_we_vote_id=voter_we_vote_id)
                    sms_phone_number_list_for_promotion = []
                    if sms_promotion_results['sms_phone_number_list_found']:
                        # This sms was used by more than one person
                        sms_phone_number_list_for_promotion = sms_promotion_results['sms_phone_number_list']
                        sms_phone_number_list_found_for_promotion_to_primary = True
                    else:
                        sms_phone_number_list_found_for_promotion_to_primary = False

                    if sms_phone_number_list_found_for_promotion_to_primary:
                        for sms_phone_number_for_promotion in sms_phone_number_list_for_promotion:
                            if positive_value_exists(sms_phone_number_for_promotion.sms_ownership_is_verified):
                                # Assign this as voter's new primary sms
                                try:
                                    voter.primary_sms_we_vote_id = sms_phone_number_for_promotion.we_vote_id
                                    voter.sms_ownership_is_verified = True
                                    voter.normalized_sms_phone_number = \
                                        sms_phone_number_for_promotion.normalized_sms_phone_number
                                    voter.save()
                                    sms_phone_number_already_owned_by_this_voter = True
                                    status += "SAVED_SMS_PHONE_NUMBER_AS_NEW_PRIMARY "
                                    success = True
                                except Exception as e:
                                    status += "UNABLE_TO_SAVE_SMS_PHONE_NUMBER_AS_NEW_PRIMARY "
                                    remove_cached_results = \
                                        voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(
                                            sms_phone_number_for_promotion)
                                    status += remove_cached_results['status']
                                    try:
                                        voter.primary_sms_we_vote_id = sms_phone_number_for_promotion.we_vote_id
                                        voter.sms_ownership_is_verified = True
                                        voter.normalized_sms_phone_number = \
                                            sms_phone_number_for_promotion.normalized_sms_phone_number
                                        voter.save()
                                        status += "SAVED_SMS_PHONE_NUMBER_AS_NEW_PRIMARY "
                                        success = True
                                    except Exception as e:
                                        status += "UNABLE_TO_REMOVE_VOTER_PRIMARY_SMS_PHONE_NUMBER2 "
                                break  # Stop looking at sms addresses to make the new primary

            break  # TODO DALE Is there ever a case where we want to delete more than one sms at a time?
        elif make_primary_sms_phone_number and positive_value_exists(incoming_sms_we_vote_id):
            # We know we want to make incoming_sms_we_vote_id the primary sms
            if not sms_phone_number.sms_ownership_is_verified:
                # Do not make an unverified sms primary
                pass
            elif sms_phone_number.we_vote_id.lower() == incoming_sms_we_vote_id.lower():
                # Make sure this is the primary
                if positive_value_exists(voter.primary_sms_we_vote_id) \
                        and voter.primary_sms_we_vote_id.lower() == sms_phone_number.we_vote_id.lower():
                    # If already the primary sms, leave it but make sure to heal the data
                    try:
                        voter.primary_sms_we_vote_id = sms_phone_number.we_vote_id
                        voter.sms_ownership_is_verified = True
                        voter.normalized_sms_phone_number = sms_phone_number.normalized_sms_phone_number
                        voter.save()
                        sms_phone_number_already_owned_by_this_voter = True
                        status += "SAVED_SMS_PHONE_NUMBER_AS_PRIMARY-HEALING_DATA "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_SMS_PHONE_NUMBER_AS_PRIMARY-HEALING_DATA "
                        remove_cached_results = \
                            voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(
                                sms_phone_number)
                        status += remove_cached_results['status']
                        try:
                            voter.primary_sms_we_vote_id = sms_phone_number.we_vote_id
                            voter.sms_ownership_is_verified = True
                            voter.normalized_sms_phone_number = sms_phone_number.normalized_sms_phone_number
                            voter.save()
                            sms_phone_number_already_owned_by_this_voter = True
                            status += "SAVED_SMS_PHONE_NUMBER_AS_NEW_PRIMARY "
                            success = True
                        except Exception as e:
                            status += "UNABLE_TO_REMOVE_VOTER_PRIMARY_SMS_PHONE_NUMBER2 "
                            success = False
                else:
                    # Set this sms address as the primary

                    # First, search for any other voter records that think they are using this
                    # normalized_sms_phone_number or primary_sms_we_vote_id. If there are other records
                    # using these, they are bad data that don't reflect
                    remove_cached_results = \
                        voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(
                            sms_phone_number)
                    status += remove_cached_results['status']

                    # And now, update current voter
                    try:
                        voter.primary_sms_we_vote_id = sms_phone_number.we_vote_id
                        voter.sms_ownership_is_verified = True
                        voter.normalized_sms_phone_number = sms_phone_number.normalized_sms_phone_number
                        voter.save()
                        sms_phone_number_already_owned_by_this_voter = True
                        status += "SAVED_SMS_PHONE_NUMBER_AS_PRIMARY "
                        success = True
                    except Exception as e:
                        status += "UNABLE_TO_SAVE_SMS_PHONE_NUMBER_AS_PRIMARY "
                        success = False
                break  # Break out of the sms_phone_number_list loop
            elif positive_value_exists(voter.primary_sms_we_vote_id) \
                    and voter.primary_sms_we_vote_id.lower() == sms_phone_number.we_vote_id.lower():
                # If here, we know that we are not looking at the sms we want to make primary,
                # but we only want to wipe out a voter's primary sms when we replace it with another sms
                pass

    send_verification_sms = False
    if sms_phone_number_deleted:
        # We cannot proceed with this sms address, since it was just marked deleted
        pass
    elif not positive_value_exists(incoming_sms_we_vote_id):
        # Save the new sms address
        sms_ownership_is_verified = False
        sms_save_results = sms_manager.create_sms_phone_number(
            normalized_sms_phone_number, voter_we_vote_id, sms_ownership_is_verified)

        if sms_save_results['sms_phone_number_saved']:
            # Send verification sms
            send_verification_sms = True
            new_sms_phone_number = sms_save_results['sms_phone_number']
            sms_phone_number_we_vote_id = new_sms_phone_number.we_vote_id
            sms_phone_number_saved_we_vote_id = new_sms_phone_number.we_vote_id
            normalized_sms_phone_number = new_sms_phone_number.normalized_sms_phone_number
            if positive_value_exists(new_sms_phone_number.secret_key):
                recipient_sms_secret_key = new_sms_phone_number.secret_key
            else:
                recipient_sms_secret_key = \
                    sms_manager.update_sms_phone_number_with_new_secret_key(sms_phone_number_we_vote_id)
            sms_phone_number_created = True
            sms_phone_number_found = True
            success = True
            status += sms_save_results['status']
        else:
            send_verification_sms = False
            success = False
            status += "UNABLE_TO_SAVE_SMS_PHONE_NUMBER "

    secret_code_system_locked_for_this_voter_device_id = False
    voter_device_link_manager = VoterDeviceLinkManager()
    if send_sign_in_code_sms:
        # Run the code to send sms with sign in verification code (6 digit)
        sms_phone_number_we_vote_id = sms_phone_number_we_vote_id \
            if positive_value_exists(sms_phone_number_we_vote_id) \
            else incoming_sms_we_vote_id
        # We need to link a randomly generated 6 digit code to this voter_device_id
        results = voter_device_link_manager.retrieve_voter_secret_code_up_to_date(voter_device_id)
        secret_code = results['secret_code']
        secret_code_system_locked_for_this_voter_device_id = \
            results['secret_code_system_locked_for_this_voter_device_id']

        if positive_value_exists(secret_code_system_locked_for_this_voter_device_id):
            status += results['status']
            success = True
        elif positive_value_exists(secret_code):
            # And we need to store the secret_key (as opposed to the 6 digit secret code) in the voter_device_link
            #  so we can match this phone number to this session
            link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if link_results['voter_device_link_found']:
                voter_device_link = link_results['voter_device_link']
                update_results = voter_device_link_manager.update_voter_device_link_with_sms_secret_key(
                    voter_device_link, recipient_sms_secret_key)
                if not positive_value_exists(update_results['success']):
                    status += update_results['status']
                    # Wipe out existing value and save again
                    voter_device_link_manager.clear_secret_key(sms_secret_key=recipient_sms_secret_key)
                    update_results = voter_device_link_manager.update_voter_device_link_with_sms_secret_key(
                        voter_device_link, recipient_sms_secret_key)
                    if not positive_value_exists(update_results['success']):
                        status += update_results['status']
            else:
                status += "VOTER_DEVICE_LINK_NOT_UPDATED_WITH_SMS_SECRET_KEY "

            link_send_results = schedule_sign_in_code_sms(
                voter_we_vote_id, voter_we_vote_id,
                sms_phone_number_we_vote_id, normalized_sms_phone_number,
                secret_code, web_app_root_url=web_app_root_url)
            status += link_send_results['status']
            sms_scheduled_sent = link_send_results['sms_scheduled_sent']
            if sms_scheduled_sent:
                sign_in_code_sms_sent = True
                success = True
            else:
                status += 'SCHEDULE_SIGN_IN_CODE_SMS_FAILED '
                success = False
        else:
            status += results['status']
            status += 'RETRIEVE_VOTER_SECRET_CODE_UP_TO_DATE_FAILED '
            success = False
    elif send_verification_sms:
        # We need to link a randomly generated 6 digit code to this voter_device_id
        results = voter_device_link_manager.retrieve_voter_secret_code_up_to_date(voter_device_id)
        # Run the code to send verification sms
        sms_phone_number_we_vote_id = sms_phone_number_we_vote_id \
            if positive_value_exists(sms_phone_number_we_vote_id) \
            else incoming_sms_we_vote_id
        verifications_send_results = schedule_verification_sms(
            voter_we_vote_id, voter_we_vote_id, sms_phone_number_we_vote_id, normalized_sms_phone_number,
            results['secret_code'], web_app_root_url=web_app_root_url)
        status += verifications_send_results['status']
        sms_scheduled_saved = verifications_send_results['sms_scheduled_saved']
        if sms_scheduled_saved:
            verification_sms_sent = True
            success = True

    # Now that the save is complete, retrieve the updated list
    sms_phone_number_list_augmented = []
    sms_results = sms_manager.retrieve_voter_sms_phone_number_list(voter_we_vote_id)
    if sms_results['sms_phone_number_list_found']:
        sms_phone_number_list_found = True
        sms_phone_number_list = sms_results['sms_phone_number_list']
        augment_results = augment_sms_phone_number_list(sms_phone_number_list, voter)
        sms_phone_number_list_augmented = augment_results['sms_phone_number_list']
        status += augment_results['status']

    json_data = {
        'status':                               status,
        'success':                              success,
        'voter_device_id':                      voter_device_id,
        'sms_phone_number':                     normalized_sms_phone_number,
        'sms_phone_number_we_vote_id':          sms_phone_number_we_vote_id,
        'sms_phone_number_already_owned_by_other_voter':    sms_phone_number_already_owned_by_other_voter,
        'sms_phone_number_already_owned_by_this_voter':     sms_phone_number_already_owned_by_this_voter,
        'sms_phone_number_found':               sms_phone_number_found,
        'sms_phone_number_list_found':          sms_phone_number_list_found,
        'sms_phone_number_list':                sms_phone_number_list_augmented,
        'sms_phone_number_saved_we_vote_id':    sms_phone_number_saved_we_vote_id,
        'sms_phone_number_created':             sms_phone_number_created,
        'sms_phone_number_deleted':             sms_phone_number_deleted,
        'verification_sms_sent':                verification_sms_sent,
        'link_to_sign_in_sms_sent':             link_to_sign_in_sms_sent,
        'sign_in_code_sms_sent':                sign_in_code_sms_sent,
        'secret_code_system_locked_for_this_voter_device_id': secret_code_system_locked_for_this_voter_device_id,
    }
    return json_data
