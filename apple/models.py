# apple/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


class AppleUser(models.Model):
    """
    Sign in with Apple returns a unique apple user_code for a Apple ID/iCloud sign-in (8/5/20 is it unique or sb `sub`?)
    example user_code "001407.8220c1ff0bf84328bcc85ac1ca25e9aa.0456"
    Apple allows alias sign in email addresses, so the reported email address might be an alias that would not be
    in our system anywhere else
    """
    # objects = None
    # voter_device_id = models.CharField(verbose_name='voter device id',
    #                                    max_length=255, null=False, blank=False, unique=True, default='DELETE_ME')
    objects = None
    voter_we_vote_id = models.CharField(verbose_name="we vote id for the Apple ID owner", max_length=255, unique=True)
    user_code = models.CharField(verbose_name="User's apple id code", max_length=255, null=False, unique=False)
    email = models.EmailField(verbose_name='apple email address', max_length=255, unique=False,
                              null=True, blank=True)
    first_name = models.CharField(
        verbose_name="User's first_name from Apple", max_length=255, null=True, blank=True, unique=False)
    middle_name = models.CharField(
        verbose_name="User's middle_name from Apple", max_length=255, null=True, blank=True, unique=False)
    last_name = models.CharField(
        verbose_name="User's last_name from Apple", max_length=255, null=True, blank=True, unique=False)

    # The next three are for debugging/statistics are not necessary for sign in
    apple_platform = models.CharField(
        verbose_name="Platform of Apple Device", max_length=32, null=True, blank=True, unique=False)
    apple_os_version = models.CharField(
        verbose_name="Apple OS Version", max_length=32, null=True, blank=True, unique=False)
    apple_model = models.CharField(
        verbose_name="Apple Device Model", max_length=32, null=True, blank=True, unique=False)

    date_created = models.DateTimeField(verbose_name='date created', null=False, auto_now_add=True)
    date_last_referenced = models.DateTimeField(verbose_name='date last referenced', null=False, auto_now=True)

    def __unicode__(self):
        return AppleUser
