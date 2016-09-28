# import_export_facebook/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.validators import RegexValidator
from django.db import models
from email_outbound.models import SEND_STATUS_CHOICES, TO_BE_PROCESSED

FRIEND_INVITATION_FACEBOOK_TEMPLATE = 'FRIEND_INVITATION_FACEBOOK_TEMPLATE'
GENERIC_EMAIL_FACEBOOK_TEMPLATE = 'GENERIC_EMAIL_FACEBOOK_TEMPLATE'
KIND_OF_FACEBOOK_TEMPLATE_CHOICES = (
    (GENERIC_EMAIL_FACEBOOK_TEMPLATE,  'Generic Email'),
    (FRIEND_INVITATION_FACEBOOK_TEMPLATE, 'Invite Friend'),
)


class FacebookMessageOutboundDescription(models.Model):
    """
    A description of the Facebook direct message we want to send.
    """
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

    kind_of_send_template = models.CharField(max_length=50, choices=KIND_OF_FACEBOOK_TEMPLATE_CHOICES,
                                             default=GENERIC_EMAIL_FACEBOOK_TEMPLATE)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    recipient_facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    recipient_facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                                 null=True, blank=True)
    recipient_fb_username = models.CharField(unique=True, max_length=20, validators=[alphanumeric], null=True)
    send_status = models.CharField(max_length=50, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)
