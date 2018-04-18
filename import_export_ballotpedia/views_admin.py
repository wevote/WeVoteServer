# import_export_ballotpedia/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_candidates_from_api, retrieve_districts_to_which_address_belongs_from_api
from admin_tools.views import redirect_to_sign_in_page
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from election.models import Election
from polling_location.models import PollingLocation
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
ELECTED_OFFICE = 'ELECTED_OFFICE'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'


def import_ballot_items_for_location_view(request):
    """
    Reach out to Ballotpedia API to retrieve a short list of districts the voter can vote in.
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', "")

    results = retrieve_districts_to_which_address_belongs_from_api(
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


def import_export_ballotpedia_index_view(request):
    """
    Provide an index of import/export actions (for We Vote data maintenance)
    """
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':    messages_on_stage,
    }
    return render(request, 'import_export_ballotpedia/index.html', template_values)


def retrieve_candidates_from_api_view(request):
    """
    Reach out to Ballotpedia API to retrieve candidates.
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated():
        return redirect('/admin')

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    zero_entries = request.GET.get('zero_entries', True)

    results = retrieve_candidates_from_api(google_civic_election_id, zero_entries)

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
def retrieve_distributed_ballotpedia_ballots_view(request, election_local_id=0):
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
    import_limit = convert_to_int(request.GET.get('import_limit', 100))

    ballotpedia_election_found = False
    google_civic_election_id = 0

    try:
        if positive_value_exists(election_local_id):
            election_on_stage = Election.objects.get(id=election_local_id)
            ballotpedia_election_found = election_on_stage.ballotpedia_election_id
            google_civic_election_id = election_on_stage.google_civic_election_id
    except Election.MultipleObjectsReturned as e:
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. More than one election found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))
    except Election.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'Could not retrieve ballot data. Election could not be found.')
        return HttpResponseRedirect(reverse('election:election_list', args=()))

    if not positive_value_exists(ballotpedia_election_found):
        messages.add_message(request, messages.ERROR, 'Ballotpedia election could not be found.')
        return HttpResponseRedirect(reverse('election:election_summary', args=(election_local_id,)))

    # Check to see if we have polling location data related to the region(s) covered by this election
    # We request the ballot data for each polling location as a way to build up our local data
    if not positive_value_exists(state_code):
        state_code = election_on_stage.get_election_state()
        if not positive_value_exists(state_code):
            state_code = "CA"  # TODO DALE Temp for 2016

    try:
        polling_location_count_query = PollingLocation.objects.all()
        polling_location_count_query = polling_location_count_query.filter(state__iexact=state_code)
        polling_location_count_query = polling_location_count_query.filter(use_for_bulk_retrieve=True)
        polling_location_count = polling_location_count_query.count()

        polling_location_list = PollingLocation.objects.all()
        polling_location_list = polling_location_list.filter(state__iexact=state_code)
        polling_location_list = polling_location_list.filter(use_for_bulk_retrieve=True)
        # We used to have a limit of 500 ballots to pull per election, but now retrieve all
        # Ordering by "location_name" creates a bit of (locational) random order
        polling_location_list = polling_location_list.order_by('location_name')[:import_limit]
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
    rate_limit_count = 0

    # # Create Batch Set
    # election_name = ""
    # import_date = date.today()
    # batch_set_name = "Ballotpedia ballot locations " + election_name + " - ballotpedia: " + ballotpedia_election_id + \
    #                  " - " + str(import_date)
    #
    # # create batch_set object
    # try:
    #     batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
    #                                         batch_set_source=BATCH_SET_SOURCE_IMPORT_EXPORT_ENDORSEMENTS,
    #                                         source_uri=batch_set_name_url, import_date=import_date)
    #     batch_set_id = batch_set.id
    #     if positive_value_exists(batch_set_id):
    #         status += " BATCH_SET_SAVED"
    #         success = True
    # except Exception as e:
    #     # Stop trying to save rows -- break out of the for loop
    #     batch_set_id = 0
    #     status += " EXCEPTION_BATCH_SET "
    #     handle_exception(e, logger=logger, exception_message=status)

    # Step though our set of polling locations, until we find one that contains a ballot.  Some won't contain ballots
    # due to data quality issues.
    for polling_location in polling_location_list:
        one_ballot_results = retrieve_districts_to_which_address_belongs_from_api(
            google_civic_election_id, polling_location=polling_location)
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
                             election_name=election_on_stage.election_name))
    return HttpResponseRedirect(reverse('import_export_batches:batch_list', args=()) +
                                '?kind_of_batch=IMPORT_BALLOT_ITEM' +
                                '&google_civic_election_id=' + str(google_civic_election_id))
