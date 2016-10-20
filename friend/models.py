# friend/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from email_outbound.models import EmailAddress, EmailManager
from wevote_functions.functions import convert_to_int, positive_value_exists
from voter.models import VoterManager

NO_RESPONSE = 'NO_RESPONSE'
PENDING_EMAIL_VERIFICATION = 'PENDING_EMAIL_VERIFICATION'
ACCEPTED = 'ACCEPTED'
IGNORED = 'IGNORED'
INVITATION_STATUS_CHOICES = (
    (PENDING_EMAIL_VERIFICATION, 'Pending verification of your email'),
    (NO_RESPONSE, 'No response yet'),
    (ACCEPTED, 'Invitation accepted'),
    (IGNORED, 'Voter invited chose to ignore the invitation'),
)

# Processing invitations
ACCEPT_INVITATION = 'ACCEPT_INVITATION'
IGNORE_INVITATION = 'IGNORE_INVITATION'
DELETE_INVITATION_VOTER_SENT_BY_ME = 'DELETE_INVITATION_VOTER_SENT_BY_ME'
DELETE_INVITATION_EMAIL_SENT_BY_ME = 'DELETE_INVITATION_EMAIL_SENT_BY_ME'
UNFRIEND_CURRENT_FRIEND = 'UNFRIEND_CURRENT_FRIEND'

# Kinds of lists of friends
CURRENT_FRIENDS = 'CURRENT_FRIENDS'
FRIEND_INVITATIONS_PROCESSED = 'FRIEND_INVITATIONS_PROCESSED'
FRIEND_INVITATIONS_SENT_TO_ME = 'FRIEND_INVITATIONS_SENT_TO_ME'
FRIEND_INVITATIONS_SENT_BY_ME = 'FRIEND_INVITATIONS_SENT_BY_ME'
FRIENDS_IN_COMMON = 'FRIENDS_IN_COMMON'
IGNORED_FRIEND_INVITATIONS = 'IGNORED_FRIEND_INVITATIONS'
SUGGESTED_FRIENDS = 'SUGGESTED_FRIENDS'


class CurrentFriend(models.Model):
    """
    This table stores friendship relationships. The "direction" doesn't matter, although it usually indicates
    who initiated the first friend invitation.
    """
    viewer_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False)
    viewee_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 2", max_length=255, null=True, blank=True, unique=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def fetch_other_voter_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.viewer_voter_we_vote_id:
            return self.viewee_voter_we_vote_id
        elif one_we_vote_id == self.viewee_voter_we_vote_id:
            return self.viewer_voter_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class FriendInvitationEmailLink(models.Model):
    """
    Created when voter 1) invites via email (and the email isn't recognized or linked to voter).
    Once we have linked the email address to a voter, we want to remove this database entry and
    rely on the FriendInvitationVoterLink.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    sender_email_ownership_is_verified = models.BooleanField(default=False)  # Do we have an email address for sender?
    recipient_email_we_vote_id = models.CharField(
        verbose_name="email we vote id for recipient", max_length=255, null=True, blank=True, unique=False)
    # We include this here for data monitoring and debugging
    recipient_voter_email = models.EmailField(
        verbose_name='email address for recipient', max_length=255, null=True, blank=True, unique=False)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=50, choices=INVITATION_STATUS_CHOICES, default=NO_RESPONSE)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    merge_by_secret_key_allowed = models.BooleanField(default=True)  # To allow merges after delete
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendInvitationTwitterLink(models.Model):
    """
    Created when voter 1) invites via twitter handle and the twitter handle isn't recognized or linked to voter).
    Once we have linked the twitter handle to a voter, we want to remove this database entry and
    rely on the FriendInvitationVoterLink.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_twitter_handle = models.CharField(
        verbose_name='twitter screen_name', max_length=255, null=False, unique=False)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=50, choices=INVITATION_STATUS_CHOICES, default=NO_RESPONSE)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    merge_by_secret_key_allowed = models.BooleanField(default=True)  # To allow merges after delete
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendInvitationVoterLink(models.Model):
    """
    Created when voter 1) invites via email (and the email IS recognized), 2) invites via Facebook direct message, or
    3) invites via “friend suggestion” shown on We Vote.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    sender_email_ownership_is_verified = models.BooleanField(default=False)  # Do we have an email address for sender?
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=50, choices=INVITATION_STATUS_CHOICES, default=NO_RESPONSE)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    merge_by_secret_key_allowed = models.BooleanField(default=True)  # To allow merges after delete
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendManager(models.Model):

    def __unicode__(self):
        return "FriendManager"

    def create_or_update_friend_invitation_email_link(self, sender_voter_we_vote_id, recipient_email_we_vote_id='',
                                                      recipient_voter_email='', invitation_message='',
                                                      sender_email_ownership_is_verified=False,
                                                      invitation_secret_key=''):
        defaults = {
            "sender_voter_we_vote_id":          sender_voter_we_vote_id,
            "recipient_email_we_vote_id":       recipient_email_we_vote_id,
            "recipient_voter_email":            recipient_voter_email,
        }
        if positive_value_exists(sender_email_ownership_is_verified):
            defaults["sender_email_ownership_is_verified"] = sender_email_ownership_is_verified
        if positive_value_exists(invitation_message):
            defaults["invitation_message"] = invitation_message
        if positive_value_exists(invitation_secret_key):
            defaults["secret_key"] = invitation_secret_key

        try:
            friend_invitation, created = FriendInvitationEmailLink.objects.update_or_create(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                recipient_voter_email__iexact=recipient_voter_email,
                defaults=defaults,
            )
            # recipient_email_we_vote_id__iexact = recipient_email_we_vote_id,
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
                                                      invitation_message='', sender_email_ownership_is_verified=False,
                                                      invitation_secret_key=''):
        defaults = {
            "sender_voter_we_vote_id":              sender_voter_we_vote_id,
            "recipient_voter_we_vote_id":           recipient_voter_we_vote_id,
        }
        if positive_value_exists(sender_email_ownership_is_verified):
            defaults["sender_email_ownership_is_verified"] = sender_email_ownership_is_verified
        if positive_value_exists(invitation_message):
            defaults["invitation_message"] = invitation_message
        if positive_value_exists(invitation_secret_key):
            defaults["secret_key"] = invitation_secret_key

        try:
            friend_invitation, created = FriendInvitationVoterLink.objects.update_or_create(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
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

    def retrieve_current_friend(self, sender_voter_we_vote_id, recipient_voter_we_vote_id):
        current_friend = CurrentFriend()
        # Note that the direction of the friendship does not matter
        try:
            current_friend = CurrentFriend.objects.get(
                viewer_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                viewee_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
            )
            current_friend_found = True
            success = True
            status = "CURRENT_FRIEND_UPDATED_OR_CREATED"
        except CurrentFriend.DoesNotExist:
            # No data found. Try again below
            success = True
            current_friend_found = False
            status = 'NO_CURRENT_FRIEND_RETRIEVED_DoesNotExist'
        except Exception as e:
            current_friend_found = False
            current_friend = CurrentFriend()
            success = False
            status = "CURRENT_FRIEND_NOT_UPDATED_OR_CREATED"

        if not current_friend_found and success:
            try:
                current_friend = CurrentFriend.objects.get(
                    viewer_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                    viewee_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                )
                current_friend_found = True
                success = True
                status = "CURRENT_FRIEND_UPDATED_OR_CREATED"
            except CurrentFriend.DoesNotExist:
                # No data found. Try again below
                success = True
                current_friend_found = False
                status = 'NO_CURRENT_FRIEND_RETRIEVED2_DoesNotExist'
            except Exception as e:
                current_friend_found = False
                current_friend = CurrentFriend()
                success = False
                status = "CURRENT_FRIEND_NOT_UPDATED_OR_CREATED"

        results = {
            'success': success,
            'status': status,
            'current_friend_found': current_friend_found,
            'current_friend': current_friend,
        }
        return results

    def create_or_update_current_friend(self, sender_voter_we_vote_id, recipient_voter_we_vote_id):
        current_friend_created = False

        results = self.retrieve_current_friend(sender_voter_we_vote_id, recipient_voter_we_vote_id)
        current_friend_found = results['current_friend_found']
        current_friend = results['current_friend']
        success = results['success']
        status = results['status']

        if current_friend_found:
            # We don't need to actually do anything
            pass
        else:
            try:
                current_friend = CurrentFriend.objects.create(
                    viewer_voter_we_vote_id=sender_voter_we_vote_id,
                    viewee_voter_we_vote_id=recipient_voter_we_vote_id,
                )
                current_friend_created = True
                success = True
                status = "CURRENT_FRIEND_CREATED"
            except Exception as e:
                current_friend_created = False
                current_friend = CurrentFriend()
                success = False
                status = "CURRENT_FRIEND_NOT_CREATED"

        results = {
            'success':                  success,
            'status':                   status,
            'current_friend_found':     current_friend_found,
            'current_friend_created':   current_friend_created,
            'current_friend':           current_friend,
        }
        return results

    def process_friend_invitation_voter_response(self, sender_voter, voter, kind_of_invite_response):
        # Find the invite from other_voter (who issued this invitation) to the voter (who is responding)
        # 1) invite found
        # 2) invite NOT found
        # If 2, check for an invite to this voter's email (from before the email was linked to voter)
        # TODO: If 2, check to see if these two are already friends so we can return success if
        #  kind_of_invite_response == ACCEPT_INVITATION

        friend_invitation_deleted = False
        friend_invitation_saved = False

        friend_invitation_voter_link = FriendInvitationVoterLink()
        try:
            friend_invitation_voter_link = FriendInvitationVoterLink.objects.get(
                recipient_voter_we_vote_id__iexact=voter.we_vote_id,
                sender_voter_we_vote_id__iexact=sender_voter.we_vote_id,
            )
            success = True
            friend_invitation_found = True
            status = 'FRIEND_INVITATION_RETRIEVED'
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_found = False
            status = 'NO_FRIEND_INVITATION_RETRIEVED_DoesNotExist'
        except Exception as e:
            success = False
            friend_invitation_found = False
            status = 'FAILED process_friend_invitation_voter_response FriendInvitationVoterLink '

        if friend_invitation_found:
            if kind_of_invite_response == ACCEPT_INVITATION:
                # Create a CurrentFriend entry
                friend_manager = FriendManager()
                results = friend_manager.create_or_update_current_friend(sender_voter.we_vote_id, voter.we_vote_id)
                success = results['success']
                status = results['status']

                # And then delete the friend_invitation_voter_link
                if results['current_friend_found'] or results['current_friend_created']:
                    try:
                        friend_invitation_voter_link.delete()
                        friend_invitation_deleted = True
                    except Exception as e:
                        friend_invitation_deleted = False
                        success = False
                        status = 'FAILED process_friend_invitation_voter_response delete FriendInvitationVoterLink '
            elif kind_of_invite_response == IGNORE_INVITATION:
                try:
                    friend_invitation_voter_link.invitation_status = IGNORED
                    friend_invitation_voter_link.save()
                    friend_invitation_saved = True
                    success = True
                    status = 'CURRENT_FRIEND_INVITATION_VOTER_LINK_STATUS_UPDATED_TO_IGNORE'
                except Exception as e:
                    friend_invitation_saved = False
                    success = False
                    status = 'FAILED process_friend_invitation_voter_response delete FriendInvitationVoterLink '
            elif kind_of_invite_response == DELETE_INVITATION_VOTER_SENT_BY_ME:
                try:
                    friend_invitation_voter_link.delete()
                    friend_invitation_saved = True
                    success = True
                    status = 'CURRENT_FRIEND_INVITATION_VOTER_LINK_DELETED'
                except Exception as e:
                    friend_invitation_saved = False
                    success = False
                    status = 'FAILED process_friend_invitation_voter_response delete FriendInvitationVoterLink '
            else:
                success = False
                status = 'CURRENT_FRIEND_INVITATION_KIND_OF_INVITE_RESPONSE_NOT_SUPPORTED'

        results = {
            'success':                      success,
            'status':                       status,
            'sender_voter_we_vote_id':      sender_voter.we_vote_id,
            'recipient_voter_we_vote_id':   voter.we_vote_id,
            'friend_invitation_found':      friend_invitation_found,
            'friend_invitation_deleted':    friend_invitation_deleted,
            'friend_invitation_saved':      friend_invitation_saved,
        }
        return results

    def process_friend_invitation_email_response(self, sender_voter, recipient_voter_email, kind_of_invite_response):
        # Find the invite from other_voter (who issued this invitation) to the voter (who is responding)
        # 1) invite found
        # 2) invite NOT found

        friend_invitation_deleted = False
        friend_invitation_saved = False

        friend_invitation_email_link = FriendInvitationEmailLink()
        try:
            friend_invitation_email_link = FriendInvitationEmailLink.objects.get(
                sender_voter_we_vote_id__iexact=sender_voter.we_vote_id,
                recipient_voter_email__iexact=recipient_voter_email,
            )
            success = True
            friend_invitation_found = True
            status = 'FRIEND_INVITATION_EMAIL_RETRIEVED'
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_found = False
            status = 'NO_FRIEND_INVITATION_EMAIL_RETRIEVED_DoesNotExist'
        except Exception as e:
            success = False
            friend_invitation_found = False
            status = 'FAILED process_friend_invitation_email_response FriendInvitationEmailLink '

        if friend_invitation_found:
            if kind_of_invite_response == DELETE_INVITATION_EMAIL_SENT_BY_ME:
                try:
                    friend_invitation_email_link.deleted = True
                    friend_invitation_email_link.save()
                    friend_invitation_deleted = True
                    success = True
                    status = 'FRIEND_INVITATION_EMAIL_DELETED'
                except Exception as e:
                    friend_invitation_deleted = False
                    success = False
                    status = 'FAILED process_friend_invitation_email_response delete FriendInvitationEmailLink '
            else:
                success = False
                status = 'PROCESS_FRIEND_INVITATION_EMAIL_KIND_OF_INVITE_RESPONSE_NOT_SUPPORTED'

        results = {
            'success':                      success,
            'status':                       status,
            'sender_voter_we_vote_id':      sender_voter.we_vote_id,
            'recipient_voter_email':        recipient_voter_email,
            'friend_invitation_found':      friend_invitation_found,
            'friend_invitation_deleted':    friend_invitation_deleted,
            'friend_invitation_saved':      friend_invitation_saved,
        }
        return results

    def retrieve_current_friends(self, voter_we_vote_id):
        current_friend_list = []  # The entries from CurrentFriend table
        current_friend_list_found = False

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status = 'VALID_VOTER_WE_VOTE_ID_MISSING'
            results = {
                'success':                      success,
                'status':                       status,
                'voter_we_vote_id':             voter_we_vote_id,
                'current_friend_list_found':    current_friend_list_found,
                'current_friend_list':          current_friend_list,
            }
            return results

        try:
            current_friend_queryset = CurrentFriend.objects.all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friend_queryset = current_friend_queryset.order_by('-date_last_changed')
            current_friend_list = current_friend_queryset

            if len(current_friend_list):
                success = True
                current_friend_list_found = True
                status = 'CURRENT_FRIEND_LIST_RETRIEVED'
            else:
                success = True
                current_friend_list_found = False
                status = 'NO_CURRENT_FRIEND_LIST_RETRIEVED'
        except CurrentFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            current_friend_list_found = False
            status = 'NO_CURRENT_FRIEND_LIST_RETRIEVED_DoesNotExist'
            current_friend_list = []
        except Exception as e:
            success = False
            current_friend_list_found = False
            status = 'FAILED retrieve_current_friends '
            current_friend_list = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_we_vote_id':             voter_we_vote_id,
            'current_friend_list_found':    current_friend_list_found,
            'current_friend_list':          current_friend_list,
        }
        return results

    def retrieve_current_friends_as_voters(self, voter_we_vote_id):
        current_friend_list = []  # The entries from CurrentFriend table
        friend_list_found = False
        friend_list = []  # A list of friends, returned as voter entries

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status = 'VALID_VOTER_WE_VOTE_ID_MISSING'
            results = {
                'success':              success,
                'status':               status,
                'voter_we_vote_id':     voter_we_vote_id,
                'friend_list_found':    friend_list_found,
                'friend_list':          friend_list,
            }
            return results

        try:
            current_friend_queryset = CurrentFriend.objects.all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friend_queryset = current_friend_queryset.order_by('-date_last_changed')
            current_friend_list = current_friend_queryset

            if len(current_friend_list):
                success = True
                current_friend_list_found = True
                status = 'FRIEND_LIST_RETRIEVED'
            else:
                success = True
                current_friend_list_found = False
                status = 'NO_FRIEND_LIST_RETRIEVED'
        except CurrentFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            current_friend_list_found = False
            status = 'NO_FRIEND_LIST_RETRIEVED_DoesNotExist'
            friend_list = []
        except Exception as e:
            success = False
            current_friend_list_found = False
            status = 'FAILED retrieve_current_friends_as_voters '

        if current_friend_list_found:
            voter_manager = VoterManager()
            for current_friend_entry in current_friend_list:
                if current_friend_entry.viewer_voter_we_vote_id == voter_we_vote_id:
                    we_vote_id_of_friend = current_friend_entry.viewee_voter_we_vote_id
                else:
                    we_vote_id_of_friend = current_friend_entry.viewer_voter_we_vote_id
                # This is the voter you are friends with
                friend_voter_results = voter_manager.retrieve_voter_by_we_vote_id(we_vote_id_of_friend)
                if friend_voter_results['voter_found']:
                    friend_voter = friend_voter_results['voter']
                    friend_list.append(friend_voter)
                    friend_list_found = True

        results = {
            'success':              success,
            'status':               status,
            'voter_we_vote_id':     voter_we_vote_id,
            'friend_list_found':    friend_list_found,
            'friend_list':          friend_list,
        }
        return results

    def retrieve_friends_we_vote_id_list(self, voter_we_vote_id):
        """
        This is similar to retrieve_current_friends, but only returns the we_vote_id
        :param voter_we_vote_id:
        :return:
        """
        current_friend_list_found = False
        current_friend_list = []  # The entries from CurrentFriend table
        friends_we_vote_id_list_found = False
        friends_we_vote_id_list = []  # A list of friends, returned as we_vote_id's

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status = 'VALID_VOTER_WE_VOTE_ID_MISSING'
            results = {
                'success':                          success,
                'status':                           status,
                'voter_we_vote_id':                 voter_we_vote_id,
                'friends_we_vote_id_list_found':    friends_we_vote_id_list_found,
                'friends_we_vote_id_list':          friends_we_vote_id_list,
            }
            return results

        try:
            current_friend_queryset = CurrentFriend.objects.all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friend_queryset = current_friend_queryset.order_by('-date_last_changed')
            current_friend_list = current_friend_queryset

            if len(current_friend_list):
                success = True
                current_friend_list_found = True
                status = 'FRIEND_LIST_RETRIEVED'
            else:
                success = True
                current_friend_list_found = False
                status = 'NO_FRIEND_LIST_RETRIEVED'
        except CurrentFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            current_friend_list_found = False
            status = 'NO_FRIEND_LIST_RETRIEVED_DoesNotExist'
            friends_we_vote_id_list = []
        except Exception as e:
            success = False
            current_friend_list_found = False
            status = 'FAILED retrieve_friends_we_vote_id_list '

        if current_friend_list_found:
            for current_friend_entry in current_friend_list:
                if current_friend_entry.viewer_voter_we_vote_id == voter_we_vote_id:
                    we_vote_id_of_friend = current_friend_entry.viewee_voter_we_vote_id
                else:
                    we_vote_id_of_friend = current_friend_entry.viewer_voter_we_vote_id
                # This is the voter you are friends with
                friends_we_vote_id_list.append(we_vote_id_of_friend)
                friends_we_vote_id_list_found = True

        results = {
            'success':                          success,
            'status':                           status,
            'voter_we_vote_id':                 voter_we_vote_id,
            'friends_we_vote_id_list_found':    friends_we_vote_id_list_found,
            'friends_we_vote_id_list':          friends_we_vote_id_list,
        }
        return results

    def retrieve_friend_invitation_email_link_list(self, sender_voter_we_vote_id):
        status = ""

        if not positive_value_exists(sender_voter_we_vote_id):
            success = False
            status = 'RETRIEVE_FRIEND_INVITATION_EMAIL_LINK-MISSING_SENDER '
            results = {
                'success':                      success,
                'status':                       status,
                'sender_voter_we_vote_id':      sender_voter_we_vote_id,
                'friend_invitation_list_found': False,
                'friend_invitation_list':       [],
            }
            return results

        friend_invitation_email_link_list = []
        try:
            # Find invitations that I sent.
            friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id)
            friend_invitation_email_link_list = friend_invitation_email_queryset

            if len(friend_invitation_email_link_list):
                success = True
                friend_invitation_email_link_list_found = True
                status += ' FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
            else:
                success = True
                friend_invitation_email_link_list_found = False
                status += ' NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_email_link_list_found = False
            status += ' NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED_DoesNotExist '
            friend_invitation_email_link_list = []
        except Exception as e:
            success = False
            friend_invitation_email_link_list_found = False
            status += ' FAILED retrieve_friend_invitation_email_link_list FriendInvitationVoterLink '

        results = {
            'success':                      success,
            'status':                       status,
            'sender_voter_we_vote_id':      sender_voter_we_vote_id,
            'friend_invitation_list_found': friend_invitation_email_link_list_found,
            'friend_invitation_list':       friend_invitation_email_link_list,
        }
        return results

    def retrieve_friend_invitation_voter_link_list(self, sender_voter_we_vote_id='', recipient_voter_we_vote_id=''):
        status = ""

        if not positive_value_exists(sender_voter_we_vote_id) and not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status = 'RETRIEVE_FRIEND_INVITATION_VOTER_LINK-MISSING_BOTH_SENDER_AND_RECIPIENT '
            results = {
                'success':                      success,
                'status':                       status,
                'sender_voter_we_vote_id':      sender_voter_we_vote_id,
                'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
                'friend_invitation_list_found': False,
                'friend_invitation_list':       [],
            }
            return results

        friend_invitation_from_voter_list = []
        try:
            # Find invitations that I sent.
            friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.all()
            if positive_value_exists(sender_voter_we_vote_id):
                friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                    sender_voter_we_vote_id__iexact=sender_voter_we_vote_id)
            if positive_value_exists(recipient_voter_we_vote_id):
                friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                    recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id)
            friend_invitation_from_voter_list = friend_invitation_voter_queryset

            if len(friend_invitation_from_voter_list):
                success = True
                friend_invitation_from_voter_list_found = True
                status += ' FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
            else:
                success = True
                friend_invitation_from_voter_list_found = False
                status += ' NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_from_voter_list_found = False
            status += ' NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED_DoesNotExist '
            friend_invitation_from_voter_list = []
        except Exception as e:
            success = False
            friend_invitation_from_voter_list_found = False
            status += ' FAILED retrieve_friend_invitation_voter_link_list FriendInvitationVoterLink '

        results = {
            'success': success,
            'status': status,
            'sender_voter_we_vote_id': sender_voter_we_vote_id,
            'recipient_voter_we_vote_id': recipient_voter_we_vote_id,
            'friend_invitation_list_found': friend_invitation_from_voter_list_found,
            'friend_invitation_list': friend_invitation_from_voter_list,
        }
        return results

    def retrieve_friend_invitations_processed(self, viewer_voter_we_vote_id):
        """

        :param viewer_voter_we_vote_id:
        :return:
        """
        friend_list_found = False
        friend_list = []
        status = ""

        if not positive_value_exists(viewer_voter_we_vote_id):
            success = False
            status = 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                  success,
                'status':                   status,
                'viewer_voter_we_vote_id':  viewer_voter_we_vote_id,
                'friend_list_found':        friend_list_found,
                'friend_list':              friend_list,
            }
            return results

        # ###########################
        # In this block, we look for invitations sent by viewer_voter_we_vote_id
        friend_invitation_from_voter_list = []
        friend_invitation_from_voter_list_found = False
        try:
            # Find invitations that I sent that were accepted. Do NOT show invitations that were ignored.
            friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                sender_voter_we_vote_id__iexact=viewer_voter_we_vote_id)
            # It is possible through account merging to have an invitation to yourself. We want to exclude these.
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                recipient_voter_we_vote_id__iexact=viewer_voter_we_vote_id)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(invitation_status=ACCEPTED)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(deleted=True)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.order_by('-date_last_changed')
            friend_invitation_from_voter_list = friend_invitation_voter_queryset

            if len(friend_invitation_from_voter_list):
                success = True
                friend_invitation_from_voter_list_found = True
                status += 'FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
            else:
                success = True
                friend_invitation_from_voter_list_found = False
                status += 'NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_from_voter_list_found = False
            status += 'NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED_DoesNotExist '
            friend_invitation_from_voter_list = []
        except Exception as e:
            success = False
            friend_invitation_from_voter_list_found = False
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationVoterLink '

        friend_invitation_from_email_list = []
        try:
            # Find invitations that I sent that were accepted. Do NOT show invitations that were ignored.
            friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                sender_voter_we_vote_id__iexact=viewer_voter_we_vote_id)
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(invitation_status=ACCEPTED)
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(deleted=True)
            friend_invitation_email_queryset = friend_invitation_email_queryset.order_by('-date_last_changed')
            friend_invitation_from_email_list = friend_invitation_email_queryset
            success = True

            if len(friend_invitation_from_email_list):
                status += 'FRIEND_LIST_EMAIL_RETRIEVED '
                friend_invitation_from_email_list_found = True
            else:
                status += 'NO_FRIEND_LIST_EMAIL_RETRIEVED '
                friend_invitation_from_email_list_found = False
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            friend_invitation_from_email_list_found = False
            status += 'NO_FRIEND_LIST_EMAIL_RETRIEVED_DoesNotExist '
        except Exception as e:
            friend_invitation_from_email_list_found = False
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationEmailLink '

        if friend_invitation_from_voter_list_found and friend_invitation_from_email_list_found:
            friend_invitation_from_list_found = True
            friend_invitation_from_list = list(friend_invitation_from_voter_list) + \
                list(friend_invitation_from_email_list)
        elif friend_invitation_from_voter_list_found:
            friend_invitation_from_list_found = True
            friend_invitation_from_list = friend_invitation_from_voter_list
        elif friend_invitation_from_email_list_found:
            friend_invitation_from_list_found = True
            friend_invitation_from_list = friend_invitation_from_email_list
        else:
            friend_invitation_from_list_found = False
            friend_invitation_from_list = []

        # ###########################
        # In this block, we look for invitations sent TO viewer_voter_we_vote_id
        friend_invitation_to_voter_list = []
        friend_invitation_to_voter_list_found = False
        try:
            # Find invitations that I received, including ones that I have ignored.
            friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                recipient_voter_we_vote_id__iexact=viewer_voter_we_vote_id)
            # It is possible through account merging to have an invitation to yourself. We want to exclude these.
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                sender_voter_we_vote_id__iexact=viewer_voter_we_vote_id)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                Q(invitation_status=ACCEPTED) |
                Q(invitation_status=IGNORED))
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(deleted=True)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.order_by('-date_last_changed')
            friend_invitation_to_voter_list = friend_invitation_voter_queryset

            if len(friend_invitation_to_voter_list):
                success = True
                friend_invitation_to_voter_list_found = True
                status += 'FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED'
            else:
                success = True
                friend_invitation_to_voter_list_found = False
                status += 'NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_to_voter_list_found = False
            status += 'NO_FRIEND_INVITATIONS_PROCESSED_LIST_RETRIEVED_DoesNotExist '
            friend_invitation_to_voter_list = []
        except Exception as e:
            success = False
            friend_invitation_to_voter_list_found = False
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationVoterLink '

        friend_invitation_to_email_list = []
        friend_invitation_to_email_list_found = False
        try:
            # Cycle through all of the viewer_voter_we_vote_id email addresses so we can retrieve invitations sent
            #  to this voter when we didn't know the voter_we_vote_id

            # First, find the verified email for viewer_voter_we_vote_id. # TODO DALE
            email_manager = EmailManager()
            filters = []
            email_results = email_manager.retrieve_voter_email_address_list(viewer_voter_we_vote_id)
            if email_results['email_address_list_found']:
                email_address_list = email_results['email_address_list']

                for one_email in email_address_list:
                    if positive_value_exists(one_email.we_vote_id):
                        new_filter = Q(recipient_voter_email__iexact=one_email.normalized_email_address)
                        filters.append(new_filter)

            # Add the first query
            if len(filters):
                viewer_voter_emails_found = True
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item
            else:
                viewer_voter_emails_found = False
        except EmailAddress.DoesNotExist:
            # No data found. Not a problem.
            viewer_voter_emails_found = False
            status += 'NO_FRIEND_LIST_EMAIL_RETRIEVED_DoesNotExist '
        except Exception as e:
            viewer_voter_emails_found = False
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationEmailLink '

        if viewer_voter_emails_found and len(final_filters):
            try:
                # Find invitations that were sent to one of my email addresses
                friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
                friend_invitation_email_queryset = friend_invitation_email_queryset.filter(final_filters)
                friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                    Q(invitation_status=ACCEPTED) |
                    Q(invitation_status=IGNORED))
                friend_invitation_email_queryset = friend_invitation_email_queryset.filter(deleted=True)
                friend_invitation_email_queryset = friend_invitation_email_queryset.order_by('-date_last_changed')
                friend_invitation_to_email_list = friend_invitation_email_queryset
                success = True

                if len(friend_invitation_to_email_list):
                    status += ' FRIEND_LIST_EMAIL_RETRIEVED '
                    friend_invitation_to_email_list_found = True
                else:
                    status += ' NO_FRIEND_LIST_EMAIL_RETRIEVED '
                    friend_invitation_to_email_list_found = False
            except FriendInvitationEmailLink.DoesNotExist:
                # No data found. Not a problem.
                friend_invitation_to_email_list_found = False
                status += 'NO_FRIEND_LIST_EMAIL_RETRIEVED_DoesNotExist '
            except Exception as e:
                friend_invitation_to_email_list_found = False
                status += 'FAILED retrieve_friend_invitations_processed FriendInvitationEmailLink '

        if friend_invitation_to_voter_list_found and friend_invitation_to_email_list_found:
            friend_invitation_to_list_found = True
            friend_invitation_to_list = list(friend_invitation_to_voter_list) + list(friend_invitation_to_email_list)
        elif friend_invitation_to_voter_list_found:
            friend_invitation_to_list_found = True
            friend_invitation_to_list = friend_invitation_to_voter_list
        elif friend_invitation_to_email_list_found:
            friend_invitation_to_list_found = True
            friend_invitation_to_list = friend_invitation_to_email_list
        else:
            friend_invitation_to_list_found = False
            friend_invitation_to_list = []

        # ####################################
        # Now merge the "from" and "to" lists
        if friend_invitation_from_list_found and friend_invitation_to_list_found:
            friend_list_found = True
            friend_list = list(friend_invitation_from_list) + list(friend_invitation_to_list)
        elif friend_invitation_from_list_found:
            friend_list_found = True
            friend_list = friend_invitation_from_list
        elif friend_invitation_to_list_found:
            friend_list_found = True
            friend_list = friend_invitation_to_list
        else:
            friend_list_found = False
            friend_list = []

        results = {
            'success':                  success,
            'status':                   status,
            'viewer_voter_we_vote_id':  viewer_voter_we_vote_id,
            'friend_list_found':        friend_list_found,
            'friend_list':              friend_list,
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
            friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id)
            # It is possible through account merging to have an invitation to yourself. We want to exclude these.
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                recipient_voter_we_vote_id__iexact=sender_voter_we_vote_id)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(deleted=False)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.order_by('-date_last_changed')
            friend_list = friend_invitation_voter_queryset

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
            status = 'FAILED retrieve_friend_invitations_processed FriendInvitationVoterLink'

        friend_list_email = []
        try:
            friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id)
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(deleted=False)
            friend_invitation_email_queryset = friend_invitation_email_queryset.order_by('-date_last_changed')
            friend_list_email = friend_invitation_email_queryset
            success = True

            if len(friend_list_email):
                status += ' FRIEND_LIST_EMAIL_RETRIEVED'
                friend_list_email_found = True

                # Filter out invitations to the same voter (assuming the other voter signed in). These are invitations
                #  sent to an email address before we knew who owned the email address. There isn't a need to
                #  show the invitation to the email address if we have a direct invitation to the voter above.
                updated_friend_list_email = []
                email_manager = EmailManager()
                # Cycle through each invitation. If a verified owner of the email is found, augment the record
                # with recipient_voter_we_vote_id so we can treat the invitation as a link to a We Vote account
                for friend_invitation_email_link_object in friend_list_email:
                    is_new_invitation = True
                    email_results = email_manager.retrieve_primary_email_with_ownership_verified(
                        "", friend_invitation_email_link_object.recipient_voter_email)
                    if email_results['email_address_object_found']:
                        email_address_object = email_results['email_address_object']
                        # We create a new attribute on this object (that normally doesn't exist)
                        friend_invitation_email_link_object.recipient_voter_we_vote_id = \
                            email_address_object.voter_we_vote_id
                        just_found_voter_we_vote_id = friend_invitation_email_link_object.recipient_voter_we_vote_id
                        for friend_invitation_voter_link in friend_list:
                            # Do we already have an invitation from this voter? If so, ignore it.
                            if just_found_voter_we_vote_id == friend_invitation_voter_link.recipient_voter_we_vote_id:
                                is_new_invitation = False
                                break

                        # Is there already an invitation for just_found_voter_we_vote_id?
                    if is_new_invitation:
                        updated_friend_list_email.append(friend_invitation_email_link_object)
                friend_list_email = updated_friend_list_email
            else:
                status += ' NO_FRIEND_LIST_EMAIL_RETRIEVED'
                friend_list_email_found = False
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            friend_list_email_found = False
            status = 'NO_FRIEND_LIST_EMAIL_RETRIEVED_DoesNotExist'
        except Exception as e:
            friend_list_email_found = False
            status = 'FAILED retrieve_friend_invitations_sent_by_me FriendInvitationEmailLink'

        if friend_list_found and friend_list_email_found:
            friend_list = list(friend_list) + list(friend_list_email)
        elif friend_list_email_found:
            friend_list = friend_list_email

        results = {
            'success':                  success,
            'status':                   status,
            'sender_voter_we_vote_id':  sender_voter_we_vote_id,
            'friend_list_found':        friend_list_found or friend_list_email_found,
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
            friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id)
            # It is possible through account merging to have an invitation to yourself. We want to exclude these.
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                sender_voter_we_vote_id__iexact=recipient_voter_we_vote_id)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.order_by('-date_last_changed')
            friend_list = friend_invitation_voter_queryset

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
            status = 'FAILED retrieve_friend_invitations_sent_to_me '

        results = {
            'success':                      success,
            'status':                       status,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
            'friend_list_found':            friend_list_found,
            'friend_list':                  friend_list,
        }
        return results

    def retrieve_friend_invitation_from_secret_key(self, invitation_secret_key, for_merge_accounts=False):
        """

        :param invitation_secret_key:
        :param for_merge_accounts:
        :return:
        """
        # Start by looking in FriendInvitationVoterLink table
        friend_invitation_voter_link_found = False
        friend_invitation_voter_link = FriendInvitationVoterLink()
        # If not found, then look in FriendInvitationEmailLink table
        friend_invitation_email_link_found = False
        friend_invitation_email_link = FriendInvitationEmailLink()
        status = ""

        try:
            if positive_value_exists(invitation_secret_key) and for_merge_accounts:
                friend_invitation_voter_link = FriendInvitationVoterLink.objects.get(
                    secret_key=invitation_secret_key,
                    merge_by_secret_key_allowed=True,
                )
                friend_invitation_voter_link_found = True
                success = True
                status += "RETRIEVE_FRIEND_INVITATION_FOUND_BY_SECRET_KEY_FOR_MERGE "
            elif positive_value_exists(invitation_secret_key):
                friend_invitation_voter_link = FriendInvitationVoterLink.objects.get(
                    secret_key=invitation_secret_key,
                    deleted=False,
                )
                friend_invitation_voter_link_found = True
                success = True
                status += "RETRIEVE_FRIEND_INVITATION_FOUND_BY_SECRET_KEY1 "
            else:
                friend_invitation_voter_link_found = False
                success = False
                status += "RETRIEVE_FRIEND_INVITATION_BY_SECRET_KEY_VARIABLES_MISSING1 "
        except FriendInvitationVoterLink.DoesNotExist:
            success = True
            status += "RETRIEVE_FRIEND_INVITATION_BY_SECRET_KEY_NOT_FOUND1 "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_friend_invitation_from_secret_key FriendInvitationVoterLink '

        if friend_invitation_voter_link_found:

            results = {
                'success':                              success,
                'status':                               status,
                'friend_invitation_found':
                    friend_invitation_email_link_found or friend_invitation_voter_link_found,
                'friend_invitation_email_link_found':   friend_invitation_email_link_found,
                'friend_invitation_email_link':         friend_invitation_email_link,
                'friend_invitation_voter_link_found':   friend_invitation_voter_link_found,
                'friend_invitation_voter_link':         friend_invitation_voter_link,
            }
            return results

        try:
            if positive_value_exists(invitation_secret_key) and for_merge_accounts:
                friend_invitation_email_link = FriendInvitationEmailLink.objects.get(
                    secret_key=invitation_secret_key,
                    merge_by_secret_key_allowed=True,
                )
                friend_invitation_email_link_found = True
                success = True
                status += "RETRIEVE_FRIEND_INVITATION_FOUND_BY_INVITATION_SECRET_KEY_FOR_MERGE2 "
            elif positive_value_exists(invitation_secret_key):
                friend_invitation_email_link = FriendInvitationEmailLink.objects.get(
                    secret_key=invitation_secret_key,
                    deleted=False,
                )
                friend_invitation_email_link_found = True
                success = True
                status += "RETRIEVE_FRIEND_INVITATION_FOUND_BY_SECRET_KEY2"
            else:
                friend_invitation_email_link_found = False
                success = False
                status += "RETRIEVE_FRIEND_INVITATION_BY_SECRET_KEY_VARIABLES_MISSING2"
        except FriendInvitationEmailLink.DoesNotExist:
            success = True
            status += "RETRIEVE_FRIEND_INVITATION_BY_SECRET_KEY_NOT_FOUND2"
        except Exception as e:
            success = False
            status += 'FAILED retrieve_friend_invitation_from_secret_key FriendInvitationEmailLink'

        results = {
            'success':                              success,
            'status':                               status,
            'friend_invitation_found':
                friend_invitation_email_link_found or friend_invitation_voter_link_found,
            'friend_invitation_email_link_found':   friend_invitation_email_link_found,
            'friend_invitation_email_link':         friend_invitation_email_link,
            'friend_invitation_voter_link_found':   friend_invitation_voter_link_found,
            'friend_invitation_voter_link':         friend_invitation_voter_link,
        }
        return results

    def unfriend_current_friend(self, acting_voter_we_vote_id, other_voter_we_vote_id):
        # Retrieve the existing friendship
        results = self.retrieve_current_friend(acting_voter_we_vote_id, other_voter_we_vote_id)

        success = False
        status = 'PREPARING_TO_DELETE_CURRENT_FRIEND'
        current_friend_deleted = False

        if results['current_friend_found']:
            current_friend = results['current_friend']
            try:
                current_friend.delete()
                current_friend_deleted = True
                success = True
                status = 'CURRENT_FRIEND_DELETED'
            except Exception as e:
                success = False
                current_friend_deleted = False
                status = 'FAILED unfriend_current_friend '

        results = {
            'success':                      success,
            'status':                       status,
            'acting_voter_we_vote_id':      acting_voter_we_vote_id,
            'other_voter_we_vote_id':       other_voter_we_vote_id,
            'current_friend_deleted':       current_friend_deleted,
        }
        return results
