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
    email_we_vote_id = models.CharField(
        verbose_name="we vote id for the email address", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_email = models.EmailField(
        verbose_name='email address', max_length=255, null=True, blank=True, unique=False)
    email_scheduled_id = models.PositiveIntegerField(
        verbose_name="the internal id of EmailScheduled", default=0, null=False)
    assembly_status = models.CharField(max_length=20, choices=ASSEMBLY_STATUS_CHOICES, default=TO_BE_PROCESSED)


class EmailScheduled(models.Model):
    """
    Used to tell the email server literally what to send.
    """
    subject = models.CharField(verbose_name="email subject", max_length=255, null=True, blank=True, unique=False)
    message_text = models.TextField(null=True, blank=True)
    message_html = models.TextField(null=True, blank=True)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_email_we_vote_id = models.CharField(
        verbose_name="we vote id for the email", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_email = models.EmailField(
        verbose_name='email address', max_length=255, null=True, blank=True, unique=False)
    send_status = models.CharField(max_length=20, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)


class EmailManager(models.Model):
    def __unicode__(self):
        return "EmailManager"

    def create_email_outbound_description(self, voter, email_addresses_raw, invitation_message):
        friend_invitation_by_email_saved = False
        # try:
        #     friend_invitation_by_email = FriendInvitationByEmail.objects.create(
        #         email_addresses_raw=email_addresses_raw,
        #         invitation_message=invitation_message,
        #         sender_voter_we_vote_id=voter.we_vote_id,
        #     )
        #     friend_invitation_by_email_saved = True
        #     success = True
        #     status = "BATCH_ROW_ACTION_ORGANIZATION_CREATED"
        # except Exception as e:
        #     batch_row_action_created = False
        #     batch_row_action_organization = BatchRowActionOrganization()
        #     success = False
        #     status = "BATCH_ROW_ACTION_ORGANIZATION_NOT_CREATED"
        #
        # # if friend_invitation_by_email_saved:

        results = {
            'success': success,
            'status': status,
            'batch_row_action_created': batch_row_action_created,
            'batch_row_action_organization': batch_row_action_organization,
        }
        return results
