# polling_location/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation
from .controllers import import_and_save_all_polling_locations_data
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from wevote_functions.models import convert_to_int
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


# @login_required()  # Commented out while we are developing login process()
def import_polling_locations_view(request):
    # This should be updated to be a view with some import options
    messages.add_message(request, messages.INFO, 'TODO We need to create interface where we can control which '
                                                 'polling_locations import file to use.')
    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def import_polling_locations_process_view(request):
    # Pass a "state" variable into this view so we know which file to process
    state = 'va'  # Convert to get variable so we can control which state to process from the interface
    results = import_and_save_all_polling_locations_data(state)

    messages.add_message(request, messages.INFO,
                         'Polling locations retrieved from file. '
                         '({create_count} added, {update_count} updated)'.format(
                             create_count=results['create_count'],
                             update_count=results['update_count']))
    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def polling_location_edit_process_view(request):
    """
    Process the new or edit polling_location forms
    :param request:
    :return:
    """
    polling_location_id = convert_to_int(request.POST['polling_location_id'])
    polling_location_name = request.POST['polling_location_name']

    # Check to see if this polling_location is already being used anywhere
    polling_location_on_stage_found = False
    try:
        polling_location_query = PollingLocation.objects.filter(id=polling_location_id)
        if len(polling_location_query):
            polling_location_on_stage = polling_location_query[0]
            polling_location_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    try:
        if polling_location_on_stage_found:
            # Update
            polling_location_on_stage.polling_location_name = polling_location_name
            polling_location_on_stage.save()
            messages.add_message(request, messages.INFO, 'PollingLocation updated.')
        else:
            # Create new
            messages.add_message(request, messages.INFO, 'We do not support adding new polling locations.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save polling_location.')

    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def polling_location_edit_view(request, polling_location_local_id):
    messages_on_stage = get_messages(request)
    polling_location_local_id = convert_to_int(polling_location_local_id)
    polling_location_on_stage_found = False
    try:
        polling_location_on_stage = PollingLocation.objects.get(id=polling_location_local_id)
        polling_location_on_stage_found = True
    except PollingLocation.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except PollingLocation.DoesNotExist:
        # This is fine, create new
        pass

    if polling_location_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'polling_location': polling_location_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'polling_location/polling_location_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def polling_location_list_view(request):
    messages_on_stage = get_messages(request)
    polling_location_list = PollingLocation.objects.order_by('city')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'polling_location_list': polling_location_list,
    }
    return render(request, 'polling_location/polling_location_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def polling_location_summary_view(request, polling_location_local_id):
    messages_on_stage = get_messages(request)
    polling_location_local_id = convert_to_int(polling_location_local_id)
    polling_location_on_stage_found = False
    try:
        polling_location_on_stage = PollingLocation.objects.get(id=polling_location_local_id)
        polling_location_on_stage_found = True
    except PollingLocation.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except PollingLocation.DoesNotExist:
        # This is fine, create new
        pass

    if polling_location_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'polling_location': polling_location_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'polling_location/polling_location_summary.html', template_values)
