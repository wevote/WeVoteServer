# polling_location/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation
from .controllers import save_polling_locations_from_list, return_polling_locations_data
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


@login_required()
def import_polling_locations_view(request):
    # This should be updated to be a view with some import options
    messages.add_message(request, messages.INFO, 'TODO We need to create interface where we can control which '
                                                 'polling_locations import file to use.')
    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()))


@login_required()
def import_polling_locations_process_view(request):
    # Pass a "state" variable into this view so we know which file to process
    state = 'va'  # Convert to get variable so we can control which state to process from the interface
    polling_locations_list = return_polling_locations_data(state)
    results = save_polling_locations_from_list(polling_locations_list)

    messages.add_message(request, messages.INFO,
                         'Polling locations retrieved from file. '
                         '({create_count} added, {update_count} updated)'.format(
                             create_count=results['create_count'],
                             update_count=results['update_count']))
    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()))


@login_required()
def polling_location_list_view(request):
    messages_on_stage = get_messages(request)
    polling_location_list = PollingLocation.objects.order_by('city')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'polling_location_list': polling_location_list,
    }
    return render(request, 'polling_location/polling_location_list.html', template_values)
