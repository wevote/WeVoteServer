# import_export_google_civic/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_representatives_from_google_civic_api, store_representatives_from_google_civic_api
from admin_tools.views import redirect_to_sign_in_page
from ballot.controllers import refresh_voter_ballots_from_polling_location
from ballot.models import BallotItemListManager, BallotReturnedListManager, BallotReturnedManager, \
    VoterBallotSavedManager
from config.base import get_environment_variable
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from polling_location.models import PollingLocation
from wevote_settings.models import RemoteRequestHistoryManager
from voter.models import VoterAddressManager, VoterDeviceLinkManager, voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_device_id, positive_value_exists, STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


@login_required
def retrieve_representatives_for_many_addresses_view(request):  # THIS FUNCTION TO BE MIGRATED TO REPRESENTATIVES
    """
    Reach out to Google and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those polling locations, enough that we are caching all of the possible ballot items
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    import_limit = convert_to_int(request.GET.get('import_limit', 500))

    try:
        if positive_value_exists(election_local_id):
            election_on_stage = Election.objects.get(id=election_local_id)
            google_civic_election_id = election_on_stage.google_civic_election_id
        else:
            election_on_stage = Election.objects.get(google_civic_election_id=google_civic_election_id)
            election_local_id = election_on_stage.id
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code):
        state_code = election_on_stage.get_election_state()
        # if not positive_value_exists(state_code):
        #     state_code = "CA"  # TODO DALE Temp for 2016

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        # If Google wasn't able to return ballot data in the past ignore that polling location
        polling_location_count_query = polling_location_count_query.filter(
            google_response_address_not_found__isnull=True)
        polling_location_count = polling_location_count_query.count()

        polling_location_query = PollingLocation.objects.all()
        polling_location_query = polling_location_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.filter(
            google_response_address_not_found__isnull=True)
        # We used to have a limit of 500 ballots to pull per election, but now retrieve all
        # Ordering by "location_name" creates a bit of (locational) random order
        polling_location_list = polling_location_query.order_by('location_name')[:import_limit]
    except PollingLocation.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations returned for the state \'{state}\'. (error 2)'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    locations_retrieved = 0
    locations_not_retrieved = 0
    ballots_with_contests_retrieved = 0
    polling_locations_retrieved = 0
    ballots_with_election_administration_data = 0
    ballots_refreshed = 0
    # We used to only retrieve up to 500 locations from each state, but we don't limit now
    # # We retrieve 10% of the total polling locations, which should give us coverage of the entire election
    # number_of_polling_locations_to_retrieve = int(.1 * polling_location_count)
    ballot_returned_manager = BallotReturnedManager()
    rate_limit_count = 0
    # Step though our set of polling locations, until we find one that contains a ballot.  Some won't contain ballots
    # due to data quality issues.
    for polling_location in polling_location_list:
        success = False
        # Get the address for this polling place, and then retrieve the ballot from Google Civic API
        results = polling_location.get_text_for_map_search_results()
        text_for_map_search = results['text_for_map_search']
        representatives_results = retrieve_representatives_from_google_civic_api(
            text_for_map_search, election_on_stage.google_civic_election_id)
        if representatives_results['success']:
            one_ballot_json = representatives_results['structured_json']
            store_representatives_results = store_representatives_from_google_civic_api(one_ballot_json, 0,
                                                                              polling_location.we_vote_id)
            if store_representatives_results['success']:
                success = True
                if store_representatives_results['ballot_returned_found']:
                    ballot_returned = store_representatives_results['ballot_returned']
                    ballot_returned_id = ballot_returned.id
                    # Now refresh all of the other copies of this ballot
                    if positive_value_exists(polling_location.we_vote_id) \
                            and positive_value_exists(google_civic_election_id):
                        refresh_ballot_results = refresh_voter_ballots_from_polling_location(
                            ballot_returned, google_civic_election_id)
                        ballots_refreshed += refresh_ballot_results['ballots_refreshed']
                # NOTE: We don't support retrieving ballots for polling locations AND geocoding simultaneously
                # if store_representatives_results['ballot_returned_found']:
                #     ballot_returned = store_representatives_results['ballot_returned']
                #     ballot_returned_results = \
                #         ballot_returned_manager.populate_latitude_and_longitude_for_ballot_returned(ballot_returned)
                #     if ballot_returned_results['success']:
                #         rate_limit_count += 1
                #         if rate_limit_count >= 10:  # Avoid problems with the geocoder rate limiting
                #             time.sleep(1)
                #             # After pause, reset the limit count
                #             rate_limit_count = 0
        else:
            if 'google_response_address_not_found' in representatives_results:
                if positive_value_exists(representatives_results['google_response_address_not_found']):
                    try:
                        if not polling_location.google_response_address_not_found:
                            polling_location.google_response_address_not_found = 1
                        else:
                            polling_location.google_response_address_not_found += 1
                        polling_location.save()
                        print("Updated PollingLocation google_response_address_not_found: " + str(text_for_map_search))
                    except Exception as e:
                        print("Cannot update PollingLocation: " + str(text_for_map_search))

        if success:
            locations_saved += 1
        else:
            locations_not_retrieved += 1

        if representatives_results['contests_retrieved']:
            ballots_with_contests_retrieved += 1

        # We used to only retrieve up to 500 locations from each state, but we don't limit now
        # # Break out of this loop, assuming we have a minimum number of ballots with contests retrieved
        # #  If we don't achieve the minimum number of ballots_with_contests_retrieved, break out at the emergency level
        # emergency = (locations_retrieved + locations_not_retrieved) >= (3 * number_of_polling_locations_to_retrieve)
        # if ((locations_retrieved + locations_not_retrieved) >= number_of_polling_locations_to_retrieve and
        #         ballots_with_contests_retrieved > 20) or emergency:
        #     break

    total_retrieved = locations_retrieved + locations_not_retrieved
    if locations_retrieved > 0:
        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Google Civic for the {election_name}. '
                             '(polling_locations_retrieved: {polling_locations_retrieved}, '
                             'ballots_with_election_administration_data: {ballots_with_election_administration_data}, '
                             'ballots retrieved: {locations_retrieved}, '
                             '(with contests: {ballots_with_contests_retrieved}), '
                             'not retrieved: {locations_not_retrieved}, '
                             'total: {total}), '
                             'ballots refreshed: {ballots_refreshed}'.format(
                                 polling_locations_retrieved=polling_locations_retrieved,
                                 ballots_with_election_administration_data=ballots_with_election_administration_data,
                                 ballots_refreshed=ballots_refreshed,
                                 locations_retrieved=locations_retrieved,
                                 locations_not_retrieved=locations_not_retrieved,
                                 ballots_with_contests_retrieved=ballots_with_contests_retrieved,
                                 election_name=election_on_stage.election_name,
                                 total=total_retrieved))
    else:
        messages.add_message(request, messages.ERROR,
                             'Ballot data NOT retrieved from Google Civic for the {election_name}. '
                             '(polling_locations_retrieved: {polling_locations_retrieved}, '
                             'ballots_with_election_administration_data: {ballots_with_election_administration_data}, '
                             'ballots retrieved: {locations_retrieved}, '
                             '(with contests: {ballots_with_contests_retrieved}), '
                             'not retrieved: {locations_not_retrieved}, '
                             'total: {total})'.format(
                                 polling_locations_retrieved=polling_locations_retrieved,
                                 ballots_with_election_administration_data=ballots_with_election_administration_data,
                                 locations_retrieved=locations_retrieved,
                                 locations_not_retrieved=locations_not_retrieved,
                                 ballots_with_contests_retrieved=ballots_with_contests_retrieved,
                                 election_name=election_on_stage.election_name,
                                 total=total_retrieved))
    return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))


@login_required
def retrieve_representatives_for_one_address_view(request):
    """
    Reach out to Google and retrieve civicinfo.representatives.representativeInfoByAddress
    (for one address, typically from a polling location)
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    ballot_returned_id = convert_to_int(request.GET.get('ballot_returned_id', 0))
    state_code = request.GET.get('state_code', '')
    one_ballot_json = {}
    voter_id = convert_to_int(request.GET.get('voter_id', 0))
    text_for_map_search = ""
    locations_retrieved = 0

    one_ballot_json_found = False
    if positive_value_exists(polling_location_we_vote_id):
        try:
            polling_location = PollingLocation.objects.get(we_vote_id__iexact=polling_location_we_vote_id)
        except PollingLocation.DoesNotExist:
            messages.add_message(request, messages.INFO,
                                 'Polling location not found. ')
            return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                                args=(polling_location_we_vote_id,)) +
                                        "?state_code=" + str(state_code) +
                                        "&google_civic_election_id=" + str(google_civic_election_id)
                                        )
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 'Polling location could not be found. ')
            return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                                args=(polling_location_we_vote_id,)) +
                                        "?state_code=" + str(state_code) +
                                        "&google_civic_election_id=" + str(google_civic_election_id)
                                        )
        # Get the address for this polling place, and then retrieve the ballot from Google Civic API
        results = polling_location.get_text_for_map_search_results()
        text_for_map_search = results['text_for_map_search']
        representatives_results = retrieve_representatives_from_google_civic_api(text_for_map_search)
        if representatives_results['success']:
            one_ballot_json = representatives_results['structured_json']
            one_ballot_json_found = True
        if representatives_results['locations_retrieved']:
            locations_retrieved += 1
    elif positive_value_exists(voter_id):
        if positive_value_exists(text_for_map_search):
            representatives_results = retrieve_representatives_from_google_civic_api(text_for_map_search)
            if representatives_results['success']:
                one_ballot_json = representatives_results['structured_json']
                one_ballot_json_found = True
            if representatives_results['locations_retrieved']:
                locations_retrieved += 1

    locations_saved = 0
    locations_not_saved = 0
    ballots_refreshed = 0
    success = False
    if one_ballot_json_found:
        store_representatives_results = store_representatives_from_google_civic_api(
            one_ballot_json, voter_id, polling_location_we_vote_id)
        if store_representatives_results['success']:
            success = True
            # if store_representatives_results['ballot_returned_found']:
            #     ballot_returned = store_representatives_results['ballot_returned']
            #     ballot_returned_id = ballot_returned.id
            #     # Now refresh all of the other copies of this ballot
            #     if positive_value_exists(polling_location_we_vote_id) \
            #             and positive_value_exists(google_civic_election_id):
            #         refresh_ballot_results = refresh_voter_ballots_from_polling_location(
            #             ballot_returned, google_civic_election_id)
            #         ballots_refreshed = refresh_ballot_results['ballots_refreshed']
            #     elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
            #         # Nothing else to be done
            #         pass

    if success:
        locations_saved += 1
    else:
        locations_not_saved += 1

    if locations_saved > 0:
        total_retrieved = locations_saved + locations_not_saved
        messages.add_message(request, messages.INFO,
                             'Representatives saved from Google Civic. '
                             '(locations_saved: {locations_saved} '
                             'locations_not_saved: {locations_not_saved}, '
                             'total: {total}), '
                             'ballots refreshed: {ballots_refreshed}'.format(
                                 ballots_refreshed=ballots_refreshed,
                                 locations_saved=locations_saved,
                                 locations_not_saved=locations_not_saved,
                                 total=total_retrieved))
    else:
        messages.add_message(request, messages.ERROR,
                             'Representatives NOT saved from Google Civic.'
                             ' (not retrieved: {locations_not_saved})'.format(
                                 locations_not_saved=locations_not_saved))
    return HttpResponseRedirect(reverse('polling_location:polling_location_summary_by_we_vote_id',
                                        args=(polling_location_we_vote_id,)) +
                                "?state_code=" + str(state_code) +
                                "&google_civic_election_id=" + str(google_civic_election_id)
                                )
