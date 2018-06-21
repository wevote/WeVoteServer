# election/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import election_remote_retrieve, elections_import_from_master_server
from .models import Election
from admin_tools.views import redirect_to_sign_in_page
from analytics.models import AnalyticsManager
from ballot.controllers import refresh_voter_ballots_from_polling_location
from ballot.models import BallotItemListManager, BallotReturnedListManager, BallotReturnedManager, \
    VoterBallotSavedManager
from candidate.models import CandidateCampaignListManager, CandidateCampaign
from config.base import get_environment_variable
from datetime import datetime, timedelta
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from election.models import ElectionManager
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from image.models import WeVoteImageManager
from import_export_google_civic.controllers import retrieve_one_ballot_from_google_civic_api, \
    store_one_ballot_from_google_civic_api
from measure.models import ContestMeasureList
from office.models import ContestOfficeListManager
from pledge_to_vote.models import PledgeToVoteManager
from polling_location.models import PollingLocation
from position.models import ANY_STANCE, PositionEntered, PositionListManager
import pytz
from quick_info.models import QuickInfoManager
from wevote_settings.models import RemoteRequestHistoryManager
from voter.models import VoterAddressManager, VoterDeviceLinkManager, voter_has_authority
from voter_guide.models import VoterGuide, VoterGuideListManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)

ELECTIONS_SYNC_URL = get_environment_variable("ELECTIONS_SYNC_URL")  # electionsSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


@login_required
def election_all_ballots_retrieve_view(request, election_local_id=0):
    """
    Reach out to Google and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those polling locations, enough that we are caching all of the possible ballot items
    :param request:
    :param election_local_id:
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

    ballots_retrieved = 0
    ballots_not_retrieved = 0
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
                    # Now refresh all of the other copies of this ballot
                    if positive_value_exists(polling_location.we_vote_id) \
                            and positive_value_exists(google_civic_election_id):
                        refresh_ballot_results = refresh_voter_ballots_from_polling_location(
                            ballot_returned, google_civic_election_id)
                        ballots_refreshed += refresh_ballot_results['ballots_refreshed']
                # NOTE: We don't support retrieving ballots for polling locations AND geocoding simultaneously
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
    Reach out to Google and retrieve ballot data (for one ballot, typically a polling location)
    :param request:
    :param election_local_id:
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

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
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
                                 'Could not retrieve ballot data for this polling location for {election_name}, '
                                 'state: {state}. '.format(
                                     election_name=election_on_stage.election_name,
                                     state=state_code))
            return HttpResponseRedirect(reverse('ballot:ballot_item_list_edit', args=(ballot_returned_id,)) +
                                        "?polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&google_civic_election_id=" + str(google_civic_election_id)
                                        )
        except Exception as e:
            messages.add_message(request, messages.ERROR,
                                 'Problem retrieving polling location '
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
                # Now refresh all of the other copies of this ballot
                if positive_value_exists(polling_location_we_vote_id) \
                        and positive_value_exists(google_civic_election_id):
                    refresh_ballot_results = refresh_voter_ballots_from_polling_location(
                        ballot_returned, google_civic_election_id)
                    ballots_refreshed = refresh_ballot_results['ballots_refreshed']
                elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                    # Nothing else to be done
                    pass
            # NOTE: We don't support retrieving ballots for polling locations AND geocoding simultaneously
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
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_local_id = convert_to_int(election_local_id)
    election_on_stage_found = False
    election_on_stage = Election()

    if positive_value_exists(election_local_id):
        try:
            election_on_stage = Election.objects.get(id=election_local_id)
            election_on_stage_found = True
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except Election.DoesNotExist:
            # This is fine, create new
            pass
    else:
        # If here we are creating a
        pass

    if election_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'election': election_on_stage,
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
    election_id = convert_to_int(request.POST.get('election_id', 0))
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this election. '
                             'Please check the checkbox to confirm you want to delete this election.')
        return HttpResponseRedirect(reverse('election:election_edit', args=(election_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    election_manager = ElectionManager()
    results = election_manager.retrieve_election(0, election_id)
    if results['election_found']:
        election = results['election']

        office_list_manager = ContestOfficeListManager()
        office_count = office_list_manager.fetch_office_count(election.google_civic_election_id)

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
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status = ""

    election_local_id = convert_to_int(request.POST.get('election_id', 0))
    election_name = request.POST.get('election_name', False)
    election_day_text = request.POST.get('election_day_text', False)
    state_code = request.POST.get('state_code', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', '0')
    ballotpedia_election_id = request.POST.get('ballotpedia_election_id', False)
    ballotpedia_kind_of_election = request.POST.get('ballotpedia_kind_of_election', False)
    include_in_list_for_voters = request.POST.get('include_in_list_for_voters', False)

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
                election_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    if not election_on_stage_found and positive_value_exists(ballotpedia_election_id):
        status += "RETRIEVING_ELECTION_BY_BALLOTPEDIA_ELECTION_ID "
        try:
            election_query = Election.objects.filter(ballotpedia_election_id=ballotpedia_election_id)
            if len(election_query):
                election_on_stage = election_query[0]
                election_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    if election_on_stage_found:
        status += "UPDATING_EXISTING_ELECTION "
        # if convert_to_int(election_on_stage.google_civic_election_id) < 1000000:  # Not supported currently
        # If here, this is an election created by Google Civic and we limit what fields to update
        # If here, this is a We Vote created election

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
            election_on_stage.ballotpedia_election_id = convert_to_int(ballotpedia_election_id)

        if ballotpedia_kind_of_election is not False:
            election_on_stage.ballotpedia_kind_of_election = ballotpedia_kind_of_election

        election_on_stage.include_in_list_for_voters = include_in_list_for_voters

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

        try:
            election_on_stage = Election(
                google_civic_election_id=google_civic_election_id,
                include_in_list_for_voters=include_in_list_for_voters,
                state_code=state_code,
            )
            if positive_value_exists(ballotpedia_election_id):
                election_on_stage.ballotpedia_election_id = ballotpedia_election_id
            if positive_value_exists(election_name):
                election_on_stage.election_name = election_name
            if positive_value_exists(election_day_text):
                election_on_stage.election_day_text = election_day_text
            election_on_stage.save()
            status += "CREATED_NEW_ELECTION "
            messages.add_message(request, messages.INFO, 'New election ' + str(election_name) + ' saved.')
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save new election ' +
                                 str(google_civic_election_id) +
                                 '. ' + status)

    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_manager', 'political_data_viewer',
                          'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    election_search = request.GET.get('election_search', '')
    show_all_elections = request.GET.get('show_all_elections', False)

    messages_on_stage = get_messages(request)

    election_list_query = Election.objects.all()
    election_list_query = election_list_query.order_by('election_day_text').reverse()
    election_list_query = election_list_query.exclude(google_civic_election_id=2000)

    if not positive_value_exists(show_all_elections):
        timezone = pytz.timezone("America/Los_Angeles")
        datetime_now = timezone.localize(datetime.now())
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
    for election in election_list:
        election.ballot_returned_count = \
            ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                election.google_civic_election_id, election.state_code)
        election.ballot_location_display_option_on_count = \
            ballot_returned_list_manager.fetch_ballot_location_display_option_on_count_for_election(
                election.google_civic_election_id, election.state_code)

        # if not positive_value_exists(show_all_elections):
        # If we are only looking at upcoming elections, gather some additional statistics
        # How many candidates?
        candidate_list_query = CandidateCampaign.objects.all()
        candidate_list_query = candidate_list_query.filter(
            google_civic_election_id=election.google_civic_election_id)
        election.candidate_count = candidate_list_query.count()

        # How many without photos?
        candidate_list_query = CandidateCampaign.objects.all()
        candidate_list_query = candidate_list_query.filter(
            google_civic_election_id=election.google_civic_election_id)
        candidate_list_query = candidate_list_query.filter(
            Q(we_vote_hosted_profile_image_url_tiny__isnull=True) | Q(we_vote_hosted_profile_image_url_tiny='')
        )
        election.candidates_without_photo_count = candidate_list_query.count()

        # Number of Voter Guides
        voter_guide_query = VoterGuide.objects.filter(google_civic_election_id=election.google_civic_election_id)
        election.voter_guides_count = voter_guide_query.count()

        # Number of Public Positions
        position_query = PositionEntered.objects.filter(google_civic_election_id=election.google_civic_election_id)
        election.public_positions_count = position_query.count()

        election_list_modified.append(election)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'election_list':            election_list_modified,
        'election_search':          election_search,
        'google_civic_election_id': google_civic_election_id,
        'show_all_elections':       show_all_elections,
        'state_code':               state_code,
    }
    return render(request, 'election/election_list.html', template_values)


@login_required()
def election_remote_retrieve_view(request):
    """
    Reach out to Google and retrieve the latest list of available elections
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    results = election_remote_retrieve()

    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Upcoming elections retrieved from Google Civic.')
    return HttpResponseRedirect(reverse('election:election_list', args=()))


@login_required()
def election_summary_view(request, election_local_id=0, google_civic_election_id=''):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_manager', 'political_data_viewer',
                          'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    show_offices_and_candidates = request.GET.get('show_offices_and_candidates', False)
    if not positive_value_exists(google_civic_election_id):
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')
    election_local_id = convert_to_int(election_local_id)
    ballot_returned_search = request.GET.get('ballot_returned_search', '')
    voter_ballot_saved_search = request.GET.get('voter_ballot_saved_search', '')

    election_on_stage_found = False
    election_on_stage = Election()

    try:
        if positive_value_exists(election_local_id):
            election_on_stage = Election.objects.get(id=election_local_id)
        else:
            election_on_stage = Election.objects.get(google_civic_election_id=google_civic_election_id)
        election_on_stage_found = True
        election_local_id = election_on_stage.id
        google_civic_election_id = election_on_stage.google_civic_election_id
        state_code = election_on_stage.state_code
    except Election.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Election.DoesNotExist:
        # This is fine, proceed anyways
        pass

    sorted_state_list = []
    status_print_list = ""
    ballot_returned_count = 0
    ballot_returned_count_entire_election = 0
    entries_missing_latitude_longitude = 0
    ballot_returned_list_manager = BallotReturnedListManager()
    candidate_campaign_list_manager = CandidateCampaignListManager()

    if election_on_stage_found:
        state_list = STATE_CODE_MAP
        state_list_modified = {}
        for one_state_code, one_state_name in state_list.items():
            ballot_returned_count = ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                election_on_stage.google_civic_election_id, one_state_code)

            state_name_modified = one_state_name
            if positive_value_exists(ballot_returned_count):
                state_name_modified += " - " + str(ballot_returned_count)
            state_list_modified[one_state_code] = state_name_modified

        sorted_state_list = sorted(state_list_modified.items())

        limit = 100  # Since this is a summary page, we don't need to show very many ballot_returned entries
        ballot_returned_list_results = ballot_returned_list_manager.retrieve_ballot_returned_list_for_election(
            election_on_stage.google_civic_election_id, state_code, limit, ballot_returned_search)
        ballot_returned_count_entire_election = \
            ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                election_on_stage.google_civic_election_id)
        entries_missing_latitude_longitude = \
            ballot_returned_list_manager.fetch_ballot_returned_entries_needed_lat_long_for_election(
                election_on_stage.google_civic_election_id, state_code)

        if ballot_returned_list_results['success']:
            ballot_returned_list = ballot_returned_list_results['ballot_returned_list']
            if not positive_value_exists(state_code):
                ballot_returned_list = ballot_returned_list[:limit]
        else:
            ballot_returned_list = []

        status_print_list += "ballot_returned_count: " + str(ballot_returned_count_entire_election) + ""
        messages.add_message(request, messages.INFO, status_print_list)
        messages_on_stage = get_messages(request)

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
                    results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                        one_ballot_returned.polling_location_we_vote_id, google_civic_election_id)
                    if results['ballot_item_list_found']:
                        ballot_item_list = results['ballot_item_list']
                        ballot_items_count = len(ballot_item_list)
                        for one_ballot_item in ballot_item_list:
                            if positive_value_exists(one_ballot_item.contest_office_we_vote_id):
                                offices_count += 1
                                office_list.append(one_ballot_item.contest_office_we_vote_id)
                                candidate_results = candidate_campaign_list_manager.retrieve_candidate_count_for_office(
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
                google_civic_election_id, find_all_entries_for_election=True)
        if voter_ballot_saved_results['voter_ballot_saved_list_found']:
            voter_ballot_saved_list = voter_ballot_saved_results['voter_ballot_saved_list']

        template_values = {
            'ballot_returned_search':                   ballot_returned_search,
            'ballot_returned_list':                     ballot_returned_list_modified,
            'ballot_returned_count_entire_election':    ballot_returned_count_entire_election,
            'entries_missing_latitude_longitude':       entries_missing_latitude_longitude,
            'election':                                 election_on_stage,
            'google_civic_election_id':                 google_civic_election_id,
            'messages_on_stage':                        messages_on_stage,
            'state_code':                               state_code,
            'state_list':                               sorted_state_list,
            'voter_ballot_saved_list':                  voter_ballot_saved_list,
            'voter_ballot_saved_search':                voter_ballot_saved_search,
        }
    else:
        messages_on_stage = get_messages(request)

        template_values = {
            'ballot_returned_count_entire_election':    ballot_returned_count_entire_election,
            'ballot_returned_search':                   ballot_returned_search,
            'entries_missing_latitude_longitude':       entries_missing_latitude_longitude,
            'google_civic_election_id':                 google_civic_election_id,
            'messages_on_stage':                        messages_on_stage,
            'state_code':                               state_code,
            'state_list':                               sorted_state_list,
        }
    return render(request, 'election/election_summary.html', template_values)


@login_required
def elections_import_from_master_server_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in ELECTIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = elections_import_from_master_server(request)

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
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    election_manager = ElectionManager()
    we_vote_election = Election()
    we_vote_election_found = False
    office_list_manager = ContestOfficeListManager()
    candidate_list_manager = CandidateCampaignListManager()
    position_list_manager = PositionListManager()
    we_vote_election_candidate_list = []
    we_vote_election_office_list = []
    google_civic_election_found = False
    we_vote_election_office_count = 0
    we_vote_election_ballot_item_count = 0
    we_vote_election_ballot_returned_count = 0
    we_vote_election_candidate_count = 0
    error = False
    status = ""

    results = election_manager.retrieve_we_vote_elections()
    we_vote_election_list = results['election_list']
    state_code_list = []
    for election in we_vote_election_list:
        if election.state_code not in state_code_list:
            state_code_list.append(election.state_code)

    google_civic_election = Election()
    results = election_manager.retrieve_google_civic_elections_in_state_list(state_code_list)
    google_civic_election_list = results['election_list']

    # Find the election using an internal election_id (greater than 1,000,000)
    we_vote_election_id = convert_to_int(request.GET.get('we_vote_election_id', 0))
    if not positive_value_exists(we_vote_election_id):
        we_vote_election_id = convert_to_int(request.POST.get('we_vote_election_id', 0))
    if positive_value_exists(we_vote_election_id):
        results = election_manager.retrieve_election(we_vote_election_id)
        if results['election_found']:
            we_vote_election = results['election']
            we_vote_election_found = True

    # Find the google_civic election we want to migrate all data over to
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    if not positive_value_exists(google_civic_election_id):
        google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    if positive_value_exists(google_civic_election_id):
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            google_civic_election = results['election']
            google_civic_election_found = True

    # Do we want to actually migrate the election ids?
    change_now = request.POST.get('change_now', False)

    if not positive_value_exists(we_vote_election_found) \
            or not positive_value_exists(google_civic_election_found):
        # If we don't have both elections, break out
        template_values = {
            'change_now':                       change_now,
            'google_civic_election':            google_civic_election,
            'google_civic_election_id':         google_civic_election_id,
            'google_civic_election_list':       google_civic_election_list,
            'messages_on_stage':                messages_on_stage,
            'we_vote_election':                 we_vote_election,
            'we_vote_election_id':              we_vote_election_id,
            'we_vote_election_list':            we_vote_election_list,
            'we_vote_election_candidate_list':  we_vote_election_candidate_list,
            'we_vote_election_office_list':     we_vote_election_office_list,
        }

        return render(request, 'election/election_migration.html', template_values)

    # ########################################
    # Analytics Action
    analytics_action_manager = AnalyticsManager()
    analytics_action_results = analytics_action_manager.retrieve_analytics_action_list('', we_vote_election_id)
    we_vote_election_analytics_action_count = 0
    if analytics_action_results['analytics_action_list_found']:
        we_vote_election_analytics_action_list = analytics_action_results['analytics_action_list']
        we_vote_election_analytics_action_count = len(we_vote_election_analytics_action_list)

        if positive_value_exists(change_now):
            try:
                for one_analytics_action in we_vote_election_analytics_action_list:
                    one_analytics_action.google_civic_election_id = google_civic_election_id
                    one_analytics_action.save()
            except Exception as e:
                error = True
                status += analytics_action_results['status']

    # ########################################
    # Organization Election Metrics
    organization_election_metrics_results = analytics_action_manager.retrieve_organization_election_metrics_list(
        we_vote_election_id)
    we_vote_election_organization_election_metrics_count = 0
    if organization_election_metrics_results['organization_election_metrics_list_found']:
        we_vote_election_organization_election_metrics_list = \
            organization_election_metrics_results['organization_election_metrics_list']
        we_vote_election_organization_election_metrics_count = len(we_vote_election_organization_election_metrics_list)

        if positive_value_exists(change_now):
            try:
                for one_organization_election_metrics in we_vote_election_organization_election_metrics_list:
                    one_organization_election_metrics.google_civic_election_id = google_civic_election_id
                    one_organization_election_metrics.save()
            except Exception as e:
                error = True
                status += organization_election_metrics_results['status']

    # ########################################
    # Sitewide Election Metrics
    sitewide_election_metrics_results = analytics_action_manager.retrieve_sitewide_election_metrics_list(
        we_vote_election_id)
    we_vote_election_sitewide_election_metrics_count = 0
    if sitewide_election_metrics_results['sitewide_election_metrics_list_found']:
        we_vote_election_sitewide_election_metrics_list = \
            sitewide_election_metrics_results['sitewide_election_metrics_list']
        we_vote_election_sitewide_election_metrics_count = len(we_vote_election_sitewide_election_metrics_list)

        if positive_value_exists(change_now):
            try:
                for one_sitewide_election_metrics in we_vote_election_sitewide_election_metrics_list:
                    one_sitewide_election_metrics.google_civic_election_id = google_civic_election_id
                    one_sitewide_election_metrics.save()
            except Exception as e:
                error = True
                status += sitewide_election_metrics_results['status']

    # ########################################
    # Ballot Items
    ballot_item_list_manager = BallotItemListManager()
    ballot_item_results = ballot_item_list_manager.retrieve_ballot_items_for_election(we_vote_election_id)
    if ballot_item_results['ballot_item_list_found']:
        we_vote_election_ballot_item_list = ballot_item_results['ballot_item_list']
        we_vote_election_ballot_item_count = len(we_vote_election_ballot_item_list)

        if positive_value_exists(change_now):
            try:
                for one_ballot_item in we_vote_election_ballot_item_list:
                    one_ballot_item.google_civic_election_id = google_civic_election_id
                    one_ballot_item.save()
            except Exception as e:
                error = True
                status += ballot_item_results['status']

    # ########################################
    # Ballot Returned
    ballot_returned_list_manager = BallotReturnedListManager()
    ballot_returned_results = ballot_returned_list_manager.retrieve_ballot_returned_list_for_election(
        we_vote_election_id)
    if ballot_returned_results['ballot_returned_list_found']:
        we_vote_election_ballot_returned_list = ballot_returned_results['ballot_returned_list']
        we_vote_election_ballot_returned_count = len(we_vote_election_ballot_returned_list)

        if positive_value_exists(change_now):
            try:
                for one_ballot_returned in we_vote_election_ballot_returned_list:
                    one_ballot_returned.google_civic_election_id = google_civic_election_id
                    one_ballot_returned.save()
            except Exception as e:
                error = True
                status += ballot_returned_results['status']

    # ########################################
    # Candidates
    state_code = ""
    return_list_of_objects = True
    candidate_results = candidate_list_manager.retrieve_all_candidates_for_upcoming_election(
        we_vote_election_id, state_code, return_list_of_objects)
    if candidate_results['candidate_list_found']:
        we_vote_election_candidate_list = candidate_results['candidate_list_objects']
        we_vote_election_candidate_count = len(we_vote_election_candidate_list)

        if positive_value_exists(change_now):
            try:
                for one_candidate in we_vote_election_candidate_list:
                    one_candidate.google_civic_election_id = google_civic_election_id
                    one_candidate.save()
            except Exception as e:
                error = True
                status += candidate_results['status']

    # ########################################
    # Measures
    measure_manager = ContestMeasureList()
    state_code = ''
    return_list_of_objects = True
    limit = 0
    measure_results = measure_manager.retrieve_all_measures_for_upcoming_election(we_vote_election_id,
                                                                                  state_code,
                                                                                  return_list_of_objects, limit)
    we_vote_election_measure_count = 0
    if measure_results['measure_list_found']:
        we_vote_election_measure_list = measure_results['measure_list_objects']
        we_vote_election_measure_count = len(we_vote_election_measure_list)

        if positive_value_exists(change_now):
            try:
                for one_measure in we_vote_election_measure_list:
                    one_measure.google_civic_election_id = google_civic_election_id
                    one_measure.save()
            except Exception as e:
                error = True
                status += measure_results['status']

    # ########################################
    # Offices
    state_code = ""
    office_list = []
    return_list_of_objects = True
    results = office_list_manager.retrieve_offices(we_vote_election_id, state_code, office_list,
                                                   return_list_of_objects)

    if results['office_list_found']:
        we_vote_election_office_list = results['office_list_objects']
        we_vote_election_office_count = len(we_vote_election_office_list)

        if positive_value_exists(change_now):
            try:
                for one_office in we_vote_election_office_list:
                    # Save the election_id we want to migrate to
                    one_office.google_civic_election_id = google_civic_election_id
                    one_office.save()
            except Exception as e:
                error = True
                status += results['status']

    # ########################################
    # Pledge to Vote
    pledge_to_vote_manager = PledgeToVoteManager()
    results = pledge_to_vote_manager.retrieve_pledge_to_vote_list(we_vote_election_id)
    we_vote_election_pledge_to_vote_count = 0
    if results['pledge_to_vote_list_found']:
        we_vote_election_pledge_to_vote_list = results['pledge_to_vote_list']
        we_vote_election_pledge_to_vote_count = len(we_vote_election_pledge_to_vote_list)

        if positive_value_exists(change_now):
            try:
                for one_pledge_to_vote in we_vote_election_pledge_to_vote_list:
                    # Save the election_id we want to migrate to
                    one_pledge_to_vote.google_civic_election_id = google_civic_election_id
                    one_pledge_to_vote.save()
            except Exception as e:
                error = True
                status += results['status']

    # ########################################
    # Positions

    # retrieve public positions
    stance_we_are_looking_for = ANY_STANCE
    retrieve_public_positions = True
    # This function returns a list, not a results dict
    public_position_list = position_list_manager.retrieve_all_positions_for_election(
        we_vote_election_id, stance_we_are_looking_for, retrieve_public_positions)
    public_position_count = len(public_position_list)

    if positive_value_exists(change_now):
        for one_position in public_position_list:
            try:
                one_position.google_civic_election_id = google_civic_election_id
                one_position.save()
            except Exception as e:
                error = True

    # retrieve friends-only positions
    stance_we_are_looking_for = ANY_STANCE
    retrieve_friend_positions = False
    # This function returns a list, not a results dict
    friends_position_list = position_list_manager.retrieve_all_positions_for_election(
        we_vote_election_id, stance_we_are_looking_for, retrieve_friend_positions)
    friend_position_count = len(friends_position_list)

    if positive_value_exists(change_now):
        for one_position in friends_position_list:
            try:
                one_position.google_civic_election_id = google_civic_election_id
                one_position.save()
            except Exception as e:
                error = True

    # ########################################
    # Quick Info
    quick_info_manager = QuickInfoManager()
    quick_info_results = quick_info_manager.retrieve_quick_info_list(we_vote_election_id)
    we_vote_election_quick_info_count = 0
    if quick_info_results['quick_info_list_found']:
        we_vote_election_quick_info_list = quick_info_results['quick_info_list']
        we_vote_election_quick_info_count = len(we_vote_election_quick_info_list)

        if positive_value_exists(change_now):
            try:
                for one_quick_info in we_vote_election_quick_info_list:
                    one_quick_info.google_civic_election_id = google_civic_election_id
                    one_quick_info.save()
            except Exception as e:
                error = True
                status += quick_info_results['status']

    # ########################################
    # Remote Request History
    remote_request_history_manager = RemoteRequestHistoryManager()
    remote_request_history_results = remote_request_history_manager.retrieve_remote_request_history_list(
        we_vote_election_id)
    we_vote_election_remote_request_history_count = 0
    if remote_request_history_results['remote_request_history_list_found']:
        we_vote_election_remote_request_history_list = remote_request_history_results['remote_request_history_list']
        we_vote_election_remote_request_history_count = len(we_vote_election_remote_request_history_list)

        if positive_value_exists(change_now):
            try:
                for one_remote_request_history in we_vote_election_remote_request_history_list:
                    one_remote_request_history.google_civic_election_id = google_civic_election_id
                    one_remote_request_history.save()
            except Exception as e:
                error = True
                status += remote_request_history_results['status']

    # ########################################
    # Voter Address
    voter_address_manager = VoterAddressManager()
    voter_address_results = voter_address_manager.retrieve_voter_address_list(we_vote_election_id)
    we_vote_election_voter_address_count = 0
    if voter_address_results['voter_address_list_found']:
        we_vote_election_voter_address_list = voter_address_results['voter_address_list']
        we_vote_election_voter_address_count = len(we_vote_election_voter_address_list)

        if positive_value_exists(change_now):
            try:
                for one_voter_address in we_vote_election_voter_address_list:
                    one_voter_address.google_civic_election_id = google_civic_election_id
                    one_voter_address.save()
            except Exception as e:
                error = True
                status += voter_address_results['status']

    # ########################################
    # Voter Ballot Saved
    voter_ballot_saved_manager = VoterBallotSavedManager()
    voter_ballot_saved_results = voter_ballot_saved_manager.retrieve_voter_ballot_saved_list_for_election(
        we_vote_election_id)
    we_vote_election_voter_ballot_saved_count = 0
    if voter_ballot_saved_results['voter_ballot_saved_list_found']:
        we_vote_election_voter_ballot_saved_list = voter_ballot_saved_results['voter_ballot_saved_list']
        we_vote_election_voter_ballot_saved_count = len(we_vote_election_voter_ballot_saved_list)

        if positive_value_exists(change_now):
            try:
                for one_voter_ballot_saved in we_vote_election_voter_ballot_saved_list:
                    one_voter_ballot_saved.google_civic_election_id = google_civic_election_id
                    one_voter_ballot_saved.election_description_text = google_civic_election.election_name
                    one_voter_ballot_saved.save()
            except Exception as e:
                error = True
                status += voter_ballot_saved_results['status']
                status += "ELECTION_MIGRATION-EXCEPTION_SAVING_VOTER_BALLOT_SAVED, e: " + str(e) + " "

    # ########################################
    # Voter Device Link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link_list(
        we_vote_election_id)
    we_vote_election_voter_device_link_count = 0
    if voter_device_link_results['voter_device_link_list_found']:
        we_vote_election_voter_device_link_list = voter_device_link_results['voter_device_link_list']
        we_vote_election_voter_device_link_count = len(we_vote_election_voter_device_link_list)

        if positive_value_exists(change_now):
            try:
                for one_voter_device_link in we_vote_election_voter_device_link_list:
                    one_voter_device_link.google_civic_election_id = google_civic_election_id
                    one_voter_device_link.save()
            except Exception as e:
                error = True
                status += voter_device_link_results['status']

    # ########################################
    # Voter Guides
    voter_guide_manager = VoterGuideListManager()
    voter_guide_results = voter_guide_manager.retrieve_voter_guides_for_election(we_vote_election_id)
    we_vote_election_voter_guide_count = 0
    if voter_guide_results['voter_guide_list_found']:
        we_vote_election_voter_guide_list = voter_guide_results['voter_guide_list']
        we_vote_election_voter_guide_count = len(we_vote_election_voter_guide_list)

        if positive_value_exists(change_now):
            try:
                for one_voter_guide in we_vote_election_voter_guide_list:
                    one_voter_guide.google_civic_election_id = google_civic_election_id
                    one_voter_guide.save()
            except Exception as e:
                error = True
                status += voter_guide_results['status']

    # ########################################
    # We Vote Images
    we_vote_image_manager = WeVoteImageManager()
    we_vote_image_results = we_vote_image_manager.retrieve_we_vote_image_list_from_google_civic_election_id(
        we_vote_election_id)
    we_vote_election_we_vote_image_count = 0
    if we_vote_image_results['we_vote_image_list_found']:
        we_vote_election_we_vote_image_list = we_vote_image_results['we_vote_image_list']
        we_vote_election_we_vote_image_count = len(we_vote_election_we_vote_image_list)

        if positive_value_exists(change_now):
            try:
                for one_we_vote_image in we_vote_election_we_vote_image_list:
                    one_we_vote_image.google_civic_election_id = google_civic_election_id
                    one_we_vote_image.save()
            except Exception as e:
                error = True
                status += we_vote_image_results['status']

    # ########################################
    # PositionNetworkScore
    position_network_score_results = position_list_manager.migrate_position_network_scores_to_new_election_id(
        we_vote_election_id, google_civic_election_id, change_now)
    position_network_scores_migrated = position_network_score_results['position_network_scores_migrated']
    if not position_network_score_results['success']:
        status += position_network_score_results['status']

    message_with_summary_of_elections = 'Election Migration from We Vote Election id {we_vote_election_id} ' \
                                        'to Google Civic Election id {google_civic_election_id}. ' \
                                        ''.format(we_vote_election_id=we_vote_election_id,
                                                  google_civic_election_id=google_civic_election_id)

    if positive_value_exists(change_now):
        info_message = message_with_summary_of_elections + '<br />Changes completed.<br />' \
                         'status: {status} '.format(status=status, )

        messages.add_message(request, messages.INFO, info_message)
    elif error:
        error_message = 'There was an error migrating data.<br />' \
                         'status: {status} '.format(status=status, )

        messages.add_message(request, messages.ERROR, error_message)
    else:

        current_counts = '\'from\' counts: <br />' \
                         'office_count: {office_count}, <br />' \
                         'candidate_count: {candidate_count}, <br />' \
                         'public_position_count: {public_position_count}, <br />' \
                         'friend_position_count: {friend_position_count}, <br />' \
                         'analytics_action_count: {analytics_action_count}, <br />' \
                         'organization_election_metrics_count: {organization_election_metrics_count}, <br />' \
                         'sitewide_election_metrics_count: {sitewide_election_metrics_count}, <br />' \
                         'ballot_item_count: {ballot_item_count}, <br />' \
                         'ballot_returned_count: {ballot_returned_count}, <br />' \
                         'voter_ballot_saved_count: {voter_ballot_saved_count}, <br />' \
                         'we_vote_image_count: {we_vote_image_count}, <br />' \
                         'measure_count: {measure_count}, <br />' \
                         'pledge_to_vote_count: {pledge_to_vote_count}, <br />' \
                         'quick_info_count: {quick_info_count}, <br />' \
                         'remote_request_history_count: {remote_request_history_count}, <br />' \
                         'voter_address_count: {voter_address_count}, <br />' \
                         'voter_device_link_count: {voter_device_link_count}, <br />' \
                         'voter_guide_count: {voter_guide_count}, <br />' \
                         'position_network_scores_count: {position_network_scores_migrated}, <br />' \
                         'status: {status} '.format(
                             we_vote_election_id=we_vote_election_id,
                             google_civic_election_id=google_civic_election_id,
                             office_count=we_vote_election_office_count,
                             candidate_count=we_vote_election_candidate_count,
                             public_position_count=public_position_count,
                             friend_position_count=friend_position_count,
                             analytics_action_count=we_vote_election_analytics_action_count,
                             pledge_to_vote_count=we_vote_election_pledge_to_vote_count,
                             organization_election_metrics_count=we_vote_election_organization_election_metrics_count,
                             sitewide_election_metrics_count=we_vote_election_sitewide_election_metrics_count,
                             ballot_item_count=we_vote_election_ballot_item_count,
                             ballot_returned_count=we_vote_election_ballot_returned_count,
                             voter_ballot_saved_count=we_vote_election_voter_ballot_saved_count,
                             we_vote_image_count=we_vote_election_we_vote_image_count,
                             measure_count=we_vote_election_measure_count,
                             quick_info_count=we_vote_election_quick_info_count,
                             remote_request_history_count=we_vote_election_remote_request_history_count,
                             voter_address_count=we_vote_election_voter_address_count,
                             voter_device_link_count=we_vote_election_voter_device_link_count,
                             voter_guide_count=we_vote_election_voter_guide_count,
                             position_network_scores_migrated=position_network_scores_migrated,
                             status=status,)

        info_message = message_with_summary_of_elections + current_counts

        messages.add_message(request, messages.INFO, info_message)

    template_values = {
        'change_now':                           change_now,
        'google_civic_election':                google_civic_election,
        'google_civic_election_id':             google_civic_election_id,
        'google_civic_election_list':           google_civic_election_list,
        'messages_on_stage':                    messages_on_stage,
        'we_vote_election':                     we_vote_election,
        'we_vote_election_id':                  we_vote_election_id,
        'we_vote_election_list':                we_vote_election_list,
        'we_vote_election_candidate_list':      we_vote_election_candidate_list,
        'we_vote_election_office_list':         we_vote_election_office_list,
    }

    return render(request, 'election/election_migration.html', template_values)
