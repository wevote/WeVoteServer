# email_outbound/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import date, timedelta
from django.apps import apps
from django.db import models
from django.core.mail import EmailMultiAlternatives, get_connection
from config.base import get_environment_variable
from wevote_functions.functions import convert_to_int, extract_email_addresses_from_string, generate_random_string, \
    positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_email_integer, fetch_site_unique_id_prefix

CAMPAIGNX_NEWS_ITEM_TEMPLATE = 'CAMPAIGNX_NEWS_ITEM_TEMPLATE'
CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE = 'CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE'
CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE = 'CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE'
CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE = 'CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE'
FRIEND_ACCEPTED_INVITATION_TEMPLATE = 'FRIEND_ACCEPTED_INVITATION_TEMPLATE'
FRIEND_INVITATION_TEMPLATE = 'FRIEND_INVITATION_TEMPLATE'
GENERIC_EMAIL_TEMPLATE = 'GENERIC_EMAIL_TEMPLATE'
LINK_TO_SIGN_IN_TEMPLATE = 'LINK_TO_SIGN_IN_TEMPLATE'
MESSAGE_TO_FRIEND_TEMPLATE = 'MESSAGE_TO_FRIEND_TEMPLATE'
NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE = 'NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE'
NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE = 'NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE'
VERIFY_EMAIL_ADDRESS_TEMPLATE = 'VERIFY_EMAIL_ADDRESS_TEMPLATE'
SEND_BALLOT_TO_SELF = 'SEND_BALLOT_TO_SELF'
SEND_BALLOT_TO_FRIENDS = 'SEND_BALLOT_TO_FRIENDS'
SIGN_IN_CODE_EMAIL_TEMPLATE = 'SIGN_IN_CODE_EMAIL_TEMPLATE'
KIND_OF_EMAIL_TEMPLATE_CHOICES = (
    (GENERIC_EMAIL_TEMPLATE,  'Generic Email'),
    (FRIEND_ACCEPTED_INVITATION_TEMPLATE, 'Accept an invitation to be a Friend'),
    (FRIEND_INVITATION_TEMPLATE, 'Invite Friend'),
    (LINK_TO_SIGN_IN_TEMPLATE, 'Link to sign in.'),
    (MESSAGE_TO_FRIEND_TEMPLATE, 'Message to friend'),
    (NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE, 'New opinion from Friend.'),
    (NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE, 'Daily summary of activity for the voter.'),
    (VERIFY_EMAIL_ADDRESS_TEMPLATE, 'Verify Senders Email Address'),
    (SEND_BALLOT_TO_SELF, 'Send ballot to self'),
    (SEND_BALLOT_TO_FRIENDS, 'Send ballot to friends'),
    (SIGN_IN_CODE_EMAIL_TEMPLATE, 'Send code to verify sign in.'),
)

TO_BE_PROCESSED = 'TO_BE_PROCESSED'
BEING_ASSEMBLED = 'BEING_ASSEMBLED'
SCHEDULED = 'SCHEDULED'
ASSEMBLY_STATUS_CHOICES = (
    (TO_BE_PROCESSED,  'Email to be assembled'),
    (BEING_ASSEMBLED, 'Email being assembled with template'),
    (SCHEDULED, 'Sent to the scheduler'),
)
WAITING_FOR_VERIFICATION = 'WAITING_FOR_VERIFICATION'

BEING_SENT = 'BEING_SENT'
SENT = 'SENT'
SEND_STATUS_CHOICES = (
    (TO_BE_PROCESSED,  'Message to be processed'),
    (BEING_SENT, 'Message being sent'),
    (SENT, 'Message sent'),
)

SENDGRID_API_KEY = get_environment_variable("SENDGRID_API_KEY", no_exception=True)

EMAIL_HOST = get_environment_variable("EMAIL_HOST", no_exception=True)
EMAIL_HOST_USER = get_environment_variable("EMAIL_HOST_USER", no_exception=True)
EMAIL_HOST_PASSWORD = get_environment_variable("EMAIL_HOST_PASSWORD", no_exception=True)
EMAIL_PORT = get_environment_variable("EMAIL_PORT", no_exception=True)
EMAIL_USE_TLS = get_environment_variable("EMAIL_USE_TLS", no_exception=True)


class EmailAddress(models.Model):
    """
    We give every email address its own unique we_vote_id for things like invitations
    """
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "email", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_email_integer
    we_vote_id = models.CharField(
        verbose_name="we vote id of this email address", max_length=255, default=None, null=True,
        blank=True, unique=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the email owner", max_length=255, null=True, blank=True, unique=False)
    # Until an EmailAddress has had its ownership verified, multiple voter accounts can try to use it
    normalized_email_address = models.EmailField(
        verbose_name='email address', max_length=255, null=False, blank=False, unique=False)
    # Has this email been verified by the owner?
    email_ownership_is_verified = models.BooleanField(default=False)
    # Has this email had a permanent bounce? If so, we should not send emails to it.
    email_permanent_bounce = models.BooleanField(default=False)
    secret_key = models.CharField(
        verbose_name="secret key to verify ownership of email", max_length=255, null=True, blank=True, unique=True)
    subscription_secret_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    deleted = models.BooleanField(default=False)  # If email address is removed from person's account, mark as deleted

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_email_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "email" = tells us this is a unique id for a EmailAddress
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}email{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(EmailAddress, self).save(*args, **kwargs)


class EmailOutboundDescription(models.Model):
    """
    Specifications for a single email we want to send. This data is used to assemble an EmailScheduled
    """
    kind_of_email_template = models.CharField(max_length=50, choices=KIND_OF_EMAIL_TEMPLATE_CHOICES,
                                              default=GENERIC_EMAIL_TEMPLATE)
    sender_voter_name = models.CharField(
        verbose_name='sender full name', max_length=255, null=True, blank=True, unique=False)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    sender_voter_email = models.EmailField(
        verbose_name='email address for sender', max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    recipient_email_we_vote_id = models.CharField(
        verbose_name="email we vote id for recipient", max_length=255, null=True, blank=True, unique=False)
    # We include this here for data monitoring and debugging
    recipient_voter_email = models.EmailField(
        verbose_name='email address for recipient', max_length=255, null=True, blank=True, unique=False)
    list_unsubscribe_mailto = models.TextField(null=True, blank=True)
    list_unsubscribe_url = models.TextField(null=True, blank=True)
    template_variables_in_json = models.TextField(null=True, blank=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class EmailScheduled(models.Model):
    """
    Used to tell the email server literally what to send. If an email bounces temporarily, we will
    want to trigger the EmailOutboundDescription to generate an new EmailScheduled entry.
    """
    subject = models.CharField(verbose_name="email subject", max_length=255, null=True, blank=True, unique=False)
    message_text = models.TextField(null=True, blank=True)
    message_html = models.TextField(null=True, blank=True)
    sender_voter_name = models.CharField(
        verbose_name='sender full name', max_length=255, null=True, blank=True, unique=False)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    sender_voter_email = models.EmailField(
        verbose_name='sender email address', max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient", max_length=255, null=True, blank=True, unique=False)
    recipient_email_we_vote_id = models.CharField(
        verbose_name="we vote id for the email", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_email = models.EmailField(
        verbose_name='recipient email address', max_length=255, null=True, blank=True, unique=False)
    list_unsubscribe_mailto = models.TextField(null=True, blank=True)
    list_unsubscribe_url = models.TextField(null=True, blank=True)
    send_status = models.CharField(max_length=50, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)
    email_outbound_description_id = models.PositiveIntegerField(
        verbose_name="the internal id of EmailOutboundDescription", default=0, null=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class EmailManager(models.Manager):

    def __unicode__(self):
        return "EmailManager"

    def clear_secret_key_from_email_address(self, email_secret_key):
        """

        :param email_secret_key:
        :return:
        """
        email_address_found = False
        email_address = None
        status = ''

        try:
            if positive_value_exists(email_secret_key):
                email_address = EmailAddress.objects.get(
                    secret_key=email_secret_key,
                )
                email_address_found = True
                success = True
            else:
                email_address_found = False
                success = False
                status += "SECRET_KEY_MISSING "
        except EmailAddress.DoesNotExist:
            success = True
            status += "EMAIL_ADDRESS_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'ERROR_EMAIL_ADDRESS_DB_RETRIEVE_ERROR: ' + str(e) + ' '
            print(status)

        if email_address_found:
            try:
                email_address.secret_key = None
                email_address.save()
            except Exception as e:
                success = False
                status += 'ERROR_EMAIL_ADDRESS_DB_SAVE_ERROR: ' + str(e) + ' '
                print(status)

        results = {
            'success':                      success,
            'status':                       status,
        }
        return results

    def create_email_address_for_voter(self, normalized_email_address, voter, email_ownership_is_verified=False):
        return self.create_email_address(normalized_email_address, voter.we_vote_id, email_ownership_is_verified)

    def create_email_address(
            self,
            normalized_email_address='',
            voter_we_vote_id='',
            email_ownership_is_verified=False,
            make_primary_email=True):
        secret_key = generate_random_string(12)
        status = ""
        normalized_email_address = str(normalized_email_address)
        normalized_email_address = normalized_email_address.strip()
        normalized_email_address = normalized_email_address.lower()

        if not positive_value_exists(normalized_email_address):
            email_address_object = EmailAddress()
            results = {
                'status':                       "EMAIL_ADDRESS_FOR_VOTER_MISSING_RAW_EMAIL ",
                'success':                      False,
                'email_address_object_saved':   False,
                'email_address_object':         email_address_object,
            }
            return results

        try:
            email_address_object = EmailAddress.objects.create(
                normalized_email_address=normalized_email_address,
                voter_we_vote_id=voter_we_vote_id,
                email_ownership_is_verified=email_ownership_is_verified,
                secret_key=secret_key,
            )
            email_address_object_saved = True
            success = True
            status += "EMAIL_ADDRESS_FOR_VOTER_CREATED "
        except Exception as e:
            email_address_object_saved = False
            email_address_object = EmailAddress()
            success = False
            status += "ERROR_EMAIL_ADDRESS_FOR_VOTER_NOT_CREATED: " + str(e) + ' '
            print(status)

        results = {
            'success':                    success,
            'status':                     status,
            'email_address_object_saved': email_address_object_saved,
            'email_address_object':       email_address_object,
        }
        return results

    def create_email_outbound_description(
            self,
            sender_voter_we_vote_id='',
            sender_voter_email='',
            sender_voter_name='',
            recipient_voter_we_vote_id='',
            recipient_email_we_vote_id='',
            recipient_voter_email='',
            template_variables_in_json='',
            kind_of_email_template='',
            list_unsubscribe_mailto=None,
            list_unsubscribe_url=None,
    ):
        status = ""
        if not positive_value_exists(kind_of_email_template):
            kind_of_email_template = GENERIC_EMAIL_TEMPLATE

        try:
            email_outbound_description = EmailOutboundDescription.objects.create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                sender_voter_email=sender_voter_email,
                sender_voter_name=sender_voter_name,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                recipient_email_we_vote_id=recipient_email_we_vote_id,
                recipient_voter_email=recipient_voter_email,
                kind_of_email_template=kind_of_email_template,
                template_variables_in_json=template_variables_in_json,
                list_unsubscribe_mailto=list_unsubscribe_mailto,
                list_unsubscribe_url=list_unsubscribe_url,
            )
            email_outbound_description_saved = True
            success = True
            status += "EMAIL_OUTBOUND_DESCRIPTION_CREATED "
        except Exception as e:
            email_outbound_description_saved = False
            email_outbound_description = EmailOutboundDescription()
            success = False
            status += "ERROR_EMAIL_OUTBOUND_DESCRIPTION_NOT_CREATED: " + str(e) + " "
            print(status)

        results = {
            'success':                          success,
            'status':                           status,
            'email_outbound_description_saved': email_outbound_description_saved,
            'email_outbound_description':       email_outbound_description,
        }
        return results

    def find_and_merge_all_duplicate_emails(self, voter_we_vote_id):
        success = True
        status = ''
        already_merged_email_we_vote_ids = []

        list_results = self.retrieve_voter_email_address_list(voter_we_vote_id)
        if list_results['email_address_list_found']:
            initial_email_address_list = list_results['email_address_list']
            for email_address_object in initial_email_address_list:
                for comparison_email_address_object in initial_email_address_list:
                    if comparison_email_address_object.we_vote_id in already_merged_email_we_vote_ids:
                        # If this email has already been merged, skip forward
                        continue
                    if email_address_object.normalized_email_address != \
                            comparison_email_address_object.normalized_email_address:
                        # If we are looking at different email addresses, skip forward
                        continue
                    if email_address_object.we_vote_id == comparison_email_address_object.we_vote_id:
                        # If we are looking at the same email entry, skip forward
                        continue
                    # Merge verified email addresses where both are verified
                    if email_address_object.email_ownership_is_verified \
                            and comparison_email_address_object.email_ownership_is_verified:
                        friend_results = update_friend_invitation_email_link_with_new_email(
                            comparison_email_address_object.we_vote_id, email_address_object.we_vote_id)
                        if not friend_results['success']:
                            status += friend_results['status']
                        merge_results = self.merge_two_duplicate_emails(
                            email_address_object, comparison_email_address_object)
                        status += merge_results['status']
                        already_merged_email_we_vote_ids.append(email_address_object.we_vote_id)
                        already_merged_email_we_vote_ids.append(comparison_email_address_object.we_vote_id)
                    # Merge verified email addresses where both are not verified
                    elif not email_address_object.email_ownership_is_verified \
                            and not comparison_email_address_object.email_ownership_is_verified:
                        friend_results = update_friend_invitation_email_link_with_new_email(
                            comparison_email_address_object.we_vote_id, email_address_object.we_vote_id)
                        if not friend_results['success']:
                            status += friend_results['status']
                        merge_results = self.merge_two_duplicate_emails(
                            email_address_object, comparison_email_address_object)
                        status += merge_results['status']
                        already_merged_email_we_vote_ids.append(email_address_object.we_vote_id)
                        already_merged_email_we_vote_ids.append(comparison_email_address_object.we_vote_id)

        # Now look for the same emails where one is verified and the other isn't
        list_results2 = self.retrieve_voter_email_address_list(voter_we_vote_id)
        if list_results2['email_address_list_found']:
            initial_email_address_list = list_results2['email_address_list']
            for email_address_object in initial_email_address_list:
                for comparison_email_address_object in initial_email_address_list:
                    if comparison_email_address_object.we_vote_id in already_merged_email_we_vote_ids:
                        # If this email has already been merged, skip forward
                        continue
                    if email_address_object.normalized_email_address != \
                            comparison_email_address_object.normalized_email_address:
                        # If we are looking at different email addresses, skip forward
                        continue
                    if email_address_object.we_vote_id == comparison_email_address_object.we_vote_id:
                        # If we are looking at the same email entry, skip forward
                        continue
                    # If here, the normalized_email_addresses match
                    if email_address_object.email_ownership_is_verified:
                        # Delete the comparison_email_address
                        try:
                            friend_results = update_friend_invitation_email_link_with_new_email(
                                comparison_email_address_object.we_vote_id, email_address_object.we_vote_id)
                            if not friend_results['success']:
                                status += friend_results['status']
                            already_merged_email_we_vote_ids.append(email_address_object.we_vote_id)
                            already_merged_email_we_vote_ids.append(comparison_email_address_object.we_vote_id)
                            comparison_email_address_object.delete()
                        except Exception as e:
                            status += "ERROR_COULD_NOT_DELETE_UNVERIFIED_EMAIL: " + str(e) + " "
                            print(status)
        results = {
            'success': success,
            'status': status,
        }
        return results

    def merge_two_duplicate_emails(self, email_address_object1, email_address_object2):
        """
        We assume that the checking to see if these are duplicates has been done outside this function.
        We will keep email_address_object1 and eliminate email_address_object2.
        :param email_address_object1:
        :param email_address_object2:
        :return:
        """
        success = True
        status = ''

        try:
            test_we_vote_id = email_address_object1.we_vote_id
            test_we_vote_id = email_address_object2.we_vote_id
        except Exception as e:
            status += 'ERROR_PROBLEM_WITH_EMAIL1_OR_EMAIL2: ' + str(e) + ' '
            print(status)
            success = False
            results = {
                'success': success,
                'status': status,
            }
            return results

        if email_address_object1.voter_we_vote_id != email_address_object2.voter_we_vote_id:
            status += 'ONLY_MERGE_EMAILS_FROM_SAME_VOTER '
            success = False
            results = {
                'success': success,
                'status': status,
            }
            return results

        if email_address_object1.normalized_email_address != email_address_object2.normalized_email_address:
            status += 'ONLY_MERGE_EMAILS_WITH_SAME_NORMALIZED_EMAIL_ADDRESS '
            success = False
            results = {
                'success': success,
                'status': status,
            }
            return results

        at_least_one_is_verified = email_address_object1.email_ownership_is_verified \
            or email_address_object2.email_ownership_is_verified
        both_are_bouncing = email_address_object1.email_permanent_bounce \
            and email_address_object2.email_permanent_bounce

        try:
            email_address_object1.email_ownership_is_verified = at_least_one_is_verified
            email_address_object1.email_permanent_bounce = both_are_bouncing
            email_address_object1.save()
        except Exception as e:
            status += "ERROR_COULD_NOT_SAVE_EMAIL1: " + str(e) + " "
            print(status)

        # We don't need to handle repairing the primary email link here
        # because it is done in heal_primary_email_data_for_voter

        # Are there any scheduled emails for email_address_object2 waiting to send?

        try:
            email_address_object2.delete()
        except Exception as e:
            status += "ERROR_COULD_NOT_DELETE_EMAIL2: " + str(e) + " "
            print(status)
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    def parse_raw_emails_into_list(self, email_addresses_raw):
        success = True
        status = "EMAIL_MANAGER_PARSE_RAW_EMAILS"
        email_list = extract_email_addresses_from_string(email_addresses_raw)
        at_least_one_email_found = email_list and len(email_list) > 0

        results = {
            'success':                  success,
            'status':                   status,
            'at_least_one_email_found': at_least_one_email_found,
            'email_list':               email_list,
        }
        return results

    def retrieve_email_address_object(
            self,
            normalized_email_address='',
            email_address_object_we_vote_id='',
            voter_we_vote_id=''):
        """
        There are cases where we store multiple entries for the same normalized_email_address (prior to an email
        address being verified)
        :param normalized_email_address:
        :param email_address_object_we_vote_id:
        :param voter_we_vote_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        email_address_object_found = False
        email_address_object = EmailAddress()
        email_address_object_id = 0
        email_address_list_found = False
        email_address_list = []
        status = ""

        try:
            if positive_value_exists(email_address_object_we_vote_id):
                if positive_value_exists(voter_we_vote_id):
                    email_address_object = EmailAddress.objects.get(
                        we_vote_id__iexact=email_address_object_we_vote_id,
                        voter_we_vote_id__iexact=voter_we_vote_id,
                        deleted=False
                    )
                else:
                    email_address_object = EmailAddress.objects.get(
                        we_vote_id__iexact=email_address_object_we_vote_id,
                        deleted=False
                    )
                email_address_object_id = email_address_object.id
                email_address_object_we_vote_id = email_address_object.we_vote_id
                email_address_object_found = True
                success = True
                status += "RETRIEVE_EMAIL_ADDRESS_FOUND_BY_WE_VOTE_ID "
            elif positive_value_exists(normalized_email_address):
                email_address_queryset = EmailAddress.objects.all()
                if positive_value_exists(voter_we_vote_id):
                    email_address_queryset = email_address_queryset.filter(
                        normalized_email_address__iexact=normalized_email_address,
                        voter_we_vote_id__iexact=voter_we_vote_id,
                        deleted=False
                    )
                else:
                    email_address_queryset = email_address_queryset.filter(
                        normalized_email_address__iexact=normalized_email_address,
                        deleted=False
                    )
                # We need the email that has been verified email at top of list
                email_address_queryset = email_address_queryset.order_by('-email_ownership_is_verified')
                email_address_list = email_address_queryset

                if len(email_address_list):
                    if len(email_address_list) == 1:
                        # If only one email is found, return the results as a single email
                        email_address_object = email_address_list[0]
                        email_address_object_id = email_address_object.id
                        email_address_object_we_vote_id = email_address_object.we_vote_id
                        email_address_object_found = True
                        email_address_list_found = False
                        success = True
                        status += "RETRIEVE_EMAIL_ADDRESS_FOUND_BY_NORMALIZED_EMAIL_ADDRESS "
                    else:
                        success = True
                        email_address_list_found = True
                        status += 'RETRIEVE_EMAIL_ADDRESS_OBJECT-EMAIL_ADDRESS_LIST_RETRIEVED '
                else:
                    success = True
                    email_address_list_found = False
                    status += 'RETRIEVE_EMAIL_ADDRESS_OBJECT-NO_EMAIL_ADDRESS_LIST_RETRIEVED '
            else:
                email_address_object_found = False
                success = False
                status += "RETRIEVE_EMAIL_ADDRESS_VARIABLES_MISSING "
        except EmailAddress.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_EMAIL_ADDRESS_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'ERROR_FAILED retrieve_email_address_object EmailAddress: ' + str(e) + ' '
            print(status)

        results = {
            'success':                          success,
            'status':                           status,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'email_address_object_found':       email_address_object_found,
            'email_address_object_id':          email_address_object_id,
            'email_address_object_we_vote_id':  email_address_object_we_vote_id,
            'email_address_object':             email_address_object,
            'email_address_list_found':         email_address_list_found,
            'email_address_list':               email_address_list,
        }
        return results

    def retrieve_email_address_object_from_secret_key(self, email_secret_key='', subscription_secret_key=''):
        """
        :param email_secret_key:
        :param subscription_secret_key:
        :return:
        """
        email_address_object_found = False
        email_address_object = EmailAddress()
        email_address_object_id = 0
        email_address_object_we_vote_id = ""
        email_ownership_is_verified = False
        status = ''

        try:
            if positive_value_exists(email_secret_key) or positive_value_exists(subscription_secret_key):
                if positive_value_exists(email_secret_key):
                    email_address_object = EmailAddress.objects.get(
                        secret_key=email_secret_key,
                        deleted=False
                    )
                elif positive_value_exists(subscription_secret_key):
                    email_address_object = EmailAddress.objects.get(
                        subscription_secret_key=subscription_secret_key,
                        deleted=False
                    )
                email_address_object_id = email_address_object.id
                email_address_object_we_vote_id = email_address_object.we_vote_id
                email_ownership_is_verified = email_address_object.email_ownership_is_verified
                email_address_object_found = True
                success = True
                status += "RETRIEVE_EMAIL_ADDRESS_FOUND_BY_SECRET_KEY "
            else:
                email_address_object_found = False
                success = False
                status += "RETRIEVE_EMAIL_ADDRESS_BY_SECRET_KEY_VARIABLE_MISSING "
        except EmailAddress.DoesNotExist:
            success = True
            status += "RETRIEVE_EMAIL_ADDRESS_BY_SECRET_KEY_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'ERROR_FAILED retrieve_email_address_object_from_secret_key EmailAddress: ' + str(e) + ' '
            print(status)

        results = {
            'success':                          success,
            'status':                           status,
            'email_address_object_found':       email_address_object_found,
            'email_address_object_id':          email_address_object_id,
            'email_address_object_we_vote_id':  email_address_object_we_vote_id,
            'email_address_object':             email_address_object,
            'email_ownership_is_verified':      email_ownership_is_verified,
        }
        return results

    def verify_email_address_object_from_secret_key(self, email_secret_key=''):
        """

        :param email_secret_key:
        :return:
        """
        email_address_object_found = False
        email_address_object = EmailAddress()
        email_address_object_id = 0
        email_address_object_we_vote_id = ""
        status = ''

        try:
            if positive_value_exists(email_secret_key):
                email_address_object = EmailAddress.objects.get(
                    secret_key=email_secret_key,
                    deleted=False
                )
                email_address_object_id = email_address_object.id
                email_address_object_we_vote_id = email_address_object.we_vote_id
                email_address_object_found = True
                success = True
                status += "VERIFY_EMAIL_ADDRESS_FOUND_BY_WE_VOTE_ID "
            else:
                email_address_object_found = False
                success = False
                status += "VERIFY_EMAIL_ADDRESS_VARIABLES_MISSING "
        except EmailAddress.DoesNotExist:
            success = True
            status += "VERIFY_EMAIL_ADDRESS_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'ERROR_FAILED verify_email_address_object_from_secret_key EmailAddress: ' + str(e) + ' '
            print(status)

        email_ownership_is_verified = False
        if email_address_object_found:
            try:
                # Note that we leave the secret key in place so we can find the owner we_vote_id in a subsequent call
                email_address_object.email_ownership_is_verified = True
                email_address_object.save()
                email_ownership_is_verified = True
            except Exception as e:
                success = False
                status += 'ERROR_FAILED_TO_SAVE_EMAIL_OWNERSHIP_IS_VERIFIED: ' + str(e) + " "
                print(status)
        else:
            status += 'EMAIL_ADDRESS_OBJECT_NOT_FOUND '

        results = {
            'success':                          success,
            'status':                           status,
            'email_address_object_found':       email_address_object_found,
            'email_address_object_id':          email_address_object_id,
            'email_address_object_we_vote_id':  email_address_object_we_vote_id,
            'email_address_object':             email_address_object,
            'email_ownership_is_verified':      email_ownership_is_verified,
        }
        return results

    def retrieve_voter_email_address_list(self, voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        status = ""
        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                  success,
                'status':                   status,
                'voter_we_vote_id':         voter_we_vote_id,
                'email_address_list_found': False,
                'email_address_list':       [],
            }
            return results

        email_address_list = []
        try:
            email_address_queryset = EmailAddress.objects.all()
            email_address_queryset = email_address_queryset.filter(
                voter_we_vote_id__iexact=voter_we_vote_id,
                deleted=False
            )
            email_address_queryset = email_address_queryset.order_by('-id')  # Put most recent email at top of list
            email_address_list = email_address_queryset

            if len(email_address_list):
                success = True
                email_address_list_found = True
                status += 'EMAIL_ADDRESS_LIST_RETRIEVED '
            else:
                success = True
                email_address_list_found = False
                status += 'NO_EMAIL_ADDRESS_LIST_RETRIEVED '
        except EmailAddress.DoesNotExist:
            # No data found. Not a problem.
            success = True
            email_address_list_found = False
            status += 'NO_EMAIL_ADDRESS_LIST_RETRIEVED_DoesNotExist '
            email_address_list = []
        except Exception as e:
            success = False
            email_address_list_found = False
            status += 'ERROR_FAILED retrieve_voter_email_address_list EmailAddress: ' + str(e) + ' '
            print(status)

        results = {
            'success': success,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
            'email_address_list_found': email_address_list_found,
            'email_address_list': email_address_list,
        }
        return results

    def retrieve_primary_email_with_ownership_verified(self, voter_we_vote_id='', normalized_email_address=''):
        status = ""
        email_address_list = []
        email_address_list_found = False
        email_address_object = EmailAddress()
        email_address_object_found = False
        try:
            if positive_value_exists(voter_we_vote_id):
                email_address_queryset = EmailAddress.objects.all()
                email_address_queryset = email_address_queryset.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    email_ownership_is_verified=True,
                    deleted=False
                )
                email_address_queryset = email_address_queryset.order_by('-id')  # Put most recent email at top of list
                email_address_list = email_address_queryset
            elif positive_value_exists(normalized_email_address):
                email_address_queryset = EmailAddress.objects.all()
                email_address_queryset = email_address_queryset.filter(
                    normalized_email_address__iexact=normalized_email_address,
                    email_ownership_is_verified=True,
                    deleted=False
                )
                email_address_queryset = email_address_queryset.order_by('-id')  # Put most recent email at top of list
                email_address_list = email_address_queryset
            else:
                email_address_list = []
            if len(email_address_list):
                success = True
                email_address_list_found = True
                status += 'RETRIEVE_PRIMARY_EMAIL_ADDRESS_OBJECT-EMAIL_ADDRESS_LIST_RETRIEVED '
            else:
                success = True
                email_address_list_found = False
                status += 'RETRIEVE_PRIMARY_EMAIL_ADDRESS_OBJECT-NO_EMAIL_ADDRESS_LIST_RETRIEVED '
        except EmailAddress.DoesNotExist:
            success = True
            status += "RETRIEVE_PRIMARY_EMAIL_ADDRESS_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'ERROR_FAILED retrieve_primary_email_with_ownership_verified EmailAddress: ' + str(e) + " "
            print(status)

        if email_address_list_found:
            email_address_object_found = True
            email_address_object = email_address_list[0]

        results = {
            'success':                          success,
            'status':                           status,
            'email_address_object_found':       email_address_object_found,
            'email_address_object':             email_address_object,
        }
        return results

    def fetch_primary_email_with_ownership_verified(self, voter_we_vote_id):
        results = self.retrieve_primary_email_with_ownership_verified(voter_we_vote_id)
        if results['email_address_object_found']:
            email_address_object = results['email_address_object']
            return email_address_object.normalized_email_address

        return ""

    def fetch_simple_voter_email_address_list(self, voter_we_vote_id):
        simple_email_address_list = []
        results = self.retrieve_voter_email_address_list(voter_we_vote_id=voter_we_vote_id)
        if results['email_address_list_found']:
            email_address_list = results['email_address_list']
            for email_object in email_address_list:
                # We don't care if the email is confirmed or not -- if the voter thinks the email is there own,
                #  don't show it in the contacts list
                if positive_value_exists(email_object.normalized_email_address) and \
                        email_object.normalized_email_address not in simple_email_address_list:
                    simple_email_address_list.append(email_object.normalized_email_address)

        return simple_email_address_list

    def retrieve_scheduled_email_list_from_send_status(self, sender_voter_we_vote_id, send_status):
        status = ""
        scheduled_email_list = []
        try:
            email_scheduled_queryset = EmailScheduled.objects.all()
            email_scheduled_queryset = email_scheduled_queryset.filter(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                send_status=send_status,
            )
            scheduled_email_list = email_scheduled_queryset

            if len(scheduled_email_list):
                success = True
                scheduled_email_list_found = True
                status += 'SCHEDULED_EMAIL_LIST_RETRIEVED '
            else:
                success = True
                scheduled_email_list_found = False
                status += 'NO_SCHEDULED_EMAIL_LIST_RETRIEVED '
        except EmailScheduled.DoesNotExist:
            # No data found. Not a problem.
            success = True
            scheduled_email_list_found = False
            status += 'NO_SCHEDULED_EMAIL_LIST_RETRIEVED_DoesNotExist '
            scheduled_email_list = []
        except Exception as e:
            success = False
            scheduled_email_list_found = False
            status += 'FAILED retrieve_scheduled_email_list_from_send_status EmailAddress: ' + str(e) + " "
            print(status)

        results = {
            'success':                      success,
            'status':                       status,
            'scheduled_email_list_found':   scheduled_email_list_found,
            'scheduled_email_list':         scheduled_email_list,
        }
        return results

    def update_scheduled_email_with_new_send_status(self, email_scheduled_object, send_status):
        try:
            email_scheduled_object.send_status = send_status
            email_scheduled_object.save()
            return email_scheduled_object
        except Exception as e:
            status = "ERROR_UPDATE_SCHEDULED_EMAIL_WITH_NEW_SEND_STATUS:" + str(e) + ' '
            print(status)
            return email_scheduled_object

    def schedule_email(
            self,
            email_outbound_description=None,
            subject="",
            message_text="",
            message_html="",
            send_status=TO_BE_PROCESSED):
        status = ''
        try:
            email_scheduled = EmailScheduled.objects.create(
                sender_voter_name=email_outbound_description.sender_voter_name,
                sender_voter_we_vote_id=email_outbound_description.sender_voter_we_vote_id,
                sender_voter_email=email_outbound_description.sender_voter_email,
                recipient_voter_we_vote_id=email_outbound_description.recipient_voter_we_vote_id,
                recipient_email_we_vote_id=email_outbound_description.recipient_email_we_vote_id,
                recipient_voter_email=email_outbound_description.recipient_voter_email,
                message_html=message_html,
                message_text=message_text,
                email_outbound_description_id=email_outbound_description.id,
                send_status=send_status,
                subject=subject,
                list_unsubscribe_mailto=email_outbound_description.list_unsubscribe_mailto,
                list_unsubscribe_url=email_outbound_description.list_unsubscribe_url,
            )
            email_scheduled_saved = True
            email_scheduled_id = email_scheduled.id
            success = True
            status += "SCHEDULE_EMAIL_CREATED "
        except Exception as e:
            email_scheduled_saved = False
            email_scheduled = EmailScheduled()
            email_scheduled_id = 0
            success = False
            status += "ERROR_SCHEDULE_EMAIL_NOT_CREATED: " + str(e) + ' '
            print(status)

        results = {
            'success':                  success,
            'status':                   status,
            'email_scheduled_saved':    email_scheduled_saved,
            'email_scheduled_id':       email_scheduled_id,
            'email_scheduled':          email_scheduled,
        }
        return results

    def send_scheduled_email(self, email_scheduled):
        success = True
        status = ""

        # DALE 2016-11-3 sender_voter_email is no longer required, because we use a system email
        # if not positive_value_exists(email_scheduled.sender_voter_email):
        #     status += "MISSING_SENDER_VOTER_EMAIL"
        #     success = False

        if not positive_value_exists(email_scheduled.recipient_voter_email):
            status += "MISSING_EMAIL_SCHEDULED_RECIPIENT_VOTER_EMAIL "
            success = False

        if not positive_value_exists(email_scheduled.subject):
            status += "MISSING_EMAIL_SUBJECT "
            success = False

        # We need either plain text or HTML message
        if not positive_value_exists(email_scheduled.message_text) and \
                not positive_value_exists(email_scheduled.message_html):
            status += "MISSING_EMAIL_MESSAGE "
            success = False

        if success:
            send_via_sendgrid = True
            if send_via_sendgrid:
                return self.send_scheduled_email_via_sendgrid(email_scheduled)
            else:
                return self.send_scheduled_email_via_smtp(email_scheduled)
        else:
            status += "ERROR_DID_NOT_SEND: ["
            try:
                status += 'subject:' + str(email_scheduled.subject) + ' '
                status += 'email_scheduled.id:' + str(email_scheduled.id)
            except Exception as e:
                pass
            status += "] "
            email_scheduled_sent = False
            results = {
                'success': success,
                'status': status,
                'email_scheduled_sent': email_scheduled_sent,
            }
            return results

    def send_scheduled_email_via_sendgrid(self, email_scheduled):
        """
        Send a single scheduled email
        :param email_scheduled:
        :return:
        """
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Content, From, Header, Mail, MimeType, Subject, To, ReplyTo
        status = ""
        success = True
        email_scheduled_sent = False
        sendgrid_turned_off_for_testing = False
        if sendgrid_turned_off_for_testing:
            status += "ERROR_SENDGRID_TURNED_OFF_FOR_TESTING "
            print(status)
            results = {
                'success':                  success,
                'status':                   status,
                'email_scheduled_sent':     False,
            }
            return results

        try:
            message = Mail()
            if positive_value_exists(email_scheduled.sender_voter_name):
                message.from_email = From(
                    'info@wevote.us',
                    "{sender_voter_name} via We Vote".format(sender_voter_name=email_scheduled.sender_voter_name))
            else:
                message.from_email = From('info@wevote.us', 'We Vote')
            message.reply_to = ReplyTo('info@wevote.us', 'We Vote')
            message.to = To(email_scheduled.recipient_voter_email, email_scheduled.recipient_voter_email, p=0)
            try:
                if email_scheduled.list_unsubscribe_mailto or email_scheduled.list_unsubscribe_url:
                    list_unsubscribe_text = ''
                    if email_scheduled.list_unsubscribe_mailto:
                        list_unsubscribe_text += \
                            "<mailto:{list_unsubscribe_mailto}>" \
                            "".format(list_unsubscribe_mailto=email_scheduled.list_unsubscribe_mailto)
                        if email_scheduled.list_unsubscribe_url:
                            list_unsubscribe_text += ", "
                    if email_scheduled.list_unsubscribe_url:
                        list_unsubscribe_text += \
                            "<{list_unsubscribe_url}>" \
                            "".format(list_unsubscribe_url=email_scheduled.list_unsubscribe_url)
                    message.add_header(
                        Header(key="List-Unsubscribe", value=list_unsubscribe_text)
                    )
                    if email_scheduled.list_unsubscribe_url:
                        message.add_header(
                            Header(key="List-Unsubscribe-Post", value="List-Unsubscribe=One-Click")
                        )
            except Exception as e:
                status += "SEND_SCHEDULED_ADD_HEADER_ERROR: " + str(e) + " "
                print(status)
            message.subject = Subject(email_scheduled.subject)
            message.content = Content(
                MimeType.text,
                email_scheduled.message_text)
            message.content = Content(
                MimeType.html,
                email_scheduled.message_html)
            try:
                sendgrid_client = SendGridAPIClient(SENDGRID_API_KEY)
                response = sendgrid_client.send(message)
                # print(response.status_code)
                # print(response.body)
                # print(response.headers)
                status += "SENDING_VIA_SENDGRID "
                email_scheduled_sent = True
            except Exception as e:
                status += "ERROR_COULD_NOT_SEND_VIA_SENDGRID: " + str(e) + ' '
                print(status)
                email_scheduled_sent = False
        except Exception as e:
            status += "ERROR_COULD_NOT_BE_PREPARED_FOR_SENDGRID: " + str(e) + ' '
            print(status)

        results = {
            'success':                  success,
            'status':                   status,
            'email_scheduled_sent':     email_scheduled_sent,
        }
        return results

    def send_scheduled_email_via_smtp(self, email_scheduled):
        """
        Send a single scheduled email but using the SMTP settings in environment_variables
        :param email_scheduled:
        :return:
        """
        status = ""
        success = True
        email_scheduled_sent = False
        smtp_turned_off_for_testing = False
        if smtp_turned_off_for_testing:
            status += "ERROR_SMTP_TURNED_OFF_FOR_TESTING "
            print(status)
            results = {
                'success':                  success,
                'status':                   status,
                'email_scheduled_sent':     False,
            }
            return results

        try:
            # Prepare headers_dict
            headers_dict = {}
            try:
                if email_scheduled.list_unsubscribe_mailto or email_scheduled.list_unsubscribe_url:
                    list_unsubscribe_text = ''
                    if email_scheduled.list_unsubscribe_mailto:
                        list_unsubscribe_text += \
                            "<mailto:{list_unsubscribe_mailto}>" \
                            "".format(list_unsubscribe_mailto=email_scheduled.list_unsubscribe_mailto)
                        if email_scheduled.list_unsubscribe_url:
                            list_unsubscribe_text += ", "
                    if email_scheduled.list_unsubscribe_url:
                        list_unsubscribe_text += \
                            "<{list_unsubscribe_url}>" \
                            "".format(list_unsubscribe_url=email_scheduled.list_unsubscribe_url)
                    headers_dict["List-Unsubscribe"] = list_unsubscribe_text
                    if email_scheduled.list_unsubscribe_url:
                        headers_dict["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
            except Exception as e:
                status += "SEND_SCHEDULED_ADD_HEADER_ERROR: " + str(e) + " "
                print(status)
            if positive_value_exists(email_scheduled.sender_voter_name):
                from_email = "{sender_voter_name} via We Vote <email_address>" \
                             "".format(email_address='info@wevote.us',
                                       sender_voter_name=email_scheduled.sender_voter_name)
            else:
                from_email = "We Vote <email_address>" \
                             "".format(email_address='info@wevote.us')
            # For some reason the default Emailbackend doesn't have access to environment_variables.json directly
            connection = get_connection(
                username=EMAIL_HOST_USER,
                password=EMAIL_HOST_PASSWORD,
                host=EMAIL_HOST,
                port=EMAIL_PORT)
            connection.open()
            message = EmailMultiAlternatives(
                subject=email_scheduled.subject,
                body=email_scheduled.message_text,
                from_email=from_email,
                to=[email_scheduled.recipient_voter_email],
                connection=connection,
                reply_to=['We Vote <info@wevote.us>'],
                headers=headers_dict,
            )
            message.attach_alternative(email_scheduled.message_html, "text/html")

            try:
                message.send(fail_silently=False)
                connection.close()
                status += "SENDING_VIA_SMTP "
                email_scheduled_sent = True
            except Exception as e:
                status += "ERROR_COULD_NOT_SEND_VIA_SMTP: " + str(e) + ' '
                print(status)
                email_scheduled_sent = False
        except Exception as e:
            status += "ERROR_COULD_NOT_BE_PREPARED_FOR_SMTP: " + str(e) + ' '
            print(status)

        results = {
            'success':                  success,
            'status':                   status,
            'email_scheduled_sent':     email_scheduled_sent,
        }
        return results

    def send_scheduled_email_list(self, messages_to_send):
        """
        Take in a list of scheduled_email_id's, and send them
        :param messages_to_send:
        :return:
        """
        success = False
        status = ""

        results = {
            'success':                  success,
            'status':                   status,
            'at_least_one_email_found': True,
        }
        return results

    def send_scheduled_emails_waiting_for_verification(self, sender_we_vote_id, sender_name=''):
        """
        Searched the scheduled email for the text "Your   friend" (with three spaces) and replace with sender_name
        :param sender_we_vote_id:
        :param sender_name:
        :return:
        """
        at_least_one_email_found = False
        save_scheduled_email = False
        send_status = WAITING_FOR_VERIFICATION
        success = True
        status = ""
        scheduled_email_results = self.retrieve_scheduled_email_list_from_send_status(
            sender_we_vote_id, send_status)
        status += scheduled_email_results['status']
        if scheduled_email_results['scheduled_email_list_found']:
            scheduled_email_list = scheduled_email_results['scheduled_email_list']
            for scheduled_email in scheduled_email_list:
                at_least_one_email_found = True
                if positive_value_exists(sender_name):
                    # Check scheduled_email.message_text and scheduled_email.message_html
                    # if there is a variable that hasn't been filled in yet.
                    try:
                        if scheduled_email.message_text:
                            save_scheduled_email = True
                            scheduled_email.message_text = \
                                scheduled_email.message_text.replace('Your   friend', sender_name)
                    except Exception as e:
                        status += "COULD_NOT_REPLACE_NAME_IN_MESSAGE_TEXT: " + str(e) + " "
                    try:
                        if scheduled_email.message_html:
                            save_scheduled_email = True
                            scheduled_email.message_html = \
                                scheduled_email.message_html.replace('Your   friend', sender_name)
                    except Exception as e:
                        status += "COULD_NOT_REPLACE_NAME_IN_HTML: " + str(e) + " "
                    if save_scheduled_email:
                        try:
                            scheduled_email.save()
                            status += "SCHEDULED_EMAIL_SAVED "
                        except Exception as e:
                            status += "ERROR_COULD_NOT_SAVE_SCHEDULED_EMAIL: " + str(e) + " "
                            print(status)
                send_results = self.send_scheduled_email(scheduled_email)
                email_scheduled_sent = send_results['email_scheduled_sent']
                status += send_results['status']
                if email_scheduled_sent:
                    # If scheduled email sent successfully change their status from WAITING_FOR_VERIFICATION to SENT
                    send_status = SENT
                    try:
                        scheduled_email.send_status = send_status
                        scheduled_email.save()
                    except Exception as e:
                        status += "ERROR_FAILED_TO_UPDATE_SEND_STATUS: " + str(e) + ' '
                        print(status)
        results = {
            'success':                  success,
            'status':                   status,
            'at_least_one_email_found': at_least_one_email_found,
        }
        return results

    def update_email_address_with_new_secret_key(self, email_we_vote_id):
        results = self.retrieve_email_address_object('', email_we_vote_id)
        if results['email_address_object_found']:
            email_address_object = results['email_address_object']
            try:
                email_address_object.secret_key = generate_random_string(12)
                email_address_object.save()
                return email_address_object.secret_key
            except Exception as e:
                status = "ERROR_UPDATE_EMAIL_ADDRESS_WITH_NEW_SECRET_KEY: " + str(e) + " "
                print(status)
                return ""
        else:
            return ""

    def update_email_address_with_new_subscription_secret_key(self, email_we_vote_id='', force_change=False):
        """
        The subscription_secret_key is used to let the voter unsubscribe without being signed in,
        so it shouldn't change.
        :param email_we_vote_id:
        :param force_change:
        :return:
        """
        results = self.retrieve_email_address_object('', email_we_vote_id)
        if results['email_address_object_found']:
            email_address_object = results['email_address_object']
            if not positive_value_exists(email_address_object.subscription_secret_key) or force_change:
                try:
                    email_address_object.subscription_secret_key = generate_random_string(48)
                    email_address_object.save()
                    return email_address_object.subscription_secret_key
                except Exception as e:
                    status = "ERROR_UPDATE_EMAIL_ADDRESS_WITH_NEW_SUBSCRIPTION_SECRET_KEY: " + str(e) + " "
                    print(status)
                    return ""
            else:
                return email_address_object.subscription_secret_key
        else:
            return ""

    def update_email_address_object_as_verified(self, email_address_object):
        try:
            email_address_object.email_ownership_is_verified = True
            email_address_object.save()
            return email_address_object
        except Exception as e:
            status = "ERROR_UPDATE_EMAIL_ADDRESS_AS_VERIFIED: " + str(e) + " "
            print(status)
            return email_address_object


def update_friend_invitation_email_link_with_new_email(deleted_email_we_vote_id, updated_email_we_vote_id):
    success = True
    status = ""
    try:
        FriendInvitationEmailLink = apps.get_model('friend', 'FriendInvitationEmailLink')

        try:
            FriendInvitationEmailLink.objects.filter(recipient_email_we_vote_id=deleted_email_we_vote_id).\
                update(recipient_email_we_vote_id=updated_email_we_vote_id)
        except Exception as e:
            status += "ERROR_FAILED_TO_UPDATE-FriendInvitationEmailLink: " + str(e) + ' '
            print(status)

    except Exception as e:
        status += "ERROR_FAILED_TO_LOAD-FriendInvitationEmailLink: " + str(e) + ' '
        print(status)
    results = {
        'success':              success,
        'status':               status,
    }
    return results


class SendGridApiCounter(models.Model):
    datetime_of_action = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)
    kind_of_action = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    number_of_items_sent_in_query = models.PositiveIntegerField(null=True, db_index=True)


class SendGridApiCounterDailySummary(models.Model):
    date_of_action = models.DateField(verbose_name='date of action', null=False, auto_now=False)
    kind_of_action = models.CharField(verbose_name="kind of call", max_length=50, null=True, blank=True)


class SendGridApiCounterWeeklySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    week_of_action = models.SmallIntegerField(verbose_name='number of the week', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call", max_length=50, null=True, blank=True)


class SendGridApiCounterMonthlySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    month_of_action = models.SmallIntegerField(verbose_name='number of the month', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call", max_length=50, null=True, blank=True)


# noinspection PyBroadException
class SendGridApiCounterManager(models.Manager):

    def create_counter_entry(self, kind_of_action, number_of_items_sent_in_query=0):
        """
        Create an entry that records that a call to the SendGrid Api was made.
        """
        try:
            number_of_items_sent_in_query = convert_to_int(number_of_items_sent_in_query)

            # TODO: We need to work out the timezone questions
            SendGridApiCounter.objects.create(
                kind_of_action=kind_of_action,
                number_of_items_sent_in_query=number_of_items_sent_in_query,
            )
            success = True
            status = 'ENTRY_SAVED'
        except Exception:
            success = False
            status = 'SOME_ERROR'

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def retrieve_daily_summaries(self, kind_of_action='', days_to_display=30):
        # Start with today and cycle backwards in time
        daily_summaries = []
        day_on_stage = date.today()  # TODO: We need to work out the timezone questions
        number_found = 0
        maximum_attempts = 365
        attempt_count = 0

        try:
            while number_found <= days_to_display and attempt_count <= maximum_attempts:
                attempt_count += 1
                counter_queryset = SendGridApiCounter.objects.all()
                if positive_value_exists(kind_of_action):
                    counter_queryset = counter_queryset.filter(kind_of_action=kind_of_action)

                # Find the number of these entries on that particular day
                counter_queryset = counter_queryset.filter(
                    datetime_of_action__year=day_on_stage.year,
                    datetime_of_action__month=day_on_stage.month,
                    datetime_of_action__day=day_on_stage.day)
                api_call_count = counter_queryset.count()

                # If any api calls were found on that date, pass it out for display
                if positive_value_exists(api_call_count):
                    daily_summary = {
                        'date_string': day_on_stage,
                        'count': api_call_count,
                    }
                    daily_summaries.append(daily_summary)
                    number_found += 1

                day_on_stage -= timedelta(days=1)
        except Exception:
            pass

        return daily_summaries
