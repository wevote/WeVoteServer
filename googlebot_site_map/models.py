# googlebot_site_map/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models


class GooglebotRequest(models.Model):
    objects = None
    date_requested = models.DateTimeField(verbose_name='date requested', null=False, auto_now_add=True)
    request_url_type = models.CharField(
        verbose_name="Request URL end string", max_length=255, null=True, blank=True)
    is_from_google = models.BooleanField(default=False, verbose_name='is remote address registered as Google\'s')
    remote_address = models.CharField(
        verbose_name="Remote Address", max_length=255, null=True, blank=True)
    remote_dns = models.CharField(
        verbose_name="Remote reverse DNS", max_length=255, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
