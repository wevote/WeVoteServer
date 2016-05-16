# ballot/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItem, BallotItemListManager, BallotItemManager, BallotReturned, BallotReturnedManager
from .serializers import BallotItemSerializer, BallotReturnedSerializer
from admin_tools.views import redirect_to_sign_in_page
from office.models import ContestOffice, ContestOfficeManager
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election, ElectionManager
from measure.models import ContestMeasureManager
from polling_location.models import PollingLocation, PollingLocationManager
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
class BallotItemsSyncOutView(APIView):
    def get(self, request, format=None):
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

        ballot_item_list = BallotItem.objects.all()
        # We only want BallotItem values associated with polling locations
        ballot_item_list.exclude(polling_location_we_vote_id__isnull=True).exclude(
            polling_location_we_vote_id__exact='')
        if positive_value_exists(google_civic_election_id):
            ballot_item_list = ballot_item_list.filter(google_civic_election_id=google_civic_election_id)

        serializer = BallotItemSerializer(ballot_item_list, many=True)
        return Response(serializer.data)


# This page does not need to be protected.
class BallotReturnedSyncOutView(APIView):
    def get(self, request, format=None):
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

        ballot_returned_list = BallotReturned.objects.all()
        # We only want BallotReturned values associated with polling locations
        ballot_returned_list.exclude(polling_location_we_vote_id__isnull=True).exclude(
            polling_location_we_vote_id__exact='')
        if positive_value_exists(google_civic_election_id):
            ballot_returned_list = ballot_returned_list.filter(google_civic_election_id=google_civic_election_id)

        serializer = BallotReturnedSerializer(ballot_returned_list, many=True)
        return Response(serializer.data)


@login_required
def ballot_items_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    results = candidates_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Candidates import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Master data not imported (local duplicates found): '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id))


@login_required
def ballot_returned_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    results = candidates_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Candidates import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Master data not imported (local duplicates found): '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id))


@login_required
def ballot_item_list_edit_view(request, ballot_returned_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We can accept either, but give preference to polling_location_id
    polling_location_id = request.GET.get('polling_location_id', 0)
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', '')
    polling_location_city = request.GET.get('polling_location_city', '')
    polling_location_zip = request.GET.get('polling_location_zip', '')

    ballot_returned_found = False
    ballot_returned = BallotReturned()
    contest_office_id = 0
    contest_office_list = []

    ballot_returned_manager = BallotReturnedManager()
    results = ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id)
    if results['ballot_returned_found']:
        ballot_returned = results['ballot_returned']
        ballot_returned_found = True
        google_civic_election_id = ballot_returned.google_civic_election_id
    else:
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        google_civic_election_id = convert_to_int(google_civic_election_id)

    election = Election()
    election_state = ''
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
    else:
        messages.add_message(request, messages.ERROR, 'In order to create a \'ballot_returned\' entry, '
                                                      'a google_civic_election_id is required.')

    polling_location_found = False
    polling_location = PollingLocation()
    polling_location_manager = PollingLocationManager()
    if positive_value_exists(polling_location_id):
        results = polling_location_manager.retrieve_polling_location_by_id(polling_location_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_found = True
    if not polling_location_found and positive_value_exists(polling_location_we_vote_id):
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            polling_location_found = True

    polling_location_list = []
    if not polling_location_found:
        results = polling_location_manager.retrieve_polling_locations_in_city_or_state(
            election_state, polling_location_city, polling_location_zip)
        if results['polling_location_list_found']:
            polling_location_list = results['polling_location_list']

    messages_on_stage = get_messages(request)
    ballot_item_list = []
    if ballot_returned_found:
        # Get a list of ballot_items stored at this location
        ballot_item_list_manager = BallotItemListManager()
        if positive_value_exists(ballot_returned.polling_location_we_vote_id):
            results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                ballot_returned.polling_location_we_vote_id, google_civic_election_id)
            if results['ballot_item_list_found']:
                ballot_item_list = results['ballot_item_list']

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'ballot_returned':              ballot_returned,
        'ballot_returned_id':           ballot_returned_id,
        'election':                     election,
        'office_list':                  contest_office_list,
        'polling_location_we_vote_id':  polling_location_we_vote_id,
        'polling_location_found':       polling_location_found,
        'polling_location':             polling_location,
        'polling_location_list':        polling_location_list,
        'polling_location_city':        polling_location_city,
        'polling_location_zip':         polling_location_zip,
        'ballot_item_list':             ballot_item_list,
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

    ballot_returned_id = convert_to_int(request.POST.get('ballot_returned_id', 0))
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    polling_location_id = convert_to_int(request.POST.get('polling_location_id', 0))
    polling_location_city = request.POST.get('polling_location_city', '')
    polling_location_zip = request.POST.get('polling_location_zip', '')
    contest_office1_id = request.POST.get('contest_office1_id', 0)
    contest_office1_order = request.POST.get('contest_office1_order', 0)
    contest_measure1_id = request.POST.get('contest_measure1_id', 0)

    election_local_id = 0

    # Find existing ballot_returned
    ballot_returned_found = False
    ballot_returned = BallotReturned()
    if positive_value_exists(ballot_returned_id):
        try:
            ballot_returned_query = BallotReturned.objects.filter(id=ballot_returned_id)
            if len(ballot_returned_query):
                ballot_returned = ballot_returned_query[0]
                ballot_returned_found = True
        except Exception as e:
            pass

    election_manager = ElectionManager()
    polling_location_manager = PollingLocationManager()
    polling_location = PollingLocation()
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

            # polling_location must be found
            # We cannot change a polling location once saved, so we ignore the incoming polling_location_id here
            results = polling_location_manager.retrieve_polling_location_by_id(
                0, ballot_returned.polling_location_we_vote_id)
            if results['polling_location_found']:
                polling_location = results['polling_location']
                polling_location_found = True
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
                                            "&polling_location_id=" + str(polling_location_id) +
                                            "&polling_location_city=" + polling_location_city +
                                            "&polling_location_zip=" + str(polling_location_zip)
                                            )

            # polling_location must be found
            if positive_value_exists(polling_location_id):
                results = polling_location_manager.retrieve_polling_location_by_id(polling_location_id)
                if results['polling_location_found']:
                    polling_location = results['polling_location']
                    polling_location_found = True

            if not polling_location_found:
                messages.add_message(request, messages.ERROR, 'Could not find polling_location -- '
                                                              'required to save ballot_returned.')
                return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                            "?google_civic_election_id=" + str(google_civic_election_id) +
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
                text_for_map_search=polling_location.get_text_for_map_search(),
            )
            ballot_returned.save()
            ballot_returned_id = ballot_returned.id
            messages.add_message(request, messages.INFO, 'New ballot_returned saved.')

        # #######################################
        # Now create new ballot_item entries

        # Contest Office 1
        ballot_item_manager = BallotItemManager()
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(contest_office1_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            ballot_item_display_name = contest_office.office_name

            google_ballot_placement = 0
            measure_subtitle = ''
            local_ballot_order = contest_office1_order if positive_value_exists(contest_office1_order) else 0

            results = ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location.we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle, local_ballot_order,
                contest_office.id, contest_office.we_vote_id)

            if results['new_ballot_item_created']:
                messages.add_message(request, messages.INFO, 'Office 1 added.')
            else:
                messages.add_message(request, messages.ERROR, 'Office 1 could not be added.')

        # Contest Measure 1
        ballot_item_manager = BallotItemManager()
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure(contest_measure1_id)
        if results['contest_measure_found']:
            contest_measure = results['contest_measure']

            google_ballot_placement = 0
            ballot_item_display_name = contest_measure.measure_title
            contest_office_id = 0
            contest_office_we_vote_id = ''
            local_ballot_order = 0

            ballot_item_manager.update_or_create_ballot_item_for_polling_location(
                polling_location.we_vote_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, contest_measure.measure_subtitle, local_ballot_order,
                contest_office_id, contest_office_we_vote_id,
                contest_measure.id)
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save ballot_returned.')

    return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&polling_location_id=" + str(polling_location_id) +
                                "&polling_location_city=" + polling_location_city +
                                "&polling_location_zip=" + str(polling_location_zip)
                                )
