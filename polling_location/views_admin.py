# polling_location/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation, PollingLocationManager
from .controllers import import_and_save_all_polling_locations_data, polling_locations_import_from_master_server
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception
from voter.models import voter_has_authority
from wevote_functions.functions import convert_state_code_to_state_text, convert_to_float, convert_to_int, \
    positive_value_exists
import wevote_functions.admin
from django.http import HttpResponse
import json

POLLING_LOCATIONS_SYNC_URL = get_environment_variable("POLLING_LOCATIONS_SYNC_URL")  # pollingLocationsSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

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
def polling_locations_sync_out_view(request):  # pollingLocationsSyncOut
    state = request.GET.get('state', '')

    try:
        polling_location_list = PollingLocation.objects.using('readonly').all()
        if positive_value_exists(state):
            polling_location_list = polling_location_list.filter(state__iexact=state)

        polling_location_list_dict = polling_location_list.values('we_vote_id', 'city', 'directions_text',
                                                                  'latitude', 'longitude',
                                                                  'line1', 'line2', 'location_name',
                                                                  'polling_hours_text',
                                                                  'polling_location_id', 'state',
                                                                  'use_for_bulk_retrieve',
                                                                  'zip_long')
        if polling_location_list_dict:
            polling_location_list_json = list(polling_location_list_dict)
            return HttpResponse(json.dumps(polling_location_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'POLLING_LOCATION_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def polling_locations_import_from_master_server_view(request):
    """
    This view reaches out to the master servers configured in WeVoteServer/config/environment_variables.json
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in POLLING_LOCATIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = polling_locations_import_from_master_server(request, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Polling Locations import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Duplicates skipped: '
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
    """
    This view imports the polling location data from xml files from VIP (http://data.votinginfoproject.org)
    :param request:
    :return:
    """
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

    status = ""
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', "")

    polling_location_id = convert_to_int(request.POST['polling_location_id'])
    location_name = request.POST.get('location_name', "")
    line1 = request.POST.get('line1', "")
    line2 = request.POST.get('line2', "")
    city = request.POST.get('city', "")
    zip_long_raw = request.POST.get('zip_long', "")
    zip_long = zip_long_raw.strip()
    latitude = convert_to_float(request.POST.get('latitude', 0))
    longitude = convert_to_float(request.POST.get('longitude', 0))
    use_for_bulk_retrieve = request.POST.get('use_for_bulk_retrieve', False)

    # Check to see if this polling_location is already being used anywhere
    polling_location_on_stage_found = False
    polling_location_on_stage = PollingLocation()
    polling_location_manager = PollingLocationManager()
    polling_location_we_vote_id = ""
    try:
        polling_location_query = PollingLocation.objects.filter(id=polling_location_id)
        if len(polling_location_query):
            polling_location_on_stage = polling_location_query[0]
            polling_location_on_stage_found = True
    except Exception as e:
        pass

    try:
        if not polling_location_on_stage_found:
            # Create new
            polling_location_on_stage = PollingLocation.objects.create(
                state=state_code,
                zip_long=zip_long,
            )

        polling_location_on_stage.location_name = location_name
        polling_location_on_stage.state = state_code
        polling_location_on_stage.line1 = line1
        polling_location_on_stage.line2 = line2
        polling_location_on_stage.city = city
        polling_location_on_stage.zip_long = zip_long
        polling_location_on_stage.latitude = latitude
        polling_location_on_stage.longitude = longitude
        polling_location_on_stage.use_for_bulk_retrieve = positive_value_exists(use_for_bulk_retrieve)

        polling_location_on_stage.save()
        polling_location_id = polling_location_on_stage.id
        polling_location_we_vote_id = polling_location_on_stage.we_vote_id

        if not zip_long or not latitude or not longitude:
            lat_long_results = polling_location_manager.populate_latitude_and_longitude_for_polling_location(
                polling_location_on_stage)
            status += lat_long_results['status']
            latitude = lat_long_results['latitude']
            longitude = lat_long_results['longitude']

        if polling_location_on_stage_found:
            # Update
            messages.add_message(request, messages.INFO, 'Polling location updated. ' + status)
        else:
            # Create new
            messages.add_message(request, messages.INFO, 'Polling location created. ' + status)

    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save polling_location. ' + status)

    # Now update ballot returned with lat/long
    try:
        if latitude and longitude:
            ballot_returned_list_manager = BallotReturnedListManager()
            results = ballot_returned_list_manager.retrieve_ballot_returned_list(
                google_civic_election_id, polling_location_we_vote_id)
            if results['ballot_returned_list_found']:
                ballot_returned_list = results['ballot_returned_list']
                for one_ballot_returned in ballot_returned_list:
                    one_ballot_returned.latitude = latitude
                    one_ballot_returned.longitude = longitude
                    one_ballot_returned.save()

    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not update ballot_returned. ' + status)

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&state_code=" + str(state_code)
    if positive_value_exists(polling_location_we_vote_id):
        return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                    args=(polling_location_we_vote_id,)) + url_variables)
    else:
        return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) + url_variables)


@login_required
def polling_location_edit_view(request, polling_location_local_id=0, polling_location_we_vote_id=""):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    messages_on_stage = get_messages(request)
    polling_location_local_id = convert_to_int(polling_location_local_id)
    polling_location_on_stage_found = False
    polling_location_on_stage = PollingLocation()
    try:
        if positive_value_exists(polling_location_local_id):
            polling_location_on_stage = PollingLocation.objects.get(id=polling_location_local_id)
            polling_location_on_stage_found = True
        elif positive_value_exists(polling_location_we_vote_id):
            polling_location_on_stage = PollingLocation.objects.get(we_vote_id=polling_location_we_vote_id)
            polling_location_on_stage_found = True
    except PollingLocation.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except PollingLocation.DoesNotExist:
        # This is fine, create new
        pass

    if polling_location_on_stage_found:
        template_values = {
            'google_civic_election_id': google_civic_election_id,
            'messages_on_stage': messages_on_stage,
            'polling_location': polling_location_on_stage,
            'polling_location_id': polling_location_on_stage.id,
            'state_code': state_code,
        }
    else:
        template_values = {
            'google_civic_election_id': google_civic_election_id,
            'messages_on_stage': messages_on_stage,
            'polling_location_id': 0,
            'state_code': state_code,
        }
    return render(request, 'polling_location/polling_location_edit.html', template_values)


@login_required
def polling_location_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_bulk_retrieve = request.GET.get('show_bulk_retrieve', 0)
    state_code = request.GET.get('state_code', '')
    polling_location_search = request.GET.get('polling_location_search', '')

    polling_location_count_query = PollingLocation.objects.all()
    polling_location_without_latitude_count = 0
    polling_location_query = PollingLocation.objects.all()

    if positive_value_exists(show_bulk_retrieve):
        polling_location_count_query = polling_location_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_query = polling_location_query.filter(use_for_bulk_retrieve=True)

    if positive_value_exists(state_code):
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.filter(state__iexact=state_code)

        polling_location_without_latitude_count_query = PollingLocation.objects.all()
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.filter(state__iexact=state_code)
        if positive_value_exists(show_bulk_retrieve):
            polling_location_without_latitude_count_query = \
                polling_location_without_latitude_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.filter(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_without_latitude_count = polling_location_without_latitude_count_query.count()

    if positive_value_exists(polling_location_search):
        search_words = polling_location_search.split()
        for one_word in search_words:
            filters = []

            new_filter = Q(we_vote_id__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(location_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(directions_text__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(city__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(zip_long__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(line1__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(line2__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                polling_location_count_query = polling_location_count_query.filter(final_filters)
                polling_location_query = polling_location_query.filter(final_filters)

    polling_location_count = polling_location_count_query.count()

    info_message = '{polling_location_count} polling locations found.'.format(
        polling_location_count=polling_location_count)
    if positive_value_exists(polling_location_without_latitude_count):
        info_message += ' {polling_location_without_latitude_count} polling locations without lat/long.'.format(
            polling_location_without_latitude_count=polling_location_without_latitude_count)

    messages.add_message(request, messages.INFO, info_message)

    polling_location_list = polling_location_query.order_by('location_name')[:100]

    state_list = STATE_LIST_IMPORT
    sorted_state_list = sorted(state_list.items())

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'polling_location_list':    polling_location_list,
        'polling_location_count':   polling_location_count,
        'polling_location_search':  polling_location_search,
        'show_bulk_retrieve':       show_bulk_retrieve,
        'state_code':               state_code,
        'state_name':               convert_state_code_to_state_text(state_code),
        'state_list':               sorted_state_list,
    }
    return render(request, 'polling_location/polling_location_list.html', template_values)


@login_required
def polling_locations_add_latitude_and_longitude_view(request):
    """
    Find polling location entries that don't have latitude/longitude (up to a limit), and update them
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    limit = request.GET.get('limit', 1000)
    state_code = request.GET.get('state_code', "")
    google_civic_election_id = request.GET.get('google_civic_election_id', "")

    if not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR, 'State code required.')
        return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) + \
                                    "&state_code=" + str(state_code))

    polling_location_manager = PollingLocationManager()
    polling_location_we_vote_id = ""
    polling_location_list = []
    polling_locations_saved = 0
    polling_locations_not_saved = 0

    try:
        # Find all polling locations with an empty latitude (with limit)
        polling_location_query = PollingLocation.objects.filter(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_query = polling_location_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.order_by('location_name')[:limit]
        polling_location_list = list(polling_location_query)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'No polling locations found that need lat/long.')

    for polling_location_on_stage in polling_location_list:
        try:
            lat_long_results = polling_location_manager.populate_latitude_and_longitude_for_polling_location(
                polling_location_on_stage)
            status += lat_long_results['status']
            if lat_long_results['success']:
                polling_locations_saved += 1
            else:
                polling_locations_not_saved += 1

        except Exception as e:
            polling_locations_not_saved += 1

    messages.add_message(request, messages.INFO, 'Polling locations saved: ' + str(polling_locations_saved) +
                         ", not saved: " + str(polling_locations_not_saved))

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&state_code=" + str(state_code)
    if positive_value_exists(polling_location_we_vote_id):
        return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                    args=(polling_location_we_vote_id,)) + url_variables)
    else:
        return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) + url_variables)


@login_required
def polling_location_summary_view(request, polling_location_local_id):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

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

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'polling_location':         polling_location_on_stage,
    }
    return render(request, 'polling_location/polling_location_summary.html', template_values)


@login_required
def polling_location_summary_by_we_vote_id_view(request, polling_location_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

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

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'polling_location':         polling_location_on_stage,
    }
    return render(request, 'polling_location/polling_location_summary.html', template_values)
