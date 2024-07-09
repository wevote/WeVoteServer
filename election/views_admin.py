# election/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import election_remote_retrieve, elections_import_from_master_server
from .models import Election
from admin_tools.views import redirect_to_sign_in_page
from analytics.models import AnalyticsManager
from ballot.models import BallotItem, BallotItemListManager, \
    BallotReturned, BallotReturnedListManager, BallotReturnedManager, \
    VoterBallotSaved, VoterBallotSavedManager
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager, \
    CandidateToOfficeLink
from config.base import get_environment_variable
import copy
from datetime import datetime, timedelta
from django.http import HttpResponseRedirect
from django.utils.timezone import now
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from election.models import BallotpediaElection, ElectionManager
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from image.models import WeVoteImageManager
from import_export_ballotpedia.models import BallotpediaApiCounter, BallotpediaApiCounterDailySummary, \
    BallotpediaApiCounterWeeklySummary, BallotpediaApiCounterMonthlySummary
from import_export_batches.models import BatchDescription, BatchManager, BatchProcess, \
    BatchRowActionBallotItem, \
    BatchRowActionCandidate, BatchRowActionContestOffice, BatchRowActionMeasure, BatchRowActionPosition,  \
    BatchRowTranslationMap, BatchSet
from import_export_google_civic.controllers import retrieve_one_ballot_from_google_civic_api, \
    store_one_ballot_from_google_civic_api
from import_export_google_civic.models import GoogleCivicApiCounter, GoogleCivicApiCounterDailySummary, \
    GoogleCivicApiCounterWeeklySummary, GoogleCivicApiCounterMonthlySummary
from import_export_vote_smart.models import VoteSmartApiCounter, VoteSmartApiCounterDailySummary, \
    VoteSmartApiCounterWeeklySummary, VoteSmartApiCounterMonthlySummary
from measure.models import ContestMeasure, ContestMeasureListManager
from office.models import ContestOffice, ContestOfficeListManager, ContestOfficeManager
from pledge_to_vote.models import PledgeToVoteManager
from polling_location.models import PollingLocation, PollingLocationManager
from position.models import PositionEntered, PositionForFriends, PositionListManager
import pytz
from quick_info.models import QuickInfoManager
from voter.models import VoterAddressManager, VoterDeviceLink, voter_has_authority
from voter_guide.models import VoterGuide, VoterGuidePossibility, \
    VoterGuideListManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, \
    STATE_CODE_MAP, STATE_GEOGRAPHIC_CENTER
from wevote_functions.functions_date import convert_we_vote_date_string_to_date, generate_localized_datetime_from_obj
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE
from wevote_settings.models import RemoteRequestHistoryManager

logger = wevote_functions.admin.get_logger(__name__)

ELECTIONS_SYNC_URL = get_environment_variable("ELECTIONS_SYNC_URL")  # electionsSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")

POSITIONS_GOAL_CANDIDATE_MULTIPLIER = .9


def test_view(request):
    success = True
    status = ""

    # Add delay

    # Every 5 seconds, send html to the browser (like a simple "."), before calling render after 30 seconds

    template_values = {
        'success':      success,
        'status':       status,
    }
    return render(request, 'election/election_list.html', template_values)


@login_required
def ballotpedia_election_delete_process_view(request):
    """
    Delete a ballotpedia election
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    ballotpedia_election_id = convert_to_int(request.POST.get('ballotpedia_election_id', 0))
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    election_manager = ElectionManager()
    election_id = 0
    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this ballotpedia election without confirmation. '
                             'Please check the checkbox to confirm you want to delete this election.')
        if positive_value_exists(google_civic_election_id):
            results = election_manager.retrieve_election(google_civic_election_id)
            if results['election_found']:
                election = results['election']
                election_id = election.id

        if positive_value_exists(election_id):
            return HttpResponseRedirect(reverse('election:election_edit', args=(election_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))
        else:
            return HttpResponseRedirect(reverse('election:election_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))

    results = election_manager.retrieve_ballotpedia_election(ballotpedia_election_id)
    if results['ballotpedia_election_found']:
        ballotpedia_election = results['ballotpedia_election']
        ballotpedia_election.delete()
        messages.add_message(request, messages.INFO, 'Ballotpedia election deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'Ballotpedia election not found.')

    if positive_value_exists(google_civic_election_id):
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            return HttpResponseRedirect(reverse('election:election_edit', args=(election.id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required
def election_all_ballots_retrieve_view(request, election_local_id=0):
    """
    Reach out to Google and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those map points, enough that we are caching all the possible ballot items
    :param request:
    :param election_local_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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

    # Check to see if we have map point data related to the region(s) covered by this election
    # We request the ballot data for each map point as a way to build up our local data
    if not positive_value_exists(state_code):
        state_code = election_on_stage.get_election_state()
        # if not positive_value_exists(state_code):
        #     state_code = "CA"  # TODO DALE Temp for 2016

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
        # If Google wasn't able to return ballot data in the past ignore that map point
        polling_location_count_query = polling_location_count_query.filter(
            google_response_address_not_found__isnull=True)
        polling_location_count = polling_location_count_query.count()

        polling_location_query = PollingLocation.objects.all()
        polling_location_query = polling_location_query.filter(state__iexact=state_code)
        polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
        polling_location_query = polling_location_query.filter(
            google_response_address_not_found__isnull=True)
        # We used to have a limit of 500 ballots to pull per election, but now retrieve all
        # Ordering by "location_name" creates a bit of (locational) random order
        polling_location_list = polling_location_query.order_by('location_name')[:import_limit]
    except PollingLocation.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No map points exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No map points returned for the state \'{state}\'. '
                             '(error 2 - election_all_ballots_retrieve_view)'.format(
                                 election_name=election_on_stage.election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    ballots_retrieved = 0
    ballots_not_retrieved = 0
    ballots_with_contests_retrieved = 0
    polling_locations_retrieved = 0
    ballots_with_election_administration_data = 0
    ballots_refreshed = 0
    # We used to only retrieve up to 500 locations from each state, but we don't limit now
    # # We retrieve 10% of the total map points, which should give us coverage of the entire election
    # number_of_polling_locations_to_retrieve = int(.1 * polling_location_count)
    ballot_returned_manager = BallotReturnedManager()
    rate_limit_count = 0
    # Step though our set of map points, until we find one that contains a ballot.  Some won't contain ballots
    # due to data quality issues.
    for polling_location in polling_location_list:
        success = False
        # Get the address for this polling place, and then retrieve the ballot from Google Civic API
        results = polling_location.get_text_for_map_search_results()
        text_for_map_search = results['text_for_map_search']
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(
            text_for_map_search, election_on_stage.google_civic_election_id)
        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']
            store_one_ballot_results = store_one_ballot_from_google_civic_api(one_ballot_json, 0,
                                                                              polling_location.we_vote_id)
            if store_one_ballot_results['success']:
                success = True
                if store_one_ballot_results['ballot_returned_found']:
                    ballot_returned = store_one_ballot_results['ballot_returned']
                    ballot_returned_id = ballot_returned.id
                    # NOTE: This routine won't work because we are caching new ballot items, so they aren't
                    #  ready to copy here
                    # # Now refresh all the other copies of this ballot
                    # if positive_value_exists(polling_location.we_vote_id) \
                    #         and positive_value_exists(google_civic_election_id):
                    #     refresh_ballot_results = refresh_voter_ballots_from_polling_location(
                    #         ballot_returned, google_civic_election_id)
                    #     ballots_refreshed += refresh_ballot_results['ballots_refreshed']
                # NOTE: We don't support retrieving ballots for map points AND geocoding simultaneously
                # if store_one_ballot_results['ballot_returned_found']:
                #     ballot_returned = store_one_ballot_results['ballot_returned']
                #     ballot_returned_results = \
                #         ballot_returned_manager.populate_latitude_and_longitude_for_ballot_returned(ballot_returned)
                #     if ballot_returned_results['success']:
                #         rate_limit_count += 1
                #         if rate_limit_count >= 10:  # Avoid problems with the geocoder rate limiting
                #             time.sleep(1)
                #             # After pause, reset the limit count
                #             rate_limit_count = 0
        else:
            if 'google_response_address_not_found' in one_ballot_results:
                if positive_value_exists(one_ballot_results['google_response_address_not_found']):
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
            ballots_retrieved += 1
        else:
            ballots_not_retrieved += 1

        if one_ballot_results['contests_retrieved']:
            ballots_with_contests_retrieved += 1

        if one_ballot_results['polling_location_retrieved']:
            polling_locations_retrieved += 1

        if one_ballot_results['election_administration_data_retrieved']:
            ballots_with_election_administration_data += 1

        # We used to only retrieve up to 500 locations from each state, but we don't limit now
        # # Break out of this loop, assuming we have a minimum number of ballots with contests retrieved
        # #  If we don't achieve the minimum number of ballots_with_contests_retrieved, break out at the emergency level
        # emergency = (ballots_retrieved + ballots_not_retrieved) >= (3 * number_of_polling_locations_to_retrieve)
        # if ((ballots_retrieved + ballots_not_retrieved) >= number_of_polling_locations_to_retrieve and
        #         ballots_with_contests_retrieved > 20) or emergency:
        #     break

    total_retrieved = ballots_retrieved + ballots_not_retrieved
    if ballots_retrieved > 0:
        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Google Civic for the {election_name}. '
                             '(polling_locations_retrieved: {polling_locations_retrieved}, '
                             'ballots_with_election_administration_data: {ballots_with_election_administration_data}, '
                             'ballots retrieved: {ballots_retrieved}, '
                             '(with contests: {ballots_with_contests_retrieved}), '
                             'not retrieved: {ballots_not_retrieved}, '
                             'total: {total}), '
                             'ballots refreshed: {ballots_refreshed}'.format(
                                 polling_locations_retrieved=polling_locations_retrieved,
                                 ballots_with_election_administration_data=ballots_with_election_administration_data,
                                 ballots_refreshed=ballots_refreshed,
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 ballots_with_contests_retrieved=ballots_with_contests_retrieved,
                                 election_name=election_on_stage.election_name,
                                 total=total_retrieved))
    else:
        messages.add_message(request, messages.ERROR,
                             'Ballot data NOT retrieved from Google Civic for the {election_name}. '
                             '(polling_locations_retrieved: {polling_locations_retrieved}, '
                             'ballots_with_election_administration_data: {ballots_with_election_administration_data}, '
                             'ballots retrieved: {ballots_retrieved}, '
                             '(with contests: {ballots_with_contests_retrieved}), '
                             'not retrieved: {ballots_not_retrieved}, '
                             'total: {total})'.format(
                                 polling_locations_retrieved=polling_locations_retrieved,
                                 ballots_with_election_administration_data=ballots_with_election_administration_data,
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 ballots_with_contests_retrieved=ballots_with_contests_retrieved,
                                 election_name=election_on_stage.election_name,
                                 total=total_retrieved))
    return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))


@login_required
def election_one_ballot_retrieve_view(request, election_local_id=0):
    """
    Reach out to Google and retrieve ballot data (for one ballot, typically a map point)
    :param request:
    :param election_local_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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
    ballots_with_contests_retrieved = 0

    ballot_returned_manager = BallotReturnedManager()
    ballot_returned = None
    results = ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id)
    ballot_returned_found = False
    if results['ballot_returned_found']:
        ballot_returned = results['ballot_returned']
        ballot_returned_found = True
        polling_location_we_vote_id = ballot_returned.polling_location_we_vote_id
        voter_id = ballot_returned.voter_id
        text_for_map_search = ballot_returned.text_for_map_search
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
    except Exception as e:
        pass

    # Check to see if we have map point data related to the region(s) covered by this election
    # We request the ballot data for each map point as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(election_local_id):
        state_code = election_on_stage.get_election_state()
        # if not positive_value_exists(state_code):
        #     state_code = "CA"  # TODO DALE Temp for 2016

    one_ballot_json_found = False
    if positive_value_exists(polling_location_we_vote_id):
        try:
            polling_location = PollingLocation.objects.get(
                we_vote_id__iexact=polling_location_we_vote_id)
        except PollingLocation.DoesNotExist:
            messages.add_message(request, messages.INFO,
                                 'Could not retrieve ballot data for this map point for {election_name}, '
                                 'state: {state}. '.format(
                                     election_name=election_on_stage.election_name,
                                     state=state_code))
            return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                        "?polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&google_civic_election_id=" + str(google_civic_election_id)
                                        )
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 'Problem retrieving map point '
                                 '"{polling_location_we_vote_id}" for {election_name}. '
                                 'state: {state}. '.format(
                                     election_name=election_on_stage.election_name,
                                     polling_location_we_vote_id=polling_location_we_vote_id,
                                     state=state_code))
            return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                        "?polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&google_civic_election_id=" + str(google_civic_election_id)
                                        )
        # Get the address for this polling place, and then retrieve the ballot from Google Civic API
        results = polling_location.get_text_for_map_search_results()
        text_for_map_search = results['text_for_map_search']
        one_ballot_results = retrieve_one_ballot_from_google_civic_api(
            text_for_map_search, google_civic_election_id)
        if one_ballot_results['success']:
            one_ballot_json = one_ballot_results['structured_json']
            one_ballot_json_found = True
        if one_ballot_results['contests_retrieved']:
            ballots_with_contests_retrieved += 1
    elif positive_value_exists(voter_id):
        if positive_value_exists(text_for_map_search):
            one_ballot_results = retrieve_one_ballot_from_google_civic_api(
                text_for_map_search, google_civic_election_id)
            if one_ballot_results['success']:
                one_ballot_json = one_ballot_results['structured_json']
                one_ballot_json_found = True
            if one_ballot_results['contests_retrieved']:
                ballots_with_contests_retrieved += 1

    ballots_retrieved = 0
    ballots_not_retrieved = 0
    ballots_with_contests_retrieved = 0
    ballots_refreshed = 0
    success = False
    if one_ballot_json_found:
        if ballot_returned_found:
            store_one_ballot_results = store_one_ballot_from_google_civic_api(
                one_ballot_json, voter_id, polling_location_we_vote_id, ballot_returned)
        else:
            store_one_ballot_results = store_one_ballot_from_google_civic_api(
                one_ballot_json, voter_id, polling_location_we_vote_id)
        if store_one_ballot_results['success']:
            success = True
            if store_one_ballot_results['ballot_returned_found']:
                ballot_returned = store_one_ballot_results['ballot_returned']
                ballot_returned_id = ballot_returned.id
                # Now refresh all the other copies of this ballot
                # DALE NOTE Feb 2020 I don't think this is correct
                # if positive_value_exists(polling_location_we_vote_id) \
                #         and positive_value_exists(google_civic_election_id):
                #     refresh_ballot_results = refresh_voter_ballots_from_polling_location(
                #         ballot_returned, google_civic_election_id)
                #     ballots_refreshed = refresh_ballot_results['ballots_refreshed']
                # elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                #     # Nothing else to be done
                #     pass
            # NOTE: We don't support retrieving ballots for map points AND geocoding simultaneously
            # if store_one_ballot_results['ballot_returned_found']:
            #     ballot_returned = store_one_ballot_results['ballot_returned']
            #     ballot_returned_results = \
            #         ballot_returned_manager.populate_latitude_and_longitude_for_ballot_returned(ballot_returned)
            #     if ballot_returned_results['success']:
            #         rate_limit_count += 1
            #         if rate_limit_count >= 10:  # Avoid problems with the geocoder rate limiting
            #             time.sleep(1)
            #             # After pause, reset the limit count
            #             rate_limit_count = 0

    if success:
        ballots_retrieved += 1
    else:
        ballots_not_retrieved += 1

    if ballots_retrieved > 0:
        total_retrieved = ballots_retrieved + ballots_not_retrieved
        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Google Civic for the {election_name}. '
                             '(ballots retrieved: {ballots_retrieved} '
                             '(with contests: {ballots_with_contests_retrieved}), '
                             'not retrieved: {ballots_not_retrieved}, '
                             'total: {total}), '
                             'ballots refreshed: {ballots_refreshed}'.format(
                                 ballots_refreshed=ballots_refreshed,
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 ballots_with_contests_retrieved=ballots_with_contests_retrieved,
                                 election_name=election_on_stage.election_name,
                                 total=total_retrieved))
    else:
        messages.add_message(request, messages.ERROR,
                             'Ballot data NOT retrieved from Google Civic for the {election_name}.'
                             ' (not retrieved: {ballots_not_retrieved})'.format(
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 election_name=election_on_stage.election_name))
    return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                "?polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                "&google_civic_election_id=" + str(google_civic_election_id)
                                )


@login_required
def election_edit_view(request, election_local_id):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)

    ctcl_uuid = request.GET.get('ctcl_uuid', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    election_local_id = convert_to_int(election_local_id)
    election_on_stage_found = False
    election_on_stage = Election()

    if positive_value_exists(election_local_id):
        try:
            election_on_stage = Election.objects.get(id=election_local_id)
            election_on_stage_found = True
            ctcl_uuid = election_on_stage.ctcl_uuid
            google_civic_election_id = election_on_stage.google_civic_election_id
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except Election.DoesNotExist:
            # This is fine, create new
            pass
    else:
        # If here we are creating a
        pass

    if election_on_stage_found:
        ballotpedia_election_query = BallotpediaElection.objects.filter(
            google_civic_election_id=google_civic_election_id)
        ballotpedia_election_list = list(ballotpedia_election_query)

        use_ctcl_as_data_source_by_state_code = election_on_stage.use_ctcl_as_data_source_by_state_code
        # use_ctcl_as_data_source_override = False
        # if positive_value_exists(state_code) and positive_value_exists(use_ctcl_as_data_source_by_state_code):
        #     if state_code.lower() in use_ctcl_as_data_source_by_state_code.lower():
        #         use_ctcl_as_data_source_override = True

        template_values = {
            'ballotpedia_election_list': ballotpedia_election_list,
            'ctcl_uuid': ctcl_uuid,
            'google_civic_election_id': google_civic_election_id,
            'election': election_on_stage,
            'messages_on_stage': messages_on_stage,
            'state_code': state_code,
            'use_ctcl_as_data_source_by_state_code':    use_ctcl_as_data_source_by_state_code,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, "election/election_edit.html", template_values)


@login_required
def election_delete_process_view(request):
    """
    Delete an election
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    election_id = convert_to_int(request.POST.get('election_id', 0))
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this election without confirmation. '
                             'Please check the checkbox to confirm you want to delete this election.')
        return HttpResponseRedirect(reverse('election:election_edit', args=(election_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    election_manager = ElectionManager()
    results = election_manager.retrieve_election(0, election_id, read_only=False)
    if results['election_found']:
        election = results['election']

        office_list_manager = ContestOfficeListManager()
        office_count = office_list_manager.fetch_office_count(
            election.google_civic_election_id, ignore_office_visiting_list=True)

        if positive_value_exists(office_count):
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'offices still attached to this election.')
            return HttpResponseRedirect(reverse('election:election_edit', args=(election_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&state_code=" + str(state_code))

        election.delete()
        messages.add_message(request, messages.INFO, 'Election deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'Election not found.')

    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_edit_process_view(request):
    """
    Process the new or edit election forms
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    ballotpedia_election_id = request.POST.get('ballotpedia_election_id', False)
    ballotpedia_kind_of_election = request.POST.get('ballotpedia_kind_of_election', False)
    candidate_photos_finished = request.POST.get('candidate_photos_finished', False)
    ctcl_uuid = request.POST.get('ctcl_uuid', False)
    ctcl_uuid2 = request.POST.get('ctcl_uuid2', False)
    ctcl_uuid3 = request.POST.get('ctcl_uuid3', False)
    election_day_text = request.POST.get('election_day_text', False)
    election_local_id = convert_to_int(request.POST.get('election_id', 0))
    election_name = request.POST.get('election_name', False)
    election_preparation_finished = request.POST.get('election_preparation_finished', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', '0')
    ignore_this_election = request.POST.get('ignore_this_election', False)
    include_in_list_for_voters = request.POST.get('include_in_list_for_voters', False)
    internal_notes = request.POST.get('internal_notes', False)
    is_national_election = request.POST.get('is_national_election', False)
    ocd_division_id = request.POST.get('ocd_division_id', False)
    state_code = request.POST.get('state_code', False)
    use_ballotpedia_as_data_source = request.POST.get('use_ballotpedia_as_data_source', False)
    use_ballotpedia_as_data_source = positive_value_exists(use_ballotpedia_as_data_source)
    use_ctcl_as_data_source = request.POST.get('use_ctcl_as_data_source', False)
    use_ctcl_as_data_source = positive_value_exists(use_ctcl_as_data_source)
    use_ctcl_as_data_source_by_state_code = request.POST.get('use_ctcl_as_data_source_by_state_code', None)
    use_google_civic_as_data_source = request.POST.get('use_google_civic_as_data_source', False)
    use_google_civic_as_data_source = positive_value_exists(use_google_civic_as_data_source)
    use_vote_usa_as_data_source = request.POST.get('use_vote_usa_as_data_source', False)
    use_vote_usa_as_data_source = positive_value_exists(use_vote_usa_as_data_source)
    vote_usa_election_id = request.POST.get('vote_usa_election_id', False)

    election_on_stage = Election()

    # Check to see if this election is already being used anywhere
    election_on_stage_found = False
    if positive_value_exists(election_local_id):
        status += "RETRIEVING_ELECTION_BY_ELECTION_LOCAL_ID "
        try:
            election_on_stage = Election.objects.get(id=election_local_id)
            election_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not find election with local id: ' +
                                 str(election_local_id) +
                                 '. ' + status)
            return HttpResponseRedirect(reverse('election:election_list', args=()))

    if not election_on_stage_found and positive_value_exists(google_civic_election_id):
        status += "RETRIEVING_ELECTION_BY_GOOGLE_CIVIC_ELECTION_ID "
        try:
            election_query = Election.objects.filter(google_civic_election_id=google_civic_election_id)
            if len(election_query):
                election_on_stage = election_query[0]
                election_local_id = election_on_stage.id
                election_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    if not election_on_stage_found and positive_value_exists(ballotpedia_election_id):
        status += "RETRIEVING_ELECTION_BY_BALLOTPEDIA_ELECTION_ID "
        try:
            election_query = Election.objects.filter(ballotpedia_election_id=ballotpedia_election_id)
            if len(election_query):
                election_on_stage = election_query[0]
                election_local_id = election_on_stage.id
                election_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    if not election_on_stage_found and positive_value_exists(ctcl_uuid):
        status += "RETRIEVING_ELECTION_BY_CTCL_UUID "
        try:
            election_query = Election.objects.filter(ctcl_uuid=ctcl_uuid)
            if len(election_query):
                election_on_stage = election_query[0]
                election_local_id = election_on_stage.id
                election_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    if election_on_stage_found:
        status += "UPDATING_EXISTING_ELECTION "
        # if convert_to_int(election_on_stage.google_civic_election_id) < 1000000:  # Not supported currently
        # If here, this is an election created by Google Civic and we limit what fields to update
        # If here, this is a We-Vote-created election

        # We do not have a try/except block here because as an admin tool we want to see any errors on-screen
        if election_name is False:
            election_name = election_on_stage.election_name  # Update election_name for the message below
        else:
            election_on_stage.election_name = election_name

        if election_day_text is not False:
            election_on_stage.election_day_text = election_day_text

        if state_code is not False:
            election_on_stage.state_code = state_code

        if not positive_value_exists(election_on_stage.google_civic_election_id) \
                and positive_value_exists(google_civic_election_id):
            election_on_stage.google_civic_election_id = google_civic_election_id

        if ballotpedia_election_id is not False:
            if positive_value_exists(ballotpedia_election_id):
                ballotpedia_election_id = convert_to_int(ballotpedia_election_id)
            else:
                ballotpedia_election_id = None
            election_on_stage.ballotpedia_election_id = ballotpedia_election_id

        if ballotpedia_kind_of_election is not False:
            election_on_stage.ballotpedia_kind_of_election = ballotpedia_kind_of_election

        if ctcl_uuid is not False:
            if not positive_value_exists(ctcl_uuid):
                ctcl_uuid = None
            election_on_stage.ctcl_uuid = ctcl_uuid

        if ctcl_uuid2 is not False:
            if not positive_value_exists(ctcl_uuid2):
                ctcl_uuid2 = None
            election_on_stage.ctcl_uuid2 = ctcl_uuid2

        if ctcl_uuid3 is not False:
            if not positive_value_exists(ctcl_uuid3):
                ctcl_uuid3 = None
            election_on_stage.ctcl_uuid3 = ctcl_uuid3

        if internal_notes is not False:
            election_on_stage.internal_notes = internal_notes

        if ocd_division_id is not False:
            if not positive_value_exists(ocd_division_id):
                ocd_division_id = None
            election_on_stage.ocd_division_id = ocd_division_id

        election_on_stage.candidate_photos_finished = candidate_photos_finished
        election_on_stage.election_preparation_finished = election_preparation_finished
        election_on_stage.include_in_list_for_voters = include_in_list_for_voters
        election_on_stage.ignore_this_election = ignore_this_election
        election_on_stage.is_national_election = is_national_election
        election_on_stage.use_ballotpedia_as_data_source = use_ballotpedia_as_data_source
        election_on_stage.use_ctcl_as_data_source = use_ctcl_as_data_source
        election_on_stage.use_ctcl_as_data_source_by_state_code = use_ctcl_as_data_source_by_state_code
        election_on_stage.use_google_civic_as_data_source = use_google_civic_as_data_source
        election_on_stage.use_vote_usa_as_data_source = use_vote_usa_as_data_source

        if vote_usa_election_id is not False:
            election_on_stage.vote_usa_election_id = vote_usa_election_id

        election_on_stage.save()
        status += "UPDATED_EXISTING_ELECTION "
        messages.add_message(request, messages.INFO, str(election_name) +
                             ' (' + str(election_on_stage.google_civic_election_id) + ') updated.')
    else:
        # Create new
        status += "CREATING_NEW_ELECTION "
        if not positive_value_exists(google_civic_election_id):
            election_manager = ElectionManager()
            google_civic_election_id = election_manager.fetch_next_local_google_civic_election_id_integer()
            google_civic_election_id = convert_to_int(google_civic_election_id)

        if not state_code:
            state_code = ""

        if not positive_value_exists(ctcl_uuid):
            ctcl_uuid = None

        try:
            election_on_stage = Election(
                candidate_photos_finished=candidate_photos_finished,
                election_preparation_finished=election_preparation_finished,
                google_civic_election_id=google_civic_election_id,
                ignore_this_election=ignore_this_election,
                is_national_election=is_national_election,
                include_in_list_for_voters=include_in_list_for_voters,
                state_code=state_code,
                use_ballotpedia_as_data_source=use_ballotpedia_as_data_source,
                use_ctcl_as_data_source=use_ctcl_as_data_source,
                use_ctcl_as_data_source_by_state_code=use_ctcl_as_data_source_by_state_code,
                use_google_civic_as_data_source=use_google_civic_as_data_source,
                use_vote_usa_as_data_source=use_vote_usa_as_data_source,
            )
            if positive_value_exists(ballotpedia_election_id):
                election_on_stage.ballotpedia_election_id = ballotpedia_election_id
            if positive_value_exists(ballotpedia_kind_of_election):
                election_on_stage.ballotpedia_kind_of_election = ballotpedia_kind_of_election
            if positive_value_exists(ctcl_uuid):
                election_on_stage.ctcl_uuid = ctcl_uuid
            if positive_value_exists(election_name):
                election_on_stage.election_name = election_name
            if positive_value_exists(election_day_text):
                election_on_stage.election_day_text = election_day_text
            if positive_value_exists(internal_notes):
                election_on_stage.internal_notes = internal_notes
            if positive_value_exists(ocd_division_id):
                election_on_stage.ocd_division_id = ocd_division_id
            if positive_value_exists(vote_usa_election_id):
                election_on_stage.vote_usa_election_id = vote_usa_election_id
            election_on_stage.save()
            election_local_id = election_on_stage.id
            status += "CREATED_NEW_ELECTION "
            messages.add_message(request, messages.INFO, 'New election ' + str(election_name) + ' saved.')
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save new election ' +
                                 str(google_civic_election_id) +
                                 '. ' + status)

    if election_on_stage and positive_value_exists(google_civic_election_id) \
            and hasattr(election_on_stage, 'state_code_list_raw'):
        ballot_returned_list_manager = BallotReturnedListManager()
        results = ballot_returned_list_manager.retrieve_state_codes_in_election(google_civic_election_id)
        if results['success']:
            state_code_list = results['state_code_list']
            try:
                state_code_list_raw = ','.join(state_code_list)
                election_on_stage.state_code_list_raw = state_code_list_raw
                election_on_stage.save()
            except Exception as e:
                pass

    return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))


@login_required()
def election_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    election_search = request.GET.get('election_search', '')
    refresh_states = positive_value_exists(request.GET.get('refresh_states', False))
    show_all_elections_this_year = request.GET.get('show_all_elections_this_year', False)
    show_election_statistics = request.GET.get('show_election_statistics', False)
    show_ignored_elections = request.GET.get('show_ignored_elections', False)
    if positive_value_exists(show_all_elections_this_year):
        # Give priority to show_all_elections_this_year
        show_all_elections = False
    else:
        show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
        if positive_value_exists(show_all_elections):
            # If here, then we want to make sure show_all_elections_this_year is False
            show_all_elections_this_year = False
    show_this_year = convert_to_int(request.GET.get('show_this_year', 0))

    messages_on_stage = get_messages(request)
    office_manager = ContestOfficeManager()

    election_list_query = Election.objects.all()  # Cannot be readonly because we save stats below
    election_list_query = election_list_query.order_by('election_day_text', 'election_name')
    election_list_query = election_list_query.exclude(google_civic_election_id=2000)
    if positive_value_exists(show_ignored_elections):
        # Do not filter out ignored elections
        pass
    else:
        election_list_query = election_list_query.exclude(ignore_this_election=True)

    # timezone = pytz.timezone("America/Los_Angeles")
    # datetime_now = timezone.localize(datetime.now())
    timezone, datetime_now = generate_localized_datetime_from_obj()
    if positive_value_exists(show_this_year):
        first_day_of_year_to_show = "{year}-01-01".format(year=show_this_year)
        last_day_of_year_to_show = "{year}-12-31".format(year=show_this_year)
        election_list_query = election_list_query.filter(
            election_day_text__gte=first_day_of_year_to_show,
            election_day_text__lte=last_day_of_year_to_show)
    elif positive_value_exists(show_all_elections_this_year):
        first_day_this_year = datetime_now.strftime("%Y-01-01")
        election_list_query = election_list_query.exclude(election_day_text__lt=first_day_this_year)
    elif not positive_value_exists(show_all_elections):
        two_days = timedelta(days=2)
        datetime_two_days_ago = datetime_now - two_days
        earliest_date_to_show = datetime_two_days_ago.strftime("%Y-%m-%d")
        election_list_query = election_list_query.exclude(election_day_text__lt=earliest_date_to_show)

    if positive_value_exists(election_search):
        filters = []
        new_filter = Q(election_name__icontains=election_search)
        filters.append(new_filter)

        new_filter = Q(election_day_text__icontains=election_search)
        filters.append(new_filter)

        new_filter = Q(google_civic_election_id__icontains=election_search)
        filters.append(new_filter)

        new_filter = Q(state_code__icontains=election_search)
        filters.append(new_filter)

        new_filter = Q(vote_usa_election_id__iexact=election_search)
        filters.append(new_filter)

        # Add the first query
        if len(filters):
            final_filters = filters.pop()

            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item

            election_list_query = election_list_query.filter(final_filters)

    election_count = election_list_query.count()
    messages.add_message(request, messages.INFO,
                         '{election_count:,} elections found.'.format(election_count=election_count))

    election_list = election_list_query[:500]
    election_list_modified = []
    ballot_returned_list_manager = BallotReturnedListManager()
    candidate_list_manager = CandidateListManager()
    data_stale_if_older_than = now() - timedelta(days=30)
    state_list = STATE_CODE_MAP
    for election in election_list:
        # Set up state-by-state statistics dict. Reset this for every election
        election.state_statistics_dict = {}
        for one_state_code, one_state_name in state_list.items():
            if positive_value_exists(one_state_code):
                one_state_code_lower = one_state_code.lower()
                election.state_statistics_dict[one_state_code_lower] = {
                    'candidate_count':                      0,
                    'candidates_without_photo_count':       0,
                    'candidates_without_photo_percentage':  0,
                    'candidates_without_links_count':       0,
                    'candidates_without_links_percentage':  0,
                    'measure_count':                        0,
                    'office_count':                         0,
                    'offices_with_candidates_count':        0,
                    'offices_without_candidates_count':     0,
                    'positions_goal_count':                 0,
                    'positions_goal_percentage':            0,
                    'positions_needed_to_reach_goal':       0,
                    'public_positions_count':               0,
                    'state_name':                           one_state_name,
                    'values_exist':                         False,
                }

        if positive_value_exists(election.election_day_text):
            try:
                date_of_election = timezone.localize(datetime.strptime(election.election_day_text, "%Y-%m-%d"))
                if date_of_election > datetime_now:
                    time_until_election = date_of_election - datetime_now
                    election.days_until_election = convert_to_int("%d" % time_until_election.days)
            except Exception as e:
                # Simply do not create "days_until_election"
                pass

        # How many offices?
        office_list_query = ContestOffice.objects.using('readonly').all()
        office_list_query = office_list_query.filter(google_civic_election_id=election.google_civic_election_id)
        election.office_count = office_list_query.count()

        if positive_value_exists(show_election_statistics):
            google_civic_election_id_list = [election.google_civic_election_id]
            results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=google_civic_election_id_list,
                limit_to_this_state_code=state_code)
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']

            office_list = list(office_list_query)
            election.ballot_returned_count = \
                ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                    election.google_civic_election_id, election.state_code)
            election.ballot_location_display_option_on_count = \
                ballot_returned_list_manager.fetch_ballot_location_display_option_on_count_for_election(
                    election.google_civic_election_id, election.state_code)
            # Running this for every entry on the elections page makes the page too slow
            # if election.ballot_returned_count < 500:
            #     batch_set_source = "IMPORT_BALLOTPEDIA_BALLOT_ITEMS"
            #     results = batch_manager.retrieve_unprocessed_batch_set_info_by_election_and_set_source(
            #         election.google_civic_election_id, batch_set_source)
            #     if positive_value_exists(results['batches_not_processed']):
            #         election.batches_not_processed = results['batches_not_processed']
            #         election.batches_not_processed_batch_set_id = results['batch_set_id']

            # How many offices with zero candidates?
            offices_with_candidates_count = 0
            offices_without_candidates_count = 0
            for one_office in office_list:
                results = candidate_list_manager.retrieve_candidate_count_for_office(
                    office_we_vote_id=one_office.we_vote_id)
                candidate_count_for_office = results['candidate_count']
                if positive_value_exists(candidate_count_for_office):
                    offices_with_candidates_count += 1
                else:
                    offices_without_candidates_count += 1
            election.offices_with_candidates_count = offices_with_candidates_count
            election.offices_without_candidates_count = offices_without_candidates_count

            # How many candidates?
            candidate_list_query = CandidateCampaign.objects.using('readonly').all()
            candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            # election.candidate_count = candidate_list_query.count()
            dict_list = list(candidate_list_query.values('state_code'))
            election.candidate_count = len(dict_list)
            state_code_list = []
            for one_dict in dict_list:
                if positive_value_exists(one_dict['state_code']):
                    state_code_lower = one_dict['state_code'].lower()
                    if state_code_lower in election.state_statistics_dict:
                        if state_code_lower not in state_code_list:
                            state_code_list.append(state_code_lower)
                        election.state_statistics_dict[state_code_lower]['candidate_count'] += 1
                        election.state_statistics_dict[state_code_lower]['values_exist'] = True

            # How many without photos?
            candidate_list_query = CandidateCampaign.objects.using('readonly').all()
            candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_list_query = candidate_list_query.filter(
                Q(we_vote_hosted_profile_image_url_tiny__isnull=True) | Q(we_vote_hosted_profile_image_url_tiny='')
            )
            # election.candidates_without_photo_count = candidate_list_query.count()
            dict_list = list(candidate_list_query.values('state_code'))
            election.candidates_without_photo_count = len(dict_list)
            state_code_list = []
            for one_dict in dict_list:
                if positive_value_exists(one_dict['state_code']):
                    state_code_lower = one_dict['state_code'].lower()
                    if state_code_lower in election.state_statistics_dict:
                        if state_code_lower not in state_code_list:
                            state_code_list.append(state_code_lower)
                        election.state_statistics_dict[state_code_lower]['candidates_without_photo_count'] += 1
                        election.state_statistics_dict[state_code_lower]['values_exist'] = True
            for state_code_lower in state_code_list:
                if positive_value_exists(election.state_statistics_dict[state_code_lower]['candidate_count']):
                    election.state_statistics_dict[state_code_lower]['candidates_without_photo_percentage'] = \
                        100 * (election.state_statistics_dict[state_code_lower]['candidates_without_photo_count'] /
                               election.state_statistics_dict[state_code_lower]['candidate_count'])
            if positive_value_exists(election.candidate_count):
                election.candidates_without_photo_percentage = \
                    100 * (election.candidates_without_photo_count / election.candidate_count)

            # How many without links?
            # If you make changes here, please also search for 'hide_candidates_with_links' in candidate/views_admin.py
            candidate_list_query = CandidateCampaign.objects.using('readonly').all()
            candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_list_query = candidate_list_query.filter(
                (Q(ballotpedia_candidate_url__isnull=True) | Q(ballotpedia_candidate_url=""))
                & (Q(candidate_twitter_handle__isnull=True) | Q(candidate_twitter_handle="")
                   | Q(twitter_handle_updates_failing=True))
                & (Q(candidate_url__isnull=True) | Q(candidate_url=""))
                & (Q(facebook_url__isnull=True) | Q(facebook_url="") | Q(facebook_url_is_broken=True))
                & (Q(instagram_handle__isnull=True) | Q(instagram_handle=""))
            )
            # election.candidates_without_links_count = candidate_list_query.count()  # Turning this off, set below
            dict_list = list(candidate_list_query.values('state_code'))
            election.candidates_without_links_count = len(dict_list)
            state_code_list = []
            for one_dict in dict_list:
                if positive_value_exists(one_dict['state_code']):
                    state_code_lower = one_dict['state_code'].lower()
                    if state_code_lower in election.state_statistics_dict:
                        if state_code_lower not in state_code_list:
                            state_code_list.append(state_code_lower)
                        election.state_statistics_dict[state_code_lower]['candidates_without_links_count'] += 1
                        election.state_statistics_dict[state_code_lower]['values_exist'] = True
            for state_code_lower in state_code_list:
                if positive_value_exists(election.state_statistics_dict[state_code_lower]['candidate_count']):
                    election.state_statistics_dict[state_code_lower]['candidates_without_links_percentage'] = \
                        100 * (election.state_statistics_dict[state_code_lower]['candidates_without_links_count'] /
                               election.state_statistics_dict[state_code_lower]['candidate_count'])
            if positive_value_exists(election.candidate_count):
                election.candidates_without_links_percentage = \
                    100 * (election.candidates_without_links_count / election.candidate_count)

            # How many measures?
            measure_list_query = ContestMeasure.objects.using('readonly').all()
            measure_list_query = measure_list_query.filter(
                google_civic_election_id=election.google_civic_election_id)
            election.measure_count = measure_list_query.count()

            # Number of Voter Guides
            voter_guide_query = VoterGuide.objects.using('readonly')\
                .filter(google_civic_election_id=election.google_civic_election_id)
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            election.voter_guides_count = voter_guide_query.count()

            # Number of Public Positions
            position_query = PositionEntered.objects.using('readonly').all()
            # Catch both candidates and measures (which have google_civic_election_id in the Positions table)
            position_query = position_query.filter(
                Q(google_civic_election_id=election.google_civic_election_id) |
                Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
            # As of Aug 2018 we are no longer using PERCENT_RATING
            position_query = position_query.exclude(stance__iexact='PERCENT_RATING')
            # election.public_positions_count = position_query.count()  # Turning this off -- we can use len(list)
            position_dict_list = list(position_query.values('state_code'))
            election.public_positions_count = len(position_dict_list)
            state_code_list = []
            for one_position_dict in position_dict_list:
                if positive_value_exists(one_position_dict['state_code']):
                    state_code_lower = one_position_dict['state_code'].lower()
                    if state_code_lower in election.state_statistics_dict:
                        if state_code_lower not in state_code_list:
                            state_code_list.append(state_code_lower)
                        election.state_statistics_dict[state_code_lower]['public_positions_count'] += 1
                        election.state_statistics_dict[state_code_lower]['values_exist'] = True
            for state_code_lower in state_code_list:
                positions_goal_count = POSITIONS_GOAL_CANDIDATE_MULTIPLIER * \
                                       election.state_statistics_dict[state_code_lower]['candidate_count']
                election.state_statistics_dict[state_code_lower]['positions_goal_count'] = \
                    convert_to_int(positions_goal_count)
                if positive_value_exists(election.state_statistics_dict[state_code_lower]['positions_goal_count']):
                    if positive_value_exists(election.state_statistics_dict[state_code_lower]['public_positions_count']):
                        election.state_statistics_dict[state_code_lower]['positions_goal_percentage'] = \
                            100 * (election.state_statistics_dict[state_code_lower]['positions_goal_count'] /
                                   election.state_statistics_dict[state_code_lower]['public_positions_count'])
                        election.state_statistics_dict[state_code_lower]['positions_needed_to_reach_goal'] = \
                            election.state_statistics_dict[state_code_lower]['positions_goal_count'] - \
                            election.state_statistics_dict[state_code_lower]['public_positions_count']
                    else:
                        election.state_statistics_dict[state_code_lower]['positions_goal_percentage'] = 0
                        election.state_statistics_dict[state_code_lower]['positions_needed_to_reach_goal'] = \
                            election.state_statistics_dict[state_code_lower]['positions_goal_count']

            election.positions_goal_count = \
                convert_to_int(POSITIONS_GOAL_CANDIDATE_MULTIPLIER * election.candidate_count)
            if positive_value_exists(election.positions_goal_count):
                election.positions_goal_percentage = \
                    100 * (election.positions_goal_count / election.candidate_count)
                election.positions_needed_to_reach_goal = \
                    election.positions_goal_count - election.public_positions_count

            # ############################
            # Figure out the last dates we retrieved data
            refresh_date_started = None
            refresh_date_completed = None
            retrieve_date_started = None
            retrieve_date_completed = None
            try:
                batch_process_queryset = BatchProcess.objects.using('readonly').all()
                batch_process_queryset = \
                    batch_process_queryset.filter(google_civic_election_id=election.google_civic_election_id)
                batch_process_queryset = batch_process_queryset.filter(date_started__isnull=False)
                batch_process_queryset = batch_process_queryset.exclude(batch_process_paused=True)
                ballot_item_processes = [
                    'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS',
                    'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=ballot_item_processes)
                batch_process_queryset = batch_process_queryset.order_by("-id")

                batch_process_queryset = batch_process_queryset[:3]
                batch_process_list = list(batch_process_queryset)

                if len(batch_process_list):
                    for one_batch_process in batch_process_list:
                        if one_batch_process.kind_of_process == 'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not refresh_date_completed and one_batch_process.date_completed:
                                refresh_date_completed = one_batch_process.date_completed
                            if not refresh_date_started and one_batch_process.date_started:
                                refresh_date_started = one_batch_process.date_started
                        elif one_batch_process.kind_of_process == 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not retrieve_date_completed and one_batch_process.date_completed:
                                retrieve_date_completed = one_batch_process.date_completed
                            if not retrieve_date_started and one_batch_process.date_started:
                                retrieve_date_started = one_batch_process.date_started
                        # if refresh_date_completed and retrieve_date_completed:
                        #     break  # Break out of this batch_process loop only
            except BatchProcess.DoesNotExist:
                # No offices found. Not a problem.
                batch_process_list = []
            except Exception as e:
                pass

            # Upcoming refresh date scheduled?
            refresh_date_added_to_queue = None
            retrieve_date_added_to_queue = None
            try:
                batch_process_queryset = BatchProcess.objects.using('readonly').all()
                batch_process_queryset = \
                    batch_process_queryset.filter(google_civic_election_id=election.google_civic_election_id)
                batch_process_queryset = batch_process_queryset.filter(date_completed__isnull=True)
                batch_process_queryset = batch_process_queryset.exclude(batch_process_paused=True)
                ballot_item_processes = [
                    'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS',
                    'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=ballot_item_processes)
                batch_process_queryset = batch_process_queryset.order_by("-id")

                batch_process_queryset = batch_process_queryset[:3]
                batch_process_list = list(batch_process_queryset)

                if len(batch_process_list):
                    for one_batch_process in batch_process_list:
                        if one_batch_process.kind_of_process == 'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not refresh_date_added_to_queue and one_batch_process.date_added_to_queue:
                                refresh_date_added_to_queue = one_batch_process.date_added_to_queue
                        elif one_batch_process.kind_of_process == 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not retrieve_date_added_to_queue and one_batch_process.date_added_to_queue:
                                retrieve_date_added_to_queue = one_batch_process.date_added_to_queue
            except BatchProcess.DoesNotExist:
                # No offices found. Not a problem.
                batch_process_list = []
            except Exception as e:
                pass

            # election_for_one_state = copy.deepcopy(national_election)
            election.refresh_date_completed = refresh_date_completed
            election.refresh_date_started = refresh_date_started
            election.refresh_date_added_to_queue = refresh_date_added_to_queue
            election.retrieve_date_completed = retrieve_date_completed
            election.retrieve_date_started = retrieve_date_started
            election.retrieve_date_added_to_queue = retrieve_date_added_to_queue

            if refresh_date_completed:
                most_recent_time = refresh_date_completed
            elif refresh_date_started:
                most_recent_time = refresh_date_started
            elif retrieve_date_completed:
                most_recent_time = retrieve_date_completed
            elif retrieve_date_started:
                most_recent_time = retrieve_date_started
            else:
                most_recent_time = None

            if most_recent_time:
                if refresh_date_completed and refresh_date_completed > most_recent_time:
                    most_recent_time = refresh_date_completed
                if refresh_date_started and refresh_date_started > most_recent_time:
                    most_recent_time = refresh_date_started
                if retrieve_date_completed and retrieve_date_completed > most_recent_time:
                    most_recent_time = retrieve_date_completed
                if retrieve_date_started and retrieve_date_started > most_recent_time:
                    most_recent_time = retrieve_date_started

                if most_recent_time > data_stale_if_older_than:
                    election.data_getting_stale = False
                else:
                    election.data_getting_stale = True
            else:
                election.data_getting_stale = True

        if positive_value_exists(refresh_states):
            if election and positive_value_exists(election.google_civic_election_id) \
                    and hasattr(election, 'state_code_list_raw'):
                results = \
                    ballot_returned_list_manager.retrieve_state_codes_in_election(election.google_civic_election_id)
                if results['success']:
                    state_code_list = results['state_code_list']
                    try:
                        state_code_list_raw = ','.join(state_code_list)
                        election.state_code_list_raw = state_code_list_raw
                        election.save()
                    except Exception as e:
                        pass
        election_list_modified.append(election)

    try:
        from import_export_ctcl.controllers import CTCL_API_KEY, CTCL_ELECTION_QUERY_URL
        ctcl_elections_api_url = \
            "{url}?key={accessKey}" \
            "".format(
                url=CTCL_ELECTION_QUERY_URL,
                accessKey=CTCL_API_KEY,
            )
    except Exception as e:
        ctcl_elections_api_url = "FAILED: " + str(e) + " "

    try:
        from import_export_vote_usa.controllers import VOTE_USA_ELECTION_QUERY_URL
        VOTE_USA_API_KEY = get_environment_variable("VOTE_USA_API_KEY", no_exception=True)
        vote_usa_elections_api_url = \
            "{url}?accessKey={accessKey}" \
            "".format(
                url=VOTE_USA_ELECTION_QUERY_URL,
                accessKey=VOTE_USA_API_KEY,
            )
    except Exception as e:
        vote_usa_elections_api_url = "FAILED: " + str(e) + " "

    template_values = {
        'ctcl_elections_api_url':       ctcl_elections_api_url,
        'election_list':                election_list_modified,
        'election_search':              election_search,
        'google_civic_election_id':     google_civic_election_id,
        'messages_on_stage':            messages_on_stage,
        'show_all_elections':           show_all_elections,
        'show_all_elections_this_year': show_all_elections_this_year,
        'show_election_statistics':     show_election_statistics,
        'show_ignored_elections':       show_ignored_elections,
        'show_this_year':               show_this_year,
        'state_code':                   state_code,
        'years_available':              ELECTION_YEARS_AVAILABLE,
        'vote_usa_elections_api_url':   vote_usa_elections_api_url,
    }
    return render(request, 'election/election_list.html', template_values)


@login_required()
def nationwide_election_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    election_search = request.GET.get('election_search', '')
    show_all_elections_this_year = request.GET.get('show_all_elections_this_year', False)
    show_election_statistics = request.GET.get('show_election_statistics', False)
    show_ignored_elections = request.GET.get('show_ignored_elections', False)
    show_related_elections = request.GET.get('show_related_elections', False)
    if positive_value_exists(show_all_elections_this_year):
        # Give priority to show_all_elections_this_year
        show_all_elections = False
    else:
        show_all_elections = positive_value_exists(request.GET.get('show_all_elections', False))
        if positive_value_exists(show_all_elections):
            # If here, then we want to make sure show_all_elections_this_year is False
            show_all_elections_this_year = False

    messages_on_stage = get_messages(request)
    # timezone = pytz.timezone("America/Los_Angeles")
    # datetime_now = timezone.localize(datetime.now())
    timezone, datetime_now = generate_localized_datetime_from_obj()
    election_manager = ElectionManager()

    is_national_election = False
    national_election = None
    if positive_value_exists(google_civic_election_id):
        results = election_manager.retrieve_election(google_civic_election_id, read_only=False)
        if results['election_found']:
            national_election = results['election']
            is_national_election = national_election.is_national_election
            if not positive_value_exists(is_national_election):
                national_election = None

    data_stale_if_older_than = now() - timedelta(days=30)
    if is_national_election:
        from election.models import fetch_next_election_for_state, fetch_prior_election_for_state
        state_list = STATE_CODE_MAP
        election_list = []
        cached_national_election_list = False
        for one_state_code, one_state_name in state_list.items():
            # ############################
            # Figure out the last dates we retrieved data for this state
            refresh_date_started = None
            refresh_date_completed = None
            retrieve_date_started = None
            retrieve_date_completed = None
            try:
                batch_process_queryset = BatchProcess.objects.using('readonly').all()
                batch_process_queryset = \
                    batch_process_queryset.filter(google_civic_election_id=google_civic_election_id)
                batch_process_queryset = batch_process_queryset.filter(state_code__iexact=one_state_code)
                batch_process_queryset = batch_process_queryset.filter(date_started__isnull=False)
                batch_process_queryset = batch_process_queryset.exclude(batch_process_paused=True)
                ballot_item_processes = [
                    'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS',
                    'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=ballot_item_processes)
                batch_process_queryset = batch_process_queryset.order_by("-id")

                batch_process_queryset = batch_process_queryset[:3]
                batch_process_list = list(batch_process_queryset)

                if len(batch_process_list):
                    for one_batch_process in batch_process_list:
                        if one_batch_process.kind_of_process == 'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not refresh_date_completed and one_batch_process.date_completed:
                                refresh_date_completed = one_batch_process.date_completed
                            if not refresh_date_started and one_batch_process.date_started:
                                refresh_date_started = one_batch_process.date_started
                        elif one_batch_process.kind_of_process == 'RETRIEVE_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not retrieve_date_completed and one_batch_process.date_completed:
                                retrieve_date_completed = one_batch_process.date_completed
                            if not retrieve_date_started and one_batch_process.date_started:
                                retrieve_date_started = one_batch_process.date_started
                        # if refresh_date_completed and retrieve_date_completed:
                        #     break  # Break out of this batch_process loop only
            except BatchProcess.DoesNotExist:
                # No offices found. Not a problem.
                batch_process_list = []
            except Exception as e:
                pass

            # Upcoming refresh date scheduled?
            refresh_date_added_to_queue = None
            try:
                batch_process_queryset = BatchProcess.objects.using('readonly').all()
                batch_process_queryset = \
                    batch_process_queryset.filter(google_civic_election_id=google_civic_election_id)
                batch_process_queryset = batch_process_queryset.filter(state_code__iexact=one_state_code)
                batch_process_queryset = batch_process_queryset.filter(date_completed__isnull=True)
                batch_process_queryset = batch_process_queryset.exclude(batch_process_paused=True)
                ballot_item_processes = [
                    'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS']
                batch_process_queryset = batch_process_queryset.filter(kind_of_process__in=ballot_item_processes)
                batch_process_queryset = batch_process_queryset.order_by("-id")

                batch_process_queryset = batch_process_queryset[:3]
                batch_process_list = list(batch_process_queryset)

                if len(batch_process_list):
                    for one_batch_process in batch_process_list:
                        if one_batch_process.kind_of_process == 'REFRESH_BALLOT_ITEMS_FROM_POLLING_LOCATIONS':
                            if not refresh_date_added_to_queue and one_batch_process.date_added_to_queue:
                                refresh_date_added_to_queue = one_batch_process.date_added_to_queue
            except BatchProcess.DoesNotExist:
                # No offices found. Not a problem.
                batch_process_list = []
            except Exception as e:
                pass

            prior_election_in_state = None
            next_election_in_state = None
            if positive_value_exists(show_related_elections):
                # Prior Election (so we know if the primary has ended, and if it makes sense to start a process)
                results = election_manager.retrieve_prior_election_for_state(
                    state_code=one_state_code, cached_national_election_list=cached_national_election_list)
                if results['election_found']:
                    prior_election_in_state = results['election']
                    if not cached_national_election_list and positive_value_exists(results['national_election_list']):
                        cached_national_election_list = results['national_election_list']
                else:
                    prior_election_in_state = None
                # Next Election (is a primary coming up?)
                next_election_in_state = fetch_next_election_for_state(one_state_code)

            # Transfer to election object
            if one_state_code == "NA":
                pass
            else:
                election_for_one_state = copy.deepcopy(national_election)
                election_for_one_state.state_code = one_state_code
                election_for_one_state.is_national_election = False
                election_for_one_state.internal_notes = None  # Do we want to try to add this for states?
                election_for_one_state.refresh_date_completed = refresh_date_completed
                election_for_one_state.refresh_date_started = refresh_date_started
                election_for_one_state.refresh_date_added_to_queue = refresh_date_added_to_queue
                election_for_one_state.retrieve_date_completed = retrieve_date_completed
                election_for_one_state.retrieve_date_started = retrieve_date_started

                election_for_one_state.prior_election_in_state = prior_election_in_state
                if prior_election_in_state and prior_election_in_state.election_day_text:
                    election_for_one_state.prior_election_in_state_date = \
                        convert_we_vote_date_string_to_date(prior_election_in_state.election_day_text)

                election_for_one_state.next_election_in_state = next_election_in_state
                if next_election_in_state and next_election_in_state.election_day_text:
                    election_for_one_state.next_election_in_state_date = \
                        convert_we_vote_date_string_to_date(next_election_in_state.election_day_text)

                if refresh_date_completed:
                    most_recent_time = refresh_date_completed
                elif refresh_date_started:
                    most_recent_time = refresh_date_started
                elif retrieve_date_completed:
                    most_recent_time = retrieve_date_completed
                elif retrieve_date_started:
                    most_recent_time = retrieve_date_started
                else:
                    most_recent_time = None

                if most_recent_time:
                    if refresh_date_completed and refresh_date_completed > most_recent_time:
                        most_recent_time = refresh_date_completed
                    if refresh_date_started and refresh_date_started > most_recent_time:
                        most_recent_time = refresh_date_started
                    if retrieve_date_completed and retrieve_date_completed > most_recent_time:
                        most_recent_time = retrieve_date_completed
                    if retrieve_date_started and retrieve_date_started > most_recent_time:
                        most_recent_time = retrieve_date_started

                    if most_recent_time > data_stale_if_older_than:
                        election_for_one_state.data_getting_stale = False
                    else:
                        election_for_one_state.data_getting_stale = True
                else:
                    election_for_one_state.data_getting_stale = True

                election_list.append(election_for_one_state)
    else:
        election_list_query = Election.objects.all()
        election_list_query = election_list_query.order_by('election_day_text').reverse()
        election_list_query = election_list_query.exclude(google_civic_election_id=2000)
        if positive_value_exists(show_ignored_elections):
            # Do not filter out ignored elections
            pass
        else:
            election_list_query = election_list_query.exclude(ignore_this_election=True)

        if positive_value_exists(show_all_elections_this_year):
            first_day_this_year = datetime_now.strftime("%Y-01-01")
            election_list_query = election_list_query.exclude(election_day_text__lt=first_day_this_year)
        elif not positive_value_exists(show_all_elections):
            two_days = timedelta(days=2)
            datetime_two_days_ago = datetime_now - two_days
            earliest_date_to_show = datetime_two_days_ago.strftime("%Y-%m-%d")
            election_list_query = election_list_query.exclude(election_day_text__lt=earliest_date_to_show)

        if positive_value_exists(election_search):
            filters = []
            new_filter = Q(election_name__icontains=election_search)
            filters.append(new_filter)

            new_filter = Q(election_day_text__icontains=election_search)
            filters.append(new_filter)

            new_filter = Q(google_civic_election_id__icontains=election_search)
            filters.append(new_filter)

            new_filter = Q(state_code__icontains=election_search)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                election_list_query = election_list_query.filter(final_filters)

        election_list = election_list_query[:200]

    election_list_modified = []
    ballot_returned_list_manager = BallotReturnedListManager()
    candidate_list_manager = CandidateListManager()
    for election in election_list:
        if positive_value_exists(election.election_day_text):
            try:
                date_of_election = timezone.localize(datetime.strptime(election.election_day_text, "%Y-%m-%d"))
                if date_of_election > datetime_now:
                    time_until_election = date_of_election - datetime_now
                    election.days_until_election = convert_to_int("%d" % time_until_election.days)
            except Exception as e:
                # Simply do not create "days_until_election"
                pass

        # How many offices?
        office_list_query = ContestOffice.objects.using('readonly').all()
        office_list_query = office_list_query.filter(google_civic_election_id=election.google_civic_election_id)
        if is_national_election and positive_value_exists(election.state_code):
            office_list_query = office_list_query.filter(state_code__iexact=election.state_code)
        election.office_count = office_list_query.count()

        if positive_value_exists(show_election_statistics):
            google_civic_election_id_list = [election.google_civic_election_id]
            results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=google_civic_election_id_list,
                limit_to_this_state_code=election.state_code)
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']

            office_list = list(office_list_query)
            election.ballot_returned_count = \
                ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                    election.google_civic_election_id, election.state_code)
            election.ballot_location_display_option_on_count = \
                ballot_returned_list_manager.fetch_ballot_location_display_option_on_count_for_election(
                    election.google_civic_election_id, election.state_code)
            # Running this for every entry on the elections page makes the page too slow
            # if election.ballot_returned_count < 500:
            #     batch_set_source = "IMPORT_BALLOTPEDIA_BALLOT_ITEMS"
            #     results = batch_manager.retrieve_unprocessed_batch_set_info_by_election_and_set_source(
            #         election.google_civic_election_id, batch_set_source)
            #     if positive_value_exists(results['batches_not_processed']):
            #         election.batches_not_processed = results['batches_not_processed']
            #         election.batches_not_processed_batch_set_id = results['batch_set_id']

            # How many offices with zero candidates?
            offices_with_candidates_count = 0
            offices_without_candidates_count = 0
            for one_office in office_list:
                results = candidate_list_manager.retrieve_candidate_count_for_office(
                    office_we_vote_id=one_office.we_vote_id)
                candidate_count_for_office = results['candidate_count']
                if positive_value_exists(candidate_count_for_office):
                    offices_with_candidates_count += 1
                else:
                    offices_without_candidates_count += 1
            election.offices_with_candidates_count = offices_with_candidates_count
            election.offices_without_candidates_count = offices_without_candidates_count

            # How many candidates?
            candidate_list_query = CandidateCampaign.objects.using('readonly').all()
            candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            if is_national_election and positive_value_exists(election.state_code):
                candidate_list_query = candidate_list_query.filter(state_code__iexact=election.state_code)
            election.candidate_count = candidate_list_query.count()

            # How many without photos?
            candidate_list_query = CandidateCampaign.objects.using('readonly').all()
            candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            if is_national_election and positive_value_exists(election.state_code):
                candidate_list_query = candidate_list_query.filter(state_code__iexact=election.state_code)
            candidate_list_query = candidate_list_query.filter(
                Q(we_vote_hosted_profile_image_url_tiny__isnull=True) | Q(we_vote_hosted_profile_image_url_tiny='')
            )
            election.candidates_without_photo_count = candidate_list_query.count()
            if positive_value_exists(election.candidate_count):
                election.candidates_without_photo_percentage = \
                    100 * (election.candidates_without_photo_count / election.candidate_count)

            # How many measures?
            measure_list_query = ContestMeasure.objects.using('readonly').all()
            measure_list_query = measure_list_query.filter(google_civic_election_id=election.google_civic_election_id)
            if is_national_election and positive_value_exists(election.state_code):
                measure_list_query = measure_list_query.filter(state_code__iexact=election.state_code)
            election.measure_count = measure_list_query.count()

            # Number of Voter Guides
            voter_guide_query = VoterGuide.objects.filter(google_civic_election_id=election.google_civic_election_id)
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            if is_national_election and positive_value_exists(election.state_code):
                voter_guide_query = voter_guide_query.filter(state_code__iexact=election.state_code)
            election.voter_guides_count = voter_guide_query.count()

            # Number of Public Positions
            position_query = PositionEntered.objects.using('readonly').all()
            # Catch both candidates and measures (which have google_civic_election_id in the Positions table)
            position_query = position_query.filter(
                Q(google_civic_election_id=election.google_civic_election_id) |
                Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
            # As of Aug 2018 we are no longer using PERCENT_RATING
            position_query = position_query.exclude(stance__iexact='PERCENT_RATING')
            if is_national_election and positive_value_exists(election.state_code):
                position_query = position_query.filter(state_code__iexact=election.state_code)
            election.public_positions_count = position_query.count()

        election_list_modified.append(election)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'election_list':                election_list_modified,
        'election_search':              election_search,
        'is_national_election':         is_national_election,
        'national_election':            national_election,
        'google_civic_election_id':     google_civic_election_id,
        'show_all_elections':           show_all_elections,
        'show_all_elections_this_year': show_all_elections_this_year,
        'show_election_statistics':     show_election_statistics,
        'show_ignored_elections':       show_ignored_elections,
        'show_related_elections':       show_related_elections,
        'state_code':                   state_code,
    }
    return render(request, 'election/election_list.html', template_values)


@login_required()
def election_remote_retrieve_view(request):
    """
    Reach out to one of our data sources and retrieve the latest list of available elections
    :param request:
    :return:
    """
    success = True
    status = ""
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    use_ctcl = positive_value_exists(request.GET.get('use_ctcl', False))
    use_google_civic = positive_value_exists(request.GET.get('use_google_civic', False))
    use_vote_usa = positive_value_exists(request.GET.get('use_vote_usa', False))

    if use_ctcl:
        results = election_remote_retrieve(use_ctcl=True)
        status += results['status']
        success = results['success']
    elif use_google_civic:
        results = election_remote_retrieve(use_google_civic=True)
        status += results['status']
        success = results['success']
    elif use_vote_usa:
        results = election_remote_retrieve(use_vote_usa=True)
        status += results['status']
        success = results['success']
    else:
        status += "One parameter is required: use_ctcl, use_google_civic, or use_vote_usa. "

    if success:
        messages.add_message(request, messages.INFO, status)
    else:
        messages.add_message(request, messages.ERROR, status)
    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_summary_view(request, election_local_id=0, google_civic_election_id=''):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = \
        {'partner_organization', 'political_data_manager', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    show_all_ballotpedia_elections = request.GET.get('show_all_ballotpedia_elections', False)
    show_offices_and_candidates = request.GET.get('show_offices_and_candidates', False)
    if not positive_value_exists(google_civic_election_id):
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')
    election_local_id = convert_to_int(election_local_id)
    ballot_returned_search = request.GET.get('ballot_returned_search', '')
    ballot_returned_search = ballot_returned_search.strip() if positive_value_exists(ballot_returned_search) else ''
    use_ctcl_as_data_source_override = False
    voter_ballot_saved_search = request.GET.get('voter_ballot_saved_search', '')
    merge_ballot_returned_duplicates = \
        positive_value_exists(request.GET.get('merge_ballot_returned_duplicates', False))

    election_found = False
    election = Election()
    is_national_election = False

    try:
        if positive_value_exists(election_local_id):
            election = Election.objects.get(id=election_local_id)
        else:
            election = Election.objects.get(google_civic_election_id=google_civic_election_id)
        election_found = True
        election_local_id = election.id
        is_national_election = election.is_national_election
        google_civic_election_id = election.google_civic_election_id
        if not positive_value_exists(state_code):
            state_code = election.state_code
        use_ctcl_as_data_source_by_state_code = election.use_ctcl_as_data_source_by_state_code
        if positive_value_exists(state_code) and positive_value_exists(use_ctcl_as_data_source_by_state_code):
            if state_code.lower() in use_ctcl_as_data_source_by_state_code.lower():
                use_ctcl_as_data_source_override = True
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Election.DoesNotExist:
        # This is fine, proceed anyways
        pass

    ballotpedia_election_list = []
    more_than_three_ballotpedia_elections = False
    all_ballotpedia_elections_shown = True
    if election_found:
        ballotpedia_election_query = BallotpediaElection.objects.filter(
            google_civic_election_id=google_civic_election_id)
        if is_national_election and positive_value_exists(state_code):
            ballotpedia_election_query = ballotpedia_election_query.filter(state_code__iexact=state_code)
        ballotpedia_election_list = list(ballotpedia_election_query)
        if len(ballotpedia_election_list) > 3:
            more_than_three_ballotpedia_elections = True
            if not show_all_ballotpedia_elections:
                all_ballotpedia_elections_shown = False
                ballotpedia_election_list = ballotpedia_election_list[:3]

    sorted_state_list = []
    status_print_list = ""
    ballot_returned_count = 0
    ballot_returned_count_entire_election = 0
    ballot_returned_oldest_date = ''
    ballot_returned_voter_oldest_date = ''
    entries_missing_latitude_longitude = 0
    ballot_returned_list_manager = BallotReturnedListManager()
    candidate_list_manager = CandidateListManager()
    office_manager = ContestOfficeManager()
    # See if the number of map points for this state exceed the "large" threshold
    polling_location_manager = PollingLocationManager()
    map_points_retrieved_each_batch_chunk = \
        polling_location_manager.calculate_number_of_map_points_to_retrieve_with_each_batch_chunk(state_code)

    if election_found:
        batch_manager = BatchManager()
        state_list = STATE_CODE_MAP
        state_list_modified = {}
        for one_state_code, one_state_name in state_list.items():
            ballot_returned_count = ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                election.google_civic_election_id, one_state_code)

            state_name_modified = one_state_name
            if positive_value_exists(ballot_returned_count):
                state_name_modified += " - " + str(ballot_returned_count)
            state_list_modified[one_state_code] = state_name_modified

        sorted_state_list = sorted(state_list_modified.items())

        if positive_value_exists(merge_ballot_returned_duplicates):
            results = ballot_returned_list_manager.merge_ballot_returned_duplicates(
                google_civic_election_id=election.google_civic_election_id, state_code=state_code)

            message_to_print = "MERGE_BALLOT_RETURNED_DUPLICATES, status: " + str(results['status']) \
                               + ", total_count:" + str(results['total_updated']) + " "
            messages.add_message(request, messages.INFO, message_to_print)

        limit = 20  # Since this is a summary page, we don't need to show very many ballot_returned entries
        ballot_returned_list_results = ballot_returned_list_manager.retrieve_ballot_returned_list_for_election(
            election.google_civic_election_id, state_code, limit, ballot_returned_search)
        ballot_returned_count_entire_election = \
            ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                election.google_civic_election_id, state_code=state_code)
        entries_missing_latitude_longitude = \
            ballot_returned_list_manager.fetch_ballot_returned_entries_needed_lat_long_for_election(
                election.google_civic_election_id, state_code)

        if ballot_returned_list_results['success']:
            ballot_returned_list = ballot_returned_list_results['ballot_returned_list']
            if not positive_value_exists(state_code):
                ballot_returned_list = ballot_returned_list[:limit]
        else:
            ballot_returned_list = []

        ballot_returned_oldest_date = ballot_returned_list_manager.fetch_oldest_date_last_updated(
            election.google_civic_election_id, state_code)

        ballot_returned_voter_oldest_date = ballot_returned_list_manager.fetch_oldest_date_last_updated(
            election.google_civic_election_id, state_code, for_voter=True)

        if positive_value_exists(ballot_returned_count_entire_election):
            status_print_list += "ballot_returned_count: " + str(ballot_returned_count_entire_election) + ""
            messages.add_message(request, messages.INFO, status_print_list)

        google_civic_election_id_list = [google_civic_election_id]
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=state_code)
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

        ballot_item_list_manager = BallotItemListManager()
        voter_ballot_saved_manager = VoterBallotSavedManager()
        ballot_returned_list_modified = []
        if show_offices_and_candidates:
            ballot_returned_list_modified = []
            # office_list_manager = ContestOfficeListManager()
            ballot_returned_list_shorter = ballot_returned_list[:50]
            for one_ballot_returned in ballot_returned_list_shorter:
                candidates_count = 0
                offices_count = 0
                if positive_value_exists(one_ballot_returned.polling_location_we_vote_id):
                    office_list = []
                    google_civic_election_id_list = [google_civic_election_id]
                    results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                        polling_location_we_vote_id=one_ballot_returned.polling_location_we_vote_id,
                        google_civic_election_id_list=google_civic_election_id_list)
                    ballot_items_count = 0
                    if results['ballot_item_list_found']:
                        ballot_item_list = results['ballot_item_list']
                        ballot_items_count = len(ballot_item_list)
                        for one_ballot_item in ballot_item_list:
                            if positive_value_exists(one_ballot_item.contest_office_we_vote_id):
                                offices_count += 1
                                office_list.append(one_ballot_item.contest_office_we_vote_id)
                                candidate_results = candidate_list_manager.retrieve_candidate_count_for_office(
                                    0, one_ballot_item.contest_office_we_vote_id)
                                candidates_count += candidate_results['candidate_count']
                    one_ballot_returned.office_and_candidate_text = \
                        "offices: {offices_count}, candidates: {candidates_count}".format(
                            offices_count=offices_count, candidates_count=candidates_count)
                    one_ballot_returned.ballot_items_count = ballot_items_count
                elif positive_value_exists(one_ballot_returned.voter_id):
                    voter_ballot_saved_results = \
                        voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_ballot_returned_we_vote_id(
                            one_ballot_returned.voter_id, one_ballot_returned.we_vote_id)
                    if voter_ballot_saved_results['voter_ballot_saved_found']:
                        voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
                        one_ballot_returned.polling_location_we_vote_id_source = \
                            voter_ballot_saved.polling_location_we_vote_id_source
                ballot_returned_list_modified.append(one_ballot_returned)
        else:
            for one_ballot_returned in ballot_returned_list:
                one_ballot_returned.ballot_items_count = \
                    ballot_item_list_manager.fetch_ballot_item_list_count_for_ballot_returned(
                        one_ballot_returned.voter_id,
                        one_ballot_returned.polling_location_we_vote_id,
                        one_ballot_returned.google_civic_election_id)
                if positive_value_exists(one_ballot_returned.voter_id):
                    voter_ballot_saved_results = \
                        voter_ballot_saved_manager.retrieve_voter_ballot_saved_by_ballot_returned_we_vote_id(
                            one_ballot_returned.voter_id, one_ballot_returned.we_vote_id)
                    if voter_ballot_saved_results['voter_ballot_saved_found']:
                        voter_ballot_saved = voter_ballot_saved_results['voter_ballot_saved']
                        one_ballot_returned.polling_location_we_vote_id_source = \
                            voter_ballot_saved.polling_location_we_vote_id_source
                ballot_returned_list_modified.append(one_ballot_returned)

        voter_ballot_saved_list = []
        voter_ballot_saved_results = \
            voter_ballot_saved_manager.retrieve_voter_ballot_saved_list_for_election(
                google_civic_election_id, state_code=state_code, find_all_entries_for_election=True)
        if voter_ballot_saved_results['voter_ballot_saved_list_found']:
            voter_ballot_saved_list = voter_ballot_saved_results['voter_ballot_saved_list']

        # ############################
        # Add election statistics
        # timezone = pytz.timezone("America/Los_Angeles")
        # datetime_now = timezone.localize(datetime.now())
        timezone, datetime_now = generate_localized_datetime_from_obj()
        if positive_value_exists(election.election_day_text):
            try:
                date_of_election = timezone.localize(datetime.strptime(election.election_day_text, "%Y-%m-%d"))
                if date_of_election > datetime_now:
                    time_until_election = date_of_election - datetime_now
                    election.days_until_election = convert_to_int("%d" % time_until_election.days)
            except Exception as e:
                # Simply do not create "days_until_election"
                pass

        election.ballot_returned_count = \
            ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                election.google_civic_election_id, state_code)
        election.ballot_location_display_option_on_count = \
            ballot_returned_list_manager.fetch_ballot_location_display_option_on_count_for_election(
                election.google_civic_election_id, state_code)
        if election.ballot_returned_count < 500:
            batch_set_source = "IMPORT_BALLOTPEDIA_BALLOT_ITEMS"
            results = batch_manager.retrieve_unprocessed_batch_set_info_by_election_and_set_source(
                election.google_civic_election_id, batch_set_source, state_code)
            if positive_value_exists(results['batches_not_processed']):
                election.batches_not_processed = results['batches_not_processed']
                election.batches_not_processed_batch_set_id = results['batch_set_id']

        # How many offices?
        office_list_query = ContestOffice.objects.all()
        office_list_query = office_list_query.filter(google_civic_election_id=google_civic_election_id)
        if is_national_election and positive_value_exists(state_code):
            office_list_query = office_list_query.filter(state_code__iexact=state_code)
        office_list = list(office_list_query)
        election.office_count = len(office_list)

        # How many offices with zero candidates?
        offices_with_candidates_count = 0
        offices_without_candidates_count = 0
        for one_office in office_list:
            results = candidate_list_manager.retrieve_candidate_count_for_office(
                office_we_vote_id=one_office.we_vote_id)
            candidate_count_for_office = results['candidate_count']
            if positive_value_exists(candidate_count_for_office):
                offices_with_candidates_count += 1
            else:
                offices_without_candidates_count += 1
        election.offices_with_candidates_count = offices_with_candidates_count
        election.offices_without_candidates_count = offices_without_candidates_count

        # How many candidates?
        candidate_list_query = CandidateCampaign.objects.all()
        candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
        if is_national_election and positive_value_exists(state_code):
            candidate_list_query = candidate_list_query.filter(state_code__iexact=state_code)
        election.candidate_count = candidate_list_query.count()

        # How many without photos?
        candidate_list_query = CandidateCampaign.objects.all()
        candidate_list_query = candidate_list_query.filter(we_vote_id__in=candidate_we_vote_id_list)
        if is_national_election and positive_value_exists(state_code):
            candidate_list_query = candidate_list_query.filter(state_code__iexact=state_code)
        candidate_list_query = candidate_list_query.filter(
            Q(we_vote_hosted_profile_image_url_tiny__isnull=True) | Q(we_vote_hosted_profile_image_url_tiny='')
        )
        election.candidates_without_photo_count = candidate_list_query.count()
        if positive_value_exists(election.candidate_count):
            election.candidates_without_photo_percentage = \
                100 * (election.candidates_without_photo_count / election.candidate_count)

        # How many measures?
        measure_list_query = ContestMeasure.objects.all()
        measure_list_query = measure_list_query.filter(google_civic_election_id=google_civic_election_id)
        if is_national_election and positive_value_exists(state_code):
            measure_list_query = measure_list_query.filter(state_code__iexact=state_code)
        election.measure_count = measure_list_query.count()

        # Number of Voter Guides
        voter_guide_query = VoterGuide.objects.filter(
            google_civic_election_id=election.google_civic_election_id)
        voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
        if is_national_election and positive_value_exists(state_code):
            voter_guide_query = voter_guide_query.filter(state_code__iexact=state_code)
        election.voter_guides_count = voter_guide_query.count()

        # Number of Public Positions
        position_query = PositionEntered.objects.all()
        # Catch both candidates and measures (which have google_civic_election_id in the Positions table)
        position_query = position_query.filter(
            Q(google_civic_election_id=election.google_civic_election_id) |
            Q(candidate_campaign_we_vote_id__in=candidate_we_vote_id_list))
        # As of Aug 2018 we are no longer using PERCENT_RATING
        position_query = position_query.exclude(stance__iexact='PERCENT_RATING')
        if is_national_election and positive_value_exists(state_code):
            position_query = position_query.filter(state_code__iexact=state_code)
        election.public_positions_count = position_query.count()

        messages_on_stage = get_messages(request)

        template_values = {
            'ballot_returned_search':                   ballot_returned_search,
            'ballot_returned_list':                     ballot_returned_list_modified,
            'ballot_returned_count_entire_election':    ballot_returned_count_entire_election,
            'ballot_returned_oldest_date':              ballot_returned_oldest_date,
            'ballot_returned_voter_oldest_date':        ballot_returned_voter_oldest_date,
            'ballotpedia_election_list':                ballotpedia_election_list,
            'entries_missing_latitude_longitude':       entries_missing_latitude_longitude,
            'election':                                 election,
            'google_civic_election_id':                 google_civic_election_id,
            'is_national_election':                     election.is_national_election,
            'map_points_retrieved_each_batch_chunk':    map_points_retrieved_each_batch_chunk,
            'messages_on_stage':                        messages_on_stage,
            'more_than_three_ballotpedia_elections':    more_than_three_ballotpedia_elections,
            'all_ballotpedia_elections_shown':          all_ballotpedia_elections_shown,
            'state_code':                               state_code,
            'state_list':                               sorted_state_list,
            'use_ctcl_as_data_source_override':         use_ctcl_as_data_source_override,
            'voter_ballot_saved_list':                  voter_ballot_saved_list,
            'voter_ballot_saved_search':                voter_ballot_saved_search,
        }
    else:
        messages_on_stage = get_messages(request)
        template_values = {
            'ballotpedia_election_list':                ballotpedia_election_list,
            'ballot_returned_count_entire_election':    ballot_returned_count_entire_election,
            'ballot_returned_oldest_date':              ballot_returned_oldest_date,
            'ballot_returned_voter_oldest_date':        ballot_returned_voter_oldest_date,
            'ballot_returned_search':                   ballot_returned_search,
            'entries_missing_latitude_longitude':       entries_missing_latitude_longitude,
            'google_civic_election_id':                 google_civic_election_id,
            'is_national_election':                     is_national_election,
            'map_points_retrieved_each_batch_chunk':    map_points_retrieved_each_batch_chunk,
            'messages_on_stage':                        messages_on_stage,
            'state_code':                               state_code,
            'state_list':                               sorted_state_list,
        }
    return render(request, 'election/election_summary.html', template_values)


@login_required
def elections_import_from_master_server_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in ELECTIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = elections_import_from_master_server(request)  # Consumes electionsSyncOut

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Elections import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required()
def election_migration_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_manager = ElectionManager()
    from_election = Election()
    from_election_list = []
    from_election_found = False
    office_manager = ContestOfficeManager()
    position_list_manager = PositionListManager()
    from_election_candidate_list = []
    from_election_office_list = []
    to_election_found = False
    error = False
    status = ""
    sorted_state_list = []

    google_civic_election = Election()
    results = election_manager.retrieve_upcoming_elections()
    google_civic_election_list = results['election_list']

    # Find the election using an internal election_id (greater than 1,000,000)
    from_election_id = convert_to_int(request.GET.get('from_election_id', 0))
    if not positive_value_exists(from_election_id):
        from_election_id = convert_to_int(request.POST.get('from_election_id', 0))
    from_state_code = request.GET.get('from_state_code', '')
    if not positive_value_exists(from_state_code):
        from_state_code = request.POST.get('from_state_code', '')
    if positive_value_exists(from_election_id):
        results = election_manager.retrieve_election(from_election_id, read_only=False)
        if results['election_found']:
            from_election = results['election']
            from_election_found = True

            state_list = STATE_CODE_MAP
            state_list_modified = {}
            for one_state_code, one_state_name in state_list.items():
                state_name_modified = one_state_name
                state_list_modified[one_state_code] = state_name_modified

            sorted_state_list = sorted(state_list_modified.items())

    # Find the google_civic election we want to migrate all data over to (coming from form submission)
    to_election_id = convert_to_int(request.GET.get('to_election_id', 0))  # GET
    if not positive_value_exists(to_election_id):
        to_election_id = convert_to_int(request.POST.get('to_election_id', 0))  # POST
    if positive_value_exists(to_election_id):
        results = election_manager.retrieve_election(to_election_id, read_only=False)
        if results['election_found']:
            google_civic_election = results['election']
            to_election_found = True

    # Do we want to actually migrate the election ids?
    change_now = request.POST.get('change_now', False)

    if change_now and not positive_value_exists(to_election_found) or not positive_value_exists(from_election_found):
        # Without a from and to election, we cannot change now
        messages.add_message(request, messages.ERROR, "Both elections must be chosen to start migration.")
        change_now = False

    if not positive_value_exists(from_election_found):
        # If we don't have the from election, break out
        template_values = {
            'change_now':                   change_now,
            'google_civic_election':        google_civic_election,
            'to_election_id':               to_election_id,
            'google_civic_election_list':   google_civic_election_list,
            'messages_on_stage':            messages_on_stage,
            'state_list':                   sorted_state_list,
            'from_election':                from_election,
            'from_election_id':             from_election_id,
            'from_election_list':           from_election_list,
            'from_election_candidate_list': from_election_candidate_list,
            'from_election_office_list':    from_election_office_list,
            'from_state_code':              from_state_code,
        }

        return render(request, 'election/election_migration.html', template_values)

    # ########################################
    # Analytics Action
    analytics_action_manager = AnalyticsManager()
    analytics_action_results = analytics_action_manager.retrieve_analytics_action_list(
        google_civic_election_id=from_election_id, state_code=from_state_code)
    from_election_analytics_action_count = 0
    if analytics_action_results['analytics_action_list_found']:
        from_election_analytics_action_list = analytics_action_results['analytics_action_list']
        from_election_analytics_action_count = len(from_election_analytics_action_list)

        if positive_value_exists(change_now):
            try:
                for one_analytics_action in from_election_analytics_action_list:
                    one_analytics_action.google_civic_election_id = to_election_id
                    one_analytics_action.save()
            except Exception as e:
                error = True
                status += analytics_action_results['status'] + str(e) + ' '

    # ########################################
    # Organization Election Metrics
    from_election_organization_election_metrics_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        organization_election_metrics_results = analytics_action_manager.retrieve_organization_election_metrics_list(
            from_election_id)
        if organization_election_metrics_results['organization_election_metrics_list_found']:
            from_election_organization_election_metrics_list = \
                organization_election_metrics_results['organization_election_metrics_list']
            from_election_organization_election_metrics_count = len(from_election_organization_election_metrics_list)

            if positive_value_exists(change_now):
                try:
                    for one_organization_election_metrics in from_election_organization_election_metrics_list:
                        one_organization_election_metrics.google_civic_election_id = to_election_id
                        one_organization_election_metrics.save()
                except Exception as e:
                    error = True
                    status += organization_election_metrics_results['status'] + str(e) + ' '

    # ########################################
    # Sitewide Election Metrics
    from_election_sitewide_election_metrics_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        sitewide_election_metrics_results = analytics_action_manager.retrieve_sitewide_election_metrics_list(
            from_election_id)
        if sitewide_election_metrics_results['sitewide_election_metrics_list_found']:
            from_election_sitewide_election_metrics_list = \
                sitewide_election_metrics_results['sitewide_election_metrics_list']
            from_election_sitewide_election_metrics_count = len(from_election_sitewide_election_metrics_list)

            if positive_value_exists(change_now):
                try:
                    for one_sitewide_election_metrics in from_election_sitewide_election_metrics_list:
                        one_sitewide_election_metrics.google_civic_election_id = to_election_id
                        one_sitewide_election_metrics.save()
                except Exception as e:
                    error = True
                    status += sitewide_election_metrics_results['status'] + str(e) + ' '

    # ########################################
    # BallotpediaApiCounter
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        ballotpedia_query = BallotpediaApiCounter.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_ballotpedia_api_counter_count = ballotpedia_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_ballotpedia_api_counter_count):
            try:
                BallotpediaApiCounter.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BALLOTPEDIA_API_COUNTER " + str(e) + ' '

    # ########################################
    # BallotpediaApiCounterDailySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        ballotpedia_query = BallotpediaApiCounterDailySummary.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_ballotpedia_api_counter_daily_count = ballotpedia_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_ballotpedia_api_counter_daily_count):
            try:
                BallotpediaApiCounterDailySummary.objects\
                    .filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BALLOTPEDIA_API_COUNTER_DAILY_SUMMARY " + str(e) + ' '

    # ########################################
    # BallotpediaApiCounterWeeklySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        ballotpedia_query = BallotpediaApiCounterWeeklySummary.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_ballotpedia_api_counter_weekly_count = ballotpedia_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_ballotpedia_api_counter_weekly_count):
            try:
                BallotpediaApiCounterWeeklySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BALLOTPEDIA_API_COUNTER_WEEKLY " + str(e) + ' '

    # ########################################
    # BallotpediaApiCounterMonthlySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        ballotpedia_query = BallotpediaApiCounterMonthlySummary.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_ballotpedia_api_counter_monthly_count = ballotpedia_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_ballotpedia_api_counter_monthly_count):
            try:
                BallotpediaApiCounterMonthlySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BALLOTPEDIA_API_COUNTER_MONTHLY " + str(e) + ' '

    # ########################################
    # Ballotpedia Election
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        ballotpedia_election_query = BallotpediaElection.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_ballotpedia_election_count = ballotpedia_election_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_ballotpedia_election_count):
            try:
                BallotpediaElection.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BALLOTPEDIA_ELECTIONS " + str(e) + ' '

    # ########################################
    # Ballot Items
    from_election_ballot_item_count = 0
    try:
        if positive_value_exists(from_state_code):
            from_election_ballot_item_count = BallotItem.objects.using('readonly')\
                .filter(google_civic_election_id=from_election_id)\
                .filter(state_code__iexact=from_state_code).count()
        else:
            from_election_ballot_item_count = \
                BallotItem.objects.using('readonly').filter(google_civic_election_id=from_election_id).count()
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                BallotItem.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code)\
                    .update(google_civic_election_id=to_election_id)
            else:
                BallotItem.objects.filter(
                    google_civic_election_id=from_election_id).update(google_civic_election_id=to_election_id)
            status += 'BALLOT_ITEMS_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_BALLOT_ITEMS ' + str(e) + ' '

    # ########################################
    # Ballot Returned
    from_election_ballot_returned_count = 0
    try:
        if positive_value_exists(from_state_code):
            from_election_ballot_returned_count = BallotReturned.objects\
                .filter(google_civic_election_id=from_election_id)\
                .filter(Q(state_code__iexact=from_state_code) | Q(normalized_state__iexact=from_state_code))\
                .count()
        else:
            from_election_ballot_returned_count = \
                BallotReturned.objects.filter(google_civic_election_id=from_election_id).count()
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                BallotReturned.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(Q(state_code__iexact=from_state_code) | Q(normalized_state__iexact=from_state_code))\
                    .update(google_civic_election_id=to_election_id)
            else:
                BallotReturned.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            status += 'BALLOT_RETURNED_ITEMS_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_BALLOT_RETURNED_ITEMS ' + str(e) + ' '

    # ########################################
    # Candidates
    from_election_candidate_count = 0
    try:
        if positive_value_exists(from_state_code):
            from_election_candidate_count = CandidateCampaign.objects.filter(google_civic_election_id=from_election_id)\
                .filter(state_code__iexact=from_state_code).count()
        else:
            from_election_candidate_count = \
                CandidateCampaign.objects.filter(google_civic_election_id=from_election_id).count()
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                CandidateCampaign.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code).update(google_civic_election_id=to_election_id)
            else:
                CandidateCampaign.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            status += 'CANDIDATES_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_CANDIDATES ' + str(e) + ' '

    # ########################################
    # CandidateToOfficeLink
    candidate_to_office_link_count = 0
    try:
        candidate_to_office_link_count = CandidateToOfficeLink.objects\
            .filter(google_civic_election_id=from_election_id).filter(state_code__iexact=from_state_code).count()
        if positive_value_exists(change_now):
            # Note that we never alter state_code in these routines
            CandidateToOfficeLink.objects\
                .filter(google_civic_election_id=from_election_id)\
                .filter(state_code__iexact=from_state_code)\
                .update(google_civic_election_id=to_election_id)
            status += 'CANDIDATE_TO_OFFICE_LINK_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_CANDIDATE_TO_OFFICE_LINK: ' + str(e) + ' '

    # ########################################
    # Candidates Hosted From Other Elections - We don't move, but include the count for error checking
    from_election_hosted_candidate_count = 0  # DEPRECATED ContestOfficeVisitingOtherElection

    # ########################################
    # GoogleCivicApiCounter
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        google_civic_api_query = GoogleCivicApiCounter.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_google_civic_api_counter_count = google_civic_api_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_google_civic_api_counter_count):
            try:
                GoogleCivicApiCounter.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_GOOGLE_CIVIC_API_COUNTER " + str(e) + ' '

    # ########################################
    # GoogleCivicApiCounterDailySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        google_civic_api_query = GoogleCivicApiCounterDailySummary.objects\
            .filter(google_civic_election_id=from_election_id)
        we_vote_google_civic_api_counter_daily_count = google_civic_api_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_google_civic_api_counter_daily_count):
            try:
                GoogleCivicApiCounterDailySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_GOOGLE_CIVIC_API_COUNTER_DAILY_SUMMARY " + str(e) + ' '

    # ########################################
    # GoogleCivicApiCounterWeeklySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        google_civic_api_query = GoogleCivicApiCounterWeeklySummary.objects\
            .filter(google_civic_election_id=from_election_id)
        we_vote_google_civic_api_counter_weekly_count = google_civic_api_query.count()
        if positive_value_exists(change_now) and positive_value_exists(
                we_vote_google_civic_api_counter_weekly_count):
            try:
                GoogleCivicApiCounterWeeklySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_GOOGLE_CIVIC_API_COUNTER_WEEKLY " + str(e) + ' '

    # ########################################
    # GoogleCivicApiCounterMonthlySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        google_civic_api_query = GoogleCivicApiCounterMonthlySummary.objects\
            .filter(google_civic_election_id=from_election_id)
        we_vote_google_civic_api_counter_monthly_count = google_civic_api_query.count()
        if positive_value_exists(change_now) and positive_value_exists(
                we_vote_google_civic_api_counter_monthly_count):
            try:
                GoogleCivicApiCounterMonthlySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_GOOGLE_CIVIC_API_COUNTER_MONTHLY " + str(e) + ' '

    # ########################################
    # Measures
    contest_measure_we_vote_ids_migrated = []
    from_election_measure_count = 0
    try:
        if positive_value_exists(from_state_code):
            contest_measure_query = ContestMeasure.objects.filter(google_civic_election_id=from_election_id)\
                .filter(state_code__iexact=from_state_code)
            from_election_measure_count = contest_measure_query.count()
            contest_measure_query = contest_measure_query.values_list('we_vote_id', flat=True).distinct()
            contest_measure_we_vote_ids_migrated = list(contest_measure_query)
        else:
            contest_measure_query = ContestMeasure.objects.filter(google_civic_election_id=from_election_id)
            from_election_measure_count = contest_measure_query.count()
            contest_measure_query = contest_measure_query.values_list('we_vote_id', flat=True).distinct()
            contest_measure_we_vote_ids_migrated = list(contest_measure_query)
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                ContestMeasure.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code)\
                    .update(google_civic_election_id=to_election_id)
            else:
                ContestMeasure.objects.filter(
                    google_civic_election_id=from_election_id).update(google_civic_election_id=to_election_id)
            status += 'MEASURES_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_MEASURES ' + str(e) + ' '

    # ########################################
    # Offices
    contest_office_we_vote_ids_migrated = []
    from_election_office_count = 0
    try:
        if positive_value_exists(from_state_code):
            contest_office_query = ContestOffice.objects.filter(google_civic_election_id=from_election_id)\
                .filter(state_code__iexact=from_state_code)
            from_election_office_count = contest_office_query.count()
            contest_office_query = contest_office_query.values_list('we_vote_id', flat=True).distinct()
            contest_office_we_vote_ids_migrated = list(contest_office_query)
        else:
            contest_office_query = \
                ContestOffice.objects.filter(google_civic_election_id=from_election_id)
            from_election_office_count = contest_office_query.count()
            contest_office_query = contest_office_query.values_list('we_vote_id', flat=True).distinct()
            contest_office_we_vote_ids_migrated = list(contest_office_query)
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                ContestOffice.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code)\
                    .update(google_civic_election_id=to_election_id)
            else:
                ContestOffice.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            status += 'OFFICES_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_OFFICES ' + str(e) + ' '

    # ########################################
    # Offices Hosted From Other Elections - We don't move, but include the count for error checking
    # TODO: April 6, 2022 restored the following 5 lines, to eliminate the undefined variable errors
    office_visiting_list_we_vote_ids = office_manager.fetch_office_visiting_list_we_vote_ids(
        host_google_civic_election_id_list=[from_election_id])
    contest_office_visiting_host_count = 0
    position_network_scores_migrated = 0
    contest_office_visiting_origin_count = 0
    # End of restore TODO
    from_election_hosted_office_count = 0
    try:
        if positive_value_exists(from_state_code):
            from_election_hosted_office_count = ContestOffice.objects\
                .filter(we_vote_id__in=office_visiting_list_we_vote_ids)\
                .filter(state_code__iexact=from_state_code).count()
        else:
            from_election_hosted_office_count = \
                ContestOffice.objects.filter(we_vote_id__in=office_visiting_list_we_vote_ids).count()
    except Exception as e:
        error = True
        status += 'FAILED_TO_COUNT_HOSTED_OFFICES ' + str(e) + ' '

    # ########################################
    # Pledge to Vote
    from_election_pledge_to_vote_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        pledge_to_vote_manager = PledgeToVoteManager()
        results = pledge_to_vote_manager.retrieve_pledge_to_vote_list(from_election_id)
        if results['pledge_to_vote_list_found']:
            from_election_pledge_to_vote_list = results['pledge_to_vote_list']
            from_election_pledge_to_vote_count = len(from_election_pledge_to_vote_list)

            if positive_value_exists(change_now):
                try:
                    for one_pledge_to_vote in from_election_pledge_to_vote_list:
                        # Save the election_id we want to migrate to
                        one_pledge_to_vote.google_civic_election_id = to_election_id
                        one_pledge_to_vote.save()
                except Exception as e:
                    error = True
                    status += results['status'] + str(e) + ' '

    # ########################################
    # Positions

    # retrieve public positions
    public_position_count = 0
    try:
        if positive_value_exists(from_state_code):
            public_position_count = PositionEntered.objects.filter(google_civic_election_id=from_election_id)\
                .filter(Q(contest_office_we_vote_id__in=contest_office_we_vote_ids_migrated) |
                        Q(contest_measure_we_vote_id__in=contest_measure_we_vote_ids_migrated))\
                .count()
        else:
            public_position_count = \
                PositionEntered.objects.filter(google_civic_election_id=from_election_id).count()
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                PositionEntered.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(Q(contest_office_we_vote_id__in=contest_office_we_vote_ids_migrated) |
                            Q(contest_measure_we_vote_id__in=contest_measure_we_vote_ids_migrated))\
                    .update(google_civic_election_id=to_election_id)
            else:
                PositionEntered.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            status += 'POSITION_ENTERED_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_POSITION_ENTERED ' + str(e) + ' '

    # retrieve friends-only positions
    friend_position_count = 0
    try:
        if positive_value_exists(from_state_code):
            friend_position_count = PositionForFriends.objects.filter(google_civic_election_id=from_election_id)\
                .filter(Q(contest_office_we_vote_id__in=contest_office_we_vote_ids_migrated) |
                        Q(contest_measure_we_vote_id__in=contest_measure_we_vote_ids_migrated))\
                .count()
        else:
            friend_position_count = \
                PositionForFriends.objects.filter(google_civic_election_id=from_election_id).count()
        if positive_value_exists(change_now):
            if positive_value_exists(from_state_code):
                PositionForFriends.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(Q(contest_office_we_vote_id__in=contest_office_we_vote_ids_migrated) |
                            Q(contest_measure_we_vote_id__in=contest_measure_we_vote_ids_migrated))\
                    .update(google_civic_election_id=to_election_id)
            else:
                PositionForFriends.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            status += 'POSITION_FOR_FRIENDS_UPDATED '
    except Exception as e:
        error = True
        status += 'FAILED_TO_UPDATE_POSITION_FOR_FRIENDS ' + str(e) + ' '

    # ########################################
    # Quick Info
    from_election_quick_info_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        quick_info_manager = QuickInfoManager()
        quick_info_results = quick_info_manager.retrieve_quick_info_list(from_election_id)
        if quick_info_results['quick_info_list_found']:
            from_election_quick_info_list = quick_info_results['quick_info_list']
            from_election_quick_info_count = len(from_election_quick_info_list)

            if positive_value_exists(change_now):
                try:
                    for one_quick_info in from_election_quick_info_list:
                        one_quick_info.google_civic_election_id = to_election_id
                        one_quick_info.save()
                except Exception as e:
                    error = True
                    status += quick_info_results['status'] + str(e) + ' '

    # ########################################
    # Remote Request History
    from_election_remote_request_history_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        remote_request_history_manager = RemoteRequestHistoryManager()
        remote_request_history_results = remote_request_history_manager.retrieve_remote_request_history_list(
            from_election_id)
        if remote_request_history_results['remote_request_history_list_found']:
            from_election_remote_request_history_list = remote_request_history_results['remote_request_history_list']
            from_election_remote_request_history_count = len(from_election_remote_request_history_list)

            if positive_value_exists(change_now):
                try:
                    for one_remote_request_history in from_election_remote_request_history_list:
                        one_remote_request_history.google_civic_election_id = to_election_id
                        one_remote_request_history.save()
                except Exception as e:
                    error = True
                    status += remote_request_history_results['status'] + str(e) + ' '

    # ########################################
    # Voter Address
    from_election_voter_address_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        voter_address_manager = VoterAddressManager()
        voter_address_results = voter_address_manager.retrieve_voter_address_list(from_election_id)
        if voter_address_results['voter_address_list_found']:
            from_election_voter_address_list = voter_address_results['voter_address_list']
            from_election_voter_address_count = len(from_election_voter_address_list)

            if positive_value_exists(change_now):
                try:
                    for one_voter_address in from_election_voter_address_list:
                        one_voter_address.google_civic_election_id = to_election_id
                        one_voter_address.save()
                except Exception as e:
                    error = True
                    status += voter_address_results['status'] + str(e) + ' '

    # ########################################
    # VoterBallotSaved
    if positive_value_exists(from_state_code):
        from_election_voter_ballot_saved_count = VoterBallotSaved.objects\
            .filter(google_civic_election_id=from_election_id).filter(state_code__iexact=from_state_code).count()
    else:
        from_election_voter_ballot_saved_count = VoterBallotSaved.objects\
            .filter(google_civic_election_id=from_election_id).count()
    if positive_value_exists(change_now) and positive_value_exists(from_election_voter_ballot_saved_count):
        try:
            if positive_value_exists(from_state_code):
                VoterBallotSaved.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code)\
                    .update(google_civic_election_id=to_election_id)
            else:
                VoterBallotSaved.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
        except Exception as e:
            error = True
            status += "COULD_NOT_UPDATE_ALL_VOTER_BALLOT_SAVED " + str(e) + ' '

    # ########################################
    # Voter Device Link
    from_election_voter_device_link_count = 0
    if positive_value_exists(from_state_code):
        from_election_voter_device_link_count = VoterDeviceLink.objects\
            .filter(google_civic_election_id=from_election_id).filter(state_code__iexact=from_state_code)\
            .count()
    else:
        from_election_voter_device_link_count = VoterDeviceLink.objects\
            .filter(google_civic_election_id=from_election_id).count()
    if positive_value_exists(change_now) and positive_value_exists(from_election_voter_device_link_count):
        try:
            if positive_value_exists(from_state_code):
                VoterDeviceLink.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code)\
                    .update(google_civic_election_id=to_election_id)
            else:
                VoterDeviceLink.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
        except Exception as e:
            error = True
            status += "COULD_NOT_UPDATE_ALL_VOTER_DEVICE_LINKS " + str(e) + ' '

    # ########################################
    # Voter Guides
    from_election_voter_guide_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        voter_guide_manager = VoterGuideListManager()
        google_civic_election_id_list = [from_election_id]
        voter_guide_results = voter_guide_manager.retrieve_voter_guides_for_election(google_civic_election_id_list)
        if voter_guide_results['voter_guide_list_found']:
            from_election_voter_guide_list = voter_guide_results['voter_guide_list']
            from_election_voter_guide_count = len(from_election_voter_guide_list)
    
            if positive_value_exists(change_now):
                try:
                    for one_voter_guide in from_election_voter_guide_list:
                        one_voter_guide.google_civic_election_id = to_election_id
                        one_voter_guide.save()
                except Exception as e:
                    error = True
                    status += voter_guide_results['status'] + str(e) + ' '

    # ########################################
    # VoterGuidePossibility
    # if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
    #     one_number = 0
    #     if positive_value_exists(change_now):
    #         try:
    #             for one_number in POSSIBLE_ENDORSEMENT_NUMBER_LIST:
    #                 key = "google_civic_election_id_" + one_number
    #                 VoterGuidePossibility.objects.filter(
    #                     **{key: from_election_id}).update(
    #                     **{key: to_election_id})
    #         except Exception as e:
    #             error = True
    #             status += "COULD_NOT_UPDATE_ALL_VOTER_GUIDE_POSSIBILITIES, one_number: " + str(one_number) + \
    #                       " " + str(e) + ' '

    # ########################################
    # VoteSmartApiCounter
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        vote_smart_query = VoteSmartApiCounter.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_vote_smart_api_counter_count = vote_smart_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_vote_smart_api_counter_count):
            try:
                VoteSmartApiCounter.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_VOTE_SMART_API_COUNTER " + str(e) + ' '

    # ########################################
    # VoteSmartApiCounterDailySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        vote_smart_query = VoteSmartApiCounterDailySummary.objects.filter(google_civic_election_id=from_election_id)
        we_vote_vote_smart_api_counter_daily_count = vote_smart_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_vote_smart_api_counter_daily_count):
            try:
                VoteSmartApiCounterDailySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_VOTE_SMART_API_COUNTER_DAILY_SUMMARY " + str(e) + ' '

    # ########################################
    # VoteSmartApiCounterWeeklySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        vote_smart_query = VoteSmartApiCounterWeeklySummary.objects.filter(
            google_civic_election_id=from_election_id)
        we_vote_vote_smart_api_counter_weekly_count = vote_smart_query.count()
        if positive_value_exists(change_now) and positive_value_exists(
                we_vote_vote_smart_api_counter_weekly_count):
            try:
                VoteSmartApiCounterWeeklySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_VOTE_SMART_API_COUNTER_WEEKLY " + str(e) + ' '

    # ########################################
    # VoteSmartApiCounterMonthlySummary
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        vote_smart_query = VoteSmartApiCounterMonthlySummary.objects.filter(google_civic_election_id=from_election_id)
        we_vote_vote_smart_api_counter_monthly_count = vote_smart_query.count()
        if positive_value_exists(change_now) and positive_value_exists(
                we_vote_vote_smart_api_counter_monthly_count):
            try:
                VoteSmartApiCounterMonthlySummary.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_VOTE_SMART_API_COUNTER_MONTHLY " + str(e) + ' '

    # ########################################
    # We Vote Images
    from_election_we_vote_image_count = 0
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        we_vote_image_manager = WeVoteImageManager()
        we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_list_from_google_civic_election_id(
            from_election_id)
        if we_vote_image_results['we_vote_image_list_found']:
            from_election_we_vote_image_list = we_vote_image_results['we_vote_image_list']
            from_election_we_vote_image_count = len(from_election_we_vote_image_list)
    
            if positive_value_exists(change_now):
                try:
                    for one_we_vote_image in from_election_we_vote_image_list:
                        one_we_vote_image.google_civic_election_id = to_election_id
                        one_we_vote_image.save()
                except Exception as e:
                    error = True
                    status += we_vote_image_results['status'] + str(e) + ' '

    # ########################################
    # BatchDescription
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchDescription.objects.filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchDescription.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_DESCRIPTIONS " + str(e) + ' '

    # ########################################
    # BatchRowActionBallotItem
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchRowActionBallotItem.objects.using('readonly')\
            .filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchRowActionBallotItem.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_BALLOT_ITEMS " + str(e) + ' '

    # ########################################
    # BatchRowActionCandidate
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchRowActionCandidate.objects.using('readonly')\
            .filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchRowActionCandidate.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_CANDIDATES " + str(e) + ' '

    # ########################################
    # BatchRowActionContestOffice
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchRowActionContestOffice.objects.using('readonly')\
            .filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchRowActionContestOffice.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_CONTEST_OFFICES " + str(e) + ' '

    # ########################################
    # BatchRowActionMeasure
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchRowActionMeasure.objects.using('readonly').filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchRowActionMeasure.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_MEASURES " + str(e) + ' '

    # ########################################
    # BatchRowActionPosition
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchRowActionPosition.objects.using('readonly').filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchRowActionPosition.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_POSITIONS " + str(e) + ' '

    # ########################################
    # BatchRowTranslationMap
    if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
        batch_query = BatchRowTranslationMap.objects.using('readonly').filter(google_civic_election_id=from_election_id)
        we_vote_batch_count = batch_query.count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            try:
                BatchRowTranslationMap.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
            except Exception as e:
                error = True
                status += "COULD_NOT_UPDATE_ALL_BATCH_TRANSLATION_MAPS " + str(e) + ' '

    # ########################################
    # BatchSet
    try:
        if positive_value_exists(from_state_code):
            we_vote_batch_count = BatchSet.objects.using('readonly')\
                .filter(google_civic_election_id=from_election_id)\
                .filter(state_code__iexact=from_state_code).count()
        else:
            we_vote_batch_count = BatchSet.objects.using('readonly')\
                .filter(google_civic_election_id=from_election_id).count()
        if positive_value_exists(change_now) and positive_value_exists(we_vote_batch_count):
            if positive_value_exists(from_state_code):
                BatchSet.objects.filter(google_civic_election_id=from_election_id)\
                    .filter(state_code__iexact=from_state_code)\
                    .update(google_civic_election_id=to_election_id)
            else:
                BatchSet.objects.filter(google_civic_election_id=from_election_id)\
                    .update(google_civic_election_id=to_election_id)
    except Exception as e:
        error = True
        status += "COULD_NOT_UPDATE_ALL_BATCH_SETS " + str(e) + ' '

    # ########################################
    # There are some settings on the election object we want to transfer
    # NOTE: This is less relevant when we are moving elections into other elections
    # if not positive_value_exists(from_state_code):  # Only move if we are NOT moving just one state
    #     if positive_value_exists(change_now) and not positive_value_exists(error):
    #         try:
    #             google_civic_election.candidate_photos_finished = from_election.candidate_photos_finished
    #             from_election.candidate_photos_finished = False
    #
    #             google_civic_election.election_preparation_finished = from_election.election_preparation_finished
    #             from_election.election_preparation_finished = False
    #
    #             google_civic_election.ignore_this_election = from_election.ignore_this_election
    #             from_election.ignore_this_election = False
    #
    #             google_civic_election.include_in_list_for_voters = from_election.include_in_list_for_voters
    #             from_election.include_in_list_for_voters = False
    #
    #             google_civic_election.internal_notes = from_election.internal_notes
    #             from_election.internal_notes = None
    #
    #             google_civic_election.is_national_election = from_election.is_national_election
    #             from_election.is_national_election = False
    #
    #             google_civic_election.save()
    #             from_election.save()
    #
    #         except Exception as e:
    #             error = True
    #             status += "COULD_NOT_SAVE_ELECTIONS " + str(e) + ' '

    # #########################
    # Now print results to the screen
    message_with_summary_of_elections = 'Election Migration from election id {from_election_id} ' \
                                        'to election id {to_election_id}. ' \
                                        ''.format(from_election_id=from_election_id,
                                                  to_election_id=to_election_id)

    if positive_value_exists(change_now):
        info_message = message_with_summary_of_elections + '<br />Changes completed.<br />' \
                         'status: {status} '.format(status=status, )

        messages.add_message(request, messages.INFO, info_message)
    elif error:
        error_message = 'There was an error migrating data.<br />' \
                         'status: {status} '.format(status=status, )

        messages.add_message(request, messages.ERROR, error_message)
    else:
        current_counts = "\'from\' counts: " \
                         "\n" \
                         'office_count: {office_count}, ' \
                         'hosted_office_count: {hosted_office_count}, ' \
                         'candidate_count: {candidate_count}, ' \
                         'candidate_to_office_link_count: {candidate_to_office_link_count},' \
                         'hosted_candidate_count: {hosted_candidate_count}, ' \
                         '\n' \
                         'public_position_count: {public_position_count}, ' \
                         'friend_position_count: {friend_position_count}, ' \
                         'analytics_action_count: {analytics_action_count}, ' \
                         'organization_election_metrics_count: {organization_election_metrics_count}, ' \
                         'sitewide_election_metrics_count: {sitewide_election_metrics_count}, ' \
                         '\n' \
                         'ballot_item_count: {ballot_item_count}, ' \
                         'ballot_returned_count: {ballot_returned_count}, ' \
                         'voter_ballot_saved_count: {voter_ballot_saved_count}, ' \
                         'we_vote_image_count: {we_vote_image_count}, ' \
                         '\n' \
                         'measure_count: {measure_count}, ' \
                         'pledge_to_vote_count: {pledge_to_vote_count}, ' \
                         'quick_info_count: {quick_info_count}, ' \
                         'remote_request_history_count: {remote_request_history_count}, ' \
                         '\n' \
                         'voter_address_count: {voter_address_count}, ' \
                         'voter_device_link_count: {voter_device_link_count}, ' \
                         'voter_guide_count: {voter_guide_count}, ' \
                         'position_network_scores_count: {position_network_scores_migrated}, ' \
                         '\n' \
                         'contest_office_visiting_host_count: {contest_office_visiting_host_count}, ' \
                         'contest_office_visiting_origin_count: {contest_office_visiting_origin_count}, ' \
                         'status: {status} '.format(
                             office_count=from_election_office_count,
                             hosted_office_count=from_election_hosted_office_count,
                             candidate_count=from_election_candidate_count,
                             hosted_candidate_count=from_election_hosted_candidate_count,
                             candidate_to_office_link_count=candidate_to_office_link_count,
                             public_position_count=public_position_count,
                             friend_position_count=friend_position_count,
                             analytics_action_count=from_election_analytics_action_count,
                             pledge_to_vote_count=from_election_pledge_to_vote_count,
                             organization_election_metrics_count=from_election_organization_election_metrics_count,
                             sitewide_election_metrics_count=from_election_sitewide_election_metrics_count,
                             ballot_item_count=from_election_ballot_item_count,
                             ballot_returned_count=from_election_ballot_returned_count,
                             voter_ballot_saved_count=from_election_voter_ballot_saved_count,
                             we_vote_image_count=from_election_we_vote_image_count,
                             measure_count=from_election_measure_count,
                             quick_info_count=from_election_quick_info_count,
                             remote_request_history_count=from_election_remote_request_history_count,
                             voter_address_count=from_election_voter_address_count,
                             voter_device_link_count=from_election_voter_device_link_count,
                             voter_guide_count=from_election_voter_guide_count,
                             position_network_scores_migrated=position_network_scores_migrated,
                             contest_office_visiting_host_count=contest_office_visiting_host_count,
                             contest_office_visiting_origin_count=contest_office_visiting_origin_count,
                             status=status,)

        info_message = message_with_summary_of_elections + current_counts

        messages.add_message(request, messages.INFO, info_message)

    template_values = {
        'change_now':                   change_now,
        'google_civic_election':        google_civic_election,
        'to_election_id':               to_election_id,
        'google_civic_election_list':   google_civic_election_list,
        'messages_on_stage':            messages_on_stage,
        'state_list':                   sorted_state_list,
        'from_election':                from_election,
        'from_election_id':             from_election_id,
        'from_election_list':           from_election_list,
        'from_election_candidate_list': from_election_candidate_list,
        'from_election_office_list':    from_election_office_list,
        'from_state_code':              from_state_code,
    }

    return render(request, 'election/election_migration.html', template_values)

@login_required
def election_ballot_location_visualize_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    show_base_pins = request.GET.get('show_base_pins', True)
    show_no_pins = request.GET.get('show_no_pins', True)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', 'CA').upper()
    if state_code == '':
        state_code = 'CA'
    election_id = 0
    is_national_election = False
    election_name = ''
    if positive_value_exists(google_civic_election_id):
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id, read_only=False)
        if results['election_found']:
            election = results['election']
            election_name = election.election_name
            election_id = election.id
            is_national_election = election.is_national_election
            if not positive_value_exists(is_national_election):
                is_national_election = False

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    #  Predefined Google Maps marker icons are listed at https://kml4earth.appspot.com/icons.html
    template_values = {
        'election_id':              election_id,
        'election_name':            election_name,
        'geo_center_lat':           request.GET.get('geo_center_lat', STATE_GEOGRAPHIC_CENTER.get(state_code)[0]),
        'geo_center_lng':           request.GET.get('geo_center_lng', STATE_GEOGRAPHIC_CENTER.get(state_code)[1]),
        'geo_center_zoom':          request.GET.get('geo_center_zoom', STATE_GEOGRAPHIC_CENTER.get(state_code)[2]),
        'google_civic_election_id': google_civic_election_id,
        'icon_scale_base':          25,                # 25 percent of full size
        'icon_scale_no':            25,                # 25 percent of full size
        'icon_url_base':            'https://maps.google.com/mapfiles/kml/paddle/grn-circle.png',
        'icon_url_no':              'https://maps.google.com/mapfiles/kml/paddle/red-stars.png',
        'is_national_election':     is_national_election,
        'show_base_pins':           show_base_pins,
        'show_no_pins':             show_no_pins,
        'state_code':               state_code,
        'state_list':               sorted_state_list,
        'google_maps_api_key':      GOOGLE_MAPS_API_KEY,
    }

    return render(request, 'election/election_ballot_location_visualize.html', template_values)
