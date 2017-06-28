# import_export_ctcl/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)

class CandidateSelection(models.Model):
    """
    Contest Office to Candidate mapping is stored in this table.
    """
    batch_set_id = models.PositiveIntegerField(verbose_name="batch set id", default=0, null=True, blank=True)
    candidate_selection_id = models.CharField(verbose_name="candidate selection id", default='', null=True,
                                              max_length=255)
    contest_office_id = models.CharField(verbose_name="contest office ctcl id", default='', null=True, max_length=255)
