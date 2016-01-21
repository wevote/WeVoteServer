# polling_location/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation
from .controllers import import_and_save_all_polling_locations_data
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
# from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from wevote_functions.models import convert_to_int, positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

STATE_LIST_IMPORT = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        # 'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        # 'CO': 'Colorado',
        # 'CT': 'Connecticut',
        # 'DC': 'District of Columbia',
        # 'DE': 'Delaware',
        # 'FL': 'Florida',
        # 'GA': 'Georgia',
        # 'GU': 'Guam',
        # 'HI': 'Hawaii',
        # 'IA': 'Iowa',
        # 'ID': 'Idaho',
        # 'IL': 'Illinois',
        # 'IN': 'Indiana',
        # 'KS': 'Kansas',
        # 'KY': 'Kentucky',
        # 'LA': 'Louisiana',
        # 'MA': 'Massachusetts',
        # 'MD': 'Maryland',
        # 'ME': 'Maine',
        # 'MI': 'Michigan',
        # 'MN': 'Minnesota',
        # 'MO': 'Missouri',
        # 'MP': 'Northern Mariana Islands',
        # 'MS': 'Mississippi',
        'MT': 'Montana',
        # 'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        # 'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        # 'OH': 'Ohio',
        # 'OK': 'Oklahoma',
        # 'OR': 'Oregon',
        # 'PA': 'Pennsylvania',
        # 'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        # 'SC': 'South Carolina',
        # 'SD': 'South Dakota',
        # 'TN': 'Tennessee',
        # 'TX': 'Texas',
        # 'UT': 'Utah',
        'VA': 'Virginia',
        # 'VI': 'Virgin Islands',
        # 'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming'
}


# @login_required()  # Commented out while we are developing login process()
def import_polling_locations_view(request):
    # This should be updated to be a view with some import options
    messages.add_message(request, messages.INFO, 'TODO We need to create interface where we can control which '
                                                 'polling_locations import file to use.')
    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def import_polling_locations_process_view(request):
    results = import_and_save_all_polling_locations_data()

    messages.add_message(request, messages.INFO,
                         'Polling locations retrieved from file. '
                         '({saved} added, {updated} updated, {not_processed} not_processed)'.format(
                             saved=results['saved'],
                             updated=results['updated'],
                             not_processed=results['not_processed'],))
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
    polling_location_on_stage = PollingLocation()
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
    polling_location_on_stage = PollingLocation()
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
    polling_location_state = request.GET.get('polling_location_state')
    no_limit = False

    polling_location_count_query = PollingLocation.objects.all()
    if positive_value_exists(polling_location_state):
        polling_location_count_query = polling_location_count_query.filter(state__iexact=polling_location_state)
    polling_location_count = polling_location_count_query.count()
    messages.add_message(request, messages.INFO, '{polling_location_count} polling locations found.'.format(
        polling_location_count=polling_location_count))

    polling_location_query = PollingLocation.objects.all()
    if positive_value_exists(polling_location_state):
        polling_location_query = polling_location_query.filter(state__iexact=polling_location_state)
    if no_limit:
        polling_location_query = polling_location_query.order_by('location_name')
    else:
        polling_location_query = polling_location_query.order_by('location_name')[:100]
    polling_location_list = polling_location_query

    state_list = STATE_LIST_IMPORT

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'polling_location_list':    polling_location_list,
        'polling_location_count':   polling_location_count,
        'polling_location_state':   polling_location_state,
        'state_list':               state_list,
    }
    return render(request, 'polling_location/polling_location_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def polling_location_summary_view(request, polling_location_local_id):
    messages_on_stage = get_messages(request)
    polling_location_local_id = convert_to_int(polling_location_local_id)
    polling_location_on_stage_found = False
    polling_location_on_stage = PollingLocation()
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
