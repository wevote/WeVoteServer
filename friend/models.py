# friend/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
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

# Kinds of lists of friends
CURRENT_FRIENDS = 'CURRENT_FRIENDS'
FRIEND_INVITATIONS_SENT_TO_ME = 'FRIEND_INVITATIONS_SENT_TO_ME'
FRIEND_INVITATIONS_SENT_BY_ME = 'FRIEND_INVITATIONS_SENT_BY_ME'
FRIENDS_IN_COMMON = 'FRIENDS_IN_COMMON'
IGNORED_FRIEND_INVITATIONS = 'IGNORED_FRIEND_INVITATIONS'
SUGGESTED_FRIENDS = 'SUGGESTED_FRIENDS'


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
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class FriendInvitationEmailLink(models.Model):
    """
    Created when voter 1) invites via email (and the email isn't recognized or linked to voter).
    Once we have linked the email address to a voter, we want to remove this database entry and
    rely on the FriendInvitationVoterLink.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_email_we_vote_id = models.CharField(
        verbose_name="email we vote id for recipient", max_length=255, null=True, blank=True, unique=False)
    # We include this here for data monitoring and debugging
    recipient_voter_email = models.EmailField(
        verbose_name='email address for recipient', max_length=255, null=True, blank=True, unique=False)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=20, choices=INVITATION_STATUS_CHOICES, default=DRAFT)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendInvitationVoterLink(models.Model):
    """
    Created when voter 1) invites via email (and the email IS recognized), 2) invites via Facebook direct message, or
    3) invites via “friend suggestion” shown on We Vote.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=20, choices=INVITATION_STATUS_CHOICES, default=DRAFT)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendManager(models.Model):

    def __unicode__(self):
        return "FriendManager"

    def create_or_update_friend_invitation_email_link(self, sender_voter_we_vote_id, recipient_email_we_vote_id='',
                                                      recipient_voter_email='', invitation_message=''):
        defaults = {
            "sender_voter_we_vote_id":      sender_voter_we_vote_id,
            "recipient_email_we_vote_id":   recipient_email_we_vote_id,
            "recipient_voter_email":        recipient_voter_email,
            "invitation_message":           invitation_message
        }

        try:
            friend_invitation, created = FriendInvitationEmailLink.objects.update_or_create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                recipient_email_we_vote_id=recipient_email_we_vote_id,
                defaults=defaults,
            )
            friend_invitation_saved = True
            success = True
            status = "FRIEND_INVITATION_EMAIL_LINK_UPDATED_OR_CREATED"
        except Exception as e:
            friend_invitation_saved = False
            friend_invitation = FriendInvitationEmailLink()
            success = False
            created = False
            status = "FRIEND_INVITATION_EMAIL_LINK_NOT_UPDATED_OR_CREATED"

        results = {
            'success':                      success,
            'status':                       status,
            'friend_invitation_saved':      friend_invitation_saved,
            'friend_invitation_created':    created,
            'friend_invitation':            friend_invitation,
        }
        return results

    def create_or_update_friend_invitation_voter_link(self, sender_voter_we_vote_id, recipient_voter_we_vote_id='',
                                                      invitation_message=''):
        defaults = {
            "sender_voter_we_vote_id":      sender_voter_we_vote_id,
            "recipient_voter_we_vote_id":   recipient_voter_we_vote_id,
            "invitation_message":           invitation_message
        }

        try:
            friend_invitation, created = FriendInvitationVoterLink.objects.update_or_create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                defaults=defaults,
            )
            friend_invitation_saved = True
            success = True
            status = "FRIEND_INVITATION_VOTER_LINK_UPDATED_OR_CREATED"
        except Exception as e:
            friend_invitation_saved = False
            friend_invitation = FriendInvitationVoterLink()
            success = False
            created = False
            status = "FRIEND_INVITATION_VOTER_LINK_NOT_UPDATED_OR_CREATED"

        results = {
            'success':                      success,
            'status':                       status,
            'friend_invitation_saved':      friend_invitation_saved,
            'friend_invitation_created':    created,
            'friend_invitation':            friend_invitation,
        }
        return results

    def retrieve_friend_invitations_sent_by_me(self, sender_voter_we_vote_id):
        friend_list_found = False
        friend_list = []

        if not positive_value_exists(sender_voter_we_vote_id):
            success = False
            status = 'VALID_VOTER_WE_VOTE_ID_MISSING'
            results = {
                'success':                  success,
                'status':                   status,
                'sender_voter_we_vote_id':  sender_voter_we_vote_id,
                'friend_list_found':        friend_list_found,
                'friend_list':              friend_list,
            }
            return results

        try:
            friend_invitation_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_queryset = friend_invitation_queryset.filter(
                sender_voter_we_vote_id=sender_voter_we_vote_id)
            friend_invitation_queryset = friend_invitation_queryset.order_by('-date_last_changed')
            friend_list = friend_invitation_queryset

            if len(friend_list):
                success = True
                friend_list_found = True
                status = 'FRIEND_LIST_RETRIEVED'
            else:
                success = True
                friend_list_found = False
                status = 'NO_FRIEND_LIST_RETRIEVED'
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_list_found = False
            status = 'NO_FRIEND_LIST_RETRIEVED_DoesNotExist'
            friend_list = []
        except Exception as e:
            success = False
            friend_list_found = False
            status = 'FAILED retrieve_friend_invitations_sent_by_me ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                  success,
            'status':                   status,
            'sender_voter_we_vote_id':  sender_voter_we_vote_id,
            'friend_list_found':        friend_list_found,
            'friend_list':              friend_list,
        }
        return results

    def retrieve_friend_invitations_sent_to_me(self, recipient_voter_we_vote_id):
        friend_list_found = False
        friend_list = []

        if not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status = 'VALID_RECIPIENT_VOTER_WE_VOTE_ID_MISSING'
            results = {
                'success':                      success,
                'status':                       status,
                'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
                'friend_list_found':            friend_list_found,
                'friend_list':                  friend_list,
            }
            return results

        try:
            friend_invitation_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_queryset = friend_invitation_queryset.filter(
                recipient_voter_we_vote_id=recipient_voter_we_vote_id)
            friend_invitation_queryset = friend_invitation_queryset.order_by('-date_last_changed')
            friend_list = friend_invitation_queryset

            if len(friend_list):
                success = True
                friend_list_found = True
                status = 'FRIEND_LIST_RETRIEVED'
            else:
                success = True
                friend_list_found = False
                status = 'NO_FRIEND_LIST_RETRIEVED'
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_list_found = False
            status = 'NO_FRIEND_LIST_RETRIEVED_DoesNotExist'
            friend_list = []
        except Exception as e:
            success = False
            friend_list_found = False
            status = 'FAILED retrieve_friend_invitations_sent_to_me ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      success,
            'status':                       status,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
            'friend_list_found':            friend_list_found,
            'friend_list':                  friend_list,
        }
        return results
