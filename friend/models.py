# friend/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import psycopg2
from django.db import models
from django.db.models import Q
from config.base import get_environment_variable
from email_outbound.models import EmailManager
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists

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

# Which database table is the invitation from?
FRIEND_INVITATION_EMAIL_LINK = 'EMAIL'
FRIEND_INVITATION_FACEBOOK_LINK = 'FACEBOOK'
FRIEND_INVITATION_TWITTER_LINK = 'TWITTER'
FRIEND_INVITATION_VOTER_LINK = 'VOTER'

# Processing invitations
ACCEPT_INVITATION = 'ACCEPT_INVITATION'
IGNORE_INVITATION = 'IGNORE_INVITATION'
IGNORE_SUGGESTION = 'IGNORE_SUGGESTION'
DELETE_INVITATION_VOTER_SENT_BY_ME = 'DELETE_INVITATION_VOTER_SENT_BY_ME'
DELETE_INVITATION_EMAIL_SENT_BY_ME = 'DELETE_INVITATION_EMAIL_SENT_BY_ME'
UNFRIEND_CURRENT_FRIEND = 'UNFRIEND_CURRENT_FRIEND'

# Kinds of lists of friends
CURRENT_FRIENDS = 'CURRENT_FRIENDS'
FRIEND_INVITATIONS_PROCESSED = 'FRIEND_INVITATIONS_PROCESSED'
FRIEND_INVITATIONS_SENT_TO_ME = 'FRIEND_INVITATIONS_SENT_TO_ME'
FRIEND_INVITATIONS_SENT_BY_ME = 'FRIEND_INVITATIONS_SENT_BY_ME'
FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION = 'FRIEND_INVITATIONS_WAITING_FOR_VERIFICATION'
FRIENDS_IN_COMMON = 'FRIENDS_IN_COMMON'
IGNORED_FRIEND_INVITATIONS = 'IGNORED_FRIEND_INVITATIONS'
SUGGESTED_FRIEND_LIST = 'SUGGESTED_FRIEND_LIST'


class CurrentFriend(models.Model):
    """
    This table stores friendship relationships. The "direction" doesn't matter, although it usually indicates
    who initiated the first friend invitation.
    """
    viewer_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False, db_index=True)
    viewer_organization_we_vote_id = models.CharField(
        max_length=255, null=True, blank=True, unique=False, db_index=True)
    viewee_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 2", max_length=255, null=True, blank=True, unique=False, db_index=True)
    viewee_organization_we_vote_id = models.CharField(
        max_length=255, null=True, blank=True, unique=False, db_index=True)

    mutual_friend_count = models.PositiveSmallIntegerField(null=True, unique=False)
    mutual_friend_count_last_updated = models.DateTimeField(null=True)

    mutual_friend_preview_list_serialized = models.TextField(default=None, null=True)
    mutual_friend_preview_list_update_needed = models.BooleanField(default=True)

    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def fetch_other_organization_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.viewer_voter_we_vote_id:
            return self.viewee_voter_we_vote_id
        elif one_we_vote_id == self.viewee_voter_we_vote_id:
            return self.viewer_voter_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""

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
    recipient_first_name = models.CharField(verbose_name='first name', max_length=255, null=True, blank=True)
    recipient_last_name = models.CharField(verbose_name='last name', max_length=255, null=True, blank=True)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invited_friend_accepted_notification_sent = models.BooleanField(default=False)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=50, choices=INVITATION_STATUS_CHOICES, default=NO_RESPONSE)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    merge_by_secret_key_allowed = models.BooleanField(default=True)  # To allow merges after delete
    invitation_table = models.CharField(max_length=8, default=FRIEND_INVITATION_EMAIL_LINK)
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
    invitation_table = models.CharField(max_length=8, default=FRIEND_INVITATION_TWITTER_LINK)
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendInvitationFacebookLink(models.Model):
    """
    Created when voter 1) invites via Facebook direct message.
    """
    sender_facebook_id = models.BigIntegerField(verbose_name='facebook user id of sender', null=True, blank=True)
    recipient_facebook_id = models.BigIntegerField(verbose_name='facebook user id of recipient', null=True, blank=True)
    recipient_facebook_name = models.CharField(
        verbose_name="recipient facebook full name", max_length=255, null=True, blank=True, unique=False)
    facebook_request_id = models.CharField(
        verbose_name="facebook app request id", max_length=255, null=True, blank=True, unique=False)
    invitation_status = models.CharField(max_length=50, choices=INVITATION_STATUS_CHOICES, default=NO_RESPONSE)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    invitation_table = models.CharField(max_length=8, default=FRIEND_INVITATION_FACEBOOK_LINK)
    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendInvitationVoterLink(models.Model):
    """
    Created when voter 1) invites via email (and the email IS recognized), 2) invites via Facebook direct message, or
    3) invites via “friend suggestion” shown on We Vote.
    """
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False, db_index=True)
    sender_email_ownership_is_verified = models.BooleanField(default=False)  # Do we have an email address for sender?
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it",
        max_length=255, null=True, blank=True, unique=False, db_index=True)
    secret_key = models.CharField(
        verbose_name="secret key to accept invite", max_length=255, null=True, blank=True, unique=True)
    invited_friend_accepted_notification_sent = models.BooleanField(default=False)
    invitation_message = models.TextField(null=True, blank=True)
    invitation_status = models.CharField(max_length=50, choices=INVITATION_STATUS_CHOICES, default=NO_RESPONSE)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)
    merge_by_secret_key_allowed = models.BooleanField(default=True)  # To allow merges after delete
    invitation_table = models.CharField(max_length=8, default=FRIEND_INVITATION_VOTER_LINK)

    mutual_friend_count = models.PositiveSmallIntegerField(null=True, unique=False)
    mutual_friend_count_last_updated = models.DateTimeField(null=True)

    mutual_friend_preview_list_serialized = models.TextField(default=None, null=True)
    mutual_friend_preview_list_update_needed = models.BooleanField(default=True)

    deleted = models.BooleanField(default=False)  # If invitation is completed or rescinded, mark as deleted


class FriendManager(models.Manager):

    def __unicode__(self):
        return "FriendManager"

    def update_or_create_friend_invitation_email_link(
            self,
            sender_voter_we_vote_id='',
            recipient_email_we_vote_id='',
            recipient_voter_email='',
            recipient_first_name='',
            recipient_last_name='',
            invitation_message='',
            sender_email_ownership_is_verified=False,
            invitation_secret_key=''):
        status = ""
        defaults = {
            "sender_voter_we_vote_id":          sender_voter_we_vote_id,
            "recipient_email_we_vote_id":       recipient_email_we_vote_id,
            "recipient_voter_email":            recipient_voter_email,
        }
        if positive_value_exists(recipient_first_name):
            defaults["recipient_first_name"] = recipient_first_name
        if positive_value_exists(recipient_last_name):
            defaults["recipient_last_name"] = recipient_last_name
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
            status += "FRIEND_INVITATION_EMAIL_LINK_UPDATED_OR_CREATED "
        except Exception as e:
            friend_invitation_saved = False
            friend_invitation = FriendInvitationEmailLink()
            success = False
            created = False
            status += "FRIEND_INVITATION_EMAIL_LINK_NOT_UPDATED_OR_CREATED " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'friend_invitation_saved':      friend_invitation_saved,
            'friend_invitation_created':    created,
            'friend_invitation':            friend_invitation,
        }
        return results

    def update_or_create_friend_invitation_voter_link(self, sender_voter_we_vote_id, recipient_voter_we_vote_id='',
                                                      invitation_message='', sender_email_ownership_is_verified=False,
                                                      invitation_status=NO_RESPONSE, invitation_secret_key=''):
        status = ""
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
        if positive_value_exists(invitation_status):
            defaults['invitation_status'] = invitation_status
        defaults["deleted"] = False

        try:
            friend_invitation, created = FriendInvitationVoterLink.objects.update_or_create(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                defaults=defaults,
            )
            friend_invitation_saved = True
            success = True
            status += "FRIEND_INVITATION_VOTER_LINK_UPDATED_OR_CREATED "
        except Exception as e:
            friend_invitation_saved = False
            friend_invitation = FriendInvitationVoterLink()
            success = False
            created = False
            status += "FRIEND_INVITATION_VOTER_LINK_NOT_UPDATED_OR_CREATED " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'friend_invitation_saved':      friend_invitation_saved,
            'friend_invitation_created':    created,
            'friend_invitation':            friend_invitation,
        }
        return results

    def update_or_create_friend_invitation_facebook_link(self, facebook_request_id, sender_facebook_id,
                                                         recipient_facebook_id, recipient_facebook_name='',):
        status = ""
        defaults = {
            "facebook_request_id": facebook_request_id,
            "sender_facebook_id": sender_facebook_id,
            "recipient_facebook_id": recipient_facebook_id,
            "recipient_facebook_name":  recipient_facebook_name,
        }

        try:
            friend_invitation, created = FriendInvitationFacebookLink.objects.update_or_create(
                sender_facebook_id=sender_facebook_id,
                recipient_facebook_id=recipient_facebook_id,
                defaults=defaults,
            )
            friend_invitation_saved = True
            success = True
            status += "FRIEND_INVITATION_FACEBOOK_LINK_UPDATED_OR_CREATED "
        except Exception as e:
            friend_invitation_saved = False
            friend_invitation = FriendInvitationFacebookLink()
            success = False
            created = False
            status += "FRIEND_INVITATION_FACEBOOK_LINK_NOT_UPDATED_OR_CREATED " + str(e) + " "

        results = {
            'success': success,
            'status': status,
            'friend_invitation_saved': friend_invitation_saved,
            'friend_invitation_created': created,
            'friend_invitation': friend_invitation,
        }
        return results

    def retrieve_current_friend(self, sender_voter_we_vote_id, recipient_voter_we_vote_id, read_only=True):
        status = ""
        current_friend = CurrentFriend()
        # Note that the direction of the friendship does not matter
        try:
            if positive_value_exists(read_only):
                current_friend = CurrentFriend.objects.using('readonly').get(
                    viewer_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                    viewee_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                )
            else:
                current_friend = CurrentFriend.objects.get(
                    viewer_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                    viewee_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                )
            current_friend_found = True
            success = True
            status += "RETRIEVE_CURRENT_FRIEND_FOUND-1 "
        except CurrentFriend.DoesNotExist:
            # No data found. Try again below
            success = True
            current_friend_found = False
            status += 'RETRIEVE_CURRENT_FRIEND_NOT_FOUND-1 '
        except Exception as e:
            current_friend_found = False
            current_friend = CurrentFriend()
            success = False
            status += "RETRIEVE_CURRENT_FRIEND_ERROR-1 " + str(e) + " "

        if not current_friend_found and success:
            try:
                if positive_value_exists(read_only):
                    current_friend = CurrentFriend.objects.using('readonly').get(
                        viewer_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                        viewee_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                    )
                else:
                    current_friend = CurrentFriend.objects.get(
                        viewer_voter_we_vote_id__iexact=recipient_voter_we_vote_id,
                        viewee_voter_we_vote_id__iexact=sender_voter_we_vote_id,
                    )
                current_friend_found = True
                success = True
                status += "RETRIEVE_CURRENT_FRIEND_FOUND-2 "
            except CurrentFriend.DoesNotExist:
                # No data found. Try again below
                success = True
                current_friend_found = False
                status += 'RETRIEVE_CURRENT_FRIEND_NOT_FOUND-2 '
            except Exception as e:
                current_friend_found = False
                current_friend = CurrentFriend()
                success = False
                status += "RETRIEVE_CURRENT_FRIEND_ERROR-2 " + str(e) + " "

        results = {
            'success': success,
            'status': status,
            'current_friend_found': current_friend_found,
            'current_friend': current_friend,
        }
        return results

    def retrieve_suggested_friend(self, voter_we_vote_id_one, voter_we_vote_id_two, read_only=True):
        status = ""
        suggested_friend = SuggestedFriend()
        # Note that the direction of the friendship does not matter
        try:
            if positive_value_exists(read_only):
                suggested_friend = SuggestedFriend.objects.using('readonly').get(
                    viewer_voter_we_vote_id__iexact=voter_we_vote_id_one,
                    viewee_voter_we_vote_id__iexact=voter_we_vote_id_two,
                )
            else:
                suggested_friend = SuggestedFriend.objects.get(
                    viewer_voter_we_vote_id__iexact=voter_we_vote_id_one,
                    viewee_voter_we_vote_id__iexact=voter_we_vote_id_two,
                )
            suggested_friend_found = True
            success = True
            status += "SUGGESTED_FRIEND_UPDATED_OR_CREATED "
        except SuggestedFriend.DoesNotExist:
            # No data found. Try again below
            success = True
            suggested_friend_found = False
            status += 'NO_SUGGESTED_FRIEND_RETRIEVED_DoesNotExist '
        except Exception as e:
            suggested_friend_found = False
            suggested_friend = SuggestedFriend()
            success = False
            status += "SUGGESTED_FRIEND_NOT_UPDATED_OR_CREATED " + str(e) + " "

        if not suggested_friend_found and success:
            try:
                if positive_value_exists(read_only):
                    suggested_friend = SuggestedFriend.objects.using('readonly').get(
                        viewer_voter_we_vote_id__iexact=voter_we_vote_id_two,
                        viewee_voter_we_vote_id__iexact=voter_we_vote_id_one,
                    )
                else:
                    suggested_friend = SuggestedFriend.objects.get(
                        viewer_voter_we_vote_id__iexact=voter_we_vote_id_two,
                        viewee_voter_we_vote_id__iexact=voter_we_vote_id_one,
                    )
                suggested_friend_found = True
                success = True
                status += "SUGGESTED_FRIEND_UPDATED_OR_CREATED "
            except SuggestedFriend.DoesNotExist:
                # No data found. Try again below
                success = True
                suggested_friend_found = False
                status += 'NO_SUGGESTED_FRIEND_RETRIEVED2_DoesNotExist '
            except Exception as e:
                suggested_friend_found = False
                suggested_friend = SuggestedFriend()
                success = False
                status += "SUGGESTED_FRIEND_NOT_UPDATED_OR_CREATED " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'suggested_friend_found':   suggested_friend_found,
            'suggested_friend':         suggested_friend,
        }
        return results

    def update_or_create_current_friend(
            self,
            sender_voter_we_vote_id,
            recipient_voter_we_vote_id,
            sender_organization_we_vote_id=None,
            recipient_organization_we_vote_id=None):
        status = ""
        if not positive_value_exists(sender_voter_we_vote_id) or not positive_value_exists(recipient_voter_we_vote_id):
            current_friend = CurrentFriend()
            results = {
                'success':                  False,
                'status':                   "ONE_OR_MORE_FRIEND_NOT_A_VALID_VALUE ",
                'current_friend_found':     False,
                'current_friend_created':   False,
                'current_friend':           current_friend,
            }
            return results

        if sender_voter_we_vote_id == recipient_voter_we_vote_id:
            current_friend = CurrentFriend()
            results = {
                'success':                  False,
                'status':                   "BOTH_FRIEND_ENTRIES_ARE_THE_SAME ",
                'current_friend_found':     False,
                'current_friend_created':   False,
                'current_friend':           current_friend,
            }
            return results

        current_friend_created = False

        results = self.retrieve_current_friend(sender_voter_we_vote_id, recipient_voter_we_vote_id, read_only=False)
        current_friend_found = results['current_friend_found']
        current_friend = results['current_friend']
        success = results['success']
        status += results['status']

        if current_friend_found:
            if positive_value_exists(sender_organization_we_vote_id) \
                    or positive_value_exists(recipient_organization_we_vote_id):
                # Update current friend
                try:
                    current_friend.viewer_organization_we_vote_id = sender_organization_we_vote_id
                    current_friend.viewee_organization_we_vote_id = recipient_organization_we_vote_id
                    current_friend.save()
                    current_friend_created = True
                    success = True
                    status += "CURRENT_FRIEND_UPDATED "
                except Exception as e:
                    current_friend_created = False
                    current_friend = CurrentFriend()
                    success = False
                    status += "CURRENT_FRIEND_NOT_UPDATED " + str(e) + " "
        else:
            try:
                current_friend = CurrentFriend.objects.create(
                    viewer_voter_we_vote_id=sender_voter_we_vote_id,
                    viewee_voter_we_vote_id=recipient_voter_we_vote_id,
                    viewer_organization_we_vote_id=sender_organization_we_vote_id,
                    viewee_organization_we_vote_id=recipient_organization_we_vote_id,
                )
                current_friend_created = True
                success = True
                status += "CURRENT_FRIEND_CREATED "
            except Exception as e:
                current_friend_created = False
                current_friend = CurrentFriend()
                success = False
                status += "CURRENT_FRIEND_NOT_CREATED " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'current_friend_found':     current_friend_found,
            'current_friend_created':   current_friend_created,
            'current_friend':           current_friend,
        }
        return results

    def update_or_create_suggested_friend(self, sender_voter_we_vote_id, recipient_voter_we_vote_id):
        status = ""
        if not positive_value_exists(sender_voter_we_vote_id) or not positive_value_exists(recipient_voter_we_vote_id):
            suggested_friend = SuggestedFriend()
            results = {
                'success':                  False,
                'status':                   "ONE_OR_MORE_SUGGESTED_FRIEND_NOT_A_VALID_VALUE ",
                'suggested_friend_found':   False,
                'suggested_friend_created': False,
                'suggested_friend':         suggested_friend,
            }
            return results

        if sender_voter_we_vote_id == recipient_voter_we_vote_id:
            suggested_friend = SuggestedFriend()
            results = {
                'success':                  False,
                'status':                   "BOTH_SUGGESTED_FRIEND_ENTRIES_ARE_THE_SAME ",
                'suggested_friend_found':   False,
                'suggested_friend_created': False,
                'suggested_friend':         suggested_friend,
            }
            return results

        suggested_friend_created = False

        results = self.retrieve_suggested_friend(voter_we_vote_id_one=sender_voter_we_vote_id,
                                                 voter_we_vote_id_two=recipient_voter_we_vote_id)
        suggested_friend_found = results['suggested_friend_found']
        suggested_friend = results['suggested_friend']
        success = results['success']
        status += results['status']

        if suggested_friend_found:
            # We don't need to actually do anything
            pass
        else:
            try:
                suggested_friend = SuggestedFriend.objects.create(
                    viewer_voter_we_vote_id=sender_voter_we_vote_id,
                    viewee_voter_we_vote_id=recipient_voter_we_vote_id,
                )
                suggested_friend_created = True
                success = True
                status += "SUGGESTED_FRIEND_CREATED "
            except Exception as e:
                suggested_friend_created = False
                suggested_friend = SuggestedFriend()
                success = False
                status += "SUGGESTED_FRIEND_NOT_CREATED " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'suggested_friend_found':   suggested_friend_found,
            'suggested_friend_created': suggested_friend_created,
            'suggested_friend':         suggested_friend,
        }
        return results

    def process_friend_invitation_voter_response(self, sender_voter, recipient_voter, kind_of_invite_response):
        # Find the invite from sender_voter (who issued this invitation) to the recipient_voter (who is responding)
        # 1) invite found
        # 2) invite NOT found
        # If 2, check for an invite to this voter's email (from before the email was linked to voter)
        # TODO: If 2, check to see if these two are already friends so we can return success if
        #  kind_of_invite_response == ACCEPT_INVITATION

        status = ""
        friend_invitation_accepted = False
        friend_invitation_deleted = False
        friend_invitation_saved = False

        friend_invitation_voter_link = FriendInvitationVoterLink()
        try:
            friend_invitation_voter_link = FriendInvitationVoterLink.objects.get(
                sender_voter_we_vote_id__iexact=sender_voter.we_vote_id,
                recipient_voter_we_vote_id__iexact=recipient_voter.we_vote_id,
            )
            success = True
            friend_invitation_found = True
            status += 'FRIEND_INVITATION_RETRIEVED '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_found = False
            status += 'NO_FRIEND_INVITATION_RETRIEVED_DoesNotExist '
        except Exception as e:
            success = False
            friend_invitation_found = False
            status += 'FAILED process_friend_invitation_voter_response FriendInvitationVoterLink ' + str(e) + " "

        if friend_invitation_found:
            if kind_of_invite_response == ACCEPT_INVITATION:
                # Create a CurrentFriend entry
                friend_manager = FriendManager()
                results = friend_manager.update_or_create_current_friend(
                    sender_voter.we_vote_id,
                    recipient_voter.we_vote_id,
                    sender_voter.linked_organization_we_vote_id,
                    recipient_voter.linked_organization_we_vote_id)
                success = results['success']
                status += results['status']

                friend_manager.update_suggested_friends_starting_with_one_voter(sender_voter.we_vote_id)
                friend_manager.update_suggested_friends_starting_with_one_voter(recipient_voter.we_vote_id)

                if results['current_friend_created']:
                    friend_invitation_accepted = True

                # And then delete the friend_invitation_voter_link
                if results['current_friend_found'] or results['current_friend_created']:
                    try:
                        friend_invitation_voter_link.deleted = True
                        friend_invitation_voter_link.secret_key = None
                        friend_invitation_voter_link.save()
                        friend_invitation_deleted = True
                        status += "ACCEPT_INVITATION-DELETED"
                        # Update the SuggestedFriend entry to show that an invitation was accepted
                        defaults = {
                            'current_friends': True,
                        }
                        suggested_results = self.update_suggested_friend(
                            voter_we_vote_id=sender_voter.we_vote_id, other_voter_we_vote_id=recipient_voter.we_vote_id,
                            defaults=defaults)
                        status += suggested_results['status']
                    except Exception as e:
                        friend_invitation_deleted = False
                        success = False
                        status += 'FAILED process_friend_invitation_voter_response ACCEPT_INVITATION ' \
                                  '' + str(e) + " "
            elif kind_of_invite_response == IGNORE_INVITATION:
                try:
                    friend_invitation_voter_link.invitation_status = IGNORED
                    friend_invitation_voter_link.secret_key = None
                    friend_invitation_voter_link.save()
                    friend_invitation_saved = True
                    success = True
                    status += 'IGNORE_INVITATION-CURRENT_FRIEND_INVITATION_VOTER_LINK_STATUS_UPDATED_TO_IGNORE '
                    # Update the SuggestedFriend entry to show that the signed in voter doesn't want to be friends
                    defaults = {
                        'voter_we_vote_id_deleted': recipient_voter.we_vote_id,
                    }
                    suggested_results = self.update_suggested_friend(
                        voter_we_vote_id=sender_voter.we_vote_id, other_voter_we_vote_id=recipient_voter.we_vote_id,
                        defaults=defaults)
                    status += suggested_results['status']
                except Exception as e:
                    friend_invitation_saved = False
                    success = False
                    status += 'FAILED process_friend_invitation_voter_response IGNORE_INVITATION ' \
                              '' + str(e) + " "
            elif kind_of_invite_response == DELETE_INVITATION_VOTER_SENT_BY_ME:
                try:
                    friend_invitation_voter_link.deleted = True
                    friend_invitation_voter_link.secret_key = None
                    friend_invitation_voter_link.save()
                    friend_invitation_saved = True
                    success = True
                    status += 'DELETE_INVITATION_VOTER_SENT_BY_ME_DELETED '
                    # Update the SuggestedFriend entry to show that an invitation was canceled
                    defaults = {
                        'friend_invite_sent': False,
                    }
                    suggested_results = self.update_suggested_friend(
                        voter_we_vote_id=sender_voter.we_vote_id, other_voter_we_vote_id=recipient_voter.we_vote_id,
                        defaults=defaults)
                    status += suggested_results['status']
                except Exception as e:
                    friend_invitation_saved = False
                    success = False
                    status += 'FAILED process_friend_invitation_voter_response DELETE_INVITATION_VOTER_SENT_BY_ME ' \
                              '' + str(e) + " "
            else:
                success = False
                status += 'CURRENT_FRIEND_INVITATION_KIND_OF_INVITE_RESPONSE_NOT_SUPPORTED '

        results = {
            'success':                      success,
            'status':                       status,
            'sender_voter_we_vote_id':      sender_voter.we_vote_id,
            'recipient_voter_we_vote_id':   recipient_voter.we_vote_id,
            'friend_invitation_found':      friend_invitation_found,
            'friend_invitation_deleted':    friend_invitation_deleted,
            'friend_invitation_saved':      friend_invitation_saved,
            'friend_invitation_accepted':   friend_invitation_accepted,
        }
        return results

    def process_friend_invitation_email_response(self, sender_voter, recipient_voter_email, kind_of_invite_response):
        # Find the invite from other_voter (who issued this invitation) to the voter (who is responding)
        # 1) invite found
        # 2) invite NOT found
        status = ""

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
            status += 'FRIEND_INVITATION_EMAIL_RETRIEVED '
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_found = False
            status += 'NO_FRIEND_INVITATION_EMAIL_RETRIEVED_DoesNotExist '
        except Exception as e:
            success = False
            friend_invitation_found = False
            status += 'FAILED process_friend_invitation_email_response FriendInvitationEmailLink ' + str(e) + ' '

        if friend_invitation_found:
            if kind_of_invite_response == DELETE_INVITATION_EMAIL_SENT_BY_ME:
                try:
                    friend_invitation_email_link.deleted = True
                    friend_invitation_email_link.secret_key = None
                    friend_invitation_email_link.save()
                    friend_invitation_deleted = True
                    success = True
                    status += 'FRIEND_INVITATION_EMAIL_DELETED '
                except Exception as e:
                    friend_invitation_deleted = False
                    success = False
                    status += 'FAILED process_friend_invitation_email_response delete FriendInvitationEmailLink ' \
                              '' + str(e) + ' '
            else:
                success = False
                status += 'PROCESS_FRIEND_INVITATION_EMAIL_KIND_OF_INVITE_RESPONSE_NOT_SUPPORTED '

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

    def fetch_current_friends_count(self, voter_we_vote_id):
        current_friends_count = 0

        if not positive_value_exists(voter_we_vote_id):
            return current_friends_count

        try:
            current_friend_queryset = CurrentFriend.objects.using('readonly').all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friends_count = current_friend_queryset.count()
        except Exception as e:
            current_friends_count = 0
        return current_friends_count

    def fetch_mutual_friends_voter_we_vote_id_list_from_current_friends(
            self,
            voter_we_vote_id='',
            friend_voter_we_vote_id=''):
        """
        TODO: This could be converted to database only calculation for better speed
        :param voter_we_vote_id:
        :param friend_voter_we_vote_id:
        :return:
        """
        mutual_friends_voter_we_vote_id_list = []

        if not positive_value_exists(voter_we_vote_id) or not positive_value_exists(friend_voter_we_vote_id):
            return mutual_friends_voter_we_vote_id_list

        voter_friends_we_vote_id_list = []
        friend_friends_we_vote_id_list = []

        try:
            voter_friends_queryset = CurrentFriend.objects.using('readonly').all()
            voter_friends_queryset = voter_friends_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            voter_friends_list = list(voter_friends_queryset)
            for one_friend in voter_friends_list:
                voter_friends_we_vote_id_list.append(one_friend.fetch_other_voter_we_vote_id(voter_we_vote_id))
        except Exception as e:
            mutual_friends_count = 0
            return mutual_friends_count

        try:
            friend_friends_queryset = CurrentFriend.objects.using('readonly').all()
            friend_friends_queryset = friend_friends_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=friend_voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=friend_voter_we_vote_id))
            friend_friends_list = list(friend_friends_queryset)
            for one_friend in friend_friends_list:
                friend_friends_we_vote_id_list.append(one_friend.fetch_other_voter_we_vote_id(friend_voter_we_vote_id))
        except Exception as e:
            mutual_friends_voter_we_vote_id_list = []
            return mutual_friends_voter_we_vote_id_list

        voter_set = set(voter_friends_we_vote_id_list)
        friend_set = set(friend_friends_we_vote_id_list)
        mutual_set = voter_set & friend_set
        mutual_friends_voter_we_vote_id_list = list(mutual_set)
        return mutual_friends_voter_we_vote_id_list

    def fetch_mutual_friends_count_from_current_friends(self, voter_we_vote_id='', friend_voter_we_vote_id=''):
        mutual_friends_count = 0
        mutual_friends_voter_we_vote_id_list = \
            self.fetch_mutual_friends_voter_we_vote_id_list_from_current_friends(
                voter_we_vote_id, friend_voter_we_vote_id)

        if mutual_friends_voter_we_vote_id_list:
            mutual_friends_count = len(mutual_friends_voter_we_vote_id_list)

        return mutual_friends_count

    def fetch_suggested_friends_count(self, voter_we_vote_id):
        suggested_friends_count = 0

        if not positive_value_exists(voter_we_vote_id):
            return suggested_friends_count

        try:
            suggested_friend_queryset = SuggestedFriend.objects.using('readonly').all()
            suggested_friend_queryset = suggested_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            suggested_friends_count = suggested_friend_queryset.count()
        except Exception as e:
            suggested_friends_count = 0
        return suggested_friends_count

    def retrieve_current_friend_list(self, voter_we_vote_id, read_only=True):
        status = ""
        current_friend_list = []  # The entries from CurrentFriend table
        current_friend_list_found = False

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
                'voter_we_vote_id':             voter_we_vote_id,
                'current_friend_list_found':    current_friend_list_found,
                'current_friend_list':          current_friend_list,
            }
            return results

        try:
            if positive_value_exists(read_only):
                current_friend_queryset = CurrentFriend.objects.using('readonly').all()
            else:
                current_friend_queryset = CurrentFriend.objects.all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friend_queryset = current_friend_queryset.order_by('-date_last_changed')
            current_friend_list = list(current_friend_queryset)

            if len(current_friend_list):
                success = True
                current_friend_list_found = True
                status += 'CURRENT_FRIEND_LIST_RETRIEVED '
            else:
                success = True
                current_friend_list_found = False
                status += 'NO_CURRENT_FRIEND_LIST_RETRIEVED '
        except CurrentFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            current_friend_list_found = False
            status += 'NO_CURRENT_FRIEND_LIST_RETRIEVED_DoesNotExist '
            current_friend_list = []
        except Exception as e:
            success = False
            current_friend_list_found = False
            status += 'FAILED retrieve_current_friend_list: ' + str(e) + " "
            current_friend_list = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_we_vote_id':             voter_we_vote_id,
            'current_friend_list_found':    current_friend_list_found,
            'current_friend_list':          current_friend_list,
        }
        return results

    def retrieve_current_friends_as_voters(self, voter_we_vote_id, read_only=True):
        """
        This function is used to return the current friends of the viewer as a list of voters via the api.
        :param voter_we_vote_id:
        :param read_only:
        :return:
        """
        status = ""
        current_friend_list = []  # The entries from CurrentFriend table
        friend_list_found = False
        friend_list = []  # A list of friends, returned as voter entries

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':              success,
                'status':               status,
                'voter_we_vote_id':     voter_we_vote_id,
                'friend_list_found':    friend_list_found,
                'friend_list':          friend_list,
            }
            return results

        try:
            # Note that since we are ultimately returning a list of voter objects, so we don't need to retrieve
            # editable CurrentFriend objects.
            current_friend_queryset = CurrentFriend.objects.using('readonly').all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            # We can sort on the client
            # current_friend_queryset = current_friend_queryset.order_by('-date_last_changed')
            current_friend_list = list(current_friend_queryset)

            if len(current_friend_list):
                success = True
                current_friend_list_found = True
                status += 'AS_VOTERS_FRIEND_LIST_RETRIEVED '
            else:
                success = True
                current_friend_list_found = False
                status += 'AS_VOTERS_NO_FRIEND_LIST_RETRIEVED '
        except CurrentFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            current_friend_list_found = False
            status += 'AS_VOTERS_NO_FRIEND_LIST_RETRIEVED_DoesNotExist '
            friend_list = []
        except Exception as e:
            success = False
            current_friend_list_found = False
            status += 'AS_VOTERS_FAILED retrieve_current_friends_as_voters ' + str(e) + " "

        if current_friend_list_found:
            current_friend_dict = {}
            current_friend_voter_we_vote_id_list = []
            for current_friend_entry in current_friend_list:
                we_vote_id_of_friend = current_friend_entry.fetch_other_voter_we_vote_id(voter_we_vote_id)
                current_friend_voter_we_vote_id_list.append(we_vote_id_of_friend)
                current_friend_dict[we_vote_id_of_friend] = current_friend_entry
            voter_manager = VoterManager()
            results = voter_manager.retrieve_voter_list_by_we_vote_id_list(
                voter_we_vote_id_list=current_friend_voter_we_vote_id_list,
                read_only=read_only)
            if results['voter_list_found']:
                friend_list = []
                raw_friend_list = results['voter_list']
                friend_list_found = True
                # Augment friend_list with mutual_friend data
                for one_voter in raw_friend_list:
                    if one_voter.we_vote_id in current_friend_dict:
                        current_friend = current_friend_dict[one_voter.we_vote_id]
                        one_voter.mutual_friend_count = current_friend.mutual_friend_count
                        if current_friend.mutual_friend_preview_list_serialized:
                            mutual_friend_preview_list = \
                                json.loads(current_friend.mutual_friend_preview_list_serialized)
                        else:
                            mutual_friend_preview_list = []
                        one_voter.mutual_friend_preview_list = mutual_friend_preview_list
                    friend_list.append(one_voter)

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
        This is similar to retrieve_current_friend_list, but only returns the we_vote_id
        :param voter_we_vote_id:
        :return:
        """
        status = ""
        current_friend_list_found = False
        current_friend_list = []  # The entries from CurrentFriend table
        friends_we_vote_id_list_found = False
        friends_we_vote_id_list = []  # A list of friends, returned as we_vote_id's

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                          success,
                'status':                           status,
                'voter_we_vote_id':                 voter_we_vote_id,
                'friends_we_vote_id_list_found':    friends_we_vote_id_list_found,
                'friends_we_vote_id_list':          friends_we_vote_id_list,
            }
            return results

        try:
            current_friend_queryset = CurrentFriend.objects.using('readonly').all()
            current_friend_queryset = current_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friend_queryset = current_friend_queryset.order_by('-date_last_changed')
            current_friend_list = current_friend_queryset

            if len(current_friend_list):
                success = True
                current_friend_list_found = True
                status += 'FRIEND_LIST_RETRIEVED-WE_VOTE_IDS '
            else:
                success = True
                current_friend_list_found = False
                status += 'NO_FRIEND_LIST_RETRIEVED-WE_VOTE_IDS '
        except CurrentFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            current_friend_list_found = False
            status += 'NO_FRIEND_LIST_RETRIEVED_DoesNotExist-WE_VOTE_IDS '
            friends_we_vote_id_list = []
        except Exception as e:
            success = False
            current_friend_list_found = False
            status += 'FAILED retrieve_friends_we_vote_id_list-WE_VOTE_IDS ' + str(e) + " "

        if current_friend_list_found:
            for current_friend_entry in current_friend_list:
                if current_friend_entry.viewer_voter_we_vote_id == voter_we_vote_id:
                    we_vote_id_of_friend = current_friend_entry.viewee_voter_we_vote_id
                else:
                    we_vote_id_of_friend = current_friend_entry.viewer_voter_we_vote_id
                # This is the voter you are friends with
                if positive_value_exists(we_vote_id_of_friend):
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
            status += 'RETRIEVE_FRIEND_INVITATION_EMAIL_LINK-MISSING_SENDER '
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
            status += ' FAILED retrieve_friend_invitation_email_link_list FriendInvitationVoterLink ' + str(e) + " "

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
            status += 'RETRIEVE_FRIEND_INVITATION_VOTER_LINK-MISSING_BOTH_SENDER_AND_RECIPIENT '
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
            status += 'FAILED retrieve_friend_invitation_voter_link_list FriendInvitationVoterLink ' + str(e) + " "

        results = {
            'success': success,
            'status': status,
            'sender_voter_we_vote_id': sender_voter_we_vote_id,
            'recipient_voter_we_vote_id': recipient_voter_we_vote_id,
            'friend_invitation_list_found': friend_invitation_from_voter_list_found,
            'friend_invitation_list': friend_invitation_from_voter_list,
        }
        return results

    def delete_friend_invitation_voter_link(self, id=0):
        status = ""

        if not positive_value_exists(id):
            success = False
            status += 'DELETE_FRIEND_INVITATION_VOTER_LINK-MISSING_UNIQUE_ID '
            results = {
                'success':                              success,
                'status':                               status,
                'friend_invitation_voter_link_found':   False,
                'friend_invitation_voter_link_deleted': False,
            }
            return results

        try:
            FriendInvitationVoterLink.objects.filter(id=id).update(deleted=True, secret_key=None)
            success = True
            friend_invitation_voter_link_found = True
            friend_invitation_voter_link_deleted = True
            status += 'DELETE_FRIEND_INVITATION_VOTER_LINK-SUCCESS '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_invitation_voter_link_found = False
            friend_invitation_voter_link_deleted = False
            status += 'DELETE_FRIEND_INVITATION_VOTER_LINK-DoesNotExist '
            friend_invitation_from_voter_list = []
        except Exception as e:
            success = False
            friend_invitation_voter_link_found = False
            friend_invitation_voter_link_deleted = False
            status += 'FAILED DELETE_FRIEND_INVITATION_VOTER_LINK: ' + str(e) + " "

        results = {
            'success': success,
            'status': status,
            'friend_invitation_voter_link_found': friend_invitation_voter_link_found,
            'friend_invitation_voter_link_deleted': friend_invitation_voter_link_deleted,
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
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
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
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(deleted=False)
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
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationVoterLink ' + str(e) + " "

        friend_invitation_from_email_list = []
        try:
            # Find invitations that I sent that were accepted. Do NOT show invitations that were ignored.
            friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                sender_voter_we_vote_id__iexact=viewer_voter_we_vote_id)
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(invitation_status=ACCEPTED)
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(deleted=False)
            friend_invitation_email_queryset = friend_invitation_email_queryset.order_by('-date_last_changed')
            friend_invitation_from_email_list = friend_invitation_email_queryset
            success = True

            if len(friend_invitation_from_email_list):
                status += 'FRIEND_INVITATIONS_PROCESSED-FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED '
                friend_invitation_from_email_list_found = True
            else:
                status += 'FRIEND_INVITATIONS_PROCESSED-NO_FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED '
                friend_invitation_from_email_list_found = False
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            friend_invitation_from_email_list_found = False
            status += 'FRIEND_INVITATIONS_PROCESSED-NO_FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED_DoesNotExist '
        except Exception as e:
            friend_invitation_from_email_list_found = False
            status += 'FRIEND_INVITATIONS_PROCESSED-FAILED retrieve_friend_invitations_processed ' \
                      'FriendInvitationEmailLink ' + str(e) + " "

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
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(deleted=False)
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
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationVoterLink ' + str(e) + " "

        friend_invitation_to_email_list = []
        friend_invitation_to_email_list_found = False
        try:
            # Cycle through all the viewer_voter_we_vote_id email addresses so we can retrieve invitations sent
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
        except Exception as e:
            viewer_voter_emails_found = False
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationEmailLink ' + str(e) + ' '

        if viewer_voter_emails_found and len(final_filters):
            try:
                # Find invitations that were sent to one of my email addresses
                friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
                friend_invitation_email_queryset = friend_invitation_email_queryset.filter(final_filters)
                friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                    Q(invitation_status=ACCEPTED) |
                    Q(invitation_status=IGNORED))
                friend_invitation_email_queryset = friend_invitation_email_queryset.filter(deleted=False)
                friend_invitation_email_queryset = friend_invitation_email_queryset.order_by('-date_last_changed')
                friend_invitation_to_email_list = friend_invitation_email_queryset
                success = True

                if len(friend_invitation_to_email_list):
                    status += ' FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED '
                    friend_invitation_to_email_list_found = True
                else:
                    status += ' NO_FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED '
                    friend_invitation_to_email_list_found = False
            except FriendInvitationEmailLink.DoesNotExist:
                # No data found. Not a problem.
                friend_invitation_to_email_list_found = False
                status += 'NO_FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED_DoesNotExist '
            except Exception as e:
                friend_invitation_to_email_list_found = False
                status += 'FAILED retrieve_friend_invitations_processed FriendInvitationEmailLink ' + str(e) + " "

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

    def fetch_friend_invitations_sent_by_me_count(self, voter_we_vote_id):
        results = self.retrieve_friend_invitations_sent_by_me(voter_we_vote_id)
        if results['friend_list_found']:
            friend_list = results['friend_list']
            return len(friend_list)
        return 0

    def fetch_friend_invitations_sent_by_me_we_vote_id_list(self, sender_voter_we_vote_id):
        results = self.retrieve_friend_invitations_sent_by_me(sender_voter_we_vote_id)
        we_vote_id_list = []
        if results['friend_list_found']:
            friend_list = results['friend_list']
            for friend_invitation in friend_list:
                if hasattr(friend_invitation, "recipient_voter_we_vote_id"):
                    we_vote_id_list.append(friend_invitation.recipient_voter_we_vote_id)
        return we_vote_id_list

    def retrieve_friend_invitations_sent_by_me(self, sender_voter_we_vote_id):
        status = ""
        friend_list_found = False
        friend_list = []

        if not positive_value_exists(sender_voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
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
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                invitation_status__iexact=ACCEPTED)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                invitation_status__iexact=IGNORED)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.order_by('-date_last_changed')
            friend_list = friend_invitation_voter_queryset

            if len(friend_list):
                success = True
                friend_list_found = True
                status += 'FRIEND_INVITATION_VOTER_LINK-SENT_BY_ME '
            else:
                success = True
                friend_list_found = False
                status += 'NO_FRIEND_INVITATION_VOTER_LINK-SENT_BY_ME '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_list_found = False
            status += 'NO_FRIEND_INVITATION_VOTER_LINK_DoesNotExist-SENT_BY_ME '
            friend_list = []
        except Exception as e:
            success = False
            friend_list_found = False
            status += 'FAILED retrieve_friend_invitations_processed FriendInvitationVoterLink-SENT_BY_ME ' \
                      '' + str(e) + ' '

        friend_list_email = []
        try:
            friend_invitation_email_queryset = FriendInvitationEmailLink.objects.all()
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(
                sender_voter_we_vote_id__iexact=sender_voter_we_vote_id)
            friend_invitation_email_queryset = friend_invitation_email_queryset.filter(deleted=False)
            friend_invitation_email_queryset = friend_invitation_email_queryset.exclude(
                invitation_status__iexact=ACCEPTED)
            friend_invitation_email_queryset = friend_invitation_email_queryset.exclude(
                invitation_status__iexact=IGNORED)
            friend_invitation_email_queryset = friend_invitation_email_queryset.order_by('-date_last_changed')
            friend_list_email = friend_invitation_email_queryset
            success = True

            if len(friend_list_email):
                status += ' FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED-SENT_BY_ME'
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
                status += ' NO_FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED-SENT_BY_ME'
                friend_list_email_found = False
        except FriendInvitationEmailLink.DoesNotExist:
            # No data found. Not a problem.
            friend_list_email_found = False
            status += 'NO_FRIEND_INVITATION_EMAIL_LINK_LIST_RETRIEVED-SENT_BY_ME_DoesNotExist '
        except Exception as e:
            friend_list_email_found = False
            status += 'FAILED-SENT_BY_ME retrieve_friend_invitations_sent_by_me FriendInvitationEmailLink: ' \
                      '' + str(e) + ' '

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

    def fetch_friend_invitations_sent_to_me_count(self, voter_we_vote_id):
        read_only = True
        results = self.retrieve_friend_invitations_sent_to_me(voter_we_vote_id, read_only)
        if results['friend_list_found']:
            friend_list = results['friend_list']
            return len(friend_list)
        return 0

    def fetch_friend_invitations_sent_to_me_we_vote_id_list(self, voter_we_vote_id):
        read_only = True
        results = self.retrieve_friend_invitations_sent_to_me(recipient_voter_we_vote_id=voter_we_vote_id,
                                                              read_only=read_only)
        we_vote_id_list = []
        if results['friend_list_found']:
            friend_list = results['friend_list']
            for friend_invitation in friend_list:
                if hasattr(friend_invitation, "sender_voter_we_vote_id"):
                    we_vote_id_list.append(friend_invitation.sender_voter_we_vote_id)
        return we_vote_id_list

    def fetch_friend_related_voter_we_vote_id_list(self, voter_we_vote_id):
        """
        Find any other voter_we_vote_id related to voter_we_vote_id. Used for maintenance function.
        :param voter_we_vote_id:
        :return:
        """
        status = ''
        success = True

        try:
            queryset = CurrentFriend.objects.using('readonly').all()
            queryset = queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            current_friends_list_one = list(queryset.values_list('viewer_voter_we_vote_id', flat=True).distinct())
            current_friends_list_two = list(queryset.values_list('viewee_voter_we_vote_id', flat=True).distinct())
        except Exception as e:
            current_friends_list_one = []
            current_friends_list_two = []
            status += "CurrentFriend e: " + str(e) + ' '

        try:
            queryset = FriendInvitationVoterLink.objects.using('readonly').all()
            queryset = queryset.filter(recipient_voter_we_vote_id__iexact=voter_we_vote_id)
            queryset = queryset.filter(deleted=False)
            queryset = queryset.exclude(invitation_status__iexact=ACCEPTED)
            queryset = queryset.exclude(invitation_status__iexact=IGNORED)
            friend_invitation_sender_list = list(queryset.values_list('sender_voter_we_vote_id', flat=True).distinct())
        except Exception as e:
            friend_invitation_sender_list = []
            status += "FriendInvitationVoterLink1 e: " + str(e) + ' '

        try:
            queryset = FriendInvitationVoterLink.objects.using('readonly').all()
            queryset = queryset.filter(sender_voter_we_vote_id__iexact=voter_we_vote_id)
            queryset = queryset.filter(deleted=False)
            queryset = queryset.exclude(invitation_status__iexact=ACCEPTED)
            queryset = queryset.exclude(invitation_status__iexact=IGNORED)
            friend_invitation_recipient_list = \
                list(queryset.values_list('recipient_voter_we_vote_id', flat=True).distinct())
        except Exception as e:
            friend_invitation_recipient_list = []
            status += "FriendInvitationVoterLink2 e: " + str(e) + ' '

        try:
            queryset = SuggestedFriend.objects.using('readonly').all()
            queryset = queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            suggested_friends_list_one = list(queryset.values_list('viewer_voter_we_vote_id', flat=True).distinct())
            suggested_friends_list_two = list(queryset.values_list('viewee_voter_we_vote_id', flat=True).distinct())
        except Exception as e:
            suggested_friends_list_one = []
            suggested_friends_list_two = []
            status += "SuggestedFriend e: " + str(e) + ' '

        try:
            friend_related_voter_we_vote_id_list = \
                list(set(current_friends_list_one + current_friends_list_two + friend_invitation_sender_list +
                         friend_invitation_recipient_list + suggested_friends_list_one + suggested_friends_list_two))
        except Exception as e:
            friend_related_voter_we_vote_id_list = []
        return friend_related_voter_we_vote_id_list

    def fetch_voter_friendships_count(self):
        current_friend_count = 0
        try:
            current_friend_count = CurrentFriend.objects.using('readonly').count()
        except Exception as e:
            pass

        return current_friend_count

    # def fetch_voters_with_friends_count(self, this_many_friends_or_more=0):
    #     voters_with_friends_count = 0
    #     if positive_value_exists(this_many_friends_or_more):
    #         # TODO We need to figure out how to count number of voter_we_vote_ids in either column, so we can limit
    #         #  the count of the number of friendships to those voter_we_vote_ids which
    #         #  appear "this_many_friends_or_more" times or more
    #         #  Started Google searching with "django python count distinct"
    #         pass
    #     else:
    #         from django.db.models import F
    #         try:
    #             friends_query = CurrentFriend.objects.using('readonly') \
    #                 .annotate(voter_we_vote_id=F('viewee_voter_we_vote_id')).values_list('voter_we_vote_id', flat=True) \
    #                 .union(
    #                 CurrentFriend.objects.using('readonly')
    #                     .annotate(voter_we_vote_id=F('viewer_voter_we_vote_id'))
    #                     .values_list('voter_we_vote_id', flat=True)
    #             )
    #             voters_with_friends_count = friends_query.count()
    #         except Exception as e:
    #             pass
    #
    #     return voters_with_friends_count

    # Run in the phpPgAdmin console to find the top friendly voters, then change viewer to viewee for the back direction
    # SELECT "viewer_voter_we_vote_id", COUNT("viewer_voter_we_vote_id") FROM "public"."friend_currentfriend"
    #   GROUP BY "viewer_voter_we_vote_id" ORDER BY count DESC;
    def fetch_voters_with_friends_for_graph(self, friendlinks):
        reduced_friendlies = []
        # index    0    1    2    3    4    5    6    7    8      9        10       11     12
        voters = ["2", "3", "4", "5", "6", "7", "8", "9", "10-19", "20-29", "30-39", "40+"]
        counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        try:
            counts[0] = self.get_count_of_friendlinks(friendlinks, "==", 2)
            counts[1] = self.get_count_of_friendlinks(friendlinks, "==", 3)
            counts[2] = self.get_count_of_friendlinks(friendlinks, "==", 4)
            counts[3] = self.get_count_of_friendlinks(friendlinks, "==", 5)
            counts[4] = self.get_count_of_friendlinks(friendlinks, "==", 6)
            counts[5] = self.get_count_of_friendlinks(friendlinks, "==", 7)
            counts[6] = self.get_count_of_friendlinks(friendlinks, "==", 8)
            counts[7] = self.get_count_of_friendlinks(friendlinks, "==", 9)
            counts[8] = self.get_count_of_friendlinks(friendlinks, "range", 10, 19)
            counts[9] = self.get_count_of_friendlinks(friendlinks, "range", 20, 29)
            counts[10] = self.get_count_of_friendlinks(friendlinks, "range", 30, 39)
            counts[11] = self.get_count_of_friendlinks(friendlinks, ">=", 40)

        except Exception as e:
            print("Exception in fetch_voters_with_friends_count_improved", e)
            pass
        voters_json = json.dumps(voters)
        counts_json = json.dumps(counts)

        return voters_json, counts_json

    # def fetch_voters_with_friends_dataset(self):
    #     reduced_friendlies = []
    #     friendlies = []
    #
    #     try:
    #         conn = psycopg2.connect(
    #             database=get_environment_variable('DATABASE_NAME'),
    #             user=get_environment_variable('DATABASE_USER'),
    #             password=get_environment_variable('DATABASE_PASSWORD'),
    #             host=get_environment_variable('DATABASE_HOST'),
    #             port=get_environment_variable('DATABASE_PORT')
    #         )
    #         cur = conn.cursor()
    #         sql_viewer = 'SELECT "viewer_voter_we_vote_id", COUNT("viewer_voter_we_vote_id") FROM ' \
    #                      '"public"."friend_currentfriend" GROUP BY "viewer_voter_we_vote_id" ORDER BY count'
    #         cur.execute(sql_viewer)
    #         viewers = list(cur.fetchall())
    #         # Now the other direction
    #         cur = conn.cursor()  # replace the cursor with a new one
    #         sql_viewee = sql_viewer.replace('viewer', 'viewee')
    #         cur.execute(sql_viewee)
    #         viewees = list(cur.fetchall())
    #         conn.close()
    #         friendlies = sorted(viewers + viewees, key=lambda tup: tup[0])
    #         prior_voter = ''
    #         for voter in friendlies:
    #             if voter[0] != prior_voter:
    #                 reduced_friendlies.append(voter)
    #                 prior_voter = voter[0]
    #             else:
    #                 sumo = voter[1] + reduced_friendlies[len(reduced_friendlies) - 1][1]
    #                 reduced_friendlies[len(reduced_friendlies) - 1] = tuple([prior_voter, sumo])
    #
    #     except Exception as e:
    #         print("Exception in fetch_voters_with_friends_count_improved", e)
    #         pass
    #
    #     return sorted(reduced_friendlies, key=lambda tup: tup[1], reverse=True)

    # https://stackoverflow.com/questions/65764804/count-of-group-of-two-fields-in-sql-query-postgres/65765087#65765087
    def fetch_voters_with_friends_dataset_improved(self):
        friendlies = []

        try:
            conn = psycopg2.connect(
                database=get_environment_variable('DATABASE_NAME'),
                user=get_environment_variable('DATABASE_USER'),
                password=get_environment_variable('DATABASE_PASSWORD'),
                host=get_environment_variable('DATABASE_HOST'),
                port=get_environment_variable('DATABASE_PORT')
            )
            cur = conn.cursor()
            sql_viewer = \
                'SELECT id, COUNT(*) AS we_count FROM ( ' \
                'SELECT viewee_voter_we_vote_id id FROM "public"."friend_currentfriend" ' \
                'UNION ALL ' \
                'SELECT viewer_voter_we_vote_id id FROM "public"."friend_currentfriend") ' \
                'AS throwaway_variable ' \
                'GROUP BY id  ' \
                'ORDER BY COUNT(*) desc'
            cur.execute(sql_viewer)
            friendlies = list(cur.fetchall())

        except Exception as e:
            print("Exception in fetch_voters_with_friends_count_improved", e)
            pass

        return friendlies

    def get_count_of_friendships(self, friendlinks):
        count = 0
        for link in friendlinks:
            count += link[1]
        return count

    def get_count_of_friendlinks(self, friendlinks, comparison, num1, num2=0):
        matches = []
        if comparison == "==":
            matches = list(filter(lambda x: x[1] == num1, friendlinks))
        elif comparison == ">=":
            matches = list(filter(lambda x: x[1] >= num1, friendlinks))
        elif comparison == "range":
            matches = list(filter(lambda x: num1 <= x[1] <= num2, friendlinks))
        else:
            print("Unknown comparison in get_count_of_friendlinks")
        return len(matches)

    def retrieve_friend_invitations_sent_to_me(self, recipient_voter_we_vote_id, read_only=False):
        status = ''
        friend_list_found = False
        friend_list = []

        if not positive_value_exists(recipient_voter_we_vote_id):
            success = False
            status += 'VALID_RECIPIENT_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
                'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
                'friend_list_found':            friend_list_found,
                'friend_list':                  friend_list,
            }
            return results

        try:
            if read_only:
                friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.using('readonly').all()
            else:
                friend_invitation_voter_queryset = FriendInvitationVoterLink.objects.all()
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(
                recipient_voter_we_vote_id__iexact=recipient_voter_we_vote_id)
            # It is possible through account merging to have an invitation to yourself. We want to exclude these.
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                sender_voter_we_vote_id__iexact=recipient_voter_we_vote_id)
            # Exclude accepted invitations, ignored and deleted invitations
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.filter(deleted=False)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                invitation_status__iexact=ACCEPTED)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.exclude(
                invitation_status__iexact=IGNORED)
            friend_invitation_voter_queryset = friend_invitation_voter_queryset.order_by('-date_last_changed')
            friend_list = friend_invitation_voter_queryset

            if len(friend_list):
                success = True
                friend_list_found = True
                status += 'FRIEND_INVITATION_VOTER_LINK-SENT_TO_ME '
            else:
                success = True
                friend_list_found = False
                status += 'NO_FRIEND_INVITATION_VOTER_LINK-SENT_TO_ME '
        except FriendInvitationVoterLink.DoesNotExist:
            # No data found. Not a problem.
            success = True
            friend_list_found = False
            status += 'NO_FRIEND_INVITATION_VOTER_LINK_DoesNotExist-SENT_TO_ME '
            friend_list = []
        except Exception as e:
            success = False
            friend_list_found = False
            status += 'FAILED retrieve_friend_invitations_sent_to_me ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'recipient_voter_we_vote_id':   recipient_voter_we_vote_id,
            'friend_list_found':            friend_list_found,
            'friend_list':                  friend_list,
        }
        return results

    def retrieve_friend_invitation_from_secret_key(
            self,
            invitation_secret_key,
            for_accepting_friendship=False,
            for_additional_processes=False,
            for_merge_accounts=False,
            for_retrieving_information=False,
            read_only=True):
        """

        :param invitation_secret_key:
        :param for_accepting_friendship:
        :param for_additional_processes:
        :param for_merge_accounts:
        :param for_retrieving_information:
        :param read_only:
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
            if positive_value_exists(invitation_secret_key):
                if positive_value_exists(read_only):
                    voter_link_query = FriendInvitationVoterLink.objects.using('readonly').all()
                else:
                    voter_link_query = FriendInvitationVoterLink.objects.all()
                voter_link_query = voter_link_query.filter(secret_key=invitation_secret_key)
                voter_link_query = voter_link_query.filter(deleted=False)
                if positive_value_exists(for_accepting_friendship):
                    voter_link_query = voter_link_query.exclude(invitation_status__iexact=ACCEPTED)
                    status += "FOR_ACCEPTING_FRIENDSHIP "
                elif positive_value_exists(for_additional_processes):
                    voter_link_query = voter_link_query.filter(invitation_status__iexact=ACCEPTED)
                    status += "FOR_ADDITIONAL_PROCESSES "
                elif positive_value_exists(for_merge_accounts):
                    voter_link_query = voter_link_query.filter(merge_by_secret_key_allowed=True)
                    status += "FOR_MERGE_ACCOUNTS "
                elif positive_value_exists(for_retrieving_information):
                    voter_link_query = voter_link_query.filter(invitation_status__iexact=ACCEPTED)
                    status += "FOR_RETRIEVING_INFORMATION "
                voter_link_list = list(voter_link_query)
                if len(voter_link_list) > 0:
                    friend_invitation_voter_link = voter_link_list[0]
                    friend_invitation_voter_link_found = True
                    status += "RETRIEVE_FRIEND_INVITATION_VOTER_LINK_FOUND_BY_SECRET_KEY1 "
                else:
                    friend_invitation_voter_link = None
                    status += "RETRIEVE_FRIEND_INVITATION_VOTER_LINK_BY_SECRET_KEY_NOT_FOUND1 "
                success = True
            else:
                friend_invitation_voter_link_found = False
                success = False
                status += "RETRIEVE_FRIEND_INVITATION_VOTER_LINK_BY_SECRET_KEY_VARIABLES_MISSING1 "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_friend_invitation_from_secret_key FriendInvitationVoterLink ' + str(e) + " "

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
            if positive_value_exists(invitation_secret_key):
                if positive_value_exists(read_only):
                    email_link_query = FriendInvitationEmailLink.objects.using('readonly').all()
                else:
                    email_link_query = FriendInvitationEmailLink.objects.all()
                email_link_query = email_link_query.filter(secret_key=invitation_secret_key)
                email_link_query = email_link_query.filter(deleted=False)
                if positive_value_exists(for_accepting_friendship):
                    email_link_query = email_link_query.exclude(invitation_status__iexact=ACCEPTED)
                    status += "FOR_ACCEPTING_FRIENDSHIP "
                elif positive_value_exists(for_additional_processes):
                    email_link_query = email_link_query.filter(invitation_status__iexact=ACCEPTED)
                    status += "FOR_ADDITIONAL_PROCESSES "
                elif positive_value_exists(for_merge_accounts):
                    email_link_query = email_link_query.filter(merge_by_secret_key_allowed=True)
                    status += "FOR_MERGE_ACCOUNTS "
                elif positive_value_exists(for_retrieving_information):
                    email_link_query = email_link_query.filter(invitation_status__iexact=ACCEPTED)
                    status += "FOR_RETRIEVING_INFORMATION "
                email_link_list = list(email_link_query)
                if len(email_link_list):
                    friend_invitation_email_link = email_link_list[0]
                    friend_invitation_email_link_found = True
                    status += "RETRIEVE_FRIEND_INVITATION_EMAIL_LINK_FOUND_BY_INVITATION_SECRET_KEY2 "
                else:
                    friend_invitation_email_link = None
                    status += "RETRIEVE_FRIEND_INVITATION_EMAIL_LINK_BY_SECRET_KEY_NOT_FOUND2 "
                success = True
            else:
                friend_invitation_email_link_found = False
                success = False
                status += "RETRIEVE_FRIEND_INVITATION_EMAIL_LINK_BY_SECRET_KEY_VARIABLES_MISSING2 "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_friend_invitation_from_secret_key FriendInvitationEmailLink ' + str(e) + ' '

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

    def retrieve_friend_invitation_from_facebook(self, facebook_request_id, recipient_facebook_id,
                                                 sender_facebook_id):
        """

        :param facebook_request_id:
        :param recipient_facebook_id:
        :param sender_facebook_id:
        :return:
        """
        # Start by looking in FriendInvitationFacebookLink table
        friend_invitation_facebook_link_found = False
        friend_invitation_facebook_link = FriendInvitationFacebookLink()
        status = ""

        try:
            friend_invitation_facebook_link = FriendInvitationFacebookLink.objects.get(
                facebook_request_id=facebook_request_id,
                recipient_facebook_id=recipient_facebook_id,
                sender_facebook_id=sender_facebook_id,
            )
            friend_invitation_facebook_link_found = True
            success = True
            status += "RETRIEVE_FRIEND_FACEBOOK_INVITATION_FROM_FACEBOOK_FOUND "
        except FriendInvitationVoterLink.DoesNotExist:
            success = True
            status += "RETRIEVE_FRIEND_INVITATION_FROM_FACEBOOK_NOT_FOUND1 "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_friend_invitation_from_facebook FriendInvitationFacebookLink ' + str(e) + ' '

        results = {
            'success':                                  success,
            'status':                                   status,
            'friend_invitation_facebook_link_found':    friend_invitation_facebook_link_found,
            'friend_invitation_facebook_link':          friend_invitation_facebook_link
        }
        return results

    def retrieve_mutual_friend_list(
            self,
            first_friend_voter_we_vote_id='',
            second_friend_voter_we_vote_id='',
            mutual_friend_voter_we_vote_id='',
            read_only=True):
        status = ""
        success = True
        mutual_friend_list = []  # The entries from MutualFriend table
        mutual_friend_list_found = False

        if positive_value_exists(first_friend_voter_we_vote_id) and \
                positive_value_exists(second_friend_voter_we_vote_id):
            pass
        elif positive_value_exists(mutual_friend_voter_we_vote_id):
            pass
        else:
            success = False
            status += 'RETRIEVE_MUTUAL_FRIEND_LIST_MISSING_KEY_VARIABLE '
            results = {
                'success':                  success,
                'status':                   status,
                'mutual_friend_list_found': mutual_friend_list_found,
                'mutual_friend_list':       mutual_friend_list,
            }
            return results

        try:
            if positive_value_exists(read_only):
                queryset = MutualFriend.objects.using('readonly').all()
            else:
                queryset = MutualFriend.objects.all()
            if positive_value_exists(first_friend_voter_we_vote_id):
                queryset = queryset.filter(
                    Q(viewer_voter_we_vote_id__iexact=first_friend_voter_we_vote_id) |
                    Q(viewee_voter_we_vote_id__iexact=first_friend_voter_we_vote_id))
            if positive_value_exists(second_friend_voter_we_vote_id):
                queryset = queryset.filter(
                    Q(viewer_voter_we_vote_id__iexact=second_friend_voter_we_vote_id) |
                    Q(viewee_voter_we_vote_id__iexact=second_friend_voter_we_vote_id))
            if positive_value_exists(mutual_friend_voter_we_vote_id):
                queryset = queryset.filter(
                    mutual_friend_voter_we_vote_id=mutual_friend_voter_we_vote_id,
                )
            queryset = queryset.order_by('-date_last_changed')
            mutual_friend_list = list(queryset)

            if len(mutual_friend_list):
                mutual_friend_list_found = True
                status += 'MUTUAL_FRIEND_LIST_RETRIEVED '
            else:
                mutual_friend_list_found = False
                status += 'NO_MUTUAL_FRIEND_LIST_RETRIEVED '
        except Exception as e:
            success = False
            mutual_friend_list_found = False
            status += 'FAILED retrieve_mutual_friend_list: ' + str(e) + " "
            mutual_friend_list = []

        results = {
            'success':                  success,
            'status':                   status,
            'mutual_friend_list_found': mutual_friend_list_found,
            'mutual_friend_list':       mutual_friend_list,
        }
        return results

    def unfriend_current_friend(self, acting_voter_we_vote_id, other_voter_we_vote_id):
        # Retrieve the existing friendship
        status = ""
        success = False

        results = self.retrieve_current_friend(acting_voter_we_vote_id, other_voter_we_vote_id, read_only=False)
        if not results['success']:
            status += results['status']

        status += 'PREPARING_TO_DELETE_CURRENT_FRIEND '
        current_friend_deleted = False

        if results['current_friend_found']:
            current_friend = results['current_friend']
            try:
                current_friend.delete()
                current_friend_deleted = True
                success = True
                status += 'CURRENT_FRIEND_DELETED '
                # Update the SuggestedFriend entry to show that the friend was unfriended, which implies the
                # acting_voter_we_vote_id doesn't want to see this person as a SuggestedFriend
                defaults = {
                    'current_friends': False,
                    'friend_invite_sent': False,
                    'voter_we_vote_id_deleted': acting_voter_we_vote_id,
                }
                suggested_results = self.update_suggested_friend(
                    voter_we_vote_id=acting_voter_we_vote_id, other_voter_we_vote_id=other_voter_we_vote_id,
                    defaults=defaults)
                status += suggested_results['status']
            except Exception as e:
                success = False
                current_friend_deleted = False
                status += 'FAILED unfriend_current_friend ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'acting_voter_we_vote_id':      acting_voter_we_vote_id,
            'other_voter_we_vote_id':       other_voter_we_vote_id,
            'current_friend_deleted':       current_friend_deleted,
        }
        return results

    def retrieve_suggested_friend_list(self, voter_we_vote_id, hide_deleted=True, read_only=True):
        """
        A list of SuggestedFriend table entries.
        :param voter_we_vote_id:
        :param hide_deleted:
        :param read_only:
        :return:
        """
        status = ''
        suggested_friend_list = []  # The entries from SuggestedFriend table
        suggested_friend_list_found = False

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                      success,
                'status':                       status,
                'voter_we_vote_id':             voter_we_vote_id,
                'suggested_friend_list_found':    suggested_friend_list_found,
                'suggested_friend_list':          suggested_friend_list,
            }
            return results

        try:
            if positive_value_exists(read_only):
                suggested_friend_queryset = SuggestedFriend.objects.using('readonly').all()
            else:
                suggested_friend_queryset = SuggestedFriend.objects.all()
            suggested_friend_queryset = suggested_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            if positive_value_exists(hide_deleted):
                suggested_friend_queryset = suggested_friend_queryset.exclude(
                    Q(voter_we_vote_id_deleted_first__iexact=voter_we_vote_id) |
                    Q(voter_we_vote_id_deleted_second__iexact=voter_we_vote_id))
                suggested_friend_queryset = suggested_friend_queryset.exclude(friend_invite_sent=True)
                suggested_friend_queryset = suggested_friend_queryset.exclude(current_friends=True)
            suggested_friend_queryset = suggested_friend_queryset.order_by('-date_last_changed')
            suggested_friend_list = suggested_friend_queryset

            if len(suggested_friend_list):
                success = True
                suggested_friend_list_found = True
                status += 'SUGGESTED_FRIEND_LIST_RETRIEVED '
            else:
                success = True
                suggested_friend_list_found = False
                status += 'NO_SUGGESTED_FRIEND_LIST_RETRIEVED '
        except SuggestedFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            suggested_friend_list_found = False
            status += 'NO_SUGGESTED_FRIEND_LIST_RETRIEVED_DoesNotExist '
            suggested_friend_list = []
        except Exception as e:
            success = False
            suggested_friend_list_found = False
            status += 'FAILED retrieve_suggested_friend_list ' + str(e) + ' '
            suggested_friend_list = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_we_vote_id':             voter_we_vote_id,
            'suggested_friend_list_found':  suggested_friend_list_found,
            'suggested_friend_list':        suggested_friend_list,
        }
        return results

    def retrieve_suggested_friend_list_as_voters(self, voter_we_vote_id='', read_only=True):
        """
        This function is used to return the current friends of the viewer as a list of voters via the api.
        :param voter_we_vote_id:
        :param read_only:
        :return:
        """
        status = ''
        suggested_friend_list = []  # The entries from SuggestedFriend table
        friend_list_found = False
        friend_list = []  # A list of friends, returned as voter entries

        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success': success,
                'status': status,
                'voter_we_vote_id': voter_we_vote_id,
                'friend_list_found': friend_list_found,
                'friend_list': friend_list,
            }
            return results

        try:
            suggested_friend_queryset = SuggestedFriend.objects.using('readonly').all()
            suggested_friend_queryset = suggested_friend_queryset.filter(
                Q(viewer_voter_we_vote_id__iexact=voter_we_vote_id) |
                Q(viewee_voter_we_vote_id__iexact=voter_we_vote_id))
            suggested_friend_queryset = suggested_friend_queryset.exclude(
                Q(voter_we_vote_id_deleted_first__iexact=voter_we_vote_id) |
                Q(voter_we_vote_id_deleted_second__iexact=voter_we_vote_id))
            suggested_friend_queryset = suggested_friend_queryset.exclude(friend_invite_sent=True)
            suggested_friend_queryset = suggested_friend_queryset.exclude(current_friends=True)
            # suggested_friend_queryset = suggested_friend_queryset.order_by('-date_last_changed')
            suggested_friend_list = list(suggested_friend_queryset)

            if len(suggested_friend_list):
                success = True
                suggested_friend_list_found = True
                status += 'SUGGESTED_FRIEND_LIST_AS_VOTERS_RETRIEVED '
            else:
                success = True
                suggested_friend_list_found = False
                status += 'NO_SUGGESTED_FRIEND_LIST_AS_VOTERS_RETRIEVED '
        except SuggestedFriend.DoesNotExist:
            # No data found. Not a problem.
            success = True
            suggested_friend_list_found = False
            status += 'NO_SUGGESTED_FRIEND_LIST_AS_VOTERS_RETRIEVED_DoesNotExist '
            friend_list = []
        except Exception as e:
            success = False
            suggested_friend_list_found = False
            status += 'FAILED retrieve_suggested_friend_list_as_voters ' + str(e) + ' '

        friend_results = self.retrieve_friends_we_vote_id_list(voter_we_vote_id)
        friends_we_vote_id_list = []
        if friend_results['friends_we_vote_id_list_found']:
            friends_we_vote_id_list = friend_results['friends_we_vote_id_list']

        invitations_sent_by_me_we_vote_id_list = self.fetch_friend_invitations_sent_by_me_we_vote_id_list(
            voter_we_vote_id)

        invitations_sent_to_me_we_vote_id_list = self.fetch_friend_invitations_sent_to_me_we_vote_id_list(
            voter_we_vote_id)

        filtered_suggested_friend_list_we_vote_ids = {}
        if suggested_friend_list_found:
            suggested_friend_dict = {}
            voter_manager = VoterManager()
            for suggested_friend_entry in suggested_friend_list:
                we_vote_id_of_friend = suggested_friend_entry.fetch_other_voter_we_vote_id(voter_we_vote_id)
                suggested_friend_dict[we_vote_id_of_friend] = suggested_friend_entry

                if we_vote_id_of_friend in friends_we_vote_id_list:
                    # If this person is already a friend, don't suggest as a friend
                    continue

                if we_vote_id_of_friend in invitations_sent_by_me_we_vote_id_list:
                    # If we already sent them an invite, don't suggest as a friend
                    continue

                if we_vote_id_of_friend in invitations_sent_to_me_we_vote_id_list:
                    # If we have already been sent an invite from them, don't suggest as a friend
                    continue

                # Create a dictionary of we_vote_ids with the number of times a friend is suggested
                if hasattr(filtered_suggested_friend_list_we_vote_ids, we_vote_id_of_friend):
                    filtered_suggested_friend_list_we_vote_ids[we_vote_id_of_friend] += 1
                else:
                    filtered_suggested_friend_list_we_vote_ids[we_vote_id_of_friend] = 1

            # Note: 2022-01-25 I'm not sure the results are actually sorted as claimed
            ordered_suggested_friend_list_we_vote_ids = sorted(filtered_suggested_friend_list_we_vote_ids)
            results = voter_manager.retrieve_voter_list_by_we_vote_id_list(
                voter_we_vote_id_list=ordered_suggested_friend_list_we_vote_ids,
                read_only=read_only)
            if results['voter_list_found']:
                friend_list = []
                raw_friend_list = results['voter_list']
                friend_list_found = True
                # Augment friend_list with mutual_friend data
                for one_voter in raw_friend_list:
                    if one_voter.we_vote_id in suggested_friend_dict:
                        suggested_friend = suggested_friend_dict[one_voter.we_vote_id]
                        one_voter.mutual_friend_count = suggested_friend.mutual_friend_count
                        if suggested_friend.mutual_friend_preview_list_serialized:
                            mutual_friend_preview_list = \
                                json.loads(suggested_friend.mutual_friend_preview_list_serialized)
                        else:
                            mutual_friend_preview_list = []
                        one_voter.mutual_friend_preview_list = mutual_friend_preview_list
                    friend_list.append(one_voter)

        results = {
            'success':              success,
            'status':               status,
            'voter_we_vote_id':     voter_we_vote_id,
            'friend_list_found':    friend_list_found,
            'friend_list':          friend_list,
        }
        return results

    def update_suggested_friends_starting_with_one_voter(self, starting_voter_we_vote_id, read_only=False):
        """
        Note that we default to "read_only=False" (that is, the live db) since usually we are doing this update
        right after adding a friend, and we want the new friend to be returned in "retrieve_current_friend_list".
        We use the live database ("read_only=False") because we don't want to create a race condition with
        the replicated read_only not being caught up with the master fast enough (since a friend
        was just created above.)

        :param starting_voter_we_vote_id:
        :param read_only:
        :return:
        """
        all_friends_one_person_results = self.retrieve_current_friend_list(starting_voter_we_vote_id, read_only=read_only)
        suggested_friend_created_count = 0
        if all_friends_one_person_results['current_friend_list_found']:
            current_friend_list = all_friends_one_person_results['current_friend_list']
            # For each friend on this list, suggest every other friend as a possible friend
            # Ex/ You have the friends Jo and Pat. This routine makes sure they both see each other as suggested friends
            for one_current_friend_to_suggest in current_friend_list:
                first_voter_we_vote_id = one_current_friend_to_suggest.fetch_other_voter_we_vote_id(
                    starting_voter_we_vote_id)
                for second_current_friend_to_suggest in current_friend_list:
                    second_voter_we_vote_id = second_current_friend_to_suggest.fetch_other_voter_we_vote_id(
                        starting_voter_we_vote_id)
                    if positive_value_exists(first_voter_we_vote_id) and \
                            positive_value_exists(second_voter_we_vote_id) and \
                            first_voter_we_vote_id != second_voter_we_vote_id:
                        # Are they already friends?
                        already_friend_results = self.retrieve_current_friend(first_voter_we_vote_id,
                                                                              second_voter_we_vote_id)
                        if not already_friend_results['current_friend_found']:
                            suggested_friend_results = self.update_or_create_suggested_friend(first_voter_we_vote_id,
                                                                                              second_voter_we_vote_id)
                            if suggested_friend_results['suggested_friend_created'] or \
                                    suggested_friend_results['suggested_friend_found']:
                                suggested_friend_created_count += 1

        results = {
            'status':                           "UPDATE_SUGGESTED_FRIENDS_COMPLETED ",
            'success':                          True,
            'suggested_friend_created_count':   suggested_friend_created_count,
        }
        return results

    def update_suggested_friend(self, voter_we_vote_id, other_voter_we_vote_id,
                                defaults=None):
        status = ""
        success = True
        suggested_friend = None
        suggested_friend_found = False

        if defaults is None:
            status += 'UPDATE_SUGGESTED_FRIEND-NO_DEFAULTS_PROVIDED '
            results = {
                'status':                   status,
                'success':                  success,
                'suggested_friend_found':   suggested_friend_found,
                'suggested_friend':         suggested_friend,
            }
            return results

        retrieve_results = self.retrieve_suggested_friend(voter_we_vote_id_one=voter_we_vote_id,
                                                          voter_we_vote_id_two=other_voter_we_vote_id,
                                                          read_only=False)
        if retrieve_results['suggested_friend_found']:
            suggested_friend = retrieve_results['suggested_friend']
            try:
                if 'current_friends' in defaults:
                    suggested_friend.current_friends = defaults['current_friends']
                if 'friend_invite_sent' in defaults:
                    suggested_friend.friend_invite_sent = defaults['friend_invite_sent']
                if 'voter_we_vote_id_deleted_first' in defaults:
                    suggested_friend.voter_we_vote_id_deleted_first = defaults['voter_we_vote_id_deleted_first']
                if 'voter_we_vote_id_deleted_second' in defaults:
                    suggested_friend.voter_we_vote_id_deleted_second = defaults['voter_we_vote_id_deleted_second']
                # This is a case where we don't know if the we_vote_id is already stored
                if 'voter_we_vote_id_deleted' in defaults:
                    # Does a "first" value exist?
                    if suggested_friend.voter_we_vote_id_deleted_first == defaults['voter_we_vote_id_deleted']:
                        # An update isn't needed
                        pass
                    elif not positive_value_exists(suggested_friend.voter_we_vote_id_deleted_first):
                        # A first "opt out" does not exist, so put the value in "first"
                        suggested_friend.voter_we_vote_id_deleted_first = defaults['voter_we_vote_id_deleted']
                    elif suggested_friend.voter_we_vote_id_deleted_second == defaults['voter_we_vote_id_deleted']:
                        # An update isn't needed
                        pass
                    elif not positive_value_exists(suggested_friend.voter_we_vote_id_deleted_second):
                        # A second "opt out" does not exist, so put the value in "second"
                        suggested_friend.voter_we_vote_id_deleted_second = defaults['voter_we_vote_id_deleted']
                suggested_friend.save()
                suggested_friend_found = True
                status += "SUGGESTED_FRIEND_UPDATED "
            except Exception as e:
                status += "UPDATE_SUGGESTED_FRIEND-ERROR: " + str(e) + " "
        else:
            status += "UPDATE_SUGGESTED_FRIEND-NOT_FOUND "

        results = {
            'status':                   status,
            'success':                  success,
            'suggested_friend_found':   suggested_friend_found,
            'suggested_friend':         suggested_friend,
        }
        return results


class MutualFriend(models.Model):
    """
    This is considered a "cache" table, with all data being generated and aggregated to speed up other processes.
    This table helps us generate and update the array stored in CurrentFriend.mutual_friend_preview_list_serialized.
    The "direction" doesn't matter, although it usually indicates who initiated the first friend invitation.
    """
    viewer_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False, db_index=True)
    viewee_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 2", max_length=255, null=True, blank=True, unique=False, db_index=True)
    mutual_friend_voter_we_vote_id = models.CharField(
        max_length=255, null=True, blank=True, unique=False, db_index=True)

    mutual_friend_display_name = models.CharField(max_length=255, null=True, blank=True)
    mutual_friend_display_name_exists = models.BooleanField(default=False, db_index=True)

    mutual_friend_we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    mutual_friend_profile_image_exists = models.BooleanField(default=False, db_index=True)

    # The more friends the viewer and the mutual_friend share, the more important this mutual friend is
    viewer_to_mutual_friend_friend_count = models.PositiveSmallIntegerField(null=True, unique=False)
    # The more friends the viewee and the mutual_friend share, the more important this mutual friend is
    viewee_to_mutual_friend_friend_count = models.PositiveSmallIntegerField(null=True, unique=False)

    date_last_changed = models.DateTimeField(null=True, auto_now=True)

    def fetch_other_voter_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.viewer_voter_we_vote_id:
            return self.viewee_voter_we_vote_id
        elif one_we_vote_id == self.viewee_voter_we_vote_id:
            return self.viewer_voter_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class SuggestedFriend(models.Model):
    """
    This table stores possible friend connections.
    """
    viewer_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 1", max_length=255, null=True, blank=True, unique=False)
    viewee_voter_we_vote_id = models.CharField(
        verbose_name="voter we vote id person 2", max_length=255, null=True, blank=True, unique=False)
    # Each voter can choose to remove this suggested friend entry for themselves. When one voter's id
    # is in "first" that voter won't see the suggested entry. The second voter can also remove the entry.
    voter_we_vote_id_deleted_first = models.CharField(
        verbose_name="first voter to remove suggested friend", max_length=255, null=True, blank=True, unique=False)
    voter_we_vote_id_deleted_second = models.CharField(
        verbose_name="second voter to remove suggested friend", max_length=255, null=True, blank=True, unique=False)
    friend_invite_sent = models.BooleanField(default=False)
    current_friends = models.BooleanField(default=False)

    mutual_friend_count = models.PositiveSmallIntegerField(null=True, unique=False)
    mutual_friend_count_last_updated = models.DateTimeField(null=True)

    mutual_friend_preview_list_serialized = models.TextField(default=None, null=True)
    mutual_friend_preview_list_update_needed = models.BooleanField(default=True)

    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def fetch_other_voter_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.viewer_voter_we_vote_id:
            return self.viewee_voter_we_vote_id
        elif one_we_vote_id == self.viewee_voter_we_vote_id:
            return self.viewer_voter_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""
