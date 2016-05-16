# polling_location/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation
from .controllers import import_and_save_all_polling_locations_data, polling_locations_import_from_master_server
from .serializers import PollingLocationSerializer
from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int, positive_value_exists
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

# These are states for which we have polling location data
STATE_LIST_IMPORT = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        # 'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        # 'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        # 'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        # 'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        # 'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        # 'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming'
}


# This page does not need to be protected.
class PollingLocationsSyncOutView(APIView):
    def get(self, request, format=None):
        state = request.GET.get('state', '')

        polling_location_list = PollingLocation.objects.all()
        if positive_value_exists(state):
            polling_location_list = polling_location_list.filter(state__iexact=state)

        serializer = PollingLocationSerializer(polling_location_list, many=True)
        return Response(serializer.data)


@login_required
def polling_locations_import_from_master_server_view(request):
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    results = polling_locations_import_from_master_server(request, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Polling Locations import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Master data not imported (local duplicates found): '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def import_polling_locations_process_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    polling_location_state = request.GET.get('polling_location_state', '')
    # polling_location_state = 'mo'  # State code for Missouri

    results = import_and_save_all_polling_locations_data(polling_location_state.lower())

    messages.add_message(request, messages.INFO,
                         'Polling locations retrieved from file. '
                         '({saved} added, {updated} updated, {not_processed} not_processed)'.format(
                             saved=results['saved'],
                             updated=results['updated'],
                             not_processed=results['not_processed'],))
    return HttpResponseRedirect(reverse('polling_location:polling_location_list',
                                        args=()) + "?polling_location_state={var}".format(
        var=polling_location_state))


@login_required
def polling_location_edit_process_view(request):
    """
    Process the new or edit polling_location forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    polling_location_id = convert_to_int(request.POST['polling_location_id'])
    polling_location_name = request.POST.get('polling_location_name', False)

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


@login_required
def polling_location_edit_view(request, polling_location_local_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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


@login_required
def polling_location_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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
    sorted_state_list = sorted(state_list.items())

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'polling_location_list':    polling_location_list,
        'polling_location_count':   polling_location_count,
        'polling_location_state':   polling_location_state,
        'state_list':               sorted_state_list,
    }
    return render(request, 'polling_location/polling_location_list.html', template_values)


@login_required
def polling_location_summary_view(request, polling_location_local_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

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


@login_required
def polling_location_summary_by_we_vote_id_view(request, polling_location_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    polling_location_on_stage_found = False
    polling_location_on_stage = PollingLocation()
    try:
        polling_location_on_stage = PollingLocation.objects.get(we_vote_id=polling_location_we_vote_id)
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
