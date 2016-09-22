# email_outbound/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_email_integer, fetch_site_unique_id_prefix

FRIEND_INVITATION = 'FRIEND_INVITATION'
GENERIC_EMAIL = 'GENERIC_EMAIL'
KIND_OF_EMAIL_TEMPLATE_CHOICES = (
    (GENERIC_EMAIL,  'Generic Email'),
    (FRIEND_INVITATION, 'Invite Friend'),
)

TO_BE_PROCESSED = 'TO_BE_PROCESSED'
BEING_ASSEMBLED = 'BEING_ASSEMBLED'
SCHEDULED = 'SCHEDULED'
ASSEMBLY_STATUS_CHOICES = (
    (TO_BE_PROCESSED,  'Email to be assembled'),
    (BEING_ASSEMBLED, 'Email being assembled with template'),
    (SCHEDULED, 'Sent to the scheduler'),
)

BEING_SENT = 'BEING_SENT'
SENT = 'SENT'
SEND_STATUS_CHOICES = (
    (TO_BE_PROCESSED,  'Message to be processed'),
    (BEING_SENT, 'Message being sent'),
    (SENT, 'Message sent'),
)


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
    normalized_email_address = models.EmailField(
        verbose_name='email address', max_length=255, null=False, blank=False, unique=True)
    secret_key = models.CharField(
        verbose_name="secret key to verify ownership of email", max_length=255, null=True, blank=True, unique=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_email_integer()
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
    kind_of_email_template = models.CharField(max_length=20, choices=KIND_OF_EMAIL_TEMPLATE_CHOICES,
                                              default=GENERIC_EMAIL)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    recipient_email_we_vote_id = models.CharField(
        verbose_name="email we vote id for recipient", max_length=255, null=True, blank=True, unique=False)
    # We include this here for data monitoring and debugging
    recipient_voter_email = models.EmailField(
        verbose_name='email address for recipient', max_length=255, null=True, blank=True, unique=False)
    invitation_message = models.TextField(null=True, blank=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class EmailScheduled(models.Model):
    """
    Used to tell the email server literally what to send. If an email bounces temporarily, we will
    want to trigger the EmailOutboundDescription to generate an new EmailScheduled entry.
    """
    subject = models.CharField(verbose_name="email subject", max_length=255, null=True, blank=True, unique=False)
    message_text = models.TextField(null=True, blank=True)
    message_html = models.TextField(null=True, blank=True)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient", max_length=255, null=True, blank=True, unique=False)
    recipient_email_we_vote_id = models.CharField(
        verbose_name="we vote id for the email", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_email = models.EmailField(
        verbose_name='email address', max_length=255, null=True, blank=True, unique=False)
    send_status = models.CharField(max_length=20, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)
    email_outbound_description_id = models.PositiveIntegerField(
        verbose_name="the internal id of EmailOutboundDescription", default=0, null=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class EmailManager(models.Model):
    def __unicode__(self):
        return "EmailManager"

    def create_email_address_for_voter(self, normalized_email_address, voter):
        return self.create_email_address(normalized_email_address, voter.we_vote_id)

    def create_email_address(self, normalized_email_address, voter_we_vote_id=''):
        secret_key = None
        normalized_email_address = str(normalized_email_address)
        normalized_email_address = normalized_email_address.strip()
        normalized_email_address = normalized_email_address.lower()

        if not positive_value_exists(normalized_email_address):
            email_address_object = EmailAddress()
            results = {
                'success':                      False,
                'status':                       "EMAIL_ADDRESS_FOR_VOTER_MISSING_RAW_EMAIL",
                'email_address_object_saved':   False,
                'email_address_object':         email_address_object,
            }
            return results

        try:
            email_address_object = EmailAddress.objects.create(
                normalized_email_address=normalized_email_address,
                voter_we_vote_id=voter_we_vote_id,
                secret_key=secret_key,
            )
            email_address_object_saved = True
            success = True
            status = "EMAIL_ADDRESS_FOR_VOTER_CREATED"
        except Exception as e:
            email_address_object_saved = False
            email_address_object = EmailAddress()
            success = False
            status = "EMAIL_ADDRESS_FOR_VOTER_NOT_CREATED"

        results = {
            'success':                    success,
            'status':                     status,
            'email_address_object_saved': email_address_object_saved,
            'email_address_object':       email_address_object,
        }
        return results

    def create_email_outbound_description(
            self, sender_voter_we_vote_id, recipient_voter_we_vote_id='',
            recipient_email_we_vote_id='', recipient_voter_email='', invitation_message='',
            kind_of_email_template=''):
        if not positive_value_exists(kind_of_email_template):
            kind_of_email_template = GENERIC_EMAIL

        try:
            email_outbound_description = EmailOutboundDescription.objects.create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                recipient_email_we_vote_id=recipient_email_we_vote_id,
                recipient_voter_email=recipient_voter_email,
                invitation_message=invitation_message,
                kind_of_email_template=kind_of_email_template,
            )
            email_outbound_description_saved = True
            success = True
            status = "EMAIL_OUTBOUND_DESCRIPTION_CREATED"
        except Exception as e:
            email_outbound_description_saved = False
            email_outbound_description = EmailOutboundDescription()
            success = False
            status = "EMAIL_OUTBOUND_DESCRIPTION_NOT_CREATED"

        results = {
            'success':                          success,
            'status':                           status,
            'email_outbound_description_saved': email_outbound_description_saved,
            'email_outbound_description':       email_outbound_description,
        }
        return results

    def parse_raw_emails_into_list(self, email_addresses_raw):
        success = True
        status = "EMAIL_MANAGER_PARSE_RAW_EMAILS-TEST_MODE"
        email_list = []
        email_list.append(email_addresses_raw)  # TODO DALE This is a hack for testing now. Needs to be implemented.

        results = {
            'success':                  success,
            'status':                   status,
            'at_least_one_email_found': True,
            'email_list':               email_list,
        }
        return results

    def retrieve_email_address_object(self, normalized_email_address, email_address_object_we_vote_id=''):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        email_address_object_found = False
        email_address_object = EmailAddress()
        email_address_object_id = 0

        try:
            if positive_value_exists(email_address_object_we_vote_id):
                email_address_object = EmailAddress.objects.get(
                    we_vote_id__iexact=email_address_object_we_vote_id)
                email_address_object_id = email_address_object.id
                email_address_object_we_vote_id = email_address_object.we_vote_id
                email_address_object_found = True
                success = True
                status = "RETRIEVE_EMAIL_ADDRESS_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(normalized_email_address):
                email_address_object = EmailAddress.objects.get(
                    normalized_email_address__iexact=normalized_email_address)
                email_address_object_id = email_address_object.id
                email_address_object_we_vote_id = email_address_object.we_vote_id
                email_address_object_found = True
                success = True
                status = "RETRIEVE_EMAIL_ADDRESS_FOUND_BY_RAW_EMAIL"
            else:
                email_address_object_found = False
                success = False
                status = "RETRIEVE_EMAIL_ADDRESS_VARIABLES_MISSING"
        except EmailAddress.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status = "RETRIEVE_EMAIL_ADDRESS_MULTIPLE_OBJECTS_RETURNED"
        except EmailAddress.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status = "RETRIEVE_EMAIL_ADDRESS_NOT_FOUND"

        results = {
            'success':                          success,
            'status':                           status,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'email_address_object_found':       email_address_object_found,
            'email_address_object_id':          email_address_object_id,
            'email_address_object_we_vote_id':  email_address_object_we_vote_id,
            'email_address_object':             email_address_object,
        }
        return results

    def schedule_email(self, email_outbound_description):
        sender_voter_we_vote_id = email_outbound_description.sender_voter_we_vote_id
        recipient_voter_we_vote_id = email_outbound_description.recipient_voter_we_vote_id
        recipient_email_we_vote_id = email_outbound_description.recipient_email_we_vote_id
        recipient_voter_email = email_outbound_description.recipient_voter_email
        invitation_message = email_outbound_description.invitation_message
        if positive_value_exists(email_outbound_description.kind_of_email_template):
            kind_of_email_template = email_outbound_description.kind_of_email_template
        else:
            kind_of_email_template = GENERIC_EMAIL

        # We need to combine the invitation_message with the kind_of_email_template
        subject = "TEST SUBJECT"
        message_html = ""
        message_text = "TEST TEXT: " + invitation_message

        send_status = TO_BE_PROCESSED

        try:
            email_scheduled = EmailScheduled.objects.create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                recipient_email_we_vote_id=recipient_email_we_vote_id,
                recipient_voter_email=recipient_voter_email,
                message_html=message_html,
                message_text=message_text,
                email_outbound_description_id=email_outbound_description.id,
                send_status=send_status,
                subject=subject,
            )
            email_scheduled_saved = True
            success = True
            status = "SCHEDULE_EMAIL_CREATED"
        except Exception as e:
            email_scheduled_saved = False
            email_scheduled = EmailScheduled()
            success = False
            status = "SCHEDULE_EMAIL_NOT_CREATED"

        results = {
            'success':                  success,
            'status':                   status,
            'email_scheduled_saved':    email_scheduled_saved,
            'email_scheduled_id':       email_scheduled.id,
            'email_scheduled':          email_scheduled,
        }
        return results

    def send_scheduled_email_list(self, messages_to_send):
        """
        Take in a list of scheduled_email_id's, and send them
        :param messages_to_send:
        :return:
        """
        results = {
            'success':                  success,
            'status':                   status,
            'at_least_one_email_found': True,
            'email_list':               email_list,
        }
        return results
