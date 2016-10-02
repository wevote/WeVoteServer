# friend/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
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
            defaults["invitation_secret_key"] = invitation_secret_key

        try:
            friend_invitation, created = FriendInvitationEmailLink.objects.update_or_create(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                recipient_email_we_vote_id__iexact=recipient_email_we_vote_id,
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
            defaults["invitation_secret_key"] = invitation_secret_key

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
                    viewer_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                    viewee_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
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
                    status = 'CURRENT_FRIEND_STATUS_UPDATED_TO_IGNORE'
                except Exception as e:
                    friend_invitation_saved = False
                    success = False
                    status = 'FAILED process_friend_invitation_voter_response delete FriendInvitationVoterLink '
            elif kind_of_invite_response == DELETE_INVITATION_VOTER_SENT_BY_ME:
                try:
                    friend_invitation_voter_link.invitation_status = IGNORED
                    friend_invitation_voter_link.save()
                    friend_invitation_saved = True
                    success = True
                    status = 'CURRENT_FRIEND_STATUS_UPDATED_TO_IGNORE'
                except Exception as e:
                    friend_invitation_saved = False
                    success = False
                    status = 'FAILED process_friend_invitation_voter_response delete FriendInvitationVoterLink '
            else:
                success = False
                status = 'CURRENT_FRIEND_KIND_OF_INVITE_RESPONSE_NOT_SUPPORTED'

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
            status = 'FAILED retrieve_current_friends '

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
            status = 'FAILED retrieve_friend_invitations_sent_by_me '

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
            status = 'FAILED retrieve_friend_invitations_sent_by_me FriendInvitationVoterLink'

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
            friend_invitation_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_queryset = friend_invitation_queryset.filter(
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id)
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
            status = 'FAILED retrieve_friend_invitations_sent_to_me '

        results = {
            'success':                      success,
            'status':                       status,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
            'friend_list_found':            friend_list_found,
            'friend_list':                  friend_list,
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
