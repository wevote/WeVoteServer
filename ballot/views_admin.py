# ballot/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import ballot_items_import_from_master_server, ballot_returned_import_from_master_server, \
    repair_ballot_items_for_election
from .models import BallotItem, BallotItemListManager, BallotItemManager, BallotReturned, BallotReturnedManager
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaignListManager
from config.base import get_environment_variable
from office.models import ContestOffice, ContestOfficeManager
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from election.models import Election, ElectionManager
from geopy.geocoders import get_geocoder_for_service
from measure.models import ContestMeasure, ContestMeasureManager
from polling_location.models import PollingLocation, PollingLocationManager
import time
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
import json

GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
def ballot_items_sync_out_view(request):  # ballotItemsSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', False)

    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
        json_data = {
            'success': False,
            'status': 'BALLOT_ITEM_LIST-ELECTION_OR_STATE_CODE_FILTER_REQUIRED'
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    try:
        ballot_item_list = BallotItem.objects.all()
        # We only want BallotItem values associated with polling locations
        ballot_item_list = ballot_item_list.exclude(polling_location_we_vote_id__isnull=True)
        ballot_item_list = ballot_item_list.exclude(polling_location_we_vote_id__iexact='')
        if positive_value_exists(google_civic_election_id):
            ballot_item_list = ballot_item_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            ballot_item_list = ballot_item_list.filter(state_code__iexact=state_code)

        # serializer = BallotItemSerializer(ballot_item_list, many=True)
        # return Response(serializer.data)
        ballot_item_list_dict = ballot_item_list.values('ballot_item_display_name', 'contest_office_we_vote_id',
                                                        'contest_measure_we_vote_id', 'google_ballot_placement',
                                                        'google_civic_election_id', 'state_code', 'local_ballot_order',
                                                        'measure_subtitle', 'polling_location_we_vote_id')
        if ballot_item_list_dict:
            ballot_item_list_json = list(ballot_item_list_dict)
            return HttpResponse(json.dumps(ballot_item_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'BALLOT_ITEM_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def ballot_returned_delete_process_view(request, ballot_returned_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    success = False
    ballot_returned_found = False
    ballot_returned = BallotReturned()

    ballot_returned_manager = BallotReturnedManager()
    results = ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id)
    if results['ballot_returned_found']:
        ballot_returned = results['ballot_returned']
        ballot_returned_found = True
        # google_civic_election_id = ballot_returned.google_civic_election_id
        # polling_location_we_vote_id = ballot_returned.polling_location_we_vote_id

    if not ballot_returned_found:
        messages.add_message(request, messages.ERROR, 'Could not find ballot_returned, id: ' + ballot_returned_id +
                                                      '  -- required to delete this ballot location.')
        return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code)
                                    )

    # Get a list of ballot_items stored at this location
    ballot_item_list_manager = BallotItemListManager()
    ballot_items_delete_failed_count = 0
    if positive_value_exists(ballot_returned.polling_location_we_vote_id) and \
            positive_value_exists(ballot_returned.google_civic_election_id):
        results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
            ballot_returned.polling_location_we_vote_id, ballot_returned.google_civic_election_id)
        if results['ballot_item_list_found']:
            ballot_item_list = results['ballot_item_list']
            for one_ballot_item in ballot_item_list:
                try:
                    one_ballot_item.delete()
                except Exception as e:
                    ballot_items_delete_failed_count += 0

    if not positive_value_exists(ballot_items_delete_failed_count):
        google_civic_election_id = ballot_returned.google_civic_election_id
        try:
            ballot_returned.delete()
            success = True
        except Exception as e:
            success = False

    if success:
        messages.add_message(request, messages.INFO, 'ballot_returned and ballot_items deleted.')
        election_local_id = 0
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code)
                                    )
    else:
        messages.add_message(request, messages.ERROR, 'Could not delete.')
        return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code)
                                    )


# This page does not need to be protected.
def ballot_returned_sync_out_view(request):  # ballotReturnedSyncOut
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
        json_data = {
            'success': False,
            'status': 'BALLOT_RETURNED_LIST_MISSING-google_civic_election_id or state_code required'
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    try:
        ballot_returned_list = BallotReturned.objects.all()
        # We only want BallotReturned values associated with polling locations
        ballot_returned_list = ballot_returned_list.exclude(polling_location_we_vote_id__isnull=True)
        ballot_returned_list = ballot_returned_list.exclude(polling_location_we_vote_id__iexact='')
        if positive_value_exists(google_civic_election_id):
            ballot_returned_list = ballot_returned_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            ballot_returned_list = ballot_returned_list.filter(normalized_state__iexact=state_code)

        # serializer = BallotReturnedSerializer(ballot_returned_list, many=True)
        # return Response(serializer.data)
        if ballot_returned_list:
            ballot_returned_list = ballot_returned_list.extra(
                select={'election_day_text': "to_char(election_date, 'YYYY-MM-DD')"})
            ballot_returned_list_dict = ballot_returned_list.values('election_day_text', 'election_description_text',
                                                                    'google_civic_election_id', 'latitude', 'longitude',
                                                                    'normalized_line1', 'normalized_line2',
                                                                    'normalized_city', 'normalized_state',
                                                                    'normalized_zip', 'polling_location_we_vote_id',
                                                                    'text_for_map_search')
            if ballot_returned_list_dict:
                ballot_returned_list_json = list(ballot_returned_list_dict)
                return HttpResponse(json.dumps(ballot_returned_list_json), content_type='application/json')
    except Exception as e:
        pass

    json_data = {
        'success': False,
        'status': 'BALLOT_RETURNED_LIST_MISSING'
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@login_required
def ballot_items_import_from_master_server_view(request):
    """
    Retrieve Saved Ballot Items for election nnnn

    :param request:
    :return:
    """

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = ballot_items_import_from_master_server(request, google_civic_election_id, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Ballot Items import completed. '
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
def ballot_returned_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    print("Importing ballot returned from master server")
    results = ballot_returned_import_from_master_server(request, google_civic_election_id, state_code)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Ballot Returned import completed. '
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
def ballot_item_list_by_polling_location_edit_view(request, polling_location_we_vote_id):
    ballot_returned_id = 0
    return ballot_item_list_edit_view(request, ballot_returned_id, polling_location_we_vote_id)


@login_required
def ballot_item_list_edit_view(request, ballot_returned_id, polling_location_we_vote_id_from_path=''):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We can accept either, but give preference to polling_location_id
    polling_location_id = request.GET.get('polling_location_id', 0)
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', '')
    polling_location_city = request.GET.get('polling_location_city', '')
    polling_location_zip = request.GET.get('polling_location_zip', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', '')

    ballot_returned_found = False
    ballot_returned = BallotReturned()

    ballot_returned_manager = BallotReturnedManager()
    voter_id = 0
    if positive_value_exists(ballot_returned_id) or positive_value_exists(polling_location_we_vote_id_from_path):
        results = ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id, google_civic_election_id, voter_id, polling_location_we_vote_id_from_path)
        if results['ballot_returned_found']:
            ballot_returned = results['ballot_returned']
            ballot_returned_found = True
            google_civic_election_id = ballot_returned.google_civic_election_id

    election = Election()
    election_state = ''
    contest_measure_list = []
    contest_office_list = []
    if google_civic_election_id:
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            election_state = election.get_election_state()

        # Get a list of offices for this election so we can create drop downs
        try:
            contest_office_list = ContestOffice.objects.order_by('office_name')
            contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
        except Exception as e:
            contest_office_list = []

        # Get a list of measures for this election so we can create drop downs
        try:
            contest_measure_list = ContestMeasure.objects.order_by('measure_title')
            contest_measure_list = contest_measure_list.filter(google_civic_election_id=google_civic_election_id)
        except Exception as e:
            contest_measure_list = []
    else:
        messages.add_message(request, messages.ERROR, 'In order to create a \'ballot_returned\' entry, '
                                                      'a google_civic_election_id is required.')

    polling_location_found = False
    polling_location = PollingLocation()
    polling_location_manager = PollingLocationManager()
    polling_location_state_code = ""
    if positive_value_exists(polling_location_id):
        results = polling_location_manager.retrieve_polling_location_by_id(polling_location_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_we_vote_id = polling_location.we_vote_id
            polling_location_id = polling_location.id
            polling_location_state_code = polling_location.state
            polling_location_found = True
    if not polling_location_found and positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_we_vote_id = polling_location.we_vote_id
            polling_location_id = polling_location.id
            polling_location_state_code = polling_location.state
            polling_location_found = True

    polling_location_list = []
    if not polling_location_found:
        results = polling_location_manager.retrieve_polling_locations_in_city_or_state(
            election_state, polling_location_city, polling_location_zip)
        if results['polling_location_list_found']:
            polling_location_list = results['polling_location_list']

    messages_on_stage = get_messages(request)
    ballot_item_list = []
    ballot_item_list_modified = []
    candidate_campaign_list_manager = CandidateCampaignListManager()
    contest_office_we_vote_ids_already_on_ballot = []
    contest_offices_to_choose_list = []
    if ballot_returned_found:
        # Get a list of ballot_items stored at this location
        ballot_item_list_manager = BallotItemListManager()
        if positive_value_exists(ballot_returned.polling_location_we_vote_id):
            results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                ballot_returned.polling_location_we_vote_id, google_civic_election_id)
            if results['ballot_item_list_found']:
                ballot_item_list = results['ballot_item_list']
                ballot_item_list_modified = []
                for one_ballot_item in ballot_item_list:
                    one_ballot_item.candidates_string = ""
                    if positive_value_exists(one_ballot_item.contest_office_we_vote_id):
                        contest_office_we_vote_ids_already_on_ballot.append(one_ballot_item.contest_office_we_vote_id)
                        candidate_results = candidate_campaign_list_manager.retrieve_all_candidates_for_office(
                            0, one_ballot_item.contest_office_we_vote_id)
                        if candidate_results['candidate_list_found']:
                            candidate_list = candidate_results['candidate_list']
                            for one_candidate in candidate_list:
                                one_ballot_item.candidates_string += one_candidate.display_candidate_name() + ", "
                    ballot_item_list_modified.append(one_ballot_item)

    # Remove the offices that are already attached to this ballot location
    for one_contest_office in contest_office_list:
        if one_contest_office.we_vote_id not in contest_office_we_vote_ids_already_on_ballot:
            contest_offices_to_choose_list.append(one_contest_office)

    if positive_value_exists(google_civic_election_id):
        election_list = []
    else:
        # Only offer an election list if a google_civic_election_id was not passed in
        election_query = Election.objects.filter(Q(state_code=None) | Q(state_code="") |
                                                 Q(state_code__iexact="na") |
                                                 Q(state_code__iexact=polling_location_state_code) |
                                                 Q(state_code__iexact=state_code))
        election_query = election_query.order_by('-election_day_text')
        election_list = list(election_query)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'ballot_returned':              ballot_returned,
        'ballot_returned_id':           ballot_returned_id,
        'election':                     election,
        'election_list':                election_list,
        'measure_list':                 contest_measure_list,
        'office_list':                  contest_office_list,
        'contest_offices_to_choose_list':   contest_offices_to_choose_list,
        'polling_location_id':          polling_location_id,
        'polling_location_we_vote_id':  polling_location_we_vote_id,
        'polling_location_found':       polling_location_found,
        'polling_location':             polling_location,
        'polling_location_list':        polling_location_list,
        'polling_location_city':        polling_location_city,
        'polling_location_zip':         polling_location_zip,
        'ballot_item_list':             ballot_item_list_modified,
        'google_civic_election_id':     google_civic_election_id,
    }
    return render(request, 'ballot/ballot_item_list_edit.html', template_values)


@login_required
def ballot_item_list_edit_process_view(request):
    """
    Process the new or edit ballot form
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    ballot_returned_id = convert_to_int(request.POST.get('ballot_returned_id', 0))
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')
    polling_location_id = convert_to_int(request.POST.get('polling_location_id', 0))
    polling_location_we_vote_id = ""
    polling_location_city = request.POST.get('polling_location_city', '')
    polling_location_zip = request.POST.get('polling_location_zip', '')
    contest_office1_id = request.POST.get('contest_office1_id', 0)
    contest_office1_order = request.POST.get('contest_office1_order', 0)
    contest_measure1_id = request.POST.get('contest_measure1_id', 0)

    ballot_location_display_option_on = request.POST.get('ballot_location_display_option_on', False)
    ballot_location_display_name = request.POST.get('ballot_location_display_name', '')
    ballot_location_shortcut = request.POST.get('ballot_location_shortcut', '')

    # Find existing ballot_returned
    ballot_returned_found = False
    ballot_returned = BallotReturned()
    if positive_value_exists(ballot_returned_id):
        try:
            ballot_returned_query = BallotReturned.objects.filter(id=ballot_returned_id)
            if len(ballot_returned_query):
                ballot_returned = ballot_returned_query[0]
                ballot_returned_found = True
                if not positive_value_exists(polling_location_id):
                    polling_location_we_vote_id = ballot_returned.polling_location_we_vote_id
        except Exception as e:
            pass

    election_manager = ElectionManager()
    polling_location_manager = PollingLocationManager()
    polling_location = PollingLocation()
    polling_location_found = False
    try:
        if ballot_returned_found:
            # Update

            # Check to see if this is a We Vote-created election
            is_we_vote_google_civic_election_id = True \
                if convert_to_int(ballot_returned.google_civic_election_id) >= 1000000 \
                else False

            results = election_manager.retrieve_election(ballot_returned.google_civic_election_id)
            if results['election_found']:
                election = results['election']
                election_local_id = election.id
                if not positive_value_exists(state_code):
                    state_code = election.state_code

            # polling_location must be found
            # We cannot change a polling location once saved, so we ignore the incoming polling_location_id here
            results = polling_location_manager.retrieve_polling_location_by_id(
                0, ballot_returned.polling_location_we_vote_id)
            if results['polling_location_found']:
                polling_location = results['polling_location']
                polling_location_we_vote_id = polling_location.we_vote_id
                polling_location_found = True
                if not positive_value_exists(state_code):
                    state_code = polling_location.state
        else:
            # Create new ballot_returned entry
            # election must be found
            election_results = election_manager.retrieve_election(google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                election_local_id = election.id
                state_code = election.get_election_state()
            else:
                messages.add_message(request, messages.ERROR, 'Could not find election -- '
                                                              'required to save ballot_returned.')
                return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                            "?google_civic_election_id=" + str(google_civic_election_id) +
                                            "&state_code=" + str(state_code) +
                                            "&polling_location_id=" + str(polling_location_id) +
                                            "&polling_location_city=" + polling_location_city +
                                            "&polling_location_zip=" + str(polling_location_zip)
                                            )

            # polling_location must be found
            if positive_value_exists(polling_location_id):
                results = polling_location_manager.retrieve_polling_location_by_id(polling_location_id)
                if results['polling_location_found']:
                    polling_location = results['polling_location']
                    polling_location_we_vote_id = polling_location.we_vote_id
                    polling_location_found = True
            elif positive_value_exists(polling_location_we_vote_id):
                results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
                if results['polling_location_found']:
                    polling_location = results['polling_location']
                    polling_location_we_vote_id = polling_location.we_vote_id
                    polling_location_found = True

            if not polling_location_found:
                messages.add_message(request, messages.ERROR, 'Could not find polling_location -- '
                                                              'required to save ballot_returned.')
                return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                            "?google_civic_election_id=" + str(google_civic_election_id) +
                                            "&state_code=" + str(state_code) +
                                            "&polling_location_id=" + str(polling_location_id) +
                                            "&polling_location_city=" + polling_location_city +
                                            "&polling_location_zip=" + str(polling_location_zip)
                                            )

            ballot_returned = BallotReturned(
                election_date=election.election_day_text,
                election_description_text=election.election_name,
                google_civic_election_id=google_civic_election_id,
                polling_location_we_vote_id=polling_location.we_vote_id,
                normalized_city=polling_location.city,
                normalized_line1=polling_location.line1,
                normalized_line2=polling_location.line2,
                normalized_state=polling_location.state,
                normalized_zip=polling_location.get_formatted_zip(),
                ballot_location_display_name=ballot_location_display_name,
                ballot_location_display_option_on=ballot_location_display_option_on,
                ballot_location_shortcut=ballot_location_shortcut,
                text_for_map_search=polling_location.get_text_for_map_search(),
            )
            ballot_returned.save()
            ballot_returned_id = ballot_returned.id
            ballot_returned_found = True
            messages.add_message(request, messages.INFO, 'New ballot_returned saved.')

        # #######################################
        # Update the ballot_returned entry
        if ballot_returned_found:
            if positive_value_exists(ballot_returned.text_for_map_search):
                try:
                    if not ballot_returned.latitude or not ballot_returned.longitude:
                        # Make sure we have saved a latitude and longitude for the ballot_returned entry
                        google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
                        location = google_client.geocode(ballot_returned.text_for_map_search)
                        if location is None:
                            status += 'Could not find location matching "{}"'.format(ballot_returned.text_for_map_search)
                            logger.debug(status)
                        else:
                            ballot_returned.latitude = location.latitude
                            ballot_returned.longitude = location.longitude
                except Exception as e:
                    status += "EXCEPTION with get_geocoder_for_service "
            ballot_returned.ballot_location_display_option_on = ballot_location_display_option_on
            ballot_returned.ballot_location_display_name = ballot_location_display_name
            ballot_returned.ballot_location_shortcut = ballot_location_shortcut

            ballot_returned.save()
            messages.add_message(request, messages.INFO, 'Ballot_returned updated.')

        # #######################################
        # Now create new ballot_item entries
        ballot_item_manager = BallotItemManager()
        ballot_item_list_manager = BallotItemListManager()

        # Contest Office 1
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(contest_office1_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            ballot_item_display_name = contest_office.office_name
            google_ballot_placement = 0
            measure_subtitle = ''
            local_ballot_order = contest_office1_order if positive_value_exists(contest_office1_order) else 0
            contest_measure_id = 0
            contest_measure_we_vote_id = ""
            if not positive_value_exists(state_code):
                state_code = contest_office.state_code

            results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location.we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle, local_ballot_order,
                contest_office.id, contest_office.we_vote_id,
                contest_measure_id, contest_measure_we_vote_id, state_code)

            if results['new_ballot_item_created']:
                messages.add_message(request, messages.INFO, 'Office 1 added.')
            else:
                messages.add_message(request, messages.ERROR, 'Office 1 could not be added.')

        # Contest Measure 1
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure(contest_measure1_id)
        if results['contest_measure_found']:
            contest_measure = results['contest_measure']

            google_ballot_placement = 0
            ballot_item_display_name = contest_measure.measure_title
            contest_office_id = 0
            contest_office_we_vote_id = ''
            local_ballot_order = 0
            if not positive_value_exists(state_code):
                state_code = contest_measure.state_code

            ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location.we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, contest_measure.measure_subtitle, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure.id, contest_measure.we_vote_id, state_code)

        # Update the ballot item order
        if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
            ballot_item_list_results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                polling_location_we_vote_id, google_civic_election_id)
            if ballot_item_list_results['ballot_item_list_found']:
                ballot_item_list = ballot_item_list_results['ballot_item_list']
                local_ballot_order_count = 0
                for one_ballot_item in ballot_item_list:
                    try:
                        local_ballot_order_count += 1
                        local_ballot_order_key = 'local_ballot_order_' + str(one_ballot_item.id)
                        local_ballot_order = request.POST.get(local_ballot_order_key, local_ballot_order_count)
                        if local_ballot_order:
                            one_ballot_item.local_ballot_order = local_ballot_order
                            one_ballot_item.save()
                    except Exception as e:
                        pass

    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save ballot_returned.')

    return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code) +
                                "&polling_location_id=" + str(polling_location_id) +
                                "&polling_location_city=" + polling_location_city +
                                "&polling_location_zip=" + str(polling_location_zip)
                                )


@login_required
def ballot_items_repair_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We can accept either, but give preference to polling_location_id
    local_election_id = request.GET.get('local_election_id', 0)
    local_election_id = convert_to_int(local_election_id)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    state_code = request.GET.get('state_code', '')

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, 'Either google_civic_election_id or state_code required.')
        return HttpResponseRedirect(reverse('election:election_summary', args=(local_election_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = repair_ballot_items_for_election(google_civic_election_id)
    messages.add_message(request, messages.INFO, results['status'])

    return HttpResponseRedirect(reverse('election:election_summary', args=(local_election_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&state_code=" + str(state_code))


@login_required
def update_ballot_returned_with_latitude_and_longitude_view(request):
    """
    Cycle through all of the specified BallotReturned entries and look up latitude and longitude
    :param request:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ballot_returned_id = convert_to_int(request.GET.get('ballot_returned_id', 0))
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    latitude_and_longitude_updated_count = 0
    latitude_and_longitude_not_updated_count = 0
    errors_status = ""
    polling_location_updated_count = 0
    polling_location_not_updated_count = 0

    ballot_returned_manager = BallotReturnedManager()
    polling_location_manager = PollingLocationManager()
    if positive_value_exists(ballot_returned_id):
        # Find existing ballot_returned
        if positive_value_exists(ballot_returned_id):
            try:
                ballot_returned_query = BallotReturned.objects.filter(id=ballot_returned_id)
                if len(ballot_returned_query):
                    ballot_returned = ballot_returned_query[0]
                    ballot_returned_results = \
                        ballot_returned_manager.populate_latitude_and_longitude_for_ballot_returned(ballot_returned)
                    if ballot_returned_results['success']:
                        latitude_and_longitude_updated_count += 1
                    else:
                        latitude_and_longitude_not_updated_count += 1
                        errors_status += ballot_returned_results['status']

            except Exception as e:
                pass
    else:
        # Gather the list of ballot_returned entries that need to be updated
        ballot_returned_query = BallotReturned.objects.order_by('id')
        ballot_returned_query = ballot_returned_query.filter(Q(latitude=None) | Q(latitude=0))
        # Don't retrieve entries for voters
        ballot_returned_query = ballot_returned_query.exclude(Q(polling_location_we_vote_id=None) |
                                                              Q(polling_location_we_vote_id=""))
        if positive_value_exists(google_civic_election_id):
            ballot_returned_query = ballot_returned_query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            ballot_returned_query = ballot_returned_query.filter(normalized_state__iexact=state_code)
        # Limit to 200 because that is all that seems to store anyways with each call
        ballot_returned_query = ballot_returned_query[:100]

        rate_limit_count = 0
        for ballot_returned in ballot_returned_query:
            rate_limit_count += 1
            ballot_returned_results = ballot_returned_manager.populate_latitude_and_longitude_for_ballot_returned(
                 ballot_returned)
            if ballot_returned_results['success']:
                # Keep track of the number we have processed since last break, since we can only request 10 per second
                latitude_and_longitude_updated_count += 1
            else:
                latitude_and_longitude_not_updated_count += 1
                errors_status += ballot_returned_results['status']

            if rate_limit_count >= 10:
                time.sleep(1)
                # After pause, reset the limit count
                rate_limit_count = 0

            if ballot_returned_results['geocoder_quota_exceeded']:
                break

        # Write the lat/long data that we have back to the polling location table
        ballot_returned_query = BallotReturned.objects.order_by('id')
        ballot_returned_query = ballot_returned_query.exclude(Q(latitude=None) | Q(latitude=0))  # Exclude empty entries
        ballot_returned_query = ballot_returned_query.exclude(Q(polling_location_we_vote_id=None) |
                                                              Q(polling_location_we_vote_id=""))
        if positive_value_exists(google_civic_election_id):
            ballot_returned_query = ballot_returned_query.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            ballot_returned_query = ballot_returned_query.filter(normalized_state__iexact=state_code)
        for ballot_returned in ballot_returned_query:
            if positive_value_exists(ballot_returned.polling_location_we_vote_id) \
                    and ballot_returned.latitude \
                    and ballot_returned.longitude:
                results = polling_location_manager.retrieve_polling_location_by_id(
                    0, ballot_returned.polling_location_we_vote_id)
                if results['polling_location_found']:
                    polling_location = results['polling_location']
                    if not polling_location.latitude or \
                            not polling_location.longitude:
                        try:
                            polling_location.latitude = ballot_returned.latitude
                            polling_location.longitude = ballot_returned.longitude
                            polling_location.save()
                            polling_location_updated_count += 1
                        except Exception as e:
                            polling_location_not_updated_count += 1

    status_print_list = ""
    errors_status = errors_status[:155]  # We cut off the string so we don't overwhelm the message system

    status_print_list += "BallotReturned entries updated with lat/long info: " + \
                         str(latitude_and_longitude_updated_count) + "<br />" + \
                         "not updated: " + str(latitude_and_longitude_not_updated_count) + \
                         ", errors: " + errors_status + "<br />"
    if positive_value_exists(polling_location_updated_count) \
            or positive_value_exists(polling_location_not_updated_count):
        status_print_list += "polling_location_updated_count: " + str(polling_location_updated_count) + ", "
        status_print_list += "polling_location_not_updated_count: " + str(polling_location_not_updated_count) + " "
        status_print_list += "<br />"

    messages.add_message(request, messages.INFO, status_print_list)

    if positive_value_exists(google_civic_election_id):
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_election(google_civic_election_id)
        if election_results['election_found']:
            election = election_results['election']
            local_election_id = election.id
            return HttpResponseRedirect(reverse('election:election_summary', args=(local_election_id,)) +
                                        "?state_code=" + state_code)

    return HttpResponseRedirect(reverse('election:election_list', args=()) + "?state_code=" + state_code)

