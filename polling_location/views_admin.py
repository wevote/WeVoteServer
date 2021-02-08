# polling_location/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation, PollingLocationManager
from .controllers import filter_polling_locations_structured_json_for_local_duplicates, \
    import_and_save_all_polling_locations_data, polling_locations_import_from_structured_json
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturned, BallotReturnedListManager
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception
from voter.models import voter_has_authority
from wevote_functions.functions import convert_state_code_to_state_text, convert_to_float, convert_to_int, \
    positive_value_exists, process_request_from_master, STATE_CODE_MAP, STATE_GEOGRAPHIC_CENTER
import wevote_functions.admin
from django.http import HttpResponse
import json

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POLLING_LOCATIONS_SYNC_URL = get_environment_variable("POLLING_LOCATIONS_SYNC_URL")  # pollingLocationsSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)

# These are states for which we have map point data
STATE_LIST_IMPORT = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    'AS': 'American Samoa',
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DC': 'District of Columbia',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'GU': 'Guam',
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
    'PR': 'Puerto Rico',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VA': 'Virginia',
    'VI': 'Virgin Islands',
    'VT': 'Vermont',
    'WA': 'Washington',
    'WI': 'Wisconsin',
    'WV': 'West Virginia',
    'WY': 'Wyoming'
}

# https://simple.wikipedia.org/wiki/List_of_U.S._states_by_population
STATE_POPULATION = {
    'AK': 731545,
    'AL': 4903185,
    'AR': 3017825,
    'AS': 55641,
    'AZ': 7278717,
    'CA': 39512223,
    'CO': 5758736,
    'CT': 3565287,
    'DC': 705749,
    'DE': 973764,
    'FL': 21477737,
    'GA': 10617423,
    'GU': 165718,
    'HI': 1415872,
    'IA': 3155070,
    'ID': 1787065,
    'IL': 12671821,
    'IN': 6732219,
    'KS': 2913314,
    'KY': 4467673,
    'LA': 4648794,
    'MA': 6949503,
    'MD': 6045680,
    'ME': 1344212,
    'MI': 9986857,
    'MN': 5639632,
    'MO': 6137428,
    # 'MP': ,
    'MS': 2976149,
    'MT': 1068778,
    # 'NA': ,
    'NC': 10488084,
    'ND': 762062,
    'NE': 1934408,
    'NH': 1359711,
    'NJ': 8882190,
    'NM': 2096829,
    'NV': 3080156,
    'NY': 19453561,
    'OH': 11689100,
    'OK': 3956971,
    'OR': 4217737,
    'PA': 12801989,
    'PR': 3193694,
    'RI': 1059361,
    'SC': 5148714,
    'SD': 884659,
    'TN': 6833174,
    'TX': 28995881,
    'UT': 3205958,
    'VA': 8535519,
    'VI': 104914,
    'VT': 623989,
    'WA': 7614893,
    'WI': 5822434,
    'WV': 1792147,
    'WY': 578759,
}

polling_locations_import_status_string = ""


# This page does not need to be protected.
def polling_locations_sync_out_view(request):  # pollingLocationsSyncOut
    state = request.GET.get('state', '')

    try:
        polling_location_query = PollingLocation.objects.using('readonly').all()
        polling_location_query = polling_location_query.filter(polling_location_deleted=False)
        if positive_value_exists(state):
            polling_location_query = polling_location_query.filter(state__iexact=state)

        polling_location_list_dict = polling_location_query.values('we_vote_id', 'city',
                                                                   'county_name',
                                                                   'directions_text',
                                                                   'latitude', 'longitude',
                                                                   'line1', 'line2', 'location_name',
                                                                   'polling_hours_text',
                                                                   'polling_location_id',
                                                                   'precinct_name',
                                                                   'state',
                                                                   'use_for_bulk_retrieve',
                                                                   'polling_location_deleted',
                                                                   'source_code',
                                                                   'zip_long', 'id')
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
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in POLLING_LOCATIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    global polling_locations_import_status_string
    status = ""

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    # results = polling_locations_import_from_master_server(request, state_code)
    import_results, structured_json = process_request_from_master(
        request, "Loading Map Points from We Vote Master servers",
        POLLING_LOCATIONS_SYNC_URL, {
            "key":    WE_VOTE_API_KEY,  # This comes from an environment variable
            "state":  state_code,
        }
    )

    duplicates_removed = 0
    json_retrieved = False
    saved = 0
    updated = 0
    not_processed = 0
    if import_results['success']:
        status += import_results['status']
        json_retrieved = True
        polling_locations_import_status_string = "Checking " + str(len(structured_json)) + \
                                                 " map points for duplicates. "
        results = filter_polling_locations_structured_json_for_local_duplicates(structured_json)
        filtered_structured_json = results['structured_json']
        duplicates_removed = results['duplicates_removed']

        polling_locations_import_status_string = "Importing " + str(len(filtered_structured_json)) + \
                                                 " map points."
        import_results = polling_locations_import_from_structured_json(filtered_structured_json)
        saved = import_results['saved']
        updated = import_results['updated']
        not_processed = import_results['not_processed']
    else:
        polling_locations_import_status_string = \
            "Not able to retrieve the selected polling data from the Master Server. "
        status += polling_locations_import_status_string + import_results['status']

    if not json_retrieved:
        messages.add_message(request, messages.ERROR, status)
    else:
        messages.add_message(request, messages.INFO, 'Map Points import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Duplicates skipped: '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=saved,
                                                               updated=updated,
                                                               duplicates_removed=duplicates_removed,
                                                               not_processed=not_processed))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def polling_locations_import_from_master_server_status_view(request):
    # This function makes the assumption that only one developer is synchronizing at a time, to make it handle
    # multiple simultaneous users, we would need a map of strings, keyed to the device id.
    global polling_locations_import_status_string

    if 'polling_locations_import_status_string' not in globals():
        polling_locations_import_status_string = ""

    json_data = {
        'text': polling_locations_import_status_string,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def import_polling_locations_process_view(request):
    """
    This view imports the map point data from xml files from VIP (http://data.votinginfoproject.org)
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    # state_code = 'mo'  # State code for Missouri

    if not positive_value_exists(state_code):
        messages.add_message(request, messages.INFO,
                             'State code required to run import_polling_locations_process.')
        return HttpResponseRedirect(reverse('polling_location:polling_location_list',
                                            args=()) + "?state_code={var}".format(
            var=state_code))

    results = import_and_save_all_polling_locations_data(state_code.lower())

    messages.add_message(request, messages.INFO,
                         'Polling locations retrieved from file. '
                         '({saved} added, {updated} updated, {not_processed} not_processed)'.format(
                             saved=results['saved'],
                             updated=results['updated'],
                             not_processed=results['not_processed'],))
    return HttpResponseRedirect(reverse('polling_location:polling_location_list',
                                        args=()) + "?state_code={var}".format(
        var=state_code))


@login_required
def polling_location_edit_process_view(request):
    """
    Process the new or edit polling_location forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
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
    polling_location_deleted = request.POST.get('polling_location_deleted', False)

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
        polling_location_on_stage.polling_location_deleted = positive_value_exists(polling_location_deleted)

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
                google_civic_election_id=google_civic_election_id,
                polling_location_we_vote_id=polling_location_we_vote_id)
            if results['ballot_returned_list_found']:
                ballot_returned_list = results['ballot_returned_list']
                for one_ballot_returned in ballot_returned_list:
                    one_ballot_returned.latitude = latitude
                    one_ballot_returned.longitude = longitude
                    one_ballot_returned.save()

    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not update ballot_returned. ' +
                             status + " " + str(e) + " ")

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&state_code=" + str(state_code)
    if positive_value_exists(polling_location_we_vote_id):
        return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                    args=(polling_location_we_vote_id,)) + url_variables)
    else:
        return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) + url_variables)


@login_required
def polling_location_edit_view(request, polling_location_local_id=0, polling_location_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
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
def polling_location_visualize_view(request, polling_location_local_id=0, polling_location_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', 'CA').upper()
    if state_code == '':
        state_code = 'CA'

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'geo_center_lat': STATE_GEOGRAPHIC_CENTER.get(state_code)[0],
        'geo_center_lng': STATE_GEOGRAPHIC_CENTER.get(state_code)[1],
        'geo_center_zoom': STATE_GEOGRAPHIC_CENTER.get(state_code)[2],
        'state_code': state_code,
        'state_list': sorted_state_list,
    }

    return render(request, 'polling_location/polling_location_visualize.html', template_values)


@login_required
def polling_location_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    limit = convert_to_int(request.GET.get('limit', 100))
    show_bulk_retrieve = request.GET.get('show_bulk_retrieve', 0)
    state_code = request.GET.get('state_code', '')
    polling_location_search = request.GET.get('polling_location_search', '')

    polling_location_count_query = PollingLocation.objects.all()
    polling_location_without_latitude_count = 0
    polling_location_query = PollingLocation.objects.all()
    if not positive_value_exists(polling_location_search):
        polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
        polling_location_query = polling_location_query.exclude(polling_location_deleted=True)

    if positive_value_exists(show_bulk_retrieve):
        polling_location_count_query = polling_location_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_query = polling_location_query.filter(use_for_bulk_retrieve=True)

    if positive_value_exists(state_code):
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.filter(state__iexact=state_code)

        polling_location_without_latitude_count_query = PollingLocation.objects.all()
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.filter(state__iexact=state_code)
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.exclude(polling_location_deleted=True)
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

            new_filter = Q(county_name__icontains=one_word)
            filters.append(new_filter)

            try:
                one_word_float = float(one_word)
                new_filter = Q(latitude=one_word_float)
                filters.append(new_filter)

                new_filter = Q(longitude=one_word_float)
                filters.append(new_filter)
            except Exception as e:
                pass

            new_filter = Q(line1__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(line2__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(precinct_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(source_code__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(zip_long__icontains=one_word)
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

    info_message = '{polling_location_count:,} map points found.'.format(
        polling_location_count=polling_location_count)
    if positive_value_exists(polling_location_without_latitude_count):
        info_message += ' {polling_location_without_latitude_count:,} map points without lat/long.'.format(
            polling_location_without_latitude_count=polling_location_without_latitude_count)

    messages.add_message(request, messages.INFO, info_message)

    polling_location_list = polling_location_query.order_by('location_name')[:limit]

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
def polling_locations_add_address_from_latitude_and_longitude_view(request):
    """
    Find map point entries that don't have state, but do have latitude/longitude, and update them
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    limit = request.GET.get('limit', 1000)
    state_code = request.GET.get('state_code', "")
    google_civic_election_id = request.GET.get('google_civic_election_id', "")

    polling_location_manager = PollingLocationManager()
    polling_location_we_vote_id = ""
    polling_location_list = []
    polling_locations_saved = 0
    polling_locations_not_saved = 0

    try:
        # Find all map points with an empty latitude (with limit)
        polling_location_query = PollingLocation.objects.all()
        polling_location_query = polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_query = polling_location_query.filter(Q(state__isnull=True) | Q(state=''))
        polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        polling_location_query = polling_location_query.order_by('location_name')[:limit]
        polling_location_list = list(polling_location_query)
    except Exception as e:
        messages.add_message(request, messages.ERROR,
                             'No map points found that have lat/long and need state: ' + str(e))

    for polling_location_on_stage in polling_location_list:
        try:
            lat_long_results = \
                polling_location_manager.populate_address_from_latitude_and_longitude_for_polling_location(
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
def polling_locations_add_latitude_and_longitude_view(request):
    """
    Find map point entries that don't have latitude/longitude (up to a limit), and update them
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    limit = request.GET.get('limit', 1000)
    state_code = request.GET.get('state_code', "")
    refresh_all = request.GET.get('refresh_all', "")
    google_civic_election_id = request.GET.get('google_civic_election_id', "")

    if not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR, 'State code required.')
        return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    polling_location_manager = PollingLocationManager()
    polling_location_we_vote_id = ""
    polling_location_list = []
    polling_locations_saved = 0
    polling_locations_not_saved = 0

    try:
        # Find all map points with an empty latitude (with limit)
        polling_location_query = PollingLocation.objects.all()
        if positive_value_exists(refresh_all):
            # Do not restrict to entries without lat/long
            pass
        else:
            polling_location_query = polling_location_query.filter(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_query = polling_location_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        polling_location_query = polling_location_query.order_by('location_name')[:limit]
        polling_location_list = list(polling_location_query)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'No map points found that need lat/long: ' + str(e))

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
def polling_location_statistics_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_search = request.GET.get('polling_location_search', '')

    state_list = STATE_LIST_IMPORT
    sorted_state_list = sorted(state_list.items())
    modified_state_list = []
    for one_state in sorted_state_list:
        state_details = {}

        state_code = one_state[0]
        state_name = one_state[1]
        state_details['state_code'] = state_code
        state_details['state_name'] = state_name

        if state_code in STATE_POPULATION:
            state_population = convert_to_int(STATE_POPULATION[state_code])
        else:
            state_population = 1
        state_details['state_population'] = state_population

        polling_location_count_query = PollingLocation.objects.all()
        polling_location_query = PollingLocation.objects.all()
        if not positive_value_exists(polling_location_search):
            polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count = polling_location_count_query.count()
        state_details['polling_location_count'] = polling_location_count

        if state_population > 0 and polling_location_count > 0:
            average_people_per_map_point = state_population / polling_location_count
            state_details['average_people_per_map_point'] = convert_to_int(average_people_per_map_point)
        else:
            state_details['average_people_per_map_point'] = 0

        polling_location_without_latitude_count_query = PollingLocation.objects.all()
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.filter(state__iexact=state_code)
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.exclude(polling_location_deleted=True)
        polling_location_without_latitude_count_query = \
            polling_location_without_latitude_count_query.filter(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_without_latitude_count = polling_location_without_latitude_count_query.count()
        state_details['polling_location_without_latitude_count'] = polling_location_without_latitude_count

        modified_state_list.append(state_details)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'state_details_list':       modified_state_list,
    }
    return render(request, 'polling_location/polling_location_statistics.html', template_values)


@login_required
def polling_location_summary_view(request, polling_location_local_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
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
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
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

    ballot_returned_list = []
    ballot_returned_list_found = False
    if polling_location_on_stage_found:
        ballot_returned_queryset = BallotReturned.objects.using('readonly').all()
        if positive_value_exists(google_civic_election_id):
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
        ballot_returned_queryset = ballot_returned_queryset.filter(
            polling_location_we_vote_id=polling_location_we_vote_id)

        ballot_returned_list = list(ballot_returned_queryset)

        if len(ballot_returned_list):
            ballot_returned_list_found = True

    template_values = {
        'ballot_returned_list':         ballot_returned_list,
        'ballot_returned_list_found':   ballot_returned_list_found,
        'google_civic_election_id':     google_civic_election_id,
        'messages_on_stage':            messages_on_stage,
        'polling_location':             polling_location_on_stage,
    }
    return render(request, 'polling_location/polling_location_summary.html', template_values)


@login_required
def soft_delete_duplicates_view(request):
    """
    Find map point entries that have the same address and mark them as deleted
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""
    state_code = request.GET.get('state_code', "")
    google_civic_election_id = request.GET.get('google_civic_election_id', "")
    analyze_start = convert_to_int(request.GET.get('analyze_start', 0))
    analyze_limit = convert_to_int(request.GET.get('analyze_limit', 3000))
    analyze_end = analyze_start + analyze_limit

    polling_location_manager = PollingLocationManager()

    if not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR, 'State code required.')
        return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    polling_location_list = []

    try:
        # Find all map points not already deleted
        polling_location_query = PollingLocation.objects.all()
        polling_location_query = polling_location_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        # Entry must have city to analyze or delete
        polling_location_query = polling_location_query.exclude(Q(city__isnull=True) | Q(city__iexact=""))
        polling_location_list = polling_location_query[analyze_start:analyze_end]
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'No map points found. ' + str(e))

    polling_locations_deleted = 0
    polling_locations_reviewed = 0
    previously_reviewed_we_vote_ids = []
    previously_deleted_we_vote_ids = []
    with transaction.atomic():
        for polling_location in polling_location_list:
            current_we_vote_id = polling_location.we_vote_id
            polling_locations_reviewed += 1

            # Add this polling_location_we_vote_id to the "previously_reviewed" list so we don't find it this pass
            if current_we_vote_id not in previously_reviewed_we_vote_ids:
                previously_reviewed_we_vote_ids.append(current_we_vote_id)

            # ############################
            # Search for matches by address
            try:
                duplicate_polling_location_query = PollingLocation.objects.all()
                duplicate_polling_location_query = duplicate_polling_location_query.filter(state__iexact=state_code)
                duplicate_polling_location_query = \
                    duplicate_polling_location_query.filter(city__iexact=polling_location.city)
                duplicate_polling_location_query = \
                    duplicate_polling_location_query.filter(line1__iexact=polling_location.line1)
                duplicate_polling_location_query = \
                    duplicate_polling_location_query.filter(zip_long__iexact=polling_location.zip_long)
                duplicate_polling_location_query = \
                    duplicate_polling_location_query.exclude(polling_location_deleted=True)
                duplicate_polling_location_query = \
                    duplicate_polling_location_query.exclude(we_vote_id__in=previously_reviewed_we_vote_ids)
                duplicate_polling_location_query = \
                    duplicate_polling_location_query.exclude(we_vote_id__in=previously_deleted_we_vote_ids)

                mark_as_duplicates_list = list(duplicate_polling_location_query)

                for duplicate_polling_location in mark_as_duplicates_list:
                    if duplicate_polling_location.we_vote_id not in previously_deleted_we_vote_ids:
                        try:
                            # Mark duplicates as a soft delete
                            duplicate_polling_location.polling_location_deleted = True
                            duplicate_polling_location.save()
                            previously_deleted_we_vote_ids.append(duplicate_polling_location.we_vote_id)
                            polling_locations_deleted += 1
                        except Exception as e:
                            status += "QUERY_BY_ADDRESS_COULD_NOT_SAVE-ERROR:" + str(e) + " "

            except Exception as e:
                status += "QUERY_BY_ADDRESS_PROBLEM:" + str(e) + " "

            # ############################
            # Search for matches by lat/long
            outer_loop_lat_long_changed = False
            polling_location_lat_long_refreshed = False
            if polling_location.latitude and polling_location.longitude:
                try:
                    duplicate_polling_location_query = PollingLocation.objects.all()
                    duplicate_polling_location_query = \
                        duplicate_polling_location_query.filter(latitude=polling_location.latitude)
                    duplicate_polling_location_query = \
                        duplicate_polling_location_query.filter(longitude=polling_location.longitude)
                    duplicate_polling_location_query = \
                        duplicate_polling_location_query.exclude(polling_location_deleted=True)
                    duplicate_polling_location_query = \
                        duplicate_polling_location_query.exclude(we_vote_id__in=previously_reviewed_we_vote_ids)
                    duplicate_polling_location_query = \
                        duplicate_polling_location_query.exclude(we_vote_id__in=previously_deleted_we_vote_ids)

                    mark_as_duplicates_list = list(duplicate_polling_location_query)

                    for duplicate_polling_location in mark_as_duplicates_list:
                        if not polling_location_lat_long_refreshed:
                            outer_loop_latitude_before = polling_location.latitude
                            outer_loop_longitude_before = polling_location.longitude
                            lat_long_results = \
                                polling_location_manager.populate_latitude_and_longitude_for_polling_location(
                                    polling_location)
                            status += lat_long_results['status']
                            outer_loop_latitude = lat_long_results['latitude']
                            outer_loop_longitude = lat_long_results['longitude']
                            polling_location = lat_long_results['polling_location']
                            outer_loop_lat_long_changed = outer_loop_latitude_before != outer_loop_latitude \
                                or outer_loop_longitude_before != outer_loop_longitude
                            polling_location_lat_long_refreshed = True

                        # Since we have seen some bad lat/long data, try to refresh it before deleting the duplicate
                        original_latitude = duplicate_polling_location.latitude
                        original_longitude = duplicate_polling_location.longitude

                        lat_long_results = \
                            polling_location_manager.populate_latitude_and_longitude_for_polling_location(
                                duplicate_polling_location)
                        status += lat_long_results['status']
                        latitude = lat_long_results['latitude']
                        longitude = lat_long_results['longitude']
                        duplicate_polling_location = lat_long_results['polling_location']

                        lat_long_same = original_latitude == latitude and original_longitude == longitude

                        if lat_long_same \
                                and duplicate_polling_location.we_vote_id not in previously_deleted_we_vote_ids \
                                and not outer_loop_lat_long_changed:
                            try:
                                # Mark duplicates as a soft delete
                                duplicate_polling_location.polling_location_deleted = True
                                duplicate_polling_location.save()
                                previously_deleted_we_vote_ids.append(duplicate_polling_location.we_vote_id)
                                polling_locations_deleted += 1
                            except Exception as e:
                                status += "QUERY_BY_LAT_LONG_COULD_NOT_SAVE-ERROR:" + str(e) + " "

                except Exception as e:
                    status += "QUERY_BY_LAT_LONG_PROBLEM:" + str(e) + " "

    messages.add_message(request, messages.INFO,
                         'Polling locations reviewed: ' + str(polling_locations_reviewed) +
                         ", deleted: " + str(polling_locations_deleted))

    url_variables = "?google_civic_election_id=" + str(google_civic_election_id) + \
                    "&state_code=" + str(state_code)
    return HttpResponseRedirect(reverse('polling_location:polling_location_list', args=()) + url_variables)
