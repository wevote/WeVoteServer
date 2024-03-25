# retrieve_tables/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models


class RetrieveTableState(models.Model):
    objects = None
    is_running = models.BooleanField(verbose_name='Is the retrieve table running?', default=False)
    started_date = models.DateTimeField(verbose_name='Date, tables retrieve started', null=False, auto_now_add=True)
    table_name = models.CharField(verbose_name="Current table name", max_length=255, null=True, blank=True)
    chunk = models.PositiveIntegerField(verbose_name="Current chunk number", default=0)
    current_record = models.PositiveIntegerField(verbose_name="Current record counter", default=0)
    total_records = models.PositiveIntegerField(verbose_name="Total records to be exported", default=0)
    voter_device_id = models.CharField(verbose_name='voter device id', max_length=255, null=True, unique=True,
                                       db_index=True)
