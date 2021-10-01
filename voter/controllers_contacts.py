# voter/controllers_contacts.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from dateutil import parser
from wevote_functions.functions import positive_value_exists
from .models import VoterContactEmail, VoterManager


def move_voter_contact_email_to_another_voter(from_voter_we_vote_id, to_voter_we_vote_id):
    status = ''
    success = True
    voter_contact_email_entries_moved = 0

    if not positive_value_exists(from_voter_we_vote_id) or not positive_value_exists(to_voter_we_vote_id):
        status += "MOVE_VOTER_CONTACT_EMAIL-MISSING_EITHER_FROM_OR_TO_VOTER_WE_VOTE_ID "
        success = False
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'voter_contact_email_entries_moved':    voter_contact_email_entries_moved,
        }
        return results

    if from_voter_we_vote_id == to_voter_we_vote_id:
        status += "MOVE_VOTER_CONTACT_EMAIL-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status':                               status,
            'success':                              success,
            'from_voter_we_vote_id':                from_voter_we_vote_id,
            'to_voter_we_vote_id':                  to_voter_we_vote_id,
            'voter_contact_email_entries_moved':    voter_contact_email_entries_moved,
        }
        return results

    # ######################
    # Migrations
    try:
        voter_contact_email_entries_moved += VoterContactEmail.objects\
            .filter(imported_by_voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(imported_by_voter_we_vote_id=to_voter_we_vote_id)
    except Exception as e:
        status += "FAILED-VOTER_CONTACT_EMAIL_UPDATE: " + str(e) + " "

    results = {
        'status':                               status,
        'success':                              success,
        'from_voter_we_vote_id':                from_voter_we_vote_id,
        'to_voter_we_vote_id':                  to_voter_we_vote_id,
        'voter_contact_email_entries_moved':    voter_contact_email_entries_moved,
    }
    return results


def delete_google_contacts(voter_we_vote_id=''):  # voterContactListSave - Delete
    status = ''
    success = True
    google_contacts_deleted_count = 0

    try:
        # When we support other kinds of imports, don't delete entries which also have data from another source
        # We will need to update remaining entries to set 'has_data_from_google_people_api' to False
        # and clear other fields
        google_contacts_deleted_tuple = VoterContactEmail.objects\
            .filter(
                has_data_from_google_people_api=True,
                imported_by_voter_we_vote_id__iexact=voter_we_vote_id,
            )\
            .delete()
        google_contacts_deleted_count = google_contacts_deleted_tuple[0]
    except Exception as e:
        status += "FAILED-VOTER_CONTACT_EMAIL_DELETE: " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'google_contacts_deleted_count': google_contacts_deleted_count,
    }
    return results


def filter_google_contacts(contacts):
    filtered_contacts = []
    strings_to_filter_out = [
        '@noreply.github.com',
        '@reply.github.com',
        '.zendesk.com',
    ]
    for contact in contacts:
        email_address_text = contact['email'] if 'email' in contact else ''
        if positive_value_exists(email_address_text):
            # If the email address contains any of the strings in strings_to_filter_out, don't import it
            if not any(substring in email_address_text for substring in strings_to_filter_out):
                filtered_contacts.append(contact)
    return filtered_contacts


def save_google_contacts(voter_we_vote_id='', contacts=[]):  # voterContactListSave
    status = ''
    success = True
    voter_manager = VoterManager()

    if contacts is not None:
        contacts = filter_google_contacts(contacts)

        existing_voter_contact_email_dict = {}
        results = voter_manager.retrieve_voter_contact_email_list(
            imported_by_voter_we_vote_id=voter_we_vote_id,
            read_only=False)
        if results['voter_contact_email_list_found']:
            voter_contact_email_list = results['voter_contact_email_list']
            for voter_contact_email in voter_contact_email_list:
                existing_voter_contact_email_dict[voter_contact_email.email_address_text.lower()] = voter_contact_email
        for contact in contacts:
            email_address_text = contact['email'] if 'email' in contact else ''
            if positive_value_exists(email_address_text):
                display_name = contact['display_name'] if 'display_name' in contact else ''
                first_name = contact['given_name'] if 'given_name' in contact else ''
                google_contact_id = contact['id'] if 'id' in contact else ''
                update_time = contact['update_time'] if 'update_time' in contact else ''
                if positive_value_exists(update_time):
                    google_date_last_updated = parser.parse(update_time)
                else:
                    google_date_last_updated = None
                last_name = contact['family_name'] if 'family_name' in contact else ''
                update_results = voter_manager.update_or_create_voter_contact_email(
                    email_address_text=email_address_text,
                    existing_voter_contact_email_dict=existing_voter_contact_email_dict,
                    from_google_people_api=True,
                    google_contact_id=google_contact_id,
                    google_date_last_updated=google_date_last_updated,
                    display_name=display_name,
                    first_name=first_name,
                    last_name=last_name,
                    imported_by_voter_we_vote_id=voter_we_vote_id,
                )
                status += update_results['status']

    results = {
        'status': status,
        'success': success,
    }
    return results


def voter_contact_list_retrieve_for_api(voter_we_vote_id=''):  # voterContactListRetrieve
    status = ''
    voter_manager = VoterManager()
    voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
        imported_by_voter_we_vote_id=voter_we_vote_id)

    voter_contact_email_google_count = 0
    voter_contact_email_list = voter_contact_results['voter_contact_email_list']
    voter_contact_email_list_found = voter_contact_results['voter_contact_email_list_found']
    status += voter_contact_results['status']
    success = voter_contact_results['success']

    voter_contact_email_list_for_json = []
    for voter_contact_email in voter_contact_email_list:
        date_last_changed_string = ''
        google_date_last_updated_string = ''
        if voter_contact_email.has_data_from_google_people_api:
            voter_contact_email_google_count += 1
        try:
            date_last_changed_string = voter_contact_email.date_last_changed.strftime('%Y-%m-%d %H:%M:%S')
            google_date_last_updated_string = voter_contact_email.google_date_last_updated.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            status += "DATE_CONVERSION_ERROR: " + str(e) + " "
        voter_contact_email_dict = {
            'date_last_changed': date_last_changed_string,
            'email_address_text': voter_contact_email.email_address_text,
            'google_contact_id': voter_contact_email.google_contact_id,
            'google_date_last_updated': google_date_last_updated_string,
            'google_display_name': voter_contact_email.google_display_name,
            'google_first_name': voter_contact_email.google_first_name,
            'google_last_name': voter_contact_email.google_last_name,
            'has_data_from_google_people_api': voter_contact_email.has_data_from_google_people_api,
            'ignore_contact': voter_contact_email.ignore_contact,
            'imported_by_voter_we_vote_id': voter_contact_email.imported_by_voter_we_vote_id,
            'state_code': voter_contact_email.state_code,
        }
        voter_contact_email_list_for_json.append(voter_contact_email_dict)
    results = {
        'status':                           status,
        'success':                          success,
        'voter_contact_email_google_count': voter_contact_email_google_count,
        'voter_contact_email_list':         voter_contact_email_list_for_json,
        'voter_contact_email_list_found':   voter_contact_email_list_found,
    }
    return results
