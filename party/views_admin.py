# party/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import party_import_from_sample_file
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from import_export_ctcl.controllers import CTCL_SAMPLE_XML_FILE
from django.contrib.auth.decorators import login_required
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def party_import_from_xml_view(request):

    results = party_import_from_sample_file(CTCL_SAMPLE_XML_FILE)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Party import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
