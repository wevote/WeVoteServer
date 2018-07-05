# import_export_ballotpedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import attach_ballotpedia_election_by_district_from_api, \
    retrieve_ballot_items_from_polling_location, \
    retrieve_ballotpedia_candidates_by_district_from_api, retrieve_ballotpedia_measures_by_district_from_api, \
    retrieve_ballotpedia_district_id_list_for_polling_location, retrieve_ballotpedia_offices_by_district_from_api, \
    retrieve_ballotpedia_offices_by_election_from_api
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from election.models import Election
from import_export_batches.models import BatchSet, BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS
from polling_location.models import PollingLocation
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

BALLOTPEDIA_API_CONTAINS_URL = get_environment_variable("BALLOTPEDIA_API_CONTAINS_URL")

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
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', "")

    results = retrieve_ballot_items_from_polling_location(
        google_civic_election_id, polling_location_we_vote_id)

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
    election_state_code = ""

    ballotpedia_election_id = 0
    ballotpedia_kind_of_election = ""
    google_civic_election_id = 0
    polling_location_list = []
    election_name = "(election name unknown)"
    status = ""

    try:
        election_on_stage = Election.objects.get(id=election_local_id)
        ballotpedia_election_id = election_on_stage.ballotpedia_election_id
        google_civic_election_id = election_on_stage.google_civic_election_id
        ballotpedia_kind_of_election = election_on_stage.ballotpedia_kind_of_election
        election_state_code = election_on_stage.get_election_state()
        election_name = election_on_stage.election_name
    except Election.MultipleObjectsReturned as e:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve election data. More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve election data. Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    # We want to be able to run this again later in the election cycle
    # if positive_value_exists(ballotpedia_election_id) and positive_value_exists(ballotpedia_kind_of_election):
    #     messages.add_message(request, messages.ERROR,
    #                          'Required values already exist. '
    #                          '(ballotpedia_election_id & ballotpedia_kind_of_election)')
    #     return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.exclude(
            Q(latitude__isnull=True) | Q(latitude__exact=0.0))
        polling_location_count = polling_location_count_query.count()

        if positive_value_exists(polling_location_count):
            polling_location_query = PollingLocation.objects.all()
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            polling_location_query = polling_location_query.exclude(
                Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            # Ordering by "location_name" creates a bit of (locational) random order
            polling_location_list = polling_location_query.order_by('location_name')[:1000]
    except PollingLocation.DoesNotExist:
        messages.add_message(request, messages.INFO,
                             'Could not retrieve polling location data for the {election_name}. '
                             'No polling locations exist for the state \'{state}\'. '
                             'Data needed from VIP.'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    if polling_location_count == 0:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve ballot data for the {election_name}. '
                             'No polling locations returned for the state \'{state}\'. (error 2)'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    merged_district_list = []
    for polling_location in polling_location_list:
        one_ballot_results = retrieve_ballotpedia_district_id_list_for_polling_location(
            google_civic_election_id, polling_location=polling_location)
        if one_ballot_results['success']:
            ballotpedia_district_id_list = one_ballot_results['ballotpedia_district_id_list']
            if len(ballotpedia_district_id_list):
                for one_ballotpedia_district_id in ballotpedia_district_id_list:
                    if one_ballotpedia_district_id not in merged_district_list:
                        # Build up a list of ballotpedia districts that we need to retrieve races for
                        merged_district_list.append(one_ballotpedia_district_id)

    # Once we have a summary of all ballotpedia districts, we want to request all of the races
    if not len(merged_district_list):
        messages.add_message(request, messages.ERROR,
                             'Could not find Ballotpedia districts. ')
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)) +
                                    '?google_civic_election_id=' + str(google_civic_election_id))

    results = attach_ballotpedia_election_by_district_from_api(election_on_stage, google_civic_election_id,
                                                               merged_district_list)

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

    results = retrieve_ballotpedia_candidates_by_district_from_api(google_civic_election_id,
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
    2) Cycle through a portion of those polling locations, enough that we are caching all of the possible ballot items
    :param request:
    :param election_local_id:
    :return:
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    state_code = request.GET.get('state_code', '')
    retrieve_races = positive_value_exists(request.GET.get('retrieve_races', False))
    retrieve_measures = positive_value_exists(request.GET.get('retrieve_measures', False))
    election_state_code = ""
    import_limit = convert_to_int(request.GET.get('import_limit', 500))

    ballotpedia_election_found = False
    ballotpedia_election_id = 0
    google_civic_election_id = 0
    polling_location_list = []
    polling_location_count = 0
    election_name = "(election name unknown)"
    status = ""

    try:
        if positive_value_exists(election_local_id):
            election_on_stage = Election.objects.get(id=election_local_id)
            ballotpedia_election_found = positive_value_exists(election_on_stage.ballotpedia_election_id)
            ballotpedia_election_id = election_on_stage.ballotpedia_election_id
            google_civic_election_id = election_on_stage.google_civic_election_id
            ballotpedia_kind_of_election = election_on_stage.ballotpedia_kind_of_election
            election_state_code = election_on_stage.get_election_state()
            election_name = election_on_stage.election_name
    except Election.MultipleObjectsReturned as e:
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    # 2018-6-7 We now can retrieve two elections at once (primary and general)
    # if not positive_value_exists(ballotpedia_election_found):
    #     messages.add_message(request, messages.ERROR, 'Ballotpedia election could not be found.')
    #     return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
        state_code = election_state_code

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_count = polling_location_count_query.count()

        if positive_value_exists(polling_location_count):
            polling_location_query = PollingLocation.objects.all()
            polling_location_query = polling_location_query.filter(state__iexact=state_code)
            polling_location_query = polling_location_query.filter(use_for_bulk_retrieve=True)
            # We used to have a limit of 500 ballots to pull per election, but now retrieve all
            # Ordering by "location_name" creates a bit of (locational) random order
            polling_location_list = polling_location_query.order_by('location_name')[:import_limit]
    except Exception as e:
        status += "COULD_NOT_FIND_POLLING_LOCATION_LIST " + str(e) + " "

    if polling_location_count == 0:
        # We didn't find any polling locations marked for bulk retrieve, so just retrieve the top 100 (for now)
        try:
            polling_location_count_query = PollingLocation.objects.all()
            polling_location_count_query = \
                polling_location_count_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
            polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
            polling_location_count = polling_location_count_query.count()

            if positive_value_exists(polling_location_count):
                polling_location_query = PollingLocation.objects.all()
                polling_location_query = \
                    polling_location_query.exclude(Q(latitude__isnull=True) | Q(latitude__exact=0.0))
                polling_location_query = polling_location_query.filter(state__iexact=state_code)
                # Ordering by "location_name" creates a bit of (locational) random order
                polling_location_list = polling_location_query.order_by('location_name')[:import_limit]
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
                             'No polling locations returned for the state \'{state}\'. (error 2)'.format(
                                 election_name=election_name,
                                 state=state_code))
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # If here, we know that we have some polling_locations to use in order to retrieve ballotpedia districts
    ballots_retrieved = 0
    ballots_not_retrieved = 0

    # Step though our set of polling locations, until we find one that contains a ballot.  Some won't contain ballots
    # due to data quality issues.
    if retrieve_races or retrieve_measures:
        polling_locations_with_data = 0
        polling_locations_without_data = 0
        # If here we just want to retrieve the races for this election
        merged_district_list = []
        for polling_location in polling_location_list:
            one_ballot_results = retrieve_ballotpedia_district_id_list_for_polling_location(
                google_civic_election_id, polling_location=polling_location)
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
                results = retrieve_ballotpedia_offices_by_district_from_api(google_civic_election_id,
                                                                            merged_district_list)

                kind_of_batch = ""
                if 'kind_of_batch' in results:
                    kind_of_batch = results['kind_of_batch']
                if not positive_value_exists(kind_of_batch):
                    kind_of_batch = CONTEST_OFFICE
            elif retrieve_measures:
                results = retrieve_ballotpedia_measures_by_district_from_api(google_civic_election_id,
                                                                             merged_district_list)

                kind_of_batch = ""
                if 'kind_of_batch' in results:
                    kind_of_batch = results['kind_of_batch']
                if not positive_value_exists(kind_of_batch):
                    kind_of_batch = MEASURE

            batch_header_id = 0
            if 'batch_saved' in results and results['batch_saved']:
                messages.add_message(request, messages.INFO,
                                     kind_of_batch +
                                     ' import batch for {google_civic_election_id} election saved.'
                                     ''.format(google_civic_election_id=google_civic_election_id))
                batch_header_id = results['batch_header_id']
            elif 'batch_header_id' in results and results['batch_header_id']:
                messages.add_message(request, messages.INFO,
                                     kind_of_batch +
                                     ' import batch for {google_civic_election_id} election saved, '
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
                if retrieve_races:
                    # Go to the office listing page
                    return HttpResponseRedirect(reverse('office:office_list', args=()) +
                                                "?google_civic_election_id=" + str(google_civic_election_id))
                elif retrieve_measures:
                    # Go to the measure listing page
                    return HttpResponseRedirect(reverse('measure:measure_list', args=()) +
                                                "?google_civic_election_id=" + str(google_civic_election_id))

        messages.add_message(request, messages.INFO,
                             'Races retrieved from Ballotpedia for the {election_name}. '
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
        batch_set_name = "Ballotpedia ballot locations for " + election_name + \
                         " - ballotpedia: " + str(ballotpedia_election_id) + \
                         " - " + str(import_date)

        # create batch_set object
        try:
            batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
                                                batch_set_source=BATCH_SET_SOURCE_IMPORT_BALLOTPEDIA_BALLOT_ITEMS,
                                                google_civic_election_id=google_civic_election_id,
                                                source_uri=BALLOTPEDIA_API_CONTAINS_URL, import_date=import_date)
            batch_set_id = batch_set.id
            if positive_value_exists(batch_set_id):
                status += " BATCH_SET_SAVED"
                success = True
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            status += " EXCEPTION_BATCH_SET "

        # If here, we assume we have already retrieved races for this election, and now we want to
        # put ballot items for this location onto a ballot
        for polling_location in polling_location_list:
            one_ballot_results = retrieve_ballot_items_from_polling_location(
                google_civic_election_id, polling_location=polling_location, batch_set_id=batch_set_id)
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


@login_required
def retrieve_ballotpedia_offices_by_election_from_api_view(request):
    """
    Reach out to Ballotpedia API to retrieve offices.
    """
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    results = retrieve_ballotpedia_offices_by_election_from_api(google_civic_election_id)

    kind_of_batch = ""
    if 'kind_of_batch' in results:
        kind_of_batch = results['kind_of_batch']
    if not positive_value_exists(kind_of_batch):
        kind_of_batch = CONTEST_OFFICE

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
