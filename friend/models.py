# friend/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import MEASURE, OFFICE, CANDIDATE
import codecs
import csv
from django.db import models
from organization.models import ORGANIZATION_TYPE_CHOICES, UNKNOWN, alphanumeric
from position.models import POSITION, POSITION_CHOICES, NO_STANCE
import urllib.request
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

NO_RESPONSE = 'NO_RESPONSE'
ACCEPTED = 'ACCEPTED'
IGNORED = 'IGNORED'
INVITATION_STATUS_CHOICES = (
    (NO_RESPONSE,  'No response yet'),
    (ACCEPTED, 'Invitation accepted'),
    (IGNORED, 'Voter invited chose to ignore the invitation'),
)

DRAFT = 'DRAFT'
INVITATIONS_SENT = 'INVITATIONS_SENT'
FRIEND_INVITATIONS_STATUS_CHOICES = (
    (DRAFT,  'Still a draft, more info needed'),
    (INVITATIONS_SENT,  'Invitations sent'),
)


class CurrentFriend(models.Model):
    """
    We store both directions in one entry so we only have to make one call to this table
    to find a friendship relationship.
    """
    viewer1_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False)
    viewer2_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 2", max_length=255, null=True, blank=True, unique=False)
    viewee1_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 2", max_length=255, null=True, blank=True, unique=False)
    viewee2_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False)


class FriendInvitation(models.Model):
    """
    Created when voter 1) invites via email, 2) invites via Facebook direct message, or
    3) invites via “friend suggestion” shown on We Vote.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    email_we_vote_id = models.CharField(
        verbose_name="we vote id for the email address", max_length=255, null=True, blank=True, unique=False)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invitation_status = models.CharField(max_length=20, choices=INVITATION_STATUS_CHOICES, default=DRAFT)
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendManager(models.Model):

    def __unicode__(self):
        return "FriendManager"

    def create_friend_invitation(self, voter, email_addresses_raw, invitation_message):
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

        # if friend_invitation_by_email_saved:

        results = {
            'success': success,
            'status': status,
            'batch_row_action_created': batch_row_action_created,
            'batch_row_action_organization': batch_row_action_organization,
        }
        return results
