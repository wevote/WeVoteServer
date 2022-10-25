# email_outbound/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .functions import merge_message_content_with_template
from .models import EmailAddress, EmailManager, EmailOutboundDescription, EmailScheduled,\
    GENERIC_EMAIL_TEMPLATE, LINK_TO_SIGN_IN_TEMPLATE, SendGridApiCounterManager, \
    SIGN_IN_CODE_EMAIL_TEMPLATE, TO_BE_PROCESSED, VERIFY_EMAIL_ADDRESS_TEMPLATE
from config.base import get_environment_variable
from exception.models import handle_exception
import json
from organization.controllers import transform_web_app_url
from organization.models import OrganizationManager, INDIVIDUAL
import requests
from validate_email import validate_email
from voter.models import VoterContactEmail, VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import extract_first_name_from_full_name, extract_last_name_from_full_name, \
    is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

SENDGRID_API_KEY = get_environment_variable("SENDGRID_API_KEY", no_exception=True)
SENDGRID_EMAIL_VALIDATION_URL = "https://api.sendgrid.com/v3/"
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def augment_email_address_list(email_address_list, voter):
    email_address_list_augmented = []
    primary_email_address = None
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


# 2021-09-30 SendGrid email verification requires Pro account which costs $90/month - Not turned on currently
# TODO: This function needs to be finished
def augment_emails_for_voter_with_sendgrid(voter_we_vote_id=''):
    status = ''
    success = True

    voter_manager = VoterManager()
    # Augment all voter contacts with data from SendGrid
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id)
    if voter_contact_results['voter_contact_email_list_found']:
        email_addresses_returned_list = voter_contact_results['email_addresses_returned_list']

        # Get list of emails which need to be augmented (updated) with data from SendGrid
        contact_email_augmented_list_as_dict = {}
        results = voter_manager.retrieve_contact_email_augmented_list(
            email_address_text_list=email_addresses_returned_list,
            read_only=False,
        )
        if results['contact_email_augmented_list_found']:
            # We retrieve all existing so we don't need 200 queries within update_or_create_contact_email_augmented
            contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']

        # Make sure we have an augmented entry for each email
        for email_address_text in email_addresses_returned_list:
            voter_manager.update_or_create_contact_email_augmented(
                email_address_text=email_address_text,
                existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict)

        # Get list of emails which need to be augmented (updated) with data from TargetSmart
        results = voter_manager.retrieve_contact_email_augmented_list(
            checked_against_sendgrid_more_than_x_days_ago=15,
            email_address_text_list=email_addresses_returned_list,
            read_only=False,
        )
        if results['contact_email_augmented_list_found']:
            contact_email_augmented_list = results['contact_email_augmented_list']
            contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']
            email_addresses_returned_list = results['email_addresses_returned_list']
            email_addresses_remaining_list = email_addresses_returned_list

            # Now reach out to SendGrid, in blocks of 200
            failed_api_count = 0
            loop_count = 0
            safety_valve_triggered = False
            while len(email_addresses_remaining_list) > 0 and not safety_valve_triggered:
                loop_count += 1
                safety_valve_triggered = loop_count >= 250
                email_addresses_for_query = email_addresses_remaining_list[:200]
                email_addresses_remaining_list = \
                    list(set(email_addresses_remaining_list) - set(email_addresses_for_query))
                sendgrid_augmented_email_list_dict = {}
                sendgrid_results = query_sendgrid_api_to_augment_email_list(email_list=email_addresses_for_query)
                if not sendgrid_results['success']:
                    failed_api_count += 1
                    if failed_api_count >= 3:
                        safety_valve_triggered = True
                        status += "SENDGRID_API_FAILED_3_TIMES "
                elif sendgrid_results['augmented_email_list_found']:
                    # A dict of results from TargetSmart, with email_address_text as the key
                    sendgrid_augmented_email_list_dict = sendgrid_results['augmented_email_list_dict']

                    # Update our cached augmented data
                    for contact_email_augmented in contact_email_augmented_list:
                        if contact_email_augmented.email_address_text in sendgrid_augmented_email_list_dict:
                            augmented_email = \
                                sendgrid_augmented_email_list_dict[contact_email_augmented.email_address_text]
                            sendgrid_id = augmented_email['sendgrid_id'] \
                                if 'sendgrid_id' in augmented_email else None
                            results = voter_manager.update_or_create_contact_email_augmented(
                                checked_against_sendgrid=True,
                                email_address_text=contact_email_augmented.email_address_text,
                                existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict,
                                sendgrid_id=sendgrid_id,
                            )
                            if results['success']:
                                # Now update all the VoterContactEmail entries, regardless of whose contact it is
                                try:
                                    number_updated = VoterContactEmail.objects.filter(
                                        email_address_text__iexact=contact_email_augmented.email_address_text) \
                                        .update(state_code='')
                                    status += "NUMBER_OF_VOTER_CONTACT_EMAIL_UPDATED: " + str(number_updated) + " "
                                except Exception as e:
                                    status += "NUMBER_OF_VOTER_CONTACT_EMAIL_NOT_UPDATED: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
    }
    return results


def augment_emails_for_voter_with_we_vote_data(voter_we_vote_id=''):
    status = ''
    success = True

    from friend.models import FriendManager
    friend_manager = FriendManager()
    from voter.models import VoterManager
    voter_manager = VoterManager()
    # Augment all voter contacts with updated data from We Vote
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id)
    if voter_contact_results['voter_contact_email_list_found']:
        email_addresses_returned_list = voter_contact_results['email_addresses_returned_list']

        # Get list of emails which need to be augmented (updated) with data
        #  We need to do this for later steps where we reach out to other services like Open People Search and Twilio
        contact_email_augmented_list_as_dict = {}
        results = voter_manager.retrieve_contact_email_augmented_list(
            email_address_text_list=email_addresses_returned_list,
            read_only=False,
        )
        if results['contact_email_augmented_list_found']:
            # We retrieve all existing at once so we don't need 200 separate queries
            #  within update_or_create_contact_email_augmented
            contact_email_augmented_list_as_dict = results['contact_email_augmented_list_as_dict']

        # Make sure we have an augmented entry for each email
        for email_address_text in email_addresses_returned_list:
            if email_address_text.lower() not in contact_email_augmented_list_as_dict:
                voter_manager.update_or_create_contact_email_augmented(
                    email_address_text=email_address_text,
                    existing_contact_email_augmented_dict=contact_email_augmented_list_as_dict)

        # Now augment VoterContactEmail table with data from We Vote database to help find friends
        # Start by retrieving checking EmailAddress table (in one query) for all entries we currently have in our db
        email_addresses_found_list = []
        try:
            queryset = EmailAddress.objects.filter(normalized_email_address__in=email_addresses_returned_list)
            queryset = queryset.filter(email_ownership_is_verified=True)
            email_addresses_found_list = list(queryset)
        except Exception as e:
            status += "FAILED_TO_RETRIEVE_EMAIL_ADDRESSES: " + str(e) + ' '

        for email_address_object in email_addresses_found_list:
            # Retrieve the voter to see if there is data to use in the VoterContactEmail table
            results = voter_manager.retrieve_voter_by_we_vote_id(email_address_object.voter_we_vote_id)
            if results['voter_found']:
                voter = results['voter']
                voter_data_found = positive_value_exists(voter.we_vote_hosted_profile_image_url_medium) or \
                    positive_value_exists(voter.we_vote_id)
                if results['success'] and voter_data_found:
                    # Now update all the VoterContactEmail entries, regardless of whose contact it is
                    try:
                        if positive_value_exists(voter.state_code_for_display):
                            number_updated = VoterContactEmail.objects.filter(
                                email_address_text__iexact=email_address_object.normalized_email_address) \
                                .update(
                                    state_code=voter.state_code_for_display,
                                    voter_we_vote_id=voter.we_vote_id,
                                    we_vote_hosted_profile_image_url_medium=
                                    voter.we_vote_hosted_profile_image_url_medium)
                        else:
                            number_updated = VoterContactEmail.objects.filter(
                                email_address_text__iexact=email_address_object.normalized_email_address) \
                                .update(
                                    voter_we_vote_id=voter.we_vote_id,
                                    we_vote_hosted_profile_image_url_medium=
                                    voter.we_vote_hosted_profile_image_url_medium)
                        status += "NUMBER_OF_VOTER_CONTACT_EMAIL_UPDATED: " + str(number_updated) + " "
                    except Exception as e:
                        status += "FAILED_TO_UPDATE_VOTER_CONTACT_EMAIL: " + str(e) + ' '

    # Retrieve again now that voter_we_vote_id has been updated, so we can see if they are a friend
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id,
        read_only=False)
    if voter_contact_results['voter_contact_email_list_found']:
        voter_contact_email_list = voter_contact_results['voter_contact_email_list']
        # Retrieve main voter's friends, and then update voter contacts with is_friend
        friend_results = friend_manager.retrieve_friends_we_vote_id_list(voter_we_vote_id)
        friends_we_vote_id_list = []
        if friend_results['friends_we_vote_id_list_found']:
            friends_we_vote_id_list = friend_results['friends_we_vote_id_list']
        for voter_contact in voter_contact_email_list:
            if positive_value_exists(voter_contact.voter_we_vote_id):
                should_save_voter_contact = False
                voter_contact_should_be_friend = voter_contact.voter_we_vote_id in friends_we_vote_id_list
                if positive_value_exists(voter_contact.is_friend):
                    if voter_contact_should_be_friend:
                        pass  # all is well!
                    else:
                        voter_contact.is_friend = False
                        should_save_voter_contact = True
                elif voter_contact_should_be_friend:
                    voter_contact.is_friend = True
                    should_save_voter_contact = True
                if should_save_voter_contact:
                    try:
                        voter_contact.save()
                    except Exception as e:
                        status += "COULD_NOT_SAVE_VOTER_CONTACT: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
    }
    return results


def delete_email_address_entries_for_voter(voter_to_delete_we_vote_id, voter_to_delete):
    status = "DELETE_EMAIL_ADDRESSES "
    success = False
    email_addresses_deleted = 0
    email_addresses_not_deleted = 0

    if not positive_value_exists(voter_to_delete_we_vote_id):
        status += "DELETE_EMAIL_ADDRESS_ENTRIES_MISSING_FROM_VOTER_WE_VOTE_ID "
        results = {
            'status':                       status,
            'success':                      success,
            'voter_to_delete_we_vote_id':   voter_to_delete_we_vote_id,
            'voter_to_delete':              voter_to_delete,
            'email_addresses_deleted':      email_addresses_deleted,
            'email_addresses_not_deleted':  email_addresses_not_deleted,
        }
        return results

    email_manager = EmailManager()
    email_address_list_results = email_manager.retrieve_voter_email_address_list(voter_to_delete_we_vote_id)
    if email_address_list_results['email_address_list_found']:
        email_address_list = email_address_list_results['email_address_list']

        for email_address_object in email_address_list:
            try:
                email_address_object.delete()
                email_addresses_deleted += 1
            except Exception as e:
                email_addresses_not_deleted += 1
                status += "UNABLE_TO_DELETE_EMAIL_ADDRESS " + str(e) + " "

        status += "EMAIL_ADDRESSES-DELETED: " + str(email_addresses_deleted) + \
                  ", NOT_DELETED: " + str(email_addresses_not_deleted) + " "
    else:
        status += email_address_list_results['status']

    if positive_value_exists(voter_to_delete.primary_email_we_vote_id):
        # Remove the email information so we don't have a future conflict
        try:
            voter_to_delete.email = None
            voter_to_delete.primary_email_we_vote_id = None
            voter_to_delete.email_ownership_is_verified = False
            voter_to_delete.save()
        except Exception as e:
            status += "CANNOT_CLEAR_OUT_VOTER_EMAIL_INFO: " + str(e) + " "

    results = {
        'status':                       status,
        'success':                      success,
        'voter_to_delete':              voter_to_delete,
        'voter_to_delete_we_vote_id':   voter_to_delete_we_vote_id,
        'email_addresses_deleted':      email_addresses_deleted,
        'email_addresses_not_deleted':  email_addresses_not_deleted,
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
                status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES " + str(e) + " "
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
                    status += "UNABLE_TO_SAVE_UPDATED_EMAIL_VALUES2 " + str(e) + " "
    else:
        # If here we need to heal data. If here we know that the voter record doesn't have any email info that matches
        #  an email address, so we want to make the first verified email address in the list the new master
        for primary_email_address_candidate in email_address_list:
            if primary_email_address_candidate.email_ownership_is_verified:
                # Now that we have found a verified email, save it to the voter account, and break out of loop
                voter.primary_email_we_vote_id = primary_email_address_candidate.we_vote_id
                voter.email = primary_email_address_candidate.normalized_email_address
                voter.email_ownership_is_verified = True
                try:
                    voter.save()
                    status += "SAVED_PRIMARY_EMAIL_ADDRESS_CANDIDATE "
                except Exception as e:
                    status += "UNABLE_TO_SAVE_PRIMARY_EMAIL_ADDRESS_CANDIDATE " + str(e) + " "
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
                        status += "UNABLE_TO_SAVE_PRIMARY_EMAIL_ADDRESS_CANDIDATE2 " + str(e) + " "
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
        'status':               status,
        'success':              success,
        'email_address_list':   email_address_list_deduped,
    }
    return results


def move_email_address_entries_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id, from_voter, to_voter):
    status = "MOVE_EMAIL_ADDRESSES "
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
            'from_voter': from_voter,
            'to_voter': to_voter,
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
            'from_voter': from_voter,
            'to_voter': to_voter,
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

        status += "MOVE_EMAIL_ADDRESSES-MOVED: " + str(email_addresses_moved) + \
                  ", NOT_MOVED: " + str(email_addresses_not_moved) + " "
    else:
        status += email_address_list_results['status']

    # Now clean up the list of emails
    merge_results = email_manager.find_and_merge_all_duplicate_emails(to_voter_we_vote_id)
    status += merge_results['status']

    email_results = email_manager.retrieve_voter_email_address_list(to_voter_we_vote_id)
    status += email_results['status']
    if email_results['email_address_list_found']:
        email_address_list_found = True
        email_address_list = email_results['email_address_list']

        # Make sure the voter's primary email address matches email table data
        merge_results = heal_primary_email_data_for_voter(email_address_list, to_voter)
        email_address_list = merge_results['email_address_list']
        status += merge_results['status']

    if positive_value_exists(from_voter.primary_email_we_vote_id):
        # Remove the email information so we don't have a future conflict
        try:
            from_voter.email = None
            from_voter.primary_email_we_vote_id = None
            from_voter.email_ownership_is_verified = False
            from_voter.save()
        except Exception as e:
            status += "CANNOT_CLEAR_OUT_VOTER_EMAIL_INFO: " + str(e) + " "

    # Update EmailOutboundDescription entries: Sender
    try:
        email_scheduled_queryset = EmailOutboundDescription.objects.all()
        email_scheduled_queryset.filter(sender_voter_we_vote_id=from_voter_we_vote_id).\
            update(sender_voter_we_vote_id=to_voter_we_vote_id)
        status += 'UPDATED_EMAIL_OUTBOUND-SENDER '
    except Exception as e:
        success = False
        status += 'FAILED_UPDATE_EMAIL_OUTBOUND-SENDER ' + str(e) + " "
    # Recipient
    try:
        email_scheduled_queryset = EmailOutboundDescription.objects.all()
        email_scheduled_queryset.filter(recipient_voter_we_vote_id=from_voter_we_vote_id).\
            update(recipient_voter_we_vote_id=to_voter_we_vote_id)
        status += 'UPDATED_EMAIL_OUTBOUND-RECIPIENT '
    except Exception as e:
        success = False
        status += 'FAILED_UPDATE_EMAIL_OUTBOUND-RECIPIENT ' + str(e) + " "

    # Update EmailScheduled entries: Sender
    try:
        email_scheduled_queryset = EmailScheduled.objects.all()
        email_scheduled_queryset.filter(sender_voter_we_vote_id=from_voter_we_vote_id).\
            update(sender_voter_we_vote_id=to_voter_we_vote_id)
        status += 'UPDATED_EMAIL_SCHEDULED-SENDER '
    except Exception as e:
        success = False
        status += 'FAILED_UPDATE_EMAIL_SCHEDULED-SENDER ' + str(e) + " "
    # Recipient
    try:
        email_scheduled_queryset = EmailScheduled.objects.all()
        email_scheduled_queryset.filter(recipient_voter_we_vote_id=from_voter_we_vote_id).\
            update(recipient_voter_we_vote_id=to_voter_we_vote_id)
        status += 'UPDATED_EMAIL_SCHEDULED-RECIPIENT '
    except Exception as e:
        success = False
        status += 'FAILED_UPDATE_EMAIL_SCHEDULED-RECIPIENT ' + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'to_voter': to_voter,
        'email_addresses_moved': email_addresses_moved,
        'email_addresses_not_moved': email_addresses_not_moved,
    }
    return results


# 2021-09-30 SendGrid email verification requires Pro account which costs $90/month - Not turned on currently
# TODO: This function needs to be finished
def query_sendgrid_api_to_augment_email_list(email_list=None):
    success = True
    status = ""
    augmented_email_list_dict = {}
    augmented_email_list_found = False
    json_from_sendgrid = {}

    if email_list is None or len(email_list) == 0:
        status += "MISSING_EMAIL_LIST "
        success = False
        results = {
            'success': success,
            'status': status,
            'augmented_email_list_found':  augmented_email_list_found,
            'augmented_email_list_dict': augmented_email_list_dict,
        }
        return results

    number_of_items_sent_in_query = len(email_list)

    try:
        api_key = SENDGRID_API_KEY
        emails_param = ",".join(email_list)
        # Get the ballot info at this address
        response = requests.post(
            SENDGRID_EMAIL_VALIDATION_URL,
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            },
            params={
                "emails": emails_param,
            })
        json_from_sendgrid = json.loads(response.text)

        if 'message' in json_from_sendgrid:
            status += json_from_sendgrid['message'] + " "
            if json_from_sendgrid['message'].strip() in ['Failed', 'Forbidden']:
                success = False

        # Use TargetSmart API call counter to track the number of queries we are doing each day
        api_counter_manager = SendGridApiCounterManager()
        api_counter_manager.create_counter_entry(
            'email-search',
            number_of_items_sent_in_query=number_of_items_sent_in_query)
    except Exception as e:
        success = False
        status += 'QUERY_SENDGRID_EMAIL_SEARCH_API_FAILED: ' + str(e) + ' '
        handle_exception(e, logger=logger, exception_message=status)

    if 'results' in json_from_sendgrid:
        results_list_from_sendgrid = json_from_sendgrid['results']
        for augmented_email in results_list_from_sendgrid:
            email_address_text = augmented_email['vb.email_address']
            if positive_value_exists(email_address_text):
                sendgrid_id = augmented_email['vb.voterbase_id']
                sendgrid_source_state = augmented_email['vb.vf_source_state']
                # Last voted?
                # Political party?
                # Full address so we can find their ballot?
                augmented_email_dict = {
                    'email_address_text':       email_address_text,
                    'sendgrid_id':           sendgrid_id,
                    'sendgrid_source_state': sendgrid_source_state,
                }
                augmented_email_list_dict[email_address_text.lower()] = augmented_email_dict

    results = {
        'success': success,
        'status': status,
        'augmented_email_list_found': augmented_email_list_found,
        'augmented_email_list_dict': augmented_email_list_dict,
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
        schedule_email_results = email_manager.schedule_email(
            email_outbound_description=email_outbound_description,
            subject=subject,
            message_text=message_text,
            message_html=message_html,
            send_status=send_status)
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


def schedule_verification_email(
        sender_voter_we_vote_id='',
        recipient_voter_we_vote_id='',
        recipient_email_we_vote_id='',
        recipient_voter_email='',
        recipient_email_address_secret_key='',
        recipient_email_subscription_secret_key='',
        web_app_root_url=''):
    """
    When a voter adds a new email address for self, create and send an outbound email with a link
    that the voter can click to verify the email.
    TODO: Deprecate this (in favor of sending 6 digit code)
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param recipient_email_address_secret_key:
    :param recipient_email_subscription_secret_key:
    :param web_app_root_url:
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = VERIFY_EMAIL_ADDRESS_TEMPLATE
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

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

    # Unsubscribe link in email
    # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
    #     recipient_email_subscription_secret_key,
    recipient_unsubscribe_url = \
        "{root_url}/unsubscribe/{email_secret_key}/login" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=web_app_root_url_verified,
        )
    # Instant unsubscribe link in email header
    list_unsubscribe_url = \
        "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/login/" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=WE_VOTE_SERVER_ROOT_URL,
        )
    # Instant unsubscribe email address in email header
    # from voter.models import NOTIFICATION_LOGIN_EMAIL
    list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                              "".format(setting='login')

    template_variables_for_json = {
        "recipient_unsubscribe_url":    recipient_unsubscribe_url,
        "recipient_voter_email":        recipient_voter_email,
        "subject":                      subject,
        "verify_email_link":
            web_app_root_url_verified + "/verify_email/" + recipient_email_address_secret_key,
        "we_vote_url":                  web_app_root_url_verified,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    verification_from_email = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=sender_voter_we_vote_id,
        sender_voter_email=verification_from_email,
        sender_voter_name='',
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_voter_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        list_unsubscribe_mailto=list_unsubscribe_mailto,
        list_unsubscribe_url=list_unsubscribe_url,
    )
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


def schedule_link_to_sign_in_email(
        sender_voter_we_vote_id='',
        recipient_voter_we_vote_id='',
        recipient_email_we_vote_id='',
        recipient_voter_email='',
        recipient_email_address_secret_key='',
        recipient_email_subscription_secret_key='',
        is_cordova=False,
        web_app_root_url=''):
    """
    When a voter wants to sign in with a pre-existing email, create and send an outbound email with a link
    that the voter can click to sign in.
    TODO: Deprecate this function (in favor of sending 6 digit code)
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param recipient_email_address_secret_key:
    :param recipient_email_subscription_secret_key:
    :param is_cordova:
    :param web_app_root_url:
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = LINK_TO_SIGN_IN_TEMPLATE
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

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
    link_to_sign_in = web_app_root_url_verified + "/sign_in_email/" + recipient_email_address_secret_key
    if is_cordova:
        link_to_sign_in = "wevotetwitterscheme://sign_in_email/" + recipient_email_address_secret_key

    # Unsubscribe link in email
    # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
    # recipient_email_subscription_secret_key,
    recipient_unsubscribe_url = \
        "{root_url}/unsubscribe/{email_secret_key}/login" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=web_app_root_url_verified,
        )
    # Instant unsubscribe link in email header
    list_unsubscribe_url = \
        "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/login/" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=WE_VOTE_SERVER_ROOT_URL,
        )
    # Instant unsubscribe email address in email header
    # from voter.models import NOTIFICATION_LOGIN_EMAIL
    list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                              "".format(setting='login')

    template_variables_for_json = {
        "link_to_sign_in":              link_to_sign_in,
        "recipient_unsubscribe_url":    recipient_unsubscribe_url,
        "recipient_voter_email":        recipient_voter_email,
        "subject":                      subject,
        "we_vote_url":                  web_app_root_url_verified,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    verification_from_email = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=sender_voter_we_vote_id,
        sender_voter_email=verification_from_email,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_voter_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        list_unsubscribe_mailto=list_unsubscribe_mailto,
        list_unsubscribe_url=list_unsubscribe_url,
    )
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


def schedule_sign_in_code_email(
        sender_voter_we_vote_id='',
        recipient_voter_we_vote_id='',
        recipient_email_we_vote_id='',
        recipient_voter_email='',
        secret_numerical_code='',
        recipient_email_subscription_secret_key='',
        web_app_root_url=''):
    """
    When a voter wants to sign in with a pre-existing email, create and send an outbound email with a secret
    code that can be entered into the interface where the code was requested.
    :param sender_voter_we_vote_id:
    :param recipient_voter_we_vote_id:
    :param recipient_email_we_vote_id:
    :param recipient_voter_email:
    :param secret_numerical_code:
    :param recipient_email_subscription_secret_key:
    :param web_app_root_url:
    :return:
    """
    email_scheduled_saved = False
    email_scheduled_sent = False
    email_scheduled_id = 0

    email_manager = EmailManager()
    status = ""
    kind_of_email_template = SIGN_IN_CODE_EMAIL_TEMPLATE
    web_app_root_url_verified = transform_web_app_url(web_app_root_url)  # Change to client URL if needed

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

    # Unsubscribe link in email
    # "recipient_unsubscribe_url":    web_app_root_url_verified + "/settings/notifications/esk/" +
    # recipient_email_subscription_secret_key,
    recipient_unsubscribe_url = \
        "{root_url}/unsubscribe/{email_secret_key}/login" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=web_app_root_url_verified,
        )
    # Instant unsubscribe link in email header
    list_unsubscribe_url = \
        "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/login/" \
        "".format(
            email_secret_key=recipient_email_subscription_secret_key,
            root_url=WE_VOTE_SERVER_ROOT_URL,
        )
    # Instant unsubscribe email address in email header
    # from voter.models import NOTIFICATION_LOGIN_EMAIL
    list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
                              "".format(setting='login')

    template_variables_for_json = {
        "recipient_unsubscribe_url":    recipient_unsubscribe_url,
        "recipient_voter_email":        recipient_voter_email,
        "secret_numerical_code":        secret_numerical_code,
        "subject":                      subject,
        "we_vote_url":                  web_app_root_url_verified,
    }
    template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    verification_from_email = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    outbound_results = email_manager.create_email_outbound_description(
        sender_voter_we_vote_id=sender_voter_we_vote_id,
        sender_voter_email=verification_from_email,
        recipient_voter_we_vote_id=recipient_voter_we_vote_id,
        recipient_email_we_vote_id=recipient_email_we_vote_id,
        recipient_voter_email=recipient_voter_email,
        template_variables_in_json=template_variables_in_json,
        kind_of_email_template=kind_of_email_template,
        list_unsubscribe_mailto=list_unsubscribe_mailto,
        list_unsubscribe_url=list_unsubscribe_url,
    )
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
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=False)
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
    email_results = email_manager.retrieve_email_address_object_from_secret_key(email_secret_key=email_secret_key)
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


def voter_email_address_verify_for_api(  # voterEmailAddressVerify
        voter_device_id,
        email_secret_key,
        first_name=False,
        last_name=False,
        full_name=False,
        name_save_only_if_no_existing_names=True):
    """
    See also voter_verify_secret_code_view  # voterVerifySecretCode
    :param voter_device_id:
    :param email_secret_key:
    :param first_name:
    :param last_name:
    :param full_name:
    :param name_save_only_if_no_existing_names:
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
    secret_key_results = email_manager.retrieve_email_address_object_from_secret_key(email_secret_key=email_secret_key)
    if not secret_key_results['email_address_object_found']:
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

    status += "EMAIL_ADDRESS_FOUND_FROM_SECRET_KEY "
    email_object_from_secret_key = secret_key_results['email_address_object']
    email_address_found = True
    link_to_this_voter_if_no_conflicts = False
    normalized_email_ownership_verified_count = 0
    normalized_not_verified_count = 0
    normalized_voter_we_vote_id = ''
    update_this_voter_if_missing_primary = False
    verify_email_address_if_no_conflicts = False

    # Check existing data before verifying. Note: this is not a "merge accounts" process.

    # How many EmailAddress entries are there with this normalized_email, and are any already verified?
    matching_results = email_manager.retrieve_email_address_object(
        normalized_email_address=email_object_from_secret_key.normalized_email_address)
    if matching_results['email_address_object_found']:
        # Only one entry with normalized_email_address.
        email_object_from_normalized = matching_results['email_address_object']
        if email_object_from_secret_key.we_vote_id != email_object_from_normalized.we_vote_id:
            # This should not be possible, but we still have to check
            status += "EMAIL_OBJECT_FROM_SECRET_KEY_DOES_NOT_MATCH_NORMALIZED "
        elif not email_object_from_normalized.email_ownership_is_verified:
            # Only proceed if not verified
            normalized_voter_we_vote_id = email_object_from_normalized.voter_we_vote_id
            verify_email_address_if_no_conflicts = True
            if positive_value_exists(normalized_voter_we_vote_id):
                if voter_we_vote_id == normalized_voter_we_vote_id:
                    link_to_this_voter_if_no_conflicts = True
                    update_this_voter_if_missing_primary = True
                else:
                    # Verification was requested from another account we aren't currently signed in with.
                    #  Here we will verify_email_address_if_no_conflicts, but we won't link to the current account
                    pass
            else:
                link_to_this_voter_if_no_conflicts = True
                update_this_voter_if_missing_primary = True
    elif matching_results['email_address_list_found']:
        # Multiple entries with the same normalized_email_address found
        email_address_list = matching_results['email_address_list']
        email_object_from_normalized = None
        for email_object_from_normalized in email_address_list:
            if email_object_from_normalized.email_ownership_is_verified:
                normalized_email_ownership_verified_count += 1
            else:
                # Entry with is not verified
                normalized_not_verified_count += 1
                # normalized_email_we_vote_id = email_object_from_normalized.we_vote_id
                normalized_voter_we_vote_id = email_object_from_normalized.voter_we_vote_id
        if normalized_email_ownership_verified_count > 0:
            # EmailAddress with this normalized_email_address is already verified, so do not proceed
            pass
        elif normalized_not_verified_count == 1:
            if email_object_from_secret_key.we_vote_id != email_object_from_normalized.we_vote_id:
                # This should not be possible, but we still have to check
                status += "EMAIL_OBJECT_FROM_SECRET_KEY_DOES_NOT_MATCH_NORMALIZED_LIST "
            else:
                verify_email_address_if_no_conflicts = True
                if positive_value_exists(normalized_voter_we_vote_id):
                    if voter_we_vote_id == normalized_voter_we_vote_id:
                        link_to_this_voter_if_no_conflicts = True
                        update_this_voter_if_missing_primary = True
                    else:
                        # Verification was requested from another account we aren't currently signed in with.
                        #  Here we will verify_email_address_if_no_conflicts, but we won't link to the current account
                        pass
        elif normalized_not_verified_count > 1:
            # Cycle through list until we find the EmailAddress match for this voter, so we can verify
            pass

    # ##########################
    # Error conditions to check

    # Do any other voter records have this normalized_email_we_vote_id already in voter.primary_email_we_vote_id?
    # Do any other voter records have this normalized_email_address already in voter.email?

    # Note that voter.email and voter.primary_email_we_vote_id must be unique, so calling
    #  voter_manager.update_voter_email_ownership_verified below will fail if they are already stored
    #  in another voter record

    # See if email already in voter.primary_email_we_vote_id
    voter_is_missing_primary = False
    if not positive_value_exists(voter.primary_email_we_vote_id) or not positive_value_exists(voter.email):
        voter_is_missing_primary = True

    # See if this email_address_object has a different voter_we_vote_id

    # ##########
    # Update voter name - this may seem out of place here, but this update is related to a successful click
    #  from a contact after being reminded to vote with sharedItemSaveRemindContact
    if positive_value_exists(voter.first_name) or positive_value_exists(voter.last_name):
        saved_first_or_last_name_exists = True
    else:
        saved_first_or_last_name_exists = False

    incoming_first_or_last_name = positive_value_exists(first_name) or positive_value_exists(last_name)
    # If a first_name or last_name is coming in, we want to ignore the full_name
    if positive_value_exists(full_name) and not positive_value_exists(incoming_first_or_last_name):
        incoming_full_name_can_be_processed = True
    else:
        incoming_full_name_can_be_processed = False

    if incoming_full_name_can_be_processed:
        # If here we want to parse full_name into first and last
        first_name = extract_first_name_from_full_name(full_name)
        last_name = extract_last_name_from_full_name(full_name)

    if name_save_only_if_no_existing_names:
        if saved_first_or_last_name_exists:
            first_name = False
            last_name = False

    if positive_value_exists(first_name) or positive_value_exists(last_name):
        try:
            if positive_value_exists(first_name):
                voter.first_name = first_name
            if positive_value_exists(last_name):
                voter.last_name = last_name
            voter.save()
        except Exception as e:
            status += "COULD_NOT_SAVE_FIRST_NAME_OR_LAST_NAME " + str(e) + " "

    save_email_object_from_secret_key = False
    if verify_email_address_if_no_conflicts:
        try:
            email_object_from_secret_key.email_ownership_is_verified = True
            save_email_object_from_secret_key = True
            status += "EMAIL_OWNERSHIP_VERIFIED "
        except Exception as e:
            status += "COULD_NOT_ASSIGN_EMAIL_OWNERSHIP_IS_VERIFIED: " + str(e) + " "

    if link_to_this_voter_if_no_conflicts:
        try:
            email_object_from_secret_key.voter_we_vote_id = voter_we_vote_id
            save_email_object_from_secret_key = True
            status += "UPDATE_VOTER_WE_VOTE_ID "
        except Exception as e:
            status += "COULD_NOT_UPDATE_VOTER_WE_VOTE_ID: " + str(e) + " "

    if save_email_object_from_secret_key:
        try:
            email_object_from_secret_key.save()
            status += "EMAIL_OBJECT_FROM_SECRET_KEY_SAVED "
        except Exception as e:
            status += "COULD_NOT_UPDATE_EMAIL_OBJECT_FROM_SECRET_KEY: " + str(e) + " "

    if voter_we_vote_id == email_object_from_secret_key.voter_we_vote_id:
        email_secret_key_belongs_to_this_voter = True

    email_ownership_is_verified = email_object_from_secret_key.email_ownership_is_verified
    if email_secret_key_belongs_to_this_voter and update_this_voter_if_missing_primary and voter_is_missing_primary:
        voter_ownership_results = voter_manager.update_voter_email_ownership_verified(
            voter, email_object_from_secret_key)
        voter_ownership_saved = voter_ownership_results['voter_updated']
        if voter_ownership_saved:
            voter = voter_ownership_results['voter']

    organization_manager = OrganizationManager()
    if voter_ownership_saved:
        if not positive_value_exists(voter.linked_organization_we_vote_id):
            # Create new organization
            organization_name = voter.get_full_name()
            organization_image = voter.voter_photo_url()
            organization_type = INDIVIDUAL
            create_results = organization_manager.create_organization(
                organization_name=organization_name,
                organization_image=organization_image,
                organization_type=organization_type,
                we_vote_hosted_profile_image_url_large=voter.we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny
            )
            if create_results['organization_created']:
                # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                organization = create_results['organization']
                try:
                    voter.linked_organization_we_vote_id = organization.we_vote_id
                    voter.save()
                except Exception as e:
                    status += "UNABLE_TO_LINK_NEW_ORGANIZATION_TO_VOTER: " + str(e) + " "

        # TODO DALE We want to reset the email_secret key used

    is_organization = False
    organization_full_name = ""
    if positive_value_exists(voter.linked_organization_we_vote_id):
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            voter.linked_organization_we_vote_id)
        if organization_results['organization_found']:
            organization = organization_results['organization']
            if organization.is_organization():
                is_organization = True
                organization_full_name = organization.organization_name

    # send previous scheduled emails
    real_name_only = True
    from_voter_we_vote_id = email_object_from_secret_key.voter_we_vote_id
    if is_organization:
        if positive_value_exists(organization_full_name) and 'Voter-' not in organization_full_name:
            # Only send if the organization name exists
            send_results = email_manager.send_scheduled_emails_waiting_for_verification(
                from_voter_we_vote_id, organization_full_name)
            status += send_results['status']
            # invitation_update_results = friend_manager.update_friend_data_with_name(
            #     from_voter_we_vote_id, organization_full_name)
        else:
            status += "CANNOT_SEND_SCHEDULED_EMAILS_WITHOUT_ORGANIZATION_NAME-EMAIL_CONTROLLER "
    elif positive_value_exists(voter.get_full_name(real_name_only)):
        # Only send if the sender's full name exists
        send_results = email_manager.send_scheduled_emails_waiting_for_verification(
            from_voter_we_vote_id, voter.get_full_name(real_name_only))
        status += send_results['status']
    else:
        status += "CANNOT_SEND_SCHEDULED_EMAILS_WITHOUT_NAME-EMAIL_CONTROLLER "

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'voter_device_id':                          voter_device_id,
        'email_ownership_is_verified':              email_ownership_is_verified,
        'email_secret_key_belongs_to_this_voter':   email_secret_key_belongs_to_this_voter,
        'email_address_found':                      email_address_found,
    }
    return json_data


def voter_email_address_save_for_api(
        voter_device_id='',
        text_for_email_address='',
        incoming_email_we_vote_id='',
        send_link_to_sign_in=False,
        send_sign_in_code_email=False,
        resend_verification_email=False,
        resend_verification_code_email=False,
        make_primary_email=False,
        delete_email=False,
        is_cordova=False,
        web_app_root_url=''):
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
    :param is_cordova:
    :param web_app_root_url:
    :return:
    """
    email_address_we_vote_id = ""
    email_address_saved_we_vote_id = ""
    email_address_created = False
    email_address_deleted = False
    email_address_not_valid = False
    verification_email_sent = False
    link_to_sign_in_email_sent = False
    sign_in_code_email_sent = False
    sign_in_code_email_already_valid = False
    send_verification_email = False
    email_address_found = False
    email_address_list_found = False
    recipient_email_address_secret_key = ""
    messages_to_send = []
    status = "VOTER_EMAIL_ADDRESS_SAVE-START "
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
            'email_address_not_valid':          False,
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
                'email_address_not_valid':          True,  # Signal that the email address wasn't valid
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
            'email_address_not_valid':          False,
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
            'email_address_not_valid':          False,
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
    recipient_email_subscription_secret_key = ''
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
        # The only person who will see this is someone who has access to this verified_email_address
        recipient_email_subscription_secret_key = verified_email_address_object.subscription_secret_key
        if send_sign_in_code_email:
            sign_in_code_email_already_valid = True
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
                'email_address_not_valid':      False,
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

    # Clean up our email list
    # 1) Remove duplicates
    excess_email_objects = []
    filtered_email_address_list = []
    ownership_verified_email_object = None
    ownership_verified_emails = []
    ownership_not_verified_email_object = None
    ownership_not_verified_emails = []
    for email_address_object in email_address_list:
        if email_address_object.email_ownership_is_verified:
            if email_address_object.normalized_email_address not in ownership_verified_emails:
                ownership_verified_email_object = email_address_object
                ownership_verified_emails.append(email_address_object.normalized_email_address)
            else:
                excess_email_objects.append(email_address_object)
        else:
            if email_address_object.normalized_email_address not in ownership_not_verified_emails:
                ownership_not_verified_email_object = email_address_object
                ownership_not_verified_emails.append(email_address_object.normalized_email_address)
            else:
                excess_email_objects.append(email_address_object)

    if ownership_verified_email_object is not None:
        status += "VERIFIED_EMAIL_FOUND "
        filtered_email_address_list.append(ownership_verified_email_object)
        excess_email_objects.append(ownership_not_verified_email_object)
        if send_sign_in_code_email:
            sign_in_code_email_already_valid = True
            if not recipient_email_subscription_secret_key:
                recipient_email_subscription_secret_key = ownership_verified_email_object.subscription_secret_key
    elif ownership_not_verified_email_object is not None:
        status += "UNVERIFIED_EMAIL_FOUND "
        filtered_email_address_list.append(ownership_not_verified_email_object)

    # Delete the duplicates from the database
    for email_address_object in excess_email_objects:
        try:
            email_address_object.delete()
        except Exception as e:
            status += "CANNOT_DELETE_EXCESS_EMAIL: " + str(e) + " "

    # Cycle through all EmailAddress entries with "text_for_email_address" or "incoming_email_we_vote_id"
    for email_address_object in filtered_email_address_list:
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
                # Delete all other emails associated with this account that are not verified
                if positive_value_exists(text_for_email_address):
                    duplicate_results = email_manager.retrieve_email_address_object(
                        text_for_email_address, voter_we_vote_id=voter_we_vote_id)
                    if duplicate_results['email_address_object_found']:
                        email_address_object_to_delete = duplicate_results['email_address_object']
                        if not positive_value_exists(email_address_object_to_delete.email_ownership_is_verified):
                            try:
                                email_address_object_to_delete.delete()
                                status += "DELETED_ONE_DUP_EMAIL_ADDRESS "
                            except Exception as e:
                                status += "UNABLE_TO_DELETE_ONE_DUP_EMAIL_ADDRESS "
                    elif duplicate_results['email_address_list_found']:
                        email_address_list_for_delete = duplicate_results['email_address_list']
                        for email_address_object_to_delete in email_address_list_for_delete:
                            if not positive_value_exists(email_address_object_to_delete.email_ownership_is_verified):
                                try:
                                    email_address_object_to_delete.delete()
                                    status += "DELETED_DUP_EMAIL_ADDRESS_IN_LIST "
                                except Exception as e:
                                    status += "UNABLE_TO_DELETE_DUP_EMAIL_ADDRESS_IN_LIST "

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
                                    status += "UNABLE_TO_SAVE_EMAIL_ADDRESS_AS_NEW_PRIMARY: " + str(e) + " "
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
            status += "STARTING_MAKE_PRIMARY_EMAIL "
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
            # If email_address_already_owned_by_other_voter, use the existing subscription_secret_key
            if not email_address_already_owned_by_other_voter:
                if positive_value_exists(new_email_address_object.subscription_secret_key):
                    recipient_email_subscription_secret_key = new_email_address_object.subscription_secret_key
                else:
                    recipient_email_subscription_secret_key = \
                        email_manager.update_email_address_with_new_subscription_secret_key(
                            email_we_vote_id=email_address_we_vote_id)
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
        link_send_results = schedule_link_to_sign_in_email(
            sender_voter_we_vote_id=voter_we_vote_id,
            recipient_voter_we_vote_id=voter_we_vote_id,
            recipient_email_we_vote_id=email_address_we_vote_id,
            recipient_voter_email=text_for_email_address,
            recipient_email_address_secret_key=recipient_email_address_secret_key,
            recipient_email_subscription_secret_key=recipient_email_subscription_secret_key,
            is_cordova=is_cordova,
            web_app_root_url=web_app_root_url)
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

            if not sign_in_code_email_already_valid:
                recipient_email_subscription_secret_key = ''
                results = email_manager.retrieve_email_address_object(
                    email_address_object_we_vote_id=email_address_we_vote_id)
                if results['email_address_object_found']:
                    recipient_email_address_object = results['email_address_object']
                    if positive_value_exists(recipient_email_address_object.subscription_secret_key):
                        recipient_email_subscription_secret_key = recipient_email_address_object.subscription_secret_key
                    else:
                        recipient_email_subscription_secret_key = \
                            email_manager.update_email_address_with_new_subscription_secret_key(
                                email_we_vote_id=email_address_we_vote_id)

            status += 'ABOUT_TO_SEND_SIGN_IN_CODE '
            link_send_results = schedule_sign_in_code_email(
                sender_voter_we_vote_id=voter_we_vote_id,
                recipient_voter_we_vote_id=voter_we_vote_id,
                recipient_email_we_vote_id=email_address_we_vote_id,
                recipient_voter_email=text_for_email_address,
                secret_numerical_code=secret_code,
                recipient_email_subscription_secret_key=recipient_email_subscription_secret_key,
                web_app_root_url=web_app_root_url)
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
        verifications_send_results = schedule_verification_email(
            sender_voter_we_vote_id=voter_we_vote_id,
            recipient_voter_we_vote_id=voter_we_vote_id,
            recipient_email_we_vote_id=email_address_we_vote_id,
            recipient_voter_email=text_for_email_address,
            recipient_email_address_secret_key=recipient_email_address_secret_key,
            recipient_email_subscription_secret_key=recipient_email_subscription_secret_key,
            web_app_root_url=web_app_root_url)
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
        'email_address_not_valid':          email_address_not_valid,
        'verification_email_sent':          verification_email_sent,
        'link_to_sign_in_email_sent':       link_to_sign_in_email_sent,
        'sign_in_code_email_sent':          sign_in_code_email_sent,
        'secret_code_system_locked_for_this_voter_device_id': secret_code_system_locked_for_this_voter_device_id,
    }
    return json_data


def voter_email_address_send_sign_in_code_email_for_api(  # voterEmailAddressSave
        voter_device_id='',
        text_for_email_address='',
        web_app_root_url=''):
    """

    :param voter_device_id:
    :param text_for_email_address:
    :param web_app_root_url:
    :return:
    """
    email_address_we_vote_id = ""
    email_address_created = False
    email_address_deleted = False
    email_address_not_valid = False
    verification_email_sent = False
    link_to_sign_in_email_sent = False
    sign_in_code_email_sent = False
    email_address_list_found = False
    status = "VOTER_EMAIL_ADDRESS_SAVE-START "
    error_results = {
        'status': status,
        'success': False,
        'voter_device_id': voter_device_id,
        'text_for_email_address': text_for_email_address,
        'email_address_we_vote_id': '',
        'email_address_created': False,
        'email_address_deleted': False,
        'email_address_not_valid': False,
        'verification_email_sent': False,
        'link_to_sign_in_email_sent': False,
        'sign_in_code_email_sent': False,
        'email_address_already_owned_by_other_voter': False,
        'email_address_already_owned_by_this_voter': False,
        'email_address_found': False,
        'email_address_list_found': False,
        'email_address_list': [],
        'secret_code_system_locked_for_this_voter_device_id': False,
    }

    # If a voter_device_id is passed in that isn't valid, we want to throw an error
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        status += device_id_results['status'] + " VOTER_DEVICE_ID_NOT_VALID "
        error_results['status'] = status
        return error_results

    # Is the text_for_email_address a valid email address?
    if positive_value_exists(text_for_email_address):
        if not validate_email(text_for_email_address):
            status += "VOTER_EMAIL_ADDRESS_SAVE_MISSING_VALID_EMAIL "
            error_results['status'] = status
            return error_results
    else:
        status += "VOTER_EMAIL_ADDRESS_SAVE_MISSING_EMAIL "
        error_results['status'] = status
        return error_results

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        error_results['status'] = status
        return error_results
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id

    email_manager = EmailManager()
    email_address_already_owned_by_this_voter = False
    email_address_already_owned_by_other_voter = False
    email_address_found = False

    # Independent of email verification, we need a consistent recipient_email_subscription_secret_key
    #  If there is an email_with_ownership_verified, we need to use that above all others,
    #  and if not, we can generate it with a new email created further below.
    recipient_email_subscription_secret_key = ''
    # For verification purposes (stored in voter_device_link), this might come from temporary email address
    recipient_email_address_secret_key = ''
    # Is this email already verified by any account?
    find_verified_email_results = email_manager.retrieve_primary_email_with_ownership_verified(
        voter_we_vote_id='',
        normalized_email_address=text_for_email_address)
    if not find_verified_email_results['success']:
        status += "PROBLEM_RETRIEVING_EMAIL: " + find_verified_email_results['status'] + " "
        error_results['status'] = status
        return error_results
    elif find_verified_email_results['email_address_object_found']:
        verified_email_address_object = find_verified_email_results['email_address_object']
        email_address_we_vote_id = verified_email_address_object.we_vote_id
        # The only person who will see subscription_secret_key is someone who has access to this verified_email_address
        recipient_email_subscription_secret_key = verified_email_address_object.subscription_secret_key
        if verified_email_address_object.voter_we_vote_id != voter_we_vote_id:
            email_address_already_owned_by_other_voter = True
        # The email.secret_key isn't shown to voter
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

    # From here on down, if email_address_we_vote_id is empty, we know we need to retrieve an
    #  email_address_object specific to this voter, or create one
    if not positive_value_exists(email_address_we_vote_id):
        # Look to see if there is an EmailAddress entry for the incoming text_for_email_address for this voter
        email_results = email_manager.retrieve_email_address_object(
            normalized_email_address=text_for_email_address,
            voter_we_vote_id=voter_we_vote_id)
        if email_results['email_address_object_found']:
            voter_email_address_object = email_results['email_address_object']
            email_address_we_vote_id = voter_email_address_object.we_vote_id
            if not recipient_email_subscription_secret_key:
                recipient_email_subscription_secret_key = voter_email_address_object.subscription_secret_key
            email_address_created = False
            email_address_found = True
        elif email_results['email_address_list_found']:
            # This email was used by more than one person
            email_address_list = email_results['email_address_list']

            # Clean up our email list
            # 1) Remove duplicates
            excess_email_objects = []
            ownership_verified_email_object = None
            ownership_verified_emails = []
            ownership_not_verified_email_object = None
            ownership_not_verified_emails = []
            for email_address_object in email_address_list:
                if email_address_object.email_ownership_is_verified:
                    if email_address_object.normalized_email_address not in ownership_verified_emails:
                        ownership_verified_email_object = email_address_object
                        ownership_verified_emails.append(email_address_object.normalized_email_address)
                    else:
                        excess_email_objects.append(email_address_object)
                else:
                    if email_address_object.normalized_email_address not in ownership_not_verified_emails:
                        ownership_not_verified_email_object = email_address_object
                        ownership_not_verified_emails.append(email_address_object.normalized_email_address)
                    else:
                        excess_email_objects.append(email_address_object)

            if ownership_verified_email_object is not None:
                email_address_we_vote_id = ownership_verified_email_object.we_vote_id
                email_address_created = False
                email_address_found = True
                status += "VERIFIED_EMAIL_FOUND "
                excess_email_objects.append(ownership_not_verified_email_object)
                if not recipient_email_subscription_secret_key:
                    recipient_email_subscription_secret_key = ownership_verified_email_object.subscription_secret_key
                # The email.secret_key isn't shown to voter
                if positive_value_exists(ownership_verified_email_object.secret_key):
                    recipient_email_address_secret_key = ownership_verified_email_object.secret_key
                    status += "EXISTING_SECRET_KEY_FOUND2 "
                else:
                    recipient_email_address_secret_key = \
                        email_manager.update_email_address_with_new_secret_key(email_address_we_vote_id)
                    if positive_value_exists(recipient_email_address_secret_key):
                        status += "NEW_SECRET_KEY_GENERATED2 "
                    else:
                        status += "NEW_SECRET_KEY_COULD_NOT_BE_GENERATED2 "
            elif ownership_not_verified_email_object is not None:
                email_address_we_vote_id = ownership_not_verified_email_object.we_vote_id
                email_address_created = False
                email_address_found = True
                status += "UNVERIFIED_EMAIL_FOUND "
                if not recipient_email_subscription_secret_key:
                    recipient_email_subscription_secret_key = \
                        ownership_not_verified_email_object.subscription_secret_key
                # The email.secret_key isn't shown to voter
                if positive_value_exists(ownership_not_verified_email_object.secret_key):
                    recipient_email_address_secret_key = ownership_not_verified_email_object.secret_key
                    status += "EXISTING_SECRET_KEY_FOUND3 "
                else:
                    recipient_email_address_secret_key = \
                        email_manager.update_email_address_with_new_secret_key(email_address_we_vote_id)
                    if positive_value_exists(recipient_email_address_secret_key):
                        status += "NEW_SECRET_KEY_GENERATED3 "
                    else:
                        status += "NEW_SECRET_KEY_COULD_NOT_BE_GENERATED3 "

            # Delete the duplicates from the database
            for email_address_object in excess_email_objects:
                try:
                    email_address_object.delete()
                except Exception as e:
                    status += "CANNOT_DELETE_EXCESS_EMAIL: " + str(e) + " "

    if not positive_value_exists(email_address_we_vote_id):
        # Save the new email address
        status += "CREATE_NEW_EMAIL_ADDRESS "
        email_ownership_is_verified = False
        email_save_results = email_manager.create_email_address(
            normalized_email_address=text_for_email_address,
            voter_we_vote_id=voter_we_vote_id,
            email_ownership_is_verified=email_ownership_is_verified)
        status += email_save_results['status']
        if email_save_results['email_address_object_saved']:
            new_email_address_object = email_save_results['email_address_object']
            email_address_we_vote_id = new_email_address_object.we_vote_id
            if positive_value_exists(new_email_address_object.subscription_secret_key):
                recipient_email_subscription_secret_key = new_email_address_object.subscription_secret_key
            else:
                recipient_email_subscription_secret_key = \
                    email_manager.update_email_address_with_new_subscription_secret_key(
                        email_we_vote_id=email_address_we_vote_id)
            # The email.secret_key isn't shown to voter
            if positive_value_exists(new_email_address_object.secret_key):
                recipient_email_address_secret_key = new_email_address_object.secret_key
                status += "EXISTING_SECRET_KEY_FOUND4 "
            else:
                recipient_email_address_secret_key = \
                    email_manager.update_email_address_with_new_secret_key(email_address_we_vote_id)
                if positive_value_exists(recipient_email_address_secret_key):
                    status += "NEW_SECRET_KEY_GENERATED4 "
                else:
                    status += "NEW_SECRET_KEY_COULD_NOT_BE_GENERATED4 "
            email_address_created = True
            email_address_found = True
            status += email_save_results['status']
        else:
            status += "UNABLE_TO_CREATE_EMAIL_ADDRESS "
            error_results['status'] = status
            return error_results

    voter_device_link_manager = VoterDeviceLinkManager()
    # Run the code to send email with sign in verification code (6 digit)
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
            sender_voter_we_vote_id=voter_we_vote_id,
            recipient_voter_we_vote_id=voter_we_vote_id,
            recipient_email_we_vote_id=email_address_we_vote_id,
            recipient_voter_email=text_for_email_address,
            secret_numerical_code=secret_code,
            recipient_email_subscription_secret_key=recipient_email_subscription_secret_key,
            web_app_root_url=web_app_root_url)
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
        'email_address_created':            email_address_created,
        'email_address_deleted':            email_address_deleted,
        'email_address_not_valid':          email_address_not_valid,
        'verification_email_sent':          verification_email_sent,
        'link_to_sign_in_email_sent':       link_to_sign_in_email_sent,
        'sign_in_code_email_sent':          sign_in_code_email_sent,
        'secret_code_system_locked_for_this_voter_device_id': secret_code_system_locked_for_this_voter_device_id,
    }
    return json_data
