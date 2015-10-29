# import_export_google_civic/models.py
# Brought to you by We Vote. Be good.
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.models import positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)
