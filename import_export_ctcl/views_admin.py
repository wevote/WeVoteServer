# import_export_ctcl/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib.messages import get_messages
from django.shortcuts import redirect, render
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def import_export_ctcl_index_view(request):
    """
    Provide an index of import/export actions (for We Vote data maintenance)
    """
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':    messages_on_stage,
    }
    return render(request, 'import_export_ctcl/index.html', template_values)

