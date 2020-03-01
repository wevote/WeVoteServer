# import_export_ballotpedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import attach_ballotpedia_election_by_district_from_api, \
    retrieve_ballot_items_for_one_voter_api_v4, \
    retrieve_ballot_items_from_polling_location, retrieve_ballot_items_from_polling_location_api_v4, \
    retrieve_ballotpedia_candidates_by_district_from_api, retrieve_ballotpedia_measures_by_district_from_api, \
    retrieve_ballotpedia_district_id_list_for_polling_location, retrieve_ballotpedia_offices_by_district_from_api
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager
from config.base import get_environment_variable
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.urls import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from election.models import Election, ElectionManager
from import_export_batches.controllers_batch_process import \
    schedule_retrieve_ballotpedia_ballots_for_polling_locations_api_v4, \
    schedule_refresh_ballotpedia_ballots_for_voters_api_v4
from import_export_batches.models import BatchSet, BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS
from polling_location.models import PollingLocation
import random
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_valid_state_code, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

BALLOTPEDIA_API_CONTAINS_URL = get_environment_variable("BALLOTPEDIA_API_CONTAINS_URL")
BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL = "https://api4.ballotpedia.org/sample_ballot_results"

CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
ELECTED_OFFICE = 'ELECTED_OFFICE'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'


@login_required
def import_ballot_items_for_location_view(request):
    """
    Reach out to Ballotpedia API to retrieve a short list of districts the voter can vote in.
    """
    status = ""
    success = True

    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', "")

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR,
                             'Google Civic Election Id missing.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    election_manager = ElectionManager()
    election_day_text = ""
    results = election_manager.retrieve_election(google_civic_election_id=google_civic_election_id)
    if results['election_found']:
        election = results['election']
        election_day_text = election.election_day_text

    results = retrieve_ballot_items_from_polling_location_api_v4(
        google_civic_election_id,
        election_day_text=election_day_text,
        polling_location_we_vote_id=polling_location_we_vote_id,
        state_code=state_code,
    )

    kind_of_batch = ""
    if 'kind_of_batch' in results:
        kind_of_batch = results['kind_of_batch']
    if not positive_value_exists(kind_of_batch):
        kind_of_batch = IMPORT_BALLOT_ITEM

    batch_header_id = 0
    if 'batch_saved' in results and results['batch_saved']:
        messages.add_message(request, messages.INFO, 'Ballot items import batch for {google_civic_election_id} '
                                                     'election saved.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    elif 'batch_header_id' in results and results['batch_header_id']:
        messages.add_message(request, messages.INFO, 'Ballot items import batch for {google_civic_election_id} '
                                                     'election saved, batch_header_id.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    if positive_value_exists(batch_header_id):
        # Go straight to the new batch
        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    "?batch_header_id=" + str(batch_header_id) +
                                    "&kind_of_batch=" + str(kind_of_batch) +
                                    "&google_civic_election_id=" + str(google_civic_election_id))
    else:
        # Go to the ballot_item_list_edit page
        if positive_value_exists(polling_location_we_vote_id):
            return HttpResponseRedirect(reverse('ballot:ballot_item_list_by_polling_location_edit',
                                                args=(polling_location_we_vote_id,)) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&state_code=" + str(state_code)
                                        )
        else:
            messages.add_message(request, messages.ERROR, "Missing polling_location_we_vote_id.")
            return HttpResponseRedirect(reverse('election:election_list', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&polling_location_we_vote_id=" + str(polling_location_we_vote_id) +
                                        "&state_code=" + str(state_code)
                                        )


@login_required
def import_export_ballotpedia_index_view(request):
    """
    Provide an index of import/export actions (for We Vote data maintenance)
    """
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':    messages_on_stage,
    }
    return render(request, 'import_export_ballotpedia/index.html', template_values)


@login_required
def attach_ballotpedia_election_view(request, election_local_id=0):
    """
    Reach out to Ballotpedia and retrieve the details about this election needed to make other API calls.
    :param request:
    :param election_local_id:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    force_district_retrieve_from_ballotpedia = request.GET.get('force_district_retrieve_from_ballotpedia', False)
    polling_location_list = []
    status = ""

    try:
        election_on_stage = Election.objects.get(id=election_local_id)
        google_civic_election_id = election_on_stage.google_civic_election_id
        election_state_code = election_on_stage.get_election_state()
        election_name = election_on_stage.election_name
        is_national_election = election_on_stage.is_national_election
    except Election.MultipleObjectsReturned as e:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve election data. More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve election data. Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR,
                             'For National elections, a State Code is required in order to run any '
                             'Ballotpedia data preparation.')
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if not is_valid_state_code(state_code):
        messages.add_message(request, messages.ERROR,
                             '{state_code} is not a valid State Code'.format(state_code=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
        polling_location_count_query = polling_location_count_query.exclude(
            Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_count_query = polling_location_count_query.exclude(
            Q(zip_long__isnull=True) | Q(zip_long__exact='0') | Q(zip_long__exact=''))
        polling_location_count = polling_location_count_query.count()

        if positive_value_exists(polling_location_count):
            polling_location_limited_count = 1000

            polling_location_query = PollingLocation.objects.all()
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            polling_location_query = polling_location_query.exclude(
                Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            polling_location_query = polling_location_query.exclude(
                Q(zip_long__isnull=True) | Q(zip_long__exact='0') | Q(zip_long__exact=''))
            # Ordering by "line1" creates a bit of (locational) random order
            polling_location_list = polling_location_query.order_by('line1')[:polling_location_limited_count]
    except PollingLocation.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Could not retrieve polling location data for the {election_name}. '
                             'No polling locations exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                    "?state_code=" + str(state_code))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations returned for the state \'{state}\'. '
                             '(error 2 - attach_ballotpedia_election_view)'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                    "?state_code=" + str(state_code))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    could_not_retrieve_district_id_list_for_polling_location_count = 0
    merged_district_list = []
    for polling_location in polling_location_list:
        one_ballot_results = retrieve_ballotpedia_district_id_list_for_polling_location(
            google_civic_election_id, polling_location=polling_location,
            force_district_retrieve_from_ballotpedia=force_district_retrieve_from_ballotpedia)
        if one_ballot_results['success']:
            ballotpedia_district_id_list = one_ballot_results['ballotpedia_district_id_list']
            if len(ballotpedia_district_id_list):
                for one_ballotpedia_district_id in ballotpedia_district_id_list:
                    if one_ballotpedia_district_id not in merged_district_list:
                        # Build up a list of ballotpedia districts that we need to retrieve races for
                        merged_district_list.append(one_ballotpedia_district_id)
        else:
            could_not_retrieve_district_id_list_for_polling_location_count += 1

    if positive_value_exists(could_not_retrieve_district_id_list_for_polling_location_count):
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve district_id list for this many Polling Locations: ' +
                             str(could_not_retrieve_district_id_list_for_polling_location_count))

    # Once we have a summary of all ballotpedia districts, we want to request all of the races
    if not len(merged_district_list):
        messages.add_message(request, messages.ERROR,
                             'Could not find Ballotpedia districts. ')
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    results = attach_ballotpedia_election_by_district_from_api(election_on_stage, google_civic_election_id,
                                                               merged_district_list, state_code)

    status += results['status']
    status = status[:1000]
    if positive_value_exists(results['election_found']):
        messages.add_message(request, messages.INFO,
                             'Ballotpedia election information attached. status: {status} '.format(status=status))
    else:
        # We limit the number of status characters we print to the screen to 2000 so we don't get
        # the error "Not all temporary messages could be stored."
        messages.add_message(request, messages.ERROR,
                             'Ballotpedia election information not attached. status: {status} '
                             .format(status=status))
    return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code))


@login_required
def refresh_ballotpedia_districts_for_polling_locations_view(request):
    """
    This function refreshes the Ballotpedia districts used with subsequent calls to Ballotpedia:
    1) Retrieve (internally) polling locations (so we can use those addresses to retrieve a
    representative set of ballots)
    2) Cycle through a portion of those polling locations, enough that we are caching all of the possible ballot items
    3) Ask for Ballotpedia districts for each of the polling locations being analyzed
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    # This is 500 because we're looking for districts
    import_limit = convert_to_int(request.GET.get('import_limit', 500))

    polling_location_list = []
    polling_location_count = 0
    status = ""

    if not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve Ballotpedia data. Missing state_code.')
        return HttpResponseRedirect(reverse('electoral_district:electoral_district_list', args=()))

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
        polling_location_count = polling_location_count_query.count()

        if positive_value_exists(polling_location_count):
            polling_location_query = PollingLocation.objects.all()
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            polling_location_query = polling_location_query.filter(use_for_bulk_retrieve=True)
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            # We used to have a limit of 500 ballots to pull per election, but now retrieve all
            # Ordering by "line1" creates a bit of (locational) random order
            polling_location_list = polling_location_query.order_by('line1')[:import_limit]
    except Exception as e:
        status += "ELECTORAL_DISTRICT-COULD_NOT_FIND_POLLING_LOCATION_LIST " + str(e) + " "

    if polling_location_count == 0:
        # We didn't find any polling locations marked for bulk retrieve, so just retrieve up to the import_limit
        try:
            polling_location_count_query = PollingLocation.objects.all()
            polling_location_count_query = \
                polling_location_count_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            polling_location_count_query = \
                polling_location_count_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                                     Q(zip_long__exact=''))
            polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
            polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
            polling_location_count = polling_location_count_query.count()

            if positive_value_exists(polling_location_count):
                polling_location_query = PollingLocation.objects.all()
                polling_location_query = \
                    polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
                polling_location_query = \
                    polling_location_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                                   Q(zip_long__exact=''))
                polling_location_query = polling_location_query.filter(state__iexact=state_code)
                polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
                # Ordering by "line1" creates a bit of (locational) random order
                polling_location_list = polling_location_query.order_by('line1')[:import_limit]
        except PollingLocation.DoesNotExist:
            messages.add_message(request, messages.INFO,
                                 'Could not retrieve ballot data. '
                                 'No polling locations exist for the state \'{state}\'. '
                                 'Data needed from VIP.'.format(
                                     state=state_code))
            return HttpResponseRedirect(reverse('electoral_district:electoral_district_list', args=()))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data. '
                             'No polling locations returned for the state \'{state}\'. '
                             '(error 2 - refresh_ballotpedia_districts_for_polling_locations_view)'.format(
                                 state=state_code))
        return HttpResponseRedirect(reverse('electoral_district:electoral_district_list', args=()))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts

    # Step though our set of polling locations, until we find one that contains a ballot.  Some won't contain ballots
    # due to data quality issues.
    polling_locations_with_data = 0
    polling_locations_without_data = 0
    # If here we just want to retrieve the races for this election
    merged_district_list = []
    google_civic_election_id = 0
    force_district_retrieve_from_ballotpedia = True
    for polling_location in polling_location_list:
        one_ballot_results = retrieve_ballotpedia_district_id_list_for_polling_location(
            google_civic_election_id, polling_location=polling_location,
            force_district_retrieve_from_ballotpedia=force_district_retrieve_from_ballotpedia)
        success = False
        if one_ballot_results['success']:
            success = True
            ballotpedia_district_id_list = one_ballot_results['ballotpedia_district_id_list']
            if len(ballotpedia_district_id_list):
                for one_ballotpedia_district_id in ballotpedia_district_id_list:
                    if one_ballotpedia_district_id not in merged_district_list:
                        # Build up a list of ballotpedia districts that we need to retrieve races for
                        merged_district_list.append(one_ballotpedia_district_id)

        if success:
            polling_locations_with_data += 1
        else:
            polling_locations_without_data += 1

    messages.add_message(request, messages.INFO,
                         'Electoral data retrieved from Ballotpedia. '
                         'polling_locations_with_data: {polling_locations_with_data}, '
                         'polling_locations_without_data: {polling_locations_without_data}. '
                         ''.format(
                             polling_locations_with_data=polling_locations_with_data,
                             polling_locations_without_data=polling_locations_without_data))
    return HttpResponseRedirect(reverse('electoral_district:electoral_district_list', args=()) +
                                '?state_code=' + str(state_code) +
                                '&google_civic_election_id=' + str(google_civic_election_id))


@login_required
def retrieve_ballotpedia_candidates_by_district_from_api_view(request):
    """
    Reach out to Ballotpedia API to retrieve candidates.
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    only_retrieve_if_zero_candidates = request.GET.get('only_retrieve_if_zero_candidates', False)
    state_code = request.GET.get('state_code', "")

    election_manager = ElectionManager()
    election_local_id = 0
    is_national_election = False
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        election_local_id = election.id
        is_national_election = election.is_national_election

    if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR,
                             'For National elections, a State Code is required in order to run any '
                             'Ballotpedia data preparation.')

        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    results = retrieve_ballotpedia_candidates_by_district_from_api(google_civic_election_id, state_code,
                                                                   only_retrieve_if_zero_candidates)

    kind_of_batch = ""
    if 'kind_of_batch' in results:
        kind_of_batch = results['kind_of_batch']
    if not positive_value_exists(kind_of_batch):
        kind_of_batch = CANDIDATE

    batch_header_id = 0
    if 'batch_saved' in results and results['batch_saved']:
        messages.add_message(request, messages.INFO, 'Import batch for {google_civic_election_id} election saved.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    elif 'batch_header_id' in results and results['batch_header_id']:
        messages.add_message(request, messages.INFO, 'Import batch for {google_civic_election_id} election saved, '
                                                     'batch_header_id.'
                                                     ''.format(google_civic_election_id=google_civic_election_id))
        batch_header_id = results['batch_header_id']
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    if positive_value_exists(batch_header_id):
        # Go straight to the new batch
        return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                    "?batch_header_id=" + str(batch_header_id) +
                                    "&kind_of_batch=" + str(kind_of_batch) +
                                    "&google_civic_election_id=" + str(google_civic_election_id))
    else:
        # Go to the office listing page
        return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))


@login_required
def retrieve_ballotpedia_ballots_for_polling_locations_api_v4_view(request):
    """
    This is different than retrieve_ballotpedia_data_for_polling_locations_view because it is getting the districts
    from lat/long, and then the ballot items. Ballotpedia API v4
    Reach out to Ballotpedia and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those polling locations, enough that we are caching all of the possible ballot items
    :param request:
    :return:
    """
    status = ""

    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    refresh_ballot_returned = request.GET.get('refresh_ballot_returned', False)
    use_batch_process = request.GET.get('use_batch_process', False)
    # import_limit = convert_to_int(request.GET.get('import_limit', 1000))  # If > 1000, we get error 414 (url too long)

    if positive_value_exists(use_batch_process):
        results = schedule_retrieve_ballotpedia_ballots_for_polling_locations_api_v4(
            google_civic_election_id=google_civic_election_id, state_code=state_code,
            refresh_ballot_returned=refresh_ballot_returned)
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code)
                                    )
    else:
        return retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view(
            request=request, from_browser=True, google_civic_election_id=google_civic_election_id,
            state_code=state_code, refresh_ballot_returned=refresh_ballot_returned)


def retrieve_ballotpedia_ballots_for_polling_locations_api_v4_internal_view(
        request=None, from_browser=False, google_civic_election_id="", state_code="", refresh_ballot_returned=False,
        date_last_updated_should_not_exceed=None):
    status = ""
    success = True

    batch_set_id = 0
    retrieve_row_count = 0

    try:
        if positive_value_exists(google_civic_election_id):
            election_on_stage = Election.objects.using('readonly').get(google_civic_election_id=google_civic_election_id)
            ballotpedia_election_id = election_on_stage.ballotpedia_election_id
            election_day_text = election_on_stage.election_day_text
            election_local_id = election_on_stage.id
            election_state_code = election_on_stage.get_election_state()
            election_name = election_on_stage.election_name
            is_national_election = election_on_stage.is_national_election
        else:
            message = 'Could not retrieve Ballotpedia ballots. Missing google_civic_election_id. '
            if from_browser:
                messages.add_message(request, messages.ERROR, message)
                return HttpResponseRedirect(reverse('election:election_list', args=()))
            else:
                success = False
                status += message + " "
                results = {
                    'status': status,
                    'success': success,
                    'batch_set_id': batch_set_id,
                    'retrieve_row_count': retrieve_row_count,
                }
                return results
    except Election.MultipleObjectsReturned as e:
        message = 'Could not retrieve Ballotpedia ballots. More than one election found. '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results
    except Election.DoesNotExist:
        message = 'Could not retrieve Ballotpedia ballots. Election could not be found. '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
        message = \
            'For National elections, a State Code is required in order to run any Ballotpedia ballots preparation. '
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
        else:
            success = False
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    try:
        ballot_returned_list_manager = BallotReturnedListManager()

        if positive_value_exists(refresh_ballot_returned):
            limit_polling_locations_retrieved = 250
        else:
            limit_polling_locations_retrieved = 0

        # Retrieve polling locations already in ballot_returned table
        if positive_value_exists(is_national_election) and positive_value_exists(state_code):
            results = ballot_returned_list_manager.retrieve_polling_location_we_vote_id_list_from_ballot_returned(
                google_civic_election_id=google_civic_election_id, state_code=state_code,
                limit=limit_polling_locations_retrieved,
                date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
            )
        else:
            results = ballot_returned_list_manager.retrieve_polling_location_we_vote_id_list_from_ballot_returned(
                google_civic_election_id=google_civic_election_id,
                limit=limit_polling_locations_retrieved,
                date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
            )
        if results['polling_location_we_vote_id_list_found']:
            polling_location_we_vote_id_list = results['polling_location_we_vote_id_list']
        else:
            polling_location_we_vote_id_list = []

        if positive_value_exists(refresh_ballot_returned):
            polling_location_query = PollingLocation.objects.using('readonly').all()
            polling_location_query = polling_location_query.filter(we_vote_id__in=polling_location_we_vote_id_list)
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            polling_location_list = list(polling_location_query)
            polling_location_count = len(polling_location_list)
        else:
            polling_location_query = PollingLocation.objects.using('readonly').all()
            polling_location_query = \
                polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            polling_location_query = \
                polling_location_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                               Q(zip_long__exact=''))
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            # Exclude deleted and polling locations already retrieved
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            polling_location_query = polling_location_query.exclude(we_vote_id__in=polling_location_we_vote_id_list)

            # Randomly change the sort order so we over time load different polling locations (before timeout)
            random_sorting = random.randint(1, 5)
            first_retrieve_limit = 250
            # first_retrieve_limit = 10  # For Testing
            if random_sorting == 1:
                # Ordering by "line1" creates a bit of (locational) random order
                polling_location_list = polling_location_query.order_by('line1')[:first_retrieve_limit]
                status += "RANDOM_SORTING-LINE1-ASC: " + str(random_sorting) + " "
            elif random_sorting == 2:
                polling_location_list = polling_location_query.order_by('-line1')[:first_retrieve_limit]
                status += "RANDOM_SORTING-LINE1-DESC: " + str(random_sorting) + " "
            elif random_sorting == 3:
                polling_location_list = polling_location_query.order_by('city')[:first_retrieve_limit]
                status += "RANDOM_SORTING-CITY-ASC: " + str(random_sorting) + " "
            else:
                polling_location_list = polling_location_query.order_by('-city')[:first_retrieve_limit]
                status += "RANDOM_SORTING-CITY-DESC: " + str(random_sorting) + " "
            polling_location_count = len(polling_location_list)
    except PollingLocation.DoesNotExist:
        message = 'Could not retrieve ballot data for the {election_name}. ' \
                  'No polling locations exist for the state \'{state}\'. ' \
                  'Data needed from VIP.'.format(
                     election_name=election_name,
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
        else:
            success = False
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    if polling_location_count == 0:
        message = 'Did not retrieve ballot data for the {election_name}. ' \
                  'No polling locations exist for the state \'{state}\' earlier than ' \
                  'date_last_updated_should_not_exceed: \'{date_last_updated_should_not_exceed}\'. ' \
                  '(result 2 - retrieve_ballotpedia_ballots_for_polling_locations_api_v4_view)'.format(
                     election_name=election_name,
                     date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
                     state=state_code)
        if from_browser:
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
        else:
            status += message + " "
            results = {
                'status': status,
                'success': success,
                'batch_set_id': batch_set_id,
                'retrieve_row_count': retrieve_row_count,
            }
            return results

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # If here, we assume we have already retrieved races for this election, and now we want to
    # put ballot items for this location onto a ballot
    existing_office_objects_dict = {}
    existing_candidate_objects_dict = {}
    existing_measure_objects_dict = {}
    new_office_we_vote_ids_list = []
    new_candidate_we_vote_ids_list = []
    new_measure_we_vote_ids_list = []

    batch_set_id = 0
    if len(polling_location_list) > 0:
        # Create Batch Set for ballot items
        import_date = date.today()
        batch_set_name = "Ballot items (from Polling Locations v4) for " + election_name
        if positive_value_exists(state_code):
            batch_set_name += " (state " + str(state_code.upper()) + ")"
        if positive_value_exists(ballotpedia_election_id):
            batch_set_name += " - ballotpedia: " + str(ballotpedia_election_id)
        batch_set_name += " - " + str(import_date)

        # create batch_set object
        try:
            batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
                                                batch_set_source=BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS,
                                                google_civic_election_id=google_civic_election_id,
                                                source_uri=BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL,
                                                import_date=import_date,
                                                state_code=state_code)
            batch_set_id = batch_set.id
            if positive_value_exists(batch_set_id):
                status += " BATCH_SET_SAVED-BALLOTS_FOR_POLLING_LOCATIONS "
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            status += " EXCEPTION_BATCH_SET " + str(e) + " "

    for polling_location in polling_location_list:
        one_ballot_results = retrieve_ballot_items_from_polling_location_api_v4(
            google_civic_election_id,
            election_day_text=election_day_text,
            polling_location_we_vote_id=polling_location.we_vote_id,
            polling_location=polling_location,
            state_code=state_code,
            batch_set_id=batch_set_id,
            existing_office_objects_dict=existing_office_objects_dict,
            existing_candidate_objects_dict=existing_candidate_objects_dict,
            existing_measure_objects_dict=existing_measure_objects_dict,
            new_office_we_vote_ids_list=new_office_we_vote_ids_list,
            new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
            new_measure_we_vote_ids_list=new_measure_we_vote_ids_list
        )
        success = False
        if one_ballot_results['success']:
            success = True

        if len(status) < 1024:
            status += one_ballot_results['status']

        existing_office_objects_dict = one_ballot_results['existing_office_objects_dict']
        existing_candidate_objects_dict = one_ballot_results['existing_candidate_objects_dict']
        existing_measure_objects_dict = one_ballot_results['existing_measure_objects_dict']
        new_office_we_vote_ids_list = one_ballot_results['new_office_we_vote_ids_list']
        new_candidate_we_vote_ids_list = one_ballot_results['new_candidate_we_vote_ids_list']
        new_measure_we_vote_ids_list = one_ballot_results['new_measure_we_vote_ids_list']

        if one_ballot_results['batch_header_id']:
            ballots_retrieved += 1
        else:
            ballots_not_retrieved += 1

    retrieve_row_count = ballots_retrieved

    existing_offices_found = len(existing_office_objects_dict)
    existing_candidates_found = len(existing_candidate_objects_dict)
    existing_measures_found = len(existing_measure_objects_dict)
    new_offices_found = len(new_office_we_vote_ids_list)
    new_candidates_found = len(new_candidate_we_vote_ids_list)
    new_measures_found = len(new_measure_we_vote_ids_list)

    if from_browser:
        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Ballotpedia (Polling Locations) for the {election_name}. '
                             'ballots retrieved: {ballots_retrieved}. '
                             'new offices: {new_offices_found} (existing: {existing_offices_found}) '
                             'new candidates: {new_candidates_found} (existing: {existing_candidates_found}) '
                             'new measures: {new_measures_found} (existing: {existing_measures_found}) '
                             ''.format(
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 election_name=election_name,
                                 existing_offices_found=existing_offices_found,
                                 existing_candidates_found=existing_candidates_found,
                                 existing_measures_found=existing_measures_found,
                                 new_offices_found=new_offices_found,
                                 new_candidates_found=new_candidates_found,
                                 new_measures_found=new_measures_found,
                             ))

        messages.add_message(request, messages.INFO, 'status: {status}'.format(status=status))

        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=IMPORT_BALLOTPEDIA_BALLOT_ITEMS' +
                                    '&google_civic_election_id=' + str(google_civic_election_id))
    else:
        status += \
            'Ballot data retrieved from Ballotpedia (Polling Locations) for the {election_name}. ' \
            'ballots retrieved: {ballots_retrieved}. ' \
            'new offices: {new_offices_found} (existing: {existing_offices_found}) ' \
            'new candidates: {new_candidates_found} (existing: {existing_candidates_found}) ' \
            'new measures: {new_measures_found} (existing: {existing_measures_found}) ' \
            ''.format(
                ballots_retrieved=ballots_retrieved,
                ballots_not_retrieved=ballots_not_retrieved,
                election_name=election_name,
                existing_offices_found=existing_offices_found,
                existing_candidates_found=existing_candidates_found,
                existing_measures_found=existing_measures_found,
                new_offices_found=new_offices_found,
                new_candidates_found=new_candidates_found,
                new_measures_found=new_measures_found,
            )
        results = {
            'status': status,
            'success': success,
            'batch_set_id': batch_set_id,
            'retrieve_row_count': retrieve_row_count,
        }
        return results


@login_required
def refresh_ballotpedia_ballots_for_voters_api_v4_view(request):
    """
    :param request:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')
    use_batch_process = request.GET.get('use_batch_process', False)

    if positive_value_exists(use_batch_process):
        results = schedule_refresh_ballotpedia_ballots_for_voters_api_v4(
            google_civic_election_id=google_civic_election_id, state_code=state_code)
        messages.add_message(request, messages.INFO, results['status'])
        return HttpResponseRedirect(reverse('import_export_batches:batch_process_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code)
                                    )
    else:
        return refresh_ballotpedia_ballots_for_voters_api_v4_internal_view(
            request=request, from_browser=True, google_civic_election_id=google_civic_election_id,
            state_code=state_code)


def refresh_ballotpedia_ballots_for_voters_api_v4_internal_view(
        request=None, from_browser=False, google_civic_election_id="", state_code="",
        date_last_updated_should_not_exceed=None):
    status = ""
    success = True
    batch_set_id = 0
    retrieve_row_count = 0

    try:
        if positive_value_exists(google_civic_election_id):
            election_on_stage = Election.objects.using('readonly').get(google_civic_election_id=google_civic_election_id)
            ballotpedia_election_id = election_on_stage.ballotpedia_election_id
            election_day_text = election_on_stage.election_day_text
            election_local_id = election_on_stage.id
            election_state_code = election_on_stage.get_election_state()
            election_name = election_on_stage.election_name
            is_national_election = election_on_stage.is_national_election
        else:
            message = 'Could not retrieve Ballotpedia ballots. Missing google_civic_election_id.'
            if from_browser:
                messages.add_message(request, messages.ERROR, message)
                return HttpResponseRedirect(reverse('election:election_list', args=()))
            else:
                success = False
                status += message + " "
                results = {
                    'status':               status,
                    'success':              success,
                    'batch_set_id':         batch_set_id,
                    'retrieve_row_count':   retrieve_row_count,
                }
                return results
    except Election.MultipleObjectsReturned as e:
        message = 'Could not retrieve Ballotpedia ballots. More than one election found.'
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status':               status,
                'success':              success,
                'batch_set_id':         batch_set_id,
                'retrieve_row_count':   retrieve_row_count,
            }
            return results
    except Election.DoesNotExist:
        message = 'Could not retrieve Ballotpedia ballots. Election could not be found.'
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_list', args=()))
        else:
            success = False
            status += message + " "
            results = {
                'status':               status,
                'success':              success,
                'batch_set_id':         batch_set_id,
                'retrieve_row_count':   retrieve_row_count,
            }
            return results

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    # if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
    #     messages.add_message(request, messages.ERROR,
    #                          'For National elections, a State Code is required in order to run any '
    #                          'Ballotpedia ballots preparation.')
    #     return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    ballot_returned_list_manager = BallotReturnedListManager()
    limit_voters_retrieved = 250

    # Retrieve voter_id entries from ballot_returned table, from oldest to newest
    if positive_value_exists(is_national_election) and positive_value_exists(state_code):
        results = ballot_returned_list_manager.retrieve_ballot_returned_list(
            google_civic_election_id=google_civic_election_id,
            for_voters=True,
            state_code=state_code,
            date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
            limit=limit_voters_retrieved)
    else:
        results = ballot_returned_list_manager.retrieve_ballot_returned_list(
            google_civic_election_id=google_civic_election_id,
            for_voters=True,
            date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
            limit=limit_voters_retrieved)
    if results['ballot_returned_list_found']:
        ballot_returned_list = results['ballot_returned_list']
    else:
        ballot_returned_list = []

    if len(ballot_returned_list) == 0:
        message = 'No ballot_returned items found for {election_name} for the state \'{state}\' earlier than ' \
                  'date_last_updated_should_not_exceed: \'{date_last_updated_should_not_exceed}\'. ' \
                  '(refresh_ballotpedia_ballots_for_voters_api_v4_internal_view)'.format(
                    election_name=election_name,
                    date_last_updated_should_not_exceed=date_last_updated_should_not_exceed,
                    state=state_code)
        if from_browser:
            messages.add_message(request, messages.ERROR, message)
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))
        else:
            status += message + " "
            results = {
                'status':               status,
                'success':              success,
                'batch_set_id':         batch_set_id,
                'retrieve_row_count':   retrieve_row_count,
            }
            return results

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # If here, we assume we have already retrieved races for this election, and now we want to
    # put ballot items for this location onto a ballot
    existing_office_objects_dict = {}
    existing_candidate_objects_dict = {}
    existing_measure_objects_dict = {}
    new_office_we_vote_ids_list = []
    new_candidate_we_vote_ids_list = []
    new_measure_we_vote_ids_list = []

    batch_set_id = 0
    # Create Batch Set for ballot items
    import_date = date.today()
    batch_set_name = "Ballot items (from Voters v4) for " + election_name
    if positive_value_exists(state_code):
        batch_set_name += " (state " + str(state_code.upper()) + ")"
    if positive_value_exists(ballotpedia_election_id):
        batch_set_name += " - ballotpedia: " + str(ballotpedia_election_id)
    batch_set_name += " - " + str(import_date)

    # create batch_set object
    try:
        batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
                                            batch_set_source=BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS,
                                            google_civic_election_id=google_civic_election_id,
                                            source_uri=BALLOTPEDIA_API_SAMPLE_BALLOT_RESULTS_URL,
                                            import_date=import_date,
                                            state_code=state_code)
        batch_set_id = batch_set.id
        if positive_value_exists(batch_set_id):
            status += " BATCH_SET_SAVED-BALLOTS_FOR_VOTERS "
    except Exception as e:
        # Stop trying to save rows -- break out of the for loop
        status += " EXCEPTION_BATCH_SET " + str(e) + " "

    for ballot_returned in ballot_returned_list:
        one_ballot_results = retrieve_ballot_items_for_one_voter_api_v4(
            google_civic_election_id,
            election_day_text=election_day_text,
            ballot_returned=ballot_returned,
            state_code=state_code,
            batch_set_id=batch_set_id,
            existing_office_objects_dict=existing_office_objects_dict,
            existing_candidate_objects_dict=existing_candidate_objects_dict,
            existing_measure_objects_dict=existing_measure_objects_dict,
            new_office_we_vote_ids_list=new_office_we_vote_ids_list,
            new_candidate_we_vote_ids_list=new_candidate_we_vote_ids_list,
            new_measure_we_vote_ids_list=new_measure_we_vote_ids_list
        )
        success = False
        if one_ballot_results['success']:
            success = True

        if len(status) < 1024:
            status += one_ballot_results['status']

        existing_office_objects_dict = one_ballot_results['existing_office_objects_dict']
        existing_candidate_objects_dict = one_ballot_results['existing_candidate_objects_dict']
        existing_measure_objects_dict = one_ballot_results['existing_measure_objects_dict']
        new_office_we_vote_ids_list = one_ballot_results['new_office_we_vote_ids_list']
        new_candidate_we_vote_ids_list = one_ballot_results['new_candidate_we_vote_ids_list']
        new_measure_we_vote_ids_list = one_ballot_results['new_measure_we_vote_ids_list']

        if success:
            ballots_retrieved += 1
        else:
            ballots_not_retrieved += 1

    existing_offices_found = len(existing_office_objects_dict)
    existing_candidates_found = len(existing_candidate_objects_dict)
    existing_measures_found = len(existing_measure_objects_dict)
    new_offices_found = len(new_office_we_vote_ids_list)
    new_candidates_found = len(new_candidate_we_vote_ids_list)
    new_measures_found = len(new_measure_we_vote_ids_list)

    retrieve_row_count = ballots_retrieved

    message = \
        'Ballot data retrieved from Ballotpedia (Voters) for the {election_name}. ' \
        'ballots retrieved: {ballots_retrieved}. ' \
        'new offices: {new_offices_found} (existing: {existing_offices_found}) ' \
        'new candidates: {new_candidates_found} (existing: {existing_candidates_found}) ' \
        'new measures: {new_measures_found} (existing: {existing_measures_found}) ' \
        ''.format(
             ballots_retrieved=ballots_retrieved,
             ballots_not_retrieved=ballots_not_retrieved,
             election_name=election_name,
             existing_offices_found=existing_offices_found,
             existing_candidates_found=existing_candidates_found,
             existing_measures_found=existing_measures_found,
             new_offices_found=new_offices_found,
             new_candidates_found=new_candidates_found,
             new_measures_found=new_measures_found,
        )
    if from_browser:
        messages.add_message(request, messages.INFO, message)

        messages.add_message(request, messages.INFO, 'status: {status}'.format(status=status))

        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=IMPORT_BALLOTPEDIA_BALLOT_ITEMS' +
                                    '&google_civic_election_id=' + str(google_civic_election_id))
    else:
        status += message + " "
        results = {
            'status':               status,
            'success':              success,
            'batch_set_id':         batch_set_id,
            'retrieve_row_count':   retrieve_row_count,
        }
        return results


@login_required
def retrieve_ballotpedia_data_for_polling_locations_view(request, election_local_id=0):
    """
    Reach out to Ballotpedia and retrieve (for one election):
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

    force_district_retrieve_from_ballotpedia = request.GET.get('force_district_retrieve_from_ballotpedia', False)
    state_code = request.GET.get('state_code', '')
    retrieve_races = positive_value_exists(request.GET.get('retrieve_races', False))
    retrieve_measures = positive_value_exists(request.GET.get('retrieve_measures', False))
    import_limit = convert_to_int(request.GET.get('import_limit', 1000))  # If > 1000, we get error 414 (url too long)

    polling_location_list = []
    polling_location_count = 0
    status = ""

    try:
        if positive_value_exists(election_local_id):
            election_on_stage = Election.objects.get(id=election_local_id)
            ballotpedia_election_id = election_on_stage.ballotpedia_election_id
            google_civic_election_id = election_on_stage.google_civic_election_id
            election_state_code = election_on_stage.get_election_state()
            election_name = election_on_stage.election_name
            is_national_election = election_on_stage.is_national_election
        else:
            messages.add_message(request, messages.ERROR,
                                 'Could not retrieve Ballotpedia data. Missing election_local_id.')
            return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.MultipleObjectsReturned as e:
        messages.add_message(request, messages.ERROR, 'Could not retrieve Ballotpedia data. '
                                                      'More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'Could not retrieve Ballotpedia data. '
                                                      'Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    if positive_value_exists(is_national_election) and not positive_value_exists(state_code):
        messages.add_message(request, messages.ERROR,
                             'For National elections, a State Code is required in order to run any '
                             'Ballotpedia data preparation.')
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
        polling_location_count = polling_location_count_query.count()

        if positive_value_exists(polling_location_count):
            polling_location_query = PollingLocation.objects.all()
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            polling_location_query = polling_location_query.filter(use_for_bulk_retrieve=True)
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            # We used to have a limit of 500 ballots to pull per election, but now retrieve all
            # Ordering by "line1" creates a bit of (locational) random order
            polling_location_list = polling_location_query.order_by('line1')[:import_limit]
    except Exception as e:
        status += "COULD_NOT_FIND_POLLING_LOCATION_LIST " + str(e) + " "

    if polling_location_count == 0:
        # We didn't find any polling locations marked for bulk retrieve, so just retrieve up to the import_limit
        try:
            polling_location_count_query = PollingLocation.objects.all()
            polling_location_count_query = \
                polling_location_count_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            polling_location_count_query = \
                polling_location_count_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                                     Q(zip_long__exact=''))
            polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
            polling_location_count_query = polling_location_count_query.exclude(polling_location_deleted=True)
            polling_location_count = polling_location_count_query.count()

            if positive_value_exists(polling_location_count):
                polling_location_query = PollingLocation.objects.all()
                polling_location_query = \
                    polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
                polling_location_query = \
                    polling_location_query.exclude(Q(zip_long__isnull=True) | Q(zip_long__exact='0') |
                                                   Q(zip_long__exact=''))
                polling_location_query = polling_location_query.filter(state__iexact=state_code)
                polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
                # Ordering by "line1" creates a bit of (locational) random order
                polling_location_list = polling_location_query.order_by('line1')[:import_limit]
        except PollingLocation.DoesNotExist:
            messages.add_message(request, messages.INFO,
                                 'Could not retrieve ballot data for the {election_name}. '
                                 'No polling locations exist for the state \'{state}\'. '
                                 'Data needed from VIP.'.format(
                                     election_name=election_name,
                                     state=state_code))
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations returned for the state \'{state}\'. '
                             '(error 2 - retrieve_ballotpedia_data_for_polling_locations_view)'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # Step though our set of polling locations, until we find one that contains a ballot.  Some won't contain ballots
    # due to data quality issues.
    if retrieve_races or retrieve_measures or force_district_retrieve_from_ballotpedia:
        polling_locations_with_data = 0
        polling_locations_without_data = 0
        # If here we just want to retrieve the races for this election
        merged_district_list = []
        for polling_location in polling_location_list:
            one_ballot_results = retrieve_ballotpedia_district_id_list_for_polling_location(
                google_civic_election_id, polling_location=polling_location,
                force_district_retrieve_from_ballotpedia=force_district_retrieve_from_ballotpedia)
            success = False
            if one_ballot_results['success']:
                success = True
                ballotpedia_district_id_list = one_ballot_results['ballotpedia_district_id_list']
                if len(ballotpedia_district_id_list):
                    for one_ballotpedia_district_id in ballotpedia_district_id_list:
                        if one_ballotpedia_district_id not in merged_district_list:
                            # Build up a list of ballotpedia districts that we need to retrieve races for
                            merged_district_list.append(one_ballotpedia_district_id)

            if success:
                polling_locations_with_data += 1
            else:
                polling_locations_without_data += 1

        # Once we have a summary of all ballotpedia districts, we want to request all of the races or measures
        if len(merged_district_list):
            kind_of_batch = "Unknown"
            results = {}
            if retrieve_races:
                results = retrieve_ballotpedia_offices_by_district_from_api(google_civic_election_id, state_code,
                                                                            merged_district_list)

                kind_of_batch = ""
                if 'kind_of_batch' in results:
                    kind_of_batch = results['kind_of_batch']
                if not positive_value_exists(kind_of_batch):
                    kind_of_batch = CONTEST_OFFICE
                status += results['status']
            elif retrieve_measures:
                results = retrieve_ballotpedia_measures_by_district_from_api(google_civic_election_id, state_code,
                                                                             merged_district_list)

                kind_of_batch = ""
                if 'kind_of_batch' in results:
                    kind_of_batch = results['kind_of_batch']
                if not positive_value_exists(kind_of_batch):
                    kind_of_batch = MEASURE
                status += results['status']
            batch_header_id = 0
            if 'batch_saved' in results and results['batch_saved']:
                messages.add_message(request, messages.INFO,
                                     kind_of_batch +
                                     ' import batch for {google_civic_election_id} election saved. '
                                     'status: {status}'
                                     ''.format(google_civic_election_id=google_civic_election_id,
                                               status=status))
                batch_header_id = results['batch_header_id']
            elif 'multiple_batches_found' in results and results['multiple_batches_found']:
                messages.add_message(request, messages.INFO,
                                     kind_of_batch +
                                     ' multiple import batches for {google_civic_election_id} election saved.'
                                     ' status: {status}'
                                     ''.format(google_civic_election_id=google_civic_election_id,
                                               status=status))
                batch_header_id = results['batch_header_id']
                # Go straight to the list of batches
                return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                            "?kind_of_batch=" + str(kind_of_batch) +
                                            "&google_civic_election_id=" + str(google_civic_election_id))
            elif 'batch_header_id' in results and results['batch_header_id']:
                messages.add_message(request, messages.INFO,
                                     kind_of_batch +
                                     ' import batch for {google_civic_election_id} election saved, '
                                     'batch_header_id. status: {status}'
                                     ''.format(google_civic_election_id=google_civic_election_id,
                                               status=status))
                batch_header_id = results['batch_header_id']
            else:
                messages.add_message(request, messages.ERROR, results['status'])

            if positive_value_exists(batch_header_id):
                # Go straight to the new batch
                return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
                                            "?batch_header_id=" + str(batch_header_id) +
                                            "&kind_of_batch=" + str(kind_of_batch) +
                                            "&google_civic_election_id=" + str(google_civic_election_id))
            else:
                if retrieve_races:
                    # Go to the office listing page
                    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                                "?google_civic_election_id=" + str(google_civic_election_id))
                elif retrieve_measures:
                    # Go to the measure listing page
                    return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                                "?google_civic_election_id=" + str(google_civic_election_id))

        messages.add_message(request, messages.INFO,
                             'Races or measures retrieved from Ballotpedia for the {election_name}. '
                             'polling_locations_with_data: {polling_locations_with_data}, '
                             'polling_locations_without_data: {polling_locations_without_data}. '
                             ''.format(
                                 polling_locations_with_data=polling_locations_with_data,
                                 polling_locations_without_data=polling_locations_with_data,
                                 election_name=election_name))
        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=IMPORT_BALLOTPEDIA_BALLOT_ITEMS' +
                                    '&google_civic_election_id=' + str(google_civic_election_id))
    else:
        # Create Batch Set for ballot items
        import_date = date.today()
        batch_set_id = 0
        batch_set_name = "Ballotpedia ballot items (from Polling Locations v3) for " + election_name
        if positive_value_exists(state_code):
            batch_set_name += " (state " + str(state_code.upper()) + ")"
        if positive_value_exists(ballotpedia_election_id):
            batch_set_name += " - ballotpedia: " + str(ballotpedia_election_id)
        batch_set_name += " - " + str(import_date)

        # create batch_set object
        try:
            batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
                                                batch_set_source=BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS,
                                                google_civic_election_id=google_civic_election_id,
                                                source_uri=BALLOTPEDIA_API_CONTAINS_URL, import_date=import_date,
                                                state_code=state_code)
            batch_set_id = batch_set.id
            if positive_value_exists(batch_set_id):
                status += " BATCH_SET_SAVED-POLLING_OLD "
                success = True
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            status += " EXCEPTION_BATCH_SET " + str(e) + " "

        # If here, we assume we have already retrieved races for this election, and now we want to
        # put ballot items for this location onto a ballot
        for polling_location in polling_location_list:
            one_ballot_results = retrieve_ballot_items_from_polling_location(
                google_civic_election_id, polling_location=polling_location, batch_set_id=batch_set_id,
                state_code=state_code)
            success = False
            if one_ballot_results['success']:
                success = True

            if success:
                ballots_retrieved += 1
            else:
                ballots_not_retrieved += 1

        # We used to only retrieve up to 500 locations from each state, but we don't limit now
        # # Break out of this loop, assuming we have a minimum number of ballots with contests retrieved
        # #  If we don't achieve the minimum number of ballots_with_contests_retrieved, break out at the emergency level
        # emergency = (ballots_retrieved + ballots_not_retrieved) >= (3 * number_of_polling_locations_to_retrieve)
        # if ((ballots_retrieved + ballots_not_retrieved) >= number_of_polling_locations_to_retrieve and
        #         ballots_with_contests_retrieved > 20) or emergency:
        #     break

        messages.add_message(request, messages.INFO,
                             'Ballot data retrieved from Ballotpedia for the {election_name}. '
                             'ballots retrieved: {ballots_retrieved}. '
                             ''.format(
                                 ballots_retrieved=ballots_retrieved,
                                 ballots_not_retrieved=ballots_not_retrieved,
                                 election_name=election_name))
        return HttpResponseRedirect(reverse('import_export_batches:batch_set_list', args=()) +
                                    '?kind_of_batch=IMPORT_BALLOTPEDIA_BALLOT_ITEMS' +
                                    '&google_civic_election_id=' + str(google_civic_election_id))


# @login_required
# def retrieve_ballotpedia_offices_by_election_from_api_view(request):
#     """
#     Reach out to Ballotpedia API to retrieve offices.
#     """
#     # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
#     authority_required = {'political_data_manager'}
#     if not voter_has_authority(request, authority_required):
#         return redirect_to_sign_in_page(request, authority_required)
#
#     google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
#
#     results = retrieve_ballotpedia_offices_by_election_from_api(google_civic_election_id)
#
#     kind_of_batch = ""
#     if 'kind_of_batch' in results:
#         kind_of_batch = results['kind_of_batch']
#     if not positive_value_exists(kind_of_batch):
#         kind_of_batch = CONTEST_OFFICE
#
#     batch_header_id = 0
#     if 'batch_saved' in results and results['batch_saved']:
#         messages.add_message(request, messages.INFO, 'Import batch for {google_civic_election_id} election saved.'
#                                                      ''.format(google_civic_election_id=google_civic_election_id))
#         batch_header_id = results['batch_header_id']
#     elif 'batch_header_id' in results and results['batch_header_id']:
#         messages.add_message(request, messages.INFO, 'Import batch for {google_civic_election_id} election saved, '
#                                                      'batch_header_id.'
#                                                      ''.format(google_civic_election_id=google_civic_election_id))
#         batch_header_id = results['batch_header_id']
#     else:
#         messages.add_message(request, messages.ERROR, results['status'])
#
#     if positive_value_exists(batch_header_id):
#         # Go straight to the new batch
#         return HttpResponseRedirect(reverse('import_export_batches:batch_action_list', args=()) +
#                                     "?batch_header_id=" + str(batch_header_id) +
#                                     "&kind_of_batch=" + str(kind_of_batch) +
#                                     "&google_civic_election_id=" + str(google_civic_election_id))
#     else:
#         # Go to the office listing page
#         return HttpResponseRedirect(reverse('office:office_list', args=()) +
#                                     "?google_civic_election_id=" + str(google_civic_election_id))
