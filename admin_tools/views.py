# admin_tools/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.controllers import candidates_import_from_sample_file
from config.base import get_environment_variable, LOGIN_URL
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from election.models import Election
from election.controllers import elections_import_from_sample_file
from import_export_google_civic.models import GoogleCivicApiCounterManager
from import_export_vote_smart.models import VoteSmartApiCounterManager
from office.controllers import offices_import_from_sample_file
from organization.controllers import organizations_import_from_sample_file
from polling_location.controllers import import_and_save_all_polling_locations_data
from position.controllers import positions_import_from_sample_file
from voter.models import Voter, VoterDeviceLinkManager, VoterManager, voter_has_authority, voter_setup
from wevote_functions.functions import delete_voter_api_device_id_cookie, generate_voter_device_id, \
    get_voter_api_device_id, positive_value_exists, set_voter_api_device_id

BALLOT_ITEMS_SYNC_URL = get_environment_variable("BALLOT_ITEMS_SYNC_URL")
BALLOT_RETURNED_SYNC_URL = get_environment_variable("BALLOT_RETURNED_SYNC_URL")
ELECTIONS_SYNC_URL = get_environment_variable("ELECTIONS_SYNC_URL")
ORGANIZATIONS_SYNC_URL = get_environment_variable("ORGANIZATIONS_SYNC_URL")
OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")
CANDIDATES_SYNC_URL = get_environment_variable("CANDIDATES_SYNC_URL")
MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")
POLLING_LOCATIONS_SYNC_URL = get_environment_variable("POLLING_LOCATIONS_SYNC_URL")
POSITIONS_SYNC_URL = get_environment_variable("POSITIONS_SYNC_URL")
VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")


@login_required
def admin_home_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # Create a voter_device_id and voter in the database if one doesn't exist yet
    results = voter_setup(request)
    voter_api_device_id = results['voter_api_device_id']
    store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']
    template_values = {
    }
    response = render(request, 'admin_tools/index.html', template_values)

    # We want to store the voter_api_device_id cookie if it is new
    if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


@login_required
def import_sample_data_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # This routine works without requiring a Google Civic API key

    # We want to make sure that all voters have been updated to have a we_vote_id
    voter_list = Voter.objects.all()
    for one_voter in voter_list:
        one_voter.save()

    polling_locations_results = import_and_save_all_polling_locations_data()

    # NOTE: The approach of having each developer pull directly from Google Civic won't work because if we are going
    # to import positions, we need to have stable we_vote_ids for all ballot items
    # =========================
    # # We redirect to the view that calls out to Google Civic and brings in ballot data
    # # This isn't ideal (I'd rather call a controller instead of redirecting to a view), but this is a unique case
    # # and we have a lot of error-display-to-screen code
    # election_local_id = 0
    # google_civic_election_id = 4162  # Virginia
    # return HttpResponseRedirect(reverse('election:election_all_ballots_retrieve',
    #                                     args=(election_local_id,)) +
    #                             "?google_civic_election_id=" + str(google_civic_election_id))

    # Import election data from We Vote export file
    elections_results = elections_import_from_sample_file()

    # Import ContestOffices
    load_from_uri = False
    offices_results = offices_import_from_sample_file(request, load_from_uri)

    # Import candidate data from We Vote export file
    load_from_uri = False
    candidates_results = candidates_import_from_sample_file(request, load_from_uri)

    # Import ContestMeasures

    # Import organization data from We Vote export file
    load_from_uri = False
    organizations_results = organizations_import_from_sample_file(request, load_from_uri)

    # Import positions data from We Vote export file
    # load_from_uri = False
    positions_results = positions_import_from_sample_file(request)  # , load_from_uri

    messages.add_message(request, messages.INFO,
                         'The following data has been imported: <br />'
                         'Polling locations saved: {polling_locations_saved}, updated: {polling_locations_updated},'
                         ' not_processed: {polling_locations_not_processed} <br />'
                         'Elections saved: {elections_saved}, updated: {elections_updated},'
                         ' not_processed: {elections_not_processed} <br />'
                         'Offices saved: {offices_saved}, updated: {offices_updated},'
                         ' not_processed: {offices_not_processed} <br />'
                         'Candidates saved: {candidates_saved}, updated: {candidates_updated},'
                         ' not_processed: {candidates_not_processed} <br />'
                         'Organizations saved: {organizations_saved}, updated: {organizations_updated},'
                         ' not_processed: {organizations_not_processed} <br />'
                         'Positions saved: {positions_saved}, updated: {positions_updated},'
                         ' not_processed: {positions_not_processed} <br />'
                         ''.format(
                             polling_locations_saved=polling_locations_results['saved'],
                             polling_locations_updated=polling_locations_results['updated'],
                             polling_locations_not_processed=polling_locations_results['not_processed'],
                             elections_saved=elections_results['saved'],
                             elections_updated=elections_results['updated'],
                             elections_not_processed=elections_results['not_processed'],
                             offices_saved=offices_results['saved'],
                             offices_updated=offices_results['updated'],
                             offices_not_processed=offices_results['not_processed'],
                             candidates_saved=candidates_results['saved'],
                             candidates_updated=candidates_results['updated'],
                             candidates_not_processed=candidates_results['not_processed'],
                             organizations_saved=organizations_results['saved'],
                             organizations_updated=organizations_results['updated'],
                             organizations_not_processed=organizations_results['not_processed'],
                             positions_saved=positions_results['saved'],
                             positions_updated=positions_results['updated'],
                             positions_not_processed=positions_results['not_processed'],
                         ))
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


@login_required
def delete_test_data_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We leave in place the polling locations data and the election data from Google civic

    # Delete candidate data from exported file

    # Delete organization data from exported file

    # Delete positions data from exported file
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


def login_user(request):
    """
    This method is called when you login from the /login/ form
    :param request:
    :return:
    """
    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    store_new_voter_api_device_id_in_cookie = False
    voter_signed_in = False

    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id)
    if results['voter_found']:
        voter_on_stage = results['voter']
        voter_on_stage_id = voter_on_stage.id
        # Just because a We Vote voter is found doesn't mean they are authenticated for Django
    else:
        voter_on_stage_id = 0

    info_message = ''
    error_message = ''
    username = ''

    # Does Django think user is already signed in?
    if request.user.is_authenticated():
        # If so, make sure user and voter_on_stage are the same.
        if request.user.id != voter_on_stage_id:
            # Delete the prior voter_api_device_id from database
            voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

            # Create a new voter_api_device_id and voter_device_link
            voter_api_device_id = generate_voter_device_id()
            results = voter_device_link_manager.save_new_voter_device_link(voter_api_device_id, request.user.id)
            store_new_voter_api_device_id_in_cookie = results['voter_device_link_created']
            voter_on_stage = request.user
            voter_on_stage_id = voter_on_stage.id
    elif request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                info_message = "You're successfully logged in!"

                # Delete the prior voter_api_device_id from database
                voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

                # Create a new voter_api_device_id and voter_device_link
                voter_api_device_id = generate_voter_device_id()
                results = voter_device_link_manager.save_new_voter_device_link(voter_api_device_id, user.id)
                store_new_voter_api_device_id_in_cookie = results['voter_device_link_created']
            else:
                error_message = "Your account is not active, please contact the site admin."

            if user.id != voter_on_stage_id:
                # Eventually we want to merge voter_on_stage into user account
                pass
        else:
            error_message = "Your username and/or password were incorrect."
    elif not positive_value_exists(voter_on_stage_id):
        # If here, delete the prior voter_api_device_id from database
        voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

        # We then need to set a voter_api_device_id cookie and create a new voter (even though not signed in)
        results = voter_setup(request)
        voter_api_device_id = results['voter_api_device_id']
        store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']

    # Does Django think user is signed in?
    if request.user.is_authenticated():
        voter_signed_in = True
    else:
        info_message = "Please log in below..."

    if positive_value_exists(error_message):
        messages.add_message(request, messages.ERROR, error_message)
    if positive_value_exists(info_message):
        messages.add_message(request, messages.INFO, info_message)

    messages_on_stage = get_messages(request)
    template_values = {
        'request':              request,
        'username':             username,
        'next':                 next,
        'voter_signed_in':      voter_signed_in,
        'messages_on_stage':    messages_on_stage,
    }
    response = render(request, 'registration/login_user.html', template_values)

    # We want to store the voter_api_device_id cookie if it is new
    if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


def logout_user(request):
    logout(request)

    info_message = "You are now signed out."
    messages.add_message(request, messages.INFO, info_message)

    messages_on_stage = get_messages(request)
    template_values = {
        'request':              request,
        'next':                 '/admin/',
        'messages_on_stage':    messages_on_stage,
    }
    response = render(request, 'registration/login_user.html', template_values)

    # Find current voter_api_device_id
    voter_api_device_id = get_voter_api_device_id(request)

    delete_voter_api_device_id_cookie(response)

    # Now delete voter_api_device_id from database
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

    return response


def redirect_to_sign_in_page(request, authority_required={}):
    authority_required_text = ''
    for each_authority in authority_required:
        if each_authority == 'admin':
            authority_required_text += 'or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Admin rights'
        if each_authority == 'verified_volunteer':
            authority_required_text += 'or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Verified Volunteer rights'
    error_message = "You must sign in with account that " \
                    "{authority_required_text} to see that page." \
                    "".format(authority_required_text=authority_required_text)
    messages.add_message(request, messages.ERROR, error_message)

    if positive_value_exists(request.path):
        next_url_variable = '?next=' + request.path
    else:
        next_url_variable = ''
    return HttpResponseRedirect(LOGIN_URL + next_url_variable)


@login_required
def statistics_summary_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_daily_summary_list = google_civic_api_counter_manager.retrieve_daily_summaries()
    vote_smart_api_counter_manager = VoteSmartApiCounterManager()
    vote_smart_daily_summary_list = vote_smart_api_counter_manager.retrieve_daily_summaries()
    template_values = {
        'google_civic_daily_summary_list':  google_civic_daily_summary_list,
        'vote_smart_daily_summary_list':    vote_smart_daily_summary_list,
    }
    response = render(request, 'admin_tools/statistics_summary.html', template_values)

    return response


@login_required
def sync_data_with_master_servers_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', '')

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'election_list':            election_list,
        'google_civic_election_id': google_civic_election_id,

        'ballot_items_sync_url':        BALLOT_ITEMS_SYNC_URL,
        'ballot_returned_sync_url':     BALLOT_RETURNED_SYNC_URL,
        'candidates_sync_url':          CANDIDATES_SYNC_URL,
        'elections_sync_url':           ELECTIONS_SYNC_URL,
        'measures_sync_url':            MEASURES_SYNC_URL,
        'offices_sync_url':             OFFICES_SYNC_URL,
        'organizations_sync_url':       ORGANIZATIONS_SYNC_URL,
        'polling_locations_sync_url':   POLLING_LOCATIONS_SYNC_URL,
        'positions_sync_url':           POSITIONS_SYNC_URL,
        'voter_guides_sync_url':        VOTER_GUIDES_SYNC_URL,
    }
    response = render(request, 'admin_tools/sync_data_with_master_dashboard.html', template_values)

    return response
