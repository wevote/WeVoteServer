# voter/controllers_contacts.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from dateutil import parser
from wevote_functions.functions import positive_value_exists
from .models import VoterContactEmail, VoterManager


def assemble_contact_display_name(
        first_name=None,
        last_name=None,
        middle_name=None):
    new_display_name = ''
    if first_name is not None:
        new_display_name += first_name
    if middle_name is not None and middle_name != '':
        if positive_value_exists(new_display_name):
            new_display_name += " "
        new_display_name += middle_name
    if last_name is not None:
        if positive_value_exists(new_display_name):
            new_display_name += " "
        new_display_name += last_name
    return new_display_name


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
        query = VoterContactEmail.objects.all()
        query = query.filter(imported_by_voter_we_vote_id__iexact=to_voter_we_vote_id)
        query = query.exclude(google_contact_id__isnull=True)
        query = query.values_list('google_contact_id', flat=True).distinct()
        google_contact_id_list_to_not_overwrite = list(query)

        voter_contact_email_entries_moved += VoterContactEmail.objects\
            .filter(imported_by_voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .exclude(google_contact_id__in=google_contact_id_list_to_not_overwrite)\
            .update(imported_by_voter_we_vote_id=to_voter_we_vote_id)

        entries_deleted = \
            VoterContactEmail.objects.filter(imported_by_voter_we_vote_id__iexact=from_voter_we_vote_id).delete()
        status += "ENTRIES_DELETED: " + str(entries_deleted) + " "
    except Exception as e:
        status += "FAILED-VOTER_CONTACT_EMAIL_UPDATE_IMPORTED_BY: " + str(e) + " "

    try:
        voter_contact_email_entries_moved += VoterContactEmail.objects\
            .filter(voter_we_vote_id__iexact=from_voter_we_vote_id)\
            .update(voter_we_vote_id=to_voter_we_vote_id)
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


def delete_all_voter_contact_emails_for_voter(voter_we_vote_id=''):  # voterContactListSave - Delete
    status = ''
    success = True
    google_contacts_deleted_count = 0

    try:
        google_contacts_deleted_tuple = VoterContactEmail.objects\
            .filter(
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
        'aws-nonprofit-credits@amazon.com',
        'tickets@countable.uservoice.com',
        'billing@nationbuilder.com',
        '@noreply.github.com',
        '@reply.github.com',
        '@support.facebook.com',
        'ra@godaddy.com',
        'noreply',
        'no-reply',
        'support+',
        '.zendesk.com',
        'info@',
        'support@',
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
                google_contact_id = contact['id'] if 'id' in contact else ''
                update_time = contact['update_time'] if 'update_time' in contact else ''
                if positive_value_exists(update_time):
                    google_date_last_updated = parser.parse(update_time)
                else:
                    google_date_last_updated = None
                google_display_name = contact['display_name'] if 'display_name' in contact else ''
                google_first_name = contact['given_name'] if 'given_name' in contact else ''
                google_last_name = contact['family_name'] if 'family_name' in contact else ''
                update_results = voter_manager.update_or_create_voter_contact_email(
                    email_address_text=email_address_text,
                    existing_voter_contact_email_dict=existing_voter_contact_email_dict,
                    from_google_people_api=True,
                    google_contact_id=google_contact_id,
                    google_date_last_updated=google_date_last_updated,
                    google_display_name=google_display_name,
                    google_first_name=google_first_name,
                    google_last_name=google_last_name,
                    imported_by_voter_we_vote_id=voter_we_vote_id,
                )
                status += update_results['status']

    results = {
        'status': status,
        'success': success,
    }
    return results


def get_voter_contact_email_value(voter_contact_email=None, best_option='', fallback_option=''):
    if hasattr(voter_contact_email, best_option) and positive_value_exists(getattr(voter_contact_email, best_option)):
        return getattr(voter_contact_email, best_option)
    else:
        return getattr(voter_contact_email, fallback_option)


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
            'city': voter_contact_email.city if hasattr(voter_contact_email, 'city') else '',
            'date_last_changed': date_last_changed_string,
            'display_name': get_voter_contact_email_value(voter_contact_email, 'display_name', 'google_display_name'),
            'email_address_text': voter_contact_email.email_address_text
            if hasattr(voter_contact_email, 'email_address_text') else '',
            'first_name': get_voter_contact_email_value(voter_contact_email, 'first_name', 'google_first_name'),
            'google_contact_id': voter_contact_email.google_contact_id
            if hasattr(voter_contact_email, 'google_contact_id') else '',
            'google_date_last_updated': google_date_last_updated_string,
            'has_data_from_google_people_api': voter_contact_email.has_data_from_google_people_api,
            'id': voter_contact_email.id if hasattr(voter_contact_email, 'id') else 0,
            'ignore_contact': voter_contact_email.ignore_contact,
            'imported_by_voter_we_vote_id': voter_contact_email.imported_by_voter_we_vote_id
            if hasattr(voter_contact_email, 'imported_by_voter_we_vote_id') else '',
            'last_name': get_voter_contact_email_value(voter_contact_email, 'last_name', 'google_last_name'),
            'state_code': voter_contact_email.state_code if hasattr(voter_contact_email, 'state_code') else '',
            'voter_we_vote_id': voter_contact_email.voter_we_vote_id
            if hasattr(voter_contact_email, 'voter_we_vote_id') else '',
            'we_vote_hosted_profile_image_url_medium': voter_contact_email.we_vote_hosted_profile_image_url_medium
            if hasattr(voter_contact_email, 'we_vote_hosted_profile_image_url_medium') else '',
            'zip_code': voter_contact_email.zip_code if hasattr(voter_contact_email, 'zip_code') else '',
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
