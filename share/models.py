# share/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime, now
from organization.models import ORGANIZATION_TYPE_CHOICES, UNKNOWN
import sys
from wevote_functions.functions import convert_to_int, generate_random_string, positive_value_exists


class SharedItem(models.Model):
    """
    When a voter shares a link to a candidate, measure, office, or a ballot, map
    the
    """
    # The ending destination -- meaning the link that is being shared
    destination_full_url = models.URLField(max_length=255, blank=True, null=True)
    # A short code that is part of the link that is sent out. For example rFx5 as part of https://WeVote.US/-rFx5
    shared_item_code_no_opinions = models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    # Code for include_public_positions - Not implemented yet
    # shared_item_code_public_opinions = \
    #     models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    # Code for include_friends_only_positions
    shared_item_code_all_opinions = models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    # Returns link to /friends/remind URL
    shared_item_code_remind_contacts = models.CharField(max_length=50, null=True, unique=True, db_index=True)
    # Returns link to /ready URL
    shared_item_code_ready = models.CharField(max_length=50, null=True, unique=True, db_index=True)
    # secret key to verify ownership of email on first click
    email_secret_key = models.CharField(max_length=255, null=True, db_index=True)
    # secret key to verify ownership of phone number on first click
    sms_secret_key = models.CharField(max_length=255, null=True, db_index=True)
    # The voter and organization id of the person initiating the share
    shared_by_display_name = models.TextField(blank=True, null=True)
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_by_organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    shared_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    shared_by_state_code = models.CharField(max_length=2, null=True, db_index=True)
    shared_by_we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    shared_by_we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    shared_by_we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    shared_message = models.TextField(blank=True, null=True)  # Added for remind
    # The owner of the custom site this share was from
    site_owner_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=False, db_index=True)
    google_civic_election_id = models.PositiveIntegerField(default=0, null=True, blank=True)
    hide_introduction = models.BooleanField(default=False)
    is_ballot_share = models.BooleanField(default=False)
    is_campaignx_share = models.BooleanField(default=False)
    is_candidate_share = models.BooleanField(default=False)
    is_measure_share = models.BooleanField(default=False)
    is_office_share = models.BooleanField(default=False)
    is_organization_share = models.BooleanField(default=False)
    is_ready_share = models.BooleanField(default=False)
    is_remind_contact_share = models.BooleanField(default=False)
    # When reminding a contact to vote, we save info about them, so we can auto-create account
    other_voter_email_address_text = models.TextField(blank=True, null=True, db_index=True)
    other_voter_display_name = models.CharField(max_length=255, null=True, blank=True)
    other_voter_first_name = models.CharField(max_length=255, null=True, blank=True)
    other_voter_last_name = models.CharField(max_length=255, null=True, blank=True)
    other_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    # What is being shared
    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    candidate_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    measure_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    office_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    date_first_shared = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    # We store YYYY as an integer for very fast lookup (ex/ "2017" for permissions in the year 2017)
    year_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    deleted = models.BooleanField(default=False)

    # We override the save function to auto-generate date_as_integer
    def save(self, *args, **kwargs):
        if self.year_as_integer:
            self.year_as_integer = convert_to_int(self.year_as_integer)
        if self.year_as_integer == "" or self.year_as_integer is None:  # If there isn't a value...
            self.generate_year_as_integer()
        super(SharedItem, self).save(*args, **kwargs)

    def generate_year_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        year_as_string = "{:d}".format(
            datetime_now.year,
        )
        self.year_as_integer = convert_to_int(year_as_string)
        return


class SharedPermissionsGranted(models.Model):
    """
    Keep track of the permissions a voter has been granted from
    clicking a link that has been shared with them.
    Note: We use SharedPermissionsGranted to keep track of organizations that are on a voter's radar, even if
    include_friends_only_positions is False (which means they can only see PUBLIC_ONLY positions)
    """
    # The voter and organization id of the person initiating the share
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_by_organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    shared_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    # The person being granted the permissions
    shared_to_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_to_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    google_civic_election_id = models.PositiveIntegerField(default=0, null=True, blank=True)
    # We store YYYY as an integer for very fast lookup (ex/ "2017" for permissions in the year 2017)
    year_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    # Having an entry in this table assumes include_public_positions is True
    include_friends_only_positions = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)


class SharedLinkClicked(models.Model):
    """
    Keep track of each time the shared link was clicked
    """
    # The ending destination -- meaning the link that is being shared
    destination_full_url = models.URLField(max_length=255, blank=True, null=True)
    # The voter and organization id of the person initiating the share
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_by_organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    shared_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    shared_by_state_code = models.CharField(max_length=2, null=True, db_index=True)
    # The person clicking the link
    viewed_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    viewed_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    viewed_by_state_code = models.CharField(max_length=2, null=True, db_index=True)
    # Information about the share item clicked
    shared_item_id = models.PositiveIntegerField(default=0, null=True, blank=True)
    shared_item_code = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    site_owner_organization_we_vote_id = models.CharField(max_length=255, null=True)
    include_public_positions = models.BooleanField(default=False)
    include_friends_only_positions = models.BooleanField(default=False)
    date_clicked = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    # We store YYYY as an integer for very fast lookup (ex/ "2017" for the year 2017)
    year_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)


class ShareManager(models.Manager):

    def __unicode__(self):
        return "ShareManager"

    def add_and_remove_email_recipients(
            self,
            campaignx_we_vote_id='',
            email_recipient_list=[],
            shared_by_voter_we_vote_id='',
            super_share_item_id=0,
    ):
        success = True
        status = ''
        existing_emails_in_email_recipient_list = []

        # Get the existing list of SuperShareEmailList recipients for this super_share_item_id
        results = self.retrieve_super_share_email_recipient_list(
            super_share_item_id=super_share_item_id,
            read_only=False,
        )
        if results['email_recipient_list_found']:
            recipient_list = results['email_recipient_list']
            for super_share_email_recipient in recipient_list:
                if super_share_email_recipient.email_address_text.lower() not in email_recipient_list:
                    try:
                        super_share_email_recipient.delete()
                    except Exception as e:
                        status += "DELETE_FAIL: " + str(e) + " "
                else:
                    existing_emails_in_email_recipient_list.append(
                        super_share_email_recipient.email_address_text.lower())

        # At the end, calculate email_recipient_list_to_add by comparing email_recipient_list with
        #  existing_email_recipient_list. Retrieve/augment data from VoterContactEmail
        #  and create SuperShareEmailRecipient from email_recipient_list_to_add
        email_recipient_list_to_add = list(set(email_recipient_list) - set(existing_emails_in_email_recipient_list))
        existing_voter_contact_emails = {}
        if len(email_recipient_list_to_add) > 0:
            # We need to augment the email addresses we are sending to
            from voter.models import VoterManager
            voter_manager = VoterManager()
            voter_contact_results = voter_manager.retrieve_voter_contact_email_list(
                imported_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                read_only=True)
            if voter_contact_results['voter_contact_email_list_found']:
                voter_contact_email_list = voter_contact_results['voter_contact_email_list']
                for voter_contact_email in voter_contact_email_list:
                    existing_voter_contact_emails[voter_contact_email.email_address_text.lower()] = voter_contact_email
        for new_email in email_recipient_list_to_add:
            if new_email.lower() in existing_voter_contact_emails:
                voter_contact_email = existing_voter_contact_emails[new_email.lower()]
                google_contact_id = voter_contact_email.google_contact_id
                recipient_display_name = voter_contact_email.google_display_name
                recipient_first_name = voter_contact_email.google_first_name
                recipient_last_name = voter_contact_email.google_last_name
                recipient_state_code = voter_contact_email.state_code
            else:
                google_contact_id = 0
                recipient_display_name = ''
                recipient_first_name = ''
                recipient_last_name = ''
                recipient_state_code = ''
            defaults = {
                'campaignx_we_vote_id': campaignx_we_vote_id,
                'google_contact_id': google_contact_id,
                'recipient_display_name': recipient_display_name,
                'recipient_first_name': recipient_first_name,
                'recipient_last_name': recipient_last_name,
                'recipient_state_code': recipient_state_code,
                'shared_by_voter_we_vote_id': shared_by_voter_we_vote_id,
            }
            new_results = self.update_or_create_super_share_email_recipient(
                email_address_text=new_email,
                super_share_item_id=super_share_item_id,
                defaults=defaults,
            )

        results = {
            'success': success,
            'status': status,
        }

        return results

    def create_shared_link_clicked(
            self,
            destination_full_url='',
            shared_item_code='',
            shared_item_id=0,
            shared_by_voter_we_vote_id='',
            shared_by_organization_type='',
            shared_by_organization_we_vote_id='',
            site_owner_organization_we_vote_id='',
            viewed_by_voter_we_vote_id='',
            viewed_by_organization_we_vote_id='',
            include_public_positions=False,
            include_friends_only_positions=False):
        status = ""

        try:
            include_public_positions = positive_value_exists(include_public_positions)
            include_friends_only_positions = positive_value_exists(include_friends_only_positions)
            year_as_integer = self.generate_year_as_integer()
            shared_link_clicked = SharedLinkClicked.objects.create(
                destination_full_url=destination_full_url,
                include_public_positions=include_public_positions,
                include_friends_only_positions=include_friends_only_positions,
                shared_item_code=shared_item_code,
                shared_item_id=shared_item_id,
                shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                shared_by_organization_type=shared_by_organization_type,
                shared_by_organization_we_vote_id=shared_by_organization_we_vote_id,
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
                viewed_by_voter_we_vote_id=viewed_by_voter_we_vote_id,
                viewed_by_organization_we_vote_id=viewed_by_organization_we_vote_id,
                year_as_integer=year_as_integer,
            )
            shared_link_clicked_saved = True
            success = True
            status += "SHARED_LINK_CLICKED_CREATED "
        except Exception as e:
            shared_link_clicked_saved = False
            shared_link_clicked = None
            success = False
            status += "SHARED_LINK_CLICKED_NOT_CREATED: " + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'shared_link_clicked_saved':    shared_link_clicked_saved,
            'shared_link_clicked':          shared_link_clicked,
        }
        return results

    def update_or_create_shared_item(
            self,
            destination_full_url='',
            force_create_new=False,
            shared_by_voter_we_vote_id='',
            google_civic_election_id=None,
            defaults={}):
        create_shared_item_code_no_opinions = True
        create_shared_item_code_all_opinions = True
        create_shared_item_code_ready = True
        create_shared_item_code_remind_contacts = True
        shared_item_code_no_opinions = None
        shared_item_code_all_opinions = None
        shared_item_code_ready = None
        shared_item_code_remind_contacts = None
        shared_item_created = False
        shared_item_found = False
        status = ""
        success = True
        if positive_value_exists(google_civic_election_id):
            google_civic_election_id = convert_to_int(google_civic_election_id)
        else:
            google_civic_election_id = 0
        is_remind_contact_share = defaults['is_remind_contact_share'] \
            if 'is_remind_contact_share' in defaults else False
        if positive_value_exists(is_remind_contact_share):
            # destination_full_url is optional because by for remind_contact_share we only require the
            #  built-in /ready and /friends/remind links
            required_variables = positive_value_exists(shared_by_voter_we_vote_id)
        else:
            required_variables = positive_value_exists(shared_by_voter_we_vote_id) and \
                positive_value_exists(destination_full_url)
        if not positive_value_exists(required_variables):
            if positive_value_exists(is_remind_contact_share):
                status += "CREATE_OR_UPDATE_SHARED_ITEM-MISSING_REMIND_CONTACT_REQUIRED_VARIABLE "
            else:
                status += "CREATE_OR_UPDATE_SHARED_ITEM-MISSING_REQUIRED_VARIABLES "
            results = {
                'success':              False,
                'status':               status,
                'shared_item_found':    shared_item_found,
                'shared_item_created':  shared_item_created,
                'shared_item':          None,
            }
            return results

        if force_create_new or positive_value_exists(is_remind_contact_share):
            shared_item = None
            shared_item_found = False
        else:
            results = self.retrieve_shared_item(
                destination_full_url=destination_full_url,
                shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                read_only=False)
            shared_item_found = results['shared_item_found']
            shared_item = results['shared_item']
            success = results['success']
            status += results['status']

        if shared_item_found:
            if positive_value_exists(shared_item.shared_item_code_no_opinions):
                create_shared_item_code_no_opinions = False
            if positive_value_exists(shared_item.shared_item_code_all_opinions):
                create_shared_item_code_all_opinions = False
            if positive_value_exists(shared_item.shared_item_code_ready):
                create_shared_item_code_ready = False
            if positive_value_exists(shared_item.shared_item_code_remind_contacts):
                create_shared_item_code_remind_contacts = False
            if not positive_value_exists(defaults['shared_by_organization_we_vote_id']):
                pass

        if create_shared_item_code_no_opinions:
            random_string = generate_random_string(6)
            # TODO: Confirm its not in use
            shared_item_code_no_opinions = random_string

        if create_shared_item_code_all_opinions:
            random_string = generate_random_string(10)
            # TODO: Confirm its not in use
            shared_item_code_all_opinions = random_string

        if create_shared_item_code_ready:
            random_string = generate_random_string(8)
            # TODO: Confirm its not in use
            shared_item_code_ready = random_string

        if create_shared_item_code_remind_contacts:
            random_string = generate_random_string(8)
            # TODO: Confirm its not in use
            shared_item_code_remind_contacts = random_string

        email_secret_key = defaults['email_secret_key'] if 'email_secret_key' in defaults else None
        other_voter_email_address_text = defaults['other_voter_email_address_text'] \
            if 'other_voter_email_address_text' in defaults else None
        other_voter_display_name = defaults['other_voter_display_name'] \
            if 'other_voter_display_name' in defaults else None
        other_voter_first_name = defaults['other_voter_first_name'] \
            if 'other_voter_first_name' in defaults else None
        other_voter_last_name = defaults['other_voter_last_name'] \
            if 'other_voter_last_name' in defaults else None
        other_voter_we_vote_id = defaults['other_voter_we_vote_id'] if 'other_voter_we_vote_id' in defaults else None
        shared_by_display_name = defaults['shared_by_display_name'] if 'shared_by_display_name' in defaults else None
        shared_by_we_vote_hosted_profile_image_url_large = \
            defaults['shared_by_we_vote_hosted_profile_image_url_large'] \
            if 'shared_by_we_vote_hosted_profile_image_url_large' in defaults else None
        shared_by_we_vote_hosted_profile_image_url_medium = \
            defaults['shared_by_we_vote_hosted_profile_image_url_medium'] \
            if 'shared_by_we_vote_hosted_profile_image_url_medium' in defaults else None
        shared_by_we_vote_hosted_profile_image_url_tiny = \
            defaults['shared_by_we_vote_hosted_profile_image_url_tiny'] \
            if 'shared_by_we_vote_hosted_profile_image_url_tiny' in defaults else None
        shared_message = defaults['shared_message'] if 'shared_message' in defaults else None
        sms_secret_key = defaults['sms_secret_key'] if 'sms_secret_key' in defaults else None

        if shared_item_found:
            try:
                change_to_save = False
                if shared_item.other_voter_display_name != other_voter_display_name:
                    if not positive_value_exists(other_voter_display_name):
                        other_voter_display_name = None
                    shared_item.other_voter_display_name = other_voter_display_name
                    change_to_save = True
                if shared_item.other_voter_first_name != other_voter_first_name:
                    if not positive_value_exists(other_voter_first_name):
                        other_voter_first_name = None
                    shared_item.other_voter_first_name = other_voter_first_name
                    change_to_save = True
                if shared_item.other_voter_last_name != other_voter_last_name:
                    if not positive_value_exists(other_voter_last_name):
                        other_voter_last_name = None
                    shared_item.other_voter_last_name = other_voter_last_name
                    change_to_save = True
                if shared_item.other_voter_email_address_text != other_voter_email_address_text:
                    if not positive_value_exists(other_voter_email_address_text):
                        other_voter_email_address_text = None
                    shared_item.other_voter_email_address_text = other_voter_email_address_text
                    change_to_save = True
                if shared_item.other_voter_we_vote_id != other_voter_we_vote_id:
                    if not positive_value_exists(other_voter_we_vote_id):
                        other_voter_we_vote_id = None
                    shared_item.other_voter_we_vote_id = other_voter_we_vote_id
                    change_to_save = True
                if shared_item.shared_by_display_name != shared_by_display_name:
                    shared_item.shared_by_display_name = shared_by_display_name
                    change_to_save = True
                if shared_item.shared_by_we_vote_hosted_profile_image_url_large \
                        != shared_by_we_vote_hosted_profile_image_url_large:
                    shared_item.shared_by_we_vote_hosted_profile_image_url_large = \
                        shared_by_we_vote_hosted_profile_image_url_large
                    change_to_save = True
                if shared_item.shared_by_we_vote_hosted_profile_image_url_medium \
                        != shared_by_we_vote_hosted_profile_image_url_medium:
                    shared_item.shared_by_we_vote_hosted_profile_image_url_medium = \
                        shared_by_we_vote_hosted_profile_image_url_medium
                    change_to_save = True
                if shared_item.shared_by_we_vote_hosted_profile_image_url_tiny \
                        != shared_by_we_vote_hosted_profile_image_url_tiny:
                    shared_item.shared_by_we_vote_hosted_profile_image_url_tiny = \
                        shared_by_we_vote_hosted_profile_image_url_tiny
                    change_to_save = True
                if positive_value_exists(shared_item_code_no_opinions) and \
                        shared_item.shared_item_code_no_opinions != shared_item_code_no_opinions:
                    shared_item.shared_item_code_no_opinions = shared_item_code_no_opinions
                    change_to_save = True
                if positive_value_exists(shared_item_code_all_opinions) and \
                        shared_item.shared_item_code_all_opinions != shared_item_code_all_opinions:
                    shared_item.shared_item_code_all_opinions = shared_item_code_all_opinions
                    change_to_save = True
                if positive_value_exists(shared_item_code_ready) and \
                        shared_item.shared_item_code_ready != shared_item_code_ready:
                    shared_item.shared_item_code_ready = shared_item_code_ready
                    change_to_save = True
                if positive_value_exists(shared_item_code_remind_contacts) and \
                        shared_item.shared_item_code_remind_contacts != shared_item_code_remind_contacts:
                    shared_item.shared_item_code_remind_contacts = shared_item_code_remind_contacts
                    change_to_save = True
                if shared_item.shared_message != shared_message:
                    if not positive_value_exists(shared_message):
                        shared_message = None
                    shared_item.shared_message = shared_message
                    change_to_save = True
                if not positive_value_exists(shared_item.year_as_integer):
                    shared_item.generate_year_as_integer()
                    change_to_save = True
                if change_to_save:
                    shared_item.save()
                    shared_item_created = True
                    success = True
                    status += "SHARED_ITEM_UPDATED "
            except Exception as e:
                shared_item_created = False
                shared_item = None
                success = False
                status += "SHARED_ITEM_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                shared_item = SharedItem.objects.create(
                    candidate_we_vote_id=defaults['candidate_we_vote_id'],
                    destination_full_url=destination_full_url,
                    email_secret_key=email_secret_key,
                    google_civic_election_id=google_civic_election_id,
                    is_ballot_share=defaults['is_ballot_share'],
                    is_candidate_share=defaults['is_candidate_share'],
                    is_measure_share=defaults['is_measure_share'],
                    is_office_share=defaults['is_office_share'],
                    is_organization_share=defaults['is_organization_share'],
                    is_ready_share=defaults['is_ready_share'],
                    is_remind_contact_share=defaults['is_remind_contact_share'],
                    measure_we_vote_id=defaults['measure_we_vote_id'],
                    office_we_vote_id=defaults['office_we_vote_id'],
                    other_voter_display_name=other_voter_display_name,
                    other_voter_first_name=other_voter_first_name,
                    other_voter_last_name=other_voter_last_name,
                    other_voter_email_address_text=other_voter_email_address_text,
                    other_voter_we_vote_id=other_voter_we_vote_id,
                    shared_by_display_name=shared_by_display_name,
                    shared_by_organization_type=defaults['shared_by_organization_type'],
                    shared_by_organization_we_vote_id=defaults['shared_by_organization_we_vote_id'],
                    shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                    shared_by_we_vote_hosted_profile_image_url_large=shared_by_we_vote_hosted_profile_image_url_large,
                    shared_by_we_vote_hosted_profile_image_url_medium=shared_by_we_vote_hosted_profile_image_url_medium,
                    shared_by_we_vote_hosted_profile_image_url_tiny=shared_by_we_vote_hosted_profile_image_url_tiny,
                    shared_item_code_no_opinions=shared_item_code_no_opinions,
                    shared_item_code_all_opinions=shared_item_code_all_opinions,
                    shared_item_code_ready=shared_item_code_ready,
                    shared_item_code_remind_contacts=shared_item_code_remind_contacts,
                    shared_message=shared_message,
                    site_owner_organization_we_vote_id=defaults['site_owner_organization_we_vote_id'],
                    sms_secret_key=sms_secret_key,
                )
                shared_item_created = True
                shared_item_found = True
                status += "SHARED_ITEM_CREATED "
            except Exception as e:
                shared_item_created = False
                shared_item = None
                success = False
                status += "SHARED_ITEM_NOT_CREATED: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'shared_item_found':    shared_item_found,
            'shared_item_created':  shared_item_created,
            'shared_item':          shared_item,
        }
        return results

    def update_or_create_shared_permissions_granted(
            self,
            shared_by_voter_we_vote_id='',
            shared_by_organization_type='',
            shared_by_organization_we_vote_id='',
            shared_to_voter_we_vote_id='',
            shared_to_organization_we_vote_id='',
            google_civic_election_id=None,
            year_as_integer=None,
            include_friends_only_positions=False):
        shared_permissions_granted_created = False
        shared_permissions_granted_found = False
        status = ""
        success = True
        if positive_value_exists(google_civic_election_id):
            google_civic_election_id = convert_to_int(google_civic_election_id)
        else:
            google_civic_election_id = 0

        if not positive_value_exists(shared_by_voter_we_vote_id) \
                or not positive_value_exists(shared_to_voter_we_vote_id) or not positive_value_exists(year_as_integer):
            status += "CREATE_OR_UPDATE_SHARED_PERMISSIONS_GRANTED-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':              False,
                'status':               status,
                'shared_permissions_granted_found':    shared_permissions_granted_found,
                'shared_permissions_granted_created':  shared_permissions_granted_created,
                'shared_permissions_granted':          None,
            }
            return results

        results = self.retrieve_shared_permissions_granted(
            shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
            shared_to_voter_we_vote_id=shared_to_voter_we_vote_id,
            google_civic_election_id=google_civic_election_id,
            year_as_integer=year_as_integer,
            read_only=False)
        shared_permissions_granted_found = results['shared_permissions_granted_found']
        shared_permissions_granted = results['shared_permissions_granted']
        success = results['success']
        status += results['status']

        if shared_permissions_granted_found:
            # Are we going from include_friends_only_positions == False to include_friends_only_positions == True?
            include_friends_only_positions_added = \
                not positive_value_exists(shared_permissions_granted.include_friends_only_positions) \
                and positive_value_exists(include_friends_only_positions)
            if not positive_value_exists(shared_permissions_granted.year_as_integer) \
                    or include_friends_only_positions_added:
                # There is a reason to update
                try:
                    change_to_save = False
                    if not positive_value_exists(shared_permissions_granted.year_as_integer):
                        shared_permissions_granted.year_as_integer = year_as_integer
                        change_to_save = True
                    if include_friends_only_positions_added:
                        shared_permissions_granted.include_friends_only_positions = True
                        change_to_save = True
                    if change_to_save:
                        shared_permissions_granted.save()
                        shared_permissions_granted_created = True
                        success = True
                        status += "SHARED_PERMISSIONS_GRANTED_UPDATED "
                except Exception as e:
                    shared_permissions_granted_created = False
                    shared_permissions_granted = None
                    success = False
                    status += "SHARED_PERMISSIONS_GRANTED_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                shared_permissions_granted = SharedPermissionsGranted.objects.create(
                    shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                    shared_by_organization_type=shared_by_organization_type,
                    shared_by_organization_we_vote_id=shared_by_organization_we_vote_id,
                    shared_to_voter_we_vote_id=shared_to_voter_we_vote_id,
                    shared_to_organization_we_vote_id=shared_to_organization_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    year_as_integer=year_as_integer,
                    include_friends_only_positions=include_friends_only_positions,
                )
                shared_permissions_granted_created = True
                shared_permissions_granted_found = True
                status += "SHARED_PERMISSIONS_GRANTED_CREATED "
            except Exception as e:
                shared_permissions_granted_created = False
                shared_permissions_granted = None
                success = False
                status += "SHARED_PERMISSIONS_GRANTED_NOT_CREATED: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'shared_permissions_granted_found':    shared_permissions_granted_found,
            'shared_permissions_granted_created':  shared_permissions_granted_created,
            'shared_permissions_granted':          shared_permissions_granted,
        }
        return results

    def update_or_create_super_share_email_recipient(
            self,
            email_address_text='',
            super_share_item_id=0,
            defaults={}):
        super_share_email_recipient_created = False
        super_share_email_recipient_found = False
        status = ""
        if not positive_value_exists(super_share_item_id) or not positive_value_exists(email_address_text):
            status += "CREATE_OR_UPDATE_EMAIL_RECIPIENT-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':                              False,
                'status':                               status,
                'super_share_email_recipient_found':    super_share_email_recipient_found,
                'super_share_email_recipient_created':  super_share_email_recipient_created,
                'super_share_email_recipient':          None,
            }
            return results

        results = self.retrieve_super_share_email_recipient_list(
            email_address_text=email_address_text,
            super_share_item_id=super_share_item_id,
            read_only=False)
        super_share_email_recipient_found = results['email_recipient_found']
        super_share_email_recipient = results['email_recipient']
        success = results['success']
        status += results['status']

        if super_share_email_recipient_found:
            try:
                change_to_save = False
                if 'campaignx_we_vote_id' in defaults:
                    super_share_email_recipient.campaignx_we_vote_id = defaults['campaignx_we_vote_id']
                    change_to_save = True
                if 'date_sent_to_email' in defaults:
                    super_share_email_recipient.date_sent_to_email = defaults['date_sent_to_email']
                    change_to_save = True
                if 'google_contact_id' in defaults:
                    super_share_email_recipient.google_contact_id = defaults['google_contact_id']
                    change_to_save = True
                if 'recipient_first_name' in defaults:
                    super_share_email_recipient.recipient_first_name = defaults['recipient_first_name']
                    change_to_save = True
                if 'recipient_last_name' in defaults:
                    super_share_email_recipient.recipient_last_name = defaults['recipient_last_name']
                    change_to_save = True
                if 'recipient_state_code' in defaults:
                    super_share_email_recipient.recipient_state_code = defaults['recipient_state_code']
                    change_to_save = True
                if 'recipient_voter_we_vote_id' in defaults:
                    super_share_email_recipient.recipient_voter_we_vote_id = defaults['recipient_voter_we_vote_id']
                    change_to_save = True
                if 'shared_by_voter_we_vote_id' in defaults:
                    super_share_email_recipient.shared_by_voter_we_vote_id = defaults['shared_by_voter_we_vote_id']
                    change_to_save = True
                if change_to_save:
                    super_share_email_recipient.save()
                    super_share_email_recipient_created = True
                    success = True
                    status += "SUPER_SHARE_EMAIL_RECIPIENT_UPDATED "
            except Exception as e:
                super_share_email_recipient_created = False
                super_share_email_recipient = None
                success = False
                status += "SUPER_SHARE_EMAIL_RECIPIENT_NOT_UPDATED: " + str(e) + " "

        if success and not super_share_email_recipient_found:
            try:
                super_share_email_recipient = SuperShareEmailRecipient.objects.create(
                    campaignx_we_vote_id=defaults['campaignx_we_vote_id']
                    if 'campaignx_we_vote_id' in defaults else None,
                    date_sent_to_email=defaults['date_sent_to_email']
                    if 'date_sent_to_email' in defaults else None,
                    email_address_text=email_address_text.lower(),
                    google_contact_id=defaults['google_contact_id']
                    if 'google_contact_id' in defaults else None,
                    recipient_display_name=defaults['recipient_display_name']
                    if 'recipient_display_name' in defaults else None,
                    recipient_first_name=defaults['recipient_first_name']
                    if 'recipient_first_name' in defaults else None,
                    recipient_last_name=defaults['recipient_last_name']
                    if 'recipient_last_name' in defaults else None,
                    recipient_state_code=defaults['recipient_state_code']
                    if 'recipient_state_code' in defaults else None,
                    recipient_voter_we_vote_id=defaults['recipient_voter_we_vote_id']
                    if 'recipient_voter_we_vote_id' in defaults else None,
                    shared_by_voter_we_vote_id=defaults['shared_by_voter_we_vote_id']
                    if 'shared_by_voter_we_vote_id' in defaults else None,
                    super_share_item_id=super_share_item_id,
                )
                super_share_email_recipient_created = True
                super_share_email_recipient_found = True
                status += "SUPER_SHARE_EMAIL_RECIPIENT_CREATED "
            except Exception as e:
                super_share_email_recipient_created = False
                super_share_email_recipient = None
                success = False
                status += "SUPER_SHARE_EMAIL_RECIPIENT_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                              success,
            'status':                               status,
            'super_share_email_recipient_found':    super_share_email_recipient_found,
            'super_share_email_recipient_created':  super_share_email_recipient_created,
            'super_share_email_recipient':          super_share_email_recipient,
        }
        return results

    def update_or_create_super_share_item(
            self,
            campaignx_we_vote_id='',
            shared_by_voter_we_vote_id='',
            super_share_item_id=0,
            defaults={}):
        super_share_item_created = False
        super_share_item_found = False
        status = ""
        success = True
        if not positive_value_exists(campaignx_we_vote_id) or not positive_value_exists(shared_by_voter_we_vote_id):
            status += "CREATE_OR_UPDATE_SUPER_SHARE_ITEM-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':              False,
                'status':               status,
                'super_share_item_found':    super_share_item_found,
                'super_share_item_created':  super_share_item_created,
                'super_share_item':          None,
            }
            return results

        results = self.retrieve_super_share_item(
            campaignx_we_vote_id=campaignx_we_vote_id,
            shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
            super_share_item_id=super_share_item_id,
            read_only=False)
        super_share_item_found = results['super_share_item_found']
        super_share_item = results['super_share_item']
        success = results['success']
        status += results['status']

        # if create_super_share_item_code_no_opinions:
        #     random_string = generate_random_string(6)
        #     # TODO: Confirm its not in use
        #     super_share_item_code_no_opinions = random_string
        #
        # if create_super_share_item_code_all_opinions:
        #     random_string = generate_random_string(10)
        #     # TODO: Confirm its not in use
        #     super_share_item_code_all_opinions = random_string

        if super_share_item_found:
            try:
                change_to_save = False
                personalized_message_changed = defaults['personalized_message_changed'] \
                    if 'personalized_message_changed' in defaults else False
                if positive_value_exists(personalized_message_changed):
                    super_share_item.personalized_message = defaults['personalized_message'] \
                        if 'personalized_message' in defaults else ''
                    change_to_save = True
                personalized_subject_changed = defaults['personalized_subject_changed'] \
                    if 'personalized_subject_changed' in defaults else False
                if positive_value_exists(personalized_subject_changed):
                    super_share_item.personalized_subject = defaults['personalized_subject'] \
                        if 'personalized_subject' in defaults else ''
                    change_to_save = True
                if change_to_save:
                    super_share_item.save()
                    super_share_item_created = True
                    success = True
                    status += "SUPER_SHARE_ITEM_UPDATED "
            except Exception as e:
                super_share_item_created = False
                super_share_item = None
                success = False
                status += "SUPER_SHARE_ITEM_NOT_UPDATED: " + str(e) + " "

        if success and not super_share_item_found:
            try:
                super_share_item = SuperShareItem.objects.create(
                    campaignx_we_vote_id=defaults['campaignx_we_vote_id']
                    if 'campaignx_we_vote_id' in defaults else None,
                    destination_full_url=defaults['destination_full_url']
                    if 'destination_full_url' in defaults else None,
                    in_draft_mode=defaults['in_draft_mode']
                    if 'in_draft_mode' in defaults else True,
                    personalized_message=defaults['personalized_message']
                    if 'personalized_message' in defaults else None,
                    personalized_subject=defaults['personalized_subject']
                    if 'personalized_subject' in defaults else None,
                    shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                    site_owner_organization_we_vote_id=defaults['site_owner_organization_we_vote_id']
                    if 'site_owner_organization_we_vote_id' in defaults else None,
                )
                super_share_item_created = True
                super_share_item_found = True
                status += "SUPER_SHARE_ITEM_CREATED "
            except Exception as e:
                super_share_item_created = False
                super_share_item = None
                success = False
                status += "SUPER_SHARE_ITEM_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'super_share_item_found':   super_share_item_found,
            'super_share_item_created': super_share_item_created,
            'super_share_item':         super_share_item,
        }
        return results

    def fetch_shared_link_clicked_unique_sharer_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='shared_by_voter_we_vote_id')

    def fetch_shared_link_clicked_unique_viewer_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='viewed_by_voter_we_vote_id')

    def fetch_shared_link_clicked_shared_links_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='shared_item_id')

    def fetch_shared_link_clicked_shared_links_click_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='id')

    def fetch_shared_link_clicked_count(
            self, shared_by_state_code_list=[],
            viewed_by_state_code_list=[],
            year_as_integer_list=[],
            field_for_distinct_filter=''):
        if 'test' in sys.argv:
            # If coming from a test, we cannot use readonly
            queryset = SharedLinkClicked.objects.all()
        else:
            queryset = SharedLinkClicked.objects.using('readonly').all()

        if positive_value_exists(len(shared_by_state_code_list)):
            queryset = queryset.filter(shared_by_state_code__in=shared_by_state_code_list)
        if positive_value_exists(len(viewed_by_state_code_list)):
            queryset = queryset.filter(viewed_by_state_code__in=viewed_by_state_code_list)
        if positive_value_exists(len(year_as_integer_list)):
            queryset = queryset.filter(year_as_integer__in=year_as_integer_list)
        if positive_value_exists(field_for_distinct_filter):
            queryset = queryset.values(field_for_distinct_filter).distinct()

        shared_link_clicked_count = 0
        try:
            shared_link_clicked_count = queryset.count()
        except Exception as e:
            pass

        return shared_link_clicked_count

    def fetch_shared_link_clicked_shared_links_click_without_reclick_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        if 'test' in sys.argv:
            # If coming from a test, we cannot use readonly
            queryset = SharedLinkClicked.objects.all()
        else:
            queryset = SharedLinkClicked.objects.using('readonly').all()

        if positive_value_exists(len(shared_by_state_code_list)):
            queryset = queryset.filter(shared_by_state_code__in=shared_by_state_code_list)
        if positive_value_exists(len(viewed_by_state_code_list)):
            queryset = queryset.filter(viewed_by_state_code__in=viewed_by_state_code_list)
        if positive_value_exists(len(year_as_integer_list)):
            queryset = queryset.filter(year_as_integer__in=year_as_integer_list)
        queryset = queryset.order_by('shared_item_id', 'viewed_by_voter_we_vote_id')\
            .distinct('shared_item_id', 'viewed_by_voter_we_vote_id')

        shared_link_clicked_count = 0
        try:
            shared_link_clicked_count = queryset.count()
        except Exception as e:
            pass

        return shared_link_clicked_count

    def generate_year_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        year_as_string = "{:d}".format(
            datetime_now.year,
        )
        return convert_to_int(year_as_string)

    def retrieve_shared_item(
            self, shared_item_id=0,
            shared_item_code='',
            destination_full_url='',
            shared_by_voter_we_vote_id='',
            google_civic_election_id='',
            read_only=False):
        """

        :param shared_item_id:
        :param shared_item_code:
        :param destination_full_url:
        :param shared_by_voter_we_vote_id:
        :param google_civic_election_id:
        :param read_only:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        shared_item_found = False
        shared_item = SharedItem()
        shared_item_list_found = False
        shared_item_list = []
        status = ""

        try:
            if positive_value_exists(shared_item_id):
                if positive_value_exists(read_only):
                    shared_item = SharedItem.objects.using('readonly').get(
                        id=shared_item_id,
                        deleted=False
                    )
                else:
                    shared_item = SharedItem.objects.get(
                        id=shared_item_id,
                        deleted=False
                    )
                shared_item_id = shared_item.id
                shared_item_found = True
                success = True
                status += "RETRIEVE_SHARED_ITEM_FOUND_BY_ID "
            elif positive_value_exists(shared_item_code):
                if positive_value_exists(read_only):
                    shared_item = SharedItem.objects.using('readonly').get(
                        Q(shared_item_code_no_opinions=shared_item_code) |
                        Q(shared_item_code_all_opinions=shared_item_code) |
                        Q(shared_item_code_ready=shared_item_code) |
                        Q(shared_item_code_remind_contacts=shared_item_code),
                        deleted=False
                    )
                else:
                    shared_item = SharedItem.objects.get(
                        Q(shared_item_code_no_opinions=shared_item_code) |
                        Q(shared_item_code_all_opinions=shared_item_code) |
                        Q(shared_item_code_ready=shared_item_code) |
                        Q(shared_item_code_remind_contacts=shared_item_code),
                        deleted=False
                    )
                shared_item_id = shared_item.id
                shared_item_found = True
                success = True
                status += "RETRIEVE_SHARED_ITEM_FOUND_BY_CODE "
            elif positive_value_exists(destination_full_url) and positive_value_exists(shared_by_voter_we_vote_id):
                if positive_value_exists(read_only):
                    shared_item_queryset = SharedItem.objects.using('readonly').all()
                else:
                    shared_item_queryset = SharedItem.objects.all()
                if positive_value_exists(google_civic_election_id):
                    shared_item_queryset = shared_item_queryset.filter(
                        destination_full_url__iexact=destination_full_url,
                        shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                        google_civic_election_id=google_civic_election_id,
                        deleted=False
                    )
                else:
                    shared_item_queryset = shared_item_queryset.filter(
                        destination_full_url__iexact=destination_full_url,
                        shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                        deleted=False
                    )
                # We need the sms that has been verified sms at top of list
                shared_item_queryset = shared_item_queryset.order_by('-date_first_shared')
                shared_item_list = shared_item_queryset

                if len(shared_item_list):
                    if len(shared_item_list) == 1:
                        # If only one shared_item is found, return the results as a single shared_item
                        shared_item = shared_item_list[0]
                        shared_item_id = shared_item.id
                        shared_item_found = True
                        shared_item_list_found = False
                        success = True
                        status += "RETRIEVE_SHARED_ITEM_FOUND_BY_URL-ONLY_ONE_FOUND "
                    else:
                        success = True
                        shared_item = shared_item_list[0]
                        shared_item_found = True
                        shared_item_list_found = True
                        status += 'RETRIEVE_SHARED_ITEM_FOUND_BY_URL-LIST_RETRIEVED '
                else:
                    success = True
                    shared_item_list_found = False
                    status += 'RETRIEVE_SHARED_ITEM-NO_SHARED_ITEM_LIST_RETRIEVED '
            else:
                shared_item_found = False
                success = False
                status += "RETRIEVE_SHARED_ITEM_VARIABLES_MISSING "
        except SharedItem.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_SHARED_ITEM_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED_RETRIEVE_SHARED_ITEM: ' + str(e) + ' '

        results = {
            'success':                 success,
            'status':                  status,
            'DoesNotExist':            exception_does_not_exist,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'shared_item_found':       shared_item_found,
            'shared_item_id':          shared_item_id,
            'shared_item':             shared_item,
            'shared_item_list_found':  shared_item_list_found,
            'shared_item_list':        shared_item_list,
        }
        return results

    def retrieve_shared_permissions_granted(
            self, shared_permissions_granted_id=0,
            shared_by_voter_we_vote_id='',
            shared_to_voter_we_vote_id='',
            google_civic_election_id=0,
            year_as_integer=0,
            current_year_only=True,
            read_only=False):
        """
        This implementation assumes we only ever get single item results
        :param shared_permissions_granted_id:
        :param shared_by_voter_we_vote_id:
        :param shared_to_voter_we_vote_id:
        :param google_civic_election_id:
        :param year_as_integer:
        :param current_year_only:
        :param read_only:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        shared_permissions_granted_found = False
        shared_permissions_granted = None
        status = ""

        if positive_value_exists(current_year_only):
            year_as_integer = self.generate_year_as_integer()

        try:
            if positive_value_exists(shared_permissions_granted_id):
                if positive_value_exists(read_only):
                    shared_permissions_granted = SharedPermissionsGranted.objects.using('readonly').get(
                        id=shared_permissions_granted_id,
                        deleted=False
                    )
                else:
                    shared_permissions_granted = SharedPermissionsGranted.objects.get(
                        id=shared_permissions_granted_id,
                        deleted=False
                    )
                shared_permissions_granted_id = shared_permissions_granted.id
                shared_permissions_granted_found = True
                success = True
                status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND_BY_ID "
            elif positive_value_exists(shared_by_voter_we_vote_id) \
                    and positive_value_exists(shared_to_voter_we_vote_id) and positive_value_exists(year_as_integer):
                if positive_value_exists(read_only):
                    shared_permissions_granted_queryset = SharedPermissionsGranted.objects.using('readonly').all()
                else:
                    shared_permissions_granted_queryset = SharedPermissionsGranted.objects.all()
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                    shared_to_voter_we_vote_id__iexact=shared_to_voter_we_vote_id,
                    deleted=False
                )
                if positive_value_exists(google_civic_election_id):
                    shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                        google_civic_election_id=google_civic_election_id,
                    )
                if positive_value_exists(year_as_integer):
                    shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                        year_as_integer=year_as_integer,
                    )
                # We need the sms that has been verified sms at top of list
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.order_by('-id')
                shared_permissions_granted_list = list(shared_permissions_granted_queryset)

                if len(shared_permissions_granted_list):
                    if len(shared_permissions_granted_list) == 1:
                        # If only one shared_permissions_granted is found,
                        # return the results as a single shared_permissions_granted
                        shared_permissions_granted = shared_permissions_granted_list[0]
                        shared_permissions_granted_id = shared_permissions_granted.id
                        shared_permissions_granted_found = True
                        success = True
                        status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND-ONLY_ONE_FOUND "
                    else:
                        success = True
                        shared_permissions_granted = shared_permissions_granted_list[0]
                        shared_permissions_granted_found = True
                        status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND-LIST_RETRIEVED '
                        if not positive_value_exists(read_only):
                            # Consider marking additional items as deleted
                            number_found = len(shared_permissions_granted_list)
                            for index in range(1, number_found):
                                temp_shared_permissions_granted = shared_permissions_granted_list[index]
                                temp_shared_permissions_granted.deleted = True
                                temp_shared_permissions_granted.save()
                else:
                    success = True
                    status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED-NO_SHARED_PERMISSIONS_GRANTED_LIST_RETRIEVED '
            else:
                shared_permissions_granted_found = False
                success = False
                status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_VARIABLES_MISSING "
        except SharedPermissionsGranted.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_shared_permissions_granted SharedPermissionsGranted: ' + str(e) + ' '

        results = {
            'success':                 success,
            'status':                  status,
            'DoesNotExist':            exception_does_not_exist,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'shared_permissions_granted_found':       shared_permissions_granted_found,
            'shared_permissions_granted_id':          shared_permissions_granted_id,
            'shared_permissions_granted':             shared_permissions_granted,
        }
        return results

    def retrieve_shared_permissions_granted_list(self,
                                                 shared_by_voter_we_vote_id='',
                                                 shared_to_voter_we_vote_id='',
                                                 google_civic_election_id=0,
                                                 year_as_integer=0,
                                                 current_year_only=True,
                                                 only_include_friends_only_positions=False,
                                                 read_only=False):
        shared_permissions_granted_list_found = False
        shared_permissions_granted_list = []
        status = ""
        if positive_value_exists(current_year_only):
            year_as_integer = self.generate_year_as_integer()

        try:
            if positive_value_exists(read_only):
                shared_permissions_granted_queryset = SharedPermissionsGranted.objects.using('readonly').all()
            else:
                shared_permissions_granted_queryset = SharedPermissionsGranted.objects.all()
            shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                deleted=False
            )
            if positive_value_exists(shared_by_voter_we_vote_id):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                )
            if positive_value_exists(shared_to_voter_we_vote_id):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    shared_to_voter_we_vote_id__iexact=shared_to_voter_we_vote_id,
                )
            if positive_value_exists(google_civic_election_id):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    google_civic_election_id=google_civic_election_id,
                )
            if positive_value_exists(year_as_integer):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    year_as_integer=year_as_integer,
                )
            if positive_value_exists(only_include_friends_only_positions):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    include_friends_only_positions=True,
                )

            shared_permissions_granted_queryset = shared_permissions_granted_queryset.order_by('-id')
            shared_permissions_granted_list = list(shared_permissions_granted_queryset)

            if len(shared_permissions_granted_list):
                success = True
                shared_permissions_granted_list_found = True
                status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND-LIST_RETRIEVED '
            else:
                success = True
                shared_permissions_granted_list_found = False
                status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED-NO_SHARED_PERMISSIONS_GRANTED_LIST_RETRIEVED '
        except Exception as e:
            success = False
            status += 'FAILED-RETRIEVE_SHARED_PERMISSIONS_GRANTED_LIST: ' + str(e) + ' '

        results = {
            'success': success,
            'status': status,
            'shared_permissions_granted_list_found': shared_permissions_granted_list_found,
            'shared_permissions_granted_list': shared_permissions_granted_list,
        }
        return results

    def retrieve_super_share_email_recipient_list(
            self,
            email_address_text='',
            read_only=True,
            retrieve_count_limit=0,
            retrieve_only_if_not_sent=False,
            super_share_email_recipient_already_reviewed_list=[],
            super_share_item_id=0):
        email_recipient = None
        email_recipient_found = False
        email_recipient_list = []
        success = True
        status = ""

        try:
            if read_only:
                queryset = SuperShareEmailRecipient.objects.using('readonly').all()
            else:
                queryset = SuperShareEmailRecipient.objects.all()
            queryset = queryset.filter(super_share_item_id=super_share_item_id)
            if positive_value_exists(email_address_text):
                queryset = queryset.filter(email_address_text__iexact=email_address_text)
            if positive_value_exists(retrieve_only_if_not_sent):
                queryset = queryset.filter(date_sent_to_email__isnull=True)
            if super_share_email_recipient_already_reviewed_list and \
                    len(super_share_email_recipient_already_reviewed_list) > 0:
                queryset = queryset.exclude(id__in=super_share_email_recipient_already_reviewed_list)
            queryset = queryset.order_by('-id')  # Put most recent at top of list

            if positive_value_exists(retrieve_count_limit):
                email_recipient_list = queryset[:retrieve_count_limit]
            else:
                email_recipient_list = list(queryset)

            email_recipient_list_found = positive_value_exists(len(email_recipient_list))
            status += "RETRIEVE_SUPER_SHARE_EMAIL_RECIPIENT_LIST_SUCCEEDED "
            if len(email_recipient_list) == 1:
                email_recipient = email_recipient_list[0]
                email_recipient_found = True
        except Exception as e:
            success = False
            status += "RETRIEVE_SUPER_SHARE_EMAIL_RECIPIENT_LIST_FAILED: " + str(e) + " "
            email_recipient_list_found = False

        results = {
            'success':                                  success,
            'status':                                   status,
            'email_recipient_list':                     email_recipient_list,
            'email_recipient_list_found':               email_recipient_list_found,
            'email_recipient':                          email_recipient,
            'email_recipient_found':                    email_recipient_found,
        }
        return results

    def retrieve_super_share_item(
            self,
            campaignx_we_vote_id='',
            super_share_item_id=0,
            super_share_item_code='',
            destination_full_url='',
            shared_by_voter_we_vote_id='',
            read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        super_share_item_found = False
        super_share_item = SuperShareItem()
        super_share_item_list_found = False
        super_share_item_list = []
        status = ""

        try:
            if positive_value_exists(super_share_item_id):
                if positive_value_exists(read_only):
                    super_share_item = SuperShareItem.objects.using('readonly').get(
                        id=super_share_item_id,
                    )
                else:
                    super_share_item = SuperShareItem.objects.get(
                        id=super_share_item_id,
                    )
                super_share_item_id = super_share_item.id
                super_share_item_found = True
                success = True
                status += "RETRIEVE_SUPER_SHARE_ITEM_FOUND_BY_ID "
            elif positive_value_exists(campaignx_we_vote_id) and positive_value_exists(shared_by_voter_we_vote_id):
                if positive_value_exists(read_only):
                    super_share_item_queryset = SuperShareItem.objects.using('readonly').all()
                else:
                    super_share_item_queryset = SuperShareItem.objects.all()
                super_share_item_queryset = super_share_item_queryset.filter(
                    shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                    campaignx_we_vote_id__iexact=campaignx_we_vote_id,
                    in_draft_mode=True
                )
                super_share_item_queryset = super_share_item_queryset.order_by('-date_created')
                super_share_item_list = list(super_share_item_queryset)

                if len(super_share_item_list):
                    if len(super_share_item_list) == 1:
                        # If only one super_share_item is found, return the results as a single super_share_item
                        super_share_item = super_share_item_list[0]
                        super_share_item_id = super_share_item.id
                        super_share_item_found = True
                        super_share_item_list_found = False
                        success = True
                        status += "RETRIEVE_SUPER_SHARE_ITEM_FOUND_BY_CAMPAIGN-ONLY_ONE_FOUND "
                    else:
                        success = True
                        super_share_item = super_share_item_list[0]
                        super_share_item_found = True
                        super_share_item_list_found = True
                        status += 'RETRIEVE_SUPER_SHARE_ITEM_FOUND_BY_CAMPAIGN-LIST_RETRIEVED '
                else:
                    success = True
                    super_share_item_list_found = False
                    status += 'RETRIEVE_SUPER_SHARE_ITEM-NO_SUPER_SHARE_ITEM_LIST_RETRIEVED '
            else:
                super_share_item_found = False
                success = False
                status += "RETRIEVE_SUPER_SHARE_ITEM_VARIABLES_MISSING "
        except SuperShareItem.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_SUPER_SHARE_ITEM_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED_RETRIEVE_SUPER_SHARE_ITEM: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'super_share_item_found':       super_share_item_found,
            'super_share_item_id':          super_share_item_id,
            'super_share_item':             super_share_item,
            'super_share_item_list_found':  super_share_item_list_found,
            'super_share_item_list':        super_share_item_list,
        }
        return results


class SuperShareItem(models.Model):
    """
    Keep track of the data assembled in the Super Share process
    """
    # What is being shared
    campaignx_news_item_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    date_created = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    date_sent_to_email = models.DateTimeField(null=True, default=None)
    # The ending destination -- meaning the link that is being shared
    destination_full_url = models.URLField(max_length=255, blank=True, null=True)
    in_draft_mode = models.BooleanField(default=True, db_index=True)
    personalized_message = models.TextField(null=True, blank=True, db_index=True)
    personalized_subject = models.TextField(null=True, blank=True, db_index=True)
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    # The owner of the custom site this share was from
    site_owner_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=False, db_index=True)


class SuperShareEmailRecipient(models.Model):
    """
    One recipient of one super shared email.
    """
    # What is being shared
    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    date_sent_to_email = models.DateTimeField(null=True, default=None)
    email_address_text = models.TextField(null=True, blank=True, db_index=True)
    google_contact_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    recipient_display_name = models.CharField(max_length=255, default=None, null=True)
    recipient_first_name = models.CharField(max_length=255, default=None, null=True)
    recipient_last_name = models.CharField(max_length=255, default=None, null=True)
    recipient_state_code = models.CharField(max_length=2, default=None, null=True, db_index=True)
    recipient_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    shared_by_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    super_share_item_id = models.PositiveIntegerField(default=0, null=True, blank=True)
