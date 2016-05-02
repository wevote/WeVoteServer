# ballot/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItemListManager, BallotReturned, BallotReturnedManager
from admin_tools.views import redirect_to_sign_in_page
from candidate.models import CandidateCampaign, CandidateCampaignList, CandidateCampaignManager
from office.models import ContestOffice
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception, print_to_log
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def ballot_item_list_edit_view(request, ballot_returned_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', '')

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
    contest_office_list = []
    if google_civic_election_id:
        try:
            election = Election.objects.get(google_civic_election_id=google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            pass
        except Election.DoesNotExist:
            pass

        # Get a list of offices for this election so we can create drop downs
        try:
            contest_office_list = ContestOffice.objects.order_by('office_name')
            contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
        except Exception as e:
            contest_office_list = []
    else:
        messages.add_message(request, messages.ERROR, 'In order to create a \'ballot_returned\' entry, '
                                                      'a google_civic_election_id is required.')

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
        'messages_on_stage':        messages_on_stage,
        'ballot_returned':          ballot_returned,
        'ballot_returned_id':       ballot_returned_id,
        'election':                 election,
        'office_list':              contest_office_list,
        'ballot_item_list':         ballot_item_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'ballot/ballot_item_list_edit.html', template_values)


@login_required
def ballot_item_list_edit_process_view(request):
    """
    Process the new or edit candidate forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(request.POST['candidate_id'])
    candidate_name = request.POST.get('candidate_name', False)
    candidate_twitter_handle = request.POST.get('candidate_twitter_handle', False)
    candidate_url = request.POST.get('candidate_url', False)
    contest_office_id = request.POST.get('contest_office_id', False)
    ballot_guide_official_statement = request.POST.get('ballot_guide_official_statement', False)

    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)

    # Check to see if this candidate is already being used anywhere
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    if positive_value_exists(candidate_id):
        try:
            candidate_query = CandidateCampaign.objects.filter(id=candidate_id)
            if len(candidate_query):
                candidate_on_stage = candidate_query[0]
                candidate_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    try:
        if candidate_on_stage_found:
            # Update
            if candidate_twitter_handle is not False:
                candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
            if candidate_url is not False:
                candidate_on_stage.candidate_url = candidate_url
            if ballot_guide_official_statement is not False:
                candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement

            # Check to see if this is a We Vote-created election
            is_we_vote_google_civic_election_id = True \
                if convert_to_int(candidate_on_stage.google_civic_election_id) >= 1000000 \
                else False

            if contest_office_id is not False and is_we_vote_google_civic_election_id:
                candidate_on_stage.contest_office_id = contest_office_id
            candidate_on_stage.save()
            messages.add_message(request, messages.INFO, 'Candidate Campaign updated.')
        else:
            # Create new
            # election must be found
            election_manager = ElectionManager()
            election_results = election_manager.retrieve_election(google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                state_code = election.get_election_state()
            else:
                messages.add_message(request, messages.ERROR, 'Could not find election -- required to save candidate.')
                return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

            required_candidate_variables = True if positive_value_exists(candidate_name) and positive_value_exists(contest_office_id) else False
            if required_candidate_variables:
                candidate_on_stage = CandidateCampaign(
                    candidate_name=candidate_name,
                    google_civic_election_id=google_civic_election_id,
                    contest_office_id=contest_office_id,
                    state_code=state_code,
                )
                if candidate_twitter_handle is not False:
                    candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
                if candidate_url is not False:
                    candidate_on_stage.candidate_url = candidate_url
                if ballot_guide_official_statement is not False:
                    candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
                candidate_on_stage.save()
                candidate_id = candidate_on_stage.id
                messages.add_message(request, messages.INFO, 'New candidate saved.')
            else:
                messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save candidate.')
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_remove_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))
    else:
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
