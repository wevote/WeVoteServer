# import_export_ballotpedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from candidate.models import CandidateCampaign, CandidateListManager
from wevote_settings.models import RemoteRequestHistoryManager
from .controllers import attach_ballotpedia_election_by_district_from_api, \
    retrieve_ballot_items_from_polling_location, \
    retrieve_ballotpedia_candidates_by_district_from_api, retrieve_ballotpedia_measures_by_district_from_api, \
    retrieve_ballotpedia_district_id_list_for_polling_location, retrieve_ballotpedia_offices_by_district_from_api
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from election.models import Election, ElectionManager
from import_export_ballotpedia.controllers import get_photo_url_from_ballotpedia
from import_export_batches.models import BatchSet, BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS

from polling_location.models import PollingLocation
from volunteer_task.models import VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE, VolunteerTaskManager
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_valid_state_code, positive_value_exists
from wevote_settings.models import RemoteRequestHistory, RETRIEVE_POSSIBLE_BALLOTPEDIA_PHOTOS

logger = wevote_functions.admin.get_logger(__name__)

BALLOTPEDIA_API_CONTAINS_URL = get_environment_variable("BALLOTPEDIA_API_CONTAINS_URL")
MAXIMUM_BALLOTPEDIA_IMAGES_TO_RECEIVE_AT_ONCE = 50

CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
OFFICE_HELD = 'OFFICE_HELD'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'


@login_required
def bulk_retrieve_ballotpedia_photos_view(request):
    status = ""
    remote_request_history_manager = RemoteRequestHistoryManager()

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    hide_candidate_tools = request.GET.get('hide_candidate_tools', False)
    page = request.GET.get('page', 0)
    state_code = request.GET.get('state_code', '')
    limit = convert_to_int(request.GET.get('limit', MAXIMUM_BALLOTPEDIA_IMAGES_TO_RECEIVE_AT_ONCE))
    print(google_civic_election_id, hide_candidate_tools, state_code, limit)
    if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code) \
            and not positive_value_exists(limit):
        messages.add_message(request, messages.ERROR,
                             'bulk_retrieve_ballotpedia_photos_view, LIMITING_VARIABLE_REQUIRED')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&state_code=' + str(state_code) +
                                    '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                    '&page=' + str(page)
                                    )

    try:
        # Give the volunteer who entered this credit
        volunteer_task_manager = VolunteerTaskManager()
        task_results = volunteer_task_manager.create_volunteer_task_completed(
            action_constant=VOLUNTEER_ACTION_PHOTO_BULK_RETRIEVE,
            request=request,
        )
    except Exception as e:
        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    # #############################################################
    # Get candidates in the elections we care about - used below
    candidate_list_manager = CandidateListManager()
    if positive_value_exists(google_civic_election_id):
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=[google_civic_election_id])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']
    else:
        # Only look at candidates for this year
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_year_list(
            year_list=[2024])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    candidate_list = []
    already_retrieved = 0
    already_stored = 0
    try:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(we_vote_id__in=candidate_we_vote_id_list)  # Candidates for election or this year
        queryset = queryset.exclude(ballotpedia_photo_url_is_placeholder=True)
        # queryset = queryset.filter(ballotpedia_photo_url_is_broken=False)
        # Don't include candidates that do not have ballotpedia_candidate_url
        queryset = queryset. \
            exclude(Q(ballotpedia_candidate_url__isnull=True) | Q(ballotpedia_candidate_url__exact=''))
        # Only include candidates that don't have a photo
        queryset = queryset.filter(
            Q(ballotpedia_photo_url__isnull=True) | Q(ballotpedia_photo_url__iexact=''))
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        if positive_value_exists(limit):
            candidate_list = queryset[:limit]
        else:
            candidate_list = list(queryset)
        print(candidate_list)
        # Run search in ballotpedia candidates
        for one_candidate in candidate_list:
            # Check to see if we have already tried to find their photo link from Ballotpedia. We don't want to
            #  search Ballotpedia more than once.
            # request_history_query = RemoteRequestHistory.objects.using('readonly').filter(
            #     candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
            #     kind_of_action=RETRIEVE_POSSIBLE_BALLOTPEDIA_PHOTOS)
            # request_history_list = list(request_history_query)
            request_history_list = []
            if not positive_value_exists(len(request_history_list)):
                add_messages = False
                get_results = get_photo_url_from_ballotpedia(
                    incoming_object=one_candidate,
                    request=request,
                    remote_request_history_manager=remote_request_history_manager,
                    save_to_database=True,
                    add_messages=add_messages)
                status += get_results['status']
            else:
                logger.info("Skipped URL: " + one_candidate.ballotpedia_candidate_url)
                already_stored += 1
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    if positive_value_exists(already_stored):
        status += "ALREADY_STORED_TOTAL-(" + str(already_stored) + ") "
    if positive_value_exists(already_retrieved):
        status += "ALREADY_RETRIEVED_TOTAL-(" + str(already_retrieved) + ") "

    messages.add_message(request, messages.INFO, status)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                '?google_civic_election_id=' + str(google_civic_election_id) +
                                '&state_code=' + str(state_code) +
                                '&hide_candidate_tools=' + str(hide_candidate_tools) +
                                '&page=' + str(page)
                                )


@login_required
def attach_ballotpedia_election_view(request, election_local_id=0):
    """
    Reach out to Ballotpedia and retrieve the details about this election needed to make other API calls.
    :param request:
    :param election_local_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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

    # Check to see if we have map point data related to the region(s) covered by this election
    # We request the ballot data for each map point as a way to build up our local data
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
                             'Could not retrieve map point data for the {election_name}. '
                             'No map points exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                    "?state_code=" + str(state_code))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No map points returned for the state \'{state}\'. '
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
                             'Could not retrieve district_id list for this many Map Points: ' +
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
    1) Retrieve (internally) map points (so we can use those addresses to retrieve a
    representative set of ballots)
    2) Cycle through a portion of those map points, enough that we are caching all of the possible ballot items
    3) Ask for Ballotpedia districts for each of the map points being analyzed
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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
        # We didn't find any map points marked for bulk retrieve, so just retrieve up to the import_limit
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
                                 'No map points exist for the state \'{state}\'. '
                                 'Data needed from VIP.'.format(
                                     state=state_code))
            return HttpResponseRedirect(reverse('electoral_district:electoral_district_list', args=()))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data. '
                             'No map points returned for the state \'{state}\'. '
                             '(error 2 - refresh_ballotpedia_districts_for_polling_locations_view)'.format(
                                 state=state_code))
        return HttpResponseRedirect(reverse('electoral_district:electoral_district_list', args=()))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts

    # Step though our set of map points, until we find one that contains a ballot.  Some won't contain ballots
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
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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
def retrieve_ballotpedia_data_for_polling_locations_view(request, election_local_id=0):
    """
    Reach out to Ballotpedia and retrieve (for one election):
    1) Polling locations (so we can use those addresses to retrieve a representative set of ballots)
    2) Cycle through a portion of those map points, enough that we are caching all of the possible ballot items
    :param request:
    :param election_local_id:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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

    # Check to see if we have map point data related to the region(s) covered by this election
    # We request the ballot data for each map point as a way to build up our local data
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
        # We didn't find any map points marked for bulk retrieve, so just retrieve up to the import_limit
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
                                 'No map points exist for the state \'{state}\'. '
                                 'Data needed from VIP.'.format(
                                     election_name=election_name,
                                     state=state_code))
            return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No map points returned for the state \'{state}\'. '
                             '(error 2 - retrieve_ballotpedia_data_for_polling_locations_view)'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # Step though our set of map points, until we find one that contains a ballot.  Some won't contain ballots
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
        batch_set_name = "Ballotpedia ballot items (from Map Points v3) for " + election_name
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
                             'Ballot data retrieved from Ballotpedia v3 for the {election_name}. '
                             'ballots retrieved: {ballots_retrieved}. '
                             'ballots not retrieved: {ballots_not_retrieved}. '
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
#     # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
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
